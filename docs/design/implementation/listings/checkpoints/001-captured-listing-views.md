# listings 001 — Captured listing values and views

**Status.** Ready to implement.

## Goal

Add the two retained listing domain values, their immutable cached member
records, and their pure sort/filter view behavior. A listing is one stable
object with one immutable captured sequence and one replaceable view state.
Every view operation consumes only captured fields.

This is the second split of the listing-model layer in specification section
7.1. It creates no presentations or history rows, performs no host capture,
and changes no command or terminal behavior. Stop when the pure model and its
tests are green; do not integrate `ls`, `ps`, or view commands yet.

## Identity, authority, and predecessors

- Identity is `(listings, 001)`, spoken **listings 001**.
- [`../spec.md`](../spec.md), especially sections 2, 3.3, 4.2, 7.1, and 8,
  is the design authority. Preserve the accepted listener behavior when this
  checkpoint is silent.
- Listings 000 is implemented and reviewed. It added opaque identity-based
  `HistoryRow.listing_owner` metadata and atomic in-place
  `PresentationHistory.replace_listing_rows`.
- The reviewed baseline suite has **107 passing tests**.
- This checkpoint remains within the first headless layer. A later listings
  checkpoint will capture host data, create stable header/member
  presentations, append listing-owned history blocks, and route the four view
  commands through this model.
- The project root is
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application code
  and tests remain there, never under `docs/`.

## Exact file scope

### May edit

- `src/pbui/domain.py`
- `tests/test_domain.py`
- `tests/test_commands.py`, only to update assertions about the expanded exact
  domain-type registry and to prove the two listing types have no translator

### Must not edit or create

- `.python-version`, `pyproject.toml`, `uv.lock`, `README.md`, or `AGENTS.md`
- `src/pbui/__init__.py` or `src/pbui/__main__.py`
- `src/pbui/substrate.py`, `src/pbui/text.py`, `src/pbui/commands.py`, or
  `src/pbui/terminal.py`
- `tests/test_substrate.py` or `tests/test_terminal.py`
- another production module or test module
- anything under `docs/`, including this checkpoint, the specification, and
  earlier checkpoints
- any file outside the project root

If the model appears to require a filesystem/process service, drawing-context
change, history edit, Textual code, or new dependency, stop and return the
checkpoint for correction instead of widening the slice.

## Preserved behavior

Preserve all listener 005 and listings 000 behavior, including:

- the current six working commands and their exact parsing, effects, errors,
  presentation accepts, chips, and translators;
- current `ls` and `ps` capture and row text as a temporary predecessor state;
- current path and process inspection seams and fresh `show` behavior;
- existing `File`, `Directory`, `Process`, `Text`, and `Error` values, drawers,
  formatting helpers, and exact meanings;
- exact registry-identity acceptance rather than Python subtype acceptance;
- history ownership, replacement, revision, retention, and eviction;
- all terminal drawing, interaction, styling, and lifecycle behavior; and
- the 500-logical-row default.

The only currently observable listener composition change is that its domain
registry contains the two additional exact type tokens. They are inert in this
checkpoint: no command produces or accepts them and no translator is
registered for them.

## Exact domain types

Extend `DomainTypes` and `register_domain_types` with exactly these two entries:

- `DirectoryListing`, exposed by a `directory_listing` field; and
- `ProcessListing`, exposed by a `process_listing` field.

Register them after the five existing types, so iteration yields:

```text
File
Directory
Process
Text
Error
DirectoryListing
ProcessListing
```

Do not add `User`, `MenuAction`, or another domain type. `MenuAction` is a
private transient terminal type in a later screen checkpoint, not part of
`DomainTypes`.

The two listing tokens are not compatible with their member tokens. Do not add
them to the acceptable type set for `show`, `cd`, `rm`, or `kill`, and do not
register a default-click translator for either. Do not add listing drawers in
this checkpoint; the complete table header becomes their visible form in the
table-text layer.

Extend public type aliases and exports as needed so the two listing values can
legitimately be stored with their exact tokens later. Do not weaken an exact
value union to unconstrained `Any` merely to accommodate them.

## Cached directory members

Add one frozen, slotted record for a captured directory member. A concise name
such as `DirectoryListingMember` is preferred. Each record contains only:

- the original absolute `FileRef` or `DirectoryRef`;
- the full escaped displayed basename used by listing operations;
- the cached byte size for a file, or `None` for a directory; and
- the cached mtime rounded to an integer number of seconds.

Validate exact shapes at construction:

- the reference is exactly `FileRef` or `DirectoryRef`;
- the displayed basename is a string;
- a file has a nonnegative exact integer size;
- a directory has `None` size; and
- mtime is an exact integer, with `bool` rejected. Negative timestamps remain
  valid because host files may predate the Unix epoch.

The record does not hold a filesystem service, raw `stat_result`, absolute
display name, formatted timestamp, history row, fragment, or presentation.
Escaping, classification, followed-`stat`/broken-link `lstat`, and rounding are
capture responsibilities for the next checkpoint. Timestamp formatting and
column fitting belong to the table-text layer.

## Cached process members

Add one frozen, slotted record for a captured process member, preferably
`ProcessListingMember`. Each record contains only:

- the original `ProcessRef` with its canonical integer pid;
- the canonical readable state word;
- the real uid as a nonnegative exact integer;
- the already escaped displayed user; and
- the full already escaped command text.

The allowed state words are exactly:

```text
running  sleeping  disk-sleep  stopped  tracing
zombie  dead  idle  unknown
```

Reject another state word, a boolean uid, a negative uid, or non-string user
and command fields. Do not truncate the cached user or command. This record
does not consult `pwd`, `/proc`, or `ProcessService`, and it does not introduce
a `User` value or presentation.

## View state

Represent the three independent view choices explicitly:

- `sort_key`;
- `substring_filter`, either a nonempty string or `None`; and
- `kind_filter`, either an allowed word for that listing kind or `None`.

A small frozen, slotted `ListingView` value is preferred. A listing replaces
its complete view value only after an operation validates, so an invalid
operation cannot leave partial state.

Default views are:

- directory: `sort_key="name"`, no substring filter, no kind filter;
- process: `sort_key="pid"`, no substring filter, no kind filter.

Reject an empty-string substring filter as model input; `None` means absent.
Do not strip, case-fold, normalize, parse, or otherwise change a supplied
nonempty substring. Internal and trailing spaces are data.

## Stable listing values

Add mutable-by-view, identity-compared, slotted `DirectoryListing` and
`ProcessListing` values.

A `DirectoryListing` owns:

- the exact `DirectoryRef` that was listed;
- one tuple of `DirectoryListingMember` captured once; and
- its current directory view.

A `ProcessListing` owns:

- one tuple of `ProcessListingMember` captured once; and
- its current process view.

Defensively convert a supplied member iterable to a tuple once during
construction. Reject a member of the wrong record type. Never expose a mutable
member collection or replace the captured tuple during a view operation.

Listing equality must be object identity, not structural equality. The listing
object itself is the stable listing identity that later rows pass as
`listing_owner`; no UUID, parsed label, or second identity registry is needed.
Its identity and captured member objects survive every view change.

Do not add stable header/member `Presentation` objects in this checkpoint.
They will be created exactly once when the next checkpoint integrates capture,
using these same listing and member values. This split must not invent a
parallel presentation or history model.

## Pure directory view operations

Expose one coherent model path, whether methods or small functions, that can:

- replace the sort key;
- replace the substring filter;
- replace the kind filter;
- clear both filters while preserving the sort key; and
- return the currently visible members.

Directory sort keys are exactly `name`, `size`, and `mtime`.

- `name`: full cached escaped basename ascending by case-sensitive Unicode
  code-point order.
- `size`: files first by numeric byte size descending; directories after every
  file; ties within both groups by cached displayed basename ascending.
- `mtime`: cached integer timestamp descending; ties by cached displayed
  basename ascending.

Directory kind words are exactly `files` and `directories`, selected by the
exact member reference class. Substring matching is case-sensitive containment
in the full cached escaped basename. It never examines the absolute path,
size, or timestamp.

Apply both active filters before sorting. Replacing one view choice preserves
the other two. `widen` clears both filters and preserves the current sort key.
An invalid sort key, kind word, or empty substring raises a model validation
error and leaves the whole prior view unchanged.

## Pure process view operations

Process sort keys are exactly `pid`, `state`, and `command`.

- `pid`: canonical integer pid ascending.
- `state`: cached state word ascending by Unicode code-point order, then pid
  ascending.
