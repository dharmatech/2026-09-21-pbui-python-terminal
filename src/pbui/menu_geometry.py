"""Terminal-cell geometry for a bordered action menu.

This module intentionally has no terminal toolkit dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from pbui.text import display_width


@dataclass(frozen=True, slots=True)
class CellRect:
    x: int
    y: int
    width: int
    height: int

    def contains(self, x: int, y: int) -> bool:
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height


@dataclass(frozen=True, slots=True)
class MenuGeometry:
    rect: CellRect
    anchor: tuple[int, int]
    labels: tuple[str, ...]

    def item_at(self, x: int, y: int) -> int | None:
        if not self.rect.contains(x, y):
            return None
        if not self.rect.x < x < self.rect.x + self.rect.width - 1:
            return None
        index = y - self.rect.y - 1
        return index if 0 <= index < len(self.labels) else None

    def row_text(self, y: int) -> str:
        width = self.rect.width
        if y == self.rect.y:
            return "┌" + "─" * (width - 2) + "┐"
        if y == self.rect.y + self.rect.height - 1:
            return "└" + "─" * (width - 2) + "┘"
        label = self.labels[y - self.rect.y - 1]
        return "│ " + label + " " * (width - 4 - display_width(label)) + " │"


def measure_menu(labels: Iterable[str]) -> tuple[int, int]:
    labels = tuple(labels)
    return max((display_width(label) for label in labels), default=0) + 4, len(labels) + 2


def place_menu(
    labels: Iterable[str], bounds: CellRect, anchor: tuple[int, int]
) -> MenuGeometry | None:
    labels = tuple(labels)
    if not labels:
        return None
    width, height = measure_menu(labels)
    if width > bounds.width or height > bounds.height:
        return None
    x = min(max(anchor[0], bounds.x), bounds.x + bounds.width - width)
    y = min(max(anchor[1], bounds.y), bounds.y + bounds.height - height)
    return MenuGeometry(CellRect(x, y, width, height), anchor, labels)


def opening_anchor(
    pointer: tuple[int, int] | None,
    pointer_hits_target: bool,
    visible_cells: Iterable[tuple[int, int]],
) -> tuple[int, int] | None:
    """Use the pointer on the target, otherwise its first visible cell."""

    if pointer_hits_target and pointer is not None:
        return pointer
    return min(visible_cells, key=lambda cell: (cell[1], cell[0]), default=None)
