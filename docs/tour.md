# Tour

This file is the working manuscript of the pbui tour. It is the ordered
path a new person walks: Listener, SymPy, HTTP, JSON, DataFrames, and
stock data with a candlestick chart. Start `uv run pbui` from the project
root and stay in that session for the whole path. Each subject is a few
card-sized stops. Objects from earlier stops stay in the session, and
later stops say what they expect to find already there.

The live cards behind `:tutorial` are the reader. This file is the
manuscript those cards can be cut from. [`user-guide.md`](user-guide.md)
is the command reference. A `demo.md` beside an exploration shows what
that one series made possible. This tour is the path across series.

If you were told to edit the tour, this file is the whole assignment.
The conversation that created it is background.

## Editing this file

Change this file directly. Read the tour, name the issue, and edit the
card. There is no charter, spec, or checkpoint for a wording change.

Leave the program alone. That includes `src/`, `tests/`, `AGENTS.md`,
`README.md`, [`user-guide.md`](user-guide.md), and everything under
`docs/design/implementation/`. Those series remain the law for what the
program does. When a card describes the program, follow the accepted
spec and the series README, and look at the program if the status line
has moved.

A leaf stays card-sized: a few sentences, at most one Try line, and the
three lines below.

- **Holding.** The object still in history when the leaf is done, or the
  editor state when the leaf loads a line and does not run it.
- **Next.** The next thing a reader of this manuscript should read.
  Inside a subject, Next follows the live card order where those cards
  exist. Across a subject boundary, Next is the handoff. The live
  tutorial's Next control still stops at the last card of a subject.
  This line does not add a control to the program.
- **See also.** A cross-reference that is not the next step. The user
  guide, a series demo, or another subject may be the target.

Mark a stop **tryable** only after you have confirmed the behavior is in
the program. A stop may be **drafted** from an accepted spec before the
listener can do it. Say which of the two it is. A future stop with no
accepted spec stays a placeholder.

Come back to the direction conversation, and leave the file unchanged,
when an edit would:

