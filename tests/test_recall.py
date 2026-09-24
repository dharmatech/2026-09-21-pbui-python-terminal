"""Headless recall of submitted Python forms and colon commands."""

from __future__ import annotations

import pytest
import sympy

from pbui.chips import PythonChip
from pbui.commands import HeadlessListener, RootedFilesystem
from pbui.transcript import CommandInput, PythonInput


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


def presentations(listener, presentation_type):
    return tuple(
        item for item in listener.history.presentations
        if item.type is presentation_type
    )


def test_mixed_order_duplicates_boundaries_and_committed_value_identity(tmp_path):
    listener = listener_at(tmp_path)
    assert listener.recall_entries == ()
    assert listener.recall_position is None
    assert not listener.recall_previous()
    assert not listener.recall_next()

    listener.submit(":ls")
    listener.submit("2 + 3")
    listener.submit(":tutorial")
    listener.submit(":ls")
    entries = listener.recall_entries
    assert entries == (
        CommandInput("ls"), PythonInput((("2 + 3",),)),
        CommandInput("tutorial"), CommandInput("ls"),
    )
    assert entries[0] is not entries[3]
    committed = [
        item.value for item in listener.history.presentations
        if item.type in (listener.types.python_input, listener.types.command_input)
    ]
    assert all(entry is value for entry, value in zip(entries, committed, strict=True))
    with pytest.raises(AttributeError):
        entries.append(CommandInput("extra"))

    listener.set_input_text("unfinished")
    for index in (3, 2, 1, 0):
        assert listener.recall_previous()
        assert listener.recall_position == index
    assert listener.input_text == ":ls"
    assert not listener.recall_previous()
    assert listener.recall_position == 0
    for index in (1, 2, 3):
        assert listener.recall_next()
        assert listener.recall_position == index
    assert listener.recall_next()
    assert listener.recall_position is None
    assert listener.input_text == "unfinished"
    assert not listener.recall_next()


def test_multiline_python_chip_and_continuation_draft_copy(tmp_path):
    listener = listener_at(tmp_path)
    target = object()
    listener.python_namespace["target"] = target
    listener.submit("target")
    value = presentations(listener, listener.types.value)[-1]
    listener.submit("(")
    listener.set_input_text("")
    assert listener.select_for_input(value)
    chip = listener.python_pieces[0]
    assert isinstance(chip, PythonChip)
    listener.submit()
    listener.submit(")")
    saved = listener.recall_entries[-1]
    assert isinstance(saved, PythonInput)
    assert saved.lines == (("(",), (chip,), (")",))

    listener.submit("for n in range(2):")
    listener.set_input_text("    n")
    listener.set_python_cursor(4)
    pending = listener.pending_python_pieces
    pieces = listener.python_pieces
    assert listener.recall_previous()
    assert listener.pending_python_pieces == saved.lines[:-1]
    assert listener.pending_python_pieces[1][0] is chip
    assert listener.python_pieces == saved.lines[-1]
    assert listener.python_cursor == 1
    assert listener.recall_next()
    assert listener.pending_python_pieces == pending
    assert listener.python_pieces == pieces
    assert listener.python_cursor == 4
    listener.insert_python_text("+ 1")
    assert listener.python_pieces == ("    + 1n",)


def test_python_draft_chip_and_midline_cursor_restore(tmp_path):
    listener = listener_at(tmp_path)
    target = object()
    listener.python_namespace["target"] = target
    listener.submit("target")
    value = presentations(listener, listener.types.value)[-1]
    listener.set_input_text("f()")
    listener.set_python_cursor(2)
    assert listener.select_for_input(value)
    draft_chip = listener.python_pieces[1]
    assert isinstance(draft_chip, PythonChip)
    listener.set_python_cursor(1)
    draft_pieces = listener.python_pieces
    assert listener.recall_previous()
    assert listener.python_pieces == ("target",)
    assert listener.recall_next()
    assert listener.python_pieces == draft_pieces
    assert listener.python_pieces[1] is draft_chip
    assert listener.python_cursor == 1


