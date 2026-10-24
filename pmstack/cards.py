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
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
WINDOW_RE = re.compile(r"^[\s-]?(?:days?|weeks?|months?|years?|sessions?|quarters?|[dwmy])\b", re.I)   # "4-week", "5 days", "10y"
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


def _numbers(text: str) -> list[tuple[float, int, str]]:
    """(value, decimals, raw) for each figure in a text, skipping citation ids, dates and plain years."""
    t = CITE_RE.sub(" ", text)
    t = DATE_RE.sub(" ", t)
    out = []
    for m in NUM_RE.finditer(t):
        raw = m.group(0)
        s = raw.replace(",", "").replace("−", "-")
        try:
            v = float(s)
        except ValueError:
            continue
        dec = len(s.split(".")[1]) if "." in s else 0
        if dec == 0 and 1900 <= abs(v) <= 2100:      # a year ("since 2018"), not a figure
            continue
        if dec == 0 and abs(v) <= 260 and WINDOW_RE.match(t[m.end():m.end() + 10]):   # a window, not a figure
            continue
        out.append((v, dec, raw))
    return out


def _source_values(card: dict) -> list[float]:
    vals = []
    for s in card.get("sources") or []:
        v = s.get("value") if isinstance(s, dict) else None
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            vals.append(float(v))
        elif isinstance(v, str):
            vals += [x[0] for x in _numbers(v)]
    return vals


def _matches(x: float, dec: int, pool: list[float]) -> bool:
    tol = 0.5 * 10 ** (-dec) + 1e-9
    return any(abs(abs(x) - abs(v)) <= tol for v in pool)


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
        if isinstance(s, dict) and s.get("date") and str(s["date"]) > asof:
            out.append(f"sources.{s.get('id')}: dated {s['date']}, after the card's as_of (look-ahead)")
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
        for v, dec, raw in _numbers(text):
            if not _matches(v, dec, pool):
                out.append(f"{where}: figure {raw} is not a cited source value (numbers come from code)")
    if card.get("level") in ("complex", "generalist") and not card.get("children"):
        out.append("children: a complex or generalist card lists the cards it combines")
    return out


def validate(card: dict, today: date | None = None) -> list[str]:
    probs = schema_problems(card)
    return probs + ([] if probs else semantic_problems(card, today))


def save(card: dict, writer: str = "pmstack.cards", root: Path | None = None, today: date | None = None) -> Path:
    """Validate and write cards/<subject>/<as_of>-<author>[-n].json. Never overwrites."""
    probs = validate(card, today)
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
    s = sub.add_parser("save", help="validate and save a card under cards/<subject>/")
    s.add_argument("file")
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
    probs = validate(card)
    if a.cmd == "validate":
        print("ok" if not probs else "\n".join(probs))
        return 0 if not probs else 1
    try:
        path = save(card)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    runlog.log(runlog.new_run_id(), a.step, "ok", card=path.relative_to(ROOT).as_posix(), subject=card["subject"],
               as_of=card["as_of"], sources=len(card["sources"]))
    print(path.relative_to(ROOT).as_posix())
    return 0
