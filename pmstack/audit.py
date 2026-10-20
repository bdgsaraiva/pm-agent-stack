"""Number auditor (agent 5): every figure in a written output must come from code.

Extracts each figure, date and alert ref from a markdown output (morning note, Friday critic page,
critic questions) and checks it, one by one, against what code produced that day: briefs/<date>/facts.json
and facts.md, the journal, and any extra JSON the caller passes (a critic card, the weekly pack).

Why code and not a model (docs/research/critic.md): GPT-4-Turbo still got 15% of FinanceBench answers
wrong with the exact evidence in context; LLM verifiers pass most wrong answers (Valmeekam et al.;
Stechly et al.); model-based numerical fact-checking tops out near 58 macro-F1 (QuanTemp). Checking
each claim separately beats checking the draft as a whole (Chain-of-Verification; FActScore).

Statuses per figure:
  matched     value found (to its displayed precision) in a source whose context shares a word with the
              figure's sentence (e.g. "RBOB")
  unbound     value found, but only in an unrelated context: possible coincidence, listed in the report
  orphan      value not found anywhere: flagged at the top of the output and in the run log
  structural  a window, tenor, time, rule number or calendar item ("60-day", "10y", "15:30", "Zweig #3")
  trivial     a small unit-less integer (a count)
Dates (YYYY-MM-DD) must appear in the sources; alert refs (alerts:<date>#<n>) must exist and share a
word with their line.
"""
from __future__ import annotations

import argparse
import functools
import json
import math
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from . import runlog

ROOT = Path(__file__).resolve().parents[1]
BRIEFS = None  # default: monitor.BRIEFS (so tests that move the briefs folder move it here too)


def _briefs(b: Path | None = None) -> Path:
    if b is not None:
        return b
    if BRIEFS is not None:
        return BRIEFS
    from . import monitor
    return monitor.BRIEFS
BANNER_MARK = "**Number audit"

DATE_RE = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)")
REF_RE = re.compile(r"alerts:(\d{4}-\d{2}-\d{2})#(\d+)((?:\s*,\s*#\d+)*)")
URL_RE = re.compile(r"https?://[^\s)\]>]+")
JID_RE = re.compile(r"\b\d{8}-\d{4}-[a-z0-9-]+")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
FIG_RE = re.compile(
    r"(?<![\w.^/=$])(?P<sign>[+\-\u2212\u2013])?(?P<cur>(?:[A-Z]{1,2})?\$)?(?P<num>\d{1,3}(?:,\d{3})+|\d+)"
    r"(?:\.(?P<dec>\d+)|(?![.,]\d))"
    r"(?P<unit>\s?(?:%|pp|bps|bp|sd|x|R|th|st|nd|rd|mb/d|kb/d|b/d|mbbl|mb|kb|bbl|bpd|mmbtu|mt|k|bn|tn|mn)(?![A-Za-z/]))?"
    r"(?P<other>(?<=\d)[A-Za-z][A-Za-z/]*)?(?![\w])")
UNIT_KIND = {"%": "pct", "pp": "pct", "sd": "sd", "th": "pctile", "st": "pctile", "nd": "pctile", "rd": "pctile",
             "bp": "bp", "bps": "bp", "R": "r", "x": "x"}
COMPAT = {"pct": {"pct", "level", "chg"}, "sd": {"sd"}, "pctile": {"pctile", "level"}, "bp": {"bp", "chg", "pct", "level"},
          "r": {"r", "level"}, "x": {"x", "level"}, "level": {"level", "chg"},
          "none": {"level", "chg", "pct", "pctile", "r", "bp", "x"}}


def _key_kind(key: str) -> str:
    """What a stored number measures, from its field name (so a z-score can't vouch for a % move)."""
    k = str(key).lower().rsplit(".", 1)[-1]
    if k in ("z1", "wow_z", "surprise_z", "week_sd") or k.endswith("_z") or k.endswith("_sd"):
        return "sd"
    if "pct_3y" in k or "on_side_pct" in k or k in ("pct", "crowd_on_side_pct") or "pctile" in k:
        return "pctile"
    if k.startswith("ret") or "pct" in k or k.endswith("_pp") or k == "change_pp":
        return "pct"
    if k in ("r_now", "r_multiple", "expected_r", "avg_r", "median_r", "worst_r") or k.endswith("_r"):
        return "r"
    if k == "change":
        return "chg"
    if k == "reward_risk":
        return "x"
    return "level"


