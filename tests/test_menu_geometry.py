"""Pure terminal-cell placement and hit testing for the popup."""

from pbui.menu_geometry import CellRect, measure_menu, opening_anchor, place_menu


def test_bordered_measurement_middle_edge_shifts_and_no_fit():
    bounds = CellRect(4, 2, 30, 10)
    labels = ("show", "rm")
    assert measure_menu(labels) == (8, 4)

    middle = place_menu(labels, bounds, (12, 4))
    assert middle is not None
    assert middle.rect == CellRect(12, 4, 8, 4)
    assert middle.row_text(4) == "┌──────┐"
    assert middle.row_text(5) == "│ show │"
    assert middle.row_text(6) == "│ rm   │"
    assert middle.row_text(7) == "└──────┘"
    assert middle.item_at(13, 5) == 0
    assert middle.item_at(18, 6) == 1
    assert middle.item_at(12, 5) is None
    assert middle.item_at(13, 4) is None

    right = place_menu(labels, bounds, (32, 4))
    assert right is not None
    assert right.rect == CellRect(26, 4, 8, 4)
    assert right.anchor == (32, 4)

    shifted = place_menu(labels, bounds, (32, 10))
    assert shifted is not None
    assert shifted.rect == CellRect(26, 8, 8, 4)
    assert shifted.item_at(32, 10) == 1
    assert shifted.item_at(32, 11) is None

    assert place_menu(tuple(str(index) for index in range(9)), bounds, (10, 3)) is None


def test_ctrl_o_anchor_uses_pointer_only_on_target_and_visible_fallback():
    cells = ((16, 8), (3, 6), (8, 6))
    assert opening_anchor((15, 8), True, cells) == (15, 8)
    assert opening_anchor((15, 8), False, cells) == (3, 6)
    assert opening_anchor(None, False, cells) == (3, 6)
    assert opening_anchor((15, 8), False, ()) is None
