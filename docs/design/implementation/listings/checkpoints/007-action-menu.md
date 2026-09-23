# listings 007 — Transient action menu

**Status.** Ready to implement.

## Goal

Complete the automated screen-and-menu layer. Add one transient `ActionMenu`
surface above the documentation line and prompt, with exact actions for
listing headers and member rows. Open it by button 3 or `Ctrl-O`, route every
item through the existing command or listing-view operation, and provide the
specified menu documentation and close behavior. Menu opening and closing
must preserve the listings 006 viewport anchor.

The disposable-directory live hand check in specification section 7.4 is a
separate final checkpoint.

## Identity, authority, and predecessors

- Identity is `(listings, 007)`, spoken **listings 007**.
- [`../spec.md`](../spec.md), especially sections 2.1, 4.3–4.4, 5, 6.1,
  6.3–6.4, 7.3, and 8, is the design authority. Preserve the rest of that
  specification when this checkpoint is silent.
- Listings 000–006 are implemented and reviewed. They provide stable member
  and header presentations, cached listing views, exact table drawing,
  semantic styles, modal substring state, pointer-aware documentation, and
  viewport anchors.
- The baseline suite has **185 passing tests**.
- The project root is
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application
  code and tests remain there, never under `docs/`.

## Exact file scope

### May edit

- `src/pbui/terminal.py`
- `src/pbui/commands.py`, only for small public stored-object/menu-narrow
  dispatch seams that reuse existing command and view operations
- `tests/test_terminal.py`
- `tests/test_commands.py`, only to verify those new headless dispatch seams

### Must not edit or create

- `.python-version`, `pyproject.toml`, `uv.lock`, `README.md`, or `AGENTS.md`
- `src/pbui/__init__.py` or `src/pbui/__main__.py`
- `src/pbui/domain.py`, `src/pbui/substrate.py`, or `src/pbui/text.py`
- another production module or test module
- anything under `docs/`, including this checkpoint, the specification, and
  earlier checkpoints
- any file outside the project root

The terminal's `MenuAction` type is private and transient. Do not add it to
`DomainTypes`, the listener's seven exact registered domain types, command
names, typed accept set, or retained history. If menu work seems to require
a new domain model, a second command grammar, or a dependency, return the
checkpoint for correction rather than widening the slice.

## Preserved behavior

Preserve all listings 000–006 capture, identity, view, table, style,
documentation, anchor, modal substring, and lifecycle behavior. In
particular:

- With the menu closed, single left-click on a member still runs the `show`
  translator; single left-click on a listing header remains inert.
- Existing typed `show`, `cd`, `rm`, `kill`, `ls`, `ps`, `sort`, `narrow`, `only`,
  and `widen` keep their grammar, validation, safety checks, errors, and
  effects. No menu label is parsed as a command line.
- A menu action uses the member's exact stored object or the header's exact
  retained listing, never a displayed cell, path reconstruction, pid lookup
  for targeting, newest-listing fallback, or a host rescan for a view action.
- A successful view action replaces one owned block in place; an `ls` action
  on a directory member appends a **fresh** listing of that directory.
- History remains one `HistorySurface` with row-local hover restyling. The
  menu does not create one Textual widget per item or any history row.
- The prompt and documentation line stay mounted as one fixed row each and
  do not scroll. Normal exit, `Ctrl-C`, and all errors retain terminal cleanup.

## One private menu surface

Add exactly one custom `ActionMenu` surface to the listener screen. While
closed it occupies no screen height. While open it is a transient panel
immediately above the documentation line and prompt and outside the history
surface; its height reduces the history viewport. Do not append a menu row
to history. If the terminal is too short for all items, keep the fixed bottom
rows visible and make every menu item reachable within that one panel.

The terminal privately registers a `MenuAction` presentation type, separate
from the listener's domain registry. Each drawn item is one `Presentation`
of that type. Its stored value identifies the canonical operation, optional
argument, and the exact target member presentation/object or listing. The
complete displayed item row is its hit region. These presentations exist
only for the open menu, are not accepted into chips, and are discarded on
close. Menu item hover uses reverse video and repaints only the item rows
being left and entered; it does not rebuild the history surface.

