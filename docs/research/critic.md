---
title: Critic + number auditor — literature review
agent: 5 (critic + number auditor)
date: 2026-10-10
status: reviewed before build; code in pmstack/critic.py and pmstack/audit.py, parameters in config/critic.yaml
docs: https://claude.ai/code/artifact/48d36e62-379d-4820-88f7-346f6d775b45
---

# Critic + number auditor — literature review

**Answer.** The evidence supports a critic that asks little, and asks only when the data disagrees with the PM: a failure story by default, a counter-argument or rule question only when code finds a reason, and an outside view computed by code. Generic contrarianism and LLM self-checking both make things worse. Numbers are checked by code, not by a model: even with the exact evidence in context, GPT-4-Turbo got 15% of FinanceBench answers wrong.

## 1. Papers: how people take criticism

| Finding | What it changes | Source |
|---|---|---|
| Pre-mortem: assume failure, write why. Mitchell et al.: **certainty of the outcome** drives it, not the future tense; they counted reasons (~30% more), not accuracy. | Phrase as a certain failure with date and loss; never claim it improves accuracy. | Klein, HBR 2007; Mitchell, Russo & Pennington 1989 |
| Veinott, Klein & Wiggins 2010 (n=178): biggest cut in overconfidence vs pro/con and critique. Replication (n=53, d=0.81); group vs solo no difference (p=.77). | Pre-mortem is the default question; solo is fine. | Klein 2021 summary; Keysor et al. poster |
| Gandhi, Duke & Schweitzer (n=2,345): less overconfidence, but **more blame on luck**. | At least one reason tagged "thesis error". | SJDM poster 2021 |
| Koriat, Lichtenstein & Fischhoff 1980 (n=200): after a choice, **only contradicting reasons** improved calibration. | One strongest counter-argument, asked after commitment. | JEP:HLM 1980 |
| Sanna, Schwarz & Stocker 2002: listing 10 alternatives *increased* bias; 2 did not. | Each question asks for one answer. | abstract |
| Hirt & Markman 1995: plausible alternatives debias; implausible ones raise confidence. | Counter-argument must be specific and grounded. | abstract |
| Kahneman & Lovallo 1993; Flyvbjerg 2006 (rail overruns 44.7%, n=46). | Show the outcome distribution of similar cases. | Mgmt Sci; PMJ |
| Lovallo, Clarke & Camerer 2012: many analogues beat the few remembered. | Similarity-weighted set of past ideas. | SMJ abstract |
| Lovallo & Sibony 2010 (1,048 decisions): process 6× analysis; ≥6 analogues. | Reference class only at 6+; market base rate otherwise. | McKinsey |
| Kahneman, Lovallo & Sibony 2011: checklist not for routine decisions. | Small low-conviction ideas: card only. | HBR |
| Heuer ACH vs Dhami et al. 2019 (50 analysts): no accuracy gain (36% vs 33%), less consistency, base rates crowded out (12% vs 52%); recalibration and aggregation cut error 35–61% (Mandel et al. 2018). | Light structure; "what evidence is diagnostic now" on Fridays; code recalibrates. | Heuer ch. 8; ACP 2019; JDM 2018 |
| Nemeth, Brown & Rogers 2001: authentic dissent beats role-played devil's advocate, which bolsters the original view; structured critique still beats consensus (Schweiger 1989). | Every question carries a data-backed reason and the critic's own number. | EJSP; SMJ |
| Chang et al. 2016: training −6–12% Brier/yr; only comparison classes linked to accuracy. Mellers 2015: updating r=.49. | Log P(win) before/after the card; Brier. | JDM; JEP:Applied |
| Kahneman & Klein 2009: intuition needs a valid environment and feedback. | Conviction is not evidence; the journal is the feedback. | Am Psych |
| Alerts overridden 49–96% (van der Sijs 2006); −30% acceptance per extra reminder, −10% per 5-pt rise in repeats, no effect of total workload (Ancker 2017); tiering → 67% acceptance (Shah 2006). | Default 1, cap 3, no repeats in 30 days, two tiers. | JAMIA; BMC MIDM; JAMIA |
| Dietvorst 2015/2016: algorithm aversion after errors; modifiable outputs get used. | One-tap reaction; dismiss with a reason. | Wharton |

