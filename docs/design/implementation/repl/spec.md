# Specification — Python in the listener

**Status:** proposed specification for human review. This is the complete
design input for the later REPL checkpoint series. The charter is not an
implementation input. Application code and tests remain at the project root;
checkpoint files, written later one at a time, belong in this folder's
`checkpoints/` directory as **repl 000**, **repl 001**, and so on.

The existing full-screen Linux listener evaluates unprefixed input as Python
and presents its resulting object. A leading colon selects the existing
listener command grammar. Python values retain their identity in history.
This exploration has two ordered slices: a headless evaluator, then its screen
interaction. It adds no chip inside Python source and no third-party printer.

## 1. Authority and project boundary

This specification extends the accepted
[`listener/spec.md`](../listener/spec.md) through listener 005 and the
[`listings/spec.md`](../listings/spec.md) design implemented through listings
008. It supersedes these sentences and only these parts of their behavior:

- Listener section 1's statement that there is no evaluator, and listener
  section 6.1's statement that the editor has no multiline mode, are replaced
  by the Python evaluator and accumulated continuation source below.
- Listener section 5.1's dispatch of every submitted line as a command, and
  listings section 1's statement that there is no evaluator, are replaced by
  section 2 below. The command name/argument split, parsers, accept behavior,
  chips, and effects after command dispatch are unchanged.
- Listener section 6.2's complete documentation wording and listings section
  6.3's additions gain the `Value` wording below. Listings section 5.2's
  “any other presentation” no-menu row gains registered `Value` translators.
  Existing documentation and menu items for all other types stay exact.

The ten command names remain exactly `ls`, `ps`, `show`, `kill`, `cd`, `rm`,
`sort`, `narrow`, `only`, and `widen`. A typed command now needs a colon;
menu actions are not typed lines and do not gain one. Existing history
retention, exact presentation-type acceptance, listing redisplay, table
drawing, row-local hover, and terminal restoration remain required. A Python
`Value` is not a `File`, `Directory`, `Process`, or listing presentation even
when its stored object happens to be a path or process object.

Use the existing `src/pbui/` package and `tests/`, with Python 3.11 or newer.
Only `pbui.terminal` imports Textual. The evaluator and registration hook must
be testable without Textual. No new dependency is expected: `code`, `reprlib`,
and `traceback` are in the standard library. Implementers use the existing
uv-managed project, never `pip` or a hand-made environment. Every checkpoint
runs `uv sync` and `uv run pytest`; only the terminal checkpoint also runs
`uv run pbui` for its hand check. If uv is unavailable, stop and report it.

## 2. Submitted input and modal precedence

Dispatch a submitted line at the ordinary prompt only when no Python
continuation, presentation accept, substring accept, or action menu is open.
An empty or all-whitespace line does nothing. Otherwise remove leading
whitespace only for the dispatch decision. If the first remaining character
is `:`, remove that colon and at most one immediately following ASCII space.
An empty or all-whitespace remainder does nothing. Pass every other remainder
to the existing command parser, including its existing leading-whitespace
handling and chip path. It is never compiled as Python. Thus `:ls`,
`: ls /tmp`, and `:sort name` are commands; `:ls()` is an unknown command.

Every line without that leading colon is Python source. `ls`, `ls()`, and
`sort(name)` are Python, with no fallback to commands. If a single bare
command name fails with `NameError` because it is unbound, append an `Error`
that ends with `Use :NAME to run the listener command.` For example, bare
`ls` must produce a `NameError` and this hint, without listing a directory.
The hint is added only for a failed source consisting of that one identifier
and one of the ten command names; no command is run. Python source otherwise
keeps its original leading whitespace for compilation.

While a Python continuation is open, *every* submitted line, including a
blank line or one starting with `:`, is appended to the pending source after
one newline and compiled as Python. It is not reconsidered for command
dispatch. The existing presentation accept and substring accept remain modal
and take precedence over ordinary dispatch. Their clicks, chips, typed
buffers, Enter behavior, and cancellations stay as specified. An open action
menu likewise handles its own gestures before prompt dispatch; its actions
call the existing operations directly and never pass through colon parsing.

## 3. Python evaluator

