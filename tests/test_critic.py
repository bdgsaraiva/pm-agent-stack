"""Critic (agent 5) and number auditor: card, slots, silence, validation, answers, Fridays, stats, audit (offline)."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pytest

from pmstack import audit, critic, journal, monitor
from test_journal import jbox  # noqa: F401  (fixture: fake data fetched into a temp store)

T0 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def _idea(**kw):
    args = dict(market="Brent", direction="long", conviction=3, thesis="Draws continue into Q4.",
                price_ref="BZ=F", target=None, invalidation_price=None, size_planned=1.0, horizon_days=20, now=T0)
    args.update(kw)
    if args["target"] is None or args["invalidation_price"] is None:
        px = journal._last_price(args["price_ref"])[0]
        args["entry_price"] = args.get("entry_price") or px
        args["target"] = args["target"] or round(args["entry_price"] * 1.05, 2)
        args["invalidation_price"] = args["invalidation_price"] or round(args["entry_price"] * 0.96, 2)
    return journal.new(**args)


def test_new_idea_gets_card_with_base_rate_and_premortem(jbox):
    e, _ = _idea()
    cr = journal.get(e["id"])["critic"]
    assert cr["silent"] is False and cr["slots"][0]["slot"] == "premortem"
    card = cr["card"]
    assert card["base.n_starts"] > 250
    assert card["base.target_first_pct"] + card["base.stop_first_pct"] + card["base.neither_pct"] == pytest.approx(100, abs=0.2)
    assert card["prob.before_pct"] == 50.0           # conviction-3 prior from the sizing config


def test_small_low_conviction_idea_is_card_only(jbox):
    e, _ = _idea(conviction=2, size_planned=0.5)
    cr = journal.get(e["id"])["critic"]
    assert cr["silent"] and cr["slots"] == [] and cr["tier"] == "card-only"


def test_overconfident_prob_triggers_counter_and_tier(jbox):
    e, _ = _idea(prob_win=0.9)
    cr = journal.get(e["id"])["critic"]
    counter = [s for s in cr["slots"] if s["slot"] == "counter"]
    assert counter and counter[0]["basis"] == "base-rate"
    assert cr["tier"] == "before-sizing"
    assert len(cr["slots"]) <= 3


def test_rules_from_data_and_text():
    e = {"direction": "short", "source": "news", "catalysts": None,
         "_body": "\n## Thesis\nPrices should fall: a new era of supply.\n\n## What breaks it\n"}
    t = {"against_trend": True, "trend_pct": 12.0}
    found = {r["rule"]: r for r in critic.rules(e, t, None, None)}
    assert {"zweig-1", "zweig-5", "zweig-9", "zweig-17", "zweig-15", "zweig-16"} <= set(found)
    assert found["zweig-1"]["kind"] == "data" and found["zweig-9"]["kind"] == "text"
    assert critic.rules(e, t, None, None)[0]["rule"] == "zweig-1"      # data outranks text


def test_save_validates_slots_facts_and_figures(jbox):
    e, _ = _idea(prob_win=0.9)
    cr = journal.get(e["id"])["critic"]
    stop = cr["card"]["base.stop_first_pct"]
    _, errs = critic.save(e["id"], [{"slot": "rule", "text": "Why?", "facts": ["entry.source"]}] if
                          not any(s["slot"] == "rule" for s in cr["slots"]) else [{"slot": "bogus", "text": "x"}])
    assert errs and "not planned" in errs[0]
    _, errs = critic.save(e["id"], [{"slot": "premortem", "text": "It lost 1R by 99.9% odds. Why?", "facts": ["entry.horizon_date"]}])
    assert any("not on the card" in x for x in errs)
    good = [{"slot": "premortem", "facts": ["entry.horizon_date", "base.stop_first_pct"],
             "text": f"It is {cr['card']['entry.horizon_date']} and this lost 1R; random entries hit your stop first "
                     f"{stop}% of the time. What happened? Name one reason that is a thesis error."}]
    e2, errs = critic.save(e["id"], good)
    assert not errs and e2["critic"]["questions"][0]["status"] == "open"
    _, errs = critic.save(e["id"], good)
    assert any("frozen" in x for x in errs)


def test_answer_logs_critic_event_and_stats(jbox):
    e, _ = _idea()
    cr = journal.get(e["id"])["critic"]
    critic.save(e["id"], [{"slot": "premortem", "facts": ["entry.horizon_date"],
                           "text": f"It is {cr['card']['entry.horizon_date']}; this lost 1R. Most likely why?"}])
    critic.answer(e["id"], "q1", "Inventories built; my read of the curve was wrong.", thesis_error=True,
                  reaction="useful", premise="valid", changed="size", prob_after=0.45)
    e2 = journal.get(e["id"])
    assert e2["events"][-1]["reason"] == "critic"
    s = critic.stats()
    assert s["questions"] == 1 and s["changed_decision"] == 1 and s["critic_events"] == 1
    assert s["prob_shift_pp_mean"] == pytest.approx(-5.0)
    with pytest.raises(SystemExit):
        critic.withdraw(e["id"], "q1", "  ")         # sycophancy guard: only a new fact withdraws a question


def test_reference_class_needs_six_analogues(jbox):
    for i in range(6):
        x, _ = _idea(now=T0 - timedelta(days=40 + i))
        journal.close(x["id"], r=(1.0 if i % 2 else -1.0), process=3, now=T0 - timedelta(days=35 + i))
    e, _ = _idea(prob_win=0.9)
    ref = critic.reference_class(journal.get(e["id"]), journal.load_all())
    assert ref["n"] == 6 and ref["enough"] and ref["hit_rate_pct"] == 50.0
    cr = journal.get(e["id"])["critic"]
    assert any(s["basis"] == "reference-class" for s in cr["slots"])


def test_repeat_question_on_same_market_is_suppressed(jbox):
    a, _ = _idea(prob_win=0.9, now=T0 - timedelta(days=5))
    critic.save(a["id"], [{"slot": "counter", "facts": ["base.win_pct"], "text": "What do you see that random entries don't?"}])
    critic.answer(a["id"], "q1", "Physical tightness.", now=T0 - timedelta(days=4))
    b, _ = _idea(prob_win=0.9)
    assert not any(s["slot"] == "counter" for s in journal.get(b["id"])["critic"]["slots"])


def test_weekly_is_silent_unless_something_changed(jbox):
    quiet, _ = _idea(entry_price=None, horizon_days=60)
    px = journal._last_price("BZ=F")[0]
    hit, _ = _idea(market="Brent short", direction="short", entry_price=px * 0.9, target=px * 0.8,
                   invalidation_price=px * 0.95, horizon_days=60)
    out = critic.weekly(asof="2026-10-01", now=T0)
    rows = {r["id"]: r for r in out["ideas"]}
    assert "invalidated" in rows[hit["id"]]["reasons"] and not rows[hit["id"]]["silent"]
    assert out["summary"]["open"] == 2


# ------------------------------------------------------------------ number auditor
def _pack(jbox):
    monitor.build(asof=date(2026, 10, 1))
    facts = json.loads((jbox / "briefs" / "2026-10-01" / "facts.json").read_text(encoding="utf-8"))
    brent = next(r for r in facts["sections"]["prices"] if r["id"] == "BZ=F")
    return facts, brent


def test_audit_matches_flags_orphans_dates_and_refs(jbox):
    facts, brent = _pack(jbox)
    a1 = next(a for a in facts["alerts"] if a.get("id") == "BZ=F")       # the Brent alert, whatever its rank
    note = (f"# Morning note — Thursday 1 Oct 2026\n\n"
            f"- Brent front month {brent['ret1_pct']:+.1f}% to {brent['last']:.2f} over 5 days. [{a1['ref']}]\n"
            f"- Brent 999.99 on 2026-09-17, 10y yields, Zweig #3, CFTC 15:30 ET. [alerts:2026-10-01#99]\n")
    p = jbox / "briefs" / "2026-10-01" / "note.md"
    p.write_text(note, encoding="utf-8")
    rep = audit.audit_file(p, flag=True)
    st = {f["text"]: f["status"] for f in rep["figures"]}
    assert st[f"{brent['last']:.2f}"] == "matched"
    assert st["999.99"] == "orphan"
    assert all(f["status"] in ("structural", "trivial") for f in rep["figures"] if f["text"] in ("10y", "3", "15", "30", "1", "5"))
    assert any(d["date"] == "2026-09-17" and d["status"] == "orphan" for d in rep["dates"])
    assert any(r["ref"] == "alerts:2026-10-01#99" and r["status"] == "missing" for r in rep["refs"])
    text = p.read_text(encoding="utf-8")
    assert "**Number audit" in text and "999.99" in text.split("\n")[2]
    p.write_text(text.replace("Brent 999.99", f"Brent {brent['last']:.2f}").replace("2026-09-17", "2026-10-01")
                 .replace("#99", f"#{a1['rank']}"), encoding="utf-8")
    rep2 = audit.audit_file(p, flag=True)
    assert rep2["summary"]["orphan"] == 0 and "**Number audit" not in p.read_text(encoding="utf-8")


def test_audit_catches_ref_pointing_at_another_market(jbox):
    facts, _ = _pack(jbox)
    a1 = facts["alerts"][0]
    p = jbox / "briefs" / "2026-10-01" / "note.md"
    p.write_text(f"# Note\n\n- Cocoa melted. [{a1['ref']}]\n", encoding="utf-8")
    rep = audit.audit_file(p)
    assert rep["refs"][0]["status"] == "mismatch"


# ------------------------------------------------------------------ regressions from the independent review
def test_audit_sign_units_and_calendar_words(jbox):
    facts, brent = _pack(jbox)
    p = jbox / "briefs" / "2026-10-01" / "note.md"
    r1, z1 = brent["ret1_pct"], brent["z1"]
    flip = -r1
    p.write_text(f"# Note\n\n- Brent front month {flip:+.1f}% today.\n"                    # wrong sign
                 f"- Brent front month {z1:+.1f}% ({r1:+.1f} sd).\n"                        # % and sd swapped
                 f"- Brent declined 12% and decreased 15% in early trade.\n"                 # month-like words
                 f"- Brent at US${brent['last']:,.2f}.\n", encoding="utf-8")
    rep = audit.audit_text(p.read_text(encoding="utf-8"), audit.pool_for("2026-10-01", with_journal=False))
    st = [(f["text"], f["status"]) for f in rep["figures"]]
    assert (f"{flip:+.1f}%", "orphan") in st or (f"{flip:+.1f}%", "unbound") in st     # flagged either way
    if abs(round(z1, 1)) != abs(round(r1, 1)):
        assert (f"{r1:+.1f} sd", "orphan") in st      # the % move can't vouch for a z-score
    assert not any(t in ("12%", "15%") and s_ == "structural" for t, s_ in st)   # "declined", "decreased" aren't months
    assert any(s == "matched" and t.startswith("US$") for t, s in st)


def test_save_refuses_after_answers_and_binds_to_cited_facts(jbox):
    e, _ = _idea()
    card = journal.get(e["id"])["critic"]["card"]
    q = [{"slot": "premortem", "facts": ["entry.horizon_date"],
          "text": f"It is {card['entry.horizon_date']}; this lost 1R. Random entries hit the stop first {card['base.stop_first_pct']}% of the time. What happened?"}]
    _, errs = critic.save(e["id"], q)                 # cites horizon only, quotes a base-rate figure
    assert any("not on the card" in x for x in errs)
    q[0]["facts"] = ["entry.horizon_date", "base.stop_first_pct"]
    assert critic.save(e["id"], q)[1] == []
    critic.answer(e["id"], "q1", "Spread collapsed.")
    assert any("frozen" in x for x in critic.save(e["id"], q)[1])
    assert journal.get(e["id"])["critic"]["questions"][0]["answer"] == "Spread collapsed."


def test_card_figure_passes_when_the_market_name_gives_the_binder_no_word(jbox):
    # 20 Oct 2026 regression: market "US 10y rates" ("US" too short, "10y" starts with a digit) left the binder only
    # "rates", so 106.50 cited from entry.invalidation came back "unbound" and was refused as not on the card
    e, _ = _idea(market="US 10y rates", price_ref="ZN=F", direction="short", entry_price=105.2656, target=104,
                 invalidation_price=106.5, conviction=3, size_planned=1.0, prob_win=0.9)
    cr = journal.get(e["id"])["critic"]
    assert cr["card"]["entry.invalidation"] == 106.5
    for fig in ("106.50", "106.5"):
        q = [{"slot": cr["slots"][0]["slot"], "facts": ["entry.invalidation"],
              "text": f"If 10y futures trade through {fig} before the event, what was wrong in the thesis?"}]
        out, errs = critic.validate_questions(journal.get(e["id"]), q)
        assert not errs, errs
    q[0]["text"] = "If 10y futures trade through 107.25 before the event, what was wrong in the thesis?"
    assert any("not on the card: 107.25" in x for x in critic.validate_questions(journal.get(e["id"]), q)[1])


def test_source_only_analogues_do_not_make_a_reference_class(jbox):
    for i, (m, ref) in enumerate([("Gold", "GC=F"), ("S&P", "ES=F"), ("Corn", "ZC=F"), ("Copper", "HG=F"),
                                  ("10y", "ZN=F"), ("Euro", "EURUSD=X")]):
        x, _ = _idea(market=m, price_ref=ref, direction="short", entry_price=100, target=90, invalidation_price=105,
                     now=T0 - timedelta(days=40 + i))
        journal.close(x["id"], r=-1.0, process=3, now=T0 - timedelta(days=35 + i))
    e, _ = _idea()
    ref = critic.reference_class(journal.get(e["id"]), journal.load_all())
    assert ref["n"] == 0 and not ref["enough"]


def test_trend_counter_and_trend_rule_are_not_both_asked():
    e = {"id": "x", "status": "open", "conviction": 4, "size_planned": 1.0, "market": "Brent", "direction": "short",
         "catalysts": "OPEC meeting"}
    cd = {"facts": {"entry.horizon_date": {"value": "2026-11-01"}}, "gap_pp": None,
          "contradictions": [{"basis": "trend", "severity": 3, "facts": ["tape.trend_pct"]}],
          "rules": [{"rule": "zweig-1", "name": "trend", "why": "fades", "kind": "data", "facts": ["tape.trend_pct"], "severity": 3}]}
    slots = critic.plan(e, cd, entries=[])["slots"]
    assert [s["slot"] for s in slots] == ["premortem", "counter"]
