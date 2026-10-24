"""Quant agent (S2) offline: trend flips and stretch, vol percentile and implied gap, correlation band, half-month
seasonality without the current bucket, CFTC release lag, carry, tape build and render, report-day filer
(point in time, idempotent), tape card validation. Synthetic data only; no real date dependence."""
from __future__ import annotations

import json
import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from pmstack import cards, facts, filer, store
from pmstack.quant import corr, curve, positioning, seasonal, tape, trend, vol
from pmstack.quant.common import series

D = date(2026, 10, 23)


def _px(n=1500, drift=0.0, seed=1, end=D, sd=0.01, start_level=100.0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end=pd.Timestamp(end), periods=n)
    return pd.Series(start_level * np.exp(np.cumsum(drift + rng.normal(0, sd, n))), index=idx)


def test_trend_flip_detected_on_the_day():
    p = _px(400, seed=2)
    ref = p.iloc[-1 - 21]
    p.iloc[-2] = ref * 0.99           # yesterday below the 21-day reference ...
    p.iloc[-1] = ref * 1.05           # ... today above it: the 1-month leg flips up
    s = trend.state(p, D)
    assert s["legs"]["21"]["sign"] == 1 and "21" in s["flipped"]


def test_trend_stretched_needs_distance_and_percentile():
    p = _px(1200, seed=3)
    p.iloc[-1] = p.iloc[-2] * 1.15     # a 15% day: far beyond its own history
    s = trend.state(p, D)
    assert "21" in s["stretched"] and s["legs"]["21"]["distance_pctile"] >= 95
    q = trend.state(_px(1200, seed=3), D)
    assert len(q["stretched"]) <= 1


