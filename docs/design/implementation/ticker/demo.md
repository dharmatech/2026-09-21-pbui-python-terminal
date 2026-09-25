# Try ticker history

This hands-on tour creates a retained `yfinance.Ticker`, requests its daily
price history, and explores the returned pandas frame in the listener.

## Start

From the project root, run:

```console
uv run pbui
```

Type the following Python expressions in the listener's bottom input row and
press Enter after each. Keep one session for the whole tour. Press Ctrl-D on
an empty input row to quit. Choosing `history` makes a live request to Yahoo;
the result depends on Yahoo's availability and does not need a particular
price or date.

## Steps

1. Type `import yfinance`. The import adds the module to this listener's Python
   namespace and prints no ticker row.
2. Type `yfinance.Ticker("AAPL")`. A `Ticker AAPL` Value appears in history.
   Hovering it shows `TICKER AAPL • Left: show • Right: menu` and does not
   request prices.
3. Right-click the `Ticker AAPL` row, or hover it and press Ctrl-O. Choose
   `history`. The menu closes, an action row appears, and the request appends a
   `DataFrame R×C` summary when Yahoo returns a frame. If the request fails,
   the listener shows one Error instead.
4. Left-click the DataFrame summary to open its pandas preview. Find `Close`
   among the columns; the date labels appear in the frame index. At a narrow
   terminal width, the preview may wrap its columns or require scrolling.
5. To make dates part of JSON records, type `_.reset_index()` while `_` still
   refers to the history frame. This appends a new DataFrame with dates as a
   column. Right-click that new frame and choose `To JSON records`. Applying
   `To JSON records` directly to the original history frame omits its date
   index, so `reset_index()` is the step that includes dates in each record.
