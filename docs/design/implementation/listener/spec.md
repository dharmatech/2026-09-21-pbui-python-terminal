# Specification — pbui presentation listener

**Status:** design for review. This specification defines the first `pbui`
exploration. It is the complete input to later checkpoint-manager and
implementation conversations; those conversations do not need the charter.

`pbui` is a small, full-screen Linux terminal listener. Its scrollable history
retains Python objects and their presentation types, not merely the characters
used to draw them. A left click either supplies an acceptable object to a
waiting command or, when no command is waiting, invokes `show` for the object.
The complete command set is `ls`, `ps`, `show`, `kill`, `cd`, and `rm`.

This document specifies four implementation layers, in order: substrate,
domain, commands, and terminal. Each layer is independently testable before the
next is added. The terminal layer is likely to require two checkpoints (drawing
and layout first, interaction and lifecycle second); the other layers should
each fit in one checkpoint. A checkpoint manager may split a layer further but
must preserve this order and must not add features.

## 1. Product boundary

The listener starts with the process's current working directory. It enters the
terminal's alternate screen, owns a finite scrollable history, and keeps a
documentation line and command input pinned at the bottom. Emulator scrollback
is not listener history. The listener owns both its drawn text and its hit
regions, so scroll and resize move them together.

The screen has exactly these regions, from top to bottom:

1. a scrollable history surface;
2. an always-present, one-row documentation line; and
3. a one-row prompt and input editor.

The application has no evaluator or shell grammar. It does not run external
programs. There are no pipelines, redirections, quotes, globs, multi-argument
commands, popup menus, right-click actions, planned commands, annotations,
delete marks, confirmation dialogs, up-arrow command history, or second
graphical presenter, icons, or spatial directory. It does not add `User`,
socket, systemd-unit, git-repository, window, scrollbar, desktop, or buffer
objects; make emulator scrollback mouse-sensitive; edit Ciccarelli or Genera
documents; reimplement CLIM; support macOS or Windows process listing; or make
a C# port.

The six named commands are the whole command registry. `Ctrl-D` on an empty,
non-waiting input is a normal exit; it is a key action, not a seventh command.
`Ctrl-C` also exits. Both paths restore the terminal before returning to the
shell.

## 2. Host, project, and source layout

The target is Linux and Python 3.11 or newer. Linux `/proc` is the only process
table source. Code and tests live at the project root:

`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`

They do not live under `docs/`. Use a `src` package layout:

```text
pyproject.toml
uv.lock
src/
  pbui/
    __init__.py
    __main__.py
    substrate.py       # type registry, presentations, accept, chips, history
    text.py            # pure text drawing, display-column layout, hit testing
    domain.py          # File, Directory, Process, Text, Error and parsers
    commands.py        # headless listener, six commands, host seams
    terminal.py        # the only module that imports Textual
tests/
  test_substrate.py
  test_domain.py
  test_commands.py
  test_terminal.py
```

The package import name and console script are both `pbui`. The script calls
`pbui.terminal:main`; `python -m pbui` calls the same function. This module split
is a layer boundary, not permission to create parallel object models.

The project uses **uv for its entire Python lifecycle**. The initial project
checkpoint runs these commands from the project root:

```console
uv init --package --python 3.11
uv add textual rich wcwidth
uv add --dev pytest pytest-asyncio
uv sync
```

The generated console-script entry is changed to `pbui = "pbui.terminal:main"`.
Development and verification use:

```console
uv run pbui
uv run pytest
```

Every checkpoint repeats only the applicable `uv sync`, `uv run pytest ...`, or
`uv run pbui` commands. Dependencies are added with `uv add` or `uv add --dev`
so they are recorded in both `pyproject.toml` and `uv.lock`. Do not create a
virtual environment by hand and do not use `pip`, `python -m pip`, `uv pip
install`, Poetry, Pipenv, Conda, Hatch, or globally installed packages. If `uv`
is unavailable, stop and tell the human.

## 3. Layer 1: presentation substrate

This layer is plain Python and has no filesystem, process, or Textual imports.
It establishes one object path from history to hit testing to command
invocation.

### 3.1 Explicit presentation types

`PresentationType` is an immutable registry entry with a stable name. A
`PresentationTypeRegistry` explicitly registers entries and rejects duplicate
names. The registry is application-defined: it is not generated from Python
classes, method reflection, or inheritance.

