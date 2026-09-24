# Specification — HTTP GET and one-level JSON browsing

**Status:** Accepted design. Both **http 000** and **http 001** are implemented
per user reports. This document remains their design authority and assigns no
implementation work by itself.

A GET request is a retained object. Performing it leaves that request in
history and appends a response or an `Error`. A JSON response can present a
tree of Python values, with one level of members added by each dig click.

## 1. Boundary and existing interaction

Extend the implemented listener, listings, REPL, chips, SymPy, transcript, and
popup behavior in the existing `src/pbui/` package and `tests/`. Add only the
colon command `get` to the existing command names. The other commands,
command accepts, Python evaluator, chip insertion, `_`, bounded history,
listing redisplay, transcript recording, menu overlay, and input modes retain
their rules. In particular, a submitted `:get URL` gets a `CommandInput` row
before its result. Each selected `perform`, `json`, or `body` item gets a
`MenuActionInput` row before its result; `run again` reuses the saved target
object and operation. These rows count toward the existing 500-logical-row
history limit. No input is replayed by constructing Python source.

Use the existing `Value` presentation and Python-class row-printer mechanism
for request, response, `JsonObject`, and `JsonArray`. They retain their stored
objects by identity. Do not register a printer for plain `dict` or `list`.
Their special default clicks and response-specific menus below extend the
existing `Value` behavior only for these classes. During Python composition,
including continuation, a first left click at a valid expression position
inserts the stored object as an atomic chip instead of taking its default
action. An open menu, presentation accept, or substring accept keeps its
existing higher click priority. These values remain inert targets for typed
`:show`, `:rm`, `:cd`, `:kill`, and the listing accepts. Right-click or Ctrl-O
opens an available action menu at the pointer with the existing border,
geometry, dismissal, and documentation rules. Only `pbui.terminal` imports
Textual; the model and tests are headless.

The project already uses uv. Implementers run `uv sync` and `uv run pytest`
for the automated gate; `uv run pbui` is for the hand check only. If uv is
unavailable, stop and report it. Prefer no new dependency: production HTTP
uses the Python standard library. Automated tests never access the network.

## 2. Request and transport

Export the frozen `GetRequest` constructor from `pbui.http`. Its public form
is `GetRequest(url: str)`; it stores that URL string and the constant method
`GET`. It does not open a socket. A user can write
`from pbui.http import GetRequest` in Python, then evaluate
`GetRequest("https://example.org/")`. Do not inject the constructor or its
module into the listener's Python namespace. A displayed constructor result
is a `Value` and updates `_` under the existing REPL rule.

`:get URL` appends a `GetRequest` as a `Value` and does not fetch. After the
command name and its required separating space, the entire remaining line is
one URL argument, including any further spaces; never split it into more
arguments. Store it unchanged. A missing or empty URL appends the usual
command `Error` and no request. The ordinary colon-command transcript row
comes first in either case. `get` joins the bare-command-name hint: unprefixed
`get` is Python, and an unbound bare `get` suggests `:get` without issuing a
request. A command-created request does not change `_`.

The request row is `GET URL`, escaped and capped at 120 display cells with
`…` inside the cap. A short URL appears in full. Its action menu has exactly
one item, `perform`. Ordinary left click retains the existing generic
`Value` detail action. Selecting `perform` records the action, calls the
injected transport once, and appends a new response `Value` on success. It
does not alter or replace the request or its row. Selecting it again appends
another response. A transport failure, including a bad URL, appends one
`Error` after the action row and leaves the request. A successful response
updates `_`; a failure leaves `_` unchanged. `run again` on a recorded
`perform` action calls the same operation on that saved request.

