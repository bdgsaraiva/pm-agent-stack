"""Research digester (agent 10): transcripts, quote anchoring, number and hedge checks, the call ledger with
no look-ahead, the index and the critic hook (offline, synthetic prices, no network)."""
from __future__ import annotations

import json
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from pmstack import critic, digest, journal, runlog, store


def _prices(ref: str, start: str, end: str, p0: float, step: float) -> pd.DataFrame:
    days = pd.bdate_range(start, end)
    vals = p0 + step * np.arange(len(days))
    return pd.DataFrame({"source": "prices", "series_id": ref, "name": ref, "date": days.date, "value": vals,
                         "unit": "usd", "freq": "D", "source_url": f"https://finance.yahoo.com/quote/{ref}",
                         "fetched_at": pd.Timestamp("2026-10-15")})


@pytest.fixture()
def dbox(tmp_path, monkeypatch):
    """Fresh store with two synthetic series (reset per test), notes and transcripts in tmp."""
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    monkeypatch.setattr(runlog, "LOG", tmp_path / "logs" / "runs.jsonl")
    monkeypatch.setattr(digest, "NOTES", tmp_path / "notes")
    monkeypatch.setattr(digest, "TRANSCRIPTS", tmp_path / "data" / "transcripts")
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal")
    # Brent rises 0.1 a business day from 100; copper falls 0.01 a day from 5
    store.upsert_obs("prices", pd.concat([_prices("BZ=F", "2026-01-01", "2026-12-31", 100.0, 0.1),
                                          _prices("HG=F", "2026-01-01", "2026-12-31", 5.0, -0.01)]))
    return tmp_path


TRANSCRIPT = """[00:01:00] Welcome to the show.
[00:05:10] I think Brent could trade to one hundred and ten dollars by the end of the year if Hormuz stays tense.
[00:12:00] Copper is at 4.85 today and we probably see it lower next quarter.
[00:18:30] Gold will make new highs, I am very confident.
[00:25:00] Thanks for listening.
"""


def _note(box, day="2026-03-02", series="Test Pod", name="ep"):
    d = box / "notes" / "podcasts" / "test-pod"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{day}-{name}.md"
    p.write_text(f"---\ntype: podcast\nseries: {series}\nepisode: {name}\ndate: {day}\nguests: [Guest]\n"
                 'assets: [BZ=F]\nquestions: ["What breaks the Brent call?"]\n---\n\n## Key messages\n- x\n', encoding="utf-8")
    t = box / "t.txt"
    t.write_text(TRANSCRIPT, encoding="utf-8")
    return p, t


def _brent(**kw):
    k = {"speaker": "Guest", "t": "00:05:10",
         "quote": "Brent could trade to one hundred and ten dollars by the end of the year if Hormuz stays tense",
         "claim": "Brent could reach 110 by year-end if Hormuz stays tense.", "type": "forecast", "markets": ["BZ=F"],
         "direction": "up", "level": 110, "deadline": "2026-12-31", "hedge": ["I think", "could", "if"], "horizon": "tactical"}
    # "I think" sits just before the quote in the transcript: a card that starts after it keeps it in `hedge`
    # (hedge_cut, own test set 16 Oct)
    k.update(kw)
    return k


# ------------------------------------------------------------------ numbers and quotes
def test_numbers_in_digits_words_and_formats():
    n = digest.numbers_in("one hundred and ten dollars, oitenta e cinco, dois virgula cinco, 1,234.5 and 1.234,5 and 80,5")
    assert {110.0, 85.0, 2.5, 1234.5, 80.5} <= n
    assert 1500.0 in digest.numbers_in("1.500") and 1.5 in digest.numbers_in("1.500")
    # structure is not a figure: quarters, ordinals, ISO dates, market names with digits
    assert digest.numbers_in("Q4 and 3rd and 2026-12-31 and the S&P 500", words=False) == set()


