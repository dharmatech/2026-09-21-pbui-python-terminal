# repl 000 — Headless Python evaluator

**Status.** Ready to implement.

## Goal

Add Python evaluation to the existing headless listener. Unprefixed submitted
input is Python; a leading colon selects the existing command grammar. Retain
Python results as object-bearing `Value` presentations, capture printed output,
and keep compilation, execution, and representation failures in history.

Stop when the headless evaluator and the full automated suite are green. This
checkpoint does not implement the terminal presentation of the REPL.

## Identity, authority, and starting point

- Identity is `(repl, 000)`, spoken **repl 000**.
- The human-accepted [`../spec.md`](../spec.md), especially sections 1–5 and
  **Slice 1 — evaluator, headless** in section 6, is the authority. Follow it
  when this checkpoint is silent. The charter is not an implementation input.
- Listener 000–005 and listings 000–008 are implemented. Preserve their
  behavior except for the accepted change to typed-input dispatch.
- Work in the existing project at
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application
  code and tests stay at the project root, never under `docs/`.
- Python is 3.11 or newer. The project and environment already use uv.

## File and feature boundary

The headless implementation may edit `src/pbui/commands.py` and the existing
plain-Python presentation modules `src/pbui/domain.py`, `src/pbui/substrate.py`,
and `src/pbui/text.py` as needed. A focused `src/pbui/repl.py` may be added for
evaluation, stream capture, bounded representation, and class registration.
Keep that module independent of Textual. Add focused tests in
`tests/test_repl.py` and update existing tests in `tests/test_commands.py`,
`tests/test_domain.py`, or `tests/test_substrate.py` only where the headless
model changes require it. Edit `tests/test_terminal.py` only to migrate
predecessor typed-command submissions to the new colon form and preserve their
existing assertions. No production edit to `src/pbui/terminal.py` belongs in
this checkpoint.

Do not change dependencies, the project metadata, command names or argument
grammar, host service seams, domain command effects, chips, presentation
acceptance, listing capture or redisplay, or existing menus. Do not add a
Textual import to the evaluator or another nonterminal module. The only
presentation type added here is `Value`; its Python-class registration does not
alter exact presentation-type acceptance.

## Dispatch and continuation state

At the ordinary headless prompt, do nothing for an empty or all-whitespace
line. Remove leading whitespace for the dispatch decision only. If the first
remaining character is `:`, remove it and at most one immediately following
ASCII space. Do nothing if the remainder is empty or whitespace; otherwise
pass it to the existing command parser, including the established leading
whitespace, chip, and accept paths. Never compile a colon command as Python.
`:ls`, `: ls /tmp`, and `:sort name` are commands; `:ls()` is an unknown
command. Menu operations remain direct calls to their existing operations.

Every other ordinary submission is Python source, preserving its original
leading whitespace. `ls`, `ls()`, and `sort(name)` have no command fallback.
For an unbound bare name that is exactly one of the ten command names, append
one `NameError` presentation whose final line ends with
`Use :NAME to run the listener command.` The command must not run.

Keep pending Python source on the headless listener. When it is nonempty,
append every submitted line after one newline, including a blank or
colon-starting line, and compile the accumulation as Python. The pending
continuation takes precedence over ordinary dispatch. Existing presentation
accept and substring accept retain their modal typed-input and cancellation
behavior. Expose the headless cancellation operation needed for Ctrl-G,
Escape, and Ctrl-D to discard a continuation and clear the editable input
without a history row or command effect. Terminal key bindings and the
continuation prompt wait for a later checkpoint.

## Evaluation and output history

Own one namespace for the lifetime of the listener, initially
`{"__name__": "__pbui__"}`. Keep it separate from `pbui` module globals and do
not populate it with listener command names. Bindings persist across
submissions. Compile accumulated source with
`code.compile_command(source, symbol="single")`. `None` retains the pending
source, clears the editable line, and executes nothing. A `SyntaxError`,
`OverflowError`, or `ValueError` appends one `Error`, drops the pending source,
and returns to ordinary dispatch. Execute a completed code object with
`exec(code_object, namespace, namespace)` and clear pending source on success
or failure. There is no shell or external-command fallback.

For the interval of that `exec`, temporarily install `sys.displayhook` and
line-buffered `sys.stdout` and `sys.stderr` writers. Save and restore all three
in the same `finally`, including when evaluated code raises `SystemExit` or
`KeyboardInterrupt`. Evaluated writes must not reach the real process streams;
the display hook must not write to either captured stream. Evaluation remains
synchronous, with no worker thread or process.

Append a `Text` presentation when a writer completes a line, omitting its
trailing newline; flush a nonempty partial line at execution end. An empty
completed line, including `print()`, is one empty `Text` row. Prefix stderr
rows with `stderr: `. Escape each line with `escape_display` before storing it,
then cap the complete row to 4096 display cells, preserving the beginning and
placing `…` within the cap when truncated. The existing `Text` drawer can draw
the stored string unchanged. Append completed output rows and displayed values
in program order: `print("a"); 1` gives a `Text` row `a`, then `Value` `int 1`.

For every non-`None` display-hook call, append one `Value` carrying the exact
original object and set `namespace["_"]` to that object. Multiple calls append
in order, with the last one winning `_`. A `None` hook call or a statement that
never calls the hook adds no value and leaves `_` unchanged. If execution
later raises, preserve earlier output and values, then append one `Error`.

## `Value` rows and class registration

Register one explicit presentation type named `Value` in the listener's
existing type registry. Every Python result uses it, regardless of the
object's Python class; a Python object resembling a path, process, or listing
does not become an accepted domain presentation. The class registry starts
empty and the product registers no class.

