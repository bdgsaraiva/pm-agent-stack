"""Knowledge by commodity (specialists S0): drivers with sign, lag and where each size came from.

knowledge/<complex>/<commodity>/
  primer.md          contracts, delivery, spreads that matter, seasonality, report calendar (hand-written)
  drivers.yaml       testable claims; written only through this module (code, with provenance)
  drivers.md         rendered from drivers.yaml (never edit by hand)
  balance.md         template: each line tied to a public series
  events.md          playbooks per scheduled report; reaction base rates computed by code
  analogues.md       linked to agent 8's stress library
  lessons.md         from closed journal ideas (lessons router)
  open-questions.md  hand-written questions + a code block "Prior vs estimate" rebuilt by `knowledge check`

Every quantified relationship records where its size came from (specialists-kickoff.md section 4):
  literature      a cited paper or agency study (url + page or table)
  own_estimate    computed by code from public data, point in time, the regression stored (path)
  bernardo_prior  Bernardo's experience, entered only through the inbox confirm step (he confirms each one)
A broker's own quantified sensitivity is never copied in. Where a prior and an estimate disagree, code writes
an open question.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from . import facts, runlog

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
PENDING = KNOWLEDGE / "inbox" / "pending.jsonl"
SIZE_KINDS = ("literature", "own_estimate", "bernardo_prior")
SIGNS = ("+", "-", "0", "?")
STATUSES = ("untested", "supported", "no edge", "reversed", "in-sample only", "insufficient", "literature only")
DRIVER_FIELDS = ("id", "claim", "driver", "target", "sign", "lag", "status", "sizes", "source", "test", "notes")
BLOCK_START = "<!-- code: prior-vs-estimate (pmstack knowledge check) -->"
BLOCK_END = "<!-- /code -->"
DISAGREE_REL = 0.5          # no interval: prior and estimate differ by more than half the estimate


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def folder(commodity: str, root: Path | None = None) -> Path:
    """'crude' or 'energy/crude' -> knowledge/energy/crude (looked up in config/agents.yaml)."""
    root = root or KNOWLEDGE
    if "/" in commodity:
        return root / commodity
    from . import route
    for s in route.cfg()["specialists"].values():
        c = (s.get("commodities") or {}).get(commodity)
        if c:
            return root / Path(c["knowledge"]).relative_to("knowledge")
    raise KeyError(f"unknown commodity {commodity}")


def load(commodity: str, root: Path | None = None) -> list[dict]:
    f = folder(commodity, root) / "drivers.yaml"
    if not f.exists():
        return []
    return yaml.safe_load(f.read_text(encoding="utf-8")) or []


def _write(commodity: str, drivers: list[dict], root: Path | None = None):
    d = folder(commodity, root)
    d.mkdir(parents=True, exist_ok=True)
    head = ("# Written by pmstack/knowledge.py only (add, confirm-prior, estimate). Rendered to drivers.md.\n"
            "# sizes[].kind: literature | own_estimate | bernardo_prior (specialists-kickoff.md section 4)\n")
    (d / "drivers.yaml").write_text(head + yaml.safe_dump(drivers, sort_keys=False, allow_unicode=True, width=110), encoding="utf-8")
    render(commodity, root)


def size_problems(s: dict) -> list[str]:
    out = []
    k = s.get("kind")
    if k not in SIZE_KINDS:
        return [f"size kind must be one of {SIZE_KINDS}"]
    if s.get("value") is None and not s.get("range"):
        out.append("size needs a value or a range")
    if not s.get("unit"):
        out.append("size needs a unit (e.g. '$/bbl per 1 mb', '% per 1 sd')")
    if k == "literature" and not (s.get("source") and s.get("url")):
        out.append("literature size needs source and url")
    if k == "own_estimate" and not (s.get("regression") and s.get("as_of")):
        out.append("own estimate needs the stored regression (path) and its as_of date")
    if k == "bernardo_prior" and not s.get("confirmed"):
        out.append("a Bernardo prior is filed only through `knowledge confirm-prior` (he confirms it)")
    if re.search(r"(?i)\b(goldman|morgan stanley|jpmorgan|j\.p\. morgan|citi(group)?|barclays|ubs|bofa|hsbc|"
                 r"macquarie|societe generale|bnp|broker|sell[- ]side)\b", json.dumps(s)):
        out.append("a broker's quantified sensitivity is never copied in (personal build)")
    return out


def driver_problems(d: dict) -> list[str]:
    out = []
    for k in ("id", "claim", "driver", "target", "sign", "lag"):
        if not d.get(k):
            out.append(f"{k} is required")
    if d.get("id") and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", d["id"]):
        out.append("id: lowercase words and dashes")
    if d.get("sign") not in SIGNS:
        out.append(f"sign must be one of {SIGNS}")
    if d.get("status", "untested") not in STATUSES:
        out.append(f"status must be one of {STATUSES}")
    unknown = set(d) - set(DRIVER_FIELDS)
    if unknown:
        out.append(f"unknown fields {sorted(unknown)}")
    for s in d.get("sizes") or []:
        out += size_problems(s)
    return out


def _file_size(commodity: str, d: dict, s: dict):
    """Each size is also a dated fact, so a specialist can read 'what we believed on date X'."""
    if s.get("value") is None:
        return
    st = {"literature": "literature", "own_estimate": "own_estimate", "bernardo_prior": "bernardo_prior"}[s["kind"]]
    url = s.get("url") or s.get("regression") or f"knowledge/{folder(commodity).relative_to(KNOWLEDGE).as_posix()}/drivers.yaml#{d['id']}"
    facts.record(f"driver:{d['id']}", f"size:{s['kind']}", s["value"], unit=s.get("unit"),
                 valid_from=s.get("as_of") or s.get("confirmed") or s.get("published") or _today(),
                 available_at=None,          # known from when it is filed (an estimate's data cutoff is its valid_from)
                 source_url=url, source_type=st, writer="pmstack.knowledge",
                 author="bernardo" if s["kind"] == "bernardo_prior" else s.get("source"))


def add(commodity: str, d: dict, root: Path | None = None, file_facts: bool = True) -> dict:
    """Add a driver, or merge sizes into an existing one with the same id. Bernardo priors are refused here."""
    d = {k: v for k, v in d.items() if v is not None}
    if any((s or {}).get("kind") == "bernardo_prior" for s in d.get("sizes") or []):
        raise ValueError("a Bernardo prior is filed only through `knowledge confirm-prior` (he confirms it), never by add")
    d.setdefault("status", "untested")
    d.setdefault("sizes", [])
    probs = driver_problems(d)
    if probs:
        raise ValueError("; ".join(probs))
    drivers = load(commodity, root)
    old = next((x for x in drivers if x["id"] == d["id"]), None)
    if old:
        for k in ("claim", "driver", "target", "sign", "lag", "status", "source", "test", "notes"):
            if d.get(k) and k not in ("sizes",):
                old[k] = d[k]
        old.setdefault("sizes", []).extend(s for s in d["sizes"] if s not in old["sizes"])
    else:
        drivers.append(d)
    _write(commodity, drivers, root)
    if file_facts and root is None:
        for s in d["sizes"]:
            _file_size(commodity, d, s)
    return old or d


# ------------------------------------------------------------------ Bernardo priors (inbox -> pending -> confirm)
def propose(entries: list[dict], source_file_sha: str, pending: Path | None = None) -> list[dict]:
    """Code stores proposed priors (from a document Bernardo dropped in the inbox) until he confirms each."""
    pending = pending or PENDING
    pending.parent.mkdir(parents=True, exist_ok=True)
    out = []
    for i, e in enumerate(entries, 1):
        for k in ("commodity", "driver_id", "value", "unit"):
            if e.get(k) in (None, ""):
                raise ValueError(f"proposal {i}: {k} is required")
        pid = f"p{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{i}"
        rec = {"pid": pid, "status": "pending", "from_sha": source_file_sha, **e}
        with pending.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        out.append(rec)
    return out


def pending_list(pending: Path | None = None) -> list[dict]:
    pending = pending or PENDING
    if not pending.exists():
        return []
    rows = [json.loads(x) for x in pending.read_text(encoding="utf-8").splitlines() if x.strip()]
    props: dict[str, dict] = {}
    decided: dict[str, str] = {}
    for r in rows:
        if r.get("status") == "pending" and r["pid"] not in props:
            props[r["pid"]] = r
        else:
            decided[r["pid"]] = r.get("status")
    return [r for pid, r in props.items() if pid not in decided]


def reject_prior(pid: str, reason: str = "", pending: Path | None = None) -> None:
    pending = pending or PENDING
    if not any(r["pid"] == pid for r in pending_list(pending)):
        raise KeyError(f"no pending proposal {pid}")
    with pending.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"pid": pid, "status": "rejected", "on": _today(), "reason": reason}) + "\n")


def confirm_prior(pid: str, edits: dict | None = None, today: str | None = None, root: Path | None = None,
                  pending: Path | None = None) -> dict:
    """Bernardo confirmed (or edited) a proposed prior in chat: file it on the driver and in the facts log."""
    pending = pending or PENDING
    p = next((r for r in pending_list(pending) if r["pid"] == pid), None)
    if not p:
        raise KeyError(f"no pending proposal {pid}")
    p = p | (edits or {})
    today = today or _today()
    size = {"kind": "bernardo_prior", "value": p["value"], "unit": p["unit"], "confirmed": today,
            "note": p.get("note"), "from_sha": p.get("from_sha")}
    if p.get("range"):
        size["range"] = p["range"]
    drivers = load(p["commodity"], root)
    d = next((x for x in drivers if x["id"] == p["driver_id"]), None)
    if d is None:
        d = {"id": p["driver_id"], "claim": p.get("claim") or "", "driver": p.get("driver") or "",
             "target": p.get("target") or "", "sign": p.get("sign") or "?", "lag": p.get("lag") or "?",
             "status": "untested", "sizes": []}
        drivers.append(d)
    probs = [x for x in driver_problems(d | {"sizes": []}) if not x.startswith("sizes")] + size_problems(size)
    if probs:
        raise ValueError("; ".join(probs))
    d.setdefault("sizes", []).append({k: v for k, v in size.items() if v is not None})
    _write(p["commodity"], drivers, root)
    if root is None:
        _file_size(p["commodity"], d, size)
    with pending.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"pid": pid, "status": "confirmed", "on": today}) + "\n")
    return d


# ------------------------------------------------------------------ prior vs estimate
def _interval(s: dict) -> tuple[float, float] | None:
    r = s.get("ci") or s.get("range")
    if isinstance(r, (list, tuple)) and len(r) == 2:
        return float(min(r)), float(max(r))
    return None


def disagreements(commodity: str, root: Path | None = None) -> list[dict]:
    out = []
    for d in load(commodity, root):
        priors = [s for s in d.get("sizes") or [] if s["kind"] == "bernardo_prior" and s.get("value") is not None]
        others = [s for s in d.get("sizes") or [] if s["kind"] != "bernardo_prior" and s.get("value") is not None]
        for p in priors:
            for e in others:
                if (p.get("unit") or "").strip().lower() != (e.get("unit") or "").strip().lower():
                    out.append({"driver": d["id"], "why": "units differ", "prior": p, "estimate": e})
                    continue
                pv, ev = float(p["value"]), float(e["value"])
                iv = _interval(e)
                if pv * ev < 0:
                    why = "opposite sign"
                elif iv and not (iv[0] <= pv <= iv[1]):
                    why = f"prior outside the {e['kind'].replace('_', ' ')} interval"
                elif not iv and ev and abs(pv - ev) / abs(ev) > DISAGREE_REL:
                    why = f"prior and {e['kind'].replace('_', ' ')} differ by more than {int(DISAGREE_REL * 100)}%"
                else:
                    continue
                out.append({"driver": d["id"], "why": why, "prior": p, "estimate": e})
    return out


def check(commodity: str, root: Path | None = None) -> list[dict]:
    """Rebuild the code block in open-questions.md from the disagreements."""
    dis = disagreements(commodity, root)
    f = folder(commodity, root) / "open-questions.md"
    text = f.read_text(encoding="utf-8") if f.exists() else f"# Open questions: {commodity}\n"
    lines = [BLOCK_START, "## Prior vs estimate (code)", ""]
    if not dis:
        lines.append("No disagreement between a Bernardo prior and an estimate.")
    for x in dis:
        p, e = x["prior"], x["estimate"]
        lines.append(f"- **{x['driver']}**: {x['why']}. Prior {p['value']} {p['unit']} (confirmed {p.get('confirmed')}) vs "
                     f"{e['kind'].replace('_', ' ')} {e['value']} {e['unit']} ({e.get('source') or e.get('regression')}). Test it before using either.")
    lines.append(BLOCK_END)
    block = "\n".join(lines)
    if BLOCK_START in text:
        text = re.sub(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END), block, text, flags=re.S)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    return dis


# ------------------------------------------------------------------ render
def _fmt_size(s: dict) -> str:
    v = s.get("value")
    rng = _interval(s)
    core = f"{v} {s.get('unit', '')}".strip() if v is not None else f"{rng[0]} to {rng[1]} {s.get('unit', '')}"
    if s["kind"] == "literature":
        band = f", range {rng[0]} to {rng[1]}" if rng and v is not None else ""
        return f"literature: {core}{band} ([{s.get('source')}]({s.get('url')}){', ' + s['where'] if s.get('where') else ''})"
    if s["kind"] == "own_estimate":
        ci = f", 90% CI {rng[0]} to {rng[1]}" if rng and v is not None else ""
        return f"own estimate: {core}{ci}, n {s.get('n', '?')}, as of {s.get('as_of')} ([regression]({s.get('regression')}))"
    return f"Bernardo prior: {core} (confirmed {s.get('confirmed')})"


def render(commodity: str, root: Path | None = None) -> Path:
    d = folder(commodity, root)
    drivers = load(commodity, root)
    out = [f"# Drivers: {d.name}", "",
           "Rendered from `drivers.yaml` by `pmstack/knowledge.py`; do not edit by hand. Each size says where it came from "
           "(literature, own estimate, Bernardo prior). Status comes from the testing gate (`/research`); \"untested\" claims "
           "are hypotheses, not signals.", ""]
    for x in drivers:
        out += [f"## {x['id']}", "", f"- **Claim:** {x['claim']}", f"- **Driver → target:** {x['driver']} → {x['target']}",
                f"- **Sign / lag:** {x['sign']} / {x['lag']}", f"- **Status:** {x.get('status', 'untested')}"
                + (f" (study `{x['test']}`)" if x.get("test") else "")]
        if x.get("source"):
            out.append(f"- **Source:** {x['source']}")
        for s in x.get("sizes") or []:
            out.append(f"- Size, {_fmt_size(s)}")
        if x.get("notes"):
            out.append(f"- Notes: {x['notes']}")
        out.append("")
    path = d / "drivers.md"
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    return path


def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack knowledge")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="add drivers (JSON list) to a commodity's drivers.yaml")
    a.add_argument("commodity")
    a.add_argument("--json", required=True)
    pr = sub.add_parser("propose", help="store proposed Bernardo priors from an inbox document (pending his confirmation)")
    pr.add_argument("--json", required=True)
    pr.add_argument("--sha", required=True, help="sha12 of the inbox file")
    sub.add_parser("pending", help="list priors waiting for confirmation")
    c = sub.add_parser("confirm-prior", help="file a prior Bernardo confirmed in chat")
    c.add_argument("pid")
    c.add_argument("--set", nargs="*", default=[], help="edits k=v (value, unit, sign, lag, note...)")
    rj = sub.add_parser("reject-prior", help="drop a proposed prior Bernardo did not confirm")
    rj.add_argument("pid")
    rj.add_argument("--reason", default="")
    ch = sub.add_parser("check", help="prior vs estimate: rebuild the code block in open-questions.md")
    ch.add_argument("commodity")
    r = sub.add_parser("render", help="re-render drivers.md")
    r.add_argument("commodity")
    x = p.parse_args(argv)
    rid = runlog.new_run_id()
    if x.cmd == "add":
        items = json.loads(Path(x.json).read_text(encoding="utf-8"))
        for d in items if isinstance(items, list) else [items]:
            add(x.commodity, d)
        runlog.log(rid, "knowledge:add", "ok", commodity=x.commodity, drivers=len(items) if isinstance(items, list) else 1)
        print(render(x.commodity).relative_to(ROOT).as_posix())
    elif x.cmd == "propose":
        recs = propose(json.loads(Path(x.json).read_text(encoding="utf-8")), x.sha)
        print(json.dumps(recs, indent=2, ensure_ascii=False))
    elif x.cmd == "pending":
        print(json.dumps(pending_list(), indent=2, ensure_ascii=False))
    elif x.cmd == "confirm-prior":
        edits = {}
        for kv in x.set:
            k, v = kv.split("=", 1)
            try:
                v = float(v)
            except ValueError:
                pass
            edits[k] = v
        d = confirm_prior(x.pid, edits)
        runlog.log(rid, "knowledge:confirm-prior", "ok", pid=x.pid, driver=d["id"])
        print(f"filed on {d['id']}")
    elif x.cmd == "reject-prior":
        reject_prior(x.pid, x.reason)
        runlog.log(rid, "knowledge:reject-prior", "ok", pid=x.pid)
        print(f"{x.pid} rejected")
    elif x.cmd == "check":
        dis = check(x.commodity)
        print(f"{len(dis)} disagreement(s)")
    elif x.cmd == "render":
        print(render(x.commodity).relative_to(ROOT).as_posix())
    return 0
