"""Report playbooks: reaction base rates for scheduled energy reports (specialists S1).

What it measures, for each report and (series, market) pair in config/energy.yaml, on daily closes:
  - surprise proxy: the week's change minus the average change in the same and adjacent weeks of the prior five years
    (the monitor's and balance keeper's definition; no paid survey exists here), in sd of those changes
  - release-day volatility vs other days (ratio of sd, Levene p), and the big-move rate (|return| > 1.5 trailing sd)
    on release days vs other days, with Wilson intervals
  - sign agreement on releases with |z| >= 1: a bigger-than-normal draw with a price rise (the storage-theory sign)
  - slope of the release-day return on the surprise (per 1 sd and per 1 million barrels / 1 bcf), HC1 errors
  - halves, the day before and the day after as placebos (pre-release drift or leakage; delayed reaction)

Why this shape (docs/research/energy.md): announcement studies find inventory surprises move energy futures on
release, measured against survey expectations; without a survey the five-year same-week change is the proxy, and
its error is a known weakness, so the base rates are descriptive. They explain the release-day move and do not
predict anything: the release-day return is contemporaneous. Nothing here may alert (agent 12's gate decides that).

Point in time: `--date D` uses only releases on or before D, prices up to D, and history known then.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import runlog, store

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "energy.yaml"
KNOWLEDGE = ROOT / "knowledge"


def cfg() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ release dates
def _holidays(start: date, end: date) -> set[date]:
    from pandas.tseries.holiday import USFederalHolidayCalendar
    return {d.date() for d in USFederalHolidayCalendar().holidays(start=start, end=end)}


def release_date(week_ending: date, rel: dict, hol: set[date] | None = None) -> date:
    """Week ending Friday -> the report's release date (holiday shifts approximate; flagged in the output)."""
    exc = rel.get("exceptions") or {}
    if str(week_ending) in exc:                      # dates checked against EIA's schedule pages
        return date.fromisoformat(str(exc[str(week_ending)]))
    hol = hol if hol is not None else _holidays(week_ending, week_ending + timedelta(days=10))
    d = week_ending + timedelta(days=int(rel["lag_days"]))
    lo, hi = rel.get("holiday_window", [3, rel["lag_days"]])
    days = [week_ending + timedelta(days=k) for k in range(int(lo), int(hi) + 1)]
    h = next((x for x in days if x in hol), None)
    if h is not None:
        by_day = rel.get("holiday_shift")            # shift by the holiday's weekday (review A15: gas differs from oil)
        shift = int(by_day.get(h.strftime("%a"), 0)) if by_day else int(rel.get("shift_days", 1))
        d = d + timedelta(days=shift)
    return d


# ------------------------------------------------------------------ data
def _series(con, source: str, sid: str, until: date) -> pd.Series:
    df = con.execute("SELECT date, value FROM obs WHERE source = ? AND series_id = ? AND date <= ? ORDER BY date",
                     [source, sid, until]).df()
    if df.empty:
        return pd.Series(dtype=float)
    return pd.Series(df["value"].values, index=pd.to_datetime(df["date"]).dt.date).groupby(level=0).last()