Type acceptance is exact registry identity. Python subclass relationships do
not imply presentation compatibility. In particular, the later `Directory`
type is not a subtype of `File` for acceptance. The substrate must also allow a
presentation type to be used with values whose Python class is otherwise
uninteresting.

A `Presentation` contains:

- the Python value itself;
- one registered `PresentationType`;
- a stable identity within the retained history; and
- its current derived display-span intervals, empty before layout and replaced
  rather than patched when layout changes.

The value is authoritative. The label drawn for it is never parsed to recover
that value. The logical text drawing is a separate history structure referring
to the presentation identity; a future drawer can use the same object and type
without consuming terminal text.

### 3.2 Rows, drawing, and spans

The pure terminal-text drawer in `pbui.text` produces logical `HistoryRow`
objects from literal fragments and presented fragments. A presented fragment
may contain child presented fragments. This is how an outer presentation can
contain a more specific inner presentation without making either one a Textual
widget.

`present(value, presentation_type, drawing_context)` creates a presentation and
asks the registered pure text drawer for a row containing it. Composed rows
such as an `ls` row use the same operation for the name fragment and combine it
with unpresented literal columns. A `PresentedFragment` associates separately
drawn content with a presentation and may contain child fragments. The history
retains each `Presentation`, including its value and type, alongside but not
inside the logical drawing. Object identity must not live only in Rich spans or
widgets.

Layout at a given width creates one or more half-open cell intervals
`[start_column, end_column)` for every presentation on every physical display
row that its text occupies. Those intervals are its display span. Coordinates
are zero-based. A multi-line span is a collection of row intervals, not one
bounding rectangle, so it cannot claim cells it did not draw.

Column width is terminal display width, calculated with `wcwidth`; it is never
a Python string index. Combining characters have zero width and wide
characters have width two. A wide character that does not fit in the remaining
column starts on the next physical row. All product printers escape embedded
newlines, tabs, control characters, and unpaired surrogates, so one logical row
never injects a layout newline. A width less than one is treated as one for
layout.

Resize discards derived cell intervals and lays out retained logical rows again
at the new width. Presentations and their values remain unchanged.

### 3.3 History and hit testing

History retains at most **500 logical rows**. Appending row 501 drops the oldest
logical row and every presentation owned only by it. Wrapped physical rows do
not count separately toward retention. Five hundred rows is intentionally large
enough for several listings and the required older-object hand check.

Hit testing accepts a display-column `x` and a laid-out history-row `y`. It
considers only retained presentations whose exact interval contains that cell.
The candidate at greatest nesting depth wins. If malformed drawing creates two
candidates at the same depth, the one drawn last wins; normal drawers must not
create such overlapping siblings. A pointer on literal text or padding returns
no presentation. Viewport coordinates are translated through the current
vertical scroll offset before this pure hit test is called.

When old rows are dropped, scrolling is clamped and no dropped presentation is
hit-testable. When layout width changes, the terminal layer preserves the
oldest visible logical-row anchor where possible, then clamps it. Thus an older
retained name remains connected to its object after both scroll and resize.

### 3.4 Accept, chips, and default translation

`AcceptRequest` holds the command name, a nonempty set of acceptable registered
types, and the continuation to invoke with an accepted value. While a request
is pending:

- presentations whose exact type is in the acceptable set are targets;
- all other presentations are inert;
- selecting a target creates a `Chip` and supplies it to the continuation;
- selecting a non-target changes neither the request nor the input; and
- cancellation drops the request and any chip.

A `Chip` stores the selected presentation type and the original Python value,
plus a label used only for drawing. It is one atomic input argument. Supplying
it to a command passes the stored value directly. It never inserts label
characters into the text buffer and never invokes a parser. If a chip is
present in an editable state, Backspace removes the whole chip in one action.
For this product, clicking a valid target supplies the chip and immediately
runs the waiting command, so a terminal-rendered chip may be brief; its atomic
model and direct value path are still required and tested.

With no pending accept, the default translator maps the domain `File`,
`Directory`, and `Process` types to `show` with the stored object. `Text` and
`Error` have no default command. Only a left click invokes translation or
acceptance.

## 4. Layer 2: domain objects and printers

This layer is plain Python and imports no Textual code. It defines exactly five
presentation types and explicitly registers them:

| Type | Stored value | Acceptance and display |
|---|---|---|
| `File` | `FileRef(path)` | A non-directory path; listing name or standalone absolute path |
| `Directory` | `DirectoryRef(path)` | A directory path; listing name or standalone absolute path |
| `Process` | `ProcessRef(pid)` | A decimal pid token |
| `Text` | a string or small text value | Unstructured product output |
| `Error` | a failure message | Product failure output |

`Text` and `Error` are never acceptable for `File`, `Directory`, or `Process`.
The Python classes make values convenient; only the explicit registered type
determines accept compatibility.

### 4.1 Paths and classification

Every stored path is absolute. Relative input is joined to the listener's
current directory and normalized with `abspath` at presentation or parse time.
Here, “resolved” means that the cwd and `.`/`..` components have been applied;
it does **not** mean `realpath`. The final symlink must remain in the stored path
so `rm` can unlink the link rather than its target. A later `cd` never retargets
an old presentation.

Classification calls `stat`, following symlinks:

- a resulting directory is `Directory`;
- every other result is `File`;
- a broken symlink, detected with `lstat`/`lexists` after `stat` fails, is
  `File`; and
- an absent path may still be represented as a `FileRef`, allowing an old or
  typed path to keep denoting that location. An operation that requires it to
  exist reports `Error` rather than raising.

A symlink to a directory is consequently `Directory`; a symlink to a
non-directory is `File`. `rm` reclassifies at effect time, refuses any current
`Directory` including a symlink to one, and calls `unlink` on the stored path.
It never recursively removes or follows a link for deletion.

The `Directory` typed parser normalizes one path string and succeeds only when
current followed `stat` says directory. The `File` parser normalizes one path
string and rejects it only when current followed `stat` says directory;
missing paths and broken symlinks can produce `FileRef`s. The `Process` parser
accepts one base-10 integer with an optional sign and no surrounding junk;
range and safety refusals belong to `kill`.

For typed `show`, whose accepted types form a union, parsing is deterministic:
an existing or lexisting path is classified first; otherwise a signed decimal
string becomes `Process`; any other string becomes a `File`. Clicking is never
ambiguous because it supplies the stored type and value.

### 4.2 Safe display strings

Path display preserves ordinary Unicode and spaces. It displays backslash as
`\\`, newline as `\n`, carriage return as `\r`, tab as `\t`, other control
characters with `\x`, `\u`, or `\U` escapes, and unpaired surrogates with a
Unicode escape. These are display escapes only. The stored path is unchanged.
A filename containing spaces is one complete presented name span.

The same control-character escaping is applied to process names, OS error
text, and echoed command names. It does not alter their stored values. This
keeps every product output to one logical row even when host or input text is
unusual.

Listings sort by this displayed basename in Unicode code-point order,
case-sensitively. They include dotfiles and exclude only `.` and `..`.

The exact terminal-text printers are:

- `File` in a listing: the escaped basename; standalone: the escaped absolute
  path.
- `Directory` in a listing: the escaped basename; standalone: the escaped
  absolute path.
- `Process`: the canonical decimal pid, with no embedded spaces.
- `Text`: its plain text.
- `Error`: `Error: ` followed by its plain failure message.

Rich/Textual markup parsing is disabled for all product strings. Brackets and
markup-like filenames are literal.

### 4.3 Detail and row wording

An `ls` child occupies one logical row:

```text
file       NAME
directory  NAME
```

Only `NAME` is the `File` or `Directory` presentation. The type column and
spacing are literal, non-presented text. There is no separate heading row.

A `ps` row is:

```text
PID  STATE  COMMAND
```

Only `PID` is the `Process` presentation. Rows sort by integer pid. `STATE` is
one of the readable state words in section 5.3, and `COMMAND` is plain text.
There is no separate heading row.

`show` emits one `Text` detail row, not `repr` of the stored object:

```text
path: ABSOLUTE_PATH | type: file | size: N bytes | mtime: UTC_TIMESTAMP
path: ABSOLUTE_PATH | type: directory
pid: PID | command: COMMAND | state: STATE
```

`UTC_TIMESTAMP` is ISO 8601 to whole seconds with a trailing `Z`. For a
symlink, insert ` | symlink -> LINK_TARGET` after the type. The link target is
the escaped string returned by `readlink`, not a canonical path. For a live
symlink, file size and mtime come from followed `stat`. For a broken symlink,
the type text is `file (broken symlink)` and size and mtime come from `lstat`.
Directory detail does not add size or mtime. A process detail always performs a
fresh inspection and includes its current command and state.

