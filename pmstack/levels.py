"""Market levels table for the morning note (v5, Bernardo 20 Oct 2026 evening): code picks the rows (always-shown
markets, plus "relevant" ones only on a move of 1.5 sd or more, or when in today's alerts) so the note copies a
table instead of choosing. Config: config/levels.yaml.

One snapshot (Bernardo, 20 Oct 2026 night): every prices row is the latest Yahoo Finance mark at the data job's fetch
(live for markets still trading, the session close for closed ones), with ONE change vs the previous session's close
in the row's unit (% for prices, vol points for VIX, bp for yields) and that change in sd of its 60-day vol. The
snapshot time is stated once; a row fetched earlier than the snapshot says so. Rows from another source (JGB 10y from
Japan MoF) are the marked exception, at their own date."""
from __future__ import annotations

import math
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
BRT = ZoneInfo("America/Sao_Paulo")
SOURCE_NAMES = {"mof_jgb": "Japan MoF", "oat": "Banque de France"}


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


def _prices_row(r: dict) -> dict:
    """One mark per row: the live price if the market is still trading at the fetch, else its last close."""
    unit = r.get("chg_unit") or "%"
    if _num(r.get("live")) is not None:
        chg = r.get("live_chg") if r.get("live_chg") is not None else r.get("live_pct")
        return {"level": r.get("live"), "mark": "live", "change": chg, "change_unit": unit, "sd": r.get("live_z"),
                "prev_close": r.get("last"), "prev_date": r.get("date"), "pct": r.get("live_pct")}
    chg = r.get("chg1") if r.get("chg1") is not None else r.get("ret1_pct")
    return {"level": r.get("last"), "mark": "close", "mark_date": r.get("date"), "change": chg, "change_unit": unit,
            "sd": r.get("z1"), "prev_close": r.get("prev"), "pct": r.get("ret1_pct")}


def _fetched(r: dict):
    t = r.get("live_fetched_utc") or r.get("fetched_utc")
    return pd.Timestamp(t, tz="UTC") if t else None


