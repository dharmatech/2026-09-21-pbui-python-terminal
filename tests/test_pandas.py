"""Headless pandas Value registration and captured inspector data."""

from __future__ import annotations

import subprocess

import numpy as np
import pandas as pd

from pbui.chips import PythonChip
from pbui.commands import HeadlessListener, RootedFilesystem
from pbui.pandas_inspector import capture_frame, frame_preview_rows, list_series_values
from pbui.text import (
    LiteralFragment, PresentedFragment, display_width, logical_presentation_text,
    stored_row_text,
)


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


def values(listener):
    return tuple(
        presentation for presentation in listener.history.presentations
        if presentation.type is listener.types.value
    )


def drawing(listener, presentation):
    return logical_presentation_text(listener.history, presentation)


def test_registration_summaries_identity_and_namespace(tmp_path):
    listener = listener_at(tmp_path)
    assert listener.python_namespace == {"__name__": "__pbui__"}
    listener.submit("import pandas")
    assert listener.python_namespace["pandas"] is pd

    frame = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    integer = pd.Series([1, 2], dtype="int64", name="integers")
    words = pd.Series(["x"], dtype="object", name="words")
    flags = pd.Series([True, pd.NA], dtype="boolean")
    expected = (
        (frame, "DataFrame 2×2"),
        (integer, "Series 2 integers int64"),
        (words, "Series 1 words object"),
        (flags, "Series 2 boolean"),
    )
    for index, (original, text) in enumerate(expected):
        listener.python_namespace[f"item_{index}"] = original
        listener.submit(f"item_{index}")
        presentation = values(listener)[-1]
        assert presentation.value is original
        assert drawing(listener, presentation) == text
        assert listener.python_namespace["_"] is original
        assert listener.python_classes.registered_class(original) is type(original)
        assert listener.python_classes.translators_for(original) == ()

    frame_presentation = values(listener)[0]
    listener.set_input_text("id(")
    assert listener.select_for_input(frame_presentation)
    chip = next(piece for piece in listener.python_pieces if isinstance(piece, PythonChip))
    assert chip.value is frame
    assert listener.python_namespace["_"] is flags


def test_generic_classes_and_non_domain_accepts(tmp_path):
    listener = listener_at(tmp_path)
    assert listener.python_classes.registered_class({}) is None
    assert listener.python_classes.registered_class([]) is None
    assert listener.python_classes.registered_class(np.array([1])) is None
    assert listener.python_classes.registered_class(pd.Index([1])) is None
    assert listener.python_classes.registered_class(np.int64(1)) is None
    for name, value in (
        ("mapping", {"a": 1}),
        ("items", [1, 2]),
        ("array", np.array([1, 2])),
    ):
        listener.python_namespace[name] = value
        listener.submit(name)
        presentation = values(listener)[-1]
        assert drawing(listener, presentation).startswith(type(value).__name__ + " ")
        assert listener.python_translators_for(presentation) == ()

    frame = pd.DataFrame({"a": [1]})
    listener.python_namespace["frame"] = frame
    listener.submit("frame")
    target = values(listener)[-1]
    listener.submit(":show")
    assert listener.pending_request is not None
    assert not listener.select_for_input(target)
    assert listener.pending_request is not None


