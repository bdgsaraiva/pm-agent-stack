"""GDELT through BigQuery: daily narrative attention from the Global Knowledge Graph, plus top headline links.

Why: the DOC 2.0 API (adapters/gdelt.py) answers GitHub's shared addresses with HTTP 429 and has been nearly
empty since 1 Oct 2026. The same GDELT data sit in Google's public BigQuery dataset `gdelt-bq.gdeltv2`, read here
with a service account (repo secrets GCP_SA_KEY = the JSON key, GCP_PROJECT_ID). The key is read from the
environment only, never printed or written to disk.

What a series measures (new instrument, so new series ids `gdeltbq:<qid>:*`; never mixed with the DOC series):
  - match: the narrative's frozen DOC query, applied to the words of each article's URL path (lower-cased, split
    on non-alphanumerics). Most news sites put the headline in the path; sites with numeric paths are missed.
    The GKG holds no article text, so full-text matching is impossible; title matching would need the large
    `Extras` column every day. URL-path matching reads two small columns, so the whole backfill fits the free tier.
  - gdeltbq:<qid>:count  matching web articles that day (GKG partition day = GDELT's ingest day, UTC)
  - gdeltbq:<qid>:share  matching / all web articles in the partition, in %
  - gdeltbq:<qid>:tone   average V2Tone of the matching articles (compare only with its own history)
  - gdeltbq:norm         all web articles in the partition
  Operators the GKG cannot express (sourcecountry:, sourcelang:, ...) are dropped and listed in the run log.

Headlines: for the last `headline_days` complete days, the top `headlines_per_day` distinct page titles per
narrative, ranked by how many articles carried the same title (syndication = prominence). Stored as title,
source domain, URL and date only (data/text/gdelt_headlines.parquet), never article text.

Budget (BigQuery sandbox: 1 TiB of queries a month free): every query is dry-run first; it runs only if its bytes
fit the per-query, per-run and per-month caps, with `maximum_bytes_billed` set. A chunk that does not fit is halved
down to one day, then the run stops. Bytes are logged per month in data/obs/gdelt_bq/_bytes.json (committed by the
daily job, so the monthly cap holds across runs). The daily run reads the new days only; the backfill goes back in
chunks, newest first, with what is left of the run's budget. Cite "The GDELT Project" with a link.
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yaml

from . import base

KIND = "obs"
TABLE = "gdelt-bq.gdeltv2.gkg_partitioned"
BQ_URL = "https://www.gdeltproject.org/data.html#googlebigquery"
GB = 1024 ** 3
TEXT_SOURCE = "gdelt_headlines"


# ------------------------------------------------------------------ query translation (DOC syntax -> URL-path regex)
_TOKEN = re.compile(r'-?"[^"]*"|-?\(|\)|[^\s()]+')


def norm_text(s: str) -> str:
    """The same normalisation BigQuery applies to the URL path: lower case, non-alphanumerics (except +) to spaces."""
    return " ".join(re.sub(r"[^a-z0-9+]+", " ", s.lower()).split())


_FIELDS = {"theme", "org"}          # GKG fields a query term can name: theme:ECON_OILPRICE, org:opec (underscores = spaces)


def _term(tok: str) -> str | None:
    """One query token -> a clause term: normalised words (title/URL), 'theme:NAME' or 'org:name'. None = dropped
    (operators the GKG cannot express, e.g. sourcecountry:). Normalised words never hold ':', so kinds never clash."""
    if ":" in tok and not tok.startswith('"'):
        key, val = tok.split(":", 1)
        if key.lower() == "theme" and re.fullmatch(r"[A-Za-z0-9_]+", val):
            return f"theme:{val.upper()}"
        if key.lower() == "org" and norm_text(val.replace("_", " ")):
            return f"org:{norm_text(val.replace('_', ' '))}"
        return None
    return norm_text(tok.strip('"')) or None


def parse_doc_query(q: str) -> dict:
    """Split a DOC 2.0 query into AND-ed clauses of OR-ed terms, exclusions, and operators the GKG cannot use.
    Supported: "phrase", bare word, (a OR b ...) blocks (not nested), -term / -"phrase", theme:NAME and org:name
    (GKG fields, in any clause), other key:value (dropped)."""
    toks = _TOKEN.findall(q)
    clauses, exclude, dropped = [], [], []
    i = 0
    while i < len(toks):
        t = toks[i]
        neg = t.startswith("-") and len(t) > 1
        body = t[1:] if neg else t
        if body == "(":
            j, group = i + 1, []
            while j < len(toks) and toks[j] != ")":
                if toks[j].upper() != "OR":
                    term = _term(toks[j])
                    if term:
                        group.append(term)
                    elif ":" in toks[j]:
                        dropped.append(toks[j])
                j += 1
            if group:
                (exclude.extend(group) if neg else clauses.append(group))
            i = j + 1
            continue
        if body.upper() == "OR" or body == ")":
            i += 1
            continue
        term = _term(body)
        if term is None:
            if ":" in body:
                dropped.append(t)
        else:
            (exclude.append(term) if neg else clauses.append([term]))
        i += 1
    return {"all": clauses, "none": exclude, "dropped": dropped}


def _split(terms: list[str]) -> dict[str, list[str]]:
    out = {"text": [], "theme": [], "org": []}
    for t in terms:
        if t.startswith(("theme:", "org:")):
            k, _, v = t.partition(":")
            out[k].append(v)
        else:
            out["text"].append(t)
    return out


def fields_used(qs: list[dict]) -> set[str]:
    """GKG fields (theme, org) any of these queries needs: only those columns are read (BigQuery bills by column)."""
    return {k for q in qs for c in q["_parsed"]["all"] + [q["_parsed"]["none"]] for k, v in _split(c).items()
            if v and k != "text"}


def _rx(terms: list[str]) -> str:
    """RE2 pattern over the space-padded normalised path. Terms hold only [a-z0-9+ ] after norm_text, so they are
    safe inside a raw SQL string literal."""
    alts = "|".join(re.escape(t) for t in sorted(set(terms), key=lambda x: (-len(x), x)))
    return f" ({alts}) "


def _list_rx(names: list[str]) -> str:
    """RE2 pattern for whole entries of a ';'-separated GKG list (themes: [A-Z0-9_]; orgs: normalised words)."""
    alts = "|".join(re.escape(t) for t in sorted(set(names), key=lambda x: (-len(x), x)))
    return f";({alts});"


def _any(terms: list[str], col: str) -> str:
    """SQL: any of these terms (words in `col`, themes in `th`, organisations in `og`)."""
    sp = _split(terms)
    ors = []
    if sp["text"]:
        ors.append(f"REGEXP_CONTAINS({col}, r'{_rx(sp['text'])}')")
    if sp["theme"]:
        ors.append(f"REGEXP_CONTAINS(th, r'{_list_rx(sp['theme'])}')")
    if sp["org"]:
        ors.append(f"REGEXP_CONTAINS(og, r'{_list_rx(sp['org'])}')")
    return ors[0] if len(ors) == 1 else "(" + " OR ".join(ors) + ")"


def sql_condition(parsed: dict, col: str = "s") -> str:
    if not parsed["all"]:
        return "FALSE"
    parts = [_any(c, col) for c in parsed["all"]]
    if parsed["none"]:
        parts.append(f"NOT {_any(parsed['none'], col)}")
    return "(" + " AND ".join(parts) + ")"


def _gkg_list(raw: str | None, kind: str) -> str:
    """Python twin of the SQL normalisation of the Themes / Organizations columns: ';a;b;'."""
    items = [x for x in str(raw or "").split(";") if x.strip()]
    items = [x.strip().upper() for x in items] if kind == "theme" else [norm_text(x) for x in items]
    return ";" + ";".join(items) + ";"


def matches(parsed: dict, url: str, title: str | None = None, themes: str | None = None,
            orgs: str | None = None) -> bool:
    """Python twin of sql_condition (tests and the headline audit). With a title: title or URL path, the two kept
    apart by a separator so a phrase never spans them. Themes / orgs: the raw GKG `Themes` / `Organizations` text."""
    s = f" {norm_text(re.sub(r'^https?://[^/]+', '', url))} "
    if title is not None:
        s = f" {norm_text(title)} ~{s}"
    th, og = _gkg_list(themes, "theme"), _gkg_list(orgs, "org")

    def any_of(terms):
        sp = _split(terms)
        return bool((sp["text"] and re.search(_rx(sp["text"]), s))
                    or (sp["theme"] and re.search(_list_rx(sp["theme"]), th))
                    or (sp["org"] and re.search(_list_rx(sp["org"]), og)))

    hit = all(any_of(c) for c in parsed["all"]) if parsed["all"] else False
    return hit and not (parsed["none"] and any_of(parsed["none"]))


_NORM = "TRIM(REGEXP_REPLACE(LOWER({x}), r'[^a-z0-9+]+', ' '))"
_PATH_X = "REGEXP_REPLACE(DocumentIdentifier, r'^https?://[^/]+', '')"
_TITLE_X = "IFNULL(REGEXP_EXTRACT(Extras, r'<PAGE_TITLE>(.*?)</PAGE_TITLE>'), '')"
_PATH = f"CONCAT(' ', {_NORM.format(x=_PATH_X)}, ' ')"
# title, a separator no normalised word can contain, then the path: a phrase can match in either, never across
_TITLE_OR_PATH = f"CONCAT(' ', {_NORM.format(x=_TITLE_X)}, ' ~ ', {_NORM.format(x=_PATH_X)}, ' ')"


# GKG lists as ';a;b;' (themes as stored; organisations lower-cased, non-alphanumerics to spaces, like norm_text)
_THEMES = "CONCAT(';', IFNULL(Themes, ''), ';')"
_ORGS = ("CONCAT(';', REGEXP_REPLACE(TRIM(REGEXP_REPLACE(LOWER(IFNULL(Organizations, '')), r'[^a-z0-9+;]+', ' ')), "
         "r' *; *', ';'), ';')")


def _text_expr(match: str) -> str:
    return _TITLE_OR_PATH if match == "title_or_path" else _PATH


def _cols(qs: list[dict]) -> str:
    """Extra GKG columns, only when a query names a theme or an organisation (BigQuery bills by column)."""
    f = fields_used(qs)
    return (f", {_THEMES} AS th" if "theme" in f else "") + (f", {_ORGS} AS og" if "org" in f else "")


def series_sql(qs: list[dict], table: str = TABLE, match: str = "path") -> str:
    cols = []
    for q in qs:
        c = sql_condition(q["_parsed"])
        cols.append(f"COUNTIF({c}) AS `{q['id']}__n`, AVG(IF({c}, tone, NULL)) AS `{q['id']}__tone`")
    return (f"WITH a AS (SELECT DATE(_PARTITIONTIME) AS day, {_text_expr(match)} AS s{_cols(qs)}, "
            f"SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64) AS tone FROM `{table}` "
            f"WHERE _PARTITIONTIME >= TIMESTAMP(@start) AND _PARTITIONTIME < TIMESTAMP(@stop) "
            f"AND SourceCollectionIdentifier = 1) "
            f"SELECT day, COUNT(*) AS n_all, {', '.join(cols)} FROM a GROUP BY day ORDER BY day")


def headlines_sql(qs: list[dict], table: str = TABLE, match: str = "path") -> str:
    tags = ", ".join(f"IF({sql_condition(q['_parsed'])}, '{q['id']}', NULL)" for q in qs)
    return (f"WITH a AS (SELECT DATE(_PARTITIONTIME) AS day, DocumentIdentifier AS url, SourceCommonName AS src, "
            f"REGEXP_EXTRACT(Extras, r'<PAGE_TITLE>(.*?)</PAGE_TITLE>') AS title, {_text_expr(match)} AS s{_cols(qs)} "
            f"FROM `{table}` "
            f"WHERE _PARTITIONTIME >= TIMESTAMP(@start) AND _PARTITIONTIME < TIMESTAMP(@stop) "
            f"AND SourceCollectionIdentifier = 1), "
            f"m AS (SELECT day, url, src, title, qid FROM a, UNNEST([{tags}]) AS qid "
            f"WHERE qid IS NOT NULL AND title IS NOT NULL AND TRIM(title) != ''), "
            f"g AS (SELECT day, qid, LOWER(TRIM(title)) AS k, ANY_VALUE(title) AS title, MIN(url) AS url, "
            f"ANY_VALUE(src) AS src, COUNT(*) AS copies FROM m GROUP BY day, qid, k) "
            f"SELECT day, qid, title, url, src, copies FROM g WHERE TRUE "      # BigQuery: QUALIFY needs a WHERE
            f"QUALIFY ROW_NUMBER() OVER (PARTITION BY day, qid ORDER BY copies DESC, k) <= @top")


# ------------------------------------------------------------------ BigQuery access (monkeypatched in tests)
def _client(cfg: dict):
    """BigQuery client from the GCP_SA_KEY secret (service-account JSON in the environment). None when unset."""
    raw = os.environ.get("GCP_SA_KEY")
    if not raw:
        return None
    from google.cloud import bigquery
    from google.oauth2 import service_account
    info = json.loads(raw)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/bigquery"])
    return bigquery.Client(project=os.environ.get("GCP_PROJECT_ID") or info.get("project_id"), credentials=creds)


def _query(client, sql: str, params: dict, dry_run: bool, max_bytes: int | None = None):
    """Dry run -> bytes the query would read. Real run -> (rows as list of dicts, bytes billed)."""
    from google.cloud import bigquery
    qp = [bigquery.ScalarQueryParameter(k, "INT64" if isinstance(v, int) else "STRING", v) for k, v in params.items()]
    jc = bigquery.QueryJobConfig(query_parameters=qp, dry_run=dry_run, use_query_cache=False)
    if not dry_run:
        jc.maximum_bytes_billed = int(max_bytes)
    job = client.query(sql, job_config=jc)
    if dry_run:
        return int(job.total_bytes_processed or 0)
    rows = [dict(r.items()) for r in job.result(timeout=600)]
    return rows, int(job.total_bytes_billed or job.total_bytes_processed or 0)


def _stored_range(sid: str) -> tuple[date | None, date | None]:
    from .. import store
    try:
        r = store.connect().execute("SELECT min(date), max(date) FROM obs WHERE series_id = ?", [sid]).fetchone()
    except Exception:  # noqa: BLE001  (no obs files yet)
        return None, None
    to_d = lambda x: None if x is None else pd.Timestamp(x).date()  # noqa: E731
    return to_d(r[0]), to_d(r[1])


def _headline_days_stored(match: str = "path", qids: set[str] | None = None) -> set[date]:
    """Days that already have headlines drawn with this match mode (rows without a mode tag are 'path'), for any of
    these query ids when given (an instrument with its own definitions never counts another's headlines)."""
    from .. import store
    p = store.DATA / "text" / f"{TEXT_SOURCE}.parquet"
    if not p.exists():
        return set()
    t = pd.read_parquet(p, columns=["item_id", "published", "summary"])
    keep = t["summary"].fillna("").astype(str).str.extract(r"match=(\w+)")[0].fillna("path") == match
    if qids is not None:
        keep &= t["item_id"].astype(str).str.split("|").str[0].isin(qids)
    return set(pd.to_datetime(t.loc[keep, "published"], utc=True).dt.date)


# ------------------------------------------------------------------ byte ledger
def _ledger_path() -> Path:
    from .. import store
    return store.DATA / "obs" / "gdelt_bq" / "_bytes.json"


def load_ledger() -> dict:
    try:
        return json.loads(_ledger_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"months": {}, "log": []}


def _save_ledger(led: dict) -> None:
    p = _ledger_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    led["log"] = led["log"][-300:]
    p.write_text(json.dumps(led, indent=1, sort_keys=True), encoding="utf-8")


class Budget:
    def __init__(self, cfg: dict, led: dict, month: str):
        self.q = float(cfg.get("max_gb_query", 60)) * GB
        self.run = float(cfg.get("max_gb_run", 150)) * GB
        self.month_cap = float(cfg.get("max_gb_month", 800)) * GB
        self.led, self.month, self.used = led, month, 0

    def room(self) -> float:
        return min(self.q, self.run - self.used, self.month_cap - self.led["months"].get(self.month, 0))

    def spend(self, n: int, kind: str, start: date, days: int, at: str) -> None:
        self.used += n
        self.led["months"][self.month] = self.led["months"].get(self.month, 0) + n
        self.led["log"].append({"at": at, "kind": kind, "start": str(start), "days": days, "gb": round(n / GB, 3)})


# ------------------------------------------------------------------ fetch
def load_queries(cfg: dict) -> list[dict]:
    """Queries: this block's own, or the frozen DOC list (`queries_from: gdelt`). Retired queries are skipped;
    a `bq_query:` key overrides the DOC query for this instrument. Own queries carry `narrative:` (the narrative id
    they measure) and may name GKG themes and organisations (theme:NAME, org:name)."""
    qs = cfg.get("queries")
    if qs is None:
        root = Path(__file__).resolve().parents[2]
        src = yaml.safe_load((root / "config" / "sources.yaml").read_text(encoding="utf-8"))
        qs = (src.get(cfg.get("queries_from", "gdelt")) or {}).get("queries", [])
    out = []
    for q in qs:
        if q.get("retired"):
            continue
        out.append({**q, "_parsed": parse_doc_query(q.get("bq_query") or q["query"])})
    return out


def _chunks_forward(a: date, b: date, n: int):
    d = a
    while d <= b:
        e = min(b, d + timedelta(days=n - 1))
        yield d, e
        d = e + timedelta(days=1)


def _chunks_backward(a: date, b: date, n: int):
    """From b back to a, newest chunk first."""
    e = b
    while e >= a:
        s = max(a, e - timedelta(days=n - 1))
        yield s, e
        e = s - timedelta(days=1)


def series_rows(rows: list[dict], qs: list[dict], fetched, prefix: str = "gdeltbq",
                source: str = "gdelt_bq") -> list[dict]:
    out = []
    for r in rows:
        d = pd.Timestamp(r["day"]).date()
        n_all = float(r.get("n_all") or 0)
        b = {"source": source, "date": d, "freq": "daily", "fetched_at": fetched, "source_url": BQ_URL}
        if n_all <= 0:
            continue
        out.append({**b, "series_id": f"{prefix}:norm", "name": "GDELT GKG web articles (BigQuery)",
                    "value": n_all, "unit": "articles"})
        for q in qs:
            n = r.get(f"{q['id']}__n")
            if n is None:
                continue
            out.append({**b, "series_id": f"{prefix}:{q['id']}:count", "name": f"{q['name']} (articles, GKG)",
                        "value": float(n), "unit": "articles"})
            out.append({**b, "series_id": f"{prefix}:{q['id']}:share", "name": f"{q['name']} (share of coverage, GKG)",
                        "value": 100.0 * float(n) / n_all, "unit": "pct"})
            t = r.get(f"{q['id']}__tone")
            if t is not None and n:
                out.append({**b, "series_id": f"{prefix}:{q['id']}:tone", "name": f"{q['name']} (tone, GKG)",
                            "value": float(t), "unit": "tone"})
    return out


def headline_rows(rows: list[dict], fetched, match: str = "path") -> pd.DataFrame:
    import html
    out = []
    for r in rows:
        d = pd.Timestamp(r["day"]).date()
        title = " ".join(html.unescape(str(r["title"])).split())[:300]
        url = str(r["url"])
        if not url.startswith("http"):
            continue
        mode = "" if match == "path" else f"{match}|"          # a new match mode never collides with stored ids
        out.append({"source": TEXT_SOURCE, "item_id": f"{r['qid']}|{d}|{mode}{url}", "title": title, "url": url,
                    "published": pd.Timestamp(d, tz="UTC"),
                    "summary": f"src={r.get('src') or ''}; copies={int(r.get('copies') or 1)}; match={match}",
                    "fetched_at": fetched})
    return pd.DataFrame(out, columns=["source", "item_id", "title", "url", "published", "summary", "fetched_at"])


def _run_chunk(client, sql, params, kind, start, stop, budget, at, errors) -> list[dict] | None:
    """Dry-run, check the budget, run. None when it does not fit (caller halves the chunk)."""
    need = _query(client, sql, params, dry_run=True)
    if need > budget.room():
        return None
    rows, billed = _query(client, sql, params, dry_run=False, max_bytes=int(min(budget.room(), need * 1.25 + 50e6)))
    budget.spend(billed, kind, start, (stop - start).days + 1, at)
    return rows


def fetch(cfg: dict, since=None) -> pd.DataFrame:
    fetched = base.now_utc()
    errors: list[str] = []
    out = pd.DataFrame()
    out.attrs["errors"] = errors
    client = _client(cfg)
    if client is None:
        out.attrs["skipped"] = "GCP_SA_KEY not set (BigQuery runs in GitHub Actions only)"
        return out
    qs = load_queries(cfg)
    dropped = sorted({d for q in qs for d in q["_parsed"]["dropped"]})
    if dropped:
        out.attrs["notes"] = [f"operators not available in the GKG, dropped: {', '.join(dropped)}"]
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()          # complete UTC days only
    first_allowed = date.fromisoformat(str(cfg.get("backfill_start", "2025-08-01")))
    deadline = time.monotonic() + float(cfg.get("max_minutes", 10)) * 60
    led = load_ledger()
    budget = Budget(cfg, led, f"{yesterday:%Y-%m}")
    at = fetched.isoformat()
    n_days = int(cfg.get("days_per_query", 14))
    prefix, match = str(cfg.get("series_prefix", "gdeltbq")), str(cfg.get("match", "path"))
    first, last = _stored_range(f"{prefix}:norm")
    plan = []
    if last is None:
        plan += [("back", s, e) for s, e in _chunks_backward(first_allowed, yesterday, n_days)]
    else:
        start = max(first_allowed, last - timedelta(days=int(cfg.get("overlap_days", 3))))
        plan += [("new", s, e) for s, e in _chunks_forward(start, yesterday, n_days)]
        if first is not None and first > first_allowed:
            plan += [("back", s, e) for s, e in _chunks_backward(first_allowed, first - timedelta(days=1), n_days)]
    rows: list[dict] = []
    sql = series_sql(qs, cfg.get("table", TABLE), match)
    heads = headline_rows([], fetched)

    def run_series(queue: list) -> bool:
        """Run chunks in order, halving any that do not fit. False when the run must stop (budget or time)."""
        nonlocal rows
        stop_reason, s = None, None
        while queue:
            kind, s, e = queue.pop(0)
            if time.monotonic() > deadline:
                stop_reason = f"time budget ({cfg.get('max_minutes', 10)} min) used up"
                break
            got = _run_chunk(client, sql, {"start": str(s), "stop": str(e + timedelta(days=1))}, f"series:{kind}",
                             s, e, budget, at, errors)
            if got is None:
                if s < e:                                   # halve: newest half first for the backfill
                    mid = s + timedelta(days=((e - s).days) // 2)
                    halves = [(kind, s, mid), (kind, mid + timedelta(days=1), e)]
                    queue[:0] = halves[::-1] if kind == "back" else halves
                    continue
                stop_reason = (f"byte budget: one day ({s}) does not fit what is left "
                               f"({max(0.0, budget.room()) / GB:.1f} GB)")
                break
            rows += series_rows(got, qs, fetched, prefix, str(cfg.get("store_key", "gdelt_bq")))
        if stop_reason:
            errors.append(f"{stop_reason}; {len(queue) + 1} chunk(s) left, oldest day "
                          f"{min([s] + [x[1] for x in queue])}; they continue on the next run")
            return False
        return True

    try:
        # order: new days, then headlines for recent days that have none, then the backfill with what is left
        ok = run_series([p for p in plan if p[0] == "new"])
        hd = int(cfg.get("headline_days", 3))
        have = _headline_days_stored(match, {q["id"] for q in qs} if cfg.get("queries") is not None else None)
        want = [yesterday - timedelta(days=k) for k in range(hd) if yesterday - timedelta(days=k) not in have]
        if ok and want and time.monotonic() < deadline:
            a, b = min(want), max(want)
            hsql = headlines_sql(qs, cfg.get("table", TABLE), match)
            got = _run_chunk(client, hsql, {"start": str(a), "stop": str(b + timedelta(days=1)),
                                            "top": int(cfg.get("headlines_per_day", 5))}, "headlines", a, b, budget,
                             at, errors)
            if got is None:
                errors.append(f"headlines {a}..{b}: byte budget left ({max(0.0, budget.room()) / GB:.1f} GB) too small")
            else:
                heads = headline_rows(got, fetched, match)
        if ok:
            run_series([p for p in plan if p[0] == "back"])
    except Exception as ex:  # noqa: BLE001  (what was fetched is kept; the error is logged)
        errors.append(f"{type(ex).__name__}: {str(ex)[:300]}")
    finally:
        _save_ledger(led)
    out = pd.DataFrame(rows)
    out.attrs["errors"] = errors
    out.attrs["text"] = {TEXT_SOURCE: heads}
    out.attrs["bytes_gb"] = round(budget.used / GB, 3)
    out.attrs["month_gb"] = round(led["months"].get(budget.month, 0) / GB, 3)
    if dropped:
        out.attrs["notes"] = [f"operators not available in the GKG, dropped: {', '.join(dropped)}"]
    return out
