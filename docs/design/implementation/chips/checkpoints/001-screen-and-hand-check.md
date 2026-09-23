# chips 001 — Screen interaction and live hand check

**Status.** Ready to implement.

## Goal

Connect the chips 000 headless Python line to the full-screen listener. Draw
object chips and an atomic cursor in the one-row editor, insert retained
history objects through first left clicks, explain valid and refused clicks on
the documentation line, and keep menus and continuation working together.
Verify the finished chips exploration with the full automated suite and one
real terminal session.

This is the second and final slice of the chips specification. Stop after its
automated and live checks; do not start the SymPy or pandas exploration.

## Identity, authority, and starting point

- Identity is `(chips, 001)`, spoken **chips 001**.
- The human-reviewed [`../spec.md`](../spec.md), especially sections 2–5 and
  **Slice 2 — screen** in section 6, is the authority. Follow it where this
  checkpoint is silent. The charter is not an implementation input.
- [`000-headless-pieces-and-splicing.md`](000-headless-pieces-and-splicing.md)
  supplied `PythonLine`, `PythonChip`, insertion-site validation, object
  capture, continuation pieces, and temporary execution bindings. The user
  reported `uv sync` and a full **233-test** pass. Run this checkpoint's gate
  again; that report is not verification of the screen work.
- Listener 000–005, listings 000–008, and repl 000–001 remain accepted.
  Preserve their command effects and accept types, menu contents, listing
  redisplay, viewport anchoring, history retention, row-local hover,
  synchronous execution, and terminal restoration.
- Work in the existing project at
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application
  code and tests stay at the project root, never under `docs/`.

## File and feature boundary

Edit `src/pbui/terminal.py` for screen routing, editor drawing and keys,
documentation, menu interaction, and the terminal lifecycle. Edit
`src/pbui/commands.py`, `src/pbui/chips.py`, or `src/pbui/repl.py` only for
small headless seams needed to classify insertion-site refusals, synchronize
the Python cursor, and suspend and restore Python input while the existing
menu `narrow` action borrows the editor. Keep the pieces, stored object,
continuation, and namespace in the headless model rather than a Textual
widget. Add focused regression tests in `tests/test_terminal.py` and, for a
headless seam, `tests/test_chips.py` or `tests/test_repl.py`.

Do not edit `src/pbui/domain.py`, `src/pbui/substrate.py`, `src/pbui/text.py`,
other production modules, project metadata, dependencies, the accepted spec,
or previous checkpoints. Do not create a second editor, history surface,
menu system, command chip, evaluator thread, or Python syntax. Only
`pbui.terminal` imports Textual. Preserve the ten listener commands behind
their leading colon and the existing command-argument `Chip` path. If a
headless seam needs more than the small changes above, return this checkpoint
for correction before widening its scope.

## One-row editor and submission

For Python composition, the chips 000 `PythonLine` is the authoritative
editable line and cursor. Render text runs in order and each `PythonChip` as
`⟨LABEL⟩`, using its captured label. The brackets and label are display only:
neither the editor nor Enter may submit or reconstruct them as Python source.
Keep the existing horizontal crop, safe display, focus cursor, and one-row
height on narrow screens. The visual cursor marks a boundary between text
characters or whole chips and never enters a chip label. Left and Right
cross one chip at a time; Home and End reach line boundaries. Text typing and
one-row paste insert at the model cursor; Backspace after a chip and Delete
before one remove that whole chip. Redraw immediately after every edit and
history insertion, including at a cursor in the middle of text.

Keep the existing command and substring-accept editor path for their text
buffer and optional command chip. A chip-free line may change between Python,
colon-command, and empty-prompt mode as its text changes. Keep screen and
headless cursors aligned across those transitions and after deleting the last
Python chip. Do not use `set_input_text` or `submit(text)` in a way that erases
Python pieces: on Python Enter, submit the current pieces through the
headless no-argument submission path. Command Enter retains its existing
parser and accept path. A line containing a Python chip stays Python even if
its text begins with `:`; a chip-free colon command cannot gain a Python
chip by click.