def test_frame_capture_windows_safe_text_and_positional_copies(tmp_path):
    listener = listener_at(tmp_path)
    columns = ["same", "same", "x\ny", "界" * 13, "\u0301", "last", "omitted"]
    frame = pd.DataFrame(
        [[f"{row}:{column}" for column in range(7)] for row in range(13)],
        columns=columns,
        index=["", "wide界", "e\u0301", *range(3, 13)],
    )
    frame.iloc[0, 0] = "hello\tworld"
    frame.iloc[0, 1] = None
    frame.iloc[1, 0] = "界" * 9
    frame.iloc[2, 0] = "e\u0301" * 18
    listener.python_namespace["frame"] = frame
    listener.submit("frame")
    source = values(listener)[-1]
    preview = listener.capture_pandas_frame(source)
    assert preview is not None
    assert preview.snapshot is not frame
    assert preview.snapshot.equals(frame)
    assert preview.column_labels == ("same", "same", r"x\ny", "界" * 11 + "…", "''", "last")
    assert preview.row_labels[:3] == ("''", "wide界", "e\u0301")
    assert len(preview.row_labels) == 12
    assert len(preview.cell_text) == 12
    assert all(len(row) == 6 for row in preview.cell_text)
    assert (preview.omitted_rows, preview.omitted_columns) == (1, 1)
    assert preview.selectable
    assert preview.cell_text[0][:2] == (r"hello\tworld", "NA")
    assert display_width(preview.cell_text[1][0]) <= 16
    assert preview.cell_text[1][0].endswith("…")
    assert preview.cell_text[2][0] == "e\u0301" * 15 + "…"
    assert listener.python_namespace["_"] is frame

    assert preview.column_at(-1) is None
    assert preview.column_at(6) is None
    assert preview.column_at(True) is None
    assert preview.row_at(-1) is None
    assert preview.row_at(12) is None
    before = len(listener.history.rows)
    assert listener.present_pandas_copy(preview.column_at(6)) is None
    assert len(listener.history.rows) == before
    second_column = preview.column_at(1)
    assert second_column is not None
    assert second_column.name == "same"
    assert pd.isna(second_column.iloc[0])
    assert second_column.iloc[1] == "1:1"
    extracted = listener.present_pandas_copy(second_column)
    assert extracted is values(listener)[-1]
    assert extracted.value is second_column
    assert listener.python_namespace["_"] is second_column
    one_row = preview.row_at(1)
    assert one_row is not None
    assert one_row.shape == (1, 7)
    assert list(one_row.columns[:2]) == ["same", "same"]
    extracted_row = listener.present_pandas_copy(one_row)
    assert extracted_row is values(listener)[-1]
    assert extracted_row.value is one_row
    assert listener.python_namespace["_"] is one_row
    assert source.value is frame


def test_snapshot_isolation_recapture_and_invalid_sources(tmp_path):
    listener = listener_at(tmp_path, max_rows=10)
    frame = pd.DataFrame({"one": [1, 2], "two": [3, 4]})
    listener.python_namespace["frame"] = frame
    listener.submit("frame")
    source = values(listener)[-1]
    first = listener.capture_pandas_frame(source)
    assert first is not None
    before = (listener.history.rows, listener.python_namespace["_"])
    frame.iloc[0, 0] = 99
    assert first.snapshot.iat[0, 0] == 1
    assert first.cell_text[0][0] == "1"
    assert first.column_at(0).iloc[0] == 1
    assert first.row_at(0).iat[0, 0] == 1
    second = listener.capture_pandas_frame(source)
    assert second is not None
    assert second.cell_text[0][0] == "99"
    assert listener.history.rows == before[0]
    assert listener.python_namespace["_"] is before[1]

    series = pd.Series([1])
    listener.python_namespace["series"] = series
    listener.submit("series")
    series_source = values(listener)[-1]
    assert listener.capture_pandas_frame(series_source) is None
    assert listener.list_pandas_series(source) is None
    input_presentation = next(
        presentation for presentation in listener.history.presentations
        if presentation.type is listener.types.python_input
    )
    assert listener.capture_pandas_frame(input_presentation) is None
    assert listener.list_pandas_series(input_presentation) is None
    assert listener.capture_pandas_frame(None) is None
    assert listener.present_pandas_copy(1) is None

    for position in range(10):
        if source not in listener.history.presentations:
            break
        listener._append_text(f"evict {position}")
    assert source not in listener.history.presentations
    assert listener.capture_pandas_frame(source) is None
    assert listener.list_pandas_series(series_source) is not None
    for position in range(10, 20):
        if series_source not in listener.history.presentations:
            break
        listener._append_text(f"evict {position}")
    assert series_source not in listener.history.presentations
    assert listener.list_pandas_series(series_source) is None


