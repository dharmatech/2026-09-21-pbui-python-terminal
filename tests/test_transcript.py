"""Transcript 000 headless recording and editor restoration."""

from __future__ import annotations

import code

import sympy

from pbui.chips import PythonChip
from pbui.substrate import Chip
from pbui.commands import HeadlessListener, RootedFilesystem
from pbui.transcript import CommandInput, MenuActionInput, PythonInput, input_text
from pbui.text import display_width, layout


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


def by_type(listener, presentation_type):
    return [p for p in listener.history.presentations if p.type is presentation_type]


def row_types(listener):
    return [row.presentations[0].type for row in listener.history.rows]


def drawings(listener):
    return tuple(row.text for row in layout(listener.history, 10000).rows)


def test_python_record_order_yank_and_resubmit(tmp_path):
    listener = listener_at(tmp_path)
    listener.submit("1 + 2 + 3")
    first = by_type(listener, listener.types.python_input)[0]
    assert isinstance(first.value, PythonInput)
    assert first.value.lines == (("1 + 2 + 3",),)
    assert row_types(listener) == [listener.types.python_input, listener.types.value]
    assert by_type(listener, listener.types.value)[0].value == 6
    assert drawings(listener)[0] == "› 1 + 2 + 3"
    assert listener.yank_input(first)
    assert listener.python_pieces == ("1 + 2 + 3",)
    assert len(listener.history.rows) == 2
    listener.submit()
    assert len(by_type(listener, listener.types.python_input)) == 2
    assert by_type(listener, listener.types.python_input)[0] is first
    assert row_types(listener)[-2:] == [listener.types.python_input, listener.types.value]


def test_continuation_compile_error_and_empty_cancel(tmp_path):
    listener = listener_at(tmp_path)
    listener.submit("if True:")
    assert not listener.history.rows
    listener.submit("    3")
    assert not listener.history.rows
    listener.submit("")
    assert row_types(listener) == [
        listener.types.python_input, listener.types.python_input,
        listener.types.python_input, listener.types.value
    ]
    record = by_type(listener, listener.types.python_input)[0]
    assert record.value.lines == (("if True:",), ("    3",), ())
    assert all(record in row.presentations for row in listener.history.rows[:3])
    listener.submit("if True:")
    listener.cancel_python_continuation()
    listener.submit(":")
    listener.submit("   ")
    assert len(by_type(listener, listener.types.python_input)) == 1
    listener.submit("1 +")
    assert row_types(listener)[-2:] == [listener.types.python_input, listener.types.error]


def test_command_records_text_chip_and_delayed_narrow(tmp_path):
    target = tmp_path / "target"
    target.write_text("x")
    listener = listener_at(tmp_path)
    listener.submit(":ls")
    assert isinstance(by_type(listener, listener.types.command_input)[0].value, CommandInput)
    assert row_types(listener)[0] is listener.types.command_input
    file = by_type(listener, listener.types.file)[0]
    listener.submit(":show target")
    assert by_type(listener, listener.types.command_input)[-1].value.chip is None
    listener.submit(":rm")
    assert listener.pending_request is not None
    before = len(by_type(listener, listener.types.command_input))
    assert listener.select_for_input(file, "target")
    commands = by_type(listener, listener.types.command_input)
    assert len(commands) == before + 1
    saved = commands[-1]
    assert saved.value.tail == "rm"
    assert saved.value.chip.value is file.value
    assert saved.value.chip.label == "target"
    assert not target.exists()
    assert listener.yank_input(saved)
    assert listener.input_text == ":rm"
    assert listener.chip.value is file.value
    listener.submit()
    assert by_type(listener, listener.types.command_input)[-1].value.chip.value is file.value
    listener.submit(":narrow")
    assert listener.pending_substring_listing is not None
    before = len(by_type(listener, listener.types.command_input))
    listener.set_input_text("target")
    listener.submit()
    assert len(by_type(listener, listener.types.command_input)) == before + 1
    delayed = by_type(listener, listener.types.command_input)[-1]
    assert delayed.value == CommandInput("narrow target")
    assert listener.yank_input(delayed)
    assert listener.input_text == ":narrow target"
    listener.submit()
    assert by_type(listener, listener.types.command_input)[-1] is not delayed


def test_unknown_and_malformed_record_before_error(tmp_path):
    listener = listener_at(tmp_path)
    listener.submit(":bad")
    listener.submit(":ps extra")
    assert row_types(listener) == [
        listener.types.command_input, listener.types.error,
        listener.types.command_input, listener.types.error,
    ]
    listener.submit(":rm")
    pending = by_type(listener, listener.types.command_input)[0]
    assert not listener.select_for_input(pending)
    listener.cancel()
    assert len(by_type(listener, listener.types.command_input)) == 2


