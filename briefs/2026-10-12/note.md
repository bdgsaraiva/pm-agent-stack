<!-- doc: https://claude.ai/code/artifact/d93d0f26-f874-407b-919a-bf3fdbabdaab -->
# Morning note — Monday 12 Oct 2026

**Data not refreshed.** Today's fact pack (`briefs/2026-10-12/facts.md`) is missing; the latest pack is `briefs/2026-10-10/` (Saturday 10 Oct, built from a manual run).

- **What failed:** the scheduled `daily-fetch-and-monitor` job did not run this morning; GitHub shows no scheduled run of it so far, only manual runs. In the last fetch (10 Oct), EIA, CFTC, FRED, prices and central-bank text were ok; GDELT was partial (rate-limited on `opec_supply_v1`).
- **Effect:** nothing is refreshed. No figures, alerts, book status or crowd check today; none are filled from memory or the web.

Read: the cron schedule may not be active on the repo. Worth checking the Actions tab or running the workflow by hand (workflow_dispatch) before the next note.
