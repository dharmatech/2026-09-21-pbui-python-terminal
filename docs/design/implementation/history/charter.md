# Charter — space between history operations

**Status.** Handoff from the high-level discussion into a **design
conversation**. Not a checkpoint. Not an implementer assignment.
This file lives in `docs/design/implementation/history/`. The
specification will live beside it as [`spec.md`](spec.md).
Checkpoint files will live in `checkpoints/` beside it. Map:
[`README.md`](README.md). The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.
The grouping rule below was tightened in that design conversation
so a view change cannot be read as moving the listing into the new
group, and so the append sites in the current listener are named
here.

**Your job.** Turn this charter into a specification that separates
history operations with a blank line and indents every row that is
not transcript input by two display columns. Then **stop**. Do not
write checkpoints. Do not implement.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Read the history append and replace paths, the transcript
   drawers, and `HistorySurface` layout and hit testing. Name the
   operations that already append or replace rows. Do not invent a
   second history.
3. Record the locked decisions in §4. There is no open-question
   section.
4. Write `spec.md` in this folder. A later checkpoint-manager
   conversation slices **history 000**, then **history 001**, under
   `checkpoints/` here, one checkpoint per conversation.
5. Stop. The human reviews the spec. Do not write those checkpoint
   files.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification.

Keep the spec to spacing and indent. A new glyph, a box, a listing
banner, a documentation-line edit, or a new click is a defect in
this document.

## 2. Predecessors

The listener through the tutorial is implemented. Transcript input
already stays in history, and each of those rows already begins with
`› ` (U+203A plus one space) at column 0. Cards, values, errors, and
listings are drawn from that same left edge, so a tutorial session
reads as one document.

Bottom checkpoints 000, 001, and 002 are implemented. Bottom 003 is a
separate wording checkpoint and is not this exploration.

This exploration does not create a new project. Implementers keep
using uv in the existing project. Prefer no new dependency. The
designer does not run uv.

| Place | What goes there |
|---|---|
| `docs/design/implementation/history/` | This charter, `spec.md`, and `checkpoints/` |
| Project root | The existing `pbui` package and `tests/` |

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **Operations separate.** After `:tutorial`, Try `1 + 2 + 3`,
   Enter, Next, Try `:ls`, Enter, and Next, a blank line sits after
   `int 6` and before card 2, and a blank line sits after the file
   table and before card 3. The `›` line stays on the same block as
   the rows that submission produced.
2. **Results sit one step in.** `›` stays at column 0. The card from
   `:tutorial`, `int 6`, the file table, and each later card sit two
   display columns in. Lines inside a card share one edge. Rows
   inside a table share one edge.
3. **The objects are the same objects.** Try, Next, a file name, and
   a value still receive the clicks they receive today. The blank
   line and the two indent cells are not presentations.
4. **The rest of the screen stays put.** No box, rule, or new glyph.
   The listing header keeps its column names. The input row and the
   documentation line keep their current wording.
5. **Old tests still pass**, plus headless group tests, a screen
   test for the gap and the indent, and one hand check. Hover still
   restyles only the presentations being left and entered.

## 4. Locked decisions (record these; do not reopen)

### 4.1 A group is one operation

A group is the contiguous run of stored rows one user operation
appends. One call to append is not, by itself, a group. The
transcript-input row and the result rows that same operation appends
are one group.

Replacing rows in place does not move them into the operation that
performs the replacement. `replace_row` keeps the replaced row's
group. `replace_listing_rows` keeps the group the listing block
already belongs to. Sort, narrow, only, and widen therefore leave
the table where it stands. The command or menu-action row recorded
for that view change is a new group at the end of history, and an
Error from that view change joins that new group, under that input
row. The view change does not pull the table down with it.

A direct `PresentationHistory.append` outside one of the operations
below leaves the row ungrouped. Ungrouped rows are how existing
substrate tests build history. They are not a product operation.
Layout neither indents them nor separates them.

These operations exist today. The spec names each one from these
call sites:

| Operation | What shares the group |
|---|---|
| Enter on a finished Python form, including a syntax error | The input presentation and the print rows, stderr rows, value, and Error that submission appends. A value-presentation failure, and an invalid-JSON Error appended while that value is presented, stay in this group. |
| Enter on a colon command, including a failed command and a delayed accept completed by a click | The command presentation and the listing, card, value, text, or Error that command appends. A successful `cd` may be the command row alone. |
| A menu action that records `MenuActionInput`, including run-again, member commands, translators, and HTTP actions | The action presentation and the rows that action appends. HTTP perform includes the response row and an invalid-JSON Error if presentation of that response appends one. |
| Next, Back, Up, or Contents | The card rows only. Do not invent a `›` row for the control. |
| Digging a JSON object or array | The member rows and, when it is appended, the literal trailer `… (N more members)`. An empty collection appends nothing. |
| Show-detail of a value | The detail lines, or the Error if drawing the detail fails. |
| A left click on a File, Directory, or Process with nothing waiting | The show detail or Error that click appends. Do not invent a `›` row. Menu Show is the menu-action operation above. |

An unfinished continuation, an empty submission, Try, a canceled
accept, and any other path that appends nothing start no group.

### 4.2 The blank line

Before every retained group except the first, the screen inserts one
blank physical row. No blank row appears inside a group. No blank row
appears before the first retained row.

The blank row is layout. It is not a stored history row, not a
presentation, and not a hit target. It has no stored logical-row
index. It does not count toward the 500-row retention limit.
Eviction still drops stored rows. After eviction, one blank row
separates adjacent retained groups, and the new first retained row
has none before it. Later groups therefore sit one physical row
lower on the screen. The separator belongs to the same pure layout
the screen hit-tests.

