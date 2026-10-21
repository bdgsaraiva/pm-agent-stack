"""Market levels table for the morning note (pmstack/levels.py, config/levels.yaml) and the prices rows it reads
(pmstack/monitor.py prices()): one Yahoo snapshot, one change column vs the previous close, VIX in vol points,
yields in bp, row order, relevant rows by sd or alert, c / y level marks, 1-year vol, the most active contract,
and the JGB row as the marked exception."""
from datetime import date

import numpy as np
import pandas as pd
import yaml

from pmstack import levels, monitor
from pmstack.levels import ROOT

ASOF = date(2026, 10, 20)
SNAP = "2026-10-20 09:05"
PRICES = [{"id": "BZ=F", "name": "Brent", "last": 109.5, "date": "2026-10-19", "live": 108.2, "live_pct": -1.2,
           "live_chg": -1.2, "chg_unit": "%", "live_z": -1.6, "ret1_pct": 0.1, "chg1": 0.1, "z1": -0.9,
           "live_fetched_utc": SNAP, "fetched_utc": SNAP, "source_url": "https://x/bz"},
          {"id": "ES=F", "name": "S&P e-mini", "last": 7734.5, "date": "2026-10-19", "live": 7765.4, "live_pct": 0.4,
           "live_chg": 0.4, "chg_unit": "%", "live_z": 0.5, "ret1_pct": 0.4, "chg1": 0.4, "z1": 0.5,
           "live_fetched_utc": SNAP, "fetched_utc": SNAP, "source_url": "https://x/es"},
          {"id": "NG=F", "name": "Henry Hub", "last": 3.1, "date": "2026-10-19", "live": 3.09, "live_pct": -0.3,
           "live_chg": -0.3, "chg_unit": "%", "live_z": -0.3, "ret1_pct": -0.2, "chg1": -0.2, "z1": -0.2,
           "live_fetched_utc": SNAP, "fetched_utc": SNAP, "source_url": "https://x/ng"},
          {"id": "SI=F", "name": "Silver", "last": 50.0, "date": "2026-10-19", "live": 50.95, "live_pct": 1.9,
           "live_chg": 1.9, "chg_unit": "%", "live_z": 1.7, "ret1_pct": 0.4, "chg1": 0.4, "z1": 0.4,
           "live_fetched_utc": SNAP, "fetched_utc": SNAP, "source_url": "https://x/si"},
          {"id": "^VIX", "name": "VIX", "last": 18.4, "prev": 17.2, "date": "2026-10-19", "live": None, "ret1_pct": 7.0,
           "chg1": 1.2, "chg_unit": "pts", "z1": 1.1, "fetched_utc": SNAP, "source_url": "https://x/vix"},
          {"id": "^TNX", "name": "US 10y Treasury yield (Cboe)", "last": 5.117, "prev": 5.136, "date": "2026-10-19",
           "live": None, "ret1_pct": -0.37, "chg1": -1.9, "chg_unit": "bp", "z1": -0.4, "fetched_utc": SNAP,
           "source_url": "https://x/tnx"},
          {"id": "^N225", "name": "Nikkei 225", "last": 49000.0, "prev": 48500.0, "date": "2026-10-20", "live": None,
           "ret1_pct": 1.03, "chg1": 1.03, "chg_unit": "%", "z1": 0.8, "fetched_utc": "2026-10-20 06:00",
           "source_url": "https://x/n225"}]


def test_relevant_rows_alerts_and_no_roll_note():
    L = {"relevant_sd": 1.5,
         "groups": [{"name": "Energy", "rows": [{"id": "BZ=F", "show": "always"}, {"id": "NG=F", "show": "relevant"},
                                                 {"id": "KC=F", "show": "relevant"}]},
                    {"name": "Metals", "rows": [{"id": "SI=F", "show": "relevant"}]},
                    {"name": "Equities", "rows": [{"id": "ES=F", "show": "always"}]},
                    {"name": "Rates", "rows": [{"id": "JGB10Y", "source": "mof_jgb", "show": "relevant", "label": "JGB 10y"}]}]}
    sec, _ = levels.build(PRICES, [], pd.DataFrame(), [{"id": "NG=F"}], ASOF, C=L)
    shown = {r["id"]: r for g in sec["groups"] for r in g["rows"]}
    assert set(shown) == {"BZ=F", "NG=F", "SI=F", "ES=F"}               # Henry Hub by alert, silver by its 1.7 sd move
    assert shown["NG=F"]["shown_because"] == "alert" and shown["SI=F"]["shown_because"] == "move 1.7 sd"
    assert shown["ES=F"]["note"] is None                                 # active contracts replace the roll note (21 Oct)
    assert "JGB 10y" in sec["missing"] and "KC=F" in sec["missing"]
    assert "| Metals | Silver |" in "\n".join(levels.render(sec))


