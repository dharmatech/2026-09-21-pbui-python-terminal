# listener 004 — Terminal interaction and lifecycle

**Status.** Ready to implement.

## Goal

Complete the listener by activating the passive terminal surface: implement the
one-row editor, bracketed paste, submission and cancellation, mouse hover and
left-click object selection, three-row wheel scrolling, fresh coordinate hit
testing, exit bindings, production composition, console and module entry
points, and terminal restoration. Finish with the automated interaction test
and the guarded live hand check.

This is the final listener checkpoint. Stop when it is green and the hand check
passes. Do not add another command, shell grammar, evaluator, command history,
completion, popup, right-click behavior, graphical presenter, or any feature
listed outside the accepted product boundary.

The implementer receives this checkpoint and the accepted listener
specification. This checkpoint completes the second half of the terminal layer;
it does not revise the specification.

## Identity, authority, and predecessors

- Identity is `(listener, 004)`, spoken **listener 004**.
- [`../spec.md`](../spec.md), especially sections 1, 2, 6, 6.1, 6.4, 7.4,
  7.5, and 8, is the design authority. Preserve it when this checkpoint is
  silent.
- Listener 000 through [listener 003](003-terminal-drawing-and-layout.md) are
  implemented and reviewed. All 91 current tests pass.
- Listener 002 supplies the complete `HeadlessListener`, safe host seams,
  command submission, accept/chip state, cancellation, selection, translators,
  and production headless composition.
- Listener 003 supplies `PbuiApp`, `ListenerScreen`, `HistorySurface`,
  `DocumentationLine`, `CommandInput`, current pure layout, programmatic
  scrolling, hover styling, prompt/chip drawing, resize anchoring, and complete
  passive synchronization hooks.
- The project root is
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application code
  and tests remain there, never under `docs/`.

Extend those objects directly. Do not add a second editor, history renderer,
coordinate model, command parser, application controller, or terminal module.
Presentation values and display intervals remain authoritative in the reviewed
plain-Python layers.

## Exact file scope

### May create or edit

- `src/pbui/terminal.py`
- `src/pbui/__main__.py` (new)
- `tests/test_terminal.py`
- `pyproject.toml`, only to add the exact `pbui` console entry point
- `uv.lock`, only if `uv sync` updates root-package metadata

### Must not edit or create

- `.python-version`, `README.md`, `AGENTS.md`, or `src/pbui/__init__.py`
- `src/pbui/substrate.py`, `src/pbui/text.py`, `src/pbui/domain.py`,
  `src/pbui/commands.py`, or any of their existing tests
- any new dependency
- another production module or test module
- anything under `docs/`, including earlier checkpoints and the specification
- any file outside the project root, except the terminal emulator's own
  transient state during the live hand check

If a predecessor production file appears necessary, stop and return the
checkpoint for correction instead of widening the slice.

## Dependencies, metadata, and uv workflow

Add no dependency. Keep runtime dependencies exactly Rich, Textual, and
wcwidth; keep development dependencies exactly pytest and pytest-asyncio.

Set the exact console entry in `pyproject.toml`:

```toml
[project.scripts]
pbui = "pbui.terminal:main"
```

Create `src/pbui/__main__.py` as a minimal forwarder to that same `main`
function. It contains no listener composition or exception policy of its own.

Run all Python lifecycle commands through uv:

```console
uv sync
uv run pytest
```

The guarded physical-terminal check later uses:

```console
uv run pbui
```

`uv run python -m pbui` must reach the same function, but do not launch a
second physical hand-check session merely to duplicate every step. Do not use
`pip`, `python -m pip`, `uv pip install`, Poetry, Pipenv, Conda, Hatch, or
globally installed packages. If uv is unavailable, stop and tell the human.

## Interaction synchronization contract

After any editor, accept, command, selection, cancellation, scroll, or resize
transition, update the three passive views coherently:

1. synchronize `HistorySurface` if history, width, or accept styling changed;
2. recompute the presentation under the current pointer when coordinates are
   still meaningful, otherwise clear hover;
3. refresh history styles and the exact documentation sentence;
4. refresh prompt, input, chip, and cursor drawing; and
5. clamp history scroll and editor cursor.

Do not recreate widgets or the screen. A history-producing action should reveal
the newly appended result by scrolling history to its newest physical rows.
An action with no new history, such as successful `cd` or entering accept,
preserves/clamps the current history position while updating prompt or styles.

