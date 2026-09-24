# Charter — HTTP and JSON

**Status.** Handoff from the high-level discussion into a **design
conversation**. Not a checkpoint. Not an implementer assignment.
This file lives in `docs/design/implementation/http/`. The
specification will live beside it as [`spec.md`](spec.md).
Checkpoint files will live in `checkpoints/` beside it. Map:
[`README.md`](README.md). The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

**Your job.** Turn this charter into a specification for GET
requests, responses, and one-level JSON values you can click into.
Then **stop**. Do not write checkpoints. Do not implement.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Use the REPL, chips, transcript, and popup specifications only
   to preserve presentations, menus, chips, and the transcript.
   Do not copy them. Restate every rule an implementer must obey.
3. Record the locked decisions in §4. Resolve the open questions in
   §5.
4. Write `spec.md` in this folder. A later checkpoint-manager
   conversation slices **http 000**, `001`, … under `checkpoints/`
   here, one checkpoint per conversation.
5. Stop. The human reviews the spec. Do not write those checkpoint
   files.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification.

Keep the spec **small enough to slice**. A general collection
algebra, pandas, and SQL are defects in this document.

## 2. Predecessors

The listener through the popup exploration is implemented. Values
have printers and menu translators. A click while composing Python
inserts the stored object. Submitted input is recorded before its
results. The action menu opens beside the pointer.

This exploration does not create a new project. Implementers keep
using uv in the existing project. Prefer no new dependency. HTTP
comes from the standard library. The designer does not run uv.

| Place | What goes there |
|---|---|
| `docs/design/implementation/http/` | This charter, `spec.md`, and `checkpoints/` |
| Project root | The existing `pbui` package and `tests/` |

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **The request survives the fetch.** Performing a GET appends a
   response. The request row remains, unchanged.
2. **Automated tests do not use the network.** A fake transport
   supplies the status, headers, and body. Production GET is the
   only path that opens a socket, and the hand check is the only
   required use of it.
3. **JSON is a tree of values.** A JSON object shows its keys, and
   a JSON array shows its indexes, one level at a time. A click that
   digs in appends that member as its own value. The parent stays.
4. **A Reddit listing can be walked.** The hand check fetches one
   `https` URL ending in `.json`, opens the JSON, and reaches a
   nested value by clicking. No API key and no login.
5. **A non-JSON body and a transport failure stay visible.** An HTTP
   status, including 404, is a response. A failure to connect is an
   `Error`. The request remains either way.

## 4. Locked decisions (record these; do not reopen)

### 4.1 The request

A request is a frozen object. It stores the method `GET` and the
URL string. No other method exists in this exploration. The URL
scheme must be `http` or `https`. Anything else is an `Error` when
the request is performed, and the request row still remains.

`:get URL` appends a request. It does not fetch. The rest of the
line is the URL, so the URL may contain spaces only if they are
part of that one argument. There is no second argument. The user
can also construct the same object from Python. The spec names that
constructor. It is not injected into the listener namespace. The
user imports it, as they import SymPy.

The request's menu has one item, `perform`. It issues the GET and
appends a response, or an `Error` if the transport fails. The
request is not modified. A second `perform` appends another
response.

Production transport uses the standard library, follows redirects,
and sends a `User-Agent` that identifies pbui. The spec writes that
header value. It also chooses one timeout of at least ten seconds
and one maximum body size of at least one mebibyte and at most four.
A body over that size is a transport `Error`, not a partial
response. Tests never call the production transport. They pass a
fake that returns a status, headers, and body, or raises a
transport failure.

### 4.2 The response

A response stores the status code, the final URL after redirects,
the content type, and the body bytes. Status 404 and any other
HTTP status are responses, not errors.

Its history row is one line: the status code and the final URL,
truncated like other values. `show` may add the content type. The
menu is:

| Item | When | Result |
|---|---|---|
| `json` | The content type's media type is `application/json` or ends in `+json`, and the body parses as UTF-8 JSON | Appends the parsed value |
| `body` | Always | Appends the body as text, capped |

