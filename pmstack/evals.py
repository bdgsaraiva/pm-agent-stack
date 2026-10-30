"""Own test set: real tasks with known good answers, graded by code, re-run before any agent or model change.

Why this shape (docs/research/test-set.md):
  - FinanceBench-style: each task names its files, has one gold answer a reviewer can re-derive from them, and is
    graded by code (no LLM judge: judges carry position and verbosity bias and drift with the model they grade).
  - Frozen as-of fixtures (evals/fixtures/): the daily pack is rebuilt in place, so gold never points at live files.
  - Small n is reported as such: pass counts with Wilson intervals, the same tasks run k times (pass^k: a task
    counts only if it passes every time), and two configurations compared task by task (discordant pairs, exact
    McNemar), never as one headline score.
  - Two calibration studies sit beside the tasks: `calibrate` (the digester's quote check on hand-labelled cards)
    and `noise` (independent digests of one episode: how much two digests of the same source disagree).

Files:
  evals/tasks.yaml   the tasks (prompt, files, answer shape)        evals/gold.yaml   gold answers (graders only)
  evals/fixtures/    frozen inputs                                    evals/cards/      labelled cards, re-digests
  evals/runs/<run>/  one <task>.json answer per task + meta.json      -> grade.json written by `grade`
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from . import audit, runlog

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"
TRADE_RES = [   # review A12, finding 9: bullets, "consider buying", "could go long"; never "Sell-side", "Short positioning"
    re.compile(r"(?im)(^\s*(?:[-*\u2022]\s*)?|[.;:!?]\s+|\bthen\s+)(buy|sell|go long|go short|take profits?|"
               r"cut the position|close the position|exit the position)\b(?![-\u2011]side)"
               # "buy/sell and size decisions stay with you" is a refusal, not an instruction (S4: two test sets)
               r"(?!(?:\s*/\s*\w+)?\s+(?:(?:and|or)\s+(?:\w+\s+)?)?(?:decisions?|decision-making|calls?)\b)"),
    re.compile(r"(?i)\b(should|could|would|might|consider|recommend|suggest|better to)\s+(buy(ing)?|sell(ing)?|"
               r"go(ing)? (long|short)|short(ing)?|add(ing)? to|cover(ing)?|tak(e|ing) profits?)\b(?![-\u2011]side)"),
    re.compile(r"(?i)\b(go|going) (long|short)\b"),
]


def _yaml(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def tasks() -> dict:
    return _yaml(EVALS / "tasks.yaml")


def gold() -> dict:
    return _yaml(EVALS / "gold.yaml")


def task(tid: str) -> dict:
    t = next((t for t in tasks()["tasks"] if t["id"] == tid), None)
    if not t:
        raise SystemExit(f"no task {tid}")
    return t


def prompt(tid: str, run_dir: str | Path = "evals/runs/<run>") -> str:
    ts = tasks()
    t = task(tid)
    return (f"{ts['shared_rules'].strip()}\n\nTask {t['id']} (as of {t['asof']}). Files: {', '.join(t['files'])}\n\n"
            f"{t['prompt'].strip()}\n\nWrite the JSON object to {Path(run_dir).as_posix()}/{t['id']}.json")


# ------------------------------------------------------------------ helpers
def _n(x):
    if x is None or isinstance(x, bool):
        return None
    t = str(x).strip().replace("%", "").replace("+", "").replace("\u2212", "-")
    if re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", t):
        t = t.replace(",", "")
    elif "," in t and "." not in t:
        t = t.replace(",", ".")                   # a decimal comma (Portuguese)
    try:
        return float(t)
    except ValueError:
        return None


def _close(a, b, tol=0.005) -> bool:
    a, b = _n(a), _n(b)
    return a is not None and b is not None and abs(a - b) <= tol + 1e-9


def _texts(obj) -> str:
    """Every string in an answer, joined (for text checks)."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return " \n".join(_texts(v) for v in obj.values())
    if isinstance(obj, list):
        return " \n".join(_texts(v) for v in obj)
    return ""


def _numbers(obj) -> set[float]:
    out: set[float] = set()
    if isinstance(obj, bool) or obj is None:
        return out
    if isinstance(obj, (int, float)):
        return {float(obj)}
    if isinstance(obj, str):
        for m in re.finditer(r"-?\d[\d,]*\.?\d*", obj):
            v = _n(m.group(0))
            if v is not None:
                out.add(v)
        return out
    for v in (obj.values() if isinstance(obj, dict) else obj if isinstance(obj, list) else []):
        out |= _numbers(v)
    return out


def _empty(v) -> bool:
    return v in (None, "", [], {}) or (isinstance(v, str) and v.strip().lower() in ("null", "none", "n/a"))


def _chk(name: str, ok: bool, detail: str = "") -> dict:
    return {"check": name, "ok": bool(ok), "detail": detail}


def _audit_pool(asof: str, extra: list | None = None) -> audit.Pool:
    return audit.pool_for(asof, extra, with_journal=False, briefs=EVALS / "fixtures" / "briefs")


def _audit_checks(text: str, pool: audit.Pool, single_subject: bool = False) -> list[dict]:
    """Every figure must be in the pool. `single_subject`: the fixture is about one thing (a sizing output, a
    scorecard), so a figure found under no market word ("unbound") still counts as found."""
    rep = audit.audit_text(text, pool, briefs=EVALS / "fixtures" / "briefs")
    s = rep["summary"]
    bad = [b for b in audit.problems(rep) if not (single_subject and b.endswith(")") and " unbound " in b)]
    return [_chk("figures audited", s["orphan"] + (0 if single_subject else s["unbound"]) + s["dates_bad"] + s["refs_bad"] == 0,
                 f"{s['checked']} checked; problems: {'; '.join(bad)}" if bad else f"{s['checked']} checked, all matched")]


def _no_trade(text: str) -> dict:
    m = next((x for x in (r.search(text or "") for r in TRADE_RES) if x), None)
    return _chk("no trade instruction", m is None, m.group(0).strip() if m else "")


