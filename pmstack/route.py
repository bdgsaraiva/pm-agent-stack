"""Router for /ask (fundamentals pillar): code picks the specialist, the question type and the knowledge files.

Routing lives in config/agents.yaml, so adding a layer or a specialist is a config change plus a test run, never
a prompt rewrite (specialists-kickoff.md section 3.1). Kim et al. (2025): an orchestrator that checks its
specialists' work holds error amplification to 4.4x vs 17.2x without checks, and multi-agent setups lose on
sequential tasks, so the default is one specialist; several only when the question names several complexes.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "agents.yaml"
PREFIX_RE = re.compile(r"^\s*/?(?:ask\s+)?([a-z_]+)\s*:\s*(.+)$", re.I | re.S)


def cfg(path: Path | None = None) -> dict:
    return yaml.safe_load((path or CONFIG).read_text(encoding="utf-8"))


def _hits(text: str, words: list[str]) -> list[str]:
    t = " " + re.sub(r"[^a-z0-9&+/ -]+", " ", text.lower()) + " "
    return [w for w in words if re.search(r"(?<![a-z0-9])" + re.escape(w.lower()) + r"(?![a-z0-9])", t)]


def route(question: str, c: dict | None = None) -> dict:
    """{specialist, commodities, question_types, files, mode, other_pillar, inactive, note}."""
    c = c or cfg()
    specs = c["specialists"]
    q = question.strip()
    forced = None
    m = PREFIX_RE.match(q)
    if m and m.group(1).lower() in specs:
        forced, q = m.group(1).lower(), m.group(2).strip()
    scores: dict[str, dict] = {}
    for name, s in specs.items():
        for com, cc in (s.get("commodities") or {}).items():
            h = _hits(q, cc.get("keywords") or []) + [r for r in cc.get("refs") or [] if r.lower() in q.lower()]
            if h:
                scores.setdefault(name, {})[com] = h
    qtypes = [k for k, v in (c.get("question_types") or {}).items() if _hits(q, v.get("keywords") or [])]
    other = [k for k, v in (c.get("other_pillars") or {}).items() if _hits(q, v.get("keywords") or [])]
    if forced:
        chosen = [forced]
    else:
        ranked = sorted(scores, key=lambda n: -sum(len(v) for v in scores[n].values()))
        chosen = ranked
    active = [n for n in chosen if specs[n].get("status") == "active"]
    inactive = [n for n in chosen if specs[n].get("status") != "active"]
    out = {"question": q, "forced": forced, "specialist": active[0] if active else None,
           "also": active[1:], "inactive": inactive, "question_types": qtypes or ["driver"],
           "other_pillars": {k: c["other_pillars"][k] for k in other}, "commodities": [], "files": [], "mode": "single", "note": None}
    if len(active) > 1:
        out["mode"] = "generalist" if c.get("generalist", {}).get("status") == "active" else "single"
        if out["mode"] == "single":
            out["note"] = f"several complexes named; the generalist is not built yet (S6), so {active[0]} answers and says what {', '.join(active[1:])} would add"
    if not out["specialist"]:
        if inactive:
            out["note"] = f"{', '.join(inactive)} specialist not built yet ({', '.join(specs[n].get('status', '') for n in inactive)})"
        elif other:
            out["note"] = "belongs to another pillar: " + "; ".join(f"agent {c['other_pillars'][k]['agent']} ({c['other_pillars'][k]['how']})" for k in other)
        else:
            out["note"] = "no specialist matched: name one (\"/ask energy: ...\")"
        return out
    sp = specs[out["specialist"]]
    hits = scores.get(out["specialist"]) or {}
    coms = sorted(hits, key=lambda c: -len(hits[c])) or list((sp.get("commodities") or {}).keys())   # most hits first
    out["commodities"] = coms
    files = []
    for com in coms:
        base = sp["commodities"][com]["knowledge"]
        names = {"primer.md"} | {f for t in out["question_types"] for f in c["question_types"].get(t, {}).get("files", [])}
        files += [f"{base}/{n}" for n in sorted(names)]
    out["files"] = files
    out["skill"] = sp.get("skill")
    return out


def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack route")
    p.add_argument("question", nargs="+")
    a = p.parse_args(argv)
    print(json.dumps(route(" ".join(a.question)), indent=2, ensure_ascii=False))
    return 0
