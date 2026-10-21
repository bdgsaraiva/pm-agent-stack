"""Japanese government bond yields from Japan's Ministry of Finance (benchmark constant-maturity yields, daily CSV).
Free, no key. The current month's file is small; the full history (since 1974) is read once for a backfill."""
from __future__ import annotations

import io

import pandas as pd

from . import base

KIND = "obs"
CURRENT = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv"
HISTORY = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv"
HUMAN = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/index.htm"


def _parse(txt: str) -> pd.DataFrame:
    lines = txt.splitlines()
    head = next(i for i, ln in enumerate(lines) if ln.startswith("Date,"))
    df = pd.read_csv(io.StringIO("\n".join(lines[head:])))
    df["Date"] = pd.to_datetime(df["Date"], format="%Y/%m/%d", errors="coerce")
    return df.dropna(subset=["Date"])


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    fetched = base.now_utc()
    known = cfg.get("_known")
    full = since is None or (known is not None and any(s["id"] not in known for s in cfg["series"]))
    df = _parse(base.get_text(CURRENT))
    if full:
        hist = _parse(base.get_text(HISTORY, timeout=90))
        df = pd.concat([hist[hist["Date"] >= pd.Timestamp(cfg.get("backfill_start", "2015-01-01"))], df]).drop_duplicates("Date")
    elif since is not None:
        df = df[df["Date"].dt.date >= since]
    frames = []
    for s in cfg["series"]:
        col = s["column"]
        if col not in df.columns:
            continue
        frames.append(pd.DataFrame({
            "source": "mof_jgb", "series_id": s["id"], "name": s["name"],
            "date": df["Date"].dt.date, "value": pd.to_numeric(df[col], errors="coerce"),
            "unit": "pct", "freq": "daily", "source_url": HUMAN, "fetched_at": fetched,
        }).dropna(subset=["value"]))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