def test_command_chip_loaded_state_and_midline_command_caret(tmp_path):
    (tmp_path / "target").write_text("x")
    listener = listener_at(tmp_path)
    listener.submit(":ls")
    file = presentations(listener, listener.types.file)[0]
    listener.submit(":show")
    assert listener.pending_request is not None
    assert listener.select_for_input(file, "captured")
    saved = listener.recall_entries[-1]
    assert isinstance(saved, CommandInput)
    assert saved.chip is not None
    assert saved.chip.value is file.value
    assert saved.chip.label == "captured"

    assert listener.recall_previous()
    assert listener.input_text == ":show"
    assert listener.chip is saved.chip
    assert listener.command_cursor == len(":show")
    assert listener.recall_previous()
    assert listener.chip is None
    assert listener.recall_next()
    assert listener.chip is saved.chip
    assert listener.recall_next()

    saved_presentation = presentations(listener, listener.types.command_input)[-1]
    assert listener.yank_input(saved_presentation)
    listener.set_command_cursor(2)
    assert listener.command_cursor == 2
    assert listener.recall_previous()
    assert listener.command_cursor == len(":show")
    assert listener.recall_next()
    assert listener.input_text == ":show"
    assert listener.command_cursor == 2
    assert listener.chip is saved.chip
    listener.submit()
    newest = listener.recall_entries[-1]
    assert isinstance(newest, CommandInput)
    assert newest.chip is saved.chip
    assert newest is not saved
    assert listener.recall_position is None

    listener.set_input_text(":longer")
    assert listener.command_cursor == len(":longer")
    with pytest.raises(ValueError):
        listener.set_command_cursor(-1)
    with pytest.raises(ValueError):
        listener.set_command_cursor(100)
    with pytest.raises(ValueError):
        listener.set_command_cursor(True)


def test_edit_discard_edited_submission_and_incomplete_continuation(tmp_path):
    listener = listener_at(tmp_path)
    listener.submit("1")
    listener.submit("2")
    source = listener.recall_entries[-1]
    listener.set_input_text("draft")
    assert listener.recall_previous()
    listener.set_input_text("200")
    assert listener.recall_previous()
    assert listener.input_text == "1"
    assert listener.recall_next()
    assert listener.input_text == "2"
    listener.set_input_text("22")
    listener.submit()
    assert listener.recall_entries[-2] is source
    assert source.lines == (("2",),)
    assert listener.recall_entries[-1] == PythonInput((("22",),))
    assert listener.recall_position is None
    assert not listener.recall_next()

    assert listener.recall_previous()
    position = listener.recall_position
    count = len(listener.recall_entries)
    listener.submit("if True:")
    assert listener.pending_python_pieces == (("if True:",),)
    assert listener.recall_position == position
    assert len(listener.recall_entries) == count
    assert listener.recall_previous()
    assert listener.pending_python_pieces == ()
    assert listener.input_text == "2"


