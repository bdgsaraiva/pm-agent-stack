"""Critic (agent 5): code builds a card of facts that bear on a new idea and picks at most three question
slots; the model only words the questions; answers are stored in the journal entry.

Evidence behind every rule: docs/research/critic.md. In short:
  - Outside view first (Kahneman & Lovallo; Flyvbjerg; Lovallo, Clarke & Camerer): the card shows
      * a reference class of similar past ideas, weighted by similarity, as a distribution, only with
        6+ effective analogues (Lovallo & Sibony);
      * a market base rate: how often a random entry in the stored prices hit the idea's target before
        its stop within its horizon (same distances, same direction) - available from day one.
  - Small question budget (Sanna et al.; Ancker et al.): the pre-mortem by default; a counter-argument only
    when a fact on the card contradicts the idea; a Zweig rule question only when code finds a trigger.
    Card only for small, low-conviction ideas. No repeat on the same market within 30 days.
  - Grounded, never generic (Nemeth; Hirt & Markman; CRITIC): every question cites card facts; any figure
    in a question must be on the card (checked by the number auditor before saving).
  - Code picks and ranks the slots (LLM judges are biased: Zheng et al.); questions are frozen once
    saved and withdrawn only for a new fact (sycophancy: Sharma et al.).
  - Measure (Mellers; Dietvorst; McAleese): P(win) before/after, reaction, premise valid or wrong, what
    changed (logged as a journal event with reason "critic"), and whether the named risk happened.
Fridays: `weekly` lists open ideas; silent on those where nothing changed (Heuer: diagnostic evidence;
Duke: kill criteria are a state and a date).
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import audit, journal, runlog, sizing, store

ROOT = Path(__file__).resolve().parents[1]
SLOTS = ("premortem", "counter", "rule")
REACTIONS = ("useful", "known", "irrelevant")
CHANGES = ("none", "size", "stop", "target", "prob", "horizon", "pass")

ZWEIG = {
    "zweig-1": "The trend is your friend",
    "zweig-5": "The cheap get cheaper, the dear get dearer (no catalyst on a reversal)",
    "zweig-6": "Don't fight the Fed",
    "zweig-9": "Don't let what should happen bias you",
    "zweig-12": "The market isn't efficient, but it's tough to beat (what do you know the crowd doesn't?)",
    "zweig-14": "If you can't sleep at night, reduce",
    "zweig-15": "Don't put too much faith in experts (one source)",
    "zweig-16": "Don't focus on short-term information flows (headline)",
    "zweig-17": "Beware \"new era\" thinking",
}


def _all_cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "critic.yaml").read_text(encoding="utf-8"))


def cfg() -> dict:
    return _all_cfg()["critic"]


def _num(x):
    return journal._num(x)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _brt_today(now: datetime | None = None) -> str:
    return ((now or _now()) - timedelta(hours=3)).date().isoformat()


def group_of(price_ref: str | None) -> str | None:
    for g, ids in _all_cfg()["groups"].items():
        if price_ref in ids:
            return g
    return None


def _dir(e: dict) -> int | None:
    return {"long": 1, "short": -1}.get(e.get("direction"))


def _series(series_id: str | None, until=None) -> pd.DataFrame | None:
    if not series_id:
        return None
    try:
        q = "SELECT date, value, source_url FROM obs WHERE series_id = ?" + (" AND date <= ?" if until else "") + " ORDER BY date"
        df = store.connect().execute(q, [series_id, until] if until else [series_id]).df()
    except Exception:
        return None
    return df if len(df) else None


# ------------------------------------------------------------------ outside view
def base_rate(e: dict, until=None) -> dict | None:
    """Random-entry baseline with the idea's own target, stop, horizon and direction, on stored daily closes.
    Descriptive only: windows overlap, closes not highs/lows, and the period is short."""
    c = cfg()
    entry, tgt, inv, d = _num(e.get("entry_price")), _num(e.get("target")), _num(e.get("invalidation_price")), _dir(e)
    if None in (entry, tgt, inv, d) or entry <= 0 or entry == inv:
        return None
    if d * (tgt - entry) <= 0 or d * (entry - inv) <= 0:
        return None  # target must be on the profit side and invalidation on the loss side
    df = _series(e.get("price_ref"), until)
    if df is None:
        return None
    p = df["value"].astype(float).to_numpy()
    H = max(1, int(round(float(e.get("horizon_days") or 30) * 5 / 7)))
    up, dn = abs(tgt / entry - 1), abs(inv / entry - 1)
    n = len(p) - H
    if n < c["base_rate_min_starts"]:
        return None
    t = s = w = 0
    for i in range(n):
        path = d * (p[i + 1:i + 1 + H] / p[i] - 1)
        hu, hd = np.flatnonzero(path >= up), np.flatnonzero(path <= -dn)
        a, b = (hu[0] if len(hu) else H), (hd[0] if len(hd) else H)
        if a < b:
            t += 1; w += 1
        elif b < a:
            s += 1
        elif path[-1] > 0:
            w += 1
    return {"series": e["price_ref"], "since": str(df["date"].iloc[0])[:10], "to": str(df["date"].iloc[n - 1])[:10],
            "n_starts": int(n), "n_independent": int(n // H), "horizon_trading_days": H,
            "target_pct": round(100 * up, 1), "stop_pct": round(100 * dn, 1),
            "target_first_pct": round(100 * t / n, 1), "stop_first_pct": round(100 * s / n, 1),
            "neither_pct": round(100 * (n - t - s) / n, 1), "win_pct": round(100 * w / n, 1),
            "source_url": df["source_url"].iloc[-1]}


def _similarity(e: dict, o: dict) -> float:
    w = cfg()["similarity"]
    # source alone is a weak link: it counts only together with the same group or market (reviewer finding)
    same_m = (e.get("market") or "").strip().lower() == (o.get("market") or "").strip().lower() and e.get("market")
    same_d = e.get("direction") == o.get("direction")
    g = group_of(e.get("price_ref"))
    out = 0.0
    if same_m and same_d:
        out = max(out, w["market_direction"])
    if same_m:
        out = max(out, w["market"])
    if g and g == group_of(o.get("price_ref")) and same_d:
        out = max(out, w["group_direction"])
    if out > 0 and e.get("source") and e.get("source") == o.get("source"):
        out = min(1.0, out + w["source"] / 3)
    return out


def reference_class(e: dict, entries: list[dict], now: datetime | None = None) -> dict:
    rows, grave = [], []
    for o in entries:
        if o.get("id") == e.get("id") or o.get("book") == "example":
            continue
        w = _similarity(e, o)
        if w <= 0:
            continue
        if o.get("status") == "closed" and _num(o.get("r_multiple")) is not None:
            rows.append((w, float(o["r_multiple"]), o["id"]))
        elif o.get("status") == "rejected":
            r = journal.what_happened(o, now)
            if r is not None:
                grave.append((w, r, o["id"]))
    out = {"n": len(rows), "n_eff": 0.0, "enough": False, "graveyard_n": len(grave)}
    if rows:
        ws = np.array([r[0] for r in rows]); rs = np.array([r[1] for r in rows])
        out.update({"n_eff": round(float(ws.sum()), 1),   # sum of similarity weights = count of fully similar ideas
                    "hit_rate_pct": round(100 * float((ws * (rs > 0)).sum() / ws.sum()), 1),
                    "avg_r": round(float((ws * rs).sum() / ws.sum()), 2),
                    "median_r": round(float(np.median(rs)), 2), "worst_r": round(float(rs.min()), 2),
                    "analogues": [r[2] for r in sorted(rows, key=lambda r: -r[0])[:5]]})
        out["enough"] = out["n_eff"] >= cfg()["min_analogues"]
    if grave:
        out["graveyard_avg_r"] = round(sum(g[1] for g in grave) / len(grave), 2)
    return out


# ------------------------------------------------------------------ tape, crowd, policy, alerts
def tape(e: dict, until=None) -> dict | None:
    c = cfg()
    df = _series(e.get("price_ref"), until)
    if df is None or len(df) <= c["trend_days"]:
        return None
    p = df["value"].astype(float).to_numpy()
    tr = 100 * (p[-1] / p[-1 - c["trend_days"]] - 1)
    trend = "up" if tr >= c["trend_pct"] else "down" if tr <= -c["trend_pct"] else "flat"
    d = _dir(e)
    out = {"last": round(float(p[-1]), 4), "last_date": str(df["date"].iloc[-1])[:10], "source_url": df["source_url"].iloc[-1],
           "trend_pct": round(float(tr), 1), "trend": trend,
           "against_trend": bool(d and trend != "flat" and ((trend == "up") != (d > 0)))}
    entry = _num(e.get("entry_price"))
    if entry:
        out["since_entry_pct"] = round(100 * (p[-1] / entry - 1), 2)
        out["r_now"] = journal.r_multiple(e, float(p[-1]))
    return out


def crowding(e: dict) -> dict | None:
    code = journal._cfg()["cftc_map"].get(e.get("price_ref") or "")
    c = journal._cftc_pct(code)
    if not c or _dir(e) is None:
        return None
    c["on_side_pct"] = c["pct"] if _dir(e) > 0 else 100 - c["pct"]
    c["crowded"] = c["on_side_pct"] >= cfg()["crowded_pct"]
    c["code"] = code
    return c


def policy(until=None) -> dict | None:
    c = cfg()
    df = _series(c["policy_series"], until)
    if df is None or len(df) <= c["trend_days"]:
        return None
    v = df["value"].astype(float).to_numpy()
    bp = round(100 * (v[-1] - v[-1 - c["trend_days"]]), 0)
    return {"series": c["policy_series"], "change_bp": bp, "date": str(df["date"].iloc[-1])[:10],
            "direction": "tightening" if bp >= c["policy_bp"] else "easing" if bp <= -c["policy_bp"] else None,
            "source_url": df["source_url"].iloc[-1]}


def _latest_pack(asof: str | None, briefs: Path | None = None) -> tuple[str | None, dict | None]:
    briefs = audit._briefs(briefs)
    days = sorted(p.name for p in briefs.glob("????-??-??") if (p / "facts.json").exists())
    if asof:
        days = [d for d in days if d <= asof]
    if not days:
        return None, None
    return days[-1], json.loads((briefs / days[-1] / "facts.json").read_text(encoding="utf-8"))


def market_alerts(e: dict, facts: dict | None) -> list[dict]:
    if not facts:
        return []
    m = (e.get("market") or "").lower()
    code = journal._cfg()["cftc_map"].get(e.get("price_ref") or "")
    out = []
    live = sorted((a for a in facts.get("alerts", []) if not a.get("no_longer_firing")),   # rebuilt packs: rank order
                  key=lambda a: -float(a.get("severity") or 0))                         # is not severity order
    for a in live:
        if a.get("id") in (e.get("price_ref"), code) or (m and re.search(rf"\b{re.escape(m)}\b", a.get("text", "").lower())):
            pct = re.search(r"([+\-−]?\d+(?:\.\d+)?)%", a.get("text", ""))
            move = float(pct.group(1).replace("−", "-")) if pct and a.get("kind", "").endswith("move") else None
            against = bool(move is not None and _dir(e) and move * _dir(e) < 0)
            out.append({"ref": a.get("ref"), "text": a.get("text"), "kind": a.get("kind"), "against": against,
                        "source_url": a.get("source_url")})
    return out


# ------------------------------------------------------------------ rules
def rules(e: dict, t: dict | None, cr: dict | None, pol: dict | None) -> list[dict]:
    c, out = cfg(), []
    thesis = (e.get("_body") or "").split("## What breaks it")[0].lower() + " " + (e.get("why_different") or "").lower()

    def add(rule, severity, kind, facts, why):
        out.append({"rule": rule, "name": ZWEIG.get(rule, rule), "severity": round(severity, 2), "kind": kind,
                    "facts": facts, "why": why})

    if t and t["against_trend"]:
        add("zweig-1", 1.5 + abs(t["trend_pct"]) / 10, "data", ["tape.trend_pct", "tape.trend_days"],
            "the idea fades a 3-month trend")
        if not (e.get("catalysts") or "").strip():
            add("zweig-5", 1.4 + abs(t["trend_pct"]) / 20, "data", ["tape.trend_pct"],
                "a reversal with no catalyst written down")
    if cr and (cr["crowded"] or (e.get("source") == "consensus" and not (e.get("why_different") or "").strip())):
        sev = 2 + max(0, cr["on_side_pct"] - c["crowded_pct"]) / 10 if cr["crowded"] else 1.2
        add("zweig-12", sev, "data" if cr["crowded"] else "text",
            ["crowd.on_side_pct", "crowd.date"] if cr["crowded"] else ["entry.source", "crowd.on_side_pct"],
            "crowded on your side" if cr["crowded"] else "source is consensus and no edge is written down")
    elif e.get("source") == "consensus" and not (e.get("why_different") or "").strip():
        add("zweig-12", 1.2, "text", ["entry.source"], "source is consensus and no edge is written down")
    g = group_of(e.get("price_ref"))
    if pol and pol["direction"] and g in ("equity", "rates") and _dir(e):
        fights = (pol["direction"] == "tightening" and _dir(e) > 0) or (pol["direction"] == "easing" and _dir(e) < 0)
        if fights:
            add("zweig-6", 1.6, "data", ["policy.change_bp", "policy.date"], f"positioned against {pol['direction']}")
    if re.search(c["should_words"], thesis):
        add("zweig-9", 1.0, "text", ["entry.thesis"], "\"should\" language in the thesis")
    if re.search(c["new_era_words"], thesis):
        add("zweig-17", 1.1, "text", ["entry.thesis"], "\"new era\" language in the thesis")
    if e.get("source") in c["single_source_kinds"]:
        add("zweig-15", 0.9, "text", ["entry.source"], f"rests on one {e.get('source')} source")
    if e.get("source") in c["headline_kinds"]:
        add("zweig-16", 0.9, "text", ["entry.source"], "came from a headline")
    st = e.get("state") or {}
    jc = journal._cfg()["checks"]
    if (_num(st.get("sleep")) or 9) <= jc["poor_state_sleep"] or (_num(st.get("stress")) or 0) >= jc["poor_state_stress"]:
        add("zweig-14", 1.3, "data", ["entry.state"], "poor sleep or high stress at entry")
    return sorted(out, key=lambda r: -r["severity"])


# ------------------------------------------------------------------ card and plan
def _created_brt(e: dict) -> str | None:
    try:
        return (pd.Timestamp(e["created_utc"]) - pd.Timedelta(hours=3)).date().isoformat()
    except Exception:
        return None


def _horizon_date(e: dict) -> str | None:
    try:
        return (pd.Timestamp(e["created_utc"]) + pd.Timedelta(days=int(e.get("horizon_days") or 30))).date().isoformat()
    except Exception:
        return None


def card(e: dict, entries: list[dict] | None = None, asof: str | None = None, now: datetime | None = None,
         briefs: Path | None = None) -> dict:
    """Everything the critic may say, computed by code, with a flat `facts` map the questions must cite."""
    entries = entries if entries is not None else journal.load_all()
    now = now or _now()
    asof = asof or _created_brt(e) or _brt_today(now)   # as of the idea's own date: no look-ahead on old ideas
    pack_date, facts_json = _latest_pack(asof, briefs)
    until = asof
    br = base_rate(e, until)
    ref = reference_class(e, entries, now)
    t = tape(e, until)
    cr = crowding(e)
    pol = policy(until)
    al = market_alerts(e, facts_json)
    p_implied, p_src = sizing.prob_for(int(e.get("conviction") or 3), entries)
    stated = _num(e.get("prob_win"))
    p_before = stated if stated is not None else p_implied

    F: dict[str, dict] = {}

    def put(key, value, label, source):
        if value is not None:
            F[key] = {"value": value, "label": label, "source": source}

    jsrc = e.get("_path") or "journal"
    put("entry.price", _num(e.get("entry_price")), "entry price", e.get("entry_price_source") or jsrc)
    put("entry.target", _num(e.get("target")), "target", jsrc)
    put("entry.invalidation", _num(e.get("invalidation_price")) or e.get("invalidation"), "invalidation", jsrc)
    put("entry.horizon_days", e.get("horizon_days"), "horizon (calendar days)", jsrc)
    put("entry.horizon_date", _horizon_date(e), "horizon date", jsrc)
    put("entry.reward_risk", e.get("reward_risk"), "reward-to-risk", jsrc)
    put("entry.conviction", e.get("conviction"), "conviction (1-5)", jsrc)
    put("entry.source", e.get("source"), "idea source", jsrc)
    put("entry.thesis", (e.get("_body") or "").split("## What breaks it")[0].replace("## Thesis", "").strip()[:300] or None,
        "thesis (your words)", jsrc)
    put("entry.state", e.get("state") if any((e.get("state") or {}).values()) else None, "sleep/stress at entry", jsrc)
    put("prob.before_pct", round(100 * p_before, 1), "your P(win)" if stated is not None else f"implied P(win): {p_src}",
        jsrc if stated is not None else "pmstack/sizing.py")
    if br:
        for k in ("target_first_pct", "stop_first_pct", "neither_pct", "win_pct", "n_starts", "n_independent",
                  "since", "to", "horizon_trading_days", "target_pct", "stop_pct"):
            put(f"base.{k}", br[k], f"market base rate: {k.replace('_', ' ')}", br["source_url"])
        put("base.gap_pp", round(100 * p_before - br["win_pct"], 1), "your P(win) minus the base-rate win share",
            "pmstack/critic.py")
    if ref["n"]:
        for k in ("n", "n_eff", "hit_rate_pct", "avg_r", "median_r", "worst_r"):
            put(f"ref.{k}", ref.get(k), f"similar past ideas: {k.replace('_', ' ')}", "journal")
        if ref["enough"]:
            put("ref.gap_pp", round(100 * p_before - ref["hit_rate_pct"], 1), "your P(win) minus similar ideas' hit rate", "journal")
    if ref.get("graveyard_n"):
        put("ref.graveyard_n", ref["graveyard_n"], "similar ideas you passed on", "journal")
        put("ref.graveyard_avg_r", ref.get("graveyard_avg_r"), "their would-have-been R", "journal")
    if t:
        put("tape.last", t["last"], f"last price ({t['last_date']})", t["source_url"])
        put("tape.last_date", t["last_date"], "last price date", t["source_url"])
        put("tape.trend_pct", t["trend_pct"], f"{cfg()['trend_days']}-trading-day change, %", t["source_url"])
        put("tape.trend_days", cfg()["trend_days"], "trend window (trading days)", "config/critic.yaml")
        put("tape.since_entry_pct", t.get("since_entry_pct"), "change since entry, %", t["source_url"])
        put("tape.r_now", t.get("r_now"), "R so far", "journal")
    if cr:
        put("crowd.on_side_pct", cr["on_side_pct"], "CFTC managed-money percentile on your side (3y)",
            "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm")
        put("crowd.net_pct_oi", cr["net_pct_oi"], "managed money net, % of OI", "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm")
        put("crowd.date", cr["date"], "CFTC report date", "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm")
    if pol:
        put("policy.change_bp", pol["change_bp"], f"2y Treasury change over {cfg()['trend_days']} trading days, bp", pol["source_url"])
        put("policy.date", pol["date"], "2y Treasury date", pol["source_url"])
    for i, a in enumerate(al[:3], 1):
        put(f"alert.{i}", f"{a['ref']}: {a['text']}", "today's alert on this market", a.get("source_url") or a["ref"])
    # consensus map (agent 7): trend-follower proxy, label and the narratives on this market (descriptive)
    cmk = next((r for r in ((facts_json or {}).get("sections", {}).get("consensus") or {}).get("markets", [])
                if r.get("market") == e.get("price_ref")), None)
    opp_hot = []
    if cmk:
        d_ = _dir(e) or 0
        if cmk.get("trend"):
            put("map.trend_score", cmk["trend"]["score"], "trend-follower proxy (avg sign of 1/3/12-month returns)",
                cmk["trend"].get("source_url") or "pmstack/consensus.py")
        put("map.label", cmk.get("label"), "consensus-map label (inference)", "pmstack/consensus.py")
        hot = {"spreading", "peaking"}
        opp_hot = [n["name"] for n in cmk.get("narratives", []) if n["sign"] == -d_ and n["stage"] in hot]
        same_hot = [n["name"] for n in cmk.get("narratives", []) if n["sign"] == d_ and n["stage"] in hot]
        put("map.narratives_against", ", ".join(opp_hot) or None, "narratives pushing the other way, spreading or peaking (unvalidated)",
            "https://www.gdeltproject.org/")
        put("map.narratives_with", ", ".join(same_hot) or None, "narratives pushing your way, spreading or peaking (unvalidated)",
            "https://www.gdeltproject.org/")

    rl = rules(e, t, cr, pol)
    contra = []
    gap = None
    if ref.get("enough"):
        gap = F["ref.gap_pp"]["value"]
        if gap >= cfg()["gap_pp"]:
            contra.append({"basis": "reference-class", "severity": 2 + gap / 20, "facts": ["ref.hit_rate_pct", "ref.n", "prob.before_pct"]})
    elif br:
        gap = F["base.gap_pp"]["value"]
        if gap >= cfg()["gap_pp"]:
            contra.append({"basis": "base-rate", "severity": 1.8 + gap / 20,
                           "facts": ["base.win_pct", "base.target_first_pct", "base.stop_first_pct", "prob.before_pct"]})
    if t and t["against_trend"]:
        contra.append({"basis": "trend", "severity": 1.5 + abs(t["trend_pct"]) / 10, "facts": ["tape.trend_pct"]})
    if cr and cr["crowded"]:
        contra.append({"basis": "crowding", "severity": 2 + (cr["on_side_pct"] - cfg()["crowded_pct"]) / 10,
                       "facts": ["crowd.on_side_pct", "crowd.date"]})
    for i, a in enumerate(al[:3], 1):
        if a["against"]:
            contra.append({"basis": "alert", "severity": 1.7, "facts": [f"alert.{i}"]})
    if opp_hot:
        contra.append({"basis": "narrative", "severity": 1.6, "facts": ["map.narratives_against"]})
    contra.sort(key=lambda x: -x["severity"])
    return {"id": e.get("id"), "asof": asof, "pack_date": pack_date,
            "computed_utc": now.isoformat(), "facts": F, "rules": rl, "contradictions": contra,
            "base_rate": br, "reference_class": ref, "gap_pp": gap}


def _asked_recently(e: dict, entries: list[dict], basis: str, now: datetime) -> bool:
    days = cfg()["repeat_days"]
    m = (e.get("market") or "").strip().lower()
    for o in entries:
        if o.get("id") == e.get("id") or (o.get("market") or "").strip().lower() != m:
            continue
        for q in (o.get("critic") or {}).get("questions", []):
            if q.get("basis") == basis and q.get("answer") and q.get("answered_utc"):
                if now - pd.Timestamp(q["answered_utc"]).to_pydatetime() <= timedelta(days=days):
                    return True
    return False


def plan(e: dict, cd: dict, entries: list[dict] | None = None, now: datetime | None = None) -> dict:
    """Which slots to fill (code decides), the tier, and the silence reason if any."""
    c, now = cfg(), now or _now()
    entries = entries if entries is not None else journal.load_all()
    units = _num(e.get("size_planned")) or 0.0
    if e.get("status") not in ("open", "idea"):
        return {"silent": True, "reason": f"status {e.get('status')}", "tier": "card-only", "slots": []}
    if int(e.get("conviction") or 0) <= c["silent_max_conviction"] and units <= c["silent_max_units"]:
        return {"silent": True, "reason": f"conviction {e.get('conviction')} at {units:g} units: card only",
                "tier": "card-only", "slots": []}
    hz = "entry.horizon_date" if "entry.horizon_date" in cd["facts"] else "entry.horizon_days"
    pm_facts = [k for k in (hz, "entry.invalidation", "base.stop_first_pct") if k in cd["facts"]]
    slots = [{"slot": "premortem", "basis": "premortem", "facts": pm_facts,
              "brief": "Certain failure on the horizon date, idea lost 1R: most likely why? Ask for at least one "
                       "reason that is a thesis error, not luck. If base.stop_first_pct is on the card, quote it."}]
    used = set()
    rule_of = {"trend": ("zweig-1", "zweig-5"), "crowding": ("zweig-12",)}
    for x in cd["contradictions"]:
        if _asked_recently(e, entries, x["basis"], now) or any(_asked_recently(e, entries, r, now) for r in rule_of.get(x["basis"], ())):
            continue
        slots.append({"slot": "counter", "basis": x["basis"], "facts": x["facts"],
                      "brief": "The strongest case against, built on these facts only; state the critic's own number "
                               "(e.g. 'random entries hit your target first 32% of the time; you imply 50%'). One question."})
        used.add(x["basis"])
        break
    basis_of = {"zweig-1": "trend", "zweig-5": "trend", "zweig-12": "crowding"}
    for r in cd["rules"]:
        if basis_of.get(r["rule"]) in used:
            continue
        if _asked_recently(e, entries, r["rule"], now) or (basis_of.get(r["rule"]) and _asked_recently(e, entries, basis_of[r["rule"]], now)):
            continue
        slots.append({"slot": "rule", "basis": r["rule"], "facts": r["facts"],
                      "brief": f"{r['name']} — triggered because {r['why']}. Ask one question about it."})
        break
    slots = slots[: c["max_questions"]]
    data_rule = any(r["kind"] == "data" for r in cd["rules"])
    tier = "before-sizing" if data_rule or (cd["gap_pp"] is not None and cd["gap_pp"] >= c["gap_pp"]) else "when-you-like"
    return {"silent": False, "reason": None, "tier": tier, "slots": slots}


def attach(e: dict, entries: list[dict] | None = None, now: datetime | None = None) -> dict:
    """Compute the card and plan and store a compact copy on the entry (called by journal.new)."""
    now = now or _now()
    entries = entries if entries is not None else journal.load_all()
    cd = card(e, entries, now=now)
    pl = plan(e, cd, entries, now)
    prev = e.get("critic") or {}
    e["critic"] = {
        "card_utc": cd["computed_utc"], "pack_date": cd["pack_date"], "tier": pl["tier"], "silent": pl["silent"],
        "silence_reason": pl["reason"], "prob_before": round(cd["facts"]["prob.before_pct"]["value"] / 100, 3),
        "prob_after": prev.get("prob_after"),
        "card": {k: v["value"] for k, v in cd["facts"].items() if k != "entry.thesis"},
        "rules": [r["rule"] for r in cd["rules"]],
        "slots": [{"slot": s["slot"], "basis": s["basis"], "facts": s["facts"]} for s in pl["slots"]],
        "questions": prev.get("questions", []),
    }
    e["critic"] = _plain(e["critic"])
    return e


def _plain(x):
    """numpy scalars -> python, so the entry's YAML stays plain."""
    return json.loads(json.dumps(x, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


# ------------------------------------------------------------------ saving and answering
def _pool_from_card(e: dict, keys: list[str] | None = None) -> audit.Pool:
    """Pool of the card facts a question cites (all of them when keys is None), each with its kind."""
    pool = audit.Pool()
    cr = e.get("critic") or {}
    for k, v in (cr.get("card") or {}).items():
        if keys is not None and k not in keys:
            continue
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            pool.add_value(v, f"{k} {e.get('market', '')}", audit._key_kind(k))
        elif isinstance(v, str):
            pool.add_text(v, f"{k} {e.get('market', '')} {v}")
            pool.dates.add(v) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) else None
    return pool


def save(entry_id: str, questions: list[dict], now: datetime | None = None) -> tuple[dict, list[str]]:
    """Validate and store the model's wording. Returns (entry, problems); nothing is written on problems."""
    e = journal.get(entry_id)
    now = now or _now()
    cr = e.get("critic")
    if not cr or "error" in cr or "slots" not in cr:
        e = attach(e, now=now); cr = e["critic"]
    errs = []
    planned = {s["slot"]: s for s in cr.get("slots", [])}
    if cr.get("silent"):
        errs.append(f"card only: {cr.get('silence_reason')}")
    if cr.get("questions"):
        errs.append("questions already saved; they are frozen (withdraw one with a new fact)")
    if len(questions) > cfg()["max_questions"]:
        errs.append(f"at most {cfg()['max_questions']} questions")
    keys = set((cr.get("card") or {}).keys()) | {"entry.thesis"}
    out = []
    for i, q in enumerate(questions, 1):
        s = planned.get(q.get("slot"))
        if not s:
            errs.append(f"q{i}: slot '{q.get('slot')}' was not planned by code ({', '.join(planned) or 'none'})")
            continue
        cited = [k for k in q.get("facts") or s["facts"] if k in keys]
        if not cited:
            errs.append(f"q{i}: cites no fact from the card")
        rep = audit.audit_text(q.get("text", ""), _pool_from_card(e, cited))   # figures must come from the cited facts
        orphans = [f["text"] for f in rep["figures"] if f["status"] in ("orphan", "unbound")]
        if orphans:
            errs.append(f"q{i}: figures not on the card: {', '.join(orphans)}")
        out.append({"id": f"q{i}", "slot": s["slot"], "basis": s["basis"], "facts": cited, "text": q.get("text", "").strip(),
                    "asked_utc": now.isoformat(), "status": "open", "answer": None, "answered_utc": None,
                    "thesis_error": None, "reaction": None, "premise": None, "changed": None, "happened": None})
    if errs:
        return e, errs
    cr["questions"] = out
    journal.write(dict(e))
    runlog.log(runlog.new_run_id(), "critic:save", "ok", id=entry_id, tier=cr["tier"],
               slots=[q["slot"] for q in out], bases=[q["basis"] for q in out])
    return e, []


def answer(entry_id: str, qid: str | None = None, text: str | None = None, thesis_error: bool | None = None,
           reaction: str | None = None, premise: str | None = None, changed: str | None = None,
           prob_after: float | None = None, now: datetime | None = None) -> dict:
    e = journal.get(entry_id)
    now = now or _now()
    cr = e.get("critic") or {}
    if prob_after is not None:
        if not 0 < float(prob_after) < 1:
            raise SystemExit("--prob-after is a probability between 0 and 1 (e.g. 0.45)")
        cr["prob_after"] = float(prob_after)
    if qid:
        q = next((q for q in cr.get("questions", []) if q["id"] == qid), None)
        if not q:
            raise SystemExit(f"{entry_id}: no question {qid}")
        if reaction and reaction not in REACTIONS:
            raise SystemExit(f"reaction must be one of {REACTIONS}")
        if changed and changed not in CHANGES:
            raise SystemExit(f"changed must be one of {CHANGES}")
        if premise and premise not in ("valid", "wrong"):
            raise SystemExit("premise must be valid or wrong")
        if text:
            q.update({"answer": text, "answered_utc": now.isoformat(), "status": "answered"})
        for k, v in (("thesis_error", thesis_error), ("reaction", reaction), ("premise", premise), ("changed", changed)):
            if v is not None:
                q[k] = v
        if changed and changed != "none":
            e.setdefault("events", []).append({"ts": now.isoformat(), "action": "note", "size": None, "price": None,
                                               "reason": "critic", "detail": f"{qid} ({q['slot']}, {q['basis']}) changed {changed}"})
    e["critic"] = cr
    journal.write(dict(e))
    runlog.log(runlog.new_run_id(), "critic:answer", "ok", id=entry_id, q=qid, changed=changed, reaction=reaction,
               prob_after=prob_after)
    return e


def withdraw(entry_id: str, qid: str, new_fact: str, now: datetime | None = None) -> dict:
    if not (new_fact or "").strip():
        raise SystemExit("a question is withdrawn only for a new fact (sycophancy guard)")
    e = journal.get(entry_id)
    q = next((q for q in (e.get("critic") or {}).get("questions", []) if q["id"] == qid), None)
    if not q:
        raise SystemExit(f"{entry_id}: no question {qid}")
    q.update({"status": "withdrawn", "withdrawn_utc": (now or _now()).isoformat(), "new_fact": new_fact})
    journal.write(dict(e))
    runlog.log(runlog.new_run_id(), "critic:withdraw", "ok", id=entry_id, q=qid)
    return e


def outcome(entry_id: str, qid: str, happened: bool) -> dict:
    e = journal.get(entry_id)
    q = next((q for q in (e.get("critic") or {}).get("questions", []) if q["id"] == qid), None)
    if not q:
        raise SystemExit(f"{entry_id}: no question {qid}")
    q["happened"] = bool(happened)
    journal.write(dict(e))
    runlog.log(runlog.new_run_id(), "critic:outcome", "ok", id=entry_id, q=qid, happened=happened)
    return e


# ------------------------------------------------------------------ Fridays
def weekly(asof: str | None = None, now: datetime | None = None, briefs: Path | None = None, write: bool = False) -> dict:
    """Open ideas with what changed this week; silent on ideas where nothing did."""
    c, now = cfg()["weekly"], now or _now()
    asof = asof or _brt_today(now)
    briefs = audit._briefs(briefs)
    entries = journal.load_all()
    ideas = []
    for e in entries:
        if e.get("status") not in ("open", "idea"):
            continue
        row = {"id": e["id"], "market": e.get("market"), "direction": e.get("direction"), "book": e.get("book"),
               "conviction": e.get("conviction"), "entry_price": _num(e.get("entry_price")),
               "invalidation_price": _num(e.get("invalidation_price")), "target": _num(e.get("target")),
               "horizon_date": _horizon_date(e), "reasons": []}
        df = _series(e.get("price_ref"), asof)
        if df is not None and len(df) > 25:
            p = df["value"].astype(float).to_numpy()
            r = np.diff(np.log(p[-61:]))
            wk = 100 * (p[-1] / p[-6] - 1)
            wsd = float(r.std(ddof=1)) * np.sqrt(5) * 100 if len(r) > 5 else None
            row.update({"last": round(float(p[-1]), 4), "last_date": str(df["date"].iloc[-1])[:10],
                        "source_url": df["source_url"].iloc[-1], "week_pct": round(wk, 2),
                        "week_sd": round(wk / wsd, 1) if wsd else None, "r_now": journal.r_multiple(e, float(p[-1]))})
            entry, inv = row["entry_price"], row["invalidation_price"]
            if entry and inv and entry != inv:
                left = (p[-1] - inv) / (entry - inv)
                row["risk_left"] = round(float(left), 2)
                if left <= 0:
                    row["reasons"].append("invalidated")
                elif left <= c["risk_left"]:
                    row["reasons"].append(f"under {int(100 * c['risk_left'])}% of the risk distance left")
            if row.get("week_sd") is not None and abs(row["week_sd"]) >= c["move_sd"]:
                row["reasons"].append(f"moved {row['week_sd']:+} weekly sd")
        if row["horizon_date"] and row["horizon_date"] <= asof:
            row["reasons"].append("past horizon")
        cr = crowding(e)
        if cr:
            row["crowd_on_side_pct"] = cr["on_side_pct"]
            then = ((e.get("critic") or {}).get("card") or {}).get("crowd.on_side_pct")
            if then is not None:
                row["crowd_change_pct"] = round(cr["on_side_pct"] - float(then), 0)
                if abs(row["crowd_change_pct"]) >= c["crowd_move_pct"]:
                    row["reasons"].append(f"crowding moved {row['crowd_change_pct']:+.0f} percentile points")
        recent = []
        for d in sorted(p.name for p in briefs.glob("????-??-??")):
            week_lo = (pd.Timestamp(asof) - pd.Timedelta(days=c["alert_lookback_days"])).date().isoformat()
            born = _created_brt(e) or ""
            if week_lo < d <= asof and d >= born:          # this week's packs, none from before the idea
                fj = briefs / d / "facts.json"
                if fj.exists():
                    recent += market_alerts(e, json.loads(fj.read_text(encoding="utf-8")))
        if recent:
            row["alerts"] = [{"ref": a["ref"], "text": a["text"]} for a in recent[:5]]
            row["reasons"].append(f"{len(recent)} alert(s) on this market")
        row["open_questions"] = [{"id": q["id"], "slot": q["slot"], "text": q["text"]}
                                 for q in (e.get("critic") or {}).get("questions", []) if q.get("status") == "open"]
        row["silent"] = not row["reasons"]
        ideas.append(row)
    out = {"asof": asof, "computed_utc": now.isoformat(), "ideas": ideas,
           "summary": {"open": len(ideas), "to_review": sum(1 for i in ideas if not i["silent"]),
                       "silent": sum(1 for i in ideas if i["silent"]),
                       "unanswered_questions": sum(len(i["open_questions"]) for i in ideas)}}
    if write:
        d = briefs / asof
        d.mkdir(parents=True, exist_ok=True)
        (d / "critic-weekly.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    runlog.log(runlog.new_run_id(), "critic:weekly", "ok", asof=asof, **out["summary"],
               output=str(briefs / asof / "critic-weekly.json") if write else None)
    return out


# ------------------------------------------------------------------ measure
def stats(entries: list[dict] | None = None) -> dict:
    entries = entries if entries is not None else journal.load_all()
    qs, shifts, briers = [], [], []
    critic_events = 0
    for e in entries:
        cr = e.get("critic") or {}
        for q in cr.get("questions", []):
            qs.append(q)
        critic_events += sum(1 for ev in e.get("events", []) if str(ev.get("reason", "")).lower().startswith("critic"))
        if cr.get("prob_after") is not None and cr.get("prob_before") is not None:
            shifts.append(100 * (float(cr["prob_after"]) - float(cr["prob_before"])))
            if e.get("status") == "closed" and _num(e.get("r_multiple")) is not None:
                y = 1.0 if float(e["r_multiple"]) > 0 else 0.0
                briers.append(((float(cr["prob_before"]) - y) ** 2, (float(cr["prob_after"]) - y) ** 2))
    by = {}
    for q in qs:
        k = f"{q['slot']}:{q['basis']}"
        b = by.setdefault(k, {"asked": 0, "answered": 0, "changed": 0, "useful": 0, "premise_wrong": 0, "happened": 0, "scored": 0})
        b["asked"] += 1
        b["answered"] += q.get("status") == "answered"
        b["changed"] += bool(q.get("changed") and q["changed"] != "none")
        b["useful"] += q.get("reaction") == "useful"
        b["premise_wrong"] += q.get("premise") == "wrong"
        if q.get("happened") is not None:
            b["scored"] += 1
            b["happened"] += bool(q["happened"])
    out = {"ideas_with_critic": sum(1 for e in entries if e.get("critic")), "questions": len(qs),
           "answered": sum(1 for q in qs if q.get("status") == "answered"),
           "changed_decision": sum(1 for q in qs if q.get("changed") and q["changed"] != "none"),
           "critic_events": critic_events, "by_template": by,
           "false_alarm_rate": (round(sum(q.get("premise") == "wrong" for q in qs) / rated, 2)
                                if (rated := sum(q.get("premise") in ("valid", "wrong") for q in qs)) else None),
           "prob_shift_pp_mean": round(statistics.mean(shifts), 1) if shifts else None, "prob_shift_n": len(shifts)}
    if len(briers) >= 5:
        out["brier_before"] = round(statistics.mean(b[0] for b in briers), 3)
        out["brier_after"] = round(statistics.mean(b[1] for b in briers), 3)
    return out


# ------------------------------------------------------------------ CLI
def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack critic", description="Critic: card, questions, answers, Friday pass, stats")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("card", help="compute the card and the planned question slots for an idea")
    c.add_argument("id"); c.add_argument("--date"); c.add_argument("--write", action="store_true", help="store on the entry")
    s = sub.add_parser("save", help="store the model's questions (validated: slots, cited facts, figures)")
    s.add_argument("id"); s.add_argument("--json", required=True, help='[{"slot":"premortem","text":"...","facts":["..."]}]')
    a = sub.add_parser("answer"); a.add_argument("id"); a.add_argument("--q"); a.add_argument("--text")
    a.add_argument("--thesis-error", action="store_true", default=None); a.add_argument("--reaction", choices=REACTIONS)
    a.add_argument("--premise", choices=("valid", "wrong")); a.add_argument("--changed", choices=CHANGES)
    a.add_argument("--prob-after", type=float)
    w = sub.add_parser("withdraw"); w.add_argument("id"); w.add_argument("--q", required=True); w.add_argument("--new-fact", required=True)
    o = sub.add_parser("outcome"); o.add_argument("id"); o.add_argument("--q", required=True)
    o.add_argument("--happened", required=True, choices=("yes", "no"))
    wk = sub.add_parser("weekly"); wk.add_argument("--date"); wk.add_argument("--write", action="store_true")
    sub.add_parser("stats")
    x = p.parse_args(argv)

    if x.cmd == "card":
        e = journal.get(x.id)
        entries = journal.load_all()
        cd = card(e, entries, asof=x.date)
        pl = plan(e, cd, entries)
        if x.write:
            attach(e, entries); journal.write(dict(e))
        runlog.log(runlog.new_run_id(), "critic:card", "ok", id=x.id, tier=pl["tier"], silent=pl["silent"],
                   slots=[s["slot"] for s in pl["slots"]], rules=[r["rule"] for r in cd["rules"]], written=x.write)
        print(json.dumps({"id": x.id, "tier": pl["tier"], "silent": pl["silent"], "silence_reason": pl["reason"],
                          "slots": pl["slots"], "facts": cd["facts"], "rules": cd["rules"],
                          "contradictions": cd["contradictions"]}, indent=1, ensure_ascii=False, default=str))
        return 0
    if x.cmd == "save":
        raw = x.json.strip()
        qs = json.loads(raw) if raw.startswith("[") else json.loads(Path(raw).read_text(encoding="utf-8"))
        e, errs = save(x.id, qs)
        print(json.dumps({"id": x.id, "saved": not errs, "problems": errs,
                          "questions": (e.get("critic") or {}).get("questions") if not errs else qs}, indent=1, ensure_ascii=False))
        return 1 if errs else 0
    if x.cmd == "answer":
        e = answer(x.id, x.q, x.text, x.thesis_error, x.reaction, x.premise, x.changed, x.prob_after)
        print(json.dumps((e.get("critic") or {}), indent=1, ensure_ascii=False, default=str)); return 0
    if x.cmd == "withdraw":
        withdraw(x.id, x.q, x.new_fact); print(f"withdrew {x.id} {x.q}"); return 0
    if x.cmd == "outcome":
        outcome(x.id, x.q, x.happened == "yes"); print(f"{x.id} {x.q}: happened={x.happened}"); return 0
    if x.cmd == "weekly":
        print(json.dumps(weekly(x.date, write=x.write), indent=1, ensure_ascii=False, default=str)); return 0
    if x.cmd == "stats":
        out = stats()
        runlog.log(runlog.new_run_id(), "critic:stats", "ok", questions=out["questions"], changed=out["changed_decision"])
        print(json.dumps(out, indent=1, ensure_ascii=False)); return 0
    return 2
