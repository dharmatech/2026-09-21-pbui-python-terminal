# Try the transcript

This is a hands-on tour of the completed transcript exploration. Submitted
Python, colon commands, and menu actions now leave marked input rows in pbui
history before their results. Those rows retain the original input or action,
so you can bring an input back to the editor or run an action again.

## Start

From the project root, launch pbui:

```console
cd /home/dharmatech/journal/2026-09-21-pbui-python-terminal
uv run pbui
```

Type the examples below **inside pbui** and keep one session open. Python
input has no prefix; listener commands start with `:`. This tour uses only
Python and read-only file commands. Use Ctrl-C to exit when finished.

## 1. See a form above its result

Enter `1 + 2 + 3`. History should show these two rows in this order:

```text
› 1 + 2 + 3
int 6
```

The `› ` marker belongs to the history drawing, not the Python source. Even
an input with no result, such as `import sympy`, gets a marked row when it
finishes. An incomplete Python continuation gets no row until the whole form
is complete.

With the editor empty, left-click `› 1 + 2 + 3`. The same text should appear
in the editor without running it or adding history. Press Backspace once,
type `4`, and press Enter. A **new** `› 1 + 2 + 4` row should appear above
`int 7`; the older form and `int 6` remain. Enter, not the click, ran the
edited form.

You can also hover over either form and press Ctrl-O, or right-click it. Its
menu has one item, `yank`, which loads it into the editor. Press Escape to
clear any input you do not want to submit.

## 2. Bring back a colon command

Enter `:ls`. Its marked `› :ls` row appears before the directory listing.
At an empty editor, click `› :ls`. The editor should contain `:ls`, and no
new listing appears yet. Press Enter to run it again; a second command row
appears before the second listing.

For an object argument, enter `:show` with no argument. It waits for a
presentation. Click a file row, such as `README.md`, in a listing. The
completed command is then recorded with a command chip, roughly:

```text
› :show ⟨File: README.md⟩
```

Click that command row at an empty editor. It restores `:show` and the same
file chip, not path text reconstructed from the label. Enter runs `show` on
that stored file object. The chip label may differ with the file you chose.

## 3. Compare source insertion with object insertion

Enter `2` to create a `› 2` input row followed by an `int 2` result row.
Type `10 + ` and leave the cursor at the end. Click the **marked input row**.
The saved source text is inserted, so the editor reads `10 + 2`. Press Enter
to get `int 12`.

Now type `10 + ` again and click the **result row** `int 2`. This time the
editor shows `10 + ⟨int 2⟩`: that is an object chip from the earlier chips
exploration. It also evaluates to `int 12`, but the brackets and label are
only the chip's drawing. A click on a transcript input inserts its saved
pieces; a click on a result inserts the retained object.

The fixed documentation line makes that distinction clear. With an empty
editor, hover over the marked form to see:

```text
Click to load this Python form into the editor; Enter runs it.
```

While composing Python, the same row says:

```text
Click to insert this input at the cursor.
```

The sentence updates when the editor mode changes, even if the pointer stays
still.

While composing Python, an input row's `yank` menu item inserts its pieces at
the cursor too. It keeps the text already being edited rather than replacing
the whole line. An input with saved chips brings those same objects back.

## 4. Run a saved menu action again

If you have not already done so, enter these lines separately:

```python
import sympy
x = sympy.Symbol("x")
sympy.sin(x)**2 + sympy.cos(x)**2
```

The last line displays a SymPy expression. Hover over that **result row** and
press Ctrl-O, or right-click it, then choose `simplify`. History gains a row
beginning `› simplify — ` above a new result `1`. The original expression
row remains. The action row records the chosen operation and its original
target object; it is not a Python statement.

With an empty editor, click the `› simplify — …` action row. It immediately
runs `simplify` again on that saved object and adds another action row and
result. To find the same operation through its menu, hover over the action
row, press Ctrl-O or right-click, and choose its only item, `run again`.
Unlike a Python form or colon command, an action click runs immediately and
does not load the editor. During Python composition, a left click on the
action row instead inserts a chip of its target object at a valid expression
position.

## 5. Look at a multiline form

Enter `for i in range(2):`, press Enter, then enter four spaces followed by
`print(i)` and press Enter. Press Enter once more on the blank continuation
line to finish the form. History should contain **one** saved Python input
presentation, drawn across multiple marked rows, before its `0` and `1`
output rows. Click any of the marked form rows at an empty editor: the whole
form comes back, not just the line you clicked. Ctrl-G or Escape discards this
loaded continuation without running it.

Long source lines split into marked history rows at 120 display cells. A very
tall form shows at most 11 content rows and a twelfth `› … (N more input
rows)` marker. Clicking that marker still restores the entire saved form.
Long colon-command and menu-action drawings instead stay on one logical row
and end with `…`; their saved text, chips, and target objects remain complete.

The [specification](spec.md) defines the full behavior; this tour is for
trying the completed interaction by hand.
