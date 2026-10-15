# Session notes A5 — Critic + number auditor (agent 5), 10 Oct 2026

## Asked
"Continue phase 2: build the next AI agents, literature first" (kickoff brief), starting with agent 5.

## Done
- **Literature review** → Docs: https://claude.ai/code/artifact/48d36e62-379d-4820-88f7-346f6d775b45 ; repo `docs/research/critic.md`. Two research sub-agents opened every page cited.
  - Decision science: Klein pre-mortem; Mitchell et al. (certainty, not tense, drives it; counts reasons, not accuracy); Veinott 2010 + replication; Gandhi/Duke (pre-mortems raise blame on luck); Koriat 1980 (one contradicting reason after choice); Sanna 2002 (10 reasons backfire); Hirt & Markman (implausible counters backfire); Kahneman & Lovallo, Flyvbjerg, Lovallo/Clarke/Camerer, Lovallo & Sibony (≥6 analogues); KLS checklist (not for routine decisions); ACH fails (Dhami 2019), recalibration wins (Mandel 2018); Nemeth (role-played devil's advocate bolsters); Chang/Mellers (comparison classes, updating); alert fatigue (van der Sijs 49–96% overrides; Ancker −30% per extra prompt; Shah tiering 67%); Dietvorst.
  - LLM: Self-Refine (+0.2 on maths), Huang (self-correction hurts), Kamoi survey, CRITIC (tools), Valmeekam/Stechly (sound verifier), debate vs self-consistency (Du, Smit, Wang, Liang), CoVe, FActScore, RARR, FinanceBench (15% wrong with oracle evidence), FinQA, TAT-QA, PoT, PAL, QuanTemp, sycophancy (Sharma, Perez), LLM-judge bias (Zheng), Chiang devil's advocate, Buçinca, CriticGPT.
  - Atlas: Viking sceptical avatar, GIC virtual IC member, Temasek; Soros, Dalio, Druckenmiller, Howard, Kovner, Marks, Klarman, Andurand, Andy Hall, Jakurski, Cohen. Books (not page-checked except Heuer ch. 8): Heuer, Tetlock, Noise, Mauboussin, Duke, Zenko, Janis.
- **Bernardo's answers:** critic right after capture; no control group yet (revisit at 50 closed ideas); auditor fixes once and flags the rest.
- **Code** (commit 6a5681f): `pmstack/critic.py`, `pmstack/audit.py`, `config/critic.yaml`; `journal new` attaches the card; journal skill (card → questions → answers; pushback rules), morning-note skill (audit step), new `skills/critic-weekly/`. CLI: `critic card|save|answer|withdraw|outcome|weekly|stats`, `audit <file> [--facts] [--flag]`. 42 tests pass (15 new).
- **Independent review** (sub-agent that didn't build it): 11 defects reproduced and fixed with regression tests — sign ignored, % vs sd interchangeable, wrong-market matches silent, "declined 12%" read as December, US$ parsing, re-save wiped answers, source-only analogues, trend asked twice, error recovery, substring alert match, prob range. Remaining limits written in the review.
- **Live runs:** Brent example card — base rate won 49.7% (target first 31.9%, stop first 38.3%; 928 starts since 2023-01-03), gap 0.3 pts, CFTC 17th pct, Zweig #12 → pre-mortem + rule question saved. Friday pass on 9 Oct data: example silent. First audit of the 9 Oct note: 44/44 figures matched, **6 alert refs stale** (pack rebuilt after the note shifted ranks) → fixed in repo copy, re-audit clean.
- **Scheduled tasks:** new "Friday review" (trig_01Q9SQrQjkA72XNpf2LP5pg3), Fridays 18:17 BRT, push on, auto-approve; first run 16 Oct. "Morning note" prompt updated so delivery runs the audit before the Docs page.
- **PM Agent Plan doc:** roster 5 → Running, trigger cells for 5 and 6 updated, section 5 notes the build with the review link, schedule paragraph notes the early ship and Friday reviews from 16 Oct.
- CLAUDE.md (layout, commands, audit rule) and README updated.

## Follow-ups
- Pipeline: don't rebuild a day's pack once its note exists, or give alerts stable ids (refs shifted on 9 Oct).
- Gate 1 Nov: 0 paper ideas logged so far (only the example); 2 Friday reviews possible on 16 and 23 Oct.

## Next
Agent 6, weekly review (process scorecard into the Friday task) — literature review first (Steenbarger, Tharp, disposition effect, overtrading, Akepanidtaworn, implementation intentions, small-sample statistics).
