# Charter — chips in a Python expression

**Status.** Handoff from the high-level discussion into a **design
conversation**. Not a checkpoint. Not an implementer assignment.
This file lives in `docs/design/implementation/chips/`. The
specification will live beside it as [`spec.md`](spec.md).
Checkpoint files will live in `checkpoints/` beside it. Map:
[`README.md`](README.md). The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

**Your job.** Turn this charter into a specification that lets a
click insert a history object into the Python expression being
typed, and lets that expression run against the object rather than
against its printed text. Then **stop**. Do not write checkpoints.
Do not implement.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Read the REPL specification at
   [`../repl/spec.md`](../repl/spec.md). Python dispatch, the
   evaluator, `Value`, and continuation are already implemented.
   Also use the listener and listings specifications for command
   chips, accept, and menus. Do not copy them. Restate every rule
   an implementer must obey, and name the REPL sentences this spec
   supersedes. The superseded part is: a click never inserts a
   Python value into source, and Python source is only text.
3. Record the locked decisions in §4. Resolve the open questions in
   §5.
4. Write `spec.md` in this folder. A later checkpoint-manager
   conversation slices **chips 000**, `001`, … under
   `checkpoints/` here, one checkpoint per conversation.
5. Stop. The human reviews the spec. Do not write those checkpoint
   files.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification.

Keep the spec **small enough to slice**. SymPy, pandas, and a
second kind of Python syntax are defects in this document.

## 2. Predecessors

Listener is implemented through listener 005. Listings is
implemented through listings 008. The REPL is implemented through
repl 001. Unprefixed input is Python. A leading colon is a listener
command. `_` names the last displayed value. Command accept still
uses one `Chip` in `SubstrateState` for a file, directory, or
process. That command chip is not this exploration's input model.

This exploration does not create a new project. Implementers keep
using uv in the existing project. Prefer no new dependency. The
designer does not run uv.

| Place | What goes there |
|---|---|
| `docs/design/implementation/chips/` | This charter, `spec.md`, and `checkpoints/` |
| Project root | The existing `pbui` package and `tests/` |

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **The object is what runs.** An expression can contain a chip
   whose stored object has no usable `repr`. Evaluating `f(CHIP)`
   calls `f` on that object. It does not parse the chip's label.
2. **An empty prompt still shows.** With no continuation and an
   empty Python line, a left click runs `show`, as it does today.
3. **A command line is not a Python chip line.** While the line
   being typed is a colon command, or a command accept is pending,
   clicks keep today's command behavior. `:rm` still accepts a
   file.
4. **Chip names do not leak.** After the expression finishes,
   successful or not, the namespace has no synthetic chip name
   unless the user's own source spelled that name. `_` still
   updates exactly as the REPL specification says.
5. **Old tests still pass**, plus headless cases for splicing and
   one hand check. No SymPy and no pandas.

## 4. Locked decisions (record these; do not reopen)

### 4.1 When a click inserts

Left click keeps its current meaning except in the Python-composition
cases below. Menu clicks, command accept, and substring accept stay
modal and win over insertion.

Insert on left click only when all of these hold:

- no action menu is open;
- no command accept and no substring accept is pending;
- a Python continuation is open, or the editable line is Python
  rather than a colon command.

The editable line is a colon command when, after stripping leading
whitespace and ignoring Python chips, its first character is `:`.
An empty or all-whitespace line with no continuation is not Python
composition: a left click there still runs `show`. A line that
already contains a Python chip is Python composition even if the
text is otherwise empty.

Ctrl-O and mouse button 3 still open the object's existing menu
during Python composition. Insertion is left click only. The user
can show, remove, or list from the menu without inserting.

### 4.2 The Python input

Python source, including a continuation, is a sequence of pieces.
A piece is either a text run or a Python chip. This is separate
from `SubstrateState.chip`, which remains the single command-argument
chip. Do not store Python chips in that field.

