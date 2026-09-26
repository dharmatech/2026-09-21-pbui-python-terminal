# chart 000 — Headless chart and retained hits

**Status.** Implemented per user report. `uv sync` succeeded; focused tests
and the full 497-test suite passed.

## Goal

Build the retained, immutable candlestick chart from a ticker's injected daily
history result. Draw it in the existing history, preserve nested chart and
candle hits, and make direct headless clicks produce detail or exact-object
chips. Stop after the headless chart and a passing automated suite. The ticker
menu item, Rich colors, documentation wording, Textual screen test, live Yahoo
check, and demo belong to chart 001.

## Authority and starting point

The implementer receives this checkpoint and the accepted
[`../spec.md`](../spec.md); the checkpoint narrows the spec to one slice and
does not revise it.

- Identity: **chart 000**. Numbers begin at 000, have three digits, and are
  never renumbered. Complete this checkpoint and stop.
- Read spec sections 1–4 and the chart 000 gate in section 6. Section 3 is the
  fixed chart contract, and section 4 assigns this slice. The accepted spec
  governs any detail this checkpoint does not repeat. The charter is not an
  implementation input.
- There is no predecessor chart checkpoint. The implemented ticker `history`
  action and constructor-injected `ticker_history` seam, ordinary pandas
  presentation, nested `HistoryRow` fragments, layout, hit testing, history
  grouping, and Python chips are the starting point. Preserve them.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.
  Code and tests go there, not in this design folder.

## File scope

Create only `src/pbui/chart.py` and `tests/test_chart.py`. Edit only
`src/pbui/domain.py` and `src/pbui/commands.py` in addition to those new
files. Leave `src/pbui/terminal.py`, `src/pbui/bottom.py`, `src/pbui/text.py`,
`src/pbui/substrate.py`, other source and test files, and other design files
untouched. Leave `pyproject.toml` and `uv.lock` untouched; add no dependency.
Do not run `uv init` in this existing packaged project. If another file is
necessary, stop and send the checkpoint back to the checkpoint manager rather
than widening the slice.

## Chart values and capture

Add exact `Chart` and `Candle` presentation types in `domain.py`. Put immutable
chart and candle values, snapshot validation, price mapping, and the pure row
builder in `chart.py`. A chart retains the ticker's reported symbol, every
captured daily bar sorted oldest to newest, its most recent visible suffix,
and the omitted count. Each visible candle is a distinct object with the
captured ISO date and finite float Open, High, Low, and Close; omitted bars
have no candle presentation. Do not retain the mutable source frame as the
chart's data or mutate it during capture.

Expose a headless chart operation in `HeadlessListener` for one currently
retained ticker `Value`. Reject a non-ticker or stale presentation without a
fetch. Call the existing injected `ticker_history` callable exactly once on
the exact ticker for a valid source. Validate and build the entire chart
before appending its first row. On success, append chart rows without
appending the frame, set `_` to the chart object, and retain the ticker
subject to the 500-logical-row limit. A later frame mutation or `history`
call must not change the chart.

An empty frame, missing required OHLC column, non-`DatetimeIndex`, `NaT`
date, missing or non-finite OHLC value, reversed High/Low, or Open/Close
outside the Low–High range appends exactly one text row `no prices`, no chart,
and leaves `_` unchanged. A raised seam exception appends exactly one
existing-style `Error`, no chart, and leaves `_` unchanged. Neither outcome
removes the ticker. Keep the headless imports free of Textual and leave typed
calls to `ticker.history(...)` on the ordinary pandas path.

## Drawing and retained hits

Follow spec §3.2 exactly: 60 display cells, up to 15 most recent candles in
oldest-to-newest order, three cells per candle with one chart-owned gap,
12 plot rows, title, 60-cell horizontal date axis, endpoint date labels, and
an optional `… (N more days)` trailer. Use the specified half-up price-to-row
formula and the row-5 constant-price case. Draw inclusive High-to-Low stems,
left Open ticks, and right Close ticks, including `─│─` when they coincide.
Keep the chart at 15 logical rows without a trailer or 16 with one; normal
history grouping, indentation, wrapping, and retention apply.

Make one outer `Chart` presentation cover every drawn cell on every chart
row. Reuse one presentation for each visible `Candle` across all 12 plot
rows, wrapping its complete three-cell block even where the block is blank.
The title, gaps, padding, axis, labels, and trailer belong to the chart only.
Use the existing pure layout and hit test: a candle wins in any of its three
cells, while a gap or date label hits the chart. Do not add per-character
color data or a widget per candle.

## Direct selection and focused tests

In the existing headless selection route, an ordinary first left click on a
candle appends one text row in the spec §3.3 detail format and leaves `_`
unchanged. A chart-only click appends nothing. During valid Python
composition, a candle click inserts a chip containing that exact candle
object, and a chart-only click inserts the exact chart object. Use the spec's
`Candle YYYY-MM-DD` and `Ticker SYMBOL chart` chip labels; these clicks append
no detail. Preserve invalid-site refusal and existing open-menu,
pending-accept, substring-accept, and click-chain precedence. Add no accept
target or right-button menu for either type.

In `tests/test_chart.py`, use local dated `pandas.DataFrame` fixtures, a
`yfinance.Ticker` stand-in, and an injected callable. No test opens a socket.
Cover:

1. A valid retained ticker calls the seam once with the exact object,
   appends no frame, sets `_` to the chart, and leaves the ticker retained.
   A non-ticker or stale Value never fetches. Mutating the source frame after
   capture does not change the chart or candle values.
2. Empty data; missing `Close`; a non-date index; `NaT`, missing, non-finite,
   and incoherent OHLC values; and a raised seam exception produce their
   specified single-row outcomes, with no chart and unchanged `_`.
3. A 17-day fixture yields the last 15 dated candles, their exact four
   captured floats, and `… (2 more days)`. An out-of-order fixture sorts by
   date. Rising, falling, and flat candles map to the correct direction.
4. The 60-cell rows, top and bottom stem endpoints, Open-left and Close-right
   ticks, coincident ticks, axis, endpoint dates, and constant-price row 5
   match the fixed drawing rules.
5. At a width of at least 62 cells, layout gives the same candle on its
   occupied and blank plot cells across rows, and gives the chart on an
   adjacent gap and a date label. Ordinary candle and chart-only clicks,
   valid composition chips, and unchanged `_` obey the rules above.
6. Importing the headless listener and chart module does not import Textual.

Do not test menu choices, action replay, Rich styles, documentation
sentences, or the Textual screen in this checkpoint.

## Verification and completion

From the project root, use uv for the environment and every Python or test
command:

```console
uv sync
uv run pytest tests/test_chart.py
uv run pytest
```

`uv run pytest` is the automated gate; all old and new tests must pass. If
`uv` is unavailable, stop and report it. Do not substitute another package
manager, a direct Python command, or a hand-made environment. Do not run
`uv run pbui` for this slice.

Chart 000 is complete when its captured objects, drawing, nested hits,
headless selection, and failure outcomes meet the accepted spec and the full
suite passes. Report test results and changed files, then stop. Do not start
chart 001.
