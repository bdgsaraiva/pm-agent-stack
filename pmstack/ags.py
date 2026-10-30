"""Ags specialist (S4): report playbooks for WASDE, Crop Progress, Grain Stocks and Acreage, on daily closes.

Code computes, the model writes. Point in time: `--date D` uses only releases on or before D and prices up to D.
  - report days (WASDE, Grain Stocks, Acreage + Prospective Plantings): volatility on the report day vs other days,
    big-move lift, placebo days (metals.day_vol), with exact dates from USDA ESMIS. WASDE also gets eras (the release
    moved into trading hours in May 2013) and, from 2021 (WASDE as first published, agent 9), the same-day return
    against the revision of US ending stocks vs the previous report, in sd of revisions: a weak proxy, since there is
    no consensus and part of the revision was expected.
  - crop progress: the week's good/excellent change vs the same and adjacent ISO weeks of the prior 5 seasons, in
    sd (events.surprises), priced on the next trading day (the report comes out at 16:00 ET, after the close), with
    July-August apart (Lehecka 2014). Release dates come from ESMIS: NASS rows are dated at the Monday even when a
    holiday moved the report to Tuesday or later.
Contemporaneous, never a forecast; nothing alerts. Evidence: docs/research/ags.md. `--write` saves
knowledge/ags/<commodity>/estimates/*.json and the events.md code tables.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import events, metals, runlog, store

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "ags.yaml"
KNOWLEDGE = ROOT / "knowledge" / "ags"


def cfg() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def _today() -> date:
    return (datetime.now(timezone.utc) - timedelta(hours=3)).date()


def _r(x, nd=3):
    return events._r(x, nd)


def release_dates(con, series, asof: date) -> list[date]:
    out = set()
    for sid in ([series] if isinstance(series, str) else series):
        out |= set(events._series(con, "esmis", sid, asof).index)
    return sorted(out)


def report_set(con, rep: dict, asof: date) -> list[date]:
    """Days of one report category: union of `include`, kept only if also in every `require` series, minus `exclude`
    (review S4: Grain Stocks shares its day with Prospective Plantings/Acreage in March and June and with WASDE in
    January, so categories are disjoint and no day counts twice)."""
    days = set(release_dates(con, rep["include"], asof))
    for sid in rep.get("require") or []:
        days &= set(release_dates(con, sid, asof))
    for sid in rep.get("exclude") or []:
        days -= set(release_dates(con, sid, asof))
    return sorted(days)


def _rets(con, ref: str, asof: date, st: dict) -> pd.DataFrame:
    px = events._series(con, "prices", ref, asof)
    px = px[px.index >= date.fromisoformat(st["start"])]
    return events.returns(px, st) if len(px) > 300 else pd.DataFrame()


def era_vol(rets: pd.DataFrame, days: list[date], st: dict, eras) -> dict:
    out = {}
    for name, lo, hi in eras or []:
        lo, hi = date.fromisoformat(lo), date.fromisoformat(hi)
        sub = rets[(rets.index >= lo) & (rets.index < hi)]
        dd = [d for d in days if lo <= d < hi]
        out[name] = {k: v for k, v in metals.day_vol(sub, dd, st).items() if k in ("events", "ratio", "levene_p", "lift", "status")} if len(sub) > 100 else {"events": 0}
    return out


# ------------------------------------------------------------------ WASDE revision proxy
def wasde_revisions(con, prefix: str, asof: date) -> pd.DataFrame:
    """Per WASDE (as first published, 2021 on): US ending stocks for the newest market year in that report, and its
    change vs the previous report for the same market year."""
    df = con.execute("SELECT series_id, date, value FROM obs WHERE source = 'wasde' AND series_id LIKE ? AND date <= ? ORDER BY date",
                     [prefix + ":%", asof]).df()
    if df.empty:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["my"] = df["series_id"].str.split(":").str[-1]
    df = df.drop_duplicates(["series_id", "date"], keep="last")
    rows = []
    reps = sorted(df["date"].unique())
    for i, d in enumerate(reps[1:], 1):
        cur = df[df["date"] == d]
        my = max(cur["my"])
        prev = df[(df["date"] == reps[i - 1]) & (df["my"] == my)]
        if prev.empty:
            continue
        v, p = float(cur[cur["my"] == my]["value"].iloc[0]), float(prev["value"].iloc[0])
        rows.append({"release": d, "my": my, "level": v, "change": v - p, "change_pct": 100 * (v / p - 1) if p else None})
    out = pd.DataFrame(rows)
    if len(out) > 5:
        sd = out["change_pct"].expanding(min_periods=8).std().shift(1)   # only earlier revisions scale today's (point in time)
        out["z"] = out["change_pct"] / sd.where(sd > 0)
    return out


def revision_fit(rev: pd.DataFrame, rets: pd.DataFrame) -> dict | None:
    if rev.empty or "z" not in rev:
        return None
    rr = rets[~rets["outlier"]]
    ev = rev[np.isfinite(rev["z"].astype(float))].copy()
    ev["ret"] = ev["release"].map(rr["ret"])
    ev = ev.dropna(subset=["ret"])
    if len(ev) < 15:
        return {"n": len(ev), "status": "insufficient"}
    f = events.ols_hc1(ev["z"].to_numpy(), ev["ret"].to_numpy())
    strong = ev[ev["z"].abs() >= 1]
    hits = int((np.sign(strong["ret"]) == -np.sign(strong["z"])).sum())
    lo, hi = events.wilson(hits, len(strong))
    last = rev.iloc[-1]
    return {"n": len(ev), "from": str(ev["release"].min()), "to": str(ev["release"].max()),
            "slope_per_sd": _r(f.get("slope"), 4), "t": _r(f.get("t"), 2), "ci90": [_r(x, 4) for x in f.get("ci90", [None, None])],
            "hit_rate": _r(hits / len(strong)) if len(strong) else None, "hit_n": len(strong), "hit_ci95": [_r(lo), _r(hi)],
            "hit_status": "ok" if len(strong) >= 30 else "insufficient (fewer than 30 revisions of at least 1 sd)",
            "latest": {"release": str(last["release"]), "my": last["my"], "level": _r(last["level"], 1), "change": _r(last["change"], 1),
                       "change_pct": _r(last["change_pct"], 2), "z": _r(last.get("z"), 2)},
            "meaning": "same-day return per 1 sd of the US ending-stocks revision vs the previous WASDE (no consensus: a weak proxy)"}


def placebo_ratio(rets: pd.DataFrame, days: list[date], shift: int, blocked: set, st: dict) -> dict:
    """Both measures on the report days shifted `shift` trading days, leaving out shifted days within one trading
    day of any USDA report (e.g. 10 days after Acreage is the July WASDE): a placebo must be a quiet day."""
    idx = rets.index
    pos = [p + shift for p in idx.searchsorted(days)]
    cand = [idx[p] for p in pos if 0 <= p < len(idx)]
    near = set()
    for d in blocked:
        q = idx.searchsorted(d)
        near |= {idx[k] for k in (q - 1, q, q + 1) if 0 <= k < len(idx)}
    keep = [d for d in cand if d not in near]
    loc = local_ratio(rets, keep, blocked, st)
    return {"days": len(keep), "ratio_all": metals.day_vol(rets, keep, st).get("ratio"), "local": loc.get("ratio"), "local_t": loc.get("t_paired")}


def local_ratio(rets: pd.DataFrame, days: list[date], blocked: set, st: dict, window: int = 10) -> dict:
    """Report-day abs(return) / trailing sd vs the same for the `window` trading days either side (other report days
    left out): a seasonal control, since report days cluster in high-volatility months (June-July weather)."""
    rr = rets[~rets["outlier"]].dropna(subset=["sd"])
    idx = rr.index
    scaled = (rr["ret"].abs() / rr["sd"]).to_numpy()
    bpos = set(idx.searchsorted(sorted(blocked)))
    ev, ctl, pairs = [], [], []
    for d in days:
        p = idx.searchsorted(d)
        if p >= len(idx) or idx[p] != d:
            continue
        around = [k for k in range(p - window, p + window + 1) if 0 <= k < len(idx) and k != p and k not in bpos]
        if len(around) < window:
            continue
        ev.append(scaled[p])
        c_ = float(np.mean(scaled[around]))
        ctl.append(c_)
        pairs.append(scaled[p] - c_)
    if len(ev) < 10:
        return {"events": len(ev), "status": "insufficient"}
    diff = np.array(pairs)
    t = float(diff.mean() / (diff.std(ddof=1) / math.sqrt(len(diff)))) if diff.std(ddof=1) > 0 else None
    return {"events": len(ev), "ratio": _r(float(np.mean(ev)) / float(np.mean(ctl))), "t_paired": _r(t, 2),
            "meaning": f"mean abs(return)/sd on report days over the mean of the {window} trading days either side (other report days left out)"}


def report_days(asof: date, con, c: dict) -> dict:
    st = c["stats"]
    out = {}
    blocked0 = set(release_dates(con, c["report_series"], asof))     # every USDA report day
    cp_rel = release_dates(con, c["crop_progress"]["release_series"], asof)
    for key, rep in c["reports"].items():
        days = report_set(con, rep, asof)
        rows = {}
        for m in rep["markets"]:
            mk = c["markets"][m]
            rets = _rets(con, mk["ref"], asof, st)
            if rets.empty or len(days) < 10:
                rows[m] = {"market": mk["ref"], "status": "no data"}
                continue
            # Crop Progress is priced the next trading day (it comes out after the close): those days are not quiet either
            idx = rets.index
            cp_next = {idx[p] for p in idx.searchsorted(cp_rel, side="right") if p < len(idx)}
            blocked = blocked0 | cp_next
            base = metals.day_vol(rets, days, st)
            base["placebo"] = {f"{s:+d}d": placebo_ratio(rets, days, s, blocked, st) for s in st["placebo_shifts"]}
            base["local"] = local_ratio(rets, days, blocked - set(days), st)
            if rep.get("eras"):
                base["eras"] = era_vol(rets, days, st, rep["eras"])
            if (rep.get("revision") or {}).get(m):
                base["revision"] = revision_fit(wasde_revisions(con, rep["revision"][m], asof), rets)
            rows[m] = {"market": mk["ref"], "label": mk["label"], **base}
        out[key] = {"name": rep["name"], "url": rep["url"], "time_et": rep["time_et"], "events_known": len(days),
                    "last_release": str(days[-1]) if days else None, "markets": rows}
    return out


# ------------------------------------------------------------------ crop progress
def condition_series(con, crop: dict, releases: list[date], asof: date) -> pd.Series:
    """Good + excellent %, re-dated at the actual ESMIS release (the first release on or after the NASS date, within
    3 days), so holiday weeks are never read early."""
    g = events._series(con, "nass", crop["good"], asof + timedelta(days=5))
    e = events._series(con, "nass", crop["excellent"], asof + timedelta(days=5))
    ge = (g + e).dropna()
    rel = pd.Index(releases)
    out = {}
    for d, v in ge.items():
        p = rel.searchsorted(d)
        if p < len(rel) and (rel[p] - d).days <= 3 and rel[p] <= asof:
            out[rel[p]] = float(v)
    return pd.Series(out, dtype=float).sort_index()


def season_surprises(ge: pd.Series, years: int, asof: date) -> pd.DataFrame:
    """Weekly changes within a season only (a change across a gap over 10 days, i.e. the first report of a season vs
    last autumn's final rating, is not a change), each against the changes in the same and adjacent ISO weeks of the
    prior `years` seasons. An event needs changes from `years` distinct prior seasons (review S4: the norm used to
    include cross-season jumps, and the season count was off by one)."""
    s = ge[ge.index <= asof].sort_index()
    if len(s) < 30:
        return pd.DataFrame()
    x = pd.DataFrame({"value": s.values}, index=s.index)
    span = pd.Series([None] + [(b - a).days for a, b in zip(s.index[:-1], s.index[1:])], index=s.index)
    x["chg"] = x["value"].diff().where(span <= 10)
    x["wk"] = [d.isocalendar()[1] for d in x.index]
    x["yr"] = [d.year for d in x.index]
    ok = x.dropna(subset=["chg"])
    yr, wk, chg = ok["yr"].to_numpy(), ok["wk"].to_numpy(), ok["chg"].to_numpy()
    rows = []
    for i, d in enumerate(ok.index):
        dw = np.abs(wk - wk[i])
        m = (yr >= yr[i] - years) & (yr < yr[i]) & ((dw <= 1) | (dw >= 51))
        if len(set(yr[m])) < years:
            continue
        near = chg[m]
        mu, sd = float(near.mean()), float(near.std(ddof=1))
        rows.append({"week_ending": d, "release": d, "level": float(ok["value"].iloc[i]), "change": float(chg[i]),
                     "avg5_change": mu, "seasonal_sd": sd, "n_norm": int(len(near)), "surprise": float(chg[i] - mu),
                     "z": float((chg[i] - mu) / sd) if sd > 0 else float("nan")})
    return pd.DataFrame(rows)


def next_day(sur: pd.DataFrame, rets: pd.DataFrame) -> pd.DataFrame:
    """Price each release on the first trading day strictly after it (released after the close)."""
    if sur.empty:
        return sur
    idx = rets.index
    pos = idx.searchsorted(list(sur["release"]), side="right")
    sur = sur.copy()
    sur["release"] = [idx[p] if p < len(idx) else None for p in pos]
    return sur.dropna(subset=["release"]).drop_duplicates("release", keep="last").reset_index(drop=True)


def crop_progress(asof: date, con, c: dict) -> dict:
    cp, st = c["crop_progress"], c["stats"]
    releases = release_dates(con, cp["release_series"], asof)
    out = {}
    for key, crop in cp["crops"].items():
        mk = c["markets"][crop["market"]]
        ge = condition_series(con, crop, releases, asof)
        rets = _rets(con, mk["ref"], asof, st)
        if len(ge) < 60 or rets.empty:
            out[key] = {"crop": key, "market": mk["ref"], "status": "no data"}
            continue
        sur = season_surprises(ge, int(st["norm_years"]), asof)
        priced = next_day(sur, rets)
        eras = [tuple(e) for e in cp["eras"]]
        br = events.base_rates(priced, rets, st, 1.0, eras) if len(priced) else {"status": "insufficient", "events": 0}
        wk_of = dict(zip(next_day(sur, rets)["release"], sur.loc[next_day(sur, rets).index, "week_ending"])) if len(priced) else {}
        peak = priced[[wk_of.get(d, d).month in cp["peak_months"] for d in priced["release"]]] if len(priced) else priced
        pk = events.base_rates(peak, rets, st, 1.0, eras) if len(peak) >= 10 else {"status": "insufficient", "events": len(peak)}
        lt = events.latest(sur) if len(sur) else None
        if lt:
            lt["note"] = "latest release with a seasonal norm" + ("" if lt["release"] == str(ge.index[-1]) else f" (later releases up to {ge.index[-1]} have no norm: late-season weeks)")
        out[key] = {"crop": key, "market": mk["ref"], "label": f"{key.replace('_', ' ')} condition (good + excellent) vs {mk['label']}",
                    "unit_per": "1 pp", **br, "peak_months": {k: pk.get(k) for k in ("status", "events", "slope_per_sd", "sign")},
                    "latest": lt, "level": _r(float(ge.iloc[-1]), 1), "level_date": str(ge.index[-1]),
                    "norm": "weekly change in good + excellent vs the same and adjacent ISO weeks of the prior 5 seasons",
                    "series_url": "https://quickstats.nass.usda.gov/", "release_url": cp["url"]}
    return out


# ------------------------------------------------------------------ run and write
def run(asof: date | None = None, con=None, write: bool = False) -> dict:
    c = cfg()
    asof = asof or _today()
    con = con or store.connect()
    out = {"asof": asof.isoformat(), "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
           "method": "docs/research/ags.md", "reports": report_days(asof, con, c), "crop_progress": crop_progress(asof, con, c)}
    if write:
        write_outputs(out)
    return out


FOLDER = {"corn": "corn", "soybeans": "soybeans", "wheat": "wheat", "sugar": "sugar",
          "winter_wheat": "wheat", "spring_wheat": "wheat"}


def write_outputs(out: dict) -> list[Path]:
    paths = []

    def save(com, name, obj):
        f = KNOWLEDGE / com / "estimates" / f"{name}.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"asof": out["asof"], **obj}, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        paths.append(f)
    for rkey, rep in out["reports"].items():
        for m, row in rep["markets"].items():
            if row.get("status") != "no data":
                save(FOLDER[m], f"{rkey}-days", {**{k: v for k, v in rep.items() if k != "markets"}, **row})
    for key, row in out["crop_progress"].items():
        if row.get("status") != "no data":
            save(FOLDER[key], f"crop_progress-{key}", row)
    for com in ("corn", "soybeans", "wheat", "sugar"):
        paths.append(_events_block(com, out))
    return paths


BLOCK_START = "<!-- code: reaction base rates (pmstack ags --write) -->"
BLOCK_END = "<!-- /code -->"
_f = events._fmt


def _events_block(com: str, out: dict) -> Path:
    f = KNOWLEDGE / com / "events.md"
    text = f.read_text(encoding="utf-8") if f.exists() else f"# Event playbooks: {com}\n"
    L = [BLOCK_START, f"## Reaction base rates (code, as of {out['asof']})", "",
         "### Report days (volatility)", "Daily closes (Yahoo continuous front month, personal use only) on report days vs other days; exact dates from USDA ESMIS. "
         "Local ratio = the report day against the 10 trading days either side (a seasonal control: June-July days are volatile anyway). Placebo = the same days shifted 5 trading days back or 10 forward, leaving out USDA report days and Crop Progress reaction days (days and t in the JSON). Contemporaneous: predicts nothing. Full numbers: `estimates/*-days.json`.", "",
         "| Report day | Market | Events | Vol ratio (report / other) | Local ratio vs +-10 days (paired t) | Big-move rate report vs other (lift) | Levene p | Halves | Placebo -5d / +10d: vol ratio, local | Eras: ratio |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for rkey, rep in out["reports"].items():
        r = rep["markets"].get(com)
        if not r or not r.get("events"):
            continue
        hv, pl = r.get("halves") or {}, r.get("placebo") or {}
        er = "; ".join(f"{k} {_f(v.get('ratio'))} ({v.get('events')})" for k, v in (r.get("eras") or {}).items()) or "-"
        L.append(f"| {rep['name']} | {r['label']} | {r['events']} ({r['from'][:4]}-{r['to'][:4]}) | {_f(r.get('ratio'))} | "
                 f"{_f((r.get('local') or {}).get('ratio'))} ({_f((r.get('local') or {}).get('t_paired'), 1)}) | "
                 f"{_f(r.get('big_event'), pct=True)} vs {_f(r.get('big_other'), pct=True)} ({_f(r.get('lift'))}) | {_f(r.get('levene_p'), 3)} | "
                 f"{_f(hv.get('first'))} / {_f(hv.get('second'))} | {_f((pl.get('-5d') or {}).get('ratio_all'))}, {_f((pl.get('-5d') or {}).get('local'))} / {_f((pl.get('+10d') or {}).get('ratio_all'))}, {_f((pl.get('+10d') or {}).get('local'))} | {er} |")
    w = (out["reports"].get("wasde") or {}).get("markets", {}).get(com) or {}
    rv = w.get("revision") or {}
    if rv.get("n"):
        L += ["", f"WASDE revision proxy ({rv.get('from', '')[:4]} on, WASDE as first published): same-day return per 1 sd of the US ending-stocks revision "
              f"vs the previous report {_f(rv.get('slope_per_sd'), 3)}% (t {_f(rv.get('t'), 1)}, {rv['n']} reports); only {rv.get('hit_n')} revisions of at least 1 sd, "
              f"too few for a sign-agreement rate. No consensus is stored, so this is a weak, attenuated proxy."] if rv.get("hit_status") != "ok" else \
             ["", f"WASDE revision proxy ({rv.get('from', '')[:4]} on): {_f(rv.get('slope_per_sd'), 3)}% per sd (t {_f(rv.get('t'), 1)}, {rv['n']} reports); sign hit {_f(rv.get('hit_rate'), pct=True)} of {rv.get('hit_n')}."]
    rows = [r for k, r in out["crop_progress"].items() if FOLDER[k] == com and r.get("events")]
    if rows:
        L += ["", "### Crop Progress (condition)", "Next-day return (the report comes out at 16:00 ET, after the close) vs the week's good + excellent change against its "
              "seasonal norm (same and adjacent ISO weeks of the prior 5 seasons), in sd. Sign hit = a bigger-than-normal improvement with a price fall. Release dates from ESMIS.", "",
              "| Crop vs market | Events | Sign hit at abs(z) >= 1 (95% CI) | Slope per 1 sd (t) | Slope per 1 pp (t) | July-August: slope per sd (n) | Halves | Placebo day before / after (t) |",
              "|---|---|---|---|---|---|---|---|"]
        for r in rows:
            s, z, u, h, pl, pk = r["sign"], r["slope_per_sd"], r["slope_per_unit"], r["halves"], r["placebo"], r.get("peak_months") or {}
            L.append(f"| {r['label']} | {r['events']} ({r['from'][:4]}-{r['to'][:4]}){' insufficient' if r['status'] == 'insufficient' else ''} | "
                     f"{_f(s['hit_rate'], pct=True)} of {s['strong_n']} ({_f(s['ci95'][0], pct=True)}-{_f(s['ci95'][1], pct=True)}) | "
                     f"{_f(z.get('slope'))}% ({_f(z.get('t'), 1)}) | {_f(u.get('slope'), 3)}% ({_f(u.get('t'), 1)}) | "
                     f"{_f((pk.get('slope_per_sd') or {}).get('slope'))} ({pk.get('events')}) | {_f(h['first']['slope_per_sd'])} / {_f(h['second']['slope_per_sd'])} | "
                     f"{_f(pl['day_before']['slope_per_sd'])} ({_f(pl['day_before']['t'], 1)}) / {_f(pl['day_after']['slope_per_sd'])} ({_f(pl['day_after']['t'], 1)}) |")
    starts = sorted({r["from"][:4] for r in rows}) if rows else []
    L += ["", f"Condition data from 2015 (NASS Quick Stats): the norm needs five prior seasons, so events start in {', '.join(starts) or '-'}. "
          "Report-day categories are disjoint: WASDE excludes January (its day is shared with Grain Stocks and the annual Crop Production), "
          "and Grain Stocks alone is September only (March and June share the day with Prospective Plantings and Acreage). "
          "Sugar (#11) is a world market: US crop reports are shown for context only.", BLOCK_END]
    block = "\n".join(L)
    if BLOCK_START in text:
        text = re.sub(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END), lambda m: block, text, flags=re.S)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    return f


def summary(out: dict) -> dict:
    return {"reports": {k: {m: {"events": r.get("events"), "ratio": r.get("ratio"), "local": r.get("local"), "lift": r.get("lift"), "placebo": r.get("placebo"),
                                "eras": {e: v.get("ratio") for e, v in (r.get("eras") or {}).items()},
                                "revision": {x: (r.get("revision") or {}).get(x) for x in ("n", "slope_per_sd", "t", "hit_rate")} if r.get("revision") else None}
                            for m, r in rep["markets"].items()} for k, rep in out["reports"].items()},
            "crop_progress": {k: {"events": r.get("events"), "slope_per_sd": (r.get("slope_per_sd") or {}).get("slope"), "t": (r.get("slope_per_sd") or {}).get("t"),
                                  "hit": (r.get("sign") or {}).get("hit_rate"), "peak": ((r.get("peak_months") or {}).get("slope_per_sd") or {}).get("slope"),
                                  "placebo": {k2: (v or {}).get("t") for k2, v in (r.get("placebo") or {}).items()}, "latest_z": (r.get("latest") or {}).get("z")}
                              for k, r in out["crop_progress"].items()}}


def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack ags")
    p.add_argument("--date", help="as-of date (point in time), default today BRT")
    p.add_argument("--write", action="store_true", help="write knowledge/ags/*/estimates/*.json and the events.md code tables")
    a = p.parse_args(argv)
    out = run(date.fromisoformat(a.date) if a.date else None, write=a.write)
    s = summary(out)
    runlog.log(runlog.new_run_id(), "ags:base-rates", "ok", asof=out["asof"], write=a.write, crop_progress=s["crop_progress"])
    print(json.dumps(s, indent=1, default=str))
    return 0
