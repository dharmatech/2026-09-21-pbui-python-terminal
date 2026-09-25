# Charter — pandas inspector

**Status.** Handoff from the high-level discussion into a **design
conversation**. Not a checkpoint. Not an implementer assignment.
This file lives in `docs/design/implementation/pandas/`. The
specification will live beside it as [`spec.md`](spec.md).
Checkpoint files will live in `checkpoints/` beside it. Map:
[`README.md`](README.md). The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

**Your job.** Turn this charter into a specification for presenting
a pandas `DataFrame` and `Series`, opening a bounded snapshot of a
frame, and taking a column or a row out of that snapshot by
position. The series identity is **pandas**. Then **stop**. Do not
write checkpoints. Do not implement.

The specification refuses sorting, filtering, grouping, JSON
conversion, plotting, and a click that turns one cell into a scalar.
Those refusals keep the series small enough to slice.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Read the SymPy specification for registering a library class and
   retaining its object. Read the HTTP specification for a click that
   appends a bounded view and leaves the source row in place. Read
   the chips specification for a left click during composition. Use
   pandas' own positional indexing. Do not route this table through
   the file and process listing commands.
3. Record the locked decisions in §4. Resolve the open question in
   §5.
4. Write `spec.md` in this folder. A later checkpoint-manager
   conversation slices **pandas 000**, then **pandas 001**, under
   `checkpoints/` here, one checkpoint per conversation.
5. Stop. The human reviews the spec. Do not write those checkpoint
   files.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification, including
the integers from §5.

Keep the spec to the inspector. A sort command, a `To DataFrame`
menu, or a plot is a defect in this document.

## 2. Predecessors

The listener through sections is implemented. A Python result stays
the object the call returned. SymPy registers a printer without
binding `sympy` in the listener namespace. JSON dig appends members
and does not replace the parent row. A left click during composition
inserts a chip instead of running a value's ordinary click. File and
process tables have their own sort and filter commands. This series
does not call those commands.

This exploration adds one dependency, `pandas`, with `uv add`, so
the version is pinned in `uv.lock`. Prefer no further dependency.
The designer does not run uv. Startup may import pandas in the
application. The listener namespace still starts as `__name__` only.
The user makes `pandas` available with `import pandas`.

| Place | What goes there |
|---|---|
| `docs/design/implementation/pandas/` | This charter, `spec.md`, and `checkpoints/` |
| Project root | The existing `pbui` package, `tests/`, `pyproject.toml`, and `uv.lock` |

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **The pandas object is the value.** Evaluating a `DataFrame` shows
   `DataFrame R×C` and retains that frame. Evaluating a `Series`
   shows a short summary and retains that series. A chip holds that
   same object.
2. **The preview is a snapshot.** An ordinary click on the frame
   appends a bounded table captured then. The source row remains.
   Clicking the source again captures the frame as it is at that
   later click.
3. **A column and a row come out by position.** A column header
   presents the `Series` at that column position in the snapshot. A
   row label presents the one-row `DataFrame` at that row position.
   Two columns with the same label stay distinct.
4. **The series can be read.** An ordinary click on a `Series`
   appends a bounded list of its values as text.
5. **The edges stay quiet.** A cell does not become an object. A
   MultiIndex axis has no header or row-label click. Composition
   still inserts a chip. No network and no listing command is
   involved.
6. **Old tests still pass.** `requires-python` stays `>=3.11`.

## 4. Locked decisions (record these; do not reopen)

### 4.1 Which objects

Register `pandas.DataFrame` and `pandas.Series` through the existing
class registry. Lookup walks the method resolution order and uses
the first registered class. Do not register `Index`, `ndarray`, or a
numpy scalar. A `dict`, a `list`, and a numpy array keep their
generic rows.

The summary row retains the evaluated object by identity. The
preview retains a copy of the frame made when the preview opens.
A column or row taken from that preview is a copy drawn from that
snapshot, so a later mutation of the source frame does not change
the preview or the extracted object.

### 4.2 Summaries

A `DataFrame` row is `DataFrame R×C`. `R` is the number of rows and
`C` is the number of columns at the time the row is presented.

A named `Series` row is `Series N NAME DTYPE`. An unnamed one is
`Series N DTYPE`. `N` is its length. `NAME` is its name. `DTYPE`
is the dtype's ordinary short text. The spec names that text for
the dtypes it tests.

No summary prefixes a Python class repr. The existing value path
escapes the line and caps it at 120 display cells. The summary does
not live-update. Evaluating the object again presents it again.

### 4.3 The preview

An ordinary left click on a `DataFrame` summary, with no accept
pending and no composition in progress, appends a preview and leaves
the summary in place. It does not change `_`. Clicking it again
appends another preview from the frame's current contents.

The preview shows a header row and then the captured data rows, in
positional order. Row labels and column labels are the labels from
the snapshot. §5 chooses how many data rows and columns are visible.
Omitted rows end the preview with the text `… (N more rows)`.
Omitted columns are reported with the text `… (N more columns)`.
`N` is the number omitted. A frame with no rows and no columns
previews as one text row, `empty DataFrame`. A frame with columns
and no rows shows the headers and one text row, `no rows`.

