# listener 001 — Domain objects and printers

**Status.** Ready to implement.

## Goal

Add the listener's five explicit domain presentation types, immutable path and
process references, path normalization and read-only classification, typed
argument parsers, safe one-row display escaping, pure domain drawers, and the
exact row/detail wording consumed by later commands.

Stop when this layer is green. Do not add the headless listener, command
registry, filesystem mutation, `/proc` reading, process signaling, Textual,
Rich, a console script, or a runnable `pbui`.

The implementer receives this checkpoint and the accepted listener
specification. This checkpoint narrows that specification to one independently
testable slice; it does not revise it.

## Identity, authority, and predecessor

- Identity is `(listener, 001)`, spoken **listener 001**.
- [`../spec.md`](../spec.md), especially sections 1, 2, 4, and 7.2, is the
  design authority. Preserve it when this checkpoint is silent.
- [listener 000](000-presentation-substrate.md) is implemented and reviewed.
  Its 15 tests pass. It supplies the explicit `PresentationTypeRegistry`,
  identity-compared `PresentationType`, `PresentationHistory`, `DrawingContext`,
  drawer table, fragments, logical rows, layout, and pure hit testing.
- The project root is
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application code
  and tests remain there, never under `docs/`.
- Python remains 3.11 or newer and the import package remains `pbui`.

The predecessor APIs are sufficient for this slice. Do not repair, redesign,
or bypass them. In particular, domain rows create presentations through
`DrawingContext.present` / `present_row`; they do not construct fake text spans
or recover values by parsing labels.

## Exact file scope

### May create or edit

- `src/pbui/domain.py` (new)
- `tests/test_domain.py` (new)
- `src/pbui/__init__.py`, only if needed to re-export stable domain names

### Must not edit or create

- `pyproject.toml`, `uv.lock`, `.python-version`, `README.md`, or `AGENTS.md`
- `src/pbui/substrate.py`, `src/pbui/text.py`, or
  `tests/test_substrate.py`
- `src/pbui/commands.py`, `src/pbui/terminal.py`, or
  `src/pbui/__main__.py`
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

## The five domain presentation types

Register exactly these five entries in an application-supplied
`PresentationTypeRegistry`, in this order:

| Name | Stored value |
|---|---|
| `File` | `FileRef(path)` |
| `Directory` | `DirectoryRef(path)` |
| `Process` | `ProcessRef(pid)` |
| `Text` | one-row product text stored as a string |
| `Error` | one-row failure message stored as a string |

Return or retain a small immutable aggregate giving later layers explicit
access to all five registered entries. Do not create a module-global registry:
`HeadlessListener` will own its registry in listener 002. Re-registering into a
registry that already contains one of the exact names fails through the
predecessor's ordinary duplicate-name rule.

`File` and `Directory` are distinct exact presentation types. Neither accepts
the other, even if their Python reference classes are related or hold the same
path spelling. `Text` and `Error` are never acceptable as path or process
types. No compatibility is inferred from a Python class.

## Immutable stored references

Implement immutable value objects:

```text
FileRef(path: str)
DirectoryRef(path: str)
ProcessRef(pid: int)
```

Every stored path is an absolute lexical path. The path constructors reject a
non-string or non-absolute path; callers normalize before construction.
`ProcessRef` stores an exact Python integer, not `bool`, a float, or numeric
text. It does not reject pid 1, zero, or negative pids: safety refusals belong
to `kill` in listener 002.

The references carry no cached `stat`, process state, display label, cwd, or
service object. Their path or pid remains authoritative after the host changes.

## Read-only path access and normalization

Provide a small structural read-only path-access contract sufficient for this
layer: lexical absolute normalization relative to an explicit cwd, followed
`stat`, and `lstat`/lexistence. Supply a production implementation using
`os.path.abspath`, `os.stat`, and `os.lstat`. Keep it narrow: directory
iteration, `readlink`, unlink, an allowed-root policy, and all mutations belong
to the command-layer filesystem service in listener 002.

Normalization of an input path is exactly:

1. if the input is relative, join it to the listener's explicit absolute cwd;
2. apply `abspath` so `.` and `..` components are resolved; and
3. do **not** apply `realpath`, `resolve`, or any operation that follows the
   final symbolic link.

The returned spelling is captured immediately in the reference. A later cwd
change cannot retarget it. A symlink reference retains the link pathname, not
the target pathname.

Classification uses followed `stat`:

- a successful directory result is `Directory` plus `DirectoryRef(path)`;
- every other successful result is `File` plus `FileRef(path)`;
- when followed `stat` fails but `lstat` shows a final path entry, treat that
  unresolved or broken final link as `File`; and
