# bsky 002 — Screen route and public hand check

**Status.** Implemented per user report; `uv run pytest` passed 434 tests and
the public, read-only hand check passed.

## Goal

Prove that the completed public Bluesky objects work through the full terminal screen: post row, click detail, menu navigation through replies and author posts, object-bearing hit targets, documentation, chip precedence, and scrolling. Then attempt and report one live read-only public-host session. Stop after this slice; it is the final checkpoint in the bsky series.

## Authority and starting point

The implementer receives this checkpoint and the accepted [spec](../spec.md); the checkpoint narrows the spec to one slice and does not revise it.

- Series identity: **bsky**. This is **bsky 002**. [Bsky 000](000-retained-models-and-local-graph.md) and [bsky 001](001-public-client-and-commands.md) are implemented. The bsky 001 implementer reported `uv run pytest` passing all 433 tests.
- Governing spec: sections 1–3 and 6–8 for this slice. Sections 4–5 remain authoritative for the objects, rows, menus, commands, and client seam exercised on screen. The charter is not an implementation input.
- Project root: `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application code and tests stay there, outside this design folder. Keep Python `>=3.11` and the direct `atproto==0.0.72` pin.

## File scope

Add a focused Bluesky screen test in `tests/test_terminal.py`, using real pinned-SDK fixture models and an injected fake `bsky_client`. Existing screen-test helpers in that file may be reused. Edit `src/pbui/terminal.py` only if the new screen test demonstrates a concrete terminal adapter gap that prevents the accepted bsky behavior; keep any fix limited to that gap and cover it in the same screen test. Among application modules, only `pbui.terminal` may import Textual.

Leave `src/pbui/bsky.py`, `src/pbui/commands.py`, `src/pbui/repl.py`, all other application and test files, `pyproject.toml`, `uv.lock`, and design files untouched. If another tracked file becomes necessary, stop and send the checkpoint back to the checkpoint manager instead of widening the slice. A fresh disposable directory beneath the project root is permitted solely for the live hand check. Do not add a new presentation type, SDK wrapper, network dependency, login, write action, tutorial subject, media viewer, or post card.

## Screen route

Use `PbuiApp.run_test()` with a headless listener carrying the fake client. The automated screen test must open no socket. Its fixture thread response has a visible subject with an author and at least one direct reply; provide a parent if needed to verify the conditional third menu item. Its fake profile and author-feed results include at least one post. Drive the actual screen route, not direct calls to `invoke_python_translator` as a substitute for the menu.

Prove these visible behaviors:

1. The subject row displays `AUTHOR_HANDLE: TEXT` while its history presentation retains the exact `AppBskyFeedGetPostThread.Response` fixture. Hovering it uses the existing registered-`Value` documentation sentence. At an empty prompt, left-click its visible hit area and read the resulting text detail row. The source row and `_` remain unchanged by detail.
2. Open the subject's menu with the existing screen gesture. Verify `author`, `replies`, and conditional `parent` order. Select `replies` through the menu; the new row shows the direct reply's handle and text. At the row's visible coordinates, `HistorySurface.presentation_at_content_offset` resolves to a presentation whose value is the exact `ThreadViewPost` fixture. A click on that reply follows the same post detail behavior. No nested reply is listed by the first replies action.
3. Reopen the source's menu and select `author` through the screen. The fake client receives the author's DID and the resulting Value retains its detailed profile fixture. Open that profile's `posts` menu item through the screen. The fake receives `get_author_feed(profile.did, limit=20)`; the resulting post row retains the exact `FeedViewPost.post` fixture. The feed response need not be appended.
4. Verify the existing registered-`Value` and menu-item documentation while hovering the source and a menu item. During valid Python composition, clicking the source inserts a chip carrying the exact response and does not append detail. The existing accept/composition precedence remains intact. A menu action during composition preserves pending input and cursor. Use enough history to exercise ordinary scrolling and confirm an older Bluesky row's visible hit target still resolves to its original presentation after scrolling.

The screen test may be one focused test or a few related tests. Use the existing screen click/menu helpers or equivalent pointer events so its assertions cover user-visible routing. Do not replace headless bsky 000/001 assertions with screen-only checks. Preserve ordinary popup geometry, documentation, transcript, history-cap, and other command behavior.

## Automated verification

Run the full suite through uv. The new screen test must pass with the fake client and no socket, alongside all predecessor tests. It must establish visible text and menu order, exact response/reply/profile/feed-post identity, client arguments, documentation, chip precedence, and scrolling. A source change to `src/pbui/terminal.py` is justified only by a failing screen assertion that shows an adapter gap; report the gap and the focused fix.

## Live public-host hand check

After `uv sync` and the full `uv run pytest` gate pass, create a **fresh disposable directory under the project root**, record its absolute path, and launch `uv run pbui` from that directory in a real interactive terminal. One way, starting at the project root, is:

```console
bsky_check_dir=$(mktemp -d "$PWD/.bsky-002-XXXXXX")
cd "$bsky_check_dir"
pwd
uv run pbui
```

Choose one public `bsky.app` post with an author and at least one direct reply. Record its web URL and corresponding `at://` URI. In one pbui session, explicitly type the SDK imports and construct the public, unauthenticated client specified in section 5 of the spec:

```python
from atproto import Client, Request
client = Client(base_url="https://public.api.bsky.app", request=Request(timeout=15.0))
thread = client.get_post_thread("at://HANDLE/app.bsky.feed.post/RKEY")
thread
```

Use the chosen real handle or DID and record key in place of the placeholders. Read the post row, left-click for its text, open `author` then `posts`, open `replies` then one reply, and run `:post` on the same `bsky.app` URL. Confirm the Python and command results are the same SDK class and draw the same kind of post row. Run `:profile` on that author's handle and confirm the detailed-profile row. Do not log in or perform a write action.

Report the disposable directory path, public post URL or URI, observed row/detail/menu traversal, class comparison, command results, and any limitation. If the public host refuses or the interactive terminal is unavailable, report the attempted step and exact obstacle; do not claim the hand check passed or weaken the automated gate.

## Verification and completion

If `uv` is missing, stop and report it. From the project root run, in order:

```console
uv sync
uv run pytest
```

Use `uv run pbui` only for the live hand check from the disposable directory. Do not use `pip`, `python -m pip`, `uv pip install`, another package manager, or a handmade environment.

Bsky 002 is complete when the socket-free screen route passes the full suite and the live public-host hand check has been attempted and reported with its result or exact external limitation. Report changed files, the test count, the disposable directory path, and the live observations; then stop. Do not begin another feature or checkpoint.
