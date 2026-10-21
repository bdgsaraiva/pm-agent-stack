"""Korea Customs Service (관세청) export releases: the 1-10 and 1-20 day early prints and the monthly final, from the
KCS press-release board (public, no key; KOGL type 1 "출처표시": free reuse with attribution, cite "Korea Customs
Service"). Korean semiconductor exports are the first hard print of the memory and AI-server chip cycle each month.

Each release is a page (summary text) plus a PDF (the full text: item table commentary). Read, as first published:
  kcs:exports:<kind>        total exports in the window, USD bn
  kcs:exports_yoy:<kind>    vs the same window a year earlier, %
  kcs:chips:<kind>          semiconductor exports, USD bn (stated in the release; else share x total, marked "derived")
  kcs:chips_yoy:<kind>      semiconductor exports vs a year earlier, %
  kcs:chips_share:<kind>    semiconductors' share of exports, %
kind: d10 (1st-10th), d20 (1st-20th), m (monthly final, ~15th). The 1st-of-month preliminary is skipped: KCS's
version states no chip figure (MOTIE's joint release has it, in a different format).
Dated at the release day (point in time); the window is in `name`. Like-for-like comparison = the previous print of
the same kind (last month's same window). Early prints swing with working days (the release states them).
"""
from __future__ import annotations

import io
import os
import re
import time
from datetime import date

import pandas as pd
import requests

from . import ai_common as ac, base

KIND = "obs"
BASE = "https://www.customs.go.kr"
LIST = BASE + "/kcs/na/ntt/selectNttList.do"
INFO = BASE + "/kcs/na/ntt/selectNttInfo.do"
BOARD = {"mi": "2891", "bbsId": "1362"}
PAGE = LIST + "?mi=2891&bbsId=1362"

_ITEM = re.compile(r'data-id="(\d+)"\s+data-url="([0-9a-f]+)"\s+class="nttInfoBtn"\s+title="([^"]*)"')
_DATE = re.compile(r'data-table="date">\s*(\d{4})\.(\d{2})\.(\d{2})')
_PDF = re.compile(r'href="(/common/nttFileDownload\.do\?fileKey=[0-9a-f]+)"\s+title="[^"]*\.pdf')
_MON = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}


def classify(title: str):
    """(kind, year, month, window label) for an export release title, else None."""
    t = re.sub(r"\s+", "", title)
    m = re.match(r"(\d{4})년(\d{1,2})월1일~\d{1,2}월(10|20)일수출입현황", t)
    if m:
        y, mo, end = int(m.group(1)), int(m.group(2)), m.group(3)
        return f"d{end}", y, mo, f"1-{end} {_MON[mo]} {y}"
    m = re.match(r"(\d{4})년(\d{1,2})월월간수출입현황\[확정치\]", t)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        return "m", y, mo, f"{_MON[mo]} {y} final"
    return None             # the 1st-of-month preliminary ("<month> 수출입 현황 [잠정치]") states no chip figure: skipped


def items(list_html: str) -> list[dict]:
    """Board rows: id, url key, title, posting date (each item's date cell follows its link)."""
    out = []
    marks = list(_ITEM.finditer(list_html))
    for i, m in enumerate(marks):
        stop = marks[i + 1].start() if i + 1 < len(marks) else len(list_html)
        d = _DATE.search(list_html, m.end(), stop)
        out.append({"id": m.group(1), "key": m.group(2), "title": m.group(3),
                    "date": date(int(d.group(1)), int(d.group(2)), int(d.group(3))) if d else None})
    return out


def _f(s: str) -> float:
    return float(s.replace(",", ""))


def _signed(v: float, neg_mark: str | None, word: str | None = None) -> float:
    return -v if (neg_mark == "△" or word == "감소") else v


def parse(text: str) -> dict:
    """Figures from a release's text (page summary + PDF). Whitespace is removed first: the PDF spaces letters out."""
    t = re.sub(r"\s+", "", text)
    out = {}
    m = re.search(r"수출은([\d,.]+)억달러로전년동(?:기|월)대비(△)?([\d.]+)%(증가|감소)", t)
    if m:
        out["exports"], out["exports_yoy"] = _f(m.group(1)) / 10, _signed(_f(m.group(3)), m.group(2), m.group(4))
    else:
        m = re.search(r"수출은(△)?([\d.]+)%(증가|감소)한([\d,.]+)억달러", t)
        if m:
            out["exports"], out["exports_yoy"] = _f(m.group(4)) / 10, _signed(_f(m.group(2)), m.group(1), m.group(3))
    m = re.search(r"반도체(?:수출)?\(([\d,.]+)억달러\)", t)
    if m:
        out["chips"] = _f(m.group(1)) / 10
    m = re.search(r"반도체\((?:전년동(?:기|월)대비(?:증감률)?)?(△)?([\d.]+)%\)", t)
    if m:
        out["chips_yoy"] = _signed(_f(m.group(2)), m.group(1))
    m = re.search(r"반도체수출비중은([\d.]+)%", t)
    if m:
        out["chips_share"] = _f(m.group(1))
    if "chips" not in out and "chips_share" in out and "exports" in out:
        out["chips"], out["chips_derived"] = out["exports"] * out["chips_share"] / 100, True
    return out


