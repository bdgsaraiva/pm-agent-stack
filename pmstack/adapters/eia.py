"""EIA Weekly Petroleum Status Report via the EIA API v2 (free key: EIA_API_KEY)."""
from __future__ import annotations

import os

import pandas as pd

from . import base

KIND = "obs"
API = "https://api.eia.gov/v2/seriesid/{sid}"
HUMAN = "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s={code}&f=W"


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    key = os.environ.get("EIA_API_KEY")
    if not key:
        raise RuntimeError("EIA_API_KEY not set (free key: https://www.eia.gov/opendata/register.php)")
    start = str(since) if since else cfg.get("backfill_start", "2018-01-01")
    fetched = base.now_utc()
    frames = []
    for s in cfg["series"]:
        js = base.get_json(API.format(sid=s["id"]), params={"api_key": key, "start": start, "length": 5000})
        rows = js.get("response", {}).get("data", [])
        if not rows:
            continue
        df = pd.DataFrame(rows)
        code = s["id"].split(".")[1]
        frames.append(pd.DataFrame({
            "source": "eia",
            "series_id": s["id"],
            "name": s["name"],
            "date": pd.to_datetime(df["period"]).dt.date,
            "value": pd.to_numeric(df["value"], errors="coerce"),
            "unit": s["unit"],
            "freq": "weekly",
            "source_url": HUMAN.format(code=code),
            "fetched_at": fetched,
        }))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
