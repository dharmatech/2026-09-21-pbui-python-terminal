# repl 001 — Screen interaction and live hand check

**Status.** Ready to implement.

## Goal

Connect the repl 000 evaluator to the existing full-screen listener. Show a
distinct continuation prompt, make retained `Value` rows clickable for detail,
add their documentation and registered translator menus, and enforce the
continuation key and menu rules. Verify the finished REPL and predecessor
listener behavior in one real interactive terminal session.

This is the second and final slice of the accepted REPL specification. Stop
after the automated and live checks; do not start another exploration.

## Identity, authority, and starting point

- Identity is `(repl, 001)`, spoken **repl 001**.
- The human-accepted [`../spec.md`](../spec.md), especially sections 2–5 and
  **Slice 2 — screen and hand check** in section 6, is the authority. The
  charter is not an implementation input.
- [`000-python-evaluator.md`](000-python-evaluator.md) supplied colon dispatch,
  continuation state, the namespace, stream capture, `Value` history, bounded
  rows, and the class registry. The user reported its full suite green at
  **203 passed**. Run the gate again; do not treat that report as this
  checkpoint's verification.
- Listener 000–005 and listings 000–008 remain accepted. Their command
  grammar after the colon, typed and clicked accept, chips, listing capture
  and redisplay, menu items, history drawing, viewport anchoring, and terminal
  restoration remain required.
- Work in the existing project at
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application
  code and tests remain at the project root, never under `docs/`.

## Exact scope

### May edit

- `src/pbui/terminal.py` for the screen adapter, documentation, menus, keys,
  and drawing integration;
- `src/pbui/commands.py` and `src/pbui/repl.py` only for the headless `Value`
  detail operation and the smallest adapter methods needed to route a default
  click or registered translator; and
- `tests/test_terminal.py`, `tests/test_repl.py`, and `tests/test_commands.py`
  for focused regression tests of those changes.

For the live hand check, create one fresh, uniquely named disposable fixture
directory beneath the project root. Record its absolute path and leave it in
place for inspection. Only its designated disposable file may be removed by
the listener after the path check below.

### Must not edit or create

- `src/pbui/domain.py`, `src/pbui/substrate.py`, `src/pbui/text.py`, or their
  tests; `src/pbui/__init__.py` or `src/pbui/__main__.py`;
- `.python-version`, `pyproject.toml`, `uv.lock`, `README.md`, or `AGENTS.md`;
- another production module, test module, dependency, or console entry point;
- anything under `docs/`, including this checkpoint, the accepted spec, and
  previous checkpoints; or
- a file outside the project root, except the effects of running the existing
  uv-managed application and test tools.

If a missing headless seam appears to require a larger model redesign, stop
and return the checkpoint for correction instead of expanding the slice.
Only `pbui.terminal` may import Textual. Do not move evaluator state, stored
object identity, or menu effects into screen widgets.

## Continuation prompt and modal controls

The normal prompt stays exactly `pbui:/absolute/current/directory> `, using
the listener's safe escaped cwd. While `pending_python_source` is nonempty,
draw the prompt exactly `...> `. The pending source stays in the headless
controller; do not redraw it into the one-row editor, add a multiline editor,
or create a history row merely for entering continuation. The current editable
line starts clear after an incomplete submission. Enter passes that line to
the headless listener, which appends it to pending Python source even if it is
blank or begins with a colon. A completed evaluation returns to the cwd
prompt. Output and `Value` rows already retained by the evaluator appear
through the existing history surface and scroll behavior.

Show a continuation documentation sentence while source is pending, regardless
of hover. It must state that a Python continuation is open and that Ctrl-G or
Escape discards it. For this checkpoint use:

```text
Python continuation: enter another line; Ctrl-G or Esc discards it.
```

Ctrl-G and Escape discard a pending continuation and clear the editable line,
appending nothing. With no continuation, preserve the existing priority:
close an open menu first, otherwise cancel accept or input as before. While a
continuation is open, Ctrl-O and mouse button 3 neither open a menu nor
hit-test a menu target; they must not replace its documentation with a menu
refusal. A continuation and an action menu must not be open together.

Ctrl-D during a continuation performs the same discard as Ctrl-G and does not
exit. Ctrl-D exits only when the editable line is empty and there is no
continuation, chip, presentation accept, substring accept, or open menu. In
the other blocked states it does not exit. Ctrl-C exits from any state. Keep
the reviewed Textual lifecycle restoration for every exit and error path.