- a genuinely absent path can still be represented as `FileRef(path)` where a
  parser permits absence.

Return the explicit registered presentation type together with the stored
value. Do not make later callers infer a presentation type from `isinstance`.
Unexpected access errors must be expressible as an ordinary domain parse or
classification failure for listener 002 to turn into an `Error`; do not print,
exit, or mutate the filesystem here.

## Typed argument parsers

Parsers receive the raw one-argument string, the listener's explicit cwd, the
five registered domain types, and the read-only path access. They return the
stored object together with its exact registered presentation type, or raise a
small domain parse error carrying a human-readable failure message. They never
append history or perform command effects.

Implement these exact rules:

- **Directory:** normalize the whole input as one path string and succeed only
  when current followed `stat` says directory. A file, broken link, absent
  path, or inaccessible path is a parse failure.
- **File:** normalize the whole input as one path string and reject it only
  when current followed `stat` says directory. A regular file, non-directory
  symlink target, broken final symlink, or absent path produces `FileRef`.
- **Process:** accept exactly an optional `+` or `-` followed by one or more
  ASCII decimal digits. Reject an empty string, whitespace, surrounding junk,
  a decimal point, and non-ASCII digit forms. Convert with base ten and return
  its canonical integer in `ProcessRef`. Do not apply pid safety checks.
- **Show union:** first normalize the raw string as a possible path. If that
  path currently exists or lexists, classify it as `File` or `Directory`.
  Otherwise, a string matching the exact signed-decimal process grammar becomes
  `Process`; every other string becomes an absent `File`. This ordering means a
  real path named `123` is a path, not a process.

Do not strip typed input. Spaces are part of the one path argument, including
leading or trailing spaces after command dispatch has separated the command
name. There is no quote, escape, glob, multi-argument, or shell grammar.

## Safe one-row display strings

Implement one reusable pure escaping function. It preserves printable Unicode,
ordinary spaces, brackets, quotes, and other markup-looking text literally. It
escapes:

| Input | Display text |
|---|---|
| backslash | `\\` |
| LF | `\n` |
| CR | `\r` |
| tab | `\t` |
| another non-printable byte-range code point | lower-case `\xNN` |
| another non-printable BMP code point, including an unpaired surrogate | lower-case `\uNNNN` |
| another non-printable non-BMP code point | lower-case `\UNNNNNNNN` |

Use fixed-width hexadecimal digits. These transformations affect display only;
stored paths, process command text, OS messages, and input strings remain
unchanged. The result must contain no literal newline, carriage return, tab,
other control code point, or unpaired surrogate that can reach terminal
layout. Do not apply Rich or Textual markup processing.

Use this function for path labels and for raw process names, OS error text, and
echoed command names when the later command layer asks domain formatting helpers
to render them. Do not escape a completed product row a second time; literal
separators such as ` | ` and display escapes already inserted into fields must
remain single.

## Pure drawers and path modes

Register pure drawers for all five exact types into an application-supplied
`DrawingContext` or its drawer table. Support two explicit path-label modes so
later commands do not bypass the presentation operation:

- **standalone:** a `File` or `Directory` draws its escaped absolute path;
- **listing:** a `File` or `Directory` draws its escaped basename.

It is acceptable and expected to use two separately configured drawing
contexts/tables, one for each path mode. Presentation ids are already globally
unique and every produced `HistoryRow` carries its own presentations. Do not
add a display-mode field to `FileRef` or `DirectoryRef`, and do not manually
construct a `PresentedFragment` to evade the registered drawer.

The other drawers are mode-independent:

- `Process` draws canonical `str(pid)` with no spaces;
- `Text` draws the supplied already-composed one-row product string; and
- `Error` draws `Error: ` followed by the supplied already-composed one-row
  failure message.

Validate obvious value-shape misuse clearly, but remember that exact
presentation compatibility still comes from the registry entry, not the
Python class.

## Listing order and composed rows

Sort path entries by their escaped basename in Unicode code-point order,
case-sensitively. Do not use locale collation, natural-number ordering, or
case-folding. Dotfiles are ordinary names. Directory iteration and excluding
`.` and `..` belong to listener 002; this layer receives candidate references
and sorts them.

Provide pure composed-row helpers with these exact outputs:

```text
file       NAME
directory  NAME
PID  STATE  COMMAND
```

For a path row, `NAME` is the sole `File` or `Directory` presentation and is
drawn in listing mode. The type word and spacing are literal, unpresented text.
For a process row, only the canonical `PID` token is a `Process` presentation;
the two double-space separators, readable state word, and safely escaped raw
command text are literal. There is no heading row.

