"""JODI Oil World Database: monthly crude balances by country (free bulk CSV, no key; cite "JODI").

No data licence is published beyond "free, internationally comparable energy data" (jodidata.org FAQ): personal
research use with attribution. JODI overwrites its files and keeps no vintages, so each fetch also files the
values that changed into the facts log (pmstack.facts.record_changed): from 24 Oct 2026 on, what was known when is
recoverable (point in time). Rows marked "-" or "x" (not available / confidential) are dropped.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone

import pandas as pd

from . import base

KIND = "obs"
URL = "https://www.jodidata.org/_resources/files/downloads/oil-data/annual-csv/primary/{name}.csv"
HUMAN = "https://www.jodidata.org/oil/database/data-downloads.aspx"


def _year(year: int, cur: int, timeout: int) -> pd.DataFrame:
    name = f"primaryyear{year}" if year == cur else str(year)
    import requests
    r = requests.get(URL.format(name=name), timeout=timeout, headers={"User-Agent": "pm-agent-stack (personal research)"})
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.text), dtype=str)


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    cur = datetime.now(timezone.utc).year
    first = cfg.get("_known") is not None and not cfg.get("_known")
    years = list(range(int(cfg.get("history_from", 2015)), cur + 1)) if (since is None or first) else [cur - 1, cur]
    keep = {(f["flow"], f["unit"]) for f in cfg["flows"]}
    countries = set(cfg["countries"])
    frames, errors = [], []
    t0 = datetime.now(timezone.utc)
    for y in sorted(years, reverse=True):                     # newest first: a budget cut loses old history, not today
        if (datetime.now(timezone.utc) - t0).total_seconds() > float(cfg.get("budget_s", 120)):
            errors.append(f"budget reached before {y}")
            break
        try:
            df = _year(y, cur, int(cfg.get("timeout_s", 60)))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{y}: {e}")
            continue
        df = df[df["REF_AREA"].isin(countries) & (df["ENERGY_PRODUCT"] == cfg.get("product", "CRUDEOIL"))]
        df = df[[(f, u) in keep for f, u in zip(df["FLOW_BREAKDOWN"], df["UNIT_MEASURE"])]]
        df = df.assign(value=pd.to_numeric(df["OBS_VALUE"], errors="coerce")).dropna(subset=["value"])
        frames.append(df)
    if not frames:
        out = pd.DataFrame()
        out.attrs["errors"] = errors
        if errors:
            raise RuntimeError("; ".join(errors)[:500])
        return out
    raw = pd.concat(frames, ignore_index=True)
    fetched = base.now_utc()
    out = pd.DataFrame({
        "source": "jodi",
        "series_id": "jodi:" + raw["REF_AREA"] + ":" + raw["ENERGY_PRODUCT"] + ":" + raw["FLOW_BREAKDOWN"],
        "name": "JODI " + raw["REF_AREA"] + " crude " + raw["FLOW_BREAKDOWN"],
        "date": pd.to_datetime(raw["TIME_PERIOD"] + "-01").dt.date,
        "value": raw["value"], "unit": raw["UNIT_MEASURE"], "freq": "monthly", "source_url": HUMAN, "fetched_at": fetched,
    })
    if cfg.get("vintages", True):
        from .. import facts
        recent = out[pd.to_datetime(out["date"]) >= pd.Timestamp(cur - 1, 1, 1)]
        n = facts.record_changed([{"subject": r.series_id, "predicate": "value", "value": float(r.value), "unit": r.unit,
                                   "valid_from": r.date, "source_url": HUMAN, "author": "JODI"} for r in recent.itertuples()],
                                 writer="pmstack.adapters.jodi", source_type="data")
        out.attrs["notes"] = f"{n} JODI value(s) new or revised, filed in data/facts/facts.jsonl"
    out.attrs["errors"] = errors
    return out
