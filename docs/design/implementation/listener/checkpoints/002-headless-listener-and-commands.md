# listener 002 — Headless listener and commands

**Status.** Ready to implement.

## Goal

Implement the complete headless listener over the reviewed presentation and
domain layers: the real and test-safe filesystem seams, Linux process seam,
input dispatch, contextual accept, default `show` translation, and exactly the
six commands `ls`, `ps`, `show`, `kill`, `cd`, and `rm`.

Stop when the complete command layer is green. Do not add Textual, Rich,
terminal widgets, keyboard or mouse event classes, a documentation line, a
console script, `pbui.__main__`, or a runnable `pbui`.

The implementer receives this checkpoint and the accepted listener
specification. This checkpoint narrows that specification to one independently
testable slice; it does not revise it.

## Identity, authority, and predecessors

- Identity is `(listener, 002)`, spoken **listener 002**.
- [`../spec.md`](../spec.md), especially sections 1, 2, 4.3, 5, and 7.3, is
  the design authority. Preserve it when this checkpoint is silent.
- [listener 000](000-presentation-substrate.md) is implemented and reviewed.
  It supplies explicit types, object-bearing history, `SubstrateState`,
  `AcceptRequest`, atomic `Chip`, `TranslatorTable`, logical rows, layout, and
  hit testing.
- [listener 001](001-domain-objects-and-printers.md) is implemented and
  reviewed. All 46 current tests pass. It supplies `DomainTypes`, immutable
  refs, `TypedDomainValue`, read-only path parsing and classification, safe
  display, domain drawing contexts, composed listing rows, and exact detail and
  result formatters.
- The project root is
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application code
  and tests remain there, never under `docs/`.
- Python remains 3.11 or newer and the package remains `pbui`.

The predecessor APIs are sufficient. Do not redesign them or add a parallel
object, row, type, parser, escaping, or hit-test path. Every command output is
appended through the existing presentation history and drawing contexts.

## Exact file scope

### May create or edit

- `src/pbui/commands.py` (new)
- `tests/test_commands.py` (new)
- `src/pbui/__init__.py`, only if needed to re-export stable command-layer
  names

### Must not edit or create

- `pyproject.toml`, `uv.lock`, `.python-version`, `README.md`, or `AGENTS.md`
- `src/pbui/substrate.py`, `src/pbui/text.py`, `src/pbui/domain.py`, or any of
  their existing tests
- `src/pbui/terminal.py` or `src/pbui/__main__.py`
- a console-script entry or runnable application entry point
- anything under `docs/`, including earlier checkpoints and the specification
- any file outside the project root

If another production or test file appears necessary, stop and return the
checkpoint for correction instead of widening the slice.

## Environment and dependencies

This checkpoint adds no dependency. Runtime dependencies remain exactly
`wcwidth`; development dependencies remain exactly pytest. From the project
root run:

```console
uv sync
uv run pytest
```

Use uv for every Python command. Do not use `pip`, `python -m pip`, `uv pip
install`, Poetry, Pipenv, Conda, Hatch, or globally installed Python packages.
If uv is unavailable, stop and tell the human.

## Headless listener composition

`HeadlessListener` owns one coherent application model:

- its own `PresentationTypeRegistry` and the five `DomainTypes` registered into
  it in their listener 001 order;
- one `PresentationHistory`;
- the standalone and listing domain drawing contexts;
- one current cwd stored as an absolute lexical path;
- one `SubstrateState` for command text, a pending accept request, and an
  optional chip;
- one `TranslatorTable`;
- exactly six command registrations;
- one injected filesystem service; and
- one injected process service.

Construction receives an explicit starting cwd and both services. Production
composition supplies `os.getcwd()`, the production filesystem, and the Linux
process service. Tests inject a cwd under `tmp_path`, a rooted filesystem
adapter, and a fixed process service/kill recorder.

Validate the initial cwd as an existing followed directory through the injected
filesystem and store its lexical absolute spelling. Do not call `os.chdir` at
construction or later. The process-global cwd and the launching shell are never
mutated.

