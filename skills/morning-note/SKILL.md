---
name: morning-note
description: Write Bernardo's weekday morning note (commodity supply-demand + central banks, read-through to Petrobras, Vale, BRL, IBOV) from the day's fact pack in this repo. Use in the 06:30 BRT scheduled task or when asked for today's morning note.
---

# Morning note

You write a short, sourced morning note for a cross-asset PM (commodities and equity indices, Brazil-based, global book). Code has already fetched the data and computed every number. Your job is to choose what matters and say why, in plain English.

## Inputs (read in this order)

1. `briefs/<today BRT>/facts.md` — the fact pack. **The only source of figures you may quote.**
2. `briefs/<today BRT>/alerts.json` — ranked alerts.
3. `briefs/<previous weekday>/note.md` if it exists — so you don't repeat yesterday's story and can say what changed.
4. Notes changed in the last 7 days: `notes/**/*.md` (research, calls, podcasts) and `journal/*.md` with `status: open`. On the personal build the journal holds dummy or public ideas only.

If today's `facts.md` is missing or its "Data health" shows a source in `error`, say so in the first line of the note and continue with what is there. If no fact pack exists for today, write a three-line note: the date of the latest fact pack, which fetch failed (from `logs/runs.jsonl`), and that the numbers are not refreshed. Do not fill gaps from memory or the web.

## Rules

- **Every number comes from the fact pack and carries its link** in the form `[source](url)` right after it, with its date when it isn't today's. No other numbers. Never round in a way that changes meaning.
- **Facts vs inference.** State facts plainly. Mark interpretation with "Read:" or "Inference:". Never present an inference as a fact.
- **No trade instructions, sizing or targets.** You can say what a move implies or what to watch; decisions stay with the PM.
- "Overnight" means the Asia session. Futures and FX marked "Live" are still trading; call them "live" or "overnight", never "closed".
- Prefer what changed and what is unusual (alerts, extremes, surprises against the seasonal norm) over a tour of every market. A quiet market gets one line or none.
- Length: 300 to 450 words. Short sentences. No emoji. British or American spelling, consistently.

## Structure

Title: `Morning note — <Weekday> <D> <Mon> <YYYY>`

1. **Three things that matter today** — three bullets, each one sentence with its figure and link.
2. **Overnight (Asia)** — one or two sentences from the Asia table, plus any live energy or FX moves.
3. **Commodities: supply, demand, positioning** — energy first (EIA week vs seasonal, positioning), then metals and ags only where something moved or sits at an extreme.
4. **Central banks and policy** — new statements in the last 36 hours, with links; Focus revisions.
5. **Read-through** — one line each for Petrobras, Vale, BRL, IBOV, using the "Read-through inputs" list. Label each as inference.
6. **Releases this week (fixed schedule)** — EIA Weekly Petroleum Status Report, Wednesday 10:30 ET; CFTC Commitments of Traders, Friday 15:30 ET for Tuesday data; BCB Focus survey, Monday morning. Convert ET to BRT for the date in question (ET is UTC-4 until the first Sunday of November, UTC-5 after; BRT is UTC-3 all year), and note that US holidays push EIA and CFTC back a day. Mention only releases still ahead this week.
7. **Data health** — one line: sources that failed or are stale, and the known gaps.

## Delivery

1. Create a Docs page with the title above and the note as its body (sources linked inline).
2. Save the same text as `briefs/<today>/note.md`, with a first line `<!-- doc: <docs url> -->`.
3. Log the run: `python -m pmstack log --step note:morning --fields '{"asof":"<today>","outputs":["briefs/<today>/note.md"],"doc_url":"<url>","alerts_used":[<ranks>]}'`
4. Commit `briefs/` and `logs/` with message `note: <today>` and push.
5. Final message of the task (this is what the phone notification shows): the three "things that matter" bullets in one line each, then the Docs link.