def _fig_kind(m: re.Match) -> str:
    unit = (m.group("unit") or "").strip()
    if unit:
        return UNIT_KIND.get(unit, "level")
    return "level" if m.group("other") or m.group("cur") else "none"
WORD_RE = re.compile(r"[a-z][a-z0-9&]{2,}")
SCALE = {"k": 1e3, "mn": 1e6, "bn": 1e9, "tn": 1e12}


def cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "critic.yaml").read_text(encoding="utf-8"))["audit"]


# ------------------------------------------------------------------ the pool of code-produced facts
@dataclass
class Pool:
    # (signed value, context, kind, subject): subject = the market/series a number belongs to ("" = use context)
    values: list[tuple[float, str, str, str]] = field(default_factory=list)
    dates: set[str] = field(default_factory=set)
    alerts: dict[str, dict[int, str]] = field(default_factory=dict)  # date -> rank -> text
    names: set[str] = field(default_factory=set)                     # instrument names with digits
    idnames: dict[str, str] = field(default_factory=dict)            # series id -> name (BZ=F -> Brent front month)

    def finish(self) -> "Pool":
        """Give every number whose context holds a series id the series' name too, so "Brent" binds to BZ=F."""
        if self.idnames:
            out = []
            for v, ctx, kind, subj in self.values:
                toks = set(ctx.split()) | set(subj.split())
                extra = " ".join(self.idnames[t] for t in toks if t in self.idnames)
                out.append((v, f"{ctx} {extra}" if extra else ctx, kind, f"{subj} {extra}".strip() if subj else subj))
            self.values = out
        return self

    def add_value(self, v, ctx: str, kind: str = "level", subject: str = ""):
        try:
            f = float(v)
        except (TypeError, ValueError):
            return
        if math.isfinite(f) and not isinstance(v, bool):
            self.values.append((f, ctx, kind, subject or ""))

    def add_text(self, text: str, ctx: str | None = None, subject: str = ""):
        if not isinstance(text, str) or not text:
            return
        self.dates.update(DATE_RE.findall(text))
        masked = _mask(text, self)
        for m in FIG_RE.finditer(masked):
            k = _fig_kind(m)
            self.add_value(_value(m, signed=True), ctx or text, "level" if k == "none" else k, subject or text)

    def add_obj(self, obj, ctx: str = "", subject: str = ""):
        """Walk JSON-like data; a dict's string fields give context to its numbers."""
        if isinstance(obj, dict):
            label = " ".join(str(obj[k]) for k in ("name", "market", "id", "code", "series", "title", "group",
                                                    "price_ref", "text", "label", "term") if isinstance(obj.get(k), str))
            # a row may name its own binding words (narratives: words only its name has, so "oil" in one
            # narrative's name cannot vouch for another narrative's figure - agent 7 review, finding 5)
            explicit = obj.get("audit_subject") if isinstance(obj.get("audit_subject"), str) else None
            for idk in ("id", "code", "series", "price_ref"):
                if isinstance(obj.get(idk), str) and isinstance(explicit or obj.get("name"), str):
                    self.idnames.setdefault(obj[idk], explicit or obj["name"])
            here = f"{ctx} {label}".strip()
            # the market a row's numbers belong to: its own name/series, else its parent's (never field names)
            own = explicit or " ".join(str(obj[k]) for k in ("name", "market", "series", "id", "code", "price_ref", "term")
                                       if isinstance(obj.get(k), str))
            subj = own or subject
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    self.add_obj(v, f"{here} {k}", subj)
                elif isinstance(v, str):
                    if k == "name" and re.search(r"\d", v):
                        self.names.add(v)
                    self.add_text(v, f"{here} {v}", subj or v)
                else:
                    self.add_value(v, f"{here} {k}", _key_kind(k), subj)
        elif isinstance(obj, list):
            for v in obj:
                self.add_obj(v, ctx, subject)
        elif isinstance(obj, str):
            self.add_text(obj, f"{ctx} {obj}", subject)
        else:
            self.add_value(obj, ctx, "level", subject)