Expose stable read-only access needed by listener 003: current cwd, registry
and domain types, history, input/accept/chip state, translators, and the exact
command names. Do not expose host mutation as a terminal shortcut.

## Filesystem protocol and production service

Define one filesystem protocol extending listener 001's read-only path access
with:

- lexical absolute normalization;
- followed `stat`;
- `lstat`;
- `readlink`;
- directory iteration sufficient to obtain every child name/path once; and
- `unlink`.

The production implementation delegates to `os.path.abspath`, `os.stat`,
`os.lstat`, `os.readlink`, `os.scandir`, and specifically `os.unlink`. It does
not call a shell, recurse for deletion, call `shutil.rmtree`, or use
`Path.resolve`/`realpath` to rewrite a stored final path.

Every path command re-reads current filesystem state. An older presentation's
type is historical context, not permission to trust stale classification.
Expected `OSError`, missing-path, race, and permission failures become one
`Error` presentation and never escape the listener as a traceback.

## Rooted test filesystem

Provide a filesystem adapter constructed with `allowed_root=tmp_path` for
automated command tests. It may delegate successful operations to the real
Python filesystem, but every operation rejects access outside the allowed
root. Canonicalize and retain the root once at construction.

For operations that follow the final component (`stat` and directory
iteration), canonicalize the followed candidate and require it to be the root
or below it. For operations on the final entry itself (`lstat`, `readlink`, and
especially `unlink`):

1. require an absolute normalized candidate;
2. canonicalize the candidate's parent, thereby following every intermediate
   symlink;
3. require that canonical parent to be the root or below it; and
4. operate on the unchanged final component without following it.

Use `os.path.commonpath` or an equivalently component-aware containment check;
string-prefix checks are forbidden. This policy allows unlinking a final
symlink located inside the root, including a broken link, while preventing an
intermediate symlink from escaping the root and deleting an external target.
It also prevents lexical `..` escape. A rejected access raises an ordinary
filesystem error that the listener reports as `Error`.

No automated test may unlink a path outside its `tmp_path` root. Do not add a
memory-only second path semantics when the rooted adapter can safely exercise
real stat, link, directory, and unlink behavior in the temporary tree.

## Process records and protocol

Use one immutable inspected-process record containing at least:

```text
pid: int
real_uid: int
state: readable state word
command: raw decoded command text
```

The process protocol supplies:

- the uid the listener considers its own;
- the pid the listener considers its own;
- `list_for_uid(uid)` returning inspectable matching records;
- `inspect(pid)` performing a fresh inspection; and
- `send_sigterm(pid)` sending or recording exactly `SIGTERM`.

Ordinary tests inject a fixed table plus a recorder. The injected own pid must
be independent of pytest's real pid. A fixed service never reads live `/proc`
or calls `os.kill`.

## Linux `/proc` production service

The production service uses `os.getuid()`, `os.getpid()`, Linux `/proc`, and
`os.kill(pid, signal.SIGTERM)`. It never shells out to `ps`. Permit a custom
proc-root and host-call injection for isolated parser tests, while production
defaults remain `/proc` and the real `os` calls.

For one pid, read both `PROC/PID/status` and `PROC/PID/cmdline`. From `status`
require and parse:

- `Name`, preserving its raw text for fallback;
- the first integer in `Uid` as the real uid; and
- the single state code at the start of the `State` value.

Read `cmdline` as bytes. Replace every NUL byte with one ASCII space byte,
decode with `sys.getfilesystemencoding()` and `surrogateescape`, and retain that
raw decoded string for the domain row/detail formatter to escape once. Do not
trim the resulting spaces. If `cmdline` is empty, use the `Name` field instead.

Map state codes exactly:

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

`list_for_uid` considers only numeric directory names, inspects each, keeps
records whose real uid equals its argument, and returns them in integer-pid
order. It skips a process whose directory disappears or whose required files
or fields are unreadable or malformed. It does not special-case kernel threads;
an empty `cmdline` uses `Name` as above.