def test_quote_found_exact_fuzzy_and_missing(dbox):
    _, t = _note(dbox)
    tr = digest.load_transcript(t)
    assert tr["kind"] == "time"
    hit = digest.find_quote("Brent could trade to one hundred and ten dollars", tr, 310)
    assert hit["found"] and hit["ratio"] == 1.0 and hit["loc"] == 310
    near = digest.find_quote("brent could trade to one hundred ten dollars by the end of year", tr, None)
    assert near["found"] and near["ratio"] < 1.0                       # caption-style small differences
    assert not digest.find_quote("brent could trade to 150 by spring", tr, 310)["found"]


def test_card_checks_catch_numbers_names_hedges_and_markets(dbox):
    p, t = _note(dbox)
    tr = digest.load_transcript(t)
    ok = digest.check_card(_brent(), tr, "2026-03-02", "2026-03-10")
    assert ok["status"] == "ok" and ok["probability"] == 0.4 and "inference" in ok["prob_source"]   # "could" -> 0.4
    bad = digest.check_card(_brent(claim="Brent could reach 120 by year-end if Goldman is right."), tr, "2026-03-02", "2026-03-10")
    codes = {x["code"] for x in bad["problems"]}
    assert {"number_not_in_quote", "extrinsic_term"} <= codes and bad["status"] == "flagged"
    hedge = digest.check_card(_brent(claim="Brent reaches 110 by year-end.", hedge=[]), tr, "2026-03-02", "2026-03-10")
    assert any(x["code"] == "hedge_dropped" for x in hedge["problems"])
    unk = digest.check_card(_brent(markets=["BRENT"]), tr, "2026-03-02", "2026-03-10")
    assert any(x["code"] == "unknown_market" for x in unk["problems"])
    late = digest.check_card(_brent(deadline="2026-02-01"), tr, "2026-03-02", "2026-03-10")
    assert any(x["code"] == "bad_deadline" for x in late["problems"]) and late["status"] == "flagged"
    gone = digest.check_card(_brent(quote="Brent to two hundred by spring"), tr, "2026-03-02", "2026-03-10")
    assert gone["status"] == "rejected"


def test_location_corrected_and_data_level_checked(dbox):
    p, t = _note(dbox)
    tr = digest.load_transcript(t)
    k = digest.check_card(_brent(t="00:20:00"), tr, "2026-03-02", "2026-03-10")
    assert k["t"] == "00:05:10" and any(x["code"] == "location_off" for x in k["problems"]) and k["status"] == "ok"
    d = digest.check_card({"speaker": "Guest", "t": "00:12:00", "quote": "Copper is at 4.85 today",
                           "claim": "Copper is at 4.85.", "type": "data", "markets": ["HG=F"], "level": 4.85},
                          tr, "2026-03-02", "2026-03-10")
    # synthetic copper is ~4.57 on 2 Mar: 4.85 is 6% away -> shown for checking, not blocking
    assert d["stored"]["date"] <= "2026-03-02" and d["stored"]["diff_pct"] > 5
    assert any(x["code"] == "level_differs" for x in d["problems"]) and d["status"] == "ok"


def test_hedge_lexicon_most_hedged_wins():
    assert digest.hedge_prob("it will likely rise")[0] == 0.7
    assert digest.hedge_prob("vai subir")[0] == 0.8
    assert digest.hedge_prob("no qualifier here") == (None, None)


