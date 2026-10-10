"""Offline end-to-end test: fake HTTP responses shaped like each real API,
then fetch -> store -> monitor -> fact pack. Run: python -m pytest -q"""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from pmstack import fetch, monitor, runlog, store
from pmstack.adapters import base

ASOF = date(2026, 10, 2)
NOW = datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc)
rng = np.random.default_rng(7)


def _weeks(start="2018-01-05", end="2026-09-26"):
    return pd.date_range(start, end, freq="W-FRI")


def eia_payload(url):
    d = _weeks()
    base_lvl = 430_000 + 15_000 * np.sin(2 * np.pi * d.isocalendar().week.to_numpy() / 52)
    lvl = base_lvl + rng.normal(0, 1500, len(d)).cumsum() * 0.2
    lvl[-1] = lvl[-2] - 12_000                       # a big draw in the last week -> surprise alert
    return {"response": {"data": [{"period": x.strftime("%Y-%m-%d"), "value": f"{v:.0f}"}
                                  for x, v in zip(d[::-1], lvl[::-1])]}}


def cftc_payload(params):
    d = pd.date_range("2020-01-07", "2026-09-29", freq="W-TUE")
    rows = []
    for code in ["067651", "023651", "111659", "022651", "088691", "085692", "005602", "002602", "080732", "083731"]:
        net = rng.normal(0, 1, len(d)).cumsum() * 3000
        if code == "083731":
            net[-1] = net.max() + 20_000             # coffee at a 3-year extreme -> positioning alert
        for x, n in zip(d, net):
            oi = 300_000
            rows.append({"report_date_as_yyyy_mm_dd": x.strftime("%Y-%m-%dT00:00:00.000"),
                         "cftc_contract_market_code": code, "open_interest_all": str(oi),
                         "m_money_positions_long_all": str(int(80_000 + max(n, 0))),
                         "m_money_positions_short_all": str(int(80_000 + max(-n, 0))),
                         "prod_merc_positions_long": "50000", "prod_merc_positions_short": "90000"})
    return rows


def fred_csv(sid):
    if sid.startswith("P"):        # IMF monthly
        d = pd.date_range("2018-01-01", "2026-08-01", freq="MS")
    else:
        d = pd.bdate_range("2018-01-02", "2026-10-01")
    v = 80 * np.exp(rng.normal(0, 0.01, len(d)).cumsum())
    lines = [f"observation_date,{sid}"] + [f"{x:%Y-%m-%d},{y:.2f}" for x, y in zip(d, v)]
    lines[5] = lines[5].split(",")[0] + ",."    # FRED's missing-value marker
    return "\n".join(lines)


def yahoo_payload(ticker):
    d = pd.bdate_range("2023-01-02", "2026-10-02" if ticker in ("^N225", "^HSI", "000300.SS", "^KS11", "^AXJO") else "2026-10-01")
    v = 100 * np.exp(rng.normal(0, 0.012, len(d)).cumsum())
    if ticker == "BZ=F":
        v[-1] = v[-2] * 1.06                          # a 6% Brent jump -> price alert
    ts = [int(pd.Timestamp(x).tz_localize("UTC").timestamp()) + 4 * 3600 for x in d]
    return {"chart": {"result": [{"meta": {"gmtoffset": -14400}, "timestamp": ts,
                                  "indicators": {"quote": [{"close": [float(x) for x in v]}]}}]}}


RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Federal Reserve issues FOMC statement</title><link>https://www.federalreserve.gov/newsevents/pressreleases/monetary20261001a.htm</link>
<pubDate>Thu, 01 Oct 2026 18:00:00 GMT</pubDate><description>The Committee decided to maintain the target range...</description></item>
<item><title>Agencies announce enforcement action</title><link>https://www.federalreserve.gov/x</link>
<pubDate>Thu, 01 Oct 2026 20:00:00 GMT</pubDate><description>Termination of enforcement action</description></item>
<item><title>Old item</title><link>https://www.federalreserve.gov/old</link><pubDate>Mon, 01 Sep 2026 20:00:00 GMT</pubDate></item>
</channel></rss>"""


def sgs_payload(sid):
    if sid == 432:
        return [{"data": "18/06/2026", "valor": "14.75"}, {"data": "17/09/2026", "valor": "15.25"}]
    if sid == 433:
        return [{"data": "01/07/2026", "valor": "0.30"}, {"data": "01/08/2026", "valor": "0.21"}]
    d = pd.bdate_range("2022-01-03", "2026-10-01")
    return [{"data": f"{x:%d/%m/%Y}", "valor": f"{5.2 + 0.001 * i:.4f}"} for i, x in enumerate(d)]


def focus_payload(url):
    ind = "IPCA" if "IPCA" in url else "Selic" if "Selic" in url else "Câmbio"
    out = []
    for i, dt in enumerate(pd.date_range("2026-06-05", "2026-10-02", freq="W-FRI")):
        for ref in ("2026", "2027"):
            base_v = {"IPCA": 4.8, "Selic": 15.0, "Câmbio": 5.5}[ind]
            bump = 0.25 if (ind == "IPCA" and ref == "2026" and dt == pd.Timestamp("2026-10-02")) else 0
            out.append({"Indicador": ind, "Data": f"{dt:%Y-%m-%d}", "DataReferencia": ref, "Mediana": base_v + bump})
    return {"value": out}


def fake_get_json(url, params=None, **kw):
    if "api.eia.gov" in url:
        return eia_payload(url)
    if "publicreporting.cftc.gov" in url:
        return cftc_payload(params)
    if "query1.finance.yahoo.com" in url:
        return yahoo_payload(url.split("/chart/")[1])
    if "bcdata.sgs" in url:
        return sgs_payload(int(url.split("sgs.")[1].split("/")[0]))
    if "olinda.bcb.gov.br" in url:
        return focus_payload(url)
    if "copomcomunicados" in url:
        return {"conteudo": [{"titulo": "Copom mantém a taxa Selic em 15,25% a.a.", "dataReferencia": "2026-10-01T21:30:00Z",
                              "link": "/detalhenoticia/123/nota"}]}
    raise AssertionError(f"unexpected json url {url}")


def fake_get_text(url, params=None, **kw):
    if "fredgraph.csv" in url:
        return fred_csv(params["id"])
    if url.endswith((".xml", "press.html", "news")):
        return RSS
    raise AssertionError(f"unexpected text url {url}")


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA", tmp_path / "data")
    monkeypatch.setattr(runlog, "LOG", tmp_path / "logs" / "runs.jsonl")
    monkeypatch.setattr(monitor, "BRIEFS", tmp_path / "briefs")
    from pmstack import journal
    monkeypatch.setattr(journal, "JOURNAL", tmp_path / "journal")
    monkeypatch.setattr(base, "get_json", fake_get_json)
    monkeypatch.setattr(base, "get_text", fake_get_text)
    monkeypatch.setenv("EIA_API_KEY", "test")
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    return tmp_path


def test_end_to_end(sandbox):
    res = fetch.run(backfill=True)
    assert {r["step"] for r in res} == {f"fetch:{k}" for k in ["eia", "cftc", "fred", "prices", "cbtext"]}
    assert all(r["status"] == "ok" for r in res), res

    # every stored row is traceable
    con = store.connect()
    bad = con.execute("SELECT count(*) FROM obs WHERE source_url IS NULL OR fetched_at IS NULL").fetchone()[0]
    assert bad == 0
    assert con.execute("SELECT count(DISTINCT series_id) FROM obs").fetchone()[0] > 50

    facts = monitor.build(asof=ASOF, now=NOW)
    kinds = {a["kind"] for a in facts["alerts"]}
    assert {"eia_surprise", "positioning_extreme", "price_move", "policy_text"} <= kinds, kinds
    # every alert links to a source
    assert all(a["source_url"].startswith("http") for a in facts["alerts"])
    # the enforcement-action item is listed but not alerted; the old item is outside the window
    titles = [r["title"] for r in facts["sections"]["cbtext"]]
    assert "Old item" not in titles
    assert not any("enforcement" in a["text"] for a in facts["alerts"])

    md = (sandbox / "briefs" / str(ASOF) / "facts.md").read_text()
    for h in ["## Alerts (ranked)", "## Overnight: Asia session closes", "## US petroleum inventories (EIA weekly)",
              "## Positioning (CFTC, managed money)", "## US rates, credit and macro", "## US equities", "## USD", "## Read-through inputs", "## Data health"]:
        assert h in md, h
    assert "nan" not in md.lower().replace("financ", "")


def test_incremental_fetch_dedupes(sandbox):
    fetch.run(backfill=True)
    n1 = store.connect().execute("SELECT count(*) FROM obs").fetchone()[0]
    fetch.run()                       # second run overlaps the last weeks; must not duplicate
    n2 = store.connect().execute("SELECT count(*) FROM obs").fetchone()[0]
    assert n2 == n1


def test_one_failing_source_does_not_stop_others(sandbox, monkeypatch):
    def broken(url, params=None, **kw):
        if "api.eia.gov" in url:
            raise RuntimeError("HTTP 503")
        return fake_get_json(url, params=params)
    monkeypatch.setattr(base, "get_json", broken)
    res = {r["step"]: r["status"] for r in fetch.run(backfill=True)}
    assert res["fetch:eia"] == "error" and res["fetch:cftc"] == "ok"
    facts = monitor.build(asof=ASOF, now=NOW)
    md = (sandbox / "briefs" / str(ASOF) / "facts.md").read_text()
    assert "fetch:eia — error" in md


def test_eia_surprise_math(sandbox):
    fetch.run(only=["eia"], backfill=True)
    facts = monitor.build(asof=ASOF, now=NOW)
    r = next(x for x in facts["sections"]["eia"] if x["id"] == "PET.WCESTUS1.W")
    assert r["change"] == pytest.approx(-12_000, abs=1)
    assert r["n_seasonal_obs"] >= 12          # 5 years x 3 neighbouring weeks
    assert r["surprise_z"] < -1.5


def test_live_bar_is_not_treated_as_a_close(sandbox, monkeypatch):
    # Morning run: 05:40 BRT = 08:40 UTC on 1 Oct, futures still trading
    monkeypatch.setattr(base, "now_utc", lambda: datetime(2026, 10, 1, 8, 40, tzinfo=timezone.utc))
    fetch.run(only=["prices"], backfill=True)
    facts = monitor.build(asof=date(2026, 10, 1), now=NOW)   # futures bar dated 1 Oct is still trading
    brent = next(r for r in facts["sections"]["prices"] if r["id"] == "BZ=F")
    assert brent["date"] == "2026-09-30" and brent["live_pct"] == pytest.approx(6.0, abs=0.01)
    assert any(a["kind"] == "overnight_move" and a["id"] == "BZ=F" for a in facts["alerts"])
    nikkei = next(r for r in facts["sections"]["prices"] if r["id"] == "^N225")
    assert nikkei["date"] == "2026-10-01" and nikkei["live"] is None     # Asia close is final


def test_keywords_match_whole_words_only(sandbox, monkeypatch):
    rss = RSS.replace("Agencies announce enforcement action", "Updated data release calendar")
    monkeypatch.setattr(base, "get_text", lambda url, params=None, **kw: rss if not "fredgraph" in url else fred_csv(params["id"]))
    fetch.run(only=["cbtext"], backfill=True)
    facts = monitor.build(asof=ASOF, now=NOW)
    cal = [r for r in facts["sections"]["cbtext"] if "calendar" in r["title"].lower()]
    assert cal and all(r["keywords"] == [] for r in cal)        # "data" must not match "ata"


def test_evening_fetch_treats_todays_bar_as_final(sandbox, monkeypatch):
    # Evening run: 20:55 BRT, after futures (18:00) and cash (17:00) closes
    monkeypatch.setattr(base, "now_utc", lambda: datetime(2026, 10, 1, 23, 55, tzinfo=timezone.utc))
    fetch.run(only=["prices"], backfill=True)
    facts = monitor.build(asof=date(2026, 10, 1), now=datetime(2026, 10, 1, 23, 56, tzinfo=timezone.utc))
    brent = next(r for r in facts["sections"]["prices"] if r["id"] == "BZ=F")
    assert brent["date"] == "2026-10-01" and brent["live"] is None
    assert brent["ret1_pct"] == pytest.approx(6.0, abs=0.01)
