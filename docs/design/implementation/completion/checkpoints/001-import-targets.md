# completion 001 — Import targets

Ready to implement.

## Goal

Extend the headless completion API to complete `import` and `from ... import` targets at the caret. Discover module names without importing a target or changing the evaluator namespace.

Stop after this headless slice. Do not bind Tab, draw a candidate list, edit the keyboard guide, or start completion 002.

## Authority

The implementer receives this checkpoint and the accepted spec; the checkpoint narrows the spec to one slice and does not revise it.

- Series identity: **completion**; this is checkpoint **001**.
- Governing spec sections: §1 (series and order), §2 (product boundary and existing authority), §3 (host, layout, and commands), §4 (shared headless contract), §5.2 (name filtering and live attributes), §6 (this slice), §8 (verification), and §9 (acceptance).
- Predecessor: [completion 000](000-headless-names-and-attributes.md) is implemented. Its headless API, token scanning, chip-preserving editor, and tests are the starting state; the reported focused tests and full suite passed.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Run commands there. Code and tests belong there, not in this design folder.

## File scope

The implementer may edit only `src/pbui/completion.py`, `src/pbui/commands.py`, and `tests/test_completion.py`.

Leave `src/pbui/chips.py`, `src/pbui/terminal.py`, `src/pbui/repl.py`, other product modules, other tests, `docs/user-guide.md`, and dependency files untouched. If completing this slice needs another file, stop and send this checkpoint back to the checkpoint manager instead of widening the scope.

## Slice requirements

1. Extend the existing `HeadlessListener.completion_candidates`, `complete`, and `apply_completion` path. Keep their signatures and the §4 candidate, replacement, caret, modal-guard, and no-submission rules. Completion changes only the current editable identifier component; pending Python lines provide lexical context but are not edited. Keep the 000 behaviors and tests passing.
2. Recognize the current unsent `import` or `from MODULE import` statement under §6.1, including incomplete input, later comma-separated targets, and a parenthesized `from ... import` continuation in pending Python lines. Locate the component under the caret. A caret immediately after `import ` or `from MODULE import ` is an empty-fragment site. An alias after `as`, a relative import, a string or comment, a later unrelated statement, and an import line containing a chip have no import-name site. Do not complete an earlier component or target.
3. For `import MODULE`, offer top-level modules and packages by combining `pkgutil.iter_modules()` over import paths with `sys.builtin_module_names` and `sys.stdlib_module_names`. For a dotted target, walk only its preceding complete components with `importlib.machinery.PathFinder.find_spec` and explicit parent search paths, then discover the next direct child through `pkgutil.iter_modules` on `submodule_search_locations`. A non-package or failing finder yields no candidates for that path. Do not call `importlib.import_module`, `__import__`, `importlib.util.find_spec` on a dotted name, or another helper that imports a parent merely to discover names.
4. Supply the explicit additional children `os.path` and `collections.abc` in their parent contexts, as required by §6.2. Apply the typed prefix, final-component underscore rule, deduplication, case-sensitive alphabetical order, and shared-prefix edit rule to discovered names. Insert identifiers only, with no dot, space, parenthesis, or import side effect.
5. For `from MODULE import TARGET`, resolve a root that is already bound in `python_namespace` through plain attribute segments using the §5.2 inspection rules. If it resolves, offer that live object's attributes through `dir`; do not mix in discoverable submodules. If no root binding exists, offer only discoverable direct submodules of `MODULE` and the explicit additional children. If a bound lookup fails, return no candidates instead of trying module discovery. A relative module expression yields none. Do not add the module or target to `sys.modules` or the evaluator namespace merely to discover it.
6. Extend `tests/test_completion.py` with deterministic cases from §6.3. Use a temporary module search path and multiple planted names sharing a prefix so test outcomes do not depend on installed distributions. Prove `import pathl` → `import pathlib` without importing it; component-by-component `import importlib.resources`; later comma-separated targets; `os.path` and `collections.abc`; bound `from math import sq` → `sqrt`; unbound `from math import sq` with submodule-only results and `math` still absent from the evaluator namespace; a parenthesized continuation; alias and relative-import refusal; and shared-prefix behavior. Check target absence from `sys.modules` where applicable, as well as absence from the evaluator namespace. Keep all 000 tests passing.

## Verification and completion

From the project root, use uv only:

```console
uv sync
uv run pytest tests/test_completion.py
uv run pytest
```

If uv is unavailable, stop and report it; do not substitute another environment manager. The checkpoint is complete when §6 import completion works through the existing headless API, discovery does not import targets, the focused and full suites pass, no forbidden file changed, and Tab remains unbound. Report the test result and changed files, then stop without starting completion 002.
