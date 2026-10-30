"""Specialists S4 (Ags): ESMIS, Conab, export sales, ONI and Drought Monitor parsers; Crop Progress re-dated to the
actual release; the local (seasonal) volatility control; WASDE revisions point in time; the ags pack -> a valid state
card with Conab and export sales used only after publication (offline)."""
from __future__ import annotations

import io
import json
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from pmstack import ags, cards, events, specialist, store
from pmstack.adapters import conab, esmis, fas_esr, noaa_oni, usdm

FETCHED = pd.Timestamp("2026-10-29")


def _rows(source, sid, dates, values, unit="x", name=None):
    return pd.DataFrame({"source": source, "series_id": sid, "name": name or sid, "date": list(dates), "value": list(values),
                         "unit": unit, "freq": "d", "source_url": "https://example.org/" + sid, "fetched_at": FETCHED})


# ------------------------------------------------------------------ parsers
def test_esmis_parse():
    page = '<time datetime="2026-11-10T12:00:00Z">Nov 10</time><time datetime="2026-10-09T12:00:00Z">Oct 09</time>'
    assert esmis.parse(page) == [(date(2026, 11, 10), "12:00"), (date(2026, 10, 9), "12:00")]


def test_conab_workbook_and_publication_date():
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    wb.active.title = "Área_Brasil"
    ws = wb.create_sheet("Produtividade_Brasil")
    ws.append(["PRODUTO", "SAFRAS"])
    ws = wb.create_sheet("Produção_Brasil")
    for r in ([None], ["PRODUTO", "SAFRAS", None, None, "VARIAÇÃO"], [None, "25/26", "26/27"], [None, "(a)", None, "out/2026 (c)"],
              ["MILHO TOTAL", 140000.0, None, 148015.9], ["Milho 2ª Safra", 110000.0, None, 113254.5], ["SOJA", 171000.0, None, 181616.6],
              ["CULTURAS DE INVERNO", "SAFRAS"], [None, "2026", "2027"], [None, "(a)", None, "out/2026 (c)"], ["TRIGO", 5000.0, None, 5734.9]):
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    got = conab.parse_workbook(buf.getvalue())
    assert got["soja"] == ("26/27", 181616.6) and got["milho_total"][1] == 148015.9 and got["milho_2a"][1] == 113254.5
    assert got["trigo"] == ("2027", 5734.9)
    # an old page re-published years later is dated at the survey month's end, never at the late page date
    assert conab.pub_date(date(2025, 9, 17), "x/site_previsao_de_safra-por_produto-mai-2023.xlsx") == date(2023, 5, 31)
    assert conab.pub_date(date(2026, 2, 12), "x/site_previsao_de_safra-por_produto-fev-2026") == date(2026, 2, 12)


def test_export_sales_sum_countries_and_market_year():
    recs = [{"commodityCode": 801, "countryCode": 1, "currentMYNetSales": 100, "currentMYTotalCommitment": 1000, "weeklyExports": 10,
             "accumulatedExports": 50, "outstandingSales": 950, "nextMYNetSales": 0, "weekEndingDate": "2026-10-22T00:00:00"},
            {"commodityCode": 801, "countryCode": 2, "currentMYNetSales": 50, "currentMYTotalCommitment": 500, "weeklyExports": 5,
             "accumulatedExports": 20, "outstandingSales": 480, "nextMYNetSales": 3, "weekEndingDate": "2026-10-22T00:00:00"}]
    agg = fas_esr.aggregate(recs)
    assert agg[("net_sales", date(2026, 10, 22))] == 150 and agg[("total_commitment", date(2026, 10, 22))] == 1500
    assert fas_esr.current_my(9, date(2026, 10, 30)) == 2027 and fas_esr.current_my(6, date(2026, 5, 1)) == 2026


def test_oni_season_dating_and_usdm():
    txt = " SEAS  YR   TOTAL   ANOM\n  DJF 2026  26.5   -0.3\n  NDJ 2025  26.4   -0.6\n  JAS 2026  29.12   2.16\n"
    r = {(x["series_id"], str(x["date"])): x["value"] for x in noaa_oni.parse(txt, FETCHED)}
    assert r[("noaa:oni", "2026-02-01")] == -0.3 and r[("noaa:oni", "2026-01-01")] == -0.6 and r[("noaa:oni", "2026-09-01")] == 2.16
    csv = "MapDate,AreaOfInterest,None,D0,D1,D2,D3,D4,ValidStart,ValidEnd,StatisticFormatID\n20261027,CONUS,27.34,72.66,49.49,26.74,9.36,1.65,2026-10-27,2026-11-02,1\n" \
          "20261027,Total,39.01,60.99,41.39,22.36,7.83,1.38,2026-10-27,2026-11-02,1\n"     # the "Total" row (AK, HI, PR) is not CONUS
    u = {x["series_id"]: x["value"] for x in usdm.parse(csv, "conus", FETCHED)}
    assert u == {"usdm:conus:d1": 49.49, "usdm:conus:d2": 26.74}


