"""Balance keeper (agent 9): oil and grain balances against trailing norms, and each report against a code-built
expectation. Descriptive only: no price forecast, no verdict, never "vs consensus".

Why this shape (docs/research/balance.md):
  - Theory of storage: low stocks go with backwardation, a higher basis and higher volatility, non-linearly
    (Working; Gorton, Hayashi & Rouwenhorst; Symeonidis et al.). So levels are shown against a norm, with their
    position in the range and flags beyond it, not only a z-score.
  - The norm is the EIA convention, the same week of the prior five years (current year excluded): trailing only.
    GHR's two-sided HP "normal" would look ahead.
  - Inventories mostly carry speculative/precautionary demand and supply smoothing (Kilian & Murphy), so a build
    is not "bearish" by law: any reading is labelled inference and goes to the critic as a question.
  - No free consensus exists for EIA or USDA; naive surprises are noisier and bias price responses toward zero
    (Halova et al.). Surprises are "vs the 5-year same-week change" or "vs the previous WASDE", shown beside
    USDA's own average miss for that month's projection (from the WASDE file), and never turned into a sensitivity.
  - Stocks-to-use is the grain summary; price is convex in it and the curve shifts by regime (Good & Irwin;
    Janzen): shown with its percentile since 2007/08 and the new-crop line beside old-crop.
  - Every number is dated when it became public (available_lag_days): a backdated pack sees only what existed.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yaml

from . import runlog, store

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("eia", "eia_bal", "wasde", "usda_psd", "nass")
EIA_URL = "https://www.eia.gov/petroleum/supply/weekly/"
WASDE_URL = "https://www.usda.gov/oce/commodity/wasde"
PSD_URL = "https://apps.fas.usda.gov/psdonline/app/index.html#/app/advQuery"
NASS_URL = "https://quickstats.nass.usda.gov/"
NASS_NOTICE = "This product uses the NASS API but is not endorsed or certified by NASS."


def cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "balance.yaml").read_text(encoding="utf-8"))


def _f(x, nd=2):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) or math.isinf(x) else round(x, nd)


# ------------------------------------------------------------------ data, as of a date
def load(asof: date, con=None) -> pd.DataFrame:
    """Every balance observation that was public on `asof` (stored date + available_lag_days <= asof)."""
    con = con or store.connect()
    q = f"SELECT source, series_id, name, date, value, unit, source_url FROM obs WHERE source IN ({', '.join('?' * len(SOURCES))})"
    try:
        df = con.execute(q, list(SOURCES)).df()
    except Exception:  # noqa: BLE001
        return pd.DataFrame(columns=["source", "series_id", "name", "date", "value", "unit", "source_url", "avail"])
    if df.empty:
        return df.assign(avail=pd.Series(dtype="object"))
    df["date"] = pd.to_datetime(df["date"]).dt.date
    c = cfg()
    lag = c["available_lag_days"]
    late = {date.fromisoformat(str(x)) for x in c.get("eia_late_weeks") or []}
    df["avail"] = [d + timedelta(days=int(lag.get(s, 1)) + (1 if s in ("eia", "eia_bal") and d in late else 0))
                   for d, s in zip(df["date"], df["source"])]
    return df[df["avail"] <= asof].sort_values(["series_id", "date"]).reset_index(drop=True)


def _s(df: pd.DataFrame, sid: str) -> pd.DataFrame:
    return df[df.series_id == sid].dropna(subset=["value"]).sort_values("date")


def _same_week(s: pd.DataFrame, d: date, years: int) -> list[tuple[int, float]]:
    """(year, value) for the same ISO week in each of the prior `years` years (week 53 falls back to 52)."""
    iso = pd.to_datetime(s["date"]).dt.isocalendar()
    wk0 = d.isocalendar()[1]
    out = []
    for k in range(1, years + 1):
        y = d.isocalendar()[0] - k
        hit = s[(iso["year"].values == y) & (iso["week"].values == wk0)]
        if hit.empty and wk0 == 53:
            hit = s[(iso["year"].values == y) & (iso["week"].values == 52)]
        if not hit.empty:
            out.append((y, float(hit["value"].iloc[-1])))
    return out


# ------------------------------------------------------------------ oil
def stock_row(s: pd.DataFrame, c: dict, years: int, min_years: int) -> dict | None:
    if len(s) < 2:
        return None
    last, prev = s.iloc[-1], s.iloc[-2]
    d = last["date"]
    norm = _same_week(s, d, years)
    vals = [v for _, v in norm]
    row = {"id": c["id"], "label": c["label"], "name": f"{c['label']} stocks", "markets": c.get("markets", []),
           "week_ending": str(d), "level": _f(last["value"], 1), "unit": last["unit"], "change": _f(last["value"] - prev["value"], 1),
           "source_url": last["source_url"], "norm_years": [y for y, _ in norm]}
    if len(vals) >= min_years:
        avg, lo, hi = sum(vals) / len(vals), min(vals), max(vals)
        sd = pd.Series(vals).std(ddof=1)
        row.update(avg5=_f(avg, 1), min5=_f(lo, 1), max5=_f(hi, 1),
                   vs_avg=_f(last["value"] - avg, 1), vs_avg_pct=_f(100 * (last["value"] / avg - 1), 1) if avg else None,
                   z_sd=_f((last["value"] - avg) / sd, 1) if sd and sd > 0 else None,
                   range_pos_pct=_f(100 * (last["value"] - lo) / (hi - lo), 0) if hi > lo else None,
                   beyond="below" if last["value"] < lo else "above" if last["value"] > hi else None)
        # weekly change vs the 5-year same-week change: the naive expectation (not a consensus). Same definition as
        # the monitor's EIA table (weekly changes in the same and adjacent ISO weeks of the prior five calendar years),
        # so one fact pack never shows two different "5-year average changes" for one series
        x = s.assign(chg=s["value"].diff(), wk=pd.to_datetime(s["date"]).dt.isocalendar().week.astype(int),
                     yr=pd.to_datetime(s["date"]).dt.year)
        ly, lw = pd.Timestamp(d).year, d.isocalendar()[1]
        hist = x[(x.yr >= ly - years) & (x.yr < ly)]
        near = hist[(hist.wk - lw).abs().isin([0, 1]) | ((hist.wk - lw).abs() >= 51)]["chg"].dropna()
        if len(near) >= min_years:
            row["avg5_change"] = _f(near.mean(), 1)
            row["change_vs_avg5"] = _f(row["change"] - near.mean(), 1)
    return row


def flow_row(s: pd.DataFrame, c: dict, years: int, min_years: int) -> dict | None:
    """4-week average vs the same 4 weeks of the prior years (EIA practice for implied demand)."""
    if len(s) < 4:
        return None
    last4 = s.iloc[-4:]
    d = last4["date"].iloc[-1]
    cur = float(last4["value"].mean())
    past = []
    for k in range(1, years + 1):
        target = pd.Timestamp(d) - pd.DateOffset(years=k)
        win = s[(pd.to_datetime(s["date"]) > target - pd.Timedelta(days=28)) & (pd.to_datetime(s["date"]) <= target + pd.Timedelta(days=3))]
        if len(win) >= 3:
            past.append(float(win["value"].iloc[-4:].mean()))
    row = {"id": c["id"], "label": c["label"], "name": c["label"], "markets": c.get("markets", []), "week_ending": str(d),
           "avg4": _f(cur, 0), "unit": last4["unit"].iloc[-1], "source_url": last4["source_url"].iloc[-1]}
    if len(past) >= min_years:
        a = sum(past) / len(past)
        row.update(avg4_5y=_f(a, 0), vs_5y_pct=_f(100 * (cur / a - 1), 1) if a else None)
    return row


def adjustment_row(s: pd.DataFrame, c: dict) -> dict | None:
    if len(s) < 8:
        return None
    a4 = s["value"].rolling(4).mean()
    d = s["date"].iloc[-1]
    post = s[pd.to_datetime(s["date"]) >= pd.Timestamp(c["break_date"])]
    band = post["value"].rolling(4).mean().dropna().iloc[-int(c["band_weeks"]):]
    mu, sd = (band.mean(), band.std(ddof=1)) if len(band) >= 12 else (None, None)
    z = (a4.iloc[-1] - mu) / sd if sd else None
    return {"id": c["id"], "label": "Crude adjustment (unaccounted), 4-week avg", "name": "US crude adjustment",
            "week_ending": str(d),
            "avg4": _f(a4.iloc[-1], 0), "unit": s["unit"].iloc[-1], "band_z": _f(z, 1),
            "band_since": c["break_date"],
            "flag": bool(z is not None and abs(z) >= c["flag_z"]), "source_url": s["source_url"].iloc[-1]}


def oil(df: pd.DataFrame, c: dict) -> dict:
    o, yrs, mn = c["oil"], c["norm_years"], c["min_norm_years"]
    stocks = [r for r in (stock_row(_s(df, x["id"]), x, yrs, mn) for x in o["stocks"]) if r]
    days = {}
    for k, sid in o["days_of_supply"].items():
        s = _s(df, sid)
        if len(s):
            norm = [v for _, v in _same_week(s, s["date"].iloc[-1], yrs)]
            days[k] = {"days": _f(s["value"].iloc[-1], 1), "week_ending": str(s["date"].iloc[-1]),
                       "avg5": _f(sum(norm) / len(norm), 1) if len(norm) >= mn else None, "source_url": s["source_url"].iloc[-1]}
    for r in stocks:
        k = o["stock_days"].get(r["id"])
        if k and k in days and days[k]["week_ending"] == r["week_ending"]:
            r["days_supply"], r["days_supply_avg5"] = days[k]["days"], days[k]["avg5"]
    flows = [r for r in (flow_row(_s(df, x["id"]), x, yrs, mn) for x in o["flows"]) if r]
    adj = adjustment_row(_s(df, o["adjustment"]["id"]), o["adjustment"]) if (o.get("adjustment") or {}).get("id") else None
    return {"stocks": stocks, "days_of_supply": days, "flows": flows, "adjustment": adj}


# ------------------------------------------------------------------ grains
def _my_key(my: str) -> int:
    m = re.match(r"(\d{4})", str(my))
    return int(m.group(1)) if m else -1


def _wasde_at(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """Rows of one commodity/region/attribute across market years: columns my, date, value."""
    x = df[df.series_id.str.startswith(prefix)].copy()
    if x.empty:
        return x
    x["my"] = x.series_id.str.rsplit(":", n=1).str[-1]
    return x


def _first(df: pd.DataFrame, prefixes: list[str]) -> pd.DataFrame:
    for p in prefixes:
        x = _wasde_at(df, p)
        if not x.empty:
            return x
    return pd.DataFrame()


def _sur_history(df: pd.DataFrame, key: str, country: str, use_attrs: list[str], from_my: int,
                 exclude_my: set[int]) -> list[float]:
    """Stocks-to-use by market year from PSD (latest vintage public on the as-of date), regime years only."""
    es = _wasde_at(df, f"psd:{key}:{country}:ending-stocks:")
    if es.empty:
        return []
    out = []
    for my, g in es.groupby("my"):
        y = _my_key(my)
        if y < from_my or y in exclude_my:
            continue
        e = float(g.sort_values("date")["value"].iloc[-1])
        u = _psd_use(df, key, country, use_attrs, my)
        if u:
            out.append(100 * e / u)
    return out


def _psd(df: pd.DataFrame, key: str, country: str, attr: str, my: str) -> float | None:
    x = _s(df, f"psd:{key}:{country}:{attr}:{my}")
    return float(x["value"].iloc[-1]) if len(x) else None


def _psd_use(df: pd.DataFrame, key: str, country: str, use_attrs: list[str], my: str) -> float | None:
    """Use for stocks-to-use: the first configured attribute PSD has; a single country also counts its exports
    (world exports are other countries' imports, so the world ratio uses consumption alone)."""
    for a in use_attrs:
        v = _psd(df, key, country, a, my)
        if v:
            if country != "world" and a == "domestic-consumption":
                v += _psd(df, key, country, "exports", my) or 0.0
            return v
    return None


def _world(df: pd.DataFrame, key: str, use_attrs: list[str]) -> dict | None:
    """World stocks-to-use for the latest PSD market year, and world excluding China (China's large stocks are
    not available to the market: Bobenrieth, Wright & Zeng)."""
    es = _wasde_at(df, f"psd:{key}:world:ending-stocks:")
    if es.empty:
        return None
    my = max(es["my"], key=_my_key)
    e = _psd(df, key, "world", "ending-stocks", my)
    u = next((v for v in (_psd(df, key, "world", a, my) for a in use_attrs) if v), None)
    out = {"my": my, "ending_stocks": _f(e, 2), "sur_pct": _f(100 * e / u, 1) if e is not None and u else None,
           "date": str(_s(df, f"psd:{key}:world:ending-stocks:{my}")["date"].iloc[-1]), "source_url": PSD_URL, "from": "PSD"}
    ech = _psd(df, key, "ch", "ending-stocks", my)
    uch = next((v for v in (_psd(df, key, "ch", a, my) for a in use_attrs) if v), None)
    if e is not None and u and ech is not None and uch and u > uch:
        out["ex_china_sur_pct"] = _f(100 * (e - ech) / (u - uch), 1)
    return out


def grain_row(df: pd.DataFrame, key: str, m: dict, c: dict) -> dict | None:
    """US balance from the latest WASDE public on the as-of date, its revision vs the previous report, USDA's
    average miss for that month, the stocks-to-use percentile since regime_from_my, and the world line (PSD)."""
    es = _wasde_at(df, f"wasde:{key}:united-states:ending-stocks:")
    if es.empty:
        return None
    rel_date = es["date"].max()
    at = es[es["date"] == rel_date]
    mys = sorted(at["my"].unique(), key=_my_key)
    cur = mys[-1]
    row = {"market": m["label"], "key": key, "price_ref": m["price_ref"], "report_date": str(rel_date), "my": cur,
           "unit": at["unit"].iloc[0], "source_url": at["source_url"].iloc[0]}

    def val(attr_prefixes, my, d):
        for a in attr_prefixes:
            s = _s(df, f"wasde:{key}:united-states:{a}:{my}")
            s = s[s["date"] == d]
            if len(s):
                return float(s["value"].iloc[-1])
        return None

    e = val(["ending-stocks"], cur, rel_date)
    u = val(m["us_use"], cur, rel_date)
    row.update(ending_stocks=_f(e, 1), use=_f(u, 1), sur_pct=_f(100 * e / u, 1) if e is not None and u else None)
    if len(mys) > 1:                                          # old crop (estimate) beside new crop (projection)
        old = mys[-2]
        eo, uo = val(["ending-stocks"], old, rel_date), val(m["us_use"], old, rel_date)
        row.update(old_my=old, old_sur_pct=_f(100 * eo / uo, 1) if eo is not None and uo else None)
    prev = es[(es["my"] == cur) & (es["date"] < rel_date)]
    if len(prev):
        pd_ = prev["date"].max()
        ep = float(prev[prev["date"] == pd_]["value"].iloc[-1])
        row.update(prev_report=str(pd_), es_change=_f(e - ep, 1), es_change_pct=_f(100 * (e / ep - 1), 1) if ep else None)
        up = val(m["us_use"], cur, pd_)
        if up and row.get("sur_pct") is not None:
            row["sur_change_pp"] = _f(row["sur_pct"] - 100 * ep / up, 1)
    else:
        row["first_projection"] = True
    # USDA's reliability table for this month's projection; it may be in metric tons while the US balance is in
    # bushels (soybeans, wheat): converted with the fixed factors in config, or left out when no factor applies
    conv = (c["grains"].get("mt_to_balance_unit") or {}).get(key)
    for stat, k in (("average", "usda_avg_miss"), ("root-mean-square-error", "usda_rmse_pct")):
        r = _s(df, f"wasde_rel:{key}:united-states:ending-stocks:{stat}")
        r = r[r["date"] == rel_date]
        if not len(r):
            continue
        v, u = float(r["value"].iloc[-1]), str(r["unit"].iloc[-1]).lower()
        if stat == "average" and u != str(row["unit"]).lower():
            if "metric ton" in u and conv:
                v *= conv
            else:
                continue
        row[k] = _f(v, 2)
    hist = _sur_history(df, key, "us", c["grains"]["world_use"], c["grains"]["regime_from_my"], {_my_key(cur)})
    if len(hist) >= 5 and row.get("sur_pct") is not None:
        row["sur_pctile"] = _f(100 * sum(h <= row["sur_pct"] for h in hist) / len(hist), 0)
        row["sur_hist_n"] = len(hist)
    w = _world_wasde(df, key, c["grains"]["world_use"], rel_date, cur) or _world(df, key, c["grains"]["world_use"])
    if w:
        row["world"] = w
    return row


def _world_wasde(df: pd.DataFrame, key: str, use_attrs: list[str], rel_date, my: str) -> dict | None:
    """World and world-less-China stocks-to-use from the same WASDE report (first published)."""
    def ratio(region):
        e = _s(df, f"wasde:{key}:{region}:ending-stocks:{my}")
        e = e[e["date"] == rel_date]
        if e.empty:
            return None, None
        for a in use_attrs:
            u = _s(df, f"wasde:{key}:{region}:{a}:{my}")
            u = u[u["date"] == rel_date]
            if len(u) and float(u["value"].iloc[-1]):
                return float(e["value"].iloc[-1]), 100 * float(e["value"].iloc[-1]) / float(u["value"].iloc[-1])
        return float(e["value"].iloc[-1]), None
    e, sur = ratio("world")
    if e is None:
        return None
    _, ex = ratio("world-less-china")
    src = df[df.series_id == f"wasde:{key}:world:ending-stocks:{my}"]["source_url"]
    return {"my": my, "ending_stocks": _f(e, 2), "sur_pct": _f(sur, 1), "ex_china_sur_pct": _f(ex, 1),
            "date": str(rel_date), "source_url": src.iloc[-1] if len(src) else WASDE_URL, "from": "WASDE"}


def grains(df: pd.DataFrame, c: dict) -> list[dict]:
    out = []
    for key, m in c["grains"]["markets"].items():
        r = grain_row(df, key, m, c)
        if r is None:                    # no WASDE yet (sugar world-only from PSD is still useful)
            w = _world(df, key, c["grains"]["world_use"])
            if w:
                r = {"market": m["label"], "key": key, "price_ref": m["price_ref"], "world": w}
        if r:
            out.append(r)
    return out


# ------------------------------------------------------------------ crops (NASS)
def condition(df: pd.DataFrame, c: dict, asof: date | None = None) -> list[dict]:
    """Good + excellent per crop. A crop whose last release is more than `season_over_days` old is shown as season
    over (live probe 16 Oct: winter wheat's last week was 5 Jul and read as a "key month")."""
    out = []
    for key, cr in c["crop_condition"]["crops"].items():
        g, ex = _s(df, f"nass:{cr['good']}"), _s(df, f"nass:{cr['excellent']}")
        if g.empty or ex.empty:
            continue
        both = g[["date", "value", "name"]].merge(ex[["date", "value"]], on="date", suffixes=("_g", "_e"))
        if both.empty:
            continue
        both["ge"] = both["value_g"] + both["value_e"]
        last = both.iloc[-1]
        row = {"crop": cr["label"], "name": f"{cr['label']} condition", "price_ref": cr["price_ref"], "released": str(last["date"]),
               "week": str(last["name"]).rsplit("(", 1)[-1].rstrip(")"), "good_excellent_pct": _f(last["ge"], 0),
               "source_url": NASS_URL}
        if len(both) > 1 and (last["date"] - both.iloc[-2]["date"]).days <= 8:
            row["weekly_change_pp"] = _f(last["ge"] - both.iloc[-2]["ge"], 0)
        s = both.rename(columns={"ge": "value"})[["date", "value"]]
        norm = [v for _, v in _same_week(s, last["date"], c["norm_years"])]
        if len(norm) >= c["min_norm_years"]:
            row["avg5"] = _f(sum(norm) / len(norm), 0)
            row["vs_avg5_pp"] = _f(last["ge"] - sum(norm) / len(norm), 0)
        stale = asof is not None and (asof - last["date"]).days > int(c["crop_condition"].get("season_over_days", 14))
        row["season_over"] = bool(stale)
        row["key_month"] = (not stale) and pd.Timestamp(last["date"]).month in c["crop_condition"]["key_months"]
        out.append(row)
    return out


def stocks_quarterly(df: pd.DataFrame, c: dict) -> list[dict]:
    out = []
    for key, g in c["grain_stocks"].items():
        s = _s(df, f"nass:{g['series']}")
        if s.empty:
            continue
        last = s.iloc[-1]
        ref = str(last["name"]).rsplit("(", 1)[-1].rstrip(")")
        q = ref.split("-", 1)[-1] if "-" in ref else ref           # e.g. 2026-first-of-sep -> first-of-sep
        same = s[s["name"].str.contains(q, regex=False) & (s["date"] < last["date"])]
        row = {"market": key.capitalize(), "name": f"{key} stocks", "price_ref": g["price_ref"], "released": str(last["date"]), "reference": ref,
               "level_mbu": _f(last["value"] / 1e6, 1), "source_url": NASS_URL}
        if len(same):
            ya = float(same["value"].iloc[-1])
            row["vs_year_ago_pct"] = _f(100 * (last["value"] / ya - 1), 1) if ya else None
            prior = same["value"].iloc[-c["norm_years"]:]
            if len(prior) >= c["min_norm_years"]:
                row["vs_avg5_pct"] = _f(100 * (last["value"] / prior.mean() - 1), 1)
        out.append(row)
    return out


# ------------------------------------------------------------------ section, alerts, critic facts
def build(asof: date, con=None) -> tuple[dict, list[dict]]:
    """The fact-pack section and its alerts, using only numbers public on `asof`."""
    c = cfg()
    df = load(asof, con)
    sec = {"asof": str(asof), "health": health(df, asof, c), "oil": oil(df, c), "grains": grains(df, c),
           "condition": condition(df, c, asof),
           "grain_stocks": stocks_quarterly(df, c),
           "labels": {"surprise": "vs the 5-year same-week change or the previous report (code), not a consensus",
                      "nass": NASS_NOTICE}}
    return sec, alerts(sec, asof, c)


def health(df: pd.DataFrame, asof: date, c: dict) -> list[dict]:
    """Latest public date per new source and whether it is stale (the monitor's staleness check reads only
    config/sources.yaml: review A12, finding 9). NASS is seasonal and never flagged."""
    out = []
    for src, days in (c.get("stale_days") or {}).items():
        x = df[df["source"] == src]
        last = max(x["avail"]) if len(x) else None
        out.append({"source": src, "last_public": str(last) if last else None,
                    "stale": last is None or (asof - last).days > int(days)})
    return out


def _fresh(d: str, asof: date, days: int) -> bool:
    try:
        return 0 <= (asof - date.fromisoformat(d)).days <= days
    except (TypeError, ValueError):
        return False


def alerts(sec: dict, asof: date, c: dict) -> list[dict]:
    a, out = c["alerts"], []
    lag = c["available_lag_days"]["eia"]
    for r in sec["oil"]["stocks"]:
        cf = next((x for x in c["oil"]["stocks"] if x["id"] == r["id"]), {})
        if not cf.get("alert") or not r.get("beyond") or r.get("z_sd") is None or abs(r["z_sd"]) < a["range_min_z"]:
            continue
        pub = (date.fromisoformat(r["week_ending"]) + timedelta(days=lag)).isoformat()
        if not _fresh(pub, asof, a["fresh_days"]):
            continue
        yrs = r["norm_years"]
        bound = r["min5"] if r["beyond"] == "below" else r["max5"]
        out.append({"kind": "balance_range", "severity": abs(r["z_sd"]), "id": r["id"],
                    "text": (f"{r['label']} stocks {r['level']:,.0f} {r['unit']} in week to {r['week_ending']}: {r['beyond']} the "
                             f"{min(yrs)}-{max(yrs)} same-week range ({'low' if r['beyond'] == 'below' else 'high'} {bound:,.0f}; "
                             f"{r['z_sd']:+.1f} sd vs the 5-year average)"),
                    "source_url": r["source_url"]})
    for g in sec["grains"]:
        if g.get("es_change") is None or not g.get("usda_avg_miss") or not _fresh(g["report_date"], asof, a["fresh_days"]):
            continue
        ratio = abs(g["es_change"]) / g["usda_avg_miss"]
        if ratio >= a["wasde_min_vs_miss"]:
            out.append({"kind": "wasde_revision", "severity": min(4.0, 1.5 * ratio), "id": g["price_ref"],
                        "text": (f"WASDE {g['report_date']}: US {g['market'].lower()} {g['my']} ending stocks {g['ending_stocks']:,.0f} "
                                 f"{g['unit']}, {g['es_change']:+,.0f} vs the {g['prev_report']} report; USDA's average miss "
                                 f"for this month's projection is {g['usda_avg_miss']:,.0f} (revision vs the previous report, not a consensus)"),
                        "source_url": g["source_url"]})
    for r in sec["condition"]:
        ch = r.get("weekly_change_pp")
        if ch is None or not r.get("key_month") or abs(ch) < a["condition_change_pp"] or not _fresh(r["released"], asof, a["fresh_days"]):
            continue
        out.append({"kind": "crop_condition", "severity": abs(ch) / 2.5, "id": r["price_ref"],
                    "text": (f"{r['crop']} rated good/excellent {r['good_excellent_pct']:.0f}% (week ending {r['week']}), "
                             f"{ch:+.0f} pts on the week" + (f", {r['vs_avg5_pp']:+.0f} vs the 5-year same-week average"
                                                            if r.get("vs_avg5_pp") is not None else "")),
                    "source_url": r["source_url"]})
    return out


def critic_facts(sec: dict | None, price_ref: str | None, direction: str | None) -> tuple[dict, dict | None]:
    """Card facts for one market and, when the balance leans against the idea, a counter basis (inference)."""
    if not sec or not price_ref:
        return {}, None
    c = cfg()["critic"]
    F: dict[str, tuple] = {}
    d = {"long": 1, "short": -1}.get(direction or "")
    lean = None
    st = next((r for r in sec.get("oil", {}).get("stocks", []) if price_ref in (r.get("markets") or [])), None)
    if st:
        F["bal.stock"] = (st["label"], "inventory series", st["source_url"])
        F["bal.week"] = (st["week_ending"], "EIA week ending", st["source_url"])
        F["bal.stock_vs_5y_pct"] = (st.get("vs_avg_pct"), "stocks vs the 5-year same-week average, %", st["source_url"])
        F["bal.stock_z"] = (st.get("z_sd"), "stocks vs the 5-year same-week average, sd", st["source_url"])
        F["bal.stock_range_pos"] = (st.get("range_pos_pct"), "position in the prior-5-year same-week range, % (0 = the low, "
                                    "100 = the high; below 0 or above 100 = outside the range)",
                                    st["source_url"])
        if st.get("days_supply") is not None:
            F["bal.days_supply"] = (st["days_supply"], "days of supply (EIA)", st["source_url"])
        z = st.get("z_sd")
        if d and z is not None and ((d > 0 and z >= c["loose_z"]) or (d < 0 and z <= c["tight_z"])):
            lean = {"basis": "balance", "severity": c["severity"], "facts": ["bal.stock", "bal.stock_vs_5y_pct", "bal.stock_z"]}
    gr = next((r for r in sec.get("grains", []) if r.get("price_ref") == price_ref), None)
    if gr:
        us_ok = (cfg()["grains"]["markets"].get(gr.get("key", ""), {}) or {}).get("us_for_critic", True)
        if us_ok:   # US sugar (#16, protected) is not the world raw sugar market (#11): review A12, finding 8
            F["bal.report_date"] = (gr.get("report_date"), "latest WASDE", gr.get("source_url") or WASDE_URL)
            F["bal.sur_pct"] = (gr.get("sur_pct"), f"US stocks-to-use {gr.get('my', '')}, %", gr.get("source_url") or WASDE_URL)
            F["bal.sur_pctile"] = (gr.get("sur_pctile"), "stocks-to-use percentile since 2007/08 (PSD)", PSD_URL)
            F["bal.es_change"] = (gr.get("es_change"), "ending stocks revision vs the previous WASDE", gr.get("source_url") or WASDE_URL)
            F["bal.usda_avg_miss"] = (gr.get("usda_avg_miss"), "USDA's average miss for this month's projection",
                                      gr.get("source_url") or WASDE_URL)
        if gr.get("world"):
            w = gr["world"]
            wsrc = w.get("from", "PSD")
            F["bal.world_sur_pct"] = (w.get("sur_pct"), f"world stocks-to-use {w['my']}, % ({wsrc})", w.get("source_url") or PSD_URL)
            F["bal.world_ex_china_sur_pct"] = (w.get("ex_china_sur_pct"), f"world ex-China stocks-to-use, % ({wsrc})",
                                               w.get("source_url") or PSD_URL)
        p = gr.get("sur_pctile") if us_ok else None
        if lean is None and d and p is not None and ((d > 0 and p >= c["loose_pctile"]) or (d < 0 and p <= c["tight_pctile"])):
            lean = {"basis": "balance", "severity": c["severity"], "facts": ["bal.sur_pct", "bal.sur_pctile"]}
    F = {k: v for k, v in F.items() if v[0] is not None}
    if lean:
        lean["facts"] = [f for f in lean["facts"] if f in F]
        if not lean["facts"]:
            lean = None
    return F, lean


# ------------------------------------------------------------------ fact-pack markdown
def _n(x, nd=1, sign=False):
    if x is None:
        return "-"
    return f"{x:+,.{nd}f}" if sign else f"{x:,.{nd}f}"


def _p(x, nd=1, sign=False) -> str:
    return "-" if x is None else _n(x, nd, sign) + "%"


def render(sec: dict) -> list[str]:
    if not sec or sec.get("error"):
        return ["## Balances (agent 9)", "", f"Not available: {sec.get('error') if sec else 'no data'}", ""] if sec else []
    o = sec.get("oil") or {}
    L = ["## Balances (descriptive; vs trailing norms and code expectations, never a consensus)", "",
         "Norm = the same week of the prior five years (EIA convention, current year excluded). "
         "Reading a balance as tight or loose is inference; inventories mostly reflect precautionary demand and supply "
         "smoothing, not flow demand.", ""]
    if o.get("stocks"):
        L += ["| Stocks | Week ending | Level | vs 5y avg | 5y same-week range | Range position | z | Change | vs 5y avg change | Days of supply (5y avg) | Source |",
              "|---|---|---:|---:|---|---:|---:|---:|---:|---|---|"]
        for r in o["stocks"]:
            rng = f"{_n(r.get('min5'), 0)}–{_n(r.get('max5'), 0)}" + (f" ({r['beyond']})" if r.get("beyond") else "") if r.get("min5") is not None else "-"
            dos = f"{_n(r.get('days_supply'))} ({_n(r.get('days_supply_avg5'))})" if r.get("days_supply") is not None else "-"
            L.append(f"| {r['label']} ({r['unit']}) | {r['week_ending']} | {_n(r['level'], 0)} | {_p(r.get('vs_avg_pct'), 1, True)} | "
                     f"{rng} | {_p(r.get('range_pos_pct'), 0)} | {_n(r.get('z_sd'), 1, True)} | {_n(r.get('change'), 0, True)} | "
                     f"{_n(r.get('change_vs_avg5'), 0, True)} | {dos} | [EIA]({r['source_url']}) |")
        L += [""]
    if o.get("flows"):
        L += ["| Flow (4-week average) | Week ending | Level | Same 4 weeks, 5y avg | vs 5y | Source |", "|---|---|---:|---:|---:|---|"]
        for r in o["flows"]:
            L.append(f"| {r['label']} ({r['unit']}) | {r['week_ending']} | {_n(r['avg4'], 0)} | {_n(r.get('avg4_5y'), 0)} | "
                     f"{_p(r.get('vs_5y_pct'), 1, True)} | [EIA]({r['source_url']}) |")
        L += ["", "Implied demand = product supplied (disappearance from primary supply), not consumption; weekly flows "
              "are revised by the monthly data.", ""]
    adj = o.get("adjustment")
    if adj:
        L += [f"Crude adjustment (unaccounted crude, the balancing line), 4-week average: {_n(adj['avg4'], 0)} {adj['unit']} "
              f"in week to {adj['week_ending']}, {_n(adj.get('band_z'), 1, True)} sd vs its band since {adj['band_since']}"
              + (" — large: read this week's stock change with care." if adj.get("flag") else ".") + f" ([EIA]({adj['source_url']}))", ""]
    gs = sec.get("grains") or []
    if gs:
        L += ["| Grains and sugar (US, WASDE as first published) | Report | Market year | Ending stocks | Stocks-to-use | "
              "Revision vs previous report | USDA avg miss, this month | Stocks-to-use pctile since 2007/08 | Old crop stocks-to-use | "
              "World / ex-China stocks-to-use | Source |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|---|---|"]
        for g in gs:
            w = g.get("world") or {}
            wtxt = (f"{_p(w.get('sur_pct'))} / {_p(w.get('ex_china_sur_pct'))} ({w.get('my')}, {w.get('from', 'WASDE')})"
                    if w else "-")
            if g.get("report_date") is None:
                L.append(f"| {g['market']} | - | - | - | - | - | - | - | - | {wtxt} | [PSD]({PSD_URL}) |")
                continue
            rev = ("first projection" if g.get("first_projection") else f"{_n(g.get('es_change'), 0, True)} ({g.get('prev_report')})")
            L.append(f"| {g['market']} ({g['unit']}) | {g['report_date']} | {g['my']} | {_n(g.get('ending_stocks'), 0)} | "
                     f"{_p(g.get('sur_pct'))} | {rev} | {_n(g.get('usda_avg_miss'), 0)} | {_n(g.get('sur_pctile'), 0)} | "
                     f"{_p(g.get('old_sur_pct'))} ({g.get('old_my', '-')}) | {wtxt} | [WASDE]({g['source_url']}) |")
        L += ["", "Revision = this report vs the previous one for the same market year (code comparison). USDA's average "
              "miss = the mean gap between this month's projection and the final, from USDA's reliability table in the "
              "same file. Stocks-to-use is a consistency check, not a price model: the curve shifts by regime.", ""]
    cd = sec.get("condition") or []
    if cd:
        L += ["| Crop condition (NASS) | Week ending | Good/excellent | Week change | vs 5y same week | Note |", "|---|---|---:|---:|---:|---|"]
        for r in cd:
            pts = lambda x: "-" if x is None else f"{_n(x, 0, True)} pts"
            note = ("season over" if r.get("season_over") else "key month" if r.get("key_month")
                    else "outside Jul-Aug: low weight")
            L.append(f"| {r['crop']} | {r['week']} | {_n(r['good_excellent_pct'], 0)}% | {pts(r.get('weekly_change_pp'))} | "
                     f"{pts(r.get('vs_avg5_pp'))} | {note} |")
        L += [""]
    st = sec.get("grain_stocks") or []
    if st:
        L += ["| Grain stocks (NASS quarterly) | Reference | Released | Level (million bu) | vs year ago | vs 5y avg |", "|---|---|---|---:|---:|---:|"]
        for r in st:
            L.append(f"| {r['market']} | {r['reference']} | {r['released']} | {_n(r['level_mbu'])} | {_p(r.get('vs_year_ago_pct'), 1, True)} | "
                     f"{_p(r.get('vs_avg5_pct'), 1, True)} |")
        L += [""]
    if cd or st:
        L += [f"NASS: {NASS_NOTICE} Source: [NASS Quick Stats]({NASS_URL}).", ""]
    stale = [h for h in sec.get("health") or [] if h.get("stale")]
    if stale:
        L += ["Data health: " + "; ".join(f"{h['source']} last public {h['last_public'] or 'never'}" for h in stale)
              + " (stale or missing: check the fetch log).", ""]
    L[2] = L[2] + " Range position: 0 = the 5-year same-week low, 100 = the high; below 0 or above 100 = outside the range."
    if not (o.get("stocks") or gs or cd or st):
        L += ["No balance data yet (first fetch pending).", ""]
    return L


# ------------------------------------------------------------------ CLI
def probe_report(con=None) -> dict:
    """What the new sources returned (first live run): series counts and names per source, for checking the
    WASDE/PSD/NASS field mapping against the real files."""
    con = con or store.connect()
    out = {}
    for s in SOURCES:
        try:
            df = con.execute("SELECT series_id, count(*) n, min(date) d0, max(date) d1 FROM obs WHERE source = ? GROUP BY 1 ORDER BY 1",
                             [s]).df()
        except Exception as e:  # noqa: BLE001
            out[s] = {"error": str(e)}
            continue
        prefixes = sorted({":".join(x.split(":")[:4]) for x in df["series_id"]}) if s in ("wasde", "usda_psd") else []
        out[s] = {"series": len(df), "rows": int(df["n"].sum()) if len(df) else 0,
                  "first": str(df["d0"].min()) if len(df) else None, "last": str(df["d1"].max()) if len(df) else None,
                  "prefixes": prefixes[:400] if prefixes else df["series_id"].tolist()[:60]}
    return out


def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack balance", description="Balance keeper (agent 9): oil and grain balances")
    p.add_argument("cmd", nargs="?", default="show", choices=["show", "probe"])
    p.add_argument("--date", help="as-of date (BRT), default today")
    p.add_argument("--out", help="write the markdown section (show) or the probe JSON (probe) here")
    a = p.parse_args(argv)
    asof = date.fromisoformat(a.date) if a.date else (pd.Timestamp.now(tz="America/Sao_Paulo").date())
    if a.cmd == "probe":
        rep = probe_report()
        txt = json.dumps(rep, indent=1, default=str)
        if a.out:
            Path(a.out).write_text(txt, encoding="utf-8")
        print(txt[:6000])
        return 0
    sec, al = build(asof)
    md = "\n".join(render(sec))
    if a.out:
        Path(a.out).write_text(md + "\n", encoding="utf-8")
    print(md)
    if al:
        print("\nAlerts:\n" + "\n".join(f"- [{x['kind']}] {x['text']}" for x in al))
    runlog.log(runlog.new_run_id(), "balance:show", "ok", asof=str(asof), stocks=len(sec["oil"]["stocks"]),
               grains=len(sec["grains"]), condition=len(sec["condition"]), alerts=len(al))
    return 0
