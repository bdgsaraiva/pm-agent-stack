"""USDA FAS weekly Export Sales (ESR) via the FAS Data API (key: USDA_FAS_API_KEY, the api.data.gov key PSD uses;
host api.fas.usda.gov, X-Api-Key header or ?api_key=). US government data, public domain.

Released Thursday 08:30 ET for the week ending the previous Thursday (a Friday after a holiday). The API returns one
row per destination country and week; this adapter sums the countries:

  fas_esr:<crop>:<field>:MY<marketYear>   metric tons, dated at the week-ending date

fields: net_sales (current market year), weekly_exports, accumulated_exports, outstanding_sales, total_commitment
(= accumulated exports + outstanding sales), next_my_net_sales. ESR labels a market year by the calendar year it
ends in (corn "2026" = Sep 2025-Aug 2026; wheat "2027" = Jun 2026-May 2027). A reader uses a week from its release:
week ending + `release_lag_days` (8: the Thursday after, one day of margin for holiday weeks). Weekly values are
revised in later reports; the API keeps the latest, so history is the revised series (first prints are not kept).
"""
from __future__ import annotations

import os
from collections import defaultdict
from datetime import date

import pandas as pd

from . import ai_common as ac, base

KIND = "obs"
API = "https://api.fas.usda.gov/api/esr"
HUMAN = "https://apps.fas.usda.gov/esrquery/"
FIELDS = {"currentmynetsales": "net_sales", "weeklyexports": "weekly_exports", "accumulatedexports": "accumulated_exports",
          "outstandingsales": "outstanding_sales", "currentmytotalcommitment": "total_commitment", "nextmynetsales": "next_my_net_sales"}


def _get(path: str, key: str, cfg: dict):
    return base.get_json(API + path, headers={"X-Api-Key": key, "Accept": "application/json"},
                         timeout=int(cfg.get("timeout_s", 60)), tries=int(cfg.get("tries", 2)))


def aggregate(records: list[dict]) -> dict[tuple[str, date], float]:
    """Sum every country's row per week and field."""
    out: dict[tuple[str, date], float] = defaultdict(float)
    for r in records:
        k = {str(a).lower(): v for a, v in r.items()}
        wk = str(k.get("weekendingdate") or "")[:10]
        if not wk:
            continue
        d = date.fromisoformat(wk)
        for src, name in FIELDS.items():
            v = k.get(src)
            if isinstance(v, (int, float)):
                out[(name, d)] += float(v)
    return dict(out)


def current_my(month_start: int, today: date) -> int:
    """ESR market-year label (the calendar year the market year ends in)."""
    return today.year + 1 if today.month >= month_start else today.year


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    key = os.environ.get("USDA_FAS_API_KEY")
    if not key:
        raise RuntimeError("USDA_FAS_API_KEY not set (repo secret; api.data.gov key)")
    fetched = base.now_utc()
    budget = ac.Budget(cfg, 300)
    today = date.today()
    rows, errors, fails = [], [], 0
    for crop, c in cfg["commodities"].items():
        cur = current_my(int(c["my_start_month"]), today)
        known = cfg.get("_known") or set()
        allyrs = list(range(int(cfg.get("history_from_my", 2012)), cur + 1))
        # a normal run reads the current market year plus any year not stored yet (a cut-short backfill resumes)
        years = allyrs if since is None else [y for y in allyrs if y == cur or f"fas_esr:{crop}:net_sales:MY{y}" not in known]
        for my in reversed(years):
            if budget.out() or fails >= 3:
                errors.append(f"{crop} MY{my}: " + ("time budget" if fails < 3 else "3 calls failed in a row") + " (the rest next run)")
                break
            try:
                recs = _get(f"/exports/commodityCode/{c['code']}/allCountries/marketYear/{my}", key, cfg)
            except Exception as e:  # noqa: BLE001  (a 429 or outage: stop after three in a row)
                fails += 1
                errors.append(f"{crop} MY{my}: {type(e).__name__}: {e}"[:200])
                continue
            fails = 0
            for (field, d), v in aggregate(recs or []).items():
                rows.append(ac.row("fas_esr", f"fas_esr:{crop}:{field}:MY{my}", f"US {crop} export sales: {field.replace('_', ' ')} (MY{my}, all countries)",
                                   d, v, "t", "weekly", HUMAN, fetched))
    if not rows:
        raise RuntimeError("; ".join(errors) or "no export-sales rows")
    return ac.frame(rows, errors)
