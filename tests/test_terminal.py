from __future__ import annotations

import ast
import importlib
import os
import signal
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from rich.console import Console
from textual import events
from textual.geometry import Offset
from textual.widget import Widget
from textual.widgets import Button, Label, Static

from pbui import terminal as terminal_module
from pbui.commands import HeadlessListener, InspectedProcess, RootedFilesystem
from pbui.domain import DirectoryRef, FileRef, ProcessRef
from pbui.repl import ValueTranslator
from pbui.substrate import Chip, Presentation, PresentationType
from pbui.terminal import (
    ActionMenu,
    CommandInput,
    DocumentationLine,
    HistorySurface,
    ListenerScreen,
    PbuiApp,
    build_history_text,
    display_width,
    filter_one_row,
    format_documentation,
    main,
    presentation_style,
    truncate_display,
)
from pbui.text import (
    DrawingContext,
    display_width as pure_display_width,
    layout,
    truncate_display as pure_truncate_display,
)


PROJECT_ROOT = Path(__file__).parents[1]


@dataclass
class FixedProcesses:
    own_uid: int = 1000
    own_pid: int = 700
    records: dict[int, InspectedProcess] = field(default_factory=dict)
    sent: list[tuple[int, signal.Signals]] = field(default_factory=list)

    def list_for_uid(self, uid):
        return tuple(
            record for record in self.records.values() if record.real_uid == uid
        )

    def inspect(self, pid):
        try:
            return self.records[pid]
        except KeyError:
            raise ProcessLookupError("process is gone") from None

    def send_sigterm(self, pid):
        self.sent.append((pid, signal.SIGTERM))


def make_listener(tmp_path, *, history_max_rows=500):
    return HeadlessListener(
        str(tmp_path),
        RootedFilesystem(tmp_path),
        FixedProcesses(
            records={
                42: InspectedProcess(42, 1000, "sleeping", "worker"),
                700: InspectedProcess(700, 1000, "running", "pbui"),
            }
        ),
        history_max_rows=history_max_rows,
    )


def domain_presentations(listener):
    types = listener.types
    return {
        "File": Presentation(10_001, types.file, FileRef("/tmp/a name")),
        "Directory": Presentation(
            10_002, types.directory, DirectoryRef("/tmp/a directory")
        ),
        "Process": Presentation(10_003, types.process, ProcessRef(42)),
        "Text": Presentation(10_004, types.text, "plain"),
        "Error": Presentation(10_005, types.error, "failure"),
    }


def _process_listener(tmp_path, records, *, displayed_user="tester"):
    return HeadlessListener(
        str(tmp_path),
        RootedFilesystem(tmp_path),
        FixedProcesses(own_pid=-1, records={record.pid: record for record in records}),
        username_lookup=lambda _uid: displayed_user,
    )


def _offset_for_logical_column(surface, presentation, logical_column):
    logical_row = surface.current_layout.rows[
        presentation.intervals[0].physical_row
    ].logical_row
    remaining = logical_column
    for physical_row, rendered_row in enumerate(surface.current_layout.rows):
        if rendered_row.logical_row != logical_row:
            continue
        if remaining < rendered_row.display_width:
            return (
                remaining,
                physical_row - int(surface.scroll_y),
            )
        remaining -= rendered_row.display_width
    raise AssertionError(f"logical column {logical_column} is outside the row")


def _first_physical_row(surface, logical_row):
    logical_index = next(
        index for index, row in enumerate(surface._logical_rows) if row is logical_row
    )
    return next(
        index
        for index, row in enumerate(surface.current_layout.rows)
        if row.logical_row == logical_index
    )


def _top_logical_row(surface):
    return surface._logical_rows[
        surface.current_layout.rows[int(surface.scroll_y)].logical_row
    ]


def _append_plain_rows(listener, count, *, prefix="after"):
    for index in range(count):
        listener.history.append(
            listener.drawing_contexts.standalone.present_row(
                f"{prefix}-{index}", listener.types.text
            )
        )


