# sympy 000 — Expression presentations

**Status.** Ready to implement.

## Goal

Present `sympy.Expr` results as algebra in the existing listener: a symbolic
one-line history row, bounded multiline detail on a default click, and the
`simplify`, `expand`, and `factor` action-menu operations. Complete the
headless tests, the full automated gate, and one live terminal hand check in
this single slice. Stop after reporting the result; do not begin pandas or a
second SymPy slice.

## Identity, authority, and starting point

- Identity is `(sympy, 000)`, spoken **sympy 000**.
- The human-reviewed [`../spec.md`](../spec.md) is the design authority. Follow
  it where this checkpoint is silent. The charter is not an implementation
  input.
- Listener 000–005, listings 000–008, repl 000–001, and chips 000–001 are
  implemented. Preserve their behavior outside the `sympy.Expr` extension.
- Work in the existing project at
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application
  code, dependency metadata, and tests stay at the project root, never under
  `docs/`.
- Keep the evaluator and registration importable without Textual; only
  `pbui.terminal` imports Textual.

## File and feature boundary

Add SymPy as a project dependency through uv, updating `pyproject.toml` and
`uv.lock`. Register the production class in the existing headless listener
startup path, using the Python-class `Value` registry in `src/pbui/repl.py` and
`src/pbui/commands.py`. A focused plain-Python SymPy helper module under
`src/pbui/` is permitted if it keeps registration, row printing, and detail
formatting clear. Edit `src/pbui/terminal.py` only if the existing menu and
click routes cannot already expose the registered behavior. Add focused
headless tests under `tests/` and adjust existing tests only for a concrete
change required by this specification.

Do not add a presentation type or a second printer registry. Do not register
`sympy.Basic`, `sympy.Matrix`, or `sympy.MatrixBase`. Do not preload names in
the user's Python namespace, alter colon commands or accept types, change chip
splicing, or add another menu route. Pandas, a matrix presentation, solvers,
plots, LaTeX, and new input syntax are outside this checkpoint.

## Production registration and retained objects

At each listener's startup, import SymPy for application registration and
register **`sympy.Expr` only** with the existing class registry. Keep the
listener's Python namespace initially exactly `{"__name__": "__pbui__"}`;
only a user's ordinary `import sympy` binds that name there. Preserve lookup
through `type(value).__mro__`, taking the first registered class without
merging registrations. Python `int`, SymPy matrices, and other unregistered
objects keep generic `Value` printing, detail, and empty SymPy menus.

Register these translators in this exact order:

| Label | Function called with the retained object |
|---|---|
| `simplify` | `sympy.simplify` |
| `expand` | `sympy.expand` |
| `factor` | `sympy.factor` |

Each operation receives the clicked presentation's exact stored expression.
On success, append a **new** `Value` for its return, including `None`, update
`_` to that returned object, and print the result through the same class
registry. Do not replace or mutate the source presentation. On an operation
exception, append exactly one `Error`, leave `_` unchanged, and append no
substitute `Value`. A failure while printing the result follows the existing
fallback-`Value` and `Error` rule; the returned object remains `_`.

## One-line row and click detail

For an `Expr` row, call
`sympy.pretty(expr, use_unicode=True, wrap_line=False)`. If its result has no
actual newline, use that entire string. Otherwise use `sympy.sstr(expr)` as
the entire row. The registered printer returns this raw text, without a class
prefix or `repr`/`srepr`; the existing `Value` path escapes unsafe characters
and truncates the complete row to **120 display cells**, with `…` inside the
cap. The original expression remains the presentation's stored object. If
either printer raises, retain the fallback `TYPE <repr unavailable>` row,
append one `Error`, and keep `_` pointing to the expression. The row is one
logical history row even if a narrow screen wraps it physically.

