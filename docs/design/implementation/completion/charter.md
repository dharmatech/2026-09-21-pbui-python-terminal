# Charter — complete the input row

**Status.** Handoff from the high-level discussion into a **design
conversation**. Not a checkpoint. Not an implementer assignment.
This file lives in `docs/design/implementation/completion/`. The
specification will live beside it as [`spec.md`](spec.md).
Checkpoint files will live in `checkpoints/` beside it. Map:
[`README.md`](README.md). The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.
The spec writer returned three example conflicts. This revision
resolves them. `:sort` is submitted only after `:ls` and only with
one key. The square-root call is typed after Tab. The unique import
fragment is `pathl`.

**Your job.** Turn this charter into a specification for Tab
completion in the input row: listener command names, Python names,
attributes of a live object, and import targets. The series identity
is **completion**. Then **stop**. Do not write checkpoints. Do not
implement.

The specification refuses a newer Python requirement, a completion
library, path completion, and completion that calls or imports in
order to discover names. Those refusals keep the series small enough
to slice.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Read the command registry and command parse in
   `HeadlessListener`, the Python piece cursor and the evaluator
   namespace, and chip insertion. Read `CommandInput.on_key`, recall's
   Up and Down, the action-menu overlay, and the keyboard table in
   [`docs/user-guide.md`](../../../user-guide.md). Completion reads
   the unsent editor. It does not complete the drawn `⟨…⟩` text.
3. Record the locked decisions in §4. Resolve the open question in
   §5.
4. Write `spec.md` in this folder. A later checkpoint-manager
   conversation slices **completion 000**, then **completion 001**,
   then **completion 002**, under `checkpoints/` here, one checkpoint
   per conversation.
5. Stop. The human reviews the spec. Do not write those checkpoint
   files.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification.

Keep the spec to Tab on the unsent editor. A new dependency, a raised
Python requirement, Jedi, or completion of a file path is a defect in
this document.

## 2. Predecessors

The listener through recall is implemented. Colon commands and Python
forms share one input row. A Python form is a sequence of text pieces
and chips. The evaluator keeps a process-local namespace whose
`__name__` is `__pbui__`. Up and Down recall earlier submissions.
Escape and `Ctrl-G` cancel the unsent editor, and they close an open
action menu first. The mouse wheel scrolls history. The project
requires Python 3.11 or newer.

This exploration does not create a new project. Implementers keep
using uv in the existing project. Add no dependency. Do not raise
`requires-python`. The designer does not run uv.

| Place | What goes there |
|---|---|
| `docs/design/implementation/completion/` | This charter, `spec.md`, and `checkpoints/` |
| Project root | The existing `pbui` package, `tests/`, and `docs/user-guide.md` |

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **A command name completes.** `:` then Tab lists the listener's
   commands. `:so` then Tab becomes `:sort`.
2. **A live object completes.** After `import math` has been
   submitted, `math.sq` then Tab becomes `math.sqrt`. A chip followed
   by `.` then Tab lists the public attributes of that chip's object.
3. **An import completes without importing.** `import pathl` then Tab
   becomes `import pathlib`, and `pathlib` is not imported by that
   Tab. `import pa` is not that example: another installed
   distribution can share the prefix `pa`. `from math import sq`
   completes `sqrt` when `math` is already bound, and offers no
   attributes when `math` is not bound.
4. **The line you were typing survives.** Several matches open a list
   and leave the unsent editor otherwise intact, apart from a shared
   prefix the rules insert. Escape closes the list and leaves that
   editor. Up and Down move in the list while it is open, and they
   recall again once it is closed.
5. **Waiting and menus ignore Tab.** Tab changes nothing while a
   presentation accept, a substring accept, or the action menu is
   open.
6. **Old tests still pass**, plus headless completion tests, one
   screen test, the user-guide keyboard changes, and one hand check.
   `requires-python` remains `>=3.11`.

## 4. Locked decisions (record these; do not reopen)

### 4.1 One Tab, on the unsent editor

Tab asks the headless listener to complete at the current caret.
The listener decides from the unsent editor, which is the pending
Python lines plus the current line, or the colon-command text and
its chip. The drawn input, including a chip's `⟨…⟩` label, is not
the text that is completed.

The result is one of three:

| Result | What happens |
|---|---|
| No candidate | The editor stays as it is. No list opens. |
| One candidate | That name replaces the partial token. The caret sits just after the inserted name. No list opens. |
| Several candidates | They are offered in alphabetical order. When they share a prefix longer than the typed fragment, that extra prefix is inserted first. The list stays open for what remains. |

A completion is an ordinary edit of the unsent editor. It does not
submit, does not move the recall position, and does not scroll
history. The next Up still discards unsent edits, including a
completion, under the recall rules.

