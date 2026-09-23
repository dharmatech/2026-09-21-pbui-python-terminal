# listings 006 — Viewport anchoring for listing redisplay

**Status.** Ready to implement.

## Goal

Keep the reader's place when a retained listing is sorted, filtered, widened,
or relaid out. Anchor the oldest visible logical row and its position within
wrapped physical rows; map that anchor through an in-place listing replacement
by stable row identity; and re-hit-test hover at the current pointer
coordinate. A view operation must not scroll to newest output. Appended output
keeps the listener's existing reveal-newest behavior.

This is the viewport portion of specification section 7.3. The action menu,
button 3, and `Ctrl-O` remain a later checkpoint.

## Identity, authority, and predecessors

- Identity is `(listings, 006)`, spoken **listings 006**.
- [`../spec.md`](../spec.md), especially sections 4.4, 5.1's
  opening/closing anchor rule, 6.1, 6.4, 7.3, and 8, is the design authority.
  Preserve the rest of that specification when this checkpoint is silent.
- Listings 000–005 are implemented and reviewed. The stable listing/header/
  member identities, atomic owner-block replacement, pure layout, and terminal
  pointer and styling behavior are already available.
- The baseline suite has **177 passing tests**.
- The project root is
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application
  code and tests remain there, never under `docs/`.

## Exact file scope

### May edit

- `src/pbui/terminal.py`
- `tests/test_terminal.py`

### Must not edit or create

- `.python-version`, `pyproject.toml`, `uv.lock`, `README.md`, or `AGENTS.md`
- `src/pbui/__init__.py` or `src/pbui/__main__.py`
- `src/pbui/commands.py`, `src/pbui/domain.py`, `src/pbui/substrate.py`, or
  `src/pbui/text.py`
- another production module or test module
- anything under `docs/`, including this checkpoint, the specification, and
  earlier checkpoints
- any file outside the project root

The anchor is terminal-derived state, not a new history or listing model
field. If an invariant appears to require changing the headless API, pure
layout, or history replacement, stop and return the checkpoint for correction.

## Preserved behavior

Preserve exactly:

- the listings 000–005 identity, capture, table, view, styling,
  documentation, modal substring, chip, accept, and click semantics;
- the 500-logical-row bound and row-based eviction;
- the single `HistorySurface`, direct per-physical-row drawing, and targeted
  hover restyling from listener 005;
- normal appended-output reveal-newest behavior after submitted commands;
- existing one-row fixed documentation and prompt regions, left click, wheel,
  terminal cleanup, `Ctrl-C`, and guarded `Ctrl-D` behavior; and
- no host refresh or confirmation row for a listing view operation.

No menu surface or binding belongs to this checkpoint. The anchor mechanism
should be usable when a later menu temporarily changes the history viewport
height, but do not build that menu now.

## Capturing the viewport anchor

Before relayout caused by a history revision, content-width change, or
viewport-height change, capture from the **old** layout and its corresponding
saved logical rows:

1. The top visible physical row, clamped into the old layout.
2. Its logical `HistoryRow` object and its identity-based listing owner, if
   any.
3. Its zero-based offset among the physical rows wrapped from that logical
   row. If the viewport starts on the second line of a wrapped row, this
   offset is one, not zero.
4. For a listing row, a stable row key: the exact header presentation, the
   exact captured member presentation, or the explanatory-row role. The
   listing owner plus row key distinguishes two listings with equal text or
   equal member values.

An ordinary row outside a listing block is keyed by its `HistoryRow` object
identity. Do not use rendered text, logical index, pid, pathname, structural
equality, stale display intervals, or pointer coordinates as an anchor key.
The old logical rows must be read from the layout's own saved snapshot, since
the live history may already have been atomically replaced when the terminal
synchronizes. A small private terminal-only anchor record/helper is fine.

When history is empty, use scroll row zero. A height-only resize must still
recompute the clamped target and hover even when content width and history
revision are unchanged.

## Resolving after replacement or relayout

After constructing the new pure layout, resolve the captured anchor in this
order:

1. If its exact logical row object is still retained, use that row. This
   preserves an outside row even when a preceding listing shrinks or grows.
2. Otherwise, if its listing owner is still retained and its keyed header,
   member, or explanatory role is visible, use that replacement row. This
   preserves the same listing header/member across new `HistoryRow` objects
   and altered sort position.
3. If that listing member or explanatory row disappeared under a filter, use
   the same listing's new header.
4. If the header was itself evicted by the logical-row bound, use the first
   retained replacement row for that listing.
