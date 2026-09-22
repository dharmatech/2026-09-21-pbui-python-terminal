# listings 004 — Table text and whole-row presentations

**Status.** Ready to implement.

## Goal

Replace the transitional listing rows with the complete pure directory and
process tables. Draw exact headers and explanatory rows, fit every cell in
terminal display columns, expose cached size/mtime/user data, truncate only
the specified process cells, and make each stable header/member presentation
span its complete printed row.

Initial capture and every in-place redisplay must call the same pure table-row
builder. This checkpoint changes no view semantics, host capture, command
grammar, action menu, styling, viewport behavior, or terminal input event.

## Identity, authority, and predecessors

- Identity is `(listings, 004)`, spoken **listings 004**.
- [`../spec.md`](../spec.md), especially sections 2.2, 2.3, 3, 4.4, 6.1,
  7.2, and 8, is the design authority. Preserve the rest of that specification
  when this checkpoint is silent.
- Listings 000 through listings 003 are implemented and reviewed. Together
  they supply owner-block replacement, cached listing models, atomic capture,
  stable bound presentations, the ten commands, target selection, modal
  substring state, and cached in-place redisplay.
- The baseline suite has **166 passing tests**.
- This checkpoint is the complete table-text layer from specification section
  7.2. The next checkpoint may begin screen/menu work.
- The project root is
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application code
  and tests remain there, never under `docs/`.

## Exact file scope

### May edit

- `src/pbui/text.py`, only for shared pure display-width/truncation helpers
- `src/pbui/domain.py`
- `src/pbui/commands.py`
- `src/pbui/terminal.py`, only to consume and re-export the shared pure helpers
  with no behavior change
- `tests/test_domain.py`
- `tests/test_commands.py`
- `tests/test_terminal.py`, only for compatibility assertions around the moved
  display helpers

### Must not edit or create

- `.python-version`, `pyproject.toml`, `uv.lock`, `README.md`, or `AGENTS.md`
- `src/pbui/__init__.py` or `src/pbui/__main__.py`
- `src/pbui/substrate.py`
- `tests/test_substrate.py`
- another production module or test module
- anything under `docs/`, including this checkpoint, the specification, and
  earlier checkpoints
- any file outside the project root

If exact table text appears to require a host read, history redesign, Textual
surface, new dependency, or menu/style behavior, stop and return the checkpoint
for correction instead of widening the slice.

## Preserved behavior

Preserve exactly:

- listings 000 owner identity, atomic replacement, reference counts, revision,
  interval invalidation, and row-based eviction;
- listings 001 captured values and all deterministic sort/filter semantics;
- listings 002 capture fields, symlink seams, username lookup/fallback, stable
  presentation binding, and capture failure atomicity;
- listings 003 command registry, parsing, exact errors, typed/explicit target
  selection, modal substring state, no-confirmation success, and no-refresh
  behavior;
- existing `show`, `cd`, `rm`, and `kill` behavior and member translators;
- exact type acceptance, chips, stale object behavior, and the original stored
  member references;
- listener 005 direct physical-row construction and targeted hover cost; and
- all current terminal events, documentation, base styling, scrolling,
  anchoring, prompt, and lifecycle behavior.

Only table blocks change their logical text and presentation spans. Do not add
semantic colors, bold headers, truncated-command documentation, listing-header
documentation, right click, Ctrl-O, a menu surface, or terminal substring
rendering in this checkpoint.

## Shared display-cell helpers

Table sizing uses terminal display cells, never Python character count.
`src/pbui/terminal.py` already has reviewed `display_width` and
`truncate_display` behavior for wide and combining characters. Move or factor
that implementation into the Textual-free `pbui.text` layer so pure domain
table code can use it.

- Keep `wcwidth` as the existing dependency; add none.
- Preserve the current public imports from `pbui.terminal` by importing and
  re-exporting the shared helpers there.
- Preserve every existing helper test and terminal output.
- Zero-width marks remain grouped with the preceding drawn character during
  truncation.
- Wide characters occupy two cells and are never split.
- Already-sanitized negative-width characters are treated harmlessly exactly
  as the reviewed terminal helper does.
- `truncate_display` continues returning text no wider than its requested
  bound; do not silently change its existing general behavior merely to pad a
  table cell.

Add small pure cell helpers in `pbui.domain` as needed for left/right padding
and fixed-cell ellipsis. Padding is ASCII spaces. For a truncated fixed-width
process cell, the ellipsis must occupy the final display cell. If a wide
cluster cannot consume the last pre-ellipsis cell, insert ASCII padding before
the ellipsis rather than splitting that cluster or placing the ellipsis early.

