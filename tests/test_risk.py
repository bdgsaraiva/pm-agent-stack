"""Risk and crowding (agent 8): risk model, stress P&L in R, worst case, clusters, CTA levels, crowding, the shared
marked drawdown, warnings and the fact-pack wiring (offline; synthetic prices, then the fake pipeline)."""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import pytest

from pmstack import audit, fetch, journal, monitor, risk, sizing
from test_pipeline import sandbox  # noqa: F401

ASOF = date(2026, 10, 1)
NOW = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)


def _obs(n=700, seed=3, drift=None, end="2026-10-01", shock_last=0):
    """Synthetic closes: an oil factor (BZ, CL, HO), an equity factor (ES, NQ) and independent ZN, DXY, GC, VIX."""
    rng = np.random.default_rng(seed)
    d = pd.bdate_range(end=end, periods=n)
    oil, eq = rng.normal(0, 0.02, n), rng.normal(0, 0.01, n)
    if shock_last:
        eq[-shock_last:] = -0.06                                     # a run of crash days: turbulence
    r = {"BZ=F": oil + rng.normal(0, 0.004, n), "CL=F": oil + rng.normal(0, 0.004, n), "HO=F": 0.8 * oil + rng.normal(0, 0.01, n),
         "ES=F": eq + rng.normal(0, 0.002, n), "NQ=F": 1.3 * eq + rng.normal(0, 0.004, n), "ZN=F": rng.normal(0, 0.003, n),
         "DX-Y.NYB": rng.normal(0, 0.003, n), "GC=F": rng.normal(0, 0.01, n), "^VIX": -3 * eq + rng.normal(0, 0.03, n)}
    for k, v in (drift or {}).items():
        r[k] = r[k] + v
    rows = []
    for k, v in r.items():
        px = 100 * np.exp(np.cumsum(v))
        rows += [{"series_id": k, "date": x.date(), "value": float(y), "source_url": f"https://example.com/{k}"} for x, y in zip(d, px)]
    hy = 3 + np.cumsum(rng.normal(0, 0.01, n))
    rows += [{"series_id": "BAMLH0A0HYM2", "date": x.date(), "value": float(y), "source_url": "https://fred.stlouisfed.org/series/BAMLH0A0HYM2"} for x, y in zip(d, hy)]
    return pd.DataFrame(rows)


def _px(obs, m, back=1):
    s = obs[obs.series_id == m].sort_values("date")
    return float(s.value.iloc[-back]), s.date.iloc[-back]


def _idea(i, m, direction, obs, stop_pct=0.05, size=1.0, book="paper", created="2026-08-01T00:00:00+00:00", entry=None):
    px = entry or _px(obs, m)[0]
    sgn = 1 if direction == "long" else -1
    return {"id": f"i{i}", "status": "open", "book": book, "market": m, "price_ref": m, "direction": direction,
            "entry_price": px, "invalidation_price": px * (1 - sgn * stop_pct), "target": px * (1 + sgn * 2 * stop_pct),
            "size_planned": size, "created_utc": created, "events": []}


def _row(e, last, r_now=0.0):
    return {"id": e["id"], "price_ref": e["price_ref"], "size": risk.size_of(e), "last": last, "r_now": r_now,
            "dir": 1 if e["direction"] == "long" else -1, "_e": e}


# ------------------------------------------------------------------ maths
def test_ledoit_wolf_shrinks_toward_constant_correlation():
    rng = np.random.default_rng(1)
    x = rng.normal(size=(60, 8))
    cov, delta = risk.lw_constant_corr(x)
    assert 0 < delta <= 1 and np.all(np.linalg.eigvalsh(cov) > 0)
    c = cov / np.sqrt(np.outer(np.diag(cov), np.diag(cov)))
    off = ~np.eye(8, dtype=bool)
    assert np.abs(c[off]).mean() < np.abs(np.corrcoef(x, rowvar=False)[off]).mean()
    f = rng.normal(size=(5000, 1))                                   # strongly unequal correlations, lots of data
    big = np.hstack([f + 0.1 * rng.normal(size=(5000, 1)), f + 0.1 * rng.normal(size=(5000, 1)), rng.normal(size=(5000, 2))])
    assert risk.lw_constant_corr(big)[1] < 0.05


def test_k_equivalent_matches_exact_chi_square():
    from scipy.stats import norm
    assert risk.k_equivalent(3.0, 1) == 3.0
    for d in (2.0, 4.0, 8.0):                                       # chi2(2) tail = exp(-d^2/2) exactly
        assert risk.k_equivalent(d, 2) == pytest.approx(norm.isf(math.exp(-d * d / 2) / 2), rel=1e-6)
    assert risk.k_equivalent(math.sqrt(21), 21) < 1.0               # a typical day in 21 markets is not rare


