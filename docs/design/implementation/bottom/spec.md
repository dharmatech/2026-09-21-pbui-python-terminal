# Specification — the bottom two rows

**Status:** Accepted for the bottom checkpoint series. This file is the complete design input for the checkpoint manager and implementers. It assigns no implementation work by itself.

The input row names the listener's current editor mode before its prompt. The documentation row above it begins with the pointer target or pending selection, then gives the existing left and right actions in short, scannable clauses. This changes presentation of those two rows, not the actions behind them.

## 1. Checkpoint series and boundary

The series identity is **bottom**. Checkpoints are spoken “bottom 000”, “bottom 001”, and so on, filed as `checkpoints/000-slug.md`, `checkpoints/001-slug.md`, with three-digit numbers starting at 000 and never renumbered. Slugs are lowercase hyphenated words. A checkpoint manager writes one checkpoint and stops; each implementer works from one checkpoint and stops. After human acceptance, this specification is their design authority. Code and tests go in the project root, `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`, not this design folder.

There is **one layer, bottom 000**: mode word, visual boundary, documentation shape and complete sentence conversion, with tests and a hand check together. A manager may split it only if one implementer conversation would exceed the checkpoint size described by the project workflow. Any split keeps this order and adds no feature. No history-marker slice belongs to this series.

The existing listener, listings, REPL, chips, SymPy, transcript, and popup behavior is in place. The HTTP request/JSON and tutorial explorations are separate and are not prerequisites; where their presentations already have documentation, this specification converts its wording too. Earlier specifications remain the authority for clicks, accept types, menu contents and placement, input editing, retained objects, style, and card navigation. This specification **supersedes §4, “Documentation row,” of `docs/design/implementation/popup/spec.md` for wording and truncation**, along with earlier exact documentation sentences on the same cases. It does not supersede popup routing or any click behavior. The currently implemented HTTP and tutorial documentation cases are included below; if either exploration changes before bottom 000 is implemented, its click behavior remains authoritative and its new documentation case must be translated into the same shape before this layer is complete.

No history markers, listing-header changes, new colors, click gestures, command or menu changes, card layout changes, popup movement, sidebar, result boxes, spinner, or session status bar. The `› ` transcript input marker remains. Green underlining keeps its existing meaning: a presentation is acceptable to the pending command. The existing directory and process-state colors stay. A tutorial card that literally quotes an old documentation sentence updates just that quote; the tour otherwise stays as it is.

## 2. Host, source layout, and interfaces

This is the existing Python `src/` package in `src/pbui/`, with tests in `tests/`. Python and dependency management use **uv only**. Do not reinitialize the project or add a dependency for this change. From the project root, `uv sync` refreshes the environment, `uv run pytest` is the automated gate, and `uv run pbui` is used only for the manual screen check. If uv is unavailable, stop and report it.

Keep formatting rules in a pure `src/pbui/bottom.py` module that imports no Textual object. It may use the headless listener, presentations, and existing display-width/escaping helpers. Its public headless functions are:

```python
format_mode(listener: HeadlessListener) -> str
format_documentation(
    listener: HeadlessListener,
    presentation: Presentation | None,
    logical_column: int | None = None,
    *,
    menu_open: bool = False,
) -> str
format_menu_item_documentation(
    listener: HeadlessListener, label: str, target: Presentation
) -> str
```

The menu-border, invisible-target, and too-large-menu messages also use pure helpers or constants in that module. `src/pbui/terminal.py` remains the only Textual boundary: it calls these functions, supplies menu hover/override context, and renders the two rows. Existing callers that import `format_documentation` from `pbui.terminal` may keep doing so via a re-export; there must be one source of wording. A headless mode/target/segment formatter must not create widgets or inspect a live terminal. Tests of its returned text import `pbui.bottom` without importing Textual.

The documentation formatter returns the **full**, untruncated sentence. The widget applies terminal-cell truncation at render time. An action-menu item is a transient menu presentation whose saved action label and target are supplied to `format_menu_item_documentation`; it is not an ordinary history hit. Any presentation label placed in documentation uses the same escaping and captured identity already used by history and the popup. Do not read a live filesystem or process to build a label.

## 3. Input row

