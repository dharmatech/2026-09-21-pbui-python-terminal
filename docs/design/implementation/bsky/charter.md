# Charter — public Bluesky objects

**Status.** Handoff from the high-level discussion into a **design
conversation**. Not a checkpoint. Not an implementer assignment.
This file lives in `docs/design/implementation/bsky/`. The
specification will live beside it as [`spec.md`](spec.md).
Checkpoint files will live in `checkpoints/` beside it. Map:
[`README.md`](README.md). The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.
The spec writer returned one conflict in the feed row. This revision
resolves it. A feed object does not carry the requested actor, so its
own row is `feed: N posts`. A handle appears only when the caller
already has one and uses it as a label.

**Your job.** Turn this charter into a specification for presenting
public Bluesky posts, profiles, and bounded post listings. The
series identity is **bsky**. Then **stop**. Do not write
checkpoints. Do not implement.

The specification refuses login, writing, media, a home feed, a
tutorial subject, and a second post object that copies the library
record. Those refusals keep the series small enough to slice.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Read the SymPy specification for how a real library object keeps
   its identity, gains a row, a detail `show`, and a menu. Read the
   HTTP specification for the injected fetch seam, the colon-command
   argument rule, and the rule that automated tests never open a
   socket. Read the pinned `atproto` version's client constructor,
   public-host usage, and the models returned by the thread, profile,
   and author-feed calls. Name those classes. Do not invent a
   parallel post type.
3. Record the locked decisions in §4. There is no open-question
   section.
4. Write `spec.md` in this folder. A later checkpoint-manager
   conversation slices **bsky 000**, then **bsky 001**, then **bsky
   002**, under `checkpoints/` here, one checkpoint per conversation.
5. Stop. The human reviews the spec. Do not write those checkpoint
   files.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification, including
the `atproto` version `uv add` resolved and the class names it
presents.

Keep the spec to public reading. A login flow, a post composer, or a
tutorial section is a defect in this document.

## 2. Predecessors

The listener through sections is implemented. A Python result stays
the object the call returned. SymPy registers a printer and menu on
`sympy.Expr` without binding `sympy` in the listener namespace.
HTTP fetches through an injected transport, and its tests never open
a socket. `:get` stores one URL argument as the remainder of the
line.

This exploration adds one dependency, `atproto`, with `uv add`, so
the version is pinned in `uv.lock`. It is pre-1.0. This series does
not upgrade it after that pin and does not install it from a git URL.
Prefer no further dependency. The designer does not run uv.

The public AppView for unauthenticated `app.bsky.*` reads is
`https://public.api.bsky.app`. Commands use that host and do not log
in. A user's own `Client` is the library's client. The listener does
not bind `atproto`, `Client`, or a client in the Python namespace.
The namespace still starts as `__name__` only.

| Place | What goes there |
|---|---|
| `docs/design/implementation/bsky/` | This charter, `spec.md`, and `checkpoints/` |
| Project root | The existing `pbui` package, `tests/`, `pyproject.toml`, and `uv.lock` |

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **The library object is the value.** Calling the pinned client's
   thread method on a public post presents that call's result. The
   row shows the post. The retained object is the result itself, and
   a chip holds that same object.
2. **The graph is clickable.** From that post, a menu opens its
   author and its direct replies. From the author, a menu opens a
   bounded list of that author's posts. A reply is the same kind of
   object as the first post, so the walk can continue.
3. **Python and the commands meet.** `:post` of a public `bsky.app`
   URL and the corresponding `atproto` calls present the same class
   of object. `:profile` of that author's handle presents the same
   class `get_profile` would return. Neither command logs in.
4. **Absence is an object.** A missing post and a blocked post each
   get a row and no author or replies menu. A transport failure
   appends one `Error`.
5. **Tests do not touch the network.** Fixture models prove the rows,
   menus, and commands. One hand check reads one public post.
6. **Old tests still pass.** `requires-python` stays `>=3.11`.

## 4. Locked decisions (record these; do not reopen)

### 4.1 Which objects

Present only the classes the pinned `atproto` uses for these
results:

| Result | What the row is about |
|---|---|
| Thread result whose subject is a post | That post |
| Direct reply inside a thread | That reply post |
| Profile result | That profile |
| Author-feed result | That bounded feed |
| Thread result whose subject is missing | An unavailable post |
| Thread result whose subject is blocked | A blocked post |

The spec names each class from the pinned library. Any other
`atproto` model stays a generic value. The listener does not define
a `Post` or `Profile` class that copies those records.

A thread result is presented as its subject post. Replies and the
parent, when the result includes them, stay reachable from that
retained result. A reply row retains the reply object the library
put in the thread, not a reconstructed record.

### 4.2 Rows and detail

A post row is one line: the author's handle, a colon, a space, then
the post text. An empty text uses `(no text)` after that colon. A
profile row is the display name, a space, an em dash, a space, then
the handle. A profile with no display name is the handle alone. An
unavailable post's row is `unavailable post`. A blocked post's row is
`blocked post`.

A feed row is drawn from the library feed object and, when the caller
already has the author's handle, from that handle. The feed object
stays the retained value either way. The handle is not written onto
it, and it is not read from a post inside the feed.

| How the feed is presented | Row |
|---|---|
| From the object alone, including a directly evaluated `get_author_feed` result, an empty feed, or a feed whose first item is a repost | `feed: N posts` |
| By a caller that already holds the author's handle, such as the profile `posts` action or a command argument, when that caller presents the feed object itself | `HANDLE: N posts` |

`N` is the number of posts this series will list from that feed, at
most 20. An empty feed has `N` of 0. The profile `posts` action still
lists those posts as post rows. It uses the handle form only if it
also presents the feed object.

No row prefixes a class name. The existing value path escapes the
line and caps it at 120 display cells.

Left click on a post, with nothing waiting, appends the post text as
detail rows. Split on newlines. Escape and cap each row at 120
display cells. Show at most 24 rows, then one `… (N more lines)` row
when more remain. Detail does not change `_` or replace the source.
A profile, a feed, an unavailable post, and a blocked post keep the
ordinary value detail.

The post text is the library's text. Links and facets stay
characters in that text. This series does not fetch or draw images,
video, or linked pages.

### 4.3 Menus

A presented post has these menu actions, in order, and only these:

| Label | What it appends |
|---|---|
| `author` | The profile `get_profile` would return for that author. Use the profile already on the retained object when it is that class. Otherwise fetch it through the command client. |
| `replies` | One row per direct reply, at most 20, in the library's order. When more direct replies exist, one trailer row `… (N more replies)`. When there are none, one text row `no replies`. |
| `parent` | The parent post, only when the retained thread has one. Omit the item when it does not. |

Nested replies of a reply are not in that list. Opening a reply's
own `replies` action is how the walk goes deeper.

A presented profile has one menu action, `posts`. It fetches that
author's posts through the command client with a limit of 20 and
appends one row per returned post, using the post printer. When the
feed is empty, append one text row `no posts`. A feed value the user
evaluated directly uses this same listing for the posts it already
contains, capped at 20, without a second fetch.

An unavailable post and a blocked post have no Bluesky menu.

Each action retains the library object it appends. It does not
replace the source. A fetch failure appends one `Error` and no
partial listing. A successful presented object becomes `_` under the
existing value rule. An `Error` leaves `_` unchanged.

### 4.4 Python and the two commands

The primary path is an expression the user types. The spec writes
the exact pinned-library calls that do all of the following against
`https://public.api.bsky.app`, with no login:

- turn a `bsky.app` post URL into the thread result `:post` presents
- fetch a thread when the user already has an `at://` URI
- fetch a profile for a handle or DID
- fetch at most 20 posts for that author

Importing `atproto` in the listener does not happen until the user's
own `import`. Startup registration may import the library in the
application, as SymPy does, without binding it in the namespace.

`:post` takes the remainder of the line, as `:get` takes a URL. The
argument is one public `bsky.app` post URL or one post `at://` URI.
It presents the thread result. `:profile` takes the remainder of the
line as one handle or DID and presents the profile result. Both use
the public host, do not log in, and return the same classes the
Python calls return. A malformed argument or an unsupported URL
appends one `Error` and no Bluesky object.