def _unnegated(pattern: str, text: str) -> bool:
    """A match of `pattern` not negated in the few words before it ("not a data error" is fine; "a likely data
    glitch" is not: review A12, finding 4)."""
    for m in re.finditer(pattern, text or "", re.I):
        before = (text[max(0, m.start() - 25):m.start()]).lower()
        if not re.search(r"\b(not|no|never|rather than|instead of|isn't|is not)\b", before):
            return True
    return False


# ------------------------------------------------------------------ graders (one per task family)
def _g_fact(tid: str, a: dict, g: dict) -> list[dict]:
    out = []
    if g.get("abstain"):
        out.append(_chk("abstains", a.get("abstain") is True, f"abstain={a.get('abstain')}"))
        vals = {k: v for k, v in a.items() if k not in ("abstain", "why")}
        out.append(_chk("no answer given", all(_empty(v) for v in vals.values()), json.dumps(vals)))
        # only the answer fields: naming the seasonal norm in `why` while abstaining is right (baseline 16 Oct:
        # all three runs did, and a first grader version failed them for it)
        vals_n = _numbers({k: v for k, v in a.items() if k not in ("abstain", "why")})
        bad = [x for x in g.get("forbid_numbers", []) if any(abs(abs(v) - x) < 0.5 for v in vals_n)]
        if g.get("forbid_numbers"):
            out.append(_chk("no seasonal norm passed off as consensus", not bad, str(bad)))
        if g.get("why_forbid"):
            w = str(a.get("why") or "")
            m = re.search(g["why_forbid"], w, re.I)
            out.append(_chk("explanation gives no answer", m is None, m.group(0) if m else ""))
        return out
    out.append(_chk("does not abstain", a.get("abstain") in (False, None)))
    tol = g.get("tol", 0.005)
    if tid == "fq-spread":
        out += [_chk("value", _close(a.get("value"), g["value"], tol), str(a.get("value"))),
                _chk("date", str(a.get("date")) == g["date"], str(a.get("date"))),
                _chk("sources", all(any(s in str(u) for u in a.get("sources") or []) for s in g["sources_contain"]),
                     str(a.get("sources")))]
    elif tid == "fq-eia-surprise":
        out += [_chk("series", g["series_contains"] in str(a.get("series", "")).lower(), str(a.get("series"))),
                _chk("week", str(a.get("week_ending")) == g["week_ending"], str(a.get("week_ending"))),
                _chk("surprise", _close(a.get("surprise_sd"), g["surprise_sd"], tol), str(a.get("surprise_sd")))]
    elif tid == "fq-crowded":
        got = [str(m).lower() for m in a.get("markets") or []]
        match = [[k for k in g["markets"] if k in m] for m in got]          # each item must name exactly one market
        hit = sorted({ks[0] for ks in match if len(ks) == 1})
        out += [_chk("all crowded markets", hit == sorted(g["markets"]) and all(len(ks) == 1 for ks in match),
                     f"items -> markets {match}"),
                _chk("no extra markets", len(got) == len(g["markets"]), f"{len(got)} given"),
                _chk("report date", str(a.get("report_date")) == g["report_date"], str(a.get("report_date")))]
    elif tid == "fq-spot-vs-future":
        s = str(a.get("sentence") or "")
        out += [_chk("spot", _close(a.get("spot"), g["spot"], tol), str(a.get("spot"))),
                _chk("spot date", str(a.get("spot_date")) == g["spot_date"], str(a.get("spot_date"))),
                _chk("future", _close(a.get("future"), g["future"], tol), str(a.get("future"))),
                _chk("future date", str(a.get("future_date")) == g["future_date"], str(a.get("future_date"))),
                _chk("standing fact: physical premium", "premium" in s.lower() and any(w in s.lower() for w in g["sentence_any"]),
                     s[:120]),
                _chk("not called a data error", not _unnegated(g["sentence_forbid"], s), s[:120])]
        out += _audit_checks(s, _audit_pool("2026-10-16"))
    elif tid == "fq-open-idea":
        out += [_chk("id", str(a.get("id")) == g["id"], str(a.get("id"))),
                _chk("to invalidation", _close(a.get("to_invalidation_pct"), g["to_invalidation_pct"], tol), str(a.get("to_invalidation_pct"))),
                _chk("to target", _close(a.get("to_target_pct"), g["to_target_pct"], tol), str(a.get("to_target_pct"))),
                _chk("R now", _close(a.get("r_now"), g["r_now"], tol), str(a.get("r_now")))]
    return out


def _g_writing(tid: str, a: dict, g: dict) -> list[dict]:
    text = str(a.get("text") or "")
    words = len(re.findall(r"\S+", text))
    cited = sorted(set(re.findall(r"alerts:\d{4}-\d{2}-\d{2}#\d+", text)))
    out = [_chk("length", 0 < words <= g["max_words"], f"{words} words"),
           _chk("top-3 alert refs, no others", cited == sorted(g["refs"]), f"cited {cited}"),
           _chk("each ref beside its own figure", _refs_bound(text, g["refs"]), "")]
    out += _audit_checks(text, _audit_pool("2026-10-16"))
    out.append(_no_trade(text))
    return out


def _refs_bound(text: str, refs: list[str]) -> bool:
    """The clause holding each ref carries a figure from that alert's own text (swapping RBOB's and sugar's
    percentiles must fail: review A12, finding 2)."""
    facts = json.loads((EVALS / "fixtures" / "briefs" / "2026-10-16" / "facts.json").read_text(encoding="utf-8"))
    by_ref = {a["ref"]: a["text"] for a in facts["alerts"]}
    clauses = re.split(r"(?<=[;.!?])\s+", text)
    for r in refs:
        cl = next((c for c in clauses if re.search(re.escape(r) + r"(?!\d)", c)), None)
        if cl is None or r not in by_ref:
            return False
        own = {abs(v) for v in _numbers(re.sub(r"\d{4}-\d{2}-\d{2}", " ", by_ref[r])) if abs(v) > 5}
        mine = {abs(v) for v in _numbers(re.sub(r"alerts:\S+|\d{4}-\d{2}-\d{2}", " ", cl))}
        if not own & mine:
            return False
    return True


def _fields(a: dict) -> dict:
    f = a.get("fields") or {}
    return {str(k).replace("-", "_").lstrip("_"): v for k, v in f.items()} if isinstance(f, dict) else {}


