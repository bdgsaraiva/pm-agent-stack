---
title: Own test set — literature review and first results
agent: own test set (cross-cutting; gate before any agent or model change)
date: 2026-10-16
status: reviewed before build; code in pmstack/evals.py, tasks in evals/, digester changes in pmstack/digest.py + config/digest.yaml
docs: https://claude.ai/code/artifact/c562b35f-b3fa-4cae-bcce-28e27eabde06
---

# Own test set — literature review and first results

**Answer.** Twenty frozen tasks with known answers, graded by code, form a **gate, not a ruler**. At n = 20, 18 of 20 passing has a 95% Wilson interval of 70–97%, and the smallest change it can reliably detect is about 20 points. So the decision rule is not a significance test: **any task that newly fails blocks the change until someone reads the answer** and either fixes the task (a gold or grader bug) or accepts the regression. Each task runs 3 times and counts only at 3 of 3 (pass^3); 5 of the 20 are sealed and never used while a prompt is tuned.

The two calibration studies paid for themselves on day one:
- **Quote check.** On 50 hand-labelled cards, the 15 Oct digester rules let 7 of 21 unfaithful quotes through (every one-name swap, at ratios of 0.89–0.96). On 198 seeded synthetic variants they let 144 of 167 unfaithful ones through. No threshold can fix this, because the swaps score higher than honest filler cleanup. A changed-word guard fixes it: 0 of 21 and 0 of 167 now pass (Wilson upper bounds 15.5% and 2.2%), and 0.85 stays as the threshold. Caveat: the hand labels and the rules come from the same session, and the synthetic kinds are ones I chose. The guard has not met an attack it wasn't built for; the next episode's labels are the real hold-out.
- **Re-digest noise.** Two blind re-digests of the Mind Asset episode agree with each other: 89% and 86% of claims shared, type kappa 1.0. The 15 Oct digest kept 14 claims where they kept 57 and 59. The noise is **omission**, which the one-card-per-window coverage check could not see.

