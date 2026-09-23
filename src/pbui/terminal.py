"""Textual drawing, interaction, and lifecycle for the presentation listener.

This is deliberately the package's only Textual boundary.  It adapts the
headless listener without moving presentation identity, wrapping, or hit
testing into widgets.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from rich.style import Style
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.geometry import Offset, Region, Size
from textual.screen import Screen
from textual.scroll_view import ScrollView
from textual.strip import Strip
from textual.widget import Widget

from pbui.commands import HeadlessListener
from pbui.domain import (
    DirectoryListing,
    DirectoryRef,
    FileRef,
    ProcessListing,
    ProcessListingMember,
    ProcessRef,
    escape_display,
)
from pbui.substrate import (
    DisplayInterval,
    Presentation,
    PresentationTypeRegistry,
)
from pbui.text import (
    HistoryRow,
    Layout,
    _character_width,
    display_width,
    layout,
    truncate_display,
)


_UNSET = object()

_PROCESS_STATE_COLORS = {
    "running": "#00d787",
    "sleeping": "#5f87d7",
    "idle": "#5f87d7",
    "disk-sleep": "#d7af00",
    "stopped": "#d787ff",
    "tracing": "#d787ff",
    "zombie": "#ff5f5f",
    "dead": "#ff5f5f",
    "unknown": "#a8a8a8",
}

_SUBSTRING_DOCUMENTATION = (
    "Type a substring and press Enter to narrow this listing; "
    "Ctrl-G or Esc cancels."
)

_MENU_DOCUMENTATION = "Point at an action and click; Ctrl-G or Esc closes the menu."
_DIRECTORY_ACTIONS = (
    "sort name", "sort size", "sort mtime", "only files", "only directories",
    "narrow", "widen",
)
_PROCESS_ACTIONS = (
    "sort pid", "sort state", "sort command", "only running",
    "only sleeping", "only disk-sleep", "only stopped", "only tracing",
    "only zombie", "only dead", "only idle", "only unknown",
    "narrow", "widen",
)


@dataclass(frozen=True, slots=True)
class MenuAction:
    label: str
    operation: str
    argument: str | None
    target: Presentation


@dataclass(frozen=True, slots=True)
class _ViewportAnchor:
    row: HistoryRow
    owner: DirectoryListing | ProcessListing | None
    row_key: Presentation | None
    wrapped_offset: int


def _history_appended(
    before: tuple[HistoryRow, ...], after: tuple[HistoryRow, ...]
) -> bool:
    """Recognize newly appended output without interpreting command text."""

    old_rows = {id(row) for row in before}
    old_owners = {id(row.listing_owner) for row in before if row.listing_owner is not None}
    return any(
        id(row) not in old_rows
        and (row.listing_owner is None or id(row.listing_owner) not in old_owners)
        for row in after
    )


def filter_one_row(text: str) -> str:
    """Keep only printable code points suitable for the one-row editor."""

    if not isinstance(text, str):
        raise TypeError("editor text must be a string")
    return "".join(character for character in text if character.isprintable())


def _domain_kind(
    listener: HeadlessListener, presentation: Presentation | None
) -> str | None:
    """Identify only entries from this listener's exact type registry."""

    if presentation is None:
        return None
    presentation_type = presentation.presentation_type
    types = listener.types
    if presentation_type is types.file and type(presentation.value) is FileRef:
        return "File"
    if (
        presentation_type is types.directory
        and type(presentation.value) is DirectoryRef
    ):
        return "Directory"
    if presentation_type is types.process and type(presentation.value) is ProcessRef:
        return "Process"
    if (
        presentation_type is types.directory_listing
        and type(presentation.value) is DirectoryListing
    ):
        return "DirectoryListing"
    if (
        presentation_type is types.process_listing
        and type(presentation.value) is ProcessListing
    ):
        return "ProcessListing"
    if presentation_type is types.text:
        return "Text"
    if presentation_type is types.error:
        return "Error"
    return None


def _name(presentation: Presentation) -> str:
    value = presentation.value
    if type(value) not in {FileRef, DirectoryRef}:
        raise TypeError("path documentation requires a path presentation")
    return escape_display(os.path.basename(value.path))


def _pid(presentation: Presentation) -> str:
    value = presentation.value
    if type(value) is not ProcessRef:
        raise TypeError("process documentation requires a process presentation")
    return str(value.pid)


def _menu_labels(kind: str | None) -> tuple[str, ...]:
    return {
        "File": ("show", "rm"),
        "Directory": ("show", "cd", "ls"),
        "Process": ("show", "kill"),
        "DirectoryListing": _DIRECTORY_ACTIONS,
        "ProcessListing": _PROCESS_ACTIONS,
    }.get(kind, ())


def _menu_refusal(target: Presentation | None, kind: str | None) -> str:
    if target is None:
        return "Point at a presentation before opening an action menu."
    if kind == "Text":
        return "Text has no action menu."
    if kind == "Error":
        return "Error has no action menu."
    return "This presentation has no action menu."


def _menu_item_documentation(action: MenuAction, listener: HeadlessListener) -> str:
    target = action.target
    kind = _domain_kind(listener, target)
    label = action.label
    if kind == "File":
        return f"Click to run “{label}” for file “{_name(target)}”."
    if kind == "Directory":
        return f"Click to run “{label}” for directory “{_name(target)}”."
    if kind == "Process":
        return f"Click to run “{label}” for process {_pid(target)}."
    if kind == "DirectoryListing":
        return f"Click to apply “{label}” to this directory listing."
    if kind == "ProcessListing":
        return f"Click to apply “{label}” to this process listing."
    raise AssertionError("menu action requires an actionable target")


def _captured_process_member(
    listener: HeadlessListener, presentation: Presentation
) -> ProcessListingMember | None:
    """Find a process row's immutable captured record by presentation identity."""

    seen_listings: set[int] = set()
    for row in listener.history.rows:
        listing = row.listing_owner
        if type(listing) is not ProcessListing or id(listing) in seen_listings:
            continue
        seen_listings.add(id(listing))
        for member, member_presentation in zip(
            listing.members, listing.member_presentations, strict=True
        ):
            if member_presentation is presentation:
                return member
    return None


