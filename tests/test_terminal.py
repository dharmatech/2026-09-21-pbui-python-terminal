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
from pbui.http import GetResult, JsonArray, JsonObject
from pbui.repl import ValueTranslator
from pbui.transcript import CommandInput as SavedCommandInput, MenuActionInput, PythonInput
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
    row_indents,
    stored_row_text,
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


def make_listener(tmp_path, *, history_max_rows=500, **kwargs):
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
        **kwargs,
    )


def first_listing(listener):
    return next(row.listing_owner for row in listener.history.rows if row.listing_owner)


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
    assert logical_row is not None
    indent = 2 if surface.current_layout.width >= 3 and row_indents(
        surface._logical_rows[logical_row]
    ) else 0
    remaining = logical_column
    for physical_row, rendered_row in enumerate(surface.current_layout.rows):
        if rendered_row.logical_row != logical_row:
            continue
        content_width = rendered_row.display_width - indent
        if remaining < content_width:
            return (
                remaining + indent,
                physical_row - int(surface.scroll_y),
            )
        remaining -= content_width
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
    physical = int(surface.scroll_y)
    logical = surface.current_layout.rows[physical].logical_row
    if logical is None:
        logical = surface.current_layout.rows[physical + 1].logical_row
    assert logical is not None
    return surface._logical_rows[logical]


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
        "sympy>=1.14.0",
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


def _menu_cell(menu, index, *, x=1):
    geometry = menu.geometry
    assert geometry is not None
    surface = menu.screen.history_surface
    region = surface.scrollable_content_region
    return surface, geometry.rect.x - region.x + x, geometry.rect.y - region.y + index + 1


def _click_menu_index(menu, index, *, x=1, button=1, chain=1):
    surface, cell_x, cell_y = _menu_cell(menu, index, x=x)
    surface.on_click(_mouse_event(
        events.Click, surface, cell_x, cell_y, button=button, chain=chain
    ))


def _move_menu_index(menu, index, *, x=1):
    surface, cell_x, cell_y = _menu_cell(menu, index, x=x)
    surface.on_mouse_move(_mouse_event(events.MouseMove, surface, cell_x, cell_y))


def _click_menu_label(menu, label):
    _click_menu_index(menu, menu.labels.index(label))


def _outside_menu_cell(menu):
    geometry = menu.geometry
    assert geometry is not None
    surface = menu.screen.history_surface
    region = surface.scrollable_content_region
    for x, y in ((0, 0), (region.width - 1, 0), (0, region.height - 1),
                 (region.width - 1, region.height - 1)):
        if not geometry.rect.contains(region.x + x, region.y + y):
            return surface, x, y
    raise AssertionError("no history cell outside the menu")


def _open_menu_for(screen, target):
    surface = screen.history_surface
    surface.synchronize()
    if (
        target is not None
        and target.intervals
        and screen.listener.pending_request is None
        and screen.listener.pending_substring_listing is None
        and not screen._visible_cells(target)
    ):
        surface.scroll_to_row(target.intervals[0].physical_row)
    screen.open_menu(target)


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
        assert command.region.height == 2
        assert history.region.height == 9
        assert history.current_layout.rows == ()
        assert history.virtual_size.height == 0
        assert documentation.sentence == "READY"
        assert documentation.render().plain == "READY"


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
            logical_row: stored_row_text(row)
            for logical_row, row in enumerate(listener.history.rows)
        }
        assert all(
            rendered.text.startswith("  ")
            for rendered in surface.current_layout.rows
            if rendered.logical_row is not None and rendered.logical_row > 0
        )
        assert logical_text[0] == "› : ps"
        assert logical_text[1] == (
            f"{'pid':>10}  {'state':<10}  {'user':<16}  {'command':<48}"
        )
        listing = first_listing(listener)
        displayed_users = {
            member.reference.pid: member.displayed_user for member in listing.members
        }
        for logical_row, record in enumerate(
            sorted(records.values(), key=lambda item: item.pid), start=2
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
    listing = first_listing(listener)
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
    directory_listing = first_listing(listener)
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
    process_listing = first_listing(process_listener)
    presentation = process_listing.member_presentations[0]
    current_layout = layout(process_listener.history, 120)
    physical_row = presentation.intervals[0].physical_row
    row = current_layout.rows[physical_row]
    rich_row = terminal_module.build_history_row_text(
        process_listener, current_layout, physical_row
    )
    console = Console()
    assert row.text.endswith("…")
    assert len(row.text) == 92
    for column in (0, 1):
        assert current_layout.hit_test(column, physical_row) is None
    for column in (2, 11, 12, 13, 23, 24, 25, 41, 42, 43, 44, 91):
        assert current_layout.hit_test(column, physical_row) is presentation
    for index in range(len(row.text)):
        style = rich_row.get_style_at_offset(console, index)
        if index < 2:
            assert style.color is None or style.color.name == "default"
        else:
            assert style.color is not None
            assert style.color.triplet.hex == "#5f87d7"


def test_documentation_formatter_covers_normative_table(tmp_path):
    listener = make_listener(tmp_path)
    item = domain_presentations(listener)
    assert format_documentation(listener, None) == "READY"
    assert format_documentation(listener, item["File"]) == (
        "FILE “a name” • Left: show • Right: menu"
    )
    assert format_documentation(listener, item["Directory"]) == (
        "DIRECTORY “a directory” • Left: show • Right: menu"
    )
    assert format_documentation(listener, item["Process"]) == (
        "PROCESS 42 • Left: show • Right: menu"
    )
    assert format_documentation(listener, item["Text"]) == (
        "TEXT • Left: no action • Right: no menu"
    )
    assert format_documentation(listener, item["Error"]) == (
        "ERROR • Left: no action • Right: no menu"
    )

    cases = {
        "rm": [
            "SELECTING FILE FOR rm • Point at highlighted File and click • Esc: cancel • Ctrl-G: cancel",
            "SELECTING FILE FOR rm — FILE “a name” • Left: use and run command • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING FILE FOR rm — DIRECTORY “a directory” • Left: cannot use Directory; File required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING FILE FOR rm — PROCESS 42 • Left: cannot use Process; File required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING FILE FOR rm — TEXT • Left: cannot use Text; File required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING FILE FOR rm — ERROR • Left: cannot use Error; File required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
        ],
        "cd": [
            "SELECTING DIRECTORY FOR cd • Point at highlighted Directory and click • Esc: cancel • Ctrl-G: cancel",
            "SELECTING DIRECTORY FOR cd — FILE “a name” • Left: cannot use File; Directory required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING DIRECTORY FOR cd — DIRECTORY “a directory” • Left: use and run command • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING DIRECTORY FOR cd — PROCESS 42 • Left: cannot use Process; Directory required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING DIRECTORY FOR cd — TEXT • Left: cannot use Text; Directory required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING DIRECTORY FOR cd — ERROR • Left: cannot use Error; Directory required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
        ],
        "kill": [
            "SELECTING PROCESS FOR kill • Point at highlighted Process and click • Esc: cancel • Ctrl-G: cancel",
            "SELECTING PROCESS FOR kill — FILE “a name” • Left: cannot use File; Process required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING PROCESS FOR kill — DIRECTORY “a directory” • Left: cannot use Directory; Process required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING PROCESS FOR kill — PROCESS 42 • Left: use and run command • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING PROCESS FOR kill — TEXT • Left: cannot use Text; Process required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING PROCESS FOR kill — ERROR • Left: cannot use Error; Process required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
        ],
        "show": [
            "SELECTING FILE/DIRECTORY/PROCESS FOR show • Point at highlighted File, Directory, or Process and click • Esc: cancel • Ctrl-G: cancel",
            "SELECTING FILE/DIRECTORY/PROCESS FOR show — FILE “a name” • Left: use and run command • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING FILE/DIRECTORY/PROCESS FOR show — DIRECTORY “a directory” • Left: use and run command • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING FILE/DIRECTORY/PROCESS FOR show — PROCESS 42 • Left: use and run command • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING FILE/DIRECTORY/PROCESS FOR show — TEXT • Left: cannot use Text; File, Directory, or Process required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING FILE/DIRECTORY/PROCESS FOR show — ERROR • Left: cannot use Error; File, Directory, or Process required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
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
        "NO TARGET"
    )


def test_listing_header_documentation_and_all_accept_refusals(tmp_path):
    (tmp_path / "file").write_text("payload")
    listener = make_listener(tmp_path)
    listener.submit(": ls")
    listener.submit(": ps")
    directory_listing = first_listing(listener)
    process_listing = next(
        row.listing_owner
        for row in listener.history.rows
        if row.listing_owner is not None and row.listing_owner is not directory_listing
    )
    headers = (
        directory_listing.header_presentation,
        process_listing.header_presentation,
    )
    assert format_documentation(listener, headers[0]) == (
        "DIRECTORY LISTING • Left: no action • Right: menu"
    )
    assert format_documentation(listener, headers[1]) == (
        "PROCESS LISTING • Left: no action • Right: menu"
    )

    expected = {
        "rm": (
            "SELECTING FILE FOR rm — DIRECTORY LISTING • Left: cannot use DirectoryListing; File required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING FILE FOR rm — PROCESS LISTING • Left: cannot use ProcessListing; File required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
        ),
        "cd": (
            "SELECTING DIRECTORY FOR cd — DIRECTORY LISTING • Left: cannot use DirectoryListing; Directory required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING DIRECTORY FOR cd — PROCESS LISTING • Left: cannot use ProcessListing; Directory required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
        ),
        "kill": (
            "SELECTING PROCESS FOR kill — DIRECTORY LISTING • Left: cannot use DirectoryListing; Process required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING PROCESS FOR kill — PROCESS LISTING • Left: cannot use ProcessListing; Process required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
        ),
        "show": (
            "SELECTING FILE/DIRECTORY/PROCESS FOR show — DIRECTORY LISTING • Left: cannot use DirectoryListing; File, Directory, or Process required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
            "SELECTING FILE/DIRECTORY/PROCESS FOR show — PROCESS LISTING • Left: cannot use ProcessListing; File, Directory, or Process required • Right: no menu • Esc: cancel • Ctrl-G: cancel",
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
    listing = first_listing(listener)
    by_pid = {
        presentation.value.pid: presentation
        for presentation in listing.member_presentations
    }
    ordinary_10 = "PROCESS 10 • Left: show • Right: menu"
    ordinary_11 = "PROCESS 11 • Left: show • Right: menu"
    ordinary_12 = "PROCESS 12 • Left: show • Right: menu"
    assert format_documentation(listener, by_pid[10], 42) == ordinary_10
    assert format_documentation(listener, by_pid[11], 41) == ordinary_11
    assert format_documentation(listener, by_pid[11], 42) == (
        "PROCESS 11 (command truncated) • Left: show full command • Right: menu"
    )
    assert format_documentation(listener, by_pid[11], 89) == (
        "PROCESS 11 (command truncated) • Left: show full command • Right: menu"
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
    listing = first_listing(listener)
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
        assert documentation.sentence == "PROCESS 21 • Left: show • Right: menu"
        assert surface.pointer_logical_column == 41
        assert built_rows

        built_rows.clear()
        x, y = _offset_for_logical_column(surface, long_process, 42)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, x, y))
        assert documentation.sentence == (
            "PROCESS 21 (command truncated) • Left: show full command • Right: menu"
        )
        assert surface.pointer_logical_column == 42
        assert built_rows == []

        x, y = _offset_for_logical_column(surface, long_process, 89)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, x, y))
        assert documentation.sentence == (
            "PROCESS 21 (command truncated) • Left: show full command • Right: menu"
        )
        assert surface.pointer_logical_column == 89
        assert built_rows == []

        x, y = _offset_for_logical_column(surface, long_process, 41)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, x, y))
        assert documentation.sentence == "PROCESS 21 • Left: show • Right: menu"
        assert built_rows == []

        long_start = long_process.intervals[0].physical_row
        short_start = short_process.intervals[0].physical_row
        surface.scroll_to_row(short_start - long_start)
        assert documentation.sentence != (
            "PROCESS 21 (command truncated) • Left: show full command • Right: menu"
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
    assert command.display_text == f"PYTHON │ pbui:{tmp_path}> show"
    command.cursor_position = 2
    assert command.cursor_position == 2
    command.cursor_position = 100
    assert command.cursor_position == 4

    original = FileRef(str(tmp_path / "[literal] name"))
    listener.state.chip = Chip(listener.types.file, original, "[literal] name")
    listener.set_input_text("show")
    assert command.display_text == (
        f"PYTHON │ pbui:{tmp_path}> show ⟨File: [literal] name⟩"
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
    listing = first_listing(listener)
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
        assert listener.history.revision == revision + 2
        assert len(listener.history.rows) == len(outside) + 3
        assert _top_logical_row(surface) is anchor
        assert tuple(row for row in listener.history.rows if row in outside) == outside

        assert listener.apply_listing_view(listing, "widen")
        surface.synchronize()
        assert len(listener.history.rows) == len(outside) + 11
        assert _top_logical_row(surface) is anchor
        assert all(
            current is original
            for current, original in zip(
                (row for row in listener.history.rows if row in outside),
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
    listing = first_listing(listener)
    _append_plain_rows(listener, 10)
    member = listing.member_presentations[0]
    app = PbuiApp(listener)

    async with app.run_test(size=(34, 8)):
        surface = app.screen.history_surface
        header = next(row for row in listener.history.rows
                      if row.presentations == (listing.header_presentation,))
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
    listing = first_listing(listener)
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
    listener.submit(": ps")
    listing = listener.history.rows[4].listing_owner
    assert listener.apply_listing_view(listing, "narrow", "worker-1")
    _append_plain_rows(listener, 3)
    oldest = listener.history.rows[0]
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
    listing = first_listing(listener)
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
    listing = first_listing(listener)
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
        assert app.screen.command_input.region.height == 2
        assert app.screen.history_surface.region.height == 6


@pytest.mark.asyncio
async def test_explanatory_row_anchor_and_wrapped_offset_clamp(tmp_path):
    listener = _process_listener(
        tmp_path,
        [InspectedProcess(1, 1000, "running", "worker")],
    )
    listener.submit(": ps")
    listing = first_listing(listener)
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
    listing = first_listing(listener)
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
            assert listener.history.revision == revision + 2
            assert member in listener.history.presentations
            assert int(surface.scroll_y) == int(surface.max_scroll_y)

        revision = listener.history.revision
        await pilot.press(*_key_names(":narrow"), "enter")
        assert listener.pending_substring_listing is listing
        assert listener.history.revision == revision
        assert member in listener.history.presentations
        await pilot.press(*_key_names("worker-1"), "enter")
        assert listener.pending_substring_listing is None
        assert listener.history.revision == revision + 2
        assert member in listener.history.presentations
        assert int(surface.scroll_y) == int(surface.max_scroll_y)

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
    listing = first_listing(listener)
    _append_plain_rows(listener, 14)
    app = PbuiApp(listener)

    async with app.run_test(size=(34, 12)) as pilot:
        surface = app.screen.history_surface
        documentation = app.screen.documentation_line
        header = next(row for row in listener.history.rows
                      if row.presentations == (listing.header_presentation,))
        surface.scroll_to_row(_first_physical_row(surface, header))
        first_member = next(row for row in listener.history.rows if row.presentations == (listing.member_presentations[0],))
        y = _first_physical_row(surface, first_member) - int(surface.scroll_y)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, 2, y))
        assert documentation.sentence == "PROCESS 1 • Left: show • Right: menu"

        revision = listener.history.revision
        assert listener.apply_listing_view(listing, "sort", "state")
        surface.synchronize()
        assert listener.history.revision == revision + 2
        assert surface.hovered_presentation is listing.member_presentations[1]
        assert documentation.sentence == "PROCESS 2 • Left: show • Right: menu"

        assert listener.apply_listing_view(listing, "narrow", "worker-1")
        surface.synchronize()
        assert surface.hovered_presentation is listing.member_presentations[0]
        assert documentation.sentence == "PROCESS 1 • Left: show • Right: menu"

        await pilot.resize_terminal(26, 12)
        assert surface.hovered_presentation is surface.presentation_at_content_offset(2, y)
        assert documentation.sentence == format_documentation(
            listener, surface.hovered_presentation, surface.pointer_logical_column
        )

        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, 0, 8))
        assert surface.pointer_offset == Offset(0, 8)
        await pilot.resize_terminal(26, 6)
        assert surface.pointer_offset is None
        assert surface.hovered_presentation is None
        assert documentation.sentence == "READY"
        assert listener.history.revision == revision + 4


