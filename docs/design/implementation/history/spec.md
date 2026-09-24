# Specification — space between history operations

**Status:** Accepted. This file is the complete design input
for the checkpoint manager and the implementers. It assigns no
implementation work by itself.

History stays one list of stored rows. Each user operation that appends
rows marks those rows as one group. The screen draws one blank physical
row before every group except the first, and it draws result rows two
display columns to the right of transcript input. The objects, the
clicks, and the stored text stay as they are.

## 1. Checkpoint series

The series identity is **history**. Checkpoint 000 is spoken **history
000** and filed as
`docs/design/implementation/history/checkpoints/000-groups.md`.
Checkpoint 001 is spoken **history 001** and filed as
`docs/design/implementation/history/checkpoints/001-gap-and-indent.md`.
Numbers are three digits, start at 000, and are never renumbered. Slugs
are lowercase words separated by hyphens. The checkpoint manager writes
one checkpoint, then stops. Each implementer completes only the
checkpoint it receives, then stops. After this specification is
accepted, it is the design authority for those conversations.

The layer order is **groups**, then **gap and indent**.

- **history 000** records group membership on the stored rows and proves
  it with headless tests. Laid-out text stays flush left.
- **history 001** draws the blank row and the indent, moves hit testing
  with the ink, and includes the screen test and the hand check.

A checkpoint manager may split a layer that would not fit in one
implementer conversation. A split keeps this order and adds no feature.
There is no slice for a listing banner, a new marker, or the bottom
rows.

## 2. Product boundary

This specification extends the accepted listener, listings, REPL, chips,
SymPy, transcript, popup, HTTP, tutorial, and bottom specifications. It
changes the horizontal position of non-input rows and inserts a blank
physical row between operations. Those earlier specifications remain the
law for clicks, recording, printers, the `› ` marker, listing redisplay,
HTTP, tutorial cards, and the bottom rows.

Where this specification and an earlier one disagree about horizontal
position or a blank row between operations, this specification wins.
Where they disagree about what a click does or what stored text a row
contains, the earlier specification wins. Listener 005 remains the law
for per-row drawing and hover, including one Rich `Text` per physical
row and a hover that restyles only the presentations being left and
entered.

The program keeps one history. Group membership is data on the stored
rows already retained by `PresentationHistory`. This effort does not add
a second history, a box, a rule, a glyph, a color, a command, a listing
banner, or sort and filter words on a listing header. The listing header
stays `name`, `size`, and `modified`, or `pid`, `state`, `user`, and
`command`. Type prefixes such as `int` and `Error:` stay the result
markers. `stderr: ` stays. `:tutorial`, Try, Next, Back, and Contents do
what they do today. The popup stays an overlay beside the pointer.

The input row and the documentation line stay on the bottom
specification, including bottom 003 if that checkpoint has landed.
This series does not edit those sentences and does not edit the
process-command window: content columns 42 through 89 inclusive still
select the truncated-command wording. The `› ` transcript marker remains
the first two characters of each stored transcript-input row.

## 3. Host and layout

The project root is
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Code and
tests stay in the existing `src/pbui/` package and `tests/`. Design
files stay in `docs/design/implementation/history/`. The host is Linux.
Python is the existing project interpreter. `pyproject.toml`, `uv.lock`,
and the `pbui` console script already exist. Do not create another
project. Prefer no new dependency.

Only `pbui.terminal` imports Textual. Group membership and pure layout
stay headless.

All Python environment, program, and test commands use uv. From the
project root:

```console
uv sync
uv run pytest
```

`uv run pytest` is the automated gate for both checkpoints. History 001
also uses `uv run pbui` for the hand check in section 5.5. If uv is
unavailable, stop and report it. Do not use `pip`, `python -m pip`,
`uv pip install`, Poetry, Pipenv, Conda, Hatch, or a hand-made virtual
environment.

## 4. Groups

### 4.1 Membership on the stored row

`HistoryRow` gains `group_id: int | None`, default `None`, excluded from
equality, like `listing_owner`. `None` means the row is ungrouped.

