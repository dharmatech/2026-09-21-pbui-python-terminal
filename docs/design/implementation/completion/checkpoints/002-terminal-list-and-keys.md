# completion 002 — Terminal list and keys

Ready to implement.

## Goal

Connect the completed headless API to Tab in the Textual input row. Add the transient candidate list over visible history, its key and pointer behavior, the keyboard-guide rows, one focused screen test, and the specified hand check.

Stop after this UI slice. Do not add a new screen region, new completion source, command, dependency, or transcript presentation.

## Authority

The implementer receives this checkpoint and the accepted spec; the checkpoint narrows the spec to one slice and does not revise it.

- Series identity: **completion**; this is checkpoint **002**.
- Governing spec sections: §1 (series and order), §2 (product boundary and existing authority), §3 (host, layout, and commands), §4.1 (headless API and edit rules), §7 (this slice), §8 (verification), and §9 (acceptance).
- Predecessor: [completion 001](001-import-targets.md) is implemented. Completion 000 and 001 provide the headless candidate and edit operations; the reported focused tests (13 passed) and full suite (359 passed) are the starting state.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Run commands there. Code and tests belong there, not in this design folder.

## File scope

The implementer may edit `src/pbui/terminal.py`, `docs/user-guide.md`, and `tests/test_terminal.py`. If the screen exposes a genuine headless API gap, a minimal adjustment may also edit only `src/pbui/commands.py`, `src/pbui/completion.py`, or `src/pbui/chips.py`, with its focused coverage in `tests/test_completion.py`. Keep those adjustments within the accepted spec.

Leave other product modules, other tests, the guide's smoke test, and dependency files untouched. If completing this slice needs another file, stop and send this checkpoint back to the checkpoint manager instead of widening the scope.

## Slice requirements

1. In `pbui.terminal.CommandInput.on_key`, consume an initial Tab and call `HeadlessListener.complete(menu_open=screen.action_menu.is_open)`. Zero candidates leave the editor and list unchanged; one applies without opening a list; several open the list after any shared-prefix edit. A pending accept or open action menu keeps priority and remains unchanged by Tab. Tab must no longer perform focus navigation.
2. Keep transient candidate-list state on `ListenerScreen` and its input row, mutually exclusive with the action menu. Paint it over the bottom rows of the visible history rectangle, directly above the unchanged documentation line. It takes no layout height and is not a menu, history presentation, or history hit target. Opening, updating, navigating the list, resizing, and closing it must not change the history scroll offset, anchor, logical rows, presentation intervals, or underlying hit testing. Refresh its former cells when it closes so history reappears. Preserve the input row's mode word, directory, prompt, caret, and chip drawing.
3. Show one alphabetically ordered candidate per row, up to `min(8, visible history height, candidate count)`, bottom aligned. Crop only drawing when the terminal is narrow; retain complete names for insertion. Reverse-style the highlighted row. Highlight the first candidate when the list opens or recomputes. Up and Down move one candidate without wrapping and shift the visible window to keep it in view; Tab advances and wraps to the first when several candidates remain. Short terminals may show fewer rows but never cover documentation or input.
4. While the list is open, Enter applies the highlighted name through `apply_completion`, closes the list, and does not submit. Escape or Ctrl-G closes it first without changing the editor; a later press reaches existing cancellation. Ordinary text input, paste, Backspace, and Delete edit first and then recompute candidates at the new caret. Zero closes the list; one or more leave it open without automatically inserting the sole name. A later Tab applies a sole candidate and closes the list, or advances the highlight when several remain. Caret movement recomputes for the new site and closes the list when that site has no candidates. List keys do not traverse recall or scroll history; Up and Down return to recall after the list closes.
5. Consume the first click anywhere while the list is open, closing it before history selection, chip insertion, yank, menu opening, or input-row action. The next click uses the ordinary behavior. The wheel keeps its history-scroll behavior while the overlay stays pinned to the bottom of visible history. Close stale list state before an external editor load, submit, accept, or menu opening. The list itself never appends a transcript row. Preserve the action menu's existing behavior when no list is open.
6. In the keyboard table of `docs/user-guide.md`, add the exact Tab row and replace the Escape row given in spec §7.3. Ctrl-G has the same list-first behavior in the app. Leave the rest of the guide and its smoke test unchanged. Update the existing terminal test that expects Tab to navigate focus, since Tab now belongs to completion.
7. Add the one focused screen test specified in §8 to `tests/test_terminal.py`. Open a colon list in a viewport tall enough for eight rows and check that exactly eight are visible, the documentation sentence and history scroll offset stay fixed, Up/Down and list-window movement keep the highlight visible, and Enter inserts without submission. Reopen and close with Escape, then confirm Up recalls again. Also check inert Tab during an action menu, first-click dismissal, and that the overlay has no history hit target. Keep the existing terminal and headless tests passing.

## Verification and completion

From the project root, use uv only:

```console
uv sync
uv run pytest tests/test_terminal.py
uv run pytest
```

Then run the spec §8 hand check from a disposable directory under the project root containing two ordinary files. One way to prepare and launch it is:

```console
COMPLETION_CHECK_DIR=$(mktemp -d "$PWD/.completion-002-XXXXXX")
touch "$COMPLETION_CHECK_DIR/alpha" "$COMPLETION_CHECK_DIR/beta"
(cd "$COMPLETION_CHECK_DIR" && uv run pbui)
```

In that session: type `:` and Tab to see commands; submit `:ls`; complete `:so` to `:sort`, add ` name`, and submit to sort the listing without an error; submit `import math`; complete `math.sq` to `math.sqrt`, add `(4)`, and submit to see `2.0`; complete `import pathl` to `import pathlib`, cancel that unsent line with Ctrl-G, then submit `pathlib` and see a name error; complete and submit `from math import sq` to bind `sqrt`; open an action menu and confirm Tab leaves it open. After exiting, remove only the disposable directory created for this check.

If uv is unavailable, stop and report it; do not substitute another environment manager. Completion 002 is complete when the focused and full suites pass, the hand check succeeds, the guide reflects the keys, no forbidden file changed, and all §7 overlay and routing behavior is present. Report the results and changed files, then stop. Do not start another checkpoint.