On incomplete Python, show `...> `, retain all pending pieces headlessly, and
start a clear editable line. Draw only the current line in the editor. A
blank or colon-starting continuation line remains Python. On execution or
compile failure, return to the ordinary cwd prompt with cleared pieces.
Ctrl-G or Escape with no menu or substring accept open discards a continuation
and current line without executing it. An ordinary chip-bearing line is
cleared by the existing input cancellation keys. Keep Ctrl-C exit and
terminal restoration behavior.

## Clicks, documentation, and hover

Resolve a fresh innermost history hit from the event coordinate. Only a first
left click (`button == 1`, `chain == 1`) may insert; later clicks in a chain,
literal fields, and empty space do not insert. Route an open menu first, then
presentation accept or substring accept, then Python composition, then the
ordinary default click. Use the headless `select_for_input` path for the
selection: it already enforces command/empty-line precedence and captures
the clicked presentation's stored object. A refused Python insertion leaves
the line, cursor, history, and namespace unchanged and must not fall through
to `show`. An empty or whitespace-only ordinary prompt still invokes default
`show` on `File`, `Directory`, `Process`, or `Value`; chip-free `:rm` still
accepts only its exact `File` target.

When Python composition is active, a retained presentation is under the
pointer, and insertion is valid at the current cursor, show exactly:

```text
Click to insert this value into the expression.
```

For a cursor inside a string or comment, including an unclosed string, show:

```text
This value would be literal text here; move the cursor outside the string or comment.
```

For another invalid insertion site, show:

```text
Move the cursor to a Python expression position to insert this value.
```

Use the same headless insertion-site decision for the actual click and the
documentation; expose a reason from that model if needed, without a second
Python parser in the terminal module. The rules apply during continuation
and on a line containing only a chip. An open menu, presentation accept, or
substring accept keeps its own higher-priority documentation. With no
presentation under the pointer, use the ordinary no-target sentence, except
that continuation keeps its established continuation sentence. A chip-free
colon command or ordinary empty prompt retains the current default-click
wording. Recompute documentation when editor mode, cursor, or text changes
even if the pointer is stationary. Keep the mounted one-row documentation
surface and display-cell truncation.

Python composition uses ordinary reverse-video history hover, never command
accept green/underline or inert gray. True command accept keeps its exact
highlighting. Preserve the listener 005 regression: moving history hover
restyles only the physical rows left and entered, without rebuilding all
history rows.

## Menus, suspension, and cancellation priority

Ctrl-O for the fresh hovered presentation and mouse button 3 at a fresh hit
coordinate may open the existing action menu during Python composition,
including continuation. They never insert a chip. Presentation accept and
substring accept still block menu opening. Keep each target's current menu
items, order, refusal sentences, actions, and viewport behavior. A menu
action executes directly and preserves the Python line, pending pieces, and
cursor; do not move a composing cursor to the end after an action. Closing a
menu or clicking outside it likewise preserves that input.

The open menu wins over continuation for clicks, Ctrl-G, Escape, and Ctrl-D.
The first cancellation or Ctrl-D closes only the menu; a later Ctrl-G,
Escape, or Ctrl-D may discard the continuation under the rules above. Ctrl-D
at a chip-bearing ordinary line cannot exit. With no menu, Ctrl-D during a
continuation discards pending and current pieces without execution or exit.
At an ordinary empty prompt it retains the REPL's exit behavior.

The header-menu `narrow` action enters the existing textual substring
accept for that exact listing. Suspend pending Python lines, current pieces,
and cursor headlessly before the existing accept clears its input buffer.
While it owns the editor, draw the ordinary pbui prompt and noneditable
`narrow ` prefix with an initially empty substring, and route typed text and
Enter only to substring accept. Empty Enter keeps waiting; nonempty Enter
applies `narrow`. On completion or Ctrl-G/Escape cancellation, restore the
suspended Python lines, pieces, cursor, and editor focus exactly, whether or
not the listing changed. History clicks cannot insert during substring
accept. A saved continuation is suspended for key routing: Ctrl-D cannot
exit or discard it while substring accept is active. Typed `:narrow` on a
colon command line keeps its existing behavior.

