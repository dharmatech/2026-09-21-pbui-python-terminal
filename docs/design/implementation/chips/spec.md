# Specification — history objects in Python input

**Status:** accepted and implemented through chips 001. This is the complete
design input for the chips checkpoint series. Checkpoints belong in this directory's
`checkpoints/`, beginning with **chips 000**. This document assigns no
implementation work.

A left click while composing Python inserts the clicked history object's value
at the editor cursor. The input displays an atomic chip; evaluation receives
the stored object, never Python reconstructed from the chip's label.

## 1. Authority and boundary

This specification extends the accepted [listener](../listener/spec.md),
[listings](../listings/spec.md), and [REPL](../repl/spec.md) specifications.
It supersedes the REPL introduction's statement that Python source has no
chip, section 2's treatment of ordinary Python input as text only, section
3's string-only pending source, and sections 3 and 6's prohibition on menus
during continuation. Listener sections 3.4, 5.1, and 6.1–6.4 and listings
sections 5–6 gain the Python-composition click and editor behavior below.
Their command chip, exact-type accept, command effects, history, table,
viewport, and menu rules otherwise remain in force.

The existing Linux `pbui` project remains the product. Keep the ten listener
commands behind their leading colon, the single command-argument `Chip` in
`SubstrateState`, the `Value` type and class registration hook, `_`, the
500-logical-row history limit, the one-row editor, and synchronous Python
evaluation. Python input chips are a separate model; never put one in
`SubstrateState.chip` or pass it through a command parser. Use the existing
`src/pbui/` package and `tests/`. The model and evaluator remain headless;
only `pbui.terminal` imports Textual. No new dependency is expected.
Implementers use `uv sync`, `uv run pytest`, and, for the screen hand check,
`uv run pbui`. If uv is unavailable, stop and report it.

## 2. Click routing and mode

Resolve a fresh innermost hit at the click coordinate. A click on a literal
field or empty space has no object to insert. Only a first left click
(`button == 1`, `chain == 1`) can insert; later clicks in a chain do nothing.
Route it in this order:

1. An open action menu handles the click. A pending presentation accept or
   substring accept handles its own clicks next, with today's exact-type
   acceptance, inert targets, cancellation, and command chip behavior.
2. Otherwise, insert the hit presentation into Python input if a Python
   continuation is open, or if the editable line is Python composition as
   defined below.
3. Otherwise, keep the existing default click: `File`, `Directory`,
   `Process`, and `Value` run their current `show` branch; other history
   presentations have no default action. An empty or whitespace-only ordinary
   prompt belongs here, so a left click still shows the object.

A click routed to Python composition at an invalid insertion site is refused;
it does not fall through to the default `show` action.

With no continuation, a line containing any Python chip is Python composition,
even when its text is empty or begins with `:`. With no chip, strip leading
whitespace from its text for this decision: a first `:` makes it a colon
command; non-whitespace text with any other first character makes it Python
composition; empty or whitespace-only text is the ordinary empty prompt.
Changing the text can change this mode immediately. For example, typing `:`
at the start of a chip-free Python line makes it a command line; typing `:`
before an existing Python chip leaves the line Python. Removing the last chip
from such a line lets its text determine the mode again. A colon command line
never gains a Python chip from a click. During continuation, every line is
Python, including one beginning with `:`.

A click that inserts accepts any retained history presentation with a stored
value, including `Value`, domain members, listing headers, `Text`, and `Error`.
The clicked presentation's exact type is irrelevant to Python insertion.
This does not enlarge any listener command's accept set. Its current value is
captured by object identity at the click. A later history edit or eviction
cannot retarget or remove the chip. The object's own mutable state may of
course change as normal Python state.

Ctrl-O and mouse button 3 still open the hit object's existing action menu
while composing Python, including during continuation; they never insert a
chip. Menu availability, contents, actions, and refusal sentences remain as
specified for each type. A menu action executes directly and keeps the Python
pieces intact. The open menu's click, Ctrl-G, and Escape handling wins:
the first cancellation closes only that menu; a later cancellation may
discard the continuation. This replaces the REPL's continuation-era menu
ban. Presentation accept and substring accept still block menu opening.

A menu `narrow` action borrows the editor. Suspend the pending Python lines,
current pieces, and cursor position exactly; close the menu and enter the
existing substring accept for the selected listing. Show its ordinary pbui
prompt and noneditable `narrow ` prefix, with an empty substring buffer.
The substring is never Python source. An empty Enter keeps waiting; a
nonempty Enter applies `narrow`. On completion or Ctrl-G/Escape cancellation,
restore the suspended Python lines, pieces, cursor, and editor focus exactly,
regardless of whether the listing changed. While substring accept is pending,
history clicks do not insert Python chips. Typed `:narrow` on a command line
retains its existing path.
While substring accept owns the editor, a saved continuation is suspended
for key routing. Ctrl-D cannot exit or discard the saved Python pieces.

