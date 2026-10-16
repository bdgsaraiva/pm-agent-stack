"""CLI: python -m pmstack {fetch|monitor|all} [--only eia,cftc] [--backfill] [--date YYYY-MM-DD]"""
from __future__ import annotations

import argparse
import sys
from datetime import date

from . import fetch, monitor, runlog


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "journal":            # python -m pmstack journal <new|event|close|reject|list|stats|book|check>
        from . import journal
        return journal.cli(argv[1:])
    if argv and argv[0] == "audit":              # python -m pmstack audit <file> [--date] [--facts ...] [--flag]
        from . import audit
        return audit.cli(argv[1:])
    if argv and argv[0] == "review":             # python -m pmstack review weekly|goal ...
        from . import review
        return review.cli(argv[1:])
    if argv and argv[0] == "risk":               # python -m pmstack risk [--date D] [--out file.md]
        from . import risk
        return risk.cli(argv[1:])
    if argv and argv[0] == "narratives":         # python -m pmstack narratives tracker|headlines|audit|audit-score
        from . import consensus
        return consensus.cli(argv[1:])
    if argv and argv[0] == "critic":             # python -m pmstack critic <card|save|answer|withdraw|outcome|weekly|stats>
        from . import critic
        return critic.cli(argv[1:])
    p = argparse.ArgumentParser(prog="pmstack")
    p.add_argument("cmd", choices=["fetch", "monitor", "all", "log"])
    p.add_argument("--step", help="log: step name, e.g. note:morning")
    p.add_argument("--status", default="ok", help="log: ok | partial | error")
    p.add_argument("--fields", default="{}", help="log: JSON object of extra fields (outputs, sources, doc_url...)")
    p.add_argument("--only", help="comma-separated source keys from config/sources.yaml")
    p.add_argument("--backfill", action="store_true", help="ignore stored data and fetch full history")
    p.add_argument("--date", help="as-of date for the monitor (BRT), default today")
    a = p.parse_args(argv)
    run_id = runlog.new_run_id()
    if a.cmd == "log":                      # used by Claude tasks to write their own audit line
        import json
        rec = runlog.log(run_id, a.step or "agent", a.status, **json.loads(a.fields))
        print(json.dumps(rec, ensure_ascii=False))
        return 0
    if a.cmd in ("fetch", "all"):
        res = fetch.run(only=a.only.split(",") if a.only else None, backfill=a.backfill, run_id=run_id)
        if res and all(r["status"] == "error" for r in res):
            print("all sources failed", file=sys.stderr)
            return 2
    if a.cmd in ("monitor", "all"):
        facts = monitor.build(asof=date.fromisoformat(a.date) if a.date else None, run_id=run_id)
        print(f"fact pack written for {facts['asof_brt']}: {len(facts['alerts'])} alerts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