@pytest.mark.asyncio
async def test_recall_keys_keep_editor_caret_and_history_viewport(tmp_path):
    (tmp_path / "sample").write_text("data")
    listener = make_listener(tmp_path)
    _append_plain_rows(listener, 30, prefix="seed")
    app = PbuiApp(listener)

    async with app.run_test(size=(120, 9)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        editor = screen.command_input
        await pilot.press(*_key_names(":ls"), "enter")
        await pilot.press(*_key_names("1+2"), "enter")
        saved_command = next(
            item for item in listener.history.presentations
            if item.type is listener.types.command_input
        )
        assert len(listener.recall_entries) == 2
        await pilot.press(*_key_names("draft"), "left", "left")
        assert editor.cursor_position == 3
        surface.scroll_to_row(5)
        await pilot.pause()
        scroll = int(surface.scroll_y)
        anchor = _top_logical_row(surface)
        input_region = editor.region
        assert scroll < saved_command.intervals[0].physical_row

        async def check(key, expected, mode, cursor):
            await pilot.press(key)
            row = editor.render_line(0).text
            assert row.startswith(f"{mode} │ ")
            assert expected in row
            assert listener.input_text == expected
            assert editor.cursor_position == cursor
            cursor_index = editor._cursor_index(editor.display_text)
            assert any(
                span.style.reverse and span.start == cursor_index
                for span in editor.renderable.spans
            )
            assert editor.has_focus
            assert editor.region == input_region
            assert int(surface.scroll_y) == scroll
            assert _top_logical_row(surface) is anchor

        await check("up", "1+2", "PYTHON", 3)
        await check("up", ":ls", "COMMAND", 3)
        await check("down", "1+2", "PYTHON", 3)
        await check("down", "draft", "PYTHON", 3)

        surface.post_message(_mouse_event(events.MouseScrollDown, surface, 0, 0))
        await pilot.pause()
        assert int(surface.scroll_y) == scroll + 3
        assert editor.region == input_region
        assert "draft" in editor.render_line(0).text
        await pilot.press("up", "down")
        assert int(surface.scroll_y) == scroll + 3
        assert editor.cursor_position == 3

        await pilot.press("ctrl+g", *_key_names(":draft"), "left", "left")
        assert listener.command_cursor == 4
        await pilot.press("up", "down")
        assert listener.input_text == ":draft"
        assert listener.command_cursor == 4
        assert editor.cursor_position == 4
        assert ":draft" in editor.render_line(0).text
        assert int(surface.scroll_y) == scroll + 3

        _open_menu_for(screen, saved_command)
        await pilot.pause()
        assert screen.action_menu.is_open
        menu_scroll = int(surface.scroll_y)
        menu_row = editor.render_line(0).text
        await pilot.press("up", "down")
        assert screen.action_menu.is_open
        assert editor.render_line(0).text == menu_row
        assert listener.input_text == ":draft"
        assert editor.cursor_position == 4
        assert int(surface.scroll_y) == menu_scroll


@pytest.mark.asyncio
async def test_completion_list_overlay_keys_click_and_menu(tmp_path):
    (tmp_path / "sample").write_text("data")
    listener = make_listener(tmp_path)
    _append_plain_rows(listener, 20, prefix="before")
    listener.submit(":ls")
    listing = first_listing(listener)
    file = next(
        item for item in listing.member_presentations
        if item.presentation_type is listener.types.file
    )
    _append_plain_rows(listener, 20, prefix="after")
    app = PbuiApp(listener)

    async with app.run_test(size=(100, 14)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        editor = screen.command_input
        documentation = screen.documentation_line
        height = surface.scrollable_content_region.height
        assert height >= 8
        interval = file.intervals[0]
        surface.scroll_to_row(interval.physical_row - height + 1)
        await pilot.pause()
        assert surface.presentation_at_content_offset(
            interval.start_column, height - 1
        ) is file
        scroll = int(surface.scroll_y)
        anchor = _top_logical_row(surface)
        rows = listener.history.rows
        revision = listener.history.revision
        presentations = listener.history.presentations
        sentence = documentation.sentence

        await pilot.press(":", "tab")
        assert screen.completion_candidates == tuple(sorted(listener.command_names))
        assert len(screen.completion_candidates) > 8
        assert screen.completion_highlight == 0
        assert screen.completion_window == 0
        assert [screen.completion_row(y)[0] for y in range(height - 8, height)] == list(
            screen.completion_candidates[:8]
        )
        assert all(screen.completion_row(y) is None for y in range(height - 8))
        assert surface.render_line(height - 8).text.startswith(
            screen.completion_candidates[0]
        )
        assert any(segment.style.reverse for segment in surface.render_line(height - 8))
        assert documentation.sentence == sentence
        assert int(surface.scroll_y) == scroll
        assert _top_logical_row(surface) is anchor
        assert listener.history.rows == rows
        assert listener.history.presentations == presentations

        await pilot.press("up", "down")
        assert screen.completion_highlight == 1
        assert listener.recall_position is None
        await pilot.press(*("down",) * 8)
        assert screen.completion_highlight == 9
        assert screen.completion_window == 2
        assert screen.completion_row(height - 1) == (
            screen.completion_candidates[9], True
        )
        await pilot.press("tab", "tab", "tab")
        assert screen.completion_highlight == 0
        assert screen.completion_window == 0
        await pilot.press(*("down",) * 9)
        assert screen.completion_highlight == 9
        chosen = screen.completion_candidates[9]
        await pilot.press("enter")
        assert not screen.completion_is_open
        assert listener.input_text == ":" + chosen
        assert editor.cursor_position == len(listener.input_text)
        assert listener.history.revision == revision
        assert listener.history.rows == rows
        assert int(surface.scroll_y) == scroll
        assert surface.render_line(height - 1).text != chosen

        await pilot.press("ctrl+g", ":", "tab", "escape")
        assert not screen.completion_is_open
        assert listener.input_text == ":"
        await pilot.press("up")
        assert listener.input_text == ":ls"
        assert listener.recall_position == 0
        await pilot.press("ctrl+g", ":", "tab", "s", "o")
        assert screen.completion_is_open
        assert screen.completion_candidates == ("sort",)
        assert listener.input_text == ":so"
        await pilot.press("tab")
        assert not screen.completion_is_open
        assert listener.input_text == ":sort"
        await pilot.press("ctrl+g")

        screen.open_menu(file)
        assert screen.action_menu.is_open
        await pilot.press("tab")
        assert screen.action_menu.is_open
        assert not screen.completion_is_open
        screen.close_menu()

        await pilot.press(":", "tab")
        assert screen.completion_is_open
        await pilot.resize_terminal(40, 6)
        short_height = surface.scrollable_content_region.height
        assert short_height == 3
        assert sum(
            screen.completion_row(y) is not None for y in range(short_height)
        ) == short_height
        assert documentation.region.y == surface.region.bottom
        assert editor.region.y == documentation.region.bottom

        await pilot.resize_terminal(100, 14)
        height = surface.scrollable_content_region.height
        assert screen.completion_row(height - 1) is not None
        surface.scroll_to_row(file.intervals[0].physical_row - height + 1)
        await pilot.pause()
        before_wheel = int(surface.scroll_y)
        surface.post_message(_mouse_event(
            events.MouseScrollDown, surface, 0, 0
        ))
        await pilot.pause()
        assert int(surface.scroll_y) == before_wheel + 3
        assert screen.completion_row(height - 1) is not None
        surface.scroll_to_row(file.intervals[0].physical_row - height + 1)
        await pilot.pause()
        scroll = int(surface.scroll_y)
        interval = file.intervals[0]
        assert surface.presentation_at_content_offset(
            interval.start_column, height - 1
        ) is file
        assert listener.history.presentations == presentations
        surface.on_click(_mouse_event(
            events.Click, surface, interval.start_column, height - 1, button=1
        ))
        assert not screen.completion_is_open
        assert listener.input_text == ":"
        assert listener.history.revision == revision
        assert int(surface.scroll_y) == scroll
        surface.on_click(_mouse_event(
            events.Click, surface, interval.start_column, height - 1, button=1
        ))
        assert listener.history.revision > revision


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
async def test_paste_is_one_row_and_tab_keeps_input_focus(tmp_path):
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
        assert command.has_focus
        assert not app.screen.completion_is_open
        command.post_message(events.Key("unknown", "\ud800"))
        await pilot.pause()
        assert listener.input_text == before


@pytest.mark.asyncio
async def test_visible_substring_accept_editor_submission_and_cancellation(tmp_path):
    target = tmp_path / "target-file"
    target.write_text("payload")
    listener = make_listener(tmp_path)
    listener.submit(": ls")
    listing = first_listing(listener)
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

        prefix = f"SELECT TEXT FOR narrow │ pbui:{tmp_path}> narrow "
        assert listener.pending_substring_listing is listing
        assert listener.input_text == ""
        assert listener.chip is None
        assert command.display_text == prefix
        assert command.cursor_position == 0
        assert command._cursor_index(command.display_text) == len(prefix)
        assert documentation.sentence == (
            "SELECTING TEXT FOR narrow • Type substring; Enter: narrow listing • Esc: cancel • Ctrl-G: cancel"
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
        assert documentation.sentence.startswith("SELECTING TEXT FOR narrow")

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
        assert listener.history.revision == revision + 2
        assert command.display_text == f"PYTHON │ pbui:{tmp_path}> "
        assert not documentation.sentence.startswith("SELECTING TEXT FOR narrow")

        post_submit_revision = listener.history.revision
        await pilot.press(*_key_names(":narrow"), "enter", "q", "escape")
        assert listener.pending_substring_listing is None
        assert listener.input_text == ""
        assert listener.history.revision == post_submit_revision
        assert command.display_text == f"PYTHON │ pbui:{tmp_path}> "

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
            "rm": "SELECTING FILE FOR rm",
            "cd": "SELECTING DIRECTORY FOR cd",
            "kill": "SELECTING PROCESS FOR kill",
            "show": "SELECTING FILE/DIRECTORY/PROCESS FOR show",
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
        assert listener.history.revision == revision + 1
        assert int(surface.scroll_y) == int(surface.max_scroll_y)
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
        assert surface.presentation_at_content_offset(0, y) is None
        assert surface.presentation_at_content_offset(1, y) is None
        literal_x = surface.current_layout.rows[interval.physical_row].display_width + 1
        assert surface.presentation_at_content_offset(literal_x, y) is None
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, literal_x, y))
        assert app.screen.documentation_line.sentence == "READY"
        assert app.screen.documentation_line.render().plain == "READY"

        assert app.screen.command_input.has_focus
        assert not surface.can_focus
        await pilot.click(surface, offset=(literal_x, y))
        assert app.screen.command_input.has_focus

        surface.on_mouse_move(move)
        assert surface.hovered_presentation is target_presentation
        assert app.screen.documentation_line.sentence == (
            "FILE “file with space” • Left: show • Right: menu"
        )
        surface.on_leave(events.Leave(surface))
        assert surface.hovered_presentation is None
        assert app.screen.documentation_line.sentence == "READY"

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
        outside_surface, outside_x, outside_y = _outside_menu_cell(app.screen.action_menu)
        outside_surface.on_click(
            _mouse_event(events.Click, outside_surface, outside_x, outside_y, button=1, chain=1)
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

    async with app.run_test(size=(100, 25)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        menu = screen.action_menu
        original_registry = tuple(listener.registry)
        original_history = listener.history.rows
        targets = (
            (listener.types.file, ("show", "rm")),
            (listener.types.directory, ("show", "cd", "ls")),
            (listener.types.process, ("show", "kill")),
            (listener.types.directory_listing, terminal_module._DIRECTORY_ACTIONS),
            (listener.types.process_listing, terminal_module._PROCESS_ACTIONS),
        )
        for presentation_type, labels in targets:
            target = next(
                item for item in listener.history.presentations
                if item.presentation_type is presentation_type
            )
            screen._pointer_screen = None
            _open_menu_for(screen, target)
            await pilot.pause()
            assert menu.is_open
            assert menu.labels == labels
            assert len(menu.item_presentations) == len(labels)
            assert all(item.presentation_type is menu.menu_type for item in menu.item_presentations)
            assert all(item.value.target is target for item in menu.item_presentations)
            assert all(item.value.label == label for item, label in zip(menu.item_presentations, labels))
            assert screen.documentation_line.sentence == "NO TARGET • Click an item • Esc: close menu • Ctrl-G: close menu"
            rect = menu.geometry.rect
            history = surface.scrollable_content_region
            assert history.x <= rect.x and rect.x + rect.width <= history.x + history.width
            assert history.y <= rect.y and rect.y + rect.height <= history.y + history.height
            assert (rect.width, rect.height) == (
                max(map(display_width, labels)) + 4, len(labels) + 2
            )
            assert menu.presentation_at_content_offset(0, 1) is None
            assert menu.presentation_at_content_offset(1, 1) is menu.item_presentations[0]
            assert menu.presentation_at_content_offset(rect.width - 2, 1) is menu.item_presentations[0]
            assert menu.presentation_at_content_offset(rect.width - 1, 1) is None
            _move_menu_index(menu, 0)
            process_pid = next(
                item.value.pid for item in listener.history.presentations
                if item.presentation_type is listener.types.process
            )
            expected_documentation = {
                listener.types.file: f"MENU “{labels[0]}” ON FILE “file name” • Left: run • Right: no menu",
                listener.types.directory: f"MENU “{labels[0]}” ON DIRECTORY “directory” • Left: run • Right: no menu",
                listener.types.process: f"MENU “{labels[0]}” ON PROCESS {process_pid} • Left: run • Right: no menu",
                listener.types.directory_listing: f"MENU “{labels[0]}” ON DIRECTORY LISTING • Left: apply • Right: no menu",
                listener.types.process_listing: f"MENU “{labels[0]}” ON PROCESS LISTING • Left: apply • Right: no menu",
            }[presentation_type]
            assert screen.documentation_line.sentence == expected_documentation
            assert set(surface.current_layout.presentations) == set(listener.history.presentations)
            screen.close_menu()
            await pilot.pause()
            assert menu.geometry is None
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
        assert screen.documentation_line.sentence.startswith("NO TARGET • Click an item")
        surface.on_leave(events.Leave(surface))
        assert menu.is_open
        _move_menu_index(menu, 0)
        assert screen.documentation_line.sentence == "MENU “show” ON FILE “file” • Left: run • Right: no menu"
        outside_surface, outside_x, outside_y = _outside_menu_cell(menu)
        outside_surface.on_mouse_move(_mouse_event(
            events.MouseMove, outside_surface, outside_x, outside_y
        ))
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

        for target in (
            None,
            next(item for item in listener.history.presentations if item.presentation_type is listener.types.text),
            next(item for item in listener.history.presentations if item.presentation_type is listener.types.error),
            next(item for item in listener.history.presentations if item.presentation_type is unrelated_type),
        ):
            _open_menu_for(screen, target)
            assert not menu.is_open
            assert screen.documentation_line.override_sentence is None
            screen.synchronize()
            assert screen.documentation_line.override_sentence is None
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
            "TEXT • Left: move cursor to Python expression position to insert • Right: no menu"
        )
        _open_menu_for(screen, None)
        assert screen.documentation_line.override_sentence is None
        listener.set_input_text("changed")
        screen.synchronize()
        assert screen.documentation_line.sentence == (
            "TEXT • Left: move cursor to Python expression position to insert • Right: no menu"
        )

        listener.submit(": rm")
        screen.synchronize()
        pending = listener.pending_request
        documentation = screen.documentation_line.sentence
        _open_menu_for(screen, file_target)
        await pilot.press("ctrl+o")
        surface.on_click(_mouse_event(events.Click, surface, x, y, button=3))
        assert not menu.is_open
        assert listener.pending_request is pending
        assert screen.documentation_line.sentence == (
            'SELECTING FILE FOR rm — FILE “file” • Left: use and run command • Right: no menu • Esc: cancel • Ctrl-G: cancel'
        )
        listener.cancel()
        listener.submit(": narrow")
        screen.synchronize()
        pending_listing = listener.pending_substring_listing
        documentation = screen.documentation_line.sentence
        _open_menu_for(screen, file_target)
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
    directory_listing = first_listing(listener)
    listener.submit(": ps")
    process_listing = next(
        row.listing_owner for row in listener.history.rows
        if row.listing_owner is not None and row.listing_owner is not directory_listing
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
            _open_menu_for(screen, header)
            await pilot.pause()
            _click_menu_label(menu, label)
            await pilot.pause()
            assert getattr(directory_listing.view, view_field) == expected
            assert process_listing.view.sort_key == "pid"
            assert tuple(row for row in listener.history.rows if row.listing_owner is process_listing) == process_rows
            assert {row.listing_owner for row in listener.history.rows if row.listing_owner is not None} == {
                directory_listing, process_listing
            }
            assert not menu.is_open

        _open_menu_for(screen, header)
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

        _open_menu_for(screen, process_listing.header_presentation)
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
    listing = first_listing(listener)
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
        _open_menu_for(screen, file_target)
        await pilot.pause()
        rows_before = listener.history.rows
        interval = file_target.intervals[0]
        outside_surface, outside_x, outside_y = _outside_menu_cell(menu)
        outside_surface.on_click(_mouse_event(
            events.Click, outside_surface, outside_x, outside_y, button=1,
        ))
        await pilot.pause()
        assert not menu.is_open
        assert listener.history.rows == rows_before
        assert file_path.exists()

        for target, label in (
            (file_target, "show"),
            (directory_target, "show"),
            (process_target, "show"),
        ):
            _open_menu_for(screen, target)
            await pilot.pause()
            revision = listener.history.revision
            _click_menu_label(menu, label)
            await pilot.pause()
            assert listener.history.revision == revision + 2
            assert not menu.is_open

        _open_menu_for(screen, directory_target)
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

        _open_menu_for(screen, directory_target)
        await pilot.pause()
        _click_menu_label(menu, "cd")
        await pilot.pause()
        assert listener.cwd == str(directory)

        _open_menu_for(screen, process_target)
        await pilot.pause()
        _click_menu_label(menu, "kill")
        await pilot.pause()
        assert processes.sent == [(42, signal.SIGTERM)]

        _open_menu_for(screen, file_target)
        await pilot.pause()
        _click_menu_label(menu, "rm")
        await pilot.pause()
        assert not file_path.exists()

        _open_menu_for(screen, process_target)
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

    async with app.run_test(size=(25, 12)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        first = _first_physical_row(surface, member_row)
        assert surface.current_layout.rows[first + 1].logical_row == surface.current_layout.rows[first].logical_row
        surface.scroll_to_row(first + 1)
        assert _top_logical_row(surface) is member_row
        assert int(surface.scroll_y) == first + 1
        hit = surface.presentation_at_content_offset(2, 0)
        assert hit is member
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, 2, 0))
        surface.on_click(_mouse_event(events.Click, surface, 2, 0, button=3))
        await pilot.pause()
        assert screen.action_menu.target is member
        assert _top_logical_row(surface) is member_row
        assert int(surface.scroll_y) == first + 1
        assert surface.hovered_presentation is surface.presentation_at_content_offset(2, 0)
        _move_menu_index(screen.action_menu, 0)
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

        _open_menu_for(screen, listing.header_presentation)
        await pilot.pause()
        _click_menu_label(screen.action_menu, "sort size")
        await pilot.pause()
        assert listing.view.sort_key == "size"
        assert listing.header_presentation in listener.history.presentations
        assert int(surface.scroll_y) == int(surface.max_scroll_y)

        _open_menu_for(screen, member)
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

    async with app.run_test(size=(70, 14)) as pilot:
        screen = app.screen
        _open_menu_for(screen, header)
        await pilot.pause()
        menu = screen.action_menu
        history = screen.history_surface
        assert menu.is_open
        refreshed = []
        original_refresh = history.refresh

        def record_refresh(*regions, **kwargs):
            refreshed.extend(regions)
            return original_refresh(*regions, **kwargs)

        monkeypatch.setattr(history, "refresh", record_refresh)
        monkeypatch.setattr(history, "_build_all_rows", lambda: pytest.fail("menu hover rebuilt history rows"))
        _move_menu_index(menu, 0)
        _move_menu_index(menu, 1)
        expected = {
            menu.geometry.rect.y - history.scrollable_content_region.y + 1,
            menu.geometry.rect.y - history.scrollable_content_region.y + 2,
        }
        assert {region.y for region in refreshed} == expected
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
            assert editor.prompt == f"pbui:{tmp_path} ...> "
            assert screen.documentation_line.sentence == (
                "NO TARGET • Python continuation: enter another line • Esc: discard • Ctrl-G: discard"
                if cancel_key == "ctrl+g" else
                "PYTHON VALUE • Left: move cursor to Python expression position to insert • Right: no menu"
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
            assert screen.documentation_line.sentence == format_documentation(
                listener, screen.history_surface.hovered_presentation,
                screen.history_surface.pointer_logical_column
            )
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
        listener.types.python_input, listener.types.value,
        listener.types.python_input, listener.types.text, listener.types.value,
        listener.types.python_input, listener.types.error,
    ]
    app = PbuiApp(listener)
    async with app.run_test(size=(24, 8)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        assert len(value.intervals) > 1
        surface.scroll_to_row(value.intervals[1].physical_row)
        interval = value.intervals[1]
        y = interval.physical_row - int(surface.scroll_y)
        assert surface.presentation_at_content_offset(2, y) is value
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, 2, y))
        assert screen.documentation_line.sentence == (
            "PYTHON VALUE • Left: show • Right: no menu"
        )
        _open_menu_for(screen, value)
        assert not screen.action_menu.is_open
        assert screen.documentation_line.sentence == format_documentation(
                listener, surface.hovered_presentation, surface.pointer_logical_column
            )
        screen.synchronize()
        listener.set_input_text("")
        screen.synchronize()
        surface.on_click(_mouse_event(events.Click, surface, 2, y, button=1))
        assert listener.input_text == ""
        assert listener.history.presentations[-1].type is listener.types.text
        assert listener.history.presentations[-1].value.startswith("list: [")
        listener.cancel()
        listener.submit(":rm")
        screen.synchronize()
        surface.scroll_to_row(value.intervals[1].physical_row)
        y = value.intervals[1].physical_row - int(surface.scroll_y)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, 2, y))
        assert screen.documentation_line.sentence == (
            "SELECTING FILE FOR rm — PYTHON VALUE • Left: cannot use Value; File required • Right: no menu • Esc: cancel • Ctrl-G: cancel"
        )
        assert presentation_style(listener, value, value).dim
        before = listener.history.rows
        surface.on_click(_mouse_event(events.Click, surface, 2, y, button=1))
        assert listener.history.rows == before
        assert listener.chip is None and listener.pending_request is not None
        await pilot.press("escape")
        await pilot.resize_terminal(16, 8)
        await pilot.pause()
        surface.scroll_to_row(value.intervals[-1].physical_row)
        interval = value.intervals[-1]
        y = interval.physical_row - int(surface.scroll_y)
        assert surface.presentation_at_content_offset(2, y) is value
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
            "PYTHON VALUE • Left: show • Right: menu"
        )
        await pilot.press("ctrl+o")
        await pilot.pause()
        assert menu.target is target
        assert menu.labels == ("show", "show", "fail")
        assert [p.value.translator_index for p in menu.item_presentations] == [0, 1, 2]
        _move_menu_index(menu, 1)
        assert screen.documentation_line.sentence == (
            "MENU “show” ON PYTHON VALUE • Left: apply • Right: no menu"
        )
        _click_menu_index(menu, 1)
        assert calls == [(1, original)]
        assert listener.python_namespace["_"] is None
        assert listener.history.presentations[-1].value is None
        await pilot.pause()
        _open_menu_for(screen, target)
        await pilot.pause()
        assert menu.is_open
        _click_menu_index(menu, 0)
        assert calls[-1] == (0, original)
        assert listener.python_namespace["_"] == 7
        _open_menu_for(screen, target)
        await pilot.pause()
        assert menu.is_open
        before = len(listener.history.presentations)
        _click_menu_index(menu, 2)
        assert len(listener.history.presentations) == before + 2
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
    async with app.run_test(size=(50, 12)) as pilot:
        screen = app.screen
        listener.submit(":narrow")
        screen.synchronize()
        await pilot.press("ctrl+d")
        assert app.is_running and listener.pending_substring_listing is not None
        await pilot.press("escape")
        _open_menu_for(screen, header)
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
        assert screen.documentation_line.sentence == "PYTHON VALUE • Left: insert value into expression • Right: no menu"
        before = listener.history.rows
        surface.on_click(_mouse_event(events.Click, surface, x, y, button=1, chain=2))
        assert listener.python_pieces == ("f()",)
        listener.set_input_text('"abc"')
        editor.cursor_position = 2
        screen.synchronize()
        assert screen.documentation_line.sentence == (
            "PYTHON VALUE • Left: insertion unavailable in string or comment • Right: no menu"
        )
        surface.on_click(_mouse_event(events.Click, surface, x, y, button=1))
        assert listener.python_pieces == ('"abc"',) and listener.history.rows == before
        listener.set_input_text("foo")
        editor.cursor_position = 1
        screen.synchronize()
        assert screen.documentation_line.sentence == (
            "PYTHON VALUE • Left: move cursor to Python expression position to insert • Right: no menu"
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
        assert editor.prompt == f"pbui:{tmp_path} ...> "
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
        assert editor.has_focus and editor.prompt == f"pbui:{tmp_path} ...> "
        for key in ("ctrl+g", "escape"):
            _open_menu_for(screen, header)
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



def _click_history_presentation(screen, presentation, *, button=1, chain=1, interval_index=0):
    surface = screen.history_surface
    interval = presentation.intervals[interval_index]
    surface.scroll_to_row(interval.physical_row)
    y = interval.physical_row - int(surface.scroll_y)
    surface.on_click(
        _mouse_event(
            events.Click, surface, interval.start_column, y,
            button=button, chain=chain,
        )
    )


@pytest.mark.asyncio
async def test_transcript_screen_click_loads_then_enter_records_new_rows(tmp_path):
    listener = make_listener(tmp_path)
    listener.submit("1 + 2 + 3")
    python = next(p for p in listener.history.presentations if p.type is listener.types.python_input)
    result = next(p for p in listener.history.presentations if p.type is listener.types.value)
    listener.submit(":ls")
    command = next(p for p in listener.history.presentations if p.type is listener.types.command_input)
    assert isinstance(python.value, PythonInput)
    assert isinstance(command.value, SavedCommandInput)
    assert listener.history.rows[0].presentations == (python,)
    assert listener.history.rows[1].presentations == (result,)
    assert listener.history.rows[2].presentations == (command,)
    app = PbuiApp(listener)

    async with app.run_test(size=(60, 10)) as pilot:
        screen = app.screen
        assert screen.history_surface.current_layout.rows[0].text == "› 1 + 2 + 3"
        assert screen.history_surface.current_layout.rows[2].text == ""
        assert screen.history_surface.current_layout.rows[3].text == "› :ls"
        revision = listener.history.revision
        _click_history_presentation(screen, python)
        assert listener.input_text == "1 + 2 + 3"
        assert screen.command_input.cursor_position == len(listener.input_text)
        assert listener.history.revision == revision
        assert screen.command_input.display_text.endswith("1 + 2 + 3")
        await pilot.press("backspace", "4", "enter")
        new_python = [p for p in listener.history.presentations if p.type is listener.types.python_input][-1]
        assert new_python is not python
        rows = listener.history.rows
        index = next(i for i, row in enumerate(rows) if new_python in row.presentations)
        assert rows[index + 1].presentations[0].type is listener.types.value
        assert rows[index + 1].presentations[0].value == 7

        revision = listener.history.revision
        _click_history_presentation(screen, command)
        assert listener.input_text == ":ls"
        assert screen.command_input.cursor_position == 3
        assert listener.history.revision == revision
        await pilot.press("enter")
        new_command = [p for p in listener.history.presentations if p.type is listener.types.command_input][-1]
        assert new_command is not command
        index = next(i for i, row in enumerate(listener.history.rows) if new_command in row.presentations)
        assert listener.history.rows[index].presentations == (new_command,)
        assert listener.history.rows[index + 1].listing_owner is not None


@pytest.mark.asyncio
async def test_transcript_screen_wrapped_omission_row_yanks_full_form(tmp_path):
    listener = make_listener(tmp_path)
    saved_lines = tuple((f"line-{index}-" + "界" * 30,) for index in range(14))
    saved = listener._record_python(saved_lines)
    app = PbuiApp(listener)
    async with app.run_test(size=(18, 8)):
        screen = app.screen
        surface = screen.history_surface
        assert len(listener.history.rows) == 12
        omission = next(
            row for row in surface.current_layout.rows
            if row.logical_row == 11 and row.text.startswith("› … (")
        )
        assert omission.text.startswith("› … (")
        assert all(
            surface.current_layout.hit_test(interval.start_column, interval.physical_row) is saved
            for interval in saved.intervals
        )
        revision = listener.history.revision
        _click_history_presentation(screen, saved, interval_index=-1)
        assert listener.history.revision == revision
        assert listener.pending_python_pieces == saved_lines[:-1]
        assert listener.python_pieces == saved_lines[-1]
        assert screen.command_input.cursor_position == len(saved_lines[-1][0])


@pytest.mark.asyncio
async def test_transcript_screen_command_chip_and_menu_yank(tmp_path):
    target = tmp_path / "target"
    target.write_text("payload")
    listener = make_listener(tmp_path)
    listener.submit(":ls")
    file = next(p for p in listener.history.presentations if p.type is listener.types.file)
    listener.submit(":rm")
    assert listener.select_for_input(file, "saved target")
    saved = [p for p in listener.history.presentations if p.type is listener.types.command_input][-1]
    assert saved.value.chip.value is file.value
    app = PbuiApp(listener)
    async with app.run_test(size=(80, 10)) as pilot:
        screen = app.screen
        _click_history_presentation(screen, saved)
        assert listener.input_text == ":rm"
        assert listener.chip is saved.value.chip
        assert screen.command_input.cursor_position == 3
        assert screen.command_input.display_text.endswith("⟨File: saved target⟩")
        listener.cancel()
        screen.synchronize()
        _open_menu_for(screen, saved)
        await pilot.pause()
        assert screen.action_menu.labels == ("yank",)
        _move_menu_index(screen.action_menu, 0)
        assert screen.documentation_line.sentence == "MENU “yank” ON COMMAND INPUT • Left: yank into editor • Right: no menu"
        _click_menu_label(screen.action_menu, "yank")
        assert listener.input_text == ":rm"
        assert listener.chip.value is file.value
        assert screen.command_input.cursor_position == 3


@pytest.mark.asyncio
async def test_transcript_screen_action_click_and_menu_replay_preserve_composition(tmp_path):
    import sympy

    listener = make_listener(tmp_path)
    x = sympy.Symbol("x")
    original = sympy.sin(x) ** 2 + sympy.cos(x) ** 2
    listener.python_namespace["original"] = original
    listener.submit("original")
    source = [p for p in listener.history.presentations if p.type is listener.types.value][-1]
    listener.invoke_python_translator(source, 0)
    action = [p for p in listener.history.presentations if p.type is listener.types.menu_action_input][-1]
    assert isinstance(action.value, MenuActionInput)
    assert action.value.target is original
    assert listener.history.rows[-2].presentations == (action,)
    assert listener.history.rows[-1].presentations[0].value == 1
    app = PbuiApp(listener)

    async with app.run_test(size=(80, 10)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        interval = action.intervals[0]
        surface.on_mouse_move(_mouse_event(
            events.MouseMove, surface, interval.start_column,
            interval.physical_row - int(surface.scroll_y),
        ))
        assert screen.documentation_line.sentence == (
            "ACTION “simplify” • Left: run again on same object • Right: menu"
        )
        _click_history_presentation(screen, action)
        newer = [p for p in listener.history.presentations if p.type is listener.types.menu_action_input][-1]
        assert newer is not action
        assert newer.value.target is original
        assert listener.history.rows[-2].presentations == (newer,)
        assert listener.history.rows[-1].presentations[0].value == 1

        listener.set_input_text("f(x)")
        listener.set_python_cursor(2)
        screen.synchronize()
        before = (listener.python_pieces, listener.python_cursor)
        _open_menu_for(screen, action)
        await pilot.pause()
        assert screen.action_menu.labels == ("run again",)
        _move_menu_index(screen.action_menu, 0)
        assert screen.documentation_line.sentence == (
            "MENU “run again” ON ACTION “simplify” • Left: run again on same object • Right: no menu"
        )
        _click_menu_label(screen.action_menu, "run again")
        assert (listener.python_pieces, listener.python_cursor) == before
        assert [p for p in listener.history.presentations if p.type is listener.types.menu_action_input][-1] is not newer



@pytest.mark.asyncio
async def test_transcript_documentation_recomputes_at_stationary_pointer(tmp_path):
    import sympy

    listener = make_listener(tmp_path)
    listener.submit("2")
    python = next(p for p in listener.history.presentations if p.type is listener.types.python_input)
    value = next(p for p in listener.history.presentations if p.type is listener.types.value)
    listener.submit(":ls")
    command = next(p for p in listener.history.presentations if p.type is listener.types.command_input)
    x = sympy.Symbol("x")
    listener.python_namespace["expr"] = (x + 1) ** 2
    listener.submit("expr")
    symbolic = [p for p in listener.history.presentations if p.type is listener.types.value][-1]
    listener.invoke_python_translator(symbolic, 1)
    action = [p for p in listener.history.presentations if p.type is listener.types.menu_action_input][-1]
    app = PbuiApp(listener)

    async with app.run_test(size=(90, 12)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        editor = screen.command_input
        for target, expected in (
            (python, "PYTHON INPUT • Left: load into editor; Enter runs • Right: menu"),
            (command, "COMMAND INPUT • Left: load into editor; Enter runs • Right: menu"),
            (action, "ACTION “expand” • Left: run again on same object • Right: menu"),
        ):
            interval = target.intervals[0]
            surface.scroll_to_row(interval.physical_row)
            surface.on_mouse_move(_mouse_event(
                events.MouseMove, surface, interval.start_column,
                interval.physical_row - int(surface.scroll_y),
            ))
            assert screen.documentation_line.sentence == expected

        interval = python.intervals[0]
        surface.scroll_to_row(interval.physical_row)
        surface.on_mouse_move(_mouse_event(
            events.MouseMove, surface, interval.start_column,
            interval.physical_row - int(surface.scroll_y),
        ))
        listener.set_input_text("f()")
        editor.cursor_position = 2
        screen.synchronize()
        assert screen.documentation_line.sentence == "PYTHON INPUT • Left: insert at cursor • Right: menu"
        interval = command.intervals[0]
        surface.scroll_to_row(interval.physical_row)
        surface.on_mouse_move(_mouse_event(
            events.MouseMove, surface, interval.start_column,
            interval.physical_row - int(surface.scroll_y),
        ))
        assert screen.documentation_line.sentence == "COMMAND INPUT • Left: insert at cursor • Right: menu"
        interval = action.intervals[0]
        surface.scroll_to_row(interval.physical_row)
        surface.on_mouse_move(_mouse_event(
            events.MouseMove, surface, interval.start_column,
            interval.physical_row - int(surface.scroll_y),
        ))
        listener.set_input_text("f()")
        editor.cursor_position = 2
        screen.synchronize()
        assert screen.documentation_line.sentence == (
            "ACTION “expand” • Left: insert target into expression • Right: menu"
        )
        listener.set_input_text('"abc"')
        editor.cursor_position = 2
        screen.synchronize()
        assert screen.documentation_line.sentence == (
            "ACTION “expand” • Left: insertion unavailable in string or comment • Right: menu"
        )
        listener.set_input_text("foo")
        editor.cursor_position = 1
        screen.synchronize()
        assert screen.documentation_line.sentence == (
            "ACTION “expand” • Left: move cursor to Python expression position to insert • Right: menu"
        )
        listener.set_input_text("f()")
        editor.cursor_position = 2
        screen.synchronize()
        _click_history_presentation(screen, action, chain=2)
        assert listener.python_pieces == ("f()",)
        _click_history_presentation(screen, action)
        assert listener.python_pieces[1].value is action.value.target
        assert len([p for p in listener.history.presentations if p.type is listener.types.menu_action_input]) == 1

        listener.cancel()
        screen.synchronize()
        listener.submit(":rm")
        screen.synchronize()
        assert "cannot use PythonInput; File required" in format_documentation(listener, python)
        assert "cannot use CommandInput; File required" in format_documentation(listener, command)
        assert "cannot use MenuActionInput; File required" in format_documentation(listener, action)
        revision = listener.history.revision
        _click_history_presentation(screen, python)
        assert listener.pending_request is not None
        assert listener.history.revision == revision
        assert screen.documentation_line.sentence.startswith("SELECTING FILE FOR rm — PYTHON INPUT • Left: cannot use PythonInput;")
        await pilot.press("ctrl+g")
        assert format_documentation(listener, None) == "READY"


@pytest.mark.asyncio
async def test_transcript_screen_multiline_and_command_composition_yank(tmp_path):
    listener = make_listener(tmp_path)
    original = object()
    saved = listener._record_python((("a",), ("b",)))
    command = listener._record_command(
        "rm", Chip(listener.types.file, original, "saved label")
    )
    app = PbuiApp(listener)
    async with app.run_test(size=(70, 9)) as pilot:
        screen = app.screen
        editor = screen.command_input
        listener.set_input_text("preSUF")
        editor.cursor_position = 3
        screen.synchronize()
        _click_history_presentation(screen, saved, interval_index=-1)
        assert listener.pending_python_pieces == (("pre", "a"),)
        assert listener.python_pieces == ("bSUF",)
        assert listener.python_cursor == 1
        assert editor.cursor_position == 1

        listener.cancel()
        listener.set_input_text("f()")
        editor.cursor_position = 2
        screen.synchronize()
        _open_menu_for(screen, saved)
        await pilot.pause()
        assert screen.action_menu.labels == ("yank",)
        _click_menu_label(screen.action_menu, "yank")
        assert listener.pending_python_pieces == (("f(", "a"),)
        assert listener.python_pieces == ("b)",)
        assert listener.python_cursor == 1

        listener.cancel()
        listener.set_input_text("f()")
        editor.cursor_position = 2
        screen.synchronize()
        _click_history_presentation(screen, command)
        assert listener.python_pieces[0] == "f(:rm"
        assert listener.python_pieces[1].value is original
        assert listener.python_pieces[1].label == "saved label"
        assert listener.python_pieces[-1] == ")"
        assert editor.cursor_position == listener.python_cursor


@pytest.mark.asyncio
async def test_transcript_screen_listing_action_replay_and_evicted_error(tmp_path):
    (tmp_path / "alpha").write_text("a")
    (tmp_path / "beta").write_text("b")
    listener = make_listener(tmp_path, history_max_rows=12)
    listener.submit(":ls")
    listing = first_listing(listener)
    assert listener.apply_listing_view(listing, "sort", "name")
    action = [p for p in listener.history.presentations if p.type is listener.types.menu_action_input][-1]
    before_listing_rows = tuple(
        row for row in listener.history.rows if row.listing_owner is listing
    )
    app = PbuiApp(listener)
    async with app.run_test(size=(80, 10)) as pilot:
        screen = app.screen
        _click_history_presentation(screen, action)
        replay = [p for p in listener.history.presentations if p.type is listener.types.menu_action_input][-1]
        assert replay is not action
        assert replay.value.target is listing
        assert tuple(row for row in listener.history.rows if row.listing_owner is listing) == before_listing_rows

        listener.set_input_text("f()")
        screen.command_input.cursor_position = 2
        screen.synchronize()
        before = (listener.python_pieces, listener.python_cursor)
        _open_menu_for(screen, replay)
        await pilot.pause()
        _click_menu_label(screen.action_menu, "run again")
        assert (listener.python_pieces, listener.python_cursor) == before
        assert [p for p in listener.history.presentations if p.type is listener.types.menu_action_input][-1] is not replay

    stale_root = tmp_path / "stale"
    stale_root.mkdir()
    stale = make_listener(stale_root, history_max_rows=4)
    stale.submit(":ls")
    stale_listing = first_listing(stale)
    assert stale.apply_listing_view(stale_listing, "sort", "name")
    stale_action = [p for p in stale.history.presentations if p.type is stale.types.menu_action_input][-1]
    index = 0
    while stale._listing_is_retained(stale_listing):
        stale._append_text(f"evict-{index}")
        index += 1
    assert stale_action in stale.history.presentations
    stale_app = PbuiApp(stale)
    async with stale_app.run_test(size=(60, 8)):
        _click_history_presentation(stale_app.screen, stale_action)
        assert stale.history.rows[-2].presentations[0].type is stale.types.menu_action_input
        assert stale.history.rows[-1].presentations[0].type is stale.types.error
        assert "no longer in history" in stale.history.rows[-1].fragments[0].children[0].text



@pytest.mark.asyncio
async def test_transcript_screen_saved_narrow_replays_exact_listing_and_substring(tmp_path):
    (tmp_path / "alpha").write_text("a")
    (tmp_path / "beta").write_text("b")
    listener = make_listener(tmp_path)
    listener.submit(":ls")
    listing = first_listing(listener)
    assert listener.begin_listing_narrow(listing)
    listener.set_input_text("alpha")
    listener.submit()
    action = [p for p in listener.history.presentations if p.type is listener.types.menu_action_input][-1]
    assert action.value.label == "narrow"
    assert action.value.argument == "alpha"
    assert action.value.target is listing
    assert any(row.presentations == (action,) for row in listener.history.rows)
    app = PbuiApp(listener)
    async with app.run_test(size=(70, 10)):
        screen = app.screen
        assert any(row.text.startswith("› narrow alpha — ") for row in screen.history_surface.current_layout.rows)
        _click_history_presentation(screen, action)
        replay = [p for p in listener.history.presentations if p.type is listener.types.menu_action_input][-1]
        assert replay is not action
        assert replay.value.argument == "alpha"
        assert replay.value.target is listing
        assert listing.view.substring_filter == "alpha"


@pytest.mark.asyncio
async def test_transcript_hover_rebuilds_only_rows_of_old_and_new_inputs(tmp_path, monkeypatch):
    listener = make_listener(tmp_path)
    for index in range(40):
        listener._append_text(f"before-{index}")
    first = listener._record_python((("x" * 300,),))
    second = listener._record_python((("y" * 220,),))
    for index in range(40):
        listener._append_text(f"after-{index}")
    app = PbuiApp(listener)
    async with app.run_test(size=(18, 8)):
        surface = app.screen.history_surface
        assert len(first.intervals) > 3
        built = []
        original_build = surface._build_row
        monkeypatch.setattr(surface, "_build_row", lambda row: built.append(row) or original_build(row))
        monkeypatch.setattr(surface, "_build_all_rows", lambda: pytest.fail("hover rebuilt every row"))
        surface.set_hovered_presentation(first)
        surface.set_hovered_presentation(second)
        expected = {interval.physical_row for interval in first.intervals + second.intervals}
        assert set(built) == expected
        assert len(built) < len(surface.current_layout.rows)



@pytest.mark.asyncio
async def test_transcript_input_menus_use_fresh_pointer_ctrl_o_and_right_click(tmp_path):
    listener = make_listener(tmp_path)
    listener.submit("3")
    python = next(p for p in listener.history.presentations if p.type is listener.types.python_input)
    listener.submit(":ls")
    command = next(p for p in listener.history.presentations if p.type is listener.types.command_input)
    app = PbuiApp(listener)
    async with app.run_test(size=(30, 8)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        interval = python.intervals[0]
        surface.on_mouse_move(_mouse_event(
            events.MouseMove, surface, interval.start_column,
            interval.physical_row - int(surface.scroll_y),
        ))
        await pilot.press("ctrl+o")
        await pilot.pause()
        assert screen.action_menu.target is python
        assert screen.action_menu.labels == ("yank",)
        screen.close_menu()
        await pilot.resize_terminal(18, 8)
        await pilot.pause()
        interval = command.intervals[0]
        surface.scroll_to_row(interval.physical_row)
        y = interval.physical_row - int(surface.scroll_y)
        surface.on_click(_mouse_event(
            events.Click, surface, interval.start_column, y, button=3,
        ))
        await pilot.pause()
        assert screen.action_menu.target is command
        surface.on_click(_mouse_event(
            events.Click, surface, interval.start_column, y,
            button=1, chain=2,
        ))
        assert screen.action_menu.is_open
        _click_menu_label(screen.action_menu, "yank")
        assert listener.input_text == ":ls"
        assert screen.command_input.cursor_position == 3


@pytest.mark.asyncio
async def test_popup_overlays_history_without_changing_rows_or_viewport(tmp_path):
    import sympy

    listener = make_listener(tmp_path)
    listener.python_namespace["expr"] = (sympy.Symbol("x") + 1) ** 2
    listener.submit("expr")
    expression = [p for p in listener.history.presentations if p.type is listener.types.value][-1]
    app = PbuiApp(listener)
    async with app.run_test(size=(70, 14)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        interval = expression.intervals[0]
        x = min(interval.start_column + 3, interval.end_column - 1)
        y = interval.physical_row - int(surface.scroll_y)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, x, y))
        assert screen.documentation_line.sentence == (
            "SYMPY EXPRESSION • Left: show • Right: menu"
        )
        history_region = surface.region
        documentation_region = screen.documentation_line.region
        input_region = screen.command_input.region
        scroll = int(surface.scroll_y)
        intervals = expression.intervals
        hit = surface.presentation_at_content_offset(x, y)
        surface.on_click(_mouse_event(events.Click, surface, x, y, button=3))
        await pilot.pause()
        menu = screen.action_menu
        assert menu.target is expression
        assert menu.labels == ("simplify", "expand", "factor")
        assert menu.geometry.anchor == (surface.scrollable_content_region.x + x,
                                        surface.scrollable_content_region.y + y)
        rect = menu.geometry.rect
        region = surface.scrollable_content_region
        top_line = surface.render_line(rect.y - region.y).text
        bottom_line = surface.render_line(rect.y + rect.height - 1 - region.y).text
        assert top_line[rect.x - region.x:rect.x - region.x + rect.width] == menu.geometry.row_text(rect.y)
        assert bottom_line[rect.x - region.x:rect.x - region.x + rect.width] == menu.geometry.row_text(rect.y + rect.height - 1)
        assert surface.region == history_region
        assert screen.documentation_line.region == documentation_region
        assert screen.command_input.region == input_region
        assert int(surface.scroll_y) == scroll
        assert expression.intervals == intervals
        screen.close_menu()
        await pilot.pause()
        assert surface.presentation_at_content_offset(x, y) is hit
        assert expression.intervals == intervals
        assert menu.geometry is None


@pytest.mark.asyncio
async def test_popup_clamping_hover_border_clicks_and_outside_routing(tmp_path):
    file_path = tmp_path / "a-very-long-file-name-for-pointer"
    file_path.write_text("payload")
    listener = make_listener(tmp_path)
    listener.submit(":ls")
    file = next(p for p in listener.history.presentations if p.type is listener.types.file)
    app = PbuiApp(listener)
    async with app.run_test(size=(35, 12)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        region = surface.scrollable_content_region
        pointer = Offset(region.x + region.width - 2, region.y + region.height - 2)
        screen._pointer_screen = pointer
        screen.open_menu(file, anchor=(pointer.x, pointer.y))
        menu = screen.action_menu
        assert menu.is_open
        assert menu.geometry.rect.x + menu.geometry.rect.width == region.x + region.width
        assert menu.geometry.rect.y + menu.geometry.rect.height == region.y + region.height
        assert menu.hovered_presentation is menu.item_presentations[1]
        assert screen.documentation_line.sentence == (
            f"MENU “rm” ON FILE “{file_path.name}” • Left: run • Right: no menu"
        )
        # Border and non-left clicks stay inert, as do later clicks in a chain.
        rect = menu.geometry.rect
        border_x = rect.x - region.x
        border_y = rect.y - region.y + 1
        surface.on_click(_mouse_event(events.Click, surface, border_x, border_y, button=1))
        assert menu.is_open and file_path.exists()
        _click_menu_index(menu, 1, button=3)
        _click_menu_index(menu, 1, chain=2)
        assert menu.is_open and file_path.exists()
        assert screen.documentation_line.sentence.endswith("Right: no menu")
        # The blank right padding belongs to the item row.
        before = listener.history.revision
        _click_menu_index(menu, 0, x=rect.width - 2)
        assert not menu.is_open
        assert listener.history.revision > before
        assert file_path.exists()

        interval = file.intervals[0]
        surface.scroll_to_row(interval.physical_row)
        y = interval.physical_row - int(surface.scroll_y)
        x = min(interval.start_column + 10, interval.end_column - 1)
        surface.on_click(_mouse_event(events.Click, surface, x, y, button=3))
        assert menu.is_open
        before = listener.history.revision
        assert not menu.geometry.rect.contains(region.x, region.y + y)
        assert surface.presentation_at_content_offset(0, y) is None
        surface.on_click(_mouse_event(events.Click, surface, 0, y, button=1))
        assert not menu.is_open
        assert listener.history.revision == before

        surface.on_click(_mouse_event(events.Click, surface, x, y, button=3))
        assert menu.is_open
        outside_surface, outside_x, outside_y = _outside_menu_cell(menu)
        outside_surface.on_mouse_move(_mouse_event(
            events.MouseMove, outside_surface, outside_x, outside_y
        ))
        assert not menu.is_open


@pytest.mark.asyncio
async def test_popup_ctrl_o_anchor_resize_scroll_and_colon_yank(tmp_path):
    (tmp_path / "file").write_text("x")
    listener = make_listener(tmp_path)
    listener.submit(":ls")
    saved = listener._record_command("ls", None)
    file = next(p for p in listener.history.presentations if p.type is listener.types.file)
    _append_plain_rows(listener, 25)
    app = PbuiApp(listener)
    async with app.run_test(size=(30, 12)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        surface.scroll_to_row(file.intervals[0].physical_row)
        interval = file.intervals[0]
        x, y = interval.start_column, interval.physical_row - int(surface.scroll_y)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, x, y))
        await pilot.press("ctrl+o")
        assert screen.action_menu.target is file
        region = surface.scrollable_content_region
        assert screen.action_menu.geometry.anchor == (region.x + x, region.y + y)
        screen.close_menu()

        screen._pointer_screen = Offset(region.x + region.width - 1, region.y + region.height - 1)
        surface.set_hovered_presentation(file)
        await pilot.press("ctrl+o")
        assert screen.action_menu.target is file
        assert screen.action_menu.geometry.anchor == screen._visible_cells(file)[0]
        await pilot.resize_terminal(12, 8)
        await pilot.pause()
        assert screen.action_menu.is_open
        rect = screen.action_menu.geometry.rect
        region = surface.scrollable_content_region
        assert region.x <= rect.x and rect.x + rect.width <= region.x + region.width
        assert region.y <= rect.y and rect.y + rect.height <= region.y + region.height
        await pilot.resize_terminal(7, 8)
        await pilot.pause()
        assert not screen.action_menu.is_open
        assert screen.documentation_line.region.height == 1
        screen.open_menu(file, anchor=(surface.scrollable_content_region.x,
                                       surface.scrollable_content_region.y))
        assert not screen.action_menu.is_open
        assert screen.documentation_line.sentence == (
            "FILE “file” • Menu does not fit in history area"
        )

        await pilot.resize_terminal(30, 12)
        surface.scroll_to_row(file.intervals[0].physical_row)
        surface.set_hovered_presentation(file)
        screen._pointer_screen = None
        await pilot.press("ctrl+o")
        assert screen.action_menu.is_open
        surface.scroll_to(
            y=int(surface.scroll_y) + 3, animate=False, force=True, immediate=True
        )
        await pilot.pause()
        assert not screen.action_menu.is_open
        surface.set_hovered_presentation(file)
        await pilot.press("ctrl+o")
        assert not screen.action_menu.is_open
        assert screen.documentation_line.sentence == "FILE “file” • Point at object to open its menu"

        surface.scroll_to_row(saved.intervals[0].physical_row)
        listener.set_input_text(":show")
        screen.command_input.cursor_position = len(listener.input_text)
        screen.synchronize()
        screen._pointer_screen = None
        screen.open_menu(saved)
        assert screen.action_menu.labels == ("yank",)
        _move_menu_index(screen.action_menu, 0)
        assert screen.documentation_line.sentence == (
            "MENU “yank” ON COMMAND INPUT • Left: no action while editing command • Right: no menu"
        )
        before = listener.input_text
        _click_menu_label(screen.action_menu, "yank")
        assert not screen.action_menu.is_open
        assert listener.input_text == before


@pytest.mark.asyncio
async def test_http_screen_menus_json_dig_and_wrapped_member_hits(tmp_path):
    body = b'{"data":{"children":[{"name":"Ada"}]}}'
    calls = []

    def fake_get(request):
        calls.append(request)
        return GetResult(200, request.url, {'Content-Type': 'application/json'}, body)

    listener = make_listener(tmp_path, get_transport=fake_get)
    listener.submit(':get https://example.org/tree.json')
    request = listener.history.presentations[-1]
    request_row = listener.history.rows[-1]
    app = PbuiApp(listener)
    async with app.run_test(size=(28, 14)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        interval = request.intervals[0]
        surface.scroll_to_row(interval.physical_row)
        x, y = interval.start_column, interval.physical_row - int(surface.scroll_y)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, x, y))
        assert screen.documentation_line.sentence == (
            'GET REQUEST “https://example.org/tree.json” • Left: show • Right: menu'
        )
        await pilot.press('ctrl+o')
        assert screen.action_menu.target is request
        assert screen.action_menu.labels == ('perform',)
        _move_menu_index(screen.action_menu, 0)
        assert screen.documentation_line.sentence == (
            'MENU “perform” ON GET REQUEST “https://example.org/tree.json” • Left: apply • Right: no menu'
        )
        menu = screen.action_menu
        border = menu.geometry.rect
        region = surface.scrollable_content_region
        surface.on_mouse_move(_mouse_event(
            events.MouseMove, surface, border.x - region.x,
            border.y - region.y,
        ))
        assert screen.documentation_line.sentence == (
            'NO TARGET • Click an item • Esc: close menu • Ctrl-G: close menu'
        )
        _click_menu_label(menu, 'perform')
        assert calls == [request.value]
        assert listener.history.rows[1] is request_row
        action = listener.history.rows[-2].presentations[0]
        response = listener.history.rows[-1].presentations[0]
        assert action.value.label == 'perform'
        assert action.value.target is request.value
        assert response.value.body is body
        interval = response.intervals[0]
        surface.scroll_to_row(interval.physical_row)
        x, y = interval.start_column, interval.physical_row - int(surface.scroll_y)
        surface.on_click(_mouse_event(events.Click, surface, x, y, button=3))
        assert screen.action_menu.target is response
        assert screen.action_menu.labels == ('json', 'body')
        assert screen.action_menu.geometry.anchor == (
            region.x + x, region.y + y,
        )
        _click_menu_label(screen.action_menu, 'json')
        json_action = listener.history.rows[-2].presentations[0]
        root_row = listener.history.rows[-1]
        root = root_row.presentations[0]
        assert json_action.value.label == 'json'
        assert json_action.value.target is response.value
        assert type(root.value) is JsonObject
        assert root.value is listener.python_namespace['_']
        assert root_row is listener.history.rows[-1]
        assert root_row.presentations == (root,)
        assert surface.current_layout.rows[-1].text == '  ▸ JsonObject (1 keys)'
        _click_history_presentation(screen, root, button=3)
        assert not screen.action_menu.is_open
        _click_history_presentation(screen, root)
        assert listener.history.rows[-2] is root_row
        data_row = listener.history.rows[-1]
        data = data_row.presentations[0]
        assert type(data.value) is JsonObject
        assert data.value is root.value['data']
        assert data_row.presentations == (data,)
        assert len(data.intervals) > 1
        for interval in (data.intervals[0], data.intervals[-1]):
            surface.scroll_to_row(interval.physical_row)
            y = interval.physical_row - int(surface.scroll_y)
            assert surface.presentation_at_content_offset(interval.start_column, y) is data
        _click_history_presentation(screen, data, interval_index=-1)
        children = listener.history.rows[-1].presentations[0]
        assert type(children.value) is JsonArray
        assert children.value is data.value['children']
        assert listener.history.rows[-2] is data_row
        _click_history_presentation(screen, children)
        assert listener.history.rows[-1].presentations[0].value is children.value[0]
        assert listener.history.rows[-2].presentations[0] is children

        _open_menu_for(screen, response)
        assert screen.action_menu.labels == ('json', 'body')
        _click_menu_label(screen.action_menu, 'body')
        assert listener.history.rows[-2].presentations[0].value.label == 'body'
        assert listener.history.rows[-1].presentations[0].value == body.decode()
        assert listener.python_namespace['_'] is root.value

        listener.set_input_text('f()')
        screen.command_input.cursor_position = 2
        screen.synchronize()
        _open_menu_for(screen, response)
        _click_menu_label(screen.action_menu, 'json')
        assert listener.python_pieces == ('f()',)
        assert listener.python_cursor == 2
        assert listener.history.presentations[-1].value is root.value
        listener.cancel()
        _click_history_presentation(screen, action)
        assert calls == [request.value, request.value]
        assert listener.history.rows[-2].presentations[0].value.label == 'perform'
        assert listener.history.rows[-2].presentations[0].value.target is request.value
        assert listener.history.rows[-1].presentations[0].value.status == 200


@pytest.mark.asyncio
async def test_http_screen_json_documentation_chip_and_modal_precedence(tmp_path):
    tree = JsonObject({'child': JsonArray([4])})
    listener = make_listener(tmp_path)
    listener.python_namespace['tree'] = tree
    listener.submit('tree')
    root = listener.history.presentations[-1]
    app = PbuiApp(listener)
    async with app.run_test(size=(70, 12)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        editor = screen.command_input
        interval = root.intervals[0]
        x, y = interval.start_column, interval.physical_row - int(surface.scroll_y)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, x, y))
        assert screen.documentation_line.sentence == (
            "JSON OBJECT (1 keys) • Left: list members • Right: no menu"
        )
        await pilot.press('ctrl+o')
        assert not screen.action_menu.is_open
        listener.set_input_text('f()')
        editor.cursor_position = 2
        screen.synchronize()
        assert screen.documentation_line.sentence == (
            'JSON OBJECT (1 keys) • Left: insert value into expression • Right: no menu'
        )
        before = listener.history.rows
        _click_history_presentation(screen, root)
        assert listener.python_pieces[1].value is tree
        assert listener.history.rows == before
        listener.cancel()
        listener.set_input_text('"abc"')
        editor.cursor_position = 2
        screen.synchronize()
        assert screen.documentation_line.sentence == (
            'JSON OBJECT (1 keys) • Left: insertion unavailable in string or comment • Right: no menu'
        )
        _click_history_presentation(screen, root)
        assert listener.history.rows == before
        listener.set_input_text('foo')
        editor.cursor_position = 1
        screen.synchronize()
        assert screen.documentation_line.sentence == (
            'JSON OBJECT (1 keys) • Left: move cursor to Python expression position to insert • Right: no menu'
        )
        _click_history_presentation(screen, root)
        assert listener.history.rows == before
        listener.cancel()
        listener.set_input_text('if True:')
        editor.cursor_position = len(listener.input_text)
        await pilot.press('enter')
        listener.set_input_text('    lambda x: x[')
        editor.cursor_position = len(listener.input_text)
        screen.synchronize()
        _click_history_presentation(screen, root)
        assert listener.python_pieces[-1].value is tree
        assert listener.history.rows == before
        listener.cancel()
        listener.submit(':rm')
        screen.synchronize()
        assert screen.documentation_line.sentence == (
            'SELECTING FILE FOR rm — JSON OBJECT (1 keys) • Left: cannot use Value; File required • Right: no menu • Esc: cancel • Ctrl-G: cancel'
        )
        _click_history_presentation(screen, root)
        assert listener.pending_request is not None
        assert listener.history.rows == before
        await pilot.press('escape')
        listener.submit(':ls')
        listener.submit(':narrow')
        screen.synchronize()
        assert listener.pending_substring_listing is not None
        assert screen.documentation_line.sentence == (
            'SELECTING TEXT FOR narrow • Type substring; Enter: narrow listing • Esc: cancel • Ctrl-G: cancel'
        )
        before = listener.history.rows
        _click_history_presentation(screen, root)
        assert listener.history.rows == before
        await pilot.press('escape')
        _click_history_presentation(screen, root)
        child = listener.history.rows[-1].presentations[0]
        assert type(child.value) is JsonArray
        interval = child.intervals[0]
        surface.scroll_to_row(interval.physical_row)
        y = interval.physical_row - int(surface.scroll_y)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, interval.start_column, y))
        assert screen.documentation_line.sentence == (
            "JSON ARRAY (1 elements) • Left: list members • Right: no menu"
        )
        _click_history_presentation(screen, child)
        scalar = listener.history.rows[-1].presentations[0]
        assert scalar.value == 4
        surface.on_mouse_move(_mouse_event(
            events.MouseMove, surface, scalar.intervals[0].start_column,
            scalar.intervals[0].physical_row - int(surface.scroll_y),
        ))
        assert screen.documentation_line.sentence == (
            'PYTHON VALUE • Left: show • Right: no menu'
        )


