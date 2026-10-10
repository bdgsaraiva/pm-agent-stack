"""Sizing assistant (agent 4): turn conviction and payoff into a suggested size, and keep score of the
gap between what was suggested and what was taken. That gap is the under-sizing leak, measured.

Evidence behind each rule: docs/research/sizing.md. Method (all code, no model):
  p      = P(win). Prior by conviction (config), replaced by the PM's own hit rate per conviction, shrunk
           toward the prior, once enough ideas are closed. A probability the PM states is blended with
           that estimate, not used raw: stated probabilities are usually overconfident, and the optimal
           bet shrinks when p is uncertain (Baker & McHale 2013).
  b      = reward-to-risk = |target - entry| / |entry - invalidation|
  f*     = Kelly fraction = p - (1 - p) / b      (<= 0 means no edge on these numbers)
  units  = f* / f*(reference idea), so the reference idea (conviction 3, b = 2) earns 1.0 unit, the PM's
           normal risk. Kelly is used for *relative* size only: any real per-trade risk is far below even
           half Kelly, so the binding limits are the cap and the drawdown rule, not the Kelly level.
  cap    = max_units (2.0: Carver caps forecasts at 2x average; over-betting past Kelly destroys growth).
  overlap: directional 60-day return correlation with an open idea above the threshold cuts size,
           linearly to corr_floor at perfect overlap (Turtles, Grinold & Kahn breadth).
  drawdown: paper drawdown in R over the lookback (marked book: closed R + open marks, since agent 8) beyond the
           trigger halves every suggestion
           (Tudor Jones, Howard, Platt: cut size after losses; ergodicity: avoid the ruin path).
  steps  = rounded to 0.25 units; under 0.25 is "pass" (Lopez de Prado: discretise to avoid jitter).
  noise  = distance to invalidation in daily std devs; under min_stop_sd is flagged, because a stop inside
           the noise inflates any risk-based size. Volatility normalises risk; it is not a timing signal
           (Cederburg et al. 2020; Harvey et al. 2018: no Sharpe gain from vol targeting in commodities).
The suggestion is advice. The PM decides; the journal records both numbers.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import store

ROOT = Path(__file__).resolve().parents[1]


def cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "journal.yaml").read_text(encoding="utf-8"))["sizing"]


def _num(x):
    try:
        return None if x is None or x == "" else float(x)
    except (TypeError, ValueError):
        return None


def kelly(p: float, b: float) -> float:
    return p - (1 - p) / b


def _closed(entries: list[dict]) -> list[dict]:
    return [e for e in entries if e.get("status") == "closed" and e.get("book") != "example"
            and _num(e.get("r_multiple")) is not None]


def prob_for(conviction: int, entries: list[dict], c: dict | None = None) -> tuple[float, str]:
    c = c or cfg()
    prior = float(c["conviction_prior"][int(conviction)])
    closed = _closed(entries)
    if len(closed) < c["calibrate_after"]:
        return prior, f"prior for conviction {conviction} (calibrates after {c['calibrate_after']} closed ideas; {len(closed)} so far)"
    bucket = [e for e in closed if int(e.get("conviction") or 0) == int(conviction)]
    wins = sum(1 for e in bucket if float(e["r_multiple"]) > 0)
    k = c["shrink_k"]
    p = (wins + k * prior) / (len(bucket) + k)
    return round(p, 3), f"your hit rate at conviction {conviction}: {wins}/{len(bucket)}, shrunk toward prior {prior}"


def _returns(series_id: str, n: int) -> pd.Series | None:
    try:
        df = store.connect().execute(
            "SELECT date, value FROM obs WHERE series_id = ? ORDER BY date DESC LIMIT ?", [series_id, n + 1]).df()
    except Exception:
        return None
    if len(df) < max(20, n // 2):
        return None
    s = df.sort_values("date").set_index("date")["value"].astype(float)
    return np.log(s).diff().dropna()


def _dir(e: dict) -> int | None:
    return {"long": 1, "short": -1}.get(e.get("direction"))


def overlap(e: dict, others: list[dict], window: int) -> tuple[float | None, str | None]:
    """Highest directional return correlation between this idea and any open idea."""
    if not e.get("price_ref") or _dir(e) is None:
        return None, None
    r0 = _returns(e["price_ref"], window)
    if r0 is None:
        return None, None
    best, who = None, None
    for o in others:
        if o.get("status") != "open" or o.get("id") == e.get("id") or not o.get("price_ref") or _dir(o) is None:
            continue
        r1 = _returns(o["price_ref"], window)
        if r1 is None:
            continue
        j = pd.concat([r0, r1], axis=1, join="inner").dropna()
        if len(j) < 20:
            continue
        rho = float(j.iloc[:, 0].corr(j.iloc[:, 1])) * _dir(e) * _dir(o)
        if best is None or rho > best:
            best, who = rho, o["id"]
    return (round(best, 2) if best is not None else None), who


def stop_in_sd(e: dict, window: int) -> float | None:
    entry, inv = _num(e.get("entry_price")), _num(e.get("invalidation_price"))
    if None in (entry, inv) or not e.get("price_ref"):
        return None
    r = _returns(e["price_ref"], window)
    if r is None or r.std() == 0:
        return None
    return round(abs(entry - inv) / (entry * float(r.std(ddof=1))), 2)


def drawdown_r(entries: list[dict], now: datetime | None = None, lookback_days: int = 60) -> float:
    """Paper drawdown in R over the lookback, on the marked book (closed R + open ideas marked to the close on each
    day, size-weighted): today's level minus the highest level in the window. Since agent 8 (Bernardo, 10 Oct 2026)
    open losses count before they are closed; the risk section's red warning calls this same function."""
    from . import risk  # lazy: risk imports this module's config
    now = pd.Timestamp(now or datetime.now(timezone.utc))
    now = now.tz_localize("UTC") if now.tzinfo is None else now
    asof = now.tz_convert(risk.BRT).date()
    return risk.marked_drawdown(entries, asof, lookback_days, book="paper")