# ------------------------------------------------------------------ book risk
def test_same_market_twice_counts_once_and_a_short_is_a_hedge():
    obs = _obs()
    ents = [_idea(1, "BZ=F", "long", obs), _idea(2, "CL=F", "long", obs), _idea(3, "ES=F", "long", obs, stop_pct=0.025)]
    sec, _ = risk.build(obs, ents, {}, {}, ASOF)
    br = sec["book_risk"]
    assert br["ideas"] == 3 and 1.6 <= br["effective_ideas"] <= 2.4      # Brent and WTI are one bet
    assert any(set(g) == {"i1", "i2"} for g in br["clusters"])
    assert sum(r["contrib_pct"] for r in sec["ideas"]) == pytest.approx(100, abs=2)
    dup, _ = risk.build(obs, [_idea(1, "BZ=F", "long", obs), _idea(5, "BZ=F", "long", obs)], {}, {}, ASOF)
    assert dup["book_risk"]["same_idea_pairs"][0][:2] == ["i1", "i5"] and dup["book_risk"]["effective_ideas"] == 1.0
    one, _ = risk.build(obs, [_idea(1, "BZ=F", "long", obs, size=2.0)], {}, {}, ASOF)
    w2 = next(s for s in dup["stress"] if s["kind"] == "worst")
    w1 = next(s for s in one["stress"] if s["kind"] == "worst")
    assert w2["linear_r"] == pytest.approx(w1["linear_r"], rel=1e-6)      # same exposure, same worst case
    ents.append(_idea(4, "CL=F", "short", obs))
    sec2, _ = risk.build(obs, ents, {}, {}, ASOF)
    assert "i4" in sec2["book_risk"]["hedges"]
    assert sec2["book_risk"]["daily_sd_r_stress"] < sec["book_risk"]["daily_sd_r_stress"]
    hedge, _ = risk.build(obs, [_idea(1, "BZ=F", "long", obs), _idea(2, "CL=F", "short", obs)], {}, {}, ASOF)
    assert hedge["book_risk"]["effective_ideas"] <= 2 and hedge["book_risk"]["effective_capped"]


def test_ideas_after_the_asof_date_are_left_out_and_later_closes_count_as_open():
    obs = _obs()
    late = _idea(1, "BZ=F", "long", obs, created="2026-10-05T12:00:00+00:00")
    closed_later = {**_idea(2, "CL=F", "long", obs), "status": "closed", "closed_utc": "2026-10-05T12:00:00+00:00", "r_multiple": 1.0}
    ideas, book = risk.book_ideas([late, closed_later], ASOF)
    assert [e["id"] for e in ideas] == ["i2"] and book == "paper"


# ------------------------------------------------------------------ stress
def test_stress_pnl_in_r_honours_stops_and_shows_gaps():
    obs = _obs()
    e = _idea(1, "BZ=F", "long", obs, stop_pct=0.05)
    rows = [_row(e, e["entry_price"])]
    res = risk.apply(rows, {"BZ=F": math.log(0.80)})                   # -20% through a 5% stop
    assert res["gapped_r"] == pytest.approx(-4.0, abs=0.01) and res["honoured_r"] == -1.0
    up = risk.apply(rows, {"BZ=F": math.log(1.10)})
    assert up["gapped_r"] == up["honoured_r"] == pytest.approx(2.0, abs=0.01)
    assert risk.apply(rows, {})["missing"] == ["i1"]
    # a replay whose path went through the stop and came back: stopped out on the way
    path = risk.apply(rows, {"BZ=F": math.log(1.02)}, {"BZ=F": (math.log(0.90), math.log(1.02))})
    assert path["honoured_r"] == -1.0 and path["gapped_r"] > 0
    # a short in profit: floor is the distance to its stop from here
    s = _idea(2, "BZ=F", "short", obs, stop_pct=0.05)
    sp = risk.apply([_row(s, s["entry_price"] * 0.95, r_now=1.0)], {"BZ=F": math.log(1.30)})
    assert sp["honoured_r"] == pytest.approx(-2.0, abs=0.01) and sp["gapped_r"] < -2
    # already past its stop: exited at today's mark
    past = risk.apply([_row(s, s["entry_price"] * 1.08, r_now=-1.6)], {"BZ=F": math.log(1.30)})
    assert past["honoured_r"] == 0.0 and past["gapped_r"] < -6


