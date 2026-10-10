"""Sizing assistant (agent 4): Kelly-relative units, cap, steps, calibration, drawdown cut, flags, review."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from pmstack import journal, sizing
from test_journal import T0, _paper, jbox  # noqa: F401  (fixture)


def _idea(**kw):
    e = {"id": "x", "status": "open", "book": "paper", "direction": "long", "conviction": 3,
         "entry_price": 100.0, "target": 110.0, "invalidation_price": 95.0, "price_ref": None}
    e.update(kw)
    return e


def _closed(i, conviction=3, r=1.0, days_ago=10, size=1.0):
    return {"id": f"c{i}", "status": "closed", "book": "paper", "conviction": conviction, "r_multiple": r,
            "size_planned": size, "closed_utc": (T0 - timedelta(days=days_ago)).isoformat(),
            "created_utc": (T0 - timedelta(days=days_ago + 5)).isoformat()}


def test_reference_idea_is_one_unit():
    s = sizing.suggest(_idea(), [], T0)            # conviction 3, b = 2
    assert s["reward_risk"] == 2.0 and s["kelly"] == pytest.approx(0.25)
    assert s["units"] == 1.0


def test_high_conviction_scales_up_in_quarter_steps_and_is_capped():
    s = sizing.suggest(_idea(conviction=5, target=115), [], T0)   # p .6, b 3 -> 1.87 -> 1.75
    assert s["units"] == 1.75
    s = sizing.suggest(_idea(conviction=5, target=150), [], T0)   # b 10 -> 2.24 -> cap 2.0
    assert s["units"] == 2.0 and any("Capped" in n for n in s["notes"])


def test_no_edge_and_too_small_mean_pass():
    s = sizing.suggest(_idea(conviction=1, target=105), [], T0)   # p .4, b 1
    assert s["units"] == 0.0 and s["kelly"] < 0
    s = sizing.suggest(_idea(conviction=2, target=106.5), [], T0)  # p .45, b 1.3 -> tiny edge
    assert s["units"] == 0.0 and any("minimum" in n for n in s["notes"])


def test_stated_probability_is_blended_not_used_raw():
    s = sizing.suggest(_idea(prob_win=0.7), [], T0)                # 0.5*0.7 + 0.5*0.5 = 0.6
    assert s["p"] == pytest.approx(0.6)
    assert s["units"] == 1.5                                       # f .4 / .25 = 1.6 -> 1.5


def test_calibrates_to_own_record_after_twenty_closed():
    rec = [_closed(i, r=1.0 if i < 15 else -1.0) for i in range(20)]
    p, src = sizing.prob_for(3, rec)
    assert p == pytest.approx((15 + 10 * 0.5) / (20 + 10), abs=1e-3) and "15/20" in src


def test_drawdown_halves_suggestions():
    rec = [_closed(i, r=-2.0, days_ago=5 + i) for i in range(3)]   # -6R inside 60 days
    s = sizing.suggest(_idea(), rec, T0)
    assert s["drawdown_r"] == -6.0 and s["units"] == 0.5


def test_flags_under_and_over_sizing_and_noise():
    e = _idea(conviction=5, target=115, size_planned=1.0)
    e["sizing"] = sizing.suggest(e, [], T0)
    assert any(f["rule"] == "undersized-vs-suggestion" for f in sizing.flags(e))
    e["size_planned"] = 3.0
    assert any(f["rule"] == "oversized" for f in sizing.flags(e))
    e["sizing"]["stop_sd"] = 0.6
    assert any(f["rule"] == "stop-in-noise" for f in sizing.flags(e))


def test_review_counts_r_left_on_table_and_brier():
    a = {**_closed(1, conviction=5, r=2.0), "size_planned": 1.0, "sizing": {"units": 2.0, "p": 0.6}}
    b = {**_closed(2, conviction=5, r=-1.0), "size_planned": 1.0, "sizing": {"units": 2.0, "p": 0.6}}
    out = sizing.review([a, b])
    assert out["r_left_on_table"] == pytest.approx((2 - 1) * 2.0 + (2 - 1) * -1.0)
    assert out["brier"]["score"] == pytest.approx(((0.6 - 1) ** 2 + 0.6 ** 2) / 2, abs=1e-3)
    assert out["by_conviction"][5]["hit_rate"] == 0.5


def test_journal_entry_carries_the_suggestion_and_cli_reviews(jbox, capsys):
    e, found = _paper(conviction=5, size_planned=0.5)              # b = 3, conviction 5
    saved = journal.get(e["id"])
    assert saved["size_suggested"] == e["sizing"]["units"] and saved["size_suggested"] > 0
    assert any(f["rule"] == "undersized-vs-suggestion" for f in found)
    assert journal.cli(["size", e["id"]]) == 0
    assert json.loads(capsys.readouterr().out)["units"] == saved["size_suggested"]
    assert journal.cli(["sizing-review"]) == 0
    assert json.loads(capsys.readouterr().out)["ideas"] == 1
