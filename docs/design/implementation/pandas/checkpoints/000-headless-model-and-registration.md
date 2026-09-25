# pandas 000 — Headless model and registration

**Status.** Implemented per user report; `uv run pytest` passed 441 tests.

## Goal

Retain pandas frames and series as typed Python Values, capture a bounded frame
preview with positional copies, and format a bounded series list. Make these
operations callable and testable without Textual. Stop before appending preview
history rows, adding preview presentations or screen clicks, or doing the live
hand check; those belong to pandas 001.

## Authority and starting point

The implementer receives this checkpoint and the accepted
[`../spec.md`](../spec.md); the checkpoint narrows the spec to one slice and
does not revise it.

- Identity: **pandas 000**. Numbers begin at 000, have three digits, and are
  never renumbered. The checkpoint manager writes one checkpoint and stops;
  each implementer completes one checkpoint and stops.
- Read spec sections 1–4 and the layer 000 verification in section 6. Sections
  3 and 4 govern exact text, limits, snapshot behavior, and tests. The accepted
  spec governs where this checkpoint is silent; the charter is not an
  implementation input.
- There is no predecessor checkpoint in this series. The existing listener,
  REPL, SymPy, HTTP, chips, and listings behavior is the starting point. Keep
  their accepted behavior, including the 500-logical-row history limit.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.
  Application code and tests live there, not in the design folder.

## File scope

Create `src/pbui/pandas_inspector.py` and `tests/test_pandas.py`. Edit only
`src/pbui/repl.py`, `src/pbui/commands.py`, `pyproject.toml`, and `uv.lock` in
addition to those new files. Add the runtime dependency through `uv add pandas`;
do not hand-edit dependency metadata. The project already has a packaged `src/`
layout; do not run `uv init` again.

Edit `tests/test_terminal.py` only in
`test_dependency_metadata_and_terminal_import_boundary`: add the pandas
runtime dependency to its exact expected `dependencies` list, matching
`pyproject.toml` after `uv add pandas`. Leave the rest of that test and all
other tests in that file unchanged. This narrow exception is needed for the
full-suite gate; it adds no pandas screen behavior to 000.

Leave `src/pbui/terminal.py`, `src/pbui/domain.py`, `src/pbui/bottom.py`,
`src/pbui/text.py`, other existing tests, and other design files untouched. Do not
add a presentation type, translator, menu, colon command, accept type, or
listing reuse. If another file is needed, stop and return this checkpoint to
the checkpoint manager rather than widening the slice.

## Registration and summaries

Register `pandas.DataFrame` and `pandas.Series` in the existing `ValueClasses`
registry at listener startup. Give each only a summary printer; lookup still
uses the first registered class in `type(value).__mro__`. Importing pandas for
registration must not bind it in the listener's Python namespace. That
namespace starts exactly as `{"__name__": "__pbui__"}`; a user's ordinary
`import pandas` binds the name.

The printers return raw `DataFrame R×C`, `Series N NAME DTYPE`, or unnamed
`Series N DTYPE` text, using the lengths, name, and dtype at presentation time.
The existing Value path escapes and caps the complete row at 120 display
cells. It retains the original object by identity and follows the existing
`_` and chip rules. Keep generic Value printing for dicts, lists, NumPy
arrays, and other unregistered classes. Do not register `Index`, `ndarray`,
NumPy scalars, plain dict, or plain list.

## Headless model interface

Use `src/pbui/pandas_inspector.py` for pure formatting and capture. Expose
`capture_frame(frame)` returning a `FramePreview` and `list_series_values(series)`
returning a tuple of already formatted logical row strings. `FramePreview`
must expose its owned `snapshot`, its visible `column_labels` and `row_labels`
as formatted strings, its rectangular `cell_text` as formatted strings, its
`omitted_columns` and `omitted_rows` counts, and whether both axes are
single-level (`selectable`). It must provide `column_at(position)` and
`row_at(position)` to return the cached pandas object for an integer position
within the visible window, or `None` outside that window. The names in this
paragraph are the interface for pandas 001; its screen formatter will consume
the captured strings and cached objects without reading the source frame
again.