The row order is **bold mode word**, a plain ` │ ` separator, then the prompt and editable content. Draw a one-cell, full-width, **thin top rule** on the input widget in the terminal's ordinary foreground; this border sits between documentation and input content and carries no accent color. The documentation content remains one physical row and the editor content remains one physical row. The rule is part of the input widget, not a new status widget. Keep the input's existing focused cursor indication distinct from the bold mode word.

At ordinary and colon prompts the content after ` │ ` begins `pbui:/absolute/current/directory> `. A continuation keeps its `...> ` prompt after the directory, for example `CONTINUE │ pbui:/work ...> `; the cwd is still visible on a wide terminal. The pending substring editor keeps its literal `narrow ` prefix after the prompt. The absolute directory is the listener's current `cwd`, escaped with the existing safe-display rule, and updates after `cd`. For illustration:

```text
PYTHON │ pbui:/work>
COMMAND │ pbui:/work> :ls
CONTINUE │ pbui:/work ...>     value
SELECT FILE FOR rm │ pbui:/work>
SELECT TEXT FOR narrow │ pbui:/work> narrow abc
```

Mode selection has this precedence, independent of whether a menu is open:

| State | Exact mode word |
|---|---|
| Pending `:rm` presentation accept | `SELECT FILE FOR rm` |
| Pending `:cd` presentation accept | `SELECT DIRECTORY FOR cd` |
| Pending `:kill` presentation accept | `SELECT PROCESS FOR kill` |
| Pending `:show` presentation accept | `SELECT FILE/DIRECTORY/PROCESS FOR show` |
| Pending command or menu `narrow` substring accept | `SELECT TEXT FOR narrow` |
| Pending Python continuation, including an empty continuation line | `CONTINUE` |
| A colon command being typed, including a bare colon and leading spaces before it | `COMMAND` |
| Ordinary Python text or chips, and an empty prompt | `PYTHON` |

A pending accept outranks a suspended Python continuation. An open menu shows the mode of the editor underneath it. Tutorial Try refusal and navigation are documentation cases, not editor modes. Resolve the mode from the listener's state, not from a previously painted prompt or the presence of green history text.

The mode is a fixed left anchor. At any content width at least the display width of its mode word, **all of that word is visible**, including when the cursor moves through a long editable line. The separator, directory, and editor use the remaining cells. At a wide width the complete absolute directory and editor are visible. As width shrinks, shorten the directory first with a leading ellipsis, preserving its trailing path; then horizontally scroll only the editor area to keep the cursor visible. Omit the separator and prompt only when no room remains after the mode. Do not scroll the mode off the left edge, clip its letters, or change the stored cwd or editor text when shortening their drawing. A width smaller than the mode word can crop safely because the physical row cannot contain it.

## 4. Documentation grammar and precedence

Use ` • ` between scan parts. A normal target sentence is `TARGET • Left: ACTION • Right: ACTION`. `Left` and `Right` are the actual existing mouse buttons, and `Right: menu` means the existing menu is available. `Right: no menu` means it is unavailable. No middle-button text. A named target carries its kind and its existing short label where there is one, so the action clause does not repeat that label. The examples and table below are exact full sentences before width truncation; replace capitalized placeholders as defined here.

| Placeholder | Target text |
|---|---|
| `FILE “NAME”`, `DIRECTORY “NAME”` | Existing safely escaped basename of the retained path. |
| `PROCESS PID` | Retained captured decimal PID. |
| `DIRECTORY LISTING`, `PROCESS LISTING` | Existing listing header, with no fabricated name. |
| `PYTHON INPUT`, `COMMAND INPUT` | Saved input kind; the potentially long source is not copied into this row. |
| `ACTION “LABEL”` | Captured action label, safely escaped. |
| `SYMPY EXPRESSION`, `PYTHON VALUE` | Existing value kind; do not call `repr` or synthesize a label. |
| `GET REQUEST “URL”`, `HTTP RESPONSE STATUS “URL”` | Existing safely escaped request URL, and captured response status/final URL. |
| `JSON OBJECT (N keys)`, `JSON ARRAY (N elements)` | Existing collection summary/count, also for a nested member. |
| `TEXT`, `ERROR`, `TUTORIAL CARD “TITLE”`, `TUTORIAL TRY` | Existing kind, stored card title where available. |
| `TUTORIAL DIRECTION “TITLE”` | Existing control direction (`Next`, `Back`, `Up`, or `Contents`) and destination title when it has one. A disabled boundary control uses just `TUTORIAL BACK` or `TUTORIAL NEXT`. |
| `NO TARGET` | Empty/literal history, no hit, or an unrecognized ordinary presentation. |

