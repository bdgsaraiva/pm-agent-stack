"""Specialists S3 (Metals): SHFE and Pink Sheet parsers, the Westmetall month-name fix, NBS PMI dates, China-day
volatility, stock surprises without look-ahead, the storage fit on synthetic data, long-run availability lags, and the
metals pack -> a valid state card (offline)."""
from __future__ import annotations

import io
import json
import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from pmstack import cards, events, metals, specialist, store
from pmstack.adapters import pinksheet, shfe, westmetall

FETCHED = pd.Timestamp("2026-10-24")


def _rows(source, sid, dates, values, unit="t"):
    return pd.DataFrame({"source": source, "series_id": sid, "name": sid, "date": list(dates), "value": list(values), "unit": unit,
                         "freq": "daily", "source_url": "https://example.org/" + sid, "fetched_at": FETCHED})


# ------------------------------------------------------------------ parsers
def test_westmetall_month_names_keep_january_and_february():
    assert westmetall._date("2. January 2026") == date(2026, 1, 2)          # was "Januaryy" -> dropped (25 Oct fix)
    assert westmetall._date("27. February 2025") == date(2025, 2, 27)
    assert westmetall._date("27. Februar 2025") == date(2025, 2, 27)
    assert westmetall._date("1. Mai 2023") == date(2023, 5, 1)
    assert westmetall._date("15. May 2023") == date(2023, 5, 15)


def test_shfe_parsers_both_formats():
    js = {"o_cursor": [
        {"VARID": "cu      ", "VARNAME": "铜$$COPPER", "WHABBRNAME": "完税商品总计$$Total (Tax included)", "SPOTWGHTS": 100, "WRTWGHTS": 50},
        {"VARID": "cu      ", "VARNAME": "铜$$COPPER", "WHABBRNAME": "总计$$Total", "SPOTWGHTS": 110, "WRTWGHTS": 55},
        {"VARNAME": "铝$$ALUMINIUM", "WHABBRNAME": "总计$$Total", "SPOTWGHTS": 200, "WRTWGHTS": 80},     # 2015 format: no VARID
        {"VARID": "zn", "VARNAME": "锌$$ZINC", "WHABBRNAME": "总计$$Total", "SPOTWGHTS": 9, "WRTWGHTS": 9}],
        "o_cursorau": [{"WRTWGHTS": 1140}]}
    assert shfe.parse_dat(js) == {"cu_stock": 110.0, "cu_warrants": 55.0, "al_stock": 200.0, "al_warrants": 80.0, "au_warrants": 1140.0}
    page = ("<table><tr><td>铜</td><td>单位：吨</td></tr><tr><td>上海</td><td>中储</td><td>1</td><td>2</td><td>3</td><td>4</td></tr>"
            "<tr><td>完税商品总计</td><td>70</td><td>30</td><td>50</td><td>20</td><td>-20</td><td>-10</td></tr>"
            "<tr><td>总计</td><td>73962</td><td>36386</td><td>54356</td><td>19058</td><td>-19606</td><td>-17328</td></tr>"
            "<tr><td>铝</td><td>单位：吨</td></tr><tr><td>总计</td><td>1</td><td>2</td><td>212858</td><td>68242</td><td>0</td><td>0</td></tr>"
            "<tr><td>黄金</td><td>单位：千克</td><td>116928</td><td>116904</td><td>-24</td></tr></table>")
    assert shfe.parse_html(page) == {"cu_stock": 54356.0, "cu_warrants": 19058.0, "al_stock": 212858.0, "al_warrants": 68242.0,
                                     "au_warrants": 116904.0}