def format_documentation(
    listener: HeadlessListener,
    presentation: Presentation | None,
    logical_column: int | None = None,
) -> str:
    """Return the exact documentation sentence for the current pointer state."""

    if listener.pending_substring_listing is not None:
        return _SUBSTRING_DOCUMENTATION

    kind = _domain_kind(listener, presentation)
    request = listener.pending_request
    if request is None:
        if kind == "File":
            assert presentation is not None
            return f"Click to show file “{_name(presentation)}”."
        if kind == "Directory":
            assert presentation is not None
            return f"Click to show directory “{_name(presentation)}”."
        if kind == "Process":
            assert presentation is not None
            member = _captured_process_member(listener, presentation)
            if (
                member is not None
                and logical_column is not None
                and 42 <= logical_column < 90
                and display_width(member.command) > 48
            ):
                return (
                    "Command is truncated; click to show the full command "
                    f"for process {_pid(presentation)}."
                )
            return f"Click to show process {_pid(presentation)}."
        if kind == "DirectoryListing":
            return "Directory listing: Ctrl-O or right-click to open its view menu."
        if kind == "ProcessListing":
            return "Process listing: Ctrl-O or right-click to open its view menu."
        if kind == "Text":
            return "Text has no default click action."
        if kind == "Error":
            return "Error has no default click action."
        return "No presentation under pointer."

    command = request.command_name
    if kind in {"DirectoryListing", "ProcessListing"}:
        accepted = {
            "rm": "File",
            "cd": "Directory",
            "kill": "Process",
            "show": "File, Directory, or Process",
        }[command]
        subject = (
            "directory listing" if kind == "DirectoryListing" else "process listing"
        )
        return (
            f"Accept {accepted} for {command}: {subject} is not a {accepted} target."
        )
    if command == "rm":
        prefix = "Accept File for rm:"
        if kind is None:
            return (
                f"{prefix} point to a highlighted File and click; "
                "Ctrl-G or Esc cancels."
            )
        if kind == "File":
            assert presentation is not None
            return f"{prefix} click to use file “{_name(presentation)}” and run rm."
        if kind == "Directory":
            assert presentation is not None
            return f"{prefix} directory “{_name(presentation)}” is not a File target."
        if kind == "Process":
            assert presentation is not None
            return f"{prefix} process {_pid(presentation)} is not a File target."
        return f"{prefix} {kind} is not a File target."

    if command == "cd":
        prefix = "Accept Directory for cd:"
        if kind is None:
            return (
                f"{prefix} point to a highlighted Directory and click; "
                "Ctrl-G or Esc cancels."
            )
        if kind == "Directory":
            assert presentation is not None
            return (
                f"{prefix} click to use directory “{_name(presentation)}” and run cd."
            )
        if kind == "File":
            assert presentation is not None
            return (
                f"{prefix} file “{_name(presentation)}” is not a Directory target."
            )
        if kind == "Process":
            assert presentation is not None
            return f"{prefix} process {_pid(presentation)} is not a Directory target."
        return f"{prefix} {kind} is not a Directory target."

    if command == "kill":
        prefix = "Accept Process for kill:"
        if kind is None:
            return (
                f"{prefix} point to a highlighted Process and click; "
                "Ctrl-G or Esc cancels."
            )
        if kind == "Process":
            assert presentation is not None
            return f"{prefix} click to use process {_pid(presentation)} and run kill."
        if kind == "File":
            assert presentation is not None
            return f"{prefix} file “{_name(presentation)}” is not a Process target."
        if kind == "Directory":
            assert presentation is not None
            return (
                f"{prefix} directory “{_name(presentation)}” "
                "is not a Process target."
            )
        return f"{prefix} {kind} is not a Process target."

    if command == "show":
        accepted = "File, Directory, or Process"
        prefix = f"Accept {accepted} for show:"
        if kind is None:
            return (
                f"{prefix} point to a highlighted {accepted} and click; "
                "Ctrl-G or Esc cancels."
            )
        if kind == "File":
            assert presentation is not None
            return f"{prefix} click to use file “{_name(presentation)}” and run show."
        if kind == "Directory":
            assert presentation is not None
            return (
                f"{prefix} click to use directory “{_name(presentation)}” "
                "and run show."
            )
        if kind == "Process":
            assert presentation is not None
            return f"{prefix} click to use process {_pid(presentation)} and run show."
        return f"{prefix} {kind} is not a {accepted} target."

    # HeadlessListener never creates another accept request.  Keeping this
    # fallback literal and non-domain-specific makes malformed external state
    # harmless without inventing product wording.
    return "No presentation under pointer."


def format_prompt(listener: HeadlessListener) -> str:
    """Return the literal prompt derived from the listener's own cwd."""

    return f"pbui:{escape_display(listener.cwd)}> "


def presentation_style(
    listener: HeadlessListener,
    presentation: Presentation,
    hovered_presentation: Presentation | None,
) -> Style:
    """Map one retained presentation to its complete interaction style."""

    request = listener.pending_request
    if request is not None:
        acceptable = presentation.presentation_type in request.acceptable_types
        if acceptable:
            return Style(
                color="#00d787",
                bold=True,
                underline=True,
                dim=False,
                reverse=presentation is hovered_presentation,
            )
        return Style(
            color="#808080",
            bold=False,
            underline=False,
            dim=True,
            reverse=False,
        )

    kind = _domain_kind(listener, presentation)
    color = "default"
    bold = False
    if kind == "Error":
        color = "red"
    elif kind == "Directory":
        color = "#00afff"
    elif kind == "Process":
        member = _captured_process_member(listener, presentation)
        if member is not None:
            color = _PROCESS_STATE_COLORS[member.state]
    elif kind in {"DirectoryListing", "ProcessListing"}:
        bold = True
    return Style(
        color=color,
        bold=bold,
        underline=False,
        dim=False,
        reverse=presentation is hovered_presentation,
    )