## 2. Papers: LLM critique and numbers

| Finding | What it changes | Source |
|---|---|---|
| Self-Refine ~+20% open-ended, **+0.2 on maths**; own feedback said "looks good" on 94% of maths cases. | Self-review polishes; doesn't find errors. | Madaan et al. 2023 |
| Intrinsic self-correction hurts: GPT-4 GSM8K 95.5→89.0; GPT-3.5 CSQA 75.8→38.1. | No reflect-and-revise loop. | Huang et al. 2023 |
| Self-correction works with reliable external feedback (survey). | Leverage = the code card. | Kamoi et al., TACL 2024 |
| CRITIC: with tools +7.7 F1 QA, +7.0 maths; without tools ~+2.3, toxicity worse. | Questions must cite card facts. | Gou et al. 2023 |
| Sound verifier 88/100 vs LLM verifier 55/100 (passed 38/45 wrong plans); self-critique 16%→2%. | Deterministic checker; failing-item list is enough feedback. | Valmeekam 2023; Stechly 2024 |
| Debate gains vanish at equal compute (88.2 vs 83.0); one agent with examples ≈ six (75.6 vs 74.5). | One critic, no panel. | Du; Smit; Wang |
| CoVe: factored checks win (55.9→71.4 FActScore); FActScore per atomic fact. | Per-figure checks; share matched. | Dhuliawala; Min |
| RARR: smallest edit per unsupported claim. | Fix orphans one at a time. | Gao et al. ACL 2023 |
| FinanceBench: **15% wrong with oracle evidence**, 17% long context. | Auditor needed even with facts in prompt. | Islam et al. 2023 |
| PoT ~+12%; PAL large numbers 61.2% vs 23.1%. | Derived numbers come from code. | Chen 2022; Gao 2022 |
| QuanTemp: best macro-F1 58.3 on numerical claims. | Deterministic matching. | 2024 |
| Sycophancy: "Are you sure?" → Claude 1.3 98%, GPT-4 42% false admissions; RLHF doesn't fix it. | Questions frozen; withdrawn only for a new fact. | Sharma 2023; Perez 2022 |
| LLM judges biased by order/length/self. | Code picks slots. | Zheng 2023 |
| LLM devil's advocate helped only when interactive and aimed at the recommendation; best group felt worst. Cognitive forcing liked least. | Aim at the thesis; judge by changed decisions. | Chiang, IUI 2024; Buçinca 2021 |
| CriticGPT: critiques preferred 63%, but hallucinate problems. | Track false-alarm rate. | McAleese 2024 |

## 3. Atlas investors and books

