"""Point-in-time memory (specialists S0): one append-only log of dated facts, read as of any date.

Why this shape (docs/research/specialists-architecture.md):
  - FinMem / FinCon keep agent memory in layers and route lessons to the analyst concerned; Zep/Graphiti keep
    bi-temporal facts that are invalidated, never deleted. A specialist must be able to say what was known on a
    date without seeing later revisions (look-ahead: agent 8's review found four ways it leaks).
  - Two clocks per fact: **valid time** (valid_from / valid_to: when the fact is true in the world) and
    **knowledge time** (available_at: when it became public; recorded_at: when this repo wrote it). `as_of(d)`
    uses only facts available by d. Backfilled history carries its real release date in available_at, so a
    fact filed today about a 2024 report still reads as known in 2024.
  - Nothing is overwritten. The log only grows (data/facts/facts.jsonl: one JSON object a line, so git merges
    it like logs/runs.jsonl). A newer fact on the same subject and predicate supersedes the old one by closing
    its valid_to at the new valid_from - derived on read, so a reader as of an earlier date still sees the old
    fact open. A revision (same valid_from, new value) wins from its own available_at; before that, the first
    print stands (vintages). A retraction is a row of its own.
  - Only code writes here, always with provenance: `writer` must be a pmstack function, `source_url` and
    `source_type` are required. Specialists (models) never call record(); code saves what they cite.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime, time, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "data" / "facts" / "facts.jsonl"

COLS = ["fact_id", "op", "subject", "predicate", "value", "value_num", "unit", "valid_from", "valid_to",
        "available_at", "recorded_at", "source_url", "source_type", "confidence", "author", "writer", "target", "note"]
# where a figure or claim comes from; drivers' sizes use the last three (specialists-kickoff.md section 4)
SOURCE_TYPES = ("data", "agency_report", "public_report", "academic", "own_study", "own_note", "journal",
                "literature", "own_estimate", "bernardo_prior")
CONFIDENCE = ("low", "medium", "high")
WRITER_RE = re.compile(r"^pmstack\.[a-z_][a-z0-9_.]*$")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _day(x) -> date | None:
    if x is None or x == "" or (isinstance(x, float) and pd.isna(x)):
        return None
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    return date.fromisoformat(str(x)[:10])


def _ts(x) -> datetime | None:
    """A knowledge timestamp (UTC). A bare date means the end of that day: a release on day d is usable on d."""
    if x is None or x == "":
        return None
    if isinstance(x, datetime):
        return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
    s = str(x)
    if len(s) <= 10:
        return datetime.combine(date.fromisoformat(s), time(23, 59, 59), tzinfo=timezone.utc)
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _num(v):
    if isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def _id(*parts) -> str:
    return hashlib.sha256("\x1f".join("" if p is None else str(p) for p in parts).encode()).hexdigest()[:16]


def load(path: Path | None = None) -> pd.DataFrame:
    path = path or FACTS
    if not path.exists():
        return pd.DataFrame(columns=COLS)
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    df = pd.DataFrame(rows, columns=COLS) if rows else pd.DataFrame(columns=COLS)
    return df


def _append(rec: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


def record(subject: str, predicate: str, value, *, valid_from, source_url: str, source_type: str, writer: str,
           unit: str | None = None, available_at=None, valid_to=None, confidence: str | None = None,
           author: str | None = None, note: str | None = None, path: Path | None = None) -> dict:
    """Append one fact. Re-recording the same fact (same subject, predicate, valid_from, value, unit, source and
    availability) is a no-op, so a daily filer can re-run. `available_at` defaults to now (unknown release time
    = when we learnt it: never earlier)."""
    path = path or FACTS
    subject, predicate = (subject or "").strip(), (predicate or "").strip()
    problems = []
    if not subject or not predicate:
        problems.append("subject and predicate are required")
    if value is None or value == "":
        problems.append("value is required")
    if not (source_url or "").strip():
        problems.append("source_url is required (provenance)")
    if source_type not in SOURCE_TYPES:
        problems.append(f"source_type must be one of {SOURCE_TYPES}")
    if not WRITER_RE.match(writer or ""):
        problems.append("writer must be a pmstack code function (e.g. pmstack.balance): models never write memory")
    if confidence is not None and confidence not in CONFIDENCE:
        problems.append(f"confidence must be one of {CONFIDENCE}")
    vf = _day(valid_from)
    if vf is None:
        problems.append("valid_from is required")
    vt = _day(valid_to)
    if vf and vt and vt <= vf:
        problems.append("valid_to must be after valid_from")
    now = _now()
    av = _ts(available_at) or now
    if av > now and av.date() == now.date():      # "released today" (a bare date = end of day): known from now
        av = now
    if av > now:
        problems.append("available_at is in the future")
    if problems:
        raise ValueError("; ".join(problems))
    fid = _id(subject, predicate, vf, value, unit, source_url, av.isoformat())
    df = load(path)
    if len(df) and (df["fact_id"] == fid).any():
        return df[df["fact_id"] == fid].iloc[0].to_dict()
    rec = {"fact_id": fid, "op": "assert", "subject": subject, "predicate": predicate,
           "value": value if isinstance(value, (int, float, str)) else json.dumps(value),
           "value_num": _num(value), "unit": unit, "valid_from": vf.isoformat(),
           "valid_to": vt.isoformat() if vt else None, "available_at": av.isoformat(),
           "recorded_at": now.isoformat(), "source_url": source_url.strip(), "source_type": source_type,
           "confidence": confidence, "author": author, "writer": writer, "target": None, "note": note}
    _append(rec, path)
    return rec


def retract(fact_id: str, *, reason: str, writer: str, path: Path | None = None) -> dict:
    """Mark a fact as wrong from now on (it stays in the log, and in reads as of earlier dates)."""
    path = path or FACTS
    if not WRITER_RE.match(writer or ""):
        raise ValueError("writer must be a pmstack code function")
    df = load(path)
    if not len(df) or not ((df["fact_id"] == fact_id) & (df["op"] == "assert")).any():
        raise KeyError(f"no fact {fact_id}")
    now = _now()
    rec = {c: None for c in COLS} | {"fact_id": _id("retract", fact_id, now.isoformat()), "op": "retract",
                                      "target": fact_id, "available_at": now.isoformat(),
                                      "recorded_at": now.isoformat(), "writer": writer, "note": reason}
    _append(rec, path)
    return rec


def known(known_at=None, path: Path | None = None, df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Every fact as the repo would have shown it at `known_at` (default now): only rows available by then,
    retractions applied from their own time, revisions resolved, valid_to derived from the next fact."""
    df = load(path) if df is None else df
    if not len(df):
        return pd.DataFrame(columns=COLS)
    k = _ts(known_at) if known_at is not None else _now()
    av = df["available_at"].map(_ts)
    df = df[av <= k].copy()
    gone = set(df.loc[df["op"] == "retract", "target"])
    df = df[(df["op"] == "assert") & ~df["fact_id"].isin(gone)].copy()
    if not len(df):
        return pd.DataFrame(columns=COLS)
    df["_av"] = df["available_at"].map(_ts)
    # a revision (same subject, predicate, valid_from) replaces the earlier print once it is available
    df = (df.sort_values(["_av", "recorded_at"])
            .drop_duplicates(["subject", "predicate", "valid_from"], keep="last")
            .sort_values(["subject", "predicate", "valid_from"]))
    nxt = df.groupby(["subject", "predicate"])["valid_from"].shift(-1)
    explicit = df["valid_to"]
    vt = [min(x for x in (e, n) if isinstance(x, str) and x) if any(isinstance(x, str) and x for x in (e, n))
          else None for e, n in zip(explicit, nxt)]
    df["valid_to"] = pd.Series(vt, index=df.index, dtype="object")
    return df.drop(columns="_av").reset_index(drop=True)


