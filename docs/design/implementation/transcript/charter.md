# Charter — input in the transcript

**Status.** Handoff from the high-level discussion into a **design
conversation**. Not a checkpoint. Not an implementer assignment.
This file lives in `docs/design/implementation/transcript/`. The
specification will live beside it as [`spec.md`](spec.md).
Checkpoint files will live in `checkpoints/` beside it. Map:
[`README.md`](README.md). The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

**Your job.** Turn this charter into a specification that records
every submitted input in the history, as a presentation, before the
results of that input. A later click can bring a typed input back
into the editor. Then **stop**. Do not write checkpoints. Do not
implement.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Read the REPL, chips, and SymPy specifications only to preserve
   them. Do not copy them. Restate every rule an implementer must
   obey. This spec adds history rows. It does not change colon
   dispatch, splicing, or the SymPy operations.
3. Record the locked decisions in §4. Resolve the open questions in
   §5.
4. Write `spec.md` in this folder. A later checkpoint-manager
   conversation slices **transcript 000**, `001`, … under
   `checkpoints/` here, one checkpoint per conversation.
5. Stop. The human reviews the spec. Do not write those checkpoint
   files.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification.

Keep the spec **small enough to slice**. Pandas and in-place
editing of history rows are defects in this document.

## 2. Predecessors

Listener, listings, the REPL, chips, and SymPy are implemented.
Today a submitted line is cleared from the one-row editor, and the
history receives only the results. Python source is a sequence of
text runs and chips. A colon command may include one command chip.
Value translators such as `simplify` append a new value and no
record of the menu action.

This exploration does not create a new project. Implementers keep
using uv in the existing project. Prefer no new dependency. The
designer does not run uv.

| Place | What goes there |
|---|---|
| `docs/design/implementation/transcript/` | This charter, `spec.md`, and `checkpoints/` |
| Project root | The existing `pbui` package and `tests/` |

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **The form stays above the result.** Submitting `1 + 2 + 3`
   appends a presentation of that input, then a `Value` whose
   object is `6`. The history reads as a transcript.
2. **Bring-back does not run it.** With an empty editor and no
   continuation, a left click on that input presentation loads the
   same pieces into the editor. Enter is what runs them, and that
   run appends a new input presentation.
3. **Commands and menu actions are visible too.** `:ls` appears
   before the listing it produces. `simplify` on an expression
   appears before the simplified value. The original expression
   remains.
4. **A half-finished continuation is not yet history.** Rows are
   recorded when a form or command actually runs, or when it fails
   as a finished submission. An incomplete Python line only changes
   the continuation prompt.
5. **Old tests still pass**, plus headless order tests and one
   hand check.

## 4. Locked decisions (record these; do not reopen)

### 4.1 What is recorded

Three kinds of input presentation exist. Each is recorded
immediately before the first result of that action. Results keep
their current order after it: captured output, values, listings,
and errors.

| Kind | When | What it stores |
|---|---|---|
| Python form | A completed Python submission is compiled, whether execution then succeeds or raises | The pieces of the whole form, including every continuation line and every Python chip's stored object |
| Colon command | A colon line is accepted as a command attempt, including an unknown command | The command text after the colon, plus the command chip's object when the argument was a chip rather than text |
| Menu action | A value translator or an existing row menu command runs | The action label and the object that was under the pointer |

Do not record an empty submission, a bare colon, or a Python
submission that `compile_command` says is incomplete. Do record a
syntax error: the form, then the `Error`. Do record a command that
fails: the command, then the `Error`. Cancelling a continuation
records nothing.

A multi-line Python form is one presentation. Its drawing may
occupy several history rows. A click on any of those rows is a
click on that one form.

The 500-logical-row bound still applies. Input rows count.

### 4.2 How a click behaves

An input presentation is not a `Value`. A left click does not run
`show` on it and does not insert it as a value chip.

With an empty editor, no continuation, no accept, and no menu, a
left click on a Python form or a colon command loads that input
into the editor and does not run it. Python chips come back as
chips holding the same objects. A command chip comes back as the
command chip. The user edits and presses Enter to run it again.

While a Python expression is being composed, a left click on a
`Value`, file, directory, or process still inserts that object as
a Python chip, as chips does today. A left click on an input
presentation during composition inserts that input's pieces at the
cursor. It does not replace the line already being typed.

A left click on a menu-action presentation, when the editor is
empty and no continuation or accept is pending, runs that action
again on the same object and records a new menu-action row before
the new results. It does not invent a Python statement such as
`simplify(...)`. While composing Python, a left click on a
menu-action presentation inserts a chip of the action's target
object, not the action itself.

Command accept and substring accept still win over these clicks.
Ctrl-O and button 3 still open the existing menu of the object
under the pointer. An input presentation's own menu has one item,
`yank`, which performs the same load-into-the-editor action as the
empty-prompt left click. A menu-action presentation's menu has one
item, `run again`.

### 4.3 How an input is drawn

Each input row is visually distinct from a result. The spec chooses
a one-row marker, shared by every kind. A Python form uses the same
chip labels the editor uses. A tall form wraps onto more history
rows rather than escaping newlines into one row. A colon command
is drawn with its leading colon. A menu action is drawn as its
label and the target's one-line history text.

`show` is not the left click. The documentation line states the
left-click action exactly. The spec writes those sentences. Hover
stays ordinary hover, not accept-target styling.

### 4.4 Tests

Headless tests, with no Textual, must show:

- `1 + 2 + 3` records the form and then the value `6`, in that
  order;
- bringing that form back yields the same pieces and does not
  evaluate them;
- an incomplete continuation records nothing, and the completed
  form records once;
- a syntax error records the form and then one `Error`;
- `:ls` records the command before its listing rows;
- `simplify` on a SymPy expression records the action before the
  new expression, and the source expression is unchanged.

The hand check, from a disposable directory, is: enter `1 + 2 + 3`,
see the form above `6`, click the form, change it, and press Enter.
Then `:ls`, and see the command above the listing. Then a SymPy
`simplify`, and see the action above the result. `uv run pytest`
is the automated gate. `uv run pbui` is only the hand check.

### 4.5 Slice order

1. **Record and restore.** Headless presentations, order, yank,
   and run-again. No Textual.
2. **Screen.** Drawing, documentation lines, clicks, and the hand
   check.

Do not add a slice for a feature in §4.6.

### 4.6 Out of this spec

- Editing a history row in place.
- Pandas, new SymPy operations, or a change to pretty-printing.
- A second thread, or recording keys that do not submit.
- Replaying a menu action by synthesizing Python source.

## 5. Open questions (resolve these in the spec)

### 5.1 Marker and wording

Choose the marker that distinguishes an input row, and the exact
documentation sentences for a Python form, a colon command, and a
menu action. A one-token form such as `1 + 2 + 3` must be readable
in full on its row.

### 5.2 Tall forms

Choose how many history rows a recorded form may occupy before it
is cut, and how the cut is marked. `show` is not required for
inputs. If the drawing is cut, yank still restores the whole form.

### 5.3 Command arguments

State the drawing and the restored editor for three colon commands:
one with no argument, one whose argument was typed text, and one
whose argument was a command chip.

## 6. Authority

This charter is the design for this exploration. The listener,
listings, REPL, chips, and SymPy specifications remain the law for
everything it does not change.

The Genera listener kept the accepted form in the output history
as a presentation, and a click could bring that command back. This
exploration takes that. It does not take a full command processor.

## 7. Handoff reminder

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. Identity is **transcript 000**, then
**transcript 001**.
