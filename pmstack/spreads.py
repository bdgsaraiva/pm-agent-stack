"""Relative-value spreads (24 Oct 2026): two-leg ideas priced as one series, so the journal, sizing assistant,
critic, weekly review and risk model handle them like any long or short idea.

Definitions live in config/spreads.yaml. A spread is a ratio index, value = 100 x long leg / short leg in a common
unit (premium % = value - 100); its log return is the two-leg P&L in log terms (long one leg, short the other, equal
notional). Being long the spread is the convention: a journal idea on a spread has direction `relative`, side long.

Series written to the research memory (source `spread`):
  spread:<id>     the spread from the exact legs where both exist; before that, chain-linked on the generic legs'
                  returns (levels are never spliced; the name says from which date the exact legs start)
  rv:<idea id>    the same spread rebased to the idea's own entry on its entry day (first spread close on or after
                  the entry's BRT day), so marks, R and stops are in the idea's units. History before entry is the
                  same series scaled by that one factor (known on the entry day: no look-ahead in R)

Leg alignment: a date is used only when every leg has its own close that day (LME and COMEX holidays differ).
Closing times differ too (LME official prices ~12:30-13:00 London, COMEX settles 13:30 New York): a daily mark is
approximate, which is why the idea is rebased to the PM's own fill.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
BRT = ZoneInfo("America/Sao_Paulo")
SOURCE = "spread"


# ------------------------------------------------------------------ direction helpers (shared by every agent)
def side(e: dict) -> str | None:
    """'long' / 'short' for single-market ideas; 'long' for a relative idea on a defined spread (long the first
    leg, short the second); None for anything else (vol trades, relative ideas without a spread)."""
    d = e.get("direction")
    if d in ("long", "short"):
        return d
    if d == "relative" and (e.get("spread") or {}).get("id"):
        return "long"
    return None


def sign(e: dict) -> int | None:
    s = side(e)
    return 1 if s == "long" else -1 if s == "short" else None


def is_spread(e: dict) -> bool:
    return e.get("direction") == "relative" and bool((e.get("spread") or {}).get("id"))


def rv_ref(entry_id: str) -> str:
    return f"rv:{entry_id}"


def premium(index_value) -> float | None:
    """Premium % of the long leg over the short leg from an index value (100 = parity)."""
    try:
        return round(float(index_value) - 100.0, 4)
    except (TypeError, ValueError):
        return None


def to_index(premium_pct) -> float | None:
    try:
        return round(100.0 + float(premium_pct), 4)
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ config
def config() -> dict:
    p = ROOT / "config" / "spreads.yaml"
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("spreads", {}) if p.exists() else {}


def get(spread_id: str) -> dict:
    cfg = config()
    if spread_id not in cfg:
        raise KeyError(f"unknown spread '{spread_id}'; defined: {', '.join(sorted(cfg)) or 'none'} (config/spreads.yaml)")
    return {"id": spread_id, **cfg[spread_id]}


# ------------------------------------------------------------------ legs
def _wide(obs: pd.DataFrame, ids: list[str]) -> pd.DataFrame:
    o = obs[obs.series_id.isin(ids)]
    if o.empty:
        return pd.DataFrame(columns=ids)
    p = o.pivot_table(index="date", columns="series_id", values="value", aggfunc="last").sort_index()
    p.index = pd.to_datetime(p.index)
    for i in ids:
        if i not in p:
            p[i] = float("nan")
    return p[ids].astype(float)


def _unit(s: pd.Series, leg: dict) -> pd.Series:
    cut = leg.get("cents_if_above")
    if cut is not None:
        s = s.where(s <= float(cut), s / 100.0)
    return s * float(leg.get("factor", 1.0))


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    last = (date(y + (m // 12), m % 12 + 1, 1) - timedelta(days=1)).day
    return date(y, m, min(d.day, last))


def lme_prompt_weight(trade_day: date, prompt: date) -> float | None:
    """Weight on the 3-month price for an LME prompt: 0 at cash (T+2), 1 at 3-month (T+3 calendar months); None when
    the prompt is outside that range (no interpolation, no extrapolation)."""
    cash, m3 = trade_day + timedelta(days=2), add_months(trade_day, 3)
    if not cash <= prompt <= m3:
        return None
    return (prompt - cash).days / max(1, (m3 - cash).days)


def exact_leg(w: pd.DataFrame, leg: dict) -> pd.Series:
    """The leg's exact price (common unit) per date; NaN where it is not available."""
    if leg.get("lme"):
        lm = leg["lme"]
        prompt = date.fromisoformat(str(lm["prompt"]))
        out = []
        for d, cash, m3 in zip(w.index, w[lm["cash"]], w[lm["m3"]]):
            wt = lme_prompt_weight(d.date(), prompt)
            out.append(float("nan") if wt is None or pd.isna(cash) or pd.isna(m3) else cash + wt * (m3 - cash))
        return _unit(pd.Series(out, index=w.index), leg)
    return _unit(w[leg["series"]], leg)


