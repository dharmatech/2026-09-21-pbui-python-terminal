# Specification — recall submitted input

**Status:** Accepted. This file is the complete design input for the checkpoint
manager and implementers. It assigns no implementation work by itself.

Up and Down walk the Python forms and colon commands submitted in this pbui
session. The chosen submission replaces the input editor, with its saved
objects intact. Moving forward past the newest submission restores the unsent
editor exactly as it was when the walk began.

## 1. Checkpoint series

The series identity is **recall**. Checkpoint 000 is spoken **recall 000** and
filed as `docs/design/implementation/recall/checkpoints/000-slug.md`;
checkpoint 001 is spoken **recall 001** and filed as
`docs/design/implementation/recall/checkpoints/001-slug.md`. Numbers have
three digits, start at 000, and are never renumbered. Slugs are lowercase
words separated by hyphens. The checkpoint manager writes one checkpoint,
then stops. Each implementer finishes only the checkpoint it receives, then
stops. After acceptance, this spec is their design authority; they do not
need the charter.

The layer order is **headless recall state**, then **terminal keys and guide**.
Recall 000 owns the ring, draft, previous/next operations, and their headless
tests. Up and Down may remain unbound on screen at its end. Recall 001 binds
the keys, adds one screen test, updates the keyboard table, and performs the
hand check. A checkpoint manager may split a layer that exceeds one
implementer conversation, preserving this order and adding no feature.

## 2. Product boundary and authority

Recall changes only the editor's Up and Down behavior for this process. There
is no history file, search binding, `history` command, history expansion,
`Ctrl-P`, `Ctrl-N`, or `Ctrl-R` recall behavior. The walk does not filter by
the editor's text. Quitting discards it. There is no change to clicks, yank,
Try, `run again`, accept, menus, colon dispatch, transcript recording, or the
documentation sentences. It adds no scroll key or multiline input viewport.
The mouse wheel continues to scroll the history surface.

The accepted [transcript specification](../transcript/spec.md) controls the
three saved input record types, their append points, yank, and `run again`.
The [chips specification](../chips/spec.md) controls chip identity and editor
pieces. The [listener specification](../listener/spec.md) controls the three
screen regions, wheel, and command grammar. Its §1 sentence beginning “There
are no pipelines” lists “up-arrow command history” among exclusions. This
series supersedes that exclusion for Up and Down only; the other exclusions
stay in force. The [bottom specification](../bottom/spec.md) controls the
input row, mode word, directory, chip drawing, and documentation line. The
[history specification](../history/spec.md) controls history grouping, blank
rows, and indent. Recall does not depend on completion of that spacing work.

Where this spec and an earlier one disagree about Up or Down, this spec wins.
Where they disagree about what a click, yank, or saved record does, the
earlier spec wins. The screen history remains capped at 500 logical rows;
recall has its own bound and does not change history retention, layout, hit
testing, or viewport anchoring.

## 3. Host and layout

The project root is
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. The existing
Linux application uses Python 3.11 or newer, a `src/pbui/` package, and uv.
Keep code in `src/pbui/`, tests in `tests/`, and the user guide at
`docs/user-guide.md`; only the design artifacts live in this folder. Do not
initialize another project or add a dependency for recall. `pbui.terminal`
remains the Textual boundary; the ring, draft, and traversal are headless.

The project and environment already exist. From the project root, use
`uv sync` to refresh the environment, `uv run pytest` for the automated gate,
and `uv run pbui` for the manual screen check. All Python and pbui commands
run through `uv`. If uv is unavailable, stop and report it; do not use pip or
another environment manager. The spec writer does not run uv.

## 4. Recall 000 — headless recall state

### 4.1 Entries and retention

`HeadlessListener` owns one process-local, ordered ring of the immutable
`PythonInput` and `CommandInput` **values** already appended as transcript
presentations. At the successful `_record_python` or `_record_command` append
point, put that same value at the newest end exactly once. Use the committed
record, including its original chip objects, labels, and complete Python
lines or command tail. Do not flatten displayed `› ` rows, reparse input, or
retain a `Presentation` as the recall entry. `MenuActionInput` is never an
entry. A read-only headless view of the entries and current position must let
tests inspect order and identity without Textual.

