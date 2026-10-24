"""Per-commodity test sets for the specialists (specialists-kickoff.md section 6): ~20 dated questions per complex
with known answers from frozen public material, graded by code. Same discipline as the own test set (pmstack/
evals.py: k runs, pass^k, Wilson intervals, sealed tasks, frozen fixtures), with data-driven graders, so adding a
task is a YAML edit and a gold line, never new code.

  evals/<set>/tasks.yaml   prompts (the answering session reads these and the named fixtures only)
  evals/<set>/gold.yaml    gold fields per task (never opened by the answering session)
  evals/<set>/runs/<date>-<label>/<task>.json   one answer per task; grade.json after grading
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from . import runlog
from .evals import _close, _empty, _no_trade, _unnegated, wilson

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"


def _y(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def tasks(s: str) -> dict:
    return _y(EVALS / s / "tasks.yaml")


def gold(s: str) -> dict:
    return _y(EVALS / s / "gold.yaml")


def prompt(s: str, tid: str, run_dir: str = "<run>") -> str:
    ts = tasks(s)
    t = next(x for x in ts["tasks"] if x["id"] == tid)
    return (f"{ts['shared_rules'].strip()}\n\nTask {t['id']} (as of {t['asof']}). Files: {', '.join(t['files'])}\n\n"
            f"{t['prompt'].strip()}\n\nWrite the JSON object to {run_dir}/{t['id']}.json")


def _chk(name: str, ok: bool, detail: str = "") -> dict:
    return {"check": name, "ok": bool(ok), "detail": detail[:160]}


def grade_answer(g: dict, a) -> list[dict]:
    if not isinstance(a, dict):
        return [_chk("answer is a JSON object", False)]
    out = []
    if g.get("abstain"):
        out.append(_chk("abstains", a.get("abstain") is True, f"abstain={a.get('abstain')}"))
        vals = {k: v for k, v in a.items() if k not in ("abstain", "why")}
        out.append(_chk("no answer given", all(_empty(v) for v in vals.values()), json.dumps(vals)[:160]))
        nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", json.dumps(vals))]
        bad = [x for x in g.get("forbid_numbers", []) if any(abs(abs(v) - x) < 0.5 for v in nums)]
        if g.get("forbid_numbers"):
            out.append(_chk("no norm passed off as an answer", not bad, str(bad)))
        return out
    out.append(_chk("does not abstain", a.get("abstain") in (False, None)))
    for f, rule in (g.get("fields") or {}).items():
        v = a.get(f)
        if "num" in rule:
            out.append(_chk(f, _close(v, rule["num"], rule.get("tol", 0.005)), str(v)))
        elif "eq" in rule:
            out.append(_chk(f, str(v).strip().lower() == str(rule["eq"]).strip().lower(), str(v)))
        elif "contains" in rule:
            out.append(_chk(f, str(rule["contains"]).lower() in str(v or "").lower(), str(v)))
        elif "any" in rule:
            out.append(_chk(f, any(w.lower() in str(v or "").lower() for w in rule["any"]), str(v)))
        elif "list_eq" in rule:
            got = sorted(str(x).strip().lower() for x in (v or []))
            out.append(_chk(f, got == sorted(x.lower() for x in rule["list_eq"]), str(v)))
        elif "bool" in rule:
            out.append(_chk(f, v is rule["bool"], str(v)))
    for f, pat in (g.get("forbid") or {}).items():          # "not a data error" is fine; "a data error" is not
        out.append(_chk(f"{f}: forbidden wording", not _unnegated(pat, str(a.get(f) or "")), str(a.get(f))[:80]))
    if g.get("no_trade"):
        out.append(_no_trade(str(a.get(g["no_trade"]) or "")))
    return out


def grade(s: str, run: str | Path, log: bool = True) -> dict:
    run = Path(run)
    G = gold(s)
    results = []
    for t in tasks(s)["tasks"]:
        f = run / f"{t['id']}.json"
        if not f.exists():
            results.append({"task": t["id"], "pass": None, "checks": [], "missing": True, "sealed": bool(t.get("sealed"))})
            continue
        try:
            a = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            results.append({"task": t["id"], "pass": False, "checks": [_chk("valid JSON", False, str(e))], "sealed": bool(t.get("sealed"))})
            continue
        ch = grade_answer(G[t["id"]], a)
        results.append({"task": t["id"], "pass": all(c["ok"] for c in ch), "checks": ch, "sealed": bool(t.get("sealed"))})
    done = [r for r in results if r["pass"] is not None]
    k = sum(1 for r in done if r["pass"])
    lo, hi = wilson(k, len(done)) if done else (None, None)
    out = {"set": s, "run": run.as_posix(), "graded_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
           "answered": len(done), "passed": k, "pass_rate": round(k / len(done), 3) if done else None,
           "ci95": [round(lo / 100, 3), round(hi / 100, 3)] if done else None, "results": results}   # evals.wilson is in %
    (run / "grade.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    if log:
        runlog.log(runlog.new_run_id(), f"cevals:grade:{s}", "ok", run=run.as_posix(), answered=len(done), passed=k,
                   failed=[r["task"] for r in done if not r["pass"]])
    return out


def report(s: str, runs: list[str]) -> dict:
    """pass^k: a task counts only if it passed in every run (the own test set's rule)."""
    per = {}
    for r in runs:
        g = json.loads((Path(r) / "grade.json").read_text(encoding="utf-8"))
        for x in g["results"]:
            per.setdefault(x["task"], []).append(x["pass"])
    allk = {t: all(v is True for v in vs) and len(vs) == len(runs) for t, vs in per.items()}
    k = sum(allk.values())
    lo, hi = wilson(k, len(allk))
    return {"set": s, "runs": runs, "tasks": len(allk), "pass_all_runs": k, "ci95": [round(lo / 100, 3), round(hi / 100, 3)],
            "failing": sorted(t for t, ok in allk.items() if not ok)}


def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack cevals", description="Per-commodity specialist test sets")
    sub = p.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("list")
    l.add_argument("set")
    pr = sub.add_parser("prompt")
    pr.add_argument("set")
    pr.add_argument("task")
    pr.add_argument("--run", default="<run>")
    nw = sub.add_parser("new-run")
    nw.add_argument("set")
    nw.add_argument("label")
    nw.add_argument("--model", required=True)
    gr = sub.add_parser("grade")
    gr.add_argument("set")
    gr.add_argument("run")
    rp = sub.add_parser("report")
    rp.add_argument("set")
    rp.add_argument("runs", nargs="+")
    a = p.parse_args(argv)
    if a.cmd == "list":
        for t in tasks(a.set)["tasks"]:
            print(f"{t['id']:<24} as of {t['asof']}{'  (sealed)' if t.get('sealed') else ''}")
    elif a.cmd == "prompt":
        print(prompt(a.set, a.task, a.run))
    elif a.cmd == "new-run":
        d = EVALS / a.set / "runs" / f"{date.today().isoformat()}-{re.sub(r'[^a-z0-9-]+', '-', a.label.lower())}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "meta.json").write_text(json.dumps({"model": a.model, "label": a.label, "tasks_version": tasks(a.set)["version"],
                                                 "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}, indent=1), encoding="utf-8")
        print(d.relative_to(ROOT).as_posix())
    elif a.cmd == "grade":
        out = grade(a.set, a.run)
        print(json.dumps({k: v for k, v in out.items() if k != "results"} |
                         {"failed": [{"task": r["task"], "checks": [c for c in r["checks"] if not c["ok"]]} for r in out["results"] if r["pass"] is False]}, indent=1))
    elif a.cmd == "report":
        print(json.dumps(report(a.set, a.runs), indent=1))
    return 0