5. If the old anchor was evicted entirely, or no row of its listing remains,
   use the first retained logical row of the new history.

For the selected row, choose its first physical row plus the old wrapped-row
offset, limited to the selected row's new physical-row count. Then clamp to
the new viewport's maximum scroll position. If the result is clamped because
there is too little history below it, that is expected; never scroll beyond
the physical extent. If no physical row exists, use zero.

The same rule applies on width-only and height-only resize. In particular, a
width change must not reset an anchor from a continuation line to the first
line merely because the row's wrapping changed. On a forced relayout with no
data change, keep the anchor as well. Do not cache stale pure-layout hit
intervals.

## Terminal command and pointer integration

`HistorySurface.synchronize` currently anchors only when width changes, and
`CommandInput.on_key` currently requests `reveal_newest` for every revision
change. Update these paths together:

- Successful typed `sort`, `narrow`, `only`, and `widen`, including completion
  of modal `narrow`, replace a listing in place and keep the resolved anchor.
  This holds whether the target listing is newest or an older retained block.
- An ordinary command that appends a row or a fresh `ls`/`ps` listing still
  reveals the newest output after Enter, as before. A command that changes no
  history keeps the current position.
- Do not use changed row count as the append/replacement discriminator: a
  replacement may lengthen or shorten its block. Distinguish effects from
  pre/post row and owner identities or an equally reliable terminal-local
  result; do not duplicate the headless command parser or recapture data.
- A direct headless `apply_listing_view` followed by terminal synchronize
  must also preserve the anchor, without depending on a CommandInput event.
- After the final scroll position is established, re-hit-test the retained
  viewport pointer against the **new** layout and current coordinate. Update
  hover styling and pointer-aware documentation from that fresh hit. A row
  that moved away must not remain hovered merely because its presentation is
  still retained.
- If the pointer is outside the newly drawable viewport, clear pointer/hover
  and restore the appropriate no-presentation or modal documentation.

Changing the anchor or hover must not append history, mutate a listing view,
create new presentations, or run `show`/`rm`/`cd`/`kill`.

## Automated tests

Extend `tests/test_terminal.py` without deleting or weakening predecessor
tests. Use `PbuiApp.run_test()`, injected services, constructed cached
listings, temporary filesystem roots, and small history bounds where useful.
No live `/proc`, arbitrary signal, or external filesystem mutation is needed.

Prove at least:

- an outside logical-row anchor stays at the top when an older listing before
  it shrinks and grows, with exact outside `HistoryRow` identity preserved;
- a retained listing header and member stay anchored across sort, filter,
  and widen, including a member whose sorted logical position changes;
- an anchor on a filtered-away member falls back to its listing header; an
  evicted header falls back to the first retained replacement row; a fully
  evicted anchor falls back to the first retained history row;
- an anchor beginning on a wrapped row's continuation line keeps its offset
  across replacement and resize, limited by the new wrap count and viewport
  clamp;
- width-only and height-only resizes preserve the logical anchor and keep
  the prompt/documentation outside the scrolling region;
- typed view commands and modal `narrow` completion do not reveal newest,
  while a command that appends output still does;
- pointer hover and the documentation line are re-hit-tested after shifting
  rows, changed wrapping, filtering, and viewport-height change;
- the replacement increments history revision only through the existing
  headless operation, with no new capture, confirmation row, or changed
  outside-row identities; and
- the listener 005 regression remains green: passive hover rebuilds only
  entered/exited physical rows, with no elapsed-time assertion.

Keep all 177 predecessor tests green. Do not weaken them to fit the new
anchor behavior.

## uv workflow and verification

Add no dependency. Use only the existing uv-managed project:

```console
uv sync
uv run pytest
```

All predecessor tests plus the new listings 006 tests must pass. Do not use
`pip`, `python -m pip`, `uv pip install`, Poetry, Pipenv, Conda, Hatch, a
hand-made virtual environment, or a globally installed Python. If `uv` is
unavailable, stop and tell the human.

No physical-terminal hand check, action-menu implementation, live `/proc`
exercise, or new dependency is required for this viewport checkpoint.

## Completion boundary

Listings 006 is complete when in-place listing redisplay and resize preserve
the specified stable row and wrapped-line anchor where possible; missing or
evicted rows use the exact fallback order; appended output still reveals
newest; pointer hover and documentation follow the new layout; and the full
suite passes without compromising local hover rendering.

Stop there. Do not add button 3, `Ctrl-O`, an action menu, menu actions or
documentation, or the live hand check.
