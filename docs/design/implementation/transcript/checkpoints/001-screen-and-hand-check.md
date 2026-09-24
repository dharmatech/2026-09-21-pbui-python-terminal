# transcript 001 — Screen interaction and hand check

**Status.** Proposed for human review. Do not implement until accepted.

## Goal and authority

Make the submitted-input presentations from transcript 000 visible and usable in
the full-screen listener. Draw bounded, marked history rows; let a fresh click
load or insert saved input, or run a saved menu action; add their one-item menus
and exact documentation. Verify the screen behavior and perform the specified
live hand check.

- Identity is `(transcript, 001)`, spoken **transcript 001**.
- The human-reviewed [`../spec.md`](../spec.md), especially sections 3–5 and
  **Slice 2 — screen**, is the authority wherever this checkpoint is silent.
  The charter is not an implementation input.
- Transcript 000 supplies immutable `PythonInput`, `CommandInput`, and
  `MenuActionInput` records, commit-point ordering, and headless `yank_input`,
  `select_for_input`, and `run_again` behavior. Its reported `uv run pytest -q`
  result was 252 passing tests. Keep those tests and all predecessor behavior.
- Work in the existing project at
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application code
  and tests stay at the project root. Only `pbui.terminal` imports Textual.
  Add no dependency.

Stop when the full automated suite passes and the real-terminal hand check is
observed. Do not add another feature slice or write another checkpoint.

## File boundary

Edit `src/pbui/transcript.py` for pure, bounded history-row drawing and
`src/pbui/terminal.py` for screen routing, menus, documentation, editor repaint,
and hit testing. A narrow pure display-cell helper in `src/pbui/text.py` is
allowed if the existing helpers cannot split long input lines without breaking
wide or combining characters. Add focused drawing tests to
`tests/test_transcript.py` and screen tests to `tests/test_terminal.py`. Make a
small change to `src/pbui/commands.py` only if the screen exposes a concrete
headless interface defect, with a focused regression test; preserve transcript
000's records and commit points. Do not change command grammar, domain
operations, evaluator semantics, history retention, project metadata, or
dependencies. Do not edit the accepted spec or checkpoint 000.

The terminal already has `HistorySurface`, a pure `Layout`, `ActionMenu`,
`DocumentationLine`, and an editor widget named `CommandInput`. Reuse these
surfaces. The editor widget's name is distinct from the saved `CommandInput`
record. Do not add a second history renderer, menu, or input model.

## Bounded history drawing

Every logical input row begins with the single character `›` followed by one
space. This marker is drawing only and uses two of the row's display cells;
it is absent from saved Python source and command text. Escape unsafe text by
the existing safe-display rules. Draw saved Python chips as `⟨LABEL⟩` and a
saved command chip as `⟨TYPE: LABEL⟩`, preserving their captured editor labels
and objects rather than regenerating either from a value. A command shows its
colon: `› :ls`, `› :ls /tmp`, or `› :rm ⟨File: /tmp/a⟩`. A menu action shows
its label, ` — `, and the captured one-line target text. Show a completed
menu `narrow` substring after its label. Cap the drawn target label at 96
display cells without shortening the saved target or argument.

For a Python form, preserve each source newline as a new logical history row;
do not draw a literal `\n` in its place. Split a long displayed source line
into logical rows of at most 120 display cells, including each `› ` marker.
Count wide and combining characters by display cells and keep their drawing
intact. Draw at most 12 logical rows for one form. If more would be needed,
show the first 11 and a twelfth row exactly `› … (N more input rows)`, with
`N` equal to the omitted logical-row count. Every visible row, including the
omission marker, belongs to the same saved presentation. Clicking any row
must address the whole original form.

A colon command and a menu action each occupy exactly one logical row. Cap
each complete drawn row at 120 display cells including `› `; if longer, keep
the first 119 display cells and end with `…`. Apply this row cap after
assembling the saved command chip label or the menu's 96-cell target label.
Never truncate the immutable input record. Yank and `run again` use its full
text, chips, substring, function, and object. Every drawn input row counts
toward the existing 500-logical-row history limit. The viewport may wrap a
logical row further at terminal width; every physical segment still
hit-tests to the original input presentation.

