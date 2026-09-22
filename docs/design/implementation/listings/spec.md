# Specification — listings you can redisplay

**Status:** proposed specification, ready for human review. This specification
extends the accepted presentation-listener specification through listener 005.
It is the complete design input for the later listings checkpoint series; the
charter is not an implementation input.

`ls` and `ps` now append object-bearing table listings. A listing retains the
objects captured by that command and a view over those objects. `sort`,
`narrow`, `only`, and `widen` change the view and replace the listing's rows at
their existing history position. A transient action menu exposes the same
operations as typed commands.

This document supersedes these parts of the listener specification:

- section 1's six-command registry, popup-menu prohibition, and prohibition on
  right-click actions;
- section 4's statement that there are exactly five presentation types;
- section 4.3's `ls` and `ps` row wording and its statement that those outputs
  have no header;
- sections 5 and 5.1 where command dispatch is limited to six commands;
- section 6's three-region description while the transient menu is open;
- sections 6.2–6.4 where this document adds documentation sentences, colors,
  and input events.

All other listener behavior remains required. In particular, the retained
history contains values rather than parsed labels; exact presentation-type
acceptance, chips, safe display escaping, path and process seams, command
refusals and effects, terminal restoration, and listener 005's drawing rule do
not change.

## 1. Product and project boundary

The project remains a Linux, Python 3.11-or-newer, full-screen Textual
application at:

```text
/home/dharmatech/journal/2026-09-21-pbui-python-terminal/
```

Application code stays under `src/pbui/`; tests stay under `tests/`; design
artifacts stay under `docs/design/implementation/listings/`. This exploration
does not create another Python project or another object model. Only
`pbui.terminal` imports Textual.

The complete typed command registry becomes:

```text
ls  ps  show  kill  cd  rm  sort  narrow  only  widen
```

There is still no evaluator, external command execution, shell grammar,
pipeline, redirection, quoting, globbing, command history, completion, rename,
copy, stop, continue, refresh command, text pipe, graphical presenter, icon,
or second per-row widget hierarchy. `User` is not a presentation type.

The existing uv-managed project is used unchanged. Every implementation
checkpoint runs:

```console
uv sync
uv run pytest
```

Only a terminal checkpoint also runs `uv run pbui` for its hand check. Add a
dependency with `uv add` or `uv add --dev` only if one is actually required;
prefer no new dependency. Never use `pip`, `python -m pip`, `uv pip install`,
Poetry, Pipenv, Conda, Hatch, a hand-made virtual environment, or a globally
installed package. If `uv` is unavailable, stop and report that fact.

## 2. Listing values and presentations

### 2.1 Explicit types

The retained domain type registry adds exactly two types to the five accepted
listener types:

| Type | Stored value | Role |
|---|---|---|
| `DirectoryListing` | one captured directory listing | Header and redisplay target for `ls` |
| `ProcessListing` | one captured process listing | Header and redisplay target for `ps` |

`File`, `Directory`, `Process`, `Text`, and `Error` retain their exact meanings.
Acceptance remains exact registry identity. A listing is not acceptable as a
file, directory, or process, and a member is not acceptable as a listing.

The terminal additionally registers one private, transient `MenuAction`
presentation type. Its values refer to canonical command operations. It is
never retained in listener history, never accepted into a chip, and does not
add a domain object or a typed command.

### 2.2 Captured data

A `DirectoryListing` owns:

- the `DirectoryRef` that `ls` listed;
- an immutable captured member sequence;
- one stable `File` or `Directory` presentation per member;
- cached escaped basename, classification, byte size where applicable, and
  UTC mtime for every member;
- a view containing a sort key, optional substring filter, and optional kind
  filter; and
- a stable listing identity used to find its rows in history.

The member value remains the original absolute `FileRef` or `DirectoryRef`.
For a live file or symlink target, size and mtime come from followed `stat`.
For a broken final symlink they come from `lstat`, as in `show`. Directories
have a cached mtime but their size cell is blank. Mtime is rounded to whole
seconds and formatted in UTC as `YYYY-MM-DDTHH:MM:SSZ`.

A `ProcessListing` owns:

- an immutable captured member sequence for the same processes that `ps`
  already includes;
- one stable `Process` presentation per captured pid;
- each member's canonical integer pid, readable state word, real uid,
  displayed user, and full escaped command text;