The inserted text is the identifier only. Tab does not add `(`.

### 4.2 Command names

A completion site in a colon command is the command token: optional
whitespace, `:`, optional whitespace, then the partial command name,
with the caret in that name. `:` with the caret just after it lists
every command. `:so` completes among the names that start with `so`.

The names are the listener's existing command registry, matched
case-sensitively. Today that registry is `ls`, `ps`, `show`, `kill`,
`cd`, `rm`, `sort`, `narrow`, `only`, `widen`, `get`, and `tutorial`.
The spec reads the registry rather than copying a second list.

Once a space or a chip follows the command name, Tab does nothing.
Arguments, URLs, and paths have no completion. Choosing a file,
directory, or process stays a click.

### 4.3 Python names and attributes

Outside an import statement, the site is a partial identifier at the
caret, or a dot whose receiver is already an object.

A bare identifier completes from the evaluator namespace, then
builtins, then keywords, as one set of names. A name is offered once.
A name bound in the evaluator namespace is that binding.

A dotted site is a chain that starts with a bound name or a chip and
continues by attributes. `math.sq` completes attributes of the bound
`math` whose names start with `sq`. A chip, then `.`, completes
attributes of that chip's object. A longer chain uses `getattr` for
each plain attribute. The caret's partial identifier is the last
segment and may be empty, as in `math.` or a chip followed by `.`.

These are not sites: a call, a subscript, parentheses around the
receiver, an operator, a string, or a comment. `make_object().` does
not complete. Tab does not call the receiver and does not evaluate a
subscript. Listing attributes uses `dir` and may run a user
`__getattr__`. The spec states that limit. A failing lookup leaves
the editor unchanged.

Names that start with `_` are omitted unless the typed fragment
itself starts with `_`.

### 4.4 Import targets

An import site is an unsent form that is an `import` statement or a
`from … import` statement, including a parenthesized continuation of
that statement. Each comma-separated target is its own site. The text
after `as` is not a site. A relative import, one whose module part
starts with `.`, is not a site.

`import` completes module and package components from the import
finders, without importing the module. The public sources are
`pkgutil.iter_modules`, `sys.builtin_module_names`, and
`sys.stdlib_module_names`. Dots select the next component, so
`import importlib.res` can complete `resources` without importing
`importlib`. The spec names the extra components those sources miss
and that Tab must still offer. The minimum extra set is `os.path`
and `collections.abc`.

Underscore modules follow the same prefix rule as attributes.

`from math import sq` completes attributes of `math` only when `math`
is already bound in the evaluator namespace. The attribute rules in
§4.3 apply, including the underscore rule. When `math` is not bound,
Tab completes submodules of `math` and does not import `math`. It
does not offer `sqrt` in that case.

### 4.5 When Tab does nothing

Tab does nothing, and opens no list, when any of these is true:

- a presentation accept is pending
- a substring accept is pending
- the action menu is open
- the caret is not in a site from §4.2, §4.3, or §4.4
- the empty editor has no token to complete

`:` is a site. A dot after a receiver is a site. A blank Python
prompt is not.

### 4.6 The candidate list

Several candidates open one list. It is an overlay owned by the
input row. It is not the action menu, and its entries are not menu
actions. It is not a history row, not a presentation, and not a hit
target in history. Opening and closing it leaves the history
viewport where it was. The documentation line keeps its current
sentence.

The list shows candidates in the alphabetical order §4.1 names,
with one highlighted row. The highlighted row stays visible while it
moves. §5 picks how many rows are visible and whether the list sits
above the documentation line or over the bottom of history.

While the list is open:

| Key | Effect |
|---|---|
| Up, Down | Move the highlight. They do not recall. |
| Tab | Move the highlight to the next candidate, wrapping to the first. |
| Enter | Insert the highlighted candidate, close the list, and do not submit. |
| Escape, Ctrl-G | Close the list and leave the editor as it is. |
| A character that edits the editor | Recompute the candidates from the new caret. Zero candidates close the list. One or more candidates leave the list open and do not insert a final name until Enter or a later Tab that finds exactly one. |
| A click | Close the list. The click does not also run its ordinary command, yank, or chip insertion. |

Recall's Up and Down apply again only after the list is closed.
Escape and `Ctrl-G` close this list before they close a menu or
clear the editor. The user-guide keyboard table gains a Tab row and
adjusts the Escape row so this list is closed first. The spec writes
those sentences. The rest of the guide stays as it is, and the smoke
test gains no new step.

### 4.7 What stays as it is

Clicks, yank, chips, accept, the action menu, colon dispatch,
recording, recall, and the 500-row history stay as they are once the
list is closed. The wheel still scrolls history. The input row keeps
its mode word, directory, and chip drawing. Documentation sentences
stay on the bottom specification.