## Automated tests

Run the full predecessor suite without weakening assertions. Add focused
`PbuiApp.run_test()` tests using injected services and temporary roots:

1. Click a retained `Value` into the middle of an expression and assert its
   stored object reaches Python, its captured `⟨LABEL⟩` draws once, the
   visual cursor is immediately after the whole chip, text and one-row paste
   work on both sides, and Backspace/Delete remove the whole chip. Verify
   narrow-screen crop and that a second event is not needed to repaint.
2. Click during continuation, then complete the expression. Prove the
   pending pieces are not redrawn in the one-row editor. Test empty-prompt
   `show`, a chip-free `:rm` accept consuming a `File`, `:` typed before an
   existing chip remaining Python, and no insertion on a literal field or
   later click in a chain.
3. Move the cursor between valid, string/comment, and other invalid sites
   under a stationary history pointer. Assert all three exact documentation
   sentences, unchanged state and no default `show` on refusal, ordinary
   no-target and continuation wording, and command/accept documentation
   priority. Check ordinary hover and the listener 005 row-local regression.
4. Open menus by Ctrl-O and button 3 during composition and continuation;
   run a harmless action and prove pieces and cursor survive. Test outside
   click, Ctrl-G, Escape, and menu-first Ctrl-D, followed by continuation
   cancellation. Existing accept modes must still block menu opening.
5. Choose a listing header's `narrow` item while a Python continuation and
   chip-bearing current line exist. Check its ordinary prompt, prefix,
   empty Enter, blocked chip clicks and Ctrl-D, then complete it and verify
   exact restoration of pending lines, current pieces, cursor, and focus.
   Repeat for Ctrl-G and Escape cancellation, and keep typed `:narrow`
   behavior covered.

Keep tests independent of SymPy, pandas, network access, live process
signaling, and a physical terminal. A small headless test may exercise any
new suspension or refusal-reason seam.

## Live hand check

After `uv run pytest`, launch `uv run pbui` in a real interactive terminal
from one fresh disposable directory beneath the project root. Record that
directory's absolute path and verify the prompt shows it before any command
with destructive effects. If a usable terminal is unavailable, report the
checkpoint as unverified rather than replacing this check with `run_test()`.

Observe and record these checks:

1. Run `:ls` to show the disposable directory's entries. At an empty prompt,
   click a file or directory row and confirm its normal `show` detail appears.
2. Evaluate `1 + 1`, then type `10 + ` and click the displayed numeric
   `Value`; Enter must display `12`, demonstrating insertion of the earlier
   object rather than its row label.
3. Bind `v = object()`, then evaluate `v` to display its `Value` row. Type
   `id(`, click that row, type `) == id(v)`, and press Enter. The result must
   be `True` although the object's `repr` is not valid Python source.
4. Start another expression, click a value chip, and press Backspace just
   after it. The whole chip disappears in one action; the surrounding text
   remains. Confirm `:ls` still lists normally afterward.

The hand check needs no `rm` or `kill`. Record the absolute directory path,
terminal used, automated test count, observations, and any unavailable or
failed step. Do not claim an unobserved check passed.

## uv workflow and completion boundary

Use only the existing uv-managed project. Add no dependency. From the
project root run:

```console
uv sync
uv run pytest
```

`uv run pytest` is the automated gate. Then run `uv run pbui` from the
verified disposable directory for the hand check. Do not use `pip`,
`python -m pip`, `uv pip install`, Poetry, Pipenv, Conda, Hatch, a hand-made
environment, or global Python. If uv is unavailable, stop and report it.

Chips 001 is complete only when the full suite passes and all mandatory live
checks are observed. If a mandatory live check is unavailable, report the
checkpoint as unverified with its exact limitation. Stop after reporting;
do not add SymPy, pandas, printers, menus, Python completion, dragging,
another syntax, or another evaluation thread.