def test_named_scenario_conditional_mean_worst_case_and_replays():
    obs = _obs()
    ents = [_idea(1, "CL=F", "long", obs), _idea(2, "NQ=F", "long", obs)]
    sec, _ = risk.build(obs, ents, {}, {}, ASOF)
    st = {s["id"]: s for s in sec["stress"]}
    wti = next(i for i in st["oil_supply_spike_v1"]["ideas"] if i["id"] == "i1")
    assert wti["move_pct"] > 15 and st["oil_supply_spike_v1"]["gapped_r"] > 0   # Brent is the driver; WTI follows
    assert st["ai_unwind_v1"]["gapped_r"] < -1
    wc = st["worst_k3_5d"]
    assert wc["kind"] == "worst" and wc["k"] == 3.0 and risk.k_equivalent(wc["radius"], 2) == pytest.approx(3.0, abs=0.01)
    assert wc["gapped_r"] == pytest.approx(wc["linear_r"], rel=0.25)
    assert all(s["honoured_r"] >= s["gapped_r"] - 1e-9 for s in sec["stress"]          # instantaneous: stops cap the loss
               if s.get("gapped_r") is not None and s["kind"] != "replay")      # replays: a stop-out can miss a recovery
    rp = st["ai_slide_2026"]                                          # a replay inside the synthetic history
    assert rp["kind"] == "replay" and rp["days"] > 0 and rp["gapped_r"] is not None
    old = [dict(e, created_utc="2025-01-02T12:00:00+00:00") for e in ents]
    early, _ = risk.build(obs, old, {}, {}, date(2026, 3, 3))
    assert {s["id"]: s for s in early["stress"]}["war_2026"]["note"] == "not yet happened on the as-of date"
    json.dumps(sec, allow_nan=False, default=str)


# ------------------------------------------------------------------ CTA levels and crowding
def test_cta_levels_rolloff_state_and_vol_scale():
    c = risk.cfg()
    d = pd.bdate_range(end="2026-10-01", periods=400)
    v = np.linspace(50, 100, 400)
    v[-22], v[-21] = 99.0, 101.0                                      # today's 1m reference is below, tomorrow's above
    x = risk.cta_levels(pd.Series(v, index=d), c)
    assert x["legs"]["21"]["sign"] == 1 and x["legs"]["21"]["flip_level"] == 99.0
    assert x["legs"]["21"]["rolloff_flip_days"] == 1
    assert x["legs"]["252"]["rolloff_flip_days"] is None and x["state"] == "aligned" and x["vol_scale"] is not None
    w = np.concatenate([np.linspace(50, 100, 380), np.linspace(100, 92, 20)])
    assert risk.cta_levels(pd.Series(w, index=d), c)["state"] == "correction"


def test_crowding_is_red_only_when_funding_stresses_and_uses_released_reports():
    obs = _obs()
    d = pd.date_range(end="2026-09-29", periods=160, freq="W-TUE")
    mm = np.concatenate([np.linspace(-5, 10, 159), [30.0]])          # the last report jumps to a record long
    cf = pd.DataFrame({"series_id": "067651.mm_net_pct_oi", "date": d.date, "value": mm, "source_url": "u"})
    obs2 = pd.concat([obs, cf], ignore_index=True)
    ents = [_idea(1, "CL=F", "long", obs)]
    sec, _ = risk.build(obs2, ents, {}, {"CL=F": "067651"}, ASOF)    # Tue 29 Sep released Fri 2 Oct: not yet
    assert sec["ideas"][0]["crowding"]["date"] == "2026-09-22"
    sec, _ = risk.build(obs2, ents, {}, {"CL=F": "067651"}, date(2026, 10, 2))
    cr = sec["ideas"][0]["crowding"]
    assert cr["date"] == "2026-09-29" and cr["crowded"] and cr["crowded_entry"] and cr["pct_on_side"] >= 99
    assert sec["ideas"][0]["crowded_red"] == sec["funding"]["stressing"]
    hy = obs2.series_id == "BAMLH0A0HYM2"
    obs3 = obs2.copy()
    obs3.loc[hy & (obs3.date == obs3[hy].date.max()), "value"] += 2.0   # +200bp: funding stressing
    sec3, al = risk.build(obs3, ents, {}, {"CL=F": "067651"}, date(2026, 10, 2))
    assert sec3["funding"]["stressing"] and sec3["ideas"][0]["crowded_red"]
    assert not any("crowd" in a["kind"] for a in al)                 # crowding is shown, never alerted


