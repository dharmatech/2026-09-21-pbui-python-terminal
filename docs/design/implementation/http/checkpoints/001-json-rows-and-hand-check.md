# http 001 — JSON rows and hand check

**Status.** Implemented per user report. `uv sync` succeeded and
`uv run pytest` passed 289 tests. The prescribed live URL returned HTTP 403
and offered only `body`, so the JSON walk was unavailable.

## Goal and authority

Finish the HTTP exploration by drawing JSON collections as one-line summaries,
letting a click append one bounded level of members, and connecting the
completed headless HTTP actions to the terminal screen. Verify the interaction
with automated tests and the single live HTTPS hand check.

- Identity is `(http, 001)`, spoken **http 001**.
- The human-reviewed [`../spec.md`](../spec.md), especially sections 1, 3–5
  and **http 001 — JSON rows and hand check**, is the authority. Follow it
  wherever this checkpoint is silent. The charter is not an implementation
  input.
- Http 000 is implemented in the existing headless listener. The user's
  completion report says `uv sync` and all 281 tests passed. Preserve its
  `:get`, transport, request and response identity, body-size rule, JSON
  validation cache, `perform`/`json`/`body` action order and replay, transcript
  rows, and `_` behavior. Do not repeat that slice.
- Work in the existing project at
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Keep code in
  `src/pbui/` and tests in `tests/`. Add no dependency. Only `pbui.terminal`
  may import Textual.

## File and feature boundary

Extend the headless presentation and click operations in
`src/pbui/commands.py` and `src/pbui/repl.py`. Use `src/pbui/text.py` or the
existing drawing substrate if a pure helper is needed for a one-presentation
member row. Edit `src/pbui/terminal.py` for history click routing,
request/response menus, documentation, and screen refresh. Change
`src/pbui/http.py` only if a small JSON-row helper belongs with its value
classes. Add focused tests to `tests/test_http.py` and screen tests using the
existing `PbuiApp.run_test()` pattern in `tests/test_terminal.py` or a focused
new test file. Preserve predecessor assertions and menu geometry.

Do not add a command or transport feature, change the production GET policy,
register a printer for plain `dict` or `list`, or implement collection
editing. The screen must call the headless HTTP actions from http 000 rather
than fetch, parse, or synthesize Python source itself.

## JSON summaries and one-level dig

Register class-specific row printers for `JsonObject` and `JsonArray` using
the existing `Value` presentation. Draw exactly `▸ JsonObject (N keys)` and
`▸ JsonArray (N elements)`, with `N` equal to the immediate count. The `▸`
belongs to the collection's own presentation and marks the parent summary
row. Retain the original Python object by identity. A plain Python `dict` or
`list` keeps its generic row and generic `Value` detail click.

At an ordinary non-accept prompt, a first left click on a JSON collection
summary appends only its immediate members. Use object source order or array
index order. Append at most **100 member rows** per dig. If more members
exist, append one literal row `… (N more members)` after them, where `N` is
the omitted count; this trailer has no presentation, hit target, action menu,
or stored object. An empty collection appends nothing. Clicking the same
summary again appends another copy of the same bounded level. A dig does not
replace, edit, or remove the parent row and does not create a menu-action
input row. The existing 500-logical-row history limit still applies and may
eventually evict it; one bounded dig cannot itself evict a parent among the
newest 400 rows.

An object member draws `["KEY"]  VALUE_ROW`; an array member draws
`[INDEX]  VALUE_ROW`. `KEY` is its JSON string key, escaped for safe display;
`INDEX` is the zero-based decimal index. `VALUE_ROW` is the member value's
normal one-line `Value` text, including `▸` and the count for a nested JSON
collection. Cap the key label at 48 display cells and the complete member
row at 120 display cells, with `…` inside each cap. Keep short keys, indexes,
and values complete. A member row is **one presentation of the member value**:
its bracketed label and value text have the same hit target, and the stored
object is never the key or index. The parent's separate summary remains its
own hit target. A nested collection member's whole row, including its label
and `▸`, targets that nested collection; left click appends its next level.
Scalar members retain generic `Value` detail behavior and any action menu
their value class already has. Physical wrapping must preserve the same
presentation hit area on every visible segment.

Do not add an `append`, `with`, or other collection-building menu for
`JsonObject` or `JsonArray`. The JSON subclasses continue to support ordinary
Python subscripting and iteration. Do not give plain Python containers the
dig behavior.

## Screen routing, menus, and documentation

