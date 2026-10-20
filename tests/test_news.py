"""News since the US close (pmstack/news.py, morning note v4): window, stories, tags, narrative check, point in time."""
from datetime import date, datetime, timezone

import pandas as pd

from pmstack import news
from pmstack.adapters import rss

OUTLETS = {"bbg": "Bloomberg", "ft": "FT", "rtr": "Reuters", "cnbc": "CNBC"}
C = {
    "close_utc_hour": 20, "max_per_topic": 6, "top_stories": 8, "same_story_jaccard": 0.34,
    "baseline_days": 7, "min_history_days": 2,
    "tiers": {"Bloomberg": 1, "FT": 1, "Reuters": 1, "CNBC": 2},
    "topics": {"oil": {"name": "Oil", "markets": ["BZ=F"], "keywords": ["oil", "crude", "hormuz"]},
               "equities": {"name": "Equities", "markets": ["ES=F"], "keywords": ["stocks", "chip"]}},
    "narratives": {"hormuz_iran_v1": ["hormuz", "iranian oil"], "ai_trade_v1": ["chip stocks"],
                   "retired_v1": ["anything"]},
}
CONS = {"narratives": [
    {"id": "hormuz_iran_v1", "name": "Hormuz / Iran oil supply", "stage": "fading", "stage_prev": "fading",
     "markets": {"BZ=F": 1}, "burst": {"is_burst": False}},
    {"id": "ai_trade_v1", "name": "AI trade scare", "stage": "steady", "markets": {"ES=F": -1},
     "burst": {"is_burst": True, "ratio_7d_vs_26w": 3.29}},
]}
PRICES = [{"id": "BZ=F", "name": "Brent", "live_pct": -1.2, "z1": -0.9, "ret1_pct": 0.1, "date": "2026-10-19"},
          {"id": "ES=F", "name": "S&P e-mini", "live_pct": 0.4, "z1": 0.5, "date": "2026-10-19"}]


def _txt(rows):
    return pd.DataFrame([{"source": s, "item_id": f"{i}", "title": t, "url": f"https://x/{i}",
                          "published": pd.Timestamp(p, tz="UTC"), "summary": "",
                          "fetched_at": pd.Timestamp(f or p, tz="UTC")} for i, (s, t, p, f) in enumerate(rows)])


def test_window_starts_at_previous_weekday_close():
    s, e = news.window(date(2026, 10, 19), datetime(2026, 10, 19, 9, tzinfo=timezone.utc), 20)   # Monday
    assert s == pd.Timestamp("2026-10-16 20:00", tz="UTC") and e == pd.Timestamp("2026-10-19 09:00", tz="UTC")
    s, e = news.window(date(2026, 10, 14), datetime(2026, 10, 20, 9, tzinfo=timezone.utc), 20)   # backdated
    assert s == pd.Timestamp("2026-10-13 20:00", tz="UTC") and e == pd.Timestamp("2026-10-14 12:00", tz="UTC")


def test_stories_tags_moves_and_narrative_check():
    txt = _txt([
        ("bbg", "Oil Jumps as Tanker Hit Near Hormuz Strait", "2026-10-20 02:00", None),
        ("rtr", "Tanker hit near Strait of Hormuz, oil jumps", "2026-10-20 03:00", None),
        ("cnbc", "Oil jumps after tanker is hit near Hormuz", "2026-10-20 04:00", None),
        ("ft", "Chip stocks slide again in Asia", "2026-10-20 05:00", None),
        ("ft", "Hormuz shipping insurers raise rates", "2026-10-19 10:00", None),       # before the window: history
        ("ft", "Iranian oil exports fall", "2026-10-18 10:00", None),                     # history, another day
        ("bbg", "Hormuz late story", "2026-10-20 06:00", "2026-10-20 11:00"),             # fetched after the build
        ("other", "Oil from an unknown feed", "2026-10-20 05:00", None),                 # not a news feed
    ])
    sec, alerts = news.build(txt, PRICES, CONS, date(2026, 10, 20), datetime(2026, 10, 20, 9, tzinfo=timezone.utc),
                             C=C, outlets=OUTLETS)
    assert alerts == []
    assert sec["n_headlines"] == 4                                      # point in time: the 11:00 fetch is excluded
    lead = sec["top"][0]
    assert lead["n_outlets"] == 3 and lead["lead"]["outlet"] == "Bloomberg"   # three outlets, tier-1 lead
    assert lead["topics"] == ["oil"] and lead["narratives"] == ["hormuz_iran_v1"]
    assert lead["markets"][0]["id"] == "BZ=F" and lead["markets"][0]["live"]
    chk = {c["id"]: c for c in sec["narrative_check"]}
    assert "retired_v1" not in chk                                     # not on the Consensus map: skipped
    h = chk["hormuz_iran_v1"]
    assert h["headlines_today"] == 3 and h["prior_days"] == 2 and h["headlines_prior_avg"] == 1.0
    assert h["price_verdict"] == "price disagrees"                     # Hormuz pushes Brent up; Brent fell
    a = chk["ai_trade_v1"]
    assert a["burst"] and a["price_verdict"] == "price disagrees"     # pushes S&P down; S&P rose
    md = "\n".join(news.render(sec))
    assert "## News since the US close" in md and "### Narrative check" in md and "also Reuters, CNBC" in md


def test_empty_feed_renders_and_strip_suffix():
    sec, _ = news.build(pd.DataFrame(), PRICES, CONS, date(2026, 10, 20), datetime(2026, 10, 20, 9, tzinfo=timezone.utc),
                        C=C, outlets=OUTLETS)
    assert sec["n_headlines"] == 0 and "No headlines in the window" in "\n".join(news.render(sec))
    assert rss._strip_suffix("Oil rises on supply fears - Reuters", "Reuters") == "Oil rises on supply fears"
    assert rss._strip_suffix("Oil rises - and falls", "Reuters") == "Oil rises - and falls"
