# Morning note — Tuesday 13 Oct 2026

**Data not refreshed.** Today's fact pack (`briefs/2026-10-13/facts.md`) is missing; the latest pack is still `briefs/2026-10-10/` (Saturday 10 Oct, manual run).

- **What failed:** the scheduled `daily-fetch-and-monitor` job did run yesterday afternoon (Monday, much later than its 05:40 BRT slot) and every fetch came back ok (EIA, CFTC, FRED, prices, central-bank text, GDELT), but the job stopped at its test step: `tests/test_consensus.py::test_narrative_stages_from_fake_gdelt` failed (the fake Hormuz narrative came out "peaking" where the test expects "spreading"), so no pack was built or committed. This morning's scheduled run has not appeared yet.
- **Effect:** nothing is refreshed. No figures, alerts, book status or crowd check today; none are filled from memory or the web.

Read: the blocker is now a failing offline test, not the cron; until that test is fixed, every run will fetch fine and still publish no pack. Worth fixing the test (or the stage logic it caught), then running the workflow by hand.