- the same three-part view state and stable listing identity.

At `ps` capture time, the displayed user is `pwd.getpwuid(real_uid).pw_name`
when that password-database entry exists; otherwise it is the decimal uid.
Lookup failure also falls back to the decimal uid. The result receives the
listener's one-row control-character escaping and is literal text, never a
`User` presentation.

The listing value owns one stable header presentation. Redisplay reuses that
header presentation and the stable member presentations; it never parses a
cell to reconstruct a value. A filtered-out member may have no current history
span, but the listing still owns its captured value and presentation. When the
last logical row owned by a listing is evicted, the listing and its otherwise
unreferenced presentations may be discarded.

### 2.3 Capture is the only refresh

A successful `ls` or `ps` captures fresh host data once and appends one new
listing. `ls` still revalidates its directory, includes dotfiles, omits only
`.` and `..`, follows the accepted classification rules, and does not change
cwd. `ps` still reads Linux `/proc`, filters to the listener's real uid, skips
unreadable or malformed entries, includes the listener when inspectable, and
never shells out.

Sort and filter use only captured fields. They do not call `stat`, read a
directory, consult the password database, or read `/proc` again. `show` keeps
its accepted behavior and performs a fresh inspection, so it can reveal a
changed file or process and the full current process command. Running a later
`ls` or `ps` appends a different listing containing newly captured data.

Host failure while capturing a listing appends the existing stable `Error`
form and appends no partial listing. Existing `show`, `cd`, `rm`, and `kill`
revalidation, refusals, effects, confirmations, and errors are unchanged.

## 3. Table text

All column widths are terminal display-cell widths computed with `wcwidth`,
not Python character counts. Combining marks stay with their base character,
wide characters occupy two cells, control characters are escaped before
measurement, and Rich markup parsing remains disabled. Columns are separated
by exactly two ASCII spaces. A table record is always one logical history row;
at a terminal narrower than the table it may become several physical rows by
the existing layout algorithm.

### 3.1 Directory table

The literal header cells are:

```text
name  size  modified
```

The name column is left aligned and has width equal to the greatest of four
cells and the display widths of all currently visible escaped basenames. Names
are never truncated. The size column is 12 cells and right aligned. It contains
an ungrouped base-10 byte count for a file and exactly 12 spaces for a
directory. If a byte count needs more than 12 cells, that view's size column
widens to fit it. The modified column is 20 cells and contains the UTC
timestamp. Header labels follow their columns' alignment.

The header's complete printed row is the `DirectoryListing` presentation. Each
complete member row—including name, padding, size, separators, and modified
time—is exactly one `File` or `Directory` presentation. Thus a click on size or
mtime is a click on the same stored object as a click on its name.

An underlying empty directory has the header followed by the existing exact
literal row:

```text
Directory is empty: ABSOLUTE_PATH
```

`ABSOLUTE_PATH` uses the existing safe display. If the captured sequence is
not empty but active filters leave no visible member, the header is followed
by the exact literal row:

```text
Nothing matches the active filters.
```

These explanatory rows belong to the listing's history block but contain no
clickable presentation.

### 3.2 Process table

The literal header cells are:

```text
pid  state  user  command
```

The columns are:

| Cell | Width | Alignment and overflow |
|---|---:|---|
| `pid` | 10 | Right; canonical decimal pid |
| `state` | 10 | Left; full existing state word |
| `user` | 16 | Left; truncate with `…` in the last cell |
| `command` | 48 | Left; truncate with `…` in the last cell |

Linux pids fit the 10-cell pid field. Truncation is display-column aware and
does not split a wide character or separate combining marks. Cells shorter
than their width are padded with ASCII spaces. The stored command remains the
full escaped command string; sorting, narrowing, and `show` do not consume the
truncated cell.

The complete header row is the `ProcessListing` presentation. Each complete
member row is one `Process` presentation, including all literal columns and
padding. `USER` remains literal text inside that presentation.

If a captured process sequence is empty and no filter is active, the header is
followed by this exact literal row:

```text
No processes are available.
```

If a nonempty captured sequence has no visible member after filtering, use
`Nothing matches the active filters.` exactly as for a directory listing.

### 3.3 Default order and deterministic ties

Before any view command:

- a directory listing sorts all files and directories together by full
  escaped displayed basename, case-sensitive Unicode code-point order; and
- a process listing sorts by integer pid ascending.

Filters are applied before sorting. Directory sort keys are:

- `name`: ascending full displayed basename;
- `size`: numeric byte size descending, with directory blanks after every
  file; and
- `mtime`: cached timestamp descending, newest first.

Process sort keys are:

- `pid`: integer ascending;
- `state`: ascending Unicode code-point order of the displayed state word; and
- `command`: ascending Unicode code-point order of the full escaped command.

Every directory tie breaks by name ascending. Every process tie breaks by pid
ascending. These tie breakers are part of the specified output.

## 4. View commands and in-place history editing

### 4.1 Target selection

The typed commands `sort`, `narrow`, `only`, and `widen` have no listing
argument. They scan retained logical history from newest to oldest and target
the first listing identity owned by any retained row. This works even if the
listing's header row has already crossed the 500-row boundary while some of
its member rows remain.

If no listing has a retained row, a typed view command appends:

```text
Error: no listing in history.
```

and changes nothing. A menu view action targets the header listing under the
pointer, regardless of which listing is newest.

### 4.2 Command grammar and effects

The commands are:

| Command | Argument | Effect |
|---|---|---|
| `sort` | exactly one word | Replace the target sort key and redisplay. |
| `narrow` | one nonempty rest-of-line string | Replace the substring filter and redisplay. |
| `only` | exactly one word | Replace the kind filter and redisplay. |
| `widen` | none | Clear both filters, preserve the sort key, and redisplay. |

The listener's existing input split still discards the separator run between
the command name and argument; internal and trailing spaces in a `narrow`
argument are part of the substring. There is no quoting or escape grammar.
Successful view commands append no confirmation row and clear their input.

Directory sort words are exactly `name`, `size`, and `mtime`. Process sort
words are exactly `pid`, `state`, and `command`. An inapplicable word appends:

```text
Error: cannot sort this directory listing by KEY.
Error: cannot sort this process listing by KEY.
```

respectively, and does not alter the view.

`narrow` performs a case-sensitive substring match against the full escaped
basename of a directory member or the full escaped process command. It never
matches an absolute path, pid, user, state, size, timestamp, or truncated cell.
Replacing the substring filter preserves the kind filter and sort key.

Directory `only` words are exactly `files` and `directories`. Process `only`
words are exactly `running`, `sleeping`, `disk-sleep`, `stopped`, `tracing`,
`zombie`, `dead`, `idle`, and `unknown`. The two filters apply together.
Replacing the kind filter preserves the substring filter and sort key. An
inapplicable word appends:

```text
Error: cannot apply only WORD to this directory listing.
Error: cannot apply only WORD to this process listing.
```

and leaves the view unchanged. `KEY` and `WORD` in these error templates are
the safely escaped typed word.

`sort` or `only` with no word or with a whitespace-containing argument appends
`Error: sort requires one key.` or `Error: only requires one word.`. `widen`
with an argument appends `Error: widen does not take an argument.`.

### 4.3 Substring accept

Typed `narrow` with no argument first resolves the most recent listing, then
enters a textual substring accept. Choosing `narrow` from a header menu enters
the same state but binds it to that menu's listing. This is not a presentation
accept, creates no chip, and does not change highlighting.

While waiting, the non-editable command prefix and editable substring buffer
render as:

```text
pbui:/absolute/current/directory> narrow SUBSTRING
```

Before any substring has been typed, the row ends after the space following
`narrow`. The exact documentation sentence is:

```text
Type a substring and press Enter to narrow this listing; Ctrl-G or Esc cancels.
```

Enter with a nonempty buffer applies it. Enter with an empty buffer remains in
the wait. `Ctrl-G` or Escape clears the buffer and target, restores ordinary
input, changes no listing state, and appends nothing.

### 4.4 The history operation

Every logical row may carry an optional listing-owner identity. Rows belonging
to one retained listing are contiguous. History exposes one named atomic
operation:

```text
replace_listing_rows(listing_identity, replacement_rows)
```

