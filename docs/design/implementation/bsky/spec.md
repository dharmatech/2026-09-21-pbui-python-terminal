# Specification — public Bluesky objects

**Status:** Accepted for implementation.

Public Bluesky reads produce ordinary object-bearing Value presentations. A presentation retains the exact object returned by the pinned atproto SDK even when its row describes a post inside that object. This file is the complete design input for the checkpoint manager and implementers; they do not need the charter.

## 1. Checkpoint series

The stable identity is **bsky**. Checkpoint 000 is spoken **bsky 000** and filed as checkpoints/000-slug.md. Numbers have three digits, begin at 000, and are never renumbered. Slugs use lowercase words separated by hyphens. The checkpoint manager writes one checkpoint and stops; each implementer works on one checkpoint in a separate conversation and stops after verification. Code and tests go at the project root, /home/dharmatech/journal/2026-09-21-pbui-python-terminal/, not in this design folder. Once accepted, this specification is the design authority for those conversations.

The order is **bsky 000** (SDK pin, registration, rows, detail, and fixture-local menus), **bsky 001** (injected public client, fetch-backed menus, and the two commands), then **bsky 002** (screen test and live hand check). A manager may split a layer too large for one implementer conversation, keeping this order and adding no feature.

## 2. Product boundary and prior authority

The listener presents public posts, their direct reply and parent graph, detailed profiles, and one bounded page of an author's feed. The user's Python expression is the primary path. The :post and :profile commands are conveniences over the same SDK result classes. This effort adds no login, session management, write action, composer, like, repost, follow, home timeline, media viewer, linked-page fetch, post card, or tutorial subject. It creates no copied Post or Profile record.

The accepted [SymPy specification](../sympy/spec.md) governs third-party class registration and identity. The accepted [HTTP specification](../http/spec.md) governs the injected fetch seam, remainder-of-line command argument, and socket-free tests. The accepted [REPL specification](../repl/spec.md) governs generic values, errors, _, and chips. The Bluesky rows, details, and menus below supersede generic Value behavior only for their registered classes. Earlier specifications continue to govern other classes and commands. Chips, yank, accepts, recall, completion, colon dispatch, transcript rows, popup geometry, card controls, documentation sentences, and the 500-logical-row history limit retain their existing rules. Bluesky values use the existing registered-Value and menu documentation sentences.

## 3. Host, dependency, SDK types, and files

Use the existing src/pbui/ package and tests/. Python remains requires-python = ">=3.11". Use uv exclusively. In bsky 000 run uv add 'atproto==0.0.72' from the project root, then uv sync and uv run pytest. The direct dependency is exactly **atproto 0.0.72**, recorded in pyproject.toml and resolved in uv.lock. Later slices do not upgrade it or install it from Git. Prefer no other direct dependency. Use uv run pbui only for the bsky 002 hand check. If uv is missing, stop and report it. Do not run uv init in this existing package. The spec writer does not run uv.

The relevant classes exposed by from atproto import models are:

| SDK class | Role |
|---|---|
| models.AppBskyFeedGetPostThread.Response | Exact result of Client.get_post_thread; its .thread is the subject. |
| models.AppBskyFeedDefs.ThreadViewPost | Visible subject, direct reply, or parent; .post is the view, .replies and .parent retain the graph. |
| models.AppBskyFeedDefs.PostView | Post view under a thread node or an author-feed entry; .record.text and .author supply its row. |
| models.AppBskyFeedDefs.NotFoundPost | Unavailable subject, reply, or parent. |
| models.AppBskyFeedDefs.BlockedPost | Blocked subject, reply, or parent. |
| models.AppBskyActorDefs.ProfileViewDetailed | Exact result of Client.get_profile. |
| models.AppBskyFeedGetAuthorFeed.Response | Exact result of Client.get_author_feed; .feed contains the entries. |
| models.AppBskyFeedDefs.FeedViewPost | One feed entry; its .post is the listed PostView. |

Register the thread response, ThreadViewPost, PostView, NotFoundPost, BlockedPost, detailed profile, and author-feed response using the existing Python-class Value mechanism. FeedViewPost is traversed to reach .post, not registered itself. ProfileViewBasic on PostView.author, a raw app.bsky.feed.post.Record, other feed responses, and every other SDK model remain generic when evaluated directly. Keep first-MRO-match registration, one Value presentation type, and the existing generic fallback. If a thread response contains an unrecognized .thread union member, use a generic Value row and no Bluesky menu rather than calling it a visible post.

