# bsky 000 — Retained models and local graph

**Status.** Implemented per user report.

## Goal

Pin atproto, register its public Bluesky result classes as existing `Value` presentations, and implement their rows, post detail, and fixture-local graph actions in the headless listener. Prove that presentations and chips retain the exact SDK objects. Stop after this slice. The injected public client, fetch-backed actions, `:post`, `:profile`, the screen test, and the live hand check belong to later checkpoints.

## Authority and starting point

The implementer receives this checkpoint and the accepted [spec](../spec.md); the checkpoint narrows the spec to one slice and does not revise it.

- Identity: **bsky 000**, the first checkpoint in the **bsky** series. There is no predecessor checkpoint.
- Governing spec: sections 1–4, 7, and 8. Section 4 defines this slice’s behavior. Sections 5–6 are later work, except where section 4 identifies deferred fetch-backed actions.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Code, tests, and dependency metadata go there, outside this design folder.
- Preserve the accepted listener, REPL, chips, menus, transcript, documentation, and 500-row history rules. Only `pbui.terminal` imports Textual.

## File scope

Create `src/pbui/bsky.py` for pure SDK model access and row/detail helpers. Edit `src/pbui/repl.py` for registered `Value` rows and post detail, and `src/pbui/commands.py` for startup registration, dynamic Bluesky menus, local actions, and `HeadlessListener.present_bsky_feed`. Add the dependency through uv, updating `pyproject.toml` and `uv.lock`. Create `tests/test_bsky.py` for focused headless tests. Edit `tests/test_terminal.py` only in `test_dependency_metadata_and_terminal_import_boundary` to include `atproto==0.0.72` in the expected direct-dependency list in the order recorded by `uv add`; keep every other assertion in that test unchanged.

Leave `src/pbui/terminal.py`, all other existing tests, other application modules, and other design files untouched. This dependency expectation is the only authorized change to an existing test. If another file is necessary, stop and send this checkpoint back to the checkpoint manager instead of widening the slice. Do not add a presentation type, copied post/profile records, client injection, a network transport, colon commands, login, write actions, media handling, a post card, or a tutorial subject.

## SDK registration and identity

Use exactly `atproto==0.0.72`. Register these classes from `atproto.models` through the existing Python-class `Value` mechanism:

| SDK class | Retained value |
|---|---|
| `AppBskyFeedGetPostThread.Response` | The response itself; its `.thread` is the subject. |
| `AppBskyFeedDefs.ThreadViewPost` | The exact visible reply or parent node. |
| `AppBskyFeedDefs.PostView` | The post view, including `.post` from a feed entry. |
| `AppBskyFeedDefs.NotFoundPost` | The unavailable node. |
| `AppBskyFeedDefs.BlockedPost` | The blocked node. |
| `AppBskyActorDefs.ProfileViewDetailed` | The detailed profile. |
| `AppBskyFeedGetAuthorFeed.Response` | The feed response. |

Traverse `FeedViewPost` only to reach its `.post`; do not register it. `ProfileViewBasic`, a raw post record, and unrelated SDK models stay generic. Keep first-match MRO lookup, the generic fallback, and one `Value` type. Application startup may import SDK classes, but a fresh evaluator namespace remains exactly `{"__name__": "__pbui__"}`. The user imports SDK names explicitly. A Python chip of a response, reply, or feed post carries the exact retained object.

If a thread response has an unrecognized `.thread` union member, give it a generic `Value` row and no Bluesky menu. Missing and blocked response subjects use their specific rows and have no Bluesky menu.

## One-line rows and feed presentation

- Visible thread responses, thread nodes, and post views draw `AUTHOR_HANDLE: TEXT`. For a node, read `.post.author.handle` and `.post.record.text`; for `PostView` read `.author.handle` and `.record.text`. Empty text becomes `(no text)`. Keep links and facets as characters in the text.
- A detailed profile draws `DISPLAY_NAME — HANDLE`, or `HANDLE` when display name is absent or empty. Missing and blocked nodes or response subjects draw exactly `unavailable post` and `blocked post`, respectively.
- A directly evaluated feed response draws `feed: N posts`, where `N = min(len(feed), 20)`. This holds for an empty feed and one starting with a repost.
- Add `HeadlessListener.present_bsky_feed(feed, *, handle=None)`. It appends one `Value` retaining the same feed and updates `_`. A caller-supplied handle draws `HANDLE: N posts`; without one it draws the ordinary feed row. This handle is presentation metadata, never assigned to the response or inferred from any feed entry.
- Registered printers return raw rows with no class prefix. The existing `Value` path escapes controls, tabs, embedded newlines, and surrogates, then caps the complete row at 120 display cells with `…` inside the cap. A printer failure follows the existing fallback-`Value` and one-`Error` rule while retaining the object.

