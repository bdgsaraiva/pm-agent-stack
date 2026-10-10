# Decision journal

One file per idea: `journal/<YYYY>/<id>.md` (YAML front matter + thesis, what breaks it, outcome).
Capture with `/journal <idea in your words>` in a Claude session on this repo, or the CLI:

```
python -m pmstack journal new --market Brent --direction long --conviction 4 --thesis "..." \
  --price-ref BZ=F --target 115 --invalidation-price 95 --size-planned 1 --source own
python -m pmstack journal event <id> --action add --size 0.5 --price 101 --reason "..."
python -m pmstack journal close <id> --exit-price 110 --process 4 --lesson "..."
python -m pmstack journal reject <id> --reason "..."      # passed ideas: the graveyard
python -m pmstack journal stats | book | list | check <id>
```

Personal build: `book` must be `paper` or `example` (config/journal.yaml). No fund positions, sizes or P&L.

Checks at entry: no invalidation on an open idea (block, Zweig #3); payoff undefined (Zweig #2); best ideas
under-sized vs your median; adding to a CFTC side at the 90th+ percentile; too many new ideas in 5 days
(Zweig #11); entry within 24h of a ±2R close (tilt); poor sleep or high stress (Zweig #14).
