# Chart

The ticker menu can append a candlestick chart. The chart is one
presentation. Each candle is a presentation inside it, green or red,
and the pointer highlights that candle.

| Artifact | Path |
|---|---|
| Charter | [`charter.md`](charter.md) |
| Spec | [`spec.md`](spec.md) — accepted and implemented through chart 001 |
| Checkpoints | [`checkpoints/000-headless-chart-and-hits.md`](checkpoints/000-headless-chart-and-hits.md) and [`checkpoints/001-menu-styles-screen-and-demo.md`](checkpoints/001-menu-styles-screen-and-demo.md) — implemented per user report |
| Demo | [`demo.md`](demo.md) — hands-on tour |

**Status.** Candlestick specification accepted and implemented through chart
001 per user report. `uv sync` succeeded, 108 focused tests passed, and the
full suite passed 505/505. In the live AAPL check, `candlestick` returned
`no prices`; `history` then appended a `DataFrame 22×7` without a chart.
The fixture screen test covers dated candle hover. The demo is complete.

The program lives at the project root
(`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`).
This folder is only that chart. Guiding influences are in
[`../../../../AGENTS.md`](../../../../AGENTS.md).

Project map: [`../../../../README.md`](../../../../README.md).
