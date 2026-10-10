"""Consensus and narrative monitor (agent 7): where attention, positioning and trend sit, and where each
open idea sits against them. Descriptive only - nothing here is a signal until it passes the quant gate.

Evidence behind each rule: docs/research/consensus.md. In short:
  - Attention = a narrative's share of all news GDELT monitored (Baker, Bloom & Davis; Bybee et al.), daily,
    read weekly (Heston & Sinha). Gap days (GDELT's total collapses) are dropped (Wang et al. 2016).
  - Stage from spread = ln(last 4 weeks / prior 26 weeks) and the level's percentile since 2017: spreading,
    peaking, fading, dormant, steady (Shiller's epidemic shape; Larsen & Thorsrud: waves last months).
  - Tone only as a change against the narrative's own history (Loughran & McDonald: general dictionaries
    misread "crude"; Calomiris & Mamaysky: the sign of tone flips by topic).
  - Trend-follower proxy = average sign of 1/3/12-month returns, plus a capped strength and flip levels
    (Hurst, Ooi & Pedersen; Baltas & Kosowski). CFTC managed money shown beside it with an agreement flag
    (Moskowitz et al.; Fishe & Smith: they mostly move together). Extremes = crowding context, not contrarian
    (Sanders, Irwin & Merrin: 5 of 30 tests).
  - Labels (self-reinforcing, twilight, crowded, quiet, mixed) follow Soros and Marks and are inference.
  - Every narrative is "unvalidated" until checked against GPR/EPU and a 20-30 headline audit (Gentzkow et al.).
"""
from __future__ import annotations

import math
import re
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
GDELT_URL = "https://www.gdeltproject.org/"


def cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "monitor.yaml").read_text(encoding="utf-8"))["consensus"]


def queries() -> list[dict]:
    src = yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))
    return (src.get("gdelt") or {}).get("queries", [])


def _daily(obs: pd.DataFrame, sid: str, asof: date) -> pd.Series:
    s = obs[(obs.series_id == sid) & (obs.date <= asof)][["date", "value"]]
    if s.empty:
        return pd.Series(dtype=float)
    return s.set_index(pd.to_datetime(s.date))["value"].astype(float).sort_index()


def _url(obs: pd.DataFrame, sid: str) -> str | None:
    s = obs[obs.series_id == sid]
    return s.source_url.iloc[-1] if len(s) else None


# ------------------------------------------------------------------ narratives
def stage_of(share: pd.Series, count: pd.Series, norm: pd.Series, asof: date, c: dict) -> dict:
    """Stage and scores for one narrative as of `asof` (share in % of all monitored articles)."""
    end = pd.Timestamp(asof)
    s = share[share.index <= end]
    if len(norm):
        n = norm[norm.index <= end]
        med = n.rolling(28, min_periods=7).median()
        gap = n < (1 - c["gap_norm_drop"]) * med
        s = s[~s.index.isin(gap[gap].index)]
    if len(s) < c["min_history_days"]:
        return {"stage": "insufficient history", "days": int(len(s))}
    d = s.asfreq("D")
    lvl_win = d[(d.index > end - pd.Timedelta(days=c["level_days"])) & (d.index <= end)]
    base_win = d[(d.index > end - pd.Timedelta(days=c["level_days"] + c["base_days"])) &
                 (d.index <= end - pd.Timedelta(days=c["level_days"]))]
    lvl, base = float(lvl_win.mean()), float(base_win.mean())
    cnt = count[(count.index > end - pd.Timedelta(days=c["level_days"])) & (count.index <= end)]
    per_day = float(cnt.mean()) if len(cnt) else 0.0
    if not (lvl > 0 and base > 0) or math.isnan(lvl) or math.isnan(base):
        return {"stage": "insufficient coverage", "articles_per_day": round(per_day, 1)}
    spread = math.log(lvl / base)
    roll = d.rolling(c["level_days"], min_periods=int(0.7 * c["level_days"])).mean().dropna()
    pct = float(100 * (roll <= roll.iloc[-1]).mean())
    weeks = [float(d[(d.index > end - pd.Timedelta(days=7 * (k + 1))) & (d.index <= end - pd.Timedelta(days=7 * k))].mean())
             for k in range(8)][::-1]                       # oldest .. latest week ending asof
    ups = sum(1 for a, b in zip(weeks[-4:-1], weeks[-3:]) if b > a)
    peak = max(w for w in weeks if not math.isnan(w))
    drop = 1 - weeks[-1] / peak if peak > 0 else 0.0
    if per_day < c["min_daily_articles"]:
        st = "insufficient coverage"
    elif spread > c["spread_up"] and ups >= 2:
        st = "spreading"
    elif spread < c["spread_down"] or drop > c["peak_drop"]:
        st = "fading"
    elif pct >= c["peaking_pct"]:
        st = "peaking"
    elif pct < c["dormant_pct"]:
        st = "dormant"
    else:
        st = "steady"
    return {"stage": st, "share_4w_pct": round(lvl, 4), "share_26w_pct": round(base, 4),
            "ratio_vs_26w": round(lvl / base, 2), "spread": round(spread, 2), "level_pctile": round(pct, 0),
            "weeks_up_of_3": ups, "below_8w_peak_pct": round(100 * drop, 0), "articles_per_day": round(per_day, 1),
            "since": str(d.index[0].date())}


