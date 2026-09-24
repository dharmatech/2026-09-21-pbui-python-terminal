# bottom 003 — remove no-target wording

Ready to implement.

## Goal

Apply the later accepted spec wording for the remaining unnamed documentation cases: an unrecognized ordinary presentation says `UNKNOWN`, and continuation and popup-border instructions begin directly with their action text. `READY` from bottom 002 remains the ordinary empty-pointer sentence. **Stop after this wording correction; do not add a new interaction or start another checkpoint.**

## Authority

The implementer receives this checkpoint and the accepted spec; the checkpoint narrows the spec to one slice and does not revise it.

- Series identity: **bottom**. This is checkpoint **bottom 003**, added for the later wording correction.
- Governing spec: [`../spec.md`](../spec.md), §§4, 5.2, 5.3, and 6. Its latest exact sentences supersede the historical `NO TARGET` wording recorded in bottom 002; do not edit that completed checkpoint.
- Predecessor: bottom 002 is implemented. Its `READY` behavior and tests are the starting state.
- Project root for code, tests, and commands: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

## File scope

This slice may edit `src/pbui/bottom.py`, `tests/test_bottom.py`, and `tests/test_terminal.py` at the project root. On completion, update only the status line in `docs/design/implementation/bottom/README.md`.

Leave `src/pbui/terminal.py`, all other source and tests, the accepted spec, and earlier checkpoints untouched. The terminal already renders the pure formatter and its popup-border constant. If another file is necessary, stop and send this checkpoint back to the checkpoint manager instead of widening the slice.

## Slice requirements

1. An unrecognized ordinary presentation returns the exact full sentence `UNKNOWN`. Keep the pending-accept refusal for an unrecognized presentation distinct: it still names the escaped presentation type as `OBJECT TYPE` and retains its selection lead, refusal, and cancel clauses. Do not turn ordinary no-hit cells into `UNKNOWN`; they continue to return `READY`.
2. For a Python continuation with no hit, return exactly `Python continuation: enter another line • Esc: discard • Ctrl-G: discard`. The continuation state still outranks the idle-pointer `READY` case.
3. For a popup border or interior cell without an item, return exactly `Click an item • Esc: close menu • Ctrl-G: close menu`. Do not add a target word or change menu routing, item behavior, or the lifetime of popup documentation overrides. A `Ctrl-O` attempt with nothing under the pointer continues to leave the normal `READY` sentence in place.
4. Remove all remaining `NO TARGET` wording from the active documentation formatter and its tests. Keep the pure formatter signatures, one-row fitting, input-row rendering, all named targets, selections, click behavior, and existing style meanings unchanged. Do not make a broad search-and-replace that changes unrelated text.
5. Update headless and Textual assertions for the three changed cases. Prove `READY` for an idle pointer, `UNKNOWN` for an unrecognized ordinary presentation, the instruction-led continuation, the instruction-led menu border, and the unchanged pending-accept refusal for an unrecognized presentation. Update every old exact-wording assertion for these cases; the full suite must still pass.

## Verification and completion

From the project root, run:

```sh
uv sync
uv run pytest tests/test_bottom.py tests/test_terminal.py
uv run pytest
```

Use a Textual screen test to check the rendered continuation and popup-border sentences if the live PTY cannot deliver keystrokes reliably. Confirm a normal empty pointer still renders `READY`. A search of active documentation code and tests should find no remaining `NO TARGET` sentence.

Completion means the three new exact sentences render in their specified states, `READY` and pending-selection behavior remain intact, and the focused and full suites pass. Report changed files and verification results, update the README status line, then stop.
