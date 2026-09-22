# listings 000 — Listing-owned history blocks

**Status.** Ready to implement.

## Goal

Add the headless history primitive that later listing checkpoints require:
logical rows may identify the retained listing block that owns them, and
`PresentationHistory` can atomically replace one retained listing block at its
existing logical position.

This is the first, deliberately narrow split of the listing-model layer in
specification section 7.1. It changes no command, capture, drawing, or terminal
behavior. Stop when the history primitive and its tests are green; do not begin
captured listing values or view commands.

## Identity, authority, and predecessors

- Identity is `(listings, 000)`, spoken **listings 000**.
- [`../spec.md`](../spec.md), especially sections 2.2, 4.1, 4.4, 7.1, and 8,
  is the design authority. Preserve the accepted listener behavior when this
  checkpoint is silent.
- Listener 000 through listener 005 are implemented and reviewed. The baseline
  suite has **102 passing tests**.
- There is no preceding listings checkpoint.
- This checkpoint supplies infrastructure only. A later checkpoint in the same
  section 7.1 layer will add `DirectoryListing`, `ProcessListing`, capture,
  sorting, filtering, and command dispatch. Do not anticipate that work here.
- The project root is
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application code
  and tests remain there, never under `docs/`.

## Exact file scope

### May edit

- `src/pbui/text.py`
- `src/pbui/substrate.py`
- `tests/test_substrate.py`

### Must not edit or create

- `.python-version`, `pyproject.toml`, `uv.lock`, `README.md`, or `AGENTS.md`
- `src/pbui/__init__.py` or `src/pbui/__main__.py`
- `src/pbui/domain.py`, `src/pbui/commands.py`, or `src/pbui/terminal.py`
- `tests/test_domain.py`, `tests/test_commands.py`, or
  `tests/test_terminal.py`
- another production module or test module
- anything under `docs/`, including this checkpoint, the specification, and
  listener checkpoints
- any file outside the project root

If the primitive appears to require a listing domain class, a command change,
Textual code, or a new dependency, stop and return the checkpoint for
correction instead of widening the slice.

## Preserved behavior

All currently constructed `HistoryRow` values are unowned. Their existing
construction, equality, fragments, presentations, layout, hit testing, and
rendered text remain unchanged when the new metadata is omitted.

Preserve exactly:

- the 500-logical-row default and configurable positive test bound;
- append-time presentation validation and presentation-id uniqueness;
- one reference count per presentation per logical row, even if a row's
  fragments mention that presentation more than once;
- eviction by oldest logical row;
- clearing the display intervals of a presentation when its final retained
  reference disappears;
- the history revision behavior of existing `append` calls;
- stale-layout rejection through history revision;
- exact presentation objects and values retained outside an edited block; and
- every existing substrate, domain, command, and terminal behavior.

Do not create a second history collection, a listing-specific history class,
or a terminal-side replacement algorithm.

## Row ownership metadata

Extend `HistoryRow` with one optional listing-owner value. The public field may
be named `listing_owner`; an equally direct name is acceptable if it is used
consistently by the history API and tests.

- The default is `None`, meaning that the row is not part of a listing block.
- A non-`None` owner is an opaque identity token. History does not import or
  inspect a future listing class.
- Compare owners by Python object identity (`is`), never by equality or hash.
  The value need not be hashable and an adversarial `__eq__` must not run.
- Ownership is metadata only. It does not add a fragment, presentation, text,
  or logical row.
- Existing positional construction of `HistoryRow(fragments, presentations)`
  remains valid.

Rows carrying one retained non-`None` owner form exactly one contiguous block.
Keep that invariant in the history model. Appending another row for an owner is
valid while that owner's retained block is the newest block. Appending it after
an intervening retained row with another owner or with no owner is invalid and
must leave history unchanged. If no row for the identity remains after normal
oldest-row eviction, history need not remember the discarded identity.

Do not add a stable member/header row key in this checkpoint. The later table
and screen work will introduce the key at the point where viewport anchoring
can use it.

## Atomic replacement operation

Add the named operation required by the specification:

```text
replace_listing_rows(listing_identity, replacement_rows)
```

It belongs on `PresentationHistory`, because that class already owns logical
row order, presentation retention, reference counts, revision, and eviction.
It has these exact semantics:

1. `listing_identity` must be non-`None`.
2. Find rows whose owner *is* that identity. At least one retained row must
   exist, and all matches must be one contiguous block.
3. Materialize the replacement iterable exactly once. It must contain at least
   one `HistoryRow`, and every replacement row's owner must be that exact
   identity. A replacement cannot insert unowned or foreign-owned rows.
4. Validate every replacement row with the same fragment/presentation and
   presentation-id uniqueness rules used by `append`.
5. Validate that insertion would preserve one contiguous block for every
   retained owner and that one presentation id never denotes two different
   `Presentation` objects.
6. Only after every validation succeeds, replace the target block at its first
   retained logical index. Rows before and after it are the exact same row
   objects in the same relative order.
7. Recompute or update presentation reference counts for the resulting rows.
   Presentations reused by the replacement remain the exact same objects.
   A presentation with another retained reference is not discarded merely
   because its target-block row was removed.