A Python chip stores the presentation's value as it is at the
moment of the click, plus a display label. Later changes to the
history do not retarget it. Dropping the presentation from history
does not drop the chip. The chip is one atom: the cursor may sit
before it or after it, never inside its label. Backspace immediately
after a chip deletes the chip. Delete immediately before a chip
deletes the chip. Either key inside a text run deletes one character,
as today.

The label is the same one-line text the history uses for that
object, then cut to a width the spec chooses. The spec chooses the
visible brackets. The label is not source text.

The cursor is where the next click inserts. Typing goes into the
text run at the cursor, splitting a run when a chip is inserted in
the middle of it. A command line being typed does not gain this
structure. Its one command chip stays on the existing path.

When a continuation line is submitted, its pieces join the pending
source. Cancelling a continuation discards those pieces and does
not change the namespace. The editable line for the next continuation
step starts empty.

### 4.3 Splicing

Before `code.compile_command`, walk the pending pieces in order and
build one source string. Each text run is copied. Each chip becomes
one identifier `_pbui_chip_N`. Number from zero in order of
appearance. If that identifier already occurs in a text run, skip
to the next free integer. The same chip object inserted twice is
two occurrences and may share one number only when it is the same
stored object; the spec may instead use a fresh number every time.
Either choice is acceptable if `f(CHIP, CHIP)` passes the object
twice and the names are bound only for that execution.

Execute with those names bound to the stored objects. Do not bind
them by running the chip label through `eval`. After `exec` returns
or raises, remove every name this splice added. Leave keys the
user's source bound. If the user's source itself assigned to a
spliced name, remove that name too: the prefix is reserved. Do not
remove a name the user had already bound before the splice.

`compile_command`, the display hook, stdout, stderr, tracebacks,
and `_` stay as in the REPL specification. Completeness is judged
on the spliced source. The continuation prompt stays `...> `. The
pending pieces are not drawn into that one-row editor; only the
line being typed is.

### 4.4 What the screen says

During Python composition, the documentation line on a presentation
is exactly:

```text
Click to insert this value into the expression.
```

Hover stays the ordinary hover treatment. Do not reuse the
accept-target treatment. Accept-target remains the mark of a real
command accept.

The hand check starts in a disposable directory. It includes: an
empty-prompt click still shows; typing an expression and clicking a
previous number uses that number; an object whose `repr` is not
valid Python still arrives intact; `:ls` still lists; Backspace
removes a whole chip. `uv run pytest` is the automated gate.
`uv run pbui` is only the hand check.

### 4.5 Slice order

1. **Pieces and splicing.** Headless model of Python pieces,
   insertion, deletion, splice, reserved names, and execution.
   No Textual.
2. **Screen.** Cursor, chip drawing, documentation line, click
   insertion, and the hand check.

Do not add a layer for a feature in §4.6.

### 4.6 Out of this spec

- SymPy, pandas, and any new printer or menu for a library type.
- Dragging a chip, editing its label, or a chip inside a colon
  command beyond the one command chip that already exists.
- Changing colon dispatch, `_`, or the generic `Value` row.
- Completing Python names.
- A second thread for evaluation.

## 5. Open questions (resolve these in the spec)

### 5.1 Chip appearance

Choose the brackets and the maximum label width. A chip whose
history text is one short token must show that token in full.

### 5.2 Shared numbers

Choose whether two insertions of the same stored object share one
`_pbui_chip_N` or each gets a fresh number. State it with one test
that uses the object twice.

### 5.3 Cursor and the command line

State how the editor decides the line is a colon command when the
user types `:` after a Python chip is already present. The locked
rule is that a line containing a Python chip stays Python. Spell
the transition the other way: a colon command line has no Python
chips, and inserting one does not happen on that line.

## 6. Authority

This charter is the design for this exploration. The listener,
listings, and REPL specifications remain the law for everything it
does not change.

The Genera listener could accept a previous result into the next
form as the object. This exploration takes that for Python. Printers
and menus for particular libraries are the following exploration,
not this one.

## 7. Handoff reminder

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. Identity is **chips 000**, then
**chips 001**, and so on.
