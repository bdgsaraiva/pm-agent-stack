"""Balance keeper (agent 9): norms, availability (no look-ahead), WASDE/PSD/NASS parsing, alerts, critic facts,
fact-pack wiring (offline: synthetic data, faked downloads)."""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from pmstack import balance, critic, fetch, monitor, runlog, store
from pmstack.adapters import nass, usda_psd, wasde

EIA_URL = "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s={c}&f=W"


def _weekly(sid: str, source: str, last: date, base_v: float, amp: float, end_v: float | None = None,
            unit: str = "kbbl", start: str = "2015-01-02", noise: float = 0.0) -> pd.DataFrame:
    d = pd.date_range(start, last, freq="W-FRI").date
    wk = np.array([x.isocalendar()[1] for x in d])
    v = base_v + amp * np.sin(2 * math.pi * wk / 52.0) + np.random.default_rng(9).normal(0, noise, len(d))
    if end_v is not None:
        v[-1] = end_v
    code = sid.split(".")[1]
    return pd.DataFrame({"source": source, "series_id": sid, "name": sid, "date": d, "value": v, "unit": unit,
                         "freq": "weekly", "source_url": EIA_URL.format(c=code), "fetched_at": pd.Timestamp("2026-10-15")})


@pytest.fixture()
def bbox(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    monkeypatch.setattr(runlog, "LOG", tmp_path / "logs" / "runs.jsonl")
    monkeypatch.setattr(monitor, "BRIEFS", tmp_path / "briefs")
    return tmp_path


WASDE_CSV = '''"WasdeNumber","ReportDate","ReportTitle","Attribute","ReliabilityProjection","Commodity","Region","MarketYear","ProjEstFlag","AnnualQuarterFlag","Value","Unit","ReleaseDate","ReleaseTime","ForecastYear","ForecastMonth"
"676","{rd}","U.S. Feed Grain and Corn Supply and Use","Ending Stocks","","Corn","United States","2025/26","Est.","Annual","{es_old}","Million Bushels","{rel}","12:00:00.0000000","2026","10"
"676","{rd}","U.S. Feed Grain and Corn Supply and Use","Use, Total","","Corn","United States","2025/26","Est.","Annual","16000","Million Bushels","{rel}","12:00:00.0000000","2026","10"
"676","{rd}","U.S. Feed Grain and Corn Supply and Use","Ending Stocks","","Corn","United States","2026/27","Proj.","Annual","{es}","Million Bushels","{rel}","12:00:00.0000000","2026","10"
"676","{rd}","U.S. Feed Grain and Corn Supply and Use","Use, Total","","Corn","United States","2026/27","Proj.","Annual","16000","Million Bushels","{rel}","12:00:00.0000000","2026","10"
"676","{rd}","World Corn Supply and Use","Ending Stocks","","Corn","United States","2026/27","Proj.","Annual","47.0","Million Metric Tons","{rel}","12:00:00.0000000","2026","10"
"676","{rd}","World Corn Supply and Use","Ending Stocks","","Corn","World","2026/27","Proj.","Annual","300","Million Metric Tons","{rel}","12:00:00.0000000","2026","10"
"676","{rd}","World Corn Supply and Use","Domestic Total","","Corn","World","2026/27","Proj.","Annual","1250","Million Metric Tons","{rel}","12:00:00.0000000","2026","10"
"676","{rd}","World Corn Supply and Use","Ending Stocks","","Corn","World Less China","2026/27","Proj.","Annual","100","Million Metric Tons","{rel}","12:00:00.0000000","2026","10"
"676","{rd}","World Corn Supply and Use","Domestic Total","","Corn","World Less China","2026/27","Proj.","Annual","930","Million Metric Tons","{rel}","12:00:00.0000000","2026","10"
"676","{rd}","Reliability of United States October Projections","Ending Stocks","average","Corn","United States","","","Annual","200","Million Bushels","{rel}","12:00:00.0000000","2026","10"
"676","{rd}","Reliability of United States October Projections","Ending Stocks","root_mean_square_error","Corn","United States","","","Annual","20","Percent","{rel}","12:00:00.0000000","2026","10"
"676","{rd}","U.S. Wheat Supply and Use","Ending Stocks","","Wheat","United States","2026/27","Proj.","Annual","700","Million Bushels","{rel}","12:00:00.0000000","2026","10"
"676","{rd}","U.S. Wheat Supply and Use","Use, Total","","Wheat","United States","2026/27","Proj.","Annual","1800","Million Bushels","{rel}","12:00:00.0000000","2026","10"
"676","{rd}","Reliability of United States October Projections","Ending Stocks","average","Wheat","United States","","","Annual","2.0","Million Metric Tons","{rel}","12:00:00.0000000","2026","10"
"676","{rd}","U.S. Dairy Prices","Ending Stocks","","Milk","United States","2026/27","Proj.","Annual","9","Million Pounds","{rel}","12:00:00.0000000","2026","10"
'''


def _wasde_cfg():
    import yaml
    return yaml.safe_load((balance.ROOT / "config" / "sources.d" / "balance.yaml").read_text(encoding="utf-8"))["wasde"]


def _csv(rel, rd, es, es_old=1500):
    return "﻿" + WASDE_CSV.format(rel=rel, rd=rd, es=es, es_old=es_old)


# ------------------------------------------------------------------ sources
def test_sources_d_merge_and_duplicate_keys(monkeypatch, tmp_path):
    monkeypatch.delenv("PMSTACK_NO_SOURCES_D", raising=False)
    src = fetch.load_sources()
    assert {"eia", "eia_bal", "wasde", "usda_psd", "nass"} <= set(src)
    d = tmp_path / "config" / "sources.d"
    d.mkdir(parents=True)
    (tmp_path / "config" / "sources.yaml").write_text("eia: {adapter: eia}\n", encoding="utf-8")
    (d / "x.yaml").write_text("eia: {adapter: eia}\n", encoding="utf-8")
    monkeypatch.setattr(fetch, "ROOT", tmp_path)
    with pytest.raises(ValueError):
        fetch.load_sources()


def test_wasde_parse_keeps_us_tables_world_and_reliability():
    df = wasde.parse(_csv("2026-10-09", "October 2026", 1849), "https://x/2026-10.csv", _wasde_cfg())
    ids = set(df.series_id)
    assert "wasde:corn:united-states:ending-stocks:2026/27" in ids
    assert "wasde:corn:world-less-china:domestic-total:2026/27" in ids
    assert "wasde_rel:corn:united-states:ending-stocks:average" in ids
    assert not any(s.startswith("wasde:milk") for s in ids)                        # not configured
    us = df[df.series_id == "wasde:corn:united-states:ending-stocks:2026/27"]
    assert len(us) == 1 and us["value"].iloc[0] == 1849 and us["unit"].iloc[0] == "Million Bushels"   # world-table MT row dropped
    assert set(df.date) == {date(2026, 10, 9)}


def test_wasde_fetch_skips_missing_months_as_notes(monkeypatch):
    files = {"2026-09": _csv("2026-09-11", "September 2026", 1567), "2026-10": _csv("2026-10-09", "October 2026", 1849)}
    monkeypatch.setattr(wasde, "_get_csv", lambda ym, t: (files.get(ym), f"https://x/{ym}.csv") if ym in files else (None, None))
    df = wasde.fetch({**_wasde_cfg(), "budget_s": 60}, since="2026-08-01")
    assert set(df.date) == {date(2026, 9, 11), date(2026, 10, 9)}
    assert df.attrs["errors"] == [] and "2026-08" in df.attrs["notes"]


def test_nass_availability_dates():
    rel = {"FIRST OF SEP": [9, 30, 0], "FIRST OF DEC": [1, 13, 1]}
    assert nass.available({"week_ending": "2026-08-09"}, rel) == date(2026, 8, 10)
    assert nass.available({"reference_period_desc": "FIRST OF SEP", "year": "2026"}, rel) == date(2026, 9, 30)
    assert nass.available({"reference_period_desc": "FIRST OF DEC", "year": "2025"}, rel) == date(2026, 1, 13)
    rows = nass.records([{"short_desc": "CORN - CONDITION, MEASURED IN PCT GOOD", "week_ending": "2026-08-09", "Value": "55"},
                         {"short_desc": "CORN - CONDITION, MEASURED IN PCT GOOD", "week_ending": "2026-08-16", "Value": "(D)"}],
                        {"stock_release": rel}, pd.Timestamp("2026-10-15"))
    assert len(rows) == 1 and rows[0]["series_id"] == "nass:corn-condition-measured-in-pct-good" and rows[0]["date"] == date(2026, 8, 10)


def test_psd_records_loose_keys_and_vintage_not_after_fetch():
    attrs = usda_psd.attribute_names([{"attributeId": 176, "attributeName": "Ending Stocks"},
                                      {"Attribute_ID": 125, "Attribute_Name": "Domestic Consumption"}])
    assert attrs == {176: "Ending Stocks", 125: "Domestic Consumption"}
    rows = usda_psd.records([{"commodityCode": "0612000", "countryCode": "world", "marketYear": "2026", "calendarYear": "2026",
                              "month": "11", "attributeId": 176, "unitId": 8, "value": 45000},
                             {"attributeId": 999, "marketYear": 2026, "value": 1}],
                            "sugar", "world", attrs, {8: "(1000 MT)"}, {"ending-stocks"}, date(2026, 10, 16), pd.Timestamp("2026-10-16"))
    assert len(rows) == 1 and rows[0]["series_id"] == "psd:sugar:world:ending-stocks:2026"
    assert rows[0]["date"] == date(2026, 10, 16)       # a November vintage is never dated after the fetch


def test_eia_adapter_keeps_its_block_source(monkeypatch):
    from pmstack.adapters import base, eia
    monkeypatch.setenv("EIA_API_KEY", "test")
    monkeypatch.setattr(base, "get_json", lambda url, **kw: {"response": {"data": [{"period": "2026-10-09", "value": "1"}]}})
    df = eia.fetch({"source": "eia_bal", "series": [{"id": "PET.WKJSTUS1.W", "name": "jet", "unit": "kbbl"}]})
    assert set(df["source"]) == {"eia_bal"}


# ------------------------------------------------------------------ norms and availability
def _store_oil(end_v=380000.0, last=date(2026, 10, 9)):
    store.upsert_obs("eia", pd.concat([_weekly("PET.WCESTUS1.W", "eia", last, 420000, 10000, end_v, noise=2000),
                                       _weekly("PET.WDISTUS1.W", "eia", last, 120000, 8000)]))
    store.upsert_obs("eia_bal", pd.concat([_weekly("PET.W_EPC0_VSD_NUS_DAYS.W", "eia_bal", last, 25, 1, unit="days"),
                                           _weekly("PET.WRPUPUS2.W", "eia_bal", last, 20000, 500, unit="kbd"),
                                           _weekly("PET.WCRAUUS2.W", "eia_bal", last, 0, 300, end_v=6000, unit="kbd")]))


def test_stock_norm_is_same_week_prior_five_years(bbox):
    _store_oil()
    sec, _ = balance.build(date(2026, 10, 16))
    crude = next(r for r in sec["oil"]["stocks"] if r["id"] == "PET.WCESTUS1.W")
    assert crude["week_ending"] == "2026-10-09" and crude["norm_years"] == [2025, 2024, 2023, 2022, 2021]
    assert crude["beyond"] == "below" and crude["z"] < -2 and crude["range_pos_pct"] < 0
    assert crude["days_supply"] == pytest.approx(25 + math.sin(2 * math.pi * 41 / 52), abs=0.1)
    flow = next(r for r in sec["oil"]["flows"] if r["id"] == "PET.WRPUPUS2.W")
    assert flow["vs_5y_pct"] is not None and abs(flow["vs_5y_pct"]) < 2
    assert sec["oil"]["adjustment"]["flag"] is True


def test_eia_week_is_invisible_until_released(bbox):
    """Week ending Fri 9 Oct is released Wed 14 Oct (10:30 ET): the 05:40 BRT pack of 15 Oct is the first to show it."""
    _store_oil()
    before = balance.build(date(2026, 10, 14))[0]
    after = balance.build(date(2026, 10, 15))[0]
    w = lambda s: next(r for r in s["oil"]["stocks"] if r["id"] == "PET.WCESTUS1.W")["week_ending"]
    assert w(before) == "2026-10-02" and w(after) == "2026-10-09"


def test_range_alert_only_when_fresh_and_large(bbox):
    _store_oil()
    al = balance.build(date(2026, 10, 16))[1]
    rng = [a for a in al if a["kind"] == "balance_range"]
    assert len(rng) == 1 and "below the 2021-2025 same-week range" in rng[0]["text"] and rng[0]["severity"] >= 2
    assert not [a for a in balance.build(date(2026, 11, 20))[1] if a["kind"] == "balance_range"]   # stale week: no alert


# ------------------------------------------------------------------ grains
def _store_wasde(monkeypatch):
    files = {"2026-09": _csv("2026-09-11", "September 2026", 1567), "2026-10": _csv("2026-10-09", "October 2026", 1849)}
    monkeypatch.setattr(wasde, "_get_csv", lambda ym, t: (files.get(ym), f"https://x/{ym}.csv") if ym in files else (None, None))
    store.upsert_obs("wasde", wasde.fetch({**_wasde_cfg(), "budget_s": 60}, since="2026-09-01"))


def _store_psd_history():
    rows = []
    for my in range(2007, 2026):
        for attr, v in (("ending-stocks", 1000 + 60 * (my - 2007)), ("domestic-consumption", 300), ("exports", 50)):
            rows.append({"source": "usda_psd", "series_id": f"psd:corn:us:{attr}:{my}", "name": "x", "date": date(my + 1, 1, 15),
                         "value": float(v), "unit": "(1000 MT)", "freq": "monthly", "source_url": "https://psd",
                         "fetched_at": pd.Timestamp("2026-10-15")})
    store.upsert_obs("usda_psd", pd.DataFrame(rows))


def test_grain_row_revision_reliability_world_and_percentile(bbox, monkeypatch):
    _store_wasde(monkeypatch)
    _store_psd_history()
    sec, al = balance.build(date(2026, 10, 16))
    corn = next(g for g in sec["grains"] if g["market"] == "Corn")
    assert corn["report_date"] == "2026-10-09" and corn["my"] == "2026/27"
    assert corn["ending_stocks"] == 1849 and corn["es_change"] == 282 and corn["prev_report"] == "2026-09-11"
    assert corn["sur_pct"] == pytest.approx(11.6, abs=0.05) and corn["old_my"] == "2025/26"
    assert corn["usda_avg_miss"] == 200 and corn["usda_rmse_pct"] == 20
    assert corn["world"]["sur_pct"] == pytest.approx(24.0, abs=0.05) and corn["world"]["ex_china_sur_pct"] == pytest.approx(10.8, abs=0.05)
    assert corn["sur_hist_n"] == 19 and corn["sur_pctile"] is not None
    wheat = next(g for g in sec["grains"] if g["market"] == "Wheat")
    assert wheat["usda_avg_miss"] == pytest.approx(2.0 * 36.7437, abs=0.01)      # metric tons converted to bushels
    wa = [a for a in al if a["kind"] == "wasde_revision"]
    assert len(wa) == 1 and "corn" in wa[0]["text"] and "+282" in wa[0]["text"] and "not a consensus" in wa[0]["text"]


def test_wasde_is_invisible_on_its_release_day(bbox, monkeypatch):
    _store_wasde(monkeypatch)
    on_day = balance.build(date(2026, 10, 9))[0]
    corn = next(g for g in on_day["grains"] if g["market"] == "Corn")
    assert corn["report_date"] == "2026-09-11"          # the 05:40 BRT pack comes before the 12:00 ET release


# ------------------------------------------------------------------ crops
def _nass_rows(sd, dates_vals, freq="weekly"):
    return pd.DataFrame([{"source": "nass", "series_id": f"nass:{nass.slug(sd)}", "name": f"{sd} ({d - timedelta(days=1)})",
                          "date": d, "value": float(v), "unit": "PCT", "freq": freq, "source_url": nass.HUMAN,
                          "fetched_at": pd.Timestamp("2026-10-15")} for d, v in dates_vals])


def test_condition_change_alerts_in_key_months_only(bbox):
    # Mondays (release days) of ISO weeks 33 and 34 in 2021-2026: last year falls 10 points on the week
    days = [(date.fromisocalendar(y, w, 1), y, w) for y in range(2021, 2027) for w in (33, 34)]
    good = [(d, 50 if y < 2026 else (55 if w == 33 else 45)) for d, y, w in days]
    exc = [(d, 15) for d, _, _ in days]
    days = [d for d, _, _ in days]
    store.upsert_obs("nass", pd.concat([_nass_rows("CORN - CONDITION, MEASURED IN PCT GOOD", good),
                                        _nass_rows("CORN - CONDITION, MEASURED IN PCT EXCELLENT", exc)]))
    last = max(days)
    sec, al = balance.build(last + timedelta(days=1))
    row = next(r for r in sec["condition"] if r["crop"] == "Corn")
    assert row["weekly_change_pp"] == -10 and row["key_month"] and row["vs_avg5_pp"] == -5
    assert [a for a in al if a["kind"] == "crop_condition"]


# ------------------------------------------------------------------ critic and fact pack
def test_critic_facts_and_counter_when_balance_leans_against(bbox):
    _store_oil(end_v=470000.0)                         # crude far above its range: loose
    sec, _ = balance.build(date(2026, 10, 16))
    f, lean = balance.critic_facts(sec, "CL=F", "long")
    assert f["bal.stock"][0] == "US crude ex SPR" and f["bal.stock_z"][0] > 1
    assert lean and lean["basis"] == "balance" and set(lean["facts"]) <= set(f)
    _, lean_short = balance.critic_facts(sec, "CL=F", "short")
    assert lean_short is None                          # loose stocks agree with a short
    assert balance.critic_facts(sec, "GC=F", "long") == ({}, None)


def test_monitor_pack_has_balances_and_critic_reads_them_without_lookahead(bbox):
    _store_oil(end_v=470000.0)
    now = datetime(2026, 10, 16, 9, 0, tzinfo=timezone.utc)
    facts = monitor.build(asof=date(2026, 10, 16), now=now)
    assert facts["sections"]["balance"]["oil"]["stocks"]
    md = (bbox / "briefs" / "2026-10-16" / "facts.md").read_text(encoding="utf-8")
    assert "## Balances (descriptive" in md and "never a consensus" in md and "nan" not in md.lower().replace("financ", "")
    e = {"id": "x", "market": "WTI", "price_ref": "CL=F", "direction": "long", "conviction": 3, "status": "open",
         "created_utc": "2026-10-16T12:00:00+00:00", "entry_price": 98.0, "target": 105.0, "invalidation_price": 94.0}
    cd = critic.card(e, entries=[], asof="2026-10-16", now=now, briefs=bbox / "briefs")
    assert "bal.stock_z" in cd["facts"] and any(c["basis"] == "balance" for c in cd["contradictions"])
    old = critic.card(e, entries=[], asof="2026-10-15", now=now, briefs=bbox / "briefs")
    assert "bal.stock_z" not in old["facts"]            # no pack on or before the idea's date: nothing leaks back


def test_monitor_survives_a_balance_error(bbox, monkeypatch):
    _store_oil()
    monkeypatch.setattr(balance, "build", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    facts = monitor.build(asof=date(2026, 10, 16), now=datetime(2026, 10, 16, 9, 0, tzinfo=timezone.utc))
    assert "boom" in facts["sections"]["balance"]["error"]
    md = (bbox / "briefs" / "2026-10-16" / "facts.md").read_text(encoding="utf-8")
    assert "## Balances (agent 9)" in md and "## Data health" in md


def test_render_empty_and_audit_binds_balance_figures(bbox):
    from pmstack import audit
    assert "No balance data yet" in "\n".join(balance.render(balance.build(date(2026, 10, 16))[0]))
    _store_oil()
    sec, _ = balance.build(date(2026, 10, 16))
    crude = next(r for r in sec["oil"]["stocks"] if r["id"] == "PET.WCESTUS1.W")
    pool = audit.Pool()
    pool.add_obj({"sections": {"balance": sec}})
    rep = audit.audit_text(f"US crude stocks are {abs(crude['vs_avg_pct']):.1f}% below the 5-year same-week average.", pool.finish())
    assert rep["summary"]["orphan"] == 0 and rep["summary"]["matched"] >= 1


# ------------------------------------------------------------------ live probe findings (16 Oct)
def test_errors_never_carry_api_keys(tmp_path, monkeypatch):
    from pmstack.adapters import base
    monkeypatch.setattr(runlog, "LOG", tmp_path / "runs.jsonl")

    class R:
        status_code, text = 404, "not valid"
        url = "https://api.eia.gov/v2/seriesid/X?api_key=SECRET123&start=2015"
    monkeypatch.setattr(base.SESSION, "get", lambda *a, **k: R())
    with pytest.raises(RuntimeError) as e:
        base.get("https://api.eia.gov/v2/seriesid/X", params={"api_key": "SECRET123"}, tries=1)
    assert "SECRET123" not in str(e.value) and "REDACTED" in str(e.value)
    runlog.log("r", "fetch:x", "error", errors=["https://q/api_GET/?key=SECRET456&short_desc=a"])
    assert "SECRET456" not in (tmp_path / "runs.jsonl").read_text(encoding="utf-8")


def test_eia_bad_series_does_not_cost_the_block(monkeypatch):
    from pmstack.adapters import base, eia
    monkeypatch.setenv("EIA_API_KEY", "test")

    def fake(url, **kw):
        if "BAD" in url:
            raise RuntimeError("HTTP 404: Series ID is not valid")
        return {"response": {"data": [{"period": "2026-10-09", "value": "1"}]}}
    monkeypatch.setattr(base, "get_json", fake)
    df = eia.fetch({"source": "eia_bal", "series": [{"id": "PET.BAD.W", "name": "x", "unit": "kbd"},
                                                     {"id": "PET.WKJSTUS1.W", "name": "jet", "unit": "kbbl"}]})
    assert list(df["series_id"]) == ["PET.WKJSTUS1.W"] and "PET.BAD.W" in df.attrs["errors"][0]


def test_psd_falls_back_to_standard_attribute_ids(monkeypatch):
    monkeypatch.setenv("USDA_FAS_API_KEY", "test")

    def fake(path, key, timeout):
        if path == "/commodityAttributes":
            raise RuntimeError("HTTP 500")
        if path == "/unitsOfMeasure":
            return []
        return [{"attributeId": 176, "marketYear": 2026, "calendarYear": 2026, "month": 10, "value": 50.0, "unitId": 1}]
    monkeypatch.setattr(usda_psd, "_get", fake)
    df = usda_psd.fetch({"commodities": {"sugar": {"code": "0612000", "countries": ["world"]}}, "attributes": ["Ending Stocks"],
                         "history_from_my": 2026, "budget_s": 30}, since=None)
    assert set(df["series_id"]) == {"psd:sugar:world:ending-stocks:2026"} and "fallback" in df.attrs["notes"]


def test_condition_season_over_is_not_a_key_month(bbox):
    days = [date.fromisocalendar(y, w, 1) for y in range(2021, 2027) for w in (27, 28)]
    store.upsert_obs("nass", pd.concat([_nass_rows("WHEAT, WINTER - CONDITION, MEASURED IN PCT GOOD", [(d, 40) for d in days]),
                                        _nass_rows("WHEAT, WINTER - CONDITION, MEASURED IN PCT EXCELLENT", [(d, 10) for d in days])]))
    sec, al = balance.build(date(2026, 10, 16))
    row = next(r for r in sec["condition"] if r["crop"] == "Winter wheat")
    assert row["season_over"] and not row["key_month"]
    assert "season over" in "\n".join(balance.render(sec)) and "- pts" not in "\n".join(balance.render(sec))