`PresentationHistory` allocates group ids as integers starting at 1. An
id is never reused on that history. Survivors are not renumbered when a
row is dropped.

`PresentationHistory.operation()` is a context manager and the only way
product code opens a group.

- The outermost `operation()` on a history opens one group.
- A nested `operation()` joins the group already open and does not close
  it.
- The outermost `operation()` closes the group when it exits, including
  when the body raises.
- Calling the lower-level open while a group is already open raises.
  Closing when no group is open raises. Product code uses `operation()`
  rather than those lower-level calls.
- An `operation()` that appends nothing leaves no row behind. Its id is
  unused and invisible.

`append` keeps the caller's row object. While a group is open, `append`
writes that group's id onto the same object, replacing any id the caller
had set. While no group is open, `append` leaves `group_id` as the
caller set it. A direct `append` outside `operation()` therefore stores
an ungrouped row. That is the substrate tests' path, and it is not a
product operation.

`replace_row` writes the old row's `group_id` onto the new row. It still
requires the same presentations and the same listing owner. The caller's
old row object remains the lookup key.

`replace_listing_rows` writes one `group_id` onto every replacement row:
the id shared by the retained block it replaces. Every retained row of
that block has the same `group_id`; a disagreement raises `ValueError`.
The open group is not that id. Replacement still happens at the block's
current position, still keeps the listing owner, and still drops oldest
stored rows only when the result exceeds the retention limit.

Eviction still drops the oldest stored logical row and the presentations
owned only by it. The dropped row's group id disappears with it. A
surviving row keeps its id. Adjacent survivors with different ids are
not merged. The 500-row limit still counts stored logical rows only.

A stored row is transcript input when at least one of its presentations
has the type name `PythonInput`, `CommandInput`, or `MenuActionInput`.
`pbui.text` exposes one predicate for that test and one predicate,
`row_indents`, which is true exactly when the row has a group id and is
not transcript input. History 001's layout uses these predicates. It
does not keep a second copy of the rule.

### 4.2 Which call opens the group

One call to `append` is not a group. The call sites below acquire
`operation()` around the whole operation, before that operation's first
`append`, so the transcript-input row and every result row that same
operation appends share one id. Nested calls join that id.

| Entry | What shares the group |
|---|---|
| `HeadlessListener.submit` | Wrap the whole body, including the Python branch and the substring branch at the top. A finished Python form, including a syntax error: the `PythonInput` rows and the stdout rows, stderr rows, value row, and `Error` that submission appends. A printer failure while the value row is replaced, and an invalid-JSON `Error` appended from value presentation, stay in this group. A colon command, including an unknown command, a bad argument, `:get`, `:tutorial`, `:ls`, `:ps`, `:show`, `:cd`, `:rm`, `:kill`, and a finished substring accept: the `CommandInput` row and the listing, card, value, text, or `Error` that command appends. A successful `cd` may be the command row alone. |
| `HeadlessListener._finish_chip` | A delayed accept completed by a click. The command row is recorded here, then the command result joins it. When `submit` or a menu operation is already open, this joins that group instead of starting another. |
| `HeadlessListener.invoke_python_translator` | The `MenuActionInput` row and the rows the translator or HTTP action appends. HTTP perform includes the response row and an invalid-JSON `Error` if presenting that response appends one. |
| `HeadlessListener.execute_stored_member` | The member-command `MenuActionInput` row and the rows that command appends, including a new listing. |
| `HeadlessListener.run_again` | The new `MenuActionInput` row and the rows that saved action appends. |
| `HeadlessListener.apply_listing_view` | The menu-recorded action row, when this call records one, and an `Error` from the view change. The replaced listing rows keep the listing block's existing group and stay where they stand. |
| `HeadlessListener.open_tutorial_target` | The card rows for Next, Back, Up, or Contents. No `›` row is added. |
| `HeadlessListener.dig_json` | The labeled member rows and, when the collection is longer than 100 members, the literal trailer `… (N more members)`. An empty collection, or a click that is not a JSON object or array, appends nothing. |
| `PythonEvaluator.show_detail` | The detail lines, or the `Error` if drawing the detail fails. A refusal appends nothing. |
| `HeadlessListener._command_show` | The show detail or `Error` from a left click on a `File`, `Directory`, or `Process` with nothing waiting. No `›` row is added. Menu Show and `:show` join the menu or command group already open around this call. |

