from dataclasses import FrozenInstanceError

import pytest

from pbui.substrate import (
    AcceptRequest,
    DisplayInterval,
    Presentation,
    PresentationHistory,
    PresentationTypeRegistry,
    SubstrateState,
    TranslatorTable,
)
from pbui.text import DrawingContext, HistoryRow, hit_test, layout


def one_type(name: str = "Alpha"):
    return PresentationTypeRegistry().register(name)


def retain(row):
    history = PresentationHistory()
    history.append(row)
    return history


def owned(row, listing_owner):
    return HistoryRow(row.fragments, row.presentations, listing_owner)


def history_snapshot(history):
    return (
        tuple((id(row), id(row.listing_owner)) for row in history.rows),
        tuple(
            (presentation_id, id(presentation), presentation.intervals)
            for presentation_id, presentation in history._presentations.items()
        ),
        tuple(history._reference_counts.items()),
        history.revision,
    )


def test_type_registration_is_explicit_immutable_and_identity_based():
    first_registry = PresentationTypeRegistry()
    second_registry = PresentationTypeRegistry()
    alpha = first_registry.register("Alpha")
    same_spelling = second_registry.register("Alpha")

    assert first_registry.lookup("Alpha") is alpha
    assert alpha is not same_spelling
    assert alpha != same_spelling
    with pytest.raises(ValueError, match="already registered"):
        first_registry.register("Alpha")
    with pytest.raises(FrozenInstanceError):
        alpha.name = "changed"
    with pytest.raises(ValueError, match="nonempty"):
        first_registry.register("")


def test_presentation_retains_original_value_and_stable_id_before_layout():
    alpha = one_type()
    value = object()
    context = DrawingContext()
    context.register_drawer(alpha, lambda item, _context: "shown")

    row = context.present_row(value, alpha)
    presentation = row.presentations[0]

    assert presentation.value is value
    assert presentation.presentation_type is alpha
    assert presentation.id == row.fragments[0].presentation_id
    assert presentation.intervals == ()


def test_drawers_build_standalone_composed_and_nested_presentations():
    registry = PresentationTypeRegistry()
    outer = registry.register("Outer")
    inner = registry.register("Inner")
    context = DrawingContext()
    context.register_drawer(inner, lambda item, _context: item["name"])
    context.register_drawer(
        outer,
        lambda item, current: ("<", current.present(item["inner"], inner), ">"),
    )
    value = {"inner": {"name": "deep name"}}

    standalone = context.present_row(value["inner"], inner)
    composed = context.row("name: ", context.present(value["inner"], inner))
    nested = context.present_row(value, outer)

    assert len(standalone.presentations) == 1
    assert len(composed.presentations) == 1
    assert [item.presentation_type for item in nested.presentations] == [outer, inner]
    with pytest.raises(ValueError, match="already registered"):
        context.register_drawer(inner, lambda _item, _context: "other")
    with pytest.raises(KeyError, match="no drawer"):
        DrawingContext().present(value, inner)


def test_nested_hit_testing_prefers_inner_and_literals_and_padding_miss():
    registry = PresentationTypeRegistry()
    outer = registry.register("Outer")
    inner = registry.register("Inner")
    context = DrawingContext()
    context.register_drawer(inner, lambda item, _context: item)
    context.register_drawer(
        outer, lambda item, current: ("<", current.present(item, inner), ">")
    )
    row = context.row("kind ", context.present("deep", outer), " tail")
    history = retain(row)

    result = layout(history, 40)
    outer_presentation, inner_presentation = row.presentations

    assert result.hit_test(6, 0) is inner_presentation
    assert result.hit_test(5, 0) is outer_presentation
    assert result.hit_test(1, 0) is None
    assert result.hit_test(12, 0) is None
    assert result.hit_test(39, 0) is None


