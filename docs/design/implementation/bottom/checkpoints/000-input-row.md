# bottom 000 — mode and input row

Ready to implement.

## Goal

Make the input row show the current editor mode before its directory prompt, keep that mode visible while the editor scrolls, and draw the specified top rule. This is the first slice of the spec's single layer: the complete documentation sentence conversion is large enough to need its own implementer conversation. **Stop after the input row; do not change documentation wording or start bottom 001.**

## Authority

The implementer receives this checkpoint and the accepted spec; the checkpoint narrows the spec to one slice and does not revise it.

- Series identity: **bottom**. This is checkpoint **bottom 000**.
- Governing spec: [`../spec.md`](../spec.md), §§1–3 and §6 (mode tests, input rendering, and the relevant acceptance conditions). The documentation grammar and sentence list in §§4–5 belong to a later checkpoint.
- Predecessor: none. The existing listener, REPL, listings, chips, transcript, popup, HTTP, and tutorial implementations are the starting state.
- Project root for all code, tests, and commands: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

## File scope

This slice may create `src/pbui/bottom.py` and `tests/test_bottom.py`, and may edit `src/pbui/terminal.py` and `tests/test_terminal.py` at the project root. On completion, update only the status line in `docs/design/implementation/bottom/README.md`. Keep `src/pbui/bottom.py` free of Textual imports. Existing documentation assertions in `tests/test_terminal.py` may change only where the input row layout or continuation prompt makes them obsolete.

Leave all other source, tests, design documents, and checkpoints untouched. In particular, do not change click routing, documentation sentences, menu geometry, retained presentations, tutorial content, or history layout. If another file is necessary, stop and send this checkpoint back to the checkpoint manager instead of widening the slice.

## Slice requirements

1. Add the public pure function `format_mode(listener: HeadlessListener) -> str` in `pbui.bottom`. Derive its result from listener state, with the exact words and precedence in spec §3: pending presentation accept, pending command or menu `narrow` substring accept, Python continuation, colon command including a bare colon with leading spaces, then ordinary Python or empty input. Cover `rm`, `cd`, `kill`, and `show`. An open popup does not change the mode underneath it. Pending accepts outrank a suspended continuation. No widget or live terminal state is used to decide the mode.
2. Render a bold mode word, plain ` │ ` separator, absolute escaped cwd prompt, and existing editable content in that order. Ordinary and colon prompts retain `pbui:/absolute/path> ` after the separator; continuation displays the cwd followed by `...> `. The pending substring editor retains the literal `narrow ` prefix. Cwd changes appear after `cd`. Keep existing chip drawing, editor operations, and focused cursor indication.
3. Put a one-cell full-width thin top rule on the input widget in its ordinary foreground. Keep the documentation content and editor content to one physical row each. Do not add a status widget or accent color.
4. Reserve the left edge for the complete mode word whenever the input content width can fit it. Shorten the directory first with a leading ellipsis that preserves its trailing path, then scroll only the editor area to keep the cursor visible. Omit the separator and prompt only when no cells remain after the mode. At a width smaller than the mode word, crop safely. Drawing shortcuts must not mutate the stored cwd, input text, chips, or cursor position.
5. Update only input row related existing tests. Add focused headless tests for every exact mode word and its precedence, including an empty continuation. Add focused Textual screen tests that check the mode beneath an open popup, the top rule, and that a long editable line cannot scroll the mode word off the left edge; check a wide cwd and a narrow cwd draw. Existing editor and click tests must still pass.

## Verification and completion

From the project root, run:

```sh
uv sync
uv run pytest tests/test_bottom.py tests/test_terminal.py
uv run pytest
```

For a visual check, run `uv run pbui` from the project root. Confirm the empty input shows `PYTHON`, a typed `:rm` shows `COMMAND`, a pending `:rm` shows `SELECT FILE FOR rm`, Escape restores `PYTHON`, and the top rule separates the documentation and input content. Do not select or delete a file during this check. The full documentation line hand check in spec §6 belongs to the later slice.

Completion means the exact mode transitions, prompt shape, top rule, and fixed mode anchor work; the current documentation wording and all click behavior remain intact; and the focused and full suites pass. Report changed files and verification results, then stop without starting bottom 001.
