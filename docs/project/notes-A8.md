# Session notes A8: risk & crowding (agent 8), 10 Oct 2026

Literature review (Docs): https://claude.ai/code/artifact/f4a74a73-6de9-4269-8832-8b7959f1f5d2 · repo: `docs/research/risk.md`
Commits: 09d2017 (v1), 5fc1c51 and 211f6a2 (v2: long-history stress, below). Tests: 96 pass (~5 min).

## Context
- **Gate 1 Nov not met:** 1 journal entry (the example), 0 of 10 paper ideas, 0 of 2 Friday reviews (the first is 16 Oct). Bernardo: "Gate not met: build anyway."
- Three research sub-agents ran in parallel: crowding and fire sales; correlation and stress testing; CTA flows plus books. Every cited page was opened. Abstract-only and secondary sources are marked; book points are marked "not page-checked".
- **His answers to the 3 questions:**
  - No budget caps: numbers only.
  - Amber early warning; red = the sizing cut, now counting open marks.
  - Stress set: replays + 6 named shocks + worst case.

## What the evidence said (short)
- **Correlations:** they rise in sell-offs, mostly on the downside (Longin & Solnik; Ang & Chen). Part of the rise is mechanical (Forbes & Rigobon). So the stress matrix comes from turbulent days, and no alert fires on a raw correlation jump.
- **Stress losses:** compute them from scenarios, never sigma multiples (Pedersen 2009: over 30 sd in Aug 2007). Show stops honoured and gapped.
- **Positioning:** CFTC levels mostly restate past returns (Sanders et al.: returns lead positions in 10 of 10 markets). Weekly changes carry a small, short reversal (Kang, Rouwenhorst & Tang). Crowding matters most under funding stress (Cheng, Kirilenko & Xiong).
- **CTA flows:** small and temporary on average, so trigger levels are context. Commodities are where CTAs are largest relative to the market (Hurst et al.).
- **Early warning:** stress tests are poor early warnings (Borio et al.). Warnings rest on realised losses and persistent turbulence (Kritzman & Li).

## What shipped (v1)
**`pmstack/risk.py` + `config/risk.yaml`**
- **Risk model:**
  - Current vol: EWMA 0.94.
  - Turbulence and stress days (top 20%): measured on a fixed universe of 21 synchronous US-close markets.
  - Calm matrix: 250 days. Both matrices shrunk with Ledoit–Wolf.
  - Markets outside the universe join pairwise, shrunk the same way and repaired to positive semi-definite.
- **Risk table in R, per idea:** stop in daily sd, 1-sd day in R, share of stress risk, cluster, CFTC crowding on the idea's side (percentile, weekly-change z, ex-trend percentile; counted from the Friday release), and flags. The flags are: past stop, stop near a flip level, panic state, crowded (red only under funding stress), crowded entry, and a trend leg flipping by roll-off.
- **Book:**
  - Effective independent ideas (stress matrix), capped at the count with the raw value shown.
  - Daily sd in R, calm and stress.
  - Open R, and R to the stops.
  - Clusters (directional stress correlation ≥ 0.7) and same-idea pairs (≥ 0.95).
- **Stress table (v1):** 13 rows: 6 replays from 2023–26, 6 named driver shocks, the worst case at k = 3 over 5 days. Replaced in v2 (below).
- **CTA levels:** flip level and distance in daily sd per leg; roll-off flips within 5 days; vol-target scale; Correction/Rebound state; panic state. Captioned as not a forecast.
- **Warnings (the only alerts):**
  - Amber: −3R from the 10-day high, or 3+ ideas in one cluster each at −0.5R or worse.
  - Red: the sizing cut (−4R over 60 days).
  - Persistent turbulence: 3 of the last 5 days in the top 20%.
  - The example book never claims a sizing cut, and its warnings are tagged "[example book]".

