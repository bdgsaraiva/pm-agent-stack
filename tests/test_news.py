"""Morning note inputs (v4/v5): news since the US close (pmstack/news.py) and the watching ladder
(pmstack/agenda.py); the market levels table is in tests/test_levels.py. Window, stories, leans, price-move flags, relevance, calendar filters."""
from datetime import date, datetime, timezone

import pandas as pd

from pmstack import agenda, news
from pmstack.adapters import rss

OUTLETS = {"bbg": "Bloomberg", "ft": "FT", "rtr": "Reuters", "cnbc": "CNBC"}
C = {
    "close_utc_hour": 20, "max_per_topic": 6, "top_stories": 8, "same_story_jaccard": 0.34,
    "baseline_days": 7, "min_history_days": 2,
    "tiers": {"Bloomberg": 1, "FT": 1, "Reuters": 1, "CNBC": 2},
    "topics": {"oil": {"name": "Oil", "markets": ["BZ=F"], "keywords": ["oil", "crude", "hormuz", "tanker"]},
               "equities": {"name": "Equities", "markets": ["ES=F"], "keywords": ["stocks", "chip"]}},
    "narratives": {
        "oil_supply": {"name": "Oil and product supply", "markets": {"BZ=F": 1},
                       "keywords": ["tanker", "refinery", "hormuz"], "reinforce": ["hit", "attack"], "fade": ["resume", "reopens"]},
        "ai_trade_v1": {"keywords": ["chip stocks"], "reinforce": ["slide"], "fade": ["rally"]},
        "retired_v1": {"keywords": ["anything"]},                      # neither on the map nor news-only: skipped
    },
    "price_move": {"subjects": ["oil", "stocks", "gold"], "verbs": ["jumps", "rise", "falls", "slide"], "always": ["markets wrap"]},
}
CONS = {"narratives": [
    {"id": "ai_trade_v1", "name": "AI trade scare", "stage": "steady", "markets": {"ES=F": -1},
     "burst": {"is_burst": True, "ratio_7d_vs_26w": 3.29}},
]}
PRICES = [{"id": "BZ=F", "name": "Brent", "live_pct": -1.2, "z1": -0.9, "live_z": -1.6, "ret1_pct": 0.1, "last": 109.5,
           "date": "2026-10-19", "source_url": "https://x/bz"},
          {"id": "ES=F", "name": "S&P e-mini", "live_pct": 0.4, "z1": 0.5, "live_z": 0.5, "ret1_pct": 0.4, "last": 7734.5,
           "date": "2026-10-19", "source_url": "https://x/es"},
          {"id": "NG=F", "name": "Henry Hub", "live_pct": -0.3, "z1": -0.2, "live_z": -0.3, "ret1_pct": -0.2, "last": 3.1,
           "date": "2026-10-19", "source_url": "https://x/ng"},
          {"id": "SI=F", "name": "Silver", "live_pct": 1.9, "z1": 0.4, "live_z": 1.7, "ret1_pct": 0.4, "last": 50.0,
           "date": "2026-10-19", "source_url": "https://x/si"}]


def _txt(rows):
    return pd.DataFrame([{"source": s, "item_id": f"{i}", "title": t, "url": f"https://x/{i}",
                          "published": pd.Timestamp(p, tz="UTC"), "summary": "",
                          "fetched_at": pd.Timestamp(f or p, tz="UTC")} for i, (s, t, p, f) in enumerate(rows)])


def test_window_starts_at_previous_weekday_close():
    s, e = news.window(date(2026, 10, 19), datetime(2026, 10, 19, 9, tzinfo=timezone.utc), 20)   # Monday
    assert s == pd.Timestamp("2026-10-16 20:00", tz="UTC") and e == pd.Timestamp("2026-10-19 09:00", tz="UTC")
    s, e = news.window(date(2026, 10, 14), datetime(2026, 10, 20, 9, tzinfo=timezone.utc), 20)   # backdated
    assert s == pd.Timestamp("2026-10-13 20:00", tz="UTC") and e == pd.Timestamp("2026-10-14 12:00", tz="UTC")


