"""Morning note page (29 Oct 2026, Bernardo: an HTML page instead of a doc, with a listen mode).

Renders the audited briefs/<date>/note.md into briefs/<date>/note.html: the page body the Artifact tool
publishes (no doctype/html/head/body; the publisher adds the skeleton). The page carries the note as
written (no figure is added or changed) and a spoken script built from the same text, read aloud by
the browser's own speech engine (Web Speech API: no audio file, no external service).

    python -m pmstack notepage briefs/2026-10-29/note.md [--out briefs/2026-10-29/note.html]
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

import markdown

# Sections the audio skips (the page still shows them).
SILENT = ("journal candidates", "data health")

_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
           "October", "November", "December"]


# --------------------------------------------------------------------------- parsing
def split_sections(md: str) -> tuple[str, str, list[dict]]:
    """-> (title, banner_md, [{title, md}]) from the note's markdown."""
    md = re.sub(r"<!--.*?-->\s*", "", md, flags=re.S)
    lines = md.strip().splitlines()
    title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("# ") else "Morning note"
    body = "\n".join(lines[1:] if lines and lines[0].startswith("# ") else lines)
    parts = re.split(r"^## +(.+)$", body, flags=re.M)
    banner = parts[0].strip()
    secs = [{"title": parts[i].strip(), "md": parts[i + 1].strip()} for i in range(1, len(parts), 2)]
    return title, banner, secs


# --------------------------------------------------------------------------- speech
def _say_date(m: re.Match) -> str:
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f"{d} {_MONTHS[mo - 1]}"


def _say_signed(m: re.Match) -> str:
    sign, num, unit = m.group(1), m.group(2), m.group(3) or ""
    word = {"+": "up ", "-": "down ", "−": "down "}.get(sign, "")
    unit = {"%": " percent", "bp": " basis points", "pp": " percentage points", "pts": " points",
            "sd": " standard deviations", "kbd": " thousand barrels a day",
            "kbbl": " thousand barrels"}.get(unit.strip(), unit)
    return f"{word}{num}{unit}"


def speakable(text: str) -> str:
    """Plain markdown text -> words a speech engine reads well. Numbers are kept as written."""
    t = text
    t = re.sub(r"\s*\(\[[^\]]+\]\([^)]+\)[^()]*\)", "", t)    # "([Reuters](url), also NYT)" citations
    t = re.sub(r"\s*\(([^()]*);\s*\[link\]\([^)]+\)\)", "", t)   # "(Site; [link](url))"
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)          # remaining links -> their text
    t = re.sub(r"\balerts:\d{4}-\d{2}-\d{2}#(\d+)", r"alert \1", t)
    t = re.sub(r"\*\*|__|\*", "", t)
    t = re.sub(r"\s*\([A-Z]{2,4}[FGHJKMNQUVXZ]\d{2}\)", "", t)  # contract codes
    t = re.sub(r"(\d{4})-(\d{2})-(\d{2})", _say_date, t)
    t = re.sub(r"\b(\d+)y\b", r"\1-year", t)
    t = re.sub(r"(?<![\w.])([+\-\u2212])(\d[\d,]*(?:\.\d+)?)\s?(%|bp|pp|pts|sd|kbd|kbbl)?", _say_signed, t)
    t = re.sub(r"(\d)%", r"\1 percent", t)
    t = re.sub(r"(percent|points|basis points|\d) (c|y)\b(?!-)", r"\1", t)
    t = re.sub(r"\$(\d[\d,.]*)\s?(tn|trillion|bn|billion)\b", lambda m: f"{m.group(1)} {'trillion' if m.group(2).startswith('t') else 'billion'} dollars", t)
    t = re.sub(r"\$(\d[\d,.]*)/GPU-hr", r"\1 dollars per GPU hour", t)
    t = re.sub(r"\$(\d[\d,.]*)", r"\1 dollars", t)
    rep = {" vs prev": " versus the previous print", " vs ": " versus ", " q/q": " quarter on quarter",
           " m/m": " month on month", " y/y": " year on year", " ET ": " Eastern ", " ET,": " Eastern,",
           " BRT": " Brasília time", " 4w": " four weeks", "SAAR": "annualised", " / ": " or ", "<": "below ",
           " \u2014 ": ", ", "\u2014": ", ", "\u2013": ", "}
    for k, v in rep.items():
        t = t.replace(k, v)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([,;.:)])", r"\1", t)
    return t