## Click, editor, and menu routing

Use a fresh innermost hit at the event coordinate and only the first left
click in a chain. An open menu handles its own click first. Presentation
accept and substring accept handle theirs next, with the existing exact-type
rules and cancellation. Input presentations are inert accept targets. Keep
Ctrl-O and button 3 opening the menu of the fresh hit when menus are allowed.
Python composition keeps ordinary reverse-video hover, not accept-target
styling. Preserve the listener 005 row-local hover rule when these new
presentations span several physical rows.

At a genuinely empty editor with no continuation, accept, or menu, a left
click on `PythonInput` calls the headless yank path and loads every saved line
and chip without running it. Earlier lines become pending continuation lines;
the final line is editable with the correct prompt and cursor. A click on
`CommandInput` loads its colon, exact tail, and optional command chip. The
screen must repaint the editor and cursor immediately. Enter is the only
submission action, and it creates a new input row before new effects. The
source presentation stays in history.

During Python composition, a left click on `PythonInput` or `CommandInput`
uses the headless insertion path at the current cursor. It preserves typed
text and pending source, joins multiline pieces as specified, and does not
compile or execute on click. A command chip becomes a Python chip of the same
saved object and label. Ordinary result presentations keep their existing
single-object insertion and expression-atom guard. Clicking a
`MenuActionInput` during composition inserts a Python chip of its target only
at a valid site; refusal at an invalid site leaves input unchanged. At an
empty editor, clicking that action row calls `run_again`, appends a new action
row, then performs the saved operation directly on its saved object. Preserve
scroll/reveal behavior for appended rows and in-place listing redisplay.

The `PythonInput` and `CommandInput` action menus each have exactly one item,
`yank`. It loads at an empty editor or inserts at the cursor during Python
composition. The `MenuActionInput` menu has exactly one item, `run again`.
That item executes the saved action directly, including during composition;
it preserves pending pieces and cursor. A completed saved menu `narrow` uses
its saved substring and listing. Keep the current menu-first outside-click,
close, cancellation, stale-target, and viewport behavior. Choosing a new
listing header `narrow` still uses its existing suspend-and-restore substring
accept; do not turn the saved action into Python source.

## Exact documentation

With no higher-priority modal state, use these exact sentences for a hovered
history input presentation:

| Target and editor mode | Sentence |
|---|---|
| Python form, empty editor | `Click to load this Python form into the editor; Enter runs it.` |
| Colon command, empty editor | `Click to load this command into the editor; Enter runs it.` |
| Menu action, empty editor | `Click to run “LABEL” again on the same object.` |
| Python form or colon command, composing Python | `Click to insert this input at the cursor.` |
| Menu action, composing Python at a valid chip site | `Click to insert this action's target into the expression.` |

Replace `LABEL` with the captured action label. At an invalid site for a
menu-action target chip, use the chips specification's exact string/comment
or other invalid-site sentence. While an input menu item is hovered, show
`Click to yank this input into the editor.` While the action's menu item is
hovered, show `Click to run “LABEL” again on the same object.` An open menu,
presentation accept, substring accept, continuation with no target, and
no-target documentation keep their existing precedence. Recompute the
sentence when editor mode, cursor, or text changes without pointer movement.
Keep the fixed one-row documentation surface and its display-cell truncation.

## Automated verification

Keep the full predecessor suite, including transcript 000 and listener 005,
without deleting or weakening assertions. Add pure drawing tests and focused
`PbuiApp.run_test()` tests with injected services and temporary roots:

1. `› 1 + 2 + 3` appears in full above `6`; `› :ls` appears before its
   listing; a `simplify` action appears before the new symbolic result while
   the source expression remains. Verify each history row's presentation
   type, stored object, and ordering, not text alone.
