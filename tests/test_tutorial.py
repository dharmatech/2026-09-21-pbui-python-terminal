"""Headless tutorial data, drawing, and selection."""

from __future__ import annotations

import os
import socket
import subprocess
from dataclasses import FrozenInstanceError

import pytest

from pbui.commands import HeadlessListener, RootedFilesystem
from pbui.domain import escape_display
from pbui.text import layout
from pbui.transcript import CommandInput, PythonInput
from pbui.tutorial import (
    TutorialCard,
    TutorialLink,
    append_tutorial_card,
    make_tutorial_stack,
)


class NoProcesses:
    def list_for_uid(self, _uid):
        raise AssertionError("tutorial must not list processes")

    def inspect(self, _pid):
        raise AssertionError("tutorial must not inspect processes")

    def send_sigterm(self, _pid):
        raise AssertionError("tutorial must not signal processes")


def make_listener(tmp_path):
    def no_transport(_request):
        raise AssertionError("tutorial must not use the network")

    return HeadlessListener(
        str(tmp_path), RootedFilesystem(tmp_path), NoProcesses(),
        get_transport=no_transport,
    )


def text_rows(listener):
    return tuple(row.text for row in layout(listener.history, 200).rows)


def card_rows(listener, outer):
    return tuple(
        row for row in listener.history.rows
        if row.presentations and row.presentations[0] is outer
    )


def control(listener, outer, direction):
    matches = [
        presentation
        for row in card_rows(listener, outer)
        for presentation in row.presentations[1:]
        if presentation.type is listener.types.tutorial_target
        and presentation.value.direction == direction
    ]
    assert len(matches) == 1
    return matches[0]


def try_control(listener, outer):
    matches = [
        presentation
        for row in card_rows(listener, outer)
        for presentation in row.presentations[1:]
        if presentation.type is listener.types.tutorial_try
    ]
    assert len(matches) == 1
    return matches[0]


def latest_card(listener):
    return next(
        presentation for presentation in reversed(listener.history.presentations)
        if presentation.type is listener.types.tutorial_card
    )


def transcript(listener):
    input_types = {
        listener.types.python_input,
        listener.types.command_input,
        listener.types.menu_action_input,
    }
    return tuple(
        item for item in listener.history.presentations if item.type in input_types
    )


