"""Immutable local tutorial cards and their headless history drawings."""

from __future__ import annotations

from dataclasses import dataclass

from pbui.domain import DomainTypes, escape_display
from pbui.substrate import Presentation, PresentationHistory
from pbui.text import (
    DrawingContext,
    HistoryRow,
    LiteralFragment,
    PresentedFragment,
    wrap_display,
)
from pbui.transcript import CommandInput, PythonInput


@dataclass(frozen=True, slots=True)
class TutorialExample:
    saved_input: PythonInput | CommandInput
    source: str


@dataclass(frozen=True, slots=True)
class TutorialLink:
    direction: str
    destination_id: str | None


@dataclass(frozen=True, slots=True)
class TutorialCard:
    identifier: str
    title: str
    body: tuple[str, ...]
    examples: tuple[TutorialExample, ...] = ()
    previous: TutorialLink | None = None
    next: TutorialLink | None = None
    contents: TutorialLink | None = None
    entries: tuple[TutorialCard, ...] = ()


@dataclass(frozen=True, slots=True)
class TutorialTarget:
    """A navigation control, including a disabled boundary control."""

    direction: str
    label: str
    destination: TutorialCard | None


@dataclass(frozen=True, slots=True)
class TutorialStack:
    tour: tuple[TutorialCard, ...]
    sympy_leaves: tuple[TutorialCard, ...]
    sections: tuple[TutorialCard, ...]
    contents: TutorialCard

    def get(self, identifier: str) -> TutorialCard:
        for card in (*self.tour, *self.sympy_leaves, *self.sections, self.contents):
            if card.identifier == identifier:
                return card
        raise KeyError(identifier)


def make_tutorial_stack() -> TutorialStack:
    """Build the local tour without consulting any external service."""

    definitions = (
        (
            "presentations", "1. Presentations",
            (
                "History keeps an object together with the text you see.",
                "Run 1 + 2 + 3 to get a value holding 6.",
                "At an empty prompt, click that value to show its detail.",
                "Try loads the line; Enter runs it.",
            ),
            (TutorialExample(PythonInput((("1 + 2 + 3",),)), "1 + 2 + 3"),),
        ),
        (
            "commands", "2. Colon commands",
            (
                "Commands start with a colon in the same editor.",
                "Use :ls to list the current directory.",
                "The results keep file and directory objects you can click.",
                "Try loads :ls; Enter lists the directory.",
            ),
            (TutorialExample(CommandInput("ls"), ":ls"),),
        ),
        (
            "values", "3. Reuse a value",
            (
                "Run the first card's example so 6 is in history.",
                "Type 10 + , then click the 6 result.",
                "The editor inserts a chip for that exact object.",
                "Press Enter to evaluate the completed expression.",
            ),
            (),
        ),
        (
            "menus", "4. The right-button menu",
            (
                "Point at a history object and read the documentation line.",
                "Right-click an object with actions to open its menu.",
                "Choose an item to run it; Esc or Ctrl-G closes the menu.",
                "The action uses the object you pointed at.",
            ),
            (),
        ),
        (
            "yank", "5. Bring input back",
            (
                "A submitted Python form or colon command stays in history.",
                "At an empty prompt, click its input row to load it again.",
                "Edit the line if you like; Enter submits it.",
                "Right-click the row and choose yank for the same load.",
            ),
            (),
        ),
    )
    tour = tuple(
        TutorialCard(
            identifier, title, body, examples,
            previous=TutorialLink("Back", definitions[index - 1][0] if index else None),
            next=TutorialLink(
                "Next", definitions[index + 1][0]
                if index + 1 < len(definitions) else None,
            ),
            contents=TutorialLink("Up", "listener"),
        )
        for index, (identifier, title, body, examples) in enumerate(definitions)
    )
    sympy_definitions = (
        (
            "sympy-import", "1. Import",
            (
                "Import SymPy to make the sympy name available.",
                "Enter adds an input row but no value row.",
                "Later cards use that name.",
            ),
            "import sympy",
        ),
        (
            "sympy-symbol", "2. Symbol",
            (
                "This binds x to a SymPy symbol.",
                "Enter adds an input row but no value row.",
                "Later cards use x.",
            ),
            'x = sympy.Symbol("x")',
        ),
        (
            "sympy-expand", "3. Expand",
            (
                "Enter (x + 1)**2 to keep the power in history.",
                "Open that expression row's menu and choose expand.",
                "A new row shows x**2 + 2*x + 1.",
                "The original power stays in history.",
            ),
            "(x + 1)**2",
        ),
        (
            "sympy-factor", "4. Factor",
            (
                "Enter x**2 - 1 to keep the polynomial in history.",
                "Open that expression row's menu and choose factor.",
                "A new row shows (x - 1)⋅(x + 1).",
                "The original polynomial stays in history.",
            ),
            "x**2 - 1",
        ),
    )
    sympy_leaves = tuple(
        TutorialCard(
            identifier, title, body,
            (TutorialExample(PythonInput(((source,),)), source),),
            previous=TutorialLink(
                "Back", sympy_definitions[index - 1][0] if index else None,
            ),
            next=TutorialLink(
                "Next", sympy_definitions[index + 1][0]
                if index + 1 < len(sympy_definitions) else None,
            ),
            contents=TutorialLink("Up", "sympy"),
        )
        for index, (identifier, title, body, source) in enumerate(sympy_definitions)
    )
    sections = (
        TutorialCard(
            "listener", "Listener", ("Choose a card to append it to history.",),
            contents=TutorialLink("Up", "contents"), entries=tour,
        ),
        TutorialCard(
            "sympy", "SymPy",
            (
                "A SymPy expression stays a live object in history.",
                "Its menu can simplify, expand, or factor it.",
                "Import and a symbol come before the examples.",
                "Up returns here from any of these cards.",
            ),
            contents=TutorialLink("Up", "contents"), entries=sympy_leaves,
        ),
    )
    contents = TutorialCard(
        "contents", "Contents", ("Choose a card to append it to history.",),
        entries=sections,
    )
    return TutorialStack(tour, sympy_leaves, sections, contents)


