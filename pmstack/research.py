"""Research loop (agent 12): replicate an idea or a paper on public data behind the quant gate, give a verdict, and keep
every trial (the graveyard included). First jobs: the base rate and lift of agent 7's and agent 8's flags.

Evidence behind each rule: docs/research/research-loop.md. In short:
  - Pre-register, then run. A study (research/studies/<id>.yaml) is frozen by hash on its first run; an edit needs a
    new id. Every run is a line in research/ledger.jsonl, so the number of trials is known (Harvey, Liu & Zhu;
    Lopez de Prado's "every trial counts").
  - Binary flags are judged by lift against the base rate, on independent episodes, never by hit rate
    (Kaminsky, Lizondo & Reinhart's signals approach; quant-research-standards s.7). The base rate is the same market,
    the same side and the same evaluable window, so composition cannot fake a lift.
  - Flags are recomputed on a weekly grid with the agents' own functions on data available that day; the outcome starts
    at the first close after the data were public (CFTC: the Friday release; GDELT and prices: the next morning).
  - Inference is a circular-shift placebo: one shift of the calendar per draw for every source and market (it keeps
    the flag's clustering across narratives and correlated markets, and each market's volatility regime), then
    Benjamini-Hochberg across every registered flag study (missing ones at p = 1), Holm and BY and t > 3 beside it.
  - Flags whose definitions were written with their history in view (the narrative queries) are "in-sample only"
    until live episodes agree; a change to the code or config that defines a study blocks "supported".
  - The effect must hold in both chronological halves, be big enough to matter, and is shown with a decay haircut.
  - Strategies (e.g. time-series momentum) are judged by alpha against the long-only book of the same markets,
    after costs, with a deflated Sharpe over all registered variants and the post-publication period apart.
  - The model never supplies a number: it drafts a registration and words a verdict that the number auditor checks.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import qstats
from . import srcconfig

ROOT = Path(__file__).resolve().parents[1]
RDIR = ROOT / "research"
EULER = 0.5772156649015329
OUTCOMES = {"adverse", "follow", "big_move", "signed"}
KINDS = {"flag", "strategy"}
REQUIRED = ("id", "title", "kind", "hypothesis", "source", "registered")
CFTC_URL = "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"


def cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "research.yaml").read_text(encoding="utf-8"))


def paths(root: Path | None = None) -> dict[str, Path]:
    r = root or RDIR
    return {"root": r, "studies": r / "studies", "results": r / "results", "ledger": r / "ledger.jsonl",
            "index": r / "index.md", "verdicts": r / "verdicts.json"}


def _r(x, nd=3):
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) or math.isinf(x) else round(x, nd)


# ------------------------------------------------------------------ data
def load_obs(asof: date, data_root: Path | None = None) -> pd.DataFrame:
    """Every stored observation dated on or before `asof` (the hard wall: nothing later exists)."""
    from . import store
    df = store.connect(data_root).execute(
        "SELECT source, series_id, date, value, source_url FROM obs WHERE date <= ?", [asof]).df()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def _series(obs: pd.DataFrame, sid: str) -> pd.Series:
    s = obs[obs.series_id == sid][["date", "value"]]
    if s.empty:
        return pd.Series(dtype=float)
    return pd.Series(s.value.astype(float).values, index=pd.to_datetime(s.date)).sort_index()


def returns(obs: pd.DataFrame, markets: list[str], asof: date) -> pd.DataFrame:
    """Agent 8's daily log returns on the US calendar (spliced with proxies, roll jumps screened where a proxy exists)."""
    from . import risk
    lr, _ = risk.history(obs, list(dict.fromkeys(markets)), asof, risk.cfg())
    return lr.iloc[1:] if len(lr) else lr


def grid_dates(start, end, freq: str) -> pd.DatetimeIndex:
    return pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq=freq)


# ------------------------------------------------------------------ outcomes
def outcome_z(r: pd.Series, h: int, lam: float, lag_days: int) -> pd.Series:
    """Vol-scaled forward move for every signal day of the calendar: the log return from the close of the first trading
    day on or after signal + `lag_days` (the data were public by then) to h trading days later, divided by the EWMA
    daily sd known on the signal day times sqrt(h). NaN where the window is not complete or the sd is unknown."""
    idx = r.index
    x = r.astype(float)
    have = x.notna().to_numpy()
    sd = np.sqrt((x.dropna() ** 2).ewm(alpha=1 - lam, adjust=False).mean()).reindex(idx).ffill()
    n_obs = x.notna().cumsum().to_numpy()
    sd = sd.where(n_obs >= 20)
    c = np.concatenate([[0.0], np.nancumsum(x.to_numpy())])
    cnt = np.concatenate([[0], np.cumsum(have)])
    entry = idx.searchsorted(idx + pd.Timedelta(days=lag_days), side="left")
    out = np.full(len(idx), np.nan)
    ok = entry + h < len(idx)
    e = entry[ok]
    fwd = c[e + h + 1] - c[e + 1]
    filled = cnt[e + h + 1] - cnt[e + 1]
    z = fwd / (sd.to_numpy()[ok] * math.sqrt(h))
    z[filled < max(1, int(0.8 * h))] = np.nan
    out[ok] = z
    return pd.Series(out, index=idx)


def hit(z: np.ndarray, side: np.ndarray, outcome: str, k: float) -> np.ndarray:
    """Outcome per row: 'adverse' = moved >= k sd against `side`; 'follow' = >= k sd with it; 'big_move' = >= k sd
    either way; 'signed' = the side-signed vol-scaled move itself (continuous)."""
    s = np.where(side == 0, 1, side)
    if outcome == "adverse":
        return np.where(np.isnan(z), np.nan, (s * z <= -k).astype(float))
    if outcome == "follow":
        return np.where(np.isnan(z), np.nan, (s * z >= k).astype(float))
    if outcome == "big_move":
        return np.where(np.isnan(z), np.nan, (np.abs(z) >= k).astype(float))
    if outcome == "signed":
        return s * z
    raise ValueError(f"unknown outcome {outcome!r}; one of {sorted(OUTCOMES)}")


# ------------------------------------------------------------------ flag catalogue (agents' own functions, point in time)
FLAGS: dict[str, dict] = {}


def flag(name: str, agent: int, lag_days: int, doc: str, sides: str):
    def deco(fn):
        FLAGS[name] = {"fn": fn, "agent": agent, "lag_days": lag_days, "doc": doc, "sides": sides}
        return fn
    return deco


def _cftc_markets() -> dict[str, str]:
    """Price market -> CFTC code, one market per code (the first in config/journal.yaml: CL=F for WTI, not BZ=F)."""
    from . import journal
    out, seen = {}, set()
    for m, code in (journal._cfg().get("cftc_map") or {}).items():
        if code not in seen:
            out[m] = code
            seen.add(code)
    return out


def _rows(rows: list[dict]) -> pd.DataFrame:
    cols = ["date", "market", "source", "on", "side"]
    return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)


def _doc_narratives(obs: pd.DataFrame) -> list[dict]:
    """Frozen narratives (config/sources.yaml) that have a stored GDELT DOC share history (the only long instrument).
    Retired ones count too: retiring a narrative from the map (copper, OPEC+, crop weather, gold on 20 Oct 2026) must
    not change a registered study's population after its first run."""
    have = set(obs.series_id.unique())
    src = srcconfig.shared()
    return [q for q in (src.get("gdelt") or {}).get("queries", []) if not q.get("validation") and q.get("markets")
            and f"gdelt:{q['id']}:share" in have]


def narrative_stages(obs: pd.DataFrame, asof: date, freq: str, cache: dict | None = None) -> pd.DataFrame:
    """Agent 7's stage per narrative on each grid date, from consensus.stage_of on data up to that date (DOC instrument).
    A narrative whose last data day is older than `stale_days` has no stage that day (as in consensus.narratives)."""
    from . import consensus
    key = ("stages", asof, freq)
    if cache is not None and key in cache:
        return cache[key]
    c = consensus.cfg()
    norm = _series(obs, "gdelt:norm")
    rows = []
    for q in _doc_narratives(obs):
        share, count = _series(obs, f"gdelt:{q['id']}:share").dropna(), _series(obs, f"gdelt:{q['id']}:count")
        if share.empty:
            continue
        # the gap rule is causal (same-weekday median of the last 4 weeks), so the valid days up to d are the valid
        # days of the whole series up to d: computed once, then each stage ends on the last valid day, as live
        # consensus._assess does (review, finding 12b)
        good = consensus.valid_days(share, norm, share.index[-1].date(), c).index
        for d in grid_dates(share.index[0] + pd.Timedelta(days=c["min_history_days"]), asof, freq):
            last = good[good <= d]
            if not len(last) or (d - last[-1]).days > c["stale_days"]:
                continue
            st = consensus.stage_of(share, count, norm, last[-1].date(), c)["stage"]
            rows.append({"date": d, "narrative": q["id"], "name": q.get("name", q["id"]), "stage": st,
                         "markets": q["markets"]})
    out = pd.DataFrame(rows, columns=["date", "narrative", "name", "stage", "markets"])
    if cache is not None:
        cache[key] = out
    return out


@flag("narrative_stage", 7, 1, "agent 7 narrative stage == params.stage (spreading | peaking | fading | steady | "
      "dormant), on each market the narrative pushes, side = the narrative's sign for that market", "narrative sign")
def f_narrative_stage(obs, asof, p, freq, cache=None):
    st = narrative_stages(obs, asof, freq, cache)
    rows = []
    for r in st.itertuples():
        if r.stage in ("insufficient coverage", "insufficient history"):
            continue
        for m, sgn in r.markets.items():
            rows.append({"date": r.date, "market": m, "source": r.narrative, "on": r.stage == p["stage"], "side": int(sgn)})
    return _rows(rows)


def cftc_table(obs: pd.DataFrame, code: str, lookback: int = 156, weeks: int = 156) -> pd.DataFrame:
    """Per report date: the managed-money 3-year percentile (consensus.positioning / monitor positioning_extreme) and
    the weekly-change z (risk.crowding), each on reports up to that date only."""
    s = _series(obs, f"{code}.mm_net_pct_oi").dropna()
    rows = []
    for i in range(51, len(s)):                         # >= 52 reports, as all three agents require
        v = s.iloc[max(0, i + 1 - lookback):i + 1]
        pct = float(100 * (v <= v.iloc[-1]).mean())
        w = s.iloc[max(0, i + 1 - weeks):i + 1]
        ch = w.diff().dropna()
        z = float((ch.iloc[-1] - ch.mean()) / ch.std()) if len(ch) > 20 and ch.std() > 0 else float("nan")
        rows.append({"date": s.index[i], "release": cftc_release(s.index[i]), "pct": pct, "z": z})
    return pd.DataFrame(rows, columns=["date", "release", "pct", "z"])


def cftc_release(report: pd.Timestamp) -> pd.Timestamp:
    """The day a Tuesday report became public: Friday 15:30 ET, or the next Monday when a federal holiday falls in the
    release week (CFTC's schedule; review, finding 12d). Flags are dated here and scored from the next close."""
    from pandas.tseries.holiday import USFederalHolidayCalendar
    fri = pd.Timestamp(report).normalize() + pd.Timedelta(days=(4 - pd.Timestamp(report).dayofweek) % 7 or 7)
    mon = fri - pd.Timedelta(days=4)
    hol = USFederalHolidayCalendar().holidays(mon, fri)
    return fri + pd.Timedelta(days=3) if len(hol) else fri


