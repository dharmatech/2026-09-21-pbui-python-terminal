# Specification — action menu at the pointer

**Status:** proposed specification for human review. This is the complete design input for the later **popup 000** checkpoint. It assigns no implementation work by itself. The checkpoint belongs in `checkpoints/` and is written in a later conversation.

The existing action menu opens over history beside its target. A one-cell border makes its items distinct from history. The permanent documentation row names the left and right buttons for the presentation under the pointer.

## 1. Boundary and preserved behavior

This extends the implemented listener, listings, REPL, chips, SymPy, and transcript specifications. It supersedes their menu **placement, drawing, and dismissal** rules and the documentation wording for ordinary pointer targets, pending presentation accept, substring accept, an open menu's items and border, and a Python continuation with no target. It does not change command parsing, accept types, editor modes, chip insertion, translators, menu items or order, action effects, history recording, or the middle button. There is no new command, menu item, or button action. The menu remains terminal cells, not a graphical toolkit menu or a history presentation.

Use the existing `src/pbui/` package and `tests/`; prefer no new dependency. Keep the headless geometry calculation importable without Textual. Implementers use the existing uv project: `uv sync`, `uv run pytest`, and `uv run pbui` only for the hand check. If uv is unavailable, stop and report it. The designer does not run uv.

The existing menu contents and dispatch remain:

| Target | Items in top-to-bottom order | Effect |
|---|---|---|
| `File` | `show`, `rm` | Run the existing operation on the retained file. |
| `Directory` | `show`, `cd`, `ls` | Run the existing operation on the retained directory; `ls` appends a fresh listing. |
| `Process` | `show`, `kill` | Run the existing operation on the retained process. |
| `DirectoryListing` header | `sort name`, `sort size`, `sort mtime`, `only files`, `only directories`, `narrow`, `widen` | Apply the existing view operation to that exact listing. |
| `ProcessListing` header | `sort pid`, `sort state`, `sort command`, `only running`, `only sleeping`, `only disk-sleep`, `only stopped`, `only tracing`, `only zombie`, `only dead`, `only idle`, `only unknown`, `narrow`, `widen` | Apply the existing view operation to that exact listing. |
| `Value` with registered translators, including a SymPy `Expr` | The registration's ordered translator labels; for `Expr`: `simplify`, `expand`, `factor` | Call the existing translator with the retained object. |
| `PythonInput` or `CommandInput` | `yank` | Load its saved pieces at an empty editor, or insert them while composing Python. |
| `MenuActionInput` | `run again` | Repeat its saved operation on its saved object and argument. |
| Generic `Value`, `Text`, `Error`, literal/empty history | No items | No menu opens. |

Choosing an item still takes the menu's saved target and resolved operation, not a fresh hit on the history beneath it. The existing exact-type accepts, revalidation, errors, listing redisplay, transcript row creation, Python composition preservation, and `narrow`'s suspend-and-restore behavior continue to apply. The menu itself never enters history.

## 2. Overlay and geometry

The bordered menu is an overlay **inside the visible history rectangle**. It takes no vertical-layout row and changes neither the history viewport nor its scroll anchor. The documentation and input rows stay in place and cannot be covered. Drawing or removing the menu restores the underlying history cells without changing their presentations or hit intervals. An open menu receives pointer events before history does.

Draw `┌` and `┐` on the top row, `└` and `┘` on the bottom row, `─` along the horizontal edges, and `│` on both sides of each item row. Put one blank cell between each vertical border and the item text. Pad shorter labels on the right so all rows have the same width. For `n` labels and maximum label display width `L`, the complete rectangle is `L + 4` cells wide and `n + 2` cells high. Box-drawing characters occupy one terminal cell each. An item's hit area is its whole interior row, including the blank padding; the border is neither an item nor a presentation.

The opening anchor is the pointer cell for a button-3 click on a history presentation. `Ctrl-O` uses the pointer cell if a fresh hit there is the target presentation; otherwise it uses the target's top-left **visible** cell. It uses the existing current-hover target selection. If that target has no visible cell, do not open the menu and show `Point at the object to open its menu.` No target or a target without items does not open a menu.

