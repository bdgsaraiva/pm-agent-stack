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
    if argv and argv[0] == "discovery":          # python -m pmstack discovery <list|show|decide|decisions|placebo|draft>
        from . import discovery
        return discovery.cli(argv[1:])
    if argv and argv[0] == "digest":             # python -m pmstack digest <fetch|chunks|check|save|facts|index|calls|view|diff>
        from . import digest
        return digest.cli(argv[1:])
    if argv and argv[0] == "network":            # python -m pmstack network <init|contact|call|due|reconnect|prep|monthly|forget|public ...>
        from . import network
        return network.cli(argv[1:])
    if argv and argv[0] == "balance":            # python -m pmstack balance [show|probe] [--date D] [--out f]
        from . import balance
        return balance.cli(argv[1:])
    if argv and argv[0] == "evals":              # python -m pmstack evals <list|prompt|new-run|grade|report|calibrate|noise>
        from . import evals
        return evals.cli(argv[1:])
    if argv and argv[0] == "research":           # python -m pmstack research <flags|list|new|run|index|show>
        from . import research
        return research.cli(argv[1:])
    if argv and argv[0] == "spreads":          # python -m pmstack spreads <list|build|show>
        from . import spreads
        return spreads.cli(argv[1:])
    if argv and argv[0] == "critic":           # python -m pmstack critic <card|save|answer|withdraw|outcome|weekly|stats>
        from . import critic
        return critic.cli(argv[1:])
    if argv and argv[0] == "facts":            # python -m pmstack facts <as-of|history|count>   (point-in-time memory)
        from . import facts
        return facts.cli(argv[1:])
    if argv and argv[0] == "cards":            # python -m pmstack cards <validate|save|latest>  (state cards)
        from . import cards
        return cards.cli(argv[1:])
    if argv and argv[0] in ("route", "ask"):   # python -m pmstack route "<question>"           (/ask routing)
        from . import route
        return route.cli(argv[1:])
    if argv and argv[0] == "knowledge":        # python -m pmstack knowledge <add|propose|pending|confirm-prior|reject-prior|check|render>
        from . import knowledge
        return knowledge.cli(argv[1:])
    if argv and argv[0] == "events":           # python -m pmstack events [--date D] [--only wpsr,wngsr] [--write]  (report base rates)
        from . import events
        return events.cli(argv[1:])
    if argv and argv[0] == "metals":           # python -m pmstack metals [--date D] [--write]  (S3: stock playbooks, China days, storage, long run)
        from . import metals
        return metals.cli(argv[1:])
    if argv and argv[0] == "specialist":       # python -m pmstack specialist pack <energy|metals> [--date D] [--question ...]
        from . import specialist
        return specialist.cli(argv[1:])
    if argv and argv[0] == "file-reports":     # python -m pmstack file-reports [--date D]  (report-day filer, no model)
        from . import filer
        return filer.cli(argv[1:])
    if argv and argv[0] == "quant":            # python -m pmstack quant tape [--date D] [--write]   (agent 13, after the close)
        from .quant import tape
        return tape.cli(argv[1:])
    if argv and argv[0] == "cevals":           # python -m pmstack cevals <list|prompt|new-run|grade|report> <set>  (specialist test sets)
        from . import cevals
        return cevals.cli(argv[1:])
    if argv and argv[0] == "inbox":            # python -m pmstack inbox <list|screen|classify|ingest|facts>
        from . import inbox
        return inbox.cli(argv[1:])
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
