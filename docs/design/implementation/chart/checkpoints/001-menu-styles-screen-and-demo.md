# chart 001 — Menu, styles, screen, and demo

**Status.** Implemented per user report. `uv sync` succeeded, 108 focused
tests passed, and the full suite passed 505/505. The live AAPL `candlestick`
check returned `no prices`, so there was no live candle to hover; `history`
on the same retained ticker appended a `DataFrame 22×7` without a chart.
The fixture screen test verifies dated candle hover, and `demo.md` is written.

## Goal

Expose `candlestick` on the retained ticker's Value menu, preserve its saved
action for `run again`, style and document chart and candle presentations,
verify one fixture screen path, attempt the one live AAPL check, and write the
demo. Stop when this slice and its automated gate are complete. Add no other
chart action, plot type, chart library, window, or dependency.

## Authority and starting point

The implementer receives this checkpoint and the accepted
[`../spec.md`](../spec.md); the checkpoint narrows the spec to one slice and
does not revise it.

- Identity: **chart 001**. Numbers have three digits, begin at 000, and are
  never renumbered. Complete this checkpoint and stop.
- Read spec sections 1–3, section 5, and the chart 001 verification and
  acceptance in section 6. Section 4 describes the completed headless chart
  that this slice consumes. The accepted spec governs where this checkpoint
  is silent; the charter is not an implementation input.
- Predecessor: [chart 000](000-headless-chart-and-hits.md) is implemented per
  user report. `uv sync`, its focused tests, and all 497 project tests passed.
  Its `HeadlessListener.run_ticker_chart` validates a retained ticker Value,
  calls the injected history seam, and appends the chart or its one-row
  refusal/Error. Its chart and candle presentations already support headless
  hits, detail clicks, and exact-object chips. Consume that behavior; do not
  rebuild its capture or drawing.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.
  Code and tests live under `src/pbui/` and `tests/` there. The demo belongs
  in this chart design folder.

## File scope

Edit only `src/pbui/commands.py`, `src/pbui/bottom.py`,
`src/pbui/terminal.py`, `tests/test_chart.py`, and `tests/test_terminal.py`.
In `tests/test_ticker.py`, edit only the two action-list expectations at the
current lines 97 and 212 to expect `history`, then `candlestick`; rename the
affected test if its name would otherwise claim `history` is the only ticker
action. Preserve every other ticker-history assertion. Create
`docs/design/implementation/chart/demo.md` after implementation and the hand
check. Leave `src/pbui/chart.py`, `src/pbui/domain.py`,
`src/pbui/text.py`, `src/pbui/substrate.py`, the ticker adapter, pandas
preview, records conversion, other source and test files, `pyproject.toml`,
`uv.lock`, and the accepted spec untouched. Do not run `uv init` or add a
dependency. Keep Textual imports confined to `pbui.terminal`. If another
file is necessary, stop and send this checkpoint back to the checkpoint
manager rather than widening the slice.

## Ticker action and replay

For a retained `yfinance.Ticker` Value, expose exactly two menu actions in
this order: `history`, then `candlestick`. Use the existing Value popup route;
opening or hovering the menu must not call the injected history seam. An
ordinary first left click on the ticker still shows generic detail, and a
valid Python-composition click still inserts the ticker chip, with no fetch.
Do not add a chart or candle menu, accept target, generic frame plot action,
colon command, or second Yahoo adapter.

Choosing `candlestick` records one `MenuActionInput` row before any result,
then calls the same constructor-injected `ticker_history` callable once on
the exact retained ticker. Route the action to the chart append path from
chart 000, not through the generic Value translator result path. On success,
append the captured chart and no `DataFrame`, set `_` to that chart, and
retain the ticker subject to the history limit. On empty or invalid data,
append only `no prices` after the action row, no chart, and leave `_`
unchanged. On a raised fetch, append only one existing-style `Error` after
the action row, no chart, and leave `_` unchanged.

Save the original ticker object and chart operation in the action input.
`run again` records a fresh action-input row and calls the same seam once,
even after the original ticker row has left history while the saved action
row remains. This replay applies the same chart, `no prices`, and Error
rules. Its saved operation must not depend on the original ticker
presentation still being retained. Preserve saved and replayed `history`:
each choice calls the seam once and appends its returned frame, including an
empty frame, through the ordinary pandas path without drawing a chart.
Keep popup placement, dismissal, suspended composition, pending-accept, and
click-chain precedence unchanged.

## Styles and documentation

