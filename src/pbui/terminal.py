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

from pbui.bottom import (
    MENU_BORDER_DOCUMENTATION, _captured_process_member, _domain_kind,
    _name, _pid, fit_documentation, format_documentation,
    format_menu_item_documentation, format_mode, format_popup_failure,
)
from pbui.commands import HeadlessListener
from pbui.menu_geometry import CellRect, MenuGeometry, opening_anchor, place_menu
from pbui.domain import DirectoryListing, ProcessListing, escape_display
from pbui.substrate import (
    DisplayInterval,
    Presentation,
    PresentationTypeRegistry,
)
from pbui.text import (
    HistoryRow,
    Layout,
    _character_width,
    _display_clusters,
    display_width,
    layout,
    row_indents,
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
    translator_index: int | None = None


def _menu_action(
    label: str, target: Presentation, index: int,
    translator_indices: tuple[int, ...] | None,
) -> MenuAction:
    if translator_indices is not None:
        return MenuAction(label, "python-translator", None, target, translator_indices[index])
    operation, separator, argument = label.partition(" ")
    return MenuAction(label, operation, argument if separator else None, target)


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


def _menu_labels(kind: str | None) -> tuple[str, ...]:
    return {
        "File": ("show", "rm"),
        "Directory": ("show", "cd", "ls"),
        "Process": ("show", "kill"),
        "DirectoryListing": _DIRECTORY_ACTIONS,
        "ProcessListing": _PROCESS_ACTIONS,
        "PythonInput": ("yank",),
        "CommandInput": ("yank",),
        "MenuActionInput": ("run again",),
    }.get(kind, ())


def format_prompt(listener: HeadlessListener) -> str:
    """Return the literal prompt derived from the listener's own cwd."""

    cwd = escape_display(listener.cwd)
    if listener.pending_substring_listing is None and listener.pending_python_pieces:
        return f"pbui:{cwd} ...> "
    return f"pbui:{cwd}> "


def presentation_style(
    listener: HeadlessListener,
    presentation: Presentation,
    hovered_presentation: Presentation | None,
) -> Style:
    """Map one retained presentation to its complete interaction style."""

    kind = _domain_kind(listener, presentation)
    if kind == "TutorialTarget":
        enabled = presentation.value.destination is not None
        return Style(
            color="#00afff" if enabled else "#808080",
            bold=enabled, underline=enabled, dim=not enabled,
            reverse=enabled and presentation is hovered_presentation,
        )
    if kind == "TutorialTry":
        return Style(
            color="#00afff", bold=True, underline=True,
            reverse=presentation is hovered_presentation,
        )
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
        self._relayout_scroll = False

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
        if logical_index is None:
            physical_row += 1
            if physical_row >= len(self.current_layout.rows):
                return None
            logical_index = self.current_layout.rows[physical_row].logical_row
            assert logical_index is not None
            wrapped_offset = 0
        else:
            first = physical_row
            while first > 0 and self.current_layout.rows[first - 1].logical_row == logical_index:
                first -= 1
            wrapped_offset = physical_row - first
        if logical_index >= len(self._logical_rows):
            return None
        row = self._logical_rows[logical_index]
        owner = row.listing_owner
        listing = owner if type(owner) in {DirectoryListing, ProcessListing} else None
        return _ViewportAnchor(
            row,
            listing,
            row.presentations[0] if listing is not None and row.presentations else None,
            wrapped_offset,
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
        logical_row = rendered_row.logical_row
        if logical_row is None or logical_row >= len(self._logical_rows):
            return None
        indent = (
            2 if self.current_layout.width >= 3
            and row_indents(self._logical_rows[logical_row]) else 0
        )
        if offset.x < indent or offset.x >= rendered_row.display_width:
            return None
        return offset.x - indent + sum(
            row.display_width - indent
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
        self._relayout_scroll = True
        try:
            self.scroll_to(y=target_scroll, animate=False, force=True, immediate=True)
        finally:
            self._relayout_scroll = False

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

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        super().watch_scroll_y(old_value, new_value)
        if (
            old_value != new_value
            and not self._relayout_scroll
            and self.is_mounted
            and isinstance(self.screen, ListenerScreen)
        ):
            self.screen.close_menu()

    def scroll_to_row(self, row: int) -> None:
        """Programmatically scroll in the history's physical-row unit."""

        if self.is_mounted and isinstance(self.screen, ListenerScreen):
            self.screen.close_menu()
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
            if self.screen.action_menu.is_open:
                if self.screen.route_menu_move(event):
                    event.stop()
                    return
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
        if isinstance(self.screen, ListenerScreen) and self.screen.action_menu.is_open:
            self.screen.route_menu_click(event)
            return
        if event.chain != 1:
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
                self.screen.open_menu(
                    presentation,
                    anchor=(event.screen_offset.x, event.screen_offset.y),
                )
                return
        if event.button != 1:
            return
        self.select_presentation(presentation)

    def select_presentation(self, presentation: Presentation | None) -> None:
        """Route one history hit and synchronize its editor or appended rows."""

        label = ""
        kind = _domain_kind(self.listener, presentation)
        if presentation is not None and kind in {"File", "Directory"}:
            label = _name(presentation)
        elif presentation is not None and kind == "Process":
            label = _pid(presentation)

        revision = self.listener.history.revision
        selected = self.listener.select_for_input(presentation, label)
        if isinstance(self.screen, ListenerScreen):
            if selected and kind in {"PythonInput", "CommandInput", "TutorialTry"}:
                self.screen.command_input.adopt_listener_cursor()
            self.screen.synchronize(
                reveal_newest=(
                    selected and self.listener.history.revision != revision
                )
            )

    def _scroll_wheel(self, event: events.MouseEvent, delta: int) -> None:
        event.prevent_default().stop()
        if isinstance(self.screen, ListenerScreen):
            self.screen.close_menu()
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

    def refresh_menu_rows(self, screen_rows: set[int]) -> None:
        geometry = self.screen.action_menu.geometry
        if geometry is None:
            return
        region = self.scrollable_content_region
        local_x = geometry.rect.x - region.x
        for screen_y in screen_rows:
            local_y = screen_y - region.y
            if 0 <= local_y < region.height:
                self.refresh(Region(local_x, local_y, geometry.rect.width, 1))

    def render(self) -> Text:
        return self.history_text

    def render_line(self, y: int) -> Strip:
        width = max(0, self.scrollable_content_region.width)
        physical_row = y + self.scroll_offset.y
        if width == 0 or physical_row < 0 or physical_row >= len(self._line_texts):
            strip = Strip.blank(width, self.visual_style.rich_style)
        else:
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
            strip = strip.crop(
                self.scroll_offset.x, self.scroll_offset.x + width
            ).adjust_cell_length(width, self.visual_style.rich_style)

        if not self.is_mounted or not isinstance(self.screen, ListenerScreen):
            return strip
        menu = self.screen.action_menu
        geometry = menu.geometry
        if geometry is None:
            return strip
        region = self.scrollable_content_region
        screen_y = region.y + y
        rect = geometry.rect
        if not (rect.y <= screen_y < rect.y + rect.height):
            return strip
        local_x = rect.x - region.x
        if not (0 <= local_x and local_x + rect.width <= width):
            return strip
        row = Text(geometry.row_text(screen_y), no_wrap=True, overflow="crop")
        hovered = menu.hovered_presentation
        if hovered is not None:
            index = menu.item_presentations.index(hovered)
            if screen_y == rect.y + index + 1:
                row.stylize(Style(reverse=True), 1, rect.width - 1)
        options = self.app.console.options.update(
            width=rect.width, height=1, no_wrap=True, overflow="crop"
        )
        rendered = self.app.console.render_lines(
            row, options, style=self.visual_style.rich_style,
            pad=False, new_lines=False,
        )
        overlay = Strip(rendered[0] if rendered else []).adjust_cell_length(
            rect.width, self.visual_style.rich_style
        )
        return Strip.join((
            strip.crop(0, local_x),
            overlay,
            strip.crop(local_x + rect.width, width),
        ))


class ActionMenu(Widget):
    """Transient menu state painted over the history's visible cells."""

    can_focus = False

    DEFAULT_CSS = """
    ActionMenu {
        display: none;
        height: 0;
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
        self.geometry: MenuGeometry | None = None

    @property
    def is_open(self) -> bool:
        return self.target is not None

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(item.value.label for item in self.item_presentations)

    def open_for(
        self,
        target: Presentation,
        labels: tuple[str, ...],
        geometry: MenuGeometry,
        *,
        translator_indices: tuple[int, ...] | None = None,
    ) -> None:
        self.target = target
        self.geometry = geometry
        self.hovered_presentation = None
        self.item_presentations = tuple(
            Presentation(
                -(index + 1),
                self.menu_type,
                _menu_action(label, target, index, translator_indices),
            )
            for index, label in enumerate(labels)
        )
        self._update_intervals()

    def _update_intervals(self) -> None:
        assert self.geometry is not None
        width = self.geometry.rect.width
        for index, item in enumerate(self.item_presentations):
            item.replace_intervals((DisplayInterval(index + 1, 1, width - 1),))

    def close(self) -> None:
        self.target = None
        self.geometry = None
        self.hovered_presentation = None
        for item in self.item_presentations:
            item.replace_intervals(())
        self.item_presentations = ()

    def presentation_at_screen_cell(self, x: int, y: int) -> Presentation | None:
        geometry = self.geometry
        index = None if geometry is None else geometry.item_at(x, y)
        return None if index is None else self.item_presentations[index]

    def presentation_at_content_offset(self, x: int, y: int) -> Presentation | None:
        """Return a menu item for rectangle-local cells; border is inert."""

        geometry = self.geometry
        if geometry is None:
            return None
        return self.presentation_at_screen_cell(geometry.rect.x + x, geometry.rect.y + y)

    def set_hovered_presentation(self, item: Presentation | None) -> None:
        if item is self.hovered_presentation:
            return
        previous = self.hovered_presentation
        self.hovered_presentation = item
        if isinstance(self.screen, ListenerScreen):
            geometry = self.geometry
            if geometry is not None:
                rows = {
                    geometry.rect.y + self.item_presentations.index(presentation) + 1
                    for presentation in (previous, item)
                    if presentation is not None
                }
                self.screen.history_surface.refresh_menu_rows(rows)
            self.screen.refresh_menu_documentation()

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
        menu_open = (
            self.is_mounted and isinstance(self.screen, ListenerScreen)
            and self.screen.action_menu.is_open
        )
        return format_documentation(
            self.listener, self.presentation, self.logical_column,
            menu_open=menu_open,
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
            fit_documentation(self.sentence, width),
            no_wrap=True,
            overflow="crop",
        )


class CommandInput(Widget):
    """One-row editor with a fixed mode and a separate top rule."""

    can_focus = True

    DEFAULT_CSS = """
    CommandInput {
        width: 100%;
        height: 2;
        border-top: solid $foreground;
        overflow: hidden hidden;
    }
    """

    def __init__(self, listener: HeadlessListener, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.listener = listener

    @property
    def _python_editing(self) -> bool:
        return self.listener.chip is None and self.listener.input_mode in {"python", "empty"}

    @property
    def cursor_position(self) -> int:
        if self._python_editing:
            return self.listener.python_cursor
        return self.listener.command_cursor

    @cursor_position.setter
    def cursor_position(self, position: int) -> None:
        if type(position) is not int:
            raise TypeError("cursor position must be an integer")
        if self._python_editing:
            atom_count = sum(
                len(piece) if isinstance(piece, str) else 1
                for piece in self.listener.python_pieces
            )
            self.listener.set_python_cursor(min(max(0, position), atom_count))
        else:
            self.listener.set_command_cursor(
                min(max(0, position), len(self.listener.input_text))
            )
        self.refresh()
        if self.is_mounted and isinstance(self.screen, ListenerScreen):
            self.screen.synchronize()

    def set_cursor_position(self, position: int) -> None:
        self.cursor_position = position

    def adopt_listener_cursor(self) -> None:
        """Draw the caret supplied by the listener after a saved-input load."""

        self.refresh()

    def clamp_cursor(self) -> None:
        """Refresh after the listener has changed the editor or its mode."""

        self.refresh()

    def _adopt_python_edit_cursor(self) -> None:
        """Carry a Python edit caret across a change into command mode."""

        if not self._python_editing:
            self.listener.set_command_cursor(self.listener.python_cursor)

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
        if self._python_editing:
            self.listener.insert_python_text(inserted)
            self._adopt_python_edit_cursor()
            self._synchronize()
            return
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
        if key in {"up", "down"}:
            traverse = (
                self.listener.recall_previous if key == "up"
                else self.listener.recall_next
            )
            if traverse(menu_open=self.screen.action_menu.is_open):
                self._synchronize()
            event.prevent_default().stop()
            return
        python = self._python_editing
        position = self.cursor_position
        value = self.listener.input_text

        if key in {"left", "right", "home", "end"}:
            if python:
                {
                    "left": self.listener.python_left,
                    "right": self.listener.python_right,
                    "home": self.listener.python_home,
                    "end": self.listener.python_end,
                }[key]()
            else:
                self.cursor_position = (
                    position - 1 if key == "left" else
                    position + 1 if key == "right" else
                    0 if key == "home" else len(value)
                )
            self._synchronize()
        elif key == "backspace":
            if python:
                self.listener.python_backspace()
                self._adopt_python_edit_cursor()
                self._synchronize()
            elif (
                self.listener.chip is not None
                and position == len(value)
                and self.listener.backspace_chip()
            ):
                self._synchronize()
            elif position > 0:
                self._set_edited_text(
                    value[:position - 1] + value[position:], position - 1
                )
            else:
                self._synchronize()
        elif key == "delete":
            if python:
                self.listener.python_delete()
                self._adopt_python_edit_cursor()
                self._synchronize()
            elif position < len(value):
                self._set_edited_text(value[:position] + value[position + 1:], position)
            else:
                self._synchronize()
        elif key == "enter":
            before_rows = self.listener.history.rows
            revision = self.listener.history.revision
            if python:
                self.listener.submit()
            else:
                self.listener.submit(self.listener.input_text)
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
    def mode(self) -> str:
        return format_mode(self.listener)

    @property
    def editor_prefix(self) -> str:
        return (
            "narrow "
            if self.listener.pending_substring_listing is not None
            else ""
        )

    def _python_body_and_cursor(self) -> tuple[str, int]:
        body: list[str] = []
        offset = 0
        atom_position = 0
        cursor_offset = 0
        for piece in self.listener.python_pieces:
            atoms = piece if isinstance(piece, str) else (piece,)
            for atom in atoms:
                if atom_position == self.listener.python_cursor:
                    cursor_offset = offset
                drawing = atom if isinstance(atom, str) else f"⟨{atom.label}⟩"
                body.append(drawing)
                offset += len(drawing)
                atom_position += 1
        if atom_position == self.listener.python_cursor:
            cursor_offset = offset
        return "".join(body), cursor_offset

    def _editor_body_and_cursor(self) -> tuple[str, int]:
        if self._python_editing:
            return self._python_body_and_cursor()
        text = self.editor_prefix + self.listener.input_text
        chip = self.listener.chip
        if chip is not None and self.listener.pending_substring_listing is None:
            text += f" ⟨{chip.presentation_type.name}: {chip.label}⟩"
        return text, len(self.editor_prefix) + self.cursor_position

    @property
    def display_text(self) -> str:
        body, _ = self._editor_body_and_cursor()
        return self.mode + " │ " + self.prompt + body

    def _cursor_index(self, text: str) -> int:
        _, offset = self._editor_body_and_cursor()
        input_start = len(self.mode) + len(" │ ") + len(self.prompt)
        candidate = input_start + offset
        if candidate < len(text):
            if _character_width(text[candidate]) > 0:
                return candidate
            for index in range(candidate - 1, input_start - 1, -1):
                if _character_width(text[index]) > 0:
                    return index
        return candidate

    @property
    def renderable(self) -> Text:
        text = self.display_text
        cursor_index = self._cursor_index(text)
        if cursor_index == len(text):
            text += " "
        renderable = Text(text, no_wrap=True, overflow="crop")
        renderable.stylize(Style(bold=True), 0, len(self.mode))
        if self.has_focus:
            renderable.stylize(Style(reverse=True), cursor_index, cursor_index + 1)
        return renderable

    def render(self) -> Text:
        return self.renderable

    def _short_prompt(self, width: int) -> str:
        """Spend cells on the prompt while saving one for the editor."""

        prompt = self.prompt
        if display_width(prompt) + 1 <= width:
            return prompt
        suffix = (
            " ...> "
            if self.listener.pending_substring_listing is None
            and self.listener.pending_python_pieces
            else "> "
        )
        fixed = "pbui:"
        cwd = escape_display(self.listener.cwd)
        fixed_width = display_width(fixed + suffix)
        editor_reserve = min(8, max(1, width - fixed_width - 1))
        budget = width - fixed_width - editor_reserve
        if budget < 1:
            return truncate_display(fixed + "…" + suffix, width)
        kept: list[str] = []
        used = 1
        for cluster, cells in reversed(_display_clusters(cwd)):
            if used + cells > budget:
                break
            kept.append(cluster)
            used += cells
        return fixed + "…" + "".join(reversed(kept)) + suffix

    def _draw_text(self, renderable: Text) -> Strip:
        options = self.app.console.options.update(
            width=max(1, display_width(renderable.plain)),
            height=1,
            no_wrap=True,
            overflow="crop",
        )
        rendered = self.app.console.render_lines(
            renderable, options, style=self.visual_style.rich_style,
            pad=False, new_lines=False,
        )
        return Strip(rendered[0] if rendered else [])

    def render_line(self, y: int) -> Strip:
        width = max(0, self.content_size.width)
        if y != 0 or width == 0:
            return Strip.blank(width, self.visual_style.rich_style)
        mode = self.mode
        prefix = Text(mode, no_wrap=True, overflow="crop")
        prefix.stylize(Style(bold=True), 0, len(mode))
        if width > display_width(mode):
            separator = " │ "
            remaining = width - display_width(mode + separator)
            prefix.append(separator)
            if remaining > 0:
                prefix.append(self._short_prompt(remaining))
        prefix_width = min(width, display_width(prefix.plain))
        prefix_strip = self._draw_text(prefix).crop(0, prefix_width)
        editor_width = width - prefix_width
        if editor_width == 0:
            return prefix_strip.adjust_cell_length(width, self.visual_style.rich_style)

        body, cursor_index = self._editor_body_and_cursor()
        editor = Text(body + " ", no_wrap=True, overflow="crop")
        if self.has_focus:
            editor.stylize(Style(reverse=True), cursor_index, cursor_index + 1)
        cursor_column = display_width(body[:cursor_index])
        left = max(0, cursor_column - editor_width + 1)
        editor_strip = self._draw_text(editor).crop(left, left + editor_width)
        return Strip.join((prefix_strip, editor_strip)).adjust_cell_length(
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
            self.listener.pending_python_pieces,
            self.listener.python_pieces,
            self.listener.python_cursor,
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
        self.call_after_refresh(self.reposition_menu)
        self.call_after_refresh(self.synchronize)

    def history_hover_changed(self) -> None:
        if not self.action_menu.is_open:
            self.documentation_line.set_override(None)

    def remember_pointer(self, event: events.MouseEvent) -> None:
        pointer = event.screen_offset
        if pointer != self._pointer_screen and not self.action_menu.is_open:
            self.documentation_line.set_override(None)
        self._pointer_screen = pointer

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

    def _exposed_tutorial_control(self, pointer: Offset) -> Presentation | None:
        surface = self.history_surface
        region = surface.scrollable_content_region
        if pointer not in region:
            return None
        target = surface._hit_at_offset(
            Offset(pointer.x - region.x, pointer.y - region.y)
        )
        return target if _domain_kind(self.listener, target) in {
            "TutorialTarget", "TutorialTry",
        } else None

    def on_leave(self, event: events.Leave) -> None:
        if event.node is self:
            self.close_menu()
            self._pointer_screen = None
            self.history_surface.clear_pointer()

    def _history_bounds(self) -> CellRect:
        region = self.history_surface.scrollable_content_region
        return CellRect(region.x, region.y, region.width, region.height)

    def _visible_cells(self, target: Presentation) -> tuple[tuple[int, int], ...]:
        region = self.history_surface.scrollable_content_region
        scroll_y = int(self.history_surface.scroll_y)
        cells = []
        for interval in target.intervals:
            visible_y = interval.physical_row - scroll_y
            start = max(0, interval.start_column)
            if 0 <= visible_y < region.height and start < min(interval.end_column, region.width):
                cells.append((region.x + start, region.y + visible_y))
        return tuple(cells)

    def refresh_menu_documentation(self) -> None:
        item = self.action_menu.hovered_presentation
        sentence = (
            MENU_BORDER_DOCUMENTATION
            if item is None
            else format_menu_item_documentation(
                self.listener, item.value.label, item.value.target
            )
        )
        self.documentation_line.set_override(sentence)

    def _refresh_menu_rectangle(self, geometry: MenuGeometry | None) -> None:
        if geometry is None:
            return
        region = self.history_surface.scrollable_content_region
        rect = geometry.rect
        self.history_surface.refresh(
            Region(rect.x - region.x, rect.y - region.y, rect.width, rect.height)
        )

    def open_menu(
        self, target: Presentation | None, *, anchor: tuple[int, int] | None = None
    ) -> None:
        if self.action_menu.is_open:
            return
        if (
            self.listener.pending_request is not None
            or self.listener.pending_substring_listing is not None
        ):
            self.documentation_line.set_override(None)
            self.synchronize()
            return
        surface = self.history_surface
        surface.synchronize()
        kind = _domain_kind(self.listener, target)
        labels = _menu_labels(kind)
        translator_indices = None
        if kind == "Value" and target is not None:
            translators = self.listener.python_translators_for(target)
            labels = tuple(item.label for item in translators)
            translator_indices = tuple(range(len(translators)))
        if target is None or target not in self.listener.history.presentations or not labels:
            self.documentation_line.set_override(None)
            self.synchronize()
            return

        if anchor is None:
            pointer = self._pointer_screen
            region = surface.scrollable_content_region
            pointer_cell = (
                (pointer.x, pointer.y) if pointer is not None and pointer in region
                else None
            )
            pointer_hits = (
                pointer_cell is not None
                and surface._hit_at_offset(
                    Offset(pointer.x - region.x, pointer.y - region.y)
                ) is target
            )
            anchor = opening_anchor(pointer_cell, pointer_hits, self._visible_cells(target))
        if anchor is None:
            self.documentation_line.set_override(
                format_popup_failure(target, self.listener, too_large=False)
            )
            return
        geometry = place_menu(labels, self._history_bounds(), anchor)
        if geometry is None:
            self.documentation_line.set_override(
                format_popup_failure(target, self.listener, too_large=True)
            )
            return
        self.action_menu.open_for(
            target, labels, geometry, translator_indices=translator_indices
        )
        self._refresh_menu_rectangle(geometry)
        pointer = self._pointer_screen
        item = (
            None if pointer is None else
            self.action_menu.presentation_at_screen_cell(pointer.x, pointer.y)
        )
        self.action_menu.set_hovered_presentation(item)
        self.refresh_menu_documentation()

    def reposition_menu(self) -> None:
        menu = self.action_menu
        old = menu.geometry
        if old is None:
            return
        geometry = place_menu(menu.labels, self._history_bounds(), old.anchor)
        if geometry is None:
            self.close_menu()
            return
        menu.geometry = geometry
        menu._update_intervals()
        self._refresh_menu_rectangle(old)
        self._refresh_menu_rectangle(geometry)
        pointer = self._pointer_screen
        menu.set_hovered_presentation(
            None if pointer is None else
            menu.presentation_at_screen_cell(pointer.x, pointer.y)
        )
        self.refresh_menu_documentation()

    def close_menu(self) -> None:
        geometry = self.action_menu.geometry
        if geometry is None:
            return
        self.action_menu.close()
        self._refresh_menu_rectangle(geometry)
        self.documentation_line.set_override(None)
        self._rehit_history_pointer()
        self.documentation_line.set_presentation(
            self.history_surface.hovered_presentation,
            self.history_surface.pointer_logical_column,
        )

    def route_menu_move(self, event: events.MouseMove) -> bool:
        """Return true while the menu still owns this pointer movement."""

        geometry = self.action_menu.geometry
        if geometry is None:
            return False
        self.remember_pointer(event)
        pointer = event.screen_offset
        if not geometry.rect.contains(pointer.x, pointer.y):
            target = self._exposed_tutorial_control(pointer)
            if target is not None:
                surface = self.history_surface
                region = surface.scrollable_content_region
                surface._pointer_offset = Offset(
                    pointer.x - region.x, pointer.y - region.y
                )
                surface.set_hovered_presentation(target)
                self.documentation_line.set_override(None)
                surface._refresh_documentation()
                return True
            self.close_menu()
            return False
        self.action_menu.set_hovered_presentation(
            self.action_menu.presentation_at_screen_cell(pointer.x, pointer.y)
        )
        self.refresh_menu_documentation()
        return True

    def route_menu_click(self, event: events.Click) -> None:
        event.prevent_default().stop()
        geometry = self.action_menu.geometry
        if geometry is None:
            return
        self.remember_pointer(event)
        pointer = event.screen_offset
        if not geometry.rect.contains(pointer.x, pointer.y):
            target = self._exposed_tutorial_control(pointer)
            self.close_menu()
            if (
                event.button == 1 and event.chain == 1
                and _domain_kind(self.listener, target) == "TutorialTarget"
            ):
                self.history_surface.select_presentation(target)
            return
        item = self.action_menu.presentation_at_screen_cell(pointer.x, pointer.y)
        self.action_menu.set_hovered_presentation(item)
        if event.button == 1 and event.chain == 1 and item is not None:
            self.execute_menu_item(item)

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if self.action_menu.is_open:
            self.route_menu_move(event)

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
        kind = _domain_kind(self.listener, target)
        if kind in {"PythonInput", "CommandInput", "MenuActionInput"}:
            selected = (
                self.listener.run_again(target)
                if kind == "MenuActionInput"
                else self.listener.yank_input(target)
            )
            if selected and kind in {"PythonInput", "CommandInput"}:
                self.command_input.adopt_listener_cursor()
            self.synchronize(
                reveal_newest=(
                    selected
                    and self.listener.history.revision != before_revision
                    and _history_appended(before_rows, self.listener.history.rows)
                )
            )
            return
        saved = (
            self.listener.capture_python_input()
            if self.listener.input_mode == "python" and action.operation != "narrow"
            else None
        )
        try:
            if action.translator_index is not None:
                self.listener.invoke_python_translator(target, action.translator_index)
            elif action.operation in {"show", "cd", "rm", "kill", "ls"}:
                self.listener.execute_stored_member(target, action.operation)
            elif action.operation == "narrow":
                self.listener.begin_listing_narrow(target.value)
            else:
                self.listener.apply_listing_view(
                    target.value, action.operation, action.argument
                )
        finally:
            if saved is not None:
                self.listener.restore_python_input(saved)
        self.command_input.clamp_cursor()
        self.synchronize(
            reveal_newest=(
                self.listener.history.revision != before_revision
                and _history_appended(before_rows, self.listener.history.rows)
            )
        )

    def on_click(self, event: events.Click) -> None:
        if self.action_menu.is_open:
            self.route_menu_click(event)

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
        if self.listener.pending_substring_listing is not None:
            self.listener.cancel()
            if isinstance(screen, ListenerScreen):
                screen.command_input.clamp_cursor()
                screen.command_input.focus()
                screen.synchronize()
            return
        if self.listener.pending_python_source:
            self.listener.cancel_python_continuation()
            if isinstance(screen, ListenerScreen):
                screen.command_input.cursor_position = 0
                screen.synchronize()
            return
        self.listener.cancel()
        if isinstance(screen, ListenerScreen):
            screen.command_input.cursor_position = 0
            screen.synchronize(clear_hover=True)

    def action_open_action_menu(self) -> None:
        screen = self.screen
        if (
            not isinstance(screen, ListenerScreen)
            or screen.action_menu.is_open
        ):
            return
        surface = screen.history_surface
        surface.synchronize()
        screen.open_menu(surface.hovered_presentation)

    def action_exit_if_empty(self) -> None:
        if isinstance(self.screen, ListenerScreen) and self.screen.action_menu.is_open:
            self.screen.close_menu()
            return
        if self.listener.pending_substring_listing is not None:
            return
        if self.listener.pending_python_source:
            self.action_cancel_listener()
            return
        if (
            self.listener.input_text == ""
            and not self.listener.python_pieces
            and self.listener.chip is None
            and self.listener.pending_request is None
            and self.listener.pending_substring_listing is None
            and not (
                isinstance(self.screen, ListenerScreen)
                and self.screen.action_menu.is_open
            )
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
