# Session notes A17: specialists S3, the Metals specialist, 25 Oct 2026

Brief: `docs/project/specialists-kickoff.md` (S3 in section 5). Same worktree as A15–A16 (`claude/specialists-kickoff-27d712`), in sync with main (no new commits there). The notes-and-keys track is still treated as active: this session stayed out of its files and added sources through `config/sources.d/metals.yaml`.

## Bernardo's decisions (25 Oct)
- **Sources:** all four that passed the check: SHFE weekly stocks, LME aluminium, IMF metals via FRED, and the World Bank Pink Sheet.
- **Playbooks:** stock changes and China data days. Gold on Fed and CPI days was not chosen and is kept as an open question.

## Literature
`docs/research/metals.md`. One pass in this session, mostly on abstracts and working-paper pages; each row says which.
- Long-run prices: Stuermer (2018); Jacks & Stuermer (2020); Erten & Ocampo (2013).
- Storage: Fama & French (1988); Geman & Smith (2013); counterpoint Toyne; GHR (2013).
- China: Tang & Zhu (2016) on collateral; Bank of Canada (2016) on housing; IMF.
- Aluminium: power cost and the capacity cap (trade press).
- Iron ore: RBA (2013).
- Gold: Erb & Harvey (2013); Baur & Lucey (2010); the post-2022 central-bank break.
- No academic event study of copper on China PMI days was found.
- A broker per-tonne gold sensitivity turned up in a search and was **not** used.

## Source check
- **Passed:** SHFE (JSON to 14 Nov 2025, HTML from 21 Nov 2025; VARID has trailing spaces in the 2023–24 files), Westmetall aluminium, FRED IMF series, Pink Sheet.
- **Failed:** COMEX stocks (CME blocks scripts), GLD holdings (returns a PDF), China customs (no machine-readable tables), Yahoo TIO=F (dead since 2021).
- **NBS PMI dates:** the last calendar day of the month, per NBS release calendars for 2018 and 2019.

## Bug found and fixed: Westmetall dropped every January and February
`westmetall._date` replaced the German "Januar" with "January" inside "January" itself, which produced "Januaryy". Every January and February row since 2008 failed to parse, for copper too. The `spread` series (COMEX vs LME copper) and the relative idea's marks were built on these gaps.
- **Fix:** whole-word replacement.
- **Re-fetched:** `lme` and `lme_metals` (copper and aluminium now from 2 Jan 2008, with no gaps); `spread` rebuilt (now from 2008).
- **Regression test** in `tests/test_metals.py`.

## What shipped
- **Data** (local backfill committed):
  - `shfe`: 637 weekly reports, May 2014 to 23 Oct 2026, for copper, aluminium and gold.
  - `lme_metals`: aluminium cash, 3-month and stock from 2008; copper 2008–2017.
  - `fred_metals`: IMF copper, aluminium and iron ore from 1992; US CPI from 1960.
  - `pinksheet`: copper, aluminium, iron ore and gold from 1960.
  - Whether GitHub Actions can reach SHFE shows on the first daily run (`fetch:shfe`).
