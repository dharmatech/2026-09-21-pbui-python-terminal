"""Captured, bounded pandas data for the headless listener."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from pbui.domain import DomainTypes, escape_display
from pbui.substrate import PresentationType
from pbui.text import (
    DrawingContext, HistoryRow, LiteralFragment, PresentedFragment,
    display_width, truncate_display,
)


VISIBLE_ROWS = 12
VISIBLE_COLUMNS = 6


def _label_text(label: object) -> str:
    text = truncate_display(escape_display(str(label)), 24)
    return text if display_width(text) else "''"


def _value_text(value: object) -> str:
    missing = pd.isna(value)
    if isinstance(missing, (bool, np.bool_)) and missing:
        return "NA"
    return escape_display(str(value))


@dataclass(frozen=True, slots=True)
class FramePreview:
    """One frame snapshot and its positional, already formatted view."""

    snapshot: pd.DataFrame
    column_labels: tuple[str, ...]
    row_labels: tuple[str, ...]
    cell_text: tuple[tuple[str, ...], ...]
    omitted_columns: int
    omitted_rows: int
    selectable: bool
    _columns: tuple[pd.Series, ...]
    _rows: tuple[pd.DataFrame, ...]

    def column_at(self, position: int) -> pd.Series | None:
        if type(position) is not int or not 0 <= position < len(self._columns):
            return None
        return self._columns[position]

    def row_at(self, position: int) -> pd.DataFrame | None:
        if type(position) is not int or not 0 <= position < len(self._rows):
            return None
        return self._rows[position]


def capture_frame(frame: pd.DataFrame) -> FramePreview:
    """Own one deep frame copy and cache the visible positional selections."""

    snapshot = frame.copy(deep=True)
    row_count = min(len(snapshot.index), VISIBLE_ROWS)
    column_count = min(len(snapshot.columns), VISIBLE_COLUMNS)
    columns = tuple(snapshot.iloc[:, position].copy() for position in range(column_count))
    rows = tuple(snapshot.iloc[[position]].copy() for position in range(row_count))
    return FramePreview(
        snapshot=snapshot,
        column_labels=tuple(_label_text(snapshot.columns[position]) for position in range(column_count)),
        row_labels=tuple(_label_text(snapshot.index[position]) for position in range(row_count)),
        cell_text=tuple(
            tuple(
                truncate_display(_value_text(snapshot.iat[row, column]), 16)
                for column in range(column_count)
            )
            for row in range(row_count)
        ),
        omitted_columns=len(snapshot.columns) - column_count,
        omitted_rows=len(snapshot.index) - row_count,
        selectable=snapshot.index.nlevels == 1 and snapshot.columns.nlevels == 1,
        _columns=columns,
        _rows=rows,
    )


def list_series_values(series: pd.Series) -> tuple[str, ...]:
    """Return captured positional value rows with one optional omission row."""

    if len(series) == 0:
        return ("no values",)
    visible_count = min(len(series), VISIBLE_ROWS)
    rows = tuple(
        truncate_display(f"[{position}]  {_value_text(series.iloc[position])}", 120)
        for position in range(visible_count)
    )
    omitted = len(series) - visible_count
    return rows + ((f"… ({omitted} more values)",) if omitted else ())


def frame_preview_rows(
    preview: FramePreview, types: DomainTypes, context: DrawingContext,
) -> tuple[HistoryRow, ...]:
    """Draw a captured table with hits confined to its visible axis labels."""

    columns = preview.column_labels
    labels = preview.row_labels
    cells = preview.cell_text
    if len(cells) != len(labels) or any(len(row) != len(columns) for row in cells):
        raise ValueError("inconsistent frame preview dimensions")
    if not labels and not columns:
        return (context.row("empty DataFrame"),)

    widths = [max(5, max((display_width(label) for label in labels), default=0))]
    widths.extend(
        max(display_width(label), max(
            (display_width(row[position]) for row in cells), default=0,
        ))
        for position, label in enumerate(columns)
    )

    def present_label(
        label: str, value: object | None, kind: PresentationType,
    ) -> str | PresentedFragment:
        if not preview.selectable or value is None:
            return label
        fragment = context.present(value, kind)
        return PresentedFragment(fragment.presentation_id, (LiteralFragment(label),))

    rows: list[HistoryRow] = []
    header: list[str | PresentedFragment] = ["index"]
    if columns:
        header.append(" " * (widths[0] - 5))
    for position, label in enumerate(columns):
        header.append("  ")
        header.append(present_label(label, preview.column_at(position), types.pandas_column))
        if position + 1 < len(columns):
            header.append(" " * (widths[position + 1] - display_width(label)))
    rows.append(context.row(*header))

    for position, (label, values) in enumerate(zip(labels, cells, strict=True)):
        parts: list[str | PresentedFragment] = [
            present_label(label, preview.row_at(position), types.pandas_row),
        ]
        if columns:
            parts.append(" " * (widths[0] - display_width(label)))
        for column, value in enumerate(values):
            parts.extend(("  ", value))
            if column + 1 < len(values):
                parts.append(" " * (widths[column + 1] - display_width(value)))
        rows.append(context.row(*parts))

    if preview.omitted_columns:
        rows.append(context.row(f"… ({preview.omitted_columns} more columns)"))
    if not labels and columns:
        rows.append(context.row("no rows"))
    if preview.omitted_rows:
        rows.append(context.row(f"… ({preview.omitted_rows} more rows)"))
    return tuple(rows)
