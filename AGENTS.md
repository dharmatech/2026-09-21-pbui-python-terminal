# Project notes

Python in this project is managed only with **uv**. This applies to
creating the application, the environment, dependencies, and every
command that runs the program or the tests.

The personal skill `python-uv-workflow` says the same thing. This
file is the project rule, including for a conversation that does not
have that skill loaded.

- Create the application with `uv init` at the project root
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.
  Use `uv init --package` when the layout is a `src/` package.
- Create and refresh the environment with `uv sync`. Do not create a
  virtualenv by hand.
- Add dependencies with `uv add` and `uv add --dev`, so they are
  recorded in `pyproject.toml` and `uv.lock`.
- Run Python, the `pbui` script, and pytest through `uv run`.
- If `uv` is missing, stop and say so. Do not fall back to `pip`,
  `python -m pip`, Poetry, Pipenv, Conda, or Hatch.

`uv pip install` is not how this project takes a dependency.

## What this project is

pbui is an exploration of a presentation-based listener that feels
comfortable on Linux. The program is a full-screen terminal
application. Its history retains live objects, and a click hands the
object to the next command. The implemented listener is files,
directories, and processes: `ls`, `ps`, `show`, `cd`, `rm`, and
`kill`.

These are the guiding influences for discussion and design. They are
not a backlog, and they are not permission to replace the Linux
program with a Lisp machine or a CLIM port.

- Eugene C. Ciccarelli IV, *Presentation Based User Interfaces*, MIT
  AI Lab AITR-794 (1984). The copy read for this project is in the
  sibling journal `2026-09-21-presentation-ui`. This is the
  architectural idea: a presentation is a visible form of an
  application object, a presenter keeps that form current, and a
  recognizer turns the user's manipulation into commands. Style is
  separate from the objects. PSBase and its icon, menu, and
  annotation desktops are not the product.
- The Symbolics Genera Dynamic Lisp Listener, on Dynamic Windows.
  This is the interaction the listener copies: the output history
  retains the object, `present` and `accept` are the two directions,
  a click during accept supplies the object, and a click with
  nothing waiting runs the default command. A documentation line
  says what that click will do.
- Scott McKay, William York, and Michael McMahon, "A Presentation
  Manager Based on Application Semantics" (UIST 1989). The short
  account of that Genera mechanism: a presentation is the object,
  its type, and its ink. Operations come from the presentation-type
  lattice, not from a widget under the pointer.
- CLIM, and the CLIM and McCLIM listeners. The portable descendant
  of Dynamic Windows. Use it when the question is how a listener
  implemented `present`, `accept`, translators, or output recording.
  McCLIM is the one that can be run and read. Reimplementing CLIM is
  not the goal.

For implementation of the program as it stands, the accepted
specifications under `docs/design/implementation/` are the law:
listener, listings, repl, chips, sympy, transcript, popup, http,
tutorial, recall, and completion. Their charters are the original
assignments, not the current law. Bottom is accepted and implemented
through bottom 002. Recall is accepted and implemented through recall
001. Completion is accepted and implemented through completion 002.
`docs/design/implementation/bottom/checkpoints/003-remove-no-target-wording.md`
is ready to implement and is not part of the history work.
`docs/design/implementation/history/charter.md` is the open
exploration: a blank line between history operations, and a
two-column indent on every row that is not transcript input. Until
that specification is accepted, that work is discussion, not
implementation. Implementers follow one approved checkpoint. The
checkpoint repeats the `uv` commands for the slice it covers.