- add or drop a subject
- reorder the subjects
- change a decision under [Tour direction](#tour-direction)
- describe a command, menu, or object that has no accepted spec and is
  not reserved in this file
- change how this tour relates to `:tutorial` or to the user guide

Leaves inside a subject that is already on the path are editor work,
including JSON, DataFrames, and Stock data. Stock data uses the
implemented ticker and chart behavior.

## Tour direction

HTTP and JSON use the USGS earthquake feed for digging. DataFrames
starts a second request to the Treasury debt table and converts its
flat `data` array, not the earthquake `features`.

The four live HTTP leaves stay in place. The JSON subject practices
their general dig gesture on the earthquake value already in history;
it starts no new request.

Stock data uses the retained `yfinance.Ticker`, its `candlestick` chart,
and its `history` DataFrame. An ordinary DataFrame has no plot action.

## Path

1. [Listener](#listener)
2. [SymPy](#sympy)
3. [HTTP](#http)
4. [JSON](#json)
5. [DataFrames](#dataframes)
6. [Stock data](#stock-data)

Enter `:tutorial` to open "1. Presentations". In the listener, Contents
lists Listener, SymPy, and HTTP. JSON, DataFrames, and stock data are
subjects of this manuscript; continue them in the same listener
session. They are not Contents entries until a later tutorial series
adds them.

## Listener

Tryable. These five leaves are the live Listener section. Up goes to
Listener, and Up from Listener goes to Contents.

After these cards the reader can run a small expression, list a
directory, click a retained value, insert that value into an
expression, open a menu, and bring a submitted line back. SymPy starts
from an ordinary Python prompt. It does not need a file or a process
from these cards.

At an empty prompt, Up recalls an earlier submission; Tab completes a
name as you type, and Ctrl-G clears the line loaded by the last card
before SymPy.

### 1. Presentations

History keeps the object behind the text. Run the example, then click
the `6` result with an empty prompt to see its detail. Try loads the
line; Enter evaluates it.

Try: `1 + 2 + 3`

Holding: the retained `int 6` result and its detail.

Next: [2. Colon commands](#2-colon-commands)

See also: [Mouse and action menus](user-guide.md#mouse-and-action-menus).

### 2. Colon commands

Colon commands use the same editor as Python. `:ls` captures the
current directory; its file and directory rows keep objects you can
click later.

Try: `:ls`

Holding: a captured directory listing with retained member rows.

Next: [3. Reuse a value](#3-reuse-a-value)

See also: [Commands](user-guide.md#commands).

### 3. Reuse a value

Run the first example if `6` is not still in history. Type `10 + `,
then click that result: the editor inserts a chip for the exact object.
Press Enter to evaluate the completed expression.

Try: none. The reader types `10 +` and clicks the retained `6`.

Holding: the original `6` and a new `int 16` result.

Next: [4. The right-button menu](#4-the-right-button-menu)

See also: the [chips demo](design/implementation/chips/demo.md).

### 4. The right-button menu

Point at a row from `:ls` and read the documentation line. Right-click
a file or directory row, then choose `show` to append fresh detail for
that object. Esc or Ctrl-G closes a menu without running an action.

Try: none.

Holding: the listing row and the detail added by `show`.

Next: [5. Bring input back](#5-bring-input-back)

See also: [Mouse and action menus](user-guide.md#mouse-and-action-menus).

### 5. Bring input back

At an empty prompt, click the submitted `1 + 2 + 3` input row. Its
line loads into the editor, where you can change it or press Enter.
Right-clicking that row and choosing `yank` loads it too.

Try: none.

Holding: `1 + 2 + 3` in the editor, not yet submitted again.

Next: [SymPy](#sympy), in manuscript order. Live Next on this card
stops here.

See also: the [transcript demo](design/implementation/transcript/demo.md).

## SymPy

Tryable. The first four leaves are the live SymPy section. The next
two are manuscript stops for building expressions by clicking retained
values. The section card names simplify, expand, and factor. Simplify
has no leaf. Keep it that way.

The reader imports SymPy, binds `x` to a symbol, and keeps an expanded
expression and a factored expression in history. The reader then uses
one of those rows to build a product and reuses that product in a
quotient. HTTP does not use those expressions. They stay in the
session so later subjects can show older objects beside newer ones.

### 1. Import

Import SymPy in the listener's Python namespace. Enter keeps the
submitted line but adds no value row; later examples can now use
`sympy`.

Try: `import sympy`

Holding: the `sympy` name bound, with an empty editor.

Next: [2. Symbol](#2-symbol)

See also: the [SymPy demo](design/implementation/sympy/demo.md).

### 2. Symbol

Bind `x` to a SymPy symbol. This assignment adds an input row but no
value row. The next two expressions use that same `x`.

Try: `x = sympy.Symbol("x")`

Holding: the `x` name bound to a symbol, with an empty editor.

Next: [3. Expand](#3-expand)

See also: the [SymPy demo](design/implementation/sympy/demo.md).

### 3. Expand

Enter the power to keep its expression in history. Open that row's
menu and choose `expand`; a new row shows the expanded polynomial
while the power stays available.

Try: `(x + 1)**2`

Holding: `(x + 1)**2` and its `x**2 + 2*x + 1` result.

Next: [4. Factor](#4-factor)

See also: the [SymPy demo](design/implementation/sympy/demo.md#3-expand-a-retained-expression).

### 4. Factor

Enter the polynomial to keep it in history. Choose `factor` from that
row's menu; the factored result appears as another expression row.
The earlier expanded expression also remains available.

Try: `x**2 - 1`

Holding: `x**2 - 1` and its `(x - 1)⋅(x + 1)` result.

Next: [5. Multiply a retained expression](#5-multiply-a-retained-expression),
in manuscript order. Live Next on this card stops here.

See also: the [SymPy demo](design/implementation/sympy/demo.md#5-try-factor-and-simplify).

### 5. Multiply a retained expression

Tryable. At an empty prompt, type `x * (` and click the expanded
`x**2 + 2*x + 1` row from card 3. The click inserts a chip for that
exact expression; type `)` and press Enter to add the product to
history without retyping the polynomial.

Try: none.

Holding: the expanded expression and the new product with `x`.

Next: [6. Divide the product](#6-divide-the-product)

See also: the [chips demo](design/implementation/chips/demo.md).

### 6. Divide the product

Tryable. Bind `y`, then type `(` at an empty prompt and click the
product row from the previous stop. Type `) / y` and press Enter to
make a quotient from that retained product; the product stays in
history alongside it.

Try: `y = sympy.Symbol("y")`

Holding: the product, its quotient by `y`, and the bound `y` symbol.

Next: [HTTP](#http), in manuscript order.

See also: the [SymPy demo](design/implementation/sympy/demo.md#4-use-the-menu-result-as-a-python-object).

## HTTP

Tryable. The four leaves below are the live HTTP section. The first
leaf's Try is the USGS feed. Perform is the step that uses the network.
The request, the response, and the parsed JSON stay as separate rows.
The feed may fail or return a response without a usable `json` action;
in that case the browsing steps wait for a JSON response.

On a successful JSON response, these cards leave the USGS `JsonObject`,
its `metadata`, and its `features` in history. JSON continues with that
earthquake value; DataFrames later starts a separate Treasury request.

### 1. Make a request

Try loads the USGS `:get` line. Enter adds a retained `GET` request
without fetching; opening the card and clicking Try do not use the
network either.

Try: `:get https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson`

Holding: a `GET` request row for the USGS feed.

Next: [2. Perform the GET](#2-perform-the-get)

See also: the [HTTP demo](design/implementation/http/demo.md).

### 2. Perform the GET

Open the request row's menu and choose `perform`. The request stays,
and a response or an Error appears below it. A response's `body`
action shows decoded text; its `json` action is available when a JSON
response parses successfully.

Try: none. The menu action on the retained GET row is perform.

Holding: the request and, if the fetch succeeds, its response.

Next: [3. Open JSON](#3-open-json)

See also: the [HTTP demo](design/implementation/http/demo.md).

### 3. Open JSON

Open the response row's menu and choose `json`. Click the new
`JsonObject` summary with an empty prompt to list root members, then
click `["metadata"]` to read its title and count.

Try: none. The menu action on the response is json.

Holding: the response, parsed earthquake object, and `metadata` members.

Next: [4. Browse and reuse](#4-browse-and-reuse)

See also: the [HTTP demo](design/implementation/http/demo.md).

### 4. Browse and reuse

Click `["features"]` among the root members to list the array. If
`[0]` appears, click it and then `["properties"]` to read `place` and
`mag`; counts and place names are live. To reuse a JSON collection,
type `len(`, click its row, type `)`, and press Enter.

Try: none.

Holding: the earthquake root, its dug members, and a length result if run.

Next: [JSON](#json), in manuscript order. Live Next on this card
stops here.

See also: the [HTTP demo](design/implementation/http/demo.md).

## JSON

Tryable. These stops practice the general dig gesture on the
earthquake JSON already in history. No new request starts here, and
this value is not the one DataFrames converts.

Holding, for the subject: the retained earthquake JSON and its dug members.

Next: [DataFrames](#dataframes)

See also: [HTTP](#http) and the [records demo](design/implementation/records/demo.md).

### 1. List one level

With the editor empty, click the retained earthquake `JsonObject` or
one of its `JsonArray` members; start no new request. Its immediate
members appear as new rows, up to 100 at a time, while the collection
summary stays in history.

Try: none.

Holding: the collection and its immediate member rows.

Next: [2. Follow a member](#2-follow-a-member)

See also: [3. Open JSON](#3-open-json).

### 2. Follow a member

Click a member row whose value is another JSON collection. Its key or
index and its value are one click target, so this adds that value's
immediate members without another request. A scalar member instead
shows ordinary value detail; DataFrames will convert the Treasury
`data` array, not this earthquake value.

Try: none.

Holding: the earthquake collection and its newly listed members.

Next: [DataFrames](#dataframes), in manuscript order.

See also: [4. Browse and reuse](#4-browse-and-reuse).

## DataFrames

Tryable. Start a new Treasury request in the same session; the
earthquake JSON remains a browsing example. The Treasury `data` member
is the flat array of records this subject converts. If the request
fails, the frame steps wait, and Stock data can still follow.

A DataFrame or Series stays a live object. The frame preview and its
column and row hits are positional snapshots. Sorting and filtering
are ordinary pandas expressions, with no sort or filter menu here.
Only a whole DataFrame, not a Series, has `To JSON records`.

Holding, for the subject: a DataFrame the reader can preview, slice
by column or row, and turn back into JSON records.

Next: [Stock data](#stock-data)

See also: the [records demo](design/implementation/records/demo.md) and
the [pandas demo](design/implementation/pandas/demo.md).

### 1. Request the debt table

Tryable. Enter the Treasury `:get` command as one line. It adds a
retained GET request without fetching; this is separate from the
earthquake request above.

Try: `:get https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny?sort=-record_date&page[size]=10&fields=record_date,tot_pub_debt_out_amt`

Holding: the Treasury GET request row.

Next: [2. Perform the debt GET](#2-perform-the-debt-get)

See also: the [records demo](design/implementation/records/demo.md).

### 2. Perform the debt GET

Tryable. Open that GET row's menu and choose `perform` to make the
Treasury request. The request stays, and a response appears on
success. The records hand check could not resolve this API domain; if
one Error appears, the following frame steps wait.

Try: none.

Holding: the request and, on success, its response.

Next: [3. Open the debt JSON](#3-open-the-debt-json)

See also: [2. Perform the GET](#2-perform-the-get).

### 3. Open the debt JSON

Tryable. Choose `json` on the response, left-click the resulting
`JsonObject` to list its members, then left-click `["data"]`. The
retained `JsonArray` contains the debt records and offers a menu.

Try: none.

Holding: the Treasury response, root object, and `data` record array.

Next: [4. Make a frame](#4-make-a-frame)

See also: [1. List one level](#1-list-one-level).

### 4. Make a frame

Tryable. Choose `To DataFrame` on the `data` array's menu. The array
stays; the new frame has one row per returned record and columns
including `record_date` and `tot_pub_debt_out_amt`. Amounts remain
text when the JSON supplied strings; dates, amounts, and counts vary.

Try: none.

Holding: the Treasury record array and its new DataFrame.

Next: [5. Preview the frame](#5-preview-the-frame)

See also: the [records demo](design/implementation/records/demo.md).

### 5. Preview the frame

Tryable. Click the DataFrame summary with an empty editor. A bounded
snapshot appears below it, showing up to 12 rows and 6 columns. The
summary keeps the live frame; the preview keeps its captured values.

Try: none.

Holding: the DataFrame and its captured preview.

Next: [6. Take a column](#6-take-a-column)

See also: the [pandas demo](design/implementation/pandas/demo.md).

### 6. Take a column

Tryable. Click a column heading in the preview to append that
position's Series. Click its summary with an empty editor to list up
to 12 values as text. The preview and original frame remain.

Try: none.

Holding: the frame, preview, extracted Series, and listed values.

Next: [7. Take a row](#7-take-a-row)

See also: the [pandas demo](design/implementation/pandas/demo.md#3-take-the-second-column-and-list-it).

### 7. Take a row

Tryable. Click a row label in the captured preview to append a
one-row DataFrame. That result is a separate frame; the original
summary and preview stay in history.

Try: none.

Holding: the original frame, its preview, and a one-row frame.

Next: [8. Return to JSON records](#8-return-to-json-records)

See also: the [pandas demo](design/implementation/pandas/demo.md#5-take-a-row-then-change-the-source-frame).

### 8. Return to JSON records

Tryable. Open the original whole frame's menu and choose
`To JSON records`. The new `JsonArray` holds one `JsonObject` per frame
row; its index is omitted. Click the array to list its immediate records.

Try: none.

Holding: the whole DataFrame and its JSON records array.

Next: [Stock data](#stock-data), in manuscript order.

See also: the [records demo](design/implementation/records/demo.md).

## Stock data

Tryable. A retained `yfinance.Ticker` can request a candlestick chart
or a daily price DataFrame. Both actions make live Yahoo requests, so
their results may differ. In the chart series' AAPL hand check,
`candlestick` appended `no prices` and `history` still appended a frame.

### 1. Import

Import yfinance into this listener's Python namespace. Enter retains
the input line but adds no ticker value yet.

Try: `import yfinance`

Holding: the `yfinance` name bound, with an empty editor.

Next: [2. Make a ticker](#2-make-a-ticker)

See also: the [ticker demo](design/implementation/ticker/demo.md).

### 2. Make a ticker

Evaluate the expression to keep a `Ticker AAPL` value in history.
Hovering it does not fetch prices; with an empty prompt, a left click
shows its detail without fetching either.

Try: `yfinance.Ticker("AAPL")`

Holding: the retained `Ticker AAPL` value.

Next: [3. Show the chart](#3-show-the-chart)

See also: the [ticker demo](design/implementation/ticker/demo.md).

### 3. Show the chart

Right-click that ticker and choose `candlestick`, below `history`.
On success, a 60-cell chart shows `Ticker AAPL`, 12 candle rows, an
axis, and first and last visible dates: the newest 15 daily bars run
oldest to newest from left to right, with a trailer for omitted days.
Green candles rose or stayed flat; red candles fell. Use a terminal
at least 62 cells wide to see the drawing past its history indent.
If `no prices` or one Error appears, keep the ticker and continue to
[Prices as a frame](#5-prices-as-a-frame).

Try: none.

Holding: the ticker and a chart, or the `no prices` or Error row.

Next: [4. Read a candle](#4-read-a-candle)

See also: the [chart demo](design/implementation/chart/demo.md).

### 4. Read a candle

If a chart appeared, point at a three-cell candle to read its date
and rose or fell status on the documentation line. With an empty
editor, click it to append captured date, Open, High, Low, and Close;
the chart stays. Pointing at a gap names the chart; with an empty
editor, clicking it appends nothing. While typing a Python expression,
clicking a candle inserts a `Candle YYYY-MM-DD` chip; clear that
unfinished line with Ctrl-G before continuing.

Try: none.

Holding: the chart and one candle detail, when a chart appeared.

Next: [5. Prices as a frame](#5-prices-as-a-frame)

See also: the [chart demo](design/implementation/chart/demo.md).

### 5. Prices as a frame

On the same ticker, choose `history` for another live Yahoo request;
on success it appends a DataFrame without drawing another chart. If
it fails, one Error appears and the ticker remains.
When prices are present, click its summary to preview `Close`; the
dates are the frame index.
`To JSON records` on this frame omits that index; `_.reset_index()`
appends a frame whose dates are a column, so they survive conversion.

Try: `_.reset_index()` after a successful history result.

Holding: the ticker and, on success, a price frame and optional
date-column frame.

Next: end of the manuscript.

See also: the [ticker demo](design/implementation/ticker/demo.md).
