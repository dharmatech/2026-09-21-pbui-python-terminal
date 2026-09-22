# listings 003 — View commands and in-place redisplay

**Status.** Ready to implement.

## Goal

Complete the headless listing-model layer. Add `sort`, `narrow`, `only`, and
`widen`; target the newest retained listing for typed input or an explicitly
supplied older listing for later menu use; change its pure view; and atomically
replace its owner block at the same history position using the stable captured
member presentations.

Also add the UI-independent state for the modal textual substring accept that
begins when typed `narrow` has no argument. The terminal's prefix,
documentation, event handling, and drawing remain deferred.

This checkpoint retains the transitional predecessor member-row wording and
empty literal placeholder from listings 002. Stop when headless dispatch and
redisplay are green; do not begin final table text or terminal work.

## Identity, authority, and predecessors

- Identity is `(listings, 003)`, spoken **listings 003**.
- [`../spec.md`](../spec.md), especially sections 2.3, 3.3, 4, 7.1, and 8,
  is the design authority. Preserve the accepted listener behavior when this
  checkpoint is silent.
- Listings 000 supplies owner blocks and atomic
  `replace_listing_rows`.
- Listings 001 supplies cached listing values and deterministic view
  operations.
- Listings 002 supplies atomic host capture, stable bound header/member
  presentations, and contiguous owner-marked predecessor rows.
- All predecessors are implemented and reviewed. The baseline suite has
  **136 passing tests**.
- This checkpoint finishes specification section 7.1. The next checkpoint may
  begin the pure table-text layer in section 7.2.
- The project root is
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application code
  and tests remain there, never under `docs/`.

## Exact file scope

### May edit

- `src/pbui/commands.py`
- `tests/test_commands.py`

### Must not edit or create

- `.python-version`, `pyproject.toml`, `uv.lock`, `README.md`, or `AGENTS.md`
- `src/pbui/__init__.py` or `src/pbui/__main__.py`
- `src/pbui/domain.py`, `src/pbui/substrate.py`, `src/pbui/text.py`, or
  `src/pbui/terminal.py`
- `tests/test_domain.py`, `tests/test_substrate.py`, or
  `tests/test_terminal.py`
- another production module or test module
- anything under `docs/`, including this checkpoint, the specification, and
  earlier checkpoints
- any file outside the project root

If the headless command work appears to require a table formatter, history
redesign, Textual edit, or new dependency, stop and return the checkpoint for
correction instead of widening the slice.

## Preserved behavior and transitional rows

Preserve exactly:

- listings 000 history validation, replacement, reference counts, revision,
  intervals, and row-based eviction;
- listings 001 captured values, view validation, sort/filter semantics, and
  identities;
- listings 002 host capture, username lookup, presentation binding, owner
  blocks, and capture failure atomicity;
- the existing parsing, accepts, chips, effects, revalidation, refusals,
  errors, and translators of `ls`, `ps`, `show`, `kill`, `cd`, and `rm`;
- click-to-show behavior for member presentations outside a pending textual
  substring accept;
- listener 005 layout and targeted hover drawing; and
- all terminal interaction and lifecycle behavior.

Redisplay in this intermediate checkpoint deliberately uses the listings 002
surface:

- a visible directory member is `file       NAME` or `directory  NAME`;
- a visible process member is `PID  STATE  FULL_ESCAPED_COMMAND`;
- an underlying empty directory is the existing exact
  `Directory is empty: ABSOLUTE_PATH` text;
- an empty process listing, or a nonempty listing with no visible members,
  uses one empty literal owner row with no presentation; and
- the stable header presentation remains owned but absent from history.

Do not add either final header, final explanatory no-process/no-match text,
columns, widths, timestamps, users, or truncation here. Listings 004 will
replace this transitional row builder without changing command semantics.

## Complete command registry

The exact typed command registry becomes:

```text
ls  ps  show  kill  cd  rm  sort  narrow  only  widen
```

Preserve that order in `command_names`. The four new names are ordinary
registered commands, not evaluator forms and not presentation accepts. Do not
add shell syntax, quoting, globbing, completion, history, or another command.

The existing first-word/rest-of-line split remains authoritative: it discards
the separator run between the command and its argument, preserves internal and
trailing spaces in a `narrow` argument, and adds no quoting or escape grammar.

## Target selection

Add one identity-based retained-listing resolver shared by typed view
commands. Scan retained logical history newest to oldest and return the first
row owner whose exact class is `DirectoryListing` or `ProcessListing`.

- The row may be a member, explanatory row, or temporary empty row.
- The listing remains a valid target when only a suffix of its owner block is
  retained after row eviction.