def test_dependency_metadata_and_terminal_import_boundary():
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_file:
        metadata = tomllib.load(project_file)

    dependencies = metadata["project"]["dependencies"]
    development = metadata["dependency-groups"]["dev"]
    assert dependencies == [
        "rich>=15.0.0",
        "textual>=8.2.8",
        "wcwidth>=0.8.4",
    ]
    assert development == ["pytest>=9.1.1", "pytest-asyncio>=1.4.0"]
    assert metadata["project"]["scripts"] == {"pbui": "pbui.terminal:main"}
    module_entry = importlib.import_module("pbui.__main__")
    assert module_entry.main is terminal_module.main

    textual_importers = []
    for source_path in (PROJECT_ROOT / "src/pbui").glob("*.py"):
        tree = ast.parse(source_path.read_text(), filename=str(source_path))
        imports = {
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        imports.update(
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        if "textual" in imports:
            textual_importers.append(source_path.name)
    assert textual_importers == ["terminal.py"]


def _key_names(text):
    return tuple("space" if character == " " else character for character in text)


def _mouse_event(
    event_type,
    surface,
    x,
    y,
    *,
    button=0,
    chain=1,
):
    widget_x = surface.gutter.left + x
    widget_y = surface.gutter.top + y
    arguments = dict(
        widget=surface,
        x=widget_x,
        y=widget_y,
        delta_x=0,
        delta_y=0,
        button=button,
        shift=False,
        meta=False,
        ctrl=False,
        screen_x=surface.region.x + widget_x,
        screen_y=surface.region.y + widget_y,
    )
    if event_type is events.Click:
        arguments["chain"] = chain
    return event_type(**arguments)


def _click_menu_label(menu, label):
    index = menu.labels.index(label)
    menu.scroll_to(y=index, animate=False, force=True, immediate=True)
    y = index - int(menu.scroll_y)
    menu.on_click(_mouse_event(events.Click, menu, 0, y, button=1))


@pytest.mark.asyncio
async def test_empty_app_mounts_exact_fixed_regions(tmp_path):
    listener = make_listener(tmp_path)
    app = PbuiApp(listener)

    async with app.run_test(size=(50, 12)) as pilot:
        await pilot.pause()
        assert isinstance(app.screen, ListenerScreen)
        children = list(app.screen.children)
        assert [type(child) for child in children] == [
            HistorySurface,
            ActionMenu,
            DocumentationLine,
            CommandInput,
        ]
        assert [child.id for child in children] == [
            "history",
            "action-menu",
            "documentation",
            "command-input",
        ]
        history, menu, documentation, command = children
        assert menu.region.height == 0
        assert not menu.is_open
        assert documentation.region.height == 1
        assert command.region.height == 1
        assert history.region.height == 10
        assert history.current_layout.rows == ()
        assert history.virtual_size.height == 0
        assert documentation.sentence == "No presentation under pointer."


@pytest.mark.asyncio
async def test_one_literal_history_renderable_uses_content_width_and_no_item_widgets(
    tmp_path,
):
    (tmp_path / "[bold]literal").write_text("x")
    (tmp_path / "directory").mkdir()
    listener = make_listener(tmp_path)
    listener.submit(": ls")
    listener.submit(": ps")
    listener.history.append(
        listener.drawing_contexts.standalone.present_row(
            "plain [not markup]", listener.types.text
        )
    )
    listener.submit(": unknown")
    app = PbuiApp(listener)

    async with app.run_test(size=(28, 9)) as pilot:
        await pilot.pause()
        surface = app.screen.query_one("#history", HistorySurface)
        expected = "\n".join(row.text for row in surface.current_layout.rows)
        assert surface.history_text.plain == expected
        assert "[bold]literal" in surface.history_text.plain
        assert "[not markup]" in surface.history_text.plain
        assert surface.current_layout.width == surface.scrollable_content_region.width
        assert surface.virtual_size.height == len(surface.current_layout.rows)
        assert not tuple(app.screen.query(Button))
        assert not tuple(app.screen.query(Label))
        assert not tuple(app.screen.query(Static))
        assert len(tuple(app.screen.query(Widget))) < len(
            listener.history.presentations
        ) + 8


def test_display_intervals_become_character_spans_without_styling_literals(tmp_path):
    listener = make_listener(tmp_path)
    context = DrawingContext()
    inner_value = FileRef(str(tmp_path / "A界é"))

    def draw_file(value, _context):
        assert value is inner_value
        return "A界é"

    def draw_outer(value, active_context):
        assert value == "outer"
        return "[", active_context.present(inner_value, listener.types.file), "]"

    context.register_drawer(listener.types.file, draw_file)
    context.register_drawer(listener.types.text, draw_outer)
    listener.history.append(context.present_row("outer", listener.types.text))

    current_layout = layout(listener.history, 4)
    outer, inner = current_layout.presentations
    assert [row.text for row in current_layout.rows] == ["[A界", "é]"]
    assert current_layout.hit_test(1, 0) is inner
    assert current_layout.hit_test(0, 0) is outer
    assert current_layout.hit_test(1, 1) is outer
    assert current_layout.hit_test(3, 0) is inner
    assert inner.value is inner_value

    rich_text = build_history_text(listener, current_layout, inner)
    assert rich_text.plain == "[A界\né]"
    console = Console()
    assert not rich_text.get_style_at_offset(console, 0).reverse
    assert rich_text.get_style_at_offset(console, 1).reverse
    assert rich_text.get_style_at_offset(console, 2).reverse
    assert not rich_text.get_style_at_offset(console, 3).reverse
    assert rich_text.get_style_at_offset(console, 4).reverse
    assert rich_text.get_style_at_offset(console, 5).reverse
    assert not rich_text.get_style_at_offset(console, 6).reverse


@pytest.mark.asyncio
async def test_large_wrapped_process_history_rebuilds_only_hover_rows(
    tmp_path, monkeypatch
):
    process_count = 240
    records = {
        index + 1: InspectedProcess(
            index + 1,
            1000,
            "sleeping",
            f"worker-{index:03d} [literal] " + f"argument-{index:03d} " * 12,
        )
        for index in range(process_count)
    }
    listener = HeadlessListener(
        str(tmp_path),
        RootedFilesystem(tmp_path),
        FixedProcesses(own_pid=-1, records=records),
    )
    app = PbuiApp(listener)

    async with app.run_test(size=(36, 9)) as pilot:
        listener.submit(": ps")
        surface = app.screen.history_surface
        surface.synchronize(force=True)
        await pilot.pause()

        processes = [
            presentation
            for presentation in surface.current_layout.presentations
            if presentation.presentation_type is listener.types.process
        ]
        first, second = processes[40], processes[180]
        first_rows = {interval.physical_row for interval in first.intervals}
        second_rows = {interval.physical_row for interval in second.intervals}
        assert len(first_rows) > 1
        assert len(second_rows) > 1
        assert len(surface.current_layout.rows) > 10 * len(
            first_rows | second_rows
        )

        logical_text = {
            logical_row: "".join(
                row.text
                for row in surface.current_layout.rows
                if row.logical_row == logical_row
            )
            for logical_row in range(process_count + 1)
        }
        assert logical_text[0] == (
            f"{'pid':>10}  {'state':<10}  {'user':<16}  {'command':<48}"
        )
        listing = listener.history.rows[0].listing_owner
        displayed_users = {
            member.reference.pid: member.displayed_user for member in listing.members
        }
        for logical_row, record in enumerate(
            sorted(records.values(), key=lambda item: item.pid), start=1
        ):
            command = pure_truncate_display(record.command, 48)
            assert logical_text[logical_row] == (
                f"{record.pid:>10}  {record.state:<10}  "
                f"{displayed_users[record.pid]:<16}  "
                f"{command:<48}"
            )

        original_builder = terminal_module.build_history_row_text
        built_rows = []

        def record_row_build(*args, **kwargs):
            built_rows.append(args[2])
            return original_builder(*args, **kwargs)

        def reject_history_build(*_args, **_kwargs):
            pytest.fail("hover rebuilt the history-wide compatibility text")

        monkeypatch.setattr(
            terminal_module, "build_history_row_text", record_row_build
        )
        monkeypatch.setattr(
            terminal_module, "build_history_text", reject_history_build
        )
        console = Console()

        before_first = tuple(surface._line_texts)
        surface.set_hovered_presentation(first)
        assert built_rows == sorted(first_rows)
        for physical_row, previous_line in enumerate(before_first):
            if physical_row in first_rows:
                assert surface._line_texts[physical_row] is not previous_line
            else:
                assert surface._line_texts[physical_row] is previous_line
        for interval in first.intervals:
            row = surface.current_layout.rows[interval.physical_row]
            line = surface._line_texts[interval.physical_row]
            for start, end in terminal_module._interval_character_ranges(
                row.text, interval
            ):
                assert all(
                    line.get_style_at_offset(console, index).reverse
                    for index in range(start, end)
                )

        built_rows.clear()
        unchanged = tuple(surface._line_texts)
        surface.set_hovered_presentation(first)
        assert built_rows == []
        assert all(
            current is previous
            for current, previous in zip(
                surface._line_texts, unchanged, strict=True
            )
        )

        built_rows.clear()
        before_second = tuple(surface._line_texts)
        affected = first_rows | second_rows
        surface.set_hovered_presentation(second)
        assert built_rows == sorted(affected)
        for physical_row, previous_line in enumerate(before_second):
            if physical_row in affected:
                assert surface._line_texts[physical_row] is not previous_line
            else:
                assert surface._line_texts[physical_row] is previous_line
        for presentation, reverse in ((first, False), (second, True)):
            for interval in presentation.intervals:
                row = surface.current_layout.rows[interval.physical_row]
                line = surface._line_texts[interval.physical_row]
                for start, end in terminal_module._interval_character_ranges(
                    row.text, interval
                ):
                    assert all(
                        line.get_style_at_offset(console, index).reverse is reverse
                        for index in range(start, end)
                    )


@pytest.mark.parametrize(
    ("command", "acceptable"),
    [
        ("rm", {"File"}),
        ("cd", {"Directory"}),
        ("kill", {"Process"}),
        ("show", {"File", "Directory", "Process"}),
    ],
)
def test_visual_states_follow_exact_accept_types(tmp_path, command, acceptable):
    listener = make_listener(tmp_path)
    presentations = domain_presentations(listener)

    normal = presentation_style(listener, presentations["File"], None)
    error = presentation_style(listener, presentations["Error"], None)
    hovered = presentation_style(
        listener, presentations["File"], presentations["File"]
    )
    assert normal.color is not None and normal.color.name == "default"
    assert not normal.bold and not normal.underline and not normal.dim
    assert error.color is not None and error.color.name == "red"
    assert hovered.reverse

    listener.submit(": " + command)
    for name, presentation in presentations.items():
        style = presentation_style(listener, presentation, presentation)
        if name in acceptable:
            assert style.color is not None and style.color.triplet.hex == "#00d787"
            assert style.bold and style.underline and not style.dim and style.reverse
        else:
            assert style.color is not None and style.color.triplet.hex == "#808080"
            assert style.dim and not style.bold and not style.underline
            assert not style.reverse

    counterfeit = Presentation(
        20_000, PresentationType("File"), presentations["File"].value
    )
    counterfeit_style = presentation_style(listener, counterfeit, counterfeit)
    assert counterfeit_style.dim and not counterfeit_style.reverse


def test_listing_semantic_colors_headers_and_cached_state_precedence(tmp_path):
    state_colors = {
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
    records = [
        InspectedProcess(pid, 1000, state, f"command-{state}")
        for pid, state in enumerate(state_colors, start=1)
    ]
    listener = _process_listener(tmp_path, records)
    process_service = listener.processes
    listener.submit(": ps")
    listing = listener.history.rows[0].listing_owner
    assert listing.header_presentation is not None

    header = presentation_style(
        listener, listing.header_presentation, listing.header_presentation
    )
    assert header.color is not None and header.color.name == "default"
    assert header.bold and header.reverse and not header.dim

    by_pid = {
        member.reference.pid: presentation
        for member, presentation in zip(
            listing.members, listing.member_presentations, strict=True
        )
    }
    for record in records:
        presentation = by_pid[record.pid]
        style = presentation_style(listener, presentation, None)
        assert style.color is not None
        assert style.color.triplet.hex == state_colors[record.state]
        hovered = presentation_style(listener, presentation, presentation)
        assert hovered.color == style.color and hovered.reverse

    process_service.records[1] = InspectedProcess(1, 1000, "dead", "changed")
    cached = presentation_style(listener, by_pid[1], None)
    assert cached.color is not None and cached.color.triplet.hex == "#00d787"

    assert listener.apply_listing_view(listing, "sort", "state")
    assert presentation_style(listener, by_pid[1], None).color == cached.color

    synthetic = domain_presentations(listener)["Process"]
    synthetic_style = presentation_style(listener, synthetic, None)
    assert synthetic_style.color is not None
    assert synthetic_style.color.name == "default"

    listener.submit(": kill")
    acceptable = presentation_style(listener, by_pid[2], by_pid[2])
    assert acceptable.color is not None
    assert acceptable.color.triplet.hex == "#00d787"
    assert acceptable.bold and acceptable.underline and acceptable.reverse
    inert_header = presentation_style(
        listener, listing.header_presentation, listing.header_presentation
    )
    assert inert_header.color is not None
    assert inert_header.color.triplet.hex == "#808080"
    assert inert_header.dim and not inert_header.bold
    assert not inert_header.underline and not inert_header.reverse


def test_directory_colors_and_whole_process_row_styling(tmp_path):
    (tmp_path / "file").write_text("payload")
    (tmp_path / "directory").mkdir()
    listener = make_listener(tmp_path)
    listener.submit(": ls")
    directory_listing = listener.history.rows[0].listing_owner
    by_value_type = {
        type(presentation.value): presentation
        for presentation in directory_listing.member_presentations
    }
    file_style = presentation_style(listener, by_value_type[FileRef], None)
    directory_style = presentation_style(
        listener, by_value_type[DirectoryRef], None
    )
    assert file_style.color is not None and file_style.color.name == "default"
    assert directory_style.color is not None
    assert directory_style.color.triplet.hex == "#00afff"
    header_style = presentation_style(
        listener, directory_listing.header_presentation, None
    )
    assert header_style.bold

    process_listener = _process_listener(
        tmp_path,
        [InspectedProcess(7, 1000, "sleeping", "x" * 80)],
        displayed_user="a-user-name-that-truncates",
    )
    process_listener.submit(": ps")
    process_listing = process_listener.history.rows[0].listing_owner
    presentation = process_listing.member_presentations[0]
    current_layout = layout(process_listener.history, 120)
    physical_row = presentation.intervals[0].physical_row
    row = current_layout.rows[physical_row]
    rich_row = terminal_module.build_history_row_text(
        process_listener, current_layout, physical_row
    )
    console = Console()
    assert row.text.endswith("…")
    assert len(row.text) == 90
    for column in (0, 9, 10, 11, 21, 22, 23, 39, 40, 41, 42, 89):
        assert current_layout.hit_test(column, physical_row) is presentation
    for index in range(len(row.text)):
        style = rich_row.get_style_at_offset(console, index)
        assert style.color is not None
        assert style.color.triplet.hex == "#5f87d7"


def test_documentation_formatter_covers_normative_table(tmp_path):
    listener = make_listener(tmp_path)
    item = domain_presentations(listener)
    assert format_documentation(listener, None) == "No presentation under pointer."
    assert format_documentation(listener, item["File"]) == (
        "Click to show file “a name”."
    )
    assert format_documentation(listener, item["Directory"]) == (
        "Click to show directory “a directory”."
    )
    assert format_documentation(listener, item["Process"]) == (
        "Click to show process 42."
    )
    assert format_documentation(listener, item["Text"]) == (
        "Text has no default click action."
    )
    assert format_documentation(listener, item["Error"]) == (
        "Error has no default click action."
    )

    cases = {
        "rm": [
            "Accept File for rm: point to a highlighted File and click; Ctrl-G or Esc cancels.",
            "Accept File for rm: click to use file “a name” and run rm.",
            "Accept File for rm: directory “a directory” is not a File target.",
            "Accept File for rm: process 42 is not a File target.",
            "Accept File for rm: Text is not a File target.",
            "Accept File for rm: Error is not a File target.",
        ],
        "cd": [
            "Accept Directory for cd: point to a highlighted Directory and click; Ctrl-G or Esc cancels.",
            "Accept Directory for cd: file “a name” is not a Directory target.",
            "Accept Directory for cd: click to use directory “a directory” and run cd.",
            "Accept Directory for cd: process 42 is not a Directory target.",
            "Accept Directory for cd: Text is not a Directory target.",
            "Accept Directory for cd: Error is not a Directory target.",
        ],
        "kill": [
            "Accept Process for kill: point to a highlighted Process and click; Ctrl-G or Esc cancels.",
            "Accept Process for kill: file “a name” is not a Process target.",
            "Accept Process for kill: directory “a directory” is not a Process target.",
            "Accept Process for kill: click to use process 42 and run kill.",
            "Accept Process for kill: Text is not a Process target.",
            "Accept Process for kill: Error is not a Process target.",
        ],
        "show": [
            "Accept File, Directory, or Process for show: point to a highlighted File, Directory, or Process and click; Ctrl-G or Esc cancels.",
            "Accept File, Directory, or Process for show: click to use file “a name” and run show.",
            "Accept File, Directory, or Process for show: click to use directory “a directory” and run show.",
            "Accept File, Directory, or Process for show: click to use process 42 and run show.",
            "Accept File, Directory, or Process for show: Text is not a File, Directory, or Process target.",
            "Accept File, Directory, or Process for show: Error is not a File, Directory, or Process target.",
        ],
    }
    pointers = [None, item["File"], item["Directory"], item["Process"], item["Text"], item["Error"]]
    for command, expected in cases.items():
        listener.cancel()
        listener.submit(": " + command)
        assert [format_documentation(listener, pointer) for pointer in pointers] == expected

    counterfeit = Presentation(30_000, PresentationType("File"), FileRef("/tmp/x"))
    listener.cancel()
    assert format_documentation(listener, counterfeit) == (
        "No presentation under pointer."
    )


def test_listing_header_documentation_and_all_accept_refusals(tmp_path):
    (tmp_path / "file").write_text("payload")
    listener = make_listener(tmp_path)
    listener.submit(": ls")
    listener.submit(": ps")
    directory_listing = listener.history.rows[0].listing_owner
    process_listing = next(
        row.listing_owner
        for row in listener.history.rows
        if row.listing_owner is not directory_listing
    )
    headers = (
        directory_listing.header_presentation,
        process_listing.header_presentation,
    )
    assert format_documentation(listener, headers[0]) == (
        "Directory listing: Ctrl-O or right-click to open its view menu."
    )
    assert format_documentation(listener, headers[1]) == (
        "Process listing: Ctrl-O or right-click to open its view menu."
    )

    expected = {
        "rm": (
            "Accept File for rm: directory listing is not a File target.",
            "Accept File for rm: process listing is not a File target.",
        ),
        "cd": (
            "Accept Directory for cd: directory listing is not a Directory target.",
            "Accept Directory for cd: process listing is not a Directory target.",
        ),
        "kill": (
            "Accept Process for kill: directory listing is not a Process target.",
            "Accept Process for kill: process listing is not a Process target.",
        ),
        "show": (
            "Accept File, Directory, or Process for show: directory listing is not a File, Directory, or Process target.",
            "Accept File, Directory, or Process for show: process listing is not a File, Directory, or Process target.",
        ),
    }
    for command, sentences in expected.items():
        listener.cancel()
        listener.submit(": " + command)
        assert tuple(format_documentation(listener, header) for header in headers) == (
            sentences
        )


def test_truncated_command_documentation_uses_cached_field_and_exact_boundaries(
    tmp_path,
):
    listener = _process_listener(
        tmp_path,
        [
            InspectedProcess(10, 1000, "running", "x" * 48),
            InspectedProcess(11, 1000, "sleeping", "y" * 49),
            InspectedProcess(12, 1000, "idle", "short"),
        ],
        displayed_user="user-name-that-is-far-too-wide",
    )
    listener.submit(": ps")
    listing = listener.history.rows[0].listing_owner
    by_pid = {
        presentation.value.pid: presentation
        for presentation in listing.member_presentations
    }
    ordinary_10 = "Click to show process 10."
    ordinary_11 = "Click to show process 11."
    ordinary_12 = "Click to show process 12."
    assert format_documentation(listener, by_pid[10], 42) == ordinary_10
    assert format_documentation(listener, by_pid[11], 41) == ordinary_11
    assert format_documentation(listener, by_pid[11], 42) == (
        "Command is truncated; click to show the full command for process 11."
    )
    assert format_documentation(listener, by_pid[11], 89) == (
        "Command is truncated; click to show the full command for process 11."
    )
    assert format_documentation(listener, by_pid[11], 90) == ordinary_11
    assert format_documentation(listener, by_pid[12], 42) == ordinary_12


def test_documentation_truncation_is_one_row_and_display_safe(tmp_path):
    listener = make_listener(tmp_path)
    line = DocumentationLine(listener)
    assert "height: 1" in line.DEFAULT_CSS
    assert truncate_display("short", 10) == "short"
    assert truncate_display("界x", 2) == "…"
    assert truncate_display("Aé界Z", 4) == "Aé…"
    assert display_width(truncate_display("Aé界Z", 4)) <= 4
    assert not truncate_display("Aé界Z", 4).endswith("e…")
    assert terminal_module.display_width is pure_display_width
    assert terminal_module.truncate_display is pure_truncate_display


@pytest.mark.asyncio
async def test_wrapped_command_field_refreshes_documentation_without_restyling(
    tmp_path, monkeypatch
):
    listener = _process_listener(
        tmp_path,
        [
            InspectedProcess(21, 1000, "running", "long-command-" * 8),
            InspectedProcess(22, 1000, "sleeping", "short"),
        ],
    )
    listener.submit(": ps")
    listing = listener.history.rows[0].listing_owner
    long_process, short_process = listing.member_presentations
    app = PbuiApp(listener)

    async with app.run_test(size=(24, 14)) as pilot:
        await pilot.pause()
        surface = app.screen.history_surface
        documentation = app.screen.documentation_line
        assert len({item.physical_row for item in long_process.intervals}) > 1

        built_rows = []
        original_builder = terminal_module.build_history_row_text

        def record_row_build(*args, **kwargs):
            built_rows.append(args[2])
            return original_builder(*args, **kwargs)

        monkeypatch.setattr(
            terminal_module, "build_history_row_text", record_row_build
        )

        x, y = _offset_for_logical_column(surface, long_process, 41)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, x, y))
        assert documentation.sentence == "Click to show process 21."
        assert surface.pointer_logical_column == 41
        assert built_rows

        built_rows.clear()
        x, y = _offset_for_logical_column(surface, long_process, 42)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, x, y))
        assert documentation.sentence == (
            "Command is truncated; click to show the full command for process 21."
        )
        assert surface.pointer_logical_column == 42
        assert built_rows == []

        x, y = _offset_for_logical_column(surface, long_process, 89)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, x, y))
        assert documentation.sentence == (
            "Command is truncated; click to show the full command for process 21."
        )
        assert surface.pointer_logical_column == 89
        assert built_rows == []

        x, y = _offset_for_logical_column(surface, long_process, 41)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, x, y))
        assert documentation.sentence == "Click to show process 21."
        assert built_rows == []

        long_start = long_process.intervals[0].physical_row
        short_start = short_process.intervals[0].physical_row
        surface.scroll_to_row(short_start - long_start)
        assert documentation.sentence != (
            "Command is truncated; click to show the full command for process 21."
        )

        await pilot.resize_terminal(28, 14)
        await pilot.pause()
        assert documentation.sentence == format_documentation(
            listener,
            surface.hovered_presentation,
            surface.pointer_logical_column,
        )

        assert listener.apply_listing_view(listing, "narrow", "short")
        surface.synchronize()
        assert documentation.sentence == format_documentation(
            listener,
            surface.hovered_presentation,
            surface.pointer_logical_column,
        )
        assert "process 21" not in documentation.sentence