def _step(units: float, step: float) -> float:
    return round(round(units / step) * step, 2)


def suggest(e: dict, entries: list[dict], now: datetime | None = None) -> dict:
    c = cfg()
    out = {"units": None, "p": None, "p_source": None, "reward_risk": None, "kelly": None, "raw_units": None,
           "overlap_corr": None, "overlap_with": None, "drawdown_r": None, "stop_sd": None, "notes": []}
    conv = _num(e.get("conviction"))
    entry, tgt, inv = _num(e.get("entry_price")), _num(e.get("target")), _num(e.get("invalidation_price"))
    if None in (entry, tgt, inv) or entry == inv or _dir(e) is None:
        out["notes"].append("No size suggestion: needs a long/short idea with entry, target and invalidation prices.")
        return out
    others = [o for o in entries if o.get("id") != e.get("id")]
    b = abs(tgt - entry) / abs(entry - inv)
    p_rec, src = prob_for(int(conv or 3), others, c)
    p_given = _num(e.get("prob_win"))
    if p_given is not None and 0 < p_given < 1:
        w = c["prob_win_weight"]
        p = w * p_given + (1 - w) * p_rec
        src = f"{w:.0%} your probability {p_given:.2f} + {1 - w:.0%} {src}"
    else:
        p = p_rec
    f = kelly(p, b)
    ref = c["reference"]
    p_ref, _ = prob_for(int(ref["conviction"]), others, c)
    f_ref = kelly(p_ref, float(ref["reward_risk"]))
    out.update({"p": round(p, 3), "p_source": src, "reward_risk": round(b, 2), "kelly": round(f, 3)})
    out["stop_sd"] = sd = stop_in_sd(e, c["corr_window"])
    if sd is not None and sd < c["min_stop_sd"]:
        out["notes"].append(f"Invalidation is {sd:.1f} daily std devs away: inside the noise, so an ordinary day can stop you out.")
    if f <= 0:
        out["units"] = out["raw_units"] = 0.0
        out["notes"].append(f"No edge on these numbers: P(win) {p:.2f} at {b:.2f}:1 pays less than it risks. "
                            "Raise the target, move the invalidation, or pass.")
        return out
    units = f / f_ref if f_ref > 0 else 1.0
    if units > c["max_units"]:
        out["notes"].append(f"Capped at {c['max_units']:g} units (maths said {units:.2f}).")
        units = c["max_units"]
    rho, who = overlap(e, others, c["corr_window"])
    out["overlap_corr"], out["overlap_with"] = rho, who
    if rho is not None and rho > c["corr_threshold"]:
        cut = 1 - (1 - c["corr_floor"]) * (rho - c["corr_threshold"]) / (1 - c["corr_threshold"])
        units *= cut
        out["notes"].append(f"Cut to {cut:.0%} for overlap with {who} (directional correlation {rho:.2f}).")
    dd = c["drawdown"]
    out["drawdown_r"] = d = drawdown_r(others, now, dd["lookback_days"])
    if d <= -abs(dd["trigger_r"]):
        units *= dd["factor"]
        out["notes"].append(f"Paper drawdown {d:+.1f}R over {dd['lookback_days']} days (closed R + open marks): "
                            f"suggestion cut to {dd['factor']:.0%} until it recovers.")
    out["raw_units"] = round(units, 3)
    stepped = _step(units, c["step"])
    if stepped < c["min_units"]:
        out["units"] = 0.0
        out["notes"].append(f"Suggested size {units:.2f} is below the {c['min_units']:g}-unit minimum: pass, or improve the payoff.")
    else:
        out["units"] = stepped
    return out


