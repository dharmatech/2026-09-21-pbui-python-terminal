# Charter — JSON records and DataFrames

**Status.** Handoff from the high-level discussion into a **design
conversation**. Not a checkpoint. Not an implementer assignment.
This file lives in `docs/design/implementation/records/`. The
specification will live beside it as [`spec.md`](spec.md).
Checkpoint files will live in `checkpoints/` beside it. Map:
[`README.md`](README.md). The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

**Your job.** Turn this charter into a specification for converting
JSON records into a pandas `DataFrame`, and a `DataFrame` back into
JSON records. The series identity is **records**. Then **stop**.
Do not write checkpoints. Do not implement.

The specification refuses nested-field flattening, a Series
conversion, a ticker, and a chart. Those refusals keep the series
small enough to slice.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Read the HTTP specification for `JsonObject` and `JsonArray`, and
   the pandas specification for the frame summary, the preview, and
   the sentence `DATAFRAME • Left: show frame preview • Right: no
   menu`. Read `python_translators_for` and the documentation
   formatter. A left click still lists JSON members or opens a frame
   preview. This series adds menu actions only.
3. Record the locked decisions in §4. There is no open-question
   section.
4. Write `spec.md` in this folder. A later checkpoint-manager
   conversation slices **records 000**, then **records 001**, under
   `checkpoints/` here, one checkpoint per conversation.
5. Stop. The human reviews the spec. Do not write those checkpoint
   files.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification.

Keep the spec to the two conversions. A `json_normalize` step, a
`yfinance` object, or a plot is a defect in this document.

## 2. Predecessors

HTTP and pandas are implemented. A JSON object is a `JsonObject` and
a JSON array is a `JsonArray`. A left click lists the immediate
members. A `DataFrame` keeps its identity, summarizes as
`DataFrame R×C`, and a left click opens a snapshot preview. Neither
JSON value nor a frame has an action menu today. The listener
already has `:get`, `perform`, and `json`.

This exploration adds no dependency. Pandas is already installed.
The designer does not run uv.

The public demo is the Treasury Fiscal Data debt table. It needs no
API key. The URL in §4.6 returns a JSON object whose `data` member
is an array of flat records with the keys `record_date` and
`tot_pub_debt_out_amt`. The amounts arrive as text. Automated tests
use fixtures and never open a socket.

| Place | What goes there |
|---|---|
| `docs/design/implementation/records/` | This charter, `spec.md`, `demo.md`, and `checkpoints/` |
| Project root | The existing `pbui` package and `tests/` |

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **An array of records becomes a frame.** The menu action
   `To DataFrame` on a `JsonArray` of `JsonObject` values appends a
   `DataFrame` with one row per element and one column per key. The
   array stays in history. The inspector can open the frame.
2. **One object becomes one row.** The same action on a `JsonObject`
   appends a one-row frame whose columns are that object's keys.
3. **The frame becomes records.** `To JSON records` on a `DataFrame`
   appends a `JsonArray` of `JsonObject` values for the whole frame.
   The index is absent. A left click lists those records.
4. **The awkward cases stay out of the table.** An array that
   contains anything other than a JSON object offers no action.
   Nested objects are cell values, not new columns. A column label
   that is not a string, or a cell that is not JSON data, appends
   one `Error`.
5. **The Treasury path is the demo.** `:get`, `perform`, `json`, dig
   to `data`, then `To DataFrame` produces a frame whose columns
   include `record_date` and `tot_pub_debt_out_amt`. The demo does
   not promise a date or an amount.
6. **Old tests still pass.** `requires-python` stays `>=3.11`.

## 4. Locked decisions (record these; do not reopen)

### 4.1 To DataFrame

`To DataFrame` is a menu action. It is present in exactly these
cases:

| Value | Result |
|---|---|
| `JsonArray` whose every element is a `JsonObject`, including an empty array | One row per element. Columns are the keys in the order they are first encountered. A missing key is a missing cell. |
| `JsonObject` | One row. Columns are that object's keys, in its order. |

Any other `JsonArray` has no `To DataFrame` action and keeps
`Right: no menu`. A left click still lists members.

The new value is a pandas `DataFrame`. JSON strings, numbers,
booleans, and null stay those Python values. A nested `JsonObject`
or `JsonArray` stays that object in the cell. This series does not
flatten nested fields. The source value stays in history. Success
sets `_` to the frame. A failure appends one `Error`, appends no
frame, and leaves `_` unchanged.

An empty array produces `DataFrame 0×0`.

### 4.2 To JSON records