`inspect(pid)` uses the same parser and command rule but does not silently skip:
an absent, unreadable, or malformed required record is an ordinary process
inspection failure for `show` or `kill` to present as `Error`. The listener's
own process is included by listing when inspectable. In the real application,
its pid plus command text containing `pbui` makes it identifiable.

## Input-line dispatch

The input is a deliberately small command line, not a shell. On submission:

1. ignore leading whitespace before the command name;
2. take the first whitespace-delimited token as the command name;
3. discard the first complete run of separator whitespace after that token;
4. if characters remain, preserve all of them—including internal and trailing
   spaces—as one argument string; and
5. never parse quotes, escapes, globs, a second argument, pipelines, or
   redirections.

An empty or whitespace-only line does nothing. A complete command parses its
one typed argument, creates the same atomic object/chip path used by acceptance,
and runs. A typed parse failure appends one `Error`, performs no effect, and
clears the editor. A command attempt, whether successful or an expected
failure, clears text, chip, and pending accept after its result.

A missing required argument does not run or clear the command name. Normalize
the editor text to that command name and enter an `AcceptRequest` with the exact
set and a continuation that consumes the accepted chip's stored object:

| Command | Accept set |
|---|---|
| `cd` | `{Directory}` |
| `rm` | `{File}` |
| `kill` | `{Process}` |
| `show` | `{File, Directory, Process}` |

`ls` is the sole optional-argument command: absent means the current cwd and it
runs immediately. `ps` takes no argument and rejects any supplied argument.

The six names are the whole command registry. Unknown names append exactly:

```text
Error: unknown command: NAME.
```

Safely escape the raw command-name field once. A forbidden argument appends:

```text
Error: COMMAND does not take an argument.
```

The `Error: ` prefix comes from the existing Error drawer; stored error
messages do not contain a second prefix.

## Selection, cancellation, and translators

Expose a headless selection operation receiving a retained `Presentation` and
its already-drawn label. Listener 003 will perform coordinate hit testing and
call this operation only for a single left click.

While an accept request is pending:

- an exact acceptable presentation uses `SubstrateState.select_presentation`,
  creates one `Chip`, and calls the pending continuation;
- the continuation passes `chip.value` directly to the command without parsing
  `chip.label`, runs the command, then clears input, chip, and request;
- a nonmatching presentation changes neither input, request, chip, history, nor
  host state; and
- translation is not attempted.

Cancellation delegates to the substrate state: it clears text, pending request,
and chip and performs no command. Listener 003 binds both Ctrl-G and Escape to
this one operation. Expose atomic chip Backspace behavior without building the
cursor editor here.

With no accept pending, selection invokes the explicit translator table for the
presentation. During composition register `show` translators for exactly
`File`, `Directory`, and `Process`. Register no translator for `Text` or
`Error`. A default `show` click passes the stored object directly, appends its
detail/error result, and does not alter current editor text or chip.

## Output helpers and error containment

Append every row through the existing history:

- `ls` and `ps` use listener 001's composed listing-row helpers and listing
  context;
- standalone object labels, `Text`, `Error`, details, confirmations, and the
  empty-directory result use the standalone context and existing domain
  formatters.

Expected host failures never traceback out of a command. Use stable unprefixed
failure messages and let the Error drawer add `Error: `. For OS failures use
listener 001's once-escaping failure composer with these action phrases:

| Operation | Action phrase |
|---|---|
| list directory | `cannot list` |
| inspect/show path | `cannot show` |
| inspect/show process | `cannot show process` |
| change cwd | `cannot change directory to` |
| remove | `cannot remove` |
| inspect or signal for kill | `cannot signal process` |

The subject is the raw path or integer pid and the final field is the raw OS or
service error. This yields rows such as
`Error: cannot remove /tmp/missing: No such file or directory.` without double
escaping. Parser failures may present their existing `DomainParseError` message
as one Error row.

Safety refusals are stable Error messages without an OS suffix:

```text
refusing to signal process PID.
refusing to remove directory PATH.
```

Safely escape the path. A defect in pbui itself may still raise; do not blanket
catch `BaseException`, `KeyboardInterrupt`, `SystemExit`, assertion failures, or
arbitrary programming errors.

## `ls`

