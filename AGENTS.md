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

Design for the current exploration is
`docs/design/implementation/listener/charter.md`. Implementers follow
an approved checkpoint. The checkpoint repeats the `uv` commands for
the slice it covers.