# ------------------------------------------------------------------ marked book and warnings
def test_marked_drawdown_orders_closes_and_open_marks_on_one_curve():
    d = pd.bdate_range("2026-08-01", "2026-10-01")
    px = pd.DataFrame({"X": np.full(len(d), 100.0)}, index=d)
    px.loc[px.index >= "2026-08-10", "X"] = 90.0                       # open long at -2R for weeks
    op = {"id": "o", "status": "open", "book": "paper", "direction": "long", "price_ref": "X", "entry_price": 100.0,
          "invalidation_price": 95.0, "size_planned": 1.0, "created_utc": "2026-08-03T12:00:00+00:00"}
    cl = {"id": "c", "status": "closed", "book": "paper", "direction": "long", "price_ref": None, "r_multiple": 2.0,
          "size_planned": 1.0, "created_utc": "2026-08-03T12:00:00+00:00", "closed_utc": "2026-09-30T12:00:00+00:00"}
    # -2R open for weeks, then a +2R close yesterday: the marked book is back at its high
    assert risk.marked_drawdown([op, cl], ASOF, 60, prices=px) == 0.0
    # a missing last price carries the last close: no false jump
    px2 = px.copy()
    px2.loc[px2.index[-1], "X"] = np.nan
    cv = risk.book_curve([op], ASOF, "paper", date(2026, 9, 1), px2)
    assert cv.iloc[-1] == cv.iloc[-2] == -2.0


def test_sizing_cut_counts_open_marks(monkeypatch):
    monkeypatch.setattr(risk, "store_prices", lambda ids, asof: pd.DataFrame(
        {"X": [100.0, 75.0]}, index=pd.to_datetime(["2026-09-25", "2026-09-30"])))
    op = {"id": "o", "status": "open", "book": "paper", "direction": "long", "price_ref": "X", "entry_price": 100.0,
          "invalidation_price": 95.0, "size_planned": 1.0, "created_utc": "2026-09-20T12:00:00+00:00"}
    assert sizing.drawdown_r([op], NOW) == -5.0                         # -5R open, never closed
    new = {"id": "n", "status": "open", "book": "paper", "direction": "long", "conviction": 3, "entry_price": 50.0,
           "target": 60.0, "invalidation_price": 45.0, "price_ref": None}
    s = sizing.suggest(new, [op], NOW)
    assert s["drawdown_r"] == -5.0 and "open marks" in s["notes"][-1]
    ex = {**op, "book": "example"}
    assert sizing.drawdown_r([ex], NOW) == 0.0                          # example ideas never move paper sizes


def _losing_book(obs, n_back=11, book="paper", stop=0.95):
    ents = []
    for i, m in enumerate(["BZ=F", "CL=F", "HO=F"]):
        px, dt = _px(obs, m, n_back)
        ents.append({"id": f"o{i}", "status": "open", "book": book, "market": m, "price_ref": m, "direction": "long",
                     "entry_price": px, "invalidation_price": px * stop, "size_planned": 1.0,
                     "created_utc": f"{dt}T12:00:00+00:00", "events": []})
    return ents


def test_red_and_clustered_losses_fire_from_the_marked_book():
    fall = np.r_[np.zeros(690), -0.012 * np.ones(10)]                  # oil -11% over 10 days through 5% stops
    obs = _obs(drift={"BZ=F": fall, "CL=F": fall, "HO=F": fall})
    sec, al = risk.build(obs, _losing_book(obs), {}, {}, ASOF)
    kinds = {a["kind"] for a in al}
    assert sec["book_curve"]["drawdown_60d_r"] <= -4 and "risk_drawdown_red" in kinds and "risk_drawdown_amber" not in kinds
    assert "risk_cluster_loss" in kinds
    assert all(a["source_url"].startswith("http") for a in al)
    # the example book never claims a sizing cut; its warnings are tagged
    sec3, al3 = risk.build(obs, _losing_book(obs, book="example"), {}, {}, ASOF)
    assert sec3["book"] == "example" and not any(a["kind"] == "risk_drawdown_red" for a in al3)
    assert al3 and all(a["text"].endswith("[example book]") for a in al3)


def test_amber_fires_between_minus_three_and_minus_four():
    obs = _obs()
    d = pd.bdate_range(end="2026-10-01", periods=40)
    px = pd.DataFrame({"X": np.r_[np.full(30, 100.0), np.full(10, 96.5)]}, index=d)   # -3.5R on one 1R-per-1% idea
    op = {"id": "o", "status": "open", "book": "paper", "direction": "long", "price_ref": "X", "entry_price": 100.0,
          "invalidation_price": 99.0, "size_planned": 1.0, "created_utc": "2026-08-10T12:00:00+00:00"}
    rows = [{"series_id": "X", "date": x.date(), "value": float(v), "source_url": "https://example.com/X"} for x, v in zip(d, px.X)]
    sec, al = risk.build(pd.concat([obs, pd.DataFrame(rows)], ignore_index=True), [op], {}, {}, ASOF)
    assert sec["book_curve"]["from_high_r"] == -3.5 and {a["kind"] for a in al} >= {"risk_drawdown_amber"}
    assert not any(a["kind"] == "risk_drawdown_red" for a in al)


