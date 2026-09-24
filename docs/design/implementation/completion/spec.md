# Specification — Tab completion in the input row

**Status:** Accepted. This is the complete design input for the checkpoint manager and implementers. It assigns no implementation work by itself and is their design authority; they do not need the charter.

Tab completes a name at the caret of pbui's unsent input. It uses the listener's command registry, the live Python namespace, attributes of a bound object or chip, and importable module names. A candidate list lets the user choose when several names remain. Completion edits the existing editor; it never submits input or turns a displayed chip label into source.

## 1. Checkpoint series

The series identity is **completion**. Checkpoint 000 is spoken **completion 000** and filed as docs/design/implementation/completion/checkpoints/000-slug.md; 001 and 002 use the same three-digit format. Numbers start at 000, are never renumbered, and use lowercase hyphen-separated slugs. The checkpoint manager writes one checkpoint, then stops. An implementer completes only the assigned checkpoint, then stops. Code and tests go at the project root, not in this design folder.

The layer order is:

1. **Completion 000:** headless command, Python-name, and object-attribute completion, including chips and modal guards.
2. **Completion 001:** headless import and from … import completion without importing to discover names.
3. **Completion 002:** Tab and candidate-list interaction in Textual, the keyboard guide, one screen test, and the hand check.

Each layer is intended as one logical checkpoint. A manager may split a layer that would exceed one implementer conversation, preserving this order and adding no feature. Terminal keys remain unbound through 000 and 001. The manager does not write all three checkpoints in one conversation.

## 2. Product boundary and existing authority

This series adds completion only to the current unsent editor. It adds no path, URL, command-argument, signature, or call completion; no new command, completion library, newer Python requirement, or screen region. It does not call a receiver, evaluate a subscript, import a target to find its names, or add an opening parenthesis after a name. Selecting a file, directory, or process remains a history click. Completion results and the list are not transcript records or presentations. The 500-logical-row history limit and independent recall ring remain unchanged.

The accepted [REPL specification](../repl/spec.md) controls evaluator namespace and Python submission. The [chips specification](../chips/spec.md) controls Python pieces, chip identity, and caret atoms. The [recall specification](../recall/spec.md) controls Up and Down when no completion list is open. The [popup specification](../popup/spec.md) controls the action menu. The [bottom specification](../bottom/spec.md) controls documentation sentences and input-row mode, directory, and chip drawing. The [listener specification](../listener/spec.md) controls the command registry and default history clicks. While the completion list is open, this file controls Up, Down, Enter, Tab, Escape, Ctrl-G, and the first click. After it closes, the earlier click and key rules apply again.

## 3. Host, layout, and commands

The existing project root is /home/dharmatech/journal/2026-09-21-pbui-python-terminal/. The target remains Linux with requires-python = ">=3.11". Source belongs in src/pbui/, tests in tests/, and the keyboard table in docs/user-guide.md. pbui.terminal remains the only module importing Textual. The first two layers must be testable without Textual. A headless helper in src/pbui/completion.py holds token and module-discovery logic; the authoritative editor and namespace remain in HeadlessListener.

The project and environment already exist. Implementers use uv only, from the project root:

~~~console
uv sync
uv run pytest
~~~

Completion 002 additionally runs uv run pbui for the hand check from a disposable directory under the project root. There is no uv init, dependency addition, or lockfile change in this series. If uv is unavailable, stop and report it; do not substitute pip or another environment manager. The spec writer does not run uv.

## 4. Shared headless contract

### 4.1 Input and result

HeadlessListener is the source of truth. It reads input_mode, input_text, command_cursor, python_pieces, python_cursor, pending_python_pieces, python_namespace, pending_request, and pending_substring_listing as they stand when Tab is pressed. The command caret is a character boundary in command text. The Python caret counts characters and whole PythonChip atoms; a chip's value is the receiver and its label is drawing only. Pending Python lines supply lexical context but only the current editable line can be replaced. A colon command is recognized under the existing input-mode precedence; a continuation or line containing a Python chip stays Python even if its text begins with a colon.

Expose these headless operations on HeadlessListener, with no Textual imports:

- **completion_candidates(*, menu_open: bool = False) -> tuple[str, ...]** computes names at the current caret without editing input. It returns distinct, case-sensitive names in alphabetical order. It may perform the permitted dir/getattr inspection in §5.2.
- **complete(*, menu_open: bool = False) -> tuple[str, ...]** computes those candidates and applies the initial Tab rule below. Its return is the candidate tuple from before the edit, so the screen can open a list when its length exceeds one.
- **apply_completion(name: str, *, menu_open: bool = False) -> bool** recomputes the current site and replaces its identifier only if name is still a candidate. It returns whether it applied the name. The screen uses it for Enter on a highlighted row.