It finds the retained contiguous block with that owner, replaces it at the
same logical index, updates presentation reference counts and display spans,
increments the history revision once, and then enforces the existing maximum
of 500 logical rows by discarding oldest rows. The replacement reuses the
listing's header and member presentations. Rows outside the block are the
same row objects after the operation, and all presentations outside the block
retain their identity and value, except for oldest rows necessarily evicted to
enforce the bound. No copy is appended at the newest end.

Eviction remains row based. A listing is a valid typed-command target while at
least one row carrying its owner identity remains. A listing whose every row
has been evicted is gone and cannot be redisplayed. The logical-row bound does
not count wrapped physical rows.

Before replacement the terminal captures a viewport anchor consisting of the
oldest visible logical row, its offset within wrapped physical rows, and, for
a listing row, its stable row key (header, explanatory row, or captured member
identity). After replacement:

1. a retained anchor outside the replaced block keeps the same row at the same
   viewport position;
2. an anchor inside the block keeps the same header or member at that position
   if it remains visible;
3. if filtering removed that keyed row, the new header is the anchor; if the
   header was evicted, use the first retained replacement row; and
4. an anchor evicted by the 500-row bound falls back to the first retained row;
   and
5. the resulting scroll position is clamped to the new physical extent.

Thus shortening or lengthening a listing shifts surrounding rows without
making the user's retained anchor jump. Redisplay never forces the viewport to
the newest history. Hover is re-hit-tested from the current pointer coordinate
after replacement; stale screen coordinates are not reused.

## 5. Action menu

### 5.1 Surface and lifetime

`ActionMenu` is one custom terminal surface, never one Textual widget per item.
When open it occupies a transient panel immediately above the documentation
line and prompt, outside the history surface. It reduces the history viewport
height for its lifetime and disappears without adding a history row. Each
drawn item is a `MenuAction` presentation whose stored value names a canonical
operation, its argument, and its target listing or member.

Opening and closing the panel preserve the oldest visible logical-row anchor
and its wrapped-row offset where possible, then clamp, just as a resize does.

The menu opens in ordinary, non-accepting input state by either:

- mouse button 3 on a presentation with menu items; or
- `Ctrl-O` for the currently hovered presentation.

Some terminals do not report button 3; `Ctrl-O` is the required keyboard
equivalent. With no hovered presentation, `Ctrl-O` opens nothing. A pending
presentation accept or substring accept remains modal: these gestures do not
open a menu or change the pending state.

`Ctrl-G` and Escape close an open menu without altering input, a listing, or
history. Escape retains its existing input/accept cancellation behavior when
no menu is open. A single left click on an item closes the menu and runs the
item. A click elsewhere closes it without running an action. For a menu opened
away from its panel, pointer travel toward the panel does not close it before
the pointer first enters; after entry, leaving the panel closes it.

### 5.2 Exact items and labels

Items appear top to bottom in the order shown. Labels are exact.

| Target | Items |
|---|---|
| `File` row | `show`, `rm` |
| `Directory` row | `show`, `cd`, `ls` |
| `Process` row | `show`, `kill` |
| `DirectoryListing` header | `sort name`, `sort size`, `sort mtime`, `only files`, `only directories`, `narrow`, `widen` |
| `ProcessListing` header | `sort pid`, `sort state`, `sort command`, `only running`, `only sleeping`, `only disk-sleep`, `only stopped`, `only tracing`, `only zombie`, `only dead`, `only idle`, `only unknown`, `narrow`, `widen` |
| `Text`, `Error`, literal text, or any other presentation | no items |

`show`, `cd`, `rm`, and `kill` receive the member's stored object and keep all
existing accept types, revalidation, refusals, and effects. `ls` on a directory
row lists that directory and appends a fresh listing; it does not replace the
listing containing the row. View items call the same view-operation function
as typed input, passing the menu's exact listing target. The menu is not a
parallel command registry and does not duplicate operation logic.

Left click on a member with the menu closed remains the `show` translator.
Left click on a listing header with the menu closed has no default operation.

## 6. Terminal interaction and drawing

### 6.1 Hit regions and listener 005 performance

The history remains one `HistorySurface`. It draws one Rich `Text` directly per
physical row from pure-layout fragments. It never constructs those rows by
slicing an accumulated history-wide `Text`, and it never creates a Textual
widget per header or member.

The complete printed member row is the innermost hit presentation. Accept for
`File`, `Directory`, or `Process` highlights the whole row; clicking any cell
passes the original stored object through a chip. A header is its listing
presentation. Literal empty/nothing-matched rows have no hit.

