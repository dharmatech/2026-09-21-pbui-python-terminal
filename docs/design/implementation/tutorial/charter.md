# Charter — a tutorial in the listener

**Status.** Handoff from the high-level discussion into a **design
conversation**. Not a checkpoint. Not an implementer assignment.
This file lives in `docs/design/implementation/tutorial/`. The
specification will live beside it as [`spec.md`](spec.md).
Checkpoint files will live in `checkpoints/` beside it. Map:
[`README.md`](README.md). The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

**Your job.** Turn this charter into a specification for a short
local tour. Cards appear in the listener history. Next, Back,
Contents, and Try are presentations on the card. Then **stop**. Do
not write checkpoints. Do not implement.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Use the chips, transcript, and popup specifications only to
   preserve yank, chip insertion, and the documentation line. Do
   not copy them. Restate every rule an implementer must obey.
3. Record the locked decisions in §4. Resolve the open questions in
   §5.
4. Write `spec.md` in this folder. A later checkpoint-manager
   conversation slices **tutorial 000**, `001`, … under
   `checkpoints/` here, one checkpoint per conversation.
5. Stop. The human reviews the spec. Do not write those checkpoint
   files.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification.

Keep the spec **small enough to slice**. A card editor, a second
activity, and a web server are defects in this document.

## 2. Predecessors

The listener through the popup exploration is implemented. HTTP is
a separate exploration and is not required here. Submitted input
can be yanked back into the editor. A click while composing Python
inserts a value chip. The documentation line names the left and
right buttons.

This exploration does not create a new project. Implementers keep
using uv in the existing project. Prefer no new dependency. The
designer does not run uv.

| Place | What goes there |
|---|---|
| `docs/design/implementation/tutorial/` | This charter, `spec.md`, and `checkpoints/` |
| Project root | The existing `pbui` package and `tests/` |

Cards are program data in the package. They are not design
documents, not HTML, and not fetched.

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **`:tutorial` shows the first card in the history.** The card is
   more than one line. Next, Back, Contents, and at least one Try
   are clickable parts of that card, not keys the user must know.
2. **Navigation appends a card.** Next, Back, and a contents entry
   leave the current card where it is and append the card they name.
3. **Try does not run.** It loads one complete example into the
   editor. Enter runs it. The user can edit the line first.
4. **A busy editor is left alone.** If a continuation, an accept, a
   menu, or a non-empty line is open, Try does not replace it. The
   documentation line says to finish or cancel that input first.
5. **The tour is local and short.** The stack covers the listener
   as it stands. It does not document HTTP, and it does not open a
   socket.

## 4. Locked decisions (record these; do not reopen)

### 4.1 The card

A card is an object stored in the package. It has an identifier, a
title, body text, zero or more examples, and links for next,
previous, and contents. The contents card is one of these objects.
Its body entries are presentations of the other cards, not plain
titles.

`:tutorial` appends the first tour card. It does not clear history.
Calling it again appends that card again.

The first stack is a single linear tour plus the contents card. The
tour cards, in order, are at least:

1. What a presentation is, with a Python example `1 + 2 + 3`.
2. A colon command, with the example `:ls`.
3. Clicking a previous value into an expression.
4. The right-button menu.
5. Bringing an input row back into the editor.

The spec writes the sentences. It may add a SymPy card. It may not
add a card that requires the network. Contents lists every tour
card. Next and previous follow the linear order. Contents is not a
step in that order. Every tour card links up to contents. Contents
has no up link. Next on the last tour card and previous on the
first do not append a card. The documentation line says so.

### 4.2 Drawing and clicks

A card draws as one presentation of several history rows: the title,
the body, then the controls. The spec chooses a maximum number of
rows, at least 12 and at most 40. Text beyond that is cut, and the
cut is marked. The stored card is complete.

Next, Back, Up, and each contents entry are nested presentations of
cards. Try is a nested presentation of one example. The example
stores the exact input pieces to yank: a Python line, or a colon
command. A click on the surrounding card text selects the card. A
click on a control selects that control. Innermost wins.

Left click on Next, Back, Up, or a contents entry appends that card.
It does not change the editor and does not record a transcript input
row. The new card is the only addition. Left click on Try, when the
editor is empty and no continuation, accept, or menu is open, loads
the example into the editor and does not run it. Python chips are
not required in the stored examples. A later Enter is an ordinary
submission, so the transcript records it then.

If the editor is busy, Try does not change it. Navigation still
appends. While composing Python, a click on a value elsewhere in
the history still inserts a chip. A click on a card control does
not insert a chip and does not yank over a busy editor.

Card controls have no action menu. The right button is `no menu`.
The documentation line names Left and Right for the control under
the pointer. The spec writes those sentences.

### 4.3 What this is not

There is no card editor. There is no second full-screen activity.
There is no web server and no export. The same card objects must
not store HTML, so a later presenter can draw them somewhere else.
This specification has only the listener presenter.

### 4.4 Tests

Headless tests construct the stack from the package data and do not
start Textual. Cover at least:

- `:tutorial` appends the first card and does not clear older rows;
- Next appends the following card and leaves the first row in place;
- Next on the last card and previous on the first append nothing;
- Up appends contents, and a contents entry appends that card;
- Try on an empty editor returns the example pieces and does not
  evaluate them;
- Try while the editor is non-empty returns the editor unchanged.

The hand check, from a disposable directory, is: run `:tutorial`,
read the first card, use Try, press Enter, use Next, and open
Contents and choose a card. `uv run pytest` is the automated gate.
`uv run pbui` is only the hand check.

### 4.5 Slice order

1. **Cards and links.** Objects, stack order, navigation, and Try's
   returned pieces. Headless. No Textual.
2. **Screen.** Multi-line drawing, documentation sentences, clicks,
   and the hand check.

Do not add a slice for a feature in §4.3.

## 5. Open questions (resolve these in the spec)

### 5.1 Prose and control labels

Write the title and body of each tour card, and the visible labels
for Next, Back, Up, Contents, and Try. A label is one short token
sequence. The Python example and the `:ls` example must appear in
full on their cards.

### 5.2 Layout

Choose how a control is distinguished from body text, and the row
cap. The cap is at least 12 and at most 40 history rows for one card.

### 5.3 Busy Try

Write the exact documentation sentence when Try refuses because the
editor is busy. Name Left and Right.

## 6. Authority

This charter is the design for this exploration. The earlier
specifications remain the law for everything it does not change.
HTTP remains a separate exploration.

Genera could have drawn this card in the listener. It put the full
manual in Document Examiner instead, a separate activity. This
exploration is the short tour in the listener. It is not that
examiner, and it is not a manual.

## 7. Handoff reminder

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. Identity is **tutorial 000**, then
**tutorial 001**.
