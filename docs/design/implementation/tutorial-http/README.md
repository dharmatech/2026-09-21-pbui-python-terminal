# HTTP tutorial

Add an HTTP section to the listener's local tutorial. Its cards guide a user
through a live public GET request and the retained request, response, and JSON
objects. The tutorial itself remains package data and needs no local server.

| Artifact | Path |
|---|---|
| Charter | [charter.md](charter.md) — assignment for the spec writer |
| Specification | [spec.md](spec.md) — accepted design authority |
| Checkpoints | [checkpoints/](checkpoints/) — numbered implementation slices |

**Status.** The specification is accepted. Tutorial-http 000 is implemented.
Tutorial-http 001 screen implementation and tests are complete; its direct
`uv run pbui` hand check is pending.

The program and tests live at the project root
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. This folder holds
the design handoff. [AGENTS.md](../../../../AGENTS.md) gives the project rules.
