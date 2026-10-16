"""Consensus and narrative monitor (agent 7): where attention, positioning and trend sit, and where each
open idea sits against them. Descriptive only - nothing here is a signal until it passes the quant gate.

Evidence behind each rule: docs/research/consensus.md. In short:
  - Attention = a narrative's share of all news GDELT monitored (Baker, Bloom & Davis; Bybee et al.), daily,
    read weekly (Heston & Sinha). Gap days (GDELT's total collapses) are dropped (Wang et al. 2016).
  - Stage from spread = ln(last 4 weeks / prior 26 weeks) and the level's percentile in its own history: spreading,
    peaking, fading, dormant, steady (Shiller's epidemic shape; Larsen & Thorsrud: waves last months).
  - Under 20 articles a day: "quiet" when the definition has proved it can see the topic (its 4-week average held the
    floor for 4 straight weeks and it had 28 single days at the floor), else "insufficient coverage" (NCHS keeps
    "unreliable" apart from "suppressed"; Kleinberg: a baseline state is normal for a topic stream).
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

import json
import math
import re
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
GDELT_URL = "https://www.gdeltproject.org/"
BQ_URL = "https://www.gdeltproject.org/data.html#googlebigquery"
# Series prefixes of the GDELT instruments. Never mixed inside one narrative's stage.
INSTRUMENTS = {"gdeltbq2": {"label": "GDELT GKG via BigQuery (v2 definition: title or URL-path words and GKG themes)",
                            "short": "GDELT GKG v2", "url": BQ_URL},
               "gdeltbqt": {"label": "GDELT GKG via BigQuery (title or URL-path match)", "short": "GDELT GKG",
                            "url": BQ_URL},
               "gdeltbq": {"label": "GDELT GKG via BigQuery (URL-path match)", "short": "GDELT GKG path", "url": BQ_URL},
               "gdelt": {"label": "GDELT DOC API (full-text match)", "short": "GDELT DOC", "url": GDELT_URL}}
STAGES = {"spreading", "peaking", "fading", "steady", "dormant", "quiet", "insufficient coverage"}   # computed stages
QUIET_RELABEL = "rule change: quiet stage added (16 Oct 2026)"   # tracker basis for insufficient coverage -> quiet
HEADLINE_SOURCE = "gdelt_headlines"


def cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "monitor.yaml").read_text(encoding="utf-8"))["consensus"]


def queries() -> list[dict]:
    """Active frozen narrative queries (retired ids keep their stored history but leave the map)."""
    src = yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))
    return [q for q in (src.get("gdelt") or {}).get("queries", []) if not q.get("retired")]


def instrument_queries() -> dict[str, dict[str, dict]]:
    """Instruments with their own frozen definitions (a gdelt_bq block with `queries:`): series prefix ->
    narrative id -> query ({id, query, ...}). Other instruments measure each narrative with its frozen DOC query,
    under the narrative's own id."""
    src = yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))
    out: dict[str, dict[str, dict]] = {}
    for b in src.values():
        if isinstance(b, dict) and b.get("adapter") == "gdelt_bq" and b.get("queries") is not None:
            out[str(b.get("series_prefix", "gdeltbq"))] = {q["narrative"]: q for q in b["queries"]
                                                           if q.get("narrative") and not q.get("retired")}
    return out


def query_id(prefix: str, nid: str, imap: dict | None = None) -> str | None:
    """The query that measures narrative `nid` on instrument `prefix` (None: that instrument does not cover it)."""
    imap = instrument_queries() if imap is None else imap
    if prefix in imap:
        q = imap[prefix].get(nid)
        return q["id"] if q else None
    return nid


def _daily(obs: pd.DataFrame, sid: str, asof: date) -> pd.Series:
    s = obs[(obs.series_id == sid) & (obs.date <= asof)][["date", "value"]]
    if s.empty:
        return pd.Series(dtype=float)
    return s.set_index(pd.to_datetime(s.date))["value"].astype(float).sort_index()


def _url(obs: pd.DataFrame, sid: str) -> str | None:
    s = obs[obs.series_id == sid]
    return s.source_url.iloc[-1] if len(s) else None