The target of an action-menu item is `MENU “ITEM” ON TARGET`, where `TARGET` uses the table above and `ITEM` is the existing menu-item label. A menu border/interior cell without an item has `NO TARGET` in the target position. For an unrecognized presentation during an accept, show `OBJECT TYPE`, using its escaped presentation-type name, so the refusal identifies what was rejected. For a truncated process command field, append ` (command truncated)` after `PROCESS PID`; this is the existing condition, determined from the captured member and logical column, not from newly inspected process state.

Precedence is: menu rectangle item or border; exposed tutorial navigation/Try control outside that rectangle; pending substring accept; pending presentation accept; continuation with no hit; ordinary history hit; no target. Tutorial controls retain their existing click priority during either accept and while a popup is open. When a selection is pending, **prefix even a tutorial-control sentence with its selection**, so the line still begins with `SELECTING …`. A popup cannot normally open during a pending accept. Recompute on the same changes as today: pointer movement, popup open/close or item hover, editor mode/text/cursor, accept start/end, command execution, history/scroll, and resize. Special popup-failure messages persist only until the same pointer/listener change that clears them today.

## 5. Complete sentence list

### 5.1 Ordinary history target

These are the full sentences with no accept or menu item owning the pointer. `MENU` is `menu` only when the current presentation has an existing menu; otherwise it is `no menu`.

| Case | Exact full sentence |
|---|---|
| File | `FILE “NAME” • Left: show • Right: menu` |
| Directory | `DIRECTORY “NAME” • Left: show • Right: menu` |
| Process | `PROCESS PID • Left: show • Right: menu` |
| Process, pointer on a truncated command field | `PROCESS PID (command truncated) • Left: show full command • Right: menu` |
| Directory listing header | `DIRECTORY LISTING • Left: no action • Right: menu` |
| Process listing header | `PROCESS LISTING • Left: no action • Right: menu` |
| SymPy expression | `SYMPY EXPRESSION • Left: show • Right: menu` |
| Other registered value, including a GET request or HTTP response | `TARGET • Left: show • Right: menu`, where `TARGET` is `GET REQUEST “URL”`, `HTTP RESPONSE STATUS “URL”`, or `PYTHON VALUE` |
| Generic value without menu | `PYTHON VALUE • Left: show • Right: no menu` |
| JSON object | `JSON OBJECT (N keys) • Left: list members • Right: no menu` |
| JSON array | `JSON ARRAY (N elements) • Left: list members • Right: no menu` |
| Text | `TEXT • Left: no action • Right: no menu` |
| Error | `ERROR • Left: no action • Right: no menu` |
| Python input, editor empty | `PYTHON INPUT • Left: load into editor; Enter runs • Right: menu` |
| Command input, editor empty | `COMMAND INPUT • Left: load into editor; Enter runs • Right: menu` |
| Python or command input, composing Python | `TARGET • Left: insert at cursor • Right: menu` |
| Python or command input, editing a colon command | `TARGET • Left: no action while editing command • Right: menu` |
| Menu-action input, editor empty | `ACTION “LABEL” • Left: run again on same object • Right: menu` |
| Menu-action input, editing a colon command | `ACTION “LABEL” • Left: no action while editing command • Right: menu` |
| Tutorial card outer text, ordinary empty prompt or colon editing | `TUTORIAL CARD “TITLE” • Left: no action • Right: no menu` |
| Enabled tutorial Next, Back, or contents entry | `TUTORIAL DIRECTION “TITLE” • Left: open • Right: no menu` |
| Tutorial Up control | `TUTORIAL UP “Contents” • Left: open • Right: no menu` |
| Disabled Back on first card | `TUTORIAL BACK • Left: no previous card • Right: no menu` |
| Disabled Next on last card | `TUTORIAL NEXT • Left: no next card • Right: no menu` |
| Tutorial Try, editor ready | `TUTORIAL TRY • Left: load example into editor; Enter runs • Right: no menu` |
| Tutorial Try, busy editor or open popup | `TUTORIAL TRY • Left: finish or cancel current input before trying • Right: no menu` |

