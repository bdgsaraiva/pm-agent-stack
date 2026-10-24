"""Futures curves from Yahoo Finance: the next N listed contracts per root, stored under their exact codes.

Unofficial and for personal use only, like adapters/yahoo.py (never port it; the corporate build swaps in a licensed
curve). Started 24 Oct 2026 (specialists S1) so the quant library's carry-and-curve module (S2) inherits a forward
history: Yahoo keeps no history for expired contracts, so every day not collected is lost.

Series ids are the contract codes (CLZ26.NYM, BZF27.NYM...); the curve position (M1, M2...) is computed by code on
read from the listing order, never stored, so a roll never rewrites history.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pandas as pd

from . import base
from .yahoo import HUMAN, MONTHS, _one

KIND = "obs"


def contracts(root: str, exch: str, n: int, today: date, months: str = MONTHS, skip_current: bool = False) -> list[str]:
    """The next `n` contract codes in the root's cycle from this month on (Yahoo drops expired ones itself)."""
    out, y, m = [], today.year, today.month
    if skip_current:
        m += 1
        if m > 12:
            y, m = y + 1, 1
    while len(out) < n:
        code = MONTHS[m - 1]
        if code in months:
            out.append(f"{root}{code}{y % 100:02d}.{exch}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    today = datetime.now(timezone.utc).date()
    start = since or date.fromisoformat(cfg.get("backfill_start", "2025-01-01"))
    if isinstance(start, str):
        start = date.fromisoformat(start)
    fetched = base.now_utc()
    frames, errors = [], []
    t0 = datetime.now(timezone.utc)
    budget = float(cfg.get("budget_s", 120))
    known = cfg.get("_known")
    for spec in cfg["roots"]:
        n = int(spec.get("n", 12))
        # expired contracts at the front (the current month's, often the next one's too) come back empty: look 3 further
        codes = contracts(spec["root"], spec["exch"], n + 3, today, spec.get("months", MONTHS),
                          bool(spec.get("skip_current", False)))
        got = 0
        for c in codes:
            if got >= n:
                break
            if (datetime.now(timezone.utc) - t0).total_seconds() > budget:
                errors.append(f"budget {budget:.0f}s reached before {c}")
                break
            s0 = date.fromisoformat(cfg.get("backfill_start", "2025-01-01")) if (known is not None and c not in known) else start
            try:
                df = _one(c, s0 - timedelta(days=3))
            except Exception as e:  # noqa: BLE001  one contract must not sink the curve
                if got:                                           # an expired front contract (404) is not an error
                    errors.append(f"{c}: {e}")
                continue
            if df.empty or pd.to_datetime(df["date"]).max().date() < today - timedelta(days=10):
                continue                                          # expired or not trading
            got += 1
            frames.append(pd.DataFrame({
                "source": "prices_curve", "series_id": c, "name": f"{spec['name']} {c.split('.')[0][len(spec['root']):]} [curve]",
                "date": df["date"], "value": df["value"], "unit": spec.get("unit", "close"), "freq": "daily",
                "source_url": HUMAN.format(t=c), "fetched_at": fetched,
            }))
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    out.attrs["errors"] = errors
    if errors and not frames:
        raise RuntimeError("; ".join(errors)[:500])
    return out
