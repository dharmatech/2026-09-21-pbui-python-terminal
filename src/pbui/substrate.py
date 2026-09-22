"""Application-independent presentation values and state.

This module deliberately knows nothing about terminal rendering or application
domain objects.  Presentation types are explicit tokens, and compatibility is
therefore based on token identity rather than Python value classes.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    from pbui.text import HistoryRow


@dataclass(frozen=True, eq=False, slots=True)
class PresentationType:
    """An immutable, identity-compared presentation type token."""

    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("a presentation type name must be a nonempty string")


class PresentationTypeRegistry:
    """Explicitly register presentation types by their stable names."""

    def __init__(self) -> None:
        self._by_name: dict[str, PresentationType] = {}

    def register(self, name: str) -> PresentationType:
        if name in self._by_name:
            raise ValueError(f"presentation type {name!r} is already registered")
        presentation_type = PresentationType(name)
        self._by_name[name] = presentation_type
        return presentation_type

    def lookup(self, name: str) -> PresentationType:
        try:
            return self._by_name[name]
        except KeyError:
            raise KeyError(f"unknown presentation type {name!r}") from None

    def get(self, name: str) -> PresentationType | None:
        return self._by_name.get(name)

    def __contains__(self, name: object) -> bool:
        return name in self._by_name

    def __iter__(self) -> Iterator[PresentationType]:
        return iter(self._by_name.values())

    def __len__(self) -> int:
        return len(self._by_name)


@dataclass(frozen=True, slots=True)
class DisplayInterval:
    """A half-open interval occupied by a presentation on a physical row."""

    physical_row: int
    start_column: int
    end_column: int
    nesting_depth: int = 0
    draw_order: int = 0

    def __post_init__(self) -> None:
        if self.physical_row < 0:
            raise ValueError("physical_row must be nonnegative")
        if self.start_column < 0 or self.end_column <= self.start_column:
            raise ValueError("a display interval must be nonempty and half-open")
        if self.nesting_depth < 0 or self.draw_order < 0:
            raise ValueError("nesting depth and draw order must be nonnegative")

    def contains(self, x: int, y: int) -> bool:
        return (
            y == self.physical_row
            and self.start_column <= x < self.end_column
        )


@dataclass(eq=False, slots=True)
class Presentation:
    """A retained Python value plus replaceable, layout-derived intervals."""

    id: int
    presentation_type: PresentationType
    value: Any
    intervals: tuple[DisplayInterval, ...] = field(default_factory=tuple)

    @property
    def type(self) -> PresentationType:
        """A concise alias useful to acceptance and translation callers."""

        return self.presentation_type

    def replace_intervals(self, intervals: tuple[DisplayInterval, ...]) -> None:
        """Replace all derived intervals in one operation."""

        self.intervals = intervals


class PresentationHistory:
    """A bounded collection of logical rows and their presentations."""

    MAX_LOGICAL_ROWS = 500

    def __init__(self, max_rows: int = MAX_LOGICAL_ROWS) -> None:
        if max_rows < 1:
            raise ValueError("history must retain at least one logical row")
        self._max_rows = max_rows
        self._rows: deque[HistoryRow] = deque()
        self._presentations: dict[int, Presentation] = {}
        self._reference_counts: dict[int, int] = {}
        self._revision = 0

    @property
    def rows(self) -> tuple[HistoryRow, ...]:
        return tuple(self._rows)

    @property
    def presentations(self) -> tuple[Presentation, ...]:
        return tuple(self._presentations.values())

    @property
    def revision(self) -> int:
        """A generation used to reject hit tests against stale layouts."""

        return self._revision

    def __len__(self) -> int:
        return len(self._rows)

    def append(self, row: HistoryRow) -> None:
        row_presentations = {item.id: item for item in row.presentations}
        referred_ids = set(row.presentation_ids)
        if referred_ids != set(row_presentations):
            raise ValueError(
                "a history row must carry exactly the presentations its drawing refers to"
            )

        for presentation_id, presentation in row_presentations.items():
            retained = self._presentations.get(presentation_id)
            if retained is not None and retained is not presentation:
                raise ValueError(f"presentation id {presentation_id} is not unique")
            self._presentations[presentation_id] = presentation
            self._reference_counts[presentation_id] = (
                self._reference_counts.get(presentation_id, 0) + 1
            )

        self._rows.append(row)
        if len(self._rows) > self._max_rows:
            self._discard_oldest()
        self._revision += 1

    def get_presentation(self, presentation_id: int) -> Presentation | None:
        return self._presentations.get(presentation_id)

    def lookup(self, presentation_id: int) -> Presentation:
        try:
            return self._presentations[presentation_id]
        except KeyError:
            raise KeyError(f"presentation {presentation_id!r} is not retained") from None

    def _discard_oldest(self) -> None:
        oldest = self._rows.popleft()
        for presentation_id in set(oldest.presentation_ids):
            remaining = self._reference_counts[presentation_id] - 1
            if remaining:
                self._reference_counts[presentation_id] = remaining
                continue
            del self._reference_counts[presentation_id]
            presentation = self._presentations.pop(presentation_id)
            presentation.replace_intervals(())


@dataclass(frozen=True, slots=True)
class Chip:
    """One atomic input argument backed by an original presented object."""

    presentation_type: PresentationType
    value: Any
    label: str

    @property
    def type(self) -> PresentationType:
        return self.presentation_type


Continuation: TypeAlias = Callable[[Chip], None]


@dataclass(frozen=True, slots=True)
class AcceptRequest:
    """A pending request for exactly one of a set of presentation types."""

    command_name: str
    acceptable_types: frozenset[PresentationType]
    continuation: Continuation

    def __post_init__(self) -> None:
        if not isinstance(self.command_name, str) or not self.command_name.strip():
            raise ValueError("an accept request needs a nonempty command name")
        acceptable_types = frozenset(self.acceptable_types)
        if not acceptable_types:
            raise ValueError("an accept request needs at least one acceptable type")
        if not all(isinstance(item, PresentationType) for item in acceptable_types):
            raise TypeError("acceptable types must be PresentationType entries")
        object.__setattr__(self, "acceptable_types", acceptable_types)
        if not callable(self.continuation):
            raise TypeError("an accept continuation must be callable")


@dataclass(slots=True)
class SubstrateState:
    """The small atomic-input state machine needed by later controllers."""

    input_text: str = ""
    pending_request: AcceptRequest | None = None
    chip: Chip | None = None

    def begin_accept(self, request: AcceptRequest) -> None:
        self.pending_request = request

    def select_presentation(self, presentation: Presentation, label: str) -> bool:
        request = self.pending_request
        if request is None or presentation.presentation_type not in request.acceptable_types:
            return False

        chip = Chip(presentation.presentation_type, presentation.value, label)
        self.chip = chip
        self.pending_request = None
        request.continuation(chip)
        return True

    def cancel(self) -> None:
        self.pending_request = None
        self.chip = None

    def backspace(self) -> bool:
        if self.chip is None:
            return False
        self.chip = None
        return True


Translator: TypeAlias = Callable[[Any], Any]


class TranslatorTable:
    """Explicit translators keyed by exact presentation-type identity."""

    def __init__(self) -> None:
        self._translators: dict[PresentationType, Translator] = {}

    def register(
        self, presentation_type: PresentationType, translator: Translator
    ) -> None:
        if presentation_type in self._translators:
            raise ValueError(
                f"a translator is already registered for {presentation_type.name!r}"
            )
        if not callable(translator):
            raise TypeError("a translator must be callable")
        self._translators[presentation_type] = translator

    def lookup(self, presentation_type: PresentationType) -> Translator | None:
        return self._translators.get(presentation_type)

    def invoke(self, presentation: Presentation) -> Any | None:
        translator = self.lookup(presentation.presentation_type)
        if translator is None:
            return None
        return translator(presentation.value)
