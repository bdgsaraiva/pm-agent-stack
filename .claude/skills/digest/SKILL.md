---
name: digest
description: Digest a podcast episode, video, public paper or public research note into Bernardo's summary format with checked claim cards, a call ledger entry and the research index (agent 10). Use when he shares a YouTube link, a transcript file, a paper (PDF or URL) or says "digest this", "summarise this episode", "add this to the research memory", or asks what guests said about a market or how a speaker's calls did.
---

# Research digester (agent 10)

**Why this shape** (docs/research/digester.md): LLM summaries of long spoken sources go wrong often enough to matter (14.7–51% of interview summaries carry an error; omissions in 52–85% of long summaries), and model-emitted citations are unsupported about half the time. So the unit is the **claim card**: one claim, a verbatim quote that code finds in the transcript, numbers only from that quote. Public calls are right ~47% of the time, so forecasts go to a ledger that code scores against stored prices; a speaker earns weight only through that record.

## Rules
- **Public sources only** (podcasts, videos, public papers and notes). No broker research, no fund data: if the source is broker or sell-side research, say it belongs in the corporate build and stop.
- **The model never supplies a number.** Every number in a card is in its quote; every market number in the note comes from `digest facts` (code, with links). No levels from memory.
- **Report only what the speaker said.** No model context, no tense or quantifier changes, hedges kept verbatim.
- Full transcripts stay local (`data/transcripts/`, gitignored). Quotes ≤ 40 words.

## 1. Capture
`python -m pmstack digest fetch "<YouTube link | URL | file>"` → `sha12`, `kind` (time/page/none), `asr` (auto-captions), `language`, `windows`. YouTube publisher captions are used when they exist; auto-captions get names flagged [ASR?].

## 2. Extract, window by window
For each window `i`: `python -m pmstack digest chunks <sha12> --window <i>`, then write the window's cards into one JSON list (append across windows). One card per checkable claim:
```json
{"speaker": "Arlindo Penteado", "t": "00:12:40", "quote": "<exact words, ≤40>", "claim": "<paraphrase; digits only from the quote>",
 "type": "data|forecast|opinion", "markets": ["BZ=F"], "themes": ["opec"], "direction": "up|down|flat",
 "level": 110, "level_kind": "close|touch", "deadline": "2026-12-31", "deadline_basis": "by year-end",
 "probability": 0.6, "hedge": ["could", "if"], "because": "...", "unless": "...",
 "horizon": "tactical|structural"}
```
- `type`: **data** = a figure the speaker cites; **forecast** = a future, resolvable statement; **opinion** = everything else.
- `markets` only from the refs in `config/digest.yaml` (Brent `BZ=F`, WTI `CL=F`, … DXY `DX-Y.NYB`); anything else goes in `themes`.
- `deadline`: from the speaker's words (`deadline_basis`): "by year-end" → 31 Dec; "next quarter" → last day of next calendar quarter; no horizon → leave empty (the card is then unscoreable and carries no weight).
- `probability` only if the speaker states one as a percentage ("60%", "sessenta por cento"); otherwise leave it empty and code maps the hedge words (labelled inference). Code labels the source; the card can't.
- The quote is copied exactly: a near-match that changes a number, a negation ("not", "não") or a hedge is blocked (`quote_altered`).
- Translation is detected from the transcript's language; English claims from Portuguese speech get name checks as warnings.
- Cover every window; at least one card per window where something checkable was said. Skip pleasantries and ads.

## 3. Note header, then save the cards
Create `notes/<podcasts|research|letters|videos>/<series-slug>/<YYYY-MM-DD>-<slug>.md` (date = recording or publication date):
```yaml
---
type: podcast            # podcast | video | paper | research | letter | article
series: ""
episode: ""
date: YYYY-MM-DD        # recording date (as-of for the speaker's numbers)
published: YYYY-MM-DD   # when it became public, if later: the critic sees the cards only from this date
guests: []
assets: []               # price refs, e.g. [BZ=F, HG=F]
tags: []
url: ""
source_note: ""          # e.g. "YouTube auto-captions (Portuguese), read 15 Oct 2026"
questions: []            # questions to ask next (agent 11 carries them into calls)
---
```
Then `python -m pmstack digest save <note.md> --cards <cards.json> --transcript <sha12>`. For each problem, fix the card once from the transcript (shorter exact quote, drop the number, restore the hedge, fix the market) and save again. Rejected cards (quote not found) are dropped or re-extracted. Flagged cards that stay flagged are listed at the end of the note; they never reach the ledger or the critic.

## 4. Code facts and history
- `python -m pmstack digest facts <note.md> --write` → market move since the recording, 5 sessions before it, distance to each forecast level (all from stored data).
- `python -m pmstack digest diff <note.md>` → earlier cards from the same series or speakers on the same markets.
- `python -m pmstack digest view --market <ref>` → how many stored cards lean each way (for consensus vs contrarian).

## 5. Write the body (Bernardo's format), 400–900 words, no emoji
1. **Key messages** — 3–6 bullets, each traceable to cards (ids in brackets, e.g. `[c3]`).
2. **Numbers and arguments by speaker** — per speaker: each figure with its card id and timestamp; `because` and `unless` kept.
3. **Consensus vs contrarian** — counted, not asserted: "N stored cards on Brent lean up, M down (digest view)". Mark the speaker's view against that count. Inference labelled "Read:".
4. **Confidence and horizon** — a table: card, type (data/forecast/opinion), probability and its source (stated / hedge inference), horizon, deadline, scoreable yes/no.
5. **What changed since last time** — from `digest diff` (skip when empty).
6. **Market since recording** — from the facts file only ("Brent +2.5% since the recording; it fell 4.0% in the 5 sessions before").
7. **Questions to ask next** — also in the header's `questions`.
8. **Read-across for the book** — inference, labelled; open ideas it bears on by journal id. No trade instructions.
9. **Checks** — flagged cards, uncovered windows, `[ASR?]` names.

## 6. Audit, index, log, commit
1. `python -m pmstack audit <note.md> --facts <note>.cards.json <note>.facts.json --flag --step audit:digest`. Fix each orphan once from the cards or facts; re-run.
2. `python -m pmstack digest index`
3. `python -m pmstack log --step digest:note --fields '{"note":"<path>","cards_ok":<n>,"forecasts_scoreable":<n>,"flagged":<n>,"audit":{"checked":<n>,"orphans":<n>}}'`
4. `git add notes logs && git commit -m "digest: <series> <date>" && git pull --rebase && git push`
5. Reply in three lines: the key message, the scoreable calls (market, direction or level, deadline), and the checks that need his eye.

## Questions he may ask
- "What did guests say about copper?" → `digest view --market HG=F` and the cards; never a synthesis over raw transcripts.
- "How are the calls doing?" / "Is X any good?" → `python -m pmstack digest calls [--all]`: resolved, due, records. Under `record_min_calls` (15) resolved calls say "too few to judge; prior 47.4% (CXO)".
- Logging an idea from an episode: `/journal ... --source podcast --source-ref notes/<path>.md` (the journal checks the path exists).