The generic row is `TYPE REPR`. Escape and cap the class `__name__` at 64
display cells. Escape the representation and cap it at 96 display cells,
including `…` when truncated. A short one-token `repr` must remain whole.
Bound built-in container traversal to depth 4 and 16 items per container;
never consume an arbitrary iterable for a preview. Use `reprlib` or an
equivalent bounded helper without swallowing a user's raising `__repr__`.
Apply the existing safe-display rules for controls, newlines, tabs, and
surrogates. The row is one logical line even if a later narrow terminal wraps
it physically.

Append the `Value` presentation with fallback drawing
`TYPE <repr unavailable>` before invoking its generic or registered printer.
On success, replace the drawing in that same logical history row while
preserving the presentation and stored-object identities. On printer failure,
retain the fallback `Value` and append one `Error`; `_` still refers to the
original object. If the existing history API needs a narrow same-row drawing
replacement operation, preserve its row ordering, retention, presentation
lookup, revision, and listing-block invariants. Do not route this through
listing redisplay or append a second `Value` row.

Provide a headless API that maps a Python class to one row printer
and an ordered list of translators, each with a label and function. Lookup
walks `type(value).__mro__` and uses only the first registered class. A
registered printer returns the entire row, which is escaped and capped at 120
display cells; its failure uses the same fallback-and-`Error` path. A
registered translator receives the stored original object. Invoking it
headlessly appends a new `Value` for its return, including `None`, and sets
`_` to that displayed object. On translator failure append one `Error`, retain
the original presentation, and leave `_` unchanged. The new value goes
through the same class lookup and printing path. This checkpoint stores and
tests translator order and invocation; rendering action-menu items waits for
the screen checkpoint.

## Error formatting

Use the existing `Error` presentation and leave its drawer as `Error: ` plus
the stored message. The evaluator applies `escape_display` before storing
every compile, execution, printer, or translator error, so newline becomes the
two printable characters `\n` and one failure occupies one logical row.
Escape compile-error text, then cap it at 4096 display cells. A syntax error begins
`SyntaxError: MESSAGE (line N, column C).` when both coordinates exist;
`OverflowError` and `ValueError` use `CLASS: MESSAGE.` with missing coordinates
omitted.

For an execution exception, format a standard Python traceback with at most
the final eight frames and the exception type and message. Add any bare-name
colon hint to the final exception line before escaping. Cap the escaped stored
message at 4096 display cells, excluding the drawer's `Error: ` prefix. If
longer, discard frames from the front while retaining the final exception
line whole when it fits. If that escaped line alone exceeds 4096 cells, store
its first 4095 cells followed by `…`; its exception class remains at the
beginning. An exception stays inside the listener and adds exactly one
`Error`, after any output already captured. Restore the display hook and both
streams even on this path.

## Automated tests and predecessor migration

Keep the predecessor coverage. Change every existing test that **submits a
typed command** to use a leading colon in this checkpoint, including unknown
command tests, calls through `HeadlessListener.submit`, and command text
submitted by terminal tests. Preserve their parser, effect, chip, accept,
menu, listing, hover, and history assertions. Do not add a colon to Python
source, a substring-accept buffer, or unrelated editor-only text.

Add headless tests covering every case listed in specification section 6,
Slice 1:

- `1 + 1` retains the integer object and draws `int 2`; `import math` binds
  without a value row; `math.sqrt(4)` draws `float 2.0`.
- Bare `ls` gets `NameError` and the colon hint without listing; `:ls`,
  `: ls /tmp`, `:sort name`, and unknown `:ls()` take the command path,
  preserving chips and accept.
- Incomplete source retains state; blank and colon-starting continuations
  remain Python; logical Ctrl-G, Escape, and Ctrl-D cancellation paths discard
  pending source without exit or command effect.
- `print`, empty `print()`, and stderr writes create correctly escaped and
  capped `Text` rows in program order before a later value or error; previous
  process streams are restored.
- Compile failures and execution exceptions append one escaped `Error`, leave
  the listener usable, and restore the prior display hook, stdout, and stderr.
  Test the 4096-cell traceback cap, both a retained whole final exception line
  and a final line cut at 4095 cells plus `…`.
- Repeated hook calls present in order and update `_` to the last non-`None`
  object; a subsequent exception preserves an earlier value and `_`.
- A raising `repr` retains the exact object in one fallback `Value` and adds
  one `Error`; short output remains untruncated, while long or control-bearing
  output remains bounded and safe.
- A dummy class defined in the test selects the first MRO registration,
  supplies its printer and one translator, and leaves exact presentation-type
  acceptance unchanged. Exercise returned `None` and translator failure
  through the headless API.

Use injected services and temporary roots; automated tests must not require
SymPy, pandas, the network, a live process signal, or a physical terminal.

## uv workflow and completion boundary

Use the existing uv-managed project. Add no dependency. From the project root:

```console
uv sync
uv run pytest
```

`uv run pytest` is the automated gate. Do not require `uv run pbui` or a live
terminal hand check in repl 000. Do not use `pip`, `python -m pip`,
`uv pip install`, Poetry, Pipenv, Conda, Hatch, a hand-made environment, or
global Python. If uv is unavailable, stop and report it.

Repl 000 is complete when the evaluator and registration hook are headless,
all Slice 1 cases pass, every predecessor typed-command test uses the colon
form, and the full suite passes. Stop there. The continuation prompt, `Value`
rows on screen, detail clicks, documentation sentences, translator menu items,
Ctrl-O, mouse button 3, and Ctrl-D handling in Textual belong to a later
checkpoint. Do not add a Python-expression chip, SymPy or pandas support,
name completion, or a second execution thread or process.