These helpers do not acquire a group. They append into whatever
`operation()` is already open, or they append an ungrouped row when
none is open: `_append_text`, `_append_error`, `append_input`,
`append_tutorial_card`, `display_value`, `append_labeled_value`,
`invoke_resolved_translator`, `_perform_http`, `_show_http_body`,
`_on_value_presented`, `_record_python`, `_record_command`,
`_record_action`, and `PythonEvaluator.submit_pieces`.

`submit_pieces` runs inside `submit`. An unfinished continuation, an
empty submission, Try (`load_tutorial_example`), a canceled accept, and
`begin_listing_narrow` append nothing, so no retained row receives a
new group. `begin_listing_narrow` records its action later, from
`submit`, when the substring is accepted.

Sort, narrow, only, and widen replace the listing block in place. The
command or menu-action row recorded for that change is a new group at
the end of history. An `Error` from the change joins that new group,
under the input row. The table is not moved to the end.

### 4.3 What history 000 proves

Headless tests in `tests/test_history.py` build groups without Textual.
They construct a listener with the existing filesystem and process
fakes. They prove at least:

- `1 + 2 + 3` stores the `PythonInput` row and the `int 6` value in one
  group. The value row indents. The input row does not. The stored value
  text is unchanged.
- `:tutorial`, then Next, stores card 1 in the command's group and card
  2 in a new group. Every card 2 row indents. None of them is transcript
  input. History's length is the number of stored content rows.
- `:ls` stores the command row and the listing rows in one group. The
  listing rows indent. The command row does not.
- `apply_listing_view` for a menu sort appends a `MenuActionInput` in a
  new group at the end and leaves the listing rows in their original
  group, at their original position. An invalid sort's `Error` joins the
  new group and the listing group does not change.
- Digging a JSON array of 101 elements stores the member rows and the
  trailer `… (1 more members)` in one new group, distinct from the value
  that was dug.
- `select_for_input` on a file after `:ls`, with the editor empty,
  appends its show detail in a new group. That row indents. The
  listing's group id does not change.
- A successful `:cd` can be a group of one command row. The next Python
  submission is a different group.
- An empty JSON object dig, an unfinished `if True:`, an empty submit,
  Try, and a canceled `:show` accept leave the stored rows unchanged.
- `print()` stores an empty text row in the Python group. That row is a
  stored row, not an extra separator.
- With `history_max_rows=3`, submitting `1 + 1` and then `2 + 2` drops
  the first input row. The surviving first value keeps its group id,
  indents, and does not share that id with the second submission.
- A hand-built `HistoryRow` passed to `append` outside `operation()`
  stays ungrouped.
- At a wide layout width, laid-out physical text still equals stored
  logical text, and every rendered row has a stored logical index.

History 000 does not change `layout` geometry, `pbui.terminal`,
`pbui.bottom`, drawers, or documentation sentences.

## 5. Gap and indent

### 5.1 The separator

`layout` walks stored rows in order and remembers the previous stored
row's group id. There is no remembered id before the first stored row,
and none across an ungrouped row.

Before a stored row that has a group id, when the remembered id exists
and differs, `layout` emits one separator first. The separator is a
physical row with text `""`, display width 0, `logical_row is None`,
and no presentation intervals. `hit_test` on it returns no presentation.
It is not stored, so it does not count toward retention. After eviction,
one separator stands between adjacent retained groups, and the new first
stored row has none before it.

No separator appears inside a group. A printed empty line stays the
stored text row it is. At layout width 3 or more, that indented row's
physical text is two spaces when its stored text is empty. The
separator's physical text stays empty. Below width 3 the stored row
lays out flush; a test distinguishes it from a separator by its logical
index and its presentation.

