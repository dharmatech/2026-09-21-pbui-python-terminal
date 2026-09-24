# recall 000 — headless recall

**Status:** Ready to implement.

## Goal

Give `HeadlessListener` a bounded, process-local ring of submitted Python and colon-command input, plus previous/next traversal that restores the complete unsent draft. Prove the behavior without Textual. Stop with Up and Down unbound in the terminal; recall 001 owns the keys, screen test, guide, and hand check.

## Authority

The implementer receives this checkpoint and the accepted spec; the checkpoint narrows the spec to one slice and does not revise it.

- Series identity: **recall**. This is **recall 000**, the first number; there is no predecessor checkpoint.
- Governing spec: sections **1–4**, especially **4.1–4.4**, plus the recall 000 gate in section **6** and acceptance in section **7**. Section 5 belongs to recall 001.
- Project root for code, tests, and commands: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.
- Earlier accepted specifications govern saved input, chip identity, editor pieces, command accept, and screen history as assigned in spec section 2. Where recall and an earlier spec disagree about Up or Down, the recall spec wins.

## File scope

Edit only `src/pbui/commands.py` and create `tests/test_recall.py`. Use the existing types in `src/pbui/transcript.py`, `src/pbui/chips.py`, and `src/pbui/substrate.py` without editing those files.

Leave `src/pbui/terminal.py`, other production files, existing tests, `docs/user-guide.md`, `pyproject.toml`, and `uv.lock` untouched. This slice does not bind keys or change screen drawing, clicks, menus, documentation sentences, transcript retention, or viewport behavior. If another file is necessary, stop and send this checkpoint back to the checkpoint manager rather than widening the slice.

## Slice requirements

1. At each successful `_record_python` or `_record_command` transcript append, add the committed `PythonInput` or `CommandInput` value once at the newest end of a 400-entry ring. Keep the record's original lines, tail, chips, labels, and referenced objects. Do not store a `Presentation`, rebuild text from the displayed row, or add `MenuActionInput`. Preserve duplicate submissions as separate entries. Evict only the oldest ring entry on overflow, independently of the 500-row screen history. Expose read-only headless views of entry order and traversal position.
2. Start traversal at **draft**. `recall_previous(*, menu_open: bool = False)` moves from draft to the newest entry, stashing an independent copy of all unsent editor state: pending Python lines, editable `PythonLine` pieces and cursor, command text, optional command chip and loaded state, and command caret. Preserve chip objects by identity. Further Up moves older; `recall_next(*, menu_open: bool = False)` moves newer. Down from the newest entry restores every stashed field, clears the stash, and returns to draft. Empty-ring, oldest-Up, and draft-Down boundaries change nothing. Both methods return whether editor and position changed.
3. Show each saved entry by replacing the whole editor with the same state and end cursor that empty-editor yank would produce. Restore multiline Python lines as pending lines plus an editable last line; restore command `:` plus its exact tail and optional chip. Clear incompatible editor pieces or command chip. Traversal does not submit, compile, dispatch, accept, ring a bell, scroll history, or alter documentation. Editing a displayed entry changes only the live editor; the next traversal discards that edit. A submission that appends a new input record creates a new newest entry and resets to draft, leaving its source unchanged. An incomplete Python continuation leaves position and ring unchanged until completion or further traversal. A command waiting for accept resets position only when its delayed `CommandInput` is appended.
4. A successful yank or Try, including insertion during Python composition, resets traversal to draft and drops the stash; the resulting editor is the new draft. Apply this to other explicit existing saved-input loads. A refused yank or Try leaves position and stash unchanged. Internal menu suspend-and-restore is not an explicit load. Preserve current yank behavior, including cursor insertion during Python composition and command-composition refusal.
5. Before either traversal, check `pending_request`, `pending_substring_listing`, and `menu_open`; if any is active, leave editor, caret, ring, position, and stash unchanged and return false. Escape and `Ctrl-G` retain their existing behavior. A Python continuation is ordinary stashed draft state.
6. Add a read-only `command_cursor` and a bounded `set_command_cursor(position)` on `HeadlessListener`. `set_input_text` resets this caret to the end of replaced text; a later explicit move can place it elsewhere. A recalled command starts with its caret at the end. Keep the existing Python caret and its setter. The terminal's forwarding of command caret edits and movements happens in recall 001; make the headless state and draft restoration testable now.
7. In `tests/test_recall.py`, use injected services and temporary roots. Prove mixed `:ls`, Python, and `:tutorial` order; duplicate values; exact chip object identity for both input types; multiline pending lines; partial drafts and mid-line Python and command caret restoration; edit discard and edited resubmission; incomplete continuation; absence of menu-action and show-click entries; inert arrows during presentation accept, substring accept, and `menu_open=True`; empty and boundary traversal; and recall after the transcript row is evicted. Append 401 submissions and show that the first alone falls out while the last 400 retain order. These tests must not import Textual.

## Verification and completion

From the project root, use only uv for setup and Python execution:

```console
uv sync
uv run pytest tests/test_recall.py
uv run pytest
```

If `uv` is unavailable, stop and report that. Recall 000 is complete when the focused headless tests and full suite pass and no terminal or guide change is needed. Report the changed files and verification results, then stop. Do not start recall 001.
