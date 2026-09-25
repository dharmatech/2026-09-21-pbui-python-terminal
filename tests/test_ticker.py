"""Headless ticker Values and the injected daily-history operation."""

from __future__ import annotations

import subprocess

import pandas as pd
import yfinance as yf

from pbui.chips import PythonChip
from pbui.bottom import format_documentation, format_menu_item_documentation
from pbui.commands import HeadlessListener, RootedFilesystem
from pbui.text import stored_row_text
from pbui.ticker import production_history
from pbui.transcript import MenuActionInput


class EmptyProcesses:
    pass


class TickerStandIn(yf.Ticker):
    def __init__(self, frame: pd.DataFrame | None = None) -> None:
        self.ticker = "AAPL"
        self.frame = frame
        self.history_calls: list[dict[str, object]] = []

    def __repr__(self) -> str:
        return "ticker stand-in"

    def history(self, **kwargs: object) -> pd.DataFrame:
        self.history_calls.append(kwargs)
        assert self.frame is not None
        return self.frame


def frame_with_close(*, empty: bool = False) -> pd.DataFrame:
    dates = pd.DatetimeIndex([] if empty else ["2026-09-21"], name="Date")
    return pd.DataFrame({"Close": [] if empty else [123.0]}, index=dates)


def listener_at(tmp_path, history, *, max_rows=500):
    return HeadlessListener(
        str(tmp_path), RootedFilesystem(tmp_path), EmptyProcesses(),
        ticker_history=history, history_max_rows=max_rows,
    )


def values(listener):
    return tuple(
        presentation for presentation in listener.history.presentations
        if presentation.type is listener.types.value
    )


def result_rows(listener):
    input_types = {
        listener.types.python_input, listener.types.command_input,
        listener.types.menu_action_input,
    }
    return tuple(
        row for row in listener.history.rows
        if not row.presentations or row.presentations[0].type not in input_types
    )


def drawings(listener):
    return tuple(stored_row_text(row) for row in result_rows(listener))


def present_ticker(listener, ticker):
    listener.python_namespace["ticker"] = ticker
    listener.submit("ticker")
    return values(listener)[-1]


def test_ticker_summary_namespace_and_chip_retain_exact_object(tmp_path):
    listener = listener_at(tmp_path, lambda _ticker: frame_with_close())
    assert listener.python_namespace == {"__name__": "__pbui__"}
    assert list(listener.python_classes._entries).count(yf.Ticker) == 1
    ticker = TickerStandIn()
    source = present_ticker(listener, ticker)
    assert drawings(listener) == ("Ticker AAPL",)
    assert source.value is ticker
    assert listener.python_namespace["_"] is ticker
    listener.set_input_text("id(")
    assert listener.select_for_input(source)
    chip = next(piece for piece in listener.python_pieces if isinstance(piece, PythonChip))
    assert chip.value is ticker


def test_clicks_leave_history_seam_idle_and_invalid_source_cannot_fetch(tmp_path):
    calls = []
    listener = listener_at(tmp_path, lambda ticker: calls.append(ticker) or frame_with_close(), max_rows=4)
    ticker = TickerStandIn()
    source = present_ticker(listener, ticker)
    assert tuple(action.label for action in listener.python_translators_for(source)) == ("history",)
    assert listener.select_for_input(source)
    assert drawings(listener)[-1] == "TickerStandIn: ticker stand-in"
    assert calls == []

    listener.set_input_text("id(")
    assert listener.select_for_input(source)
    assert next(piece for piece in listener.python_pieces if isinstance(piece, PythonChip)).value is ticker
    assert calls == []
    listener.cancel()

    for number in range(10):
        listener.submit(str(number))
    other = values(listener)[-1]
    assert listener.run_ticker_history(other) is None
    assert calls == []
    assert listener.run_ticker_history(source) is None
    assert calls == []


def test_history_repeats_with_exact_frame_identity_and_retains_ticker(tmp_path):
    first, second = frame_with_close(), frame_with_close()
    calls = []

    def history(ticker):
        calls.append(ticker)
        return (first, second)[len(calls) - 1]

    listener = listener_at(tmp_path, history)
    ticker = TickerStandIn()
    source = present_ticker(listener, ticker)
    first_result = listener.run_ticker_history(source)
    assert first_result is not None and first_result.value is first
    assert drawings(listener)[-1] == "DataFrame 1×1"
    assert listener.python_namespace["_"] is first
    second_result = listener.run_ticker_history(source)
    assert second_result is not None and second_result.value is second
    assert drawings(listener)[-1] == "DataFrame 1×1"
    assert listener.python_namespace["_"] is second
    assert calls == [ticker, ticker]
    assert values(listener) == (source, first_result, second_result)
    assert source.value is ticker


def test_failure_adds_one_error_and_empty_frame_succeeds(tmp_path):
    calls = []

    def fail(ticker):
        calls.append(ticker)
        raise RuntimeError("no prices")

    listener = listener_at(tmp_path, fail)
    ticker = TickerStandIn()
    source = present_ticker(listener, ticker)
    before = len(result_rows(listener))
    assert listener.run_ticker_history(source) is None
    assert calls == [ticker]
    assert len(result_rows(listener)) == before + 1
    assert drawings(listener)[-1].startswith("Error: Traceback")
    assert drawings(listener)[-1].endswith("RuntimeError: no prices")
    assert values(listener) == (source,)
    assert listener.python_namespace["_"] is ticker

    empty = frame_with_close(empty=True)
    empty["Volume"] = pd.Series(dtype="int64")
    success = listener_at(tmp_path, lambda _ticker: empty)
    empty_source = present_ticker(success, TickerStandIn())
    result = success.run_ticker_history(empty_source)
    assert result is not None and result.value is empty
    assert drawings(success)[-1] == "DataFrame 0×2"
    assert success.python_namespace["_"] is empty