def test_same_depth_overlap_resolves_to_last_drawn():
    alpha = one_type("Alpha")
    beta = one_type("Beta")
    first = Presentation(
        1, alpha, object(), (DisplayInterval(0, 0, 3, 0, 1),)
    )
    second = Presentation(
        2, beta, object(), (DisplayInterval(0, 1, 2, 0, 2),)
    )

    assert hit_test((first, second), 1, 0) is second

    # Equal metadata still follows drawing/iteration order for malformed input.
    second.replace_intervals((DisplayInterval(0, 1, 2),))
    first.replace_intervals((DisplayInterval(0, 0, 3),))
    assert hit_test((first, second), 1, 0) is second


def test_interval_ends_are_exclusive_and_invalid_coordinates_miss():
    alpha = one_type()
    context = DrawingContext()
    context.register_drawer(alpha, lambda _item, _context: "abc")
    result = layout(retain(context.present_row(object(), alpha)), 3)

    assert result.hit_test(2, 0) is not None
    assert result.hit_test(3, 0) is None
    assert result.hit_test(-1, 0) is None
    assert result.hit_test(0, -1) is None
    assert result.hit_test(0, 1) is None


def test_spaces_stay_inside_one_presentation_and_neighboring_literals_do_not():
    alpha = one_type()
    context = DrawingContext()
    context.register_drawer(alpha, lambda item, _context: item)
    row = context.row("[", context.present("a name here", alpha), "]")
    result = layout(retain(row), 30)
    presentation = row.presentations[0]

    assert result.hit_test(1, 0) is presentation
    assert result.hit_test(2, 0) is presentation
    assert result.hit_test(7, 0) is presentation
    assert result.hit_test(0, 0) is None
    assert result.hit_test(12, 0) is None


def test_wide_and_combining_characters_use_display_columns_and_wide_wraps():
    alpha = one_type()
    context = DrawingContext()
    context.register_drawer(alpha, lambda item, _context: item)
    row = context.present_row("Ae\u0301界Z", alpha)
    history = retain(row)

    unwrapped = layout(history, 20)
    presentation = row.presentations[0]
    assert unwrapped.rows[0].text == "Ae\u0301界Z"
    assert unwrapped.rows[0].display_width == 5
    assert [(span.start_column, span.end_column) for span in presentation.intervals] == [
        (0, 5)
    ]

    wrapping_context = DrawingContext()
    wrapping_context.register_drawer(alpha, lambda _item, _context: "a界")
    wrapping_row = wrapping_context.present_row(object(), alpha)
    wrapped = layout(retain(wrapping_row), 2)
    assert [physical.text for physical in wrapped.rows] == ["a", "界"]
    assert [
        (span.physical_row, span.start_column, span.end_column)
        for span in wrapping_row.presentations[0].intervals
    ] == [(0, 0, 1), (1, 0, 2)]


def test_wrapped_presentation_has_row_intervals_not_a_bounding_rectangle():
    alpha = one_type()
    context = DrawingContext()
    context.register_drawer(alpha, lambda _item, _context: "abcde")
    row = context.present_row(object(), alpha)
    result = layout(retain(row), 3)
    presentation = row.presentations[0]

    assert [(item.physical_row, item.start_column, item.end_column) for item in presentation.intervals] == [
        (0, 0, 3),
        (1, 0, 2),
    ]
    assert result.hit_test(1, 1) is presentation
    assert result.hit_test(2, 1) is None


def test_zero_width_is_normalized_to_one_and_oversized_codepoint_is_placed_once():
    alpha = one_type()
    context = DrawingContext()
    context.register_drawer(alpha, lambda _item, _context: "界")
    row = context.present_row(object(), alpha)

    result = layout(retain(row), 0)

    assert result.width == 1
    assert [physical.text for physical in result.rows] == ["界"]
    assert row.presentations[0].intervals[0].start_column == 0
    assert row.presentations[0].intervals[0].end_column == 2


