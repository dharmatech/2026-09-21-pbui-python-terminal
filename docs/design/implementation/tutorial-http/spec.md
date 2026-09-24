# Specification — HTTP section in the tutorial

**Status:** accepted. This file is the complete design input for the checkpoint manager and implementers. It assigns no implementation work by itself.

Add one short HTTP section to pbui's local tutorial. Its four cards teach the existing path from a retained `:get` request to a response, a parsed JSON value, and one-level digs into that value. The only live example is the USGS magnitude 2.5+ past-day GeoJSON feed. Tutorial cards and Try remain local and inert; the user chooses `perform` to make the request.

## 1. Checkpoint series

The series identity is **tutorial-http**. Checkpoint 000 is spoken **tutorial-http 000** and filed as `docs/design/implementation/tutorial-http/checkpoints/000-slug.md`. Numbers have three digits, start at 000, are never renumbered, and use lowercase words separated by hyphens for slugs. The checkpoint manager writes only the next missing checkpoint, then stops. Each implementer handles only the assigned checkpoint and stops. After the user accepts this spec, this file is the design authority for both roles; the charter was the spec writer's assignment.

The layer order is **local cards and headless behavior** (tutorial-http 000), then **visible controls, screen coverage, and live hand check** (tutorial-http 001). Each is one logical part that can be built and tested within one implementer conversation. The second layer verifies that the existing generic renderer exposes the new cards correctly. If a layer is too large for one implementer conversation, the checkpoint manager may split it, preserving this order and adding no features.

## 2. Product boundary and authority

The full-screen Linux listener already retains request, response, `JsonObject`, and `JsonArray` values. `:get URL` creates a `GetRequest` without network access. The request menu's `perform` action makes one GET and appends a separate `HttpResponse` or an `Error`. A qualifying response menu offers `json` and `body`; `json` appends the retained parsed value, while `body` appends decoded text. Clicking a JSON collection at an ordinary empty prompt appends at most one level of members. During Python composition, clicking a retained JSON value inserts that object as a chip. The accepted [HTTP specification](../http/spec.md) governs those actions, their input rows, menu eligibility, errors, transport, 2 MiB response limit, and 100-member dig limit. This series changes none of them.

The accepted [sections specification](../sections/spec.md) governs the Contents → section → leaf hierarchy, links, card labels, and documentation. This spec extends Contents membership from Listener and SymPy to **Listener, SymPy, HTTP**, in that order. The accepted [tutorial specification](../tutorial/spec.md) governs card presentation, Try, and the original Listener lessons. The existing Listener and SymPy section bodies, leaf bodies, examples, order, identifiers, and `:tutorial` entry point remain intact. `:tutorial` still appends Presentations directly. The current source and tests show the implemented seams. The [HTTP demo](../http/demo.md) illustrates interactions but does not change these rules.

The tutorial does not add a command, presentation type, card level, HTTP action, parser, URL rule, transport behavior, retry, local server, fetched card content, or second API walkthrough. The longer HTTP demo remains the place for action replay, invalid JSON, HTTP error status, and the 100-member limit. The only public example is `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson`.

[USGS documents the feed structure](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php): root `metadata` and `features`, metadata `title` and `count`, and a feature's `properties` with `place` and `mag`. The feed is live. No card or test fixes a count, event ID, first earthquake, place, magnitude, or complete response body. The structure makes `metadata` useful even if `features` is empty. A successful public GET is not guaranteed; network access is needed only for a user-selected `perform`.

## 3. Host, layout, and commands

