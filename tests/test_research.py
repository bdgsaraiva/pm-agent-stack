"""Research loop (agent 12): statistics checked against published worked examples, outcomes and episodes without
look-ahead, the event study on planted and random flags, the agents' flags recomputed point in time (same numbers as the
agents' own functions), the registry freeze, verdict rules, time-series momentum, and the wiring (offline, synthetic)."""
from __future__ import annotations

import json
import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

from pmstack import consensus, qstats, research as R, risk


@pytest.fixture
def rroot(tmp_path, monkeypatch):
    root = tmp_path / "research"
    monkeypatch.setattr(R, "RDIR", root)
    return root


def _cfg(**gate):
    c = R.cfg()
    c["gate"] = {**c["gate"], "placebo_reps": 300, **gate}
    return c


def _prices(n=3000, seed=1, markets=("ES=F", "CL=F", "GC=F"), end="2026-10-01"):
    rng = np.random.default_rng(seed)
    d = pd.bdate_range(end=end, periods=n)
    rows = []
    for m in markets:
        px = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
        rows += [{"source": "prices", "series_id": m, "date": x.date(), "value": float(y),
                  "source_url": f"https://example.com/{m}"} for x, y in zip(d, px)]
    return pd.DataFrame(rows)


def _cftc(code="067651", n=500, seed=2, end="2026-09-29"):
    rng = np.random.default_rng(seed)
    d = pd.date_range(end=end, periods=n, freq="W-TUE")
    v = np.cumsum(rng.normal(0, 2, n))
    return pd.DataFrame([{"source": "cftc", "series_id": f"{code}.mm_net_pct_oi", "date": x.date(), "value": float(y),
                          "source_url": R.CFTC_URL} for x, y in zip(d, v)])


# ------------------------------------------------------------------ statistics
def test_qstats_selftest_passes():
    assert qstats._selftest() == 0


def test_deflated_sharpe_matches_bailey_lopez_de_prado_examples():
    # the paper's worked example: annual SR 2.5, 1250 days, 100 trials, V[SR] 0.5 (annual), skew -3, kurtosis 10
    sr, v = 2.5 / math.sqrt(250), 0.5 / 250
    assert R.dsr(sr, 1250, -3, 10, 100, v)["dsr"] == pytest.approx(0.9004, abs=1e-4)
    assert R.dsr(sr, 1250, -3, 10, 46, v)["dsr"] == pytest.approx(0.9505, abs=1e-4)
    # PSR at the benchmark itself is a coin flip; more trials raise the bar
    assert R.psr(0.1, 0.1, 100, 0, 3) == pytest.approx(0.5)
    assert R.expected_max_sr(1000, v) > R.expected_max_sr(10, v) > 0


def test_holm_bh_and_bayes_p():
    p = {"a": 0.01, "b": 0.04, "c": 0.03, "d": 0.5}
    h, q = R.holm(p), R.bh(p)
    assert h["a"] == pytest.approx(0.04) and h["c"] == pytest.approx(0.09) and h["b"] == pytest.approx(0.09)
    assert q["a"] == pytest.approx(0.04) and q["b"] == pytest.approx(0.0533, abs=1e-3) and q["d"] == pytest.approx(0.5)
    assert all(q[k] <= h[k] + 1e-12 for k in p)
    # Harvey 2017: two-sided p = 0.05 (z 1.96, MBF 0.147) at odds 4:1 -> 0.37; our placebo p is one-sided, so 0.025
    assert R.bayes_p(0.025, 4) == pytest.approx(0.37, abs=0.005) and R.bayes_p(0.6, 1) == pytest.approx(0.5)


def test_minimum_detectable_lift_matches_power_arithmetic():
    # base 10%, lift 2 needs ~69 independent episodes at 80% power, one-sided 5% (multiple-testing notes, s.3.4)
    assert R.min_detectable_lift(69, 0.10) == pytest.approx(2.0, abs=0.08)
    assert R.min_detectable_lift(20, 0.10) > R.min_detectable_lift(200, 0.10)