def _interval_character_ranges(
    row_text: str, interval: DisplayInterval
) -> tuple[tuple[int, int], ...]:
    """Translate one display-cell interval to row-local code-point ranges."""

    selected: list[int] = []
    column = 0
    owning_base_selected = False
    for index, character in enumerate(row_text):
        width = _character_width(character)
        if width == 0:
            if owning_base_selected:
                selected.append(index)
            continue

        start = column
        end = column + width
        owning_base_selected = (
            start >= interval.start_column and end <= interval.end_column
        )
        if owning_base_selected:
            selected.append(index)
        column = end

    if not selected:
        return ()
    ranges: list[tuple[int, int]] = []
    start = previous = selected[0]
    for index in selected[1:]:
        if index != previous + 1:
            ranges.append((start, previous + 1))
            start = index
        previous = index
    ranges.append((start, previous + 1))
    return tuple(ranges)


StyledInterval = tuple[int, int, int, Presentation, DisplayInterval]


def _styled_intervals_by_row(
    current_layout: Layout,
) -> tuple[tuple[StyledInterval, ...], ...]:
    """Index presentation intervals in their deterministic drawing order."""

    intervals_by_row: list[list[StyledInterval]] = [
        [] for _ in current_layout.rows
    ]
    for presentation_index, presentation in enumerate(current_layout.presentations):
        for interval in presentation.intervals:
            if interval.physical_row >= len(intervals_by_row):
                continue
            intervals_by_row[interval.physical_row].append(
                (
                    interval.nesting_depth,
                    interval.draw_order,
                    presentation_index,
                    presentation,
                    interval,
                )
            )
    return tuple(tuple(sorted(intervals)) for intervals in intervals_by_row)


def build_history_row_text(
    listener: HeadlessListener,
    current_layout: Layout,
    physical_row: int,
    hovered_presentation: Presentation | None = None,
    *,
    styled_intervals: tuple[StyledInterval, ...] | None = None,
) -> Text:
    """Build one Rich renderable directly from one pure-layout row."""

    row_text = current_layout.rows[physical_row].text
    renderable = Text(row_text, no_wrap=True, overflow="crop")
    if styled_intervals is None:
        styled_intervals = _styled_intervals_by_row(current_layout)[physical_row]

    for _, _, _, presentation, interval in styled_intervals:
        style = presentation_style(listener, presentation, hovered_presentation)
        for start, end in _interval_character_ranges(row_text, interval):
            renderable.stylize(style, start, end)
    return renderable


def _compose_history_text(line_texts: list[Text] | tuple[Text, ...]) -> Text:
    """Compose the compatibility view from independently built row objects."""

    renderable = Text(no_wrap=True, overflow="crop")
    for physical_row, line in enumerate(line_texts):
        if physical_row:
            renderable.append("\n")
        renderable.append(line)
    return renderable


def build_history_text(
    listener: HeadlessListener,
    current_layout: Layout,
    hovered_presentation: Presentation | None = None,
) -> Text:
    """Build the compatibility view from direct per-row Rich renderables."""

    intervals_by_row = _styled_intervals_by_row(current_layout)
    line_texts = [
        build_history_row_text(
            listener,
            current_layout,
            physical_row,
            hovered_presentation,
            styled_intervals=intervals_by_row[physical_row],
        )
        for physical_row in range(len(current_layout.rows))
    ]
    return _compose_history_text(line_texts)


