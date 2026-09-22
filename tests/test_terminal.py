from __future__ import annotations

import ast
import os
import signal
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from rich.console import Console
from textual.widget import Widget
from textual.widgets import Button, Label, Static

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
    format_documentation,
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
    assert any(item.startswith("textual>=") for item in dependencies)
    assert any(item.startswith("rich>=") for item in dependencies)
    assert any(item.startswith("pytest-asyncio>=") for item in development)
    assert "scripts" not in metadata["project"]
    assert not (PROJECT_ROOT / "src/pbui/__main__.py").exists()

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
