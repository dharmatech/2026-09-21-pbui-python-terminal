# Charter — listings you can redisplay

**Status.** Handoff from the high-level discussion into a **design
conversation**. Not a checkpoint. Not an implementer assignment.
This file lives in `docs/design/implementation/listings/`. The
specification will live beside it as [`spec.md`](spec.md).
Checkpoint files will live in `checkpoints/` beside it. Map:
[`README.md`](README.md). The program lives at
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

**Your job.** Turn this charter into a specification that extends
the implemented listener. `ls` and `ps` become tables of the objects
they already present. A menu offers the actions those objects
already have. Sort and filter redisplay that listing in place. Then
**stop**. Do not write checkpoints. Do not implement.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Read the listener specification at
   [`../listener/spec.md`](../listener/spec.md) so you know what
   already exists. Do not copy it into the new spec. Do restate
   every rule an implementer must obey, including the listener rules
   this work must not break.
3. Record the locked decisions in §4. Resolve the open questions in
   §5.
4. Write `spec.md` in this folder. A later checkpoint-manager
   conversation slices **listings 000**, `001`, … under
   `checkpoints/` here, one checkpoint per conversation.
5. Stop. The human reviews the spec. Do not write those checkpoint
   files.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification. Name the
listener sentences this spec supersedes, in particular the `ls` and
`ps` row wording in listener spec §4.3. Everywhere else, the
listener specification still holds.

Keep the spec **small enough to slice**. New object types, rename,
copy, a text pipe, and a graphical presenter are defects in this
document.

## 2. Predecessors

The listener exploration is implemented and reviewed through
listener 005. The program already has presentation types, history,
accept, chips, translators, the six commands, and a Textual screen
whose history is drawn as one Rich `Text` per physical row.

This exploration does not create a new Python project. Implementers
keep using uv in the existing project (`uv sync`, `uv run pytest`,
and `uv add` only if a dependency is actually required). The
designer does not run those commands. Prefer no new dependency.

Two places, and they stay separate:

| Place | What goes there |
|---|---|
| `docs/design/implementation/listings/` | This charter, `spec.md`, and `checkpoints/` |
| Project root | The existing `pbui` package and `tests/` |

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **A row is still the object.** In an `ls` table, each member row
   is a `File` or a `Directory`. In a `ps` table, each member row is
   a `Process`. A left click still runs `show`. Accept still
   highlights the whole row when that type is wanted, and a click
   still supplies the object rather than the characters in a cell.
2. **The listing is one collection.** `ls` and `ps` each leave a
   listing presentation in the history. Sort and filter change that
   listing and redisplay it where it already sits. They do not
   append a second copy, and they do not scan `/proc` or the
   directory again.
3. **The menu and the typed commands are the same operations.**
   Choosing "sort by size" from the menu and typing `sort size` do
   one thing. The menu is not a second command set.
4. **A long command stays one row.** The process command column has
   a fixed display width. `show` still presents the full command
   text. Sort and filter see that full text, not the truncated cell.
5. **Hover stays cheap.** Drawing follows listener 005: one Rich
   `Text` per physical row, built directly, and a hover restyles
   only the rows it enters and leaves. A table must not bring back
   history-wide slicing.
6. **Existing commands still mean what they mean.** `show`, `cd`,
   `rm`, and `kill` keep their accept types, refusals, and effects.
   Automated tests must not unlink outside a temporary directory or
   signal any process except the one production-SIGTERM test the
   listener spec already requires.

## 4. Locked decisions (record these; do not reopen)

### 4.1 What a listing is

`ls` presents a `DirectoryListing`. `ps` presents a `ProcessListing`.
Both are presentation types. A listing stores:

- the members, each still a `File`, `Directory`, or `Process` with
  the absolute path or pid it already denotes;
- the view: sort key, and the active filter;
- the place in the history that belongs to this listing.

A new `ls` or `ps` appends a new listing, as command output does
today. `sort`, `narrow`, `only`, and `widen`, and the menu items
that invoke them, update the listing they target and replace its
rows in place. Rows above it and below it stay. Presentations
outside it stay. Dropping old history still drops a listing only
when its rows fall off the oldest end. The 500-logical-row bound
remains.

Sort and filter use the members already stored. They do not call
`stat` or read `/proc` again. `show` on a member still re-reads, as
it does today. A later `ls` or `ps` is a new listing of fresh data.