# ------------------------------------------------------------------ outcomes and episodes
def test_outcome_uses_only_the_window_after_entry_and_sd_known_at_the_signal():
    idx = pd.bdate_range("2020-01-01", periods=300)
    r = pd.Series(np.random.default_rng(0).normal(0, 0.01, 300), index=idx)
    z = R.outcome_z(r, h=5, lam=0.94, lag_days=1)
    t = 200
    entry = t + 1                                              # first trading day on or after t + 1 calendar day
    sd = math.sqrt(float((r.iloc[:t + 1] ** 2).ewm(alpha=0.06, adjust=False).mean().iloc[-1]))
    assert z.iloc[t] == pytest.approx(r.iloc[entry + 1:entry + 6].sum() / (sd * math.sqrt(5)))
    r2 = r.copy()
    r2.iloc[entry + 6:] += 0.5                                 # after the window: no effect
    r2.iloc[entry] += 0.5                                      # the entry day's own return is before entry: no effect
    assert R.outcome_z(r2, 5, 0.94, 1).iloc[t] == pytest.approx(z.iloc[t])
    r3 = r.copy()
    r3.iloc[entry + 1] += 0.05                                 # inside the window: changes it
    assert R.outcome_z(r3, 5, 0.94, 1).iloc[t] != pytest.approx(z.iloc[t])
    assert z.iloc[-3:].isna().all()                            # incomplete windows are not scored


def test_cftc_lag_moves_entry_past_the_friday_release():
    idx = pd.bdate_range("2023-10-02", "2024-02-29")
    r = pd.Series(1e-4, index=idx)
    r[pd.Timestamp("2024-01-05")] = 0.10                       # the release Friday: before entry, not counted
    r[pd.Timestamp("2024-01-08")] = 0.10                       # Monday = entry day (Tue 2 Jan + 4 days = Sat -> Mon)
    r[pd.Timestamp("2024-01-09")] = 0.05                       # first day of the window
    z = R.outcome_z(r, 3, 0.94, 4)
    tue = idx.get_loc(pd.Timestamp("2024-01-02"))
    assert z.iloc[tue] == pytest.approx((0.05 + 2e-4) / (1e-4 * math.sqrt(3)), rel=1e-6)


def test_episodes_collapse_runs_and_respect_the_gap():
    cal = pd.bdate_range("2020-01-01", periods=200)
    d = cal[[10, 15, 20, 60, 61, 120]]
    ev = pd.DataFrame({"date": d, "market": "ES=F", "source": "s", "on": True, "side": 1})
    ep = R.episodes(ev, cal, gap=20)
    assert list(ep.pos) == [10, 60, 120]
    ev2 = pd.concat([ev, ev.assign(side=-1)])                  # each side is its own key
    assert len(R.episodes(ev2, cal, gap=20)) == 6


# ------------------------------------------------------------------ event study
def _planted(n=2500, seed=3, strength=3.0, every=60):
    rng = np.random.default_rng(seed)
    cal = pd.bdate_range("2012-01-02", periods=n)
    r = rng.normal(0, 0.01, n)
    on = np.zeros(n, dtype=bool)
    for i in range(300, n - 40, every):
        on[i] = True
        if strength:
            r[i + 2:i + 12] += strength * 0.01 / math.sqrt(10)   # a planted move after the entry day
    lr = pd.DataFrame({"ES=F": r}, index=cal)
    ev = pd.DataFrame({"date": cal[250:n - 30], "market": "ES=F", "source": "x", "on": on[250:n - 30], "side": 1})
    return ev, lr