def _target(link: TutorialLink, stack: TutorialStack) -> TutorialTarget:
    destination = None if link.destination_id is None else stack.get(link.destination_id)
    label = (
        f"Up: {destination.title}"
        if link.direction == "Up" and destination else link.direction
    )
    return TutorialTarget(link.direction, label, destination)


def _control(
    value: TutorialTarget | TutorialExample,
    context: DrawingContext,
    types: DomainTypes,
    label: str,
) -> PresentedFragment:
    control_type = (
        types.tutorial_target if isinstance(value, TutorialTarget) else types.tutorial_try
    )
    fragment = context.present(value, control_type)
    return PresentedFragment(
        fragment.presentation_id, (LiteralFragment("[" + escape_display(label) + "]"),)
    )


def tutorial_rows(
    card: TutorialCard,
    stack: TutorialStack,
    context: DrawingContext,
    types: DomainTypes,
) -> tuple[HistoryRow, ...]:
    """Draw a fresh outer presentation over every logical row of a card."""

    outer_fragment = context.present(card, types.tutorial_card)
    outer = context.presentation(outer_fragment.presentation_id)

    def row(*parts: str | PresentedFragment) -> HistoryRow:
        children = context.row(*parts).fragments
        return context.row(PresentedFragment(outer.id, children))

    title_row = row(escape_display(card.title))
    body_lines = tuple(
        part
        for line in card.body
        for part in wrap_display(escape_display(line), 120)
    )
    example_rows = tuple(
        row(_control(example, context, types, "Try"), " ", escape_display(example.source))
        for example in card.examples
    )
    entry_rows = tuple(
        row(_control(TutorialTarget("Contents", entry.title, entry), context, types, entry.title))
        for entry in card.entries
    )
    navigation: tuple[HistoryRow, ...] = ()
    if card.contents is not None:
        up = _target(card.contents, stack)
        if card.entries:
            if card.previous is not None or card.next is not None:
                raise ValueError("a section cannot have sibling links")
            navigation = (row(_control(up, context, types, up.label)),)
        else:
            if card.previous is None or card.next is None:
                raise ValueError("a leaf needs both boundary links")
            navigation = (
                row(
                    _control(_target(card.previous, stack), context, types, "Back"),
                    "  ",
                    _control(_target(card.next, stack), context, types, "Next"),
                    "  ",
                    _control(up, context, types, up.label),
                ),
            )

    body_budget = max(0, 20 - 1 - len(example_rows) - len(entry_rows) - len(navigation))
    if len(body_lines) > body_budget:
        if body_budget == 0:
            raise ValueError("card controls leave no row for a cut marker")
        body_lines = body_lines[: body_budget - 1] + ("… (card text cut)",)
    return (
        title_row,
        *(row(line) for line in body_lines),
        *example_rows,
        *entry_rows,
        *navigation,
    )


def append_tutorial_card(
    history: PresentationHistory,
    context: DrawingContext,
    types: DomainTypes,
    stack: TutorialStack,
    card: TutorialCard,
) -> Presentation:
    rows = tutorial_rows(card, stack, context, types)
    outer = rows[0].presentations[0]
    for row in rows:
        history.append(row)
    return outer
