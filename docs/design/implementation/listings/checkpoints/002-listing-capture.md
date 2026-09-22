# listings 002 — Listing capture and stable presentations

**Status.** Ready to implement.

## Goal

Make successful `ls` and `ps` executions capture one retained
`DirectoryListing` or `ProcessListing`. Cache every field required by later
sort, filter, and table redisplay; create one stable header presentation and
one stable member presentation per captured member; and mark every appended
logical row with that listing object as its owner.

This checkpoint continues the headless listing-model layer. It deliberately
keeps the predecessor member-row wording and adds no view command or table
header. Stop when capture, presentation identity, row ownership, and their
tests are green; do not begin redisplay or final table text.

## Identity, authority, and predecessors

- Identity is `(listings, 002)`, spoken **listings 002**.
- [`../spec.md`](../spec.md), especially sections 2, 3.3, 4.4, 7.1, and 8,
  is the design authority. Preserve the accepted listener behavior when this
  checkpoint is silent.
- Listings 000 supplies identity-based listing-owner blocks and atomic
  `replace_listing_rows`.
- Listings 001 supplies the seven exact domain types, cached member records,
  stable identity-based listing values, and pure view operations.
- Both predecessors are implemented and reviewed. The baseline suite has
  **125 passing tests**.
- Listings 003 will add headless view command dispatch and in-place redisplay.
  A later layer will replace the transitional rows with exact tables and make
  the already-created header presentations visible.
- The project root is
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application code
  and tests remain there, never under `docs/`.

## Exact file scope

### May edit

- `src/pbui/domain.py`
- `src/pbui/commands.py`
- `tests/test_domain.py`
- `tests/test_commands.py`

### Must not edit or create

- `.python-version`, `pyproject.toml`, `uv.lock`, `README.md`, or `AGENTS.md`
- `src/pbui/__init__.py` or `src/pbui/__main__.py`
- `src/pbui/substrate.py`, `src/pbui/text.py`, or `src/pbui/terminal.py`
- `tests/test_substrate.py` or `tests/test_terminal.py`
- another production module or test module
- anything under `docs/`, including this checkpoint, the specification, and
  earlier checkpoints
- any file outside the project root

If capture appears to require a history redesign, table formatter, terminal
change, or new dependency, stop and return the checkpoint for correction
instead of widening the slice.

## Preserved behavior and transitional surface

Preserve exactly:

- the current six-command registry and all argument/accept behavior;
- current `show`, `cd`, `rm`, and `kill` revalidation, effects, refusals, chips,
  errors, and translators;
- `ls` revalidation, inclusion of dotfiles, omission only of `.` and `..`,
  symlink classification, and no cwd change;
- `ps` enumeration through the injected service, real-uid filtering, inclusion
  of the listener when inspectable, and no shell execution;
- all listing 001 view behavior and validation;
- the listings 000 history bound, ownership, replacement, and revision rules;
- listener 005 drawing behavior and every terminal interaction; and
- the current safe escaping rule and disabled Rich markup.

This is an intermediate headless checkpoint. Until the table-text layer:

- nonempty directory and process listings retain their reviewed predecessor
  member-row wording;
- the stable listing header presentation exists and is owned by the listing
  but is not yet placed in history;
- an underlying empty directory keeps the existing exact
  `Directory is empty: ABSOLUTE_PATH` row; and
- an empty process capture appends one empty literal owned logical row so the
  captured listing has a retained target. It has no presentation and is not
  final product wording.

Do not add `name  size  modified`, `pid  state  user  command`, `No processes
are available.`, or `Nothing matches the active filters.` here. Those are
table-text requirements, not capture requirements.

## Stable presentation ownership

A production-captured listing must own:

- exactly one header `Presentation` whose value is that exact listing object
  and whose type is the corresponding `DirectoryListing` or `ProcessListing`
  registry entry; and
- one ordered tuple of member `Presentation` objects aligned one-to-one with
  its immutable captured member tuple.

Extend the listings 001 values with a small one-time binding mechanism or
equivalent private construction path. Preserve their identity equality,
captured tuple identity, and view API.

The binding rules are exact:

- an unbound pure listing remains legal for listings 001 callers and tests;
- a production capture binds once and cannot be rebound;
- the header presentation's value is the listing object itself;
- each directory member presentation's value is the original `FileRef` or
  `DirectoryRef` and its exact type agrees with that reference;