def _value(m: re.Match, signed: bool = False) -> float:
    v = float(m.group("num").replace(",", "") + ("." + m.group("dec") if m.group("dec") else ""))
    return -v if signed and m.group("sign") in ("-", "\u2212", "\u2013") else v


def _name_patterns(pool: Pool) -> list[re.Pattern]:
    pats = []
    for n in pool.names:
        for m in re.finditer(r"([A-Za-z&.]+\.?)\s(\d[\d,]*)", n):
            pats.append(re.compile(re.escape(m.group(1)) + r"\s" + re.escape(m.group(2)) + r"\b"))
    return pats


def _mask(text: str, pool: Pool | None = None, extra: list[re.Pattern] | None = None) -> str:
    """Blank out spans that are not figures (urls, ids, dates, refs, names with digits), keeping offsets."""
    def blank(s: str, rx) -> str:
        return rx.sub(lambda m: " " * len(m.group(0)), s)
    for rx in (COMMENT_RE, URL_RE, REF_RE, JID_RE, DATE_RE):
        text = blank(text, rx)
    for rx in (_name_patterns(pool) if pool else []) + (extra or []):
        text = blank(text, rx)
    return text


def _journal_entries() -> list[dict]:
    try:
        from . import journal
        return journal.load_all()
    except Exception:
        return []


def _strip_discovery(facts: dict) -> dict:
    """Discovery candidates carry news titles and terms ("5 reasons gold...", "opec+ 2"): their digits are not code
    figures, so only the counts, scores and context lines enter the pool."""
    sec = (facts.get("sections") or {}).get("discovery") if isinstance(facts.get("sections"), dict) else facts.get("discovery")
    if not isinstance(sec, dict) or not sec.get("candidates"):
        return facts
    drop = ("label", "headlines", "terms", "lead_term", "id", "decision", "demoted")
    cands = [{k: v for k, v in x.items() if k not in drop} for x in sec["candidates"]]
    sec2 = {**sec, "candidates": cands}
    if isinstance(facts.get("sections"), dict) and "discovery" in facts["sections"]:
        return {**facts, "sections": {**facts["sections"], "discovery": sec2}}
    return {**facts, "discovery": sec2}


def pool_for(asof: str | None, extra: list | None = None, with_journal: bool = True,
             briefs: Path | None = None) -> Pool:
    pool = Pool()
    briefs = _briefs(briefs)
    if asof:
        pool.dates.add(asof)
        d = briefs / asof
        fj = d / "facts.json"
        if fj.exists():
            facts = json.loads(fj.read_text(encoding="utf-8"))
            pool.add_obj(_strip_discovery(facts))
            pool.alerts[asof] = {int(a["rank"]): a.get("text", "") for a in facts.get("alerts", []) if "rank" in a}
        fm = d / "facts.md"
        if fm.exists():
            skip = False
            for line in fm.read_text(encoding="utf-8").splitlines():
                if line.startswith("## "):   # the consensus map is checked from facts.json, where each row
                    skip = line.startswith(("## Consensus map", "## Narrative discovery"))   # carries its own subject;
                    # its md rows mix names; discovery headlines are news text, not code figures
                if not skip:
                    pool.add_text(line, line)
    if with_journal:
        for e in _journal_entries():
            e = {k: v for k, v in e.items() if not k.startswith("_")}
            pool.add_obj(e, f"{e.get('market', '')} {e.get('price_ref', '')}")
        try:
            from . import journal
            pool.add_obj(journal.open_book())
        except Exception:
            pass
    for x in extra or []:
        if isinstance(x, (str, Path)) and Path(x).exists():
            p = Path(x)
            pool.add_obj(json.loads(p.read_text(encoding="utf-8")) if p.suffix == ".json" else p.read_text(encoding="utf-8"))
        else:
            pool.add_obj(x)
    return pool.finish()


