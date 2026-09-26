"""Immutable daily-price capture and character chart rows."""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING

import pandas as pd

from pbui.domain import escape_display
from pbui.text import (
    DrawingContext, HistoryRow, LiteralFragment, PresentedFragment,
    display_width, truncate_display,
)

if TYPE_CHECKING:
    from pbui.domain import DomainTypes


CHART_WIDTH = 60
PLOT_HEIGHT = 12
MAX_CANDLES = 15
REQUIRED_COLUMNS = ("Open", "High", "Low", "Close")


@dataclass(frozen=True, slots=True)
class Candle:
    date: str
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True, slots=True)
class Chart:
    symbol: str
    bars: tuple[Candle, ...]
    visible_candles: tuple[Candle, ...]
    omitted_count: int


def capture_chart(symbol: str, frame: pd.DataFrame) -> Chart:
    """Copy and validate every daily bar before any history row is appended."""

    if (
        not isinstance(frame, pd.DataFrame)
        or frame.empty
        or not isinstance(frame.index, pd.DatetimeIndex)
        or any(frame.columns.tolist().count(name) != 1 for name in REQUIRED_COLUMNS)
    ):
        raise ValueError("no prices")

    positions = tuple(frame.columns.get_loc(name) for name in REQUIRED_COLUMNS)
    bars: list[Candle] = []
    for date, values in zip(frame.index, frame.itertuples(index=False, name=None)):
        if pd.isna(date):
            raise ValueError("no prices")
        try:
            day = date.date().isoformat()
            opening, high, low, close = (float(values[position]) for position in positions)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("no prices") from error
        if (
            not all(math.isfinite(price) for price in (opening, high, low, close))
            or low > high
            or not low <= opening <= high
            or not low <= close <= high
        ):
            raise ValueError("no prices")
        bars.append(Candle(day, opening, high, low, close))

    ordered = tuple(sorted(bars, key=lambda candle: candle.date))
    visible = ordered[-MAX_CANDLES:]
    return Chart(symbol, ordered, visible, len(ordered) - len(visible))


def price_row(price: float, minimum: float, maximum: float) -> int:
    """Map a price to a zero-based, top-to-bottom plot row with half-up ties."""

    if maximum == minimum:
        return 5
    # Fractions avoid overflow for valid finite floats with opposite signs.
    scaled = (
        (Fraction.from_float(maximum) - Fraction.from_float(price))
        * (PLOT_HEIGHT - 1)
        / (Fraction.from_float(maximum) - Fraction.from_float(minimum))
    )
    return max(0, min(PLOT_HEIGHT - 1, math.floor(scaled + Fraction(1, 2))))


def candle_detail(candle: Candle) -> str:
    return (
        f"{candle.date} • Open {candle.open} • High {candle.high} "
        f"• Low {candle.low} • Close {candle.close}"
    )


def _padded(text: str) -> str:
    bounded = truncate_display(text, CHART_WIDTH)
    return bounded + " " * (CHART_WIDTH - display_width(bounded))


def chart_rows(
    chart: Chart, types: DomainTypes, context: DrawingContext,
) -> tuple[HistoryRow, ...]:
    """Draw one chart object and reuse each nested candle across plot rows."""

    chart_id = context.present(chart, types.chart).presentation_id
    candle_ids = tuple(
        context.present(candle, types.candle).presentation_id
        for candle in chart.visible_candles
    )

    def outer(*parts: LiteralFragment | PresentedFragment) -> HistoryRow:
        return context.row(PresentedFragment(chart_id, parts))

    rows = [outer(LiteralFragment(_padded("Ticker " + escape_display(chart.symbol))))]
    minimum = min(candle.low for candle in chart.visible_candles)
    maximum = max(candle.high for candle in chart.visible_candles)
    for plot_row in range(PLOT_HEIGHT):
        parts: list[LiteralFragment | PresentedFragment] = []
        width = 0
        for index, (candle, candle_id) in enumerate(zip(chart.visible_candles, candle_ids)):
            high = price_row(candle.high, minimum, maximum)
            low = price_row(candle.low, minimum, maximum)
            opening = price_row(candle.open, minimum, maximum)
            close = price_row(candle.close, minimum, maximum)
            block = (
                ("─" if plot_row == opening else " ")
                + ("│" if high <= plot_row <= low else " ")
                + ("─" if plot_row == close else " ")
            )
            parts.append(PresentedFragment(candle_id, (LiteralFragment(block),)))
            width += 3
            if index < len(candle_ids) - 1:
                parts.append(LiteralFragment(" "))
                width += 1
        parts.append(LiteralFragment(" " * (CHART_WIDTH - width)))
        rows.append(outer(*parts))

    rows.append(outer(LiteralFragment("─" * CHART_WIDTH)))
    first = chart.visible_candles[0].date
    last = chart.visible_candles[-1].date
    labels = first if len(chart.visible_candles) == 1 else first + " " * (CHART_WIDTH - 20) + last
    rows.append(outer(LiteralFragment(_padded(labels))))
    if chart.omitted_count:
        rows.append(outer(LiteralFragment(_padded(f"… ({chart.omitted_count} more days)"))))
    return tuple(rows)