Successful effects use these `Text` rows:

```text
Removed file: ABSOLUTE_PATH
Sent SIGTERM to process PID.
```

An empty `ls` emits `Directory is empty: ABSOLUTE_PATH`. `cd` succeeds without
adding a history row; the prompt change is its visible confirmation.

All expected failures become one `Error` presentation. OS failures use a
stable action phrase, the escaped path or pid, and the operating-system message,
for example `Error: cannot remove /tmp/missing: No such file or directory.`
Unknown input uses `Error: unknown command: NAME.` Commands with forbidden
arguments use `Error: COMMAND does not take an argument.` No expected missing
path, bad pid, race, or permission error may escape as a terminal traceback.

## 5. Layer 3: headless listener and commands

`HeadlessListener` owns the explicit type registry, history, current absolute
cwd, input/accept state, command registry, filesystem service, and process
service. It starts with an injected cwd; production injects `os.getcwd()`.
`cd` updates this listener field and does not call `os.chdir`, so the launching
shell and process-global cwd are not mutated.

The controller presents output through the substrate. It has no Textual import
and can execute all six commands in tests.

### 5.1 Input dispatch

The input editor is not a shell. Leading whitespace before a command is
ignored. The command name is the first whitespace-delimited token. The first
run of separator whitespace is discarded and the rest of the line, if any, is
one argument string; internal and trailing spaces are preserved. There is no
quote or escape grammar and no second argument. Clicking avoids all textual
ambiguity by supplying a chip.

Pressing Enter behaves as follows:

- an empty line does nothing;
- a complete command parses its typed argument, makes an object/chip, and runs;
- an invalid typed argument appends `Error` and performs no command effect;
- a missing required argument leaves the command name in the editor and enters
  accept for its required type or types; and
- `ls` is the exception: no argument runs immediately on the current cwd.

`ps` rejects any argument. A command attempt, whether successful or an expected
failure, clears the editor after its result is appended. A missing-argument
accept does not. A matching click fills an atomic chip, invokes the command,
then clears the editor and pending request. A nonmatching click changes
nothing. `Ctrl-G` clears both text and chip and cancels accept. `Escape` has the
same action.

With no accept pending, left-clicking an innermost `File`, `Directory`, or
`Process` invokes `show` with that stored value. It does not alter the editor.
Clicking `Text`, `Error`, literal columns, or empty history performs no command.

### 5.2 Filesystem seam

The filesystem protocol covers path normalization, `stat`, `lstat`,
`readlink`, directory iteration, and `unlink`. Production delegates to Python's
real filesystem APIs: `os.stat`, `os.lstat`, `os.readlink`, and `os.scandir`
(direct `pathlib` wrappers with identical semantics are acceptable for these
reads). The production unlink operation specifically calls `os.unlink`. A test
adapter is constructed with `allowed_root=tmp_path` and rejects access
outside that root. In particular, its unlink check validates the canonical
root, follows and canonicalizes the candidate's parent directory, and confirms
that parent is still under the root, while never following the final pathname
component. It can therefore unlink a final symlink inside the root but cannot
traverse an intermediate symlink and unlink an external target. Tests start
the listener cwd inside the same temporary root.

All path commands re-read current filesystem state rather than trusting an old
listing classification. The adapter translates `OSError` subclasses to command
failures; the controller appends `Error` and stays alive.

### 5.3 Process seam and `/proc`

The process protocol provides `list_for_uid(uid)`, `inspect(pid)`, and
`send_sigterm(pid)`. It also supplies the uid and pid that pbui considers its
own. Production uses `os.getuid()`, `os.getpid()`, Linux `/proc`, and
`os.kill(pid, signal.SIGTERM)`. It never shells out to `ps`.

Production process listing iterates numeric `/proc` directory names and reads
`/proc/PID/status`. It uses `Name`, the first integer in `Uid` (real uid), and
the code at the start of `State`. It includes only processes whose real uid
equals the listener's uid and skips any process whose directory disappears or
whose required fields are unreadable or malformed. It does not special-case
kernel threads. State codes map as follows:

| Code | Word |
|---|---|
| `R` | `running` |
| `S` | `sleeping` |
| `D` | `disk-sleep` |
| `T` | `stopped` |
| `t` | `tracing` |
| `Z` | `zombie` |
| `X` or `x` | `dead` |
| `I` | `idle` |
| anything else | `unknown` |

The listener's own pid is included when inspectable; its command name and pid
make it identifiable in `show`. `show Process` always calls `inspect` again. If
the process exited or cannot be inspected, it appends `Error`.

Tests inject a fixed process table and a kill recorder. The own pid is
injectable, so the own-process refusal never targets pytest. Automated tests do
not signal arbitrary processes.

### 5.4 The six commands

| Command | Accepted argument | Required behavior |
|---|---|---|
| `ls` | optional `Directory`; absent is cwd | Revalidate the directory, list each child once in displayed-name order, include dotfiles, exclude `.` and `..`, and present every name as current `File` or `Directory`. Do not change cwd. A non-directory or inaccessible path appends `Error`. |
| `ps` | none | Present every inspectable, real-uid-matching process from the process seam in integer-pid order. Each pid token stores `ProcessRef(pid)`. |
| `show` | `File`, `Directory`, or `Process` | Re-read state and append the exact detail row from section 4.3. For a path, report its current followed classification even if it differs from the stored presentation type. Missing/inaccessible paths or processes append `Error`. |
| `cd` | `Directory` | Revalidate it, then replace listener cwd with its stored absolute path. Keep all history. Missing paths or files append `Error` and leave cwd unchanged. There is no `$HOME` default. |
| `rm` | `File` | Reclassify and refuse a current directory, including a symlink to a directory. Otherwise call `unlink` on exactly the stored path. Never recurse. Append confirmation or `Error`. |
| `kill` | `Process` | Refuse pid 1, every pid below 1, and the injected own pid with `Error`. Freshly inspect any other pid, then send exactly `SIGTERM`. Append confirmation, or `Error` if inspection or signaling fails. Never offer `SIGKILL`. |

The exact accept sets are `{Directory}` for `cd`, `{File}` for `rm`,
`{Process}` for `kill`, and `{File, Directory, Process}` for `show`. `ls` with
no argument means cwd, so it does not enter accept merely because its optional
argument is absent.

## 6. Layer 4: Textual terminal

Only `pbui.terminal` imports Textual. It adapts one `HeadlessListener`; it does
not replace history values with widget state.

The non-presentation UI objects are:

- `PbuiApp`, the Textual `App` that runs full-screen in the alternate screen;
- `ListenerScreen`, the one screen arranging the three fixed regions;
- `HistorySurface`, one custom scrollable widget that draws all history rows;
- `DocumentationLine`, one plain-text one-row widget; and
- `CommandInput`, one custom one-row editor for prompt text, command text,
  cursor, and an optional atomic chip.

There is never a `Button`, `Label`, `Static`, or other widget per file,
directory, process, or presentation. `HistorySurface` builds one Rich `Text`
renderable from the pure layout. Presented fragments carry presentation ids,
so styling is applied to the corresponding Rich character spans while the
separate display-cell intervals remain the authority for hit testing; codepoint
indices and display-column indices are not interchanged.

### 6.1 Prompt and editor

The prompt is:

```text
pbui:/absolute/current/directory> 
```

The cwd is always absolute and uses the safe path display. The accept type is
always readable on the documentation line; it is not duplicated in the prompt.
When present, a chip is drawn as `⟨Type: LABEL⟩` after the command name. Its
label is presentation output only and its stored value remains the argument.

`CommandInput` is a deliberately small editor. It supports printable-character
insertion, bracketed paste, Left, Right, Home, End, Backspace, Delete, and
Enter. Backspace adjacent to a chip deletes the whole chip. It has no command
history, completion, multiline mode, or shell editing. Tab does not insert a
path character or add completion; it remains focus navigation if Textual needs
it.

### 6.2 Documentation line

The documentation line is always mounted, even over empty history. It is a
single visual row and truncates with an ellipsis at narrow widths instead of
wrapping. It is recalculated on hover, accept changes, execution, scrolling,
and resize. Required exact sentences are:

| Situation | Sentence |
|---|---|
| Empty/literal history, no accept | `No presentation under pointer.` |
| `File` under pointer, no accept | `Click to show file “NAME”.` |
| `Directory` under pointer, no accept | `Click to show directory “NAME”.` |
| `Process` under pointer, no accept | `Click to show process PID.` |
| `Text` under pointer, no accept | `Text has no default click action.` |
| `Error` under pointer, no accept | `Error has no default click action.` |
| Nothing under pointer while `rm` waits | `Accept File for rm: point to a highlighted File and click; Ctrl-G or Esc cancels.` |
| `File` under pointer while `rm` waits | `Accept File for rm: click to use file “NAME” and run rm.` |
| `Directory` under pointer while `rm` waits | `Accept File for rm: directory “NAME” is not a File target.` |
| `Text` under pointer while `rm` waits | `Accept File for rm: Text is not a File target.` |

The same grammar generalizes to other waits: `Accept TYPE-LIST for COMMAND`, a
matching object says `click to use ... and run COMMAND`, and a nonmatching type
says `TYPE is not a TYPE-LIST target`. The `show` type list is printed as
`File, Directory, or Process`. These words supplement rather than replace the
visual target treatment.

### 6.3 Visual treatments

The history surface uses three unambiguous interaction looks:

- **hover with no accept:** reverse video on the innermost presentation;
- **acceptable during accept:** bold bright green (`#00d787`) and underline;
  the currently hovered acceptable target also uses reverse video; and
- **inert during accept:** dim neutral gray (`#808080`) with no underline;
  hovering it does not acquire the green target style.

`Error` text is red outside accept. Normal presented names and pids use the
theme foreground. Color is reinforcement only; bold/underline/dim/reverse keep
the three states distinguishable without relying solely on hue.

### 6.4 Event mapping and scrolling

The Textual event mapping is concrete:

- `events.MouseMove` on `HistorySurface` obtains the offset within the widget's
  content area, maps it through `scroll_y`, pure-hit-tests, and updates hover,
  style, and docs. Padding, border, and screen-relative coordinates are not
  mistaken for content coordinates.
- `events.Leave` clears the hovered item and shows the appropriate no-pointer
  sentence.
- `events.Click` with `button == 1` and `chain == 1` runs accept or default
  translation for the current hit. Other buttons and later clicks in a click
  chain do nothing.
- `events.MouseScrollUp` and `events.MouseScrollDown` move the history by three
  physical rows and clamp to its content. Prompt and documentation do not move.
- `events.Resize` recomputes display-column layout at the history content width
  and preserves the logical-row scroll anchor where possible.
- the `ctrl+g` and `escape` bindings clear input and cancel accept. This
  single-screen app reserves Escape for cancellation; no needed Textual action
  conflicts with it.
- `enter` submits `CommandInput`; missing required input enters accept rather
  than parsing an empty string.
- `ctrl+d` exits only when text and chip are empty and no accept is pending;
  otherwise it does nothing. `ctrl+c` exits from any state.

After scrolling or resizing, hover and click always hit-test the newly laid-out
coordinates; cached pre-scroll screen coordinates are not reused.

`main()` runs `PbuiApp` in Textual's ordinary non-inline application mode.
Normal `App.exit`, `Ctrl-D`, and `Ctrl-C` all unwind through Textual's terminal
cleanup. A caught `KeyboardInterrupt` exits without a traceback. The alternate
screen, mouse reporting, cursor mode, and input mode are restored before
control returns to the shell.

## 7. Verification

All automated tests run through uv and avoid the user's live files and process
table. No test imports Textual except `tests/test_terminal.py`.

### 7.1 Pure substrate tests — `tests/test_substrate.py`

At minimum, tests must:

- register arbitrary explicit types without inspecting Python inheritance;
- build nested outer and inner presentations and prove the inner span wins;
- prove a literal field hit returns no presentation;
- accept a matching type and leave state unchanged for a nonmatching click;
- pass a chip's original object by identity without parsing its label;
- remove a chip atomically with Backspace;
- prove `File` and `Directory` exact types are not interchangeable;
- treat a filename containing a space as one span;
- verify display-cell spans for a wide and a combining character;
- retain only the newest 500 logical rows; and
- relayout and hit-test the same retained object after a width change.

Run this layer with:

```console
uv run pytest tests/test_substrate.py
```

### 7.2 Domain tests — `tests/test_domain.py`

