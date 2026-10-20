---
name: research
description: Bernardo's research loop (agent 12) - test an idea, a paper or one of the agents' flags on public data behind the quant gate (pre-registered, base rate and lift, placebo, BH across every test ever run, costs, look-ahead checks), give a verdict and keep the graveyard. Use when he asks "does X predict Y?", "test/replicate this paper", "is the crowding (or CTA, narrative) flag any good?", "what's in the graveyard?", or to re-run the studies.
---

# Research loop (agent 12)

**Why this shape** (docs/research/research-loop.md): agents can test hundreds of ideas, so the bottleneck is the overfitting control, not ideas (Two Sigma; Man's AlphaGPT runs the same committee for human and AI research). Every trial is counted (Harvey, Liu & Zhu; Bailey & López de Prado), binary flags are judged by lift against their base rate on independent episodes (Kaminsky et al.'s signals approach), and published effects shrink 26–58% (McLean & Pontiff). An LLM recalls index levels almost exactly before its cutoff (Lopez-Lira, Tang & Zhu), so **code computes every number and the model never sees an outcome before the registration is frozen**.

## Rules
- **Register before running.** A study is a YAML in `research/studies/` (fields: `python -m pmstack research flags` lists what code can test). It is hashed at registration; an edit after that is a new id (`_v2`), never an overwrite. A sign flip after seeing a result is a new study, judged on later data.
- **Before the run, write the recall probe** in the registration: your honest guess (yes/no/unknown and a probability) of whether it will pass. Never look at prices, results or other studies' outputs before registering.
- **Queue by rule**, not by what you remember worked: the agents' own flags, papers Bernardo names, ideas from his journal.
- **No numbers from memory or the web.** Figures come only from `research/results/<id>.json` or `research/index.md`.
- A new kind of flag or strategy needs code in `pmstack/research.py` (a function in the catalogue, with an offline test) before it can be registered. Say so and stop; don't approximate it in a prompt.
- Verdicts: `supported` (all gate rules hold: ≥ 20 independent episodes, placebo p ≤ 5%, BH q ≤ 10% across every registered flag study, lift ≥ 1.25 or excess ≥ 0.10 sd, same sign in both halves and with any one year dropped; an imported idea also t ≥ 3; the definition unchanged since its first hashed run), `no edge`, `reversed` (the same gate passed in the other direction), `in-sample only` (would pass, but the flag's definition was written with that history in view, e.g. the narrative queries: live episodes decide), `insufficient` (too few episodes; says the smallest lift it could detect), and for strategies `decayed` (worked in the paper's sample, not after publication). Only `supported` flags may alert, and even then they are context, not signals or trade instructions.
- **Quote the index, not a stale page.** `research run` ends by rebuilding the index, which rewrites every result page with the verdict after the whole family; quote verdicts from `research/index.md` or a page rebuilt after the last run. A run with `--no-write` is still a ledger line (a "peek").
- Write audited summaries outside `research/results/` (the auditor leaves a `.audit.json` beside the file it checks).

## Testing an idea
1. Check it fits the catalogue: `python -m pmstack research flags`. If not, stop and say what code it needs.
2. Draft the YAML (id, title, kind, flag + params or strategy, outcome, horizon_days, expected direction: 1, -1 or 0 for two-sided, hypothesis, source with dates, registered, registered_by, queue, recall_probe). Imported ideas (a paper, a podcast claim) also get `paper:` with `published` and `sample_end`.
3. `python -m pmstack research new <file.yaml>` (refuses an existing id).
4. `python -m pmstack research run <id> [--date D]` → `research/results/<id>.md` and `.json`, the ledger line, and the index rebuilt.
5. Answer in at most five lines from the result page: episodes, base rate vs hit rate and lift (shrunk), placebo p and BH q, the verdict with its failing rules, the strongest caveat. Label any reading as inference.
6. Audit any written summary: `python -m pmstack audit <file> --facts research/results/<id>.json`.

## Re-running and reading
- `python -m pmstack research run --all [--date D]` re-runs every study on the latest data (the same frozen specs; each run is a ledger line). `python -m pmstack research index` rebuilds `research/index.md` and `research/verdicts.json` (the Risk section and the critic card read the latter).
- `python -m pmstack research list` and `research show <id>` for a quick look; the graveyard is the second half of `research/index.md` and is never pruned.

## Log
`new` and `run` log themselves (`research:new`, `research:run`). After answering: `python -m pmstack log --step research:answer --fields '{"study":"<id>","verdict":"<v>"}'`.
