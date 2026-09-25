# ticker 000 — Headless ticker and history

**Status.** Implemented per user report. Focused tests passed and `uv run pytest`
passed 477 tests.

## Goal

Retain a `yfinance.Ticker` as a Python Value with its symbol summary, and add
one injected, headless history operation that appends the returned pandas
`DataFrame`. Stop before exposing `history` in a menu, adding documentation or
a screen test, making a live Yahoo request, or writing the demo. Those belong
to ticker 001.

## Authority and starting point

The implementer receives this checkpoint and the accepted
[`../spec.md`](../spec.md); the checkpoint narrows the spec to one slice and
does not revise it.

- Identity: **ticker 000**. Numbers begin at 000, have three digits, and are
  never renumbered. The implementer completes this checkpoint and stops.
- Read spec sections 1–4 and the ticker 000 verification in section 6. Section
  3 governs identity, result, failure, and click behavior; section 4 governs
  this slice and its tests. The accepted spec governs where this checkpoint is
  silent. The charter is not an implementation input.
- There is no predecessor ticker checkpoint. The existing listener, pandas
  presentation, generic Value detail, chips, and 500-logical-row history limit
  are the starting point. Preserve their accepted behavior.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.
  Code and tests go there, not in this design folder.

## File scope

Create `src/pbui/ticker.py` and `tests/test_ticker.py`. Edit only
`src/pbui/commands.py`, `src/pbui/repl.py` if registration needs it,
`pyproject.toml`, and `uv.lock` in addition to those new files. Add the pinned
runtime dependency with `uv add 'yfinance==1.7.0'`, then run `uv sync`; do not
hand-edit dependency metadata or run `uv init` in this existing packaged
project.

Edit `tests/test_terminal.py` only in
`test_dependency_metadata_and_terminal_import_boundary`: add the exact
`yfinance==1.7.0` constraint to its expected runtime-dependencies list.
Leave the rest of that test and all other screen tests untouched.

Leave `src/pbui/terminal.py`, `src/pbui/bottom.py`, other source and test files,
and other design files untouched. Do not add a Value translator, ticker menu
item, colon command, accept type, quote view, indicator, or chart. If another
file is necessary, stop and send this checkpoint back to the checkpoint
manager instead of widening its scope.

## Registration and headless history

Register `yfinance.Ticker` and no other yfinance class in the existing
`ValueClasses` registry. Its raw printer returns `Ticker {value.ticker}` from
the object's reported symbol, without a network lookup. The existing Value
path escapes unsafe text, caps the whole row at 120 display cells, retains
the exact object, and supports its chip by identity. Importing yfinance for
registration must not bind it in the listener's Python namespace, which
starts exactly as `{"__name__": "__pbui__"}`. The user can bind it with
ordinary `import yfinance`.

In `src/pbui/ticker.py`, implement the production history adapter as a
one-argument callable. Given the exact ticker object, it calls
`ticker.history(period="1mo", interval="1d", timeout=15)` and returns the
library result. Pass no `progress` keyword and print no progress line.
Keep this module and the headless operation free of Textual imports.

Add one constructor-injected history callable to `HeadlessListener`, defaulting
to that production adapter. Give the listener a headless operation callable
with a retained ticker Value before any menu exists. It validates the source
presentation and ticker type, calls the injected callable exactly once for a
valid source, and never fetches from an unrelated or stale Value. Ticker 001
will route its menu action to this same operation, with no second fetch path.

On success, append the same `DataFrame` object returned by the callable as a
normal Value, set `_` to that frame, and leave the ticker in history subject
only to the existing row limit. Use the existing pandas summary, including
`DataFrame 0×C` for an empty frame with `C` actual columns. Repeating the
headless operation calls the seam again and appends another result. On a
raised exception, append exactly one existing-style `Error`, append no frame,
leave `_` unchanged, and retain the ticker. A user's typed
`ticker.history(period="1mo")` result follows the ordinary pandas Value path
and does not call the injected seam.

Keep `python_translators_for` from offering `history` in this checkpoint.
Opening a menu, recording `MenuActionInput`, and replaying the action are
ticker 001 work. Ordinary first left click remains generic Value detail and
must not call the history seam; Python-composition chip insertion also must
not call it. Preserve pending-accept and click-chain precedence.

## Focused tests

In `tests/test_ticker.py`, use a `yfinance.Ticker` stand-in reporting `AAPL`,
local pandas frames with a `Close` column and a date index, and injected
callables. Tests never contact Yahoo. Cover:

1. A fresh namespace lacks `yfinance`; an evaluated ticker presents exactly
   `Ticker AAPL`, retains the stand-in by identity, and yields a chip holding
   that same object.
2. An ordinary first left click shows generic Value detail without calling
   the injected history callable. No ticker `history` translator is exposed.
   A non-ticker or stale Value cannot cause a history fetch.
3. The first headless history call receives the exact ticker, appends the
   exact fixture frame, sets `_` to it, and retains the ticker. A second call
   invokes the callable again and appends another frame.
4. A raising callable appends one `Error` and no frame, leaves `_` unchanged,
   and retains the ticker. An empty fixture with `C` columns succeeds and
   displays `DataFrame 0×C`.
5. Calling `ticker.history(period="1mo")` in typed Python on the stand-in
   presents its frame through the normal pandas path without invoking the
   injected callable. Test the production adapter directly with a stand-in
   `history` method that records its keyword arguments and returns a fixture;
   assert exactly `period="1mo"`, `interval="1d"`, and `timeout=15`, with no
   `progress` argument.
6. Importing the headless listener and ticker module in the test process does
   not import Textual.

## Verification and completion

From the project root, use uv for dependency, Python, and test commands:

```console
uv add 'yfinance==1.7.0'
uv sync
uv run pytest tests/test_ticker.py tests/test_terminal.py::test_dependency_metadata_and_terminal_import_boundary
uv run pytest
```

`uv run pytest` is the automated gate; all existing tests must pass. If `uv`
is unavailable, stop and report it. Do not substitute another package
manager, direct Python commands, or a hand-made environment. Do not run
`uv run pbui` for this slice.

Ticker 000 is complete when its registration, retained identity, injected
history outcomes, adapter arguments, and focused tests meet the accepted
specification and the full suite passes. Report test results and changed
files, then stop. Do not start ticker 001.
