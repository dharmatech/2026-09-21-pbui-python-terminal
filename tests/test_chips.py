"""Headless Python chips: editing, insertion, splicing, and execution."""

from __future__ import annotations

import code

import pytest

from pbui.chips import PythonChip, PythonLine, splice
from pbui.commands import HeadlessListener, RootedFilesystem
from pbui.text import display_width, layout, truncate_display


class EmptyProcesses:
    own_uid = 1000
    own_pid = 700

    def list_for_uid(self, uid):
        return ()


def listener_at(tmp_path, *, max_rows=500):
    return HeadlessListener(
        str(tmp_path), RootedFilesystem(tmp_path), EmptyProcesses(),
        history_max_rows=max_rows,
    )


def drawings(listener):
    return tuple(row.text for row in layout(listener.history, 10000).rows)


def value_row(listener):
    return next(p for p in listener.history.presentations if p.type is listener.types.value)


def test_piece_cursor_editing_and_atomic_deletion():
    object_value = object()
    chip = PythonChip(object_value, "captured")
    line = PythonLine(("abcd",), 2)
    line.insert_chip(chip)
    assert line.pieces == ("ab", chip, "cd")
    assert line.cursor == 3
    line.insert_text("X")
    assert line.pieces == ("ab", chip, "Xcd")
    line.left()
    line.left()
    assert line.cursor == 2
    line.insert_text("Y")
    assert line.pieces == ("abY", chip, "Xcd")
    line.home()
    assert line.cursor == 0
    line.end()
    assert line.cursor == 7
    line.backspace()
    assert line.pieces == ("abY", chip, "Xc")
    line.home()
    for _ in range(3):
        line.right()
    assert line.delete()
    assert line.pieces == ("abYXc",)
    line = PythonLine(("a", chip, "b"), 2)
    assert line.backspace()
    assert line.pieces == ("ab",)
    assert line.cursor == 1


def test_capture_label_identity_and_eviction(tmp_path):
    listener = listener_at(tmp_path, max_rows=2)
    original = object()
    listener.python_namespace["original"] = original
    listener.submit("original")
    presentation = value_row(listener)
    captured = drawings(listener)[0]
    listener.set_input_text("f(")
    assert listener.select_for_input(presentation)
    chip = next(p for p in listener.python_pieces if isinstance(p, PythonChip))
    assert chip.value is original
    assert chip.label == truncate_display(captured, 32)
    assert display_width(chip.label) <= 32
    listener._append_text("eviction one")
    listener._append_text("eviction two")
    assert presentation not in listener.history.presentations
    assert chip.value is original
    assert chip.label == truncate_display(captured, 32)
    assert not listener.select_for_input(presentation)


def test_mode_routing_and_modal_precedence(tmp_path):
    target = tmp_path / "target"
    target.write_text("x")
    listener = listener_at(tmp_path)
    listener.submit(":ls")
    file_presentation = next(p for p in listener.history.presentations if p.type is listener.types.file)
    before = len(listener.history.rows)
    assert listener.input_mode == "empty"
    assert listener.select_for_input(file_presentation)
    assert len(listener.history.rows) == before + 1
    listener.submit(":rm")
    assert listener.pending_request is not None
    assert listener.input_mode == "command"
    assert listener.select_for_input(file_presentation, "target")
    assert listener.pending_request is None
    assert not target.exists()
    listener.set_input_text("  :show")
    assert listener.input_mode == "command"
    assert not listener.insert_python_chip(file_presentation)
    listener.set_input_text("f(")
    assert listener.input_mode == "python"
    assert listener.select_for_input(file_presentation)
    listener.python_home()
    listener.insert_python_text(":")
    assert listener.input_mode == "python"
    listener.python_right()
    listener.python_right()
    assert listener.python_delete()
    assert listener.input_mode == "command"
    listener.cancel()
    listener.submit(":ls")
    listing = listener.history.rows[-2].listing_owner
    assert listener.begin_listing_narrow(listing)
    listener.set_input_text("target")
    assert not listener.select_for_input(file_presentation)
    listener.cancel()


@pytest.mark.parametrize("source,cursor", [
    ('f("abc")', 4),
    ('f("abc', 4),
    ("f('''abc''')", 6),
    ('f(f"{x}")', 5),
    ('x # comment', 7),
    ('foo', 2),
    ('123', 2),
    ('obj.', 4),
    ('import ', 7),
    ('def ', 4),
])
def test_invalid_insertion_does_not_compile_or_mutate(tmp_path, monkeypatch, source, cursor):
    listener = listener_at(tmp_path)
    listener.submit("1")
    presentation = value_row(listener)
    listener.set_input_text(source)
    listener.python_home()
    for _ in range(cursor):
        listener.python_right()
    old = (listener.python_pieces, listener.python_cursor, listener.history.rows, listener.python_namespace.copy())
    monkeypatch.setattr(code, "compile_command", lambda *args, **kwargs: pytest.fail("compiled on click"))
    assert not listener.select_for_input(presentation)
    assert (listener.python_pieces, listener.python_cursor, listener.history.rows, listener.python_namespace) == old


def test_valid_insertion_positions_and_refusal_no_default_show(tmp_path):
    listener = listener_at(tmp_path)
    listener.submit("1")
    presentation = value_row(listener)
    listener.set_input_text("f(")
    assert listener.select_for_input(presentation)
    assert isinstance(listener.python_pieces[-1], PythonChip)
    listener.python_home()
    listener.python_delete()
    listener.python_delete()
    listener.python_end()
    listener.python_backspace()
    assert listener.python_pieces == ()
    assert listener.input_mode == "empty"
    listener.cancel()
    listener.set_input_text("x = ")
    assert listener.select_for_input(presentation)
    listener.cancel()
    listener.set_input_text('"abc"')
    listener.python_home()
    listener.python_right()
    rows = listener.history.rows
    assert not listener.select_for_input(presentation)
    assert listener.history.rows == rows