**Sizing assistant:** `sizing.drawdown_r` now runs `risk.marked_drawdown`, the marked book (closed R + open marks, last close carried over missing days). The pack and the suggestion can't disagree.

**Wiring:**
- "Risk and crowding" section in facts.md and facts.json.
- `python -m pmstack risk [--date] [--out]`, about 3 s, logged as `risk:report`.
- Morning note: a risk line, exceptions only.
- Friday review: section 3b, risk and stress, when 2+ paper ideas are open. The task prompt was updated to run `pmstack risk` and audit against risk.md.
- facts.json is written as strict JSON; a risk render error can't break facts.md.
- scipy added to requirements.txt.

## Independent review of v1: 12 defects, all fixed
1. A late price on one series faked an amber alert → marks carry the last close.
2. One idea market reset the model window → turbulence and stress days on the universe only.
3. Look-ahead in `--date` runs:
   - ideas are filtered to the as-of day;
   - replays that end later read "not yet happened";
   - CFTC counts from the Friday release;
   - sizing marks to the as-of close.
4. Red ordered closes and open marks wrongly → one daily marked curve.
5. The pack and sizing could disagree on red, and the example book claimed a cut → one function; no red for the example book.
6. Duplicate markets overstated the worst case → exposures are summed by market.
7. A past-stop idea showed the same loss in both columns → it is now exited at today's mark.
8. Replays ignored the path → the window's worst point decides the stop.
9. Effective ideas exceeded the count on hedged books → capped, with the raw value shown.
10. Ideas missing from a scenario were silent → they are named in the row.
11. Holiday fills gave false dates → trading days come from the universe; tables show observed last dates.
12. Closed ideas outside the model jumped at close → the curve uses all journal refs and explicit-R closes.

Nits fixed: exact chi-square; render guard; strict JSON; the turbulence alert links to prices; render reads thresholds from config. Vacuous tests rewritten; red, amber, turbulence, example book, past stop, path, duplicates, as-of filtering and LW/chi-square checks added.

## Live run v1 (9–10 Oct, 2023–26 data)
- Market state: turbulence at the 63rd percentile, 0 of the last 5 days in the top 20%. HY OAS 3.15%, +44bp over 21 observations (close to the 50bp funding line). VIX 14.8. No warnings.
- Only the example Brent idea is open, so the book reads "example".
- A sample note line quoting the risk section passed the number auditor.

## v2, same evening: stress tests on the long history (commits 5fc1c51, 211f6a2)
Bernardo's review: "The past shocks only look at a short history. Start by looking at literature for the best way to stress test and how the most famous companies/softwares do. Adjust what we have done as necessary."

**Research** (two sub-agents, pages opened; both sections are in the Docs page and in `docs/research/risk.md`):
- **Standard setters:**
  - BCBS 2009: pre-2008 tests used "mild shocks" because recent history looked benign.
  - FRTB MAR33: find the window in which *today's* portfolio loses most; the look-back includes 2007; liquidity horizons 10/20/60 days.
  - CPMI-IOSCO: keep the most extreme episodes, never drop them for age.
  - Fed GMS: one-month horizon; mappings for factors without history.
  - EACH: use proxies.
- **Firms and tools:**
  - MSCI and Bloomberg PORT: event libraries; core shocks, isolated vs propagated.
  - Axioma: recent vs crisis covariance side by side (the sign can flip).
  - CME SPAN 2, Eurex, LCH: long look-backs, stress periods outside the look-back, day-by-day path replays, decorrelation scenarios.
  - NBIM: 15 episodes on current holdings, plus an extreme-weather scenario.
  - BlackRock: one month, analogue-calibrated.
  - Man and AQR: tests back to 1926 and 1880 with flagged proxies.