`requires-python` stays `>=3.11`. Completion uses the standard
library already available there. It does not import
`_pyrepl._module_completer`, `readline`, or `rlcompleter`, and it
does not add Jedi or another completion package.

### 4.8 Tests

Headless tests build candidates and apply them without Textual.
Cover at least: `:` listing the registry in alphabetical order;
`:so` becoming `:sort`; no completion after `:ls `; a bound name; a
keyword; a namespace name hiding a builtin of the same spelling;
`math.sqrt` from a bound module; a chip's attributes; `_` names
hidden until the fragment starts with `_`; no completion of
`make_object().`; `import pathl` becoming `import pathlib` without
importing it, on a module path the test controls; several planted
matches for one prefix, so the test does not depend on `packaging`
or any other installed distribution; `import importlib.resources`
component by component;
`os.path` and `collections.abc`; `from math import sqrt` when `math`
is bound; submodule-only results when it is not, with `math` still
absent from the namespace; no relative-import completion; no
completion after `as`; a shared prefix inserted while several
candidates remain; inert Tab during accept, substring accept, and
`menu_open=True`.

Completion 000 proves §4.1 through §4.3 and §4.5 for commands, names,
and attributes. Import sites return no candidates there.

Completion 001 proves §4.4. The terminal keys stay unbound through
both headless slices.

Completion 002 binds Tab, draws the list, covers the keys in §4.6,
updates the user-guide keyboard table, and adds one screen test and
the hand check. The screen test opens a list, moves the highlight
with Up and Down, accepts with Enter, closes with Escape, and shows
that history does not scroll and that Up recalls again after the
list is gone.

The hand check uses a disposable directory that contains two ordinary
files. Run `uv run pbui` from that directory. Type `:` and press Tab.
Submit `:ls` and see the file table. Type `:so`, press Tab, and see
`:sort` with the caret after the name. Type ` name` and press Enter.
The table sorts by name, and history shows neither
`no listing in history` nor `sort requires one key`. Submit
`import math`. Type `math.sq` and press Tab. The line is `math.sqrt`
and still has no parentheses. Type `(4)` and press Enter. The value
is `float 2.0`. Type `import pathl` and press Tab. The line is
`import pathlib`. Press `Ctrl-G`, submit `pathlib`, and see a name
error, so the Tab did not import the module. Type
`from math import sq`, press Tab, and press Enter. The import binds
`sqrt`. Open a menu and press Tab. The menu stays. `uv run pytest`
is the automated gate. `uv run pbui` is only the hand check.

### 4.9 Slice order

**completion 000** completes command names, Python names, and
attribute chains, including chips, on the headless listener.

**completion 001** completes `import` and `from … import` on that
same listener.

**completion 002** binds Tab, draws the list, updates the user-guide
keyboard table, and adds the screen test and the hand check.

The checkpoint manager may split a slice that does not fit one
implementer conversation. The split keeps this order and adds no
feature. Do not add a slice for path completion, signature hints, or
a documentation-line rewrite.

## 5. Open question (resolve this in the spec)

### 5.1 How the list is drawn

Pick one visible-row cap from 6 through 12 inclusive. The highlight
scrolls inside the list when there are more candidates than the cap.
Choose whether the list is placed just above the documentation line
or over the bottom rows of history. The documentation line stays
visible and keeps its current sentence. The list is not stored in
history.

State the cap, the placement, and the screen assertion that shows
the cap and the unchanged documentation sentence.

## 6. Authority

The repl specification is the law for the evaluator namespace. The
chips specification is the law for pieces and chip identity. The
recall specification is the law for Up and Down while no completion
list is open. The popup specification is the law for the action
menu. The bottom specification is the law for the documentation
sentences and the input row's mode word. The listener specification
is the law for the command registry and for choosing a file,
directory, or process by click.

While the completion list is open, this exploration wins for Up,
Down, Enter, Tab, Escape, and `Ctrl-G`. Where this charter and an
earlier specification disagree about a click once the list is
closed, the earlier specification wins.

## 7. Handoff reminder

The series identity is **completion**. Checkpoint 000 is spoken
**completion 000** and filed as `checkpoints/000-slug.md`. Checkpoint
001 is spoken **completion 001**. Checkpoint 002 is spoken
**completion 002**. Numbers are three digits, start at 000, and are
never renumbered. The slug is lowercase words separated by hyphens.
The checkpoint manager writes one checkpoint, then stops. Code and
tests go at the project root
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`, not in
this folder.

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. The first identity is **completion 000**.
The second, in a later conversation, is **completion 001**. The
third, in a later conversation, is **completion 002**.

After the spec is accepted, `spec.md` is the design authority for
those conversations. This charter is the assignment for the spec
writer. Later conversations do not read it.
