"""World Bank Commodity Price Data (the Pink Sheet), monthly prices from 1960, nominal USD (CC BY 4.0).

One workbook, `CMO-Historical-Data-Monthly.xlsx`, sheet "Monthly Prices": one column per commodity, rows `1960M01`...
The file's address changes with every monthly update, so the link is read from the World Bank commodity-markets page
each run (the configured `url` is the fallback). Published around the second business day of the month for the month
before: a reader uses month M from `lag_days` after M ends (point in time). The World Bank keeps no vintages; values
are rarely revised. Cite "World Bank, Commodity Price Data (The Pink Sheet)" with a link.

  wb:<key>   monthly average price, dated the first of the month
"""
from __future__ import annotations

import io
import re

import pandas as pd

from . import ai_common as ac, base

KIND = "obs"
PAGE = "https://www.worldbank.org/en/research/commodity-markets"
LINK = re.compile(r"https://thedocs\.worldbank\.org/[^\"'\s]*CMO-Historical-Data-Monthly\.xlsx")


def workbook_url(cfg: dict) -> str:
    try:
        m = LINK.search(ac.get(PAGE, cfg, headers={"User-Agent": ac.BROWSER_UA}).text)
        if m:
            return m.group(0)
    except Exception:  # noqa: BLE001  fall back to the configured address
        pass
    return cfg["url"]


def parse(content: bytes, series: list[dict], url: str, fetched) -> tuple[list[dict], list[str]]:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    rows = list(wb["Monthly Prices"].iter_rows(values_only=True))
    hdr_i = next(i for i, r in enumerate(rows) if r and r[1] and "crude oil" in str(r[1]).lower())
    hdr = [str(h or "").strip() for h in rows[hdr_i]]
    units = [str(u or "").strip("() ") for u in rows[hdr_i + 1]]
    out, errors = [], []
    for s in series:
        col = next((i for i, h in enumerate(hdr) if h.lower().startswith(s["column"].lower())), None)
        if col is None:
            errors.append(f"{s['key']}: column {s['column']!r} not found")
            continue
        for r in rows[hdr_i + 2:]:
            m = re.fullmatch(r"(\d{4})M(\d{2})", str(r[0] or ""))
            if not m or col >= len(r):
                continue
            try:
                v = float(r[col])
            except (TypeError, ValueError):                  # '…' = not available
                continue
            out.append(ac.row("pinksheet", f"wb:{s['key']}", f"{hdr[col]} (World Bank Pink Sheet)",
                              f"{m.group(1)}-{m.group(2)}-01", v, units[col] or s.get("unit", ""), "monthly", url, fetched))
    return out, errors


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    fetched = base.now_utc()
    url = workbook_url(cfg)
    content = ac.get(url, cfg, headers={"User-Agent": ac.BROWSER_UA}).content
    rows, errors = parse(content, cfg["series"], url, fetched)
    if since is not None:
        cut = pd.Timestamp(since).date().replace(day=1) - pd.Timedelta(days=400)   # recent revisions too
        known = cfg.get("_known") or set()
        rows = [x for x in rows if x["date"] >= cut or x["series_id"] not in known]   # a new series gets its history
    if not rows:
        raise RuntimeError("; ".join(errors) or "no rows")
    return ac.frame(rows, errors)