The typed commands `sort`, `narrow`, `only`, and `widen` target the
most recent listing still in the history. The menu targets the
listing under the pointer, even when it is not the most recent.
If no listing is in the history, the typed command appends `Error`
and changes nothing.

### 4.2 Tables

An `ls` listing draws a header and one logical row per visible
member:

```text
name      size  modified
NAME      SIZE  MTIME
```

`NAME` is the member's escaped basename. The whole member row is
the `File` or `Directory` presentation, so a click on the size is a
click on that object. The header row is the `DirectoryListing`, not
a member.

A `ps` listing draws:

```text
pid  state  user  command
PID  STATE  USER  COMMAND
```

The whole member row is the `Process`. `PID` is the canonical
decimal pid. `STATE` is the existing state word. `USER` is the
username for the process's real uid when the password database has
one, otherwise the decimal uid. It is literal text, not a `User`
presentation. `COMMAND` is the existing command text, escaped as
today, cut to a fixed display width the spec chooses. Cutting is
display only.

Header labels are literal. There is no separate listing title row
beyond the header. An empty directory still produces a listing whose
body says it is empty, using the existing empty-directory sentence.
A filter that matches nothing keeps the header and says that nothing
matched, with a sentence the spec writes. `widen` can bring the
members back.

Default views, before any sort or filter:

- a directory listing sorts by displayed basename, Unicode
  code-point order, case-sensitive, files and directories together,
  dotfiles included, `.` and `..` omitted;
- a process listing sorts by integer pid ascending and includes the
  same processes `ps` includes today.

Size is the byte length from `stat` of the member as already
defined for `show`. Mtime is that `show` timestamp, UTC, to whole
seconds. A directory member's size cell is blank. The listing may
read size and mtime when `ls` builds the listing. Sort and filter
must not require a later read.

### 4.3 Sort, narrow, only, widen

These commands take no listing argument. They use the target rule
in §4.1.

| Command | Argument | Effect |
|---|---|---|
| `sort` | one key | Sets the listing's sort key and redisplays. |
| `narrow` | the rest of the line | Sets the substring filter. Spaces are part of the text. |
| `only` | one word | Sets the kind filter. |
| `widen` | none | Clears `narrow` and `only`. Leaves the sort key. |

Sort keys:

- directory listing: `name`, `size`, `mtime`;
- process listing: `pid`, `state`, `command`.

`name` is the default directory order. `size` is numeric, largest
first; a blank directory size sorts last. `mtime` is newest first.
`pid` is ascending. `state` and `command` are Unicode code-point
order of the displayed state word and the full command text.
A key that does not belong to that listing appends `Error` and
leaves the view unchanged.

`narrow` matches a case-sensitive substring of the displayed
basename, or of the full process command text. It does not match
the truncated cell, the path, or the pid.

`only` on a directory listing accepts `files` or `directories`.
`only` on a process listing accepts one existing state word
(`running`, `sleeping`, and the rest of the listener's state
table). Anything else appends `Error` and leaves the view
unchanged.

A listing remembers both the `only` filter and the `narrow`
filter. Both apply together. Changing the sort does not clear
them. `widen` clears both filters and does not change the sort.

### 4.4 The menu

The menu is a transient list of actions for the presentation under
the pointer. It is not inserted into the history, it is not a
listing, and it does not survive leaving the menu. Draw it in a
region of the screen that is not the history. Ctrl-G closes it
with no effect. Escape closes it when it is open, and otherwise
keeps the listener's current Escape behavior.

Open it two ways:

- mouse button 3 on a presentation;
- `ctrl+o` for the hovered presentation.

If nothing is hovered, `ctrl+o` does not open a menu. The
documentation line says to point at a presentation. Some terminals
never deliver button 3. `ctrl+o` is enough.

Menu items are presentations. A left click on an item runs that
action. The items are exactly:

| Pointer is on | Items |
|---|---|
| `File` row | `show`, `rm` |
| `Directory` row | `show`, `cd`, `ls` |
| `Process` row | `show`, `kill` |
| `DirectoryListing` header | `sort name`, `sort size`, `sort mtime`, `only files`, `only directories`, `narrow`, `widen` |
| `ProcessListing` header | `sort pid`, `sort state`, `sort command`, `only` for each state word, `narrow`, `widen` |
| `Text`, `Error`, or anything else | no items; the documentation line says there is no menu |

