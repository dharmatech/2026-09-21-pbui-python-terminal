# Try Python input chips

This is a short, hands-on tour of the completed chips exploration. In pbui,
typed listener commands start with `:`; other input is Python. A left click on
a history object normally shows it when the prompt is empty. While you are
composing Python, the click inserts that same stored object into your input as
an atomic chip.

## Start

From the project root, launch the terminal application:

```console
cd /home/dharmatech/journal/2026-09-21-pbui-python-terminal
uv run pbui
```

All commands and Python examples below are typed **inside pbui**. They only
inspect files and evaluate Python; they do not need `rm` or `kill`. The steps
build on one another, so keep the same session open. Use Ctrl-C to exit
when finished.

## 1. An empty-prompt click still shows

Type `:ls` and press Enter. With the input line empty, left-click a file row
in the listing. Its `show` detail should appear in history. No Python chip is
inserted. This is the listener's ordinary default click.

You can also type `:show`, press Enter, and then click a file row. The click
supplies the file to the waiting command; it does not insert a Python chip.
Cancel the wait with Ctrl-G or Escape if you do not want to select a file.

## 2. Put an earlier number into an expression

Type `1 + 1` and press Enter. History should gain an `int 2` Value row. Now
type `10 + `, leaving the cursor after the space, and left-click that `int 2`
row. The editor should look like this:

```text
10 + ⟨int 2⟩
```

Press Enter. The result should be `int 12`. The brackets and label show where
the object sits in the input; they are not Python source.

To try insertion in the middle of a line, type `pow(, 3)` and press Left four
times, placing the cursor just after `(`. Click the `int 2` row. The editor
should show `pow(⟨int 2⟩, 3)`; Enter should produce `int 8`.

## 3. Check that the original object is used

Type `v = object()` and press Enter, then type `v` and press Enter to display
its Value row. It will look roughly like `object <object object at 0x…>`; the
address varies.

Type `id(`, click that Value row, then type `) == id(v)` and press Enter. The
complete input will visually resemble:

```text
id(⟨object <object object at 0x…>⟩) == id(v)
```

The result should be `bool True`. The row's printed representation is not
usable Python source, so this demonstrates that the chip passes the original
stored object to `id`.

## 4. Edit a chip as one unit

Type `10 + ` and click the earlier `int 2` row again. With the cursor just
after its chip, press Backspace once. The entire `⟨int 2⟩` should disappear,
leaving `10 + `. Type `3` and press Enter; the result should be `int 13`.

You can also put the cursor before a chip with one Left press and cross it
again with one Right press. The cursor never enters the label. Delete while
just before the chip removes the whole chip, too.

## 5. See a refused insertion

Type `print("ab")`. From the end of that line, press Left three times. The
cursor is now between `a` and `b` (`print("a|b")`, where `|` only marks the
cursor for this explanation). Hover over a Value row. The documentation line
should say:

```text
This value would be literal text here; move the cursor outside the string or comment.
```

Left-clicking the row should leave the editor unchanged: no chip is inserted
and no default `show` action runs. Press Escape to clear the line. With
the cursor at a valid expression position, hovering the row instead shows
`Click to insert this value into the expression.` on the documentation line.

## 6. Insert during a Python continuation

Type `if True:` and press Enter. The prompt changes to `...> `. Type four
spaces followed by `10 + `, then click the earlier `int 2` row. Press Enter
to submit the body, and press Enter once more on the blank continuation line
to finish the block. The result should be `int 12`. The pending line is kept
as Python pieces; only the current line appears in the one-row editor.

To try cancellation separately, start another `if True:` continuation and
press Ctrl-G or Escape. It should return to the ordinary prompt without
running that incomplete block.

## 7. Use a menu without losing your expression

Type `10 + ` and leave the cursor at the end. Hover over a file row from
`:ls`, press Ctrl-O (or right-click), and choose `show` from its action menu.
The file detail appears, while the unfinished `10 + ` and its cursor remain
in the editor. You can click the `int 2` row and press Enter to get `int 12`.

For a fuller version, begin `10 + `, click `int 2`, then open the listing
**header's** menu and choose `narrow`. Type a substring such as `py` and press
Enter. The listing may change, but the Python input, chip, and cursor return
exactly as they were. Press Enter to evaluate the restored expression; it
should still produce `int 12`. Ctrl-G or Escape while `narrow` is waiting
also restores the Python input.

The [specification](spec.md) defines the complete behavior; this tour is for
trying the interaction by hand.
