"""Watching ladder for the morning note (v5, Bernardo 20 Oct 2026 evening): watchlist earnings, economic releases,
central-bank decisions and speakers over the next two weeks, plus hand-entered events (config/calendar.yaml).
Weekly reports (CFTC, EIA inventories, jobless claims) are left out. Point in time: only fetches made by the pack's
build time are read, and each event's latest fetch wins."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
ET, BRT = ZoneInfo("America/New_York"), ZoneInfo("America/Sao_Paulo")


def cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "calendar.yaml").read_text(encoding="utf-8"))


def _meta(summary: str) -> dict:
    out = {}
    for part in (summary or "").split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
    return out


def _keep_macro(title: str, m: dict, C: dict) -> bool:
    mc = C.get("macro") or {}
    t = title.lower()
    if any(x in t for x in mc.get("exclude", [])):
        return False
    country, impact = m.get("country"), (m.get("impact") or "").lower()
    speaker = any(w in t for w in mc.get("speaker_words", []))
    if speaker and country in mc.get("keep_countries_any_impact_speakers", []):
        return True
    if impact == "high" and country in mc.get("keep_high_impact", []):
        return True
    return impact == "medium" and country in mc.get("keep_medium_impact", [])


def build(txt: pd.DataFrame, asof: date, now: datetime, C: dict | None = None) -> tuple[dict, list[dict]]:
    C = C or cfg()
    now_ts = pd.Timestamp(now).tz_convert("UTC") if pd.Timestamp(now).tzinfo else pd.Timestamp(now, tz="UTC")
    start_day = asof
    end_day = asof + timedelta(days=int(C.get("days_ahead", 14)))
    rows = []
    t = txt[txt["source"] == "agenda"].copy() if txt is not None and not txt.empty else pd.DataFrame()
    if not t.empty:
        t["published"] = pd.to_datetime(t["published"], utc=True, errors="coerce")
        t["fetched_at"] = pd.to_datetime(t["fetched_at"], utc=True, errors="coerce")
        t = t[t["fetched_at"] <= now_ts]
        t["meta"] = t["summary"].map(_meta)
        t["kind"] = t["meta"].map(lambda m: m.get("kind"))
        t["key"] = t["kind"].astype(str) + "|" + t["title"] + "|" + t["published"].dt.strftime("%Y-%m-%d")
        t = t.sort_values("fetched_at").drop_duplicates("key", keep="last")
        for r in t.itertuples():
            m = r.meta
            if m.get("kind") == "macro" and not _keep_macro(r.title, m, C):
                continue
            et = r.published.tz_convert(ET)
            dated_only = m.get("kind") == "earnings"
            d = r.published.date() if dated_only else et.date()
            if not (start_day <= d <= end_day):
                continue
            rows.append({"date": str(d), "kind": m.get("kind"), "title": r.title, "url": r.url,
                         "time_et": None if dated_only else et.strftime("%H:%M"),
                         "time_brt": None if dated_only else r.published.tz_convert(BRT).strftime("%H:%M"),
                         "when": m.get("time") if dated_only else None, "country": m.get("country"),
                         "impact": m.get("impact"), "forecast": m.get("forecast") or None, "previous": m.get("previous") or None})
    for e in C.get("events") or []:
        d = date.fromisoformat(str(e["date"]))
        if start_day <= d <= end_day:
            rows.append({"date": str(d), "kind": e.get("kind", "event"), "title": e["title"], "url": e.get("url"),
                         "time_et": e.get("time_et"), "time_brt": None, "when": None, "country": e.get("country"),
                         "impact": "hand-entered", "forecast": None, "previous": None, "source": e.get("source")})
    seen, uniq = set(), []
    for r in rows:                                     # one row per company and day (GOOG and GOOGL are one report)
        k = (r["date"], re.sub(r"\s*\([A-Z.]+\)", "", r["title"]))
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    rows = sorted(uniq, key=lambda r: (r["date"], r["time_et"] or "99:99", r["kind"] or "", r["title"]))

    def bucket(d: str) -> str:
        dd = date.fromisoformat(d)
        if dd == asof:
            return "today"
        if dd == asof + timedelta(days=1) or (asof.weekday() == 4 and dd == asof + timedelta(days=3)):
            return "next session"
        monday_next = asof + timedelta(days=7 - asof.weekday())
        return "this week" if dd < monday_next else "next week" if dd < monday_next + timedelta(days=7) else "later"
    for r in rows:
        r["bucket"] = bucket(r["date"])
    return {"from": str(start_day), "to": str(end_day), "rows": rows,
            "caption": ("Economic releases, central-bank decisions and speakers: Forex Factory calendar (impact as it rates "
                        "it; times ET and BRT). Earnings: Nasdaq calendar, watchlist only. Hand-entered events: "
                        "config/calendar.yaml. Weekly reports (CFTC, EIA, jobless claims) left out.")}, []


def render(A: dict) -> list[str]:
    if not A:
        return []
    if A.get("error"):
        return ["## Calendar", "", f"Not available: {A['error']}", ""]
    L = ["## Calendar (watching ladder)", "", f"{A['from']} to {A['to']}. {A['caption']}", ""]
    if not A["rows"]:
        return L + ["No events in the window (calendar fetch missing or empty).", ""]
    cur = None
    for r in A["rows"]:
        if r["bucket"] != cur:
            cur = r["bucket"]
            L += ["", f"**{cur.capitalize()}**", ""]
        when = (f"{r['time_et']} ET" + (f" / {r['time_brt']} BRT" if r.get("time_brt") else "")) if r.get("time_et") else (r.get("when") or "time not given")
        extra = []
        if r.get("forecast"):
            extra.append(f"forecast {r['forecast']}")
        if r.get("previous"):
            extra.append(f"previous {r['previous']}")
        if r["kind"] == "macro" and r.get("impact"):
            extra.append(f"{r['impact'].lower()} impact")
        src = f"[source]({r['url']})" if r.get("url") else (r.get("source") or "hand-entered")
        L.append(f"- {r['date']} {when}: {r['title']}" + (f" ({r['country']})" if r.get("country") and r["kind"] == "macro" else "")
                 + (f"; {', '.join(extra)}" if extra else "") + f" — {src}")
    return L + [""]
