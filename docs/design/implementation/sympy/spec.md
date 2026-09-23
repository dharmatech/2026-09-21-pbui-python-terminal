# Specification — SymPy expressions in the listener

**Status:** accepted specification for **sympy 000**. This is the complete design input for that checkpoint. The charter is not an implementation input; this document assigns no implementation work by itself.

A SymPy expression is still a Python `Value` retaining its original object. Its history row reads as algebra, its default `show` displays bounded Unicode pretty printing, and its action menu offers `simplify`, `expand`, and `factor`.

## 1. Authority and boundary

This specification extends the implemented [listener](../listener/spec.md), [listings](../listings/spec.md), [REPL](../repl/spec.md), and [chips](../chips/spec.md) designs. For objects whose class is under `sympy.Expr`, it supersedes the REPL's generic `Value` row printer and generic `Value` detail `show`. It also adds one production class registration to the REPL's existing registry. All other presentation types, generic values, commands, accepts, menus, input modes, and chip behavior keep their existing rules.

Use the existing `src/pbui/` package and `tests/`; this is not a new application or a second printer framework. Add SymPy as a project dependency with `uv add sympy`, refresh the environment with `uv sync`, and run the automated gate with `uv run pytest`. Run `uv run pbui` only for the hand check. If `uv` is unavailable, stop and report it. The headless evaluator and registration must remain importable without Textual; only `pbui.terminal` imports Textual.

## 2. Registration and object identity

At listener startup, import SymPy in the application and register **`sympy.Expr` only** through the existing Python-class `Value` registry. Do not register `sympy.Basic`, `sympy.Matrix`, or `sympy.MatrixBase`. Lookup still walks `type(value).__mro__` and takes the first registered class without combining registrations. The registration supplies the row printer in section 3 and these translators in this exact order:

| Menu label | Function called with the stored expression |
|---|---|
| `simplify` | `sympy.simplify` |
| `expand` | `sympy.expand` |
| `factor` | `sympy.factor` |

Importing SymPy for registration must not bind `sympy` or any SymPy name in the listener's Python namespace. That namespace still begins with only `{"__name__": "__pbui__"}`; the user makes `sympy` available to their own code with ordinary `import sympy`. A Python `int`, a SymPy matrix, and any other unregistered object use the generic `TYPE REPR` `Value` row and have no SymPy menu.

Each translator receives the exact object retained by the clicked `Value`. On success, append a new `Value` for the returned object, even when it is `None`, and set `_` to that returned object. Present the result through the same class registry, so an `Expr` result gets the SymPy row and any non-`Expr` result follows its own registration or the generic printer. The source presentation and its object are not mutated or replaced. If the function raises, append exactly one `Error`, keep `_` unchanged, and do not present a substitute result. The source presentation remains in history, subject only to the existing history capacity. Printing a returned object follows the REPL's existing fallback-`Value` and `Error` rule.

## 3. One-line history row

For an `Expr`, compute `sympy.pretty(expr, use_unicode=True, wrap_line=False)`. If that string contains no newline, use it as the entire row. If it contains a newline, use `sympy.sstr(expr)` as the entire row instead. This makes a tall fraction or other two-dimensional form legible on a single history row without showing escaped pretty-print line breaks. Neither path prefixes the row with a Python class name or uses `repr`/`srepr`. A short value such as `x` or `sympy.sqrt(8)` must remain recognizably symbolic; SymPy may already have simplified the latter to `2*sqrt(2)` before presentation.

The registered printer returns the chosen raw string. The existing `Value` registration path escapes control characters, tabs, embedded newlines, and unpaired surrogates, then truncates the complete row to **120 display cells**, with `…` inside that budget. This also makes an unusual symbol name safe if the string printer contains a newline. The row is one logical history row; ordinary terminal layout may wrap it on a narrower screen. The `Value` presentation retains the original expression by identity, not its printed text. If either printer raises, keep the existing fallback `TYPE <repr unavailable>` row and append one `Error`; `_` still refers to the expression.

