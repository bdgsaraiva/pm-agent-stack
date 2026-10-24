"""Shared helpers for the quant library: config, point-in-time price series, percentiles."""
from __future__ import annotations

import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .. import store

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "quant.yaml"


def cfg() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def r(x, nd=2):
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return round(f, nd) if math.isfinite(f) else None


def series(con, source: str, sid: str, asof: date, start: date | None = None) -> pd.Series:
    """Observed values on or before asof (no filled holidays), indexed by Timestamp."""
    q = "SELECT date, value FROM obs WHERE source = ? AND series_id = ? AND date <= ?"
    args = [source, sid, asof]
    if start:
        q += " AND date >= ?"
        args.append(start)
    try:
        df = con.execute(q + " ORDER BY date", args).df()
    except Exception:  # noqa: BLE001  source not fetched yet
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    if df.empty:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    s = pd.Series(df["value"].astype(float).values, index=pd.to_datetime(df["date"])).groupby(level=0).last()
    return s[s > 0] if source == "prices" else s


def log_returns(p: pd.Series) -> pd.Series:
    return np.log(p).diff().dropna()


def pctile(hist: pd.Series, x: float) -> float | None:
    """Share (0-100) of the history at or below x."""
    h = hist.dropna()
    if len(h) < 20 or x is None or not math.isfinite(x):
        return None
    return float(100 * (h <= x).mean())


def connect(con=None):
    return con or store.connect()
