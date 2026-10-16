"""Agent 11 regressions from the independent review (notes-A11): look-ahead in follow-ups, reconnect vs new
tie, forget and id reuse, nested forbidden fields, repo-internal home, public scorecard licence, post checks."""
from __future__ import annotations

import pytest
import yaml

from pmstack import network, store
from test_digest import _prices
from test_network import _call, _contact, nbox  # noqa: F401  (fixture)


def test_followup_closed_later_is_open_on_earlier_dates(nbox):
    c = _contact()
    rec = _call(c["id"], day="2026-09-20", follow_ups=[{"what": "send chart", "due": "2026-09-25"}])
    network.close_followup(rec["id"], "f1", "2026-10-10")
    assert network.due("2026-09-30")["follow_ups"][0]["overdue_days"] == 5
    assert network.due("2026-10-12")["follow_ups"] == []


def test_old_contact_first_call_is_a_reconnect_not_a_new_tie(nbox, monkeypatch):
    monkeypatch.setattr(network, "_today", lambda: "2026-10-20")
    c = _contact(first_contact="2020-01-15")
    _call(c["id"], day="2026-10-12")
    m = network.metrics("2026-10")
    assert m["new_ties"] == 0 and m["reconnects"] == 1
    assert network.due("2026-10-30")["second_touch"] == []        # not a new tie: no second-touch prompt
    with pytest.raises(SystemExit, match="hasn't started"):
        network.metrics("2026-11")


def test_forget_never_reuses_ids_and_lists_shared_calls(nbox):
    a, b = _contact(name="A One"), _contact(name="B Two")
    rec, _, _ = network.new_call({"date": "2026-09-02", "with": [a["id"], b["id"]], "initiator": "me",
                                  "medium": "in-person", "mnpi_attestation": "None received."})
    out = network.forget(b["id"])
    assert out["redact_by_hand"] == [rec["id"]]
    c, _ = network.add_contact({"name": "C Three", "role": "r", "firm": "f", "cluster": "energy"})
    assert c["id"] == "c0003"                                     # c0002 is never given to someone else


def test_nested_and_camelcase_forbidden_fields(nbox):
    _, errs = network.add_contact({"name": "X", "role": "r", "firm": "f", "cluster": "energy", "phoneNumber": "1"})
    assert any("phoneNumber" in e for e in errs)
    c = _contact()
    rec, block, _ = network.new_call({"date": "2026-09-02", "with": [c["id"]], "initiator": "me", "medium": "phone",
                                      "mnpi_attestation": "none received", "context": {"personal": {"spouse": "x"}}})
    assert rec is None and any("context.personal.spouse" in b for b in block)


def test_attestation_wording(nbox):
    c = _contact()
    base = {"date": "2026-09-02", "with": [c["id"]], "initiator": "me", "medium": "phone"}
    assert network.new_call({**base, "mnpi_attestation": "Not received"})[0] is not None
    _, block, _ = network.new_call({**base, "mnpi_attestation": "maybe"})
    assert block and "must read" in block[0] and "compliance" not in block[0]


def test_home_inside_repo_is_refused(monkeypatch):
    monkeypatch.setenv("PM_NETWORK_HOME", str(network.ROOT / "network"))
    with pytest.raises(SystemExit, match="inside pm-agent-stack"):
        network.home()


def test_public_score_refuses_a_call_without_a_public_series(nbox):
    store.upsert_obs("prices", _prices("BZ=F", "2025-01-01", "2026-12-31", 70.0, 0.05))
    pub = nbox / "public"
    pub.mkdir(exist_ok=True)
    # a hand-edited call with no recorded series must still be scored on the public series, never on Yahoo
    (pub / "calls.yaml").write_text(yaml.safe_dump({"calls": [
        {"id": "pub-1-1", "issue": 1, "date": "2026-06-30", "market": "BZ=F", "direction": "up", "deadline": "2026-08-31",
         "claim": "x", "invalidation": "y"},
        {"id": "pub-1-2", "issue": 1, "date": "2026-06-30", "market": "GC=F", "direction": "up", "deadline": "2026-08-31",
         "claim": "x", "invalidation": "y"}]}), encoding="utf-8")
    store.upsert_obs("prices", _prices("GC=F", "2025-01-01", "2026-12-31", 2000.0, 1.0))
    rows = {r["card"]: r for r in network.score_public("2026-10-01")["calls"]}
    assert "fred.stlouisfed" in rows["pub-1-1"]["source_url"] or "DCOILBRENTEU" in rows["pub-1-1"]["price_ref"]
    assert rows["pub-1-2"]["status"] == "refused"


def test_post_check_without_repo_and_surnames_and_issue(nbox, monkeypatch):
    _contact(name="Ana Silva")
    post = nbox / "post.md"
    disc = network.cfg()["public"]["disclaimer"]
    post.write_text(f"# 3 things on Brent: Commodity note #1\n\nSilva thinks Brent goes up.\n\n{disc}\n", encoding="utf-8")
    chk = network.check_post(post)
    assert chk["issue"] == 1 and any("contact" in p for p in chk["problems"])
    monkeypatch.setenv("PM_NETWORK_HOME", str(nbox / "missing"))
    post.write_text(f"# Commodity note #1\n\nBrent goes up.\n\n{disc}\n", encoding="utf-8")
    assert any("not checked" in p for p in network.check_post(post)["problems"])
