"""Headless membership checks for history 000."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from pbui.commands import HeadlessListener, InspectedProcess, RootedFilesystem
from pbui.http import JsonArray, JsonObject
from pbui.repl import ValueTranslator
from pbui.substrate import Presentation, PresentationHistory, PresentationType
from pbui.text import (
    HistoryRow,
    LiteralFragment,
    is_transcript_input,
    layout,
    row_indents,
    stored_row_text,
)


@dataclass
class FixedProcesses:
    own_uid: int = 1000
    own_pid: int = 700

    def list_for_uid(self, _uid):
        return (InspectedProcess(17, 1000, "sleeping", "worker"),)

    def inspect(self, _pid):
        return InspectedProcess(17, 1000, "sleeping", "worker")

    def send_sigterm(self, _pid):
        raise AssertionError("history tests do not signal processes")


def listener_at(tmp_path, **kwargs):
    return HeadlessListener(
        str(tmp_path),
        RootedFilesystem(tmp_path),
        FixedProcesses(),
        username_lookup=lambda _uid: "owner",
        **kwargs,
    )


def literal(text, *, owner=None, group=None):
    return HistoryRow((LiteralFragment(text),), listing_owner=owner, group_id=group)


def text_rows(history):
    return tuple(stored_row_text(row) for row in history.rows)


def newest(listener, presentation_type):
    return next(
        item for item in reversed(listener.history.presentations)
        if item.type is presentation_type
    )


def test_operation_identity_nesting_exception_and_empty_context():
    history = PresentationHistory()
    direct = literal("direct")
    history.append(direct)
    assert history.rows[0] is direct
    assert direct.group_id is None
    assert not row_indents(direct)
    tagged = literal("caller tagged", group=41)
    separate = PresentationHistory()
    separate.append(tagged)
    assert separate.rows[0] is tagged and tagged.group_id == 41

    with history.operation():
        first = literal("first", group=77)
        history.append(first)
        with history.operation():
            second = literal("second")
            history.append(second)
        assert first.group_id == second.group_id == 1
        with pytest.raises(ValueError, match="nested"):
            with history.operation():
                raise ValueError("nested")
        still_open = literal("still open")
        history.append(still_open)
        assert still_open.group_id == 1
        with pytest.raises(RuntimeError, match="already open"):
            history._open_group()
    assert first.group_id == 1
    assert history.rows[1] is first
    with pytest.raises(RuntimeError, match="no history group"):
        history._close_group()

    with history.operation():
        pass
    with pytest.raises(ZeroDivisionError):
        with history.operation():
            failed = literal("failed")
            history.append(failed)
            1 / 0
    with history.operation():
        after = literal("after")
        history.append(after)
    assert [row.group_id for row in history.rows] == [None, 1, 1, 1, 3, 4]
    assert literal("after", group=99) == after
    assert row_indents(after)
    assert text_rows(history) == (
        "direct", "first", "second", "still open", "failed", "after"
    )


def test_input_predicate_checks_every_presentation_type_name():
    result = Presentation(1, PresentationType("Value"), 6)
    input_item = Presentation(2, PresentationType("PythonInput"), "source")
    row = HistoryRow((), (result, input_item), group_id=1)
    assert is_transcript_input(row)
    assert not row_indents(row)


def test_replacements_transfer_group_without_retagging_or_moving_listing():
    history = PresentationHistory()
    owner = object()
    with history.operation():
        before = literal("before")
        header = literal("header", owner=owner)
        member = literal("member", owner=owner)
        for row in (before, header, member):
            history.append(row)
    old_group = header.group_id
    with history.operation():
        action = literal("action")
        history.append(action)
        replacement = literal("replacement", group=999)
        history.replace_row(before, replacement)
        replacements = (
            literal("new header", owner=owner, group=999),
            literal("new member", owner=owner),
        )
        history.replace_listing_rows(owner, replacements)
        assert action.group_id != old_group
        assert replacement.group_id == old_group
        assert all(row.group_id == old_group for row in replacements)
    assert history.rows == (replacement, *replacements, action)
    assert history.rows[1] is replacements[0]
    assert text_rows(history) == ("replacement", "new header", "new member", "action")

    mixed = PresentationHistory()
    mixed.append(literal("header", owner=owner, group=1))
    mixed.append(literal("member", owner=owner, group=2))
    snapshot = mixed.rows
    with pytest.raises(ValueError, match="share one group"):
        mixed.replace_listing_rows(owner, (literal("new", owner=owner),))
    assert mixed.rows == snapshot


def test_eviction_keeps_surviving_ids_and_does_not_merge_groups(tmp_path):
    listener = listener_at(tmp_path, history_max_rows=3)
    listener.submit("1 + 1")
    first_id = listener.history.rows[-1].group_id
    listener.submit("2 + 2")
    assert text_rows(listener.history) == ("int 2", "› 2 + 2", "int 4")
    assert [row.group_id for row in listener.history.rows] == [
        first_id, first_id + 1, first_id + 1
    ]
    assert row_indents(listener.history.rows[0])
    assert not is_transcript_input(listener.history.rows[0])


def test_python_input_value_empty_output_and_one_row_cd(tmp_path):
    (tmp_path / "child").mkdir()
    listener = listener_at(tmp_path)
    listener.submit("1 + 2 + 3")
    input_row, value_row = listener.history.rows
    assert text_rows(listener.history) == ("› 1 + 2 + 3", "int 6")
    assert input_row.group_id == value_row.group_id == 1
    assert is_transcript_input(input_row) and not row_indents(input_row)
    assert not is_transcript_input(value_row) and row_indents(value_row)

    listener.submit("print()")
    assert text_rows(listener.history)[-2:] == ("› print()", "")
    assert listener.history.rows[-1].group_id == listener.history.rows[-2].group_id
    assert row_indents(listener.history.rows[-1])

    before = len(listener.history)
    listener.submit(":cd child")
    assert len(listener.history) == before + 1
    cd_row = listener.history.rows[-1]
    assert is_transcript_input(cd_row)
    listener.submit("7")
    assert cd_row.group_id != listener.history.rows[-2].group_id
    assert listener.history.rows[-2].group_id == listener.history.rows[-1].group_id
    assert text_rows(listener.history)[-3:] == ("› :cd child", "› 7", "int 7")


def test_tutorial_navigation_and_no_append_paths(tmp_path):
    listener = listener_at(tmp_path)
    listener.submit(":tutorial")
    first = newest(listener, listener.types.tutorial_card)
    first_rows = listener.history.rows
    first_id = first_rows[0].group_id
    assert all(row.group_id == first_id for row in first_rows)
    assert is_transcript_input(first_rows[0])
    assert all(row_indents(row) for row in first_rows[1:])

    next_control = next(
        presentation for row in first_rows for presentation in row.presentations
        if presentation.type is listener.types.tutorial_target
        and presentation.value.direction == "Next"
    )
    assert listener.select_for_input(next_control)
    card_two = listener.history.rows[len(first_rows):]
    assert card_two and len(listener.history) == len(first_rows) + len(card_two)
    assert len({row.group_id for row in card_two}) == 1
    assert card_two[0].group_id != first_id
    assert all(row_indents(row) and not is_transcript_input(row) for row in card_two)

    try_control = next(
        presentation for row in first_rows for presentation in row.presentations
        if presentation.type is listener.types.tutorial_try
    )
    snapshot = listener.history.rows
    assert listener.select_for_input(try_control)
    assert listener.history.rows == snapshot
    listener.submit()
    assert listener.history.rows != snapshot

    snapshot = listener.history.rows
    listener.submit("")
    assert listener.history.rows == snapshot
    listener.submit("if True:")
    assert listener.history.rows == snapshot
    listener.cancel()
    assert listener.history.rows == snapshot
    listener.submit(":show")
    assert listener.history.rows == snapshot
    listener.cancel()
    assert listener.history.rows == snapshot


def test_listing_redisplay_menu_error_and_click_to_show(tmp_path):
    (tmp_path / "file").write_text("data")
    listener = listener_at(tmp_path)
    listener.submit(":ls")
    initial = listener.history.rows
    listing = next(row.listing_owner for row in initial if row.listing_owner is not None)
    listing_id = initial[0].group_id
    listing_rows = tuple(row for row in initial if row.listing_owner is listing)
    assert len(listing_rows) >= 2
    assert all(row.group_id == listing_id and row_indents(row) for row in listing_rows)
    assert not row_indents(initial[0])

    assert listener.apply_listing_view(listing, "sort", "size")
    sorted_rows = tuple(row for row in listener.history.rows if row.listing_owner is listing)
    action = listener.history.rows[-1]
    assert len(sorted_rows) == len(listing_rows)
    assert all(row.group_id == listing_id for row in sorted_rows)
    assert is_transcript_input(action)
    assert action.group_id != listing_id
    assert listener.history.rows[1:1 + len(sorted_rows)] == sorted_rows

    assert not listener.apply_listing_view(listing, "sort", "bad")
    bad_action, error = listener.history.rows[-2:]
    assert bad_action.group_id == error.group_id
    assert bad_action.group_id != action.group_id
    assert is_transcript_input(bad_action) and row_indents(error)
    assert all(row.group_id == listing_id for row in listener.history.rows if row.listing_owner is listing)
    assert text_rows(listener.history)[-1] == "Error: cannot sort this directory listing by bad."

    file_presentation = next(
        presentation for row in sorted_rows for presentation in row.presentations
        if presentation.type is listener.types.file
    )
    before = len(listener.history)
    assert listener.select_for_input(file_presentation)
    detail_rows = listener.history.rows[before:]
    assert len(detail_rows) == 1
    assert detail_rows[0].group_id != listing_id
    assert row_indents(detail_rows[0])
    assert text_rows(listener.history)[-1].startswith(f"path: {tmp_path / 'file'}")


def test_json_dig_trailer_detail_translator_and_process_fake(tmp_path):
    listener = listener_at(tmp_path)
    values = JsonArray(range(101))
    listener.python_namespace["values"] = values
    listener.submit("values")
    source = listener.history.rows[-1]
    before = len(listener.history)
    assert listener.dig_json(source.presentations[0])
    dig_rows = listener.history.rows[before:]
    assert len(dig_rows) == 101
    assert len({row.group_id for row in dig_rows}) == 1
    assert dig_rows[0].group_id != source.group_id
    assert all(row_indents(row) for row in dig_rows)
    assert text_rows(listener.history)[-1] == "… (1 more members)"

    listener.python_namespace["empty"] = JsonObject()
    listener.submit("empty")
    snapshot = listener.history.rows
    assert listener.dig_json(snapshot[-1].presentations[0])
    assert listener.history.rows == snapshot

    listener.submit("42")
    value = listener.history.rows[-1].presentations[0]
    before = len(listener.history)
    assert listener.select_for_input(value)
    assert all(row_indents(row) for row in listener.history.rows[before:])
    assert listener.history.rows[-1].group_id != listener.history.rows[before - 1].group_id

    listener.submit(":ps")
    process = next(
        p for p in listener.history.presentations if p.type is listener.types.process
    )
    listing_id = next(
        row.group_id for row in listener.history.rows if process in row.presentations
    )
    assert listener.select_for_input(process)
    assert listener.history.rows[-1].group_id != listing_id
    assert row_indents(listener.history.rows[-1])


def test_translator_member_replay_and_wide_layout_keep_stored_text(tmp_path):
    (tmp_path / "file").write_text("data")
    listener = listener_at(tmp_path)
    listener.register_python_class(
        int, lambda value: f"int {value}",
        (ValueTranslator("double", lambda value: value * 2),),
    )
    listener.submit("5")
    value = listener.history.rows[-1].presentations[0]
    before = len(listener.history)
    listener.invoke_python_translator(value, 0)
    action, result = listener.history.rows[before:]
    assert is_transcript_input(action)
    assert action.group_id == result.group_id
    assert row_indents(result)
    assert text_rows(listener.history)[-1] == "int 10"

    assert listener.run_again(action.presentations[0])
    replay_action, replay_result = listener.history.rows[-2:]
    assert replay_action.group_id == replay_result.group_id != action.group_id

    listener.submit(":ls")
    file_presentation = next(
        p for p in listener.history.presentations if p.type is listener.types.file
    )
    before = len(listener.history)
    assert listener.execute_stored_member(file_presentation, "show")
    member_action, detail = listener.history.rows[before:]
    assert member_action.group_id == detail.group_id
    assert is_transcript_input(member_action)
    assert row_indents(detail)

    picture = layout(listener.history, 10_000)
    assert tuple(
        row.text for row in picture.rows if row.logical_row is None
    ) == ("",) * 4
    assert all(
        row.text == (
            ("  " if row_indents(listener.history.rows[row.logical_row]) else "")
            + text_rows(listener.history)[row.logical_row]
        )
        for row in picture.rows if row.logical_row is not None
    )


def test_tutorial_tour_layout_has_group_gaps_and_result_indent(tmp_path):
    (tmp_path / "sample").write_text("data")
    listener = listener_at(tmp_path)
    listener.submit(":tutorial")
    first_try = newest(listener, listener.types.tutorial_try)
    first_next = next(
        item for item in listener.history.presentations
        if item.type is listener.types.tutorial_target
        and item.value.direction == "Next"
    )
    assert listener.select_for_input(first_try)
    listener.submit()
    assert listener.select_for_input(first_next)
    second_try = newest(listener, listener.types.tutorial_try)
    second_next = next(
        item for item in reversed(listener.history.presentations)
        if item.type is listener.types.tutorial_target
        and item.value.direction == "Next"
    )
    assert listener.select_for_input(second_try)
    listener.submit()
    assert listener.select_for_input(second_next)

    stored = listener.history.rows
    picture = layout(listener.history, 120)
    expected = []
    previous_group = None
    for index, row in enumerate(stored):
        if previous_group is not None and row.group_id != previous_group:
            expected.append(("", None))
        expected.append(
            (("  " if row_indents(row) else "") + stored_row_text(row), index)
        )
        previous_group = row.group_id
    assert [(row.text, row.logical_row) for row in picture.rows] == expected
    assert sum(row.logical_row is None for row in picture.rows) == 4
    assert picture.rows[0].text == "› :tutorial"
    assert any(row.text == "  int 6" for row in picture.rows)
    assert any(row.text.startswith("  name") for row in picture.rows)
    value_y = next(i for i, row in enumerate(picture.rows) if row.text == "  int 6")
    assert picture.rows[value_y + 1].logical_row is None
    assert picture.rows[value_y + 2].text.startswith("  2. Colon commands")
    file_y = next(i for i, row in enumerate(picture.rows) if row.text.startswith("  sample"))
    assert picture.rows[file_y + 1].logical_row is None
    assert picture.rows[file_y + 2].text.startswith("  3. Reuse a value")
    file = next(
        item for item in listener.history.presentations
        if item.type is listener.types.file
    )
    assert picture.hit_test(0, file_y) is None
    assert picture.hit_test(1, file_y) is None
    assert picture.hit_test(2, file_y) is file
    assert picture.hit_test(2, value_y + 1) is None


def test_wrapped_indent_narrow_fallback_and_ungrouped_rows():
    from pbui.text import DrawingContext

    history = PresentationHistory()
    context = DrawingContext()
    kind = PresentationType("Item")
    context.register_drawer(kind, lambda value, _context: value)
    with history.operation():
        grouped = context.present_row("Ae\u0301界" * 8, kind)
        history.append(grouped)

    narrow = layout(history, 17)
    assert len(narrow.rows) > 1
    assert all(row.text.startswith("  ") for row in narrow.rows)
    assert "".join(row.text[2:] for row in narrow.rows) == stored_row_text(grouped)
    assert all(interval.start_column >= 2 for interval in grouped.presentations[0].intervals)
    for y, row in enumerate(narrow.rows):
        assert narrow.hit_test(0, y) is None
        assert narrow.hit_test(1, y) is None
        assert narrow.hit_test(2, y) is grouped.presentations[0]
        assert row.display_width <= 17

    flush = layout(history, 2)
    assert all(not row.text.startswith("  ") for row in flush.rows)
    assert flush.rows[0].logical_row == 0
    assert flush.hit_test(0, 0) is grouped.presentations[0]
    wide = PresentationHistory()
    with wide.operation():
        wide.append(context.present_row("界", kind))
    assert layout(wide, 3).rows[0].text == "  界"

    ungrouped = literal("loose")
    history.append(ungrouped)
    with history.operation():
        history.append(literal("next"))
    rows = layout(history, 120).rows
    assert [(row.text, row.logical_row) for row in rows] == [
        ("  " + stored_row_text(grouped), 0),
        ("loose", 1),
        ("  next", 2),
    ]


def test_eviction_and_stored_empty_line_are_distinct_from_separator(tmp_path):
    listener = listener_at(tmp_path, history_max_rows=3)
    listener.submit("1 + 1")
    listener.submit("2 + 2")
    picture = layout(listener.history, 80)
    assert [(row.text, row.logical_row) for row in picture.rows] == [
        ("  int 2", 0),
        ("", None),
        ("› 2 + 2", 1),
        ("  int 4", 2),
    ]
    assert picture.hit_test(0, 1) is None

    listener = listener_at(tmp_path)
    listener.submit("print()")
    listener.submit("3")
    picture = layout(listener.history, 80)
    assert [(row.text, row.logical_row) for row in picture.rows] == [
        ("› print()", 0),
        ("  ", 1),
        ("", None),
        ("› 3", 2),
        ("  int 3", 3),
    ]