If there is no candidate, complete returns an empty tuple and changes nothing. With one candidate, it replaces the current identifier and puts the caret immediately after the name. With several, it finds their longest shared prefix; if that prefix extends beyond the fragment typed to the left of the caret, it replaces the current identifier with that prefix and puts the caret after it. Otherwise it makes no edit. It returns all candidates in either case. The list opens only for several candidates. Replacement is confined to the current identifier token, including its part to the right of the caret; all text and chips outside that token retain position and identity. For an empty fragment after a colon or dot, the replacement span is empty. Candidate names are identifiers only: no parenthesis, space, dot, or import side effect is inserted.

Completion does not submit, compile, dispatch, change recall_position, overwrite the recall draft, append history, or move the history viewport. It is an ordinary live-editor edit: if the user is viewing a recalled entry, the next recall traversal discards this edit under the accepted recall rules. A Python replacement preserves every PythonChip by identity, including chips beside the replacement. Do not flatten the line or use set_input_text on a chip-bearing line.

### 4.2 Site detection and failure

Find the site from lexical source assembled from pending lines and the current line. Represent each chip as one opaque atom for scanning and keep a mapping back to current-line atom offsets; never scan or insert its displayed label. Tokenization must tolerate incomplete source, because completion runs before Enter. A string or comment, including an unclosed or multiline string, is never a site. Identify the current statement and caret rather than completing a similar word elsewhere in the form. A caret inside an identifier uses the prefix to its left for matching and replaces that whole identifier when applied. Unrelated suffix text remains untouched.

Return no candidates when a presentation accept, substring accept, or action menu is active; the screen passes menu_open=True for the menu. Also return none at a blank Python prompt, an unsupported syntax position, or a failing lookup. These paths open no list and leave editor, caret, chips, recall state, and history unchanged. A bare colon and a dot after an eligible receiver are sites even with an empty fragment.

## 5. Completion 000 — commands, names, and live attributes

### 5.1 Colon command token

A command site is optional leading whitespace, a colon, optional whitespace, and the command-name token, with the caret in or immediately after that token. A bare colon at its end is a site. Read names from the listener's existing command_names/registry, not a second maintained list. The current registry has ls, ps, show, kill, cd, rm, sort, narrow, only, widen, get, and tutorial; alphabetical display order comes from sorting the registry result. Matching is case-sensitive. A bare colon lists all names; :so has only sort and becomes :sort.

Once whitespace or a command chip follows the command name, there is no command-name site. Tab in an argument, URL, or path does nothing. :ls followed by a space, including a caret immediately after that space, has no candidates. Completion neither prepares an accept nor runs the command.

### 5.2 Python bare and dotted names

Outside an import statement, a bare partial identifier completes from the evaluator namespace, Python builtins, and Python keywords as one set. A spelling occurs once. If a spelling exists in the evaluator namespace, that binding is the value used when a later dotted lookup starts from it; it hides the builtin of the same spelling. Do not inject command names into the Python namespace. A blank Python prompt has no prefix and no site.

A dotted site is a contiguous chain beginning with a name bound in the evaluator namespace or with a PythonChip, followed by one or more plain attribute segments separated by dots. The final segment is the fragment being completed and may be empty. Resolve the root to its live value and each *preceding* plain attribute with getattr; obtain final candidate names with dir on the resulting object. math.sq can become math.sqrt after import math has bound math; a chip followed by a dot lists attributes of the chip's original object. Resolve a namespace binding before any builtin with the same name.

A call, subscript, parenthesized receiver, operator inside the receiver, or other expression is not a dotted chain. make_object()., object[0]., and (object). do not complete; a failure in such a chain does not fall back to bare-name completion after the dot. Never invoke a candidate attribute merely to inspect it, call a receiver, or evaluate a subscript. dir can execute a user-defined __dir__, and getattr on a preceding segment can execute a user-defined __getattr__ or descriptor. That is the deliberate limit of live-object inspection; if either raises, Tab leaves the editor unchanged and offers no list.

For bare names, attributes, and later module components, omit names beginning with an underscore unless the current typed fragment begins with an underscore. Deduplicate, then sort alphabetically. The filter applies to the final component, not an earlier receiver segment.

### 5.3 Scope and proof

Completion 000 edits src/pbui/commands.py and adds src/pbui/completion.py for lexical and discovery helpers. It may edit src/pbui/chips.py for an atom-preserving text-span replacement. Add headless tests in tests/test_completion.py. It does not edit src/pbui/terminal.py, the guide, the evaluator, transcript, action-menu, or history code. Reserve import statements as unsupported sites in this layer: import pathl and from math import sq return no candidates until 001. Do not bind Tab yet.