def test_prompt_cursor_and_atomic_chip_are_passive_listener_drawing(tmp_path):
    child = tmp_path / "child"
    child.mkdir()
    listener = make_listener(tmp_path)
    listener.set_input_text("show")
    command = CommandInput(listener)
    assert command.prompt == f"pbui:{tmp_path}> "
    assert command.display_text == f"pbui:{tmp_path}> show"
    command.cursor_position = 2
    assert command.cursor_position == 2
    command.cursor_position = 100
    assert command.cursor_position == 4

    original = FileRef(str(tmp_path / "[literal] name"))
    listener.state.chip = Chip(listener.types.file, original, "[literal] name")
    listener.set_input_text("show")
    assert command.display_text == (
        f"pbui:{tmp_path}> show ⟨File: [literal] name⟩"
    )
    assert listener.chip is not None and listener.chip.value is original
    assert listener.input_text == "show"

    listener.state.chip = None
    listener.submit(": cd child")
    assert command.prompt == f"pbui:{child}> "
    assert os.getcwd() != str(child)
    listener.submit(": rm")
    assert "File" not in command.prompt


@pytest.mark.asyncio
async def test_scroll_and_resize_preserve_logical_anchor_and_fixed_regions(tmp_path):
    listener = make_listener(tmp_path, history_max_rows=12)
    for index in range(10):
        listener.history.append(
            listener.drawing_contexts.standalone.present_row(
                f"logical-{index}:" + "x" * 50, listener.types.text
            )
        )
    app = PbuiApp(listener)

    async with app.run_test(size=(24, 9)) as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, ListenerScreen)
        surface = screen.history_surface
        anchor_index = next(
            index
            for index, row in enumerate(surface.current_layout.rows)
            if row.logical_row == 3
        )
        anchor = listener.history.rows[3]
        presentation = listener.history.presentations[3]
        old_intervals = presentation.intervals
        documentation_region = screen.documentation_line.region
        command_region = screen.command_input.region

        surface.scroll_to_row(anchor_index)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, 0, 0))
        assert surface.pointer_offset == Offset(0, 0)
        await pilot.pause()
        assert int(surface.scroll_y) == anchor_index
        await pilot.resize_terminal(16, 9)
        await pilot.pause()

        top_physical = int(surface.scroll_y)
        top_logical = surface.current_layout.rows[top_physical].logical_row
        assert listener.history.rows[top_logical] is anchor
        assert presentation.intervals is not old_intervals
        assert (
            screen.documentation_line.region.y,
            screen.documentation_line.region.height,
        ) == (documentation_region.y, documentation_region.height)
        assert (screen.command_input.region.y, screen.command_input.region.height) == (
            command_region.y,
            command_region.height,
        )
        assert surface.current_layout.width == surface.scrollable_content_region.width
        assert surface.hovered_presentation is surface.presentation_at_content_offset(
            0, 0
        )

        for index in range(10, 16):
            listener.history.append(
                listener.drawing_contexts.standalone.present_row(
                    f"logical-{index}:" + "y" * 50, listener.types.text
                )
            )
        await pilot.resize_terminal(18, 9)
        surface.synchronize()
        await pilot.pause()
        assert 0 <= surface.scroll_y <= surface.max_scroll_y


@pytest.mark.asyncio
async def test_listing_replacement_keeps_outside_row_identity_at_viewport_top(tmp_path):
    for index in range(8):
        (tmp_path / f"item-{index}").write_text("data")
    listener = make_listener(tmp_path)
    listener.submit(": ls")
    listing = listener.history.rows[0].listing_owner
    _append_plain_rows(listener, 12)
    outside = tuple(row for row in listener.history.rows if row.listing_owner is None)
    app = PbuiApp(listener)

    async with app.run_test(size=(28, 8)):
        surface = app.screen.history_surface
        anchor = outside[2]
        surface.scroll_to_row(_first_physical_row(surface, anchor))
        assert _top_logical_row(surface) is anchor
        revision = listener.history.revision

        assert listener.apply_listing_view(listing, "narrow", "item-0")
        surface.synchronize()
        assert listener.history.revision == revision + 1
        assert len(listener.history.rows) == len(outside) + 2
        assert _top_logical_row(surface) is anchor
        assert tuple(row for row in listener.history.rows if row.listing_owner is None) == outside

        assert listener.apply_listing_view(listing, "widen")
        surface.synchronize()
        assert len(listener.history.rows) == len(outside) + 9
        assert _top_logical_row(surface) is anchor
        assert all(
            current is original
            for current, original in zip(
                (row for row in listener.history.rows if row.listing_owner is None),
                outside,
                strict=True,
            )
        )


@pytest.mark.asyncio
async def test_listing_header_member_sort_filter_widen_and_missing_member_anchor(
    tmp_path, monkeypatch
):
    records = [
        InspectedProcess(pid, 1000, "sleeping" if pid == 1 else "running", f"worker-{pid}")
        for pid in range(1, 10)
    ]
    listener = _process_listener(tmp_path, records)
    listener.submit(": ps")
    monkeypatch.setattr(
        listener.processes,
        "list_for_uid",
        lambda _uid: pytest.fail("redisplay recaptured processes"),
    )
    listing = listener.history.rows[0].listing_owner
    _append_plain_rows(listener, 10)
    member = listing.member_presentations[0]
    app = PbuiApp(listener)

    async with app.run_test(size=(34, 8)):
        surface = app.screen.history_surface
        header = listener.history.rows[0]
        surface.scroll_to_row(_first_physical_row(surface, header))
        assert listener.apply_listing_view(listing, "sort", "state")
        surface.synchronize()
        assert _top_logical_row(surface).presentations == (listing.header_presentation,)

        old_member_row = next(row for row in listener.history.rows if member in row.presentations)
        surface.scroll_to_row(_first_physical_row(surface, old_member_row))
        old_logical_index = next(i for i, row in enumerate(listener.history.rows) if row is old_member_row)
        assert listener.apply_listing_view(listing, "sort", "pid")
        surface.synchronize()
        assert member in _top_logical_row(surface).presentations
        assert next(i for i, row in enumerate(listener.history.rows) if member in row.presentations) != old_logical_index

        assert listener.apply_listing_view(listing, "narrow", "worker-1")
        surface.synchronize()
        assert member in _top_logical_row(surface).presentations
        assert listener.apply_listing_view(listing, "widen")
        surface.synchronize()
        assert member in _top_logical_row(surface).presentations

        assert listener.apply_listing_view(listing, "narrow", "worker-5")
        surface.synchronize()
        assert _top_logical_row(surface).presentations == (listing.header_presentation,)


@pytest.mark.asyncio
async def test_listing_anchor_fallbacks_after_header_and_outside_row_eviction(tmp_path):
    records = [
        InspectedProcess(pid, 1000, "running", f"worker-{pid}")
        for pid in range(1, 7)
    ]
    listener = HeadlessListener(
        str(tmp_path),
        RootedFilesystem(tmp_path),
        FixedProcesses(own_pid=-1, records={record.pid: record for record in records}),
        history_max_rows=9,
    )
    listener.submit(": ps")
    listing = listener.history.rows[0].listing_owner
    assert listener.apply_listing_view(listing, "narrow", "worker-1")
    _append_plain_rows(listener, 7)
    app = PbuiApp(listener)

    async with app.run_test(size=(24, 7)):
        surface = app.screen.history_surface
        header = listener.history.rows[0]
        surface.scroll_to_row(_first_physical_row(surface, header))
        assert _top_logical_row(surface) is header
        assert listener.apply_listing_view(listing, "widen")
        first_retained = listener.history.rows[0]
        assert first_retained.listing_owner is listing
        assert listing.header_presentation not in first_retained.presentations
        surface.synchronize()
        assert _top_logical_row(surface) is first_retained

    four_records = records[:4]
    listener = HeadlessListener(
        str(tmp_path),
        RootedFilesystem(tmp_path),
        FixedProcesses(own_pid=-1, records={record.pid: record for record in four_records}),
        history_max_rows=9,
    )
    _append_plain_rows(listener, 4, prefix="before")
    oldest = listener.history.rows[0]
    listener.submit(": ps")
    listing = listener.history.rows[4].listing_owner
    assert listener.apply_listing_view(listing, "narrow", "worker-1")
    _append_plain_rows(listener, 3)
    app = PbuiApp(listener)
    async with app.run_test(size=(24, 7)):
        surface = app.screen.history_surface
        surface.scroll_to_row(0)
        assert _top_logical_row(surface) is oldest
        assert listener.apply_listing_view(listing, "widen")
        assert all(row is not oldest for row in listener.history.rows)
        first_retained = listener.history.rows[0]
        surface.synchronize()
        assert _top_logical_row(surface) is first_retained