@pytest.mark.asyncio
@pytest.mark.parametrize('content_type,body,expected_error', [
    ('application/json', b'{bad}', True),
    ('text/plain', b'{"valid":true}', False),
])
async def test_http_screen_ineligible_json_has_body_only_menu(
    tmp_path, content_type, body, expected_error
):
    listener = make_listener(
        tmp_path,
        get_transport=lambda request: GetResult(
            200, request.url, {'Content-Type': content_type}, body
        ),
    )
    listener.submit(':get https://example.org/data')
    response = listener.invoke_python_translator(listener.history.presentations[-1], 0)
    assert (listener.history.presentations[-1].type is listener.types.error) == expected_error
    app = PbuiApp(listener)
    async with app.run_test(size=(60, 10)):
        screen = app.screen
        count = len(listener.history.rows)
        _click_history_presentation(screen, response, button=3)
        assert screen.action_menu.target is response
        assert screen.action_menu.labels == ('body',)
        assert len(listener.history.rows) == count
        _click_menu_label(screen.action_menu, 'body')
        assert listener.history.rows[-2].presentations[0].value.label == 'body'
        assert listener.history.rows[-1].presentations[0].value == body.decode()


@pytest.mark.asyncio
async def test_http_screen_literal_trailer_is_inert(tmp_path):
    listener = make_listener(tmp_path)
    listener.python_namespace['many'] = JsonArray(range(101))
    listener.submit('many')
    parent_row = listener.history.rows[-1]
    parent = parent_row.presentations[0]
    app = PbuiApp(listener)
    async with app.run_test(size=(24, 8)):
        screen = app.screen
        surface = screen.history_surface
        _click_history_presentation(screen, parent)
        assert parent_row in listener.history.rows
        trailer = listener.history.rows[-1]
        assert trailer.presentations == ()
        trailer_logical = len(listener.history.rows) - 1
        physical = next(
            y for y, row in enumerate(surface.current_layout.rows)
            if row.logical_row == trailer_logical
        )
        surface.scroll_to_row(physical)
        y = physical - int(surface.scroll_y)
        assert surface.presentation_at_content_offset(0, y) is None
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, 0, y))
        assert screen.documentation_line.sentence == 'READY'
        revision = listener.history.revision
        surface.on_click(_mouse_event(events.Click, surface, 0, y, button=1))
        surface.on_click(_mouse_event(events.Click, surface, 0, y, button=3))
        assert listener.history.revision == revision
        assert not screen.action_menu.is_open


