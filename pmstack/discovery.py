"""Narrative discovery (agent 7, step 1 of 2): nominate emerging themes from the news, with a low bar, for Bernardo to
select in conversation (step 2, `/narratives review`). Tracking stays in consensus.py: frozen, audited definitions.

Why this shape (docs/research/narrative-discovery.md):
  - Per-article first-story detection is not worth it (TDT-3 normalised cost 0.81; Petrovic et al. AP 24-34): flag
    the first DAY of a burst in aggregate counts instead, as EMM/MedISys and GPHIN do.
  - Unit: words and word pairs of English page titles, each counted once per source domain (GPHIN keyword pairs;
    Kleinberg's bursts on titles). GKG themes mark mentions, not subjects (our headline audit: copper 4/25).
  - Score: share of the day's domain-titles vs its own EWMA/EWM variance with an explicit noise floor beta
    (SigniTrend). "Rising" = score >= 4 with >= 5 domains; "new" (day 1) = <= 2 domains on each of the last 28 days,
    >= 8 today. No p-values: thousands of terms are watched; the list is ranked and shown whole (Bernardo: everything,
    daily).
  - Rank and group by distinct sources; demote press-release wires and one-item copies (SigniTrend's Reuters
    artifact; the copper audit's junior-miner releases).
  - Context is co-movement only (Bybee et al.; Brandt & Gao: geopolitical oil news hits on the day and reverses;
    no study links news attention to CFTC positioning). Every number is point-in-time; nothing is a forecast.

Files (all under data/narratives/discovery/):
  days/<YYYY-MM-DD>.parquet       per term: domains, titles, copies, press-release domains (terms >= 3 domains);
                                  the row "__total__" holds the day's domain-title count N
  candidates/<YYYY-MM-DD>.json    the day's candidates, written once (point-in-time); usable from the next day
  decisions.jsonl                 Bernardo's promote / watch / dismiss decisions (append-only)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yaml

from . import runlog, store

ROOT = Path(__file__).resolve().parents[1]
TOTAL = "__total__"
ACTIONS = ("promote", "watch", "dismiss")
REASONS = ("noise", "not-market", "duplicate", "known", "other")


def cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "discovery.yaml").read_text(encoding="utf-8"))


def home() -> Path:
    return store.DATA / "narratives" / "discovery"


def _d(x) -> date:
    return x if isinstance(x, date) else date.fromisoformat(str(x)[:10])


# ------------------------------------------------------------------ text
SUFFIX_RE = re.compile(r"\s+[-|–—:]\s+[^-|–—:]{2,40}$")


def norm(s: str | None) -> str:
    """Lower case, non-alphanumerics (except +) to spaces: the same normalisation as the GKG queries."""
    return " ".join(re.sub(r"[^a-z0-9+]+", " ", str(s or "").lower()).split())


def clean_title(raw: str | None) -> str:
    """The title without its site-name suffix (" - Reuters", " | Mining.com"), normalised."""
    return norm(SUFFIX_RE.sub("", str(raw or "")))


def terms_of(t: str, stop: set[str]) -> set[str]:
    """Unigrams (3+ letters, not stop-words, not numbers) and bigrams (neither word a stop-word or a number)."""
    w = t.split()
    ok = [x not in stop and not x.isdigit() for x in w]
    out = {x for x, k in zip(w, ok) if k and len(x) > 2}
    out |= {f"{a} {b}" for (a, ka), (b, kb) in zip(zip(w, ok), zip(w[1:], ok[1:])) if ka and kb}
    return out


def count_terms(rows: list[dict], c: dict | None = None) -> pd.DataFrame:
    """Python twin of the BigQuery day aggregate (tests, local runs): rows with domain and title -> per term
    domains / titles / copies / press-release domains, terms with >= store_min_domains, plus the __total__ row."""
    c = c or cfg()
    stop, pr = set(c["stopwords"]), set(c["press_release_domains"])
    pairs: dict[tuple[str, str], int] = {}
    for r in rows:
        t = clean_title(r.get("title"))
        if len(t.split()) < 3:
            continue
        k = (str(r.get("domain") or ""), t)
        pairs[k] = pairs.get(k, 0) + 1
    agg: dict[str, dict] = {}
    for (d, t), n in pairs.items():
        for term in terms_of(t, stop):
            a = agg.setdefault(term, {"doms": set(), "titles": set(), "copies": 0})
            a["doms"].add(d)
            a["titles"].add(t)
            a["copies"] += n
    out = [{"term": k, "domains": len(v["doms"]), "titles": len(v["titles"]), "copies": v["copies"],
            "pr_domains": len(v["doms"] & pr)} for k, v in agg.items() if len(v["doms"]) >= c["store_min_domains"]]
    out.append({"term": TOTAL, "domains": len(pairs), "titles": len({t for _, t in pairs}),
                "copies": sum(pairs.values()), "pr_domains": 0})
    return pd.DataFrame(out)


# ------------------------------------------------------------------ BigQuery (run by adapters/gdelt_disc.py)
_SAFE = re.compile(r"^[a-z0-9+ .\-]+$")


def _lit(xs: list[str]) -> str:
    bad = [x for x in xs if not _SAFE.match(x)]
    if bad:
        raise ValueError(f"unsafe literal(s) {bad[:3]}")
    return "[" + ", ".join(f"'{x}'" for x in xs) + "]"


def _base_cte(table: str) -> str:
    title = "IFNULL(REGEXP_EXTRACT(Extras, r'<PAGE_TITLE>(.*?)</PAGE_TITLE>'), '')"
    cls = "-|" + chr(0x2013) + chr(0x2014) + ":"          # the dashes as characters: RE2 has no \u escapes
    strip = "REGEXP_REPLACE(" + title + r", r'\s+[" + cls + r"]\s+[^" + cls + r"]{2,40}$', '')"
    t = rf"TRIM(REGEXP_REPLACE(LOWER({strip}), r'[^a-z0-9+]+', ' '))"
    return (f"a AS (SELECT LOWER(SourceCommonName) AS d, DocumentIdentifier AS url, {title} AS raw, {t} AS t "
            f"FROM `{table}` WHERE _PARTITIONTIME >= TIMESTAMP(@start) AND _PARTITIONTIME < TIMESTAMP(@stop) "
            f"AND SourceCollectionIdentifier = 1 AND NOT REGEXP_CONTAINS(GKGRECORDID, r'-T')), "
            f"b AS (SELECT d, t, ANY_VALUE(raw) AS raw, MIN(url) AS url, COUNT(*) AS copies FROM a "
            f"WHERE ARRAY_LENGTH(SPLIT(t, ' ')) >= 3 GROUP BY d, t)")


def terms_sql(c: dict, table: str) -> str:
    """One day's term aggregate, counted in BigQuery so ~tens of thousands of rows come back, not every title.
    English records only (machine-translated GKG records carry '-T' in GKGRECORDID: GKG 2.1 codebook)."""
    stop, pr = _lit(sorted(set(c["stopwords"]))), _lit(sorted(set(c["press_release_domains"])))
    num = r"r'^[0-9]+$'"
    return (f"WITH {_base_cte(table)}, "
            f"w AS (SELECT d, t, copies, tok, off FROM b, UNNEST(SPLIT(t, ' ')) AS tok WITH OFFSET off), "
            f"g AS (SELECT d, t, copies, tok AS w1, LEAD(tok) OVER (PARTITION BY d, t ORDER BY off) AS w2 FROM w), "
            f"terms AS (SELECT d, t, copies, w1 AS term FROM g WHERE w1 NOT IN UNNEST({stop}) "
            f"AND NOT REGEXP_CONTAINS(w1, {num}) AND LENGTH(w1) > 2 "
            f"UNION ALL SELECT d, t, copies, CONCAT(w1, ' ', w2) FROM g WHERE w2 IS NOT NULL "
            f"AND w1 NOT IN UNNEST({stop}) AND w2 NOT IN UNNEST({stop}) "
            f"AND NOT REGEXP_CONTAINS(w1, {num}) AND NOT REGEXP_CONTAINS(w2, {num})) "
            f"SELECT term, COUNT(DISTINCT d) AS domains, COUNT(DISTINCT t) AS titles, SUM(copies) AS copies, "
            f"COUNT(DISTINCT IF(d IN UNNEST({pr}), d, NULL)) AS pr_domains FROM terms GROUP BY term "
            f"HAVING domains >= {int(c['store_min_domains'])} "
            f"UNION ALL SELECT '{TOTAL}', COUNT(*), COUNT(DISTINCT t), SUM(copies), 0 FROM b")


def titles_sql(terms: list[str], c: dict, table: str) -> str:
    """Titles for the day's flagged terms only (query 2): per term, the most widely carried distinct titles."""
    return (f"WITH {_base_cte(table)}, f AS (SELECT term FROM UNNEST({_lit(terms)}) AS term), "
            f"m AS (SELECT f.term, b.* FROM b JOIN f ON STRPOS(CONCAT(' ', b.t, ' '), CONCAT(' ', f.term, ' ')) > 0) "
            f"SELECT term, t, ANY_VALUE(raw) AS title, MIN(url) AS url, COUNT(DISTINCT d) AS domains, SUM(copies) AS copies, "
            f"ARRAY_AGG(DISTINCT d LIMIT 100) AS doms FROM m GROUP BY term, t "
            f"QUALIFY ROW_NUMBER() OVER (PARTITION BY term ORDER BY COUNT(DISTINCT d) DESC, FARM_FINGERPRINT(t)) "
            f"<= {int(c['titles_per_term'])}")


