# Try the pandas inspector

This is a hands-on tour of the completed pandas exploration. A DataFrame or
Series stays a Python object in pbui history. Clicking a frame shows a bounded
snapshot; clicking a column header takes a Series, and clicking a row label
takes a one-row DataFrame. The same objects can become Python input chips.

## Start

From the project root, launch pbui in an interactive terminal:

```console
cd /home/dharmatech/journal/2026-09-21-pbui-python-terminal
uv run pbui
```

Type the Python lines below at **pbui's bottom input line**, pressing Enter
after each line. Keep one session open, and leave the input line empty before
an ordinary history click. Scroll back when an older row moves off screen.
Use Ctrl-C to exit when finished. This tour makes only in-memory pandas
objects; it writes no files and uses no network requests or destructive
listener commands. Widen the terminal if a documentation sentence is cut off.

## 1. Present a frame with duplicate column names

Enter these lines separately:

```python
import pandas
frame = pandas.DataFrame([[1, pandas.NA], [3, 4]], columns=["same", "same"], index=["row0", "row1"])
frame
```

The import and assignment add input rows but no value result. Evaluating
`frame` adds `DataFrame 2×2`. That row retains the frame object; it does not
expand the whole table. Hover over it to see `DATAFRAME • Left: show frame
preview • Right: no menu` on the documentation line.

## 2. Open the captured table

With the input empty, left-click `DataFrame 2×2`. The summary stays in
history, followed by a table headed `index  same  same`. Its `row0` line shows
`1` and `NA`; its `row1` line shows `3` and `4`. The two `same` headers have
separate hits even though their text is equal.

Hover over the second `same` header to read `PANDAS COLUMN • Left: take column
• Right: no menu`. Hover over `row0` to read `PANDAS ROW • Left: take row •
Right: no menu`. Click a cell value such as `NA`, or the spaces beside a
header: nothing new appears. Right-click a header or the frame summary; it
has no pandas menu.

## 3. Take the second column and list it

With the input empty, left-click the **second** `same` header. A new Series
summary appears. Enter `column = _` to keep that extracted Series in your
Python session. With the input empty again, left-click its Series summary.
The new literal rows are:

```text
[0]  NA
[1]  4
```

Clicking the Series listed its values; it did not replace the summary or
change `_`. The value rows themselves have no click action.

## 4. Use a header as a Python chip

Type `id(` but do not press Enter. Left-click the **same second header** in
the earlier preview. This click inserts a chip into the unfinished Python
expression, instead of extracting another Series. Type `) == id(column)`
and press Enter. The result is `bool True`: the chip passed the cached Series
object taken in step 3, even though its visible label was just `same`.

With the input empty again, left-click that header once more. It appends
another Series summary for the same cached copy. A preview header always
refers to the snapshot that created it.

## 5. Take a row, then change the source frame

Left-click `row0` in the first preview. A new `DataFrame 1×2` summary appears
for that one-row copy. Its `_` value is the extracted DataFrame. The cell
values and labels in the first preview remain as they were.

Now enter:

```python
frame.iloc[0, 1] = 99
```

Scroll back to the original `DataFrame 2×2` summary and click it again. A
second preview appears with `99` where the first preview still shows `NA`.
The original summary retains the live source frame, while each preview keeps
its own captured data. Clicking the old second header still takes the old
Series with `NA`; clicking the new second header takes a Series with `99`.

## 6. See the preview and list limits

Enter these lines separately:

```python
big = pandas.DataFrame({f"c{c}": range(13) for c in range(7)})
big
```

The summary reads `DataFrame 13×7`. Click it. The preview shows the first 12
data rows and first 6 columns, then literal `… (1 more columns)` and
`… (1 more rows)` lines. Those trailers do not have click actions.

Enter these lines separately:

```python
long_series = pandas.Series(range(13), name="count")
long_series
```

The summary reads `Series 13 count int64`. Click it to get `[0]  0` through
`[11]  11`, followed by `… (1 more values)`.

## 7. Compare a MultiIndex preview and an empty frame

Enter these lines separately:

```python
multi = pandas.DataFrame([[10, 20]], columns=pandas.MultiIndex.from_tuples([("a", 1), ("a", 2)]), index=["row"])
multi
```

Click its `DataFrame 1×2` summary. The table shows the tuple column labels
as text. Because one axis is a MultiIndex, neither those headers nor `row`
is an extraction hit; clicking their displayed text does nothing.

Finally, enter `pandas.DataFrame()` and click its `DataFrame 0×0` summary.
It adds one literal row: `empty DataFrame`.

The [specification](spec.md) defines the full behavior. This tour uses only
objects created during this session.