def flags(e: dict) -> list[dict]:
    """Sizing checks for journal.checks, from the suggestion stored on the entry."""
    s, c, out = e.get("sizing") or {}, cfg(), []
    planned, sugg, conv = _num(e.get("size_planned")), _num(s.get("units")), _num(e.get("conviction"))
    if s.get("kelly") is not None and s["kelly"] <= 0:
        out.append({"level": "flag", "rule": "no-edge", "text": s["notes"][-1] if s.get("notes") else "No edge on these numbers."})
    if planned is not None and sugg:
        if conv is not None and conv >= 4 and planned < c["undersized_ratio"] * sugg:
            out.append({"level": "flag", "rule": "undersized-vs-suggestion",
                        "text": f"Conviction {int(conv)}: planned {planned:g} units vs suggested {sugg:g}. This is the leak you named; size it or say why not."})
        if planned > max(c["oversize_ratio"] * sugg, sugg + c["step"]) or planned > c["max_units"]:
            out.append({"level": "flag", "rule": "oversized",
                        "text": f"Planned {planned:g} units vs suggested {sugg:g} (cap {c['max_units']:g}). Past the optimum, growth falls while drawdowns grow."})
    if s.get("stop_sd") is not None and s["stop_sd"] < c["min_stop_sd"]:
        out.append({"level": "flag", "rule": "stop-in-noise",
                    "text": f"Invalidation is {s['stop_sd']:.1f} daily std devs away. Widen it and size down, or wait for a better entry."})
    if s.get("drawdown_r") is not None and s["drawdown_r"] <= -abs(c["drawdown"]["trigger_r"]):
        out.append({"level": "flag", "rule": "drawdown", "text": f"Paper drawdown {s['drawdown_r']:+.1f}R: sizes are halved until it recovers."})
    return out


def _r_after_exit(e: dict, days_default: int = 20) -> float | None:
    """R the idea would have shown at its horizon (or close + 20 days) minus the R realised. > 0: exited too early."""
    from .journal import r_multiple  # lazy: journal imports this module
    if not e.get("price_ref") or not e.get("closed_utc"):
        return None
    def ts(x):
        t = pd.Timestamp(x)
        return t.tz_localize("UTC") if t.tzinfo is None else t
    closed = ts(e["closed_utc"])
    end = ts(e["created_utc"]) + pd.Timedelta(days=int(e["horizon_days"])) if e.get("horizon_days") else \
        closed + pd.Timedelta(days=days_default)
    end = min(end, pd.Timestamp.now(tz="UTC"))
    if end <= closed:
        return None
    try:
        r = store.connect().execute("SELECT value FROM obs WHERE series_id = ? AND date <= ? ORDER BY date DESC LIMIT 1",
                                    [e["price_ref"], end.date()]).fetchone()
    except Exception:
        return None
    later = r_multiple(e, float(r[0])) if r else None
    return None if later is None else round(later - float(e["r_multiple"]), 2)


def review(entries: list[dict]) -> dict:
    """Sizing review (Friday / monthly): suggested vs planned by conviction, R left on the table,
    calibration (Brier) and exits (what closed ideas did after you left)."""
    c = cfg()
    rows = []
    for e in entries:
        if e.get("book") == "example":
            continue
        s = e.get("sizing") or {}
        closed = e.get("status") == "closed" and _num(e.get("r_multiple")) is not None
        rows.append({"id": e.get("id"), "conviction": e.get("conviction"), "suggested": _num(s.get("units")),
                     "planned": _num(e.get("size_planned")), "p": _num(s.get("p")),
                     "r": _num(e.get("r_multiple")) if closed else None,
                     "after_exit": _r_after_exit(e) if closed else None})
    df = pd.DataFrame(rows)
    if df.empty:
        return {"ideas": 0, "note": "No paper ideas yet."}
    out = {"ideas": int(len(df)), "closed": int(df.r.notna().sum()), "by_conviction": {}}
    for k, g in df.groupby("conviction"):
        cl = g.dropna(subset=["r"])
        out["by_conviction"][int(k)] = {
            "n": int(len(g)), "closed": int(len(cl)),
            "avg_suggested": None if g.suggested.isna().all() else round(float(g.suggested.mean()), 2),
            "avg_planned": None if g.planned.isna().all() else round(float(g.planned.mean()), 2),
            "hit_rate": None if cl.empty else round(float((cl.r > 0).mean()), 2),
            "prior_p": float(c["conviction_prior"][int(k)]),
            "avg_r": None if cl.empty else round(float(cl.r.mean()), 2)}
    both = df.dropna(subset=["suggested", "planned", "r"])
    out["r_left_on_table"] = round(float(((both.suggested - both.planned) * both.r).sum()), 2) if len(both) else None
    cal = df.dropna(subset=["p", "r"])
    if len(cal):
        o = (cal.r > 0).astype(float)
        out["brier"] = {"n": int(len(cal)), "score": round(float(((cal.p - o) ** 2).mean()), 3), "coin_flip": 0.25}
    ex = df.dropna(subset=["after_exit"])
    if len(ex):
        out["exits"] = {"n": int(len(ex)), "avg_r_after_exit": round(float(ex.after_exit.mean()), 2),
                        "share_left_early": round(float((ex.after_exit > 0).mean()), 2)}
    out["read_me"] = ("r_left_on_table = sum over closed ideas of (suggested - planned units) x R: positive means the "
                      "suggestion would have made more. brier: 0 is perfect, 0.25 is a coin flip. exits: avg R the idea "
                      "added after you closed it, to its horizon; positive means you sell too early.")
    return out