def test_planted_signal_is_found_and_random_flag_is_not():
    c = _cfg()
    ev, lr = _planted()
    res = R.event_study(ev, lr, "follow", 10, 1, c, expected=1)
    assert res["n_episodes"] >= 30 and res["lift"] > 2 and res["p_placebo"] < 0.02
    assert res["halves"]["stat"][0] > 1 and res["halves"]["stat"][1] > 1
    sig = R.event_study(ev, lr, "signed", 10, 1, c, expected=1)
    assert sig["excess_sd"] > 0.5 and sig["p_placebo"] < 0.02
    ev0, lr0 = _planted(strength=0)
    nul = R.event_study(ev0, lr0, "follow", 10, 1, c, expected=1)
    assert 0.3 < nul["lift"] < 2.2 and nul["p_placebo"] > 0.05
    assert nul["lift_shrunk"] == pytest.approx(
        (nul["hits"] + 20 * nul["base_rate"]) / (nul["expected_hits"] + 20 * nul["base_rate"]), abs=0.01)


def test_base_rate_is_market_and_side_matched():
    c = _cfg()
    ev, lr = _planted(strength=0)
    lr["CL=F"] = lr["ES=F"] * 3                                  # same shape, other market
    ev2 = pd.concat([ev, ev.assign(market="CL=F", source="y", side=-1)])
    res = R.event_study(ev2, lr, "adverse", 10, 1, c, expected=1)
    assert res["n_sources"] == 2 and res["expected_hits"] > 0
    assert set(res["markets"]) == {"ES=F", "CL=F"}


# ------------------------------------------------------------------ verdicts
def _flagres(**kw):
    base = {"kind": "flag", "id": "x", "binary": True, "n_episodes": 50, "stat": 1.6, "centre": 1.0, "expected": 1,
            "p_placebo": 0.01, "p_opposite": 0.99, "halves": {"stat": [1.5, 1.7]},
            "drop_year": {"min": 1.4, "max": 1.8, "min_year": 2020, "max_year": 2021}}
    return {**base, **kw}


def test_verdict_rules():
    c = _cfg()
    assert R.verdict(_flagres(), c, q_bh=0.05)[0] == "supported"
    assert R.verdict(_flagres(n_episodes=10), c)[0] == "insufficient"
    assert R.verdict(_flagres(stat=0.5, p_placebo=0.99, p_opposite=0.01), c)[0] == "no edge"      # halves disagree
    assert R.verdict(_flagres(stat=0.5, p_placebo=0.99, p_opposite=0.01, halves={"stat": [0.5, 0.6]},
                              drop_year={"min": 0.4, "max": 0.7, "min_year": 1, "max_year": 2}), c)[0] == "reversed"
    v, why = R.verdict(_flagres(), c, q_bh=0.2)
    assert v == "no edge" and any("BH q" in w for w in why)
    assert R.verdict(_flagres(stat=1.1), c, q_bh=0.05)[0] == "no edge"                 # too small to matter
    assert R.verdict(_flagres(halves={"stat": [1.9, 0.9]}), c, q_bh=0.05)[0] == "no edge"
    assert R.verdict(_flagres(drop_year={"min": 0.95, "max": 1.8, "min_year": 2020, "max_year": 2021}), c,
                     q_bh=0.05)[0] == "no edge"
    # two-sided: the observed sign is the one that must hold
    assert R.verdict(_flagres(expected=0, stat=0.6, p_opposite=None, halves={"stat": [0.6, 0.7]},
                              drop_year={"min": 0.5, "max": 0.7, "min_year": 1, "max_year": 2}), c, q_bh=0.01)[0] == "supported"


def test_family_counts_insufficient_studies_with_p_one():
    c = _cfg()
    rs = [_flagres(id="a", p_placebo=0.01), _flagres(id="b", n_episodes=5, p_placebo=0.001),
          _flagres(id="c", p_placebo=0.03)]
    f = R.family(rs, c)
    assert f["b"]["verdict"] == "insufficient" and f["a"]["family_size"] == 3
    assert f["a"]["q_bh"] == pytest.approx(0.03) and f["c"]["q_bh"] == pytest.approx(0.045)
    assert f["a"]["q_by"] > f["a"]["q_bh"]


