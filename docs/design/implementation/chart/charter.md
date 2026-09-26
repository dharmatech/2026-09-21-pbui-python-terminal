# Charter — candlestick chart

**Status.** Handoff from the high-level discussion into a **design
conversation**. Not a checkpoint. Not an implementer assignment.
This file lives in `docs/design/implementation/chart/`. The
specification will live beside it as [`spec.md`](spec.md).
Checkpoint files will live in `checkpoints/` beside it. Map:
[`README.md`](README.md). The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

The earlier draft of this charter specified a line plot of one
`Series`. This revision replaces that assignment. A spec writer who
reads this file follows the candlestick rules below.

**Your job.** Turn this charter into a specification for a
candlestick chart reached from a ticker. The series identity is
**chart**. Then **stop**. Do not write checkpoints. Do not implement.

The specification refuses a chart library, a line plot, a plot on an
arbitrary `DataFrame`, and a separate chart window. Those refusals
keep the series small enough to slice.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Read the ticker specification for the `history` action, the
   injected history seam, and the daily columns `Open`, `High`,
   `Low`, and `Close`. Read `DisplayInterval`, `hit_test`, and
   `presentation_style`. A presentation may occupy several rows and
   only some columns of each row. The deepest presentation at a cell
   wins the hit. Hovering reverses that presentation.
3. Record the locked decisions in §4. Resolve the open question in
   §5.
4. Write `spec.md` in this folder. A later checkpoint-manager
   conversation slices **chart 000**, then **chart 001**, under
   `checkpoints/` here, one checkpoint per conversation.
5. Stop. The human reviews the spec. Do not write those checkpoint
   files.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification.

Keep the spec to this one chart. A second plot type or a new window
is a defect in this document.

## 2. Predecessors

Ticker 001 is implemented. `history` calls
`ticker.history(period="1mo", interval="1d", timeout=15)` through one
injected seam and appends the returned `DataFrame`. Daily dates are
the frame index. The close column is `Close`. The ticker's only menu
item today is `history`. An ordinary click does not fetch.

This exploration adds no dependency. It does not add `plotext`. The
designer does not run uv. The chart is drawn with characters in the
existing history. The listener namespace is unchanged.

| Place | What goes there |
|---|---|
| `docs/design/implementation/chart/` | This charter, `spec.md`, `demo.md`, and `checkpoints/` |
| Project root | The existing `pbui` package and `tests/` |

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **The chart hangs from the ticker.** The menu action
   `candlestick` fetches the same one-month daily bars as `history`
   and appends one chart. It does not append the frame. The ticker
   stays. `history` still appends the frame and does not draw.
2. **The chart is one object full of candles.** Each day is a candle
   object inside the chart. The pointer lands on that candle. Its
   cells are green when the close is greater than or equal to the
   open, and red when the close is lower. Hovering reverses that
   candle and leaves the others alone.
3. **The picture is the prices.** Each candle draws a stem from low
   to high, a tick to the left for the open, and a tick to the right
   for the close. The date axis is part of the chart.
4. **A missing frame does not draw.** No rows, or a frame without
   those four columns, appends no chart. A fetch exception appends
   one `Error`.
5. **Old tests still pass.** `requires-python` stays `>=3.11`. No
   network in the automated tests.

## 4. Locked decisions (record these; do not reopen)

### 4.1 The action

`candlestick` is a second menu action on a `yfinance.Ticker`, beside
`history`. Opening or hovering the menu does not fetch. An ordinary
left click on the ticker still does not fetch. During composition, a
left click on the ticker still inserts the ticker chip.

Choosing `candlestick` calls the existing history seam once, with the
same production arguments as `history`. It does not add a second
Yahoo function. Tests supply a fixture frame or a failure and never
open a socket.

On success, build the chart from that frame and append the chart.
Set `_` to the chart. Leave the ticker in history. Do not append the
frame. On a raised exception, append one `Error`, append no chart,
and leave `_` unchanged. An empty frame, or a frame missing `Open`,
`High`, `Low`, `Close`, or a date index, appends one text row
`no prices`, appends no chart, and leaves `_` unchanged.

The chart is a snapshot of those rows. A later `history` call does
not change it.

### 4.2 The objects

The chart presentation retains the snapshot and covers the whole
drawn rectangle, including the date labels. Each candle is a nested
presentation and retains that day's date, open, high, low, and close.
Its intervals are the columns of that candle on every terminal line
the candle occupies. The hit test therefore returns the candle rather
than the chart. A click between candles returns the chart.