# ------------------------------------------------------------------ narratives
def valid_days(share: pd.Series, norm: pd.Series, asof: date, c: dict) -> pd.Series:
    """Share without gap days: days when GDELT's own total fell more than `gap_norm_drop` below the median of the
    same weekday over the last 4 weeks (outages, partial days) say nothing about attention (Wang et al. 2016).
    Same weekday because weekends carry ~0.55x a weekday's articles in the GKG: a plain 28-day median dropped
    ordinary weekends as gaps (first BigQuery run, 15 Oct)."""
    if share.empty:
        return share
    end = pd.Timestamp(asof)
    s = share[share.index <= end].dropna()
    if len(norm):
        n = norm[norm.index <= end].sort_index()
        med = n.groupby(n.index.dayofweek, group_keys=False).apply(
            lambda x: x.rolling(4, min_periods=2).median()).reindex(n.index)
        gap = n < (1 - c["gap_norm_drop"]) * med
        s = s[~s.index.isin(gap[gap].index)]
    return s


def floor_record(count: pd.Series, days: pd.Index, asof: date, c: dict) -> dict:
    """The definition's own record at the article floor, from data up to `asof` only (gap days dropped): the
    longest run of days its 4-week average held the floor, the single days at the floor, and the last day the
    4-week average was at the floor. A low reading counts as "quiet" only with both legs met: a run alone can be
    met by a few burst days (one 560-article day keeps a 4-week average at 20 for 28 days)."""
    floor, end = c["min_daily_articles"], pd.Timestamp(asof)
    k = count[(count.index <= end) & count.index.isin(days)].dropna()
    if k.empty:
        return {"floor_longest_run_days": 0, "floor_days": 0, "floor_last_met": None, "quiet_eligible": False}
    r = k.asfreq("D").rolling(c["level_days"], min_periods=int(0.7 * c["level_days"])).mean().dropna()
    ok = (r >= floor).to_numpy()
    best = run = 0
    for v in ok:
        run = run + 1 if v else 0
        best = max(best, run)
    met = r.index[ok]
    n_days = int((k >= floor).sum())
    return {"floor_longest_run_days": int(best), "floor_days": n_days,
            "floor_last_met": str(met[-1].date()) if len(met) else None,
            "quiet_eligible": bool(best >= c.get("quiet_min_run_days", 28) and n_days >= c.get("quiet_min_days", 28))}


def stage_of(share: pd.Series, count: pd.Series, norm: pd.Series, asof: date, c: dict) -> dict:
    """Stage and scores for one narrative with windows ending on `asof` (share in % of all monitored articles).
    Callers pass the last data date, not the pack date (data run a day behind), so each recompute differs by
    exactly one new data day (agent 7 review, finding 1)."""
    end = pd.Timestamp(asof)
    s = valid_days(share, norm, asof, c)
    if len(s) < c["min_history_days"]:
        return {"stage": "insufficient history", "days": int(len(s))}
    d = s.asfreq("D")
    lvl_win = d[(d.index > end - pd.Timedelta(days=c["level_days"])) & (d.index <= end)]
    base_win = d[(d.index > end - pd.Timedelta(days=c["level_days"] + c["base_days"])) &
                 (d.index <= end - pd.Timedelta(days=c["level_days"]))]
    lvl, base = float(lvl_win.mean()), float(base_win.mean())
    cnt = count[(count.index > end - pd.Timedelta(days=c["level_days"])) & (count.index <= end)]
    per_day = float(cnt.mean()) if len(cnt) else 0.0
    rec = floor_record(count, s.index, asof, c) if per_day < c["min_daily_articles"] else None
    low = None if rec is None else ("quiet" if rec.pop("quiet_eligible") else "insufficient coverage")
    if not (lvl > 0 and base > 0) or math.isnan(lvl) or math.isnan(base):
        return {"stage": low or "insufficient coverage", "articles_per_day": round(per_day, 1), **(rec or {}),
                "data_through": str(end.date())}
    spread = math.log(lvl / base)
    roll = d.rolling(c["level_days"], min_periods=int(0.7 * c["level_days"])).mean().dropna()
    x = roll.iloc[-1]
    pct = float(100 * ((roll < x).sum() + 0.5 * (roll == x).sum()) / len(roll))   # mid-rank: ties sit in the middle
    weeks = [float(d[(d.index > end - pd.Timedelta(days=7 * (k + 1))) & (d.index <= end - pd.Timedelta(days=7 * k))].mean())
             for k in range(8)][::-1]                       # oldest .. latest week ending on `asof`
    ups = sum(1 for a, b in zip(weeks[-4:-1], weeks[-3:]) if b > a)
    seen = [w for w in weeks if not math.isnan(w)]
    peak = max(seen) if seen else float("nan")
    drop = None if math.isnan(weeks[-1]) or not peak > 0 else 1 - weeks[-1] / peak
    if low:
        st = low                                    # under the floor: no spread-based stage, a low reading at most
    elif spread > c["spread_up"] and ups >= 2:
        st = "spreading"
    elif spread < c["spread_down"] or (drop is not None and drop > c["peak_drop"]):
        st = "fading"
    elif pct >= c["peaking_pct"]:
        st = "peaking"
    elif pct < c["dormant_pct"]:
        st = "dormant"
    else:
        st = "steady"
    return {"stage": st, "share_4w_pct": round(lvl, 4), "share_26w_pct": round(base, 4),
            "ratio_vs_26w": round(lvl / base, 2), "spread": round(spread, 2), "level_pctile": round(pct, 0),
            "weeks_up_of_3": ups, "below_8w_peak_pct": None if drop is None else round(100 * drop, 0),
            "articles_per_day": round(per_day, 1), **(rec or {}), "since": str(d.index[0].date()),
            "data_through": str(end.date())}


