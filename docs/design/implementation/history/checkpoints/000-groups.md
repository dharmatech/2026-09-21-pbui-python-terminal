# history 000 — groups

**Status:** Ready to implement.

## Goal

Record which stored history rows belong to one user operation, including rows replaced during value presentation or listing redisplay. Prove the membership and the input-versus-result distinction with headless tests. Stop with the existing flush-left layout: this checkpoint adds no separator, indent, hit-geometry change, or terminal UI change.

## Authority

The implementer receives this checkpoint and the accepted spec; the checkpoint narrows the spec to one slice and does not revise it.

- Series identity: **history**; this is **history 000**, the first number. There is no predecessor checkpoint.
- Governing spec: sections **1–4**, especially **4.1–4.3**, and the history 000 gate in section **6**. Section 5 describes the later layout slice and is outside this checkpoint.
- Project root for code, tests, and commands: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.
- Earlier accepted specifications continue to govern existing recording, commands, listing replacement, and clicks as described in spec section 2.

## File scope

This slice may edit `src/pbui/substrate.py`, `src/pbui/text.py`, `src/pbui/commands.py`, and `src/pbui/repl.py`. It may create `tests/test_history.py` for the focused headless tests.

Leave `src/pbui/terminal.py`, `src/pbui/bottom.py`, stored drawers, other tests, documentation sentences, `pyproject.toml`, and `uv.lock` untouched. Do not change `layout` geometry, `RenderedRow.logical_row`, or hit intervals. If another file is necessary, stop and send this checkpoint back to the checkpoint manager instead of widening the slice.

## Slice requirements

1. Add `HistoryRow.group_id: int | None`, defaulting to `None` and excluded from equality. Add the two predicates in `pbui.text` described in spec section 4.1: transcript input is detected from presentation type names `PythonInput`, `CommandInput`, and `MenuActionInput`; `row_indents` is true exactly for a grouped row that is not transcript input. This checkpoint records that decision but does not draw the indent.
2. Add per-history, monotonically increasing group ids beginning at 1. `PresentationHistory.operation()` opens a group for the outermost context, lets nested contexts join it, and closes it even on an exception. Opening the lower-level group twice or closing one that is not open raises. An operation with no append leaves no stored row. `append` retains and tags the caller's row object while a group is open; an append outside a group preserves the caller's `group_id`. Preserve the retention limit and surviving ids through eviction.
3. Make `replace_row` transfer the old row's group id to the replacement while keeping its current presentation and listing-owner requirements. Make `replace_listing_rows` transfer the retained block's one shared id to every replacement row, reject disagreement among retained block ids with `ValueError`, and preserve the block's position and existing eviction behavior. A concurrently open operation must not retag the replacement block.
4. Open `operation()` at the product entry points in spec section 4.2: `HeadlessListener.submit`, `_finish_chip`, `invoke_python_translator`, `execute_stored_member`, `run_again`, `apply_listing_view`, `open_tutorial_target`, `dig_json`, `_command_show`, and `PythonEvaluator.show_detail`. Cover each whole operation before its first append; nested entry points join the outer group. Keep the helpers listed after that table as append-only helpers with no new group context. Canceled, empty, and unfinished interactions leave stored rows unchanged. Listing view actions append their own new group while the existing table remains at its original position and retains its original group id.
5. Add headless tests in `tests/test_history.py` for the scenarios in spec section 4.3. Include direct substrate cases for nested and exceptional operation exits, row identity, replacement propagation, inconsistent listing ids, and eviction. Exercise the listener with existing filesystem and process fakes; cover Python input and value, tutorial cards, a listing and menu sort or invalid sort, JSON dig and its trailer, click-to-show detail, a one-row `:cd`, no-append paths, an empty printed line, and ungrouped direct append. Assert stored text is unchanged and, at a wide width, `layout` still emits the same flush-left stored rows with a valid logical index for every physical row.

## Verification and completion

From the project root, use only uv for Python setup and execution:

```console
uv sync
uv run pytest
```

If `uv` is unavailable, stop and report that. History 000 is complete when the new section 4.3 headless tests and the full suite pass, group and replacement rules are exercised, and grouped rows still render flush left with no separator. Report the changed files and verification result, then stop. Do not start history 001.
