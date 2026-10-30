"""USDA ESMIS release dates (WASDE, Crop Progress, Grain Stocks, Acreage, Prospective Plantings, Crop Production).

The Economics, Statistics and Market Information System (esmis.nal.usda.gov, formerly usda.library.cornell.edu)
lists every release of a report with its date and time, back to the 1970s for WASDE. The Ags playbooks need exact
report days, so this adapter stores one row per release: `esmis:<slug>` = 1 on the release date (US government,
public domain). ESMIS also lists scheduled future releases: those go to `esmis:<slug>:scheduled` (next-event dates
for the pack), so `esmis:<slug>` only ever holds releases that happened.

The `datetime` attribute carries the release time as printed by ESMIS (labelled Z, but it is Eastern time:
WASDE 12:00, Crop Progress 16:00); the time goes into the row name.
"""
from __future__ import annotations

import re
from datetime import date

import pandas as pd

from . import ai_common as ac, base

KIND = "obs"
URL = "https://esmis.nal.usda.gov/publication/{slug}"
_DT = re.compile(r'datetime="(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})')


def parse(page: str) -> list[tuple[date, str]]:
    return [(date.fromisoformat(d), t) for d, t in _DT.findall(page)]


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    fetched = base.now_utc()
    today = pd.Timestamp.now(tz="America/New_York").date()
    budget = ac.Budget(cfg, 180)
    start = date.fromisoformat(str(cfg.get("history_from", "2000-01-01")))
    rows, errors = [], []
    for rep in cfg["reports"]:
        slug, url = rep["slug"], URL.format(slug=rep["slug"])
        seen: dict[date, str] = {}
        for page in range(int(cfg.get("max_pages", 120))):
            if budget.out():
                errors.append(f"{slug}: time budget at page {page}")
                break
            try:
                got = parse(ac.get(url + (f"?page={page}" if page else ""), cfg, headers={"User-Agent": ac.BROWSER_UA}).text)
            except Exception as e:  # noqa: BLE001
                errors.append(f"{slug} page {page}: {type(e).__name__}: {e}"[:200])
                break
            if not got:
                break
            for d, t in got:
                seen.setdefault(d, t)
            oldest = min(d for d, _ in got)
            if oldest < start or (since is not None and oldest < since):
                break
        for d, t in sorted(seen.items()):
            if start <= d <= today:
                rows.append(ac.row("esmis", f"esmis:{slug}", f"{rep['name']} release ({t} ET)", d, 1.0, "release", "event", url, fetched))
            if d >= today:                                    # USDA's published schedule (today included: may not be out yet)
                rows.append(ac.row("esmis", f"esmis:{slug}:scheduled", f"{rep['name']} scheduled ({t} ET)", d, 1.0, "release", "event", url, fetched))
    if not rows:
        raise RuntimeError("; ".join(errors) or "no ESMIS releases parsed")
    return ac.frame(rows, errors)
