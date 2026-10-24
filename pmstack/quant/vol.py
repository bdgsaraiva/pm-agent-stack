"""Volatility (quant library): realised vol at 21 and 63 days (21 sessions = the 30-calendar-day horizon of CBOE's
OVX/GVZ/VIX), its percentile and regime against the market's own history, a same-calendar-month percentile for
seasonal markets (gas, products, grains: winter vol would always look stretched otherwise; Suenaga, Smith &
Williams 2008), and the implied-minus-realised gap where a free implied index exists.

Implied above realised is the normal state (negative variance risk premia in 18 of 21 commodities, Prokopczuk,
Symeonidis & Wese Simen 2017; Trolle & Schwartz 2010 for energy), so the gap is judged against its own history,
never by its sign. OVX is implied vol of USO options and GVZ of GLD options, not of the futures: the card says so.
Vol state is risk context, never a timing input (vol-managed portfolios fail out of sample: Cederburg et al. 2020;
no Sharpe gain for commodities: Harvey et al. 2018). Details: docs/research/quant.md."""
from __future__ import annotations

import math
from datetime import date

import numpy as np
import pandas as pd

from .common import cfg, pctile, r, series

IV_INSTRUMENT = {"OVXCLS": "OVX (options on the USO ETF, not on WTI futures)", "GVZCLS": "GVZ (options on the GLD ETF)",
                 "VIXCLS": "VIX (S&P 500 index options)"}


def realised(p: pd.Series, window: int, ann: int = 252) -> pd.Series:
    return np.log(p).diff().rolling(window, min_periods=int(window * 0.8)).std() * math.sqrt(ann) * 100


def regime(pc: float | None, c: dict) -> str | None:
    if pc is None:
        return None
    lo, hi, ex = c["vol"]["regime_pctiles"]
    return "extreme" if pc >= ex else "high" if pc > hi else "low" if pc < lo else "normal"


def state(p: pd.Series, asof: date, con=None, iv_id: str | None = None, c: dict | None = None,
          seasonal_vol: bool = False) -> dict | None:
    c = c or cfg()
    v = c["vol"]
    p = p[p.index <= pd.Timestamp(asof)].dropna()
    w1, w2 = v["windows"]
    if len(p) < w2 + 30:
        return None
    a, b = realised(p, w1, v["annualise"]).dropna(), realised(p, w2, v["annualise"]).dropna()
    if a.empty or b.empty:
        return None
    now = float(a.iloc[-1])
    recent = a.tail(v["pctile_lookback_days"])
    pc_recent, pc_full = pctile(recent, now), pctile(a, now)
    out = {"date": str(p.index[-1].date()), "rv_short": r(now, 1), "rv_long": r(b.iloc[-1], 1), "windows": [w1, w2],
           "pctile_3y": r(pc_recent, 0), "pctile_full": r(pc_full, 0), "full_since": str(a.index[0].date()),
           "regime": regime(pc_full, c), "ratio": r(now / float(b.iloc[-1]), 2) if b.iloc[-1] else None}
    out["change_1w"] = r(now - float(a.iloc[-6]), 1) if len(a) > 6 else None
    out["rising_fast"] = bool(out["ratio"] is not None and out["ratio"] >= v["jump_ratio"])
    if seasonal_vol:                                      # same calendar month only, strictly earlier years
        m = p.index[-1].month
        same = a[(a.index.month == m) & (a.index.year < p.index[-1].year)]
        out["pctile_same_month"] = r(pctile(same, now), 0) if len(same) >= 200 else None
    if iv_id and con is not None:
        iv = series(con, "fred", iv_id, asof)
        if len(iv):
            ivl = float(iv.iloc[-1])
            gap_hist = (iv - a.reindex(iv.index)).dropna()            # implied minus realised on common days
            rv_at = a.loc[:iv.index[-1]]                               # realised vol on the implied index's own date (review S2)
            rv_iv = float(rv_at.iloc[-1]) if len(rv_at) else now
            gap = ivl - rv_iv
            out.update(iv_id=iv_id, iv_instrument=IV_INSTRUMENT.get(iv_id, iv_id), iv=r(ivl, 1), iv_date=str(iv.index[-1].date()),
                       rv_on_iv_date=r(rv_iv, 1), iv_minus_rv=r(gap, 1), iv2_minus_rv2=r(ivl ** 2 - rv_iv ** 2, 0),
                       gap_pctile=r(pctile(gap_hist.tail(v["pctile_lookback_days"]), gap), 0),
                       realised_above_implied=bool(gap < 0),
                       iv_url=f"https://fred.stlouisfed.org/series/{iv_id}")
            g = out["gap_pctile"]
            out["gap_stretched"] = bool(g is not None and (g >= v["gap_stretched_pctile"][1] or g <= v["gap_stretched_pctile"][0]))
    return out
