"""Monitor 3a: commodity supply-demand + central-bank text.

Computes every number deterministically from the research memory and writes, for date D:
  briefs/D/facts.json   structured facts (each with value, date, source_url)
  briefs/D/alerts.json  ranked alerts
  briefs/D/facts.md     the fact pack the morning-note agent is allowed to quote from

Alerts mean "look at this", not "trade this". No signal is promoted without the
quant-research gate (Step 6).
"""
from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yaml

from . import runlog, store

ROOT = Path(__file__).resolve().parents[1]
BRT = ZoneInfo("America/Sao_Paulo")
BRIEFS = ROOT / "briefs"


# ---------------------------------------------------------------- helpers
def _cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "monitor.yaml").read_text(encoding="utf-8"))


def _src() -> dict:
    return yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))


def _series(obs: pd.DataFrame, sid: str) -> pd.DataFrame:
    s = obs[obs.series_id == sid].dropna(subset=["value"]).sort_values("date")
    return s


def _fmt(x, nd=2, pct=False, sign=False):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "n/a"
    s = f"{x:+,.{nd}f}" if sign else f"{x:,.{nd}f}"
    return s + ("%" if pct else "")


def _link(label: str, url: str) -> str:
    return f"[{label}]({url})"


CASH_ETFS = {"XLE", "XLB", "EWZ", "SPY", "QQQ"}


def _utc(ts) -> str:
    t = pd.Timestamp(ts)
    t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    return t.strftime("%Y-%m-%d %H:%M")