Opening or closing the panel, including after executing an item, preserves
the oldest visible logical-row anchor and wrapped-line offset where possible
under listings 006, then clamps. Re-hit-test the current pointer after the
history viewport changes. Moving the pointer from the original history
target toward a menu opened elsewhere must not close it before first entry
into the panel. Once the pointer has entered the panel, leaving the panel
closes it. Track that entry per opening, not globally.

## Exact menu items

Items appear top to bottom in the exact order below. Labels are literal;
there is no abbreviation, dynamic sorting, separator item, or extra action.

| Target | Exact labels in order |
|---|---|
| `File` member | `show`, `rm` |
| `Directory` member | `show`, `cd`, `ls` |
| `Process` member | `show`, `kill` |
| `DirectoryListing` header | `sort name`, `sort size`, `sort mtime`, `only files`, `only directories`, `narrow`, `widen` |
| `ProcessListing` header | `sort pid`, `sort state`, `sort command`, `only running`, `only sleeping`, `only disk-sleep`, `only stopped`, `only tracing`, `only zombie`, `only dead`, `only idle`, `only unknown`, `narrow`, `widen` |
| `Text`, `Error`, literal text, or any other presentation | no items |

Only exact registered member/header presentations from the current history
can be menu targets. A filtered-out or wholly evicted target must not be
resurrected by an already-open menu. Resolve labels and targets from stored
presentations, not table text. The process `user` field is never a separate
menu target.

## Opening, closing, and executing

- A single button-3 click on the history resolves a **fresh hit at the event
  coordinate** and opens that target's menu when allowed. Later clicks in
  the same click chain do nothing. A button-3 event is not also a left-click
  selection.
- `Ctrl-O` uses the fresh current history hover/pointer hit and opens that
  target's menu when allowed. With no hovered presentation it opens nothing.
  This is the required keyboard equivalent for terminals without button 3.
- A pending presentation accept or pending substring accept remains modal:
  neither opening gesture opens a menu or changes the pending state. Preserve
  its existing documentation sentence.
- `Ctrl-G` or Escape while a menu is open closes the menu **without**
  cancelling or changing the listener's input, chip, listing, or history.
  With no menu open, these keys retain their existing listener-cancellation
  behavior.
- One left click on an item closes the menu and runs that action exactly
  once. A click elsewhere while open closes it without running an action;
  that same click must not fall through to the history `show` translator or
  another target. Later clicks in a click chain do nothing.
- Closing by leave, cancellation, or outside click adds no history row and
  does not alter the ordinary input editor. Once closed, the original
  left-click behavior resumes.

For member actions, add only the smallest headless stored-object execution
seam needed to reuse the existing `_run_typed`/`_execute` command path and
its exact type checks and live safety revalidation. `show`, `rm`, `cd`, and
`kill` receive the member's original reference; directory `ls` receives its
original `DirectoryRef`. Do not submit a synthesized command string or call
a parallel filesystem/process implementation. A stale or unretained
presentation must not run through this seam.

For `sort`, `only`, and `widen`, invoke the existing
`apply_listing_view(listing, operation, argument)` with the menu's exact
retained listing. For header-menu `narrow`, enter the existing headless modal
substring state **bound to that listing**; do not call typed `narrow` and
resolve the newest listing. A tiny public headless begin-narrow seam may
expose the existing `_begin_substring_accept` after exact type/retention
validation. Close the menu before showing the `narrow ` editor. Nonempty
Enter then applies to that same listing through the existing headless path;
empty Enter and cancellation retain listings 005 behavior.

After an action, synchronize the screen: append effects reveal newest output,
in-place view replacement keeps the listings 006 anchor, and no-history
effects keep the position. Recompute hover/documentation against the new
viewport and pointer, never stale menu or history coordinates.

## Documentation line

While the menu is open and no item is hovered, use exactly:

```text
Point at an action and click; Ctrl-G or Esc closes the menu.
```

Item hover uses exactly one of these templates, substituting the exact
menu label and the existing escaped member label or decimal pid:

```text
Click to run “LABEL” for file “NAME”.
Click to run “LABEL” for directory “NAME”.
Click to run “LABEL” for process PID.
Click to apply “LABEL” to this directory listing.
Click to apply “LABEL” to this process listing.
```

An allowed opening gesture without an actionable target must show exactly
one of these persistent sentences:

```text
Point at a presentation before opening an action menu.
Text has no action menu.
Error has no action menu.
This presentation has no action menu.
```

Use the first for empty/literal history space, the next two for exact `Text`
and `Error`, and the last for any other non-actionable presentation. An
unsuccessful-open sentence persists until hover or listener state next
changes. It must not be overwritten immediately by a routine screen sync or
by pointer motion within the same hovered presentation. Modal accept
documentation takes precedence when opening is disallowed. On menu close,
restore the appropriate ordinary/accept/modal sentence from the current
pointer. The documentation surface remains one mounted visual row and
ellipsis-truncates rather than wrapping.

## Automated tests

Extend only the allowed test files. Use injected filesystem/process services,
`tmp_path`, and `PbuiApp.run_test()` where appropriate. Do not read live
`/proc`, unlink outside `tmp_path`, or signal an arbitrary process. Keep all
185 predecessor tests without deletion or weakened assertions.

Prove at least:

- the single private `MenuAction` type and presentation-per-item model,
  complete-row item hits, exact item labels/order for all five actionable
  target kinds, and no listener-domain-registry/history additions;
- button 3 uses the event's fresh whole-row hit; `Ctrl-O` uses fresh hover;
  empty, `Text`, `Error`, and unrelated presentations give exact refusal
  documentation; later click-chain events do nothing;
- modal presentation accept and modal substring accept block both opening
  gestures without changing their targets or sentences;
- `Ctrl-G`, Escape, outside click, and post-entry leave close the menu with
  the specified input/history preservation; travel toward the panel before
  first entry does not close it;
- item hover documentation uses all five exact templates, the no-hover
  sentence is exact, unsuccessful-open sentences persist and clear at the
  specified boundary, and documentation still occupies one nonwrapping row;
- a menu on an **older** listing sorts, filters, widens, and begins `narrow`
  on that exact listing while a newer one remains unchanged; no view action
  rescans the host or appends a copy;
- member `show`, `cd`, `rm`, `kill`, and directory `ls` route through the
  original stored reference and existing revalidation/refusal behavior; use
  safe injected services and disposable files only;
- a stale or evicted menu target cannot execute; a menu-item click executes
  once and cannot fall through into a second history action;
- opening/closing and action completion preserve the correct viewport anchor
  and wrapped offset, clamp when necessary, and re-hit-test hover;
- history passive hover and menu-item hover each repaint only affected rows,
  including the listener 005 hundreds-of-rows regression, with no elapsed
  time assertion; and
- ordinary member left-click and header inertness return after menu close,
  with the existing exit and cleanup paths still green.

## uv workflow and verification

Add no dependency. Use only the existing uv-managed project:

```console
uv sync
uv run pytest
```

All predecessor tests plus new listings 007 tests must pass. Do not use
`pip`, `python -m pip`, `uv pip install`, Poetry, Pipenv, Conda, Hatch, a
hand-made virtual environment, or a globally installed Python. If `uv` is
unavailable, stop and tell the human.

No live hand check, live `/proc` exercise, dependency edit, or terminal
emulator-specific button-3 assertion is required for this automated menu
checkpoint.

## Completion boundary

Listings 007 is complete when one transient menu presents every exact action
and sentence; both opening gestures, all closing gestures, item routing,
modal precedence, anchors, and pointer hover work; member and view actions
share their existing headless operations; and the full automated suite
passes. This finishes specification section 7.3.

Stop there. Do not perform the disposable-directory live hand check or add a
new domain type, shell syntax, refresh command, graphical table, or another
menu surface.
