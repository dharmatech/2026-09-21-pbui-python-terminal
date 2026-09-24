# tutorial 001 — screen

**Status.** Implemented.

## Goal

Make the retained tutorial cards usable in the Textual listener: draw and hit their nested controls, route clicks through the existing headless operations, and show the exact documentation for each control. Verify the complete local tour on screen.

Stop after the screen tests and one live hand check. This slice adds no card, command, editor feature, menu item, web activity, or fetched content.

## Authority and starting point

The implementer receives this checkpoint and the accepted [`../spec.md`](../spec.md); the checkpoint narrows the spec to one slice and does not revise it.

- Identity: **tutorial 001**. The predecessor, tutorial 000, is implemented; its implementer reported `uv sync` and `uv run pytest` passing 301 tests. This checkpoint does not reimplement its data or headless operations.
- Governing spec sections: 1–3, 5–8. Section 4 supplies the exact card text and labels already stored by tutorial 000. The tutorial spec governs card controls where existing popup, transcript, or chips behavior differs.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Code and tests live there, not in this design folder.
- The existing `TutorialCard`, `TutorialTarget`, and `TutorialExample` values and `tutorial_card`, `tutorial_target`, and `tutorial_try` presentation types are in place. `HeadlessListener.select_for_input`, `open_tutorial_target`, and `load_tutorial_example` supply the headless actions.

## File scope

May edit `src/pbui/terminal.py` and `tests/test_terminal.py` only. Use the existing retained rows and presentation identities from tutorial 000. Leave `src/pbui/tutorial.py`, `src/pbui/domain.py`, `src/pbui/commands.py`, other source and test files, project metadata, and dependency files untouched. If another file is necessary, stop and return this checkpoint to the checkpoint manager instead of widening the slice. Keep `pbui.terminal` the only package module importing Textual.

## Slice requirements

### Drawing and hits

- Recognize the three tutorial presentation types by this listener's exact registered types. Show a multi-row card in the ordinary scrollable history, with each visible row belonging to its shared outer card and each bracketed control belonging to its nested presentation. The innermost target wins. Title, body, example source outside `[Try]`, cut marker, and spaces between controls hit the outer card.
- Give enabled navigation controls, contents entries, and Try a visible control style; dim first-card Back and last-card Next. Preserve ordinary outer-card hover, card text, 500-row eviction, viewport anchoring, physical wrapping, and hit intervals after scrolling and resizing. Disabled controls remain hit targets but append nothing.
- Card controls have no action menu: right button opens none, and `Ctrl-O` finds none. A bare outer card also has no tutorial menu or default append action. Other values and submitted input rows retain their menus and styles.

### Click routing and popup priority

- A first left click on an exposed enabled Next, Back, Up: Contents, or contents entry appends only a fresh presentation of its stored destination and reveals the new history. It does not submit or change editor text, pieces, cursor, pending accept, or transcript. It works while composing Python, editing a colon command, and during presentation or substring accept. A disabled control is inert. Clicking outer card text follows the existing card behavior from spec section 6.
- A first left click on `[Try]` at an empty ordinary prompt loads the exact saved Python line or `:ls` command into the editor, with cursor at the end. It appends no history and runs nothing until Enter. The editor must visibly adopt the listener's new cursor. Try refuses a nonempty line or chip, continuation, pending accept, substring accept, or open popup without changing input or history.
- An open popup owns clicks inside its rectangle. A first left click on an exposed navigation control outside that rectangle closes the popup and appends the destination in the same click. Other outside clicks keep the popup dismissal rule and do not pass through; an exposed Try click while the popup is open does not load. Preserve the existing outside-movement behavior for other targets. When an exposed tutorial control is hovered outside the popup, keep the popup open long enough to show that control's documentation and apply the one-click rule. Click chains and non-left buttons do not activate controls.
- Ordinary value clicks during Python composition still insert chips at valid sites; submitted Python and command input rows still yank. Tutorial control clicks never become a chip, yank, or accept target.

### Documentation line

- Show the exact seven tutorial sentences in spec section 7 for enabled links, Up, disabled Back and Next, ready and busy Try, and the outer card at an empty prompt. Substitute the destination card title in the enabled-link sentence. Preserve the one-row position, safe truncation, and recomputation after pointer, editor, menu, accept, history, scroll, and viewport changes.
- Navigation controls keep their navigation sentences during presentation or substring accept. Try uses the busy sentence for a nonempty line or chip, continuation, either accept, or open popup. Inside a popup rectangle, item or border documentation wins; over an exposed card control outside it, the card-control sentence wins. Outer-card text during Python composition uses the existing chip-site wording with `Right: no menu`; during presentation accept it uses the existing typed refusal. Other pointer targets retain their current documentation.

## Verification and completion

Add focused screen tests in `tests/test_terminal.py` for shared outer and nested hits across card rows, source text versus `[Try]`, wrapping and scrolling, dimmed boundaries, enabled and disabled clicks, and exact documentation in ready, busy, and modal states. Cover Try refusal for nonempty input, continuation, accept, and popup; exposed navigation on the first click during accept and popup; menu ownership inside its rectangle; and preserved value-chip insertion and input yank. Use injected services and disposable roots. No screen test performs a network request.

From the project root, run:

```sh
uv sync
uv run pytest
```

For the live hand check, make a disposable directory under the project root, change into it, and run `uv run pbui`. Enter `:tutorial`, read the first card, click Try, confirm `1 + 2 + 3` is editable and no result has appeared, then press Enter and see 6. Click Next, Up: Contents, and one contents entry; each click should append a card without removing its predecessor. The hand check uses no destructive command.

If `uv` is unavailable, stop and report that. Completion requires the automated suite, the hand check, and the accepted spec's screen behavior to pass. Report results and changed files, then stop without starting another number.