## `Value` drawing, default click, and detail

The existing `HistorySurface` draws the object-bearing `Value` row retained by
repl 000. Keep that single surface and its pure layout: no widget per value,
text reparsing, or second object registry. The complete logical `Value` row is
the presentation's hit region, including its wrapped physical segments. A
normal hover restyles only the affected physical rows. During a presentation
accept, `Value` is inert and receives the existing dim, non-target treatment;
it never supplies a chip or satisfies `show`, `rm`, `cd`, or `kill`, regardless
of the Python class of its stored object. The existing domain types keep their
exact accept behavior.

With no accept pending, a single left click on `Value` invokes the `Value`
detail branch of `show` with that exact retained object and leaves the input
unchanged. Add a headless operation in the permitted files for this branch;
do not make typed `:show` accept `Value`. Append one `Text` row of `TYPE: REPR`.
Escape and cap the type name at 64 display cells. The separate detail
representation uses bounded built-in container traversal to depth 6 and 64
items per container, never scans an arbitrary iterable, and is capped at 4096
display cells after escaping. A raising `__repr__` leaves the original
`Value` and `_` intact and appends one escaped `Error` instead of a `Text`
detail. Use the existing one-row safe display and history retention rules.

## Documentation and registered translator menus

At ordinary hover, the exact generic `Value` sentence is:

```text
Click to show this Python value; it has no action menu.
```

When that object's first MRO class registration has translators, the exact
sentence is:

```text
Click to show this Python value; Ctrl-O or right-click to open its action menu.
```

While `show`, `rm`, `cd`, or `kill` waits for a presentation, use its existing
refusal template with `Value` in place of another inert type. For example:

```text
Accept File for rm: Value is not a File target.
```

Keep the single mounted documentation row, its ellipsis truncation at narrow
widths, and refresh on hover, accept, continuation transitions, execution,
menu changes, scrolling, replacement, and resize. Existing sentences for all
other presentation types remain exact. The generic `Value` has no menu items;
an unsuccessful open gesture retains the established no-menu refusal behavior.

For a `Value` whose registered class has translators, open the existing
transient `ActionMenu` by Ctrl-O on the fresh hovered value or button 3 at its
fresh hit coordinate. Show labels in registration order. Each menu action
must retain the target presentation and the corresponding translator
identity or index; do not infer the operation from label text or route it
through colon parsing. Duplicate labels must still select their respective
registered functions. Selecting an item closes the menu, invokes the
headless translator on the original stored object, and appends its returned
object as a new `Value`, including `None`, or one `Error` on failure. The
headless API owns the `_` update and printer-failure handling. A registered
translator never replaces the default left-click detail action.

While a translator item is hovered, show exactly
`Click to apply “LABEL” to this Python value.` with that item's label. With
the menu open and no item hovered, retain the existing generic menu sentence.
Menu close, outside click, scrolling, viewport anchoring, stale-target checks,
and row-local menu hover continue to use the reviewed behavior. All existing
file, directory, process, and listing menu labels, order, and effects stay
unchanged.

## Automated tests

Run the whole predecessor suite without weakening or deleting its assertions.
Add focused `PbuiApp.run_test()` coverage using injected services and a
temporary root:

- Incomplete Python moves the prompt from the cwd form to `...> `, clears
  only the editable line, retains pending source, and shows the continuation
  documentation. A later blank or colon-starting line stays Python. Completion
  returns to the cwd prompt; Ctrl-G, Escape, and Ctrl-D each discard pending
  source without a command or exit. Ctrl-O and button 3 do not open a menu in
  that state; Ctrl-C still exits.
- Evaluating `1 + 1`, `print("a"); 1`, and an exception displays the existing
  headless `Value`, `Text`, and `Error` rows in history order. Hit testing a
  `Value` row returns its original presentation, including after wrap,
  scrolling, and resize. A left click appends its bounded detail `Text` row
  without editing input. A raising detail `repr` retains the value and adds
  one `Error`.
- Generic and registered `Value` hover produce their exact sentences; a
  pending domain accept produces the exact `Value` refusal and cannot consume
  it as a chip. Documentation remains one truncated visual row.
- A dummy class registered in the test supplies two ordered translators,
  including duplicate-label or command-like-label coverage. Ctrl-O and
  button 3 open their menu when supported by `run_test`; an item click uses
  its associated function, preserves the original object, updates `_` for
  returned values including `None`, and shows one `Error` while leaving `_`
  unchanged on failure. Default left click still shows detail. Generic
  `Value` has no menu.
