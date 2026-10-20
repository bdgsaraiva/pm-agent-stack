"""GDELT GKG on BigQuery -> narrative discovery (agent 7 step 1; pmstack/discovery.py does the scoring).

Per complete UTC day: query 1 counts title words and word pairs per distinct source domain inside BigQuery (English
records only), so tens of thousands of rows come back, not every title; the day aggregate is stored locally. For the
newest days (no candidate list yet) the day is scored against the stored days before it and query 2 fetches titles for
the flagged terms only, giving the day's candidate list. Missing history is backfilled newest-first within the time and
byte budget and resumes next run. Same rails as gdelt_bq.py: dry run, maximum_bytes_billed, the shared byte ledger and
its query / run / month caps. Secrets GCP_SA_KEY and GCP_PROJECT_ID, read from the environment only (Actions only).
Cite "The GDELT Project".
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from . import base
from . import gdelt_bq as bq

KIND = "obs"


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    from .. import discovery as disc
    out = pd.DataFrame()
    errors: list[str] = []
    out.attrs["errors"] = errors
    client = bq._client(cfg)
    if client is None:
        out.attrs["skipped"] = "GCP_SA_KEY not set (BigQuery runs in GitHub Actions only)"
        return out
    c = disc.cfg()
    table = cfg.get("table", bq.TABLE)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    deadline = time.monotonic() + float(cfg.get("max_minutes", 8)) * 60
    led = bq.load_ledger()
    budget = bq.Budget(cfg, led, f"{yesterday:%Y-%m}")
    at = base.now_utc().isoformat()
    have = set(disc.stored_days())
    hist_n = int(c["history_days"])
    want = [yesterday - timedelta(days=k) for k in range(hist_n)]
    missing = [d for d in want if d not in have]                       # newest first
    cand_days = [d for d in want[: int(cfg.get("candidate_days", 3))] if not disc.cand_path(d).exists()]
    tsql = disc.terms_sql(c, table)
    done, cands, notes = [], 0, []

    def day_agg(d: date) -> pd.DataFrame | None:
        got = bq._run_chunk(client, tsql, {"start": str(d), "stop": str(d + timedelta(days=1))}, "discovery:terms",
                            d, d, budget, at, errors)
        if got is None:
            errors.append(f"byte budget: {d} does not fit what is left ({max(0.0, budget.room()) / bq.GB:.1f} GB)")
            return None
        return pd.DataFrame(got)

    empty: list[date] = []
    left = [d for d in sorted(missing, reverse=True) if d not in cand_days]

    def backfill(enough=None) -> bool:
        """History, newest first (the baseline nearest today matters most; review #11). Stops at `enough()`; False
        when the time or byte budget ran out."""
        while left:
            if enough is not None and enough():
                return True
            if time.monotonic() > deadline:
                errors.append(f"time budget used up; {len(left)} history day(s) left, they continue next run")
                return False
            d = left[0]
            agg = day_agg(d)
            if agg is None:
                return False
            left.pop(0)
            if disc.save_day(d, agg):                                    # an empty partition is not stored: refetched
                done.append(d)
            else:
                empty.append(d)
        return True

    try:
        # 1. just enough history for the oldest candidate day to be scored (live run 20 Oct: a full 87-day backfill
        #    used the whole budget and no list was written), then the candidates, then the rest of the history
        first = min(cand_days) if cand_days else None
        ok = backfill((lambda: len([x for x in disc.stored_days() if x < first]) >= c["min_history_days"])
                     if first else None)
        if not ok:
            cand_days = []
        # 2. the newest days: score on the stored history, fetch titles for the flagged terms, write the candidates
        for d in sorted(cand_days):
            if time.monotonic() > deadline:
                errors.append(f"time budget used up before the candidates of {d}")
                break
            agg = pd.read_parquet(disc.day_path(d)) if d in have else day_agg(d)
            if agg is None:
                break
            hist = disc.history(d, hist_n)
            if len(hist) < c["min_history_days"]:                       # no flags possible yet: store, no titles
                if disc.save_day(d, agg):
                    done.append(d)
                notes.append(f"{d}: only {len(hist)} stored days before it, no flags yet (needs {c['min_history_days']})")
                continue
            if time.monotonic() > deadline:
                disc.save_day(d, agg)
                errors.append(f"time budget used up before scoring {d}; its candidates come next run")
                break
            sc = disc.score(d, agg, hist, c)
            fl = disc.flagged(sc, c) if len(sc) else sc
            rows = []
            if len(fl):
                if time.monotonic() > deadline:
                    disc.save_day(d, agg)
                    errors.append(f"time budget used up before the titles of {d}; its candidates come next run")
                    break
                got = bq._run_chunk(client, disc.titles_sql(list(fl["term"]), c, table),
                                    {"start": str(d), "stop": str(d + timedelta(days=1))}, "discovery:titles", d, d,
                                    budget, at, errors)
                if got is None:
                    errors.append(f"byte budget: no titles for {d}; its candidates come next run")
                    disc.save_day(d, agg)
                    continue
                rows = [{**r, "doms": list(r.get("doms") or [])} for r in got]
            res = disc.process_day(d, agg, rows, c)
            cands += len(res.get("candidates", []))
            done.append(d)
        if ok:
            backfill()                                                   # 3. the rest of the baseline
        pruned = disc.prune(hist_n + 14, yesterday)
        if pruned:
            notes.append(f"pruned {pruned} day file(s) older than the baseline")
    except Exception as ex:  # noqa: BLE001  (what was fetched is kept; the error is logged)
        errors.append(f"{type(ex).__name__}: {str(ex)[:300]}")
    finally:
        bq._save_ledger(led)
    out.attrs["errors"] = errors
    out.attrs["bytes_gb"] = round(budget.used / bq.GB, 3)
    out.attrs["month_gb"] = round(led["months"].get(budget.month, 0) / bq.GB, 3)
    out.attrs["notes"] = ([f"days processed: {len(done)}; candidates written: {cands}; stored days: "
                           f"{len(disc.stored_days())}"] + ([f"empty partitions (not stored): {[str(d) for d in empty]}"]
                                                          if empty else []) + notes[:3])
    return out
