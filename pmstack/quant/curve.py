"""Futures curve shape from stored contracts (prices_curve), point in time. First module of the quant library.

The theory of storage (Working 1949; Kaldor 1939; Brennan 1958) ties the slope of the curve to inventories: low
stocks go with backwardation (a convenience yield), ample stocks with contango up to the cost of carry. Gorton,
Hayashi & Rouwenhorst (2013) find the futures basis tracks inventory deviations. So the energy card reports the
front spreads beside the balance; code computes them, and S2 extends this into the carry-and-curve module.

Positions (M1, M2...) are computed from the contracts that have a close on the as-of date, ordered by delivery
month, so a roll never rewrites history. History is short: collection started 24 Oct 2026 (Yahoo keeps no expired
contracts), plus whatever each live contract's own history covers.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from .. import store

MONTHS = "FGHJKMNQUVXZ"
COLLECTION_START = date(2026, 10, 24)    # only contracts alive on this day were fetched: earlier "curves" are wrong


def _month_key(code: str, root: str) -> tuple[int, int] | None:
    body = code.split(".")[0][len(root):]
    if len(body) != 3 or body[0] not in MONTHS:
        return None
    return 2000 + int(body[1:]), MONTHS.index(body[0]) + 1


def curve(root: str, asof: date, con=None, max_age_days: int = 5) -> pd.DataFrame:
    """Closes of the root's live contracts on the last date <= asof that has at least two of them."""
    if asof < COLLECTION_START:
        return pd.DataFrame()
    con = con or store.connect()
    try:
        df = con.execute("SELECT series_id, date, value, source_url FROM obs WHERE source = 'prices_curve' AND series_id LIKE ? "
                         "AND date <= ? AND date >= ?", [f"{root}%", asof, asof - pd.Timedelta(days=max_age_days + 10)]).df()
    except Exception:  # noqa: BLE001  no prices_curve data yet
        return pd.DataFrame()
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df[df["series_id"].map(lambda c: _month_key(c, root) is not None)]
    for d in sorted(df["date"].unique(), reverse=True):
        day = df[df["date"] == d].copy()
        if len(day) >= 2 and (asof - d).days <= max_age_days:
            day["ym"] = day["series_id"].map(lambda c: _month_key(c, root))
            day = day.sort_values("ym").reset_index(drop=True)
            y, m = day["ym"].iloc[0]
            if (y - asof.year) * 12 + (m - asof.month) > 3:          # the front contract is missing: not a curve
                return pd.DataFrame()
            day["pos"] = [f"M{i + 1}" for i in range(len(day))]
            return day[["pos", "series_id", "date", "value", "source_url"]]
    return pd.DataFrame()


def shape(root: str, asof: date, con=None) -> dict | None:
    """Front spreads in price units and % of M1, and a label: backwardation / contango / flat (within 0.25%)."""
    c = curve(root, asof, con)
    if c.empty:
        return None
    m = {r.pos: r for r in c.itertuples()}
    out = {"root": root, "date": str(c["date"].iloc[0]), "contracts": len(c), "m1": m["M1"].series_id,
           "m1_close": round(float(m["M1"].value), 4), "source_url": m["M1"].source_url}
    for far in ("M2", "M3", "M6", "M12"):
        if far in m:
            sp = float(m["M1"].value) - float(m[far].value)
            out[f"m1_{far.lower()}"] = round(sp, 4)
            out[f"m1_{far.lower()}_pct"] = round(100 * sp / float(m["M1"].value), 2) if m["M1"].value else None
            out[f"{far.lower()}_contract"] = m[far].series_id
    # carry (Koijen, Moskowitz, Pedersen & Vrugt 2018): the annualised return if the curve stays put, from M1 and M2
    if "M2" in m:
        (y1, mo1), (y2, mo2) = _month_key(m["M1"].series_id, root), _month_key(m["M2"].series_id, root)
        gap = (y2 - y1) * 12 + (mo2 - mo1)
        if gap > 0 and float(m["M2"].value) > 0:
            out["carry_ann_pct"] = round(100 * (float(m["M1"].value) / float(m["M2"].value) - 1) * 12 / gap, 1)
            out["carry_note"] = "M1 over M2, annualised; seasonal for gas and gasoline (compare the same months, not the level)"
    span = (asof - COLLECTION_START).days
    out["basis_momentum"] = None
    out["basis_momentum_note"] = f"n/a: needs 12 months of rolled M1 and M2 returns (history {span / 365:.1f} years)"
    key = "m1_m6_pct" if "m1_m6_pct" in out else "m1_m2_pct"
    v = out.get(key)
    out["label"] = None if v is None else "backwardation" if v > 0.25 else "contango" if v < -0.25 else "flat"
    out["label_basis"] = key
    return out
