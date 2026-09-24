# Charter — a menu at the pointer

**Status.** Handoff from the high-level discussion into a **design
conversation**. Not a checkpoint. Not an implementer assignment.
This file lives in `docs/design/implementation/popup/`. The
specification will live beside it as [`spec.md`](spec.md).
Checkpoint files will live in `checkpoints/` beside it. Map:
[`README.md`](README.md). The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

**Your job.** Turn this charter into a specification that draws the
existing action menu beside the pointer, with a border, and makes
the bottom line name the left and right buttons. Then **stop**. Do
not write checkpoints. Do not implement.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Read the listings, chips, and transcript specifications only far
   enough to preserve the menu items, the clicks, and the sentences
   those clicks perform. Do not copy them. Restate every rule an
   implementer must obey. This spec supersedes only where the menu
   is drawn and how the documentation line names the buttons. It
   does not change which item runs which action.
3. Record the locked decisions in §4. Resolve the open questions in
   §5.
4. Write `spec.md` in this folder. A later checkpoint-manager
   conversation slices **popup 000**, `001`, … under `checkpoints/`
   here, one checkpoint per conversation.
5. Stop. The human reviews the spec. Do not write those checkpoint
   files.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification.

Keep the spec **small enough to slice**. A new mouse button action
is a defect in this document.

## 2. Predecessors

Listener, listings, the REPL, chips, SymPy, and the transcript are
implemented. The action menu is a vertical region between the
history and the documentation line. The same items open with mouse
button 3 or Ctrl-O. The documentation line is one permanent row
above the input. It says what a left click will do, and it often
mentions the right button in the same sentence. The middle button
does nothing.

This exploration does not create a new project. Implementers keep
using uv in the existing project. Prefer no new dependency. The
designer does not run uv.

| Place | What goes there |
|---|---|
| `docs/design/implementation/popup/` | This charter, `spec.md`, and `checkpoints/` |
| Project root | The existing `pbui` package and `tests/` |

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **The menu opens at the pointer.** Right-click an expression in
   the middle of the history and the menu is drawn beside that
   cell, over the history. It is not inserted above the prompt and
   it does not push the input row down.
2. **It looks like a menu.** A border surrounds the items. The
   border is not an item. Choosing an item still runs the same
   action it runs today.
3. **The bottom line names the buttons.** With the pointer on that
   expression, the documentation line states the left-button action
   and the right-button action as two labeled parts. It does not
   mention the middle button.
4. **Leaving the menu closes it.** Moving the pointer off the
   bordered menu closes it without running an item. Ctrl-G and
   Escape still close it. A click outside it closes it.
5. **Old tests still pass**, plus a geometry test and one hand
   check. No new command and no new menu item.

## 4. Locked decisions (record these; do not reopen)

### 4.1 Where the menu is

The menu is an overlay on the history area. It is not a row in the
vertical layout, it is not part of the history, and its items are
not history presentations. The documentation line and the input
line stay where they are and are never covered.

Anchor the menu's top-left cell on the pointer cell that opened it.
Then move it by the smallest shift that keeps the whole bordered
menu inside the history area. The pointer may rest on an item after
that shift. That item is the hovered item.

Ctrl-O has no click. If the pointer is already over the target
presentation, use that pointer cell as the anchor. Otherwise use
the top-left visible cell of the target presentation. If the target
is not visible, do not open the menu. The documentation line says
to point at the object.

If the bordered menu cannot fit in the history area even after
shifting, do not open it. The documentation line says it does not
fit. A later resize re-applies the same shift rule. If it still
cannot fit, close the menu.

### 4.2 What the menu looks like and how it closes

Draw a one-cell border around the items with box-drawing
characters. The spec chooses the characters. The border is not a
presentation and not a hit target. Moving onto the border does not
count as leaving the menu. Clicking the border does not run an
item and does not close the menu.

The items, their order, and the actions they run are unchanged.
Hover inside the menu still updates the documentation line to the
item under the pointer.

The menu closes without running an item when the pointer leaves the
bordered region, when the user clicks a cell that is not inside
that region, or when Ctrl-G or Escape is pressed. Choosing an item
runs it and closes the menu, as today. Moving inside the menu does
not close it. Scrolling the history while the menu is open closes
it. The history underneath does not receive the click that chooses
an item.

### 4.3 The documentation line

The documentation line remains one row above the input. Its text
names the left button and the right button, and only those, for the
presentation under the pointer. Do not mention the middle button.
Do not give the middle button an action.

The left-button action is exactly today's left click: show, insert
a chip, yank an input, supply an accept, or run a menu action
again, whichever already applies. The right-button action is
`menu` when that presentation has menu items, and `no menu` when it
does not. The spec writes the exact sentences. They replace the
current sentences that bury the right button inside one clause.
The actions do not change.

While the menu is open, the documentation line describes the menu
item under the pointer. On the border, or on a menu cell that is
not an item, it says to click an item, or press Ctrl-G or Escape to
close. With no presentation under the pointer and no menu open, the
line does not invent button actions. The spec writes that sentence
too.

### 4.4 Tests

A headless test computes the anchor and the shift. Cover a click in
the middle of the history, a click that would place the menu past
the right or bottom edge, and a menu too tall for the history area.
No Textual in that test.

The hand check, from a disposable directory, is: produce a SymPy
expression, right-click it near the middle of the history, see a
bordered menu beside the pointer rather than above the prompt, move
the pointer off the menu and see it close, and read a bottom line
that names the left and right buttons. Also press Ctrl-O on that
expression and see the same menu beside the object. `uv run pytest`
is the automated gate. `uv run pbui` is only the hand check.

### 4.5 Slice order

One slice. The position, the border, the dismissal, and the
documentation line belong together. Do not add a slice for a
feature in §4.6.

### 4.6 Out of this spec

- A middle-button action, or a shifted-button action.
- New menu items, new commands, or a change to what an existing
  item does.
- Pandas, or a change to the transcript, chips, or SymPy results.
- A graphical toolkit menu. This remains terminal cells.
- Recording the menu itself in the history.

## 5. Open questions (resolve these in the spec)

### 5.1 Border

Choose the box-drawing characters and the gap, if any, between the
border and the item text. The border is one cell thick.

### 5.2 Sentences

Write the exact documentation sentences for: a SymPy expression, a
file row, an input form, a presentation with no menu, empty
history, a hovered menu item, and the menu border. Each object
sentence names `Left` and `Right` in that order.

### 5.3 Anchor after the shift

State whether the hovered item is the one under the pointer after
the menu has been shifted. The locked rule is that it is.

## 6. Authority

This charter is the design for this exploration. The earlier
specifications remain the law for everything it does not change.

Genera kept a mouse-documentation line at the bottom of the screen
and popped the presentation menu up at the pointer. This
exploration takes that split. It does not take Genera's
middle-button handlers.

## 7. Handoff reminder

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. Identity is **popup 000**.