`RenderedRow.logical_row` becomes `int | None`. `None` is only the
separator and is never an index into `history.rows`. Every reader that
indexes history by `logical_row` treats `None` as not a stored row.

The separator is part of the same pure layout the screen hit-tests.
`HistorySurface` already builds one Rich `Text` per physical layout row.
The separator's text is empty, so its `Text` is empty. The gap is not
made by slicing one history-wide `Text`.

### 5.2 The two spaces

`row_indents` decides which stored rows indent. The prefix is drawn
only when that predicate is true and the layout width is at least 3.
Below width 3 the row lays out flush, as it does today.

The prefix is two ASCII spaces, two display columns, on every physical
row produced from that logical row. Columns 0 and 1 contain those
spaces and no presentation interval. Stored content starts at column 2
and uses the remaining columns of the same viewport width. Wrapping
still uses display width, including wide and combining characters. A
continuation line starts with the two spaces again.

A character that does not fit moves to a new physical row only when the
current physical row already contains a content cell. A fresh indented
row that cannot fit the next character places that character after the
prefix. This keeps a width-2 character from wrapping forever on a
3-column viewport, and it is the same overflow a too-wide character
already receives on an empty row.

Transcript-input rows stay at column 0, including every physical
continuation of those logical rows. The stored `› ` marker remains the
first two characters of those logical rows. Viewport wrapping does not
invent another marker.

The two spaces are not written into fragments. Yank text and
`logical_presentation_text` stay as they are. The 120-cell caps, the
12-row Python-form drawing limit, and the card wrap width still apply
to the content they already apply to. They are not reduced to 118, and
this series adds no truncation policy.

Every physical row of one card shares the card's left edge. Every
physical row of one listing shares the table's left edge. The body of a
card is not indented past the title. A member row is not indented past
the header. A listing explanation row takes the same prefix as the
header. A JSON trailer takes the same prefix as the member rows.

Ungrouped rows receive neither a prefix nor a separator.

### 5.3 Hits, hover, columns, and anchoring

Hit intervals move with the content ink. The innermost presentation
still wins. Columns 0 and 1 of an indented physical row, and every
column of a separator, hit no presentation.

Hover still restyles only the physical rows of the presentations being
left and entered. It does not style the separator, the two spaces, or
every retained row. The existing hover-rebuild test continues to prove
that a hover does not rebuild every row. A new assertion proves that a
hover on an indented presentation does not rebuild the separator's
physical row.

`pointer_logical_column` returns `None` on a separator and on either
indent cell. On content, it returns the column within the stored row,
counting only content cells of the earlier physical rows of that same
logical row. The two spaces are not content columns. The documentation
line's existing tests, including the process-command window at content
columns 42 through 89, therefore still name the same cells.
`_offset_for_logical_column` learns the inverse mapping. `pbui.bottom`
and its sentences stay untouched.

Listing viewport anchoring still keeps the same header or member in
view across a redisplay. The separator before that group is outside the
listing block. When the viewport's top physical row is a separator, the
anchor is the next stored row, at wrapped offset 0. Restoring that
anchor places the stored row at the top of the viewport. A separator is
never an index into the stored rows, and it is never the first physical
row of a listing block.

### 5.4 What history 001 changes in tests

History 001 switches these predecessor helpers from laid-out physical
text to stored logical text, so their assertions remain assertions
about content:

- `history_text` in `tests/test_commands.py`
- `drawings` in `tests/test_repl.py`
- `drawings` in `tests/test_sympy.py`
- `drawings` in `tests/test_chips.py`

A small stored-text reader may be added in `pbui.text` for that. Those
helpers are not the proof of the indent or the gap.

Picture and hit assertions that read `layout()` or `HistorySurface`
for grouped listener output are updated to the new geometry. Known
sites include `tests/test_tutorial.py` (`text_rows`, card hit
columns), the width-17 hit loop in `tests/test_http.py`, the direct
listing hit in `tests/test_commands.py` that currently expects column
0 on a file name, `test_directory_colors_and_whole_process_row_styling`
(the process row's physical length, the unstyled indent cells, and
hits starting at the content), and
`test_wrapped_command_field_refreshes_documentation_without_restyling`.
Terminal helpers `_top_logical_row` and `_offset_for_logical_column`
must tolerate a separator and must map content columns. Assertions
about stored fragment text, command effects, yank, and which object a
click delivers keep their meaning. Pictures of ungrouped rows,
including substrate layout and domain tables laid out without a group,
stay flush.

