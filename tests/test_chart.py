"""Headless daily chart capture, retained drawing, and direct selection."""

from __future__ import annotations

import subprocess

import pandas as pd
import pytest
import yfinance as yf

from pbui.chart import Candle, capture_chart, chart_rows, price_row
from pbui.chips import PythonChip
from pbui.bottom import format_documentation
from pbui.commands import HeadlessListener, RootedFilesystem
from pbui.terminal import build_history_text, presentation_style
from pbui.text import display_width, layout, stored_row_text
from pbui.transcript import MenuActionInput
from rich.console import Console


class EmptyProcesses:
    pass


class TickerStandIn(yf.Ticker):
    def __init__(self, symbol: str = "AAPL") -> None:
        self.ticker = symbol

    def __repr__(self) -> str:
        return "ticker stand-in"


def frame_for(count: int = 3) -> pd.DataFrame:
    dates = pd.date_range("2026-09-01", periods=count, name="Date")
    return pd.DataFrame(
        {
            "Open": [10.0 + i for i in range(count)],
            "High": [12.0 + i for i in range(count)],
            "Low": [9.0 + i for i in range(count)],
            "Close": [11.0 + i for i in range(count)],
        },
        index=dates,
    )


def listener_at(tmp_path, seam, *, max_rows=500):
    return HeadlessListener(
        str(tmp_path), RootedFilesystem(tmp_path), EmptyProcesses(),
        ticker_history=seam, history_max_rows=max_rows,
    )


def present_ticker(listener, ticker):
    listener.python_namespace["ticker"] = ticker
    listener.submit("ticker")
    return next(
        presentation for presentation in reversed(listener.history.presentations)
        if presentation.type is listener.types.value
    )


def chart_rows_in(listener, chart_presentation):
    return tuple(
        row for row in listener.history.rows
        if chart_presentation in row.presentations
    )


def test_capture_exact_ticker_once_and_isolate_snapshot(tmp_path):
    frame = frame_for(17)
    later_frame = frame_for(1)
    calls = []

    def history(ticker):
        calls.append(ticker)
        return frame if len(calls) == 1 else later_frame

    listener = listener_at(tmp_path, history)
    ticker = TickerStandIn()
    source = present_ticker(listener, ticker)
    chart_presentation = listener.run_ticker_chart(source)
    assert chart_presentation is not None
    chart = chart_presentation.value
    assert calls == [ticker]
    assert chart.symbol == "AAPL"
    assert len(chart.bars) == 17
    assert len(chart.visible_candles) == 15
    assert chart.omitted_count == 2
    assert chart.visible_candles[0].date == "2026-09-03"
    assert chart.visible_candles[-1].date == "2026-09-17"
    assert chart.visible_candles == tuple(
        Candle(f"2026-09-{day:02d}", float(day + 9), float(day + 11),
               float(day + 8), float(day + 10))
        for day in range(3, 18)
    )
    assert stored_row_text(chart_rows_in(listener, chart_presentation)[-1]).strip() == "… (2 more days)"
    assert len(chart_rows_in(listener, chart_presentation)) == 16
    assert sum(
        presentation.type is listener.types.candle
        for presentation in listener.history.presentations
    ) == 15
    assert listener.python_namespace["_"] is chart
    assert listener.history.get_presentation(source.id) is source
    assert all(presentation.value is not frame for presentation in listener.history.presentations)
    frame.iloc[:, :] = -999.0
    assert chart.visible_candles[0] == Candle("2026-09-03", 12.0, 14.0, 11.0, 13.0)
    assert listener.run_ticker_history(source).value is later_frame
    assert chart.visible_candles[0] == Candle("2026-09-03", 12.0, 14.0, 11.0, 13.0)

    other = listener_at(tmp_path, history, max_rows=3)
    stale = present_ticker(other, TickerStandIn())
    other.submit("1")
    other.submit("2")
    assert other.run_ticker_chart(stale) is None
    non_ticker = next(
        presentation for presentation in reversed(other.history.presentations)
        if presentation.type is other.types.value
    )
    assert other.run_ticker_chart(non_ticker) is None
    assert calls == [ticker, ticker]


