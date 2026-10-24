"""Trend and CTA levels (quant library). Reuses agent 8's `risk.cta_levels` (flip levels, roll-off, vol-target
scale) and adds what the tape card needs: which legs flipped since the previous close, and which are stretched
against their own history. Descriptive: trend-follower positioning is context, never a forecast (published trend
flow pressure is small and fades within weeks: docs/research/risk.md, Kang, Rouwenhorst & Tang)."""
from __future__ import annotations

import math
from datetime import date

import numpy as np
import pandas as pd

from .. import risk
from .common import cfg, pctile, r


def distances(p: pd.Series, h: int) -> pd.Series:
    """Log distance of each close to its h-day-ago reference, in daily sd (trailing 60-day, known the day before)."""
    lr = np.log(p).diff()
    sd = lr.rolling(60, min_periods=40).std().shift(1)
    return (np.log(p / p.shift(h)) / sd).dropna()


def state(p: pd.Series, asof: date, c: dict | None = None) -> dict | None:
    c = c or cfg()
    t = c["trend"]
    rc = risk.cfg()
    p = p[p.index <= pd.Timestamp(asof)].dropna()
    if len(p) < t["legs"][1] + 5:
        return None
    now = risk.cta_levels(p, rc, legs=tuple(t["legs"]))
    prev = risk.cta_levels(p.iloc[:-1], rc, legs=tuple(t["legs"])) if len(p) > t["legs"][1] + 6 else None
    if not now:
        return None
    out = {"last": now["last"], "last_date": now["last_date"], "daily_sd_pct": now["daily_sd_pct"], "state": now["state"],
           "vol_scale": now.get("vol_scale"), "panic": (now.get("panic") or {}).get("panic"), "legs": {}, "flipped": [], "stretched": []}
    for h in map(str, t["legs"]):
        leg = (now.get("legs") or {}).get(h)
        if not leg:
            continue
        d = distances(p, int(h))
        d = d[d.index >= pd.Timestamp(t.get("history_from", "2000-01-01"))]
        if not len(d):
            continue
        dist = float(d.iloc[-1])                                   # in daily sd (trailing 60-day): printed AND ranked
        pc = pctile(d, dist)
        before = ((prev or {}).get("legs") or {}).get(h, {}).get("sign")
        flipped = before is not None and leg["sign"] != before and leg["sign"] != 0
        scaled = dist / math.sqrt(int(h))                          # in h-day sd: comparable across legs
        stretched = (abs(scaled) >= t["stretched_sd"] and pc is not None
                     and (pc >= t["stretched_pctile"] or pc <= 100 - t["stretched_pctile"]))
        out["legs"][h] = {**leg, "distance_sd": r(dist, 1), "distance_hday_sd": r(scaled, 2), "distance_unit": "daily sd (trailing 60-day)",
                          "distance_pctile": r(pc, 0), "flipped": flipped, "stretched": stretched, "sign_prev": before}
        if flipped:
            out["flipped"].append(h)
        if stretched:
            out["stretched"].append(h)
    # changed against vol: today's and this week's move in trailing daily sd (sd known the day before)
    lr = np.log(p).diff()
    sd = lr.rolling(60, min_periods=40).std().shift(1)
    if len(p) > 6 and sd.iloc[-1] and np.isfinite(sd.iloc[-1]):
        z1 = float(lr.iloc[-1] / sd.iloc[-1])
        z5 = float(np.log(p.iloc[-1] / p.iloc[-6]) / (sd.iloc[-1] * math.sqrt(5)))
        out.update(z1d=r(z1, 1), z5d=r(z5, 1), big_move=bool(max(abs(z1), abs(z5)) >= t.get("big_move_z", 2.0)))
    out["base_rate"] = "not studied (print rule; /research registers it before any use)"
    return out
