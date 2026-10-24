"""Seasonality (quant library), reported honestly (quant-research-standards section 13): returns by half-month
(24 periods a year), mean beside median, the share of years up, and a split-sample check (first half of the years
vs the second). With ~20 years per bucket and 24 buckets, about one bucket clears 5% by chance: the card says so.
Only data before the as-of year's bucket is used (point in time). Descriptive, never a calendar signal."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from .common import cfg, r


def period_of(d) -> int:
    d = pd.Timestamp(d)
    return (d.month - 1) * 2 + (0 if d.day <= 15 else 1)          # 0..23


def label(k: int) -> str:
    m = pd.Timestamp(2000, k // 2 + 1, 1).strftime("%b")
    return f"{'1-15' if k % 2 == 0 else '16-end'} {m}"


def table(p: pd.Series, asof: date) -> pd.DataFrame:
    """Log return (%) per year and half-month, from closes strictly before the as-of half-month."""
    p = p[p.index < pd.Timestamp(asof)].dropna()
    if p.empty:
        return pd.DataFrame()
    df = pd.DataFrame({"p": p})
    df["y"], df["k"] = df.index.year, [period_of(d) for d in df.index]
    last = df.groupby(["y", "k"])["p"].last()
    ret = 100 * np.log(last / last.shift(1))
    ret = ret.dropna()
    cur = (pd.Timestamp(asof).year, period_of(asof))
    ret = ret[[idx < cur for idx in ret.index]]                     # never the current (incomplete) bucket
    return ret.rename("ret").reset_index()


def state(p: pd.Series, asof: date, c: dict | None = None) -> dict | None:
    c = c or cfg()
    s = c["seasonal"]
    t = table(p, asof)
    if t.empty:
        return None
    k = (period_of(asof) + s["horizon_periods"]) % 24
    b = t[t["k"] == k].sort_values("y")
    if len(b) < s["min_years"]:
        return None
    h = len(b) // 2
    m1, m2 = float(b["ret"].iloc[:h].mean()), float(b["ret"].iloc[h:].mean())
    q1, q3 = np.percentile(b["ret"], [25, 75])
    se = float(b["ret"].std(ddof=1) / np.sqrt(len(b)))
    mean = float(b["ret"].mean())
    return {"period": label(k), "years": len(b), "from": int(b["y"].min()), "to": int(b["y"].max()),
            "mean_pct": r(mean, 2), "mean_ci95": [r(mean - 1.96 * se, 2), r(mean + 1.96 * se, 2)],
            "median_pct": r(b["ret"].median(), 2), "iqr_pct": [r(q1, 2), r(q3, 2)],
            "up_share": r((b["ret"] > 0).mean(), 2), "first_half_mean": r(m1, 2), "second_half_mean": r(m2, 2),
            "halves_agree": bool(np.sign(m1) == np.sign(m2) and m1 != 0),
            "note": "seasonal norm, descriptive, not tested as a signal; 24 half-month buckets: about 1 clears 5% by chance"}
