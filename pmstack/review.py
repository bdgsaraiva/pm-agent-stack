"""Weekly review (agent 6): the process scorecard behind the Friday review page.

Code computes everything here; the model writes 5 lines of debrief and words one if-then goal from the
catalogue in config/review.yaml. Evidence behind each rule: docs/research/weekly-review.md. In short:
  - Process before outcome (Baron & Hershey; Lovallo & Sibony): plan followed, invalidation respected, size
    vs the sizing rule, P(win) written, critic answered, exits tagged. Targets are 100%, so misses are facts.
  - Small samples (Tversky & Kahneman; Brown, Cai & DasGupta; Efron & Morris): under 10 closed ideas,
    counts only; then Wilson intervals, shrunk estimates beside raw ones, mean R with a t-interval labelled
    optimistic plus the median; slices only at 20+ per group; no significance flags; no streak statistics.
    Calibration uses only the P(win) he wrote, never the sizing blend.
  - Leaks against his own baseline: days held past invalidation and horizon (Locke & Mann), tilt in both
    directions after a big close (Coval & Shumway; Liu et al.), new ideas vs his trailing median (Barber &
    Odean), exits by trigger and R after exit (Akepanidtaworn et al.).
  - One if-then goal, active from Monday unless he changes it, tracked by code and reported next Friday
    (Gollwitzer & Sheeran; Harkin et al.; Seijts & Latham; Dai, Milkman & Riis). A goal he set himself is
    never overwritten by the Friday proposal.
  - Monthly (first Friday after month end): alerts acted on by type (Zweig #7, descriptive only), a regime
    table (Zweig #8), post-mortems of the month's closed ideas (Zweig #10).
Windows: a review "week" is the 7 days ending at 18:00 BRT on the as-of date (the Friday run is 18:17), so
weekend and Friday-evening entries fall into the next review instead of no review.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import audit, critic, journal, runlog, sizing, store

ROOT = Path(__file__).resolve().parents[1]
BRT = timedelta(hours=-3)
CUTOFF_HOUR_BRT = 18


def _all_cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "review.yaml").read_text(encoding="utf-8"))


def cfg() -> dict:
    return _all_cfg()["review"]


def goals_path() -> Path:
    return journal.JOURNAL / "goals.yaml"


def _num(x):
    return journal._num(x)


def _ts(ts) -> pd.Timestamp:
    t = pd.Timestamp(ts)
    return t.tz_localize("UTC") if t.tzinfo is None else t


def _brt_date(ts) -> date | None:
    return (_ts(ts) + pd.Timedelta(hours=-3)).date() if ts else None


def _today() -> date:
    return (datetime.now(timezone.utc) + BRT).date()


def next_monday(d: date, include_today: bool = False) -> date:
    if include_today and d.weekday() == 0:
        return d
    return d + timedelta(days=(7 - d.weekday()) % 7 or 7)


@dataclass
class Window:
    """(start, end] in UTC; dates are BRT calendar days (start_d exclusive, end_d inclusive)."""
    start: pd.Timestamp
    end: pd.Timestamp

    def has(self, ts) -> bool:
        return bool(ts) and self.start < _ts(ts) <= self.end

    @property
    def start_d(self) -> date:
        return (self.start + pd.Timedelta(hours=-3)).date()

    @property
    def end_d(self) -> date:
        return (self.end + pd.Timedelta(hours=-3)).date()

    def has_d(self, d: date | None) -> bool:
        return d is not None and self.start_d < d <= self.end_d


def window(asof: date, weeks_back: int = 0) -> Window:
    end = pd.Timestamp(asof).tz_localize("UTC") + pd.Timedelta(hours=CUTOFF_HOUR_BRT + 3) - pd.Timedelta(days=7 * weeks_back)
    return Window(end - pd.Timedelta(days=7), end)


def _paper(entries: list[dict]) -> list[dict]:
    return [e for e in entries if e.get("book") != "example"]


def opened_ts(e: dict):
    """When the idea was actually taken: the 'open' event, else creation for ideas logged as open."""
    for ev in e.get("events", []):
        if ev.get("action") == "open":
            return ev["ts"]
    if e.get("status") in ("open", "closed"):
        return e.get("created_utc")
    return None


def _fills(entries: list[dict]) -> list[dict]:
    return sorted([e for e in entries if opened_ts(e)], key=lambda e: _ts(opened_ts(e)))


# ------------------------------------------------------------------ statistics
T975 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228, 2.201, 2.179, 2.160, 2.145, 2.131,
        2.120, 2.110, 2.101, 2.093, 2.086, 2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042]


def t975(df: int) -> float:
    """Student t 97.5% quantile (table to 30 df, then a close approximation)."""
    return T975[df - 1] if df <= 30 else 1.959964 + 2.4 / df


def wilson(x: int, n: int, z: float = 1.959964) -> tuple[float, float] | None:
    if n <= 0:
        return None
    p = x / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round((c - h) / d, 3), round((c + h) / d, 3)


def t_interval(xs: list[float]) -> tuple[float, float] | None:
    n = len(xs)
    if n < 2:
        return None
    m, s = float(np.mean(xs)), float(np.std(xs, ddof=1))
    h = t975(n - 1) * s / math.sqrt(n)
    return round(m - h, 2), round(m + h, 2)


def ideas_needed(edge_r: float, sd_r: float) -> int:
    """Closed ideas to tell a mean R of `edge_r` from 0 (two-sided 5%, 80% power, normal approximation)."""
    return int(math.ceil(((1.959964 + 0.841621) * sd_r / edge_r) ** 2))


def outcomes(closed: list[dict]) -> dict:
    """Outcome statistics, gated by sample size. Hit = R > 0 everywhere on the page."""
    c, sz = cfg(), sizing.cfg()
    rs = [float(e["r_multiple"]) for e in closed]
    n = len(rs)
    out = {"n_closed": n, "power_caption": f"At an R sd of {c['r_sd_assumed']}, telling a +0.25R edge from zero takes "
                                            f"about {ideas_needed(0.25, c['r_sd_assumed'])} closed ideas."}
    hits = sum(r > 0 for r in rs)
    out["counts"] = {"wins": hits, "losses": sum(r < 0 for r in rs), "flat": sum(r == 0 for r in rs),
                     "sum_r": round(sum(rs), 2)}
    if n < c["counts_only_below"]:
        out["mode"] = "counts-only"
        out["note"] = f"{n} closed paper ideas: too few to judge hit rate, R or calibration (needs {c['counts_only_below']})."
        return out
    out["mode"] = "intervals"
    prior = statistics.mean(float(sz["conviction_prior"][int(e.get("conviction") or 3)]) for e in closed)
    k = c["hit_shrink_k"]
    out["hit_rate"] = {"raw": round(hits / n, 3), "wilson95": wilson(hits, n),
                       "shrunk": round((hits + k * prior) / (n + k), 3), "prior": round(prior, 3), "k": k}
    m = float(np.mean(rs))
    out["mean_r"] = {"raw": round(m, 2), "t95_optimistic": t_interval(rs), "median": round(float(np.median(rs)), 2),
                     "shrunk": round(m * n / (n + c["r_prior_n0"]), 2), "sd": round(float(np.std(rs, ddof=1)), 2)}
    ci = out["mean_r"]["t95_optimistic"]
    out["mean_r"]["excludes_zero"] = bool(ci and (ci[0] > 0 or ci[1] < 0))
    # calibration: only the probability he wrote (the sizing blend would grade the code, not him)
    probs = [(float(e["prob_win"]), float(e["r_multiple"]) > 0) for e in closed if _num(e.get("prob_win")) is not None]
    out["prob_stated"] = {"n": len(probs), "of_closed": n}
    sq = [(p - y) ** 2 for p, y in probs]
    if len(sq) >= c["counts_only_below"]:
        b, se = float(np.mean(sq)), float(np.std(sq, ddof=1)) / math.sqrt(len(sq))
        out["brier"] = {"n": len(sq), "score": round(b, 3),
                        "ci95": (round(max(0.0, b - 1.96 * se), 3), round(min(1.0, b + 1.96 * se), 3)), "coin_flip": 0.25,
                        "note": ("fewer than 30 forecasts: no calibration claim (forecasts near 50% make this interval look "
                                 "tighter than skill warrants)") if len(sq) < c["slices_from"] else None}
    if n >= c["slices_from"]:
        out["mode"] = "slices"
        sl = {}
        for name, grp in (("conviction 4-5", [e for e in closed if int(e.get("conviction") or 0) >= 4]),
                          ("conviction 1-3", [e for e in closed if int(e.get("conviction") or 0) <= 3])):
            g = [float(e["r_multiple"]) for e in grp]
            sl[name] = ({"n": len(g), "hit_wilson95": wilson(sum(r > 0 for r in g), len(g)),
                         "mean_r": round(float(np.mean(g)), 2), "t95_optimistic": t_interval(g)}
                        if len(g) >= c["slice_min"] else {"n": len(g), "note": f"under {c['slice_min']}: not compared"})
        out["slices"] = sl
        bins = {"p<0.45": [], "0.45-0.60": [], "p>0.60": []}
        for p, y in probs:
            bins["p<0.45" if p < 0.45 else "0.45-0.60" if p <= 0.60 else "p>0.60"].append((p, y))
        out["calibration"] = {k_: ({"n": len(v), "mean_p": round(float(np.mean([a for a, _ in v])), 2),
                                    "hit": round(float(np.mean([b for _, b in v])), 2),
                                    "wilson95": wilson(sum(b for _, b in v), len(v))}
                                   if len(v) >= c["calib_bin_min"] else {"n": len(v), "note": "too few"})
                              for k_, v in bins.items()}
    if n >= c["per_level_from"]:
        out["mode"] = "per-level"
        out["per_level"] = {lvl: {"n": len(g), "mean_r": round(float(np.mean(g)), 2), "t95_optimistic": t_interval(g)}
                            for lvl in range(1, 6)
                            if len(g := [float(e["r_multiple"]) for e in closed if int(e.get("conviction") or 0) == lvl]) >= c["slice_min"]}
    return out


# ------------------------------------------------------------------ prices
def _prices(series_id: str | None) -> pd.DataFrame | None:
    if not series_id:
        return None
    try:
        df = store.connect().execute("SELECT date, value, source_url FROM obs WHERE series_id = ? ORDER BY date", [series_id]).df()
    except Exception:
        return None
    if df.empty:
        return None
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def _price_on(series_id: str | None, d: date) -> float | None:
    df = _prices(series_id)
    if df is None:
        return None
    w = df[df.date <= d]
    return float(w.value.iloc[-1]) if len(w) else None


def first_invalidation(e: dict, until: date) -> date | None:
    """First daily close at/through the invalidation after the idea was taken, up to its close (or `until`)."""
    inv, d, ot = _num(e.get("invalidation_price")), e.get("direction"), opened_ts(e)
    df = _prices(e.get("price_ref"))
    if inv is None or d not in ("long", "short") or df is None or not ot:
        return None
    if e.get("status") == "closed" and e.get("closed_utc"):
        until = min(until, _brt_date(e["closed_utc"]))
    w = df[(df.date >= _brt_date(ot)) & (df.date <= until)]
    hit = w[w.value <= inv] if d == "long" else w[w.value >= inv]
    return hit.date.iloc[0] if len(hit) else None


def _reunderwritten(e: dict, since: date) -> date | None:
    for ev in e.get("events", []):
        if "underwrit" in str(ev.get("reason", "")).lower() and _brt_date(ev["ts"]) >= since:
            return _brt_date(ev["ts"])
    return None


# ------------------------------------------------------------------ process block
def _critic_due(entries: list[dict], w: Window) -> dict:
    """Questions whose 48h deadline fell inside the window: answered in time or not. Others are pending."""
    hours = cfg()["critic_answer_hours"]
    due, ok, misses, pending = 0, 0, [], []
    for e in entries:
        for q in (e.get("critic") or {}).get("questions", []):
            if not q.get("asked_utc") or q.get("status") == "withdrawn":
                continue
            deadline = _ts(q["asked_utc"]) + pd.Timedelta(hours=hours)
            if w.start < deadline <= w.end:
                due += 1
                if q.get("answered_utc") and _ts(q["answered_utc"]) <= deadline:
                    ok += 1
                else:
                    misses.append(f"{e['id']}:{q['id']}")
            elif deadline > w.end and w.has(q["asked_utc"]) and not q.get("answered_utc"):
                pending.append(f"{e['id']}:{q['id']}")
    return {"n": due, "ok": ok, "misses": misses, "pending": pending}


def process(entries: list[dict], w: Window, asof: date) -> dict:
    c = cfg()
    lo_, hi_ = c["size_band"]
    new = [e for e in entries if w.has(e.get("created_utc")) and e.get("status") != "rejected"]
    closes = [e for e in entries if e.get("status") == "closed" and w.has(e.get("closed_utc"))]
    out = {"new_ideas": len(new), "rejected_logged": sum(1 for e in entries if w.has(e.get("rejected_utc"))),
           "closed": len(closes)}

    def share(items, ok):
        return {"n": len(items), "ok": sum(1 for x in items if ok(x)), "misses": [x["id"] for x in items if not ok(x)]}

    def by_rule(e):
        s, p = _num(e.get("size_suggested")), _num(e.get("size_planned"))
        return p == 0 if s == 0 else lo_ <= p / s <= hi_          # planning size against a "no edge" suggestion is a miss

    out["invalidation_written"] = share(new, lambda e: bool(e.get("invalidation_price") or e.get("invalidation")))
    out["prob_written"] = share(new, lambda e: e.get("prob_win") is not None)
    out["sized_by_rule"] = share([e for e in new if _num(e.get("size_suggested")) is not None
                                  and _num(e.get("size_planned")) is not None], by_rule)
    out["critic_answered_48h"] = _critic_due(entries, w)
    out["exits_tagged"] = share(closes, lambda e: bool(e.get("exit_trigger")) and bool(e.get("lesson")))
    past_inv, reund, past_hz = [], [], []
    for e in entries:
        if e.get("status") != "open":
            continue
        fi = first_invalidation(e, asof)
        if fi:
            r = _reunderwritten(e, fi)
            (reund if r else past_inv).append({"id": e["id"], "since": fi.isoformat(), "days": (asof - fi).days,
                                               **({"re_underwritten": r.isoformat()} if r else {})})
        hz = critic._horizon_date(e)
        if hz and hz < asof.isoformat():
            past_hz.append({"id": e["id"], "horizon": hz, "days": (asof - date.fromisoformat(hz)).days})
    out["held_past_invalidation"] = past_inv
    out["re_underwritten_after_invalidation"] = reund
    out["past_horizon"] = past_hz
    flags = [f for e in new for f in e.get("checks_at_entry", []) if str(f).startswith("flag:")]
    out["rule_flags_at_entry"] = {"n": len(flags), "by_rule": {r: flags.count(r) for r in sorted(set(flags))},
                                  "forced_blocks": sum(1 for e in new for f in e.get("checks_at_entry", []) if str(f).startswith("block:"))}
    return out


# ------------------------------------------------------------------ leaks
def weekly_fills(entries: list[dict], asof: date, weeks: int) -> list[int]:
    """Ideas taken in each of the `weeks` review windows before this one, from the first idea on."""
    fills = _fills(entries)
    if not fills:
        return []
    first = _ts(opened_ts(fills[0]))
    out = []
    for i in range(1, weeks + 1):
        w = window(asof, i)
        if w.end < first:
            break
        out.append(sum(1 for e in fills if w.has(opened_ts(e))))
    return out


def leaks(entries: list[dict], w: Window, asof: date) -> dict:
    c, tc = cfg(), cfg()["tilt"]
    out = {}
    fills = _fills(entries)
    tilt = {"window_days": tc["days"]}
    for side, test in (("after_loss", lambda r: r <= tc["loss_r"]), ("after_win", lambda r: r >= tc["win_r"])):
        closes, n_new, ratios = 0, 0, []
        for e in entries:
            r = _num(e.get("r_multiple"))
            if e.get("status") != "closed" or r is None or not test(r):
                continue
            closes += 1
            t0 = _ts(e["closed_utc"])
            before = [_num(o["size_planned"]) for o in fills if _ts(opened_ts(o)) <= t0 and _num(o.get("size_planned"))]
            base = statistics.median(before) if before else None
            nxt = [o for o in fills if t0 < _ts(opened_ts(o)) <= t0 + pd.Timedelta(days=tc["days"])]
            n_new += len(nxt)
            if base:
                ratios += [_num(o["size_planned"]) / base for o in nxt if _num(o.get("size_planned")) is not None]
        tilt[side] = {"closes": closes, "new_ideas_within": n_new,
                      "avg_size_vs_prior_median": round(float(np.mean(ratios)), 2) if ratios else None}
    if len(fills) >= 2:
        span = max(1.0, (_ts(opened_ts(fills[-1])) - _ts(opened_ts(fills[0]))).total_seconds() / 86400)
        tilt["baseline_new_ideas_per_window"] = round(len(fills) / span * tc["days"], 2)
    out["tilt"] = tilt
    prev = weekly_fills(entries, asof, c["overtrading_weeks"])
    out["new_ideas"] = {"this_week": sum(1 for e in fills if w.has(opened_ts(e))), "trailing_weeks": len(prev),
                        "trailing_median": statistics.median(prev) if prev else None}
    # realised this week: of ideas taken and alive in the window, winners vs losers closed (asof prices)
    wo = wc = lo = lc = 0
    for e in fills:
        if _ts(opened_ts(e)) > w.end:
            continue
        if e.get("status") == "closed":
            if not w.has(e.get("closed_utc")):
                continue
            r, closed_now = _num(e.get("r_multiple")), True
        elif e.get("status") == "open":
            px = _price_on(e.get("price_ref"), asof)
            r, closed_now = (journal.r_multiple(e, px) if px else None), False
        else:
            continue
        if r is None:
            continue
        if r > 0:
            wo += 1; wc += closed_now
        elif r < 0:
            lo += 1; lc += closed_now
    out["realised_this_week"] = {"winners": {"open_or_closed": wo, "closed": wc}, "losers": {"open_or_closed": lo, "closed": lc}}
    cl = [e for e in entries if e.get("status") == "closed" and _num(e.get("r_multiple")) is not None and e.get("holding_days") is not None]
    wins = [float(e["holding_days"]) for e in cl if float(e["r_multiple"]) > 0]
    loss = [float(e["holding_days"]) for e in cl if float(e["r_multiple"]) <= 0]
    hm = c["holding_min_each"]
    out["holding_days"] = ({"winners_median": round(statistics.median(wins), 1), "losers_median": round(statistics.median(loss), 1),
                            "n_winners": len(wins), "n_losers": len(loss)} if len(wins) >= hm and len(loss) >= hm else
                           {"n_winners": len(wins), "n_losers": len(loss), "note": f"medians shown once each has {hm}"})
    ex = {}
    now = pd.Timestamp.now(tz="UTC")
    for e in cl:
        t = e.get("exit_trigger") or "untagged"
        b = ex.setdefault(t, {"n_all_time": 0, "this_week": 0, "sum_r": 0.0, "_after": []})
        b["n_all_time"] += 1
        b["this_week"] += w.has(e.get("closed_utc"))
        b["sum_r"] = round(b["sum_r"] + float(e["r_multiple"]), 2)
        end = (_ts(e["created_utc"]) + pd.Timedelta(days=int(e["horizon_days"]))) if e.get("horizon_days") else \
            _ts(e["closed_utc"]) + pd.Timedelta(days=20)
        if end <= now:                                  # only complete after-exit windows
            a = sizing._r_after_exit(e)
            if a is not None:
                b["_after"].append(a)
    for b in ex.values():
        a = b.pop("_after")
        b["after_exit_n"] = len(a)
        b["avg_r_after_exit"] = round(float(np.mean(a)), 2) if a else None
    out["exits_by_trigger"] = ex
    return out


# ------------------------------------------------------------------ goals
def load_goals() -> list[dict]:
    p = goals_path()
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or []) if p.exists() else []


def save_goals(goals: list[dict]) -> None:
    p = goals_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(goals, sort_keys=False, allow_unicode=True, width=110), encoding="utf-8")


def active_goal(on: date) -> dict | None:
    live = [g for g in load_goals() if g.get("status") == "active" and date.fromisoformat(g["start"]) <= on
            and (not g.get("end") or date.fromisoformat(g["end"]) >= on)]
    return live[-1] if live else None


def pending_own_goal(after: date) -> dict | None:
    """A goal Bernardo set himself that starts after `after` (the Friday proposal must not overwrite it)."""
    own = [g for g in load_goals() if g.get("status") == "active" and g.get("set_by") != "review"
           and date.fromisoformat(g["start"]) > after]
    return own[-1] if own else None


def set_goal(key: str, start: date, text: str | None = None, source: str = "review") -> dict:
    cat = _all_cfg()["goals"]
    if key not in cat:
        raise SystemExit(f"goal must be one of: {', '.join(cat)}")
    if source == "review":
        own = pending_own_goal(start - timedelta(days=1))
        if own:
            return own                                   # his choice stands
    goals = load_goals()
    for g in goals:
        if g.get("status") != "active":
            continue
        if date.fromisoformat(g["start"]) >= start:
            g["status"] = "replaced"
        elif not g.get("end") or date.fromisoformat(g["end"]) >= start:
            g["end"] = (start - timedelta(days=1)).isoformat()
    g = {"key": key, "text": text or cat[key]["text"], "start": start.isoformat(), "status": "active",
         "set_by": source, "set_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    goals.append(g)
    save_goals(goals)
    runlog.log(runlog.new_run_id(), "review:goal", "ok", key=key, start=g["start"], set_by=source)
    return g


def drop_goal(on: date) -> None:
    goals = load_goals()
    for g in goals:
        if g.get("status") == "active" and (not g.get("end") or date.fromisoformat(g["end"]) >= on):
            if date.fromisoformat(g["start"]) > on:
                g["status"] = "dropped"
            else:
                g["end"] = on.isoformat()
    save_goals(goals)
    runlog.log(runlog.new_run_id(), "review:goal", "ok", dropped=True)


def goal_counts(key: str, entries: list[dict], asof: date, weeks: int = 1) -> dict:
    """Triggers met and honoured over the last `weeks` review windows (summed week by week)."""
    if weeks > 1:
        parts = [goal_counts(key, entries, asof - timedelta(days=7 * i)) for i in range(weeks)]
        if key == "log-ideas":
            return {"key": key, "triggers": None, "honoured": None, "ideas_logged": sum(p["ideas_logged"] for p in parts)}
        return {"key": key, "triggers": sum(p["triggers"] for p in parts), "honoured": sum(p["honoured"] for p in parts),
                "ids": [i for p in parts for i in p["ids"]]}
    c, tc = cfg(), cfg()["tilt"]
    w = window(asof)
    trig, ok, ids = 0, 0, []
    if key == "invalidation-same-day":
        for e in entries:
            if e.get("direction") not in ("long", "short") or not opened_ts(e):
                continue
            fi = first_invalidation(e, w.end_d)
            if not w.has_d(fi):
                continue
            trig += 1; ids.append(e["id"])
            closed_d = _brt_date(e.get("closed_utc")) if e.get("status") == "closed" else None
            r = _reunderwritten(e, fi)
            ok += bool((closed_d and closed_d <= fi + timedelta(days=1)) or (r and r <= fi + timedelta(days=1)))
    elif key == "after-loss-pause":
        fills = _fills(entries)
        for e in entries:
            if e.get("status") == "closed" and w.has(e.get("closed_utc")) and (_num(e.get("r_multiple")) or 0) <= tc["loss_r"]:
                trig += 1; ids.append(e["id"])
                t0 = _ts(e["closed_utc"])
                ok += not any(t0 < _ts(opened_ts(o)) <= t0 + pd.Timedelta(hours=24) for o in fills)
    elif key == "size-best-ideas":
        lo_ = c["size_band"][0]
        for e in entries:
            s, p = _num(e.get("size_suggested")), _num(e.get("size_planned"))
            if w.has(e.get("created_utc")) and int(e.get("conviction") or 0) >= 4 and s is not None and p is not None:
                trig += 1; ids.append(e["id"])
                ok += (p >= lo_ * s) or any("size" in str(ev.get("reason", "")).lower() for ev in e.get("events", []))
    elif key == "state-small-first":
        for e in entries:
            if w.has(e.get("created_utc")) and "flag:zweig-14" in e.get("checks_at_entry", []):
                trig += 1; ids.append(e["id"])
                s, p = _num(e.get("size_suggested")), _num(e.get("size_planned"))
                ok += bool(s is not None and p is not None and p <= 0.5 * s)
    elif key == "pace-new-ideas":
        prev = weekly_fills(entries, asof, c["overtrading_weeks"])
        base = int(statistics.median(prev)) if prev else None
        if base is not None:
            mine = [e for e in _fills(entries) if w.has(opened_ts(e))]
            for i, e in enumerate(mine):
                if i >= max(1, base):
                    trig += 1; ids.append(e["id"]); ok += int(e.get("conviction") or 0) >= 4
    elif key == "answer-critic-48h":
        p = _critic_due(entries, w)
        trig, ok, ids = p["n"], p["ok"], p["misses"]
    elif key in ("prob-before-entry", "tag-exits"):
        p = process(entries, w, asof)["prob_written" if key == "prob-before-entry" else "exits_tagged"]
        trig, ok, ids = p["n"], p["ok"], p["misses"]
    elif key == "log-ideas":
        n = sum(1 for e in entries if w.has(e.get("created_utc")))
        return {"key": key, "triggers": None, "honoured": None, "ideas_logged": n,
                "note": "the trigger (a view at conviction 3+) isn't observable; ideas logged (taken or passed) is the measure"}
    return {"key": key, "triggers": trig, "honoured": ok, "ids": ids}


def propose_goal(entries: list[dict], asof: date) -> dict:
    """Next week's goal. His own pending goal stands; else keep the current goal if its trigger came up fewer
    than 2 times in 2 weeks; else the catalogue item with the most misses over 4 weeks (ties: catalogue order);
    with no paper ideas, log-ideas."""
    own = pending_own_goal(asof)
    if own:
        return {"key": own["key"], "why": "you set it", "already_set": True}
    cat = list(_all_cfg()["goals"])
    if not _paper(entries):
        return {"key": "log-ideas", "why": "no paper ideas logged yet; the 1 Nov gate needs 10"}
    cur = active_goal(asof)
    if cur and cur["key"] != "log-ideas":
        g2 = goal_counts(cur["key"], entries, asof, weeks=2)
        if (g2.get("triggers") or 0) < 2:
            return {"key": cur["key"], "why": f"kept: its trigger came up {g2.get('triggers') or 0} time(s) in 2 weeks"}
    best, best_miss = None, 0
    for k in cat:
        if k == "log-ideas":
            continue
        g = goal_counts(k, entries, asof, weeks=4)
        miss = (g["triggers"] or 0) - (g["honoured"] or 0)
        if miss > best_miss:
            best, best_miss = k, miss
    if best:
        return {"key": best, "why": f"{best_miss} miss(es) in the last 4 weeks"}
    if cur:
        return {"key": cur["key"], "why": "no misses anywhere; current goal kept"}
    return {"key": "log-ideas", "why": "no misses anywhere; keep the journal filling"}


# ------------------------------------------------------------------ monthly
def first_friday_after_month_end(d: date) -> bool:
    return d.weekday() == 4 and d.day <= 7


def monthly(entries: list[dict], asof: date, briefs: Path | None = None) -> dict:
    c = cfg()
    briefs = audit._briefs(briefs)
    end = asof.replace(day=1) - timedelta(days=1)
    start = end.replace(day=1)
    in_m = lambda ts: bool(ts) and start <= _brt_date(ts) <= end  # noqa: E731
    kinds: dict[str, dict] = {}
    ref_kind = {}
    for d in sorted(p.name for p in briefs.glob("????-??-??")):
        if not (start.isoformat() <= d <= end.isoformat()):
            continue
        fj = briefs / d / "facts.json"
        if not fj.exists():
            continue
        for a in json.loads(fj.read_text(encoding="utf-8")).get("alerts", []):
            k = kinds.setdefault(a.get("kind", "?"), {"alerts": 0, "ideas": 0, "closed": 0, "sum_r": 0.0})
            k["alerts"] += 1
            ref_kind[a.get("ref")] = a.get("kind", "?")
    for e in _paper(entries):
        ref = e.get("source_ref") or ""
        if ref in ref_kind:
            k = kinds[ref_kind[ref]]
            k["ideas"] += 1
            if e.get("status") == "closed" and _num(e.get("r_multiple")) is not None:
                k["closed"] += 1
                k["sum_r"] = round(k["sum_r"] + float(e["r_multiple"]), 2)
    regime = []
    for sid in c["regime_series"]:
        df = _prices(sid)
        if df is None:
            continue
        df = df[df.date <= end]
        if len(df) < c["regime_vol_days"] + 70:
            continue
        lr = np.log(df.value.astype(float)).diff().dropna()
        vol = (lr.rolling(c["regime_vol_days"]).std() * math.sqrt(252) * 100).dropna().tail(c["regime_lookback_days"])
        if vol.empty:
            continue
        p = df.value.astype(float).to_numpy()
        prior = df[df.date < start]
        regime.append({"series": sid, "source_url": df.source_url.iloc[-1], "vol_21d_pct": round(float(vol.iloc[-1]), 1),
                       "vol_pctile": round(float(100 * (vol <= vol.iloc[-1]).mean()), 0),
                       "trend_63d_pct": round(float(100 * (p[-1] / p[-64] - 1)), 1) if len(p) > 64 else None,
                       "month_pct": round(float(100 * (p[-1] / float(prior.value.iloc[-1]) - 1)), 1) if len(prior) else None})
    pm = []
    for e in _paper(entries):
        if e.get("status") == "closed" and in_m(e.get("closed_utc")):
            te = [q["id"] for q in (e.get("critic") or {}).get("questions", []) if q.get("thesis_error")]
            pm.append({"id": e["id"], "market": e.get("market"), "r": _num(e.get("r_multiple")),
                       "process_score": e.get("process_score"), "exit_trigger": e.get("exit_trigger"),
                       "lesson": e.get("lesson"), "critic_thesis_error_answers": te})
    return {"month": start.strftime("%Y-%m"), "alerts_by_kind": kinds, "regime": regime,
            "policy_2y": critic.policy(end.isoformat()), "post_mortems": pm,
            "note": "Alert types are descriptive (acted on, R of ideas they led to); none is a signal until it passes the quant-research gate."}


# ------------------------------------------------------------------ the scorecard
def weekly(asof: date | None = None, entries: list[dict] | None = None, write: bool = False,
           briefs: Path | None = None, monthly_override: bool | None = None) -> dict:
    asof = asof or _today()
    all_entries = entries if entries is not None else journal.load_all()
    ents = _paper(all_entries)
    w = window(asof)
    c = cfg()
    closed_all = [e for e in ents if e.get("status") == "closed" and _num(e.get("r_multiple")) is not None]
    week_closed = [e for e in closed_all if w.has(e["closed_utc"])]
    week_r = round(sum(float(e["r_multiple"]) for e in week_closed), 2)
    goal = active_goal(asof)
    out = {
        "asof": asof.isoformat(), "window_utc": [str(w.start), str(w.end)],
        "computed_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "examples_excluded": sum(1 for e in all_entries if e.get("book") == "example"),
        "process": process(ents, w, asof),
        "leaks": leaks(ents, w, asof),
        "outcomes": outcomes(closed_all),
        "week_closes": [{"id": e["id"], "r": float(e["r_multiple"]), "exit_trigger": e.get("exit_trigger"),
                         "process_score": e.get("process_score")} for e in week_closed],
        "week_sum_r": week_r,
        "extreme_week": abs(week_r) >= c["extreme_week_r"],
        "sizing_review": sizing.review(ents),
        "critic": critic.stats(ents),
        "graveyard": journal.stats(ents).get("graveyard"),
        "gate_1nov": {"paper_ideas": len(ents), "needed": 10},
        "goal_last_week": ({**goal_counts(goal["key"], ents, asof), "text": goal["text"], "start": goal["start"]}
                           if goal else None),
    }
    prop = propose_goal(ents, asof)
    out["goal_next_week"] = {**prop, "text": _all_cfg()["goals"][prop["key"]]["text"],
                             "start": (pending_own_goal(asof) or {}).get("start") or next_monday(asof).isoformat()}
    if out["extreme_week"]:
        out["captions"] = ["Extreme weeks usually revert toward average: no process change on one week's outcome."]
    if monthly_override if monthly_override is not None else first_friday_after_month_end(asof):
        out["monthly"] = monthly(all_entries, asof, briefs)
    if write:
        d = audit._briefs(briefs) / asof.isoformat()
        d.mkdir(parents=True, exist_ok=True)
        (d / "review.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    runlog.log(runlog.new_run_id(), "review:weekly", "ok", asof=asof.isoformat(), closed=out["outcomes"]["n_closed"],
               mode=out["outcomes"]["mode"], new_ideas=out["process"]["new_ideas"], goal_next=prop["key"],
               monthly="monthly" in out, output=str(audit._briefs(briefs) / asof.isoformat() / "review.json") if write else None)
    return out


def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack review", description="Weekly review: process scorecard and the one goal")
    sub = p.add_subparsers(dest="cmd", required=True)
    wk = sub.add_parser("weekly"); wk.add_argument("--date"); wk.add_argument("--write", action="store_true")
    wk.add_argument("--monthly", action="store_true", help="force the monthly section")
    g = sub.add_parser("goal", help="show, set (from the catalogue), drop or list the weekly goal")
    g.add_argument("action", choices=("show", "set", "drop", "list"))
    g.add_argument("key", nargs="?"); g.add_argument("--start", help="YYYY-MM-DD (default: next Monday, or today if Monday)")
    g.add_argument("--text", help="your own wording of the catalogue goal"); g.add_argument("--by", default="bernardo")
    a = p.parse_args(argv)
    today = _today()
    if a.cmd == "weekly":
        d = date.fromisoformat(a.date) if a.date else today
        print(json.dumps(weekly(d, write=a.write, monthly_override=True if a.monthly else None),
                         indent=1, ensure_ascii=False, default=str))
        return 0
    if a.action == "list":
        print(json.dumps({k: v["text"] for k, v in _all_cfg()["goals"].items()}, indent=1, ensure_ascii=False)); return 0
    if a.action == "show":
        print(json.dumps({"active": active_goal(today), "next": pending_own_goal(today)}, indent=1, ensure_ascii=False)); return 0
    if a.action == "drop":
        drop_goal(today); print("goal dropped"); return 0
    if not a.key:
        raise SystemExit("goal set needs a key; `pmstack review goal list` shows them")
    start = date.fromisoformat(a.start) if a.start else next_monday(today, include_today=(a.by != "review"))
    print(json.dumps(set_goal(a.key, start, a.text, a.by), indent=1, ensure_ascii=False))
    return 0