There is no candle presentation on a generic `DataFrame`. There is
no line-plot action on a `Series`.

### 4.3 The drawing

Draw the candles in date order, oldest at the left. §5 chooses how
many of the most recent days fit. Older days that do not fit are
named by one trailer, `… (N more days)`.

For each visible day, draw a vertical stem from the low to the high
and two ticks on that stem: the open on the left, the close on the
right. A day whose close is greater than or equal to its open is
green. A day whose close is lower is red. The whole candle uses that
one color. The axis, title, and date labels use the ordinary history
color. The title is `Ticker SYMBOL`, using the symbol the ticker
reports.

Hovering a candle reverses that candle's cells and does not reverse
the other candles or the axis. The documentation line names that
candle's date and whether it rose or fell. Hovering the chart names
the chart. The spec writes those sentences in the current
target-first form.

An ordinary left click on a candle, with nothing waiting, appends a
text detail of that day's date, open, high, low, and close. It does
not remove the chart and does not change `_`. During composition, a
left click on a candle inserts a chip of that candle. A left click on
the chart, off any candle, appends nothing. During composition it
inserts a chip of the chart. These objects are not accept targets.

### 4.4 What stays as it is

`history`, the frame preview, and `To JSON records` stay as they are.
No `plotext` picture, no separate window, no indicator, and no plot
of an arbitrary frame or series. The history does not gain a color
on every character. A candle is colored because the whole candle is
one presentation.

### 4.5 Tests

Headless tests build a fixture frame without Textual and without a
network. Cover at least: `candlestick` calls the history seam once
and does not append a frame; the chart retains one candle per
visible day, with that day's four prices; a rising day is green and
a falling day is red; the stem spans low to high and the ticks sit
on the open and the close; a hit on a candle's column returns that
candle, and a hit between candles returns the chart; an empty frame
and a frame without `Close` append `no prices` and leave `_`
unchanged; a seam exception appends one `Error`; success sets `_` to
the chart and leaves the ticker.

Chart 000 proves the objects, the drawing, and the hits. The menu
may stay unwired there.

Chart 001 adds the menu item, the green and red styles, the reverse
hover, the documentation sentences, one screen test, the hand check,
and `demo.md`. The screen test chooses `candlestick` on a fixture
ticker, reads a green candle and a red candle, and checks that
hovering the red one reverses only that candle.

The hand check needs the network. From a disposable directory, run
`uv run pbui`. Evaluate `yfinance.Ticker("AAPL")` and choose
`candlestick`. Read a chart with both green and red candles. Point at
one candle and read its date on the documentation line. Choose
`history` and confirm the frame still appears without a chart.
If Yahoo refuses, report that and do not weaken the automated gate.
`uv run pytest` is that gate. `uv run pbui` is only the hand check.

`demo.md` records the same path. It stores no prices.

### 4.6 Slice order

**chart 000** builds the chart and its candles from a fixture frame
without Textual.

**chart 001** puts `candlestick` on the ticker menu and adds the
styles, the screen test, the hand check, and the demo.

Do not add a slice for a line plot, a chart library, or another
window.

## 5. Open question (resolve this in the spec)

### 5.1 How many candles fit

Pick a chart width from 48 through 64 display cells, and a width for
one candle of either 2 or 3 of those cells. Show the most recent days
that fit. State the fixture that is wider than the chart and the
trailer it produces.

## 6. Authority

The ticker specification is the law for `yfinance.Ticker`, the
`history` action, and the injected history seam. The pandas
specification is the law for a `DataFrame`. The listener
specification is the law for presentations, hits, and hover.

Where this charter and the ticker specification disagree about a
second menu action on a ticker, this exploration wins. Where they
disagree about `history` or a frame, the ticker and pandas
specifications win.

## 7. Handoff reminder

The series identity is **chart**. Checkpoint 000 is spoken **chart
000** and filed as `checkpoints/000-slug.md`. Checkpoint 001 is
spoken **chart 001**. Numbers are three digits, start at 000, and
are never renumbered. The slug is lowercase words separated by
hyphens. The checkpoint manager writes one checkpoint, then stops.
Code and tests go at the project root
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`, not in
this folder.

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. The first identity is **chart 000**. The
second, in a later conversation, is **chart 001**.

After the spec is accepted, `spec.md` is the design authority for
those conversations. This charter is the assignment for the spec
writer. Later conversations do not read it.