# ------------------------------------------------------------------ storage
def day_path(day: date) -> Path:
    return home() / "days" / f"{day}.parquet"


def cand_path(day: date) -> Path:
    return home() / "candidates" / f"{day}.json"


def save_day(day: date, agg: pd.DataFrame):
    p = day_path(day)
    p.parent.mkdir(parents=True, exist_ok=True)
    agg[["term", "domains", "titles", "copies", "pr_domains"]].to_parquet(p, index=False)


def stored_days() -> list[date]:
    return sorted(_d(p.stem) for p in (home() / "days").glob("*.parquet"))


def history(day: date, n: int) -> list[tuple[date, pd.DataFrame]]:
    """The stored days before `day` (never `day` itself or later), at most n, oldest first."""
    ds = [d for d in stored_days() if d < day][-n:]
    return [(d, pd.read_parquet(day_path(d))) for d in ds]


# ------------------------------------------------------------------ scoring
def score(day: date, agg: pd.DataFrame, hist: list[tuple[date, pd.DataFrame]], c: dict | None = None) -> pd.DataFrame:
    """Per term today: share x = domains / N; EWMA and EWM variance of x over the stored prior days (zero where a
    stored day lacks the term: it had fewer than store_min_domains); s = (x - max(ewma, beta)) / (sqrt(var) + beta),
    beta = noise_floor_domains / N. Flags: rising, new (day 1). Only days before `day` enter the baseline."""
    c = c or cfg()
    tot = agg.loc[agg["term"] == TOTAL, "domains"]
    n_today = float(tot.iloc[0]) if len(tot) else 0.0
    t = agg[agg["term"] != TOTAL].copy()
    if t.empty or n_today <= 0:
        return pd.DataFrame(columns=["term", "domains", "share", "score", "rising", "new", "history_days"])
    t["share"] = t["domains"] / n_today
    beta = c["noise_floor_domains"] / n_today
    lam = 1 - 0.5 ** (1 / float(c["half_life_days"]))
    terms = set(t["term"])
    ewma = {k: 0.0 for k in terms}
    ewv = {k: 0.0 for k in terms}
    lookback = c["new"]["lookback_days"]
    recent_max = {k: 0 for k in terms}
    started = False
    for i, (d, h) in enumerate(hist):
        hn = h.loc[h["term"] == TOTAL, "domains"]
        if not len(hn) or float(hn.iloc[0]) <= 0:
            continue
        nn = float(hn.iloc[0])
        hh = h[h["term"].isin(terms)].set_index("term")
        dom = hh["domains"].to_dict()
        if not started:                       # EWMA starts at the first observation, not at zero (no warm-up ramp)
            for k in terms:
                ewma[k] = dom.get(k, 0) / nn
            started = True
        else:
            for k in terms:
                x = dom.get(k, 0) / nn
                diff = x - ewma[k]
                ewma[k] += lam * diff
                ewv[k] = (1 - lam) * (ewv[k] + lam * diff * diff)
        if i >= len(hist) - lookback:
            for k, v in dom.items():
                recent_max[k] = max(recent_max[k], int(v))
    valid = sum(1 for _, h in hist if len(h.loc[h["term"] == TOTAL]))
    t["ewma"] = t["term"].map(ewma)
    t["ewm_sd"] = t["term"].map(lambda k: math.sqrt(max(ewv[k], 0.0)))
    t["score"] = (t["share"] - t["ewma"].clip(lower=beta)) / (t["ewm_sd"] + beta)
    t["prior_max_domains"] = t["term"].map(recent_max)
    enough = valid >= c["min_history_days"]
    r, nw = c["rising"], c["new"]
    t["rising"] = enough & (t["score"] >= r["min_score"]) & (t["domains"] >= r["min_domains"])
    t["new"] = enough & (t["prior_max_domains"] <= nw["max_prior_domains"]) & (t["domains"] >= nw["min_domains"])
    t["history_days"] = valid
    return t.sort_values(["new", "score"], ascending=False).reset_index(drop=True)