A printed empty line stays a stored row inside its group. It is not
the separator. At a layout width of 3 or more, that stored row is
indented, so its physical text is two spaces when its stored text is
empty. The separator's physical text is empty. Below that width the
stored row lays out flush, and a test tells the two rows apart by
the stored row's logical index and presentation.

### 4.3 The indent

A transcript input row stays at column 0. That is every logical row
of a `PythonInput`, `CommandInput`, or `MenuActionInput`, including
the existing `› ` marker. The marker remains the first two characters
of those rows.

Every other physical row in a group is prefixed with two ASCII
spaces, which are two display columns. A group with no transcript
input — a card opened from Next, a JSON dig, a value show-detail, or
a click that shows a file, directory, or process — indents every one
of its rows.

The prefix is the same on every row of a card and every row of a
listing, so the card's own lines stay aligned with each other and the
table's columns stay aligned with each other. Do not indent the body
of a card past the title. Do not indent a member row past the header.

The two spaces are layout. They are not written into stored
fragments, so yank text and the retained logical text stay as they
are. They are not content columns. The documentation line's existing
logical-column tests still name the same cells of the stored row.
Hovering either space yields no presentation and no content column.

On a layout width of 3 or more, every physical row produced from an
indented logical row begins with those two spaces, and that row's
stored content lays out in the remaining columns of the same viewport
width. One content column remains, so a continuation line can still
place a character after its own two spaces. A logical row that wraps
starts the two spaces again on each continuation line. On a layout
width below 3 there is no room for the prefix and a content column,
and the content lays out flush, as it does today.

Existing 120-cell caps, the 12-row Python-form drawing limit, and the
card wrap width apply to the content they already apply to. The two
spaces sit in front of that content. Do not shrink those caps to 118
and do not add a truncation policy.

### 4.4 Hits, hover, and anchoring

The two spaces and the blank row contain no presentation. Hit targets
move with their ink. The innermost presentation still wins. Hover
restyles only the physical rows of the presentations being left and
entered. It does not style the blank row, and it does not rebuild or
slice every retained row.

`HistorySurface` still builds one Rich Text per physical row directly.
A blank row is its own empty Text. Do not form the gap by slicing one
history-wide Text.

`pointer_logical_column` skips a separator and skips the two indent
cells. It reports a column inside the stored content, so the
process-command window used by the documentation line still names
the command's own cells.

Listing viewport anchoring still keeps the same header or member in
view across a redisplay. The blank row before that group is outside
the listing block. When the viewport's top physical row is a
separator, the anchor is the next stored row.

### 4.5 What does not change

Clicks, yank, chips, accept, menus, colon dispatch, and recording
stay as they are. The popup stays an overlay beside the pointer.
`:tutorial`, Try, Next, Back, and Contents do what they do today.

The listing header remains the column header it is now: `name`,
`size`, and `modified`, or `pid`, `state`, `user`, and `command`.
This exploration adds no snapshot banner and no sort or filter
words on that header.

Type prefixes such as `int` and `Error:` stay the result markers.
`stderr: ` stays. Do not add a second glyph system.

The input row and the documentation line stay on the bottom
specification, including bottom 003 if that checkpoint has landed.
This exploration does not edit those sentences.

No boxes, rules, new colors, or new commands.

### 4.6 Tests

Headless tests build groups without Textual. Cover at least: a Python
form and its value are one group; the next tutorial card is the next
group; `:ls` and its listing rows are one group; a menu sort appends
its action row as a new group and leaves the listing rows in the
original group; a JSON dig's members and trailer are one group; a
blank separator is not a stored presentation; eviction of an input
row leaves its result rows in that group and does not merge them into
a neighbor. History 000 proves that membership. Those result rows are
classified as indented there, and history 001 draws the two spaces.
History 000 leaves laid-out text flush, so existing picture
assertions stay as they are.

History 001 updates assertions that lock the old flush picture of
grouped listener output. Assertions about stored fragment text,
command effects, and clicks keep their meaning. Pictures of
ungrouped rows, including substrate layout and domain tables laid
out without a group, stay flush. Predecessor helpers that exist to
read result and listing content keep reading that stored content.

One screen test reads the tutorial sequence: `›` at column 0, `int 6`
and the table and the following card two columns in, a blank row
between those groups, and no blank row between `›` and its own
result. A click still hits the indented file name and the indented
Try control.

The hand check starts in a disposable directory that contains one
ordinary file, so the table has a name to click. Run `uv run pbui`,
then `:tutorial`, Try `1 + 2 + 3`, Enter, Next, Try `:ls`, Enter,
Next. Read the gaps and the indent. Click a file name, Try, and the
value.
`uv run pytest` is the automated gate. `uv run pbui` is only the hand
check.

### 4.7 Slice order

**history 000** records group membership on stored rows. Headless
tests prove §4.1 and the retention rule. The screen may stay
flush left.

**history 001** draws the blank row and the indent, and moves hit
testing and hover with the ink. It includes the screen test and the
hand check.

Do not add a slice for a listing banner, new markers, or the bottom
rows.

## 5. Authority

This charter is the design for spacing and indent. Earlier
specifications remain the law for clicks, recording, printers, the
`› ` marker, listing redisplay, HTTP, tutorial cards, and the bottom
rows.

Where this charter and an earlier specification disagree about
horizontal position or a blank row between operations, this
exploration wins. Where they disagree about what a click does or what
text a row contains, the earlier specification wins.

Listener 005 remains the law for per-row drawing and hover.

## 6. Handoff reminder

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. The first identity is **history 000**.
The second, in a later conversation, is **history 001**.