The documentation line is recalculated on hover, leave, accept changes,
execution, scrolling, and resize. The prompt and documentation never scroll
with history.

## One-row editor behavior

Activate the existing `CommandInput`. Its editable value is exactly
`listener.input_text`; its cursor remains a Python code-point insertion index
from zero through `len(input_text)`. Every edit calls the listener's existing
text setter and refreshes drawing without creating a shell token model.

Support exactly:

- insertion of printable characters at the cursor;
- bracketed paste at the cursor;
- Left and Right by one code point;
- Home to zero and End to `len(input_text)`;
- Backspace before the cursor;
- Delete at the cursor; and
- Enter submission.

Filter paste to a single row: preserve printable characters and ordinary
spaces exactly, and discard LF, CR, tab, C0/C1 control characters, unpaired
surrogates, and other non-printable code points. Apply the same one-row rule to
individual key insertion. A literal Tab key remains Textual focus navigation;
it does not insert a tab or trigger completion.

There is no command history, completion, multiline input, shell quoting,
word-motion, kill/yank ring, evaluator, or second argument. Up and Down do not
recall commands. Unrecognized editing keys leave the model unchanged.

### Atomic chip editing

A chip remains outside `listener.input_text` and is never parsed as characters.
When a chip exists and the cursor is at the end of editable command text, one
Backspace removes the entire chip through `listener.backspace_chip()` and
removes no command character. Otherwise Backspace removes at most the preceding
text code point. The cursor never enters the chip label. Delete is not required
to remove a chip.

The normal product path supplies a valid clicked chip and immediately runs its
waiting command, so a rendered chip may be brief; tests still prove the atomic
editor model without changing that immediate execution rule.

### Enter

Enter passes the current complete text to `HeadlessListener.submit()` exactly
once. Then:

- a completed command clears input/chip/request through the headless model and
  moves the cursor to zero;
- a missing required argument leaves the normalized command name in the editor,
  enters accept, and moves the cursor to its end;
- a typed parse or command failure draws its Error result and clears the
  editor; and
- empty input does nothing.

Synchronize every view afterward. If history gained rows, reveal the newest
physical row. Never parse or execute in `CommandInput` itself.

## Cancellation and app key bindings

Reserve both `Ctrl-G` and Escape for one action that calls
`HeadlessListener.cancel()`, clears input/request/chip, resets the cursor, clears
or recomputes hover styling, and refreshes documentation. This single-screen
application has no needed Escape behavior that outranks cancellation.

`Ctrl-D` exits only when all three are true:

- input text is exactly empty;
- no chip exists; and
- no accept request is pending.

In every other state `Ctrl-D` does nothing. It is a key action, not a seventh
command and not an input character.

`Ctrl-C` exits from any state. Both exit paths use ordinary Textual `App.exit`
and its cleanup. Do not call `os._exit`, manually write alternate-screen escape
sequences, or bypass Textual's driver teardown.

Keep application bindings focused and non-discoverability UI is not required.
Bindings must not add a footer, command palette, or popup.

## Pointer-coordinate translation

All pointer handling lives on `HistorySurface`. Maintain the most recent
pointer offset inside its **content area** for hover recomputation after scroll
or resize. Use Textual's coordinate conversion for the widget/content region;
do not assume that event screen coordinates already exclude borders, padding,
or scrollbar gutters.

For every pointer lookup:

1. synchronize the surface to current history and width;
2. reject coordinates outside the current content area;
3. derive zero-based content-column `x` from the content offset;
4. derive laid-out physical history-row `y` as content-offset row plus current
   integer `scroll_y`;
5. call the current pure `Layout.hit_test(x, y)`; and
6. use that returned retained `Presentation` directly.

Do not use Rich character spans, cached pre-scroll coordinates, widget ids, or
drawn label parsing for object lookup. Horizontal scrolling remains disabled,
so no hidden horizontal offset is introduced.

When a presentation must be supplied to `HeadlessListener.select`, derive only
its drawing label for the atomic chip: safely escaped basename for `File` or
`Directory`, canonical decimal pid for `Process`. The original value still
comes from the presentation object.

## Mouse move and leave

On `events.MouseMove` over history, compute a fresh hit from the event's current
content offset. Store the pointer offset, set the exact hovered presentation,
redraw styles, and update documentation. Moving over literal text, padding,
scrollbar space, or empty history sets hover to none and displays the applicable
no-pointer sentence.

