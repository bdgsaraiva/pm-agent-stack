"""Consensus and narrative monitor (agent 7): GDELT stages, trend proxy, labels, ideas, stable alert refs (offline)."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd

from pmstack import audit, consensus, critic, fetch, journal, monitor
from pmstack.adapters import gdelt
from test_pipeline import sandbox  # noqa: F401

ASOF = date(2026, 10, 1)


def _run(tmp):
    fetch.run(backfill=True)
    return monitor.build(asof=ASOF, now=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc))


def test_narrative_stages_from_fake_gdelt(sandbox):
    facts = _run(sandbox)
    nar = {n["id"]: n for n in facts["sections"]["consensus"]["narratives"]}
    assert nar["hormuz_iran_v1"]["stage"] == "spreading" and nar["hormuz_iran_v1"]["ratio_vs_26w"] > 3
    assert nar["oil_glut_v1"]["stage"] == "fading"
    assert nar["copper_shortage_v1"]["stage"] in ("steady", "dormant", "peaking")
    assert all(n["validated"] is False for n in nar.values())
    h = nar["hormuz_iran_v1"]
    assert h["data_through"] <= str(ASOF) and h["stage_prev_basis"] == "one data day earlier"
    fired = any(a["kind"] == "narrative_spreading" and a["id"] == "hormuz_iran_v1" for a in facts["alerts"])
    assert fired == (h["stage_prev"] != "spreading")      # no masking "or": the alert follows the comparison
    json.dumps(facts, allow_nan=False, default=str)        # strict JSON: no NaN anywhere in the pack


def test_gap_days_are_dropped():
    c = consensus.cfg()
    d = pd.date_range("2025-01-01", "2026-10-01", freq="D")
    norm = pd.Series(200000.0, index=d)
    share = pd.Series(0.04, index=d)
    count = share / 100 * norm
    share.iloc[-3:] = 1.0                      # a spike on days when GDELT's total collapsed
    norm.iloc[-3:] = 20000.0
    st = consensus.stage_of(share, count, norm, date(2026, 10, 1), c)
    assert st["stage"] != "spreading"


def test_trend_proxy_signs_and_flip_levels():
    c = consensus.cfg()
    d = pd.bdate_range("2024-01-01", "2026-10-01")
    px = pd.Series(np.linspace(50, 100, len(d)), index=d)
    obs = pd.DataFrame({"series_id": "X", "date": d.date, "value": px.values, "source_url": "u"})
    t = consensus.trend(obs, "X", date(2026, 10, 1), c)
    assert t["score"] == 1.0 and t["legs_used"] == 3 and t["strength"] > 0
    assert t["legs"]["252"]["flip_level"] < t["last"]


def test_labels_are_rule_based():
    c = consensus.cfg()
    up = {"score": 1.0}
    crowded = {"pct_3y": 95}
    assert consensus._label(up, crowded, [{"sign": 1, "stage": "fading"}], c) == "twilight"
    assert consensus._label(up, {"pct_3y": 75}, [{"sign": 1, "stage": "spreading"}], c) == "self-reinforcing"
    assert consensus._label(up, crowded, [], c) == "crowded"
    assert consensus._label({"score": 0.0}, {"pct_3y": 50}, [{"sign": 1, "stage": "dormant"}], c) == "quiet"


def test_ideas_are_placed_and_rendered(sandbox):
    fetch.run(backfill=True)
    journal.new(market="Brent", direction="long", conviction=3, thesis="Hormuz risk.", price_ref="BZ=F",
                target=200, invalidation_price=10, size_planned=1.0, now=datetime(2026, 9, 30, tzinfo=timezone.utc))
    facts = monitor.build(asof=ASOF, now=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc))
    ideas = facts["sections"]["consensus"]["ideas"]
    assert ideas and ideas[0]["price_ref"] == "BZ=F" and "Hormuz / Iran oil supply" in ideas[0]["narratives_with"]
    md = (sandbox / "briefs" / str(ASOF) / "facts.md").read_text()
    assert "## Consensus map" in md and "Hormuz / Iran oil supply" in md and "not a forecast" in md
    # a note quoting the map passes the auditor
    n = next(x for x in facts["sections"]["consensus"]["narratives"] if x["id"] == "hormuz_iran_v1")
    p = sandbox / "briefs" / str(ASOF) / "note.md"
    p.write_text(f"# N\n\n- Hormuz / Iran oil supply narrative is {n['ratio_vs_26w']}x its prior 26 weeks.\n")
    assert audit.audit_file(p)["summary"]["orphan"] == 0


def test_alert_refs_stay_stable_when_pack_is_rebuilt_after_the_note(sandbox):
    facts = _run(sandbox)
    out = sandbox / "briefs" / str(ASOF)
    (out / "note.md").write_text("# note\n")
    before = {a["ref"]: (a["kind"], a["id"]) for a in facts["alerts"]}
    old = json.loads((out / "alerts.json").read_text())
    old.insert(0, {"kind": "price_move", "id": "ZZZ", "text": "gone", "severity": 9, "rank": 99, "ref": f"alerts:{ASOF}#99",
                   "source_url": "u"})
    (out / "alerts.json").write_text(json.dumps(old))
    again = monitor.build(asof=ASOF, now=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc))
    after = {a["ref"]: (a["kind"], a["id"]) for a in again["alerts"]}
    assert all(after[r] == k for r, k in before.items())
    assert any(a["ref"] == f"alerts:{ASOF}#99" and a.get("no_longer_firing") for a in again["alerts"])


# ------------------------------------------------------------------ agent 7 review regressions
def _nar_obs(end: date, jump_from: date | None = None, gap_last: int = 0) -> pd.DataFrame:
    """Hormuz-only GDELT series: flat share, ramping up from `jump_from`; the last `gap_last` days missing."""
    d = pd.date_range("2025-01-01", str(end), freq="D")
    rs = np.random.default_rng(7)
    share = 0.04 * (1 + 0.05 * rs.standard_normal(len(d)))
    if jump_from:
        k = np.clip((d - pd.Timestamp(jump_from)).days, 0, None)
        share = share * np.exp(0.06 * k)
    if gap_last:
        d, share = d[:-gap_last], share[:-gap_last]
    norm = np.full(len(d), 200000.0)
    rows = []
    for sid, vals in (("gdelt:hormuz_iran_v1:share", share), ("gdelt:hormuz_iran_v1:count", share / 100 * norm),
                      ("gdelt:norm", norm)):
        rows += [{"series_id": sid, "date": x.date(), "value": float(v), "source_url": "u"} for x, v in zip(d, vals)]
    return pd.DataFrame(rows)


def _first_spreading_day(obs: pd.DataFrame, c: dict) -> date:
    share = consensus._daily(obs, "gdelt:hormuz_iran_v1:share", date(2030, 1, 1))
    count = consensus._daily(obs, "gdelt:hormuz_iran_v1:count", date(2030, 1, 1))
    norm = consensus._daily(obs, "gdelt:norm", date(2030, 1, 1))
    for t in pd.date_range("2026-09-01", "2026-09-30"):
        if consensus.stage_of(share, count, norm, t.date(), c)["stage"] == "spreading":
            return t.date()
    raise AssertionError("no spreading day in the synthetic series")


def _spread_alerts(obs, asof, briefs=None):
    _, al = consensus.build(obs, pd.DataFrame(), [], {}, {}, asof, briefs=briefs)
    return [a for a in al if a["id"] == "hormuz_iran_v1"]


def test_spreading_alert_fires_on_the_pack_after_the_turn(tmp_path):
    """Finding 1: data run a day behind the pack, so the turn must be seen on the next pack, not swallowed."""
    c = consensus.cfg()
    full = _nar_obs(date(2026, 9, 30), jump_from=date(2026, 9, 5))
    t = _first_spreading_day(full, c)
    obs_t = full[full.date <= t]
    assert _spread_alerts(obs_t, t + timedelta(days=1))                  # pack the morning after the turn
    assert not _spread_alerts(full[full.date <= t - timedelta(days=1)], t)   # pack before it: not yet
    # against the previous pack: alert only if that pack did not already show spreading
    for prev_stage, expect in (("spreading", False), ("steady", True)):
        b = tmp_path / prev_stage
        (b / str(t)).mkdir(parents=True)
        (b / str(t) / "facts.json").write_text(json.dumps({"sections": {"consensus": {"narratives": [
            {"id": "hormuz_iran_v1", "stage": prev_stage}]}}}))
        al = _spread_alerts(full[full.date <= t + timedelta(days=2)], t + timedelta(days=3), briefs=b)
        assert bool(al) is expect
        if al:
            assert f"was {prev_stage}" in al[0]["text"]


def test_stale_and_tied_narratives():
    """Finding 7: no stage from stale data; ties take the middle rank, so a flat series is not 'peaking'."""
    c = consensus.cfg()
    stale = consensus.narratives(_nar_obs(date(2026, 9, 30), gap_last=8), date(2026, 9, 30), c)
    assert next(n for n in stale if n["id"] == "hormuz_iran_v1")["stage"] == "stale"
    d = pd.date_range("2025-01-01", "2026-09-30", freq="D")
    flat = pd.Series(0.04, index=d)
    st = consensus.stage_of(flat, flat / 100 * 200000, pd.Series(200000.0, index=d), date(2026, 9, 30), c)
    assert st["stage"] == "steady" and st["level_pctile"] == 50
    json.dumps(st, allow_nan=False)


def test_two_of_three_legs_is_a_trend():
    """Finding 2: score 0.33 (2 of 3 legs up) is a direction, not flat."""
    c = consensus.cfg()
    d = pd.bdate_range("2024-01-01", "2026-10-01")
    px = pd.Series(np.linspace(50, 100, len(d)), index=d)
    px.iloc[-15:] = np.linspace(100, 98, 15)                  # 1-month leg down, 3- and 12-month legs up
    obs = pd.DataFrame({"series_id": "X", "date": d.date, "value": px.values, "source_url": "u"})
    t = consensus.trend(obs, "X", date(2026, 10, 1), c)
    assert t["score"] == 0.33 and t["vote"] == 1
    assert consensus._label(t, {"pct_3y": 95}, [], c) == "crowded"
    assert consensus._label(t, {"pct_3y": 50}, [], c) != "quiet"
    mk = [{"market": "X", "trend": t, "cftc": None, "narratives": [], "label": "mixed"}]
    idea = consensus.ideas([{"id": "i1", "status": "open", "direction": "long", "price_ref": "X"}], mk, c)[0]
    assert idea["vs_trend"] == "with"


def test_stable_ranks_with_duplicate_keys_and_old_files(tmp_path):
    """Finding 3: two Fed releases share (kind, id); an old alerts.json may lack ranks; gone alerts are not live."""
    out = tmp_path / "2026-10-01"
    out.mkdir()
    (out / "note.md").write_text("# note\n")
    A = {"kind": "policy_text", "id": "fed", "text": "Fed statement A", "severity": 3, "source_url": "u"}
    B = {"kind": "policy_text", "id": "fed", "text": "Fed speech B", "severity": 2, "source_url": "u"}
    P = {"kind": "price_move", "id": "BZ=F", "text": "Brent +5%", "severity": 4, "source_url": "u"}
    (out / "alerts.json").write_text(json.dumps([P, A, B]))          # old file without "rank"
    got = monitor._stable_ranks([dict(P), dict(B)], out, date(2026, 10, 1))
    by = {a["rank"]: a for a in got}
    assert by[1]["text"] == "Brent +5%" and not by[1].get("no_longer_firing")
    assert by[2]["text"] == "Fed statement A" and by[2]["no_longer_firing"]
    assert by[3]["text"] == "Fed speech B" and not by[3].get("no_longer_firing")
    live = monitor.live_alerts(got)
    assert [a["text"] for a in live] == ["Brent +5%", "Fed speech B"]
    facts = {"alerts": [{**a, "ref": f"alerts:2026-10-01#{a['rank']}"} for a in got]}
    e = {"market": "Fed", "price_ref": "ZN=F", "direction": "long"}
    assert all("statement A" not in a["text"] for a in critic.market_alerts(e, facts))


def test_auditor_keeps_narrative_figures_apart(sandbox):
    """Finding 5: a figure of one narrative must not be matched under another narrative's name."""
    facts = _run(sandbox)
    nar = {n["id"]: n for n in facts["sections"]["consensus"]["narratives"]}
    h, g = nar["hormuz_iran_v1"], nar["oil_glut_v1"]
    p = sandbox / "briefs" / str(ASOF) / "note.md"
    p.write_text(f"# N\n\n- Oil glut story at {h['ratio_vs_26w']}x its prior 26 weeks.\n\n"
                 f"- Oil glut / surplus narrative at {g['ratio_vs_26w']}x its prior 26 weeks.\n")
    figs = [f for f in audit.audit_file(p)["figures"] if f["text"].endswith("x")]
    assert figs[0]["status"] != "matched" and figs[1]["status"] == "matched"