@pytest.mark.parametrize(
    "change",
    [
        lambda frame: frame.iloc[:0],
        lambda frame: frame.drop(columns="Close"),
        lambda frame: frame.set_axis([0, 1, 2]),
        lambda frame: frame.set_axis(pd.DatetimeIndex(["2026-09-01", pd.NaT, "2026-09-03"])),
        lambda frame: frame.assign(Open=[pd.NA, 11.0, 12.0]),
        lambda frame: frame.assign(High=[float("inf"), 13.0, 14.0]),
        lambda frame: frame.assign(Low=[13.0, 10.0, 11.0]),
        lambda frame: frame.assign(Close=[13.0, 12.0, 13.0]),
    ],
    ids=["empty", "missing-column", "non-date-index", "nat", "missing-price", "nonfinite", "reversed-range", "outside-range"],
)
def test_invalid_prices_append_one_text_row_and_preserve_last_value(tmp_path, change):
    calls = []
    frame = change(frame_for())
    listener = listener_at(tmp_path, lambda ticker: calls.append(ticker) or frame)
    ticker = TickerStandIn()
    source = present_ticker(listener, ticker)
    before = len(listener.history.rows)
    assert listener.run_ticker_chart(source) is None
    assert calls == [ticker]
    assert len(listener.history.rows) == before + 1
    row = listener.history.rows[-1]
    assert row.presentations[0].type is listener.types.text
    assert stored_row_text(row) == "no prices"
    assert listener.python_namespace["_"] is ticker
    assert listener.history.get_presentation(source.id) is source
    assert all(p.type is not listener.types.chart for p in listener.history.presentations)


def test_raised_seam_adds_one_error_and_preserves_last_value(tmp_path):
    def fail(_ticker):
        raise RuntimeError("Yahoo unavailable")

    listener = listener_at(tmp_path, fail)
    ticker = TickerStandIn()
    source = present_ticker(listener, ticker)
    before = len(listener.history.rows)
    assert listener.run_ticker_chart(source) is None
    assert len(listener.history.rows) == before + 1
    row = listener.history.rows[-1]
    assert row.presentations[0].type is listener.types.error
    assert stored_row_text(row).startswith("Error: Traceback")
    assert stored_row_text(row).endswith("RuntimeError: Yahoo unavailable")
    assert listener.python_namespace["_"] is ticker
    assert listener.history.get_presentation(source.id) is source


def test_sort_directions_and_fixed_price_geometry():
    frame = pd.DataFrame(
        {
            "Open": [10.0, 18.0, 10.0],
            "High": [20.0, 20.0, 20.0],
            "Low": [0.0, 0.0, 0.0],
            "Close": [15.0, 5.0, 10.0],
        },
        index=pd.DatetimeIndex(["2026-09-03", "2026-09-01", "2026-09-02"]),
    )
    chart = capture_chart("AAPL", frame)
    assert [c.date for c in chart.bars] == ["2026-09-01", "2026-09-02", "2026-09-03"]
    assert [c.close >= c.open for c in chart.visible_candles] == [False, True, True]
    assert price_row(20.0, 0.0, 20.0) == 0
    assert price_row(0.0, 0.0, 20.0) == 11
    assert price_row(10.0, 0.0, 20.0) == 6
    assert price_row(0.0, -1e308, 1e308) == 6


def test_rising_and_falling_ticks_use_left_open_and_right_close(tmp_path):
    frame = pd.DataFrame(
        {"Open": [10.0, 15.0], "High": [20.0, 20.0],
         "Low": [0.0, 0.0], "Close": [15.0, 10.0]},
        index=pd.DatetimeIndex(["2026-09-21", "2026-09-22"]),
    )
    listener = listener_at(tmp_path, lambda _ticker: frame)
    chart = listener.run_ticker_chart(present_ticker(listener, TickerStandIn()))
    assert chart is not None
    drawings = [stored_row_text(row) for row in chart_rows_in(listener, chart)]
    assert all(display_width(row) == 60 for row in drawings)
    assert drawings[1][1] == drawings[1][5] == "│"
    assert drawings[12][1] == drawings[12][5] == "│"
    assert drawings[4][:8] == " │─ ─│  "
    assert drawings[7][:8] == "─│   │─ "
    assert drawings[13] == "─" * 60
    assert drawings[14] == "2026-09-21" + " " * 40 + "2026-09-22"


