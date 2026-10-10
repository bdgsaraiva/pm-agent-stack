"""Run every adapter in config/sources.yaml and upsert into the research memory."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pandas as pd
import yaml

from . import adapters, runlog, store

ROOT = Path(__file__).resolve().parents[1]
OVERLAP_DAYS = {"eia": 28, "cftc": 28, "fred": 14, "bcb": 45, "prices": 10, "gdelt": 10}


def load_sources() -> dict:
    return yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))


def _history_file(key: str) -> Path:
    return store.DATA / "obs" / key / "_history.json"


def deep_history(key: str, cfg: dict) -> dict[str, str]:
    """Series whose stored history starts later than `history_start` and that were never fetched back to it.
    Agent 8's stress replays need 1987-2026 (futures from ~2000, spot/index proxies before): each such series is
    fetched once from `history_start`, then marked done, even when the source has nothing that early."""
    import json
    hs = str(cfg["history_start"])
    try:
        done = json.loads(_history_file(key).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        done = {}
    try:
        k = store.connect().execute("SELECT series_id, min(date) AS first FROM obs WHERE source = ? GROUP BY 1", [key]).df()
        first = {r.series_id: str(pd.Timestamp(r.first).date()) for r in k.itertuples()}
    except Exception:  # noqa: BLE001
        first = {}
    ids = [x["id"] for x in cfg.get("series") or cfg.get("tickers") or []]
    return {i: first[i] for i in ids if i in first and first[i] > hs and str(done.get(i, "9999")) > hs}


def history_reached(df: pd.DataFrame, deep: dict, new_ids: set, backfill: bool) -> list[str]:
    """Series to mark done: a deep fetch that returned rows on or before the stored first date (the source had
    nothing earlier, or it all arrived), a new series fetched from history_start, or any series in a backfill."""
    if df is None or df.empty:
        return []
    first = df.groupby("series_id")["date"].min().astype(str).to_dict()
    out = []
    for sid, d0 in first.items():
        if backfill or sid in new_ids or (sid in deep and d0 <= deep[sid]):
            out.append(sid)
    return out


def mark_history(key: str, ids: list[str], start) -> None:
    import json
    if not ids:
        return
    f = _history_file(key)
    try:
        done = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        done = {}
    done.update({i: str(start) for i in ids})
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(done, indent=1, sort_keys=True), encoding="utf-8")


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
            # series added since the last run (or with under 20 points) get their full history, not just the overlap
            try:
                k = store.connect().execute(
                    "SELECT series_id, max(date) AS last FROM obs WHERE source = ? GROUP BY 1 HAVING count(*) >= 20",
                    [key]).df()
                known = set(k["series_id"])
                last_by = {r.series_id: pd.Timestamp(r.last).date() for r in k.itertuples()}
            except Exception:
                known, last_by = set(), {}
            cfg = {**cfg, "_known": known, "_last": last_by}   # _last: per-series restart point (gdelt)
        if mod.KIND == "obs" and cfg.get("history_start") and not backfill:
            cfg = {**cfg, "_deep": deep_history(key, cfg)}   # one-time fetch back to history_start (agent 8)
        if backfill and cfg.get("history_start"):
            cfg = {**cfg, "backfill_start": cfg["history_start"]}
        try:
            df = mod.fetch(cfg, since)
            errors = df.attrs.get("errors", []) if df is not None else []
            n_new = 0 if df is None else len(df)
            total = store.upsert_obs(key, df) if mod.KIND == "obs" else store.upsert_text(key, df)
            status = "ok" if not errors else "partial"
            if cfg.get("history_start"):
                ids = [x["id"] for x in cfg.get("series") or cfg.get("tickers") or []]
                known = cfg.get("_known")
                new_ids = {i for i in ids if known is not None and i not in known}
                mark_history(key, history_reached(df, cfg.get("_deep") or {}, new_ids, backfill), cfg["history_start"])
            rec = runlog.log(run_id, f"fetch:{key}", status, adapter=cfg["adapter"], since=since,
                             rows_fetched=n_new, rows_stored=total, errors=errors,
                             output=f"data/obs/{key}/" if mod.KIND == "obs" else f"data/text/{key}.parquet")
        except Exception as e:  # one failing source must not stop the others
            rec = runlog.log(run_id, f"fetch:{key}", "error", adapter=cfg["adapter"], since=since,
                             errors=[f"{type(e).__name__}: {e}"])
        results.append(rec)
        print(f"[{rec['status']:7}] {key:8} fetched={rec.get('rows_fetched', 0)} stored={rec.get('rows_stored', '-')} {rec.get('errors') or ''}")
    return results