def test_persistent_turbulence_alerts_only_with_ideas():
    obs = _obs(shock_last=4)
    sec, al = risk.build(obs, [_idea(1, "GC=F", "long", obs)], {}, {}, ASOF)
    assert sec["turbulence"]["persistent"] and any(a["kind"] == "risk_turbulence" for a in al)
    _, none = risk.build(obs, [], {}, {}, ASOF)
    assert not any(a["kind"] == "risk_turbulence" for a in none)


def test_size_follows_events():
    e = {"size_planned": 1.0, "events": [{"action": "add", "size": 1.5}, {"action": "note", "size": None}]}
    assert risk.size_of(e) == 1.5 and risk.size_of({}) == 1.0


def test_render_never_crashes_on_an_empty_section():
    assert "Not available" in "\n".join(risk.render({}))


# ------------------------------------------------------------------ wiring
def test_fact_pack_carries_risk_section_and_note_figures_pass_audit(sandbox):
    fetch.run(backfill=True)
    journal.new(market="Brent", direction="long", conviction=3, thesis="Physical premium.", price_ref="BZ=F",
                target=200, invalidation_price=10, size_planned=1.0, now=datetime(2026, 9, 30, tzinfo=timezone.utc))
    journal.new(market="Gold", direction="short", conviction=2, thesis="Real yields.", price_ref="GC=F",
                target=1, invalidation_price=10000, size_planned=0.5, now=datetime(2026, 9, 30, tzinfo=timezone.utc))
    facts = monitor.build(asof=ASOF, now=NOW)
    R = facts["sections"]["risk"]
    assert "error" not in R, R.get("error")
    assert R["book"] == "paper" and R["book_risk"]["ideas"] == 2 and len(R["stress"]) == 32 + 9 + 2
    assert R["cta"] and all("legs" in x for x in R["cta"].values())
    raw = (sandbox / "briefs" / str(ASOF) / "facts.json").read_text()

    def strict(c):
        raise ValueError(c)
    json.loads(raw, parse_constant=strict)                              # strict JSON on disk
    md = (sandbox / "briefs" / str(ASOF) / "facts.md").read_text()
    assert "## Risk and crowding" in md and "Stress P&L" in md and "not a forecast" in md and "nan" not in md.lower().replace("financ", "")
    p = sandbox / "briefs" / str(ASOF) / "note.md"
    br = R["book_risk"]
    p.write_text(f"# N\n\n- Risk: {br['effective_ideas']} effective independent ideas; daily sd {br['daily_sd_r_stress']}R under stress.\n")
    assert audit.audit_file(p)["summary"]["orphan"] == 0


def test_cli_report_logs_its_time(sandbox):
    fetch.run(backfill=True)
    journal.new(market="WTI", direction="long", conviction=3, thesis="x", price_ref="CL=F", target=500,
                invalidation_price=1, size_planned=1.0, now=datetime(2026, 9, 30, tzinfo=timezone.utc))
    from pmstack import __main__ as cli
    assert cli.main(["risk", "--date", str(ASOF), "--out", str(sandbox / "risk.md")]) == 0
    assert "## Risk and crowding" in (sandbox / "risk.md").read_text()
    from pmstack import runlog
    rec = [r for r in runlog.read(50) if r["step"] == "risk:report"]
    assert rec and rec[-1]["seconds"] >= 0


# ------------------------------------------------------------------ long history (agent 8 v2)
def _long_obs():
    """2006-2026 with a 2008 window where bonds rally as stocks fall and a 2022 window where they fall together."""
    rng = np.random.default_rng(11)
    d = pd.bdate_range("2006-01-02", "2026-10-01")
    n = len(d)
    eq, oil = rng.normal(0, 0.01, n), rng.normal(0, 0.02, n)
    zn = rng.normal(0, 0.003, n)
    w08 = (d >= "2008-09-01") & (d <= "2009-03-31")
    w22 = (d >= "2022-01-01") & (d <= "2022-10-31")
    zn[w08] = -0.4 * eq[w08] + rng.normal(0, 0.001, w08.sum())
    zn[w22] = 0.4 * eq[w22] + rng.normal(0, 0.001, w22.sum())
    eq[(d >= "2020-02-24") & (d <= "2020-03-16")] = -0.05            # a planted crash
    r = {"BZ=F": oil, "CL=F": oil + rng.normal(0, 0.004, n), "ES=F": eq, "NQ=F": 1.3 * eq + rng.normal(0, 0.004, n),
         "ZN=F": zn, "DX-Y.NYB": rng.normal(0, 0.003, n), "GC=F": rng.normal(0, 0.01, n), "^VIX": -3 * eq + rng.normal(0, 0.03, n),
         "HO=F": 0.8 * oil + rng.normal(0, 0.01, n), "ZC=F": rng.normal(0, 0.015, n), "ZS=F": rng.normal(0, 0.012, n),
         "ZW=F": rng.normal(0, 0.016, n)}
    rows = []
    for k, v in r.items():
        px = 100 * np.exp(np.cumsum(v))
        rows += [{"series_id": k, "date": x.date(), "value": float(y), "source_url": f"https://example.com/{k}"} for x, y in zip(d, px)]
    return pd.DataFrame(rows)


