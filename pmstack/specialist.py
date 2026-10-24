"""Specialist input packs (fundamentals pillar, agent 12 "Research"; S1 = Energy).

Code computes, the model writes. For a question routed to a specialist (`pmstack route`), code assembles every
figure the specialist may cite into one numbered list (s1, s2...), each with its value, unit, date, link and the
place it came from (fact pack key, events estimate, curve, journal). The specialist (a skill, read-only) writes the
state card's text citing those ids; `pmstack cards save` validates that every number in the text is one of them,
and the number auditor checks the chat answer against the pack. Nothing here is a signal (alerts are not signals).

Point in time: `--date D` uses the fact pack of D (or the latest one before it), events and curves as of D, and
saved cards and knowledge as of D.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import events, route, runlog

ROOT = Path(__file__).resolve().parents[1]
BRIEFS = ROOT / "briefs"
PACKS = ROOT / "cards" / "_packs"
STEO_RELEASE_LAG_DAYS = 7
CFTC_NAMES = {"CL=F": "067651", "BZ=F": "067651", "NG=F": "023651", "RB=F": "111659", "HO=F": "022651"}


def _today() -> date:
    return (datetime.now(timezone.utc) - timedelta(hours=3)).date()


def fact_pack(asof: date, briefs: Path | None = None) -> tuple[dict | None, str | None]:
    briefs = briefs or BRIEFS
    days = sorted(p.name for p in briefs.glob("20*-*-*") if (p / "facts.json").exists() and p.name <= asof.isoformat())
    if not days:
        return None, None
    d = days[-1]
    return json.loads((briefs / d / "facts.json").read_text(encoding="utf-8")), d


class Pack:
    def __init__(self):
        self.sources: list[dict] = []
        self.groups: dict[str, list[str]] = {}

    def add(self, group: str, label: str, value, unit: str | None, day, url: str, frm: str) -> str | None:
        if value is None or url is None:
            return None
        if isinstance(value, float):
            value = round(value, 4)
        sid = f"s{len(self.sources) + 1}"
        self.sources.append({"id": sid, "label": label, "value": value, "unit": unit,
                             "date": str(day)[:10] if day else None, "url": url, "from": frm})
        self.groups.setdefault(group, []).append(sid)
        return sid


def _refs(spec: dict, commodities: list[str] | None) -> list[str]:
    out = []
    for com, c in (spec.get("commodities") or {}).items():
        if not commodities or com in commodities:
            out += c.get("refs") or []
    return list(dict.fromkeys(out))


def build(specialist: str, asof: date | None = None, question: str | None = None, briefs: Path | None = None,
          con=None) -> dict:
    asof = asof or _today()
    c = route.cfg()
    spec = c["specialists"][specialist]
    r = route.route(f"{specialist}: {question}") if question else None
    coms = (r or {}).get("commodities") or list(spec["commodities"])
    refs = _refs(spec, coms)
    all_refs = _refs(spec, None)
    fp, pack_day = fact_pack(asof, briefs)
    P = Pack()
    if fp:
        S = fp["sections"]
        url_pack = f"briefs/{pack_day}/facts.json"
        for row in S.get("prices") or []:
            if row.get("id") in refs:
                P.add("prices", f"{row['name']} close", row.get("last"), "close", row.get("date"), row["source_url"], f"{url_pack}:prices[{row['id']}].last")
                P.add("prices", f"{row['name']} 1-day change", row.get("ret1_pct"), "%", row.get("date"), row["source_url"], f"{url_pack}:prices[{row['id']}].ret1_pct")
                P.add("prices", f"{row['name']} 5-day change", row.get("ret5_pct"), "%", row.get("date"), row["source_url"], f"{url_pack}:prices[{row['id']}].ret5_pct")
        if "BZ=F" in refs:                                     # standing fact: dated Brent far above futures in 2026 (notes/context.md)
            spot = next((x for x in S.get("fred") or [] if x.get("id") == "DCOILBRENTEU"), None)
            fut = next((x for x in S.get("prices") or [] if x.get("id") == "BZ=F"), None)
            if spot and fut:
                P.add("balance", "Dated Brent spot (EIA via FRED)", spot.get("last"), "USD/bbl", spot.get("date"), spot["source_url"], f"{url_pack}:fred[DCOILBRENTEU].last")
        bal = (S.get("balance") or {}).get("oil") or {}
        for row in bal.get("stocks") or []:
            if set(row.get("markets") or []) & set(refs):
                u, lab, d = row.get("unit"), row["label"], row.get("week_ending")
                base = f"{url_pack}:balance.oil.stocks[{row['id']}]"
                P.add("balance", f"{lab} stocks", row.get("level"), u, d, row["source_url"], base + ".level")
                P.add("balance", f"{lab} vs 5-year average", row.get("vs_avg_pct"), "%", d, row["source_url"], base + ".vs_avg_pct")
                P.add("balance", f"{lab} vs 5-year average", row.get("z_sd"), "sd", d, row["source_url"], base + ".z_sd")
                P.add("balance", f"{lab} weekly change", row.get("change"), u, d, row["source_url"], base + ".change")
                P.add("balance", f"{lab} 5-year average change for the week", row.get("avg5_change"), u, d, row["source_url"], base + ".avg5_change")
                if row.get("days_supply") is not None:
                    P.add("balance", f"{lab} days of supply", row.get("days_supply"), "days", d, row["source_url"], base + ".days_supply")
                    P.add("balance", f"{lab} days of supply, 5-year average", row.get("days_supply_avg5"), "days", d, row["source_url"], base + ".days_supply_avg5")
                if (row.get("seasonality") or {}).get("weak") and row.get("vs_avg52w_pct") is not None:
                    P.add("balance", f"{lab} vs trailing 52-week average (weak seasonality)", row.get("vs_avg52w_pct"), "%", d, row["source_url"], base + ".vs_avg52w_pct")
        for row in bal.get("flows") or []:
            if set(row.get("markets") or []) & set(refs):
                d = row.get("week_ending")
                P.add("balance", f"{row['label']} 4-week average", row.get("avg4"), row.get("unit"), d, row["source_url"], f"{url_pack}:balance.oil.flows[{row['id']}].avg4")
                P.add("balance", f"{row['label']} vs 5-year same 4 weeks", row.get("vs_5y_pct"), "%", d, row["source_url"], f"{url_pack}:balance.oil.flows[{row['id']}].vs_5y_pct")
        for row in S.get("eia") or []:
            if row.get("surprise_z") is not None and abs(row["surprise_z"]) >= 1.5:
                P.add("balance", f"{row['name']}: weekly change vs 5-year same-week norm", row.get("surprise_z"), "sd", row.get("week_ending"), row["source_url"], f"{url_pack}:eia[{row['id']}].surprise_z")
        codes = {CFTC_NAMES[x] for x in refs if x in CFTC_NAMES}
        for row in S.get("cftc") or []:
            if row.get("code") in codes:
                b = f"{url_pack}:cftc[{row['code']}]"
                P.add("positioning", f"{row['name']} managed money net, % of open interest", row.get("mm_net_pct_oi"), "%", row.get("date"), row["source_url"], b + ".mm_net_pct_oi")
                P.add("positioning", f"{row['name']} managed money net, 3-year percentile", row.get("pct_3y"), "pctile", row.get("date"), row["source_url"], b + ".pct_3y")
                P.add("positioning", f"{row['name']} managed money, weekly change", row.get("wow_change_pp"), "pp", row.get("date"), row["source_url"], b + ".wow_change_pp")
        cta = (S.get("risk") or {}).get("cta") or {}
        for ref in refs:
            x = cta.get(ref)
            if not x:
                continue
            for h, leg in (x.get("legs") or {}).items():
                P.add("positioning", f"{x['name']} trend {h}-day leg flip level", leg.get("flip_level"), "close", x.get("last_date"), f"https://finance.yahoo.com/quote/{ref}", f"{url_pack}:risk.cta[{ref}].legs[{h}].flip_level")
            P.add("positioning", f"{x['name']} trend state (CTA proxy): {x.get('state')}", x.get("vol_scale"), "vol-target scale", x.get("last_date"), f"https://finance.yahoo.com/quote/{ref}", f"{url_pack}:risk.cta[{ref}].vol_scale")
        cons = S.get("consensus") or {}
        for n in cons.get("narratives") or []:
            if set((n.get("markets") or {}).keys()) & set(all_refs) and n.get("stage") not in ("insufficient coverage", None):
                P.add("narrative", f"Narrative '{n['name']}' ({n['stage']}): share of coverage vs 26 weeks", n.get("ratio_vs_26w"), "x", n.get("data_through"), "https://www.gdeltproject.org/", f"{url_pack}:consensus.narratives[{n['id']}].ratio_vs_26w")
        nc = ((S.get("news") or {}).get("narrative_check") or [])
        for n in nc if isinstance(nc, list) else []:
            lab = n.get("name") or n.get("id") or ""
            if any(k in f"{lab} {n.get('id', '')}".lower() for k in ("oil", "crude", "opec", "geopolit", "gas", "supply")):
                b = f"{url_pack}:news.narrative_check[{n.get('id')}]"
                url = ((n.get("stories") or [{}])[0] or {}).get("url") or url_pack
                P.add("narrative", f"News narrative '{lab}' ({n.get('news_verdict')}; stage {n.get('stage')}): headlines today", n.get("headlines_today"), "headlines", pack_day, url, b + ".headlines_today")
                P.add("narrative", f"News narrative '{lab}': prior daily average of headlines", n.get("headlines_prior_avg"), "headlines", pack_day, url, b + ".headlines_prior_avg")
        for a in fp.get("alerts") or []:
            if any(ref in json.dumps(a) for ref in all_refs) or a.get("id", "").startswith("PET."):
                P.add("alerts", a["text"], a.get("severity"), "severity", pack_day, a.get("source_url") or url_pack, a.get("ref") or url_pack)
        for row in ((S.get("journal") or {}).get("open") or []):
            if row.get("price_ref") in all_refs:
                P.add("journal", f"Open idea {row['id']} ({row.get('book')}): {row['direction']} {row['market']}, R now", row.get("r_now"), "R", row.get("last_date"), f"journal/{row['id'][:4]}/{row['id']}.md", f"{url_pack}:journal.open[{row['id']}].r_now")
    # report playbooks (code base rates, point in time)
    ev = events.run(asof, con=con)
    next_events = []
    for rkey, rep in ev["reports"].items():
        next_events.append({"date": rep["next_release"], "event": rep["name"], "playbook": f"knowledge/energy/*/events.md#{rkey}"})
        for key, row in rep["pairs"].items():
            if row.get("commodity") not in coms or row.get("status") in ("no data", None) or not row.get("events"):
                continue
            src = rep["url"]
            frm = f"knowledge/energy/{row['commodity']}/estimates/{rkey}-{key}.json"
            lt = row.get("latest") or {}
            P.add("events", f"{row['label']}: latest surprise (week to {lt.get('week_ending')})", lt.get("z"), "sd", lt.get("release"), src, frm + ":latest.z")
            P.add("events", f"{row['label']}: release-day return per 1 sd surprise ({row['events']} releases since {row['from'][:4]})", row["slope_per_sd"].get("slope"), "%", ev["asof"], src, frm + ":slope_per_sd.slope")
            P.add("events", f"{row['label']}: t-stat of that slope", row["slope_per_sd"].get("t"), "t", ev["asof"], src, frm + ":slope_per_sd.t")
            P.add("events", f"{row['label']}: share of abs(z) >= 1 releases where price moved against the surprise", row["sign"].get("hit_rate"), "share", ev["asof"], src, frm + ":sign.hit_rate")
            rec = (row.get("eras") or {}).get("since_2015") or {}
            if rec.get("slope_per_sd") is not None:
                tag = " (the base rate: under half the full sample)" if row.get("base_rate_block") == "since_2015" else ""
                P.add("events", f"{row['label']}: release-day return per 1 sd surprise since 2015 ({rec['events']} releases){tag}", rec["slope_per_sd"], "%", ev["asof"], src, frm + ":eras.since_2015.slope_per_sd")
                P.add("events", f"{row['label']}: since 2015, share of abs(z) >= 1 releases where price moved against the surprise", rec.get("hit_rate"), "share", ev["asof"], src, frm + ":eras.since_2015.hit_rate")
            pb = (row.get("placebo") or {}).get("day_before") or {}
            if pb.get("t") is not None and abs(pb["t"]) >= 2:
                P.add("events", f"{row['label']}: day-before return per 1 sd of the coming surprise (API Tuesday report or pre-positioning)", pb.get("slope_per_sd"), "%", ev["asof"], src, frm + ":placebo.day_before.slope_per_sd")
            cp = row.get("comparable") or {}
            if cp.get("up_share") is not None:
                P.add("events", f"{row['label']}: past {cp['side']}s of at least {cp['z_at_least']} sd ({cp['n']} releases): share with a price rise", cp["up_share"], "share", ev["asof"], src, frm + ":comparable.up_share")
                P.add("events", f"{row['label']}: past {cp['side']}s of at least {cp['z_at_least']} sd: median release-day return", cp["median_ret_pct"], "%", ev["asof"], src, frm + ":comparable.median_ret_pct")
    # curve (prices_curve, collected since 24 Oct 2026)
    from .quant import curve
    roots = {"CL=F": "CL", "BZ=F": "BZ", "HO=F": "HO", "RB=F": "RB", "NG=F": "NG"}
    for ref in refs:
        sh = curve.shape(roots[ref], asof, con) if ref in roots else None
        if sh:
            for far in ("m2", "m6", "m12"):
                if sh.get(f"m1_{far}_pct") is not None:
                    P.add("curve", f"{roots[ref]} {sh['m1']} minus {sh[far + '_contract']} ({sh['label'] if far == sh['label_basis'][3:5] else 'spread'})", sh[f"m1_{far}_pct"], "% of M1", sh["date"], sh["source_url"], f"prices_curve:{sh['m1']}-{sh[far + '_contract']}")
    if "crude" in coms:
        world_figures(P, asof, con)
    upcoming = [e for e in next_events if e["date"] >= asof.isoformat()]
    out = {"specialist": specialist, "as_of": asof.isoformat(), "fact_pack": pack_day, "question": question,
           "route": r, "commodities": coms, "refs": refs,
           "read": [spec.get("skill")] + ((r or {}).get("files") or [f"{spec['commodities'][k]['knowledge']}/primer.md" for k in coms]),
           "groups": P.groups, "sources": P.sources, "next_events": upcoming,
           "gaps": [g for g in ("balance", "curve", "positioning", "narrative") if g not in P.groups],
           "card_template": {"schema": "state_card/v1", "subject": coms[0] if len(coms) == 1 else specialist,
                             "level": "commodity" if len(coms) == 1 else "complex", "as_of": asof.isoformat(),
                             "author": f"{specialist}/<model id>", "question": question or ""}}
    return out


def _q(con, sql: str, args: list):
    try:
        return con.execute(sql, args).df()
    except Exception:  # noqa: BLE001  source not fetched yet
        import pandas as pd
        return pd.DataFrame()


def world_figures(P: Pack, asof: date, con=None) -> None:
    """STEO (latest issue published by asof, and its revision vs the previous issue), JODI, ANP Brazil and US rigs, each
    used only from its availability (STEO forecast date; ANP and EIA monthly ~60 / ~31 days after the month)."""
    import re as _re
    from . import store
    con = con or store.connect()
    st = _q(con, "SELECT series_id, name, date, value, source_url FROM obs WHERE source = 'steo'", [])
    if len(st):
        st["issue"] = st["series_id"].str.split("@").str[1]
        st["sid"] = st["series_id"].str.split("@").str[0].str.replace("steo:", "", regex=False)
        st["fdate"] = st["name"].map(lambda n: (_re.search(r"forecast date (\d{4}-\d{2}-\d{2})", n) or [None, None])[1])
        # the sheet's date is when the forecast was completed; EIA publishes it about a week later (review A15)
        st["avail"] = st["fdate"].map(lambda d: (date.fromisoformat(d) + timedelta(days=STEO_RELEASE_LAG_DAYS)).isoformat() if d else None)
        ok = st[st["avail"].notna() & (st["avail"] <= asof.isoformat())]
        issues = sorted(ok["issue"].unique())
        if issues:
            cur, prev = issues[-1], (issues[-2] if len(issues) > 1 else None)
            for sid, lab, unit in (("BREPUUS", "STEO Brent forecast", "USD/bbl"), ("T3_STCHANGE_WORLD", "STEO world inventory net withdrawals (negative = stock build)", "mb/d"),
                                   ("PAPR_WORLD", "STEO world liquids production", "mb/d"), ("PATC_WORLD", "STEO world liquids consumption", "mb/d")):
                a = ok[(ok["issue"] == cur) & (ok["sid"] == sid)].sort_values("date")
                if a.empty:
                    continue
                q = a[(a["date"].astype(str) >= asof.replace(day=1).isoformat())].head(12)
                if q.empty:
                    continue
                v = float(q["value"].mean())
                fd = a["avail"].iloc[0]
                P.add("world", f"{lab}, average of the next 12 months (issue {cur}, EIA's view, not a consensus)", round(v, 2), unit, fd, a["source_url"].iloc[0], f"steo:{sid}@{cur}")
                if prev:
                    b = ok[(ok["issue"] == prev) & (ok["sid"] == sid)]
                    b = b[b["date"].isin(q["date"])]
                    if len(b) == len(q):
                        P.add("world", f"{lab}: revision vs the {prev} issue, same 12 months", round(v - float(b["value"].mean()), 2), unit, fd, a["source_url"].iloc[0], f"steo:{sid}@{cur}-@{prev}")
    lag = {"anp": 60, "eia_rigs": 31, "jodi": 60}          # JODI updates ~48-50 days after month end: margin
    for src, sid, lab, unit in (("anp", "anp:crude_production_kbd", "Brazil crude production (ANP)", "kbd"),
                                ("anp", "anp:sales_m3:diesel", "Brazil diesel sales (ANP)", "m3"),
                                ("eia_rigs", "PET.E_ERTRRO_XR0_NUS_C.M", "US oil rigs (Baker Hughes via EIA)", "rigs"),
                                ("jodi", "jodi:SA:CRUDEOIL:INDPROD", "Saudi crude production (JODI)", "kbd"),
                                ("jodi", "jodi:RU:CRUDEOIL:INDPROD", "Russia crude production (JODI)", "kbd"),
                                ("jodi", "jodi:CN:CRUDEOIL:TOTIMPSB", "China crude imports (JODI)", "kbd")):
        cutoff = asof - timedelta(days=lag[src] + 31)
        d = _q(con, "SELECT date, value, source_url FROM obs WHERE source = ? AND series_id = ? AND date <= ? ORDER BY date", [src, sid, cutoff])
        if d.empty:
            continue
        last = d.iloc[-1]
        rev = " (latest vintage: revised, not as first published)" if src in ("jodi", "anp") else ""
        P.add("world", f"{lab}, {str(last['date'])[:7]}{rev}", round(float(last["value"]), 1), unit, last["date"], last["source_url"], f"{src}:{sid}")
        yr = d[d["date"].astype(str) == (f"{int(str(last['date'])[:4]) - 1}{str(last['date'])[4:10]}")]
        if len(yr) and float(yr["value"].iloc[0]):
            P.add("world", f"{lab}, {str(last['date'])[:7]} vs a year earlier", round(100 * (float(last["value"]) / float(yr["value"].iloc[0]) - 1), 1), "%", last["date"], last["source_url"], f"{src}:{sid}:yoy")


def write(pack: dict, root: Path | None = None) -> Path:
    root = root or PACKS
    root.mkdir(parents=True, exist_ok=True)
    p = root / f"{pack['as_of']}-{pack['specialist']}.json"
    p.write_text(json.dumps(pack, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    return p


def cli(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="pmstack specialist")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pk = sub.add_parser("pack", help="numbered figures a specialist may cite (written to cards/_packs/)")
    pk.add_argument("specialist")
    pk.add_argument("--date")
    pk.add_argument("--question")
    a = ap.parse_args(argv)
    pack = build(a.specialist, date.fromisoformat(a.date) if a.date else None, a.question)
    p = write(pack)
    runlog.log(runlog.new_run_id(), f"specialist:pack:{a.specialist}", "ok", as_of=pack["as_of"], fact_pack=pack["fact_pack"],
               sources=len(pack["sources"]), gaps=pack["gaps"], pack=p.relative_to(ROOT).as_posix())
    print(json.dumps({"pack": p.relative_to(ROOT).as_posix(), "fact_pack": pack["fact_pack"], "sources": len(pack["sources"]),
                      "groups": {k: len(v) for k, v in pack["groups"].items()}, "gaps": pack["gaps"],
                      "next_events": pack["next_events"], "read": pack["read"]}, indent=1))
    return 0
