"""US Drought Monitor (National Drought Mitigation Center, USDA, NOAA): % of area in drought, weekly (public domain;
cite "U.S. Drought Monitor").

Maps are valid as of Tuesday and released Thursday 08:30 ET. The statistics API returns cumulative categories
(D0 = abnormally dry or worse, D1 = moderate drought or worse, ... D4), so D1 is the "in drought" share.

  usdm:<area>:d1   % of area in drought (D1-D4), dated at the map date (Tuesday)
  usdm:<area>:d2   % in severe drought or worse (D2-D4)

Areas: CONUS, plus any states named in the config (postal codes). The state endpoint answered once and then came back
empty on 30 Oct 2026, so the config lists none for now. A reader uses a map from its Thursday release (map date + 2 days).
"""
from __future__ import annotations

import io
from datetime import date

import pandas as pd

from . import ai_common as ac, base

KIND = "obs"
US = "https://usdmdataservices.unl.edu/api/USStatistics/GetDroughtSeverityStatisticsByAreaPercent?aoi=us&startdate={s}&enddate={e}&statisticsType=1"
STATE = "https://usdmdataservices.unl.edu/api/StateStatistics/GetDroughtSeverityStatisticsByAreaPercent?aoi={a}&startdate={s}&enddate={e}&statisticsType=1"
HUMAN = "https://droughtmonitor.unl.edu/"


def parse(text: str, area: str, fetched) -> list[dict]:
    if not text.strip().startswith("MapDate"):
        return []
    df = pd.read_csv(io.StringIO(text))
    if area == "conus" and "AreaOfInterest" in df:      # the US endpoint also returns "Total" (with AK, HI, PR) per date
        df = df[df["AreaOfInterest"].astype(str).str.upper() == "CONUS"]
    rows = []
    for _, r in df.iterrows():
        d = pd.to_datetime(str(r["MapDate"]), format="%Y%m%d").date()
        rows.append(ac.row("usdm", f"usdm:{area}:d1", f"{area.upper()} % area in drought (D1-D4)", d, float(r["D1"]), "pct", "weekly", HUMAN, fetched))
        rows.append(ac.row("usdm", f"usdm:{area}:d2", f"{area.upper()} % area in severe drought or worse (D2-D4)", d, float(r["D2"]), "pct", "weekly", HUMAN, fetched))
    return rows


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    fetched = base.now_utc()
    start = pd.Timestamp(since).date() if since is not None else date.fromisoformat(str(cfg.get("history_from", "2000-01-04")))
    end = date.today()
    fmt = lambda d: f"{d.month}/{d.day}/{d.year}"   # noqa: E731
    rows, errors = [], []
    for area in ["conus"] + [s.lower() for s in cfg.get("states", [])]:
        url = (US if area == "conus" else STATE.replace("{a}", area.upper())).format(s=fmt(start), e=fmt(end))
        try:
            got = parse(ac.get(url, cfg, headers={"User-Agent": ac.BROWSER_UA}).text, area, fetched)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{area}: {type(e).__name__}: {e}"[:200])
            continue
        if not got:
            errors.append(f"{area}: empty answer")
        rows += got
    if not rows:
        raise RuntimeError("; ".join(errors) or "no Drought Monitor rows")
    return ac.frame(rows, errors)
