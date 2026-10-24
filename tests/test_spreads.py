"""Relative-value spreads (24 Oct 2026): the LME adapter, spread maths, rv: marks, journal R and the agents reading a
relative idea like any other price (offline)."""
from __future__ import annotations

from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import pytest

from pmstack import journal, monitor, runlog, spreads, store
from pmstack.adapters import westmetall

T_ENTRY = datetime(2026, 10, 23, 22, 0, tzinfo=timezone.utc)      # 19:00 BRT on Friday 23 Oct

PAGE = """<html><body><table>
<tr><th>date</th><th>LME Copper Cash-Settlement</th><th>LME Copper 3-month</th><th>LME Copper stock</th></tr>
<tr><td>23. October 2026</td><td>10,512.50</td><td>10,580.00</td><td>135,775</td></tr>
<tr><td>22. October 2026</td><td>10,401.00</td><td>10,470.50</td><td>136,000</td></tr>
<tr><td>Average</td><td>9,999.00</td><td>9,999.00</td><td>1</td></tr>
</table></body></html>"""


def test_westmetall_parse_reads_headers_and_numbers():
    rows, errors = westmetall.parse(PAGE, "copper", "u", pd.Timestamp("2026-10-24"))
    assert not errors
    got = {(r["series_id"], str(r["date"])): r["value"] for r in rows}
    assert got[("lme:copper_cash", "2026-10-23")] == 10512.5
    assert got[("lme:copper_3m", "2026-10-22")] == 10470.5
    assert got[("lme:copper_stock", "2026-10-23")] == 135775
    assert len(rows) == 6                                           # the "Average" row is not a date


def test_westmetall_parse_reports_layout_change():
    rows, errors = westmetall.parse("<table><tr><td>nothing</td></tr></table>", "copper", "u", None)
    assert not rows and "no rows parsed" in errors[0]


def test_lme_prompt_weight_interpolates_between_cash_and_3m():
    assert spreads.lme_prompt_weight(date(2026, 10, 23), date(2026, 12, 16)) == pytest.approx(52 / 90)
    assert spreads.lme_prompt_weight(date(2026, 8, 1), date(2026, 12, 16)) is None     # beyond 3 months
    assert spreads.lme_prompt_weight(date(2026, 12, 15), date(2026, 12, 16)) is None   # inside T+2