def test_typed_history_uses_normal_pandas_path_and_adapter_passes_exact_keywords(tmp_path):
    frame = frame_with_close()
    calls = []
    listener = listener_at(tmp_path, lambda ticker: calls.append(ticker) or frame)
    ticker = TickerStandIn(frame)
    present_ticker(listener, ticker)
    listener.submit('ticker.history(period="1mo")')
    assert values(listener)[-1].value is frame
    assert drawings(listener)[-1] == "DataFrame 1×1"
    assert listener.python_namespace["_"] is frame
    assert calls == []
    assert ticker.history_calls == [{"period": "1mo"}]

    adapter_ticker = TickerStandIn(frame)
    assert production_history(adapter_ticker) is frame
    assert adapter_ticker.history_calls == [
        {"period": "1mo", "interval": "1d", "timeout": 15}
    ]


def test_headless_imports_do_not_import_textual():
    result = subprocess.run(
        ["uv", "run", "--offline", "python", "-c", (
            "import sys; import pbui.ticker; import pbui.commands; "
            "assert 'textual' not in sys.modules"
        )],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_menu_history_is_only_ticker_action_and_records_each_result(tmp_path):
    first, second = frame_with_close(), frame_with_close()
    calls = []

    def history(ticker):
        calls.append(ticker)
        return (first, second)[len(calls) - 1]

    listener = listener_at(tmp_path, history)
    ticker = TickerStandIn()
    source = present_ticker(listener, ticker)
    assert tuple(action.label for action in listener.python_translators_for(source)) == ("history",)
    listener.submit("42")
    assert listener.python_translators_for(values(listener)[-1]) == ()
    assert calls == []

    for expected in (first, second):
        result = listener.invoke_python_translator(source, 0)
        assert result is not None and result.value is expected
        action_row, result_row = listener.history.rows[-2:]
        action = action_row.presentations[0]
        assert action.type is listener.types.menu_action_input
        assert isinstance(action.value, MenuActionInput)
        assert action.value.label == "history"
        assert action.value.target is ticker
        assert action.value.operation is history
        assert result_row.presentations == (result,)
        assert listener.python_namespace["_"] is expected
    assert calls == [ticker, ticker]
    assert source in listener.history.presentations
    assert values(listener)[-2].value is first
    assert values(listener)[-1].value is second


def test_menu_failure_records_one_error_and_preserves_last_value(tmp_path):
    calls = []

    def fail(ticker):
        calls.append(ticker)
        raise RuntimeError("no prices")

    listener = listener_at(tmp_path, fail)
    ticker = TickerStandIn()
    source = present_ticker(listener, ticker)
    previous = listener.python_namespace["_"]
    assert listener.invoke_python_translator(source, 0) is None
    assert calls == [ticker]
    action_row, error_row = listener.history.rows[-2:]
    assert action_row.presentations[0].value.target is ticker
    assert error_row.presentations[0].type is listener.types.error
    assert "RuntimeError: no prices" in stored_row_text(error_row)
    assert values(listener) == (source,)
    assert listener.python_namespace["_"] is previous


def test_saved_history_action_replays_after_ticker_row_eviction(tmp_path):
    frames = [frame_with_close(), frame_with_close()]
    calls = []

    def history(ticker):
        calls.append(ticker)
        return frames[len(calls) - 1]

    listener = listener_at(tmp_path, history, max_rows=6)
    ticker = TickerStandIn()
    source = present_ticker(listener, ticker)
    first = listener.invoke_python_translator(source, 0)
    action = listener.history.rows[-2].presentations[0]
    listener.submit("1")
    listener.submit("2")
    assert source not in listener.history.presentations
    assert action in listener.history.presentations
    assert listener.run_again(action)
    replay, result_row = listener.history.rows[-2:]
    assert replay.presentations[0].value.target is ticker
    assert replay.presentations[0] is not action
    assert result_row.presentations[0].value is frames[1]
    assert first is not None and first.value is frames[0]
    assert listener.python_namespace["_"] is frames[1]
    assert calls == [ticker, ticker]


def test_ticker_documentation_in_ordinary_composition_and_accept_modes(tmp_path):
    listener = listener_at(tmp_path, lambda _ticker: frame_with_close())
    ticker = TickerStandIn()
    source = present_ticker(listener, ticker)
    assert format_documentation(listener, source) == (
        "TICKER AAPL • Left: show • Right: menu"
    )
    assert format_menu_item_documentation(listener, "history", source) == (
        "MENU “history” ON TICKER AAPL • Left: apply • Right: no menu"
    )
    ticker.ticker = "BRK\\B\n"
    target = "TICKER BRK\\\\B\\n"
    assert format_documentation(listener, source) == (
        f"{target} • Left: show • Right: menu"
    )
    listener.set_input_text("id()")
    listener.set_python_cursor(3)
    assert format_documentation(listener, source) == (
        f"{target} • Left: insert value into expression • Right: menu"
    )
    listener.set_input_text('"literal"')
    listener.set_python_cursor(2)
    assert format_documentation(listener, source) == (
        f"{target} • Left: insertion unavailable in string or comment • Right: menu"
    )
    listener.cancel()
    listener.submit(":rm")
    assert format_documentation(listener, source) == (
        f"SELECTING FILE FOR rm — {target} • Left: cannot use Value; File required"
        " • Right: no menu • Esc: cancel • Ctrl-G: cancel"
    )
    assert not listener.select_for_input(source)