def test_pinksheet_parse():
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Monthly Prices"
    ws.append(["World Bank Commodity Price Data (The Pink Sheet)"])
    ws.append([None, "Crude oil, average", "Copper", "Iron ore, cfr spot"])
    ws.append([None, "($/bbl)", "($/mt)", "($/dmtu)"])
    ws.append(["1960M01", 1.6, 715, "…"])
    ws.append(["2026M09", 70.1, 10123.4, 101.5])
    buf = io.BytesIO()
    wb.save(buf)
    rows, errors = pinksheet.parse(buf.getvalue(), [{"key": "copper", "column": "Copper"}, {"key": "iron_ore", "column": "Iron ore"},
                                                    {"key": "gold", "column": "Gold"}], "https://x", FETCHED)
    got = {(r["series_id"], str(r["date"])): r["value"] for r in rows}
    assert got == {("wb:copper", "1960-01-01"): 715.0, ("wb:copper", "2026-09-01"): 10123.4, ("wb:iron_ore", "2026-09-01"): 101.5}
    assert errors and "gold" in errors[0]


# ------------------------------------------------------------------ China data days
def test_pmi_dates_rule_exceptions_and_asof():
    spec = {"from": "2024-01-01", "exceptions": {"2024-02": "2024-03-01"}}
    d = metals.pmi_dates(spec, date(2024, 6, 29))
    assert d[0] == date(2024, 1, 31) and d[1] == date(2024, 3, 1) and d[2] == date(2024, 3, 31)
    assert d[-1] == date(2024, 5, 31)                                       # June's release (30th) is after the as-of date


def test_day_vol_detects_event_volatility_and_placebo():
    rng = np.random.default_rng(1)
    days = pd.bdate_range("2012-01-02", "2026-10-23").date
    ev = metals.pmi_dates({"from": "2012-01-01"}, date(2026, 10, 23))
    idx = pd.Index(days)
    on = {days[min(p, len(days) - 1)] for p in idx.searchsorted(ev)}
    r = np.array([rng.normal(0, 3.0 if d in on else 1.0) for d in days])
    px = pd.Series(100 * np.exp(np.cumsum(r / 100)), index=days)
    st = {"vol_window": 60, "outlier_sd": 8, "big_move_sd": 1.5, "min_events": 30}
    rets = events.returns(px, st)
    out = metals.day_vol(rets, ev, st)
    assert out["ratio"] > 2 and out["levene_p"] < 0.01
    assert abs(metals.day_vol(rets, ev, st, 5)["ratio"] - 1) < 0.25          # shifted days: no effect


# ------------------------------------------------------------------ stocks and storage
def test_daily_stock_surprise_uses_only_past_norm():
    days = pd.bdate_range("2020-01-01", "2026-10-23").date
    rng = np.random.default_rng(2)
    s = pd.Series(300000 + np.cumsum(rng.normal(0, 2000, len(days))), index=days)
    st = {"daily_norm_days": 250}
    a = metals.stock_surprises(s, "daily", st, date(2026, 10, 23))
    s2 = s.copy()
    s2.iloc[-1] += 50000                                                    # a change on the last day...
    b = metals.stock_surprises(s2, "daily", st, date(2026, 10, 23))
    pd.testing.assert_series_equal(a["z"].iloc[:-1], b["z"].iloc[:-1])      # ...never moves an earlier day's z
    assert b["z"].iloc[-1] > a["z"].iloc[-1]
    c = metals.stock_surprises(s, "daily", st, date(2025, 6, 30))
    assert max(c["release"]) <= date(2025, 6, 30)


