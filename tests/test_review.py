"""Weekly review (agent 6): gates, intervals, leaks, exits, goals, monthly section (offline)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from pmstack import journal, monitor, review
from test_journal import jbox  # noqa: F401

T0 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)      # Thursday
FRI = date(2026, 10, 2)


def _idea(**kw):
    args = dict(market="Brent", direction="long", conviction=3, thesis="Draws continue.", price_ref="BZ=F",
                entry_price=100, target=110, invalidation_price=95, size_planned=1.0, horizon_days=20, now=T0)
    args.update(kw)
    return journal.new(**args)[0]


def _closed(r, when, **kw):
    e = _idea(now=when - timedelta(days=5), **kw)
    return journal.close(e["id"], r=r, process=3, lesson="x", now=when, trigger="event")


def test_wilson_and_t_table():
    assert review.wilson(3, 5) == (0.231, 0.882)
    assert review.wilson(12, 20) == (0.387, 0.781)
    assert review.t975(9) == pytest.approx(2.262)
    assert review.ideas_needed(0.25, 1.5) in (283, 284)


def test_counts_only_below_ten_then_intervals(jbox):
    for i in range(5):
        _closed(1.0 if i % 2 else -1.0, T0 - timedelta(days=10 + i), market=f"M{i}")
    out = review.weekly(FRI)
    assert out["outcomes"]["mode"] == "counts-only" and "hit_rate" not in out["outcomes"]
    for i in range(7):
        _closed(1.5 if i % 2 else -0.5, T0 - timedelta(days=20 + i), market=f"N{i}")
    o = review.weekly(FRI)["outcomes"]
    assert o["mode"] == "intervals" and o["n_closed"] == 12
    hr = o["hit_rate"]
    assert hr["wilson95"][0] < hr["raw"] < hr["wilson95"][1]
    assert abs(hr["shrunk"] - 0.5) < abs(hr["raw"] - 0.5) or hr["raw"] == hr["shrunk"]   # shrunk toward the prior
    assert abs(o["mean_r"]["shrunk"]) <= abs(o["mean_r"]["raw"])


def test_examples_are_excluded(jbox):
    _closed(2.0, T0, book="example")
    out = review.weekly(FRI)
    assert out["outcomes"]["n_closed"] == 0 and out["examples_excluded"] == 1


def test_tilt_counts_both_directions(jbox):
    _closed(-1.5, T0 - timedelta(days=2), market="Loss")
    _idea(market="Rebound A", now=T0 - timedelta(days=1), size_planned=2.0)
    _idea(market="Rebound B", now=T0 - timedelta(hours=30))
    _closed(1.2, T0 - timedelta(days=30), market="Win")
    t = review.weekly(FRI)["leaks"]["tilt"]
    assert t["after_loss"]["closes"] == 1 and t["after_loss"]["new_ideas_within"] == 2
    assert t["after_loss"]["avg_size_vs_prior_median"] > 1
    assert t["after_win"]["closes"] == 1


def test_held_past_invalidation_and_goal_tracking(jbox):
    px = journal._last_price("BZ=F")[0]
    e = _idea(entry_price=px * 1.2, target=px * 1.4, invalidation_price=px * 1.1)   # already through invalidation
    out = review.weekly(FRI)
    assert any(h["id"] == e["id"] for h in out["process"]["held_past_invalidation"])
    g = review.goal_counts("invalidation-same-day", journal.load_all(), FRI)
    assert g["triggers"] == 1 and g["honoured"] == 0
    journal.event(e["id"], "note", "re-underwritten: physical premium still wide", now=T0 + timedelta(hours=2))
    g = review.goal_counts("invalidation-same-day", journal.load_all(), FRI)
    assert g["honoured"] == 1


def test_exit_trigger_inferred_or_required(jbox):
    e = _idea()
    assert journal.infer_trigger(journal.get(e["id"]), 111) == "target"
    assert journal.infer_trigger(journal.get(e["id"]), 94) == "invalidation"
    assert journal.infer_trigger(journal.get(e["id"]), 102) is None
    assert journal.cli(["close", e["id"], "--exit-price", "102", "--process", "3"]) == 2      # must tag
    assert journal.cli(["close", e["id"], "--exit-price", "102", "--process", "3", "--trigger", "event"]) == 0
    assert journal.get(e["id"])["exit_trigger"] == "event"
    out = review.weekly(FRI)
    assert out["leaks"]["exits_by_trigger"]["event"]["n_all_time"] == 1


def test_goal_set_propose_and_replace(jbox):
    assert review.propose_goal([], FRI)["key"] == "log-ideas"
    review.set_goal("tag-exits", date(2026, 10, 5))
    assert review.active_goal(date(2026, 10, 4)) is None
    assert review.active_goal(date(2026, 10, 6))["key"] == "tag-exits"
    review.set_goal("after-loss-pause", date(2026, 10, 12), source="bernardo")
    assert review.active_goal(date(2026, 10, 13))["key"] == "after-loss-pause"
    assert review.active_goal(date(2026, 10, 7))["key"] == "tag-exits"
    with pytest.raises(SystemExit):
        review.set_goal("make-money", date(2026, 10, 12))                     # outcome goals aren't in the catalogue


def test_goal_proposed_from_misses(jbox):
    for i in range(3):
        _idea(market=f"P{i}", now=T0 - timedelta(days=i), invalidation_price=1, target=1000)   # no P(win); never invalidated
    p = review.propose_goal(journal.load_all(), FRI)
    assert p["key"] == "prob-before-entry"


def test_extreme_week_caption_and_monthly(jbox):
    monitor.build(asof=date(2026, 10, 1))
    for i in range(2):
        _closed(2.0, T0 - timedelta(hours=i + 1), market=f"Big{i}")
    out = review.weekly(FRI, monthly_override=True)
    assert out["extreme_week"] and out["captions"]
    m = out["monthly"]
    assert m["month"] == "2026-09" and isinstance(m["regime"], list)
    assert review.first_friday_after_month_end(date(2026, 11, 6))
    assert not review.first_friday_after_month_end(date(2026, 10, 30))


# ------------------------------------------------------------------ regressions from the independent review
SAT = datetime(2026, 10, 3, 15, 0, tzinfo=timezone.utc)


def test_weekend_and_friday_evening_ideas_land_in_next_review(jbox):
    _idea(market="Weekend", now=SAT)
    _idea(market="Friday late", now=datetime(2026, 10, 2, 22, 30, tzinfo=timezone.utc))     # 19:30 BRT, after the run
    assert review.weekly(FRI)["process"]["new_ideas"] == 0
    assert review.weekly(date(2026, 10, 9))["process"]["new_ideas"] == 2


def test_friday_proposal_never_overwrites_his_goal(jbox):
    mine = review.set_goal("after-loss-pause", date(2026, 10, 12), source="bernardo")
    assert review.propose_goal(journal.load_all(), date(2026, 10, 9))["key"] == "after-loss-pause"
    got = review.set_goal("tag-exits", date(2026, 10, 12), source="review")
    assert got["key"] == "after-loss-pause" and review.active_goal(date(2026, 10, 13))["set_by"] == "bernardo"
    assert mine["status"] == "active"


def test_invalidation_uses_fill_close_and_event_order(jbox):
    px = journal._last_price("BZ=F")[0]
    early = _idea(market="Closed early", entry_price=px * 1.2, target=px * 1.4, invalidation_price=px * 1.1,
                  now=T0 - timedelta(days=20))
    journal.close(early["id"], r=1.0, process=3, lesson="x", trigger="target", now=T0 - timedelta(days=19))
    pre = _idea(market="Noted first", entry_price=px * 1.2, target=px * 1.4, invalidation_price=px * 1.1,
                now=T0 - timedelta(days=1), status="idea")
    journal.event(pre["id"], "note", "re-underwrite before anything happened", now=T0 - timedelta(hours=20))
    out = review.weekly(FRI)
    assert not any(h["id"] == early["id"] for h in out["process"]["held_past_invalidation"])
    assert not any(h["id"] == pre["id"] for h in out["process"]["held_past_invalidation"])     # never taken
    g = review.goal_counts("invalidation-same-day", journal.load_all(), FRI)
    assert early["id"] not in g["ids"] and pre["id"] not in g["ids"]


def test_brier_uses_stated_prob_only(jbox):
    for i in range(10):
        _closed(1.0 if i < 8 else -1.0, T0 - timedelta(days=10 + i), market=f"B{i}", prob_win=0.95)
    for i in range(2):
        _closed(1.0, T0 - timedelta(days=30 + i), market=f"C{i}")              # no stated P(win)
    o = review.weekly(FRI)["outcomes"]
    assert o["prob_stated"] == {"n": 10, "of_closed": 12}
    assert o["brier"]["score"] == pytest.approx((8 * 0.05 ** 2 + 2 * 0.95 ** 2) / 10, abs=1e-3)


def test_zero_suggestion_counts_as_a_sizing_miss(jbox):
    e = _idea(market="No edge", entry_price=100, target=100.5, invalidation_price=95, size_planned=1.0, now=T0)
    assert journal.get(e["id"])["size_suggested"] == 0
    assert e["id"] in review.weekly(FRI)["process"]["sized_by_rule"]["misses"]


def test_after_loss_pause_ignores_logged_passes(jbox):
    _closed(-1.5, T0 - timedelta(days=1), market="Loss")
    p = _idea(market="Passed", status="idea", now=T0 - timedelta(hours=20))
    journal.reject(p["id"], "no edge", now=T0 - timedelta(hours=19))
    g = review.goal_counts("after-loss-pause", journal.load_all(), FRI)
    assert g == {"key": "after-loss-pause", "triggers": 1, "honoured": 1, "ids": g["ids"]}


def test_audit_binds_figures_to_their_own_market_and_list_markers(jbox):
    import json as _json
    from pmstack import audit
    monitor.build(asof=date(2026, 10, 1))
    facts = _json.loads((jbox / "briefs" / "2026-10-01" / "facts.json").read_text(encoding="utf-8"))
    brent = next(r for r in facts["sections"]["prices"] if r["id"] == "BZ=F")
    pool = audit.pool_for("2026-10-01", with_journal=False)
    last = f"{brent['last']:.2f}"
    rep = audit.audit_text(f"# T\n\nGold front month at {last} today.\nBrent fell to\n{last}. That breaks it.\n\n1. Brent at {last}.\n", pool)
    st = [(f["line"], f["status"]) for f in rep["figures"] if f["text"] == last]
    assert (3, "unbound") in st                    # Brent's price quoted as gold's
    assert (5, "unbound") in st                    # a figure at a line start is checked, not taken for a list marker
    assert any(f["line"] == 7 and f["text"] == "1." or f["line"] == 7 and f["status"] == "structural" for f in rep["figures"])
