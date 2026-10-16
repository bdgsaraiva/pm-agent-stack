"""USDA WASDE as first published: one machine-readable CSV per report (USDA OCE "Historical WASDE Report Data").

No key. Values are as published that month (never revised), so a month-on-month change is the report's own
revision and the file is a vintage store (docs/research/balance.md). Each file also carries USDA's reliability
table for that month's projections (average and largest miss vs final, root mean square error, years above/below
final): the surprise is shown beside USDA's own typical error, never against an invented variance.

Rows kept: configured commodities and attributes, every region (United States, World, Foreign, countries).
  wasde:<commodity>:<region>:<attribute>:<market year>     date = release date, value as published
  wasde_rel:<commodity>:<region>:<attribute>:<statistic>  date = release date (the month's reliability table)
www.usda.gov answers some clients with HTTP 403; the usda.azureedge.us mirror serves the same files.
"""
from __future__ import annotations

import io
import re
import time
from datetime import date

import pandas as pd

from . import base

KIND = "obs"
HOSTS = ["https://www.usda.gov", "https://usda.azureedge.us"]
PATH = "/sites/default/files/documents/oce-wasde-report-data-{ym}{v}.csv"
PAGE = "https://www.usda.gov/oce/commodity/wasde"
BOM = chr(0xFEFF)


def slug(s) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")


def _months(start: date, end: date) -> list[str]:
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


LAST_ERRORS: list[str] = []


def _get_csv(ym: str, timeout: int) -> tuple[str | None, str | None]:
    """The report's CSV text and URL: the original file, else a corrected one (-V2); usda.gov, then the mirror."""
    for host in HOSTS:
        for v in ("", "-V2"):     # the original is what was first published; -V2 only when it is all there is
            url = host + PATH.format(ym=ym, v=v)
            try:
                r = base.SESSION.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 (pm-agent-stack research)"})
            except Exception as e:  # noqa: BLE001
                LAST_ERRORS.append(f"{ym} {host}: {type(e).__name__}")
                continue
            if r.status_code not in (200, 404):
                LAST_ERRORS.append(f"{ym} {host}{v}: HTTP {r.status_code}")
            if r.status_code == 200 and r.text.lstrip(BOM + ' "' + chr(9) + chr(13) + chr(10)).lower().startswith("wasdenumber"):
                return r.text, url
    return None, None


def parse(text: str, url: str, cfg: dict, fetched=None) -> pd.DataFrame:
    """One report's CSV -> obs rows (configured commodities and attributes only)."""
    df = pd.read_csv(io.StringIO(text.lstrip(BOM)), dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    want_c = {c.lower(): k for k, c in ((k, v["commodity"]) for k, v in cfg["commodities"].items())}
    attrs = {a.lower() for a in cfg["attributes"]}
    df = df[df["Commodity"].str.strip().str.lower().isin(want_c) & df["Attribute"].str.strip().str.lower().isin(attrs)]
    # US rows only from the U.S. tables (domestic units): the world tables repeat the US in metric tons under the
    # same attribute names, which would collide on one series id
    rel0 = df["ReliabilityProjection"].str.strip()
    df = df[(rel0 != "") | (df["Region"].str.strip() != "United States") | df["ReportTitle"].str.strip().str.startswith("U.S.")]
    if df.empty:
        return pd.DataFrame()
    rel = df["ReliabilityProjection"].str.strip()
    when = pd.to_datetime(df["ReleaseDate"].str.strip(), errors="coerce")
    when = when.fillna(pd.to_datetime(df["ReportDate"].str.strip(), format="%B %Y", errors="coerce"))
    key = df["Commodity"].str.strip().str.lower().map(want_c)
    reg, att = df["Region"].map(slug), df["Attribute"].map(slug)
    sid = ("wasde:" + key + ":" + reg + ":" + att + ":" + df["MarketYear"].str.strip()).where(rel == "",
           "wasde_rel:" + key + ":" + reg + ":" + att + ":" + rel.map(slug))
    flag = df["ProjEstFlag"].str.strip().str.strip("()").str.lower().replace({"": "final"})
    out = pd.DataFrame({
        "source": "wasde", "series_id": sid,
        "name": (df["Commodity"].str.strip() + " " + df["Region"].str.strip() + " " + df["Attribute"].str.strip() + " "
                 + df["MarketYear"].str.strip() + " (" + flag.where(rel == "", rel) + ")").str.replace(r"\s+", " ", regex=True),
        "date": when.dt.date, "value": pd.to_numeric(df["Value"].str.replace(",", ""), errors="coerce"),
        "unit": df["Unit"].str.strip(), "freq": "monthly", "source_url": url, "fetched_at": fetched or base.now_utc()})
    return out.dropna(subset=["date", "value"]).drop_duplicates(["series_id", "date"], keep="last")


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    """Reports from `since` (or backfill_start) to this month, within `budget_s` seconds; missing months
    (no report, e.g. the October 2025 shutdown) are skipped and reported."""
    start = pd.Timestamp(since or cfg.get("backfill_start", "2021-01-01")).date().replace(day=1)
    t0, frames, errors, missing = time.monotonic(), [], [], []
    for ym in _months(start, date.today()):
        if time.monotonic() - t0 > float(cfg.get("budget_s", 240)):
            errors.append(f"time budget reached before {ym}; the rest follows next run")
            break
        LAST_ERRORS.clear()
        text, url = _get_csv(ym, int(cfg.get("timeout_s", 30)))
        if text is None:          # no report that month (shutdown) or not released yet: a note, not an error...
            if LAST_ERRORS:       # ...unless a host answered with an error (review A12: failures were silent)
                errors.append(f"{ym}: " + "; ".join(LAST_ERRORS)[:200])
            else:
                missing.append(ym)
            continue
        try:
            frames.append(parse(text, url, cfg))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{ym}: {type(e).__name__}: {e}")
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    out.attrs["errors"] = errors
    if missing:
        out.attrs["notes"] = f"no file for {', '.join(missing)}"
    return out