def _alerts_for(date: str, pool: Pool, briefs: Path) -> dict[int, str] | None:
    if date in pool.alerts:
        return pool.alerts[date]
    p = briefs / date / "alerts.json"
    if p.exists():
        rows = json.loads(p.read_text(encoding="utf-8"))
        rows = rows.get("alerts", rows) if isinstance(rows, dict) else rows
        pool.alerts[date] = {int(a["rank"]): a.get("text", "") for a in rows if "rank" in a}
        return pool.alerts[date]
    return None


# ------------------------------------------------------------------ matching
@functools.lru_cache(maxsize=1)
def _aliases() -> dict:
    return cfg().get("aliases") or {}


def _words(s: str, stop: set[str]) -> set[str]:
    words = {w for w in WORD_RE.findall(s.lower()) if w not in stop}
    for k, v in _aliases().items():   # "natgas" also means "natural gas", etc.
        if k in words:
            words |= set(v)
    return words


def _variants(c: float, unit: str) -> list[float]:
    if unit in ("%", "pp"):
        return [c, c * 100, c / 100]
    if unit in ("bp", "bps"):
        return [c, c * 100, c * 10000]
    return [c]


def _close(v: float, decimals: int, c: float) -> bool:
    tol = 0.5 * 10 ** (-decimals) + 1e-9
    return abs(v - c) <= tol * (1 + 1e-9)


def _sentences(text: str) -> list[tuple[int, int]]:
    """Spans of sentences/clauses: split on line breaks and sentence ends."""
    spans, start = [], 0
    for m in re.finditer(r"\n|(?<=[.;!?])\s+(?=[A-Z(\[`*])", text):
        spans.append((start, m.start()))
        start = m.end()
    spans.append((start, len(text)))
    return spans


def audit_text(text: str, pool: Pool, briefs: Path | None = None) -> dict:
    c = cfg()
    briefs = _briefs(briefs)
    stop = set(c["stop_words"])
    structural = [re.compile(p, re.I | re.M) for p in c["structural_patterns"]]
    masked = _mask(text, pool)
    line_starts = [0] + [m.end() for m in re.finditer(r"\n", text)]

    def line_of(pos: int) -> int:
        lo = 0
        for i, s in enumerate(line_starts):
            if s <= pos:
                lo = i
        return lo + 1

    sents = _sentences(text)

    def sentence(pos: int) -> str:
        for a, b in sents:
            if a <= pos <= b:
                return text[a:b]
        return text

    struct_spans = [(m.start(), m.end()) for rx in structural for m in rx.finditer(masked)]
    prev, pos = "", 0
    for line in text.split("\n"):             # ordered-list markers, only where a list can start or continue
        mm = re.match(r"\s*\d{1,2}\.\s", line)
        if mm and (not prev.strip() or prev.lstrip().startswith("#") or re.match(r"\s*\d{1,2}\.\s", prev)):
            struct_spans.append((pos, pos + mm.end()))
        prev, pos = line, pos + len(line) + 1
    figures = []
    for m in FIG_RE.finditer(masked):
        unit = (m.group("unit") or "").strip()
        dec = len(m.group("dec") or "")
        v = _value(m)
        signed = m.group("sign") is not None
        sv = _value(m, signed=True)
        fk = _fig_kind(m)
        if unit in SCALE:
            vs, dec_scale = v * SCALE[unit], SCALE[unit]
        else:
            vs, dec_scale = v, 1
        sent = sentence(m.start())
        sw = _words(sent, stop)
        hits = []
        for cv, ctx, kind, subj in pool.values:
            if kind not in COMPAT[fk]:
                continue                 # a z-score can't vouch for a % move, a price for a percentile, etc.
            for var in _variants(cv, unit):
                var = var / dec_scale
                # a written sign must agree with the source's sign; unsigned text compares magnitudes
                ok = _close(sv, dec, var) if signed else _close(v, dec, abs(var))
                if ok:
                    hits.append((ctx, subj))
                    break
        status, why = None, None
        if any(a <= m.start() < b for a, b in struct_spans):
            status = "structural"       # windows, tenors, times, calendar: checked before values on purpose
        elif hits:
            # bound = the sentence names the number's own market (its subject), not just shares a field word
            bound = [h for h, sj in hits if _words(sj or h, stop) & sw]
            status = "matched" if bound else "unbound"
            why = (bound or [h for h, _ in hits])[0][:120]
        elif not unit and not dec and v <= c["trivial_max_int"] and not m.group("cur") and not m.group("other"):
            status = "trivial"
        else:
            status = "orphan"
        figures.append({"text": m.group(0).strip(), "value": vs, "unit": unit or (m.group("other") or ""), "line": line_of(m.start()),
                        "status": status, "source": why})

    dates = []
    for m in DATE_RE.finditer(COMMENT_RE.sub(lambda x: " " * len(x.group(0)), URL_RE.sub(lambda x: " " * len(x.group(0)), text))):
        if REF_RE.match(text, max(0, m.start() - 7)):
            continue  # the date inside an alert ref is checked with the ref
        dates.append({"date": m.group(1), "line": line_of(m.start()), "status": "ok" if m.group(1) in pool.dates else "orphan"})

    refs = []
    for m in REF_RE.finditer(text):
        d, ranks = m.group(1), [int(m.group(2))] + [int(x) for x in re.findall(r"#(\d+)", m.group(3) or "")]
        line = text[line_starts[line_of(m.start()) - 1]:].split("\n", 1)[0]
        lw = _words(REF_RE.sub(" ", line), stop)
        table = _alerts_for(d, pool, briefs)
        for r in ranks:
            ref = f"alerts:{d}#{r}"
            if table is None:
                st, txt = "no-pack", None
            elif r not in table:
                st, txt = "missing", None
            else:
                txt = table[r]
                st = "ok" if _words(txt, stop) & lw else "mismatch"
            refs.append({"ref": ref, "line": line_of(m.start()), "status": st, "alert": txt})

    n = {k: sum(1 for f in figures if f["status"] == k) for k in ("matched", "unbound", "orphan", "structural", "trivial")}
    checked = n["matched"] + n["unbound"] + n["orphan"]
    return {
        "figures": figures, "dates": dates, "refs": refs,
        "summary": {**n, "checked": checked,
                    "precision": round((n["matched"] + n["unbound"]) / checked, 3) if checked else None,
                    "dates_bad": sum(1 for d in dates if d["status"] != "ok"),
                    "refs_bad": sum(1 for r in refs if r["status"] != "ok")},
    }


