"""Mode decisions remain usable without importing the terminal adapter."""

from __future__ import annotations

import pytest

from pbui.bottom import format_mode
from pbui.commands import HeadlessListener, RootedFilesystem
from pbui.substrate import AcceptRequest


class EmptyProcesses:
    own_uid = 1000
    own_pid = 1

    def list_for_uid(self, _uid):
        return ()

    def inspect(self, _pid):
        raise AssertionError("mode formatting must not inspect a process")

    def send_sigterm(self, _pid):
        raise AssertionError("mode formatting must not signal a process")


def listener_at(tmp_path):
    return HeadlessListener(str(tmp_path), RootedFilesystem(tmp_path), EmptyProcesses())


def test_python_command_and_continuation_modes(tmp_path):
    listener = listener_at(tmp_path)
    assert format_mode(listener) == "PYTHON"
    listener.set_input_text("value + 1")
    assert format_mode(listener) == "PYTHON"
    for text in (":", "   :", "  :rm", ":ls"):
        listener.set_input_text(text)
        assert format_mode(listener) == "COMMAND"
    listener.set_input_text("if True:")
    listener.submit()
    assert listener.input_text == ""
    assert listener.pending_python_pieces
    assert format_mode(listener) == "CONTINUE"


@pytest.mark.parametrize(
    ("command", "expected"),
    (
        ("rm", "SELECT FILE FOR rm"),
        ("cd", "SELECT DIRECTORY FOR cd"),
        ("kill", "SELECT PROCESS FOR kill"),
        ("show", "SELECT FILE/DIRECTORY/PROCESS FOR show"),
    ),
)
def test_presentation_accept_modes_and_precedence(tmp_path, command, expected):
    listener = listener_at(tmp_path)
    listener.submit(f":{command}")
    assert listener.pending_request is not None
    assert format_mode(listener) == expected
    listener.cancel()
    assert format_mode(listener) == "PYTHON"


def test_pending_accept_outranks_suspended_continuation(tmp_path):
    listener = listener_at(tmp_path)
    listener.submit("if True:")
    assert format_mode(listener) == "CONTINUE"
    listener.state.begin_accept(
        AcceptRequest("rm", frozenset({listener.types.file}), lambda _chip: None)
    )
    assert listener.pending_python_pieces
    assert format_mode(listener) == "SELECT FILE FOR rm"


def test_command_and_menu_narrow_modes(tmp_path):
    (tmp_path / "one").write_text("value")
    listener = listener_at(tmp_path)
    listener.submit(":ls")
    listing = next(row.listing_owner for row in listener.history.rows if row.listing_owner)

    listener.submit(":narrow")
    assert listener.pending_substring_listing is listing
    assert format_mode(listener) == "SELECT TEXT FOR narrow"
    listener.cancel()

    listener.submit("if True:")
    assert format_mode(listener) == "CONTINUE"
    assert listener.begin_listing_narrow(listing)
    assert format_mode(listener) == "SELECT TEXT FOR narrow"
    listener.cancel()
    assert format_mode(listener) == "CONTINUE"


def test_documentation_target_kinds_and_saved_values(tmp_path):
    from pbui.bottom import format_documentation
    from pbui.domain import DirectoryRef, FileRef, ProcessRef
    from pbui.http import GetRequest, HttpResponse, JsonArray, JsonObject
    from pbui.substrate import Presentation

    listener = listener_at(tmp_path)
    types = listener.types
    cases = (
        (types.file, FileRef("/saved/a\n界"), "FILE “a\\n界” • Left: show • Right: menu"),
        (types.directory, DirectoryRef("/saved/work"), "DIRECTORY “work” • Left: show • Right: menu"),
        (types.process, ProcessRef(42), "PROCESS 42 • Left: show • Right: menu"),
        (types.value, 9, "PYTHON VALUE • Left: show • Right: no menu"),
        (types.value, GetRequest("https://example.test/a\nb"), "GET REQUEST “https://example.test/a\\nb” • Left: show • Right: menu"),
        (types.value, HttpResponse(201, "https://example.test/end", None, b""), "HTTP RESPONSE 201 “https://example.test/end” • Left: show • Right: menu"),
        (types.value, JsonObject({"a": 1, "b": 2}), "JSON OBJECT (2 keys) • Left: list members • Right: no menu"),
        (types.value, JsonArray([1, 2, 3]), "JSON ARRAY (3 elements) • Left: list members • Right: no menu"),
        (types.text, "text", "TEXT • Left: no action • Right: no menu"),
        (types.error, "error", "ERROR • Left: no action • Right: no menu"),
    )
    assert format_documentation(listener, None) == "NO TARGET"
    for index, (presentation_type, value, expected) in enumerate(cases):
        presentation = Presentation(10000 + index, presentation_type, value)
        assert format_documentation(listener, presentation) == expected


