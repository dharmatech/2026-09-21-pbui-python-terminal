# pandas 001 — Preview history and screen clicks

**Status.** Implemented per user report. `uv sync` succeeded; focused tests
passed 93/93 and `uv run pytest` passed 446/446. The live listener check
passed in
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/pandas-001-hand-Bewh4j`.

## Goal

Make a normal click on a retained frame or series summary append its bounded
detail to history. Give a frame preview exact column-header and row-label hits
that present the cached pandas copies, and make the screen and documentation
describe those clicks. Complete the automated gate and the live hand check.
Stop after this slice; do not add pandas commands, menus, filtering, plotting,
or cell extraction.

## Authority and starting point

The implementer receives this checkpoint and the accepted
[`../spec.md`](../spec.md); the checkpoint narrows the spec to one slice and
does not revise it.

- Identity: **pandas 001**. Checkpoint numbers have three digits, begin at 000,
  and are never renumbered. The checkpoint manager writes one number and
  stops; each implementer completes one number and stops.
- Read spec sections 1–3, section 5, and section 6. Section 4 defines the
  completed headless interface that this slice consumes. The accepted spec
  governs where this checkpoint is silent; the charter is not an
  implementation input.
- Predecessor: [pandas 000](000-headless-model-and-registration.md) is
  implemented per user report; `uv run pytest` passed 441 tests. Its code is
  the starting point, not a slice to reimplement.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.
  Code and tests remain under `src/pbui/` and `tests/` there.

## File scope

This slice may edit only `src/pbui/pandas_inspector.py`, `src/pbui/commands.py`,
`src/pbui/repl.py`, `src/pbui/domain.py` for the two exact presentation types
and their drawers, `src/pbui/bottom.py`, `src/pbui/terminal.py`,
`tests/test_pandas.py`, and `tests/test_terminal.py`. Use only the files needed
for this behavior. Keep `pyproject.toml`, `uv.lock`, `src/pbui/text.py`,
`src/pbui/substrate.py`, other tests, other design files, and existing
non-pandas behavior untouched. If another file is necessary, stop and return
this checkpoint to the checkpoint manager instead of widening its scope.

No new dependency, `uv init`, presentation registry, Textual cell widget, or
listing-owned preview block belongs here. Keep Textual imports confined to
`pbui.terminal`; use the existing `DrawingContext`, `HistoryRow`, and pure
layout fragments in the one history surface.

## Append captured detail

On a normal first left click on a retained `DataFrame` `Value`, call the
completed `HeadlessListener.capture_pandas_frame(presentation)`. Append a
table built from that `FramePreview`; leave the original summary and `_`
unchanged. Each later click on that summary captures the frame again, so
source cell assignments made between clicks appear only in the later preview.
On a normal first left click on a retained `Series` `Value`, call
`list_pandas_series(presentation)` and append its already formatted rows as
literal history content. Leave the series summary and `_` unchanged.

Build and validate the complete preview or series list before appending its
first row. If capture or formatting raises, append exactly one existing-style
`Error`, no partial table or list, and leave `_` unchanged. Do not write a
transcript command row for either click. Keep the ordinary 500-logical-row
history limit.

## Frame rows and exact hits

Draw from `FramePreview.snapshot`, `column_labels`, `row_labels`, `cell_text`,
`omitted_columns`, `omitted_rows`, and `selectable`. The model from 000 already
escapes and caps each label and cell; do not read or reformat the source frame.
The first logical row begins with literal `index`, then up to six displayed
column labels. Each of up to 12 data rows begins with its displayed index
label, then the visible cells. For each field, left-align and pad to the
maximum displayed width in that visible column; the index field is at least
as wide as `index`. Separate fields with exactly two spaces and leave no
padding after the final field. Measure display cells, not code points.
Physical wrapping does not create logical rows or extend a hit into another
field.

Handle the boundaries exactly:

- Zero rows and zero columns: only `empty DataFrame`.
- Columns but no rows: header, then `no rows`.
- Rows but no columns: `index`, then one row-label-only row per visible row.
- Omitted columns: `… (N more columns)` after visible data rows, before any
  omitted-row trailer. With columns but no rows, it goes between header and
  `no rows`.
- Omitted rows: finish with `… (N more rows)`.

For a snapshot whose **both** axes have `nlevels == 1`, register exact
`PandasColumn` and `PandasRow` presentation types and put one presentation on
each displayed column header and row label. The column presentation stores
the exact `FramePreview.column_at(position)` Series; the row presentation
stores the exact `FramePreview.row_at(position)` one-row DataFrame. Select by
integer position, including when labels repeat. A hit covers only the
displayed label characters, including the visible `''` substitute for an
empty label. The literal `index` corner, padding, separators, cells, trailers,
`empty DataFrame`, `no rows`, and every series-list row have no presentation
or chip source. If either axis is a MultiIndex, display its escaped labels
but create **no** column or row hits on either axis.

One preview uses no more than 15 logical rows: header, 12 data rows, and at
most two trailers. It does not by itself evict a source summary among the
newest 400 rows; normal history eviction otherwise applies. Preview rows
are ordinary append-only history rows, never listing-owned replacements.

## Click routing, chips, and documentation

In ordinary mode, a normal first left click on a retained `PandasColumn` or
`PandasRow` hit calls the 000 `present_pandas_copy` path with that hit's
stored object. It appends one new `Value` summary, sets `_` to the exact
cached Series or DataFrame, and leaves the preview in place. Clicking the same
hit again presents the same cached object by identity; do not recapture or
reslice the source. Add no menu action or transcript command row.

Preserve the existing precedence: an open menu handles its own click; pending
presentation and substring accepts retain their behavior; a valid Python
composition site makes a first left click on a frame summary, series summary,
header, or row label insert a chip of that presentation's stored object.
Those clicks do not preview, list, or extract. An invalid composition site
keeps the existing refusal. Later clicks in a click chain do nothing. Literal
preview text is inert in every mode, including composition. Typed `:show`
still rejects pandas Values. Button 3 and Ctrl-O open no menu for these
targets.

Extend the pure formatter in `src/pbui/bottom.py` so ordinary-mode target
sentences are exactly:

```text
DATAFRAME • Left: show frame preview • Right: no menu
SERIES • Left: list values • Right: no menu
PANDAS COLUMN • Left: take column • Right: no menu
PANDAS ROW • Left: take row • Right: no menu
```

The existing width rule may fit or truncate them on screen. During Python
composition use the existing chip insertion or refusal wording with these
targets; during a pending accept use its existing wrong-type wording.
Multilevel labels and literal preview content have no target-specific
sentence. Preserve the existing no-menu response.

## Automated tests

Extend `tests/test_pandas.py` with headless checks of exact table strings,
display-cell alignment, all empty-axis cases, both omission counts and their
order, the 15-row maximum, and literal versus presented fragments. Prove
preview and series-list clicks leave `_` and source Values unchanged; a
second source click sees later cell assignment while the first preview and
its cached objects remain fixed. Repeated header and row clicks must present
the same stored copy by identity and set `_`. Cover duplicate labels,
MultiIndex on either axis (no hits at all), stale hits, and one-`Error`
atomicity when capture or formatting fails. No automated test opens a
network connection.

Extend `tests/test_terminal.py` with `PbuiApp.run_test()` coverage. Click a
frame summary, the second of two equal-labeled headers, and a row label;
check resulting types, object identities, and `_`. Click a cell and padding
beside a label and prove no action or chip. Cover a valid composition click
on a header, an invalid composition site, ordinary documentation sentences,
one MultiIndex preview without extraction hits, the no-menu response, and a
later click in a click chain. Preserve all predecessor screen tests.

## Verification and completion

From the project root, use only uv-managed commands:

```console
uv sync
uv run pytest tests/test_pandas.py tests/test_terminal.py
uv run pytest
```

`uv run pytest` is the automated gate. If uv is unavailable, stop and report
it; do not substitute pip, `python -m pip`, Poetry, Pipenv, Conda, Hatch, or
a hand-made environment. Keep `requires-python` at `>=3.11`.

After the automated gate, make the spec's live hand check. Create a
disposable directory under the project root, print and record its absolute
path, change into it, and launch the listener:

```console
cd /home/dharmatech/journal/2026-09-21-pbui-python-terminal
pandas_hand_dir="$(mktemp -d "$PWD/pandas-001-hand-XXXXXX")"
printf '%s\n' "$pandas_hand_dir"
cd "$pandas_hand_dir"
uv run pbui
```

In one listener session, run `import pandas`; make and evaluate a small frame
with one missing value and two columns both labeled `same`. Read its
`DataFrame R×C` summary, click it, and inspect the captured table. Click the
second duplicate header and use the resulting Series as a chip in a later
Python expression. Click a row label and see a one-row DataFrame. Click the
Series summary to list its values. Assign a different value to a source
frame cell, click the old frame summary again, and confirm the new preview
changes while the first stays fixed. No destructive listener command is
needed. Record the disposable directory path and result in the completion
report; the hand check complements the automated gate. If the live session
cannot be completed, report that limitation rather than claiming completion.

Pandas 001 is complete when the accepted spec's history, hits, precedence,
documentation, and test bar all hold, the full suite passes, and the hand
check is completed and reported. Report changed files and verification,
then stop. Do not start another checkpoint or unrelated feature.
