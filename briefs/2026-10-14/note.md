<!-- doc: https://claude.ai/code/artifact/5fecbb4a-8731-4081-97c6-7996d5ca873f -->
# Morning note — Wednesday 14 Oct 2026

**Data not refreshed.** Today's fact pack (`briefs/2026-10-14/facts.md`) is missing; the latest pack is still `briefs/2026-10-10/` (Saturday 10 Oct, manual run). Third weekday in a row without a pack.

- **What failed:** yesterday's scheduled `daily-fetch-and-monitor` run (Tuesday afternoon, well after its morning slot) fetched every source ok, then stopped at the same test as Monday: `tests/test_consensus.py::test_narrative_stages_from_fake_gdelt` (fake narrative comes out "peaking", test expects "spreading"). No pack was built or committed. This morning's scheduled run has not appeared yet.
- **Effect:** nothing is refreshed. No figures, alerts, book status or crowd check today; none are filled from memory or the web. Today's EIA Weekly Petroleum Status Report will not reach a note until a pack builds.

Read: the fetchers are healthy; the single failing offline test is what blocks every run. Fixing that test (or the stage logic it caught) and running the workflow by hand would restore tomorrow's note.
