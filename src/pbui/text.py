"""Logical terminal text, display-column layout, and pure hit testing."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from itertools import count
from typing import Any, TypeAlias

from wcwidth import wcwidth

from pbui.substrate import (
    DisplayInterval,
    Presentation,
    PresentationHistory,
    PresentationType,
)


@dataclass(frozen=True, slots=True)
class LiteralFragment:
    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise TypeError("literal text must be a string")


@dataclass(frozen=True, slots=True)
class PresentedFragment:
    """Logical content associated with a stable presentation id."""

    presentation_id: int
    children: tuple[Fragment, ...]


Fragment: TypeAlias = LiteralFragment | PresentedFragment
FragmentPart: TypeAlias = str | Fragment


def _walk_presentation_ids(fragments: Iterable[Fragment]) -> Iterator[int]:
    for fragment in fragments:
        if isinstance(fragment, PresentedFragment):
            yield fragment.presentation_id
            yield from _walk_presentation_ids(fragment.children)


@dataclass(frozen=True, slots=True)
class HistoryRow:
    """A logical row plus the object-bearing presentations it owns."""

    fragments: tuple[Fragment, ...]
    presentations: tuple[Presentation, ...] = field(default_factory=tuple)

    @property
    def presentation_ids(self) -> tuple[int, ...]:
        return tuple(_walk_presentation_ids(self.fragments))


DrawerContent: TypeAlias = str | Fragment | HistoryRow | Sequence[FragmentPart]
Drawer: TypeAlias = Callable[[Any, "DrawingContext"], DrawerContent]


class DrawerTable:
    """An explicit table of pure text drawers."""

    def __init__(self) -> None:
        self._drawers: dict[PresentationType, Drawer] = {}

    def register(self, presentation_type: PresentationType, drawer: Drawer) -> None:
        if presentation_type in self._drawers:
            raise ValueError(
                f"a drawer is already registered for {presentation_type.name!r}"
            )
        if not callable(drawer):
            raise TypeError("a drawer must be callable")
        self._drawers[presentation_type] = drawer

    def lookup(self, presentation_type: PresentationType) -> Drawer:
        try:
            return self._drawers[presentation_type]
        except KeyError:
            raise KeyError(
                f"no drawer registered for presentation type "
                f"{presentation_type.name!r}"
            ) from None


_presentation_ids = count(1)


class DrawingContext:
    """Create presentations and their separate logical drawings."""

    def __init__(self, drawers: DrawerTable | None = None) -> None:
        self.drawers = drawers if drawers is not None else DrawerTable()
        self._presentations: dict[int, Presentation] = {}

    def register_drawer(
        self, presentation_type: PresentationType, drawer: Drawer
    ) -> None:
        self.drawers.register(presentation_type, drawer)

    def lookup_drawer(self, presentation_type: PresentationType) -> Drawer:
        return self.drawers.lookup(presentation_type)

    def present(
        self, value: Any, presentation_type: PresentationType
    ) -> PresentedFragment:
        drawer = self.lookup_drawer(presentation_type)
        presentation = Presentation(next(_presentation_ids), presentation_type, value)
        self._presentations[presentation.id] = presentation
        try:
            content = drawer(value, self)
            children = self._coerce_content(content)
        except BaseException:
            del self._presentations[presentation.id]
            raise
        return PresentedFragment(presentation.id, children)

    def row(self, *parts: FragmentPart) -> HistoryRow:
        fragments = self._coerce_parts(parts)
        seen: set[int] = set()
        presentations: list[Presentation] = []
        for presentation_id in _walk_presentation_ids(fragments):
            if presentation_id in seen:
                continue
            try:
                presentation = self._presentations[presentation_id]
            except KeyError:
                raise ValueError(
                    f"presentation {presentation_id!r} was not created by this context"
                ) from None
            seen.add(presentation_id)
            presentations.append(presentation)
        return HistoryRow(fragments, tuple(presentations))

    def present_row(
        self, value: Any, presentation_type: PresentationType
    ) -> HistoryRow:
        return self.row(self.present(value, presentation_type))

    def presentation(self, presentation_id: int) -> Presentation:
        try:
            return self._presentations[presentation_id]
        except KeyError:
            raise KeyError(f"unknown presentation {presentation_id!r}") from None

    @staticmethod
    def _coerce_parts(parts: Iterable[FragmentPart]) -> tuple[Fragment, ...]:
        result: list[Fragment] = []
        for part in parts:
            if isinstance(part, str):
                result.append(LiteralFragment(part))
            elif isinstance(part, (LiteralFragment, PresentedFragment)):
                result.append(part)
            else:
                raise TypeError(f"unsupported drawing fragment {part!r}")
        return tuple(result)

    def _coerce_content(self, content: DrawerContent) -> tuple[Fragment, ...]:
        if isinstance(content, HistoryRow):
            return content.fragments
        if isinstance(content, (str, LiteralFragment, PresentedFragment)):
            return self._coerce_parts((content,))
        return self._coerce_parts(content)


def present(
    value: Any,
    presentation_type: PresentationType,
    drawing_context: DrawingContext,
) -> PresentedFragment:
    """Create a presented fragment through the context's exact drawer table."""

    return drawing_context.present(value, presentation_type)