## 3. Python pieces and editor

Represent the current Python line and each pending continuation line as an
ordered sequence of text runs and Python chips. A Python chip contains the
clicked presentation's stored object and a captured display label. It is one
atom. Adjacent text runs may be merged; empty runs need not be stored. Source
text is exactly the text runs, in order, with a chip position between them.
The command line remains its existing text buffer plus at most one command
chip; do not change its editor path.

Use `⟨LABEL⟩` for a Python chip. At insertion, take the one-line logical
history text associated with the innermost hit presentation as currently
drawn (the complete member row for a listing member), then cut it to at
most **32 display cells** using the existing
safe-display truncation and `…`. A short, one-token history label is shown
in full. Capture this label once; subsequent redisplay does not rewrite
it. The brackets and label are display only and are never put into Python
source or evaluated. Drawing stays on the editor's single row and uses its
existing horizontal crop on narrow screens.

The cursor denotes a boundary between characters or chips. Left and Right
cross a chip in one move, Home and End reach the first and last boundary, and
the cursor never lands inside the brackets or label. Typing or one-row paste
inserts text at that boundary. A left click on history inserts its chip at the
current cursor and leaves the cursor immediately after it, splitting a text
run if necessary. Backspace just after a chip removes that whole chip; Delete
just before one does the same. In a text run those keys remove one character
as today. Other editor keys and paste filtering retain their existing rules.
The rendered cursor and edited text must reflect every chip insertion or
deletion without requiring a second event.

### Insertion site

A chip must splice as a standalone Python identifier used as an expression
atom. Decide from the pending lines and current line together, treating
existing chips as identifier atoms. Refuse a click when the cursor is inside
a string literal or comment, including an unclosed or multiline string, or
when the inserted name would merge with another token or occupy a grammar
position other than an expression atom. Thus `f(|)` and `x = |` allow a chip;
`fo|o`, `12|3`, `obj.|`, `import |`, and `def |` do not (`|` marks the
cursor). Refuse a chip throughout an f-string literal, including its
replacement fields. An incomplete expression such as `f(` remains a valid
insertion site after `(`. Use Python lexical rules for the boundary check;
do not call `compile_command` on a click. Refusal leaves pieces, cursor,
pending source, and namespace unchanged.

Each Python Enter takes the already-pending lines plus the editable line just
submitted, with exactly one newline between lines. Construct that combined
sequence once and compile it once through the splice in section 4. Do not
append or walk the submitted line a second time for the same Enter. On an
incomplete compile, retain the whole original sequence as pending source,
clear the editable line, and show `...> `. Only the new line is drawn in the
one-row editor; pending lines are not redrawn there. On successful execution
or a compile/execution failure, clear all pending and current pieces and
return to the ordinary prompt. When no menu or substring accept is active,
Ctrl-G and Escape discard the continuation and current line without
execution, namespace changes, or history rows.
Ctrl-D follows menu priority: if a menu is open, its first press only closes
the menu. Otherwise, if a continuation is open, it discards that continuation
and the current line, chips included, without running them or exiting. A
Python chip makes the editable line nonempty, so Ctrl-D cannot exit in that
state. Ctrl-C retains its existing exit behavior. An ordinary chip-bearing
line can also be cleared by the existing input cancellation keys.

## 4. Splicing and execution

On each Python Enter, construct and splice the combined sequence from section 3
once, in source order. Copy each text run verbatim and replace each chip
occurrence with a Python identifier `_pbui_chip_N`. Choose fresh numbers for
every occurrence, starting at zero and increasing. Skip a candidate only if
its exact spelling appears as a whole Python identifier in a text run or is
already a key in the listener namespace. Apply Python identifier boundaries
even inside strings and comments: `_pbui_chip_0` there collides, while
`_pbui_chip_0` inside `_pbui_chip_01` or `x_pbui_chip_0` does not. Thus user
text and prior bindings cannot collide with an injected name. Keep a mapping
from each chosen name to that occurrence's stored object. Two chips containing
the same object receive two names and both names refer to that same object.
For example, in `f(⟨x⟩, ⟨x⟩)`, `f` receives the original object twice by
identity.