`ls` on a directory row runs `ls` of that directory and appends a
new listing. It does not redisplay the listing that contained the
row. `show`, `cd`, `rm`, and `kill` are the existing commands,
including their refusals. `narrow` from the menu closes the menu
and enters accept for the substring, then redisplays. The other
items run immediately.

Left click on a member row remains `show`, including while a menu
is closed. Left click on a header does not run `show`. The
documentation line on a header says that `ctrl+o` or the right
button opens the listing's view menu.

### 4.5 Color

Color marks the type inside a member row and must lose to the
existing hover and accept treatments. A hovered row is still
reverse video. An acceptable row during accept is still the
existing green underline, and an inert row is still dim. The spec
picks a directory color and a small set of process-state colors.
Files stay at the theme foreground. Color is not a theme system.

### 4.6 What this must not break

- Left click with no accept runs `show` on a member.
- Accept types stay exact. A directory row is not an `rm` target.
  A file row is not a `cd` target. A process row is not an `ls`
  target.
- Chips still store the object. A name with a space is still one
  object.
- The documentation line remains one row and still has a sentence
  for every hover the listener spec already lists. New sentences
  are added for headers, menu items, and the truncated command
  cell. The spec writes those sentences and does not loosen the
  old ones.
- Listener 005 drawing: per-row Rich `Text`, no history-wide
  slice, hover restyles only the rows it enters and leaves.
- `uv run pytest` is the automated gate. `uv run pbui` is the
  human hand check. The hand check starts in a disposable
  directory and does not `rm` or `kill` outside the rules the
  listener spec already states. Add hand-check steps for a table,
  a sort, a narrow, and opening the menu with `ctrl+o`.

### 4.7 Slice order

Structure the spec in this order. Each layer is testable without
the later ones.

1. **Listing model.** Listing types, stored members and view,
   in-place replacement in the history, `sort`, `narrow`, `only`,
   and `widen`. Headless tests. No Textual.
2. **Table text.** Header and member rows, truncation, username
   display, empty filter text. Headless tests. No Textual.
3. **Screen.** Draw the tables under the listener 005 rule, color,
   the transient menu, button 3, `ctrl+o`, documentation lines,
   and the hand check.

A layer may become more than one checkpoint. Do not add a layer
for a feature in §4.8.

### 4.8 Out of this spec

- A `User`, socket, mount, or any other new domain type. The user
  column is text.
- Rename, copy, stop, continue, and any command that is not in
  §4.3 and §4.4.
- A text pipe, `grep`, globs, or a shell grammar.
- Refreshing a listing's members without running `ls` or `ps`
  again.
- A graphical table, icons, or a second presenter.
- Changing the 500-row bound, process enumeration, or the `show`
  detail text, except that `show` must still reveal the command
  text the table cut off.
- Making the menu a history listing, or one Textual widget per
  member row.

## 5. Open questions (resolve these in the spec)

### 5.1 Wording

Write the header cells, the blank size cell, the nothing-matched
sentence, the menu item labels, and the new documentation-line
sentences. Keep every listener documentation sentence that still
applies to a member under the pointer.

### 5.2 Widths and alignment

Choose the fixed command-column width and the other column widths.
A member row whose fields fit must be one logical row, including a
long command. Alignment is part of the table, not a feature of its
own.

### 5.3 Colors

Choose the directory color and the process-state colors. State how
they yield to reverse video, green underline, and dim.

### 5.4 History edit

Name the history operation that replaces one listing's rows and
leaves every other presentation's identity and value in place.
State what happens to the scroll anchor when the replacement is
shorter or longer than the old listing.

### 5.5 Menu accept for narrow

State the documentation line and the prompt while `narrow` is
waiting for its substring, and what Ctrl-G does during that wait.
The substring is the rest of the line, as with other one-argument
commands.

## 6. Authority

This charter is the design for the listings exploration. The
listener specification remains the law for everything this charter
does not change.

Ciccarelli, the Genera listener, the McKay, York, and McMahon
paper, and the CLIM and McCLIM listeners are influences, recorded
in the project [`AGENTS.md`](../../../../AGENTS.md). The piece this
exploration takes from them is a listing you can redisplay: the
row is the object, and sort and filter are a view of the
collection. It does not take viewspec menus, More processing, or a
CLIM port.

## 7. Handoff reminder

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. Identity is **listings 000**, then
**listings 001**, and so on.
