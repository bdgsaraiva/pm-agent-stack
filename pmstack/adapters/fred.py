"""FRED (St. Louis Fed). Uses FRED_API_KEY when set, else the public graph CSV endpoint."""
from __future__ import annotations

import io
import os

import pandas as pd

from . import base

KIND = "obs"
API = "https://api.stlouisfed.org/fred/series/observations"
CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"
HUMAN = "https://fred.stlouisfed.org/series/{id}"


def _one(sid: str, start: str) -> pd.DataFrame:
    key = os.environ.get("FRED_API_KEY")
    if key:
        js = base.get_json(API, params={"series_id": sid, "api_key": key, "file_type": "json",
                                        "observation_start": start})
        df = pd.DataFrame(js.get("observations", []))
        return pd.DataFrame({"date": df.get("date"), "value": df.get("value")})
    txt = base.get_text(CSV, params={"id": sid, "cosd": start})
    df = pd.read_csv(io.StringIO(txt))
    df.columns = ["date", "value"]
    return df


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    start = str(since) if since else cfg.get("backfill_start", "2018-01-01")
    fetched = base.now_utc()
    frames = []
    for s in cfg["series"]:
        df = _one(s["id"], start)
        if df.empty:
            continue
        frames.append(pd.DataFrame({
            "source": "fred",
            "series_id": s["id"],
            "name": s["name"],
            "date": pd.to_datetime(df["date"]).dt.date,
            "value": pd.to_numeric(df["value"].replace(".", None), errors="coerce"),
            "unit": s["unit"],
            "freq": s.get("freq", "daily"),
            "source_url": HUMAN.format(id=s["id"]),
            "fetched_at": fetched,
        }))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