## Click detail

At an empty non-accept prompt, left-clicking a visible thread response, thread node, or post view appends its library text as `Text` rows. Split on actual newlines before escaping; preserve empty internal lines. Append at most 24 lines, each capped at 120 display cells, then exactly `… (N more lines)` if lines remain. Empty text produces one empty `Text` row. Calculate the lines before appending so a failure yields one `Error` and no partial detail. Leave `_` and the source unchanged. Profiles, feeds, missing posts, and blocked posts retain generic `Value` detail. Typed `:show` still does not accept `Value`.

## Menus and local actions

Supply labels in this order:

| Retained value | Menu labels |
|---|---|
| Visible thread response or thread node | `author`, `replies`, then `parent` only when its node has a non-`None` `.parent` |
| `PostView` | `author`, `replies` |
| `ProfileViewDetailed` or author-feed response | `posts` |
| Missing or blocked node or response subject | No Bluesky menu |

The normal basic-author `author` action, profile `posts` action, and `PostView` `replies` action need a fetch; their labels are required now, and their fetch behavior belongs to bsky 001. If an embedded author is already exactly `ProfileViewDetailed`, its `author` action appends that object by identity. Never substitute a basic profile. Drawing or opening a menu makes no fetch.

Implement these local actions through the existing menu and `MenuActionInput` path, including run again against the saved original target:

1. `replies` on a retained thread node or visible response subject appends at most the first 20 immediate `.replies` nodes in SDK order. Each row is a `Value` retaining its exact node, including missing or blocked nodes. Do not recurse. If more than 20 exist, append one non-presented `Text` trailer exactly `… (N more replies)`. If none exist, append one `Text` row `no replies`.
2. `parent` appends the exact retained `.parent` node, visible or unavailable, without a fetch.
3. `posts` on a retained author-feed response lists the first 20 existing `.feed` entries in SDK order. Append each entry's exact `.post` as a `PostView` `Value`, including repost entries. Do not fetch or append a second feed response. If empty, append one `Text` row `no posts`.

Each successful appended `Value` updates `_` in order, leaving the last one there. A text-only listing leaves `_` unchanged. Keep the source in history subject to normal eviction. Preserve composition and chip precedence, popup rules, and registered-`Value` documentation. Local formatting failures follow the existing `Value` error rule. Do not create a temporary production client or use a network response to test this slice.

## Focused automated verification

Build real pinned-SDK model fixtures in `tests/test_bsky.py`, without importing Textual or opening a socket. Prove:

1. Fresh namespace, class registration, generic behavior for unrelated SDK models, response/reply/feed-post identity, `_`, and chip identity.
2. Visible and empty-text post rows, profile name fallback, ordinary and caller-labeled feed rows (including empty and repost-first), missing and blocked rows without menus, unrecognized subject fallback, escaping, and 120-cell caps.
3. One-line, multiline, and empty post detail; internal blank lines and unsafe characters; the 24-line cap and exact trailer; one `Error` and no partial detail on extraction failure.
4. Exact menu order and conditional parent; local replies in SDK order, first-20 cap and trailer, `no replies`, exact parent identity, direct-feed `posts` with reposts, `no posts`, and saved local action target identity. Check `_` updates only when `Value` rows are appended.
5. Presenting a value or opening its menu makes no fetch. Existing generic values, other commands, and typed `:show` keep their predecessor behavior.

## Verification and completion

If `uv` is missing, stop and report it. From the project root, run:

```console
uv add 'atproto==0.0.72'
uv sync
uv run pytest
```

Do not use `pip`, `python -m pip`, `uv pip install`, another package manager, or a handmade environment. The full `uv run pytest` suite must pass, with no automated socket use. `uv run pbui` and the public-host hand check belong to bsky 002.

Bsky 000 is complete when the dependency, registration, rows, detail, local menus and listings, identity tests, and full automated suite satisfy this checkpoint and the accepted spec. Report changed files and test results, then stop without starting bsky 001.