- Do not require its unrendered header presentation to be retained.
- Ignore unowned rows and any unrelated opaque owner.
- Do not keep a separate newest-listing pointer or registry.

If no listing has a retained row, a typed view command appends exactly:

```text
Error: no listing in history.
```

and changes no view. As elsewhere, `_append_error` receives the unprefixed
message. Resolve this target before validating that command's argument, so the
no-listing error takes precedence for every typed view command when history
contains no retained listing.

Expose one canonical explicit-target operation for the later action menu. It
accepts an exact retained listing object, operation, and argument and routes
through the same mutation/redisplay path as typed input. It must not rescan and
silently substitute the newest listing. Reject an explicit target that has no
retained owner row; the terminal menu will only supply retained targets.

## Command grammar and exact errors

Implement these typed forms:

| Command | Argument | Success |
|---|---|---|
| `sort` | exactly one word | Replace sort key and redisplay. |
| `narrow` | one nonempty rest-of-line string | Replace substring filter and redisplay. |
| `only` | exactly one word | Replace kind filter and redisplay. |
| `widen` | none | Clear both filters, preserve sort key, and redisplay. |

Successful direct commands append no confirmation row and clear ordinary
input/chip state.

For `sort` or `only`, a missing argument or any argument containing whitespace
appends respectively:

```text
Error: sort requires one key.
Error: only requires one word.
```

`widen` with any argument appends:

```text
Error: widen does not take an argument.
```

An inapplicable but grammatically single sort word appends one exact error:

```text
Error: cannot sort this directory listing by KEY.
Error: cannot sort this process listing by KEY.
```

An inapplicable but grammatically single kind word appends:

```text
Error: cannot apply only WORD to this directory listing.
Error: cannot apply only WORD to this process listing.
```

Safely escape `KEY` and `WORD` exactly once in these messages. Invalid grammar
or value leaves the listing's complete prior `ListingView` unchanged. The
error row is unowned; normal history eviction caused by appending it still
applies.

Directory and process allowed words remain exactly those validated by the
listings 001 model. Do not duplicate sorting/filtering algorithms in the
command layer; call the listing operations.

## Modal substring accept state

Typed `narrow` without an argument first resolves the newest retained listing.
If resolution succeeds, enter a small headless textual-accept state bound to
that exact listing:

- the editable buffer is the listener's existing `input_text` and starts
  empty;
- retain the bound listing in a dedicated property/state field;
- `pending_request` remains `None` because this is not presentation accept;
- `chip` remains `None`;
- history and the listing view do not change on entry; and
- a second host read never occurs.

When this state is active, `submit` treats the complete current input buffer as
the substring, not as a command line. This preserves leading, internal, and
trailing spaces typed into the modal buffer.

- Enter/submit with an empty buffer remains in the state and changes nothing.
- A nonempty buffer applies `narrow` to the bound listing through the canonical
  explicit-target operation, redisplays, then clears the buffer and pending
  target.
- `cancel()` clears buffer and target, restores ordinary input state, changes
  no view or history, and appends nothing.
- A pending substring target blocks presentation accept and default
  translators: `select` returns false and does not run `show`.

If the target loses its final owner row before completion, applying the buffer
must fail safely without mutating the listing: clear the modal target and
buffer, leave history unchanged, and return an internal unsuccessful result if
the API returns a result. Do not invent user-visible wording for this
externally induced edge case.

Expose enough read-only state for the later terminal layer to distinguish
ordinary input, presentation accept, and substring accept. Do not implement
the non-editable `narrow ` prefix, documentation sentence, Ctrl-G/Escape key
precedence, or styling in `terminal.py` here.

## Canonical view operation

Typed direct commands, modal substring completion, and the future menu must
share one operation function. Given a retained exact listing, operation, and
validated argument, it must:

1. Confirm the explicit target still owns at least one retained row.
2. Validate the requested word before mutating the listing.
3. Apply the corresponding listings 001 mutation.
4. Build a full replacement block using only `visible_members`, cached scalar
   fields, and the listing's already-bound stable presentations.
5. Call `replace_listing_rows(listing, replacement_rows)` exactly once.

The command layer may validate words before model mutation to select the exact
product error, but it must not implement its own sort or filter.

Build member-to-presentation alignment by captured object identity, not by
parsing text or structural equality. Every visible row carries the exact
stable presentation aligned with that member and `listing_owner is listing`.
A filtered-out presentation may leave retained history, but remains owned by
the listing and must be the same object when `widen` or a replacement filter
makes it visible again.