def as_of(d, subject: str | None = None, predicate: str | None = None, known_at=None,
          path: Path | None = None) -> pd.DataFrame:
    """Facts true on date `d` as known at `known_at` (default: the end of `d`, i.e. point in time)."""
    d = _day(d)
    k = known(known_at if known_at is not None else d.isoformat(), path=path)
    if subject:
        k = k[k["subject"] == subject]
    if predicate:
        k = k[k["predicate"] == predicate]
    vf = k["valid_from"].map(_day)
    vt = k["valid_to"].map(_day)
    keep = (vf <= d) & vt.map(lambda x: x is None or x > d)
    return k[keep].reset_index(drop=True)


def history(subject: str, predicate: str | None = None, known_at=None, path: Path | None = None) -> pd.DataFrame:
    k = known(known_at, path=path)
    k = k[k["subject"] == subject]
    if predicate:
        k = k[k["predicate"] == predicate]
    return k.reset_index(drop=True)


def value_as_of(d, subject: str, predicate: str, known_at=None, path: Path | None = None):
    r = as_of(d, subject, predicate, known_at=known_at, path=path)
    if not len(r):
        return None
    row = r.iloc[-1]
    return row["value_num"] if row["value_num"] is not None and row["value_num"] == row["value_num"] else row["value"]


def connect(con=None, known_at=None, path: Path | None = None):
    """Register the facts table (valid_to as known at `known_at`, default now) in a DuckDB connection as `facts`."""
    from . import store
    con = con or store.connect()
    con.register("facts", known(known_at, path=path))
    return con


# ------------------------------------------------------------------ CLI
def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack facts")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("as-of", help="facts true on a date, as known then")
    a.add_argument("date")
    a.add_argument("--subject")
    a.add_argument("--predicate")
    a.add_argument("--known-at")
    h = sub.add_parser("history", help="a subject's timeline as known now (or at --known-at)")
    h.add_argument("subject")
    h.add_argument("--predicate")
    h.add_argument("--known-at")
    sub.add_parser("count", help="rows in the log by source type")
    x = p.parse_args(argv)
    cols = ["subject", "predicate", "value", "unit", "valid_from", "valid_to", "available_at", "source_type", "source_url"]
    if x.cmd == "as-of":
        df = as_of(x.date, x.subject, x.predicate, known_at=x.known_at)
    elif x.cmd == "history":
        df = history(x.subject, x.predicate, known_at=x.known_at)
    else:
        df = load()
        print(df.groupby(["op", "source_type"], dropna=False).size().to_string() if len(df) else "empty")
        return 0
    if not len(df):
        print("no facts")
        return 0
    with pd.option_context("display.max_rows", 200, "display.max_colwidth", 60, "display.width", 200):
        print(df[cols].to_string(index=False))
    return 0
