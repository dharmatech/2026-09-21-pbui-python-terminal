# popup 000 — Action menu at the pointer

**Status.** Accepted by the user and implemented.

## Goal and authority

Move the existing action menu into a bordered overlay on the visible history,
open it beside its target, and make the fixed documentation row name the left
and right buttons. Complete the geometry and screen checks, the full automated
gate, and one live terminal hand check in this single slice.

- Identity is `(popup, 000)`, spoken **popup 000**.
- The human-reviewed [`../spec.md`](../spec.md) is the design authority,
  including its exact menu contents, geometry, documentation sentences, and
  preserved behavior. Follow it wherever this checkpoint is silent. The
  charter is not an implementation input.
- Listener, listings, REPL, chips, SymPy, and transcript are implemented.
  Preserve their command grammar, accepts, editor and chip behavior, action
  effects, retained objects, history recording, and middle-button behavior.
- Work in the existing project at
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Keep code in
  `src/pbui/` and tests in `tests/`. Add no dependency unless a concrete need
  arises; the geometry calculation must import without Textual.

Stop after this checkpoint. Do not start pandas, add another menu item or
button action, change transcript/chip/SymPy results, or write another popup
checkpoint.

## File and feature boundary

Update `src/pbui/terminal.py` for the menu overlay, event routing, and
documentation. Put the measured rectangle, clamping, and cell hit calculation
in a small headless module under `src/pbui/` or an existing pure module. Add
focused geometry tests without importing Textual and screen tests using the
existing `PbuiApp.run_test()` pattern. Adjust old terminal tests whose
assertions describe the superseded panel position, scrolling, or wording;
retain their checks for action dispatch, object identity, hover, viewport,
modal priority, and cancellation. Do not edit the accepted spec.

Reuse the existing menu target and resolved `MenuAction` dispatch. The menu
still contains the items, in the order, given in spec section 1. A click must
run the menu's saved operation on its saved object, never re-hit the history
under the overlay. Keep the menu out of history and the border out of the
presentation and item hit maps. The menu remains terminal cells; do not add
a graphical toolkit menu or a widget for each item.

## Overlay, geometry, and opening

Draw the menu wholly inside the **visible history rectangle**, over its
existing cells. It must consume no vertical-layout row, change no history
scroll anchor or hit interval, and cover neither documentation nor input.
Opening and closing must restore the underlying history drawing without
changing its retained presentations.

Measure every label in terminal display cells. For `n` labels and widest
display width `L`, the complete rectangle is `L + 4` cells wide and `n + 2`
cells high. Use `┌─┐`, `│`, and `└─┘` for the one-cell border, one blank cell
on either side of padded item text, and a uniform row width. An item owns its
whole interior row, including padding, but no border cell. Do not truncate,
wrap, resize, or scroll the menu to force a fit.

- Button 3 opens from a fresh presentation hit at the event's pointer cell.
  `Ctrl-O` uses the existing current-hover target; use the pointer cell as
  its anchor when a fresh hit there is that target, otherwise the target's
  top-left visible cell. If the target has no visible cell, leave the menu
  closed and show `Point at the object to open its menu.` No target or no
  menu items leaves it closed.
- Reject a menu wider or taller than visible history and show
  `The action menu does not fit in the history area.` Otherwise clamp the
  opening anchor by the smallest horizontal and vertical shifts that fit the
  **complete bordered rectangle**. Hit-test the current pointer after the
  placement: an item now beneath it is immediately hovered; a border cell
  has no hovered item.
- On resize, recompute history bounds and clamp the stored opening anchor
  again. Close the menu if it no longer fits; otherwise recompute item hover
  and documentation at the pointer's current cell. A history scroll closes
  the menu instead of moving it with the history.

## Pointer, keyboard, and documentation

An open menu receives pointer events before history. A first left click on
an item runs it exactly once and closes the menu. A click outside the complete
rectangle closes it without passing that click through to history. Moving
outside closes it even if the pointer has not entered an item. Movement
inside, including on the border, leaves it open; clicking the border or
another interior non-item cell does nothing. A non-left click inside does not
run an item or open another menu. Later clicks in a click chain cannot choose
an item. Pending presentation accept and substring accept still block menu
opening, while Python composition and continuation allow it without inserting
a chip or discarding input.