def test_exact_immutable_stack_and_pure_construction(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("stack construction performed I/O")

    with monkeypatch.context() as patch:
        patch.setattr(os, "stat", forbidden)
        patch.setattr(os, "scandir", forbidden)
        patch.setattr(socket, "create_connection", forbidden)
        patch.setattr(subprocess, "Popen", forbidden)
        stack = make_tutorial_stack()

    assert tuple(card.identifier for card in stack.tour) == (
        "presentations", "commands", "values", "menus", "yank"
    )
    assert tuple(card.title for card in stack.tour) == (
        "1. Presentations", "2. Colon commands", "3. Reuse a value",
        "4. The right-button menu", "5. Bring input back",
    )
    assert tuple(card.body for card in stack.tour) == (
        (
            "History keeps an object together with the text you see.",
            "Run 1 + 2 + 3 to get a value holding 6.",
            "At an empty prompt, click that value to show its detail.",
            "Try loads the line; Enter runs it.",
        ),
        (
            "Commands start with a colon in the same editor.",
            "Use :ls to list the current directory.",
            "The results keep file and directory objects you can click.",
            "Try loads :ls; Enter lists the directory.",
        ),
        (
            "Run the first card's example so 6 is in history.",
            "Type 10 + , then click the 6 result.",
            "The editor inserts a chip for that exact object.",
            "Press Enter to evaluate the completed expression.",
        ),
        (
            "Point at a history object and read the documentation line.",
            "Right-click an object with actions to open its menu.",
            "Choose an item to run it; Esc or Ctrl-G closes the menu.",
            "The action uses the object you pointed at.",
        ),
        (
            "A submitted Python form or colon command stays in history.",
            "At an empty prompt, click its input row to load it again.",
            "Edit the line if you like; Enter submits it.",
            "Right-click the row and choose yank for the same load.",
        ),
    )
    assert stack.tour[0].examples[0].saved_input == PythonInput((("1 + 2 + 3",),))
    assert stack.tour[1].examples[0].saved_input == CommandInput("ls")
    assert tuple(card.examples for card in stack.tour[2:]) == ((), (), ())
    assert stack.contents.title == "Contents"
    assert stack.contents.body == ("Choose a card to append it to history.",)
    assert all(entry is card for entry, card in zip(stack.contents.entries, stack.tour))
    assert tuple(card.previous.destination_id for card in stack.tour) == (
        None, "presentations", "commands", "values", "menus"
    )
    assert tuple(card.next.destination_id for card in stack.tour) == (
        "commands", "values", "menus", "yank", None
    )
    assert all(card.contents.destination_id == "contents" for card in stack.tour)
    assert stack.contents.previous is stack.contents.next is stack.contents.contents is None
    with pytest.raises(FrozenInstanceError):
        stack.tour[0].title = "Changed"


def test_command_records_then_appends_fresh_card_without_replacing_history(tmp_path):
    listener = make_listener(tmp_path)
    listener.submit("40 + 2")
    old_rows = listener.history.rows
    old_text = text_rows(listener)

    listener.submit(":tutorial")
    first = latest_card(listener)
    assert listener.history.rows[:len(old_rows)] == old_rows
    assert text_rows(listener)[:len(old_text)] == old_text
    assert transcript(listener)[-1].value == CommandInput("tutorial")
    assert listener.history.rows[len(old_rows)].presentations[0] is transcript(listener)[-1]
    assert first.value is listener.tutorial_stack.tour[0]
    assert len(card_rows(listener, first)) == 7
    assert tuple(row.text for row in layout(listener.history, 200).rows)[-7:] == (
        "1. Presentations",
        *listener.tutorial_stack.tour[0].body,
        "[Try] 1 + 2 + 3",
        "[Back]  [Next]  [Up: Contents]",
    )
    assert all(row.presentations[0] is first for row in card_rows(listener, first))
    before = listener.history.rows

    listener.submit(":tutorial")
    second = latest_card(listener)
    assert second is not first and second.value is first.value
    assert listener.history.rows[:len(before)] == before
    assert transcript(listener)[-1].value == CommandInput("tutorial")
    assert len(transcript(listener)) == 3

    count = len(listener.history)
    listener.submit(":tutorial extra")
    assert len(listener.history) == count + 2
    assert latest_card(listener) is second
    assert text_rows(listener)[-1] == "Error: tutorial does not take an argument."


def test_nested_hits_navigation_and_disabled_boundaries(tmp_path):
    listener = make_listener(tmp_path)
    listener.submit(":tutorial")
    first = latest_card(listener)
    back = control(listener, first, "Back")
    assert back.value.destination is None
    before = listener.history.rows
    assert not listener.select_for_input(back)
    assert listener.history.rows == before

    drawing = layout(listener.history, 80)
    assert drawing.hit_test(0, 0).type is listener.types.command_input
    first_title_y = next(i for i, row in enumerate(drawing.rows) if row.text == first.value.title)
    assert drawing.hit_test(0, first_title_y) is first
    nav_y = next(i for i, row in enumerate(drawing.rows) if row.text.startswith("[Back]"))
    assert drawing.hit_test(1, nav_y) is back
    assert drawing.hit_test(6, nav_y) is first
    assert drawing.hit_test(9, nav_y) is control(listener, first, "Next")

    count = len(transcript(listener))
    assert listener.select_for_input(control(listener, first, "Next"))
    second = latest_card(listener)
    assert second.value is listener.tutorial_stack.tour[1]
    assert len(transcript(listener)) == count
    assert listener.select_for_input(control(listener, second, "Back"))
    assert latest_card(listener).value is first.value
    assert listener.select_for_input(control(listener, second, "Up"))
    contents = latest_card(listener)
    assert contents.value is listener.tutorial_stack.contents
    assert len(card_rows(listener, contents)) == 7
    assert text_rows(listener)[-5:] == tuple(f"[{card.title}]" for card in listener.tutorial_stack.tour)
    entry = next(
        item for row in card_rows(listener, contents) for item in row.presentations[1:]
        if item.value.destination is listener.tutorial_stack.tour[3]
    )
    assert listener.select_for_input(entry)
    assert latest_card(listener).value is listener.tutorial_stack.tour[3]
    last = listener.append_tutorial_card(listener.tutorial_stack.tour[-1])
    next_control = control(listener, last, "Next")
    assert next_control.value.destination is None
    before = listener.history.rows
    assert not listener.select_for_input(next_control)
    assert listener.history.rows == before


def test_navigation_preserves_composition_accept_and_substring_state(tmp_path):
    listener = make_listener(tmp_path)
    listener.submit(":tutorial")
    first = latest_card(listener)
    next_control = control(listener, first, "Next")
    listener.set_input_text("10 + 20")
    listener.set_python_cursor(3)
    before = (listener.input_text, listener.python_pieces, listener.python_cursor,
              listener.pending_python_pieces, transcript(listener))
    assert listener.select_for_input(next_control)
    assert (listener.input_text, listener.python_pieces, listener.python_cursor,
            listener.pending_python_pieces, transcript(listener)) == before

    listener.set_input_text("[")
    listener.submit()
    assert listener.pending_python_pieces
    listener.set_input_text("4 + 5")
    listener.set_python_cursor(2)
    before = (listener.input_text, listener.python_pieces, listener.python_cursor,
              listener.pending_python_pieces, transcript(listener))
    assert listener.select_for_input(next_control)
    assert (listener.input_text, listener.python_pieces, listener.python_cursor,
            listener.pending_python_pieces, transcript(listener)) == before

    listener.cancel_python_continuation()
    listener.submit(":show")
    request = listener.pending_request
    listener.set_input_text("waiting")
    cursor = listener.python_cursor
    assert request is not None
    assert listener.select_for_input(next_control)
    assert listener.pending_request is request
    assert listener.input_text == "waiting" and listener.python_cursor == cursor

    listener.cancel()
    listener.submit(":ls")
    listing = next(row.listing_owner for row in listener.history.rows
                   if row.listing_owner is not None)
    assert listener.begin_listing_narrow(listing)
    pending = listener.pending_substring_listing
    listener.set_input_text("partial")
    cursor = listener.python_cursor
    assert listener.select_for_input(next_control)
    assert listener.pending_substring_listing is pending
    assert listener.input_text == "partial" and listener.python_cursor == cursor


def test_ordinary_value_and_input_yank_still_select_with_cards(tmp_path):
    listener = make_listener(tmp_path)
    listener.submit("6")
    value = next(item for item in listener.history.presentations
                 if item.type is listener.types.value)
    saved_input = next(item for item in listener.history.presentations
                       if item.type is listener.types.python_input)
    listener.submit(":tutorial")
    listener.set_input_text("10 + ")
    assert listener.select_for_input(value, "6")
    assert listener.python_pieces[-1].value == 6
    listener.cancel()
    assert listener.select_for_input(saved_input)
    assert listener.python_pieces == ("6",)
    assert listener.input_text == "6"


def test_try_loads_exact_editable_pieces_only_at_empty_prompt(tmp_path):
    listener = make_listener(tmp_path)
    listener.submit(":tutorial")
    first = latest_card(listener)
    example = try_control(listener, first)
    before = (listener.history.rows, transcript(listener))
    assert listener.select_for_input(example)
    assert listener.python_pieces == ("1 + 2 + 3",)
    assert listener.python_cursor == len("1 + 2 + 3")
    assert listener.input_text == "1 + 2 + 3"
    assert (listener.history.rows, transcript(listener)) == before
    listener.set_python_cursor(0)
    listener.insert_python_text("0 + ")
    assert listener.input_text == "0 + 1 + 2 + 3"
    listener.submit()
    assert isinstance(transcript(listener)[-1].value, PythonInput)

    second = listener.append_tutorial_card(listener.tutorial_stack.tour[1])
    command_example = try_control(listener, second)
    before = listener.history.rows
    assert listener.select_for_input(command_example)
    assert listener.input_text == ":ls"
    assert listener.python_pieces == (":ls",)
    assert listener.python_cursor == 3
    assert listener.history.rows == before
    listener.set_input_text(":ls .")
    assert listener.input_text == ":ls ."


@pytest.mark.parametrize("busy", ("text", "chip", "continuation", "accept", "substring"))
def test_try_refuses_busy_editor_without_changes(tmp_path, busy):
    listener = make_listener(tmp_path)
    listener.submit(":tutorial")
    example = try_control(listener, latest_card(listener))
    if busy == "text":
        listener.set_input_text(":ps")
    elif busy == "chip":
        listener.submit("6")
        value = next(item for item in listener.history.presentations
                     if item.type is listener.types.value)
        listener.set_input_text("10 + ")
        assert listener.insert_python_chip(value)
    elif busy == "continuation":
        listener.set_input_text("[")
        listener.submit()
    elif busy == "accept":
        listener.submit(":show")
    else:
        listener.submit(":ls")
        listing = next(row.listing_owner for row in listener.history.rows
                       if row.listing_owner is not None)
        listener.begin_listing_narrow(listing)
    before = (listener.input_text, listener.python_pieces, listener.python_cursor,
              listener.pending_python_pieces, listener.pending_request,
              listener.pending_substring_listing, listener.history.rows)
    assert not listener.select_for_input(example)
    assert (listener.input_text, listener.python_pieces, listener.python_cursor,
            listener.pending_python_pieces, listener.pending_request,
            listener.pending_substring_listing, listener.history.rows) == before


def test_long_card_cuts_at_twenty_rows_without_losing_data(tmp_path):
    listener = make_listener(tmp_path)
    long_body = ("wide 水" * 30, "unsafe\nline", *(f"line {i}" for i in range(25)))
    card = TutorialCard(
        "synthetic", "Synthetic", long_body,
        previous=TutorialLink("Back", None),
        next=TutorialLink("Next", None),
        contents=TutorialLink("Up", "contents"),
    )
    outer = append_tutorial_card(
        listener.history, listener.drawing_contexts.standalone,
        listener.types, listener.tutorial_stack, card,
    )
    rows = card_rows(listener, outer)
    assert len(rows) == 20
    assert outer.value is card and outer.value.body == long_body
    drawn = tuple(row.text for row in layout(listener.history, 200).rows)
    assert drawn[0] == "Synthetic"
    assert "… (card text cut)" in drawn[-2]
    assert drawn[-1] == "[Back]  [Next]  [Up: Contents]"
    assert escape_display("unsafe\nline") == "unsafe\\nline"
