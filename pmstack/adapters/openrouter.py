"""OpenRouter Data API, rankings-daily: tokens processed through OpenRouter per UTC day (top 50 models + "other").

Key: OPENROUTER_API_KEY (any free OpenRouter key; repo secret, read from env only). Without it the source is
"skipped", not an error. Data licensed CC BY 4.0; cite "Source: OpenRouter (openrouter.ai/rankings), as of
<meta.as_of>". History from 2025-01-01, at most 366 days per request; 30 requests/minute, 500/day. The API serves
completed UTC days only (the default end date), and a day can be restated while snapshots refresh (latest wins).

  or:tokens        all tokens that day (top 50 + other), tokens
  or:top_share     share of the day's tokens taken by the single largest model, %
OpenRouter is one router (developer and agent traffic), not the market: a demand proxy for applications, with
mix shifts (a popular free model, a coding agent) that need not mean more AI demand overall.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import pandas as pd

from . import ai_common as ac, base

KIND = "obs"
API = "https://openrouter.ai/api/v1/datasets/rankings-daily"
PAGE = "https://openrouter.ai/rankings"
START = date(2025, 1, 1)


def records(js: dict, fetched) -> list[dict]:
    d = pd.DataFrame(js.get("data") or [])
    if d.empty:
        return []
    d["total_tokens"] = pd.to_numeric(d["total_tokens"], errors="coerce")
    out = []
    for day, g in d.groupby("date"):
        tot = float(g["total_tokens"].sum())
        if tot <= 0:
            continue
        top = float(g.loc[g["model_permaslug"] != "other", "total_tokens"].max())
        out.append(ac.row("openrouter", "or:tokens", "OpenRouter tokens per day", day, tot, "tokens", "daily", PAGE, fetched))
        out.append(ac.row("openrouter", "or:top_share", "OpenRouter top model share of tokens", day, 100 * top / tot, "%",
                          "daily", PAGE, fetched))
    return out


def windows(since: date | None, today: date) -> list[tuple[date, date]]:
    start = max(since or START, START)
    end = today - timedelta(days=1)
    out = []
    while start <= end:
        stop = min(start + timedelta(days=365), end)
        out.append((start, stop))
        start = stop + timedelta(days=1)
    return out


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        df = ac.frame([], [])
        df.attrs["skipped"] = "OPENROUTER_API_KEY not set (free key at openrouter.ai; add it as a repo secret)"
        return df
    fetched, rows, errors, budget = base.now_utc(), [], [], ac.Budget(cfg)
    for a, b in windows(since, fetched.date()):
        if budget.out():
            errors.append(f"time budget reached before {a}; the rest follows next run")
            break
        try:
            js = ac.get(API, cfg, params={"start_date": str(a), "end_date": str(b)},
                        headers={"Authorization": f"Bearer {key}"}).json()
            rows += records(js, fetched)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{a}..{b}: {type(e).__name__}: {e}")
    if not rows and errors:
        raise RuntimeError("; ".join(errors))
    return ac.frame(rows, errors)
