"""Pure conversions between retained JSON records and pandas frames."""

from __future__ import annotations

from datetime import datetime
import math

import numpy as np
import pandas as pd

from pbui.http import JsonArray, JsonObject


def _validate_json(value: object, path: str, active: set[int]) -> None:
    """Validate a retained JSON tree without replacing its nested objects."""

    if type(value) in (JsonObject, JsonArray):
        identity = id(value)
        if identity in active:
            raise ValueError(f"cycle in JSON value at {path}")
        active.add(identity)
        try:
            if type(value) is JsonObject:
                for key, child in value.items():
                    if not isinstance(key, str):
                        raise ValueError(f"non-string JSON key at {path}: {key!r}")
                    _validate_json(child, f"{path}[{key!r}]", active)
            else:
                for position, child in enumerate(value):
                    _validate_json(child, f"{path}[{position}]", active)
        finally:
            active.remove(identity)
        return
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is float:
        if math.isfinite(value):
            return
        raise ValueError(f"non-finite JSON number at {path}")
    raise TypeError(f"unsupported JSON value at {path}: {type(value).__name__}")


def to_dataframe(value: object) -> pd.DataFrame:
    """Make an object-valued frame from one JSON record or an array of them."""

    if type(value) is JsonObject:
        records = [value]
    elif type(value) is JsonArray:
        records = value
        if any(type(record) is not JsonObject for record in records):
            raise TypeError("JSON array must contain only JsonObject records")
    else:
        raise TypeError("To DataFrame requires a JsonObject or JsonArray of records")

    _validate_json(value, "$", set())
    columns = list(dict.fromkeys(key for record in records for key in record))
    frame = pd.DataFrame(index=range(len(records)))
    for key in columns:
        cells = np.empty(len(records), dtype=object)
        for position, record in enumerate(records):
            cells[position] = record[key] if key in record else pd.NA
        frame[key] = pd.Series(cells, dtype=object)
    return frame


def _json_cell(value: object, path: str, active: set[int]) -> object:
    """Build a fresh JSON value from one frame cell or nested member."""

    if type(value) in (JsonObject, dict, JsonArray, list):
        identity = id(value)
        if identity in active:
            raise ValueError(f"cycle in frame value at {path}")
        active.add(identity)
        try:
            if type(value) in (JsonObject, dict):
                result = JsonObject()
                for key, child in value.items():
                    if not isinstance(key, str):
                        raise ValueError(f"non-string nested key at {path}: {key!r}")
                    result[key] = _json_cell(child, f"{path}[{key!r}]", active)
                return result
            return JsonArray(
                _json_cell(child, f"{path}[{position}]", active)
                for position, child in enumerate(value)
            )
        finally:
            active.remove(identity)

    # Missingness can be array-valued for containers, so check it only here.
    missing = pd.isna(value)
    if isinstance(missing, (bool, np.bool_)) and missing:
        return None
    if isinstance(value, str):
        return str(value)
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        converted = float(value)
        if math.isfinite(converted):
            return converted
        raise ValueError(f"non-finite number at {path}")
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, np.datetime64):
        return pd.Timestamp(value).isoformat()
    raise TypeError(f"unsupported frame value at {path}: {type(value).__name__}")


def to_json_records(frame: pd.DataFrame) -> JsonArray:
    """Convert every row and column of a frame to fresh JSON records."""

    if not isinstance(frame, pd.DataFrame):
        raise TypeError("To JSON records requires a pandas DataFrame")
    labels = list(frame.columns)
    if any(not isinstance(label, str) for label in labels):
        raise ValueError("DataFrame column labels must be strings")
    if len(set(labels)) != len(labels):
        raise ValueError("DataFrame column labels must be unique")

    result = JsonArray()
    for row in range(len(frame.index)):
        record = JsonObject()
        for column, label in enumerate(labels):
            record[label] = _json_cell(frame.iat[row, column], f"row {row}, column {label!r}", set())
        result.append(record)
    return result
