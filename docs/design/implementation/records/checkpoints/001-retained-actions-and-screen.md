# records 001 — Retained actions and screen behavior

**Status.** Implemented. After the scope amendment, `uv sync`, the focused
suite (138 passed), and the full suite (471 passed) completed. The listener
was launched from `records-001-hand-PbQRFd`; the live Treasury request could
not proceed because this host could not resolve the API domain. The fixture
screen path passed, and the demo is written.

## Goal

Expose the completed JSON/frame conversions as Value menu actions, verify
their history and documentation behavior through headless and screen tests,
perform the Treasury hand check, and write the demo. Stop when this slice is
complete. Do not add other conversions or a new menu route.

## Authority and starting point

The implementer receives this checkpoint and the accepted
[`../spec.md`](../spec.md); the checkpoint narrows the spec to one slice and
does not revise it.

- Identity: **records 001**. Numbers have three digits, begin at 000, and are
  never renumbered. The implementer completes this checkpoint and stops.
- Read spec sections 1–2, section 4, and the records 001 verification and
  acceptance in section 5. Section 3 defines the pure conversion API consumed
  here. The accepted spec governs where this checkpoint is silent; the
  charter is not an implementation input.
- Predecessor: [records 000](000-headless-conversions.md) is implemented per
  user report. `uv sync`, 18 focused tests, and all 464 project tests passed.
  Its `pbui.records.to_dataframe` and `to_json_records` functions are the
  starting point, not a slice to reimplement.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.
  Code and tests belong there; the demo belongs beside this checkpoint's
  parent spec.

## File scope

Edit only `src/pbui/commands.py`, `src/pbui/bottom.py`,
`tests/test_records.py`, `tests/test_bottom.py`, and `tests/test_terminal.py`.
In `tests/test_http.py`, change only the action-availability assertion in
`test_json_summary_dig_nested_identity_and_plain_containers` from no actions
to the single `To DataFrame` action required for its exact `JsonObject`.
Preserve that test's JSON dig, identity, and no-menu-action-row assertions.
Create `docs/design/implementation/records/demo.md` after implementation and
the hand check. Update the Demo row and status line in
`docs/design/implementation/records/README.md` when the demo is written; the
checkpoint's own status may record completion and verification results.

Leave `src/pbui/records.py`, `src/pbui/terminal.py`, the HTTP transport,
pandas inspector, all other source and tests, `pyproject.toml`, `uv.lock`, and the
accepted spec untouched. The existing terminal already obtains Value menu
items through `python_translators_for` and dispatches the selected item; use
that path. Add no dependency or new widget, click route, command, presenter,
or conversion feature. If another file is necessary, stop and send this
checkpoint back to the checkpoint manager instead of widening the slice.

## Value actions and retained history

In `HeadlessListener.python_translators_for`, offer exactly one new action per
eligible source:

| Retained Value | Action |
|---|---|
| Exact `JsonObject` | `To DataFrame` |
| Exact `JsonArray` containing only exact `JsonObject` elements, including an empty array | `To DataFrame` |
| `pandas.DataFrame` or subclass | `To JSON records` |

An ineligible `JsonArray`, `Series`, plain `dict` or `list`, and other generic
Values gain no records action. Preserve request, response, and other existing
menus. Eligibility is based on the source shape/type; data validation belongs
to the chosen conversion, so an otherwise eligible object with invalid data
still offers its item and yields an Error when chosen. Do not add a disabled
item.

Use the existing `ValueTranslator` and `invoke_python_translator` route with
the pure functions from records 000. Choosing an item records one
`MenuActionInput` before its result and acts on the exact retained source
object. Success appends one new `Value` containing the new frame or
`JsonArray`, updates `_` to it, and leaves the source row intact. Failure
appends exactly one `Error`, no result `Value`, and leaves `_` and the source
row unchanged. Normal 500-row history eviction still applies. A saved action's
`run again` calls the same conversion on its saved source object under the
existing replay rule, including after that source row leaves history.

Keep ordinary left clicks and their priority unchanged: JSON lists immediate
members; a frame opens its bounded snapshot preview; its row and column hits
extract their stored copies. A valid Python composition click inserts a chip;
pending accepts and an open menu retain their current behavior. Conversion
runs only when its menu item is chosen or its saved action is replayed.

## Documentation

The pure formatter in `src/pbui/bottom.py` must give these exact ordinary
target-first sentences for eligible Values:

```text
JSON OBJECT (N keys) • Left: list members • Right: menu
JSON ARRAY (N elements) • Left: list members • Right: menu
DATAFRAME • Left: show frame preview • Right: menu
```

An ineligible array keeps its `list members` left clause and `Right: no menu`;
`SERIES • Left: list values • Right: no menu` remains. In Python composition,
use the existing insertion/refusal left clause and determine the right clause
from the actual action list. During an accept, keep `Right: no menu`. A
selected Value item uses the existing sentence, for example
`MENU “To DataFrame” ON JSON ARRAY (2 elements) • Left: apply • Right: no menu`.
Do not add a documentation mode.

## Automated tests

Extend `tests/test_records.py` with retained fixture Values and headless
listener checks. Assert exact action availability on every eligible and
ineligible source, including an empty array and a DataFrame subclass. Check
the action input immediately precedes the successful Value or failure Error;
success changes `_` to the new object; failure leaves `_` unchanged; and the
source presentation keeps its original object. Exercise failures for a frame
with a non-string column label and a frame with an inconvertible cell. Prove
`run again` uses the saved source object, including after its row is evicted,
and that a missing cell in a converted frame displays `NA` in the existing
preview.

Extend `tests/test_bottom.py` for eligible and ineligible JSON, frame, Series,
composition insertion/refusal, pending accept, and selected-item wording.
Adjust predecessor assertions only where the new eligible-menu clause
requires it. In `tests/test_terminal.py`, the existing JSON-object and
DataFrame screen cases currently assert `Right: no menu`; update those
expectations and any follow-on popup dismissal needed before their left-click
checks. Keep their dig, preview, chip, and accept assertions.

Add **one** fixture-driven screen test to `tests/test_terminal.py`: open the
menu on a retained record `JsonArray`, choose `To DataFrame`, open the menu on
the resulting frame, choose `To JSON records`, then left-click the resulting
array to list its records. Assert the documentation and unchanged ordinary
left-click behavior along that path. Use the existing `PbuiApp.run_test()` and
menu helpers. Headless and screen tests must not open a socket.

The HTTP predecessor test at `tests/test_http.py:308` has an exact
`JsonObject` target. Its action list must now be `["To DataFrame"]`. The test
continues to prove that an ordinary left click digs without recording a
`MenuActionInput`; changing action availability does not change that click.

## Verification, hand check, and demo

From the project root, run:

```console
export UV_CACHE_DIR="$(mktemp -d /tmp/pbui-records-001-uv-cache-XXXXXX)"
uv sync
uv run pytest tests/test_records.py tests/test_bottom.py tests/test_terminal.py tests/test_http.py
uv run pytest
```

`uv run pytest` is the automated gate. The temporary cache avoids the
read-only default cache reported during records 000. Use uv for every Python,
app, and test command. If uv is unavailable, stop and report it; do not
substitute another tool. Do not add a dependency or rerun `uv init`.

After the automated gate, create a disposable directory under the project
root, record its absolute path, and launch from it:

```console
records_hand_dir="$(mktemp -d "$PWD/records-001-hand-XXXXXX")"
cd "$records_hand_dir"
pwd
uv run pbui
```

In the listener enter this command as one line:

```text
:get https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny?sort=-record_date&page[size]=10&fields=record_date,tot_pub_debt_out_amt
```

Choose `perform`, then `json`, then dig into `data`. Choose `To DataFrame` on
that array. Its summary should have one row per returned record and columns
including `record_date` and `tot_pub_debt_out_amt`; open its preview and read
those columns. Choose `To JSON records` on the frame and left-click the
resulting array to list its records. Amounts remain text unless already
numeric in the JSON. Do not require a particular date, amount, or record
count. If the host refuses the request, report that result and keep the
fixture tests as the automated gate.

After implementation, write `docs/design/implementation/records/demo.md` as
a hands-on tour of the behavior just checked. Include the exact launch
command and URL, where the user types, how to stop, and the fact that debt
figures change. Do not store a live response body. Update the README Demo row
and status line when the file exists.

Records 001 is complete when the menu eligibility, history and `_` outcomes,
replay, documentation, preserved left clicks, and fixture screen path satisfy
the accepted spec; the full suite passes; the live check is reported; and the
demo describes the implemented path. Report verification and changed files,
then stop. Do not start another feature.