# ------------------------------------------------------------------ save, ledger, no look-ahead
def test_save_writes_cards_and_header_and_logs(dbox):
    p, t = _note(dbox)
    rep = digest.save(p, [_brent(), _brent(quote="nothing like this was said at all")], t, today="2026-03-10")
    assert rep["counts"] == {"ok": 1, "flagged": 0, "rejected": 1}
    cards = json.loads(p.with_suffix(".cards.json").read_text(encoding="utf-8"))
    assert cards["cards"][0]["id"].endswith("#c1") and cards["cards"][0]["name"] == "Brent"
    meta = digest.read_note(p)
    assert meta["digest"]["ok"] == 1 and meta["questions"] == ["What breaks the Brent call?"]
    assert len(digest.load_cards()) == 1 and digest.load_cards("2026-03-01") == []     # recorded 2 Mar: not before
    log = [json.loads(x) for x in (dbox / "logs" / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert log[-1]["step"] == "digest:save"


def test_future_note_date_is_refused(dbox):
    p, t = _note(dbox, day="2026-03-20")
    with pytest.raises(SystemExit):
        digest.check(p, [_brent()], t, today="2026-03-10")


def test_resolve_direction_level_touch_and_no_lookahead(dbox):
    base = {"type": "forecast", "scoreable": True, "speaker": "G", "price_ref": "BZ=F", "markets": ["BZ=F"],
            "as_of": "2026-03-02", "deadline": "2026-06-30"}
    up = digest.resolve({**base, "direction": "up"}, "2026-10-01")
    assert up["status"] == "hit" and up["move_pct"] > 0
    down = digest.resolve({**base, "direction": "down", "probability": 0.8}, "2026-10-01")
    assert down["status"] == "miss" and down["brier"] == pytest.approx(0.64)
    # start ~104.3 on 2 Mar, ~112.9 on 30 Jun: level 112 at the close is a hit and beats no-change
    lv = digest.resolve({**base, "level": 112}, "2026-10-01")
    assert lv["status"] == "hit" and lv["beat_no_change"] is True
    far = digest.resolve({**base, "level": 200}, "2026-10-01")
    assert far["status"] == "miss" and far["beat_no_change"] is False
    touch = digest.resolve({**base, "level": 110, "level_kind": "touch"}, "2026-10-01")
    assert touch["status"] == "hit"
    # as of a date before the deadline the call is open, even though later prices exist in the store
    early = digest.resolve({**base, "direction": "down"}, "2026-04-15")
    assert early["status"] == "open" and early["last_date"] <= "2026-04-15"
    assert digest.resolve({**base, "scoreable": False}, "2026-10-01")["status"] == "unscoreable"


def test_calls_and_speaker_records(dbox, monkeypatch):
    p, t = _note(dbox)
    digest.save(p, [_brent(deadline="2026-04-30", level=None, direction="up",
                           claim="Brent could rise by year-end if Hormuz stays tense.")], t, today="2026-03-10")
    out = digest.calls("2026-05-03")
    assert out["counts"]["hit"] == 1 and out["resolved_recently"][0]["card"].endswith("#c1")
    rec = out["records"]["guest"]
    assert rec["resolved"] == 1 and rec["wilson_pct"][0] < 100 and rec["enough"] is False
    monkeypatch.setattr(digest, "cfg", lambda: {**yaml_cfg(), "record_min_calls": 1})
    assert digest.calls("2026-05-03")["records"]["guest"]["enough"] is True
    assert digest.calls("2026-04-20")["due_soon"] == [] and digest.calls("2026-04-25")["due_soon"]


def yaml_cfg():
    import yaml
    return yaml.safe_load((digest.ROOT / "config" / "digest.yaml").read_text(encoding="utf-8"))


def test_index_and_previous(dbox):
    p1, t = _note(dbox, day="2026-03-02", name="ep1")
    digest.save(p1, [_brent()], t, today="2026-04-10")
    p2, _ = _note(dbox, day="2026-04-01", name="ep2")
    digest.save(p2, [_brent(direction="down", level=None, claim="Brent could fall by year-end if Hormuz stays tense.")], t,
                today="2026-04-10")
    txt = digest.index()
    lines = [l for l in txt.splitlines() if l.startswith("| 2026")]
    assert lines[0].startswith("| 2026-04-01") and "BZ=F" in lines[0] and "1 / 1" in lines[0]
    prev = digest.previous(p2)
    assert len(prev) == 1 and prev[0]["as_of"] == "2026-03-02"


# ------------------------------------------------------------------ critic hook
def test_market_view_and_critic_counter_without_lookahead(dbox):
    p1, t = _note(dbox, day="2026-03-02", name="ep1")
    p2, _ = _note(dbox, day="2026-03-05", name="ep2")
    down = _brent(direction="down", level=None, claim="Brent could fall by year-end if Hormuz stays tense.")
    digest.save(p1, [down], t, today="2026-04-10")
    digest.save(p2, [{**down, "speaker": "Second Guest"}], t, today="2026-04-10")
    v = digest.market_view("BZ=F", "2026-03-10", "long")
    assert v["speakers_against"] == 2
    assert v["n_against"] == 2 and v["n_with"] == 0 and v["latest_against"]["as_of"] == "2026-03-05"
    assert digest.market_view("BZ=F", "2026-03-01", "long") is None          # nothing recorded yet on 1 Mar
    e = {"id": "x", "market": "Brent", "price_ref": "BZ=F", "direction": "long", "conviction": 3,
         "created_utc": "2026-03-10T12:00:00+00:00", "status": "open", "entry_price": 106, "target": 115,
         "invalidation_price": 100, "horizon_days": 30, "source": "own", "_body": "## Thesis\nx\n"}
    cd = critic.card(e, entries=[], asof="2026-03-10", briefs=dbox / "briefs")
    assert cd["facts"]["notes.n_against"]["value"] == 2 and "notes.latest_against" in cd["facts"]
    assert any(x["basis"] == "notes" for x in cd["contradictions"])
    early = critic.card(e, entries=[], asof="2026-03-03", briefs=dbox / "briefs")
    assert early["facts"]["notes.n_against"]["value"] == 1
    assert not any(x["basis"] == "notes" for x in early["contradictions"])  # one card is not enough


def test_facts_moves_since_recording(dbox):
    p, t = _note(dbox)
    digest.save(p, [_brent()], t, today="2026-03-10")
    f = digest.facts(p, "2026-04-01")
    m = f["markets"][0]
    assert m["price_ref"] == "BZ=F" and m["recording_close_date"] <= "2026-03-02" and m["last_date"] <= "2026-04-01"
    assert m["since_recording_pct"] > 0 and m["to_levels"][0]["level"] == 110


# ------------------------------------------------------------------ capture (no network)
def test_fetch_local_vtt_and_text(dbox):
    vtt = dbox / "ep.vtt"
    vtt.write_text("WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nHello <b>there</b>\n\n00:01:05.500 --> 00:01:09.000\n"
                   "Brent at eighty\n", encoding="utf-8")
    meta = digest.fetch(str(vtt))
    assert meta["kind"] == "time" and meta["lines"] == 2 and meta["sha12"]
    tr = digest.load_transcript(meta["path"])
    assert tr["lines"][1] == (65.0, "Brent at eighty") and not tr["asr"]
    assert digest.load_transcript(meta["sha12"])["sha12"] == meta["sha12"]       # by sha too


def test_fetch_youtube_marks_auto_captions(dbox, monkeypatch):
    monkeypatch.setattr(digest, "_youtube_lines", lambda vid, langs: ([(1.0, "ola"), (70.0, "petroleo")],
                                                                      {"language": "pt", "asr": True}))
    meta = digest.fetch("https://www.youtube.com/watch?v=vQAQYzpWXZw")
    assert meta["asr"] and meta["source"] == "youtube-captions" and meta["language"] == "pt"
    assert digest.youtube_id("https://youtu.be/vQAQYzpWXZw") == "vQAQYzpWXZw"


def test_journal_source_ref_guards(dbox):
    e = {"book": "paper", "status": "idea", "direction": "long", "source": "podcast", "source_ref": "notes/podcasts/nope.md",
         "created_utc": "2026-10-01T12:00:00+00:00"}
    assert any(f["rule"] == "source-ref" for f in journal.checks(e, others=[]))
    e2 = {**e, "source": "call", "source_ref": "call with John at Acme"}
    assert any("no contact names" in f["text"] for f in journal.checks(e2, others=[]))
    e3 = {**e, "source": "call", "source_ref": "call:2026-10-15-01"}
    assert not any(f["rule"] == "source-ref" for f in journal.checks(e3, others=[]))


def test_audit_skips_yaml_header_keeps_it_first_and_treats_timestamps_as_structure(dbox, monkeypatch):
    from pmstack import audit
    monkeypatch.setattr(audit, "BRIEFS", dbox / "briefs")
    p, t = _note(dbox)
    digest.save(p, [_brent()], t, today="2026-03-10")
    text = p.read_text(encoding="utf-8") + "\nBrent could reach 110 [c1, 00:05:10]. A made-up 987.6 figure.\n"
    p.write_text(text, encoding="utf-8")
    rep = audit.audit_file(p, "2026-03-10", [str(p.with_suffix(".cards.json"))], flag=True)
    figs = {f["text"]: f["status"] for f in rep["figures"]}
    assert figs.get("110") == "matched" and figs.get("987.6") == "orphan"
    assert not any(f["line"] <= 12 for f in rep["figures"] if f["status"] != "structural")   # header not audited
    out = p.read_text(encoding="utf-8")
    assert out.startswith("---\n") and "**Number audit" in out.split("---\n", 2)[2]          # banner after the header
    assert digest.read_note(p)["digest"]["ok"] == 1



# ------------------------------------------------------------------ independent review (A11) regressions
ALT = """[00:01:00] If the cartel holds, Brent could get to eighty five dollars by the end of the year.
[00:02:00] Copper will not fall below four dollars this quarter.
"""


def _alt(dbox):
    t = dbox / "alt.txt"
    t.write_text(ALT, encoding="utf-8")
    return digest.load_transcript(t)


def test_altered_quote_number_hedge_or_negation_is_blocked(dbox):
    tr = _alt(dbox)
    base = {"speaker": "G", "t": "00:01:00", "type": "forecast", "markets": ["BZ=F"], "direction": "up",
            "deadline": "2026-12-31", "hedge": ["if", "could"]}
    ok = digest.check_card({**base, "level": 85, "quote": "If the cartel holds, Brent could get to eighty five dollars "
                            "by the end of the year", "claim": "Brent could reach 85 by year-end if the cartel holds."},
                           tr, "2026-03-02")
    assert ok["status"] == "ok" and ok["probability"] == 0.4
    changed = digest.check_card({**base, "level": 86, "hedge": ["if"], "quote": "If the cartel holds, Brent will get to "
                                 "eighty six dollars by the end of the year", "claim": "Brent will reach 86 by year-end if the cartel holds."},
                                tr, "2026-03-02")
    alt = [x for x in changed["problems"] if x["code"] == "quote_altered"]
    assert alt and all(f"'{w}'" in alt[0]["detail"] for w in ("could", "will", "five", "six"))
    assert changed["status"] == "flagged"
    rewritten = digest.check_card({**base, "level": 150, "hedge": [], "quote": "the cartel holds, Brent will get to one "
                                   "hundred fifty dollars by the end of the year", "claim": "Brent will reach 150 by year-end."},
                                  tr, "2026-03-02")
    assert rewritten["status"] != "ok"
    neg = digest.check_card({"speaker": "G", "t": "00:02:00", "type": "forecast", "markets": ["HG=F"], "direction": "down",
                             "deadline": "2026-06-30", "quote": "Copper will fall below four dollars this quarter",
                             "claim": "Copper will fall below 4 this quarter."}, tr, "2026-03-02")
    assert any("not" in x["detail"] for x in neg["problems"] if x["code"] == "quote_altered")


def test_number_reading_bypasses_closed(dbox):
    tr = _alt(dbox)
    base = {"speaker": "G", "t": "00:01:00", "type": "forecast", "markets": ["BZ=F"], "direction": "up", "deadline": "2026-12-31",
            "hedge": ["if", "could"], "quote": "If the cartel holds, Brent could get to eighty five dollars by the end of the year"}
    glued = digest.check_card({**base, "claim": "Brent could reach USD150 if the cartel holds."}, tr, "2026-03-02")
    assert any("150" in x["detail"] for x in glued["problems"] if x["code"] == "number_not_in_quote")
    prefix = digest.check_card({**base, "level": 80, "claim": "Brent could reach 80 if the cartel holds."}, tr, "2026-03-02")
    assert any(x["code"] == "number_not_in_quote" for x in prefix["problems"])          # "eighty five" is not 80
    prob = digest.check_card({**base, "probability": 0.85, "prob_source": "inferred",
                              "claim": "Brent could reach 85 if the cartel holds."}, tr, "2026-03-02")
    assert prob["prob_source"] == "stated" and any(x["code"] == "prob_not_in_quote" for x in prob["problems"])
    assert digest.numbers_in("1.500", lang="pt") == {1500.0} and digest.numbers_in("1.5", words=False, lang="en") == {1.5}
    assert digest.numbers_in("rates at 12y highs", words=False) == {12.0}


def test_claim_initial_names_and_translation_flag_from_source(dbox):
    tr = _alt(dbox)
    k = digest.check_card({"speaker": "G", "t": "00:01:00", "type": "opinion", "translated": True,
                           "quote": "If the cartel holds, Brent could get to eighty five dollars",
                           "claim": "Citi: Brent could reach 85 if the cartel holds."}, tr, "2026-03-02")
    assert any(x["code"] == "extrinsic_term" and "Citi" in x["detail"] for x in k["problems"])   # blocking: English source
    assert digest.hedge_prob("Oil will not go above 100 by May")[0] == 0.8                        # May is a month


def test_stale_prices_never_score_a_call(dbox):
    store.upsert_obs("fred", _prices("DCOILWTICO", "2026-01-01", "2026-10-06", 70.0, 0.1).assign(source="fred"))
    k = {"type": "forecast", "scoreable": True, "speaker": "G", "price_ref": "DCOILWTICO", "markets": ["CL=F"],
         "as_of": "2026-09-01", "direction": "up"}
    assert digest.resolve({**k, "deadline": "2026-10-30"}, "2026-11-02")["status"] == "pending-data"
    assert digest.resolve({**k, "deadline": "2026-10-09"}, "2026-10-09")["status"] == "open"          # deadline day
    assert digest.resolve({**k, "deadline": "2026-10-09"}, "2026-10-10")["status"] == "hit"           # 6 Oct is within 7 days
    flat = digest.resolve({**k, "direction": "flat", "level": 200, "deadline": "2026-09-15"}, "2026-10-01")
    assert flat["status"] == "hit"                                                                    # flat ignores the level side


def test_published_after_idea_is_not_on_its_card(dbox):
    p, t = _note(dbox, day="2026-03-02")
    txt = p.read_text(encoding="utf-8").replace("date: 2026-03-02\n", "date: 2026-03-02\npublished: 2026-03-20\n")
    p.write_text(txt, encoding="utf-8")
    digest.save(p, [_brent(direction="down", level=None, claim="Brent could fall by year-end if Hormuz stays tense.")], t,
                today="2026-04-10")
    assert digest.market_view("BZ=F", "2026-03-10", "long") is None
    assert digest.market_view("BZ=F", "2026-03-25", "long")["n_against"] == 1


def test_index_skips_malformed_notes(dbox):
    p, t = _note(dbox)
    digest.save(p, [_brent()], t, today="2026-03-10")
    bad = p.parent / "2026-03-03-bad.md"
    bad.write_text("---\ntype: podcast\nguests: [a, b\n---\n", encoding="utf-8")
    assert "BZ=F" in digest.index()