def test_history_splices_proxies_yields_and_drops_bad_prices():
    c = risk.cfg()
    d = pd.bdate_range("2019-01-01", "2021-12-31")
    rows = []
    def add(sid, vals, dates):
        rows.extend({"series_id": sid, "date": x.date(), "value": float(v), "source_url": "u"} for x, v in zip(dates, vals))
    add("ES=F", np.linspace(100, 130, len(d)), d)
    late = d[d >= "2020-06-01"]
    add("CL=F", np.linspace(30, 60, len(late)), late)                  # futures only from Jun 2020
    wti = np.linspace(50, 40, len(d))
    wti[d.get_loc(pd.Timestamp("2020-04-20"))] = -37.63               # the negative settle
    add("DCOILWTICO", wti, d)
    add("BZ=F", np.linspace(60, 70, len(d)), d)
    add("DGS10", np.linspace(2.0, 1.0, len(d)), d)
    obs = pd.DataFrame(rows)
    R, SRC = risk.history(obs, ["CL=F", "ZN=F"], date(2021, 12, 31), c)
    assert SRC.loc["2020-07-01", "CL=F"] == "own" and SRC.loc["2019-06-03", "CL=F"] == "DCOILWTICO"
    assert SRC.loc["2020-04-20", "CL=F"] == "BZ=F"                      # excluded window falls to the next proxy
    assert np.isfinite(R["CL=F"].dropna()).all()
    dy = (1.0 - 2.0) / (len(d) - 1)                                     # yields fall: the note future gains
    assert R.loc["2019-06-03", "ZN=F"] == pytest.approx(-6.5 * dy / 100, rel=1e-6) and SRC.loc["2019-06-03", "ZN=F"] == "DGS10"


def test_episode_replays_the_path_and_a_gap_costs_more_than_one_r():
    obs = _obs()
    e = _idea(1, "BZ=F", "long", obs, stop_pct=0.05)
    r = {"id": "i1", "price_ref": "BZ=F", "size": 1.0, "last": e["entry_price"], "r_now": 0.0, "dir": 1, "_e": e}
    g, h = risk._path_r(r, np.log(np.array([0.99, 0.90, 1.10])))       # gaps to -10%, then recovers to +10%
    assert g == pytest.approx(2.0, abs=0.01) and h == pytest.approx(-2.0, abs=0.01)
    g2, h2 = risk._path_r(r, np.log(np.array([0.98, 1.02])))
    assert g2 == h2


def test_long_history_episodes_worst_windows_and_correlation_regimes():
    obs = _long_obs()
    ents = [_idea(1, "ES=F", "long", obs, created="2006-01-01T00:00:00+00:00"),
            _idea(2, "ZN=F", "long", obs, stop_pct=0.02, created="2006-01-01T00:00:00+00:00")]
    sec, _ = risk.build(obs, ents, {}, {}, ASOF)
    st = {s["id"]: s for s in sec["stress"]}
    assert st["covid_2020"]["gapped_r"] < -10 and st["covid_2020"]["honoured_r"] >= st["covid_2020"]["gapped_r"]
    assert st["covid_2020"]["worst_inside_r"] <= min(0.0, st["covid_2020"]["gapped_r"]) + 0.01
    assert st["black_monday_1987"]["note"] == "no data for this window"
    assert st["lehman_2008"]["proxy_share_pct"] == 0
    ww = sec["worst_windows"]
    assert ww["since"] <= "2006-01-10"
    w5 = next(w for w in ww["windows"] if w["horizon_days"] == 5)
    assert "2020-02-24" <= w5["end"] <= "2020-03-20" and w5["gapped_r"] < 0       # finds the planted crash
    assert ww["reverse"]["moves_pct"]["ES=F"] < 0
    assert set(sec["model"]["crisis_windows"]) == {"gfc_2008", "infl_2022"}
    ai = st["ai_unwind_v1"]                                           # long notes: 2008 hedge, 2022 loss
    assert {"stress", "gfc_2008", "infl_2022"} <= set(ai["under"])
    zn_only, _ = risk.build(obs, [ents[1]], {}, {}, ASOF)
    z = {s["id"]: s for s in zn_only["stress"]}["ai_unwind_v1"]
    assert z["under"]["gfc_2008"] > 0 > z["under"]["infl_2022"] and z["sign_flip"]
    assert z["isolated_r"] == 0.0                                       # drivers only: the note doesn't move
    assert any(a["id"] == "dotcom_2000" for a in ai["analogues"])
    wc = [s for s in sec["stress"] if s["kind"] == "worst"]
    assert [w["horizon_days"] for w in wc] == [5, 20] and wc[1]["gapped_r"] < wc[0]["gapped_r"]
    md = "\n".join(risk.render(sec))
    assert "Worst historical windows" in md and "Episode library" in md and "sign flip" in md
    json.dumps(sec, allow_nan=False, default=str)