def _tutorial_presentation(listener, kind, *, direction=None, card=None):
    presentation_type = {
        "card": listener.types.tutorial_card,
        "target": listener.types.tutorial_target,
        "try": listener.types.tutorial_try,
    }[kind]
    return next(
        item for item in reversed(listener.history.presentations)
        if item.type is presentation_type
        and (direction is None or item.value.direction == direction)
        and (card is None or item.value is card)
    )


def _tutorial_cell(surface, presentation, interval_index=0):
    interval = presentation.intervals[interval_index]
    y = interval.physical_row - int(surface.scroll_y)
    if not 0 <= y < surface.scrollable_content_region.height:
        surface.scroll_to_row(interval.physical_row)
        y = interval.physical_row - int(surface.scroll_y)
    assert 0 <= y < surface.scrollable_content_region.height
    return interval.start_column, y


def _tutorial_click(surface, presentation, *, button=1, chain=1):
    x, y = _tutorial_cell(surface, presentation)
    surface.on_click(_mouse_event(
        events.Click, surface, x, y, button=button, chain=chain
    ))


def _tutorial_hover(surface, presentation):
    x, y = _tutorial_cell(surface, presentation)
    surface.on_mouse_move(_mouse_event(events.MouseMove, surface, x, y))


@pytest.mark.asyncio
async def test_history_tour_screen_gaps_indent_hits_and_hover(tmp_path, monkeypatch):
    (tmp_path / "sample").write_text("data")
    listener = make_listener(tmp_path)
    app = PbuiApp(listener)

    async with app.run_test(size=(120, 20)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        listener.submit(":tutorial")
        screen.synchronize()
        first_try = _tutorial_presentation(listener, "try")
        first_next = _tutorial_presentation(listener, "target", direction="Next")
        _tutorial_click(surface, first_try)
        assert listener.input_text == "1 + 2 + 3"
        await pilot.press("enter")
        value = next(
            item for item in listener.history.presentations
            if item.type is listener.types.value and item.value == 6
        )
        _tutorial_click(surface, first_next)
        second_try = _tutorial_presentation(listener, "try")
        second_next = _tutorial_presentation(listener, "target", direction="Next")
        _tutorial_click(surface, second_try)
        assert listener.input_text == ":ls"
        await pilot.press("enter")
        file = next(
            item for item in listener.history.presentations
            if item.type is listener.types.file
        )
        _tutorial_click(surface, second_next)
        picture = surface.current_layout
        assert picture.rows[0].text == "› :tutorial"
        value_y = next(i for i, row in enumerate(picture.rows) if row.text == "  int 6")
        file_y = next(
            i for i, row in enumerate(picture.rows)
            if row.text.startswith("  sample")
        )
        assert picture.rows[value_y + 1].text == ""
        assert picture.rows[value_y + 1].logical_row is None
        assert picture.rows[value_y + 2].text.startswith("  2. Colon commands")
        assert picture.rows[file_y + 1].text == ""
        assert picture.rows[file_y + 1].logical_row is None
        assert picture.rows[file_y + 2].text.startswith("  3. Reuse a value")
        assert picture.hit_test(0, file_y) is None
        assert picture.hit_test(1, file_y) is None
        assert picture.hit_test(2, file_y) is file
        assert picture.hit_test(2, value_y + 1) is None
        try_interval = first_try.intervals[0]
        assert picture.hit_test(
            try_interval.start_column, try_interval.physical_row
        ) is first_try
        assert picture.hit_test(0, try_interval.physical_row) is None
        assert picture.hit_test(1, try_interval.physical_row) is None

        gap = value_y + 1
        surface.scroll_to_row(file_y)
        file_view_y = file_y - int(surface.scroll_y)
        for indent_x in (0, 1):
            surface.on_mouse_move(_mouse_event(
                events.MouseMove, surface, indent_x, file_view_y
            ))
            assert surface.pointer_logical_column is None
        surface.on_mouse_move(_mouse_event(
            events.MouseMove, surface, 2, file_view_y
        ))
        assert surface.pointer_logical_column == 0
        surface.scroll_to_row(gap)
        assert int(surface.scroll_y) == gap
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, 2, 0))
        assert surface.pointer_logical_column is None
        surface.synchronize(force=True)
        assert int(surface.scroll_y) == gap + 1
        assert _top_logical_row(surface) is listener.history.rows[
            picture.rows[gap + 1].logical_row
        ]

        surface.set_hovered_presentation(None)
        built = []
        original_builder = terminal_module.build_history_row_text

        def record_row(*args, **kwargs):
            built.append(args[2])
            return original_builder(*args, **kwargs)

        monkeypatch.setattr(terminal_module, "build_history_row_text", record_row)
        surface.set_hovered_presentation(file)
        assert built
        assert file_y in built
        assert all(surface.current_layout.rows[y].logical_row is not None for y in built)
        assert file_y + 1 not in built

        surface.set_hovered_presentation(None)
        before = len(listener.history.rows)
        _click_history_presentation(screen, file)
        assert len(listener.history.rows) == before + 1
        detail_rows = [
            row for row in surface.current_layout.rows
            if row.logical_row == len(listener.history.rows) - 1
        ]
        assert detail_rows[0].text.startswith("  path: ")
        assert all(row.text.startswith("  ") for row in detail_rows)
        before = len(listener.history.rows)
        _click_history_presentation(screen, value)
        assert len(listener.history.rows) > before
        assert surface.current_layout.rows[-1].text.startswith("  ")
        _tutorial_click(surface, first_try)
        assert listener.input_text == "1 + 2 + 3"


