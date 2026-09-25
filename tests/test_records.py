"""Headless conversion tests for retained JSON records and pandas frames."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from pbui.http import JsonArray, JsonObject
from pbui.records import to_dataframe, to_json_records
from pbui.commands import HeadlessListener, RootedFilesystem
from pbui.transcript import MenuActionInput


class _NoProcesses:
    own_uid = 1000
    own_pid = 1

    def list_for_uid(self, _uid):
        return ()

    def inspect(self, _pid):
        raise AssertionError("no process inspection expected")

    def send_sigterm(self, _pid):
        raise AssertionError("no signal expected")


def _listener(tmp_path, *, max_rows=500):
    return HeadlessListener(
        str(tmp_path), RootedFilesystem(tmp_path), _NoProcesses(),
        history_max_rows=max_rows,
    )


def _retain(listener, value):
    result = listener._repl.display_value(value)
    assert result is not None
    return result


def test_records_to_frame_order_types_and_missing_cells():
    first = JsonObject({"name": "Ada", "active": True, "count": 2, "empty": None})
    second = JsonObject({"score": 1.5, "name": "Grace", "active": False})
    source = JsonArray([first, second])

    frame = to_dataframe(source)

    assert frame.shape == (2, 5)
    assert list(frame.columns) == ["name", "active", "count", "empty", "score"]
    assert list(frame.index) == [0, 1]
    assert all(dtype == object for dtype in frame.dtypes)
    assert frame.iat[0, 0] == "Ada" and type(frame.iat[0, 0]) is str
    assert frame.iat[0, 1] is True
    assert frame.iat[0, 2] == 2 and type(frame.iat[0, 2]) is int
    assert frame.iat[0, 3] is None
    assert frame.iat[1, 0] == "Grace" and frame.iat[1, 1] is False
    assert frame.iat[1, 4] == 1.5 and type(frame.iat[1, 4]) is float
    assert frame.iat[1, 2] is pd.NA
    assert frame.iat[1, 3] is pd.NA
    assert source == [first, second]
    assert source[0] is first and source[1] is second


def test_single_empty_and_ineligible_sources():
    one = JsonObject({"x": 7, "y": None})
    frame = to_dataframe(one)
    assert frame.shape == (1, 2)
    assert list(frame.columns) == ["x", "y"]
    assert frame.iat[0, 0] == 7 and frame.iat[0, 1] is None
    assert to_dataframe(JsonObject()).shape == (1, 0)
    assert to_dataframe(JsonArray()).shape == (0, 0)
    for source in ({"x": 1}, [{"x": 1}], JsonArray([JsonObject(), 1]), JsonArray([{}]), 4):
        with pytest.raises((TypeError, ValueError)):
            to_dataframe(source)


def test_nested_json_is_one_identical_cell_and_source_is_unchanged():
    nested = JsonObject({"items": JsonArray([1, None])})
    source = JsonArray([JsonObject({"payload": nested})])

    frame = to_dataframe(source)

    assert frame.shape == (1, 1)
    assert list(frame.columns) == ["payload"]
    assert frame.iat[0, 0] is nested
    assert source[0]["payload"] is nested
    assert nested == {"items": [1, None]}


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (JsonObject({1: "bad"}), "non-string JSON key"),
        (JsonObject({"nested": JsonArray([float("inf")])}), "non-finite"),
        (JsonObject({"nested": JsonObject({"bad": object()})}), "unsupported"),
    ],
)
def test_invalid_json_wrappers_are_rejected_without_mutation(source, message):
    before = list(source.items())
    with pytest.raises((TypeError, ValueError), match=message):
        to_dataframe(source)
    assert list(source.items()) == before


def test_cyclic_json_wrapper_is_rejected_without_mutation():
    source = JsonObject()
    source["self"] = source
    with pytest.raises(ValueError, match="cycle"):
        to_dataframe(source)
    assert source["self"] is source


def test_whole_frame_to_records_omits_named_index_and_preview_bounds():
    class FrameSubclass(pd.DataFrame):
        pass

    columns = [f"column_{position}" for position in range(7)]
    frame = FrameSubclass(
        [[f"{row}:{column}" for column in range(7)] for row in range(13)],
        columns=columns,
        index=pd.Index([f"key_{row}" for row in range(13)], name="source_index"),
    )
    before = frame.copy(deep=True)

    result = to_json_records(frame)

    assert type(result) is JsonArray
    assert len(result) == 13
    assert all(type(record) is JsonObject for record in result)
    assert all(list(record) == columns for record in result)
    assert result[0]["column_0"] == "0:0"
    assert result[12]["column_6"] == "12:6"
    assert all("source_index" not in record for record in result)
    assert frame.equals(before)


def test_multiindex_is_omitted():
    index = pd.MultiIndex.from_tuples([("north", 1), ("south", 2)], names=["area", "id"])
    frame = pd.DataFrame({"value": [3, 4]}, index=index)

    assert to_json_records(frame) == JsonArray([
        JsonObject({"value": 3}), JsonObject({"value": 4}),
    ])


def test_zero_rows_zero_columns_missing_scalars_and_timestamps():
    assert to_json_records(pd.DataFrame(columns=["a", "b"])) == JsonArray()
    assert to_json_records(pd.DataFrame(index=["one", "two"])) == JsonArray([
        JsonObject(), JsonObject(),
    ])
    frame = pd.DataFrame({
        "missing": pd.Series([None, pd.NA, pd.NaT, np.nan], dtype=object),
        "stamp": pd.Series([
            pd.Timestamp("2024-01-02T03:04:05+02:00"),
            datetime(2024, 1, 2, 3, 4, 5),
            np.datetime64("2024-01-02T03:04:05"),
            np.datetime64("NaT"),
        ], dtype=object),
    })
    before = frame.copy(deep=True)

    result = to_json_records(frame)

    assert [row["missing"] for row in result] == [None] * 4
    assert [row["stamp"] for row in result] == [
        "2024-01-02T03:04:05+02:00",
        "2024-01-02T03:04:05",
        "2024-01-02T03:04:05",
        None,
    ]
    assert frame.equals(before)


def test_nested_cells_are_fresh_wrappers_and_numeric_scalars_are_python_types():
    nested = JsonObject({"list": JsonArray([np.int64(3), {"ok": np.bool_(True)}])})
    plain = {"items": [1, None, {"when": datetime(2024, 1, 1, tzinfo=timezone.utc)}]}
    frame = pd.DataFrame({
        "wrapped": pd.Series([nested], dtype=object),
        "plain": pd.Series([plain], dtype=object),
        "integer": pd.Series([np.int64(8)], dtype=object),
        "floating": pd.Series([np.float32(1.25)], dtype=object),
        "boolean": pd.Series([np.bool_(True)], dtype=object),
    })

    result = to_json_records(frame)
    record = result[0]

    assert type(record["wrapped"]) is JsonObject
    assert record["wrapped"] is not nested
    assert type(record["wrapped"]["list"]) is JsonArray
    assert record["wrapped"]["list"] is not nested["list"]
    assert record["wrapped"]["list"] == [3, {"ok": True}]
    assert type(record["wrapped"]["list"][1]) is JsonObject
    assert type(record["plain"]) is JsonObject
    assert record["plain"] is not plain
    assert type(record["plain"]["items"]) is JsonArray
    assert type(record["plain"]["items"][2]) is JsonObject
    assert record["plain"]["items"][2]["when"] == "2024-01-01T00:00:00+00:00"
    assert record["integer"] == 8 and type(record["integer"]) is int
    assert record["floating"] == 1.25 and type(record["floating"]) is float
    assert record["boolean"] is True
    assert nested["list"][1] == {"ok": np.bool_(True)}
    assert plain["items"][2]["when"] == datetime(2024, 1, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("frame", "message"),
    [
        (pd.DataFrame(columns=["same", "same"]), "unique"),
        (pd.DataFrame(columns=["good", 2]), "strings"),
        (pd.DataFrame({"good": [1, 2], "bad": [{1: "value"}, {"ok": 3}]}), "non-string nested key"),
        (pd.DataFrame({"good": [1, 2], "bad": [float("inf"), 3]}), "non-finite"),
        (pd.DataFrame({"good": [1, 2], "bad": [object(), 3]}), "unsupported"),
    ],
)
def test_invalid_frame_rejects_whole_conversion_without_mutation(frame, message):
    before = frame.copy(deep=True)
    with pytest.raises((TypeError, ValueError), match=message):
        to_json_records(frame)
    assert frame.equals(before)


def test_nested_frame_cycle_is_rejected_without_mutation():
    cycle = []
    cycle.append(cycle)
    frame = pd.DataFrame({"good": [1], "bad": pd.Series([cycle], dtype=object)})
    with pytest.raises(ValueError, match="cycle"):
        to_json_records(frame)
    assert frame.iat[0, 1] is cycle and cycle[0] is cycle


def test_non_frame_input_is_rejected():
    with pytest.raises(TypeError, match="DataFrame"):
        to_json_records([{"x": 1}])


def test_retained_value_action_eligibility(tmp_path):
    class FrameSubclass(pd.DataFrame):
        pass

    listener = _listener(tmp_path)
    cases = (
        (JsonObject({"a": 1}), ("To DataFrame",)),
        (JsonArray([JsonObject({"a": 1})]), ("To DataFrame",)),
        (JsonArray(), ("To DataFrame",)),
        (JsonArray([JsonObject(), 1]), ()),
        (JsonArray([{}]), ()),
        (pd.DataFrame({"a": [1]}), ("To JSON records",)),
        (FrameSubclass({"a": [1]}), ("To JSON records",)),
        (pd.Series([1]), ()),
        ({"a": 1}, ()),
        ([{"a": 1}], ()),
        (1, ()),
    )
    for value, expected in cases:
        source = _retain(listener, value)
        assert tuple(action.label for action in listener.python_translators_for(source)) == expected


def test_retained_actions_append_input_then_value_and_preserve_sources(tmp_path):
    listener = _listener(tmp_path)
    records = JsonArray([JsonObject({"name": "Ada", "count": 2}),
                         JsonObject({"name": "Grace"})])
    source = _retain(listener, records)
    source_row = listener.history.rows[-1]

    frame_value = listener.invoke_python_translator(source, 0)
    assert frame_value is listener.history.presentations[-1]
    assert isinstance(frame_value.value, pd.DataFrame)
    assert frame_value.value.shape == (2, 2)
    assert listener.python_namespace["_"] is frame_value.value
    action = listener.history.rows[-2].presentations[0]
    assert action.type is listener.types.menu_action_input
    assert isinstance(action.value, MenuActionInput)
    assert action.value.target is records
    assert source_row in listener.history.rows and source.value is records
    assert listener.capture_pandas_frame(frame_value).cell_text[1][1] == "NA"

    json_value = listener.invoke_python_translator(frame_value, 0)
    assert type(json_value.value) is JsonArray
    assert json_value.value == JsonArray([
        JsonObject({"name": "Ada", "count": 2}),
        JsonObject({"name": "Grace", "count": None}),
    ])
    assert listener.python_namespace["_"] is json_value.value
    assert listener.history.rows[-2].presentations[0].value.target is frame_value.value
    assert source_row in listener.history.rows


@pytest.mark.parametrize("frame", [
    pd.DataFrame({"good": [1], 2: [3]}),
    pd.DataFrame({"good": [1], "bad": [object()]}),
])
def test_retained_action_failure_has_one_error_and_no_result(tmp_path, frame):
    listener = _listener(tmp_path)
    source = _retain(listener, frame)
    source_row = listener.history.rows[-1]
    previous = listener.python_namespace["_"]
    before = len(listener.history.rows)

    assert listener.invoke_python_translator(source, 0) is None
    assert len(listener.history.rows) == before + 2
    action, error = (row.presentations[0] for row in listener.history.rows[-2:])
    assert action.type is listener.types.menu_action_input
    assert action.value.target is frame
    assert error.type is listener.types.error
    assert listener.python_namespace["_"] is previous
    assert source_row in listener.history.rows and source.value is frame


def test_run_again_uses_saved_source_even_after_source_row_eviction(tmp_path):
    listener = _listener(tmp_path, max_rows=2)
    source_object = JsonObject({"a": 7})
    source = _retain(listener, source_object)
    first = listener.invoke_python_translator(source, 0)
    saved = listener.history.rows[-2].presentations[0]
    assert saved.value.target is source_object
    assert listener.history.get_presentation(source.id) is None
    assert first.value.iat[0, 0] == 7

    source_object["a"] = 8
    assert listener.run_again(saved)
    assert listener.history.rows[-2].presentations[0].value.target is source_object
    repeated = listener.history.rows[-1].presentations[0]
    assert repeated.value.iat[0, 0] == 8
    assert listener.python_namespace["_"] is repeated.value