## 4. `show` and screen interaction

With no accept pending, left click on an `Expr` `Value` runs its detail `show`. Compute `sympy.pretty(expr, use_unicode=True, wrap_line=False)` again and append its lines as separate `Text` history rows, one row per pretty line, with no class prefix and no generic bounded `repr`. Split on actual `\n` characters before escaping. Escape each line with the listener's safe-display rules and truncate each to **120 display cells**, using the existing `…` truncation. Empty internal pretty lines remain empty `Text` rows. A one-line pretty form produces one `Text` row.

Show at most **24 pretty lines**. If more exist, append the first 24 and then one additional `Text` row exactly `… (N more lines)`, where `N` is the number omitted. The marker is not part of the expression and is subject to the same 120-cell safety limit. Compute the lines before appending them: if pretty printing raises, append one `Error` and no partial detail rows. Showing detail never changes `_` or replaces the source `Value`; ordinary 500-row history eviction still applies.

Only an `Expr` gets this detail branch. A generic `Value`, including a Python `int` or SymPy matrix, keeps the REPL's one-row `TYPE: REPR` detail with its 4096-cell representation cap. Typed `:show` still does not accept a `Value`, including an `Expr`; this branch is the existing direct-click detail action.

Ctrl-O or mouse button 3 opens the existing `Value` action menu with the three labels above. No second menu route or new documentation sentence is needed: the existing registered-`Value` hover sentence and menu-item sentence remain exact. Menu dispatch is direct and does not pass through colon parsing. During Python composition, menu actions preserve the pending pieces and cursor according to the chips specification. A left click at a valid Python expression insertion site still inserts a chip containing the stored expression by identity; it does not call `show` or insert the pretty text. Existing menu, accept, and composition precedence remains unchanged.

## 5. Verification and slice

Keep all existing tests passing. Add headless SymPy tests without importing Textual. Cover at least:

- With a fresh listener, its Python namespace has no `sympy`; `import sympy` binds it without adding a `Value`. Submitting `sympy.sqrt(8)` then adds an `Expr` `Value` whose one-line row follows section 3, has no class-name prefix, and retains the exact result object.
- The menu labels are exactly `simplify`, `expand`, `factor` in that order. `expand` on the retained `(x + 1)**2` adds a new expression structurally equal to `x**2 + 2*x + 1`; the source presentation still holds the original power object. `factor` on `x**2 - 1` adds a new expression structurally equal to `(x - 1)*(x + 1)`. Test the `simplify` action as well. Use SymPy expression `==` for these structural comparisons, plus identity checks where identity matters; never compare `repr` or pretty text to decide expression equality.
- A subsequent Python chip or call such as `sympy.factor` receives the translator result object itself. A translator exception adds one `Error` without changing `_` or fabricating a result row. A successful translator that returns `None` still presents `None`, as the REPL requires.
- A Python `int`, a SymPy matrix, and an unregistered object remain generic and have no SymPy menu. A multiline pretty form uses `sstr` for its history row and pretty lines for `show`; detail line width, line count, omission marker, control escaping, and a one-line detail are bounded as specified. A printer or detail failure keeps the source object and appends one `Error`.

One implementation slice, **sympy 000**, covers the dependency, startup registration, row printer, detail branch, three translators, and headless tests. Run `uv run pytest` before the hand check. From a fresh disposable directory under the project root, record its absolute path and run `uv run pbui`; import SymPy, enter `sympy.sqrt(8)`, read the symbolic row, apply one menu operation, then click the resulting row into a later Python expression and confirm the expression object was used. No destructive command is needed.

The human reviews this specification before the checkpoint manager writes **sympy 000**. Pandas, matrices as a new presentation, solvers, plots, LaTeX, new commands or input syntax, name preloading, and changes to chip splicing are outside this exploration.
