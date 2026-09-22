# listener 005 — History drawing

**Status.** Ready to implement.

## Goal

Correct the terminal history drawing path so every physical layout row owns a
Rich `Text` built directly from that row, rather than being sliced out of one
history-wide `Text`. On a hover transition, redraw only the physical rows
occupied by the presentation being left and the presentation being entered.

Add the structural history-drawing regression required by specification
section 7.6. It uses hundreds of injected process rows with long command lines
and proves the hover work by row identity and/or instrumentation, never by
elapsed time.

This checkpoint corrects drawing only. It adds no command or product behavior.
Stop when the automated suite passes; do not begin another listener change.

## Identity, authority, and predecessors

- Identity is `(listener, 005)`, spoken **listener 005**.
- [`../spec.md`](../spec.md), especially sections 6 and 7.6, is the authority.
  Preserve the rest of that specification when this checkpoint is silent.
- Listener 000 through listener 004 are implemented and reviewed. All 101
  existing tests pass.
- The statement in listener 004 that it was the final checkpoint is superseded
  only by the amended specification and this narrowly scoped correction.
- Listener 003 supplied the passive layout and drawing surface. Listener 004
  activated its pointer, accept, scroll, resize, and lifecycle behavior. Rework
  that existing `HistorySurface`; do not create a second history renderer or
  coordinate model.
- The project root is
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application code
  and tests remain there, never under `docs/`.

## Exact file scope

### May edit

- `src/pbui/terminal.py`
- `tests/test_terminal.py`

### Must not edit or create

- `.python-version`, `pyproject.toml`, `uv.lock`, `README.md`, or `AGENTS.md`
- `src/pbui/__init__.py` or `src/pbui/__main__.py`
- `src/pbui/substrate.py`, `src/pbui/text.py`, `src/pbui/domain.py`,
  `src/pbui/commands.py`, or any of their tests
- another production module or test module
- a dependency, console entry point, command, or other product behavior
- anything under `docs/`, including this checkpoint, earlier checkpoints, and
  the specification
- any file outside the project root

If the correction appears to require a predecessor layer, process service, or
new dependency, stop and return the checkpoint for correction instead of
widening the slice.

## Preserved behavior and data

This is not a process, layout, or interaction redesign. Preserve all of the
following exactly:

- process enumeration and the injected `LinuxProcessService` seam;
- the command text stored and drawn for every process, without truncation,
  abbreviation, normalization, caching, or replacement;
- the 500-logical-row default history-retention limit and its existing drop
  behavior;
- pure-layout wrapping, fragment identity, presentations, display intervals,
  nesting depth, draw order, and `Layout.hit_test` results;
- display-cell hit testing, including wide and combining characters;
- hover, accept, documentation, click, editor, scrolling, resize anchoring,
  entry-point, and exit behavior;
- the exact normal, error, hovered, acceptable-target, and inert-target visual
  treatments from specification section 6.3; and
- the existing `build_history_text` behavior used by the reviewed tests, if
  that compatibility helper remains part of `pbui.terminal`.

Do not solve the drawing cost by changing what `ps` returns, by reading fewer
processes, by shortening command lines, by lowering retention, by changing hit
testing, or by virtualizing away retained model rows.

## Direct physical-row construction

The current pure `Layout` remains the complete source of drawing text and
presentation intervals. For each physical row at index `physical_row`:

1. Create a new Rich `Text` directly from
   `current_layout.rows[physical_row].text`, with the reviewed literal-text,
   no-wrap, and crop behavior.
2. Select only presentation intervals whose `physical_row` equals that row.
3. Apply styles in the existing deterministic nesting-depth/draw-order order.
4. Translate each interval's row-local display-column bounds to row-local Rich
   character spans with the reviewed wide/combining-character logic.
5. Store that independently built object as the renderable for that physical
   row.

The per-row cache used by `HistorySurface.render_line` is authoritative. It
must not be populated by indexing, slicing, splitting, or copying ranges from a
history-wide Rich `Text`. In particular, replace the current pipeline in which
`build_history_text` creates the accumulated renderable and
`_update_line_texts` slices every row back out of it.

A history-wide Rich `Text` may remain as a compatibility or diagnostic view,
as section 6 permits. If retained, compose it from independently built row
objects or row source data. It must never be the source of the per-row cache,
and constructing or refreshing it must not put a full-history operation back
on the hover path. Keep literal product strings literal; do not enable Rich
markup while refactoring.

Prefer one small, spyable row-building helper shared by initial construction,
full synchronization, and targeted restyling. Do not duplicate the
display-column-to-character conversion or create a second style policy.

## Full synchronization

A complete direct-row rebuild remains correct when the underlying drawing
state genuinely changes:

- retained history revision changes;
- the content width changes and the pure layout is recomputed;
- an explicit forced synchronization occurs; or
- accept state changes, because entering or leaving accept can change the base
  style of presentations throughout retained history.

Even in those cases, build each physical-row Rich `Text` directly from its own
pure-layout row. Preserve scroll anchoring, pointer re-hit-testing, virtual
size, documentation refresh, and all other reviewed synchronization behavior.

If a history-wide compatibility view is materialized, it may be refreshed on
these full synchronization paths. It must not be eagerly rebuilt merely
because hover moved while history, width, and accept state stayed unchanged.

## Targeted hover and accept-target restyling

`set_hovered_presentation` retains the current pure-layout validation and
identity semantics. When the hovered presentation changes:

1. Save the presentation being left.
2. Validate and save the presentation being entered.
3. Collect physical-row indices from the intervals of both presentations.
4. Take the union, so an overlapping row is rebuilt once.
5. Rebuild only those row Rich `Text` objects, using the complete current style
   state for every interval on each affected row.
6. Refresh only the affected drawing rows or the smallest available Textual
   region that displays them, while retaining the existing documentation
   update.

All physical rows outside that union keep the exact same Rich `Text` object.
Setting the same presentation again rebuilds no row. Entering from no hover
touches only the entered presentation's rows; leaving to no hover touches only
the left presentation's rows. A presentation that wraps across several
physical rows causes each of those rows, and no unrelated row, to be rebuilt.

Rebuild a whole affected row rather than trying to remove Rich spans in place.
That row rebuild must reapply all of its presentations in normal style order,
so nested and overlapping presentations remain correct. Presentation ids in
the pure fragments/intervals identify the spans to style; display intervals
remain hit-testing authority. Never interchange a Rich code-point offset with
a terminal display column.

The same targeted rule applies while an accept request is stable. Moving from
one acceptable target to another, from a target to an inert presentation, or
away from a presentation redraws only the physical rows of the presentation
being left and the one being entered. The existing accept-wide bold/underline
or dim base styling is already present on other rows and must not cause them to
be rebuilt for a hover transition. Entering or leaving accept itself may use
the full synchronization described above.

Do not call a history-wide builder, a history-wide slicing helper, or the old
all-row `_update_line_texts` path from a hover-only transition. Do not change
pointer coordinate translation, scrolling, resize hit testing, selection, or
accept execution while making this correction.

## Automated regression

Extend `tests/test_terminal.py`; do not add another test module. Retain every
one of the 101 reviewed tests without deletion, weakening, or replacement.

Add a regression with all of these properties:

1. Use an injected `FixedProcesses`-style process table or construct listener
   history directly. It contains **hundreds** of process rows with distinct
   pids and long, literal command lines.
2. Never instantiate or call the production Linux process service, scan live
   `/proc`, or depend on host processes.
3. Use a content width that wraps long commands, so at least the chosen process
   presentations occupy multiple physical rows and the layout contains far
   more rows than either hover affects.
4. Complete the initial/full synchronization before measuring the hover-only
   operation. Snapshot the per-row Rich `Text` object identities.
5. Instrument the direct row-building seam and, if necessary, guard the old
   history-wide build/slice seam. A transition from no hover to one process
   must build exactly that presentation's physical rows. A transition from it
   to a different process must build exactly the union of the physical rows
   occupied by the left and entered presentations.
6. Assert that every unaffected physical row retains object identity. Also
   assert that the affected styles change correctly and that all original long
   command text remains present and unmodified.
7. Make the regression fail if hover rebuilds all retained physical rows or
   slices rows from an accumulated history-wide Rich `Text`.

Use structural observations such as helper calls, affected-row sets, and Rich
`Text` object identity. Do not use a wall-clock duration, benchmark threshold,
sleep, scheduler assumption, or machine-dependent ratio.

Keep the existing wide/combining-character and nested-presentation assertions
green. Add a focused assertion if needed to show that direct row construction
preserves their character-span behavior, but do not expand this checkpoint
into new layout or hit-test work.

## uv workflow and verification

Add no dependency. Use only the project-managed uv environment:

```console
uv sync
uv run pytest
```

All 101 existing tests plus the new regression must pass. Do not use `pip`,
`python -m pip`, `uv pip install`, Poetry, Pipenv, Conda, Hatch, or a globally
installed Python. If uv is unavailable, stop and tell the human.

No live `/proc` exercise, physical-terminal hand check, dependency update, or
documentation edit is required for this drawing-only checkpoint.

## Completion boundary

Listener 005 is complete only when each rendered physical row is built directly
from that row, the hover path redraws exactly the rows belonging to the
presentation left and entered, the large injected-process regression proves
that behavior without timing, and the full automated suite passes.

Stop there. Do not alter enumeration, hit testing, retention, stored process
commands, commands, or any other product behavior.
