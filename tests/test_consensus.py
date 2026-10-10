"""Consensus and narrative monitor (agent 7): GDELT stages, trend proxy, labels, ideas, stable alert refs (offline)."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd

from pmstack import audit, consensus, fetch, journal, monitor
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
    assert any(a["kind"] == "narrative_spreading" and a["id"] == "hormuz_iran_v1" for a in facts["alerts"]) \
        or nar["hormuz_iran_v1"]["stage_yesterday"] == "spreading"


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