Headless tests prove the registry's sorted colon list, :so to :sort, :ls-space inertness, a namespace name and keyword, a namespace binding hiding a builtin, a bound module attribute, a chip receiver preserved by identity, underscore filtering, a failed or ineligible dotted receiver, a string and comment refusal, a replacement at a mid-token caret, an ordinary shared-prefix edit with several candidates, no history or recall mutation, and inertness during both accepts and menu_open=True. Run uv run pytest.

## 6. Completion 001 — import targets

### 6.1 Import-site grammar

Recognize the current unsent import or from MODULE import statement lexically, including an incomplete statement and a parenthesized from … import continuation in pending Python lines. Each comma-separated target is independent. Complete the module or package component under the caret, not an earlier component or target. After an as token and in its alias, Tab has no site. A module part beginning with a dot is a relative import and has no site. Do not treat names in strings, comments, or a later unrelated statement as import targets. An import line containing a chip is not an import-name site.

A caret just after import and its separating space is a top-level site with an empty fragment. For import MODULE, match top-level module/package names after import; for a dotted module name, resolve the preceding complete components to a package search path and match only the next component. import importlib.res can become import importlib.resources without importing importlib. This also works for later comma-separated targets. The typed fragment, underscore rule, alphabetical order, shared-prefix rule, and identifier-only replacement are the same as §4 and §5.

### 6.2 Discovery without imports

For top-level names, combine pkgutil.iter_modules() over import paths, sys.builtin_module_names, and sys.stdlib_module_names. For child names, obtain a parent package specification and its submodule_search_locations by walking complete components with importlib.machinery.PathFinder.find_spec and explicit parent search paths; then use pkgutil.iter_modules on those paths. Do not use importlib.import_module, __import__, importlib.util.find_spec on a dotted name, or another helper that imports a parent merely to discover a child. A non-package parent has no discoverable child path. Finder or filesystem failure yields no candidates for that path rather than changing the editor. Discovery can consult import finders and package paths, but must not execute an import statement or add the completed target to sys.modules or the evaluator namespace.

The public discovery sources miss some importable standard-library components. Supply at least the explicit additional children os.path and collections.abc in their correct parent contexts, with the same prefix and underscore rules. They are candidates, not eager imports. The implementation may include another demonstrated missing standard-library component through the same small explicit map; it must not build a private hard-coded replacement for general finder discovery.

A caret just after from MODULE import and its separating space is an empty-fragment site. For from MODULE import TARGET, first check whether the module expression already resolves from a root binding in python_namespace through plain attribute segments. If it does, list that live object's attributes with the §5.2 rules; do not mix submodules into this bound-object result. If it does not resolve to a bound object, offer only discoverable direct submodules of MODULE using the safe package-path method, plus the explicit missing children. Thus bound math offers sqrt, while unbound math offers no sqrt and remains absent from the evaluator namespace. Failed bound-object lookup produces no candidates rather than importing to recover it. A relative from .… import statement offers none.

### 6.3 Scope and proof

Completion 001 extends src/pbui/completion.py and src/pbui/commands.py and adds import cases to tests/test_completion.py. It does not edit terminal, guide, dependency files, or history. Tests control a temporary module search path and plant multiple names sharing one prefix so results do not depend on unrelated installed distributions. They prove import pathl to import pathlib without importing pathlib, component-by-component import importlib.resources, comma-separated targets, both explicit extra children, bound from math import sq to sqrt, unbound from math import sq with submodule-only results and math still absent, a parenthesized continuation, alias and relative-import refusal, and shared-prefix behavior. Test imported-target absence in sys.modules where applicable, as well as absence from the evaluator namespace. The preexisting 000 tests keep passing. Run uv run pytest.

## 7. Completion 002 — keys, list, and guide

### 7.1 List placement and drawing

The completion list is transient state owned by ListenerScreen and its input row. Draw it **over the bottom rows of the visible history rectangle**, directly above the documentation line. It takes no layout height; opening, updating, and closing it do not change history scroll offset, anchor, logical rows, presentation intervals, or hit testing. The action menu and completion list are mutually exclusive. The list is never a menu, history presentation, or clickable history target. The documentation row stays in place and retains its current sentence. The input row retains mode word, directory, prompt, caret, and chip drawing.