New headless layout tests in `tests/test_history.py` prove the picture
at width 80 or wider, and the narrow cases:

- The tutorial sequence in section 5.5, performed through
  `select_for_input` and `submit` with no Textual app: `›` at column
  0, card rows and `int 6` and the file table two columns in, one
  empty physical row between groups, and no empty physical row between
  a `›` row and the result of that same submission. The first group
  has no separator before it.
- A wrapped indented row at width 17: every physical row begins with
  two spaces, intervals start at column 2 or later, and columns 0 and
  1 miss.
- The same logical content at width 2 lays out flush.
- An ungrouped row gains neither a prefix nor a separator.
- After the eviction in section 4.3, the surviving value is the first
  physical row, its text begins with two spaces, and one separator
  stands before the next group.
- A stored empty `print()` line has physical text `"  "` at width 80.
  After another submission, the separator before that next group has
  physical text `""` and `logical_row is None`.

### 5.5 Screen test and hand check

One screen test, in `tests/test_terminal.py`, uses a wide terminal and
a disposable directory that contains one ordinary file. It drives
`:tutorial`, clicks Try for `1 + 2 + 3`, Enter, Next, clicks Try for
`:ls`, Enter, and Next. It reads the layout described above. A hit on
the indented file name's content cell is that file, and a click still
shows it. A hit on the indented Try control is that control, and a
click with an empty editor still loads its example. Hits on the two
indent cells and on the blank row between `int 6` and the next card
return no presentation.

The hand check starts in a disposable directory that contains one
ordinary file. From the project root:

```console
uv run pbui
```

Then `:tutorial`, Try `1 + 2 + 3`, Enter, Next, Try `:ls`, Enter, Next.
Read the gaps and the indent. Click a file name, Try, and the value.
The file detail and the value detail each appear as a new indented
group below a blank row. Try loads the example into the input row.
`uv run pbui` is only this hand check.

History 001 may edit `pbui.text` layout, the anchor and
`pointer_logical_column` paths in `pbui.terminal`, and the tests named
in this section. It does not edit documentation sentences, the
process-command window, or the stored drawers.

## 6. Verification

History 000 is complete when `uv run pytest` passes, the section 4.3
tests exist, and layout text of grouped rows is still flush.

History 001 is complete when `uv run pytest` passes, the section 5.4
and 5.5 tests exist, and the hand check in section 5.5 has been run.
The automated gate does not include the hand check.

Hover, yank, accept, menu dispatch, and listing redisplay remain
covered by their existing tests. Update a picture assertion that the
gap or the indent makes false. Do not change an assertion about which
object was retained or which command ran in order to make the suite
pass.

## 7. Acceptance

The specification is met only when all of these are true:

1. After `:tutorial`, Try `1 + 2 + 3`, Enter, Next, Try `:ls`, Enter,
   and Next, one blank row sits after `int 6` and before card 2, and
   one blank row sits after the file table and before card 3. The same
   rule separates every pair of retained groups. The `›` line stays in
   the group its submission produced, with no blank row between them.
2. `›` stays at column 0. The `:tutorial` card, `int 6`, the file
   table, and each later card sit two display columns in whenever the
   layout width is at least 3. Lines inside a card share one edge.
   Rows inside a table share one edge.
3. Try, Next, a file name, and a value still receive the clicks they
   receive today. The blank row and the two indent cells are not
   presentations.
4. No box, rule, or new glyph appears. The listing header keeps its
   column names. The input row and the documentation line keep their
   current wording, including the process-command window on the stored
   row's own columns.
5. The existing suite passes, together with the headless group tests,
   the layout tests, and the screen test. Hover still restyles only
   the presentations being left and entered.
