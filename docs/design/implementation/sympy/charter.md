# Charter — SymPy expressions

**Status.** Handoff from the high-level discussion into a **design
conversation**. Not a checkpoint. Not an implementer assignment.
This file lives in `docs/design/implementation/sympy/`. The
specification will live beside it as [`spec.md`](spec.md).
Checkpoint files will live in `checkpoints/` beside it. Map:
[`README.md`](README.md). The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

**Your job.** Turn this charter into a specification that registers
SymPy expressions on the existing value hook: a pretty history row,
a taller `show`, and three menu operations. Then **stop**. Do not
write checkpoints. Do not implement.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Read the REPL specification at [`../repl/spec.md`](../repl/spec.md)
   for `Value`, the class registry, `show`, and translator results.
   Read the chips specification at [`../chips/spec.md`](../chips/spec.md)
   only to preserve insertion. Do not copy those documents. Restate
   every rule an implementer must obey. The sentence this spec
   supersedes is the generic `Value` printer and generic `show` for
   objects whose class is under `sympy.Expr`.
3. Record the locked decisions in §4. Resolve the open questions in
   §5.
4. Write `spec.md` in this folder. A later checkpoint-manager
   conversation slices **sympy 000**, `001`, … under `checkpoints/`
   here, one checkpoint per conversation.
5. Stop. The human reviews the spec. Do not write those checkpoint
   files.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification.

Keep the spec **small enough to slice**. Pandas, matrices, and a
new input syntax are defects in this document.

## 2. Predecessors

Listener, listings, the REPL, and chips are implemented. The value
registry maps a class to a printer and a list of translators.
Lookup walks the instance's method-resolution order. A translator
calls a function with the stored object and presents the result.
The original presentation stays. A click while composing Python
inserts that stored object.

This exploration does not create a new project. Implementers add
SymPy with `uv add sympy` and keep using `uv sync` and
`uv run pytest`. The designer does not run those commands.

| Place | What goes there |
|---|---|
| `docs/design/implementation/sympy/` | This charter, `spec.md`, and `checkpoints/` |
| Project root | The existing `pbui` package, `tests/`, and `pyproject.toml` |

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **An expression is not a generic `repr`.** After `import sympy`
   and `sympy.sqrt(8)`, the history row is a one-line symbolic form
   of that `Pow`, not `Pow` plus Python's `repr`.
2. **The menu computes a new expression.** `simplify`, `expand`,
   and `factor` each append a new `Value` whose object is the
   SymPy result. The row that was clicked remains, unchanged.
3. **The result is the object.** A later chip or a later call such
   as `sympy.factor` on that object receives the expression, not
   the pretty text.
4. **Other values stay generic.** A Python `int`, a SymPy matrix,
   and an unregistered object still use the generic `Value` row
   and have no SymPy menu.
5. **Old tests still pass**, plus headless SymPy cases and one
   hand check. The listener does not import SymPy into the user's
   namespace for them.

## 4. Locked decisions (record these; do not reopen)

### 4.1 What is registered

At listener startup, import SymPy and register `sympy.Expr`. Do not
register `sympy.Basic`, `sympy.Matrix`, or `sympy.MatrixBase`.
Matrices and other non-`Expr` SymPy objects stay on the generic
printer. A Python `int` is not a `sympy.Integer`.

Do not bind the name `sympy` in the listener namespace. The user
imports it with ordinary Python, as they do today.

The three translators, in this order, are exactly:

| Label | Operation |
|---|---|
| `simplify` | `sympy.simplify` |
| `expand` | `sympy.expand` |
| `factor` | `sympy.factor` |

Each function receives the stored expression and returns a new
object. Present that object through the same registry, so the new
row is pretty when the result is an `Expr`. `None` is presented
when a translator returns it, because that is the existing
translator rule. If the operation raises, append one `Error`, leave
`_` unchanged, and keep the original presentation. That is the
existing translator failure rule. Do not catch a failure and
present the original expression as if it were a new result.

### 4.2 How an expression is drawn

The history row is one logical row. Prefer SymPy's Unicode pretty
form when that form is a single line. When the pretty form is
taller than one line, use SymPy's one-line string form instead of
escaping the newlines into the row. Truncate to the existing
`Value` row budget. A short expression such as `sqrt(8)` or `x`
must be recognizable as symbolic on that row. Do not prefix the
row with the class name `Pow`, `Add`, or `Expr`.

`show` on an `Expr` appends the pretty form as its own rows, one
history row per pretty line, not the generic bounded `repr`. Cap
the number of lines and the width of each line. The spec chooses
both caps. Lines beyond the cap are omitted, and the spec says how
the omission is marked. Control characters are escaped. The
original expression presentation stays.

A generic `Value` still uses the generic `show`. Registering `Expr`
must not change `show` for other objects.

### 4.3 What the screen already does

The menu for a `Value` with translators already opens with Ctrl-O
or mouse button 3, and choosing an item calls the translator. The
documentation line already says that this menu exists. Do not
invent a second menu path or a new documentation sentence unless
the existing sentence is false for an `Expr`. Left click remains
`show`. Chips remain chips: the inserted object is the expression.

### 4.4 Tests

Headless tests import SymPy. They do not need Textual. Cover at
least:

- `sympy.sqrt(8)` displays as a symbolic one-line form;
- `expand` of `(x + 1)**2` presents an expression equal to
  `x**2 + 2*x + 1`, and the source row's object is still the power;
- `factor` of `x**2 - 1` presents an expression equal to
  `(x - 1)*(x + 1)`;
- a Python `int` and a `sympy.Matrix` do not gain these menu items;
- the user's namespace does not contain `sympy` until their own
  `import`.

The hand check, from a disposable directory, is: import SymPy,
enter `sympy.sqrt(8)`, read the symbolic row, run one of the three
menu operations, and insert the resulting row into a later
expression with a click. `uv run pytest` is the automated gate.
`uv run pbui` is only that hand check.

### 4.5 Slice order

One slice is enough unless the spec cannot state the printer and
the three operations in a single checkpoint. Headless tests come
before the hand check. Do not add a slice for a feature in §4.6.

### 4.6 Out of this spec

- Pandas and any table of cells.
- SymPy matrices, solvers, plots, and LaTeX.
- New commands, colon changes, or a change to chip splicing.
- Preloading `sympy` into the namespace.
- A second pretty-printer framework beside the existing registry.

## 5. Open questions (resolve these in the spec)

### 5.1 One-line choice

Name the SymPy functions used for the one-line row and for the case
where Unicode pretty output is taller than one line. State the
row-width budget you are reusing.

### 5.2 Show caps

Choose the maximum number of pretty lines and the maximum width of
each. A one-line expression's `show` is that one line, not a
generic `repr`.

### 5.3 Equality in tests

State that the tests compare SymPy expressions with SymPy equality,
not with `repr` or with the pretty text.

## 6. Authority

This charter is the design for this exploration. The listener,
listings, REPL, and chips specifications remain the law for
everything it does not change.

A presentation type can own a printer and a small set of
operations. This exploration uses that for algebraic expressions.
A dataframe is the following exploration, not this one.

## 7. Handoff reminder

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. Identity is **sympy 000**, then
**sympy 001** only if the spec splits the slice.
