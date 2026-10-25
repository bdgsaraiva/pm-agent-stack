"""Shanghai Futures Exchange weekly warehouse stocks (copper, aluminium, gold), every Friday ~15:20 Beijing time.

PERSONAL USE ONLY, like adapters/westmetall.py: SHFE publishes the weekly stock report on its public site; we store
the national totals for Bernardo's own research (the Metals specialist). Never use them in a public post.

  shfe:<metal>_stock     total stock of deliverable quality (总计 小计), t    (cu, al)
  shfe:<metal>_warrants  of which on warrant (总计 期货), t                    (cu, al)
  shfe:au_warrants       gold on warrant, kg

Dated at the report day (the week's last trading day, usually Friday; SHFE's own `o_tradingday`). Two formats:
  - JSON  /data/tradedata/future/weeklydata/<YYYYMMDD>weeklystock.dat        (about 2014 to 14 Nov 2025)
  - HTML  /data/tradedata/future/stockdata/weeklystock_<YYYYMMDD>/ZH/all.html (from 21 Nov 2025)
A week whose Friday is a Chinese holiday is reported on the last trading day before it: the adapter tries Friday,
then Thursday back to Monday. Reachability from GitHub Actions is checked on the first run (fetch:shfe in the log).
"""
from __future__ import annotations

import html as htmlmod
import json
import re
from datetime import date, timedelta

import pandas as pd

from . import ai_common as ac, base

KIND = "obs"
SITE = "https://www.shfe.com.cn"
DAT = SITE + "/data/tradedata/future/weeklydata/{d}weeklystock.dat"
HTML = SITE + "/data/tradedata/future/stockdata/weeklystock_{d}/ZH/all.html"
NAMES = {"cu": ("铜", "Copper"), "al": ("铝", "Aluminium")}


def parse_dat(js: dict) -> dict[str, float]:
    out = {}
    for r in js.get("o_cursor") or []:
        varid = (r.get("VARID") or "").strip().lower() or {"铜": "cu", "铝": "al"}.get(str(r.get("VARNAME", "")).split("$$")[0])
        if varid in NAMES and str(r.get("WHABBRNAME", "")).split("$$")[0].strip() == "总计":
            out[f"{varid}_stock"] = float(r["SPOTWGHTS"])
            out[f"{varid}_warrants"] = float(r["WRTWGHTS"])
    au = (js.get("o_cursorau") or [{}])[0]
    if au.get("WRTWGHTS") is not None:
        out["au_warrants"] = float(au["WRTWGHTS"])
    return out


def _tokens(page: str) -> list[str]:
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S | re.I)
    t = htmlmod.unescape(re.sub(r"<[^>]+>", "|", t))
    return [x.strip() for x in t.split("|") if x.strip()]


def _n(s: str):
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def parse_html(page: str) -> dict[str, float]:
    """Sections start with '<metal> | 单位：吨'. In a copper or aluminium section the row '总计' (all regions, bonded
    included) reads: last week 小计, 期货; this week 小计, 期货; change 小计, 期货. Gold: '黄金 | 单位：千克 | last | this | change'."""
    tok = _tokens(page)
    out = {}
    heads = [i for i in range(len(tok) - 1) if tok[i + 1].startswith("单位")]
    for k, i in enumerate(heads):
        end = heads[k + 1] if k + 1 < len(heads) else len(tok)
        name = tok[i]
        if name == "黄金" and i + 4 < len(tok):
            v = _n(tok[i + 3])
            if v is not None:
                out["au_warrants"] = v
            continue
        varid = next((v for v, (zh, _) in NAMES.items() if zh == name), None)
        if not varid:
            continue
        for j in range(i, end):
            if tok[j] == "总计":
                nums = [_n(x) for x in tok[j + 1:j + 7]]
                if len(nums) == 6 and None not in nums:
                    out[f"{varid}_stock"], out[f"{varid}_warrants"] = nums[2], nums[3]
    return out


def _fridays(start: date, end: date) -> list[date]:
    d = start + timedelta(days=(4 - start.weekday()) % 7)
    out = []
    while d <= end:
        out.append(d)
        d += timedelta(days=7)
    return out


def one_week(friday: date, cfg: dict) -> tuple[date | None, dict, str | None]:
    """The report for the week of `friday`: (report day, values, url), trying Friday back to Monday."""
    for back in range(5):
        d = friday - timedelta(days=back)
        ds = d.strftime("%Y%m%d")
        for url, kind in ((HTML.format(d=ds), "html"), (DAT.format(d=ds), "dat")) if d >= date(2025, 11, 15) else \
                ((DAT.format(d=ds), "dat"), (HTML.format(d=ds), "html")):
            try:
                r = ac.get(url, cfg, headers={"User-Agent": ac.BROWSER_UA})
            except Exception:  # noqa: BLE001  404 = no report that day
                continue
            r.encoding = "utf-8"
            try:
                vals = parse_dat(json.loads(r.text)) if kind == "dat" else parse_html(r.text)
            except ValueError:
                continue
            if vals:
                return d, vals, url
    return None, {}, None


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    fetched = base.now_utc()
    budget = ac.Budget(cfg, 120)
    today = (pd.Timestamp.now(tz="Asia/Shanghai")).date()
    start = since if since is not None else date.fromisoformat(str(cfg.get("backfill_start", "2014-01-01")))
    weeks = _fridays(start, today)
    weeks.reverse()                                        # newest first: a budget cut leaves the oldest for next run
    rows, errors, misses = [], [], 0
    units = {"stock": "t", "warrants": "t"}
    for fri in weeks:
        if budget.out():
            errors.append(f"time budget: stopped at week of {fri} (older weeks next run)")
            break
        d, vals, url = one_week(fri, cfg)
        if not vals:
            misses += 1
            if since is None and misses >= int(cfg.get("stop_after_misses", 12)):
                break                                      # before the first report: stop walking back
            continue
        misses = 0
        for key, v in vals.items():
            metal, kind = key.split("_")
            label = {"cu": "Copper", "al": "Aluminium", "au": "Gold"}[metal]
            unit = "kg" if metal == "au" else units[kind]
            what = "on warrant" if kind == "warrants" else "stock (deliverable quality)"
            rows.append(ac.row("shfe", f"shfe:{key}", f"SHFE {label} {what}, weekly", d, v, unit, "weekly", url, fetched))
    if not rows and since is None:
        raise RuntimeError("; ".join(errors) or "no SHFE weekly report found")
    return ac.frame(rows, errors)
