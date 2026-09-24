# Specification — a tutorial in the listener

**Status:** accepted and implemented through tutorial 001. This is the complete design input for the checkpoint manager and implementers. It assigns no implementation work by itself.

The tutorial is a short, local tour inside the existing listener. A colon command adds a card to history. Each card is a retained object drawn across several rows, with smaller presentations for navigation and examples. A link appends another card; Try places an editable example in the ordinary input line.

## 1. Checkpoint series

The series identity is **tutorial**. Checkpoint 000 is spoken **tutorial 000** and filed as docs/design/implementation/tutorial/checkpoints/000-cards-and-links.md. Subsequent numbers have three digits, start at 000, are never renumbered, and use lowercase hyphenated slugs. The checkpoint manager writes one checkpoint, then stops. Each implementer completes only the checkpoint received and stops. After the user accepts this spec, it is the design authority for those conversations; the charter is not an implementation input.

The layer order is **cards and links**, then **screen**. Tutorial 000 covers package data, headless history and navigation, and Try's saved input. Tutorial 001 covers screen drawing, hit routing, documentation, and the hand check. Each is one independently testable slice. A checkpoint manager may split a layer that exceeds one implementer conversation, preserving this order and adding no feature.

## 2. Product boundary and authority

This extends the implemented listener in the existing pbui package. It keeps the 500-logical-row history limit, scroll/resize hit testing, command transcript, Python evaluator, exact-type accept, chip insertion, input yank, and popup menu behavior except where this spec gives a card control its own action. The chips, transcript, and popup specifications in sibling implementation folders govern those preserved seams; this spec governs tutorial cards and their controls when a rule differs. HTTP is a separate exploration and is not a prerequisite.

There is one linear tour and one contents card. No card editor, second screen, web server, export, HTML in stored cards, fetched content, socket, or HTTP tutorial card belongs in this series. The contents card is a card in the same data set, not a separate activity. Card content is package data; only the listener presenter draws it here.

## 3. Host, layout, and commands

The project root is /home/dharmatech/journal/2026-09-21-pbui-python-terminal/. Code belongs in its existing src/pbui/ package and tests in tests/, never in this design folder. The host is Linux with Python 3.11 or newer. pyproject.toml, uv.lock, the pbui console entry point, and the src/ layout already exist. Add src/pbui/tutorial.py for immutable card data and pure card operations; extend src/pbui/domain.py for presentation types, src/pbui/commands.py for the headless listener, and src/pbui/terminal.py for the Textual adapter. Keep pbui.terminal the only package module importing Textual. Prefer no new dependency.

All Python environment, dependency, program, and test commands use uv. The existing project needs no uv init. From the project root, implementers use:

    uv sync
    uv run pytest
    uv run pbui

uv run pytest is the automated gate. uv run pbui is for the final hand check only. If uv is unavailable, stop and report it; do not use another Python tool. The spec writer does not run uv.

## 4. Card data and exact tour text

Define an immutable TutorialCard with a stable identifier, title, complete body lines, zero or more immutable examples, optional next and previous links, and an optional contents link. Links resolve to the same stored card objects by identifier; reopening a card creates a new history presentation of that stored object. Store no rendered fragments, HTML, Textual widget, editor state, or callback in a card. The contents card also has entries referencing every tour card, in tour order. Each entry is a card-target presentation, not a literal-only title.

An example retains the exact input kind and pieces to load: one Python line or one colon command. Use the existing PythonInput/CommandInput piece shapes for loading, without creating a transcript input presentation until Enter submits. The first stack has exactly these five tour cards in order, plus contents; it has no SymPy card:

### presentations — 1. Presentations

Body, in order:

- History keeps an object together with the text you see.
- Run 1 + 2 + 3 to get a value holding 6.
- At an empty prompt, click that value to show its detail.
- Try loads the line; Enter runs it.

Example: Python line 1 + 2 + 3.

### commands — 2. Colon commands

Body, in order:

- Commands start with a colon in the same editor.
- Use :ls to list the current directory.
- The results keep file and directory objects you can click.
- Try loads :ls; Enter lists the directory.

Example: colon command :ls.

### values — 3. Reuse a value

Body, in order:

- Run the first card's example so 6 is in history.
- Type 10 + , then click the 6 result.
- The editor inserts a chip for that exact object.
- Press Enter to evaluate the completed expression.

No example.

### menus — 4. The right-button menu

Body, in order:

- Point at a history object and read the documentation line.
- Right-click an object with actions to open its menu.
- Choose an item to run it; Esc or Ctrl-G closes the menu.
- The action uses the object you pointed at.

No example.

### yank — 5. Bring input back

Body, in order:

- A submitted Python form or colon command stays in history.
- At an empty prompt, click its input row to load it again.
- Edit the line if you like; Enter submits it.
- Right-click the row and choose yank for the same load.

No example.

### contents — Contents

Body: Choose a card to append it to history.

Its entries are 1. Presentations, 2. Colon commands, 3. Reuse a value, 4. The right-button menu, and 5. Bring input back, each referencing its complete stored card. No example.

The five tour cards link forward and backward in that order. The first has no previous target; the last has no next target. Every tour card's contents link targets contents. Contents has no next, previous, or up link. Absent targets remain visible as disabled Back/Next on boundary tour cards, with no append action; contents has only its five entries. Constructing the stack does not run commands, read files, inspect processes, or open a network connection.

## 5. Card rows and presentations

Append one card as a contiguous group of **at most 20 logical history rows**, all sharing one outer TutorialCard presentation. Rows appear in this order: title, body lines, example rows, and navigation row. A blank separator may be included within the cap. Store the card's complete text even if drawing cuts it. Escape unsafe display characters using the listener's existing rules and wrap long body text into logical rows at 120 display cells; narrower terminals may further wrap those rows physically. If the group would exceed 20 logical rows, reserve the title and controls, show as much body/example text as fits, and put “… (card text cut)” on the last available content row. Every visible physical segment of every retained card row must hit the same outer card when no nested target covers that cell. Ordinary 500-row history eviction may remove old rows without changing the stored card.

Use bracketed controls to distinguish actions from prose. The brackets and label are part of the nested hit area; spaces between controls are outer-card text. On tour cards the final row is [Back]  [Next]  [Up: Contents]. Up: Contents is the visible label for the up link to the contents card. The first and last boundary controls remain bracketed but visibly dimmed. The Python example row is [Try] 1 + 2 + 3; the command example row is [Try] :ls. The whole bracketed Try control is the nested presentation of that example; the adjacent source remains legible body text. On contents, each entry is a bracketed title, such as [1. Presentations], and the entire bracketed entry is its nested card-target presentation. The exact control labels are Back, Next, Up: Contents, Try, and the five contents titles; Contents is also the title of the contents card.

An enabled navigation control or contents entry retains its destination TutorialCard by identity. A disabled boundary control retains its direction and no destination. Try retains its complete example. The innermost presentation wins a hit: a control hit selects its link or example; a title, body, source text outside Try's brackets, cut marker, or spacing hit selects the surrounding card. Card controls have no action menu. Right button on them is no menu; Ctrl-O finds none. A bare card has no tutorial action menu or default append action.

## 6. Command, navigation, and Try

Register tutorial as a colon command taking no argument. :tutorial appends the ordinary CommandInput transcript row and then the first card. It does not clear or rewrite older history. Submitting it again appends another command row and another presentation of the first card. An argument follows ordinary no-argument command error behavior and appends no card. No tour command is evaluated merely because a card is drawn.

A first left click on an enabled Next, Back, Up, or contents entry appends **only** a fresh presentation of the destination card. The selected card stays in history; the editor, pending Python pieces, and cursor stay as they were. Navigation records no PythonInput, CommandInput, or MenuActionInput row. Clicking disabled Next or Back appends nothing. Card navigation takes priority over Python chip insertion and input yank when its control receives the click, even while composing a Python line or continuation or editing a colon command. A click on an ordinary value elsewhere in history during Python composition still follows the chips rule and inserts a chip at a valid expression site. A click on a prior input row still follows transcript yank; card controls never yank that row.

Card navigation is an explicit exception to modal accept and popup routing. A first left click on a visible navigation control appends its target even during a pending presentation accept or substring accept; the pending request, its input, and any suspended Python pieces remain intact. If a popup is open, its rectangle still owns all clicks inside it. A first left click on an exposed card navigation control outside that rectangle closes the popup and appends the target in that one click. Other outside clicks keep the popup rule and do not pass through. A navigation click never supplies an accept target, inserts a chip, or yanks input.