def problems(report: dict) -> list[str]:
    out = [f"`{f['text']}` (line {f['line']})" for f in report["figures"] if f["status"] == "orphan"]
    out += [f"`{d['date']}` (line {d['line']})" for d in report["dates"] if d["status"] != "ok"]
    out += [f"`{r['ref']}` {r['status']} (line {r['line']})" for r in report["refs"] if r["status"] != "ok"]
    out += [f"`{f['text']}` unbound (line {f['line']})" for f in report["figures"] if f["status"] == "unbound"]
    return out


def banner(report: dict) -> str:
    s = report["summary"]
    orphans = [f"`{f['text']}` (line {f['line']})" for f in report["figures"] if f["status"] == "orphan"]
    dates = [f"`{d['date']}` (line {d['line']})" for d in report["dates"] if d["status"] != "ok"]
    refs = [f"`{r['ref']}` (line {r['line']}, {'does not match its line' if r['status'] == 'mismatch' else r['status']})"
            for r in report["refs"] if r["status"] != "ok"]
    unbound = [f"`{f['text']}` (line {f['line']})" for f in report["figures"] if f["status"] == "unbound"]
    parts = []
    if orphans:
        parts.append(f"{len(orphans)} of {s['checked']} figures not found in the fact pack or journal: " + ", ".join(orphans) + ".")
    if dates:
        parts.append("Dates not in the sources: " + ", ".join(dates) + ".")
    if refs:
        parts.append("Alert refs: " + ", ".join(refs) + ".")
    if unbound:
        parts.append("Found only under another market, check: " + ", ".join(unbound) + ".")
    return f"> {BANNER_MARK} (code):** " + " ".join(parts) if parts else ""