def _md_blocks(md: str) -> list[str]:
    """Paragraphs and list items as separate plain-text blocks (tables dropped)."""
    out, para = [], []
    for raw in md.splitlines():
        line = raw.rstrip()
        if line.startswith("|"):
            continue
        m = re.match(r"\s*(?:[-*]|\d+\.)\s+(.*)", line)
        if m:
            if para:
                out.append(" ".join(para)); para = []
            out.append(m.group(1))
        elif not line.strip():
            if para:
                out.append(" ".join(para)); para = []
        else:
            para.append(line.strip())
    if para:
        out.append(" ".join(para))
    return out


def _sentences(text: str) -> list[str]:
    """Split on '; ' and '. ' outside parentheses; each piece ends with a full stop."""
    out, buf, depth = [], "", 0
    for k, ch in enumerate(text):
        buf += ch
        depth += ch == "("
        depth -= ch == ")"
        nxt = text[k + 1:k + 2]
        if depth <= 0 and ch in ".;" and nxt == " " and len(buf.strip()) > 25:
            out.append(buf); buf = ""
    if buf.strip():
        out.append(buf)
    res = []
    for p in out:
        p = p.strip().rstrip(";:,").strip()
        if len(p) > 1:
            p = p[0].upper() + p[1:]
            res.append(p if p.endswith((".", "?", "!")) else p + ".")
    return res


def table_speech(md: str) -> list[str]:
    rows = [r for r in md.splitlines() if r.startswith("|")]
    out = []
    for r in rows[2:]:
        cells = [c.strip() for c in r.strip("|").split("|")]
        if len(cells) < 3 or not cells[1]:
            continue                                     # group header rows
        name, level, chg = cells[0], cells[1], cells[2]
        level = re.sub(r"\s+[cy]$", "", level)
        out.append(speakable(f"{name}, {level}, {chg}."))
    return out


def speech_script(sections: list[dict], title: str) -> list[dict]:
    script = [{"i": -1, "title": title, "lines": [speakable(title) + "."]}]
    for i, s in enumerate(sections):
        if s["title"].lower().startswith(SILENT):
            continue
        lines = [speakable(s["title"]) + "."]
        if s["title"].lower().startswith("market levels"):
            lines += table_speech(s["md"])
        else:
            for b in _md_blocks(s["md"]):
                b = re.sub(r"^\*\*Data:\*\*", "Data:", b)
                lines += _sentences(speakable(b))
        script.append({"i": i, "title": s["title"], "lines": [x for x in lines if x.strip(". ")]})
    return script


# --------------------------------------------------------------------------- html
_SIGNED = re.compile(r"(?<![\w.#/=-])([+\-−]\d[\d,]*(?:\.\d+)?\s?(?:%|bp|pp|pts)?)")


def _mark_signs(h: str) -> str:
    """Colour signed changes in text nodes only (never inside tags or URLs)."""
    def fix(seg: str) -> str:
        return _SIGNED.sub(lambda m: f'<span class="{"up" if m.group(1)[0] == "+" else "dn"}">{m.group(1)}</span>', seg)
    parts = re.split(r"(<[^>]+>)", h)
    inside_code = False
    for k, p in enumerate(parts):
        if p.startswith("<"):
            inside_code = p.startswith("<code") or (inside_code and not p.startswith("</code"))
            continue
        if not inside_code:
            parts[k] = fix(p)
    return "".join(parts)


def _render(md: str) -> str:
    h = markdown.markdown(md, extensions=["tables", "sane_lists"], tab_length=2)
    h = re.sub(r'<a href="', '<a target="_blank" rel="noopener" href="', h)
    # sd column: flag moves of 1.5 sd or more
    h = re.sub(r"<td([^>]*)>([+\-]\d+\.\d)</td>\s*</tr>",
               lambda m: f'<td{m.group(1)} class="sd{" big" if abs(float(m.group(2))) >= 1.5 else ""}">{m.group(2)}</td></tr>', h)
    # bold group rows in the levels table
    h = re.sub(r"<tr>\s*<td><strong>([^<]+)</strong></td>(\s*<td[^>]*></td>)+\s*</tr>",
               r'<tr class="grp"><td colspan="4">\1</td></tr>', h)
    # narrative verdict lines: "**Name — verdict**: ..."
    h = re.sub(r"<strong>([^<]+?) — ([^<]+?)</strong>",
               lambda m: f'<strong class="nar">{m.group(1)}</strong> <span class="verdict v-{_vclass(m.group(2))}">{m.group(2)}</span>', h)
    h = re.sub(r"<li>(\s*)<strong>(very [a-z]+):</strong>", r'<li class="very">\1<strong>\2:</strong>', h)
    return _mark_signs(h)