def flagged(scored: pd.DataFrame, c: dict | None = None) -> pd.DataFrame:
    c = c or cfg()
    f = scored[scored["rising"] | scored["new"]]
    return f.head(int(c["max_flagged_terms"]))


# ------------------------------------------------------------------ grouping into candidates
def _jacc(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def _rand_key(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def group(day: date, fl: pd.DataFrame, title_rows: list[dict], c: dict | None = None) -> list[dict]:
    """Terms sharing >= group_jaccard of their titles form one candidate (union-find). Its domains are the union of
    its titles' domains; its label is its most widely carried title (the model only words a summary later)."""
    c = c or cfg()
    by_term: dict[str, dict[str, dict]] = {}
    for r in title_rows:
        k = str(r.get("t") or "") or clean_title(r.get("title"))
        if not k:
            continue
        e = by_term.setdefault(str(r["term"]), {}).setdefault(k, {"t": k, "title": r.get("title"), "url": r.get("url"),
                                                                  "doms": set(), "copies": 0})
        e["doms"] |= set(r.get("doms") or ([r["domain"]] if r.get("domain") else []))
        e["copies"] += int(r.get("copies") or 1)
    terms = [t for t in fl["term"] if t in by_term]
    parent = {t: t for t in terms}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    sets = {t: set(by_term[t]) for t in terms}
    for i, a in enumerate(terms):
        for b in terms[i + 1:]:
            if _jacc(sets[a], sets[b]) >= c["group_jaccard"]:
                parent[find(a)] = find(b)
    groups: dict[str, list[str]] = {}
    for t in terms:
        groups.setdefault(find(t), []).append(t)
    info = fl.set_index("term")
    pr = set(c["press_release_domains"])
    out = []
    for ts in groups.values():
        titles: dict[str, dict] = {}
        for t in ts:
            for k, e in by_term[t].items():
                x = titles.setdefault(k, {"t": k, "title": e["title"], "url": e["url"], "doms": set(), "copies": 0})
                x["doms"] |= e["doms"]
                x["copies"] = max(x["copies"], e["copies"])
        doms = set().union(*[x["doms"] for x in titles.values()]) if titles else set()
        ranked = sorted(titles.values(), key=lambda x: (-len(x["doms"]), -x["copies"], x["t"]))
        top = ranked[: int(c["headlines_top"])]
        rest = sorted(ranked[len(top):], key=lambda x: _rand_key(f"{day}|{x['t']}"))[: int(c["headlines_random"])]
        copies = sorted((x["copies"] for x in titles.values()), reverse=True)
        best = max(ts, key=lambda t: (bool(info.loc[t, "new"]), float(info.loc[t, "score"])))
        cid = f"{day}-{re.sub(r'[^a-z0-9]+', '-', best).strip('-')[:40]}"
        out.append({
            "id": cid, "day": str(day), "label": top[0]["title"] if top else best, "terms": sorted(ts),
            "lead_term": best, "domains": len(doms), "titles": len(titles),
            "new": bool(any(info.loc[t, "new"] for t in ts)), "rising": bool(any(info.loc[t, "rising"] for t in ts)),
            "score": round(float(max(info.loc[t, "score"] for t in ts)), 2),
            "press_release_share": round(len(doms & pr) / len(doms), 2) if doms else 0.0,
            "top3_copy_share": round(sum(copies[:3]) / sum(copies), 2) if sum(copies) else 0.0,
            "headlines": [{"title": x["title"], "url": x["url"], "domains": len(x["doms"]), "kind": "top"} for x in top]
            + [{"title": x["title"], "url": x["url"], "domains": len(x["doms"]), "kind": "random"} for x in rest],
            "_titles": [x["title"] or x["t"] for x in titles.values()],
        })
    return out


def _lex(c: dict) -> dict[str, list[str]]:
    return {ref: [norm(w) for w in m["terms"]] for ref, m in c["markets"].items()}


def markets_touched(titles: list[str], c: dict) -> list[dict]:
    lex = _lex(c)
    out = []
    ts = [f" {clean_title(t)} " for t in titles if t]
    for ref, words in lex.items():
        hit = sum(1 for t in ts if any(f" {w} " in t for w in words))
        if ts and hit / len(ts) >= c["market_title_share"]:
            out.append({"price_ref": ref, "name": c["markets"][ref]["name"], "title_share": round(hit / len(ts), 2)})
    return sorted(out, key=lambda m: -m["title_share"])


def tracked_link(titles: list[str], c: dict) -> str | None:
    """The tracked narrative (frozen query) that matches >= link_to_tracked_share of the candidate's titles."""
    try:
        from .adapters import gdelt_bq as bq
        qs = [q for q in bq.load_queries({"queries_from": "gdelt"}) if not q.get("retired") and not q.get("validation")]
    except Exception:  # noqa: BLE001
        return None
    best = (0.0, None)
    for q in qs:
        n = sum(1 for t in titles if t and bq.matches(q["_parsed"], "", t))
        share = n / len(titles) if titles else 0.0
        if share > best[0]:
            best = (share, q["id"])
    return best[1] if best[0] >= c["link_to_tracked_share"] else None


def enrich(day: date, cands: list[dict], c: dict | None = None) -> list[dict]:
    c = c or cfg()
    dm = c["demote"]
    prev = {}
    for k in range(1, 5):
        p = cand_path(day - timedelta(days=k))
        if p.exists():
            try:
                prev[k] = {t for x in json.loads(p.read_text(encoding="utf-8")).get("candidates", []) for t in x["terms"]}
            except ValueError:
                pass
    for x in cands:
        titles = x.pop("_titles", [])
        why = []
        if x["press_release_share"] >= dm["press_release_share"]:
            why.append(f"press-release wires {int(100 * x['press_release_share'])}% of sources")
        if x["titles"] < dm["min_distinct_titles"]:
            why.append(f"only {x['titles']} distinct titles")
        if x["top3_copy_share"] >= dm["top3_copy_share"] and x["domains"] > 3:
            why.append(f"three sources carry {int(100 * x['top3_copy_share'])}% of copies")
        x["demoted"] = why
        x["sustained"] = sum(1 for k, ts in prev.items() if set(x["terms"]) & ts) >= 2
        x["markets"] = markets_touched(titles, c)
        x["tracked"] = tracked_link(titles, c)
        x["version"] = c["version"]
    return sorted(cands, key=lambda x: (bool(x["demoted"]), not x["new"], -bool(x["markets"]), -x["score"]))


def process_day(day: date, agg: pd.DataFrame, title_rows: list[dict] | None, c: dict | None = None,
                write: bool = True) -> dict:
    """Score a day against the stored days before it, group the flagged terms, write the day aggregate and (when
    titles were fetched) the candidate list. A candidate list, once written, is never rewritten."""
    c = c or cfg()
    hist = history(day, int(c["history_days"]))
    sc = score(day, agg, hist, c)
    fl = flagged(sc, c) if len(sc) else sc
    out = {"day": str(day), "version": c["version"], "history_days": int(sc["history_days"].iloc[0]) if len(sc) else len(hist),
           "terms_scored": int(len(sc)), "terms_flagged": int(len(fl)),
           "total_domain_titles": int(agg.loc[agg["term"] == TOTAL, "domains"].iloc[0]) if (agg["term"] == TOTAL).any() else 0}
    if write:
        save_day(day, agg)
    if title_rows is not None:
        cands = enrich(day, group(day, fl, title_rows, c), c)
        out["candidates"] = cands
        p = cand_path(day)
        if write and not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({**out, "written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                                    indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    return out


# ------------------------------------------------------------------ selection memory
def decisions_path() -> Path:
    return home() / "decisions.jsonl"


def load_decisions() -> list[dict]:
    p = decisions_path()
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def find_candidate(cid: str) -> dict | None:
    m = re.match(r"^(\d{4}-\d{2}-\d{2})-", cid)
    if not m:
        return None
    p = cand_path(_d(m.group(1)))
    if not p.exists():
        return None
    return next((x for x in json.loads(p.read_text(encoding="utf-8")).get("candidates", []) if x["id"] == cid), None)


def decide(cid: str, action: str, reason: str | None = None, markets: list[str] | None = None,
           on: str | None = None, note: str | None = None) -> dict:
    if action not in ACTIONS:
        raise SystemExit(f"action must be one of {ACTIONS}")
    if action == "dismiss" and reason not in REASONS:
        raise SystemExit(f"a dismissal needs --reason, one of {REASONS}")
    x = find_candidate(cid)
    if not x:
        raise SystemExit(f"no candidate {cid}")
    rec = {"id": cid, "action": action, "reason": reason, "on": on or str(datetime.now(timezone.utc).date()),
           "terms": x["terms"], "domains": x["domains"], "markets": markets or [m["price_ref"] for m in x["markets"]],
           "note": note, "version": x.get("version")}
    p = decisions_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    runlog.log(runlog.new_run_id(), "discovery:decide", "ok", candidate=cid, action=action, reason=reason)
    return rec


def status(x: dict, decs: list[dict], day: date, c: dict | None = None) -> dict | None:
    """The latest decision whose terms overlap this candidate's, made on or before `day`, and whether it hides it:
    dismiss -> hidden for dismiss_days unless domains >= dismiss_regrow x the level at dismissal; watch -> hidden for
    watch_days unless it grows watch_regrow x or turns sustained; promote -> shown as an update to the promoted theme."""
    c = c or cfg()
    ts = set(x["terms"])
    hits = [d for d in decs if _d(d["on"]) <= day and ts and len(ts & set(d["terms"])) / len(ts) >= c["term_overlap"]]
    if not hits:
        return None
    d = max(hits, key=lambda r: r["on"])
    age = (day - _d(d["on"])).days
    hide = False
    if d["action"] == "dismiss":
        hide = age <= c["dismiss_days"] and x["domains"] < c["dismiss_regrow"] * max(1, d["domains"])
    elif d["action"] == "watch":
        hide = age <= c["watch_days"] and x["domains"] < c["watch_regrow"] * max(1, d["domains"]) and not x.get("sustained")
    return {"action": d["action"], "on": d["on"], "of": d["id"], "hidden": bool(hide), "reason": d.get("reason")}


# ------------------------------------------------------------------ context (code facts, point-in-time)
def _prices(ref: str, until: str) -> pd.DataFrame | None:
    try:
        df = store.connect().execute("SELECT date, value, source_url FROM obs WHERE series_id = ? AND date <= ? ORDER BY date",
                                     [ref, until]).df()
    except Exception:  # noqa: BLE001
        return None
    if len(df) < 70:
        return None
    df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
    df["ret"] = df["value"].astype(float).pct_change()
    return df.dropna(subset=["ret"]).reset_index(drop=True)


def price_context(ref: str, t0: str, asof: str, c: dict | None = None) -> dict | None:
    """Return on the first flagged day, the 5 sessions before, and since, in units of the 60-day EWMA vol known the
    day before t0; change in 20-day realised vol; the base rate of a vol-scaled day at least this large over the
    prior 3 years. Descriptive co-movement, not a cause or forecast."""
    cx = (c or cfg())["context"]
    df = _prices(ref, asof)
    if df is None:
        return None
    before = df[df["date"] < t0]
    if len(before) < cx["vol_days"]:
        return None
    lam = 1 - 2 / (cx["vol_days"] + 1)
    vol = math.sqrt(float((before["ret"] ** 2).ewm(alpha=1 - lam).mean().iloc[-1]))
    on = df[df["date"] >= t0]
    if not len(on) or vol <= 0:
        return None
    r0 = float(on["ret"].iloc[0])
    pre = before.tail(cx["before_days"])
    since = on["value"].astype(float)
    base_vals = before["ret"].tail(252 * cx["base_rate_years"]).abs()
    rv_before = float(before["ret"].tail(cx["realised_vol_days"]).std() * math.sqrt(252))
    rv_now = float(df["ret"].tail(cx["realised_vol_days"]).std() * math.sqrt(252))
    return {"price_ref": ref, "t0_date": on["date"].iloc[0], "t0_move_sd": round(r0 / vol, 2),
            "before_move_sd": round(float((1 + pre["ret"]).prod() - 1) / (vol * math.sqrt(max(1, len(pre)))), 2),
            "since_pct": round(100 * (float(since.iloc[-1]) / float(before["value"].iloc[-1]) - 1), 2),
            "since_date": df["date"].iloc[-1],
            "base_rate_pct": round(100 * float((base_vals >= abs(r0)).mean()), 1) if len(base_vals) else None,
            "rv20_before_pct": round(100 * rv_before, 1), "rv20_now_pct": round(100 * rv_now, 1),
            "source_url": df["source_url"].iloc[-1]}


def cftc_context(ref: str, t0: str, asof: str) -> dict | None:
    """Managed-money net (% of OI) and its 3-year percentile from the last report public before t0 vs the latest
    public by the as-of date (Tuesday report, Friday release). No study links news attention to positioning."""
    from . import journal
    code = journal._cfg()["cftc_map"].get(ref)
    if not code:
        return None

    def at(day: str):
        until = (_d(day) - timedelta(days=3)).isoformat()
        try:
            df = store.connect().execute("SELECT date, value FROM obs WHERE series_id = ? AND date <= ? ORDER BY date",
                                         [f"{code}.mm_net_pct_oi", until]).df()
        except Exception:  # noqa: BLE001
            return None
        if len(df) < 52:
            return None
        v = df["value"].astype(float).tail(156).to_numpy()
        return {"date": str(df["date"].iloc[-1])[:10], "net_pct_oi": round(float(v[-1]), 1),
                "pct_3y": round(100 * float((v <= v[-1]).mean()), 0)}

    # a report dated T is public from T + 3: "before t0" = public by t0 - 1; "latest" = public by the as-of date
    pre, now = at((_d(t0) - timedelta(days=1)).isoformat()), at(str(asof))
    if not pre and not now:
        return None
    return {"before": pre, "latest": now, "source_url": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"}


def first_day(x: dict, day: date) -> str:
    """The first day a candidate's terms were flagged in the stored candidate lists (up to 14 days back)."""
    first = day
    for k in range(1, 15):
        p = cand_path(day - timedelta(days=k))
        if not p.exists():
            continue
        try:
            prev = json.loads(p.read_text(encoding="utf-8")).get("candidates", [])
        except ValueError:
            continue
        if any(set(x["terms"]) & set(y["terms"]) for y in prev):
            first = day - timedelta(days=k)
    return str(first)


# ------------------------------------------------------------------ the fact-pack section
def latest_day(asof: date) -> date | None:
    """Candidates for UTC day d are usable from d + 1 (the 05:40 BRT run fetches the complete day)."""
    ds = sorted(_d(p.stem) for p in (home() / "candidates").glob("*.json") if _d(p.stem) < asof)
    return ds[-1] if ds else None


def build(asof: date, entries: list[dict] | None = None) -> tuple[dict, list[dict]]:
    c = cfg()
    day = latest_day(asof)
    if day is None:
        return {"note": "no candidate list yet (discovery needs its first BigQuery runs)"}, []
    raw = json.loads(cand_path(day).read_text(encoding="utf-8"))
    decs = load_decisions()
    ideas = [e for e in (entries or []) if e.get("status") in ("open", "idea") and e.get("book") != "example"]
    shown, hidden = [], []
    for x in raw.get("candidates", []):
        st = status(x, decs, asof, c)
        x = {**x, "decision": st}
        if st and st["hidden"]:
            hidden.append(x)
            continue
        t0 = first_day(x, day)
        x["first_day"] = t0
        x["context"] = []
        for m in x["markets"][:3]:
            pc = price_context(m["price_ref"], t0, str(asof - timedelta(days=1)), c)
            cf = cftc_context(m["price_ref"], t0, str(asof))
            x["context"].append({"price_ref": m["price_ref"], "name": m["name"], "price": pc, "cftc": cf,
                                 "ideas": [e["id"] for e in ideas if e.get("price_ref") == m["price_ref"]]})
        shown.append(x)
    sec = {"day": str(day), "version": raw.get("version"), "history_days": raw.get("history_days"),
           "terms_flagged": raw.get("terms_flagged"), "candidates": shown, "hidden": len(hidden),
           "source_url": "https://www.gdeltproject.org/"}
    alerts = [{"kind": "narrative_new", "severity": 1.0 + min(2.0, x["domains"] / 20), "id": x["id"],
               "text": f"New theme ({x['domains']} sources, {x['day']}): {x['label']}", "source_url": x["headlines"][0]["url"]
               if x["headlines"] else "https://www.gdeltproject.org/"}
              for x in shown if x["new"] and x["markets"] and not x["demoted"] and not (x.get("decision") or {}).get("action")]
    return sec, alerts


def _ctx_line(cx: dict) -> str:
    p, f = cx.get("price"), cx.get("cftc")
    bits = []
    if p:
        bits.append(f"{cx['name']} {p['t0_move_sd']:+.1f} sd on {p['t0_date']} (a move that size or larger on "
                    f"{p['base_rate_pct']}% of days in 3 years), {p['before_move_sd']:+.1f} sd over the 5 sessions before, "
                    f"{p['since_pct']:+.1f}% since (to {p['since_date']}); 20-day vol {p['rv20_before_pct']}% -> {p['rv20_now_pct']}%")
    else:
        bits.append(f"{cx['name']}: no stored prices")
    if f and f.get("before") and f.get("latest"):
        bits.append(f"CFTC managed money {f['before']['net_pct_oi']}% of OI ({int(f['before']['pct_3y'])}th pct, {f['before']['date']}) "
                    f"-> {f['latest']['net_pct_oi']}% ({int(f['latest']['pct_3y'])}th, {f['latest']['date']})")
    if cx.get("ideas"):
        bits.append("open ideas: " + ", ".join(cx["ideas"]))
    return "; ".join(bits)


def render(sec: dict) -> list[str]:
    if not sec:
        return []
    L = ["## Narrative discovery (candidates for review; co-movement, not cause or forecast)", ""]
    if sec.get("note") or sec.get("error"):
        return L + [sec.get("note") or f"Not available: {sec['error']}", ""]
    cs = sec["candidates"]
    L += [f"Themes rising or new in English news titles on {sec['day']} (GDELT GKG; words and word pairs counted once "
          f"per source, vs their own last {sec['history_days']} days). {len(cs)} shown, {sec['hidden']} hidden by your "
          f"decisions. Review with `/narratives review`: promote, watch or dismiss. Price and CFTC lines are code facts "
          f"around the first flagged day: with this many candidates, some large moves line up by chance.", ""]
    groups: dict[str, list[dict]] = {}
    for x in cs:
        key = "Demoted (press-release wires or copies)" if x["demoted"] else (x["markets"][0]["name"] if x["markets"] else "Outside focus markets")
        groups.setdefault(key, []).append(x)
    order = [k for k in groups if not k.startswith(("Outside", "Demoted"))] + [k for k in groups if k.startswith("Outside")] + \
        [k for k in groups if k.startswith("Demoted")]
    for k in order:
        L += [f"**{k}**", ""]
        for x in groups[k]:
            flags = ", ".join(f for f, on in (("NEW", x["new"]), ("rising", x["rising"] and not x["new"]),
                                              ("sustained", x.get("sustained"))) if on)
            dec = x.get("decision")
            extra = f"; your {dec['action']} of {dec['on']}" if dec else ""
            trk = f"; update to tracked `{x['tracked']}`" if x.get("tracked") else ""
            L.append(f"- `{x['id']}` {flags}: {x['label']} ({x['domains']} sources, {x['titles']} titles, score "
                     f"{x['score']:.1f}; terms: {', '.join(x['terms'][:6])}{trk}{extra})")
            for h in x["headlines"][:3]:
                L.append(f"  - [{h['title']}]({h['url']})")
            for cx in x.get("context", []):
                L.append(f"  - {_ctx_line(cx)}")
            if x["demoted"]:
                L.append(f"  - demoted: {'; '.join(x['demoted'])}")
        L += [""]
    return L


# ------------------------------------------------------------------ placebo and promotion draft
def placebo(days: int = 120) -> dict:
    """Score every stored day against its own prior days (as the live run would have) and count flags per day:
    sizes the list honestly before anyone reads it (no titles needed)."""
    c = cfg()
    ds = stored_days()[-days:]
    per = []
    for d in ds:
        sc = score(d, pd.read_parquet(day_path(d)), history(d, int(c["history_days"])), c)
        if len(sc) and int(sc["history_days"].iloc[0]) >= c["min_history_days"]:
            per.append({"day": str(d), "new": int(sc["new"].sum()), "rising": int((sc["rising"] & ~sc["new"]).sum())})
    s = pd.DataFrame(per)
    if s.empty:
        return {"days": 0, "note": f"needs {c['min_history_days']}+ stored days"}
    return {"days": len(s), "new_median": float(s["new"].median()), "new_p90": float(s["new"].quantile(0.9)),
            "rising_median": float(s["rising"].median()), "rising_p90": float(s["rising"].quantile(0.9)),
            "per_day": per[-14:]}


def draft_query(cid: str) -> str:
    """A title-phrase draft for a promoted candidate: its two strongest terms as phrases, plus the press-release
    exclusions that cleaned the copper definition (round 3). Bernardo edits the meaning; `narratives measure` and the
    headline audit decide whether it is frozen."""
    x = find_candidate(cid)
    if not x:
        raise SystemExit(f"no candidate {cid}")
    terms = sorted(x["terms"], key=lambda t: (-(" " in t), t))[:4]
    phr = " OR ".join(f'"{t}"' if " " in t else t for t in terms)
    return f"({phr}) -globenewswire -newsfile -prnewswire -businesswire -accesswire -\"press releases\""


# ------------------------------------------------------------------ CLI
def cli(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="pmstack discovery", description="Narrative discovery (agent 7, step 1)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list", help="candidates usable on a date, with context")
    ls.add_argument("--date")
    ls.add_argument("--json", action="store_true")
    sh = sub.add_parser("show", help="one candidate with all its headlines")
    sh.add_argument("id")
    de = sub.add_parser("decide", help="record promote / watch / dismiss")
    de.add_argument("id")
    de.add_argument("--action", required=True, choices=ACTIONS)
    de.add_argument("--reason", choices=REASONS)
    de.add_argument("--markets", help="comma-separated price refs, to correct the markets touched")
    de.add_argument("--note")
    sub.add_parser("decisions", help="the decision log")
    pl = sub.add_parser("placebo", help="flags per day over the stored history")
    pl.add_argument("--days", type=int, default=120)
    dr = sub.add_parser("draft", help="a title-phrase query draft for a promoted candidate")
    dr.add_argument("id")
    a = ap.parse_args(argv)
    if a.cmd == "list":
        asof = _d(a.date) if a.date else (datetime.now(timezone.utc) - timedelta(hours=3)).date()
        from . import journal
        sec, _ = build(asof, journal.load_all())
        print(json.dumps(sec, indent=1, ensure_ascii=False, default=str) if a.json else "\n".join(render(sec)))
        return 0
    if a.cmd == "show":
        x = find_candidate(a.id)
        print(json.dumps(x, indent=1, ensure_ascii=False) if x else f"no candidate {a.id}")
        return 0 if x else 1
    if a.cmd == "decide":
        rec = decide(a.id, a.action, a.reason, a.markets.split(",") if a.markets else None, note=a.note)
        print(json.dumps(rec, indent=1, ensure_ascii=False))
        return 0
    if a.cmd == "decisions":
        for r in load_decisions():
            print(json.dumps(r, ensure_ascii=False))
        return 0
    if a.cmd == "placebo":
        print(json.dumps(placebo(a.days), indent=1))
        return 0
    if a.cmd == "draft":
        print(draft_query(a.id))
        return 0
    return 2
