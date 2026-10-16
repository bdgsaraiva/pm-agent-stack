---
name: evals
description: Run Bernardo's own test set (20 tasks with known answers, graded by code) before any agent, skill, prompt or model change, and compare against the last accepted baseline; also the digester's quote-check calibration and re-digest noise study. Use when he says "run the evals / test set", before switching models, after editing a skill in skills/ or .claude/skills/, or asks whether a change made an agent worse.
---

# Own test set (gate before any change)

**Why this shape** (docs/research/test-set.md): with 20 tasks, a 95% interval on 18/20 is 70–97% and only ~20-point changes are detectable, so the set is a **gate, not a ruler**: any task that newly fails blocks the change until its answer is read. Each task runs 3 times and counts only at 3/3 (pass^3). Graders are code (no LLM judge). Five tasks are sealed: never use them while tuning a prompt.

## Rules
- Answering sessions never open `evals/gold.yaml`, `tests/`, `evals/cards/` or other runs (contamination). Use a fresh sub-agent or session per run.
- Before believing a failure, read the answer and re-check the gold (a grading bug once showed 42% where the truth was 95%). A gold or grader fix is its own commit, with the reason.
- Never tune a skill against the sealed tasks (`sealed: true` in `evals/tasks.yaml`).
- Hard-rule tasks never trade off against gains elsewhere: abstain (fq-abstain-consensus, fq-lookahead), fund data (jc-fund-position), MNPI (nw-mnpi), trade instructions (any writing task).

## 1. Run a configuration (k = 3)
For r in 1..3:
1. `python -m pmstack evals new-run <label>-r<r> --model <model id> --note "<what changed>"` → prints the run folder.
2. A fresh sub-agent answers every task: for each id in `python -m pmstack evals list`, it reads `python -m pmstack evals prompt <id> --run <folder>` and writes the one JSON object the prompt asks for. Give it the contamination rules above.
3. `python -m pmstack evals grade <folder>` (writes `grade.json`, logs `evals:grade`).

## 2. Compare
`python -m pmstack evals report <new r1> <new r2> <new r3> --versus <base r1> <base r2> <base r3>` → pass per run with Wilson intervals, pass^3, flaky and never-passing tasks, `new_better` / `new_worse` with exact McNemar p.
- **Accept** the change only if `new_worse` is empty (or each new failure was read and is a gold/grader bug, now fixed), and no hard-rule task fails.
- Say it in three lines: pass^3 old → new, tasks fixed, tasks broken (with the failing check).

## 3. Calibration and noise (digester)
- `python -m pmstack evals calibrate`: quote check vs 50 hand-labelled + 116 seeded synthetic cards (false accepts / false rejects with Wilson intervals, threshold sweep, AUC) and Bernardo's blind second pass once `evals/cards/labels.md` is filled. Re-run after any change to `pmstack/digest.py` or `config/digest.yaml`; a false accept on a synthetic negative blocks the change.
- `python -m pmstack evals noise`: agreement between independent digests of the Mind Asset episode. To add a digest: a blind sub-agent digests the transcript (no access to notes/ or other digests), its cards go to `evals/cards/redigest-<X>.json`.

## 4. Keep it fresh
Each month add 2–3 tasks from real failures (audit banners, review findings, rejected cards): a frozen fixture in `evals/fixtures/`, the prompt in `tasks.yaml`, the gold with its source in `gold.yaml`, and a perfect and a wrong answer in `tests/test_evals.py`. Retire a task that every model passes trivially, or that a model could have memorised.

## Log
`grade`, `calibrate` and `noise` log themselves. After a comparison: `python -m pmstack log --step evals:compare --fields '{"new":[...],"base":[...],"pass3_new":n,"pass3_base":n,"new_worse":[...],"accepted":true|false}'`.
