"""Bernardo's direction check (docs/research/narrative-direction-audit/2026-10-21.md, 21 Oct 2026), frozen as a
test: each headline with the direction he read. "off" = not about the narrative, "none" = about it but no direction;
both pass when the code tags nothing or no direction. Fed policy rows are scored as Central bank policy and US fiscal
stress rows as Fiscal stress (his renames the same day). Two rows changed by his later rules the same evening
(SUPERSEDED below): "very" only for surprises against expectations, never a big number by itself; RBA, BoC and
BOE news only when very relevant."""
import pytest

from pmstack import news

ROWS = [
    ('geopolitics', 'UK to deploy jets to defend Saudi Arabia against Houthi attacks', 'none'),
    ('geopolitics', 'Netanyahu made plans to restart Iran strikes earlier this month', 'very increase'),
    ('geopolitics', 'Drone strike on a market in disputed African region of Abyei kills at least 153', 'off'),
    ('geopolitics', 'US envoy Witkoff arrives in St Petersburg for talks with Putin', 'decrease'),
    ('geopolitics', 'Iran tells Pakistan army chief no talks with Washington until demands are met', 'increase'),
    ('geopolitics', 'Hegseth Said to Make Unannounced Visit to Israel for Talks With Netanyahu', 'none'),
    ('geopolitics', 'Finnish president hails progress in talks about ending Russia’s war in Ukraine', 'none'),
    ('geopolitics', 'Rubio welcomes mediation efforts in US-Iran war, reiterates Tehran must never have nuclear weapon', 'none'),
    ('oil_supply', 'UK to deploy jets to defend Saudi Arabia against Houthi attacks', 'off'),
    ('oil_supply', 'Ship attacked near Strait of Hormuz: maritime agency', 'shortage'),
    ('oil_supply', 'Oil Rises Amid Attacks on Vessels in Strait of Hormuz', 'shortage'),
    ('oil_supply', 'Trump Says US Trade Deal With India Is ‘Pretty Close’', 'off'),
    ('oil_supply', 'Red Sea Film Foundation-backed films earn record 12 entries in Oscar race', 'off'),
    ('oil_supply', 'Red Sea container traffic set for full return in Q1 – October 20, 2026 Update', 'off'),
    ('oil_supply', 'IEA: Record tanker rates push up oil costs as Middle East disruptions bite', 'shortage'),
    ('oil_supply', 'Crazy – Attacks, Altered Crude Flows, Unbalanced Fleets Push Tanker Freight Rates to Record Levels', 'none'),
    ('ai_datacenters', 'Japan exports rise 16.7% in September as AI chip demand powers trade', 'bullish'),
    ('ai_datacenters', 'Super Micro expects first-quarter revenue above estimates', 'bullish'),
    ('ai_datacenters', 'EXCLUSIVE: ByteDance, Alibaba, Tencent place over $35 billion worth of Nvidia chip orders', 'very bullish'),
    # SUPERSEDED (was very bearish): a 42% fall is a big number, not by itself a surprise; FT's "profit warning"
    # headline on the same news carries the very (row below), and build() marks a story very when any outlet's does
    ('ai_datacenters', 'Australian AI data centre operator NextDC shares shed 42% on revenue delay, future plans on hold', 'bearish'),
    ('ai_datacenters', 'Nextdc Warns on Profit After Backlash Hits Australia Data Center', 'bearish'),
    ('ai_datacenters', 'Australian data centre group falls 44% on profit warning', 'very bearish'),
    ('ai_datacenters', 'Korean Data Center Firm Elice Jumps by Limit After Debut Slump', 'bullish'),
    ('ai_datacenters', "Trump says companies should pay 'dividend' to communities to make data centers popular", 'off'),
    ('ai_applications', 'ASI Hits $3 Billion Valuation in $325 Million Funding Round', 'none'),
    ('ai_applications', 'OpenAI busca acelerar captação de recursos antes da IPO da Anthropic, diz agência', 'none'),
    ('ai_applications', 'Anthropic IPO draft shows nearly 15-fold revenue jump and $600 billion in compute deals', 'bullish'),
    ('ai_applications', "China says US' DeepSeek ban disregards Xi-Trump consensus", 'none'),
    ('ai_applications', "US judge dismisses Sam Altman's sister's sexual abuse lawsuit", 'off'),
    ('ai_applications', 'Anthropic logged net loss of over $80 billion in first half of 2026', 'bearish'),
    ('ai_applications', "Why Anthropic can't afford to delay its IPO", 'bearish'),
    ('ai_applications', 'OpenAI Says Its Agents Weakened System That Flags AI Misbehavior', 'none'),
    ('cb_policy', 'UK Inflation at 11-Month High Pressures BOE to Hike', 'off'),
    # SUPERSEDED (was hawkish): RBA counts only when very relevant
    ('cb_policy', 'Australian central banker says inflation outlook worse, unsure about November rate hike', 'off'),
    ('cb_policy', 'BOJ to raise rates to 1.50% in December, sticking to quarterly pace: Reuters poll', 'none'),
    ('cb_policy', 'Bank of Israel to pause rate cuts ahead of October 27 election', 'off'),
    ('cb_policy', 'U.K. Inflation Jumps Again on Rising Energy Costs', 'off'),
    ('cb_policy', 'Sterling Hits Near 17-Month High Against Euro on U.K. Rate-Rise Prospects, France Concerns', 'off'),
    ('us_economy', 'US Pending Home Sales Plunged in September to a Record Low', 'weak'),
    ('us_economy', 'U.S. Housing Starts Dropped Again in September', 'weak'),
    ('us_economy', 'US single-family housing starts plunge; building permits hit 3-1/2-year low', 'weak'),
    ('us_economy', 'Eurozone Bond Yields Rise, U.S. Treasury Yields Steady', 'off'),
    ('ai_cloud', 'U.S. Stocks Mixed as Strong Earnings Offset AI Credit Fears', 'none'),
    ('ai_cloud', 'Nscale boss seeks to reassure staff amid AI market fears', 'bullish'),
    ('ai_cloud', "This Janus Henderson fund manager owns CoreWeave debt — here's why he's sticking with it", 'bullish'),
    ('ai_cloud', 'Google Cloud Outage Mostly Resolved After Knocking Out Services', 'none'),
    ('ai_cloud', 'Google Cloud outage in UK eases after impacting digital banks, public sector websites', 'none'),
    ('weak_dollar_v1', 'WSJ Dollar Index Falls 0.25% to 96.96', 'none'),
    ('weak_dollar_v1', 'Pushing for de-dollarisation', 'none'),
    ('weak_dollar_v1', 'Dollar drifts as Middle East tensions simmer, oil rises', 'none'),
    ('weak_dollar_v1', 'European Stock Indexes Mixed as Oil Holds Above $110', 'off'),
    ('weak_dollar_v1', 'Nscale Anthropic in AI Computing Talks', 'off'),
    ('fiscal', 'US oil price soars over 5% on Mideast conflict', 'off'),
    ('fiscal', 'Colombia Passes 16% Budget Increase After IMF Fiscal Warning', 'off'),
    ('fiscal', 'UK Debt Tops £3 Trillion as Deficit Overshoots Before Budget', 'worse'),
    ('fiscal', 'Chiriseri: France’s Fiscal Picture Concern Bond Markets', 'worse'),
    ('china_stimulus_v1', 'Auto industry bosses expect software, China growth to reshape sector by 2035, survey shows', 'off'),
    ('china_stimulus_v1', 'PBOC is expected to set the USD/CNY reference rate at 6.6779 – Reuters estimate', 'off'),
]


