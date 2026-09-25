# Specification — JSON records and DataFrames

**Status:** Accepted for implementation.

This series lets a retained JSON array of records, or one JSON object, produce a pandas `DataFrame`, and lets a retained frame produce JSON records. The conversions are explicit actions on the original objects. This file is the complete design input for the checkpoint manager and implementers; they do not need the charter.

## 1. Checkpoint series and authority

The series identity is **records**. Checkpoint 000 is spoken **records 000** and filed as `checkpoints/000-slug.md`; 001 is **records 001**. Numbers are three digits, begin at 000, are never renumbered, and use lowercase hyphenated slugs. The checkpoint manager writes one checkpoint and stops. An implementer receives one checkpoint, implements and tests that slice, then stops. Code and tests belong at the project root, not in this design folder. After acceptance, this specification is the authority for both checkpoints.

The layer order is fixed: **000** builds and tests the pure, headless conversions; **001** exposes them as Value menu actions, verifies retained history and documentation, adds one screen test, performs the live hand check, and writes the demo. Each layer is one independently testable checkpoint. A checkpoint manager may split a layer only if it cannot fit comfortably in one implementer conversation; it keeps the order and adds no features.

The accepted [HTTP specification](../http/spec.md) governs `JsonObject`, `JsonArray`, `:get`, `perform`, `json`, and one-level dig. The accepted [pandas specification](../pandas/spec.md) governs frame and series summaries, the captured preview, and positional extraction. The [popup specification](../popup/spec.md) and the implemented listener govern menu placement, input rows, action replay, and click precedence. This series changes only the actions available on eligible JSON values and frames and their corresponding documentation right clauses. It does not change ordinary left clicks, previews, generic values, or accepts. On those seams, the earlier specifications win.

## 2. Product boundary, host, and layout

Use the existing Linux full-screen listener at `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`, with Python `>=3.11`, the packaged `src/pbui/` source tree, and `tests/`. It is already a `uv init --package` project; do not initialize it again. Pandas and pytest are already recorded in `pyproject.toml` and `uv.lock`. Add no dependency and do not change `requires-python`. An implementer uses `uv sync` to refresh the environment, `uv run pytest` for the automated gate, and `uv run pbui` for the live hand check. Every Python or test command runs through `uv run`. If `uv` is unavailable, stop and report it. The spec writer does not run uv.

Put the pure conversion functions in `src/pbui/records.py`; this module imports no Textual code and opens no socket. The listener integration uses `src/pbui/commands.py`, and documentation wording uses `src/pbui/bottom.py`. The existing `src/pbui/terminal.py` menu already reads `python_translators_for` for Value targets and dispatches a selected translator; this series uses that path and does not add a new menu widget or click route. Put focused headless tests in `tests/test_records.py`, wording tests in `tests/test_bottom.py`, and the screen test in `tests/test_terminal.py`. The completed demo belongs at `docs/design/implementation/records/demo.md`.

Do not add `json_normalize`, nested-field flattening, a Series conversion, a new colon command, a ticker, an indicator, a chart, or changes to HTTP transport. Do not modify the frame preview, series list, sorting, filtering, grouping, or row and column extraction. A plain Python `dict` or `list` is not a source action target. A `Series` gains no action.

## 3. Layer 000 — headless conversion

Create two pure functions in `pbui.records`:

| Function | Accepted input | Return value |
|---|---|---|
| `to_dataframe(value)` | Exactly a `JsonObject`, or exactly a `JsonArray` whose elements are all exactly `JsonObject` values | A new pandas `DataFrame` |
| `to_json_records(frame)` | A pandas `DataFrame`, including a subclass | A new `JsonArray` whose elements are `JsonObject` values |

An empty `JsonArray` is eligible because every element satisfies the record condition. Reject a mixed array, an array of primitives, a plain list or dict, and other unsupported inputs rather than silently filtering or wrapping them. The functions do not append history or alter `_`; they either return the complete new value or raise an ordinary exception with a useful message. Conversion failure must not leave a partial result in history when these functions are used by the listener in layer 001.

### 3.1 JSON to frame

