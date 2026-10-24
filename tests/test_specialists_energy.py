"""Specialists S1 (Energy): release dates, surprise definition, reaction base rates on synthetic data with a known
effect, no look-ahead, curve shape from stored contracts, and the input pack -> a valid state card (offline)."""
from __future__ import annotations

import json
import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from pmstack import cards, events, specialist, store
from pmstack.quant import curve

REL_WPSR = {"lag_days": 5, "holiday_window": [3, 5], "holiday_shift": {"Mon": 1, "Tue": 1, "Wed": 1}}
REL_GAS = {"lag_days": 6, "holiday_window": [3, 6], "holiday_shift": {"Mon": 0, "Tue": 1, "Wed": 1, "Thu": -1}}


def test_release_dates_and_holiday_shift():
    assert events.release_date(date(2026, 10, 16), REL_WPSR) == date(2026, 10, 21)       # Friday -> Wednesday
    assert events.release_date(date(2025, 8, 29), REL_WPSR) == date(2025, 9, 4)          # Labor Day Monday -> Thursday
    assert events.release_date(date(2026, 10, 16), REL_GAS) == date(2026, 10, 22)        # gas: Thursday
    assert events.release_date(date(2025, 11, 21), REL_GAS) == date(2025, 11, 26)        # Thanksgiving week: Wednesday
    assert events.release_date(date(2025, 8, 29), REL_GAS) == date(2025, 9, 4)           # Labor Day Monday: still Thursday
    assert events.release_date(date(2024, 12, 20), REL_GAS) == date(2024, 12, 27)        # Christmas Wednesday: Friday
    assert events.release_date(date(2024, 12, 20), {**REL_GAS, "exceptions": {"2024-12-20": "2024-12-26"}}) == date(2024, 12, 26)
    assert events.next_release(REL_WPSR, date(2026, 10, 24)) == "2026-10-28"


def _synthetic(tmp_path, monkeypatch, beta=-0.6, start="2008-01-04", end="2026-10-16", seed=3):
    """Weekly stocks with seasonality + noise; daily prices whose release-day return = beta * z + noise."""
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    rng = np.random.default_rng(seed)
    wk = pd.date_range(start, end, freq="W-FRI")
    season = 3000 * np.sin(2 * np.pi * np.array([d.isocalendar()[1] for d in wk]) / 52)
    chg = season + rng.normal(0, 2500, len(wk))
    lvl = 420000 + np.cumsum(chg - chg.mean())
    stocks = pd.DataFrame({"source": "eia", "series_id": "PET.WCESTUS1.W", "name": "x", "date": wk.date, "value": lvl,
                           "unit": "kbbl", "freq": "weekly", "source_url": "https://www.eia.gov/x", "fetched_at": pd.Timestamp("2026-10-20")})
    store.upsert_obs("eia", stocks)
    sur = events.surprises(pd.Series(lvl, index=wk.date), REL_WPSR, {"norm_years": 5}, date(2026, 10, 23))
    zmap = dict(zip(sur["release"], sur["z"]))
    days = pd.bdate_range(start, "2026-10-23")
    r = rng.normal(0, 1.8, len(days))
    for i, d in enumerate(days.date):
        if d in zmap and math.isfinite(zmap[d]):
            r[i] += beta * zmap[d]
    px = 80 * np.exp(np.cumsum(r / 100))
    prices = pd.DataFrame({"source": "prices", "series_id": "CL=F", "name": "WTI", "date": days.date, "value": px, "unit": "close",
                           "freq": "daily", "source_url": "https://finance.yahoo.com/quote/CL=F", "fetched_at": pd.Timestamp("2026-10-24")})
    store.upsert_obs("prices", prices)
    return sur


def test_surprise_matches_monitor_definition(tmp_path, monkeypatch):
    sur = _synthetic(tmp_path, monkeypatch)
    row = sur.iloc[-1]
    s = store.connect().execute("SELECT date, value FROM obs WHERE source='eia' ORDER BY date").df()
    s["chg"] = s["value"].diff()
    s["wk"] = pd.to_datetime(s["date"]).dt.isocalendar().week.astype(int)
    s["yr"] = pd.to_datetime(s["date"]).dt.year
    last = s.iloc[-1]
    hist = s[(s.yr >= last.yr - 5) & (s.yr < last.yr)]
    near = hist[(hist.wk - last.wk).abs().isin([0, 1]) | ((hist.wk - last.wk).abs() >= 51)]
    assert row["avg5_change"] == pytest.approx(near.chg.mean())
    assert row["z"] == pytest.approx((last.chg - near.chg.mean()) / near.chg.std(ddof=1))


def test_base_rates_recover_known_effect_and_placebo(tmp_path, monkeypatch):
    _synthetic(tmp_path, monkeypatch, beta=-0.6)
    out = events.run(date(2026, 10, 23), only=["wpsr"])
    row = out["reports"]["wpsr"]["pairs"]["crude_wti"]
    assert row["status"] == "ok" and row["events"] > 600
    lo, hi = row["slope_per_sd"]["ci90"]
    assert lo < -0.6 < hi                                                # the planted slope is inside the interval
    assert row["sign"]["hit_rate"] > 0.55
    assert abs(row["placebo"]["day_before"]["t"]) < 3                   # no effect planted the day before
    assert row["vol"]["ratio"] > 1


