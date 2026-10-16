# Session notes A12: own test set and balance keeper (agent 9), 16 Oct 2026

Literature reviews (Docs): test set https://claude.ai/code/artifact/c562b35f-b3fa-4cae-bcce-28e27eabde06 · balance keeper https://claude.ai/code/artifact/295b460b-e2d8-4c56-a793-b3b679988baa · repo: `docs/research/test-set.md`, `docs/research/balance.md`
Branch: `agents-10-11` (Claude Code on Bernardo's PC). Commits f974a01 (code), 68cc44b (docs); main merged in at a1c9f0b and 63d4256.

## Context
- **Gate 1 Nov not met:** 1 journal entry (the example), 0 of 10 paper ideas; 0 of 2 Friday reviews (the first runs tonight). Bernardo: "Build anyway".
- **His answers:**
  - agent 9 v1 covers oil and grains;
  - markets: corn, soy, wheat and sugar (he removed coffee);
  - output: a fact-pack section plus critic facts.
- **Research:** three research sub-agents (test-set evals; balance papers; balance data and practice), two blind re-digest sub-agents, three baseline answering sub-agents and two independent reviewers. Two research agents stalled on a watchdog and were resumed. The agent 9 reviewer hit the account's session limit and was resumed after 15:40 BRT.
- **Ownership:** the other session (notes and keys) pushed to main during the day: narrative v2, a new `gdelt_bq_v2` block in sources.yaml, and monitor.py. Main was merged into this branch twice, with only `logs/runs.jsonl` conflicting (kept the union, ordered by timestamp). I edited no files it owns; agent 9's sources live in `config/sources.d/`.

## What the evidence said (short)
- **Test set** (~40 sources):
  - with 20 tasks, 18 of 20 passing has a Wilson interval of 70–97%, so it is a gate, not a ruler;
  - a newly failing task blocks a change until its answer is read;
  - k = 3 runs, scored pass^3 (tau-bench), five sealed tasks (Varma & Simon; Leeflang);
  - code graders only (LLM judges have order and verbosity bias);
  - a quote that is present is not a claim that is supported (Zhang et al. 2026: 98% verbatim, 37% supported).
- **Balance keeper** (~80 sources):
  - storage theory: low stocks go with backwardation and volatility, non-linearly (GHR; Symeonidis);
  - inventories mostly carry precautionary demand (Kilian & Murphy);
  - GHR's "normal" uses future data, so ours is the trailing EIA same-week convention;
  - no free consensus exists, and naive surprises understate price responses (Halova et al.);
  - stocks-to-use is a consistency check whose curve shifts by regime (Good & Irwin; Janzen);
  - WASDE CSVs are first-published vintages and carry USDA's own reliability tables, plus World Less China lines.

## What shipped
**Own test set** (`pmstack/evals.py`, `evals/`, skill `.claude/skills/evals/` + `/evals`)
- 20 tasks: 7 fact-pack questions (2 must abstain), a morning-note paragraph, 4 journal captures (fund position refused, missing invalidation asked), critic wording, 3 digester tasks, 2 network tasks (MNPI refused; no phone, ids only), the weekly goal, the sizing line. 5 sealed.
- Frozen fixtures, gold in `evals/gold.yaml`, graders in code (auditor, the agents' own validators).
- `new-run` records `skills_hash` and `git_head`; `grade` stores `grader_hash` and re-grades when graders change; `report <new> --versus <base>` gives pass^3, flaky tasks, `new_worse` and exact McNemar.
- `calibrate`: 50 hand-labelled cards plus 198 seeded synthetic variants, a threshold sweep, AUC, and Bernardo's blind second pass (kappa). `noise`: independent digests matched by quote span.
- **Digester fixes** (agent 10), each from a measured failure:
  - fillers and repeats are ignored;
  - a replaced word blocks unless it is a spelling variant without a negating prefix;
  - an added word or a dropped qualifier blocks;
  - a lead-in hedge in the same sentence blocks (`hedge_cut`);
  - "no caso de" is not a hedge; "acho que" and "I think" are required hedges;
  - `sparse_windows` density check (5 cards per 1,000 words);
  - skill text: extract every claim, the claim says only what its quote says, and keep "pode" in `hedge`.
- **Other fixes:**
  - `critic.validate_questions` split out of `save`, and a question must have text and a "?";
  - the auditor reads "through/throughout/during 2015–2039" as structure.

**Agent 9 — balance keeper** (`pmstack/balance.py`, `config/balance.yaml`, `config/sources.d/balance.yaml`, skill `.claude/skills/balance/` + `/balance`)
- **Sources** (Actions only; time budgets 240/300/180 s):
  - `eia_bal`: 15 more WPSR series via the existing EIA adapter;
  - `wasde`: CSVs from 2021, as first published, mirror fallback, no key;
  - `usda_psd`: from 2007/08, world, China, US, world sugar;
  - `nass`: crop condition and Grain Stocks, dated at release.
  - `fetch.py` merges `config/sources.d/*.yaml`; offline tests skip it via `PMSTACK_NO_SOURCES_D`.
- **Section:**
  - oil stocks vs the prior-5-year same week (level, range, position, z, change vs the 5-year change, days of supply);
  - 4-week flows vs the same 4 weeks of the last 5 years;
  - the crude adjustment flag (band since the Nov 2023 break);
  - grains and sugar: US stocks-to-use, revision vs the previous report beside USDA's average miss (converted from metric tons), old crop beside new, the stocks-to-use percentile since 2007/08 (PSD), world and world ex-China (WASDE);
  - NASS condition (key months July–August) and quarterly stocks;
  - every number from its availability date.
- **Alerts:** `balance_range`, `wasde_revision`, `crop_condition`. **Critic:** `bal.*` facts and a "balance" counter basis (severity 1.4).
- **Probe:** `.github/workflows/balance-probe.yml` runs on push to `agents-*` (fetch + section + artifact; commits nothing).

## Results
- **Re-digest noise:** blind A vs B match 51 claims (89% / 86%), type kappa 1.0, hedge agreement 90%. The 15 Oct digest vs blind: 86–93% of its claims found, but only 22–23% of theirs, so it under-extracted (3.3 vs 13–14 cards per 1,000 words).
- **Quote check:**
  - 15 Oct rules: 7 of 21 hand-labelled unfaithful quotes accepted, and 144 of 167 synthetic;
  - now: 0 of 21 (Wilson ≤ 15.5%) and 0 of 167 (≤ 2.2%);
  - faithful rejected: 1 of 29 hand-labelled, 0 of 31 synthetic;
  - threshold 0.85 kept (flat from 0.60 to 0.85); ratio AUC 0.874;
  - 9 of 28 code-ok cards carry a claim the quote doesn't support (cross-language: a judge or checker is optional, review flags only).
- **Baseline** (claude-opus-5-5, three fresh runs): 18, 19 and 20 of 20; pass^3 18 of 20.
  - Flaky: `dg-window-extract` ("pode" not in `hedge`, a skill gap now fixed) and `nw-debrief` (contact id as follow-up owner).
  - A first grade had two more "failures" that turned out to be a grader bug and an auditor gap: the read-before-believe rule worked.
  - The next run under the current skills is the first clean baseline.
- **Agent 9 local run** (repo EIA history + real WASDE files, Aug–Oct 2026):
  - US distillate stocks for the week to 9 Oct were 102,611 kbbl, 11.1% under the 2021–2025 same-week average (−1.9 sd) and below the range;
  - the 9 Oct WASDE put 2026/27 US corn ending stocks at 1,849 mbu, +282 vs September, inside USDA's average October miss of 331;
  - corn stocks-to-use 11.3%, world / ex-China 21.2% / 11.6%.
- **Agent 9 live probe** (Actions, with the repo secrets): EIA, WASDE and NASS work; PSD answers HTTP 500. See "Live probe" below.

## Independent reviews
- **Test set** (22 defects: 3 High, 12 Medium, 7 Low), all fixed or documented, each with a regression test. The High ones:
  - `report --versus` read the direction backwards (a regression would have been accepted);
  - the alert-ref check was a substring test ("#10" passed for "#1");
  - empty critic questions passed (`critic.save` too).
  Details in `docs/research/test-set.md` §6.
- **Agent 9:** see "Agent 9 review" below.

## Live probe (GitHub Actions, `balance-probe.yml`, commits nothing)
- **Run 1** (38950622177):
  - WASDE: 99,843 rows from 70 reports, 2021-01 to 2026-10 (no file for 2025-10, the shutdown), in 92 s;
  - NASS: 1,885 rows (crop condition from 2014, quarterly stocks);
  - `eia_bal` failed whole: `PET.WCRAUUS2.W` (crude adjustment) is on EIA's site but not on the API;
  - PSD: HTTP 500.
  - **The failed EIA call printed the API key into the run-log line**: the shared `base.get` error text quoted the URL. The artifact is private to the repo; nothing with a key was ever committed (checked the log and its history).
- **Fixes:**
  - keys redacted in every HTTP error, in the run log and on the console;
  - one bad EIA id no longer drops the block;
  - the adjustment line moved to v2;
  - a PSD attribute fallback and a circuit breaker.
- **Run 2** (38951598305):
  - `eia_bal`: 13 of 14 series stored (crude days of supply hit a transient 504), so flows and implied demand now show;
  - WASDE and NASS: OK;
  - PSD: **HTTP 500 on every call with the key** (403 without it), so the paths exist and the key or the service is the problem.
- **Live numbers** (16 Oct, from the probe's section):
  - 4-week implied demand: total products 21,077 kbd, +3.2% vs the same 4 weeks of the last five years; jet +5.5%;
  - NASS 1 Sep stocks: corn 2,095.1 million bu (+35.1% y/y), matching WASDE's 2025/26 ending stocks of 2,095;
  - corn condition 56% good/excellent (week to 11 Oct).

## Agent 9 review: 14 defects (3 High, 1 Medium/High, 5 Medium, 1 Low/Medium, 4 Low) + nits, all fixed or documented
A sub-agent that didn't build it checked the code against 16 real WASDE files and the repo's EIA store. Each fix has a regression test in `tests/test_balance.py` (25 tests).
1. **(High)** The 5-year change was mis-paired at the turn of the year (+20,589 kbbl instead of about zero on 8 Jan). Now uses the monitor's definition, so both tables show the same number (+2,873 for the 9 Oct week).
2. **(High)** One bad EIA id dropped the whole block → errors are per series.
3. **(High)** API keys in error text → redacted in `base.get`, in `runlog.log` and on the console.
4. **(Medium/High)** PSD history never finished after a first run that ran out of time → per-pair progress file (`data/obs/usda_psd/_progress.json`), resumed every run.
5. The daily job's time budget → PSD stops after 3 failures in a row (run 2 lost 5 minutes to HTTP 500s); its budget is cut to 180 s. Run 2 took ~8 minutes in total, most of it PSD's failures.
6. The auditor could not match balance z-scores (`z` read as a level) → fields renamed `z_sd` and `band_z`.
7. World stocks-to-use was labelled "(PSD)" when it came from WASDE → the label and link follow the source.
8. The US sugar balance (#16, protected market) was attached to SB=F (world #11) → US sugar is shown in the table but kept off the critic; SB=F gets the world line.
9. New-source failures were silent → WASDE HTTP errors are errors; the section lists stale or missing sources (`stale_days`).
10. Monday-holiday EIA weeks were visible a day early in backdated packs → `eia_late_weeks` (+1 day). The Dec-1 grain stocks released late in the 2019 shutdown are documented, not modelled.
11. Corrected WASDE files could replace first prints → the original is fetched first; `-V2` only when it is the only file.
12. Range position ran outside 0–100 with a 0–100 label → the label says what below 0 or above 100 means.
13. The US sugar percentile was never computed → the use names now match.
14. The PSD fallback attribute ids are unverified → marked as such in the code and the fetch notes.
Nits fixed: "-%" cells, and the probe input now reaches the shell through an env var with a date check. Noted, not changed: the monitor's own EIA table has no release lag (it predates agent 9), so a rebuilt early-week pack can show a later week there than in Balances.

## Open items
- **Bernardo:**
  - blind second pass on 20 cards (`evals/cards/labels.md`, Y/N columns), then `python -m pmstack evals calibrate` reports kappa;
  - merge `agents-10-11` into main (the daily job, morning note and Friday review run on main);
  - the private `pm-network` repo (from A11).
- **Bernardo: the FAS PSD key.** Every PSD call with `USDA_FAS_API_KEY` answers HTTP 500 (403 without it), with the header, X-Api-Key and query forms all tried. Check on the FAS OpenData site (https://apps.fas.usda.gov/OpenData) that the key is active and that it is the FAS key, not another api.data.gov key; replace the repo secret if needed. Until then the stocks-to-use percentiles and world sugar are blank; the circuit breaker keeps PSD to seconds a day.
- **Bernardo: the EIA key** appeared in the private probe artifact of run 38950622177 (retention 14 days). Delete that artifact in the repo's Actions page, or rotate the EIA key, as you prefer; the code no longer writes keys anywhere.
- **Next clean baseline:** one `/evals` run (k = 3) under the current skills.
- **Digest tasks:** move to a second episode (contamination: the Mind Asset cards are in the repo); label 20 cards there as the true hold-out.
- **Agent 9 v2:**
  - STEO quantities as a monthly expectation;
  - ESR export sales pace;
  - Grain Stocks vs WASDE-implied stocks;
  - condition-implied yield;
  - a seasonality test per series;
  - curve spreads (no free back months);
  - time-to-confirmation of an imbalance (Hall).
  - Re-test the EIA adapter after 21 Oct (WPSR table changes).
- **Morning note (other session):** may quote Balances exceptions (range breaks, WASDE revisions ≥ USDA's average miss); the skill is theirs.
- **PM Agent Plan doc: updated from this session (16 Oct):** roster row 9 → Running, with trigger, inputs and job; the lead now names eleven running agents plus the own test set, with links to both new review pages. Not changed: the build-schedule paragraph and chart (the test set and agent 9 landed 16 Oct, ahead of their Dec/Jan slots), and there is no per-agent spec section for 9; both are left for a claude.ai chat.