@flag("cftc_crowded", 8, 1, "CFTC managed money at or beyond params.pct (default 90) of its 3-year range on a side "
      "(agent 8 crowding, agent 7 'crowded', the monitor's positioning_extreme); side = the crowded side; dated at the "
      "release (Friday, or Monday in a federal-holiday week) and scored from the next close", "crowded side")
def f_cftc_crowded(obs, asof, p, freq, cache=None):
    hi = float(p.get("pct", 90))
    rows = []
    for m, code in _cftc_markets().items():
        t = cftc_table(obs, code)
        for r in t.itertuples():
            side = 1 if r.pct >= hi else -1 if r.pct <= 100 - hi else 0
            rows.append({"date": r.release, "market": m, "source": code, "on": side != 0, "side": side or 1})
    return _rows(rows)


@flag("cftc_crowded_entry", 8, 1, "weekly managed-money change at or beyond params.z (default 2) sd of 3 years of weekly "
      "changes (agent 8 'crowded entry', the monitor's positioning_shift); side = the direction of the change",
      "direction of the change")
def f_cftc_crowded_entry(obs, asof, p, freq, cache=None):
    zc = float(p.get("z", 2.0))
    rows = []
    for m, code in _cftc_markets().items():
        t = cftc_table(obs, code)
        for r in t.itertuples():
            if math.isnan(r.z):
                continue
            rows.append({"date": r.release, "market": m, "source": code, "on": abs(r.z) >= zc, "side": 1 if r.z > 0 else -1})
    return _rows(rows)


@flag("crowded_red", 8, 1, "crowded (cftc_crowded) while funding is stressing on the release day (agent 8 'crowded "
      "red': VIX at or above its 80th percentile since 1990, or HY OAS +50bp over 21 days)", "crowded side")
def f_crowded_red(obs, asof, p, freq, cache=None):
    from . import risk
    rc = risk.cfg()
    fobs = obs[obs.series_id.isin([rc["funding"]["vix_series"], rc["funding"]["hy_series"]])]
    base = f_cftc_crowded(obs, asof, p, freq, cache)
    memo: dict = {}

    def stressing(d) -> bool:
        k = pd.Timestamp(d).date()                      # rows are dated at the release
        if k not in memo:
            memo[k] = bool(risk.funding(fobs, k, rc).get("stressing"))
        return memo[k]
    base["on"] = [bool(o) and stressing(d) for o, d in zip(base["on"], base["date"])]
    return base


@flag("consensus_label", 7, 1, "agent 7 consensus-map label == params.label (self-reinforcing | twilight | crowded | "
      "quiet | mixed) from its own trend vote, CFTC percentile and the DOC narrative stages; side = the trend direction",
      "trend direction")
def f_consensus_label(obs, asof, p, freq, cache=None):
    t = _label_table(obs, asof, freq, cache)
    if p["label"] in ("self-reinforcing", "twilight"):    # these need a narrative stage: rows (and so the base-rate
        t = t[t.n_linked > 0]                              # window) only where one exists (review, finding 4)
    return _rows([{"date": r.date, "market": r.market, "source": r.market, "on": r.label == p["label"], "side": r.side}
                  for r in t.itertuples()])


def _label_table(obs: pd.DataFrame, asof: date, freq: str, cache: dict | None = None) -> pd.DataFrame:
    """consensus._label for each CFTC market on each grid date, from consensus.trend, consensus.positioning (Friday
    release) and the DOC narrative stages of that date."""
    from . import consensus
    key = ("labels", asof, freq)
    if cache is not None and key in cache:
        return cache[key]
    c = consensus.cfg()
    lag = int(c.get("cftc_release_lag_days", 3))
    st = narrative_stages(obs, asof, freq, cache)
    by_date = {d: g for d, g in st.groupby("date")}
    rows = []
    for m, code in _cftc_markets().items():
        om = obs[obs.series_id.isin([m, f"{code}.mm_net_pct_oi"])]
        px = om[om.series_id == m]
        if px.empty:
            continue
        first = pd.Timestamp(px.date.min()) + pd.Timedelta(days=400)
        for d in grid_dates(first, asof, freq):
            tr = consensus.trend(om, m, d.date(), c)
            pos = consensus.positioning(om, code, d.date(), lag=lag)
            if tr is None or pos is None:
                continue
            g = by_date.get(d)
            linked = [] if g is None else [
                {"id": r.narrative, "name": r.name, "stage": r.stage, "sign": int(r.markets[m])}
                for r in g.itertuples() if m in r.markets]
            rows.append({"date": d, "market": m, "label": consensus._label(tr, pos, linked, c),
                         "side": consensus._dir(tr) or 1,
                         "n_linked": sum(1 for n in linked if n["stage"] in consensus.STAGES - {"insufficient coverage"})})
    out = pd.DataFrame(rows, columns=["date", "market", "label", "side", "n_linked"])
    if cache is not None:
        cache[key] = out
    return out


def _cta_states(obs: pd.DataFrame, asof: date, freq: str, cache: dict | None = None) -> pd.DataFrame:
    """risk.cta_levels on each market's observed closes up to each grid date (agent 8's CTA levels)."""
    from . import risk
    key = ("cta", asof, freq)
    if cache is not None and key in cache:
        return cache[key]
    rc = risk.cfg()
    raw = risk.observed(obs, list(rc["universe"]), asof)
    rows = []
    for m in raw.columns:
        p = raw[m].dropna()
        if len(p) < 65:
            continue
        for d in grid_dates(p.index[0] + pd.Timedelta(days=95), asof, freq):
            q = p[p.index <= d]
            if len(q) < 65 or (d - q.index[-1]).days > 5:      # live cta_levels needs 63 + 2 closes (finding 12c)
                continue
            x = risk.cta_levels(q, rc)
            if not x:
                continue
            legs = x.get("legs") or {}
            flip = [(leg["rolloff_flip_days"], -leg["sign"]) for leg in legs.values() if leg.get("rolloff_flip_days")]
            s12 = (legs.get("252") or {}).get("sign")
            vote = sum(leg["sign"] for leg in legs.values())
            rows.append({"date": d, "market": m, "state": x.get("state"), "s12": s12, "vote": vote,
                         "vol_shrinking": bool(x.get("vol_shrinking")),
                         "panic": bool((x.get("panic") or {}).get("panic")),
                         "flip_side": min(flip)[1] if flip else 0})
    out = pd.DataFrame(rows, columns=["date", "market", "state", "s12", "vote", "vol_shrinking", "panic", "flip_side"])
    if cache is not None:
        cache[key] = out
    return out


def _sgn(x) -> int:
    return 1 if x and x > 0 else -1 if x and x < 0 else 0


@flag("cta_rolloff_flip", 8, 1, "agent 8 CTA levels: a trend leg (21/63/252 days) flips by roll-off within 5 days at "
      "today's price; side = the sign the soonest leg flips to", "flip direction")
def f_cta_rolloff(obs, asof, p, freq, cache=None):
    t = _cta_states(obs, asof, freq, cache)
    return _rows([{"date": r.date, "market": r.market, "source": r.market, "on": r.flip_side != 0,
                   "side": int(r.flip_side) or 1} for r in t.itertuples()])


@flag("cta_state", 8, 1, "agent 8 CTA state == params.state (correction: 12-month leg up, 1-month down; rebound: the "
      "reverse); side = the 12-month sign", "12-month trend sign")
def f_cta_state(obs, asof, p, freq, cache=None):
    t = _cta_states(obs, asof, freq, cache)
    return _rows([{"date": r.date, "market": r.market, "source": r.market, "on": r.state == p["state"],
                   "side": _sgn(r.s12) or 1} for r in t.itertuples() if r.state is not None])


@flag("cta_vol_shrinking", 8, 1, "agent 8 vol-target channel: slow/fast vol < 0.7 (vol-targeted trend books shrinking "
      "with no flip); side = the trend vote's direction", "trend vote direction")
def f_cta_shrink(obs, asof, p, freq, cache=None):
    t = _cta_states(obs, asof, freq, cache)
    return _rows([{"date": r.date, "market": r.market, "source": r.market, "on": bool(r.vol_shrinking) and r.vote != 0,
                   "side": _sgn(r.vote) or 1} for r in t.itertuples()])


@flag("cta_panic", 8, 1, "agent 8 panic state (Daniel & Moskowitz): 24-month return < 0 and 126-day vol at or above its "
      "80th percentile of ~3 years; side = the 12-month sign; params.only = short scores only a down 12-month trend, "
      "as the live flag (\"rebound risk on a with-trend short\") does", "12-month trend sign")
def f_cta_panic(obs, asof, p, freq, cache=None):
    t = _cta_states(obs, asof, freq, cache)
    only = {"short": -1, "long": 1}.get(p.get("only") or "", 0)   # live agent 8 flags it on a with-trend short only
    return _rows([{"date": r.date, "market": r.market, "source": r.market,
                   "on": bool(r.panic) and bool(r.s12) and (not only or _sgn(r.s12) == only),
                   "side": _sgn(r.s12) or 1} for r in t.itertuples()])


@flag("turbulence_persistent", 8, 1, "agent 8 turbulence warning: Mahalanobis turbulence of the universe in its top 20% "
      "(last ~3 years) on 3 of the last 5 days, covariance from data up to that day; scored on params.market "
      "(default ES=F) with side +1 (long)", "long params.market")
def f_turbulence(obs, asof, p, freq, cache=None):
    from . import risk
    rc = risk.cfg()
    m = p.get("market", "ES=F")
    uni = list(rc["universe"])
    lr = returns(obs, uni, asof)
    tb = rc["turbulence"]
    rows = []
    if lr.empty:
        return _rows(rows)
    for d in grid_dates(lr.index[0] + pd.Timedelta(days=3 * 365), asof, freq):
        x = lr[lr.index <= d]
        u = [k for k in uni if k in x.columns and x[k].notna().sum() >= rc["min_days"]]
        if len(u) < 2:
            continue
        full = x[u].dropna()
        if len(full) < max(rc["min_days"], tb["persist_days"] + 1) or (d - full.index[-1]).days > 5:
            continue
        a = full.values
        dev = a - a.mean(0)
        inv = np.linalg.pinv(np.cov(a, rowvar=False))
        turb = pd.Series(np.einsum("ij,jk,ik->i", dev, inv, dev) / len(u), index=full.index)
        t = turb.tail(tb.get("warning_window_days", 756))
        cut = float(np.percentile(t, tb["stress_pct"]))
        hot = int((t.tail(tb["persist_days"]) >= cut).sum())
        rows.append({"date": d, "market": m, "source": "turbulence", "on": hot >= tb["persist_min"], "side": 1})
    return _rows(rows)


# ------------------------------------------------------------------ event study
def episodes(ev: pd.DataFrame, cal: pd.DatetimeIndex, gap: int) -> pd.DataFrame:
    """Collapse 'on' rows into independent episodes per (source, market, side): a new episode starts only when the same
    key was last on more than `gap` trading days earlier, so no two episodes share a forward window."""
    on = ev[ev["on"].astype(bool)].reset_index(drop=True)     # unique labels: a concatenated frame repeats them
    if on.empty:
        return on.assign(pos=pd.Series(dtype=int))
    on["pos"] = cal.searchsorted(pd.DatetimeIndex(on["date"]), side="right") - 1   # last calendar day <= signal date
    on = on[on.pos >= 0].sort_values(["source", "market", "side", "pos"])
    keep = []
    for _, g in on.groupby(["source", "market", "side"], sort=False):
        last = None
        for i, pos in zip(g.index, g.pos):
            if last is None or pos - last > gap:
                keep.append(i)
            last = pos
    return on.loc[keep].sort_values("pos").reset_index(drop=True)