`json` is absent when the media type is not JSON. When the media
type is JSON and parsing fails, `json` is absent and an `Error`
explains the failure. The response remains. `body` decodes as UTF-8
with replacement characters. The spec chooses the text cap. Control
characters are escaped. The response object is unchanged by either
item.

### 4.3 JSON values

Parsing produces ordinary Python `None`, `bool`, `int`, `float`,
and `str` for JSON null, booleans, numbers, and strings. Those use
the existing value presentations.

A JSON object becomes a `JsonObject`, a `dict` subclass. A JSON
array becomes a `JsonArray`, a `list` subclass. Nested objects and
arrays use those same classes. Do not register a printer for plain
`dict` or `list`. A dict the user typed in Python stays on the
generic value row.

A `JsonObject` or `JsonArray` history row is one line: a kind and a
count, such as how many keys or elements. It does not dump the
whole tree. Left click, when not composing Python and when no
accept is pending, appends one level of member rows and leaves the
summary row in place. While composing Python, left click still
inserts a chip holding that object. Subscripting and iteration work
because the object is a dict or a list.

Each member row is a presentation of the member value, not of the
key or the index. The key or index is a label on that row. Clicking
the label or the value targets the value. A nested `JsonObject` or
`JsonArray` on that row is itself that object, so the next left
click digs into it. The brackets or another marker that belongs to
the parent, not to a member, is how a click hits the collection.
The spec chooses that marker.

There is no `append`, `with`, or other collection-building menu.
The menu on a JSON collection can be empty. Member values keep
whatever menu their own type already has.

### 4.4 Tests

Headless tests use the fake transport and do not open sockets.
Cover at least:

- `:get` appends a request and does not fetch;
- `perform` appends a response and leaves the request unchanged;
- a transport failure appends `Error` and leaves the request;
- status 404 is a response;
- a JSON content type appends a `JsonObject` or `JsonArray` whose
  nested members are the same classes;
- a non-JSON content type has no `json` item, and a failed parse
  appends `Error`;
- left click on a `JsonObject` appends member rows whose stored
  objects are the values;
- a plain Python `dict` does not gain that member listing.

The hand check fetches one real `https` URL that ends in `.json`
and walks at least two levels by clicking. Name that URL in the
spec. If the network refuses it, the check records the `Error` and
stops. It does not retry other hosts. `uv run pytest` is the
automated gate. `uv run pbui` is only the hand check.

### 4.5 Slice order

1. **Request and response.** Types, `:get`, `perform`, the
   transport seam, status, body text, and JSON parse. Headless.
2. **JSON rows.** One-level member presentations, dig click, plain
   `dict` unchanged, and the hand check.

Do not add a slice for a feature in §4.6.

### 4.6 Out of this spec

- POST, PUT, headers supplied by the user, cookies, and authentication.
- HTML, link following, and a browser.
- Pandas, SQLite, and a general menu for `list`, `dict`, or `set`.
- Streaming or unbounded bodies.
- Images and other media types beyond `body` text.
- Preloading a request constructor into the namespace.

## 5. Open questions (resolve these in the spec)

### 5.1 Row wording

Choose the one-line text for a request, a response, a `JsonObject`,
a `JsonArray`, and a member row. A short URL and a short key must
be readable in full.

### 5.2 Caps

Choose the body-size limit, the timeout, the `User-Agent`, and the
`body` text cap. State the marker that hits the JSON collection
rather than a member.

### 5.3 Numbers

JSON numbers that are not integers become Python `float`. State
that tests use values that survive that conversion. Do not add a
decimal type.

## 6. Authority

This charter is the design for this exploration. The earlier
specifications remain the law for everything it does not change.

The useful precedent is a value whose parts are themselves values.
This exploration uses that for a JSON body fetched by GET. It does
not build a collection editor or a web client.

## 7. Handoff reminder

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. Identity is **http 000**, then
**http 001**.