# ------------------------------------------------------------------ registry
def _spec(**kw):
    s = {"id": "t1", "title": "t", "kind": "flag", "hypothesis": "h", "source": "s", "registered": "2026-10-19",
         "flag": "cftc_crowded", "params": {"pct": 90}, "outcome": "adverse", "expected": 1, "agent": 8}
    return {**s, **kw}


def test_registration_is_validated_frozen_and_never_overwritten(rroot):
    assert R.validate(_spec(lift=1.5))                       # a registration carries no results
    assert R.validate(_spec(flag="made_up"))
    R.register(_spec())
    with pytest.raises(ValueError):
        R.register(_spec())                                   # never overwritten
    spec = R.load_studies(rroot)["t1"]
    assert R.frozen_hash("t1", rroot) == R.spec_hash(spec)
    obs = pd.concat([_prices(markets=("CL=F", "ES=F")), _cftc()])
    edited = {**spec, "expected": -1}                         # a sign flip after registration
    with pytest.raises(ValueError, match="new id"):
        R.run_study(edited, obs, date(2026, 10, 1), root=rroot, c=_cfg())
    res = R.run_study(spec, obs, date(2026, 10, 1), root=rroot, c=_cfg())
    assert res["spec_hash"] == R.frozen_hash("t1", rroot)
    assert [r["id"] for r in R.runs(rroot)] == ["t1"] and len(R.ledger(rroot)) == 2


def test_run_ignores_everything_after_the_as_of_date(rroot):
    R.register(_spec())
    spec = R.load_studies(rroot)["t1"]
    obs = pd.concat([_prices(markets=("CL=F", "ES=F")), _cftc()])
    asof = date(2025, 6, 30)
    a = R.run_study(spec, obs, asof, root=rroot, c=_cfg(), write=False)
    b = R.run_study(spec, obs[obs.date <= asof], asof, root=rroot, c=_cfg(), write=False)
    for k in ("n_episodes", "stat", "p_placebo", "base_rate", "hits"):
        assert a.get(k) == b.get(k)
    assert a["last_episode"] <= str(asof)


# ------------------------------------------------------------------ flags = the agents' own numbers, point in time
def test_cftc_table_matches_consensus_positioning_and_risk_crowding():
    obs = pd.concat([_cftc(), _prices(markets=("CL=F", "ES=F"))])
    t = R.cftc_table(obs, "067651").set_index("date")
    for rep in t.index[[60, 200, -1]]:
        asof = (rep + pd.Timedelta(days=3)).date()            # the Friday release
        pos = consensus.positioning(obs, "067651", asof, lag=3)
        assert t.loc[rep, "pct"] == pytest.approx(pos["pct_3y"], abs=0.51)
        cr = risk.crowding(obs, {"direction": "long", "price_ref": None}, "067651", pd.DataFrame(), asof, risk.cfg())
        assert t.loc[rep, "z"] == pytest.approx(cr["change_z"], abs=0.051)