- An empty ordinary Ctrl-D exits; nonempty input, chip, accept, substring
  accept, continuation, and menu each block that exit, with continuation
  using its required cancel behavior. Preserve Ctrl-C exit and terminal
  restoration assertions.
- Moving hover across a large wrapped history, including `Value` rows,
  restyles only the physical rows being left and entered. Preserve the
  listener 005 structural regression without elapsed-time assertions.

The headless detail formatter and its error path may have focused tests in
`tests/test_repl.py` or `tests/test_commands.py`. Keep automated tests free of
SymPy, pandas, network use, live process signaling, and physical-terminal
requirements.

## Live hand check

After the automated gate, run `uv run pbui` in a real interactive terminal
from one fresh disposable directory beneath the project root. Record its
absolute path and designate exactly one disposable file for `:rm`. Give the
fixture a subdirectory, several files with different sizes and mtimes, a
filename containing a space, and enough entries to scroll. Leave the fixture
in place for inspection. If no usable terminal is available, report this
checkpoint as unverified rather than treating `run_test()` as a substitute.

Observe and record these checks, using colons for every typed listener
command and none for Python source or menu actions:

1. Before any destructive action, verify the prompt shows the recorded
   absolute fixture path. Run `1 + 1`, bind and reuse a Python name, produce
   an exception, and evaluate a bare `ls`; check that the bare name gives a
   `NameError` and no directory listing. Then run `:ls` and check that it
   lists the fixture. Click a `Value` to show its longer detail, and enter
   then cancel a continuation.
2. Check the directory table's alignment, whole-row member hits, color,
   filename with a space, scrolling, and fixed documentation and prompt rows.
   Run `:sort size`, append a harmless Python value row, then use the older
   listing header menu to apply `sort mtime`; confirm in-place replacement
   and an unchanged intervening row.
3. Run `:narrow` with a substring, combine it with `:only files`, inspect a
   no-match view, and use `:widen` to restore the captured listing without
   appending a new listing or visibly rescanning. Check the substring modal
   prefix and documentation.
4. Use a member menu to `show` a file or directory. Use its directory `ls`
   action to append a new listing without replacing the older one. Use
   Ctrl-O; exercise button 3 only if the terminal reports it.
5. Run `:ps` and inspect the table columns and state colors. If a long
   command is available, check its truncation documentation and full detail
   through `show`; otherwise record that conditional check as unavailable.
   Do not signal any live process.
6. Scroll to an older wrapped listing, resize, and sort it from its header
   menu. Verify the retained header/member anchor and current hover remain
   connected to the right object where possible.
7. Recheck the prompt against the recorded fixture path. Show the designated
   file and verify its absolute path is inside the fixture. Only then invoke
   typed `:rm` for that exact file. Verify it is gone and the
   other fixture files remain. Do not run `kill`.
8. In safe contexts, check Ctrl-G and Escape cancellation of presentation
   accept, substring accept, and a menu. Check Ctrl-D cancels a Python
   continuation without exiting. Exit an ordinary empty-input session with
   Ctrl-D, launch again from the recorded directory, and exit with Ctrl-C.
   After each exit confirm shell prompt, visible cursor, normal input mode,
   mouse reporting, and alternate-screen restoration without stray escapes
   or a terminal traceback.

Report the absolute fixture path, the designated removed file, the terminal
used, the automated test count, each observation, conditional skips, and any
failure or restoration problem. Do not claim an unobserved check passed.

## uv workflow and completion boundary

Use only the existing uv-managed project. Add no dependency. From the project
root run:

```console
uv sync
uv run pytest
```

`uv run pytest` is the automated gate. Then perform the live check with
`uv run pbui` from the verified fixture directory. Do not use `pip`,
`python -m pip`, `uv pip install`, Poetry, Pipenv, Conda, Hatch, a hand-made
environment, or global Python. If uv is unavailable, stop and report it.

Repl 001 is complete only when the full suite passes and all mandatory live
checks are observed in the recorded directory. If a mandatory live check is
unavailable, report the checkpoint as unverified with the exact limitation.
Stop after reporting. Do not add Python-expression chips, SymPy or pandas
support, third-party pretty-printers, name completion, IPython history
variables, magics, a `%` escape, or another execution thread or process.
