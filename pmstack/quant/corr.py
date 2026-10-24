"""Correlation and regime (quant library): each market's rolling correlation with equities, the dollar and
Treasuries, against its own three-year range. Commodity-equity correlation moves with regimes (financialisation
and stress: Tang & Xiong 2012; Büyükşahin & Robe), so a reading outside the usual band is context for the book's
diversification, not a forecast. Agent 8 owns the book-level stress correlation (risk.py)."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from .common import cfg, pctile, r


def state(prices: dict[str, pd.Series], mid: str, asof: date, c: dict | None = None) -> dict | None:
    c = c or cfg()
    k = c["corr"]
    p = prices.get(mid)
    if p is None or len(p) < k["window"] + 40:
        return None
    out = {}
    pa = p[p.index <= pd.Timestamp(asof)]
    for v in k["vs"]:
        if v == mid or v not in prices or not len(prices[v]):
            continue
        pb = prices[v][prices[v].index <= pd.Timestamp(asof)]
        # join the closes first, then difference: a holiday in one market never pairs a 1-day with a 2-day return
        j = np.log(pd.concat([pa, pb], axis=1, join="inner")).diff().dropna()
        if len(j) < k["window"] + 20:
            continue
        rc = j.iloc[:, 0].rolling(k["window"]).corr(j.iloc[:, 1]).dropna()
        hist = rc.tail(k["lookback_days"])
        now = float(rc.iloc[-1])
        pc = pctile(hist, now)
        lo, hi = k["move_pctile"]
        va = j.iloc[:, 0].rolling(k["window"]).std() * np.sqrt(252) * 100
        vol_chg = float(va.iloc[-1] - va.iloc[-22]) if len(va.dropna()) > 22 else None
        out[v] = {"corr": r(now, 2), "pctile": r(pc, 0), "min_3y": r(hist.min(), 2), "max_3y": r(hist.max(), 2),
                  "own_vol_change_1m": r(vol_chg, 1),
                  "change_1m": r(now - float(rc.iloc[-22]), 2) if len(rc) > 22 else None,
                  "unusual": bool(pc is not None and (pc <= lo or pc >= hi)),
                  "independent_windows": int(k["lookback_days"] // k["window"])}
    return out or None
