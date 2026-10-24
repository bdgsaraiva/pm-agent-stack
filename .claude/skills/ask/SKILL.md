---
name: ask
description: Bernardo's fundamentals pillar (agent 12 "Research": orchestrator + read-only Energy, Metals, Ags and Macro-context specialists + the research generalist). Use when he types /ask, or asks a fundamentals question about a commodity ("how tight is crude?", "what does the EIA report usually do?", "why is the WTI spread wide?", "what would change the gasoline view?"). Not for trade timing, sizing or narratives (those go to /journal, the critic and /narratives).
---

# /ask: the fundamentals pillar

**Why this shape** (docs/research/specialists-architecture.md, docs/research/energy.md): LLM agent systems that time trades fail out of sample (FINSABER; Profit Mirage). The one controlled commodity test gained only as a constrained layer returning a JSON contract (Wang et al. 2026). An orchestrator that checks its specialists' work holds error amplification to 4.4× (Kim et al. 2025). So code routes, code computes every figure, the specialist only interprets inside a state card, and code validates the card and the answer.

## Rules
- **Read-only.** Never edit `knowledge/`, `data/`, the journal or any config while answering. Code saves the card.
- **Numbers only from the pack** (`cards/_packs/<date>-<specialist>.json`), each cited as `[sN]`. No figures from memory, the web or the knowledge files' prose (those give method and sources, not live levels). If a figure you need is not in the pack, say what is missing; don't estimate it.
- **Facts vs inference.** Label interpretation "Read:". Contemporaneous base rates (release-day reactions) explain moves; they never predict. No trade instructions, no price targets, no sizing.
- **Literature sizes** in `drivers.md` may be quoted with their citation as context. Mark them "literature" and never mix them with the pack's live figures.
- **Personal build:** public data only. Bernardo's priors appear only once he has confirmed them (`knowledge pending` lists the unconfirmed ones; never use those).

## Steps
1. **Route.** `python -m pmstack route "<question as typed>"`. It returns the specialist, commodities, question types and the files to read. Then:
   - if `specialist` is null, reply with the router's `note` (not built yet, or another pillar) in one line and stop;
   - if `also` is non-empty, answer from the first specialist and name what the others would add (the generalist arrives in S6).
2. **Pack.** `python -m pmstack specialist pack <specialist> --question "<question>" [--date D]`. Note its `gaps` (e.g. curve: collection started 24 Oct 2026) and the fact-pack date it used.
3. **Read.** The specialist skill (`skills/specialist-<complex>/SKILL.md`), then only the files in `read`. Don't load other commodities' folders.
4. **Card.** Write the card JSON (schema `config/state_card.schema.json`) from the pack's `card_template`. Fill `balance_view`, `curve_shape`, `positioning` and `narrative_stage` with text that cites `[sN]`. Add `what_changed` (since the previous card: `python -m pmstack cards latest <subject>`), 1–6 `would_change_view` items, the pack's `next_events`, `confidence`, optional `inference` and `open_questions`. Copy `sources` from the pack: only the ids you cite, unchanged. Use `confidence: low` where the pack has gaps. Save to a temp file, then:
   `python -m pmstack cards save <file> --pack <pack.json>` (every source must be a row of the pack, copied unchanged). If it rejects the card, fix each problem once (usually an uncited figure: cite it or drop it) and save again.
5. **Answer** in chat in at most eight lines: the direct answer first, figures with `[sN]` and their links, "Read:" for inference, and one line on what would change the view. Write the same text to `cards/answers/<date>-<slug>.md` with a YAML header (`question`, `card`, `pack`).
6. **Audit.** `python -m pmstack audit cards/answers/<file>.md --facts <pack.json> <card.json> --flag --step audit:ask`. Fix each orphan once from the pack, then re-run.
7. **Log.** `python -m pmstack log --step ask:<specialist> --fields '{"question":"...","card":"<path>","pack":"<path>","sources_cited":<n>,"gaps":[...],"audit":{"checked":<n>,"orphans":<n>}}'`.

## Not this skill
- "Should I buy/sell/size": that goes to `/journal` (critic card and sizing), Bernardo decides.
- "Is this narrative growing": that goes to `/narratives` and the Consensus map (agent 7).
- "Is the trend stretched / vol / CTA": that's the quant pillar (agent 13, S2). Until then, the Risk and crowding section of facts.md.
- "Does X predict Y": that's the testing gate, `/research` (pre-registered study).