def test_60_cell_drawing_stems_ticks_axis_labels_and_flat_price(tmp_path):
    frame = pd.DataFrame(
        {"Open": [10.0], "High": [20.0], "Low": [0.0], "Close": [10.0]},
        index=pd.DatetimeIndex(["2026-09-21"]),
    )
    listener = listener_at(tmp_path, lambda _ticker: frame)
    source = present_ticker(listener, TickerStandIn())
    presentation = listener.run_ticker_chart(source)
    assert presentation is not None
    drawings = [stored_row_text(row) for row in chart_rows_in(listener, presentation)]
    assert len(drawings) == 15
    assert all(display_width(text) == 60 for text in drawings)
    assert drawings[0].startswith("Ticker AAPL")
    assert drawings[1][1] == "│"
    assert drawings[12][1] == "│"
    assert drawings[7].startswith("─│─")
    assert drawings[13] == "─" * 60
    assert drawings[14].startswith("2026-09-21")
    assert drawings[14].count("2026-09-21") == 1

    flat = frame.copy()
    flat.loc[:, ["Open", "High", "Low", "Close"]] = 7.0
    flat_chart = capture_chart("FLAT", flat)
    context = listener.drawing_contexts.standalone
    flat_rows = chart_rows(flat_chart, listener.types, context)
    flat_drawing = [stored_row_text(row) for row in flat_rows]
    assert flat_drawing[6].startswith("─│─")
    assert all(text.startswith("   ") for text in flat_drawing[1:6])
    assert all(text.startswith("   ") for text in flat_drawing[7:13])


def test_nested_hits_direct_detail_and_exact_composition_chips(tmp_path):
    frame = pd.DataFrame(
        {"Open": [10.0, 5.0], "High": [20.0, 10.0], "Low": [0.0, 5.0], "Close": [15.0, 5.0]},
        index=pd.DatetimeIndex(["2026-09-21", "2026-09-22"]),
    )
    listener = listener_at(tmp_path, lambda _ticker: frame)
    source = present_ticker(listener, TickerStandIn())
    outer = listener.run_ticker_chart(source)
    assert outer is not None
    rows = chart_rows_in(listener, outer)
    candle = next(p for p in rows[1].presentations if p.type is listener.types.candle)
    result = layout(listener.history, 80)
    logical_plot = listener.history.rows.index(rows[1])
    y = next(index for index, row in enumerate(result.rows) if row.logical_row == logical_plot)
    logical_label = listener.history.rows.index(rows[14])
    label_y = next(index for index, row in enumerate(result.rows) if row.logical_row == logical_label)
    assert result.hit_test(2, y) is candle
    assert result.hit_test(3, y) is candle
    assert result.hit_test(4, y) is candle
    assert result.hit_test(5, y) is outer
    assert result.hit_test(2, label_y) is outer
    assert result.hit_test(6, y).type is listener.types.candle
    assert result.hit_test(6, y).value is outer.value.visible_candles[1]

    old_last = listener.python_namespace["_"]
    before = len(listener.history.rows)
    assert listener.select_for_input(candle)
    assert len(listener.history.rows) == before + 1
    assert stored_row_text(listener.history.rows[-1]) == (
        "2026-09-21 • Open 10.0 • High 20.0 • Low 0.0 • Close 15.0"
    )
    assert listener.python_namespace["_"] is old_last
    before = len(listener.history.rows)
    assert not listener.select_for_input(outer)
    assert len(listener.history.rows) == before

    listener.set_input_text("id(")
    assert listener.select_for_input(candle)
    chip = next(piece for piece in listener.python_pieces if isinstance(piece, PythonChip))
    assert chip.value is candle.value
    assert chip.label == "Candle 2026-09-21"
    assert len(listener.history.rows) == before
    listener.set_input_text("id(")
    assert listener.select_for_input(outer)
    chip = next(piece for piece in listener.python_pieces if isinstance(piece, PythonChip))
    assert chip.value is outer.value
    assert chip.label == "Ticker AAPL chart"
    assert len(listener.history.rows) == before
    listener.set_input_text('"abc"')
    listener.set_python_cursor(2)
    assert not listener.select_for_input(candle)
    assert len(listener.history.rows) == before