def test_multiple_chips_continuation_compile_once_per_enter(tmp_path, monkeypatch):
    listener = listener_at(tmp_path)
    object_value = object()
    listener.python_namespace["v"] = object_value
    listener.python_namespace["f"] = lambda *args: args
    listener.submit("v")
    presentation = value_row(listener)
    original_compile = code.compile_command
    compiled_sources = []
    def recording_compile(source, *, symbol):
        compiled_sources.append(source)
        return original_compile(source, symbol=symbol)
    monkeypatch.setattr(code, "compile_command", recording_compile)
    listener.set_input_text("f(")
    assert listener.select_for_input(presentation)
    listener.insert_python_text(",")
    listener.submit()
    assert len(compiled_sources) == 1
    assert listener.pending_python_pieces[0][1].value is object_value
    listener.insert_python_text("    ")
    assert listener.select_for_input(presentation)
    listener.insert_python_text(")")
    listener.submit()
    assert len(compiled_sources) == 2
    assert compiled_sources[0] == "f(_pbui_chip_0,"
    assert compiled_sources[1] == "f(_pbui_chip_0,\n    _pbui_chip_1)"
    assert listener.pending_python_pieces == ()


def test_identity_duplicate_occurrences_and_temporary_cleanup(tmp_path):
    listener = listener_at(tmp_path)
    class Unusable:
        def __repr__(self):
            return "not Python!"
    original = Unusable()
    received = []
    listener.python_namespace.update(v=original, f=lambda *args: received.append(args))
    listener.submit("v")
    presentation = value_row(listener)
    listener.set_input_text("f(")
    assert listener.select_for_input(presentation)
    listener.insert_python_text(", ")
    assert listener.select_for_input(presentation)
    listener.insert_python_text(")")
    listener.submit()
    assert received == [(original, original)]
    assert received[0][0] is received[0][1]
    assert not any(key.startswith("_pbui_chip_") for key in listener.python_namespace)
    assert listener.python_namespace["_"] is original


def test_whole_identifier_collisions_and_namespace(tmp_path):
    original = object()
    chip = PythonChip(original, "x")
    namespace = {"_pbui_chip_2": "keep"}
    source, names = splice((("_pbui_chip_0 + '_pbui_chip_1' # _pbui_chip_3\n", chip),), namespace)
    assert source.endswith("_pbui_chip_4")
    assert names == {"_pbui_chip_4": original}
    source, names = splice((("_pbui_chip_01 + x_pbui_chip_0 + ", chip),), {})
    assert source.endswith("_pbui_chip_0")
    assert names == {"_pbui_chip_0": original}
    source, names = splice((("_pbui_", "chip_0 + ", chip),), {})
    assert source.endswith("_pbui_chip_1")
    assert names == {"_pbui_chip_1": original}


@pytest.mark.parametrize("tail", [
    " +",
    "; raise RuntimeError('bad')",
    "; raise SystemExit('bye')",
    "; globals().__setitem__('_pbui_' + 'chip_0', 'changed')",
])
def test_selected_names_clean_after_failures(tmp_path, tail):
    listener = listener_at(tmp_path)
    original = object()
    listener.python_namespace["v"] = original
    listener.submit("v")
    presentation = value_row(listener)
    listener.set_input_text("(")
    assert listener.select_for_input(presentation)
    listener.insert_python_text(")" + tail)
    listener.submit()
    assert "_pbui_chip_0" not in listener.python_namespace
    assert listener.python_namespace["_"] is original
    assert presentation.value is original


def test_listing_member_label_captures_complete_row(tmp_path):
    (tmp_path / "long-member-name").write_text("content")
    listener = listener_at(tmp_path)
    listener.submit(":ls")
    member = next(p for p in listener.history.presentations if p.type is listener.types.file)
    complete_row = next(
        row.text for row in layout(listener.history, 10000).rows
        if "long-member-name" in row.text
    )
    listener.set_input_text("id(")
    assert listener.select_for_input(member)
    chip = next(p for p in listener.python_pieces if isinstance(p, PythonChip))
    assert chip.value is member.value
    assert chip.label == truncate_display(complete_row, 32)


def test_existing_namespace_key_and_user_binding_survive(tmp_path):
    listener = listener_at(tmp_path)
    original = object()
    listener.python_namespace.update(v=original, _pbui_chip_0="existing")
    listener.submit("v")
    presentation = value_row(listener)
    listener.set_input_text("saved = (")
    assert listener.select_for_input(presentation)
    listener.insert_python_text(")")
    listener.submit()
    assert listener.python_namespace["saved"] is original
    assert listener.python_namespace["_pbui_chip_0"] == "existing"
    assert "_pbui_chip_1" not in listener.python_namespace


def test_cancel_discards_pending_and_current_chips(tmp_path):
    listener = listener_at(tmp_path)
    original = object()
    listener.python_namespace["v"] = original
    listener.submit("v")
    presentation = value_row(listener)
    listener.set_input_text("(")
    assert listener.select_for_input(presentation)
    listener.submit()
    assert listener.pending_python_pieces
    listener.insert_python_text(" + ")
    assert listener.select_for_input(presentation)
    rows = listener.history.rows
    namespace = listener.python_namespace.copy()
    listener.cancel_python_continuation()
    assert listener.pending_python_pieces == ()
    assert listener.python_pieces == ()
    assert listener.history.rows == rows
    assert listener.python_namespace == namespace
