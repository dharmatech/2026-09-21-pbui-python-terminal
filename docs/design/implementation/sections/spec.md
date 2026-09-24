# Specification — tutorial subjects

**Status:** accepted. This file is the complete design input for the checkpoint manager and implementers. It assigns no implementation work by itself.

The local tutorial becomes a stack of subjects. Contents offers Listener and SymPy. Each subject opens a section card listing its lessons. The original five gesture lessons belong to Listener; four new lessons guide a user through the SymPy expression behavior already present in pbui. Following a link still appends a fresh presentation of a stored card to listener history.

## 1. Checkpoint series

The series identity is **sections**. Checkpoint 000 is spoken **sections 000** and filed as docs/design/implementation/sections/checkpoints/000-slug.md; checkpoint 001 is **sections 001**. Numbers have three digits, start at 000, are never renumbered, and use lowercase words separated by hyphens for slugs. The checkpoint manager writes one checkpoint and stops. An implementer handles only the received checkpoint and stops. After the user accepts this spec, this file is the design authority; the charter is only the spec writer's assignment.

The layer order is **subject stack and headless behavior** (sections 000), then **visible controls, documentation, and screen verification** (sections 001). Each is one independently testable part. If a layer exceeds one implementer conversation, the checkpoint manager may split it, preserving the order and adding no features. The manager writes only the next missing number.

## 2. Product boundary and authority

This extends the existing Linux full-screen pbui listener. :tutorial continues to append the Presentations lesson directly after its command input row. The user can climb from that lesson to Listener, then Contents, and open SymPy's lessons from Contents. Displaying a card or following a link never evaluates an example.

The accepted tutorial design governs the unchanged Try load, append-only navigation, row cap, hit testing, and original gesture lesson text. This spec changes the old Contents entries, Up destinations and labels, and the documentation cases named in section 6. The accepted SymPy design governs expression objects, their one-line printer, and the simplify, expand, and factor menu actions. The expected algebraic results appear in section 4; this series adds no expression printer or translator.

Files, Processes, and HTTP cards or placeholders, another card level, a card editor, fetched content, new commands, or a changed Try load are outside this series. Recall and completion are not prerequisites. The user guide is not edited. A later subject can be added as another section of leaves under Contents without a new navigation rule.

## 3. Host, layout, and commands

The project root is /home/dharmatech/journal/2026-09-21-pbui-python-terminal/. This is the existing Python 3.11+ src/pbui/ package with tests in tests/ and the pbui console entry point. Product code and tests go at the project root, never in this design folder. src/pbui/tutorial.py owns the immutable card stack and pure row drawing. src/pbui/commands.py owns headless command, navigation, and Try behavior; src/pbui/bottom.py owns documentation wording; src/pbui/terminal.py is the Textual screen adapter. The existing TutorialCard, TutorialTarget, and TutorialTry presentation types remain; there is no new presentation type. Only pbui.terminal imports Textual.

The project already has pyproject.toml, uv.lock, the src/ layout, and SymPy. Add no dependency and do not initialize a new project. From the project root, implementers use uv sync, uv run pytest, and, for the hand check, uv run pbui. All Python, application, and test commands use uv. If uv is unavailable, stop and report it rather than using another Python tool. The spec writer does not run uv.

## 4. Card data and subject stack — sections 000

### 4.1 Roles and links

The stack has three roles, all represented by retained TutorialCard objects:

| Role | Stored children | Controls |
|---|---|---|
| Contents | Section cards, in order | One bracketed entry per section; no Back, Next, or Up |
| Section | Its leaf cards, in order | One bracketed entry per leaf, then Up to Contents; no Back or Next |
| Leaf | No children | Back, Next, and Up to its section; no entries |

Contents is the only card without a parent. Every other card has exactly one parent. Back and Next are siblings within a single section; the first Back and last Next have no destination and remain visible and disabled. Each enabled entry or Up resolves to its stored destination card by identity. A newly opened card gets a new outer presentation but retains that same stored card object. The TutorialTarget for an Up control stores its parent destination and its complete visible label, “Up: ” followed by that parent's title. Section cards and Contents must not create Back or Next controls at all.

Keep the existing five-card tour order available to the :tutorial entry point. Expose the ordered sections and make every card, including both sections and all nine leaves, resolvable by its stable identifier. Preserve the existing identifiers presentations, commands, values, menus, yank, and contents; use distinct identifiers for listener, sympy, and the four SymPy leaves. A section is an ordinary immutable card with entries, not a new screen or a special command. Construction is local package data: it must not import SymPy, read the filesystem, inspect processes, or open a socket.

The Contents card retains its title “Contents” and body line “Choose a card to append it to history.” Its entries are exactly Listener, then SymPy. The Listener section has title “Listener”, body line “Choose a card to append it to history.”, entries referencing the five gesture cards in the order below, and Up to Contents. The SymPy section has title “SymPy”, the following four body lines in order, entries referencing the four SymPy leaves in order, and Up to Contents:

- A SymPy expression stays a live object in history.
- Its menu can simplify, expand, or factor it.
- Import and a symbol come before the examples.
- Up returns here from any of these cards.

### 4.2 Listener leaves

These are the exact existing titles, body lines, and examples. The only change to these lessons is their parent: Up now targets Listener. Their order remains the Back/Next order.

**presentations — 1. Presentations**

- History keeps an object together with the text you see.
- Run 1 + 2 + 3 to get a value holding 6.
- At an empty prompt, click that value to show its detail.
- Try loads the line; Enter runs it.

Try saves the Python line “1 + 2 + 3”.

**commands — 2. Colon commands**

- Commands start with a colon in the same editor.
- Use :ls to list the current directory.
- The results keep file and directory objects you can click.
- Try loads :ls; Enter lists the directory.

Try saves the colon command “:ls”.

**values — 3. Reuse a value**

- Run the first card's example so 6 is in history.
- Type 10 + , then click the 6 result.
- The editor inserts a chip for that exact object.
- Press Enter to evaluate the completed expression.

No Try example.

**menus — 4. The right-button menu**

- Point at a history object and read the documentation line.
- Right-click an object with actions to open its menu.
- Choose an item to run it; Esc or Ctrl-G closes the menu.
- The action uses the object you pointed at.

No Try example.

**yank — 5. Bring input back**

- A submitted Python form or colon command stays in history.
- At an empty prompt, click its input row to load it again.
- Edit the line if you like; Enter submits it.
- Right-click the row and choose yank for the same load.

No Try example.

The first Back is disabled; the last Next is disabled. Up on any of these five targets Listener. No gesture card links to a SymPy card through Back or Next. Submitting :tutorial appends its ordinary CommandInput row and then Presentations, without replacing older history. A second invocation appends another presentation of the same stored Presentations card. An argument follows the existing no-argument error behavior and appends no card.

### 4.3 SymPy leaves

The four SymPy leaves have these exact titles, body lines, and Try sources. Each body is four lines or fewer. Each Try saves one editable Python input line using the existing PythonInput piece shape.

**1. Import**

- Import SymPy to make the sympy name available.
- Enter adds an input row but no value row.
- Later cards use that name.

Try saves exactly “import sympy”.

**2. Symbol**

- This binds x to a SymPy symbol.
- Enter adds an input row but no value row.
- Later cards use x.

Try saves exactly “x = sympy.Symbol("x")”.

**3. Expand**

- Enter (x + 1)**2 to keep the power in history.
- Open that expression row's menu and choose expand.
- A new row shows x**2 + 2*x + 1.
- The original power stays in history.

Try saves exactly “(x + 1)**2”.

**4. Factor**

- Enter x**2 - 1 to keep the polynomial in history.
- Open that expression row's menu and choose factor.
- A new row shows (x - 1)⋅(x + 1).
- The original polynomial stays in history.

Try saves exactly “x**2 - 1”.

Back on Import and Next on Factor are disabled. Every Up targets SymPy. Back/Next never crosses the SymPy section boundary. The Expand menu result is structurally x**2 + 2*x + 1; Factor's is structurally (x - 1)*(x + 1). The existing SymPy one-line printer decides exact glyphs and spacing in history: the demo describes the expanded row as x**2 + 2*x + 1 and the factored row as (x - 1)⋅(x + 1). The source expression remains in history and the action appends a new expression row. simplify is named only on the SymPy section; it has no leaf.

### 4.4 Headless navigation and Try

An enabled entry, Back, Next, or Up appends only a fresh presentation of its destination. The source remains in history, and navigation records no PythonInput, CommandInput, or MenuActionInput row. It preserves the editor's text, pieces and cursor, including during Python continuation, presentation accept, or substring accept. A disabled Back or Next appends nothing. An exposed navigation control outside an open popup still closes the popup and follows the link on the first click; the popup owns clicks inside its rectangle. Other popup and accept routing stays as it is. Controls have no action menu. A bare card has no default navigation action.

Try remains an editor load of exactly one saved line and does not submit it. At an empty ordinary prompt without continuation, pending accept, substring accept, or popup, it loads the line with the cursor at its end and appends no history row. An existing text or chip, continuation, accept, substring accept, or open popup makes Try refuse without changing the editor or history. Enter later submits normally. Ordinary value chip insertion and input-row yank continue to work; clicking a card control does neither.

Sections 000 changes the stored stack, parent targets, and Try data and proves the navigation in headless tests. It may use the existing pure card drawer to obtain retained controls, but the complete on-screen control text and documentation work belongs to sections 001.

## 5. Visible rows and controls — sections 001

Every card uses the existing bounded card drawing: title, body lines, example rows, entry rows, and a final navigation row, all under one outer TutorialCard presentation. The group has at most 20 logical history rows; complete text remains stored when the existing cut marker is needed. The 500-row history limit, escaping, wrapping at 120 display cells, inner-control hit priority, and scroll/resize hit testing remain unchanged.

