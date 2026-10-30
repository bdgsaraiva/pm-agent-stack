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

import pandas as pd

from . import events, route, runlog

ROOT = Path(__file__).resolve().parents[1]
BRIEFS = ROOT / "briefs"
PACKS = ROOT / "cards" / "_packs"
STEO_RELEASE_LAG_DAYS = 7
GAP_GROUPS = {"energy": ("balance", "curve", "positioning", "narrative"),
              "metals": ("stocks", "storage", "positioning", "narrative", "long_run"),
              "ags": ("balance", "brazil", "exports", "weather", "events", "positioning", "long_run")}
CFTC_NAMES = {"CL=F": "067651", "BZ=F": "067651", "NG=F": "023651", "RB=F": "111659", "HO=F": "022651",
              "GC=F": "088691", "HG=F": "085692", "ZC=F": "002602", "ZS=F": "005602", "SB=F": "080732"}
# news-feed narratives a specialist reads (matched on the narrative name and id)
NEWS_WORDS = {"energy": ("oil", "crude", "opec", "geopolit", "gas", "supply"),
              "metals": ("copper", "metal", "gold", "china", "alumin", "tariff", "iron"),
              "ags": ("crop", "grain", "corn", "soy", "wheat", "sugar", "weather", "drought", "black sea", "tariff", "food")}


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
        self.extra_gaps: list[str] = []

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
        for row in (S.get("eia") or []) if specialist == "energy" else []:
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
            if any(k in f"{lab} {n.get('id', '')}".lower() for k in NEWS_WORDS.get(specialist, ())):
                b = f"{url_pack}:news.narrative_check[{n.get('id')}]"
                url = ((n.get("stories") or [{}])[0] or {}).get("url") or url_pack
                P.add("narrative", f"News narrative '{lab}' ({n.get('news_verdict')}; stage {n.get('stage')}): headlines today", n.get("headlines_today"), "headlines", pack_day, url, b + ".headlines_today")
                P.add("narrative", f"News narrative '{lab}': prior daily average of headlines", n.get("headlines_prior_avg"), "headlines", pack_day, url, b + ".headlines_prior_avg")
        for a in fp.get("alerts") or []:
            if any(ref in json.dumps(a) for ref in all_refs) or (specialist == "energy" and a.get("id", "").startswith("PET.")):
                P.add("alerts", a["text"], a.get("severity"), "severity", pack_day, a.get("source_url") or url_pack, a.get("ref") or url_pack)
        if specialist == "metals":                             # real yields and the dollar: context for gold
            for row in S.get("fred") or []:
                if row.get("id") in ("DFII10", "DTWEXBGS") and "gold" in coms:
                    P.add("macro", f"{row['name']}", row.get("last"), row.get("unit"), row.get("date"), row["source_url"], f"{url_pack}:fred[{row['id']}].last")
                    P.add("macro", f"{row['name']}, 1-day change", row.get("change"), row.get("change_unit"), row.get("date"), row["source_url"], f"{url_pack}:fred[{row['id']}].change")
        for row in ((S.get("journal") or {}).get("open") or []):
            if row.get("price_ref") in all_refs:
                P.add("journal", f"Open idea {row['id']} ({row.get('book')}): {row['direction']} {row['market']}, R now", row.get("r_now"), "R", row.get("last_date"), f"journal/{row['id'][:4]}/{row['id']}.md", f"{url_pack}:journal.open[{row['id']}].r_now")
    next_events = energy_figures(P, asof, coms, refs, con) if specialist == "energy" else \
        metals_figures(P, asof, coms, con) if specialist == "metals" else \
        ags_figures(P, asof, coms, fp, pack_day, con) if specialist == "ags" else []
    upcoming = [e for e in next_events if e["date"] >= asof.isoformat()]
    out = {"specialist": specialist, "as_of": asof.isoformat(), "fact_pack": pack_day, "question": question,
           "route": r, "commodities": coms, "refs": refs,
           "read": [spec.get("skill")] + ((r or {}).get("files") or [f"{spec['commodities'][k]['knowledge']}/primer.md" for k in coms]),
           "groups": P.groups, "sources": P.sources, "next_events": upcoming,
           "gaps": [g for g in (GAP_GROUPS.get(specialist) or GAP_GROUPS["energy"]) if g not in P.groups] + P.extra_gaps,
           "card_template": {"schema": "state_card/v1", "subject": coms[0] if len(coms) == 1 else specialist,
                             "level": "commodity" if len(coms) == 1 else "complex", "as_of": asof.isoformat(),
                             "author": f"{specialist}/<model id>", "question": question or ""}}
    return out