@pytest.mark.parametrize("nid,title,want", ROWS)
def test_direction_matches_bernardo(nid, title, want):
    C = news.cfg()
    got = news.classify(title, C["narratives"][nid], C)
    if want in ("none", "off"):
        assert got in ("off", "neutral"), (title, got)
    else:
        assert got == want, (title, got)


def test_rules():
    spec = {"reinforce": ["attacks", "hike"], "fade": ["talks", "no hike"]}
    assert news.lean("Oil Rises Amid Attacks on Vessels", spec, price_move=True) == "reinforces"   # cause clause
    assert news.lean("Oil Rises Amid calm", spec, price_move=True) == "neutral"
    assert news.lean("Iran says no talks until demands met", spec) == "reinforces"               # negation flips
    assert news.lean("Fed signals no hike this year", spec) == "fades"                           # longer cue wins
    assert news.lean("Talks resume after attacks", spec) == "fades"                              # main clause first
    assert not news.very("Shares shed 42% on delay", {}) and news.very("Profit unexpectedly rises", {}, ("unexpectedly",))
    assert news._say("fades", ("bullish", "bearish"), True) == "very bearish"
    cb = news.cfg()["narratives"]["cb_policy"]
    assert news.actors("RBA governor flags hike", cb) == ["RBA"] and news.actors("PBOC trims rate", cb) == []
    C = news.cfg()
    assert news.classify("RBA governor flags hike", cb, C) == "off"                              # minor bank, not a surprise
    assert news.classify("RBA unexpectedly hikes rates", cb, C) == "very hawkish"
    assert news.classify("Fed officials signal more hikes", cb, C) == "hawkish"
    assert news.classify("Drone strike on a market in Abyei kills 153", C["narratives"]["geopolitics"], C) == "off"
    oil = C["narratives"]["oil_supply"]
    assert news.classify("OPEC+ extends cuts into 2027", oil, C) == "shortage"
    assert news.classify("US announces SPR release of 30 million barrels", oil, C) == "glut"