Hover changes restyle only the physical rows occupied by the presentation
being left and entered. Menu hover follows the same local rule inside its own
small surface. Resize still relays out derived cell intervals without changing
values. Scroll, resize, menu opening, and listing replacement recompute hover
against current coordinates.

### 6.2 Base colors and interaction precedence

Outside hover or accept, the whole member row has this foreground:

- `File`: theme foreground;
- `Directory`: cyan `#00afff`;
- `running`: green `#00d787`;
- `sleeping` or `idle`: blue `#5f87d7`;
- `disk-sleep`: amber `#d7af00`;
- `stopped` or `tracing`: magenta `#d787ff`;
- `zombie` or `dead`: red `#ff5f5f`; and
- `unknown`: gray `#a8a8a8`.

Headers use bold theme foreground. These colors are fixed semantic accents,
not a theme system. Interaction styling always wins over them across the whole
presentation: ordinary hover uses reverse video; an acceptable row uses the
existing bold bright green `#00d787` plus underline and adds reverse while
hovered; an inert row uses the existing dim neutral `#808080` without
underline. `Error` remains red outside accept.

### 6.3 Documentation line

The existing documentation sentences for `File`, `Directory`, `Process`,
`Text`, and `Error` remain exact. In particular, ordinary member hover still
says:

```text
Click to show file “NAME”.
Click to show directory “NAME”.
Click to show process PID.
```

When the pointer is specifically inside a 48-cell command field whose value
was truncated, the process sentence is replaced by:

```text
Command is truncated; click to show the full command for process PID.
```

Header hover uses these exact sentences:

```text
Directory listing: Ctrl-O or right-click to open its view menu.
Process listing: Ctrl-O or right-click to open its view menu.
```

While a menu is open with no item hovered, use:

```text
Point at an action and click; Ctrl-G or Esc closes the menu.
```

Menu item hover uses one of these exact templates, substituting the exact menu
label and member label:

```text
Click to run “LABEL” for file “NAME”.
Click to run “LABEL” for directory “NAME”.
Click to run “LABEL” for process PID.
Click to apply “LABEL” to this directory listing.
Click to apply “LABEL” to this process listing.
```

An unsuccessful menu-open gesture replaces the ordinary sentence for that
gesture with one of:

```text
Point at a presentation before opening an action menu.
Text has no action menu.
Error has no action menu.
This presentation has no action menu.
```

The sentence persists until hover or listener state next changes.

The accepted listener's presentation-accept sentences remain exact for member
rows and empty space. Listing headers are inert and add these exact refusal
sentences:

```text
Accept File for rm: directory listing is not a File target.
Accept File for rm: process listing is not a File target.
Accept Directory for cd: directory listing is not a Directory target.
Accept Directory for cd: process listing is not a Directory target.
Accept Process for kill: directory listing is not a Process target.
Accept Process for kill: process listing is not a Process target.
Accept File, Directory, or Process for show: directory listing is not a File, Directory, or Process target.
Accept File, Directory, or Process for show: process listing is not a File, Directory, or Process target.
```

The substring-accept sentence is the one specified in section 4.3. The
documentation line remains one mounted visual row, recalculates on all hover,
menu, accept, execution, scrolling, replacement, and resize changes, and
truncates with an ellipsis rather than wrapping.

### 6.4 Input events

The listener's existing left-click, mouse-wheel, resize, Enter, editing,
`Ctrl-C`, and `Ctrl-D` behavior remains. Add:

- button 3 single-click resolves a fresh hit at the event coordinate and opens
  its action menu when allowed;
- `Ctrl-O` opens the menu for the fresh current hover when allowed;
- while a menu is open, its `Ctrl-G`, Escape, leave, and left-click handling
  takes precedence over ordinary history handling; and
- while substring accept is active, Enter, `Ctrl-G`, and Escape follow section
  4.3.

Later clicks in a click chain do nothing. The prompt and documentation line do
not scroll. Normal exit, `Ctrl-C`, and every error path restore alternate
screen, cursor, mouse reporting, and input mode before returning to the shell.

## 7. Verification and slice order

The later checkpoint manager preserves this order. A layer may be split, but a
later layer cannot enter an earlier checkpoint.

