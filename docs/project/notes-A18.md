# Session notes A18: specialists S4, the Ags specialist, 28–30 Oct 2026

Brief: `docs/project/specialists-kickoff.md` (S4 in section 5). Same worktree, fast-forwarded to main first (bot data commits only, plus the notes track's note page). The notes-and-keys track is active (it added `pmstack/notepage.py` on 29 Oct). This session stayed out of its files and used `config/sources.d/ags.yaml`.

## Close tape routine: found broken, fixed (28 Oct)
- **What failed:** no tape card was written on 26, 27 or 28 Oct. The routine "Close tape" had no repository attached, so it could clone the public URL but got HTTP 403 on the GitHub API: it could not start `close.yml` and could not push. Each run reported the failure and stopped. The tapes themselves were built late by the backup cron.
- **Fix:** I attached the repository as a `git_repository` source, which is how the morning-note and Friday routines are set up. The prompt now uses that checkout and names the 403 case.
- **Verified:** the 29 Oct run started `close.yml` through the GitHub connector (the sandbox's `gh` token is invalid), wrote the card, audited it at 17 matched / 0 orphans, and pushed `tape: 2026-10-29`.

## Bernardo's decisions (30 Oct)
- **Sources:** Conab survey vintages, USDA export sales, and ENSO + Drought Monitor. Not chosen: Secex.
- **Playbooks:** WASDE days, Crop Progress, Grain Stocks and Acreage. Not chosen: export-sales days.

## Literature and sources
`docs/research/ags.md`.
- **Papers:** Adjemian (2012); Karali et al. (2019); Lehecka (2014); Wright (2011); Schlenker & Roberts (2009); Iizumi et al. (2014); Ubilava (2018); farmdoc on USDA vs Conab.
- **USDA's move to noon releases** (11 Jan 2013) is checked against USDA's notice.
- **Broker material:** the sugar/ethanol notes from StoneX and Czapp were not used.
- **Source check:**
  - ESMIS archive (WASDE back to the 1970s; also lists future dates).
  - Conab: one workbook per survey; old pages were re-published in 2025, so the page date is checked against the file's month. Links vary: extension present or not, folder pages, "tabela de dados" files.
  - FAS export sales moved to api.fas.usda.gov.
  - ONI, and the Drought Monitor (CONUS; the state endpoint answered once, then came back empty).
  - UNICA fails (latest PDF only). Secex passes but is rate-limited.

## What shipped
- **Adapters:** `esmis`, `conab`, `fas_esr`, `noaa_oni`, `usdm`. Pink Sheet maize, soybeans, HRW wheat and world sugar are added to the S3 block.
- **Local backfill committed:**
  - ESMIS dates from 2000;
  - Conab, 46 surveys from Oct 2021 (pre-2022 .xls and three malformed workbooks skipped and logged);
  - ONI from 1950; Drought Monitor from 2000;
  - export sales: corn MY2024–27 only. The public demo key ran out; Actions fetches the rest with the repo key, resuming missing market years.
- **`pmstack/ags.py` + `config/ags.yaml`** (`python -m pmstack ags [--date D] [--write]`):
  - report-day volatility, with a local control vs the 10 trading days either side;
  - the WASDE revision proxy from 2021;
  - Crop Progress, priced the next day, re-dated to the actual release.
- **Pack:** `specialist.py` `ags_figures` covers agent 9's balance rows, Conab with its revision, export commitments vs the same week of earlier years, ONI and drought, playbooks and long-run real prices. The next events come from USDA's own schedule.
- **Knowledge:** `knowledge/ags/{corn,soybeans,wheat,sugar}` (primers, 29 drivers, balance templates, playbooks, analogues, open questions). Skill `skills/specialist-ags/`; `/ask ags`.
- **Test set:** `evals/ags/` (20 tasks, 3 sealed). Baseline from three independent sessions on the final fixtures: **pass^3 20/20** (Wilson 0.84–1.0). The grader was spot-checked against bad answers.
- **Tests:** full suite 452 passed. `tests/test_ags.py`, 15 cases, including regression tests for the review.

## Fixes outside S4 found on the way
- **STEO (S1):** STEO data reached the store on 28 Oct, and the 2014 workbooks carry no forecast date. The energy pack crashed on them, so `/ask energy` would have failed. Those issues are now dated at the end of their issue month (conservative).
- **Card validator:** "2026/27" and "2007/08" were treated as uncited figures. Consecutive crop-year labels are now skipped like years; other "a/b" numbers still count.
- **No-trade grader (shared with the own test set):**
  - **What failed:** it flagged refusals such as "buy/sell and size decisions stay with you" (one miss in Ags, one in the Metals recheck).
  - **Fix:** "buy" or "sell" used as a modifier of "decisions" or "calls" no longer counts. Real instructions still fail, and a test pins both.
  - **Re-checks:** energy and metals re-run k = 3 after the shared skill and pack changes, both pass^3 20/20. The own test set (`/evals`) was not re-run; its answers don't contain such refusals, but check at its next run.
- **Venv:** the shared venv lacked `markdown`, which the notes track's `notepage.py` needs (it is in requirements). I installed it.

## Results (as of 2026-10-29; contemporaneous, never a forecast)
Report days are disjoint categories. "Local" is the ratio vs the 10 trading days either side, with its paired t.

| Market | WASDE (no January) | January | March/June | September Grain Stocks | Crop Progress (from 2020) |
|---|---|---|---|---|---|
| Corn | 1.31 (t 5.2) | 3.26 (t 5.0) | 2.69 (t 6.4) | 1.92 (t 3.4) | −0.26% per sd, t −2.2 |
| Soybeans | 1.19 (t 3.1) | 2.31 (t 4.2) | 1.91 (t 4.5) | 1.63 (t 2.7) | −0.20%, t −1.6 |
| Wheat | 1.09 (t 1.8) | 1.85 (t 3.1) | 1.79 (t 4.1) | 1.56 (t 2.5) | winter −0.22% (t −1.5), spring −0.24% (t −1.4) |
| Sugar No. 11 | 0.95: none | — | — | — | — |

- Placebos leave out every report day and every Crop Progress reaction day.
- The WASDE revision proxy since 2021 for corn is −1.12% per sd (t −3.9), but only 8 revisions are of at least 1 sd, too few for a hit rate.

## Live run
`/ask ags: how tight is corn, and what does the WASDE usually do?`
- Card: `cards/corn/2026-10-29-ags.json` (15 sources).
- Answer: `cards/answers/2026-10-29-corn-balance-and-wasde.md`, audited 14 matched / 0 orphans. Logged as `ask:ags`.
- Reading: corn is not tight. Stocks-to-use is 11.3% (42nd percentile); October's raise of 282 million bushels sits within USDA's usual miss of 331; September stocks are 43.8% above the 5-year average; export commitments are 9.1% behind. The 10 Nov WASDE is a volatility event, not a directional one.

## Independent review (a sub-agent that did not build it): 14 findings (2 High, 5 Medium, 6 Low, 1 test-gap list)
| # | Sev | Finding | Fix |
|---|---|---|---|
| 1 | High | Most Grain Stocks days are also Acreage/Prospective Plantings days (March, June) or January WASDE days. The two rows double-counted the same days. | Disjoint categories: WASDE without January; January; March/June; September alone (test). |
| 2 | High | The Crop Progress norm included the jump from last autumn's final rating to the first report of the season (corn up to 22 pp, spring wheat 43 pp). | Changes across a gap over 10 days are dropped before norms are built. An event needs five distinct prior seasons (test). |
| 3 | Med | The Conab wheat label jumped a year at the October survey while the value carried on, making fake and missing revisions. | Wheat is labelled by harvest year (February switch). Old rows removed and re-fetched (test). |
| 4 | Med | A report due today never appeared in next events. | The schedule includes today; Export Sales and CFTC count today too (a morning pack lists them). |
| 5 | Med | The five-season rule was off by one (events from 2021, while the text said 2020). | Counted by distinct seasons; events start in 2020; text generated from the output. |
| 6 | Med | An energy code change (the STEO date fallback) slipped into S4. | Kept: it fixes a real crash on stored 2014 issues (the reviewer's check missed the "None" dates). Energy re-checked: pass^3 20/20. |
| 7 | Med | Unsupported claims: a WASDE split by stocks-to-use regime (not built); Drought Monitor states (none); soybean March/June placebo. | Text corrected. Placebos now carry both measures, the number of days and t. The soybean +10-day placebo rests on 18 days (t 1.4). |
| 8 | Low | The WASDE revision hit rate rested on 8 reports. | Marked insufficient below 30; only the slope is quoted. |
| 9 | Low | The "latest" condition z was stale. | Labelled "latest release with a norm", with its date. |
| 10 | Low | Agent 9's condition rows carry the NASS Monday in holiday weeks. | Re-dated with ESMIS in the pack. Agent 9's own dating is an open question. |
| 11 | Low | The noon-release era boundary was May 2013. | 11 Jan 2013 (USDA notice). |
| 12 | Low | Export-sales weeks were aligned by count. | Aligned by days into the market year (±3 days). |
| 13 | Low | The live pack file was stale (drought "Total" row). | Pack regenerated after the CONUS fix. |
| 14 | — | Test gaps. | Tests added for #1–#5 and placebo exclusion; wheat CFTC now listed in the pack's gaps. |

Also fixed during the build:
- The Drought Monitor's US endpoint returns a "Total" row (with AK, HI and PR) beside CONUS for each date, and the parser had kept "Total".
- The ONI label read "neutral" at +2.16; it now counts consecutive seasons.

## Open items
- **First Actions run:** check `fetch:conab`, `fetch:fas_esr` (backfill to MY2012 resumes run to run), `fetch:esmis`, `fetch:noaa_oni` and `fetch:usdm` in `logs/runs.jsonl`.
- **Data gaps:** corn-belt drought (state statistics); a CFTC wheat series (shared CFTC block, notes track); daily heat data; UNICA vintages (parse each new PDF?); WASDE consensus.
- **Agent 9:** NASS condition rows dated at the Monday in holiday weeks; backdated packs read them a day early.
- **Own test set** (`/evals`): run it at its next change to confirm the grader fix.

## PM Agent Plan (Docs) updates this session could not make
- Roster: Ags specialist live (S4).
- Schedule: S4 done 30 Oct; next S5 Macro context.
- Close tape routine repaired 28 Oct; the first tape card since 23 Oct was written on 29 Oct.
