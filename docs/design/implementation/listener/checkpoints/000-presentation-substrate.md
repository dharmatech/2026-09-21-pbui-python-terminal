# listener 000 — Presentation substrate

**Status.** Ready to implement.

## Goal

Create the packaged Python project and implement the plain-Python presentation
substrate: explicit presentation types, object-bearing presentations, logical
text rows, display-column layout, nested hit testing, bounded history, accept
and atomic chips, and an explicit translator table.

Stop when this layer is green. Do not add domain objects, filesystem or process
services, commands, Textual, Rich, a console script, or a runnable `pbui`.

The implementer receives this checkpoint and the accepted listener
specification. This checkpoint narrows that specification to one independently
testable slice; it does not revise it.

## Identity, authority, and starting point

- Identity is `(listener, 000)`, spoken **listener 000**.
- [`../spec.md`](../spec.md), especially sections 1–3 and 7.1, is the design
  authority. If this checkpoint is silent about a substrate behavior, preserve
  the specification rather than inventing a product feature.
- The project root is
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application code
  and tests go there, never under `docs/`.
- The repository currently has design documents but no `pyproject.toml`, lock
  file, package, environment, or tests. There is no predecessor checkpoint.
- Python is 3.11 or newer. The package import name is `pbui`.

The presentation substrate is application-independent. Its tests use arbitrary
type names and values; it has no built-in knowledge of `File`, `Directory`,
`Process`, `Text`, `Error`, `show`, or any other listener command.

## Exact file scope

### May create or edit

- `.python-version` (created by `uv init`)
- `pyproject.toml`
- `uv.lock`
- `src/pbui/__init__.py`
- `src/pbui/substrate.py`
- `src/pbui/text.py`
- `tests/test_substrate.py`

`uv init` will initially derive a distribution and module name from the dated
project-directory name. Replace that generated module with `src/pbui/`, set the
project name to `pbui`, and remove the generated console-script entry. The
generated dated module may be deleted as part of this normalization even though
its exact normalized spelling is uv-version-dependent.

### Must not edit or create

- `README.md`, `AGENTS.md`, or anything under `docs/`
- `src/pbui/domain.py`, `src/pbui/commands.py`, `src/pbui/terminal.py`, or
  `src/pbui/__main__.py`
- a console-script entry or any runnable application entry point
- any file outside the project root

If another production or test file appears necessary, stop and return the
checkpoint for correction instead of widening the slice.

## Project creation and dependencies

Run these commands from the project root, in this order:

```console
uv init --package --python 3.11
uv add wcwidth
uv add --dev pytest
uv sync
```

Use uv for every Python command. Do not create a virtual environment by hand
and do not use `pip`, `python -m pip`, `uv pip install`, Poetry, Pipenv, Conda,
Hatch, or globally installed Python packages. If uv is unavailable, stop and
tell the human.

After normalizing the generated package, `pyproject.toml` must describe the
`pbui` distribution, require Python `>=3.11`, contain `wcwidth` as a runtime
dependency and pytest as a development dependency, and have no `[project.scripts]`
entry. Do not add Textual, Rich, pytest-asyncio, or another dependency in this
checkpoint. `import pbui`, `import pbui.substrate`, and `import pbui.text` must
work through `uv run`; `uv run pbui` and `python -m pbui` are deliberately not
available yet.

## Explicit presentation types

Implement an immutable `PresentationType` registry entry with one stable,
nonempty name and a `PresentationTypeRegistry` that explicitly registers and
looks up entries by name. Registering a duplicate name is an error. Registry
entries compare by object identity for compatibility: equal spelling, Python
class inheritance, and value equality never make two distinct entries
acceptable in each other's place.

The registry is not generated from Python classes, annotations, methods,
inheritance, or reflection. Any Python value can be stored with any explicitly
chosen presentation type, including a value whose class is otherwise
uninteresting to the substrate.

Each `Presentation` retains all of the following independently of drawn text:

- the original Python value, without copying or parsing it;
- the exact registered `PresentationType` object;
- a stable presentation identity while it remains in history; and
- its current collection of half-open display-cell intervals.

The display intervals are derived state. They are empty before layout and are
replaced wholesale after every layout; they are never incrementally patched.
The logical drawing refers to the stable presentation identity, not directly
to the value, and Rich spans or widgets are not involved.

## Logical rows and pure drawing

Keep the value/type/history model in `pbui.substrate` and the terminal-text
fragments, display-column layout, and pure hit testing in `pbui.text`. Both
modules are plain Python. Neither may import filesystem, process, Rich, or
Textual code.

The text model must support:

- an unpresented literal fragment;
- a presented fragment that refers to one presentation identity and contains
  separately drawn child fragments;
- arbitrary nesting of presented fragments; and
- a `HistoryRow` composed from literal and presented fragments.

A drawing context has an explicit pure-drawer table keyed by exact
`PresentationType` identity. Presenting a value creates its `Presentation`,
asks that registered drawer for its content, and returns a row or fragment that
refers to the new presentation identity. A composed row can use that same
operation for one field and combine the returned presented fragment with
literal columns. An outer drawer can likewise include a more specific inner
presented fragment. Do not introduce a parallel shortcut that draws composed
rows without creating the same object-bearing presentations.

Drawer registration and lookup are explicit. A missing drawer or duplicate
drawer registration must fail clearly rather than fall back to `str(value)`,
`repr(value)`, Python method lookup, or class-name conventions. The concrete
builder API may be chosen during implementation, but it must expose enough of
this model for later domain printers to create standalone, composed, and nested
rows without reaching into private storage.

## Display-column layout

Layout consumes retained logical rows and a requested width. Treat every width
less than one as one. Each logical row occupies at least one physical display
row; wrapping creates more physical rows but never more logical history rows.
The next logical row begins on the physical row after the previous logical
row's final wrapped row.

Use `wcwidth` for every Unicode code point. Python string indexes are never
display columns:

- a combining character has width zero;
- an ordinary narrow character has width one;
- a wide character has width two; and
- a positive-width character that does not fit in the remaining columns starts
  on the next physical row.

The product printers added in later checkpoints will escape newline, tab,
control, and unpaired-surrogate input before it reaches layout. This checkpoint
does not add domain escaping or interpret embedded newline as a second logical
row. Tests should use valid one-row drawing strings. If a code point is wider
than the entire normalized width, place it once at column zero rather than
looping while trying to wrap it.

For every presentation, derive one or more half-open intervals
`[start_column, end_column)` associated with their zero-based physical history
row. A presentation spanning wrapped rows receives separate intervals on each
physical row, never one bounding rectangle. The outer presentation includes
the cells drawn by its descendants; an inner presentation also owns its own
cells. Zero-width code points claim no cell by themselves.

The pure layout result must contain enough rendered-row information for the
later terminal surface to draw the same layout without reconstructing object
identity from text. Relayout at a new width reuses all retained presentation
objects and values, clears the old derived intervals, and computes a complete
new set.

## History retention and hit testing

History retains at most 500 logical rows. Appending logical row 501 discards
the oldest logical row and every presentation owned only by that row. Wrapped
physical rows do not count toward this limit. A discarded presentation is no
longer available by id, has no active layout intervals, and cannot be returned
by hit testing.

Pure hit testing accepts a zero-based display-column `x` and zero-based laid-out
physical history-row `y`. Negative coordinates and cells outside current
layout return no presentation. A candidate contains the pointer only when
`start_column <= x < end_column` on that exact physical row.

When candidates overlap, return the greatest nesting depth. If malformed input
creates overlapping candidates at the same depth, return the one drawn last.
Literal text, padding, holes between intervals, and empty rows return no
presentation. Scrolling and viewport translation belong to the terminal layer;
this layer tests only history coordinates.

## Accept requests and atomic chips

`AcceptRequest` contains:

- a command name;
- a nonempty immutable set of acceptable registered presentation types; and
- a continuation that receives the accepted `Chip`.