These helpers must call the same registered `DrawingContext.present` operation
as standalone rows. A filename containing spaces is one complete presented
fragment. Layout and hit testing must therefore return the object from the name
or pid and nothing from the type, state, command, separators, or padding.

## Exact detail and result formatting

Add pure formatting helpers for the complete strings below. They return
one-row product text for later presentation as `Text`; they do not read the
host or append history themselves.

```text
path: ABSOLUTE_PATH | type: file | size: N bytes | mtime: UTC_TIMESTAMP
path: ABSOLUTE_PATH | type: directory
pid: PID | command: COMMAND | state: STATE
Removed file: ABSOLUTE_PATH
Sent SIGTERM to process PID.
Directory is empty: ABSOLUTE_PATH
```

Apply safe display escaping to each raw path, link target, and raw process
command field. `UTC_TIMESTAMP` is UTC ISO 8601 to whole seconds with a trailing
`Z`.

For any symbolic link, insert this field immediately after the type field:

```text
 | symlink -> LINK_TARGET
```

The target is the raw spelling supplied by `readlink`, safely escaped; it is
not canonicalized. A live symlink to a file still says `type: file` and uses
followed-stat size and mtime. A live symlink to a directory says
`type: directory` and adds no size or mtime. A broken link says
`type: file (broken symlink)`, includes the link field, and uses lstat size and
mtime.

The process formatter receives a canonical pid, already-mapped readable state
word, and raw command text. State-code reading and mapping belong to listener
002. The removal, signal, and empty-directory helpers use the exact punctuation
shown. Do not use `repr` of a reference or other Python object.

Also provide a small failure-message composer or equivalent convention so
listener 002 can combine a stable literal action phrase with safely escaped
raw path/pid/command text and safely escaped OS error text exactly once before
presenting it as `Error`. This layer does not decide command-specific action
phrases and does not catch command effects.

## Focused tests

Add `tests/test_domain.py`. Use `tmp_path` and read-only host inspection only;
the suite must not unlink anything or signal a process. At minimum prove all of
the following:

1. Exactly `File`, `Directory`, `Process`, `Text`, and `Error` register in
   order into a supplied registry, and their identities—not value classes—are
   distinct.
2. References are immutable; path references reject relative paths; process
   references reject `bool`, floats, and text but retain signed integer values.
3. Relative inputs normalize against the supplied cwd, apply `.`/`..`, become
   absolute immediately, and remain unchanged when a different cwd is later
   used.
4. An ordinary file and directory classify correctly, as do a symlink to each;
   a broken symlink is `File`, an absent path can become `File`, and every
   stored symlink spelling remains the link path rather than its real target.
5. The Directory parser accepts only a current followed directory. The File
   parser refuses a current followed directory and accepts an ordinary file,
   broken link, and missing path.
6. The Process parser accepts canonical, plus-signed, zero, and negative
   decimal forms and rejects empty, whitespace-padded, junk, floating-point,
   and non-ASCII-digit forms.
7. The show-union parser gives an existing numeric filename precedence over
   process syntax, classifies an existing directory, treats a nonexistent
   signed decimal as `Process`, and treats other nonexistent text as `File`.
8. Display escaping covers backslash, LF, CR, tab, another C0/C1 control, an
   unpaired surrogate, a non-BMP non-printable code point if available, spaces,
   ordinary Unicode, and literal bracket/markup-looking text. Stored source
   values remain unchanged.
9. Listing labels use escaped basenames; standalone labels use escaped absolute
   paths; a name containing spaces is one presented span.
10. Path sorting is by escaped displayed basename, case-sensitive Unicode
    code-point order, including a dotfile and names whose raw/display order is
    affected by escaping.
11. Path rows have the exact literal prefixes and only the name hit-tests to
    the original `FileRef` or `DirectoryRef`. Process rows present only the pid;
    state and safely escaped command text are literal and inert.
12. `Text` and `Error` drawers produce exact one-row text, with `Error: ` added
    once, and neither type is compatible with a path or process type.
13. Every path, process, success, empty-directory, symlink, broken-symlink, and
    UTC timestamp formatting form above has exact expected text and no `repr`
    leakage.
14. Existing `tests/test_substrate.py` remains unchanged and green.

Tests may add smaller boundary cases, but must not create a command controller,
fake process table, production signal, filesystem mutation service, terminal
widget, or UI dependency.

## Verification and completion

Run the complete test suite through uv:

```console
uv run pytest
```

The checkpoint is complete when the substrate and domain tests pass; no
dependency or entry-point metadata changed; only the allowed files changed;
`pbui.domain` has no Textual or Rich import; and all filesystem access in the
new suite is read-only and confined to pytest's temporary directory.

Stop after reporting the passing command and changed files. Do not start
listener 002.
