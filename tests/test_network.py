"""Network and reputation (agent 11): private-repo contacts and calls, MNPI refusal, follow-ups, reconnects,
monthly metrics, forget, and the public note's pack, calls, score and checks (offline, synthetic prices)."""
from __future__ import annotations

import json

import pytest

from pmstack import digest, journal, network, runlog, store
from test_digest import _prices
import pandas as pd


@pytest.fixture()
def nbox(tmp_path, monkeypatch):
    h = tmp_path / "pm-network"
    monkeypatch.setenv("PM_NETWORK_HOME", str(h))
    monkeypatch.setattr(runlog, "LOG", tmp_path / "logs" / "runs.jsonl")
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    monkeypatch.setattr(digest, "NOTES", tmp_path / "notes")
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal")
    pub = tmp_path / "public"
    monkeypatch.setattr(network, "public_dir", lambda: pub)
    network.init(git=False)
    store.upsert_obs("fred", _prices("DCOILBRENTEU", "2025-01-01", "2026-12-31", 80.0, 0.05).assign(source="fred"))
    store.upsert_obs("prices", _prices("GC=F", "2025-01-01", "2026-12-31", 2000.0, 1.0))
    return tmp_path


def _contact(**kw):
    f = {"name": "Ana Example", "role": "crude trader", "firm": "Acme Trading", "cluster": "energy",
         "chain_role": "trader", "region": "eu", "layer": 15, "tie": 4, "trust": 4, "markets": ["BZ=F"]}
    f.update(kw)
    c, errs = network.add_contact(f)
    assert not errs, errs
    return c


def _call(cid, day="2026-09-01", **kw):
    m = {"date": day, "with": [cid], "initiator": "me", "medium": "video", "topics": ["Brent physical premium"],
         "gives": ["sent the EIA chart"], "asks": [], "follow_ups": [{"what": "send the dated-vs-futures chart"}],
         "mnpi_attestation": "none received"}
    m.update(kw)
    rec, block, warn = network.new_call(m, kw.pop("body", "c0001 said the premium stays wide."))
    assert not block, block
    return rec


def test_init_and_contact_validation(nbox):
    h = network.home()
    assert (h / "contacts.yaml").exists() and (h / "README.md").exists() and (h / "calls").is_dir()
    c = _contact()
    assert c["id"] == "c0001" and c["first_contact"] and c["mnpi_risk"] == "none"
    _, errs = network.add_contact({"name": "B", "role": "r", "firm": "f", "cluster": "energy", "phone": "123"})
    assert any("never stored" in e for e in errs)
    _, errs = network.add_contact({"name": "B", "role": "r", "firm": "f", "cluster": "nowhere"})
    assert any("cluster" in e for e in errs)
    assert len(network.load_contacts()) == 1


def test_call_needs_attestation_and_refuses_mnpi(nbox):
    c = _contact()
    base = {"date": "2026-09-01", "with": [c["id"]], "initiator": "me", "medium": "phone"}
    rec, block, _ = network.new_call(base)
    assert rec is None and any("attestation" in b for b in block)
    rec, block, _ = network.new_call({**base, "mnpi_attestation": "received: earnings early"})
    assert rec is None and any("compliance" in b for b in block)
    assert not list((network.home() / "calls").glob("*/*.md"))         # nothing written


def test_call_ids_followups_and_name_warning(nbox):
    c = _contact()
    r1 = _call(c["id"])
    r2 = _call(c["id"])
    assert r1["id"] == "2026-09-01-01" and r2["id"] == "2026-09-01-02"
    assert r1["follow_ups"][0] == {"what": "send the dated-vs-futures chart", "owner": "me", "due": "2026-09-02",
                                   "status": "open", "id": "f1"}
    _, _, warn = network.new_call({"date": "2026-09-03", "with": [c["id"]], "initiator": "them", "medium": "phone",
                                   "mnpi_attestation": "none received"}, "Talked to Ana Example about diesel.")
    assert warn and "by id" in warn[0]
    log = (nbox / "logs" / "runs.jsonl").read_text(encoding="utf-8")
    assert "Ana" not in log and "Acme" not in log                       # names never reach the run log


def test_due_overdue_cadence_and_second_touch(nbox):
    c = _contact(layer=5)
    _call(c["id"], day="2026-09-01")
    d = network.due("2026-09-20")
    assert d["follow_ups"][0]["overdue_days"] == 18
    assert d["cadence_gaps"][0]["id"] == c["id"] and d["cadence_gaps"][0]["cadence_days"] == 14
    assert d["second_touch"][0]["id"] == c["id"] and d["second_touch"][0]["late"] is False
    rec = network.load_calls()[0]
    network.close_followup(rec["id"], "f1", "2026-09-02")
    assert network.due("2026-09-20")["follow_ups"] == []


