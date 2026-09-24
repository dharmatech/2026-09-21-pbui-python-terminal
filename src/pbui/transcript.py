"""Immutable submitted-input records and their headless history drawings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pbui.chips import Piece
from pbui.domain import escape_display
from pbui.substrate import Chip, Presentation, PresentationHistory, PresentationType
from pbui.text import (
    DrawingContext,
    HistoryRow,
    LiteralFragment,
    PresentedFragment,
    truncate_display,
    wrap_display,
)


@dataclass(frozen=True, slots=True)
class PythonInput:
    lines: tuple[tuple[Piece, ...], ...]


@dataclass(frozen=True, slots=True)
class CommandInput:
    tail: str
    chip: Chip | None = None


@dataclass(frozen=True, slots=True)
class MenuActionInput:
    label: str
    operation: Callable[..., Any]
    argument: str | None
    target: object
    target_label: str
    kind: str
    operation_name: str | None = None


def python_line_text(line: tuple[Piece, ...]) -> str:
    return "".join(
        escape_display(piece) if isinstance(piece, str)
        else f"⟨{escape_display(piece.label)}⟩"
        for piece in line
    )


def _python_source_lines(value: PythonInput) -> tuple[str, ...]:
    """Keep saved source newlines separate from display escaping."""

    lines: list[str] = []
    for saved_line in value.lines:
        parts = [""]
        for piece in saved_line:
            if isinstance(piece, str):
                split = piece.split("\n")
                parts[-1] += escape_display(split[0])
                for part in split[1:]:
                    parts.append(escape_display(part))
            else:
                parts[-1] += f"⟨{escape_display(piece.label)}⟩"
        lines.extend(parts)
    return tuple(lines)


def _safe_captured_target(text: str) -> str:
    """Preserve already escaped history text while escaping raw controls."""

    return "".join(
        character if character == "\\" else escape_display(character)
        for character in text
    )


def input_text(value: PythonInput | CommandInput | MenuActionInput) -> tuple[str, ...]:
    if isinstance(value, PythonInput):
        rows = tuple(
            "› " + part
            for source_line in _python_source_lines(value)
            for part in wrap_display(source_line, 118)
        )
        if len(rows) > 12:
            return rows[:11] + (f"› … ({len(rows) - 11} more input rows)",)
        return rows
    if isinstance(value, CommandInput):
        chip = value.chip
        suffix = (
            "" if chip is None else
            f" ⟨{escape_display(chip.type.name)}: {escape_display(chip.label)}⟩"
        )
        return (truncate_display("› :" + escape_display(value.tail) + suffix, 120),)
    argument = (
        escape_display(" " + value.argument)
        if value.label == "narrow" and value.argument is not None
        else ""
    )
    target = truncate_display(_safe_captured_target(value.target_label), 96)
    return (
        truncate_display(
            "› " + escape_display(value.label) + argument + " — " + target,
            120,
        ),
    )


def append_input(
    history: PresentationHistory,
    context: DrawingContext,
    value: PythonInput | CommandInput | MenuActionInput,
    presentation_type: PresentationType,
) -> Presentation:
    """Append one or more marked rows belonging to the same presentation."""

    texts = input_text(value)
    fragment = context.present(value, presentation_type)
    presentation = context.presentation(fragment.presentation_id)
    for text in texts:
        history.append(
            HistoryRow(
                (PresentedFragment(presentation.id, (LiteralFragment(text),)),),
                (presentation,),
            )
        )
    return presentation
