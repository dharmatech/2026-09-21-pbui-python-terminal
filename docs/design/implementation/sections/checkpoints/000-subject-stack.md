# sections 000 — subject stack and headless navigation

**Status.** Implemented.

## Goal

Store Contents, Listener, and SymPy as an immutable three-role tutorial stack. Keep `:tutorial` opening Presentations directly, and make entries, sibling links, Up, and SymPy Try examples work through retained headless presentations. Prove this behavior without starting Textual.

Stop after the card data, pure history rows needed to retain controls, headless behavior, and automated headless verification. Screen styling, documentation sentences, screen tests, the live hand check, and any new SymPy operation belong outside sections 000.

## Authority and starting point

The implementer receives this checkpoint and the accepted [specification](../spec.md); the checkpoint narrows the spec to one slice and does not revise it.

- Identity: **sections 000**. This is the first checkpoint; there is no sections predecessor. The existing tutorial 001 and SymPy expression work are implemented.
- Governing spec sections: 1–4 for the series, boundaries, exact card data, headless navigation, and Try; section 5 for retained control rows and labels; section 7 for sections 000 tests; section 8 for the acceptance behavior this slice can prove.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Product code and tests live there, never in this design folder.
- `src/pbui/tutorial.py` already owns immutable cards, `TutorialStack`, and the pure row drawer. `src/pbui/commands.py` already starts `:tutorial` from `stack.tour[0]` and routes `TutorialTarget` and `TutorialExample` selections. Keep the existing `TutorialCard`, `TutorialTarget`, and `TutorialTry` presentation types.

## File scope

May edit `src/pbui/tutorial.py` for the stored stack, links, examples, lookup, and pure retained rows. May edit `src/pbui/commands.py` only if the new stack needs a change to the `:tutorial` entry or existing headless card-selection routes. May edit `tests/test_tutorial.py` for focused headless coverage and to update old single-tour hierarchy assumptions.

Leave `src/pbui/terminal.py`, `src/pbui/bottom.py`, `src/pbui/domain.py`, all other source and test files, `pyproject.toml`, and `uv.lock` untouched. In particular, sections 001 owns `tests/test_terminal.py` and the documentation wording. If another file becomes necessary, stop and return this checkpoint to the checkpoint manager instead of widening the slice.

## Slice requirements

### Immutable stack

- Preserve the existing five gesture cards, their identifiers, titles, body lines, Try data, and sibling order from spec section 4.2. Keep an ordered five-card tour available for `:tutorial`, with Presentations first. Preserve `contents` as the Contents identifier and make every card resolvable by stable identifier.
- Add the Listener and SymPy section cards and the four SymPy leaves specified in sections 4.1 and 4.3. Use distinct identifiers for the two sections and four new leaves. Contents has exactly the Listener and SymPy entries, in that order. Listener has exactly the five gesture entries; SymPy has exactly Import, Symbol, Expand, and Factor. A section is a stored `TutorialCard`, not a new screen or command.
- Every non-Contents card has exactly one parent. Every gesture leaf's Up resolves to Listener; every SymPy leaf's Up resolves to SymPy; both sections' Up resolves to Contents. A leaf's Back and Next stay inside its section. First Back and last Next in each section have no destination. Contents and section cards have no Back or Next links; Contents has no Up.
- Keep each link destination as the same stored card object when a control is drawn, while each append creates a fresh outer presentation. Construction is local package data and must not import SymPy, read files, inspect processes, or open a socket.

### Pure rows and headless actions

- Draw retained nested entry and navigation controls from each card's role. Contents has two bracketed entries and no navigation row. Sections have bracketed leaf entries followed by one Up control; no Back or Next controls. Leaves have Back, Next, and Up controls, with disabled boundary controls still retained and bracketed in the pure row text. The `TutorialTarget.label` for Up contains its complete visible label: `Up: Listener`, `Up: SymPy`, or `Up: Contents`, as appropriate. Its destination is the stored parent card. The pure drawer must retain the full card text, keep the existing 20-logical-row cap, and keep inner-control hit priority. Screen appearance and documentation are sections 001.
- `:tutorial` records its ordinary `CommandInput` row and appends Presentations directly; repeating it appends another presentation of the same stored Presentations card. An argument keeps the existing no-argument error and appends no card. Drawing a card or following a link never evaluates an example.
- Selecting an enabled entry, Back, Next, or Up appends only its stored destination. A disabled Back or Next appends nothing. Navigation leaves editor text, pieces, cursor, pending continuation or accept, and transcript counts unchanged; it remains distinct from chip insertion and input-row yank. Preserve existing popup and accept routing.
- Each SymPy Try stores one `PythonInput` line: `import sympy`, `x = sympy.Symbol("x")`, `(x + 1)**2`, or `x**2 - 1`, in that order. Try loads the exact editable line only at an empty ordinary prompt and appends no input or value row until Enter. Existing busy refusals remain unchanged. No new evaluator, printer, translator, or SymPy import belongs in this slice.

## Verification and completion

Update and extend `tests/test_tutorial.py` to prove the exact card text and ordering; stored identities and all parent, entry, Back, and Next destinations; stable lookup for both sections and all nine leaves; pure construction without SymPy import or filesystem, process, or network work; and each Up control's stored destination and complete label. Cover the direct and repeated `:tutorial` path and argument refusal, Up from Presentations through Listener to Contents, a SymPy leaf returning to SymPy, and both section boundaries. Cover Import and Expand Try loads without evaluation. Preserve the existing tests for editor and accept state, 20-row cap, nested hits, chip insertion, and yank, updating their former Contents and Up assumptions.

From the project root, run:

```sh
uv sync
uv run pytest tests/test_tutorial.py
uv run pytest --ignore=tests/test_terminal.py
```

The old screen tests contain assertions for the former Up destination and Contents entries. Sections 001 updates those assertions, adds the new screen coverage, and runs `uv run pytest` as the full automated gate. If `uv` is unavailable, stop and report it; do not use another Python tool. Completion of sections 000 requires the focused and non-screen tests above to pass, with no edit outside this file scope. Report results and changed files, then stop without starting sections 001.