Method: one research pass on 16 Oct 2026 (~40 sources opened; "abstract" = only the abstract read, "secondary" = someone else's summary), then the studies on the repo's own data. Book points not page-checked are marked.

## 1. Papers: what a test set with known answers needs

| Finding | What it changes | Source |
|---|---|---|
| FinanceBench: 10,231 questions, each with an answer and an evidence string, written by analysts with 10–20% of their work re-checked. Responses are scored correct / incorrect / **failed to answer**. | Each task has an answer, a source pointer and a grader. Abstaining is scored as its own outcome, and two tasks require it: a missing consensus and a date after the as-of. | Islam et al. 2023 (read) |
| With the evidence page handed over, GPT-4-Turbo still got 15% wrong. Moving the context after the question changed long-context accuracy from 78% to 25%. | Tasks test the reading step, not only retrieval. Prompt layout is a hidden variable, so the shared rules are fixed text printed by `evals prompt`. | Islam et al. 2023 (read) |
| FinQA's gold answers are programs scored by execution. | The gold for each task is copied from a frozen fixture or computed by repo code on it (`gold.yaml` names the source). | Chen et al. 2021 (abstract; repo README read) |
| Domain traps (units, levels vs probabilities) are where finance models fail (BizBench). | Traps are planted: a seasonal norm that looks like a consensus, a spot-future gap that looks like a data error, a fund position, MNPI, a phone number. | Koncel-Kedziorski et al. 2023 (abstract) |
| Below a few hundred items, normal-approximation intervals under-cover (a nominal 95% covers ~92.5% at N = 100). Use Wilson, or a paired method for comparisons. | Wilson intervals everywhere. Two configurations are compared task by task (discordant tasks, exact McNemar). | Bowyer, Aitchison & Ivanova 2025 (read) |
| Questions that share a source are not independent; comparisons should be paired; run a power analysis first; don't lower temperature just for the eval. | Tasks name their fixture (cluster). The report says what 20 tasks can and cannot detect. Runs use production settings. | Miller 2024 (read) |
| pass^k is the chance that all k trials succeed. gpt-4o scored pass^1 61 on retail but pass^8 under 25. Ambiguous tasks were found by running each one many times. | k = 3 runs. Tasks that pass sometimes are listed as **flaky** for review. | Yao et al. 2024, tau-bench (read) |
| Start with 20–50 tasks drawn from real failures. Prefer code graders. A regression set should sit near 100%, apart from capability sets. A 0% pass rate usually means a broken task, and one grading bug once showed 42% where the truth was 95%. | 20 regression tasks graded by code, and every failure is read before it is believed. New tasks come from real failures (audit banners, review findings). | Anthropic 2026, "Demystifying evals for AI agents" (read) |
| Binary labels; align any judge with human labels in batches of 25–50; report precision and recall separately. | Pass/fail per check. The card set (50) is one such batch. | Husain 2024 (read); OpenAI eval best practices (read) |
| Leaked test items inflate scores a lot (e.g. 38.8 → 81.9). | Gold answers live only in `evals/gold.yaml` and `tests/test_evals.py`; answering sessions are told never to open them, `tests/` or `evals/cards/`. | Zhou et al. 2023 (read) |
| Add new dated questions monthly; scores track how recent the items are relative to training cutoff. | Two or three tasks a month from real failures. Each task carries its as-of date. | White et al. 2024, LiveBench (abstract); Roberts et al. 2023 (abstract) |
| Lookahead propensity: forecasts are contaminated where the model recalls the outcome. | Judgement tasks use dates after the model's cutoff, or extract-only tasks. Ours are extract, compute or follow-a-rule tasks on supplied files. | Gao, Jiang & Yan 2026 (PDF intro); Glasserman & Lin 2023 (abstract) |
| Test sets carry ≥ 3.3% label errors on average, and rankings flip on the mislabelled subset. | One wrong gold answer is 5 points at n = 20. Every gold value is re-derived from its fixture by code in `test_perfect_answers_pass`, and a model's failure triggers a gold re-check first. | Northcutt, Athalye & Mueller 2021 (read) |
| Tuning a cut-off on the same small sample flatters it: ~90% estimated vs 84% true at n = 40. Cross-validation after model selection is biased; nested CV is not. | Five sealed tasks are never used while tuning. The quote rules were set on the hand-labelled cards, so the seeded synthetic set (built afterwards) is the out-of-sample check. | Leeflang et al. 2008 (abstract); Varma & Simon 2006 (read) |
| Counterpoints: benchmarks saturate (Dynabench); metrics invite gaming (Goodhart); in the METR trial AI made developers 19% slower while they felt faster. | The test set gates regressions. Usefulness is judged on real use: audit banners per note, cards Bernardo rejects, time to publish. | Kiela et al. 2021; Thomas & Uminsky 2022; Becker et al. 2025 (abstracts) |

## 2. Papers: labels, noise and the quote check

| Finding | What it changes | Source |
|---|---|---|
| Noise audit: give the same case to several judges independently. Underwriters' premiums differed by a median of 55%, five times what executives expected. | The re-digest is a noise audit of the digester: same transcript, independent runs, no gold needed to measure the scatter. | Kahneman, Sibony & Sunstein 2021 (secondary); HBR 2016 (intro) |
| LLM coders: 91–97% self-agreement (Gilardi). But a one-word instruction change drops alpha to ≤ 0.6, and a majority of runs raises it (Reiss). | Same-prompt runs measure occasion noise only. Any skill edit is a "change" that triggers the test set. | Gilardi et al. 2023 (read); Reiss 2023 (PDF) |
| Use chance-corrected agreement; 0.8 reliable, 0.67–0.8 tentative; a skewed class makes kappa meaningless, so stratify. | Agreement is reported as kappa with raw agreement. The labelled set is stratified (21 negatives of 50). | Artstein & Poesio 2008 (PDF sections 3–5) |
| FactCC builds negatives by rule (entity swap, number swap, negation) and positives by noise injection; crowd labels were unreliable (kappa 0.16). | `evals.synthetic()`: seeded variants with known labels. The gold labeller for real cards is Bernardo (blind second pass in `evals/cards/labels.md`). | Kryscinski et al. 2019 (PDF) |
| TRUE reports ROC AUC because it needs no threshold. SummaC tunes thresholds per dataset; MiniCheck's 0.5 barely needs tuning because its scores sit at the extremes. | `calibrate` reports the ratio's AUC (0.874 here) and the full sweep. The difflib ratio is not bimodal, so a threshold alone was never going to be enough. | Honovich et al. 2022 (read); Laban et al. 2022 (read); Tang, Laban & Durrett 2024 (read) |
| Verbatim citations: 98% of one model's claims carried exact quotes, but only 37.1% were fully supported. Quotes were matched after normalisation, with no fuzzy threshold. | A quote that is present is not a claim that is supported. On our cards, 9 of 28 that pass every code check have a claim adding context its quote does not carry. | Zhang et al. 2026 (read) |
| NLI support checks agree with humans only "substantially" (kappa 0.53–0.70). | An entailment checker would flag cards for review, never reject them, and only if it reaches ≥ 0.80 balanced accuracy on our cards. Not built yet: our quotes are Portuguese and the claims English. | Gao et al. 2023, ALCE (read) |
| AIS: label "interpretable?" first, then "supported?". | Two labels per card: quote faithful, claim supported. | Rashkin et al. 2021/23 (read) |

## 3. Atlas (investor and firm cards)
- **Key finding 15**: the edge moves to "evaluation discipline" because the models are shared. The test set is that discipline.
- **Balyasny**: models scored on 12+ dimensions, including robustness to noisy inputs → digest tasks run on raw auto-captions.
- **BlackRock (Aladdin Copilot)**: every prompt change goes through automated tests → the rule here: any agent, skill or model change runs the set.
- **Man Group (AlphaGPT) / Two Sigma**: agent output passes the same look-ahead and multiple-testing checks as human research; "the bottleneck becomes your overfitting controls" → sealed tasks; rules tuned on one set, checked on another.
- **Bridgewater**: judged on live capital, not benchmarks → real-use metrics sit beside the gate.
- **HRT**: every complex model must beat a simple baseline → the 15 Oct digester rules are the baseline the new quote check is measured against.

## 4. Where sources disagree, and the resolution
1. **Error bars.** Miller says use clustered normal-approximation errors; Bowyer says they fail below a few hundred items. → Wilson intervals, kept paired and clustered.
2. **Temperature.** Miller says don't lower it for the eval; Reiss shows low temperature raises consistency. → Evaluate at production settings.
3. **LLM consistency.** Gilardi says high; Reiss says fragile to wording. → Both are true, and consistency is not validity. Re-digest agreement (A vs B) is high; accuracy needs labels.
4. **Thresholds.** MiniCheck uses a fixed 0.5; SummaC tunes per dataset; TRUE uses AUC. → Our ratio's AUC is 0.874, so it separates the classes only partly. A word-level guard does the work, and the threshold is left where any value from 0.60 to 0.85 gives the same result.
5. **Benchmarks vs live results.** Anthropic and OpenAI centre development on evals; Bridgewater and METR point to live outcomes. → The gate catches regressions; real use judges value.

## 5. Design (what was built)
- **20 tasks** (`evals/tasks.yaml`) across 7 agents:
  - fact-pack questions ×7, including abstain on a missing consensus and abstain on a date after the as-of;
  - morning-note paragraph ×1 (audited);
  - journal capture ×4: full; missing invalidation; fund position, which must be refused; pass, which goes to reject;
  - critic wording ×1 (the critic's own `validate_questions`);
  - digester ×3: fix a flagged card; an unscoreable forecast; a window extraction scored by recall of claims both blind digests found;
  - network ×2: MNPI must be refused; debrief with no phone number and ids only;
  - weekly goal from the rule ×1, with a tie broken by catalogue order;
  - sizing line ×1.
- **Fixtures frozen** in `evals/fixtures/`: the 16 Oct pack, the example idea's critic card, a synthetic sizing output and scorecard, and fictional contacts. The digest tasks need the local transcript and are skipped if it is missing.
- **Graders in code** (`pmstack/evals.py`): numbers with tolerance, sets, abstention, the number auditor on prose, a trade-instruction regex, and the agents' own validators (`critic.validate_questions`, `digest.check_card`, `network.validate_call`). No LLM judge.
- **Runs**: `evals new-run <label> --model <id>` → a fresh session answers each `evals prompt <id>` → `evals grade <run>`. `evals report r1 r2 r3 [--versus …]` gives pass per run, pass^3, flaky tasks, and paired discordant tasks with exact McNemar.
- **Sealed**: 5 tasks (fq-open-idea, jc-pass, dg-unscoreable, nw-debrief, sz-explain).
- **Calibration** (`evals calibrate`): 50 hand-labelled cards (`evals/cards/labelled.json`; label rules inside), 198 seeded synthetic variants (167 unfaithful, 31 noise-only), a threshold sweep, AUC, and Bernardo's blind second pass (`evals/cards/labels.md`, 20 cards → kappa).
- **Noise** (`evals noise`): independent digests matched by quote span (≥ 50% of the shorter span); recall both ways; type kappa; speaker, hedge and deadline agreement.

## 6. Results (16 Oct 2026)

### Quote check (digester, agent 10)

| Rules | Hand-labelled: unfaithful accepted | Hand-labelled: faithful rejected | Synthetic: negatives accepted | Synthetic: positives rejected |
|---|---:|---:|---:|---:|
| 15 Oct (ratio ≥ 0.85 + number/negation/hedge guard) | 7 of 21 (6 name swaps, 1 hedge cut) | 2 of 29 | 144 of 167 (all 22 added words, 40 of 42 word swaps, all 37 negating prefixes, all 45 dropped qualifiers) | 2 of 31 |
| 16 Oct, after the independent review (fillers ignored; a replaced or added word blocks unless it is a spelling variant without a negating prefix; qualifiers like "só" may not be dropped; lead-in hedge check within the sentence) | **0 of 21** (Wilson ≤ 15.5%) | 1 of 29 (a heavy grammar rewrite) | **0 of 167** (≤ 2.2%) | **0 of 31** (≤ 11.0%) |

- Any threshold from 0.60 to 0.85 gives the same result under the new rules; at 0.90 two honest caption fixes are lost. **0.85 kept.**
- **Changes, each from a measured failure:**
  - filler words and immediate repeats are ignored in matching;
  - the span is read past the quote's length, so omitted words don't shift it (the research pass flagged this too);
  - a replaced word must be a spelling variant (character similarity ≥ 0.65: OKR/KKR, head/hedge) or the card is blocked. A spelling variant only warns, and the skill says keep the transcript's spelling in the quote. Words that differ by a negating prefix (possible/impossible, correlacionada/descorrelacionada, inflation/deflation) are never spellings (review);
  - an added word blocks; a dropped qualifier ("só", "apenas", "mais", "only", "all") blocks (review: "não é só no Brasil" without "só" passed);
  - a lead-in hedge ("eu acho que", "I think", "talvez") in the 12 tokens before the span, within the same sentence, blocks (`hedge_cut`) unless the card keeps it. It caught one real case in re-digest B: "Acho que … o Artax Janeiro são super consolidados". "could" and "might" are not lead-ins (they belong to their own clause);
  - "no caso de" is no longer a hedge (both blind runs tripped on it);
  - "acho que" and "I think" are now required hedges.
- **Set on the same labels:** the 0.65 spelling cut and the 12-token window. The synthetic kinds were chosen by the same session, and three of them (negating prefixes, dropped qualifiers, sentence-limited hedges) were added after the independent review found the gaps. So the bounds hold for these attacks only. The real hold-out is 20 labels on a second episode, plus Bernardo's blind second pass on 20 of these cards (`evals/cards/labels.md` → `calibrate` reports kappa).
- **Known gaps:** a quote cut so it starts after a meaning-flipping qualifier ("só no Brasil" → "no Brasil") is an exact span and is not checked, only lead-in hedges are. And "no caso de" + clause ("no caso de o Fed subir") is a real conditional that the `hedge_not` list now skips.
- **Claims:** 9 of the 28 cards that pass every code check carry a claim the quote does not support (context from elsewhere). Code cannot see this across languages. The skill now says the claim says only what its quote says; context goes in `because`/`unless`. A MiniCheck-class or judge pass stays optional, for review flags only.

### Re-digest noise (Mind Asset, 24 min of auto-captions, 4,261 words)

| Pair | Cards | Matched | Recall each way | Type kappa | Hedge agree | Deadline agree |
|---|---|---:|---|---:|---:|---:|
| 15 Oct digest vs blind A | 14 / 57 | 12 | 86% / 23% | 0.73 | 75% | 100% |
| 15 Oct digest vs blind B | 14 / 59 | 13 | 93% / 22% | 0.75 | 69% | 100% |
| blind A vs blind B | 57 / 59 | 51 | 89% / 86% | 1.00 | 90% | 100% |

- **Read:** with the same skill and model, two fresh runs largely agree (occasion noise is small). The first digest was the outlier: it under-extracted, keeping 3.3 cards per 1,000 words against 13–14. Its "every window has a card" check passed.
- **Changes:**
  - `sparse_windows`: windows under 5 cards per 1,000 words are listed (a heuristic floor from one episode; revisit after 5 digests);
  - the skill says extract every checkable claim;
  - `type` is defined so that durations and counts are data. The two type disagreements were "more than 15 years" (opinion vs data) and the partnerships sentence.
- **Not measured yet:** pattern noise (a reworded skill or a second model), and numeric-level agreement (the episode has no market levels). Next: an English commodity episode with stated levels.

### Baseline run of the 20 tasks (claude-opus-5-5, 3 fresh runs, 16 Oct)

| Run | Passed | Wilson 95% |
|---|---:|---|
| r1 | 18 of 20 | 69.9–97.2% |
| r2 | 19 of 20 | 76.4–99.1% |
| r3 | 20 of 20 | 83.9–100% |
| **pass^3** (all three runs) | **18 of 20** | 69.9–97.2% |

- **Flaky:** `dg-window-extract` (2 of 3 runs left "pode" out of `hedge` on 4 cards: a skill gap, now written into the skill) and `nw-debrief` (1 of 3 runs put the contact id as a follow-up owner instead of "them").
- **Read before believed** (the rule worked on day one): a first grade showed 16, 17 and 18 of 20. Two of the "failures" were wrong graders or a wrong auditor, not the model:
  - `fq-abstain-consensus`: all three runs abstained correctly and only named the seasonal norm when explaining why;
  - `fq-spot-vs-future`: "held through 2026" was read as a figure. That is a real auditor gap, so live notes would have been flagged too, and it is now fixed.
- **Not a clean baseline:** the answers came before the "pode" skill line and before the review fixes to the graders. Grades are recomputed under the current graders (`grader_hash`), but the next run under the current skills is the first clean baseline. From now on `new-run` records `skills_hash` and `git_head`, and `report` warns when runs mix them.
- **Contamination:** the digest tasks run on the Mind Asset transcript, and its cards are in the repo (`notes/`, `evals/cards/`, `tests/`). The answering prompt now forbids those paths, but a session that reads them anyway would pass. The digest tasks are therefore a capability probe, not a sealed test. They move to a fresh episode when the next one is digested.

### Independent review (16 Oct): 22 defects, all fixed or documented
A sub-agent that didn't build the test set found 3 High, 12 Medium and 7 Low defects; each fix has a regression test in `tests/test_evals.py`.
- **High:**
  - `report --versus` read the direction backwards, so a regression would have been accepted;
  - the alert-ref check was a substring test ("#10" passed for "#1"; swapped figures passed);
  - an empty critic question passed (`critic.save` too).
- **Medium:**
  - "a likely data glitch" passed the standing-fact check;
  - opposites passed as spellings;
  - a dropped "só" passed;
  - "acho que" vs "eu acho" double-counted;
  - hedge lead-ins crossed sentence ends;
  - the trade-instruction check missed "consider buying" and "- Sell" bullets, and failed "Sell-side";
  - answer paths were left open to the answering session;
  - the calibration claims overstated;
  - MNPI leaks under other words passed;
  - the baseline mixed configurations;
  - sizing figures could be swapped;
  - crowded markets were matched without one-to-one pairing.
- **Low:**
  - a final-word spelling fix was blocked;
  - untimed transcripts were all marked "sparse";
  - the auditor's year rule was too broad ("broke through 2050"); it now covers only 2015–2039 after through/throughout/during;
  - invented stops under other keys passed;
  - `why` was unchecked on the abstain tasks;
  - names were matched as substrings ("Pat" in "anticipate");
  - "no caso de" + clause (documented).

## 7. Worked example
A model change is proposed. Run `evals new-run new-model --model <id>` three times, answer each run in a fresh session, then `evals grade` each one, then `evals report <new r1..r3> --versus <baseline r1..r3>`.

Suppose `fq-abstain-consensus` passed 3 of 3 before and 1 of 3 now. It is listed under `new_worse` and as flaky. The gate blocks the change until the answer is read: the new model called the 5-year same-week average "the consensus", a hard-rule failure (numbers presented as something they are not). The change waits, whatever the McNemar p says (with one discordant task, p = 1.0).

## 8. Sources
Islam et al. 2023 FinanceBench https://arxiv.org/abs/2311.11944 · Chen et al. 2021 FinQA https://arxiv.org/abs/2109.00122 · Zhu et al. 2021 TAT-QA https://arxiv.org/abs/2105.07624 · Reddy et al. 2024 DocFinQA https://arxiv.org/abs/2401.06915 · Koncel-Kedziorski et al. 2023 BizBench https://arxiv.org/abs/2311.06602 · Miller 2024 https://arxiv.org/abs/2411.00640 · Bowyer, Aitchison & Ivanova 2025 https://arxiv.org/abs/2503.01747 · Yao et al. 2024 tau-bench https://arxiv.org/abs/2406.12045 · Liang et al. 2022 HELM https://arxiv.org/abs/2211.09110 · Anthropic 2026 https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents · OpenAI 2026 https://developers.openai.com/api/docs/guides/evaluation-best-practices · Husain 2024 https://hamel.dev/blog/posts/evals/ · Zhou et al. 2023 https://arxiv.org/abs/2311.01964 · Sainz et al. 2023 https://arxiv.org/abs/2310.18018 · Golchin & Surdeanu 2023 https://arxiv.org/abs/2308.08493 · Roberts et al. 2023 https://arxiv.org/abs/2310.10628 · White et al. 2024 LiveBench https://arxiv.org/abs/2406.19314 · Gao, Jiang & Yan 2026 https://yutongyan.xyz/files/a_test_of_lookahead_bias_in_llm_forecasts_nber.pdf · Glasserman & Lin 2023 https://arxiv.org/abs/2309.17322 · Northcutt, Athalye & Mueller 2021 https://arxiv.org/abs/2103.14749 · Artstein & Poesio 2008 https://aclanthology.org/J08-4004/ · Kahneman, Sibony & Sunstein 2021 (secondary) https://en.wikipedia.org/wiki/Noise:_A_Flaw_in_Human_Judgment · Kahneman et al. 2016 https://hbr.org/2016/10/noise · Reiss 2023 https://arxiv.org/abs/2304.11085 · Gilardi et al. 2023 https://arxiv.org/abs/2303.15056 · Zheng et al. 2023 https://arxiv.org/abs/2306.05685 · Wang et al. 2023 https://arxiv.org/abs/2305.17926 · Kryscinski et al. 2019 FactCC https://arxiv.org/abs/1910.12840 · Tang, Laban & Durrett 2024 MiniCheck https://arxiv.org/abs/2404.10774 · Honovich et al. 2022 TRUE https://arxiv.org/abs/2204.04991 · Laban et al. 2022 SummaC https://arxiv.org/abs/2111.09525 · Zha et al. 2023 AlignScore https://arxiv.org/abs/2305.16739 · Rashkin et al. AIS https://arxiv.org/abs/2112.12870 · Gao et al. 2023 ALCE https://arxiv.org/abs/2305.14627 · Zhang et al. 2026 https://arxiv.org/abs/2609.15964 · Python difflib docs https://docs.python.org/3/library/difflib.html · Leeflang et al. 2008 https://research.rug.nl/nl/publications/bias-in-sensitivity-and-specificity-caused-by-data-driven-selecti/ · Varma & Simon 2006 https://pmc.ncbi.nlm.nih.gov/articles/PMC1397873/ · Kiela et al. 2021 https://arxiv.org/abs/2104.14337 · Thomas & Uminsky 2022 https://arxiv.org/abs/2002.08512 · Becker et al. 2025 https://arxiv.org/abs/2507.09089 · Madaan et al. 2024 https://arxiv.org/abs/2406.10229 · Atlas cards: Balyasny, BlackRock, Man Group, Two Sigma, Bridgewater, HRT, key finding 15.
