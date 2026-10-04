"""Daily closes from Yahoo Finance's public chart endpoint.

Unofficial and for personal use only. Do not carry into the corporate build: replace
with a Trading Technologies or licensed vendor adapter that returns the same columns.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd

from . import base

KIND = "obs"
API = "https://query1.finance.yahoo.com/v8/finance/chart/{t}"
HUMAN = "https://finance.yahoo.com/quote/{t}"


def _one(ticker: str, start: date) -> pd.DataFrame:
    p1 = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp())
    p2 = int(datetime.now(timezone.utc).timestamp())
    js = base.get_json(API.format(t=ticker), params={"period1": p1, "period2": p2, "interval": "1d"})
    res = (js.get("chart", {}).get("result") or [None])[0]
    if not res or not res.get("timestamp"):
        return pd.DataFrame()
    off = res.get("meta", {}).get("gmtoffset", 0)
    ts = pd.to_datetime(pd.Series(res["timestamp"]) + off, unit="s")   # exchange-local trading date
    close = res["indicators"]["quote"][0]["close"]
    return pd.DataFrame({"date": ts.dt.date, "value": close})


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    start = since or date.fromisoformat(cfg.get("backfill_start", "2023-01-01"))
    if isinstance(start, str):
        start = date.fromisoformat(start)
    fetched = base.now_utc()
    frames, errors = [], []
    for t in cfg["tickers"]:
        try:
            df = _one(t["id"], start)
        except Exception as e:     # one bad ticker must not sink the batch
            errors.append(f"{t['id']}: {e}")
            continue
        if df.empty:
            continue
        frames.append(pd.DataFrame({
            "source": "prices", "series_id": t["id"], "name": t["name"] + f" [{t['group']}]",
            "date": df["date"], "value": df["value"], "unit": "close", "freq": "daily",
            "source_url": HUMAN.format(t=t["id"]), "fetched_at": fetched,
        }))
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    out.attrs["errors"] = errors
    return out