def _storage_store(tmp_path, monkeypatch, slope=-0.6, seed=4):
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2014-01-01", "2026-10-23").date
    lme = np.exp(np.log(250000) + np.cumsum(rng.normal(0, 0.01, len(days))))
    fris = [d for d in days if d.weekday() == 4]
    shfe_v = np.exp(np.log(100000) + np.cumsum(rng.normal(0, 0.03, len(fris))))
    shfe_map = dict(zip(fris, shfe_v))
    tot = np.array([l + shfe_map.get(d - timedelta(days=(d.weekday() - 4) % 7), 100000) for d, l in zip(days, lme)])
    spread = 0.3 + slope * (np.log(tot / 1000) - np.log(350)) + rng.normal(0, 0.15, len(days))
    m3 = 9000 * np.exp(np.cumsum(rng.normal(0, 0.012, len(days))))
    cash = m3 * (1 + spread / 100)
    store.upsert_obs("lme", pd.concat([_rows("lme", "lme:copper_stock", days, lme), _rows("lme", "lme:copper_3m", days, m3, "USD/t"),
                                       _rows("lme", "lme:copper_cash", days, cash, "USD/t")]))
    store.upsert_obs("shfe", _rows("shfe", "shfe:cu_stock", fris, shfe_v))
    store.upsert_obs("fred", _rows("fred", "DTB3", days, np.zeros(len(days)), "pct"))   # zero rates: net spread = raw spread
    return days


def test_storage_fit_recovers_slope_and_is_point_in_time(tmp_path, monkeypatch):
    _storage_store(tmp_path, monkeypatch, slope=-0.6)
    c = metals.cfg()
    out = metals.storage("copper", date(2026, 10, 23), store.connect(), c)
    f = out["fits"]["spread_pct"]
    assert out["status"] == "ok" and -0.75 < f["slope_per_log_stock"] < -0.45 and f["t"] < -5
    assert f["signs_agree"] and f["resid_stationary_5pct"]
    assert abs(out["now"]["spread_minus_implied_pp"]) < 0.6 and out["now"]["implied_suppressed"] is None
    assert out["now"]["implied_fit_window"][1] < "2026-10-23"              # today is scored out of sample
    early = metals.storage("copper", date(2020, 6, 30), store.connect(), c)
    assert early["to"] <= "2020-06-30" and early["weeks"] < out["weeks"]


def test_storage_spread_is_carry_adjusted_and_weak_fit_suppressed(tmp_path, monkeypatch):
    days = _storage_store(tmp_path, monkeypatch, slope=0.0)                  # no storage relation at all
    store.upsert_obs("fred", _rows("fred", "DTB3", days, np.full(len(days), 4.0), "pct"))
    out = metals.storage("copper", date(2026, 10, 23), store.connect(), metals.cfg())
    n = out["now"]
    assert abs(n["spread_pct"] - (n["raw_spread_pct"] + 4.0 * 91 / 360)) < 0.002
    assert n["inventory_implied_spread_pct"] is None and n["implied_suppressed"]   # a weak fit is never quoted


def test_shfe_changes_across_holiday_gaps_are_dropped():
    fris = pd.date_range("2014-01-03", "2026-10-23", freq="W-FRI").date
    gap = {d for d in fris if d.month == 2 and d.day <= 7}                     # one skipped week every February
    keep = [d for d in fris if d not in gap]
    s = pd.Series(np.cumsum(np.random.default_rng(7).normal(0, 1000, len(keep))) + 1e5, index=keep)
    sur = metals.stock_surprises(s, "weekly", {"norm_years": 5}, date(2026, 10, 23))
    spans = {b: (b - a).days for a, b in zip(keep[:-1], keep[1:])}
    assert all(spans[d] <= 10 for d in sur["week_ending"])
    assert min(sur["week_ending"]) >= date(2020, 1, 1)                          # 5 full prior years of reports


def test_longrun_respects_availability():
    con = None
    months = pd.date_range("1960-01-01", "2026-09-01", freq="MS").date

    class Con:                                                               # minimal stand-in for the DuckDB view
        def __init__(self, frames):
            self.df_ = pd.concat(frames)

        def execute(self, sql, args):
            src, sid, until = args
            d = self.df_[(self.df_["source"] == src) & (self.df_["series_id"] == sid) & (self.df_["date"] <= until)]

            class R:
                def df(_):
                    return d[["date", "value"]].reset_index(drop=True)
            return R()
    nom = _rows("pinksheet", "wb:gold", months, np.linspace(35, 4000, len(months)))
    cpi = _rows("fred", "CPIAUCSL", months, np.linspace(30, 320, len(months)))
    con = Con([nom, cpi])
    c = metals.cfg()
    a = metals.longrun("gold", "wb:gold", date(2026, 10, 5), con, c)        # September is out about 7 days after the month
    b = metals.longrun("gold", "wb:gold", date(2026, 10, 9), con, c)
    assert a["month"] == "2026-08" and b["month"] == "2026-09"
    assert b["real_pctile_since_1960"] == 100