Use `tmp_path` to cover ordinary files, directories, a symlink to each, a
broken symlink, missing paths, absolute path capture before cwd changes, display
escaping, spaces as one name, and case-sensitive displayed-name sorting. Prove
that a symlink to a directory classifies as `Directory`, a broken link as
`File`, and the stored link path is not canonicalized to its target.

Run this layer with:

```console
uv run pytest tests/test_domain.py
```

### 7.3 Command tests — `tests/test_commands.py`

Construct `HeadlessListener` with an allowed temporary filesystem root, a fixed
process table, a kill recorder, and an injected own pid. Cover all six commands,
including:

- `ls` dotfiles, names with spaces, sorting, missing/non-directory errors, and
  object-bearing name spans;
- `ps` uid filtering, unreadable-entry skipping, numeric ordering, and the
  listener's own visible pid;
- all `show` detail forms and stale/missing object errors;
- `cd` preserving history, rejecting a file or missing directory, and not
  retargeting an older path;
- `rm` unlinking only a temporary file or link, refusing directories including
  links to directories, confirming success, and reporting a missing path;
- `kill` recording only `SIGTERM`, refusing the injected own pid, pid 1, zero,
  and negative pids, and reporting missing or unsignalable processes;
- unknown commands and forbidden extra arguments; and
- missing arguments entering accept, non-target clicks preserving input, and
  target clicks executing with the object rather than its printed name.

No command test calls production `os.kill`. No test unlinks a path outside its
`tmp_path` root.

Run this layer with:

```console
uv run pytest tests/test_commands.py
```

### 7.4 Headless Textual test — `tests/test_terminal.py`

Use `pytest-asyncio` and `PbuiApp.run_test()` with an injected temporary
filesystem listener. Through Textual's pilot, press `l`, `s`, and `enter`, then
wait for messages to settle. Assert that the listener history model contains a
`File` or `Directory` presentation for a known temporary child and that its
stored path is the expected absolute path. Also assert that the prompt and
documentation widgets remain mounted.

This required test does not synthesize a mouse click. Mouse-coordinate behavior
is covered by pure hit-test tests and the hand check.

Run all tests with:

```console
uv run pytest
```

### 7.5 Live hand check

After automated tests pass, create a fresh temporary directory containing a
subdirectory, a disposable file named `file with space`, and enough extra
entries to wrap on a narrow terminal. Start `uv run pbui`, then perform these
steps only against that temporary directory:

1. Type `cd`, press Enter, hover the directory presentation from an earlier
   `ls` or type the temporary directory path, and enter it. Confirm the prompt
   shows its absolute path.
2. Run `ls` several times. Hover a file and a directory and confirm the exact
   documentation wording changes. Click `file with space` with no command and
   confirm `show` displays its absolute path, classification, size, and mtime.
3. Create or retain a second disposable file. Type `rm` and press Enter.
   Confirm files are green/underlined targets, directories are dim/inert, and
   the documentation line names `File`. Click the disposable file and confirm
   it alone is unlinked. Repeat `rm`, click a directory, and confirm nothing is
   removed and the input still waits.
4. Press `Ctrl-G`; confirm the wait and input clear. Repeat once with Escape.
5. Scroll to an older listing, resize the terminal so rows rewrap, then click an
   older retained name. Confirm `show` receives that object's absolute path,
   not characters at the old screen coordinates.
6. Run `ps`, identify pbui's pid, and click it to see a current process detail.
   Do not run `kill` against a live process during this check.
7. Exit with `Ctrl-D` and verify the ordinary shell screen, cursor, input, and
   mouse behavior are restored. Start once more, exit with `Ctrl-C`, and verify
   the same restoration with no traceback.

This short hand check is the only required exercise against the live process
table and unrestricted filesystem. Remove the temporary directory afterward.

## 8. Acceptance summary

The implementation is complete only when history stores live values with
explicit presentation types; hit testing returns the innermost retained object;
accept highlights only exact acceptable types and passes an atomic object chip;
default left click invokes `show`; the documentation line explains every hover
or refusal; all six commands work through safe test seams and on the live Linux
host; only the terminal layer imports Textual; scroll and resize preserve
object-aware hits; and both normal exit and `Ctrl-C` restore the terminal.

Anything listed as out of scope in section 1 is a follow-on exploration with a
new charter, spec, and checkpoint sequence. It is not a listener checkpoint.
