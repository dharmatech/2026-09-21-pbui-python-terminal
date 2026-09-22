"""Passive Textual drawing and layout for the presentation listener.

This is deliberately the package's only Textual boundary.  It adapts the
headless listener without moving presentation identity, wrapping, or hit
testing into widgets.
"""

from __future__ import annotations

import os

from rich.style import Style
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.geometry import Size
from textual.screen import Screen
from textual.scroll_view import ScrollView
from textual.strip import Strip
from textual.widget import Widget
from wcwidth import wcwidth

from pbui.commands import HeadlessListener
from pbui.domain import DirectoryRef, FileRef, ProcessRef, escape_display
from pbui.substrate import DisplayInterval, Presentation
from pbui.text import Layout, layout


ELLIPSIS = "…"
_UNSET = object()


def _character_width(character: str) -> int:
    """Return a harmless display width for already-sanitized product text."""

    return max(0, wcwidth(character))


def display_width(text: str) -> int:
    """Measure a string in terminal display columns."""

    return sum(_character_width(character) for character in text)


def _display_clusters(text: str) -> tuple[tuple[str, int], ...]:
    """Group zero-width marks with the preceding drawn character."""

    clusters: list[tuple[str, int]] = []
    for character in text:
        width = _character_width(character)
        if width == 0 and clusters:
            cluster, cluster_width = clusters[-1]
            clusters[-1] = (cluster + character, cluster_width)
        else:
            clusters.append((character, width))
    return tuple(clusters)


def truncate_display(text: str, width: int) -> str:
    """Truncate to display columns, preserving wide/combining characters."""

    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if width <= 0:
        return ""
    if display_width(text) <= width:
        return text
    if width == 1:
        return ELLIPSIS

    budget = width - 1
    used = 0
    retained: list[str] = []
    for cluster, cluster_width in _display_clusters(text):
        if used + cluster_width > budget:
            break
        retained.append(cluster)
        used += cluster_width
    return "".join(retained) + ELLIPSIS


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


