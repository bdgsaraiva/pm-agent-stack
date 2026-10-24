"""The tape (quant agent, agent 13): one table after the close, computed by code from the quant library, and the
numbered figures the tape card may cite. Written to briefs/<date>/quant.json and quant.md by the close workflow
(.github/workflows/close.yml). The morning note reads only the overnight change against these levels.

Everything is point in time (closes on or before the as-of date; CFTC from its Friday release; implied vol from
FRED's date) and descriptive: stretched, flipped, changed against vol. Nothing here alerts or is a signal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .. import runlog, store
from . import corr, curve, positioning, seasonal, trend, vol
from .common import ROOT, cfg, r, series

BRIEFS = ROOT / "briefs"


def _today() -> date:
    return (datetime.now(timezone.utc) - timedelta(hours=3)).date()


def build(asof: date | None = None, con=None) -> dict:
    asof = asof or _today()
    c = cfg()
    con = con or store.connect()
    prices = {m: series(con, "prices", m, asof) for m in c["markets"]}
    rows = {}
    for m, mc in c["markets"].items():
        p = prices[m]
        if p.empty or (asof - p.index[-1].date()).days > 7:
            rows[m] = {"name": mc["name"], "group": mc["group"], "status": "no recent close"}
            continue
        row = {"name": mc["name"], "group": mc["group"], "close": r(p.iloc[-1], 4), "close_date": str(p.index[-1].date()),
               "url": f"https://finance.yahoo.com/quote/{m}"}
        if len(p) > 1:
            row["ret1_pct"] = r(100 * (p.iloc[-1] / p.iloc[-2] - 1), 2)
        row["stale"] = p.index[-1].date() != asof                 # holiday or failed fetch: no new close today (review S2)
        row["trend"] = trend.state(p, asof, c)
        row["vol"] = vol.state(p, asof, con, mc.get("iv"), c, seasonal_vol=mc["group"] in c["vol"]["seasonal_groups"])
        row["corr"] = corr.state(prices, m, asof, c)
        row["seasonal"] = seasonal.state(p, asof, c)
        row["positioning"] = positioning.state(con, mc["cftc"], asof, c) if mc.get("cftc") else None
        row["curve"] = curve.shape(mc["root"], asof, con) if mc.get("root") else None
        rows[m] = row
    flags = {"flipped": [], "stretched": [], "vol_rising_fast": [], "vol_extreme": [], "iv_gap_stretched": [],
             "corr_unusual": [], "positioning_extreme": []}
    for m, row in rows.items():
        t = row.get("trend") or {}
        if row.get("stale"):                                          # yesterday's flips are not today's news
            continue
        flags["flipped"] += [f"{m}:{h}" for h in t.get("flipped", [])]
        flags["stretched"] += [f"{m}:{h}" for h in t.get("stretched", [])]
        vv = row.get("vol") or {}
        if vv.get("rising_fast"):
            flags["vol_rising_fast"].append(m)
        if vv.get("regime") == "extreme":
            flags["vol_extreme"].append(m)
        if vv.get("gap_stretched"):
            flags["iv_gap_stretched"].append(m)
        flags["corr_unusual"] += [f"{m}~{v}" for v, x in (row.get("corr") or {}).items() if x.get("unusual")]
        if (row.get("positioning") or {}).get("extreme"):
            flags["positioning_extreme"].append(m)
    for m, row in rows.items():
        if (row.get("trend") or {}).get("big_move") and not row.get("stale"):
            flags.setdefault("big_move", []).append(m)
    flags.setdefault("big_move", [])
    out = {"asof": asof.isoformat(), "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
           "method": "docs/research/quant.md", "markets": rows, "flags": flags, "context": context(prices, asof, c)}
    live = [x for x in rows.values() if "close" in x]
    out["stale"] = bool(not live or sum(1 for x in live if x.get("stale")) > len(live) / 2)
    out["changes"] = changes(out)
    out["sources"] = sources(out)
    return out


def context(prices: dict, asof: date, c: dict) -> dict:
    """Average pairwise 63-day correlation of the commodity markets (few independent trends when high: Hurst, Ooi &
    Pedersen; Baltas & Kosowski) and the testing gate's verdicts on the flags the tape shows."""
    import numpy as np
    import pandas as pd
    from .common import pctile
    ids = [m for m in c["context"]["avg_corr_markets"] if len(prices.get(m, [])) > 300]
    out = {}
    if len(ids) >= 3:
        lr = pd.concat({m: np.log(prices[m][prices[m].index <= pd.Timestamp(asof)]).diff() for m in ids}, axis=1).dropna()
        w = c["corr"]["window"]
        vals = []
        steps = list(range(max(w, len(lr) - c["corr"]["lookback_days"]), len(lr) + 1, 5))
        if steps and steps[-1] != len(lr):
            steps.append(len(lr))                                    # "now" always includes today's return
        for i in steps:                                              # every 5 days over 3 years
            cm = lr.iloc[i - w:i].corr().values
            vals.append(float(cm[np.triu_indices_from(cm, 1)].mean()))
        if vals:
            now = vals[-1]
            out["avg_pairwise_corr"] = {"value": r(now, 2), "pctile_3y": r(pctile(pd.Series(vals), now), 0), "markets": len(ids),
                                        "window": w}
    try:
        v = json.loads((ROOT / c["context"]["verdicts"]).read_text(encoding="utf-8"))["verdicts"]
        keep = {k: {"verdict": x.get("verdict"), "flag": x.get("flag") or x.get("strategy"), "params": x.get("params")}
                for k, x in v.items() if (x.get("flag") or x.get("strategy") or "").startswith(("cta", "cftc", "tsmom"))}
        out["measured_verdicts"] = keep
    except (OSError, ValueError, KeyError):
        out["measured_verdicts"] = {}
    return out


