# Architecture (summary)

Full document: "PM Agent Stack — Architecture" (Docs page in the Claude Project "Future of Asset Management and Trading"). This file keeps the decisions next to the code.

## Blueprint (Atlas 4.5), build order
1. Data and research memory — **this repo**
2. Gateway and audit trail — `logs/runs.jsonl`, source fields on every row (pattern; enforcement in corporate)
3. Monitors — **3a commodity S/D + central banks: this repo**; 3b news/filings and 3c weather/shipping next
4. Critic — next (`skills/critic/`)
5. Behaviour and execution review — corporate only (needs order history)
6. Research loop — Claude Code + quant-research standards
7. Risk and crowding — CFTC percentiles here; book stress in corporate
8. AI sleeve — later, corporate

## Decisions (4 Oct 2026)
- GitHub Actions fetch public data; a scheduled Claude cloud task writes the note (Claude's cloud workspace cannot reach the data sites directly).
- Bernardo is the only user of the personal build.
- Morning note about 06:30 BRT on weekdays: Docs page + phone notification.
- Free data only on the personal side.

## Personal vs corporate
Personal: architecture, code, skills, public data, dummy portfolio and journal. Corporate: positions, P&L, orders, fund research, live journal; same layout, adapters swapped (TT, vendor feeds). Nothing travels back from corporate to personal.