def test_relayout_replaces_intervals_but_preserves_presentation_and_value():
    alpha = one_type()
    value = object()
    context = DrawingContext()
    context.register_drawer(alpha, lambda _item, _context: "abcd")
    row = context.present_row(value, alpha)
    history = retain(row)
    presentation = row.presentations[0]

    first = layout(history, 4)
    first_intervals = presentation.intervals
    second = layout(history, 2)

    assert history.lookup(presentation.id) is presentation
    assert presentation.value is value
    assert first_intervals == (DisplayInterval(0, 0, 4, 0, 4),)
    assert [(span.physical_row, span.start_column, span.end_column) for span in presentation.intervals] == [
        (0, 0, 2),
        (1, 0, 2),
    ]
    assert second.hit_test(0, 1) is presentation
    assert first.hit_test(0, 0) is presentation


def test_history_retains_500_logical_rows_regardless_of_wrapping():
    alpha = one_type()
    context = DrawingContext()
    context.register_drawer(alpha, lambda _item, _context: "xy")
    history = PresentationHistory()
    first_row = context.present_row("xy", alpha)
    first_presentation = first_row.presentations[0]
    history.append(first_row)

    for number in range(1, 501):
        history.append(context.present_row(number, alpha))

    result = layout(history, 1)

    assert len(history) == 500
    assert len(result.rows) == 1000
    assert history.get_presentation(first_presentation.id) is None
    assert first_presentation.intervals == ()
    assert result.hit_test(0, 0) is history.rows[0].presentations[0]


def test_history_row_owner_is_optional_and_owned_append_uses_identity():
    class EqualOwner:
        __hash__ = None

        def __init__(self):
            self.comparisons = 0

        def __eq__(self, _other):
            self.comparisons += 1
            return True

    first_owner = EqualOwner()
    equal_but_distinct_owner = EqualOwner()
    context = DrawingContext()
    unowned = context.row("unowned")
    first = owned(context.row("first"), first_owner)
    second = owned(context.row("second"), first_owner)
    other = owned(context.row("other"), equal_but_distinct_owner)
    history = PresentationHistory()

    assert HistoryRow(unowned.fragments, unowned.presentations).listing_owner is None
    history.append(first)
    history.append(second)
    history.append(other)
    history.append(unowned)
    before_rejected_append = history_snapshot(history)

    with pytest.raises(ValueError, match="contiguous"):
        history.append(owned(context.row("reopened"), first_owner))

    assert history_snapshot(history) == before_rejected_append
    assert history.rows == (first, second, other, unowned)
    assert first_owner.comparisons == 0
    assert equal_but_distinct_owner.comparisons == 0


def test_replace_listing_rows_preserves_position_objects_and_references():
    alpha = one_type()
    context = DrawingContext()
    context.register_drawer(alpha, lambda item, _context: item)
    owner = object()

    shared_fragment = context.present("shared", alpha)
    before = context.row("before ", shared_fragment)
    header = owned(context.present_row("header", alpha), owner)
    retained_member = owned(context.present_row("retained", alpha), owner)
    shared_member = owned(context.row("member ", shared_fragment), owner)
    removed_member = owned(context.present_row("removed", alpha), owner)
    after = context.present_row("after", alpha)
    history = PresentationHistory()
    for row in (before, header, retained_member, shared_member, removed_member, after):
        history.append(row)

    stale_layout = layout(history, 80)
    revision = history.revision
    shared_presentation = before.presentations[0]
    removed_presentation = removed_member.presentations[0]
    replacement_header = HistoryRow(
        header.fragments, header.presentations, listing_owner=owner
    )
    replacement_member = HistoryRow(
        retained_member.fragments,
        retained_member.presentations,
        listing_owner=owner,
    )

    history.replace_listing_rows(owner, (replacement_header, replacement_member))

    assert history.rows == (before, replacement_header, replacement_member, after)
    assert history.rows[0] is before
    assert history.rows[1] is replacement_header
    assert history.rows[2] is replacement_member
    assert history.rows[3] is after
    assert history.lookup(header.presentations[0].id) is header.presentations[0]
    assert header.presentations[0].value == "header"
    assert (
        history.lookup(retained_member.presentations[0].id)
        is retained_member.presentations[0]
    )
    assert retained_member.presentations[0].value == "retained"
    assert history.lookup(shared_presentation.id) is shared_presentation
    assert history._reference_counts[shared_presentation.id] == 1
    assert history.get_presentation(removed_presentation.id) is None
    assert removed_presentation.intervals == ()
    assert all(presentation.intervals == () for presentation in history.presentations)
    assert history.revision == revision + 1
    assert stale_layout.hit_test(7, 0) is None

    refreshed_layout = layout(history, 80)
    assert any(presentation.intervals for presentation in history.presentations)
    assert refreshed_layout.hit_test(7, 0) is shared_presentation

    longer_rows = (
        replacement_header,
        replacement_member,
        owned(context.present_row("new one", alpha), owner),
        owned(context.present_row("new two", alpha), owner),
    )
    revision = history.revision
    history.replace_listing_rows(owner, iter(longer_rows))

    assert history.rows == (before, *longer_rows, after)
    assert history.rows[0] is before
    assert history.rows[-1] is after
    assert all(
        history.rows[index + 1] is row for index, row in enumerate(longer_rows)
    )
    assert history.revision == revision + 1