def test_stories_leans_price_moves_and_narrative_check():
    txt = _txt([
        ("bbg", "Tanker Hit Near Hormuz Strait as Attack Widens", "2026-10-20 02:00", None),
        ("rtr", "Tanker hit near Strait of Hormuz, attack widens", "2026-10-20 03:00", None),
        ("cnbc", "Tanker is hit near Hormuz in widening attack", "2026-10-20 04:00", None),
        ("ft", "Refinery restart: Gulf plant to resume runs", "2026-10-20 05:00", None),
        ("ft", "Oil jumps 3% in Asian trade", "2026-10-20 05:30", None),                  # price move only
        ("bbg", "Chip stocks slide again in Asia", "2026-10-20 05:00", None),
        ("ft", "Hormuz shipping insurers raise rates", "2026-10-19 10:00", None),       # before the window: history
        ("ft", "Tanker traffic thins", "2026-10-18 10:00", None),                         # history, another day
        ("bbg", "Hormuz late story", "2026-10-20 06:00", "2026-10-20 11:00"),             # fetched after the build
        ("other", "Oil from an unknown feed", "2026-10-20 05:00", None),                 # not a news feed
    ])
    sec, alerts = news.build(txt, PRICES, CONS, date(2026, 10, 20), datetime(2026, 10, 20, 9, tzinfo=timezone.utc),
                             C=C, outlets=OUTLETS)
    assert alerts == [] and sec["n_headlines"] == 6                     # point in time: the 11:00 fetch is excluded
    lead = sec["top"][0]
    assert lead["n_outlets"] == 3 and lead["lead"]["outlet"] == "Bloomberg"   # earliest tier-1 outlet leads
    assert lead["narratives"] == {"oil_supply": "reinforces"} and lead["markets"][0]["id"] == "BZ=F"
    assert all(not s["price_move"] for s in sec["top"])                # price-move headlines never top stories
    pm = [s for t in sec["topics"].values() for s in t["stories"] if s["price_move"]]
    assert sorted(s["lead"]["title"] for s in pm) == ["Chip stocks slide again in Asia", "Oil jumps 3% in Asian trade"]
    chk = {c["id"]: c for c in sec["narrative_check"]}
    assert "retired_v1" not in chk
    o = chk["oil_supply"]                                               # news-only narrative (no GDELT definition yet)
    assert o["news_only"] and o["stage"].startswith("not on the map")
    assert o["lean_counts"] == {"reinforces": 1, "fades": 1} and o["news_verdict"] == "news mixed"   # oil jumps: no tanker word
    assert o["headlines_today"] == 4 and o["prior_days"] == 2 and o["headlines_prior_avg"] == 1.0
    assert o["price_verdict"] == "price disagrees"                      # pushes Brent up; Brent fell
    a = chk["ai_trade_v1"]
    assert a["burst"] and a["news_verdict"] == "news reinforces" and a["price_verdict"] == "price disagrees"
    md = "\n".join(news.render(sec))
    assert "### Narrative check" in md and "(reinforces) [Tanker Hit" in md and "[price move] [Oil jumps" in md


def test_empty_feed_renders_and_strip_suffix():
    sec, _ = news.build(pd.DataFrame(), PRICES, CONS, date(2026, 10, 20), datetime(2026, 10, 20, 9, tzinfo=timezone.utc),
                        C=C, outlets=OUTLETS)
    assert sec["n_headlines"] == 0 and "No headlines in the window" in "\n".join(news.render(sec))
    assert rss._strip_suffix("Oil rises on supply fears - Reuters", "Reuters") == "Oil rises on supply fears"
    assert rss._strip_suffix("Oil rises - and falls", "Reuters") == "Oil rises - and falls"



