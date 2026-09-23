# Try SymPy expressions

This is a hands-on tour of the completed SymPy exploration. A SymPy
expression stays a live Python object in pbui history. Its row reads as
algebra, a click shows its pretty form, and its action menu can simplify,
expand, or factor it.

## Start

From the project root, launch pbui:

```console
cd /home/dharmatech/journal/2026-09-21-pbui-python-terminal
uv run pbui
```

Type all examples below **inside pbui** and keep the same session open. Each
line is Python, so it needs no `:` prefix. This tour only evaluates
expressions; it does not need `rm` or `kill`. Use Ctrl-C to exit when finished.

Start by entering these two lines separately:

```python
import sympy
x = sympy.Symbol("x")
```

Neither line adds a result row. The listener uses SymPy to present values,
but the `sympy` name becomes available to your Python input only after your
own `import sympy`.

## 1. Read a symbolic history row

Enter:

```python
sympy.sqrt(8)
```

The new history row should read `2⋅√2`, without a `Pow` or `Expr` prefix.
SymPy has simplified `sqrt(8)` to `2*sqrt(2)` before pbui presents it. The
row still carries that expression object, rather than its displayed text.

## 2. Open the taller pretty form

Enter:

```python
1/(x + 1)
```

Its one-line history row should read `1/(x + 1)`. With the input line empty,
left-click that row. The detail appears as three separate history rows,
roughly like this fraction:

```text
  1
─────
x + 1
```

The original one-line expression row remains. Clicking it for detail does
not change `_`. Other tall forms, such as `(x + 1)**2`, use the same
one-line-row and multiline-detail pattern.

## 3. Expand a retained expression

Enter:

```python
(x + 1)**2
```

Hover over its history row and press Ctrl-O, or right-click it, to open the
action menu. Choose `expand`. A **new** expression row should show the
expanded polynomial `x**2 + 2*x + 1`; the earlier `(x + 1)**2` row remains.
The menu also contains `simplify` and `factor`, in that order around
`expand`. The exact algebraic glyphs and spacing may vary with the form
being printed.

## 4. Use the menu result as a Python object

Do this immediately after `expand`, while `_` still refers to its new result.
Type `id(`, then left-click the **expanded result row**. A chip appears in
the input. Type `) == id(_)` and press Enter. Before Enter, the input should
look roughly like:

```text
id(⟨x**2 + 2*x + 1⟩) == id(_)
```

The result should be `bool True`. The chip's label is display only; Python
received the exact expression object stored in the menu result row. Entering
this comparison then changes `_` to the resulting Python `True` value.

## 5. Try factor and simplify

Enter `x**2 - 1`, open that row's menu, and choose `factor`. A new row should
show `(x - 1)⋅(x + 1)`, with the source row still present.

Then enter:

```python
sympy.sin(x)**2 + sympy.cos(x)**2
```

Open its menu and choose `simplify`. The new row should read `1`. That is a
SymPy expression result, so it has the SymPy menu too. Each menu action
works on the clicked row's stored object and appends its result.

## 6. Compare ordinary values

Enter `42`. Its row should read `int 42`, and it has no SymPy action menu.
Then enter `sympy.Integer(42)`. Its row should read `42` without the class
prefix, and it has the three SymPy actions. The two rows look different
because only the SymPy integer is a `sympy.Expr`.

For another comparison, enter `sympy.Matrix([[1, 2]])`. It keeps a generic
Python `Value` row and no SymPy menu. Left-clicking a generic value shows its
single-row `TYPE: REPR` detail, while a SymPy expression gets the pretty
detail demonstrated above.

The [specification](spec.md) defines the full behavior; this tour is for
trying the completed interaction by hand.