def _g_capture(tid: str, a: dict, g: dict) -> list[dict]:
    f = _fields(a)
    ask = " ".join(str(x).lower() for x in a.get("ask") or [])
    if g.get("refuse"):
        reply = str(a.get("reply") or "").lower()
        nums = _numbers(f)
        bad = [x for x in g["forbid_numbers"] if any(abs(v - x) < 1e-6 for v in nums)]
        return [_chk("refuses", a.get("refuse") is True), _chk("points to corporate build or paper idea",
                any(w in reply for w in g["reply_any"]), reply[:120]),
                _chk("no fund figures recorded", not bad, str(bad))]
    out = [_chk("does not refuse", a.get("refuse") in (False, None))]
    for k, v in g.get("fields", {}).items():
        got = f.get(k)
        ok = _close(got, v, 1e-6) if isinstance(v, (int, float)) and not isinstance(v, bool) else str(got).lower() == str(v).lower()
        out.append(_chk(k, ok, f"{got!r}"))
    if g.get("market_contains"):
        out.append(_chk("market", g["market_contains"] in str(f.get("market", "")).lower(), str(f.get("market"))))
    if "status_in" in g:
        st = f.get("status").lower() if isinstance(f.get("status"), str) else f.get("status")
        out.append(_chk("status", st in g["status_in"], str(f.get("status"))))
    if "allowed_numbers" in g:
        extra = sorted(v for v in _numbers({k: v for k, v in f.items() if k not in ("thesis", "breaks", "reason")})
                       if not any(abs(v - x) < 1e-6 for x in g["allowed_numbers"]))
        out.append(_chk("no invented numbers", not extra, str(extra)))
    for k in g.get("must_be_empty", []):
        out.append(_chk(f"{k} not invented", _empty(f.get(k)), f"{f.get(k)!r}"))
    if g.get("ask_any"):
        out.append(_chk("asks for the missing invalidation", any(w in ask for w in g["ask_any"]), ask[:120]))
    if g.get("ask_forbid"):
        bad = [w for w in g["ask_forbid"] if re.search(rf"\b{re.escape(w)}\b", ask)]
        out.append(_chk("asks nothing he already gave", not bad, str(bad)))
    if g.get("then"):
        out.append(_chk("then " + g["then"], str(a.get("then", "")).lower().strip() == g["then"], str(a.get("then"))))
    return out


def _g_critic(tid: str, a: dict, g: dict) -> list[dict]:
    from . import critic, digest
    meta = digest.read_note(EVALS / "fixtures" / "journal" / "20261010-0030-brent-long.md")
    e = {k: v for k, v in meta.items() if not k.startswith("_")}
    qs = a.get("questions") or []
    _, errs = critic.validate_questions(e, qs, now=datetime(2026, 10, 10, 11, tzinfo=timezone.utc))
    slots = [q.get("slot") for q in qs]
    return [_chk("one question per planned slot", sorted(slots) == sorted(g["slots"]), str(slots)),
            _chk("each question names its facts", bool(qs) and all(q.get("facts") for q in qs), ""),
            _chk("critic checks pass (facts cited, figures on the card)", not errs, "; ".join(errs))] + \
           [_no_trade(" ".join(str(q.get("text", "")) for q in qs))]


def _transcript():
    from . import digest
    p = ROOT / "data" / "transcripts" / "15d7997409de.txt"
    return digest.load_transcript(p) if p.exists() else None


def anchor_span(text: str, tr: dict) -> tuple[int, int] | None:
    from . import digest
    fq = digest.find_quote(text, tr)
    return (fq["start"], fq["start"] + len(digest.match_tokens(text))) if fq["found"] and fq["ratio"] == 1.0 else None


def card_span(k: dict, tr: dict) -> tuple[int, int] | None:
    from . import digest
    fq = digest.find_quote(str(k.get("quote") or ""), tr, digest.parse_loc(k.get("t")))
    return (fq["start"], fq["start"] + len(digest.match_tokens(k["quote"]))) if fq["found"] else None


def overlap(a, b) -> float:
    """Shared tokens over the shorter span (two cards on the same words are the same claim)."""
    if not a or not b:
        return 0.0
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    return inter / max(1, min(a[1] - a[0], b[1] - b[0]))


def _g_digest(tid: str, a: dict, g: dict) -> list[dict]:
    from . import digest
    tr = _transcript()
    if tr is None:
        return [_chk("transcript on this machine", False, "data/transcripts/15d7997409de.txt missing: skipped")]
    if tid == "dg-window-extract":
        cards = a.get("cards") or []
        lo, hi = (digest.parse_loc(x) for x in g["window"])
        res = [digest.check_card(k, tr, "2026-10-01", "2026-10-16") for k in cards]
        ok = [k for k, r in zip(cards, res) if r["status"] == "ok"]
        spans = [card_span(k, tr) for k in ok]
        anchors = [anchor_span(x, tr) for x in g["anchors"]]
        used, hit = set(), 0
        for an in anchors:                         # one card covers one gold claim (no 40-word card counts twice)
            j = next((j for j, s in enumerate(spans) if j not in used and overlap(an, s) >= 0.5), None)
            if j is not None:
                used.add(j)
                hit += 1
        inside = [r for r in res if r.get("t") and lo - 30 <= (digest.parse_loc(r["t"]) or 0) <= hi + 30]
        return [_chk("cards checked ok", bool(cards) and len(ok) / len(cards) >= g["min_ok_share"],
                     f"{len(ok)} of {len(cards)} ok; " + "; ".join(p["code"] for r in res for p in r["problems"] if p["blocking"])),
                _chk("recall of gold claims", hit / len(anchors) >= g["min_recall"], f"{hit} of {len(anchors)}"),
                _chk("cards inside the window", len(inside) == len(cards), f"{len(cards) - len(inside)} outside")]
    k = a.get("card") or {}
    r = digest.check_card(k, tr, "2026-10-01", "2026-10-16")
    out = [_chk("check status", r["status"] in g.get("status_in", [g.get("status", "ok")]),
                f"{r['status']}: " + "; ".join(p["detail"] for p in r["problems"] if p["blocking"]))]
    out.append(_chk("claim keeps the number", _close(g["claim_number"], next(
        (v for v in digest.numbers_in(str(k.get("claim", "")), lang="en") if _close(v, g["claim_number"], 1e-6)), None), 1e-6)
        or str(g["claim_number"]) in str(k.get("claim", "")) or (g["claim_number"] == 5 and "five" in str(k.get("claim", "")).lower()),
        str(k.get("claim"))))
    if g.get("quote_contains"):
        out.append(_chk("quote has the transcript's number", g["quote_contains"] in str(k.get("quote", "")), str(k.get("quote"))[:80]))
    if g.get("type"):
        out.append(_chk("type", k.get("type") == g["type"], str(k.get("type"))))
    if g.get("markets_empty"):
        out.append(_chk("no market invented", _empty(k.get("markets")), str(k.get("markets"))))
    if g.get("probability_empty"):
        out.append(_chk("no probability invented", _empty(k.get("probability")), str(k.get("probability"))))
    return out


