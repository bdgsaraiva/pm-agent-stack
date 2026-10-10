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
    meta = res.get("meta", {})
    off = meta.get("gmtoffset", 0)
    ts = pd.to_datetime(pd.Series(res["timestamp"]) + off, unit="s")   # exchange-local trading date
    close = res["indicators"]["quote"][0]["close"]
    df = pd.DataFrame({"date": ts.dt.date, "value": close}).dropna()
    # The daily series can lag the latest session by hours; use the regular-market print for that day.
    px, t = meta.get("regularMarketPrice"), meta.get("regularMarketTime")
    if px is not None and t:
        d = pd.to_datetime(t + off, unit="s").date()
        if df.empty or d > df["date"].iloc[-1]:
            df = pd.concat([df, pd.DataFrame({"date": [d], "value": [float(px)]})], ignore_index=True)
    return df


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    start = since or date.fromisoformat(cfg.get("backfill_start", "2023-01-01"))
    if isinstance(start, str):
        start = date.fromisoformat(start)
    fetched = base.now_utc()
    frames, errors = [], []
    for t in cfg["tickers"]:
        try:
            known = cfg.get("_known")
            first = known is not None and t["id"] not in known
            df = _one(t["id"], date.fromisoformat(cfg.get("backfill_start", "2023-01-01")) if first else start)
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