@pytest.mark.asyncio
async def test_tutorial_card_screen_hits_styles_wrapping_scroll_and_menus(tmp_path):
    listener = make_listener(tmp_path)
    listener.submit(":tutorial")
    card = _tutorial_presentation(listener, "card")
    back = _tutorial_presentation(listener, "target", direction="Back")
    next_link = _tutorial_presentation(listener, "target", direction="Next")
    up = _tutorial_presentation(listener, "target", direction="Up")
    example = _tutorial_presentation(listener, "try")
    app = PbuiApp(listener)

    async with app.run_test(size=(28, 8)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        documentation = screen.documentation_line
        rows = tuple(
            row for row in listener.history.rows if card in row.presentations
        )
        assert len(rows) == 7
        assert all(card in row.presentations for row in rows)
        assert any(
            sum(rendered.logical_row == index for rendered in surface.current_layout.rows) > 1
            for index, row in enumerate(listener.history.rows) if row in rows
        )
        for row in rows:
            first = _first_physical_row(surface, row)
            segments = [
                index for index, rendered in enumerate(surface.current_layout.rows)
                if rendered.logical_row == surface.current_layout.rows[first].logical_row
            ]
            if not any(item in row.presentations for item in (example, back, next_link, up)):
                for physical in segments:
                    assert surface.current_layout.hit_test(0, physical) is None
                    assert surface.current_layout.hit_test(2, physical) is card

        for control in (back, next_link, up, example):
            assert control.intervals
            for interval in control.intervals:
                assert surface.current_layout.hit_test(
                    interval.start_column, interval.physical_row
                ) is control
        assert presentation_style(listener, back, back).dim
        assert not presentation_style(listener, back, back).reverse
        for control in (next_link, up, example):
            assert presentation_style(listener, control, control).underline
        _tutorial_hover(surface, back)
        assert documentation.sentence == (
            "TUTORIAL BACK • Left: no previous card • Right: no menu"
        )
        _tutorial_hover(surface, next_link)
        assert documentation.sentence == (
            "TUTORIAL NEXT “2. Colon commands” • Left: open • Right: no menu"
        )
        _tutorial_hover(surface, up)
        assert documentation.sentence == (
            "TUTORIAL UP “Contents” • Left: open • Right: no menu"
        )
        _tutorial_hover(surface, example)
        assert documentation.sentence == (
            "TUTORIAL TRY • Left: load example into editor; Enter runs • Right: no menu"
        )
        _tutorial_hover(surface, card)
        assert documentation.sentence == (
            "TUTORIAL CARD “1. Presentations” • Left: no action • Right: no menu"
        )
        before = listener.history.rows
        _tutorial_click(surface, card)
        _tutorial_click(surface, card, button=3)
        _tutorial_click(surface, back)
        _tutorial_click(surface, next_link, button=3)
        _tutorial_click(surface, next_link, chain=2)
        assert listener.history.rows == before
        assert not screen.action_menu.is_open
        _tutorial_hover(surface, next_link)
        await pilot.press("ctrl+o")
        assert not screen.action_menu.is_open
        _tutorial_hover(surface, card)
        await pilot.press("ctrl+o")
        assert not screen.action_menu.is_open

        example_row = next(row for row in rows if example in row.presentations)
        first = _first_physical_row(surface, example_row)
        assert surface.current_layout.hit_test(8, first) is card
        await pilot.resize_terminal(16, 8)
        await pilot.pause()
        assert len(example.intervals) >= 1
        assert surface.current_layout.hit_test(
            example.intervals[-1].start_column, example.intervals[-1].physical_row
        ) is example
        _tutorial_hover(surface, example)
        assert documentation.sentence.startswith("TUTORIAL TRY • Left: load example")
        assert display_width(documentation.render().plain) <= documentation.content_size.width
        _tutorial_click(surface, next_link)
        assert _tutorial_presentation(listener, "card").value.title == "2. Colon commands"
        assert card in listener.history.presentations
        _append_plain_rows(listener, 500)
        screen.synchronize()
        assert card not in listener.history.presentations
        assert next_link not in listener.history.presentations


@pytest.mark.asyncio
async def test_tutorial_navigation_and_try_editor_states(tmp_path):
    listener = make_listener(tmp_path)
    listener.submit(":tutorial")
    first = _tutorial_presentation(listener, "card")
    back = _tutorial_presentation(listener, "target", direction="Back")
    next_link = _tutorial_presentation(listener, "target", direction="Next")
    example = _tutorial_presentation(listener, "try")
    app = PbuiApp(listener)

    async with app.run_test(size=(95, 18)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        editor = screen.command_input
        documentation = screen.documentation_line
        before = listener.history.rows
        _tutorial_click(surface, back)
        assert listener.history.rows == before
        _tutorial_click(surface, example, chain=2)
        _tutorial_click(surface, example, button=3)
        assert listener.input_text == ""
        assert listener.history.rows == before
        _tutorial_click(surface, example)
        assert listener.input_text == "1 + 2 + 3"
        assert editor.cursor_position == len(listener.input_text)
        assert listener.history.rows == before
        await pilot.press("left", "9")
        assert listener.input_text == "1 + 2 + 93"
        _tutorial_hover(surface, example)
        assert documentation.sentence == (
            "TUTORIAL TRY • Left: finish or cancel current input before trying • Right: no menu"
        )
        _tutorial_click(surface, example)
        assert listener.input_text == "1 + 2 + 93"
        listener.set_input_text("1 + 2 + 3")
        screen.synchronize()
        await pilot.press("enter")
        assert listener.history.presentations[-1].value == 6
        assert first in listener.history.presentations

        listener.set_input_text(":ls")
        editor.adopt_listener_cursor()
        screen.synchronize()
        old_cursor = editor.cursor_position
        old_input = listener.input_text
        before = listener.history.rows
        _tutorial_click(surface, next_link)
        second = _tutorial_presentation(listener, "card")
        assert second.value.title == "2. Colon commands"
        assert listener.input_text == old_input
        assert editor.cursor_position == old_cursor
        assert listener.history.rows[:len(before)] == before
        assert all(
            item.type not in {listener.types.python_input, listener.types.command_input}
            for row in listener.history.rows[len(before):] for item in row.presentations
        )
        command_example = _tutorial_presentation(listener, "try")
        _tutorial_hover(surface, command_example)
        assert documentation.sentence.startswith("TUTORIAL TRY • Left: finish or cancel")
        _tutorial_click(surface, command_example)
        assert listener.input_text == ":ls"

        listener.set_input_text("")
        screen.synchronize()
        before = listener.history.rows
        _tutorial_click(surface, command_example)
        assert listener.input_text == ":ls"
        assert editor.cursor_position == 3
        assert listener.history.rows == before

        listener.set_input_text("")
        screen.synchronize()
        up = _tutorial_presentation(listener, "target", direction="Up")
        _tutorial_click(surface, up)
        contents = _tutorial_presentation(listener, "card")
        assert contents.value.title == "Contents"
        entry = next(
            item for item in listener.history.presentations
            if item.type is listener.types.tutorial_target
            and item.value.direction == "Contents"
            and item.value.destination.title == "5. Bring input back"
        )
        _tutorial_hover(surface, entry)
        assert documentation.sentence == (
            "TUTORIAL CONTENTS “5. Bring input back” • Left: open • Right: no menu"
        )
        _tutorial_click(surface, entry)
        last = _tutorial_presentation(listener, "card")
        assert last.value.title == "5. Bring input back"
        last_next = _tutorial_presentation(listener, "target", direction="Next")
        assert presentation_style(listener, last_next, last_next).dim
        _tutorial_hover(surface, last_next)
        assert documentation.sentence == (
            "TUTORIAL NEXT • Left: no next card • Right: no menu"
        )
        before = listener.history.rows
        _tutorial_click(surface, last_next)
        assert listener.history.rows == before


@pytest.mark.asyncio
async def test_tutorial_controls_accept_continuation_popup_and_existing_hits(tmp_path):
    (tmp_path / "sample").write_text("data")
    listener = make_listener(tmp_path)
    listener.submit("2")
    value = next(item for item in listener.history.presentations if item.type is listener.types.value)
    saved_input = next(
        item for item in listener.history.presentations
        if item.type is listener.types.python_input
    )
    listener.submit(":ls")
    file = next(item for item in listener.history.presentations if item.type is listener.types.file)
    listener.submit(":tutorial")
    next_link = _tutorial_presentation(listener, "target", direction="Next")
    example = _tutorial_presentation(listener, "try")
    card = _tutorial_presentation(listener, "card")
    app = PbuiApp(listener)

    async with app.run_test(size=(100, 22)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        editor = screen.command_input
        documentation = screen.documentation_line
        listener.set_input_text("10 + ")
        editor.adopt_listener_cursor()
        screen.synchronize()
        _tutorial_hover(surface, card)
        assert documentation.sentence == (
            "TUTORIAL CARD “1. Presentations” • Left: insert value into expression • Right: no menu"
        )
        _tutorial_click(surface, next_link)
        assert listener.input_text == "10 + "
        assert listener.chip is None
        _tutorial_click(surface, value)
        assert any(getattr(piece, "value", None) is value.value for piece in listener.python_pieces)
        before = listener.history.rows
        _tutorial_hover(surface, example)
        assert documentation.sentence.startswith("TUTORIAL TRY • Left: finish or cancel")
        _tutorial_click(surface, example)
        assert listener.history.rows == before
        assert any(getattr(piece, "value", None) is value.value for piece in listener.python_pieces)
        listener.set_input_text("")
        screen.synchronize()
        _tutorial_click(surface, saved_input)
        assert listener.input_text == "2"
        listener.set_input_text("")
        screen.synchronize()

        listener.submit("if True:")
        screen.synchronize()
        assert listener.pending_python_pieces
        _tutorial_hover(surface, example)
        assert documentation.sentence.startswith("TUTORIAL TRY • Left: finish or cancel")
        before = listener.history.rows
        _tutorial_click(surface, example)
        assert listener.history.rows == before and listener.input_text == ""
        revision = listener.history.revision
        _tutorial_click(surface, next_link)
        assert listener.pending_python_pieces
        assert listener.history.revision > revision
        listener.cancel_python_continuation()

        listener.submit(":rm")
        screen.synchronize()
        pending = listener.pending_request
        _tutorial_hover(surface, card)
        assert documentation.sentence == (
            "SELECTING FILE FOR rm — TUTORIAL CARD “1. Presentations” • Left: cannot use TutorialCard; File required • Right: no menu • Esc: cancel • Ctrl-G: cancel"
        )
        _tutorial_hover(surface, next_link)
        assert documentation.sentence == (
            "SELECTING FILE FOR rm — TUTORIAL NEXT “2. Colon commands” • Left: open • Right: no menu • Esc: cancel • Ctrl-G: cancel"
        )
        _tutorial_hover(surface, example)
        assert documentation.sentence.startswith("SELECTING FILE FOR rm — TUTORIAL TRY • Left: finish or cancel")
        before = listener.history.rows
        _tutorial_click(surface, example)
        assert listener.history.rows == before
        _tutorial_click(surface, next_link)
        assert listener.pending_request is pending
        assert listener.history.rows != before
        listener.cancel()

        listener.submit(":narrow")
        screen.synchronize()
        pending_listing = listener.pending_substring_listing
        _tutorial_hover(surface, next_link)
        assert documentation.sentence == (
            "SELECTING TEXT FOR narrow — TUTORIAL NEXT “2. Colon commands” • Left: open • Right: no menu • Esc: cancel • Ctrl-G: cancel"
        )
        _tutorial_hover(surface, example)
        assert documentation.sentence.startswith("SELECTING TEXT FOR narrow — TUTORIAL TRY • Left: finish or cancel")
        _tutorial_click(surface, example)
        assert listener.input_text == ""
        _tutorial_click(surface, next_link)
        assert listener.pending_substring_listing is pending_listing
        listener.cancel()
        screen.synchronize()

        surface.scroll_to_row(example.intervals[0].physical_row)
        region = surface.scrollable_content_region
        screen.open_menu(file, anchor=(region.x + 50, region.y + 1))
        assert screen.action_menu.is_open
        geometry = screen.action_menu.geometry
        assert geometry is not None
        nav_x, nav_y = _tutorial_cell(surface, next_link)
        assert not geometry.rect.contains(region.x + nav_x, region.y + nav_y)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, nav_x, nav_y))
        assert screen.action_menu.is_open
        assert documentation.sentence == (
            "TUTORIAL NEXT “2. Colon commands” • Left: open • Right: no menu"
        )
        before = listener.history.rows
        _tutorial_click(surface, next_link)
        assert not screen.action_menu.is_open
        assert listener.history.rows != before
        assert _tutorial_presentation(listener, "card").value.title == "2. Colon commands"

        surface.scroll_to_row(example.intervals[0].physical_row)
        screen.open_menu(file, anchor=(region.x + 50, region.y + 1))
        assert screen.action_menu.is_open
        before = listener.history.rows
        _tutorial_click(surface, next_link)
        assert not screen.action_menu.is_open
        assert listener.history.rows != before

        surface.scroll_to_row(example.intervals[0].physical_row)
        screen.open_menu(file, anchor=(region.x + 50, region.y + 1))
        assert screen.action_menu.is_open
        try_x, try_y = _tutorial_cell(surface, example)
        assert not screen.action_menu.geometry.rect.contains(region.x + try_x, region.y + try_y)
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, try_x, try_y))
        assert screen.action_menu.is_open
        assert documentation.sentence.startswith("TUTORIAL TRY • Left: finish or cancel")
        before = listener.history.rows
        _tutorial_click(surface, example)
        assert not screen.action_menu.is_open
        assert listener.input_text == ""
        assert listener.history.rows == before

        screen.open_menu(file, anchor=(region.x + 50, region.y + 1))
        assert screen.action_menu.is_open
        border_x = screen.action_menu.geometry.rect.x - region.x
        border_y = screen.action_menu.geometry.rect.y - region.y
        surface.on_mouse_move(_mouse_event(events.MouseMove, surface, border_x, border_y))
        assert documentation.sentence == "NO TARGET • Click an item • Esc: close menu • Ctrl-G: close menu"
        before = listener.history.rows
        surface.on_click(_mouse_event(events.Click, surface, border_x, border_y, button=1))
        assert listener.history.rows == before
        assert screen.action_menu.is_open
        screen.close_menu()


