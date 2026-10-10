"""CFTC Commitments of Traders, disaggregated futures-only, via the CFTC public Socrata API (no key)."""
from __future__ import annotations

import pandas as pd

from . import base

KIND = "obs"
API = "https://publicreporting.cftc.gov/resource/{ds}.json"
HUMAN = "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"

# Logical field -> candidate column names (the Socrata dataset's spellings vary between
# columns; take the first that exists so a renamed column degrades instead of failing).
FIELDS = {
    "oi": ["open_interest_all"],
    "mm_long": ["m_money_positions_long_all", "m_money_positions_long"],
    "mm_short": ["m_money_positions_short_all", "m_money_positions_short"],
    "pm_long": ["prod_merc_positions_long", "prod_merc_positions_long_all"],
    "pm_short": ["prod_merc_positions_short", "prod_merc_positions_short_all"],
}
REQUIRED = ("oi", "mm_long", "mm_short")


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    start = str(since) if since else cfg.get("backfill_start", "2020-01-01")
    codes = ",".join(f"'{m['code']}'" for m in cfg["markets"])
    names = {m["code"]: m["name"] for m in cfg["markets"]}
    params = {
        "$where": f"cftc_contract_market_code in({codes}) AND report_date_as_yyyy_mm_dd >= '{start}T00:00:00'",
        "$limit": 50000,
        "$order": "report_date_as_yyyy_mm_dd",
    }
    rows = base.get_json(API.format(ds=cfg.get("dataset", "72hh-3qpy")), params=params)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"]).dt.date
    found, errors = {}, []
    for key, cands in FIELDS.items():
        col = next((c for c in cands if c in df.columns), None)
        if col is None:
            if key in REQUIRED:
                raise RuntimeError(f"CFTC column for {key} not found (tried {cands})")
            errors.append(f"column for {key} not found (tried {cands})")
            continue
        found[key] = pd.to_numeric(df[col], errors="coerce")
    found["mm_net"] = found["mm_long"] - found["mm_short"]
    found["mm_net_pct_oi"] = 100 * found["mm_net"] / found["oi"]
    fetched = base.now_utc()
    out = []
    for short, series in found.items():
        out.append(pd.DataFrame({
            "source": "cftc",
            "series_id": df["cftc_contract_market_code"] + "." + short,
            "name": df["cftc_contract_market_code"].map(names) + f" | {short}",
            "date": df["date"],
            "value": series,
            "unit": "pct" if short.endswith("pct_oi") else "contracts",
            "freq": "weekly",
            "source_url": HUMAN,
            "fetched_at": fetched,
        }))
    res = pd.concat(out, ignore_index=True)
    res.attrs["errors"] = errors
    return res