def build(prices: list[dict], fred: list[dict], obs: pd.DataFrame, alerts: list[dict], asof: date,
          C: dict | None = None) -> tuple[dict, list[dict]]:
    C = C or cfg()
    thr = float(C.get("relevant_sd", 1.5))
    px = {r["id"]: r for r in prices or [] if "id" in r}
    fr = {r["id"]: r for r in fred or [] if "id" in r}
    alert_ids = {a.get("id") for a in alerts or [] if not a.get("no_longer_firing")}
    wanted = [spec["id"] for g in C["groups"] for spec in g["rows"] if spec.get("source", "prices") == "prices"]
    times = [t for t in (_fetched(px[i]) for i in wanted if i in px) if t is not None]
    snap = max(times) if times else None
    rolls = {}
    for rc in C.get("roll_check") or []:
        a, b = px.get(rc["id"]), px.get(rc["sister"])
        pa, pb = (_prices_row(a)["pct"] if a else None), (_prices_row(b)["pct"] if b else None)
        if _num(pa) is not None and _num(pb) is not None and abs(pa - pb) >= float(rc["gap_pct"]):
            rolls[rc["id"]] = f"possible contract roll: move {pa:+.1f}% vs {b['name']} {pb:+.1f}%; not read as a move"
    groups, hidden, missing = [], [], []
    for g in C["groups"]:
        rows = []
        for spec in g["rows"]:
            sid, src = spec["id"], spec.get("source", "prices")
            notes = []
            if src == "prices":
                r = px.get(sid)
                row = r and {**_prices_row(r), "source": "Yahoo Finance", "source_url": r.get("source_url"),
                             "label": r.get("name")}
                t = r and _fetched(r)
                if row and snap is not None and t is not None and snap - t > pd.Timedelta(minutes=30):
                    notes.append(f"older fetch, {t:%Y-%m-%d %H:%M} UTC")
            elif src == "fred":
                r = fr.get(sid)
                row = r and {"level": r.get("last"), "mark": "close", "mark_date": r.get("date"), "change": r.get("change"),
                             "change_unit": r.get("change_unit"), "sd": r.get("z1"), "source": "FRED",
                             "source_url": r.get("source_url")}
                if row:
                    notes.append(f"FRED, {r.get('date')}; not in the snapshot")
            else:
                y = _yield_row(obs, src, sid, asof)
                row = y and {"level": y["last"], "mark": "close", "mark_date": y["date"], "change": y["change"],
                             "change_unit": "bp", "sd": y["z1"], "source": SOURCE_NAMES.get(src, src),
                             "source_url": y["source_url"]}
                if row:
                    notes.append(f"{row['source']}, close of {y['date']}; not in the snapshot")
            if not row:
                missing.append(spec.get("label", sid))
                continue
            row = {"id": sid, "label": spec.get("label") or row.get("label") or sid,
                   **{k: v for k, v in row.items() if k not in ("label", "pct")}}
            big = abs(row["sd"]) if _num(row.get("sd")) is not None else 0.0
            why = "always" if spec["show"] == "always" else (
                "alert" if sid in alert_ids else f"move {big:.1f} sd" if big >= thr else None)
            if spec["show"] == "relevant" and sid in alert_ids and big >= thr:
                why = f"alert; move {big:.1f} sd"
            if why is None:
                hidden.append(row["label"])
                continue
            if rolls.get(sid):
                notes.append(rolls[sid])
            row["shown_because"] = why
            row["note"] = "; ".join(notes) or None
            rows.append(row)
        if rows:
            groups.append({"name": g["name"], "rows": rows})
    return {"groups": groups, "hidden_quiet": hidden, "missing": missing, "relevant_sd": thr,
            "snapshot_utc": f"{snap:%Y-%m-%d %H:%M}" if snap is not None else None,
            "snapshot_brt": f"{snap.tz_convert(BRT):%Y-%m-%d %H:%M}" if snap is not None else None,
            "caption": ("Level = the latest Yahoo Finance mark at the snapshot: live for markets still trading, the "
                        "session close (its date shown) for closed ones. Change = vs the previous session's close: % for "
                        "prices, vol points for VIX, bp for yields. sd = that change over its 60-day volatility. "
                        f"Rows marked 'relevant' in config/levels.yaml appear only on a move of {thr} sd or more or "
                        "when in today's alerts.")}, []


def _f(x, nd=2, sign=False):
    x = _num(x)
    if x is None:
        return "-"
    return f"{x:+,.{nd}f}" if sign else f"{x:,.{nd}f}"


def _chg(x, unit) -> str:
    if unit == "bp":
        return _f(x, 1, True) + " bp"
    if unit == "pts":
        return _f(x, 2, True) + " pts"
    return _f(x, 2, True) + "%"


def render(V: dict) -> list[str]:
    if not V:
        return []
    if V.get("error"):
        return ["## Market levels", "", f"Not available: {V['error']}", ""]
    snap = (f" - Yahoo Finance snapshot {V['snapshot_utc']} UTC ({V['snapshot_brt'][11:]} BRT)"
            if V.get("snapshot_utc") else "")
    L = [f"## Market levels (table for the note){snap}", "", V["caption"], "",
         "| Group | Market | Level | Mark | Change | sd | Shown because | Source |",
         "|---|---|---:|---|---:|---:|---|---|"]
    for g in V["groups"]:
        for r in g["rows"]:
            note = f" ({r['note']})" if r.get("note") else ""
            mark = "live" if r.get("mark") == "live" else f"close {r.get('mark_date')}"
            L.append(f"| {g['name']} | {r['label']}{note} | {_f(r.get('level'), 2)} | {mark} | "
                     f"{_chg(r.get('change'), r.get('change_unit'))} | {_f(r.get('sd'), 1, True)} | {r['shown_because']} | "
                     f"[{r.get('source') or 'source'}]({r.get('source_url')}) |")
    if V.get("hidden_quiet"):
        L += ["", "Left out (no relevant move today): " + ", ".join(V["hidden_quiet"]) + "."]
    if V.get("missing"):
        L += ["", "No data: " + ", ".join(V["missing"]) + "."]
    return L + [""]