On `events.Leave`, forget the pointer offset, clear hover, redraw, and display
the applicable no-pointer sentence. Do not retain a presentation merely because
it was previously under the pointer.

While accept is pending, hovering an inert presentation changes documentation
but never adds reverse or target styling; listener 003's reviewed style model
remains authoritative.

## Left click

On `events.Click`, act only when `button == 1` and `chain == 1`. Right click,
middle click, later clicks in a double/triple-click chain, scrollbar clicks not
mapped to content, and clicks outside content do nothing.

For a qualifying click, calculate a fresh hit from that click's coordinates;
do not trust the last move event. Pass the hit and its display label to
`HeadlessListener.select()` exactly once.

- During accept, an exact target supplies its stored value and immediately runs
  the waiting command; a non-target changes no input, request, chip, history,
  or host state.
- With no accept, `File`, `Directory`, and `Process` invoke their registered
  `show` translator; `Text`, `Error`, literal fields, padding, and empty history
  do nothing.

After a successful selection, synchronize all views and reveal appended output.
After a refused/non-action click, retain accept and editor state while updating
the exact documentation sentence for the current pointer.

Do not implement a popup, context menu, right-click action, middle-click action,
double-click action, confirmation dialog, delete mark, or gesture recognizer.

## Wheel scrolling and resize hover

Map `events.MouseScrollUp` and `events.MouseScrollDown` over history to exactly
three physical rows per event. Clamp through the reviewed programmatic scroll
operation. Documentation and command input remain fixed.

After scrolling, recompute hover from the stored pointer offset against the new
`scroll_y`; do not leave documentation referring to the object formerly at that
screen coordinate. After resize, keep listener 003's oldest-visible-logical-row
anchor, then recompute hover through the new layout and coordinates. If the
pointer is no longer over content or its presentation was dropped, clear it.

Stop handled wheel events from acquiring a second default scroll step. Do not
cache a pre-scroll `Presentation` as the post-scroll hit.

## Production lifecycle and entry points

Implement `main()` in `pbui.terminal` with this single composition path:

1. construct the existing production `HeadlessListener` using the process's
   current cwd, production filesystem, and Linux process service;
2. construct `PbuiApp(listener)`; and
3. call Textual's ordinary non-inline `run()` so it owns the alternate screen,
   mouse reporting, cursor/input modes, resize delivery, and cleanup.

Catch `KeyboardInterrupt` only at this outer boundary and return normally
without a traceback. Do not catch ordinary pbui programming defects. Normal
Textual exit, `Ctrl-D`, and `Ctrl-C` must all unwind through the same cleanup.

`src/pbui/__main__.py` imports and calls this `main()` under the usual module
guard. The console script and module path therefore use identical composition
and lifecycle behavior.

## Automated terminal tests

Extend `tests/test_terminal.py`; it remains the only test module allowed to
import Textual. Use pytest-asyncio, injected rooted temporary listeners, fixed
process services, and `PbuiApp.run_test()`. Do not use the live process table,
delete outside `tmp_path`, or open a physical terminal in automated tests.

At minimum add coverage for all of the following:

1. Metadata has exactly `pbui = "pbui.terminal:main"`; `pbui.__main__` forwards
   to the same function; dependencies are unchanged; and only
   `pbui.terminal` imports Textual.
2. The editor inserts printable text at beginning/middle/end and supports Left,
   Right, Home, End, Backspace, and Delete with cursor clamping.
3. Paste inserts at the cursor, preserves printable spaces and Unicode, and
   filters newline, carriage return, tab, controls, and an unpaired surrogate
   so the input stays one row. Tab does not insert or complete.
4. A chip remains outside input text and one adjacent Backspace removes it
   atomically without deleting a command character.
5. Pilot presses `l`, `s`, and `enter`, waits for messages to settle, and proves
   the listener history contains a `File` or `Directory` presentation for a
   known temporary child whose stored path is the expected absolute path. The
   prompt and documentation widgets remain mounted.
6. Enter on `rm`, `cd`, `kill`, and `show` with no argument enters the exact
   accept state and restyles/documentation immediately; typed success and
   expected failure clear editor state and reveal appended output.
7. Ctrl-G and Escape each clear text, chip, and accept without a command effect.
8. Ctrl-D exits only from empty/nonwaiting state and is inert with text, chip,
   or pending accept. Ctrl-C exits from every tested state through the app exit
   path.
