"""Measure candidate narrative definitions on the GDELT GKG (BigQuery) before freezing any of them.

Why: a narrative series under 20 articles a day reads "insufficient coverage" (consensus.min_daily_articles). Before a
new definition is frozen, its articles a day, a random sample of its titles and the bytes it costs are measured here,
on the same table, match and byte ledger the daily fetch uses (adapters/gdelt_bq.py). Runs in GitHub Actions only
(.github/workflows/narratives-measure.yml), where the BigQuery key lives.

Spec (YAML): windows [[start, stop], ...] (inclusive days), probe_day, sample_window, sample_titles, enrich_window,
include_frozen (the frozen DOC queries, matched in title or URL path, as the baseline), candidates [{id, narrative,
query}]. Output: JSON with bytes per column, articles a day per candidate and window (mean, weekday mean, weekend
mean, min), sampled titles (distinct titles, drawn by a hash: reproducible, not ranked) and, for each frozen query,
the GKG themes most over-represented in its matches (lift = share among matches / share among all articles).
Titles, source domains and URLs only; never article text.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yaml

from .adapters import gdelt_bq as bq

ROOT = Path(__file__).resolve().parents[1]
PROBE_COLS = ["SourceCollectionIdentifier", "DocumentIdentifier", "V2Tone", "Extras", "Themes", "V2Themes",
              "Organizations", "V2Organizations", "Locations", "GCAM"]


def load_spec(path: str | Path) -> dict:
    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    cands = []
    if spec.get("include_frozen", True):
        cands += [{**q, "narrative": q["id"], "baseline": True} for q in bq.load_queries({"queries_from": "gdelt"})]
    for c in spec.get("candidates", []):
        cands.append({**c, "_parsed": bq.parse_doc_query(c["query"])})
    ids = [c["id"] for c in cands]
    assert len(ids) == len(set(ids)), "candidate ids must be unique"
    spec["_cands"] = cands
    return spec


def _where(table: str) -> str:
    return (f"FROM `{table}` WHERE _PARTITIONTIME >= TIMESTAMP(@start) AND _PARTITIONTIME < TIMESTAMP(@stop) "
            f"AND SourceCollectionIdentifier = 1")


def sample_sql(qs: list[dict], table: str = bq.TABLE) -> str:
    """Distinct titles per candidate, drawn by a hash of the title (reproducible, not ranked by prominence)."""
    tags = ", ".join(f"IF({bq.sql_condition(q['_parsed'])}, '{q['id']}', NULL)" for q in qs)
    return (f"WITH a AS (SELECT DocumentIdentifier AS url, SourceCommonName AS src, "
            f"REGEXP_EXTRACT(Extras, r'<PAGE_TITLE>(.*?)</PAGE_TITLE>') AS title, {bq._TITLE_OR_PATH} AS s"
            f"{bq._cols(qs)} {_where(table)}), "
            f"m AS (SELECT qid, title, url, src FROM a, UNNEST([{tags}]) AS qid "
            f"WHERE qid IS NOT NULL AND title IS NOT NULL AND TRIM(title) != ''), "
            f"g AS (SELECT qid, LOWER(TRIM(title)) AS k, ANY_VALUE(title) AS title, MIN(url) AS url, "
            f"ANY_VALUE(src) AS src, COUNT(*) AS copies FROM m GROUP BY qid, k) "
            f"SELECT qid, title, url, src, copies FROM g WHERE TRUE "
            f"QUALIFY ROW_NUMBER() OVER (PARTITION BY qid ORDER BY FARM_FINGERPRINT(k)) <= @top")


def enrich_sql(qs: list[dict], table: str = bq.TABLE) -> str:
    """For each query: the GKG themes most over-represented among its matches (at least 5 matching articles)."""
    tags = ", ".join(f"IF({bq.sql_condition(q['_parsed'])}, '{q['id']}', NULL)" for q in qs)
    og = f", {bq._ORGS} AS og" if "org" in bq.fields_used(qs) else ""
    return (f"WITH a AS (SELECT {bq._TITLE_OR_PATH} AS s, {bq._THEMES} AS th{og} {_where(table)}), "
            f"t AS (SELECT qid, th FROM a, UNNEST([{tags}]) AS qid WHERE qid IS NOT NULL), "
            f"qn AS (SELECT qid, COUNT(*) AS n_q FROM t GROUP BY qid), "
            f"qt AS (SELECT qid, theme, COUNT(*) AS n_in FROM t, UNNEST(SPLIT(th, ';')) AS theme "
            f"WHERE theme != '' GROUP BY qid, theme), "
            f"base AS (SELECT theme, COUNT(*) AS n_th FROM a, UNNEST(SPLIT(th, ';')) AS theme "
            f"WHERE theme != '' GROUP BY theme), "
            f"tot AS (SELECT COUNT(*) AS n_all FROM a) "
            f"SELECT qid, theme, n_in, n_q, n_th, n_all FROM qt JOIN qn USING (qid) JOIN base USING (theme) "
            f"CROSS JOIN tot WHERE n_in >= 5 AND n_in * n_all > 2 * n_q * n_th "
            f"QUALIFY ROW_NUMBER() OVER (PARTITION BY qid ORDER BY "
            f"(n_in / n_q) * LN((n_in * n_all) / (n_q * n_th)) DESC) <= @top")


def probe_sql(col: str, table: str = bq.TABLE) -> str:
    return f"SELECT {col} FROM `{table}` WHERE _PARTITIONTIME >= TIMESTAMP(@start) AND _PARTITIONTIME < TIMESTAMP(@stop)"


def summarise(rows: list[dict], cands: list[dict]) -> dict:
    """Articles a day per candidate over one window: mean, weekday mean, weekend mean, min, share of all (%)."""
    df = pd.DataFrame(rows)
    if df.empty:
        return {}
    df["wd"] = pd.to_datetime(df["day"]).dt.weekday < 5
    out = {"_n_all_mean": round(float(df.n_all.mean()), 0), "_days": len(df)}
    for c in cands:
        col = f"{c['id']}__n"
        if col not in df:
            continue
        s = df[col].astype(float)
        out[c["id"]] = {"mean": round(float(s.mean()), 1), "weekday": round(float(s[df.wd].mean()), 1) if df.wd.any() else None,
                        "weekend": round(float(s[~df.wd].mean()), 1) if (~df.wd).any() else None,
                        "min": round(float(s.min()), 0), "share_pct": round(float(100 * s.sum() / df.n_all.sum()), 4)}
    return out


def run(spec_path: str, out_path: str, max_gb: float = 60.0) -> dict:
    spec = load_spec(spec_path)
    cands = spec["_cands"]
    client = bq._client({})
    if client is None:
        raise SystemExit("GCP_SA_KEY not set: the measurement runs in GitHub Actions only")
    src = yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))["gdelt_bq"]
    table = src.get("table", bq.TABLE)
    led = bq.load_ledger()
    month = f"{datetime.now(timezone.utc):%Y-%m}"
    budget = bq.Budget({"max_gb_query": min(max_gb, float(src.get("max_gb_query", 60))), "max_gb_run": max_gb,
                        "max_gb_month": src.get("max_gb_month", 800)}, led, month)
    at, errors = datetime.now(timezone.utc).isoformat(), []
    res: dict = {"spec": str(spec_path), "at": at, "table": table, "errors": errors,
                 "candidates": [{k: c.get(k) for k in ("id", "narrative", "query", "baseline")} for c in cands]}
    try:
        # 1. bytes per column for one day (dry runs are free)
        pd_ = date.fromisoformat(str(spec["probe_day"]))
        prm = {"start": str(pd_), "stop": str(pd_ + timedelta(days=1))}
        res["probe_gb_per_day"] = {c: round(bq._query(client, probe_sql(c, table), prm, dry_run=True) / bq.GB, 4)
                                   for c in PROBE_COLS}
        res["probe_gb_per_day"]["candidates_series_sql"] = round(
            bq._query(client, bq.series_sql(cands, table, "title_or_path"), prm, dry_run=True) / bq.GB, 4)
        new_only = [c for c in cands if not c.get("baseline")]
        if new_only:
            res["probe_gb_per_day"]["new_candidates_series_sql"] = round(
                bq._query(client, bq.series_sql(new_only, table, "title_or_path"), prm, dry_run=True) / bq.GB, 4)
        # 2. articles a day per candidate, per window
        res["windows"] = {}
        sql = bq.series_sql(cands, table, "title_or_path")
        for a, b in spec["windows"]:
            a, b = date.fromisoformat(str(a)), date.fromisoformat(str(b))
            got = bq._run_chunk(client, sql, {"start": str(a), "stop": str(b + timedelta(days=1))}, "measure:series",
                                a, b, budget, at, errors)
            if got is None:
                errors.append(f"window {a}..{b} does not fit the byte budget")
                continue
            res["windows"][f"{a}..{b}"] = summarise(got, cands)
        # 3. sampled titles
        a, b = (date.fromisoformat(str(x)) for x in spec["sample_window"])
        got = bq._run_chunk(client, sample_sql(cands, table), {"start": str(a), "stop": str(b + timedelta(days=1)),
                                                               "top": int(spec.get("sample_titles", 12))},
                            "measure:samples", a, b, budget, at, errors)
        res["samples"] = {}
        for r in got or []:
            res["samples"].setdefault(r["qid"], []).append(
                {"title": " ".join(str(r["title"]).split())[:200], "src": r.get("src"), "url": r["url"],
                 "copies": int(r.get("copies") or 1)})
        if got is None:
            errors.append("samples do not fit the byte budget")
        # 4. themes over-represented in each frozen query's matches
        if spec.get("enrich_window"):
            a, b = (date.fromisoformat(str(x)) for x in spec["enrich_window"])
            base = [c for c in cands if c.get("baseline")]
            got = bq._run_chunk(client, enrich_sql(base, table), {"start": str(a), "stop": str(b + timedelta(days=1)),
                                                                  "top": int(spec.get("enrich_top", 25))},
                                "measure:enrich", a, b, budget, at, errors)
            res["enrich"] = {}
            for r in got or []:
                lift = (r["n_in"] * r["n_all"]) / (r["n_q"] * r["n_th"])
                res["enrich"].setdefault(r["qid"], []).append(
                    {"theme": r["theme"], "in_matches_pct": round(100 * r["n_in"] / r["n_q"], 1),
                     "lift": round(lift, 1), "theme_per_day": round(r["n_th"] / ((b - a).days + 1), 0)})
            if got is None:
                errors.append("theme enrichment does not fit the byte budget")
    except Exception as ex:  # noqa: BLE001  (what was measured is kept)
        errors.append(f"{type(ex).__name__}: {str(ex)[:400]}")
    finally:
        bq._save_ledger(led)
    res["bytes_gb"] = round(budget.used / bq.GB, 3)
    res["month_gb"] = round(led["months"].get(month, 0) / bq.GB, 3)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    Path(out_path).with_suffix(".md").write_text(report(res), encoding="utf-8")
    return res


def report(res: dict) -> str:
    """Markdown summary: one row per candidate with articles a day in each window."""
    wins = list(res.get("windows", {}))
    L = [f"# Narrative measurement {res['at'][:10]}", "",
         f"Spec `{res['spec']}`; table `{res['table']}`; title-or-URL-path match; bytes this run "
         f"{res.get('bytes_gb')} GB (month {res.get('month_gb')} GB). Errors: {res.get('errors') or 'none'}.", "",
         "Bytes per day by column (dry run): " + ", ".join(f"{k} {v}" for k, v in (res.get("probe_gb_per_day") or {}).items()),
         "", "| Candidate | Narrative | " + " | ".join(f"{w} mean (wkday / wkend, min)" for w in wins) + " |",
         "|---|---|" + "---:|" * len(wins)]
    for c in res["candidates"]:
        cells = []
        for w in wins:
            m = res["windows"][w].get(c["id"])
            cells.append("-" if not m else f"{m['mean']} ({m['weekday']} / {m['weekend']}, {m['min']:.0f})")
        L.append(f"| {c['id']}{' (frozen)' if c.get('baseline') else ''} | {c['narrative']} | " + " | ".join(cells) + " |")
    return "\n".join(L) + "\n"