Call `code.compile_command(source, symbol="single")` exactly once for this
Enter, using the spliced string as `source`. A later Enter necessarily uses
the earlier pending lines in its new combined sequence. If compilation is
incomplete, retain the original pieces, not the generated identifiers. If
compilation raises one of the REPL-specified compile errors, append its one
`Error`, clear the pieces, and introduce no bindings. Once compilation
succeeds, bind the mapping's names directly to the stored objects in the
REPL namespace for that execution only.
Run the existing `exec` path with its temporary display hook, stdout/stderr
capture, tracebacks, and value history. In `finally`, remove every name that
this splice added, even if execution raises, calls `SystemExit`, or reassigns
one of those names indirectly. A name that existed before the splice was
skipped and must remain untouched. User source bindings outside the selected
synthetic names persist exactly as the REPL specifies. No label is passed to
`eval`, a parser, or a command.

The REPL's `_` rule is unchanged: only a displayed non-`None` value updates it,
and an earlier displayed value survives a later exception. Source errors,
stdout/stderr order, and stream/hook restoration keep the REPL contract. In
particular, a chip whose label or object's `repr` is not usable Python must
still reach a function as the original object.

## 5. Documentation and styling

While Python composition is active, a retained presentation is under the
pointer, and the cursor is at a valid expression-atom site, the documentation
line is exactly:

```text
Click to insert this value into the expression.
```

If the cursor is inside a string or comment, including an unclosed string,
the exact sentence is:

```text
This value would be literal text here; move the cursor outside the string or comment.
```

At another invalid insertion site, the exact sentence is:

```text
Move the cursor to a Python expression position to insert this value.
```

These rules include a continuation and a line containing only a chip. An open
menu, presentation accept, or substring accept keeps its own higher-priority
documentation. With no presentation under the pointer, the ordinary
no-target sentence applies; during a continuation it is the REPL's
continuation sentence. A chip-free colon command or empty ordinary prompt
keeps today's documentation, including the default `show` wording. Recompute
documentation when the editor mode, cursor, or text changes even if the
pointer has not moved. History hover uses ordinary reverse-video hover
during Python composition, never accept-target green/underline or inert gray.
True command accept retains its existing highlighting. Do not change history
row colors, menu styling, hit testing, or row-local hover updates.

## 6. Verification and slice order

Keep existing tests passing. Headless tests use injected services and
temporary roots, without Textual, SymPy, pandas, or a network. The complete
automated gate is `uv run pytest`.

**Slice 1 — pieces and splicing.** Build the headless piece/cursor operations,
insertion and refusal, deletion, continuation joining, fresh-name splice,
and temporary execution bindings. Tests prove middle-of-run insertion and
editing on both sides; whole-chip Backspace/Delete; multiple chips and
separate continuation lines; exactly one compile per Enter with the submitted
line present once; an object with unusable `repr` passed by identity; and
`f(CHIP, CHIP)` passing the same object twice. Test whole-identifier
collisions in source, strings, comments, and namespace keys, with no
collision for `_pbui_chip_01` or `x_pbui_chip_0`; cleanup after success,
compile failure, execution failure, and indirect synthetic-name reassignment;
preservation of user bindings and `_`; command/empty-line and accept
precedence; and accepted `f(|)` versus refused strings, comments, unclosed
strings, merged tokens, and non-expression positions. This slice imports
no Textual code.

**Slice 2 — screen.** Draw the chip and atomic cursor in the one-row editor;
route click insertion and menus; update the exact documentation sentences and
ordinary hover. Screen tests cover a click in the middle of an expression,
clicking during continuation, an empty-prompt click that still shows, a
chip-free `:rm` command accept that still receives a `File`, and `:` before
a chip staying Python. Also cover Ctrl-O/button 3 during composition,
menu-first Ctrl-D, `narrow` restoring suspended Python pieces and cursor after
completion or cancellation, refusal and documentation inside a string or
comment, and whole-chip Backspace. Preserve the listener 005 row-local hover
regression. After `uv run pytest`, run `uv run pbui` from a fresh disposable
directory under the project root and record its absolute path. Hand-check an
empty-prompt `show`, a prior numeric value inserted into an expression, an
object whose `repr` is invalid Python arriving intact, `:ls`, and whole-chip
Backspace. For the invalid-`repr` check, bind `v = object()`, display `v`,
type `id(`, click its Value row, and type `) == id(v)`; the result must be
`True`. Verify the prompt path before any destructive action; the hand check
needs no `rm` or `kill`.

The human reviews this specification before a checkpoint manager writes
**chips 000**. Do not add SymPy, pandas, new printers or menus, Python name
completion, dragging or editing labels, chips inside colon commands, another
Python syntax, or a second evaluation thread.
