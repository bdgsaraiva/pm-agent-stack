"""Run every adapter in config/sources.yaml and upsert into the research memory."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import yaml

from . import adapters, runlog, store

ROOT = Path(__file__).resolve().parents[1]
OVERLAP_DAYS = {"eia": 28, "cftc": 28, "fred": 14, "bcb": 45, "prices": 10}


def load_sources() -> dict:
    return yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))


def run(only: list[str] | None = None, backfill: bool = False, run_id: str | None = None) -> list[dict]:
    run_id = run_id or runlog.new_run_id()
    results = []
    for key, cfg in load_sources().items():
        if only and key not in only:
            continue
        mod = adapters.load(cfg["adapter"])
        since = None
        if mod.KIND == "obs" and not backfill:
            last = store.last_date(key)
            if last:
                since = last - timedelta(days=OVERLAP_DAYS.get(key, 14))
        if mod.KIND == "obs" and since is not None:
            # series added to config since the last run get their full history, not just the overlap
            try:
                known = set(store.connect().execute(
                    "SELECT DISTINCT series_id FROM obs WHERE source = ?", [key]).df()["series_id"])
            except Exception:
                known = set()
            cfg = {**cfg, "_known": known}
        try:
            df = mod.fetch(cfg, since)
            errors = df.attrs.get("errors", []) if df is not None else []
            n_new = 0 if df is None else len(df)
            total = store.upsert_obs(key, df) if mod.KIND == "obs" else store.upsert_text(key, df)
            status = "ok" if not errors else "partial"
            rec = runlog.log(run_id, f"fetch:{key}", status, adapter=cfg["adapter"], since=since,
                             rows_fetched=n_new, rows_stored=total, errors=errors,
                             output=f"data/obs/{key}/" if mod.KIND == "obs" else f"data/text/{key}.parquet")
        except Exception as e:  # one failing source must not stop the others
            rec = runlog.log(run_id, f"fetch:{key}", "error", adapter=cfg["adapter"], since=since,
                             errors=[f"{type(e).__name__}: {e}"])
        results.append(rec)
        print(f"[{rec['status']:7}] {key:8} fetched={rec.get('rows_fetched', 0)} stored={rec.get('rows_stored', '-')} {rec.get('errors') or ''}")
    return results
