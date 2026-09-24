# history 001 — gap and indent

**Status:** Ready to implement.

## Goal

Draw one blank physical row between adjacent retained operation groups and place every grouped result row two display columns right of transcript input. Keep clicks, hover, content columns, and listing viewport anchors aligned with the new geometry. Stop after the layout, screen test, and hand check in this slice; add no further history feature.

## Authority

The implementer receives this checkpoint and the accepted spec; the checkpoint narrows the spec to one slice and does not revise it.

- Series identity: **history**. This is **history 001**; **history 000** is the predecessor. Its implementer reported `uv sync` success and `uv run pytest` passing 332 tests, and its group ids and `row_indents` predicate are present in the project.
- Governing spec: sections **1–3**, **4.1** for the predicates and group meaning, **5.1–5.5** for this slice, **6** for verification, and **7** for acceptance.
- Project root for code, tests, and commands: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

## File scope

This slice may edit `src/pbui/text.py` for pure layout and an optional stored-text reader, and `src/pbui/terminal.py` for rendering, pointer columns, and viewport anchoring. It may edit these test files for the new geometry: `tests/test_history.py`, `tests/test_terminal.py`, `tests/test_commands.py`, `tests/test_repl.py`, `tests/test_sympy.py`, `tests/test_chips.py`, `tests/test_tutorial.py`, and `tests/test_http.py`.

Leave `src/pbui/substrate.py`, `src/pbui/commands.py`, `src/pbui/repl.py`, `src/pbui/bottom.py`, the stored drawers, all other tests, documentation sentences, `pyproject.toml`, and `uv.lock` untouched. Do not change group allocation, stored fragments, presentation values, command effects, the `› ` marker, or the process-command content-column window. If another file is necessary, stop and send this checkpoint back to the checkpoint manager instead of widening the slice.

## Slice requirements

1. In `layout`, walk stored rows in order and emit one separator before a grouped row only when the preceding stored row has a different non-`None` group id. The first stored row gets none; an ungrouped row breaks the comparison. A separator has text `""`, display width 0, `logical_row is None`, and no presentation interval or hit. It is never stored or counted toward retention. After eviction, derive separators from the surviving stored rows.
2. Change `RenderedRow.logical_row` to `int | None`; only a separator uses `None`. Guard every reader that indexes stored history from a rendered row. Keep `HistorySurface` drawing one Rich `Text` for each physical row; the separator gets an empty `Text`.
3. Use history 000's `row_indents` predicate. At width 3 or more, prepend two ASCII spaces to every physical row from a grouped non-input logical row, including wrapped continuations and stored empty lines. No presentation interval covers either indent cell. Content wraps in the remaining viewport columns by display width, including wide and combining characters. If a width-2 character cannot fit on a fresh indented row of width 3, place it after the prefix instead of wrapping forever. At widths 1–2, lay the row out flush. Transcript input and ungrouped rows stay at column 0. Do not add the prefix to fragments or reduce the existing content caps.
4. Move hit intervals with the visible content. Indent cells and separators miss; inner presentations still win. `pointer_logical_column` returns `None` for those cells and otherwise counts only content cells, including earlier wrapped physical rows of the same stored row. Preserve the bottom documentation wording and its process-command window at content columns 42–89. Update the inverse test helper `_offset_for_logical_column` in `tests/test_terminal.py` to map those same content columns. Hover may rebuild only physical rows belonging to the presentations left and entered, never the separator row.
5. Preserve listing viewport anchoring through redisplay and resize. The separator before a listing is outside its block. If the top physical row is a separator, anchor to the next stored row at wrapped offset 0; restoring that anchor places the stored row at the viewport top. Update `HistorySurface` anchoring and the `_top_logical_row` test helper to handle `logical_row is None` without indexing history by `None`.
6. Update content-only predecessor test helpers to read stored logical text rather than laid-out physical text: `history_text` in `tests/test_commands.py`, `drawings` in `tests/test_repl.py`, `tests/test_sympy.py`, and `tests/test_chips.py`. Do the same for content assertions in the scoped HTTP and history tests when needed. Update picture and hit assertions in the scoped tests to the new physical geometry, including tutorial card hits, the HTTP width-17 hit loop, direct listing hits, process-row styling, and wrapped command documentation. Preserve assertions about stored objects, commands, yank, and click results. Ungrouped substrate and domain layouts remain flush.
7. Add the headless layout cases in spec section 5.4 to `tests/test_history.py`: the tutorial/Try/Python/Next/ls/Next sequence at a wide width; one separator between groups and none within a submission; a width-17 wrapped result; width-2 fallback; ungrouped rows; eviction; and the difference between a stored empty `print()` row and a separator. Add the wide-terminal screen test in section 5.5 to `tests/test_terminal.py`, using a disposable directory with one ordinary file. Drive Try, Enter, Next, Try, Enter, Next; verify the picture, file and Try clicks, and misses on indent and gap cells. Assert a hover on an indented presentation does not rebuild the separator's physical row.

## Verification and completion

From the project root, use only uv for Python setup and execution:

```console
uv sync
uv run pytest
```

Run the spec section 5.5 hand check with a disposable directory containing one ordinary file. Launch from the project root with:

```console
uv run pbui
```

Set the listener's directory to the disposable directory with `:cd` before the tour. Then run `:tutorial`, click Try for `1 + 2 + 3`, press Enter, click Next, click Try for `:ls`, press Enter, and click Next. Inspect the gaps and indent; click a file name, Try, and the value. Confirm file and value details appear in new indented groups, and Try loads the example into the editor. The setup `:cd` may appear as an earlier group; the tour assertions concern the sequence starting at `:tutorial`.

History 001 is complete when the full suite passes, the section 5.4 and 5.5 tests exist, and the hand check has been run. Report changed files, the automated result, and the hand-check result, then stop. Do not start another checkpoint.