def tone_change(tone: pd.Series, asof: date, c: dict) -> float | None:
    end = pd.Timestamp(asof)
    t = tone[tone.index <= end]
    last = t[t.index > end - pd.Timedelta(days=c["level_days"])]
    prior = t[(t.index <= end - pd.Timedelta(days=c["level_days"])) &
              (t.index > end - pd.Timedelta(days=c["level_days"] + c["base_days"]))]
    if len(last) < 10 or len(prior) < 60 or prior.std() == 0:
        return None
    return round(float((last.mean() - prior.mean()) / prior.std()), 1)


def narratives(obs: pd.DataFrame, asof: date, c: dict | None = None) -> list[dict]:
    c = c or cfg()
    norm = _daily(obs, "gdelt:norm", asof)
    out = []
    for q in queries():
        sid = f"gdelt:{q['id']}"
        share, count, tone = (_daily(obs, f"{sid}:share", asof), _daily(obs, f"{sid}:count", asof),
                              _daily(obs, f"{sid}:tone", asof))
        if share.empty:
            row = {"stage": "no data"}
            prev = "no data"
        else:
            row = stage_of(share, count, norm, asof, c)
            prev = stage_of(share, count, norm, asof - timedelta(days=1), c)["stage"]
        out.append({"id": q["id"], "name": q["name"], "markets": q.get("markets") or {},
                    "validation_only": bool(q.get("validation")), **row, "stage_yesterday": prev,
                    "tone_change_sd": tone_change(tone, asof, c) if not share.empty else None,
                    "validated": False, "source_url": _url(obs, f"{sid}:share") or GDELT_URL})
    return out


# ------------------------------------------------------------------ trend proxy and positioning
def trend(obs: pd.DataFrame, sid: str, asof: date, c: dict) -> dict | None:
    p = _daily(obs, sid, asof).dropna()
    if len(p) < c["trend_days"][1] + 2:
        return None
    lr = np.log(p).diff().dropna()
    sig = float(lr.ewm(span=c["vol_span"]).std().iloc[-1]) or None
    legs, signs, strength = {}, [], []
    for h in c["trend_days"]:
        if len(p) <= h:
            continue
        r = math.log(p.iloc[-1] / p.iloc[-1 - h])
        signs.append(1 if r > 0 else -1 if r < 0 else 0)
        if sig:
            strength.append(max(-1.0, min(1.0, r / (sig * math.sqrt(h)))))
        legs[str(h)] = {"ret_pct": round(100 * (math.exp(r) - 1), 1), "flip_level": round(float(p.iloc[-1 - h]), 4)}
    return {"score": round(sum(signs) / len(signs), 2), "legs_used": len(signs),
            "strength": round(float(np.mean(strength)), 2) if strength else None, "legs": legs,
            "last": round(float(p.iloc[-1]), 4), "last_date": str(p.index[-1].date()), "source_url": _url(obs, sid)}


