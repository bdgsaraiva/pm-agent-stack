"""Shared helpers for the AI compute-demand adapters (getdeploying, akash, dramexchange, openrouter, ramp, census_c30,
tsmc, kcs). Not an adapter itself. Evidence and access notes: docs/research/ai-demand-signals.md.

Every adapter here fails softly: a series or page that cannot be read becomes an entry in `df.attrs["errors"]`, and
the adapter stops at its `budget_s` so the data job (GitHub Actions, where some sites block cloud IPs) reaches its
commit step. fetch.run() logs an exception from fetch() as a source error and moves on to the next source.
"""
from __future__ import annotations

import time

import pandas as pd

from . import base
from ..store import OBS_COLS

BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/130 Safari/537.36")   # some public pages answer a bot UA with an empty shell


def row(source: str, sid: str, name: str, d, value, unit: str, freq: str, url: str, fetched) -> dict:
    return {"source": source, "series_id": sid, "name": name, "date": pd.Timestamp(d).date(), "value": float(value),
            "unit": unit, "freq": freq, "source_url": url, "fetched_at": fetched}


def frame(rows: list[dict], errors: list[str]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=OBS_COLS)
    if not df.empty:
        df = df.drop_duplicates(["series_id", "date"], keep="last").reset_index(drop=True)
    df.attrs["errors"] = errors
    return df


class Budget:
    """Wall-clock budget for one source (`budget_s` in its block)."""

    def __init__(self, cfg: dict, default: float = 90):
        self.t0, self.limit = time.monotonic(), float(cfg.get("budget_s", default))

    def out(self) -> bool:
        return time.monotonic() - self.t0 > self.limit


def get(url: str, cfg: dict, **kw):
    """base.get with the block's timeout and retries (2 tries by default: a blocked site fails fast)."""
    return base.get(url, timeout=int(cfg.get("timeout_s", 30)), tries=int(cfg.get("tries", 2)), **kw)