def leg_ids(leg: dict) -> list[str]:
    ids = [leg["lme"]["cash"], leg["lme"]["m3"]] if leg.get("lme") else [leg["series"]]
    return ids + ([leg["generic"]] if leg.get("generic") else [])


def compute(obs: pd.DataFrame, sp: dict) -> tuple[pd.Series, date | None]:
    """The spread index per date and the first date priced on the exact legs (None: generic history only)."""
    ids = list(dict.fromkeys(leg_ids(sp["long"]) + leg_ids(sp["short"])))
    w = _wide(obs, ids)
    if w.empty:
        return pd.Series(dtype=float), None
    exact = 100.0 * exact_leg(w, sp["long"]) / exact_leg(w, sp["short"])
    exact = exact[exact.notna() & (exact > 0)]
    gen = pd.Series(dtype=float)
    if sp["long"].get("generic") and sp["short"].get("generic"):
        gl = _unit(w[sp["long"]["generic"]], sp["long"])
        gs = _unit(w[sp["short"]["generic"]], sp["short"])
        gen = (100.0 * gl / gs).dropna()
        gen = gen[gen > 0]
    if exact.empty:
        return gen, None
    first = exact.index[0]
    back = gen[gen.index < first]
    if len(back) and first in gen.index:
        back = back * exact.iloc[0] / gen.loc[first]          # chain-link: generic returns, exact level
        out = pd.concat([back, exact])
    else:
        out = exact
    return out.sort_index(), first.date()


def entry_day(e: dict) -> date | None:
    ts = e.get("opened_utc") or e.get("created_utc")
    if not ts:
        return None
    t = pd.Timestamp(ts)
    t = t.tz_localize("UTC") if t.tzinfo is None else t
    return t.tz_convert(BRT).date()


def rebase(s: pd.Series, entry_price: float, day: date) -> tuple[pd.Series, date | None, float | None]:
    """The spread scaled so that it equals the idea's entry on the first close on or after its entry day."""
    after = s[s.index >= pd.Timestamp(day)]
    if after.empty or not entry_price:
        return pd.Series(dtype=float), None, None
    base_d, base_v = after.index[0], float(after.iloc[0])
    return s * float(entry_price) / base_v, base_d.date(), base_v


