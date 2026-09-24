# Charter — recall earlier submissions

**Status.** Handoff from the high-level discussion into a **design
conversation**. Not a checkpoint. Not an implementer assignment.
This file lives in `docs/design/implementation/recall/`. The
specification will live beside it as [`spec.md`](spec.md).
Checkpoint files will live in `checkpoints/` beside it. Map:
[`README.md`](README.md). The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

**Your job.** Turn this charter into a specification for walking
back through this session's submitted Python forms and colon
commands with Up and Down, and loading the chosen submission into
the input row. The series identity is **recall**. Then **stop**.
Do not write checkpoints. Do not implement.

The specification refuses a history file, search, history
expansion, and any change to what a click already does. Those
refusals keep the series small enough to slice.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Read the submitted-input records, empty-editor yank, and
   insert-during-composition in the transcript specification and in
   `yank_input` and `_load_saved_input`. Read `CommandInput.on_key`
   and the keyboard table in [`docs/user-guide.md`](../../../user-guide.md).
   Name the listener-spec sentence that lists up-arrow command
   history as out of scope. Do not invent a second kind of saved
   input.
3. Record the locked decisions in §4. Resolve the open question in
   §5.
4. Write `spec.md` in this folder. A later checkpoint-manager
   conversation slices **recall 000**, then **recall 001**, under
   `checkpoints/` here, one checkpoint per conversation.
5. Stop. The human reviews the spec. Do not write those checkpoint
   files.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification.

Keep the spec to Up and Down inside one session. A history file, a
search binding, a `history` command, or a new click is a defect in
this document.

## 2. Predecessors

The listener through the tutorial is implemented. Every completed
Python form and colon command is already a `PythonInput` or
`CommandInput` presentation. Yank into an empty editor reloads that
record, including chips. Yank during Python composition inserts the
saved pieces at the cursor. A menu action has `run again` and is a
different record.

The input row handles Left, Right, Home, End, Backspace, Delete,
and Enter. Up and Down are not recall keys today. The mouse wheel
scrolls the history surface. The documentation line and the bottom
rows have their own specifications.

Spacing between history operations is a separate series. This
exploration does not wait on it.

This exploration does not create a new project. Implementers keep
using uv in the existing project. Prefer no new dependency. The
designer does not run uv.

| Place | What goes there |
|---|---|
| `docs/design/implementation/recall/` | This charter, `spec.md`, and `checkpoints/` |
| Project root | The existing `pbui` package, `tests/`, and `docs/user-guide.md` |

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **Up walks backward through submissions.** After `:ls`, Enter,
   `1 + 2`, Enter, Up shows the Python form and Up again shows
   `:ls`. Down returns to `1 + 2`, then to the unsent editor.
2. **The objects come back.** A command submitted with a clicked
   file, and a Python form submitted with a chip, return as those
   same objects. A multi-line Python form returns as that saved
   form, shown the way the input row already shows a continuation.
3. **The unsent line is safe.** Type a partial line, move the caret
   into it, press Up, then Down. The partial line and the caret
   return. Edit a recalled submission and press Up: that edit is
   gone and the older submission is shown. Enter on an edited
   recall submits the edit as a new submission and leaves the older
   submission unchanged.
4. **Waiting and menus ignore the arrows.** Up and Down change
   nothing while a presentation accept, a substring accept, or a
   menu is open. A menu action and a left click that runs `show`
   add no recall entry.
5. **The screen around the input row stays put.** The history
   viewport does not jump to the old `›` row. The wheel still
   scrolls. Documentation sentences stay as they are. A submission
   remains recallable after its `›` row has scrolled out of the
   retained history.
6. **Old tests still pass**, plus headless recall tests, one screen
   test for Up and Down, two new rows in the user-guide keyboard
   table, and one hand check.

## 4. Locked decisions (record these; do not reopen)

### 4.1 What one entry is

An entry is the `PythonInput` or `CommandInput` value appended for a
submission, in the order those presentations are appended. The ring
stores those values. It does not store a flattened rendering, and it
does not reparse the `›` line.

Every such append adds one entry, including a syntax error, a failed
command, a repeated submission, and `:tutorial`. A path that appends
neither record adds nothing: empty Enter, an unfinished continuation
by itself, Try, a canceled accept, Next, Back, Contents, a menu
action, and a left click that shows a file, directory, or process.

A delayed accept adds its entry when its `CommandInput` is appended,
which is when the click completes the command. Until then the accept
is still waiting, and §4.4 keeps the arrows inert.

The ring outlives the 500-row screen history. Evicting a `›` row
leaves the entry in place. The ring is finite. §5 picks the bound.
Past that bound, the oldest entry drops. The screen limit stays 500
logical rows.

The ring belongs to this process. Quitting drops it. There is no
history file and no recall of a future session.

### 4.2 Up and Down

Up moves to the next older entry. Down moves toward the newer
entries. The walk is linear. The text already in the editor does not
filter it.

The position starts on the unsent editor, called the draft. The
first Up stashes that draft and shows the newest entry. Down from
the newest entry restores the stashed draft and clears the stash.
Up on the oldest entry leaves the editor on that entry. Down on the
draft leaves the draft. An empty ring leaves the editor unchanged.
Neither end rings a bell or rewrites the documentation line.

Showing an entry replaces the whole unsent editor with that
submission. It uses the same editor state as yank into an empty
editor, including chip identity and the cursor that yank leaves.
It does not submit, and it does not open an accept. A recalled
multi-line Python form uses the pending lines and the last line
that empty-editor yank already uses. The input row gains no
multi-line viewport.