- each process member presentation's value is the original `ProcessRef` and
  has exact `Process` type;
- member presentation order and count match the captured member tuple;
- presentation ids are unique within the owned set; and
- public read access returns the stable objects without copying or recreating
  them.

Use the existing `DrawingContext` allocation path so presentation ids remain
globally coherent. Register pure listing-type drawers in the existing domain
drawing contexts only as needed to allocate the header presentations. Their
transitional drawing is the empty string; no header row is appended in this
checkpoint. Validate exact `DirectoryListing`/`ProcessListing` values in those
drawers. Do not create a second presentation-id allocator.

Creating an ordinary pure listing must not allocate a presentation. A
successful `ls` or `ps` allocates each header/member presentation exactly once;
later view changes must reuse them.

## Password-database seam

Add a small injectable username-lookup seam to the headless command layer. The
production implementation uses `pwd.getpwuid(real_uid).pw_name`. Preserve all
existing `HeadlessListener` construction calls by making production lookup the
default.

For each captured process:

- when lookup returns a string name, safely escape that full name once;
- when no entry exists or lookup fails with the password database's ordinary
  lookup/OS failures, use the decimal uid and safely escape it once; and
- when an injected lookup returns a non-string result, treat it as lookup
  failure and use the decimal uid rather than admitting a malformed value.

Do not cache a username across separate `ps` commands. Do not create `User`, a
user presentation, or user-click behavior. Tests inject this seam and never
depend on the machine's live password database.

## Directory capture

Refactor successful `_command_ls` capture so it first constructs one complete
`DirectoryListing` before appending any row.

For each entry returned by the injected filesystem service:

1. Omit only literal `.` and `..` names.
2. Preserve the normalized absolute lexical child path.
3. Perform followed `stat` and classify a successful directory as
   `DirectoryRef`; classify every other successful result as `FileRef`.
4. If followed `stat` fails with the accepted absent/unresolved errors, use
   `lstat`; a final symlink is a broken `FileRef`, while another result or
   failure follows the existing error path.
5. Cache `escape_display(entry.name)` as the full displayed basename.
6. Cache `int(round(st_mtime))`, using followed `stat` for a live entry and
   `lstat` for a broken final symlink.
7. Cache followed or broken-link `st_size` for a file and `None` for a
   directory.

Each entry is inspected only during this capture. Do not call the old
classification helper and then repeat `stat` to obtain metadata. Directory
mtime is cached even though its size is blank. Capture order is not display
order; use the listing's default pure view to choose predecessor row order.

After all member records exist:

- create the stable header presentation;
- create the aligned stable `File`/`Directory` member presentations;
- bind them to the listing; and
- append one contiguous owned block whose `listing_owner is listing` on every
  row.

The predecessor row's clickable member presentation must be the exact object
owned by the listing. Do not present the same reference a second time merely
to build its row.

For an underlying empty directory, bind the header and empty member tuple, then
append the existing explanatory text as one owned row. Host failure anywhere
before completion appends the existing stable `Error` form and appends no
owned or partial listing rows.

## Process capture

Refactor successful `_command_ps` capture so it first constructs one complete
`ProcessListing` before appending any row.

- Call `list_for_uid(own_uid)` once.
- Retain the same records as the reviewed listener: real uid must equal the
  listener's real uid; unreadable/malformed entries are already skipped by the
  process service; the listener remains included when inspectable.
- For every retained record cache its exact `ProcessRef`, canonical state word,
  real uid, escaped displayed user from the injected lookup, and full
  `escape_display(record.command)` result.
- Never truncate or normalize the cached command.
- Use the listing's default pure pid view for predecessor row order.

Create and bind one stable header and the aligned stable `Process`
presentations. Build each predecessor row from its stable member presentation,
cached state, and already escaped full command; do not pass the cached command
through `escape_display` again.

If the captured sequence is empty, append one empty literal logical row with
`listing_owner is listing`, no fragments carrying a presentation, and no Text
or Error presentation. This temporary row exists only to retain the listing
identity until the table checkpoint supplies final explanatory text.

A process enumeration failure appends the existing stable `Error` form and no
owned or partial listing. Username lookup failure alone is never a listing
failure; it uses the decimal uid fallback.