def surprises(stocks: pd.Series, rel: dict, st: dict, asof: date) -> pd.DataFrame:
    """One row per weekly release known by `asof`: change, the 5-year average change and its sd, surprise and z.

    Same definition as the monitor's EIA table and the balance keeper (weekly changes in the same and adjacent ISO
    weeks of the prior five calendar years), so a fact pack and a playbook never show two different "5-year average
    changes" or surprise z-scores for one week. Only earlier years enter each week's norm (point in time)."""
    if len(stocks) < 60:
        return pd.DataFrame()
    s = stocks.sort_index()
    x = pd.DataFrame({"value": s.values}, index=s.index)
    x["chg"] = x["value"].diff()
    x["wk"] = [d.isocalendar()[1] for d in x.index]
    x["yr"] = [d.year for d in x.index]
    x = x.dropna(subset=["chg"])
    years = int(st["norm_years"])
    hol = _holidays(x.index[0], asof + timedelta(days=10))
    yr, wk, chg = x["yr"].to_numpy(), x["wk"].to_numpy(), x["chg"].to_numpy()
    rows = []
    for i, d in enumerate(x.index):
        r = release_date(d, rel, hol)
        if r > asof:
            continue
        dw = np.abs(wk - wk[i])
        m = (yr >= yr[i] - years) & (yr < yr[i]) & ((dw <= 1) | (dw >= 51))
        near = chg[m]
        if len(near) < years:
            continue
        mu, sd = float(near.mean()), float(near.std(ddof=1))
        rows.append({"week_ending": d, "release": r, "level": float(x["value"].iloc[i]), "change": float(chg[i]),
                     "avg5_change": mu, "seasonal_sd": sd, "n_norm": int(len(near)), "surprise": float(chg[i] - mu),
                     "z": float((chg[i] - mu) / sd) if sd > 0 else float("nan")})
    return pd.DataFrame(rows)


def returns(px: pd.Series, st: dict) -> pd.DataFrame:
    """Daily log returns in %, trailing sd, and a robust outlier screen (roll gaps, non-positive prints)."""
    p = px[px > 0]
    r = 100 * np.log(p / p.shift(1))
    r = r.dropna()
    df = pd.DataFrame({"ret": r})
    df["sd"] = df["ret"].shift(1).rolling(int(st["vol_window"]), min_periods=20).std()
    med = df["ret"].shift(1).rolling(250, min_periods=60).median()
    mad = (df["ret"].shift(1) - med).abs().rolling(250, min_periods=60).median() * 1.4826
    df["outlier"] = (df["ret"] - med).abs() > float(st["outlier_sd"]) * mad
    return df


# ------------------------------------------------------------------ statistics
def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float | None, float | None]:
    if n == 0:
        return None, None
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h