class HistorySurface(ScrollView):
    """The sole scrollable widget, drawing the listener's complete history."""

    can_focus = False

    DEFAULT_CSS = """
    HistorySurface {
        width: 100%;
        height: 1fr;
        overflow-x: hidden;
        overflow-y: auto;
        scrollbar-gutter: stable;
    }
    """

    def __init__(self, listener: HeadlessListener, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.listener = listener
        self.current_layout = layout(listener.history, 1)
        self.hovered_presentation: Presentation | None = None
        self._pointer_offset: Offset | None = None
        self._styled_intervals = _styled_intervals_by_row(self.current_layout)
        self._line_texts = self._build_all_rows()
        self.history_text = _compose_history_text(self._line_texts)
        self._logical_rows = listener.history.rows
        self._history_revision = -1
        self._content_width = 0
        self._viewport_height = 0
        self._pending_request: object = _UNSET
        self._pending_substring_listing: object = _UNSET

    @property
    def history_layout(self) -> Layout:
        """The current pure layout, distinct from Textual's widget layout."""

        return self.current_layout

    @property
    def content_width(self) -> int:
        """Current drawable width, excluding gutters and scrollbars."""

        if not self.is_mounted:
            return max(1, self._content_width)
        return max(1, self.scrollable_content_region.width)

    def _build_row(self, physical_row: int) -> Text:
        return build_history_row_text(
            self.listener,
            self.current_layout,
            physical_row,
            self.hovered_presentation,
            styled_intervals=self._styled_intervals[physical_row],
        )

    def _build_all_rows(self) -> list[Text]:
        return [self._build_row(row) for row in range(len(self.current_layout.rows))]

    def _refresh_physical_rows(self, physical_rows: set[int]) -> None:
        """Repaint only affected rows that are currently in the viewport."""

        if not self.is_mounted:
            self.refresh()
            return
        scroll_y = self.scroll_offset.y
        content_region = self.scrollable_content_region
        regions = tuple(
            Region(0, physical_row - scroll_y, content_region.width, 1)
            for physical_row in sorted(physical_rows)
            if scroll_y <= physical_row < scroll_y + content_region.height
        )
        if regions:
            self.refresh(*regions)

    def _viewport_anchor(self) -> _ViewportAnchor | None:
        if not self.current_layout.rows or not self._logical_rows:
            return None
        physical_row = min(
            max(0, int(self.scroll_y)), len(self.current_layout.rows) - 1
        )
        logical_index = self.current_layout.rows[physical_row].logical_row
        if logical_index >= len(self._logical_rows):
            return None
        first = physical_row
        while first > 0 and self.current_layout.rows[first - 1].logical_row == logical_index:
            first -= 1
        row = self._logical_rows[logical_index]
        owner = row.listing_owner
        listing = owner if type(owner) in {DirectoryListing, ProcessListing} else None
        return _ViewportAnchor(
            row,
            listing,
            row.presentations[0] if listing is not None and row.presentations else None,
            physical_row - first,
        )

    def _anchored_scroll_y(self, anchor: _ViewportAnchor | None) -> int:
        rows = self._logical_rows
        if not rows or not self.current_layout.rows:
            return 0
        if anchor is None:
            return 0

        logical_index = next((i for i, row in enumerate(rows) if row is anchor.row), None)
        if logical_index is None and anchor.owner is not None:
            owned = [i for i, row in enumerate(rows) if row.listing_owner is anchor.owner]
            if owned:
                for i in owned:
                    presentations = rows[i].presentations
                    if (
                        (anchor.row_key is None and not presentations)
                        or any(item is anchor.row_key for item in presentations)
                    ):
                        logical_index = i
                        break
                if logical_index is None:
                    header = anchor.owner.header_presentation
                    logical_index = next(
                        (
                            i for i in owned
                            if any(item is header for item in rows[i].presentations)
                        ),
                        owned[0],
                    )
        if logical_index is None:
            logical_index = 0

        first = next(
            i for i, row in enumerate(self.current_layout.rows)
            if row.logical_row == logical_index
        )
        stop = first + 1
        while (
            stop < len(self.current_layout.rows)
            and self.current_layout.rows[stop].logical_row == logical_index
        ):
            stop += 1
        return first + min(anchor.wrapped_offset, stop - first - 1)

    def _clamp_scroll_row(self, row: int) -> int:
        viewport_height = (
            self.scrollable_content_region.height if self.is_mounted else 0
        )
        maximum = max(0, len(self.current_layout.rows) - viewport_height)
        return min(max(0, row), maximum)

    def _offset_is_in_content(self, offset: Offset) -> bool:
        if not self.is_mounted:
            return False
        region = self.scrollable_content_region
        return 0 <= offset.x < region.width and 0 <= offset.y < region.height

    def content_offset_from_event(self, event: events.MouseEvent) -> Offset | None:
        """Translate a mouse event to the drawable content viewport."""

        offset = event.get_content_offset(self)
        if offset is None or not self._offset_is_in_content(offset):
            return None
        return offset

    def _hit_at_offset(
        self, offset: Offset, *, scroll_y: int | None = None
    ) -> Presentation | None:
        if not self._offset_is_in_content(offset):
            return None
        physical_row = offset.y + (
            int(self.scroll_y) if scroll_y is None else scroll_y
        )
        return self.current_layout.hit_test(offset.x, physical_row)

    def presentation_at_content_offset(
        self, x: int, y: int
    ) -> Presentation | None:
        """Return a fresh pure-layout hit for a viewport content coordinate."""

        self.synchronize()
        return self._hit_at_offset(Offset(int(x), int(y)))

    @property
    def pointer_offset(self) -> Offset | None:
        """The most recent pointer coordinate inside the content viewport."""

        return self._pointer_offset

    @property
    def pointer_logical_column(self) -> int | None:
        """Logical display column beneath the retained viewport pointer."""

        offset = self._pointer_offset
        if offset is None or not self._offset_is_in_content(offset):
            return None
        physical_row = offset.y + int(self.scroll_y)
        if physical_row < 0 or physical_row >= len(self.current_layout.rows):
            return None
        rendered_row = self.current_layout.rows[physical_row]
        if offset.x >= rendered_row.display_width:
            return None
        logical_row = rendered_row.logical_row
        return offset.x + sum(
            row.display_width
            for row in self.current_layout.rows[:physical_row]
            if row.logical_row == logical_row
        )

    def _recompute_pointer_hover(self, *, scroll_y: int | None = None) -> None:
        if self._pointer_offset is None:
            return
        if not self._offset_is_in_content(self._pointer_offset):
            self.clear_pointer()
            return
        self.set_hovered_presentation(
            self._hit_at_offset(self._pointer_offset, scroll_y=scroll_y)
        )

    def clear_pointer(self) -> None:
        """Forget pointer coordinates and clear all hover-derived drawing."""

        self._pointer_offset = None
        self.set_hovered_presentation(None)

    def synchronize(self, *, force: bool = False) -> bool:
        """Relayout changed history/width and refresh all derived drawing state."""

        content_width = self.content_width
        viewport_height = (
            self.scrollable_content_region.height if self.is_mounted else 0
        )
        revision = self.listener.history.revision
        width_changed = content_width != self._content_width
        height_changed = viewport_height != self._viewport_height
        pending_request = self.listener.pending_request
        pending_substring_listing = self.listener.pending_substring_listing
        state_changed = (
            pending_request is not self._pending_request
            or pending_substring_listing is not self._pending_substring_listing
        )
        if (
            not force
            and revision == self._history_revision
            and not width_changed
            and not height_changed
            and not state_changed
        ):
            return False

        anchor = self._viewport_anchor()
        self.current_layout = layout(self.listener.history, content_width)
        self._logical_rows = self.listener.history.rows
        self._history_revision = revision
        self._content_width = content_width
        self._viewport_height = viewport_height
        self._pending_request = pending_request
        self._pending_substring_listing = pending_substring_listing

        self.virtual_size = Size(content_width, len(self.current_layout.rows))

        target_scroll = self._clamp_scroll_row(self._anchored_scroll_y(anchor))
        self.scroll_to(y=target_scroll, animate=False, force=True, immediate=True)

        previous_hover = self.hovered_presentation
        retained = set(self.current_layout.presentations)
        if self._pointer_offset is not None:
            if self._offset_is_in_content(self._pointer_offset):
                self.hovered_presentation = self._hit_at_offset(
                    self._pointer_offset, scroll_y=target_scroll
                )
            else:
                self._pointer_offset = None
                self.hovered_presentation = None
        elif self.hovered_presentation not in retained:
            self.hovered_presentation = None
        if (
            self.hovered_presentation is not previous_hover
            and self.is_mounted
            and isinstance(self.screen, ListenerScreen)
        ):
            self.screen.history_hover_changed()
        self._styled_intervals = _styled_intervals_by_row(self.current_layout)
        self._line_texts = self._build_all_rows()
        self.history_text = _compose_history_text(self._line_texts)
        self.refresh(layout=True)
        self._refresh_documentation()
        return True

    def sync(self, *, force: bool = False) -> bool:
        """Short alias intended for tests and the active terminal checkpoint."""

        return self.synchronize(force=force)

    def set_hovered_presentation(
        self, presentation: Presentation | None
    ) -> None:
        """Set passive hover state without installing mouse handling yet."""

        if presentation is not None and presentation not in self.current_layout.presentations:
            presentation = None
        if presentation is self.hovered_presentation:
            self._refresh_documentation()
            return
        previous = self.hovered_presentation
        self.hovered_presentation = presentation
        if self.is_mounted and isinstance(self.screen, ListenerScreen):
            self.screen.history_hover_changed()
        physical_rows = {
            interval.physical_row
            for item in (previous, presentation)
            if item is not None
            for interval in item.intervals
        }
        for physical_row in sorted(physical_rows):
            if 0 <= physical_row < len(self._line_texts):
                self._line_texts[physical_row] = self._build_row(physical_row)
        self._refresh_physical_rows(physical_rows)
        self._refresh_documentation()

    def scroll_to_row(self, row: int) -> None:
        """Programmatically scroll in the history's physical-row unit."""

        target = self._clamp_scroll_row(int(row))
        self.scroll_to(y=target, animate=False, force=True, immediate=True)
        self._recompute_pointer_hover(scroll_y=target)
        self._refresh_documentation()

    def _refresh_documentation(self) -> None:
        if self.is_mounted and isinstance(self.screen, ListenerScreen):
            self.screen.documentation_line.set_presentation(
                self.hovered_presentation, self.pointer_logical_column
            )

    def on_mount(self) -> None:
        self.synchronize(force=True)

    def on_resize(self, _event: events.Resize) -> None:
        self.synchronize()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if isinstance(self.screen, ListenerScreen):
            self.screen.remember_pointer(event)
        self.synchronize()
        self._pointer_offset = self.content_offset_from_event(event)
        self.set_hovered_presentation(
            None
            if self._pointer_offset is None
            else self._hit_at_offset(self._pointer_offset)
        )
        event.stop()

    def on_leave(self, event: events.Leave) -> None:
        if event.node is self:
            self.clear_pointer()

    def on_click(self, event: events.Click) -> None:
        event.prevent_default().stop()
        if event.chain != 1:
            return
        if (
            event.button == 3
            and (
                self.listener.pending_request is not None
                or self.listener.pending_substring_listing is not None
            )
        ):
            return

        if isinstance(self.screen, ListenerScreen):
            self.screen.remember_pointer(event)
        self.synchronize()
        self._pointer_offset = self.content_offset_from_event(event)
        presentation = (
            None
            if self._pointer_offset is None
            else self._hit_at_offset(self._pointer_offset)
        )
        self.set_hovered_presentation(presentation)
        if isinstance(self.screen, ListenerScreen):
            if self.screen.action_menu.is_open:
                self.screen.close_menu()
                return
            if event.button == 3:
                self.screen.open_menu(presentation)
                return
        if event.button != 1:
            return
        label = ""
        kind = _domain_kind(self.listener, presentation)
        if presentation is not None and kind in {"File", "Directory"}:
            label = _name(presentation)
        elif presentation is not None and kind == "Process":
            label = _pid(presentation)

        revision = self.listener.history.revision
        selected = self.listener.select(presentation, label)
        if isinstance(self.screen, ListenerScreen):
            self.screen.synchronize(
                reveal_newest=(
                    selected and self.listener.history.revision != revision
                )
            )

    def _scroll_wheel(self, event: events.MouseEvent, delta: int) -> None:
        event.prevent_default().stop()
        if isinstance(self.screen, ListenerScreen):
            self.screen.remember_pointer(event)
        self.synchronize()
        self._pointer_offset = self.content_offset_from_event(event)
        self.scroll_to_row(int(self.scroll_y) + delta)
        if self._pointer_offset is None:
            self.set_hovered_presentation(None)

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        self._scroll_wheel(event, -3)

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        self._scroll_wheel(event, 3)

    def render(self) -> Text:
        return self.history_text

    def render_line(self, y: int) -> Strip:
        width = max(0, self.scrollable_content_region.width)
        physical_row = y + self.scroll_offset.y
        if width == 0 or physical_row < 0 or physical_row >= len(self._line_texts):
            return Strip.blank(width, self.visual_style.rich_style)

        line = self._line_texts[physical_row]
        options = self.app.console.options.update(
            width=max(1, self.current_layout.width),
            height=1,
            no_wrap=True,
            overflow="crop",
        )
        rendered = self.app.console.render_lines(
            line,
            options,
            style=self.visual_style.rich_style,
            pad=False,
            new_lines=False,
        )
        strip = Strip(rendered[0] if rendered else [])
        return strip.crop(self.scroll_offset.x, self.scroll_offset.x + width).adjust_cell_length(
            width, self.visual_style.rich_style
        )


class ActionMenu(ScrollView):
    """One transient, scrollable panel of private action presentations."""

    can_focus = False

    DEFAULT_CSS = """
    ActionMenu {
        display: none;
        width: 100%;
        height: 0;
        overflow-x: hidden;
        overflow-y: auto;
        scrollbar-gutter: stable;
    }
    """

    def __init__(self, listener: HeadlessListener, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.listener = listener
        self._registry = PresentationTypeRegistry()
        self.menu_type = self._registry.register("MenuAction")
        self.item_presentations: tuple[Presentation, ...] = ()
        self.hovered_presentation: Presentation | None = None
        self.target: Presentation | None = None
        self.entered = False
        self._pointer_offset: Offset | None = None

    @property
    def is_open(self) -> bool:
        return self.target is not None

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(item.value.label for item in self.item_presentations)

    def open_for(self, target: Presentation, labels: tuple[str, ...]) -> None:
        self.target = target
        self.entered = False
        self.hovered_presentation = None
        self._pointer_offset = None
        self.item_presentations = tuple(
            Presentation(
                -(index + 1),
                self.menu_type,
                MenuAction(
                    label,
                    label.split(" ", 1)[0],
                    label.split(" ", 1)[1] if " " in label else None,
                    target,
                ),
            )
            for index, label in enumerate(labels)
        )
        self.styles.display = "block"
        self.styles.height = min(len(labels), max(1, self.screen.size.height - 3))
        self.virtual_size = Size(max(1, self.size.width), len(labels))
        self._update_intervals()
        self.scroll_to(y=0, animate=False, force=True, immediate=True)
        self.refresh(layout=True)

    def close(self) -> None:
        self.target = None
        self.entered = False
        self.hovered_presentation = None
        self._pointer_offset = None
        for item in self.item_presentations:
            item.replace_intervals(())
        self.item_presentations = ()
        self.virtual_size = Size(0, 0)
        self.styles.display = "none"
        self.styles.height = 0
        self.refresh(layout=True)

    def _update_intervals(self) -> None:
        width = max(1, self.scrollable_content_region.width)
        self.virtual_size = Size(width, len(self.item_presentations))
        for index, item in enumerate(self.item_presentations):
            item.replace_intervals((DisplayInterval(index, 0, width),))

    def on_resize(self, _event: events.Resize) -> None:
        if self.is_open:
            self._update_intervals()
            self.refresh()

    def presentation_at_content_offset(self, x: int, y: int) -> Presentation | None:
        if not self.is_open:
            return None
        region = self.scrollable_content_region
        if not (0 <= x < region.width and 0 <= y < region.height):
            return None
        index = y + int(self.scroll_y)
        if 0 <= index < len(self.item_presentations):
            item = self.item_presentations[index]
            if item.intervals[0].contains(x, index):
                return item
        return None

    def _hit_event(self, event: events.MouseEvent) -> Presentation | None:
        offset = event.get_content_offset(self)
        return (
            None if offset is None
            else self.presentation_at_content_offset(offset.x, offset.y)
        )

    def set_hovered_presentation(self, presentation: Presentation | None) -> None:
        if presentation is self.hovered_presentation:
            return
        previous = self.hovered_presentation
        self.hovered_presentation = presentation
        for item in (previous, presentation):
            if item is None:
                continue
            y = item.intervals[0].physical_row - int(self.scroll_y)
            if 0 <= y < self.scrollable_content_region.height:
                self.refresh(Region(0, y, self.scrollable_content_region.width, 1))
        if isinstance(self.screen, ListenerScreen):
            self.screen.refresh_menu_documentation()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        self.entered = True
        if isinstance(self.screen, ListenerScreen):
            self.screen.remember_pointer(event)
        self._pointer_offset = event.get_content_offset(self)
        self.set_hovered_presentation(self._hit_event(event))
        event.stop()

    def _scroll_wheel(self, event: events.MouseEvent, delta: int) -> None:
        event.prevent_default().stop()
        if isinstance(self.screen, ListenerScreen):
            self.screen.remember_pointer(event)
        self._pointer_offset = event.get_content_offset(self)
        self.scroll_to(
            y=int(self.scroll_y) + delta,
            animate=False, force=True, immediate=True,
        )
        offset = self._pointer_offset
        self.set_hovered_presentation(
            None if offset is None
            else self.presentation_at_content_offset(offset.x, offset.y)
        )

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        self._scroll_wheel(event, -3)

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        self._scroll_wheel(event, 3)

    def on_enter(self, _event: events.Enter) -> None:
        self.entered = True

    def on_leave(self, event: events.Leave) -> None:
        self._pointer_offset = None
        if (
            event.node is self
            and self.entered
            and isinstance(self.screen, ListenerScreen)
        ):
            self.screen.close_menu()

    def on_click(self, event: events.Click) -> None:
        event.prevent_default().stop()
        if not self.is_open or event.chain != 1:
            return
        if isinstance(self.screen, ListenerScreen):
            self.screen.remember_pointer(event)
        item = self._hit_event(event) if event.button == 1 else None
        if isinstance(self.screen, ListenerScreen):
            if item is None:
                self.screen.close_menu()
            else:
                self.screen.execute_menu_item(item)

    def render_line(self, y: int) -> Strip:
        width = max(0, self.scrollable_content_region.width)
        index = y + int(self.scroll_y)
        if width == 0 or not (0 <= index < len(self.item_presentations)):
            return Strip.blank(width, self.visual_style.rich_style)
        item = self.item_presentations[index]
        label = truncate_display(item.value.label, width)
        line = Text(
            label + " " * max(0, width - display_width(label)),
            style=Style(reverse=item is self.hovered_presentation),
            no_wrap=True,
            overflow="crop",
        )
        options = self.app.console.options.update(
            width=width, height=1, no_wrap=True, overflow="crop"
        )
        rendered = self.app.console.render_lines(
            line, options, style=self.visual_style.rich_style,
            pad=False, new_lines=False,
        )
        return Strip(rendered[0] if rendered else []).adjust_cell_length(
            width, self.visual_style.rich_style
        )


class DocumentationLine(Widget):
    """Always-mounted, literal, one-row interaction documentation."""

    DEFAULT_CSS = """
    DocumentationLine {
        width: 100%;
        height: 1;
        overflow: hidden hidden;
    }
    """

    def __init__(self, listener: HeadlessListener, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.listener = listener
        self.presentation: Presentation | None = None
        self.logical_column: int | None = None
        self.override_sentence: str | None = None

    @property
    def sentence(self) -> str:
        if self.override_sentence is not None:
            return self.override_sentence
        return format_documentation(
            self.listener, self.presentation, self.logical_column
        )

    def set_presentation(
        self,
        presentation: Presentation | None,
        logical_column: int | None = None,
    ) -> None:
        self.presentation = presentation
        self.logical_column = logical_column
        self.refresh()

    def set_override(self, sentence: str | None) -> None:
        self.override_sentence = sentence
        self.refresh()

    def render(self) -> Text:
        width = self.content_size.width if self.is_mounted else display_width(self.sentence)
        return Text(
            truncate_display(self.sentence, width),
            no_wrap=True,
            overflow="crop",
        )


class CommandInput(Widget):
    """One-row editor drawing prompt, editable text, cursor, and atomic chip."""

    can_focus = True

    DEFAULT_CSS = """
    CommandInput {
        width: 100%;
        height: 1;
        overflow: hidden hidden;
    }
    """

    def __init__(self, listener: HeadlessListener, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.listener = listener
        self._cursor_position = len(listener.input_text)

    @property
    def cursor_position(self) -> int:
        return min(self._cursor_position, len(self.listener.input_text))

    @cursor_position.setter
    def cursor_position(self, position: int) -> None:
        if type(position) is not int:
            raise TypeError("cursor position must be an integer")
        self._cursor_position = min(max(0, position), len(self.listener.input_text))
        self.refresh()

    def set_cursor_position(self, position: int) -> None:
        self.cursor_position = position

    def clamp_cursor(self) -> None:
        self.cursor_position = self._cursor_position

    def _synchronize(self, *, reveal_newest: bool = False) -> None:
        if self.is_mounted and isinstance(self.screen, ListenerScreen):
            self.screen.synchronize(reveal_newest=reveal_newest)
        else:
            self.refresh()

    def _set_edited_text(self, text: str, cursor_position: int) -> None:
        self.listener.set_input_text(text)
        self.cursor_position = cursor_position
        self._synchronize()

    def _insert(self, inserted: str) -> None:
        position = self.cursor_position
        text = self.listener.input_text
        self._set_edited_text(
            text[:position] + inserted + text[position:],
            position + len(inserted),
        )

    def on_paste(self, event: events.Paste) -> None:
        event.prevent_default().stop()
        inserted = filter_one_row(event.text)
        if inserted:
            self._insert(inserted)

    def on_key(self, event: events.Key) -> None:
        key = event.key
        position = self.cursor_position
        text = self.listener.input_text

        if key == "left":
            self.cursor_position = position - 1
            self._synchronize()
        elif key == "right":
            self.cursor_position = position + 1
            self._synchronize()
        elif key == "home":
            self.cursor_position = 0
            self._synchronize()
        elif key == "end":
            self.cursor_position = len(text)
            self._synchronize()
        elif key == "backspace":
            if (
                self.listener.chip is not None
                and position == len(text)
                and self.listener.backspace_chip()
            ):
                self._synchronize()
            elif position > 0:
                self._set_edited_text(
                    text[: position - 1] + text[position:], position - 1
                )
            else:
                self._synchronize()
        elif key == "delete":
            if position < len(text):
                self._set_edited_text(text[:position] + text[position + 1 :], position)
            else:
                self._synchronize()
        elif key == "enter":
            before_rows = self.listener.history.rows
            revision = self.listener.history.revision
            self.listener.submit(self.listener.input_text)
            self.cursor_position = len(self.listener.input_text)
            self._synchronize(
                reveal_newest=(
                    self.listener.history.revision != revision
                    and _history_appended(before_rows, self.listener.history.rows)
                )
            )
        else:
            inserted = filter_one_row(event.character or "")
            if not inserted:
                return
            self._insert(inserted)

        event.prevent_default().stop()

    @property
    def prompt(self) -> str:
        return format_prompt(self.listener)

    @property
    def editor_prefix(self) -> str:
        return (
            "narrow "
            if self.listener.pending_substring_listing is not None
            else ""
        )

    @property
    def display_text(self) -> str:
        text = self.prompt + self.editor_prefix + self.listener.input_text
        chip = self.listener.chip
        if chip is not None and self.listener.pending_substring_listing is None:
            text += f" ⟨{chip.presentation_type.name}: {chip.label}⟩"
        return text

    def _cursor_index(self, text: str) -> int:
        input_start = len(self.prompt) + len(self.editor_prefix)
        position = self.cursor_position
        input_text = self.listener.input_text
        if position < len(input_text):
            candidate = input_start + position
            if _character_width(text[candidate]) > 0:
                return candidate
            for index in range(candidate - 1, input_start - 1, -1):
                if _character_width(text[index]) > 0:
                    return index
        return input_start + len(input_text)

    @property
    def renderable(self) -> Text:
        text = self.display_text
        cursor_index = self._cursor_index(text)
        if cursor_index == len(text):
            text += " "
        renderable = Text(text, no_wrap=True, overflow="crop")
        if self.has_focus:
            renderable.stylize(Style(reverse=True), cursor_index, cursor_index + 1)
        return renderable

    def render(self) -> Text:
        return self.renderable

    def render_line(self, y: int) -> Strip:
        width = max(0, self.content_size.width)
        if y != 0 or width == 0:
            return Strip.blank(width, self.visual_style.rich_style)
        renderable = self.renderable
        options = self.app.console.options.update(
            width=max(1, display_width(renderable.plain)),
            height=1,
            no_wrap=True,
            overflow="crop",
        )
        rendered = self.app.console.render_lines(
            renderable,
            options,
            style=self.visual_style.rich_style,
            pad=False,
            new_lines=False,
        )
        strip = Strip(rendered[0] if rendered else [])
        cursor_column = display_width(
            renderable.plain[: self._cursor_index(renderable.plain)]
        )
        left = max(0, cursor_column - width + 1)
        return strip.crop(left, left + width).adjust_cell_length(
            width, self.visual_style.rich_style
        )


class ListenerScreen(Screen[None]):
    """The sole screen containing history, a transient menu, and fixed rows."""

    DEFAULT_CSS = """
    ListenerScreen {
        layout: vertical;
    }
    """

    def __init__(self, listener: HeadlessListener) -> None:
        super().__init__()
        self.listener = listener
        self.history_surface = HistorySurface(listener, id="history")
        self.action_menu = ActionMenu(listener, id="action-menu")
        self.documentation_line = DocumentationLine(listener, id="documentation")
        self.command_input = CommandInput(listener, id="command-input")
        self._documentation_state = self._listener_state()
        self._pointer_screen: Offset | None = None

    def _listener_state(self) -> tuple[object, ...]:
        return (
            self.listener.history.revision,
            self.listener.pending_request,
            self.listener.pending_substring_listing,
            self.listener.input_text,
            self.listener.chip,
        )

    def compose(self) -> ComposeResult:
        yield self.history_surface
        yield self.action_menu
        yield self.documentation_line
        yield self.command_input

    def on_mount(self) -> None:
        self.command_input.focus()

    def on_resize(self, _event: events.Resize) -> None:
        if self.action_menu.is_open:
            self.action_menu.styles.height = min(
                len(self.action_menu.item_presentations),
                max(1, self.size.height - 3),
            )
            self.call_after_refresh(self.synchronize)

    def history_hover_changed(self) -> None:
        if not self.action_menu.is_open:
            self.documentation_line.set_override(None)

    def remember_pointer(self, event: events.MouseEvent) -> None:
        self._pointer_screen = event.screen_offset

    def _rehit_history_pointer(self) -> None:
        pointer = self._pointer_screen
        if pointer is None:
            return
        surface = self.history_surface
        region = surface.scrollable_content_region
        if pointer in region:
            offset = Offset(pointer.x - region.x, pointer.y - region.y)
            surface._pointer_offset = offset
            surface.set_hovered_presentation(surface._hit_at_offset(offset))
        else:
            surface.clear_pointer()

    def on_leave(self, event: events.Leave) -> None:
        if event.node is self:
            self._pointer_screen = None
            self.history_surface.clear_pointer()

    def refresh_menu_documentation(self) -> None:
        item = self.action_menu.hovered_presentation
        sentence = (
            _MENU_DOCUMENTATION
            if item is None
            else _menu_item_documentation(item.value, self.listener)
        )
        self.documentation_line.set_override(sentence)

    def open_menu(self, target: Presentation | None) -> None:
        if self.action_menu.is_open:
            return
        if (
            self.listener.pending_request is not None
            or self.listener.pending_substring_listing is not None
        ):
            self.documentation_line.set_override(None)
            self.synchronize()
            return
        kind = _domain_kind(self.listener, target)
        labels = _menu_labels(kind)
        if target is None or target not in self.listener.history.presentations:
            labels = ()
        if not labels:
            self.documentation_line.set_override(_menu_refusal(target, kind))
            return
        self.action_menu.open_for(target, labels)
        self.refresh_menu_documentation()
        self.refresh(layout=True)
        self.call_after_refresh(self.synchronize)

    def close_menu(self) -> None:
        if not self.action_menu.is_open:
            return
        self.action_menu.close()
        self.documentation_line.set_override(None)
        self.refresh(layout=True)
        self.call_after_refresh(self.synchronize)
        self.synchronize()

    def execute_menu_item(self, item: Presentation) -> None:
        if item not in self.action_menu.item_presentations:
            return
        action = item.value
        self.close_menu()
        target = action.target
        if target not in self.listener.history.presentations:
            return
        before_rows = self.listener.history.rows
        before_revision = self.listener.history.revision
        if action.operation in {"show", "cd", "rm", "kill", "ls"}:
            self.listener.execute_stored_member(target, action.operation)
        elif action.operation == "narrow":
            self.listener.begin_listing_narrow(target.value)
        else:
            self.listener.apply_listing_view(
                target.value, action.operation, action.argument
            )
        self.command_input.cursor_position = len(self.listener.input_text)
        self.synchronize(
            reveal_newest=(
                self.listener.history.revision != before_revision
                and _history_appended(before_rows, self.listener.history.rows)
            )
        )

    def on_click(self, event: events.Click) -> None:
        if self.action_menu.is_open and event.chain == 1:
            event.prevent_default().stop()
            self.remember_pointer(event)
            self.close_menu()

    def synchronize(
        self, *, reveal_newest: bool = False, clear_hover: bool = False
    ) -> None:
        state = self._listener_state()
        if state != self._documentation_state:
            self._documentation_state = state
            if not self.action_menu.is_open:
                self.documentation_line.set_override(None)
        if clear_hover:
            self._pointer_screen = None
            self.history_surface.clear_pointer()
        self.history_surface.synchronize()
        if reveal_newest:
            self.history_surface.scroll_to_row(
                len(self.history_surface.current_layout.rows)
            )
        self._rehit_history_pointer()
        if self._pointer_screen is None and self.history_surface.pointer_offset is not None:
            self.history_surface._recompute_pointer_hover()
        self.documentation_line.set_presentation(
            self.history_surface.hovered_presentation,
            self.history_surface.pointer_logical_column,
        )
        self.command_input.clamp_cursor()
        self.command_input.refresh()


class PbuiApp(App[None], inherit_bindings=False):
    """The Textual application adapting one injected listener."""

    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding(
            "ctrl+g,escape",
            "cancel_listener",
            show=False,
            priority=True,
        ),
        Binding("ctrl+d", "exit_if_empty", show=False, priority=True),
        Binding("ctrl+c", "exit_any_state", show=False, priority=True),
        Binding("ctrl+o", "open_action_menu", show=False, priority=True),
    ]

    def __init__(self, listener: HeadlessListener) -> None:
        if not isinstance(listener, HeadlessListener):
            raise TypeError("PbuiApp requires a HeadlessListener")
        super().__init__()
        self.listener = listener

    def get_default_screen(self) -> ListenerScreen:
        return ListenerScreen(self.listener)

    def action_cancel_listener(self) -> None:
        screen = self.screen
        if isinstance(screen, ListenerScreen) and screen.action_menu.is_open:
            screen.close_menu()
            return
        self.listener.cancel()
        if isinstance(screen, ListenerScreen):
            screen.command_input.cursor_position = 0
            screen.synchronize(clear_hover=True)

    def action_open_action_menu(self) -> None:
        screen = self.screen
        if not isinstance(screen, ListenerScreen) or screen.action_menu.is_open:
            return
        surface = screen.history_surface
        surface.synchronize()
        offset = surface.pointer_offset
        target = (
            surface._hit_at_offset(offset)
            if offset is not None
            else surface.hovered_presentation
        )
        screen.open_menu(target)

    def action_exit_if_empty(self) -> None:
        if (
            self.listener.input_text == ""
            and self.listener.chip is None
            and self.listener.pending_request is None
            and self.listener.pending_substring_listing is None
        ):
            self.exit()

    def action_exit_any_state(self) -> None:
        self.exit()


def main() -> None:
    """Compose and run the production listener through Textual's lifecycle."""

    try:
        listener = HeadlessListener.production()
        PbuiApp(listener).run()
    except KeyboardInterrupt:
        return


__all__ = [
    "CommandInput",
    "DocumentationLine",
    "HistorySurface",
    "ListenerScreen",
    "PbuiApp",
    "build_history_row_text",
    "build_history_text",
    "display_width",
    "filter_one_row",
    "format_documentation",
    "format_prompt",
    "main",
    "presentation_style",
    "truncate_display",
]
