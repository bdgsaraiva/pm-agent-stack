---
name: morning-note
description: Write Bernardo's weekday morning note from the day's fact pack, modelled on his three sample notes (morning, midday, close): cross-asset market levels first, then what is happening (news since the US close → the prices it moved → the narratives it feeds, and whether each narrative is strengthening or losing its grip), bulls vs bears, the watching ladder, Market in a Minute digests with outlet links, the crowd check and journal candidates. Use in the 06:18 BRT scheduled task or when asked for today's morning note.
---

# Morning note (v4, 20 Oct 2026)

**What changed from v3 (Bernardo, 20 Oct).** The note opens with markets, not his book. Its job is the chain the samples do well: **news → price moves → narratives**, and a judgement on whether each live narrative is changing. News comes from the major outlets (the fact pack's "News since the US close": Reuters, Bloomberg, FT, WSJ, CNBC, NYT, Axios, Politico, MarketWatch, BBC, plus EIA, the Fed and commodity specialists), each item with its outlet and link, as the samples cite them. Kept from v3: the crowd check (now inside the narratives block) and journal candidates. Dropped: "Your book" and the question of the day. Structure notes: `format.md`.

He is a commodity specialist (commodities are the specialism; US equities, US rates and the USD are the conditioning layer). Focus: commodities, US equities, US rates, USD; not Petrobras, Vale, BRL or IBOV.

## Inputs (read in this order)
1. `notes/context.md`: standing facts he has stated; take them as given (e.g. dated Brent far above futures in 2026 is the war premium, not a data error).
2. `briefs/<today BRT>/facts.md`: the fact pack. **The only source of figures and links you may quote.** Sections you will use most: Alerts; **News since the US close** (Top stories, Narrative check, stories by topic, each with outlet, time, narrative tags and the moves of the markets it touches); prices; US rates, credit and macro; Positioning (CFTC); Consensus map (stages, Since, Bursts, Quiet, Headlines); Narrative discovery; Balances; Data health.
3. `briefs/<today>/alerts.json`: ranked alerts with refs such as `alerts:2026-10-21#3`.
4. `briefs/<previous weekday>/note.md` if it exists: don't repeat it; say what changed.

If today's fact pack is missing, write three lines: date of the latest pack, which fetch failed (from `logs/runs.jsonl`), and that nothing is refreshed. Never fill gaps from memory or the web.

## Rules
- **Numbers:** every figure from the fact pack, with its link (or, for a news item, the item's own link) and its date when it isn't today. No other numbers. Moves as the pack gives them (% for prices, bp only where the pack gives bp).
- **News items:** only items listed in the fact pack. Write the fact first in a short plain sentence faithful to the headline (no claim, figure or name the headline doesn't carry), then the outlet linked: `… ([Reuters](url))`. Prefer the story's lead outlet; the "also" outlets show how widely it ran ("reported by Reuters, Bloomberg and CNBC"). Never invent a link or an outlet. Headlines from the Consensus map's GDELT lists are second choice: use them only when no outlet story covers the point, and name their site.
- **Interpretation** is labelled once per paragraph with "Read:" (the samples argue; so may you, but the reader must see where facts end). Co-movement is not a cause: "oil fell as Hormuz headlines rose" is a fact; "because" needs a headline that says so.
- **No trade instructions, sizes or targets.** Questions, not recommendations.
- **Data artefacts:** a front-month move far from its sister contract with no news (e.g. WTI vs Brent on a WTI expiry day, a roll) is said as "possible contract roll; not read as a move", not interpreted.
- Exceptions only in the digests: a market with nothing unusual gets no line. No emoji.

## Structure
Title: `Morning note — <Weekday> <D> <Mon> <YYYY>`

The **top block** (sections 1–4) stands alone: a reader who stops there has the day. Bullets with a bold lead-in, as in the samples.

1. **Market levels –** one dense paragraph. US equity futures (S&P and Nasdaq e-minis, live), VIX if it moved; Asia closes (Nikkei, Hang Seng, Shanghai, KOSPI, ASX) in one clause, naming the outlier; Treasuries (2y and 10y yields with their bp change and date from the macro table; T-note futures live); the dollar index and any FX outlier; then commodities in more detail than the samples give them: Brent and WTI, products, natural gas, gold, silver, copper, and grains or softs that moved. Moves with their sd when the pack has it ("−2.1 sd"); "live" for marks still trading.
2. **What's happening –** the chain, in one paragraph or two:
   - Name the one theme driving the tape, plainly, and which assets express it (what trades as its hedge, what is the "anti-theme" market).
   - "In terms of incremental news, <n> developments since the <weekday> close:" then each one in a sentence with its outlet link, from the pack's Top stories and topic lists (the story covered by the most outlets first; at most four).
   - Tie each to price: the markets it touches and their moves (from the story's "moves"), and say when price and news disagree ("despite …, oil is lower in sympathy with …").
   - Tie each to a narrative, and say whether that narrative is **changing**, from the Narrative check (headlines today vs the prior average when the pack has one, stage and its previous value, burst, price agrees / disagrees). A large move that no story or narrative in the pack explains gets one honest clause ("no story in the pack covers it").
3. **Narratives: what's changing –** one line per narrative that has a burst, a stage change, a new-theme candidate, or headlines today with a price verdict; most important first, at most six. Each line: name; status (stage and since, or the burst ratio with articles over 7 days); news flow today (headlines today, and vs the prior average when given); price verdict with the market and its move; then one verdict word, labelled inference:
   - **strengthening**: burst or above-average news flow, and price agrees;
   - **contested**: news flow up but price disagrees (the samples' "despite the headlines" case);
   - **losing its grip**: stage fading or quiet and price disagrees or doesn't move;
   - **new**: a discovery candidate flagged NEW that touches a focus market (label, sources, the market, its co-movement line verbatim from the pack, at most 2 links); end that line with "Review: /narratives review".
   Then one sentence on CFTC extremes as of the report's Tuesday date ("crowding context, not a forecast"), and say "narratives are unvalidated" once. Ignore "stale" and "insufficient coverage" rows unless a burst or headlines put them in play. Never call a quiet narrative spreading or fading. A burst is never left out.
4. **What bears said / what bulls said –** for the dominant theme, two short labelled paragraphs, each the best argued case built only from pack facts and listed headlines (a numbered list of reasons is fine, as in the samples). Skip when nothing is contested.
5. **What we'll be watching –** a ladder: today, tomorrow, rest of the week, later. Known fixtures: EIA Weekly Petroleum Status Report Wednesday 10:30 ET; CFTC Friday 15:30 ET for Tuesday's positions; USDA reports in the Balances section; plus any dated event named in a listed headline (with its link). ET is UTC−4 until the first Sunday of November, UTC−5 after; BRT is UTC−3. The pack has no macro calendar yet: never invent CPI, payroll, FOMC or earnings dates.
6. **Market in a Minute (macro) –** 4 to 8 items separated by semicolons, each a short fact with its outlet linked: Fed and rates, inflation and growth data, FX, fiscal, geopolitics and trade.
7. **Market in a Minute (commodities) –** 4 to 8 items: oil and products, gas and LNG, metals, grains and softs; company items only when they bear on a commodity (supply, refinery, mine, guidance).
8. **Market in a Minute (equities and AI) –** up to 5 items, only where they bear on risk appetite, rates or commodity demand.
9. **Journal candidates.** Up to two alerts or stories that could become ideas, each with a ready line to paste, e.g. `/journal short RBOB? crowded long at 100th pct, front -4.9% live — source alerts:2026-10-21#1`. Prompts, not recommendations.
10. **Data health.** One line: failed or stale sources, possible contract rolls, news feeds that returned nothing.

Length: the top block 350–550 words; the whole note at most 1,000 words.

## Delivery
1. Save the draft as `briefs/<today>/note.md` (title line first; no doc line yet).
2. **Number audit (agent 5).** `python -m pmstack audit briefs/<today>/note.md --step audit:note`. It checks every figure, date and alert ref against the fact pack and the journal, prints `problems`, and writes `note.audit.json`.
   - If there are problems, **fix each one once** from `facts.md`: change only that figure, date or ref (smallest edit; don't rewrite the note). A figure with no source in the pack is deleted, not guessed.
   - Re-run with `--flag`: anything still unmatched is listed in a banner at the top of the note ("Number audit (code): …"). Never remove the banner by hand.
3. Create a Docs page with the title above; the audited note is the body, banner included, with sources linked inline.
4. Add the first line `<!-- doc: <docs url> -->` to `note.md`.
5. Log: `python -m pmstack log --step note:morning --fields '{"asof":"<today>","version":"v4","outputs":["briefs/<today>/note.md"],"doc_url":"<url>","alerts_used":["<refs>"],"news_items":<n linked>,"outlets":["<outlets cited>"],"audit":{"checked":<n>,"orphans":<n>,"fixed":<n>}}'`
6. `git add briefs logs && git commit -m "note: <today>" && git pull --rebase && git push`
7. Final message (the phone notification), three short lines: (1) the dominant theme in a few words, (2) and (3) the two biggest narrative changes or moves, then the Docs link. If the banner is there, start line 1 with "Audit: <n> unmatched figures".