9. A pure or direct widget-level coordinate test covers content-origin
   subtraction, vertical `scroll_y` translation, padding/literal misses, and a
   fresh hit after scroll/resize. The required pilot test need not synthesize a
   mouse click.
10. Mouse move/leave helpers set and clear hover/documentation from fresh pure
    hits. A qualifying single left click calls headless selection once; other
    buttons and later click-chain members do nothing.
11. An accept target click uses the original object rather than label text; a
    non-target click preserves all state; a default click shows a path/process;
    Text, Error, and literal clicks have no command effect.
12. Each wheel direction changes history by exactly three physical rows and
    clamps, without moving documentation or command input. Hover/docs are
    recomputed for the new row under the stored pointer.
13. Resize retains the listener 003 logical-row anchor and recomputes pointer
    hits against new intervals rather than cached coordinates.
14. `main()` composes the production listener and non-inline app run exactly
    once and suppresses only an outer `KeyboardInterrupt`; use monkeypatching so
    this test opens no terminal and reads/signals no live process.
15. Every passive listener 003 test and all predecessor tests remain unchanged
    and green.

Textual API details may require direct message posting for paste or low-level
mouse cases. Keep such tests targeted to this application's handlers; do not
introduce a snapshot framework or make tests depend on terminal color support.

## Automated verification

Run the complete suite:

```console
uv sync
uv run pytest
```

The suite still includes listener 002's one reviewed production-SIGTERM test,
which signals and reaps only its own child. No additional automated test may
signal a live process or unlink outside `tmp_path`.

## Guarded live hand check

Perform this only after all automated tests pass and only in a real interactive
terminal. Create a fresh temporary directory **under the project root** so uv
can discover the project. Populate it with:

- one subdirectory;
- two disposable files, one named exactly `file with space`; and
- enough additional disposable entries to wrap at a narrow terminal width.

In the shell, `cd` into that fresh directory before running `uv run pbui` and
record the exact absolute output of `pwd`. The first prompt must show that same
absolute directory. If it does not, exit immediately and do not perform the
destructive portion.

Then, without changing pbui's cwd:

1. Run `ls` several times so older rows exist for scrolling.
2. Hover a file and directory; verify reverse hover and the exact documentation
   wording. Click `file with space` with no command and verify `show` reports its
   absolute path, file type, size, and UTC mtime.
3. Compare the prompt to the recorded temporary-directory path again.
   **`rm` is forbidden unless they still match exactly.** Type `rm`, Enter, and
   verify files are bright-green/bold/underlined targets while directories are
   gray/dim/inert. Click only the designated disposable file and verify only it
   is unlinked. Repeat `rm`, click the subdirectory, and verify nothing is
   removed and input still waits.
4. Press Ctrl-G and verify the wait/input clear. Enter another wait and verify
   Escape performs the same cancellation.
5. Scroll to an older listing, resize until rows rewrap, then click an older
   retained name. Verify `show` receives that object's original absolute path,
   not characters at stale coordinates.
6. Run `ps`, identify pbui's own pid by command text containing `pbui`, and
   click it to see current process detail. Do **not** run `kill` against any
   process during this hand check.
7. Exit with Ctrl-D and verify the ordinary shell screen, cursor, input, and
   mouse behavior are restored. Start once more from the same disposable
   directory, exit with Ctrl-C, and verify the same restoration with no
   traceback.

Remove the disposable directory after exiting and confirming the shell is
restored. This is the only required exercise against the unrestricted live
filesystem and live process table. Never substitute a real user directory for
the disposable tree, never click an `rm` target outside it, and never use live
`kill` in the hand check.

## Completion

Listener 004 is complete only when:

- `uv run pytest` passes the entire suite;
- `uv run pbui` and `uv run python -m pbui` share the exact entry function;
- the guarded hand check passes in a real terminal;
- normal exit, Ctrl-D, Ctrl-C, and an outer `KeyboardInterrupt` restore the
  terminal without a traceback;
- only the allowed files changed and no dependency was added; and
- history remains object-bearing through draw, hover, scroll, resize, accept,
  click, and command execution.

Report the automated result, entry-point verification, live hand-check result,
and changed files. Then stop: the accepted listener specification is complete,
and any follow-on work requires a new exploration rather than listener 005.