def test_gdelt_budget_failures_and_daily_sums(monkeypatch):
    """Findings 4 and 6: stop after repeated failures; sum sub-daily points; restart each query from its own day."""
    cfg = {"queries": [{"id": f"q{i}", "name": f"Q{i}", "query": f'"q {i}" OR "OPEC+"'} for i in range(5)],
           "backfill_start": "2017-01-01", "max_consecutive_failures": 2, "overlap_days": 10}
    calls = []

    def failing(cfg, query, mode, start, end, deadline=None):
        calls.append(query)
        raise RuntimeError("rate limited")
    monkeypatch.setattr(gdelt, "_call", failing)
    out = gdelt.fetch(cfg, since=date(2026, 9, 1))
    assert len(calls) == 2 and any("in a row" in e for e in out.attrs["errors"])

    starts = {}

    def hourly(cfg, query, mode, start, end, deadline=None):
        starts[query] = start
        day = (end - timedelta(days=1)).strftime("%Y%m%d")
        if mode == "timelinetone":
            return [{"date": f"{day}T{h:02d}0000Z", "value": v} for h, v in ((0, -1.0), (12, -3.0))]
        return [{"date": f"{day}T{h:02d}0000Z", "value": 10, "norm": 1000} for h in (0, 12)]
    monkeypatch.setattr(gdelt, "_call", hourly)
    cfg["_known"] = {"gdelt:q0:count"}
    cfg["_last"] = {"gdelt:q0:count": date(2026, 8, 1)}
    out = gdelt.fetch(cfg, since=date(2026, 9, 20))
    q0 = out[out.series_id == "gdelt:q0:count"]
    assert len(q0) == 1 and q0.value.iloc[0] == 20                     # two hourly points -> one day, summed
    assert out[out.series_id == "gdelt:q0:share"].value.iloc[0] == 1.0  # 20 / 2000
    assert out[out.series_id == "gdelt:q0:tone"].value.iloc[0] == -2.0
    assert starts['"q 0" OR "OPEC+"'] == date(2026, 7, 22)              # its own last day minus overlap
    assert starts['"q 1" OR "OPEC+"'] == date(2017, 1, 1)               # unknown query: full history
    assert "%2B" in out.source_url.iloc[0] and "%22" in out.source_url.iloc[0]
