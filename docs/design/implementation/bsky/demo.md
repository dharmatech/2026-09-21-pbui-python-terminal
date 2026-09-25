# Try public Bluesky objects

This is a hands-on tour of the completed Bluesky exploration. A public post, profile, or author feed appears as a history row that retains the atproto SDK object. You can click a post for its text, use menus to follow replies and authors, and pass a retained object into another Python expression.

## Start

From the project root, launch pbui in an interactive terminal:

```console
cd /home/dharmatech/journal/2026-09-21-pbui-python-terminal
uv run pbui
```

Type the examples below at **pbui's bottom input line**, keeping one session open. Unprefixed lines are Python; listener commands start with `:`. Leave the input empty before clicking a row for detail. Hover over a row and press Ctrl-O, or right-click it, to open its menu. Use Ctrl-C to exit when finished.

This tour reads public Bluesky data over the internet. It needs no account or login. The examples do not use file or process commands or make Bluesky write requests. The example is [a public post from bsky.app](https://bsky.app/profile/bsky.app/post/3mseeq5rllc2q). If it becomes unavailable or loses its replies, choose another public post with a direct reply and substitute its web URL, actor, and record key in the examples.

## 1. Create a public client

Enter these lines separately:

```python
from atproto import Client, Request
client = Client(base_url="https://public.api.bsky.app", request=Request(timeout=15.0))
```

The input rows appear in history, but neither line adds a result row. The client is in your Python session; pbui does not prebind `Client` or log in for you.

## 2. Present a thread result

Enter these lines separately:

```python
thread = client.get_post_thread("at://bsky.app/app.bsky.feed.post/3mseeq5rllc2q")
thread
```

The first line fetches and assigns the response. The second presents it. Its one-line row should begin `bsky.app: ` followed by post text, possibly shortened with `…` to fit 120 display cells. The row retains the **whole thread response**, including its reply graph, even though the row describes the subject post.

## 3. Read the text and use the retained object

With the editor empty, left-click the post row. Its text appears as new detail rows, split at real newlines. The original post row stays in history, and the click does not change `_`.

Now type `id(` and leave the expression unfinished. Left-click the original post row again. This time the click inserts an object chip into the input instead of showing detail. Type `) == id(thread)` and press Enter. The result should be `bool True`: Python received the exact response stored in that row, rather than its displayed text.

## 4. Follow direct replies

Scroll back to the original post row if needed. Open its menu and choose `replies`. New rows show up to 20 **direct** replies in their SDK order. A reply row retains its own thread node; left-click one with an empty editor to read its text, or open its menu to continue from that reply. The first replies action does not expand nested replies. If there are more than 20, a non-clickable `… (N more replies)` line follows the listed rows.

## 5. Open the author and their posts

Open the original post row's menu again and choose `author`. A detailed profile row appears; for this example it has been `Bluesky — bsky.app`, though the display name may change. Open that profile's menu and choose `posts`. A bounded list of up to 20 post rows appears. These are the SDK's post-view objects, including actual post authors if the author's feed contains reposts. The profile row remains in history.

## 6. Try the two listener commands

Enter this command at the bottom prompt:

```text
:post https://bsky.app/profile/bsky.app/post/3mseeq5rllc2q
```

It fetches a new thread response and draws the same kind of `bsky.app: …` row as the Python call. Immediately enter `type(thread) is type(_)`. The result should be `bool True`: the command and direct SDK call returned the same class. This comparison then changes `_` to the Boolean result.

Now enter:

```text
:profile bsky.app
```

It fetches a detailed profile and draws its name and handle. Both commands use the unauthenticated public host and append an `Error` if the public service refuses a request.

## 7. Present an author-feed response directly

Enter these lines separately:

```python
feed = client.get_author_feed("bsky.app", limit=20)
feed
```

The result row reads `feed: N posts`, with `N` at most 20. Open that row's `posts` menu to list its existing entries without fetching a second page. The feed response remains the value of the original row; each listed post row retains its own SDK `PostView` object.

The [specification](spec.md) defines the full behavior. This tour is a read-only way to try the completed interaction before it becomes a formal tutorial subject.
