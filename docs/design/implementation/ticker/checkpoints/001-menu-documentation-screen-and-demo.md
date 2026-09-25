# ticker 001 — Menu, documentation, screen, and demo

**Status.** Implemented. The focused tests (95) and full suite (482) passed.
The live AAPL check returned `DataFrame 22×7`, and its preview showed `Close`.

## Goal

Expose the retained ticker's `history` action through the existing Value
menu, document the click, verify the fixture screen path, attempt the one live
AAPL hand check, and write the demo. Stop when this slice is complete. Add no
other yfinance operation, quote, chart, period prompt, or new menu mechanism.

## Authority and starting point

The implementer receives this checkpoint and the accepted
[`../spec.md`](../spec.md); the checkpoint narrows the spec to one slice and
does not revise it.

- Identity: **ticker 001**. Checkpoint numbers have three digits, begin at
  000, and are never renumbered. The implementer completes this checkpoint
  and stops.
- Read spec sections 1–3, section 5, and the ticker 001 verification and
  acceptance in section 6. Section 4 describes the completed headless
  operation that this slice consumes. The accepted spec governs where this
  checkpoint is silent; the charter is not an implementation input.
- Predecessor: [ticker 000](000-headless-ticker-and-history.md) is implemented
  per user report. Its focused tests and all 477 project tests passed.
  `HeadlessListener.run_ticker_history` validates a retained ticker Value and
  calls the constructor-injected `ticker_history` callable through the normal
  result/Error path. This is the starting point, not a slice to reimplement.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.
  Code and tests live under `src/pbui/` and `tests/` there. The demo belongs
  in this feature's design folder.

## File scope

Edit only `src/pbui/commands.py`, `src/pbui/bottom.py`, `tests/test_ticker.py`,
and `tests/test_terminal.py`. Edit `src/pbui/terminal.py` only if its existing
Value menu route needs an adjustment to expose the new registered action.
Create `docs/design/implementation/ticker/demo.md` after implementation and
the hand check. Update the Demo row and status line in
`docs/design/implementation/ticker/README.md` when the demo exists; the
checkpoint's own status may record completion and verification results.

Leave `src/pbui/ticker.py`, `src/pbui/repl.py`, the pandas inspector, records
conversion, other source and tests, `pyproject.toml`, `uv.lock`, and the
accepted spec untouched. Ticker 000 already pinned `yfinance==1.7.0`; add
no dependency, run no `uv init`, and do not upgrade yfinance. Keep Textual
imports confined to `pbui.terminal`. If another file is necessary, stop and
send this checkpoint back to the checkpoint manager instead of widening its
scope.

## Ticker Value action and replay

For a retained `yfinance.Ticker` Value, expose exactly one action labeled
`history` in `HeadlessListener.python_translators_for`. Give no ticker action
to unrelated Values and no second action to a ticker. Use
`invoke_python_translator` and the existing Value popup route: right click or
Ctrl-O opens the menu; selecting `history` records one `MenuActionInput`
immediately before the resulting Value or Error. Hovering the ticker or
opening its menu must not call the injected history callable.

The selected action must use the same constructor-injected callable and the
same result/Error presentation path as ticker 000. Call it once on the exact
retained ticker. Do not call `ticker.history` directly from the menu, make a
second fetch path, or turn the action into generated Python source. On
success, append the same returned `DataFrame` as a new Value, set `_` to it,
and retain the ticker subject to the 500-row history limit. On failure,
append exactly one Error and no frame, leave `_` unchanged, and retain the
ticker. An empty frame remains a successful normal pandas Value.

The existing `run again` action must use its saved ticker object and saved
operation, call the seam again, and append a fresh action-input/result pair.
This still works when the original ticker row has left history but the saved
action row remains. Keep menu placement, dismissal, and suspended Python
composition behavior unchanged. Ordinary first left click on a ticker still
shows generic Value detail without a fetch; a valid composition click inserts
the ticker chip without a fetch. Pending accepts refuse the Value, and later
clicks in a click chain keep their established priority. The ticker and every
returned frame remain independently clickable for their existing behavior.

## Documentation

Extend the pure formatter in `src/pbui/bottom.py`. On an ordinary hover of an
`AAPL` ticker, the complete sentence is exactly:

```text
TICKER AAPL • Left: show • Right: menu
```

For another ticker, substitute its escaped reported symbol in the `TICKER
SYMBOL` target. During Python composition, keep the formatter's existing
insertion or refusal left clause and `Right: menu`. During a pending accept,
keep the existing wrong-type wording and menu precedence. A hovered
`history` popup item uses the existing Python Value item sentence, with no
special menu mode. Preserve documentation of non-ticker Values.

## Automated tests

Extend `tests/test_ticker.py` with fixture-only headless tests. Cover exact
`history` eligibility and no extra ticker action; the action input before a
successful frame or a failure Error; exact ticker and frame identities; `_`
after success and failure; a second selection or saved `run again` calling
the seam again on the saved ticker, including after the ticker row is
evicted; and no seam call from ordinary detail or composition clicks.
Verify the ordinary AAPL sentence, an escaped other symbol, composition
insertion and refusal clauses, pending-accept wording, and the popup item
sentence through the pure documentation formatter. Adjust only predecessor
assertions whose expected ticker action list changes from empty to
`history`.

Add **one** `PbuiApp.run_test()` screen test in `tests/test_terminal.py`.
Present a fixture ticker using an injected callable, hover it, open its
existing popup, choose `history`, and read the resulting `DataFrame` summary.
Assert that hover and menu opening alone make no history call, and selection
calls the callable once. Use the fixture frame, including a `Close` column
and date index; the test must not open a socket. Preserve the existing Value
menu route and other screen behavior.

## Verification, live hand check, and demo

From the project root, use uv for every Python, application, and test command:

```console
uv sync
uv run pytest tests/test_ticker.py tests/test_terminal.py
uv run pytest
```

`uv run pytest` is the automated gate; all old and new tests must pass. If
`uv` is unavailable, stop and report it. Do not substitute another package
manager, direct Python commands, or a hand-made environment.

After the automated gate, create a disposable directory under the project
root, record its absolute path, and launch from it:

```console
ticker_hand_dir="$(mktemp -d "$PWD/ticker-001-hand-XXXXXX")"
cd "$ticker_hand_dir"
pwd
uv run pbui
```

In the listener, enter `import yfinance`, then
`yfinance.Ticker("AAPL")`. Right-click its retained `Ticker AAPL` row and
choose `history`. Read a `DataFrame` summary with more than one row, open its
pandas preview, and find the `Close` column. Do not require a particular
price or date. This is one live AAPL request, with no other host or ticker
attempted. If Yahoo refuses it or returns an empty frame, report exactly
what happened; keep the fixture tests as the automated gate.

After implementation and the hand check, write
`docs/design/implementation/ticker/demo.md` as a hands-on tour of the
implemented path. Include the launch command, where to type, how to stop,
and that choosing `history` makes a live Yahoo request. Explain that dates
remain in the frame index and `To JSON records` omits that index; show
`_.reset_index()` as the Python step for including dates as a column before
conversion. Store no live prices. Update the feature README's Demo row and
status line when the file exists.

Ticker 001 is complete when the single ticker menu action, replay, result
and error ordering, documentation, and fixture screen path meet the accepted
spec; the full suite passes; the one live hand check is reported; and the
demo describes implemented behavior. Report verification and changed files,
then stop. Do not start another feature.
