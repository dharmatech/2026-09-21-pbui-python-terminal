# tutorial-http 000 — local cards and headless behavior

**Status.** Implemented.

## Goal

Add the HTTP section and its four local cards to the stored tutorial stack. Prove their retained headless navigation, inert Try behavior, and one fake-result walkthrough through the existing HTTP actions and JSON digs.

Stop after the headless behavior and its tests. Visible screen controls, documentation assertions, screen tests, and the live USGS hand check belong to tutorial-http 001.

## Authority and starting point

The implementer receives this checkpoint and the accepted [specification](../spec.md); the checkpoint narrows the spec to one slice and does not revise it.

- Identity: **tutorial-http 000**. This is the first checkpoint; there is no tutorial-http predecessor. Tutorial-http 001 follows in a separate conversation.
- Governing spec sections: 1–3 for series, boundaries, and host rules; 4 for exact card data and headless behavior; 6 for deterministic verification; and 7 for the acceptance conditions this slice can prove. Section 5 governs only the existing generic control shape needed by these cards; its screen coverage belongs to 001.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Code and tests live there, not in this design folder.
- The Listener and SymPy tutorial sections, `:tutorial`, Try, GET request and menu actions, JSON parsing, and one-level dig already exist. Use their current interfaces.

## File scope

May edit `src/pbui/tutorial.py` for the immutable HTTP cards, stack lookup, and generic pure rows if needed. May edit `tests/test_tutorial.py` for the exact stack assertions and focused headless tests.

Leave `src/pbui/commands.py`, `src/pbui/terminal.py`, `src/pbui/bottom.py`, `src/pbui/http.py`, other source and test files, project metadata, and dependency files untouched. In particular, tutorial-http 001 owns `tests/test_terminal.py`. If a needed change falls outside this scope, stop and return the checkpoint to the manager instead of widening the slice.

## Slice requirements

### Stored cards

- Preserve all Listener and SymPy card identifiers, titles, bodies, examples, links, order, and stored identities. Preserve the `:tutorial` entry at Presentations. Keep `TutorialStack.tour`, `sympy_leaves`, `sections`, and `contents`; add an ordered `http_leaves` tuple. Include those leaves and the `http` section in `get(identifier)`.
- Add the `HTTP` section with identifier `http`, exactly the four body lines in spec section 4.1, entries for exactly `http-request`, `http-perform`, `http-json`, and `http-browse` in that order, and only `TutorialLink("Up", "contents")` for navigation. Make `sections` and `contents.entries` exactly Listener, SymPy, HTTP. Keep the Contents title and body unchanged.
- Store the four leaf identifiers, titles, and body lines exactly as specified in section 4.1. Each leaf has Up to `http`, Back and Next only among HTTP siblings, and disabled Back or Next at its section boundary. No leaf has entries. Every identifier resolves to the same stored instance used by its entries and links.
- Give only `http-request` the exact displayed source `:get https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson` and one saved `CommandInput("get https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson")`. The other HTTP leaves have no Try example. Use the existing tutorial data types and pure drawer; add no command, presentation type, HTTP operation, or fetched content.

### Headless interaction

- Draw the new cards with the existing outer card and nested entry, Try, Back, Next, and Up controls. Retain nested control hit priority, labels, disabled boundary controls, the 20-logical-row card cap, escaping, and the 500-row history behavior. Construction and drawing remain local and perform no filesystem, process, or network work.
- Opening an entry or enabled navigation control appends a fresh outer presentation of the stored destination card. It leaves older rows, editor state, and transcript counts intact. Up from a leaf reaches HTTP; Up from HTTP reaches Contents. Back and Next never cross out of HTTP. A disabled boundary control appends nothing.
- Try loads the saved `:get` line into an empty ordinary editor with the cursor at its end and appends no history row. Preserve the existing headless refusals for text, chips, continuation, pending accept, and substring accept. Popup refusal belongs to the screen path in tutorial-http 001. Navigation and Try never invoke the GET transport or any HTTP menu action.
- Enter after a successful Try submits the ordinary `CommandInput` row and a retained `GET` request without fetching. Only the existing `perform` action invokes the injected transport and adds the existing response or `Error` behavior; the existing `json` action and empty-prompt digs open the parsed tree. Do not alter those actions.

## Verification and completion

Extend `tests/test_tutorial.py` to prove the exact HTTP and unchanged existing card data; ordered section and leaf membership; stable lookup and link destination identities; retained nested controls and disabled ends; fresh outer presentations and preserved editor and transcript state; `:tutorial` still opening Presentations; Try's exact source, ready load, and busy refusals; and no GET calls during construction, navigation, Try, or Enter. Extend its existing no-I/O guard to cover the new stack.

Add one small fake-transport walkthrough in that file. Return a synthetic JSON `GetResult` with `metadata` and one `features` member containing `properties`, `place`, and `mag`. Assert no transport call before `perform`, exactly one call after it, then use `json` and ordinary empty-prompt digs to reach metadata and the feature's properties. Assert retained request, response, and parsed collection types and the relevant input rows. Do not contact USGS or repeat the HTTP module's limit and parser-error tests.

From the project root, run:

```sh
uv sync
uv run pytest tests/test_tutorial.py
uv run pytest --ignore=tests/test_terminal.py
```

The current screen test asserts that Contents has only two entries. Tutorial-http 001 updates that assertion and runs the full `uv run pytest` gate. If `uv` is unavailable, stop and report it; do not use another Python tool. Completion of tutorial-http 000 requires the focused and non-screen tests above to pass with no edit outside this file scope. Report the test results and changed files, then stop without starting tutorial-http 001.
