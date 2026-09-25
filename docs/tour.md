# Tour

This file is the working manuscript of the pbui tour. It is the ordered
path a new person walks: Listener, SymPy, HTTP, JSON, DataFrames, and
stock data. Each subject is a few card-sized stops. Objects from earlier
stops stay in the session, and later stops say what they expect to find
already there.

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
- resolve an item under [Direction still open](#direction-still-open)
- describe a command, menu, or object that has no accepted spec and is
  not reserved in this file
- change how this tour relates to `:tutorial` or to the user guide

Leaves inside a subject that is already on the path are editor work,
including the first leaves under JSON and DataFrames. Stock data is
reserved and has no leaves until direction names the behavior.

## Direction still open

These stay as written until the direction conversation decides them.

The live HTTP cards fetch the USGS 2.5-day earthquake feed. Its
`features` are nested, so they are a poor direct `To DataFrame`
example. The records series uses a Treasury `debt_to_penny` GET whose
`data` member is a flat array of objects, with `record_date` and
`tot_pub_debt_out_amt`. The tour has not chosen whether one request
carries the reader from HTTP through DataFrames, or whether DataFrames
starts from a second request. The URLs already fixed elsewhere are:

```text
:get https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson
:get https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny?sort=-record_date&page[size]=10&fields=record_date,tot_pub_debt_out_amt
```

The live HTTP section already contains JSON browsing, in "3. Open JSON"
and "4. Browse and reuse". This manuscript also has a JSON subject
after HTTP. How those two accounts share the dig, and whether the
manuscript's HTTP subject keeps those two leaves, is undecided. Leave
the four HTTP leaves in place.

Stock data is a reserved subject. There is no ticker, price history,
indicator, or chart in the program, and no accepted spec for one.
Write no leaves under it.

## Path

1. [Listener](#listener)
2. [SymPy](#sympy)
3. [HTTP](#http)
4. [JSON](#json)
5. [DataFrames](#dataframes)
6. [Stock data](#stock-data)

`:tutorial` still opens "1. Presentations". In the listener, Contents
lists Listener, SymPy, and HTTP. JSON, DataFrames, and stock data are
subjects of this manuscript. They are not Contents entries until a
later tutorial series adds them.

## Listener

Tryable. These five leaves are the live Listener section. Up goes to
Listener, and Up from Listener goes to Contents.

After these cards the reader can run a small expression, list a
directory, click a retained value, insert that value into an
expression, open a menu, and bring a submitted line back. SymPy starts
from an ordinary Python prompt. It does not need a file or a process
from these cards.

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

Tryable. These four leaves are the live SymPy section. The section
card names simplify, expand, and factor. Simplify has no leaf. Keep
it that way.

The reader imports SymPy, binds `x` to a symbol, and keeps an expanded
expression and a factored expression in history. HTTP does not use
those expressions. They stay in the session so later subjects can show
older objects still present beside newer ones.

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

Next: [HTTP](#http), in manuscript order. Live Next on this card
stops here.

See also: the [SymPy demo](design/implementation/sympy/demo.md#5-try-factor-and-simplify).

## HTTP

Tryable. The four leaves below are the live HTTP section. The first
leaf's Try is the USGS feed. Perform is the step that uses the network.
The request, the response, and the parsed JSON stay as separate rows.
The feed may fail or return a response without a usable `json` action;
in that case the browsing steps wait for a JSON response.

What this subject leaves for JSON depends on the open choice of feed.
With the live cards, the reader can be holding the USGS `JsonObject`,
its `metadata`, and its `features`. A DataFrame subject that wants a
flat array of records needs a different retained array than those
features. See [Direction still open](#direction-still-open).

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

Try: none. The menu action on the response is json.

Holding:

Next: [4. Browse and reuse](#4-browse-and-reuse)

See also:

### 4. Browse and reuse

Try: none.

Holding:

Next: [JSON](#json), in manuscript order. Live Next on this card
stops here.

See also:

## JSON

Tryable. These stops use any retained `JsonObject` or `JsonArray`.
The HTTP leaves above provide one example, but this subject does not
choose which JSON value leads into DataFrames.

The DataFrames subject expects a `JsonArray` whose elements are
`JsonObject`s, or one `JsonObject`. Nested values stay cells if that
value later becomes a frame. Do not teach `json_normalize`, and do not
flatten nested fields. Do not remove or rewrite the HTTP leaves
"3. Open JSON" and "4. Browse and reuse" while the overlap above is
still open.

Holding, for the subject: a JSON value the next subject can turn into
a frame, once the feed question is settled.

Next: [DataFrames](#dataframes)

See also: [HTTP](#http) and the [records demo](design/implementation/records/demo.md).

### 1. List one level

With the editor empty, click a retained `JsonObject` or `JsonArray`.
Its immediate members appear as new rows, up to 100 at a time; the
collection summary stays in history.

Try: none.

Holding: the collection and its immediate member rows.

Next: [2. Follow a member](#2-follow-a-member)

See also: [3. Open JSON](#3-open-json).

### 2. Follow a member

Click a member row whose value is another JSON collection. Its key or
index and its value are one click target, so this adds that value's
immediate members. A scalar member instead shows ordinary value detail.

Try: none.

Holding: the nested collection and its newly listed members. The
specific value for DataFrames is still undecided.

Next: [DataFrames](#dataframes), in manuscript order.

See also: [4. Browse and reuse](#4-browse-and-reuse).

## DataFrames

The five leaves below are drafted as a tour path. The pandas and
records interactions are implemented, but the JSON source that hands
the reader a flat array of records is still an open direction choice.

Behavior those leaves may use:

- A DataFrame or Series stays a live object. A left click on the
  summary appends a positional snapshot and leaves the summary in
  place. A column heading yields that column as a Series. A row label
  yields a one-row DataFrame. A Series click lists values as text.
- `To DataFrame` is a menu action on a `JsonObject`, or on a
  `JsonArray` of `JsonObject`s. The source stays in history.
- `To JSON records` is a menu action on a whole DataFrame. The index
  is omitted. The source frame stays in history.
- Sorting and filtering a frame are ordinary pandas expressions. This
  tour does not add a sort or filter menu.

The records hand check digs to the Treasury `data` array and then uses
`To DataFrame`. Amounts there are text unless the JSON numbers were
already numeric. Do not promise a particular date, amount, or row
count. A `Series` has no `To DataFrame` or `To JSON records` action.

Holding, for the subject: a DataFrame the reader can preview, slice
by column or row, and turn back into JSON records.

Next: [Stock data](#stock-data)

See also: the [records demo](design/implementation/records/demo.md) and
the [pandas demo](design/implementation/pandas/demo.md).

### 1. Make a frame

Drafted. Once the chosen JSON path leaves a `JsonArray` of
`JsonObject` records, open that array's menu and choose `To DataFrame`.
One `JsonObject` also qualifies. The source stays in history.

Try: none.

Holding: the eligible JSON source and its new DataFrame.

Next: [2. Preview the frame](#2-preview-the-frame)

See also: the [records demo](design/implementation/records/demo.md).

### 2. Preview the frame

Drafted. Click the DataFrame summary with an empty editor. A bounded
snapshot appears below it, showing up to 12 rows and 6 columns. The
summary keeps the live frame; the preview keeps its captured values.

Try: none.

Holding: the DataFrame and its captured preview.

Next: [3. Take a column](#3-take-a-column)

See also: the [pandas demo](design/implementation/pandas/demo.md).

### 3. Take a column

Drafted. Click a column heading in the preview to append that
position's Series. Click its summary with an empty editor to list up
to 12 values as text. The preview and original frame remain.

Try: none.

Holding: the frame, preview, extracted Series, and listed values.

Next: [4. Take a row](#4-take-a-row)

See also: the [pandas demo](design/implementation/pandas/demo.md#3-take-the-second-column-and-list-it).

### 4. Take a row

Drafted. Click a row label in the captured preview to append a
one-row DataFrame. That result is a separate frame; the original
summary and preview stay in history.

Try: none.

Holding: the original frame, its preview, and a one-row frame.

Next: [5. Return to JSON records](#5-return-to-json-records)

See also: the [pandas demo](design/implementation/pandas/demo.md#5-take-a-row-then-change-the-source-frame).

### 5. Return to JSON records

Drafted. Open the original whole frame's menu and choose
`To JSON records`. The new `JsonArray` holds one `JsonObject` per frame
row; its index is omitted. Click the array to list its immediate records.

Try: none.

Holding: the whole DataFrame and its JSON records array.

Next: [Stock data](#stock-data), in manuscript order.

See also: the [records demo](design/implementation/records/demo.md).

## Stock data

Reserved. No leaves.

This stop is where a later price history could arrive as a DataFrame
and sit beside the frames from the previous subject. No source,
command, or card is chosen. Write nothing under this heading until
the direction conversation names the behavior.
