"""TSMC monthly consolidated net revenue from its investor-relations site (public, no key), one page per year.
Published around the 10th of the next month (unaudited); dated at the reference month (first day).

  tsmc:revenue       NT$ millions
  tsmc:revenue_yoy   year-on-year change as TSMC publishes it, %

TSMC makes nearly every leading AI accelerator, so monthly revenue is the earliest hard print of AI chip output;
it also carries smartphones and PCs, and NT$ moves change it (revenue is in NT$).
"""
from __future__ import annotations

import html as htmlmod
import re
from datetime import date

import pandas as pd

from . import ai_common as ac, base

KIND = "obs"
URL = "https://investor.tsmc.com/english/monthly-revenue/{year}"
MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
          "oct": 10, "nov": 11, "dec": 12}
_ROW = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\.?\s+([\d,]{3,})\s+(-?[\d.]+)\s*%")


def records(page: str, year: int, fetched) -> list[dict]:
    text = re.sub(r"\s+", " ", htmlmod.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style).*?</\1>", " ", page, flags=re.S))))
    i = text.find("Monthly Revenue (In Millions")
    j = text.find("Total", i)
    body = text[i:j] if i >= 0 and j > i else ""
    url, out = URL.format(year=year), []
    for m in _ROW.finditer(body):
        d = date(year, MONTHS[m.group(1).lower()], 1)
        out.append(ac.row("tsmc", "tsmc:revenue", "TSMC monthly revenue", d, float(m.group(2).replace(",", "")),
                          "NT$ mn", "monthly", url, fetched))
        out.append(ac.row("tsmc", "tsmc:revenue_yoy", "TSMC monthly revenue, y/y", d, float(m.group(3)), "%",
                          "monthly", url, fetched))
    return out


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    fetched, rows, errors, budget = base.now_utc(), [], [], ac.Budget(cfg)
    y1 = fetched.year
    y0 = (since.year - 1) if since else int(cfg.get("first_year", y1 - 3))   # the previous year too: a January needs it
    for y in range(y1, y0 - 1, -1):                                         # newest first: a budget cut keeps today
        if budget.out():
            errors.append(f"time budget reached before {y}")
            break
        try:
            got = records(ac.get(URL.format(year=y), cfg, headers={"User-Agent": ac.BROWSER_UA}).text, y, fetched)
            if not got and y < y1:
                errors.append(f"{y}: no monthly rows parsed")
            rows += got
        except Exception as e:  # noqa: BLE001
            errors.append(f"{y}: {type(e).__name__}: {e}")
    if since is not None:
        rows = [r for r in rows if r["date"] >= since]
    if not rows and errors:
        raise RuntimeError("; ".join(errors))
    return ac.frame(rows, errors)