`ls` accepts an optional `Directory`; no argument constructs a directory ref
for the current cwd. Before listing, revalidate the stored path with followed
`stat` and require a directory. Do not change cwd.

Iterate the injected filesystem once and present every current child exactly
once. Include dotfiles and exclude only `.` and `..`. Normalize each child to an
absolute lexical path, classify it with followed `stat` plus broken-link
handling, and store a current `FileRef` or `DirectoryRef` in its name
presentation. A symlink to a directory is `Directory`; a symlink to a
non-directory or a broken final symlink is `File`.

Sort by listener 001's escaped displayed-basename key, Unicode code-point order
and case-sensitive. Append one exact path listing row per child and no heading.
If there are no children, append the exact Text result
`Directory is empty: ABSOLUTE_PATH`. A missing, non-directory, inaccessible, or
racing path appends one Error and does not change cwd.

## `ps`

`ps` accepts no argument. Ask the process service for records whose real uid
equals the injected listener uid, sort defensively by integer pid, and append
one exact process listing row per record with no heading. Only the pid token is
a `Process` presentation storing `ProcessRef(pid)`; state and raw command text
are literal fields formatted by listener 001.

An inspectable own pid is not filtered out. Entries the production service
cannot inspect are skipped by that service. An expected failure of the overall
listing becomes one Error and does not terminate the listener.

## `show`

`show` accepts exactly `File`, `Directory`, or `Process`.

For either stored path reference, re-read `lstat` and followed `stat`. Report
the path's **current** followed classification even if it differs from the
presentation's historical type:

- a current regular/non-directory path uses listener 001's exact file detail
  with followed size and mtime;
- a current directory uses exact directory detail with no size or mtime;
- a live final symlink adds its raw `readlink` target after the type, retains
  the stored link path, and otherwise uses followed target classification and
  metadata; and
- a broken final symlink reports `file (broken symlink)`, its raw link target,
  and lstat size and mtime.

Append the resulting exact detail as one `Text` presentation. A missing,
inaccessible, or racing path appends one Error.

For `ProcessRef`, call `inspect(pid)` every time and format its current pid,
raw command, and readable state as one Text detail. A process that exited or
cannot be inspected appends one Error. Never use `repr` of a stored object.

## `cd`

`cd` accepts `Directory` only. Revalidate the stored path with followed `stat`
and require a directory. On success, replace only the listener's cwd field with
that stored absolute lexical path. Keep all history and append no success row;
the later prompt change is the confirmation.

There is no `$HOME` default. A missing path, inaccessible path, or current file
appends one Error and leaves cwd and history otherwise unchanged. Never call
`os.chdir`.

## `rm`

`rm` accepts `File` only. At effect time, reclassify the exact stored path with
followed `stat` and `lstat`:

- refuse a current directory, including a final symlink whose target is a
  directory, without calling unlink;
- unlink a current non-directory path;
- unlink a broken final symlink itself; and
- report a missing, inaccessible, refused, or failed unlink as one Error.

Call the injected filesystem's `unlink` on exactly the stored path. Never
follow the final link for deletion, recurse, remove a directory, or use a shell.
On success append exactly `Removed file: ABSOLUTE_PATH` as Text.

## `kill`

`kill` accepts `Process` only and offers no signal choice. Before inspection or
signaling, refuse pid 1, every pid below 1, and the process service's injected
own pid. A refusal calls neither `inspect` nor `send_sigterm` and appends one
Error.

For another pid, call `inspect(pid)` freshly; only then call
`send_sigterm(pid)`. The production method sends exactly
`os.kill(pid, signal.SIGTERM)`. On success append exactly
`Sent SIGTERM to process PID.` as Text. An absent, exited, inaccessible, or
unsignalable process appends one Error. Never offer or send `SIGKILL`.

## Focused tests

Add `tests/test_commands.py`. Except for the one isolated production-SIGTERM
case below, use the rooted temporary filesystem, fixed process table, and kill
recorder. At minimum prove all of the following:

1. `HeadlessListener` owns one registry with the five exact types, a bounded
   history, injected services, absolute cwd, exactly six command names, and no
   Textual/Rich dependency; construction and `cd` never change `os.getcwd()`.
2. Input splitting ignores leading whitespace, keeps the first token as the
   command, discards only the first separator run, and preserves the remainder
   as one argument including internal/trailing spaces. Empty input does nothing.
3. Unknown commands and forbidden `ps` arguments produce the exact safely
   escaped Error wording and clear the input without raising.
4. `ls` covers dotfiles, a name containing spaces, case-sensitive displayed
   sorting, an empty directory, ordinary files/directories, a symlink to each,
   a broken symlink, missing/non-directory/permission errors, and object-bearing
   name spans whose literal type columns do not hit.
5. The rooted adapter rejects read and write escape through `..` or an
   intermediate symlink, permits safe operations below the root, and can unlink
   a final symlink inside the root without touching its external target.
6. `ps` filters by real uid, skips unreadable/malformed production entries,
   sorts numerically, retains the own pid, presents only pid tokens, converts
   every cmdline NUL to a space, decodes with filesystem encoding plus
   surrogateescape, and falls back to `Name` only for empty cmdline. Exercise
   production parsing with an isolated fake proc-root; do not inspect the live
   process table for these cases.
7. State mapping covers every named code and an unknown code. Direct production
   inspection reports missing/malformed data rather than silently skipping it.
8. `show` covers a regular file, directory, live symlink to each, broken
   symlink, stale/missing path, a path whose classification changed since its
   presentation, a current process, and an exited/uninspectable process, with
   exact one-row detail text.
9. `cd` preserves history, updates only listener cwd on a current directory,
   leaves cwd unchanged for a file/missing path, has no home default, and does
   not retarget an older absolute path presentation.
10. `rm` unlinks only a file or final symlink under `tmp_path`, confirms exact
    success, reports a missing path, and refuses both a directory and a symlink
    to a directory without invoking unlink. No test path outside `tmp_path` is
    removed.
11. Ordinary `kill` tests record exactly `SIGTERM` for one inspectable process,
    confirm exact success, report missing and signaling failures, and refuse the
    injected own pid, pid 1, zero, and a negative pid without recording a call.
12. Missing `cd`, `rm`, `kill`, and `show` arguments leave the command name in
    input and enter exactly the specified accept set. Missing `ls` runs on cwd;
    missing `ps` runs immediately.
13. A non-target click during accept changes nothing. A target click executes
    once with the original stored object by identity rather than parsing its
    label, then clears request, chip, and input. Cancellation clears without an
    effect, and chip Backspace remains atomic.
14. With no accept pending, explicit translators invoke `show` for exactly
    `File`, `Directory`, and `Process`, preserve editor text, and do nothing for
    `Text`, `Error`, literal hits, or absent presentations.
15. Expected filesystem/process/parser failures append Error and keep the
    listener usable for a subsequent successful command; no expected failure
    escapes as a traceback.
16. Existing substrate and domain tests remain unchanged and green.

### The sole production-SIGTERM integration test

Exactly one automated test may call production `os.kill`. Start one child with:

```python
subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
```

Verify that exact child is alive. Construct a listener with the production
process service and a rooted temporary filesystem, then invoke `kill` through
the listener for `ProcessRef(child.pid)`. Wait for that exact child and assert:

```python
child.returncode == -signal.SIGTERM
```

Use `try/finally`. Cleanup after failure or timeout may terminate or kill that
same child only and must reap it. The test never signals pytest, the listener's
own pid, pid 1, another discovered pid, a process-group id, or any process it
did not create. No other test constructs a production service with real
`os.kill` or calls the production signaling path.

## Verification and completion

Run the complete test suite through uv:

```console
uv run pytest
```

The checkpoint is complete when all substrate, domain, and command tests pass;
no dependency or entry-point metadata changed; only the allowed files changed;
`pbui.commands` has no Textual or Rich import; all ordinary tests use safe
seams; and the only live signal was SIGTERM sent to and reaped from the test's
own isolated child.

Stop after reporting the passing command and changed files. Do not start
listener 003.