Cells are text. A missing value is `NA`. Numbers, booleans,
timestamps, and other values use a plain display the spec chooses
and tests. Each cell is capped at the width §5 chooses. A cell is
not a hit target and not a chip source.

When both axes have a single level, each visible column header is a
hit and each visible row label is a hit. A header click appends the
`Series` `snapshot.iloc[:, position].copy()`. A row-label click
appends the one-row `DataFrame` `snapshot.iloc[[position]].copy()`.
`position` is the integer position in the snapshot, not the label.
The new value follows the summary rules and becomes `_`. The preview
stays. Duplicate labels do not change which position is taken.

When the index or the columns have more than one level, the preview
still shows the labels as text and has no header or row-label hits.

One preview is small enough that it does not, by itself, evict a
source summary that is among the newest 400 history rows. The
500-row limit otherwise stays as it is.

### 4.4 The series list

An ordinary left click on a `Series` summary appends a bounded list
of its values as text, in order. §5 chooses the length. The trailer
is `… (N more values)`. An empty series appends one text row,
`no values`. The list does not change `_` or replace the series.
Those rows are not hit targets.

### 4.5 Clicks that do something else

During Python composition, a left click on a `DataFrame` summary, a
`Series` summary, a column header, or a row label inserts a chip of
that retained object and does not append a preview, a list, or an
extraction. The chip is the summary's original object, or the
snapshot's already copied column or row.

A cell, a trailer, and any other preview text have no action. They
do not insert a chip and do not append.

These objects are not file, directory, or process accept targets.
There is no pandas action menu and no new colon command. The spec
writes the ordinary documentation sentences: show the frame, list
the series, take the column, take the row, each with no right-button
menu. Composition uses the existing chip sentences.

### 4.6 What stays as it is

Sort, narrow, only, and widen stay on file and process listings.
JSON objects gain no `To DataFrame` action. A frame gains no plot
and no JSON export. Chips, yank, accept, recall, completion, and
tutorial cards stay as they are.

### 4.7 Tests

Headless tests build frames and series without Textual and without a
network. Cover at least: a fresh namespace has no `pandas`; a frame
summary retains that object and reads `DataFrame R×C`; a named and
an unnamed series read as §4.2; a preview copies the frame at open
and a later mutation of the source is absent from that preview;
clicking the source again captures the mutation; the visible window
and both trailers; `empty DataFrame` and `no rows`; a header click
returns the positional series, including the second of two columns
that share a label; a row click returns a one-row frame; a
MultiIndex axis has no extraction hits; a series list and its
trailer; `no values`; `NA` in a cell; preview and series list leave
`_` unchanged; an extraction sets `_` to the extracted object.

Pandas 000 proves that behavior. The screen may keep today's generic
drawing there.

Pandas 001 draws the preview and the series list, routes the hits,
writes the documentation sentences, and adds one screen test and the
hand check. The screen test clicks a frame, a column header, and a
row label, and checks that a cell has no action.

The hand check uses a disposable directory. Run `uv run pbui`. Import
pandas and evaluate a frame of a few rows and columns, including one
missing value and two columns with the same label. Read the summary.
Click it and read the preview. Click the second of the duplicate
headers and use that series as a chip in a later expression. Click a
row label and see a one-row frame. Click the series and read its
values. `uv run pytest` is the automated gate. `uv run pbui` is only
the hand check.

### 4.8 Slice order

**pandas 000** registers the two classes and proves summaries,
snapshots, extraction, and the series list without Textual.

**pandas 001** draws them, routes clicks, and adds the screen test
and the hand check.

Do not add a slice for sorting, JSON conversion, or plotting.

## 5. Open question (resolve this in the spec)

### 5.1 How much of the table is visible

Pick four integers and state the tests that use them:

| Quantity | Range |
|---|---|
| Visible data rows in a preview | 8 through 20 |
| Visible columns in a preview | 4 through 8 |
| Visible values in a series list | 8 through 20 |
| Display cells in one preview cell | 8 through 24 |

A frame larger than the window must show both trailers. A series
longer than its window must show its trailer.

## 6. Authority

The SymPy specification is the law for registering a library class
and retaining its identity. The HTTP specification is the law for a
bounded click that appends rows and leaves the source. The chips
specification is the law for composition clicks. The listings
specification remains the law for file and process tables.

Where this charter and an earlier specification disagree about the
row or the ordinary click of a `DataFrame` or a `Series`, this
exploration wins. Where they disagree about a generic value, a chip,
or a listing command, the earlier specification wins.

## 7. Handoff reminder

The series identity is **pandas**. Checkpoint 000 is spoken
**pandas 000** and filed as `checkpoints/000-slug.md`. Checkpoint
001 is spoken **pandas 001**. Numbers are three digits, start at
000, and are never renumbered. The slug is lowercase words separated
by hyphens. The checkpoint manager writes one checkpoint, then
stops. Code and tests go at the project root
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`, not in
this folder.

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. The first identity is **pandas 000**.
The second, in a later conversation, is **pandas 001**.

After the spec is accepted, `spec.md` is the design authority for
those conversations. This charter is the assignment for the spec
writer. Later conversations do not read it.