`To JSON records` is the only menu action this series adds to a
`DataFrame`. It converts the whole frame, not the visible preview.
Each row becomes one `JsonObject`, in row order, and the result is
one `JsonArray` of those objects. The index, including a named
index, is not a column and not a key.

A missing cell becomes JSON null. A timestamp becomes an ISO-8601
string. Integers, floats, booleans, and strings become those JSON
values. A `JsonObject`, `JsonArray`, `dict`, or `list` in a cell
becomes nested JSON. Every column label must be a string. A label
that is not a string, or a cell that cannot be one of those JSON
values, appends one `Error` and no array.

The source frame stays in history. Success sets `_` to the array.
The conversion is not a lossless round trip: the index is gone, and
a timestamp does not come back as a timestamp.

A `Series` gains no action.

### 4.3 What the click and the sentence do

The ordinary left click is unchanged. JSON still lists members. A
frame still opens its preview. A column or row extraction still
works. During composition, a left click still inserts a chip. The
new actions run only from the menu.

When `To DataFrame` is present, the documentation right clause for
that JSON value is `menu`. The left clause stays `list members`.
When `To JSON records` is present, the DataFrame sentence keeps
`Left: show frame preview` and its right clause is `menu`. A
`Series` sentence stays `Right: no menu`. The existing menu-item
sentence names the chosen action. The spec writes those sentences
in the current target-first form.

### 4.4 What stays as it is

`:get`, `perform`, `json`, and dig stay as they are. The preview
window, the series list, sorting, filtering, and grouping stay as
they are. There is no new colon command, no ticker, no indicator,
and no chart. `json_normalize` is not used.

### 4.5 Tests

Headless tests build JSON values and frames without Textual and
without a network. Cover at least: an array of two flat records
becomes a frame with those columns, in first-seen key order, and
retains the strings it was given; a later record that lacks a key
leaves a missing cell that the inspector shows as `NA`; one object
becomes one row; an empty array becomes `DataFrame 0×0`; an array
containing a string has no action; a nested object stays one cell
and does not add columns; `To JSON records` on that frame returns
records without the index; a missing cell becomes null; a timestamp
becomes an ISO-8601 string; a non-string column label and an
inconvertible cell each append one `Error` and leave `_` unchanged;
a successful conversion sets `_` to the new value and leaves the
source in history.

Records 000 proves the conversions. The menus may stay unwired there.

Records 001 adds the two menu actions, the documentation right
clauses, one screen test, the hand check, and `demo.md`. The screen
test opens `To DataFrame` on a fixture array and `To JSON records`
on the resulting frame.

The hand check needs the network. From a disposable directory, run
`uv run pbui`. Enter:

```text
:get https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny?sort=-record_date&page[size]=10&fields=record_date,tot_pub_debt_out_amt
```

`perform`, then `json`, then dig to `data`. Choose `To DataFrame`.
The summary shows a frame with one row per returned record and the
columns `record_date` and `tot_pub_debt_out_amt`. Open the preview
and read those columns. Choose `To JSON records` and list the
records. Do not require a particular date or amount. If the host
refuses the request, report that and do not weaken the automated
gate. `uv run pytest` is that gate. `uv run pbui` is only the hand
check.

`demo.md` records that same path, including the URL, and states that
the debt figures change. It does not store a response body.

### 4.6 Slice order

**records 000** converts fixture JSON and frames without Textual.

**records 001** wires the menus, updates the documentation clauses,
and adds the screen test, the hand check, and the demo.

Do not add a slice for nested flattening, a ticker, or a chart.

## 5. Authority

The HTTP specification is the law for `JsonObject`, `JsonArray`,
dig, and `:get`. The pandas specification is the law for the frame
summary, the preview, and extraction. The popup specification is
the law for the menu.

Where this charter and an earlier specification disagree about a
menu on an eligible JSON value or on a `DataFrame`, this exploration
wins. Where they disagree about a left click, a preview, or a
generic value, the earlier specification wins.

## 6. Handoff reminder

The series identity is **records**. Checkpoint 000 is spoken
**records 000** and filed as `checkpoints/000-slug.md`. Checkpoint
001 is spoken **records 001**. Numbers are three digits, start at
000, and are never renumbered. The slug is lowercase words separated
by hyphens. The checkpoint manager writes one checkpoint, then
stops. Code and tests go at the project root
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`, not in
this folder.

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. The first identity is **records 000**.
The second, in a later conversation, is **records 001**.

After the spec is accepted, `spec.md` is the design authority for
those conversations. This charter is the assignment for the spec
writer. Later conversations do not read it.