def test_reconnect_picks_dormant_with_seeded_random(nbox):
    ids = [_contact(name=f"P{i}", cluster="us-rates" if i % 2 else "energy", layer=50).get("id") for i in range(6)]
    for cid in ids:
        _call(cid, day="2025-01-10")
    _call(ids[0], day="2026-09-01")                       # not dormant any more
    out = network.reconnect("2026-10-01", seed="w")
    picked = [p["id"] for p in out["picks"]]
    assert out["dormant"] == 5 and ids[0] not in picked and len(picked) == 2
    assert out["picks"][-1]["why"].startswith("random")
    assert network.reconnect("2026-10-01", seed="w")["picks"] == out["picks"]   # same week, same list


def test_monthly_metrics(nbox):
    a = _contact(name="A", cluster="energy")
    b = _contact(name="B", cluster="allocators")
    _call(a["id"], day="2025-06-01")
    _call(a["id"], day="2026-09-03", initiator="them", gives=[], asks=["intro to a shipper"])
    _call(b["id"], day="2026-09-10")
    network.close_followup("2026-09-03-01", "f1", "2026-09-04")       # due 4 Sep: on time
    m = network.metrics("2026-09")
    assert m["calls"] == 2 and m["bridging_share_pct"] == 50 and m["initiated_by_them_pct"] == 50
    assert m["followups_due"] == 2 and m["followups_on_time_pct"] == 50 and m["followups_overdue"] == 2      # the June 2025 one is still open
    assert m["new_ties"] == 1 and m["reconnects"] == 1 and m["give_ask"] == 1.0
    page = network.monthly("2026-09", write=True)
    assert (network.home() / "monthly" / "2026-09.json").exists() and page["metrics"]["calls"] == 2


def test_prep_and_mnpi_warning_and_questions(nbox):
    c = _contact(mnpi_risk="gov-data")
    _call(c["id"])
    d = nbox / "notes" / "podcasts"
    d.mkdir(parents=True)
    (d / "2026-08-01-x.md").write_text('---\ntype: podcast\ndate: 2026-08-01\nassets: [BZ=F]\n'
                                       'questions: ["Is the physical premium widening?"]\n---\n', encoding="utf-8")
    out = network.prep(c["id"], "2026-09-15")
    assert "mnpi_risk gov-data" in out["warning"] and out["open_follow_ups"][0]["what"]
    assert out["questions"][0]["q"] == "Is the physical premium widening?"


def test_forget_removes_contact_calls_and_intros(nbox):
    a = _contact(name="A")
    b = _contact(name="B", introduced_by=a["id"])
    _call(a["id"])
    network.new_call(
        {"date": "2026-09-02", "with": [a["id"], b["id"]], "initiator": "me", "medium": "in-person",
         "mnpi_attestation": "none received"})
    out = network.forget(a["id"])
    assert out["calls_deleted"] == 1 and out["calls_edited"] == 1
    left = network.load_contacts()
    assert [x["id"] for x in left] == [b["id"]] and "introduced_by" not in left[0]
    assert network.load_calls()[0]["with"] == [b["id"]]


def test_compliance_log_has_roles_not_content(nbox):
    c = _contact()
    _call(c["id"])
    log = network.compliance_log("2026-09-01", "2026-09-30")
    assert log[0]["counterparties"] == ["crude trader at Acme Trading"] and log[0]["mnpi_attestation"] == "none received"
    assert "Ana" not in json.dumps(log)


def test_public_pack_chart_calls_score_and_check(nbox):
    pack = network.public_pack("BZ=F", "2026-06-30", slug="2026-06-brent")
    assert pack["series"] == "DCOILBRENTEU" and pack["last_date"] <= "2026-06-30" and pack["chg_12m_pct"] > 0
    assert (nbox / "public" / "2026-06-brent.png").exists()
    with pytest.raises(SystemExit, match="public"):
        network.public_pack("GC=F", "2026-06-30")                     # Yahoo data never goes in a public post
    _, errs = network.add_public_call({"issue": 1, "date": "2026-06-30", "market": "BZ=F", "direction": "up",
                                       "deadline": "2026-06-01", "claim": "x"})
    assert any("invalidation" in e for e in errs) and any("after the post" in e for e in errs)
    rec, errs = network.add_public_call({"issue": 1, "date": "2026-06-30", "market": "BZ=F", "direction": "up",
                                         "deadline": "2026-08-31", "probability": 0.6, "claim": "Brent higher by end-August",
                                         "invalidation": "close below 90"})
    assert rec["id"] == "pub-1-1" and rec["series"] == "DCOILBRENTEU"
    assert network.score_public("2026-07-15")["open"] == 1                 # not due yet: no look-ahead
    sc = network.score_public("2026-10-01")
    assert sc["resolved"] == 1 and sc["hits"] == 1 and sc["mean_brier"] == pytest.approx(0.16)
    c = _contact()
    post = nbox / "post.md"
    post.write_text("# Commodity note #2\n\nBrent is up. Ana Example agrees.\n", encoding="utf-8")
    chk = network.check_post(post)
    assert any("disclaimer" in p for p in chk["problems"]) and any("contact" in p for p in chk["problems"])
    assert any("scorecard" in p for p in chk["problems"])
    post.write_text("# Commodity note #2\n\nBrent is up. Scorecard: #1 call hit.\n\n"
                    + network.cfg()["public"]["disclaimer"] + "\n", encoding="utf-8")
    assert network.check_post(post)["problems"] == []
