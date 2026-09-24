# tutorial-http 001 — visible controls and hand check

**Status.** Screen implementation and tests complete; direct `uv run pbui` hand check pending.

## Goal

Expose the HTTP section and four leaves through the existing Textual tutorial controls, prove their screen behavior and documentation, then hand check the complete request-to-JSON path with the live USGS feed.

Stop after the screen coverage, full automated gate, and one hand check. This slice adds no new card data, command, HTTP action, parser, transport rule, or second feed.

## Authority and starting point

The implementer receives this checkpoint and the accepted [specification](../spec.md); the checkpoint narrows the spec to one slice and does not revise it.

- Identity: **tutorial-http 001**. Predecessor **tutorial-http 000** is implemented. Its implementer reported `uv sync`, 24 focused tests, and 294 non-screen tests passing. Use its stored cards and retained controls rather than rebuilding them.
- Governing spec sections: 1–3 for series, boundaries, and host rules; 4 for the stored card text, targets, and Try behavior; 5 for visible controls and screen coverage; 6 for verification and the live hand check; and 7 for final acceptance.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Product code and tests live there, not in this design folder.
- `src/pbui/tutorial.py` already holds the HTTP cards and pure rows. `src/pbui/terminal.py` is the Textual screen adapter. `src/pbui/bottom.py` formats the existing target-first documentation. The generic paths should display the new cards without product-code edits.

## File scope

May edit `tests/test_terminal.py` to update its former two-entry Contents assertion and add HTTP screen coverage. If a minimal correction to generic tutorial rendering, hit handling, or documentation is actually exposed by those tests, may edit only tutorial handling in `src/pbui/terminal.py` or `src/pbui/bottom.py`. Do not add HTTP-specific documentation cases.

Leave `src/pbui/tutorial.py`, `src/pbui/commands.py`, `src/pbui/http.py`, `tests/test_tutorial.py`, all other source and test files, project metadata, and dependency files untouched. Keep `pbui.terminal` the only package module importing Textual. If another file becomes necessary, stop and return this checkpoint to the manager instead of widening the slice.

## Slice requirements

### Visible rows and controls

- Contents shows `[Listener]`, `[SymPy]`, and `[HTTP]` in that order, with no Back, Next, or Up. Preserve the existing Listener and SymPy rows and interactions.
- The HTTP section shows its title, four exact body lines from spec section 4.1, entries `[1. Make a request]`, `[2. Perform the GET]`, `[3. Open JSON]`, and `[4. Browse and reuse]`, then `[Up: Contents]`. It has no Back or Next.
- Each HTTP leaf ends with `[Back]  [Next]  [Up: HTTP]`. Make a request has a visible, dimmed, unclickable Back; Browse and reuse has a visible, dimmed, unclickable Next. Only Make a request has the full Try row `[Try] :get https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson`. No other HTTP leaf has Try.
- Each bracketed label is a nested hit area whose stored `TutorialTarget.label` matches its visible label. The title, body, spaces between controls, and example source outside `[Try]` hit the outer card. Preserve scrolling, resize, popup ownership, accept handling, history, and ordinary value and input-row clicks. Right-click on a tutorial control opens no menu. Navigation appends a fresh presentation of the stored destination; disabled boundaries append nothing.

### Documentation and screen path

- At an ordinary prompt, verify the eight exact representative sentences in spec section 5: HTTP Contents entry; enabled Next from Make a request; leaf Up to HTTP; section Up to Contents; disabled first Back and last Next; ready Try and busy Try. Other entries and enabled Back/Next follow the existing destination-title rule. Preserve the accepted sections and tutorial documentation behavior during pending accept and popup contexts, and the existing HTTP documentation for request, response, and JSON rows.
- In one representative screen path, start with `:tutorial`, go Up from Presentations to Listener, then Up to Contents; open HTTP; open Make a request; use Next through all four leaves; verify both disabled ends; then use Up to HTTP and Up to Contents. Check that nested hits resolve to stored targets, that the outer card remains the hit for source text and spaces, and that right-click on a tutorial control opens no menu.
- Use an injected transport that fails if called for this screen path. Screen tests do not perform a GET or contact USGS. Preserve the existing Listener and SymPy screen assertions, changing only those that assumed Contents had two entries.

## Verification and completion

From the project root, run:

```sh
uv sync
uv run pytest tests/test_terminal.py
uv run pytest
```

All automated HTTP results remain fake or injected. The full suite must pass, including tutorial-http 000's headless tests and the existing HTTP tests. If `uv` is unavailable, stop and report it; do not use another Python tool.

After the automated gate, launch from the project root with `uv run pbui` for one manual session. Enter `:tutorial`, use Up through Listener to Contents, open HTTP, and open Make a request. Click Try and confirm that it loads the exact `:get` command without a network result. Press Enter and confirm that a retained `GET` row appears. Read Perform the GET with Next, then choose `perform` from the GET row's menu. If a response appears, briefly use `body` to see decoded text, then choose `json` on that same response. Follow Open JSON and Browse and reuse: dig the root `JsonObject`, inspect `metadata` title and count, inspect `features`, and, if `[0]` exists, open that feature and its `properties` to see `place` and `mag`. Treat counts and event values as live. At a valid Python expression prompt, type `len(`, click a retained JSON collection row to insert its object chip, type `)`, and press Enter. Confirm leaf Up returns to HTTP and section Up returns to Contents. Exit with Ctrl-C.

If `perform` yields a transport `Error`, record the visible error and stop the live portion. If the response is returned but JSON is unavailable or invalid, record the response and existing parse `Error` and stop the JSON portion. Do not retry automatically, change hosts, or relax the response limit. The deterministic tests remain evidence for the paths that the live feed could not complete.

Completion requires the HTTP screen path and documentation assertions, the full `uv run pytest` suite, and the hand check or its specified error record. Report test and hand-check results and changed files, then stop without starting another checkpoint.
