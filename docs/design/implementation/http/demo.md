# Try HTTP requests and JSON browsing

This is a hands-on tour of the completed HTTP exploration. A GET request is a
retained object: making the request row does not fetch anything. Its `perform`
action adds a separate response row. A JSON response can then become a tree of
Python values that you walk one level at a time by clicking.

The prescribed Reddit hand check returned HTTP 403. The local examples
use a small server or Python values and need no external network. Steps 7–9
use the public Hacker News API and need an internet connection, but no
account. To start at step 7, skip the server setup and launch pbui from the
project root as shown below.

## Start a local server

In one terminal, run these commands from the project root. They create three
temporary files and then keep the server running on `127.0.0.1:8765`:

```console
cd /home/dharmatech/journal/2026-09-21-pbui-python-terminal
uv sync
pbui_http_demo_dir=$(mktemp -d -t pbui-http-demo.XXXXXX)
cat > "$pbui_http_demo_dir/tree.json" <<'JSON'
{
  "data": {
    "children": [
      {"name": "Ada", "active": true},
      {"name": "Lin", "active": false}
    ],
    "count": 2
  },
  "message": "hello"
}
JSON
printf 'not valid JSON\n' > "$pbui_http_demo_dir/broken.json"
printf 'hello from the local server\n' > "$pbui_http_demo_dir/plain.txt"
uv run python -m http.server 8765 --bind 127.0.0.1 --directory "$pbui_http_demo_dir"
```

Leave that terminal open. In a **second** terminal, start pbui:

```console
cd /home/dharmatech/journal/2026-09-21-pbui-python-terminal
uv run pbui
```

All input below is typed **inside pbui**. Keep the same session open, and
leave its input line empty before an ordinary dig or replay click. Listener
commands begin with `:`; unprefixed input is Python. Use Ctrl-C to exit pbui
when finished. If port 8765 is busy, choose another port for the server and
use it in each URL below.

## 1. Make a request without fetching

Enter:

```text
:get http://127.0.0.1:8765/tree.json
```

History gains these rows in order:

```text
› :get http://127.0.0.1:8765/tree.json
GET http://127.0.0.1:8765/tree.json
```

The server has not been contacted yet. Left-clicking the request at an
empty prompt shows its Python value detail; the request row stays in history.

Right-click the request row, or hover over it and press Ctrl-O. Its menu has
one item, `perform`. Choose it. A marked `› perform — …` action row appears
before a new `HTTP 200 http://127.0.0.1:8765/tree.json` response row. The
original GET row remains. Choosing `perform` again adds another response; it
does not replace the request.

## 2. Open the JSON value

Right-click the **response** row, or hover and press Ctrl-O. Its menu lists
`json` first and `body` second. Choose `json`. A marked action row appears,
then a `▸ JsonObject (2 keys)` summary row. That row stores a Python
`JsonObject`; it does not print the whole response body.

The result also becomes the REPL's `_` value. Enter `first_json = _` now to
keep a name for it. This assignment adds an input row but no result row.
With the editor empty, left-click the earlier `› json — …` **action input**
row. It runs `json` again and adds another summary row. Enter
`id(_) == id(first_json)`; the result should be `bool True`. The replay used
the same parsed object, rather than parsing a second tree.

## 3. Dig through the tree

At an empty prompt, left-click the newest `▸ JsonObject (2 keys)` row. It
remains in history and appends its immediate members:

```text
["data"]  ▸ JsonObject (2 keys)
["message"]  str 'hello'
```

Left-click **anywhere** on the `["data"]` row, including its label. That
whole row presents the nested object. It adds `["children"]  ▸ JsonArray
(2 elements)` and `["count"]  int 2`; the root and `data` rows remain.
Click the `children` row to get `[0]` and `[1]` member rows, each presenting
a `JsonObject`. Click `[0]` to see its `name` and `active` members. Each click
adds one level at the end of history. Scroll up if an earlier parent moves
off the visible screen.

Hover over a JSON object or array row. The documentation line says that left
click lists its members and right click has no menu. Hovering over a member's
key or index label gives the same target and documentation as hovering over
its value text.

You can also use the parsed tree as ordinary Python data. Enter
`first_json["data"]["children"][0]["name"]`; the result should be
`str 'Ada'`.

## 4. Insert the retained object into Python

Type `len(` but do not press Enter. Left-click a `▸ JsonObject (2 keys)` row.
Instead of digging, the click inserts a chip of that exact stored object into
the expression. Type `)` and press Enter. The result should be `int 2`.
The chip's label is display only; pbui passed the object itself to `len`.

With an empty input line, a left click on the same row digs again. A plain
Python dictionary behaves differently: enter `{"ordinary": 1}` and
left-click its resulting `dict` row. It shows generic value detail rather
than a JSON member list.