`Chip` contains the selected presentation's exact type, the original stored
Python value, and a label used only for drawing. Supplying a presentation makes
one chip and passes it to the continuation only when the presentation's exact
type identity belongs to the acceptable set. The continuation can recover the
stored value directly and must receive the identical Python object; the chip's
label is never parsed or inserted into a text argument buffer.

Provide a small substrate state object or equivalent public operations so the
tests can establish these transitions:

- a matching selection consumes the pending request, stores one chip, and
  invokes the continuation exactly once;
- a nonmatching selection changes neither the pending request, current input
  text, nor chip and invokes nothing;
- cancellation drops both the request and any chip; and
- one Backspace action while a chip is present removes the whole chip, never
  one character of its label.

This layer does not implement command parsing, a cursor editor, keyboard event
objects, or immediate listener command execution. Those behaviors consume the
atomic model in later checkpoints.

## Explicit translators

Implement a `TranslatorTable` keyed by exact registered presentation-type
identity. It starts empty, supports explicit registration and lookup, rejects
duplicate registration for the same exact type, and can invoke a found
translator with the presentation's original stored object. A translator is not
selected from a type name, Python class, inheritance relationship, or value
shape.

The table contains no default registrations and no domain or command names.
When lookup finds no translator, it has no command effect. Mouse-button and
pending-accept precedence are terminal/controller concerns; this checkpoint
only proves the exact object-to-translator path that those layers will call.

## Focused tests

Add `tests/test_substrate.py`. Use arbitrary type names such as `Outer`,
`Inner`, `Alpha`, and `Beta`; the tests must not smuggle listener domain policy
into the substrate. At minimum, prove all of the following:

1. Explicit registration yields immutable stable entries, duplicate names are
   rejected, and two separately created entries are not compatible merely
   because names or stored Python classes are related.
2. A presentation retains the original value by identity and has a stable id;
   its intervals are empty before layout.
3. Pure drawers build a standalone presented row, a composed literal-plus-name
   row, and nested outer/inner presentations through the same presentation
   operation.
4. A hit inside nested content returns the inner presentation, a hit on the
   outer-only content returns the outer presentation, and a literal field or
   padding returns nothing.
5. A deliberately malformed same-depth overlap resolves to the last-drawn
   presentation.
6. Interval ends are exclusive and negative or out-of-layout coordinates miss.
7. A name containing spaces is one presentation across its whole drawn name,
   while neighboring literal columns remain unpresented.
8. Wide and combining characters produce display-cell rather than Python-index
   intervals. A wide character that lacks remaining room wraps before drawing.
9. A wrapped multi-row presentation owns only its per-row intervals and cannot
   be hit in the empty cells of a bounding rectangle.
10. Width zero is normalized to one without hanging.
11. Relayout at a different width replaces old intervals while preserving the
    identical retained presentation and value, and hit testing follows the new
    coordinates.
12. Appending 501 logical rows retains exactly the newest 500, regardless of
    wrapping, and the dropped presentation cannot be looked up or hit.
13. A matching accept creates one atomic chip and passes the original value by
    identity; a nonmatching accept leaves request, text, chip, and continuation
    calls unchanged.
14. Cancellation clears request and chip, and one Backspace removes an entire
    chip whose label contains multiple characters.
15. Translators can be registered and invoked for arbitrary exact types, start
    absent for all types, receive the original value by identity, and do not
    dispatch by a related Python class or equal type name.

Tests may add smaller boundary cases, but they must not require domain modules,
the live filesystem, `/proc`, terminal I/O, Rich, or Textual.

## Verification and completion

Run the complete test suite through uv:

```console
uv run pytest
```

The checkpoint is complete when that command passes; the only installed
runtime dependency is `wcwidth`; the only development dependency is pytest;
only the allowed files changed; and inspection confirms that neither
`pbui.substrate` nor `pbui.text` imports filesystem, process, Rich, or Textual
code.

Stop after reporting the passing command and changed files. Do not start
listener 001.