For an array, create one row per element in original array order. The columns are the union of record keys in first-seen order: visit records in array order and each record's keys in their stored order. For one object, create one row with that object's keys in their stored order. An empty array yields a frame with shape `0×0`, summarized by the existing printer as `DataFrame 0×0`. An empty object yields one row and zero columns. Use the ordinary positional index; the source JSON has no index field.

Each key must be a string, as in JSON. A key absent from a particular record is a missing cell (`pd.NA` is suitable); an explicit JSON `null` remains Python `None`. Preserve scalar JSON strings, integers, finite floats, booleans, and null as those Python values in cells without pandas numeric or boolean coercion. A nested `JsonObject` or `JsonArray` remains that same object in one cell. It does not create columns, rows, or a nested table. Construct object-valued columns or cells as needed to maintain this rule. The inspector displays both a missing cell and explicit null as `NA` under its existing display rule.

The source object and its nested values are not mutated. The new frame may hold references to nested JSON values; no deep-copy or lossless round trip is promised. Validate the JSON tree in artificially constructed wrappers too: object keys must be strings, scalar leaves must be JSON data, numbers must be finite, and cyclic containers are invalid. Validate nested wrappers without flattening or copying them. Unsupported source keys or values raise a conversion error; do not create display strings as a substitute for data.

### 3.2 Frame to JSON records

Convert the **whole** frame in its current row order, including rows and columns beyond the visible preview. Each row becomes one `JsonObject`; the result is one `JsonArray` of those objects. Visit columns in their frame order and use the string column labels as keys. Exclude the index entirely, even when it has a name or is a MultiIndex. A zero-row frame yields an empty `JsonArray`; it cannot retain column schema in that result. Duplicate column labels cannot be represented as distinct JSON keys, so reject them instead of dropping or overwriting a value. Reject every non-string column label, even in a zero-row frame.

Convert cells recursively to JSON data. A missing scalar, including `None`, `pd.NA`, `pd.NaT`, and numeric NaN, becomes `None` (JSON null). Python and NumPy integer, finite floating, and boolean scalars become Python `int`, `float`, and `bool`; strings stay strings. A pandas `Timestamp`, Python `datetime.datetime`, or NumPy `datetime64` becomes an ISO-8601 string, preserving an offset when present. A `JsonObject`, `JsonArray`, plain `dict`, or plain `list` in a cell becomes a newly built nested `JsonObject` or `JsonArray` by the same rules. Nested mapping keys must be strings. Test missingness only for scalar results; pandas' array-valued `isna` result for a container must not make that container a missing cell. Reject infinite numbers, unsupported scalar or container types, cycles, and any value that cannot become this JSON tree. Do not stringify an unsupported value. Build the complete array before returning it, so any invalid cell rejects the entire conversion.

The frame is not mutated. This is not a lossless round trip: its index is omitted, missing values become null, and timestamp strings do not become timestamps on a later `To DataFrame` action.

### 3.3 Focused tests

`tests/test_records.py` tests both functions without Textual or network access. Cover a two-record array with keys first encountered in different records, row order, source scalar types, an absent key, explicit null, one object as one row, empty array as `0×0`, and an ineligible mixed array. Assert a nested JSON object remains one cell by identity and does not add a column. Test whole-frame conversion with a named index and more than the preview's 12 rows or 6 columns; the result must include all data and no index key. Cover missing cells, timestamps and offsets, nested dict/list and JSON wrappers, and pandas or NumPy scalar cells. A non-string column label, duplicate label, non-string nested key, infinity, and an inconvertible cell must each raise without a partial result. Do not access the network.

The stop for records 000 is the pure conversion API and these focused tests. Menu discovery, history append behavior, documentation, the screen test, the live hand check, and the demo belong to records 001.

## 4. Layer 001 — retained actions and screen behavior

Expose exactly one new action on each eligible source: `To DataFrame` for an exact `JsonObject` and for an exact `JsonArray` whose every element is an exact `JsonObject`, including an empty array; `To JSON records` for a pandas `DataFrame` or subclass. A `JsonArray` with any other element has no action from this series and keeps `Right: no menu`. `Series` keeps `Right: no menu`. Keep plain `dict`, plain `list`, other Value classes, and existing request and response menus unchanged. Do not add a disabled menu item.