def ols_hc1(x: np.ndarray, y: np.ndarray) -> dict:
    n = len(x)
    if n < 10:
        return {"n": n}
    X = np.column_stack([np.ones(n), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    xtx = np.linalg.inv(X.T @ X)
    meat = X.T @ (X * (e ** 2)[:, None])
    cov = xtx @ meat @ xtx * n / (n - 2)
    se = float(math.sqrt(cov[1, 1]))
    r2 = 1 - float(e @ e) / float(((y - y.mean()) ** 2).sum()) if n > 2 else None
    return {"n": n, "slope": float(beta[1]), "se": se, "t": float(beta[1] / se) if se else None,
            "ci90": [float(beta[1] - 1.645 * se), float(beta[1] + 1.645 * se)], "r2": r2}


def _r(x, nd=3):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else round(float(x), nd)


ENERGY_ERAS = (("before_2006-06", "1900-01-01", "2006-06-06"), ("2006-06_to_2014", "2006-06-06", "2015-01-01"),
               ("since_2015", "2015-01-01", "2999-01-01"))


def base_rates(sur: pd.DataFrame, rets: pd.DataFrame, st: dict, unit_scale: float, eras_def=None) -> dict:
    """Release-day stats for one (series, market) pair."""
    rr = rets[~rets["outlier"]]
    dropped = int(rets["outlier"].sum())
    ev = sur.dropna(subset=["z"]).copy()
    ev = ev[ev["release"].isin(rr.index)]
    if ev.empty:
        return {"status": "insufficient", "events": 0}
    first = ev["release"].min()
    span = rr[rr.index >= first]
    is_ev = span.index.isin(set(ev["release"]))
    on, off = span[is_ev], span[~is_ev]
    from scipy import stats as sps
    lev_p = float(sps.levene(on["ret"], off["ret"]).pvalue) if len(on) > 5 and len(off) > 5 else None
    big_on = int((on["ret"].abs() > st["big_move_sd"] * on["sd"]).sum())
    big_off = int((off["ret"].abs() > st["big_move_sd"] * off["sd"]).sum())
    n_on, n_off = int(on["sd"].notna().sum()), int(off["sd"].notna().sum())
    ev["ret"] = ev["release"].map(rr["ret"])
    ev["ret_prev"] = ev["release"].map(lambda d: _neighbour(rr, d, -1))
    ev["ret_next"] = ev["release"].map(lambda d: _neighbour(rr, d, +1))
    strong = ev[ev["z"].abs() >= st["hit_z"]]
    hits = int((np.sign(strong["ret"]) == -np.sign(strong["z"])).sum())
    k_lo, k_hi = wilson(hits, len(strong))
    hit_p = float(sps.binomtest(hits, len(strong), 0.5).pvalue) if len(strong) else None
    reg_z = ols_hc1(ev["z"].to_numpy(), ev["ret"].to_numpy())
    reg_u = ols_hc1((ev["surprise"] / unit_scale).to_numpy(), ev["ret"].to_numpy())
    half = ev["release"].iloc[len(ev) // 2]
    halves = {}
    for name, part in (("first", ev[ev["release"] < half]), ("second", ev[ev["release"] >= half])):
        sp = part[part["z"].abs() >= st["hit_z"]]
        h = int((np.sign(sp["ret"]) == -np.sign(sp["z"])).sum())
        rz = ols_hc1(part["z"].to_numpy(), part["ret"].to_numpy())
        halves[name] = {"from": str(part["release"].min()), "to": str(part["release"].max()), "events": len(part),
                        "slope_per_sd": _r(rz.get("slope")), "t": _r(rz.get("t"), 2),
                        "hit_rate": _r(h / len(sp)) if len(sp) else None, "strong_n": len(sp)}
    # eras (docs/research/energy.md): the petroleum reaction weakened after 24-hour electronic trading (Jun 2006) and
    # the shale/export era (2015 on) may differ again: the recent block is the base rate when it is under half the full one
    eras = {}
    for name, lo, hi in (eras_def or ENERGY_ERAS):     # metals pass their own (pmstack/metals.py)
        part = ev[(ev["release"] >= date.fromisoformat(lo)) & (ev["release"] < date.fromisoformat(hi))]
        if len(part) < st["min_events"]:
            eras[name] = {"events": len(part), "status": "insufficient"}
            continue
        sp = part[part["z"].abs() >= st["hit_z"]]
        h = int((np.sign(sp["ret"]) == -np.sign(sp["z"])).sum())
        rz = ols_hc1(part["z"].to_numpy(), part["ret"].to_numpy())
        lo_, hi_ = wilson(h, len(sp))
        eras[name] = {"events": len(part), "slope_per_sd": _r(rz.get("slope")), "t": _r(rz.get("t"), 2),
                      "ci90": [_r(x) for x in rz.get("ci90", [None, None])], "hit_rate": _r(h / len(sp)) if len(sp) else None,
                      "hit_ci95": [_r(lo_), _r(hi_)], "strong_n": len(sp)}
    rec, full = eras.get("since_2015", {}), reg_z.get("slope")
    use_recent = bool(rec.get("slope_per_sd") is not None and full and abs(rec["slope_per_sd"]) < 0.5 * abs(full))
    plac = {}
    for name, col in (("day_before", "ret_prev"), ("day_after", "ret_next")):
        sub = ev.dropna(subset=[col])
        rz = ols_hc1(sub["z"].to_numpy(), sub[col].to_numpy())
        plac[name] = {"slope_per_sd": _r(rz.get("slope")), "t": _r(rz.get("t"), 2), "n": rz.get("n")}
    n = len(ev)
    status = "insufficient" if n < st["min_events"] else "ok"
    return {
        "status": status, "events": n, "from": str(ev["release"].min()), "to": str(ev["release"].max()),
        "outliers_dropped": dropped,
        "vol": {"sd_release": _r(on["ret"].std()), "sd_other": _r(off["ret"].std()),
                "ratio": _r(on["ret"].std() / off["ret"].std()) if len(off) else None, "levene_p": _r(lev_p, 4)},
        "big_move": {"release_rate": _r(big_on / n_on) if n_on else None, "release_ci95": [_r(x) for x in wilson(big_on, n_on)],
                     "other_rate": _r(big_off / n_off) if n_off else None, "other_ci95": [_r(x) for x in wilson(big_off, n_off)],
                     "lift": _r((big_on / n_on) / (big_off / n_off)) if n_on and n_off and big_off else None,
                     "threshold_sd": st["big_move_sd"]},
        "sign": {"strong_n": len(strong), "hits": hits, "hit_rate": _r(hits / len(strong)) if len(strong) else None,
                 "ci95": [_r(k_lo), _r(k_hi)], "binom_p": _r(hit_p, 4), "z_min": st["hit_z"],
                 "meaning": "share of releases with |surprise z| >= z_min where the price moved against the surprise (bigger draw, price up)"},
        "slope_per_sd": {k: _r(v, 4) if isinstance(v, float) else v for k, v in reg_z.items()},
        "slope_per_unit": {k: _r(v, 4) if isinstance(v, float) else v for k, v in reg_u.items()},
        "halves": halves, "eras": eras, "placebo": plac,
        "base_rate_block": "since_2015" if use_recent else "full",
        "base_rate_note": ("recent block (since 2015) is under half the full-sample slope: quote it as the base rate" if use_recent
                           else "recent block within half of the full-sample slope: the full sample stands"),
    }


def _neighbour(rr: pd.DataFrame, d, k: int):
    i = rr.index.searchsorted(d)
    j = i + k
    if i >= len(rr) or rr.index[i] != d or j < 0 or j >= len(rr):
        return None
    return float(rr["ret"].iloc[j])


def latest(sur: pd.DataFrame) -> dict | None:
    if sur.empty:
        return None
    r = sur.iloc[-1]
    return {"week_ending": str(r["week_ending"]), "release": str(r["release"]), "change": _r(r["change"], 1),
            "avg5_change": _r(r["avg5_change"], 1), "seasonal_sd": _r(r["seasonal_sd"], 1), "surprise": _r(r["surprise"], 1),
            "z": _r(r["z"], 2) if pd.notna(r["z"]) else None}


def conditional(sur: pd.DataFrame, rets: pd.DataFrame, z_now: float | None) -> dict | None:
    """How the market moved on past releases with a surprise on the same side and at least as large as today's."""
    if z_now is None or not math.isfinite(z_now) or abs(z_now) < 1:
        return None
    rr = rets[~rets["outlier"]]
    ev = sur.dropna(subset=["z"])
    latest_rel = sur["release"].max()
    ev = ev[ev["release"].isin(rr.index) & (ev["release"] < latest_rel)]   # past releases only, not the latest itself
    same = ev[(np.sign(ev["z"]) == np.sign(z_now)) & (ev["z"].abs() >= min(abs(z_now), 2.0))]
    if len(same) < 10:
        return {"n": len(same), "note": "fewer than 10 comparable releases"}
    rs = same["release"].map(rr["ret"])
    up = int((rs > 0).sum())
    lo, hi = wilson(up, len(rs))
    return {"n": len(rs), "z_at_least": _r(min(abs(z_now), 2.0), 2), "side": "build" if z_now > 0 else "draw",
            "mean_ret_pct": _r(rs.mean()), "median_ret_pct": _r(rs.median()), "up_share": _r(up / len(rs)),
            "up_ci95": [_r(lo), _r(hi)]}


# ------------------------------------------------------------------ run
def run(asof: date | None = None, con=None, write: bool = False, only: list[str] | None = None) -> dict:
    c = cfg()
    st = c["stats"]
    asof = asof or (datetime.now(timezone.utc) - timedelta(hours=3)).date()
    con = con or store.connect()
    out = {"asof": asof.isoformat(), "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
           "method": "docs/research/energy.md (EIA playbooks)", "reports": {}}
    for rkey, rep in c["events"].items():
        if only and rkey not in only:
            continue
        rows = {}
        for pr in rep["pairs"]:
            stocks = _series(con, pr["source"], pr["series"], asof)
            px = _series(con, "prices", pr["market"], asof)
            px = px[px.index >= date.fromisoformat(st["start"])]
            if stocks.empty or px.empty:
                rows[pr["key"]] = {**pr, "status": "no data"}
                continue
            sur = surprises(stocks, rep["release"], st, asof)
            rets = returns(px, st)
            scale = 1000.0 if "PET." in pr["series"] else 1.0           # kbbl -> million barrels; bcf stays bcf
            br = base_rates(sur, rets, st, scale) if not sur.empty else {"status": "insufficient", "events": 0}
            lt = latest(sur)
            rows[pr["key"]] = {**pr, "unit_per": "1 million barrels" if scale == 1000.0 else "1 bcf", **br,
                               "latest": lt, "comparable": conditional(sur, rets, lt and lt.get("z")),
                               "series_url": f"https://www.eia.gov/opendata/browser/ (series {pr['series']})"}
        out["reports"][rkey] = {"name": rep["name"], "url": rep["url"], "schedule_url": rep.get("schedule_url"),
                                "release": rep["release"], "pairs": rows,
                                "next_release": next_release(rep["release"], asof)}
    if write:
        write_outputs(out)
    return out


def next_release(rel: dict, asof: date) -> str:
    """The next release on or after `asof` (approximate around holidays; EIA's schedule page is the authority)."""
    wk = asof - timedelta(days=(asof.weekday() - 4) % 7)          # last Friday on or before asof
    for k in range(-1, 3):
        d = release_date(wk + timedelta(days=7 * k), rel)
        if d >= asof:
            return d.isoformat()
    return release_date(wk + timedelta(days=21), rel).isoformat()


def write_outputs(out: dict) -> list[Path]:
    """One JSON per pair under knowledge/energy/<commodity>/estimates/, and the code table in events.md."""
    paths = []
    by_com: dict[str, list[tuple[str, dict, dict]]] = {}
    for rkey, rep in out["reports"].items():
        for key, row in rep["pairs"].items():
            if row.get("status") == "no data":
                continue
            folder = KNOWLEDGE / "energy" / row["commodity"] / "estimates"
            folder.mkdir(parents=True, exist_ok=True)
            p = folder / f"{rkey}-{key}.json"
            p.write_text(json.dumps({"asof": out["asof"], "report": rkey, "name": rep["name"], "url": rep["url"], **row},
                                    indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            paths.append(p)
            by_com.setdefault(row["commodity"], []).append((rkey, rep, row))
    for com, items in by_com.items():
        paths.append(_events_block(com, items, out["asof"]))
    return paths


BLOCK_START = "<!-- code: reaction base rates (pmstack events --write) -->"
BLOCK_END = "<!-- /code -->"


def _fmt(x, nd=2, pct=False):
    if x is None:
        return "-"
    return f"{100 * x:.0f}%" if pct else f"{x:.{nd}f}"


def _events_block(com: str, items: list, asof: str) -> Path:
    f = KNOWLEDGE / "energy" / com / "events.md"
    text = f.read_text(encoding="utf-8") if f.exists() else f"# Event playbooks: {com}\n"
    lines = [BLOCK_START, f"## Reaction base rates (code, as of {asof})", "",
             "Daily closes (Yahoo continuous front month, personal use only) on release days vs other days. Surprise = the week's change "
             "minus the average change in the same and adjacent weeks of the prior 5 years, in sd of those changes (the fact pack's surprise z). Contemporaneous: explains the release-day move, "
             "predicts nothing. Full numbers: `estimates/*.json`.", "",
             "| Report / pair | Events | Vol ratio (release / other) | Big-move rate release vs other (lift) | Sign hit at abs(z) >= 1 (95% CI) | Slope per 1 sd (t) | Slope per unit (t) | Halves: slope per sd | Since 2015: slope per sd (t), hit | Placebo day before / after (t) |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for rkey, rep, r in items:
        if r.get("status") not in ("ok", "insufficient") or not r.get("events"):
            lines.append(f"| {rkey} {r['label']} | {r.get('status')} | | | | | | | | |")
            continue
        v, b, s, z, u, h, pl = r["vol"], r["big_move"], r["sign"], r["slope_per_sd"], r["slope_per_unit"], r["halves"], r["placebo"]
        lines.append(
            f"| {rkey} {r['label']} | {r['events']} ({r['from'][:4]}-{r['to'][:4]}){' insufficient' if r['status'] == 'insufficient' else ''} | "
            f"{_fmt(v['ratio'])} | {_fmt(b['release_rate'], pct=True)} vs {_fmt(b['other_rate'], pct=True)} ({_fmt(b['lift'])}) | "
            f"{_fmt(s['hit_rate'], pct=True)} of {s['strong_n']} ({_fmt(s['ci95'][0], pct=True)}-{_fmt(s['ci95'][1], pct=True)}) | "
            f"{_fmt(z.get('slope'))}% ({_fmt(z.get('t'), 1)}) | {_fmt(u.get('slope'), 3)}% per {r['unit_per']} ({_fmt(u.get('t'), 1)}) | "
            f"{_fmt(h['first']['slope_per_sd'])} / {_fmt(h['second']['slope_per_sd'])} | "
            f"{_fmt(r['eras']['since_2015'].get('slope_per_sd'))} ({_fmt(r['eras']['since_2015'].get('t'), 1)}), {_fmt(r['eras']['since_2015'].get('hit_rate'), pct=True)}{' (base rate)' if r['base_rate_block'] == 'since_2015' else ''} | "
            f"{_fmt(pl['day_before']['slope_per_sd'])} ({_fmt(pl['day_before']['t'], 1)}) / {_fmt(pl['day_after']['slope_per_sd'])} ({_fmt(pl['day_after']['t'], 1)}) |")
    lines += ["", "Release dates follow EIA's rule (Wednesday 10:30 ET for petroleum, Thursday for gas; holidays shift them) and are "
              "approximate around holidays (EIA's holiday alternates are mostly Thursday 12:00 ET, still before the settle). Slopes against a free proxy are attenuated "
              "lower bounds (Halova, Kurov & Kucher 2014); the day before carries part of the reaction (API Tuesday 16:30 ET; Miao et al. 2018). Outliers beyond 8 robust sd (roll gaps, April 2020) are dropped and counted in the JSON.", BLOCK_END]
    block = "\n".join(lines)
    import re
    if BLOCK_START in text:
        text = re.sub(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END), lambda m: block, text, flags=re.S)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    return f


def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack events")
    p.add_argument("--date", help="as-of date (point in time), default today BRT")
    p.add_argument("--only", help="report keys, comma-separated (wpsr, wngsr)")
    p.add_argument("--write", action="store_true", help="write estimates/*.json and the events.md code tables")
    a = p.parse_args(argv)
    out = run(date.fromisoformat(a.date) if a.date else None, write=a.write, only=a.only.split(",") if a.only else None)
    summ = {k: {pk: {"status": pv.get("status"), "events": pv.get("events"), "slope_per_sd": (pv.get("slope_per_sd") or {}).get("slope"),
                     "t": (pv.get("slope_per_sd") or {}).get("t"), "latest_z": (pv.get("latest") or {}).get("z")}
                for pk, pv in v["pairs"].items()} | {"next_release": v["next_release"]} for k, v in out["reports"].items()}
    runlog.log(runlog.new_run_id(), "events:base-rates", "ok", asof=out["asof"], write=a.write, reports=summ)
    print(json.dumps(summ, indent=1, default=str))
    return 0