@pytest.mark.asyncio
async def test_input_mode_rule_cwd_shortening_and_fixed_anchor(tmp_path):
    (tmp_path / "file").write_text("payload")
    listener = make_listener(tmp_path)
    listener.submit(":ls")
    listing = first_listing(listener)
    file_target = next(
        presentation for presentation in listing.member_presentations
        if type(presentation.value) is FileRef
    )
    app = PbuiApp(listener)

    async with app.run_test(size=(160, 10)) as pilot:
        screen = app.screen
        editor = screen.command_input
        assert editor.region.height == 2
        assert editor.content_size.height == 1
        assert editor.styles.border_top[0] == "solid"
        assert editor.render_line(0).text.startswith(f"PYTHON │ pbui:{tmp_path}> ")
        assert any(
            span.start == 0 and span.end == len("PYTHON") and span.style.bold
            for span in editor.renderable.spans
        )

        _open_menu_for(screen, file_target)
        assert screen.action_menu.is_open
        assert editor.render_line(0).text.startswith("PYTHON │ ")
        screen.close_menu()

        listener.set_input_text("x" * 120)
        editor.cursor_position = len(listener.input_text)
        screen.synchronize()
        assert editor.render_line(0).text.startswith(f"PYTHON │ pbui:{tmp_path}> ")
        await pilot.resize_terminal(48, 10)
        narrow = editor.render_line(0).text
        assert narrow.startswith("PYTHON │ pbui:…")
        assert str(tmp_path)[-8:] in narrow
        assert "> " in narrow
        assert narrow.rstrip().endswith("x")
        assert listener.cwd == str(tmp_path)
        assert listener.input_text == "x" * 120
        assert editor.cursor_position == 120

        await pilot.resize_terminal(6, 10)
        assert editor.render_line(0).text == "PYTHON"


