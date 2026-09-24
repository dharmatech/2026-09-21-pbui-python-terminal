# http 000 — Request and response

**Status.** Implemented per user report; `uv sync` and 281 tests passed.

## Goal and authority

Add a retained GET request, an injected and production GET transport, and a
retained response with `perform`, `json`, and `body` operations. Finish the
headless model and automated tests. Leave JSON member rows, dig clicks, screen
routing, and the live network hand check for http 001.

- Identity is `(http, 000)`, spoken **http 000**.
- The human-reviewed [`../spec.md`](../spec.md), especially sections 1–3 and
  **http 000 — request and response** in section 5, is the authority. Follow
  it wherever this checkpoint is silent. The charter is not an implementation
  input.
- Extend the existing listener, listings, REPL, chips, SymPy, transcript, and
  popup implementation. Preserve their command accepts, Python evaluation,
  chip insertion, `_`, listing redisplay, input rows, saved menu actions,
  500-logical-row history limit, and menu precedence except for the HTTP
  additions specified here.
- Work in the existing project at
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Keep application
  code under `src/pbui/` and tests under `tests/`. Use the Python standard
  library for HTTP; add no dependency.

## File and feature boundary

Add a focused plain-Python `src/pbui/http.py` for the request, transport
contract and adapter, response, and JSON value types. Extend
`src/pbui/commands.py` and `src/pbui/repl.py` for command dispatch, retained
`Value` rows, per-response action eligibility, and saved action execution.
Adjust another existing plain-Python module only if needed for the existing
presentation or safe-display APIs. Add focused headless tests, for example in
`tests/test_http.py`, and update predecessor assertions only where the added
command or rows require it. Do not import Textual outside `pbui.terminal`.

Do not change production `src/pbui/terminal.py` in this checkpoint. Provide
headless operations that the later screen slice can call. Do not add JSON
member presentations, dig clicks, collection menus, a live network test, or
the http 001 checkpoint.

## Request, command, and history

Export a frozen `GetRequest(url: str)` from `pbui.http`. It retains the URL
string and constant method `GET`; constructing it opens no socket. The user
can import it explicitly in Python. Do not preload the constructor or module
into the listener namespace. A Python-displayed request is a `Value` and
updates `_` by the existing REPL rule.

Add only `get` to the colon command names. `:get URL` records its normal
`CommandInput` before appending the request as a `Value`, without fetching or
changing `_`. After the command name and its required separating space, keep
the entire remaining line as one unchanged URL argument, including further
spaces; do not split it into multiple arguments. A missing or empty URL
records the command then appends the usual command `Error`, with no request.
An unprefixed `get` stays Python; an unbound bare `get` gets the existing
suggestion to use `:get` and does not issue a request. Requests remain inert
for typed domain commands and listing accepts.

Draw a request as `GET URL`, escaped and capped at 120 display cells with `…`
inside the cap. A short URL must appear in full. Register a printer for
`GetRequest`, not for plain `dict` or `list`. Ordinary left selection retains
the generic `Value` detail action. Its headless action list contains exactly
`perform`; selecting it records a `MenuActionInput` before the result. A
second selection makes a second response or `Error` while leaving the
request object and retained row unchanged. `run again` on that action uses
the saved request and operation, without constructing Python source.

## Transport and response

Inject one GET transport into the headless listener. It receives the original
`GetRequest` and either returns status code, final URL, headers, and complete
body bytes, or raises a transport failure. Tests use a fake through this
seam; no automated test opens a socket. Validate the URL when performing:
only `http` and `https` with a host are allowed. A bad or unsupported URL
leaves the request and appends one `Error` after the action row.

The production adapter uses `urllib.request`, follows redirects, sends
`User-Agent: pbui/1.0`, and uses a 15-second timeout. It reads no more than
2,097,153 bytes, one byte past the 2 MiB body limit, and closes the response
on every path. It never returns a partial response. A
`urllib.error.HTTPError` with a code other than 301, 302, 303, 307, or 308
is a completed response; retain its status, final URL, headers, and bounded
body. Those five redirect codes, including redirect-limit exhaustion, are
transport `Error`s even when raised as `HTTPError`. That redirect rule wins.
Connection, timeout, other URL, redirect, and body-size failures are also
`Error`s. Use the existing escaped and bounded error presentation.

Independently of production's read cap, the listener rejects any successful
transport result whose body is longer than 2,097,152 bytes **before** it
presents a response. This applies to fake results too. The rejected result
adds one oversized-body `Error`, no response, and leaves `_` unchanged.

