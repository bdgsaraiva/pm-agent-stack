"""Metals specialist (S3): stock-change playbooks, China data days, the storage test and long-run real prices.

Code computes, the model writes. Four blocks, each point in time (`--date D` uses only what was public by D):
  - stocks: copper and aluminium price moves on LME daily and SHFE weekly stock changes. Surprise = the change vs
    its own norm (weekly: the same and adjacent ISO weeks of the prior 5 years, as in pmstack/events.py; daily: the
    trailing 250-day mean and sd of daily changes). Same statistics as the EIA playbooks (events.base_rates).
  - china_days: copper and aluminium volatility on NBS PMI days vs other days, gold on the same days as the control
    for month-end flows, and placebo days shifted 5 trading days. No surprise (no free consensus).
  - storage: the theory of storage on weekly SHFE report days (Fama & French 1988; Geman & Smith 2013): LME
    cash-3-month spread and realised vol vs log visible stocks (LME + SHFE), Newey-West errors, chronological blocks,
    ADF on the residual, and the inventory-implied spread today.
  - longrun: World Bank monthly prices from 1960 deflated by US CPI: percentile, vs the trailing 10 years and vs a
    log-linear trend (Erten & Ocampo 2013 supercycles; Stuermer 2018).

All descriptive: contemporaneous relations, never forecasts, and nothing here alerts (agent 12's gate decides that).
Evidence and caveats: docs/research/metals.md. `--write` saves knowledge/metals/<metal>/estimates/*.json and the
code tables in knowledge/metals/<metal>/events.md.
"""
from __future__ import annotations

import argparse
import calendar
import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import events, qstats, runlog, store

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "metals.yaml"
KNOWLEDGE = ROOT / "knowledge" / "metals"
LME_URL = "https://www.westmetall.com/en/markdaten.php"
SHFE_URL = "https://www.shfe.com.cn/reports/tradedata/dailyandweeklydata/"
WB_URL = "https://www.worldbank.org/en/research/commodity-markets"


def cfg() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def _today() -> date:
    return (datetime.now(timezone.utc) - timedelta(hours=3)).date()


def _r(x, nd=3):
    return events._r(x, nd)


def _series(con, source: str, sid: str, until: date) -> pd.Series:
    return events._series(con, source, sid, until)       # duplicates across blocks collapse to one value per date


def market_url(market: str) -> str:
    return LME_URL if market.startswith("lme:") else f"https://finance.yahoo.com/quote/{market}"


# ------------------------------------------------------------------ stocks
def stock_surprises(stocks: pd.Series, freq: str, st: dict, asof: date) -> pd.DataFrame:
    if freq == "weekly":                                  # SHFE: released on its own report day
        sur = events.surprises(stocks, {"lag_days": 0, "holiday_window": [1, 0]}, st, asof)
        if sur.empty:
            return sur
        s = stocks[stocks.index <= asof].sort_index()
        span = pd.Series([(b - a).days for a, b in zip(s.index[:-1], s.index[1:])], index=s.index[1:])
        # review S3: a change across a skipped holiday week (Chinese New Year, Golden Week) spans two weeks and is not
        # comparable with one-week norms; and the norm needs `norm_years` full prior years of reports
        first = s.index[0]
        keep = (sur["week_ending"].map(span) <= 10) & (sur["week_ending"] >= date(first.year + int(st["norm_years"]) + 1, 1, 1))
        return sur[keep].reset_index(drop=True)
    s = stocks[stocks.index <= asof].sort_index()
    if len(s) < 120:
        return pd.DataFrame()
    chg = s.diff()
    n = int(st["daily_norm_days"])
    mu = chg.shift(1).rolling(n, min_periods=60).mean()
    sd = chg.shift(1).rolling(n, min_periods=60).std()
    df = pd.DataFrame({"week_ending": s.index, "release": s.index, "level": s.values, "change": chg.values,
                       "avg5_change": mu.values, "seasonal_sd": sd.values, "n_norm": n})
    df["surprise"] = df["change"] - df["avg5_change"]
    df["z"] = df["surprise"] / df["seasonal_sd"]
    return df.dropna(subset=["change", "seasonal_sd"]).reset_index(drop=True)