def test_one_snapshot_one_change_column_and_units():
    L = {"relevant_sd": 1.5, "groups": [{"name": "Equities", "rows": [
        {"id": "ES=F", "show": "always"}, {"id": "^VIX", "show": "always"}, {"id": "^N225", "show": "always"}]},
        {"name": "Rates", "rows": [{"id": "^TNX", "show": "always", "label": "US 10y yield"}]}]}
    sec, _ = levels.build(PRICES, [], pd.DataFrame(), [], ASOF, C=L)
    r = {x["id"]: x for g in sec["groups"] for x in g["rows"]}
    assert sec["snapshot_utc"] == SNAP and sec["snapshot_brt"] == "2026-10-20 06:05"
    # live market: level = live mark, change vs the 19 Oct close; closed market: its close and close-to-close change
    assert r["ES=F"]["mark"] == "live" and r["ES=F"]["level"] == 7765.4 and r["ES=F"]["change"] == 0.4
    assert r["^VIX"]["mark"] == "close" and r["^VIX"]["change"] == 1.2 and r["^VIX"]["change_unit"] == "pts"
    assert r["^TNX"]["change"] == -1.9 and r["^TNX"]["change_unit"] == "bp" and r["^TNX"]["source"] == "Yahoo Finance"
    assert "older fetch, 2026-10-20 06:00 UTC" in r["^N225"]["note"]     # fetched 3 hours before the snapshot
    md = "\n".join(levels.render(sec))
    assert "Yahoo Finance snapshot 2026-10-20 09:05 UTC (06:05 BRT)" in md
    head = next(line for line in md.splitlines() if line.startswith("| Group"))
    assert head == "| Group | Market | Level | Change | sd |"                 # no Mark, Shown because or Source (21 Oct)
    assert "| VIX | 18.40 y | +1.20 pts | +1.1 |" in md                   # the previous session's close: "y"
    assert "| US 10y yield | 5.12 y | -1.9 bp | -0.4 |" in md
    assert "| S&P e-mini | 7,765.40 | +0.40% | +0.5 |" in md                # live: no mark
    assert "49,000.00 c |" in md                                           # Asia closed today: "c"
    assert "Left out" not in md


def test_jgb_row_is_the_marked_exception():
    d = pd.bdate_range("2026-07-01", "2026-10-19")
    obs = pd.DataFrame({"source": "mof_jgb", "series_id": "JGB10Y", "date": d.date,
                        "value": 1.6 + 0.01 * np.sin(np.arange(len(d))), "source_url": "https://x/mof"})
    obs.loc[obs.index[-1], "value"] = obs.value.iloc[-2] + 0.08            # an 8 bp jump: a relevant move
    L = {"groups": [{"name": "Rates", "rows": [{"id": "JGB10Y", "source": "mof_jgb", "show": "relevant",
                                                "label": "JGB 10y yield"}]}]}
    sec, _ = levels.build(PRICES, [], obs, [], ASOF, C=L)
    r = sec["groups"][0]["rows"][0]
    assert r["source"] == "Japan MoF" and r["change_unit"] == "bp" and round(r["change"], 1) == 8.0
    assert r["note"] == "Japan MoF, close of 2026-10-19; not in the snapshot"


def test_config_order_and_yields_from_one_source():
    C = yaml.safe_load((ROOT / "config" / "levels.yaml").read_text(encoding="utf-8"))
    g = {x["name"]: x["rows"] for x in C["groups"]}
    eq = [r["id"] for r in g["Equities"]]
    assert eq[:5] == ["ES=F", "NQ=F", "RTY=F", "^STOXX50E", "^VIX"]
    assert eq[5:] == ["^N225", "^HSI", "000001.SS", "^KS11", "^AXJO"]           # then Asia
    assert all(r["show"] == "always" for r in g["Equities"][:5])
    rates = g["Rates"]
    assert not any(r.get("source") == "fred" for gr in C["groups"] for r in gr["rows"])
    us = [r["id"] for r in rates if r.get("source", "prices") == "prices"]
    assert us == ["^FVX", "^TNX", "ZN=F"]
    assert {r.get("source") for r in rates if r["id"] not in us} == {"mof_jgb", "oat"}
    assert "KC=F" not in {r["id"] for gr in C["groups"] for r in gr["rows"]}           # coffee left out
    src = yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))["prices"]["tickers"]
    t = {x["id"]: x for x in src}
    assert t["^STOXX50E"]["group"] == "europe" and t["^VIX"]["unit"] == "points"
    assert t["^TNX"]["unit"] == "bp" and t["^FVX"]["unit"] == "bp"
    ids = {r["id"] for gr in C["groups"] for r in gr["rows"] if r.get("source", "prices") == "prices"}
    assert ids <= set(t)                                                              # every prices row is fetched