The command path calls through one injected client seam. Tests
supply fixture results and failures. The seam enforces a 15-second
timeout. Automated tests never open a socket. The user's own
`Client` is not that seam. Objects it returns are presented because
their classes are registered.

### 4.5 What stays as it is

Chips, yank, accept, recall, completion, colon dispatch, and the
500-row history stay as they are. Documentation sentences stay on
the bottom specification. A Bluesky value uses the existing value
and menu sentences. Card controls and tutorial subjects stay as they
are. This series adds no tutorial card.

There is no login, session, post, reply composer, like, repost, or
follow. There is no home timeline, no image or video view, and no
fetch of a URL found inside a post.

### 4.6 Tests

Headless tests use fixture models and the injected client. They do
not import Textual and do not open a socket. Cover at least: a fresh
namespace has no `atproto`; a thread fixture keeps its identity and
prints `handle: text`; an empty text prints `handle: (no text)`; a
profile fixture prints its name and handle; a feed fixture presented
alone prints `feed: N posts`, including an empty feed and a feed whose
first item is a repost; the same fixture presented with a
caller-supplied handle prints `HANDLE: N posts` while the retained
object remains the fixture; unavailable and blocked fixtures print
their rows and offer no Bluesky menu; `author`,
`replies`, and `parent` append the fixture objects without replacing
the source; the reply cap and trailer; `no replies`; `posts` on a
profile uses the fake client and caps at 20; a transport failure is
one `Error` and leaves `_` unchanged; `:post` and `:profile` reject a
bad argument without calling the client.

Bsky 000 proves the rows, detail, and menus on fixtures. The
commands may stay unbound there.

Bsky 001 adds the injected client, `:post`, and `:profile`. The
screen may stay on the existing value drawing.

Bsky 002 is the screen test and the hand check. The screen test
drives a fixture through the menu with the injected client and reads
the post row, the text detail, and one reply row.

The hand check needs the network. From a disposable directory, run
`uv run pbui`. Using the Python calls from §4.4, open one public
post that has an author and at least one reply. Read the post row.
Left-click it and read the text. Open `author`, then `posts`. Open
`replies`, then one reply. Run `:post` with that same public URL and
see the same kind of row. `uv run pytest` is the automated gate.
`uv run pbui` is only the hand check. If the public host refuses the
hand check, report that and do not weaken the automated gate.

### 4.7 Slice order

**bsky 000** registers the pinned classes and proves rows, detail,
and menus on fixtures.

**bsky 001** adds the public client seam, `:post`, and `:profile`.

**bsky 002** adds the screen test and the hand check.

The checkpoint manager may split a slice that does not fit one
implementer conversation. The split keeps this order and adds no
feature. Do not add a slice for a tutorial subject, a post card, or
a write action.

## 5. Authority

The SymPy specification is the law for presenting a third-party
object by registering its class and retaining its identity. The HTTP
specification is the law for an injected fetch, a remainder-of-line
command argument, and tests that do not open a socket. The REPL
specification is the law for `_`, generic values, and chips.

Where this charter and an earlier specification disagree about the
row, detail, or menu of a registered Bluesky class, this exploration
wins. Where they disagree about a generic value, a chip, or a
command that is not `:post` or `:profile`, the earlier specification
wins.

## 6. Handoff reminder

The series identity is **bsky**. Checkpoint 000 is spoken **bsky
000** and filed as `checkpoints/000-slug.md`. Checkpoint 001 is
spoken **bsky 001**. Checkpoint 002 is spoken **bsky 002**. Numbers
are three digits, start at 000, and are never renumbered. The slug
is lowercase words separated by hyphens. The checkpoint manager
writes one checkpoint, then stops. Code and tests go at the project
root `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`,
not in this folder.

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. The first identity is **bsky 000**. The
second, in a later conversation, is **bsky 001**. The third, in a
later conversation, is **bsky 002**.

After the spec is accepted, `spec.md` is the design authority for
those conversations. This charter is the assignment for the spec
writer. Later conversations do not read it.