No Rich markup parsing or Textual import may enter `pbui.text` or
`pbui.domain`.

## Pure table-row builders

Add one pure row builder for an exactly bound `DirectoryListing` and one for an
exactly bound `ProcessListing`. A concise interface such as
`directory_listing_rows(listing)` and `process_listing_rows(listing)` is
preferred.

Each builder:

- reads only the listing, its cached member/view fields, and its already-bound
  stable presentations;
- returns one nonempty tuple of `HistoryRow` values;
- sets `listing_owner is listing` on every returned row;
- uses the exact stable header presentation for the first row;
- aligns visible members to their exact stable presentations by captured
  object identity, never parsed labels or structural equality;
- allocates no new `Presentation` and changes no listing view;
- performs no filesystem, password-database, process, basename, or escaping
  operation; and
- is deterministic for equal captured values and view state.

Construct a complete printed row as the children of one `PresentedFragment`
carrying the stable presentation id. Put that exact `Presentation` in the
row's presentation tuple. There is no literal prefix or padding outside the
presentation. Thus every column, separator, padding cell, and trailing cell in
a header/member row belongs to the same presentation.

Explanatory rows are literal fragments with no presentation. They still carry
the listing owner. Do not create Text or Error presentations for them.

An unbound pure listing raises a clear model/programming error if passed to a
table builder. Do not allocate missing presentations inside the builder.

## Directory table

The literal header cells are:

```text
name  size  modified
```

Columns are separated by exactly two ASCII spaces.

### Name column

- Left aligned.
- Width is the greatest of four display cells and every currently visible
  cached escaped basename width.
- Names are never truncated.
- A short value is padded on the right with ASCII spaces.

### Size column

- Right aligned.
- Width is at least 12 display cells and widens to the widest currently
  visible file's ungrouped base-10 byte count.
- A file displays `str(size)` with left padding.
- A directory displays exactly the full column width in spaces.
- The header label `size` is right aligned in the same width.

### Modified column

- Left aligned and exactly 20 display cells.
- A member displays its cached integer mtime in UTC as
  `YYYY-MM-DDTHH:MM:SSZ`, through the existing pure timestamp formatter.
- The header label `modified` is left aligned and padded to 20 cells.

The complete header row is the listing's stable `DirectoryListing`
presentation. Each complete member row is its aligned stable `File` or
`Directory` presentation.

Column widths use only currently visible members, so filtering may change the
name or size width. Sorting alone does not change a width for the same visible
set. A filename may make the logical row much wider than the terminal; normal
pure layout wrapping handles that later and the name remains untruncated.

## Process table

The literal header cells are:

```text
pid  state  user  command
```

Columns are separated by exactly two ASCII spaces. The fixed cells are:

| Cell | Width | Alignment and overflow |
|---|---:|---|
| `pid` | 10 | Right; full canonical decimal pid. |
| `state` | 10 | Left; full canonical state word. |
| `user` | 16 | Left; truncate with `…` in the final cell. |
| `command` | 48 | Left; truncate with `…` in the final cell. |

Every shorter cell, including every header cell, is padded to its width with
ASCII spaces. The command field is last and therefore leaves its required
trailing padding in the logical row. Production Linux pids and all canonical
state words fit; reject an impossible over-width cached pid/state rather than
silently widening or truncating those columns.

Truncation is display-column aware. It never splits a two-cell character or
separates a zero-width mark from its base. The listing retains the complete
cached escaped user and command; only the row cell is shortened. Existing
sort, `narrow`, and fresh `show` behavior must continue consuming full values.

The complete header row is the stable `ProcessListing` presentation. Each
complete member row is its aligned stable `Process` presentation. User text is
literal content within the process presentation, never a nested or separate
`User` presentation.

## Explanatory rows

Every table always starts with its header presentation, even when no member is
visible.

For a directory listing whose captured sequence is empty, append this exact
literal row regardless of current filters:

```text
Directory is empty: ABSOLUTE_PATH
```

Use the existing safe `format_empty_directory` result for `ABSOLUTE_PATH`.

For a process listing whose captured sequence is empty and neither substring
nor kind filter is active, append:

```text
No processes are available.
```

If a nonempty captured sequence has no visible member after filtering, append:

```text
Nothing matches the active filters.
```

For an empty process capture with a substring or kind filter active, also use
`Nothing matches the active filters.`; it is no longer the unfiltered empty
state. A changed sort key alone is not an active filter and retains
`No processes are available.`

Each explanatory row is one logical row, carries the listing owner, and has no
presentation or clickable interval.

## Command integration