def test_monitor_prices_units_and_fetch_time(monkeypatch):
    d = pd.bdate_range("2026-06-01", "2026-10-20")
    n = len(d)
    rng = np.random.default_rng(3)
    vix = 17 + rng.normal(0, 0.5, n).cumsum() * 0.2
    tnx = 4.9 + rng.normal(0, 0.03, n).cumsum()
    stx = 6000 * np.exp(rng.normal(0, 0.008, n).cumsum())
    rows = []
    for sid, v in (("^VIX", vix), ("^TNX", tnx), ("^STOXX50E", stx)):
        rows += [{"source": "prices", "series_id": sid, "date": x.date(), "value": y, "source_url": f"https://x/{sid}",
                  "fetched_at": pd.Timestamp("2026-10-20 09:05")} for x, y in zip(d, v)]
    obs = pd.DataFrame(rows)
    ticks = [{"id": "^VIX", "name": "VIX", "group": "us_equity", "unit": "points"},
             {"id": "^TNX", "name": "US 10y", "group": "us_yields", "unit": "bp"},
             {"id": "^STOXX50E", "name": "Euro Stoxx 50", "group": "europe"}]
    monkeypatch.setattr(monitor, "_src", lambda: {"prices": {"tickers": ticks}})
    out, _ = monitor.prices(obs, {"vol_window": 60, "move_z": 9.0}, ASOF)
    r = {x["id"]: x for x in out}
    # 09:05 UTC = 06:05 BRT: every bar dated 20 Oct is still trading (US cash before 17:00, Europe before 14:00 BRT)
    assert abs(r["^VIX"]["live"] - vix[-1]) < 1e-9 and abs(r["^VIX"]["last"] - vix[-2]) < 1e-9
    assert abs(r["^VIX"]["live_chg"] - (vix[-1] - vix[-2])) < 1e-9 and r["^VIX"]["chg_unit"] == "pts"
    assert abs(r["^TNX"]["live_chg"] - 100 * (tnx[-1] - tnx[-2])) < 1e-9 and r["^TNX"]["chg_unit"] == "bp"
    assert abs(r["^TNX"]["chg1"] - 100 * (tnx[-2] - tnx[-3])) < 1e-9 and abs(r["^TNX"]["prev"] - tnx[-3]) < 1e-9
    sd = np.std(np.diff(tnx[:-1])[-61:-1] * 100, ddof=1)
    assert abs(r["^TNX"]["live_z"] - 100 * (tnx[-1] - tnx[-2]) / sd) < 1e-9          # bp change over bp vol
    assert r["^STOXX50E"]["live"] is not None and r["^STOXX50E"]["chg_unit"] == "%"
    assert r["^STOXX50E"]["fetched_utc"] == "2026-10-20 09:05"


def test_sd_uses_one_year_vol_of_the_continuous_series_and_active_contract_label():
    d = pd.bdate_range("2025-06-01", "2026-10-19")
    rng = np.random.default_rng(5)
    cl = 70 * np.exp(rng.normal(0, 0.02, len(d)).cumsum())
    obs = pd.DataFrame({"source": "prices", "series_id": "CL=F", "date": d.date, "value": cl, "source_url": "u"})
    px = [{"id": "CL.A", "name": "WTI", "last": 99.0, "date": "2026-10-19", "live": 100.0, "live_pct": 1.0101,
           "live_chg": 1.0101, "chg_unit": "%", "live_z": 9.0, "live_fetched_utc": SNAP, "fetched_utc": SNAP,
           "source_url": "https://finance.yahoo.com/quote/CLZ26.NYM"}]
    L = {"vol_days": 250, "groups": [{"name": "Energy", "rows": [{"id": "CL.A", "vol_from": "CL=F", "show": "always"}]}]}
    sec, _ = levels.build(px, [], obs, [], ASOF, C=L)
    r = sec["groups"][0]["rows"][0]
    vol = np.std(np.diff(np.log(cl[-251:])) * 100, ddof=1)
    assert abs(r["sd"] - 1.0101 / vol) < 1e-6                              # not the monitor's 60-day live_z of 9
    assert r["label"] == "WTI (CLZ26)"


def test_active_contract_is_the_most_traded(monkeypatch):
    from pmstack.adapters import yahoo
    vols = {"CLX26.NYM": [90962, 1000], "CLZ26.NYM": [319879, 56133], "CLF27.NYM": [118823, 17616]}
    monkeypatch.setattr(yahoo.base, "get_json", lambda url, **kw: {"chart": {"result": [{"indicators": {"quote": [
        {"volume": vols.get(url.rsplit("/", 1)[1], [])}]}}]}})
    assert yahoo.active_contract({"root": "CL", "exch": "NYM"}, date(2026, 11, 1)) == "CLZ26.NYM"   # X26, Z26, F27
    assert yahoo.active_contract({"root": "GC", "exch": "CMX", "months": "GJMQVZ"}, date(2026, 10, 21)) is None
