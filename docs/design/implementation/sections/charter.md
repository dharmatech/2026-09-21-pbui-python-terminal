# Charter — tutorial sections

**Status.** Handoff from the high-level discussion into a **design
conversation**. Not a checkpoint. Not an implementer assignment.
This file lives in `docs/design/implementation/sections/`. The
specification will live beside it as [`spec.md`](spec.md).
Checkpoint files will live in `checkpoints/` beside it. Map:
[`README.md`](README.md). The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

**Your job.** Turn this charter into a specification that makes the
tutorial a list of subjects, puts the existing five cards under
Listener, and adds one SymPy subject. The series identity is
**sections**. Then **stop**. Do not write checkpoints. Do not
implement.

The specification refuses Files, Processes, and HTTP cards, a second
level of children, and any change to how Try loads a line. Those
refusals keep the series small enough to slice.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Read the accepted tutorial specification and
   `src/pbui/tutorial.py`. Read the SymPy specification and
   [`../sympy/demo.md`](../sympy/demo.md) for what an expression row
   shows and what `expand` and `factor` add. Do not invent a new
   SymPy operation.
3. Record the locked decisions in §4. There is no open-question
   section.
4. Write `spec.md` in this folder. A later checkpoint-manager
   conversation slices **sections 000**, then **sections 001**, under
   `checkpoints/` here, one checkpoint per conversation.
5. Stop. The human reviews the spec. Do not write those checkpoint
   files.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification.

Keep the spec to the subject stack and the SymPy cards. A card
editor, a fetched tour, or a Files section is a defect in this
document.

## 2. Predecessors

Tutorial 001 is implemented. `:tutorial` appends the Presentations
card. Each tour card has Back, Next, and Up: Contents. Contents lists
those five cards. A click on an enabled control appends the
destination card and leaves the earlier card in history. Try loads
one saved line into an empty editor and does not run it.

SymPy is implemented. `import sympy` and `x = sympy.Symbol("x")` add
no value row. `expand` on `(x + 1)**2` and `factor` on `x**2 - 1`
are menu actions on the retained expression. The SymPy specification
is the law for the objects those actions add.

Files, processes, and HTTP already exist in the listener. Their
tutorial subjects do not. Recall and completion are not prerequisites.

This exploration does not create a new project. Implementers keep
using uv in the existing project. Add no dependency. The designer
does not run uv.

| Place | What goes there |
|---|---|
| `docs/design/implementation/sections/` | This charter, `spec.md`, and `checkpoints/` |
| Project root | The existing `pbui` package and `tests/` |

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **The tour still opens on the first gesture.** `:tutorial` appends
   1. Presentations. Try still loads `1 + 2 + 3`, and Enter still
   shows 6.
2. **Up climbs one level.** Up from Presentations appends the
   Listener card. Up from Listener appends Contents. Contents lists
   Listener and SymPy, and it does not list the five gesture cards.
3. **Next stays inside the subject.** Next from 5. Bring input back
   appends nothing. Opening SymPy from Contents, then Expand, does
   not link that card to the gesture cards.
4. **SymPy is four cards.** Import, Symbol, Expand, and Factor are
   the children. Each Try is the one line in §4.4. Expand's menu
   action and Factor's menu action add the expressions the SymPy
   specification already names.
5. **The old cards keep their lessons.** The five gesture cards keep
   their titles, body lines, and examples. Only their parent changes.
6. **Old tests still pass**, plus headless tests for the stack and
   one screen test and one hand check.

## 4. Locked decisions (record these; do not reopen)

### 4.1 Two levels

The stack has three roles:

| Role | What it holds | Controls |
|---|---|---|
| Contents | The subject sections, in order | One entry per section. No Back, Next, or Up. |
| Section | The leaves of one subject | One entry per leaf, then Up to Contents. No Back or Next. |
| Leaf | One lesson | Back, Next, and Up to its section. No entries. |

A leaf has no children. A section's entries are leaves. This series
has no deeper card. Contents is the only card with no parent.

A click on an enabled entry or Up still appends a new presentation
of the stored destination and leaves the source card in history. It
still records no input row and still preserves the editor. Disabled
Back and Next still append nothing and stay visible and dimmed.
Section cards and Contents do not draw Back or Next at all.

The 20-row card cap and the 500-row history stay as they are. Try
stays an editor load of one saved line, with the same busy refusal.
Constructing the stack does not import SymPy, read the filesystem,
inspect processes, or open a socket.

### 4.2 The subjects in this series

Contents has exactly these entries, in this order:

1. **Listener**
2. **SymPy**

Listener's leaves are the existing five cards, in their current
order, with their current titles, body lines, and examples:

1. Presentations, with Try `1 + 2 + 3`
2. Colon commands, with Try `:ls`
3. Reuse a value
4. The right-button menu
5. Bring input back

`:tutorial` still appends Presentations after its command row. A
second `:tutorial` still appends another presentation of that same
stored card. An argument still appends no card.

Back on Presentations is disabled. Next on Bring input back is
disabled. Up on every gesture card appends Listener. Up on Listener
appends Contents.

Files, Processes, and HTTP are later subjects. This series does not
add their cards, their entries, or placeholder sections. A later
series must be able to add one by adding a section of leaves under
Contents, using the roles in §4.1, without a new navigation rule.

### 4.3 Labels

The Up control's visible label is `Up:` followed by the parent
title. Gesture cards show `Up: Listener`. SymPy leaves show
`Up: SymPy`. Both section cards show `Up: Contents`.

