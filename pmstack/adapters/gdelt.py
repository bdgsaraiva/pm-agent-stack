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

import pandas as pd

from . import base

KIND = "obs"
API = "https://api.gdeltproject.org/api/v2/doc/doc"
HUMAN = "https://api.gdeltproject.org/api/v2/doc/doc?query={q}&mode={mode}"


def _pause(cfg: dict) -> None:
    if os.environ.get("PMSTACK_NO_PAUSE"):
        return
    time.sleep(float(cfg.get("pause_seconds", 5)))


def _call(cfg: dict, query: str, mode: str, start: date, end: date) -> list[dict]:
    """One timeline call; GDELT answers rate-limit breaches with plain text, so parse defensively and back off."""
    params = {"query": query, "mode": mode, "format": "json",
              "startdatetime": f"{start:%Y%m%d}000000", "enddatetime": f"{end:%Y%m%d}235959"}
    last = None
    for i in range(int(cfg.get("tries", 3))):
        _pause(cfg)
        try:
            txt = base.get_text(API, params=params, timeout=60)
            js = json.loads(txt) if txt.strip().startswith("{") else None
            if js is None:
                raise ValueError(f"non-JSON reply: {txt[:120]!r}")
            tl = js.get("timeline") or []
            return tl[0].get("data", []) if tl else []
        except Exception as e:  # noqa: BLE001
            last = e
            if not os.environ.get("PMSTACK_NO_PAUSE"):
                time.sleep(10 * (i + 1))
    raise RuntimeError(f"GDELT {mode} failed for {query[:60]!r}: {last}")


def _day(s) -> date | None:
    s = str(s)
    try:
        return datetime.strptime(s[:8], "%Y%m%d").date()
    except ValueError:
        return None


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    fetched = base.now_utc()
    end = (datetime.now(timezone.utc) - timedelta(days=1)).date()   # complete UTC days only
    full_start = date.fromisoformat(cfg.get("backfill_start", "2017-01-01"))
    rows, errors, norm_done = [], [], False
    known = cfg.get("_known")
    for q in cfg["queries"]:
        qid = f"{q['id']}"
        first = known is not None and f"gdelt:{qid}:share" not in known
        start = full_start if (since is None or first) else max(full_start, since)
        url_q = q["query"].replace(" ", "%20")
        try:
            vol = _call(cfg, q["query"], "timelinevolraw", start, end)
            tone = _call(cfg, q["query"], "timelinetone", start, end)
        except Exception as e:  # one failing query must not stop the others
            errors.append(f"{qid}: {e}")
            continue
        for p in vol:
            d = _day(p.get("date"))
            if d is None or d > end:
                continue
            cnt, norm = p.get("value"), p.get("norm")
            base_row = {"source": "gdelt", "date": d, "freq": "daily", "fetched_at": fetched,
                        "source_url": HUMAN.format(q=url_q, mode="timelinevolraw")}
            rows.append({**base_row, "series_id": f"gdelt:{qid}:count", "name": f"{q['name']} (articles)",
                         "value": cnt, "unit": "articles"})
            if norm:
                rows.append({**base_row, "series_id": f"gdelt:{qid}:share", "name": f"{q['name']} (share of coverage)",
                             "value": 100.0 * float(cnt or 0) / float(norm), "unit": "pct"})
                if not norm_done:
                    rows.append({**base_row, "series_id": "gdelt:norm", "name": "GDELT articles monitored",
                                 "value": norm, "unit": "articles"})
        norm_done = norm_done or any(p.get("norm") for p in vol)
        for p in tone:
            d = _day(p.get("date"))
            if d is None or d > end:
                continue
            rows.append({"source": "gdelt", "series_id": f"gdelt:{qid}:tone", "name": f"{q['name']} (tone)",
                         "date": d, "value": p.get("value"), "unit": "tone", "freq": "daily",
                         "source_url": HUMAN.format(q=url_q, mode="timelinetone"), "fetched_at": fetched})
    out = pd.DataFrame(rows)
    out.attrs["errors"] = errors
    return out