The project root is `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. This is the existing Python 3.11+ `src/pbui/` package with tests in `tests/` and a `pbui` console entry point. Code and tests go at that root, not in this design folder. `src/pbui/tutorial.py` owns immutable card data, stable lookup, and pure row drawing. `src/pbui/commands.py` already owns `:tutorial`, navigation, Try, and HTTP actions. `src/pbui/bottom.py` already formats control documentation; `src/pbui/terminal.py` is the Textual screen adapter. Only `pbui.terminal` imports Textual. This series expects new product data only in `tutorial.py`; the existing generic command, documentation, HTTP, and screen paths should serve it.

The project is already initialized and uv-managed. Do not run `uv init`, add a dependency, or edit `pyproject.toml` or `uv.lock` for this series. From the project root, implementers use `uv sync` to refresh the environment, `uv run pytest` for the automated gate, and `uv run pbui` for the hand check. Focused test commands, if used, also run through `uv run pytest`. If uv is unavailable, stop and report it rather than switching Python tools. The spec writer does not run uv.

## 4. Local cards and headless behavior — tutorial-http 000

### 4.1 Stack and exact card data

Keep the three existing card roles. Contents has no parent and lists section cards. A section lists its leaves and has Up to Contents; it has no Back or Next. A leaf has Back and Next among siblings and Up to its section; it has no entries. Opening any enabled link appends a fresh presentation of the destination's existing stored `TutorialCard` object. It neither replaces older rows nor changes the editor or records an input row. Disabled first Back and last Next append nothing. Navigation on HTTP leaves never enters Listener or SymPy.

Keep `TutorialStack.tour`, `TutorialStack.sympy_leaves`, `TutorialStack.sections`, and `TutorialStack.contents`; add an ordered `http_leaves` tuple and include its cards in `TutorialStack.get(identifier)`. Existing identifiers remain unchanged. The new section identifier is `http`; the four leaf identifiers, in order, are `http-request`, `http-perform`, `http-json`, and `http-browse`. All identifiers resolve to the same stored instances used by links and entries. `sections` and `contents.entries` have exactly Listener, SymPy, HTTP. The Contents title and body stay exactly `Contents` and `Choose a card to append it to history.`

The HTTP section title is `HTTP`. Its body lines, in order, are:

1. `Requests, responses, and JSON stay as separate objects in history.`
2. `Try starts one public USGS feed; perform is the network step.`
3. `The feed is live, so counts and events can change.`
4. `Up returns here from any of these cards.`

Its entries are the four leaves below, in order. Its only navigation link is `TutorialLink("Up", "contents")`. Each leaf has `TutorialLink("Up", "http")`, Back to its preceding HTTP leaf (or `None` on the first), and Next to its following HTTP leaf (or `None` on the last). Leaf titles and body lines are exact local package data:

| Identifier and title | Body lines, in order |
|---|---|
| `http-request` — `1. Make a request` | `Try loads the USGS :get command; Enter runs it.`<br>`The GET row is a retained request, not a response.`<br>`Neither opening this card nor Try fetches anything.` |
| `http-perform` — `2. Perform the GET` | `Open the GET row's menu and choose perform to fetch.`<br>`The request stays; a response or Error appears below it.`<br>`On a response, body shows its decoded text.`<br>`Use json on that same response to open parsed data.` |
| `http-json` — `3. Open JSON` | `Open the response row's menu and choose json.`<br>`The new JsonObject summary is the parsed value.`<br>`At an empty prompt, click it to list root members.`<br>`Click ["metadata"] to list title and count.` |
| `http-browse` — `4. Browse and reuse` | `From the root members, click ["features"] to list array members.`<br>`If [0] appears, click it, then ["properties"].`<br>`Read place and mag; the events and counts can change.`<br>`To reuse a JSON row, type len(, click it, type ), then Enter.` |

Only `http-request` has a Try example. Its displayed source is exactly `:get https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson`, and its saved input is one `CommandInput("get https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson")`. The other three leaves have no Try examples. This uses the existing `TutorialExample`, `TutorialLink`, `TutorialCard`, and `TutorialTarget` types; no new presentation or command type is needed. The section's body and all four leaf bodies fit the existing 20-logical-row card cap after wrapping at 120 display cells.

The wording distinguishes the inert request from `perform`, the retained response from the parsed JSON value, and `body` from `json`. The user visits `metadata` before `features`. `[0]` is conditional because the array can be empty. `place` and `mag` name fields, not promised values. The Python note uses an existing retained collection row as an object, without introducing another request or Python API lesson.