def test_series_rows_missing_values_and_multiindex():
    series = pd.Series(
        [None, pd.NA, pd.NaT, float("nan"), [1, None], "a\nb", "界" * 70,
         "e\u0301" * 140, 8, 9, 10, 11, 12],
        dtype="object",
    )
    rows = list_series_values(series)
    assert rows[:6] == (
        "[0]  NA", "[1]  NA", "[2]  NA", "[3]  NA",
        "[4]  [1, None]", r"[5]  a\nb",
    )
    assert len(rows) == 13
    assert rows[-1] == "… (1 more values)"
    assert display_width(rows[6]) == 120
    assert rows[6].endswith("…")
    assert display_width(rows[7]) == 120
    assert rows[7].endswith("…")
    assert list_series_values(pd.Series([], dtype="object")) == ("no values",)
    frame = pd.DataFrame(
        [[pd.NA, [1, 2]]],
        index=pd.MultiIndex.from_tuples([("a", 1)]),
        columns=pd.MultiIndex.from_tuples([("x", 1), ("x", 2)]),
    )
    preview = capture_frame(frame)
    assert not preview.selectable
    assert preview.cell_text == (("NA", "[1, 2]"),)
    assert preview.row_labels == (str(frame.index[0]),)


def test_headless_series_listing_does_not_change_last_value(tmp_path):
    listener = listener_at(tmp_path)
    series = pd.Series(range(13), name="numbers")
    listener.python_namespace["series"] = series
    listener.submit("series")
    source = values(listener)[-1]
    previous_rows = listener.history.rows
    assert listener.list_pandas_series(source) == tuple(
        f"[{position}]  {position}" for position in range(12)
    ) + ("… (1 more values)",)
    assert listener.history.rows == previous_rows
    assert listener.python_namespace["_"] is series
    assert source.value is series