@dataclass(frozen=True, slots=True)
class RenderedRow:
    """One physical row produced by wrapping one retained logical row."""

    text: str
    logical_row: int
    display_width: int


@dataclass(frozen=True, slots=True)
class Layout:
    """Rendered rows plus the exact presentations supplying their hit regions."""

    width: int
    rows: tuple[RenderedRow, ...]
    presentations: tuple[Presentation, ...]
    _history: PresentationHistory = field(repr=False, compare=False)
    _history_revision: int = field(repr=False, compare=False)

    def hit_test(self, x: int, y: int) -> Presentation | None:
        if self._history.revision != self._history_revision:
            return None
        if x < 0 or y < 0 or x >= self.width or y >= len(self.rows):
            return None
        return hit_test(self.presentations, x, y)


def hit_test(
    presentations: Iterable[Presentation], x: int, y: int
) -> Presentation | None:
    """Return the deepest, then last-drawn, presentation containing a cell."""

    if x < 0 or y < 0:
        return None
    winner: Presentation | None = None
    winner_key = (-1, -1)
    for presentation in presentations:
        for interval in presentation.intervals:
            if interval.contains(x, y):
                key = (interval.nesting_depth, interval.draw_order)
                if key >= winner_key:
                    winner = presentation
                    winner_key = key
    return winner


def layout(history: PresentationHistory, width: int) -> Layout:
    """Lay out all retained logical rows in terminal display columns."""

    normalized_width = max(1, width)
    presentations = history.presentations
    by_id = {presentation.id: presentation for presentation in presentations}
    interval_lists: dict[int, list[DisplayInterval]] = {
        presentation.id: [] for presentation in presentations
    }
    for presentation in presentations:
        presentation.replace_intervals(())

    rendered_rows: list[RenderedRow] = []
    physical_row = 0
    draw_order = 0

    for logical_row_number, logical_row in enumerate(history.rows):
        row_chunks: list[list[str]] = [[]]
        row_widths = [0]
        column = 0

        def draw_fragments(
            fragments: Iterable[Fragment], active: tuple[int, ...] = ()
        ) -> None:
            nonlocal column, draw_order, physical_row
            for fragment in fragments:
                if isinstance(fragment, LiteralFragment):
                    text = fragment.text
                    next_active = active
                else:
                    if fragment.presentation_id not in by_id:
                        raise ValueError(
                            f"logical row refers to unretained presentation "
                            f"{fragment.presentation_id!r}"
                        )
                    draw_fragments(
                        fragment.children, active + (fragment.presentation_id,)
                    )
                    continue

                for character in text:
                    character_width = wcwidth(character)
                    if character_width < 0:
                        raise ValueError(
                            f"unprintable code point U+{ord(character):04X} reached layout"
                        )
                    if (
                        character_width > 0
                        and column > 0
                        and character_width > normalized_width - column
                    ):
                        physical_row += 1
                        row_chunks.append([])
                        row_widths.append(0)
                        column = 0

                    row_chunks[-1].append(character)
                    if character_width == 0:
                        continue

                    draw_order += 1
                    start = column
                    end = column + character_width
                    for depth, presentation_id in enumerate(next_active):
                        _append_interval(
                            interval_lists[presentation_id],
                            DisplayInterval(
                                physical_row,
                                start,
                                end,
                                depth,
                                draw_order,
                            ),
                        )
                    column = end
                    row_widths[-1] = max(row_widths[-1], column)

        draw_fragments(logical_row.fragments)
        for chunks, display_width in zip(row_chunks, row_widths, strict=True):
            rendered_rows.append(
                RenderedRow("".join(chunks), logical_row_number, display_width)
            )
        physical_row += 1

    for presentation in presentations:
        presentation.replace_intervals(tuple(interval_lists[presentation.id]))

    return Layout(
        normalized_width,
        tuple(rendered_rows),
        presentations,
        history,
        history.revision,
    )


def _append_interval(
    intervals: list[DisplayInterval], interval: DisplayInterval
) -> None:
    """Coalesce adjacent cells while retaining last-drawn tie metadata."""

    if intervals:
        previous = intervals[-1]
        if (
            previous.physical_row == interval.physical_row
            and previous.end_column == interval.start_column
            and previous.nesting_depth == interval.nesting_depth
        ):
            intervals[-1] = DisplayInterval(
                previous.physical_row,
                previous.start_column,
                interval.end_column,
                previous.nesting_depth,
                interval.draw_order,
            )
            return
    intervals.append(interval)
