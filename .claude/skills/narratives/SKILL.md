---
name: narratives
description: Bernardo's narrative selection conversation (agent 7, step 2). Use when he says "/narratives review", "review the new themes", "what's new in the news", asks about a discovered theme, or wants to promote, watch or dismiss a candidate; also to settle a tracked narrative whose headline audit failed.
---

# Narrative selection (agent 7, step 2 of 2)

**Why this shape** (docs/research/narrative-discovery.md): discovery (step 1, code) nominates with a low bar; selection is human, as in GPHIN and EMM triage. Context is co-movement only: news volume lines up with same-day moves and volatility, geopolitical oil news reverses within a week (Brandt & Gao), and no study links news attention to CFTC positioning. Most candidates will be dismissed; that is normal. Every candidate shown counts as a trial for agent 12.

## Rules
- **Numbers only from code**: the discovery section (`python -m pmstack discovery list`) and the tracker. The model words a candidate's label in one sentence from its headlines; it never adds a price, a level or a view of its own.
- **No forecast, no trade suggestion.** "Does it talk to prices and positioning?" is answered with the code lines as they are, labelled co-movement; any "it leads prices" claim goes to `/research` (agent 12).
- Headlines are shown verbatim with their links; never paraphrased into claims.

## 1. Show the candidates (Bernardo: every candidate, daily, grouped by market)
`python -m pmstack discovery list` (add `--json` for the full record). For each candidate, in market groups (focus markets first, then "outside focus", demoted last, collapsed):
- label, NEW / rising / sustained, sources, terms, the tracked narrative it updates (if any);
- 3 headlines (the list carries top and random ones: the random ones show precision honestly);
- the context lines verbatim: move on the first day in sd with its base rate, the 5 sessions before, since; 20-day vol before and now; CFTC managed money before vs latest (commodities only; "positions follow price"); open ideas in that market.

## 2. Ask (AskUserQuestion, multiple choice; at most 4 candidates per round, the focus-market NEW ones first)
For each candidate: **Promote** (track it) / **Watch 14 days** (re-shown only if it doubles or turns sustained) / **Dismiss** (then the reason: noise = false match, not-market = real but irrelevant, duplicate, known). He may also correct the markets touched. Remaining candidates: "dismiss the rest as not-market?" in one question.

## 3. Record
`python -m pmstack discovery decide <id> --action promote|watch|dismiss [--reason noise|not-market|duplicate|known|other] [--markets BZ=F,CL=F] [--note "..."]`
A dismissal hides matching candidates for 30 days, or until they reach 3x the sources at dismissal, whichever comes first.

## 4. Promotion (a candidate he promotes becomes a tracked narrative only after it passes)
1. `python -m pmstack discovery draft <id>` → a title-phrase query; agree the meaning line and the markets it pushes (and which way) with him.
2. Measure: add it to a new spec in `docs/research/narrative-measure/<date>-spec.yaml` (two windows: the burst and a quiet one) and run the `narratives-measure` workflow (`gh workflow run narratives-measure.yml -f spec=<path> -f max_gb=30`).
3. Headline audit: 25 headlines, two blind labellers, Bernardo decides the splits; freeze only at >= 70% precision. Otherwise narrow and re-measure, or keep it watched.
4. Freeze: a new `<name>_v1` in `config/sources.yaml` `gdelt_bq_v2.queries` with `narrative:`, markets and signs, `discovered_on` and `promoted_on`; never re-fitted backward. It joins the Consensus map under the usual 20-a-day floor and the quiet rule.

## 5. Tracked narratives that failed their headline audit
`docs/research/narrative-audit/README.md` (20 Oct 2026): copper 16%, OPEC+ 20%, crop weather 44%, gold 44% precision. Offer once per review until settled: keep (labelled low precision), narrow (re-measure a tighter definition: round 3 showed precise ones run 2-9 articles a day), or retire.

## 6. Close
Log: `python -m pmstack log --step narratives:review --fields '{"day":"<day>","shown":<n>,"promoted":<n>,"watched":<n>,"dismissed":<n>}'`. Commit `data/narratives` and `logs`, pull --rebase, push.
