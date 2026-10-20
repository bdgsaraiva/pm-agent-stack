"""USDA FAS Production, Supply and Distribution (PSD) via the FAS Data API (key: USDA_FAS_API_KEY, an api.data.gov key,
sent as the X-Api-Key header; host api.fas.usda.gov since the portal moved, checked 20 Oct 2026).

Used for what WASDE's CSV does not carry: world sugar (FAS semi-annual) and long stocks-to-use histories by
market year for the percentile context (docs/research/balance.md). PSD holds the current, revised series: each
fetch stores what PSD says now, dated at its own vintage (calendar year and month of the record, never later than
the fetch), so an as-of query never sees a number before it existed.
  psd:<commodity>:<country>:<attribute>:<market year>
The swagger documents no response model, so field names are matched loosely (commodityCode / Commodity_Code ...);
the first live run (`pmstack balance probe`) prints what came back.
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import date

import pandas as pd

from . import base

KIND = "obs"
API = "https://api.fas.usda.gov/api/psd"   # the old apps.fas.usda.gov/OpenData base answers 403/500
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


AUTH = {"how": "x-api-key"}    # the variant that worked last in this process (the swagger names X-Api-Key)


def _get(path: str, key: str, timeout: int):
    """api.data.gov keys go as the X-Api-Key header (the swagger's scheme) or ?api_key=. The first variant that
    answers is kept."""
    variants = {"x-api-key": ({"X-Api-Key": key}, None), "query": ({}, {"api_key": key})}
    order = [AUTH["how"]] + [k for k in variants if k != AUTH["how"]]
    last = None
    for how in order:
        h, q = variants[how]
        try:
            out = base.get_json(API + path, headers={**h, "Accept": "application/json"}, params=q, timeout=timeout, tries=1)
            AUTH["how"] = how
            return out
        except Exception as e:  # noqa: BLE001
            last = e
    raise last


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
    # Every run refreshes the last three market years of every pair, then spends what is left of the budget on the
    # history, oldest missing year first, recorded per pair in a progress file so an interrupted first run resumes
    # next time (review A12: with `since` set the history was never finished).
    from .. import store
    prog_file = store.DATA / "obs" / "usda_psd" / "_progress.json"
    try:
        prog = json.loads(prog_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        prog = {}
    if cfg.get("backfill_start"):                     # --backfill: everything again
        prog = {}
    rows, errors, done_any = [], [], False
    budget = float(cfg.get("budget_s", 180))

    def get_year(ck, c, country, my):
        path = (f"/commodity/{c['code']}/world/year/{my}" if country == "world"
                else f"/commodity/{c['code']}/country/{country}/year/{my}")
        out = records(_get(path, key, timeout), ck, country.lower(), attrs, units, keep, today, fetched)
        time.sleep(float(cfg.get("pause_s", 0.3)) if not os.environ.get("PMSTACK_NO_PAUSE") else 0)
        return out

    pairs = [(ck, c, country) for ck, c in cfg["commodities"].items() for country in c.get("countries", ["world"])]
    fails = 0
    for ck, c, country in pairs:                       # 1. the recent years, every pair
        for my in range(max(first_my, cur - 2), cur + 1):
            if time.monotonic() - t0 > budget or fails >= 3:
                break
            try:
                rows += get_year(ck, c, country, my)
                fails = 0
            except Exception as e:  # noqa: BLE001
                fails += 1
                errors.append(f"{ck} {country} {my}: {type(e).__name__}: {str(e)[:120]}")
    if fails >= 3:                                     # the API is failing: don't spend the job's time on it
        errors.insert(0, "3 calls failed in a row: PSD skipped this run")
        budget = -1.0
    for ck, c, country in pairs:                       # 2. the history, resumable
        pk = f"{ck}:{country.lower()}"
        nxt = int(prog.get(pk, first_my))              # the oldest year not yet fetched
        while nxt < cur - 2 and time.monotonic() - t0 <= budget:
            try:
                rows += get_year(ck, c, country, nxt)
            except Exception as e:  # noqa: BLE001
                errors.append(f"{ck} {country} {nxt}: {type(e).__name__}: {str(e)[:120]}")
                break                                  # retry this year next run
            nxt += 1
            prog[pk], done_any = nxt, True
    left = sum(max(0, cur - 2 - int(prog.get(f"{ck}:{country.lower()}", first_my))) for ck, c, country in pairs)
    if done_any:
        prog_file.parent.mkdir(parents=True, exist_ok=True)
        prog_file.write_text(json.dumps(prog, indent=1, sort_keys=True), encoding="utf-8")
    out = pd.DataFrame(rows)
    out.attrs["errors"] = errors[:20]
    out.attrs["notes"] = f"attributes_source: {attr_src}; history years still to fetch: {left}"
    return out