def _vclass(v: str) -> str:
    v = v.lower()
    if v.startswith("mixed"):
        return "mixed"
    if any(w in v for w in ("increase", "shortage", "hawkish", "worse", "bearish", "weak", "less", "stronger")):
        return "hot"
    if any(w in v for w in ("decrease", "glut", "dovish", "better", "bullish", "strong", "more", "weaker")):
        return "cool"
    return "mixed"


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def build(note_path: str | Path) -> str:
    md = Path(note_path).read_text(encoding="utf-8")
    title, banner, secs = split_sections(md)
    script = speech_script(secs, title)
    m = re.search(r"— (\w+) (\d+) (\w+) (\d{4})", title)
    dateline = f"{m.group(1)}, {m.group(2)} {m.group(3)} {m.group(4)}" if m else ""
    def short(t: str) -> str:
        m2 = re.match(r"Market in a Minute \((.+)\)", t)
        return m2.group(1).capitalize() if m2 else t.split(":")[0]
    nav = "".join(f'<a href="#{_slug(s["title"])}">{html.escape(short(s["title"]))}</a>' for s in secs)
    body = []
    if banner:
        body.append(f'<div class="banner">{_render(banner)}</div>')
    for i, s in enumerate(secs):
        audible = any(x["i"] == i for x in script)
        btn = (f'<button class="from" type="button" data-sec="{i}" aria-label="Listen from {html.escape(s["title"])}">'
               f'<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5v11l9-5.5z"/></svg>Listen from here</button>') if audible else ""
        cls = "sec levels" if s["title"].lower().startswith("market levels") else "sec"
        body.append(f'<section class="{cls}" id="{_slug(s["title"])}" data-sec="{i}"><div class="sh"><h2>{html.escape(s["title"])}</h2>{btn}</div>'
                    f'<div class="sb">{_render(s["md"])}</div></section>')
    return (TEMPLATE.replace("__TITLE__", html.escape(title))
            .replace("__DATELINE__", html.escape(dateline))
            .replace("__NAV__", nav)
            .replace("__BODY__", "\n".join(body))
            .replace("__SCRIPT__", json.dumps(script, ensure_ascii=False).replace("</", "<\\/")))