def positioning(obs: pd.DataFrame, code: str | None, asof: date, lookback: int = 156) -> dict | None:
    if not code:
        return None
    s = _daily(obs, f"{code}.mm_net_pct_oi", asof).dropna()
    if len(s) < 52:
        return None
    v = s.tail(lookback)
    chg = float(v.iloc[-1] - v.iloc[-2]) if len(v) > 1 else 0.0
    return {"pct_3y": round(float(100 * (v <= v.iloc[-1]).mean()), 0), "net_pct_oi": round(float(v.iloc[-1]), 1),
            "wow_change_pp": round(chg, 1), "date": str(v.index[-1].date()), "code": code,
            "source_url": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"}


def _label(tr: dict | None, pos: dict | None, linked: list[dict], c: dict) -> str:
    score = (tr or {}).get("score", 0) or 0
    d = 1 if score >= 1 / 3 - 1e-9 else -1 if score <= -1 / 3 + 1e-9 else 0
    side = None if pos is None or d == 0 else (pos["pct_3y"] if d > 0 else 100 - pos["pct_3y"])
    same = [n for n in linked if n["sign"] == d and d != 0]
    hot = {"spreading", "peaking"}
    if side is not None and side >= c["crowded_pct"] and any(n["stage"] == "fading" for n in same) \
            and not any(n["stage"] == "spreading" for n in same):
        return "twilight"
    if d and any(n["stage"] == "spreading" for n in same) and side is not None and side >= c["leaning_pct"]:
        return "self-reinforcing"
    if side is not None and side >= c["crowded_pct"]:
        return "crowded"
    mid = pos is None or 100 - c["leaning_pct"] < pos["pct_3y"] < c["leaning_pct"]
    if abs(score) < 1 / 3 and mid and not any(n["stage"] in hot for n in linked):
        return "quiet"
    return "mixed"


def markets(obs: pd.DataFrame, nar: list[dict], refs: set[str], names: dict[str, str], cftc_map: dict,
            asof: date, c: dict) -> list[dict]:
    keys = sorted(refs | {m for n in nar if not n["validation_only"] for m in n["markets"]})
    out = []
    for m in keys:
        tr = trend(obs, m, asof, c)
        pos = positioning(obs, cftc_map.get(m), asof)
        linked = [{"id": n["id"], "name": n["name"], "stage": n["stage"], "sign": int(n["markets"][m])}
                  for n in nar if m in n["markets"] and not n["validation_only"]]
        agree = None
        if tr and pos and tr["score"]:
            agree = (tr["score"] > 0) == (pos["pct_3y"] >= 50)
        out.append({"market": m, "name": names.get(m, m), "trend": tr, "cftc": pos, "trend_mm_agree": agree,
                    "narratives": linked, "label": _label(tr, pos, linked, c), "label_is_inference": True})
    return out


def ideas(entries: list[dict], mk: list[dict], c: dict) -> list[dict]:
    by = {r["market"]: r for r in mk}
    out = []
    for e in entries:
        if e.get("status") not in ("open", "idea") or e.get("direction") not in ("long", "short"):
            continue
        r = by.get(e.get("price_ref") or "")
        if not r:
            continue
        d = 1 if e["direction"] == "long" else -1
        score = (r["trend"] or {}).get("score") or 0
        vs_trend = "with" if score * d >= 1 / 3 - 1e-9 else "against" if score * d <= -1 / 3 + 1e-9 else "flat"
        side = None if not r["cftc"] else (r["cftc"]["pct_3y"] if d > 0 else 100 - r["cftc"]["pct_3y"])
        hot = {"spreading", "peaking"}
        sup = [n["name"] for n in r["narratives"] if n["sign"] == d and n["stage"] in hot]
        opp = [n["name"] for n in r["narratives"] if n["sign"] == -d and n["stage"] in hot]
        if vs_trend == "with" and ((side or 0) >= c["leaning_pct"] or sup):
            place = "with the crowd"
        elif vs_trend == "against" and ((side is not None and side <= 100 - c["leaning_pct"]) or opp):
            place = "against the crowd"
        elif r["label"] == "quiet":
            place = "quiet"
        else:
            place = "mixed"
        out.append({"id": e["id"], "market": e.get("market"), "price_ref": e.get("price_ref"),
                    "direction": e["direction"], "book": e.get("book"), "vs_trend": vs_trend,
                    "cftc_pct_on_side": side, "narratives_with": sup, "narratives_against": opp,
                    "placement": place, "placement_is_inference": True})
    return out


# ------------------------------------------------------------------ central-bank text
def cb_terms(txt: pd.DataFrame, asof: date, c: dict) -> dict:
    if txt is None or txt.empty:
        return {"terms": [], "note": "no central-bank text stored"}
    t = txt[txt.source.isin(c["cb_sources"])].copy()
    t["published"] = pd.to_datetime(t["published"], utc=True, errors="coerce")
    end = pd.Timestamp(asof).tz_localize("UTC") + pd.Timedelta(days=1)
    t = t[t.published < end]
    if t.empty:
        return {"terms": [], "note": "no Fed releases stored"}
    first = t.published.min()
    recent = t[t.published >= end - pd.Timedelta(days=c["level_days"])]
    prior = t[(t.published < end - pd.Timedelta(days=c["level_days"])) &
              (t.published >= end - pd.Timedelta(days=c["level_days"] + c["base_days"]))]
    span_prior = max(1.0, min(c["base_days"], (end - pd.Timedelta(days=c["level_days"]) - first).days) / c["level_days"])
    rows = []
    for term in c["cb_terms"]:
        rx = re.compile(r"\b" + re.escape(term) + r"\b", re.I)
        n_r = int(sum(bool(rx.search(f"{a} {b}")) for a, b in zip(recent.title, recent.summary)))
        n_p = int(sum(bool(rx.search(f"{a} {b}")) for a, b in zip(prior.title, prior.summary)))
        rows.append({"term": term, "releases_4w": n_r, "per_4w_before": round(n_p / span_prior, 1)})
    hist_days = (end - first).days
    return {"terms": sorted(rows, key=lambda r: -r["releases_4w"]), "releases_4w": int(len(recent)),
            "history_days": int(hist_days),
            "note": None if hist_days >= c["level_days"] + c["base_days"] else
            f"only {hist_days} days of Fed releases stored: counts, no trend claims yet"}


# ------------------------------------------------------------------ the section
def build(obs: pd.DataFrame, txt: pd.DataFrame, entries: list[dict], names: dict[str, str], cftc_map: dict,
          asof: date) -> tuple[dict, list[dict]]:
    c = cfg()
    if obs.empty:
        return {"note": "no data"}, []
    nar = narratives(obs, asof, c)
    refs = {e.get("price_ref") for e in entries if e.get("status") in ("open", "idea") and e.get("price_ref")}
    mk = markets(obs, nar, refs, names, cftc_map, asof, c)
    sec = {"asof": str(asof), "narratives": nar, "markets": mk, "ideas": ideas(entries, mk, c),
           "central_bank_terms": cb_terms(txt, asof, c),
           "captions": {"cftc": c["caption_cftc"], "trend": c["caption_trend"], "validation": c["unvalidated_note"],
                        "rule": "Descriptive only: no component is a signal until it passes the quant-research gate.",
                        "gdelt": "News data: The GDELT Project, https://www.gdeltproject.org/"}}
    alerts = []
    for n in nar:
        if n["stage"] == "spreading" and n["stage_yesterday"] != "spreading" and not n["validation_only"]:
            alerts.append({"kind": "narrative_spreading", "severity": 2.0 + float(n.get("spread") or 0), "id": n["id"],
                           "text": f"Narrative spreading: {n['name']}, {n['ratio_vs_26w']}x its prior-26-week share of "
                                   f"coverage ({n['share_4w_pct']}% of articles over 4 weeks; {n['articles_per_day']} a day; unvalidated)",
                           "source_url": n["source_url"]})
    return sec, alerts
