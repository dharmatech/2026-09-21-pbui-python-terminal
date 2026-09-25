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

Try: `1 + 2 + 3`

Holding:

Next: [2. Colon commands](#2-colon-commands)

See also:

### 2. Colon commands

Try: `:ls`

Holding:

Next: [3. Reuse a value](#3-reuse-a-value)

See also:

### 3. Reuse a value

Try: none. The reader types `10 +` and clicks the retained `6`.

Holding:

Next: [4. The right-button menu](#4-the-right-button-menu)

See also:

### 4. The right-button menu

Try: none.

Holding:

Next: [5. Bring input back](#5-bring-input-back)

See also:

### 5. Bring input back

Try: none.

Holding:

Next: [SymPy](#sympy), in manuscript order. Live Next on this card
stops here.

See also:

## SymPy

Tryable. These four leaves are the live SymPy section. The section
card names simplify, expand, and factor. Simplify has no leaf. Keep
it that way.

The reader imports SymPy, binds `x` to a symbol, and keeps an expanded
expression and a factored expression in history. HTTP does not use
those expressions. They stay in the session so later subjects can show
older objects still present beside newer ones.

### 1. Import

Try: `import sympy`

Holding:

Next: [2. Symbol](#2-symbol)

See also:

### 2. Symbol

Try: `x = sympy.Symbol("x")`

Holding:

Next: [3. Expand](#3-expand)

See also:

### 3. Expand

Try: `(x + 1)**2`

The menu action on that expression is expand.

Holding:

Next: [4. Factor](#4-factor)

See also:

### 4. Factor

Try: `x**2 - 1`

The menu action on that expression is factor.

Holding:

Next: [HTTP](#http), in manuscript order. Live Next on this card
stops here.

See also:

## HTTP

The four leaves below are the live HTTP section. The first leaf's Try
is the USGS feed. Perform is the step that uses the network. The
request, the response, and the parsed JSON stay as separate rows.

What this subject leaves for JSON depends on the open choice of feed.
With the live cards, the reader can be holding the USGS `JsonObject`,
its `metadata`, and its `features`. A DataFrame subject that wants a
flat array of records needs a different retained array than those
features. See [Direction still open](#direction-still-open).

### 1. Make a request

Try: `:get https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson`

Holding:

Next: [2. Perform the GET](#2-perform-the-get)

See also:

### 2. Perform the GET

Try: none. The menu action on the retained GET row is perform.

Holding:

Next: [3. Open JSON](#3-open-json)

See also:

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

Subject agreed. Leaves are not named yet. You may add card-sized
leaves for behavior the program already has: left-click a `JsonObject`
or `JsonArray` to list its members, and click a member to dig.

The DataFrames subject expects a `JsonArray` whose elements are
`JsonObject`s, or one `JsonObject`. Nested values stay cells if that
value later becomes a frame. Do not teach `json_normalize`, and do not
flatten nested fields. Do not remove or rewrite the HTTP leaves
"3. Open JSON" and "4. Browse and reuse" while the overlap above is
still open.

Holding, for the subject: a JSON value the next subject can turn into
a frame, once the feed question is settled.

Next: [DataFrames](#dataframes)

See also: the HTTP leaves above, and the records series.

## DataFrames

Subject agreed. Leaves are not named yet. You may draft card-sized
leaves from the accepted pandas and records specifications. Mark each
one tryable or drafted after you check the pandas and records series
READMEs.

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

See also: the records series and the pandas series.

## Stock data

Reserved. No leaves.

This stop is where a later price history could arrive as a DataFrame
and sit beside the frames from the previous subject. No source,
command, or card is chosen. Write nothing under this heading until
the direction conversation names the behavior.
