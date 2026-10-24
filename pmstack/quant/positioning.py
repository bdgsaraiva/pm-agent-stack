"""Positioning (quant library): CFTC managed-money net as % of open interest, its 3-year percentile and the weekly
change, used only from the Friday release (positions as of Tuesday; Monday in holiday weeks). Extremes are
crowding context, never contrarian signals: agent 12 measured the CFTC crowded flag at lift 1.00 on 360 episodes
(research/index.md)."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from .common import cfg, pctile, r


_HOL: set | None = None


def release(report) -> date:
    """research.cftc_release with the holiday calendar built once (it was rebuilt per date: 2 minutes a tape)."""
    global _HOL
    if _HOL is None:
        from pandas.tseries.holiday import USFederalHolidayCalendar
        _HOL = {d.date() for d in USFederalHolidayCalendar().holidays("1990-01-01", "2040-12-31")}
    t = pd.Timestamp(report).normalize()
    fri = t + pd.Timedelta(days=(4 - t.dayofweek) % 7 or 7)
    week = {(fri - pd.Timedelta(days=k)).date() for k in range(5)}
    return (fri + pd.Timedelta(days=3)).date() if week & _HOL else fri.date()


def state(con, code: str, asof: date, c: dict | None = None) -> dict | None:
    c = c or cfg()
    k = c["positioning"]
    try:
        df = con.execute("SELECT series_id, date, value FROM obs WHERE source = 'cftc' AND series_id LIKE ? AND date <= ?",
                         [f"{code}%", asof]).df()
    except Exception:  # noqa: BLE001
        return None
    if df.empty:
        return None
    rel = {d: release(d) for d in df["date"].unique()}     # Friday, or Monday in a federal-holiday week (review S2)
    df = df[df["date"].map(lambda d: rel[d] <= asof)]
    if df.empty:
        return None
    pct = df[df["series_id"] == f"{code}.mm_net_pct_oi"].set_index("date")["value"].astype(float).sort_index()
    if len(pct) < 30:
        return None
    hist = pct[pd.to_datetime(pct.index) > pd.to_datetime(pct.index[-1]) - pd.Timedelta(days=3 * 365)]
    now = float(pct.iloc[-1])
    pc = pctile(hist, now)
    lo, hi = k["extreme_pctile"]
    slow = pct.rolling(k.get("slow_weeks", 52), min_periods=26).mean()
    oi = df[df["series_id"] == f"{code}.oi"].set_index("date")["value"].astype(float).sort_index()
    w = k.get("oi_change_weeks", 52)
    oi_chg = 100 * (oi.iloc[-1] / oi.iloc[-1 - w] - 1) if len(oi) > w and oi.iloc[-1 - w] else None
    return {"report_date": str(pct.index[-1])[:10], "net_pct_oi": r(now, 1), "pctile_3y": r(pc, 0),
            "slow_52w": r(slow.iloc[-1], 1) if len(slow.dropna()) else None, "oi_12m_change_pct": r(oi_chg, 1),
            "wow_pp": r(now - float(pct.iloc[-2]), 1) if len(pct) > 1 else None,
            "extreme": bool(pc is not None and (pc <= lo or pc >= hi)),
            "url": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"}