def test_menu_translator_replay_after_source_eviction_and_listing_error(tmp_path):
    listener = listener_at(tmp_path, max_rows=4)
    x = sympy.Symbol("x")
    original = sympy.sin(x) ** 2 + sympy.cos(x) ** 2
    listener.python_namespace["original"] = original
    listener.submit("original")
    source = by_type(listener, listener.types.value)[0]
    result = listener.invoke_python_translator(source, 0)
    action = by_type(listener, listener.types.menu_action_input)[-1]
    assert isinstance(action.value, MenuActionInput)
    assert action.value.target is original
    assert action.value.operation is sympy.simplify
    assert result.value == sympy.Integer(1)
    assert source.value is original
    assert row_types(listener)[-2:] == [
        listener.types.menu_action_input, listener.types.value,
    ]
    listener._append_text("evict source one")
    listener._append_text("evict source two")
    assert source not in listener.history.presentations
    assert listener.run_again(action)
    assert by_type(listener, listener.types.menu_action_input)[-1] is not action
    assert by_type(listener, listener.types.value)[-1].value == result.value

    listing_listener = listener_at(tmp_path, max_rows=4)
    listing_listener.submit(":ls")
    listing = next(row.listing_owner for row in listing_listener.history.rows if row.listing_owner)
    listing_listener.apply_listing_view(listing, "sort", "name")
    listing_action = by_type(listing_listener, listing_listener.types.menu_action_input)[0]
    listing_listener._append_text("one")
    listing_listener._append_text("two")
    listing_listener._append_text("three")
    assert not listing_listener._listing_is_retained(listing)
    assert listing_action in listing_listener.history.presentations
    assert listing_listener.run_again(listing_action)
    assert row_types(listing_listener)[-2:] == [
        listing_listener.types.menu_action_input, listing_listener.types.error
    ]
    assert "no longer in history" in drawings(listing_listener)[-1]


def test_multiline_insert_preserves_pieces_cursor_and_chip_identity(tmp_path, monkeypatch):
    listener = listener_at(tmp_path)
    obj = object()
    listener.python_namespace["obj"] = obj
    listener.submit("obj")
    source = by_type(listener, listener.types.value)[-1]
    listener.submit("(")
    listener.set_input_text("")
    assert listener.select_for_input(source)
    saved_chip = listener.python_pieces[0]
    assert isinstance(saved_chip, PythonChip)
    listener.submit()
    listener.submit(")")
    saved = by_type(listener, listener.types.python_input)[-1]
    assert saved.value.lines == (("(",), (saved_chip,), (")",))

    assert listener.yank_input(saved)
    assert listener.pending_python_pieces == saved.value.lines[:-1]
    assert listener.python_pieces == (")",)
    assert listener.python_cursor == 1
    listener.cancel_python_continuation()

    listener.submit("f(")
    listener.set_input_text("preSUF")
    listener.set_python_cursor(3)
    old_rows = listener.history.rows
    monkeypatch.setattr(
        code, "compile_command",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("compiled")),
    )
    assert listener.yank_input(saved)
    assert listener.pending_python_pieces == (
        ("f(",), ("pre", "("), (saved_chip,),
    )
    assert listener.python_pieces == (")SUF",)
    assert listener.python_cursor == 1
    assert listener.history.rows == old_rows
    assert saved_chip.value is obj


def test_command_chip_python_conversion_and_incompatible_edit(tmp_path):
    target = tmp_path / "target"
    target.write_text("x")
    listener = listener_at(tmp_path)
    listener.submit(":ls")
    file = by_type(listener, listener.types.file)[0]
    listener.submit(":rm")
    assert listener.select_for_input(file, "captured label")
    saved = by_type(listener, listener.types.command_input)[-1]
    listener.set_input_text("f(")
    assert listener.yank_input(saved)
    assert listener.python_pieces[0] == "f(:rm"
    inserted = listener.python_pieces[1]
    assert isinstance(inserted, PythonChip)
    assert inserted.value is file.value
    assert inserted.label == "captured label"

    listener.cancel()
    assert listener.yank_input(saved)
    listener.set_input_text(":kill")
    listener.submit()
    assert row_types(listener)[-2:] == [
        listener.types.command_input, listener.types.error,
    ]
    assert target.exists() is False


def test_menu_action_insert_guard_and_replay_preserves_composition(tmp_path):
    listener = listener_at(tmp_path)
    x = sympy.Symbol("x")
    original = (x + 1) ** 2
    listener.python_namespace["original"] = original
    listener.submit("original")
    source = by_type(listener, listener.types.value)[-1]
    listener.invoke_python_translator(source, 1)
    action = by_type(listener, listener.types.menu_action_input)[-1]
    listener.set_input_text("f(")
    before = (listener.python_pieces, listener.python_cursor)
    assert listener.run_again(action)
    assert (listener.python_pieces, listener.python_cursor) == before
    assert by_type(listener, listener.types.menu_action_input)[-1].value is not action.value
    assert listener.select_for_input(action)
    assert isinstance(listener.python_pieces[-1], PythonChip)
    assert listener.python_pieces[-1].value is original
    listener.set_input_text('"text"')
    listener.set_python_cursor(2)
    before = listener.python_pieces
    assert not listener.select_for_input(action)
    assert listener.python_pieces == before