For transitional empty rows:

- underlying empty directory plus no active filters uses the existing empty
  directory text;
- any nonempty captured sequence with zero visible members uses one empty
  literal row;
- an empty process capture uses one empty literal row; and
- every replacement contains at least one owner row.

The replacement occurs at the existing block index, appends no duplicate at
the newest end, preserves outside row objects except normal oldest-row
eviction, increments history revision once, and never forces a host refresh.

## Capture is still the only refresh

After a listing is captured, all four view commands and substring completion
must avoid:

- filesystem `stat`, `lstat`, directory iteration, or basename work;
- re-escaping any cached listing name, command, or user field (escaping a
  newly typed invalid `KEY` or `WORD` for its required error remains correct);
- password-database lookup;
- process enumeration or inspection; and
- reconstruction from displayed row text.

Use cached escaped names, states, full commands, references, sizes, mtimes, and
users already owned by the listing. `show` remains a separate fresh inspection
and is unchanged.

## Automated tests

Extend `tests/test_commands.py`. Keep all 136 predecessor tests without
deletion, weakening, or replacement. Update the exact command-registry
assertion to ten names.

### Grammar and errors

Cover every success form and exact error above for both listing kinds,
including:

- missing and whitespace-containing `sort`/`only` arguments;
- `widen` with an argument;
- each valid sort and kind word;
- cross-kind invalid words and safely escaped invalid words;
- `narrow` preserving internal and trailing spaces; and
- every invalid command leaving the prior view unchanged.

Prove a view command with no retained listing appends only the exact no-listing
Error and clears ordinary input state.

### Targeting and replacement

Create at least two retained listings with an unowned history row between
them. Prove:

- typed input targets the newest retained listing;
- the explicit-target operation can change the older listing without changing
  the newer one;
- each replacement stays at its old logical index and preserves every outside
  row object;
- no successful operation appends a confirmation or duplicate block;
- one operation increments revision exactly once;
- a partially retained listing remains a typed target;
- a completely evicted listing is not targetable; and
- replacement still enforces the 500/configured logical-row bound.

Exercise a filter that removes a member and then `widen`; assert the
reappearing row uses the exact same `Presentation` object and original stored
reference. Repeat for process and directory members.

### View semantics through commands

Do not merely repeat model-unit tests. Through submitted commands prove:

- default and alternate sorts produce the expected transitional row order;
- directory size puts every directory after every file;
- all deterministic tie breakers survive redisplay;
- directory `narrow` searches only cached displayed basename;
- process `narrow` and command sort use the full cached command, including a
  match beyond the future 48-cell field;
- substring and kind filters combine; and
- `widen` clears both while preserving the nondefault sort key.

### Modal substring state

Prove:

- `narrow` with no argument binds the newest listing, clears the editable
  buffer, creates no chip/presentation accept, and changes no history;
- empty submit remains pending;
- a nonempty buffer including leading/trailing spaces applies to the original
  bound listing even if a newer listing would otherwise exist;
- cancel clears state with exact view/history identity preserved;
- member selection is inert while pending and returns to ordinary translator
  behavior after cancel; and
- loss of the target block before completion does not mutate its view or
  corrupt listener state.

### No refresh and regressions

Use the listings 002 counting filesystem, fixed process service, and username
lookup counters. Snapshot call counts after capture, then exercise every view
operation, explicit older targeting, removal/reappearance, and modal
completion. Assert no counter changes.

Keep `show`, `cd`, `rm`, `kill`, chips, exact type acceptance, stale object
behavior, empty capture ownership, and capture failure tests green.

## uv workflow and verification

Add no dependency. Use only the existing uv-managed project:

```console
uv sync
uv run pytest
```

All 136 predecessor tests plus the new listings 003 tests must pass. Do not use
`pip`, `python -m pip`, `uv pip install`, Poetry, Pipenv, Conda, Hatch, a
hand-made virtual environment, or a globally installed Python. If `uv` is
unavailable, stop and tell the human.

No `uv run pbui`, physical-terminal hand check, live `/proc` exercise,
dependency edit, or documentation edit is required for this headless
checkpoint.

## Completion boundary

Listings 003 is complete only when the ten-command registry is exact, typed
and explicit targets share one cached-data operation path, successful view
changes replace one owner block in place with stable presentations, all exact
errors and modal substring behavior hold, no view action refreshes host data,
and the full automated suite passes.

Stop there. Do not add final table text or headers; make header presentations
visible; add column fitting, timestamps, users, or truncation; add action menus,
colors, viewport anchors, documentation sentences, or terminal input-event
handling.
