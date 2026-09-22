# Charter — a presentation listener in the terminal

**Status.** Handoff from the high-level discussion in Grok (journal
`2026-09-21-presentation-ui`) into a **design conversation**. Not a
checkpoint. Not an implementer assignment. This file lives in
`docs/design/implementation/listener/`. The specification will live
beside it as [`spec.md`](spec.md). Checkpoint files will live in
`checkpoints/` beside it. Map: [`README.md`](README.md). The project
root, where the program will live, is
`/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

**Your job.** Turn this charter into a specification for a small
Python program, **pbui**: a full-screen terminal listener whose
history stores live objects, not text. Six commands present and
accept files, directories, and processes. Then **stop**. Do not
write checkpoints. Do not implement. Do not specify a Python
evaluator, pipelines, a second graphical presenter, or a desktop.

If you have been told to read this file, this is the whole assignment.

---

## 1. How this conversation works

1. Read this charter and [`README.md`](README.md). Do not rely on
   the Grok transcript. This file is the assignment.
2. Record the locked decisions in §4. Resolve the open questions in
   §5.
3. Write `spec.md` in this folder
   (`docs/design/implementation/listener/`). A later
   checkpoint-manager conversation slices **listener 000**, `001`,
   … under `checkpoints/` in this same folder, one checkpoint per
   conversation. Later explorations get their own folders beside
   `listener/`; they are not slices of this spec.
4. Stop. The human reviews the spec. Do not write those checkpoint
   files.

The checkpoint manager and the implementers will not have this
charter. Put every rule they need in the specification.

Keep the spec **small enough to slice**. A shell grammar, a Python
REPL, object pipelines, popup menus, planned commands, a canvas
UI, and a C# port are defects in this document.

## 2. Predecessors

None. There is no existing code to extend and no library whose API
is law.

Two places, and they stay separate:

| Place | What goes there |
|---|---|
| `docs/design/implementation/listener/` | This charter, `spec.md`, and `checkpoints/` |
| Project root `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/` | The uv project: `pyproject.toml`, the `pbui` package, `tests/` |

The implementers will create the uv project at the project root
with `uv init` (see §4.2). They will not create it inside `docs/`,
and they will not create the environment or install dependencies
any other way. The designer does not run `uv init`. A later
exploration is a new folder under
`docs/design/implementation/`, with its own charter, spec, and
checkpoints. It does not reuse this spec's checkpoint numbers.

## 3. Bar (acceptance)

The specification is wrong unless all of these are true:

1. **History holds objects.** After `ls`, each displayed name is a
   presentation of a `File` or a `Directory`. The presentation
   stores the object. A later command receives that object. It
   does not parse the characters that were drawn.
2. **Accept is contextual.** Typing `rm` and nothing else waits
   for a `File`. Presentations that are not acceptable `File`s
   do not highlight as targets. Clicking an acceptable `File`
   supplies the object and runs the command. A name containing a
   space is one presentation.
3. **A click with nothing waiting shows the object.** Left click
   on a presentation when no accept is pending runs `show` on
   that object.
4. **The documentation line is part of the product.** A line above
   the prompt states what a click on the presentation under the
   pointer will do, or why that click will not satisfy the
   pending accept.
5. **The six commands work on the real machine, and the tests do
   not.** `ls`, `ps`, `show`, `kill`, `cd`, and `rm` are the whole
   command set. Automated tests exercise them through fakes and a
   temporary directory. They must not unlink the user's files or
   signal arbitrary processes. A short hand check is the only
   required exercise against the live machine.
6. **The substrate does not import the UI.** Presentation types,
   the history, hit testing, accept, and translators are specified
   as plain Python with no Textual import. The terminal screen is
   a later layer over that model.
7. **Leaving the program restores the terminal.** Normal exit and
   Ctrl-C both return the emulator to the shell the user started
   from.

## 4. Locked decisions (record these; do not reopen)

### 4.1 What this is

pbui is one listener. It takes the terminal's alternate screen,
keeps its own scrollable history, and pins an input line at the
bottom. The emulator's scrollback is not the history. If the
drawn text moves, the hit regions move with it, because both are
owned by the program.

A presentation is three things: a Python object, a presentation
type, and the span of the history it occupies. `present` appends
one to the history. `accept` reads a value of a given presentation
type. The mouse asks the history what is under the pointer.

Presentation types are a registry the program defines. They are
not "whatever Python's class tree happens to do." A presentation
type may be used for a value whose Python class is uninteresting.
Do not build an object system, and do not generate the registry by
reflecting over methods.

The application objects and the drawing of those objects are
separate. This spec has one drawer: terminal text. The separation
exists so a later presenter can draw the same objects on a canvas.
This spec does not build that presenter, and it must not store
object identity only inside a widget.

### 4.2 Host and tools

- Language: Python, minimum 3.11.
- Project tool: **uv**, for the whole Python lifecycle. The spec
  copies the following into its own tool section so every checkpoint
  can repeat the commands its slice needs. An implementer who never
  sees this charter still has to follow them.
  - Create the application at the project root with `uv init`.
    The spec names the exact command, including `--package` when
    §5.4 chooses a `src/` layout.
  - Create and refresh the environment with `uv sync`. Do not
    create a virtualenv by hand.
  - Add runtime dependencies with `uv add` and development
    dependencies with `uv add --dev`. Textual is a runtime
    dependency. The test runner is a development dependency.
    Both land in `pyproject.toml` and `uv.lock`.
  - Run the program and the tests with `uv run`. The spec names
    those invocations.
  - If `uv` is not installed, stop and tell the human. Do not
    fall back to `pip`, `python -m pip`, Poetry, Pipenv, Conda,
    Hatch, or a globally installed package.
  - `uv pip install` is not how this project records a dependency.
- UI host for the last slice: **Textual**. Textual owns the
  alternate screen, resize, mouse events, and terminal restore.
- Package import name: `pbui`. Console script: `pbui`.
- Layout of the source tree is open (§5). The import name and the
  script name are not.

Textual is not imported by the substrate. Presentations are not
Textual widgets. One history surface draws many presentations.
An implementer who builds a `Button` per file is wrong.

### 4.3 Screen

Three regions, top to bottom:

1. Scrollable history.
2. Documentation line.
3. Prompt and input.

The prompt shows the listener's current working directory as an
absolute path. Exact punctuation is open (§5). The documentation
line is always present, including when the pointer is over empty
history.

Scrolling the history does not scroll the prompt away and does not
drop presentations that are still inside the retained history.
Resize recomputes spans. A presentation's span is in the display
columns the history surface uses, not in raw Python string indices.

The input line is a small editor, not a shell. There is no
up-arrow command history in this spec.

Ctrl-G clears the input line and cancels a pending accept. The
spec also binds Escape to that same action unless Textual already
uses Escape for something this screen needs. If it does, say so,
and keep Ctrl-G.

### 4.4 Presentation types in this spec

| Type | Denotes | Printer, roughly |
|---|---|---|
| `File` | A non-directory path | The file's name in a listing; absolute path where a single path is the whole presentation |
| `Directory` | A directory path | Same rule as `File` |
| `Process` | A pid | A single token that includes the pid |
| `Text` | Unstructured text | The text |
| `Error` | A failure message | The message |

`Error` is not acceptable where `File`, `Directory`, or `Process`
is required. `Text` is not either.

`Directory` is not a subtype of `File` for accept. `cd` accepts
`Directory` only. `rm` accepts `File` only. A value that stat
classifies as a directory must not be offered to `rm`.

Classification follows `stat` (symlinks followed) for the type:

- A symlink to a directory is a `Directory`.
- A symlink to a non-directory is a `File`.
- A broken symlink is a `File`.
- `rm` unlinks that path. It does not follow a symlink and delete
  the target. `rm` on a `Directory`, including a symlink to a
  directory, is a refusal.

Paths stored in presentations are absolute, resolved at the moment
of presentation. A later `cd` does not retarget old presentations.

A `File` or `Directory` whose path no longer exists still denotes
that path. Commands that need the filesystem produce an `Error`
presentation instead of raising out of the listener.

A `Process` stores a pid. `show` and `kill` re-read its state.
If it has exited or cannot be inspected, the command produces an
`Error` (for `show`) or a refusal (for `kill` when the process
cannot be signaled). The listener does not raise.

### 4.5 Hit testing and nesting

The innermost presentation containing the pointer wins.

An `ls` row is composed. The name span is a `File` or `Directory`
presentation. Other fields on that row (size, mtime, or whatever
§5 chooses) are `Text` or are not presentations. Clicking the name
selects the file. Clicking a non-presentation field selects
nothing. A filename containing spaces is entirely inside the name
span.

`ps` rows follow the same rule. The pid-bearing span is the
`Process`. Clicking it selects that process.

Hit testing covers only presentations still in the retained
history.

### 4.6 Accept, chips, and translators

Every command in §4.7 takes at most one argument. The command name
is one token. The remainder of the line, if any, is the typed
argument, so a typed path may contain spaces. There is no quote
syntax and no second argument. Do not specify a shell grammar.

A click that satisfies an accept does not insert those characters
into a text buffer to be parsed again. It stores the object as one
atomic argument. The input line may draw the object's printer
output, but Backspace removes the whole argument, not one character
of that drawing. Call that drawn argument a chip.

While an accept is pending:

- Presentations whose type is acceptable highlight as targets.
- Presentations of another type do not.
- A click on a target supplies the chip and, for these commands,
  runs the command.
- A click on a non-target does not supply it and does not clear
  the input. The documentation line says it is not a target.
- Ctrl-G cancels.

While no accept is pending, the default translator is `show`.
Left click runs `show` on the innermost presentation if its type
is `File`, `Directory`, or `Process`. Clicking `Text` or `Error`
does nothing useful beyond what the documentation line says.

Do not specify a popup menu, a right-click menu, middle-click
commands, or gesture recognition beyond left click and hover.

Typed input uses that presentation type's parser:

- `File` and `Directory` parsers accept one path string, absolute
  or relative to the listener's cwd, and then classify it with the
  rules in §4.4. A relative path is stored absolute.
- A typed `Directory` that is not a directory is an `Error`, and
  the command does not run its effect.
- A typed `File` that is a directory is an `Error` for `rm`.
- `Process` parses a base-10 pid.

Empty typed input when an argument is required enters accept
rather than parsing an empty string. `ls` is the exception: no
argument means the cwd (§4.7).

### 4.7 Commands

The listener starts in the process's cwd.

| Command | Argument | Effect |
|---|---|---|
| `ls` | optional `Directory`; absent means cwd | Present each child as a `File` or `Directory` row. Do not present `.` or `..`. Do present dotfiles. One list, sorted by displayed name, Unicode code-point order, case-sensitive. |
| `ps` | none | Present processes whose real uid equals the listener's uid, skipping those the program cannot inspect. Include enough that the listener's own pid is visible and identifiable in `show`. Read `/proc` (or the platform equivalent the spec names). Do not shell out to `ps`. |
| `show` | `File`, `Directory`, or `Process` | Append a detail presentation. Fields are open (§5). They must include the absolute path for a path, and the pid plus a current state for a process. `repr` of the Python object is not the detail. |
| `cd` | `Directory` | Change the listener cwd. Prompt updates. History is kept. `cd` with no argument waits for a `Directory`. There is no default of `$HOME`. |
| `rm` | `File` | Unlink that path. Do not recurse. Do not remove a directory. Success appends a short confirmation presentation (`Text` is fine). Failure appends `Error`. |
| `kill` | `Process` | Send `SIGTERM` only. Refuse the listener's own pid and refuse pid 1 and anything below 1, with an `Error`. Do not offer `SIGKILL`. |

`ls` of a path that is not a directory appends `Error` and does not
change cwd. `cd` to a missing directory appends `Error` and does
not change cwd.

Unknown command names append `Error` and do not raise.

Commands that fail must not escape into a traceback on the
terminal. A defect in pbui itself may still traceback; a missing
file, a bad pid, or a permission error must not.

### 4.8 Process and filesystem seams

Production `ps` reads the live process table. Production `kill`
calls `os.kill`. Production `rm` calls `os.unlink`. Production
`ls`, `cd`, and `show` use the real filesystem.

The spec names a seam so tests substitute both:

- a filesystem root (a temporary directory), and
- a process table plus a kill recorder.

Automated tests use those seams. They must not delete paths outside
the temporary directory and must not signal a process the test did
not create. Prefer the recorder over signaling even a test-created
process, unless a test's point is the production `os.kill` path,
in which case the test creates the child and only signals that
child.

The listener's own-pid refusal is specified against "the pid pbui
considers to be itself," so a test can set that pid without
killing the test runner.

### 4.9 What `ps` is allowed to ignore

This spec targets Linux, because `/proc` is the locked source.
The spec may name the `/proc` fields. It does not have to support
macOS or Windows. If some `/proc` files are unreadable, skip that
process.

Do not present kernel threads as a special category. Skipping
processes that are not uid-matched, or that cannot be inspected,
is enough.

### 4.10 Verification the spec must name

- Pure tests, no Textual app and no TTY, for the substrate: build a
  history, hit-test an inner span versus an outer span, accept a
  matching type, reject a non-matching click, round-trip a chip as
  an object rather than as parsed text, and treat a name containing
  a space as one span.
- Pure tests, no TTY, for the six commands against the seams in
  §4.8, including the refusals (directory `rm`, own-pid `kill`,
  pid 1, missing path, `cd` not following a file).
- One headless Textual test that starts the app, runs `ls` against
  the temporary filesystem seam, and observes that a presentation
  for a known child exists in the history model. This test does
  not have to synthesize a mouse click if the harness makes that
  awkward. Say so if it does not.
- One hand check, written as steps a person can follow, covering:
  hover updates the documentation line; click with no command runs
  `show`; `rm` then click a file unlinks it; a directory does not
  offer itself to `rm`; Ctrl-G cancels; scroll and resize, then a
  click on an older name still passes the object.

The spec names the test paths and the `uv run` command.

### 4.11 Slice order

Structure the spec as four layers, in this order, each testable
without the later layers except as noted:

1. **Substrate.** Types, presentations, history, spans, innermost
   hit test, accept, chips, the default `show` translator. No
   filesystem and no Textual.
2. **Domain.** `File`, `Directory`, `Process`, `Text`, `Error`,
   parsers, absolute paths, stat classification. No commands yet.
3. **Commands.** The six commands on a headless listener using the
   seams. No Textual.
4. **Terminal.** The Textual screen: history surface, documentation
   line, prompt, input, hover, click, chips, restore-on-exit. This
   layer is the only one that imports Textual.

A layer may become more than one checkpoint if the manager cannot
hold it in one implementation conversation. The spec should say
which layer that is likely to be, if any. Do not add a fifth layer
for a feature in §4.12.

### 4.12 Out of this spec

- A Python (or any other) expression evaluator beside the six
  commands
- Pipelines, redirection, quoting, globs, and multi-argument
  commands
- Running external programs and presenting their stdout
- Up-arrow input history
- `User`, sockets, systemd units, git repositories, and other
  domain objects
- A second, graphical presenter, icons, or a spatial directory
- Popup or right-click menus, planned commands, annotations, and
  delete-marks
- Window-manager objects: windows, scrollbars, desktops, buffers
- A C# / .NET port
- macOS and Windows process listing
- Confirmation dialogs before `rm` or `kill`
- Making the terminal emulator's own scrollback mouse-sensitive
- Editing Ciccarelli or Genera documents, or reimplementing CLIM

Those are follow-ons. The spec may name them in one paragraph so
an implementer does not "helpfully" start them. It does not design
them.

## 5. Open questions (resolve these in the spec)

### 5.1 Wording and columns

Locked behavior is in §4.4, §4.5, and §4.7. Choose the exact
printer strings and the extra columns on an `ls` row, a `ps` row,
a `show` detail, an `Error`, and the `rm` confirmation.

Every row must still satisfy the hit-test rule: the name (or the
pid span) is the object, and a space inside a filename is inside
that span.

`show` of a `File` includes the absolute path, the classification,
the size, and the mtime. `show` of a `Directory` includes the
absolute path and that it is a directory. `show` of a symlink
includes the link target string from `readlink`, in addition to
the followed classification. `show` of a `Process` includes the
pid, the command name, and a state word a person can read
(`running` is enough when the process is alive). Add fields only
when they help the hand check.

### 5.2 Three looks

Hover, acceptable target during accept, and inert during accept
are three different visual treatments. Pick treatments Textual can
draw. Inert must not look like a target. The documentation line
still carries the words; the treatment is reinforcement, not a
replacement for that line.

### 5.3 How much history

Retention is finite. Pick the bound and the unit (presentations or
rows). Drop from the oldest end. The bound must be large enough
for the hand check: several `ls` listings can sit above the
current one and the older names must still be clickable without
the user raising the bound. A bound of a few hundred rows is the
expected range. Do not specify an unbounded history.

### 5.4 Source layout

Code and tests live at the project root, not under `docs/`. Pick
`src/pbui/` or a top-level `pbui/`. Stay with one package named
`pbui` and a console script named `pbui`. Name the modules so the
four layers in §4.11 are visible in the tree. Tests live under
`tests/` at the project root, not inside the package and not beside
this charter.

### 5.5 Prompt and documentation wording

The prompt includes the absolute cwd. Pick the rest of the string,
including how a pending accept is visible on the prompt or the
documentation line (the type being accepted has to be readable
without hovering).

Pick the documentation-line sentences for: pointer on empty
history; pointer on a `File` with no accept; pointer on a `File`
while accepting `File`; pointer on a `Directory` while accepting
`File`; pointer on `Text`.

### 5.6 Textual seams that the last layer must state

Name the widget (or widgets) that are **not** presentations: the
screen, the history surface, the documentation line, the input.
State which Textual mouse and key events map to hover, left click,
scroll, Ctrl-G, Escape, and Enter.

State that Enter with a complete command runs it, and Enter with a
missing required argument leaves the user in accept rather than
running an empty parse.

If the headless Textual test in §4.10 cannot click, the hand check
covers the mouse and the headless test covers "the history model
received the presentations."

## 6. Authority

This charter is the design. The following are background, not
requirements to expand:

- Eugene C. Ciccarelli IV, *Presentation Based User Interfaces*,
  MIT AI Lab AITR-794 (1984), in the sibling journal
  `2026-09-21-presentation-ui`. Useful for the words "presentation",
  "presenter", and "recognizer." Do not implement PSBase, PPSCalc,
  or the icon/menu/annotation desktops.
- The Genera Dynamic Lisp Listener interaction this prototype
  copies is: output history retains the object; `present` and
  `accept` are the two directions; a click during accept supplies
  the object; a click otherwise runs the default command. Scott
  McKay, William York, and Michael McMahon, "A Presentation
  Manager Based on Application Semantics" (UIST 1989), is the
  short account of that mechanism. Do not implement Dynamic
  Windows or CLIM.

If a Textual behavior makes a locked rule awkward, keep the rule
and choose a different Textual facility. If no facility can do it,
say so in the spec as a single named deviation. Do not silently
drop innermost hit testing, chips, or the documentation line.

## 7. Handoff reminder

The next conversation after the spec is reviewed is a checkpoint
manager. It reads `spec.md` only. It writes one checkpoint under
`checkpoints/`, then stops. Identity is **listener 000**, then
**listener 001**, and so on. The spec's four layers are the
intended order.