When composing Python, including a continuation, a result/object-bearing presentation or outer tutorial-card text uses the following site-dependent sentences. `TARGET` is its target text above. `MENU` reflects its existing menu. A `MenuActionInput` inserts its saved **target**; the word `target` below is required for that case. Saved Python/command input retains the separate `insert at cursor` sentence above.

| Insertion site | Exact full sentence |
|---|---|
| Valid, ordinary object | `TARGET • Left: insert value into expression • Right: MENU` |
| Valid, menu-action input | `ACTION “LABEL” • Left: insert target into expression • Right: menu` |
| In a string or comment | `TARGET • Left: insertion unavailable in string or comment • Right: MENU` |
| Other invalid Python position | `TARGET • Left: move cursor to Python expression position to insert • Right: MENU` |

The two refusal rows apply to a `MenuActionInput` and tutorial-card outer text as well as ordinary values. They never fall through to `show`. A JSON collection uses its `JSON ...` target and `Right: no menu` during composition; a GET request or HTTP response uses its kind and existing `Right: menu` when a translator is registered. The process command-field special sentence applies only to an ordinary show click; composition uses insertion wording.

### 5.2 Pending accepts and no target

Use `SELECTING TYPE FOR command` as the documentation lead, with `TYPE` exactly the accept type from §3. The modes in §3 say `SELECT`; documentation says `SELECTING`. A history target follows ` — `, then clauses separated by ` • `. The selection lead always appears, including when the pointer is on an unacceptable presentation or tutorial control. `Esc: cancel` explicitly names Escape; `Ctrl-G: cancel` preserves the other current key. For `:show`, `REQUIRED` is `File, Directory, or Process`; for the other commands it is their single accepted type.

| Case | Exact full sentence |
|---|---|
| Presentation accept, no target | `SELECTING TYPE FOR command • Point at highlighted REQUIRED and click • Esc: cancel • Ctrl-G: cancel` |
| Acceptable File, Directory, or Process | `SELECTING TYPE FOR command — TARGET • Left: use and run command • Right: no menu • Esc: cancel • Ctrl-G: cancel` |
| Any unacceptable presentation | `SELECTING TYPE FOR command — TARGET • Left: cannot use TYPE; REQUIRED required • Right: no menu • Esc: cancel • Ctrl-G: cancel` |
| Substring accept, no target | `SELECTING TEXT FOR narrow • Type substring; Enter: narrow listing • Esc: cancel • Ctrl-G: cancel` |
| Substring accept, ordinary history hit | `SELECTING TEXT FOR narrow — TARGET • Type substring; Enter: narrow listing • Esc: cancel • Ctrl-G: cancel` |
| Pending accept, enabled tutorial navigation | `SELECTING TYPE FOR command — TUTORIAL DIRECTION “TITLE” • Left: open • Right: no menu • Esc: cancel • Ctrl-G: cancel` |
| Pending accept, disabled tutorial navigation | `SELECTING TYPE FOR command — TUTORIAL BACK/NEXT • Left: no previous/next card • Right: no menu • Esc: cancel • Ctrl-G: cancel` |
| Pending accept, tutorial Try | `SELECTING TYPE FOR command — TUTORIAL TRY • Left: finish or cancel current input before trying • Right: no menu • Esc: cancel • Ctrl-G: cancel` |

The last three forms also apply to substring accept with `SELECTING TEXT FOR narrow` as the lead. The tutorial Up control uses `TUTORIAL UP “Contents” • Left: open`; a contents entry uses its destination title. Ordinary history clicks during substring accept remain inert; the line does not invent a Left or Right action for them. An ordinary non-acceptable target during presentation accept uses its real presentation-type name in the `cannot use` clause, including `PythonInput`, `CommandInput`, `MenuActionInput`, `DirectoryListing`, `ProcessListing`, `Text`, `Error`, `Value`, and `TutorialCard`. The accepted pairs remain `rm`/File, `cd`/Directory, `kill`/Process, and `show`/File, Directory, or Process.

| Other no-target state | Exact full sentence |
|---|---|
| Empty or literal history, no hit | `NO TARGET` |
| Python continuation, no hit | `NO TARGET • Python continuation: enter another line • Esc: discard • Ctrl-G: discard` |
| Unrecognized ordinary presentation | `NO TARGET` |

### 5.3 Popup menu and transient messages

