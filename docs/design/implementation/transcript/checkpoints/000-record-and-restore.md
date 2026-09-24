# transcript 000 — Headless record and restore

**Status.** Proposed for human review. Do not implement until accepted.

## Goal and authority

Record each completed Python form, colon command, and menu action as a new
object-bearing input presentation immediately before its effects. Provide
headless operations to yank saved Python or command input into the editor, to
insert saved input during Python composition, and to run a saved menu action
again on its original object. Keep the full automated suite passing.

- Identity is `(transcript, 000)`, spoken **transcript 000**.
- The human-reviewed [`../spec.md`](../spec.md), especially sections 1–4 and
  **Slice 1 — record and restore** in section 5, is the authority. Follow it
  wherever this checkpoint is silent. The charter is not an implementation
  input.
- Listener, listings, REPL, chips, and SymPy are implemented. Preserve their
  command grammar, exact-type accept, Python compilation and execution, chip
  splicing and cleanup, `_`, output and error order, listing redisplay, SymPy
  behavior, and existing object operations except for the added input rows.
- Work in the existing `src/pbui/` package and `tests/` at the project root.
  The headless model and tests must import without Textual. Add no dependency.

Stop after the headless model and full automated suite pass. Terminal hit
testing, click and menu wiring, documentation, hover, final bounded drawing,
screen tests, and the live hand check belong to transcript 001. Do not write
that checkpoint in this implementation turn.

## File boundary

Add one focused plain-Python transcript module under `src/pbui/` if useful for
the immutable records and headless operations. Edit `src/pbui/commands.py`,
`src/pbui/repl.py`, and `src/pbui/chips.py` for commit points and editor
restoration. Edit `src/pbui/domain.py`, `src/pbui/text.py`, or
`src/pbui/substrate.py` only as needed to register the three presentation
types and append object-bearing history rows without changing existing
presentation, listing-block, or 500-logical-row invariants. Add focused
headless tests under `tests/`; update predecessor assertions to account for
new input rows while preserving their behavioral checks. Do not edit
production `src/pbui/terminal.py`, project metadata, or dependencies.

## Records and commit points

Register distinct `PythonInput`, `CommandInput`, and `MenuActionInput`
presentation types. Each presentation value is an immutable record. Keep the
original objects by identity, not a reconstructed path, pid, representation,
or generated `_pbui_chip_N` source. Every completed attempt, including a
resubmission or replay, gets a fresh presentation. Append its history row
before any output, value, listing, or error caused by that attempt. Retain the
row when the operation produces no result. Input presentations are not
`Value` results and are inert to file, directory, process, and listing accept.

- **Python form:** Save every submitted line as ordered text runs and Python
  chips, including each chip's captured label and original object. A form
  becomes history only when `compile_command` returns code or raises a compile
  error for a finished submission. An incomplete Enter adds no row; finishing
  a continuation adds exactly one form. Append before execution or before
  its one compile `Error`. Snapshot the already assembled pieces; recording
  must not splice or compile again.
- **Colon command:** Save the raw tail after the dispatching colon, excluding
  whitespace before that colon but retaining any optional space immediately
  after it. Save an optional command chip's exact presentation type, captured
  label, and object. A typed argument stays text. Record unknown commands,
  malformed commands, and failed commands before their `Error`. If a command
  opens presentation accept or substring accept, retain what is needed to
  complete its record, but append nothing until the accepted object or
  nonempty substring makes the operation run. Cancellation adds nothing.
  `:rm` followed by a clicked file records `rm` plus that same file chip;
  `:show`, `:cd`, and `:kill` follow the same rule. A delayed `:narrow`
  records the text `narrow SUBSTRING`, not a chip or hidden listing. A bare
  colon and empty or whitespace-only input add nothing.
- **Menu action:** Save the selected label, resolved operation (the actual
  translator function where applicable), any argument, the target's original
  object, and a captured one-line target label. Append immediately before the
  action runs, including actions that yield no result or fail. Choosing
  `narrow` only enters substring accept; its nonempty completing Enter records
  the action with that substring and the selected listing. Cancellation adds
  nothing. Route existing terminal menu calls through headless recording paths
  without editing `pbui.terminal`.