@pytest.mark.asyncio
async def test_fully_evicted_listing_anchor_uses_first_retained_history_row(tmp_path):
    listener = HeadlessListener(
        str(tmp_path),
        RootedFilesystem(tmp_path),
        FixedProcesses(
            own_pid=-1,
            records={1: InspectedProcess(1, 1000, "running", "worker")},
        ),
        history_max_rows=5,
    )
    listener.submit(": ps")
    listing = listener.history.rows[0].listing_owner
    _append_plain_rows(listener, 3)
    app = PbuiApp(listener)

    async with app.run_test(size=(24, 7)):
        surface = app.screen.history_surface
        surface.scroll_to_row(0)
        assert _top_logical_row(surface).listing_owner is listing
        _append_plain_rows(listener, 2, prefix="new")
        first_retained = listener.history.rows[0]
        assert all(row.listing_owner is not listing for row in listener.history.rows)
        surface.synchronize()
        assert _top_logical_row(surface) is first_retained


@pytest.mark.asyncio
async def test_wrapped_listing_anchor_survives_replacement_and_resizes(tmp_path):
    records = [
        InspectedProcess(pid, 1000, "sleeping", f"long-command-{pid}-" * 5)
        for pid in range(1, 10)
    ]
    listener = _process_listener(tmp_path, records)
    listener.submit(": ps")
    listing = listener.history.rows[0].listing_owner
    _append_plain_rows(listener, 10)
    member = listing.member_presentations[1]
    app = PbuiApp(listener)

    async with app.run_test(size=(24, 8)) as pilot:
        surface = app.screen.history_surface
        row = next(row for row in listener.history.rows if member in row.presentations)
        first = _first_physical_row(surface, row)
        surface.scroll_to_row(first + 1)
        assert int(surface.scroll_y) == first + 1
        assert listener.apply_listing_view(listing, "sort", "state")
        surface.synchronize()
        assert member in _top_logical_row(surface).presentations
        assert int(surface.scroll_y) - _first_physical_row(surface, _top_logical_row(surface)) == 1

        await pilot.resize_terminal(30, 8)
        assert member in _top_logical_row(surface).presentations
        assert int(surface.scroll_y) - _first_physical_row(surface, _top_logical_row(surface)) == 1
        await pilot.resize_terminal(30, 6)
        assert member in _top_logical_row(surface).presentations
        assert int(surface.scroll_y) - _first_physical_row(surface, _top_logical_row(surface)) == 1
        await pilot.resize_terminal(30, 9)
        assert member in _top_logical_row(surface).presentations
        assert int(surface.scroll_y) - _first_physical_row(surface, _top_logical_row(surface)) == 1
        surface.synchronize(force=True)
        assert member in _top_logical_row(surface).presentations
        assert int(surface.scroll_y) - _first_physical_row(surface, _top_logical_row(surface)) == 1
        assert app.screen.documentation_line.region.height == 1
        assert app.screen.command_input.region.height == 1
        assert app.screen.history_surface.region.height == 7


@pytest.mark.asyncio
async def test_explanatory_row_anchor_and_wrapped_offset_clamp(tmp_path):
    listener = _process_listener(
        tmp_path,
        [InspectedProcess(1, 1000, "running", "worker")],
    )
    listener.submit(": ps")
    listing = listener.history.rows[0].listing_owner
    _append_plain_rows(listener, 12)
    app = PbuiApp(listener)

    async with app.run_test(size=(24, 7)) as pilot:
        surface = app.screen.history_surface
        member = next(row for row in listener.history.rows if row.presentations == listing.member_presentations)
        first = _first_physical_row(surface, member)
        surface.scroll_to_row(first + 2)
        assert _top_logical_row(surface) is member
        assert listener.apply_listing_view(listing, "narrow", "no-such-command")
        surface.synchronize()
        assert _top_logical_row(surface).presentations == (listing.header_presentation,)
        assert int(surface.scroll_y) - _first_physical_row(surface, _top_logical_row(surface)) == 2
        await pilot.resize_terminal(120, 7)
        assert _top_logical_row(surface).presentations == (listing.header_presentation,)
        assert int(surface.scroll_y) == _first_physical_row(surface, _top_logical_row(surface))

        explanation = next(row for row in listener.history.rows if row.listing_owner is listing and not row.presentations)
        surface.scroll_to_row(_first_physical_row(surface, explanation))
        assert _top_logical_row(surface) is explanation
        assert listener.apply_listing_view(listing, "only", "sleeping")
        surface.synchronize()
        assert _top_logical_row(surface).listing_owner is listing
        assert not _top_logical_row(surface).presentations
        await pilot.resize_terminal(30, 7)
        assert _top_logical_row(surface).listing_owner is listing
        assert not _top_logical_row(surface).presentations
        assert listener.apply_listing_view(listing, "widen")
        surface.synchronize()
        assert _top_logical_row(surface).presentations == (listing.header_presentation,)


@pytest.mark.asyncio
async def test_typed_view_and_modal_narrow_keep_anchor_but_appends_reveal_newest(tmp_path):
    records = [
        InspectedProcess(pid, 1000, "sleeping" if pid == 1 else "running", f"worker-{pid}")
        for pid in range(1, 9)
    ]
    listener = _process_listener(tmp_path, records)
    listener.submit(": ps")
    listing = listener.history.rows[0].listing_owner
    _append_plain_rows(listener, 12)
    app = PbuiApp(listener)

    async with app.run_test(size=(30, 7)) as pilot:
        surface = app.screen.history_surface
        member = listing.member_presentations[0]
        row = next(row for row in listener.history.rows if member in row.presentations)
        surface.scroll_to_row(_first_physical_row(surface, row))
        assert member in _top_logical_row(surface).presentations

        for command_text in ("sort state", "only sleeping", "widen"):
            revision = listener.history.revision
            listener.set_input_text(": " + command_text)
            app.screen.command_input.cursor_position = len(command_text)
            await pilot.press("enter")
            assert listener.history.revision == revision + 1
            assert member in _top_logical_row(surface).presentations

        revision = listener.history.revision
        await pilot.press(*_key_names(":narrow"), "enter")
        assert listener.pending_substring_listing is listing
        assert listener.history.revision == revision
        assert member in _top_logical_row(surface).presentations
        await pilot.press(*_key_names("worker-1"), "enter")
        assert listener.pending_substring_listing is None
        assert listener.history.revision == revision + 1
        assert member in _top_logical_row(surface).presentations

        listener.set_input_text(": unknown")
        app.screen.command_input.cursor_position = len(listener.input_text)
        await pilot.press("enter")
        assert int(surface.scroll_y) == int(surface.max_scroll_y)
        surface.scroll_to_row(_first_physical_row(surface, _top_logical_row(surface)))
        listener.set_input_text(": ps")
        app.screen.command_input.cursor_position = 2
        await pilot.press("enter")
        assert int(surface.scroll_y) == int(surface.max_scroll_y)
        assert listener.history.rows[-1].listing_owner is not listing


@pytest.mark.asyncio
async def test_hover_and_documentation_rehit_after_view_resize_and_pointer_exit(tmp_path):
    records = [
        InspectedProcess(1, 1000, "sleeping", "worker-1"),
        InspectedProcess(2, 1000, "running", "worker-2"),
    ]
    listener = _process_listener(tmp_path, records)
    listener.submit(": ps")
    listing = listener.history.rows[0].listing_owner
    _append_plain_rows(listener, 14)
    app = PbuiApp(listener)

    async with app.run_test(size=(34, 12)) as pilot:
        surface = app.screen.history_surface
        documentation = app.screen.documentation_line
        header = listener.history.rows[0]
        surface.scroll_to_row(_first_physical_row(surface, header))
        first_member = next(row for row in listener.history.rows if row.presentations == (listing.member_presentations[0],))
        y = _first_physical_row(surface, first_member) - int(surface.scroll_y)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, 0, y))
        assert documentation.sentence == "Click to show process 1."

        revision = listener.history.revision
        assert listener.apply_listing_view(listing, "sort", "state")
        surface.synchronize()
        assert listener.history.revision == revision + 1
        assert surface.hovered_presentation is listing.member_presentations[1]
        assert documentation.sentence == "Click to show process 2."

        assert listener.apply_listing_view(listing, "narrow", "worker-1")
        surface.synchronize()
        assert surface.hovered_presentation is listing.member_presentations[0]
        assert documentation.sentence == "Click to show process 1."

        await pilot.resize_terminal(26, 12)
        assert surface.hovered_presentation is surface.presentation_at_content_offset(0, y)
        assert documentation.sentence == format_documentation(
            listener, surface.hovered_presentation, surface.pointer_logical_column
        )

        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, 0, 8))
        assert surface.pointer_offset == Offset(0, 8)
        await pilot.resize_terminal(26, 6)
        assert surface.pointer_offset is None
        assert surface.hovered_presentation is None
        assert documentation.sentence == "No presentation under pointer."
        assert listener.history.revision == revision + 2


@pytest.mark.asyncio
async def test_editor_inserts_moves_and_deletes_by_code_point(tmp_path):
    listener = make_listener(tmp_path)
    app = PbuiApp(listener)

    async with app.run_test(size=(50, 8)) as pilot:
        command = app.screen.command_input
        await pilot.press("a", "b", "c", "home", "X", "right", "Y", "end", "Z")
        assert listener.input_text == "XaYbcZ"
        assert command.cursor_position == 6

        await pilot.press("left", "backspace", "delete", "right")
        assert listener.input_text == "XaYb"
        assert command.cursor_position == 4

        await pilot.press("home", "left", "backspace")
        assert listener.input_text == "XaYb"
        assert command.cursor_position == 0


@pytest.mark.asyncio
async def test_paste_is_one_row_and_tab_remains_focus_navigation(tmp_path):
    listener = make_listener(tmp_path)
    listener.set_input_text("ab")
    app = PbuiApp(listener)

    assert filter_one_row(" X\nY\r\t\x00\x85\ud800界 ") == " XY界 "
    async with app.run_test(size=(50, 8)) as pilot:
        command = app.screen.command_input
        command.cursor_position = 1
        command.post_message(events.Paste(" X\nY\r\t\x00\x85\ud800界 "))
        await pilot.pause()
        assert listener.input_text == "a XY界 b"
        assert command.cursor_position == 6

        before = listener.input_text
        await pilot.press("tab")
        assert listener.input_text == before
        command.post_message(events.Key("unknown", "\ud800"))
        await pilot.pause()
        assert listener.input_text == before


@pytest.mark.asyncio
async def test_visible_substring_accept_editor_submission_and_cancellation(tmp_path):
    target = tmp_path / "target-file"
    target.write_text("payload")
    listener = make_listener(tmp_path)
    listener.submit(": ls")
    listing = listener.history.rows[0].listing_owner
    member = next(
        presentation
        for presentation in listing.member_presentations
        if type(presentation.value) is FileRef
    )
    app = PbuiApp(listener)

    async with app.run_test(size=(46, 10)) as pilot:
        command = app.screen.command_input
        documentation = app.screen.documentation_line
        surface = app.screen.history_surface
        await pilot.press(*_key_names(":narrow"), "enter")

        prefix = f"pbui:{tmp_path}> narrow "
        assert listener.pending_substring_listing is listing
        assert listener.input_text == ""
        assert listener.chip is None
        assert command.display_text == prefix
        assert command.cursor_position == 0
        assert command._cursor_index(command.display_text) == len(prefix)
        assert documentation.sentence == (
            "Type a substring and press Enter to narrow this listing; "
            "Ctrl-G or Esc cancels."
        )
        rendered_documentation = documentation.render().plain
        assert "\n" not in rendered_documentation
        assert rendered_documentation.endswith("…")

        revision = listener.history.revision
        await pilot.press("left", "backspace", "home", "enter", "ctrl+d")
        assert app.is_running
        assert listener.pending_substring_listing is listing
        assert listener.input_text == ""
        assert listener.history.revision == revision
        assert command.display_text == prefix

        interval = member.intervals[0]
        surface.scroll_to_row(interval.physical_row)
        y = interval.physical_row - int(surface.scroll_y)
        surface.on_click(
            _mouse_event(
                events.Click,
                surface,
                interval.start_column,
                y,
                button=1,
            )
        )
        assert listener.pending_substring_listing is listing
        assert listener.history.revision == revision
        assert documentation.sentence.startswith("Type a substring")

        await pilot.press("a", "b", "c", "home", "left", "backspace", "delete")
        assert listener.input_text == "bc"
        assert command.cursor_position == 0
        command.post_message(events.Paste("X\nY\t"))
        await pilot.pause()
        assert listener.input_text == "XYbc"
        assert command.cursor_position == 2
        assert command.display_text == prefix + "XYbc"
        assert command._cursor_index(command.display_text) == len(prefix) + 2

        await pilot.press("enter")
        assert listener.pending_substring_listing is None
        assert listener.input_text == ""
        assert listener.history.revision == revision + 1
        assert command.display_text == f"pbui:{tmp_path}> "
        assert not documentation.sentence.startswith("Type a substring")

        post_submit_revision = listener.history.revision
        await pilot.press(*_key_names(":narrow"), "enter", "q", "escape")
        assert listener.pending_substring_listing is None
        assert listener.input_text == ""
        assert listener.history.revision == post_submit_revision
        assert command.display_text == f"pbui:{tmp_path}> "

        await pilot.press(*_key_names(":narrow"), "enter", "z", "ctrl+g")
        assert listener.pending_substring_listing is None
        assert listener.input_text == ""
        assert listener.history.revision == post_submit_revision