An open popup retains its existing rectangle priority. These sentences describe the item under the pointer, including its saved action target. An item has no secondary menu.

| Menu item | Exact full sentence |
|---|---|
| File action | `MENU “ITEM” ON FILE “NAME” • Left: run • Right: no menu` |
| Directory action | `MENU “ITEM” ON DIRECTORY “NAME” • Left: run • Right: no menu` |
| Process action | `MENU “ITEM” ON PROCESS PID • Left: run • Right: no menu` |
| Directory-listing action | `MENU “ITEM” ON DIRECTORY LISTING • Left: apply • Right: no menu` |
| Process-listing action | `MENU “ITEM” ON PROCESS LISTING • Left: apply • Right: no menu` |
| Registered-value translator, including SymPy and HTTP | `MENU “ITEM” ON TARGET • Left: apply • Right: no menu` |
| `yank` on Python or command input, empty editor or composing Python | `MENU “yank” ON TARGET • Left: yank into editor • Right: no menu` |
| `yank` on Python or command input, editing a colon command | `MENU “yank” ON TARGET • Left: no action while editing command • Right: no menu` |
| `run again` on menu-action input | `MENU “run again” ON ACTION “LABEL” • Left: run again on same object • Right: no menu` |
| Border or interior cell without item | `NO TARGET • Click an item • Esc: close menu • Ctrl-G: close menu` |

An exposed tutorial navigation/Try control outside the popup rectangle keeps its tutorial sentence from §5.1. Try is busy while the popup is open. An outside pointer elsewhere closes the menu through the current routing and uses the newly hit history sentence. Opening a menu with `Ctrl-O` when its target has no visible cell produces `TARGET • Point at object to open its menu`; a menu too large for the history rectangle produces `TARGET • Menu does not fit in history area`. These are transient overrides with no invented button action, and they clear at the same pointer or listener state change as today. A `Ctrl-O` attempt with no target or no menu items keeps the normal target/no-target sentence and does not open a menu.

## 6. Rendering and verification

The documentation widget stays one content row immediately above the input rule; it never wraps. Compose the target and action clauses separately before display-width fitting. First shorten the target's **name/title/label** with an ellipsis, preserving its kind and the complete `Left:` and `Right:` clauses. If needed, omit the optional target detail entirely, keeping the kind. Keep `Left:` and `Right:` clauses whole whenever the terminal width can physically contain the kind, separators, and both clauses. Cancel/refusal text is semantic content, not decorative padding: preserve it ahead of optional target detail. At a width below the fixed content's minimum, use the existing display-safe ellipsis/crop; no one-row layout can show both full clauses in fewer cells than their combined width. Never split a wide character or leak raw control text. Do not change menu width or the popup's position to fit documentation.

Headless formatter tests in `tests/` import `pbui.bottom` with **no Textual import**. They prove the exact mode words for an empty Python prompt, typed colon command, Python continuation, all four presentation accepts, and a command/menu substring accept; they also prove the menu leaves the underlying mode unchanged. They verify the exact sentences in §5, especially a file with both buttons, an unacceptable accept target and its refusal, pending `:rm` with no target and Escape, substring accept, menu item and border, input yank, JSON collection, request/response, tutorial control/Try, and no-target continuation. Use existing headless listener fixtures and retained objects, not a live network or process inspection. Test display-cell fitting with a long escaped target name: the name truncates before `Left:` or `Right:` and both action clauses remain complete at a width that can fit them. Update existing exact-wording assertions across the suite; do not leave an old documentation sentence as a fallback. One focused Textual screen test may verify the top rule and fixed mode anchor through cursor scrolling.

Run `uv run pytest` from the project root. For the hand check, start `uv run pbui` from a disposable directory and inspect one session: read `PYTHON` on the empty prompt; point at a file and read its target plus `Left` and `Right`; type `:rm` and read `SELECT FILE FOR rm` and the selection-led documentation; press Escape and read `PYTHON` again. Do not click the file during this check. Passing the old suite, the new formatter tests, and this hand check is the acceptance gate.

The result is accepted when both rows show the chosen layout, every current documentation case has the new sentence shape with its existing action/refusal/cancel meaning, mode transitions and truncation follow this file, and every click, menu, insertion, yank, accept, tutorial control, style meaning, and history layout still behaves as before. Human review of this draft comes before the checkpoint manager writes bottom 000.
