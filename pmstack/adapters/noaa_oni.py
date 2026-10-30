"""NOAA CPC Oceanic Niño Index (ONI): 3-month running mean of ERSST.v5 SST anomalies in Niño 3.4 (public domain).

  noaa:oni   anomaly in °C, dated at the LAST month of the 3-month season (JAS 2026 -> 2026-09-01)
  noaa:nino34_total   the season's mean SST, °C

El Niño: ONI >= +0.5 for five overlapping seasons; La Niña <= -0.5 (CPC's definition). CPC updates ONI early each
month and revises recent seasons when ERSST is updated, so the store holds the latest values (no vintages). A reader
uses a season from about 10 days after its last month ends.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from . import ai_common as ac, base

KIND = "obs"
URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
SEASONS = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]


def parse(text: str, fetched) -> list[dict]:
    rows = []
    for line in text.splitlines():
        p = line.split()
        if len(p) != 4 or p[0] not in SEASONS:
            continue
        last_month = SEASONS.index(p[0]) + 2            # DJF ends in Feb (2), ..., NDJ ends in Jan of the next year
        yr = int(p[1]) + (1 if last_month > 12 else 0)
        m = (last_month - 1) % 12 + 1
        d = date(yr, m, 1)
        rows.append(ac.row("noaa", "noaa:oni", f"Oceanic Niño Index ({p[0]} {p[1]})", d, float(p[3]), "degC", "monthly", URL, fetched))
        rows.append(ac.row("noaa", "noaa:nino34_total", f"Niño 3.4 mean SST ({p[0]} {p[1]})", d, float(p[2]), "degC", "monthly", URL, fetched))
    return rows


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    fetched = base.now_utc()
    rows = parse(ac.get(URL, cfg, headers={"User-Agent": ac.BROWSER_UA}).text, fetched)
    if not rows:
        raise RuntimeError("ONI file not parsed")
    return ac.frame(rows, [])