The bound is **400 submissions**. Appending entry 401 drops entry 1; each
later append likewise drops only the oldest entry. The 500-row screen history
retains its separate limit. An input remains recallable when its `› ` row has
been evicted from screen history; ring eviction alone makes it unreachable.
Repeated values are distinct entries. A syntax error, failed command, and
`:tutorial` each add an entry because each appends an input presentation.

An empty Enter, a bare colon, an unfinished Python continuation, Try, a
canceled accept, Next, Back, Contents, a menu action, and a left click that
runs `show` append neither input record and therefore add no entry. A delayed
presentation or substring accept adds its command entry only when the
accepted input completes the command and `CommandInput` is appended. During
the wait, the arrows are inert under §4.3.

### 4.2 Draft and traversal

The traversal position is either **draft** or the index of an entry. It starts
at draft. On the first Up with a nonempty ring, take an independent snapshot
of the current unsent editor and show the newest entry. The snapshot contains
pending Python lines, current `PythonLine` pieces and cursor, command text,
optional command chip and its loaded state, and the command caret. Preserve
each chip's object by identity. `PythonLine` is mutable, so the snapshot must
copy its pieces and cursor rather than alias the live line.

Up from an entry shows the next older entry. Down from an entry shows the next
newer entry. Down from the newest entry restores **every** stashed draft field,
including a caret in the middle of a command, then clears the stash and sets
the position to draft. Up on the oldest entry, Down on the draft, and either
arrow with an empty ring change nothing. These boundary actions do not ring a
bell or alter the documentation line.

Showing an entry replaces the entire editor with the saved input. It has the
same resulting editor state and end cursor as yank into an empty editor:
`PythonInput` restores prior lines as pending continuation lines and its last
line as editable pieces; `CommandInput` restores `:` plus its exact tail and
its optional command chip. Replacement clears incompatible pieces or chip
from the editor it replaces. It does not compile, dispatch, submit, open an
accept, or scroll to the entry's old transcript row. A multiline form uses
the existing one-row continuation display.

Editing a recalled entry changes only the live editor. The ring and stashed
draft remain unchanged. Another Up or Down discards those edits and loads the
destination. An Enter that appends a new `PythonInput` or `CommandInput` puts
that new value at the newest end and returns the position to the draft left by
the ordinary submission flow, clearing the stash; the older entry is
unchanged. This also applies when a recalled command first waits for accept:
the position resets only when the delayed record is appended. An Enter that
merely starts a Python continuation adds no entry and leaves the traversal
position; that continuation is an editor change until it is completed or
replaced by further traversal.

A successful yank or Try, whether it loads or inserts saved pieces, resets
the traversal to draft and drops the stash. The editor left by that operation
becomes the new draft. Apply the same rule to another explicit existing
saved-input load. A refused yank or Try changes neither position nor stash.
Internal suspend-and-restore used by a menu is not a new load. Ordinary yank
while composing Python still inserts at the cursor, and yank while composing
a command still refuses.

### 4.3 Headless interface and modal guard

Expose `recall_previous(*, menu_open: bool = False)` and
`recall_next(*, menu_open: bool = False)` on `HeadlessListener`, returning
whether the editor and position changed. Before any traversal, they check
`pending_request`, `pending_substring_listing`, and `menu_open`. If any is
active, both operations leave editor, caret, ring, position, and stash exactly
as they were. The menu flag comes from the terminal adapter in recall 001;
headless tests can pass it directly. Escape and `Ctrl-G` keep their existing
meanings. A Python continuation is ordinary unsent editor state and can be
stashed.

Move the command caret's source of truth into `HeadlessListener`: expose a
read-only `command_cursor` and a bounded `set_command_cursor(position)` for
the current command text. Textual sends command caret moves and edits to this
state; the screen reads it after recall. `set_input_text` resets the command
caret to the end of replaced text; an explicit caret move may then set it to
a different boundary. Python continues to use the existing `python_cursor`
and `set_python_cursor`. On showing a saved command, the
command cursor is at the end, as with empty-editor yank. This makes restoring
a mid-line command draft testable without Textual.

### 4.4 File scope and headless proof

