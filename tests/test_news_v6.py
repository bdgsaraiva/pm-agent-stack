"""Morning note v6 news rules: opinion pieces are not news; AI is one narrative with three parts (pmstack/news.py)."""
from datetime import date, datetime, timezone

import pandas as pd

from pmstack import news

OUTLETS = {"wsj": "WSJ", "rtr": "Reuters"}
C = {"start_utc_hour": 20, "max_per_topic": 6, "top_stories": 8, "same_story_jaccard": 0.34, "baseline_days": 7,
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
    assert chk["ai_applications"]["group"] == "AI" and chk["ai_applications"]["news_verdict"] == "news: reinforces"
    assert chk["ai_datacenters"]["lean_counts"] == {"reinforces": 1, "neutral": 1}
    assert chk["ai_datacenters"]["price_verdict"] == "price agrees"
    assert "**AI: data centres** (part of AI)" in "\n".join(news.render(sec))


def test_brazil_fund_watch_keeps_industry_moves_and_drops_lookalikes():
    spec = news.cfg()["watches"]["br_funds"]
    titles = ["Millennium contrata ex-J.P. Morgan para liderar expansão no Brasil",
              "Gávea, de Arminio Fraga, deixa gestão de fundos multimercados e indica Bradesco Asset",
              "Novus transfere fundos para Leto Capital e Occam Brasil",
              "Schonfeld builds Brazil team for global fund",
              "Embraer entrega o primeiro C-390 Millennium à Força Aérea do Uzbequistão",
              "AG Seville Shipyard é a nova gestora do estaleiro de reparação do Porto de Sevilha",
              "APXM11 aprova Vinci Real Estate como nova gestora"]
    txt = pd.DataFrame([{"source": "rtr", "item_id": str(i), "title": t, "url": f"https://x/{i}", "summary": "",
                         "published": pd.Timestamp("2026-10-20 03:00", tz="UTC") - pd.Timedelta(days=i % 2 * 3),
                         "fetched_at": pd.Timestamp("2026-10-20 03:00", tz="UTC")} for i, t in enumerate(titles)])
    fr = news._frame(txt, {"rtr": "Reuters"})
    w = news.watch(fr, spec, pd.Timestamp("2026-10-19 20:00", tz="UTC"), pd.Timestamp("2026-10-20 09:00", tz="UTC"), {}, 0.34)
    kept = {s["lead"]["title"] for s in w["stories"]}
    assert kept == set(titles[:4])
    assert w["n_new"] == 2 and all(s["new"] == (s["lead"]["title"] in (titles[0], titles[2])) for s in w["stories"])


def test_window_covers_the_previous_us_session_and_generic_words_do_not_merge_stories():
    s, e = news.window(date(2026, 10, 21), datetime(2026, 10, 21, 9, tzinfo=timezone.utc), news.cfg()["start_utc_hour"])
    assert s <= pd.Timestamp("2026-10-20 13:00", tz="UTC") < e        # the 20 Oct deal report (13:00 UTC) is in the 21 Oct window
    iran = news.tokens("Iran and US talks continue, reports that a deal is close are wrong")
    mexico = news.tokens("Trump says Mexico and US are close to trade deal")
    assert news.same_story(iran, mexico, 0.34) == 0.0
    a = news.tokens("Trump sued over 50% tariffs on Canada in latest trade challenge")
    b = news.tokens("Trump Administration Sued Over 50% Tariffs on Canadian Products")
    assert news.same_story(a, b, 0.34) > 0


def test_narratives_speak_in_their_own_direction_words():
    spec = news.cfg()["narratives"]
    assert spec["cb_policy"]["labels"] == ["hawkish", "dovish"] and spec["us_economy"]["labels"] == ["strong", "weak"]
    assert spec["oil_supply"]["labels"] == ["shortage", "glut"] and spec["geopolitics"]["labels"] == ["increase", "decrease"]
    assert {spec[k]["labels"][0] for k in ("ai_applications", "ai_cloud", "ai_datacenters")} == {"bullish"}
    assert "natgas_lng_v1" not in spec and "fed_hike_v1" not in spec and "recession_v1" not in spec
    rows = [("rtr", "Fed to skip October but raise rates again in December, economists say"),
            ("rtr", "Fed officials signal more hikes as inflation stays sticky"),
            ("wsj", "US pending home sales plunged to a record low")]
    txt = pd.DataFrame([{"source": s, "item_id": str(i), "title": t, "url": f"https://x/{i}", "summary": "",
                         "published": pd.Timestamp("2026-10-20 14:00", tz="UTC"),
                         "fetched_at": pd.Timestamp("2026-10-20 14:00", tz="UTC")} for i, (s, t) in enumerate(rows)])
    C2 = {**news.cfg(), "narratives": {k: spec[k] for k in ("cb_policy", "us_economy")}}
    sec, _ = news.build(txt, PRICES, {"narratives": []}, date(2026, 10, 21), datetime(2026, 10, 21, 9, tzinfo=timezone.utc),
                        C=C2, outlets=OUTLETS)
    chk = {c["id"]: c for c in sec["narrative_check"]}
    assert chk["cb_policy"]["news_verdict"] == "news: hawkish" and chk["us_economy"]["news_verdict"] == "news: weak"
    md = chr(10).join(news.render(sec))
    assert "(hawkish; Fed) [Fed to skip October" in md and "(weak) [US pending home sales" in md


def test_google_news_falls_back_to_bing(monkeypatch):
    from pmstack.adapters import rss
    bing = """<?xml version="1.0"?><rss version="2.0" xmlns:News="https://www.bing.com/news/search"><channel><item>
      <title>Iran tells Pakistan army chief no talks until demands are met</title>
      <link>http://www.bing.com/news/apiclick.aspx?ref=FexRss&amp;aid=&amp;url=https%3a%2f%2fwww.reuters.com%2fworld%2fx&amp;c=1</link>
      <pubDate>Tue, 20 Oct 2026 18:02:00 GMT</pubDate><News:Source>Reuters on MSN</News:Source></item></channel></rss>"""
    calls = []

    def fake(url, **kw):
        calls.append((url, kw.get("params")))
        if "news.google.com" in url:
            raise RuntimeError("HTTP 503 Sorry")
        return bing
    monkeypatch.setattr(rss.base, "get_text", fake)
    df = rss.fetch({"strip_suffix": True, "keep_summary": False, "feeds": [
        {"id": "gn_iran_talks", "outlet_from_source": True,
         "url": "https://news.google.com/rss/search?q=when:1d+Iran+(talks+OR+deal)&hl=en-US"}]})
    assert [c[0] for c in calls] == ["https://news.google.com/rss/search?q=when:1d+Iran+(talks+OR+deal)&hl=en-US"] * 2 + [rss.BING]
    assert calls[-1][1] == {"q": "Iran (talks OR deal)", "format": "rss", "qft": 'interval="7"'}
    r = df.iloc[0]
    assert r.url == "https://www.reuters.com/world/x" and r.summary == "outlet=Reuters"
