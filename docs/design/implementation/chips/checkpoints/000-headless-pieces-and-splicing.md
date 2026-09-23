# chips 000 — Headless Python pieces and splicing

**Status.** Ready to implement.

## Goal

Give the headless listener an editable Python line made of text runs and atomic
object chips. Preserve those pieces across continuation, splice each chip to a
temporary namespace binding for compilation and execution, and keep ordinary
colon commands and command accept working as they do now.

Stop when the headless model and the complete automated suite pass. Drawing,
mouse coordinates, documentation, menus during continuation, terminal keys,
and the live hand check belong to a later checkpoint.

## Identity, authority, and starting point

- Identity is `(chips, 000)`, spoken **chips 000**.
- The human-reviewed [`../spec.md`](../spec.md), especially sections 1–4 and
  **Slice 1 — pieces and splicing** in section 6, is the authority. Follow it
  where this checkpoint is silent. The charter is not an implementation input.
- Listener 000–005, listings 000–008, and repl 000–001 are implemented. Retain
  their behavior except where the chips specification explicitly changes it.
- Work in the existing project at
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application
  code and tests stay at the project root, never under `docs/`.
- Python is 3.11 or newer. Keep the evaluator and piece model independent of
  Textual. Add no dependency.

## File boundary

May edit `src/pbui/repl.py` and `src/pbui/commands.py`, and may add one focused
plain-Python module under `src/pbui/` for the piece, cursor, insertion-site, and
splice model. `src/pbui/text.py` may gain only a pure helper needed to read the
logical text belonging to a retained presentation; its layout, hit testing,
and history behavior must stay unchanged. Add focused tests in a new
`tests/test_chips.py` and, where existing interfaces change, in
`tests/test_repl.py` or `tests/test_commands.py`.

Do not edit production `src/pbui/terminal.py`, `src/pbui/substrate.py`,
`src/pbui/domain.py`, the command effects, menu definitions, or any project
metadata or dependency file. Do not change the listener's ten command names,
their colon grammar, the single command-argument `SubstrateState.chip`, the
`Value` registration hook, `_`, history retention, or synchronous evaluation.
Only `pbui.terminal` may import Textual. This checkpoint adds no terminal
screen tests or live hand check.

## Headless input and routing

Represent the editable Python line and each retained continuation line as
ordered text runs and Python chips. A chip keeps the exact clicked stored
object by identity and a label captured once for display. It never enters
`SubstrateState.chip`. Preserve the existing text-buffer and command-chip path
for a chip-free colon command or pending command accept. Keep the established
plain-string submission interface working for callers that have no Python
chips; expose headless operations that the later screen checkpoint can use to
edit and submit a chip-bearing line without flattening it to display text.
Keep the existing `pending_python_source` continuation signal and chip-free
text behavior available to the current terminal adapter; the retained pieces
are authoritative for chip-bearing compilation and execution.

The headless cursor is a boundary between text characters or whole chips.
Support inserting text and a chip at that boundary; Left, Right, Home, End,
Backspace, and Delete; and splitting or merging text runs without changing the
piece order. Left and Right cross a chip in one step. Backspace immediately
after a chip and Delete immediately before it remove the whole chip. Editing
text removes one character as before. The cursor remains immediately after an
inserted chip. Do not put brackets or label characters into source text.

The headless insertion operation receives a currently retained presentation,
not a terminal coordinate. Capture its value by identity. Capture the logical
one-line history text associated with that exact presentation as currently
drawn, including the complete member row for a listing member, truncate it to
at most 32 display cells with the existing safe display helper and `…`, and
store that label. Later history redisplay or eviction must not change the
chip. A literal field or absent presentation cannot insert a chip.

Preserve modal and mode precedence from specification section 2. A pending
presentation accept or substring accept handles a selection before Python
insertion; its exact-type acceptance and command-chip behavior do not change.
With no continuation, a chip-bearing line is Python even if its text is empty
or begins with `:`. Without a chip, leading whitespace followed by `:` means
the existing command path; other non-whitespace text means Python composition;
an empty or whitespace-only ordinary prompt keeps its default `show` click.
During continuation every editable line is Python, including one starting
with `:`. A colon command line never gains a Python chip from selection.
Changing text or removing the last chip recomputes mode immediately. A failed
Python insertion must not fall through to default `show`.

## Insertion-site validation

Before inserting, check the pending lines and editable line together, treating
existing chips as identifier atoms. Accept only a boundary where the new chip
would splice as a standalone Python identifier in an expression-atom position.
Reject string and comment interiors, including unclosed or multiline strings,
and reject an entire f-string literal, including replacement fields. Reject a
boundary that would merge the inserted identifier with another token or place
it in a non-expression grammar position. `f(|)` and `x = |` are allowed;
`fo|o`, `12|3`, `obj.|`, `import |`, and `def |` are refused. An incomplete
expression such as `f(` still permits insertion after `(`. Use Python lexical
rules for the boundary check; do not call `code.compile_command` on a click.
Refusal leaves all pieces, cursor, pending lines, history, and namespace
unchanged. This is a headless result the later screen can use for its exact
documentation sentence.

