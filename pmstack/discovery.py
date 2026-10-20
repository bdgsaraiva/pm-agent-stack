"""Narrative discovery (agent 7, step 1 of 2): nominate emerging themes from the news, with a low bar, for Bernardo to
select in conversation (step 2, `/narratives review`). Tracking stays in consensus.py: frozen, audited definitions.

Why this shape (docs/research/narrative-discovery.md):
  - Per-article first-story detection is not worth it (TDT-3 normalised cost 0.81; Petrovic et al. AP 24-34): flag
    the first DAY of a burst in aggregate counts instead, as EMM/MedISys and GPHIN do.
  - Unit: words and word pairs of English page titles, each counted once per source domain (GPHIN keyword pairs;
    Kleinberg's bursts on titles). GKG themes mark mentions, not subjects (our headline audit: copper 4/25).
  - Score: share of the day's sources vs its own EWMA/EWM variance with an explicit noise floor beta (SigniTrend).
    "Rising" = score >= 4 with >= 5 sources; "new" (day 1) = <= 2 sources on each of the last 28 days, >= 8 today.
    No p-values: thousands of terms are watched; the list is ranked (Bernardo: every candidate, daily).
  - Rank and group by distinct sources; demote press-release wires and one-item copies (SigniTrend's Reuters
    artifact; the copper audit's junior-miner releases).
  - Context is co-movement only (Bybee et al.; Brandt & Gao: geopolitical oil news hits on the day and reverses;
    no study links news attention to CFTC positioning). Every number is point-in-time; nothing is a forecast.

Files (under data/narratives/discovery/):
  days/<YYYY-MM-DD>.parquet       per term: domains, titles, copies, press-release domains (terms >= 3 domains); the
                                  row "__total__" holds the day's distinct sources. NOT in git (about 1-2 MB a day):
                                  kept in the data job's Actions cache and rebuilt by the backfill when the cache is gone
  candidates/<YYYY-MM-DD>.json    the day's candidates, written once (point-in-time); usable from the next day
  decisions.jsonl                 Bernardo's promote / watch / dismiss decisions (append-only)
Independent review (20 Oct 2026, 17 defects) is in docs/research/narrative-discovery.md, "Review".
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import runlog, store

ROOT = Path(__file__).resolve().parents[1]
TOTAL = "__total__"
ACTIONS = ("promote", "watch", "dismiss")
REASONS = ("noise", "not-market", "duplicate", "known", "other")


def cfg() -> dict:
    c = yaml.safe_load((ROOT / "config" / "discovery.yaml").read_text(encoding="utf-8"))
    # "new" means absent from the stored days only while the prior cap is below the storage floor (review #16)
    assert c["new"]["max_prior_domains"] < c["store_min_domains"], "new.max_prior_domains must be < store_min_domains"
    return c


def home() -> Path:
    return store.DATA / "narratives" / "discovery"


def _d(x) -> date:
    return x if isinstance(x, date) else date.fromisoformat(str(x)[:10])


def _brt_today() -> date:
    return (datetime.now(timezone.utc) - timedelta(hours=3)).date()


# ------------------------------------------------------------------ text
DASHES = "-|" + chr(0x2013) + chr(0x2014) + ":"
TAIL_RE = re.compile(r"\s+[" + re.escape(DASHES) + r"]\s+([^" + re.escape(DASHES) + r"]{2,40})$")


def norm(s: str | None) -> str:
    """Lower case, non-alphanumerics (except +) to spaces: the same normalisation as the GKG queries."""
    return " ".join(re.sub(r"[^a-z0-9+]+", " ", str(s or "").lower()).split())


def _stem(domain: str | None) -> str:
    m = re.match(r"^(?:www\.)?([a-z0-9-]+)", str(domain or "").lower())
    return m.group(1).replace("-", "") if m else ""


def clean_title(raw: str | None, domain: str | None = None) -> str:
    """HTML entities decoded; the trailing site name cut ONLY when it names the source (" - Reuters" on
    reuters.com), so "Gold rallies - analysts see more upside" keeps its tail (review #9); normalised."""
    t = html.unescape(str(raw or ""))
    m = TAIL_RE.search(t)
    st = _stem(domain)
    if m and st and st in re.sub(r"[^a-z0-9]", "", m.group(1).lower()):
        t = t[:m.start()]
    return norm(t)


def terms_of(t: str, stop: set[str]) -> set[str]:
    """Unigrams (3+ letters, not stop-words, not numbers) and bigrams (neither word a stop-word or a number)."""
    w = t.split()
    ok = [x not in stop and not x.isdigit() for x in w]
    out = {x for x, k in zip(w, ok) if k and len(x) > 2}
    out |= {f"{a} {b}" for (a, ka), (b, kb) in zip(zip(w, ok), zip(w[1:], ok[1:])) if ka and kb}
    return out


def count_terms(rows: list[dict], c: dict | None = None) -> pd.DataFrame:
    """Python twin of the BigQuery day aggregate (tests, local runs): rows with domain and title -> per term
    domains / titles / copies / press-release domains, terms with >= store_min_domains, plus the __total__ row
    (its `domains` = the day's distinct sources: the share's denominator)."""
    c = c or cfg()
    stop, pr = set(c["stopwords"]), set(c["press_release_domains"])
    pairs: dict[tuple[str, str], int] = {}
    for r in rows:
        d = str(r.get("domain") or "").lower()
        if not d:
            continue
        t = clean_title(r.get("title"), d)
        if len(t.split()) < 3:
            continue
        pairs[(d, t)] = pairs.get((d, t), 0) + 1
    agg: dict[str, dict] = {}
    for (d, t), n in pairs.items():
        for term in terms_of(t, stop):
            a = agg.setdefault(term, {"doms": set(), "titles": set(), "copies": 0})
            a["doms"].add(d)
            a["titles"].add(t)
            a["copies"] += n
    out = [{"term": k, "domains": len(v["doms"]), "titles": len(v["titles"]), "copies": v["copies"],
            "pr_domains": len(v["doms"] & pr)} for k, v in agg.items() if len(v["doms"]) >= c["store_min_domains"]]
    out.append({"term": TOTAL, "domains": len({d for d, _ in pairs}), "titles": len({t for _, t in pairs}),
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
    """English web records with a source, titles with entities decoded and the tail cut only when it names the
    source (the Python twin: clean_title)."""
    raw = "IFNULL(REGEXP_EXTRACT(Extras, r'<PAGE_TITLE>(.*?)</PAGE_TITLE>'), '')"
    dec = raw
    for ent, ch in (("&amp;", "&"), ("&#38;", "&"), ("&quot;", '"'), ("&#34;", '"'), ("&#39;", "'"), ("&apos;", "'"),
                    ("&#8216;", "'"), ("&#8217;", "'"), ("&#8220;", '"'), ("&#8221;", '"'), ("&nbsp;", " "),
                    ("&#160;", " "), ("&#8211;", chr(0x2013)), ("&#8212;", chr(0x2014))):
        dec = f"REPLACE({dec}, '{ent}', '{ch if ch != chr(39) else chr(92) + chr(39)}')"
    cls = DASHES.replace("-", "\\-")
    tail = r"r'\s+[" + cls + r"]\s+([^" + cls + r"]{2,40})$'"
    stem = r"REPLACE(IFNULL(REGEXP_EXTRACT(LOWER(SourceCommonName), r'^(?:www\.)?([a-z0-9-]+)'), ''), '-', '')"
    cut = (f"IF(STRPOS(REGEXP_REPLACE(LOWER(IFNULL(REGEXP_EXTRACT(x.dec, {tail}), '')), r'[^a-z0-9]', ''), x.stem) > 0 "
           f"AND x.stem != '', REGEXP_REPLACE(x.dec, {tail}, ''), x.dec)")
    t = rf"TRIM(REGEXP_REPLACE(LOWER({cut}), r'[^a-z0-9+]+', ' '))"
    return (f"x AS (SELECT LOWER(SourceCommonName) AS d, DocumentIdentifier AS url, {dec} AS dec, {stem} AS stem "
            f"FROM `{table}` WHERE _PARTITIONTIME >= TIMESTAMP(@start) AND _PARTITIONTIME < TIMESTAMP(@stop) "
            f"AND SourceCollectionIdentifier = 1 AND NOT REGEXP_CONTAINS(GKGRECORDID, r'-T') "
            f"AND SourceCommonName IS NOT NULL AND SourceCommonName != ''), "
            f"a AS (SELECT x.d, x.url, x.dec AS raw, {t} AS t FROM x), "
            f"b AS (SELECT d, t, ANY_VALUE(raw) AS raw, MIN(url) AS url, COUNT(*) AS copies FROM a "
            f"WHERE ARRAY_LENGTH(SPLIT(t, ' ')) >= 3 GROUP BY d, t)")


def terms_sql(c: dict, table: str) -> str:
    """One day's term aggregate, counted in BigQuery so tens of thousands of rows come back, not every title.
    English records only (machine-translated GKG records carry '-T' in GKGRECORDID: GKG 2.1 codebook)."""
    stop, pr = _lit(sorted(set(c["stopwords"]))), _lit(sorted(set(c["press_release_domains"])))
    num = r"r'^[0-9]+$'"
    return (f"WITH {_base_cte(table)}, "
            f"w AS (SELECT d, t, copies, tok, off FROM b, UNNEST(SPLIT(t, ' ')) AS tok WITH OFFSET off), "
            f"g AS (SELECT d, t, copies, tok AS w1, LEAD(tok) OVER (PARTITION BY d, t ORDER BY off) AS w2 FROM w), "
            f"terms AS (SELECT DISTINCT d, t, copies, term FROM ("     # a term twice in one title counts once (#14)
            f"SELECT d, t, copies, w1 AS term FROM g WHERE w1 NOT IN UNNEST({stop}) "
            f"AND NOT REGEXP_CONTAINS(w1, {num}) AND LENGTH(w1) > 2 "
            f"UNION ALL SELECT d, t, copies, CONCAT(w1, ' ', w2) FROM g WHERE w2 IS NOT NULL "
            f"AND w1 NOT IN UNNEST({stop}) AND w2 NOT IN UNNEST({stop}) "
            f"AND NOT REGEXP_CONTAINS(w1, {num}) AND NOT REGEXP_CONTAINS(w2, {num}))) "
            f"SELECT term, COUNT(DISTINCT d) AS domains, COUNT(DISTINCT t) AS titles, SUM(copies) AS copies, "
            f"COUNT(DISTINCT IF(d IN UNNEST({pr}), d, NULL)) AS pr_domains FROM terms GROUP BY term "
            f"HAVING domains >= {int(c['store_min_domains'])} "
            f"UNION ALL SELECT '{TOTAL}', COUNT(DISTINCT d), COUNT(DISTINCT t), SUM(copies), 0 FROM b")


def titles_sql(terms: list[str], c: dict, table: str) -> str:
    """Titles for the day's flagged terms only (query 2): per term, the most widely carried distinct titles."""
    return (f"WITH {_base_cte(table)}, f AS (SELECT term FROM UNNEST({_lit(terms)}) AS term), "
            f"m AS (SELECT f.term, b.* FROM b JOIN f ON STRPOS(CONCAT(' ', b.t, ' '), CONCAT(' ', f.term, ' ')) > 0) "
            f"SELECT term, t, ANY_VALUE(raw) AS title, MIN(url) AS url, COUNT(DISTINCT d) AS domains, SUM(copies) AS copies, "
            f"ARRAY_AGG(DISTINCT d IGNORE NULLS LIMIT 100) AS doms FROM m GROUP BY term, t "
            f"QUALIFY ROW_NUMBER() OVER (PARTITION BY term ORDER BY COUNT(DISTINCT d) DESC, FARM_FINGERPRINT(t)) "
            f"<= {int(c['titles_per_term'])}")


# ------------------------------------------------------------------ storage
def day_path(day: date) -> Path:
    return home() / "days" / f"{day}.parquet"


def cand_path(day: date) -> Path:
    return home() / "candidates" / f"{day}.json"


def save_day(day: date, agg: pd.DataFrame) -> bool:
    """Store a day's aggregate; an empty or partial partition (no total) is not stored, so it is refetched (#11)."""
    tot = agg.loc[agg["term"] == TOTAL, "domains"] if len(agg) else pd.Series(dtype=float)
    if not len(tot) or float(tot.iloc[0]) <= 0:
        return False
    p = day_path(day)
    p.parent.mkdir(parents=True, exist_ok=True)
    agg[["term", "domains", "titles", "copies", "pr_domains"]].to_parquet(p, index=False)
    return True


def stored_days() -> list[date]:
    return sorted(_d(p.stem) for p in (home() / "days").glob("*.parquet"))


def history(day: date, n: int) -> list[tuple[date, pd.DataFrame]]:
    """The stored days before `day` (never `day` itself or later), at most n, oldest first."""
    ds = [d for d in stored_days() if d < day][-n:]
    return [(d, pd.read_parquet(day_path(d))) for d in ds]


def prune(keep_days: int, today: date) -> int:
    """Drop day aggregates older than the baseline needs (the Actions cache stays small)."""
    n = 0
    for d in stored_days():
        if d < today - timedelta(days=keep_days):
            day_path(d).unlink()
            n += 1
    return n


# ------------------------------------------------------------------ scoring
def score(day: date, agg: pd.DataFrame, hist: list[tuple[date, pd.DataFrame]], c: dict | None = None) -> pd.DataFrame:
    """Per term today: share x = sources / the day's sources; EWMA (started at the first stored day) and EWM
    variance of x over the stored prior days (zero where a stored day lacks the term: under store_min_domains);
    s = (x - max(ewma, beta)) / (sqrt(var) + beta), beta = noise_floor_domains / the day's sources. Flags: rising,
    new (day 1). Only days before `day` enter the baseline. Vectorised over terms (review #1)."""
    c = c or cfg()
    cols = ["term", "domains", "titles", "copies", "pr_domains", "share", "ewma", "ewm_sd", "score",
            "prior_max_domains", "rising", "new", "history_days"]
    tot = agg.loc[agg["term"] == TOTAL, "domains"] if len(agg) else pd.Series(dtype=float)
    n_today = float(tot.iloc[0]) if len(tot) else 0.0
    t = agg[agg["term"] != TOTAL].reset_index(drop=True).copy()
    if t.empty or n_today <= 0:
        return pd.DataFrame(columns=cols)
    idx = pd.Index(t["term"].astype(str).to_numpy(dtype=object))
    m = len(t)
    valid = [(d, h) for d, h in hist if len(h) and float((h.loc[h["term"] == TOTAL, "domains"].tolist() or [0])[0]) > 0]
    shares = np.zeros((len(valid), m))
    raw = np.zeros((len(valid), m))
    for i, (d, h) in enumerate(valid):
        nn = float(h.loc[h["term"] == TOTAL, "domains"].iloc[0])
        pos = idx.get_indexer(h["term"].astype(str).to_numpy(dtype=object))
        keep = pos >= 0
        v = h["domains"].to_numpy(dtype=float)[keep]
        raw[i, pos[keep]] = v
        shares[i, pos[keep]] = v / nn
    lam = 1 - 0.5 ** (1 / float(c["half_life_days"]))
    ewma, ewv = np.zeros(m), np.zeros(m)
    if len(valid):
        ewma = shares[0].copy()
        for i in range(1, len(valid)):
            diff = shares[i] - ewma
            ewma = ewma + lam * diff
            ewv = (1 - lam) * (ewv + lam * diff * diff)
    lb = int(c["new"]["lookback_days"])
    prior_max = raw[-lb:].max(axis=0) if len(valid) else np.zeros(m)
    t["share"] = t["domains"].to_numpy(dtype=float) / n_today
    beta = c["noise_floor_domains"] / n_today
    t["ewma"] = ewma
    t["ewm_sd"] = np.sqrt(np.maximum(ewv, 0.0))
    t["score"] = (t["share"] - np.maximum(t["ewma"], beta)) / (t["ewm_sd"] + beta)
    t["prior_max_domains"] = prior_max.astype(int)
    enough = len(valid) >= c["min_history_days"]
    r, nw = c["rising"], c["new"]
    t["rising"] = enough & (t["score"] >= r["min_score"]) & (t["domains"] >= r["min_domains"])
    t["new"] = enough & (t["prior_max_domains"] <= nw["max_prior_domains"]) & (t["domains"] >= nw["min_domains"])
    t["history_days"] = len(valid)
    return t[cols].sort_values(["new", "score"], ascending=False).reset_index(drop=True)


def flagged(scored: pd.DataFrame, c: dict | None = None) -> pd.DataFrame:
    c = c or cfg()
    if scored.empty:
        return scored
    f = scored[scored["rising"].astype(bool) | scored["new"].astype(bool)]
    return f.head(int(c["max_flagged_terms"]))


# ------------------------------------------------------------------ grouping into candidates
def _jacc(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def _rand_key(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def group(day: date, fl: pd.DataFrame, title_rows: list[dict], c: dict | None = None) -> list[dict]:
    """Terms sharing >= group_jaccard of their titles form one candidate (union-find). Its sources are the union of
    its titles' sources; its label is its most widely carried title (the model only words a summary later)."""
    c = c or cfg()
    by_term: dict[str, dict[str, dict]] = {}
    for r in title_rows:
        k = str(r.get("t") or "") or clean_title(r.get("title"))
        if not k:
            continue
        e = by_term.setdefault(str(r["term"]), {}).setdefault(
            k, {"t": k, "title": html.unescape(str(r.get("title") or k)), "url": r.get("url"), "doms": set(), "copies": 0})
        e["doms"] |= {x for x in (r.get("doms") or ([r["domain"]] if r.get("domain") else [])) if x}
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
        exact = max(int(info.loc[t, "domains"]) for t in ts) if "domains" in info.columns else 0   # titles are sampled
        ranked = sorted(titles.values(), key=lambda x: (-len(x["doms"]), -x["copies"], x["t"]))
        top = ranked[: int(c["headlines_top"])]
        rest = sorted(ranked[len(top):], key=lambda x: _rand_key(f"{day}|{x['t']}"))[: int(c["headlines_random"])]
        copies = sorted((x["copies"] for x in titles.values()), reverse=True)
        best = max(ts, key=lambda t: (bool(info.loc[t, "new"]), float(info.loc[t, "score"])))
        h6 = hashlib.sha1("|".join(sorted(ts)).encode("utf-8")).hexdigest()[:6]
        cid = f"{day}-{re.sub(r'[^a-z0-9]+', '-', best).strip('-')[:40]}-{h6}"      # unique ids (#12)
        out.append({
            "id": cid, "day": str(day), "label": top[0]["title"] if top else best, "terms": sorted(ts),
            "lead_term": best, "domains": max(len(doms), exact), "titles": len(titles),
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
    return {ref: [norm(html.unescape(w)) for w in m["terms"]] for ref, m in c["markets"].items()}


def markets_touched(titles: list[str], c: dict) -> list[dict]:
    lex = _lex(c)
    out = []
    ts = [f" {clean_title(t)} " for t in titles if t]
    for ref, words in lex.items():
        hit = sum(1 for t in ts if any(f" {w} " in t for w in words))
        if ts and hit / len(ts) >= c["market_title_share"]:
            out.append({"price_ref": ref, "name": c["markets"][ref]["name"], "title_share": round(hit / len(ts), 2)})
    return sorted(out, key=lambda m: -m["title_share"])


def tracked_queries() -> dict[str, list[dict]]:
    """narrative id -> its definitions: the frozen v1 DOC query and, when it has one, the v2 instrument's query
    (review #4). Both are tried on titles alone; a v2 clause that needs GKG themes cannot match a title, so the v1
    query keeps that narrative linkable. Validation queries (EPU, GPR) are left out."""
    from .adapters import gdelt_bq as bq
    cur: dict[str, list[dict]] = {}
    skip = set()
    for q in bq.load_queries({"queries_from": "gdelt"}):
        if q.get("validation"):
            skip.add(q["id"])
            continue
        cur.setdefault(q["id"], []).append(q)
    try:
        for q in bq.load_queries({"queries_from": "gdelt_bq_v2"}):
            nid = q.get("narrative")
            if nid and nid not in skip and not q.get("validation"):
                cur.setdefault(nid, []).append(q)
    except Exception:  # noqa: BLE001
        pass
    return cur


def tracked_link(titles: list[str], c: dict, qs: dict | None = None) -> str | None:
    """The tracked narrative (its id) one of whose definitions matches >= link_to_tracked_share of the candidate's
    titles; the best share wins."""
    try:
        from .adapters import gdelt_bq as bq
        qs = qs if qs is not None else tracked_queries()
    except Exception:  # noqa: BLE001
        return None
    ts = [t for t in titles if t]
    if not ts:
        return None
    best = (0.0, None)
    for nid, defs in qs.items():
        for q in defs:
            try:
                share = sum(1 for t in ts if bq.matches(q["_parsed"], "", t)) / len(ts)
            except Exception:  # noqa: BLE001
                continue
            if share > best[0]:
                best = (share, nid)
    return best[1] if best[0] >= c["link_to_tracked_share"] else None


def enrich(day: date, cands: list[dict], c: dict | None = None) -> list[dict]:
    c = c or cfg()
    dm = c["demote"]
    lo, hi = c["sustained_days"]
    prev = {}
    for k in range(1, hi):
        p = cand_path(day - timedelta(days=k))
        if p.exists():
            try:
                prev[k] = {t for x in json.loads(p.read_text(encoding="utf-8")).get("candidates", []) for t in x["terms"]}
            except ValueError:
                pass
    try:
        qs = tracked_queries()
    except Exception:  # noqa: BLE001
        qs = {}
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
        x["sustained"] = sum(1 for k, ts in prev.items() if set(x["terms"]) & ts) >= lo
        x["markets"] = markets_touched(titles, c)
        x["tracked"] = tracked_link(titles, c, qs)
        x["version"] = c["version"]
    return sorted(cands, key=lambda x: (bool(x["demoted"]), not x["new"], not x["markets"], -x["score"]))


def process_day(day: date, agg: pd.DataFrame, title_rows: list[dict] | None, c: dict | None = None,
                write: bool = True) -> dict:
    """Score a day against the stored days before it, group the flagged terms, write the day aggregate and (when
    titles were fetched AND the baseline is long enough) the candidate list, once; never rewritten (#11)."""
    c = c or cfg()
    hist = history(day, int(c["history_days"]))
    sc = score(day, agg, hist, c)
    fl = flagged(sc, c)
    hd = int(sc["history_days"].iloc[0]) if len(sc) else len(hist)
    tot = agg.loc[agg["term"] == TOTAL, "domains"] if len(agg) else pd.Series(dtype=float)
    out = {"day": str(day), "version": c["version"], "history_days": hd, "terms_scored": int(len(sc)),
           "terms_flagged": int(len(fl)), "total_sources": int(tot.iloc[0]) if len(tot) else 0}
    if write:
        save_day(day, agg)
    if title_rows is not None and hd >= c["min_history_days"]:
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
    out = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    for i, r in enumerate(out):
        r["_n"] = i
    return out


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
    """Record a decision, dated in Sao Paulo time: it applies from the NEXT pack (a rebuilt pack of today is not
    changed by a decision taken after it: review #10)."""
    if action not in ACTIONS:
        raise SystemExit(f"action must be one of {ACTIONS}")
    if action == "dismiss" and reason not in REASONS:
        raise SystemExit(f"a dismissal needs --reason, one of {REASONS}")
    x = find_candidate(cid)
    if not x:
        raise SystemExit(f"no candidate {cid}")
    rec = {"id": cid, "action": action, "reason": reason, "on": on or str(_brt_today()),
           "terms": x["terms"], "domains": x["domains"], "markets": markets or [m["price_ref"] for m in x["markets"]],
           "markets_corrected": bool(markets), "note": note, "version": x.get("version")}
    p = decisions_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    runlog.log(runlog.new_run_id(), "discovery:decide", "ok", candidate=cid, action=action, reason=reason)
    return rec


def status(x: dict, decs: list[dict], day: date, c: dict | None = None) -> dict | None:
    """The latest decision whose terms overlap this candidate's, made on or before `day`, and whether it hides it:
    dismiss -> hidden for dismiss_days unless sources >= dismiss_regrow x the level at dismissal; watch -> hidden for
    watch_days unless it grows watch_regrow x or turns sustained; promote -> shown as an update to the promoted theme."""
    c = c or cfg()
    ts = set(x["terms"])
    hits = [d for d in decs if _d(d["on"]) <= day and ts and len(ts & set(d["terms"])) / len(ts) >= c["term_overlap"]]
    if not hits:
        return None
    d = max(hits, key=lambda r: (r["on"], r.get("_n", 0)))           # same-day ties: the later record wins
    age = (day - _d(d["on"])).days
    hide = False
    if d["action"] == "dismiss":
        hide = age < c["dismiss_days"] and x["domains"] < c["dismiss_regrow"] * max(1, d["domains"])
    elif d["action"] == "watch":
        hide = age < c["watch_days"] and x["domains"] < c["watch_regrow"] * max(1, d["domains"]) and not x.get("sustained")
    return {"action": d["action"], "on": d["on"], "of": d["id"], "hidden": bool(hide), "reason": d.get("reason"),
            "markets": d.get("markets") if d.get("markets_corrected") else None}


# ------------------------------------------------------------------ context (code facts, point-in-time)
class Ctx:
    """One DuckDB connection and caches for a build (review #6)."""

    def __init__(self):
        try:
            self.con = store.connect()
        except Exception:  # noqa: BLE001
            self.con = None
        self.px: dict[tuple, pd.DataFrame | None] = {}
        self.cf: dict[tuple, dict | None] = {}

    def prices(self, ref: str, until: str) -> pd.DataFrame | None:
        k = (ref, until)
        if k not in self.px:
            df = None
            if self.con is not None:
                try:
                    df = self.con.execute("SELECT date, value, source_url FROM obs WHERE series_id = ? AND date <= ? "
                                          "ORDER BY date", [ref, until]).df()
                except Exception:  # noqa: BLE001
                    df = None
            if df is not None and len(df) >= 70:
                df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
                df["ret"] = df["value"].astype(float).pct_change()
                df = df.dropna(subset=["ret"]).reset_index(drop=True)
            else:
                df = None
            self.px[k] = df
        return self.px[k]

    def cftc(self, code: str, until: str) -> dict | None:
        k = (code, until)
        if k not in self.cf:
            r = None
            if self.con is not None:
                try:
                    df = self.con.execute("SELECT date, value FROM obs WHERE series_id = ? AND date <= ? ORDER BY date",
                                          [f"{code}.mm_net_pct_oi", until]).df()
                    if len(df) >= 52:
                        v = df["value"].astype(float).tail(156).to_numpy()
                        r = {"date": str(df["date"].iloc[-1])[:10], "net_pct_oi": round(float(v[-1]), 1),
                             "pct_3y": round(100 * float((v <= v[-1]).mean()), 0)}
                except Exception:  # noqa: BLE001
                    r = None
            self.cf[k] = r
        return self.cf[k]


def price_context(ref: str, t0: str, asof: str, c: dict | None = None, ctx: Ctx | None = None) -> dict | None:
    """Return on the first flagged day, the 5 sessions before, and since, in units of the 60-day EWMA vol known the
    day before t0; change in 20-day realised vol; the base rate of a daily move at least this large over the prior
    3 years. Descriptive co-movement, not a cause or forecast. No session yet since t0 (a weekend flag on Monday) is
    said so, with the move before (review #15)."""
    cx = (c or cfg())["context"]
    ctx = ctx or Ctx()
    df = ctx.prices(ref, asof)
    if df is None:
        return None
    before = df[df["date"] < t0]
    if len(before) < cx["vol_days"]:
        return None
    lam = 1 - 2 / (cx["vol_days"] + 1)
    vol = math.sqrt(float((before["ret"] ** 2).ewm(alpha=1 - lam).mean().iloc[-1]))
    pre = before.tail(cx["before_days"])
    out = {"price_ref": ref, "source_url": df["source_url"].iloc[-1],
           "before_move_sd": round(float((1 + pre["ret"]).prod() - 1) / (vol * math.sqrt(max(1, len(pre)))), 2) if vol else None,
           "rv20_before_pct": round(100 * float(before["ret"].tail(cx["realised_vol_days"]).std() * math.sqrt(252)), 1)}
    on = df[df["date"] >= t0]
    if not len(on) or vol <= 0:
        out["no_session_since"] = True
        return out
    r0 = float(on["ret"].iloc[0])
    since = on["value"].astype(float)
    base_vals = before["ret"].tail(252 * cx["base_rate_years"]).abs()
    out.update(t0_date=on["date"].iloc[0], t0_move_sd=round(r0 / vol, 2),
               since_pct=round(100 * (float(since.iloc[-1]) / float(before["value"].iloc[-1]) - 1), 2),
               since_date=df["date"].iloc[-1],
               base_rate_pct=round(100 * float((base_vals >= abs(r0)).mean()), 1) if len(base_vals) else None,
               rv20_now_pct=round(100 * float(df["ret"].tail(cx["realised_vol_days"]).std() * math.sqrt(252)), 1))
    return out


def cftc_context(ref: str, t0: str, asof: str, ctx: Ctx | None = None) -> dict | None:
    """Managed-money net (% of OI) and its 3-year percentile from the last report public before t0 vs the last one
    public before the pack (Tuesday report, Friday release: a report dated T is public from T + lag days; the
    06:18 pack of day D sees reports public by D - 1). No study links news attention to positioning."""
    from . import journal
    code = journal._cfg()["cftc_map"].get(ref)
    if not code:
        return None
    ctx = ctx or Ctx()
    try:
        lag = int(yaml.safe_load((ROOT / "config" / "monitor.yaml").read_text(encoding="utf-8"))
                  .get("consensus", {}).get("cftc_release_lag_days", 3))
    except Exception:  # noqa: BLE001
        lag = 3

    def at(public_by: date):
        return ctx.cftc(code, (public_by - timedelta(days=lag)).isoformat())

    pre, now = at(_d(t0) - timedelta(days=1)), at(_d(asof) - timedelta(days=1))
    if not pre and not now:
        return None
    return {"before": pre, "latest": now, "source_url": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"}


def first_day(x: dict, day: date, c: dict | None = None) -> str:
    """The first day the candidate's terms (>= term_overlap of them) were flagged, up to 14 days back."""
    c = c or cfg()
    ts = set(x["terms"])
    first = day
    for k in range(1, 15):
        p = cand_path(day - timedelta(days=k))
        if not p.exists():
            continue
        try:
            prev = json.loads(p.read_text(encoding="utf-8")).get("candidates", [])
        except ValueError:
            continue
        if any(ts and len(ts & set(y["terms"])) / len(ts) >= c["term_overlap"] for y in prev):
            first = day - timedelta(days=k)
    return str(first)


# ------------------------------------------------------------------ the fact-pack section
def _prev_pack(asof: date) -> date:
    """The previous weekday pack (Monday -> Friday)."""
    d = asof - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def pack_days(asof: date) -> list[date]:
    """Candidate days this pack covers: every UTC day since the previous weekday pack's (that pack showed its
    day - 1), up to asof - 1, so a Monday pack shows Friday, Saturday and Sunday (review #2)."""
    lo = _prev_pack(asof)
    ds = sorted(_d(p.stem) for p in (home() / "candidates").glob("*.json") if lo <= _d(p.stem) < asof)
    if not ds:                                          # nothing new: fall back to the latest list before asof
        prior = sorted(_d(p.stem) for p in (home() / "candidates").glob("*.json") if _d(p.stem) < asof)
        ds = prior[-1:]
    return ds


def build(asof: date, entries: list[dict] | None = None, decisions_through: date | None = None) -> tuple[dict, list[dict]]:
    """The section for the pack of `asof`. Decisions count through asof - 1 for the pack (the CLI passes asof)."""
    c = cfg()
    asof = _d(asof)
    days = pack_days(asof)
    if not days:
        return {"note": "no candidate list yet (discovery needs its first BigQuery runs and 28 stored days)"}, []
    merged: list[dict] = []
    meta = {}
    for d in days:
        raw = json.loads(cand_path(d).read_text(encoding="utf-8"))
        meta = raw
        for x in raw.get("candidates", []):
            ts = set(x["terms"])
            same = next((y for y in merged if ts and len(ts & set(y["terms"])) / max(1, min(len(ts), len(y["terms"])))
                         >= c["term_overlap"]), None)
            if same is None:
                merged.append({**x, "days": [str(d)]})
            else:                                       # the later day's record, keeping that it was new earlier
                was_new = same["new"] or x["new"]
                same.update({**x, "days": same["days"] + [str(d)], "new": was_new})
    decs = load_decisions()
    through = decisions_through or (asof - timedelta(days=1))
    ideas = [e for e in (entries or []) if e.get("status") in ("open", "idea") and e.get("book") != "example"]
    ctx = Ctx()
    shown, hidden = [], []
    for x in merged:
        st = status(x, decs, through, c)
        x = {**x, "decision": st}
        if st and st["hidden"]:
            hidden.append(x)
            continue
        if st and st.get("markets"):                    # Bernardo's correction of the markets touched
            x["markets"] = [m for m in x["markets"] if m["price_ref"] in st["markets"]] + \
                [{"price_ref": r, "name": c["markets"].get(r, {}).get("name", r), "title_share": None}
                 for r in st["markets"] if r not in {m["price_ref"] for m in x["markets"]}]
        shown.append(x)
    cap = int(c.get("max_shown", 80))
    with_ctx = int(c.get("max_with_context", 30))
    for i, x in enumerate(shown[:cap]):
        t0 = min([first_day(x, _d(x["day"]), c)] + x.get("days", []))
        x["first_day"] = t0
        x["context"] = []
        if i < with_ctx and not x["demoted"]:
            for m in x["markets"][:3]:
                x["context"].append({"price_ref": m["price_ref"], "name": m["name"],
                                     "price": price_context(m["price_ref"], t0, str(asof - timedelta(days=1)), c, ctx),
                                     "cftc": cftc_context(m["price_ref"], t0, str(asof), ctx),
                                     "ideas": [e["id"] for e in ideas if e.get("price_ref") == m["price_ref"]]})
    sec = {"days": [str(d) for d in days], "day": str(days[-1]), "version": meta.get("version"),
           "history_days": meta.get("history_days"), "candidates": shown[:cap], "more": max(0, len(shown) - cap),
           "hidden": len(hidden), "source_url": "https://www.gdeltproject.org/"}
    new_focus = [x for x in shown[:cap] if x["new"] and x["markets"] and not x["demoted"]
                 and not (x.get("decision") or {}).get("action")]
    alerts = [{"kind": "narrative_new", "severity": 1.0 + min(1.0, x["domains"] / 40), "id": x["id"],
               "text": f"New theme ({x['domains']} sources, {x['day']}): {x['label']}",
               "source_url": x["headlines"][0]["url"] if x["headlines"] else "https://www.gdeltproject.org/"}
              for x in sorted(new_focus, key=lambda x: -x["domains"])[: int(c.get("max_alerts", 3))]]
    return sec, alerts


def _md(s) -> str:
    return re.sub(r"[\[\]`|]", " ", html.unescape(str(s or ""))).strip()


def _ctx_line(cx: dict) -> str:
    p, f = cx.get("price"), cx.get("cftc")
    bits = []
    if p and not p.get("no_session_since"):
        br = f"{p['base_rate_pct']}%" if p.get("base_rate_pct") is not None else "n/a"
        bits.append(f"{cx['name']} {p['t0_move_sd']:+.1f} sd on {p['t0_date']} (a day that size or larger on {br} of "
                    f"days in 3 years), {p['before_move_sd']:+.1f} sd over the 5 sessions before, {p['since_pct']:+.1f}% "
                    f"since (to {p['since_date']}); 20-day vol {p['rv20_before_pct']}% -> {p['rv20_now_pct']}%")
    elif p:
        bits.append(f"{cx['name']}: no session since the first flag yet; {p['before_move_sd']:+.1f} sd over the 5 "
                    f"sessions before")
    else:
        bits.append(f"{cx['name']}: no stored prices")
    if f and f.get("before") and f.get("latest"):
        bits.append(f"CFTC managed money {f['before']['net_pct_oi']}% of OI ({int(f['before']['pct_3y'])}th pct, "
                    f"{f['before']['date']}) -> {f['latest']['net_pct_oi']}% ({int(f['latest']['pct_3y'])}th, {f['latest']['date']})")
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
    L += [f"Themes rising or new in English news titles on {', '.join(sec.get('days') or [sec['day']])} (GDELT GKG; words "
          f"and word pairs counted once per source, vs their own last {sec['history_days']} days). {len(cs)} shown"
          + (f" (+{sec['more']} more: `python -m pmstack discovery list`)" if sec.get("more") else "")
          + f", {sec['hidden']} hidden by your decisions. Review with `/narratives review`: promote, watch or dismiss. "
          "Price and CFTC lines are code facts around the first flagged day: with this many candidates, some large moves "
          "line up by chance.", ""]
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
                                              ("sustained", x.get("sustained"))) if on) or "flagged"
            dec = x.get("decision")
            extra = f"; your {dec['action']} of {dec['on']}" if dec else ""
            trk = f"; update to tracked `{x['tracked']}`" if x.get("tracked") else ""
            L.append(f"- `{x['id']}` {flags}: {_md(x['label'])} ({x['domains']} sources, {x['titles']} titles, score "
                     f"{x['score']:.1f}; terms: {', '.join(x['terms'][:6])}{trk}{extra})")
            for h in x["headlines"][:3]:
                L.append(f"  - [{_md(h['title'])}]({h['url']})")
            for cx in x.get("context", []):
                L.append(f"  - {_ctx_line(cx)}")
            if x["demoted"]:
                L.append(f"  - demoted: {'; '.join(x['demoted'])}")
        L += [""]
    return L


# ------------------------------------------------------------------ placebo and promotion draft
def placebo(days: int = 120) -> dict:
    """Score every stored day against its own prior days (as the live run would have) and count flags per day, by
    weekday: sizes the list honestly before anyone reads it (no titles needed)."""
    c = cfg()
    ds = stored_days()[-days:]
    per = []
    for d in ds:
        sc = score(d, pd.read_parquet(day_path(d)), history(d, int(c["history_days"])), c)
        if len(sc) and int(sc["history_days"].iloc[0]) >= c["min_history_days"]:
            per.append({"day": str(d), "weekday": d.strftime("%a"), "new": int(sc["new"].sum()),
                        "rising": int((sc["rising"] & ~sc["new"]).sum())})
    s = pd.DataFrame(per)
    if s.empty:
        return {"days": 0, "note": f"needs {c['min_history_days']}+ stored days"}
    return {"days": len(s), "new_median": float(s["new"].median()), "new_p90": float(s["new"].quantile(0.9)),
            "rising_median": float(s["rising"].median()), "rising_p90": float(s["rising"].quantile(0.9)),
            "by_weekday": s.groupby("weekday")[["new", "rising"]].median().to_dict(), "per_day": per[-14:]}


def draft_query(cid: str) -> str:
    """A title-phrase draft for a promoted candidate: its strongest terms as phrases, plus the press-release
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
    ls = sub.add_parser("list", help="candidates for a date's pack, with context (today's decisions applied)")
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
        asof = _d(a.date) if a.date else _brt_today()
        from . import journal
        sec, _ = build(asof, journal.load_all(), decisions_through=asof)
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
            r.pop("_n", None)
            print(json.dumps(r, ensure_ascii=False))
        return 0
    if a.cmd == "placebo":
        print(json.dumps(placebo(a.days), indent=1, default=str))
        return 0
    if a.cmd == "draft":
        print(draft_query(a.id))
        return 0
    return 2
