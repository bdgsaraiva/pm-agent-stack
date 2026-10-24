"""Inbox ingestion (specialists S0; agent 10 folded in): Bernardo's studies and selected public reports -> knowledge.

knowledge/inbox/ holds the files he drops (gitignored except README.md and ledger.jsonl). For each file:
  1. screen    code reads only the first pages and flags broker / fund / licence markers (classification only)
  2. classify  Bernardo confirms the type. Allowed: own_study, own_note, public_report, academic.
               Refused: broker (incl. summaries or extracts of broker research made elsewhere) and fund.
               A refused file is not read further, nothing from it is stored, and he is asked to remove it;
               the ledger keeps only its hash and the decision (personal build, CLAUDE.md hard rules).
  3. ingest    the digester stores the text locally (data/transcripts/, gitignored) and the digest skill writes
               the summary note in his podcast-summary format with checked claim cards
  4. drivers   testable claims go to knowledge/<complex>/<commodity>/drivers.yaml (pmstack.knowledge): literature
               sizes directly with their citation; his own numbers as proposed priors he confirms one by one
  5. facts     dated figures from the document go to the facts log, each one checked against an ok claim card's
               quote (the number must be in the quote) - code files them, never the model
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import facts, runlog

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "knowledge" / "inbox"
LEDGER = INBOX / "ledger.jsonl"
ALLOWED = {"own_study": "own_study", "own_note": "own_note", "public_report": "public_report", "academic": "academic"}
REFUSED = ("broker", "fund")
SKIP = {"README.md", "ledger.jsonl", "pending.jsonl", ".gitkeep"}
SCREEN_CHARS = 6000           # classification only: never read a file further before it is classified

# markers that suggest broker / sell-side research, fund material or restricted licences (case-insensitive)
MARKERS = {
    "broker": [r"analyst certification", r"important disclosures", r"price target", r"equity research", r"commodities research",
               r"global research", r"sell[- ]side", r"this report (?:is|has been) prepared by", r"for institutional (?:investors|clients) only",
               r"\b(?:goldman sachs|morgan stanley|j\.?p\.? ?morgan|citigroup|citi research|barclays|ubs|bofa|bank of america|hsbc|"
               r"macquarie|soci[eé]t[eé] g[eé]n[eé]rale|bnp paribas|jefferies|wells fargo securities|rbc capital|itau bba|xp investimentos|btg pactual)\b",
               r"\bbroker\b", r"distribution (?:is )?restricted"],
    "fund": [r"\bconfidential\b", r"internal use only", r"\bour (?:position|book|portfolio|fund)\b", r"\bp&l\b", r"\bpnl\b",
             r"order (?:book|history)", r"\bnav\b", r"investment committee"],
    "licence": [r"bloomberg l\.?p\.?", r"bloomberg terminal", r"\(c\) ?bloomberg", r"source: bloomberg", r"refinitiv", r"lseg data"],
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha12(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _head_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        out = ""
        for page in PdfReader(str(path)).pages[:3]:
            out += (page.extract_text() or "") + "\n"
            if len(out) >= SCREEN_CHARS:
                break
        return out[:SCREEN_CHARS]
    with path.open("r", encoding="utf-8", errors="replace") as f:
        return f.read(SCREEN_CHARS)


UNREADABLE = {".docx", ".pptx", ".xlsx", ".xls", ".doc", ".ppt", ".zip", ".png", ".jpg", ".jpeg"}


def screen(path: Path) -> dict:
    """Marker hits in the first pages only (classification aid; Bernardo decides the type)."""
    if path.suffix.lower() in UNREADABLE:
        return {"file": path.name, "sha12": sha12(path), "markers": {}, "suggest": None, "readable": False,
                "note": "not screened (format not read as text): classify by hand, and refuse if in doubt"}
    text = _head_text(path).lower()
    if len(text.strip()) < 50:
        return {"file": path.name, "sha12": sha12(path), "markers": {}, "suggest": None, "readable": False,
                "note": "no text found (scanned PDF?): classify by hand, and refuse if in doubt"}
    hits = {k: sorted({m.group(0) for p in pats for m in re.finditer(p, text)}) for k, pats in MARKERS.items()}
    hits = {k: v for k, v in hits.items() if v}
    sug = "broker" if "broker" in hits else "fund" if "fund" in hits else None
    return {"file": path.name, "sha12": sha12(path), "markers": hits, "suggest": sug,
            "note": "markers are a screen, not a verdict: confirm the type with `inbox classify`"}


def ledger(path: Path | None = None) -> list[dict]:
    path = path or LEDGER
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def decision(sha: str, path: Path | None = None) -> dict | None:
    rows = [r for r in ledger(path) if r.get("sha12") == sha]
    return rows[-1] if rows else None


def files(inbox: Path | None = None) -> list[Path]:
    inbox = inbox or INBOX
    return sorted(p for p in inbox.glob("*") if p.is_file() and p.name not in SKIP and not p.name.startswith("."))


def status(inbox: Path | None = None, led: Path | None = None) -> list[dict]:
    out = []
    for p in files(inbox):
        s = sha12(p)
        d = decision(s, led)
        row = {"file": p.name, "sha12": s, "type": d.get("type") if d else None,
               "state": (d.get("state") if d else "unclassified")}
        if d and d.get("type") in REFUSED:
            row["state"] = "remove: refused type, nothing stored"
        out.append(row)
    return out


def classify(path: Path, typ: str, by: str = "bernardo", led: Path | None = None, note: str | None = None) -> dict:
    led = led or LEDGER
    if typ not in ALLOWED and typ not in REFUSED:
        raise ValueError(f"type must be one of {sorted(ALLOWED) + list(REFUSED)}")
    s = sha12(path)
    if any(r.get("sha12") == s and r.get("type") in REFUSED for r in ledger(led)):
        raise PermissionError("this file was refused (broker or fund): the decision is final; delete the file")
    if typ in REFUSED:
        # nothing about the content is kept: no filename, no title, no note text
        rec = {"sha12": s, "type": typ, "state": "refused", "decided_by": by, "at": _now()}
    else:
        rec = {"sha12": s, "file": path.name, "type": typ, "state": "classified", "decided_by": by, "at": _now(),
               **({"note": note} if note else {})}
    led.parent.mkdir(parents=True, exist_ok=True)
    with led.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def ingest(path: Path, led: Path | None = None, out_dir: Path | None = None) -> dict:
    """Store the text locally through the digester (only for an allowed, classified file)."""
    s = sha12(path)
    d = decision(s, led)
    if any(r.get("sha12") == s and r.get("type") in REFUSED for r in ledger(led)):
        raise PermissionError("refused type (broker or fund): not ingested; ask Bernardo to remove the file")
    if not d:
        raise PermissionError("classify the file first (`inbox screen`, then `inbox classify <file> --type ...`)")
    if d["type"] in REFUSED:
        raise PermissionError("refused type (broker or fund): not ingested; ask Bernardo to remove the file")
    from . import digest
    meta = digest.fetch(str(path), out_dir=out_dir)
    rec = {"sha12": s, "file": path.name, "type": d["type"], "state": "ingested", "transcript": meta["sha12"], "at": _now()}
    with (led or LEDGER).open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return {**rec, "words": meta.get("words"), "kind": meta.get("kind"), "source_type": ALLOWED[d["type"]],
            "next": ["digest skill: chunks -> cards -> note under notes/research/<series>/ -> digest save",
                     "knowledge add <commodity> --json drivers.json (literature sizes with citations)",
                     "knowledge propose --sha <sha12> --json priors.json (his own numbers; he confirms each)",
                     "inbox facts <note.md> --json facts.json (dated figures, each tied to an ok card)"]}


def file_facts(note: str | Path, items: list[dict], source_type: str, writer: str = "pmstack.inbox") -> list[dict]:
    """File dated figures from a digested note. Each item names an ok card of that note whose quote holds the value."""
    from . import digest
    note = Path(note)
    meta = digest.read_note(note)
    rep = json.loads(note.with_suffix(".cards.json").read_text(encoding="utf-8"))
    cards = {c["id"].split("#")[-1]: c for c in rep["cards"]}
    avail = str(meta.get("published") or meta.get("date"))[:10]
    url = meta.get("url") or digest.note_key(note)
    out, problems = [], []
    for i, it in enumerate(items, 1):
        c = cards.get(str(it.get("card", "")))
        if not c or c.get("status") != "ok":
            problems.append(f"item {i}: card {it.get('card')} is missing or not ok")
            continue
        quote = c.get("quote") or (c.get("card") or {}).get("quote") or ""
        v = it.get("value")
        if isinstance(v, (int, float)) and not digest._has_number(float(v), digest.numbers_in(quote)):
            problems.append(f"item {i}: {v} is not in card {it['card']}'s quote")
            continue
        out.append(it)
    if problems:
        raise ValueError("; ".join(problems))
    recs = []
    for it in out:
        recs.append(facts.record(it["subject"], it["predicate"], it["value"], unit=it.get("unit"),
                                 valid_from=it["valid_from"], available_at=avail, source_url=url,
                                 source_type=source_type, writer=writer, author=meta.get("series") or meta.get("type"),
                                 note=f"{digest.note_key(note)}#{it['card']}"))
    return recs


def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack inbox")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="files in knowledge/inbox and their state")
    s = sub.add_parser("screen", help="marker screen on the first pages (classification only)")
    s.add_argument("file")
    c = sub.add_parser("classify", help="record the type Bernardo confirmed")
    c.add_argument("file")
    c.add_argument("--type", required=True, choices=sorted(ALLOWED) + list(REFUSED))
    c.add_argument("--note")
    i = sub.add_parser("ingest", help="store the text locally (allowed types only), then follow the digest skill")
    i.add_argument("file")
    f = sub.add_parser("facts", help="file dated figures from a digested note (each tied to an ok card)")
    f.add_argument("note")
    f.add_argument("--json", required=True)
    f.add_argument("--source-type", required=True, choices=sorted(ALLOWED.values()))
    a = p.parse_args(argv)

    def _path(x):
        q = Path(x)
        return q if q.exists() else INBOX / x
    rid = runlog.new_run_id()
    if a.cmd == "list":
        print(json.dumps(status(), indent=2, ensure_ascii=False))
    elif a.cmd == "screen":
        print(json.dumps(screen(_path(a.file)), indent=2, ensure_ascii=False))
    elif a.cmd == "classify":
        rec = classify(_path(a.file), a.type, note=a.note)
        runlog.log(rid, "inbox:classify", "ok", sha12=rec["sha12"], type=a.type)
        if a.type in REFUSED:
            print(f"{a.type}: not read further and nothing stored. Please delete the file from knowledge/inbox/ "
                  f"(broker-informed knowledge belongs to the corporate copy).")
        else:
            print(json.dumps(rec, indent=2, ensure_ascii=False))
    elif a.cmd == "ingest":
        res = ingest(_path(a.file))
        runlog.log(rid, "inbox:ingest", "ok", sha12=res["sha12"], type=res["type"], transcript=res["transcript"])
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif a.cmd == "facts":
        recs = file_facts(a.note, json.loads(Path(a.json).read_text(encoding="utf-8")), a.source_type)
        runlog.log(rid, "inbox:facts", "ok", note=a.note, facts=len(recs))
        print(f"{len(recs)} fact(s) filed")
    return 0