- `command`: full cached escaped command ascending by Unicode code-point
  order, then pid ascending.

Every process sort, including `pid`, has pid as its deterministic final key.
Process kind words are the nine allowed state words. Substring matching is
case-sensitive containment in the full cached escaped command. It never
examines pid, state, uid, displayed user, or a future truncated command cell.

The same replacement, combination, `widen`, and atomic validation rules as the
directory view apply. Empty results are an ordinary empty tuple; explanatory
history text belongs to the later table layer.

## No host refresh

The public visible-member operation and all four view mutations are pure with
respect to host state. They must not:

- call `os.stat`, `os.lstat`, `os.scandir`, `os.path.basename`, or a filesystem
  service;
- call `pwd.getpwuid` or another password-database API;
- read `/proc`, inspect a process, or call a process service;
- call `escape_display` again; or
- reconstruct a value by parsing cached display text.

They use only the exact references and cached scalar fields already present in
the listing. A later `show` remains free to inspect the original reference
freshly; that command is outside this checkpoint.

## Automated tests

Extend `tests/test_domain.py`, plus only the narrow registry/translator
assertions allowed in `tests/test_commands.py`. Keep all 107 predecessor tests
without deletion, weakening, or replacement.

### Types and construction

Prove at least:

- registry iteration has the exact seven names and old type objects retain
  their exact roles;
- both listing types have no translator and are absent from every existing
  command accept set;
- member records reject every wrong exact shape described above;
- input member iterables are consumed once into immutable tuples;
- listing values compare by identity even when their captured data is equal;
- a listing object, its member tuple, and each member object retain identity
  across every view operation; and
- the two default views are exact.

Do not add a listing presentation or drawer merely to test type registration.

### Directory views

Use cached members chosen to distinguish all ordering rules. Cover:

- default case-sensitive name order;
- descending file size, directory blanks after all files, and name tie breaks;
- descending mtime across files and directories with name tie breaks;
- `files` and `directories` filters;
- substring matching only the cached displayed basename;
- combined substring and kind filters;
- replacement of each filter while preserving the other and the sort key;
- `widen` clearing both filters while preserving a nondefault sort key;
- an empty visible result; and
- each invalid mutation leaving the complete prior view unchanged.

Include an absolute path containing text that is absent from its cached
basename and prove `narrow` does not match that path text.

### Process views

Use repeated states and commands at different pids. Cover:

- default numeric pid order;
- state and full-command sorts with pid tie breaks;
- each of the nine state filters, with representative members sufficient to
  exercise them without live processes;
- substring matching only the full cached escaped command;
- a match occurring beyond where the future 48-cell table field will truncate;
- combined filters, replacement, `widen`, and an empty result; and
- invalid operations leaving view and member identities unchanged.

Give pid, user, and state fields text that would match a chosen substring if
the implementation searched the wrong field, and prove they do not match.

### Purity guard

After constructing the cached values, monkeypatch or inject failure sentinels
for the relevant filesystem, password-database, process, basename, and escape
operations that are reachable from `pbui.domain`. Exercise every sort/filter
path and prove no sentinel is called. Tests use no live filesystem metadata,
password database, or `/proc` data and contain no timing assertion.

## uv workflow and verification

Add no dependency. Use only the existing uv-managed project:

```console
uv sync
uv run pytest
```

All 107 predecessor tests plus the new listings 001 tests must pass. Do not use
`pip`, `python -m pip`, `uv pip install`, Poetry, Pipenv, Conda, Hatch, a
hand-made virtual environment, or a globally installed Python. If `uv` is
unavailable, stop and tell the human.

No `uv run pbui`, physical-terminal hand check, live `/proc` exercise,
dependency edit, or documentation edit is required for this pure headless
checkpoint.

## Completion boundary

Listings 001 is complete only when the registry has the two exact inert
listing types, both listing values retain one immutable captured member tuple,
all specified directory/process view operations are deterministic and use
only cached fields, invalid operations are atomic, and the full automated suite
passes.

Stop there. Do not capture host data; create header or member presentations;
append or replace listing history rows; add `sort`, `narrow`, `only`, or
`widen` to the command registry; add table text; consult `pwd`; add action
menus, colors, viewport anchors, substring accept, or change any terminal
behavior.