## 5. Compare body text, invalid JSON, and HTTP status

Open the original `HTTP 200 …/tree.json` response menu again and choose
`body`. It appends one `Text` row containing the response bytes decoded as
text. The file's newlines appear as escaped `\n` characters inside that one
logical row. `body` does not change `_`.

Now enter `:get http://127.0.0.1:8765/plain.txt` and choose `perform` on its
request. Its `HTTP 200` response has only `body` in the menu, since the
content type is not JSON. Choosing `body` displays `hello from the local
server\n` as one Text row.

Enter `:get http://127.0.0.1:8765/broken.json` and perform it. The response
row stays, followed by one `Error` explaining the invalid JSON. Its menu
still offers `body`, but omits `json`; opening the menu does not add another
parse error.

For an HTTP status example, enter `:get http://127.0.0.1:8765/missing.txt`
and perform it. The server's 404 appears as an `HTTP 404 …` **response**, not
a transport `Error`. It also has a `body` action. In contrast, entering
`:get file:///etc/passwd` makes a retained request, but `perform` adds an
`Error` because that scheme is not allowed; it does not read the file.

## 6. See the one-click member limit

Enter these two lines separately:

```python
from pbui.http import JsonArray
JsonArray(range(101))
```

The second line shows `▸ JsonArray (101 elements)`. Left-click it with the
editor empty. One dig appends `[0]` through `[99]`, followed by the literal
`… (1 more members)` trailer. The trailer is not clickable. The parent row
is not edited, although the normal 500-row history limit may eventually
evict older rows. A second click on the parent appends the same bounded set
again.

## 7. Browse live Hacker News top-story IDs

The [official Hacker News API](https://github.com/HackerNews/API) publishes
JSON without a login. You can do these live steps in the same pbui session;
the local server can stay running, but Hacker News does not use it.

Enter:

```text
:get https://hacker-news.firebaseio.com/v0/topstories.json
```

The GET row is still inert until you choose `perform`. Its response should be
`HTTP 200`; choose `json` from the response menu. You should see a
`▸ JsonArray (N elements)` row containing ranked item IDs rather than story
titles. Left-click that summary to add `[0]`, `[1]`, and other integer member
rows. One click shows at most 100 IDs. In our hand check, there were 500 IDs,
so the rows ended at `[99]` with a literal `… (400 more members)` trailer.
The counts and ranking can change.

## 8. Open a story and find its comments

Read the number on `[0]` in your current top-story list. To fetch that item,
put its number into `/v0/item/ID.json` in a new `:get` command. A click on the
integer row only shows its value detail; it does not fetch the item.

Here is a story that was first in the list during our hand check and had
comments:

```text
:get https://hacker-news.firebaseio.com/v0/item/49826565.json
```

Choose `perform`, then `json` on the HTTP 200 response. Click the
`▸ JsonObject` summary. Its member rows include `["title"]`,
`["descendants"]`, and `["kids"]`. This example's title is “Early rogue AI
agent activity and attempts to hack found on urlquery.net”. The `kids` row
presents a `JsonArray` of comment IDs; click anywhere on that row to list
the IDs. The story and `kids` parent rows stay in history. In our check,
`kids` had 24 elements and `[0]` was `49827082`. Those values can change as
discussion continues.

## 9. Read a comment and follow one reply

Use a comment ID from the story's `kids` array in another item URL. For the
first comment we saw, enter:

```text
:get https://hacker-news.firebaseio.com/v0/item/49827082.json
```

Choose `perform`, then `json`, and click its `▸ JsonObject` summary. The
`["parent"]` member is `49826565`, linking it back to the story. The
`["text"]` member is the comment content. Its one-line value can be
truncated; left-click that scalar row with an empty editor to append its
value detail. Hacker News supplies comment text as HTML, which pbui shows
as text rather than rendering.

This comment also had a `["kids"]  ▸ JsonArray (7 elements)` row during our
check. Click it to see reply IDs. Its first reply was `49827224`; fetch it
with:

```text
:get https://hacker-news.firebaseio.com/v0/item/49827224.json
```

Choose `perform` and `json`, then click the reply object. Its
`["parent"]  int 49827082` row shows that it replies to the comment above.
Each comment needs its own `:get` because the API returns child IDs, not
nested comment objects.

## Finish

Exit pbui with Ctrl-C. If you started the local server, press Ctrl-C in
that terminal too. You can then remove only this tour's temporary files with
`rm -r "$pbui_http_demo_dir"` in that same terminal.

The [specification](spec.md) defines the full behavior; this tour is for
trying the completed interaction by hand.