### 4.2 Headless navigation, Try, and fake result

The existing pure card drawer produces the section entries, Try control, and Back, Next, and Up controls. Its 20-logical-row cap, nested hit priority, text escaping, and 500-row history limit remain in force. Card construction and drawing are local: they must not read the feed, import HTTP data, open a socket, or inspect the filesystem or processes. Showing any HTTP card, following a link, and clicking Try do not call the GET transport.

Try loads the saved `:get` line into an empty ordinary editor, puts the cursor at its end, and appends no history row. It refuses without changing the editor or history when text, chips, continuation, a pending accept, substring accept, or popup make the editor busy. Enter later submits the command, adding its ordinary `CommandInput` transcript row and a `GET URL` request row, with no fetch. The existing request menu is the only way this lesson calls the transport; a chosen `perform` records a `MenuActionInput` and adds a response or `Error` under the HTTP specification. No tutorial navigation or Try click invokes `perform`, `json`, or `body`.

In `tests/test_tutorial.py`, extend the immutable-stack assertions and the existing no-I/O construction guard to cover the HTTP section and leaves. Prove all stable IDs, exact titles, bodies, source and saved input, entry order, parent and sibling destinations by identity, enabled and disabled boundary behavior, the unchanged Listener and SymPy data, and `:tutorial` still opening Presentations. Use retained controls to prove Up from an HTTP leaf appends HTTP, Up from HTTP appends Contents, and neither Back nor Next crosses a section. Prove navigation appends a fresh outer card presentation while retaining the same card object and preserving editor state. Prove Try's ready and busy behavior and that neither construction, navigation, nor Try calls an injected GET transport.

Include one small fake-transport walkthrough in headless tests, using a synthetic JSON response with `metadata` and a `features` array containing a feature with `properties`, `place`, and `mag`. After Try and Enter, assert that the fake has not been called. Invoke the existing `perform` action and assert it is called once; then use the existing `json` action and ordinary empty-prompt digs to reach metadata and a feature's properties. The fixture proves type and navigation shape, not any current USGS data. Do not call production HTTP or contact USGS in an automated test. Existing HTTP tests remain the authority for transport limits, parser errors, and body formatting; this walkthrough need not duplicate them.

## 5. Visible controls and screen coverage — tutorial-http 001

The generic card drawing shows the HTTP section as title, the four section body lines, `[1. Make a request]`, `[2. Perform the GET]`, `[3. Open JSON]`, `[4. Browse and reuse]`, then `[Up: Contents]`. Contents shows `[Listener]`, `[SymPy]`, `[HTTP]` in that order and has no Back, Next, or Up. The HTTP section has no Back or Next. Each HTTP leaf ends with `[Back]  [Next]  [Up: HTTP]`; Back on Make a request and Next on Browse and reuse are visible, dimmed, and unclickable. The first leaf alone has a Try row: `[Try] :get https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson`.

Each bracket and label is one nested control hit area. The spaces, title, body, and example source outside `[Try]` belong to the outer card. The stored `TutorialTarget.label` matches the drawn control. Existing scroll, resize, popup, accept, click, and history rules remain unchanged. There is no new documentation case. At an ordinary prompt, the current target-first documentation yields these exact representative sentences:

| Target | Sentence |
|---|---|
| Contents entry for HTTP | `TUTORIAL CONTENTS “HTTP” • Left: open • Right: no menu` |
| First leaf's enabled Next | `TUTORIAL NEXT “2. Perform the GET” • Left: open • Right: no menu` |
| HTTP leaf's Up | `TUTORIAL UP “HTTP” • Left: open • Right: no menu` |
| HTTP section's Up | `TUTORIAL UP “Contents” • Left: open • Right: no menu` |
| First leaf's disabled Back | `TUTORIAL BACK • Left: this section has no previous card • Right: no menu` |
| Last leaf's disabled Next | `TUTORIAL NEXT • Left: this section has no next card • Right: no menu` |
| Ready Try | `TUTORIAL TRY • Left: load example into editor; Enter runs • Right: no menu` |
| Busy Try | `TUTORIAL TRY • Left: finish or cancel current input before trying • Right: no menu` |