Entry labels are bracketed destination titles. Contents shows [Listener] and [SymPy], in that order, and no gesture-card entries. Listener shows the five bracketed titles in section 4.2. SymPy shows [1. Import], [2. Symbol], [3. Expand], and [4. Factor]. Section cards put their Up control after their entries. Neither section nor Contents draws Back or Next. Contents draws no Up. Every leaf draws [Back]  [Next]  [Up: PARENT], with PARENT Listener or SymPy. Both section cards draw [Up: Contents]. Each Try row draws [Try] followed by a space and its exact source. A disabled Back or Next remains bracketed, visible, dimmed, and unclickable.

The bracket and label are the control's nested hit area. Spaces, title, body, and example source outside [Try] belong to the outer card. The stored TutorialTarget.label and the drawn control text must agree. A card control still has no menu or default action besides its specified left click.

## 6. Documentation line — sections 001

Keep the existing target-first documentation format and all other sentences, including Try's ready/busy sentences, the outer-card sentence, popup and accept context, Right behavior, and narrow-width truncation. The following are the exact complete sentences at an ordinary prompt; the existing accept lead and cancel suffix still wrap them when an accept is pending:

| Target | Exact sentence |
|---|---|
| Enabled Up from a Listener leaf | TUTORIAL UP “Listener” • Left: open • Right: no menu |
| Enabled Up from a SymPy leaf | TUTORIAL UP “SymPy” • Left: open • Right: no menu |
| Enabled Up from either section | TUTORIAL UP “Contents” • Left: open • Right: no menu |
| Disabled Back at the first leaf of either section | TUTORIAL BACK • Left: this section has no previous card • Right: no menu |
| Disabled Next at the last leaf of either section | TUTORIAL NEXT • Left: this section has no next card • Right: no menu |

Enabled Back, Next, and entries retain the same sentence shape, naming their destination in the target: “TUTORIAL DIRECTION “TITLE” • Left: open • Right: no menu”. DIRECTION is BACK, NEXT, or CONTENTS, and TITLE is the stored destination title. Thus Contents entries name Listener or SymPy, section entries name their leaf, and a leaf's enabled sibling control names its sibling. The enabled Up sentences above replace the tutorial specification's “Left: open Contents in the tutorial. Right: no menu.” rule, which assumed every Up reached Contents. The disabled sentences replace its “Left: first tutorial card; no previous card. Right: no menu.” and “Left: last tutorial card; no next card. Right: no menu.” rules. No other card documentation sentence changes.

## 7. Verification

Sections 000 adds or updates headless tests in tests/test_tutorial.py. They build the immutable stack without Textual and prove Contents has only Listener then SymPy; Listener has exactly the original five leaves and SymPy has exactly the four new leaves; all parent, Back, and Next links stay within their roles. Construction must be shown not to import SymPy or perform filesystem, process, or network work. Test :tutorial's command row and first card, a second invocation, and an argument refusal. Using retained controls, prove Up from Presentations appends Listener and Up from Listener appends Contents; Next from Bring input back appends nothing; a SymPy leaf's Up appends SymPy and its Next never opens a gesture card. Verify each Up control's stored destination and complete label. Try on Import and Expand loads the exact single line without evaluation or a value row. Preserve the existing tutorial tests for navigation state, 20-row cap, card identity, ordinary chip insertion, and yank, updating their hierarchy assumptions.

Sections 001 adds or updates tests/test_terminal.py screen coverage for bracketed entries and labels, absence of Back/Next on sections and Contents, dimmed boundary controls, and the exact sentences in section 6. At least one screen test clicks Up from Presentations to Listener to Contents, opens SymPy, and checks that Next on Bring input back appends nothing. It also verifies that a SymPy leaf's navigation remains inside SymPy and that the new controls remain nested hits. Update existing screen assertions that assumed the old Contents entries or Up target. Existing tests remain green. From the project root, run uv run pytest as the automated gate.

For one hand check, use a disposable directory and launch uv run pbui. Enter :tutorial; click Try on Presentations, press Enter, and see 6. Click Up and read the five gesture titles on Listener; click Up and read Listener and SymPy on Contents. Open SymPy, then Import; Try “import sympy” and press Enter. Its input row appears with no value row. Use Next and Try to enter “x = sympy.Symbol("x")”; it also adds no value row. Use Next and Try to enter “(x + 1)**2”, then open that expression row's menu and choose expand. Use Next and Try to enter “x**2 - 1”, then choose factor from that expression row's menu. See the new algebraic rows and the retained original expression rows. Next on Factor appends nothing. Up returns to SymPy, then Up to Contents. uv run pbui is only the hand check.

## 8. Acceptance

The series is accepted when :tutorial still opens Presentations directly, its Try loads 1 + 2 + 3, and Enter shows 6; Up from a gesture leaf opens Listener and Up from Listener opens Contents; Contents lists only Listener and SymPy; Next and Back never cross subject boundaries; the old five cards keep their lessons and examples; the four SymPy cards and their exact Try lines guide the existing expand and factor actions; no card construction imports SymPy or performs I/O; and the headless tests, one screen test, one hand check, and existing uv run pytest suite pass.