def previous(asof: date, briefs: Path | None = None) -> dict | None:
    briefs = briefs or BRIEFS
    days = sorted(p.name for p in briefs.glob("20*-*-*") if (p / "quant.json").exists() and p.name < asof.isoformat())
    return json.loads((briefs / days[-1] / "quant.json").read_text(encoding="utf-8")) if days else None


def changes(t: dict, briefs: Path | None = None) -> dict:
    prev = previous(date.fromisoformat(t["asof"]), briefs)
    if not prev:
        return {"vs": None, "note": "first tape: no earlier tape to compare"}
    out = {"vs": prev["asof"]}
    for k in ("stretched", "positioning_extreme", "corr_unusual", "vol_rising_fast", "vol_extreme", "iv_gap_stretched", "big_move"):
        a, b = set(prev["flags"].get(k, [])), set(t["flags"].get(k, []))
        out[k] = {"new": sorted(b - a), "gone": sorted(a - b)}
    return out


def sources(t: dict) -> list[dict]:
    """Numbered figures the tape card may cite (the card validator checks every number against these)."""
    out = []

    def add(label, value, unit, day, url, frm):
        if value is None:
            return
        # stable id from the row's origin: a rebuilt tape keeps the same id for the same figure (review S2)
        sid = "s" + str(int(hashlib.sha1(frm.encode()).hexdigest()[:7], 16))
        out.append({"id": sid, "label": label, "value": value, "unit": unit, "date": day, "url": url, "from": frm})
    for m, row in t["markets"].items():
        if "close" not in row:
            continue
        d, u, n = row["close_date"], row["url"], row["name"]
        add(f"{n} close", row["close"], "close", d, u, f"quant.json:markets[{m}].close")
        add(f"{n} 1-day change", row.get("ret1_pct"), "%", d, u, f"quant.json:markets[{m}].ret1_pct")
        tr = row.get("trend") or {}
        if tr.get("big_move"):
            add(f"{n} 1-day move in trailing daily sd", tr.get("z1d"), "sd", d, u, f"quant.json:markets[{m}].trend.z1d")
            add(f"{n} 5-day move in trailing sd", tr.get("z5d"), "sd", d, u, f"quant.json:markets[{m}].trend.z5d")
        for h, leg in ((row.get("trend") or {}).get("legs") or {}).items():
            if leg.get("flipped") or leg.get("stretched") or leg.get("rolloff_flip_days"):
                add(f"{n} {h}-day trend flip level", leg.get("flip_level"), "close", d, u, f"quant.json:markets[{m}].trend.legs[{h}].flip_level")
                add(f"{n} {h}-day distance to flip", leg.get("distance_sd"), "sd", d, u, f"quant.json:markets[{m}].trend.legs[{h}].distance_sd")
                add(f"{n} {h}-day distance percentile (since 2000)", leg.get("distance_pctile"), "pctile", d, u, f"quant.json:markets[{m}].trend.legs[{h}].distance_pctile")
        v = row.get("vol") or {}
        add(f"{n} 21-day realised vol", v.get("rv_short"), "% ann.", d, u, f"quant.json:markets[{m}].vol.rv_short")
        add(f"{n} 21-day realised vol percentile (3 years)", v.get("pctile_3y"), "pctile", d, u, f"quant.json:markets[{m}].vol.pctile_3y")
        add(f"{n} 21-day realised vol percentile (since {v.get('full_since')}; regime {v.get('regime')})", v.get("pctile_full"), "pctile", d, u, f"quant.json:markets[{m}].vol.pctile_full")
        add(f"{n} 21-day vol percentile, same calendar month in earlier years", v.get("pctile_same_month"), "pctile", d, u, f"quant.json:markets[{m}].vol.pctile_same_month")
        add(f"{n} 21-day over 63-day vol", v.get("ratio"), "x", d, u, f"quant.json:markets[{m}].vol.ratio")
        add(f"{n} 21-day vol change over a week", v.get("change_1w"), "vol pts", d, u, f"quant.json:markets[{m}].vol.change_1w")
        if v.get("iv") is not None:
            add(f"{n} implied vol, {v['iv_instrument']}", v["iv"], "%", v["iv_date"], v["iv_url"], f"quant.json:markets[{m}].vol.iv")
            add(f"{n} implied minus 21-day realised vol", v.get("iv_minus_rv"), "vol pts", v["iv_date"], v["iv_url"], f"quant.json:markets[{m}].vol.iv_minus_rv")
            add(f"{n} implied-minus-realised gap, percentile (3 years)", v.get("gap_pctile"), "pctile", v["iv_date"], v["iv_url"], f"quant.json:markets[{m}].vol.gap_pctile")
        for vs, x in (row.get("corr") or {}).items():
            if x.get("unusual"):
                add(f"{n} 63-day correlation with {vs}", x["corr"], "corr", d, u, f"quant.json:markets[{m}].corr[{vs}].corr")
                add(f"{n} correlation with {vs}, percentile (3 years)", x["pctile"], "pctile", d, u, f"quant.json:markets[{m}].corr[{vs}].pctile")
                add(f"{n} own 63-day vol change over a month (beside the correlation)", x.get("own_vol_change_1m"), "vol pts", d, u, f"quant.json:markets[{m}].corr[{vs}].own_vol_change_1m")
        ps = row.get("positioning") or {}
        if ps:
            add(f"{n} managed money net, % of open interest", ps.get("net_pct_oi"), "%", ps["report_date"], ps["url"], f"quant.json:markets[{m}].positioning.net_pct_oi")
            add(f"{n} managed money, 3-year percentile", ps.get("pctile_3y"), "pctile", ps["report_date"], ps["url"], f"quant.json:markets[{m}].positioning.pctile_3y")
            add(f"{n} managed money, weekly change (flow)", ps.get("wow_pp"), "pp", ps["report_date"], ps["url"], f"quant.json:markets[{m}].positioning.wow_pp")
            add(f"{n} managed money, 52-week average (slow)", ps.get("slow_52w"), "%", ps["report_date"], ps["url"], f"quant.json:markets[{m}].positioning.slow_52w")
            add(f"{n} open interest, change over 12 months", ps.get("oi_12m_change_pct"), "%", ps["report_date"], ps["url"], f"quant.json:markets[{m}].positioning.oi_12m_change_pct")
        s = row.get("seasonal") or {}
        if s:
            add(f"{n} seasonal norm {s['period']}: median return over {s['years']} years (descriptive, not a signal)", s.get("median_pct"), "%", d, u, f"quant.json:markets[{m}].seasonal.median_pct")
            add(f"{n} seasonal norm {s['period']}: share of years up", s.get("up_share"), "share", d, u, f"quant.json:markets[{m}].seasonal.up_share")
        cv = row.get("curve") or {}
        if cv:
            add(f"{n} M1 minus M2, % of M1", cv.get("m1_m2_pct"), "%", cv["date"], cv["source_url"], f"quant.json:markets[{m}].curve.m1_m2_pct")
            add(f"{n} carry, annualised (M1 over M2)", cv.get("carry_ann_pct"), "% ann.", cv["date"], cv["source_url"], f"quant.json:markets[{m}].curve.carry_ann_pct")
    ac = (t.get("context") or {}).get("avg_pairwise_corr")
    if ac:
        add(f"Average pairwise {ac['window']}-day correlation of {ac['markets']} commodity markets", ac["value"], "corr", t["asof"], "quant.json", "quant.json:context.avg_pairwise_corr.value")
        add("Average pairwise commodity correlation, percentile (3 years)", ac["pctile_3y"], "pctile", t["asof"], "quant.json", "quant.json:context.avg_pairwise_corr.pctile_3y")
    return out


