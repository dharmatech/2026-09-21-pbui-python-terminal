# Charter — HTTP section in the tutorial

**Status.** Handoff from this discussion into a **design conversation**.
This is not a checkpoint or an implementer assignment. This charter and
[`README.md`](README.md) live in `docs/design/implementation/tutorial-http/`.
The designer writes `spec.md` here; later conversations write numbered files
under `checkpoints/`. The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

**Your job.** Specify one HTTP section of short, sequential tutorial cards
that teaches the implemented request, response, and JSON presentations using
one public USGS earthquake feed. The series identity is **tutorial-http**.
Write `spec.md` beside this charter, then **stop** for review. Do not write
checkpoints or change the program.

The series does not redesign HTTP, add another command or card level, fetch
tutorial content, replace the longer HTTP demo, or require a local server.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Read the accepted
   [`sections` specification](../sections/spec.md), the accepted
   [`tutorial` specification](../tutorial/spec.md), and the accepted
   [`http` specification](../http/spec.md). Inspect the current
   `src/pbui/tutorial.py`, the relevant headless and screen tests, and the
   [HTTP demo](../http/demo.md). The demo illustrates the interactions; the
   accepted specifications and current program govern their behavior.
2. Record the locked decisions below. Resolve the limited wording and card
   organization questions in §5. Put all rules needed by later conversations
   in `spec.md`; they will not receive this charter.
3. Write `spec.md` here and stop. The human reviews it before any checkpoint
   is written. The checkpoint manager then writes one numbered checkpoint at
   a time, and each implementer handles only its assigned checkpoint.

## 2. Predecessors and boundary

The tutorial currently has Contents with Listener and SymPy sections. Each
section lists leaves; Back and Next stay within that section, and Up returns
to the parent. `:tutorial` still opens the first Listener leaf directly.
The stored cards and Try examples are local package data. Try loads a saved
line into an empty editor without running it. Navigation appends a fresh
presentation of an existing stored card and preserves the editor.

HTTP is already implemented. `:get URL` retains a `GetRequest` without
fetching. Its `perform` menu action adds a separate `HttpResponse`. A JSON
response offers `json`, which presents retained `JsonObject` and `JsonArray`
values. A click on either collection at an ordinary empty prompt appends one
level of members. The response also offers `body`. The HTTP specification
governs these behaviors, including the 2 MiB response limit, menus, clicks,
input recording, and errors. This series changes only how the tutorial
teaches them.

The chosen public example is the USGS magnitude 2.5+ past-day GeoJSON feed:

    https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson

[USGS documents the feed shape](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php):
the root has `metadata` and `features`; metadata includes a title and count;
each feature has properties and geometry. The feed is live, so counts, event
IDs, magnitudes, places, and the first feature change. In the discussion, a
GET with pbui's `User-Agent: pbui/1.0` returned HTTP 200 and JSON well below
the existing body limit. That observation is evidence for choosing the feed,
not a permanent guarantee. A network connection is needed only when the user
chooses `perform`.

This is an existing uv-managed Python project. Do not initialize a new
project or add a dependency. Code and tests belong at the project root, not
in this design folder. Implementers use `uv sync`, `uv run pytest`, and
`uv run pbui` for the hand check. Automated tests must use an injected or
fake HTTP result and never contact USGS. If uv is unavailable, stop rather
than switching Python tooling. The designer does not run uv.

## 3. Bar for the specification

The specification is wrong unless it makes all of these true:

1. Contents gains **HTTP** after Listener and SymPy. Opening it shows a
   section card whose short leaves stay within HTTP under Back and Next;
   their Up returns to HTTP, and HTTP's Up returns to Contents. Existing
   Listener and SymPy cards and their order remain intact. `:tutorial` still
   opens Presentations.
2. The first HTTP example is a Try control that loads exactly
   `:get https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson`.
   Displaying a card or clicking Try never opens a socket. Enter makes the
   request row, and the user explicitly chooses `perform` to fetch.
3. The lessons guide the user from the retained GET row to its response,
   through `json`, and into the JSON object and array by clicks. They name
   durable structural fields such as `metadata`, `features`, `properties`,
   `place`, and `mag`; they do not promise a fixed count, first earthquake,
   location, magnitude, or response body.
4. The tutorial also explains how to view `body` on the same response and
   how an object from the JSON history can be reused in Python, without
   turning either into a second API walkthrough. The spec decides where
   those short notes fit among the leaves.