def align(sur: pd.DataFrame, rets: pd.DataFrame) -> pd.DataFrame:
    """Each release priced on the first trading day of the market on or after it (a holiday moves it later)."""
    if sur.empty:
        return sur
    idx = rets.index
    pos = idx.searchsorted(list(sur["release"]))
    sur = sur.copy()
    sur["release"] = [idx[p] if p < len(idx) else None for p in pos]
    sur = sur.dropna(subset=["release"])
    return sur.drop_duplicates("release", keep="last").reset_index(drop=True)


def _prices(con, market: str, source: str, asof: date, start: str) -> pd.Series:
    px = _series(con, source, market, asof)
    return px[px.index >= date.fromisoformat(start)]


def stock_reactions(asof: date, con, c: dict) -> dict:
    st = c["stats"]
    out = {}
    for pr in c["stocks"]:
        stocks = _series(con, pr["source"], pr["series"], asof)
        px = _prices(con, pr["market"], pr["market_source"], asof, st["start"])
        if len(stocks) < 60 or px.empty:
            out[pr["key"]] = {**pr, "status": "no data"}
            continue
        rets = events.returns(px, st)
        sur = align(stock_surprises(stocks, pr["freq"], st, asof), rets)
        br = events.base_rates(sur, rets, st, 1000.0, [tuple(e) for e in st["eras"]]) if not sur.empty else {"status": "insufficient", "events": 0}
        if pr["freq"] == "daily" and br.get("vol"):        # every trading day has a report: no "other days" to compare
            br["vol"] = {"ratio": None, "note": "daily report: every trading day is a report day"}
            br["big_move"] = {"release_rate": None, "other_rate": None, "lift": None, "release_ci95": [None, None],
                              "other_ci95": [None, None], "threshold_sd": st["big_move_sd"], "note": "daily report"}
        lt = events.latest(stock_surprises(stocks, pr["freq"], st, asof))
        out[pr["key"]] = {**pr, "unit_per": "1,000 t", **br, "latest": lt,
                          "comparable": events.conditional(sur, rets, lt and lt.get("z")),
                          "norm": ("change vs the same and adjacent ISO weeks of the prior 5 years" if pr["freq"] == "weekly"
                                   else f"change vs the trailing {st['daily_norm_days']}-day mean and sd of daily changes"),
                          "series_url": SHFE_URL if pr["source"] == "shfe" else LME_URL, "market_url": market_url(pr["market"])}
    return out