The headless listener owns one namespace for its process lifetime. Initialize
it as `{"__name__": "__pbui__"}`. It is separate from `pbui` module globals;
do not insert listener command names into it. User bindings persist across
submissions. There is no shell expansion or external-command fallback.

Compile the current source with `code.compile_command(source,
symbol="single")`; do not write a Python parser. If it returns `None`, keep
the source, clear the editable input line, and show the continuation prompt.
Do not execute or append a result. If compilation raises `SyntaxError`,
`OverflowError`, or `ValueError`, append one `Error`, discard the pending
source, and return to the ordinary prompt. A compiled code object is executed
with `exec(code_object, namespace, namespace)`, then the pending source is
cleared whether execution succeeds or fails.

Install a temporary `sys.displayhook` only around that `exec`, saving and
restoring the previous hook in `finally`. For the same interval, replace
`sys.stdout` and `sys.stderr` with line-buffered writers and restore both in
that same `finally`. Do not let evaluated code write through to the process
streams; a full-screen session has no safe place for those bytes. The display
hook itself must not write to either stream.

Each writer buffers until a newline or until execution ends. A completed line
appends one history row at that moment, without the trailing newline. A
partial line still buffered at the end is appended the same way if it is
nonempty. An empty completed line, such as `print()`, appends one `Text`
presentation of the empty string. Standard-output lines are `Text`
presentations of the escaped line. Standard-error lines are `Text`
presentations of `stderr:` followed by one space and the escaped line. Escape
both with the existing `escape_display` before storing them, so the `Text`
drawer can keep returning its stored string unchanged. Cap each of those rows
at 4096 display cells after escaping, keeping the beginning and ending with
`…` inside the cap when a line is longer.

For each non-`None` value received by the hook, in call order, set
`namespace["_"]` to the original object and append one object-bearing `Value`
presentation at that moment. The last such value wins `_`. A hook call with
`None`, or a statement that never invokes the hook, appends no value and
leaves `_` unchanged. Printed lines and values therefore appear in the order
the code produced them. This makes `1 + 1` show `int 2`, while `import math`
adds no value row and leaves `math` bound; `math.sqrt(4)` then shows
`float 2.0`. `print("a"); 1` shows a `Text` row `a` and then `int 1`.

Catch exceptions raised during `exec`, including `SystemExit` and
`KeyboardInterrupt` raised by evaluated Python. Append one `Error` with the
traceback and return to the prompt; the listener stays open. A value already
presented before that exception stays in history and remains `_`. Always
restore the previous display hook, including on a failure. Evaluation is
synchronous: a long-running call blocks the listener, as a long command does.
This specification adds no worker thread or process.

Ctrl-G discards a pending continuation and clears the input line, appending
nothing. Escape does the same when a continuation is open. Otherwise both
keys retain their existing menu, accept, and input cancellation priorities.

A continuation is modal, in the same way an accept or an open menu is modal.
While one is open, Ctrl-O and mouse button 3 do not open a menu and do not
hit-test a menu target. The documentation line says a continuation is open
and that Ctrl-G or Escape discards it. Ctrl-D does not exit while a
continuation, an accept, a chip, a non-empty input line, or a menu is open.
When the blocked condition is a continuation, Ctrl-D discards that
continuation and appends nothing, exactly as Ctrl-G does. Ctrl-D exits only
when the input line is empty, no chip or accept is pending, no menu is open,
and no continuation source is retained. Ctrl-C still exits from any state and
restores the terminal. These key actions are distinct from Python code that
raises an exception.

### Errors

Use the existing `Error` presentation. Its drawer keeps drawing `Error:` plus
the stored message and does not escape. The evaluator therefore escapes every
error message with `escape_display` before storing it, which turns newlines
into the two characters `\n` and makes the stored message one logical row.
One failure appends one `Error`, never one per traceback frame. A compile
failure starts with `SyntaxError: MESSAGE (line N, column C).` when both
coordinates exist; for `OverflowError` and `ValueError`, use
`CLASS: MESSAGE.` The error message uses the exception's text and omits
unavailable coordinates. Escape that text, then cap it.

An execution error formats a standard Python traceback: `Traceback (most
recent call last):`, the final eight frames at most, and the exception type
and message. Add the colon hint from section 2 to that final exception line
before escaping. Then escape the whole formatted traceback and cap the
escaped text at 4096 display cells:

- If the escaped traceback fits, store it all.
- If it does not, drop frames from the front and keep the escaped final
  exception line intact whenever that line itself fits in 4096 cells.
- If the escaped final exception line alone exceeds 4096 cells, store its
  first 4095 display cells and a final `…`. The exception class is at the
  start of that line, so the tail of a huge message is what is cut.

The cap applies to the stored message, not to the `Error:` prefix the drawer
adds. The traceback belongs to a single `Error` presentation; it never
escapes as a terminal traceback or closes the app. Output captured before
the exception stays in the history ahead of this `Error`.

## 4. `Value` presentations and showing detail

Register one explicit presentation type named `Value` in the existing
presentation-type registry. Every displayed Python result uses it, regardless
of the object's Python class. A class registration can supply its row printer
and menu actions as described in section 5; it does not change the
presentation type or stored object. The history retains the original object
by identity; text is never parsed to reconstruct it.

The generic logical row is `TYPE REPR`: the object's class `__name__`, one
space, then a bounded representation. Escape and cap `TYPE` at 64 display
cells. Keep at most 96 display cells of the escaped representation, adding
`…` within that limit when truncated. A short, one-token `repr` appears in
full. Bound built-in container traversal to depth 4 and 16 items per
container for the row; the detail view may use depth 6 and 64 items per
container. `reprlib` or an equivalent bounded helper may supply this, but
must propagate a user's raising `__repr__` so it becomes an `Error`. Neither
printer walks an arbitrary iterable to build a preview. A user-defined
`__repr__` may itself take time, like any other Python call; it receives no
new execution thread. Escape embedded newlines, tabs, control characters,
and unpaired surrogates using the
listener's existing safe-display rules. The row is one logical line; existing
terminal layout may wrap it on a narrow screen.

Append the `Value` presentation before trying to render its row. Start with
the fallback row `TYPE <repr unavailable>`. On a successful representation,
replace that fallback text in the same logical row without changing the
presentation identity. If `repr` or a registered row printer raises, retain
that fallback `Value` row and append one `Error` naming the failure. `_` still
refers to the original object. The same rule applies when a `repr` requested
by detail fails: the original `Value` stays and one `Error` is appended.

With no accept pending, a left click on `Value` runs the `Value` detail branch
of `show` and does not alter input. It appends one `Text` row, `TYPE: REPR`,
using a separate bounded representation capped at 4096 display cells after
escaping. `TYPE` has the same 64-cell cap as the history row. This direct-click detail branch does not extend
typed `:show` acceptance. During any existing presentation accept, `Value` is
inert: it is not acceptable to `ls`, `ps`, `show`, `cd`, `rm`, `kill`, or any
listing view command, and it creates no chip. Its exact type remains `Value`
even if its Python class resembles an accepted domain type.

The generic `Value` has no action-menu items. With no accept and no menu open,
the documentation sentence on hover is exactly:

```text
Click to show this Python value; it has no action menu.
```

For a `Value` with registered translators, it is exactly:

```text
Click to show this Python value; Ctrl-O or right-click to open its action menu.
```

While `show`, `rm`, `cd`, or `kill` waits for an object, the `Value` refusal
uses the accepted sentence for that command with `Value` substituted for the
other inert type (for example, `Accept File for rm: Value is not a File
target.`). Existing hover, accept highlighting, documentation truncation,
screen hit testing, and local row restyling apply to the whole `Value` row.

## 5. Class registration hook

Provide a headless registration API mapping a Python class to a row printer
and an ordered list of menu translators. A translator has a menu label and a
function receiving the original object and returning a new object. Lookup
walks `type(value).__mro__` in order and uses the first registered class; it
does not combine printers or translators from multiple classes. The registry
starts empty, and the product registers no class. `Value` remains one
explicit presentation type, so this Python-class lookup does not change the
substrate's exact type acceptance or the existing domain registry.

