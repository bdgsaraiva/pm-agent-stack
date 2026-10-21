"""Market news since the US close (morning note v4, 20 Oct 2026): headlines from the major outlets grouped into
stories, each tied to the markets it touches (with their move) and to the tracked narratives it feeds, plus a
narrative check (news flow today vs the prior days, stage, burst, and whether price moved the narrative's way).

Descriptive only: matching is keyword-based on headlines, so a tag is a pointer, not a classification, and the
"price agrees" column is co-movement, not a cause. Headlines only (title, link, outlet, time); no article text.
Config: config/news.yaml; sources: config/sources.d/news.yaml. Point in time: only items published and fetched
by the window end are used.
"""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
STOP = set("""a an the and or of to in on for at by with from as is are was were be been has have had its it this that
these those after before over under into amid says said say new more most than about up down out off not no will
would could may might can just how why what who when where which while near per vs via his her their our your
week weeks day days year years today tomorrow yesterday report reports live update updates""".split())
OPINION = re.compile(r"^\s*(opinion|commentary|column|editorial|analysis|breakingviews|letters?|the big take|lex)\s*[|:–-]",
                     re.IGNORECASE)   # a label then a separator: "Opinion | ...", "COMMENTARY: ..."
SHORT_KEEP = {"ai", "us", "uk", "eu", "fed", "oil", "ecb", "boe", "boj", "gdp", "cpi", "ppi", "pce", "lng", "ipo", "gas"}


def cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "news.yaml").read_text(encoding="utf-8"))


