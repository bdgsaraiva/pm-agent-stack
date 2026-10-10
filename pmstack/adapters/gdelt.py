"""GDELT DOC 2.0 API: daily news volume (and the total monitored, `norm`) and average tone per narrative query.

Free, keyless; terms allow any use with a citation and link (https://www.gdeltproject.org/about.html).
Timeline modes cover 1 Jan 2017 onward; we keep our own history in Parquet so we never depend on the
API's lookback. Evidence and caveats: docs/research/consensus.md.

Rows written per query and day (complete UTC days only):
  gdelt:<qid>:count   matching articles
  gdelt:<qid>:share   matching / all monitored articles, in % (the attention share)
  gdelt:<qid>:tone    average tone of matching articles (general dictionary; compare only with its own history)
  gdelt:norm          all articles GDELT monitored that day (one series, from the first query)
"""
from __future__ import annotations

import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

import pandas as pd

from . import base

KIND = "obs"
API = "https://api.gdeltproject.org/api/v2/doc/doc"
HUMAN = "https://api.gdeltproject.org/api/v2/doc/doc?query={q}&mode={mode}"


def _pause(cfg: dict) -> None:
    if os.environ.get("PMSTACK_NO_PAUSE"):
        return
    time.sleep(float(cfg.get("pause_seconds", 5)))


def _call(cfg: dict, query: str, mode: str, start: date, end: date, deadline: float | None = None) -> list[dict]:
    """One timeline call. GDELT answers rate-limit breaches with plain text, so parse defensively and back off;
    one HTTP try per attempt (base.get's own retries would stack on ours), no sleep after the last attempt, and
    never past the source's deadline (agent 7 review, finding 4)."""
    params = {"query": query, "mode": mode, "format": "json",
              "startdatetime": f"{start:%Y%m%d}000000", "enddatetime": f"{end:%Y%m%d}235959"}
    last = None
    tries = int(cfg.get("tries", 3))
    for i in range(tries):
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError("GDELT time budget used up")
        _pause(cfg)
        try:
            txt = base.get_text(API, params=params, timeout=60, tries=1)
            js = json.loads(txt) if txt.strip().startswith("{") else None
            if js is None:
                raise ValueError(f"non-JSON reply: {txt[:120]!r}")
            tl = js.get("timeline") or []
            return tl[0].get("data", []) if tl else []
        except Exception as e:  # noqa: BLE001
            last = e
            if i < tries - 1 and not os.environ.get("PMSTACK_NO_PAUSE"):
                time.sleep(10 * (i + 1))
    raise RuntimeError(f"GDELT {mode} failed for {query[:60]!r}: {last}")


def _day(s) -> date | None:
    s = str(s)
    try:
        return datetime.strptime(s[:8], "%Y%m%d").date()
    except ValueError:
        return None


def _by_day(points: list[dict], end: date, how: str) -> dict[date, dict]:
    """One value per UTC day even if the API returns finer points: counts and norms are summed, tone averaged."""
    out: dict[date, dict] = {}
    for p in points:
        d = _day(p.get("date"))
        if d is None or d > end or p.get("value") is None:
            continue
        r = out.setdefault(d, {"value": 0.0, "norm": 0.0, "n": 0, "has_norm": False})
        if how == "sum":
            r["value"] += float(p["value"])
            if p.get("norm"):
                r["norm"] += float(p["norm"])
                r["has_norm"] = True
        else:
            r["value"] += float(p["value"])
        r["n"] += 1
    if how == "mean":
        for r in out.values():
            r["value"] /= r["n"]
    return out


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    fetched = base.now_utc()
    end = (datetime.now(timezone.utc) - timedelta(days=1)).date()   # complete UTC days only
    full_start = date.fromisoformat(cfg.get("backfill_start", "2017-01-01"))
    overlap = int(cfg.get("overlap_days", 10))
    budget = float(cfg.get("max_minutes", 8)) * 60
    deadline = time.monotonic() + budget
    max_fail = int(cfg.get("max_consecutive_failures", 2))
    rows, errors, norm_done, fails = [], [], False, 0
    known = cfg.get("_known")
    last_dates = cfg.get("_last") or {}
    qs = cfg["queries"]
    for i, q in enumerate(qs):
        qid = f"{q['id']}"
        if time.monotonic() > deadline:
            errors.append(f"time budget ({budget / 60:.0f} min) used up; skipped {len(qs) - i} queries "
                          f"({', '.join(x['id'] for x in qs[i:])}); they catch up on the next run")
            break
        if fails >= max_fail:
            errors.append(f"{fails} queries failed in a row (rate limit?); skipped {len(qs) - i} queries; "
                          "they catch up on the next run")
            break
        # each query restarts from its own last stored day, so one failing for days leaves no hole; a query
        # with no stored counts gets its full history (keyed on counts, which exist even when norm is missing)
        last = last_dates.get(f"gdelt:{qid}:count")
        if since is None or (known is not None and f"gdelt:{qid}:count" not in known):
            start = full_start
        elif last is not None:
            start = max(full_start, last - timedelta(days=overlap))
        else:
            start = max(full_start, since)
        url_q = quote(q["query"], safe="")
        try:
            vol = _by_day(_call(cfg, q["query"], "timelinevolraw", start, end, deadline), end, "sum")
            tone = _by_day(_call(cfg, q["query"], "timelinetone", start, end, deadline), end, "mean")
            fails = 0
        except Exception as e:  # one failing query must not stop the others
            errors.append(f"{qid}: {e}")
            fails += 1
            continue
        for d, p in sorted(vol.items()):
            base_row = {"source": "gdelt", "date": d, "freq": "daily", "fetched_at": fetched,
                        "source_url": HUMAN.format(q=url_q, mode="timelinevolraw")}
            rows.append({**base_row, "series_id": f"gdelt:{qid}:count", "name": f"{q['name']} (articles)",
                         "value": p["value"], "unit": "articles"})
            if p["has_norm"] and p["norm"] > 0:
                rows.append({**base_row, "series_id": f"gdelt:{qid}:share", "name": f"{q['name']} (share of coverage)",
                             "value": 100.0 * p["value"] / p["norm"], "unit": "pct"})
                if not norm_done:
                    rows.append({**base_row, "series_id": "gdelt:norm", "name": "GDELT articles monitored",
                                 "value": p["norm"], "unit": "articles"})
        norm_done = norm_done or any(p["has_norm"] for p in vol.values())
        for d, p in sorted(tone.items()):
            rows.append({"source": "gdelt", "series_id": f"gdelt:{qid}:tone", "name": f"{q['name']} (tone)",
                         "date": d, "value": p["value"], "unit": "tone", "freq": "daily",
                         "source_url": HUMAN.format(q=url_q, mode="timelinetone"), "fetched_at": fetched})
    out = pd.DataFrame(rows)
    out.attrs["errors"] = errors
    return out