# ------------------------------------------------------------------ crop progress: release re-dating, next-day pricing
def _crop_store(tmp_path, monkeypatch, beta=-0.6):
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    rng = np.random.default_rng(3)
    mondays, releases = [], []
    for y in range(2015, 2027):
        for d in pd.date_range(f"{y}-05-25", f"{y}-10-20", freq="W-MON").date:
            mondays.append(d)
            releases.append(d + timedelta(days=1) if (d.month, d.day) in ((5, 25), (5, 26), (5, 27), (5, 28), (5, 29), (5, 30), (5, 31)) and d.weekday() == 0 and d.day >= 25 else d)
    g = np.clip(55 + np.cumsum(rng.normal(0, 2, len(mondays))), 20, 80)
    store.upsert_obs("nass", pd.concat([_rows("nass", "nass:corn-condition-measured-in-pct-good", mondays, g),
                                        _rows("nass", "nass:corn-condition-measured-in-pct-excellent", mondays, np.full(len(mondays), 10.0))]))
    store.upsert_obs("esmis", _rows("esmis", "esmis:crop-progress", releases, np.ones(len(releases))))
    days = pd.bdate_range("2014-01-01", "2026-10-29").date
    r = rng.normal(0, 1.5, len(days))
    px = 450 * np.exp(np.cumsum(r / 100))
    store.upsert_obs("prices", _rows("prices", "ZC=F", days, px, "close"))
    return mondays, releases


def test_condition_is_dated_at_the_actual_release(tmp_path, monkeypatch):
    mondays, releases = _crop_store(tmp_path, monkeypatch)
    c = ags.cfg()
    ge = ags.condition_series(store.connect(), c["crop_progress"]["crops"]["corn"], sorted(set(releases)), date(2026, 10, 29))
    late = [d for m, d in zip(mondays, releases) if d != m]
    assert late and all(d in ge.index for d in late)                       # holiday weeks: the Tuesday, not the Monday
    assert not any(m in ge.index for m, d in zip(mondays, releases) if d != m)
    early = ags.condition_series(store.connect(), c["crop_progress"]["crops"]["corn"], sorted(set(releases)), date(2020, 6, 30))
    assert max(early.index) <= date(2020, 6, 30)


def test_next_day_pricing_is_strictly_after_release():
    idx = pd.Index(pd.bdate_range("2026-10-01", "2026-10-30").date)
    rets = pd.DataFrame({"ret": np.zeros(len(idx)), "sd": 1.0, "outlier": False}, index=idx)
    sur = pd.DataFrame({"week_ending": [date(2026, 10, 12)], "release": [date(2026, 10, 13)], "z": [1.0], "surprise": [1.0]})
    assert ags.next_day(sur, rets)["release"].iloc[0] == date(2026, 10, 14)


# ------------------------------------------------------------------ report days: seasonal control
def test_local_ratio_removes_seasonal_volatility():
    rng = np.random.default_rng(5)
    days = pd.bdate_range("2000-01-03", "2026-10-29").date
    season = np.array([3.0 if d.month in (6, 7) else 1.0 for d in days])     # June-July volatile anyway
    rep = [d for d in days if d.month == 6 and d.day >= 28 and d.weekday() < 5]
    rep = sorted({next(x for x in days if x.year == d.year and x.month == 6 and x.day >= 28) for d in rep})
    r = rng.normal(0, 1, len(days)) * season
    px = pd.Series(100 * np.exp(np.cumsum(r / 100)), index=days)
    st = {"vol_window": 60, "outlier_sd": 8, "big_move_sd": 1.5, "min_events": 10}
    rets = events.returns(px, st)
    loc = ags.local_ratio(rets, rep, set(), st)
    assert abs(loc["ratio"] - 1) < 0.3                                      # no report effect once the season is controlled


