# Charter — the bottom two rows

**Status.** Handoff from the high-level discussion into a **design
conversation**. Not a checkpoint. Not an implementer assignment.
This file lives in `docs/design/implementation/bottom/`. The
specification will live beside it as [`spec.md`](spec.md).
Checkpoint files will live in `checkpoints/` beside it. Map:
[`README.md`](README.md). The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

**Your job.** Turn this charter into a specification that makes the
input row show the listener mode and makes the documentation line
lead with the target and the two buttons. Then **stop**. Do not
write checkpoints. Do not implement.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Read `format_documentation` and the input prompt in
   `src/pbui/terminal.py`, and the popup specification's
   documentation section. Every current documentation sentence has
   an action. The new sentences must keep that action and change
   the shape. Do not copy the old sentences. Name the popup section
   this spec supersedes.
3. Record the locked decisions in §4. Resolve the open questions in
   §5.
4. Write `spec.md` in this folder. A later checkpoint-manager
   conversation slices **bottom 000** under `checkpoints/` here,
   then stops.
5. Stop. The human reviews the spec. Do not write that checkpoint
   file.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification. A missing
documentation case is a defect.

Keep the spec to this one screen change. History markers, new
colors, and new click behavior are defects in this document.

## 2. Predecessors

The listener through the popup exploration is implemented. The input
row shows the absolute working directory. The documentation line is
one row above it and already names `Left` and `Right` inside longer
sentences. Green underlining means an object is an acceptable target.
Directories and process states already have their own colors.

HTTP and the tutorial are separate explorations. This one does not
wait on them. Implementers keep using uv in the existing project.
Prefer no new dependency. The designer does not run uv.

| Place | What goes there |
|---|---|
| `docs/design/implementation/bottom/` | This charter, `spec.md`, and `checkpoints/` |
| Project root | The existing `pbui` package and `tests/` |

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **The mode is visible before the sentence.** An empty prompt
   shows that input is Python. After `:rm` is waiting for a file,
   the input row shows that a file is being selected. A continuation
   shows that more Python is expected.
2. **The documentation line leads with the target.** On a file, the
   line identifies the file, then the left action, then the right
   action. A pending `:rm` uses that same line to say a file is
   being selected and that Escape cancels.
3. **The clicks do not change.** Show, insert, yank, accept, menu,
   and tutorial controls do what they do today. Green still means
   only "this object can be selected."
4. **Every current documentation case has a new sentence.** The
   spec lists them. A case left as an old sentence is a defect.
5. **Old tests still pass**, plus tests for the mode label and the
   new sentence shape, and one hand check.

## 4. Locked decisions (record these; do not reopen)

### 4.1 The input row

The input row keeps the absolute working directory and gains a mode
word. A visual boundary separates this row from the documentation
line above it. The spec chooses the rule, the weight, and the order
of the mode word and the directory. Both must be visible on a wide
terminal. On a narrow terminal the mode word wins. The directory may
truncate. The mode word may not.

The mode word is exactly one of:

| State | Word |
|---|---|
| Python, including an empty prompt | `PYTHON` |
| A colon command being typed | `COMMAND` |
| A Python continuation | `CONTINUE` |
| Presentation accept or substring accept | `SELECT` plus the type, and the command when there is one |
| A menu is open | The mode of the editor underneath, not a separate menu mode |

`SELECT FILE FOR rm` is the shape of a pending `:rm`. `SELECT TEXT
FOR narrow` is the shape of a pending substring. The spec writes
each accept the listener already has, including tutorial refusal
only if that state is an editor mode. Tutorial refusal is not a new
mode. It stays a documentation sentence.

The continuation prompt may still show `...>`. The word `CONTINUE`
has to be visible as well.

### 4.2 The documentation line

The line stays one row. Its shape is a target, then the left
action, then the right action, separated so each part can be
scanned. The spec chooses the separator. An example of the shape,
not the final punctuation, is `FILE notes.txt  •  Left: show  •
Right: menu`.

The target is the object under the pointer: its kind and its short
name, pid, or other existing label. The left and right actions are
the actions the current sentences already describe, shortened to
the verb and the object when the target already names the object.
Do not add information. Do not drop a refusal, a cancel hint, or an
insertion refusal.

While a selection is pending, the line leads with that selection
instead of only the object under the pointer. The shape is
`SELECTING FILE FOR rm  •  Esc: cancel` when the pointer is not on
a target, and it still names the object when the pointer is on one.
Escape remains the cancel key already implemented. Ctrl-G remains
too. The sentence names Escape.

The middle button is not mentioned. Green is not used as a success
color. No new accent colors are introduced. Directory and process
colors stay as they are.

A menu item, the menu border, an empty history, and a continuation
with nothing under the pointer keep a sentence. The spec rewrites
each into the new shape. If there is no target, the line says so
in the target position rather than inventing a button action.

### 4.3 What does not change

History markers, listing headers, the `› ` input marker, card
layout, and popup placement stay as they are. This exploration does
not add a sidebar, a box around each result, a spinner, or a
session-status bar.

If a tutorial card quotes an old documentation sentence, update that
quote to the new sentence. Do not rewrite the tour otherwise.

### 4.4 Tests

Headless tests call the formatter. Cover at least: empty prompt is
`PYTHON`, a typed colon line is `COMMAND`, a continuation is
`CONTINUE`, pending `:rm` is a file selection, a file under the
pointer names the file and both buttons, and a non-target during
that selection says Escape cancels. No Textual in those tests.

One screen test may start the app and read the input row. The hand
check, from a disposable directory, is: read `PYTHON` on the empty
prompt, point at a file and read the target and both buttons, run
`:rm`, see the selection on the input row, press Escape, and see
`PYTHON` again. `uv run pytest` is the automated gate. `uv run pbui`
is only the hand check.

### 4.5 Slice order

One slice. The mode word and the documentation shape belong
together. Do not add a slice for history markers.

## 5. Open questions (resolve these in the spec)

### 5.1 Layout

Choose the boundary, the order of the mode word and the directory,
and the separator between documentation parts. The mode word is
fully visible whenever the row is at least as wide as that word.

### 5.2 The case list

List every documentation case the code can return today, and write
its new sentence beside it. Include accepts, menu items, menu
border, chips, transcript yank, tutorial controls, JSON, requests
if they already have sentences, and the empty pointer.

### 5.3 Truncation

Choose what truncates first when the documentation line does not
fit: the target name truncates, and `Left` and `Right` stay whole.

## 6. Authority

This charter is the design for this exploration. Earlier
specifications remain the law for every click. The popup
specification's documentation wording is what this exploration
replaces.

The bottom line is the mouse-documentation line. It names the
buttons. It does not become a status bar for the session.

## 7. Handoff reminder

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. Identity is **bottom 000**.