def test_inferred_market_when_an_episode_predates_its_series():
    obs = _long_obs()
    late = obs[(obs.series_id != "GC=F") | (obs.date >= date(2012, 1, 1))]   # gold history from 2012 only
    ents = [_idea(1, "GC=F", "long", late, created="2006-01-01T00:00:00+00:00"),
            _idea(2, "ES=F", "long", late, created="2006-01-01T00:00:00+00:00")]
    sec, _ = risk.build(late, ents, {}, {}, ASOF)
    l08 = {s["id"]: s for s in sec["stress"]}["lehman_2008"]
    assert l08["inferred"] == ["i1"] and 0 < l08["proxy_share_pct"] < 100
    assert next(x for x in l08["ideas"] if x["id"] == "i1")["basis"] == "inferred"


def test_deep_history_is_fetched_once(sandbox, monkeypatch):
    from pmstack import fetch as F
    from pmstack.adapters import base
    import test_pipeline as tp
    seen, gold_empty = [], []
    def spy(url, params=None, **kw):
        if params and "period1" in params:
            seen.append((url.split("/chart/")[1], params["period1"]))
        if gold_empty and "/chart/GC=F" in url:
            return {"chart": {"result": None}}                        # the source returns nothing, without an error
        return tp.fake_get_json(url, params=params)
    monkeypatch.setattr(base, "get_json", spy)
    y1986 = int(datetime(1986, 1, 2, tzinfo=timezone.utc).timestamp())
    F.run(only=["prices"], backfill=True)                               # a backfill goes back to history_start ...
    assert min(p for _, p in seen) <= y1986
    cfg = F.load_sources()["prices"]
    assert F.deep_history("prices", cfg) == {}                          # ... and marks every series it got
    F._history_file("prices").unlink()                                  # a store filled before v2: no marks
    assert set(F.deep_history("prices", cfg)) == {t["id"] for t in cfg["tickers"]}
    seen.clear()
    gold_empty.append(1)
    F.run(only=["prices"])
    assert {t for t, p in seen if p <= y1986} == {t["id"] for t in cfg["tickers"]}
    assert set(F.deep_history("prices", cfg)) == {"GC=F"}               # nothing came back for gold: asked again
    seen.clear()
    F.run(only=["prices"])
    assert [t for t, p in seen if p <= y1986] == ["GC=F"]


def test_handover_gaps_and_roll_screen():
    c = risk.cfg()
    d = pd.bdate_range("2019-01-01", "2020-12-31")
    rows = []
    def add(sid, vals, dates):
        rows.extend({"series_id": sid, "date": x.date(), "value": float(v), "source_url": "u"} for x, v in zip(dates, vals))
    add("ES=F", np.linspace(100, 130, len(d)), d)
    spot = 3.0 * np.exp(np.cumsum(np.random.default_rng(2).normal(0, 0.01, len(d))))
    add("DHHNGSP", spot, d)
    late = d[d >= "2020-01-02"]
    fut = 2.0 * spot[-len(late):] / spot[-len(late)]                   # futures 33% below spot: a level gap
    k = late.get_loc(pd.Timestamp("2020-06-15"))
    fut[k:] *= 1.12                                                    # an unadjusted roll jump of +12%
    add("NG=F", fut, late)
    gold = d[(d < "2020-03-02") | (d > "2020-03-11")]                  # an 8-day hole in gold
    gv = np.where(gold < "2020-03-02", 100.0, 110.0)
    add("GC=F", gv, gold)
    obs = pd.DataFrame(rows)
    R, SRC = risk.history(obs, ["NG=F", "GC=F"], date(2020, 12, 31), c)
    i = d.get_loc(pd.Timestamp("2020-01-02"))
    assert R.loc["2020-01-02", "NG=F"] == pytest.approx(math.log(spot[i] / spot[i - 1]), rel=1e-9)   # handover = proxy
    assert SRC.loc["2020-01-03", "NG=F"] == "own"
    assert SRC.loc["2020-06-15", "NG=F"] == "screened:DHHNGSP" and abs(R.loc["2020-06-15", "NG=F"]) < 0.05
    assert R.loc["2020-03-12", "GC=F"] == pytest.approx(math.log(1.1)) and R["GC=F"].loc["2020-03-02":"2020-03-11"].isna().all()