def energy_figures(P: Pack, asof: date, coms: list[str], refs: list[str], con=None) -> list[dict]:
    """EIA report playbooks, the curve and world figures (S1)."""
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
    return next_events


def _next_weekday(asof: date, wd: int) -> date:
    return asof + timedelta(days=(wd - asof.weekday()) % 7)


def metals_figures(P: Pack, asof: date, coms: list[str], con=None) -> list[dict]:
    """Stocks, the storage test, stock-change and China-day playbooks, long-run real prices and monthly ore (S3), all
    from pmstack.metals as of `asof`. LME via Westmetall and SHFE: personal use only."""
    from . import metals, store
    con = con or store.connect()
    c = metals.cfg()
    st = c["stats"]
    lme, shfe = metals.LME_URL, metals.SHFE_URL
    next_events = []
    for com in [x for x in coms if x in ("copper", "aluminium")]:
        sc = c["storage"]["metals"][com]
        lab = com.title()
        cash = metals._series(con, "lme", sc["cash"], asof)
        m3 = metals._series(con, "lme", sc["m3"], asof)
        if len(m3) > 5:
            d = m3.index[-1]
            P.add("prices", f"LME {lab} 3-month (official)", round(float(m3.iloc[-1]), 1), "USD/t", d, lme, f"lme:{sc['m3']}")
            P.add("prices", f"LME {lab} 3-month, 5-day change", round(100 * (float(m3.iloc[-1]) / float(m3.iloc[-6]) - 1), 2), "%", d, lme, f"lme:{sc['m3']}:ret5")
        # stock playbooks: latest surprise and the code base rate
        for pr in [x for x in c["stocks"] if x["metal"] == com]:
            stocks = metals._series(con, pr["source"], pr["series"], asof)
            if len(stocks) < 60:
                continue
            sur = metals.stock_surprises(stocks, pr["freq"], st, asof)
            lt = None if sur.empty else sur.iloc[-1]
            venue = "SHFE" if pr["source"] == "shfe" else "LME"
            url = shfe if venue == "SHFE" else lme
            frm = f"pmstack.metals.stock_reactions({pr['key']}, as of {asof})"
            P.add("stocks", f"{venue} {lab} stocks", round(float(stocks.iloc[-1]), 0), "t", stocks.index[-1], url, f"{pr['source']}:{pr['series']}")
            if lt is not None:
                P.add("stocks", f"{venue} {lab} stocks, latest {'weekly' if pr['freq'] == 'weekly' else 'daily'} change", round(float(lt["change"]), 0), "t", lt["release"], url, f"{pr['source']}:{pr['series']}:change")
                P.add("stocks", f"{venue} {lab} stock change vs its norm ({'5-year same weeks' if pr['freq'] == 'weekly' else 'trailing 250 days'})", round(float(lt["z"]), 2), "sd", lt["release"], url, f"{pr['source']}:{pr['series']}:z")
            px = metals._prices(con, pr["market"], pr["market_source"], asof, st["start"])
            if px.empty:
                continue
            rets = events.returns(px, st)
            al = metals.align(sur, rets)
            br = events.base_rates(al, rets, st, 1000.0, [tuple(e) for e in st["eras"]]) if not al.empty else {}
            if br.get("events"):
                z = br["slope_per_sd"]
                P.add("events", f"{pr['label']}: report-day return per 1 sd stock surprise ({br['events']} reports since {br['from'][:4]})", z.get("slope"), "%", asof, url, frm + ":slope_per_sd.slope")
                P.add("events", f"{pr['label']}: t-stat of that slope", z.get("t"), "t", asof, url, frm + ":slope_per_sd.t")
                P.add("events", f"{pr['label']}: share of abs(z) >= 1 reports where price moved against the stock surprise", br["sign"].get("hit_rate"), "share", asof, url, frm + ":sign.hit_rate")
                rec = br["eras"].get("since_2015") or {}
                if rec.get("slope_per_sd") is not None and br["from"] < "2015":
                    P.add("events", f"{pr['label']}: report-day return per 1 sd since 2015 ({rec['events']} reports)", rec["slope_per_sd"], "%", asof, url, frm + ":eras.since_2015.slope_per_sd")
                pa = br["placebo"]["day_after"]
                if pa.get("t") is not None and abs(pa["t"]) >= 2:
                    P.add("events", f"{pr['label']}: day-after return per 1 sd of the same surprise (delayed reaction or dating offset)", pa["slope_per_sd"], "%", asof, url, frm + ":placebo.day_after.slope_per_sd")
        # the storage test
        sg = metals.storage(com, asof, con, c)
        if sg.get("status") == "ok":
            n, f = sg["now"], sg["fits"]["spread_pct"]
            frm = f"pmstack.metals.storage({com}, as of {asof})"
            d = n["date"]
            P.add("storage", f"LME {lab} cash minus 3-month, % of 3-month (raw; positive = backwardation)", n["raw_spread_pct"], "%", d, lme, frm + ":now.raw_spread_pct")
            P.add("storage", f"US 3-month T-bill rate used for the carry adjustment", n["rate_pct"], "%", d, sg["sources"]["rate"], frm + ":now.rate_pct")
            P.add("storage", f"LME {lab} spread net of interest (raw spread + T-bill x 91/360; positive = backwardation)", n["spread_pct"], "%", d, lme, frm + ":now.spread_pct")
            P.add("storage", f"LME {lab} spread net of interest, percentile of weekly history since {sg['from'][:4]}", n["spread_pctile"], "pctile", d, lme, frm + ":now.spread_pctile")
            P.add("storage", f"Visible {lab} stocks (LME + SHFE)", n["visible_stock_t"], "t", d, shfe, frm + ":now.visible_stock_t")
            P.add("storage", f"Visible {lab} stocks, percentile since {sg['from'][:4]}", n["visible_stock_pctile"], "pctile", d, shfe, frm + ":now.visible_stock_pctile")
            if (sg.get("shfe_vs_5y") or {}).get("vs_avg_pct") is not None:
                P.add("storage", f"SHFE {lab} stocks vs the 5-year same-week average", sg["shfe_vs_5y"]["vs_avg_pct"], "%", d, shfe, frm + ":shfe_vs_5y.vs_avg_pct")
            sl = f["blocks"][-1] if n["implied_from"] == "latest_block" else {"slope": f["slope_per_log_stock"], "t": f["t"]}
            which = "latest block" if n["implied_from"] == "latest_block" else "full sample"
            P.add("storage", f"{lab} storage fit ({which}, net-of-interest spread): change per 1 log unit of visible stocks", sl["slope"], "pp", asof, lme, frm + ":fits.spread_pct.slope")
            P.add("storage", f"{lab} storage fit: t-stat of that slope (Newey-West)", sl["t"], "t", asof, lme, frm + ":fits.spread_pct.t")
            if n["inventory_implied_spread_pct"] is not None:       # suppressed when the fit is weak (review S3)
                win = n.get("implied_fit_window") or [None, None]
                P.add("storage", f"Inventory-implied {lab} spread net of interest (fit {str(win[0])[:7]} to {str(win[1])[:7]}, today out of sample)", n["inventory_implied_spread_pct"], "%", d, lme, frm + ":now.inventory_implied_spread_pct")
                P.add("storage", f"{lab} spread net of interest minus the inventory-implied spread", n["spread_minus_implied_pp"], "pp", d, lme, frm + ":now.spread_minus_implied_pp")
                P.add("storage", f"{lab} gap vs implied: percentile of the fit's own residuals", n["gap_pctile_vs_fit_residuals"], "pctile", d, lme, frm + ":now.gap_pctile_vs_fit_residuals")
        # China data days
        for key, spec in c["china_days"].items():
            mk = next((m for m in spec["markets"] if m["metal"] == com), None)
            if not mk:
                continue
            px = metals._prices(con, mk["market"], mk["source"], asof, st["start"])
            if px.empty:
                continue
            days = metals.pmi_dates(spec, asof)
            dv = metals.day_vol(events.returns(px, st), days, st)
            if dv.get("ratio") is not None:
                P.add("events", f"{mk['label']}: sd of returns on {spec['name']} days / other days ({dv['events']} releases since {dv['from'][:4]})", dv["ratio"], "ratio", asof, spec["url"], f"pmstack.metals.day_vol({key}, {com}, as of {asof}):ratio")
    for key, spec in c["china_days"].items():
        nxt = [d for d in metals.pmi_dates({**spec, "from": asof.replace(day=1).isoformat()}, asof + timedelta(days=40)) if d >= asof]
        if nxt and set(coms) & {"copper", "aluminium"}:
            next_events.append({"date": nxt[0].isoformat(), "event": spec["name"], "playbook": "knowledge/metals/copper/events.md"})
    if set(coms) & {"copper", "aluminium", "gold"}:
        fri = _next_weekday(asof + timedelta(days=1), 4)      # a Friday as-of date already has that day's reports
        next_events.append({"date": fri.isoformat(), "event": "SHFE weekly stocks (Beijing afternoon)", "playbook": "knowledge/metals/copper/events.md"})
        next_events.append({"date": fri.isoformat(), "event": "CFTC Commitments of Traders", "playbook": "knowledge/metals/copper/primer.md"})
    if "copper" in coms:                                   # COMEX vs LME (tariff premium), config/spreads.yaml
        sp = metals._series(con, "spread", "spread:cu_comex_lme_dec26", asof)
        if len(sp):
            P.add("prices", "COMEX Dec-26 over LME Dec-26 copper premium", round(float(sp.iloc[-1]) - 100, 2), "%", sp.index[-1], "config/spreads.yaml", "spread:cu_comex_lme_dec26")
    if "gold" in coms:
        gv = metals._series(con, "fred", "GVZCLS", asof)
        if len(gv):
            P.add("macro", "Gold implied vol (GVZ, CBOE via FRED)", round(float(gv.iloc[-1]), 2), "index", gv.index[-1], "https://fred.stlouisfed.org/series/GVZCLS", "fred:GVZCLS")
        au = metals._series(con, "shfe", "shfe:au_warrants", asof)
        if len(au) > 4:
            P.add("stocks", "SHFE gold on warrant", round(float(au.iloc[-1]), 0), "kg", au.index[-1], shfe, "shfe:shfe:au_warrants")
            P.add("stocks", "SHFE gold on warrant, 4-week change", round(float(au.iloc[-1] - au.iloc[-5]), 0), "kg", au.index[-1], shfe, "shfe:shfe:au_warrants:chg4")
    if "iron_ore" in coms:                                 # monthly IMF price, used ~10 days after the month
        io = metals._series(con, "fred", "PIORECRUSDM", asof)
        io = io[[date(d.year + (d.month == 12), d.month % 12 + 1, 1) + timedelta(days=10) <= asof for d in io.index]]
        if len(io) > 13:
            d = io.index[-1]
            url = "https://fred.stlouisfed.org/series/PIORECRUSDM"
            P.add("prices", f"Iron ore, IMF monthly average, {str(d)[:7]}", round(float(io.iloc[-1]), 2), "USD/dmt", d, url, "fred:PIORECRUSDM")
            P.add("prices", f"Iron ore, {str(d)[:7]} vs the month before", round(100 * (float(io.iloc[-1]) / float(io.iloc[-2]) - 1), 1), "%", d, url, "fred:PIORECRUSDM:mom")
            P.add("prices", f"Iron ore, {str(d)[:7]} vs a year earlier", round(100 * (float(io.iloc[-1]) / float(io.iloc[-13]) - 1), 1), "%", d, url, "fred:PIORECRUSDM:yoy")
    for com in coms:                                       # long-run real prices (World Bank, deflated by US CPI)
        sid = c["longrun"]["metals"].get(com)
        lr = metals.longrun(com, sid, asof, con, c) if sid else {}
        if lr.get("status") == "ok":
            frm = f"pmstack.metals.longrun({com}, as of {asof})"
            d = date.fromisoformat(lr["month"] + "-01")
            lab = com.replace("_", " ").title()
            P.add("long_run", f"{lab} real price ({lr['month']}), percentile since {lr['from'][:4]}", lr["real_pctile_since_1960"], "pctile", d, metals.WB_URL, frm + ":real_pctile_since_1960")
            P.add("long_run", f"{lab} real price vs its trailing 10-year average", lr["vs_trailing_10y_avg_pct"], "%", d, metals.WB_URL, frm + ":vs_trailing_10y_avg_pct")
            P.add("long_run", f"{lab} real price vs its log-linear trend since {lr['from'][:4]} (end-point sensitive)", lr["vs_log_trend_pct"], "%", d, metals.WB_URL, frm + ":vs_log_trend_pct")
    return next_events


