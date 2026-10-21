"""Ramp AI Index (https://ramp.com/data/ai-index): monthly share of US businesses paying for AI, from card and bill-pay
transactions of 85,000+ firms on Ramp. Free public page, no key; the numbers sit in the page's embedded data.
Not an official statistic: Ramp's own customers (skewed to tech-forward small and mid firms). Cite "Ramp AI Index".
Published mid-month for the previous month; dated at the reference month (first day). Recent months can be revised.

  ramp:adoption          share of businesses with paid AI subscriptions or spend, %
  ramp:spend_share       AI share of card and bill-pay spend (total payment volume), %
  ramp:adoption:<vendor> share of businesses paying that vendor (openai, anthropic), %
"""
from __future__ import annotations

import json
import re

import pandas as pd

from . import ai_common as ac, base

KIND = "obs"
URL = "https://ramp.com/data/ai-index"


def _array(payload: str, key: str) -> list[dict]:
    m = re.search(r'"%s":\[' % re.escape(key), payload)
    if not m:
        return []
    arr, _ = json.JSONDecoder().raw_decode(payload, m.end() - 1)
    return arr


def records(page: str, cfg: dict, fetched) -> tuple[list[dict], list[str]]:
    u = page.replace('\\"', '"')                  # the Next.js flight payload escapes its JSON once
    rows, errors = [], []
    overall = _array(u, "adoptionOverall")
    for r in overall:
        if r.get("adoption_rate_pct") is not None:
            rows.append(ac.row("ramp", "ramp:adoption", "Ramp AI Index: businesses paying for AI", r["date_month"],
                               r["adoption_rate_pct"], "%", "monthly", URL, fetched))
    if not overall:
        errors.append("adoptionOverall not found (page layout changed?)")
    m = re.search(r'"spendShareData":\{', u)
    share = _array(u[m.start():], "overall") if m else []
    for r in share:
        if r.get("ai_share_of_tpv") is not None:
            rows.append(ac.row("ramp", "ramp:spend_share", "Ramp AI Index: AI share of business spend", r["my_date"],
                               100 * float(r["ai_share_of_tpv"]), "%", "monthly", URL, fetched))
    if not share:
        errors.append("spendShareData.overall not found")
    want = {v.lower(): v for v in cfg.get("vendors", ["OpenAI", "Anthropic"])}
    for r in _array(u, "adoptionVendor"):
        v = str(r.get("vendor", ""))
        if v.lower() in want and r.get("adoption_rate_pct") is not None:
            rows.append(ac.row("ramp", f"ramp:adoption:{v.lower().replace(' ', '-')}", f"Ramp AI Index: businesses paying {v}",
                               r["date_month"], r["adoption_rate_pct"], "%", "monthly", URL, fetched))
    return rows, errors


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    fetched = base.now_utc()
    page = ac.get(cfg.get("url", URL), cfg, headers={"User-Agent": ac.BROWSER_UA}).text
    rows, errors = records(page, cfg, fetched)
    if not rows:
        raise RuntimeError("; ".join(errors) or "no rows")
    if since is not None:
        rows = [r for r in rows if r["date"] >= since]
    return ac.frame(rows, errors)
