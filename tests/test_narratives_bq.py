"""Narratives on BigQuery (GDELT GKG), headline links and the narrative tracker (offline: BigQuery is faked)."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd

from pmstack import consensus, store
from pmstack.adapters import gdelt_bq as bq


# ------------------------------------------------------------------ query translation
def test_doc_queries_translate_to_url_path_matches():
    p = bq.parse_doc_query('("Strait of Hormuz" OR "Iranian oil" OR "Iran oil exports" OR "Persian Gulf tanker")')
    assert p["all"] == [["strait of hormuz", "iranian oil", "iran oil exports", "persian gulf tanker"]]
    assert bq.matches(p, "https://www.reuters.com/business/energy/tanker-traffic-strait-of-hormuz-slows-2026-10-14/")
    assert not bq.matches(p, "https://example.com/strait-hormuz-something")          # phrase, not loose words
    assert not bq.matches(p, "https://strait-of-hormuz.com/12345")                    # the domain is not the path

    g = bq.parse_doc_query('("gasoline prices" OR "gas prices" OR "pump prices") sourcecountry:US')
    assert g["dropped"] == ["sourcecountry:US"] and g["all"] == [["gasoline prices", "gas prices", "pump prices"]]

    o = bq.parse_doc_query('OPEC ("output cut" OR "production cut" OR "supply cut" OR "output quota")')
    assert bq.matches(o, "https://x.com/news/opec-agrees-output-cut-of-1m-bpd")
    assert not bq.matches(o, "https://x.com/news/output-cut-at-steel-mill")         # both clauses needed
    assert not bq.matches(o, "https://x.com/news/opec-meeting-delayed")

    e = bq.parse_doc_query('"oil glut" -"no oil glut"')
    assert bq.matches(e, "https://x.com/oil-glut-looms") and not bq.matches(e, "https://x.com/no-oil-glut-yet")


def test_sql_literals_hold_only_safe_characters():
    qs = bq.load_queries({"queries_from": "gdelt"})
    assert qs and all(not q.get("retired") for q in qs)
    assert "opec_supply_v1" not in {q["id"] for q in qs} and "opec_supply_v2" in {q["id"] for q in qs}
    sql = bq.series_sql(qs)
    for lit in re.findall(r"r'([^']*)'", sql):
        assert re.fullmatch(r"[a-z0-9+ ()|\\^:/\[\]?.*_-]*", lit), lit
    assert "_PARTITIONTIME >= TIMESTAMP(@start)" in sql and "gkg_partitioned" in sql
    assert "Extras" not in sql                     # path-only series never read the title column
    assert "Extras" in bq.headlines_sql(qs) and "Extras" in bq.series_sql(qs, match="title_or_path")
    for lit in re.findall(r"r'([^']*)'", bq.series_sql(qs, match="title_or_path")):
        assert "'" not in lit


def test_title_or_path_matching_never_spans_title_and_path():
    p = bq.parse_doc_query('("oil glut" OR "crude glut")')
    assert bq.matches(p, "https://x.com/markets/12345", title="Analysts warn of an oil glut in 2027")
    assert not bq.matches(p, "https://x.com/markets/12345")                       # path alone has nothing
    assert not bq.matches(p, "https://x.com/glut-ahead", title="Prices of crude oil")   # "oil" + "glut" across the two
    assert bq.matches(p, "https://x.com/oil-glut-ahead", title="Markets today")


# ------------------------------------------------------------------ fake BigQuery
class FakeBQ:
    """Dry runs cost `gb_per_day` per partition day; real runs return one row per day (Hormuz = 1% of articles)."""

    def __init__(self, gb_per_day=2.0):
        self.gb, self.runs, self.dry = gb_per_day, [], []

    def query(self, client, sql, params, dry_run, max_bytes=None):
        a, b = date.fromisoformat(params["start"]), date.fromisoformat(params["stop"])
        days = (b - a).days
        cost = int(self.gb * days * bq.GB)
        if dry_run:
            self.dry.append((a, b))
            return cost
        assert max_bytes is not None and max_bytes >= cost      # maximum_bytes_billed always set, never below need
        self.runs.append((a, b, "Extras" in sql))
        if "Extras" in sql:
            return [{"day": a + timedelta(days=k), "qid": "hormuz_iran_v1", "title": f"Tanker traffic &amp; Hormuz {k}",
                     "url": f"https://news.example.com/hormuz-{k}", "src": "news.example.com", "copies": 9 - k}
                    for k in range(days)], cost
        rows = []
        for k in range(days):
            r = {"day": a + timedelta(days=k), "n_all": 100000}
            for q in bq.load_queries({"queries_from": "gdelt"}):
                r[f"{q['id']}__n"] = 1000 if q["id"] == "hormuz_iran_v1" else 40
                r[f"{q['id']}__tone"] = -2.5
            rows.append(r)
        return rows, cost


def _setup(monkeypatch, tmp_path, fake):
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    monkeypatch.setattr(bq, "_client", lambda cfg: object())
    monkeypatch.setattr(bq, "_query", fake.query)


def test_no_key_means_skipped(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    monkeypatch.delenv("GCP_SA_KEY", raising=False)
    out = bq.fetch({"queries_from": "gdelt"})
    assert out.empty and "GCP_SA_KEY" in out.attrs["skipped"]


def test_budget_halves_chunks_logs_bytes_and_stores_headlines(monkeypatch, tmp_path):
    fake = FakeBQ(gb_per_day=2.0)
    _setup(monkeypatch, tmp_path, fake)
    y = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    cfg = {"queries_from": "gdelt", "backfill_start": str(y - timedelta(days=59)), "days_per_query": 14,
           "max_gb_query": 10, "max_gb_run": 50, "max_gb_month": 800, "headline_days": 3, "headlines_per_day": 5}
    out = bq.fetch(cfg)
    assert all(d.days <= 5 for d in (b - a for a, b, _ in fake.runs))       # 14-day chunks (28 GB) halved to fit 10 GB
    series_gb = sum(2.0 * (b - a).days for a, b, h in fake.runs if not h)
    assert series_gb <= 50 and any("byte budget" in e for e in out.attrs["errors"])
    norm = out[out.series_id == "gdeltbq:norm"]
    assert norm.date.max() == y                                               # newest days first
    h = out[out.series_id == "gdeltbq:hormuz_iran_v1:share"]
    assert (h.value == 1.0).all()
    led = json.loads((tmp_path / "data" / "obs" / "gdelt_bq" / "_bytes.json").read_text())
    assert abs(sum(led["months"].values()) / bq.GB - out.attrs["bytes_gb"]) < 1e-6
    assert out.attrs["bytes_gb"] <= 50
    heads = out.attrs["text"]["gdelt_headlines"]
    # the headline query did not fit after the series used the run budget: logged, never over budget
    assert heads.empty == any("headlines" in e for e in out.attrs["errors"])


def test_daily_run_reads_only_new_days_then_backfills(monkeypatch, tmp_path):
    fake = FakeBQ(gb_per_day=1.0)
    _setup(monkeypatch, tmp_path, fake)
    y = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    cfg = {"queries_from": "gdelt", "backfill_start": str(y - timedelta(days=40)), "days_per_query": 7,
           "max_gb_query": 20, "max_gb_run": 20, "max_gb_month": 800, "overlap_days": 3}
    first = bq.fetch(cfg)
    store.upsert_obs("gdelt_bq", first)
    store.upsert_text("gdelt_headlines", first.attrs["text"]["gdelt_headlines"])
    fake.runs.clear()
    second = bq.fetch(cfg)
    kinds = [(a, b) for a, b, h in fake.runs if not h]
    assert kinds[0][0] == y - timedelta(days=3)                               # new days: last stored minus overlap
    assert all(b <= first.date.min() for a, b in kinds[1:])                   # then further back, never re-reading
    assert not [r for r in fake.runs if r[2]]                                 # headlines already stored: not re-read
    t = first.attrs["text"]["gdelt_headlines"]
    assert t.title.iloc[0].startswith("Tanker traffic & Hormuz") and set(t.columns) == set(store.TEXT_COLS)
    assert not second.empty


def test_month_cap_holds_across_runs(monkeypatch, tmp_path):
    fake = FakeBQ(gb_per_day=1.0)
    _setup(monkeypatch, tmp_path, fake)
    y = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    p = tmp_path / "data" / "obs" / "gdelt_bq" / "_bytes.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"months": {f"{y:%Y-%m}": int(799.5 * bq.GB)}, "log": []}))
    out = bq.fetch({"queries_from": "gdelt", "backfill_start": str(y - timedelta(days=30)), "max_gb_month": 800})
    assert not fake.runs and out.empty and any("byte budget" in e for e in out.attrs["errors"])


def test_weekends_are_not_gap_days_but_outages_are():
    c = consensus.cfg()
    d = pd.date_range("2025-08-01", "2026-10-15", freq="D")
    norm = pd.Series(np.where(d.dayofweek >= 5, 170000.0, 310000.0), index=d)   # GKG: weekends ~0.55x weekdays
    norm.iloc[-2] = 9000.0                                                         # an outage day
    share = pd.Series(0.03, index=d)
    good = consensus.valid_days(share, norm, date(2026, 10, 15), c)
    weekends = d[(d.dayofweek >= 5) & (d > pd.Timestamp("2025-09-01"))]
    assert weekends.isin(good.index).all()
    assert d[-2] not in good.index and d[-1] in good.index


def test_cftc_percentile_counts_from_the_friday_release():
    tues = pd.date_range("2023-01-03", "2026-10-13", freq="7D")              # Tuesdays; last = Tue 13 Oct 2026
    obs = pd.DataFrame({"series_id": "067651.mm_net_pct_oi", "date": tues.date,
                        "value": np.arange(len(tues), dtype=float), "source_url": "u"})
    thu = consensus.positioning(obs, "067651", date(2026, 10, 15))           # Thursday: Tuesday's report not out yet
    fri = consensus.positioning(obs, "067651", date(2026, 10, 16))           # Friday: released
    assert thu["date"] == "2026-10-06" and fri["date"] == "2026-10-13"


# ------------------------------------------------------------------ consensus: instrument, headlines, tracker
def _obs(prefix: str, end: date, start: str = "2025-01-01", jump_from: date | None = None) -> pd.DataFrame:
    d = pd.date_range(start, str(end), freq="D")
    rs = np.random.default_rng(3)
    share = 0.5 * (1 + 0.05 * rs.standard_normal(len(d)))
    if jump_from:
        share = share * np.exp(0.06 * np.clip((d - pd.Timestamp(jump_from)).days, 0, None))
    norm = np.full(len(d), 100000.0)
    rows = []
    for sid, vals in ((f"{prefix}:hormuz_iran_v1:share", share), (f"{prefix}:hormuz_iran_v1:count", share / 100 * norm),
                      (f"{prefix}:norm", norm)):
        rows += [{"series_id": sid, "date": x.date(), "value": float(v), "source_url": "u"} for x, v in zip(d, vals)]
    return pd.DataFrame(rows)


def _heads(day: date, n=4) -> pd.DataFrame:
    return pd.DataFrame([{"source": "gdelt_headlines", "item_id": f"hormuz_iran_v1|{day - timedelta(days=k)}|https://n.com/{k}",
                          "title": f"Hormuz headline {k}", "url": f"https://n.com/{k}",
                          "published": pd.Timestamp(day - timedelta(days=k), tz="UTC"),
                          "summary": f"src=n.com; copies={k + 1}", "fetched_at": pd.Timestamp("2026-10-01", tz="UTC")}
                         for k in range(n)])


def test_bigquery_series_win_when_doc_is_stale_and_headlines_attach():
    c = consensus.cfg()
    end = date(2026, 9, 30)
    obs = pd.concat([_obs("gdelt", date(2026, 9, 10)), _obs("gdeltbq", end)], ignore_index=True)
    nar = {n["id"]: n for n in consensus.narratives(obs, end, c, txt=_heads(end))}
    h = nar["hormuz_iran_v1"]
    assert h["instrument"] == "gdeltbq" and h["stage"] in consensus.STAGES
    assert [x["title"] for x in h["headlines"]] == ["Hormuz headline 3", "Hormuz headline 2", "Hormuz headline 1"]
    assert h["source_url"] == "u"
    # BigQuery still building history: shown as such rather than the DOC series' "stale"
    short = pd.concat([_obs("gdelt", date(2026, 9, 10)), _obs("gdeltbq", end, start="2026-07-01")], ignore_index=True)
    h2 = next(n for n in consensus.narratives(short, end, c) if n["id"] == "hormuz_iran_v1")
    assert h2["instrument"] == "gdeltbq" and h2["stage"] == "insufficient history"


def test_instrument_switch_compares_like_with_like(tmp_path):
    end = date(2026, 9, 30)
    b = tmp_path / "briefs" / str(end - timedelta(days=1))
    b.mkdir(parents=True)
    b.joinpath("facts.json").write_text(json.dumps({"sections": {"consensus": {"narratives": [
        {"id": "hormuz_iran_v1", "stage": "stale"}]}}}))          # old pack: DOC instrument, no "instrument" key
    obs = _obs("gdeltbq", end, jump_from=date(2026, 9, 5))
    sec, _ = consensus.build(obs, pd.DataFrame(), [], {}, {}, end, briefs=tmp_path / "briefs")
    h = next(n for n in sec["narratives"] if n["id"] == "hormuz_iran_v1")
    assert h["stage_prev_basis"] == "one data day earlier" and h["stage_prev"] != "stale"


def test_headline_audit_sheet_and_score(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    monkeypatch.setattr(consensus, "AUDIT_DIR", tmp_path / "audit")
    rows = pd.concat([_heads(date(2026, 9, 1) + timedelta(days=7 * w), n=5) for w in range(6)], ignore_index=True)
    rows["item_id"] = rows.item_id + rows.index.astype(str)
    rows["title"] = rows.title + " w" + rows.index.astype(str)
    store.upsert_text("gdelt_headlines", rows)
    sample = consensus.audit_sample("hormuz_iran_v1", n=12)
    assert len(sample) == 12 and len({r["date"] for r in sample}) >= 6          # spread over the stored days
    assert sample == consensus.audit_sample("hormuz_iran_v1", n=12)             # reproducible
    p = consensus.write_audit("hormuz_iran_v1", n=12)
    lines = p.read_text().splitlines()
    marked = [ln.replace("|  |", "| y |") if i % 4 else ln.replace("|  |", "| n |")
              for i, ln in enumerate(lines)]
    p.write_text("\n".join(marked) + "\n")
    res = consensus.score_audit("hormuz_iran_v1")
    assert res["marked"] == 12 and 0 < res["precision"] < 1
    tr = json.loads((tmp_path / "data" / "narratives" / "tracker.json").read_text())
    assert tr["narratives"]["hormuz_iran_v1"]["headline_audit"]["precision"] == res["precision"]
    try:
        consensus.write_audit("hormuz_iran_v1")                                  # never overwrites marks
        raise AssertionError("overwrote a marked sheet")
    except SystemExit:
        pass


def test_tracker_records_since_and_changes_and_ignores_older_packs(tmp_path):
    path = tmp_path / "tracker.json"
    full = _obs("gdeltbq", date(2026, 9, 30), jump_from=date(2026, 9, 5))
    t0 = date(2026, 9, 1)
    sec, _ = consensus.build(full[full.date <= t0], pd.DataFrame(), [], {}, {}, t0 + timedelta(days=1), tracker=path)
    rec = json.loads(path.read_text())["narratives"]["hormuz_iran_v1"]
    assert rec["instrument"] == "gdeltbq" and rec["stage"] in consensus.STAGES and rec["since"]
    first_stage = rec["stage"]
    # later packs: the narrative starts spreading -> one observed change, dated by its data day
    for k in range(2, 30):
        d = t0 + timedelta(days=k)
        sec, _ = consensus.build(full[full.date <= d - timedelta(days=1)], _heads(d - timedelta(days=1)), [], {}, {}, d,
                                 tracker=path)
    tr = json.loads(path.read_text())
    rec = tr["narratives"]["hormuz_iran_v1"]
    obs_changes = [ch for ch in rec["changes"] if ch["basis"] == "observed"]
    assert rec["stage"] == "spreading" and obs_changes and obs_changes[-1]["to"] == "spreading"
    assert obs_changes[0]["from"] == first_stage and obs_changes[-1]["headlines"]
    h = next(n for n in sec["narratives"] if n["id"] == "hormuz_iran_v1")
    assert h["stage_since"] == rec["since"] and h["last_change"]["to"] == "spreading"
    # a pack rebuilt for an earlier date reads the tracker but never rewrites it
    before = path.read_text()
    consensus.build(full[full.date <= t0], pd.DataFrame(), [], {}, {}, t0 + timedelta(days=1), tracker=path)
    assert path.read_text() == before
