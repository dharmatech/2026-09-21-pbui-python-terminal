# bsky 001 — Public client, fetch menus, and commands

**Status.** Implemented per user report.

## Goal

Complete public Bluesky reads through one injected client seam. Make the deferred `author`, profile `posts`, and `PostView` `replies` menu actions executable, and add `:post` and `:profile`. Keep the SDK objects as the presented values. Stop after headless verification; the Textual screen test and live public-host hand check belong to bsky 002.

## Authority and starting point

The implementer receives this checkpoint and the accepted [spec](../spec.md); the checkpoint narrows the spec to one slice and does not revise it.

- Series identity: **bsky**. This is **bsky 001**. Its predecessor, [bsky 000](000-retained-models-and-local-graph.md), is implemented and was reported passing the full 383-test suite. Build on its registered classes, rows, detail, local listings, and saved menu actions.
- Governing spec: sections 1–5, 7, and 8. Section 5 assigns the new client, validation, commands, and fetch-backed actions. Section 4 continues to govern resulting rows, identity, listing caps, `_`, and errors. Section 6 is later work.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Code and tests stay there, outside the design folder. Python remains `>=3.11` and `atproto==0.0.72` remains the direct pin.

## File scope

Edit `src/pbui/bsky.py` for headless post-URI and actor validation or small SDK helpers. Edit `src/pbui/commands.py` for the optional `bsky_client` constructor keyword, lazy production client, fetch-backed menu actions, and colon commands. Extend `tests/test_bsky.py` with SDK fixture and injected-fake tests. Edit `tests/test_commands.py` only to add `post` and `profile` to its exact `listener.command_names` expectation, matching their implemented order; leave all other assertions in that test unchanged. Edit `tests/test_terminal.py` only in `test_completion_list_overlay_keys_click_and_menu` to make its Tab wraparound count depend on `len(screen.completion_candidates)` after the highlight reaches index 9; preserve its other completion, scrolling, and history assertions.

Leave `src/pbui/repl.py`, `src/pbui/terminal.py`, all other existing tests and application modules, `pyproject.toml`, `uv.lock`, and the design files untouched. If another file is necessary, stop and send the checkpoint back to the checkpoint manager instead of widening the slice. Do not upgrade the SDK or add a dependency, presentation type, copied post/profile record, tutorial subject, login, write action, media fetch, linked-page fetch, or home timeline.

## Client seam and production construction

Add one optional `bsky_client` keyword to `HeadlessListener`. A supplied fake implements operations equivalent to `get_post_thread(uri)`, `get_profile(actor)`, and `get_author_feed(actor, limit=20)`. All bsky commands and fetch-backed menus use this seam. With no supplied client, create the production client lazily on the first fetch, using exactly:

```python
from atproto import Client, Request
Client(base_url="https://public.api.bsky.app", request=Request(timeout=15.0))
```

Use the synchronous SDK client and do not call `login`. The 15-second timeout belongs to its HTTP transport. The user's independently created Python `Client` is unaffected; application startup still leaves the evaluator namespace at `{"__name__": "__pbui__"}`. Drawing a row, showing detail, opening a menu, and evaluating an already-held SDK object make no command-client call. Tests inject a fake or monkeypatch construction; no automated test opens a socket. Preserve the pinned result classes and the 000 registration.

## Post and profile commands

Add `post` and `profile` to colon command names and the existing unbound bare-command hint. Bare `post` and `profile` remain Python expressions; neither command injects an SDK name or client into the Python namespace.

At an ordinary prompt, `:post ARGUMENT` and `:profile ARGUMENT` take the entire remainder after the command name and its required separating whitespace as one argument, following the `:get` remainder rule. Do not split it into tokens or begin a typed presentation accept. Missing or empty remainder appends one `Error`. Record the normal `CommandInput` row before a result or `Error`, and clear the command attempt through the existing path.

`:post` accepts exactly one of:

- An HTTPS URL on host `bsky.app` with path `/profile/ACTOR/post/RKEY`. Validate the actor and record key, then call `get_post_thread("at://ACTOR/app.bsky.feed.post/RKEY")`. An HTTPS query or fragment may be ignored after host and path validation.
- An `at://ACTOR/app.bsky.feed.post/RKEY` URI. Validate it, then pass that URI to `get_post_thread`.

The actor must be a syntactically valid handle or DID, and the record key must be valid and nonempty, following the accepted spec's linked AT URI authority. Reject extra path segments, credentials, a nonstandard port, whitespace, an AT URI query or fragment, another scheme or host, and malformed actor or record-key syntax. Parsing makes no redirect or handle-resolution request. `:profile` accepts exactly one syntactically valid handle or DID, with no URL, whitespace, or extra token.