@pytest.mark.asyncio
async def test_adjacent_backspace_removes_chip_as_one_editor_unit(tmp_path):
    listener = make_listener(tmp_path)
    listener.set_input_text("show")
    original = FileRef(str(tmp_path / "file with space"))
    listener.state.chip = Chip(listener.types.file, original, "file with space")
    app = PbuiApp(listener)

    async with app.run_test(size=(60, 8)) as pilot:
        command = app.screen.command_input
        command.cursor_position = len(listener.input_text)
        await pilot.press("backspace")
        assert listener.input_text == "show"
        assert listener.chip is None
        assert command.cursor_position == 4

        listener.state.chip = Chip(listener.types.file, original, "file with space")
        command.cursor_position = 2
        await pilot.press("backspace")
        assert listener.input_text == "sow"
        assert listener.chip is not None
        assert listener.chip.value is original


@pytest.mark.asyncio
async def test_pilot_submission_preserves_objects_and_fixed_regions(tmp_path):
    child = tmp_path / "known child"
    child.write_text("known")
    listener = make_listener(tmp_path)
    app = PbuiApp(listener)

    async with app.run_test(size=(60, 9)) as pilot:
        await pilot.press("colon", "l", "s", "enter")
        await pilot.pause()
        matches = [
            presentation
            for presentation in listener.history.presentations
            if presentation.presentation_type is listener.types.file
            and type(presentation.value) is FileRef
            and presentation.value.path == str(child)
        ]
        assert len(matches) == 1
        assert isinstance(app.screen.documentation_line, DocumentationLine)
        assert isinstance(app.screen.command_input, CommandInput)
        assert app.screen.documentation_line.is_mounted
        assert app.screen.command_input.is_mounted


@pytest.mark.asyncio
async def test_enter_accept_cancel_and_typed_results_synchronize_views(tmp_path):
    child = tmp_path / "child"
    child.mkdir()
    listener = make_listener(tmp_path)
    for index in range(20):
        listener.history.append(
            listener.drawing_contexts.standalone.present_row(
                f"old-{index}", listener.types.text
            )
        )
    app = PbuiApp(listener)

    async with app.run_test(size=(44, 8)) as pilot:
        command = app.screen.command_input
        surface = app.screen.history_surface
        documentation_prefixes = {
            "rm": "Accept File for rm:",
            "cd": "Accept Directory for cd:",
            "kill": "Accept Process for kill:",
            "show": "Accept File, Directory, or Process for show:",
        }
        for command_name in ("rm", "cd", "kill", "show"):
            listener.cancel()
            listener.set_input_text("")
            command.cursor_position = 0
            await pilot.press(*_key_names(":" + command_name), "enter")
            assert listener.pending_request is not None
            assert listener.pending_request.command_name == command_name
            assert listener.input_text == command_name
            assert command.cursor_position == len(command_name)
            assert app.screen.documentation_line.sentence.startswith(
                documentation_prefixes[command_name]
            )
            await pilot.press("ctrl+g")
            assert listener.input_text == ""
            assert listener.pending_request is None
            assert listener.chip is None
            assert command.cursor_position == 0

        listener.set_input_text(": cd child")
        command.cursor_position = len(listener.input_text)
        revision = listener.history.revision
        old_scroll = int(surface.scroll_y)
        await pilot.press("enter")
        assert listener.cwd == str(child)
        assert listener.history.revision == revision
        assert int(surface.scroll_y) == old_scroll
        assert command.prompt == f"pbui:{child}> "
        assert listener.input_text == ""

        listener.set_input_text(": unknown")
        command.cursor_position = len(listener.input_text)
        await pilot.press("enter")
        assert listener.input_text == ""
        assert command.cursor_position == 0
        assert int(surface.scroll_y) == int(surface.max_scroll_y)
        assert listener.history.presentations[-1].presentation_type is listener.types.error

        listener.set_input_text("rm")
        listener.submit(": rm")
        listener.state.chip = Chip(
            listener.types.file, FileRef(str(tmp_path / "unused")), "unused"
        )
        command.cursor_position = len(listener.input_text)
        await pilot.press("escape")
        assert listener.input_text == ""
        assert listener.pending_request is None
        assert listener.chip is None
        assert command.cursor_position == 0
        assert surface.hovered_presentation is None


@pytest.mark.asyncio
async def test_ctrl_d_guard_and_ctrl_c_exit_bindings(tmp_path):
    listener = make_listener(tmp_path)
    app = PbuiApp(listener)
    async with app.run_test(size=(40, 8)) as pilot:
        await pilot.press("x", "ctrl+d")
        assert app.is_running
        assert listener.input_text == "x"

        listener.set_input_text("")
        listener.submit(": rm")
        await pilot.press("ctrl+d")
        assert app.is_running
        assert listener.pending_request is not None

        listener.cancel()
        listener.state.chip = Chip(
            listener.types.file, FileRef(str(tmp_path / "unused")), "unused"
        )
        await pilot.press("ctrl+d")
        assert app.is_running

        listener.state.chip = None
        await pilot.press("ctrl+d")
        await pilot.pause()
        assert not app.is_running

    listener = make_listener(tmp_path)
    listener.set_input_text("still editing")
    app = PbuiApp(listener)
    async with app.run_test(size=(40, 8)) as pilot:
        await pilot.press("ctrl+c")
        await pilot.pause()
        assert not app.is_running


@pytest.mark.asyncio
async def test_coordinates_hover_click_selection_and_literal_misses(tmp_path, monkeypatch):
    target = tmp_path / "file with space"
    target.write_text("payload")
    (tmp_path / "directory").mkdir()
    listener = make_listener(tmp_path)
    listener.submit(": ls")
    target_presentation = next(
        presentation
        for presentation in listener.history.presentations
        if type(presentation.value) is FileRef
    )
    app = PbuiApp(listener)

    async with app.run_test(size=(60, 8)) as pilot:
        surface = app.screen.history_surface
        await pilot.pause()
        interval = target_presentation.intervals[0]
        surface.scroll_to_row(interval.physical_row)
        y = interval.physical_row - int(surface.scroll_y)
        x = interval.start_column
        move = _mouse_event(events.MouseMove, surface, x, y)
        assert surface.content_offset_from_event(move) == Offset(x, y)
        assert surface.presentation_at_content_offset(x, y) is target_presentation
        assert surface.presentation_at_content_offset(0, y) is target_presentation
        literal_x = surface.current_layout.rows[interval.physical_row].display_width + 1
        assert surface.presentation_at_content_offset(literal_x, y) is None

        assert app.screen.command_input.has_focus
        assert not surface.can_focus
        await pilot.click(surface, offset=(literal_x, y))
        assert app.screen.command_input.has_focus

        surface.on_mouse_move(move)
        assert surface.hovered_presentation is target_presentation
        assert app.screen.documentation_line.sentence == (
            "Click to show file “file with space”."
        )
        surface.on_leave(events.Leave(surface))
        assert surface.hovered_presentation is None
        assert app.screen.documentation_line.sentence == (
            "No presentation under pointer."
        )

        calls = []

        def record_select(presentation, label=""):
            calls.append((presentation, label))
            return False

        monkeypatch.setattr(listener, "select", record_select)
        surface.on_click(
            _mouse_event(events.Click, surface, x, y, button=3, chain=1)
        )
        surface.on_click(
            _mouse_event(events.Click, surface, x, y, button=1, chain=2)
        )
        assert calls == []
        surface.on_click(
            _mouse_event(events.Click, surface, x, y, button=1, chain=1)
        )
        assert calls == []
        assert not app.screen.action_menu.is_open
        surface.on_click(
            _mouse_event(events.Click, surface, x, y, button=1, chain=1)
        )
        assert calls == [(target_presentation, "file with space")]


@pytest.mark.asyncio
async def test_click_uses_original_objects_for_accept_default_and_refusals(tmp_path):
    target = tmp_path / "delete me"
    target.write_text("payload")
    directory = tmp_path / "directory"
    directory.mkdir()
    listener = make_listener(tmp_path)
    listener.submit(": ls")
    file_presentation = next(
        item for item in listener.history.presentations if type(item.value) is FileRef
    )
    directory_presentation = next(
        item
        for item in listener.history.presentations
        if type(item.value) is DirectoryRef
    )
    app = PbuiApp(listener)

    async with app.run_test(size=(60, 9)) as pilot:
        surface = app.screen.history_surface

        def click_presentation(presentation):
            interval = presentation.intervals[0]
            surface.scroll_to_row(interval.physical_row)
            y = interval.physical_row - int(surface.scroll_y)
            surface.on_click(
                _mouse_event(
                    events.Click,
                    surface,
                    interval.start_column,
                    y,
                    button=1,
                )
            )

        listener.submit(": rm")
        app.screen.synchronize()
        revision = listener.history.revision
        click_presentation(directory_presentation)
        assert listener.pending_request is not None
        assert listener.input_text == "rm"
        assert listener.history.revision == revision
        assert directory.is_dir()

        click_presentation(file_presentation)
        assert not target.exists()
        assert listener.pending_request is None
        assert listener.input_text == ""
        assert listener.history.presentations[-1].value.startswith("Removed file:")

        revision = listener.history.revision
        click_presentation(directory_presentation)
        assert listener.history.revision == revision + 1
        assert str(directory) in listener.history.presentations[-1].value

        revision = listener.history.revision
        directory_interval = directory_presentation.intervals[0]
        surface.scroll_to_row(directory_interval.physical_row)
        y = directory_interval.physical_row - int(surface.scroll_y)
        literal_x = (
            surface.current_layout.rows[directory_interval.physical_row].display_width
            + 1
        )
        surface.on_click(
            _mouse_event(events.Click, surface, literal_x, y, button=1)
        )
        assert listener.history.revision == revision


@pytest.mark.asyncio
async def test_wheel_moves_three_rows_and_recomputes_hover(tmp_path):
    listener = make_listener(tmp_path)
    context = DrawingContext()
    context.register_drawer(
        listener.types.file,
        lambda value, _context: os.path.basename(value.path),
    )
    for index in range(30):
        listener.history.append(
            context.present_row(FileRef(f"/virtual/item-{index}"), listener.types.file)
        )
    app = PbuiApp(listener)

    async with app.run_test(size=(40, 8)) as pilot:
        surface = app.screen.history_surface
        documentation_region = app.screen.documentation_line.region
        command_region = app.screen.command_input.region
        surface.scroll_to_row(6)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, 0, 0))
        before = surface.hovered_presentation
        assert before is not None and before.value.path.endswith("item-6")

        surface.post_message(_mouse_event(events.MouseScrollDown, surface, 0, 0))
        await pilot.pause()
        assert int(surface.scroll_y) == 9
        assert surface.hovered_presentation is not before
        assert surface.hovered_presentation.value.path.endswith("item-9")

        surface.post_message(_mouse_event(events.MouseScrollUp, surface, 0, 0))
        await pilot.pause()
        assert int(surface.scroll_y) == 6
        assert surface.hovered_presentation is before
        assert app.screen.documentation_line.region == documentation_region
        assert app.screen.command_input.region == command_region

        surface.scroll_to_row(0)
        surface.post_message(_mouse_event(events.MouseScrollUp, surface, 0, 0))
        await pilot.pause()
        assert int(surface.scroll_y) == 0


