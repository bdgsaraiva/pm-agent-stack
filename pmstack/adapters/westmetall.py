"""LME official prices from Westmetall's public market-data tables (cash settlement, 3-month, LME stock).

PERSONAL USE ONLY, like adapters/yahoo.py and adapters/dramexchange.py: LME prices are licensed market data
(redistribution needs an LME licence). Westmetall shows them on a public page; we store them for Bernardo's own
relative-value marks (COMEX vs LME copper, pmstack/spreads.py). Never use them in a public post (network.py's public
pack uses public-domain series only) and do not port this adapter to the corporate build: use the LME feed there.

  lme:<metal>_cash   LME official cash settlement, USD/t (dated at the LME trading day)
  lme:<metal>_3m     LME official 3-month price, USD/t
  lme:<metal>_stock  LME warehouse stocks, t

The page lists every trading day back to the 2000s in one table per year (newest first). Westmetall is unreachable
from the cloud sandbox: it runs in the data job (GitHub Actions) only, like GDELT.
"""
from __future__ import annotations

import html as htmlmod
import re
from datetime import datetime

import pandas as pd

from . import ai_common as ac, base

KIND = "obs"
URL = "https://www.westmetall.com/en/markdaten.php?action=table&field={field}"
_TR = re.compile(r"<tr\b.*?</tr>", re.S | re.I)
_CELL = re.compile(r"<t([dh])\b[^>]*>(.*?)</t[dh]>", re.S | re.I)
_DATE_FMTS = ("%d. %B %Y", "%d %B %Y", "%d. %b %Y", "%d.%m.%Y", "%Y-%m-%d", "%B %d, %Y")
_GERMAN = {"Januar": "January", "Februar": "February", "März": "March", "Mai": "May", "Juni": "June", "Juli": "July",
           "Oktober": "October", "Dezember": "December"}
# column header words -> our suffix (checked in this order; "stock" before "cash" never collides)
_COLS = (("3-month", "3m"), ("3 month", "3m"), ("3-monat", "3m"), ("stock", "stock"), ("bestand", "stock"),
         ("cash", "cash"), ("kasse", "cash"))


def _text(s: str) -> str:
    return re.sub(r"\s+", " ", htmlmod.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def _date(s: str):
    s = _text(s)
    for de, en in _GERMAN.items():
        s = s.replace(de, en)
    for f in _DATE_FMTS:
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            continue
    return None


def _num(s: str):
    t = _text(s).replace(" ", "").replace(" ", "")
    if not t or t in ("-", "n/a"):
        return None
    if re.fullmatch(r"-?[\d.]+,\d{1,2}", t):            # German style 9.876,50
        t = t.replace(".", "").replace(",", ".")
    else:
        t = t.replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


def parse(page: str, metal: str, url: str, fetched) -> tuple[list[dict], list[str]]:
    """Rows of (date, cash, 3-month, stock). Columns are located from the table headers; without headers the
    Westmetall order (date, cash, 3-month, stock) is assumed."""
    cols: dict[int, str] | None = None
    rows, errors, seen = [], [], 0
    names = {"cash": f"LME {metal.title()} cash settlement (Westmetall)",
             "3m": f"LME {metal.title()} 3-month (Westmetall)", "stock": f"LME {metal.title()} stock (Westmetall)"}
    units = {"cash": "USD/t", "3m": "USD/t", "stock": "t"}
    for m in _TR.finditer(page):
        cells = _CELL.findall(m.group(0))
        if not cells:
            continue
        if all(k.lower() == "h" for k, _ in cells):          # header row: map columns
            heads = [_text(c).lower() for _, c in cells]
            found = {}
            for i, h in enumerate(heads):
                for word, key in _COLS:
                    if word in h and key not in found.values():
                        found[i] = key
                        break
            if found:
                cols = found
            continue
        d = _date(cells[0][1])
        if d is None:
            continue
        seen += 1
        use = cols or {1: "cash", 2: "3m", 3: "stock"}
        for i, key in use.items():
            if i < len(cells):
                v = _num(cells[i][1])
                if v is not None and v > 0:
                    rows.append(ac.row("lme", f"lme:{metal}_{key}", names[key], d, v, units[key], "daily", url, fetched))
    if not rows:
        snippet = _text(page[page.lower().find("<table"):][:400]) if "<table" in page.lower() else _text(page[:300])
        errors.append(f"{metal}: no rows parsed ({seen} dated rows; page starts: {snippet!r})")
    return rows, errors


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    fetched = base.now_utc()
    rows, errors = [], []
    budget = ac.Budget(cfg, 60)
    for it in cfg["metals"]:
        if budget.out():
            errors.append(f"{it['metal']}: skipped (time budget)")
            continue
        url = URL.format(field=it["field"])
        try:
            page = ac.get(url, cfg, headers={"User-Agent": ac.BROWSER_UA}).text
        except Exception as e:  # noqa: BLE001
            errors.append(f"{it['metal']}: {type(e).__name__}: {e}"[:300])
            continue
        r, err = parse(page, it["metal"], url, fetched)
        if since is not None:
            r = [x for x in r if x["date"] >= since]
        rows += r
        errors += err
    if not rows:
        raise RuntimeError("; ".join(errors) or "no rows")
    return ac.frame(rows, errors)
