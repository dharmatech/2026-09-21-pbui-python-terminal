# Bluesky

Public posts, profiles, and bounded listings are listener objects.
The Python calls that fetch them are `atproto` calls, and the values
in history are the objects those calls return.

| Artifact | Path |
|---|---|
| Charter | [`charter.md`](charter.md) |
| Spec | [`spec.md`](spec.md) — accepted |
| Demo | [`demo.md`](demo.md) — hands-on tour |
| bsky 000 | [`checkpoints/000-retained-models-and-local-graph.md`](checkpoints/000-retained-models-and-local-graph.md) — implemented |
| bsky 001 | [`checkpoints/001-public-client-and-commands.md`](checkpoints/001-public-client-and-commands.md) — implemented |
| bsky 002 | [`checkpoints/002-screen-and-public-hand-check.md`](checkpoints/002-screen-and-public-hand-check.md) — implemented |

**Status.** Bsky 000–002 are implemented. The bsky 002 implementer
reported `uv sync` and `uv run pytest` passing (434 tests), and a
successful read-only hand check of [this public post](https://bsky.app/profile/bsky.app/post/3mseeq5rllc2q)
from the disposable directory
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/.bsky-002-FjbO4r`.

The program lives at the project root
(`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`).
This folder is only public, read-only Bluesky. Guiding influences
are in [`../../../../AGENTS.md`](../../../../AGENTS.md).

Project map: [`../../../../README.md`](../../../../README.md).