- **Viking** "sceptical avatar"; **GIC** virtual IC member; **Temasek** IC assistant; Atlas 4.5 step 4: argue against each new thesis *using the book's own history*, measured by theses changed or resized.
- **Soros** (find the flawed premise; knowing when he's wrong) → counter targets the premise. **Dalio** (have someone challenge you; pain + reflection) → reference class first; Friday pass. **Druckenmiller** (never hold just for the original thesis; crowd right 80%) → keep / re-underwrite / cut; crowding on the card. **Howard** (conviction is not a waiver) → high conviction gets more exit scrutiny. **Kovner** (stop where the idea is wrong) → pre-mortem checks the invalidation. **Marks** (second-level thinking) → Zweig #12. **Klarman** (thesis first) → critic speaks after capture. **Andurand / Andy Hall** (one event; early = wrong) → pre-mortem names event and date.
- **Mandala:** Zweig prompt rules #1, #5, #6, #9, #12, #13, #15, #16, #17 are the rule questions; hard checks stay in the journal.
- **Books** (general knowledge, not page-checked, except Heuer ch. 8): Heuer (disprove, diagnosticity, milestones); Tetlock (comparison classes, Brier, updating); Kahneman, Sibony & Sunstein, *Noise* (decision hygiene, independence, sequencing); Mauboussin (process where luck is large; outside view; pre-mortems); Duke (kill criteria = state and date); Zenko (not everything needs red-teaming); Janis (second-chance meeting; weak evidence).

## 4. Where the sources disagree

| Question | Resolution |
|---|---|
| Does challenge help? (Schweiger vs Nemeth) | Grounded critique beats none and beats theatre. |
| Does the pre-mortem change decisions? | Keep it, tag thesis errors, score by changes, not kills. |
| Consider-the-opposite fragile? | One specific counter, only when a fact contradicts. |
| More structure (ACH)? | Light; code base rates. |
| Can an LLM check itself? | No; one grounded critic; numbers by code. |
| How hard to push? | Only where a fact contradicts; hold unless a new fact. |
| How many prompts? | Default 1, cap 3, no repeats. |

## 5. Design changes vs the plan

| Rule | Plan | Now |
|---|---|---|
| Budget | ≤3 per idea | Pre-mortem by default; counter and rule only when triggered; cap 3 |
| Silence | — | Card only at conviction 1–2 and ≤0.5 units; rejected/closed; no repeat on the same market within 30 days |
| Tiers | — | "Answer before sizing up" on a data-driven rule or a 15-pt gap vs the outside view |
| Similar ideas | same market, direction or source | Weights 1.0 / 0.6 / 0.4; source only adds; shown when weights sum to 6+ |
| Outside view | — | Market base rate: random entries in stored prices with the same target, stop, horizon, direction |
| Pre-mortem | "three months on, lost 1R" | Certain failure on the horizon date; thesis-error tag |
| Counter | strongest counter | Must cite a contradicting card fact and give the critic's number |
| Picking | model | Code picks and ranks slots; model words |
| Pushback | — | Frozen; withdraw only with a new fact |
| Figures in questions | — | Must come from the facts the question cites (auditor) |
| Fridays | every open idea | Silent unless: alert, ≥1 weekly sd, ≤50% risk left, past horizon, invalidated, crowding ±10 pts |
| Measure | changes logged "critic" | + P(win) before/after, reaction, premise valid/wrong, named risk happened |
| Auditor | flag orphans | Per-figure match: displayed precision, sign, kind (%, sd, percentile, price), bound to market; dates and refs; fix once, then banner |

Decided by Bernardo (10 Oct): critic right after capture; no control group until 50 closed ideas; note auditor fixes once and flags the rest.

## 6. How it works — worked example (Brent example idea, 10 Oct 2026)

Long Brent 104.43, target 112.0, invalidation 98.0, 30 days, conviction 3, source consensus.
Card: implied P(win) 50.0% (prior); base rate won 49.7% (target first 31.9%, stop first 38.3%, neither 29.8%; 928 starts 2023-01-03 to 2026-09-10, ~44 independent); gap 0.3 pts; no reference class yet; 63-day trend +25.4% (with the long); CFTC 17th percentile on the long side (2026-10-06); rule: Zweig #12 (consensus, no edge written).
Slots: pre-mortem + rule; tier "when you like". Variants: P(win) 70% → gap 20.3 → counter on base rate, "answer before sizing up"; Brent short (97/110) → counter on the trend, Zweig #1 dropped as a repeat of the same fact.

## 7. Number auditor — live result

9 Oct note: 44 figures checked, 44 matched; 6 alert refs wrong because the pack was rebuilt after the note and alert ranks shifted. Refs fixed in the repo copy; re-audit clean. Follow-up: don't rebuild a day's pack after its note, or give alerts stable ids.

Independent review (separate agent) reproduced 11 defects before commit, all fixed with regression tests (sign ignored; % vs sd; wrong-market matches silent; "declined 12%" read as a date; US$ parsing; re-save could wipe answers; source-only analogues; trend asked twice; error recovery; whole-word alert match; prob range). Remaining limits: two cited facts can be swapped; "Oct 19"-style dates unverified; CFTC crowding is the latest report even for back-dated cards.

## Sources
Full list with links in the Docs page (above). Not verified: Schwenk 1990 meta-analysis; Mitchell et al.'s exact 30%; Lovallo, Clarke & Camerer effect sizes; Veinott et al. full text.