def test_replace_listing_rows_validation_failures_are_atomic():
    alpha = one_type()
    context = DrawingContext()
    context.register_drawer(alpha, lambda item, _context: item)
    owner = object()
    other_owner = object()
    missing_owner = object()
    shared_fragment = context.present("shared", alpha)
    outside = context.row("outside ", shared_fragment)
    target = owned(context.row("target ", shared_fragment), owner)
    trailing = context.present_row("trailing", alpha)
    history = PresentationHistory()
    for row in (outside, target, trailing):
        history.append(row)
    layout(history, 80)

    valid_replacement = HistoryRow(
        target.fragments, target.presentations, listing_owner=owner
    )
    failures = (
        (
            KeyError,
            lambda: history.replace_listing_rows(
                missing_owner, (valid_replacement,)
            ),
        ),
        (
            ValueError,
            lambda: history.replace_listing_rows(None, (valid_replacement,)),
        ),
        (ValueError, lambda: history.replace_listing_rows(owner, ())),
        (
            ValueError,
            lambda: history.replace_listing_rows(owner, (context.row("plain"),)),
        ),
        (
            ValueError,
            lambda: history.replace_listing_rows(
                owner, (owned(context.row("foreign"), other_owner),)
            ),
        ),
        (
            ValueError,
            lambda: history.replace_listing_rows(
                owner,
                (HistoryRow(target.fragments, (), listing_owner=owner),),
            ),
        ),
        (
            ValueError,
            lambda: history.replace_listing_rows(
                owner,
                (
                    HistoryRow(
                        target.fragments,
                        (
                            Presentation(
                                target.presentations[0].id,
                                alpha,
                                "different object",
                            ),
                        ),
                        owner,
                    ),
                ),
            ),
        ),
    )

    for error, operation in failures:
        before_failure = history_snapshot(history)
        with pytest.raises(error):
            operation()
        assert history_snapshot(history) == before_failure

    history._rows.append(owned(context.row("reopened target"), owner))
    before_failure = history_snapshot(history)
    with pytest.raises(ValueError, match="not contiguous"):
        history.replace_listing_rows(owner, (valid_replacement,))
    assert history_snapshot(history) == before_failure


def test_listing_replacement_enforces_row_bound_after_one_revision_change():
    alpha = one_type()
    context = DrawingContext()
    context.register_drawer(alpha, lambda item, _context: item)
    owner = object()
    history = PresentationHistory(max_rows=4)
    before = context.present_row("before", alpha)
    first = owned(context.present_row("first", alpha), owner)
    second = owned(context.present_row("second", alpha), owner)
    after = context.present_row("after", alpha)
    for row in (before, first, second, after):
        history.append(row)

    layout(history, 80)
    old_presentations = tuple(history.presentations)
    replacements = tuple(
        owned(context.present_row(f"replacement {number}", alpha), owner)
        for number in range(5)
    )
    revision = history.revision

    history.replace_listing_rows(owner, replacements)

    assert len(history) == 4
    assert history.rows == (*replacements[-3:], after)
    assert history.rows[0] is replacements[-3]
    assert history.rows[-1] is after
    assert history.revision == revision + 1
    assert all(presentation.intervals == () for presentation in history.presentations)
    assert all(presentation.intervals == () for presentation in old_presentations)

    history.append(context.present_row("later one", alpha))
    history.append(context.present_row("later two", alpha))
    history.append(context.present_row("later three", alpha))
    assert all(row.listing_owner is not owner for row in history.rows)
    before_missing_replacement = history_snapshot(history)
    with pytest.raises(KeyError):
        history.replace_listing_rows(owner, replacements)
    assert history_snapshot(history) == before_missing_replacement