def _f(x, nd=1, sign=False):
    if x is None:
        return "-"
    return f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"


def render(t: dict) -> str:
    L = [f"# Tape after the close: {t['asof']}", "",
         "Computed by code (`pmstack quant tape`): trend legs and CTA flip levels, realised and implied vol, correlation regime, "
         "positioning, half-month seasonality, front curve. Descriptive only: nothing here is a signal. Method: `docs/research/quant.md`.", ""]
    f = t["flags"]
    if t.get("stale"):
        L += ["**No new close for most markets today (holiday or failed fetch): flips and big moves are suppressed.**", ""]
    L += ["## What changed", ""]
    L.append(f"- Trend legs that flipped today: {', '.join(f['flipped']) or 'none'}")
    L.append(f"- Stretched legs (distance to flip beyond 2 sd and the 95th/5th percentile of its history since 2000; a print rule, base rate not studied): {', '.join(f['stretched']) or 'none'}")
    L.append(f"- Vol rising fast (21-day vol at least 1.5x the 63-day): {', '.join(f['vol_rising_fast']) or 'none'}")
    L.append(f"- Vol in the extreme regime (at or above the 95th percentile of its full history): {', '.join(f['vol_extreme']) or 'none'}")
    L.append(f"- Implied-minus-realised gap outside its 3-year 10-90 band: {', '.join(f['iv_gap_stretched']) or 'none'}")
    L.append(f"- Correlation outside its 3-year 10-90 band: {', '.join(f['corr_unusual']) or 'none'}")
    L.append(f"- Positioning at a 3-year extreme (CFTC, from the Friday release): {', '.join(f['positioning_extreme']) or 'none'}")
    L.append(f"- Large moves vs recent vol (1-day or 5-day beyond 2 trailing sd): {', '.join(f.get('big_move', [])) or 'none'}")
    ctx = t.get("context") or {}
    ac = ctx.get("avg_pairwise_corr")
    if ac:
        L.append(f"- Average pairwise {ac['window']}-day correlation across {ac['markets']} commodity markets: {ac['value']} (percentile {_f(ac['pctile_3y'], 0)} of the last 3 years)")
    mv = ctx.get("measured_verdicts") or {}
    if mv:
        L.append("- Measured by the testing gate (research/index.md): " + "; ".join(f"{k} {x['verdict']}" for k, x in sorted(mv.items()))
                 + ". Stretched and flipped are print rules with no study yet.")
    ch = t.get("changes") or {}
    if ch.get("vs"):
        L.append(f"- Since the {ch['vs']} tape: newly stretched {', '.join(ch['stretched']['new']) or 'none'}; no longer stretched {', '.join(ch['stretched']['gone']) or 'none'}")
    L += ["", "## Markets", "",
          "| Market | Close | 1d % | Trend 1m / 3m / 12m (flip; distance sd) | State | Vol 21d (3y pctile; regime) | 21d/63d | Implied - realised (gap pctile) | MM % OI (pctile) | Carry ann. % | Next half-month norm: median % [IQR] (years) |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for m, row in t["markets"].items():
        if "close" not in row:
            L.append(f"| {row['name']} | {row.get('status')} | | | | | | | | | |")
            continue
        tr, v, ps, s, cv = row.get("trend") or {}, row.get("vol") or {}, row.get("positioning") or {}, row.get("seasonal") or {}, row.get("curve") or {}
        legs = []
        for h in ("21", "63", "252"):
            lg = (tr.get("legs") or {}).get(h)
            if lg:
                mark = "!" if lg.get("flipped") else ("*" if lg.get("stretched") else "")
                legs.append(f"{'+' if lg['sign'] > 0 else '-'}{mark} {lg['flip_level']:g} ({_f(lg.get('distance_sd'), 1, True)})")
        L.append(f"| [{row['name']}]({row['url']}) | {row['close']:g} | {_f(row.get('ret1_pct'), 2, True)} | {' / '.join(legs) or '-'} | {tr.get('state') or '-'} | "
                 f"{_f(v.get('rv_short'))} ({_f(v.get('pctile_3y'), 0)}; {v.get('regime') or '-'}) | {_f(v.get('ratio'), 2)} | "
                 f"{_f(v.get('iv_minus_rv'), 1, True)} ({_f(v.get('gap_pctile'), 0)}) | "
                 f"{_f(ps.get('net_pct_oi'))} ({_f(ps.get('pctile_3y'), 0)}) | {_f(cv.get('carry_ann_pct'), 1, True)} | "
                 f"{_f(s.get('median_pct'), 2, True)} [{_f((s.get('iqr_pct') or [None, None])[0], 1, True)}, {_f((s.get('iqr_pct') or [None, None])[1], 1, True)}] ({s.get('years', '-')}) |")
    L += ["", "Legend: `!` flipped today, `*` stretched. Seasonality: a norm (median and interquartile range of the next half-month in "
          "earlier years), descriptive and never a signal; 24 buckets, so about one clears 5% by chance. Implied vol: OVX is options on the "
          "USO ETF and GVZ on GLD, not on the futures; implied above realised is the normal state. Prices are Yahoo continuous front "
          "months: 3- and 12-month flip levels can sit on an expired contract and roll gaps enter vol and seasonal norms. Curve and carry from contracts collected since 24 Oct 2026 "
          "(Yahoo, personal use). Implied vol: CBOE OVX/GVZ/VIX via FRED."]
    return "\n".join(L) + "\n"


def write(t: dict, briefs: Path | None = None) -> list[Path]:
    briefs = briefs or BRIEFS
    d = briefs / t["asof"]
    d.mkdir(parents=True, exist_ok=True)
    pj, pm = d / "quant.json", d / "quant.md"
    pj.write_text(json.dumps(t, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    pm.write_text(render(t), encoding="utf-8")
    return [pj, pm]


def cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="pmstack quant")
    sub = p.add_subparsers(dest="cmd", required=True)
    tp = sub.add_parser("tape", help="build the tape after the close (briefs/<date>/quant.json|md with --write)")
    tp.add_argument("--date")
    tp.add_argument("--write", action="store_true")
    a = p.parse_args(argv)
    t = build(date.fromisoformat(a.date) if a.date else None)
    paths = write(t) if a.write else []
    runlog.log(runlog.new_run_id(), "quant:tape", "ok", asof=t["asof"], flags={k: len(v) for k, v in t["flags"].items()},
               sources=len(t["sources"]), outputs=[x.relative_to(ROOT).as_posix() for x in paths])
    print(json.dumps({"asof": t["asof"], "flags": t["flags"], "sources": len(t["sources"]),
                      "written": [x.relative_to(ROOT).as_posix() for x in paths]}, indent=1))
    return 0