def _windows(ev: pd.DataFrame, cal: pd.DatetimeIndex) -> dict[str, tuple[int, int]]:
    """Evaluable calendar positions per market: from the first to the last grid date the flag was computed."""
    out = {}
    for m, g in ev.groupby("market"):
        d = pd.DatetimeIndex(g["date"])
        lo = int(cal.searchsorted(d.min(), side="left"))
        hi = int(cal.searchsorted(d.max(), side="right")) - 1
        if hi > lo:
            out[m] = (lo, hi)
    return out


def trend_dir(r: pd.Series, legs=(21, 63, 252)) -> np.ndarray:
    """Agent 7's trend vote on each calendar day from the return series (sign of the sum of the 1/3/12-month signs),
    known at that day's close; 0 where a leg is missing."""
    x = r.to_numpy(dtype=float)
    c = np.concatenate([[0.0], np.nancumsum(x)])
    n = np.concatenate([[0], np.cumsum(np.isfinite(x))])
    out = np.zeros(len(x), dtype=int)
    i = np.arange(len(x))
    vote = np.zeros(len(x))
    ok = np.ones(len(x), dtype=bool)
    for L in legs:
        j = i - L
        good = j >= 0
        ret = np.where(good, c[i + 1] - c[np.maximum(j, 0) + 1], np.nan)
        cnt = np.where(good, n[i + 1] - n[np.maximum(j, 0) + 1], 0)
        ok &= good & (cnt >= 0.8 * L)
        vote += np.sign(np.nan_to_num(ret))
    out[ok] = np.sign(vote[ok]).astype(int)
    return out


def min_detectable_lift(n: int, p0: float, alpha: float = 0.05, power: float = 0.8) -> float | None:
    """Smallest lift a one-sided binomial test on n episodes detects with the given power at base rate p0."""
    if n <= 0 or not 0 < p0 < 1:
        return None
    za, zb = qstats.norm_ppf(1 - alpha), qstats.norm_ppf(power)
    for p1 in np.linspace(p0 * 1.01, 0.999, 2000):
        need = ((za * math.sqrt(p0 * (1 - p0)) + zb * math.sqrt(p1 * (1 - p1))) / (p1 - p0)) ** 2
        if need <= n:
            return float(p1 / p0)
    return None


def bayes_p(p: float | None, odds: float) -> float | None:
    """Harvey (2017) Bayesianized p: minimum Bayes factor exp(-z^2/2) at prior odds null:alternative."""
    if p is None or not 0 < p < 1:
        return None
    z = qstats.norm_ppf(1 - p) if p < 0.5 else 0.0
    mbf = math.exp(-z * z / 2)
    return mbf * odds / (1 + mbf * odds)


def _stat(vals: np.ndarray, base: np.ndarray, binary: bool) -> float:
    if not len(vals):
        return float("nan")
    if binary:
        e = base.sum()
        return float(vals.sum() / e) if e > 0 else float("nan")
    return float(np.mean(vals - base))