Entry labels are the destination titles, bracketed as contents
entries are bracketed today. Listener's entries keep the five
current titles. Contents entries read Listener and SymPy.

The documentation sentence for an enabled Up control uses the same
shape as an enabled Next, Back, or entry: it names the destination
title. The sentences for a disabled Back and a disabled Next say
that this section has no previous or no next card. The spec writes
those exact sentences and names the tutorial-spec sentences they
replace. Every other card sentence stays as it is.

### 4.4 The SymPy leaves

SymPy's body is these four lines, in order:

- A SymPy expression stays a live object in history.
- Its menu can simplify, expand, or factor it.
- Import and a symbol come before the examples.
- Up returns here from any of these cards.

Its leaves are these four, in order. Each body is at most four
lines. The spec writes those lines so they say the facts below and
nothing that starts a second lesson. Each Try source is exact.

| Order | Title | Try | Facts the body must give |
|---|---|---|---|
| 1 | 1. Import | `import sympy` | The `sympy` name exists after this line. The line adds no value row. Later cards use that name. |
| 2 | 2. Symbol | `x = sympy.Symbol("x")` | This binds `x`. The line adds no value row. Later cards use `x`. |
| 3 | 3. Expand | `(x + 1)**2` | Enter the example, open that row's menu, and choose `expand`. A new row holds the expanded expression. The original power stays in history. |
| 4 | 4. Factor | `x**2 - 1` | Enter the example, open that row's menu, and choose `factor`. A new row holds the factored expression. The original polynomial stays in history. |

Back on Import is disabled. Next on Factor is disabled. Up on each
of the four appends the SymPy section. None of these cards is a
Next or Back neighbor of a gesture card.

`simplify` is named on the section card because it is the other menu
action. It has no leaf of its own.

The visible expanded and factored rows are the forms the accepted
SymPy specification and its demo already show. The spec copies those
forms. It does not define a new printer.

### 4.5 What stays as it is

Try, chip insertion, yank, accept, menus, and the action menu on a
SymPy value stay as they are. Card controls still have no menu.
Navigation during a pending accept or an open popup keeps the
tutorial rules. The input row, the documentation line's other
sentences, recall, and completion stay as they are.

The user guide does not describe the tour. This series does not
edit it.

### 4.6 Tests

Headless tests build the stack without Textual. Cover at least:
Contents entries are Listener then SymPy; Listener's entries are the
five gesture cards and SymPy's are the four leaves; `:tutorial`
still appends Presentations; Up from Presentations appends Listener
and Up from Listener appends Contents; Next from Bring input back
appends nothing; a SymPy leaf's Up appends SymPy and its Next does
not append a gesture card; Try on Import and on Expand loads that
exact line and does not evaluate it; constructing the stack does not
import SymPy.

Sections 000 proves the stack, the card text, the parent stored for
each Up control, and that navigation. The visible label string is
part of that stored control.

Sections 001 draws the parent labels, the two contents entries, and
the documentation sentences from §4.3. It includes one screen test
and the hand check. The screen test clicks Up from Presentations to
Listener to Contents, opens SymPy, and checks that Next on the last
gesture card appends nothing.

The hand check uses a disposable directory. Run `uv run pbui`. Enter
`:tutorial`. Try `1 + 2 + 3`, press Enter, and see 6. Click Up and
read the five gesture titles on Listener. Click Up and read Listener
and SymPy on Contents. Open SymPy, then Import, Try it, and press
Enter. The command row appears and no value row follows. Next, Try
the symbol, and press Enter. Next, Try `(x + 1)**2`, press Enter,
open that row's menu, and choose `expand`. Next, Try `x**2 - 1`,
press Enter, and choose `factor`. The original expressions remain.
Next on Factor appends nothing. Up returns to SymPy, and Up returns
to Contents. `uv run pytest` is the automated gate. `uv run pbui` is
only the hand check.

### 4.7 Slice order

**sections 000** stores the subject stack and proves navigation and
Try without Textual.

**sections 001** draws the parent labels and the contents entries,
updates the documentation sentences, and adds the screen test and
the hand check.

Do not add a slice for Files, Processes, HTTP, or a third level.

## 5. Authority

The tutorial specification remains the law for Try, append-only
navigation, the 20-row cap, card hit testing, and the five gesture
lessons. The SymPy specification remains the law for expression
presentation and for `simplify`, `expand`, and `factor`.

Where this charter and the tutorial specification disagree about
Contents entries, the target of Up, or the Up label, this exploration
wins. Where they disagree about what a gesture card teaches or what
Try loads for `1 + 2 + 3` and `:ls`, the tutorial specification wins.
Where they disagree about what `expand` or `factor` produces, the
SymPy specification wins.

## 6. Handoff reminder

The series identity is **sections**. Checkpoint 000 is spoken
**sections 000** and filed as `checkpoints/000-slug.md`. Checkpoint
001 is spoken **sections 001**. Numbers are three digits, start at
000, and are never renumbered. The slug is lowercase words separated
by hyphens. The checkpoint manager writes one checkpoint, then
stops. Code and tests go at the project root
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`, not in
this folder.

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. The first identity is **sections 000**.
The second, in a later conversation, is **sections 001**.

After the spec is accepted, `spec.md` is the design authority for
those conversations. This charter is the assignment for the spec
writer. Later conversations do not read it.