Delete the transitional table-row construction from `HeadlessListener` and
route both successful capture and every listings 003 redisplay through the
same pure builder selected by exact listing class.

- Initial `ls`/`ps` appends the complete returned block, including header.
- A view operation passes the complete returned block once to
  `replace_listing_rows`.
- Stable header/member presentations created in listings 002 are reused; no
  row rebuild presents a value again.
- A header filtered out by row eviction remains owned by the listing and is
  the exact presentation reused if later redisplay restores the full block.
- Successful operations still append no confirmation and preserve outside row
  objects.
- Every block contains at least header plus a member or explanatory row before
  ordinary history-bound eviction.

Remove the temporary empty process/no-match row. Do not retain a compatibility
path that can still emit the predecessor `file       NAME` or
`PID  STATE  COMMAND` listing surface.

Header presentations remain inert for click translation and presentation
accept in this checkpoint. Existing member clicks still pass the original
stored object even from a size, timestamp, state, user, command, separator, or
padding cell.

## Automated tests

Extend the allowed test files while keeping all 166 predecessor tests without
deletion, weakening, or replacement. Update assertions that intentionally
describe the superseded transitional listing text.

### Shared display helpers

Keep all reviewed terminal truncation tests green after factoring. Add pure
coverage as needed for:

- ASCII, wide, and combining display widths;
- truncation without splitting a wide character;
- keeping combining marks with their base; and
- fixed-cell padding that places `…` in the final display cell even when the
  preceding rejected cluster is wide.

Do not add timing or terminal-emulator-dependent assertions.

### Directory text

Use constructed cached listings and command-integrated captures to prove:

- exact header text and two-space separators;
- four-cell minimum and visible-name-derived name width;
- left name alignment and an arbitrarily long untruncated filename;
- 12-cell right-aligned size, a widened over-12-digit size, and a completely
  blank directory size cell;
- exact UTC timestamp text from cached whole seconds, including epoch;
- right-aligned `size` and left-aligned `name`/`modified` header labels;
- wide and combining basenames align following columns by display cells;
- filtering recomputes widths from only visible members;
- empty and no-match explanatory rows are exact and non-presented; and
- full header/member row spans hit their stable presentation in every printed
  cell, including padding, separators, size, mtime, and trailing cells.

### Process text

Prove:

- the exact 10/10/16/48 header and member cells with two-space separators;
- right pid and left state/user/command alignment;
- username success and decimal-uid fallback appear literally in the user cell;
- short cells are ASCII padded;
- long user and command values end with an ellipsis in their final cell;
- wide and combining text truncates without splitting or detaching marks;
- the displayed command may truncate while sort and `narrow` still use its
  complete cached value beyond cell 48;
- `show` still performs its fresh full-command inspection;
- empty/no-match sentences are exact and non-presented; and
- clicking/hit-testing any printed cell of a member row returns the same
  stable `Process` presentation, with no User presentation anywhere.

### Identity, replacement, and no refresh

Across initial capture, sorting, filtering, no-match, and `widen`, assert:

- the retained header is the listing's exact stable header presentation;
- a disappearing/reappearing member is the exact stable presentation;
- blocks replace in place with outside row identities preserved;
- every row owner is the listing;
- one view operation increments revision once;
- no host/password/process/escape counter used for cached member fields
  changes; and
- row-based history retention still permits a partially retained table target
  and complete eviction removes it from target selection.

Keep every existing command, modal substring, capture-failure, stale-object,
listener 005 drawing, and terminal lifecycle regression green.

## uv workflow and verification

Add no dependency. Use only the existing uv-managed project:

```console
uv sync
uv run pytest
```

All 166 predecessor tests plus the new listings 004 tests must pass. Do not use
`pip`, `python -m pip`, `uv pip install`, Poetry, Pipenv, Conda, Hatch, a
hand-made virtual environment, or a globally installed Python. If `uv` is
unavailable, stop and tell the human.

No `uv run pbui`, physical-terminal hand check, live `/proc` exercise,
dependency edit, action-menu test, or new terminal interaction test is required
for this pure table checkpoint.

## Completion boundary

Listings 004 is complete only when every captured listing and redisplay uses
the exact final table text; column widths and truncation are display-cell
correct; the stable header and member presentations span whole rows;
explanatory rows are exact and inert; full cached values still drive sort,
filter, and `show`; no view operation refreshes host data; and the full suite
passes.

Stop there. Do not add semantic colors, bold headers, documentation sentences,
right click, Ctrl-O, an action menu, menu actions, viewport-anchor changes,
terminal modal-prefix/event behavior, or the live hand check.
