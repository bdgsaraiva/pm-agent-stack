"""Decision journal: capture every idea (taken or rejected) in under a minute, check it
against the PM's own rules, and score it later.

Why this exists: the frontier scan (Project notes A2) found that data access, briefs and
generic "thesis health checks" are being commoditised. The PM's own decision record is not:
conviction, expected payoff, invalidation, where the idea came from, and what happened.
It compounds with time, so capture starts before anything else is built on it.

One markdown file per idea: journal/<YYYY>/<id>.md, YAML front matter + free text.
Personal build: book must be "paper" or "example" (config/journal.yaml). No fund data.

Hard checks follow the Mandala and Zweig's rules:
  Zweig #3   no open idea without an invalidation level             -> block
  added      conviction 4-5 sized below your own median             -> flag
  Zweig #2   payoff (target and invalidation) not defined           -> flag
  crowding   adding to a CFTC side at/beyond the 90th percentile    -> flag
  Zweig #11  too many new ideas in a short window                   -> flag
  tilt       new idea within 24h of a large win or loss             -> flag
  Zweig #14  poor sleep or high stress at entry                     -> flag
Sizing (agent 4, pmstack/sizing.py) adds a suggested size to every idea and flags:
  no-edge, undersized-vs-suggestion (conviction 4-5), oversized, stop-in-noise, drawdown
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yaml

from . import runlog, sizing, store

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / "journal"
STATUSES = ("idea", "open", "closed", "rejected")
DIRECTIONS = ("long", "short", "relative", "vol")
SOURCE_KINDS = ("own", "alert", "note", "podcast", "call", "broker", "consensus", "news")


# ------------------------------------------------------------------ basics
def _cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "journal.yaml").read_text(encoding="utf-8"))


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:40] or "idea"


def _path(entry_id: str) -> Path:
    return JOURNAL / entry_id[:4] / f"{entry_id}.md"


def _rel(path: Path) -> str:
    return path.relative_to(JOURNAL.parent).as_posix()


def _num(x):
    try:
        return None if x is None or x == "" else float(x)
    except (TypeError, ValueError):
        return None


def read(path: Path) -> dict:
    txt = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", txt, re.S)
    if not m:
        raise ValueError(f"{path}: no YAML front matter")
    meta = yaml.safe_load(m.group(1)) or {}
    meta["_body"] = m.group(2)
    meta["_path"] = _rel(path)
    return meta


def write(entry: dict) -> Path:
    body = entry.pop("_body", "")
    entry.pop("_path", None)
    path = _path(entry["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    front = yaml.safe_dump(entry, sort_keys=False, allow_unicode=True, width=100)
    path.write_text(f"---\n{front}---\n{body}", encoding="utf-8")
    return path


def load_all() -> list[dict]:
    out = []
    for p in sorted(JOURNAL.glob("*/*.md")):
        try:
            out.append(read(p))
        except Exception as e:  # a malformed file must not hide the rest
            print(f"skip {p}: {e}", file=sys.stderr)
    return out


def get(entry_id: str) -> dict:
    p = _path(entry_id)
    if not p.exists():
        raise SystemExit(f"no journal entry {entry_id}")
    return read(p)


# ------------------------------------------------------------------ payoff and R
def payoff(e: dict) -> dict:
    """Reward-to-risk and expected R from entry, target, invalidation and probability."""
    entry, tgt, inv = _num(e.get("entry_price")), _num(e.get("target")), _num(e.get("invalidation_price"))
    out = {"reward_risk": None, "expected_r": None}
    if None in (entry, tgt, inv) or entry == inv:
        return out
    rr = abs(tgt - entry) / abs(entry - inv)
    out["reward_risk"] = round(rr, 2)
    p = _num(e.get("prob_win"))
    if p is not None and 0 < p < 1:
        out["expected_r"] = round(p * rr - (1 - p), 2)
    return out


def r_multiple(e: dict, exit_price: float) -> float | None:
    """Result in units of initial risk (entry to invalidation), signed by direction."""
    entry, inv = _num(e.get("entry_price")), _num(e.get("invalidation_price"))
    if None in (entry, inv) or entry == inv or exit_price is None:
        return None
    sign = 1 if e.get("direction") == "long" else -1 if e.get("direction") == "short" else None
    if sign is None:  # relative / vol: R must be given explicitly
        return None
    return round(sign * (exit_price - entry) / abs(entry - inv), 2)


# ------------------------------------------------------------------ memory lookups
def _last_price(price_ref: str | None):
    if not price_ref:
        return None, None, None
    try:
        con = store.connect()
        r = con.execute("SELECT value, date, source_url FROM obs WHERE series_id = ? ORDER BY date DESC LIMIT 1",
                        [price_ref]).fetchone()
        return (round(float(r[0]), 4), str(r[1]), r[2]) if r else (None, None, None)
    except Exception:
        return None, None, None


def _cftc_pct(code: str | None, lookback: int = 156):
    if not code:
        return None
    try:
        con = store.connect()
        df = con.execute("SELECT date, value FROM obs WHERE series_id = ? ORDER BY date",
                         [f"{code}.mm_net_pct_oi"]).df()
        if len(df) < 52:
            return None
        v = df["value"].tail(lookback).to_numpy()
        return {"pct": round(100 * float((v <= v[-1]).mean()), 0), "net_pct_oi": round(float(v[-1]), 1),
                "date": str(df["date"].iloc[-1])[:10]}
    except Exception:
        return None


# ------------------------------------------------------------------ checks
def checks(e: dict, others: list[dict] | None = None, now: datetime | None = None) -> list[dict]:
    cfg, now = _cfg()["checks"], now or _now()
    others = [o for o in (others if others is not None else load_all()) if o.get("id") != e.get("id")]
    out = []

    def add(level, rule, text):
        out.append({"level": level, "rule": rule, "text": text})

    if e.get("book") not in _cfg()["allowed_books"]:
        add("block", "personal-build", f"book '{e.get('book')}' is not allowed here; use paper or example (no fund data)")
    if e.get("status") == "open" and not (e.get("invalidation_price") or e.get("invalidation")):
        add("block", "zweig-3", "No invalidation. Write the level or condition that proves the idea wrong before entry.")
    if e.get("status") in ("open", "idea") and payoff(e)["reward_risk"] is None and e.get("direction") in ("long", "short"):
        add("flag", "zweig-2", "Payoff not defined: give entry, target and invalidation prices so reward-to-risk can be computed.")

    conv, size = _num(e.get("conviction")), _num(e.get("size_planned"))
    sized = [_num(o.get("size_planned")) for o in others if _num(o.get("size_planned")) is not None]
    if conv is not None and conv >= 4 and size is not None and len(sized) >= cfg["undersized_min_history"]:
        med = float(pd.Series(sized).median())
        if size < med:
            add("flag", "size-best-ideas", f"Conviction {int(conv)} but planned size {size:g} is below your median {med:g}. Your best ideas are where under-sizing costs most.")

    code = _cfg()["cftc_map"].get(e.get("price_ref") or "")
    c = _cftc_pct(code)
    if c and e.get("direction") in ("long", "short"):
        hi = cfg["crowded_pct"]
        if (e["direction"] == "long" and c["pct"] >= hi) or (e["direction"] == "short" and c["pct"] <= 100 - hi):
            add("flag", "crowded-side", f"Managed money is at the {c['pct']:.0f}th percentile of 3 years ({c['net_pct_oi']}% of OI, {c['date']}) on your side. What do you know that the crowd doesn't?")

    created = pd.Timestamp(e.get("created_utc") or now)
    created = created.tz_localize("UTC") if created.tzinfo is None else created
    win = created - pd.Timedelta(days=cfg["overtrading_window_days"])
    recent = [o for o in others if o.get("status") in ("open", "closed") and pd.Timestamp(o["created_utc"]) >= win]
    if len(recent) >= cfg["overtrading_max_new"]:
        add("flag", "zweig-11", f"{len(recent) + 1} new positions in {cfg['overtrading_window_days']} days. Don't play all the time.")

    for o in others:
        if o.get("status") == "closed" and o.get("closed_utc") and _num(o.get("r_multiple")) is not None:
            dt = created - pd.Timestamp(o["closed_utc"])
            if pd.Timedelta(0) <= dt <= pd.Timedelta(hours=cfg["tilt_hours"]) and abs(float(o["r_multiple"])) >= cfg["tilt_r"]:
                add("flag", "tilt", f"Entered {dt.total_seconds() / 3600:.0f}h after closing {o['id']} at {o['r_multiple']:+}R. Is this the same process, or a reaction?")

    ref = str(e.get("source_ref") or "")
    if ref.startswith("notes/") and not (ROOT / ref.split("#")[0]).exists():
        add("flag", "source-ref", f"Source note {ref} does not exist: digest it first (/digest) or fix the path.")
    if (e.get("source") == "call" or ref.lower().startswith("call")) and ref and not re.fullmatch(r"call:\d{4}-\d{2}-\d{2}-\d{2}", ref):
        add("flag", "source-ref", "Call sources are recorded by call id only (call:YYYY-MM-DD-NN): no contact names in the journal.")
    try:   # contact names never belong in the journal (agent 11); checked only where the private repo exists
        from . import network
        names = [c.get("name") for c in network.load_contacts() if c.get("name")]
    except (SystemExit, Exception):
        names = []
    text = json.dumps({k: v for k, v in e.items() if not str(k).startswith("_") and k != "critic"}, default=str) \
        + str(e.get("_body") or "")
    if any(re.search(rf"\b{re.escape(n)}\b", text) for n in names):
        add("flag", "contact-name", "A contact's name is in this entry: refer to the call by id (call:YYYY-MM-DD-NN).")

    sleep, stress = _num((e.get("state") or {}).get("sleep")), _num((e.get("state") or {}).get("stress"))
    if (sleep is not None and sleep <= cfg["poor_state_sleep"]) or (stress is not None and stress >= cfg["poor_state_stress"]):
        add("flag", "zweig-14", "Poor sleep or high stress at entry. Consider a smaller first clip or waiting a session.")
    if e.get("status") in ("open", "idea"):
        out.extend(sizing.flags(e))
    return out


# ------------------------------------------------------------------ actions
def new(market: str, direction: str, conviction: int, thesis: str, *, status: str = "open", book: str = "paper",
        price_ref: str | None = None, instrument: str | None = None, expression: str = "futures",
        entry_price=None, target=None, invalidation_price=None, invalidation: str | None = None,
        prob_win=None, horizon_days=None, size_planned=None, source: str = "own", source_ref: str | None = None,
        consensus: str | None = None, why_different: str | None = None, breaks: str | None = None,
        catalysts: str | None = None, sleep=None, stress=None, tags=None, now: datetime | None = None,
        force: bool = False) -> tuple[dict, list[dict]]:
    now = now or _now()
    if direction not in DIRECTIONS:
        raise ValueError(f"direction must be one of {DIRECTIONS}")
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    if not 1 <= int(conviction) <= 5:
        raise ValueError("conviction must be 1-5")
    if source not in SOURCE_KINDS:
        raise ValueError(f"source must be one of {SOURCE_KINDS}")
    px, px_date, px_url = _last_price(price_ref)
    e = {
        "id": f"{now:%Y%m%d-%H%M}-{_slug(market + ' ' + direction)}",
        "status": status, "book": book, "created_utc": now.isoformat(),
        "market": market, "instrument": instrument, "price_ref": price_ref,
        "direction": direction, "expression": expression, "horizon_days": horizon_days,
        "conviction": int(conviction), "prob_win": _num(prob_win),
        "entry_price": _num(entry_price) if entry_price is not None else px,
        "entry_price_source": None if entry_price is not None else (f"{px_url} ({px_date})" if px is not None else None),
        "target": _num(target), "invalidation_price": _num(invalidation_price), "invalidation": invalidation,
        "size_planned": _num(size_planned), "size_unit": "risk units (paper)",
        "source": source, "source_ref": source_ref,
        "consensus": consensus, "why_different": why_different, "catalysts": catalysts,
        "state": {"sleep": _num(sleep), "stress": _num(stress)},
        "tags": tags or [], "events": [],
    }
    e.update(payoff(e))
    if direction in ("long", "short"):
        e["sizing"] = sizing.suggest(e, load_all(), now)
        e["size_suggested"] = e["sizing"]["units"]
    e["_body"] = (f"\n## Thesis\n{thesis.strip()}\n\n## What breaks it\n{(breaks or '').strip()}\n\n"
                  f"## Outcome\n")
    found = checks(e, now=now)
    e["checks_at_entry"] = [f"{c['level']}:{c['rule']}" for c in found]
    blocks = [c for c in found if c["level"] == "block"]
    if blocks and not force:
        return e, found  # not written: caller shows the blocks
    try:  # critic card (agent 5): outside view + planned question slots; never blocks capture
        from . import critic
        critic.attach(e, load_all(), now)
    except Exception as exc:  # noqa: BLE001
        e["critic"] = {"error": f"{type(exc).__name__}: {exc}"[:200]}
    path = write(dict(e))
    cr = e.get("critic") or {}
    runlog.log(runlog.new_run_id(), "journal:new", "ok", id=e["id"], entry_status=status, conviction=e["conviction"],
               source=source, checks=e["checks_at_entry"], critic_tier=cr.get("tier"),
               critic_slots=[s["slot"] for s in cr.get("slots", [])], critic_error=cr.get("error"), output=_rel(path))
    return e, found


def event(entry_id: str, action: str, reason: str, size=None, price=None, now: datetime | None = None) -> dict:
    e = get(entry_id)
    if action not in ("add", "reduce", "note", "open"):
        raise ValueError("action must be add, reduce, note or open")
    now = now or _now()
    e.setdefault("events", []).append({"ts": now.isoformat(), "action": action, "size": _num(size),
                                       "price": _num(price), "reason": reason})
    if action == "open" and e["status"] == "idea":
        e["status"] = "open"
        if price is not None:
            e["entry_price"] = _num(price)
            e.update(payoff(e))
            if e.get("direction") in ("long", "short"):
                e["sizing"] = sizing.suggest(e, load_all(), now)
                e["size_suggested"] = e["sizing"]["units"]
    write(e)
    runlog.log(runlog.new_run_id(), "journal:event", "ok", id=entry_id, action=action)
    return e


EXIT_TRIGGERS = ("target", "invalidation", "event", "time", "extreme", "funding", "ad-hoc")


def infer_trigger(e: dict, exit_price) -> str | None:
    """Target or invalidation when the exit price says so; anything else must be tagged by the PM."""
    x, tgt, inv, d = _num(exit_price), _num(e.get("target")), _num(e.get("invalidation_price")), e.get("direction")
    if x is None or d not in ("long", "short"):
        return None
    sign = 1 if d == "long" else -1
    if tgt is not None and sign * (x - tgt) >= 0:
        return "target"
    if inv is not None and sign * (x - inv) <= 0:
        return "invalidation"
    return None


def close(entry_id: str, exit_price=None, r=None, process: int | None = None, lesson: str = "",
          now: datetime | None = None, trigger: str | None = None) -> dict:
    """Close an idea. `trigger` = why you exited (agent 6 exits section); inferred from price when possible."""
    e = get(entry_id)
    now = now or _now()
    trigger = trigger or infer_trigger(e, exit_price)
    if trigger is not None and trigger not in EXIT_TRIGGERS:
        raise ValueError(f"trigger must be one of {EXIT_TRIGGERS}")
    rm = _num(r) if r is not None else r_multiple(e, _num(exit_price))
    e.update({"status": "closed", "closed_utc": now.isoformat(), "exit_price": _num(exit_price),
              "exit_trigger": trigger, "lesson": (lesson or "").strip() or None,
              "r_multiple": rm, "process_score": process,
              "holding_days": round((now - pd.Timestamp(e["created_utc"]).to_pydatetime()).total_seconds() / 86400, 1)})
    e["_body"] = e.get("_body", "") + f"\n{now:%Y-%m-%d}: closed at {exit_price} ({rm if rm is not None else 'n/a'}R), process {process}/5. {lesson}\n"
    write(e)
    runlog.log(runlog.new_run_id(), "journal:close", "ok", id=entry_id, r=rm, process=process, exit_trigger=trigger)
    return e


def reject(entry_id: str, reason: str, now: datetime | None = None) -> dict:
    e = get(entry_id)
    now = now or _now()
    e.update({"status": "rejected", "rejected_utc": now.isoformat(), "reject_reason": reason})
    write(e)
    runlog.log(runlog.new_run_id(), "journal:reject", "ok", id=entry_id)
    return e


# ------------------------------------------------------------------ review and stats
def frame(entries: list[dict] | None = None) -> pd.DataFrame:
    rows = []
    for e in entries if entries is not None else load_all():
        rows.append({k: e.get(k) for k in ("id", "status", "book", "market", "price_ref", "direction", "conviction",
                                            "size_planned", "size_suggested", "source", "reward_risk", "expected_r", "r_multiple",
                                            "process_score", "holding_days", "created_utc", "closed_utc",
                                            "entry_price", "invalidation_price", "target", "horizon_days")})
    return pd.DataFrame(rows)


def what_happened(e: dict, now: datetime | None = None) -> float | None:
    """For rejected ideas (the graveyard): R the idea would have made by its horizon (or today)."""
    if not e.get("price_ref") or e.get("direction") not in ("long", "short"):
        return None
    start = pd.Timestamp(e.get("rejected_utc") or e["created_utc"])
    end = start + pd.Timedelta(days=int(e.get("horizon_days") or 20))
    end = min(end, pd.Timestamp(now or _now()))
    try:
        con = store.connect()
        r = con.execute("SELECT value FROM obs WHERE series_id = ? AND date <= ? ORDER BY date DESC LIMIT 1",
                        [e["price_ref"], end.date()]).fetchone()
    except Exception:
        return None
    return r_multiple(e, float(r[0])) if r else None


def stats(entries: list[dict] | None = None) -> dict:
    entries = entries if entries is not None else load_all()
    df = frame(entries)
    if df.empty:
        return {"entries": 0}
    out = {"entries": int(len(df)), "by_status": df["status"].value_counts().to_dict()}
    closed = df[(df.status == "closed") & df.r_multiple.notna()].copy()
    if len(closed):
        closed["r_multiple"] = closed.r_multiple.astype(float)
        out["closed"] = {"n": int(len(closed)), "hit_rate": round(float((closed.r_multiple > 0).mean()), 2),
                         "avg_r": round(float(closed.r_multiple.mean()), 2)}
        g = closed.groupby("conviction")
        out["by_conviction"] = {int(k): {"n": int(len(v)), "avg_r": round(float(v.r_multiple.mean()), 2),
                                         "avg_size": None if v.size_planned.isna().all() else round(float(v.size_planned.astype(float).mean()), 2)}
                                for k, v in g}
        wins, losses = closed[closed.r_multiple > 0], closed[closed.r_multiple <= 0]
        if len(wins) and len(losses) and closed.holding_days.notna().any():
            out["zweig_2_holding_days"] = {"winners": round(float(wins.holding_days.astype(float).mean()), 1),
                                           "losers": round(float(losses.holding_days.astype(float).mean()), 1)}
        out["by_source"] = {k: {"n": int(len(v)), "hit_rate": round(float((v.r_multiple > 0).mean()), 2),
                                "avg_r": round(float(v.r_multiple.mean()), 2)} for k, v in closed.groupby("source")}
    sized = df[df.size_planned.notna() & df.conviction.notna()]
    if len(sized) >= 3:
        out["size_vs_conviction_corr"] = round(float(sized.size_planned.astype(float).corr(sized.conviction.astype(float))), 2)
    rej = [e for e in entries if e.get("status") == "rejected"]
    if rej:
        hyp = [r for r in (what_happened(e) for e in rej) if r is not None]
        out["graveyard"] = {"n": len(rej), "scored": len(hyp),
                            "avg_r_if_taken": round(sum(hyp) / len(hyp), 2) if hyp else None}
    return out


def open_book(now: datetime | None = None) -> list[dict]:
    """Open and idea entries with distance to invalidation and target from the latest stored price."""
    rows = []
    for e in load_all():
        if e.get("status") not in ("open", "idea"):
            continue
        px, d, url = _last_price(e.get("price_ref"))
        inv, tgt = _num(e.get("invalidation_price")), _num(e.get("target"))
        row = {"id": e["id"], "status": e["status"], "market": e.get("market"), "direction": e.get("direction"),
               "conviction": e.get("conviction"), "price_ref": e.get("price_ref"), "last": px, "last_date": d,
               "source_url": url, "invalidation_price": inv, "target": tgt,
               "to_invalidation_pct": round(100 * (inv / px - 1), 2) if px and inv else None,
               "to_target_pct": round(100 * (tgt / px - 1), 2) if px and tgt else None,
               "r_now": r_multiple(e, px) if px else None,
               "days_open": round(((now or _now()) - pd.Timestamp(e["created_utc"]).to_pydatetime()).total_seconds() / 86400, 1),
               "horizon_days": e.get("horizon_days")}
        if px and inv and e.get("direction") in ("long", "short"):
            row["invalidated"] = (px <= inv) if e["direction"] == "long" else (px >= inv)
        rows.append(row)
    return rows


# ------------------------------------------------------------------ CLI
def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack journal", description="Decision journal (paper/example ideas only on the personal build)")
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new", help="record a new idea (status open by default)")
    n.add_argument("--market", required=True); n.add_argument("--direction", required=True, choices=DIRECTIONS)
    n.add_argument("--conviction", required=True, type=int); n.add_argument("--thesis", required=True)
    n.add_argument("--status", default="open", choices=STATUSES); n.add_argument("--book", default="paper")
    n.add_argument("--price-ref"); n.add_argument("--instrument"); n.add_argument("--expression", default="futures")
    n.add_argument("--entry-price", type=float); n.add_argument("--target", type=float)
    n.add_argument("--invalidation-price", type=float); n.add_argument("--invalidation")
    n.add_argument("--prob-win", type=float); n.add_argument("--horizon-days", type=int)
    n.add_argument("--size-planned", type=float); n.add_argument("--source", default="own", choices=SOURCE_KINDS)
    n.add_argument("--source-ref"); n.add_argument("--consensus"); n.add_argument("--why-different")
    n.add_argument("--breaks"); n.add_argument("--catalysts"); n.add_argument("--sleep", type=float)
    n.add_argument("--stress", type=float); n.add_argument("--tags", nargs="*")
    n.add_argument("--force", action="store_true", help="write even if a hard check blocks (recorded in the entry)")
    ev = sub.add_parser("event"); ev.add_argument("id"); ev.add_argument("--action", required=True)
    ev.add_argument("--reason", required=True); ev.add_argument("--size", type=float); ev.add_argument("--price", type=float)
    c = sub.add_parser("close"); c.add_argument("id"); c.add_argument("--exit-price", type=float); c.add_argument("--r", type=float)
    c.add_argument("--process", type=int, required=True); c.add_argument("--lesson", default="")
    c.add_argument("--trigger", choices=EXIT_TRIGGERS,
                   help="why you exited; required unless the exit price is at/through the target or invalidation")
    r = sub.add_parser("reject"); r.add_argument("id"); r.add_argument("--reason", required=True)
    ls = sub.add_parser("list"); ls.add_argument("--status")
    sub.add_parser("stats"); sub.add_parser("book")
    ck = sub.add_parser("check"); ck.add_argument("id")
    sz = sub.add_parser("size", help="suggested size for an idea, recomputed on today's record")
    sz.add_argument("id"); sz.add_argument("--write", action="store_true", help="store the new suggestion on the entry")
    sub.add_parser("sizing-review", help="suggested vs planned, R left on the table, calibration, exits")
    a = p.parse_args(argv)

    if a.cmd == "new":
        kw = {k: v for k, v in vars(a).items() if k not in ("cmd", "market", "direction", "conviction", "thesis")}
        e, found = new(a.market, a.direction, a.conviction, a.thesis, **kw)
        blocked = [f for f in found if f["level"] == "block"]
        print(json.dumps({"id": e["id"], "written": not blocked or a.force, "reward_risk": e.get("reward_risk"),
                          "expected_r": e.get("expected_r"), "sizing": e.get("sizing"), "checks": found},
                         indent=1, ensure_ascii=False))
        return 1 if blocked and not a.force else 0
    if a.cmd == "event":
        print(json.dumps(event(a.id, a.action, a.reason, a.size, a.price)["events"][-1], ensure_ascii=False)); return 0
    if a.cmd == "close":
        if not a.trigger and not infer_trigger(get(a.id), a.exit_price):
            print(f"--trigger is required: one of {', '.join(EXIT_TRIGGERS)}", file=sys.stderr)
            return 2
        e = close(a.id, a.exit_price, a.r, a.process, a.lesson, trigger=a.trigger)
        print(json.dumps({k: e.get(k) for k in ("id", "r_multiple", "holding_days", "process_score", "exit_trigger")})); return 0
    if a.cmd == "reject":
        reject(a.id, a.reason); print(f"rejected {a.id}"); return 0
    if a.cmd == "list":
        df = frame()
        if a.status and not df.empty:
            df = df[df.status == a.status]
        print(df.to_string(index=False) if not df.empty else "journal is empty"); return 0
    if a.cmd == "stats":
        print(json.dumps(stats(), indent=1, ensure_ascii=False)); return 0
    if a.cmd == "book":
        print(json.dumps(open_book(), indent=1, ensure_ascii=False, default=str)); return 0
    if a.cmd == "check":
        print(json.dumps(checks(get(a.id)), indent=1, ensure_ascii=False)); return 0
    if a.cmd == "size":
        e = get(a.id)
        s = sizing.suggest(e, load_all())
        if a.write:
            e["sizing"], e["size_suggested"] = s, s["units"]
            write(e)
        runlog.log(runlog.new_run_id(), "journal:size", "ok", id=a.id, units=s["units"], written=a.write)
        print(json.dumps({"id": a.id, "size_planned": e.get("size_planned"), **s}, indent=1, ensure_ascii=False)); return 0
    if a.cmd == "sizing-review":
        out = sizing.review(load_all())
        runlog.log(runlog.new_run_id(), "journal:sizing-review", "ok", ideas=out.get("ideas"))
        print(json.dumps(out, indent=1, ensure_ascii=False, default=str)); return 0
    return 2
