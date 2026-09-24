# sections 001 — screen and documentation

**Status.** Implemented.

## Goal

Make the subject stack delivered by sections 000 usable and accurately described on the Textual screen. Show and hit each retained entry, Try, and navigation control; update the documentation line for parent-directed Up and section boundaries; prove the complete tour through screen tests and one hand check.

Stop after screen behavior, documentation, verification, and the hand check. Do not add cards, commands, presentation types, SymPy operations, a new printer, or a new Try behavior.

## Authority and starting point

The implementer receives this checkpoint and the accepted [specification](../spec.md); the checkpoint narrows the spec to one slice and does not revise it.

- Identity: **sections 001**. Predecessor **sections 000** is implemented. Its implementer reported `uv sync`, 16 focused tests, and 286 non-screen tests passing. This slice starts from its retained card stack and controls rather than rebuilding them.
- Governing spec sections: 1–3 for series boundaries, host, and commands; section 4 for the stored destinations, exact card text, navigation, and Try rules; sections 5–6 for visible controls and documentation; sections 7–8 for screen verification and final acceptance.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Code and tests belong there, not in this design folder.
- `src/pbui/tutorial.py` already draws pure rows with nested `TutorialTarget` and Try presentations. `src/pbui/terminal.py` is the only package module importing Textual. `src/pbui/bottom.py` formats the documentation line.

## File scope

May edit `src/pbui/bottom.py` for the documentation wording in spec section 6. May edit `src/pbui/terminal.py` only for screen styling, hit handling, click routing, or documentation refresh needed by the new controls. May edit `tests/test_terminal.py` to update assertions that encode the former hierarchy and to add focused screen coverage for this slice.

Leave `src/pbui/tutorial.py`, `src/pbui/commands.py`, `src/pbui/domain.py`, `tests/test_tutorial.py`, all other source and test files, project metadata, dependency files, and the user guide untouched. If a needed change falls outside this scope, stop and return this checkpoint to the checkpoint manager rather than widening it.

## Slice requirements

### Visible rows, styles, and hits

- Present the retained rows from sections 000 in the ordinary scrollable history. Contents shows only `[Listener]` and `[SymPy]`. Listener shows its five bracketed gesture titles; SymPy shows `[1. Import]`, `[2. Symbol]`, `[3. Expand]`, and `[4. Factor]`. Both sections show `[Up: Contents]` after their entries. Sections and Contents show no Back or Next; Contents shows no Up. Every leaf shows `[Back]  [Next]  [Up: Listener]` or `[Back]  [Next]  [Up: SymPy]`. Try rows show `[Try]` followed by a space and their saved source.
- Keep the bracket and label as each control's nested hit area. Spaces, title, body, and source outside `[Try]` hit the outer card. The drawn label must agree with `TutorialTarget.label`. A disabled first Back or last Next in either subject remains bracketed, dimmed, and unclickable. Enabled links and Try remain visibly actionable. Preserve the existing 20-logical-row card cap, full stored text, 500-row history retention, escaping, wrapping at 120 display cells, and hit intervals after scrolling or resizing.
- Card controls have no action menu. A bare card has no default navigation action. Right-click and Ctrl-O retain the existing no-menu behavior on card controls; ordinary history objects keep their existing actions.

### Click routing and documentation

- A first left click on an enabled entry, Back, Next, or Up appends only a fresh presentation of its stored destination. It leaves the source card and editor state in place, including during composition, continuation, presentation accept, and substring accept. Disabled controls append nothing. An exposed navigation control outside an open popup closes it and follows the link on that first click; the popup owns clicks inside its rectangle. Try retains its existing empty-editor load and busy refusal. Card controls never insert a chip, yank an input row, or supply an accept target.
- In `src/pbui/bottom.py`, make the complete ordinary-prompt sentences for Up and disabled boundaries exactly those in spec section 6: `TUTORIAL UP “Listener” • Left: open • Right: no menu`, `TUTORIAL UP “SymPy” • Left: open • Right: no menu`, `TUTORIAL UP “Contents” • Left: open • Right: no menu`, `TUTORIAL BACK • Left: this section has no previous card • Right: no menu`, and `TUTORIAL NEXT • Left: this section has no next card • Right: no menu`. Enabled Back, Next, and Contents entries keep the existing destination-title sentence shape, now naming the new targets. Preserve Try's ready and busy sentences, the outer-card sentence, Right behavior, popup and accept context, cancel suffix, refresh behavior, and narrow-width truncation. Change no unrelated documentation sentence.

## Verification and completion

In `tests/test_terminal.py`, update the old assumptions that a gesture leaf's Up opens Contents or that Contents lists gesture leaves. Add screen coverage for the exact bracketed labels and entries, absence of Back/Next on sections and Contents, disabled boundary styles and clicks, nested hit priority, and the exact section 6 documentation sentences. At least one screen test must click Up from Presentations to Listener to Contents, open SymPy, and verify that a click on Next at Bring input back appends nothing. Also verify that a SymPy leaf's navigation remains in SymPy, that Import's Back and Factor's Next are disabled, and that the new controls remain nested hits after layout. Preserve the existing screen coverage for Try, popup ownership, accept, ordinary chip insertion, and input-row yank.

From the project root, run:

```sh
uv sync
uv run pytest tests/test_terminal.py
uv run pytest
```

For one live hand check, create a disposable directory inside the project root and launch the application from there:

```sh
cd "$(mktemp -d -p /home/dharmatech/journal/2026-09-21-pbui-python-terminal sections-001-XXXXXX)"
uv run pbui
```

In that one session, enter `:tutorial`; click Try on Presentations, press Enter, and see 6. Click Up to Listener and read its five gesture titles; click Up to Contents and read only Listener and SymPy. Open SymPy and Import; Try `import sympy` and press Enter, confirming an input row and no value row. Use Next and Try to enter `x = sympy.Symbol("x")`, again with no value row. Use Next and Try to enter `(x + 1)**2`, then choose `expand` from that expression row's menu and see a new expanded row while the power remains. Use Next and Try to enter `x**2 - 1`, then choose `factor` from that expression row's menu and see a new factored row while the polynomial remains. Next on Factor appends nothing. Up returns to SymPy, then Up to Contents. Exit with Ctrl-C.

If `uv` is unavailable, stop and report it rather than using another Python tool. Completion requires the focused screen tests, full `uv run pytest` suite, and hand check to pass with no file-scope violation. Report results and changed files, then stop without starting another checkpoint.