`capture_frame` calls `frame.copy(deep=True)` once and takes first-position
windows of at most 12 rows and 6 columns. Cache each visible column as
`snapshot.iloc[:, position].copy()` and each visible row as
`snapshot.iloc[[position]].copy()`. Preserve duplicate labels by positional
selection. Later source cell assignments cannot alter the snapshot, its
formatted strings, or cached objects; capturing again observes the later
state. The source Value still owns the original. A Python object nested in an
object-dtype cell is subject to pandas' documented deep-copy limit.

Format labels with escaped `str(label)` capped at 24 display cells, using
`''` for an otherwise zero-width label. Format cells with plain `str(value)`
or `NA` for a missing scalar. Treat an array-like result from `pandas.isna`
as non-scalar, so a container cell uses its ordinary string. Escape before
truncating; use the existing `truncate_display` for wide and combining
characters. Cells have a 16-display-cell cap including `…`. For series,
apply the same missing-scalar and plain-string rule to each value, then format
first-position rows as `[POSITION]  VALUE`, with the whole escaped row capped
at 120 display cells; the 16-cell preview-cell cap does not apply. Return
`("no values",)` for an empty series; for
more than 12 values add exactly `… (N more values)` after the first 12 rows.
The returned tuple is captured text and never presents a scalar or changes
`_`.

Expose headless listener operations that validate an exact retained `Value`
presentation before capturing a frame or listing a series. Name them
`capture_pandas_frame(presentation)` and
`list_pandas_series(presentation)`; return `None` for a stale presentation,
wrong presentation type, or wrong pandas source type. These operations do not
append history rows or change `_`. Add `present_pandas_copy(value)` to append
one normal Value for a cached column Series or one-row DataFrame and set `_`
to that exact cached object. Reject a non-pandas value without appending. A
caller obtains a valid copy from `FramePreview.column_at` or `row_at`; an
invalid position returns `None`, so it causes no extraction. Pandas 001 will
use `present_pandas_copy` for a click on the stored hit object, without
reslicing or recapturing the source.

## Focused tests

In `tests/test_pandas.py`, use a headless listener and local pandas objects.
Cover:

1. Fresh namespace, user import, exact frame and named/unnamed series
   summaries, specified `int64`, `object`, and `boolean` dtypes, original
   Value identity, `_`, and a chip that holds the original by identity.
2. Registry lookup and no translators for pandas classes; ordinary generic
   rows for a dict, list, and NumPy array. Keep pandas Values outside file,
   directory, and process accepts.
3. A captured preview's 12-row and 6-column windows, omission counts,
   escaped and capped labels and cells, missing scalars, and wide/combining
   text. Use positional selection to take the second of two equal-labeled
   columns and a one-row frame. Assert cached object identity when presented
   and `_` changes only on extraction.
4. Change a source frame cell through pandas assignment after capture: the
   first snapshot, text, and cached copies stay fixed; a second capture sees
   the new value. Test invalid/stale source presentations and out-of-window
   positions produce no extraction.
5. A 13-value series yields exactly 12 positional rows and one omission
   trailer; an empty series yields `no values`. Listing a series and capturing
   a frame leave `_` unchanged. Importing the model and headless listener
   does not import Textual.

Use cells without nested mutable Python objects for the snapshot-isolation
test. Automated tests use no network.

## Verification and completion

For a fresh implementation, add the dependency once with `uv add pandas`.
It has already been added for this in-progress implementation; do not add it
again. From the project root, use uv for every Python and test command:

```console
uv sync
uv run pytest tests/test_pandas.py tests/test_terminal.py::test_dependency_metadata_and_terminal_import_boundary
uv run pytest
```

`uv run pytest` is the automated gate. If `uv` is unavailable, stop and
report it; do not substitute pip, `python -m pip`, Poetry, Pipenv, Conda,
Hatch, or a hand-made environment. Do not run `uv run pbui` for this slice.

Pandas 000 is complete when the registered summaries, headless capture,
cached extraction, and series text meet the accepted spec and the full suite
passes. Report test results and changed files, then stop. Do not start pandas
001.