@pytest.mark.asyncio
async def test_action_menu_private_presentations_labels_hits_and_documentation(tmp_path):
    (tmp_path / "file name").write_text("x")
    (tmp_path / "directory").mkdir()
    listener = make_listener(tmp_path)
    listener.submit(": ls")
    listener.submit(": ps")
    app = PbuiApp(listener)

    async with app.run_test(size=(100, 9)) as pilot:
        screen = app.screen
        menu = screen.action_menu
        original_registry = tuple(listener.registry)
        original_history = listener.history.rows
        targets = (
            (listener.types.file, ("show", "rm")),
            (listener.types.directory, ("show", "cd", "ls")),
            (listener.types.process, ("show", "kill")),
            (
                listener.types.directory_listing,
                ("sort name", "sort size", "sort mtime", "only files",
                 "only directories", "narrow", "widen"),
            ),
            (
                listener.types.process_listing,
                ("sort pid", "sort state", "sort command", "only running",
                 "only sleeping", "only disk-sleep", "only stopped",
                 "only tracing", "only zombie", "only dead", "only idle",
                 "only unknown", "narrow", "widen"),
            ),
        )
        for presentation_type, labels in targets:
            target = next(
                item for item in listener.history.presentations
                if item.presentation_type is presentation_type
            )
            screen.open_menu(target)
            await pilot.pause()
            assert menu.is_open
            assert menu.labels == labels
            assert len(menu.item_presentations) == len(labels)
            assert all(item.presentation_type is menu.menu_type for item in menu.item_presentations)
            assert all(item.value.target is target for item in menu.item_presentations)
            assert all(item.value.label == label for item, label in zip(menu.item_presentations, labels))
            assert screen.documentation_line.sentence == (
                "Point at an action and click; Ctrl-G or Esc closes the menu."
            )
            assert menu.region.y + menu.region.height == screen.documentation_line.region.y
            assert menu.region.height == min(len(labels), 6)
            assert menu.presentation_at_content_offset(0, 0) is menu.item_presentations[0]
            assert menu.presentation_at_content_offset(
                menu.scrollable_content_region.width - 1, 0
            ) is menu.item_presentations[0]
            menu.on_mouse_move(_mouse_event(events.MouseMove, menu, 0, 0))
            process_pid = next(
                item.value.pid for item in listener.history.presentations
                if item.presentation_type is listener.types.process
            )
            expected_documentation = {
                listener.types.file: f"Click to run “{labels[0]}” for file “file name”.",
                listener.types.directory: f"Click to run “{labels[0]}” for directory “directory”.",
                listener.types.process: f"Click to run “{labels[0]}” for process {process_pid}.",
                listener.types.directory_listing: f"Click to apply “{labels[0]}” to this directory listing.",
                listener.types.process_listing: f"Click to apply “{labels[0]}” to this process listing.",
            }[presentation_type]
            assert screen.documentation_line.sentence == expected_documentation
            if len(labels) > menu.region.height:
                menu.scroll_to(y=len(labels), animate=False, force=True, immediate=True)
                assert menu.presentation_at_content_offset(0, menu.region.height - 1) is menu.item_presentations[-1]
            if presentation_type is listener.types.process_listing:
                await pilot.resize_terminal(100, 5)
                await pilot.pause()
                assert menu.region.height == 2
                assert screen.documentation_line.region.y == 3
                assert screen.command_input.region.y == 4
                menu.scroll_to(y=len(labels), animate=False, force=True, immediate=True)
                assert menu.presentation_at_content_offset(0, 1) is menu.item_presentations[-1]
                await pilot.resize_terminal(100, 9)
                await pilot.pause()
            screen.close_menu()
            await pilot.pause()
            assert menu.region.height == 0
            assert menu.item_presentations == ()
        assert tuple(listener.registry) == original_registry
        assert listener.history.rows == original_history
        assert all(item.presentation_type is not menu.menu_type for item in listener.history.presentations)


@pytest.mark.asyncio
async def test_action_menu_gestures_refusals_modal_and_close_boundaries(tmp_path):
    (tmp_path / "file").write_text("x")
    listener = make_listener(tmp_path)
    listener.submit(": ls")
    listener._append_text("text")
    listener._append_error("error")
    context = DrawingContext()
    unrelated_type = PresentationType("Other")
    context.register_drawer(unrelated_type, lambda value, _context: value)
    listener.history.append(context.present_row("other", unrelated_type))
    app = PbuiApp(listener)

    async with app.run_test(size=(65, 12)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        menu = screen.action_menu
        file_target = next(
            item for item in listener.history.presentations
            if item.presentation_type is listener.types.file
        )
        interval = file_target.intervals[0]
        y = interval.physical_row - int(surface.scroll_y)
        x = min(interval.end_column - 1, 25)
        surface.on_click(_mouse_event(events.Click, surface, x, y, button=3))
        await pilot.pause()
        assert menu.target is file_target
        assert menu.labels == ("show", "rm")
        surface.on_click(_mouse_event(events.Click, surface, x, y, button=1, chain=2))
        assert menu.is_open
        assert screen.documentation_line.sentence.startswith("Point at an action")
        surface.on_leave(events.Leave(surface))
        assert menu.is_open
        menu.on_mouse_move(_mouse_event(events.MouseMove, menu, 0, 0))
        assert screen.documentation_line.sentence == "Click to run “show” for file “file”."
        menu.on_leave(events.Leave(menu))
        await pilot.pause()
        assert not menu.is_open

        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, x, y))
        await pilot.press("ctrl+o")
        await pilot.pause()
        assert menu.target is file_target
        listener.set_input_text("untouched")
        revision = listener.history.revision
        await pilot.press("ctrl+g")
        await pilot.pause()
        assert not menu.is_open
        assert listener.input_text == "untouched"
        assert listener.history.revision == revision
        await pilot.press("ctrl+o")
        await pilot.pause()
        assert menu.is_open
        await pilot.press("escape")
        await pilot.pause()
        assert not menu.is_open
        assert listener.input_text == "untouched"

        for target, expected in (
            (None, "Point at a presentation before opening an action menu."),
            (next(item for item in listener.history.presentations if item.presentation_type is listener.types.text), "Text has no action menu."),
            (next(item for item in listener.history.presentations if item.presentation_type is listener.types.error), "Error has no action menu."),
            (next(item for item in listener.history.presentations if item.presentation_type is unrelated_type), "This presentation has no action menu."),
        ):
            screen.open_menu(target)
            assert not menu.is_open
            assert screen.documentation_line.sentence == expected
            screen.synchronize()
            assert screen.documentation_line.sentence == expected
        text_target = next(
            item for item in listener.history.presentations
            if item.presentation_type is listener.types.text
        )
        text_interval = text_target.intervals[0]
        surface.on_mouse_move(
            _mouse_event(
                events.MouseMove, surface, text_interval.start_column,
                text_interval.physical_row - int(surface.scroll_y),
            )
        )
        assert screen.documentation_line.sentence == (
            "Move the cursor to a Python expression position to insert this value."
        )
        screen.open_menu(None)
        assert screen.documentation_line.sentence.startswith("Point at a presentation")
        listener.set_input_text("changed")
        screen.synchronize()
        assert screen.documentation_line.sentence == (
            "Move the cursor to a Python expression position to insert this value."
        )

        listener.submit(": rm")
        screen.synchronize()
        pending = listener.pending_request
        documentation = screen.documentation_line.sentence
        screen.open_menu(file_target)
        await pilot.press("ctrl+o")
        surface.on_click(_mouse_event(events.Click, surface, x, y, button=3))
        assert not menu.is_open
        assert listener.pending_request is pending
        assert screen.documentation_line.sentence == documentation
        listener.cancel()
        listener.submit(": narrow")
        screen.synchronize()
        pending_listing = listener.pending_substring_listing
        documentation = screen.documentation_line.sentence
        screen.open_menu(file_target)
        await pilot.press("ctrl+o")
        surface.on_click(_mouse_event(events.Click, surface, x, y, button=3))
        assert not menu.is_open
        assert listener.pending_substring_listing is pending_listing
        assert screen.documentation_line.sentence == documentation


@pytest.mark.asyncio
async def test_action_menu_older_listing_view_actions_and_bound_narrow(tmp_path):
    (tmp_path / "large").write_text("12345")
    (tmp_path / "small").write_text("x")
    (tmp_path / "directory").mkdir()
    listener = make_listener(tmp_path)
    listener.submit(": ls")
    directory_listing = listener.history.rows[0].listing_owner
    listener.submit(": ps")
    process_listing = next(
        row.listing_owner for row in listener.history.rows
        if row.listing_owner is not directory_listing
    )
    app = PbuiApp(listener)

    async with app.run_test(size=(100, 24)) as pilot:
        screen = app.screen
        menu = screen.action_menu
        header = directory_listing.header_presentation
        process_rows = tuple(
            row for row in listener.history.rows if row.listing_owner is process_listing
        )
        for label, view_field, expected in (
            ("sort size", "sort_key", "size"),
            ("only files", "kind_filter", "files"),
            ("widen", "kind_filter", None),
        ):
            screen.open_menu(header)
            await pilot.pause()
            _click_menu_label(menu, label)
            await pilot.pause()
            assert getattr(directory_listing.view, view_field) == expected
            assert process_listing.view.sort_key == "pid"
            assert tuple(row for row in listener.history.rows if row.listing_owner is process_listing) == process_rows
            assert {row.listing_owner for row in listener.history.rows} == {
                directory_listing, process_listing
            }
            assert not menu.is_open

        screen.open_menu(header)
        await pilot.pause()
        _click_menu_label(menu, "narrow")
        await pilot.pause()
        assert listener.pending_substring_listing is directory_listing
        assert screen.command_input.display_text.endswith("narrow ")
        listener.set_input_text("small")
        await pilot.press("enter")
        assert directory_listing.view.substring_filter == "small"
        assert process_listing.view.substring_filter is None
        assert tuple(row for row in listener.history.rows if row.listing_owner is process_listing) == process_rows

        screen.open_menu(process_listing.header_presentation)
        await pilot.pause()
        _click_menu_label(menu, "only sleeping")
        await pilot.pause()
        assert process_listing.view.kind_filter == "sleeping"
        assert directory_listing.view.kind_filter is None


@pytest.mark.asyncio
async def test_action_menu_member_actions_outside_click_and_stale_target(tmp_path):
    file_path = tmp_path / "file"
    file_path.write_text("payload")
    directory = tmp_path / "child"
    directory.mkdir()
    (directory / "nested").write_text("x")
    processes = FixedProcesses(
        records={42: InspectedProcess(42, 1000, "sleeping", "worker")}
    )
    listener = HeadlessListener(str(tmp_path), RootedFilesystem(tmp_path), processes)
    listener.submit(": ls")
    listing = listener.history.rows[0].listing_owner
    listener.submit(": ps")
    file_target = next(
        item for item in listener.history.presentations
        if item.presentation_type is listener.types.file
    )
    directory_target = next(
        item for item in listener.history.presentations
        if item.presentation_type is listener.types.directory
    )
    process_target = next(
        item for item in listener.history.presentations
        if item.presentation_type is listener.types.process
    )
    app = PbuiApp(listener)

    async with app.run_test(size=(100, 20)) as pilot:
        screen = app.screen
        menu = screen.action_menu
        screen.open_menu(file_target)
        await pilot.pause()
        rows_before = listener.history.rows
        interval = file_target.intervals[0]
        screen.history_surface.on_click(
            _mouse_event(
                events.Click, screen.history_surface,
                interval.start_column,
                interval.physical_row - int(screen.history_surface.scroll_y),
                button=1,
            )
        )
        await pilot.pause()
        assert not menu.is_open
        assert listener.history.rows == rows_before
        assert file_path.exists()

        for target, label in (
            (file_target, "show"),
            (directory_target, "show"),
            (process_target, "show"),
        ):
            screen.open_menu(target)
            await pilot.pause()
            revision = listener.history.revision
            _click_menu_label(menu, label)
            await pilot.pause()
            assert listener.history.revision == revision + 1
            assert not menu.is_open

        screen.open_menu(directory_target)
        await pilot.pause()
        before = len(listener.history.rows)
        _click_menu_label(menu, "ls")
        await pilot.pause()
        assert len(listener.history.rows) > before
        newest_listing = next(
            row.listing_owner for row in reversed(listener.history.rows)
            if row.listing_owner is not None
        )
        assert newest_listing is not listing
        assert newest_listing.directory is directory_target.value

        screen.open_menu(directory_target)
        await pilot.pause()
        _click_menu_label(menu, "cd")
        await pilot.pause()
        assert listener.cwd == str(directory)

        screen.open_menu(process_target)
        await pilot.pause()
        _click_menu_label(menu, "kill")
        await pilot.pause()
        assert processes.sent == [(42, signal.SIGTERM)]

        screen.open_menu(file_target)
        await pilot.pause()
        _click_menu_label(menu, "rm")
        await pilot.pause()
        assert not file_path.exists()

        screen.open_menu(process_target)
        await pilot.pause()
        for index in range(501):
            listener._append_error(f"eviction {index}")
        revision = listener.history.revision
        _click_menu_label(menu, "kill")
        await pilot.pause()
        assert listener.history.revision == revision
        assert processes.sent == [(42, signal.SIGTERM)]