- **`pmstack/metals.py` + `config/metals.yaml`** (`python -m pmstack metals [--date D] [--write]`): stock playbooks, NBS PMI days, the storage test, long-run real prices. `events.base_rates` now takes eras (energy unchanged).
- **Pack:** `pmstack/specialist.py` is split into `energy_figures` and `metals_figures`. The energy pack is identical before and after (73 of 73 figures).
- **Knowledge:** `knowledge/metals/{gold,copper,aluminium,iron_ore}` (primers, 20 drivers through `knowledge add`, balance templates, playbooks with code tables, analogues linked to agent 8's replays, open questions) and the `estimates/*.json` files.
- **Skills:** `skills/specialist-metals/SKILL.md` (an index only). `/ask` now covers metals; routing is active in `config/agents.yaml`.
- **Test set** `evals/metals/` (20 tasks, 4 sealed). Baseline from three independent answering sessions, run again on the fixtures refrozen after the review fixes: **pass^3 20/20** (Wilson 0.84–1.0). The grader was spot-checked against bad answers: a raw spread passed off as net, a non-abstention, trade wording, and a reaction called measurable. All four fail.
- **Tests:** full suite 436 passed. `tests/test_metals.py`, 12 cases, including regression tests for review findings 1, 3 and 4. `tests/test_specialists_s0.py`'s planned-specialist case now uses Ags.

## Results on repo data, as of 2026-10-23 (contemporaneous, never a forecast)
- **LME copper stocks vs COMEX copper:** −0.16% per sd of stock surprise (t −6.8, 4,589 reports), with similar slopes in both halves and both eras; the price moved against the surprise on 57% of reports with |z| ≥ 1. The day after also carries part of it (−0.08%, t −3.7): a delayed reaction, or a one-day dating offset (open question).
- **SHFE stocks:** no measurable reaction for either metal.
- **LME aluminium:** a reaction in 2008–14 (−0.066%, t −2.9) that is gone since 2015 (−0.008%, t −0.75).
- **NBS PMI days:** no extra volatility (copper 0.97, aluminium 0.92, gold control 0.98; placebos similar).
- **Storage fit (spread net of interest, after the review):**
  - **Copper:** −0.67 pp per log unit of visible stocks (t −5.3, R² 0.20); every block negative (−0.61, −0.47, −0.70) with the full slope inside their range; residual ADF −6.0 (Engle-Granger 5%: −3.34).
  - **Aluminium:** −0.66 (t −4.1); blocks −1.06, −0.75, −0.33 (the last one not significant on its own).
  - **Vol:** the volatility predictions are not supported for either metal (block signs disagree).
- **Today:**
  - **Copper:** raw spread 1.016% backwardation; 2.037% net of interest at a 4.04% T-bill (98th percentile since 2014). Visible stocks are at the 43rd percentile. Implied (out of sample) 0.308%, so the net spread is 1.73 pp above it (99th percentile of the fit's residuals). SHFE is 36.8% below its 5-year norm.
  - **Aluminium:** visible stocks are the lowest since 2014; the net spread is 1.85% (97th percentile), 1.34 pp above implied.
- **SHFE playbook after the review** (holiday-gap weeks dropped, five full prior years): 340 reports from 2020, still no reaction (copper t 0.0, aluminium t −0.1).
- **Long run (real, since 1960):** gold at the 99th percentile, copper 96th, aluminium 42nd, iron ore 50th.

## Live run
`/ask metals: how tight is copper and is the LME backwardation explained by stocks?`
- Card: `cards/copper/2026-10-23-metals.json` (26 sources cited). It was redone after the review: the first card used the raw spread. That card was never committed, so it was set aside rather than kept.
- Answer: `cards/answers/2026-10-23-copper-tightness-and-lme-spread.md`, audited 16 matched, 0 unbound, 0 orphans.
- Logged as `ask:metals`.

## Independent review (a sub-agent that did not build it): 9 findings (1 High, 4 Medium, 4 Low)
The reviewer also checked that the energy pack is identical before and after the refactor.

| # | Sev | Finding | Fix |
|---|---|---|---|
| 1 | High | The storage spread ignored interest rates: a 3-month spread carries about r × 91/360, and US rates went from 0 to about 5% over 2014–26. That is up to 1.3 pp, the size of today's spread. The falling block intercepts and the "full slope outside the blocks" result came from this. | Spread net of interest (3-month T-bill `DTB3`, added to `fred_metals`). Both metals now have stable slopes inside their block ranges. Raw and net spreads both in the pack. |
| 2 | Med | The residual ADF used −2.86, a raw series' critical value; the Engle-Granger value is −3.34. Newey-West at 6 lags was too short for residual AR(1) ≈ 0.8. ADF ran on a different fit from the one quoted. | Engle-Granger −3.34; Newey-West over at least 26 weeks; ADF on the fit actually used. |
| 3 | Med | The implied spread came from a fit that included today; a weak fit (aluminium, latest block t −1.2) was still quoted. | Fitted without the last 13 weeks (today out of sample). Suppressed unless significant, stationary and sign-stable (test added). |
| 4 | Med | SHFE changes across a skipped holiday week are two-week changes, scored against one-week norms (mean abs(z) 2.07 vs 0.98). | Dropped (test added). |
| 5 | Med | 30 of 105 PMI days fall on weekends and are priced on the first trading day of the month (ISM and Caixin day). The +5 placebo landed near payrolls. | Weekday releases shown alone; placebos at −5 and +10 trading days. Result unchanged: no extra volatility. |
| 6 | Low/Med | PIORECRUSDM was duplicated in `data/obs/fred` (103 stale rows) and `fred_metals`; the critic's and journal's loaders do not deduplicate. | Stale rows removed from `data/obs/fred`. |
| 7 | Low | The "5-year norm" for SHFE started with 1–2 prior years in 2016. | Norm needs five full prior years: SHFE events from 2020. |
| 8 | Low | Pack rows pointed at `estimates/*.json`, which can hold another as-of date than the card. | Rows cite the computation and its as-of date (`pmstack.metals.*(…, as of D)`). |
| 9 | Low | The energy test set was not re-run after the shared `/ask` skill and pack changes. | Re-run, k = 3 (`evals/energy/runs/2026-10-25-recheck-k*`): **pass^3 20/20**, unchanged. |

Not checked (needs the network): the LME stock dating convention (open item).

## Open items
- `fred_metals` (like `fred_quant`) re-fetches its full history every run: `fetch.py` checks known series under the block key, but the FRED rows carry `source = 'fred'`. For `fred_metals` that is about 2,000 monthly rows a day. The T-bill now sits in its own block (`fred_metals_rate`, from 2008), so the daily re-read is small. The root fix belongs in `fetch.py` (a shared file).
- First daily run: check that `fetch:shfe`, `fetch:lme_metals`, `fetch:fred_metals` and `fetch:pinksheet` are in `logs/runs.jsonl`, and that SHFE is reachable from Actions.
- LME stock dating: check a few dates against LME's own report (is the day-after slope a dating offset?).
- China customs trade-day calendar; COMEX stocks; China aluminium output and IAI data; Brazil iron ore exports (Secex); gold on FOMC/CPI days and gold's beta to real yields: all in the `open-questions.md` files.
- Bernardo's priors on metals drivers arrive through the inbox.

## PM Agent Plan (Docs) updates this session could not make
- Roster: Metals specialist live (S3).
- Schedule: S3 done 25 Oct; next S4 Ags.
- A Docs version of the metals literature review (repo copy only).