def tone_change(tone: pd.Series, asof: date, c: dict) -> float | None:
    if tone.empty:                    # tone call failed or not stored yet
        return None
    end = pd.Timestamp(asof)
    t = tone[tone.index <= end]
    last = t[t.index > end - pd.Timedelta(days=c["level_days"])]
    prior = t[(t.index <= end - pd.Timedelta(days=c["level_days"])) &
              (t.index > end - pd.Timedelta(days=c["level_days"] + c["base_days"]))]
    if len(last) < 10 or len(prior) < 60 or prior.std() == 0:
        return None
    return round(float((last.mean() - prior.mean()) / prior.std()), 1)


def subject_words(names: list[str]) -> dict[str, str]:
    """Words only this narrative's name has (plus singular/plural), so the auditor binds a figure to the right
    narrative: "Oil glut ... 4.29x" must not match Hormuz's 4.29x through the shared word "oil" (review finding 5)."""
    rx = re.compile(r"[a-z][a-z0-9&]{2,}")
    toks = {n: set(rx.findall(n.lower())) - {"narrative", "story", "news", "validation", "replica", "price", "prices"} for n in names}
    out = {}
    for n, ws in toks.items():
        others = set().union(*[t for m, t in toks.items() if m != n]) if len(toks) > 1 else set()
        own = {w for w in ws if w not in others and w.rstrip("s") not in {o.rstrip("s") for o in others}}
        own = own or ws
        out[n] = " ".join(sorted(own | {w[:-1] for w in own if w.endswith("s")} | {w + "s" for w in own if not w.endswith("s")}))
    return out


def previous_stages(briefs: Path | None, asof: date, max_age_days: int = 7) -> dict | None:
    """Stages the last earlier fact pack published (the alert compares against what he was last told)."""
    if briefs is None or not Path(briefs).exists():
        return None
    for p in sorted(Path(briefs).glob("*/facts.json"), reverse=True):
        try:
            d = date.fromisoformat(p.parent.name)
        except ValueError:
            continue
        if d >= asof:
            continue
        if (asof - d).days > max_age_days:
            return None
        try:
            nar = json.loads(p.read_text(encoding="utf-8"))["sections"]["consensus"]["narratives"]
        except Exception:  # noqa: BLE001  (pack without a consensus section)
            continue
        return {"date": str(d), "stages": {n["id"]: n.get("stage") for n in nar},
                "instruments": {n["id"]: n.get("instrument", "gdelt") for n in nar}}   # packs before BigQuery: DOC
    return None


def _assess(obs: pd.DataFrame, prefix: str, qid: str, asof: date, c: dict) -> dict:
    """Stage of one narrative on one instrument, plus the series behind it (for the tracker)."""
    sid = f"{prefix}:{qid}"
    norm = _daily(obs, f"{prefix}:norm", asof)
    share, count, tone = (_daily(obs, f"{sid}:share", asof).dropna(), _daily(obs, f"{sid}:count", asof),
                          _daily(obs, f"{sid}:tone", asof))
    good = valid_days(share, norm, asof, c)
    last = None
    if share.empty or good.empty:
        row, recomputed = {"stage": "no data"}, "no data"
    else:
        last = good.index[-1].date()                         # windows end on the last valid data day, not the pack date
        if (asof - last).days > c.get("stale_days", 4):
            row = {"stage": "stale", "data_through": str(last),
                   "note": "GDELT's coverage total collapsed or is missing since then (gap days are dropped)"}
            recomputed = "stale"
        else:
            row = stage_of(share, count, norm, last, c)
            recomputed = stage_of(share, count, norm, last - timedelta(days=1), c)["stage"]
    return {"prefix": prefix, "qid": qid, "row": row, "recomputed": recomputed, "last": last, "tone": tone,
            "good": good, "count": count, "url": _url(obs, f"{sid}:share")}


