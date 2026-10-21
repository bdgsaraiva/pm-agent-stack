"""US Census Bureau construction spending (C30, "Value of Construction Put in Place"): private, seasonally adjusted
annual rate, from the public-domain time-series workbook (no key; the Census API now asks for one, the file does not).

Data centres are their own category since the July 2024 release (before, inside Office); they come from the
Construction Progress Reporting Survey and are revised for months after first print (latest fetch wins; `p` and `r`
marks in the file = preliminary and revised). Released ~1st business day of M+2, dated at the reference month.

  census:<slug>   SAAR, USD millions (columns chosen by their header label in config)

The workbook is parsed with the standard library (no openpyxl in requirements).
"""
from __future__ import annotations

import io
import re
import zipfile
from datetime import datetime
from xml.etree import ElementTree as ET

import pandas as pd

from . import ai_common as ac, base

KIND = "obs"
URL = "https://www.census.gov/construction/c30/xlsx/privsatime.xlsx"
PAGE = "https://www.census.gov/construction/c30/c30index.html"
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def sheet_rows(blob: bytes) -> list[dict[str, str]]:
    """First worksheet of an .xlsx as a list of {column letter: text}."""
    z = zipfile.ZipFile(io.BytesIO(blob))
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(f"{_NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{_NS}t")))
    name = sorted(n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n))[0]
    out = []
    for r in ET.fromstring(z.read(name)).iter(f"{_NS}row"):
        row = {}
        for c in r.iter(f"{_NS}c"):
            col = re.match(r"[A-Z]+", c.get("r", "")).group(0)
            v = c.find(f"{_NS}v")
            if v is not None and v.text is not None:
                row[col] = shared[int(v.text)] if c.get("t") == "s" else v.text
            else:
                inline = c.find(f"{_NS}is")
                if inline is not None:
                    row[col] = "".join(t.text or "" for t in inline.iter(f"{_NS}t"))
        out.append(row)
    return out


def _month(s: str):
    m = re.match(r"^([A-Z][a-z]{2})-(\d{2})[pr]?$", str(s).strip())
    return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%b %y").date() if m else None


def _label(s: str) -> str:
    return re.sub(r"\d+$", "", re.sub(r"\s+", " ", str(s).replace("_x000D_", " "))).strip().lower()


def records(blob: bytes, cfg: dict, fetched) -> tuple[list[dict], list[str]]:
    rows = sheet_rows(blob)
    head = next((r for r in rows if str(r.get("A", "")).strip() == "Date"), None)
    if head is None:
        return [], ["header row 'Date' not found"]
    cols, errors = {}, []
    for s in cfg["series"]:
        col = next((k for k, v in head.items() if _label(v) == s["column"].lower()), None)
        if col is None:
            errors.append(f"column '{s['column']}' not found")
        else:
            cols[s["slug"]] = (col, s)
    out = []
    for r in rows:
        d = _month(r.get("A", ""))
        if d is None:
            continue
        for slug, (col, s) in cols.items():
            try:
                v = float(str(r.get(col, "")).replace(",", ""))
            except ValueError:
                continue
            out.append(ac.row("census_c30", f"census:{slug}", s["name"], d, v, "USD mn SAAR", "monthly", PAGE, fetched))
    return out, errors


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    fetched = base.now_utc()
    blob = ac.get(cfg.get("url", URL), cfg, headers={"User-Agent": ac.BROWSER_UA}).content
    rows, errors = records(blob, cfg, fetched)
    if not rows:
        raise RuntimeError("; ".join(errors) or "no rows")
    if since is not None:
        rows = [r for r in rows if r["date"] >= since]
    return ac.frame(rows, errors)
