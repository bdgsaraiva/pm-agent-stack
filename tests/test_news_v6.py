"""Morning note v6 news rules: opinion pieces are not news; AI is one narrative with three parts (pmstack/news.py)."""
from datetime import date, datetime, timezone

import pandas as pd

from pmstack import news

OUTLETS = {"wsj": "WSJ", "rtr": "Reuters"}
C = {"close_utc_hour": 20, "max_per_topic": 6, "top_stories": 8, "same_story_jaccard": 0.34, "baseline_days": 7,
     "min_history_days": 2, "tiers": {"WSJ": 1, "Reuters": 1},
     "topics": {"equities": {"name": "Equities", "markets": ["NQ=F"], "keywords": ["nvidia", "anthropic", "data center"]}},
     "narratives": {
         "ai_applications": {"name": "AI: applications", "group": "AI", "markets": {"NQ=F": 1},
                             "keywords": ["anthropic", "openai"], "reinforce": ["raises"], "fade": ["lawsuit"]},
         "ai_datacenters": {"name": "AI: data centres", "group": "AI", "markets": {"NQ=F": 1},
                            "keywords": ["nvidia", "data center"], "reinforce": ["orders"], "fade": ["delays"]}}}
PRICES = [{"id": "NQ=F", "name": "Nasdaq e-mini", "live_pct": 0.8, "z1": 0.9, "ret1_pct": 0.5, "date": "2026-10-19"}]


def test_opinion_pieces_are_dropped_and_ai_parts_are_grouped():
    rows = [("wsj", "Opinion | Elon Musk Beats Anthropic on Giveaways"), ("rtr", "COMMENTARY: Nvidia's moat is narrower"),
            ("rtr", "Anthropic raises $10 billion"), ("rtr", "Chinese firms place $35 billion of Nvidia chip orders"),
            ("wsj", "Analysis shows data center power demand rising")]
    txt = pd.DataFrame([{"source": s, "item_id": str(i), "title": t, "url": f"https://x/{i}", "summary": "",
                         "published": pd.Timestamp("2026-10-20 03:00", tz="UTC"),
                         "fetched_at": pd.Timestamp("2026-10-20 03:00", tz="UTC")} for i, (s, t) in enumerate(rows)])
    sec, _ = news.build(txt, PRICES, {"narratives": []}, date(2026, 10, 20), datetime(2026, 10, 20, 9, tzinfo=timezone.utc),
                        C=C, outlets=OUTLETS)
    assert sec["n_headlines"] == 3                                   # the two opinion pieces are gone; "Analysis shows" stays
    chk = {c["id"]: c for c in sec["narrative_check"]}
    assert chk["ai_applications"]["group"] == "AI" and chk["ai_applications"]["news_verdict"] == "news reinforces"
    assert chk["ai_datacenters"]["lean_counts"] == {"reinforces": 1, "neutral": 1}
    assert chk["ai_datacenters"]["price_verdict"] == "price agrees"
    assert "**AI: data centres** (part of AI)" in "\n".join(news.render(sec))