Validate before even calling an injected fake. Invalid input appends one `Error` and no Bluesky object or client call, leaving `_` unchanged. A successful `:post` appends the exact `AppBskyFeedGetPostThread.Response` returned by the client as one `Value`. A successful `:profile` appends the exact `ProfileViewDetailed` returned by the client as one `Value`. Both update `_` under the existing successful-value rule and use the bsky 000 printers. Do not wrap or reconstruct the result. Client exceptions, timeouts, and invalid response/model results append one `Error`, no substitute `Value`, and leave `_` unchanged. A valid thread response with an unrecognized `.thread` subject still follows the generic-row rule in section 3 of the spec.

## Fetch-backed menus

Complete the bsky 000 menu labels through the same client seam:

1. `author` on a visible post uses its `PostView.author`. If that author is already exactly `ProfileViewDetailed`, append it by identity without fetching. Otherwise call `get_profile(post.author.did)` and append the returned detailed profile as a `Value`. Do not present a basic profile.
2. `posts` on a `ProfileViewDetailed` calls `get_author_feed(profile.did, limit=20)` once, then lists at most the first 20 `.feed` entries through the existing local feed listing behavior. Append each exact `FeedViewPost.post` as a `PostView` `Value` in SDK order, including repost entries; do not append the feed response unless a caller separately presents it. Empty feed yields one `Text` row `no posts`. `posts` on an already-retained feed remains local and makes no second fetch.
3. `replies` on a retained `PostView` calls `get_post_thread(post.uri)` once and applies the existing immediate-replies rule to the fetched subject. Append at most 20 direct nodes by identity in SDK order, with the existing `no replies` and `… (N more replies)` behavior. A fetched missing or blocked subject has no reply objects to append; do not invent a post. `replies` on a retained thread response or node remains local and makes no fetch. `parent` remains local.

Keep the original source presentation in history. Each appended `Value` updates `_` in order; text-only results leave it unchanged. Fetch errors produce one `Error` and no partial listing, leaving `_` unchanged. Validate a fetched result and its listing members before appending a fetch-backed list, so a bad response does not create a partial list. Repeating a fetch-backed action makes a fresh client call. Run again on a saved `MenuActionInput` still uses its original target. Existing composition, chip, popup, documentation, and history-cap rules remain in force.

## Focused automated verification

Use real pinned-SDK fixtures and an injected fake in `tests/test_bsky.py`. Cover:

1. Fake injection and lazy production construction, the public base URL, 15-second `Request` timeout, and no `login`; drawing and menu opening make no fake call. An SDK fixture evaluated through user Python still prints and retains its class without using the command seam.
2. `:post` URL-to-AT conversion and AT pass-through, `:profile` actor forwarding, exact result class and object identity, `CommandInput` then `Value` order, `_` updates, and bare-command hints. Exercise handles and valid DIDs.
3. Missing and empty arguments; malformed scheme, host, actor, record key, path, credentials, port, whitespace, AT query/fragment, and profile URL/extra token. Each invalid case makes zero fake calls and appends one `Error` after its input row.
4. Basic-author profile fetch by DID, already-detailed author without fetch, profile-feed fetch with `limit=20`, first-20 cap, empty and repost-inclusive listings, retained-feed listing without a second fetch, and `PostView` thread fetch by URI with only direct replies. Prove listed object identities, `_`, and unchanged source rows.
5. Client exception, timeout, and malformed response for each command and fetch-backed action: one `Error`, no partial `Value` listing, stable `_`. Repeating an action and run again make a fresh call on the captured original target. Confirm existing local actions remain socket-free.
6. The only predecessor-test adjustments are the exact command-name tuple in `tests/test_commands.py` and the candidate-count-dependent Tab wraparound in `tests/test_terminal.py`. Keep the rest of the old suite green.

## Verification and completion

If `uv` is missing, stop and report it. From the project root, run:

```console
uv sync
uv run pytest
```

Do not use `pip`, `python -m pip`, `uv pip install`, another package manager, or a handmade environment. The full suite, including existing tests, must pass without an automated socket call. The `uv run pbui` live hand check is assigned to bsky 002.

Bsky 001 is complete when the three fetch-backed menu routes, the two commands, validation, identity and failure tests, and the full automated gate satisfy this checkpoint and the accepted spec. Report changed files and test results, then stop without starting bsky 002.