The headless listener accepts an injected GET transport. Its one operation
takes a `GetRequest` and returns a result containing **status code, final URL,
headers, and complete body bytes**, or raises a transport failure. Tests pass
a fake result or failure through this seam; no other path opens a socket.
Production uses `urllib.request` to follow redirects, sends exactly
`User-Agent: pbui/1.0`, and uses a **15-second timeout**. Accept only an
`http` or `https` scheme with a host when performing; reject other schemes
or malformed URLs as an `Error`, while retaining the request. Read at most
**2 MiB** (2,097,152 bytes), probing one further byte; an oversized body is
one transport `Error` and never a partial response. Close the underlying
response on every path. A `urllib.error.HTTPError` whose code is not a redirect status is a
completed HTTP response. Redirect statuses are 301, 302, 303, 307, and 308.
Read that response's headers and body under the same limit and retain its
status and final URL. Thus 404 and every other non-redirect HTTP status are
responses. An HTTP error whose code is a redirect status, including redirect
limit exhaustion, is a transport `Error` even though `urllib` raises
`HTTPError`. That redirect rule wins over the response rule. Connection,
timeout, other `URLError`s, bad URLs, and body-size failures are also
`Error` presentations. Escape and bound their messages through the existing
safe-display error path.

The listener applies the body-size rule to every successful transport
result, fake or production, before a response is presented. A returned body
longer than 2,097,152 bytes becomes the same oversized-body `Error` and no
response is appended. Production also stops reading after one byte past that
limit so it does not download the rest. The oversized-body test returns
2,097,153 bytes from the fake transport and does not call `urllib`.

## 3. Response and its menu

An `HttpResponse` stores the integer status, final URL after redirects, raw
`Content-Type` header value (or `None` when absent), and full body bytes.
Its one-line row is `HTTP STATUS FINAL_URL`, escaped and capped at 120 display
cells, so a short final URL is complete. Ordinary left click uses the generic
`Value` detail action; the bounded detail may include the content type.
Neither menu item changes the response or its row.

For media-type matching, take the portion of `Content-Type` before `;`, trim
surrounding whitespace, and compare case-insensitively. `application/json`
and any media type ending in `+json` qualify. On first presentation of a
qualifying response, decode its body as strict UTF-8 and parse it as JSON.
Retain that parse result or the validation failure with the presentation, so
menu building and repeated actions neither reparse nor mutate the response.
Reject nonstandard JSON constants such as `NaN` and `Infinity`. If decoding
or parsing fails, keep the response, append one explanatory `Error`
immediately after it, and omit `json` from its menu. A non-JSON media type
does not parse and produces no parse `Error`.

The response menu has `json` first **only** for a qualifying, successfully
parsed body, then `body` always. Choosing `json` records the menu action and
appends the retained parsed value as a `Value`, including JSON `null` as
Python `None`; it updates `_` like a displayed translator result. Repeating
`json` appends the same parsed object by identity. Choosing `body` records
the action and appends one `Text` row. Decode bytes as UTF-8 with replacement
characters, escape control characters with the existing safe-display rules,
then cap the displayed text at **4096 display cells** with `…` inside the cap.
The `Text` row stays one logical line, even for a body containing newlines;
it does not update `_`. A repeat produces another `Text` row. This rule also
applies to non-JSON and failed-JSON responses.

The response menu depends on that response's validated body, not solely on
its Python class. Extend menu lookup for this instance-specific eligibility;
do not expose a disabled `json` item or make menu opening trigger a parse
error. The popup still saves the resolved action and target at opening.

## 4. JSON values and dig clicks

JSON `null`, booleans, integer numbers, other numbers, and strings become
ordinary Python `None`, `bool`, `int`, `float`, and `str` values and use their
existing `Value` presentation. Every JSON object, including a nested one,
becomes `JsonObject`, a `dict` subclass; every array becomes `JsonArray`, a
`list` subclass. The parsed tree supports ordinary subscripting and
iteration. Use standard-library JSON parsing and recursively convert both
container kinds. Tests of fractional or exponent numbers use values that
survive conversion to `float`; add no decimal type.

The one-line summary rows are `▸ JsonObject (N keys)` and
`▸ JsonArray (N elements)`, where `N` is the actual immediate count. The `▸`
on a summary row is the parent collection's hit marker. A first left click
on that row at an ordinary, non-accept prompt appends **only its immediate
members**, in source order for an object and index order for an array, at
most **100** of them. When more members exist, the last appended row is the
literal text `… (N more members)`, where `N` is the number omitted. That
trailer is not a presentation. The dig does not replace, edit, or remove the
parent row. The ordinary 500-row history limit may still drop the parent
later if older rows fall off the oldest end. One dig does not itself append
enough rows to evict a parent that is among the newest 400 history rows.
Clicking the summary again appends another copy of that same bounded set.
An empty collection appends no rows. A plain
Python `dict` or `list` retains its generic row and generic `Value` detail
click; it gains no member listing.