@pytest.mark.asyncio
async def test_action_menu_open_close_and_view_keep_wrapped_viewport_anchor(tmp_path):
    (tmp_path / "long-file-name-for-wrapping").write_text("12345")
    listener = make_listener(tmp_path)
    _append_plain_rows(listener, 15, prefix="before-long-text")
    listener.submit(": ls")
    listing = next(row.listing_owner for row in listener.history.rows if row.listing_owner)
    member = listing.member_presentations[0]
    member_row = next(row for row in listener.history.rows if member in row.presentations)
    _append_plain_rows(listener, 25, prefix="after-long-text")
    app = PbuiApp(listener)

    async with app.run_test(size=(25, 9)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        first = _first_physical_row(surface, member_row)
        assert surface.current_layout.rows[first + 1].logical_row == surface.current_layout.rows[first].logical_row
        surface.scroll_to_row(first + 1)
        assert _top_logical_row(surface) is member_row
        assert int(surface.scroll_y) == first + 1
        hit = surface.presentation_at_content_offset(0, 0)
        assert hit is member
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, 0, 0))
        surface.on_click(_mouse_event(events.Click, surface, 0, 0, button=3))
        await pilot.pause()
        assert screen.action_menu.target is member
        assert _top_logical_row(surface) is member_row
        assert int(surface.scroll_y) == first + 1
        assert surface.hovered_presentation is surface.presentation_at_content_offset(0, 0)
        screen.action_menu.on_mouse_move(
            _mouse_event(events.MouseMove, screen.action_menu, 0, 0)
        )
        surface.on_leave(events.Leave(surface))
        await pilot.press("ctrl+g")
        await pilot.pause()
        assert _top_logical_row(surface) is member_row
        assert int(surface.scroll_y) == first + 1
        pointer = screen._pointer_screen
        region = surface.scrollable_content_region
        assert pointer in region
        assert surface.hovered_presentation is surface.presentation_at_content_offset(
            pointer.x - region.x, pointer.y - region.y
        )
        assert screen.documentation_line.sentence == format_documentation(
            listener, surface.hovered_presentation, surface.pointer_logical_column
        )

        screen.open_menu(listing.header_presentation)
        await pilot.pause()
        _click_menu_label(screen.action_menu, "sort size")
        await pilot.pause()
        assert listing.view.sort_key == "size"
        assert _top_logical_row(surface).listing_owner is listing
        assert int(surface.scroll_y) == _first_physical_row(surface, _top_logical_row(surface)) + 1

        screen.open_menu(member)
        await pilot.pause()
        _click_menu_label(screen.action_menu, "show")
        await pilot.pause()
        assert int(surface.scroll_y) == surface._clamp_scroll_row(
            len(surface.current_layout.rows)
        )


@pytest.mark.asyncio
async def test_action_menu_hover_repaints_only_item_rows(tmp_path, monkeypatch):
    (tmp_path / "file").write_text("x")
    listener = make_listener(tmp_path)
    listener.submit(": ls")
    _append_plain_rows(listener, 300)
    header = next(
        item for item in listener.history.presentations
        if item.presentation_type is listener.types.directory_listing
    )
    app = PbuiApp(listener)

    async with app.run_test(size=(70, 12)) as pilot:
        screen = app.screen
        screen.open_menu(header)
        await pilot.pause()
        menu = screen.action_menu
        history = screen.history_surface
        refreshed = []
        original_refresh = menu.refresh

        def record_refresh(*regions, **kwargs):
            refreshed.extend(regions)
            return original_refresh(*regions, **kwargs)

        def forbid_history_rebuild():
            pytest.fail("menu hover rebuilt history rows")

        monkeypatch.setattr(menu, "refresh", record_refresh)
        monkeypatch.setattr(history, "_build_all_rows", forbid_history_rebuild)
        menu.on_mouse_move(_mouse_event(events.MouseMove, menu, 0, 0))
        menu.on_mouse_move(_mouse_event(events.MouseMove, menu, 0, 1))
        assert [region.y for region in refreshed] == [0, 0, 1]
        assert all(region.height == 1 for region in refreshed)
        assert menu.hovered_presentation is menu.item_presentations[1]


def test_main_composes_runs_and_catches_only_keyboard_interrupt(tmp_path, monkeypatch):
    listener = make_listener(tmp_path)
    produced = []
    runs = []

    monkeypatch.setattr(
        terminal_module.HeadlessListener,
        "production",
        classmethod(lambda cls: produced.append(cls) or listener),
    )

    class FakeApp:
        def __init__(self, injected):
            assert injected is listener

        def run(self):
            runs.append("run")

    monkeypatch.setattr(terminal_module, "PbuiApp", FakeApp)
    main()
    assert produced == [HeadlessListener]
    assert runs == ["run"]

    def interrupt():
        raise KeyboardInterrupt

    FakeApp.run = lambda self: interrupt()
    main()

    def defect():
        raise RuntimeError("defect")

    FakeApp.run = lambda self: defect()
    with pytest.raises(RuntimeError, match="defect"):
        main()


@pytest.mark.asyncio
async def test_repl_continuation_prompt_documentation_and_modal_keys(tmp_path):
    listener = make_listener(tmp_path)
    listener.submit("1 + 1")
    target = next(p for p in listener.history.presentations if p.type is listener.types.value)
    app = PbuiApp(listener)
    async with app.run_test(size=(78, 10)) as pilot:
        screen = app.screen
        editor = screen.command_input
        assert editor.prompt == f"pbui:{tmp_path}> "
        for cancel_key in ("ctrl+g", "escape", "ctrl+d"):
            listener.set_input_text("if True:")
            editor.cursor_position = len(listener.input_text)
            await pilot.press("enter")
            assert listener.pending_python_source == "if True:"
            assert listener.input_text == ""
            assert editor.prompt == "...> "
            assert screen.documentation_line.sentence == (
                "Python continuation: enter another line; Ctrl-G or Esc discards it."
                if cancel_key == "ctrl+g" else
                "Move the cursor to a Python expression position to insert this value."
            )
            before = listener.history.rows
            await pilot.press("ctrl+o")
            assert not screen.action_menu.is_open
            interval = target.intervals[0]
            screen.history_surface.on_click(_mouse_event(
                events.Click, screen.history_surface, interval.start_column,
                interval.physical_row - int(screen.history_surface.scroll_y), button=3
            ))
            assert not screen.action_menu.is_open
            assert screen.documentation_line.sentence == "This presentation has no action menu."
            await pilot.press(cancel_key)
            assert app.is_running
            assert listener.pending_python_source == ""
            assert listener.input_text == ""
            assert listener.history.rows == before
            assert editor.prompt == f"pbui:{tmp_path}> "
        listener.set_input_text("if True:")
        editor.cursor_position = len(listener.input_text)
        await pilot.press("enter")
        await pilot.press("enter")
        assert listener.pending_python_source == "if True:\n"
        listener.set_input_text(":ls")
        editor.cursor_position = len(listener.input_text)
        await pilot.press("enter")
        assert listener.pending_python_source == ""
        assert listener.history.presentations[-1].type is listener.types.error
        assert not any(row.listing_owner is not None for row in listener.history.rows)
        listener.set_input_text("if True:")
        editor.cursor_position = len(listener.input_text)
        await pilot.press("enter")
        listener.set_input_text("    2 + 3")
        editor.cursor_position = len(listener.input_text)
        await pilot.press("enter")
        assert listener.pending_python_source
        await pilot.press("enter")
        assert listener.pending_python_source == ""
        assert editor.prompt == f"pbui:{tmp_path}> "
        assert listener.history.presentations[-1].type is listener.types.value
        listener.set_input_text("if True:")
        editor.cursor_position = len(listener.input_text)
        await pilot.press("enter")
        await pilot.press("ctrl+c")
        assert not app.is_running


@pytest.mark.asyncio
async def test_repl_value_wrapped_hit_click_hover_accept_and_history_order(tmp_path):
    listener = make_listener(tmp_path)
    listener.submit("list(range(100))")
    value = next(p for p in listener.history.presentations if p.type is listener.types.value)
    listener.submit('print("a"); 1')
    listener.submit('raise ValueError("bad")')
    assert [p.type for p in listener.history.presentations] == [
        listener.types.value, listener.types.text, listener.types.value,
        listener.types.error,
    ]
    app = PbuiApp(listener)
    async with app.run_test(size=(24, 8)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        assert len(value.intervals) > 1
        surface.scroll_to_row(value.intervals[1].physical_row)
        interval = value.intervals[1]
        y = interval.physical_row - int(surface.scroll_y)
        assert surface.presentation_at_content_offset(0, y) is value
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, 0, y))
        assert screen.documentation_line.sentence == (
            "Click to show this Python value; it has no action menu."
        )
        screen.open_menu(value)
        assert not screen.action_menu.is_open
        assert screen.documentation_line.sentence == "This presentation has no action menu."
        screen.synchronize()
        listener.set_input_text("")
        screen.synchronize()
        surface.on_click(_mouse_event(events.Click, surface, 0, y, button=1))
        assert listener.input_text == ""
        assert listener.history.presentations[-1].type is listener.types.text
        assert listener.history.presentations[-1].value.startswith("list: [")
        listener.cancel()
        listener.submit(":rm")
        screen.synchronize()
        surface.scroll_to_row(value.intervals[1].physical_row)
        y = value.intervals[1].physical_row - int(surface.scroll_y)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, 0, y))
        assert screen.documentation_line.sentence == (
            "Accept File for rm: Value is not a File target."
        )
        assert presentation_style(listener, value, value).dim
        before = listener.history.rows
        surface.on_click(_mouse_event(events.Click, surface, 0, y, button=1))
        assert listener.history.rows == before
        assert listener.chip is None and listener.pending_request is not None
        await pilot.press("escape")
        await pilot.resize_terminal(16, 8)
        await pilot.pause()
        surface.scroll_to_row(value.intervals[-1].physical_row)
        interval = value.intervals[-1]
        y = interval.physical_row - int(surface.scroll_y)
        assert surface.presentation_at_content_offset(0, y) is value
        assert screen.documentation_line.region.height == 1
        assert display_width(screen.documentation_line.render().plain) <= screen.documentation_line.content_size.width