2. Python source newlines, long lines, unsafe characters, wide and combining
   characters, and chip labels draw safely within 120 display cells. A form
   needing more than 12 rows shows 11 plus the exact omission row and count.
   All visible logical rows and their narrower-screen physical wraps hit the
   same presentation. Clicking any row, including the omission row, yanks the
   complete untruncated lines and original chip objects.
3. Long colon and menu rows remain one logical row, end in `…` within 120
   cells, and preserve full saved records. Test a typed command argument and
   a clicked `:rm` file chip separately. Clicking or menu-yanking the latter
   restores `:rm` and the same command chip, not path text. A delayed
   `:narrow` restores `:narrow SUBSTRING` as text.
4. Empty-editor left click loads Python or command input without evaluation;
   editing and Enter add a fresh input row. During Python composition, left
   click and menu `yank` insert at the cursor, preserving surrounding text,
   multiline pending pieces, chip objects, and cursor. A clicked menu-action
   row inserts only its target chip at a valid site. Invalid sites retain the
   existing refusal and do not run the action.
5. Empty-editor action click and menu `run again` create new action rows and
   execute the saved operation on its original object. Cover a saved menu
   `narrow` substring/listing, a retained listing redisplayed in place, and
   the existing one-`Error` path when that listing is no longer retained.
   Exercise action menus during composition without moving the editor cursor.
6. Assert every exact documentation sentence above, both menu-item sentences,
   invalid-site wording, and modal/no-target precedence. Move editor mode or
   cursor with a stationary pointer and verify the line changes. Test first
   click versus later click in a chain, Ctrl-O and button 3 where supported,
   accept inertness, wrap, scroll, resize, and row-local hover: only physical
   rows of the presentations left and entered may be rebuilt.

Automated tests must not require a network, real process signaling, or a
physical terminal. Use disposable files only inside test roots. The headless
model and pure drawing tests must still import without Textual.

## Live hand check

After the automated gate, create one fresh disposable directory beneath the
project root, record its absolute path, and run `uv run pbui` from that
directory in a real interactive terminal. Confirm the prompt shows the
recorded directory. Do not substitute `run_test()` for this check. Observe:

1. Enter `1 + 2 + 3`; see its marked form above the displayed `6`. Click the
   form at an empty editor. Confirm it loads without running, edit it, press
   Enter, and see a second form before the new result.
2. Enter `:ls`; see its marked command above the listing. Click the command
   at an empty editor and confirm `:ls` loads without listing again until
   Enter. Keep all operations in the disposable directory.
3. Enter `import sympy`, bind a symbol, and display a SymPy expression such
   as `sympy.sin(x)**2 + sympy.cos(x)**2`. Use its action menu to apply
   `simplify`. See a marked action row above the new expression while the
   original expression row remains. At an empty editor, click the action row
   and confirm a new action row and result appear.

Record the terminal used, absolute disposable directory path, automated test
count, observations, and any unavailable or failed step. If a real usable
terminal is unavailable, report the hand check as unverified and state the
limitation; do not claim a mocked screen test passed it. No destructive
command is needed.

## uv workflow and completion boundary

Use the existing uv-managed project. From the project root:

```console
uv sync
uv run pytest
```

The full suite must pass before the hand check. Run only `uv run pbui` for the
live program. If `uv` is unavailable, stop and report it; do not switch to
`pip`, `python -m pip`, `uv pip install`, Poetry, Pipenv, Conda, Hatch, a
manually created environment, or global Python.

Transcript 001 is complete only when the bounded rows, hit testing, clicks,
menus, documentation, and preservation regressions pass the full suite and
the live check is observed. If a mandatory hand-check step is unavailable,
report the checkpoint as unverified with its exact limitation. Stop there.
Pandas, in-place history editing, new SymPy operations or pretty-printing,
a second thread, recording non-submitting keys, and generated-source action
replay remain outside this checkpoint.
