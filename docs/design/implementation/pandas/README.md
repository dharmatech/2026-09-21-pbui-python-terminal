# Pandas

A `DataFrame` and a `Series` keep their pandas identity in history.
Clicking a frame opens a bounded snapshot. A column click takes a
`Series`. A row click takes a one-row `DataFrame`.

| Artifact | Path |
|---|---|
| Charter | [`charter.md`](charter.md) |
| Spec | [`spec.md`](spec.md) — accepted |
| Checkpoints | [`checkpoints/000-headless-model-and-registration.md`](checkpoints/000-headless-model-and-registration.md) — implemented; [`checkpoints/001-preview-history-and-screen.md`](checkpoints/001-preview-history-and-screen.md) — implemented |
| Demo | [`demo.md`](demo.md) — hands-on tour of the completed inspector |

**Status.** Specification accepted. Pandas 000 and 001 are implemented per
user report. The final `uv run pytest` passed 446 tests, and the live pandas
001 hand check passed.

The program lives at the project root
(`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`).
This folder is only that inspector. Guiding influences are in
[`../../../../AGENTS.md`](../../../../AGENTS.md).

Project map: [`../../../../README.md`](../../../../README.md).
