"""Decision journal: capture, hard checks, R maths, graveyard and stats (offline)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pmstack import fetch, journal, monitor, runlog, store
from pmstack.adapters import base
from test_pipeline import fake_get_json, fake_get_text

T0 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def jbox(tmp_path, monkeypatch):
    import numpy as np
    import test_pipeline
    monkeypatch.setattr(test_pipeline, "rng", np.random.default_rng(7))   # same fake data whatever ran before
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    monkeypatch.setattr(runlog, "LOG", tmp_path / "logs" / "runs.jsonl")
    monkeypatch.setattr(monitor, "BRIEFS", tmp_path / "briefs")
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal")
    monkeypatch.setattr(journal, "ROOT", journal.ROOT)          # config stays the repo's
    monkeypatch.setattr(base, "get_json", fake_get_json)
    monkeypatch.setattr(base, "get_text", fake_get_text)
    monkeypatch.setenv("EIA_API_KEY", "test")
    fetch.run(backfill=True)
    return tmp_path


def _paper(**kw):
    args = dict(market="Brent", direction="long", conviction=3, thesis="Draws continue into Q4.",
                price_ref="BZ=F", entry_price=100, target=115, invalidation_price=95, size_planned=1.0,
                horizon_days=20, now=T0)
    args.update(kw)
    return journal.new(**args)


def test_open_without_invalidation_is_blocked_and_not_written(jbox):
    e, found = _paper(invalidation_price=None)
    assert any(f["rule"] == "zweig-3" and f["level"] == "block" for f in found)
    assert not list((jbox / "journal").glob("*/*.md"))


def test_fund_book_is_refused_on_personal_build(jbox):
    e, found = _paper(book="live")
    assert any(f["rule"] == "personal-build" for f in found)
    assert not list((jbox / "journal").glob("*/*.md"))


def test_payoff_and_expected_r(jbox):
    e, _ = _paper(prob_win=0.4)
    assert e["reward_risk"] == 3.0                 # (115-100)/(100-95)
    assert e["expected_r"] == pytest.approx(0.4 * 3 - 0.6)
    assert (jbox / "journal" / "2026" / f"{e['id']}.md").exists()


def test_undersized_best_idea_is_flagged(jbox):
    for i in range(5):
        _paper(market=f"Idea {i}", size_planned=2.0, now=T0 - timedelta(days=30 + i))
    e, found = _paper(market="Copper", price_ref="HG=F", conviction=5, size_planned=1.0, entry_price=6, target=7,
                      invalidation_price=5.7)
    assert any(f["rule"] == "size-best-ideas" for f in found)


def test_crowded_side_flag_uses_cftc_memory(jbox):
    # fixture makes coffee managed money a 3-year extreme long
    e, found = _paper(market="Coffee", price_ref="KC=F", entry_price=300, target=330, invalidation_price=290)
    assert any(f["rule"] == "crowded-side" for f in found)


def test_close_r_multiple_holding_and_tilt(jbox):
    e, _ = _paper()
    closed = journal.close(e["id"], exit_price=110, process=4, now=T0 + timedelta(days=5))
    assert closed["r_multiple"] == 2.0 and closed["holding_days"] == 5.0
    e2, found = _paper(market="WTI", price_ref="CL=F", now=T0 + timedelta(days=5, hours=3))
    assert any(f["rule"] == "tilt" for f in found)


def test_short_r_sign(jbox):
    e, _ = _paper(direction="short", entry_price=100, target=85, invalidation_price=105)
    assert journal.close(e["id"], exit_price=95, process=3, now=T0 + timedelta(days=2))["r_multiple"] == 1.0


def test_idea_then_open_event(jbox):
    e, found = _paper(status="idea", invalidation_price=None, invalidation="close below 95")
    assert not any(f["level"] == "block" for f in found)
    e = journal.event(e["id"], "open", "breakout confirmed", size=1, price=101, now=T0 + timedelta(days=1))
    assert e["status"] == "open" and e["entry_price"] == 101


def test_stats_and_graveyard(jbox, monkeypatch):
    a, _ = _paper(conviction=4, size_planned=1.0)
    journal.close(a["id"], exit_price=110, process=4, now=T0 + timedelta(days=4))
    b, _ = _paper(market="WTI", price_ref="CL=F", conviction=2, size_planned=1.5, now=T0 + timedelta(days=10))
    journal.close(b["id"], exit_price=94, process=2, now=T0 + timedelta(days=12))
    c, _ = _paper(market="Gold", price_ref="GC=F", status="idea", now=T0 - timedelta(days=60),
                  entry_price=None, target=None, invalidation_price=None, invalidation="n/a")
    journal.reject(c["id"], "too crowded", now=T0 - timedelta(days=60))
    s = journal.stats()
    assert s["closed"]["n"] == 2 and s["closed"]["hit_rate"] == 0.5
    assert s["by_conviction"][4]["avg_r"] == 2.0 and s["by_conviction"][2]["avg_r"] == pytest.approx(-1.2)
    assert s["zweig_2_holding_days"] == {"winners": 4.0, "losers": 2.0}
    assert s["graveyard"]["n"] == 1


def test_open_book_distance_to_invalidation(jbox):
    e, _ = _paper()
    rows = journal.open_book(now=T0 + timedelta(days=1))
    r = next(x for x in rows if x["id"] == e["id"])
    assert r["last"] is not None and r["to_invalidation_pct"] is not None and r["source_url"].startswith("https://")
