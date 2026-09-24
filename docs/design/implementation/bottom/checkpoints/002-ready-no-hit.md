# bottom 002 — ready when no target

Ready to implement.

## Goal

Apply the accepted spec's small documentation wording update: show `READY` for an ordinary empty or literal-history cell with no pointer target. Keep the cases that still require `NO TARGET` and all existing actions unchanged. **Stop after this wording correction; do not start another feature or checkpoint.**

## Authority

The implementer receives this checkpoint and the accepted spec; the checkpoint narrows the spec to one slice and does not revise it.

- Series identity: **bottom**. This is checkpoint **bottom 002**, added after the implemented bottom 000 and bottom 001 checkpoints for the later spec correction.
- Governing spec: [`../spec.md`](../spec.md), §§4, 5.2, 5.3, and 6. The target table, no-target sentence table, and precedence determine where `READY` appears.
- Predecessor: bottom 001 is implemented. Its pure formatter, terminal adapter, and tests are the starting state.
- Project root for code, tests, and commands: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

## File scope

This slice may edit `src/pbui/bottom.py`, `tests/test_bottom.py`, and `tests/test_terminal.py` at the project root. On completion, update only the status line in `docs/design/implementation/bottom/README.md`.

Leave `src/pbui/terminal.py`, all other source and tests, the accepted spec, and other checkpoints untouched. The terminal already renders the pure formatter's result. If another file is necessary, stop and send this checkpoint back to the checkpoint manager instead of widening the slice.

## Slice requirements

1. In the ordinary documentation path with no presentation under the pointer, return the exact full sentence `READY`. This covers an empty history, a literal history cell, and a cleared or absent history hover when no higher-priority menu, selection, or continuation message applies. Keep `format_documentation` pure and its public signature unchanged.
2. Preserve the spec's precedence. A pending presentation accept with no target keeps its `SELECTING …` instruction; a pending substring accept keeps its `SELECTING TEXT FOR narrow …` instruction; a Python continuation with no target keeps `NO TARGET • Python continuation: enter another line • Esc: discard • Ctrl-G: discard`. An unrecognized ordinary presentation still returns `NO TARGET`, and a popup border or empty interior cell still uses `NO TARGET • Click an item • Esc: close menu • Ctrl-G: close menu`. Do not replace `NO TARGET` globally.
3. Update focused headless tests for the ordinary no-hit result and negative cases above. Update existing screen assertions for the initial empty state, literal-history hover, pointer leaving history, and the state after Escape cancels selection. Keep tests that prove the unchanged continuation, menu-border, unknown-presentation, and pending-selection sentences. No click behavior, input-row layout, fitting rule, or menu lifecycle changes belong to this slice.

## Verification and completion

From the project root, run:

```sh
uv sync
uv run pytest tests/test_bottom.py tests/test_terminal.py
uv run pytest
```

Check the rendered documentation line in a Textual screen test at an empty prompt and over a literal history cell: it must read `READY`. Verify that a continuation without a hit still begins `NO TARGET` and a pending `:rm` without a hit still begins `SELECTING FILE FOR rm`. The tests may provide this hand check when the live PTY cannot deliver keystrokes reliably.

Completion means the ordinary no-hit sentence is `READY`, all reserved `NO TARGET` cases remain intact, and the focused and full suites pass. Report changed files and verification results, update the README status line, then stop.