def feeds() -> dict[str, str]:
    """Feed id → outlet name, from the news source block ("" for a mixed feed: each item's outlet is in its summary)."""
    p = ROOT / "config" / "sources.d" / "news.yaml"
    blk = (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("news", {})
    return {f["id"]: "" if f.get("outlet_from_source") else f.get("outlet", f["id"]) for f in blk.get("feeds", [])}


def _pats(words: list[str]) -> list[re.Pattern]:
    return [re.compile(r"(?<![\w&+])" + re.escape(w.lower()) + r"(?![\w&+])", re.IGNORECASE) for w in words]


def _hits(title: str, pats: list[re.Pattern]) -> bool:
    return any(p.search(title) for p in pats)


def _stem(w: str) -> str:
    for suf in ("ian", "ese", "ies", "es", "s"):          # canadian → canad(a), tariffs → tariff, rallies → rall
        if len(w) > 4 + len(suf) - 1 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def tokens(title: str) -> set[str]:
    ws = re.findall(r"[a-z0-9&+']+", title.lower().replace("’", "'"))
    return {_stem(w.strip("'")) for w in ws if (len(w) >= 3 or w in SHORT_KEEP) and w not in STOP}


GENERIC = {"deal", "deals", "close", "closer", "us", "u.s", "says", "said", "trump", "talks", "new", "plan", "after",
           "over", "amid", "report", "reports", "could", "would", "set", "top", "big", "first", "back"}


def same_story(a: set[str], b: set[str], thr: float) -> float:
    """Overlap score: Jaccard, or a softer bar when three or more content words are shared (outlets word the same
    story differently: "Trump sued over 50% tariffs on Canada" vs "Trump Administration Sued Over 50% Tariffs")."""
    inter = len(a & b)
    j = inter / max(1, len(a | b))
    specific = len((a & b) - GENERIC)          # "close", "deal", "US" alone made Iran and Mexico one story (20 Oct)
    return j if specific >= 2 and (j >= thr or (inter >= 3 and j >= thr * 0.6)) else 0.0


def window(asof: date, now: datetime, start_hour: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    """From the previous weekday at `start_hour` UTC (about the previous morning note) to the build time, so the
    whole US session is in the window (a backdated pack ends at 12:00 UTC on its date, about the morning note's time,
    so it never sees later news)."""
    prev = asof - timedelta(days=1)
    while prev.weekday() >= 5:
        prev -= timedelta(days=1)
    start = pd.Timestamp(datetime.combine(prev, time(start_hour), tzinfo=timezone.utc))
    end_cap = pd.Timestamp(datetime.combine(asof + timedelta(days=1), time(3), tzinfo=timezone.utc))   # 00:00 BRT
    now_ts = pd.Timestamp(now).tz_convert("UTC") if pd.Timestamp(now).tzinfo else pd.Timestamp(now, tz="UTC")
    end = min(now_ts, end_cap) if now_ts.date() <= asof + timedelta(days=1) else \
        pd.Timestamp(datetime.combine(asof, time(12), tzinfo=timezone.utc))
    return start, end


def _frame(txt: pd.DataFrame, outlets: dict[str, str]) -> pd.DataFrame:
    t = (txt[txt["source"].isin(outlets)].copy() if txt is not None and not txt.empty
         else pd.DataFrame(columns=["source", "title", "url", "published", "summary", "fetched_at"]))
    t["published"] = pd.to_datetime(t["published"], utc=True, errors="coerce")
    t["fetched_at"] = pd.to_datetime(t["fetched_at"], utc=True, errors="coerce")
    item_outlet = t.get("summary", pd.Series("", index=t.index)).fillna("").str.extract(r"^outlet=(.+)$")[0]
    fixed = t["source"].map(outlets)
    t["outlet"] = fixed.where(fixed != "", item_outlet)                    # mixed feeds: the item's own outlet
    t = t.dropna(subset=["published", "outlet"])
    t = t[t["title"].fillna("").str.len() > 12]
    return t.drop_duplicates(["outlet", "title"])


def _moves(prices: list[dict]) -> dict[str, dict]:
    out = {}
    for r in prices or []:
        if "id" not in r:
            continue
        live = r.get("live_pct")
        mv = live if live is not None else r.get("ret1_pct")
        if mv is None:
            continue
        out[r["id"]] = {"name": r.get("name", r["id"]), "move_pct": round(float(mv), 2), "live": live is not None,
                        "date": r.get("date"), "z1": r.get("z1"), "source_url": r.get("source_url")}
    return out


def cluster(items: pd.DataFrame, tiers: dict[str, int], thr: float) -> list[dict]:
    """Greedy: the earliest headline of the best tier leads (the outlet that broke it); every other headline joins
    the story it overlaps most (same_story) or starts its own."""
    if items.empty:
        return []
    it = items.assign(tier=items["outlet"].map(lambda o: tiers.get(o, 3))).sort_values(
        ["tier", "published"], ascending=[True, True])
    stories: list[dict] = []
    for r in it.itertuples():
        tk = tokens(r.title)
        best, best_j = None, 0.0
        for s in stories:
            j = same_story(tk, s["_tk"], thr)
            if j > best_j:
                best, best_j = s, j
        row = {"title": r.title, "url": r.url, "outlet": r.outlet, "published_utc": r.published.isoformat()}
        if best is None:
            stories.append({"_tk": tk, "lead": row, "items": [row], "outlets": [r.outlet], "tier": int(r.tier)})
        else:
            best["items"].append(row)
            if r.outlet not in best["outlets"]:
                best["outlets"].append(r.outlet)
    return stories




def _price_move_re(C: dict) -> tuple[re.Pattern | None, list[re.Pattern]]:
    pm = C.get("price_move") or {}
    if not pm.get("subjects"):
        return None, []
    subj = "|".join(re.escape(s) for s in sorted(pm["subjects"], key=len, reverse=True))
    verb = "|".join(re.escape(v) for v in pm["verbs"])
    # the move is the headline's main clause: subject within its first three words, verb within two words after
    word = r"[\w.'’&-]+"
    rx = re.compile(rf"^(?:{word}\s+){{0,2}}(?:{subj})\b(?:\s+{word}){{0,2}}\s+(?:{verb})\b", re.IGNORECASE)
    return rx, _pats(pm.get("always", []))


def lean(title: str, spec: dict) -> str:
    """Pointer only: reinforce / fade cue words in a headline about the narrative."""
    r = _hits(title, _pats(spec.get("reinforce", [])))
    f = _hits(title, _pats(spec.get("fade", [])))
    return "mixed" if r and f else "reinforces" if r else "fades" if f else "neutral"


def _verdict(counts: dict, labels: tuple[str, str] = ("reinforces", "fades")) -> str:
    """The direction the news points, in the narrative's own words (e.g. "news: hawkish", "news: glut")."""
    r, f = counts.get("reinforces", 0), counts.get("fades", 0)
    if not r and not f:
        return "no directional news"
    if r > f and r >= 2 * f:
        return f"news: {labels[0]}"
    if f > r and f >= 2 * r:
        return f"news: {labels[1]}"
    return "news: mixed"


def _labels(spec: dict) -> tuple[str, str]:
    lb = spec.get("labels") or ["reinforces", "fades"]
    return str(lb[0]), str(lb[1])


def _say(lean: str, labels: tuple[str, str]) -> str:
    return labels[0] if lean == "reinforces" else labels[1] if lean == "fades" else lean


def build(txt: pd.DataFrame, prices: list[dict], consensus: dict, asof: date, now: datetime,
          C: dict | None = None, outlets: dict[str, str] | None = None) -> tuple[dict, list[dict]]:
    C = C or cfg()
    outlets = outlets or feeds()
    start, end = window(asof, now, int(C.get("start_utc_hour", 9)))
    df = _frame(txt, outlets)
    # opinion and commentary are not news (Bernardo, 20 Oct evening: prices, news, narratives and their links only)
    df = df[~df["title"].str.match(OPINION, na=False)]
    known = df[df["fetched_at"].isna() | (df["fetched_at"] <= end)]
    win = known[(known["published"] > start) & (known["published"] <= end)]
    tiers = C.get("tiers", {})
    stories = cluster(win, tiers, float(C.get("same_story_jaccard", 0.34)))

    topic_pats = {k: _pats(v["keywords"]) for k, v in C["topics"].items()}
    on_map = {n["id"]: n for n in (consensus or {}).get("narratives", []) if not n.get("validation_only")}
    specs = {}
    for k, v in (C.get("narratives") or {}).items():
        if k in on_map:                                   # Consensus-map narrative: name, markets, stage from the map
            specs[k] = {**v, "name": on_map[k].get("name", k), "markets": on_map[k].get("markets") or {}, "_map": on_map[k]}
        elif v.get("name"):                               # news-only narrative (GDELT definition not frozen yet)
            specs[k] = {**v, "_map": None}
    nar_pats = {k: _pats(v["keywords"]) for k, v in specs.items()}
    moves = _moves(prices)
    pm_rx, pm_always = _price_move_re(C)

    for s in stories:
        titles = " || ".join(i["title"] for i in s["items"])
        s["topics"] = [k for k, p in topic_pats.items() if _hits(titles, p)]
        s["narratives"] = {k: lean(s["lead"]["title"], specs[k]) for k, p in nar_pats.items() if _hits(titles, p)}
        lead = s["lead"]["title"]
        s["price_move"] = bool(pm_rx and pm_rx.search(lead)) or _hits(lead, pm_always)
        mk = []
        for k in s["topics"]:
            mk += [m for m in C["topics"][k].get("markets", []) if m in moves and m not in mk]
        s["markets"] = [{"id": m, **{k: moves[m][k] for k in ("name", "move_pct", "live", "date")}} for m in mk[:4]]
        s["n_outlets"] = len(s["outlets"])
        s["n_major"] = sum(1 for o in s["outlets"] if tiers.get(o, 3) <= 2)   # small outlets from topic feeds don't inflate
        s["score"] = (2 * s["n_major"] + 0.25 * (s["n_outlets"] - s["n_major"]) + (1 if s["tier"] == 1 else 0)
                      + (1 if s["topics"] else 0) - (2 if s["price_move"] else 0))
        del s["_tk"]
    stories.sort(key=lambda s: (-s["score"], -pd.Timestamp(s["lead"]["published_utc"]).timestamp()))

    top = [s for s in stories if (s["topics"] or s["n_major"] >= 3) and not s["price_move"]][: int(C.get("top_stories", 8))]
    by_topic = {}
    for k, v in C["topics"].items():
        ss = [s for s in stories if k in s["topics"]][: int(C.get("max_per_topic", 6))]
        if ss:
            by_topic[k] = {"name": v["name"], "stories": ss}

    # narrative check: what the news says (reinforce / fade cues), news flow vs prior days, stage, price
    nb = int(C.get("baseline_days", 7))
    hist = known[(known["published"] <= start) & (known["published"] > start - pd.Timedelta(days=nb))]
    hist_days = sorted({d for d in hist["published"].dt.date})
    order = {"reinforces": 0, "fades": 1, "mixed": 2, "neutral": 3}
    checks = []
    for nid, pats in nar_pats.items():
        spec, mp = specs[nid], specs[nid]["_map"] or {}
        today_h = int(sum(_hits(t, pats) for t in win["title"]))
        prior = [int(sum(_hits(t, pats) for t in hist[hist["published"].dt.date == d]["title"])) for d in hist_days]
        avg = round(sum(prior) / len(prior), 1) if len(prior) >= int(C.get("min_history_days", 5)) else None
        ns = [s for s in stories if nid in s["narratives"]]   # price-move headlines count here (left out of digests only)
        counts: dict[str, int] = {}
        for s in ns:
            counts[s["narratives"][nid]] = counts.get(s["narratives"][nid], 0) + 1
        price = []
        for m, sign in (spec.get("markets") or {}).items():
            if m in moves:
                mv = moves[m]["move_pct"]
                z = moves[m].get("z1")
                flat = abs(mv) < 0.15 if z is None else abs(float(z)) < 0.25 and abs(mv) < 0.3
                price.append({"id": m, "name": moves[m]["name"], "move_pct": mv, "live": moves[m]["live"],
                              "pushes": "up" if sign > 0 else "down",
                              "agrees": None if flat else (mv > 0) == (sign > 0)})
        votes = [p["agrees"] for p in price if p["agrees"] is not None]
        pverdict = ("no clear move" if not votes else "price agrees" if all(votes) else
                    "price disagrees" if not any(votes) else "price mixed")
        b = mp.get("burst") or {}
        ns.sort(key=lambda s: (order[s["narratives"][nid]], -s.get("n_major", s["n_outlets"]),
                               -pd.Timestamp(s["lead"]["published_utc"]).timestamp()))
        by_lean = {k: [s for s in ns if s["narratives"][nid] == k] for k in order}
        listed = by_lean["reinforces"][:10] + by_lean["fades"][:20]   # fading news is scarcer and decides "contested"
        listed += by_lean["mixed"][:3] + by_lean["neutral"][:2]
        lab = _labels(spec)
        checks.append({"id": nid, "name": spec["name"], "group": spec.get("group"), "news_only": not mp, "labels": list(lab),
                       "stage": mp.get("stage") or "not on the map yet (news feed only)", "stage_prev": mp.get("stage_prev"),
                       "since": mp.get("since"), "burst": bool(b.get("is_burst")), "burst_ratio": b.get("ratio_7d_vs_26w"),
                       "headlines_today": today_h, "headlines_prior_avg": avg, "prior_days": len(prior),
                       "stories_today": len(ns), "lean_counts": counts, "news_verdict": _verdict(counts, lab),
                       "stories": [{**s["lead"], "lean": s["narratives"][nid], "says": _say(s["narratives"][nid], lab),
                                    "outlets": s["outlets"],
                                    "price_move": s["price_move"]} for s in listed],   # both sides, not the first 8
                       "price": price, "price_verdict": pverdict})
    checks.sort(key=lambda c: (-(c["lean_counts"].get("reinforces", 0) + c["lean_counts"].get("fades", 0)),
                               -c["headlines_today"], c["name"]))

    sec = {"window": {"from_utc": start.isoformat(), "to_utc": end.isoformat()},
           "n_headlines": int(len(win)), "n_stories": len(stories),
           "outlets": win["outlet"].value_counts().to_dict(), "history_days": len(hist_days),
           "top": top, "topics": by_topic, "narrative_check": checks,
           "watches": {k: watch(known, v, start, end, tiers, float(C.get("same_story_jaccard", 0.34)))
                       for k, v in (C.get("watches") or {}).items()},
           "caption": ("Headlines only, grouped by title overlap; topic and narrative tags and the reinforce / fade lean are "
                       "keyword cues (pointers for the note writer, not a classification); price agreement is co-movement, "
                       "not a cause. [price move] = a headline whose point is only a price move.")}
    return sec, []


# ------------------------------------------------------------------ facts.md
def _hhmm(iso: str) -> str:
    return pd.Timestamp(iso).strftime("%d %b %H:%M")


def _story(s: dict, nar_names: dict[str, str], nar_labels: dict | None = None) -> str:
    nar_labels = nar_labels or {}
    L = s["lead"]
    also = [o for o in s["outlets"] if o != L["outlet"]]
    line = (f"- {'[price move] ' if s.get('price_move') else ''}[{L['title']}]({L['url']}) "
            f"({L['outlet']}, {_hhmm(L['published_utc'])} UTC")
    line += f"; also {', '.join(also)})" if also else ")"
    tags = []
    if s.get("narratives"):
        tags.append("narratives: " + ", ".join(f"{nar_names.get(n, n)} ({_say(ln, nar_labels.get(n, ('reinforces', 'fades')))})"
                                               for n, ln in s["narratives"].items()))
    if s.get("markets"):
        tags.append("moves: " + ", ".join(f"{m['name']} {m['move_pct']:+.2f}%{' live' if m['live'] else ''}"
                                          for m in s["markets"]))
    return line + (" — " + "; ".join(tags) if tags else "")


def render(N: dict) -> list[str]:
    if not N:
        return []
    if N.get("error"):
        return ["## News since the previous morning", "", f"Not available: {N['error']}", ""]
    w = N["window"]
    L = ["## News since the previous morning", "",
         f"{N['n_headlines']} headlines in {N['n_stories']} stories (since the previous morning) from {_hhmm(w['from_utc'])} to {_hhmm(w['to_utc'])} UTC "
         f"(" + ", ".join(f"{o} {n}" for o, n in N["outlets"].items()) + "). " + N["caption"], ""]
    if not N["n_headlines"]:
        return L + ["No headlines in the window (news fetch missing or empty).", ""]
    names = {c["id"]: c["name"] for c in N["narrative_check"]}
    labs = {c["id"]: tuple(c.get("labels") or ("reinforces", "fades")) for c in N["narrative_check"]}
    L += ["### Top stories (most outlets first; price-move headlines left out)", ""] + [_story(s, names, labs) for s in N["top"]] + [""]
    L += ["### Narrative check", "",
          "What today's headlines say about each narrative (reinforce / fade cue counts, then each story with its lean), "
          f"news flow vs the prior {N['history_days']} days with stored headlines (history starts 20 Oct 2026), the stage on "
          "the Consensus map, and whether its markets moved the way the narrative pushes. The lean is a keyword pointer: "
          "read the headline.", "",
          "| Narrative | News (direction counts / mixed / neutral) | Headlines today (prior avg) | Stage (prev) | Burst | Price | Markets |",
          "|---|---|---|---|---|---|---|"]
    for c in N["narrative_check"]:
        if not c["stories_today"] and not c["burst"]:
            continue
        lc = c["lean_counts"]
        lb = c.get("labels") or ["reinforces", "fades"]
        news = (f"{c['news_verdict']} ({lb[0]} {lc.get('reinforces', 0)} / {lb[1]} {lc.get('fades', 0)} / "
                f"{lc.get('mixed', 0)} / {lc.get('neutral', 0)})")
        stage = f"{c['stage']}" + (f" ({c['stage_prev']})" if c.get("stage_prev") and c["stage_prev"] != c["stage"] else "")
        mk = "; ".join(f"{p['name']} {p['move_pct']:+.2f}%{' live' if p['live'] else ''} (pushes {p['pushes']})"
                       for p in c["price"]) or "-"
        avg = "n/a" if c["headlines_prior_avg"] is None else f"{c['headlines_prior_avg']}"
        L.append(f"| {c['name']} | {news} | {c['headlines_today']} ({avg}) | {stage} | "
                 f"{'yes ' + str(c['burst_ratio']) + 'x' if c['burst'] else '-'} | {c['price_verdict']} | {mk} |")
    quiet = [c["name"] for c in N["narrative_check"] if not c["stories_today"] and not c["burst"]]
    if quiet:
        L += ["", "No matching stories today: " + ", ".join(quiet) + "."]
    L += [""]
    for c in N["narrative_check"]:
        if not c["stories"]:
            continue
        L += [f"**{c['name']}**" + (f" (part of {c['group']})" if c.get("group") else "") + f": {c['news_verdict']}", ""]
        for s in c["stories"]:
            also = [o for o in s["outlets"] if o != s["outlet"]]
            L.append(f"- ({s.get('says', s['lean'])}{', price move' if s.get('price_move') else ''}) [{s['title']}]({s['url']}) ({s['outlet']}, {_hhmm(s['published_utc'])} UTC"
                     + (f"; also {', '.join(also)})" if also else ")"))
        L += [""]
    L += render_watches(N)
    for k, t in N["topics"].items():
        L += [f"### {t['name']}", ""] + [_story(s, names, labs) for s in t["stories"]] + [""]
    return L


# ------------------------------------------------------------------ watches (low-frequency themes)
def watch(known: pd.DataFrame, spec: dict, start: pd.Timestamp, end: pd.Timestamp, tiers: dict, thr: float) -> dict:
    """Stories over the last `window_days` that match a watch (e.g. the Brazil fund industry): an industry word and
    (an event word or a watched local manager), or a watched global manager with a Brazil word. New = published since
    the previous US close. Most days this is empty and the note leaves the section out. A Brazilian manager with an
    event word also counts ("Itaú Asset monta mesa com ex-sócio da Novus")."""
    since = end - pd.Timedelta(days=int(spec.get("window_days", 7)))
    w = known[(known["published"] > since) & (known["published"] <= end)]
    ind, ev = _pats(spec.get("industry", [])), _pats(spec.get("events", []))
    loc, glob, br = _pats(spec.get("managers_br", [])), _pats(spec.get("managers_global", [])), _pats(spec.get("brazil", []))

    exc = _pats(spec.get("exclude", []))
    exc_rx = re.compile(spec["exclude_regex"]) if spec.get("exclude_regex") else None

    def hit(t: str) -> bool:
        if _hits(t, exc) or (exc_rx and exc_rx.search(t)):
            return False
        return ((_hits(t, ind) and (_hits(t, ev) or _hits(t, loc))) or (_hits(t, loc) and _hits(t, ev))
                or (_hits(t, glob) and _hits(t, br)))
    m = w[w["title"].map(hit)]
    stories = cluster(m, tiers, thr)
    out = []
    for s in sorted(stories, key=lambda s: s["lead"]["published_utc"], reverse=True):
        first = min(pd.Timestamp(i["published_utc"]) for i in s["items"])
        out.append({"lead": s["lead"], "outlets": s["outlets"], "new": bool(first > start)})
    return {"name": spec.get("name"), "window_days": int(spec.get("window_days", 7)), "stories": out,
            "n_new": sum(1 for s in out if s["new"])}


def render_watches(N: dict) -> list[str]:
    L = []
    for k, w in (N.get("watches") or {}).items():
        L += [f"### {w['name']} (last {w['window_days']} days; {w['n_new']} new since the previous morning)", ""]
        if not w["stories"]:
            L += ["Nothing in the window.", ""]
            continue
        for s in w["stories"]:
            ld = s["lead"]
            also = [o for o in s["outlets"] if o != ld["outlet"]]
            L.append(f"- {'NEW ' if s['new'] else ''}[{ld['title']}]({ld['url']}) ({ld['outlet']}, {_hhmm(ld['published_utc'])} UTC"
                     + (f"; also {', '.join(also)})" if also else ")"))
        L += [""]
    return L