# ------------------------------------------------------------------ China data days
def pmi_dates(spec: dict, asof: date) -> list[date]:
    d0 = date.fromisoformat(spec["from"])
    exc = spec.get("exceptions") or {}
    out, y, m = [], d0.year, d0.month
    while True:
        d = date(y, m, calendar.monthrange(y, m)[1])
        d = date.fromisoformat(str(exc[f"{y}-{m:02d}"])) if f"{y}-{m:02d}" in exc else d
        if d > asof:
            break
        out.append(d)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def day_vol(rets: pd.DataFrame, days: list[date], st: dict, shift: int = 0) -> dict:
    rr = rets[~rets["outlier"]].dropna(subset=["sd"])
    idx = rr.index
    pos = [p + shift for p in idx.searchsorted(days)]
    on_days = {idx[p] for p in pos if 0 <= p < len(idx)}
    if len(on_days) < 10:
        return {"events": len(on_days), "status": "insufficient"}
    span = rr[rr.index >= min(on_days)]
    is_on = span.index.isin(on_days)
    on, off = span[is_on], span[~is_on]
    from scipy import stats as sps
    big_on = int((on["ret"].abs() > st["big_move_sd"] * on["sd"]).sum())
    big_off = int((off["ret"].abs() > st["big_move_sd"] * off["sd"]).sum())
    out = {"events": len(on), "status": "ok" if len(on) >= st["min_events"] else "insufficient",
           "from": str(min(on_days)), "to": str(max(on_days)),
           "sd_event": _r(on["ret"].std()), "sd_other": _r(off["ret"].std()),
           "ratio": _r(on["ret"].std() / off["ret"].std()),
           "levene_p": _r(float(sps.levene(on["ret"], off["ret"]).pvalue), 4),
           "abs_scaled_event": _r((on["ret"].abs() / on["sd"]).mean()), "abs_scaled_other": _r((off["ret"].abs() / off["sd"]).mean()),
           "big_event": _r(big_on / len(on)), "big_event_ci95": [_r(x) for x in events.wilson(big_on, len(on))],
           "big_other": _r(big_off / len(off)), "lift": _r((big_on / len(on)) / (big_off / len(off))) if big_off else None}
    if shift == 0:
        half = sorted(on_days)[len(on_days) // 2]
        out["halves"] = {nm: _half_ratio(rr, on_days, half, nm) for nm in ("first", "second")}
    return out


def _half_ratio(rr: pd.DataFrame, on_days: set, half, nm: str):
    part = rr[(rr.index < half) if nm == "first" else (rr.index >= half)]
    part = part[part.index >= min(on_days)]
    m = part.index.isin(on_days)
    if m.sum() < 5:
        return None
    return _r(part["ret"][m].std() / part["ret"][~m].std())


def china_days(asof: date, con, c: dict) -> dict:
    st = c["stats"]
    out = {}
    for key, spec in c["china_days"].items():
        days = pmi_dates(spec, asof)
        rows = {}
        for mk in spec["markets"] + [{**spec["control"], "metal": "control"}]:
            px = _prices(con, mk["market"], mk["source"], asof, st["start"])
            if px.empty:
                rows[mk["market"]] = {**mk, "status": "no data"}
                continue
            rets = events.returns(px, st)
            base = day_vol(rets, days, st)
            # placebos avoid the first week of the month (US ISM, Caixin and payrolls days; review S3)
            base["placebo"] = {f"{s:+d}d": day_vol(rets, days, st, s).get("ratio") for s in st["placebo_shifts"]}
            # weekend releases are priced on the first trading day of the month, which is also ISM and Caixin day
            wk = day_vol(rets, [d for d in days if d.weekday() < 5], st)
            base["weekday_releases"] = {"events": wk.get("events"), "ratio": wk.get("ratio"), "levene_p": wk.get("levene_p")}
            rows[mk["market"]] = {**mk, **base, "market_url": market_url(mk["market"])}
        ctrl = rows.get(spec["control"]["market"], {}).get("ratio")
        for mk in spec["markets"]:
            r = rows.get(mk["market"], {})
            if r.get("ratio") and ctrl:
                r["ratio_vs_control"] = _r(r["ratio"] / ctrl)
        nxt = pmi_dates({**spec, "from": asof.replace(day=1).isoformat()}, asof + timedelta(days=40))
        out[key] = {"name": spec["name"], "url": spec["url"], "calendar_urls": spec.get("calendar_urls"),
                    "rule": spec["rule"], "from": spec["from"], "events_known": len(days),
                    "next_release": next((d.isoformat() for d in nxt if d >= asof), None), "markets": rows}
    return out


# ------------------------------------------------------------------ storage
def _asof_value(s: pd.Series, d, max_gap: int = 5):
    i = s.index.searchsorted(d, side="right") - 1
    if i < 0 or (d - s.index[i]).days > max_gap:
        return None
    return float(s.iloc[i])


def level_vs_5y(s: pd.Series, d, years: int = 5) -> dict | None:
    """A weekly level vs the same and adjacent ISO weeks of the prior `years` calendar years (EIA convention)."""
    if d not in s.index:
        return None
    wk, yr = d.isocalendar()[1], d.year
    hist = s[[(x.year < yr) and (x.year >= yr - years) and min(abs(x.isocalendar()[1] - wk), 53 - abs(x.isocalendar()[1] - wk)) <= 1
              for x in s.index]]
    if len(hist) < years:
        return None
    lvl, mu = float(s[d]), float(hist.mean())
    return {"level": lvl, "avg5": _r(mu, 0), "vs_avg_pct": _r(100 * (lvl / mu - 1), 1) if mu else None,
            "min5": _r(float(hist.min()), 0), "max5": _r(float(hist.max()), 0), "n": len(hist)}


EG_CRIT_5PCT = -3.34      # Engle-Granger 5% critical value for a residual with one regressor (not the -2.86 of a raw series)


def storage(metal: str, asof: date, con, c: dict) -> dict:
    """The theory of storage on weekly SHFE report days. The spread is carry-adjusted (review S3 #1): a 3-month spread
    holds about r x days/360 of interest cost, and US rates went from 0 to about 5% over the sample, so the raw spread
    mixes the rate level with the convenience yield (Fama & French 1988 use an interest-adjusted basis)."""
    sc = c["storage"]
    m = sc["metals"][metal]
    cash, m3 = _series(con, "lme", m["cash"], asof), _series(con, "lme", m["m3"], asof)
    lst, sst = _series(con, "lme", m["lme_stock"], asof), _series(con, "shfe", m["shfe_stock"], asof)
    rate = _series(con, "fred", sc["rate"], asof)
    if min(len(cash), len(m3), len(lst)) < 250 or len(sst) < 50 or len(rate) < 250:
        return {"status": "no data", "metal": metal}
    lr3 = np.log(m3).diff()
    lrc = np.log(cash).diff()
    w = int(sc["vol_window"])
    rv = lr3.rolling(w).std() * math.sqrt(252) * 100
    vr = lrc.rolling(w).std() / lr3.rolling(w).std()
    days = float(sc["carry_days"])
    rows = []
    for d in sst.index:
        c0, m0, l0, r0 = _asof_value(cash, d), _asof_value(m3, d), _asof_value(lst, d), _asof_value(rate, d, 10)
        if None in (c0, m0, l0, r0):
            continue
        raw = 100 * (c0 - m0) / m0
        rows.append({"date": d, "raw_spread_pct": raw, "spread_pct": raw + r0 * days / 360, "rate": r0, "lme": l0,
                     "shfe": float(sst[d]), "rv": _asof_value(rv.dropna(), d), "vol_ratio": _asof_value(vr.dropna(), d)})
    df = pd.DataFrame(rows).dropna()
    if len(df) < sc["min_weeks"]:
        return {"status": "insufficient", "metal": metal, "weeks": len(df)}
    df["total"] = df["lme"] + df["shfe"]
    df["x"] = np.log(df["total"] / 1000.0)
    nwmin = int(sc["nw_lags_min"])
    lags = max(qstats.nw_lags(len(df)), nwmin)          # residual AR(1) ~0.8 on weekly data: a wide window
    hold = int(sc["holdout_weeks"])
    fits = {}
    for ycol, what in (("spread_pct", f"carry-adjusted cash-3m spread: (cash - 3m) / 3m + {sc['rate']} x {int(days)}/360, % (positive = backwardation net of interest)"),
                       ("rv", f"{w}-day realised vol of LME 3-month, % a year"),
                       ("vol_ratio", f"{w}-day sd of cash returns / sd of 3-month returns")):
        res = qstats.ols(df[ycol].to_numpy(), df["x"].to_numpy(), nw=lags)
        blocks = []
        nb = int(sc["blocks"])
        for i in range(nb):
            part = df.iloc[i * len(df) // nb:(i + 1) * len(df) // nb]
            if i == nb - 1:                                   # the latest block leaves out the last quarter (today)
                part = part.iloc[:-hold] if len(part) > hold + 30 else part.iloc[:0]
            if len(part) >= 30:
                bf = qstats.ols(part[ycol].to_numpy(), part["x"].to_numpy(), nw=max(qstats.nw_lags(len(part)), nwmin))
                adf_b, _, _ = qstats.adf(bf["resid"])
                blocks.append({"from": str(part["date"].iloc[0]), "to": str(part["date"].iloc[-1]), "n": len(part),
                               "intercept": _r(bf["beta"][0]), "slope": _r(bf["beta"][1]), "t": _r(bf["t"][1], 2),
                               "adf_resid_t": _r(adf_b, 2)})
        bs = [x["slope"] for x in blocks if x["slope"] is not None]
        sl = float(res["beta"][1])
        adf_t, _, _ = qstats.adf(res["resid"])
        fits[ycol] = {"what": what, "n": int(res["n"]), "nw_lags": lags, "intercept": _r(res["beta"][0]),
                      "slope_per_log_stock": _r(sl), "t": _r(res["t"][1], 2), "r2": _r(res["r2"]),
                      "slope_per_10pct_more_stock": _r(sl * math.log(1.1)),
                      "blocks": blocks, "signs_agree": bool(bs) and all(np.sign(x) == np.sign(sl) for x in bs),
                      "full_inside_block_range": bool(bs) and min(bs) <= sl <= max(bs),
                      "adf_resid_t": _r(adf_t, 2), "resid_stationary_5pct": bool(adf_t < EG_CRIT_5PCT),
                      "adf_critical_5pct": EG_CRIT_5PCT}
    last = df.iloc[-1]
    f = fits["spread_pct"]
    # quant-research standards 2.2: when the full-sample slope lies outside the blocks' range, intercepts shifted between
    # regimes and the full fit mixes them; then the latest block (fitted without the last `holdout_weeks`) scores today
    # out of sample. The implied spread is suppressed unless that fit is significant, stationary and agrees in sign.
    use = "full" if f["full_inside_block_range"] or not f["blocks"] else "latest_block"
    lb = f["blocks"][-1] if f["blocks"] else {}
    if use == "full":                                         # refit without the last quarter: today scored out of sample
        fit_df = df.iloc[:-hold]
        ho = qstats.ols(fit_df["spread_pct"].to_numpy(), fit_df["x"].to_numpy(), nw=max(qstats.nw_lags(len(fit_df)), nwmin))
        a0, b0, t0, adf0 = float(ho["beta"][0]), float(ho["beta"][1]), float(ho["t"][1]), qstats.adf(ho["resid"])[0]
        lb = {"from": str(fit_df["date"].iloc[0]), "to": str(fit_df["date"].iloc[-1])}
    else:
        a0, b0, t0, adf0 = lb.get("intercept"), lb.get("slope"), lb.get("t"), lb.get("adf_resid_t")
    why = []
    if t0 is None or abs(t0) < 2:
        why.append("slope not significant (abs(t) below 2)")
    if not f["signs_agree"]:
        why.append("block slopes disagree in sign")
    if adf0 is None or adf0 >= EG_CRIT_5PCT:
        why.append("residual not stationary (Engle-Granger 5%)")
    f["implied_from"] = use
    implied = gap = rpct = None
    if not why:
        implied = a0 + b0 * float(last["x"])
        gap = float(last["spread_pct"]) - implied
        part = df[(df["date"] >= date.fromisoformat(lb["from"])) & (df["date"] <= date.fromisoformat(lb["to"]))]
        resid = part["spread_pct"] - (a0 + b0 * part["x"])
        rpct = _r(100 * float((resid <= gap).mean()), 0)

    def pct(series, v):
        return _r(100 * float((series <= v).mean()), 0)
    return {"status": "ok", "metal": metal, "weeks": len(df), "from": str(df["date"].iloc[0]), "to": str(last["date"]),
            "fits": fits,
            "now": {"date": str(last["date"]), "raw_spread_pct": _r(float(last["raw_spread_pct"])), "rate_pct": _r(float(last["rate"]), 2),
                    "spread_pct": _r(float(last["spread_pct"])), "lme_stock_t": _r(float(last["lme"]), 0),
                    "shfe_stock_t": _r(float(last["shfe"]), 0), "visible_stock_t": _r(float(last["total"]), 0),
                    "visible_stock_pctile": pct(df["total"], float(last["total"])),
                    "raw_spread_pctile": pct(df["raw_spread_pct"], float(last["raw_spread_pct"])),
                    "spread_pctile": pct(df["spread_pct"], float(last["spread_pct"])),
                    "inventory_implied_spread_pct": _r(implied), "implied_from": use, "implied_fit_window": [lb.get("from"), lb.get("to")],
                    "implied_suppressed": "; ".join(why) or None,
                    "spread_minus_implied_pp": _r(gap), "gap_pctile_vs_fit_residuals": rpct,
                    "rv_pct": _r(float(last["rv"]), 1), "vol_ratio": _r(float(last["vol_ratio"]), 2)},
            "shfe_vs_5y": level_vs_5y(sst, last["date"]),
            "sources": {"lme": LME_URL, "shfe": SHFE_URL, "rate": f"https://fred.stlouisfed.org/series/{sc['rate']}"}}


# ------------------------------------------------------------------ long run
def longrun(metal: str, sid: str, asof: date, con, c: dict) -> dict:
    lc = c["longrun"]
    nom = _series(con, "pinksheet", sid, asof)
    cpi = _series(con, "fred", lc["cpi"], asof)
    if len(nom) < 240 or len(cpi) < 240:
        return {"status": "no data", "metal": metal}
    def avail(d, lag):                                    # month d (first of month) is public `lag` days after it ends
        return date(d.year + (d.month == 12), d.month % 12 + 1, 1) + timedelta(days=lag)
    nom = nom[[avail(d, lc["lag_days"]) <= asof for d in nom.index]]
    cpi = cpi[[avail(d, lc["cpi_lag_days"]) <= asof for d in cpi.index]]
    if nom.empty or cpi.empty:
        return {"status": "no data", "metal": metal}
    cpi_full = cpi.reindex(sorted(set(cpi.index) | set(nom.index))).ffill()
    real = (nom / cpi_full.reindex(nom.index) * float(cpi.iloc[-1])).dropna()
    real = real[real > 0]
    last_d, last = real.index[-1], float(real.iloc[-1])
    yrs = int(lc["trailing_years"])
    trail = real[real.index > date(last_d.year - yrs, last_d.month, 1)]
    t = np.arange(len(real), dtype=float)
    fit = qstats.ols(np.log(real.to_numpy()), t)
    dev = float(np.log(last) - (fit["beta"][0] + fit["beta"][1] * t[-1]))
    ago = real[real.index <= date(last_d.year - 20, last_d.month, 1)]
    return {"status": "ok", "metal": metal, "month": str(last_d)[:7], "nominal": _r(float(nom.iloc[-1]), 2),
            "unit": "USD/troy oz" if metal == "gold" else ("USD/dmt" if metal == "iron_ore" else "USD/t"),
            "cpi_month": str(cpi.index[-1])[:7], "real_latest_dollars": _r(last, 2),
            "real_pctile_since_1960": _r(100 * float((real <= last).mean()), 0),
            "vs_trailing_10y_avg_pct": _r(100 * (last / float(trail.mean()) - 1), 1),
            "trend_growth_pct_a_year": _r(100 * (math.exp(12 * float(fit["beta"][1])) - 1), 2),
            "vs_log_trend_pct": _r(100 * (math.exp(dev) - 1), 1),
            "real_20y_earlier": _r(float(ago.iloc[-1]), 2) if len(ago) else None,
            "months": len(real), "from": str(real.index[0])[:7],
            "note": "real = nominal / US CPI x latest CPI known; trend = log-linear fit over every month to date (end-point sensitive)",
            "sources": {"pinksheet": WB_URL, "cpi": f"https://fred.stlouisfed.org/series/{lc['cpi']}"}}


# ------------------------------------------------------------------ run and write
def run(asof: date | None = None, con=None, write: bool = False) -> dict:
    c = cfg()
    asof = asof or _today()
    con = con or store.connect()
    out = {"asof": asof.isoformat(), "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
           "method": "docs/research/metals.md", "stocks": stock_reactions(asof, con, c),
           "china_days": china_days(asof, con, c),
           "storage": {m: storage(m, asof, con, c) for m in c["storage"]["metals"]},
           "longrun": {m: longrun(m, sid, asof, con, c) for m, sid in c["longrun"]["metals"].items()}}
    if write:
        write_outputs(out)
    return out


def write_outputs(out: dict) -> list[Path]:
    paths = []
    def save(metal, name, obj):
        f = KNOWLEDGE / metal / "estimates" / f"{name}.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"asof": out["asof"], **obj}, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        paths.append(f)
    for key, row in out["stocks"].items():
        if row.get("status") != "no data":
            save(row["metal"], f"stocks-{key}", row)
    for key, rep in out["china_days"].items():
        for mk, row in rep["markets"].items():
            if row.get("metal") in ("copper", "aluminium") and row.get("status") != "no data":
                ctrl = rep["markets"].get(next(iter([k for k, v in rep["markets"].items() if v.get("metal") == "control"]), ""), {})
                save(row["metal"], f"china-{key}", {**{k: v for k, v in rep.items() if k != "markets"}, **row, "control": ctrl})
    for m, row in out["storage"].items():
        if row.get("status") == "ok":
            save(m, "storage", row)
    for m, row in out["longrun"].items():
        if row.get("status") == "ok":
            save(m, "longrun", row)
    for metal in ("copper", "aluminium"):
        paths.append(_events_block(metal, out))
    return paths


BLOCK_START = "<!-- code: reaction base rates (pmstack metals --write) -->"
BLOCK_END = "<!-- /code -->"


def _f(x, nd=2, pct=False):
    return events._fmt(x, nd, pct)


def _events_block(metal: str, out: dict) -> Path:
    f = KNOWLEDGE / metal / "events.md"
    text = f.read_text(encoding="utf-8") if f.exists() else f"# Event playbooks: {metal}\n"
    L = [BLOCK_START, f"## Reaction base rates (code, as of {out['asof']})", "",
         "### Stock changes", "Daily closes on stock-report days vs other days. Surprise = the change vs its own norm (SHFE weekly: same and adjacent ISO weeks of the prior 5 years; "
         "LME daily: trailing 250-day mean and sd of daily changes), in sd. Sign hit = a bigger-than-normal draw with a price rise. Contemporaneous: predicts nothing. Full numbers: `estimates/stocks-*.json`.", "",
         "| Pair | Events | Vol ratio (report / other) | Big-move rate report vs other (lift) | Sign hit at abs(z) >= 1 (95% CI) | Slope per 1 sd (t) | Slope per 1,000 t (t) | Halves: slope per sd | Since 2015: slope per sd (t) | Placebo day before / after (t) |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for key, r in out["stocks"].items():
        if r.get("metal") != metal:
            continue
        if not r.get("events"):
            L.append(f"| {r['label']} | {r.get('status')} | | | | | | | | |")
            continue
        v, b, s, z, u, h, pl, rec = r["vol"], r["big_move"], r["sign"], r["slope_per_sd"], r["slope_per_unit"], r["halves"], r["placebo"], r["eras"].get("since_2015", {})
        L.append(f"| {r['label']} ({r['freq']}) | {r['events']} ({r['from'][:4]}-{r['to'][:4]}){' insufficient' if r['status'] == 'insufficient' else ''} | {_f(v['ratio'])} | "
                 f"{_f(b['release_rate'], pct=True)} vs {_f(b['other_rate'], pct=True)} ({_f(b['lift'])}) | "
                 f"{_f(s['hit_rate'], pct=True)} of {s['strong_n']} ({_f(s['ci95'][0], pct=True)}-{_f(s['ci95'][1], pct=True)}) | "
                 f"{_f(z.get('slope'))}% ({_f(z.get('t'), 1)}) | {_f(u.get('slope'), 3)}% ({_f(u.get('t'), 1)}) | "
                 f"{_f(h['first']['slope_per_sd'])} / {_f(h['second']['slope_per_sd'])} | {_f(rec.get('slope_per_sd'))} ({_f(rec.get('t'), 1)}) | "
                 f"{_f(pl['day_before']['slope_per_sd'])} ({_f(pl['day_before']['t'], 1)}) / {_f(pl['day_after']['slope_per_sd'])} ({_f(pl['day_after']['t'], 1)}) |")
    L += ["", "### China data days", "Volatility of daily returns on NBS manufacturing PMI days (last calendar day of the month, 09:30 Beijing; weekend releases priced next trading day) vs other days. "
          "Gold on the same days is the month-end control; placebo = the same days shifted 5 trading days back or 10 forward (clear of the first week of the month: ISM, Caixin, payrolls); weekend releases share the first trading day with ISM and Caixin, so weekday releases are also shown alone. No surprise measure (no free consensus).", "",
          "| Market | Events | Vol ratio (PMI day / other) | vs gold control | Big-move rate PMI vs other (lift) | Levene p | Halves | Placebo -5d / +10d | Weekday releases only: ratio (n) |",
          "|---|---|---|---|---|---|---|---|---|"]
    for key, rep in out["china_days"].items():
        for mk, r in rep["markets"].items():
            if r.get("metal") not in (metal, "control") or not r.get("events"):
                continue
            hv = r.get("halves") or {}
            pl = r.get("placebo") or {}
            L.append(f"| {r['label']} | {r['events']} ({r['from'][:4]}-{r['to'][:4]}) | {_f(r.get('ratio'))} | {_f(r.get('ratio_vs_control'))} | "
                     f"{_f(r.get('big_event'), pct=True)} vs {_f(r.get('big_other'), pct=True)} ({_f(r.get('lift'))}) | {_f(r.get('levene_p'), 3)} | "
                     f"{_f(hv.get('first'))} / {_f(hv.get('second'))} | {_f(pl.get('-5d'))} / {_f(pl.get('+10d'))} | {_f((r.get('weekday_releases') or {}).get('ratio'))} ({(r.get('weekday_releases') or {}).get('events')}) |")
    L += ["", "LME stocks are dated at the day Westmetall lists them; LME publishes them at 09:00 London for the previous day's moves, so "
          "a one-day offset is possible (the day-after placebo would show it). Prices and stocks via Westmetall (LME) and SHFE: personal use only. A daily report leaves no other days, so vol ratio and big-move lift are blank for LME. China customs trade days are not covered "
          "(no dated calendar yet: open-questions.md).", BLOCK_END]
    block = "\n".join(L)
    if BLOCK_START in text:
        text = re.sub(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END), lambda m: block, text, flags=re.S)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    return f


def summary(out: dict) -> dict:
    s = {"stocks": {k: {"status": v.get("status"), "events": v.get("events"), "slope_per_sd": (v.get("slope_per_sd") or {}).get("slope"),
                        "t": (v.get("slope_per_sd") or {}).get("t"), "hit": (v.get("sign") or {}).get("hit_rate"),
                        "vol_ratio": (v.get("vol") or {}).get("ratio"), "latest_z": (v.get("latest") or {}).get("z")}
                    for k, v in out["stocks"].items()},
         "china_days": {k: {mk: {"events": r.get("events"), "ratio": r.get("ratio"), "vs_control": r.get("ratio_vs_control"),
                                 "placebo": r.get("placebo")} for mk, r in rep["markets"].items()} | {"next": rep["next_release"]}
                        for k, rep in out["china_days"].items()},
         "storage": {m: {"status": v.get("status"), "weeks": v.get("weeks"),
                         **({"spread_slope": v["fits"]["spread_pct"]["slope_per_log_stock"], "t": v["fits"]["spread_pct"]["t"],
                             "r2": v["fits"]["spread_pct"]["r2"], "blocks_agree": v["fits"]["spread_pct"]["signs_agree"],
                             "adf": v["fits"]["spread_pct"]["adf_resid_t"], "now": v["now"]} if v.get("status") == "ok" else {})}
                     for m, v in out["storage"].items()},
         "longrun": {m: {k: v.get(k) for k in ("month", "real_pctile_since_1960", "vs_trailing_10y_avg_pct", "vs_log_trend_pct")}
                     for m, v in out["longrun"].items()}}
    return s


def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack metals")
    p.add_argument("--date", help="as-of date (point in time), default today BRT")
    p.add_argument("--write", action="store_true", help="write knowledge/metals/*/estimates/*.json and the events.md code tables")
    a = p.parse_args(argv)
    out = run(date.fromisoformat(a.date) if a.date else None, write=a.write)
    s = summary(out)
    runlog.log(runlog.new_run_id(), "metals:base-rates", "ok", asof=out["asof"], write=a.write,
               stocks={k: {"events": v["events"], "slope_per_sd": v["slope_per_sd"], "t": v["t"]} for k, v in s["stocks"].items()})
    print(json.dumps(s, indent=1, default=str))
    return 0