Use the existing Value translator route in `HeadlessListener.python_translators_for` and `invoke_python_translator`. Selecting an item records a `MenuActionInput` before its result, targets the exact retained source object, and applies the matching pure function. On success it appends the new frame or `JsonArray` as a Value, sets `_` to that new value, and leaves the source Value row intact. On failure it appends exactly one `Error`, appends no result Value, leaves `_` unchanged, and leaves the source row intact. The existing 500-row history limit may later evict older rows; this action does not explicitly replace or remove the source. The saved menu action's `run again` uses the same source object and conversion under the existing replay rule.

Ordinary left click remains unchanged: JSON lists its immediate members, and a frame opens its bounded snapshot preview. A click on a preview column or row still performs the existing extraction. During Python composition, a left click still inserts a chip at a valid site. Pending accepts and an open menu keep their existing priority. The new conversions run only when their menu item is chosen or its saved action is replayed.

Keep the current target-first documentation format. Eligible ordinary hover sentences are exactly:

```text
JSON OBJECT (N keys) • Left: list members • Right: menu
JSON ARRAY (N elements) • Left: list members • Right: menu
DATAFRAME • Left: show frame preview • Right: menu
```

For an ineligible array, the same left clause ends `Right: no menu`; the existing `SERIES • Left: list values • Right: no menu` remains. In composition, use the existing insertion or refusal left clause and derive `Right: menu` from actual action availability. During an accept, keep `Right: no menu`. A chosen menu item uses the existing registered-Value item sentence, such as `MENU “To DataFrame” ON JSON ARRAY (2 elements) • Left: apply • Right: no menu`. No special documentation mode is added.

Extend `tests/test_records.py` with headless listener tests using retained fixture Values. Verify exact action availability, action input before result, successful `_` update, retained source identity, one `Error` and unchanged `_` for a non-string label and an inconvertible cell, and replay against the saved object. Test a missing cell appears as `NA` in the existing frame preview. Extend `tests/test_bottom.py` with eligible and ineligible JSON, frame, Series, composition, and selected-item wording. Add **one** screen test in `tests/test_terminal.py`: open `To DataFrame` on a fixture `JsonArray` of records, choose it, open `To JSON records` on the resulting frame, choose it, and left-click the resulting JSON array to list its records. Assert the ordinary left click and documentation still match the rules above. Screen and headless tests use fixtures and never open a socket.

After `uv run pytest`, perform one live hand check from a disposable directory under the project root with `uv run pbui`. Enter this command as one line:

```text
:get https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny?sort=-record_date&page[size]=10&fields=record_date,tot_pub_debt_out_amt
```

Choose `perform`, then `json`, then dig into the `data` member. Choose `To DataFrame` on that array. Its summary must show one row per returned record and columns including `record_date` and `tot_pub_debt_out_amt`; open the frame preview and read those columns. Choose `To JSON records` on that frame and left-click the resulting array to list its records. The amount fields remain text unless their values were already numeric JSON. Do not require a particular date, amount, or record count. If the host refuses the request, report that and leave the automated gate unchanged; do not replace fixture tests with a network test.

Write `docs/design/implementation/records/demo.md` after implementation as a hands-on tour of that same path. Include the exact launch command and URL, explain where to type and how to stop, and state that debt figures change. Do not store a live response body. The demo describes implemented behavior and does not change this spec or product code.

The stop for records 001 is the action integration, tests, hand check, and demo. Do not start a later feature.

## 5. Verification and acceptance

The automated gate for each checkpoint is `uv run pytest`, with all existing tests still passing. Records 000 must prove the complete pure conversions and rejections with no Textual import or socket. Records 001 must prove the Value menu eligibility and ordering, history and `_` outcomes, documentation clauses, preserved left clicks, and the fixture screen path. The Treasury path is a separate manual check whose result is reported; it is never an automated test dependency.

The series is complete when an eligible JSON array produces one frame row per record in first-seen column order, one JSON object produces one-row frame, and a frame produces whole-frame JSON records without its index. Missing keys stay missing cells, explicit and pandas missing values become null when returned to JSON, nested objects remain cell values on the way into a frame, and unsupported labels or cells yield one `Error` with no partial output. The original source stays in history subject only to its normal bound. JSON still digs on left click, a frame still opens its preview on left click, and the new actions appear only in their specified menus. `requires-python` remains `>=3.11`, no dependency is added, and all prior tests pass.
