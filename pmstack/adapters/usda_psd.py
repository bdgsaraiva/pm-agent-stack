"""USDA FAS Production, Supply and Distribution (PSD) via the FAS OpenData API (key: USDA_FAS_API_KEY, header API_KEY).

Used for what WASDE's CSV does not carry: world sugar (FAS semi-annual) and long stocks-to-use histories by
market year for the percentile context (docs/research/balance.md). PSD holds the current, revised series: each
fetch stores what PSD says now, dated at its own vintage (calendar year and month of the record, never later than
the fetch), so an as-of query never sees a number before it existed.
  psd:<commodity>:<country>:<attribute>:<market year>
The swagger documents no response model, so field names are matched loosely (commodityCode / Commodity_Code ...);
the first live run (`pmstack balance probe`) prints what came back.
"""
from __future__ import annotations

import os
import re
import time
from datetime import date

import pandas as pd

from . import base

KIND = "obs"
API = "https://apps.fas.usda.gov/OpenData/api/psd"
HUMAN = "https://apps.fas.usda.gov/psdonline/app/index.html#/app/advQuery"


def _k(d: dict) -> dict:
    return {re.sub(r"[^a-z]", "", str(k).lower()): v for k, v in d.items()}


def slug(s) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")


# PSD's standard attribute ids, used only when /commodityAttributes fails (probe 16 Oct 2026: HTTP 500 with a
# valid key). General knowledge from the PSD downloads, NOT verified against the API: the probe report shows which
# names came from here ("attributes_source").
FALLBACK_ATTRIBUTES = {20: "Beginning Stocks", 28: "Production", 57: "Imports", 86: "Total Supply", 88: "Exports",
                       125: "Domestic Consumption", 130: "Feed Dom. Consumption", 176: "Ending Stocks",
                       178: "Total Distribution", 149: "Human Dom. Consumption"}


def _get(path: str, key: str, timeout: int):
    return base.get_json(API + path, headers={"API_KEY": key, "Accept": "application/json"}, timeout=timeout)


def attribute_names(rows: list[dict]) -> dict[int, str]:
    out = {}
    for r in rows:
        r = _k(r)
        aid = r.get("attributeid")
        name = r.get("attributename") or r.get("attributedescription") or r.get("name")
        if aid is not None and name:
            out[int(aid)] = str(name).strip()
    return out


def unit_names(rows: list[dict]) -> dict[int, str]:
    out = {}
    for r in rows:
        r = _k(r)
        uid = r.get("unitid") or r.get("unitofmeasureid")
        name = r.get("unitdescription") or r.get("unitofmeasure") or r.get("name")
        if uid is not None and name:
            out[int(uid)] = str(name).strip()
    return out


def records(rows: list[dict], key: str, country: str, attrs: dict[int, str], units: dict[int, str], keep: set[str],
            fetched_on: date, fetched) -> list[dict]:
    out = []
    for r in rows or []:
        r = _k(r)
        try:
            aid, my, val = int(r.get("attributeid")), int(r.get("marketyear")), float(r.get("value"))
        except (TypeError, ValueError):
            continue
        name = attrs.get(aid, f"attr-{aid}")
        if slug(name) not in keep:
            continue
        cy, mo = r.get("calendaryear"), r.get("month")
        try:
            vint = min(date(int(cy), int(mo), 15), fetched_on)
        except (TypeError, ValueError):
            vint = fetched_on
        out.append({"source": "usda_psd", "series_id": f"psd:{key}:{country}:{slug(name)}:{my}",
                    "name": f"PSD {key} {country} {name} {my}", "date": vint, "value": val,
                    "unit": units.get(int(r.get("unitid") or 0), ""), "freq": "monthly", "source_url": HUMAN,
                    "fetched_at": fetched})
    return out


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    key = os.environ.get("USDA_FAS_API_KEY")
    if not key:
        raise RuntimeError("USDA_FAS_API_KEY not set (repo secret; api.data.gov key)")
    timeout, t0 = int(cfg.get("timeout_s", 30)), time.monotonic()
    fetched = base.now_utc()
    today = fetched.date()
    try:
        attrs, attr_src = attribute_names(_get("/commodityAttributes", key, timeout)), "api"
    except Exception as e:  # noqa: BLE001
        attrs, attr_src = {}, f"fallback (commodityAttributes failed: {str(e)[:80]})"
    if not attrs:
        attrs = dict(FALLBACK_ATTRIBUTES)
        attr_src = attr_src if attr_src != "api" else "fallback (commodityAttributes empty)"
    try:
        units = unit_names(_get("/unitsOfMeasure", key, timeout))
    except Exception:  # noqa: BLE001
        units = {}
    keep = {slug(a) for a in cfg["attributes"]}
    first_my = int(cfg.get("history_from_my", 2007))
    cur = today.year if today.month >= 5 else today.year - 1   # PSD year 2026 = 2026/27, projected from May
    # a normal run refreshes the last three market years; the first run (nothing stored) or --backfill fetches the
    # history from history_from_my (a commodity added later: run `pmstack fetch --only usda_psd --backfill`)
    rows, errors = [], []
    for ck, c in cfg["commodities"].items():
        years = range(cur - 2 if since else first_my, cur + 1)
        for country in c.get("countries", ["world"]):
            for my in years:
                if time.monotonic() - t0 > float(cfg.get("budget_s", 240)):
                    errors.append(f"time budget reached at {ck} {country} {my}; the rest follows next run")
                    break
                path = (f"/commodity/{c['code']}/world/year/{my}" if country == "world"
                        else f"/commodity/{c['code']}/country/{country}/year/{my}")
                try:
                    rows += records(_get(path, key, timeout), ck, country.lower(), attrs, units, keep, today, fetched)
                except Exception as e:  # noqa: BLE001
                    errors.append(f"{ck} {country} {my}: {type(e).__name__}: {str(e)[:120]}")
                time.sleep(float(cfg.get("pause_s", 0.3)) if not os.environ.get("PMSTACK_NO_PAUSE") else 0)
    out = pd.DataFrame(rows)
    out.attrs["errors"] = errors[:20]
    out.attrs["notes"] = f"attributes_source: {attr_src}"
    return out
