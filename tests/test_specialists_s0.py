"""Specialists S0: point-in-time facts (no look-ahead), state-card contract, routing, knowledge drivers with size
provenance, inbox gate (offline; temp folders only, no real date dependence)."""
from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path

import pytest

from pmstack import cards, facts, inbox, knowledge, route


# ------------------------------------------------------------------ facts
@pytest.fixture()
def flog(tmp_path):
    return tmp_path / "facts.jsonl"


def _rec(flog, value, vf, av, subject="crude", predicate="us_stocks", **kw):
    return facts.record(subject, predicate, value, unit="kbbl", valid_from=vf, available_at=av,
                        source_url="https://www.eia.gov/petroleum/supply/weekly/", source_type="agency_report",
                        writer="pmstack.test", path=flog, **kw)


def test_facts_no_look_ahead_on_release_date(flog):
    _rec(flog, 420000, "2025-01-03", "2025-01-08")            # week ending Fri 3 Jan, released Wed 8 Jan
    assert facts.as_of("2025-01-07", "crude", path=flog).empty   # true on 7 Jan, but not public yet
    r = facts.as_of("2025-01-08", "crude", path=flog)
    assert list(r["value_num"]) == [420000]


def test_facts_revision_wins_only_from_its_availability(flog):
    _rec(flog, 420000, "2025-01-03", "2025-01-08")
    _rec(flog, 421500, "2025-01-03", "2025-02-01")            # revised print
    assert facts.value_as_of("2025-01-20", "crude", "us_stocks", path=flog) == 420000
    assert facts.value_as_of("2025-02-02", "crude", "us_stocks", path=flog) == 421500
    assert len(facts.load(flog)) == 2                          # nothing overwritten


def test_facts_supersede_closes_valid_to_only_once_known(flog):
    _rec(flog, 420000, "2025-01-03", "2025-01-08")
    _rec(flog, 415000, "2025-01-10", "2025-01-15")
    k_before = facts.known("2025-01-12", path=flog)
    assert k_before.iloc[0]["valid_to"] is None                # as known on 12 Jan, the old fact is still open
    k_after = facts.known("2025-01-16", path=flog)
    assert list(k_after["valid_to"]) == ["2025-01-10", None]
    assert facts.value_as_of("2025-01-16", "crude", "us_stocks", path=flog) == 415000
    # a backdated read keeps the earlier value even with today's knowledge
    assert facts.value_as_of("2025-01-09", "crude", "us_stocks", known_at="2025-06-01", path=flog) == 420000


def test_facts_retract_and_provenance_rules(flog):
    r = _rec(flog, 1, "2025-01-03", "2025-01-08")
    facts.retract(r["fact_id"], reason="wrong unit", writer="pmstack.test", path=flog)
    assert facts.known(path=flog).empty
    assert len(facts.as_of("2025-01-09", "crude", known_at="2025-01-09", path=flog)) == 1   # before the retraction
    with pytest.raises(ValueError, match="writer"):
        facts.record("x", "y", 1, valid_from="2025-01-01", source_url="u", source_type="data", writer="claude", path=flog)
    with pytest.raises(ValueError, match="source_url"):
        facts.record("x", "y", 1, valid_from="2025-01-01", source_url="", source_type="data", writer="pmstack.t", path=flog)
    with pytest.raises(ValueError, match="future"):
        facts.record("x", "y", 1, valid_from="2025-01-01", available_at="2999-01-01", source_url="u",
                     source_type="data", writer="pmstack.t", path=flog)


def test_facts_record_is_idempotent(flog):
    _rec(flog, 420000, "2025-01-03", "2025-01-08")
    _rec(flog, 420000, "2025-01-03", "2025-01-08")
    assert len(facts.load(flog)) == 1
    kw = dict(valid_from="2026-10-24", source_type="literature", writer="pmstack.test", path=flog, unit="elasticity")
    facts.record("driver:x", "size:literature", -0.26, source_url="https://a", **kw)
    facts.record("driver:x", "size:literature", -0.26, source_url="https://a", **kw)   # re-filed later, no release time
    facts.record("driver:x", "size:literature", -0.35, source_url="https://b", **kw)
    facts.record("driver:x", "size:literature", -0.08, source_url="https://c", **kw)
    assert len(facts.load(flog)) == 4
    assert sorted(facts.as_of("2026-10-24", "driver:x", known_at="2999-01-01", path=flog)["value_num"]) == [-0.35, -0.26, -0.08]


