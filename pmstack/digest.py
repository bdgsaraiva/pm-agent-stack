"""Research digester (agent 10): podcasts, papers and public notes -> claim cards, a note in Bernardo's
summary format, a call ledger and an index the critic reads.

Why claim cards and code checks (docs/research/digester.md):
  - LLM summaries of long spoken sources are wrong often enough to matter: 14.7-51% of interview summaries
    carry at least one factual error (TofuEval); omissions in 52-85% of book-length summaries (FABLES).
  - Model-emitted citations are unsupported ~50% of the time (ALCE), so the quote on every card must be
    found in the transcript by code, and every number on a card must sit inside its quote.
  - The model never computes or recalls a number (FinanceBench: 15% wrong with oracle evidence; models
    recall pre-cutoff market levels and leak later events into dated text: Sarkar & Vafa; Lopez-Lira et al.).
  - Public calls are right 46.9-48% of the time (CXO; Bailey et al.); oil surveys lose to no-change
    (Alquist & Kilian). So forecast cards are scored by code against stored prices, and a speaker's record
    carries weight only after `record_min_calls` resolved calls.

Files:
  data/transcripts/<sha12>.txt + .json   full transcript and its metadata (local only, gitignored)
  notes/<kind>/<series>/<date>-<slug>.md   the note (YAML header + body in the summary format)
  notes/.../<date>-<slug>.cards.json       checked cards (status ok / flagged / rejected, problems)
  notes/.../<date>-<slug>.facts.json       code facts for the note (moves since recording), for the auditor
  notes/index.md                           one line per note, newest first
"""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import math
import re
import sys
import unicodedata
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import yaml

from . import runlog, store

ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT / "notes"
TRANSCRIPTS = ROOT / "data" / "transcripts"
NOTE_TYPES = ("podcast", "research", "paper", "letter", "video", "article")
CARD_TYPES = ("data", "forecast", "opinion")
DIRECTIONS = ("up", "down", "flat")
BLOCKING = ("quote_not_found", "quote_altered", "hedge_cut", "quote_too_long", "number_not_in_quote", "extrinsic_term", "hedge_dropped",
            "bad_type", "bad_deadline", "unknown_market", "prob_not_in_quote", "missing_field")


def cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "digest.yaml").read_text(encoding="utf-8"))


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _today_brt() -> str:
    return (_now() - timedelta(hours=3)).date().isoformat()


def _num(x):
    try:
        return None if x is None or x == "" or isinstance(x, bool) else float(x)
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ locations (time or page)
def parse_loc(x) -> float | None:
    """'01:02:03', '62:03', '12:30', 3723 (seconds) or 'p4' (page 4) -> a number on the source's own axis."""
    if x is None or x == "":
        return None
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    s = str(x).strip().strip("[]")
    m = re.fullmatch(r"[pP](?:age)?\s*(\d+)", s)
    if m:
        return float(m.group(1))
    parts = s.split(":")
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return None
    sec = 0.0
    for n in nums:
        sec = sec * 60 + n
    return sec


def fmt_loc(v: float | None, kind: str = "time") -> str:
    if v is None:
        return "-"
    if kind == "page":
        return f"p{int(v)}"
    v = int(v)
    return f"{v // 3600:02d}:{v % 3600 // 60:02d}:{v % 60:02d}"


# ------------------------------------------------------------------ transcripts
LINE_RE = re.compile(r"^\[(\d{1,2}:\d{2}(?::\d{2})?|[pP]\d+)\]\s?(.*)$")


def _norm_lines(lines: list[tuple[float | None, str]], kind: str) -> str:
    out = []
    for loc, text in lines:
        text = re.sub(r"\s+", " ", text or "").strip()
        if text:
            out.append(f"[{fmt_loc(loc, kind)}] {text}" if loc is not None else text)
    return "\n".join(out) + "\n"


def _parse_vtt_srt(text: str) -> list[tuple[float | None, str]]:
    out, cur = [], None
    for raw in text.splitlines():
        line = raw.strip()
        m = re.match(r"^(\d{1,2}:)?\d{2}:\d{2}[.,]\d{3}\s*-->", line)
        if m:
            cur = parse_loc(line.split("-->")[0].strip().replace(",", ".").split(".")[0])
            continue
        if not line or line.isdigit() or line.upper().startswith("WEBVTT") or line.startswith("NOTE"):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        if out and out[-1][0] == cur and cur is not None:
            out[-1] = (cur, out[-1][1] + " " + line)
        else:
            out.append((cur, line))
    return out


def _pdf_lines(data: bytes) -> list[tuple[float | None, str]]:
    from pypdf import PdfReader      # lazy: only papers need it
    reader = PdfReader(io.BytesIO(data))
    out = []
    for i, page in enumerate(reader.pages, 1):
        for para in re.split(r"\n\s*\n", page.extract_text() or ""):
            if para.strip():
                out.append((float(i), para))
    return out


def _html_lines(text: str) -> list[tuple[float | None, str]]:
    text = re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?i)<(br|/p|/div|/li|/h\d)[^>]*>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return [(None, p) for p in re.split(r"\n\s*\n|\n", text) if len(p.split()) >= 4]