def test_narrative_stage_on_a_grid_date_uses_only_data_up_to_it():
    d = pd.date_range("2023-01-01", "2026-09-30", freq="D")
    rng = np.random.default_rng(5)
    share = np.abs(1 + 0.3 * np.sin(np.arange(len(d)) / 40) + rng.normal(0, 0.05, len(d)))
    rows = []
    for x, s in zip(d, share):
        rows += [{"source": "gdelt", "series_id": "gdelt:hormuz_iran_v1:share", "date": x.date(), "value": float(s), "source_url": "u"},
                 {"source": "gdelt", "series_id": "gdelt:hormuz_iran_v1:count", "date": x.date(), "value": 100.0, "source_url": "u"},
                 {"source": "gdelt", "series_id": "gdelt:norm", "date": x.date(), "value": 1e5, "source_url": "u"}]
    obs = pd.DataFrame(rows)
    full = R.narrative_stages(obs, date(2026, 9, 30), "W-FRI")
    mid = pd.Timestamp("2025-06-06")
    cut = R.narrative_stages(obs[obs.date <= mid.date()], mid.date(), "W-FRI")
    a = full[(full.date == mid) & (full.narrative == "hormuz_iran_v1")].stage.iloc[0]
    b = cut[(cut.date == mid) & (cut.narrative == "hormuz_iran_v1")].stage.iloc[0]
    assert a == b
    c = consensus.cfg()
    s_ = R._series(obs, "gdelt:hormuz_iran_v1:share")
    assert a == consensus.stage_of(s_[s_.index <= mid], R._series(obs, "gdelt:hormuz_iran_v1:count"),
                                   R._series(obs, "gdelt:norm"), mid.date(), c)["stage"]


def test_trend_dir_matches_the_vote_of_the_three_legs():
    idx = pd.bdate_range("2020-01-01", periods=400)
    r = pd.Series(np.random.default_rng(9).normal(0.0005, 0.01, 400), index=idx)
    td = R.trend_dir(r)
    i = 350
    legs = [np.sign(r.iloc[i - L + 1:i + 1].sum()) for L in (21, 63, 252)]
    assert td[i] == int(np.sign(sum(legs)))
    assert td[100] == 0                                        # 12-month leg not there yet


