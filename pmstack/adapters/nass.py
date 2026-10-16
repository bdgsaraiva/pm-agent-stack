"""USDA NASS Quick Stats (key: NASS_API_KEY): crop condition (weekly, Mondays 16:00 ET in season) and quarterly
Grain Stocks. "This product uses the NASS API but is not endorsed or certified by NASS."

Every value is dated when it became public, never at its reference date (look-ahead):
  condition  week ending Sunday -> released Monday (date = week_ending + 1 day)
  stocks     "FIRST OF SEP" -> released ~30 Sep; DEC 1 stocks -> January (release dates in config/balance.yaml)
  nass:<slug of short_desc>   one row per release, dated when public; the reference week or quarter is in `name`
"""
from __future__ import annotations

import os
import re
import time
from datetime import date, timedelta

import pandas as pd

from . import base

KIND = "obs"
API = "https://quickstats.nass.usda.gov/api/api_GET/"
HUMAN = "https://quickstats.nass.usda.gov/"
NOTICE = "This product uses the NASS API but is not endorsed or certified by NASS."


def slug(s) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")


def available(row: dict, stock_release: dict) -> date | None:
    """When a NASS number became public."""
    we = str(row.get("week_ending") or "").strip()
    if we:
        try:
            return date.fromisoformat(we[:10]) + timedelta(days=1)
        except ValueError:
            return None
    ref = str(row.get("reference_period_desc") or "").upper().strip()
    year = int(row.get("year") or 0)
    rel = stock_release.get(ref)
    if rel and year:
        m, d, roll = rel
        return date(year + int(roll), int(m), int(d))
    return None


def records(rows: list[dict], cfg: dict, fetched) -> list[dict]:
    out, rel = [], {k.upper(): v for k, v in (cfg.get("stock_release") or {}).items()}
    for r in rows or []:
        val = str(r.get("Value", "")).replace(",", "").strip()
        try:
            v = float(val)
        except ValueError:
            continue                       # (D) withheld, (NA)
        when = available(r, rel)
        if when is None:
            continue
        ref = str(r.get("week_ending") or "")[:10] or f"{r.get('year')}-{slug(r.get('reference_period_desc'))}"
        sd = str(r.get("short_desc", ""))
        out.append({"source": "nass", "series_id": f"nass:{slug(sd)}", "name": f"{sd} ({ref})", "date": when,
                    "value": v, "unit": str(r.get("unit_desc", "")), "freq": "weekly" if r.get("week_ending") else "quarterly",
                    "source_url": HUMAN, "fetched_at": fetched})
    return out


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    key = os.environ.get("NASS_API_KEY")
    if not key:
        raise RuntimeError("NASS_API_KEY not set (repo secret)")
    fetched, t0 = base.now_utc(), time.monotonic()
    y0 = (pd.Timestamp(since).year if since else int(cfg.get("history_from_year", 2015)))
    rows, errors = [], []
    for q in cfg["queries"]:
        if time.monotonic() - t0 > float(cfg.get("budget_s", 180)):
            errors.append(f"time budget reached before {q['short_desc']}; the rest follows next run")
            break
        params = {"key": key, "short_desc": q["short_desc"], "agg_level_desc": "NATIONAL", "year__GE": y0,
                  "format": "JSON", **(q.get("params") or {})}
        try:
            js = base.get_json(API, params=params, timeout=int(cfg.get("timeout_s", 60)))
            rows += records(js.get("data", []), cfg, fetched)
        except Exception as e:  # noqa: BLE001  (NASS answers 400 "no data" for an empty query)
            errors.append(f"{q['short_desc']}: {type(e).__name__}: {str(e)[:120]}")
    out = pd.DataFrame(rows)
    out.attrs["errors"] = errors
    out.attrs["notes"] = NOTICE
    return out