Keep listing view operations as in-place redisplay of their original block.
The command or action row is appended at the end of history before that
redisplay; do not move the listing. A replayed menu action uses its saved
object and resolved operation even if the source presentation was evicted.
Apply ordinary domain revalidation. If a saved listing is no longer retained
for redisplay, append the new action row and one `Error` explaining that the
listing is no longer in history; never retarget a different listing. The
normal history capacity may evict old rows, but it must not mutate another
record.

## Headless editor and action operations

Expose headless operations that a later screen can call with an exact
retained input presentation. At an empty editor with no continuation, accept,
or menu, yanking a `PythonInput` loads all saved lines and chips without
compilation or execution: earlier lines become pending continuation lines and
the final line becomes editable. Yanking a `CommandInput` loads `:` plus its
saved tail and optional command chip. The chip still supplies its original
object through the existing exact-type command rules when Enter submits it;
an incompatible edited command follows ordinary command error handling. A
resubmission records a new input row and leaves the source row intact.

While composing Python, yanking either input inserts its saved pieces at the
cursor without replacing current work. Include the colon and text for a
command; convert its saved command chip to a Python chip with the same object
and captured label. For multiline input, join the first saved line to the
prefix before the cursor, put intermediate saved lines into pending source,
and join the last saved line to the suffix after the cursor. Treat this as
one editor change and do not compile on insertion. Preserve the existing
single-object chip insertion guard for result presentations.

Provide a headless `run again` operation for `MenuActionInput`. With an empty
editor, execute its saved operation directly on its saved object, append a
fresh action row first, then retain the usual result or error order. Never
synthesize Python source. During Python composition, selecting the action
presentation for insertion adds a Python chip of its target object at a valid
expression-atom site; it does not run the action. A menu `run again` remains
a direct operation even during composition and preserves pending pieces and
cursor. Preserve the established suspend-and-restore handling for menu
`narrow`. Open menu, presentation accept, and substring accept take priority;
input presentations are inert accept targets.

Headless history rows created here must retain presentation identity, begin
with the specified `› ` marker, and be usable for order and object tests.
The marker is drawing, never part of a saved record. Keep saved records
complete regardless of interim row length. Transcript 001 completes the
specified 120-cell and 12-row drawing limits, physical hit testing,
documentation, and screen interaction.

## Automated verification

Add headless tests without importing Textual. Use temporary roots and injected
filesystem and process services. Preserve all predecessor tests. Cover:

1. `1 + 2 + 3` records one `PythonInput` before the `Value` whose object is
   `6`. Yank restores the saved pieces and chip objects by identity without
   evaluation; Enter makes a new input row before its new result.
2. An incomplete continuation records nothing; completion records one whole
   form. A finished syntax error records that form before one `Error`.
   Empty input, a bare colon, and canceled continuation or accept add no row.
3. `:ls` records a `CommandInput` before its listing rows. Unknown, malformed,
   and failed commands record their command before one `Error`. Typed command
   arguments remain text. A `:rm` accepted by clicking a file stores and
   yanks the original command chip, not path text. A delayed `:narrow` yanks
   `:narrow SUBSTRING` as text; submitting it uses the newest listing.
4. `simplify` records a `MenuActionInput` before a new SymPy expression and
   leaves the source expression intact. `run again` adds a fresh action row
   and uses the saved original object and operation. Exercise an action after
   its source presentation leaves history and the one-`Error` path for an
   evicted listing needed for redisplay.
5. Yank and insertion preserve multiline piece boundaries, chip labels and
   object identities, pending work, and cursor. Insertion does not compile or
   execute. A command chip converted for Python insertion remains an object
   chip, and a menu-action target obeys the ordinary insertion-site refusal.

Do not claim a screen click or drawing-limit test in this checkpoint; those
belong to transcript 001.

## uv workflow and completion boundary

Use the existing uv-managed project. From the project root:

```console
uv sync
uv run pytest
```

If `uv` is unavailable, stop and report it. Do not use `pip`,
`python -m pip`, `uv pip install`, Poetry, Pipenv, Conda, Hatch, a manually
created environment, or global Python. No `uv run pbui` hand check belongs
to this headless checkpoint.

Transcript 000 is complete when all three presentation records, their commit
points, headless yank and insertion, and direct menu-action replay pass the
headless tests above and the full automated suite. Stop there.