5. Card construction is local and performs no HTTP request. Existing card
   hit areas, Try busy refusal, navigation, documentation, 20-row card cap,
   500-row history, and HTTP behavior remain governed by their accepted
   specifications.
6. Headless tests prove the new stack, exact Try source, navigation, and
   no-network card construction; screen coverage proves the visible entry
   and a representative navigation path. Existing tests still pass. A hand
   check uses the public feed without starting a local server. The spec
   describes what to do if live network access fails during that check.

## 4. Locked decisions

### 4.1 One new subject in the existing hierarchy

Add HTTP as the third Contents entry. Use the current Contents → section →
leaf roles and current card controls; do not add a new screen, tutorial
command, nested section, HTTP-specific presentation type, or new navigation
rule. Back and Next on HTTP leaves never cross to SymPy or Listener. Keep
the existing `:tutorial` entry point and both existing sections unchanged
apart from the added Contents entry.

### 4.2 One live feed and one request

Use the exact USGS URL in §2 as the tutorial's saved `:get` example. The
normal route is request → `perform` → response → `json` → collection digs.
The card text must distinguish the inert request from the network action,
and the retained response from the parsed JSON value. This is the same
presentation behavior demonstrated with a local server in the HTTP demo,
but the tutorial requires no server, temporary files, account, or API key.

Guide the reader through `metadata` first so the tour has useful fields even
if `features` is temporarily empty. Then point to `features`, a member such
as `[0]` when present, its `properties`, and scalar fields such as `place`
and `mag`. Describe what the user should see by type and shape rather than
by today's values. The data remains live; do not embed a frozen event ID or
hard-code a member count in tutorial text or tests.

### 4.3 Small teaching scope

Keep the section short and sequential, comparable in size to the existing
SymPy section. The lessons cover request creation, performing, opening JSON,
and browsing one level at a time. Include brief notes on the response's
`body` action and Python reuse of a retained JSON value without reproducing
the whole HTTP demo. The demo remains the longer tour
for replay, invalid JSON, HTTP error status, and the 100-member limit.

No new transport behavior, URL handling, parser, JSON printer, response
limit, action, or network-dependent automated test belongs here. No card
fetches remote text to build itself. A live-service error is shown by the
existing HTTP error behavior; the tutorial does not silently retry or
switch hosts.

### 4.4 Verification and slice order

Use at least one headless slice for card data, text, links, and Try, followed by
one visible slice for controls, screen coverage, and the hand
check. A checkpoint manager may split a slice if the accepted spec shows it
would be too large for one implementer conversation, while preserving that
order and adding no features. Tests must not depend on the current USGS
payload or on live network availability. The manual hand check runs
`uv run pbui`, opens the HTTP section from Contents, performs the one GET,
and walks the returned JSON if it succeeds. If the network refuses the GET,
record the existing Error and stop that live portion; do not try another
host as part of this series.

## 5. Questions for the spec writer

Decide the exact number, titles, and concise text of the HTTP leaves, and
where the `body` and Python-reuse notes fit. Keep the four-stage learning
order in §4.2. Decide the stable identifiers and the minimal changes needed
to expose the new leaves from the existing tutorial stack. Give the new
controls the current documentation rules unless a specific new case is
necessary; specify any such case precisely.

## 6. Authority

The accepted [sections specification](../sections/spec.md) governs the
Contents, section, and leaf hierarchy, card links, and documentation. This
charter changes its exact Contents membership by adding HTTP third; that is
the only hierarchy difference. The accepted [tutorial
specification](../tutorial/spec.md) governs card presentation, Try, and the
original Listener lessons. The accepted [HTTP
specification](../http/spec.md) governs request, response, body, JSON,
transport, menus, and clicks. The current source and tests show the
implemented seams. The [HTTP demo](../http/demo.md) is an interaction
example, not authority over those specifications. Where there is a conflict
about new HTTP tutorial content, this charter sets the intended scope; the
new accepted spec will become the design authority for its checkpoints.

## 7. Handoff

The series identity is **tutorial-http**. Checkpoint 000 is spoken
**tutorial-http 000** and filed as `checkpoints/000-slug.md`; later numbers
are three digits, start at 000, and are never renumbered. Slugs use lowercase
words separated by hyphens. The checkpoint manager writes only one
checkpoint, then stops; each checkpoint is implemented in its own
conversation. Code and tests go at the project root
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

After the user accepts `spec.md`, it is the authority for the checkpoint
manager and implementers. This charter is the assignment for the spec
writer. The intended order is local card data and headless behavior, then
visible controls and the live hand check.
