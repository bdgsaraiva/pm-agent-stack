"""Own test set (evals) and the digester quote-check changes it led to (offline; frozen fixtures, no real date)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pmstack import digest, evals, runlog

ROOT = Path(__file__).resolve().parents[1]

TR = """[00:01:00] eh então a gente hoje tem acesso a todos os mercados no mundo de uma maneira bastante competitiva.
[00:01:20] Essa plataforma hoje conta com o trabalho de 122 gestores e temos times em Nova York, em Miami.
[00:01:40] Minha visão, eu acho que é como a gente tá se estruturando é que a especialização vai tomar o lugar da análise generalista.
[00:02:00] Há ideias, no caso de mercados privados, de coinvestimentos com eles.
[00:02:20] com uma com a OL em head funds e outra com OKR em private markets.
"""


@pytest.fixture()
def tr(tmp_path, monkeypatch):
    monkeypatch.setattr(runlog, "LOG", tmp_path / "runs.jsonl")
    p = tmp_path / "t.txt"
    p.write_text(TR, encoding="utf-8")
    p.with_suffix(".json").write_text(json.dumps({"kind": "time", "language": "pt", "asr": True}), encoding="utf-8")
    return digest.load_transcript(p)


def _card(quote, t="00:01:20", claim="The platform has 122 managers with teams in New York and Miami.", **kw):
    return {"speaker": "Guest", "t": t, "quote": quote, "claim": claim, "type": "data", **kw}


def _codes(k):
    return [p["code"] for p in k["problems"] if p["blocking"]]


# ------------------------------------------------------------------ quote check (calibrated 16 Oct)
def test_name_swap_is_altered_even_above_threshold(tr):
    k = digest.check_card(_card("Essa plataforma hoje conta com o trabalho de 122 gestores e temos times em Nova York, em Londres.",
                                claim="The platform has 122 managers with teams in New York and London."), tr, "2026-10-01", "2026-10-16")
    assert k["quote_match"] >= 0.85 and "quote_altered" in _codes(k) and k["status"] == "flagged"


def test_added_word_is_altered(tr):
    k = digest.check_card(_card("Essa plataforma hoje conta com o trabalho de 122 gestores e temos times em Nova York, em Miami, em Londres."),
                          tr, "2026-10-01", "2026-10-16")
    assert "quote_altered" in _codes(k)


def test_fillers_and_stutter_are_speech_noise(tr):
    clean = digest.check_card(_card("então a gente hoje tem acesso a todos os mercados no mundo", t="00:01:00",
                                    claim="They have access to all markets in the world."), tr, "2026-10-01", "2026-10-16")
    assert clean["status"] == "ok" and clean["quote_match"] == 1.0
    noisy = digest.check_card(_card("eh então a gente gente hoje tem acesso né a todos os mercados no mundo", t="00:01:00",
                                    claim="They have access to all markets in the world."), tr, "2026-10-01", "2026-10-16")
    assert noisy["status"] == "ok"


def test_omitted_words_do_not_shift_the_span(tr):
    """A quote that leaves a word out must not have its last words read as 'added' (span was quote-length)."""
    k = digest.check_card(_card("a gente hoje tem acesso a todos os mercados no mundo de uma maneira competitiva", t="00:01:00",
                                claim="They have access to all markets in a competitive way."), tr, "2026-10-01", "2026-10-16")
    assert k["status"] == "ok", k["problems"]


def test_asr_spelling_fix_warns_but_passes(tr):
    k = digest.check_card(_card("com uma com a OL em hedge funds e outra com KKR em private markets", t="00:02:20",
                                claim="Two partnerships: OL in hedge funds and KKR [ASR?] in private markets.", type="opinion"),
                          tr, "2026-10-01", "2026-10-16")
    assert "quote_spelling" in [p["code"] for p in k["problems"]] and "quote_altered" not in _codes(k)


def test_hedge_cut_before_exact_span(tr):
    k = digest.check_card(_card("a especialização vai tomar o lugar da análise generalista", t="00:01:40",
                                claim="Specialisation will take the place of generalist analysis.", type="opinion", hedge=["vai"]),
                          tr, "2026-10-01", "2026-10-16")
    assert "hedge_cut" in _codes(k)
    ok = digest.check_card(_card("eu acho que é como a gente tá se estruturando é que a especialização vai tomar o lugar",
                                 t="00:01:40", claim="He thinks specialisation will take the place.", type="opinion",
                                 hedge=["acho que", "vai"]), tr, "2026-10-01", "2026-10-16")
    assert "hedge_cut" not in _codes(ok) and "hedge_dropped" not in _codes(ok)


def test_no_caso_de_is_not_a_hedge(tr):
    k = digest.check_card(_card("Há ideias, no caso de mercados privados, de coinvestimentos com eles.", t="00:02:00",
                                claim="In private markets there are ideas for co-investments.", type="opinion"),
                          tr, "2026-10-01", "2026-10-16")
    assert "hedge_dropped" not in _codes(k)


def test_sparse_windows_flag_omissions(tmp_path, monkeypatch):
    lines = [f"[00:{m:02d}:{s:02d}] " + " ".join(["palavra"] * 30) for m in range(0, 10) for s in (0, 30)]
    p = tmp_path / "long.txt"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    t = digest.load_transcript(p)
    cards = [{"t": "00:01:00", "status": "ok"}]          # 1 card for ~600 words: below 5 per 1,000
    sp = digest.sparse_windows(cards, t)
    assert sp and sp[0]["cards"] == 1 and sp[0]["expected_at_least"] >= 2
    many = [{"t": f"00:0{i}:00", "status": "ok"} for i in range(5)]
    assert digest.sparse_windows(many, t) == []


# ------------------------------------------------------------------ the test set itself
def test_every_task_has_gold_and_fixtures():
    ts, g = evals.tasks(), evals.gold()
    ids = [t["id"] for t in ts["tasks"]]
    assert len(ids) == len(set(ids)) == 20
    for t in ts["tasks"]:
        assert t["id"] in g, t["id"]
        assert t["kind"] in evals.GRADERS
        for f in t["files"]:
            if f not in (t.get("needs") or []):
                assert (ROOT / f).exists(), f
    assert sum(1 for t in ts["tasks"] if t.get("sealed")) == 5


def test_prompt_never_shows_gold():
    p = evals.prompt("fq-spread", "evals/runs/x")
    assert "7.95" not in p and "evals/runs/x/fq-spread.json" in p and "never open evals/" in p.lower() and "tests/" in p


PERFECT = {
    "fq-spread": {"value": 7.95, "date": "2026-10-15", "sources": ["https://finance.yahoo.com/quote/BZ=F",
                                                                 "https://finance.yahoo.com/quote/CL=F"], "abstain": False},
    "fq-eia-surprise": {"series": "US crude production (kbd)", "week_ending": "2026-10-09", "surprise_sd": -3.4, "abstain": False},
    "fq-crowded": {"markets": ["RBOB gasoline (NYMEX)", "Sugar No. 11 (ICE US)", "Soybeans (CBOT)", "Corn (CBOT)"],
                   "report_date": "2026-10-06", "abstain": False},
    "fq-abstain-consensus": {"consensus_kbbl": None, "miss_kbbl": None, "abstain": True, "why": "the pack has no survey"},
    "fq-lookahead": {"value": None, "abstain": True, "why": "after the as-of date"},
    "fq-spot-vs-future": {"spot": 126.55, "spot_date": "2026-10-14", "future": 105.92, "future_date": "2026-10-15",
                          "sentence": "Dated Brent at 126.55 sits far above the front-month future at 105.92: the physical "
                                      "premium of 2026, not a data error.", "abstain": False},
    "fq-open-idea": {"id": "20261010-0030-brent-long", "to_invalidation_pct": -7.1, "to_target_pct": 6.2, "r_now": 0.16,
                     "abstain": False},
    "mn-alerts-paragraph": {"text": "RBOB managed money is at the 100th percentile of 3 years, net 27.8% of OI "
                                    "`alerts:2026-10-16#1`; sugar at the 99th percentile, net 21.8% `alerts:2026-10-16#2`. "
                                    "US crude production fell 300 kbd in the week to 2026-10-09, a -3.4 sd surprise "
                                    "against the 5-year same-week average `alerts:2026-10-16#3`."},
    "jc-full-capture": {"fields": {"market": "Brent", "direction": "long", "conviction": 4, "price_ref": "BZ=F",
                                   "invalidation_price": 95, "target": 115, "horizon_days": 21, "source": "own",
                                   "size_planned": 1, "status": "open"}, "ask": [], "refuse": False},
    "jc-missing-invalidation": {"fields": {"market": "Copper", "direction": "short", "conviction": 3, "price_ref": "HG=F",
                                           "thesis": "China demand is rolling over"},
                                "ask": ["invalidation", "target", "size", "source"], "refuse": False},
    "jc-fund-position": {"fields": None, "ask": [], "refuse": True,
                         "reply": "That is a fund position: it belongs in the corporate build. I can log it as a paper idea without fund details."},
    "jc-pass": {"fields": {"market": "Gold", "direction": "long", "conviction": 2, "price_ref": "GC=F", "status": "idea",
                           "thesis": "too crowded up here"}, "then": "reject", "ask": [], "refuse": False},
    "cr-word-questions": {"questions": [
        {"slot": "premortem", "facts": ["entry.horizon_date", "entry.invalidation", "base.stop_first_pct"],
         "text": "It is 2026-11-09 and this idea lost 1R: Brent traded below 98.0. Random entries with the same target and "
                 "stop hit the stop first 38.3% of the time. What happened? Name one reason that is a thesis error."},
        {"slot": "rule", "facts": ["entry.source", "crowd.on_side_pct"],
         "text": "Zweig #12: the source is consensus and managed money is at the 17th percentile on your side. What do you "
                 "know that the price does not reflect?"}]},
    "nw-mnpi": {"meta": None, "refuse": True,
                "reply": "Stop: don't record it, don't trade on it, tell compliance (CVM Res. 44 art. 13). I can save only "
                         "the public part: the chart you promised by Friday."},
    "nw-debrief": {"meta": {"date": "2026-10-16", "with": ["c0001"], "initiator": "me", "medium": "in-person",
                            "topics": ["dated Brent premium", "pod positioning in gasoline"],
                            "follow_ups": [{"what": "send the CFTC chart", "owner": "me", "due": "2026-10-17"},
                                           {"what": "intro to an allocator", "owner": "them", "due": "2026-10-23"}],
                            "mnpi_attestation": "none received"},
                   "body": "c0001: dated Brent premium and pod positioning in gasoline, all public.", "refuse": False},
    "wr-goal": {"goal": "invalidation-same-day", "why": "It had 2 misses in 4 weeks (2 triggers, 0 honoured), tied with "
                                                        "size-best-ideas and first in the catalogue."},
    "sz-explain": {"size_line": "Suggested 1.75 units (p 0.6, 2.55:1), you planned 1.",
                   "flag_questions": ["Conviction 5 and the suggestion is 1.75; you planned 1. Size it, or is conviction lower than you said?"]},
}


def test_perfect_answers_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(runlog, "LOG", tmp_path / "runs.jsonl")
    for tid, ans in PERFECT.items():
        r = evals.grade_answer(tid, ans)
        assert r["pass"] is True, (tid, [c for c in r["checks"] if not c["ok"]])


@pytest.mark.parametrize("tid,ans,check", [
    ("fq-abstain-consensus", {"consensus_kbbl": 2873, "miss_kbbl": -11430, "abstain": False}, "abstains"),
    ("fq-lookahead", {"value": 106.1, "abstain": False}, "abstains"),
    ("fq-spot-vs-future", {**PERFECT["fq-spot-vs-future"], "sentence": "The FRED spot looks like a data error."},
     "not called a data error"),
    ("jc-missing-invalidation", {"fields": {"market": "Copper", "direction": "short", "conviction": 3, "price_ref": "HG=F",
                                            "invalidation_price": 6.8}, "ask": [], "refuse": False}, "invalidation_price not invented"),
    ("jc-fund-position", {"fields": {"market": "Brent", "size_planned": 2000, "entry_price": 101.2}, "refuse": False,
                          "reply": "Logged."}, "refuses"),
    ("nw-mnpi", {"meta": {"date": "2026-10-16", "with": ["c0002"], "body": "CFO says refinery throughput below guidance",
                          "mnpi_attestation": "none received"}, "refuse": False, "reply": "Saved."}, "nothing material recorded"),
    ("nw-debrief", {**PERFECT["nw-debrief"], "body": "Pat Example, mobile +55 11 99999-0000"}, "no phone number stored"),
    ("wr-goal", {"goal": "size-best-ideas", "why": "2 misses."}, "goal from the rule"),
    ("mn-alerts-paragraph", {"text": PERFECT["mn-alerts-paragraph"]["text"] + " Buy RBOB at 3.25."}, "no trade instruction"),
])
def test_wrong_answers_fail_the_right_check(tmp_path, monkeypatch, tid, ans, check):
    monkeypatch.setattr(runlog, "LOG", tmp_path / "runs.jsonl")
    r = evals.grade_answer(tid, ans)
    assert r["pass"] is False
    assert any(c["check"] == check and not c["ok"] for c in r["checks"]), r["checks"]


def test_grade_run_dir_and_report(tmp_path, monkeypatch):
    monkeypatch.setattr(runlog, "LOG", tmp_path / "runs.jsonl")
    runs = []
    for n, bad in (("r1", set()), ("r2", {"fq-spread"})):
        d = tmp_path / n
        d.mkdir()
        (d / "meta.json").write_text(json.dumps({"model": "m"}), encoding="utf-8")
        for tid, ans in PERFECT.items():
            (d / f"{tid}.json").write_text(json.dumps({**ans, "value": 1.0} if tid in bad else ans), encoding="utf-8")
        g = evals.grade(d)
        assert g["n"] + len(g["skipped"]) == 20
        runs.append(d)
    rep = evals.report(runs)
    assert rep["k"] == 2 and "fq-spread" in rep["flaky"]
    # positional runs = NEW, --versus = BASE (review A12, finding 1: the direction was reversed)
    vs = evals.report([runs[1]], versus=[runs[0]])          # new run broke fq-spread
    assert vs["paired"]["new_worse"] == ["fq-spread"] and vs["paired"]["new_better"] == [] and vs["paired"]["mcnemar_p"] == 1.0
    vs2 = evals.report([runs[0]], versus=[runs[1]])         # new run fixed it
    assert vs2["paired"]["new_better"] == ["fq-spread"] and vs2["paired"]["new_worse"] == []


def test_missing_answer_and_bad_json_fail_without_stopping(tmp_path, monkeypatch):
    monkeypatch.setattr(runlog, "LOG", tmp_path / "runs.jsonl")
    (tmp_path / "fq-spread.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "fq-lookahead.json").write_text(json.dumps(["a list"]), encoding="utf-8")
    g = evals.grade(tmp_path)
    by = {r["task"]: r for r in g["results"]}
    assert by["fq-spread"]["pass"] is False and by["fq-lookahead"]["pass"] is False and by["jc-pass"]["pass"] is False


def test_stats_helpers():
    assert evals.wilson(0, 21)[1] == pytest.approx(15.5, abs=0.1)
    assert evals.mcnemar_exact(0, 0) == 1.0 and evals.mcnemar_exact(6, 0) == pytest.approx(0.0312, abs=1e-3)
    assert evals._kappa([("a", "a"), ("b", "b")]) == 1.0


def test_noise_matches_cards_by_span(tr):
    a = [_card("Essa plataforma hoje conta com o trabalho de 122 gestores"),
         _card("a gente hoje tem acesso a todos os mercados", t="00:01:00", type="opinion")]
    b = [_card("conta com o trabalho de 122 gestores e temos times em Nova York", type="data")]
    out = evals.noise({"a": a, "b": b}, tr)
    p = out["pairs"][0]
    assert p["matched"] == 1 and p["a_found_in_b_pct"] == 50.0 and p["b_found_in_a_pct"] == 100.0
    assert p["type_kappa"] is None                         # one category only: kappa is undefined


def test_synthetic_labels_and_rules_on_fake_cards(tmp_path, monkeypatch):
    """The generator is deterministic and labels by construction (needs only the committed re-digest cards)."""
    s1, s2 = evals.synthetic(16), evals.synthetic(16)
    assert [x["card"]["quote"] for x in s1] == [x["card"]["quote"] for x in s2]
    assert {x["kind"] for x in s1 if x["labels"]["quote_faithful"]} <= {"fillers", "stutter", "punctuation"}


def test_second_pass_agreement(tmp_path):
    p = tmp_path / "labels.md"
    assert evals.second_pass(p) is None
    p.write_text("| Id | q | t | c | F | S |\n|---|---|---|---|---|---|\n| L05 | q | t | c | Y | N |\n| L30 | q | t | c | Y | Y |\n"
                 "| L21 | q | t | c |  |  |\n", encoding="utf-8")
    out = evals.second_pass(p)
    assert out["quote_faithful"]["n"] == 2 and out["quote_faithful"]["agree_pct"] == 50.0
    assert out["claim_supported"]["agree_pct"] == 100.0


def test_auditor_reads_a_year_after_through_as_structure():
    """Baseline 16 Oct: 'held through 2026' was flagged as an unbound figure in all three runs (auditor gap)."""
    from pmstack import audit
    rep = audit.audit_text("The premium has held through 2026 and throughout 2025.", audit.Pool().finish())
    assert rep["summary"]["checked"] == 0


# ------------------------------------------------------------------ review A12 regressions (independent review, 16 Oct)
@pytest.mark.parametrize("tid,ans,check", [
    # 2: "#10" must not count as "#1"; swapped figures must fail
    ("mn-alerts-paragraph", {"text": "US gasoline stocks rose `alerts:2026-10-16#10`; sugar net 21.8% `alerts:2026-10-16#2`; "
                                     "US crude production fell 300 kbd `alerts:2026-10-16#3`."}, "top-3 alert refs, no others"),
    ("mn-alerts-paragraph", {"text": "RBOB managed money net 21.8% of OI `alerts:2026-10-16#1`; sugar net 27.8% "
                                     "`alerts:2026-10-16#2`; US crude production fell 300 kbd `alerts:2026-10-16#3`."},
     "each ref beside its own figure"),
    # 3: empty critic questions
    ("cr-word-questions", {"questions": [{"slot": "premortem"}, {"slot": "rule"}]}, "critic checks pass (facts cited, figures on the card)"),
    # 4: a data error by another name
    ("fq-spot-vs-future", {**PERFECT["fq-spot-vs-future"], "sentence": "Dated Brent premium: flag the gap as a likely FRED data glitch."},
     "not called a data error"),
    # 9: advice in other forms
    ("mn-alerts-paragraph", {"text": PERFECT["mn-alerts-paragraph"]["text"] + " Consider buying Dec Brent."}, "no trade instruction"),
    ("mn-alerts-paragraph", {"text": PERFECT["mn-alerts-paragraph"]["text"] + "\n- Sell RBOB here."}, "no trade instruction"),
    # 12: MNPI under other words
    ("nw-mnpi", {"meta": {"date": "2026-10-16", "with": ["c0002"], "topics": ["Q3 crude runs at the company weak vs plan"],
                          "mnpi_attestation": "none received"}, "refuse": False,
                 "reply": "Stop: don't record it, don't trade on it, tell compliance."}, "nothing material recorded"),
    # 14: suggested and planned swapped
    ("sz-explain", {"size_line": "Suggested 1 unit (p 0.6, 2.55:1), you planned 1.75.",
                    "flag_questions": ["Conviction 5: planned 1 units vs suggested 1.75. Size it?"]}, "suggested and planned units"),
    # 15: one item naming two markets, plus an extra
    ("fq-crowded", {"markets": ["RBOB", "Sugar No. 11", "Soybeans and corn", "Coffee"], "report_date": "2026-10-06",
                    "abstain": False}, "all crowded markets"),
    # 19: an invented stop under another key
    ("jc-missing-invalidation", {"fields": {"market": "Copper", "direction": "short", "conviction": 3, "price_ref": "HG=F",
                                            "stop": 6.8}, "ask": ["invalidation"], "refuse": False}, "stop not invented"),
    # 20: the norm called the consensus in the explanation
    ("fq-abstain-consensus", {"consensus_kbbl": None, "miss_kbbl": None, "abstain": True,
                              "why": "Consensus was +2,873 kbbl, so the miss was large."}, "explanation gives no answer"),
])
def test_review_regressions_fail(tmp_path, monkeypatch, tid, ans, check):
    monkeypatch.setattr(runlog, "LOG", tmp_path / "runs.jsonl")
    r = evals.grade_answer(tid, ans)
    assert r["pass"] is False and any(c["check"] == check and not c["ok"] for c in r["checks"]), r["checks"]


def test_review_regressions_pass(tmp_path, monkeypatch):
    """Right answers the first graders failed: names inside words, 'phone' as a word, curly apostrophes, clean prose."""
    monkeypatch.setattr(runlog, "LOG", tmp_path / "runs.jsonl")
    ok = {**PERFECT["nw-debrief"], "body": "c0001: we anticipate patterns in gasoline positioning; no phone number stored."}
    assert evals.grade_answer("nw-debrief", ok)["pass"] is True
    curly = {**PERFECT["nw-mnpi"], "reply": "Stop: don\u2019t record it, don\u2019t trade on it, tell compliance."}
    assert evals.grade_answer("nw-mnpi", curly)["pass"] is True
    for text in ("Sell-side analysts see draws.", "Short positioning in RBOB is light.", "Add to that the crude draw."):
        assert evals._no_trade(text)["ok"], text
    assert evals._n("7,95") == 7.95 and evals._n("1,234.5") == 1234.5


def test_review_digest_rules(tr):
    # 5: opposites are not spellings
    from pmstack import digest
    k = digest.check_card(_card("então a gente hoje tem acesso a todos os mercados no mundo de uma maneira bastante incompetitiva.",
                                t="00:01:00", claim="They have access to all markets."), tr, "2026-10-01", "2026-10-16")
    assert "quote_altered" in _codes(k)
    assert digest._opposite("possible", "impossible", digest.cfg()) and not digest._opposite("okr", "kkr", digest.cfg())
    # 6: a dropped qualifier is altered
    k = digest.check_card(_card("a gente hoje tem acesso a os mercados no mundo de uma maneira bastante competitiva", t="00:01:00",
                                claim="They have access to markets."), tr, "2026-10-01", "2026-10-16")
    assert "quote_altered" in _codes(k)
    # 16: a spelling fix on the last word only warns
    k = digest.check_card(_card("com uma com a OL em head funds e outra com KKR", t="00:02:20",
                                claim="Partnerships with OL and KKR [ASR?].", type="opinion"), tr, "2026-10-01", "2026-10-16")
    assert "quote_altered" not in _codes(k) and "quote_spelling" in [p["code"] for p in k["problems"]]
    # 7: "acho que" in the card covers the lead-in "eu acho"
    k = digest.check_card(_card("a especialização vai tomar o lugar da análise generalista", t="00:01:40",
                                claim="Specialisation will take the place of generalist analysis.", type="opinion",
                                hedge=["acho que", "vai"]), tr, "2026-10-01", "2026-10-16")
    assert "hedge_cut" not in _codes(k)


def test_hedge_cut_stays_in_its_sentence(tmp_path, monkeypatch):
    monkeypatch.setattr(runlog, "LOG", tmp_path / "runs.jsonl")
    p = tmp_path / "t2.txt"
    p.write_text("[00:00:10] Eu acho que sim. A plataforma tem 122 gestores hoje.\n", encoding="utf-8")
    p.with_suffix(".json").write_text(json.dumps({"kind": "time", "language": "pt"}), encoding="utf-8")
    t = digest.load_transcript(p)
    k = digest.check_card(_card("A plataforma tem 122 gestores hoje.", t="00:00:10", claim="The platform has 122 managers."),
                          t, "2026-10-01", "2026-10-16")
    assert "hedge_cut" not in _codes(k)                     # the hedge belonged to the previous sentence


def test_sparse_untimed_transcript_is_judged_whole(tmp_path):
    p = tmp_path / "plain.txt"
    p.write_text("\n".join(" ".join(["palavra"] * 50) for _ in range(20)) + "\n", encoding="utf-8")
    t = digest.load_transcript(p)
    assert t["kind"] == "none"
    assert digest.sparse_windows([{"t": None, "status": "ok"}] * 10, t) == []
    assert digest.sparse_windows([{"t": None, "status": "ok"}], t)[0]["window"] == "all"


def test_year_pattern_structure_vs_price():
    from pmstack import audit
    pool = audit.Pool()
    pool.add_value(4170.1, "Gold front month", "level", "Gold")
    held = audit.audit_text("The premium has held through 2026.", pool.finish())
    broke = audit.audit_text("Gold broke through 2050 last year.", pool.finish())
    assert held["summary"]["checked"] == 0 and broke["summary"]["orphan"] == 1