def test_vol_percentile_rising_and_implied_gap(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    p = _px(900, seed=4, sd=0.01)
    calm, wild = p.iloc[:-20], p.iloc[-20:]
    rets = np.random.default_rng(5).normal(0, 0.04, 20)
    p = pd.concat([calm, pd.Series(calm.iloc[-1] * np.exp(np.cumsum(rets)), index=wild.index)])
    iv = pd.DataFrame({"source": "fred", "series_id": "OVXCLS", "name": "OVX", "date": p.index[-40:].date,
                       "value": 40.0, "unit": "index", "freq": "daily", "source_url": "u", "fetched_at": pd.Timestamp("2026-10-24")})
    store.upsert_obs("fred_quant", iv)
    s = vol.state(p, D, store.connect(), "OVXCLS")
    assert s["pctile_3y"] >= 95 and s["rising_fast"] is True and s["regime"] in ("high", "extreme")
    assert s["iv"] == 40.0 and s["iv_minus_rv"] == pytest.approx(40.0 - s["rv_short"], abs=0.11)
    assert "USO" in s["iv_instrument"] and "gap_pctile" in s


def test_corr_band():
    a = _px(900, seed=6)
    b = a * np.exp(np.random.default_rng(7).normal(0, 0.002, len(a)))     # almost the same series
    s = corr.state({"X": a, "ES=F": b}, "X", D, {"corr": {"window": 60, "vs": ["ES=F"], "lookback_days": 756, "move_pctile": [10, 90]}})
    assert s["ES=F"]["corr"] > 0.9


def test_seasonal_excludes_current_bucket_and_splits():
    p = _px(26 * 252, seed=8, sd=0.008)
    t = seasonal.table(p, D)
    cur = (D.year, seasonal.period_of(D))
    assert all((y, k) < cur for y, k in zip(t["y"], t["k"]))
    s = seasonal.state(p, D)
    assert s["years"] >= 15 and set(s) >= {"mean_pct", "median_pct", "iqr_pct", "halves_agree", "mean_ci95"}
    assert "rank_of_24" not in s                                  # a norm, never a best bucket
    assert seasonal.label(0) == "1-15 Jan" and seasonal.label(23) == "16-end Dec"


def test_positioning_uses_friday_release(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    tue = pd.date_range(end="2026-10-20", periods=200, freq="W-TUE")
    vals = np.linspace(-10, 10, 200)
    df = pd.DataFrame({"source": "cftc", "series_id": "067651.mm_net_pct_oi", "name": "x", "date": tue.date, "value": vals,
                       "unit": "pct", "freq": "weekly", "source_url": "u", "fetched_at": pd.Timestamp("2026-10-24")})
    store.upsert_obs("cftc", df)
    con = store.connect()
    assert positioning.state(con, "067651", date(2026, 10, 22))["report_date"] == "2026-10-13"   # Tuesday 20th not out yet
    s = positioning.state(con, "067651", date(2026, 10, 23))
    assert s["report_date"] == "2026-10-20" and s["extreme"] is True


def test_curve_carry(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    d = date(2026, 10, 26)
    df = pd.DataFrame({"source": "prices_curve", "series_id": ["CLZ26.NYM", "CLF27.NYM", "CLG27.NYM"], "name": "x", "date": d,
                       "value": [100.0, 99.0, 98.0], "unit": "close", "freq": "daily", "source_url": "u", "fetched_at": pd.Timestamp("2026-10-27")})
    store.upsert_obs("prices_curve", df)
    sh = curve.shape("CL", d)
    assert sh["carry_ann_pct"] == pytest.approx(100 * (100 / 99 - 1) * 12, abs=0.05)


def _store_prices(tmp_path, monkeypatch, ids=("CL=F", "GC=F", "ES=F")):
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    rows = []
    for i, m in enumerate(ids):
        p = _px(1300, seed=10 + i)
        rows.append(pd.DataFrame({"source": "prices", "series_id": m, "name": m, "date": p.index.date, "value": p.values,
                                  "unit": "close", "freq": "daily", "source_url": f"https://finance.yahoo.com/quote/{m}",
                                  "fetched_at": pd.Timestamp("2026-10-24")}))
    store.upsert_obs("prices", pd.concat(rows))


def test_tape_build_render_and_card(tmp_path, monkeypatch):
    _store_prices(tmp_path, monkeypatch)
    monkeypatch.setattr(tape, "BRIEFS", tmp_path / "briefs")
    t = tape.build(D)
    assert t["markets"]["CL=F"]["trend"] and t["markets"]["NG=F"]["status"] == "no recent close"
    assert t["changes"]["vs"] is None and t["sources"]
    paths = tape.write(t, tmp_path / "briefs")
    assert (tmp_path / "briefs" / "2026-10-23" / "quant.md").read_text(encoding="utf-8").startswith("# Tape after the close")
    t2 = tape.build(D + timedelta(days=3))
    assert t2["changes"]["vs"] == "2026-10-23"
    close = next(s for s in t["sources"] if s["label"] == "WTI close")
    card = {"schema": "tape_card/v1", "as_of": "2026-10-23", "author": "quant/test", "headline": f"WTI closed at {close['value']} [{close['id']}].",
            "flipped": [], "stretched": [], "vol": [], "watch": ["No flip level is close."], "sources": [close]}
    assert cards.validate(card, today=date(2026, 10, 24), packs=[t]) == []
    card["headline"] = "WTI closed at 123.45."
    assert any("123.45" in p for p in cards.validate(card, today=date(2026, 10, 24), packs=[t]))


def test_filer_point_in_time_revisions_and_backlog(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    flog = tmp_path / "facts.jsonl"
    wk = pd.date_range(end="2026-10-16", periods=10, freq="W-FRI")
    vals = np.arange(10) + 400000.0

    def put(v):
        store.upsert_obs("eia", pd.DataFrame({"source": "eia", "series_id": "PET.WCESTUS1.W", "name": "x", "date": wk.date, "value": v,
                                              "unit": "kbbl", "freq": "weekly", "source_url": "u", "fetched_at": pd.Timestamp("2026-10-22")}))
    put(vals)
    t1 = datetime(2026, 10, 21, 23, 0, tzinfo=timezone.utc)
    filer.file_reports(date(2026, 10, 21), path=flog, now=t1)
    n = len(facts.load(flog))
    filer.file_reports(date(2026, 10, 21), path=flog, now=t1)
    assert len(facts.load(flog)) == n > 0                                                   # idempotent
    assert facts.value_as_of("2026-10-20", "PET.WCESTUS1.W", "value", path=flog) == 400008.0    # week to 10-09, out 10-15 (fresh)
    assert facts.value_as_of("2026-10-21", "PET.WCESTUS1.W", "value", path=flog) == 400009.0    # week to 10-16, out 10-21
    # a backlog week (released more than 7 days before the first filing) is known only from the filing time
    assert facts.value_as_of("2026-10-09", "PET.WCESTUS1.W", "value", path=flog) is None
    # a revision of the week to 10-09 seen on 10-23 is known from 10-23, never back-dated to its release
    vals[-2] = 401000.0
    put(vals)
    filer.file_reports(date(2026, 10, 23), path=flog, now=datetime(2026, 10, 23, 23, 0, tzinfo=timezone.utc))
    assert facts.value_as_of("2026-10-20", "PET.WCESTUS1.W", "value", path=flog) == 400008.0
    assert facts.value_as_of("2026-10-23", "PET.WCESTUS1.W", "value", known_at="2026-10-24", path=flog) == 400009.0
    k = facts.as_of("2026-10-12", "PET.WCESTUS1.W", known_at="2026-10-24", path=flog)
    assert list(k["value_num"]) == [401000.0]


def test_tape_card_validator_review_fixes(tmp_path, monkeypatch):
    _store_prices(tmp_path, monkeypatch)
    monkeypatch.setattr(tape, "BRIEFS", tmp_path / "briefs")
    t = tape.build(D)
    close = next(s for s in t["sources"] if s["label"] == "WTI close")
    gold = next(s for s in t["sources"] if s["label"] == "Gold close")
    base = {"schema": "tape_card/v1", "as_of": "2026-10-23", "author": "quant/test", "flipped": [], "stretched": [], "vol": [], "watch": []}
    ok = {**base, "headline": f"WTI closed at {close['value']} [{close['id']}].", "sources": [close, gold]}
    assert cards.validate(ok, today=date(2026, 10, 24), packs=[t]) == []
    wrong_cite = {**ok, "headline": f"WTI closed at {close['value']} [{gold['id']}]."}          # figure next to the wrong source
    assert any("cited in its sentence" in p for p in cards.validate(wrong_cite, today=date(2026, 10, 24), packs=[t]))
    relabel = {**ok, "sources": [{**close, "label": "Brent close"}, gold]}
    assert any("not a row of the input pack" in p for p in cards.validate(relabel, today=date(2026, 10, 24), packs=[t]))
    trade = {**ok, "headline": f"WTI is overbought at {close['value']} [{close['id']}]; sell into strength."}
    assert any("trade or forecast" in p for p in cards.validate(trade, today=date(2026, 10, 24), packs=[t]))
    p1 = cards.save(ok, root=tmp_path / "cards", today=date(2026, 10, 24), packs=[t])
    with pytest.raises(ValueError, match="already exists"):
        cards.save(ok, root=tmp_path / "cards", today=date(2026, 10, 24), packs=[t])
    assert p1.exists()


def test_tape_stale_close_suppresses_flips(tmp_path, monkeypatch):
    _store_prices(tmp_path, monkeypatch)
    monkeypatch.setattr(tape, "BRIEFS", tmp_path / "briefs")
    t = tape.build(D + timedelta(days=3))                  # Monday with Friday's closes only
    assert t["stale"] is True and t["flags"]["flipped"] == [] and t["flags"]["big_move"] == []
    ids1 = {s["from"]: s["id"] for s in tape.build(D)["sources"]}
    ids2 = {s["from"]: s["id"] for s in tape.build(D)["sources"]}
    assert ids1 == ids2                                     # stable ids