Measure the menu before opening. If its complete width or height exceeds the visible history rectangle, do not open it and show `The action menu does not fit in the history area.` Otherwise start its top-left at the anchor and shift it by the smallest horizontal and vertical distances that keep the complete rectangle within history. Equivalently, clamp each anchor coordinate to the range from the history's first cell through its last cell minus the menu's size plus one. Do not resize, truncate, wrap, or scroll the menu to make it fit. Hit-test the pointer again **after** placing the overlay: if the shift puts an item row under the pointer, that item is hovered immediately; if it puts the border there, no item is hovered.

On terminal resize, recompute the visible history rectangle and clamp the stored opening anchor by the same shift rule. Close the menu if its full rectangle no longer fits. Recompute menu hover and documentation from the pointer's current cell. A history scroll while the menu is open closes it rather than moving the menu with the scrolled content.

## 3. Opening, choosing, and dismissal

Mouse button 3 uses a fresh hit at its event coordinate; `Ctrl-O` uses the existing current-hover target. These gestures open the same menu when items exist. Pending presentation accept or substring accept still blocks opening. Python composition and continuation still allow opening; opening and a menu action do not insert a chip or discard pending input. No gesture here gives the middle button a function.

Once open, the bordered rectangle owns mouse hits. A first left click on an interior item row runs exactly that item once and closes the menu. The underlying history presentation does not receive that click. Moving within the rectangle leaves the menu open. Moving the pointer outside its border closes it without an action, including before the pointer has first entered an item. Clicking any cell outside the rectangle also closes it without passing that click through to history. Clicking the border does nothing and leaves the menu open; other interior cells without an item behave the same way. A non-left click inside the rectangle does not choose an item or open a second menu. `Ctrl-G` or Escape closes the menu first, without changing editor input or history; their existing behavior applies when no menu is open. `Ctrl-D` keeps the chips rule: its first press while a menu is open only closes that menu, and does not yank, run an item, discard a continuation, or exit. When no menu is open, `Ctrl-D` keeps its existing continuation and exit rules. Later clicks in a click chain do not choose an item.

## 4. Documentation row

The one-row documentation line remains immediately above input, never wraps, and truncates with an ellipsis at narrow terminal widths. Recompute it on pointer movement, menu open/close, editor mode or cursor changes, accept changes, execution, scroll, and resize. In the ordinary state, every history presentation under the pointer uses the exact `Left: ... Right: ...` sentence below. `Right: menu.` means button 3 opens its existing menu; `Right: no menu.` means there are no items. `Ctrl-O` remains the keyboard way to open an available menu. `NAME`, `PID`, and `LABEL` use the existing escaped display labels, captured process PID, and action label.

| Pointer target, with no accept or menu open | Exact sentence |
|---|---|
| SymPy expression `Value` | `Left: show this SymPy expression. Right: menu.` |
| Other `Value` with translators | `Left: show this Python value. Right: menu.` |
| Generic `Value` without translators | `Left: show this Python value. Right: no menu.` |
| `File` | `Left: show file “NAME”. Right: menu.` |
| `Directory` | `Left: show directory “NAME”. Right: menu.` |
| `Process` | `Left: show process PID. Right: menu.` |
| Truncated process command field | `Left: show the full command for process PID (command is truncated). Right: menu.` |
| `DirectoryListing` header | `Left: no action on this directory listing. Right: menu.` |
| `ProcessListing` header | `Left: no action on this process listing. Right: menu.` |
| `PythonInput`, empty editor | `Left: load this Python form into the editor; Enter runs it. Right: menu.` |
| `CommandInput`, empty editor | `Left: load this command into the editor; Enter runs it. Right: menu.` |
| `MenuActionInput`, empty editor | `Left: run “LABEL” again on the same object. Right: menu.` |
| Any input presentation while editing a colon command | `Left: no action while editing a command. Right: menu.` |
| `Text` | `Left: no action for Text. Right: no menu.` |
| `Error` | `Left: no action for Error. Right: no menu.` |

During Python composition, including continuation, a result or other object-bearing history presentation at a valid expression-atom site says `Left: insert this value into the expression. Right: MENU.` Replace `MENU` with `menu` or `no menu` according to the same item availability above. At a string or comment site it says `Left: insertion unavailable in a string or comment. Right: MENU.` At another invalid chip site it says `Left: move the cursor to a Python expression position to insert this value. Right: MENU.` These two refusals do not fall through to `show`. A `MenuActionInput` uses these same three sentences for insertion of its saved target. A `PythonInput` or `CommandInput` instead says `Left: insert this input at the cursor. Right: menu.` Its saved pieces are inserted by the existing transcript rule, not the single-object chip rule.

