# Charter — a ticker and its price history

**Status.** Handoff from the high-level discussion into a **design
conversation**. Not a checkpoint. Not an implementer assignment.
This file lives in `docs/design/implementation/ticker/`. The
specification will live beside it as [`spec.md`](spec.md).
Checkpoint files will live in `checkpoints/` beside it. Map:
[`README.md`](README.md). The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

**Your job.** Turn this charter into a specification for presenting
a `yfinance` ticker and appending its daily price history as the
`DataFrame` that library returns. The series identity is **ticker**.
Then **stop**. Do not write checkpoints. Do not implement.

The specification refuses indicators, charts, and any second Yahoo
object. Those refusals keep the series small enough to slice.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Read the pandas specification for how a `DataFrame` is summarized
   and previewed. Read the records specification for the fact that
   `To JSON records` omits the frame index. Read the pinned
   `yfinance` `Ticker` constructor and `Ticker.history`. Name the
   symbol attribute and the close-price column from that version.
3. Record the locked decisions in §4. There is no open-question
   section.
4. Write `spec.md` in this folder. A later checkpoint-manager
   conversation slices **ticker 000**, then **ticker 001**, under
   `checkpoints/` here, one checkpoint per conversation.
5. Stop. The human reviews the spec. Do not write those checkpoint
   files.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification, including
the pinned `yfinance` version and the close-column name.

Keep the spec to one ticker and one history action. An indicator, a
plot, or `yfinance.download` is a defect in this document.

## 2. Predecessors

Pandas and records are implemented. A `DataFrame` remains the object
pandas returned, and its preview and `To JSON records` action already
exist. HTTP's injected fetch is the pattern for a test that never
opens a socket.

This exploration adds `yfinance` with `uv add`, so the version and
its transitive dependencies are pinned in `uv.lock`. Do not upgrade
it inside this series and do not install it from a git URL. The
designer does not run uv.

Startup may import `yfinance` in the application. The listener
namespace still starts as `__name__` only. The user binds the
library with `import yfinance`. There is no API key and no new colon
command.

| Place | What goes there |
|---|---|
| `docs/design/implementation/ticker/` | This charter, `spec.md`, `demo.md`, and `checkpoints/` |
| Project root | The existing `pbui` package, `tests/`, `pyproject.toml`, and `uv.lock` |

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **The ticker is the library object.** Evaluating
   `yfinance.Ticker("AAPL")` retains that object and shows
   `Ticker AAPL`. A chip holds that same object.
2. **History is a frame.** The menu action `history` appends the
   `DataFrame` returned for one month of daily bars. The ticker stays
   in history. The pandas preview can open the frame.
3. **A typed call is the same kind of result.**
   `ticker.history(period="1mo")` presents the `DataFrame` that call
   returns, through the existing pandas rules.
4. **Tests do not touch Yahoo.** A fixture frame proves the action.
   One hand check loads AAPL. It does not require a price.
5. **Old tests still pass.** `requires-python` stays `>=3.11`.

## 4. Locked decisions (record these; do not reopen)

### 4.1 The ticker

Register `yfinance.Ticker` and no other `yfinance` class. The summary
is `Ticker SYMBOL`. `SYMBOL` is the symbol text that object reports.
The spec names the attribute from the pinned version. The existing
value path escapes the line and caps it at 120 display cells.

The summary retains the ticker by identity. An ordinary left click
does not fetch. It keeps the generic value detail. The right clause
is `menu`. The target reads `TICKER SYMBOL`, and the left clause is
`show`. During composition, a left click inserts a chip of that
ticker and does not fetch.

### 4.2 The history action

The only menu action is `history`. It calls that ticker's history
for `period="1mo"` and `interval="1d"`. It passes `timeout=15` when
the pinned method accepts `timeout`. It passes `progress=False` when
the pinned method accepts `progress`. It does not write a progress
line to standard output. It does not prompt for a period.

The appended value is the `DataFrame` the call returns, not a copy
in a listener-made table type. The pandas summary and preview apply.
Success sets `_` to that frame. The ticker remains. An empty frame
is a successful empty `DataFrame`, not an error. A raised exception
appends one `Error`, appends no frame, and leaves `_` unchanged.

The menu goes through one injected seam. Tests supply a fixture
frame or a failure and never open a socket. The production seam
calls the ticker. A `DataFrame` the user gets by calling `history`
themselves is presented because it is a `DataFrame`, not because the
seam saw it.

The dates are the frame's index. `To JSON records` therefore omits
them. This series does not change that conversion. A user who wants
the dates as a column evaluates `reset_index()` in Python. The spec
says this in the demo.

The spec records the close-price column name from the pinned
library's daily history. The fixture and the hand check use that
name. They do not require a numeric price.

### 4.3 What stays as it is

There is no action for quote, info, dividends, splits, financials,
options, or news. There is no `yfinance.download`, no multi-ticker
object, no indicator, and no chart. Sort and filter stay ordinary
pandas expressions. Their results present through pandas.

### 4.4 Tests

Headless tests build a ticker stand-in and a fixture frame without
Textual and without a network. Cover at least: a fresh namespace has
no `yfinance`; a ticker summary retains that object and reads
`Ticker AAPL`; `history` appends the fixture frame, sets `_` to it,
and leaves the ticker in place; a second `history` appends another
frame; a seam failure appends one `Error` and leaves `_` unchanged;
an empty fixture appends `DataFrame 0×C` for that fixture's column
count; the ordinary click does not call the seam.

Ticker 000 proves that behavior. The menu may stay unwired there.

Ticker 001 adds the menu, the documentation sentence, one screen
test, the hand check, and `demo.md`. The screen test chooses
`history` on a fixture ticker and reads the frame summary.

The hand check needs the network. From a disposable directory, run
`uv run pbui`. Import `yfinance`, evaluate `yfinance.Ticker("AAPL")`,
and choose `history`. Read a `DataFrame` summary with more than one
row. Open the preview and find the close column named by the spec.
Do not require a price or a date. If Yahoo refuses the request,
report that and do not weaken the automated gate. `uv run pytest` is
that gate. `uv run pbui` is only the hand check.

`demo.md` records the same path and says that `To JSON records`
omits the date index unless the user resets it first. It stores no
prices.

### 4.5 Slice order

**ticker 000** registers the ticker class and proves the summary and
the injected history action without Textual.

**ticker 001** wires the menu and the documentation sentence, and
adds the screen test, the hand check, and the demo.

Do not add a slice for an indicator or a chart.

## 5. Authority

The pandas specification is the law for a `DataFrame` summary,
preview, and extraction. The records specification is the law for
`To JSON records`, including omission of the index. The popup
specification is the law for the menu.

Where this charter and an earlier specification disagree about the
row or menu of a `yfinance.Ticker`, this exploration wins. Where
they disagree about a `DataFrame`, a JSON record, or a generic
value, the earlier specification wins.

## 6. Handoff reminder

The series identity is **ticker**. Checkpoint 000 is spoken
**ticker 000** and filed as `checkpoints/000-slug.md`. Checkpoint
001 is spoken **ticker 001**. Numbers are three digits, start at
000, and are never renumbered. The slug is lowercase words separated
by hyphens. The checkpoint manager writes one checkpoint, then
stops. Code and tests go at the project root
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`, not in
this folder.

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. The first identity is **ticker 000**.
The second, in a later conversation, is **ticker 001**.

After the spec is accepted, `spec.md` is the design authority for
those conversations. This charter is the assignment for the spec
writer. Later conversations do not read it.