def _pick(cands: list[dict]) -> dict:
    """First instrument (in config order) with a computed stage; else one still building history; else one with
    any data; else the first. So the map moves to BigQuery as soon as its history is long enough."""
    for ok in (lambda a: a["row"]["stage"] in STAGES,
               lambda a: a["row"]["stage"] == "insufficient history",
               lambda a: a["row"]["stage"] != "no data"):
        for a in cands:
            if ok(a):
                return a
    return cands[0]


def headlines_for(txt: pd.DataFrame | None, qid: str, end: date, days: int = 7, k: int = 3) -> list[dict]:
    """Top headline links for a narrative in the `days` ending on `end`: most-carried titles first (syndication =
    prominence), then the newest. Title, source, URL and date only."""
    if txt is None or txt.empty or "item_id" not in txt:
        return []
    h = txt[(txt.source == HEADLINE_SOURCE) & txt.item_id.astype(str).str.startswith(f"{qid}|")].copy()
    if h.empty:
        return []
    h["d"] = pd.to_datetime(h.published, utc=True).dt.date
    h = h[(h.d <= end) & (h.d > end - timedelta(days=days))]
    if h.empty:
        return []
    summ = h.summary.fillna("").astype(str)
    h["copies"] = pd.to_numeric(summ.str.extract(r"copies=(\d+)")[0], errors="coerce").fillna(1).astype(int)
    h["src"] = summ.str.extract(r"src=([^;]*)")[0].fillna("").str.strip()
    h["k"] = h.title.astype(str).str.lower().str.strip()
    h = h.sort_values(["copies", "d"], ascending=[False, False]).drop_duplicates("k")
    return [{"date": str(r.d), "title": str(r.title), "url": str(r.url), "source": r.src or None,
             "copies": int(r.copies)} for r in h.head(k).itertuples()]


def narratives(obs: pd.DataFrame, asof: date, c: dict | None = None, prev_pack: dict | None = None,
               txt: pd.DataFrame | None = None, series_out: dict | None = None) -> list[dict]:
    c = c or cfg()
    order = [p for p in c.get("instruments", ["gdeltbqt", "gdeltbq", "gdelt"]) if p in INSTRUMENTS]
    imap = instrument_queries()
    qs = queries()
    subj = subject_words([q["name"] for q in qs])
    out = []
    for q in qs:
        cands = [_assess(obs, p, qid, asof, c) for p in order if (qid := query_id(p, q["id"], imap))]
        a = _pick(cands or [_assess(obs, order[0], q["id"], asof, c)])
        row, last, inst = a["row"], a["last"], a["prefix"]
        if series_out is not None:
            series_out[q["id"]] = a
        same = prev_pack and q["id"] in prev_pack["stages"] and prev_pack["instruments"].get(q["id"]) == inst
        if same:
            prev, basis = prev_pack["stages"][q["id"]], f"pack {prev_pack['date']}"
        else:                    # no earlier pack, or it read another instrument: compare like with like
            prev, basis = a["recomputed"], "one data day earlier"
        end = last or asof
        out.append({"id": q["id"], "name": q["name"], "audit_subject": subj.get(q["name"], q["name"]),
                    "markets": q.get("markets") or {}, "validation_only": bool(q.get("validation")), **row,
                    "stage_prev": prev, "stage_prev_basis": basis,
                    "tone_change_sd": tone_change(a["tone"], last, c) if row.get("share_4w_pct") is not None else None,
                    "validated": False, "instrument": inst, "instrument_label": INSTRUMENTS[inst]["label"],
                    "query_id": a["qid"],
                    "headlines": headlines_for(txt, a["qid"], end, int(c.get("headline_window_days", 7)),
                                               int(c.get("headlines_per_narrative", 3))),
                    "source_url": a["url"] or INSTRUMENTS[inst]["url"]})
    return out


# ------------------------------------------------------------------ narrative tracker
def _stage_path(a: dict, start: date, end: date, c: dict) -> list[tuple[date, str]]:
    """Stage on each data day from `start` to `end` (gap days already dropped from a["good"])."""
    empty = pd.Series(dtype=float)
    out = []
    for d in pd.date_range(start, end, freq="D"):
        if d not in a["good"].index:
            continue
        out.append((d.date(), stage_of(a["good"], a["count"], empty, d.date(), c)["stage"]))
    return out