@pytest.mark.asyncio
async def test_input_mode_transitions_in_screen(tmp_path):
    listener = make_listener(tmp_path)
    app = PbuiApp(listener)
    async with app.run_test(size=(100, 10)) as pilot:
        editor = app.screen.command_input
        row = editor.render_line(0)
        assert row.text.startswith(f"PYTHON │ pbui:{tmp_path}> ")
        assert row._segments[0].text == "PYTHON"
        assert row._segments[0].style.bold
        assert not row._segments[1].style.bold

        await pilot.press(*_key_names(":rm"))
        assert editor.render_line(0).text.startswith(f"COMMAND │ pbui:{tmp_path}> :rm")
        await pilot.press("enter")
        assert editor.render_line(0).text.startswith(
            f"SELECT FILE FOR rm │ pbui:{tmp_path}> "
        )
        await pilot.press("escape")
        assert editor.render_line(0).text.startswith(f"PYTHON │ pbui:{tmp_path}> ")


@pytest.mark.asyncio
async def test_bottom_documentation_hand_check_sequence(tmp_path):
    (tmp_path / "sample-file").write_text("sample")
    listener = make_listener(tmp_path)
    listener.submit(":ls")
    listing = first_listing(listener)
    file = next(
        item for item in listing.member_presentations
        if item.presentation_type is listener.types.file
    )
    app = PbuiApp(listener)
    async with app.run_test(size=(140, 12)) as pilot:
        screen = app.screen
        surface = screen.history_surface
        line = screen.documentation_line
        assert screen.command_input.mode == "PYTHON"
        assert line.sentence == "READY"
        interval = file.intervals[0]
        surface.scroll_to_row(interval.physical_row)
        surface.on_mouse_move(_mouse_event(
            events.MouseMove, surface, interval.start_column,
            interval.physical_row - int(surface.scroll_y),
        ))
        assert line.sentence == (
            "FILE “sample-file” • Left: show • Right: menu"
        )
        assert line.render().plain == line.sentence
        await pilot.press(*_key_names(":rm"), "enter")
        assert screen.command_input.mode == "SELECT FILE FOR rm"
        assert line.sentence == (
            "SELECTING FILE FOR rm — FILE “sample-file”"
            " • Left: use and run command • Right: no menu"
            " • Esc: cancel • Ctrl-G: cancel"
        )
        await pilot.press("escape")
        assert screen.command_input.mode == "PYTHON"
        assert line.sentence == "READY"