Recall 000 may edit `src/pbui/commands.py` and add
`tests/test_recall.py`. It may use the existing transcript and chip types but
does not change `src/pbui/transcript.py`, `src/pbui/chips.py`,
`src/pbui/substrate.py`, or the terminal. If an additional production file is
truly needed, the checkpoint manager must name it before implementation.

Headless tests create a listener with injected services and temporary roots.
They prove mixed `:ls`, Python, and `:tutorial` order; duplicate submissions;
chips restored by object identity in both input types; a multi-line form's
pending lines; a partial draft and mid-line Python and command carets
restored after Up/Down; an edit discarded by another Up; an edited recall submitted as a new
newest entry while its source remains unchanged; and an incomplete
continuation adding no entry. They prove that a menu action and show-click do
not enter the ring, and that both arrows are inert during presentation accept,
substring accept, and `menu_open=True`. They cover an empty ring, oldest Up,
draft Down, and a ring entry still reachable after its transcript presentation
is evicted. A test appends **401** submissions and verifies that only the first
falls out of the 400-entry ring while the last 400 remain in order. No Textual
import is needed for these tests.

## 5. Recall 001 — terminal keys and guide

In `CommandInput.on_key`, bind `up` to `recall_previous` and `down` to
`recall_next`, passing `ListenerScreen.action_menu.is_open`. Consume the keys
even when recall is inert, so neither key scrolls history or inserts text.
After a successful traversal, read the listener's Python or command caret
and draw the input row accordingly; keep its focus, mode word, directory,
chips, and continuation prompt. Synchronize without `reveal_newest` and
without scrolling to the recalled presentation. After a refused or boundary
traversal, preserve the current caret and viewport. Ordinary Enter retains
its existing reveal behavior. Mouse-wheel scrolling still moves only the
history surface. The bottom documentation sentences stay unchanged.

Add exactly these two rows to the keyboard table in `docs/user-guide.md`:

| Key | Action |
|---|---|
| Up | Recall the next older submission from this session. |
| Down | Move toward newer submissions, then restore unsent input. |

Do not edit the rest of the guide or add a smoke-test step. Recall 001 may
edit `src/pbui/terminal.py`, `tests/test_terminal.py`, and
`docs/user-guide.md`. It does not revise the ring model, transcript drawing,
documentation formatter, history layout, or click routes.

One Textual screen test creates enough history rows to scroll, submits a
colon command and a Python form, types an unsent line, and presses Up, Up, Down, Down. It reads the input row after each
key, sees the draft restored, and checks that the history viewport has not
jumped to a transcript input row. It also sends a mouse-wheel event and
verifies that history scrolls while the input row stays pinned, then checks
that Up/Down do not use that scroll path. The screen test covers menu-open
arrows as inert; the headless tests cover all modal cases.

## 6. Verification

Run `uv run pytest` from the project root after each implemented slice; all
older tests and the new focused tests must pass. Recall 000 requires only its
headless proof. Recall 001 requires the screen test and one hand check.

For the hand check, use a disposable directory **under the project root**
containing a disposable file, and run `uv run pbui` from that directory. In one
session, submit `:ls` and a short Python expression. Type
`for n in range(2):`, press Enter to start a continuation, type `    n` on
its second line, and leave the caret before `n`. Press Up, Up, Down, Down:
the continuation and caret return. Cancel that unfinished continuation with
`Ctrl-G`. Submit `:rm` by clicking the disposable file in the listing; Up
recalls the command with that file object. Up again reaches the original
Python expression. Edit it and press Enter; the edited form becomes the
newest submission and later traversal still finds the original. Open a menu
and press Up; it stays open and the input does not change. Confirm that the
wheel still scrolls history. Clean up the disposable directory afterward.
The hand check exercises the screen; it does not replace the automated gate.

## 7. Acceptance

The result is accepted when Up walks submitted Python forms and colon
commands backward, Down walks forward and restores the complete unsent draft,
and each entry retains its original chips and multiline form. Edits to a
recalled entry do not mutate it; submitting an edit adds a new entry. The
400-entry ring outlives transcript-row eviction and drops only its oldest
entry on overflow. Pending accepts and menus ignore both arrows. History
scroll, wheel behavior, clicks, yank, documentation sentences, the 500-row
screen limit, and the rest of the guide remain governed by their existing
specifications. The full test suite, focused headless and screen tests, and
the disposable-directory hand check pass before the series is complete.