def reconstruct(a: dict, c: dict) -> dict:
    """A narrative's recent stage history from its stored series: the changes in the last `tracker_rebuild_days`
    and the date the current stage began (or 'at least since' the window start when it never changed)."""
    end = a["last"]
    start = end - timedelta(days=int(c.get("tracker_rebuild_days", 180)))
    path = [(d, s) for d, s in _stage_path(a, start, end, c) if s in STAGES]
    changes, cur, since = [], None, None
    for d, s in path:
        if s != cur:
            if cur is not None:
                changes.append({"date": str(d), "from": cur, "to": s, "basis": "reconstructed"})
            cur, since = s, d
    first = path[0][0] if path else end
    return {"stage": cur, "since": str(since) if since else None,
            "since_basis": "reconstructed" if changes else f"at least since {first} (no change in the window)",
            "changes": changes}


def update_tracker(nar: list[dict], series: dict, asof: date, path: Path, c: dict) -> dict:
    """One running record per narrative (stage, since when, share, links, every change and what came with it),
    in data/narratives/tracker.json. Changes are dated by the data day; the pack that first showed them is kept.
    A pack built for an earlier date than the last one reads the tracker but never rewrites it."""
    try:
        tr = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        tr = {"narratives": {}}
    write = str(asof) >= tr.get("last_pack", "")
    keep = int(c.get("tracker_keep_changes", 40))
    for n in nar:
        if n["validation_only"]:
            continue
        rec = tr["narratives"].get(n["id"])
        computed = n["stage"] in STAGES
        if write and (rec is None or rec.get("instrument") != n["instrument"]
                      or rec.get("query_id", n["id"]) != n.get("query_id", n["id"])):
            base_rec = {"id": n["id"], "name": n["name"], "instrument": n["instrument"],
                        "query_id": n.get("query_id", n["id"]), "stage": None,
                        "since": None, "since_basis": None, "changes": []}
            if computed and series.get(n["id"]) and series[n["id"]]["last"]:
                base_rec.update(reconstruct(series[n["id"]], c))
            rec = base_rec
        if rec is None:
            continue
        if write and computed:
            if rec.get("stage") == "insufficient coverage" and n["stage"] == "quiet":
                # Only the rule moved it (a definition reaches quiet from a measured stage, never from insufficient
                # coverage): restate since from the stored series, log the relabel, not an observed change.
                r = reconstruct(series[n["id"]], c) if series.get(n["id"]) and series[n["id"]]["last"] else {}
                rec["changes"].append({"date": n.get("data_through"), "from": rec.get("stage"), "to": "quiet",
                                       "basis": QUIET_RELABEL, "first_pack": str(asof)})
                rec.update(stage="quiet", since=r.get("since") if r.get("stage") == "quiet" else rec.get("since"),
                           since_basis=r.get("since_basis") if r.get("stage") == "quiet" else rec.get("since_basis"))
            elif rec.get("stage") != n["stage"]:
                rec["changes"].append({"date": n.get("data_through"), "from": rec.get("stage"), "to": n["stage"],
                                       "basis": "observed", "first_pack": str(asof),
                                       "share_4w_pct": n.get("share_4w_pct"), "ratio_vs_26w": n.get("ratio_vs_26w"),
                                       "headlines": n.get("headlines") or []})
                rec.update(stage=n["stage"], since=n.get("data_through"), since_basis="observed")
            rec.update(share_4w_pct=n.get("share_4w_pct"), ratio_vs_26w=n.get("ratio_vs_26w"),
                       data_through=n.get("data_through"), headlines=n.get("headlines") or rec.get("headlines", []))
        if write:
            rec["changes"] = rec["changes"][-keep:]
            rec.update(name=n["name"], shown_as=n["stage"], last_pack=str(asof))
            tr["narratives"][n["id"]] = rec
        # what the pack says about it
        if rec.get("stage") == n["stage"] and computed:
            n["stage_since"], n["stage_since_basis"] = rec.get("since"), rec.get("since_basis")
            moved = [ch for ch in rec["changes"] if ch.get("to") == n["stage"]]
            if moved:
                ch = moved[-1]
                n["last_change"] = {k: ch.get(k) for k in ("date", "from", "to", "basis", "ratio_vs_26w")}
    if write:
        tr["last_pack"] = str(asof)
        tr["note"] = ("Narrative tracker (agent 7): stage, since when, and each change with the headlines seen then. "
                      "Descriptive; every narrative unvalidated until the GPR/EPU check and a 20-30 headline audit.")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(tr, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    return tr


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
    # logic uses the integer vote; the score is rounded for display only (review finding 2)
    return {"score": round(sum(signs) / len(signs), 2), "vote": int(sum(signs)), "legs_used": len(signs),
            "strength": round(float(np.mean(strength)), 2) if strength else None, "legs": legs,
            "last": round(float(p.iloc[-1]), 4), "last_date": str(p.index[-1].date()), "source_url": _url(obs, sid)}


def positioning(obs: pd.DataFrame, code: str | None, asof: date, lookback: int = 156, lag: int = 3) -> dict | None:
    """Managed-money percentile from reports already published by `asof`: Tuesday data count from their Friday
    release (`lag` days later), as in risk.py, so a rebuilt pack never uses a report that was not out yet."""
    if not code:
        return None
    s = _daily(obs, f"{code}.mm_net_pct_oi", asof - timedelta(days=lag)).dropna()
    if len(s) < 52:
        return None
    v = s.tail(lookback)
    chg = float(v.iloc[-1] - v.iloc[-2]) if len(v) > 1 else 0.0
    return {"pct_3y": round(float(100 * (v <= v.iloc[-1]).mean()), 0), "net_pct_oi": round(float(v.iloc[-1]), 1),
            "wow_change_pp": round(chg, 1), "date": str(v.index[-1].date()), "code": code,
            "source_url": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"}


def _dir(tr: dict | None) -> int:
    """Trend direction from the vote of the legs (2 of 3 legs up = up); never from the rounded score."""
    if not tr:
        return 0
    v = tr.get("vote")
    v = tr.get("score") or 0 if v is None else v
    return 1 if v > 0 else -1 if v < 0 else 0


def _label(tr: dict | None, pos: dict | None, linked: list[dict], c: dict) -> str:
    d = _dir(tr)
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
    if d == 0 and mid and not any(n["stage"] in hot for n in linked):
        return "quiet"
    return "mixed"


def markets(obs: pd.DataFrame, nar: list[dict], refs: set[str], names: dict[str, str], cftc_map: dict,
            asof: date, c: dict) -> list[dict]:
    keys = sorted(refs | {m for n in nar if not n["validation_only"] for m in n["markets"]})
    out = []
    for m in keys:
        tr = trend(obs, m, asof, c)
        pos = positioning(obs, cftc_map.get(m), asof, lag=int(c.get("cftc_release_lag_days", 3)))
        linked = [{"id": n["id"], "name": n["name"], "stage": n["stage"], "sign": int(n["markets"][m])}
                  for n in nar if m in n["markets"] and not n["validation_only"]]
        agree = None
        if pos and _dir(tr):
            agree = (_dir(tr) > 0) == (pos["pct_3y"] >= 50)
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
        t = _dir(r["trend"]) * d
        vs_trend = "with" if t > 0 else "against" if t < 0 else "flat"
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


# ------------------------------------------------------------------ CLI: tracker, headlines, headline audit
AUDIT_DIR = ROOT / "docs" / "research" / "narrative-audit"


def _tracker_path() -> Path:
    from . import store
    return store.DATA / "narratives" / "tracker.json"


def _headline_table() -> pd.DataFrame:
    from . import store
    p = store.DATA / "text" / f"{HEADLINE_SOURCE}.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame(columns=["source", "item_id", "title", "url", "published", "summary"])


def audit_sample(qid: str, n: int = 25, seed: int = 0) -> list[dict]:
    """Headlines for the 20-30 headline audit (Gentzkow et al.; the GPR/EPU validation step): spread evenly over
    every stored day, then a fixed-seed draw, so the sample is reproducible and not just the latest news."""
    h = _headline_table()
    h = h[h.item_id.astype(str).str.startswith(f"{qid}|")].copy()
    if h.empty:
        return []
    h["d"] = pd.to_datetime(h.published, utc=True).dt.date
    h["src"] = h.summary.fillna("").astype(str).str.extract(r"src=([^;]*)")[0].fillna("").str.strip()
    h["k"] = h.title.astype(str).str.lower().str.strip()
    h = h.sort_values(["d", "item_id"]).drop_duplicates("k")
    days = sorted(h.d.unique())
    rs = np.random.default_rng(seed)
    per_day = {d: h[h.d == d].sample(frac=1, random_state=int(rs.integers(1 << 30))) for d in days}
    out, k = [], 0
    while len(out) < n and any(len(v) > k for v in per_day.values()):
        for d in days:
            if len(per_day[d]) > k and len(out) < n:
                r = per_day[d].iloc[k]
                out.append({"date": str(d), "source": r.src, "title": str(r.title), "url": str(r.url)})
        k += 1
    return sorted(out, key=lambda r: r["date"])


def resolve(any_id: str) -> dict | None:
    """Narrative id or query id -> {narrative, query_id, query, name}. A narrative id resolves to the query the map
    reads it with now (its tracker record), else its frozen DOC query."""
    nar = {q["id"]: q for q in queries()}
    defs = {q["id"]: q for m in instrument_queries().values() for q in m.values()}
    if any_id in defs:
        q = defs[any_id]
        return {"narrative": q["narrative"], "query_id": any_id, "query": q["query"],
                "name": nar.get(q["narrative"], {}).get("name", q["narrative"])}
    if any_id not in nar:
        return None
    try:
        rec = json.loads(_tracker_path().read_text(encoding="utf-8"))["narratives"].get(any_id) or {}
    except (OSError, ValueError, KeyError):
        rec = {}
    qid = rec.get("query_id") or any_id
    q = defs.get(qid) or nar[any_id]
    return {"narrative": any_id, "query_id": qid, "query": q.get("bq_query") or q["query"], "name": nar[any_id]["name"]}


def write_audit(qid: str, n: int = 25, force: bool = False) -> Path:
    r = resolve(qid)
    if r is None:
        raise SystemExit(f"unknown narrative or query id {qid}")
    qid, q = r["query_id"], {"name": r["name"], "query": r["query"]}
    p = AUDIT_DIR / f"{qid}.md"
    if p.exists() and not force:
        raise SystemExit(f"{p} exists (it may hold marks); use --force to redraw")
    rows = audit_sample(qid, n)
    if not rows:
        raise SystemExit(f"no headlines stored for {qid} yet (they arrive with the BigQuery fetch)")
    L = [f"# Headline audit: {q['name']} (`{qid}`)", "",
         f"Query: `{q.get('bq_query') or q['query']}`", "",
         "Mark each headline: `y` = it is about this narrative, `n` = it is not (false match). "
         "Then run `python -m pmstack narratives audit-score " + qid + "`. Titles and links only (GDELT).", "",
         "| # | Date | Source | Headline | About it? (y/n) |", "|---:|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        t = r["title"].replace("|", "/").replace("[", "(").replace("]", ")")
        L.append(f"| {i} | {r['date']} | {r['source'] or '?'} | [{t}]({r['url']}) |  |")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    return p


def score_audit(qid: str) -> dict:
    """Share of audited headlines that are really about the narrative; stored in the tracker record."""
    r = resolve(qid) or {"narrative": qid, "query_id": qid}
    p = AUDIT_DIR / f"{r['query_id']}.md"
    marks = re.findall(r"^\|\s*\d+\s*\|.*\|\s*([yYnN]?)\s*\|\s*$", p.read_text(encoding="utf-8"), re.M)
    y, nn = sum(m.lower() == "y" for m in marks), sum(m.lower() == "n" for m in marks)
    res = {"file": f"docs/research/narrative-audit/{p.name}", "headlines": len(marks), "marked": y + nn, "about_it": y,
           "precision": round(y / (y + nn), 2) if y + nn else None, "query_id": r["query_id"]}
    tp = _tracker_path()
    try:
        tr = json.loads(tp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        tr = {"narratives": {}}
    tr["narratives"].setdefault(r["narrative"], {"id": r["narrative"], "changes": []})["headline_audit"] = res
    tp.parent.mkdir(parents=True, exist_ok=True)
    tp.write_text(json.dumps(tr, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    return res


def cli(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="pmstack narratives")
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tracker", help="each narrative: stage, since when, last change and its headlines")
    t.add_argument("--changed-since", help="only narratives that changed stage on or after this data day")
    t.add_argument("--json", action="store_true")
    h = sub.add_parser("headlines", help="top stored headline links for one narrative")
    h.add_argument("qid")
    h.add_argument("--date", help="window end (default: newest stored day)")
    h.add_argument("--days", type=int, default=7)
    h.add_argument("-k", type=int, default=10)
    a = sub.add_parser("audit", help="draw the 20-30 headline audit sheet (docs/research/narrative-audit/<id>.md)")
    a.add_argument("qid")
    a.add_argument("--n", type=int, default=25)
    a.add_argument("--force", action="store_true")
    s = sub.add_parser("audit-score", help="score a marked audit sheet into the tracker")
    s.add_argument("qid")
    m = sub.add_parser("measure", help="measure candidate definitions on BigQuery (GitHub Actions only)")
    m.add_argument("spec", help="YAML spec (docs/research/narrative-measure/<date>-spec.yaml)")
    m.add_argument("--out", required=True, help="JSON result path (a .md summary is written beside it)")
    m.add_argument("--max-gb", type=float, default=60.0, help="byte cap for this run (the monthly cap still holds)")
    x = ap.parse_args(argv)
    if x.cmd == "tracker":
        try:
            tr = json.loads(_tracker_path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            print("no tracker yet (it is written with the first fact pack)")
            return 0
        recs = list(tr.get("narratives", {}).values())
        if x.changed_since:
            recs = [r for r in recs if any((ch.get("date") or "") >= x.changed_since and ch.get("basis") != QUIET_RELABEL
                                           for ch in r.get("changes", []))]   # a relabel is not a move
        if x.json:
            print(json.dumps(recs, indent=1, ensure_ascii=False, default=str))
            return 0
        for r in sorted(recs, key=lambda r: r.get("name", r["id"])):
            last = (r.get("changes") or [{}])[-1]
            print(f"- {r.get('name', r['id'])} [{r.get('instrument', '-')}]: {r.get('stage') or r.get('shown_as')} since "
                  f"{r.get('since') or '-'} ({r.get('since_basis') or '-'}); shown as {r.get('shown_as', '-')}"
                  + (f"; last change {last.get('from')} -> {last.get('to')} on {last.get('date')}" if last else "")
                  + (f" ({last['basis']})" if last.get("basis") == QUIET_RELABEL else "")
                  + (f"; headline audit precision {r['headline_audit']['precision']}" if r.get("headline_audit") else ""))
            for hl in last.get("headlines", [])[:3]:
                print(f"    {hl['date']} [{hl['title']}]({hl['url']}) ({hl.get('source') or '?'})")
        return 0
    if x.cmd == "headlines":
        tb = _headline_table()
        if tb.empty:
            print("no headlines stored yet")
            return 0
        end = date.fromisoformat(x.date) if x.date else pd.to_datetime(tb.published, utc=True).dt.date.max()
        for hl in headlines_for(tb, x.qid, end, x.days, x.k):
            print(f"{hl['date']}  {hl['copies']:>3}x  {hl.get('source') or '?':<28} {hl['title']}  {hl['url']}")
        return 0
    if x.cmd == "audit":
        print(write_audit(x.qid, x.n, x.force))
        return 0
    if x.cmd == "audit-score":
        print(json.dumps(score_audit(x.qid), indent=1))
        return 0
    if x.cmd == "measure":
        from . import narrative_measure
        res = narrative_measure.run(x.spec, x.out, x.max_gb)
        print(f"measured: {res.get('bytes_gb')} GB (month {res.get('month_gb')} GB); errors: {res.get('errors') or 'none'}")
        return 0 if not res.get("errors") else 2
    return 1


# ------------------------------------------------------------------ the section
def build(obs: pd.DataFrame, txt: pd.DataFrame, entries: list[dict], names: dict[str, str], cftc_map: dict,
          asof: date, briefs: Path | None = None, tracker: Path | None = None) -> tuple[dict, list[dict]]:
    c = cfg()
    if obs.empty:
        return {"note": "no data"}, []
    prev = previous_stages(briefs, asof)
    series: dict = {}
    nar = narratives(obs, asof, c, prev, txt=txt, series_out=series)
    if tracker is not None:
        update_tracker(nar, series, asof, tracker, c)
    refs = {e.get("price_ref") for e in entries if e.get("status") in ("open", "idea") and e.get("price_ref")}
    mk = markets(obs, nar, refs, names, cftc_map, asof, c)
    sec = {"asof": str(asof), "previous_pack": prev["date"] if prev else None, "narratives": nar, "markets": mk, "ideas": ideas(entries, mk, c),
           "central_bank_terms": cb_terms(txt, asof, c),
           "captions": {"cftc": c["caption_cftc"], "trend": c["caption_trend"], "validation": c["unvalidated_note"],
                        "rule": "Descriptive only: no component is a signal until it passes the quant-research gate.",
                        "instruments": "Source column: GDELT GKG = BigQuery, phrases matched in each article's title or "
                                       "URL path (GKG path = URL path only); GDELT GKG v2 = BigQuery, the narrative's v2 "
                                       "definition (title or URL-path words and GDELT themes tagged from the full text); "
                                       "GDELT DOC = the DOC API, full text. Each narrative reads one source, never a mix.",
                        "gdelt": "News data: The GDELT Project, https://www.gdeltproject.org/"}}
    alerts = []
    for n in nar:
        if n["stage"] == "spreading" and n["stage_prev"] != "spreading" and not n["validation_only"]:
            alerts.append({"kind": "narrative_spreading", "severity": 2.0 + float(n.get("spread") or 0), "id": n["id"],
                           "audit_subject": n["audit_subject"],
                           "text": f"Narrative spreading: {n['name']}, {n['ratio_vs_26w']}x its prior-26-week share of "
                                   f"coverage ({n['share_4w_pct']}% of articles over 4 weeks; {n['articles_per_day']} a day; data through "
                                   f"{n['data_through']}; was {n['stage_prev']}; unvalidated)",
                           "source_url": n["source_url"]})
    return sec, alerts
