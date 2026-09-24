# tutorial 000 — cards and links

**Status.** Implemented.

## Goal

Add the six immutable local cards, their headless history presentations, `:tutorial`, and headless navigation and Try behavior. The slice is complete when the listener can append and select those presentations without importing Textual.

Stop after the headless behavior and automated verification. Terminal styling, pointer coordinates, popup click routing, documentation text, screen tests, and the live hand check belong to tutorial 001.

## Authority and starting point

The implementer receives this checkpoint and the accepted [`../spec.md`](../spec.md); the checkpoint narrows the spec to one slice and does not revise it.

- Identity: **tutorial 000**. This is the first checkpoint; there is no tutorial predecessor. Tutorial 001 follows in a separate conversation.
- Governing spec sections: 1–6 and the tutorial 000 tests in section 8. Section 2 preserves existing listener behavior outside tutorial controls.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Code and tests live there, not in this design folder.
- The listener, transcript, chips, popup, and Python evaluator already exist. HTTP is separate and requires no work here.

## File scope

May create `src/pbui/tutorial.py` and `tests/test_tutorial.py`. May edit `src/pbui/domain.py` for tutorial presentation types and drawer registration, and `src/pbui/commands.py` for the command and headless selection and editor operations. May edit only the exact registry and command-name expectations affected by these additions in `tests/test_domain.py` and `tests/test_commands.py`.

Leave `src/pbui/terminal.py`, `src/pbui/substrate.py`, `src/pbui/text.py`, `src/pbui/transcript.py`, `src/pbui/chips.py`, other tests, project metadata, and dependency files untouched. Only `pbui.terminal` may import Textual. If implementation requires another file, stop and return this checkpoint to the checkpoint manager instead of widening the slice.

## Slice requirements

### Card data and stack

- Define immutable card, example, and link data in `tutorial.py`. Store the exact five tour cards and the contents card from spec section 4, including their titles, body lines, examples, identifiers, order, and next, previous, and contents targets. Contents entries reference the same stored tour card objects. Reopening a card creates a fresh presentation of that object, not a copied card.
- Represent the Python example as the saved pieces for one editable line `1 + 2 + 3`, and the command example as the saved pieces for `:ls`, using the existing `PythonInput` and `CommandInput` shapes. These are example data, not submitted transcript rows.
- Constructing the stack performs no command, filesystem, process, or network operation. It stores no rendered fragment, HTML, Textual widget, editor state, or callback.

### Headless presentations and history

- Register presentation types for an outer card, nested card targets, and nested Try examples. Build the rows with the existing `DrawingContext`, `HistoryRow`, and fragment model so all rows of one appended card share one outer presentation. Nested controls must retain their destination or example, while a disabled Back or Next retains its direction and no destination. A fresh append makes fresh presentations and keeps the stored card identity.
- Emit title, body, example, and navigation rows in the spec section 5 order. Preserve the exact bracketed labels, example source text, and contents entries. Keep each card to at most 20 logical rows. Escape display text with existing rules and wrap long body text at 120 display cells. When content exceeds the cap, retain the complete card data and mark the cut with `… (card text cut)` while leaving title and controls visible.
- Use the existing 500-row history retention. Appending or revisiting a card leaves older retained rows in place, subject only to ordinary history eviction. No screen styling or Textual widget is part of this slice.

### Command and selection

- Register `tutorial` as a no-argument colon command. `:tutorial` records the ordinary `CommandInput` row, then appends the first card. Repeating it records another command row and appends a distinct presentation of the same stored card. An argument follows the listener's no-argument error behavior and appends no card. Drawing a card never runs its example.
- Route a first left selection of an enabled Next, Back, Up, or contents target through the headless listener so it appends only the destination card. The editor line, cursor, pending Python pieces, pending accept or substring accept, and transcript counts stay intact. This navigation has priority over chip insertion, yank, and modal accept. Disabled boundary targets append nothing. The outer card has no default append action.
- Route a Try selection as an editor load only when the ordinary prompt is empty and there is no continuation, presentation accept, substring accept, or menu. Load the saved Python or command pieces into the existing editor and leave the cursor at the end. It appends no history row and performs no evaluation or listing. A nonempty line or chip, continuation, accept, or substring accept refuses Try without changing the editor or history. Share the existing saved-input loading behavior without creating a fake transcript presentation. Open-popup priority and refusal are completed in tutorial 001's terminal layer.
- Preserve selection of ordinary history values and submitted input rows. During Python composition, clicking a value still follows the chip rule; clicking a prior input row still follows yank. Card and control objects are not acceptable file, directory, or process targets.

## Verification and completion

Add focused headless tests in `tests/test_tutorial.py` for the exact stack, stored object identities, no side effects when constructing it, and the required outcomes in spec section 8: repeated `:tutorial`, preserved older history, navigation in both directions and through contents, disabled boundaries, no transcript or editor change on navigation, Try's exact pieces and later editable state, and refusal while busy. Include composition and pending accept preservation of line, cursor, and pending request. Verify the 20-row cut marker with a long synthetic card and prove its stored text remains complete. Use injected services and a disposable root; tests must not start Textual or use a network transport.

From the project root, run:

```sh
uv sync
uv run pytest
```

If `uv` is unavailable, stop and report that. Completion requires the focused tests and existing suite to pass, with no terminal or dependency edit. Report test results and changed files, then stop without starting tutorial 001.