8. Enforce the configured logical-row bound by discarding oldest rows, one row
   at a time, after insertion. A large replacement may evict rows before the
   block and then the oldest rows of the replacement itself.
9. Clear layout-derived intervals for every presentation retained after the
   edit as well as every presentation whose final reference was discarded.
   Replacement can shift physical coordinates on both sides of the block; no
   old display span may remain authoritative. The next layout pass rebuilds
   them.
10. Increment history revision exactly once for the complete successful
    operation, including all necessary eviction. Do not implement replacement
    as public `append` calls or expose intermediate revisions.

The operation appends no copy at the newest end. It is successful even when
the replacement happens to contain the same row objects as the old block; that
is still one replacement and one revision increment.

Use a clear failure for invalid input. `ValueError` is appropriate for a
`None` identity, empty replacement, wrong owner, discontiguous ownership, or
conflicting presentation identity; `KeyError` is appropriate when the target
identity has no retained row. Preserve an existing more specific `TypeError`
where current row validation already uses it.

Every failure is atomic: rows, presentation lookup, reference counts,
intervals, and revision all remain exactly as they were before the call. Do not
partially remove a target block and then attempt validation.

## Partial and complete retention

Eviction stays row based rather than listing based.

- If oldest-row eviction removes a listing header or early members but at
  least one row with that owner remains, the owner is still a valid replacement
  target. Replacement occurs where the first retained row of that partial
  block stood.
- If eviction removes every row with that owner, replacement raises the
  no-retained-target `KeyError` and changes nothing.
- The history model does not preserve a hidden owner registry after complete
  eviction. Future listing model objects may become collectible when neither
  history nor another application reference retains them.
- Wrapped physical rows never participate in the bound or block search.

The later command layer, not this primitive, will translate absence into the
product sentence `Error: no listing in history.`

## Automated tests

Extend `tests/test_substrate.py`. Keep all 102 predecessor tests without
deletion, weakening, or replacement. Add focused headless tests covering at
least the following.

### Compatibility and owner identity

- Existing two-argument `HistoryRow` construction produces `listing_owner is
  None` and behaves exactly as before.
- Two distinct, equality-comparing or unhashable owner objects remain distinct
  identities. The operation never calls their equality or hashes them.
- Owned append permits consecutive rows for one identity, permits a following
  different block, and rejects reopening a still-retained earlier block after
  an intervening row without changing any history state.

### Replacement position and identity

Construct unowned rows before and after an owned multirow block. Replace the
block with both shorter and longer row sequences. Assert:

- the block stays at the old logical index rather than moving to the end;
- all outside row objects retain identity and relative order;
- replacement row objects are the supplied objects;
- header/member presentations deliberately reused in replacement retain
  object identity and stored value;
- a removed, otherwise-unreferenced presentation leaves lookup and has empty
  intervals; and
- revision increases by exactly one.

Give one removed presentation a reference in an outside row and prove it
remains retained with the correct final reference behavior.

### Validation is atomic

Snapshot rows, presentations, intervals, and revision, then separately reject:

- a missing target identity;
- `None` as the target;
- an empty replacement;
- an unowned replacement row;
- a replacement row owned by a different identity;
- invalid row presentation metadata;
- the same presentation id backed by a different object; and
- any attempted discontiguous retained owner block.

Each case leaves the full snapshot unchanged. Use hand-constructed rows only
where needed to exercise a malformed boundary; normal test setup should go
through the reviewed drawing context and `append` path.

### Eviction and the logical bound

Use a small configured bound to prove all of these cases without terminal
layout:

- ordinary oldest-row eviction can leave only the tail of an owned block;
- that partially retained identity is still replaceable at its retained
  position;
- a replacement longer than available capacity evicts oldest outside rows and,
  when necessary, its own oldest rows;
- final length never exceeds the configured bound;
- complete eviction makes the old identity unavailable; and
- one replacement with several internal evictions still increments revision
  once.

Populate nonempty `DisplayInterval` tuples before a successful replacement and
prove that all resulting retained presentations have empty intervals until a
fresh `layout` call repopulates them. Also prove that a layout captured before
replacement rejects hit testing after the single revision change.

The tests import no Textual code, create no terminal application, read no live
filesystem or `/proc`, and use no timing assertions.

## uv workflow and verification

Add no dependency. Use only the existing uv-managed project:

```console
uv sync
uv run pytest
```

All 102 predecessor tests plus the new listings 000 tests must pass. Do not use
`pip`, `python -m pip`, `uv pip install`, Poetry, Pipenv, Conda, Hatch, a
hand-made virtual environment, or a globally installed Python. If `uv` is
unavailable, stop and tell the human.

No `uv run pbui`, physical-terminal hand check, live `/proc` exercise,
dependency edit, or documentation edit is required for this headless
checkpoint.

## Completion boundary

Listings 000 is complete only when owned rows form retained contiguous blocks,
`replace_listing_rows` atomically replaces one such block in place, reference
counts and display intervals are correct, row-based eviction and the logical
bound still hold, stale layouts are rejected, and the entire automated suite
passes.

Stop there. Do not add the two listing presentation types, captured member or
view models, `sort`, `narrow`, `only`, `widen`, table headers or cells, action
menus, colors, viewport anchors, substring accept, or any terminal behavior.