`Ctrl-G` and Escape close an open menu before any ordinary cancellation and
leave the editor and history alone. Preserve the chips `Ctrl-D` priority:
its first press with a menu open only closes that menu; it does not yank, run
an item, discard a continuation, or exit. With no menu open, keep the existing
continuation and exit behavior.

Implement **all exact sentences and precedence in spec section 4**, not only
the ordinary hover table. The documentation row remains mounted immediately
above input, occupies one row, and ellipsis-truncates instead of wrapping.
Refresh it on pointer movement, menu open/close, editor mode or cursor change,
accept change, execution, scroll, and resize. Cover ordinary targets
(including SymPy, truncated process command fields, listing headers, input
presentations, `Text`, and `Error`), Python composition and invalid chip
sites, pending presentation and substring accepts, hovered menu items, the
border, empty history, and continuation with no target. Name only the left
and right buttons where the spec supplies those parts; never give or document
a middle-button action.

Keep the `yank` menu item on `PythonInput` and `CommandInput`. In an empty
editor or during Python composition, it keeps its existing load or insertion
effect. While editing a colon command, its exact item sentence is
`Left: no action while editing a command. Right: no menu.` Choosing it closes
the menu and leaves the command unchanged. A `run again` item retains its
saved object and resolved action. The spec section 4 menu-item sentences and
existing input-preservation rules apply to all other items.

## Automated verification

Keep the full predecessor suite passing. Add a pure headless geometry test,
with no Textual import, for a middle anchor, right-edge and bottom-edge
shifts, and a menu too tall for the visible history. Check the bordered
dimensions, smallest shifts, no-fit result, and the item or border under the
pointer after placement. Cover `Ctrl-O` selecting the pointer cell on its
target, selecting the top-left visible cell when the pointer is elsewhere,
and finding no anchor for an invisible target.

Add focused screen checks for the risks introduced by the overlay:

1. Opening by button 3 and `Ctrl-O` puts the complete border over history
   beside the target while the history viewport, scroll anchor,
   documentation row, and input row stay fixed. Verify the underlying history
   presentation and hit intervals remain intact after close.
2. Check immediate item hover after a shifted placement, whole interior-row
   item hits, inert border hits, non-left clicks, outside movement and clicks
   before first item entry, no click-through to history, and first-click-only
   execution on the menu's saved target.
3. Check resize clamping and no-fit dismissal; history scroll dismissal;
   menu-first `Ctrl-G`, Escape, and `Ctrl-D`; and unchanged continuation
   and editor state after menu close. Both opening gestures must stay blocked
   by presentation accept and substring accept without changing that state.
4. Assert exact documentation from spec section 4 across ordinary hover,
   Python composition, pending accepts, menu item and border hover, and
   no-target cases. Include the colon-command `yank` item: its sentence is
   inert, its click closes the menu, and the command stays unchanged. Confirm
   documentation recomputes at a stationary pointer after editor and menu
   state changes and remains one truncated row at narrow widths.

Use injected services and temporary roots for tests; do not unlink outside a
temporary root or signal a live process. Update obsolete panel-position and
old-sentence assertions without deleting or weakening behavioral coverage.

## uv workflow and live hand check

If uv is unavailable, stop and report it. Use only the existing uv-managed
project. From the project root, run:

```console
uv sync
uv run pytest
```

Do not use `pip`, `python -m pip`, `uv pip install`, Poetry, Pipenv, Conda,
Hatch, a hand-made environment, or a globally installed Python. The full
`uv run pytest` suite must pass before the live check.

For the hand check, create a fresh disposable directory **under the project
root** and record its absolute path. Start `uv run pbui` from that directory
in a real interactive terminal. Produce a SymPy expression and point near
the middle of its history presentation. Read the one-row documentation naming
`Left` and `Right`. Right-click the expression: the bordered menu must open
beside the pointer over history, with documentation and input unmoved. Move
outside the border and confirm the menu closes without an action. Point at
the expression again and press `Ctrl-O`; confirm the same menu opens beside
the object. No destructive command is needed. Report a terminal that does
not deliver button 3 as a hand-check limitation, not as a passing right-click
check.

Report the test result, disposable directory path, visible menu placement,
border and dismissal behavior, documentation wording, `Ctrl-O` result, and
any terminal limitation. Popup 000 is complete when the overlay, border,
event routing, documentation, geometry checks, full suite, and live hand
check satisfy the accepted spec. Stop there.
