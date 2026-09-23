# Charter — Python in the listener

**Status.** Handoff from the high-level discussion into a **design
conversation**. Not a checkpoint. Not an implementer assignment.
This file lives in `docs/design/implementation/repl/`. The
specification will live beside it as [`spec.md`](spec.md).
Checkpoint files will live in `checkpoints/` beside it. Map:
[`README.md`](README.md). The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

**Your job.** Turn this charter into a specification that lets the
existing listener evaluate Python and present the resulting object.
Then **stop**. Do not write checkpoints. Do not implement.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Read the listener specification at
   [`../listener/spec.md`](../listener/spec.md) and the listings
   specification at [`../listings/spec.md`](../listings/spec.md) so
   you know the command grammar, accept, chips, menus, and history
   drawing that already exist. Do not copy them into the new spec.
   Do restate every rule an implementer must obey, and name the
   sentences this spec supersedes. The superseded part is prompt
   dispatch. Unprefixed input is Python. A listener command is
   typed with a leading colon, and the command grammar after that
   colon is unchanged. Menu actions are not typed lines and do not
   gain a colon.
3. Record the locked decisions in §4. Resolve the open questions in
   §5.
4. Write `spec.md` in this folder. A later checkpoint-manager
   conversation slices **repl 000**, `001`, … under `checkpoints/`
   here, one checkpoint per conversation.
5. Stop. The human reviews the spec. Do not write those checkpoint
   files.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification.

Keep the spec **small enough to slice**. Chips inside Python
source, SymPy, and pandas are defects in this document.

## 2. Predecessors

Listener is implemented through listener 005. Listings is
implemented through listings 008. The command names are exactly
`ls`, `ps`, `show`, `kill`, `cd`, `rm`, `sort`, `narrow`, `only`,
and `widen`.

This exploration does not create a new Python project. Implementers
keep using uv in the existing project. Prefer no new dependency.
`code.compile_command` is in the standard library. The designer
does not run uv.

| Place | What goes there |
|---|---|
| `docs/design/implementation/repl/` | This charter, `spec.md`, and `checkpoints/` |
| Project root | The existing `pbui` package and `tests/` |

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **Unprefixed input is Python.** `1 + 1` presents `1`.
   `import math` binds `math` and adds no value row. The next line
   `math.sqrt(4)` presents `2.0`. A bare `ls` looks up that name.
   If it is unbound, the result is an error, not a directory
   listing. The object in the history is the value, not the
   characters of its `repr`.
2. **A leading colon is a command.** `:ls`, `: ls /tmp`, and
   `:sort name` run the existing commands, including chips and
   accept. The colon is not part of the command name. A menu item
   that runs `ls` or `rm` does not require a colon.
3. **Failures stay in the listener.** A syntax error, an exception,
   and a failed command append an `Error` presentation. They do not
   close the program. A long Python call blocks the listener, just
   as a long command does. This spec does not add a second thread
   for it.
4. **Old tests still pass**, plus the new headless cases and one
   hand check. Automated tests must not depend on SymPy, pandas, or
   the network.

## 4. Locked decisions (record these; do not reopen)

### 4.1 Dispatch

This applies to a line submitted at the primary prompt, when no
Python continuation is open and the existing accept state is idle.

- An empty or all-whitespace line does nothing.
- Strip leading whitespace. If the first character is then `:`,
  the line is a command. Remove that colon and at most one space
  immediately after it. If nothing remains, do nothing. Otherwise
  the remainder is the existing command grammar, chips included,
  and it is not compiled as Python. `:ls()` is an unknown command,
  not a call.
- Every other line is Python. `ls`, `ls()`, and `sort(name)` are
  Python. A `NameError`, including one for a name that is also a
  command, does not run that command. When the failed source is a
  single name and that name is a command, the `Error` text mentions
  the colon form. The spec writes that sentence. It must not be
  ambiguous about whether the command ran.

A line submitted while a continuation is open is always more Python
source, even if it starts with `:`. It is not reconsidered as a
command. Append it to the pending source with a newline before it.

### 4.2 Compilation and the namespace

Use `code.compile_command` with `symbol="single"` on the accumulated
source. Do not write a Python parser.

- `None` means the source is incomplete. Keep it, clear the input
  line, and change the prompt to the continuation prompt. Do not
  run anything.
- A `SyntaxError`, `OverflowError`, or `ValueError` from
  `compile_command` appends one `Error` and clears the pending
  source.
