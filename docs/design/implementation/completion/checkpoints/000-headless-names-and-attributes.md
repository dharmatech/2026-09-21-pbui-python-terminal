# completion 000 — Headless names and attributes

Ready to implement.

## Goal

Add headless Tab-completion operations for colon commands, bare Python names, and attributes of live namespace objects or chips. Tests exercise the editor and candidate results without Textual.

Stop after this headless slice. Do not add import-target completion, bind Tab, draw a candidate list, or edit the keyboard guide.

## Authority

The implementer receives this checkpoint and the accepted spec; the checkpoint narrows the spec to one slice and does not revise it.

- Series identity: **completion**; this is checkpoint **000**, the first in the series. There is no predecessor checkpoint.
- Governing spec sections: §1 (series and order), §2 (product boundary and existing authority), §3 (host, layout, and commands), §4 (shared headless contract), §5 (this slice), §8 (verification), and §9 (acceptance).
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Run commands there. Code and tests belong there, not in this design folder.

## File scope

The implementer may edit `src/pbui/commands.py`, add `src/pbui/completion.py`, edit `src/pbui/chips.py` if atom-preserving text-span replacement needs it, and add `tests/test_completion.py`.

Leave `src/pbui/terminal.py`, `src/pbui/repl.py`, other product modules, existing tests, `docs/user-guide.md`, and dependency files untouched. If completing this slice needs another file, stop and send this checkpoint back to the checkpoint manager instead of widening the scope.

## Slice requirements

1. Add the three `HeadlessListener` operations from spec §4.1: `completion_candidates(*, menu_open=False)`, `complete(*, menu_open=False)`, and `apply_completion(name, *, menu_open=False)`. Candidate tuples are distinct, case-sensitive, alphabetically sorted names. `complete` returns the candidates computed before its edit; `apply_completion` recomputes and accepts only a current candidate.
2. Apply the spec §4.1 edit rules: no candidate leaves input unchanged; one candidate replaces the identifier; several candidates insert only a longer shared prefix. Replace the whole identifier at a mid-token caret while preserving everything outside it. Put the caret after the inserted name. Preserve every PythonChip by identity and keep recall, pending accepts, history, and viewport state unchanged.
3. Detect sites as specified in §4.2. Scan pending Python lines and the current editable line with chips as opaque atoms; map a replacement back to the current line. Never complete inside a string or comment, including incomplete or multiline strings, or at an unrelated statement. A blank Python prompt and unsupported syntax have no site. Reserve `import ...` and `from ... import ...` for completion 001: they return no candidates here.
4. For colon command sites, use the listener's existing command registry under the exact grammar in §5.1. A bare colon offers sorted command names, `:so` completes to `:sort`, and the command's argument position has no site. Do not prepare an accept or dispatch a command.
5. For bare Python identifiers, combine evaluator namespace names, builtins, and keywords. Namespace bindings hide builtins of the same spelling when used as dotted roots. Do not add command names to this source. For eligible dotted chains, use the bound root object or PythonChip value, resolve only preceding plain attributes with `getattr`, and list final names with `dir`, as in §5.2. Do not call a receiver, evaluate a subscript, or read a candidate attribute. A failing lookup or ineligible receiver yields no candidates, with no bare-name fallback after the dot.
6. Apply the final-component underscore filter from §5.2. During a presentation accept, substring accept, or `menu_open=True`, all three operations are inert and no list is offered.
7. Add focused headless tests in `tests/test_completion.py` for every case named in §5.3: registry order and command edit, command arguments, namespace and keyword names, shadowing, a bound module attribute, chip identity, underscore filtering, invalid and failing dotted roots, string and comment refusal, mid-token and shared-prefix edits, recall and history stability, and both accept guards plus the menu guard. Include import-statement refusal so the later layer has a clear boundary.

## Verification and completion

From the project root, use uv only:

```console
uv sync
uv run pytest tests/test_completion.py
uv run pytest
```

If uv is unavailable, stop and report that; do not use another environment manager. The checkpoint is complete when the headless API and focused tests meet §§4–5, the full test suite passes, no forbidden file changed, and Tab remains unbound. Report the test result and changed files, then stop without starting completion 001.