Showing the draft puts back every part that was stashed: Python
pending lines, the current pieces, a command's text, its chip, and
the caret. A command caret that sat in the middle of the line
returns there. The listener owns that stash, so a headless test can
see the caret without Textual. The screen applies the caret the
listener returns.

An edit while an entry is showing changes only the editor. The ring
entry stays as stored. Up or Down from that edited editor discards
the edit and shows the destination. Enter submits whatever the
editor holds. On a submission that appends a `PythonInput` or
`CommandInput`, the ring gains that new value at the newest end and
the position returns to the draft left by today's submit. The entry
that was recalled stays as it was.

Recall and yank stay different operations. Yank during Python
composition still inserts at the cursor. Yank during command
composition still refuses. A yank, Try, or any other existing load
resets the position to the draft: the stash is dropped, and the
editor left by that load is the new draft.

Recalling an entry does not scroll the history surface.

### 4.3 After submit

The entry appended for a submission is the newest entry whether or
not the user had been walking the ring. The position after submit is
the draft. Enter's existing history reveal stays as it is.

### 4.4 When the arrows do nothing

Up and Down do nothing while any of these is true:

- a presentation accept is pending
- a substring accept is pending
- a menu is open

They do not cancel those states, and they do not change the editor,
the caret, the ring, or the position. Escape and `Ctrl-G` keep their
current meanings. The user can recall after the wait or the menu is
gone.

A Python continuation is ordinary unsent editor state. Up stashes
it under §4.2. It is not one of the inert cases.

### 4.5 What stays as it is

Click yank, chip insertion, `run again`, accept, menus, colon
dispatch, recording, and the 500-row screen limit stay as they are.
The wheel still scrolls the history surface. Up and Down are not
scroll keys, and this series adds no scroll key.

The documentation sentences stay on the bottom specification. The
input row keeps its mode word, directory, and drawing of chips.
History groups, blank rows, and indent stay on the history
specification.

`Ctrl-P`, `Ctrl-N`, and `Ctrl-R` stay without recall behavior. There
is no prefix search, no `!!`, no `!n`, and no `history` command.

The user guide's keyboard table gains one row for Up and one row for
Down, in the words the spec chooses, describing this walk. The rest
of the guide stays as it is. The smoke test gains no new step.

### 4.6 Tests

Headless tests build the ring without Textual. Cover at least: mixed
Python and colon-command order; a chip's object identity; a
multi-line form's pending lines; a mid-line command caret restored
with its draft; an edit discarded by a further Up; Enter on an edit
appending a new newest entry while the older entry remains; a
duplicate submission stored again; a menu action and a show-click
absent from the ring; inert Up and Down during accept, substring
accept, and an open menu; a ring entry still reachable after its
presentation is evicted; the oldest entry dropping at the bound; an
empty ring; Up on the oldest entry; Down on the draft.

Recall 000 proves that behavior. The screen may leave Up and Down
unbound there.

Recall 001 binds Up and Down on the input row, adds the two
user-guide rows, and includes one screen test and the hand check.
The screen test presses Up and Down and reads the input row. It also
shows that a wheel scroll still moves only the history surface.

The hand check uses a disposable directory. Run `uv run pbui`. Submit
`:ls`, then a short Python expression, then start a second line and
leave the caret in it. Up, Up, Down, Down. The continuation returns.
Submit `:rm` by clicking a file in that listing. Up recalls that
command and that file. Edit the recalled Python expression and press
Enter. The new value appears, and a later Up still finds the original
expression. Open a menu and press Up. The menu stays. `uv run pytest`
is the automated gate. `uv run pbui` is only the hand check.

### 4.7 Slice order

**recall 000** puts the ring, the draft, and previous/next on the
headless listener. Tests prove §4.1 through §4.4 and the bound from
§5. The terminal keys stay unbound.

**recall 001** binds Up and Down, updates the user-guide keyboard
table, and adds the screen test and the hand check.

Do not add a slice for search, a history file, or a documentation-line
rewrite.

## 5. Open question (resolve this in the spec)

### 5.1 How many submissions

Pick one integer bound for the ring. Keep it inside 200 through 500
inclusive. A session of a few hundred submissions must not drop an
entry the hand check can still see. State the integer, the drop-oldest
rule, and the headless test that fills the ring one past the bound.

The 500-row screen history stays 500. Do not tie the two numbers
together.

## 6. Authority

The transcript specification is the law for `PythonInput`,
`CommandInput`, `MenuActionInput`, yank, and `run again`. The chips
specification is the law for chip identity. The listener
specification remains the law for the three screen regions, the
wheel, and the command grammar. The bottom specification remains the
law for the input row and the documentation sentences. The history
specification remains the law for groups, blank rows, and indent.

The listener specification names up-arrow command history as out of
scope. This exploration supersedes that exclusion for Up and Down
only. The rest of that exclusion list stays out of scope.

Where this charter and an earlier specification disagree about Up
or Down, this exploration wins. Where they disagree about what a
click, a yank, or a stored input record does, the earlier
specification wins.

## 7. Handoff reminder

The series identity is **recall**. Checkpoint 000 is spoken
**recall 000** and filed as `checkpoints/000-slug.md`. Checkpoint
001 is spoken **recall 001**. Numbers are three digits, start at
000, and are never renumbered. The slug is lowercase words separated
by hyphens. The checkpoint manager writes one checkpoint, then
stops. Code and tests go at the project root
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`, not in
this folder.

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. The first identity is **recall 000**.
The second, in a later conversation, is **recall 001**.

After the spec is accepted, `spec.md` is the design authority for
those conversations. This charter is the assignment for the spec
writer. Later conversations do not read it.