def event_study(ev: pd.DataFrame, lr: pd.DataFrame, outcome: str, h: int, lag_days: int, c: dict,
                expected: int = 1, seed: int = 0, oos_from: str | None = None, split_date: str | None = None,
                paper: bool = False) -> dict:
    """Base rate, hit rate, lift (binary) or excess vol-scaled move (signed), on independent episodes, with a
    circular-shift placebo per source, chronological halves and the live (out-of-sample) episodes apart."""
    k, lam = float(c["k_sd"]), float(c["vol_lambda"])
    binary = outcome != "signed"
    markets = [m for m in ev["market"].unique() if m in lr.columns]
    ev = ev[ev["market"].isin(markets)]
    if lr.empty or ev.empty:
        return {"n_episodes": 0, "reason": "no flag rows or no price history for its markets"}
    cal = lr.index
    Z = {m: outcome_z(lr[m], h, lam, lag_days).to_numpy() for m in markets}
    win = _windows(ev, cal)
    base: dict[tuple[str, int], float] = {}
    n_base: dict[str, int] = {}
    for m, (lo, hi) in win.items():
        z = Z[m][lo:hi + 1]
        for s in (1, -1):
            v = hit(z, np.full(len(z), s), outcome, k)
            v = v[~np.isnan(v)]
            base[(m, s)] = float(v.mean()) if len(v) else float("nan")
        n_base[m] = int(np.isfinite(z).sum())
    ep = episodes(ev, cal, h)
    ep = ep[ep.market.isin(win)]

    mkeys = sorted(win)
    Zm = np.vstack([Z[m] for m in mkeys]) if mkeys else np.zeros((0, len(cal)))

    def score(e: pd.DataFrame, pos: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        pos = e.pos.to_numpy() if pos is None else pos
        mi = np.array([mkeys.index(m) for m in e.market], dtype=int)
        sd = e.side.to_numpy().astype(int)
        v = hit(Zm[mi, pos] if len(mi) else np.array([]), sd, outcome, k)
        b = np.array([base.get((m, s if s else 1), np.nan) for m, s in zip(e.market, sd)])
        ok = np.isfinite(v) & np.isfinite(b)
        return v[ok], b[ok], ok

    v, b, ok = score(ep)
    ep = ep[ok].reset_index(drop=True)
    _mi = np.array([mkeys.index(m) for m in ep.market], dtype=int)
    _sd = ep.side.to_numpy().astype(int)
    _b = b.copy()

    def score_fast(pos: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        vv = hit(Zm[_mi, pos], _sd, outcome, k)
        okk = np.isfinite(vv)
        return vv[okk], _b[okk]
    n = int(len(v))
    res = {"n_episodes": n, "n_flag_rows": int(len(ev)), "n_on_rows": int(ev["on"].astype(bool).sum()),
           "n_sources": int(ep.source.nunique()) if n else 0, "markets": sorted(win),
           "n_clusters": int(ep.groupby(["source", "pos"]).ngroups) if n else 0,
           "window": {m: [str(cal[a].date()), str(cal[z].date())] for m, (a, z) in win.items()},
           "base_days": n_base, "outcome": outcome, "horizon_days": h, "k_sd": k, "lag_days": lag_days,
           "binary": binary}
    if not n:
        res["reason"] = "the flag never fired with a complete forward window"
        return res
    stat = _stat(v, b, binary)
    g = c["gate"]
    cut_ = float(g["decay_haircut_paper"] if paper else g["decay_haircut"])
    n0 = float(g.get("shrink_n0", 20))
    years = (cal[max(hi for _, hi in win.values())] - cal[min(lo for lo, _ in win.values())]).days / 365.25
    res.update({"first_episode": str(cal[ep.pos.min()].date()), "last_episode": str(cal[ep.pos.max()].date()),
                "episodes_per_year": _r(n / years if years > 0 else None, 2), "decay_haircut": cut_})
    # the same outcome against days in the same trend state (positions follow trends: Sanders, Irwin & Merrin)
    TD = {m: trend_dir(lr[m]) for m in win}
    base_t: dict[tuple[str, int, int], float] = {}
    for m, (lo, hi) in win.items():
        z, td = Z[m][lo:hi + 1], TD[m][lo:hi + 1]
        for s in (1, -1):
            v_ = hit(z, np.full(len(z), s), outcome, k)
            for t in (-1, 0, 1):
                w = v_[(td * s == t) & np.isfinite(v_)]
                base_t[(m, s, t)] = float(w.mean()) if len(w) >= 30 else float("nan")
    bt = np.array([base_t.get((m, int(s), int(TD[m][p] * s)), np.nan) for m, s, p in zip(ep.market, ep.side, ep.pos)])
    okt = np.isfinite(bt)
    if okt.sum() >= max(5, 0.8 * n):
        res["trend_matched"] = {"n": int(okt.sum()), "stat": _r(_stat(v[okt], bt[okt], binary), 3),
                                "with_trend_share": _r(float(np.mean([TD[m][p] * s > 0 for m, s, p in
                                                                      zip(ep.market, ep.side, ep.pos)])), 3)}
    if binary:
        exp_ = float(b.sum())
        var = float((b * (1 - b)).sum())
        p0 = float(b.mean())
        res.update({"hits": int(v.sum()), "expected_hits": _r(exp_, 2), "hit_rate": _r(v.mean(), 4),
                    "base_rate": _r(p0, 4), "lift": _r(stat, 3),
                    "lift_shrunk": _r((v.sum() + n0 * p0) / (exp_ + n0 * p0), 3),
                    "z_binomial": _r((v.sum() - exp_) / math.sqrt(var) if var > 0 else None, 2),
                    "lift_haircut": _r(1 + (stat - 1) * (1 - cut_), 3),
                    "min_detectable_lift": _r(min_detectable_lift(n, p0), 2)})
        lo_, hi_ = wilson(int(v.sum()), n)
        res["hit_rate_wilson"] = [_r(lo_, 4), _r(hi_, 4)]
    else:
        d = v - b
        sd = float(d.std(ddof=1)) if n > 1 else float("nan")
        res.update({"mean_signed_sd": _r(v.mean(), 3), "base_signed_sd": _r(b.mean(), 3), "excess_sd": _r(stat, 3),
                    "excess_shrunk_sd": _r(stat * n / (n + n0), 3),
                    "t_episodes": _r(stat / (sd / math.sqrt(n)) if n > 1 and sd > 0 else None, 2),
                    "excess_haircut_sd": _r(stat * (1 - cut_), 3),
                    "min_detectable_sd": _r((qstats.norm_ppf(0.95) + qstats.norm_ppf(0.8)) * sd / math.sqrt(n)
                                            if n > 1 and sd > 0 else None, 3),
                    "share_positive": _r((v > 0).mean(), 3)})
    # influence: the effect with each calendar year of episodes removed (Lan et al. 2025)
    yrs = np.array([cal[p].year for p in ep.pos])
    if len(set(yrs)) >= 3:
        drops = {int(y): _stat(v[yrs != y], b[yrs != y], binary) for y in sorted(set(yrs))}
        res["drop_year"] = {"min": _r(min(drops.values()), 3), "max": _r(max(drops.values()), 3),
                            "min_year": min(drops, key=drops.get), "max_year": max(drops, key=drops.get)}
    # circular-shift placebo, one random offset per source (its markets move together; clustering is kept)
    # placebo: ONE circular shift of the calendar per draw, the same for every source and market, so episodes that
    # coincide (several narratives on one market and Friday; correlated markets flagging together) stay together and
    # the null keeps the flag's clustering (review, finding 1: per-source shifts rejected a copied null flag 23% of
    # the time at 5%)
    rng = np.random.default_rng(seed)
    reps, mins = int(c["gate"]["placebo_reps"]), int(c["gate"]["placebo_min_shift"])
    null = []
    LO = min(lo for lo, _ in win.values())
    L = max(hi for _, hi in win.values()) - LO + 1
    p0 = ep.pos.to_numpy()
    for _ in range(reps):
        u = int(rng.integers(mins, L - mins)) if L > 2 * mins else (int(rng.integers(1, L)) if L > 1 else 0)
        vv, bb = score_fast(LO + (p0 - LO + u) % L)
        null.append(_stat(vv, bb, binary))
    null = np.array([x for x in null if np.isfinite(x)])
    centre = 1.0 if binary else 0.0
    if len(null):
        p_up = (1 + int((null >= stat).sum())) / (1 + len(null))
        p_dn = (1 + int((null <= stat).sum())) / (1 + len(null))
        if expected > 0:
            p, p_opp = p_up, p_dn
        elif expected < 0:
            p, p_opp = p_dn, p_up
        else:
            mid = float(np.median(null))
            p = (1 + int((np.abs(null - mid) >= abs(stat - mid)).sum())) / (1 + len(null))
            p_opp = None
        res.update({"p_placebo": _r(p, 4), "p_opposite": _r(p_opp, 4), "placebo_reps": int(len(null)),
                    "placebo_median": _r(np.median(null), 3), "placebo_p05": _r(np.percentile(null, 5), 3),
                    "placebo_p95": _r(np.percentile(null, 95), 3),
                    # a two-sided p is halved to its one-sided z (review, finding 15)
                    "bayes_p": {f"{o}:1": _r(bayes_p(p if expected else p / 2, float(o)), 3)
                                for o in g.get("prior_odds", [4, 1])}})
    # chronological halves (by episode date)
    if n >= 4:
        cut = int(np.median(ep.pos)) if split_date is None else int(cal.searchsorted(pd.Timestamp(split_date)))
        h1, h2 = ep.pos.to_numpy() <= cut, ep.pos.to_numpy() > cut
        s1, s2 = _stat(v[h1], b[h1], binary), _stat(v[h2], b[h2], binary)
        res["halves"] = {"split": str(cal[min(cut, len(cal) - 1)].date()), "n": [int(h1.sum()), int(h2.sum())],
                         "stat": [_r(s1), _r(s2)]}
    if oos_from:
        live = ep.pos.to_numpy() >= cal.searchsorted(pd.Timestamp(oos_from))
        res["live"] = {"from": oos_from, "n": int(live.sum()),
                       "stat": _r(_stat(v[live], b[live], binary)) if live.any() else None}
    res["stat"] = _r(stat, 4)
    res["stat_name"] = "lift" if binary else "excess_sd"
    res["centre"] = centre
    res["episode_dates"] = [[str(cal[p].date()), m, int(s), str(src)]
                            for p, m, s, src in zip(ep.pos, ep.market, ep.side, ep.source)]
    return res


# ------------------------------------------------------------------ statistics for the gate
def holm(pvals: dict[str, float]) -> dict[str, float]:
    """Holm step-down adjusted p-values (family-wise error), monotone."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, run = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def bh(pvals: dict[str, float]) -> dict[str, float]:
    """Benjamini-Hochberg q-values (false discovery rate)."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, run = len(items), {}, 1.0
    for i in range(m - 1, -1, -1):
        k, p = items[i]
        run = min(run, p * m / (i + 1))
        out[k] = min(1.0, run)
    return out


def psr(sr: float, sr_star: float, n: int, skew: float, kurt: float) -> float:
    """Probabilistic Sharpe ratio (Bailey & Lopez de Prado 2012): P(true SR > sr_star); per-period SR, kurt not excess."""
    den = 1 - skew * sr + (kurt - 1) / 4 * sr ** 2
    if n < 2 or den <= 0:
        return float("nan")
    return qstats.norm_cdf((sr - sr_star) * math.sqrt(n - 1) / math.sqrt(den))


def expected_max_sr(n_trials: int, var_sr: float) -> float:
    """E[max SR] of n_trials unskilled strategies (Bailey & Lopez de Prado 2014, eq. for SR0)."""
    if n_trials < 2 or var_sr <= 0:
        return 0.0
    return math.sqrt(var_sr) * ((1 - EULER) * qstats.norm_ppf(1 - 1 / n_trials)
                                + EULER * qstats.norm_ppf(1 - 1 / (n_trials * math.e)))


def dsr(sr: float, n: int, skew: float, kurt: float, n_trials: int, var_sr: float) -> dict:
    sr0 = expected_max_sr(n_trials, var_sr)
    return {"sr0": _r(sr0, 4), "dsr": _r(psr(sr, sr0, n, skew, kurt), 4), "n_trials": n_trials}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - w, c + w


# ------------------------------------------------------------------ strategy: time-series momentum
def cost_bps(market: str, when: pd.Timestamp, c: dict) -> float:
    """One-way cost in bps of notional (Hurst, Ooi & Pedersen's AQR table): by asset class, x2 for 1993-2002 and
    x6 before 1993; roll costs are not in it."""
    st = c["strategy"]
    b = float(st["costs_bps"][st.get("asset_class", {}).get(market, "commodity")])
    return b * (6.0 if when.year < 1993 else 2.0 if when.year < 2003 else 1.0)


def tsmom(lr: pd.DataFrame, lookback: int, c: dict, cost_x: float = 1.0, mode: str = "tsmom") -> pd.DataFrame:
    """Monthly time-series momentum (Moskowitz, Ooi & Pedersen 2012): at each month end, each market's position is the
    sign of its past `lookback`-day return times target_vol / ex-ante vol (EWMA, centre of mass 60 days, known at the
    month end); held over the next month; the book is the average across the markets that have a position.
    mode 'long' = always long (the beta benchmark); 'drift' = the sign of the market's mean daily return since its
    first close, i.e. the historical-mean strategy that Huang, Li, Wang & Zhou (2020) say TSMOM is no better than.
    Cost = cost_x x the AQR one-way bps x change in position, charged at the rebalance."""
    st = c["strategy"]
    com = float(st["vol_com_days"])
    tgt = float(st["target_vol"])
    me = lr.groupby(lr.index.to_period("M")).apply(lambda g: g.index[-1])
    me = pd.DatetimeIndex(me.values)
    var = lr.pow(2).ewm(com=com, min_periods=60).mean()
    vol = np.sqrt(261 * var)
    cum = lr.fillna(0).cumsum()
    cnt = lr.notna().cumsum()
    rows, prev = [], {}
    for a, b in zip(me[:-1], me[1:]):
        nxt = lr[(lr.index > a) & (lr.index <= b)]
        rets, costs, pos_now = [], [], {}
        ia = lr.index.get_loc(a)
        for m in lr.columns:
            if ia < lookback or cnt[m].iloc[ia] - cnt[m].iloc[ia - lookback] < 0.8 * lookback:
                continue
            sv = vol[m].iloc[ia]
            seen = lr[m].iloc[:ia + 1].last_valid_index()     # in the book only if it traded in the last 5 days
            if not np.isfinite(sv) or sv <= 0 or seen is None or (a - seen).days > 5:
                continue
            if mode == "long":
                sgn = 1.0
            elif mode == "drift":
                mu = cum[m].iloc[ia] / max(1, cnt[m].iloc[ia])
                sgn = 1.0 if mu > 0 else -1.0 if mu < 0 else 0.0
            else:
                past = cum[m].iloc[ia] - cum[m].iloc[ia - lookback]
                sgn = 1.0 if past > 0 else -1.0 if past < 0 else 0.0
            w = sgn * tgt / sv
            pos_now[m] = w
            r = math.exp(float(nxt[m].fillna(0).sum())) - 1
            rets.append(w * r)
            costs.append(abs(w - prev.get(m, 0.0)) * cost_x * cost_bps(m, a, c) / 1e4)
        for m in set(prev) - set(pos_now):                    # a market that leaves the book pays its exit
            costs.append(abs(prev[m]) * cost_x * cost_bps(m, a, c) / 1e4)
        if rets:
            rows.append({"month": b, "ret": float(np.mean(rets)) - float(np.sum(costs)) / len(rets), "n": len(rets),
                         "turnover": float(np.mean([abs(pos_now[m] - prev.get(m, 0.0)) for m in pos_now]))})
        prev = pos_now
    return pd.DataFrame(rows, columns=["month", "ret", "n", "turnover"]).set_index("month")


def _moments(r: pd.Series) -> dict:
    x = r.dropna().to_numpy()
    n = len(x)
    if n < 3 or x.std(ddof=1) == 0:
        return {"n": n}
    sd = x.std(ddof=1)
    sr = x.mean() / sd
    skew = float(((x - x.mean()) ** 3).mean() / x.std() ** 3)
    kurt = float(((x - x.mean()) ** 4).mean() / x.std() ** 4)
    return {"n": n, "mean_m": float(x.mean()), "sd_m": float(sd), "sr_m": float(sr), "skew": skew, "kurt": kurt,
            "ann_ret": _r(12 * x.mean(), 4), "ann_vol": _r(math.sqrt(12) * sd, 4), "sharpe": _r(math.sqrt(12) * sr, 3)}


def alpha_beta(y: pd.Series, x: pd.Series) -> dict:
    j = pd.concat([y.rename("y"), x.rename("x")], axis=1).dropna()
    if len(j) < 24:
        return {}
    r = qstats.ols(j["y"].to_numpy(), j["x"].to_numpy(), nw=qstats.nw_lags(len(j)))
    return {"alpha_ann": _r(12 * r["beta"][0], 4), "t_alpha": _r(r["t"][0], 2), "beta": _r(r["beta"][1], 3),
            "t_beta": _r(r["t"][1], 2), "n_months": int(r["n"])}


def _monthly(r: pd.Series) -> pd.Series:
    """Daily log returns -> simple monthly returns indexed by the month's last calendar day in the series."""
    x = r.dropna()
    g = x.groupby(x.index.to_period("M"))
    out = np.exp(g.sum()) - 1
    out.index = pd.DatetimeIndex([grp.index[-1] for _, grp in g])
    return out


def _align(y: pd.Series, x: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Match two monthly series by calendar month."""
    a = y.copy()
    b = x.copy()
    a.index, b.index = a.index.to_period("M"), b.index.to_period("M")
    return a, b


def strategy_study(spec: dict, lr: pd.DataFrame, c: dict, n_trials_total: int, sr_trials: list[float]) -> dict:
    """A trading replication (only time-series momentum is coded): variants, alpha against the long-only book of the
    same markets and against the historical-mean strategy, deflated Sharpe over every registered variant, the AQR cost
    table swept at 0-4x, the paper's sample vs after it vs after publication, and chronological halves."""
    p = spec.get("params") or {}
    if spec.get("strategy") != "tsmom":
        raise ValueError(f"unknown strategy {spec.get('strategy')!r} (known: tsmom)")
    st = c["strategy"]
    looks = [int(x) for x in p.get("lookbacks", [21, 63, 252])]
    primary = int(p.get("primary", 252))
    out: dict = {"variants": {}, "markets": list(lr.columns),
                 "history_since": {m: str(lr[m].first_valid_index().date()) for m in lr.columns
                                   if lr[m].first_valid_index() is not None}}
    bench = tsmom(lr, primary, c, cost_x=0.0, mode="long")["ret"]
    drift = tsmom(lr, primary, c, cost_x=1.0, mode="drift")["ret"]
    prim = prim_mo = None
    for L in looks:
        r = tsmom(lr, L, c, cost_x=1.0)
        mo = _moments(r["ret"])
        out["variants"][str(L)] = {k: v for k, v in mo.items() if k in ("n", "ann_ret", "ann_vol", "sharpe")}
        out["variants"][str(L)]["turnover_m"] = _r(r["turnover"].mean(), 3)
        if L == primary:
            prim, prim_mo = r, mo
    if prim is None or prim_mo.get("n", 0) < 24:
        raise ValueError("fewer than 24 months of strategy returns")
    out["primary"] = {k: v for k, v in prim_mo.items() if k in ("n", "ann_ret", "ann_vol", "sharpe")}
    out["primary"]["skew"], out["primary"]["kurt"] = _r(prim_mo.get("skew"), 3), _r(prim_mo.get("kurt"), 3)
    out["primary"]["from"], out["primary"]["to"] = str(prim.index[0].date()), str(prim.index[-1].date())
    out["alpha_vs_long_only"] = alpha_beta(prim["ret"], bench)
    out["alpha_vs_drift"] = alpha_beta(prim["ret"], drift)
    out["drift_benchmark"] = {k: v for k, v in _moments(drift).items() if k in ("n", "ann_ret", "sharpe")}
    out["long_only_benchmark"] = {k: v for k, v in _moments(bench).items() if k in ("n", "ann_ret", "sharpe")}
    if "ES=F" in lr.columns:
        y, x = _align(prim["ret"], _monthly(lr["ES=F"]))
        out["alpha_vs_sp500"] = alpha_beta(y, x)
    # deflated Sharpe: every registered variant is a trial; V[SR] floored while the class has under 10 trials
    srs = [v for v in sr_trials if np.isfinite(v)]
    floor = float(st.get("var_sr_floor_ann", 0.5)) / 12
    var_sr = float(np.var(srs, ddof=1)) if len(srs) >= 2 else 0.0
    if len(srs) < 10:
        var_sr = max(var_sr, floor)
    out["deflated"] = dsr(prim_mo["sr_m"], prim_mo["n"], prim_mo["skew"], prim_mo["kurt"], max(n_trials_total, 1), var_sr)
    out["deflated"]["var_sr"] = _r(var_sr, 6)
    out["deflated"]["var_sr_floored"] = len(srs) < 10
    out["psr_vs_0"] = _r(psr(prim_mo["sr_m"], 0.0, prim_mo["n"], prim_mo["skew"], prim_mo["kurt"]), 4)
    # costs: AQR table x 0..4, break-even multiple
    sweep = []
    for cx in st["cost_multipliers"]:
        rr = tsmom(lr, primary, c, cost_x=float(cx))["ret"]
        m2 = _moments(rr)
        sweep.append({"cost_x": cx, "sharpe": m2.get("sharpe"), "ann_ret": m2.get("ann_ret"),
                      "t_alpha": alpha_beta(rr, bench).get("t_alpha")})
    out["cost_sweep"] = sweep
    g0 = next((x["ann_ret"] for x in sweep if x["cost_x"] == 0), None)
    g1 = next((x["ann_ret"] for x in sweep if x["cost_x"] == 1), None)
    out["break_even_cost_x"] = _r(g0 / (g0 - g1) if g0 is not None and g1 is not None and g0 > g1 else None, 1)
    # periods: paper sample, after the sample, after publication (McLean & Pontiff)
    paper = spec.get("paper") or {}
    per = {}
    edges = [("in_paper_sample", None, paper.get("sample_end")),
             ("after_sample_before_pub", paper.get("sample_end"), paper.get("published")),
             ("after_publication", paper.get("published"), None)]
    for name, a, b in edges:
        rr = prim["ret"]
        if a:
            rr = rr[rr.index > pd.Timestamp(str(a))]
        if b:
            rr = rr[rr.index <= pd.Timestamp(str(b))]
        m3 = _moments(rr)
        per[name] = {"from": str(a) if a else str(prim.index[0].date()), "to": str(b) if b else str(prim.index[-1].date()),
                     "months": m3.get("n", 0), "sharpe": m3.get("sharpe"), "ann_ret": m3.get("ann_ret")}
    out["periods"] = per
    half = len(prim) // 2
    out["halves"] = {"split": str(prim.index[half].date()),
                     "sharpe": [_moments(prim["ret"].iloc[:half]).get("sharpe"), _moments(prim["ret"].iloc[half:]).get("sharpe")]}
    out["sr_m"] = prim_mo["sr_m"]
    return out



# ------------------------------------------------------------------ registry, ledger
def spec_hash(spec: dict) -> str:
    keep = {k: v for k, v in spec.items() if not k.startswith("_")}
    return hashlib.sha256(json.dumps(keep, sort_keys=True, default=str).encode()).hexdigest()[:16]


def validate(spec: dict) -> list[str]:
    errs = [f"missing field: {k}" for k in REQUIRED if not spec.get(k)]
    if spec.get("kind") not in KINDS:
        errs.append(f"kind must be one of {sorted(KINDS)}")
    sid = str(spec.get("id") or "")
    if sid and not all(ch.isalnum() or ch in "_-" for ch in sid):
        errs.append("id: letters, digits, _ and - only")
    if spec.get("kind") == "flag":
        if spec.get("flag") not in FLAGS:
            errs.append(f"flag must be one of {sorted(FLAGS)}")
        if spec.get("outcome") not in OUTCOMES:
            errs.append(f"outcome must be one of {sorted(OUTCOMES)}")
        if spec.get("expected") not in (-1, 0, 1):
            errs.append("expected must be -1, 0 or 1 (registered direction; 0 = two-sided)")
    if spec.get("kind") == "strategy" and spec.get("strategy") != "tsmom":
        errs.append("strategy must be tsmom (the only one coded)")
    if spec.get("llm_feature") and not spec.get("kind") == "flag":
        errs.append("llm_feature applies to flags only")
    for k in ("figures", "result", "lift", "verdict"):
        if k in spec:
            errs.append(f"a registration carries no results ({k!r}): code computes them")
    return errs


def load_studies(root: Path | None = None) -> dict[str, dict]:
    P = paths(root)
    out = {}
    for f in sorted(P["studies"].glob("*.yaml")):
        s = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        s["_path"] = str(f)
        out[str(s.get("id"))] = s
    return out


def load_results(root: Path | None = None) -> list[dict]:
    """The latest result of every registered study (research/results/<id>.json); other files there (an auditor's
    sidecar, a stray copy) are ignored."""
    P = paths(root)
    out = []
    for sid in load_studies(root):
        f = P["results"] / f"{sid}.json"
        if f.exists():
            try:
                r = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("id") == sid and r.get("kind") in KINDS:
                out.append(r)
    return out


def ledger(root: Path | None = None) -> list[dict]:
    f = paths(root)["ledger"]
    if not f.exists():
        return []
    return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]


def frozen_hash(sid: str, root: Path | None = None) -> str | None:
    """The hash recorded when the study was registered (or first run, for a study registered by hand)."""
    for rec in ledger(root):
        if rec.get("id") == sid:
            return rec.get("spec_hash")
    return None


def runs(root: Path | None = None) -> list[dict]:
    """Written runs (the first 19 Oct runs carry no event field); registrations, peeks and verdict events apart."""
    return [r for r in ledger(root) if r.get("event") in (None, "run")]


def register(spec: dict, root: Path | None = None) -> Path:
    errs = validate(spec)
    if errs:
        raise ValueError("; ".join(errs))
    P = paths(root)
    f = P["studies"] / f"{spec['id']}.yaml"
    if f.exists() or frozen_hash(spec["id"], root):
        raise ValueError(f"{spec['id']} exists: a registration is never edited; use a new id (_vN)")
    P["studies"].mkdir(parents=True, exist_ok=True)
    f.write_text(yaml.safe_dump({k: v for k, v in spec.items() if not k.startswith("_")}, sort_keys=False,
                                allow_unicode=True), encoding="utf-8")
    back = yaml.safe_load(f.read_text(encoding="utf-8"))      # hash what run_study will read back
    _append_ledger({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "event": "register",
                    "id": spec["id"], "kind": spec["kind"], "spec_hash": spec_hash(back)}, root)
    return f


def _append_ledger(rec: dict, root: Path | None = None) -> None:
    f = paths(root)["ledger"]
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, default=str, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------ run one study
def definition_hash(spec: dict, c: dict) -> str:
    """What defines a study besides its registration (review, finding 6): the loop's outcome and gate settings, the
    agents' own thresholds it replays, and the source of the code that computes the flag and the outcome. A change
    after the first hashed run means the result was not produced by the rule as first run: it cannot be supported."""
    import inspect
    from . import consensus, risk
    keys = ["horizon_days", "vol_lambda", "grid", "k_sd", "gate", "hindsight"]
    if spec["kind"] == "strategy":
        keys.append("strategy")
    parts = {k: c.get(k) for k in keys}
    mon = yaml.safe_load((ROOT / "config" / "monitor.yaml").read_text(encoding="utf-8"))
    rk = yaml.safe_load((ROOT / "config" / "risk.yaml").read_text(encoding="utf-8"))
    parts["agents"] = {"consensus": mon.get("consensus"), "cftc": mon.get("cftc"),
                       **{k: rk.get(k) for k in ("universe", "history", "turbulence", "crowding", "funding", "cta",
                                                 "vol_lambda", "min_days")}}
    fns = [outcome_z, hit, returns, risk.history]
    if spec["kind"] == "flag":
        fns += [FLAGS[spec["flag"]]["fn"], narrative_stages, cftc_table, cftc_release, _label_table, _cta_states,
                consensus.stage_of, consensus.valid_days, consensus.trend, consensus.positioning, consensus._label,
                risk.cta_levels, risk.funding]
    else:
        fns += [tsmom, cost_bps, strategy_study]
    src = "".join(inspect.getsource(f) for f in fns)
    blob = json.dumps(parts, sort_keys=True, default=str) + src
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def frozen_definition(sid: str, root: Path | None = None) -> str | None:
    for rec in ledger(root):
        if rec.get("id") == sid and rec.get("definition_hash") and rec.get("event") in (None, "run"):
            return rec["definition_hash"]
    return None


def hindsight_of(spec: dict, c: dict) -> str | None:
    for h in c.get("hindsight") or []:
        if h.get("flag") == spec.get("flag") and all((spec.get("params") or {}).get(k) == v
                                                      for k, v in (h.get("params") or {}).items()):
            return str(h["date"])
    return None


def run_study(spec: dict, obs: pd.DataFrame, asof: date, root: Path | None = None, c: dict | None = None,
              cache: dict | None = None, write: bool = True, run_id: str | None = None) -> dict:
    """Run a registered study on data up to `asof`. The spec must match the hash recorded at registration; a run
    that writes nothing is still logged as a peek (review, finding 7)."""
    c = c or cfg()
    errs = validate(spec)
    if errs:
        raise ValueError("; ".join(errs))
    h = spec_hash(spec)
    old = frozen_hash(spec["id"], root)
    if old is None:
        raise ValueError(f"{spec['id']} is not registered: `python -m pmstack research new <file>` first")
    if old != h:
        raise ValueError(f"{spec['id']}: the registration changed after it was registered (hash {old} -> {h}); "
                         "register the change under a new id (_vN)")
    dh = definition_hash(spec, c)
    fd = frozen_definition(spec["id"], root)
    obs = obs[obs.date <= asof]
    res: dict = {"id": spec["id"], "title": spec["title"], "kind": spec["kind"], "asof": str(asof), "spec_hash": h,
                 "registered": str(spec["registered"]), "hypothesis": spec["hypothesis"], "source": spec["source"],
                 "agent": spec.get("agent"), "computed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if spec["kind"] == "flag":
        F = FLAGS[spec["flag"]]
        hz = int(spec.get("horizon_days") or c["horizon_days"])
        ev = F["fn"](obs, asof, spec.get("params") or {}, c["grid"], cache)
        if spec.get("llm_feature"):                     # memorisation: an LLM-made feature counts only after the boundary
            ev = ev[pd.DatetimeIndex(ev["date"]) > pd.Timestamp(c["llm_boundary"])]
            res["scored_after"] = c["llm_boundary"]
        mk = sorted(ev["market"].unique()) if len(ev) else []
        lr = returns(obs, mk, asof) if mk else pd.DataFrame()
        oos = spec.get("oos_from") or (c.get("oos") or {}).get(f"agent{spec.get('agent')}")
        es = event_study(ev, lr, spec["outcome"], hz, F["lag_days"], c, expected=int(spec["expected"]),
                         seed=int(spec.get("seed", 0)), oos_from=oos, paper=bool(spec.get("paper")))
        res.update({"flag": spec["flag"], "params": spec.get("params") or {}, "flag_doc": F["doc"],
                    "side_meaning": F["sides"], "expected": int(spec["expected"]), "paper": bool(spec.get("paper")),
                    "hindsight": hindsight_of(spec, c), **es})
    else:
        mk = (spec.get("params") or {}).get("markets") or []
        lr = returns(obs, mk, asof)
        trials = [r for r in runs(root) if r.get("kind") == "strategy" and r.get("id") != spec["id"]]
        n_var = len((spec.get("params") or {}).get("lookbacks", [21, 63, 252]))
        n_total = n_var + sum(int(r.get("n_variants", 1)) for r in {r["id"]: r for r in trials}.values())
        sr_trials = [s for r in {r["id"]: r for r in trials}.values() for s in (r.get("sr_variants") or [])]
        # this study's own variants enter the trial set
        own = []
        for L in [int(x) for x in (spec.get("params") or {}).get("lookbacks", [21, 63, 252])]:
            mo = _moments(tsmom(lr, L, c, cost_x=1.0)["ret"])
            own.append(mo.get("sr_m", float("nan")))
        ss = strategy_study(spec, lr, c, n_total, sr_trials + own)
        res.update({"strategy": spec["strategy"], "params": spec.get("params") or {}, "paper": spec.get("paper"),
                    "n_variants": n_var, "sr_variants": [_r(x, 5) for x in own], **ss})
    res["recall_probe"] = spec.get("recall_probe")
    res["data_through"] = str(lr.index[-1].date()) if len(lr) else None
    res["definition_hash"] = dh
    res["definition_frozen"] = fd or dh
    res["env_changed"] = bool(fd and fd != dh)
    bnd = pd.Timestamp(c["llm_boundary"])
    if spec["kind"] == "flag":
        after = sum(1 for d in res.get("episode_dates") or [] if pd.Timestamp(d[0]) > bnd)
        n_ep = res.get("n_episodes") or 0
        first = ("its definition was written on " + res["hindsight"] + " with that history in view (verdict capped)"
                 if res.get("hindsight") else "the flag rule came from the literature and predates this test")
        res["llm_window"] = (f"LLM-in-sample: {n_ep - after} of {n_ep} episodes fall before the drafting model's "
                             f"boundary {c['llm_boundary']}; the model picked no number; {first}")
    else:
        res["llm_window"] = (f"LLM-in-sample: the whole history precedes the drafting model's boundary "
                             f"{c['llm_boundary']} (the paper and its result are in the model's memory; judge the "
                             "post-publication period)")
    # binding words for the number auditor: a summary that names the study's flag binds its figures to this file
    res["audit_subject"] = " ".join(str(x) for x in [spec["title"], spec.get("flag") or spec.get("strategy") or "",
                                                     *((spec.get("params") or {}).values() if spec["kind"] == "flag" else []),
                                                     "flag" if spec["kind"] == "flag" else "strategy momentum"])
    res["data_note"] = c["data"]["roll_note"] + (" Before the futures exist, spot and index proxies carry no roll or "
                                                 "carry return." if spec["kind"] == "strategy" else "")
    # provisional verdict: BH over every registered flag study (missing ones at p = 1); build_index rewrites it
    others = [r for r in load_results(root) if r["id"] != spec["id"]]
    _set_verdict(res, family(others + [res], c, list(load_studies(root))), c)
    rec = {"ts": res["computed_utc"], "run_id": run_id, "id": spec["id"], "kind": spec["kind"], "spec_hash": h,
           "definition_hash": dh, "asof": str(asof), "n_episodes": res.get("n_episodes"), "stat": res.get("stat"),
           "p": res.get("p_placebo"), "verdict": res["verdict"], "n_variants": res.get("n_variants"),
           "sr_variants": res.get("sr_variants")}
    if write:
        _write_result(res, c, root)
        _append_ledger({**rec, "event": "run"}, root)
    else:
        _append_ledger({**rec, "event": "peek"}, root)
    return res


def _set_verdict(res: dict, fam: dict, c: dict) -> None:
    f = fam.get(res["id"]) or {}
    res["family"] = ({k: f.get(k) for k in ("q_bh", "q_by", "q_bh_opposite", "p_holm", "hlz_pass", "family_size")}
                     if f else None)
    res["verdict"], res["reasons"] = (f["verdict"], f["reasons"]) if f else verdict(res, c)


def _write_result(res: dict, c: dict, root: Path | None = None) -> None:
    P = paths(root)
    P["results"].mkdir(parents=True, exist_ok=True)
    (P["results"] / f"{res['id']}.json").write_text(json.dumps(res, indent=1, default=str, ensure_ascii=False),
                                                    encoding="utf-8")
    (P["results"] / f"{res['id']}.md").write_text(render(res, c), encoding="utf-8")


# ------------------------------------------------------------------ verdicts
def verdict(res: dict, c: dict, q_bh: float | None = None, q_opp: float | None = None) -> tuple[str, list[str]]:
    """'supported' only when every gate rule holds; otherwise the failing rules are named.
    Flags: insufficient | supported | reversed | no edge. Strategies: supported | decayed | no edge.
    `q_bh` is the study's Benjamini-Hochberg q across the ledger (None until the index computes it)."""
    g = c["gate"]
    why: list[str] = []
    if res["kind"] == "strategy":
        st = c["strategy"]
        ab = res.get("alpha_vs_long_only") or {}
        ok = True
        if (ab.get("t_alpha") or 0) < st["min_alpha_t"]:
            ok = False
            why.append(f"alpha t {ab.get('t_alpha')} < {st['min_alpha_t']} vs the long-only book")
        d = (res.get("deflated") or {}).get("dsr")
        if d is None or d < st["min_dsr"]:
            ok = False
            why.append(f"deflated Sharpe {d} < {st['min_dsr']} ({(res.get('deflated') or {}).get('n_trials')} trials)")
        hv = (res.get("halves") or {}).get("sharpe") or [None, None]
        if not all(x is not None and x > 0 for x in hv):
            ok = False
            why.append(f"Sharpe not positive in both halves {hv}")
        two = next((x for x in res.get("cost_sweep") or [] if x.get("cost_x") == 2), None)
        if two is not None and not (two.get("ann_ret") or 0) > 0:
            ok = False
            why.append(f"no return left at 2x costs ({two.get('ann_ret')})")
        post = ((res.get("periods") or {}).get("after_publication") or {}).get("sharpe")
        pre = ((res.get("periods") or {}).get("in_paper_sample") or {}).get("sharpe")
        if post is not None and post <= 0:
            why.append(f"after publication Sharpe {post}")
            return ("decayed" if pre is not None and pre > 0 else "no edge"), why
        return ("supported" if ok else "no edge"), why
    n = res.get("n_episodes") or 0
    if n < g["min_episodes"]:
        mdl = res.get("min_detectable_lift")
        return "insufficient", [f"{n} independent episodes < {g['min_episodes']}"
                                + (f" (could detect only a lift of {mdl}+)" if mdl else "")]
    stat, centre, exp_ = res.get("stat"), res.get("centre", 1.0), res.get("expected", 1)
    p = res.get("p_placebo")
    if stat is None or p is None:
        return "insufficient", ["no placebo distribution"]
    sign = 1 if stat > centre else -1 if stat < centre else 0
    want = exp_ if exp_ else sign
    fails = _gate_fails(res, c, want, p, q_bh)
    if not fails:
        return _hindsight_cap(res, c, "supported", want)
    po = res.get("p_opposite")
    if exp_ and po is not None and po <= g["p_max"]:
        # the other direction faces the same gate: its own BH family, size, halves, drop-one-year (review, finding 3)
        opp = _gate_fails(res, c, -exp_, po, q_opp)
        if not opp:
            v, w = _hindsight_cap(res, c, "reversed", -exp_)
            return v, w + ["significant in the opposite direction to the registration; flipping it is a new "
                           "registration, judged on later data"]
        return "no edge", [f"leans the opposite way (placebo p {po}) but fails the gate there: " + "; ".join(opp)]
    return "no edge", fails


def _gate_fails(res: dict, c: dict, want: int, p: float, q: float | None) -> list[str]:
    """The gate rules for one direction (+1: lift above 1 / positive excess; -1: below), each failing rule named."""
    g = c["gate"]
    stat, centre = res.get("stat"), res.get("centre", 1.0)
    why = []
    if p > g["p_max"]:
        why.append(f"placebo p {p} > {g['p_max']}")
    if q is not None and q > g["fdr_q"]:
        why.append(f"BH q {_r(q, 4)} > {g['fdr_q']} across the ledger")
    if res.get("binary"):
        if not ((stat >= g["min_lift"]) if want > 0 else (stat <= 1 / g["min_lift"])):
            why.append(f"lift {_r(stat)} short of " + (f"{g['min_lift']}" if want > 0 else f"1/{g['min_lift']}"))
    elif want * stat < g["min_excess_sd"]:
        why.append(f"excess {_r(stat)} sd short of {want * g['min_excess_sd']:+}")
    if g.get("split_halves"):
        hs = (res.get("halves") or {}).get("stat") or [None, None]
        if not all(x is not None and (x - centre) * want > 0 for x in hs):
            why.append(f"halves disagree {hs}")
    if g.get("drop_year") and res.get("drop_year"):
        dy = res["drop_year"]
        worst = dy["min"] if want > 0 else dy["max"]
        if worst is None or (worst - centre) * want <= 0:
            why.append(f"gone without {dy['min_year'] if want > 0 else dy['max_year']} ({worst})")
    if res.get("env_changed"):
        why.append(f"definition changed since its first hashed run ({res.get('definition_frozen')} -> "
                   f"{res.get('definition_hash')}): re-register to judge it")
    if res.get("paper"):                                  # imported idea: the HLZ hurdle too (review, finding 8)
        t = res.get("z_binomial") if res.get("binary") else res.get("t_episodes")
        if t is None or t * want < g["hlz_t"]:
            why.append(f"t {t} short of {g['hlz_t']} (imported idea)")
    return why


def _hindsight_cap(res: dict, c: dict, v: str, want: int) -> tuple[str, list[str]]:
    """A flag whose definition was written after most of its history (the narrative queries and their market signs,
    Oct 2026) cannot be 'supported' or 'reversed' on that history alone: it needs the minimum number of live episodes
    after the definition date, with the same sign (review, finding 5; Lopez-Lira, Tang & Zhu)."""
    h = res.get("hindsight")
    if not h:
        return v, []
    lv = res.get("live") or {}
    n, st = lv.get("n") or 0, lv.get("stat")
    centre = res.get("centre", 1.0)
    if n >= c["gate"]["min_episodes"] and st is not None and (st - centre) * want > 0:
        return v, []
    return "in-sample only", [f"would be {v} on its history, but its definition was written on {h} with that history "
                              f"in view; {n} live episodes since (needs {c['gate']['min_episodes']} with the same sign)"]


def family(results: list[dict], c: dict, registered: list[str] | None = None) -> dict[str, dict]:
    """BH q (the gate), Holm and BY (reported) across every registered flag study: one with no valid result (not run,
    errored) or too few episodes counts with p = 1, because a test tried is a test counted (review, finding 9). The
    opposite direction gets its own BH family. Plus the signed HLZ t >= 3 reading."""
    by = {r["id"]: r for r in results if r.get("kind") == "flag"}
    ids = list(dict.fromkeys(list(registered or []) + list(by)))
    if not ids:
        return {}
    mn = c["gate"]["min_episodes"]

    def pv(key):
        out = {}
        for i in ids:
            r = by.get(i)
            x = None if r is None else r.get(key)
            out[i] = 1.0 if x is None or (r.get("n_episodes") or 0) < mn else float(x)
        return out
    pp, po = pv("p_placebo"), pv("p_opposite")
    ho, q, qo = holm(pp), bh(pp), bh(po)
    cm = sum(1 / i for i in range(1, len(ids) + 1))
    out = {}
    for i, r in by.items():
        t = r.get("z_binomial") if r.get("binary") else r.get("t_episodes")
        st, centre = r.get("stat"), r.get("centre", 1.0)
        want = r.get("expected") or (1 if st is not None and st > centre else -1)
        v, why = verdict(r, c, q_bh=q[i], q_opp=qo[i])
        out[i] = {"q_bh": _r(q[i], 4), "q_by": _r(min(1.0, q[i] * cm), 4), "q_bh_opposite": _r(qo[i], 4),
                  "p_holm": _r(ho[i], 4), "hlz_pass": bool(t is not None and t * want >= c["gate"]["hlz_t"]),
                  "family_size": len(ids), "verdict": v, "reasons": why}
    return out


# ------------------------------------------------------------------ writing
def _f(x, nd=2, pct=False):
    if x is None:
        return "-"
    if pct:
        return f"{100 * x:.{max(0, nd - 2)}f}%"
    return f"{x:.{nd}f}" if isinstance(x, float) else str(x)


def render(res: dict, c: dict) -> str:
    """The study's result page (research/results/<id>.md). Every figure is a field of the JSON beside it, so
    `python -m pmstack audit <page> --facts research/results/<id>.json` can check it."""
    fam = res.get("family") or {}
    L = [f"# {res['title']}", "",
         f"Study `{res['id']}` · registered {res['registered']} · spec {res['spec_hash']} · as of {res['asof']} (data "
         f"through {res.get('data_through')}) · definition {res.get('definition_hash')} · "
         f"verdict **{res['verdict']}**", "",
         f"**Hypothesis (registered).** {res['hypothesis']}", "", f"**Source.** {res['source']}", ""]
    if res["kind"] == "flag":
        L += [f"**Flag.** `{res['flag']}` {json.dumps(res.get('params') or {})}: {res.get('flag_doc')}. Side = "
              f"{res.get('side_meaning')}.",
              f"**Outcome.** `{res.get('outcome')}` over {res.get('horizon_days')} trading days from the first close "
              f"{res.get('lag_days')} day(s) after the signal date; large = {res.get('k_sd')} sd of an h-day move "
              f"(EWMA sd known on the signal date). Registered direction: {res.get('expected'):+d}.", ""]
        if not res.get("n_episodes"):
            L += [f"No episodes: {res.get('reason')}.", ""]
        else:
            L += ["| | value |", "|---|---|",
                  f"| independent episodes | {res['n_episodes']} ({res.get('n_clusters')} source-date clusters, "
                  f"{res.get('n_sources')} sources) |",
                  f"| first / last episode | {res.get('first_episode')} / {res.get('last_episode')} |",
                  f"| episodes a year | {_f(res.get('episodes_per_year'))} |"]
            if res.get("binary"):
                w = res.get("hit_rate_wilson") or [None, None]
                L += [f"| hits / expected | {res.get('hits')} / {_f(res.get('expected_hits'))} |",
                      f"| hit rate vs base rate | {_f(res.get('hit_rate'), 4, pct=True)} (95% {_f(w[0], 4, pct=True)} to "
                      f"{_f(w[1], 4, pct=True)}) vs {_f(res.get('base_rate'), 4, pct=True)} |",
                      f"| lift | {_f(res.get('lift'), 3)}; shrunk {_f(res.get('lift_shrunk'), 3)}; after the "
                      f"{int(round(100 * res.get('decay_haircut', 0)))}% decay haircut {_f(res.get('lift_haircut'), 3)} |",
                      f"| binomial z | {_f(res.get('z_binomial'))} |",
                      f"| smallest lift these episodes can detect (80% power) | {_f(res.get('min_detectable_lift'))} |"]
            else:
                L += [f"| mean side-signed move vs base | {_f(res.get('mean_signed_sd'), 3)} vs "
                      f"{_f(res.get('base_signed_sd'), 3)} sd |",
                      f"| excess | {_f(res.get('excess_sd'), 3)} sd; shrunk {_f(res.get('excess_shrunk_sd'), 3)}; after "
                      f"the {int(round(100 * res.get('decay_haircut', 0)))}% haircut {_f(res.get('excess_haircut_sd'), 3)} |",
                      f"| t (episodes) | {_f(res.get('t_episodes'))} |",
                      f"| smallest excess these episodes can detect (80% power) | {_f(res.get('min_detectable_sd'), 3)} sd |",
                      f"| share moving with the side | {_f(res.get('share_positive'), 3, pct=True)} |"]
            bp = res.get("bayes_p") or {}
            L += [f"| placebo p ({res.get('placebo_reps')} circular shifts) | {_f(res.get('p_placebo'), 4)} "
                  f"(placebo 5-95%: {_f(res.get('placebo_p05'), 3)} to {_f(res.get('placebo_p95'), 3)}) |",
                  f"| Bayesianized p (odds 4:1 / 1:1) | {_f(bp.get('4:1'), 3)} / {_f(bp.get('1:1'), 3)} |"]
            if fam:
                L.append(f"| across the ledger ({fam.get('family_size')} flag studies) | BH q {_f(fam.get('q_bh'), 4)}, "
                         f"BY q {_f(fam.get('q_by'), 4)}, Holm p {_f(fam.get('p_holm'), 4)}, t >= 3: "
                         f"{'yes' if fam.get('hlz_pass') else 'no'} |")
            hv = res.get("halves")
            if hv:
                L.append(f"| halves (split {hv['split']}) | {_f(hv['stat'][0], 3)} (n {hv['n'][0]}) · "
                         f"{_f(hv['stat'][1], 3)} (n {hv['n'][1]}) |")
            dy = res.get("drop_year")
            if dy:
                L.append(f"| one year dropped | {_f(dy['min'], 3)} (without {dy['min_year']}) to {_f(dy['max'], 3)} "
                         f"(without {dy['max_year']}) |")
            tm = res.get("trend_matched")
            if tm:
                L.append(f"| against days in the same trend state | {res['stat_name']} {_f(tm['stat'], 3)} "
                         f"({tm['n']} episodes; {_f(tm['with_trend_share'], 3, pct=True)} on the trend's side) |")
            lv = res.get("live")
            if lv:
                L.append(f"| live, since the rule was frozen ({lv['from']}) | {lv['n']} episodes"
                         + (f", {res['stat_name']} {_f(lv['stat'], 3)}" if lv.get("stat") is not None else "") + " |")
            L.append("")
    else:
        pr, ab = res.get("primary") or {}, res.get("alpha_vs_long_only") or {}
        ad, d = res.get("alpha_vs_drift") or {}, res.get("deflated") or {}
        L += [f"**Strategy.** `{res['strategy']}` {json.dumps(res.get('params') or {})}; markets: "
              f"{', '.join(res.get('markets') or [])}.", "",
              "| | value |", "|---|---|",
              f"| months | {pr.get('n')} ({pr.get('from')} to {pr.get('to')}) |",
              f"| annual return / vol / Sharpe (AQR costs) | {_f(pr.get('ann_ret'), 4, pct=True)} / "
              f"{_f(pr.get('ann_vol'), 4, pct=True)} / {_f(pr.get('sharpe'))} |",
              f"| alpha vs the long-only book (annual, HAC t, beta) | {_f(ab.get('alpha_ann'), 4, pct=True)} "
              f"(t {_f(ab.get('t_alpha'))}, beta {_f(ab.get('beta'), 3)}) |",
              f"| alpha vs the historical-mean strategy | {_f(ad.get('alpha_ann'), 4, pct=True)} (t {_f(ad.get('t_alpha'))}, "
              f"beta {_f(ad.get('beta'), 3)}) |"]
        sp = res.get("alpha_vs_sp500") or {}
        if sp:
            L.append(f"| alpha vs S&P 500 futures | {_f(sp.get('alpha_ann'), 4, pct=True)} (t {_f(sp.get('t_alpha'))}, "
                     f"beta {_f(sp.get('beta'), 3)}) |")
        L += [f"| deflated Sharpe ({d.get('n_trials')} trials) | {_f(d.get('dsr'), 4)} (expected best monthly SR of noise "
              f"{_f(d.get('sr0'), 4)}{'; V[SR] floored' if d.get('var_sr_floored') else ''}) |",
              f"| probabilistic Sharpe vs 0 | {_f(res.get('psr_vs_0'), 4)} |",
              f"| break-even cost | {_f(res.get('break_even_cost_x'), 1)}x the AQR table |"]
        for k, v in (res.get("periods") or {}).items():
            L.append(f"| {k.replace('_', ' ')} ({v['from']} to {v['to']}) | Sharpe {_f(v.get('sharpe'))}, {v.get('months')} months |")
        hv = res.get("halves") or {}
        L.append(f"| halves (split {hv.get('split')}) | Sharpe {_f((hv.get('sharpe') or [None])[0])} · "
                 f"{_f((hv.get('sharpe') or [None, None])[1])} |")
        L += ["", "Variants (all registered, all counted): " + "; ".join(
            f"{k} days: Sharpe {_f(v.get('sharpe'))}" for k, v in (res.get("variants") or {}).items()), "",
            "Cost sweep (x the AQR table): " + "; ".join(
                f"{x['cost_x']}x: Sharpe {_f(x['sharpe'])}, alpha t {_f(x['t_alpha'])}" for x in res.get("cost_sweep") or []), ""]
    rp = res.get("recall_probe")
    if rp:
        L += [f"**Recall probe (asked before the run).** {rp.get('question', '')} Answer: {rp.get('answer')} "
              f"({rp.get('prob')}).", ""]
    if res.get("hindsight"):
        L += [f"**Hindsight.** This flag's definition was written on {res['hindsight']} with this history in view, so "
              "its history can show at most 'in-sample only'; live episodes after that date decide.", ""]
    if res.get("env_changed"):
        L += [f"**Definition changed** since the first hashed run ({res.get('definition_frozen')} -> "
              f"{res.get('definition_hash')}).", ""]
    L += [f"**Verdict: {res['verdict']}.** " + ("; ".join(res.get("reasons") or []) or "every gate rule holds") + ".",
          "", f"_{res.get('llm_window', '')}. Data: {res.get('data_note')} Descriptive research, not a signal or a "
          "trade instruction; decisions stay with the PM._", ""]
    return "\n".join(L)


def build_index(root: Path | None = None, c: dict | None = None, write: bool = True) -> dict:
    """research/index.md (every study, its verdict after the family-wide haircut, and the graveyard) and
    research/verdicts.json (what the critic and the risk section read)."""
    c = c or cfg()
    P = paths(root)
    studies = load_studies(root)
    results = load_results(root)
    fam = family(results, c, [k for k, v in studies.items() if v.get("kind") == "flag"])
    led = runs(root)
    peeks = [r for r in ledger(root) if r.get("event") == "peek"]
    # the final verdict of each study is the one after the whole family; it is written back into its result page
    # and JSON, and a change is a ledger event (review, finding 2)
    for r in results:
        before = r.get("verdict")
        _set_verdict(r, fam, c)
        if write:
            _write_result(r, c, root)
            if r["verdict"] != before:
                _append_ledger({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "event": "verdict",
                                "id": r["id"], "from": before, "to": r["verdict"],
                                "q_bh": (r.get("family") or {}).get("q_bh")}, root)
    rows, grave, verd = [], [], {}
    for r in sorted(results, key=lambda x: (str(x.get("agent") or "zz"), x["id"])):
        fv = fam.get(r["id"]) or {}
        v = r["verdict"]
        why = r.get("reasons") or []
        if r["kind"] == "flag":
            stat = (f"lift {_f(r.get('lift'), 2)} ({_f(r.get('hit_rate'), 4, pct=True)} vs {_f(r.get('base_rate'), 4, pct=True)})"
                    if r.get("binary") else f"excess {_f(r.get('excess_sd'), 2)} sd")
            rows.append(f"| `{r['id']}` | {r.get('agent')} | `{r.get('flag')}` {r.get('outcome')} {r.get('horizon_days')}d | "
                        f"{r.get('n_episodes')} | {stat} | {_f(r.get('p_placebo'), 3)} | {_f(fv.get('q_bh'), 3)} | **{v}** |")
            verd[r["id"]] = {"flag": r.get("flag"), "params": r.get("params"), "agent": r.get("agent"),
                             "outcome": r.get("outcome"), "horizon_days": r.get("horizon_days"),
                             "n_episodes": r.get("n_episodes"), "base_rate": r.get("base_rate"),
                             "hit_rate": r.get("hit_rate"), "lift": r.get("lift"), "lift_shrunk": r.get("lift_shrunk"),
                             "excess_sd": r.get("excess_sd"), "excess_shrunk_sd": r.get("excess_shrunk_sd"),
                             "p_placebo": r.get("p_placebo"), "q_bh": fv.get("q_bh"), "verdict": v,
                             "registered": r.get("registered"), "hindsight": r.get("hindsight"),
                             "asof": r.get("asof"), "result": f"research/results/{r['id']}.md"}
        else:
            pr = r.get("primary") or {}
            rows.append(f"| `{r['id']}` | paper | `{r.get('strategy')}` | {pr.get('n')} months | Sharpe {_f(pr.get('sharpe'))}, "
                        f"alpha t {_f((r.get('alpha_vs_long_only') or {}).get('t_alpha'))} | - | DSR {_f((r.get('deflated') or {}).get('dsr'), 3)} | **{v}** |")
            verd[r["id"]] = {"strategy": r.get("strategy"), "verdict": v, "sharpe": pr.get("sharpe"),
                             "dsr": (r.get("deflated") or {}).get("dsr"), "asof": r.get("asof"),
                             "result": f"research/results/{r['id']}.md"}
        if v != "supported":
            grave.append(f"- `{r['id']}` ({v}): " + ("; ".join(why) or "-") + f" [{r.get('asof')}]")
    pending = [s for s in studies if not (P["results"] / f"{s}.json").exists()]
    L = ["# Research loop — index", "",
         f"Built {datetime.now(timezone.utc).date()} by `python -m pmstack research index`. {len(studies)} studies "
         f"registered, {len(led)} runs and {len(peeks)} peeks (runs that wrote nothing) in the ledger. Verdicts carry the Benjamini-Hochberg q across every registered flag study "
         f"(missing or insufficient ones count with p = 1), so a verdict can change as the ledger grows. Gate: "
         f"config/research.yaml; method: docs/research/research-loop.md.", "",
         "| study | agent | flag / outcome | episodes | effect | placebo p | BH q | verdict |",
         "|---|---|---|---|---|---|---|---|", *rows, "",
         "## Graveyard", "", "Every study that did not pass, with the rule it failed. Never deleted: each one is a trial "
         "that raises the bar for the next.", "", *(grave or ["- (empty)"]), ""]
    if pending:
        L += ["## Registered, not yet run", "", *[f"- `{s}`" for s in pending], ""]
    L += ["_Descriptive research, not signals or trade instructions; decisions stay with the PM._", ""]
    out = {"asof": str(datetime.now(timezone.utc).date()), "n_registered": len(studies), "n_runs": len(led),
           "n_peeks": len(peeks),
           "verdicts": verd}
    if write:
        P["root"].mkdir(parents=True, exist_ok=True)
        P["index"].write_text("\n".join(L), encoding="utf-8")
        P["verdicts"].write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    return out


def read_verdicts(root: Path | None = None) -> dict:
    f = paths(root)["verdicts"]
    try:
        return json.loads(f.read_text(encoding="utf-8")).get("verdicts") or {}
    except (OSError, ValueError):
        return {}


def _version(sid: str) -> int:
    tail = sid.rsplit("_v", 1)
    return int(tail[1]) if len(tail) == 2 and tail[1].isdigit() else 0


def _known_by(v: dict, asof) -> bool:
    """A verdict exists for a past as-of date only if its data ended by then (review, finding 10)."""
    if asof is None:
        return True
    try:
        return str(v.get("asof") or "9999") <= str(asof)[:10]
    except Exception:  # noqa: BLE001
        return False


def verdict_for(flag_name: str, params: dict | None = None, root: Path | None = None, asof=None) -> dict | None:
    """The verdict on a flag from its newest study (latest registration, then highest _vN) whose data ended by `asof`,
    for the critic card and the risk section."""
    best = None
    for sid, v in read_verdicts(root).items():
        if not isinstance(v, dict) or v.get("flag") != flag_name or not _known_by(v, asof):
            continue
        if params is not None and not all((v.get("params") or {}).get(k) == x for k, x in params.items()):
            continue
        key = (str(v.get("registered") or ""), _version(sid), sid)
        if best is None or key > best[0]:
            best = (key, {"id": sid, **v})
    return best[1] if best else None


def _tag(sid: str, v: dict) -> dict:
    n = v.get("n_episodes")
    if v.get("lift") is not None:
        eff = (f"lift {_f(v.get('lift'), 2)}, shrunk {_f(v.get('lift_shrunk'), 2)}; "
               f"{_f(v.get('hit_rate'), 4, pct=True)} vs base {_f(v.get('base_rate'), 4, pct=True)}")
    elif v.get("excess_sd") is not None:
        eff = f"excess {_f(v.get('excess_sd'), 2)} sd, shrunk {_f(v.get('excess_shrunk_sd'), 2)}"
    else:
        eff = "no episodes"
    hs = f"; definition written {v['hindsight']} with this history in view" if v.get("hindsight") else ""
    return {"study": sid, "verdict": v.get("verdict"), "url": v.get("result"),
            "text": f"{v.get('verdict')} ({eff}; {n} episodes, {v.get('outcome')} {v.get('horizon_days')}d; "
                    f"as of {v.get('asof')}{hs})"}


def tag_for(flag_name: str, params: dict | None = None, root: Path | None = None, asof=None) -> dict | None:
    """A one-line measured verdict for a flag, for the Risk section and the critic card (figures from verdicts.json)."""
    v = verdict_for(flag_name, params, root, asof)
    return _tag(v["id"], v) if v else None


def tag_study(sid: str, root: Path | None = None, asof=None) -> dict | None:
    v = read_verdicts(root).get(sid)
    return _tag(sid, v) if isinstance(v, dict) and _known_by(v, asof) else None


def agent_tags(agent: int, root: Path | None = None, asof=None) -> list[dict]:
    """Every measured flag study of one agent whose data ended by `asof`, for the line under its section."""
    return [{"flag": v["flag"], "params": v.get("params") or {}, **_tag(sid, v)}
            for sid, v in sorted(read_verdicts(root).items())
            if isinstance(v, dict) and v.get("agent") == agent and v.get("flag") and _known_by(v, asof)]


# ------------------------------------------------------------------ CLI
def cli(argv: list[str]) -> int:
    import argparse
    from . import runlog
    p = argparse.ArgumentParser(prog="pmstack research")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("flags", help="the flag catalogue a study can test")
    sub.add_parser("list", help="registered studies and their latest verdicts")
    s = sub.add_parser("new", help="register a study from a YAML file (validated, never overwritten)")
    s.add_argument("file")
    s = sub.add_parser("run", help="run one study (or --all) on data up to --date")
    s.add_argument("id", nargs="?")
    s.add_argument("--all", action="store_true")
    s.add_argument("--date")
    s.add_argument("--no-write", action="store_true")
    sub.add_parser("index", help="rebuild research/index.md and research/verdicts.json")
    s = sub.add_parser("show", help="print a study's latest result")
    s.add_argument("id")
    a = p.parse_args(argv)
    if a.cmd == "flags":
        for k, v in FLAGS.items():
            print(f"{k:24} agent {v['agent']}  lag {v['lag_days']}d  side = {v['sides']}\n    {v['doc']}")
        return 0
    if a.cmd == "list":
        vs = read_verdicts()
        for sid, s_ in load_studies().items():
            print(f"{sid:40} {s_.get('kind'):8} {(vs.get(sid) or {}).get('verdict', 'not run')}")
        return 0
    if a.cmd == "new":
        spec = yaml.safe_load(Path(a.file).read_text(encoding="utf-8"))
        f = register(spec)
        print(f"registered {f.relative_to(ROOT).as_posix()}")
        runlog.log(runlog.new_run_id(), "research:new", "ok", study=spec["id"], output=f.relative_to(ROOT).as_posix())
        return 0
    if a.cmd == "show":
        f = paths()["results"] / f"{a.id}.md"
        print(f.read_text(encoding="utf-8") if f.exists() else f"{a.id}: not run")
        return 0
    if a.cmd == "index":
        out = build_index()
        print(f"index: {out['n_registered']} studies, {out['n_runs']} runs -> research/index.md")
        return 0
    asof = date.fromisoformat(a.date) if a.date else date.today()
    studies = load_studies()
    ids = list(studies) if a.all else [a.id]
    if not a.all and a.id not in studies:
        print(f"unknown study {a.id}; registered: {', '.join(studies)}")
        return 2
    run_id = runlog.new_run_id()
    obs = load_obs(asof)
    cache: dict = {}
    c = cfg()
    done = []
    for sid in ids:
        try:
            r = run_study(studies[sid], obs, asof, c=c, cache=cache, write=not a.no_write, run_id=run_id)
        except Exception as e:  # noqa: BLE001  one failing study must not stop the others
            print(f"[error] {sid}: {type(e).__name__}: {e}")
            runlog.log(run_id, "research:run", "error", study=sid, errors=[f"{type(e).__name__}: {e}"])
            continue
        done.append(sid)
        stat = r.get("stat") if r["kind"] == "flag" else (r.get("primary") or {}).get("sharpe")
        print(f"{sid:40} n={r.get('n_episodes', '-')} stat={stat} p={r.get('p_placebo', '-')} -> {r['verdict']}")
        runlog.log(run_id, "research:run", "ok", study=sid, asof=str(asof), verdict=r["verdict"],
                   n_episodes=r.get("n_episodes"), output=f"research/results/{sid}.md")
    if done and not a.no_write:
        out = build_index()
        print(f"index rebuilt: {out['n_registered']} studies")
    return 0 if done else 1
