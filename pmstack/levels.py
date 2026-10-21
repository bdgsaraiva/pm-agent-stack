"""Market levels table for the morning note (v5, Bernardo 20 Oct 2026 evening): code picks the rows (always-shown
markets, plus "relevant" ones only on a move of 1.5 sd or more, or when in today's alerts) so the note copies a
table instead of choosing. Config: config/levels.yaml. Every figure is from the prices, FRED or JGB series."""
from __future__ import annotations

import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]


def cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "levels.yaml").read_text(encoding="utf-8"))


def _num(x):
    try:
        x = float(x)
        return None if math.isnan(x) else x
    except (TypeError, ValueError):
        return None


def _yield_row(obs: pd.DataFrame, source: str, sid: str, asof: date) -> dict | None:
    """Daily yield series stored in obs (e.g. JGBs): last, bp change, sd of the bp change over 60 days."""
    if obs is None or obs.empty:
        return None
    s = obs[(obs.source == source) & (obs.series_id == sid)].sort_values("date")
    s = s[pd.to_datetime(s.date).dt.date <= asof]
    if len(s) < 2:
        return None
    v = s.value.to_numpy(dtype=float)
    d = np.diff(v[-61:]) * 100
    z = d[-1] / d[:-1].std(ddof=1) if len(d) > 20 and d[:-1].std(ddof=1) > 0 else float("nan")
    return {"last": _num(v[-1]), "date": str(pd.Timestamp(s.date.iloc[-1]).date()), "change": _num(d[-1]),
            "change_unit": "bp", "z1": _num(z), "source_url": s.source_url.iloc[-1]}


def build(prices: list[dict], fred: list[dict], obs: pd.DataFrame, alerts: list[dict], asof: date,
          C: dict | None = None) -> tuple[dict, list[dict]]:
    C = C or cfg()
    thr = float(C.get("relevant_sd", 1.5))
    px = {r["id"]: r for r in prices or [] if "id" in r}
    fr = {r["id"]: r for r in fred or [] if "id" in r}
    alert_ids = {a.get("id") for a in alerts or [] if not a.get("no_longer_firing")}
    rolls = {}
    for rc in C.get("roll_check") or []:
        a, b = px.get(rc["id"]), px.get(rc["sister"])
        if a and b and a.get("live_pct") is not None and b.get("live_pct") is not None \
                and abs(a["live_pct"] - b["live_pct"]) >= float(rc["gap_pct"]):
            rolls[rc["id"]] = (f"possible contract roll: live move {a['live_pct']:+.1f}% vs {b['name']} "
                               f"{b['live_pct']:+.1f}%; not read as a move")
    groups, hidden, missing = [], [], []
    for g in C["groups"]:
        rows = []
        for spec in g["rows"]:
            sid, src = spec["id"], spec.get("source", "prices")
            if src == "prices":
                r = px.get(sid)
                row = r and {"last": r.get("last"), "date": r.get("date"), "change": r.get("ret1_pct"), "change_unit": "%",
                             "z1": r.get("z1"), "live": r.get("live"), "live_pct": r.get("live_pct"),
                             "live_z": r.get("live_z"), "source_url": r.get("source_url"), "label": r.get("name")}
            elif src == "fred":
                r = fr.get(sid)
                row = r and {"last": r.get("last"), "date": r.get("date"), "change": r.get("change"),
                             "change_unit": r.get("change_unit"), "z1": r.get("z1"), "source_url": r.get("source_url")}
            else:
                row = _yield_row(obs, src, sid, asof)
            if not row:
                missing.append(spec.get("label", sid))
                continue
            row = {"id": sid, "label": spec.get("label") or row.get("label") or sid, **{k: v for k, v in row.items() if k != "label"}}
            zs = [abs(z) for z in (row.get("z1"), row.get("live_z")) if _num(z) is not None]
            big = max(zs) if zs else 0.0
            why = "always" if spec["show"] == "always" else (
                "alert" if sid in alert_ids else f"move {big:.1f} sd" if big >= thr else None)
            if spec["show"] == "relevant" and sid in alert_ids and big >= thr:
                why = f"alert; move {big:.1f} sd"
            if why is None:
                hidden.append(row["label"])
                continue
            row["shown_because"] = why
            row["note"] = rolls.get(sid)
            rows.append(row)
        if rows:
            groups.append({"name": g["name"], "rows": rows})
    return {"groups": groups, "hidden_quiet": hidden, "missing": missing, "relevant_sd": thr,
            "caption": (f"Rows marked 'relevant' in config/levels.yaml appear only on a move of {thr} sd or more "
                        "(close-to-close or live) or when in today's alerts. sd = the move over its 60-day volatility.")}, []


def _f(x, nd=2, sign=False):
    x = _num(x)
    if x is None:
        return "-"
    return f"{x:+,.{nd}f}" if sign else f"{x:,.{nd}f}"


def render(V: dict) -> list[str]:
    if not V:
        return []
    if V.get("error"):
        return ["## Market levels", "", f"Not available: {V['error']}", ""]
    L = ["## Market levels (table for the note)", "", V["caption"], "",
         "| Group | Market | Last (date) | Change | sd | Live | Live sd | Shown because | Source |",
         "|---|---|---|---:|---:|---:|---:|---|---|"]
    for g in V["groups"]:
        for r in g["rows"]:
            unit = r.get("change_unit") or "%"
            chg = (_f(r.get("change"), 1, True) + " bp") if unit == "bp" else (_f(r.get("change"), 2, True) + "%")
            live = _f(r.get("live_pct"), 2, True) + "%" if _num(r.get("live_pct")) is not None else "-"
            note = f" ({r['note']})" if r.get("note") else ""
            L.append(f"| {g['name']} | {r['label']}{note} | {_f(r.get('last'), 2)} ({r.get('date')}) | {chg} | "
                     f"{_f(r.get('z1'), 1, True)} | {live} | {_f(r.get('live_z'), 1, True)} | {r['shown_because']} | "
                     f"[source]({r.get('source_url')}) |")
    if V.get("hidden_quiet"):
        L += ["", "Left out (no relevant move today): " + ", ".join(V["hidden_quiet"]) + "."]
    if V.get("missing"):
        L += ["", "No data: " + ", ".join(V["missing"]) + "."]
    return L + [""]