def youtube_id(url: str) -> str | None:
    m = re.search(r"(?:youtu\.be/|v=|/shorts/|/live/|/embed/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


def _youtube_lines(vid: str, languages: list[str]) -> tuple[list[tuple[float | None, str]], dict]:
    from youtube_transcript_api import YouTubeTranscriptApi      # lazy: local use only
    api = YouTubeTranscriptApi()
    tl = api.list(vid)
    try:
        tr = tl.find_manually_created_transcript(languages)      # publisher captions beat auto-captions
    except Exception:
        tr = tl.find_generated_transcript(languages)
    fetched = tr.fetch()
    lines = [(float(s.start), s.text) for s in fetched]
    return lines, {"language": tr.language_code, "asr": bool(tr.is_generated)}


def fetch(src: str, out_dir: Path | None = None) -> dict:
    """Store a transcript locally from a YouTube link, a URL (HTML or PDF) or a local file (.txt .md .vtt .srt .pdf).
    Returns its metadata: path, sha12, source kind, asr flag, location kind, lines, extent."""
    out_dir = out_dir or TRANSCRIPTS
    c = cfg()
    meta = {"src": src, "fetched_utc": _now().isoformat(), "asr": False, "language": None}
    vid = youtube_id(src) if src.startswith("http") else None
    if vid:
        lines, extra = _youtube_lines(vid, c["languages"])
        meta.update(extra, source="youtube-captions" if extra["asr"] else "youtube-publisher-captions", kind="time")
    elif src.startswith("http"):
        import requests
        r = requests.get(src, timeout=60, headers={"User-Agent": "pm-agent-stack research digester (personal use)"})
        r.raise_for_status()
        if "pdf" in r.headers.get("content-type", "") or src.lower().endswith(".pdf"):
            lines, meta["kind"] = _pdf_lines(r.content), "page"
        else:
            lines, meta["kind"] = _html_lines(r.text), "none"
        meta["source"] = "web"
    else:
        p = Path(src)
        if p.suffix.lower() == ".pdf":
            lines, meta["kind"] = _pdf_lines(p.read_bytes()), "page"
        else:
            text = p.read_text(encoding="utf-8", errors="replace")
            if p.suffix.lower() in (".vtt", ".srt") or "-->" in text[:2000]:
                lines, meta["kind"] = _parse_vtt_srt(text), "time"
            else:
                lines, labels = [], []
                for raw in text.splitlines():
                    m = LINE_RE.match(raw.strip())
                    lines.append((parse_loc(m.group(1)), m.group(2)) if m else (None, raw))
                    if m:
                        labels.append(m.group(1))
                meta["kind"] = ("page" if labels and all(l[:1] in "pP" for l in labels) else
                                "time" if labels else "none")
        meta["source"] = "file"
    body = _norm_lines(lines, meta["kind"])
    sha = hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{sha}.txt"
    path.write_text(body, encoding="utf-8")
    locs = [l for l, _ in lines if l is not None]
    meta.update(sha12=sha, path=str(path), lines=body.count("\n"), words=len(body.split()),
                extent=fmt_loc(max(locs), meta["kind"]) if locs else None)
    path.with_suffix(".json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    return meta


def load_transcript(path: str | Path) -> dict:
    """{'lines': [(loc, text)], 'kind', 'asr', 'sha12', ...} from a stored transcript (or any text file)."""
    path = Path(path)
    if not path.exists() and re.fullmatch(r"[0-9a-f]{12}", str(path)):
        path = TRANSCRIPTS / f"{path}.txt"
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = []
    for raw in text.splitlines():
        m = LINE_RE.match(raw.strip())
        lines.append((parse_loc(m.group(1)), m.group(2)) if m else (None, raw))
    mpath = path.with_suffix(".json")
    meta = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {}
    kind = meta.get("kind") or ("page" if re.search(r"^\[[pP]\d+\]", text, re.M) else
                                "time" if any(l is not None for l, _ in lines) else "none")
    lang = str(meta.get("language") or detect_language(text)).lower()[:2]
    meta["language"] = lang
    return {**meta, "lines": lines, "kind": kind, "asr": bool(meta.get("asr")),
            "sha12": meta.get("sha12") or hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], "path": str(path)}


def chunks(tr: dict, minutes: float | None = None, pages: int = 3) -> list[dict]:
    """Extraction windows: ~10 minutes of speech (or 3 pages, or ~1,500 words when there are no locations)."""
    span = (minutes or cfg()["window_minutes"]) * 60 if tr["kind"] == "time" else pages
    out, cur, start = [], [], None
    words = 0
    for loc, text in tr["lines"]:
        if not text.strip():
            continue
        if start is None:
            start = loc
        new_window = (tr["kind"] != "none" and loc is not None and start is not None and loc - start >= span) or \
                     (tr["kind"] == "none" and words >= 1500)
        if new_window and cur:
            out.append({"i": len(out) + 1, "start": fmt_loc(start, tr["kind"]), "text": "\n".join(cur)})
            cur, start, words = [], loc, 0
        cur.append(f"[{fmt_loc(loc, tr['kind'])}] {text}" if loc is not None else text)
        words += len(text.split())
    if cur:
        out.append({"i": len(out) + 1, "start": fmt_loc(start, tr["kind"]), "text": "\n".join(cur)})
    for w, nxt in zip(out, out[1:] + [None]):
        w["end"] = nxt["start"] if nxt else "end"
    return out


# ------------------------------------------------------------------ text helpers
def _fold(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9%$]+", _fold(text or "").lower())


EN_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                       "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
EN_TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}
PT_UNITS = {"zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6,
            "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12, "treze": 13, "quatorze": 14,
            "catorze": 14, "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19}
PT_TENS = {"vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60, "setenta": 70,
           "oitenta": 80, "noventa": 90}
PT_HUND = {"cem": 100, "cento": 100, "duzentos": 200, "duzentas": 200, "trezentos": 300, "quatrocentos": 400,
           "quinhentos": 500, "seiscentos": 600, "setecentos": 700, "oitocentos": 800, "novecentos": 900}
SCALES = {"hundred": 100, "thousand": 1e3, "mil": 1e3, "million": 1e6, "milhao": 1e6, "milhoes": 1e6,
          "billion": 1e9, "bilhao": 1e9, "bilhoes": 1e9, "trillion": 1e12, "trilhao": 1e12, "trilhoes": 1e12}
SMALL = {**EN_UNITS, **EN_TENS, **PT_UNITS, **PT_TENS, **PT_HUND}


def _word_numbers(text: str) -> set[float]:
    """Numbers spoken as words (English and Portuguese): 'eighty five' 85, 'oitenta e cinco' 85,
    'one point five' 1.5, 'dois virgula cinco' 2.5, 'one point two five' 1.25. Only the full value of each
    spoken number counts: 'eighty five' is 85, not also 80 (review A11, finding 5)."""
    out: set[float] = set()
    for seg in re.split(r"[,;:!?()]|\.(?!\d)", text or ""):   # a spoken number never runs across punctuation
        out |= _word_numbers_seg(tokens(seg.replace("-", " ")))
    return out


UNITS = EN_UNITS | PT_UNITS


def _word_numbers_seg(toks: list[str]) -> set[float]:
    out: set[float] = set()
    i = 0
    while i < len(toks):
        if toks[i] not in SMALL and toks[i] not in SCALES:
            i += 1
            continue
        total, cur, j, frac = 0.0, 0.0, i, None
        while j < len(toks):
            t = toks[j]
            if t in SMALL:
                v = SMALL[t]
                # "cinco dois" is two numbers: a unit or teen after a unit or teen ends the first one
                if j > i and v < 100 and (cur % 10 or 10 <= cur % 100 < 20 or (v >= 10 and cur % 100)):
                    break
                cur += v
            elif t == "hundred":
                cur = (cur or 1) * 100
            elif t in SCALES:
                total += (cur or 1) * SCALES[t]
                cur = 0
            elif t in ("and", "e") and j + 1 < len(toks) and toks[j + 1] in SMALL:
                pass
            elif t in ("point", "virgula") and j + 1 < len(toks) and toks[j + 1] in UNITS and UNITS[toks[j + 1]] < 10:
                digits = []
                j += 1
                while j < len(toks) and toks[j] in UNITS and UNITS[toks[j]] < 10:
                    digits.append(str(UNITS[toks[j]]))
                    j += 1
                frac = "".join(digits)
                break
            else:
                break
            j += 1
        v = total + cur
        out.add(float(f"{int(v)}.{frac}") if frac else v)
        i = max(j, i + 1)
    return out


# digits glued to letters count too ("USD150"); a leading dot is a decimal (".5")
DIGIT_RE = re.compile(r"(?<![\d.,])(?:\d+(?:[.,]\d+)*|[.,]\d+)")
STRUCTURAL_RE = re.compile(r"\b(?:Q[1-4]|H[12]|[12]H|[1-4]Q|FY\d{2,4}|\d{1,2}(?:st|nd|rd|th))\b", re.I)


def _digit_candidates(s: str, lang: str = "any") -> set[float]:
    """Values of a written number under a language's convention. 'en': '1,500' 1500, '1.5' 1.5;
    'pt': '1.500' 1500, '1,5' 1.5; 'any' (unknown source) keeps both readings."""
    if s[0] in ".,":
        return {float("0." + s[1:])}
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        th = "." if dec == "," else ","
        return {float(s.replace(th, "").replace(dec, "."))}
    for sep in (",", "."):
        if sep in s:
            parts = s.split(sep)
            grouped = all(len(p) == 3 for p in parts[1:])
            thousands = float("".join(parts))
            decimal = float(parts[0] + "." + parts[1]) if len(parts) == 2 else None
            th_sep = {"en": ",", "pt": "."}.get(lang)
            if th_sep is None:
                return {x for x in (thousands if grouped else None, decimal) if x is not None} or {thousands}
            if sep == th_sep:
                return {thousands} if grouped or decimal is None else {decimal}
            return {decimal} if decimal is not None else {thousands}
    return {float(s)}


ISO_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def numbers_in(text: str, words: bool = True, lang: str = "any") -> set[float]:
    """Values of every number in a text. Quarter/half labels, ordinals, ISO dates and market names that
    contain digits (S&P 500) are structure, not figures. `words` adds spoken numbers (quotes only: a claim the
    model writes uses digits, in English convention)."""
    text = ISO_RE.sub(" ", STRUCTURAL_RE.sub(" ", text or ""))
    for m in cfg()["markets"].values():
        for n in [m["name"], *m.get("aliases", [])]:
            if re.search(r"\d", n):
                text = re.sub(rf"(?<!\w){re.escape(n)}(?!\w)", " ", text, flags=re.I)
    out: set[float] = set()
    for m in DIGIT_RE.finditer(text):
        try:
            out |= _digit_candidates(m.group(0), lang)
        except ValueError:
            pass
    return out | _word_numbers(text) if words else out


PCT_RE = re.compile(r"(?i)(%|\bper\s?cent\b|\bpercent\b|\bpor\s?cento\b|\bpct\b)")


def percents_in(text: str, lang: str = "any") -> set[float]:
    """Numbers stated as percentages ("60%", "sixty percent", "sessenta por cento"): the only form a stated
    probability may take (a level of 85 must not vouch for a probability of 0.85)."""
    out: set[float] = set()
    for m in PCT_RE.finditer(text or ""):
        before = text[:m.start()]
        words = re.split(r"\s+", before.strip())[-4:]
        seg = " ".join(words)
        digits = list(DIGIT_RE.finditer(seg))
        if digits and seg.rstrip().endswith(digits[-1].group(0)):
            out |= _digit_candidates(digits[-1].group(0), lang)
            continue
        wn = _word_numbers_seg(tokens(seg.replace("-", " ")))
        if wn:
            out.add(max(wn))
    return out


def _has_number(v: float, pool: set[float]) -> bool:
    return any(abs(v - p) <= max(1e-9, 1e-6 * abs(v)) for p in pool)


def _words_in(text: str, words: list[str]) -> list[str]:
    folded = " " + " ".join(tokens(text)) + " "
    return [w for w in words if f" {' '.join(tokens(w))} " in folded]


# Common words that may start a sentence: not names. Anything else capitalised is checked against the source,
# including the first word of a claim ("Citi: Brent could ..." - review A11, finding 6).
COMMON = set("""a an the this that these those there their they he she it its we our you your i if in on at by for
from to of as and but or so then when while with without after before since until during over under about above
below between into onto per via also both each every all any some most more less many much few no not none one
two three four five six seven eight nine ten first second third last next new old high low higher lower up down
oil prices price demand supply stocks inventories rates yields inflation growth markets market spot futures crude
gas gold copper silver corn wheat soybeans sugar coffee dollar equities bonds alternatives private public global
global hedge funds fund managers manager platform platforms specialisation specialization ai agents agent future
competition portfolio partnerships partnership three desks between according by year end q1 q2 q3 q4 about around
it's he's she's they're we're there's what why how who where which will would could should may might can must
expect expects expected sees see says said think thinks thought believes argues argued notes noted rising falling
cuts cut hikes hike risk risks recession production exports imports refinery refiners margins spreads curve
in his her their its""".split())


def proper_terms(text: str) -> list[str]:
    """Acronyms and capitalised words that could be names a paraphrase imported. A capitalised word at the
    start of a sentence counts unless it is a common word."""
    out = []
    for m in re.finditer(r"\b([A-Z][A-Za-z&]*[A-Z][A-Za-z&]*|[A-Z][a-z]{2,})\b", text or ""):
        w = m.group(1)
        before = text[:m.start()].rstrip()
        initial = not before or before[-1] in ".!?:;\"'(" or before.endswith("\n")
        if w.isupper() or not initial or w.lower() not in COMMON:
            out.append(w)
    return out


# ------------------------------------------------------------------ quote anchoring
def detect_language(text: str) -> str:
    t = tokens(text[:20000])
    pt = sum(x in {"que", "nao", "uma", "para", "com", "voce", "isso", "mas", "tambem", "muito", "gente", "porque",
                   "esta", "sao", "pra", "entao"} for x in t)
    en = sum(x in {"the", "and", "that", "is", "to", "of", "you", "it", "we", "this", "with", "for", "are", "was"} for x in t)
    return "pt" if pt > en else "en"


def match_tokens(text: str, fillers: set[str] | None = None) -> list[str]:
    """Tokens for quote matching: filler words ("eh", "né") and immediate repeats ("uma uma") are speech noise,
    not content, so they never count against a quote (own test set, 16 Oct: 2 of 6 filler-cleaned quotes were
    rejected at 0.85 while one-name swaps passed at 0.89-0.96)."""
    fillers = fillers if fillers is not None else set(cfg().get("fillers") or [])
    out: list[str] = []
    for t in tokens(text):
        if t in fillers or (out and out[-1] == t):
            continue
        out.append(t)
    return out


def _index(tr: dict) -> dict:
    if "_idx" in tr:
        return tr["_idx"]
    fillers = set(cfg().get("fillers") or [])
    toks, locs, line_of, sent = [], [], [], []
    sid = 0
    for n, (loc, text) in enumerate(tr["lines"]):
        for k, piece in enumerate(re.split(r"(?<=[.!?])\s+", text or "")):
            if k:
                sid += 1                          # a sentence end inside the line
            t = match_tokens(piece, fillers)
            if toks and t and t[0] == toks[-1]:  # a repeat across a caption line break
                t = t[1:]
            toks += t
            locs += [loc] * len(t)
            line_of += [n] * len(t)
            sent += [sid] * len(t)
        if re.search(r"[.!?]\s*$", text or ""):
            sid += 1
    joined, starts, pos = [], [], 0
    for t in toks:
        starts.append(pos)
        joined.append(t)
        pos += len(t) + 1
    tr["_idx"] = {"toks": toks, "locs": locs, "line_of": line_of, "sent": sent, "joined": " ".join(joined), "starts": starts,
                  "raw": "\n".join(t for _, t in tr["lines"])}
    return tr["_idx"]


def in_source(term: str, tr: dict) -> bool:
    """Is a name or acronym in the transcript? Acronyms, and capitalised words that are also common words
    ("Will"), match case-sensitively on the raw text ("AI" is not the Portuguese "aí"); other words match on
    folded tokens."""
    ix = _index(tr)
    if term.isupper() or term.lower() in COMMON:
        return re.search(rf"(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])", ix["raw"]) is not None
    return f" {' '.join(tokens(term))} " in " " + ix["joined"] + " "


def find_quote(quote: str, tr: dict, hint: float | None = None) -> dict:
    """Where (if anywhere) the quote sits in the transcript: exact token match first, then the best
    token-level similarity, near the card's own time first and over the whole transcript second.
    Returns the matched span (token indices) so the checks can read the transcript's own words."""
    import bisect
    c = cfg()
    ix = _index(tr)
    q = match_tokens(quote)
    if not q or not ix["toks"]:
        return {"found": False, "ratio": 0.0, "loc": None, "start": None, "end": None}
    qs = " ".join(q)
    at = ix["joined"].find(qs)
    hits = []
    while at >= 0:
        if at == 0 or ix["joined"][at - 1] == " ":
            hits.append(bisect.bisect_left(ix["starts"], at))
        at = ix["joined"].find(qs, at + 1)
    if hits:
        i = min(hits, key=lambda k: abs((ix["locs"][k] or 0) - hint) if hint is not None and ix["locs"][k] is not None else 0)
        return {"found": True, "ratio": 1.0, "loc": ix["locs"][i], "start": i, "end": i + len(q)}
    qset, n = set(q), len(q)
    win = c["search_window_s"] if tr["kind"] == "time" else 1

    def best(cands):
        b = (0.0, None)
        for i in cands:
            if ix["toks"][i] not in qset:
                continue
            w = ix["toks"][i:i + n]
            if len(qset & set(w)) < 0.5 * len(qset):
                continue
            r = SequenceMatcher(None, q, w, autojunk=False).ratio()
            if r > b[0]:
                b = (r, i)
        return b

    near = range(len(ix["toks"]))
    if hint is not None and tr["kind"] != "none":
        near = [i for i, l in enumerate(ix["locs"]) if l is not None and abs(l - hint) <= win]
    r, i = best(near)
    if r < c["quote_min_ratio"] and hint is not None:
        r, i = max((r, i), best(range(len(ix["toks"]))), key=lambda x: x[0])
    return {"found": r >= c["quote_min_ratio"], "ratio": round(r, 3), "loc": ix["locs"][i] if i is not None else None,
            "start": i, "end": None if i is None else min(len(ix["toks"]), i + n)}


NEGATIONS = {"not", "no", "never", "nor", "t", "dont", "doesnt", "didnt", "wont", "cant", "cannot", "isnt", "arent",
             "wasnt", "nothing", "without", "nao", "nunca", "nem", "sem", "nada", "jamais"}


def quote_diff(quote: str, tr: dict, fq: dict) -> dict:
    """How a fuzzy-matched quote differs from the transcript (fillers and repeats already ignored):
      altered  - differences that change what was said: a number, negation or hedge anywhere in a changed
                 block (review A11, finding 1), a word the quote ADDS, or a word REPLACED by a different word
                 (own test set, 16 Oct: all six one-name swaps - Miami -> Londres, Canadá -> México - passed
                 the 0.85 ratio at 0.89-0.96, so no threshold separates them from filler-only edits);
      spelling - replacements that differ only in spelling (character similarity >= asr_spelling_min_ratio:
                 OKR/KKR, head/hedge, Antropic/Anthropic): captions misspell names, shown but not blocking;
      omitted  - transcript words the quote leaves out (fine unless sensitive, which counts as altered)."""
    out = {"altered": [], "spelling": [], "omitted": []}
    if not fq.get("found") or fq.get("ratio") == 1.0 or fq.get("start") is None:
        return out
    c = cfg()
    ix = _index(tr)
    q = match_tokens(quote)
    # a quote that leaves words out spans more transcript than its own length: read a little further, then drop
    # the transcript words after the quote's last word
    span = ix["toks"][fq["start"]:fq["start"] + len(q) + max(3, len(q) // 3)]
    hedges = {t for w in list(c["hedge_lexicon"]) + list(c["hedge_required"]) for t in tokens(w)}
    quals = {t for w in c.get("quote_sensitive_words") or [] for t in tokens(w)}
    sensitive = lambda t: bool(re.search(r"\d", t)) or t in SMALL or t in SCALES or t in ("point", "virgula") \
        or t in NEGATIONS or t in hedges or t in quals
    spell_min = float(c.get("asr_spelling_min_ratio", 0.65))
    ops = SequenceMatcher(None, q, span, autojunk=False).get_opcodes()
    while ops and ops[-1][0] == "insert":
        ops.pop()
    for n_op, (op, a0, a1, b0, b1) in enumerate(ops):
        if op == "equal":
            continue
        qa, sb = q[a0:a1], span[b0:b1]
        if op == "replace" and n_op == len(ops) - 1 and len(sb) > len(qa):
            sb = sb[:len(qa)]                     # the over-read tail is not part of the quote's last word
        sens = [t for t in qa + sb if sensitive(t)]
        if sens:
            out["altered"] += sens
        elif op == "delete":                      # the quote has words the speaker did not say here
            out["altered"] += qa
        elif op == "insert":
            out["omitted"] += sb
        elif SequenceMatcher(None, "".join(qa), "".join(sb), autojunk=False).ratio() >= spell_min \
                and not _opposite("".join(qa), "".join(sb), c):
            out["spelling"].append(f"{' '.join(qa)}/{' '.join(sb)}")
        else:
            out["altered"] += qa + sb
    return {k: sorted(set(v)) for k, v in out.items()}


def _opposite(a: str, b: str, c: dict) -> bool:
    """Two words that differ by a negating prefix are opposites, not spellings: possible/impossible,
    correlacionada/descorrelacionada, inflation/deflation (review A12, finding 5)."""
    i = 0
    while i < min(len(a), len(b)) and a[-1 - i] == b[-1 - i]:
        i += 1
    pa, pb = a[:len(a) - i], b[:len(b) - i]
    if pa == pb or i < 3:
        return False
    neg = set(c.get("opposite_prefixes") or [])
    return pa in neg or pb in neg


def altered_words(quote: str, tr: dict, fq: dict) -> list[str]:
    """Words where a fuzzy-matched quote differs from the transcript in a way that changes what was said."""
    return quote_diff(quote, tr, fq)["altered"]


def hedge_before(tr: dict, fq: dict) -> list[str]:
    """Lead-in hedges ("eu acho que", "I think", "talvez") in the words just before the matched span, within the
    same sentence: a quote cut so it starts after the hedge still matches but loses it (Peters & Chin-Yee:
    hedges are what summaries drop; own test set, 16 Oct; same-sentence limit: review A12, finding 8)."""
    c = cfg()
    if not fq.get("found") or fq.get("start") is None:
        return []
    ix = _index(tr)
    n, st = int(c.get("hedge_lead_tokens", 12)), fq["start"]
    lo = max(0, st - n)
    if ix.get("sent"):
        while lo < st and ix["sent"][lo] != ix["sent"][st]:
            lo += 1
    before = " " + " ".join(ix["toks"][lo:st]) + " "
    return [h for h in c.get("hedge_lead_in") or [] if f" {' '.join(tokens(h))} " in before]


def _hedge_kept(h: str, text: str) -> bool:
    """A lead-in hedge is kept when its core words are in the card ("acho que" covers "eu acho")."""
    core = [t for t in tokens(h) if t not in ("eu", "que", "i")] or tokens(h)
    have = set(tokens(text))
    return all(t in have for t in core)


# ------------------------------------------------------------------ prices (research memory)
def _series(ref: str, until: str | None = None) -> pd.DataFrame | None:
    try:
        q = "SELECT date, value, source_url FROM obs WHERE series_id = ?" + (" AND date <= ?" if until else "") + " ORDER BY date"
        df = store.connect().execute(q, [ref, until] if until else [ref]).df()
    except Exception:
        return None
    if not len(df):
        return None
    df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
    return df


def close_on(ref: str, day: str, lookback_days: int | None = None) -> dict | None:
    """Last stored close on or before `day` (within the lookback), with its date and source link."""
    lb = lookback_days if lookback_days is not None else cfg()["level_lookback_days"]
    df = _series(ref, day)
    if df is None:
        return None
    row = df.iloc[-1]
    if (date.fromisoformat(day) - date.fromisoformat(row["date"])).days > lb:
        return None
    return {"value": round(float(row["value"]), 4), "date": row["date"], "source_url": row["source_url"]}


# ------------------------------------------------------------------ card checks
def _no_month(text: str) -> str:
    """The month "May" is not the hedge "may" (review A11, finding 12)."""
    return re.sub(r"\bMay\b", " ", text or "")


def _no_hedge_phrases(text: str) -> str:
    """Phrases where a hedge word is not a hedge ("no caso de" = "in the case of")."""
    t = " " + " ".join(tokens(text)) + " "
    for ph in cfg().get("hedge_not") or []:
        t = t.replace(f" {' '.join(tokens(ph))} ", " ")
    return t


def hedge_prob(quote: str) -> tuple[float | None, str | None]:
    lex = cfg()["hedge_lexicon"]
    found = _words_in(_no_hedge_phrases(_no_month(quote)), list(lex))
    if not found:
        return None, None
    w = min(found, key=lambda k: (abs(lex[k] - 0.5), -len(k)))
    return lex[w], w


TIME_RE = re.compile(r"(?i)\b((19|20)\d\d|jan\w*|feb\w*|fev\w*|mar\w*|apr\w*|abr\w*|may|mai\w*|jun\w*|jul\w*|aug\w*|"
                     r"ago\w*|sep\w*|set\w*|oct\w*|out\w*|nov\w*|dec\w*|dez\w*|quarter|trimestre|semestre|year|"
                     r"ano|month|m[eê]s|week|semana|end|fim|final|next|pr[oó]xim\w*|until|at[eé]|by|days?|dias?|q[1-4]|"
                     r"h[12]|summer|winter|ver[aã]o|inverno|today|tomorrow|amanh[aã]|hoje)\b")


def check_card(card: dict, tr: dict, as_of: str, today: str | None = None) -> dict:
    """One card -> the card with `status` (ok / flagged / rejected) and `problems` [{code, detail, blocking}]."""
    c = cfg()
    today = today or _today_brt()
    k = dict(card)
    probs = []

    def bad(code, detail, blocking=None):
        probs.append({"code": code, "detail": detail, "blocking": code in BLOCKING if blocking is None else blocking})

    quote, claim = str(k.get("quote") or ""), str(k.get("claim") or "")
    for f in ("speaker", "quote", "claim", "type"):
        if not k.get(f):
            bad("missing_field", f)
    if k.get("type") not in CARD_TYPES:
        bad("bad_type", f"type must be one of {CARD_TYPES}")
    if len(quote.split()) > c["quote_max_words"]:
        bad("quote_too_long", f"{len(quote.split())} words > {c['quote_max_words']}: keep the shortest exact span")
    # 1. the quote is in the transcript, near the stated time
    hint = parse_loc(k.get("t"))
    fq = find_quote(quote, tr, hint)
    k["quote_match"] = fq["ratio"]
    if quote and not fq["found"]:
        bad("quote_not_found", f"best match {fq['ratio']:.2f} < {c['quote_min_ratio']}")
    elif quote and hint is not None and fq["loc"] is not None:
        tol = c["timestamp_tolerance_s"] if tr["kind"] == "time" else 1
        if abs(fq["loc"] - hint) > tol:
            bad("location_off", f"quote found at {fmt_loc(fq['loc'], tr['kind'])}, card says {k.get('t')}", False)
            k["t"] = fmt_loc(fq["loc"], tr["kind"])
    if fq["found"] and hint is None and fq["loc"] is not None:
        k["t"] = fmt_loc(fq["loc"], tr["kind"])
    # 1b. a near-match may not change a number, a negation or a hedge: the quote must say what the source said
    qd = quote_diff(quote, tr, fq)
    if qd["altered"]:
        bad("quote_altered", f"the quote differs from the transcript on {qd['altered']}: copy the exact words")
    if qd["spelling"]:
        bad("quote_spelling", f"spelling differs from the transcript ({', '.join(qd['spelling'])}): keep the "
            "transcript's words in the quote and put the correction in the claim with [ASR?]", False)
    # 2. every number on the card is inside its quote (claims in English convention; the quote in the source's)
    lang = tr.get("language") or "any"
    qnums = numbers_in(quote, lang=lang)
    for v in sorted(numbers_in(claim, words=False, lang="en") - {0.0}):
        if not _has_number(v, qnums):
            bad("number_not_in_quote", f"{v:g} is in the claim but not in the quote")
    lvl = _num(k.get("level"))
    if lvl is not None and not _has_number(lvl, qnums):
        bad("number_not_in_quote", f"level {lvl:g} is not in the quote")
    # a probability on the card is the speaker's own, stated as a percentage in the quote; code alone maps
    # hedges (a card cannot label its own number "inferred": review A11, finding 4)
    p = _num(k.get("probability"))
    k.pop("prob_source", None)
    if p is not None:
        k["prob_source"] = "stated"
        if not _has_number(round(100 * p, 6), percents_in(quote, lang)):
            bad("prob_not_in_quote", f"stated probability {p:g} is not in the quote as a percentage")
    # 3. nothing imported: names and acronyms in the claim appear somewhere in the source
    known = {t for m in c["markets"].values() for n in [m["name"], *m.get("aliases", [])] for t in tokens(n)}
    translated = str(tr.get("language") or "").lower().startswith("pt")   # from the source, never the card
    for w in sorted(set(proper_terms(claim))):
        if not in_source(w, tr) and not set(tokens(w)) <= known:
            if translated:   # a translated claim may name things differently: shown, not blocking
                bad("extrinsic_term_translated", f"'{w}' is not in the (other-language) transcript: check it", False)
            else:
                bad("extrinsic_term", f"'{w}' is not in the transcript")
    # 4. hedges survive ("no caso de" = "in the case of" is not the hedge "caso": own test set, 16 Oct)
    need = _words_in(_no_hedge_phrases(_no_month(quote)), c["hedge_required"])
    kept = " ".join(k.get("hedge") or []) if isinstance(k.get("hedge"), list) else str(k.get("hedge") or "")
    lost = [w for w in need if w not in _words_in(kept + " " + claim, need)]
    if lost:
        bad("hedge_dropped", f"quote hedges {lost} missing from the card's hedge words or claim")
    cut = [h for h in hedge_before(tr, fq) if not _hedge_kept(h, kept + " " + claim + " " + quote)]
    if cut:
        bad("hedge_cut", f"the words just before the quote say {cut}: start the quote at the hedge, or keep it in "
            "the card's hedge words")
    # 5. markets and the call
    markets = k.get("markets") or []
    if isinstance(markets, str):
        markets = [markets]
    k["markets"] = markets
    unknown = [m for m in markets if m not in c["markets"]]
    if unknown:
        bad("unknown_market", f"{unknown} not in config/digest.yaml markets (themes go in `themes`)")
    if markets and not unknown:
        k["price_ref"] = markets[0]
        k["name"] = ", ".join(c["markets"][m]["name"] for m in markets)
    if k.get("direction") not in (None, *DIRECTIONS):
        bad("missing_field", f"direction must be one of {DIRECTIONS}")
    if k.get("deadline"):
        try:
            dl = date.fromisoformat(str(k["deadline"]))
            if dl <= date.fromisoformat(as_of):
                bad("bad_deadline", f"deadline {k['deadline']} is not after the recording date {as_of}")
            elif dl > date.fromisoformat(as_of) + timedelta(days=3653):
                bad("bad_deadline", f"deadline {k['deadline']} is more than 10 years out")
            elif not TIME_RE.search(quote + " " + str(k.get("deadline_basis") or "")):
                bad("deadline_unsupported", "no time phrase in the quote or deadline_basis: say where the deadline "
                    "comes from", False)
        except ValueError:
            bad("bad_deadline", f"deadline {k['deadline']} is not YYYY-MM-DD")
    if k.get("type") == "forecast":
        if p is None:
            hp, hw = hedge_prob(quote)
            if hp is not None:
                k["probability"], k["prob_source"] = hp, f"hedge '{hw}' (inference)"
        k["scoreable"] = bool(markets and not unknown and k.get("deadline") and (k.get("direction") or lvl is not None)
                              and not any(x["code"] == "bad_deadline" for x in probs))
        if not k["scoreable"]:
            bad("unscoreable", "a forecast needs a known market, a deadline and a direction or level", False)
    # 6. data cards: a stated level vs the stored close on the recording date
    if k.get("type") == "data" and lvl is not None and markets and not unknown:
        st = close_on(markets[0], as_of)
        if st:
            diff = 100 * (lvl / st["value"] - 1) if st["value"] else None
            k["stored"] = {**st, "diff_pct": round(diff, 1) if diff is not None else None}
            if diff is not None and abs(diff) > c["level_tolerance_pct"]:
                bad("level_differs", f"speaker said {lvl:g}; stored {st['value']:g} on {st['date']} ({diff:+.1f}%): "
                    "check the contract, unit or date", False)
    # names the captions produced (in the transcript) are the ones auto-captions get wrong: 36-52% entity WER
    # (Earnings-21); names not in the transcript at all are already "extrinsic" above
    names = sorted({w for w in proper_terms(claim) if not set(tokens(w)) <= known and in_source(w, tr)})
    if tr.get("asr") and names:
        bad("asr_names", f"auto-captions: confirm {', '.join(names)} [ASR?]", False)
    k["as_of"] = as_of
    # the auditor binds a note's figure to the card whose words it shares (not to the series name)
    k["audit_subject"] = f"{k.get('name') or ''} {claim}".strip()
    k["problems"] = probs
    k["status"] = ("rejected" if any(x["code"] in ("quote_not_found", "missing_field", "bad_type") for x in probs)
                   else "flagged" if any(x["blocking"] for x in probs) else "ok")
    return k


def coverage(cards: list[dict], tr: dict) -> list[dict]:
    """Extraction windows that produced no card (omissions are the commonest failure: FABLES)."""
    wins = chunks(tr)
    if tr["kind"] == "none":
        return []
    starts = [parse_loc(w["start"]) for w in wins]
    used = set()
    for k in cards:
        loc = parse_loc(k.get("t"))
        if loc is None or k.get("status") == "rejected":
            continue
        i = max((j for j, s in enumerate(starts) if s is not None and s <= loc), default=0)
        used.add(i)
    return [{"window": w["i"], "start": w["start"], "end": w["end"]} for j, w in enumerate(wins) if j not in used]


def sparse_windows(cards: list[dict], tr: dict) -> list[dict]:
    """Windows with fewer cards than `min_cards_per_1k_words` per 1,000 words. One card per window hid most of
    the omissions: the 15 Oct digest kept 14 claims (3.3 per 1,000 words) where two blind re-digests kept 57
    and 59 (13-14 per 1,000), and every window had a card (own test set, 16 Oct)."""
    floor = cfg().get("min_cards_per_1k_words")
    if not floor:
        return []
    if tr["kind"] == "none":                     # no locations: cards cannot be placed in windows
        words = sum(len(str(t).split()) for _, t in tr["lines"])
        n = sum(1 for k in cards if k.get("status") != "rejected")
        need = floor * words / 1000
        return [{"window": "all", "start": None, "end": None, "cards": n, "words": words,
                 "expected_at_least": math.floor(need)}] if words >= 200 and n < need else []
    wins = chunks(tr)
    starts = [parse_loc(w["start"]) for w in wins]
    n = [0] * len(wins)
    for k in cards:
        loc = parse_loc(k.get("t"))
        if loc is None or k.get("status") == "rejected" or tr["kind"] == "none":
            continue
        n[max((j for j, s in enumerate(starts) if s is not None and s <= loc), default=0)] += 1
    out = []
    for j, w in enumerate(wins):
        words = len(re.sub(r"\[[^\]]*\]", " ", w["text"]).split())
        need = floor * words / 1000
        if words >= 200 and n[j] < need:
            out.append({"window": w["i"], "start": w["start"], "end": w["end"], "cards": n[j], "words": words,
                        "expected_at_least": math.floor(need)})
    return out


# ------------------------------------------------------------------ notes
def read_note(path: str | Path) -> dict:
    path = Path(path)
    txt = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", txt, re.S)
    if not m:
        raise SystemExit(f"{path}: no YAML header")
    meta = yaml.safe_load(m.group(1)) or {}
    meta["_body"], meta["_path"] = m.group(2), path
    return meta


def note_key(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(NOTES.resolve().parent).as_posix()
    except ValueError:
        return Path(path).as_posix()


def _write_header(path: Path, meta: dict):
    body = meta.get("_body", "")
    clean = {k: v for k, v in meta.items() if not k.startswith("_")}
    front = yaml.safe_dump(clean, sort_keys=False, allow_unicode=True, width=110)
    path.write_text(f"---\n{front}---\n{body}", encoding="utf-8")


def note_date(meta: dict) -> str:
    d = meta.get("date")
    try:
        return date.fromisoformat(str(d)).isoformat()
    except (TypeError, ValueError):
        raise SystemExit("the note header needs date: YYYY-MM-DD (recording or publication date = as-of)")


def check(note: str | Path, cards: list[dict], transcript: str | Path, today: str | None = None) -> dict:
    meta = read_note(note)
    as_of = note_date(meta)
    today = today or _today_brt()
    if as_of > today:
        raise SystemExit(f"note date {as_of} is after today {today}")
    tr = load_transcript(transcript)
    out = []
    for n, card in enumerate(cards, 1):
        k = check_card(card, tr, as_of, today)
        k["id"] = f"{Path(note).stem}#c{n}"
        out.append(k)
    cov = coverage(out, tr)
    sparse = sparse_windows(out, tr)
    stat = {s: sum(1 for k in out if k["status"] == s) for s in ("ok", "flagged", "rejected")}
    avail = str(meta.get("published") or as_of)[:10]
    if avail < as_of:
        raise SystemExit(f"published {avail} is before the recording date {as_of}")
    return {"note": note_key(Path(note)), "as_of": as_of, "available": avail, "series": meta.get("series"),
            "asr_speakers": sorted({str(k.get("speaker")) for k in out}) if tr["asr"] else [],
            "title": meta.get("episode") or meta.get("title"), "url": meta.get("url"), "type": meta.get("type"),
            "transcript": {"sha12": tr["sha12"], "source": tr.get("source"), "asr": tr["asr"], "kind": tr["kind"]},
            "checked_utc": _now().isoformat(), "counts": stat, "uncovered_windows": cov, "sparse_windows": sparse,
            "cards": out}


def save(note: str | Path, cards: list[dict], transcript: str | Path, today: str | None = None) -> dict:
    """Check the cards, write <note>.cards.json and the note header's `digest:` block, log the run."""
    note = Path(note)
    rep = check(note, cards, transcript, today)
    note.with_suffix(".cards.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    meta = read_note(note)
    meta["transcript_sha12"] = rep["transcript"]["sha12"]
    meta["digest"] = {"cards": len(rep["cards"]), **rep["counts"],
                      "forecasts_scoreable": sum(1 for k in rep["cards"] if k.get("scoreable") and k["status"] == "ok"),
                      "uncovered_windows": len(rep["uncovered_windows"]), "sparse_windows": len(rep["sparse_windows"]),
                      "asr": rep["transcript"]["asr"],
                      "checked_utc": rep["checked_utc"]}
    _write_header(note, meta)
    runlog.log(runlog.new_run_id(), "digest:save", "ok" if not rep["counts"]["flagged"] + rep["counts"]["rejected"] else "partial",
               note=rep["note"], as_of=rep["as_of"], **rep["counts"], uncovered=len(rep["uncovered_windows"]),
               transcript=rep["transcript"]["sha12"])
    return rep


def load_cards(asof: str | None = None, status: str | None = "ok", root: Path | None = None) -> list[dict]:
    """All saved cards (default: ok only) recorded on or before `asof` (no look-ahead)."""
    root = root or NOTES
    out = []
    for p in sorted(root.rglob("*.cards.json")):
        try:
            rep = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"skip {p}: {e}", file=sys.stderr)
            continue
        # usable from publication (review A11, finding 20): an episode recorded before an idea but
        # published after it must not reach that idea's critic card
        if asof and (rep.get("available") or rep.get("as_of", "9999")) > asof:
            continue
        for k in rep.get("cards", []):
            if status and k.get("status") != status:
                continue
            out.append({**k, "note": rep.get("note"), "series": rep.get("series"), "title": rep.get("title"),
                        "url": rep.get("url"), "available": rep.get("available") or rep.get("as_of")})
    return out


# ------------------------------------------------------------------ code facts for a note
def facts(note: str | Path, asof: str | None = None) -> dict:
    """Moves since the recording date and in the 5 sessions before it, per market on the note's cards:
    the only numbers about markets the note may add to what speakers said (all from stored data)."""
    note = Path(note)
    meta = read_note(note)
    as_of = note_date(meta)
    asof = asof or _today_brt()
    cp = note.with_suffix(".cards.json")
    try:
        cards = json.loads(cp.read_text(encoding="utf-8"))["cards"] if cp.exists() else []
    except (ValueError, KeyError) as e:
        raise SystemExit(f"{cp}: unreadable cards file ({e}); re-run digest save")
    refs = []
    for k in cards:
        if k.get("status") == "ok":
            refs += [m for m in k.get("markets", []) if m not in refs]
    refs += [a for a in (meta.get("assets") or []) if a in cfg()["markets"] and a not in refs]
    out = {"note": note_key(note), "as_of": as_of, "computed_for": asof, "markets": []}
    for ref in refs:
        df = _series(ref, asof)
        if df is None:
            continue
        rec = df[df["date"] <= as_of]
        if not len(rec):
            continue
        r0 = rec.iloc[-1]
        row = {"price_ref": ref, "name": cfg()["markets"][ref]["name"], "recording_close": round(float(r0["value"]), 4),
               "recording_close_date": r0["date"], "last": round(float(df["value"].iloc[-1]), 4),
               "last_date": df["date"].iloc[-1], "source_url": df["source_url"].iloc[-1]}
        row["since_recording_pct"] = round(100 * (row["last"] / row["recording_close"] - 1), 2) if row["recording_close"] else None
        row["trading_days_since"] = int((df["date"] > r0["date"]).sum())
        if len(rec) > 5:
            row["pre_5d_pct"] = round(100 * (float(rec["value"].iloc[-1]) / float(rec["value"].iloc[-6]) - 1), 2)
        out["markets"].append(row)
    for k in cards:
        lvl = _num(k.get("level"))
        if k.get("status") == "ok" and k.get("type") == "forecast" and lvl and k.get("price_ref"):
            m = next((r for r in out["markets"] if r["price_ref"] == k["price_ref"]), None)
            if m and m["last"]:
                m.setdefault("to_levels", []).append({"card": k["id"], "level": lvl,
                                                      "distance_pct": round(100 * (lvl / m["last"] - 1), 2)})
    return out


# ------------------------------------------------------------------ call ledger
def resolve(k: dict, asof: str) -> dict:
    """Score one forecast card on stored closes up to `asof` (never later): open, hit, miss, unscoreable, no-data,
    pending-data. A call resolves the day after its deadline (the deadline close is known only then), and only
    if the store has a close within `level_lookback_days` of the deadline: stale data never scores a call
    (review A11, finding 3).
    Direction calls: sign of the move from the recording close to the deadline close; "flat" = within
    flat_band_pct, with or without a level (finding 13).
    Level calls: `level_kind` close (on the right side at the deadline, default) or touch (reached on any close).
    Level calls also say whether they beat the no-change forecast (|end - level| < |end - start|)."""
    c = cfg()
    base = {"card": k.get("id"), "speaker": k.get("speaker"), "price_ref": k.get("price_ref"), "as_of": k.get("as_of"),
            "deadline": k.get("deadline"), "claim": k.get("claim"), "note": k.get("note"),
            "probability": _num(k.get("probability")), "prob_source": k.get("prob_source")}
    if k.get("type") != "forecast" or not k.get("scoreable"):
        return {**base, "status": "unscoreable"}
    ref, a, dl = k["price_ref"], k["as_of"], str(k["deadline"])
    end_day = min(dl, asof)
    df = _series(ref, end_day)
    if df is None or not len(df[df["date"] <= a]):
        return {**base, "status": "no-data"}
    start = df[df["date"] <= a].iloc[-1]
    path = df[df["date"] > start["date"]]
    s0 = float(start["value"])
    base.update(start=round(s0, 4), start_date=start["date"], source_url=start["source_url"])
    lvl = _num(k.get("level"))
    d = k.get("direction") or ((("up" if lvl > s0 else "down") if lvl != s0 else "flat") if lvl is not None else None)
    if dl >= asof:
        if len(path):
            base.update(last=round(float(path["value"].iloc[-1]), 4), last_date=path["date"].iloc[-1],
                        move_pct=round(100 * (float(path["value"].iloc[-1]) / s0 - 1), 2))
        return {**base, "status": "open"}
    if not len(path):
        return {**base, "status": "no-data"}
    if (date.fromisoformat(dl) - date.fromisoformat(path["date"].iloc[-1])).days > c["level_lookback_days"]:
        return {**base, "status": "pending-data", "last_date": path["date"].iloc[-1]}
    e = float(path["value"].iloc[-1])
    ret = 100 * (e / s0 - 1)
    base.update(end=round(e, 4), end_date=path["date"].iloc[-1], move_pct=round(ret, 2))
    if d == "flat":
        hit = abs(ret) < c["flat_band_pct"]
        if lvl is not None:
            base["beat_no_change"] = bool(abs(e - lvl) < abs(e - s0))
    elif lvl is not None:
        if (k.get("level_kind") or "close") == "touch":
            hit = (path["value"].max() >= lvl) if d == "up" else (path["value"].min() <= lvl)
        else:
            hit = e >= lvl if d == "up" else e <= lvl
        base["beat_no_change"] = bool(abs(e - lvl) < abs(e - s0))
    else:
        hit = (ret > 0) if d == "up" else (ret < 0)
    hit = bool(hit)
    p = base["probability"]
    if p is not None:
        base["brier"] = round((p - (1.0 if hit else 0.0)) ** 2, 4)
    return {**base, "status": "hit" if hit else "miss"}


def _wilson(x: int, n: int, z: float = 1.959964):
    if n == 0:
        return None
    p = x / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return round(100 * (mid - half), 1), round(100 * (mid + half), 1)


def speaker_key(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\(.*?\)", " ", _fold(str(s or "")))).strip().lower()


def records(scored: list[dict]) -> dict:
    """Per speaker: resolved calls, hits, Wilson 95% interval, mean Brier, share beating no-change.
    `enough` only from record_min_calls; before that the base rate is the prior."""
    c = cfg()
    out: dict[str, dict] = {}
    for r in scored:
        if r["status"] not in ("hit", "miss", "open"):
            continue
        s = out.setdefault(speaker_key(r["speaker"]), {"speaker": r["speaker"], "resolved": 0, "hits": 0, "open": 0,
                                                       "briers": [], "beat": []})
        if r["status"] == "open":
            s["open"] += 1
            continue
        s["resolved"] += 1
        s["hits"] += r["status"] == "hit"
        if r.get("brier") is not None:
            s["briers"].append(r["brier"])
        if r.get("beat_no_change") is not None:
            s["beat"].append(r["beat_no_change"])
    for s in out.values():
        n = s["resolved"]
        s["hit_rate_pct"] = round(100 * s["hits"] / n, 1) if n else None
        s["wilson_pct"] = _wilson(s["hits"], n)
        s["mean_brier"] = round(sum(s["briers"]) / len(s["briers"]), 3) if s["briers"] else None
        s["beat_no_change_pct"] = round(100 * sum(s["beat"]) / len(s["beat"]), 1) if s["beat"] else None
        s["enough"] = n >= c["record_min_calls"]
        s.pop("briers"), s.pop("beat")
    return out


def calls(asof: str | None = None, window_days: int = 7) -> dict:
    """The ledger as of a date: every scoreable forecast resolved on data up to that date, what resolved in the
    last `window_days`, what falls due in the next `window_days`, and speaker records."""
    asof = asof or _today_brt()
    cards = [k for k in load_cards(asof) if k.get("type") == "forecast"]
    scored = [resolve(k, asof) for k in cards]
    d0 = date.fromisoformat(asof)
    recent = [r for r in scored if r["status"] in ("hit", "miss")
              and d0 - timedelta(days=window_days) < date.fromisoformat(r["deadline"]) <= d0]
    due = [r for r in scored if r["status"] == "open" and date.fromisoformat(r["deadline"]) <= d0 + timedelta(days=window_days)]
    c = cfg()
    return {"asof": asof, "n_forecasts": len(scored),
            "counts": {s: sum(1 for r in scored if r["status"] == s)
                       for s in ("open", "hit", "miss", "pending-data", "unscoreable", "no-data")},
            "resolved_recently": recent, "due_soon": due, "records": records(scored),
            "prior": {"guest_base_rate_pct": c["guest_base_rate_pct"], "source": c["guest_base_rate_source"],
                      "record_min_calls": c["record_min_calls"]},
            "calls": scored}


# ------------------------------------------------------------------ critic hook and index
def market_view(price_ref: str | None, asof: str, direction: str | None = None) -> dict | None:
    """Stored cards on a market, as of a date (descriptive): cards leaning with and against an idea, the latest
    against, and the record of those speakers when it is long enough. None when there is nothing."""
    if not price_ref:
        return None
    c = cfg()
    lo = (date.fromisoformat(asof) - timedelta(days=c["critic_lookback_days"])).isoformat()
    ks = [k for k in load_cards(asof) if price_ref in (k.get("markets") or []) and k.get("available", k.get("as_of", "")) >= lo]
    if not ks:
        return None
    sign = {"long": "up", "short": "down"}.get(direction or "")
    lean = [k for k in ks if k.get("direction") in ("up", "down")]
    with_ = [k for k in lean if sign and k["direction"] == sign]
    against = [k for k in lean if sign and k["direction"] != sign]
    # one guest's three bearish cards are one view: the critic counts distinct speakers (review A11, finding 19)
    out = {"n_cards": len(ks), "n_with": len(with_), "n_against": len(against), "since": lo,
           "speakers_with": len({speaker_key(k.get("speaker")) for k in with_}),
           "speakers_against": len({speaker_key(k.get("speaker")) for k in against}),
           "latest": max(ks, key=lambda k: k["as_of"])}
    if against:
        la = max(against, key=lambda k: k["as_of"])
        out["latest_against"] = la
        recs = records([resolve(k, asof) for k in load_cards(asof) if speaker_key(k.get("speaker")) == speaker_key(la.get("speaker"))
                        and k.get("type") == "forecast"])
        r = recs.get(speaker_key(la.get("speaker")))
        if r and r["enough"]:
            out["latest_against_record"] = r
    return out


def index(write: bool = True, root: Path | None = None) -> str:
    """notes/index.md: one line per note (date, type, series, title, speakers, markets, cards), newest first."""
    root = root or NOTES
    c = cfg()
    rows = []
    for p in root.rglob("*.md"):
        if p.name in ("index.md", "README.md", "context.md") or p.name.startswith("_"):
            continue
        try:
            m = read_note(p)
            cp = p.with_suffix(".cards.json")
            cards = json.loads(cp.read_text(encoding="utf-8"))["cards"] if cp.exists() else []
        except (SystemExit, yaml.YAMLError, ValueError, KeyError) as e:
            print(f"skip {p}: {e}", file=sys.stderr)
            continue
        if m.get("type") not in NOTE_TYPES:
            continue
        ok = [k for k in cards if k.get("status") == "ok"]
        mk = sorted({x for k in ok for x in k.get("markets", [])} | {a for a in (m.get("assets") or []) if a in c["markets"]})
        rows.append((str(m.get("date")), p, m, ok, mk))
    rows.sort(key=lambda r: r[0], reverse=True)
    lines = ["# Research index", "", "One line per digested source, newest first. Built by `python -m pmstack digest index`; "
             "cards (checked claims) live beside each note in `<note>.cards.json`. Query by market with "
             "`python -m pmstack digest view --market BZ=F`.", "",
             "| Date | Type | Series | Title | Speakers | Markets | Cards (ok / forecasts) | Note |",
             "|---|---|---|---|---|---|---|---|"]
    for d, p, m, ok, mk in rows:
        speakers = ", ".join(str(g).split("(")[0].strip() for g in (m.get("guests") or []))[:80]
        fc = sum(1 for k in ok if k.get("type") == "forecast")
        title = str(m.get("episode") or m.get("title") or p.stem).replace("|", "/")
        lines.append(f"| {d} | {m.get('type')} | {str(m.get('series') or '').replace('|', '/')} | {title} | {speakers} | "
                     f"{' '.join(mk)} | {len(ok)} / {fc} | [{p.name}]({p.relative_to(root).as_posix()}) |")
    text = "\n".join(lines) + "\n"
    if write:
        (root / "index.md").write_text(text, encoding="utf-8")
    return text


def previous(note: str | Path) -> list[dict]:
    """Earlier ok cards from the same series or the same speakers on the same markets: for 'what changed since last time'."""
    note = Path(note)
    meta = read_note(note)
    as_of = note_date(meta)
    cp = note.with_suffix(".cards.json")
    mine = json.loads(cp.read_text(encoding="utf-8"))["cards"] if cp.exists() else []
    spk = {speaker_key(k.get("speaker")) for k in mine}
    mk = {m for k in mine for m in k.get("markets", [])}
    key = note_key(note)
    out = []
    for k in load_cards(as_of):
        if k["note"] == key or k.get("as_of", "") >= as_of:
            continue
        same_series = meta.get("series") and k.get("series") == meta.get("series")
        if (same_series or speaker_key(k.get("speaker")) in spk) and (not mk or set(k.get("markets", [])) & mk):
            out.append(k)
    return sorted(out, key=lambda k: k["as_of"], reverse=True)


# ------------------------------------------------------------------ CLI
def _load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _print(obj):
    print(json.dumps(obj, indent=1, ensure_ascii=False, default=str))


def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack digest", description="Research digester (agent 10)")
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="store a transcript locally from a YouTube link, URL or file")
    f.add_argument("src")
    ch = sub.add_parser("chunks", help="print extraction windows")
    ch.add_argument("transcript")
    ch.add_argument("--minutes", type=float)
    ch.add_argument("--window", type=int, help="print only this window")
    for name in ("check", "save"):
        s = sub.add_parser(name, help=f"{name} cards for a note")
        s.add_argument("note")
        s.add_argument("--cards", required=True, help="JSON list of cards")
        s.add_argument("--transcript", required=True, help="transcript path or sha12")
    fa = sub.add_parser("facts", help="code facts for a note (moves since recording), for writing and the auditor")
    fa.add_argument("note")
    fa.add_argument("--date")
    fa.add_argument("--write", action="store_true", help="write <note>.facts.json")
    sub.add_parser("index", help="rebuild notes/index.md")
    ca = sub.add_parser("calls", help="call ledger: resolved, due, speaker records")
    ca.add_argument("--date")
    ca.add_argument("--days", type=int, default=7)
    ca.add_argument("--all", action="store_true", help="print every call")
    v = sub.add_parser("view", help="stored cards on a market as of a date")
    v.add_argument("--market", required=True)
    v.add_argument("--date")
    v.add_argument("--direction", choices=["long", "short"])
    d = sub.add_parser("diff", help="earlier cards from the same series or speakers on the same markets")
    d.add_argument("note")
    a = p.parse_args(argv)
    if a.cmd == "fetch":
        meta = fetch(a.src)
        runlog.log(runlog.new_run_id(), "digest:fetch", "ok", source=meta.get("source"), sha12=meta["sha12"],
                   words=meta["words"], asr=meta["asr"])
        _print({**meta, "windows": len(chunks(load_transcript(meta["path"])))})
        return 0
    if a.cmd == "chunks":
        ws = chunks(load_transcript(a.transcript), a.minutes)
        if a.window:
            ws = [w for w in ws if w["i"] == a.window]
            print(ws[0]["text"] if ws else "no such window")
        else:
            _print([{"i": w["i"], "start": w["start"], "end": w["end"], "words": len(w["text"].split())} for w in ws])
        return 0
    if a.cmd in ("check", "save"):
        cards = _load_json(a.cards)
        rep = (save if a.cmd == "save" else check)(a.note, cards, a.transcript)
        _print({"note": rep["note"], "counts": rep["counts"], "uncovered_windows": rep["uncovered_windows"],
                "sparse_windows": rep["sparse_windows"],
                "problems": [{"id": k["id"], "status": k["status"], "problems": k["problems"]} for k in rep["cards"] if k["problems"]]})
        return 0 if not rep["counts"]["rejected"] + rep["counts"]["flagged"] else 1
    if a.cmd == "facts":
        out = facts(a.note, a.date)
        if a.write:
            Path(a.note).with_suffix(".facts.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        _print(out)
        return 0
    if a.cmd == "index":
        txt = index()
        print(f"{txt.count(chr(10)) - 6} notes indexed -> notes/index.md")
        return 0
    if a.cmd == "calls":
        out = calls(a.date, a.days)
        if not a.all:
            out.pop("calls")
        runlog.log(runlog.new_run_id(), "digest:calls", "ok", asof=out["asof"], **out["counts"])
        _print(out)
        return 0
    if a.cmd == "view":
        _print(market_view(a.market, a.date or _today_brt(), a.direction))
        return 0
    if a.cmd == "diff":
        _print(previous(a.note))
        return 0
    return 2