def insert_banner(text: str, ban: str) -> str:
    lines = [l for l in text.split("\n") if not l.startswith(f"> {BANNER_MARK}")]
    while len(lines) > 1 and lines[0].strip() == "" :
        lines.pop(0)
    if lines and lines[0] == "---" and "---" in lines[1:]:      # keep a note's YAML header first
        end = lines.index("---", 1) + 1
        head, rest = lines[:end], insert_banner("\n".join(lines[end:]), ban).split("\n")
        return re.sub(r"\n{3,}", "\n\n", "\n".join(head + rest))
    if not ban:
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    i = 0
    while i < len(lines) and (lines[i].startswith("<!--") or lines[i].startswith("# ") or not lines[i].strip()):
        i += 1
        if i and lines[i - 1].startswith("# "):
            break
    out = lines[:i] + ["", ban, ""] + lines[i:]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out))


def _asof_from(path: Path) -> str | None:
    for part in reversed(path.resolve().parts):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", part):
            return part
    return None


def audit_file(path: str | Path, asof: str | None = None, extra: list | None = None, flag: bool = False,
               step: str | None = None, briefs: Path | None = None) -> dict:
    path = Path(path)
    asof = asof or _asof_from(path) or (datetime.now(timezone.utc) - timedelta(hours=3)).date().isoformat()
    text = path.read_text(encoding="utf-8")
    body = "\n".join(l for l in text.split("\n") if not l.startswith(f"> {BANNER_MARK}"))
    # a note's YAML header is metadata, not prose - but only a real header (a mapping with type or date), so a
    # report that merely opens with two "---" rules is still audited (review A11, finding 7). Prose fields in
    # the header (questions, source_note) stay audited.
    hdr = re.match(r"^---\n(.*?)\n---\n", body, re.S)
    try:
        meta = yaml.safe_load(hdr.group(1)) if hdr else None
    except yaml.YAMLError:
        meta = None
    if isinstance(meta, dict) and ("type" in meta or "date" in meta):
        keep = []
        prose_key = False
        for line in hdr.group(0).split("\n"):
            m = re.match(r"^([A-Za-z_]+):", line)
            if m:
                prose_key = m.group(1) in ("questions", "source_note")
            keep.append(line if prose_key and not m else re.sub(r"[^\n]", " ", line) if not prose_key else
                        " " * (len(m.group(0))) + line[len(m.group(0)):])
        body = "\n".join(keep) + body[hdr.end():]
    pool = pool_for(asof, extra, briefs=briefs)
    rep = audit_text(body, pool, briefs=briefs)
    rep.update({"file": str(path), "asof": asof, "audited_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()})
    out = path.with_suffix(".audit.json")
    out.write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    if flag:
        path.write_text(insert_banner(text, banner(rep)), encoding="utf-8")
    s = rep["summary"]
    bad = s["orphan"] + s["dates_bad"] + s["refs_bad"] + s["unbound"]
    runlog.log(runlog.new_run_id(), step or f"audit:{path.stem}", "ok" if not bad else "partial", file=str(path),
               asof=asof, checked=s["checked"], matched=s["matched"], unbound=s["unbound"], orphans=s["orphan"],
               dates_bad=s["dates_bad"], refs_bad=s["refs_bad"], precision=s["precision"],
               problems=problems(rep)[:20], output=str(out))
    return rep


def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack audit", description="Check every figure in an output against code")
    p.add_argument("file")
    p.add_argument("--date", help="fact-pack date (default: from the path, else today BRT)")
    p.add_argument("--facts", nargs="*", default=[], help="extra JSON or markdown files code produced")
    p.add_argument("--flag", action="store_true", help="write the orphan banner at the top of the file")
    p.add_argument("--step", help="run-log step name")
    a = p.parse_args(argv)
    rep = audit_file(a.file, a.date, a.facts, a.flag, a.step)
    s = rep["summary"]
    print(json.dumps({"file": rep["file"], "asof": rep["asof"], **s, "problems": problems(rep)},
                     indent=1, ensure_ascii=False))
    return 1 if s["orphan"] + s["dates_bad"] + s["refs_bad"] + s["unbound"] else 0