def _f(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else float(x)


# ---------------------------------------------------------------- sections
def prices(obs: pd.DataFrame, cfg: dict, asof: date) -> tuple[list[dict], list[dict]]:
    rows, alerts = [], []
    tick = {t["id"]: t for t in _src()["prices"]["tickers"]}
    for sid, t in tick.items():
        s = _series(obs[obs.source == "prices"], sid)
        s = s[s.date <= asof]
        # Futures and FX trade through the night: a bar dated today (BRT) is still live, not a close.
        # Asia cash indices have closed by the time the Action runs, so their bar for today is final.
        live = None
        if t["group"] != "asia" and len(s) and s.date.iloc[-1] >= asof:
            fetched = pd.Timestamp(s.fetched_at.iloc[-1])
            fetched = (fetched.tz_localize("UTC") if fetched.tzinfo is None else fetched).tz_convert(BRT)
            # Daily bar dated today is final after the close: US cash 17:00 BRT, futures and FX 18:00 BRT.
            cutoff = 17 if (sid.startswith("^") or sid in CASH_ETFS) else 18
            if fetched.date() == asof and fetched.hour < cutoff:
                live = s.iloc[-1]
                s = s.iloc[:-1]
        if len(s) < 3:
            continue
        v = s.value.to_numpy()
        lr = np.diff(np.log(v))
        r1 = v[-1] / v[-2] - 1
        r5 = v[-1] / v[-6] - 1 if len(v) >= 6 else float("nan")
        win = lr[-(cfg["vol_window"] + 1):-1]
        vol = float(np.std(win, ddof=1)) if len(win) >= 20 else float("nan")
        z = float(lr[-1] / vol) if vol and not math.isnan(vol) and vol > 0 else float("nan")
        live_pct = _f(100 * (live.value / v[-1] - 1)) if live is not None else None
        live_z = (math.log(live.value / v[-1]) / vol) if live is not None and vol and not math.isnan(vol) else float("nan")
        row = {"id": sid, "name": t["name"], "group": t["group"], "date": str(s.date.iloc[-1]),
               "last": _f(v[-1]), "ret1_pct": _f(100 * r1), "ret5_pct": _f(100 * r5), "z1": _f(z),
               "live": _f(live.value) if live is not None else None, "live_pct": live_pct,
               "live_fetched_utc": _utc(live.fetched_at) if live is not None else None,
               "source_url": s.source_url.iloc[-1]}
        rows.append(row)
        if not math.isnan(z) and abs(z) >= cfg["move_z"]:
            alerts.append({"kind": "price_move", "severity": abs(z), "id": sid,
                           "text": f"{t['name']} {_fmt(100 * r1, 1, True, True)} on {row['date']} ({_fmt(z, 1)} sd of 60-day vol)",
                           "source_url": row["source_url"]})
        if not math.isnan(live_z) and abs(live_z) >= cfg["move_z"]:
            alerts.append({"kind": "overnight_move", "severity": abs(live_z), "id": sid,
                           "text": (f"{t['name']} {_fmt(live_pct, 1, True, True)} overnight vs the {row['date']} close "
                                    f"(live at {row['live_fetched_utc']} UTC, {_fmt(live_z, 1)} sd)"),
                           "source_url": row["source_url"]})
    return rows, alerts


def eia(obs: pd.DataFrame, cfg: dict, asof: date) -> tuple[list[dict], list[dict]]:
    rows, alerts = [], []
    for s_cfg in _src()["eia"]["series"]:
        s = _series(obs[obs.source == "eia"], s_cfg["id"])
        s = s[s.date <= asof]
        if len(s) < 60:
            continue
        s = s.assign(chg=s.value.diff(), wk=pd.to_datetime(s.date).dt.isocalendar().week.astype(int),
                     yr=pd.to_datetime(s.date).dt.year)
        last = s.iloc[-1]
        hist = s[(s.yr >= last.yr - cfg["seasonal_years"]) & (s.yr < last.yr)]
        near = hist[(hist.wk - last.wk).abs().isin([0, 1]) | ((hist.wk - last.wk).abs() >= 51)]
        mu, sd = near.chg.mean(), near.chg.std(ddof=1)
        z = (last.chg - mu) / sd if sd and sd > 0 else float("nan")
        row = {"id": s_cfg["id"], "name": s_cfg["name"], "unit": s_cfg["unit"], "week_ending": str(last.date),
               "level": _f(last.value), "change": _f(last.chg), "seasonal_mean_change": _f(mu),
               "seasonal_sd": _f(sd), "surprise_z": _f(z), "n_seasonal_obs": int(near.chg.notna().sum()),
               "source_url": last.source_url}
        rows.append(row)
        if not math.isnan(z) and abs(z) >= cfg["surprise_z"]:
            alerts.append({"kind": "eia_surprise", "severity": abs(z), "id": s_cfg["id"],
                           "text": (f"{s_cfg['name']}: {_fmt(last.chg, 0, sign=True)} {s_cfg['unit']} in week to {last.date} "
                                    f"vs 5-year same-week average {_fmt(mu, 0, sign=True)} ({_fmt(z, 1)} sd)"),
                           "source_url": last.source_url})
    return rows, alerts


def cftc(obs: pd.DataFrame, cfg: dict, asof: date) -> tuple[list[dict], list[dict]]:
    rows, alerts = [], []
    for m in _src()["cftc"]["markets"]:
        s = _series(obs[obs.source == "cftc"], f"{m['code']}.mm_net_pct_oi")
        s = s[s.date <= asof]
        if len(s) < 52:
            continue
        w = s.tail(cfg["lookback_weeks"])
        v = w.value.to_numpy()
        pct = 100 * (v <= v[-1]).mean()
        d = np.diff(v)
        dz = (d[-1] - d[:-1].mean()) / d[:-1].std(ddof=1) if len(d) > 10 and d[:-1].std(ddof=1) > 0 else float("nan")
        net = _series(obs[obs.source == "cftc"], f"{m['code']}.mm_net")
        net = net[net.date <= asof]
        row = {"code": m["code"], "name": m["name"], "date": str(s.date.iloc[-1]),
               "mm_net_pct_oi": _f(v[-1]), "mm_net_contracts": _f(net.value.iloc[-1]) if len(net) else None,
               "pct_3y": _f(pct), "wow_change_pp": _f(d[-1]), "wow_z": _f(dz), "source_url": s.source_url.iloc[-1]}
        rows.append(row)
        hi = cfg["extreme_pct"]
        if pct >= hi or pct <= 100 - hi:
            side = "long" if pct >= hi else "short"
            alerts.append({"kind": "positioning_extreme", "severity": 2 + (abs(pct - 50) - (hi - 50)) / 5, "id": m["code"],
                           "text": (f"{m['name']}: managed money net {_fmt(v[-1], 1)}% of OI on {row['date']}, "
                                    f"{_fmt(pct, 0)}th percentile of 3 years (crowded {side})"),
                           "source_url": row["source_url"]})
        if not math.isnan(dz) and abs(dz) >= cfg["weekly_change_z"]:
            alerts.append({"kind": "positioning_shift", "severity": abs(dz), "id": m["code"],
                           "text": f"{m['name']}: managed money net moved {_fmt(d[-1], 1, sign=True)} pp of OI in the week to {row['date']} ({_fmt(dz, 1)} sd)",
                           "source_url": row["source_url"]})
    return rows, alerts


def fred(obs: pd.DataFrame, cfg: dict, asof: date) -> tuple[list[dict], list[dict]]:
    rows, alerts = [], []
    for s_cfg in _src()["fred"]["series"]:
        s = _series(obs[obs.source == "fred"], s_cfg["id"])
        s = s[s.date <= asof]
        if len(s) < 2:
            continue
        v = s.value.to_numpy()
        is_rate = s_cfg["unit"] == "pct"
        chg = (v[-1] - v[-2]) * (100 if is_rate else 1) if is_rate else 100 * (v[-1] / v[-2] - 1)
        d = np.diff(v[-61:]) if is_rate else np.diff(np.log(v[-61:]))
        z = (d[-1] / d[:-1].std(ddof=1)) if len(d) > 20 and d[:-1].std(ddof=1) > 0 else float("nan")
        row = {"id": s_cfg["id"], "name": s_cfg["name"], "unit": s_cfg["unit"], "date": str(s.date.iloc[-1]),
               "last": _f(v[-1]), "change": _f(chg), "change_unit": "bp" if is_rate else "%",
               "z1": _f(z) if s_cfg.get("freq", "daily") == "daily" else None, "source_url": s.source_url.iloc[-1]}
        rows.append(row)
        if s_cfg.get("freq", "daily") == "daily" and not math.isnan(z) and abs(z) >= cfg["move_z"]:
            alerts.append({"kind": "macro_move", "severity": abs(z), "id": s_cfg["id"],
                           "text": f"{s_cfg['name']} {_fmt(chg, 1, sign=True)}{'bp' if is_rate else '%'} on {row['date']} ({_fmt(z, 1)} sd)",
                           "source_url": row["source_url"]})
    return rows, alerts


def bcb(obs: pd.DataFrame, cfg: dict, asof: date) -> tuple[list[dict], list[dict]]:
    rows, alerts = [], []
    if "bcb" not in _src():          # Brazil block disabled in config/sources.yaml
        return rows, alerts
    b = obs[obs.source == "bcb"]
    for s_cfg in _src()["bcb"]["sgs"]:
        s = _series(b, f"sgs.{s_cfg['id']}")
        s = s[s.date <= asof]
        if s.empty:
            continue
        prev = s.value.iloc[-2] if len(s) > 1 else None
        rows.append({"id": f"sgs.{s_cfg['id']}", "name": s_cfg["name"], "unit": s_cfg["unit"], "date": str(s.date.iloc[-1]),
                     "last": _f(s.value.iloc[-1]), "previous": _f(prev), "source_url": s.source_url.iloc[-1]})
    thr = cfg["focus_change_bp"] / 100
    for ref_year in (asof.year, asof.year + 1):
        for f in _src()["bcb"]["focus"]:
            slug = f["indicator"].lower().replace("â", "a")
            s = _series(b, f"focus.{slug}.{ref_year}")
            s = s[s.date <= asof]
            if s.empty:
                continue
            last = s.iloc[-1]
            wk = s[pd.to_datetime(s.date) <= pd.Timestamp(last.date) - pd.Timedelta(days=7)]
            prev = wk.value.iloc[-1] if len(wk) else None
            chg = (last.value - prev) if prev is not None else None
            rows.append({"id": f"focus.{slug}.{ref_year}", "name": f"{f['name']} for {ref_year}", "unit": last.unit,
                         "date": str(last.date), "last": _f(last.value), "previous": _f(prev),
                         "change": _f(chg), "source_url": last.source_url})
            if chg is not None and abs(chg) >= thr - 1e-9:
                alerts.append({"kind": "focus_revision", "severity": 2.0, "id": f"focus.{slug}.{ref_year}",
                               "text": f"{f['name']} for {ref_year}: {_fmt(prev)} → {_fmt(last.value)} in the week to {last.date}",
                               "source_url": last.source_url})
    return rows, alerts


def cbtext(txt: pd.DataFrame, cfg: dict, now: datetime) -> tuple[list[dict], list[dict]]:
    if txt.empty:
        return [], []
    kw = [k.lower() for k in _src()["cbtext"]["keywords"]]
    t = txt.copy()
    t["published"] = pd.to_datetime(t["published"], utc=True, errors="coerce")
    cutoff = pd.Timestamp(now) - pd.Timedelta(hours=cfg["lookback_hours"])
    t = t[t.published >= cutoff].sort_values("published", ascending=False)
    rows, alerts = [], []
    pats = {k: re.compile(r"\b" + re.escape(k) + r"\b", re.IGNORECASE) for k in kw}
    for r in t.itertuples():
        hay = f"{r.title} {r.summary}"
        hits = [k for k, p in pats.items() if p.search(hay)]
        rows.append({"source": r.source, "title": r.title, "url": r.url,
                     "published_utc": r.published.isoformat(), "keywords": hits, "summary": r.summary})
        if hits:
            alerts.append({"kind": "policy_text", "severity": 2.5, "id": r.source,
                           "text": f"{r.source.upper()}: {r.title} ({r.published:%d %b %H:%M} UTC)", "source_url": r.url})
    return rows, alerts


def missing(obs: pd.DataFrame) -> list[str]:
    """Configured price tickers and FRED/EIA series that have no stored data at all."""
    src = _src()
    counts = obs.groupby("series_id").size() if not obs.empty else pd.Series(dtype=int)
    have = set(counts[counts >= 20].index)          # fewer than 20 points = too little history to use
    want = [t["id"] for t in src.get("prices", {}).get("tickers", [])]
    want += [x["id"] for x in src.get("fred", {}).get("series", [])]
    want += [x["id"] for x in src.get("eia", {}).get("series", [])]
    return [w for w in want if w not in have]


def health(obs: pd.DataFrame, cfg: dict, asof: date) -> list[dict]:
    lim = cfg["staleness"]
    out = []
    if obs.empty:
        return out
    src = _src()
    cfg_freq = {x["id"]: x.get("freq", "daily") for x in src.get("fred", {}).get("series", [])}
    configured = {t["id"] for t in src.get("prices", {}).get("tickers", [])}
    configured |= {x["id"] for x in src.get("fred", {}).get("series", [])} | {x["id"] for x in src.get("eia", {}).get("series", [])}
    g = obs.groupby(["source", "series_id"]).agg(last=("date", "max"), freq=("freq", "first"), name=("name", "first")).reset_index()
    for r in g.itertuples():
        if r.source in ("prices", "fred", "eia") and r.series_id not in configured:
            continue                     # dropped from config: history kept, no longer monitored
        if r.source not in src and r.source != "prices":
            continue                     # whole source disabled (e.g. bcb)
        age = (asof - r.last).days
        freq = cfg_freq.get(r.series_id, r.freq)
        cap = lim.get(freq, 45)
        if freq != "event" and age > cap:
            out.append({"source": r.source, "series_id": r.series_id, "name": r.name, "last": str(r.last), "age_days": age})
    return out


# ---------------------------------------------------------------- fact pack
READ_THROUGH = {
    "Oil complex": ["BZ=F", "CL=F", "HO=F", "RB=F", "NG=F", "XLE"],
    "Metals and China": ["HG=F", "GC=F", "SI=F", "000001.SS", "^HSI", "CNY=X", "XLB"],
    "US equities": ["^GSPC", "^NDX", "^RUT", "^VIX", "ES=F", "NQ=F", "BAMLH0A0HYM2"],
    "US rates": ["DGS2", "DGS10", "DGS30", "T10Y2Y", "DFII10", "T10YIE", "SOFR", "ZN=F", "ZT=F"],
    "USD": ["DX-Y.NYB", "DTWEXBGS", "EURUSD=X", "JPY=X", "AUDUSD=X", "CNY=X"],
}


def build(asof: date | None = None, now: datetime | None = None, run_id: str | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    asof = asof or now.astimezone(BRT).date()
    run_id = run_id or runlog.new_run_id()
    cfg = _cfg()
    con = store.connect()
    obs = con.execute("SELECT * FROM obs").df()
    txt = con.execute("SELECT * FROM text").df()
    if not obs.empty:
        obs["date"] = pd.to_datetime(obs["date"]).dt.date

    sections, alerts = {}, []
    for name, fn in [("prices", prices), ("eia", eia), ("cftc", cftc), ("fred", fred), ("bcb", bcb)]:
        try:
            rows, al = fn(obs, cfg[name] if name in cfg else cfg.get("fred", {}), asof) if not obs.empty else ([], [])
        except Exception as e:
            rows, al = [{"error": f"{type(e).__name__}: {e}"}], []
        sections[name], alerts = rows, alerts + al
    rows, al = cbtext(txt, cfg["cbtext"], now)
    sections["cbtext"], alerts = rows, alerts + al
    sections["stale"] = health(obs, cfg, asof)
    sections["missing"] = missing(obs)
    last_fetch = [r for r in runlog.read(400) if r["step"].startswith("fetch:")]
    if last_fetch:
        latest_run = last_fetch[-1]["run_id"]
        sections["fetch_status"] = [{"source": r["step"][6:], "status": r["status"], "errors": r.get("errors", [])}
                                    for r in last_fetch if r["run_id"] == latest_run]
    else:
        sections["fetch_status"] = []

    alerts.sort(key=lambda a: -a["severity"])
    for i, a in enumerate(alerts, 1):
        a["rank"] = i
        a["ref"] = f"alerts:{asof}#{i}"          # cite in a journal entry's source_ref (alert -> idea -> outcome)
        a["severity"] = round(float(a["severity"]), 2)
    sections["journal"] = journal_section(now)

    facts = {"asof_brt": str(asof), "generated_utc": now.isoformat(timespec="seconds"), "run_id": run_id,
             "sections": sections, "alerts": alerts}
    out = BRIEFS / str(asof)
    out.mkdir(parents=True, exist_ok=True)
    (out / "facts.json").write_text(json.dumps(facts, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    (out / "alerts.json").write_text(json.dumps(alerts, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    (out / "facts.md").write_text(render_md(facts), encoding="utf-8")
    runlog.log(run_id, "monitor:commodity_cb", "ok", asof=str(asof), alerts=len(alerts),
               outputs=[f"briefs/{asof}/facts.md", f"briefs/{asof}/facts.json", f"briefs/{asof}/alerts.json"],
               input_hashes={p.relative_to(store.DATA).as_posix(): runlog.file_hash(p) for p in sorted(store.DATA.rglob("*.parquet"))})
    return facts


def journal_section(now: datetime) -> dict:
    """Open ideas against the latest prices, plus closes and rejections in the last 7 days."""
    from . import journal
    try:
        entries = {e["id"]: e for e in journal.load_all()}
        book = journal.open_book(now=now)
        cmap = journal._cfg()["cftc_map"]
        for r in book:
            e = entries[r["id"]]
            r["book"], r["source_ref"] = e.get("book"), e.get("source_ref")
            r["cftc"] = journal._cftc_pct(cmap.get(r.get("price_ref") or ""))
            r["past_horizon"] = bool(r.get("horizon_days")) and r["days_open"] > float(r["horizon_days"])
        cutoff = pd.Timestamp(now) - pd.Timedelta(days=7)
        recent = []
        for e in entries.values():
            t = e.get("closed_utc") or e.get("rejected_utc")
            if e.get("status") in ("closed", "rejected") and t and pd.Timestamp(t) >= cutoff:
                recent.append({"id": e["id"], "status": e["status"], "market": e.get("market"),
                               "r_multiple": e.get("r_multiple"), "reason": e.get("reject_reason"),
                               "process_score": e.get("process_score")})
        return {"open": book, "recent": recent, "stats": journal.stats(list(entries.values()))}
    except Exception as ex:   # the journal must never stop the fact pack
        return {"error": f"{type(ex).__name__}: {ex}", "open": [], "recent": []}


def render_md(f: dict) -> str:
    S = f["sections"]
    L = [f"# Fact pack — {f['asof_brt']} (BRT)", "",
         f"Generated {f['generated_utc']} UTC · run `{f['run_id']}`. Every figure below links to its source. "
         "The morning note may quote only figures that appear here.", ""]

    L += ["## Alerts (ranked)", ""]
    if f["alerts"]:
        L += [f"{a['rank']}. {a['text']} — {_link('source', a['source_url'])} `{a.get('ref', '')}`" for a in f["alerts"]]
    else:
        L += ["No alerts crossed their thresholds."]
    L += [""]

    J = S.get("journal") or {}
    L += ["## Your open ideas (journal)", ""]
    if J.get("error"):
        L.append(f"Journal could not be read: {J['error']}")
    rows = J.get("open") or []
    if rows:
        L += ["| Idea | Dir | Conv | Last (date) | To invalidation | To target | R now | Days / horizon | CFTC pct on side | Flags | Price source |",
              "|---|---|---:|---|---:|---:|---:|---|---:|---|---|"]
        for r in rows:
            flags = []
            if r.get("invalidated"):
                flags.append("INVALIDATED")
            if r.get("past_horizon"):
                flags.append("past horizon")
            c = r.get("cftc")
            if c and r.get("direction") in ("long", "short"):
                side_pct = c["pct"] if r["direction"] == "long" else 100 - c["pct"]
                cf = f"{side_pct:.0f} ({c['date']})"
                if side_pct >= 90:
                    flags.append("crowded")
            else:
                cf = "n/a"
            name = r["market"] + (" (example)" if r.get("book") == "example" else "") + f" `{r['id']}`"
            last = f"{_fmt(r.get('last'))} ({r.get('last_date')})" if r.get("last") is not None else "n/a"
            hz = f"{r['days_open']:.0f} / {r['horizon_days']}" if r.get("horizon_days") else f"{r['days_open']:.0f} / -"
            link = _link(r["price_ref"], r["source_url"]) if r.get("source_url") else "-"
            L.append(f"| {name} | {r['direction']} | {r.get('conviction')} | {last} | {_fmt(r.get('to_invalidation_pct'), 1, True, True)} | "
                     f"{_fmt(r.get('to_target_pct'), 1, True, True)} | {_fmt(r.get('r_now'), 2, sign=True)} | {hz} | {cf} | {', '.join(flags) or '-'} | {link} |")
        L.append("")
        L.append("R now = move since entry in units of initial risk (entry to invalidation). CFTC pct on side = 3-year percentile of managed-money positioning in the idea's direction (100 = most crowded).")
    else:
        L.append("No open ideas in the journal. Log one with `/journal <idea>`.")
    if J.get("recent"):
        L += ["", "Closed or rejected in the last 7 days: " + "; ".join(
            f"{x['market']} `{x['id']}` {x['status']}" + (f" {x['r_multiple']:+}R" if x.get("r_multiple") is not None else "")
            + (f" ({x['reason']})" if x.get("reason") else "") for x in J["recent"])]
    L += [""]

    px = {r["id"]: r for r in S.get("prices", []) if "id" in r}
    def ptable(group, title):
        rs = [r for r in px.values() if r["group"] == group]
        if not rs:
            return []
        has_live = any(r.get("live") is not None for r in rs)
        head = "| Instrument | Close | Date | 1d | 5d | 1d move (sd) |" + (" Live vs close |" if has_live else "") + " Source |"
        out = [f"## {title}", "", head, "|---|---:|---|---:|---:|---:|" + ("---:|" if has_live else "") + "---|"]
        for r in rs:
            lv = f" {_fmt(r['live_pct'], 1, True, True)} |" if r.get("live") is not None else (" |" if has_live else "")
            out.append(f"| {r['name']} | {_fmt(r['last'])} | {r['date']} | {_fmt(r['ret1_pct'], 1, True, True)} | "
                       f"{_fmt(r['ret5_pct'], 1, True, True)} | {_fmt(r['z1'], 1)} |{lv} {_link(r['id'], r['source_url'])} |")
        if has_live:
            t0 = next(r["live_fetched_utc"] for r in rs if r.get("live") is not None)
            out.append(f"\nLive = the price still trading when fetched ({t0} UTC), against the last settled close.")
        return out + [""]
    L += ptable("asia", "Overnight: Asia session closes")
    L += ptable("energy", "Energy")
    L += ptable("metals", "Metals")
    L += ptable("ags", "Agriculture")
    if "BZ=F" in px and "CL=F" in px and px["BZ=F"]["date"] == px["CL=F"]["date"]:
        L += [f"Brent–WTI front-month spread: {_fmt(px['BZ=F']['last'] - px['CL=F']['last'])} $/bbl on {px['BZ=F']['date']} "
              f"({_link('BZ=F', px['BZ=F']['source_url'])}, {_link('CL=F', px['CL=F']['source_url'])}).", ""]
    L += ptable("us_equity", "US equities")
    L += ptable("rates", "US rates futures")
    L += ptable("fx", "USD")

    if S.get("eia"):
        L += ["## US petroleum inventories (EIA weekly)", "",
              "| Series | Week ending | Level | Change | 5y same-week avg change | Surprise (sd) | Source |",
              "|---|---|---:|---:|---:|---:|---|"]
        for r in S["eia"]:
            if "error" in r:
                L.append(f"| error: {r['error']} |||||||"); continue
            L.append(f"| {r['name']} ({r['unit']}) | {r['week_ending']} | {_fmt(r['level'], 1)} | {_fmt(r['change'], 1, sign=True)} | "
                     f"{_fmt(r['seasonal_mean_change'], 1, sign=True)} | {_fmt(r['surprise_z'], 1)} | {_link('EIA', r['source_url'])} |")
        L += [""]

    if S.get("cftc"):
        L += ["## Positioning (CFTC, managed money)", "",
              "| Market | Report date | Net % of OI | Net contracts | 3y percentile | w/w change (pp) | Source |",
              "|---|---|---:|---:|---:|---:|---|"]
        for r in S["cftc"]:
            if "error" in r:
                L.append(f"| error: {r['error']} |||||||"); continue
            L.append(f"| {r['name']} | {r['date']} | {_fmt(r['mm_net_pct_oi'], 1)} | {_fmt(r['mm_net_contracts'], 0)} | "
                     f"{_fmt(r['pct_3y'], 0)} | {_fmt(r['wow_change_pp'], 1, sign=True)} | {_link('CFTC', r['source_url'])} |")
        L += [""]

    if S.get("fred") or S.get("bcb"):
        L += ["## US rates, credit and macro", "", "| Series | Date | Last | Change | Source |", "|---|---|---:|---:|---|"]
        for r in S.get("fred", []):
            if "error" in r:
                continue
            L.append(f"| {r['name']} | {r['date']} | {_fmt(r['last'])} | {_fmt(r['change'], 1, sign=True)} {r['change_unit']} | {_link('FRED', r['source_url'])} |")
        for r in S.get("bcb", []):
            if "error" in r:
                continue
            ch = f"{_fmt(r.get('change'), 2, sign=True)} w/w" if r.get("change") is not None else (f"prev {_fmt(r.get('previous'))}" if r.get("previous") is not None else "")
            L.append(f"| {r['name']} | {r['date']} | {_fmt(r['last'])} | {ch} | {_link('BCB', r['source_url'])} |")
        L += [""]

    L += ["## Central-bank and policy text (last 36 hours)", ""]
    hit = [r for r in S.get("cbtext", []) if r["keywords"]]
    other = [r for r in S.get("cbtext", []) if not r["keywords"]]
    for r in hit:
        L.append(f"- **{r['source'].upper()}** {r['published_utc'][:16].replace('T', ' ')} UTC: {_link(r['title'], r['url'])} — matched: {', '.join(r['keywords'])}")
    if not hit:
        L.append("No new policy items.")
    if other:
        by = {}
        for r in other:
            by[r["source"].upper()] = by.get(r["source"].upper(), 0) + 1
        L.append(f"- Also published, no policy keywords: " + ", ".join(f"{k} {v}" for k, v in by.items()) + " (titles in facts.json).")
    L += [""]

    L += ["## Read-through inputs", "", "Figures above that bear on each name (the note explains the link; this pack does not).", ""]
    allrows = {**px, **{r["id"]: r for r in S.get("fred", []) if "id" in r}, **{r["id"]: r for r in S.get("bcb", []) if "id" in r}}
    for tgt, ids in READ_THROUGH.items():
        have = [i for i in ids if i in allrows]
        L.append(f"- **{tgt}:** " + (", ".join(have) if have else "no inputs available today"))
    L += [""]

    L += ["## Data health", ""]
    fs = S.get("fetch_status", [])
    if fs:
        L += [f"- fetch:{r['source']} — {r['status']}" + (f" ({'; '.join(r['errors'])[:300]})" if r["errors"] else "") for r in fs]
    if S.get("stale"):
        L += [f"- stale: {r['name']} ({r['series_id']}), last {r['last']}, {r['age_days']} days old" for r in S["stale"][:25]]
    if S.get("missing"):
        L.append("- no usable history (under 20 points) for: " + ", ".join(S["missing"]))
    if not fs and not S.get("stale") and not S.get("missing"):
        L.append("- No fetch log yet.")
    L += ["- Known gaps: front-month prices only (no full curves); no iron ore price; no shipping or weather feeds yet.", ""]
    return "\n".join(L)
