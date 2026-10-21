"""DRAMeXchange (TrendForce) memory spot prices from the public home page: today's session average only.

PERSONAL USE ONLY, like adapters/yahoo.py: TrendForce's terms forbid reproducing or redistributing the site's
material without consent, and history is for paying members (the chart pop-up asks for a login). We store one
number per item per update, for Bernardo's own note; never use it in a public post (network.py's public pack uses
public-domain series only) and do not port it to the corporate build.

  dx:<slug>   session average, USD (chips per unit, modules per module), dated at the table's "Last Update" (Taipei)

DRAM spot is daily on Taiwan business days; module spot is weekly. Spot leads contract prices but is a thin, retail
market: read it as the direction of memory tightness, not as the price hyperscalers pay (that is HBM and contract).
"""
from __future__ import annotations

import html as htmlmod
import re
from datetime import datetime

import pandas as pd

from . import ai_common as ac, base

KIND = "obs"
URL = "https://www.dramexchange.com/"
_TR = re.compile(r"<tr\b.*?</tr>", re.S | re.I)
_TD = re.compile(r"<td\b[^>]*>(.*?)</td>", re.S | re.I)
_UPD = re.compile(r"Last\s+Update:?\s*([A-Z][a-z]{2})\.?\s*(\d{1,2})\s+(\d{4})", re.I)


def _text(s: str) -> str:
    return re.sub(r"\s+", " ", htmlmod.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def _num(s: str):
    try:
        return float(_text(s).replace(",", ""))
    except ValueError:
        return None


def parse(page: str, items: list[dict], fetched) -> tuple[list[dict], list[str]]:
    """Session average of each configured item, dated at the nearest preceding 'Last Update'."""
    ups = [(m.start(), datetime.strptime(f"{m.group(1)[:3].title()} {m.group(2)} {m.group(3)}", "%b %d %Y").date())
           for m in _UPD.finditer(page)]
    found, rows, errors = {}, [], []
    for m in _TR.finditer(page):
        tds = _TD.findall(m.group(0))
        if len(tds) < 6:
            continue
        label = _text(tds[0])
        for it in items:
            if it["slug"] in found or label != it["label"]:
                continue
            avg = _num(tds[int(it.get("avg_col", 5))])
            when = [d for pos, d in ups if pos < m.start()]
            if avg is None or not when:
                errors.append(f"{it['label']}: row found but no session average or update date")
                continue
            found[it["slug"]] = True
            rows.append(ac.row("dramexchange", f"dx:{it['slug']}", f"{it['label']} spot, session average", when[-1],
                               avg, "USD", it.get("freq", "daily"), URL, fetched))
    errors += [f"{it['label']}: not on the page (layout changed?)" for it in items if it["slug"] not in found]
    return rows, errors


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    fetched = base.now_utc()
    page = ac.get(cfg.get("url", URL), cfg, headers={"User-Agent": ac.BROWSER_UA}).text
    rows, errors = parse(page, cfg["items"], fetched)
    if not rows:
        raise RuntimeError("; ".join(errors) or "no rows")
    return ac.frame(rows, errors)
