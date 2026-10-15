# Session notes A6 — Weekly review (agent 6), 10 Oct 2026

## Asked
"Go ahead to build the next agent" (after agent 5 shipped the same morning).

## Done
- **Literature review** → Docs: https://claude.ai/code/artifact/dfaab6f8-6e05-4058-a5e8-61fe5b69d639 ; repo `docs/research/weekly-review.md`. Two research sub-agents opened every page cited.
  - Behaviour: Odean (disposition, via secondary), Shu et al. (Taiwan), Locke & Mann (pros hold losers without cost; discipline predicts success), Garvey & Murphy, Garvey/Murphy/Wu and Coval & Shumway (more risk after losses), Liu et al. (more after gains), Thaler & Johnson, Frazzini, Barber & Odean (overtrading), Glaser & Weber, Akepanidtaworn et al. (sells lag random sells ~80 bp; event-day sells better).
  - Feedback and goals: Kluger & DeNisi (>38% of feedback effects negative), Tannenbaum & Cerasoli (debriefs d=0.67), Ellis & Davidi, Baron & Hershey, Gollwitzer & Sheeran (d=0.65), Harkin et al. (monitoring d=0.40), Seijts & Latham, Dai/Milkman/Riis, Ericsson vs Macnamara (<1% in professions).
  - Small samples: Tversky & Kahneman, Miller & Sanjurjo, Wilson/Jeffreys (Brown et al.), Efron & Morris shrinkage, power (~283–285 ideas to tell +0.25R from zero at sd 1.5), Lo / MinTRL, Harvey & Liu, Benjamini–Hochberg, Brier decomposition and small-n noise, regression to the mean.
  - Atlas: NBIM Investment Simulator (4.5 step 5), Cohen, JPMorgan Spectrum, Dalio, Druckenmiller, Tudor Jones. Vendors: Essentia, Alpha Theory, Cabot, Inalytics (corporate vendor review).
- **Bernardo's answers:** goal active Monday unless changed; exit trigger required at close; monthly section first Friday after month end.
- **Code** (commit a050657): `pmstack/review.py`, `config/review.yaml`; `journal close` records `exit_trigger` (inferred or required) and `lesson`; `journal/goals.yaml`; auditor binds each figure to its own market (subject), maps series ids to names, list markers only where a list can be; Friday skill now = critic pass + scorecard + debrief + goal (+ monthly); journal skill (exit trigger, `/journal goal`). CLI: `review weekly [--date] [--write] [--monthly]`, `review goal show|set|drop|list`. 58 tests pass (16 new).
- **Independent review:** 11 defects reproduced and fixed with tests (weekend entries in no week; Friday proposal overwrote his goal; invalidation goal on closed/untaken ideas and pre-cross notes; 4-week vs 1-week median; Brier on the sizing blend; critic 48h judged early; no-edge size never a miss; passes broke after-loss pause; auditor cross-market matches and line-start figures).
- **Live run (9 Oct):** counts-only (example excluded), gate 0 of 10; monthly section for September (Brent 21-day vol 42.5%, 80th pct; RBOB 52.3%, 93rd; dollar 4.5%, 14th; 2y +71bp over 63 days); draft Friday page 34/34 figures matched. First goal set: `log-ideas` from 12 Oct.
- **Scheduled task:** "Friday review" prompt updated (critic + review weekly, goal set unless he set one, audit with both JSONs). Auto-approve, push on, first run 16 Oct.
- **PM Agent Plan doc:** roster 6 → Running; section 6 notes the build with the review link; schedule paragraph updated.
- CLAUDE.md and README updated.

## Next
Gate 1 Nov (0 of 10 paper ideas so far). Then agent 7, consensus & narrative monitor (literature first). If the gate isn't met, Bernardo chooses: build anyway or wait.
