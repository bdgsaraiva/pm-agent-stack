---
name: morning-note
description: Write Bernardo's weekday morning note from the day's fact pack and his decision journal: his open ideas first, then the few overnight changes that matter for a commodity-specialist book, the crowd check, macro as conditioning, journal candidates and one critic question. Use in the 06:18 BRT scheduled task or when asked for today's morning note.
---

# Morning note (v3, 16 Oct 2026: v2 + the top block of Bernardo's model notes, see `format.md`)

**Why v2.** Generic market briefs are now a vendor product (Bloomberg ASKB Workflows, AlphaSense, Claude templates). This note earns its place only with what nobody else has: Bernardo's open ideas, his rules, his history and the crowd measured against him. He is a commodity specialist (commodity book Sharpe 1.9 since Jul 2023); US equities, US rates and the USD are the conditioning layer. Goal: Sharpe 1.5+ over 3 years; biggest leak: under-sizing the best ideas.

## Inputs (read in this order)
1. `notes/context.md`: standing facts he has stated. Take them as given (e.g. dated Brent far above futures in 2026 is the war premium, not a data error).
2. `briefs/<today BRT>/facts.md`: the fact pack. **The only source of figures you may quote**, each with its link.
3. `briefs/<today>/alerts.json`: ranked alerts, each with a `ref` such as `alerts:2026-10-12#3`.
4. `briefs/<previous weekday>/note.md` if it exists: don't repeat yesterday; say what changed.
5. `journal/*/*.md` with status open or idea (the fact pack's "Your open ideas" table already has prices and distances), plus notes changed in the last 7 days under `notes/`.

If today's fact pack is missing, write three lines: date of the latest pack, which fetch failed (from `logs/runs.jsonl`), and that nothing is refreshed. Never fill gaps from memory or the web.

## Rules
- Every number from the fact pack, with `[source](url)` and its date when it isn't today. No other numbers.
- Facts plainly; interpretation starts with "Read:". No trade instructions, sizes or targets. Questions, not recommendations.
- Ignore journal entries with book `example`, except to say "No open paper ideas yet" when they're the only ones.
- Exceptions only: a market with nothing unusual gets no line. 300 to 500 words. No emoji.
- Format: `skills/morning-note/format.md` (structure modelled on his morning/midday/close emails; structure only).
- "Overnight" = the Asia session. Futures and FX marked live are still trading.

## Structure
Title: `Morning note — <Weekday> <D> <Mon> <YYYY>`

1. **Your book.** One line per open idea from the journal table: distance to invalidation and target, R so far, days vs horizon, and the overnight fact that most supports or contradicts it. Flags first:
   - INVALIDATED → "Zweig #3: the reason is gone. Exit, or re-underwrite in the journal."
   - past horizon → "Past its horizon: still the same thesis?"
   - crowded (90+ percentile on its side) → "You're with the crowd: what do you know that it doesn't?"
   - price against the idea for 2+ weeks while the thesis is unchanged → tape-vs-thesis question.
   No open ideas: one line, "No open ideas in the journal."
   **Risk line** (agent 8, the fact pack's "Risk and crowding" section; exceptions only, no full table):
   - Any warning (amber or red drawdown, clustered losses, persistent turbulence) first, with its alert ref. Red means size suggestions are halved: say it.
   - Idea flags from the risk table: "stop near flip level", "panic state: rebound risk", "crowded while funding is stressing", "crowded entry"; and a 1m/3m/12m leg on an idea's market that flips by roll-off within 5 days.
   - When two or more paper ideas are open: one sentence with effective independent ideas vs the count, and the worst 1-day historical window for the book in R (stops honoured and gapped), with its dates. Caption once: "stress tests describe, they don't warn."
   - Nothing to say → no risk line.
2. **Market levels.** One paragraph, figures from the fact pack only: commodities first (Brent/WTI, products, natural gas, gold/silver, copper, grains and softs that moved), then the conditioning layer (US equity futures, 2y and 10y yields in bp, dollar index, Asia session closes). Moves with their sd where the pack has it; say "live" for marks still trading.
3. **What's driving it.** The narrative-to-price paragraph. **Start from the moves, not the stage table:** take the two or three largest cross-asset moves of the day (the biggest sd moves in the alerts and levels, in any asset, not only commodities: an equity-index drop with a VIX spike counts) and, for each, say which narrative in the pack explains it. Look first at the fact pack's **Bursts** line (a narrative at 2x+ its prior-26-week share over the last 7 data days: a one-week shock the 4-week stage cannot show), then at stage changes, then at any narrative whose "Headlines" match the move. Give its figure (burst ratio and articles over 7 days, or 4-week share and stage, with "since"), say which assets express it and whether price agrees with the news (e.g. the narrative bursting while the market it pushes rebounds). At most 3 headline links per narrative, only from the pack's "Headlines" list, as `[title](url) (source)`. A large move that no narrative or headline in the pack explains gets one honest clause ("no narrative in the pack covers it"); never fill the gap from memory or the web. Interpretation starts with "Read:". A burst narrative is never left out of the note: if it explains no move today, it still gets one line in the Crowd check.
4. **What changed that matters.** At most three bullets from the alerts, commodities first, each ending with its alert ref in brackets.
5. **Bulls vs bears** (optional). For the dominant narrative or the biggest alert: one line for each side's best case, labelled inference. Skip when nothing is contested.
6. **Crowd check.** From the fact pack's "Consensus map" (agent 7; descriptive, labels are inference):
   - **Bursts first:** every narrative on the pack's Bursts line that the paragraph above did not already cover, with its 7-day ratio and articles, "new since the previous pack" when the line says so, and up to 3 headline links. A burst on a quiet or insufficient-coverage narrative is still news: report it (the 4-week stage stays what it is).
   - Narratives whose stage differs from the previous pack (the bracket in the Stage column; e.g. turned spreading or fading), with their share of coverage vs the prior 26 weeks; say "unvalidated" once. Name the narrative in the same sentence as its figure (the auditor binds a narrative figure only to words its own name has). Ignore "stale" and "insufficient coverage" rows. "Quiet" = under the article floor but measurable (a low reading, not a gap): a narrative that turned quiet from a moving stage gets one clause ("went quiet; 4-week average last at the floor on <date>", the date from the pack's Quiet line), and only when it bears on an open idea or today's moves; a change from "insufficient coverage" to "quiet" is a relabel, not news: skip it. Never call a quiet narrative spreading or fading.
   - For each of those narratives, "since <date>" from the Since column (≤ means "at least since"), and **at most 3 headline links** from the fact pack's "Headlines" list, as `[title](url) (source)`, so he can see what moved it. Links only from that list, never from the web; titles verbatim, not paraphrased into claims. No headlines listed → no links (say nothing about it).
   - **New themes** (agent 7 discovery, the fact pack's "Narrative discovery" section; Bernardo's choice 20 Oct 2026: day-1 themes reach him in this note): each candidate flagged NEW that touches a focus market and is not demoted, one line: its label, sources count, the market it touches, at most 2 headline links from its list, and its code-computed price line verbatim from the pack ("co-movement, not a cause"). End with "Review: /narratives review". None → skip. Never a forecast or a trade suggestion.
   - Your ideas' placement (with the crowd / against it / quiet), with the trend score and CFTC percentile on your side, and any narrative against you that is spreading.
   - Sides at CFTC extremes in one sentence, as of the report's Tuesday date ("crowding context, not a forecast").
   - Then one "Read:" line on what the consensus seems to assume, so he can look for the second-order view.
   - No full map in the note: the map stays in facts.md. No burst, nothing that changed and no ideas affected → one line, "Crowd: no stage changes or bursts."
7. **Macro, as it bears on commodities.** Two sentences at most: USD, real yields, equities and credit, only where they move a commodity or an open idea.
8. **Journal candidates.** Up to two alerts that could become ideas, each with a ready line to paste, e.g. `/journal short RBOB? crowded long at 100th pct, front -5.4% — source alerts:2026-10-09#1`. These are prompts, not recommendations.
9. **Question of the day.** One question tied to something concrete today, drawn from Zweig's rules (#2 losers, #3 reason gone, #9 should vs is, #11 overtrading, #16 headlines, #17 new era), Donnelly (second-order, narrative contagion, bet sizing) or the sizing rule ("Is your highest-conviction idea also your largest risk?").
10. **Watching and data health.** A ladder: today, tomorrow, rest of the week. Releases still ahead (EIA Weekly Petroleum Status Report Wednesday 10:30 ET; CFTC Friday 15:30 ET for Tuesday; ET is UTC-4 until the first Sunday of November, UTC-5 after; BRT is UTC-3; US holidays push both back a day; no macro calendar in the pack yet, so don't invent CPI, payroll or FOMC dates). Then one line on failed or stale sources.

## Delivery
1. Save the draft as `briefs/<today>/note.md` (title line first; no doc line yet).
2. **Number audit (agent 5).** `python -m pmstack audit briefs/<today>/note.md --step audit:note`. It checks every figure, date and alert ref against the fact pack and the journal, prints `problems`, and writes `note.audit.json`.
   - If there are problems, **fix each one once** from `facts.md`: change only that figure, date or ref (smallest edit; don't rewrite the note). A figure with no source in the pack is deleted, not guessed.
   - Re-run with `--flag`: anything still unmatched is listed in a banner at the top of the note ("Number audit (code): …"). Never remove the banner by hand.
3. Create a Docs page with the title above; the audited note is the body, banner included, with sources linked inline.
4. Add the first line `<!-- doc: <docs url> -->` to `note.md`.
5. Log: `python -m pmstack log --step note:morning --fields '{"asof":"<today>","outputs":["briefs/<today>/note.md"],"doc_url":"<url>","alerts_used":["<refs>"],"journal_ids":["<ids mentioned>"],"audit":{"checked":<n>,"orphans":<n>,"fixed":<n>}}'`
6. `git add briefs logs && git commit -m "note: <today>" && git pull --rebase && git push`
7. Final message (the phone notification), three short lines: (1) book status (e.g. "2 open ideas, none near invalidation" or the flag), (2) and (3) the two biggest changes, then the Docs link. If the banner is there, start line 1 with "Audit: <n> unmatched figures".
