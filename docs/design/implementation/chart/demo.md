# Try the ticker candlestick chart

This is a hands-on tour of the retained ticker menu, its character-drawn chart,
and the existing pandas history path. Keep one listener session open throughout.

## Start

From the project root, run:

```console
cd /home/dharmatech/journal/2026-09-21-pbui-python-terminal
uv run pbui
```

Type the Python lines below at the listener's bottom input prompt and press
Enter after each. Use the mouse in the history above the prompt. Press Ctrl-C
to exit. Choosing either ticker menu action makes a live Yahoo request; this
tour does not save prices or modify files.

## Steps

1. Enter `import yfinance`, then `yfinance.Ticker("AAPL")`. The listener keeps a
   `Ticker AAPL` Value in its history. Point at it to see its documentation line.

2. Right-click that retained ticker and choose `candlestick` from the menu,
   below `history`. A successful request adds an action-input row followed by a
   60-cell chart: a title, 12 rows of candles, an axis, and endpoint dates. The
   green candles rose or stayed flat; red candles fell. If Yahoo returns no
   usable prices, the listener shows `no prices` instead. If the request raises,
   it shows one Error row. You can still try `history` in step 4.

3. When a chart appears, point at a three-cell candle block. The bottom
   documentation line names that candle's captured date and says whether it
   rose or fell. Left-click the candle to append its captured Open, High, Low,
   and Close detail. Point between two candles to see the chart documentation;
   the gap belongs to the chart.

4. Find the retained `Ticker AAPL` Value, right-click it, and choose `history`.
   This makes another live Yahoo request and appends the returned pandas frame
   through the usual Value path, without drawing another chart. Left-click the
   frame to open its existing preview.
