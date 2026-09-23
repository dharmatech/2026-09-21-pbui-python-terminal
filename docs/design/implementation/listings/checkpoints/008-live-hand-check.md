# listings 008 — Disposable-directory live hand check

**Status.** Ready to verify.

## Goal

Complete the accepted listings specification with one real interactive
terminal hand check of the finished listener. Exercise the table, menu,
redisplay, anchoring, cancellation, safe file removal, and terminal
restoration behaviors in a fresh disposable directory. Record observable
results and any environment limitation honestly; an automated `run_test()`
session alone is not this checkpoint.

## Identity, authority, and predecessors

- Identity is `(listings, 008)`, spoken **listings 008**.
- [`../spec.md`](../spec.md), especially sections 7.4 and 8, is the design
  authority. Preserve all other accepted behavior.
- Listings 000–007 are implemented and reviewed. The full automated suite
  has **193 passing tests**.
- This is the final verification checkpoint. It does not authorize a new
  feature, bug fix, dependency, or documentation rewrite.
- The project root is
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`.

## Exact scope and safety boundary

### May do

- Create **one fresh, uniquely named disposable fixture directory** beneath
  the project root. Record its absolute path before launching the program.
- In that directory only, create a subdirectory, several ordinary files of
  different sizes and mtimes, a filename containing a space, a designated
  disposable file for `rm`, and enough entries to exercise scrolling.
- Run `uv sync`, `uv run pytest -q`, and `uv run pbui` through the project's
  uv-managed environment. Launch `pbui` with the disposable directory as the
  current directory.
- Remove **only** the designated disposable file via the listener's `rm`
  action after checking the prompt against the recorded fixture path.
- Leave the remaining fixture directory intact for inspection and report its
  path and final state. Do not perform broad cleanup in this checkpoint.

### Must not do

- Do not edit production code, tests, dependency metadata, lockfiles,
  `AGENTS.md`, `README.md`, the listings specification, or any checkpoint.
- Do not unlink outside the recorded disposable directory, recursively
  delete the fixture, or use a broad pathname, glob, or unresolved variable
  as a destructive target.
- Do not send a signal to any live process. In particular, **do not run
  `kill`** during the hand check.
- Do not use live `/proc` process records as targets for a destructive
  action. `ps` and `show` are read-only in this check.
- Do not substitute a mock, screenshot alone, automated `run_test()` test,
  or unobserved background launch for the interactive terminal session.

If a discrepancy appears, record the exact command/gesture, visible result,
and expected result; stop this checkpoint and return it to the checkpoint
manager. Do not silently expand its scope into an implementation repair.

## Prepare and gate

Use only uv for Python and the application. Confirm `uv` is available; if it
is not, stop and report that blocker rather than using another Python tool.
Run:

```console
uv sync
uv run pytest -q
```

Require the 193 predecessor tests to pass before the live session. The
Python uv workflow governs these commands; add no dependency. Use a real
interactive terminal that can display the alternate screen, colors, cursor,
and keyboard input. Button 3 is optional if the terminal does not report it;
`Ctrl-O` is mandatory. If no usable interactive terminal is available, report
the limitation and leave this checkpoint unverified.

Create the fresh fixture directory beneath the project root using a unique
name, not an existing user directory. Record its absolute path in the final
report. Confirm each fixture file is inside it, note which file is designated
for `rm`, and verify sizes and mtimes differ before launching. No fixture
preparation may change project source or other user data.

Start `uv run pbui` from that exact directory. Before any destructive step,
verify that the prompt is `pbui:ABSOLUTE_FIXTURE_PATH> ` and that it remains
the expected path after subsequent read-only actions. Do not proceed with
`rm` if the displayed path differs.

## Interactive checklist

Observe and record each of the following in the terminal, not only in a
test assertion:

1. Run `ls`. Check the header and complete table alignment; blank size for
   the subdirectory; distinct file sizes and UTC mtimes; cyan directory
   color; and whole-row hover/click, including padding, separator, size, and
   modified cells. Check the filename with a space and scroll through enough
   entries to confirm the fixed documentation and prompt rows do not move.
2. Type `sort size` and verify the existing `ls` listing changes in place.
   Append a harmless detail/output row, then use the older listing header's
   `Ctrl-O` menu to apply `sort mtime`. Verify that exact older listing changes
   in place and the intervening row is neither replaced nor duplicated.
3. Type `narrow` and enter a substring. Combine it with `only files`, then
   use a no-match substring and verify the exact no-match sentence. `widen`
   should restore the captured members without another listing appended or
   a visible rescan. Check the modal `narrow ` prefix and its documentation.
4. Open member menus with `Ctrl-O`. Use `show` on a file or directory and
   verify a fresh detail row. Use `ls` on the fixture's subdirectory row and
   verify a **new** listing of that directory is appended, while the original
   listing remains. Exercise button 3 only if this terminal reports it.
5. Run `ps`. Check the pid/state/user/command columns and state colors. If a
   long command is visibly truncated, hover its command field and verify the
   truncation documentation, then use `show` to display its full current
   command. If none is available, record that this conditional observation
   could not be made; do not signal or manipulate a process to manufacture
   one.
6. Scroll back to an older listing, position a wrapped row in view, resize
   the terminal, and sort that older listing from its header menu. Verify the
   anchor stays connected to the same retained header/member where possible,
   and hover still describes the object under the current pointer.
7. Recheck the prompt against the **recorded absolute fixture path**. Use
   `show` on the designated disposable file to verify its absolute path is
   inside the fixture. Then open `rm` on that same file row only and remove
   it. Verify that file is gone and unrelated fixture files remain. Do not
   run `kill`.
8. Start ordinary presentation accepts and a modal substring wait in safe
   contexts; verify both `Ctrl-G` and Escape cancel them without an action.
   Also close a menu with those keys and verify it runs no item.
9. Exit one session with `Ctrl-D` from empty ordinary input. Launch again
   from the same recorded directory and exit with `Ctrl-C`. After each exit,
   confirm the shell prompt, visible cursor, normal typing/input mode, and
   mouse/alternate-screen restoration; no traceback or stray escape
   sequence should remain.

The live observations supplement, rather than replace, the full automated
gate. Do not claim a full-command or button-3 observation if that terminal
did not make it possible.

## Report and completion boundary

Report the absolute fixture path, the designated file removed, the automated
test count, the terminal used, each checklist result, conditional skips, and
any mismatch or restoration problem. State whether the fixture was left in
place. A concise table of the nine checks is acceptable; do not put a
success claim in place of observations.

Listings 008 is complete only when the full suite is green, all mandatory
interactive checks pass in the recorded disposable directory, the safe `rm`
scope is verified, no live process is signaled, and both exit paths restore
the terminal. If a mandatory check cannot be performed, report this
checkpoint as unverified and request the missing terminal access or a
correction checkpoint. Stop after reporting; do not start another feature.