LABELS = {"exports": ("Korea exports", "USD bn"), "exports_yoy": ("Korea exports y/y", "%"),
          "chips": ("Korea chip exports", "USD bn"), "chips_yoy": ("Korea chip exports y/y", "%"),
          "chips_share": ("Korea chip share of exports", "%")}


def records(fig: dict, kind: str, window: str, released: date, fetched) -> list[dict]:
    out = []
    for k, (label, unit) in LABELS.items():
        if fig.get(k) is None:
            continue
        name = f"{label}, {window}" + (" (derived: share x total)" if k == "chips" and fig.get("chips_derived") else "")
        out.append(ac.row("kcs", f"kcs:{k}:{kind}", name, released, round(fig[k], 3), unit,
                          "event", PAGE, fetched))
    return out


def _pdf_text(blob: bytes) -> str:
    import pypdf
    return "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(io.BytesIO(blob)).pages)


def _page_text(html: str) -> str:
    x = re.sub(r"<(script|style).*?</\1>", " ", html, flags=re.S | re.I)
    i = x.find("요 약")
    return re.sub(r"<[^>]+>", " ", x[i:] if i >= 0 else x)


def _call(s: requests.Session, method: str, url: str, tries: int, **kw) -> requests.Response:
    """The KCS server drops connections now and then (RemoteDisconnected): retry, short pauses."""
    last = None
    for i in range(tries):
        try:
            r = s.request(method, url, **kw)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = e
            if i < tries - 1 and not os.environ.get("PMSTACK_NO_PAUSE"):
                time.sleep(3 * (i + 1))
    raise last  # type: ignore[misc]


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    fetched, rows, errors, budget = base.now_utc(), [], [], ac.Budget(cfg, 120)
    timeout, tries = int(cfg.get("timeout_s", 30)), int(cfg.get("tries", 3))
    s = requests.Session()
    s.headers.update({"User-Agent": ac.BROWSER_UA})
    last = cfg.get("_last") or {}
    pages = int(cfg.get("pages", 2) if since else cfg.get("backfill_pages", 8))
    found = []
    for p in range(1, pages + 1):
        if budget.out():
            errors.append(f"time budget reached at list page {p}")
            break
        try:
            r = _call(s, "GET", LIST, tries, params={**BOARD, "currPage": p}, timeout=timeout)
            found += items(r.text)
        except Exception as e:  # noqa: BLE001
            errors.append(f"list page {p}: {type(e).__name__}: {e}")
            break
    todo = []
    for it in found:
        c = classify(it["title"])
        if c is None or it["date"] is None:
            continue
        kind = c[0]
        done = last.get(f"kcs:exports:{kind}")
        if done is not None and it["date"] <= done:
            continue                                    # already stored (prints are kept as first published)
        todo.append((it, c))
    for it, (kind, _, _, window) in sorted(todo, key=lambda x: x[0]["date"], reverse=True):
        if budget.out():
            errors.append(f"time budget reached before {window}; the rest follows next run")
            break
        try:
            r = _call(s, "POST", INFO, tries, data={**BOARD, "nttSn": it["id"], "nttSnUrl": it["key"]}, timeout=timeout)
            text = _page_text(r.text)
            pdf = _PDF.search(r.text)
            if pdf:
                b = _call(s, "GET", BASE + pdf.group(1), tries, headers={"Referer": INFO}, timeout=timeout * 2)
                if b.content[:5] == b"%PDF-":
                    text += "\n" + _pdf_text(b.content)
            fig = parse(text)
            if "exports" not in fig:
                errors.append(f"{window}: exports not found in the release text")
                continue
            if "chips" not in fig and "chips_yoy" not in fig:
                errors.append(f"{window}: no semiconductor figure found")
            rows += records(fig, kind, window, it["date"], fetched)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{window}: {type(e).__name__}: {e}")
    if not rows and errors:
        raise RuntimeError("; ".join(errors))
    return ac.frame(rows, errors)