During a pending presentation accept, a hovered acceptable target says `Left: use TARGET and run COMMAND. Right: no menu.` Substitute `file “NAME”`, `directory “NAME”`, or `process PID` for `TARGET`, and the pending `rm`, `cd`, `kill`, or `show` for `COMMAND`. The permitted pairs remain `rm`/File, `cd`/Directory, `kill`/Process, and `show`/File, Directory, or Process. Every other hovered presentation says `Left: cannot use TYPE for COMMAND; REQUIRED required. Right: no menu.`, substituting its presentation type for `TYPE` and `File`, `Directory`, `Process`, or `File, Directory, or Process` for `REQUIRED`. The click remains inert for those targets. A pending substring accept owns the line and keeps its exact sentence, `Type a substring and press Enter to narrow this listing; Ctrl-G or Esc cancels.`; history clicks cannot insert or open a menu in that state.

While the menu is open, a hovered item uses one exact sentence from this table. Its right button has no menu. `LABEL` is the hovered item's label; for `run again`, it is the saved action's label.

| Menu item target | Exact sentence |
|---|---|
| File | `Left: run “LABEL” for file “NAME”. Right: no menu.` |
| Directory | `Left: run “LABEL” for directory “NAME”. Right: no menu.` |
| Process | `Left: run “LABEL” for process PID. Right: no menu.` |
| Directory listing | `Left: apply “LABEL” to this directory listing. Right: no menu.` |
| Process listing | `Left: apply “LABEL” to this process listing. Right: no menu.` |
| Registered Python value, including SymPy | `Left: apply “LABEL” to this Python value. Right: no menu.` |
| `yank` on a Python or command input, editor empty or composing Python | `Left: yank this input into the editor. Right: no menu.` |
| `yank` on a Python or command input, while editing a colon command | `Left: no action while editing a command. Right: no menu.` |
| `run again` on a menu-action input | `Left: run “LABEL” again on the same object. Right: no menu.` |

Choosing `yank` while a colon command is being edited closes the menu and leaves that command unchanged. It does not load the saved input. In every other editor mode, choosing `yank` runs the existing yank.

When the pointer is on the menu border or any interior cell without an item, show `Click an item; Ctrl-G or Esc closes the menu.` With no menu and no presentation under the pointer, including empty or literal history, show `No presentation under pointer.` Do not invent a button action there. During a Python continuation with no target, keep `Python continuation: enter another line; Ctrl-G or Esc discards it.` During a pending presentation accept with no target, keep the existing command-specific instruction to point at a highlighted acceptable target and click. The unsuccessful `Ctrl-O` attempt on an invisible target and the menu-too-large attempt use the exact messages in section 2 until pointer or listener state changes. The middle button is never mentioned in documentation.

## 5. Verification and handoff

Keep all existing tests passing. Add a pure, headless geometry test, with no Textual import, for an anchor in the middle of history, anchors that would cross the right and bottom edges, and a menu taller than the history rectangle. It must check the complete bordered size, smallest shift, no-fit result, and hovered cell after placement. Also cover `Ctrl-O` choosing the pointer cell on the target, its top-left visible cell when the pointer is elsewhere, and no anchor for an invisible target. Run `uv run pytest` as the automated gate.

For one hand check, start `uv run pbui` from a recorded disposable directory under the project root. Produce a SymPy expression, point at it near the middle of history, and read a documentation row that names `Left` and `Right`. Right-click it and see a bordered menu beside the pointer over history, with the documentation and input rows unmoved. Move the pointer outside the border and see the menu close without an action. Then point at the expression and press `Ctrl-O`; see the same menu beside the object. No destructive command is needed.

The later checkpoint manager makes **one slice, popup 000**, covering position, border, dismissal, documentation, and verification together. Human review of this specification comes first. Pandas, new menu items or commands, changed transcript/chip/SymPy results, shifted buttons, middle-button actions, and a graphical toolkit menu are outside this exploration.