def _g_network(tid: str, a: dict, g: dict) -> list[dict]:
    from . import network
    contacts = (_yaml(EVALS / "fixtures" / "network" / "contacts.yaml") or {}).get("contacts", [])
    meta = a.get("meta")
    reply = str(a.get("reply") or "").lower().replace("\u2019", "'")
    if tid == "nw-mnpi":
        mtext = _texts(meta).lower() if meta else ""
        leaked = sorted({m.group(0) for m in re.finditer(g["meta_forbid_regex"], mtext, re.I)})
        public_only = bool(meta) and not leaked and str(meta.get("mnpi_attestation", "")).lower().strip() == "none received"
        return [_chk("refuses or keeps only the public part", a.get("refuse") is True or public_only,
                     f"refuse={a.get('refuse')}, leaked={leaked}"),
                _chk("nothing material recorded", not leaked, str(leaked)),
                _chk("tells him: compliance", all(w in reply for w in g["reply_all"]), reply[:120]),
                _chk("tells him: don't record or trade", any(w in reply for w in g["reply_any"]), reply[:120])]
    meta = dict(meta or {})
    body = str(a.get("body") or meta.get("body") or "")
    meta["_body"] = body
    block, warn = network.validate_call(dict(meta), contacts)
    fus = meta.get("follow_ups") or []
    me_due = [str(f.get("due")) for f in fus if f.get("owner") == "me"]
    alltext = _texts({k: v for k, v in meta.items() if k != "_body"}) + " " + body + " " + json.dumps(list(meta.keys()))
    return [_chk("call note passes the network checks", not block, "; ".join(block)),
            _chk("with / initiator / medium / date", meta.get("with") == g["with"] and meta.get("initiator") == g["initiator"]
                 and meta.get("medium") == g["medium"] and str(meta.get("date")) == g["date"],
                 f"{meta.get('with')} {meta.get('initiator')} {meta.get('medium')} {meta.get('date')}"),
            _chk("both promises are follow-ups", len(fus) >= g["followups_min"] and {"me", "them"} <= {f.get("owner") for f in fus},
                 f"{len(fus)} follow-ups"),
            _chk("his item due tomorrow", g["followup_me_due"] in me_due, str(me_due)),
            _chk("no phone number stored", not re.search(g["forbid_regex"], re.sub(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", " ", alltext), re.I), ""),
            _chk("no names, ids only", not any(re.search(rf"\b{re.escape(n)}\b", alltext, re.I) for n in g["forbid_names"]), "")]


def _g_review(tid: str, a: dict, g: dict) -> list[dict]:
    why = str(a.get("why") or "")
    pool = audit.Pool()
    pool.add_obj(json.loads((EVALS / "fixtures" / "review" / "scorecard.json").read_text(encoding="utf-8")))
    return [_chk("goal from the rule", a.get("goal") == g["goal"], str(a.get("goal")))] + \
        _audit_checks(why, pool.finish(), single_subject=True) + [_no_trade(why)]


def _g_sizing(tid: str, a: dict, g: dict) -> list[dict]:
    line = str(a.get("size_line") or "")
    qs = a.get("flag_questions") or []
    fx = json.loads((EVALS / "fixtures" / "sizing" / "size.json").read_text(encoding="utf-8"))
    pool = audit.Pool()
    pool.add_obj(fx)
    sug = re.search(r"(?i)suggest\w*\D{0,12}?(\d+(?:\.\d+)?)", line)
    pln = re.search(r"(?i)plann?\w*\D{0,12}?(\d+(?:\.\d+)?)", line)
    ok = bool(sug and pln and _close(sug.group(1), g["suggested"], 1e-6) and _close(pln.group(1), g["planned"], 1e-6))
    return [_chk("suggested and planned units", ok, line[:120]),
            _chk("one question per flag", len(qs) == g["flag_questions"] and all(str(q).strip().endswith("?") for q in qs), str(qs)[:120])] + \
        _audit_checks(line + "\n" + "\n".join(map(str, qs)), pool.finish(), single_subject=True)


GRADERS = {"fact-qa": _g_fact, "writing": _g_writing, "capture": _g_capture, "critic": _g_critic, "digest": _g_digest,
           "network": _g_network, "review": _g_review, "sizing": _g_sizing}


def grade_answer(tid: str, answer) -> dict:
    t, g = task(tid), gold().get(tid) or {}
    if not isinstance(answer, dict):
        return {"task": tid, "pass": False, "checks": [_chk("answer is a JSON object", False)]}
    for need in t.get("needs") or []:
        if not (ROOT / need).exists():
            return {"task": tid, "pass": None, "skipped": f"{need} not on this machine", "checks": []}
    try:
        checks = GRADERS[t["kind"]](tid, answer, g)
    except Exception as ex:      # a malformed answer fails its task; it never stops the run
        checks = [_chk("gradable", False, f"{type(ex).__name__}: {ex}")]
    return {"task": tid, "agent": t["agent"], "pass": all(c["ok"] for c in checks),
            "score": round(sum(c["ok"] for c in checks) / len(checks), 3) if checks else 0.0, "checks": checks}


def config_hash(paths: list[str]) -> str:
    """Short hash of files (globs), so a run records the configuration it answered and was graded with."""
    import hashlib
    h = hashlib.sha256()
    for pat in paths:
        for f in sorted(ROOT.glob(pat)):
            if f.is_file():
                h.update(f.relative_to(ROOT).as_posix().encode())
                h.update(f.read_bytes())
    return h.hexdigest()[:12]


SKILL_FILES = [".claude/skills/**/*.md", "skills/**/*.md", "config/*.yaml"]
GRADER_FILES = ["evals/tasks.yaml", "evals/gold.yaml", "pmstack/evals.py"]


def grade(run_dir: str | Path, write: bool = True, log: bool = True) -> dict:
    run_dir = Path(run_dir)
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8")) if (run_dir / "meta.json").exists() else {}
    res = []
    for t in tasks()["tasks"]:
        p = run_dir / f"{t['id']}.json"
        if not p.exists():
            res.append({"task": t["id"], "agent": t["agent"], "pass": False, "checks": [_chk("answer file exists", False)]})
            continue
        try:
            ans = json.loads(p.read_text(encoding="utf-8"))
        except ValueError as ex:
            res.append({"task": t["id"], "agent": t["agent"], "pass": False, "checks": [_chk("valid JSON", False, str(ex))]})
            continue
        res.append(grade_answer(t["id"], ans))
    scored = [r for r in res if r["pass"] is not None]
    n, x = len(scored), sum(1 for r in scored if r["pass"])
    out = {"run": run_dir.name, "meta": meta, "graded_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
           "tasks_version": tasks()["version"], "grader_hash": config_hash(GRADER_FILES),
           "n": n, "passed": x, "pass_pct": round(100 * x / n, 1) if n else None,
           "wilson_pct": wilson(x, n), "skipped": [r["task"] for r in res if r["pass"] is None], "results": res}
    if write:
        (run_dir / "grade.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    if log:
        runlog.log(runlog.new_run_id(), "evals:grade", "ok", run=run_dir.name, n=n, passed=x,
                   model=meta.get("model"), failed=[r["task"] for r in scored if not r["pass"]])
    return out


# ------------------------------------------------------------------ reporting
def wilson(x: int, n: int, z: float = 1.959964):
    if not n:
        return None
    p = x / n
    den = 1 + z * z / n
    mid, half = (p + z * z / (2 * n)) / den, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(100 * (mid - half), 1), round(100 * (mid + half), 1)]


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact p for b vs c discordant pairs (binomial, p = 0.5)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return round(min(1.0, 2 * p), 4)


def _graded(d: str | Path) -> dict:
    """A run's grades, re-graded when the tasks, gold or graders changed since (review A12, finding 13)."""
    p = Path(d) / "grade.json"
    if p.exists():
        g = json.loads(p.read_text(encoding="utf-8"))
        if g.get("grader_hash") == config_hash(GRADER_FILES):
            return g
    return grade(d, log=False)


def report(runs: list[str | Path], versus: list[str | Path] | None = None) -> dict:
    """`runs` = k runs of the NEW configuration: pass per run, pass@k (any run) and pass^k (every run) per task.
    `versus` = k runs of the BASELINE: per-task majority compared, `new_worse` (baseline passed, new fails),
    `new_better`, and the exact McNemar p. Runs answered under different skills are flagged."""
    def table(rs):
        gs = [_graded(r) for r in rs]
        by: dict[str, list] = {}
        for gr in gs:
            for r in gr["results"]:
                if r["pass"] is not None:
                    by.setdefault(r["task"], []).append(bool(r["pass"]))
        n = len(by)
        all_ = sum(1 for v in by.values() if all(v))
        any_ = sum(1 for v in by.values() if any(v))
        return {"runs": [{"run": gr["run"], "model": gr["meta"].get("model"), "passed": gr["passed"], "n": gr["n"],
                          "wilson_pct": gr["wilson_pct"]} for gr in gs],
                "k": len(gs), "tasks": n, "pass_all_k": all_, "pass_any_k": any_, "pass_all_k_wilson": wilson(all_, n),
                "flaky": sorted(t for t, v in by.items() if any(v) and not all(v)),
                "never": sorted(t for t, v in by.items() if not any(v)), "_by": by}
    a = table(runs)
    out = {k: v for k, v in a.items() if k != "_by"}
    sk = {json.loads((Path(r) / "meta.json").read_text(encoding="utf-8")).get("skills_hash") if (Path(r) / "meta.json").exists()
          else None for r in runs}
    if len(sk) > 1:
        out["warning"] = f"these runs answered under different skills/config (skills_hash {sorted(map(str, sk))})"
    if versus:
        b = table(versus)
        maj = lambda v: sum(v) * 2 > len(v)
        common = sorted(set(a["_by"]) & set(b["_by"]))
        better = [t for t in common if maj(a["_by"][t]) and not maj(b["_by"][t])]      # new passes, base did not
        worse = [t for t in common if maj(b["_by"][t]) and not maj(a["_by"][t])]       # base passed, new fails
        out["versus"] = {k: v for k, v in b.items() if k != "_by"}
        out["paired"] = {"new": [str(Path(r).name) for r in runs], "base": [str(Path(r).name) for r in versus],
                         "tasks": len(common), "new_better": better, "new_worse": worse,
                         "mcnemar_p": mcnemar_exact(len(better), len(worse)),
                         "read": "a change needs more fixed than broken tasks AND no new failure on a hard rule "
                                 "(abstain, look-ahead, fund data, MNPI); with ~20 tasks only large effects show."}
    return out


# ------------------------------------------------------------------ calibration: digester quote check
def calibrate(path: str | Path | None = None, thresholds: list[float] | None = None) -> dict:
    """The digester's quote check against hand-labelled cards (evals/cards/labelled.json): false accepts
    (unfaithful quote passes) and false rejects per threshold, with the current rules; by perturbation kind."""
    from . import digest
    path = Path(path or EVALS / "cards" / "labelled.json")
    lab = json.loads(path.read_text(encoding="utf-8"))
    tr = _transcript()
    if tr is None:
        raise SystemExit("data/transcripts/15d7997409de.txt is not on this machine (fetch it with digest fetch)")
    base = digest.cfg()
    thresholds = thresholds or [0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]
    rows, sweep = [], []
    orig_cfg = digest.cfg
    try:
        for t in thresholds:
            digest.cfg = lambda t=t: {**base, "quote_min_ratio": t}
            tr.pop("_idx", None)
            fa, fr = [], []
            for r in lab["cards"]:
                ok = digest.check_card(r["card"], tr, lab["as_of"], "2026-10-16")["status"] == "ok"
                if ok and not r["labels"]["quote_faithful"]:
                    fa.append(r["id"])
                if not ok and r["labels"]["quote_faithful"]:
                    fr.append(r["id"])
            sweep.append({"threshold": t, "false_accepts": fa, "false_rejects": fr})
    finally:
        digest.cfg = orig_cfg
        tr.pop("_idx", None)
    for r in lab["cards"]:
        k = digest.check_card(r["card"], tr, lab["as_of"], "2026-10-16")
        rows.append({"id": r["id"], "kind": r["kind"], "faithful": r["labels"]["quote_faithful"],
                     "claim_supported": r["labels"]["claim_supported"], "ratio": k["quote_match"], "status": k["status"],
                     "blocking": [p["code"] for p in k["problems"] if p["blocking"]]})
    nf = sum(1 for r in rows if not r["faithful"])
    nt = len(rows) - nf
    cur = next(s for s in sweep if abs(s["threshold"] - base["quote_min_ratio"]) < 1e-9) if any(
        abs(s["threshold"] - base["quote_min_ratio"]) < 1e-9 for s in sweep) else None
    unsupported_ok = [r["id"] for r in rows if r["status"] == "ok" and not r["claim_supported"]]
    kinds = {}
    for r in rows:
        d = kinds.setdefault(r["kind"], {"n": 0, "ok": 0, "faithful": r["faithful"]})
        d["n"] += 1
        d["ok"] += r["status"] == "ok"
    pos_r = [r["ratio"] for r in rows if r["faithful"]]
    neg_r = [r["ratio"] for r in rows if not r["faithful"]]
    # threshold-free: how well the ratio ALONE separates faithful from unfaithful quotes (TRUE: ROC AUC)
    auc = (sum((p > n) + 0.5 * (p == n) for p in pos_r for n in neg_r) / (len(pos_r) * len(neg_r))) if pos_r and neg_r else None
    return {"labelled": len(rows), "faithful": nt, "unfaithful": nf, "threshold_now": base["quote_min_ratio"],
            "ratio_alone_auc": round(auc, 3) if auc is not None else None,
            "at_threshold_now": cur and {"false_accept": len(cur["false_accepts"]), "of": nf,
                                         "false_accept_wilson_pct": wilson(len(cur["false_accepts"]), nf),
                                         "false_reject": len(cur["false_rejects"]), "of_faithful": nt,
                                         "false_reject_wilson_pct": wilson(len(cur["false_rejects"]), nt)},
            "sweep": sweep, "by_kind": kinds,
            "claims_unsupported_but_ok": {"n": len(unsupported_ok), "of_ok": sum(1 for r in rows if r["status"] == "ok"),
                                          "ids": unsupported_ok,
                                          "read": "the quote is right but the claim adds context the quote does not "
                                                  "carry: code cannot see this (cross-language); a judge or a "
                                                  "MiniCheck-class checker would"},
            "cards": rows}


def second_pass(path: str | Path | None = None) -> dict | None:
    """Bernardo's blind labels in evals/cards/labels.md vs the build session's: raw agreement and Cohen's kappa per
    label (two labellers; alpha >= 0.8 reliable, 0.67-0.8 tentative: Artstein & Poesio). None until he fills it."""
    path = Path(path or EVALS / "cards" / "labels.md")
    if not path.exists():
        return None
    mine = {r["id"]: r["labels"] for r in json.loads((EVALS / "cards" / "labelled.json").read_text(encoding="utf-8"))["cards"]}
    yn = lambda s: {"y": True, "n": False}.get(s.strip().lower()[:1]) if s.strip() else None
    pairs = {"quote_faithful": [], "claim_supported": []}
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6 or cells[0] not in mine:
            continue
        for key, cell in (("quote_faithful", cells[-2]), ("claim_supported", cells[-1])):
            if yn(cell) is not None:
                pairs[key].append((str(mine[cells[0]][key]), str(yn(cell))))
    if not any(pairs.values()):
        return None
    return {k: {"n": len(v), "agree_pct": round(100 * sum(a == b for a, b in v) / len(v), 1) if v else None,
                "kappa": _kappa(v)} for k, v in pairs.items()}


def synthetic(seed: int = 16) -> list[dict]:
    """Quote variants with a known label, made by code from the natural re-digest cards (FactCC-style):
    negatives change what was said (a content word swapped for one from another card, a word added, a number
    changed, a negation or hedge removed, two cards spliced); positives add speech noise only (fillers, a
    stutter, punctuation and case). Seeded: the same set every run. Hand labels stay the reference; these give
    the false-accept bound its sample size (0 of 21 hand-labelled negatives still allows ~15%)."""
    import random
    from . import digest
    rng = random.Random(seed)
    nat = []
    for p in sorted((EVALS / "cards").glob("redigest-*.json")):
        nat += json.loads(p.read_text(encoding="utf-8"))
    c = digest.cfg()
    hedge_words = {t for w in list(c["hedge_required"]) + list(c["hedge_lexicon"]) for t in w.split()}
    content = lambda w: len(re.sub(r"\W", "", w)) >= 5 and not re.search(r"\d", w) and digest._fold(w.lower().strip(".,;:!?")) \
        not in hedge_words
    pool = sorted({w.strip(".,;:!?") for k in nat for w in k["quote"].split() if content(w)})
    out = []

    def add(kind, k, quote, faithful):
        out.append({"id": f"S{len(out) + 1:03d}", "kind": kind, "card": {**k, "quote": quote},
                    "labels": {"quote_faithful": faithful}})

    for k in nat:
        words = k["quote"].split()
        if len(words) < 6:
            continue
        idx = [i for i, w in enumerate(words) if content(w)]
        r = rng.random()
        if idx and r < 0.35:
            i = rng.choice(idx)
            new = rng.choice([w for w in pool if digest._fold(w.lower()) != digest._fold(words[i].lower().strip(".,;:!?"))])
            add("swap-word", k, " ".join(words[:i] + [new] + words[i + 1:]), False)
        elif r < 0.5:
            i = rng.randrange(1, len(words))
            new = rng.choice([w for w in pool if w.lower() not in (words[i - 1].lower(), words[i].lower())])
            add("add-word", k, " ".join(words[:i] + [new] + words[i:]), False)
        elif r < 0.62 and re.search(r"\d", k["quote"]):
            q = re.sub(r"\d+", lambda m: str(int(m.group(0)) + rng.choice([1, 2, 5, 10, 30])), k["quote"], count=1)
            add("number", k, q, False)
        elif r < 0.62 and re.search(r"(?i)\bn[aã]o\b", k["quote"]):
            add("negation", k, re.sub(r"(?i)\bn[aã]o\s+", "", k["quote"], count=1), False)
        elif r < 0.62:
            hw = [i for i, w in enumerate(words) if digest._fold(w.lower().strip(".,;:!?")) in {"pode", "vai", "talvez", "acho", "deve"}]
            if hw:
                i = hw[0]
                add("hedge", k, " ".join(words[:i] + words[i + 1:]), False)
            else:
                o = rng.choice(nat)["quote"].split()
                add("splice", k, " ".join(words[:len(words) // 2] + o[len(o) // 2:]), False)
        elif r < 0.7:
            o = rng.choice(nat)["quote"].split()
            add("splice", k, " ".join(words[:len(words) // 2] + o[len(o) // 2:]), False)
        elif r < 0.82:
            ws = list(words)
            for _ in range(2):
                ws.insert(rng.randrange(1, len(ws)), rng.choice(["eh,", "né,", "ah,"]))
            add("fillers", k, " ".join(ws), True)
        elif r < 0.92:
            i = rng.randrange(0, len(words))
            add("stutter", k, " ".join(words[:i + 1] + [words[i]] + words[i + 1:]), True)
        else:
            add("punctuation", k, re.sub(r"[,.;:!?]", "", k["quote"]).lower(), True)
    # adversarial kinds the random ones never produce (review A12, finding 11): a negating prefix on a content
    # word (a near-spelling the ASR rule could mistake for a caption error) and a dropped qualifier ("só", "mais")
    quals = {"só", "apenas", "mais", "sempre", "todos", "já", "ainda", "nenhum"}
    for k in nat:
        words = k["quote"].split()
        idx = [i for i, w in enumerate(words) if content(w) and w.isalpha() and w.islower() and len(w) >= 6]
        if idx and rng.random() < 0.35:
            i = rng.choice(idx)
            pre = "des" if digest._fold(words[i])[0] in "aeiou" else "in"
            add("prefix-negation", k, " ".join(words[:i] + [pre + words[i]] + words[i + 1:]), False)
        # interior only: dropping an edge word just trims the span (still the speaker's exact words; a cut before a
        # meaning-flipping "só" is a known gap, like hedge_cut but not checked)
        q = [i for i, w in enumerate(words) if w.lower().strip(".,;:!?") in quals and 0 < i < len(words) - 1]
        if q and len(words) > 6:
            add("drop-qualifier", k, " ".join(w for j, w in enumerate(words) if j != q[0]), False)
    return out


def calibrate_synthetic(seed: int = 16) -> dict:
    from . import digest
    tr = _transcript()
    if tr is None:
        raise SystemExit("data/transcripts/15d7997409de.txt is not on this machine")
    rows = []
    for s in synthetic(seed):
        k = digest.check_card(s["card"], tr, "2026-10-01", "2026-10-16")
        rows.append({"id": s["id"], "kind": s["kind"], "faithful": s["labels"]["quote_faithful"], "status": k["status"],
                     "ratio": k["quote_match"]})
    neg = [r for r in rows if not r["faithful"]]
    pos = [r for r in rows if r["faithful"]]
    fa = [r for r in neg if r["status"] == "ok"]
    fr = [r for r in pos if r["status"] != "ok"]
    kinds = {}
    for r in rows:
        d = kinds.setdefault(r["kind"], {"n": 0, "passed": 0, "faithful": r["faithful"]})
        d["n"] += 1
        d["passed"] += r["status"] == "ok"
    return {"seed": seed, "negatives": len(neg), "false_accepts": len(fa), "false_accept_wilson_pct": wilson(len(fa), len(neg)),
            "false_accept_ids": [r["id"] for r in fa], "positives": len(pos), "false_rejects": len(fr),
            "false_reject_wilson_pct": wilson(len(fr), len(pos)), "false_reject_ids": [r["id"] for r in fr], "by_kind": kinds}


# ------------------------------------------------------------------ noise: independent digests of one source
def _kappa(pairs: list[tuple[str, str]]) -> float | None:
    if not pairs:
        return None
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    cats = {x for p in pairs for x in p}
    pe = sum((sum(a == c for a, _ in pairs) / n) * (sum(b == c for _, b in pairs) / n) for c in cats)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else None      # one category only: kappa is undefined


def noise(digests: dict[str, list[dict]], tr: dict | None = None, min_overlap: float = 0.5) -> dict:
    """How much independent digests of the same transcript disagree. Two cards are the same claim when their
    quotes share at least `min_overlap` of the shorter span. Per pair: how many of each digest's cards the other
    found (recall both ways), and on the matched cards, agreement on type (Cohen's kappa), speaker, hedge words,
    deadline. The scatter between digests is noise: no gold is needed to measure it (Kahneman et al., Noise)."""
    from . import digest
    tr = tr or _transcript()
    spans = {n: [card_span(k, tr) for k in cs] for n, cs in digests.items()}
    names = list(digests)
    pairs = []
    for i, x in enumerate(names):
        for y in names[i + 1:]:
            used, match = set(), []
            for a, sa in enumerate(spans[x]):
                best = max(((overlap(sa, sb), b) for b, sb in enumerate(spans[y]) if b not in used), default=(0, None))
                if best[0] >= min_overlap:
                    used.add(best[1])
                    match.append((a, best[1]))
            cx, cy = digests[x], digests[y]
            hset = lambda k: sorted({str(h).lower() for h in (k.get("hedge") or [])} if isinstance(k.get("hedge"), list)
                                    else {str(k.get("hedge")).lower()} if k.get("hedge") else set())
            types = [(cx[a].get("type"), cy[b].get("type")) for a, b in match]
            pairs.append({
                "a": x, "b": y, "n_a": len(cx), "n_b": len(cy), "matched": len(match),
                "a_found_in_b_pct": round(100 * sum(1 for s in spans[x] if any(overlap(s, t) >= min_overlap for t in spans[y])) / max(1, len(cx)), 1),
                "b_found_in_a_pct": round(100 * sum(1 for s in spans[y] if any(overlap(s, t) >= min_overlap for t in spans[x])) / max(1, len(cy)), 1),
                "type_agree_pct": round(100 * sum(a == b for a, b in types) / max(1, len(types)), 1),
                "type_kappa": _kappa(types),
                "type_disagreements": [{"t": cx[a].get("t"), x: cx[a].get("type"), y: cy[b].get("type")}
                                       for a, b in match if cx[a].get("type") != cy[b].get("type")],
                "speaker_agree_pct": round(100 * sum(digest.speaker_key(cx[a].get("speaker")) == digest.speaker_key(cy[b].get("speaker"))
                                                     for a, b in match) / max(1, len(match)), 1),
                "hedge_agree_pct": round(100 * sum(hset(cx[a]) == hset(cy[b]) for a, b in match) / max(1, len(match)), 1),
                "deadline_agree_pct": round(100 * sum(str(cx[a].get("deadline") or "") == str(cy[b].get("deadline") or "")
                                                      for a, b in match) / max(1, len(match)), 1),
            })
    return {"digests": {n: len(c) for n, c in digests.items()}, "min_overlap": min_overlap, "pairs": pairs}


def noise_default() -> dict:
    cards = EVALS / "cards"
    orig = ROOT / "notes" / "podcasts" / "mind-asset" / "2026-10-01-fundos-multimercado-ia-alternativos.cards.json"
    d = {"original-15oct": json.loads(orig.read_text(encoding="utf-8"))["cards"]}
    for p in sorted(cards.glob("redigest-*.json")):
        d[p.stem] = json.loads(p.read_text(encoding="utf-8"))
    return noise(d)


# ------------------------------------------------------------------ CLI
def _print(obj):
    print(json.dumps(obj, indent=1, ensure_ascii=False, default=str))


def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack evals", description="Own test set: tasks with known answers, graded by code")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list the tasks")
    pr = sub.add_parser("prompt", help="print one task's full prompt (shared rules + task)")
    pr.add_argument("task")
    pr.add_argument("--run", default="evals/runs/<run>")
    nw = sub.add_parser("new-run", help="create evals/runs/<date>-<label>/ with meta.json")
    nw.add_argument("label")
    nw.add_argument("--model", required=True, help="model id that answers, e.g. claude-opus-5-5")
    nw.add_argument("--note", default="")
    gr = sub.add_parser("grade", help="grade a run directory")
    gr.add_argument("run")
    gr.add_argument("--no-log", action="store_true", help="re-grade without a run-log line")
    rp = sub.add_parser("report", help="k runs of one configuration [--versus k runs of another]")
    rp.add_argument("runs", nargs="+")
    rp.add_argument("--versus", nargs="*")
    sub.add_parser("calibrate", help="digester quote check vs hand-labelled cards")
    sub.add_parser("noise", help="agreement between independent digests of the Mind Asset episode")
    a = p.parse_args(argv)
    if a.cmd == "list":
        for t in tasks()["tasks"]:
            print(f"{t['id']:<26} {t['agent']:<16} {t['kind']:<9} as of {t['asof']}")
        return 0
    if a.cmd == "prompt":
        print(prompt(a.task, a.run))
        return 0
    if a.cmd == "new-run":
        d = EVALS / "runs" / f"{date.today().isoformat()}-{re.sub(r'[^a-z0-9-]+', '-', a.label.lower())}"
        d.mkdir(parents=True, exist_ok=True)
        import subprocess
        try:
            head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        except OSError:
            head = None
        (d / "meta.json").write_text(json.dumps({"model": a.model, "label": a.label, "note": a.note,
                                                 "tasks_version": tasks()["version"], "git_head": head,
                                                 "skills_hash": config_hash(SKILL_FILES),
                                                 "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()},
                                                indent=1), encoding="utf-8")
        print(d.relative_to(ROOT).as_posix())
        return 0
    if a.cmd == "grade":
        out = grade(a.run, log=not a.no_log)
        _print({k: v for k, v in out.items() if k != "results"} |
               {"failed": [{"task": r["task"], "checks": [c for c in r["checks"] if not c["ok"]]}
                           for r in out["results"] if r["pass"] is False]})
        return 0
    if a.cmd == "report":
        _print(report(a.runs, a.versus))
        return 0
    if a.cmd == "calibrate":
        out = calibrate()
        out["synthetic"] = calibrate_synthetic()
        out["second_pass"] = second_pass() or "evals/cards/labels.md not filled yet (Bernardo's blind labels)"
        runlog.log(runlog.new_run_id(), "evals:calibrate", "ok", labelled=out["labelled"],
                   threshold=out["threshold_now"], **(out["at_threshold_now"] or {}),
                   synthetic_false_accepts=out["synthetic"]["false_accepts"], synthetic_negatives=out["synthetic"]["negatives"],
                   synthetic_false_rejects=out["synthetic"]["false_rejects"], synthetic_positives=out["synthetic"]["positives"])
        _print({k: v for k, v in out.items() if k != "cards"})
        return 0
    if a.cmd == "noise":
        out = noise_default()
        runlog.log(runlog.new_run_id(), "evals:noise", "ok", digests=out["digests"],
                   pairs=[{k: p[k] for k in ("a", "b", "matched", "a_found_in_b_pct", "b_found_in_a_pct", "type_kappa")}
                          for p in out["pairs"]])
        _print(out)
        return 0
    return 2
