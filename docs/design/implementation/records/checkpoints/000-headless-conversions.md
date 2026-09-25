# records 000 — Headless conversions

**Status.** Implemented per user report. `uv sync` succeeded; 18 focused tests
and all 464 project tests passed. A temporary uv cache under `/tmp` was used
because the default cache was read-only.

## Goal

Create and test the pure conversions between retained JSON records and pandas
`DataFrame` values. Stop after the headless API and its focused tests. Menu
actions, history and `_` changes, documentation, screen behavior, the live hand
check, and `demo.md` belong to records 001.

## Authority and starting point

The implementer receives this checkpoint and the accepted
[`../spec.md`](../spec.md); the checkpoint narrows the spec to one slice and
does not revise it.

- Identity: **records 000**. Numbers begin at 000, have three digits, and are
  never renumbered. The implementer completes this checkpoint and stops.
- Read spec sections 1–3 and the records 000 gate in section 5. Section 3
  governs the function contracts, conversion rules, and focused tests. The
  accepted spec governs any detail this checkpoint does not repeat; the
  charter is not an implementation input.
- There is no predecessor checkpoint in this series. The implemented HTTP
  `JsonObject` and `JsonArray` types and pandas dependency are the starting
  point. Keep the predecessor behavior unchanged.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.
  Application code and tests go there, not in this design folder.

## File scope

Create only `src/pbui/records.py` and `tests/test_records.py`. The conversion
module imports no Textual code and opens no socket. Leave all other source and
test files, `pyproject.toml`, `uv.lock`, and design files untouched. Pandas and
pytest are already dependencies; add none. Do not run `uv init` in this
existing packaged project. If another file is needed, stop and send this
checkpoint back to the checkpoint manager instead of widening the slice.

## Conversion requirements

Expose `to_dataframe(value)` and `to_json_records(frame)` from
`pbui.records`. They return new complete values or raise an ordinary exception
with a useful message. Neither function touches listener history, `_`, the
input object, or the network.

`to_dataframe` accepts exactly a `JsonObject`, or exactly a `JsonArray` whose
elements are all exactly `JsonObject` values. An empty array qualifies. Reject
other roots, including plain `dict` and `list`, and reject mixed arrays rather
than filtering them. Make one row per record in source order, with columns in
first-seen key order across the records. One object makes one row; an empty
array makes a `0×0` frame; an empty object makes a `1×0` frame. Use the normal
positional index. A missing key is a missing cell, while an explicit JSON
`null` remains Python `None`. Preserve JSON scalar types without pandas
numeric or Boolean coercion. Keep a nested `JsonObject` or `JsonArray` as that
same object in one cell, without flattening or copying it. Validate the full
source JSON tree, including artificially constructed wrappers: string object
keys, supported JSON scalar leaves, finite numbers, and no container cycles.
Reject invalid data without substituting display text.

`to_json_records` accepts a pandas `DataFrame` or subclass and converts its
whole current content, not the bounded preview. Return a new `JsonArray` with
one new `JsonObject` per row, in row order; keep column order, use string
column labels as keys, and omit the index entirely. A zero-row frame returns
an empty array. Reject duplicate or non-string column labels, even with zero
rows. Convert missing scalars to `None`; convert Python and NumPy integer,
finite float, and Boolean scalars to Python JSON scalars; keep strings; and
convert pandas `Timestamp`, Python `datetime.datetime`, and NumPy
`datetime64` to ISO-8601 strings with offsets when present. Recursively build
new `JsonObject` and `JsonArray` wrappers for nested JSON wrappers, plain
`dict`, and plain `list` cells. Nested mapping keys must be strings. Detect
missingness only when the result is scalar. Reject infinity, unsupported
values, and cycles instead of stringifying them. Build the complete result
before returning, so a bad cell yields no partial result.

## Focused tests

In `tests/test_records.py`, test the functions directly, without Textual or a
network. Cover:

1. A two-record array with keys first seen in different records: row and
   column order, scalar types, a missing key, and explicit null. Check a
   single object, an empty object, an empty array, and a mixed array.
2. A nested JSON object retained as the identical value in one frame cell,
   with no extra column. Exercise invalid wrapper data, including a
   non-string key, a non-finite number, an unsupported leaf, and a cycle.
3. A frame with a named index and more than 12 rows or 6 columns: all rows and
   columns appear in JSON records, in order, without an index key. Exercise
   zero rows, missing scalars, timestamps with and without an offset, nested
   `dict`/`list` and JSON wrappers, and pandas or NumPy scalar cells.
4. Duplicate or non-string column labels, a non-string nested key, infinity,
   an inconvertible cell, and a nested cycle each raise without returning a
   partial array. Assert the source frame and source JSON remain unchanged.

Do not test listener menus, history, documentation, or the screen in this
checkpoint.

## Verification and completion

From the project root, use uv for the environment and every Python or test
command:

```console
uv sync
uv run pytest tests/test_records.py
uv run pytest
```

`uv run pytest` is the automated gate. If `uv` is unavailable, stop and report
it; do not substitute another package manager or a hand-made environment. Do
not run `uv run pbui` in this slice.

Records 000 is complete when both functions meet section 3 of the accepted
spec, focused tests cover the stated successes and rejections, and the full
suite passes. Report the results and changed files, then stop. Do not start
records 001.