# ------------------------------------------------------------------ pack -> card
def test_metals_pack_makes_a_valid_card_and_is_point_in_time(tmp_path, monkeypatch):
    days = _storage_store(tmp_path, monkeypatch)
    px = 4.5 * np.exp(np.cumsum(np.random.default_rng(5).normal(0, 0.015, len(days))))
    store.upsert_obs("prices", _rows("prices", "HG=F", days, px, "close"))
    briefs = tmp_path / "briefs" / "2026-10-23"
    briefs.mkdir(parents=True)
    facts = {"asof_brt": "2026-10-23", "alerts": [], "sections": {
        "prices": [{"id": "HG=F", "name": "Copper front month", "date": "2026-10-23", "last": 6.49, "ret1_pct": 2.1, "ret5_pct": -0.5,
                    "source_url": "https://finance.yahoo.com/quote/HG=F"}],
        "cftc": [{"code": "085692", "name": "Copper (COMEX)", "date": "2026-10-20", "mm_net_pct_oi": 14.6, "pct_3y": 48.7,
                  "wow_change_pp": -4.9, "source_url": "https://www.cftc.gov/x"}]}}
    (briefs / "facts.json").write_text(json.dumps(facts), encoding="utf-8")
    pk = specialist.build("metals", date(2026, 10, 23), "how tight is copper?", briefs=tmp_path / "briefs")
    assert {"storage", "stocks", "positioning", "prices"} <= set(pk["groups"]) and pk["commodities"] == ["copper"]
    by = {s["label"]: s for s in pk["sources"]}
    sp = by["LME Copper spread net of interest (raw spread + T-bill x 91/360; positive = backwardation)"]
    vis = by["Visible Copper stocks, percentile since 2014"]
    pos = next(s for s in pk["sources"] if "3-year percentile" in s["label"])
    card = {**pk["card_template"], "author": "metals/test",
            "balance_view": {"text": f"Visible stocks sit at the {vis['value']} percentile since 2014 [{vis['id']}].", "state": "balanced"},
            "curve_shape": {"text": f"The LME spread is {sp['value']}% of the 3-month price [{sp['id']}].", "state": "backwardation"},
            "positioning": {"text": f"Managed money at the {pos['value']} percentile of three years [{pos['id']}]."},
            "narrative_stage": {"text": "No metals narrative on the map today."},
            "what_changed": [], "would_change_view": ["Visible stocks rising while the spread holds."],
            "next_events": pk["next_events"][:1], "confidence": "medium", "sources": [vis, sp, pos]}
    assert cards.validate(card, today=date(2026, 10, 24), packs=[pk]) == []
    card["what_changed"] = ["Stocks fell 12.3% this week."]
    assert any("12.3" in p for p in cards.validate(card, today=date(2026, 10, 24), packs=[pk]))
    early = specialist.build("metals", date(2025, 3, 3), "how tight is copper?", briefs=tmp_path / "briefs")
    assert early["fact_pack"] is None
    assert all(s["date"] is None or s["date"] <= "2025-03-03" for s in early["sources"])


def test_routing_reaches_metals():
    from pmstack import route
    r = route.route("is the LME aluminium backwardation explained by stocks?")
    assert r["specialist"] == "metals" and r["commodities"][0] == "aluminium"
    r = route.route("metals: where is gold in its long-run range?")
    assert r["specialist"] == "metals" and "gold" in r["commodities"]