# ------------------------------------------------------------------ strategy
def test_tsmom_earns_on_a_persistent_trend_and_costs_bite():
    rng = np.random.default_rng(11)
    idx = pd.bdate_range("2003-01-01", periods=3000)
    regime = np.repeat(rng.choice([-1, 1], 3000 // 250 + 1), 250)[:3000]
    lr = pd.DataFrame({"CL=F": rng.normal(0.0012 * regime, 0.01), "ES=F": rng.normal(0.0003, 0.01, 3000)}, index=idx)
    c = R.cfg()
    g, n = R.tsmom(lr, 252, c, cost_x=0.0), R.tsmom(lr, 252, c, cost_x=4.0)
    assert g["ret"].mean() > n["ret"].mean() and R._moments(g["ret"])["sharpe"] > 0.3
    assert (R.tsmom(lr, 252, c, cost_x=0.0, mode="long")["ret"].index == g.index).all()
    assert R.cost_bps("ZN=F", pd.Timestamp("1990-06-01"), c) == 6.0 and R.cost_bps("CL=F", pd.Timestamp("2010-01-01"), c) == 10.0


# ------------------------------------------------------------------ index and wiring
def test_index_graveyard_verdicts_and_tags(rroot):
    R.register(_spec())
    spec = R.load_studies(rroot)["t1"]
    obs = pd.concat([_prices(markets=("CL=F", "ES=F")), _cftc()])
    R.run_study(spec, obs, date(2026, 10, 1), root=rroot, c=_cfg())
    out = R.build_index(rroot, _cfg())
    txt = (rroot / "index.md").read_text(encoding="utf-8")
    assert "## Graveyard" in txt and "`t1`" in txt
    v = json.loads((rroot / "verdicts.json").read_text(encoding="utf-8"))["verdicts"]["t1"]
    assert v["flag"] == "cftc_crowded" and v["verdict"] == out["verdicts"]["t1"]["verdict"]
    t = R.tag_for("cftc_crowded", root=rroot)
    assert t["study"] == "t1" and t["verdict"] in t["text"]
    assert R.agent_tags(8, rroot)[0]["study"] == "t1"
    # the risk section maps its flag text to the research flag
    m = risk._measured(["crowded", "stop near flip level (21d)"])
    assert [x["flag"] for x in m] == ["crowded"] and m[0]["study"] == "t1"
    page = (rroot / "results" / "t1.md").read_text(encoding="utf-8")
    assert "Verdict:" in page and "not a signal or a trade instruction" in page


def test_risk_and_critic_wiring_is_silent_without_verdicts(rroot):
    assert risk._research_tags() == [] and risk._measured(["crowded"]) == []
    from pmstack import critic
    F = {}
    critic._research_fact(lambda k, v, l, s: F.setdefault(k, v), "research.crowded", "cftc_crowded", None, "x")
    assert F == {}


# ------------------------------------------------------------------ independent review (20 Oct 2026): regressions
def test_placebo_keeps_copies_together_so_a_copied_null_flag_is_not_rejected():
    # review finding 1: one null flag copied into 4 sources was rejected 23% of the time at 5% with per-source shifts
    c = _cfg(placebo_reps=200)
    rej = 0
    for seed in range(20):
        ev, lr = _planted(strength=0, seed=100 + seed, every=45)
        ev4 = pd.concat([ev.assign(source=f"s{i}") for i in range(4)])
        rej += R.event_study(ev4, lr, "signed", 10, 1, c, expected=1, seed=seed)["p_placebo"] <= 0.05
    assert rej <= 3                                        # ~5% of 20, with room for noise


def test_reversed_must_pass_the_gate_in_the_other_direction():
    c = _cfg()
    weak = _flagres(stat=0.6, p_placebo=0.99, p_opposite=0.03, halves={"stat": [0.5, 0.98]},
                    drop_year={"min": 0.5, "max": 0.97, "min_year": 1, "max_year": 2})
    v, why = R.verdict(weak, c, q_bh=1.0, q_opp=0.5)
    assert v == "no edge" and "leans the opposite way" in why[0] and "BH q" in why[0]
    strong = _flagres(stat=0.5, p_placebo=0.99, p_opposite=0.01, halves={"stat": [0.5, 0.6]},
                      drop_year={"min": 0.4, "max": 0.7, "min_year": 1, "max_year": 2})
    assert R.verdict(strong, c, q_bh=1.0, q_opp=0.05)[0] == "reversed"


def test_hindsight_flags_are_capped_until_live_episodes_agree():
    c = _cfg()
    r = _flagres(hindsight="2026-10-10", live={"from": "2026-10-10", "n": 0, "stat": None})
    v, why = R.verdict(r, c, q_bh=0.01)
    assert v == "in-sample only" and "2026-10-10" in why[0]
    r["live"] = {"from": "2026-10-10", "n": 25, "stat": 1.4}
    assert R.verdict(r, c, q_bh=0.01)[0] == "supported"


def test_imported_ideas_need_t_three_and_env_changes_block_support():
    c = _cfg()
    assert R.verdict(_flagres(paper=True, z_binomial=2.5), c, q_bh=0.01)[0] == "no edge"
    assert R.verdict(_flagres(paper=True, z_binomial=3.2), c, q_bh=0.01)[0] == "supported"
    assert R.verdict(_flagres(env_changed=True, definition_frozen="a", definition_hash="b"), c, q_bh=0.01)[0] == "no edge"


def test_family_counts_registered_studies_without_results():
    c = _cfg()
    f = R.family([_flagres(id="a", p_placebo=0.01)], c, registered=["a", "b", "c", "d"])
    assert f["a"]["family_size"] == 4 and f["a"]["q_bh"] == pytest.approx(0.04)
    assert R.family([_flagres(id="a", expected=1, z_binomial=-3.5)], c)["a"]["hlz_pass"] is False   # signed t


def test_unregistered_spec_is_refused_and_a_no_write_run_is_a_peek(rroot):
    obs = pd.concat([_prices(markets=("CL=F", "ES=F")), _cftc()])
    with pytest.raises(ValueError, match="not registered"):
        R.run_study(_spec(), obs, date(2026, 10, 1), root=rroot, c=_cfg())
    R.register(_spec())
    spec = R.load_studies(rroot)["t1"]
    R.run_study(spec, obs, date(2026, 10, 1), root=rroot, c=_cfg(), write=False)
    ev = [r.get("event") for r in R.ledger(rroot)]
    assert ev == ["register", "peek"] and R.runs(rroot) == []
    R.run_study(spec, obs, date(2026, 10, 1), root=rroot, c=_cfg())
    assert R.frozen_definition("t1", rroot) == R.definition_hash(spec, _cfg())


def test_index_rewrites_each_result_with_the_final_family_verdict(rroot):
    obs = pd.concat([_prices(markets=("CL=F", "ES=F")), _cftc()])
    R.register(_spec())
    R.register(_spec(id="t2", outcome="follow"))
    R.run_study(R.load_studies(rroot)["t1"], obs, date(2026, 10, 1), root=rroot, c=_cfg())
    R.build_index(rroot, _cfg())
    r1 = json.loads((rroot / "results" / "t1.json").read_text(encoding="utf-8"))
    assert r1["family"]["family_size"] == 2                # t2 registered but not run counts with p = 1
    assert (rroot / "results" / "t1.md").read_text(encoding="utf-8").count("2 flag studies") == 1


def test_cftc_release_moves_to_monday_in_a_holiday_week():
    assert R.cftc_release(pd.Timestamp("2024-01-02")) == pd.Timestamp("2024-01-08")   # New Year's Day week
    assert R.cftc_release(pd.Timestamp("2024-07-02")) == pd.Timestamp("2024-07-08")   # Independence Day week
    assert R.cftc_release(pd.Timestamp("2024-10-29")) == pd.Timestamp("2024-11-01")   # an ordinary Friday


def test_verdict_lookup_takes_the_latest_version_and_respects_the_as_of_date(rroot):
    rroot.mkdir(parents=True)
    v = {"flag": "cftc_crowded", "params": {}, "agent": 8, "verdict": "no edge", "n_episodes": 30, "lift": 1.0,
         "lift_shrunk": 1.0, "hit_rate": 0.1, "base_rate": 0.1, "outcome": "adverse", "horizon_days": 20}
    (rroot / "verdicts.json").write_text(json.dumps({"verdicts": {
        "x_v1": {**v, "registered": "2026-10-19", "asof": "2026-10-19"},
        "x_v10": {**v, "registered": "2026-10-19", "asof": "2026-11-02", "verdict": "supported"},
        "bad": "not a dict"}}), encoding="utf-8")
    assert R.verdict_for("cftc_crowded", root=rroot)["id"] == "x_v10"
    assert R.verdict_for("cftc_crowded", root=rroot, asof="2026-10-20")["id"] == "x_v1"
    assert R.verdict_for("cftc_crowded", root=rroot, asof="2026-10-01") is None
    assert risk._measured(["crowded"]) and risk._research_tags("2026-10-01") == []


def test_tsmom_book_is_decided_with_information_at_the_rebalance():
    idx = pd.bdate_range("2010-01-01", periods=700)
    rng = np.random.default_rng(4)
    lr = pd.DataFrame({"CL=F": rng.normal(0.001, 0.01, 700), "GC=F": rng.normal(0.0, 0.01, 700)}, index=idx)
    lr.loc[lr.index > pd.Timestamp("2011-06-30"), "GC=F"] = np.nan            # GC stops trading after June 2011
    c = R.cfg()
    t = R.tsmom(lr, 252, c, cost_x=1.0)
    june = t.index.get_indexer([pd.Timestamp("2011-06-30")])
    # the month after the last GC close: GC was still trading at the rebalance, so it is in that month's book
    jul = t[(t.index > pd.Timestamp("2011-06-30")) & (t.index <= pd.Timestamp("2011-07-31"))]
    assert len(jul) == 1 and int(jul["n"].iloc[0]) == 2
    aug = t[(t.index > pd.Timestamp("2011-07-31")) & (t.index <= pd.Timestamp("2011-08-31"))]
    assert int(aug["n"].iloc[0]) == 1
