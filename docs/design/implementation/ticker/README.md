# Ticker

A `yfinance` ticker keeps its identity in history. Its `history`
action appends the price `DataFrame` that library returns.

| Artifact | Path |
|---|---|
| Charter | [`charter.md`](charter.md) |
| Spec | [`spec.md`](spec.md) — accepted for implementation |
| Checkpoints | [`checkpoints/000-headless-ticker-and-history.md`](checkpoints/000-headless-ticker-and-history.md) — implemented; [`checkpoints/001-menu-documentation-screen-and-demo.md`](checkpoints/001-menu-documentation-screen-and-demo.md) — implemented |
| Demo | [`demo.md`](demo.md) — hands-on tour of the implemented path |

**Status.** Specification accepted. Ticker 000 and ticker 001 are implemented.
Ticker 001 passed all 482 project tests and the live AAPL hand check.

The program lives at the project root
(`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`).
This folder is only that ticker and its daily history. Guiding
influences are in [`../../../../AGENTS.md`](../../../../AGENTS.md).

Project map: [`../../../../README.md`](../../../../README.md).