### 7.1 Listing model

Add the two retained listing types, captured member/view models, command
dispatch, filters, deterministic sorting, owner metadata, and
`replace_listing_rows`. This layer is headless and imports no Textual code.
Tests must prove at least:

- each listing captures members once and sort/filter performs no later
  filesystem, password-database, or `/proc` read;
- default and alternate sorts, tie breakers, combined filters, `widen`, invalid
  words, and no-listing errors;
- typed commands target the newest retained listing while an explicit menu
  operation can target an older listing;
- redisplay replaces one contiguous block, reuses header/member presentation
  identities, preserves outside row and presentation identities, and appends
  no duplicate;
- row-based eviction, a partially retained listing target, complete listing
  eviction, and the 500-logical-row bound; and
- existing `show`, `cd`, `rm`, `kill`, chips, exact type acceptance, and stale
  object behavior remain unchanged.

### 7.2 Table text

Add pure table drawing, cached size/mtime/user fields, explanatory rows, and
display-column fitting. Headless tests cover exact headers and sentences,
alignment, blank directory size, UTC mtime, username and decimal-uid fallback,
wide and combining characters, a long untruncated filename, command and user
ellipsis, whole-row presentation spans, and use of the full command for sort
and narrow.

### 7.3 Screen and menu

Add terminal colors, viewport anchoring, the single menu surface, button 3,
`Ctrl-O`, substring accept, and every new documentation sentence. Tests use
`PbuiApp.run_test()` and pure helpers where possible. They prove whole-row hit
behavior, header hits, menu-to-operation routing for both an older listing and
a member, close/cancel behavior, prompt and documentation wording, style
precedence, and anchor behavior for shorter and longer replacements.

The listener 005 regression remains mandatory: with hundreds of injected
process rows and long commands, moving hover restyles only entered and exited
physical rows. No performance test asserts elapsed wall-clock time, and no
test scans live `/proc` merely to construct this regression.

All automated tests use injected services and temporary filesystem roots. No
test unlinks outside `tmp_path` or signals an arbitrary process. The one
accepted production-SIGTERM integration test may signal only the child process
it created and must retain all of its existing safeguards.

Run the complete automated gate with:

```console
uv run pytest
```

### 7.4 Live hand check

Run `uv run pbui` from a fresh disposable directory beneath the project root.
Record its absolute path and verify the prompt before any destructive step.
Create a subdirectory, files of different sizes and mtimes, a filename with a
space, and enough entries to exercise scrolling.

At minimum:

1. Run `ls`; verify its header, alignment, blank directory size, colors, and
   whole-row hover/click behavior.
2. Type `sort size`, then use the header's `Ctrl-O` menu to apply `sort mtime`;
   verify the same listing changes in place and intervening history does not.
3. Type a `narrow` substring, combine it with `only files`, then `widen`; verify
   the no-match sentence and restoration without a rescan or duplicate.
4. Open member menus with `Ctrl-O`; use `show`, and use directory `ls` to append
   a fresh listing. Exercise button 3 only if the terminal reports it.
5. Run `ps`; verify pid/state/user/command columns, a visibly truncated long
   command if one is available, state colors, and that `show` displays the full
   current command.
6. Scroll to an older listing, resize, sort it from its menu, and verify the
   anchored object remains connected to the correct value.
7. Recheck the prompt against the recorded disposable path before `rm`. Remove
   only a designated disposable file. Do not run `kill` against any live
   process during the hand check.
8. Verify `Ctrl-G` and Escape cancel both ordinary presentation accept and the
   substring wait. Exit once with `Ctrl-D` and once with `Ctrl-C`, confirming
   full terminal restoration and no traceback.

## 8. Acceptance boundary

This exploration is complete only when every listing row remains its original
application object; each table is one captured collection; view operations
redisplay it in place without a host rescan; typed and menu actions share one
operation path; a truncated command retains its full value; hover remains
row-local; existing commands and safety boundaries still hold; and all tests
and the disposable-directory hand check pass.

Do not add new domain types, rename, copy, process-control commands, a text
pipe, shell syntax, listing refresh, a graphical table, icons, a second
presenter, one widget per member, a menu stored in history, or any change to
the 500-row bound, process enumeration, and existing `show` detail text. Those
require another charter.