def test_modal_guards_and_delayed_records(tmp_path):
    listener = listener_at(tmp_path)
    listener.submit(":ls")
    listing = next(row.listing_owner for row in listener.history.rows if row.listing_owner)
    file_path = tmp_path / "target"
    file_path.write_text("x")
    listener.submit(":ls")
    file = presentations(listener, listener.types.file)[-1]
    listener.set_input_text("draft")
    assert listener.recall_previous()
    snapshot = (listener.input_text, listener.command_cursor, listener.recall_entries,
                listener.recall_position)
    assert not listener.recall_previous(menu_open=True)
    assert not listener.recall_next(menu_open=True)
    assert (listener.input_text, listener.command_cursor, listener.recall_entries,
            listener.recall_position) == snapshot
    assert listener.recall_next()
    assert listener.input_text == "draft"

    assert listener.recall_previous()
    position = listener.recall_position
    count = len(listener.recall_entries)
    listener.submit(":show")
    assert listener.pending_request is not None
    assert listener.recall_position == position
    assert len(listener.recall_entries) == count
    listener.set_input_text("waiting")
    snapshot = (listener.input_text, listener.command_cursor, listener.recall_position)
    assert not listener.recall_previous()
    assert not listener.recall_next()
    assert (listener.input_text, listener.command_cursor, listener.recall_position) == snapshot
    assert listener.select_for_input(file)
    assert len(listener.recall_entries) == count + 1
    assert listener.recall_position is None
    assert listener.recall_entries[-1].chip.value is file.value

    assert listener.begin_listing_narrow(listing)
    listener.set_input_text("partial")
    snapshot = (listener.input_text, listener.command_cursor, listener.recall_position)
    assert not listener.recall_previous()
    assert not listener.recall_next()
    assert (listener.input_text, listener.command_cursor, listener.recall_position) == snapshot
    listener.cancel()

    listener.submit(":narrow")
    assert listener.pending_substring_listing is not None
    count = len(listener.recall_entries)
    listener.set_input_text("tar")
    assert not listener.recall_previous()
    listener.submit()
    assert len(listener.recall_entries) == count + 1
    assert listener.recall_entries[-1] == CommandInput("narrow tar")


def test_yank_try_and_noninput_actions(tmp_path):
    listener = listener_at(tmp_path)
    listener.submit("6")
    saved_python = presentations(listener, listener.types.python_input)[0]
    value = presentations(listener, listener.types.value)[0]
    count = len(listener.recall_entries)
    assert listener.select(value)
    assert len(listener.recall_entries) == count

    assert listener.recall_previous()
    listener.set_input_text(":show")
    assert not listener.yank_input(saved_python)
    assert listener.recall_position == 0
    listener.set_input_text("f()")
    listener.set_python_cursor(2)
    assert listener.yank_input(saved_python)
    assert listener.recall_position is None
    assert listener.python_pieces == ("f(6)",)
    assert not listener.recall_next()
    assert len(listener.recall_entries) == count

    listener.cancel()
    listener.submit(":tutorial")
    try_control = next(
        item for item in listener.history.presentations
        if item.type is listener.types.tutorial_try
    )
    assert listener.recall_previous()
    assert not listener.load_tutorial_example(try_control)
    assert listener.recall_position is not None
    listener.set_input_text("")
    assert listener.load_tutorial_example(try_control)
    assert listener.recall_position is None
    assert len(listener.recall_entries) == count + 1


def test_menu_action_and_show_click_do_not_enter_ring(tmp_path):
    listener = listener_at(tmp_path)
    listener.python_namespace["x"] = sympy.Symbol("x")
    listener.submit("x + 1")
    value = presentations(listener, listener.types.value)[-1]
    count = len(listener.recall_entries)
    listener.invoke_python_translator(value, 0)
    action = presentations(listener, listener.types.menu_action_input)[-1]
    assert len(listener.recall_entries) == count
    assert listener.run_again(action)
    assert len(listener.recall_entries) == count
    assert listener.select(value)
    assert len(listener.recall_entries) == count


def test_transcript_eviction_and_ring_overflow_are_independent(tmp_path):
    listener = listener_at(tmp_path, max_rows=2)
    listener.submit(":badfirst")
    first = presentations(listener, listener.types.command_input)[0]
    listener._append_text("evict one")
    listener._append_text("evict two")
    assert first not in listener.history.presentations
    assert listener.recall_previous()
    assert listener.input_text == ":badfirst"
    assert listener.recall_next()

    for index in range(400):
        listener.submit(f":bad{index}")
    entries = listener.recall_entries
    assert len(entries) == 400
    assert entries[0] == CommandInput("bad0")
    assert entries[-1] == CommandInput("bad399")
    assert all(entry == CommandInput(f"bad{index}")
               for index, entry in enumerate(entries))
    assert listener.recall_previous()
    assert listener.input_text == ":bad399"
