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
from pbui.substrate import Chip, Presentation, PresentationType
from pbui.terminal import (
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
from pbui.text import DrawingContext, layout


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
            DocumentationLine,
            CommandInput,
        ]
        assert [child.id for child in children] == [
            "history",
            "documentation",
            "command-input",
        ]
        history, documentation, command = children
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
    listener.submit("ls")
    listener.submit("ps")
    listener.history.append(
        listener.drawing_contexts.standalone.present_row(
            "plain [not markup]", listener.types.text
        )
    )
    listener.submit("unknown")
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

    listener.submit(command)
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
        listener.submit(command)
        assert [format_documentation(listener, pointer) for pointer in pointers] == expected

    counterfeit = Presentation(30_000, PresentationType("File"), FileRef("/tmp/x"))
    listener.cancel()
    assert format_documentation(listener, counterfeit) == (
        "No presentation under pointer."
    )


def test_documentation_truncation_is_one_row_and_display_safe(tmp_path):
    listener = make_listener(tmp_path)
    line = DocumentationLine(listener)
    assert "height: 1" in line.DEFAULT_CSS
    assert truncate_display("short", 10) == "short"
    assert truncate_display("界x", 2) == "…"
    assert truncate_display("Aé界Z", 4) == "Aé…"
    assert display_width(truncate_display("Aé界Z", 4)) <= 4
    assert not truncate_display("Aé界Z", 4).endswith("e…")


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
    listener.submit("cd child")
    assert command.prompt == f"pbui:{child}> "
    assert os.getcwd() != str(child)
    listener.submit("rm")
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
        await pilot.press("l", "s", "enter")
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
            await pilot.press(*_key_names(command_name), "enter")
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

        listener.set_input_text("cd child")
        command.cursor_position = len(listener.input_text)
        revision = listener.history.revision
        old_scroll = int(surface.scroll_y)
        await pilot.press("enter")
        assert listener.cwd == str(child)
        assert listener.history.revision == revision
        assert int(surface.scroll_y) == old_scroll
        assert command.prompt == f"pbui:{child}> "
        assert listener.input_text == ""

        listener.set_input_text("unknown")
        command.cursor_position = len(listener.input_text)
        await pilot.press("enter")
        assert listener.input_text == ""
        assert command.cursor_position == 0
        assert int(surface.scroll_y) == int(surface.max_scroll_y)
        assert listener.history.presentations[-1].presentation_type is listener.types.error

        listener.set_input_text("rm")
        listener.submit("rm")
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
        listener.submit("rm")
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
    listener.submit("ls")
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

        assert app.screen.command_input.has_focus
        assert not surface.can_focus
        await pilot.click(surface, offset=(0, y))
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
        assert calls == [(target_presentation, "file with space")]


@pytest.mark.asyncio
async def test_click_uses_original_objects_for_accept_default_and_refusals(tmp_path):
    target = tmp_path / "delete me"
    target.write_text("payload")
    directory = tmp_path / "directory"
    directory.mkdir()
    listener = make_listener(tmp_path)
    listener.submit("ls")
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

        listener.submit("rm")
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
        literal_interval = directory_presentation.intervals[0]
        surface.scroll_to_row(literal_interval.physical_row)
        y = literal_interval.physical_row - int(surface.scroll_y)
        surface.on_click(
            _mouse_event(events.Click, surface, 0, y, button=1)
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
