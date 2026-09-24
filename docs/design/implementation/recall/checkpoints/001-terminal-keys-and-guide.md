# recall 001 — terminal keys and guide

**Status:** Ready to implement.

## Goal

Connect the implemented headless recall traversal to the terminal's Up and Down keys, keep the visible caret and history viewport correct, document those keys, and verify the screen behavior. Stop after this terminal slice; it adds no further recall command, search, persistence, or history-layout work.

## Authority

The implementer receives this checkpoint and the accepted spec; the checkpoint narrows the spec to one slice and does not revise it.

- Series identity: **recall**. This is **recall 001**, following [`recall 000`](000-headless-recall.md), which the user reports implemented with 9 focused tests and 345 full-suite tests passing.
- Governing spec: sections **1–3**, **5–7**. Section **4.3** supplies the already implemented traversal methods and command-caret contract; do not reopen recall 000's ring or draft model.
- Project root for code, tests, and commands: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.
- The earlier accepted specifications named in spec section 2 continue to govern transcript records, chips, clicks, menus, bottom documentation, and history layout.

## File scope

Edit only `src/pbui/terminal.py`, `tests/test_terminal.py`, and `docs/user-guide.md`. Leave `src/pbui/commands.py`, `tests/test_recall.py`, other production files and tests, `pyproject.toml`, `uv.lock`, and other guide content untouched. If another file is necessary, stop and send this checkpoint back to the checkpoint manager instead of widening the slice.

## Slice requirements

1. In `CommandInput.on_key`, route `up` to `listener.recall_previous` and `down` to `listener.recall_next`. Pass `ListenerScreen.action_menu.is_open` as `menu_open`. Consume both keys even when the ring is empty, traversal is at a boundary, an accept is pending, or the menu is open; they must neither insert text nor scroll history. Do not bind `Ctrl-P`, `Ctrl-N`, `Ctrl-R`, or search.
2. Make `HeadlessListener.command_cursor` the terminal command caret's source of truth, as spec section 4.3 requires. Forward command caret moves and edits from Textual through `set_command_cursor`; keep Python caret behavior through `python_cursor` and `set_python_cursor`. After a successful traversal, read the appropriate listener caret and draw the input row at that position, including restoration of a mid-line unsent draft. Reconcile the editor's cursor setter, edit paths, adoption, and clamping so ordinary typing, paste, Left/Right/Home/End, Backspace/Delete, Enter, yank, and Try keep their existing behavior. A refused or boundary traversal must preserve the current caret.
3. Keep the input row focused with its mode word, directory, chips, and one-row continuation prompt. Synchronize successful traversal without `reveal_newest` and without seeking the recalled presentation's old transcript row. Preserve the current viewport after both successful and inert traversal. Ordinary Enter keeps its existing reveal behavior. The mouse wheel still scrolls only the history surface; the input row remains pinned. Leave bottom documentation sentences, click routes, menus, and history drawing unchanged.
4. Add exactly these two rows to the keyboard table in `docs/user-guide.md`, with no other guide change and no new smoke-test step:

   | Key | Action |
   |---|---|
   | Up | Recall the next older submission from this session. |
   | Down | Move toward newer submissions, then restore unsent input. |

5. Add one Textual screen test in `tests/test_terminal.py`. Create enough history rows to scroll; submit a colon command and a Python form; type an unsent line; press Up, Up, Down, Down. Read the input row after each key, verify the draft and caret return, and verify the history viewport does not jump to an old input row. Send a mouse-wheel event and verify the history scrolls while the input row stays pinned; Up and Down must not take that scroll path. Open an action menu and verify both arrows leave the menu and input unchanged. Existing headless tests cover the other modal cases.

## Verification and completion

From the project root, run:

```console
uv sync
uv run pytest tests/test_terminal.py
uv run pytest
```

If `uv` is unavailable, stop and report it. For the required hand check, create a disposable directory **under the project root** with a disposable file, enter that directory, and run `uv run pbui`. In one session:

1. Submit `:ls` and a short Python expression.
2. Type `for n in range(2):` and press Enter. On the second line type `    n` and leave the caret before `n`. Press Up, Up, Down, Down. The continuation and caret must return. Cancel the unfinished continuation with `Ctrl-G`.
3. **The next action deletes the disposable file.** Submit `:rm` and click that file in the listing. Up must recall the command with the same file object; another Up must reach the original Python expression. Edit the expression and press Enter. The edited form becomes the newest entry, and traversal still reaches the original.
4. Open a menu and press Up; it remains open and the input stays unchanged. Check that the mouse wheel still scrolls history. Exit pbui and clean up the disposable directory.

Recall 001 is complete when the new screen test and full suite pass, the hand check succeeds, the two guide rows are present, and existing documentation, click, menu, wheel, and viewport behavior is preserved. Report changed files and verification results, then stop. Do not start another checkpoint.