def test_headless_imports_do_not_load_textual():
    result = subprocess.run(
        ["uv", "run", "--offline", "python", "-c", (
            "import sys; import pbui.chart; import pbui.commands; "
            "assert 'textual' not in sys.modules"
        )],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_ticker_menu_only_fetches_on_choice_and_history_keeps_frame_path(tmp_path):
    frame = frame_for()
    calls = []
    listener = listener_at(tmp_path, lambda ticker: calls.append(ticker) or frame)
    ticker = TickerStandIn()
    source = present_ticker(listener, ticker)
    assert tuple(item.label for item in listener.python_translators_for(source)) == (
        "history", "candlestick",
    )
    assert format_documentation(listener, source) == "TICKER AAPL • Left: show • Right: menu"
    assert calls == []
    assert listener.select(source)
    assert calls == []
    listener.set_input_text("id(")
    assert listener.select_for_input(source)
    assert any(isinstance(piece, PythonChip) and piece.value is ticker
               for piece in listener.python_pieces)
    assert calls == []
    listener.cancel()

    before = len(listener.history.rows)
    chart_presentation = listener.invoke_python_translator(source, 1)
    assert chart_presentation is not None
    assert calls == [ticker]
    assert len(listener.history.rows) == before + 16
    action_row = listener.history.rows[before]
    action = action_row.presentations[0].value
    assert isinstance(action, MenuActionInput)
    assert (action.label, action.kind, action.target) == ("candlestick", "chart", ticker)
    assert action.operation.__self__ is listener
    assert stored_row_text(action_row).startswith("› candlestick — ")
    assert listener.history.rows[before + 1].presentations[0] is chart_presentation
    assert listener.python_namespace["_"] is chart_presentation.value
    assert all(p.value is not frame for p in listener.history.presentations)

    result = listener.invoke_python_translator(source, 0)
    assert calls == [ticker, ticker]
    assert result is not None and result.value is frame
    assert listener.history.rows[-2].presentations[0].value.label == "history"
    assert stored_row_text(listener.history.rows[-1]) == "DataFrame 3×4"
    assert listener.run_again(listener.history.rows[-2].presentations[0])
    assert calls == [ticker, ticker, ticker]
    assert listener.history.rows[-1].presentations[0].value is frame


@pytest.mark.parametrize("outcome", ["chart", "empty", "invalid", "error"])
def test_saved_candlestick_replays_exact_ticker_after_source_eviction(tmp_path, outcome):
    frame = frame_for()
    calls = []

    def history(ticker):
        calls.append(ticker)
        if outcome == "error":
            raise RuntimeError("fixture fetch failed")
        if outcome == "empty":
            return frame.iloc[:0]
        if outcome == "invalid":
            return frame.drop(columns="Close")
        return frame

    listener = listener_at(tmp_path, history, max_rows=20)
    ticker = TickerStandIn()
    source = present_ticker(listener, ticker)
    listener.invoke_python_translator(source, 1)
    action = next(p for p in listener.history.presentations
                  if p.type is listener.types.menu_action_input)
    assert action.value.target is ticker
    assert calls == [ticker]
    action_index = next(index for index, row in enumerate(listener.history.rows)
                        if action in row.presentations)
    assert listener.history.rows[action_index + 1].presentations[0].type is (
        listener.types.chart if outcome == "chart" else
        listener.types.error if outcome == "error" else listener.types.text
    )
    if outcome in {"empty", "invalid"}:
        assert stored_row_text(listener.history.rows[action_index + 1]) == "no prices"
        assert listener.python_namespace["_"] is ticker
    elif outcome == "error":
        assert listener.python_namespace["_"] is ticker
    listener.submit("0")
    listener.submit("1")
    if listener.history.get_presentation(source.id) is source:
        for number in range(2, 20):
            listener.submit(str(number))
            if listener.history.get_presentation(source.id) is not source:
                break
    assert listener.history.get_presentation(source.id) is None
    assert listener.history.get_presentation(action.id) is action
    before_value = listener.python_namespace["_"]
    assert listener.run_again(action)
    assert calls == [ticker, ticker]
    replay_row = next(row for row in reversed(listener.history.rows)
                      if row.presentations and row.presentations[0].type is listener.types.menu_action_input)
    replay = replay_row.presentations[0].value
    assert replay is not action.value
    assert (replay.label, replay.kind, replay.target) == ("candlestick", "chart", ticker)
    if outcome == "chart":
        assert listener.history.rows[-15].presentations[0].type is listener.types.chart
        assert listener.python_namespace["_"] is listener.history.rows[-15].presentations[0].value
        assert all(p.value is not frame for p in listener.history.presentations)
    elif outcome == "error":
        assert listener.history.rows[-1].presentations[0].type is listener.types.error
        assert stored_row_text(listener.history.rows[-1]).endswith("RuntimeError: fixture fetch failed")
    else:
        assert stored_row_text(listener.history.rows[-1]) == "no prices"
    if outcome != "chart":
        # A failed replay never replaces the last evaluated Python value.
        assert listener.python_namespace["_"] is before_value


def test_chart_documentation_and_interval_styles(tmp_path):
    frame = pd.DataFrame(
        {"Open": [10.0, 15.0, 7.0], "High": [20.0, 20.0, 7.0],
         "Low": [0.0, 0.0, 7.0], "Close": [15.0, 10.0, 7.0]},
        index=pd.DatetimeIndex(["2026-09-21", "2026-09-22", "2026-09-23"]),
    )
    listener = listener_at(tmp_path, lambda _ticker: frame)
    chart = listener.run_ticker_chart(present_ticker(listener, TickerStandIn("A\nB")))
    assert chart is not None
    rows = chart_rows_in(listener, chart)
    candles = [p for p in rows[1].presentations if p.type is listener.types.candle]
    assert format_documentation(listener, chart) == "CHART A\\nB • Left: no action • Right: no menu"
    assert [format_documentation(listener, p) for p in candles] == [
        "CANDLE 2026-09-21 (rose) • Left: show • Right: no menu",
        "CANDLE 2026-09-22 (fell) • Left: show • Right: no menu",
        "CANDLE 2026-09-23 (rose) • Left: show • Right: no menu",
    ]
    assert [presentation_style(listener, p, None).color.name for p in candles] == [
        "#00d787", "#ff5f5f", "#00d787",
    ]
    assert presentation_style(listener, chart, None).color.name == "default"
    assert presentation_style(listener, chart, chart).reverse
    assert not presentation_style(listener, candles[0], chart).reverse

    drawing = build_history_text(listener, layout(listener.history, 80), candles[1])
    console = Console(width=80)
    # Probe a plot row through its physical layout so the assertion covers
    # the styled three-cell intervals, including blank candle cells.
    physical = layout(listener.history, 80)
    plot_y = next(i for i, row in enumerate(physical.rows)
                  if row.logical_row == listener.history.rows.index(rows[1]))
    start = sum(len(row.text) + 1 for row in physical.rows[:plot_y])
    for column, reverse in ((2, False), (3, False), (4, False),
                            (5, False), (6, True), (7, True), (8, True),
                            (9, False), (10, False), (11, False)):
        assert drawing.get_style_at_offset(console, start + column).reverse is reverse

    listener.set_input_text("id(")
    assert format_documentation(listener, candles[0]) == (
        "CANDLE 2026-09-21 (rose) • Left: insert value into expression • Right: no menu"
    )
    assert format_documentation(listener, chart) == (
        "CHART A\\nB • Left: insert value into expression • Right: no menu"
    )
    listener.set_input_text('"literal"')
    listener.set_python_cursor(2)
    assert "insertion unavailable in string or comment" in format_documentation(listener, candles[1])
    assert "insertion unavailable in string or comment" in format_documentation(listener, chart)
    listener.cancel()
    listener.submit(":rm")
    for target, name in ((chart, "Chart"), (candles[0], "Candle")):
        sentence = format_documentation(listener, target)
        assert f"cannot use {name}; File required" in sentence
        assert sentence.endswith(" • Esc: cancel • Ctrl-G: cancel")
        style = presentation_style(listener, target, target)
        assert style.color.name == "#808080"
        assert style.dim and not style.reverse and not style.underline


def test_empty_history_action_and_replay_append_frame_without_chart(tmp_path):
    frame = frame_for().iloc[:0]
    calls = []
    listener = listener_at(tmp_path, lambda ticker: calls.append(ticker) or frame)
    ticker = TickerStandIn()
    source = present_ticker(listener, ticker)
    result = listener.invoke_python_translator(source, 0)
    assert calls == [ticker]
    assert result is not None and result.value is frame
    action = listener.history.rows[-2].presentations[0]
    assert isinstance(action.value, MenuActionInput)
    assert action.value.label == "history"
    assert listener.history.rows[-1].presentations[0].value is frame
    assert listener.run_again(action)
    assert calls == [ticker, ticker]
    assert listener.history.rows[-1].presentations[0].value is frame
    assert all(p.type is not listener.types.chart for p in listener.history.presentations)