def _obs(days=400, end="2026-10-23", seed=3):
    """Fake legs: generic COMEX and LME 3M for `days` business days; the Dec26 contract and LME cash only recently."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end=end, periods=days)
    lme3 = 10000 * np.exp(np.cumsum(rng.normal(0, 0.012, days)))
    prem = 1.0 + np.cumsum(rng.normal(0, 0.002, days))            # COMEX/LME ratio wanders around 1
    hg = lme3 * prem / 2204.62262                                  # USD/lb
    es = 6000 * np.exp(np.cumsum(rng.normal(0, 0.01, days)))      # two universe markets so the risk model runs
    gc = 3000 * np.exp(np.cumsum(rng.normal(0, 0.01, days)))
    rows = []
    for i, d in enumerate(idx):
        rows += [("prices", "HG=F", d, hg[i]), ("lme", "lme:copper_3m", d, lme3[i]),
                 ("prices", "ES=F", d, es[i]), ("prices", "GC=F", d, gc[i])]
        if d >= pd.Timestamp("2026-09-01"):
            rows += [("prices_rv", "HGZ26.CMX", d, hg[i] * 1.001), ("lme", "lme:copper_cash", d, lme3[i] * 0.995)]
    df = pd.DataFrame(rows, columns=["source", "series_id", "date", "value"])
    return df


def test_compute_chain_links_generic_history_to_the_exact_level():
    obs = _obs()
    s, first = spreads.compute(obs, spreads.get("cu_comex_lme_dec26"))
    assert first == date(2026, 9, 16)                 # first day the Dec26 prompt is within 3 months (and > T+2)
    d = pd.Timestamp("2026-10-23")
    w = obs[obs.date == d].set_index("series_id").value
    wt = spreads.lme_prompt_weight(d.date(), date(2026, 12, 16))
    lme_dec = w["lme:copper_cash"] + wt * (w["lme:copper_3m"] - w["lme:copper_cash"])
    assert s.loc[d] == pytest.approx(100 * w["HGZ26.CMX"] * 2204.62262 / lme_dec)
    # before the exact legs: generic returns, no level jump at the hand-over
    g = 100 * obs[obs.series_id == "HG=F"].set_index("date").value * 2204.62262 / obs[obs.series_id == "lme:copper_3m"].set_index("date").value
    before = s[s.index < pd.Timestamp(first)]
    assert np.log(before).diff().dropna().values == pytest.approx(np.log(g[g.index < pd.Timestamp(first)]).diff().dropna().values)
    assert len(s) == 400


def test_cents_are_converted():
    s = spreads._unit(pd.Series([4.8, 480.0]), {"factor": 2204.62262, "cents_if_above": 50})
    assert s.iloc[0] == pytest.approx(s.iloc[1])


@pytest.fixture()
def box(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    monkeypatch.setattr(runlog, "LOG", tmp_path / "logs" / "runs.jsonl")
    monkeypatch.setattr(monitor, "BRIEFS", tmp_path / "briefs")
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal")
    obs = _obs()
    obs["name"], obs["unit"], obs["freq"], obs["source_url"] = "x", "close", "daily", "u"
    obs["fetched_at"] = pd.Timestamp("2026-10-24")
    for src, part in obs.groupby("source"):
        store.upsert_obs(src, part)
    return tmp_path


def _idea(**kw):
    args = dict(market="Copper COMEX vs LME", direction=None, conviction=2,
                thesis="US should implement a tariff to keep copper in the US.", spread="cu_comex_lme_dec26",
                entry_price=0, invalidation_price=-2, target=5, prob_win=0.6, horizon_days=91, size_planned=0.5,
                breaks="No US tariff on copper imports.", now=T_ENTRY)
    args.update(kw)
    return journal.new(**args)


def test_relative_idea_is_captured_in_premium_and_marked_on_its_own_series(box):
    e, found = _idea()
    assert not [f for f in found if f["level"] == "block"]
    assert e["direction"] == "relative" and e["price_ref"] == f"rv:{e['id']}"
    assert (e["entry_price"], e["invalidation_price"], e["target"]) == (100.0, 98.0, 105.0)
    assert e["reward_risk"] == 2.5 and e["expected_r"] == pytest.approx(0.6 * 2.5 - 0.4)
    assert spreads.side(e) == "long" and spreads.describe(e)["invalidation_premium_pct"] == -2.0
    con = store.connect()
    rv = con.execute("SELECT date, value FROM obs WHERE series_id = ? ORDER BY date", [e["price_ref"]]).df()
    assert float(rv[pd.to_datetime(rv.date) == pd.Timestamp("2026-10-23")].value.iloc[0]) == pytest.approx(100.0)
    assert e["sizing"]["units"] is not None and e["sizing"]["stop_sd"] is not None


def test_relative_r_and_triggers(box):
    e, _ = _idea()
    assert journal.r_multiple(e, 101.0) == 0.5          # premium +1% on a 2% stop
    assert journal.r_multiple(e, 97.0) == -1.5
    assert journal.infer_trigger(e, 105.5) == "target"
    assert journal.infer_trigger(e, 97.9) == "invalidation"
    assert journal._wrong_side(e, "invalidation_price", 101.0)          # a stop above entry on a long spread
    x = journal.close(e["id"], exit_price=103.0, process=3, lesson="l", trigger="event", now=T_ENTRY)
    assert x["r_multiple"] == 1.5


def test_relative_idea_enters_the_risk_model_and_the_critic(box):
    from pmstack import critic, risk
    e, _ = _idea()
    obs = store.connect().execute("SELECT * FROM obs").df()
    obs["date"] = pd.to_datetime(obs["date"]).dt.date
    sec, _ = risk.build(obs, journal.load_all(), {}, {}, date(2026, 10, 23))
    assert [r["id"] for r in sec.get("ideas", [])] == [e["id"]], (sec.get("note"), sec.get("skipped"))
    card = journal.get(e["id"]).get("critic") or {}
    assert "error" not in card
    assert critic._dir(e) == 1


def test_spread_without_a_definition_needs_explicit_r():
    e = {"direction": "relative", "entry_price": 1, "invalidation_price": 0.5}
    assert spreads.side(e) is None and journal.r_multiple(e, 2) is None