def test_mixed_google_news_feed_keeps_each_items_outlet(monkeypatch):
    xml = """<rss><channel>
    <item><title>Iran and US talks continue, reports that a deal is close are wrong - investingLive</title>
      <link>https://n/1</link><pubDate>Tue, 20 Oct 2026 15:23:00 GMT</pubDate>
      <source url="https://investinglive.com">investingLive</source></item>
    <item><title>US, Iran give approval to new proposal, Arab media claim - Mehr News Agency</title>
      <link>https://n/2</link><pubDate>Tue, 20 Oct 2026 14:59:00 GMT</pubDate>
      <source url="https://en.mehrnews.com">Mehr News Agency</source></item>
    <item><title>Oil falls on Iran deal report - Fresh - Outlet</title>
      <link>https://n/3</link><pubDate>Tue, 20 Oct 2026 14:00:00 GMT</pubDate></item>
    </channel></rss>"""
    monkeypatch.setattr(rss.base, "get_text", lambda url, **kw: xml)
    cfg = {"keep_summary": False, "strip_suffix": True, "outlet_alias": {"Mehr News Agency": "Mehr (Iranian semi-official media)"},
           "feeds": [{"id": "gn_iran", "outlet_from_source": True, "url": "u"},
                     {"id": "rtr", "outlet": "Reuters", "url": "u"}]}
    df = rss.fetch(cfg)
    mixed = df[df.source == "gn_iran"].set_index("url")
    assert mixed.loc["https://n/1", "title"] == "Iran and US talks continue, reports that a deal is close are wrong"
    assert mixed.loc["https://n/1", "summary"] == "outlet=investingLive"
    assert mixed.loc["https://n/2", "summary"] == "outlet=Mehr (Iranian semi-official media)"   # state media labelled
    assert mixed.loc["https://n/3", "summary"] == "outlet=Outlet"                                # no <source>: title tail
    assert (df[df.source == "rtr"]["summary"] == "").all()                                       # fixed-outlet feed as before
    t = news._frame(df.assign(fetched_at=pd.Timestamp("2026-10-20 16:00", tz="UTC")), {"gn_iran": "", "rtr": "Reuters"})
    assert set(t[t.source == "gn_iran"]["outlet"]) == {"investingLive", "Mehr (Iranian semi-official media)", "Outlet"}
    assert set(t[t.source == "rtr"]["outlet"]) == {"Reuters"}
    assert news.feeds()["gn_iran_talks"] == "" and news.feeds()["investinglive"] == "investingLive"


def test_agenda_filters_weekly_reports_and_keeps_watchlist_and_speakers():
    def row(title, ts, summ, fetched="2026-10-20 08:00"):
        return {"source": "agenda", "item_id": title + ts, "title": title, "url": "https://x", "summary": summ,
                "published": pd.Timestamp(ts, tz="UTC"), "fetched_at": pd.Timestamp(fetched, tz="UTC")}
    t = pd.DataFrame([
        row("Flash Services PMI", "2026-10-23 13:45", "kind=macro;country=USD;impact=Medium;time=timed;forecast=57.8;previous=58.7"),
        row("Crude Oil Inventories", "2026-10-21 14:30", "kind=macro;country=USD;impact=Medium;time=timed;forecast=;previous="),
        row("FOMC Member Waller Speaks", "2026-10-22 17:00", "kind=macro;country=USD;impact=Low;time=timed;forecast=;previous="),
        row("German Ifo", "2026-10-22 08:00", "kind=macro;country=EUR;impact=Medium;time=timed;forecast=;previous="),
        row("Meta (META) earnings", "2026-10-21 00:00", "kind=earnings;country=US;impact=watchlist;time=after the US close;forecast=$6.54;previous=$7.25"),
        row("Late fetch", "2026-10-21 12:00", "kind=macro;country=USD;impact=High;time=timed;forecast=;previous=", "2026-10-20 12:00"),
    ])
    cal = {"days_ahead": 14, "events": [{"date": "2026-10-21", "title": "Nvidia GTC keynote", "kind": "event", "source": "test"}],
           "macro": {"keep_countries_any_impact_speakers": ["USD"], "keep_high_impact": ["USD", "EUR"],
                     "keep_medium_impact": ["USD"], "speaker_words": ["speaks"], "exclude": ["crude oil inventories"]}}
    sec, _ = agenda.build(t, date(2026, 10, 20), datetime(2026, 10, 20, 9, tzinfo=timezone.utc), C=cal)
    titles = {r["title"]: r for r in sec["rows"]}
    assert set(titles) == {"Flash Services PMI", "FOMC Member Waller Speaks", "Meta (META) earnings", "Nvidia GTC keynote"}
    assert titles["Meta (META) earnings"]["bucket"] == "next session" and titles["Flash Services PMI"]["time_et"] == "09:45"
    assert "Crude Oil Inventories" not in "\n".join(agenda.render(sec))