A default left click on a retained `Expr` `Value`, with no accept pending,
calls `sympy.pretty(expr, use_unicode=True, wrap_line=False)` again. Split on
actual `\n` before escaping. Append each pretty line as a separate `Text`
history row, with no type prefix or generic `repr`. Preserve empty internal
lines. Escape each line with the existing safe-display rules and truncate it
to **120 display cells**. Append at most the first **24** pretty lines. If
there are more, append one additional `Text` row exactly
`… (N more lines)`, where `N` is the number omitted. Calculate all lines
before appending any: if pretty printing fails, append one `Error` and no
partial detail rows. Detail does not change `_` or replace the source value;
normal 500-row history eviction still applies.

The generic one-row `TYPE: REPR` detail with its 4096-cell representation cap
remains for a Python `int`, SymPy matrix, or other non-`Expr` `Value`. Typed
`:show` still does not accept `Value`. Keep the existing registered-`Value`
hover and menu-item documentation sentences. Ctrl-O or mouse button 3 opens
the existing menu with the three labels above. A menu choice dispatches
directly, without colon parsing. While composing Python, the menu preserves
the pending pieces and cursor; a valid left-click insertion still makes a chip
that carries the stored expression by identity rather than pretty text.

## Automated verification

Add headless SymPy tests without importing Textual, and keep every existing
test passing. Cover these behaviors:

1. A fresh listener has no `sympy` binding in its Python namespace. User
   `import sympy` binds the name but adds no `Value`. Evaluating
   `sympy.sqrt(8)` adds an `Expr` `Value`, retains the evaluated object by
   identity, and draws a symbolic one-line row without a class-name prefix.
2. The menu labels are exactly `simplify`, `expand`, `factor` in that order.
   Exercise all three. Expanding retained `(x + 1)**2` produces an object
   structurally equal to `x**2 + 2*x + 1`; factoring `x**2 - 1` produces an
   object structurally equal to `(x - 1)*(x + 1)`. The clicked source still
   holds its original object. Compare SymPy expressions with `==`, and use
   identity checks for retention and forwarding; do not infer equality from
   `repr` or pretty text.
3. A later Python chip or call receives the translator result object itself.
   Confirm `_` refers to that object after success. Exercise translator
   failure and a successful `None` return through a separate **test-only**
   class registration or controlled test fixture, since the three production
   SymPy operations do not normally return `None`. These cases must not add
   production menu items or change the production `Expr` registration.
4. Python `int`, SymPy matrix, and an unregistered object stay generic, with
   no SymPy menu. A multiline pretty form uses `sstr` for its single history
   row and individual pretty lines for detail. Cover one-line detail, the
   120-cell line cap, the 24-line cap and exact omission count, an empty
   internal line, and control-character escaping. Verify that row-printer or
   detail failure appends one `Error`, retains the source object, and leaves
   no partial detail rows.

Use temporary roots and injected services for headless tests. Do not require
a network connection or a physical terminal for the automated suite.

## uv workflow and live hand check

If uv is unavailable, stop and report it; do not switch package managers or
run Python outside uv. From the project root, use:

```console
uv add sympy
uv sync
uv run pytest
```

`uv run pytest` is the full automated gate and must pass before the hand
check. Do not use `pip`, `python -m pip`, `uv pip install`, Poetry, Pipenv,
Conda, Hatch, or a hand-made environment.

For the live check, create a **fresh disposable directory beneath the project
root** and record its absolute path. Run `uv run pbui` with that directory as
the current directory in a real interactive terminal. Confirm the prompt
shows the recorded path. Enter `import sympy`, then `sympy.sqrt(8)` and read
its symbolic history row. Open that row's action menu with Ctrl-O, apply one
of the three operations, and verify a new symbolic result row appears while
the source row remains. Compose a later Python expression and click the
result row into a valid insertion site. For an identity check, `id(CHIP) ==
id(_)` should display `True` when `_` still holds that menu result; `CHIP`
means the inserted chip, not typed text. Observe that insertion uses the
object rather than its pretty string. No destructive command is needed.

Report the test result, the disposable directory path, the menu operation,
the observed row and chip behavior, and any terminal limitation. If a real
interactive session is unavailable, report the hand check as unverified
rather than claiming it passed from a mocked screen test.

Sympy 000 is complete when the dependency and registration are in place, the
row, detail, and translator rules pass the headless tests, the full suite is
green, and the live hand check succeeds. Stop there.