@pytest.mark.parametrize(
    ("command", "accepted_kind", "accepted_value", "target", "required"),
    (
        ("rm", "file", "/saved/a", "FILE “a”", "File"),
        ("cd", "directory", "/saved/d", "DIRECTORY “d”", "Directory"),
        ("kill", "process", 42, "PROCESS 42", "Process"),
        ("show", "file", "/saved/a", "FILE “a”", "File, Directory, or Process"),
    ),
)
def test_presentation_accept_documentation(tmp_path, command, accepted_kind, accepted_value, target, required):
    from pbui.bottom import format_documentation
    from pbui.domain import DirectoryRef, FileRef, ProcessRef
    from pbui.substrate import Presentation

    listener = listener_at(tmp_path)
    values = {"file": FileRef, "directory": DirectoryRef, "process": ProcessRef}
    selected = Presentation(800, getattr(listener.types, accepted_kind), values[accepted_kind](accepted_value))
    rejected = Presentation(801, listener.types.text, "text")
    listener.submit(f":{command}")
    lead = f"SELECTING {format_mode(listener)[len('SELECT '):]}"
    tail = " • Esc: cancel • Ctrl-G: cancel"
    assert format_documentation(listener, None) == (
        f"{lead} • Point at highlighted {required} and click{tail}"
    )
    assert format_documentation(listener, selected) == (
        f"{lead} — {target} • Left: use and run command • Right: no menu{tail}"
    )
    assert format_documentation(listener, rejected) == (
        f"{lead} — TEXT • Left: cannot use Text; {required} required • Right: no menu{tail}"
    )


def test_saved_inputs_insertion_sites_and_popup_items(tmp_path):
    from pbui.bottom import format_documentation, format_menu_item_documentation
    from pbui.domain import FileRef
    from pbui.substrate import Presentation
    from pbui.transcript import CommandInput, MenuActionInput, PythonInput

    listener = listener_at(tmp_path)
    types = listener.types
    py = Presentation(901, types.python_input, PythonInput((("1+2",),)))
    command = Presentation(902, types.command_input, CommandInput("ls"))
    file = Presentation(903, types.file, FileRef("/saved/a"))
    action = Presentation(
        904, types.menu_action_input,
        MenuActionInput("show", lambda: None, None, file.value, "a", "file"),
    )
    action = listener._record_action(action.value)
    assert format_documentation(listener, py) == "PYTHON INPUT • Left: load into editor; Enter runs • Right: menu"
    assert format_documentation(listener, command) == "COMMAND INPUT • Left: load into editor; Enter runs • Right: menu"
    assert format_documentation(listener, action) == "ACTION “show” • Left: run again on same object • Right: menu"
    assert format_menu_item_documentation(listener, "rm", file) == (
        "MENU “rm” ON FILE “a” • Left: run • Right: no menu"
    )
    assert format_menu_item_documentation(listener, "yank", command) == (
        "MENU “yank” ON COMMAND INPUT • Left: yank into editor • Right: no menu"
    )
    listener.set_input_text("f()")
    listener.set_python_cursor(2)
    assert format_documentation(listener, py) == "PYTHON INPUT • Left: insert at cursor • Right: menu"
    assert format_documentation(listener, action) == "ACTION “show” • Left: insert target into expression • Right: menu"
    listener.set_input_text('"abc"')
    listener.set_python_cursor(2)
    assert format_documentation(listener, action) == (
        "ACTION “show” • Left: insertion unavailable in string or comment • Right: menu"
    )
    listener.set_input_text("foo")
    listener.set_python_cursor(1)
    assert format_documentation(listener, action) == (
        "ACTION “show” • Left: move cursor to Python expression position to insert • Right: menu"
    )
    listener.set_input_text(":ls")
    assert format_documentation(listener, py) == (
        "PYTHON INPUT • Left: no action while editing command • Right: menu"
    )
    assert format_menu_item_documentation(listener, "yank", command) == (
        "MENU “yank” ON COMMAND INPUT • Left: no action while editing command • Right: no menu"
    )