A registered printer returns the entire row text used in place of `TYPE
REPR`. Escape its output and cap it to one logical row and 120 display cells;
a printer failure follows the fallback-and-`Error` rule above. A registered
translator appears in the `Value` action menu under its label, in registered
order. Choosing it closes the menu, calls the function with the stored object,
and appends a new `Value` presentation of the returned object, including
`None`. Set `_` to that new displayed object. If the function raises, append
one `Error`, leave `_` unchanged, and retain the original presentation. A
translator result is processed through the same class registry, and an error
while printing it follows the same retained-value rule. Menu action dispatch
is direct; the user does not type a colon for it.

While a registered `Value` translator item is hovered, the documentation
sentence is exactly `Click to apply “LABEL” to this Python value.`, using
that item's label. The existing generic menu sentence applies while the
menu is open with no item hovered.

`Value` left click always runs the detail branch of `show`; registration adds
menu items but does not replace the default click. The existing menus for
files, directories, processes, and listings keep their exact items and
effects. Tests register a dummy class in the test file and demonstrate that
its printer and one translator override the generic row and empty menu.

## 6. Verification and slice order

Preserve the existing tests and their coverage. Tests that submit typed
commands must use the new leading-colon syntax; their command parsing,
effects, chips, accept, menus, listing redisplay, hover, and history
assertions otherwise remain required. Automated tests use injected services
and temporary roots, never SymPy, pandas, or the network. The automated gate
is `uv run pytest`.

### Slice 1 — evaluator, headless

Implement dispatch, `compile_command`, continuation state, namespace,
temporary display hook, `Value` and `Error` history, `_`, bounded printing,
and the class registry without importing Textual. Headless tests prove at
least:

- `1 + 1` retains the integer object and prints `int 2`; `import math`
  binds without adding a value; `math.sqrt(4)` prints `float 2.0`;
- bare `ls` reports `NameError` plus the colon hint and has no listing effect;
  `:ls`, `: ls /tmp`, `:sort name`, and an unknown `:ls()` follow command
  dispatch, including existing chips and accept;
- incomplete source waits, subsequent blank and colon-starting lines remain
  Python, and Ctrl-G, Escape, and Ctrl-D each discard a continuation without
  exiting or running a command;
- `print` and `sys.stderr` writes become capped `Text` rows in program order
  ahead of a later value or error, and the real process streams are restored;
- compilation errors and execution exceptions add one escaped `Error` each,
  keep the listener open, and restore the previous display hook, stdout, and
  stderr;
- a traceback longer than 4096 display cells keeps the escaped final
  exception line, and a final line that is itself longer is cut at 4095 cells
  plus `…`;
- repeated hook calls present in order, update `_` to the last non-`None`
  value, and a later exception preserves an earlier displayed value;
- a raising `repr` keeps the exact stored object in a `Value` row and adds
  one `Error`; a short `repr` is untruncated, while long and control-character
  output remains bounded and safe; and
- a dummy class registration selects the first MRO match, uses its printer
  and translator, and leaves exact presentation-type acceptance unchanged.

### Slice 2 — screen and hand check

Add the visibly different continuation prompt, screen `Value` row and detail
click, documentation sentences, menu items for registered translators, and
cancel behavior. While a continuation is open, Ctrl-O and button 3 do not
open a menu, and Ctrl-D does not exit. The normal prompt remains
`pbui:/absolute/current/directory> `; the continuation prompt is exactly
`...> `, with the pending source retained in the controller rather than
redrawn into the one-row editor. A `PbuiApp.run_test()` case should verify
the prompt transition, a `Value` hit and click, and the new documentation
wording. Preserve the listener 005 regression: moving hover across a large
history restyles only affected physical rows.

Run the live hand check with `uv run pbui` from a fresh disposable directory
under the project root. Record its absolute path and verify the prompt before
any `rm`. Exercise `1 + 1`, a persistent name binding and use, an exception,
a bare `ls` that does not list, and `:ls` that does. Verify a `Value` click
shows more detail and a continuation can be cancelled. Then repeat the
listings hand check's sorting, filtering, menus, scrolling, resize, accept,
and terminal-restoration steps using colons for typed commands. Before the
designated disposable-file `:rm`, verify the prompt still shows the recorded
directory. Do not run `kill` against a live process.

The human reviews this specification before any checkpoint is written. No
checkpoint may introduce a Python-expression chip, SymPy or pandas support,
third-party pretty-printers, name completion, IPython history variables,
magics, a `%` escape, or a second execution thread or process.