Wire first left clicks through the existing priority order: an open popup
owns its cells; pending presentation accept or substring accept remains
modal; at a valid Python expression position, including continuation, a
`Value` click inserts its stored object as one atomic chip; other Python
positions retain the existing refusal and do not dig or show detail. Only a
default JSON collection click digs. Requests and responses retain generic
`Value` detail clicks. Typed `:show`, `:rm`, `:cd`, `:kill`, and listing accepts
must continue to reject these `Value` targets.

Use the headless action list already supplied by http 000 for a request's
single `perform` item and a response's eligible `json` then `body` items.
Right-click or `Ctrl-O` opens the existing bordered popup at its established
anchor under the popup geometry and dismissal rules. An invalid or non-JSON
response has no `json` item; opening its menu does not parse or add an error.
Selecting an item uses the popup's saved target and resolved operation,
records `MenuActionInput` before the result, and preserves Python composition
through the existing menu suspension path. A saved `run again` action still
uses the original target object and operation. A JSON collection has no
popup; a scalar member uses its own class's existing items, if any. Keep the
menu border and literal trailer out of presentation hit maps.

Use these exact ordinary hover sentences for JSON collections:

- `JsonObject`: `Left: list this JSON object's members. Right: no menu.`
- `JsonArray`: `Left: list this JSON array's members. Right: no menu.`

A request or response uses `Left: show this Python value. Right: menu.`
During Python composition, including continuation, use the existing valid
chip-insertion or invalid-position refusal sentence with `Right: menu.` for
requests and responses or `Right: no menu.` for JSON collections. Pending
accepts keep the existing `Value` refusal; a pending substring accept keeps
its own sentence. A hovered HTTP menu item uses the popup's registered Python
value item sentence. An open menu and its border retain their documentation
precedence. The documentation for a member row follows its value, including
when the pointer is on the key or index label. The literal trailer has no
presentation and uses the ordinary no-target documentation.

## Automated verification

Run the complete predecessor suite. Headless and screen tests use an injected
fake GET result and never open a socket. Cover at least:

1. A `JsonObject` and `JsonArray` show the exact summary rows and immediate
   counts. A plain Python `dict` and `list` retain generic rows and generic
   detail clicks. No plain-container printer or collection-building menu is
   registered.
2. One dig of an object or array appends members in key/index order with the
   exact labels and original member objects. The parent row is the same
   retained presentation. A nested member row is wholly hit-testable as its
   own collection, and clicking it appends only its next level. A scalar
   member keeps its normal detail click. Empty collections append nothing;
   a 101-member collection appends 100 member presentations and one literal
   `… (1 more members)` trailer. The trailer is inert. Use a small enough
   history that the 500-row limit does not evict the parent in these tests.
3. Escaping and both display-cell caps preserve a short key and short value
   in full, bound long or unsafe keys and values, and keep every cell of the
   bracketed label and value text on one presentation. Screen tests check
   summary and member hit areas, including wrapped rows where applicable.
4. The screen offers `perform` for a request and the correct instance-specific
   `json`/`body` order for responses. With fake data, choosing these items
   produces the already specified transcript/result order and object
   identity. Check button-3 placement and `Ctrl-O` with the existing popup,
   no menu for JSON collections, and no disabled `json` for an invalid or
   non-JSON response.
5. Check the exact ordinary and composition documentation above, menu item
   and border precedence, pending accept and substring-accept precedence,
   atomic Python-chip insertion of a JSON collection by identity, and
   refusals at invalid insertion sites. A dig must not run during those
   higher-priority states.

## uv workflow and live hand check

From the project root, use only the existing uv-managed environment:

```console
uv sync
uv run pytest
```

`uv run pytest` is the automated gate. If uv is unavailable, stop and report
it; do not use `pip`, `python -m pip`, `uv pip install`, Poetry, Pipenv, Conda,
Hatch, a hand-made environment, or global Python.

After the automated gate passes, make and record a disposable directory
under the project root and start `uv run pbui` from that directory. Enter
`:get https://www.reddit.com/r/python/new.json`, choose `perform`, then
`json`, and click into at least two nested levels, for example `data` and
then `children`. Observe each parent retained while its member rows appear.
This is the only required live URL; it ends in `.json` and needs no login or
API key. If the network refuses the request, record the resulting `Error`
and stop the hand check without trying another host. A non-redirect HTTP
error status still appears as a response; record it if it prevents the JSON
walk. Do not convert that status into a transport `Error`.

Http 001 is complete when the JSON rows, bounded dig, screen interaction,
documentation, automated suite, and that hand check have been recorded.
Stop there. POST, PUT, user headers, cookies, authentication, HTML browsing,
pandas, SQLite, general collection menus, images, streaming, and unbounded
bodies remain outside this exploration.