## Listing discovery and lifetime

No separate global listing registry is needed. A retained listing is
discoverable through `HistoryRow.listing_owner`, and its owned header/member
presentations are reachable from that listing value. Successive `ls` or `ps`
commands create different listing objects and append different contiguous
blocks, even when their captured host data is equal.

Expose no refresh method. Running another `ls` or `ps` is the only way to read
fresh host state. Existing pure view methods on an already captured listing
must continue using its cached fields after files or process records change.

Row-based history eviction remains unchanged. This checkpoint need not add a
listing finalizer or force collection after complete eviction; it must not add
a permanent listener registry that keeps every evicted listing alive.

## Automated tests

Extend `tests/test_domain.py` only for the one-time presentation-binding
contract. Extend `tests/test_commands.py` for capture integration. Keep all 125
predecessor tests without deletion, weakening, or replacement; update expected
row ownership and presentation composition where the new retained model makes
that necessary.

### Stable presentation binding

Prove at least:

- a pure unbound listing allocates no presentation and retains all listings 001
  behavior;
- valid one-time binding exposes the same header/member presentation objects
  in the same order;
- header/member exact types and original values are enforced;
- count/order mismatch, duplicate ids, wrong value/type, and rebinding are
  rejected without partially changing the listing; and
- view changes preserve header/member presentation object identity.

Do not invent a mock presentation class; use the reviewed substrate values and
drawing context.

### Directory capture

Use `tmp_path` through `RootedFilesystem` where real stat metadata is the point,
and an injected counting filesystem where call counts and mid-capture failure
are the point. Cover:

- files, directories, live file and directory symlinks, and a broken final
  symlink;
- dotfiles retained and only `.`/`..` omitted from an injected enumeration;
- exact absolute references, escaped basenames, file sizes, blank directory
  sizes, and rounded integer mtimes from the correct followed/unlinked stat;
- one listing object shared as owner by its complete contiguous block;
- exact alignment of cached members, stable presentations, and clickable
  predecessor rows;
- an underlying empty directory retaining one owned explanatory row;
- a later host mutation not changing cached members or pure view results;
- a second `ls` capturing a distinct listing with fresh values; and
- a failure after at least one entry was inspected appending one Error and no
  partial listing block.

The counting service must show no repeated metadata read merely to create a
member record or presentation.

### Process capture

Use injected process and username services. Cover:

- real-uid filtering and numeric default pid order;
- full escaped commands, including control characters;
- successful escaped username lookup;
- missing, failing, and malformed username lookup falling back to decimal uid;
- literal user cache with no `User` presentation;
- one stable header and one stable Process presentation per captured member;
- an empty capture retaining exactly one empty owned literal row;
- later process/username-service mutation not changing the captured listing;
- a later `ps` producing a distinct fresh listing; and
- process enumeration failure producing one Error and no partial listing.

Assert that test capture never consults the live password database or live
`/proc`.

### Existing commands and eviction

Keep the stale-object `show`, `rm`, and other command regressions green against
member presentations now owned by listings. With a small history bound, prove
ordinary row eviction can retain a suffix of one captured listing and that a
fully evicted listing is absent from every retained row. Do not test redisplay;
that belongs to listings 003.

## uv workflow and verification

Add no dependency. Use only the existing uv-managed project:

```console
uv sync
uv run pytest
```

All 125 predecessor tests plus the new listings 002 tests must pass. Do not use
`pip`, `python -m pip`, `uv pip install`, Poetry, Pipenv, Conda, Hatch, a
hand-made virtual environment, or a globally installed Python. If `uv` is
unavailable, stop and tell the human.

No `uv run pbui`, physical-terminal hand check, live `/proc` exercise,
dependency edit, or documentation edit is required for this headless capture
checkpoint.

## Completion boundary

Listings 002 is complete only when every successful `ls` or `ps` creates one
fresh fully cached listing, owns one stable header and stable aligned member
presentations, appends one contiguous owner-marked block without partial
failure, uses injected password lookup with decimal fallback, and the full
automated suite passes.

Stop there. Do not add `sort`, `narrow`, `only`, or `widen`; do not call
`replace_listing_rows`; do not add final table headers, cells, fitting, or
explanatory rows; do not add action menus, colors, viewport anchors, substring
accept, or change terminal behavior.
