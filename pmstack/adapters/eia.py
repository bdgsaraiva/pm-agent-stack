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
    frames, errors = [], []
    for s in cfg["series"]:
        known = cfg.get("_known")
        s_start = cfg.get("backfill_start", "2018-01-01") if (known is not None and s["id"] not in known) else start
        try:      # one bad id must not cost the block's other series (16 Oct 2026: WCRAUUS2 is not on the API)
            js = base.get_json(API.format(sid=s["id"]), params={"api_key": key, "start": s_start, "length": 5000})
        except Exception as e:  # noqa: BLE001
            errors.append(f"{s['id']}: {e}")
            continue
        rows = js.get("response", {}).get("data", [])
        if not rows:
            continue
        df = pd.DataFrame(rows)
        code = s["id"].split(".")[1]
        frames.append(pd.DataFrame({
            "source": cfg.get("source", "eia"),     # a second block (balance keeper: eia_bal) keeps its own source
            "series_id": s["id"],
            "name": s["name"],
            "date": pd.to_datetime(df["period"]).dt.date,
            "value": pd.to_numeric(df["value"], errors="coerce"),
            "unit": s["unit"],
            "freq": "weekly",
            "source_url": s.get("url") or HUMAN.format(code=code),   # gas series carry their own page (energy S1)
            "fetched_at": fetched,
        }))
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    out.attrs["errors"] = errors
    if errors and not frames:
        raise RuntimeError("; ".join(errors)[:500])
    return out