On success, create an `HttpResponse` containing integer status, final URL,
the raw `Content-Type` header value or `None`, and full body bytes. Present it
as a new `Value`, after the action row, and update `_`. Status 404 and other
non-redirect HTTP statuses are responses, not transport errors. Draw
`HTTP STATUS FINAL_URL`, escaped and capped at 120 display cells; keep a short
final URL complete. Ordinary left selection uses generic `Value` detail and
may show the content type. Neither action edits the response or its row.

## JSON validation and response actions

Match the media type before `;`, after trimming whitespace and ignoring case.
`application/json` and a media type ending in `+json` qualify. On the first
presentation of a qualifying response, decode the body as strict UTF-8 and
parse it with the standard-library JSON parser. Reject nonstandard constants
such as `NaN` and `Infinity`. Retain either the parsed value or validation
failure with that presentation. An invalid JSON body retains the response,
then appends exactly one explanatory `Error`, and has no `json` action. A
non-JSON media type is not parsed and adds no parse error. Building or opening
an action list never reparses a body or emits a parse error.

Convert every parsed object recursively to `JsonObject`, a `dict` subclass,
and every parsed array to `JsonArray`, a `list` subclass. Preserve ordinary
Python `None`, `bool`, `int`, `float`, and `str` for JSON primitives. The tree
must support normal subscripting and iteration; fractional and exponent
tests use numbers that survive `float` conversion. Present a chosen JSON
result as a `Value`, including `None`, without registering a printer for
plain `dict` or `list`. JSON collection summary rows and member rows are
completed in http 001.

The response's headless action list is instance-specific: `json` first only
when its media type qualifies and parsing succeeded, then `body` always.
Choosing `json` records `MenuActionInput`, appends the cached parsed object as
a `Value`, and updates `_`. Repeating the saved action appends that **same**
parsed object by identity, even if the original response row has left
history. The saved operation must retain whatever parse state is needed for
that replay. Choosing `body` records `MenuActionInput`, decodes bytes as
UTF-8 with replacement, escapes controls through the existing safe-display
rules, caps the displayed text at 4096 display cells with `…` inside the cap,
and appends one `Text` logical row. Newlines in the body must not split that
row. `body` works for non-JSON and failed-JSON responses; it and its replay
leave `_` unchanged. The popup screen will use these resolved headless
actions in http 001.

## Automated verification

Keep the full predecessor suite passing. HTTP tests inject a fake transport,
never call production GET, and never open sockets. Check at least:

1. `:get` records command then request without calling the fake or changing
   `_`; a missing or empty URL records command then `Error`; the saved URL
   preserves additional spaces. A short URL draws in full. Explicit Python
   import and evaluation of `GetRequest` stores that object in `_`, while an
   unbound bare `get` gives the colon hint without fetching.
2. `perform` records action before response or `Error`. Repeated selections
   and `run again` call the fake once per action, retain the unchanged
   request, and produce distinct response presentations. Verify status,
   final URL, raw content type, and body bytes. A fake 404 is a response.
   A fake failure and invalid URL retain the request and leave `_` unchanged;
   a successful response updates `_`.
3. The fake returns exactly 2,097,153 body bytes: the listener adds one
   oversized-body `Error` and no response, without calling `urllib`. The
   production read cap and redirect/non-redirect `HTTPError` classification
   can be checked through pure helpers or stubs, never a live request.
4. JSON content types with parameters and `+json` expose ordered `json`,
   `body` actions. A non-JSON response exposes only `body` and does not
   parse. Invalid UTF-8 or JSON retains the response, appends one `Error`
   immediately after it, and omits `json`; `body` still works. Nonstandard
   JSON constants fail validation. Opening the action list emits no new
   parse error.
5. Parsed root and nested containers have the required subclasses; JSON
   primitives retain their Python types. Choosing and repeating `json`
   reuses one parsed object by identity, including after its response row is
   evicted; JSON `null` produces a `Value` for `None` and updates `_`.
   Choosing and repeating `body` produces one escaped, replacement-decoded,
   capped `Text` row each time and does not update `_`. Check input/result
   transcript order throughout.

## uv workflow and completion boundary

From the project root, use only the existing uv-managed environment:

```console
uv sync
uv run pytest
```

`uv run pytest` is the automated gate. Do not use `pip`, `python -m pip`,
`uv pip install`, Poetry, Pipenv, Conda, Hatch, a hand-made environment, or
global Python. If uv is unavailable, stop and report it.

Http 000 is complete when the headless request, transport, response,
validation, and action paths above work and the full suite passes. Stop
there. Do not run `uv run pbui` or any live HTTP hand check. JSON summary and
member rows, 100-member dig limit and literal trailer, click routing,
documentation, screen tests, and the one-URL hand check belong to http 001.