def test_substring_continuation_and_tutorial_selection_documentation(tmp_path):
    from pbui.bottom import format_documentation
    from pbui.substrate import Presentation

    listener = listener_at(tmp_path)
    listener.submit("if True:")
    assert format_documentation(listener, None) == (
        "NO TARGET • Python continuation: enter another line • Esc: discard • Ctrl-G: discard"
    )
    listener.cancel()
    listener.submit(":tutorial")
    navigation = next(
        p for p in listener.history.presentations
        if p.type is listener.types.tutorial_target and p.value.direction == "Next"
    )
    example = next(p for p in listener.history.presentations if p.type is listener.types.tutorial_try)
    assert format_documentation(listener, navigation) == (
        "TUTORIAL NEXT “2. Colon commands” • Left: open • Right: no menu"
    )
    assert format_documentation(listener, example) == (
        "TUTORIAL TRY • Left: load example into editor; Enter runs • Right: no menu"
    )
    assert format_documentation(listener, example, menu_open=True) == (
        "TUTORIAL TRY • Left: finish or cancel current input before trying • Right: no menu"
    )
    listener.submit(":rm")
    assert format_documentation(listener, navigation) == (
        "SELECTING FILE FOR rm — TUTORIAL NEXT “2. Colon commands” • Left: open • Right: no menu • Esc: cancel • Ctrl-G: cancel"
    )
    assert format_documentation(listener, example).startswith(
        "SELECTING FILE FOR rm — TUTORIAL TRY • Left: finish or cancel"
    )
    listener.cancel()
    (tmp_path / "one").write_text("value")
    listener.submit(":ls")
    listener.submit(":narrow")
    text = Presentation(900, listener.types.text, "literal")
    assert format_documentation(listener, None) == (
        "SELECTING TEXT FOR narrow • Type substring; Enter: narrow listing • Esc: cancel • Ctrl-G: cancel"
    )
    assert format_documentation(listener, text) == (
        "SELECTING TEXT FOR narrow — TEXT • Type substring; Enter: narrow listing • Esc: cancel • Ctrl-G: cancel"
    )
    assert format_documentation(listener, navigation).startswith(
        "SELECTING TEXT FOR narrow — TUTORIAL NEXT"
    )


def test_popup_failure_and_display_cell_fitting(tmp_path):
    from pbui.bottom import (
        MENU_BORDER_DOCUMENTATION, fit_documentation, format_documentation,
        format_popup_failure,
    )
    from pbui.domain import FileRef
    from pbui.substrate import Presentation
    from pbui.text import display_width

    listener = listener_at(tmp_path)
    file = Presentation(100, listener.types.file, FileRef("/saved/界\n" + "x" * 90))
    sentence = format_documentation(listener, file)
    assert "\n" not in sentence
    assert "\\n" in sentence
    assert format_popup_failure(file, listener, too_large=False).endswith(
        " • Point at object to open its menu"
    )
    assert format_popup_failure(file, listener, too_large=True).endswith(
        " • Menu does not fit in history area"
    )
    assert MENU_BORDER_DOCUMENTATION == (
        "NO TARGET • Click an item • Esc: close menu • Ctrl-G: close menu"
    )
    width = display_width("FILE • Left: show • Right: menu") + 5
    fitted = fit_documentation(sentence, width)
    assert display_width(fitted) <= width
    assert fitted.startswith("FILE")
    assert fitted.endswith(" • Left: show • Right: menu")
    assert "\n" not in fitted
    fixed = "FILE • Left: show • Right: menu"
    assert fit_documentation(sentence, display_width(fixed)) == fixed
    assert fit_documentation(sentence, 1) == "…"


def test_unknown_presentation_refusal_uses_escaped_type_name(tmp_path):
    from pbui.bottom import format_documentation
    from pbui.substrate import Presentation, PresentationType

    listener = listener_at(tmp_path)
    unknown = Presentation(999, PresentationType("Odd\nType"), "value")
    assert format_documentation(listener, unknown) == "NO TARGET"
    listener.submit(":rm")
    assert format_documentation(listener, unknown) == (
        "SELECTING FILE FOR rm — OBJECT Odd\\nType"
        " • Left: cannot use Odd\\nType; File required"
        " • Right: no menu • Esc: cancel • Ctrl-G: cancel"
    )
