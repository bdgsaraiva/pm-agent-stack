# Inbox

Drop files here: your own studies and notes, and public reports (agencies, central banks, academic papers). Everything in this folder except this README and `ledger.jsonl` is gitignored. The summaries, drivers and facts made from a file are committed; the file itself never is.

**Not allowed:** broker or sell-side research, including summaries or extracts of it made elsewhere (for example with the corporate account), and anything from the fund. If one lands here it is classified as refused, not read further, nothing from it is stored (the ledger keeps only its hash), and you are asked to delete it. Your own notes in your own words are fine (frameworks, which drivers matter, which public data to track), even if you first met an idea in broker research, as long as they carry no broker figures, forecasts, charts or text.

Steps (code: `pmstack/inbox.py`, `pmstack/knowledge.py`):
1. `python -m pmstack inbox screen <file>`: marker screen on the first pages only.
2. You confirm the type: `python -m pmstack inbox classify <file> --type own_study|own_note|public_report|academic|broker|fund`.
3. `python -m pmstack inbox ingest <file>`, then the digest skill writes the summary (key messages; numbers and arguments; consensus vs contrarian; confidence; horizon) with checked claim cards.
4. Claims go to `drivers.yaml`: literature sizes with their citation; your numbers are proposed as priors (`knowledge propose`) and filed only once you confirm each one in chat (`knowledge confirm-prior <pid>`).
5. Dated figures go to the facts log, each tied to a checked card (`inbox facts`).