# ------------------------------------------------------------------ the derived source
def frames(obs: pd.DataFrame | None = None, entries: list[dict] | None = None, fetched=None) -> tuple[pd.DataFrame, list[str]]:
    """Every configured spread and every journal idea on one, as research-memory rows."""
    from . import journal, store
    from .adapters import base
    fetched = fetched or base.now_utc()
    if obs is None:
        obs = store.connect().execute("SELECT series_id, date, value FROM obs WHERE source <> ?", [SOURCE]).df()
    obs = obs.copy()
    obs["date"] = pd.to_datetime(obs["date"])
    entries = entries if entries is not None else journal.load_all()
    rows, notes, by_id = [], [], {}
    for sid, sp in config().items():
        sp = {"id": sid, **sp}
        s, first = compute(obs, sp)
        by_id[sid] = s
        if s.empty:
            notes.append(f"{sid}: no prices for its legs yet")
            continue
        name = f"{sp['name']} (index, 100 = parity; exact legs from {first or 'n/a'}, chain-linked before)"
        rows += [{"source": SOURCE, "series_id": f"spread:{sid}", "name": name, "date": d.date(), "value": round(float(v), 6),
                  "unit": "index", "freq": "daily", "source_url": sp["long"].get("url", ""), "fetched_at": fetched}
                 for d, v in s.items()]
    for e in entries:
        if not is_spread(e):
            continue
        sid = e["spread"]["id"]
        s, day, entry = by_id.get(sid), entry_day(e), journal._num(e.get("entry_price"))
        if s is None or s.empty or day is None or entry is None:
            notes.append(f"{e['id']}: spread {sid} not priced yet")
            continue
        rb, bd, bv = rebase(s, entry, day)
        if rb.empty:
            notes.append(f"{e['id']}: no spread close on or after {day} yet")
            continue
        name = (f"{e.get('market') or sid}, rebased to the entry {entry:g} at the {bd} close "
                f"(spread {bv:.4f} = premium {bv - 100:+.2f}%)")
        rows += [{"source": SOURCE, "series_id": rv_ref(e["id"]), "name": name, "date": d.date(), "value": round(float(v), 6),
                  "unit": "index", "freq": "daily", "source_url": e["spread"].get("url") or "", "fetched_at": fetched}
                 for d, v in rb.items()]
    from .store import OBS_COLS
    return pd.DataFrame(rows, columns=OBS_COLS), notes


def build(write: bool = True, extra: list[dict] | None = None) -> dict:
    """Recompute every spread and rv: series and store them (the `spread` source; also run by `journal new`, which
    passes the idea it is about to write as `extra`)."""
    from . import journal, store
    entries = None
    if extra:
        ids = {x["id"] for x in extra}
        entries = [x for x in journal.load_all() if x.get("id") not in ids] + list(extra)
    df, notes = frames(entries=entries)
    n = store.upsert_obs(SOURCE, df) if write and not df.empty else 0
    return {"rows": int(len(df)), "stored": n, "series": sorted(df.series_id.unique().tolist()) if len(df) else [],
            "notes": notes}


def describe(e: dict) -> dict | None:
    """What a relative idea's numbers mean, for cards and pages."""
    if not is_spread(e):
        return None
    sp = e["spread"]
    return {"id": sp["id"], "long": sp.get("long"), "short": sp.get("short"), "quote": sp.get("quote"),
            "entry_premium_pct": premium(e.get("entry_price")),
            "invalidation_premium_pct": premium(e.get("invalidation_price")),
            "target_premium_pct": premium(e.get("target"))}


def cli(argv: list[str]) -> int:
    import argparse
    import json
    p = argparse.ArgumentParser(prog="pmstack spreads", description="Relative-value spreads (config/spreads.yaml)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="configured spreads")
    sub.add_parser("build", help="recompute spread:<id> and rv:<idea> series from the stored legs")
    sh = sub.add_parser("show", help="last values of a spread")
    sh.add_argument("id")
    sh.add_argument("--n", type=int, default=10)
    a = p.parse_args(argv)
    if a.cmd == "list":
        print(json.dumps(config(), indent=1, ensure_ascii=False))
    elif a.cmd == "build":
        print(json.dumps(build(), indent=1))
    else:
        from . import store
        sid = a.id if ":" in a.id else f"spread:{a.id}"
        df = store.connect().execute("SELECT date, value, name FROM obs WHERE series_id = ? ORDER BY date DESC LIMIT ?",
                                     [sid, a.n]).df()
        if df.empty:
            print(f"{sid}: no values stored yet")
        else:
            print(df.assign(premium_pct=df.value - 100).to_string(index=False))
    return 0

