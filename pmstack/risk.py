"""Risk and crowding (agent 8): how concentrated the open paper ideas are, what stress would cost in R, where
trend followers flip, and early warnings from realised losses. Descriptive only.

Evidence behind each rule: docs/research/risk.md. In short:
  - Exposure of idea i in R per unit log return: e_i = size_i x dir_i x price_i / |entry_i - stop_i|. Book sd in R
    = sqrt(e' S e), with e summed by market first (two ideas on one market are one exposure). Everything is in R.
  - Current vol per market = EWMA 0.94 (vol only: RiskMetrics' decay is too short for correlation; Tan & Zohren).
    Turbulence (Mahalanobis distance of each day's returns; Kritzman & Li) and the stress days (top 20%) are measured
    on a fixed universe of synchronous US-close markets, so the book never changes the model. Calm correlation = the
    last 250 universe trading days; stress correlation = the stress days. Universe pairs are shrunk toward constant
    correlation (Ledoit & Wolf 2004); other markets join by pairwise estimates on the same days, shrunk with the same
    intensity and repaired to positive semi-definite. Downside correlations exceed calm ones (Longin & Solnik; Ang &
    Chen), so stress P&L uses the stress matrix; no alert fires on a raw correlation jump (Forbes & Rigobon).
  - Stress P&L from scenario shocks, never sigma multiples (Pedersen 2009: 30+ sd in Aug 2007), in two columns:
    stops honoured (a replay checks the path inside its window; an idea already past its stop is exited at today's
    mark) and gapped through the stop. Three kinds, each with a plausibility k on one scale (Berkowitz; Breuer et al.):
    replays from our own closes; named driver shocks pushed to every market by the conditional mean under the stress
    matrix (Rebonato); the worst case at k = 3, which for a linear book is radius x book sd at moves proportional to
    -S e (Breuer et al.). k = the Mahalanobis distance as a one-market sd equivalent (exact chi-square).
  - One concentration number: effective independent ideas = (sum |e_m| sd_m)^2 / e' S e under the stress matrix
    (Choueifaty; Grinold & Kahn breadth), capped at the idea count (hedges push the raw ratio above it). Clusters =
    ideas whose directional stress correlation >= 0.7. No caps (Bernardo, 10 Oct 2026: numbers only).
  - CTA levels on observed closes: flip level and distance in daily sd per leg, legs that flip by roll-off within 5
    days, the vol-target scale (slow / fast EWMA vol; Harvey et al.), Correction/Rebound state (Goulding, Harvey &
    Mazzoleni), panic state (Daniel & Moskowitz), stop near a flip level (Taleb). Captioned as not a forecast.
  - Crowding per idea, from CFTC reports already published by the as-of date (Tuesday data, Friday release): the
    percentile on the idea's side, the weekly change on that side as a z-score (Kang, Rouwenhorst & Tang), and the
    percentile after removing what 4/13/52-week returns explain (Sanders et al.). Red only when funding is stressing
    (Cheng, Kirilenko & Xiong; Brunnermeier & Pedersen).
  - One marked book curve (closed R + open marks, carried forward over missing prices) feeds both warnings: amber =
    down 3R from its 10-trading-day high; red = the sizing assistant's -4R over 60 days, the same function sizing.py
    calls, so the pack and the suggestion never disagree (Bernardo's choice, 10 Oct 2026). Crowding and CTA flags
    never alert until the research loop has their base rate and lift (Barroso et al.).
  - Nothing after the as-of date is used: ideas created later are left out, ideas closed later count as open,
    replays that end later are "not yet happened", CFTC reports count from their Friday release.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
BRT = ZoneInfo("America/Sao_Paulo")


def cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "risk.yaml").read_text(encoding="utf-8"))


def _num(x):
    try:
        v = None if x is None or x == "" else float(x)
        return None if v is None or math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def _r(x, nd=2):
    if x is None:
        return None
    x = float(x)
    return round(x, nd) if math.isfinite(x) else None


def _dir(e: dict) -> int | None:
    return {"long": 1, "short": -1}.get(e.get("direction"))


def _day(ts) -> date | None:
    """BRT calendar day of a journal timestamp (the pack's as-of dates are BRT days)."""
    if not ts:
        return None
    t = pd.Timestamp(ts)
    t = t.tz_localize("UTC") if t.tzinfo is None else t
    return t.tz_convert(BRT).date()


def size_of(e: dict) -> float:
    """Current paper size in units: planned size, then add/reduce events that state a new size."""
    s = _num(e.get("size_planned"))
    for ev in e.get("events") or []:
        if ev.get("action") in ("add", "reduce", "open") and _num(ev.get("size")) is not None:
            s = _num(ev["size"])
    return 1.0 if s is None else s


def _priced(e: dict) -> bool:
    a, b = _num(e.get("entry_price")), _num(e.get("invalidation_price"))
    return _dir(e) is not None and a is not None and b is not None and a != b and b > 0


def open_at(e: dict, asof: date) -> bool:
    """Open on the as-of day: created by then, and not closed or rejected by then."""
    c = _day(e.get("created_utc"))
    if c is not None and c > asof:
        return False
    st = e.get("status")
    if st == "open":
        return True
    if st in ("closed", "rejected"):
        end = _day(e.get("closed_utc") or e.get("rejected_utc"))
        return st == "closed" and end is not None and end > asof
    return False


def _in_book(e: dict, book: str) -> bool:
    return (e.get("book") == "example") == (book == "example")


# ------------------------------------------------------------------ prices
def observed(obs: pd.DataFrame, ids: list[str], asof: date) -> pd.DataFrame:
    """Observed closes (no fill), weekdays only, up to the as-of date."""
    o = obs[obs.series_id.isin(ids) & (obs.date <= asof)]
    if o.empty:
        return pd.DataFrame()
    p = o.pivot_table(index="date", columns="series_id", values="value", aggfunc="last").sort_index()
    p.index = pd.to_datetime(p.index)
    return p[p.index.dayofweek < 5].astype(float)


def store_prices(ids: list[str], asof: date) -> pd.DataFrame:
    """Observed closes from the research memory (for callers without an obs frame, e.g. the sizing assistant)."""
    ids = [i for i in dict.fromkeys(ids) if i]
    if not ids:
        return pd.DataFrame()
    try:
        from . import store
        q = "SELECT series_id, date, value FROM obs WHERE series_id IN (" + ",".join("?" * len(ids)) + ") AND date <= ?"
        df = store.connect().execute(q, ids + [asof]).df()
    except Exception:  # noqa: BLE001  (empty or missing store)
        return pd.DataFrame()
    if df.empty:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return observed(df, ids, asof)


def ewma_vol(r: pd.Series, lam: float) -> float | None:
    r = r.dropna()
    if len(r) < 20:
        return None
    w = lam ** np.arange(len(r))[::-1]
    return float(math.sqrt(np.sum(w * r.values ** 2) / np.sum(w)))


def lw_constant_corr(x: np.ndarray) -> tuple[np.ndarray, float]:
    """Ledoit & Wolf (2004) shrinkage of the sample covariance toward constant correlation (covCor). Returns
    (cov, intensity)."""
    t, n = x.shape
    x = x - x.mean(0)
    s = x.T @ x / t
    var = np.diag(s).copy()
    sd = np.sqrt(var)
    if n == 1:
        return s, 0.0
    corr = s / np.outer(sd, sd)
    rbar = (corr.sum() - n) / (n * (n - 1))
    f = rbar * np.outer(sd, sd)
    np.fill_diagonal(f, var)
    y = x ** 2
    phi_mat = y.T @ y / t - s ** 2
    phi = phi_mat.sum()
    theta = (x ** 3).T @ x / t - var[:, None] * s
    np.fill_diagonal(theta, 0.0)
    rho = np.diag(phi_mat).sum() + rbar * (np.outer(1 / sd, sd) * theta).sum()
    gamma = float(np.linalg.norm(s - f, "fro") ** 2)
    delta = 0.0 if gamma == 0 else max(0.0, min(1.0, (phi - rho) / gamma / t))
    return delta * f + (1 - delta) * s, float(delta)


def _corr(cov: np.ndarray) -> np.ndarray:
    sd = np.sqrt(np.diag(cov))
    c = cov / np.outer(sd, sd)
    np.fill_diagonal(c, 1.0)
    return c


def _psd(c: np.ndarray) -> np.ndarray:
    w, v = np.linalg.eigh((c + c.T) / 2)
    c2 = (v * np.maximum(w, 1e-8)) @ v.T
    d = np.sqrt(np.diag(c2))
    c2 = c2 / np.outer(d, d)
    np.fill_diagonal(c2, 1.0)
    return c2


def _matrix(lr: pd.DataFrame, days: pd.DatetimeIndex, uni: list[str], markets: list[str], min_pairs: int):
    """Correlation and per-market sd on `days`: universe block by Ledoit-Wolf; other markets pairwise, shrunk with the
    universe intensity toward the universe's average correlation, then repaired to PSD."""
    X = lr.loc[lr.index.isin(days), markets]
    cov_u, delta = lw_constant_corr(X[uni].dropna().values)
    cu = _corr(cov_u)
    n_u = len(uni)
    rbar = float((cu.sum() - n_u) / (n_u * (n_u - 1))) if n_u > 1 else 0.0
    pc = X.corr(min_periods=min_pairs).reindex(index=markets, columns=markets).values
    pc = np.where(np.isnan(pc), rbar, pc)
    c = (1 - delta) * pc + delta * rbar
    np.fill_diagonal(c, 1.0)
    ix = [markets.index(m) for m in uni]
    c[np.ix_(ix, ix)] = cu
    sd = X.std().reindex(markets).values.astype(float)
    sd[ix] = np.sqrt(np.diag(cov_u))
    return _psd(c), sd, delta


def model(obs: pd.DataFrame, extra: list[str], asof: date, c: dict) -> dict | None:
    """Returns, current vols, calm and stress covariance, turbulence history."""
    ids = list(dict.fromkeys(list(c["universe"]) + [m for m in extra if m]))
    raw = observed(obs, ids, asof)
    if raw.empty:
        return None
    uni = [m for m in c["universe"] if m in raw.columns and raw[m].notna().sum() >= c["min_days"]]
    if len(uni) < 2:
        return None
    # trading days = days when most of the universe printed (futures holidays drop out even if FX traded)
    days = raw.index[raw[uni].notna().sum(axis=1) >= max(2, len(uni) // 2)]
    p = raw.loc[days].ffill()                                       # a market closed for a day carries its close
    lr = np.log(p).diff().iloc[1:]
    markets = [m for m in p.columns if lr[m].notna().sum() >= c["min_days"]]
    full_u = lr[uni].dropna()
    if len(full_u) < c["min_days"]:
        return None
    u = full_u.values
    d = u - u.mean(0)
    inv = np.linalg.pinv(np.cov(u, rowvar=False))
    turb = pd.Series(np.einsum("ij,jk,ik->i", d, inv, d) / len(uni), index=full_u.index)
    cut = float(np.percentile(turb, c["turbulence"]["stress_pct"]))
    stress_days = full_u.index[turb >= cut]
    calm_days = full_u.index[-c["corr_days"]:]
    C_calm, _, d_calm = _matrix(lr, calm_days, uni, markets, 60)
    C_str, sd_str, d_str = _matrix(lr, stress_days, uni, markets, 30)
    vol_now = {m: ewma_vol(lr[m], c["vol_lambda"]) for m in markets}
    sd_now = np.array([vol_now[m] or float(lr[m].std()) for m in markets])
    sd_s = np.maximum(np.nan_to_num(sd_str, nan=0.0), sd_now)        # stress vol never below today's vol
    return {"markets": markets, "universe": uni, "prices": p, "raw": raw, "returns": lr, "turb": turb, "turb_cut": cut,
            "n_stress_days": int(len(stress_days)), "n_calm_days": int(len(calm_days)),
            "shrink": {"calm": round(d_calm, 2), "stress": round(d_str, 2)},
            "vol_now": vol_now, "S_calm": C_calm * np.outer(sd_now, sd_now), "S_stress": C_str * np.outer(sd_s, sd_s),
            "C_stress": C_str, "since": str(full_u.index[0].date()), "through": str(full_u.index[-1].date())}


# ------------------------------------------------------------------ book curve (shared with the sizing assistant)
def _r_now(e: dict, price: float) -> float:
    return _dir(e) * (price - _num(e["entry_price"])) / abs(_num(e["entry_price"]) - _num(e["invalidation_price"]))


def book_curve(entries: list[dict], asof: date, book: str, start: date, prices: pd.DataFrame | None = None) -> pd.Series:
    """Closed R plus open marks on each business day from `start` to `asof`. A missing price carries the last
    observed close (no false jumps when one series is late). Closed ideas count their stated R from the close day,
    whatever their kind; open ones are marked only when long/short with prices."""
    keep = [e for e in entries if _in_book(e, book) and e.get("status") in ("open", "closed")]
    idx = pd.bdate_range(start, asof)
    if not len(idx):
        return pd.Series(dtype=float)
    refs = [e.get("price_ref") for e in keep if _priced(e) and e.get("price_ref")]
    if prices is None:
        prices = store_prices(refs, asof)
    if len(prices.columns):
        px = prices.reindex(prices.index.union(idx)).sort_index().ffill().reindex(idx)
    else:
        px = pd.DataFrame(index=idx)
    vals = np.zeros(len(idx))
    for e in keep:
        t0, t1 = _day(e.get("created_utc")), _day(e.get("closed_utc"))
        s = size_of(e)
        r_close = _num(e.get("r_multiple"))
        ref = e.get("price_ref")
        for k, d in enumerate(idx.date):
            if t0 is not None and d < t0:
                continue
            if e.get("status") == "closed" and t1 is not None and d >= t1:
                vals[k] += (r_close or 0.0) * s
            elif _priced(e) and ref in px.columns and pd.notna(px.iat[k, px.columns.get_loc(ref)]):
                vals[k] += s * _r_now(e, float(px.iat[k, px.columns.get_loc(ref)]))
    return pd.Series(vals, index=idx)


def marked_drawdown(entries: list[dict], asof: date, lookback_days: int, book: str = "paper",
                    prices: pd.DataFrame | None = None) -> float:
    """Drawdown in R of the marked book over the lookback: today's level minus the highest level in the window."""
    cv = book_curve(entries, asof, book, asof - timedelta(days=lookback_days), prices)
    if cv.empty:
        return 0.0
    return round(float(cv.iloc[-1] - cv.max()), 2)


# ------------------------------------------------------------------ stress
def _pnl(e: dict, price: float, ret: float) -> float:
    """R for a log return `ret` from `price` (gapped: no stop)."""
    risk = abs(_num(e["entry_price"]) - _num(e["invalidation_price"]))
    return size_of(e) * _dir(e) * price * (math.exp(ret) - 1) / risk


def apply(rows: list[dict], moves: dict[str, float], paths: dict[str, tuple[float, float]] | None = None) -> dict:
    """Stress P&L in R for log-return moves per market. Gapped = linear through the stop. Stops honoured = an idea
    already past its stop is exited at today's mark (0 from here); otherwise the loss stops at the stop if the end
    move, or (for a replay) the worst point of the path, reaches it."""
    gap = hon = 0.0
    per = []
    for r in rows:
        m = r["price_ref"]
        if m not in moves:
            per.append({"id": r["id"], "move_pct": None, "gapped_r": None, "honoured_r": None})
            continue
        g = _pnl(r["_e"], r["last"], moves[m])
        if r["r_now"] <= -1:
            h = 0.0
        else:
            floor = -r["size"] * (1 + r["r_now"])
            worst = g
            if paths and m in paths:
                lo, hi = paths[m]
                worst = min(g, _pnl(r["_e"], r["last"], lo if r["dir"] > 0 else hi))
            h = floor if worst <= floor else g
        gap, hon = gap + g, hon + h
        per.append({"id": r["id"], "move_pct": _r(100 * (math.exp(moves[m]) - 1), 1), "gapped_r": _r(g), "honoured_r": _r(h)})
    missing = [x["id"] for x in per if x["gapped_r"] is None]
    return {"gapped_r": _r(gap), "honoured_r": _r(hon), "ideas": per, "missing": missing}


def k_equivalent(d: float, n: int) -> float:
    """Mahalanobis distance d in n dimensions as a one-market sd equivalent: the two-sided normal quantile with the
    same tail probability as chi-square(n) beyond d^2. Without this a typical day in 21 markets reads as k ~ 4.6."""
    from scipy.stats import chi2, norm
    if n <= 1:
        return float(abs(d))
    p = float(chi2.sf(d * d, n))
    if p <= 0:
        return float(abs(d))
    return float(norm.isf(p / 2)) if p < 1 else 0.0


def plausibility(moves: dict[str, float], M: dict, days: int, only: list[str] | None = None) -> float | None:
    """k = how many sd the scenario sits from normal (stress matrix scaled to its length), as a 1-d equivalent."""
    ks = [m for m in dict.fromkeys(moves) if m in M["markets"] and (only is None or m in only)]
    if not ks:
        return None
    ix = [M["markets"].index(m) for m in ks]
    S = M["S_stress"][np.ix_(ix, ix)] * max(1, days)
    v = np.array([moves[m] for m in ks])
    d = math.sqrt(max(0.0, float(v @ np.linalg.pinv(S) @ v)))
    return _r(k_equivalent(d, len(ks)), 1)


def replays(rows: list[dict], M: dict, c: dict, asof: date) -> list[dict]:
    p = M["prices"]
    out = []
    for rp in c["replays"]:
        a, b = pd.Timestamp(rp["start"]), pd.Timestamp(rp["end"])
        base = {"id": rp["id"], "name": rp["name"], "kind": "replay", "window": f"{rp['start']} to {rp['end']}"}
        if b.date() > asof:
            out.append({**base, "note": "not yet happened on the as-of date"})
            continue
        pa, pw = p[p.index <= a], p[(p.index > a) & (p.index <= b)]
        if pa.empty or pw.empty:
            out.append({**base, "note": "no data for this window"})
            continue
        x = pa.iloc[-1]
        moves, paths = {}, {}
        for m in p.columns:
            if pd.isna(x[m]) or x[m] <= 0 or pw[m].isna().all():
                continue
            path = np.log(pw[m].dropna() / x[m])
            moves[m], paths[m] = float(path.iloc[-1]), (float(path.min()), float(path.max()))
        res = apply(rows, moves, paths)
        only = list(c["worst_case"]["replay_k_markets"]) + [r["price_ref"] for r in rows]
        out.append({**base, "days": int(len(pw)), "k": plausibility(moves, M, len(pw), only=only), **res,
                    "drivers": {m: _r(100 * (math.exp(moves[m]) - 1), 1) for m in c["worst_case"]["replay_k_markets"] if m in moves}})
    return out


def named(rows: list[dict], M: dict, c: dict) -> list[dict]:
    mk, S = M["markets"], M["S_stress"]
    out = []
    for sc in c["scenarios"]:
        drv = {m: math.log(1 + float(v)) for m, v in sc["drivers"].items() if m in mk}
        if len(drv) < len(sc["drivers"]):
            out.append({"id": sc["id"], "name": sc["name"], "kind": "named", "note": "a driver has no price history"})
            continue
        di = [mk.index(m) for m in drv]
        v = np.array(list(drv.values()))
        cond = S[:, di] @ np.linalg.pinv(S[np.ix_(di, di)]) @ v       # conditional mean of every market
        moves = {m: float(cond[i]) for i, m in enumerate(mk)}
        moves.update(drv)
        res = apply(rows, moves)
        out.append({"id": sc["id"], "name": sc["name"], "kind": "named", "chain": sc["chain"],
                    "k": plausibility(drv, M, c["worst_case"]["horizon_days"]), **res,
                    "drivers": {m: _r(100 * float(x), 1) for m, x in sc["drivers"].items()}})
    return out


def worst_case(rows: list[dict], e_m: dict[str, float], M: dict, c: dict) -> dict | None:
    """Worst linear loss at plausibility k (one-market sd equivalent) over the horizon, exposures summed by market."""
    wc = c["worst_case"]
    mk = list(e_m)
    ix = [M["markets"].index(m) for m in mk]
    e = np.array([e_m[m] for m in mk])
    S = M["S_stress"][np.ix_(ix, ix)] * wc["horizon_days"]
    sd = math.sqrt(max(0.0, float(e @ S @ e)))
    if sd == 0:
        return None
    lo, hi = 0.0, 100.0                  # radius whose one-market equivalent is k (same scale as the other rows)
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if k_equivalent(mid, len(ix)) < wc["k"] else (lo, mid)
    radius = (lo + hi) / 2
    vec = -radius * (S @ e) / sd
    moves = {m: float(vec[j]) for j, m in enumerate(mk)}
    res = apply(rows, moves)
    return {"id": "worst_k3", "name": f"Worst case at k = {wc['k']:g} ({wc['horizon_days']} days)", "kind": "worst",
            "k": wc["k"], "radius": _r(radius, 2), "linear_r": _r(-radius * sd), **res,
            "drivers": {m: _r(100 * (math.exp(x) - 1), 1) for m, x in moves.items()}}


def clusters(rows: list[dict], M: dict, c: dict) -> tuple[list[list[str]], list[list]]:
    n = len(rows)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    same = []
    for i in range(n):
        for j in range(i + 1, n):
            a, b = rows[i], rows[j]
            rho = float(M["C_stress"][a["_ix"], b["_ix"]]) * a["dir"] * b["dir"]
            if rho >= c["clusters"]["link_corr"]:
                parent[find(i)] = find(j)
            if rho >= c["clusters"]["same_corr"]:
                same.append([a["id"], b["id"], round(rho, 2)])
    groups: dict[int, list[str]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(rows[i]["id"])
    return sorted(groups.values(), key=lambda g: -len(g)), same


def funding(obs: pd.DataFrame, asof: date, c: dict) -> dict:
    f = c["funding"]
    out = {"stressing": False}
    hy = obs[(obs.series_id == f["hy_series"]) & (obs.date <= asof)].sort_values("date")
    if len(hy) > f["hy_days"]:
        chg = 100 * (float(hy.value.iloc[-1]) - float(hy.value.iloc[-1 - f["hy_days"]]))
        out.update({"hy_oas_pct": _r(hy.value.iloc[-1]), "hy_change_bp": _r(chg, 0), "hy_date": str(hy.date.iloc[-1]),
                    "hy_url": hy.source_url.iloc[-1]})
        out["stressing"] |= chg >= f["hy_change_bp"]
    vx = obs[(obs.series_id == f["vix_series"]) & (obs.date <= asof)].sort_values("date")
    if len(vx) > 60:
        last = float(vx.value.iloc[-1])
        pct = float(100 * (vx.value <= last).mean())
        out.update({"vix": _r(last, 1), "vix_pct": _r(pct, 0), "vix_date": str(vx.date.iloc[-1]), "vix_url": vx.source_url.iloc[-1],
                    "vix_since": str(vx.date.iloc[0])})
        out["stressing"] |= pct >= f["vix_pct"]
    return out


# ------------------------------------------------------------------ CTA levels
def _ewm_sd(r: pd.Series, halflife: int) -> float | None:
    r = r.dropna()
    return None if len(r) < 2 * halflife else float(np.sqrt((r ** 2).ewm(halflife=halflife).mean().iloc[-1]))


def cta_levels(p: pd.Series, c: dict, legs=(21, 63, 252)) -> dict | None:
    """On observed closes only (no filled holidays)."""
    p = p.dropna()
    if len(p) < legs[1] + 2:
        return None
    k = c["cta"]
    lr = np.log(p).diff().dropna()
    sd = ewma_vol(lr, c["vol_lambda"]) or float(lr.std())
    last = float(p.iloc[-1])
    out = {"last": _r(last, 4), "last_date": str(p.index[-1].date()), "daily_sd_pct": _r(100 * sd, 2), "legs": {}}
    signs = {}
    for h in legs:
        if len(p) <= h + k["roll_days"]:
            continue
        ref = float(p.iloc[-1 - h])
        sgn = 1 if last > ref else -1 if last < ref else 0
        signs[h] = sgn
        flips_in = None
        for j in range(1, k["roll_days"] + 1):                     # in j days the reference is j closes later
            nxt = float(p.iloc[-1 - h + j])
            s2 = 1 if last > nxt else -1 if last < nxt else 0
            if s2 != sgn:
                flips_in = j
                break
        out["legs"][str(h)] = {"sign": sgn, "flip_level": _r(ref, 4),
                               "distance_sd": _r(math.log(last / ref) / sd, 1) if sd else None,
                               "rolloff_flip_days": flips_in}
    fast, slow = _ewm_sd(lr, k["fast_halflife"]), _ewm_sd(lr, k["slow_halflife"])
    out["vol_scale"] = _r(slow / fast, 2) if fast and slow else None
    out["vol_shrinking"] = bool(out["vol_scale"] is not None and out["vol_scale"] < k["shrink_below"])
    s1, s12 = signs.get(legs[0]), signs.get(legs[2])
    out["state"] = None if s1 is None or s12 is None else ("correction" if s12 > 0 > s1 else "rebound" if s12 < 0 < s1 else "aligned")
    panic = None
    if len(p) > k["panic_ret_days"] and len(lr) > 2 * k["panic_vol_days"]:
        ret = math.log(last / float(p.iloc[-1 - k["panic_ret_days"]]))
        rv = lr.rolling(k["panic_vol_days"]).std().dropna()
        pct = float(100 * (rv <= rv.iloc[-1]).mean())
        panic = {"ret_24m_pct": _r(100 * (math.exp(ret) - 1), 1), "vol_pctile": _r(pct, 0),
                 "panic": bool(ret < 0 and pct >= k["panic_vol_pct"])}
    out["panic"] = panic
    return out


# ------------------------------------------------------------------ crowding per idea
def crowding(obs: pd.DataFrame, e: dict, code: str | None, prices: pd.DataFrame, asof: date, c: dict) -> dict | None:
    if not code:
        return None
    k = c["crowding"]
    lag = int(k.get("release_lag_days", 3))
    s = obs[(obs.series_id == f"{code}.mm_net_pct_oi") & (obs.date <= asof - timedelta(days=lag))].sort_values("date")
    if len(s) < 52:
        return None
    v = pd.Series(s.value.astype(float).values, index=pd.to_datetime(s.date)).tail(k["weeks"])
    d = _dir(e)
    pct = float(100 * (v <= v.iloc[-1]).mean())
    side = pct if d > 0 else 100 - pct
    ch = v.diff().dropna()
    z = None
    if len(ch) > 20 and ch.std() > 0:
        z = float(d * (ch.iloc[-1] - ch.mean()) / ch.std())
    resid_pct = None
    ref = e.get("price_ref")
    if ref in prices.columns:
        px = prices[ref].dropna()
        wk = px.reindex(px.index.union(v.index)).sort_index().ffill().reindex(v.index)
        X = pd.concat({f"r{l}": np.log(wk / wk.shift(l)) for l in k["resid_lags"]}, axis=1)
        j = pd.concat([v.rename("y"), X], axis=1).dropna()
        if len(j) >= 40:
            A = np.column_stack([np.ones(len(j)), j[X.columns].values])
            beta, *_ = np.linalg.lstsq(A, j["y"].values, rcond=None)
            res = j["y"].values - A @ beta
            rp = float(100 * (res <= res[-1]).mean())
            resid_pct = rp if d > 0 else 100 - rp
    return {"code": code, "date": str(v.index[-1].date()), "pct_on_side": _r(side, 0),
            "change_on_side_pp": _r(d * float(ch.iloc[-1]), 1) if len(ch) else None,
            "change_z": _r(z, 1), "crowded_entry": bool(z is not None and z >= k["change_z"]),
            "resid_pct_on_side": _r(resid_pct, 0), "crowded": side >= k["crowded_pct"],
            "source_url": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"}


# ------------------------------------------------------------------ the section
def book_ideas(entries: list[dict], asof: date) -> tuple[list[dict], str]:
    """Long/short ideas with prices open on the as-of day; the paper book, or the example book when no paper idea is open."""
    live = [e for e in entries if open_at(e, asof) and _priced(e)]
    paper = [e for e in live if e.get("book") != "example"]
    return (paper, "paper") if paper else ([e for e in live if e.get("book") == "example"], "example")


def _sizing_dd() -> dict:
    from . import sizing
    return sizing.cfg()["drawdown"]


def build(obs: pd.DataFrame, entries: list[dict], names: dict[str, str], cftc_map: dict, asof: date,
          consensus_markets: list[str] | None = None, now: datetime | None = None) -> tuple[dict, list[dict]]:
    c = cfg()
    if obs.empty:
        return {"note": "no data"}, []
    ideas, book = book_ideas(entries, asof)
    refs = [e.get("price_ref") for e in ideas]
    drivers = [m for sc in c["scenarios"] for m in sc["drivers"]]
    M = model(obs, refs + drivers, asof, c)
    if M is None:
        return {"note": "not enough price history for the risk model"}, []
    raw = M["raw"]
    sz = _sizing_dd()
    sec = {"asof": str(asof), "book": book, "captions": c["captions"],
           "settings": {"same_corr": c["clusters"]["same_corr"], "link_corr": c["clusters"]["link_corr"],
                        "hy_days": c["funding"]["hy_days"], "dd_lookback_days": sz["lookback_days"],
                        "dd_trigger_r": sz["trigger_r"], "amber_r": c["drawdown"]["amber_r"],
                        "amber_days": c["drawdown"]["amber_days"]},
           "model": {"since": M["since"], "through": M["through"], "calm_days": M["n_calm_days"],
                     "stress_days": M["n_stress_days"], "shrinkage": M["shrink"], "markets": len(M["markets"])}}
    t = M["turb"]
    recent = t.tail(c["turbulence"]["persist_days"])
    hot = int((recent >= M["turb_cut"]).sum())
    sec["turbulence"] = {"date": str(t.index[-1].date()), "pctile": _r(100 * (t <= t.iloc[-1]).mean(), 0),
                         "days_hot_of_last": [hot, len(recent)], "persistent": hot >= c["turbulence"]["persist_min"]}
    sec["funding"] = fund = funding(obs, asof, c)

    rows, skipped = [], []
    for e in ideas:
        m = e.get("price_ref")
        if m not in M["markets"] or m not in raw.columns or raw[m].dropna().empty:
            skipped.append({"id": e["id"], "market": e.get("market"), "reason": f"no price history for {m} in the risk model"})
            continue
        ob = raw[m].dropna()
        last = float(ob.iloc[-1])
        vol = M["vol_now"].get(m)
        risk = abs(_num(e["entry_price"]) - _num(e["invalidation_price"]))
        rn = _r_now(e, last)
        rows.append({"id": e["id"], "market": e.get("market"), "price_ref": m, "direction": e["direction"],
                     "dir": _dir(e), "size": size_of(e), "last": last, "last_date": str(ob.index[-1].date()),
                     "r_now": rn, "past_stop": rn <= -1, "_ix": M["markets"].index(m), "_e": e,
                     "_exp": _dir(e) * size_of(e) * last / risk,
                     "stop_sd": _r(_dir(e) * math.log(last / _num(e["invalidation_price"])) / vol, 1) if vol else None,
                     "sd_r": size_of(e) * last * (vol or 0) / risk})
    sec["skipped"] = skipped
    if rows:
        e_m: dict[str, float] = {}
        for r in rows:
            e_m[r["price_ref"]] = e_m.get(r["price_ref"], 0.0) + r["_exp"]
        mk = list(e_m)
        mix = [M["markets"].index(m) for m in mk]
        ev = np.array([e_m[m] for m in mk])
        Sc, Ss = M["S_calm"][np.ix_(mix, mix)], M["S_stress"][np.ix_(mix, mix)]
        var_c, var_s = float(ev @ Sc @ ev), float(ev @ Ss @ ev)
        sd_s = np.sqrt(np.diag(Ss))
        raw_eff = (float(np.sum(np.abs(ev) * sd_s)) ** 2 / var_s) if var_s > 0 else None
        cov_m = dict(zip(mk, Ss @ ev))                                 # (S e)_m per market
        groups, same = clusters(rows, M, c)
        gid = {i: k + 1 for k, g in enumerate(groups) for i in g}
        for r in rows:
            r["contrib_pct"] = _r(100 * r["_exp"] * cov_m[r["price_ref"]] / var_s, 0) if var_s > 0 else None
            r["cluster"] = gid[r["id"]]
        n = len(rows)
        sec["book_risk"] = {"ideas": n, "markets": len(mk), "effective_ideas": _r(min(raw_eff, n), 1) if raw_eff else None,
                            "effective_raw": _r(raw_eff, 1), "effective_capped": bool(raw_eff and raw_eff > n + 0.05),
                            "daily_sd_r_calm": _r(math.sqrt(max(var_c, 0))), "daily_sd_r_stress": _r(math.sqrt(max(var_s, 0))),
                            "open_r": _r(sum(r["size"] * r["r_now"] for r in rows)),
                            "to_stops_r": _r(-sum(r["size"] * (1 + r["r_now"]) for r in rows if r["r_now"] > -1)),
                            "past_stop": [r["id"] for r in rows if r["past_stop"]],
                            "clusters": groups, "same_idea_pairs": same,
                            "hedges": [r["id"] for r in rows if r["contrib_pct"] is not None and r["contrib_pct"] < 0]}
        st = replays(rows, M, c, asof) + named(rows, M, c)
        wc = worst_case(rows, e_m, M, c)
        if wc:
            st.append(wc)
        sec["stress"] = st
        full = [s for s in st if s.get("gapped_r") is not None and not s.get("missing")]
        if full:
            w = min(full, key=lambda s: s["gapped_r"])
            sec["worst_stress"] = {"id": w["id"], "name": w["name"], "gapped_r": w["gapped_r"], "honoured_r": w["honoured_r"], "k": w.get("k")}
    else:
        sec["note"] = "no open long/short ideas with prices"
    return _finish(sec, M, rows, c, consensus_markets, names, cftc_map, obs, asof, entries, book, fund)


def _finish(sec, M, rows, c, consensus_markets, names, cftc_map, obs, asof, entries, book, fund):
    mk = list(dict.fromkeys([r["price_ref"] for r in rows] + list(consensus_markets or [])))
    obsd = observed(obs, mk, asof)
    lv = {}
    for m in mk:
        if m in obsd.columns:
            x = cta_levels(obsd[m], c)
            if x:
                x["name"] = names.get(m, m)
                lv[m] = x
    sec["cta"] = lv
    out = []
    for r in rows:
        e = r["_e"]
        cr = crowding(obs, e, cftc_map.get(r["price_ref"]), obsd, asof, c)
        x = lv.get(r["price_ref"]) or {}
        sd = x.get("daily_sd_pct")
        near = []
        if sd:
            stop = _num(e["invalidation_price"])
            for h, leg in (x.get("legs") or {}).items():
                if leg.get("flip_level") and abs(math.log(stop / leg["flip_level"])) * 100 / sd <= c["cta"]["stop_near_flip_sd"]:
                    near.append(h)
        with_trend_short = r["dir"] < 0 and (x.get("legs", {}).get("252", {}).get("sign") or 0) < 0
        flags = []
        if r["past_stop"]:
            flags.append("past its stop")
        if near:
            flags.append("stop near flip level (" + ", ".join(f"{h}d" for h in near) + ")")
        if with_trend_short and (x.get("panic") or {}).get("panic"):
            flags.append("panic state: rebound risk on a with-trend short")
        if cr and cr["crowded"]:
            flags.append("crowded" + (" while funding is stressing" if fund.get("stressing") else ""))
        if cr and cr["crowded_entry"]:
            flags.append("crowded entry (weekly change)")
        ro = [h for h, leg in (x.get("legs") or {}).items() if leg.get("rolloff_flip_days")]
        if ro:
            flags.append("trend leg flips by roll-off within 5 days (" + ", ".join(f"{h}d" for h in ro) + ")")
        out.append({k: v for k, v in r.items() if not k.startswith("_") and k != "dir"} | {
            "r_now": _r(r["r_now"]), "last": _r(r["last"], 4), "sd_r": _r(r["sd_r"]),
            "book": e.get("book"), "crowding": cr, "flags": flags, "crowded_red": bool(cr and cr["crowded"] and fund.get("stressing"))})
    sec["ideas"] = out

    # one marked book curve: amber and red (red = the sizing assistant's own function and threshold)
    dd, sz = c["drawdown"], _sizing_dd()
    refs = [e.get("price_ref") for e in entries if _in_book(e, book) and _priced(e) and e.get("price_ref")]
    pj = observed(obs, refs, asof)
    start = asof - timedelta(days=max(sz["lookback_days"], 3 * dd["amber_days"]))
    curve = book_curve(entries, asof, book, start, pj)
    alerts, warn = [], []
    if len(curve):
        hi = float(curve.tail(dd["amber_days"] + 1).max())
        chg = round(float(curve.iloc[-1]) - hi, 2)
        win = curve[curve.index >= pd.Timestamp(asof - timedelta(days=sz["lookback_days"]))]
        red = round(float(curve.iloc[-1] - win.max()), 2)
        sec["book_curve"] = {"last_r": _r(curve.iloc[-1]), "high_10d_r": _r(hi), "from_high_r": chg, "drawdown_60d_r": red,
                             "since": str(curve.index[0].date()), "through": str(curve.index[-1].date())}
        if book == "paper" and red <= -abs(sz["trigger_r"]):
            warn.append(("risk_drawdown_red", 4.0, f"Red: paper drawdown {red:+.2f}R over {sz['lookback_days']} days (closed R + open "
                         f"marks) is past the sizing trigger of -{abs(sz['trigger_r']):g}R: size suggestions are halved"))
        elif chg <= -dd["amber_r"]:
            warn.append(("risk_drawdown_amber", 3.0, f"Amber: {book} book {chg:+.2f}R from its {dd['amber_days']}-day high "
                         f"(closed R + open marks; amber at -{dd['amber_r']:g}R)"))
    for g in (sec.get("book_risk") or {}).get("clusters", []):
        losing = [r for r in rows if r["id"] in g and r["r_now"] <= dd["cluster_r"]]
        if len(losing) >= dd["cluster_ideas"]:
            warn.append(("risk_cluster_loss", 3.0, f"Clustered losses: {len(losing)} ideas in one cluster at or below "
                         f"{dd['cluster_r']:g}R ({', '.join(r['market'] or r['id'] for r in losing)})"))
    tb = sec["turbulence"]
    if rows and tb["persistent"]:
        warn.append(("risk_turbulence", 2.5, f"Turbulence persistent: {tb['days_hot_of_last'][0]} of the last "
                     f"{tb['days_hot_of_last'][1]} days in the top 20% (today's percentile {tb['pctile']:.0f}, data through {tb['date']})"))
    es = obs[obs.series_id == "ES=F"].source_url
    src = {"risk_turbulence": es.iloc[-1] if len(es) else "https://finance.yahoo.com/"}
    for k, s, t in warn:
        if book == "example":
            s, t = s - 1.0, t + " [example book]"
        alerts.append({"kind": k, "severity": s, "id": book, "text": t,
                       "source_url": src.get(k, "https://github.com/bdgsaraiva/pm-agent-stack/tree/main/journal")})
    sec["warnings"] = [{"kind": a["kind"], "text": a["text"]} for a in alerts]
    return sec, alerts


# ------------------------------------------------------------------ CLI (stress report on demand)
def report(asof: date | None = None, out: Path | None = None) -> str:
    """Build the risk section from the store and the journal now, and render it (the on-demand stress report)."""
    import time

    from . import consensus, journal, monitor, runlog, store
    t0 = time.time()
    asof = asof or datetime.now(timezone.utc).astimezone(BRT).date()
    obs = store.connect().execute("SELECT * FROM obs").df()
    obs["date"] = pd.to_datetime(obs["date"]).dt.date
    names = {x["id"]: x["name"] for x in monitor._src().get("prices", {}).get("tickers", [])}
    cm = sorted({m for q in consensus.queries() if not q.get("validation") for m in (q.get("markets") or {})})
    sec, al = build(obs, journal.load_all(), names, journal._cfg()["cftc_map"], asof, consensus_markets=cm)
    md = "\n".join([f"# Risk and crowding — {asof}", ""] + render(sec))
    if out:
        Path(out).write_text(md, encoding="utf-8")
    runlog.log(runlog.new_run_id(), "risk:report", "ok", asof=str(asof), seconds=round(time.time() - t0, 1),
               ideas=len(sec.get("ideas", [])), alerts=len(al), outputs=[str(out)] if out else [])
    return md


def _f(x, nd=2, sign=False, pct=False):
    if x is None:
        return "-"
    s = f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"
    return s + ("%" if pct else "")


def render(S: dict) -> list[str]:
    L = ["## Risk and crowding (descriptive; in paper R)", ""]
    if not S.get("model"):
        return L + [f"Not available: {S.get('error') or S.get('note') or 'no section'}", ""]
    caps, st = S.get("captions", {}), S.get("settings", {})
    mdl = S["model"]
    L += [caps.get("model", ""), f"Model window {mdl['since']} to {mdl['through']}; {mdl['stress_days']} stress days; "
          f"shrinkage calm {mdl['shrinkage']['calm']}, stress {mdl['shrinkage']['stress']}.", ""]
    tb, fd = S.get("turbulence") or {}, S.get("funding") or {}
    line = f"**Market state:** turbulence percentile {_f(tb.get('pctile'), 0)} ({tb.get('date')}); " \
           f"{tb.get('days_hot_of_last', [0, 0])[0]} of the last {tb.get('days_hot_of_last', [0, 0])[1]} days in the top 20%."
    if fd.get("hy_change_bp") is not None:
        line += f" HY OAS {_f(fd['hy_oas_pct'])}% ({fd['hy_date']}), {_f(fd['hy_change_bp'], 0, sign=True)}bp over {st.get('hy_days')} observations ([FRED]({fd['hy_url']}))."
    if fd.get("vix") is not None:
        line += f" VIX {_f(fd['vix'], 1)}, percentile {_f(fd['vix_pct'], 0)} since {fd.get('vix_since')} ({fd['vix_date']})."
    line += " Funding " + ("**stressing**." if fd.get("stressing") else "not stressing.")
    L += [line, ""]
    if S.get("warnings"):
        L += ["**Warnings:** " + " ".join(w["text"] + "." for w in S["warnings"]), ""]
    ideas = S.get("ideas") or []
    if not ideas:
        L += [S.get("note") or "No open long/short ideas with prices.", ""]
    else:
        br, bc = S["book_risk"], S.get("book_curve") or {}
        tag = " (example book: no paper ideas open)" if S.get("book") == "example" else ""
        eff = _f(br["effective_ideas"], 1) + (f" (raw {_f(br['effective_raw'], 1)}: hedges push it above the count)" if br.get("effective_capped") else "")
        L += [f"**Book{tag}:** {br['ideas']} ideas, {eff} effective independent ideas (stress matrix). "
              f"Daily sd {_f(br['daily_sd_r_calm'])}R calm, {_f(br['daily_sd_r_stress'])}R stress. Open {_f(br['open_r'], sign=True)}R; "
              f"{_f(br['to_stops_r'])}R more if every stop is hit. Book {_f(bc.get('from_high_r'), sign=True)}R from its "
              f"{st.get('amber_days')}-day high; {_f(bc.get('drawdown_60d_r'), sign=True)}R over {st.get('dd_lookback_days')} days "
              f"(closed R + open marks; sizing halves at -{st.get('dd_trigger_r')}R).", ""]
        if br.get("same_idea_pairs"):
            L += [f"Same idea twice (stress correlation >= {st.get('same_corr')}): " + "; ".join(f"`{a}` and `{b}` ({c})" for a, b, c in br["same_idea_pairs"]), ""]
        L += ["| Idea | Dir | Size | Last (date) | R now | Stop (daily sd) | 1-sd day (R) | Share of stress risk | Cluster | CFTC pct on side (w/w z; ex-trend pct; report date) | Flags |",
              "|---|---|---:|---|---:|---:|---:|---:|---:|---|---|"]
        for r in ideas:
            cr = r.get("crowding")
            cf = f"{_f(cr['pct_on_side'], 0)} ({_f(cr['change_z'], 1, sign=True)}; {_f(cr['resid_pct_on_side'], 0)}; {cr['date']})" if cr else "n/a"
            nm = (r["market"] or r["price_ref"]) + (" (example)" if r.get("book") == "example" else "") + f" `{r['id']}`"
            L.append(f"| {nm} | {r['direction']} | {_f(r['size'])} | {_f(r['last'])} ({r['last_date']}) | {_f(r['r_now'], sign=True)} | {_f(r['stop_sd'], 1)} | "
                     f"{_f(r['sd_r'])} | {_f(r['contrib_pct'], 0, pct=True)} | {r['cluster']} | {cf} | {'; '.join(r['flags']) or '-'} |")
        L += ["", "Share of stress risk sums to 100%; a negative share is a hedge. " + caps.get("crowding", ""), ""]
        stx = S.get("stress") or []
        if stx:
            L += ["**Stress P&L.** " + caps.get("stress", ""), "",
                  "| Scenario | Kind | Key moves | k | Stops honoured (R) | Gapped (R) |", "|---|---|---|---:|---:|---:|"]
            for s in stx:
                kind = {"replay": f"replay {s.get('window', '')}", "named": "named", "worst": "worst case"}[s["kind"]]
                if s.get("note"):
                    L.append(f"| {s['name']} | {kind} | {s['note']} | - | - | - |")
                    continue
                drv = s.get("drivers") or {}
                if s["kind"] == "worst":
                    drv = dict(sorted(drv.items(), key=lambda kv: -abs(kv[1] or 0))[:3])
                km = ", ".join(f"{m} {_f(v, 1, sign=True, pct=True)}" for m, v in drv.items())
                if s.get("missing"):
                    km += f" (no move for {', '.join(s['missing'])})"
                L.append(f"| {s['name']} | {kind} | {km} | {_f(s.get('k'), 1)} | {_f(s['honoured_r'], sign=True)} | {_f(s['gapped_r'], sign=True)} |")
            L += [""]
    lv = S.get("cta") or {}
    if lv:
        L += ["**CTA levels** (trend-follower proxy, observed closes). " + caps.get("cta", ""), "",
              "| Market | Last (date) | Daily sd | Flip 1m / 3m / 12m | Distance in daily sd | Flips by roll-off within 5 days | Vol-target scale | State | 24m return, vol pctile |",
              "|---|---|---:|---|---|---|---:|---|---|"]
        lab = {"21": "1m", "63": "3m", "252": "12m"}
        for m, x in lv.items():
            legs = x.get("legs", {})
            fl = " / ".join(_f(legs.get(h, {}).get("flip_level")) for h in lab)
            ds = " / ".join(_f(legs.get(h, {}).get("distance_sd"), 1, sign=True) for h in lab)
            ro = ", ".join(f"{lab[h]} in {legs[h]['rolloff_flip_days']}d" for h in lab if legs.get(h, {}).get("rolloff_flip_days")) or "-"
            pn = x.get("panic")
            pz = (f"{_f(pn['ret_24m_pct'], 1, sign=True, pct=True)}, {_f(pn['vol_pctile'], 0)}" + (" (panic)" if pn["panic"] else "")) if pn else "-"
            vs = _f(x.get("vol_scale")) + (" (shrinking)" if x.get("vol_shrinking") else "")
            L.append(f"| {x['name']} ({m}) | {_f(x['last'])} ({x['last_date']}) | {_f(x['daily_sd_pct'], 2, pct=True)} | {fl} | {ds} | {ro} | {vs} | {x.get('state') or '-'} | {pz} |")
        L += [""]
    if S.get("skipped"):
        L += ["Not in the risk model: " + "; ".join(f"`{s['id']}` ({s['reason']})" for s in S["skipped"]), ""]
    L += [caps.get("rule", ""), ""]
    return L


def cli(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="pmstack risk", description="Risk and crowding report (agent 8)")
    ap.add_argument("--date", help="as-of date (BRT), default today")
    ap.add_argument("--out", help="write the markdown report here")
    a = ap.parse_args(argv)
    print(report(date.fromisoformat(a.date) if a.date else None, Path(a.out) if a.out else None))
    return 0
