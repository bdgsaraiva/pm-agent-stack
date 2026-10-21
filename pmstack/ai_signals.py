"""AI compute-demand signals: the "AI demand signals" section of the fact pack.

Hard data for the AI narrative's three parts (applications, cloud compute, data centres): GPU rental prices
(GetDeploying, Akash), memory spot (DRAMeXchange), tokens routed (OpenRouter), paid business adoption (Ramp AI
Index), US data-centre construction (Census), TSMC monthly revenue and Korean chip exports (Korea Customs).
Per signal: latest value and date, change vs the previous print and vs ~4 weeks / 3 months / 1 year where the
history allows, the source link, and the part it bears on.

Descriptive only: no thresholds and no alerts (none of these has been through the research loop). Point in time:
a figure counts from its date + `lag_days` (config/ai_signals.yaml), so a pack rebuilt for an earlier date never
shows a later release. Evidence and caveats per source: docs/research/ai-demand-signals.md.
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "ai_signals.yaml"
WINDOW_DAYS = {"4w": 28, "3m": 91, "1y": 365}
SOURCE_LABEL = {"getdeploying": "GetDeploying", "akash": "Akash", "dramexchange": "DRAMeXchange",
                "openrouter": "OpenRouter", "ramp": "Ramp", "census_c30": "Census", "tsmc": "TSMC", "kcs": "Korea Customs"}


def cfg() -> dict:
    return yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}


def _change(v: float, v0: float, how: str):
    if v0 is None or v is None:
        return None
    if how == "pp":
        return v - v0
    return None if v0 == 0 else (v / v0 - 1) * 100


def _near(s: pd.DataFrame, target: date, tol: int):
    """The print nearest `target` (either side; `s` holds only prints before the latest), if within `tol` days."""
    if s.empty:
        return None
    gap = s["date"].map(lambda d: abs((d - target).days))
    i = gap.idxmin()
    return s.loc[i] if gap[i] <= tol else None


def signal_row(s: pd.DataFrame, c: dict, asof: date, C: dict) -> dict | None:
    """One signal from its stored series (columns date, value, freq, source, source_url, name)."""
    if s.empty:
        return None
    s = s.sort_values("date")
    lag = int(c.get("lag_days", 0))
    s = s[[d + timedelta(days=lag) <= asof for d in s["date"]]]         # point in time
    if s.empty:
        return None
    s = s.copy()
    if c.get("smooth"):
        s["value"] = s["value"].rolling(int(c["smooth"]), min_periods=int(c["smooth"])).mean()
        s = s.dropna(subset=["value"])
        if s.empty:
            return None
    scale = float(c.get("scale", 1.0))
    s["value"] = s["value"] * scale
    last = s.iloc[-1]
    freq = str(last.get("freq") or "daily")
    tol = int((C.get("tolerance") or {}).get(freq, 6))
    out = {"id": c["id"], "label": c["label"], "part": c["part"], "unit": c.get("unit", ""), "dp": int(c.get("dp", 2)),
           "chg_kind": c.get("chg", "pct"), "value": float(last["value"]), "date": str(last["date"]),
           "name": str(last.get("name") or ""), "freq": freq, "source": str(last.get("source") or ""),
           "source_url": str(last.get("source_url") or ""), "age_days": (asof - last["date"]).days,
           "reads": c.get("reads", ""), "n": int(len(s)), "first": str(s["date"].iloc[0])}
    out["stale"] = out["age_days"] > int((C.get("stale_days") or {}).get(freq, 45)) + lag
    for w in c.get("windows", ["prev"]):
        if w == "prev":
            if len(s) < 2:
                continue
            p = s.iloc[-2]
        else:
            p = _near(s.iloc[:-1], last["date"] - timedelta(days=WINDOW_DAYS[w]), tol)
            if p is None:
                continue
        ch = _change(out["value"], float(p["value"]), out["chg_kind"])
        if ch is not None and not math.isnan(ch):
            out[w] = {"change": round(ch, 2), "from": round(float(p["value"]), out["dp"] + 2), "from_date": str(p["date"]),
                      "from_name": str(p.get("name") or "")}
    return out


def build(obs: pd.DataFrame, asof: date, C: dict | None = None) -> tuple[dict, list]:
    """Section dict for facts.json; no alerts (descriptive only)."""
    C = C or cfg()
    rows, empty = [], []
    by = {k: g for k, g in obs.groupby("series_id")} if obs is not None and not obs.empty else {}
    for c in C.get("signals", []):
        s = by.get(c["id"])
        r = signal_row(s, c, asof, C) if s is not None else None
        if r is None:
            empty.append(c["label"])
        else:
            rows.append(r)
    order = {p: i for i, p in enumerate(C.get("parts", []))}
    rows.sort(key=lambda r: order.get(r["part"], 99))
    return {"asof": str(asof), "rows": rows, "no_data": empty, "not_wired": C.get("not_wired", [])}, []


def _num(x: float, dp: int) -> str:
    return f"{x:,.{dp}f}"


def _val(r: dict) -> str:
    u = r["unit"]
    if u == "%":
        return f"{_num(r['value'], r['dp'])}%"
    if u.startswith("$") and len(u) > 1:
        return f"${_num(r['value'], r['dp'])}{u[1:]}"
    if u == "$":
        return f"${_num(r['value'], r['dp'])}"
    return f"{_num(r['value'], r['dp'])} {u}"


def _chg(r: dict, w: str) -> str:
    x = r.get(w)
    if not x:
        return "n/a"
    ch = x["change"]
    s = f"{ch:+.1f} pp" if r["chg_kind"] == "pp" else f"{ch:+.1f}%"
    if w == "prev":
        when = x["from_date"]
        if r["freq"] == "event" and "," in x["from_name"]:
            when = x["from_name"].split(",", 1)[1].strip()          # the release window, e.g. "1-20 Sep 2026"
        s += f" (from {_num(x['from'], r['dp'])}, {when})"
    return s


def render(sec: dict) -> list[str]:
    L = ["## AI demand signals", "",
         "Hard data for the AI narrative's three parts (descriptive; no thresholds, no alerts). Change vs the previous "
         "print, and vs the print nearest 4 weeks / 3 months / 1 year earlier where the history allows; % change for "
         "prices and amounts, pp for series already in %. Point in time: monthly figures count from their publication lag.", ""]
    if sec.get("error"):
        return L + [f"Not available: {sec['error']}", ""]
    rows = sec.get("rows") or []
    if not rows:
        L.append("No AI demand data stored yet (sources in config/sources.d/ai_signals.yaml).")
    else:
        L += ["| Part | Signal | Latest | Date | vs prev | vs 4w | vs 3m | vs 1y | Source |",
              "|---|---|---:|---|---|---:|---:|---:|---|"]
        for r in rows:
            label = r["label"] + (" (stale)" if r.get("stale") else "")
            src = SOURCE_LABEL.get(r["source"], r["source"])
            L.append(f"| {r['part']} | {label} | {_val(r)} | {r['date']} | {_chg(r, 'prev')} | {_chg(r, '4w')} | "
                     f"{_chg(r, '3m')} | {_chg(r, '1y')} | [{src}]({r['source_url']}) |")
        L += ["", "Reading convention (inference, not measured): "
              + "; ".join(f"{r['label']}: {r['reads']}" for r in rows if r.get("reads") and r["reads"] != "as H100"
                          and not r["reads"].startswith("as ")) + "."]
        L += ["", "Dates: GPU rentals are the week starting that Monday (latest week partial); Akash and DRAMeXchange are "
              "the day of the reading; Ramp, Census and TSMC the reference month (published later); Korea Customs the "
              "release day. GetDeploying and OpenRouter data are CC BY 4.0; Korea Customs KOGL type 1 (attribution); "
              "DRAMeXchange is personal use only (never in a public post)."]
    if sec.get("no_data"):
        L += ["", "No data yet: " + "; ".join(sec["no_data"]) + "."]
    if sec.get("not_wired"):
        L += ["", "Not wired (see docs/research/ai-demand-signals.md): " + "; ".join(sec["not_wired"]) + "."]
    return L + [""]