def test_model_and_headless_listener_do_not_import_textual():
    result = subprocess.run(
        ["uv", "run", "--offline", "python", "-c", (
            "import sys; import pbui.pandas_inspector; import pbui.commands; "
            "assert 'textual' not in sys.modules"
        )],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_preview_table_exact_hits_and_cached_clicks(tmp_path):
    listener = listener_at(tmp_path)
    frame = pd.DataFrame([[1, 20], [300, 4]], columns=["same", "same"], index=["界", "b"])
    listener.python_namespace["frame"] = frame
    listener.submit("frame")
    source = values(listener)[-1]
    before = listener.python_namespace["_"]
    assert listener.select_for_input(source)
    first_rows = listener.history.rows[-3:]
    assert tuple(map(stored_row_text, first_rows)) == (
        "index  same  same",
        "界     1     20",
        "b      300   4",
    )
    assert listener.python_namespace["_"] is before
    assert source.value is frame
    header = first_rows[0]
    assert tuple(p.type for p in header.presentations) == (
        listener.types.pandas_column, listener.types.pandas_column,
    )
    assert isinstance(header.fragments[0], LiteralFragment)
    assert sum(isinstance(fragment, PresentedFragment) for fragment in header.fragments) == 2
    assert first_rows[1].presentations[0].type is listener.types.pandas_row
    assert all(not row.presentations[1:] for row in first_rows[1:])
    second_column = header.presentations[1]
    row_hit = first_rows[1].presentations[0]
    assert listener.select_for_input(second_column)
    assert values(listener)[-1].value is second_column.value
    assert listener.python_namespace["_"] is second_column.value
    assert listener.select_for_input(second_column)
    assert values(listener)[-1].value is second_column.value
    assert listener.select_for_input(row_hit)
    assert values(listener)[-1].value is row_hit.value
    assert listener.python_namespace["_"] is row_hit.value

    frame.iloc[0, 1] = 77
    assert listener.select_for_input(source)
    assert all(any(row is retained for retained in listener.history.rows) for row in first_rows)
    assert "77" in stored_row_text(listener.history.rows[-2])
    assert "20" in stored_row_text(first_rows[1])
    assert second_column.value.iloc[0] == 20


def test_preview_boundaries_alignment_and_literal_rows(tmp_path):
    listener = listener_at(tmp_path)
    context = listener.drawing_contexts.standalone
    types = listener.types
    cases = (
        (pd.DataFrame(), ("empty DataFrame",)),
        (pd.DataFrame(columns=["a", "b"]), ("index  a  b", "no rows")),
        (pd.DataFrame(index=["a", "b"]), ("index", "a", "b")),
        (pd.DataFrame(columns=list("abcdefg")), (
            "index  a  b  c  d  e  f", "… (1 more columns)", "no rows",
        )),
    )
    for frame, expected in cases:
        rows = frame_preview_rows(capture_frame(frame), types, context)
        assert tuple(map(stored_row_text, rows)) == expected
        assert all(not row.presentations for row in rows if "…" in stored_row_text(row))

    frame = pd.DataFrame(
        [["e\u0301", "界"], ["界", "x"]], columns=["界", "long"], index=["a", "wide"]
    )
    rows = frame_preview_rows(capture_frame(frame), types, context)
    assert tuple(map(stored_row_text, rows)) == (
        "index  界  long", "a      e\u0301   界", "wide   界  x",
    )
    assert display_width(stored_row_text(rows[0]).split("  ")[1]) == 2

    large = pd.DataFrame([[1] * 8 for _ in range(14)])
    rows = frame_preview_rows(capture_frame(large), types, context)
    assert len(rows) == 15
    assert tuple(map(stored_row_text, rows[-2:])) == (
        "… (2 more columns)", "… (2 more rows)",
    )
    assert rows[-2].presentations == rows[-1].presentations == ()


def test_series_literal_multiindex_stale_and_atomic_errors(tmp_path, monkeypatch):
    listener = listener_at(tmp_path)
    series = pd.Series([1, None], dtype="object")
    listener.python_namespace["series"] = series
    listener.submit("series")
    source = values(listener)[-1]
    assert listener.select_for_input(source)
    rows = listener.history.rows[-2:]
    assert tuple(map(stored_row_text, rows)) == ("[0]  1", "[1]  NA")
    assert all(row.presentations == () for row in rows)
    assert listener.python_namespace["_"] is series
    series.iloc[0] = 9
    assert stored_row_text(rows[0]) == "[0]  1"

    for axis in ("index", "columns"):
        frame = pd.DataFrame([[1]], index=["i"], columns=["c"])
        if axis == "index":
            frame.index = pd.MultiIndex.from_tuples([("i", 1)])
        else:
            frame.columns = pd.MultiIndex.from_tuples([("c", 1)])
        rows = frame_preview_rows(capture_frame(frame), listener.types, listener.drawing_contexts.standalone)
        assert all(row.presentations == () for row in rows)

    frame = pd.DataFrame({"a": [1]})
    listener.python_namespace["frame"] = frame
    listener.submit("frame")
    frame_source = values(listener)[-1]
    assert listener.select_for_input(frame_source)
    stale = listener.history.rows[-2].presentations[0]
    for index in range(500):
        listener._append_text(f"evict {index}")
    assert not listener.select_for_input(stale)
    assert not listener.select_for_input(frame_source)

    listener.submit("frame")
    fresh = values(listener)[-1]
    before = len(listener.history.rows)
    monkeypatch.setattr("pbui.commands.frame_preview_rows", lambda *_: (_ for _ in ()).throw(ValueError("bad preview")))
    assert listener.select_for_input(fresh)
    assert len(listener.history.rows) == before  # bounded history replaces the oldest row
    assert listener.history.rows[-1].presentations[0].type is listener.types.error
    assert stored_row_text(listener.history.rows[-1]) == "Error: bad preview"
    assert listener.python_namespace["_"] is frame
    listener.submit("series")
    fresh_series = values(listener)[-1]
    monkeypatch.setattr("pbui.commands.list_series_values", lambda *_: (_ for _ in ()).throw(ValueError("bad series")))
    assert listener.select_for_input(fresh_series)
    assert listener.history.rows[-1].presentations[0].type is listener.types.error
    assert stored_row_text(listener.history.rows[-1]) == "Error: bad series"
    assert listener.python_namespace["_"] is series
