"""State cards (specialists S0): the one JSON contract every specialist, complex and the generalist return.

Why (docs/research/specialists-architecture.md): MAST (NeurIPS 2025) traces most multi-agent failures to loose
specs, misalignment between agents and weak verification; Wang et al. (2026) got their only commodity gain from
an LLM constrained to a JSON contract. So a specialist's answer is a card that code validates before it is
saved: the schema (config/state_card.schema.json), no look-ahead (no source dated after the card), and every
number in its text tied to a cited figure. The model never saves a card itself; `save` does, and never
overwrites one.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import runlog

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "config" / "state_card.schema.json"
CARDS = ROOT / "cards"
TEXT_VIEWS = ("balance_view", "curve_shape", "positioning", "narrative_stage")
TEXT_LISTS = ("what_changed", "would_change_view", "inference", "open_questions", "cross_links")
CITE_RE = re.compile(r"\[(s\d+)\]")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}"                                                  # ISO
                     r"|\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b"   # 24 Oct 2026
                     r"|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, \d{4}\b")  # Oct 24, 2026
# a window is a hyphenated span ("4-week", "5-day", "12-month"), never a quantity ("25 days" of supply is a figure)
WINDOW_RE = re.compile(r"^(?:-(?:day|week|month|year|session|quarter)s?|\s(?:weeks?|months?|years?|sessions?|quarters?|releases?))\b", re.I)
YEAR_CTX = re.compile(r"^\s?(?:%|\$|/|bbl|b/d|mb|kb|oz|t\b|tonnes|usd|bp|sd|x\b)", re.I)   # "2,050 $/oz" is a figure, not a year
NUM_RE = re.compile(r"(?<![\w.])[-+−]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.])[-+−]?\d+(?:\.\d+)?")


def schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ a small JSON Schema subset (no dependency)
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _is(v, t: str) -> bool:
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def _check(v, s: dict, root: dict, where: str, out: list[str]):
    if "$ref" in s:
        ref = s["$ref"].split("/")[-1]
        s = root["$defs"][ref]
    t = s.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        if not any(_is(v, x) for x in ts):
            out.append(f"{where}: expected {'/'.join(ts)}")
            return
    if "enum" in s and v not in s["enum"]:
        out.append(f"{where}: must be one of {s['enum']}")
    if isinstance(v, str):
        if len(v) < s.get("minLength", 0):
            out.append(f"{where}: empty")
        if "pattern" in s and not re.search(s["pattern"], v):
            out.append(f"{where}: does not match {s['pattern']}")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if "minimum" in s and v < s["minimum"]:
            out.append(f"{where}: below {s['minimum']}")
        if "maximum" in s and v > s["maximum"]:
            out.append(f"{where}: above {s['maximum']}")
    if isinstance(v, list):
        if len(v) < s.get("minItems", 0):
            out.append(f"{where}: needs at least {s['minItems']} item(s)")
        if "maxItems" in s and len(v) > s["maxItems"]:
            out.append(f"{where}: at most {s['maxItems']} items")
        for i, x in enumerate(v):
            if "items" in s:
                _check(x, s["items"], root, f"{where}[{i}]", out)
    if isinstance(v, dict):
        for k in s.get("required", []):
            if k not in v:
                out.append(f"{where}.{k}: missing")
        props = s.get("properties", {})
        for k, x in v.items():
            if k in props:
                _check(x, props[k], root, f"{where}.{k}", out)
            elif s.get("additionalProperties") is False:
                out.append(f"{where}.{k}: unknown field")


def schema_problems(card: dict) -> list[str]:
    sc = schema()
    out: list[str] = []
    _check(card, sc, sc, "card", out)
    return out


# ------------------------------------------------------------------ semantic checks
def _texts(card: dict) -> list[tuple[str, str]]:
    out = []
    for k in TEXT_VIEWS:
        v = card.get(k)
        if isinstance(v, dict) and isinstance(v.get("text"), str):
            out.append((k, v["text"]))
    for k in TEXT_LISTS:
        for i, x in enumerate(card.get(k) or []):
            if isinstance(x, str):
                out.append((f"{k}[{i}]", x))
    pr = card.get("probability")
    if isinstance(pr, dict) and isinstance(pr.get("statement"), str):
        out.append(("probability.statement", pr["statement"]))
    for i, e in enumerate(card.get("next_events") or []):
        if isinstance(e, dict) and isinstance(e.get("event"), str):
            out.append((f"next_events[{i}].event", e["event"]))
    return out


def _numbers(text: str) -> list[tuple[float, int, str, bool]]:
    """(value, decimals, raw, explicit sign) for each figure in a text, skipping citation ids, dates, plain years and
    hyphenated windows (review A15: "25 days" and "2,050 $/oz" are figures and must be cited)."""
    t = CITE_RE.sub(" ", text)
    t = DATE_RE.sub(" ", t)
    out = []
    for m in NUM_RE.finditer(t):
        raw = m.group(0)
        s = raw.replace(",", "").replace("\u2212", "-")
        try:
            v = float(s)
        except ValueError:
            continue
        dec = len(s.split(".")[1]) if "." in s else 0
        before, after = t[max(0, m.start() - 1):m.start()], t[m.end():m.end() + 8]
        if (dec == 0 and "," not in raw and 1900 <= abs(v) <= 2100 and before != "$" and not YEAR_CTX.match(after)):
            continue                                   # a year ("since 2018")
        if dec == 0 and abs(v) <= 260 and WINDOW_RE.match(after):
            continue                                   # a window ("4-week")
        out.append((v, dec, raw, raw[:1] in "+-\u2212"))
    return out


def _source_values(card: dict) -> list[float]:
    """Numeric source values only (a string value no longer whitelists the numbers inside it: review A15)."""
    vals = []
    for s in card.get("sources") or []:
        v = s.get("value") if isinstance(s, dict) else None
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            vals.append(float(v))
            if str(s.get("unit") or "").lower() in ("share", "fraction"):    # a share of 0.638 may be written 64%
                vals.append(100 * float(v))
    return vals


def _matches(x: float, dec: int, pool: list[float], signed: bool) -> bool:
    """A figure written with an explicit sign must match the sign too ("+3.1" is not a draw of -3.1); an unsigned
    figure may be the magnitude ("drew 3,060 kbbl" for a change of -3060)."""
    tol = 0.5 * 10 ** (-dec) + 1e-9
    if signed:
        return any(abs(x - v) <= tol for v in pool)
    return any(abs(abs(x) - abs(v)) <= tol for v in pool)


def pack_problems(card: dict, packs: list[dict]) -> list[str]:
    """Every card source must be a row of the input pack(s) it was built from: same id, value, date and url (review
    A15: otherwise the model could write its own 'source' and cite it). Complex and generalist cards pass the child
    cards as packs."""
    rows = {}
    for pk in packs:
        for r in pk.get("sources") or []:
            rows.setdefault(r.get("id"), []).append(r)
    out = []
    for s in card.get("sources") or []:
        cand = rows.get(s.get("id")) or []
        ok = any(r.get("value") == s.get("value") and r.get("date") == s.get("date") and r.get("url") == s.get("url")
                 for r in cand)
        if not ok:
            out.append(f"sources.{s.get('id')}: not a row of the input pack (value, date and url must be copied unchanged)")
    return out


def semantic_problems(card: dict, today: date | None = None) -> list[str]:
    out = []
    today = today or (datetime.now(timezone.utc) - timedelta(hours=3)).date()
    asof = card.get("as_of")
    try:
        ad = date.fromisoformat(asof)
    except (TypeError, ValueError):
        return ["as_of: not a date"]
    if ad > today:
        out.append("as_of: after today")
    ids = [s.get("id") for s in card.get("sources") or [] if isinstance(s, dict)]
    if len(ids) != len(set(ids)):
        out.append("sources: duplicate ids")
    for s in card.get("sources") or []:
        if not isinstance(s, dict):
            continue
        if s.get("date") and str(s["date"]) > asof:
            out.append(f"sources.{s.get('id')}: dated {s['date']}, after the card's as_of (look-ahead)")
        if not s.get("date") and isinstance(s.get("value"), (int, float)):
            out.append(f"sources.{s.get('id')}: a numeric source needs its date (look-ahead check)")
    pr = card.get("probability")
    if isinstance(pr, dict) and str(pr.get("by", "9")) <= asof:
        out.append("probability.by: must be after as_of")
    for e in card.get("next_events") or []:
        if isinstance(e, dict) and str(e.get("date", "")) < asof:
            out.append(f"next_events: {e.get('date')} is before as_of")
    pool = _source_values(card)
    cited = set()
    for where, text in _texts(card):
        for ref in CITE_RE.findall(text):
            cited.add(ref)
            if ref not in ids:
                out.append(f"{where}: cites {ref}, which is not in sources")
        for v, dec, raw, signed in _numbers(text):
            if not _matches(v, dec, pool, signed):
                out.append(f"{where}: figure {raw} is not a cited source value (numbers come from code)")
    if card.get("level") in ("complex", "generalist") and not card.get("children"):
        out.append("children: a complex or generalist card lists the cards it combines")
    return out


def validate(card: dict, today: date | None = None, packs: list[dict] | None = None) -> list[str]:
    probs = schema_problems(card)
    if probs:
        return probs
    return semantic_problems(card, today) + (pack_problems(card, packs) if packs is not None else [])


def save(card: dict, writer: str = "pmstack.cards", root: Path | None = None, today: date | None = None,
         packs: list[dict] | None = None) -> Path:
    """Validate (schema, figures, look-ahead, and every source against the input pack) and write
    cards/<subject>/<as_of>-<author>[-n].json. Never overwrites. A pack is required."""
    if not packs:
        raise ValueError("card rejected: pass the input pack(s) it was built from (sources are checked against them)")
    probs = validate(card, today, packs)
    if probs:
        raise ValueError("card rejected:\n  " + "\n  ".join(probs))
    root = root or CARDS
    who = re.sub(r"[^a-z0-9]+", "-", card["author"].split("/")[0].lower()).strip("-") or "card"
    folder = root / card["subject"]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{card['as_of']}-{who}.json"
    n = 2
    while path.exists():
        path = folder / f"{card['as_of']}-{who}-{n}.json"
        n += 1
    path.write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def latest(subject: str, asof: str | None = None, root: Path | None = None) -> Path | None:
    """The newest saved card on a subject dated on or before `asof` (point in time)."""
    root = root or CARDS
    def key(f: Path):
        m = re.search(r"-(\d+)$", f.stem)
        return (f.name[:10], int(m.group(1)) if m and not re.search(r"\d{4}-\d{2}-\d{2}$", f.stem) else 1)
    files = sorted((root / subject).glob("*.json"), key=key) if (root / subject).exists() else []
    if asof:
        files = [f for f in files if f.name[:10] <= asof]
    return files[-1] if files else None


def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack cards")
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="check a card JSON against the schema and the figure rules")
    v.add_argument("file")
    v.add_argument("--pack", nargs="*", help="also check the sources against the input pack(s)")
    s = sub.add_parser("save", help="validate and save a card under cards/<subject>/")
    s.add_argument("file")
    s.add_argument("--pack", nargs="+", required=True, help="the input pack(s) (or child cards) the card was built from")
    s.add_argument("--step", default="cards:save")
    l = sub.add_parser("latest", help="newest saved card on a subject")
    l.add_argument("subject")
    l.add_argument("--date")
    a = p.parse_args(argv)
    if a.cmd == "latest":
        f = latest(a.subject, a.date)
        print(f.relative_to(ROOT).as_posix() if f else "none")
        return 0
    card = json.loads(Path(a.file).read_text(encoding="utf-8"))
    packs = [json.loads(Path(x).read_text(encoding="utf-8")) for x in (a.pack or [])] or None
    probs = validate(card, packs=packs)
    if a.cmd == "validate":
        print("ok" if not probs else "\n".join(probs))
        return 0 if not probs else 1
    try:
        path = save(card, packs=packs)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    runlog.log(runlog.new_run_id(), a.step, "ok", card=path.relative_to(ROOT).as_posix(), subject=card["subject"],
               as_of=card["as_of"], sources=len(card["sources"]))
    print(path.relative_to(ROOT).as_posix())
    return 0