An object member row is `["KEY"]  VALUE_ROW`; an array member row is
`[INDEX]  VALUE_ROW`. `KEY` is the JSON string key, escaped for safe display;
`INDEX` is the zero-based decimal index. `VALUE_ROW` is the member's normal
one-line `Value` text, including the `▸` summary if the member is a JSON
collection. Escape unsafe characters, cap the key label at 48 display cells,
and cap the complete member row at 120 display cells, using `…` within each
cap. Short keys, indexes, and values fit in full. The label and the value
text are one presentation whose **stored object is the member value**, never
the key or index. Clicking any cell in that row, including its label, targets
that value. A nested collection member's own `▸` and entire row target the
nested collection; clicking it appends the next level. The parent is targeted
by its separate retained summary row. Ordinary scalar members keep their
existing default `Value` detail click and any menus their value class has.

`JsonObject` and `JsonArray` have no collection-building action menu: no
`append`, `with`, or equivalent item. Their ordinary hover documentation is
respectively `Left: list this JSON object's members. Right: no menu.` and
`Left: list this JSON array's members. Right: no menu.` Request and response
ordinary hover use the popup's registered-value wording,
`Left: show this Python value. Right: menu.` During Python composition,
their rows use the existing chip insertion or refusal sentences with
`Right: menu.` for requests/responses and `Right: no menu.` for JSON
collections. Pending accepts use the existing `Value` refusal. A menu item
uses the popup's registered Python value item sentence. An open menu and its
border keep their existing documentation precedence.

## 5. Verification and handoff

Keep all existing tests passing. Headless HTTP tests inject a fake transport;
they never call production GET or open sockets. Test at least `:get` making a
request without calling the fake, a Python-imported `GetRequest`, repeated
`perform` calls retaining an unchanged request, a transport failure, an
oversized body, and a 404 response. Check status, final URL, content type,
body bytes, transcript ordering, and `_` changes. Test JSON media types with
parameters and `+json`, non-JSON media with no `json` item, and invalid UTF-8
or JSON yielding a retained response followed by one `Error` and no `json`
item. Test `body` replacement decoding, escaping, and its cap.

Test that a JSON object or array and every nested container have the specified
subclasses; primitive values keep their Python types. A dig click must append
at most 100 immediate member rows with the member objects and key/index
labels, leave the parent row unreplaced, and allow a nested member to be
clicked again. A collection of 101 members appends 100 value rows and one
literal trailer. The test history must stay small enough that the 500-row
limit does not drop the parent. Cover a short key
and URL in full, an empty collection, a plain Python `dict` retaining its
generic behavior, Python-chip insertion of a JSON object by identity, and
menu/accept click precedence. Screen tests should verify summary and member
hit areas, right-click menu placement, and documentation. The automated gate
is `uv run pytest`.

**http 000 — request and response.** Add types, `:get`, the injected transport
and production adapter, `perform`, response rows, `body`, JSON validation and
`json`, plus headless tests. No live network test in this slice.

**http 001 — JSON rows and hand check.** Add one-level member presentations,
dig clicks, screen routing and documentation, plain-`dict` regression, and
the screen tests. After `uv run pytest`, start `uv run pbui` from a recorded
disposable directory under the project root. Enter
`:get https://www.reddit.com/r/python/new.json`, use `perform`, then `json`,
and click into at least two nested levels (for example `data`, then
`children`) while each parent remains visible. This one HTTPS URL ends in
`.json` and needs no login or API key. If the network refuses the request,
record the resulting `Error` and stop the hand check; do not retry another
host. An HTTP error status still appears as a response, not a transport
`Error`; record it if it prevents the walk.

The human reviews this specification before any checkpoint is written. POST,
PUT, user-supplied headers, cookies, authentication, HTML browsing, pandas,
SQLite, general collection menus, streaming, unbounded bodies, images, and
preloading `GetRequest` into Python are outside this exploration.
