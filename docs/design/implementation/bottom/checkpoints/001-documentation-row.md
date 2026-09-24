# bottom 001 — documentation row

Ready to implement.

## Goal

Convert the documentation row to the accepted target-first sentences for every current listener, popup, HTTP, and tutorial case. Keep one pure source of wording and fit the result into the existing one-row widget. This completes the documentation part of the spec after bottom 000. **Stop without adding history markers, click behavior, menu changes, or another checkpoint.**

## Authority

The implementer receives this checkpoint and the accepted spec; the checkpoint narrows the spec to one slice and does not revise it.

- Series identity: **bottom**. This is checkpoint **bottom 001**.
- Governing spec: [`../spec.md`](../spec.md), §§1–2 and §§4–6. Section 3's input-row behavior is already implemented and must remain intact.
- Predecessor: bottom 000 is implemented. Its mode words, cwd prompt, top rule, fixed mode anchor, and tests are the starting state.
- Project root for all code, tests, and commands: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

## File scope

This slice may edit `src/pbui/bottom.py`, `src/pbui/terminal.py`, `tests/test_bottom.py`, and `tests/test_terminal.py` at the project root. On completion, update only the status line in `docs/design/implementation/bottom/README.md`. The current tutorial cards do not quote an old documentation sentence, so `src/pbui/tutorial.py` and `tests/test_tutorial.py` stay untouched.

Leave all other source, tests, design documents, and checkpoints untouched. Do not change input-row drawing from bottom 000, click routing, accept types, popup geometry, menu items, HTTP transport, retained objects, tutorial navigation, history layout, or style meanings. If another file is necessary, stop and send this checkpoint back to the checkpoint manager instead of widening the slice.

## Slice requirements

1. Make `pbui.bottom` the pure source of documentation wording. Add the exact public signatures from spec §2: `format_documentation(listener, presentation, logical_column=None, *, menu_open=False) -> str` and `format_menu_item_documentation(listener, label, target) -> str`. They return full, untruncated sentences and import no Textual object. Put the menu-border and popup-failure messages in pure helpers or constants there too. `terminal.py` supplies pointer, logical-column, menu-hover, and transient-override context; it may re-export `format_documentation` for existing callers. Remove old wording branches and constants from the terminal adapter so there is one source of sentences.
2. Implement the grammar, target labels, and precedence in spec §4 and every ordinary-history and Python-insertion sentence in §5.1. Include files, directories, captured processes and truncated command fields, listing headers, saved Python/command/menu-action inputs, SymPy and other values, GET requests and HTTP responses, JSON objects and arrays (including nested members), text, errors, tutorial cards, navigation controls, Try controls, and no target. Use captured labels, status, URLs, counts, and presentation identity; escape displayed names and type names. Never inspect a live filesystem, process, or network service for a label. The right-menu clause reflects the actual existing menu.
3. Implement all pending-accept, substring, continuation, and refusal sentences in spec §5.2. Begin every pending-selection sentence with `SELECTING …`, including tutorial controls. Keep the exact `Esc: cancel` and `Ctrl-G: cancel` clauses, required-type wording, real rejected presentation-type name, and accepted command/type pairs. Ordinary history clicks remain inert during substring accept, and its documentation does not invent a button action. Tutorial controls retain their existing priority and click behavior during either accept.
4. Implement the popup item, border, and transient sentences in spec §5.3. An item uses its saved label and saved target through `format_menu_item_documentation`; a border or empty interior cell has the specified `NO TARGET` sentence. Preserve the popup rectangle's pointer priority, exposed tutorial controls outside it, and the current lifetime of popup-failure overrides. Invisible-target and too-large-menu messages name the target and keep the exact spec wording. No popup placement or routing change is part of this slice.
5. Keep `DocumentationLine` to one nonwrapping content row above the input rule. Its `sentence` remains the full formatter result; rendering applies terminal-cell fitting as spec §6 directs. Compose semantic parts before fitting: shorten an optional target name/title/label first, then omit that detail if needed, while preserving its kind and complete `Left:` and `Right:` clauses whenever they fit. Give cancel/refusal text priority over optional target detail. At smaller widths use display-safe ellipsis or crop without splitting wide characters or exposing control text. Use a pure internal fitting helper in `bottom.py` so headless tests can exercise the width rules; the widget supplies only the content width.
6. Add focused headless tests in `tests/test_bottom.py` that import `pbui.bottom` without importing Textual. Cover the exact §5 sentences across the categories above, all four presentation accepts, unacceptable targets and real type names, command/menu substring accept, tutorial priority, menu item/border and transient messages, continuation/no target, retained HTTP/JSON labels, and display-cell fitting with a long escaped label. Use existing headless fixtures and retained objects, not live network or process inspection. Update every old exact-documentation assertion in `tests/test_terminal.py`; retain interaction assertions and add focused screen coverage for menu hover/overrides, stationary-pointer refresh, selection-led tutorial documentation, and the one-row width behavior. No old documentation sentence may remain as a fallback.

## Verification and completion

From the project root, run:

```sh
uv sync
uv run pytest tests/test_bottom.py tests/test_terminal.py
uv run pytest
```

For the spec §6 hand check, launch the app from a disposable directory using `uv run --project /home/dharmatech/journal/2026-09-21-pbui-python-terminal pbui`. In one session, read `PYTHON` at an empty prompt; point at a file and read its target, `Left`, and `Right`; type `:rm` and read `SELECT FILE FOR rm` plus the selection-led documentation; press Escape and read `PYTHON` again. Do not click the file. If the available PTY cannot deliver keystrokes, report that limit and verify the transitions in a Textual screen test.

Completion means all current documentation cases use the spec's exact sentence shape, the display fitting preserves the action meaning at widths where it fits, bottom 000 still works, and the focused and full suites pass. Report changed files, test results, and hand-check results or its limitation; update the README status line; then stop.