In `presentation_style`, color each whole rising or flat candle `#00d787`
and each whole falling candle `#ff5f5f` outside accept. A hovered candle
reverses only that candle's three-cell blocks across its 12 plot rows;
other candles, chart-owned gaps, title, axis, labels, and trailer do not
reverse. Chart-owned cells use ordinary history color, and a chart-only
hover follows the existing outer-presentation hover rule. During pending
accept, chart and candle presentations use the listener's inert dim-gray
style, without acceptable-target green. Apply styles through presentation
intervals, not per-character color fields.

In the pure documentation formatter, recognize retained `Chart` and
`Candle` presentations. In ordinary mode the complete target-first
sentences for these examples are exactly:

```text
CANDLE 2026-09-21 (rose) • Left: show • Right: no menu
CANDLE 2026-09-22 (fell) • Left: show • Right: no menu
CHART AAPL • Left: no action • Right: no menu
```

`rose` includes a flat day. Substitute the captured date or safely escaped
reported symbol. A valid Python-composition site uses `Left: insert value
into expression`; invalid sites keep the existing insertion-refusal wording.
A pending accept uses the existing wrong-type wording and cancel suffix with
`Candle` or `Chart` as the type. Keep the documentation line's existing
fitting and truncation behavior. Preserve ticker, frame, popup item, and
other existing documentation.

## Automated tests

Extend `tests/test_chart.py` with local fixture-only tests. Cover the exact
two menu labels and order; no seam call from ticker hover, ordinary detail,
composition insertion, or menu opening; one call on each `candlestick`
choice or replay; action-input ordering before chart, `no prices`, or Error;
unchanged `_` on refusal/failure; and no appended frame on chart success.
Prove `run again` uses the saved exact ticker after its row is evicted while
the action row remains. Verify that choosing or replaying `history` still
appends the returned frame, including an empty frame. Cover the ordinary,
valid-composition, invalid-composition, and pending-accept documentation,
including rising, falling, flat, chart-only, and safely escaped symbols.
Assert green and red Rich colors, reverse hover limited to the hovered
candle, ordinary chart color, and inert pending-accept styles. No automated
test contacts Yahoo.

Update the two predecessor ticker action-list assertions permitted above;
they must reflect the spec's two-item ticker menu without weakening the
existing checks of `history` behavior. Add exactly one fixture
`PbuiApp.run_test()` test to `tests/test_terminal.py`. Use an injected local
frame containing at least one
rising and one falling candle, with a screen wide enough to show the 60-cell
chart and its result indent. Present a ticker, open its existing menu, choose
`candlestick`, and inspect both candle styles. Hover the falling candle and
assert that only its blocks reverse, its documentation names its captured
date and direction, and a between-candle hit names the chart. Hover and menu
opening alone must not fetch; choosing the item calls the fixture seam once.
Exercise the existing screen route without opening a socket or creating a
second chart widget.

## Verification, live hand check, and demo

From the project root, use uv for the environment and every Python, test,
and application command:

```console
uv sync
uv run pytest tests/test_chart.py tests/test_terminal.py
uv run pytest
```

`uv run pytest` is the automated gate; all old and new tests must pass. If
`uv` is unavailable, stop and report it. Do not substitute another package
manager, direct Python commands, or a hand-made environment.

After the automated gate, create a disposable directory under the project
root, record its absolute path, and launch the existing app from it:

```console
chart_hand_dir="$(mktemp -d "$PWD/chart-001-hand-XXXXXX")"
cd "$chart_hand_dir"
pwd
uv run pbui
```

In the listener, enter `import yfinance`, then evaluate
`yfinance.Ticker("AAPL")`. Choose `candlestick` on its retained ticker Value.
Read the chart, point at one candle, and read its date on the documentation
line. Find the retained ticker and choose `history`; confirm it appends a
pandas frame without drawing a chart. Do not require a particular date,
price, row count, or both color directions in the live month; the fixture
screen test proves both directions. These two chosen actions make live Yahoo
requests. If Yahoo refuses or returns no bars, report the result without
weakening the automated gate or trying another host or ticker as part of
this check. `uv run pbui` is only the hand check.

After implementation and the hand check, write
`docs/design/implementation/chart/demo.md` as a hands-on tour of that same
path. Include the exact launch command, where to type, how to stop, and that
choosing either ticker action makes a live Yahoo request. Describe the chart,
candle click detail, hover documentation, and unchanged `history` frame path.
Store no live prices.

Chart 001 is complete when the two ticker actions and saved replay, chart
styles, target-first documentation, fixture screen path, and demo meet the
accepted spec; the full suite passes; and the live hand check is reported.
Report verification and changed files, then stop. Do not start another
feature.