def test_oldest_row_eviction_leaves_listing_tail_replaceable():
    owner = object()
    context = DrawingContext()
    history = PresentationHistory(max_rows=3)
    rows = tuple(owned(context.row(f"owned {number}"), owner) for number in range(3))
    for row in rows:
        history.append(row)
    outside = context.row("outside")
    history.append(outside)

    assert history.rows == (rows[1], rows[2], outside)
    replacement = owned(context.row("replacement"), owner)
    revision = history.revision
    history.replace_listing_rows(owner, (replacement,))

    assert history.rows == (replacement, outside)
    assert history.rows[0] is replacement
    assert history.rows[1] is outside
    assert history.revision == revision + 1


def test_accept_matching_is_atomic_and_nonmatching_leaves_all_state_unchanged():
    registry = PresentationTypeRegistry()
    alpha = registry.register("Alpha")
    beta = registry.register("Beta")
    value = object()
    calls = []
    state = SubstrateState(input_text="untouched")
    request = AcceptRequest("choose", frozenset({alpha}), calls.append)
    state.begin_accept(request)

    assert not state.select_presentation(Presentation(1, beta, object()), "wrong")
    assert state.pending_request is request
    assert state.input_text == "untouched"
    assert state.chip is None
    assert calls == []

    presentation = Presentation(2, alpha, value)
    assert state.select_presentation(presentation, "many character label")
    assert state.pending_request is None
    assert state.chip is calls[0]
    assert state.chip.value is value
    assert state.chip.presentation_type is alpha
    assert state.input_text == "untouched"
    assert len(calls) == 1
    assert not state.select_presentation(presentation, "again")
    assert len(calls) == 1


def test_cancel_and_backspace_treat_chip_as_one_atomic_value():
    alpha = one_type()
    state = SubstrateState(chip=None)
    state.begin_accept(AcceptRequest("choose", frozenset({alpha}), lambda _chip: None))

    state.select_presentation(Presentation(1, alpha, object()), "several letters")
    assert state.backspace()
    assert state.chip is None
    assert not state.backspace()

    state.begin_accept(AcceptRequest("choose", frozenset({alpha}), lambda _chip: None))
    state.select_presentation(Presentation(2, alpha, object()), "another label")
    state.begin_accept(AcceptRequest("choose", frozenset({alpha}), lambda _chip: None))
    state.cancel()
    assert state.pending_request is None
    assert state.chip is None


def test_translators_are_empty_explicit_exact_and_receive_original_value():
    class Parent:
        pass

    class Child(Parent):
        pass

    first_registry = PresentationTypeRegistry()
    second_registry = PresentationTypeRegistry()
    alpha = first_registry.register("Alpha")
    equal_name = second_registry.register("Alpha")
    beta = first_registry.register("Beta")
    value = Child()
    calls = []
    table = TranslatorTable()

    assert table.lookup(alpha) is None
    assert table.invoke(Presentation(1, alpha, value)) is None
    table.register(alpha, lambda item: calls.append(item) or "translated")

    assert table.invoke(Presentation(2, alpha, value)) == "translated"
    assert calls == [value]
    assert calls[0] is value
    assert table.lookup(equal_name) is None
    assert table.lookup(beta) is None
    assert table.invoke(Presentation(3, equal_name, value)) is None
    with pytest.raises(ValueError, match="already registered"):
        table.register(alpha, lambda _item: None)
