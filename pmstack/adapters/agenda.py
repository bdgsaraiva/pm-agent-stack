"""Forward calendar for the morning note's watching ladder (20 Oct 2026, Bernardo).

- Economic releases, central-bank decisions and speakers: Forex Factory's weekly calendar JSON (this week and next;
  free, no key; impact High / Medium / Low as Forex Factory rates it). Times are converted to UTC.
- Earnings of the watchlist in config/calendar.yaml: Nasdaq's public earnings calendar, one call per day ahead
  (US listings and ADRs only; Asian listings such as Samsung or SK Hynix go in config/events.yaml by hand).

Stored as text rows (source `agenda`): title, a link, published = the event time (UTC; date-only events at 00:00),
summary = "kind=...;country=...;impact=...;time=...;forecast=...;previous=..." (no article text). Each fetch is stored
under its own item id, so the pack reads the latest fetch of each event (forecasts and times can move).
"""
from __future__ import annotations

import hashlib
from datetime import timedelta

import pandas as pd

from . import base

KIND = "text"
BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
           "Accept": "application/json, text/plain, */*"}
FF_PAGE = "https://www.forexfactory.com/calendar"
NASDAQ_PAGE = "https://www.nasdaq.com/market-activity/earnings"


def _id(*parts) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


def _summary(**kw) -> str:
    return ";".join(f"{k}={'' if v is None else str(v).replace(';', ',')}" for k, v in kw.items())


def _ff(url: str, fetched) -> list[dict]:
    rows = []
    for e in base.get_json(url, headers=BROWSER):
        ts = pd.to_datetime(e.get("date"), utc=True, errors="coerce")
        if pd.isna(ts):
            continue
        rows.append({"title": e.get("title", ""), "url": FF_PAGE, "published": ts,
                     "summary": _summary(kind="macro", country=e.get("country"), impact=e.get("impact"),
                                         time="timed", forecast=e.get("forecast"), previous=e.get("previous")),
                     "key": ("macro", e.get("country"), e.get("title"), ts.isoformat())})
    return rows


def _nasdaq(day, watch: dict[str, str]) -> list[dict]:
    js = base.get_json("https://api.nasdaq.com/api/calendar/earnings", params={"date": str(day)}, headers=BROWSER)
    rows = []
    for r in ((js.get("data") or {}).get("rows") or []):
        sym = (r.get("symbol") or "").upper()
        if sym not in watch:
            continue
        when = {"time-pre-market": "before the US open", "time-after-hours": "after the US close"}.get(r.get("time"), "time not given")
        rows.append({"title": f"{watch[sym]} ({sym}) earnings", "url": f"https://www.nasdaq.com/market-activity/stocks/{sym.lower()}/earnings",
                     "published": pd.Timestamp(str(day), tz="UTC"),
                     "summary": _summary(kind="earnings", country="US", impact="watchlist", time=when,
                                         forecast=r.get("epsForecast"), previous=r.get("lastYearEPS")),
                     "key": ("earnings", sym, str(day))})
    return rows


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    fetched = base.now_utc()
    rows, errors = [], []
    for url in cfg.get("ff_urls", []):
        try:
            rows += _ff(url, fetched)
        except Exception as e:  # next week's file appears late in the week; a miss is not an error
            errors.append(f"forexfactory {url.rsplit('/', 1)[-1]}: {e}") if "thisweek" in url else None
    watch = {s.upper(): n for s, n in (cfg.get("watchlist") or {}).items()}
    today = fetched.date()
    for i in range(int(cfg.get("earnings_days_ahead", 12))):
        day = today + timedelta(days=i)
        if day.weekday() >= 5:
            continue
        try:
            rows += _nasdaq(day, watch)
        except Exception as e:
            errors.append(f"nasdaq earnings {day}: {e}")
    out = pd.DataFrame([{"source": "agenda", "item_id": _id(*r["key"], fetched.date()), "title": r["title"],
                         "url": r["url"], "published": r["published"], "summary": r["summary"], "fetched_at": fetched}
                        for r in rows])
    out.attrs["errors"] = [e for e in errors if e]
    return out