# ------------------------------------------------------------------ state cards
def _card(**over):
    c = {
        "schema": "state_card/v1", "subject": "crude", "level": "commodity", "as_of": "2026-10-23",
        "author": "energy/claude-opus-5-5",
        "balance_view": {"text": "US commercial crude stocks sit 2.1 sd below the 5-year same week [s1].", "state": "tight"},
        "curve_shape": {"text": "Front spread not stored yet; no read.", "state": "unknown"},
        "positioning": {"text": "Managed money at the 85th percentile of three years [s2].", "state": "crowded long"},
        "narrative_stage": {"text": "Oil and product supply reinforcing in the news feed.", "state": "growing"},
        "what_changed": ["Stocks drew more than the 5-year change for the week [s1]."],
        "would_change_view": ["A build larger than the seasonal norm for 4 weeks in a row."],
        "next_events": [{"date": "2026-10-28", "event": "EIA weekly petroleum status report"}],
        "confidence": "medium",
        "sources": [{"id": "s1", "label": "bal.crude.z", "value": -2.1, "unit": "sd", "date": "2026-10-16",
                     "url": "https://www.eia.gov/petroleum/supply/weekly/"},
                    {"id": "s2", "label": "CFTC MM percentile", "value": 85, "unit": "pct", "date": "2026-10-20",
                     "url": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"}],
    }
    c.update(over)
    return c


def test_card_valid_and_saved_without_overwrite(tmp_path):
    c = _card()
    assert cards.validate(c, today=date(2026, 10, 24)) == []
    pack = {"sources": copy.deepcopy(c["sources"])}
    with pytest.raises(ValueError, match="input pack"):
        cards.save(c, root=tmp_path, today=date(2026, 10, 24))
    p1 = cards.save(c, root=tmp_path, today=date(2026, 10, 24), packs=[pack])
    p2 = cards.save(c, root=tmp_path, today=date(2026, 10, 24), packs=[pack])
    assert p1 != p2 and p1.exists() and p2.exists()
    assert cards.latest("crude", "2026-10-23", root=tmp_path) == p2
    assert cards.latest("crude", "2026-10-22", root=tmp_path) is None


def test_card_rejects_uncited_figures_unknown_refs_and_look_ahead():
    c = _card(what_changed=["Stocks fell 3.7 mb [s3]."])
    probs = cards.validate(c, today=date(2026, 10, 24))
    assert any("3.7" in p for p in probs) and any("s3" in p for p in probs)
    c = _card()
    c["sources"][0]["date"] = "2026-10-25"
    assert any("look-ahead" in p for p in cards.validate(c, today=date(2026, 10, 30)))
    c = _card(as_of="2026-10-30")
    assert any("after today" in p for p in cards.validate(c, today=date(2026, 10, 24)))


def test_card_schema_errors_and_windows_are_not_figures():
    c = _card()
    del c["confidence"]
    c["mood"] = "bullish"
    probs = cards.validate(c, today=date(2026, 10, 24))
    assert any("confidence: missing" in p for p in probs) and any("mood: unknown field" in p for p in probs)
    c = _card(would_change_view=["A 4-week run of builds since 2018, as on Oct 24, 2025."])
    assert cards.validate(c, today=date(2026, 10, 24)) == []
    c = _card(would_change_view=["Cover falls to 25 days; gold at 2,050 $/oz."])      # quantities, not windows or years
    probs = cards.validate(c, today=date(2026, 10, 24))
    assert any("25" in p for p in probs) and any("2,050" in p for p in probs)


def test_card_review_fixes_sign_strings_and_pack():
    c = _card(what_changed=["Stocks moved +2.1 sd [s1]."])                 # source is -2.1: explicit sign must match
    assert any("+2.1" in p for p in cards.validate(c, today=date(2026, 10, 24)))
    c = _card(what_changed=["Stocks sit 2.1 sd below normal [s1]."])        # unsigned magnitude is fine
    assert cards.validate(c, today=date(2026, 10, 24)) == []
    c = _card(what_changed=["Brent at 95 [s3]."])
    c["sources"].append({"id": "s3", "label": "made up", "value": "90 95 100", "unit": None, "date": "2026-10-20", "url": "x"})
    assert any("95" in p for p in cards.validate(c, today=date(2026, 10, 24)))   # a string value whitelists nothing
    c = _card()
    pack = {"sources": copy.deepcopy(c["sources"])}
    c["sources"][0]["value"] = -2.5
    c["balance_view"]["text"] = "Stocks sit 2.5 sd below the 5-year same week [s1]."
    probs = cards.validate(c, today=date(2026, 10, 24), packs=[pack])
    assert any("not a row of the input pack" in p for p in probs)


def test_complex_card_lists_children():
    c = _card(subject="energy", level="complex")
    assert any("children" in p for p in cards.validate(c, today=date(2026, 10, 24)))
    c["children"] = ["cards/crude/2026-10-23-energy.json"]
    c["cross_links"] = ["Diesel cracks link crude to the products balance."]
    assert cards.validate(c, today=date(2026, 10, 24)) == []


# ------------------------------------------------------------------ routing
def test_route_explicit_prefix_and_keywords():
    r = route.route("/ask energy: why is the WTI spread wide?")
    assert r["specialist"] == "energy" and r["forced"] == "energy" and "curve" in r["question_types"]
    assert any(f.endswith("crude/primer.md") for f in r["files"])
    r = route.route("How tight are distillate stocks vs normal?")
    assert r["specialist"] == "energy" and r["commodities"] == ["products"] and "balance" in r["question_types"]


def test_route_planned_specialist_and_other_pillar():
    r = route.route("What is driving corn this week?")              # ags is planned (S4); metals went live in S3
    assert r["specialist"] is None and r["inactive"] == ["ags"] and "not built yet" in r["note"]
    r = route.route("Is the CTA trend signal stretched?")
    assert r["specialist"] is None and "quant" in r["other_pillars"]


# ------------------------------------------------------------------ knowledge
@pytest.fixture()
def kroot(tmp_path, monkeypatch):
    root = tmp_path / "knowledge"
    (root / "energy" / "crude").mkdir(parents=True)
    monkeypatch.setattr(knowledge, "KNOWLEDGE", root)
    monkeypatch.setattr(knowledge, "PENDING", root / "inbox" / "pending.jsonl")
    monkeypatch.setattr(facts, "FACTS", tmp_path / "facts.jsonl")
    return root


def _driver(**over):
    d = {"id": "stocks-vs-spread", "claim": "Lower US crude stocks vs norm go with a stronger WTI front spread.",
         "driver": "US commercial crude stocks vs 5-year same week", "target": "WTI M1-M2 spread", "sign": "-",
         "lag": "same week",
         "sizes": [{"kind": "literature", "value": -0.3, "unit": "$/bbl per 10 mb", "source": "Example (2020)",
                    "url": "https://example.org/paper"}]}
    d.update(over)
    return d


def test_driver_add_render_and_fact(kroot):
    knowledge.add("energy/crude", _driver(), root=None)
    md = (kroot / "energy" / "crude" / "drivers.md").read_text(encoding="utf-8")
    assert "stocks-vs-spread" in md and "literature: -0.3" in md
    f = facts.as_of(date.today().isoformat(), "driver:stocks-vs-spread")
    assert list(f["source_type"]) == ["literature"]


def test_driver_rules_refuse_unconfirmed_priors_and_broker_sizes(kroot):
    with pytest.raises(ValueError, match="confirm-prior"):
        knowledge.add("energy/crude", _driver(sizes=[{"kind": "bernardo_prior", "value": -0.5, "unit": "$/bbl per 10 mb"}]))
    with pytest.raises(ValueError, match="confirm-prior"):        # a 'confirmed' key does not bypass the confirm flow
        knowledge.add("energy/crude", _driver(sizes=[{"kind": "bernardo_prior", "value": -0.5, "unit": "$/bbl per 10 mb",
                                                       "confirmed": "2026-10-20"}]))
    with pytest.raises(ValueError, match="broker"):
        knowledge.add("energy/crude", _driver(sizes=[{"kind": "literature", "value": -0.5, "unit": "$/bbl per 10 mb",
                                                       "source": "Goldman Sachs commodities note", "url": "https://x"}]))
    with pytest.raises(ValueError, match="regression"):
        knowledge.add("energy/crude", _driver(sizes=[{"kind": "own_estimate", "value": -0.5, "unit": "$/bbl per 10 mb"}]))


def test_prior_confirm_flow_and_disagreement(kroot):
    knowledge.add("energy/crude", _driver(), root=None)
    recs = knowledge.propose([{"commodity": "energy/crude", "driver_id": "stocks-vs-spread", "value": 0.4,
                               "unit": "$/bbl per 10 mb"}], source_file_sha="abc123def456")
    pid = recs[0]["pid"]
    assert [r["pid"] for r in knowledge.pending_list()] == [pid]
    knowledge.confirm_prior(pid, today="2026-01-02")
    assert knowledge.pending_list() == []
    dis = knowledge.check("energy/crude")
    assert len(dis) == 1 and dis[0]["why"] == "opposite sign"
    oq = (kroot / "energy" / "crude" / "open-questions.md").read_text(encoding="utf-8")
    assert "opposite sign" in oq and knowledge.BLOCK_START in oq
    knowledge.check("energy/crude")                                    # rebuilt, not duplicated
    assert (kroot / "energy" / "crude" / "open-questions.md").read_text(encoding="utf-8").count(knowledge.BLOCK_START) == 1
    with pytest.raises(KeyError):
        knowledge.confirm_prior(pid)                                   # only once


# ------------------------------------------------------------------ inbox
@pytest.fixture()
def ibox(tmp_path):
    d = tmp_path / "inbox"
    d.mkdir()
    return d


def test_inbox_screen_flags_broker_and_refusal_stores_nothing(ibox):
    f = ibox / "note.txt"
    f.write_text("Commodities Research. Analyst certification. Price target raised. Important disclosures.", encoding="utf-8")
    s = inbox.screen(f)
    assert s["suggest"] == "broker"
    led = ibox / "ledger.jsonl"
    rec = inbox.classify(f, "broker", led=led)
    assert set(rec) == {"sha12", "type", "state", "decided_by", "at"}         # no filename, no content
    assert "note.txt" not in led.read_text(encoding="utf-8")
    with pytest.raises(PermissionError):
        inbox.ingest(f, led=led)
    assert inbox.status(ibox, led)[0]["state"].startswith("remove")
    with pytest.raises(PermissionError, match="final"):            # a refusal cannot be overturned
        inbox.classify(f, "own_note", led=led)
    x = ibox / "deck.pptx"
    x.write_bytes(b"PK\x03\x04 not text")
    assert inbox.screen(x)["readable"] is False


def test_inbox_requires_classification_then_ingests(ibox, tmp_path):
    f = ibox / "my-study.md"
    f.write_text("My framework for crude timespreads.\nInventories drive the front spread, with a lag of weeks.\n", encoding="utf-8")
    led = ibox / "ledger.jsonl"
    with pytest.raises(PermissionError):
        inbox.ingest(f, led=led)
    assert inbox.screen(f)["suggest"] is None
    inbox.classify(f, "own_study", led=led)
    res = inbox.ingest(f, led=led, out_dir=tmp_path / "tr")
    assert res["source_type"] == "own_study" and (tmp_path / "tr" / f"{res['transcript']}.txt").exists()
    assert inbox.status(ibox, led)[0]["state"] == "ingested"