def test_base_rates_no_look_ahead(tmp_path, monkeypatch):
    _synthetic(tmp_path, monkeypatch, beta=-0.6)
    a = events.run(date(2020, 6, 30), only=["wpsr"])["reports"]["wpsr"]["pairs"]["crude_wti"]
    assert a["to"] <= "2020-06-30" and a["latest"]["release"] <= "2020-06-30"
    # appending later data must not change an earlier as-of result
    extra = pd.DataFrame({"source": "prices", "series_id": "CL=F", "name": "WTI", "date": [date(2026, 10, 26)], "value": [1.0],
                          "unit": "close", "freq": "daily", "source_url": "u", "fetched_at": pd.Timestamp("2026-10-27")})
    store.upsert_obs("prices", extra)
    b = events.run(date(2020, 6, 30), only=["wpsr"])["reports"]["wpsr"]["pairs"]["crude_wti"]
    assert a["slope_per_sd"] == b["slope_per_sd"] and a["events"] == b["events"]


def test_curve_shape_from_stored_contracts(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    d = date(2026, 10, 26)
    rows = [("CLZ26.NYM", 100.0), ("CLF27.NYM", 98.0), ("CLG27.NYM", 96.5), ("CLH27.NYM", 95.0), ("CLJ27.NYM", 94.0),
            ("CLK27.NYM", 93.0)]
    df = pd.DataFrame({"source": "prices_curve", "series_id": [r[0] for r in rows], "name": "x", "date": d,
                       "value": [r[1] for r in rows], "unit": "close", "freq": "daily",
                       "source_url": "https://finance.yahoo.com/quote/CLZ26.NYM", "fetched_at": pd.Timestamp("2026-10-24")})
    store.upsert_obs("prices_curve", df)
    sh = curve.shape("CL", d)
    assert sh["m1"] == "CLZ26.NYM" and sh["m1_m2"] == pytest.approx(2.0) and sh["m1_m6_pct"] == pytest.approx(7.0)
    assert sh["label"] == "backwardation"
    assert curve.shape("CL", date(2026, 10, 23)) is None                 # nothing before collection started
    assert curve.shape("CL", date(2026, 10, 25)) is None                 # nothing before the first stored day


def test_pack_numbers_make_a_valid_card(tmp_path, monkeypatch):
    _synthetic(tmp_path, monkeypatch, beta=-0.6)
    briefs = tmp_path / "briefs" / "2026-10-23"
    briefs.mkdir(parents=True)
    facts = {"asof_brt": "2026-10-23", "alerts": [], "sections": {
        "prices": [{"id": "CL=F", "name": "WTI front month", "date": "2026-10-23", "last": 103.44, "ret1_pct": 3.99, "ret5_pct": 2.0,
                    "source_url": "https://finance.yahoo.com/quote/CL=F"}],
        "balance": {"oil": {"stocks": [{"id": "PET.WCESTUS1.W", "label": "US crude ex SPR", "markets": ["CL=F", "BZ=F"],
                                        "week_ending": "2026-10-16", "level": 412517.0, "unit": "kbbl", "change": -3060.0,
                                        "avg5_change": 66.8, "vs_avg_pct": -3.7, "z_sd": -2.1,
                                        "source_url": "https://www.eia.gov/x"}]}},
        "cftc": [{"code": "067651", "name": "WTI crude (NYMEX)", "date": "2026-10-20", "mm_net_pct_oi": 1.97, "pct_3y": 14.1,
                  "wow_change_pp": -0.16, "source_url": "https://www.cftc.gov/x"}]}}
    (briefs / "facts.json").write_text(json.dumps(facts), encoding="utf-8")
    pk = specialist.build("energy", date(2026, 10, 23), "how tight is crude?", briefs=tmp_path / "briefs")
    assert pk["fact_pack"] == "2026-10-23" and "balance" in pk["groups"] and "events" in pk["groups"]
    ids = {s["label"]: s["id"] for s in pk["sources"]}
    z_id = ids["US crude ex SPR vs 5-year average"] if "US crude ex SPR vs 5-year average" in ids else None
    lvl = next(s for s in pk["sources"] if s["label"] == "US crude ex SPR stocks")
    sd = next(s for s in pk["sources"] if s["label"] == "US crude ex SPR vs 5-year average" and s["unit"] == "sd")
    pos = next(s for s in pk["sources"] if "3-year percentile" in s["label"])
    card = {**pk["card_template"], "author": "energy/test",
            "balance_view": {"text": f"US crude stocks sit {abs(sd['value'])} sd below the 5-year average [{sd['id']}].", "state": "tight"},
            "curve_shape": {"text": "No stored curve yet.", "state": "unknown"},
            "positioning": {"text": f"Managed money at the {pos['value']} percentile of three years [{pos['id']}]."},
            "narrative_stage": {"text": "No narrative on the map touches crude today."},
            "what_changed": [], "would_change_view": ["A 4-week run of builds above the seasonal norm."],
            "next_events": pk["next_events"][:1], "confidence": "medium", "sources": [lvl, sd, pos]}
    assert z_id is not None
    assert cards.validate(card, today=date(2026, 10, 24)) == []
    # a figure the pack does not hold is rejected
    card["what_changed"] = ["Stocks are 9.9% below normal."]
    assert any("9.9" in p for p in cards.validate(card, today=date(2026, 10, 24)))


def test_pack_is_point_in_time(tmp_path, monkeypatch):
    _synthetic(tmp_path, monkeypatch)
    root = tmp_path / "briefs"
    for d in ("2026-10-20", "2026-10-23"):
        (root / d).mkdir(parents=True)
        (root / d / "facts.json").write_text(json.dumps({"asof_brt": d, "alerts": [], "sections": {}}), encoding="utf-8")
    pk = specialist.build("energy", date(2026, 10, 21), briefs=root)
    assert pk["fact_pack"] == "2026-10-20"
    assert all(s["date"] is None or s["date"] <= "2026-10-21" for s in pk["sources"])