Other HTTP entry and enabled Back/Next sentences follow the same existing destination-title rule. The accepted sections and tutorial specifications govern documentation in pending accept and popup contexts, and the HTTP specification governs request, response, and JSON documentation. No HTTP-specific wording is added to `bottom.py`.

Extend `tests/test_terminal.py` to show the three Contents entries, the four HTTP entries, the full first Try row, and the absence of sibling controls on Contents and HTTP. In one representative screen path, start at `:tutorial`, go Up to Listener, Up to Contents, enter HTTP, open Make a request, use Next through the leaves, verify the disabled end controls, then use Up to HTTP and Up to Contents. Check that nested hits resolve to stored targets, right-click on a tutorial control opens no menu, and the representative documentation sentences above appear. Preserve screen coverage for Listener and SymPy, updating only assumptions that Contents had two entries. Use an injected no-network transport for this screen test; it does not need to perform a GET. `tests/test_terminal.py` is the expected edit for this layer. If the existing generic renderer itself needs a minimal correction exposed by these cards, restrict it to tutorial handling in `src/pbui/terminal.py` or `src/pbui/bottom.py`; do not change HTTP transport or parsing.

## 6. Verification

The automated gate is `uv run pytest` from the project root, after `uv sync`. Focused runs may use `uv run pytest tests/test_tutorial.py tests/test_terminal.py`, followed by the full gate. All automated HTTP results are injected or fake; tests never call the public feed. They prove the exact Try source, inert card construction and Try, a request before fetch, the four-leaf stack and bounded controls, parent and sibling navigation, a synthetic response-to-JSON walk, and visible entry and control behavior. Existing suite tests remain green.

After tutorial-http 001 passes the automated gate, perform one manual check from the project root with `uv run pbui`; no local server, temporary files, API key, or account are required. In one session, enter `:tutorial`, use Up to reach Contents, open HTTP, and open Make a request. Click Try and verify it loads the exact saved command without a network result. Press Enter and verify the retained `GET` row appears. Use Next to read Perform the GET, then choose `perform` from the GET row's menu. If a response appears, use its `body` action briefly to see decoded text, then use `json` on the same response. Continue through Open JSON and Browse and reuse: dig the root `JsonObject`, inspect `metadata` title and count, inspect `features`, and, if an array member exists, click one feature and its `properties` to see `place` and `mag`. Confirm the displayed counts and values are treated as live. At a valid Python expression prompt, use a retained JSON collection row to try `len(` + object chip + `)` and Enter. Confirm leaf Up goes to HTTP and section Up goes to Contents. Ctrl-C exits pbui.

If `perform` produces a transport `Error` because the network is unavailable, record that visible `Error` and stop the live portion. If a response is returned but JSON is unavailable or invalid, record the response and existing parse `Error` and stop the JSON portion. Do not retry automatically, change hosts, or relax the response limit. The automated fake-result walkthrough and screen tests remain the deterministic evidence for those paths.

## 7. Acceptance

The series is complete when Contents lists Listener, SymPy, HTTP in order; the original two sections and `:tutorial` entry behavior remain intact; HTTP has exactly the four specified local leaves and their links remain within HTTP; the first Try loads exactly the USGS `:get` line without fetching; Enter makes a retained request and only explicit `perform` calls the transport; the cards guide a response through `json`, `metadata`, conditional `features` members, `properties`, `place`, and `mag`; the same response's `body` and one retained JSON value's Python reuse are explained briefly; no live value is hard-coded; card construction stays local; the headless and screen evidence in sections 4–6 is present; the existing `uv run pytest` suite passes; and the live hand check succeeds or records the existing network/JSON error path as specified.