The cap is **8 visible candidate rows**. Show one alphabetically ordered candidate per row, using at most min(8, visible history height, candidate count) rows, bottom aligned to the history rectangle. The first candidate is highlighted on opening. Up and Down move one candidate and stop at the first or last; Tab advances one and wraps to the first. Keep the highlighted index visible by shifting the list's window when it crosses the visible edge. Candidate text may be safely cropped to terminal width, but the stored name and Enter insertion remain complete. Distinguish the highlighted row by reverse style. Refresh the overlay area as needed, and restore underlying history drawing when it closes. A narrow or short terminal may show fewer than eight rows; it must not cover documentation or input.

### 7.2 Key and pointer routing

In pbui.terminal.CommandInput.on_key, an initial Tab calls HeadlessListener.complete(menu_open=screen.action_menu.is_open). Zero candidates leave editor and list unchanged; one candidate is applied without a list; several open the list and draw any shared-prefix edit. Consume Tab in all cases, including while an accept or menu blocks it. An open action menu keeps priority and is unchanged by Tab.

While the list is open, Up and Down move its highlight instead of recalling; Tab advances highlight and wraps when several candidates remain. Enter applies the highlighted candidate through apply_completion, closes the list, and does not submit. Escape or Ctrl-G closes the list first and leaves the editor exactly as it stands; only a later cancellation reaches existing menu/editor behavior. A character that edits the editor, including text input, paste, Backspace, or Delete, first performs the ordinary edit and then recomputes candidates at the new caret. Zero closes the list; one or more leave it open without applying a final name. A later Tab with exactly one candidate applies it and closes the list; a later Tab with several advances the highlight. After recomputation, highlight the first remaining candidate and keep it visible. A caret movement recomputes for the new site; close the list if that site has no candidates. No list key changes recall position or scrolls history.

The first click anywhere while the list is open closes it and is consumed before history selection, chip insertion, yank, menu opening, or an input-row action. After that click, ordinary clicks work again. The mouse wheel retains existing history-scroll behavior; the overlay remains pinned to the bottom of visible history until another rule closes it. If an external editor load, submit, accept, or menu opening occurs while a list is visible, close stale list state before showing the new state. These transitions do not add a transcript row for the list itself.

### 7.3 Keyboard guide and file scope

Add this row to the keyboard table of docs/user-guide.md:

| Tab | Complete a name at the caret; when a completion list is open, move to the next candidate. |

Replace its Escape row with:

| Escape | Close a completion list first; otherwise cancel like Ctrl-G, closing an open action menu first. |

Ctrl-G has the same list-first behavior described in §7.2. Leave the rest of the guide and its smoke test unchanged. Completion 002 may edit src/pbui/terminal.py, docs/user-guide.md, and tests/test_terminal.py; headless API adjustments, if genuinely needed, stay within files already named for 000 and 001. Do not alter other product modules or dependency files.

## 8. Verification

The automated gate is uv run pytest from the project root. Headless tests in 000 and 001 inspect candidates and applied edits without Textual, and verify no import to discover names. Existing tests must continue to pass. One focused screen test in tests/test_terminal.py opens the colon list, checks exactly eight candidate rows are visible when the history viewport can fit them, checks documentation sentence and history scroll offset before and after opening, moves highlight with Up and Down, scrolls the list window while keeping highlight visible, accepts with Enter without submission, reopens and closes with Escape, then confirms Up recalls again. It also checks inert Tab during the action menu and first-click dismissal. The list must not create a history hit target.

The hand check uses a disposable directory under the project root containing two ordinary files. Run uv run pbui there. Type a colon and press Tab to see commands. Submit :ls and see the file table. Type :so, press Tab to get :sort, then type a space and name and press Enter; the table sorts by name without no listing in history or sort requires one key. Submit import math. Complete math.sq to math.sqrt, type (4), and press Enter; see float 2.0. Complete import pathl to import pathlib, cancel that unsent line with Ctrl-G, then submit pathlib and see a name error, proving the Tab did not import it. Complete and submit from math import sq, confirming sqrt is bound. Open an action menu and press Tab; the menu stays open. uv run pbui is this hand check, not an automated gate.

## 9. Acceptance

The series is complete when a colon lists the current command registry alphabetically and :so becomes :sort; a bound math and a Python chip expose eligible live attributes; bare Python names include namespace, builtins, and keywords with correct shadowing; import components include pathlib, importlib.resources, os.path, and collections.abc without importing to discover them; bound from math import offers attributes and unbound math offers submodules only; unsupported and modal sites are inert; and multiple matches use the eight-row list with the key, click, recall, viewport, and documentation behavior above. The keyboard table reflects Tab and list-first Escape. The old suite, new headless tests, one screen test, and hand check pass. requires-python remains >=3.11, with no new dependency.