- A code object is executed with `exec` in one listener-owned
  namespace. That namespace starts as `{"__name__": "__pbui__"}`.
  It is not the module globals of `pbui`, and the command names are
  not placed in it. It lives for the process. Names bound by the
  user stay bound.
- Execution installs a display hook for that `exec` only. When the
  hook receives a value other than `None`, set `_` in the namespace
  to that value and append a presentation of the value. When the
  hook receives `None`, or when a statement never calls the hook,
  append no value row and leave `_` as it was.
- An exception during `exec` appends one `Error` containing a
  traceback and clears the pending source. It does not change `_`
  unless the display hook already ran. It does not leak the
  display hook past the execution.

Ctrl-G clears a pending continuation and the input line, and
otherwise keeps its current meaning. Escape clears a continuation
first when one is open, and otherwise keeps its current meaning.

### 4.3 The generic presentation

Every displayed Python value uses one presentation type, `Value`,
unless a registered printer applies (§4.4). The presentation stores
the object.

The history row is one logical row: the type's `__name__`, then a
truncated `repr`. The spec chooses the width. Truncation keeps the
row on one line. `show` presents a longer `repr`, also capped, with
the cap written in the spec. Neither printer may scan an unbounded
structure without a cap. `repr` that raises becomes an `Error`, and
the `Value` presentation already in the history stays.

Left click runs `show`. A `Value` is not acceptable to `ls`, `ps`,
`show`'s existing domain accept, `cd`, `rm`, `kill`, or the listing
view commands. The menu for an unregistered `Value` has no items.
The documentation line says what the left click will do and that
there is no menu.

`_` in a later Python line is how the user names the last displayed
value. This spec does not insert that object into the input line as
a chip.

### 4.4 Registration hook

The listener has a registry from a class to a printer and a list of
menu translators. Lookup walks the instance's method-resolution
order and uses the first registered class. A printer returns the
row text. A translator has a label and a function from the object
to a new object. Running it appends a presentation of that new
object, or an `Error` if it raises. The original presentation stays.

This exploration registers nothing. Tests register a dummy class
defined in the test file and prove that its printer and one
translator are used instead of the generic row. SymPy and pandas
are not dependencies and have no special case in the program.

### 4.5 What this must not break

- Command chips, accept, listing redisplay, table drawing, and the
  listener 005 hover rule.
- The hand check still starts in a disposable directory before any
  `rm`. Add steps for `1 + 1`, a name binding, an exception, a bare
  `ls` that does not list the directory, and `:ls` listing it.
- `uv run pytest` is the automated gate. `uv run pbui` is the human
  check.

### 4.6 Slice order

1. **Evaluator.** Dispatch, `compile_command`, namespace, display
   hook, `Value`, errors, `_`, and the registry. Headless tests.
   No Textual.
2. **Screen.** Continuation prompt, the `Value` row, `show`,
   documentation lines, and the hand check.

Do not add a layer for a feature in §4.7.

### 4.7 Out of this spec

- A chip, or any click, that inserts a Python value into a Python
  expression. `_` is the only way back to the last value.
- SymPy, pandas, and any pretty-printer for a third-party type.
- A second process or thread for evaluation.
- Changing command grammar, listing columns, or the menu items that
  already exist for files, directories, processes, and listings.
- IPython-style `_1`, `Out`, magics, or a `%` escape.
- Completing Python names while typing.

## 5. Open questions (resolve these in the spec)

### 5.1 Prompts and errors

Choose the continuation prompt. It must be visibly different from
the cwd prompt. Choose the `Error` text for a syntax error and for
an exception, including how much of the traceback is kept. One
`Error` presentation per failure.

### 5.2 Widths

Choose the history-row `repr` width and the `show` cap. A value
whose `repr` is one short token must appear in full on the history
row.

### 5.3 Display hook and `_`

State the order when the hook runs more than once during a single
`exec`. Each non-`None` value is presented, and `_` is the last of
them. State that a failed `repr` still leaves the object in its
`Value` presentation.

## 6. Authority

This charter is the design for this exploration. The listener and
listings specifications remain the law for everything it does not
change.

The Genera listener accepted a Lisp form and presented the value.
This exploration takes that, for Python, only as far as evaluation
and a generic presentation. The later explorations, not this one,
are an expression that can contain the presented object, and then
printers and menus for particular libraries.

## 7. Handoff reminder

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. Identity is **repl 000**, then
**repl 001**, and so on.