def yaml_esr() -> dict:
    import yaml
    return (yaml.safe_load((ROOT / "config" / "sources.d" / "ags.yaml").read_text(encoding="utf-8")).get("fas_esr") or {})["commodities"]


def ags_figures(P: Pack, asof: date, coms: list[str], fp: dict | None, pack_day: str | None, con=None) -> list[dict]:
    """Balances (agent 9's WASDE, PSD and NASS rows from the fact pack), Conab survey vintages, export sales, ENSO and
    drought, report playbooks and long-run real prices (S4), point in time."""
    from . import ags, metals, store
    con = con or store.connect()
    c = ags.cfg()
    st, cx = c["stats"], c["context"]
    names = {"corn": "Corn", "soybeans": "Soybeans", "wheat": "Wheat", "sugar": "Sugar"}
    if fp:                                                 # agent 9's balance rows (WASDE as first published, NASS)
        B, url_pack = fp["sections"].get("balance") or {}, f"briefs/{pack_day}/facts.json"
        for row in B.get("grains") or []:
            if row.get("key") not in coms:
                continue
            k, d, u, src = row["key"], row.get("report_date"), row.get("unit"), row["source_url"]
            b = f"{url_pack}:balance.grains[{k}]"
            lab = f"US {k} {row.get('my')} (WASDE {d})"
            P.add("balance", f"{lab}: ending stocks", row.get("ending_stocks"), u, d, src, b + ".ending_stocks")
            P.add("balance", f"{lab}: stocks-to-use", row.get("sur_pct"), "%", d, src, b + ".sur_pct")
            P.add("balance", f"{lab}: stocks-to-use percentile since 2007/08 ({row.get('sur_hist_n')} years)", row.get("sur_pctile"), "pctile", d, src, b + ".sur_pctile")
            P.add("balance", f"{lab}: ending-stocks revision vs the {row.get('prev_report')} report", row.get("es_change"), u, d, src, b + ".es_change")
            P.add("balance", f"{lab}: ending-stocks revision vs the previous report", row.get("es_change_pct"), "%", d, src, b + ".es_change_pct")
            if row.get("usda_avg_miss") is not None:
                P.add("balance", f"{lab}: USDA's own average miss on ending stocks at this point of the season", row.get("usda_avg_miss"), u, d, src, b + ".usda_avg_miss")
            P.add("balance", f"US {k} {row.get('old_my')} stocks-to-use (old crop)", row.get("old_sur_pct"), "%", d, src, b + ".old_sur_pct")
            w = row.get("world") or {}
            P.add("balance", f"World {k} {w.get('my')} stocks-to-use ({w.get('from')})", w.get("sur_pct"), "%", w.get("date"), w.get("source_url"), b + ".world.sur_pct")
            if w.get("ex_china_sur_pct") is not None:
                P.add("balance", f"World ex China {k} {w.get('my')} stocks-to-use", w.get("ex_china_sur_pct"), "%", w.get("date"), w.get("source_url"), b + ".world.ex_china_sur_pct")
        cp_rel = ags.release_dates(con, c["crop_progress"]["release_series"], asof)
        for row in B.get("condition") or []:
            k = {"Corn": "corn", "Soybeans": "soybeans"}.get(row.get("crop"), "wheat" if "heat" in str(row.get("crop")) else None)
            if k in coms and row.get("released"):
                rd = date.fromisoformat(str(row["released"])[:10])   # agent 9 dates rows at the NASS Monday: use ESMIS
                later = [d for d in cp_rel if rd <= d <= rd + timedelta(days=3)]
                row = {**row, "released": (later[0] if later else rd).isoformat()}
                lab = f"{row['name']} (week to {row.get('week')})"
                P.add("balance", f"{lab}: good + excellent", row.get("good_excellent_pct"), "%", row.get("released"), row["source_url"], f"{url_pack}:balance.condition[{row['name']}].good_excellent_pct")
                P.add("balance", f"{lab}: weekly change", row.get("weekly_change_pp"), "pp", row.get("released"), row["source_url"], f"{url_pack}:balance.condition[{row['name']}].weekly_change_pp")
        for row in B.get("grain_stocks") or []:
            k = str(row.get("market", "")).lower()
            if k in coms:
                lab = f"US {k} stocks, {row.get('reference')} (NASS {row.get('released')})"
                P.add("balance", lab, row.get("level_mbu"), "million bu", row.get("released"), row["source_url"], f"{url_pack}:balance.grain_stocks[{k}].level_mbu")
                P.add("balance", f"{lab} vs the 5-year average", row.get("vs_avg5_pct"), "%", row.get("released"), row["source_url"], f"{url_pack}:balance.grain_stocks[{k}].vs_avg5_pct")
    # Conab: the latest survey published by asof, and its revision vs the previous survey (same crop year)
    cb = con.execute("SELECT series_id, date, value FROM obs WHERE source = 'conab' AND date <= ? ORDER BY date", [asof]).df()
    if len(cb):
        cb["date"] = pd.to_datetime(cb["date"]).dt.date
        cb["crop"] = cb["series_id"].str.split(":").str[1]
        cb["year"] = cb["series_id"].str.split(":").str[3].str.split("@").str[0]
        for com, crop in cx["conab_crops"].items():
            if com not in coms:
                continue
            x = cb[cb["crop"] == crop]
            if x.empty:
                continue
            last = x.iloc[-1]
            same = x[(x["year"] == last["year"]) & (x["date"] < last["date"])]
            url = "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/safras/safra-de-graos/boletim-da-safra-de-graos"
            lab = f"Conab Brazil {com} {last['year'].replace('-', '/')} production (survey of {last['date']})"
            P.add("brazil", lab, round(float(last["value"]) / 1000, 2), "Mt", last["date"], url, f"conab:{last['series_id']}")
            if len(same):
                prev = same.iloc[-1]
                P.add("brazil", f"Conab Brazil {com} {last['year'].replace('-', '/')}: revision vs the {prev['date']} survey", round((float(last["value"]) - float(prev["value"])) / 1000, 2), "Mt", last["date"], url, f"conab:{last['series_id']}-{prev['series_id'].split('@')[1]}")
            if com == "corn":
                x2 = cb[(cb["crop"] == "milho_2a") & (cb["date"] == last["date"])]
                if len(x2):
                    P.add("brazil", f"Conab Brazil second-crop corn (safrinha) {last['year'].replace('-', '/')} (survey of {last['date']})", round(float(x2['value'].iloc[0]) / 1000, 2), "Mt", last["date"], url, f"conab:{x2['series_id'].iloc[0]}")
    # export sales: total commitments vs the same week of earlier market years, used from release (week end + 8 days)
    for com in [x for x in coms if x in ("corn", "soybeans", "wheat")]:
        es = con.execute("SELECT series_id, date, value FROM obs WHERE source = 'fas_esr' AND series_id LIKE ? AND date <= ? ORDER BY date",
                         [f"fas_esr:{com}:%", asof - timedelta(days=int(cx["esr_lag_days"]))]).df()
        if es.empty:
            continue
        es["date"] = pd.to_datetime(es["date"]).dt.date
        es["field"] = es["series_id"].str.split(":").str[2]
        es["my"] = es["series_id"].str.split(":").str[3].str[2:].astype(int)
        tc = es[es["field"] == "total_commitment"]
        cur_my = int(tc["my"].max())
        cur = tc[tc["my"] == cur_my].sort_values("date")
        if cur.empty:
            continue
        last = cur.iloc[-1]
        start_m = int(next(v["my_start_month"] for k, v in yaml_esr().items() if k == com))
        url = "https://apps.fas.usda.gov/esrquery/"
        lab = f"US {com} export commitments MY{cur_my - 1}/{str(cur_my)[2:]} (week to {last['date']})"
        P.add("exports", lab, round(float(last["value"]) / 1e6, 2), "Mt", last["date"], url, f"fas_esr:{com}:total_commitment:MY{cur_my}")
        prior = []
        off = (last["date"] - date(cur_my - 1, start_m, 1)).days            # days into the market year
        for my in range(cur_my - 5, cur_my):
            p_ = tc[tc["my"] == my].sort_values("date")
            if p_.empty:
                continue
            target = date(my - 1, start_m, 1) + timedelta(days=off)
            gap = p_["date"].map(lambda d: abs((d - target).days))
            if gap.min() <= 3:                                          # the same week of that market year
                prior.append(float(p_.loc[gap.idxmin(), "value"]))
        if prior:
            P.add("exports", f"{lab} vs the same week of the prior {len(prior)} market years (average)", round(100 * (float(last['value']) / (sum(prior) / len(prior)) - 1), 1), "%", last["date"], url, f"fas_esr:{com}:total_commitment:vs_prior")
        ns = es[(es["field"] == "net_sales") & (es["my"] == cur_my)].sort_values("date")
        if len(ns):
            P.add("exports", f"US {com} weekly net sales, current market year (week to {ns['date'].iloc[-1]})", round(float(ns["value"].iloc[-1]) / 1000, 1), "kt", ns["date"].iloc[-1], url, f"fas_esr:{com}:net_sales:MY{cur_my}")
    # ENSO and drought (context)
    oni = metals._series(con, "noaa", "noaa:oni", asof)
    oni = oni[[date(d.year + (d.month == 12), d.month % 12 + 1, 1) + timedelta(days=int(cx["oni_lag_days"])) <= asof for d in oni.index]]
    if len(oni) > 5:
        v = float(oni.iloc[-1])
        side = 1 if v >= 0.5 else -1 if v <= -0.5 else 0
        run = 0
        for x in reversed(oni.to_list()):                  # consecutive overlapping seasons past the threshold
            if side and ((side > 0 and x >= 0.5) or (side < 0 and x <= -0.5)):
                run += 1
            else:
                break
        phase = ("neutral (within 0.5 °C)" if not side else
                 f"{'El Niño' if side > 0 else 'La Niña'} side for {run} consecutive seasons; CPC calls an episode at 5")
        oni_url = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
        P.add("weather", f"Oceanic Niño Index, season ending {str(oni.index[-1])[:7]} ({phase})", round(v, 2), "degC", oni.index[-1], oni_url, "noaa:oni")
        if side:
            P.add("weather", "Consecutive seasons with ONI past ±0.5 °C", run, "seasons", oni.index[-1], oni_url, "noaa:oni:run")
    dm = metals._series(con, "usdm", "usdm:conus:d1", asof - timedelta(days=int(cx["usdm_lag_days"])))
    if len(dm) > 60:
        d0 = dm.index[-1]
        yr = dm[dm.index <= date(d0.year - 1, d0.month, d0.day)]
        P.add("weather", f"US area in drought (D1-D4), map of {d0}", round(float(dm.iloc[-1]), 1), "%", d0, "https://droughtmonitor.unl.edu/", "usdm:conus:d1")
        if len(yr):
            P.add("weather", "US area in drought a year earlier", round(float(yr.iloc[-1]), 1), "%", yr.index[-1], "https://droughtmonitor.unl.edu/", "usdm:conus:d1:yoy")
    # playbooks (code base rates, as of asof)
    out = ags.run(asof, con)
    for rkey, rp in out["reports"].items():
        for com in coms:
            r = rp["markets"].get(com) or {}
            loc = r.get("local") or {}
            if loc.get("ratio") is not None:
                P.add("events", f"{r['label']}: volatility on {rp['name']} days vs the 10 days either side ({loc['events']} releases since {r['from'][:4]})", loc["ratio"], "ratio", asof, rp["url"], f"pmstack.ags.report_days({rkey}, {com}, as of {asof}):local.ratio")
                P.add("events", f"{r['label']}: paired t-stat of that ratio", loc.get("t_paired"), "t", asof, rp["url"], f"pmstack.ags.report_days({rkey}, {com}, as of {asof}):local.t_paired")
            rv = r.get("revision") or {}
            if rv.get("slope_per_sd") is not None:
                P.add("events", f"{r['label']}: WASDE-day return per 1 sd of the US ending-stocks revision ({rv['n']} reports since {rv['from'][:4]}; no consensus, weak proxy)", rv["slope_per_sd"], "%", asof, rp["url"], f"pmstack.ags.report_days(wasde, {com}, as of {asof}):revision.slope_per_sd")
                P.add("events", f"{r['label']}: t-stat of that slope", rv.get("t"), "t", asof, rp["url"], f"pmstack.ags.report_days(wasde, {com}, as of {asof}):revision.t")
    for key, r in out["crop_progress"].items():
        com = ags.FOLDER[key]
        if com in coms and r.get("events"):
            z = r["slope_per_sd"]
            P.add("events", f"{r['label']}: next-day return per 1 sd condition surprise ({r['events']} reports since {r['from'][:4]})", z.get("slope"), "%", asof, r["release_url"], f"pmstack.ags.crop_progress({key}, as of {asof}):slope_per_sd.slope")
            P.add("events", f"{r['label']}: t-stat of that slope", z.get("t"), "t", asof, r["release_url"], f"pmstack.ags.crop_progress({key}, as of {asof}):slope_per_sd.t")
            lt = r.get("latest") or {}
            if lt.get("z") is not None:
                P.add("events", f"{key.replace('_', ' ')} condition: weekly change vs its seasonal norm, latest release with a norm ({lt.get('release')})", lt["z"], "sd", lt.get("release"), r["release_url"], f"pmstack.ags.crop_progress({key}, as of {asof}):latest.z")
    # long-run real prices (World Bank, deflated by US CPI)
    mc = metals.cfg()
    for com in coms:
        sid = cx["longrun"].get(com)
        lr = metals.longrun(com, sid, asof, con, mc) if sid else {}
        if lr.get("status") == "ok":
            d = date.fromisoformat(lr["month"] + "-01")
            frm = f"pmstack.metals.longrun({sid}, as of {asof})"
            lab = com.title()
            P.add("long_run", f"{lab} real price ({lr['month']}, World Bank), percentile since {lr['from'][:4]}", lr["real_pctile_since_1960"], "pctile", d, metals.WB_URL, frm + ":real_pctile_since_1960")
            P.add("long_run", f"{lab} real price vs its trailing 10-year average", lr["vs_trailing_10y_avg_pct"], "%", d, metals.WB_URL, frm + ":vs_trailing_10y_avg_pct")
    # next events: USDA's published schedule (ESMIS), Crop Production = the WASDE day
    nxt = []
    for sid, name in (("esmis:crop-production:scheduled", "WASDE and Crop Production"), ("esmis:crop-progress:scheduled", "NASS Crop Progress")):
        sch = con.execute("SELECT min(date) FROM obs WHERE series_id = ? AND date >= ?", [sid, asof]).fetchone()[0]
        if sch:
            nxt.append({"date": str(sch)[:10], "event": name, "playbook": "knowledge/ags/corn/events.md"})
    nxt.append({"date": _next_weekday(asof, 3).isoformat(), "event": "USDA Export Sales", "playbook": "knowledge/ags/corn/primer.md"})
    nxt.append({"date": _next_weekday(asof, 4).isoformat(), "event": "CFTC Commitments of Traders", "playbook": "knowledge/ags/corn/primer.md"})
    if "wheat" in coms:
        P.extra_gaps.append("positioning: no CFTC series for wheat (not in the shared CFTC block)")
    if not any(s_["label"].startswith("US ") and "export commitments" in s_["label"] for s_ in P.sources) and set(coms) & {"corn", "soybeans", "wheat"}:
        P.extra_gaps.append("exports: no export-sales week released by the as-of date")
    return sorted(nxt, key=lambda e: e["date"])


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
        def _avail(r):
            if isinstance(r["fdate"], str):
                return (date.fromisoformat(r["fdate"]) + timedelta(days=STEO_RELEASE_LAG_DAYS)).isoformat()
            m = _re.fullmatch(r"(\d{4})-(\d{2})", str(r["issue"]))        # older workbooks carry no forecast date:
            if not m:                                                     # the last day of the issue month (conservative)
                return None
            import calendar
            y, mo = int(m.group(1)), int(m.group(2))
            return date(y, mo, calendar.monthrange(y, mo)[1]).isoformat()
        st["avail"] = st.apply(_avail, axis=1)
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