## One splice and one compile per Enter

For each Python Enter, combine already-pending lines with the submitted line
exactly once, inserting one newline between lines. Walk that combined sequence
once to make source: copy text runs verbatim and replace each chip occurrence
with a fresh `_pbui_chip_N` identifier. Start numbering at zero in occurrence
order. Skip a candidate when its exact spelling is a whole Python identifier
anywhere in a text run, including a string or comment, or is already a key in
the listener namespace. A candidate contained only as a substring of a longer
identifier does not collide: `_pbui_chip_01` and `x_pbui_chip_0` do not block
`_pbui_chip_0`. Every chip occurrence gets a different synthetic name, even
when two chips store the same object. Map every chosen name to its occurrence's
original object, without using its label or `repr` as source. For collision
checking, adjacent text runs are one contiguous stretch of source even if the
piece model has not merged them.

Call `code.compile_command(spliced_source, symbol="single")` exactly once for
that Enter. When it returns `None`, retain the original combined pieces as
pending continuation, clear only the editable line, and introduce no
synthetic namespace bindings or history row. A later Enter makes a new
combined sequence and one new splice. A specified compile exception appends
the existing single `Error`, clears current and pending pieces, and introduces
no bindings.

After successful compilation, bind the chosen names directly to their mapped
objects in the evaluator namespace for this execution only. Run the existing
`exec` path, preserving its display hook, stdout/stderr capture, output order,
tracebacks, `Value` identity, and `_` behavior. In `finally`, remove every
synthetic name chosen for this splice, including one reassigned indirectly by
the evaluated code, after normal completion or an execution exception such as
`SystemExit`. A preexisting namespace key was skipped and remains untouched.
User-created bindings outside the selected synthetic names persist. Clear
pending and editable pieces after execution success or failure. Cancellation
discards pending and current pieces without execution or namespace changes.

## Focused tests

Use injected services and temporary roots; import no Textual module. Preserve
all predecessor tests. Add tests that prove:

1. Middle-of-run chip insertion splits text correctly; typing and cursor
   movement work on both sides; Home and End reach the boundaries; Backspace
   and Delete each remove a whole chip, while text editing removes one
   character. Captured labels stay bounded and unchanged after redisplay or
   eviction, and the stored object remains identical.
2. Empty-prompt selection keeps `show`; chip-free `:rm` still enters exact
   `File` accept; accept and substring accept win over insertion; a command
   line cannot gain a Python chip; `:` before an existing chip remains Python;
   removing the last chip lets text decide mode again. A refused insertion
   does not run `show` or change state.
3. `f(|)` accepts insertion while strings, comments, unclosed and multiline
   strings, f-strings, merged tokens, and non-expression positions refuse it.
   A refusal does not call `compile_command`.
4. Multiple chips across separate continuation lines preserve their original
   pieces. Each Enter compiles exactly once with that Enter's submitted line
   included once and exactly one newline between submitted lines.
5. An object whose `repr` is unusable Python reaches `f(CHIP)` by identity;
   `f(CHIP, CHIP)` receives that same object twice by identity while the two
   occurrences use distinct temporary names.
6. Whole-identifier collisions in ordinary source, strings, comments, and
   preexisting namespace keys are skipped. Longer identifiers such as
   `_pbui_chip_01` and `x_pbui_chip_0` do not spuriously block `_pbui_chip_0`.
7. Temporary names never leak after success, compile failure, execution
   failure, `SystemExit`, or indirect reassignment of a selected name.
   Preexisting keys, user bindings outside selected names, and the REPL's `_`
   rule remain intact. Earlier displayed values survive a later exception.

## uv workflow and completion boundary

From the project root, use only the existing uv-managed environment:

```console
uv sync
uv run pytest
```

`uv run pytest` is the complete automated gate. Do not use `pip`,
`python -m pip`, `uv pip install`, Poetry, Pipenv, Conda, Hatch, a hand-made
environment, or global Python. If uv is unavailable, stop and report it.

Chips 000 is complete when the headless piece, insertion-site, splice, and
execution paths above work; all focused tests and the full suite pass; and no
Textual code has entered the headless modules. Stop there. Terminal drawing,
click hit testing, editor integration, documentation and hover updates,
continuation menus, the `narrow` suspension flow, Ctrl-D routing, and the
live `uv run pbui` hand check remain for a later checkpoint. Do not add SymPy,
pandas, new printers or menus, completion, dragging, or another evaluation
thread.