def format_documentation(
    listener: HeadlessListener, presentation: Presentation | None
) -> str:
    """Return the exact documentation sentence for the current pointer state."""

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
            return f"Click to show process {_pid(presentation)}."
        if kind == "Text":
            return "Text has no default click action."
        if kind == "Error":
            return "Error has no default click action."
        return "No presentation under pointer."

    command = request.command_name
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

    color = (
        "red"
        if presentation.presentation_type is listener.types.error
        else "default"
    )
    return Style(
        color=color,
        bold=False,
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


def build_history_text(
    listener: HeadlessListener,
    current_layout: Layout,
    hovered_presentation: Presentation | None = None,
) -> Text:
    """Build the single literal Rich renderable for a complete pure layout."""

    row_texts = tuple(row.text for row in current_layout.rows)
    row_offsets: list[int] = []
    offset = 0
    for row_text in row_texts:
        row_offsets.append(offset)
        offset += len(row_text) + 1

    renderable = Text("\n".join(row_texts), no_wrap=True, overflow="crop")
    styled_intervals: list[
        tuple[int, int, int, Presentation, DisplayInterval]
    ] = []
    for presentation_index, presentation in enumerate(current_layout.presentations):
        for interval in presentation.intervals:
            styled_intervals.append(
                (
                    interval.nesting_depth,
                    interval.draw_order,
                    presentation_index,
                    presentation,
                    interval,
                )
            )

    for _, _, _, presentation, interval in sorted(styled_intervals):
        if interval.physical_row >= len(row_texts):
            continue
        style = presentation_style(listener, presentation, hovered_presentation)
        row_text = row_texts[interval.physical_row]
        row_offset = row_offsets[interval.physical_row]
        for start, end in _interval_character_ranges(row_text, interval):
            renderable.stylize(style, row_offset + start, row_offset + end)
    return renderable


class HistorySurface(ScrollView):
    """The sole scrollable widget, drawing the listener's complete history."""

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
        self.history_text = build_history_text(listener, self.current_layout)
        self._line_texts: tuple[Text, ...] = ()
        self._logical_rows = listener.history.rows
        self._history_revision = -1
        self._content_width = 0
        self._pending_request: object = _UNSET
        self._update_line_texts()

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

    def _update_line_texts(self) -> None:
        lines: list[Text] = []
        offset = 0
        for row in self.current_layout.rows:
            lines.append(self.history_text[offset : offset + len(row.text)])
            offset += len(row.text) + 1
        self._line_texts = tuple(lines)

    def _oldest_visible_logical_row(self) -> object | None:
        if not self.current_layout.rows or not self._logical_rows:
            return None
        physical_row = min(
            max(0, int(self.scroll_y)), len(self.current_layout.rows) - 1
        )
        logical_index = self.current_layout.rows[physical_row].logical_row
        if logical_index >= len(self._logical_rows):
            return None
        return self._logical_rows[logical_index]

    def _anchored_scroll_y(self, anchor: object, fallback: int) -> int:
        logical_index = next(
            (
                index
                for index, row in enumerate(self.listener.history.rows)
                if row is anchor
            ),
            None,
        )
        if logical_index is None:
            return fallback
        return next(
            (
                index
                for index, row in enumerate(self.current_layout.rows)
                if row.logical_row == logical_index
            ),
            fallback,
        )

    def _clamp_scroll_row(self, row: int) -> int:
        viewport_height = (
            self.scrollable_content_region.height if self.is_mounted else 0
        )
        maximum = max(0, len(self.current_layout.rows) - viewport_height)
        return min(max(0, row), maximum)

    def synchronize(self, *, force: bool = False) -> bool:
        """Relayout changed history/width and refresh all derived drawing state."""

        content_width = self.content_width
        revision = self.listener.history.revision
        width_changed = content_width != self._content_width
        pending_request = self.listener.pending_request
        state_changed = pending_request is not self._pending_request
        if (
            not force
            and revision == self._history_revision
            and not width_changed
            and not state_changed
        ):
            return False

        fallback_scroll = int(self.scroll_y)
        anchor = self._oldest_visible_logical_row() if width_changed else None
        self.current_layout = layout(self.listener.history, content_width)
        self._logical_rows = self.listener.history.rows
        self._history_revision = revision
        self._content_width = content_width
        self._pending_request = pending_request

        retained = set(self.current_layout.presentations)
        if self.hovered_presentation not in retained:
            self.hovered_presentation = None
        self.history_text = build_history_text(
            self.listener, self.current_layout, self.hovered_presentation
        )
        self._update_line_texts()
        self.virtual_size = Size(content_width, len(self.current_layout.rows))

        target_scroll = fallback_scroll
        if anchor is not None:
            target_scroll = self._anchored_scroll_y(anchor, fallback_scroll)
        target_scroll = self._clamp_scroll_row(target_scroll)
        self.scroll_to(y=target_scroll, animate=False, force=True, immediate=True)
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
            return
        self.hovered_presentation = presentation
        self.history_text = build_history_text(
            self.listener, self.current_layout, presentation
        )
        self._update_line_texts()
        self.refresh()
        self._refresh_documentation()

    def scroll_to_row(self, row: int) -> None:
        """Programmatically scroll in the history's physical-row unit."""

        target = self._clamp_scroll_row(int(row))
        self.scroll_to(y=target, animate=False, force=True, immediate=True)

    def _refresh_documentation(self) -> None:
        if self.is_mounted and isinstance(self.screen, ListenerScreen):
            self.screen.documentation_line.set_presentation(
                self.hovered_presentation
            )

    def on_mount(self) -> None:
        self.synchronize(force=True)

    def on_resize(self, _event: events.Resize) -> None:
        self.synchronize()

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

    @property
    def sentence(self) -> str:
        return format_documentation(self.listener, self.presentation)

    def set_presentation(self, presentation: Presentation | None) -> None:
        self.presentation = presentation
        self.refresh()

    def render(self) -> Text:
        width = self.content_size.width if self.is_mounted else display_width(self.sentence)
        return Text(
            truncate_display(self.sentence, width),
            no_wrap=True,
            overflow="crop",
        )


class CommandInput(Widget):
    """Passive one-row drawing for prompt, editor cursor, and atomic chip."""

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

    @property
    def prompt(self) -> str:
        return format_prompt(self.listener)

    @property
    def display_text(self) -> str:
        text = self.prompt + self.listener.input_text
        chip = self.listener.chip
        if chip is not None:
            text += f" ⟨{chip.presentation_type.name}: {chip.label}⟩"
        return text

    def _cursor_index(self, text: str) -> int:
        input_start = len(self.prompt)
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
    """The sole screen containing the three fixed product regions."""

    DEFAULT_CSS = """
    ListenerScreen {
        layout: vertical;
    }
    """

    def __init__(self, listener: HeadlessListener) -> None:
        super().__init__()
        self.listener = listener
        self.history_surface = HistorySurface(listener, id="history")
        self.documentation_line = DocumentationLine(listener, id="documentation")
        self.command_input = CommandInput(listener, id="command-input")

    def compose(self) -> ComposeResult:
        yield self.history_surface
        yield self.documentation_line
        yield self.command_input

    def on_mount(self) -> None:
        self.command_input.focus()

    def synchronize(self) -> None:
        self.history_surface.synchronize()
        self.documentation_line.set_presentation(
            self.history_surface.hovered_presentation
        )
        self.command_input.refresh()


class PbuiApp(App[None]):
    """A passive Textual application adapting one injected listener."""

    def __init__(self, listener: HeadlessListener) -> None:
        if not isinstance(listener, HeadlessListener):
            raise TypeError("PbuiApp requires a HeadlessListener")
        super().__init__()
        self.listener = listener

    def get_default_screen(self) -> ListenerScreen:
        return ListenerScreen(self.listener)


__all__ = [
    "CommandInput",
    "DocumentationLine",
    "HistorySurface",
    "ListenerScreen",
    "PbuiApp",
    "build_history_text",
    "display_width",
    "format_documentation",
    "format_prompt",
    "presentation_style",
    "truncate_display",
]