**Built:**
- **Deep history:** one-time fetch of prices and FRED from 1986 (`history_start`; marked in `data/obs/<source>/_history.json`). Ran in Actions run 38086467424 (12.5 min, success): 242k price rows, 122k FRED rows. New FRED proxies: VIXCLS, DHOILNYH, DGASNYH (`risk_only`).
- **`risk.history`:**
  - Spliced returns per market: own futures from about 2000, then the proxy list (FRED spot, ^GSPC, ^NDX, yields by duration).
  - Moves are booked on the next print, so nothing is lost across gaps or holidays.
  - WTI's −$37.63 settle is excluded.
  - Roll screen: the spot replaces the future only when the future jumps and the spot doesn't.
- **Stress matrix:** top 20% turbulence days over Dec 2003 – 2026 (the start is set by EUR/USD). 1,120 stress days, including 2008, 2020 and 2022.
- **32-episode library** (1987–2026; windows from NBIM, Eurex, Man or ours), replayed day by day on today's book:
  - Stops trigger at the first close beyond them, so a gap can cost more than 1R.
  - Columns: gapped, vol-scaled, worst point inside, proxy share, and the markets that were inferred.
- **Worst 1/5/20/60-day windows** for today's book over all history, plus a reverse stress (average moves on the book's worst 1% of days × 0.85).
- **9 named one-month shocks** (adds hedges fail, crop failure and inflation re-acceleration):
  - each run under the stress, 2008 and 2022 correlations, and isolated;
  - analogue episodes shown beside each;
  - sign flips flagged.
- **Worst case at k = 3** over 5 and 20 days, with the loss by market.
- **Lookbacks kept:** the turbulence warning and the panic flag stay on 756 days. The critic's base rate stays on 1,000 days (`config/critic.yaml`).
- **Skills:** the morning note's risk line quotes the book's worst historical day; the Friday review's 3b quotes the worst 20-day window.

**Review:** an independent review found 8 defects, and the live run found 2 more. All are fixed (list in `docs/research/risk.md`). The two from the live run:
- the roll screen misfired on Dated Brent's genuine breakaway (21 Apr 2020; 2026);
- sparse FRED proxies were treated as missing.

Tests: 96 pass. The 10 Oct fact pack was rebuilt with the final code; a sample note line quoting the worst window passed the auditor.

**Live (illustration, same 3 paper ideas as before):**
- Brent and ULSD are now one cluster. Effective ideas 1.4 (was 1.6). Stress sd 1.18R a day (was 1.05R).
- Worst day since 1986: Desert Storm, 17 Jan 1991, −9.17R even with stops (spot proxies, a gap through the stops).
- Worst 20 days: 19 Feb – 18 Mar 2020, −2.89R honoured / −19.71R gapped.
- Worst 60 days: Oct–Dec 2008, −22.12R gapped.
- Lehman replay: −2.80R honoured / −25.23R gapped.
- The Fed hike shock flips sign between the 2008 and 2022 correlations.

## Open items
- **Done:** the first Actions run with scipy succeeded (run 38086467424). Monday's 05:40 run is the first scheduled one on v2.
- **Known limit:** markets without a proxy (metals, grains, softs) keep unadjusted roll days. A back-adjusted source would fix this; none is free.
- **Agent 7 follow-up:** the GDELT OPEC query now fails with "The specified phrase is too short", on top of HTTP 429. Re-version it (`opec_supply_v2`).
- **Align later:**
  - consensus.py's CFTC percentile uses the Tuesday date; risk.py lags it to the Friday release.
  - The sizing overlap cut uses a 60-day correlation; risk uses 250 days plus shrinkage.
- **Research loop (agent 12):** base rate and lift of every crowding and CTA flag before any may alert.
- **Next agents:** 10 research digester + 11 network & reputation, after the gate.
- **Lessons for the kickoff:**
  - Independent reviews found 12 defects in v1 and 8 in v2; the live run on real data found 2 more. Keep both for every agent.
  - Look-ahead in `--date` runs is the common miss: test the as-of filtering explicitly.
  - Ask how long a history an agent really needs before building on what the store already has.