@pytest.mark.asyncio
async def test_repl_registered_value_menu_keeps_translator_indices(tmp_path):
    class Dummy:
        def __repr__(self):
            return "dummy"

    listener = make_listener(tmp_path)
    original = Dummy()
    calls = []
    listener.register_python_class(Dummy, lambda value: "dummy row", (
        ValueTranslator("show", lambda value: calls.append((0, value)) or 7),
        ValueTranslator("show", lambda value: calls.append((1, value)) or None),
        ValueTranslator("fail", lambda value: 1 / 0),
    ))
    listener.python_namespace["item"] = original
    listener.submit("item")
    target = next(p for p in listener.history.presentations if p.type is listener.types.value)
    app = PbuiApp(listener)
    async with app.run_test(size=(95, 12)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        menu = screen.action_menu
        interval = target.intervals[0]
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface,
            interval.start_column, interval.physical_row - int(surface.scroll_y)))
        assert screen.documentation_line.sentence == (
            "Click to show this Python value; Ctrl-O or right-click to open its action menu."
        )
        await pilot.press("ctrl+o")
        await pilot.pause()
        assert menu.target is target
        assert menu.labels == ("show", "show", "fail")
        assert [p.value.translator_index for p in menu.item_presentations] == [0, 1, 2]
        menu.on_mouse_move(_mouse_event(events.MouseMove, menu, 0, 1))
        assert screen.documentation_line.sentence == (
            "Click to apply “show” to this Python value."
        )
        menu.on_click(_mouse_event(events.Click, menu, 0, 1, button=1))
        assert calls == [(1, original)]
        assert listener.python_namespace["_"] is None
        assert listener.history.presentations[-1].value is None
        await pilot.pause()
        screen.open_menu(target)
        await pilot.pause()
        assert menu.is_open
        menu.on_click(_mouse_event(events.Click, menu, 0, 0, button=1))
        assert calls[-1] == (0, original)
        assert listener.python_namespace["_"] == 7
        screen.open_menu(target)
        await pilot.pause()
        assert menu.is_open
        before = len(listener.history.presentations)
        menu.on_click(_mouse_event(events.Click, menu, 0, 2, button=1))
        assert len(listener.history.presentations) == before + 1
        assert listener.history.presentations[-1].type is listener.types.error
        assert listener.python_namespace["_"] == 7
        assert target.value is original
        surface.scroll_to_row(target.intervals[0].physical_row)
        interval = target.intervals[0]
        surface.on_click(_mouse_event(events.Click, surface,
            interval.start_column, interval.physical_row - int(surface.scroll_y), button=3))
        assert menu.target is target
        screen.close_menu()
        surface.on_click(_mouse_event(events.Click, surface,
            interval.start_column, interval.physical_row - int(surface.scroll_y), button=1))
        assert listener.history.presentations[-1].type is listener.types.text
        assert listener.history.presentations[-1].value == "Dummy: dummy"


@pytest.mark.asyncio
async def test_ctrl_d_blocks_substring_and_menu_then_exits(tmp_path):
    (tmp_path / "file").write_text("x")
    listener = make_listener(tmp_path)
    listener.submit(":ls")
    header = next(p for p in listener.history.presentations
                  if p.type is listener.types.directory_listing)
    app = PbuiApp(listener)
    async with app.run_test(size=(50, 10)) as pilot:
        screen = app.screen
        listener.submit(":narrow")
        screen.synchronize()
        await pilot.press("ctrl+d")
        assert app.is_running and listener.pending_substring_listing is not None
        await pilot.press("escape")
        screen.open_menu(header)
        await pilot.press("ctrl+d")
        assert app.is_running and not screen.action_menu.is_open
        await pilot.press("ctrl+d")
        assert not app.is_running


@pytest.mark.asyncio
async def test_repl_value_hover_restyles_only_affected_wrapped_rows(tmp_path, monkeypatch):
    listener = make_listener(tmp_path)
    _append_plain_rows(listener, 200, prefix="before")
    listener.submit("list(range(100))")
    value = next(p for p in listener.history.presentations if p.type is listener.types.value)
    listener.submit("42")
    other = [p for p in listener.history.presentations if p.type is listener.types.value][-1]
    _append_plain_rows(listener, 200)
    app = PbuiApp(listener)
    async with app.run_test(size=(20, 8)) as pilot:
        surface = app.screen.history_surface
        assert len(value.intervals) > 1
        surface.scroll_to_row(value.intervals[0].physical_row)
        built = []
        refreshed = []
        original_build = surface._build_row
        original_refresh = surface._refresh_physical_rows

        def record_build(row):
            built.append(row)
            return original_build(row)

        def record_refresh(rows):
            refreshed.append(set(rows))
            return original_refresh(rows)

        monkeypatch.setattr(surface, "_build_row", record_build)
        monkeypatch.setattr(surface, "_refresh_physical_rows", record_refresh)
        monkeypatch.setattr(surface, "_build_all_rows", lambda: pytest.fail("hover rebuilt all rows"))
        surface.set_hovered_presentation(value)
        surface.set_hovered_presentation(other)
        expected = {interval.physical_row for interval in value.intervals + other.intervals}
        assert set(built) == expected
        assert refreshed[0] == {interval.physical_row for interval in value.intervals}
        assert refreshed[1] == expected
        assert len(built) < len(surface.current_layout.rows)


@pytest.mark.asyncio
async def test_python_chip_click_draws_atom_and_executes_stored_value(tmp_path):
    listener = make_listener(tmp_path)
    listener.submit("2")
    target = next(p for p in listener.history.presentations if p.type is listener.types.value)
    app = PbuiApp(listener)
    async with app.run_test(size=(24, 8)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        editor = screen.command_input
        listener.set_input_text("10 + ()")
        editor.cursor_position = 6
        screen.synchronize()
        interval = target.intervals[0]
        y = interval.physical_row - int(surface.scroll_y)
        surface.on_click(_mouse_event(events.Click, surface, interval.start_column, y, button=1))
        assert len(listener.python_pieces) == 3
        assert listener.python_pieces[1].value is target.value
        assert editor.display_text.count("⟨int 2⟩") == 1
        assert editor._cursor_index(editor.display_text) == editor.display_text.index("⟨int 2⟩") + len("⟨int 2⟩")
        assert editor.render_line(0).cell_length == 24
        await pilot.press("enter")
        assert listener.history.presentations[-1].value == 12
        assert listener.python_pieces == ()

        listener.set_input_text("f()")
        editor.cursor_position = 2
        screen.synchronize()
        surface.on_click(_mouse_event(events.Click, surface, interval.start_column, y, button=1))
        chip = listener.python_pieces[1]
        assert chip.value is target.value
        editor.on_paste(events.Paste("xy\nz"))
        assert listener.input_text == "f(xyz)"
        await pilot.press("backspace", "backspace", "backspace")
        assert listener.python_pieces[1] is chip
        await pilot.press("backspace")
        assert listener.python_pieces == ("f()",)
        assert editor.display_text.endswith("f()")
        surface.on_click(_mouse_event(events.Click, surface, interval.start_column, y, button=1))
        await pilot.press("left", "delete")
        assert listener.python_pieces == ("f()",)
        surface.on_click(_mouse_event(events.Click, surface, interval.start_column, y, button=1))
        await pilot.press("home", "delete", "delete", "right", "delete")
        assert len(listener.python_pieces) == 1
        assert listener.python_pieces[0].value is target.value
        await pilot.press("ctrl+d")
        assert app.is_running and len(listener.python_pieces) == 1
        await pilot.resize_terminal(12, 8)
        assert editor.render_line(0).cell_length == 12


@pytest.mark.asyncio
async def test_python_click_refusal_documentation_and_continuation(tmp_path):
    listener = make_listener(tmp_path)
    listener.submit("2")
    target = next(p for p in listener.history.presentations if p.type is listener.types.value)
    app = PbuiApp(listener)
    async with app.run_test(size=(80, 9)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        editor = screen.command_input
        interval = target.intervals[0]
        x, y = interval.start_column, interval.physical_row - int(surface.scroll_y)
        listener.set_input_text("f()")
        editor.cursor_position = 2
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, x, y))
        screen.synchronize()
        assert screen.documentation_line.sentence == "Click to insert this value into the expression."
        before = listener.history.rows
        surface.on_click(_mouse_event(events.Click, surface, x, y, button=1, chain=2))
        assert listener.python_pieces == ("f()",)
        listener.set_input_text('"abc"')
        editor.cursor_position = 2
        screen.synchronize()
        assert screen.documentation_line.sentence == (
            "This value would be literal text here; move the cursor outside the string or comment."
        )
        surface.on_click(_mouse_event(events.Click, surface, x, y, button=1))
        assert listener.python_pieces == ('"abc"',) and listener.history.rows == before
        listener.set_input_text("foo")
        editor.cursor_position = 1
        screen.synchronize()
        assert screen.documentation_line.sentence == (
            "Move the cursor to a Python expression position to insert this value."
        )
        surface.on_click(_mouse_event(events.Click, surface, x, y, button=1))
        assert listener.python_pieces == ("foo",) and listener.history.rows == before
        listener.set_input_text("f()")
        editor.cursor_position = 2
        screen.synchronize()
        surface.on_click(_mouse_event(events.Click, surface, x, y, button=1))
        assert listener.python_pieces[1].value is target.value
        await pilot.press("home", "colon")
        assert listener.input_mode == "python"
        assert editor.display_text.endswith(":f(⟨int 2⟩)")
        await pilot.press("ctrl+g")
        listener.set_input_text("if True:")
        editor.cursor_position = len(listener.input_text)
        await pilot.press("enter")
        assert editor.prompt == "...> "
        assert "if True:" not in editor.display_text
        listener.set_input_text("    10 + ")
        editor.cursor_position = len(listener.input_text)
        screen.synchronize()
        surface.on_click(_mouse_event(events.Click, surface, x, y, button=1))
        assert listener.python_pieces[-1].value is target.value
        await pilot.press("enter", "enter")
        assert listener.history.presentations[-1].value == 12
        assert listener.pending_python_pieces == ()


@pytest.mark.asyncio
async def test_python_menu_narrow_suspends_and_restores_continuation(tmp_path):
    (tmp_path / "file").write_text("x")
    listener = make_listener(tmp_path)
    listener.submit(":ls")
    header = next(p for p in listener.history.presentations if p.type is listener.types.directory_listing)
    listener.submit("2")
    target = next(p for p in listener.history.presentations if p.type is listener.types.value)
    app = PbuiApp(listener)
    async with app.run_test(size=(90, 12)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        editor = screen.command_input
        listener.set_input_text("if True:")
        editor.cursor_position = len(listener.input_text)
        await pilot.press("enter")
        listener.set_input_text("    10 + ")
        editor.cursor_position = len(listener.input_text)
        screen.synchronize()
        interval = target.intervals[0]
        surface.on_click(_mouse_event(events.Click, surface, interval.start_column, interval.physical_row - int(surface.scroll_y), button=1))
        await pilot.press("left")
        saved = listener.capture_python_input()
        header_interval = header.intervals[0]
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, header_interval.start_column, header_interval.physical_row - int(surface.scroll_y)))
        await pilot.press("ctrl+o")
        assert screen.action_menu.is_open
        await pilot.pause()
        _click_menu_label(screen.action_menu, "sort size")
        assert listener.pending_python_pieces == saved[0]
        assert listener.python_pieces == saved[1].pieces
        assert listener.python_cursor == saved[1].cursor
        await pilot.pause()
        header_interval = header.intervals[0]
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, header_interval.start_column, header_interval.physical_row - int(surface.scroll_y)))
        await pilot.press("ctrl+o")
        assert screen.action_menu.is_open
        await pilot.press("ctrl+d")
        assert not screen.action_menu.is_open
        assert listener.capture_python_input() == saved
        surface.on_click(_mouse_event(events.Click, surface, header_interval.start_column, header_interval.physical_row - int(surface.scroll_y), button=3))
        assert screen.action_menu.is_open
        await pilot.pause()
        _click_menu_label(screen.action_menu, "narrow")
        assert listener.pending_substring_listing is not None
        assert editor.prompt == f"pbui:{tmp_path}> "
        assert editor.display_text.endswith("narrow ")
        await pilot.press("enter", "ctrl+d")
        assert listener.pending_substring_listing is not None and app.is_running
        surface.on_click(_mouse_event(events.Click, surface, interval.start_column, interval.physical_row - int(surface.scroll_y), button=1))
        assert listener.pending_substring_listing is not None
        assert listener.python_pieces == ()
        await pilot.press("f", "i", "l", "e", "enter")
        assert listener.pending_substring_listing is None
        assert listener.pending_python_pieces == saved[0]
        assert listener.python_pieces == saved[1].pieces
        assert listener.python_cursor == saved[1].cursor
        assert editor.has_focus and editor.prompt == "...> "
        for key in ("ctrl+g", "escape"):
            screen.open_menu(header)
            assert screen.action_menu.is_open
            await pilot.pause()
            _click_menu_label(screen.action_menu, "narrow")
            assert listener.pending_substring_listing is not None
            await pilot.press(key)
            assert listener.pending_substring_listing is None
            assert listener.pending_python_pieces == saved[0]
            assert listener.python_pieces == saved[1].pieces
            assert listener.python_cursor == saved[1].cursor
        await pilot.press("ctrl+d")
        assert listener.pending_python_pieces == () and app.is_running