def cli(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pmstack notepage")
    ap.add_argument("note")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    out = Path(a.out) if a.out else Path(a.note).with_suffix(".html")
    out.write_text(build(a.note), encoding="utf-8")
    print(json.dumps({"out": str(out), "bytes": out.stat().st_size}))
    return 0


TEMPLATE = r"""<title>Morning Note</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75..100,500..800&family=Public+Sans:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
/* Layout: a single reading column under a sticky listen bar; the levels table is a quote board. */
:root{
  --bg:#f3f5f6; --paper:#ffffff; --ink:#14212b; --muted:#5b6b76; --rule:#d9e0e4;
  --accent:#0f6b73; --accent-ink:#ffffff; --up:#0b7a47; --dn:#b3261e; --hot:#9a3b12; --hot-bg:#fbe9df;
  --cool:#0f5c8a; --cool-bg:#e2f0f8; --mix:#5b5f2a; --mix-bg:#efefd9; --hl:#fff3c4;
  --f-display:"Archivo","Helvetica Neue",Arial,sans-serif; --f-body:"Public Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --f-data:"JetBrains Mono",ui-monospace,"SFMono-Regular",Menlo,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#0e161c; --paper:#152029; --ink:#e4ebef; --muted:#93a4ae; --rule:#26343e;
  --accent:#4fb8bf; --accent-ink:#06262a; --up:#4cc98a; --dn:#ff8a80; --hot:#ffb38a; --hot-bg:#3a2418;
  --cool:#8fcaf0; --cool-bg:#142d3d; --mix:#d8d89a; --mix-bg:#2e2f1c; --hl:#3d3514; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0e161c; --paper:#152029; --ink:#e4ebef; --muted:#93a4ae; --rule:#26343e;
  --accent:#4fb8bf; --accent-ink:#06262a; --up:#4cc98a; --dn:#ff8a80; --hot:#ffb38a; --hot-bg:#3a2418;
  --cool:#8fcaf0; --cool-bg:#142d3d; --mix:#d8d89a; --mix-bg:#2e2f1c; --hl:#3d3514; color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font:16px/1.55 var(--f-body);margin:0}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:10;background:var(--paper)}
.wrap{max-width:46rem;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:0 3rem}
header.top{padding-block:1.75rem 1rem}
.eyebrow{font:600 .72rem/1 var(--f-data);letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}
h1{font:800 clamp(1.9rem,6vw,2.6rem)/1.05 var(--f-display);font-stretch:85%;margin:.4rem 0 0;text-wrap:balance}
nav.toc{display:flex;flex-wrap:wrap;gap:.35rem .9rem;margin-top:.9rem;font-size:.82rem}
nav.toc a{color:var(--muted);text-decoration:none;border-bottom:1px solid var(--rule)}
nav.toc a:hover{color:var(--accent)}
.player{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--paper);border-bottom:1px solid var(--rule);box-shadow:0 1px 0 var(--rule)}
.player .in{max-width:46rem;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:.6rem;display:flex;align-items:center;gap:.6rem;flex-wrap:wrap}
.pbtn{display:inline-flex;align-items:center;justify-content:center;gap:.4rem;border:1px solid var(--rule);background:var(--paper);color:var(--ink);border-radius:999px;height:2.4rem;min-width:2.4rem;padding:0 .7rem;font:600 .85rem var(--f-body);cursor:pointer}
.pbtn svg{width:1rem;height:1rem;fill:currentColor}
.pbtn.main{background:var(--accent);color:var(--accent-ink);border-color:var(--accent);padding:0 1.05rem}
.pbtn:focus-visible,.from:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.now{flex:1 1 10rem;min-width:0;font-size:.8rem;color:var(--muted);line-height:1.3}
.now b{display:block;color:var(--ink);font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar{height:3px;background:var(--rule);border-radius:2px;margin-top:.35rem;overflow:hidden}
.bar i{display:block;height:100%;width:0;background:var(--accent);transition:width .3s}
.opts{display:flex;gap:.4rem;align-items:center}
select{font:.8rem var(--f-body);color:var(--ink);background:var(--paper);border:1px solid var(--rule);border-radius:6px;height:2.1rem;padding:0 .3rem;max-width:9rem}
.nosupport{font-size:.8rem;color:var(--muted)}
.banner{background:var(--hl);border-radius:8px;padding:.7rem 1rem;margin:1rem 0;font-size:.9rem}
.sec{padding-block:1.4rem .4rem;border-top:1px solid var(--rule)}
.sec:first-of-type{border-top:0}
.sh{display:flex;align-items:baseline;justify-content:space-between;gap:1rem;flex-wrap:wrap}
h2{font:700 1.2rem/1.2 var(--f-display);font-stretch:90%;margin:0;text-wrap:balance}
.from{display:inline-flex;align-items:center;gap:.3rem;border:0;background:none;color:var(--accent);font:600 .78rem var(--f-body);cursor:pointer;padding:.2rem 0}
.from svg{width:.75rem;height:.75rem;fill:currentColor}
.sb{min-width:0}
.sb p{margin:.7rem 0;max-width:65ch}
.sb ul{padding-left:1.15rem;margin:.6rem 0}
.sb li{margin:.4rem 0}
.sb li li{font-size:.94rem}
.sb a{color:var(--accent);text-decoration-thickness:1px;text-underline-offset:2px}
code{font:.82em var(--f-data);background:var(--bg);border:1px solid var(--rule);border-radius:4px;padding:.05rem .3rem;overflow-wrap:anywhere}
.up{color:var(--up);font-variant-numeric:tabular-nums;white-space:nowrap}
.dn{color:var(--dn);font-variant-numeric:tabular-nums;white-space:nowrap}
.nar{font-family:var(--f-display);font-stretch:90%;font-size:1.02rem}
.verdict{display:inline-block;font:600 .74rem/1 var(--f-data);text-transform:uppercase;letter-spacing:.06em;padding:.28rem .5rem;border-radius:4px;vertical-align:.1em}
.v-hot{background:var(--hot-bg);color:var(--hot)} .v-cool{background:var(--cool-bg);color:var(--cool)} .v-mixed{background:var(--mix-bg);color:var(--mix)}
li.very{list-style:none;margin-left:-1.15rem;padding:.35rem .6rem;border-left:3px solid var(--hot);background:var(--hot-bg);border-radius:0 6px 6px 0}
.levels .sb{overflow-x:auto}
.levels table{border-collapse:collapse;width:100%;font:.88rem var(--f-data);font-variant-numeric:tabular-nums;background:var(--paper);border-radius:8px;overflow:hidden}
.levels th{font:600 .7rem var(--f-body);text-transform:uppercase;letter-spacing:.08em;color:var(--muted);text-align:right;padding:.55rem .7rem;border-bottom:1px solid var(--rule)}
.levels th:first-child,.levels td:first-child{text-align:left;font-family:var(--f-body)}
.levels td{padding:.38rem .7rem;text-align:right;border-bottom:1px solid var(--rule);white-space:nowrap}
.levels tr.grp td{font:600 .68rem var(--f-body);text-transform:uppercase;letter-spacing:.1em;color:var(--accent);background:var(--bg);padding:.45rem .7rem}
.levels td.sd{color:var(--muted)} .levels td.sd.big{color:var(--ink);font-weight:600}
.levels p{font-size:.78rem;color:var(--muted)}
.reading{background:var(--hl);border-radius:4px;box-shadow:0 0 0 .3rem var(--hl)}
@media (max-width:480px){.levels table{font-size:.78rem}.levels td,.levels th{padding:.34rem .4rem}.levels th{font-size:.62rem;letter-spacing:.04em}}
@media (prefers-reduced-motion:reduce){.bar i{transition:none}}
</style>

<header class="top wrap"><div class="eyebrow">Commodities desk · 06:18 BRT</div><h1>__TITLE__</h1><nav class="toc" aria-label="Sections">__NAV__</nav></header>
<div class="player" role="region" aria-label="Listen to the note"><div class="in">
  <button class="pbtn" id="prev" type="button" aria-label="Previous section"><svg viewBox="0 0 16 16"><path d="M3 2h2v12H3zM14 2.5v11L6 8z"/></svg></button>
  <button class="pbtn main" id="play" type="button"><svg viewBox="0 0 16 16" id="ico"><path d="M4 2.5v11l9-5.5z"/></svg><span id="lbl">Listen</span></button>
  <button class="pbtn" id="next" type="button" aria-label="Next section"><svg viewBox="0 0 16 16"><path d="M11 2h2v12h-2zM2 2.5v11L10 8z"/></svg></button>
  <div class="now"><b id="nowT">About <span id="mins">0</span> min of audio</b><span id="nowS">Tap Listen to hear the note read aloud.</span><div class="bar"><i id="prog"></i></div></div>
  <div class="opts"><select id="rate" aria-label="Speed"><option value="0.9">0.9×</option><option value="1" selected>1×</option><option value="1.15">1.15×</option><option value="1.3">1.3×</option><option value="1.5">1.5×</option></select><select id="voice" aria-label="Voice"></select></div>
</div></div>
<main class="wrap">__BODY__</main>
<script id="speech" type="application/json">__SCRIPT__</script>
<script>
(function(){
  var S=JSON.parse(document.getElementById('speech').textContent);
  var q=[];S.forEach(function(s,si){s.lines.forEach(function(l){q.push({si:si,sec:s.i,t:l});});});
  var words=q.reduce(function(n,x){return n+x.t.split(' ').length;},0);
  document.getElementById('mins').textContent=Math.max(1,Math.round(words/160));
  var syn=window.speechSynthesis, pos=0, playing=false, voices=[], cur=null;
  var $=function(id){return document.getElementById(id);};
  if(!syn||typeof SpeechSynthesisUtterance==='undefined'){
    $('nowT').textContent='Listening is not available here';
    $('nowS').textContent='This view has no speech engine. Open the page in Safari or Chrome to listen.';
    ['play','prev','next','rate','voice'].forEach(function(id){$(id).disabled=true;});
    document.querySelectorAll('.from').forEach(function(b){b.hidden=true;});
    return;
  }
  var pref=null; try{pref=localStorage.getItem('mn-voice');}catch(e){}
  var rate=1; try{rate=parseFloat(localStorage.getItem('mn-rate'))||1;}catch(e){}
  $('rate').value=String(rate);
  function loadVoices(){
    voices=syn.getVoices().filter(function(v){return /^en/i.test(v.lang);});
    voices.sort(function(a,b){return score(b)-score(a);});
    var sel=$('voice');sel.innerHTML='';
    voices.forEach(function(v,k){var o=document.createElement('option');o.value=v.name;o.textContent=v.name.replace(/Microsoft |Google |\(.*\)/g,'').trim()+' · '+v.lang.slice(-2);sel.appendChild(o);});
    if(pref&&voices.some(function(v){return v.name===pref;}))sel.value=pref;
    sel.hidden=!voices.length;
  }
  function score(v){var s=0;if(/natural|neural|premium|enhanced|siri/i.test(v.name))s+=4;if(/google/i.test(v.name))s+=2;if(/en-(GB|US)/i.test(v.lang))s+=1;if(v.localService)s+=0.5;return s;}
  loadVoices(); if(syn.onvoiceschanged!==undefined)syn.onvoiceschanged=loadVoices;
  function mark(){
    document.querySelectorAll('.reading').forEach(function(e){e.classList.remove('reading');});
    var x=q[pos]; if(!x)return;
    $('nowT').textContent=S[x.si].title;
    $('nowS').textContent=(x.si+1)+' of '+S.length;
    $('prog').style.width=(100*pos/q.length)+'%';
    if(x.sec>=0){var el=document.querySelector('section[data-sec="'+x.sec+'"] h2');if(el){el.classList.add('reading');}}
  }
  function setBtn(){ $('lbl').textContent=playing?'Pause':(pos>0&&pos<q.length?'Resume':'Listen');
    $('ico').innerHTML=playing?'<path d="M3.5 2h3v12h-3zM9.5 2h3v12h-3z"/>':'<path d="M4 2.5v11l9-5.5z"/>'; }
  function speak(){
    if(pos>=q.length){playing=false;pos=0;setBtn();$('prog').style.width='100%';$('nowS').textContent='Finished.';return;}
    mark();
    var u=new SpeechSynthesisUtterance(q[pos].t); cur=u;
    var v=voices.filter(function(v){return v.name===$('voice').value;})[0]; if(v){u.voice=v;u.lang=v.lang;}else{u.lang='en-GB';}
    u.rate=parseFloat($('rate').value)||1;
    u.onend=function(){ if(cur!==u||!playing)return; pos++; speak(); };
    u.onerror=function(e){ if(cur!==u)return; if(e.error==='interrupted'||e.error==='canceled')return; pos++; if(playing)speak(); };
    syn.speak(u);
  }
  function stop(){ cur=null; syn.cancel(); }
  function play(){ playing=true; setBtn(); stop(); speak(); }
  function pause(){ playing=false; stop(); setBtn(); }
  function jumpSection(si){ var k=q.findIndex(function(x){return x.si===si;}); if(k<0)return; pos=k; play(); }
  $('play').onclick=function(){ playing?pause():play(); };
  $('next').onclick=function(){ var si=(q[pos]?q[pos].si:0)+1; if(si<S.length)jumpSection(si); };
  $('prev').onclick=function(){ var si=q[pos]?q[pos].si:0; var first=q.findIndex(function(x){return x.si===si;}); jumpSection(pos-first>1?si:Math.max(0,si-1)); };
  $('rate').onchange=function(){ try{localStorage.setItem('mn-rate',this.value);}catch(e){} if(playing)play(); };
  $('voice').onchange=function(){ try{localStorage.setItem('mn-voice',this.value);}catch(e){} if(playing)play(); };
  document.querySelectorAll('.from').forEach(function(b){ b.onclick=function(){ var sec=+b.dataset.sec; var si=S.findIndex(function(s){return s.i===sec;}); if(si>=0)jumpSection(si); }; });
  // Chrome stops long speech after ~15 s in the background; keep it alive.
  var mobile=/Android|iPhone|iPad/i.test(navigator.userAgent);
  setInterval(function(){ if(!mobile&&playing&&syn.speaking&&!syn.paused){ syn.pause(); syn.resume(); } },12000);
  window.addEventListener('pagehide',stop);
})();
</script>
"""


if __name__ == "__main__":
    raise SystemExit(cli())
