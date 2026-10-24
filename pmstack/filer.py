"""Report-day filer (no model; specialists-kickoff.md section 3.5): after the close, file the latest weekly
releases into the point-in-time facts log with their release time, so a later read as of any date sees what was
public then, including revisions as they appear (EIA gas storage is revised; WPSR rarely).

Filed: the WPSR stock series of config/energy.yaml (released Wednesday 10:30 ET, Thursday after a holiday), the
gas storage series (Thursday 10:30 ET), and CFTC managed money (positions as of Tuesday, released Friday 15:30 ET).
Only weeks released in the last `window_days` are filed; an identical fact is never written twice.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, time, timedelta, timezone

import pandas as pd

from . import events, facts, runlog, store

ET_OFFSET_H = 4            # EDT; EST weeks are an hour later: we use the later of the two (never earlier than real)


def _release_ts(d: date, hhmm: str = "10:30") -> datetime:
    h, m = map(int, hhmm.split(":"))
    # conservative: release time in UTC assuming EST (UTC-5), i.e. an hour late in summer, never early
    return datetime.combine(d, time(h, m), tzinfo=timezone.utc) + timedelta(hours=ET_OFFSET_H + 1)


def _when(subject: str, wk, value: float, release_ts: datetime, now: datetime, known, fresh_days: int = 7) -> datetime | None:
    """When the repo may say this value was public: its release time only for a first print filed within a week of
    release; otherwise (a revision, or a backlog week) the time it was seen. None = already known, skip (review S2)."""
    k = known.get((subject, str(wk)[:10]))
    if k is not None:
        return None if abs(float(k) - float(value)) < 1e-9 else now
    return release_ts if (now - release_ts).days <= fresh_days else now


def file_reports(asof: date | None = None, window_days: int = 21, con=None, path=None, now: datetime | None = None) -> dict:
    asof = asof or (datetime.now(timezone.utc) - timedelta(hours=3)).date()
    con = con or store.connect()
    c = events.cfg()
    now = now or datetime.now(timezone.utc)
    kn = facts.known(known_at=now, path=path)
    known = {(x.subject, x.valid_from): x.value_num for x in kn.itertuples() if x.predicate == "value"} if len(kn) else {}
    n, seen = 0, []
    for rkey, rep in c["events"].items():
        rel = rep["release"]
        done = set()
        for pr in rep["pairs"]:
            if (pr["source"], pr["series"]) in done:
                continue
            done.add((pr["source"], pr["series"]))
            s = events._series(con, pr["source"], pr["series"], asof)
            for wk, val in s[s.index >= asof - timedelta(days=window_days + 7)].items():
                rd = events.release_date(wk, rel)
                ts = _release_ts(rd, rel.get("time_et", "10:30"))
                if ts > now or rd > asof:
                    continue
                av = _when(pr["series"], wk, float(val), ts, now, known)
                if av is None:
                    continue
                facts.record(pr["series"], "value", float(val), unit="kbbl" if pr["series"].startswith("PET.") else "bcf",
                             valid_from=wk, available_at=av, source_url=rep["url"], source_type="agency_report",
                             writer="pmstack.filer", author="EIA", path=path)
                n += 1
            seen.append(pr["series"])
    # CFTC managed money net (% of open interest): Tuesday positions, released Friday 15:30 ET
    try:
        cf = con.execute("SELECT series_id, date, value FROM obs WHERE source = 'cftc' AND series_id LIKE '%.mm_net_pct_oi' "
                         "AND date >= ? AND date <= ?", [asof - timedelta(days=window_days + 7), asof]).df()
    except Exception:  # noqa: BLE001
        cf = None
    if cf is not None:
        for row in cf.itertuples():
            d = datetime.fromisoformat(str(row.date)[:10]).date()
            from .quant.positioning import release
            rd = release(d)                                          # Friday, or Monday in a federal-holiday week
            ts = _release_ts(rd, "15:30")
            if ts > now or rd > asof:
                continue
            av = _when(row.series_id, d, float(row.value), ts, now, known)
            if av is None:
                continue
            facts.record(row.series_id, "value", float(row.value), unit="% of open interest", valid_from=d, available_at=av,
                         source_url="https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm", source_type="data",
                         writer="pmstack.filer", author="CFTC", path=path)
            n += 1
    return {"asof": asof.isoformat(), "attempted": n, "series": seen}


def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack file-reports", description="file the latest weekly releases into the facts log")
    p.add_argument("--date")
    p.add_argument("--window-days", type=int, default=21)
    a = p.parse_args(argv)
    before = len(facts.load())
    out = file_reports(date.fromisoformat(a.date) if a.date else None, a.window_days)
    out["new_facts"] = len(facts.load()) - before
    runlog.log(runlog.new_run_id(), "filer:reports", "ok", **out)
    print(json.dumps(out, indent=1))
    return 0
