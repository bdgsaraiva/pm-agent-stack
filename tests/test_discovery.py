"""Narrative discovery (agent 7 step 1): counting, scoring with no look-ahead, day-1 flags, grouping, demotion,
markets, decisions (dismiss 30 days or 3x; watch), the section and the BigQuery adapter with a fake client (offline)."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from pmstack import discovery as disc
from pmstack import runlog, store
from pmstack.adapters import gdelt_bq as bq
from pmstack.adapters import gdelt_disc


@pytest.fixture()
def dbox(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    monkeypatch.setattr(runlog, "LOG", tmp_path / "logs" / "runs.jsonl")
    return tmp_path


def _rows(day: date, k: int, extra: list[tuple[str, str]] = ()) -> list[dict]:
    """A day of background titles from 300 domains (varied words), plus extra (domain, title) rows."""
    rng = np.random.default_rng(day.toordinal())
    words = [f"word{i:03d}" for i in range(400)]
    out = []
    for j in range(300):
        w = rng.choice(words, 4, replace=False)
        out.append({"domain": f"site{j}.com", "title": f"{w[0]} {w[1]} {w[2]} {w[3]} - Site{j}"})
    return out + [{"domain": d, "title": t} for d, t in extra]


def _store_history(start: date, n: int, extra_by_day=None):
    for i in range(n):
        d = start + timedelta(days=i)
        disc.save_day(d, disc.count_terms(_rows(d, i, (extra_by_day or {}).get(d, []))))


# ------------------------------------------------------------------ counting
def test_count_terms_domain_once_suffix_stopwords_numbers_bigrams():
    rows = [{"domain": "reuters.com", "title": "Copper smelters cut output in Chile - Reuters"},
            {"domain": "reuters.com", "title": "Copper smelters cut output in Chile - Reuters"},
            {"domain": "reuters.com", "title": "Copper smelters cut output in Peru - Reuters"},
            {"domain": "mining.com", "title": "Copper smelters cut output | MINING.COM"},
            {"domain": "c.com", "title": "Chile copper smelters 2026 strike &amp; protest"}]
    agg = disc.count_terms(rows).set_index("term")
    assert agg.loc["copper", "domains"] == 3 and agg.loc["smelters", "domains"] == 3
    assert agg.loc["copper smelters", "domains"] == 3 and agg.loc["copper smelters", "copies"] == 5
    assert "2026" not in agg.index and "in" not in agg.index and "amp" not in agg.index
    assert agg.loc[disc.TOTAL, "domains"] == 3                            # distinct sources, not domain-title pairs


def test_site_suffix_cut_only_when_it_names_the_source():
    assert disc.clean_title("Copper smelters cut output - Reuters", "reuters.com") == "copper smelters cut output"
    assert disc.clean_title("Oil slides | MINING.COM", "www.mining.com") == "oil slides"
    assert disc.clean_title("Gold rallies - analysts see more upside", "kitco.com") == "gold rallies analysts see more upside"
    assert disc.clean_title("Oil &amp; gas &#8217;slump&#8217;", "x.com") == "oil gas slump"


def test_sql_is_english_only_counted_in_bigquery_and_literals_are_safe():
    c = disc.cfg()
    s = disc.terms_sql(c, bq.TABLE)
    assert "NOT REGEXP_CONTAINS(GKGRECORDID, r'-T')" in s and "COUNT(DISTINCT d) AS domains" in s
    assert f"HAVING domains >= {c['store_min_domains']}" in s and disc.TOTAL in s
    assert "_PARTITIONTIME >= TIMESTAMP(@start)" in s and "SourceCommonName IS NOT NULL" in s
    assert "SELECT DISTINCT d, t, copies, term" in s and "'&amp;', '&'" in s
    assert f"SELECT '{disc.TOTAL}', COUNT(DISTINCT d)" in s
    t = disc.titles_sql(["oil price", "copper"], c, bq.TABLE)
    assert "UNNEST(['oil price', 'copper'])" in t and "IGNORE NULLS" in t
    with pytest.raises(ValueError):
        disc._lit(["x'; DROP TABLE y; --"])


def test_vectorised_score_matches_a_plain_loop(dbox):
    start = date(2026, 8, 1)
    some = {start + timedelta(days=i): [(f"z{j}.com", f"Zinc mine expansion talks {j}") for j in range(3 + i % 5)]
            for i in range(40)}
    _store_history(start, 40, some)
    day = start + timedelta(days=40)
    agg = disc.count_terms(_rows(day, 40, [(f"z{j}.com", f"Zinc mine expansion talks {j}") for j in range(9)]))
    hist = disc.history(day, 90)
    got = disc.score(day, agg, hist).set_index("term").loc["zinc mine"]
    c = disc.cfg()
    lam = 1 - 0.5 ** (1 / c["half_life_days"])
    xs = []
    for _, h in hist:
        h = h.set_index("term")
        xs.append((h.loc["zinc mine", "domains"] if "zinc mine" in h.index else 0) / h.loc[disc.TOTAL, "domains"])
    m, v = xs[0], 0.0
    for x in xs[1:]:
        dlt = x - m
        m += lam * dlt
        v = (1 - lam) * (v + lam * dlt * dlt)
    n = agg.set_index("term").loc[disc.TOTAL, "domains"]
    beta = c["noise_floor_domains"] / n
    assert got["score"] == pytest.approx((9 / n - max(m, beta)) / (v ** 0.5 + beta))


# ------------------------------------------------------------------ scoring
def test_new_theme_flagged_on_its_first_day_and_steady_one_not(dbox):
    start = date(2026, 8, 1)
    steady = [(f"steady{j}.com", f"Zinc mine expansion talks {j}") for j in range(10)]
    _store_history(start, 40, {start + timedelta(days=i): steady for i in range(40)})
    day = start + timedelta(days=40)
    new = [(f"news{j}.com", f"Hormuz tanker seized near Kharg island {j}") for j in range(12)]
    agg = disc.count_terms(_rows(day, 40, steady + new))
    sc = disc.score(day, agg, disc.history(day, 90)).set_index("term")
    assert sc.loc["kharg island", "new"] and sc.loc["kharg island", "domains"] == 12
    assert not sc.loc["zinc mine", "new"] and not sc.loc["zinc mine", "rising"]
    # from nothing, s = (domains - beta) / beta with beta = 3 domains: 12 domains score 3.0, so day 1 is caught by the
    # "new" flag (>= 8 domains), not by "rising" (score >= 4 needs ~15)
    assert sc.loc["kharg island", "score"] == pytest.approx(3.0, abs=0.01)


def test_no_flags_before_min_history_and_no_lookahead(dbox):
    start = date(2026, 8, 1)
    _store_history(start, 10)
    day = start + timedelta(days=10)
    new = [(f"n{j}.com", f"Cocoa crop disease spreads {j}") for j in range(12)]
    sc = disc.score(day, disc.count_terms(_rows(day, 10, new)), disc.history(day, 90))
    assert not sc["new"].any() and not sc["rising"].any()                 # only 10 stored days
    _store_history(start, 40)
    later = start + timedelta(days=60)
    disc.save_day(later, disc.count_terms(_rows(later, 60, new)))         # a LATER day stored
    h = disc.history(start + timedelta(days=40), 90)
    assert all(d < start + timedelta(days=40) for d, _ in h) and later not in [d for d, _ in h]


def test_rising_needs_score_and_domains(dbox):
    start = date(2026, 8, 1)
    base = [(f"b{j}.com", f"Lithium prices slump again {j}") for j in range(3)]
    _store_history(start, 40, {start + timedelta(days=i): base for i in range(40)})
    day = start + timedelta(days=40)
    up = [(f"u{j}.com", f"Lithium prices slump again {j}") for j in range(18)]
    sc = disc.score(day, disc.count_terms(_rows(day, 40, up)), disc.history(day, 90)).set_index("term")
    assert sc.loc["lithium", "rising"] and not sc.loc["lithium", "new"]   # it had 3 domains a day before


# ------------------------------------------------------------------ grouping, demotion, markets, tracked link
def _title_rows(term, titles, doms_per=3, prefix="d"):
    return [{"term": term, "t": disc.clean_title(t), "title": t, "url": f"https://x.com/{i}", "copies": 2,
             "doms": [f"{prefix}{i}-{k}.com" for k in range(doms_per)]} for i, t in enumerate(titles)]


def test_group_terms_sharing_titles_and_label_and_headlines():
    day = date(2026, 10, 19)
    ts = [f"Kharg island tanker seized by Iran report {i}" for i in range(8)]
    fl = pd.DataFrame([{"term": "kharg island", "new": True, "rising": True, "score": 9.0},
                       {"term": "tanker seized", "new": True, "rising": True, "score": 7.0},
                       {"term": "zinc mine", "new": False, "rising": True, "score": 5.0}])
    rows = _title_rows("kharg island", ts) + _title_rows("tanker seized", ts) + \
        _title_rows("zinc mine", ["Zinc mine expansion approved", "Zinc mine strike ends", "New zinc mine opens"], prefix="z")
    cs = disc.group(day, fl, rows)
    big = next(x for x in cs if "kharg island" in x["terms"])
    assert set(big["terms"]) == {"kharg island", "tanker seized"} and big["new"] and big["domains"] == 24
    assert len([h for h in big["headlines"] if h["kind"] == "top"]) == 5 and big["id"].startswith("2026-10-19-kharg-island-")
    assert len({x["id"] for x in cs}) == len(cs)


def test_enrich_demotes_press_releases_tags_markets_and_links_tracked(dbox):
    c = disc.cfg()
    day = date(2026, 10, 19)
    pr = [{"term": "copper project", "t": disc.clean_title(f"Junior copper project drill results {i}"),
           "title": f"Junior copper project drill results {i}", "url": "u", "copies": 1, "doms": ["globenewswire.com", f"x{i}.com"] if i == 0 else ["globenewswire.com", "newsfile.com"]}
          for i in range(5)]
    hz = _title_rows("strait hormuz", [f"Strait of Hormuz tanker traffic halts {i}" for i in range(6)])
    fl = pd.DataFrame([{"term": "copper project", "new": True, "rising": True, "score": 6.0},
                       {"term": "strait hormuz", "new": False, "rising": True, "score": 8.0}])
    cs = disc.enrich(day, disc.group(day, fl, pr + hz, c), c)
    cu = next(x for x in cs if "copper project" in x["terms"])
    hzc = next(x for x in cs if "strait hormuz" in x["terms"])
    assert cu["demoted"] and "press-release" in cu["demoted"][0] and cu["markets"][0]["price_ref"] == "HG=F"
    assert not hzc["demoted"] and {m["price_ref"] for m in hzc["markets"]} >= {"BZ=F"}
    assert hzc["tracked"] == "hormuz_iran_v1"                           # matches the frozen Hormuz query
    assert cs[0] is hzc                                                 # demoted candidates sort last


# ------------------------------------------------------------------ decisions and the section
def _write_cands(day: date, cands: list[dict]):
    p = disc.cand_path(day)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"day": str(day), "version": "disc_v1", "history_days": 40, "terms_flagged": 3,
                             "candidates": cands}), encoding="utf-8")


def _cand(day, terms, domains, new=True, markets=(("BZ=F", "Brent"),)):
    return {"id": f"{day}-{terms[0].replace(' ', '-')}", "day": str(day), "label": f"{terms[0]} label", "terms": terms,
            "lead_term": terms[0], "domains": domains, "titles": 10, "new": new, "rising": True, "score": 6.0,
            "press_release_share": 0.0, "top3_copy_share": 0.2, "demoted": [], "sustained": False,
            "markets": [{"price_ref": r, "name": n, "title_share": 0.8} for r, n in markets], "tracked": None,
            "headlines": [{"title": "t", "url": "https://x", "domains": 3, "kind": "top"}], "version": "disc_v1"}


def test_dismiss_hides_30_days_or_until_3x_and_watch_regrows(dbox):
    d0 = date(2026, 10, 1)
    _write_cands(d0, [_cand(d0, ["kharg island", "tanker seized"], 10)])
    disc.decide(f"{d0}-kharg-island", "dismiss", "noise", on=str(d0))
    with pytest.raises(SystemExit):
        disc.decide(f"{d0}-kharg-island", "dismiss")                    # a dismissal needs a reason
    c = disc.cfg()
    decs = disc.load_decisions()
    later = _cand(d0 + timedelta(days=5), ["kharg island"], 20)
    assert disc.status(later, decs, d0 + timedelta(days=5), c)["hidden"] is True        # 2x: still hidden
    assert disc.status({**later, "domains": 31}, decs, d0 + timedelta(days=5), c)["hidden"] is False   # >= 3x
    assert disc.status(later, decs, d0 + timedelta(days=31), c)["hidden"] is False     # after 30 days
    assert disc.status(later, decs, d0 - timedelta(days=1), c) is None                 # decision not yet made
    _write_cands(d0 + timedelta(days=2), [_cand(d0 + timedelta(days=2), ["lithium slump"], 8)])
    disc.decide(f"{d0 + timedelta(days=2)}-lithium-slump", "watch", on=str(d0 + timedelta(days=2)))
    w = _cand(d0 + timedelta(days=4), ["lithium slump"], 12)
    assert disc.status(w, disc.load_decisions(), d0 + timedelta(days=4), c)["hidden"] is True
    assert disc.status({**w, "domains": 16}, disc.load_decisions(), d0 + timedelta(days=4), c)["hidden"] is False


def _prices(ref, start="2025-01-01", end="2026-12-31"):
    d = pd.bdate_range(start, end)
    rng = np.random.default_rng(1)
    v = 80 * np.exp(np.cumsum(rng.normal(0, 0.015, len(d))))
    return pd.DataFrame({"source": "prices", "series_id": ref, "name": ref, "date": d.date, "value": v, "unit": "usd",
                         "freq": "D", "source_url": f"https://finance.yahoo.com/quote/{ref}",
                         "fetched_at": pd.Timestamp("2026-10-15")})


def test_section_usable_next_day_with_point_in_time_context_and_alert(dbox):
    store.upsert_obs("prices", _prices("BZ=F"))
    d0 = date(2026, 10, 14)
    _write_cands(d0, [_cand(d0, ["kharg island"], 12), _cand(d0, ["zinc mine"], 6, new=False, markets=())])
    sec, al = disc.build(d0)                                             # same day: not usable yet
    assert "no candidate list" in sec["note"] and al == []
    sec, al = disc.build(d0 + timedelta(days=1))
    k = next(x for x in sec["candidates"] if "kharg island" in x["terms"])
    px = k["context"][0]["price"]
    assert px["t0_date"] >= str(d0) and px["since_date"] <= str(d0) and px["base_rate_pct"] is not None
    assert [a["kind"] for a in al] == ["narrative_new"]                  # day-1 flag in a focus market only
    text = "\n".join(disc.render(sec))
    assert "**Brent**" in text and "**Outside focus markets**" in text and "co-movement" in text
    disc.decide(k["id"], "dismiss", "known", on=str(d0 + timedelta(days=1)))
    again, _ = disc.build(d0 + timedelta(days=1))                         # today's pack rebuilt: decision not yet
    assert again["hidden"] == 0
    cli_view, _ = disc.build(d0 + timedelta(days=1), decisions_through=d0 + timedelta(days=1))
    assert cli_view["hidden"] == 1                                       # the CLI list applies today's decisions
    sec2, al2 = disc.build(d0 + timedelta(days=2))
    assert sec2["hidden"] == 1 and al2 == []


def test_monday_pack_covers_the_weekend_and_merges_repeats(dbox):
    fri, sat, sun, mon = date(2026, 10, 16), date(2026, 10, 17), date(2026, 10, 18), date(2026, 10, 19)
    _write_cands(fri, [_cand(fri, ["kharg island", "tanker seized"], 12)])
    _write_cands(sat, [_cand(sat, ["cocoa disease"], 9)])
    _write_cands(sun, [_cand(sun, ["kharg island"], 20, new=False)])
    sec, al = disc.build(mon)
    assert sec["days"] == [str(fri), str(sat), str(sun)]
    k = [x for x in sec["candidates"] if "kharg island" in x["terms"]]
    assert len(k) == 1 and k[0]["new"] and k[0]["domains"] == 20 and k[0]["days"] == [str(fri), str(sun)]
    assert any("cocoa disease" in x["terms"] for x in sec["candidates"])
    assert len(al) <= disc.cfg()["max_alerts"]


# ------------------------------------------------------------------ the adapter, with a fake BigQuery
def test_adapter_backfills_scores_and_writes_candidates(dbox, monkeypatch):
    monkeypatch.setattr(bq, "_client", lambda cfg: object())
    yday = (datetime.now(timezone.utc) - timedelta(days=1)).date()        # the adapter's clock is UTC
    new = [(f"news{j}.com", f"Kharg island tanker seized report {j}") for j in range(12)]

    def fake_chunk(client, sql, params, kind, start, stop, budget, at, errors):
        day = date.fromisoformat(params["start"])
        rows = _rows(day, 0, new if day == yday else [])
        budget.spend(int(0.1 * bq.GB), kind, start, 1, at)
        if kind == "discovery:terms":
            return disc.count_terms(rows).to_dict("records")
        terms = [t.strip("'") for t in sql.split("UNNEST([")[1].split("])")[0].split(", ")]
        out = []
        for term in terms:
            for r in rows:
                tt = disc.clean_title(r["title"], r["domain"])
                if f" {term} " in f" {tt} ":
                    out.append({"term": term, "t": tt, "title": r["title"], "url": "https://x", "domains": 1,
                                "copies": 1, "doms": [r["domain"]]})
        return out

    monkeypatch.setattr(bq, "_run_chunk", fake_chunk)
    out = gdelt_disc.fetch({"max_minutes": 5, "candidate_days": 1, "max_gb_query": 10, "max_gb_run": 40,
                            "max_gb_month": 800})
    assert not out.attrs["errors"], out.attrs["errors"]
    assert len(disc.stored_days()) == disc.cfg()["history_days"] and disc.cand_path(yday).exists()
    cands = json.loads(disc.cand_path(yday).read_text(encoding="utf-8"))["candidates"]
    assert any("kharg island" in x["terms"] and x["new"] for x in cands)
    assert json.loads((store.DATA / "obs" / "gdelt_bq" / "_bytes.json").read_text())["months"]
    before = disc.cand_path(yday).read_text(encoding="utf-8")
    gdelt_disc.fetch({"max_minutes": 5, "candidate_days": 1})
    assert disc.cand_path(yday).read_text(encoding="utf-8") == before   # written once, never rewritten


def test_adapter_skips_without_key(dbox, monkeypatch):
    monkeypatch.delenv("GCP_SA_KEY", raising=False)
    assert "GCP_SA_KEY" in gdelt_disc.fetch({}).attrs["skipped"]


def test_auditor_ignores_discovery_headlines_but_keeps_counts():
    from pmstack import audit
    facts = {"sections": {"discovery": {"candidates": [
        {"id": "2026-10-19-gold-abc123", "label": "7 reasons gold is up", "terms": ["gold"], "domains": 14,
         "headlines": [{"title": "Gold 2,450 target", "url": "u"}], "context": [{"price": {"t0_move_sd": 2.1}}]}]}}}
    out = audit._strip_discovery(facts)["sections"]["discovery"]["candidates"][0]
    assert "label" not in out and "headlines" not in out and out["domains"] == 14 and out["context"]
    assert facts["sections"]["discovery"]["candidates"][0]["label"]         # the pack itself is untouched