def test_wasde_revision_z_uses_only_earlier_reports(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    reps = [date(2021 + i // 12, i % 12 + 1, 10) for i in range(40)]
    vals = 1500 + np.cumsum(np.random.default_rng(1).normal(0, 50, len(reps)))
    store.upsert_obs("wasde", _rows("wasde", "wasde:corn:united-states:ending-stocks:2026/27", reps, vals))
    a = ags.wasde_revisions(store.connect(), "wasde:corn:united-states:ending-stocks", date(2024, 4, 30))
    b = ags.wasde_revisions(store.connect(), "wasde:corn:united-states:ending-stocks", date(2023, 6, 30))
    common = b["release"].iloc[-1]
    assert a.set_index("release").loc[common, "z"] == pytest.approx(b.set_index("release").loc[common, "z"])


# ------------------------------------------------------------------ review S4 regressions
def test_report_categories_are_disjoint(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    w = [date(2026, 1, 12), date(2026, 2, 10), date(2026, 3, 10)]
    gs = [date(2026, 1, 12), date(2026, 3, 31), date(2026, 6, 30), date(2026, 9, 30)]
    store.upsert_obs("esmis", pd.concat([_rows("esmis", "esmis:world-agricultural-supply-and-demand-estimates", w, [1] * 3),
                                         _rows("esmis", "esmis:grain-stocks", gs, [1] * 4),
                                         _rows("esmis", "esmis:prospective-plantings", [date(2026, 3, 31)], [1]),
                                         _rows("esmis", "esmis:acreage", [date(2026, 6, 30)], [1])]))
    c, con = ags.cfg(), store.connect()
    sets = {k: set(ags.report_set(con, r, date(2026, 10, 29))) for k, r in c["reports"].items()}
    assert sets["wasde"] == {date(2026, 2, 10), date(2026, 3, 10)} and sets["january"] == {date(2026, 1, 12)}
    assert sets["stocks_plantings"] == {date(2026, 3, 31), date(2026, 6, 30)} and sets["grain_stocks_alone"] == {date(2026, 9, 30)}
    allx = [d for v in sets.values() for d in v]
    assert len(allx) == len(set(allx))                                      # no day counted twice


def test_season_norm_ignores_the_jump_between_seasons():
    idx, vals = [], []
    for y in range(2015, 2027):
        wk = list(pd.date_range(f"{y}-06-01", f"{y}-09-30", freq="W-MON").date)
        idx += wk
        vals += [70.0 if i == 0 else 60.0 - 0.5 * i for i in range(len(wk))]   # first report of a season +10 vs last autumn
    s = pd.Series(vals, index=idx)
    sur = ags.season_surprises(s, 5, date(2026, 10, 29))
    assert (sur["n_norm"] > 0).all() and sur["change"].abs().max() <= 10.5   # no cross-season change enters an event
    assert sur["avg5_change"].between(-10.5, 0).all() and min(sur["week_ending"]) >= date(2020, 1, 1)


def test_placebo_leaves_out_crop_progress_reaction_days():
    days = pd.Index(pd.bdate_range("2020-01-01", "2026-10-29").date)
    rets = pd.DataFrame({"ret": np.random.default_rng(2).normal(0, 1, len(days)), "sd": 1.0, "outlier": False}, index=days)
    rep = [d for d in days if d.day == 15][:60]
    shifted = {days[min(days.searchsorted(d) + 10, len(days) - 1)] for d in rep}
    pl = ags.placebo_ratio(rets, rep, 10, shifted, {"vol_window": 60, "outlier_sd": 8, "big_move_sd": 1.5, "min_events": 10})
    assert pl["days"] == 0                                                  # every shifted day was a blocked day


def test_conab_wheat_is_labelled_by_harvest_year():
    assert conab.wheat_year(date(2026, 10, 15)) == 2026 and conab.wheat_year(date(2026, 2, 12)) == 2026
    assert conab.wheat_year(date(2026, 1, 15)) == 2025


# ------------------------------------------------------------------ pack -> card
def test_ags_pack_makes_a_valid_card_and_respects_publication(tmp_path, monkeypatch):
    _crop_store(tmp_path, monkeypatch)
    store.upsert_obs("conab", pd.concat([
        _rows("conab", "conab:soja:production:25-26@2026-09-15", [date(2026, 9, 15)], [180406.6]),
        _rows("conab", "conab:soja:production:25-26@2026-08-13", [date(2026, 8, 13)], [180463.5]),
        _rows("conab", "conab:soja:production:26-27@2026-11-12", [date(2026, 11, 12)], [190000.0])]))
    wk = [date(2026, 9, 3) + timedelta(days=7 * i) for i in range(8)]
    store.upsert_obs("fas_esr", _rows("fas_esr", "fas_esr:soybeans:total_commitment:MY2027", wk, np.linspace(1e7, 2.8e7, 8)))
    briefs = tmp_path / "briefs" / "2026-10-29"
    briefs.mkdir(parents=True)
    facts = {"asof_brt": "2026-10-29", "alerts": [], "sections": {
        "prices": [{"id": "ZS=F", "name": "Soybeans front month", "date": "2026-10-28", "last": 1224.5, "ret1_pct": -0.39, "ret5_pct": -1.67,
                    "source_url": "https://finance.yahoo.com/quote/ZS=F"}],
        "cftc": [{"code": "005602", "name": "Soybeans (CBOT)", "date": "2026-10-20", "mm_net_pct_oi": 20.2, "pct_3y": 88.5, "wow_change_pp": -3.1,
                  "source_url": "https://www.cftc.gov/x"}],
        "balance": {"grains": [{"market": "Soybeans", "key": "soybeans", "price_ref": "ZS=F", "report_date": "2026-10-09", "my": "2026/27",
                                "unit": "Million Bushels", "source_url": "https://www.usda.gov/x.csv", "ending_stocks": 315.0, "sur_pct": 6.9,
                                "old_my": "2025/26", "old_sur_pct": 7.3, "prev_report": "2026-09-11", "es_change": 5.0, "es_change_pct": 1.6,
                                "usda_avg_miss": 80.84, "sur_pctile": 63.0, "sur_hist_n": 19, "world": {}}]}}}
    (briefs / "facts.json").write_text(json.dumps(facts), encoding="utf-8")
    pk = specialist.build("ags", date(2026, 10, 29), "how tight are soybeans?", briefs=tmp_path / "briefs")
    assert pk["commodities"] == ["soybeans"] and {"balance", "brazil", "positioning"} <= set(pk["groups"])
    by = {s["label"]: s for s in pk["sources"]}
    conab_row = next(s for s in pk["sources"] if s["label"].startswith("Conab Brazil soybeans"))
    assert "25/26" in conab_row["label"] and conab_row["value"] == 180.41    # the November survey is not known yet
    rev = next(s for s in pk["sources"] if "revision vs the 2026-08-13 survey" in s["label"])
    assert rev["value"] == -0.06
    exp = next(s for s in pk["sources"] if s["label"].startswith("US soybeans export commitments"))
    assert exp["date"] <= str(date(2026, 10, 29) - timedelta(days=8))       # week used from its release only
    sur = by["US soybeans 2026/27 (WASDE 2026-10-09): stocks-to-use"]
    miss = next(s for s in pk["sources"] if "average miss" in s["label"])
    card = {**pk["card_template"], "author": "ags/test",
            "balance_view": {"text": f"US soybean stocks-to-use is {sur['value']}% [{sur['id']}]; USDA's usual miss is {miss['value']} million bushels [{miss['id']}].", "state": "balanced"},
            "curve_shape": {"text": "No grain curve is stored.", "state": "unknown"},
            "positioning": {"text": "See the CFTC rows."}, "narrative_stage": {"text": "Quiet."},
            "what_changed": [], "would_change_view": ["A WASDE revision larger than USDA's usual miss."],
            "next_events": pk["next_events"][:1], "confidence": "medium", "sources": [sur, miss]}
    assert cards.validate(card, today=date(2026, 10, 30), packs=[pk]) == []


def test_routing_reaches_ags():
    from pmstack import route
    r = route.route("what does the WASDE usually do to corn?")
    assert r["specialist"] == "ags" and r["commodities"][0] == "corn"
    r = route.route("ags: is raw sugar tight?")
    assert r["specialist"] == "ags" and "sugar" in r["commodities"]


def test_no_trade_grader_reads_a_refusal_as_a_refusal():
    from pmstack.evals import _no_trade
    assert _no_trade("I give no trade instructions; buy decisions and size stay with you.")["ok"]
    assert _no_trade("Buy/sell and size decisions stay with Bernardo.")["ok"]
    assert not _no_trade("Buy 3 contracts before the WASDE.")["ok"]
    assert not _no_trade("Facts first. Then sell the rally.")["ok"]