Try is an editor load, not a submission. At an empty ordinary prompt with no continuation, pending accept, substring accept, or open menu, clicking Try loads the example's exact pieces and puts the cursor at the end. For the Python example it loads 1 + 2 + 3 as one editable Python line. For the command example it loads :ls as one editable colon command. It appends no history row, performs no evaluation or listing, and leaves the card in history. The user may edit the line; a later Enter follows normal submission and transcript recording. Share the existing yank loading semantics for these saved pieces rather than fabricating a transcript presentation merely to call yank_input.

If the editable line contains any text or chip, a Python continuation is pending, an accept or substring accept is pending, or a menu is open, Try returns no pieces and changes neither editor nor history. It never inserts an example into a nonempty Python expression or overwrites a colon command. An open popup retains its screen click priority, so a click through it cannot activate Try.

Clicking the surrounding card at an empty prompt returns that card presentation as the hit but has no default command. During Python composition, its object may be inserted as a chip only through the existing chip insertion guard; this does not change how clicks on ordinary values work. During accept, card and control presentations are not acceptable file, directory, or process targets.

## 7. Documentation line

The existing one-row documentation line remains immediately above input, names Left and Right for the hovered target, and truncates at narrow widths. Recompute it when the pointer, editor mode, menu, accept, history, scroll, or viewport changes. The following are the exact sentences when a card target is available to the pointer:

| Target and state | Exact sentence |
|---|---|
| Enabled Next, Back, or contents entry | Left: open “TITLE” in the tutorial. Right: no menu. Replace TITLE with the destination title. |
| Up control | Left: open Contents in the tutorial. Right: no menu. |
| Back on the first card | Left: first tutorial card; no previous card. Right: no menu. |
| Next on the last card | Left: last tutorial card; no next card. Right: no menu. |
| Try, editor ready | Left: load this example into the editor; Enter runs it. Right: no menu. |
| Try, editor busy | Left: finish or cancel the current input before trying this example. Right: no menu. |
| Outer card, ordinary empty prompt | Left: no action on this tutorial card. Right: no menu. |

For the Try sentence, **busy** means a nonempty line, a chip, continuation, pending presentation or substring accept, or open menu. Inside an open popup rectangle, its item/border documentation still owns the pointer. On an exposed card control outside the popup, the control sentence above applies. Try remains busy while the popup is open. During a pending presentation or substring accept, navigation controls keep their navigation sentences, Try uses the busy sentence, and clicking either preserves the pending input as stated in section 6. When Python composition hovers outer card text, use the existing chips documentation: valid insertion, string/comment refusal, or other invalid-site refusal, each with Right: no menu. When a pending presentation accept hovers outer card text, keep the existing accept refusal sentence with its presentation type and Right: no menu. Other pointer targets retain the popup specification documentation.

## 8. Verification and acceptance

Tutorial 000 adds headless tests in tests/test_tutorial.py that import package data without importing Textual. They must prove: the five-card order and contents entries; :tutorial leaving older history rows in place and appending a command row then the first card; a second invocation appending a distinct presentation of the same stored card; Next, Back, Up, and a contents entry appending the right card without editor or transcript changes; first Back and last Next appending nothing; Try returning the Python or command pieces on an empty editor without evaluation; and Try refusing a nonempty editor or continuation without changing pieces. Test that navigation during ordinary composition and pending accept preserves the line, cursor, and pending request. Use injected services and a disposable root where a listener is needed. Test the 20-row cut marker and that a retained card still holds its complete data. No test starts Textual or calls a network transport.

Tutorial 001 adds screen tests in tests/test_terminal.py for multiple card rows sharing one outer presentation, nested hit priority on controls, links remaining clickable after wrapping/scrolling, dimmed boundary controls, exact documentation sentences, no card menu, busy Try refusal for nonempty input, continuation, accept, and popup, navigation through exposed controls with a pending accept or popup, and preservation of ordinary value-chip insertion and input yank. Existing tests remain green. Run uv run pytest from the project root.

For one hand check, start uv run pbui from a disposable directory. Enter :tutorial, read the first card, click Try and confirm the line is editable and no result has appeared, press Enter and see 6, click Next, click Up: Contents, and choose a contents entry. Check that each navigation appends a card without removing its predecessor. No destructive command is part of the tour.

The series is accepted when :tutorial shows the multi-row first card in history, the first card's Next, Back, Up/Contents, and Try are clickable nested parts, navigation appends its chosen card, Try loads exactly one editable example without running it, a busy editor is preserved with the stated documentation, and all five local tour cards and contents work without HTTP or a socket.
