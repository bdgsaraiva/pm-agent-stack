"""CFTC Commitments of Traders, disaggregated futures-only, via the CFTC public Socrata API (no key)."""
from __future__ import annotations

import pandas as pd

from . import base

KIND = "obs"
API = "https://publicreporting.cftc.gov/resource/{ds}.json"
HUMAN = "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"

FIELDS = {
    "open_interest_all": "oi",
    "m_money_positions_long_all": "mm_long",
    "m_money_positions_short_all": "mm_short",
    "prod_merc_positions_long_all": "pm_long",
    "prod_merc_positions_short_all": "pm_short",
}


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    start = str(since) if since else cfg.get("backfill_start", "2020-01-01")
    codes = ",".join(f"'{m['code']}'" for m in cfg["markets"])
    names = {m["code"]: m["name"] for m in cfg["markets"]}
    params = {
        "$where": f"cftc_contract_market_code in({codes}) AND report_date_as_yyyy_mm_dd >= '{start}T00:00:00'",
        "$select": "report_date_as_yyyy_mm_dd,cftc_contract_market_code," + ",".join(FIELDS),
        "$limit": 50000,
        "$order": "report_date_as_yyyy_mm_dd",
    }
    rows = base.get_json(API.format(ds=cfg.get("dataset", "72hh-3qpy")), params=params)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"]).dt.date
    for f in FIELDS:
        df[f] = pd.to_numeric(df.get(f), errors="coerce")
    df["mm_net"] = df["m_money_positions_long_all"] - df["m_money_positions_short_all"]
    df["mm_net_pct_oi"] = 100 * df["mm_net"] / df["open_interest_all"]
    fetched = base.now_utc()
    out = []
    for col, short in list(FIELDS.items()) + [("mm_net", "mm_net"), ("mm_net_pct_oi", "mm_net_pct_oi")]:
        out.append(pd.DataFrame({
            "source": "cftc",
            "series_id": df["cftc_contract_market_code"] + "." + short,
            "name": df["cftc_contract_market_code"].map(names) + f" | {short}",
            "date": df["date"],
            "value": df[col],
            "unit": "pct" if short.endswith("pct_oi") else "contracts",
            "freq": "weekly",
            "source_url": HUMAN,
            "fetched_at": fetched,
        }))
    return pd.concat(out, ignore_index=True)
