# HTTP

The eighth pbui exploration: an HTTP request and its response are
objects, and a JSON body can be walked by clicking.

| Artifact | Path |
|---|---|
| Charter | [`charter.md`](charter.md) |
| Spec | [`spec.md`](spec.md) |
| Demo | [`demo.md`](demo.md) |
| Checkpoints | [`http 000`](checkpoints/000-request-and-response.md) · [`http 001`](checkpoints/001-json-rows-and-hand-check.md) |

**Status.** The spec is accepted. Http 000 and http 001 are implemented per
user reports; `uv run pytest` passed 289 tests after http 001. The prescribed
live URL returned HTTP 403 and offered only `body`, so the JSON walk was
unavailable. The disposable hand-check directory was removed.

The program lives at the project root
(`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`).
This exploration extends the implemented listener. Guiding influences
are in [`../../../../AGENTS.md`](../../../../AGENTS.md).

Project map: [`../../../../README.md`](../../../../README.md).
