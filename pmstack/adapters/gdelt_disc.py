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

    try:
        # 1. history first, oldest of the missing days last: a new day can only be scored on the days before it
        for d in sorted(missing):
            if d in cand_days:
                continue                                                # scored in step 2, in date order
            if time.monotonic() > deadline:
                errors.append(f"time budget used up; {len([m for m in missing if m not in done])} day(s) left, they continue next run")
                break
            agg = day_agg(d)
            if agg is None:
                break
            disc.save_day(d, agg)
            done.append(d)
        # 2. the newest days: score on the stored history, fetch titles for the flagged terms, write the candidates
        for d in sorted(cand_days):
            if time.monotonic() > deadline:
                errors.append(f"time budget used up before the candidates of {d}")
                break
            agg = pd.read_parquet(disc.day_path(d)) if d in have else day_agg(d)
            if agg is None:
                break
            hist = disc.history(d, hist_n)
            sc = disc.score(d, agg, hist, c)
            fl = disc.flagged(sc, c) if len(sc) else sc
            rows = []
            if len(fl):
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
            if res.get("history_days", 0) < c["min_history_days"]:
                notes.append(f"{d}: only {res.get('history_days')} stored days before it, no flags yet "
                             f"(needs {c['min_history_days']})")
            done.append(d)
    except Exception as ex:  # noqa: BLE001  (what was fetched is kept; the error is logged)
        errors.append(f"{type(ex).__name__}: {str(ex)[:300]}")
    finally:
        bq._save_ledger(led)
    out.attrs["errors"] = errors
    out.attrs["bytes_gb"] = round(budget.used / bq.GB, 3)
    out.attrs["month_gb"] = round(led["months"].get(budget.month, 0) / bq.GB, 3)
    out.attrs["notes"] = [f"days processed: {len(done)}; candidates written: {cands}"] + notes[:3]
    return out