def test_delayed_menu_narrow_eviction_records_action_and_error(tmp_path):
    listener = listener_at(tmp_path, max_rows=4)
    listener.submit(":ls")
    listing = next(row.listing_owner for row in listener.history.rows if row.listing_owner)
    assert listener.begin_listing_narrow(listing)
    for index in range(4):
        listener._append_text(f"evict {index}")
    assert not listener._listing_is_retained(listing)
    listener.set_input_text("match")
    listener.submit()
    assert row_types(listener)[-2:] == [
        listener.types.menu_action_input, listener.types.error
    ]
    action = by_type(listener, listener.types.menu_action_input)[-1]
    assert action.value.target is listing
    assert action.value.argument == "match"
    assert "no longer in history" in drawings(listener)[-1]



def test_bounded_python_drawing_preserves_newlines_unicode_and_chip_identity(tmp_path):
    listener = listener_at(tmp_path)
    original = object()
    chip = PythonChip(original, "wide 界 e\u0301\\\t")
    saved_lines = (
        ("x" * 117 + "界e\u0301" + "\\", chip, "\nnext\tline"),
        *(("line " + str(index),) for index in range(11)),
    )
    saved = listener._record_python(saved_lines)
    rows = listener.history.rows
    assert saved.value.lines == saved_lines
    assert len(rows) == 12
    assert all(row.presentations == (saved,) for row in rows)
    drawn = drawings(listener)
    assert drawn[0] == "› " + "x" * 117
    assert drawn[1].startswith("› 界e\u0301\\\\⟨wide 界 e\u0301\\\\\\t⟩")
    assert "› next\\tline" in drawn
    assert drawn[-1] == "› … (3 more input rows)"
    assert all(row.startswith("› ") and display_width(row) <= 120 for row in drawn)
    narrow = layout(listener.history, 17)
    assert all(
        narrow.hit_test(interval.start_column, interval.physical_row) is saved
        for interval in saved.intervals
    )
    assert listener.yank_input(saved)
    assert listener.pending_python_pieces == saved_lines[:-1]
    assert listener.python_pieces == saved_lines[-1]
    assert listener.pending_python_pieces[0][1].value is original


def test_single_input_rows_are_capped_without_changing_records(tmp_path):
    listener = listener_at(tmp_path)
    original = object()
    command = CommandInput("rm " + "z" * 150, Chip(listener.types.file, original, "L" * 50))
    action = MenuActionInput(
        "narrow", lambda *_: None, "S" * 150, original, "界" * 80,
        "listing", "narrow",
    )
    command_row = input_text(command)
    action_row = input_text(action)
    assert len(command_row) == len(action_row) == 1
    assert command_row[0].endswith("…")
    assert action_row[0].endswith("…")
    assert display_width(command_row[0]) <= 120
    assert display_width(action_row[0]) <= 120
    assert command.tail.endswith("z" * 150)
    assert command.chip.value is original
    assert action.argument == "S" * 150
    assert action.target_label == "界" * 80
    target_only = MenuActionInput(
        "show", lambda *_: None, None, original, "界" * 80, "member"
    )
    assert display_width(input_text(target_only)[0].split(" — ", 1)[1]) <= 96
    saved_command = listener._record_command(command.tail, command.chip)
    assert listener.yank_input(saved_command)
    assert listener.input_text == ":" + command.tail
    assert listener.chip is command.chip
    unsafe_target = MenuActionInput(
        "show", lambda *_: None, None, original, "line\nnext\x1b", "member"
    )
    assert input_text(unsafe_target) == ("› show — line\\nnext\\x1b",)
    assert input_text(CommandInput("ls")) == ("› :ls",)
    assert input_text(CommandInput("ls /tmp")) == ("› :ls /tmp",)
    assert input_text(CommandInput("rm", Chip(listener.types.file, original, "/tmp/a"))) == (
        "› :rm ⟨File: /tmp/a⟩",
    )



def test_each_drawn_input_row_counts_toward_history_limit(tmp_path):
    listener = listener_at(tmp_path, max_rows=4)
    saved = listener._record_python(tuple((f"row-{index}",) for index in range(6)))
    assert len(listener.history.rows) == 4
    assert [row.text for row in layout(listener.history, 80).rows] == [
        "› row-2", "› row-3", "› row-4", "› row-5",
    ]
    assert all(row.presentations == (saved,) for row in listener.history.rows)
    assert saved.value.lines[0] == ("row-0",)