The pinned SDK shapes and calls are documented in its [client reference](https://atproto.blue/atproto_client/client/), [thread response](https://atproto.blue/models/app/bsky/feed/getPostThread/), [feed definitions](https://atproto.blue/en/latest/atproto/atproto_client.models.app.bsky.feed.defs.html), [actor definitions](https://atproto.blue/models/app/bsky/actor/defs/), and [author-feed response](https://atproto.blue/models/app/bsky/feed/getAuthorFeed/). The selected release is [atproto 0.0.72 on PyPI](https://pypi.org/project/atproto/0.0.72/). This pre-1.0 API is fixed for this series.

Put pure model access, row formatting, and post-URI validation in src/pbui/bsky.py or equivalent small headless code. Extend src/pbui/repl.py for registered Value detail, src/pbui/commands.py for listener registration, menu actions, injection, and commands, and src/pbui/terminal.py only where the screen test exposes an adapter gap. Tests belong in tests/test_bsky.py and a focused screen test. Only pbui.terminal imports Textual.

## 4. bsky 000 — retained models, rows, and local graph

At startup application code may import SDK classes for registration, as it does with SymPy. The evaluator's namespace still begins with only {"__name__": "__pbui__"}. It does not bind atproto, Client, models, or a client; the user imports those names explicitly. Every result stays the exact object passed to Value. A Python chip retains it by identity. In particular, a get_post_thread result presents the **response itself**, although its row describes response.thread.post. A reply row retains the exact ThreadViewPost inside .replies. A feed listing row retains the exact FeedViewPost.post.

### One-line rows and detail

A visible thread response, ThreadViewPost, or PostView has the raw row AUTHOR_HANDLE: TEXT. Substitute (no text) when TEXT is the empty string. On a thread node read .post.author.handle and .post.record.text; on PostView read .author.handle and .record.text. Links and facets remain characters in that text; no linked URL or media is fetched. A ProfileViewDetailed row is DISPLAY_NAME — HANDLE, or just HANDLE if the display name is absent or empty. A NotFoundPost, or a thread response whose subject is one, has the row unavailable post. The corresponding BlockedPost row is blocked post.

An author-feed response has no actor field. Its ordinary row is feed: N posts, including an empty feed or one beginning with a repost. N is min(len(feed), 20), the number of entries this series will list; each entry contributes its .post, including a repost entry returned by the endpoint. A caller that **already has the author's handle** and chooses to present that same response may instead label that presentation HANDLE: N posts. That handle is row metadata, never written onto the response and never taken from a feed post. The profile posts action below appends post rows directly, so it creates no labeled feed row. Direct Python evaluation always uses feed: N posts.

Expose HeadlessListener.present_bsky_feed(feed, *, handle=None) for a caller that already owns a feed response. It appends one Value retaining feed, updates _ by the ordinary successful-value rule, and uses the optional handle only for this presentation's row. The normal Python displayhook calls the ordinary value path without a handle.

Registered printers supply raw rows without class prefixes. The existing Value path escapes controls, tabs, embedded newlines, and surrogates, then caps each complete row at 120 display cells, keeping … inside the cap. The object is unchanged. A printer failure follows the existing fallback-Value and one-Error rule.

At an empty non-accept prompt, left click on a visible post response, ThreadViewPost, or PostView appends its library text as Text detail rows. Split on actual newlines before escaping and cap each row at 120 display cells. Append at most 24 lines, preserving empty internal lines, then exactly … (N more lines) if more remain. Empty text produces one empty Text row. Calculate lines before appending; a failure appends one Error and no partial detail. Detail leaves _ and the source unchanged. Profiles, feeds, unavailable posts, and blocked posts retain ordinary generic Value detail. Typed :show still does not accept Value.

### Menus and listings

A visible post's menu has author, replies, and, only when the retained thread node has a non-None .parent, parent, in that order. PostView has no retained thread parent, so it has author and replies. A response uses its .thread; a ThreadViewPost uses itself. Unavailable and blocked posts, including response-wrapped subjects, have no Bluesky menu.

For a retained thread node, replies uses only its immediate .replies in SDK order. Append Value rows for the first 20 nodes, including missing or blocked nodes, retaining each by identity. If more than 20 exist, append one non-presented Text trailer exactly … (N more replies). If none exist, append one Text row no replies. It never recursively expands a child. The child has its own replies action. Parent appends the exact retained .parent node, visible or unavailable. These actions do not fetch. A PostView has no .replies, so bsky 001 obtains its thread by .uri and then applies this same direct-list rule, without replacing the source.

Author appends a ProfileViewDetailed. If the post's embedded author is already that exact class, append it by identity. The normal PostView.author is ProfileViewBasic, so bsky 001 fetches a detailed profile by its DID through the injected client. Do not substitute a basic profile. A detailed profile has exactly one menu item, posts. An author-feed response also has exactly one menu item, posts. A feed's posts action lists the first 20 existing .feed entries without a second fetch. A profile's posts action fetches one author-feed page with limit=20 in bsky 001 and lists its first 20 entries. Each row retains the entry's .post as PostView, uses the post printer, and keeps SDK order. There is no pagination. If there are no entries, append one Text row no posts. Author feeds can include reposted posts; those entries use the actual post author and text.

An action appending Values updates _ to each successful value in order; the last displayed object remains _. An action appending only Text leaves _ unchanged. The source remains in history, subject to normal capacity eviction. Existing MenuActionInput, run again, chips, composition precedence, and popup rules apply. A failed fetch appends one Error and no partial listing; _ is unchanged. Local formatting failures use the existing Value error rule.

Bsky 000 pins the dependency, registers the classes, implements rows and detail, and proves menu labels plus local replies and parent on SDK fixtures. It proves the author and posts menu labels and a directly evaluated feed's local posts listing. Fetch-backed actions become executable in bsky 001; the two commands may remain unbound in bsky 000. No bsky 000 test contacts the network.

## 5. bsky 001 — injected public reads and commands

The production command client is the SDK's synchronous Client(base_url="https://public.api.bsky.app", request=Request(timeout=15.0)), with Client and Request imported from atproto. Request passes a 15-second timeout to its HTTP transport. Never call login. The headless listener has one injectable client seam with operations equivalent to get_post_thread(uri), get_profile(actor), and get_author_feed(actor, limit=20). Production uses the public client; tests pass a fake returning SDK fixture models or raising. All command and fetch-backed menu calls use this seam. The user's own Python-created Client is independent; its result still has the registered class. Drawing a row or opening a menu makes no fetch.

Use one optional bsky_client constructor keyword for a test fake; with no supplied client, create the production client lazily at the first fetch. The seam is independent of the user's Python namespace.

The exact direct Python calls are:

~~~python
from atproto import Client, Request
client = Client(base_url="https://public.api.bsky.app", request=Request(timeout=15.0))
thread = client.get_post_thread("at://HANDLE/app.bsky.feed.post/RKEY")
thread
profile = client.get_profile("HANDLE_OR_DID")
profile
feed = client.get_author_feed("HANDLE_OR_DID", limit=20)
feed
~~~

For https://bsky.app/profile/HANDLE_OR_DID/post/RKEY, construct at://HANDLE_OR_DID/app.bsky.feed.post/RKEY and call client.get_post_thread(uri). An existing post at:// URI is passed to the same method. The [AT URI specification](https://atproto.com/specs/at-uri-scheme) allows a handle or DID authority. get_post_thread returns AppBskyFeedGetPostThread.Response, get_profile returns ProfileViewDetailed, and get_author_feed returns AppBskyFeedGetAuthorFeed.Response. Python and colon commands therefore present the same classes. The [Bluesky public API reference](https://docs.bsky.app/docs/api/app-bsky-feed-get-author-feed) identifies the unauthenticated AppView host for public app.bsky.* reads.

Add post and profile to the colon command names. At an ordinary prompt, :post ARGUMENT and :profile ARGUMENT consume the **entire remainder after the command name and its required separating whitespace** as one argument, like :get; do not split it into words or enter a typed presentation accept. Missing or empty remainder is an Error. Post accepts exactly one HTTPS URL on host bsky.app with path /profile/ACTOR/post/RKEY, or one at://ACTOR/app.bsky.feed.post/RKEY URI. ACTOR is a syntactically valid handle or DID and RKEY a valid nonempty record key. Reject extra path components, credentials, nonstandard port, whitespace, query or fragment on an AT URI, and other schemes or hosts. An HTTPS URL's query or fragment may be ignored once host and path pass validation. Parsing makes no redirect or handle-resolution request. Profile accepts exactly one syntactically valid handle or DID, with no URL, whitespace, or extra token. Validate before even a fake client call; invalid input appends one Error and no Bluesky object or client call.

The normal CommandInput row precedes the result or Error. On success :post calls the injected get_post_thread with the normalized URI and appends the **returned response object** as one Value. Profile calls get_profile with the actor and appends its exact returned detailed profile. Both update _ under the existing successful-value rule. Client exceptions, timeouts, and response/model failures append one Error and no substitute object; _ remains unchanged. Bare post and profile remain Python names and join the existing unbound bare-command hint. Neither command injects an SDK name into Python.

Complete fetch-backed menus through the same seam. Author calls get_profile(post.author.did) unless the embedded author is already ProfileViewDetailed. A profile's posts calls get_author_feed(profile.did, limit=20), then lists .post objects as in section 4; it need not append the feed response. Replies on PostView calls get_post_thread(post.uri) and lists only the fetched subject's direct replies. An unavailable or blocked fetched subject yields no replies and no invented post. Fetch errors append one Error and no partial list. Repeating a fetch-backed action makes a fresh call. Saved menu actions retain their original target for run again.

Tests use injected fakes and SDK fixture models. They prove URI conversion, client parameters, the 20-entry cap, identity, profile fetch for a basic author, direct-feed listing without a second fetch, validation before any client call, and one Error with stable _ for each fetch failure. No automated test opens a socket.

## 6. bsky 002 — screen and live hand check

Drive SDK fixtures through PbuiApp.run_test() with the fake client. Read the visible handle: text row, left-click at an empty prompt and read a detail row, open the menu, select replies, and read a direct reply row whose hit target retains the fixture reply. Exercise author and posts through the screen route. Verify registered-Value documentation, menu order, composition/chip priority, and ordinary history scrolling. Preserve the terminal adapter unless this test exposes a necessary gap.

Run uv sync and uv run pytest first. For the live hand check, make a fresh disposable directory under the project root, record its absolute path, and start there with uv run pbui. Choose one public post with an author and at least one reply. In one session, explicitly import Client and Request, construct the public client above, evaluate get_post_thread on its AT URI, read the row, left-click for text, open author then posts, open replies then one reply, and run :post on the same bsky.app URL. Confirm Python and command results have the same SDK class and kind of row; also run :profile on the author's handle. Do not log in. If the public host refuses the hand check, report that without weakening the automated gate.

## 7. Verification

Automated tests are headless except the explicit Textual screen test. They build real SDK model fixtures and inject a fake client. They do not open a socket. Bsky 000 covers fresh namespace without atproto; thread, reply, chip, feed, and parent identity; normal and empty post text; row safety and 120-cell caps; multiline detail, 24-line cap and trailer; profile name fallback; unavailable and blocked rows without menus; direct empty and repost-first feeds; caller-supplied feed label without mutation; menu order; reply cap and trailer; no replies; and generic handling for unrelated SDK classes. Bsky 001 covers fetch-backed author, posts, and PostView replies; 20-entry cap; _ updates; errors without partial listings; both commands' argument, identity, class, and error paths; and no client call for invalid input. Bsky 002 covers the screen flow and the public hand check.

The automated gate is uv run pytest, including all old tests. Python remains >=3.11. uv run pbui is only the live hand check; public-host reachability is not a prerequisite for automated tests.

## 8. Acceptance

A public thread result itself is retained under a post row, a chip holds that same result, and clicks can traverse author and direct replies without reconstructing SDK records. Reply rows retain their SDK nodes and support the same post interaction. A detailed profile opens a bounded author-feed listing whose rows retain SDK PostView objects. A directly evaluated feed retains its SDK response and uses feed: N posts; a handle labels that same response only when the caller already knows it. Missing and blocked subjects have distinct rows and no Bluesky menu. :post and :profile present the same classes as corresponding user-written SDK calls, use the unauthenticated public host, and append one Error for invalid input or fetch failure. Automated tests remain socket-free, the screen route works, the live hand check is reported, and the old suite passes with requires-python unchanged.