def test_worst_window_infers_a_missing_market_and_finds_the_crash():
    obs = _long_obs()
    gap = (obs.series_id == "GC=F") & (obs.date >= date(2020, 2, 10)) & (obs.date <= date(2020, 3, 31))
    o2 = obs[~gap]
    ents = [_idea(1, "ES=F", "long", o2, created="2006-01-01T00:00:00+00:00"),
            _idea(2, "GC=F", "long", o2, created="2006-01-01T00:00:00+00:00")]
    sec, _ = risk.build(o2, ents, {}, {}, ASOF)
    w5 = next(w for w in sec["worst_windows"]["windows"] if w["horizon_days"] == 5)
    assert "2020-02-24" <= w5["end"] <= "2020-03-31" and w5["inferred_days_pct"] > 0
    rv = sec["worst_windows"]["reverse"]
    assert rv["book_r"] < 0 and rv["moves_pct"]["ES=F"] < 0
    cov = {s["id"]: s for s in sec["stress"]}["covid_2020"]
    assert cov["inferred"] == ["i2"] and cov["proxy_share_pct"] > 0
    assert cov["worst_inside_r"] <= min(0.0, cov["gapped_r"]) + 0.01
    assert cov["vol_scaled_r"] is not None and cov["vol_scaled_r"] != cov["gapped_r"]
    late = obs[(obs.series_id != "GC=F") | (obs.date >= date(2012, 1, 1))]
    g_only = [_idea(1, "GC=F", "long", late, created="2006-01-01T00:00:00+00:00")]
    gs, _ = risk.build(late, g_only, {}, {}, ASOF)
    leh = {s["id"]: s for s in gs["stress"]}["lehman_2008"]
    assert leh["inferred"] == ["i1"] and leh["worst_inside_r"] <= min(0.0, leh["gapped_r"]) + 0.01
    assert "gfc_2008" not in gs["model"]["crisis_windows"]             # universe incomplete before 2012: no 2008 matrix
    vix_late = obs[(obs.series_id != "^VIX") | (obs.date >= date(2012, 1, 1))]
    vs, _ = risk.build(vix_late, [_idea(1, "ES=F", "long", vix_late, created="2006-01-01T00:00:00+00:00")], {}, {}, ASOF)
    ro = {s["id"]: s for s in vs["stress"]}["risk_off_funding_v1"]      # VIX (a driver) had no 2008 data: "-"
    assert "^VIX" in vs["model"]["crisis_windows"]["gfc_2008"]["missing"]
    assert ro["under"]["gfc_2008"] is None and ro["under"]["infl_2022"] is not None
    early, _ = risk.build(obs, [_idea(1, "ES=F", "long", obs, created="2006-01-01T00:00:00+00:00")], {}, {}, date(2022, 6, 30))
    assert set(early["model"]["crisis_windows"]) == {"gfc_2008"}       # the 2022 window had not ended yet


def test_a_sparse_proxy_still_carries_the_whole_move():
    obs = _long_obs()
    v = obs[obs.series_id == "^VIX"].sort_values("date").reset_index(drop=True)
    sparse = pd.concat([obs[obs.series_id != "^VIX"], v.iloc[::3]], ignore_index=True)   # prints one day in three
    e = _idea(1, "^VIX", "long", sparse, stop_pct=0.2, created="2006-01-01T00:00:00+00:00")
    sec, _ = risk.build(sparse, [e], {}, {}, ASOF)
    cov = {s["id"]: s for s in sec["stress"]}["covid_2020"]
    assert cov["inferred"] == [] and cov["gapped_r"] > 0                # replayed, not inferred: VIX rose in the crash
    s3 = v.iloc[::3].set_index(pd.to_datetime(v.iloc[::3].date))["value"]
    a, b = s3[:"2020-01-31"].iloc[-1], s3[:"2020-03-31"].iloc[-1]
    assert next(x for x in cov["ideas"] if x["id"] == "i1")["move_pct"] == pytest.approx(100 * (b / a - 1), abs=0.1)
    assert sec["worst_windows"]["inferred_days_pct"] == 0
