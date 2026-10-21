---
name: morning-note
description: Write Bernardo's weekday morning note from the day's fact pack, modelled on his three sample notes (morning, midday, close): a market levels table first, then what is happening (news since the US close → the prices it moved → the narratives it feeds), each narrative judged strengthening, fading, contested or new from what the news says, with the reinforcing and fading news under it, the watching ladder (earnings, data, central banks, events), Market in a Minute digests with outlet links (no price-move headlines) and journal candidates. Use in the 06:18 BRT scheduled task or when asked for today's morning note.
---

# Morning note (v6, 20 Oct 2026 night)

**v6 (Bernardo, 20 Oct night):** no opinion (prices, news, narratives and their links only); at most two outlets named per story; AI as one narrative with three parts (applications, cloud compute, data centres); no CFTC line; no UK data in the ladder; opinion pieces filtered out of the news; levels table from one source at one time with one change column.

**v5 (Bernardo, 20 Oct evening):** market levels as a code-picked table (relevant rows only on a 1.5 sd move or an alert; no coffee; JGBs added); narratives judged by what the news says (reinforces or fades), not by headline counts, with the reinforcing and fading news listed under each; bulls vs bears removed; the watching ladder from a calendar (watchlist earnings, data, central banks and speakers, hand-entered events; no weekly reports); no price-move headlines in the digests; five narratives retired and two redesigned (Oil and product supply, Geopolitical risk).

