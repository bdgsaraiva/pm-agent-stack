# Note format spec (structure only)

Written 16 Oct 2026 from three email notes Bernardo considers models (one morning, one midday, one close, same day, from a US market newsletter he receives). Per `docs/project/notes-and-keys-kickoff.md` §3, **only the structure is kept here**: no content, figures, names, tickers or text from the samples. The samples are equity-first; this spec adapts the structure to his commodity-specialist book and to this repo's rules (figures from the fact pack only, links from the fact pack only, inference labelled).

## 1. What the models do well
1. **One skeleton, three clocks.** Morning (before the open), midday (late morning), close (just after the cash close) share the same top block, so a reader knows where to look. What changes is the time anchor and what "news" means (since the last close / since this morning / today).
2. **Cross-asset levels in one paragraph.** The first bullet states every market that matters in one dense sentence: equity indices (futures in the morning, cash later), regions (Europe, then Asia by market), rates (curve move in bp), the policy-rate path the market prices (by meeting), the dollar, oil, gold, silver, crypto. Moves in bp or points, not prose.
3. **One dominant narrative, said plainly, then tied to prices.** The second bullet ("what's happening") names the theme driving the tape, says which assets express it and why (e.g. one asset class trades as the hedge against the theme; a region outperforms because it is the "anti-theme" market), and reconciles price with news when they disagree ("despite escalating headlines, oil is lower in sympathy with risk-off"). It counts the incremental developments since the last note ("two developments since the close: A and B") and links each.
4. **Both sides of each live narrative.** Labelled paragraphs: "what bears/hawks said" and "what bulls/doves said" about the key data or theme, each a short argued case. A numbered list of reasons when the note disagrees with the obvious reading of a headline ("volumes are back, but this isn't a reason to celebrate: 1) … 6) …").
5. **Every news line carries its source.** One line per item, the fact first, then the source in parentheses, linked: wire and press (Bloomberg, Reuters, FT, WSJ most often; CNN, Axios, CNBC, NYT, Politico), company releases, official data, and the author's own earlier pieces. Two digests: macro and micro ("market in a minute"), split by when the news broke (overnight vs after the morning send).
6. **A forward ladder.** "What we'll be watching": today, tomorrow, next week, the week after, then a long calendar (data, central banks, elections, budgets, company events) out ~2 months. Times in ET.
7. **Midday adds breadth.** What is outperforming / underperforming, by industry group, and which moves are news-linked (earnings) vs theme-linked.
8. **Close adds the verdict.** Closing levels with the intraday extreme; "what happened" as an interpretation of the day (breadth, rotation, what the market ignored and why); bears vs bulls; out/underperformers.
9. **Thematic sections after the top block.** Geopolitics, US macro/Washington, international macro, then sectors. Long, but skippable: the top block stands alone.

## 2. Our morning note, adapted (06:18 BRT)
Keeps v2's purpose (his book first, exceptions only, audited) and borrows the models' top block. Target 300–500 words.

1. **Your book** (unchanged from v2): open ideas, flags, risk line.
2. **Market levels** (new; one paragraph, from the fact pack only): commodities first (Brent/WTI, products, natgas, gold/silver, copper, grains/softs where they moved), then the conditioning layer (US equity futures, 2y/10y in bp, dollar index, Asia session closes). Moves with their sd where the pack gives it; live marks said as live.
3. **What's driving it** (new; the narrative-to-price paragraph): name the one or two narratives that best explain today's moves, using the Consensus map (stage, since when, share vs 26 weeks) and the prices above; say which assets express each narrative and whether price agrees with the news (e.g. narrative spreading but the market it pushes is falling: say so). Up to 3 headline links per narrative from the pack's "Headlines" list, as `[title](url) (source)`. Inference starts with "Read:".
4. **What changed that matters** (v2's alerts, max 3, each with its alert ref).
5. **Bulls vs bears** (new, optional, one line each): for the dominant narrative or the biggest alert, the best case on each side, labelled inference. Skip when nothing is contested.
6. **Crowd check** (v2): stage changes (a narrative going "quiet" = under the floor but measurable; "insufficient coverage" → "quiet" is a relabel, skipped), idea placement, CFTC extremes (Friday release rule), one "Read:".
7. **Macro as it bears on commodities** (v2, ≤2 sentences).
8. **Journal candidates** and **Question of the day** (v2).
9. **Watching** (v2's "this week", reshaped as a ladder): today, tomorrow, rest of week, from what the pack knows (EIA weekly, CFTC, central-bank calendar when added). No invented dates.

## 3. Midday and close (only if Bernardo asks for them)
- **Midday (~13:00 BRT):** market levels (intraday), what's driving it, what's out/underperforming across his markets, news since 06:18 with links, watching for the afternoon. Needs an intraday data run and a fresh pack.
- **Close (~18:30 BRT):** closing levels with the day's range, what happened (interpretation), bulls vs bears, out/underperformers, watching for tomorrow. Needs a post-close data run.
- Both: same audit, same link rule, ~250 words.

## 4. Rules that do not change
- Figures only from `briefs/<date>/facts.md`, each linked; the auditor runs before publishing.
- Links only from the fact pack (its Headlines list and source links), never from the web or from memory. Titles verbatim.
- No broker or sell-side content in this repo (CLAUDE.md): the models give structure only.

## 5. Gaps against the models (what the pack does not have yet)
| Model element | Our status |
|---|---|
| Policy-rate path by meeting | Not in the pack (no futures-implied path). Free option to evaluate: fed funds futures via a public source |
| Macro / company calendar ladder | Only EIA and CFTC; a public economic calendar adapter would be needed |
| Breadth (equal-weight vs cap-weight, sector leaders) | Partial (sector ETFs XLE, XLB); fine for a commodity book |
| Wire headlines on any topic | Only for the 18 frozen narratives (GDELT); off-narrative news is not covered |
| Intraday levels | Daily job only; midday/close need extra runs |