**What changed from v3 (Bernardo, 20 Oct).** The note opens with markets, not his book. Its job is the chain the samples do well: **news → price moves → narratives**, and a judgement on whether each live narrative is changing. News comes from the major outlets (the fact pack's "News since the US close": Reuters, Bloomberg, FT, WSJ, CNBC, NYT, Axios, Politico, MarketWatch, BBC, plus EIA, the Fed and commodity specialists), each item with its outlet and link, as the samples cite them. Kept from v3: the crowd check (now inside the narratives block) and journal candidates. Dropped: "Your book" and the question of the day. Structure notes: `format.md`.

He is a commodity specialist (commodities are the specialism; US equities, US rates and the USD are the conditioning layer). Focus: commodities, US equities, US rates, USD; not Petrobras, Vale, BRL or IBOV.

## Inputs (read in this order)
1. `notes/context.md`: standing facts he has stated; take them as given (e.g. dated Brent far above futures in 2026 is the war premium, not a data error).
2. `briefs/<today BRT>/facts.md`: the fact pack. **The only source of figures and links you may quote.** Sections you will use most: Alerts; **Market levels (table for the note)**; **News since the US close** (Top stories, Narrative check, stories by topic, each with outlet, time, narrative tags and the moves of the markets it touches); prices; US rates, credit and macro; Positioning (CFTC); Consensus map (stages, Since, Bursts, Quiet, Headlines); Narrative discovery; **Calendar (watching ladder)**; Balances; Data health.
3. `briefs/<today>/alerts.json`: ranked alerts with refs such as `alerts:2026-10-21#3`.
4. `briefs/<previous weekday>/note.md` if it exists: don't repeat it; say what changed.

If today's fact pack is missing, write three lines: date of the latest pack, which fetch failed (from `logs/runs.jsonl`), and that nothing is refreshed. Never fill gaps from memory or the web.

## Rules
- **Numbers:** every figure from the fact pack, with its link (or, for a news item, the item's own link) and its date when it isn't today. No other numbers. Moves as the pack gives them (% for prices, bp only where the pack gives bp).
- **News items:** only items listed in the fact pack. Write the fact first in a short plain sentence faithful to the headline (no claim, figure or name the headline doesn't carry), then the outlet linked: `… ([Reuters](url))`. Link the story's lead outlet; name at most one more ("reported by Reuters and Bloomberg"), or say how many carried it ("one of six outlets"), never the full list. Never invent a link or an outlet. Headlines from the Consensus map's GDELT lists are second choice: use them only when no outlet story covers the point, and name their site.
- **No opinion (Bernardo, 20 Oct evening).** The note holds only price data, news, narratives and the links between them. A link is either one the fact pack states (a story's narrative tag and its "moves"; the narrative check's price verdict) or plain co-movement said as such ("Brent -0.75% live as Gulf attack headlines rose"). No "Read:" lines, no chains of reasoning the news doesn't state (e.g. "the housing data feeds the Fed's hike debate"), no claims about what the market "treats as priced", no adjectives about the mood. "Because" only when a listed headline says so. The narrative verdict words below are the one judgement allowed, and they come from the news.
- **No trade instructions, sizes or targets.**
- **Data artefacts:** a front-month move far from its sister contract with no news (e.g. WTI vs Brent on a WTI expiry day, a roll) is said as "possible contract roll; not read as a move", not interpreted.
- Exceptions only in the digests: a market with nothing unusual gets no line. No emoji.

## Structure
Title: `Morning note — <Weekday> <D> <Mon> <YYYY>`

The **top block** (sections 1–3) stands alone: a reader who stops there has the day.

1. **Market levels** — a table, copied from the fact pack's "Market levels (table for the note)": the same rows in the same order (code chose them: fixed rows, plus Henry Hub, wheat, silver, RBOB, ULSD, JGB and OAT yields, EUR/USD, USD/JPY and other "relevant" rows only on a move of 1.5 sd or more or an alert). Never add or drop a row; coffee and LME metals are out by Bernardo's choice. Columns exactly as the pack's table gives them (one snapshot time, one change column vs the previous day, in % for prices, vol points for VIX, bp for yields), group headers as bold rows, the snapshot time from the pack's header. A row the pack marks "possible contract roll" or as an exception (e.g. a yield from another source) keeps that note in the Market cell. One source line under the table, from the pack. No commentary under the table.
2. **What's happening –** the chain, in one paragraph or two:
   - Open with the biggest moves (from the table) in one plain sentence, no characterisation.
   - "In terms of incremental news, <n> developments since the <weekday> close:" then each one in a sentence with its outlet link, from the pack's Top stories and topic lists (the story covered by the most outlets first; at most four; never a [price move] headline).
   - Tie each to price (the story's "moves", as co-movement) and to the narrative the pack tags it with. When price went the other way, say so as a fact ("Brent -0.75% live despite the attack headlines"). A large move that no story explains gets one clause: "no story in the pack covers it".
3. **Narratives: what's changing –** one block per narrative that has stories today, a burst or a stage change (most important first, at most six), from the pack's Narrative check and its per-narrative story lists:
   - **Judge direction from what the news says, not from how much there is.** Read each listed headline: does it make the narrative more likely or more intense (reinforces), or less (fades)? The code's lean tag is a keyword pointer; overrule it when the headline says otherwise (e.g. a "deal" that ends supply would reinforce a supply-tightness narrative). Headline counts and the prior average are context only.
   - One line: name — **verdict** (inference) — why, in a clause: stage and since (or "news feed only, not on the map yet"), burst if any, and whether its markets moved its way (the pack's price verdict with the market and move).
   - Verdicts: **strengthening** (the news mostly reinforces it); **fading** (the news mostly fades it, or no new reinforcing news while the stage is fading or quiet); **contested** (news on both sides, or the news reinforces it while price moves against it: say which); **new** (a discovery candidate flagged NEW that touches a focus market: label, sources, the market, its co-movement line verbatim from the pack, "Review: /narratives review").
   - Under the line, the news that moved it: up to three headlines that **reinforce** it and up to two that **fade** it, each a short sentence with its outlet linked, marked "reinforces:" / "fades:".
   - **AI is one narrative with three parts** (Bernardo, 20 Oct evening): **AI: applications** (model and app companies: OpenAI, Anthropic, agents), **AI: cloud compute** (hyperscalers including Oracle, and neoclouds), **AI: data centres** (capex beneficiaries: semis, memory, power, optical, cooling and other data-centre suppliers). Write one **AI** block: a heading line, then one verdict line per part with its reinforcing and fading news under it; a part with no stories today gets "no stories today".
   - Live narratives: AI (three parts), Oil and product supply, Geopolitical risk (these news feed only until their GDELT definitions are frozen), Oil glut, Natural gas / LNG, China stimulus, Fed hikes, Fed cuts, Recession fears, Weak dollar, US fiscal stress. Retired on 20 Oct (don't use): AI bubble, AI trade scare (now inside AI), Trade war / tariffs, US pump prices, Inflation scare, Russian oil sanctions, Hormuz / Iran oil supply (now inside Oil and product supply and Geopolitical risk), OPEC+, Copper shortage, Gold buying, Crop weather.
   - Say "narratives are unvalidated" once. No CFTC positioning line (Bernardo, 20 Oct evening). Never call a quiet narrative spreading or fading on the map's stage alone. A burst is never left out.
4. **What we'll be watching –** from the pack's "Calendar (watching ladder)": **Today**, **Next session**, **This week**, **Next week**, **Later**. Include watchlist earnings (with "before the US open" / "after the US close"), hand-entered events (conferences, keynotes), economic releases and central-bank decisions the calendar keeps (with ET and BRT times and the forecast when given; no UK data), and Fed and other central-bank speakers. No weekly reports (CFTC, EIA inventories, jobless claims). You may add a dated event named in a listed headline, with its link. Never invent dates; an empty bucket is left out.
5. **Market in a Minute (macro) –** 4 to 8 items separated by semicolons, each a short fact with its outlet linked: Fed and rates, data, FX, fiscal, geopolitics and trade. **Never a [price move] headline** (one whose point is only that a market rose or fell).
6. **Market in a Minute (commodities) –** 4 to 8 items: oil and products, gas and LNG, metals, grains and softs; company items only when they bear on a commodity (supply, refinery, mine, guidance). No [price move] headlines.
7. **Market in a Minute (equities and AI) –** up to 5 items, only where they bear on risk appetite, rates or commodity demand. No [price move] headlines.
8. **Journal candidates.** Up to two alerts or stories that could become ideas, each with a ready line to paste, e.g. `/journal short RBOB? front -4.9% live — source alerts:2026-10-21#1`. The line only; no comment or question after it.
9. **Data health.** One line: failed or stale sources, possible contract rolls, news or calendar feeds that returned nothing, rows with no data (e.g. French OAT).

Length: the top block 350–550 words (the table not counted); the whole note at most 1,000 words.

## Delivery
1. Save the draft as `briefs/<today>/note.md` (title line first; no doc line yet).
2. **Number audit (agent 5).** `python -m pmstack audit briefs/<today>/note.md --step audit:note`. It checks every figure, date and alert ref against the fact pack and the journal, prints `problems`, and writes `note.audit.json`.
   - If there are problems, **fix each one once** from `facts.md`: change only that figure, date or ref (smallest edit; don't rewrite the note). A figure with no source in the pack is deleted, not guessed.
   - Re-run with `--flag`: anything still unmatched is listed in a banner at the top of the note ("Number audit (code): …"). Never remove the banner by hand.
3. Create a Docs page with the title above; the audited note is the body, banner included, with sources linked inline.
4. Add the first line `<!-- doc: <docs url> -->` to `note.md`.
5. Log: `python -m pmstack log --step note:morning --fields '{"asof":"<today>","version":"v6","outputs":["briefs/<today>/note.md"],"doc_url":"<url>","alerts_used":["<refs>"],"news_items":<n linked>,"outlets":["<outlets cited>"],"audit":{"checked":<n>,"orphans":<n>,"fixed":<n>}}'`
6. `git add briefs logs && git commit -m "note: <today>" && git pull --rebase && git push`
7. Final message (the phone notification), three short lines: (1) the dominant theme in a few words, (2) and (3) the two biggest narrative changes (strengthening or fading) or moves, then the Docs link. If the banner is there, start line 1 with "Audit: <n> unmatched figures".
