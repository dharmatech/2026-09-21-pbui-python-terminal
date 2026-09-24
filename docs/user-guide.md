# pbui user guide

`pbui` is a full-screen terminal listener for files, directories, and Linux
processes. Its history retains the objects represented by each row. You can
type a command, click an object to supply it to a waiting command, or open an
action menu for the object under the pointer.

## Start pbui

Start pbui in the directory you want to explore:

```console
cd /path/to/a/directory
uv run --project /path/to/pbui pbui
```

When starting it from the project root itself, this shorter command is enough:

```console
uv run pbui
```

The prompt shows pbui's current directory:

```text
pbui:/absolute/current/directory>
```

The screen has three parts: scrollable history, a documentation line, and the
prompt. The documentation line changes as the pointer moves and usually tells
you what clicking will do.

## Commands

| Command | What it does |
|---|---|
| `ls` | Append a captured table of the current directory. |
| `ls DIRECTORY` | Append a captured table of another directory. |
| `ps` | Append a captured table of your Linux processes. |
| `show OBJECT` | Inspect a file, directory, or process and append fresh details. |
| `cd DIRECTORY` | Change pbui's current directory without clearing history. |
| `rm FILE` | Unlink exactly one file. Directories are refused. |
| `kill PID` | Send `SIGTERM` to one process. PID 1 and pbui itself are refused. |
| `sort KEY` | Change the order of the newest retained listing. |
| `narrow TEXT` | Keep rows whose name or command contains the case-sensitive text. |
| `only KIND` | Keep rows of one file kind or process state. |
| `widen` | Clear both filters while keeping the current sort order. |

Commands are intentionally simpler than shell commands. There are no pipes,
redirects, or globs. Quotes have no special meaning. Tab completes a name
in the input row, and Up and Down recall earlier submissions. The rest of
a path command is its argument, so a path containing spaces can be entered
directly:

```text
show a file with spaces.txt
```

`show`, `cd`, `rm`, and `kill` may also be entered without an argument. pbui
then waits for you to click a compatible object in retained history. Valid
targets become bold, green, and underlined; other presentations become dim.
The documentation line describes the expected target.

### Directory-listing views

```text
sort name
sort size
sort mtime
only files
only directories
narrow report
widen
```

### Process-listing views

```text
sort pid
sort state
sort command
only running
only sleeping
only disk-sleep
only stopped
only tracing
only zombie
only dead
only idle
only unknown
narrow python
widen
```

Typed view commands act on the newest retained listing. A menu opened from an
older listing header acts on that exact older listing. Sorting and filtering
redisplay the captured listing in place; they do not reread the filesystem or
`/proc`. Run `ls` or `ps` again to capture current host state. `show` always
performs a fresh inspection.

Entering `narrow` without text starts a small modal prompt. Type the substring
and press Enter, or cancel it with `Ctrl-G` or Escape.

## Mouse and action menus

- Hover over a presented row to highlight it and update the documentation
  line.
- With no command waiting, left-click a file, directory, or process to run
  `show` on it.
- A complete table row is one object. Its padding, size, timestamp, pid,
  state, user, and command cells all refer to the same object.
- Hover over an object or listing header and press `Ctrl-O` to open its action
  menu. Right-click does the same thing in terminals that report button 3.
- Left-click a menu item to run it. `Ctrl-G` or Escape closes the menu without
  running anything.
- Mouse-wheel scrolling moves history while the documentation line and prompt
  remain fixed.

Menus contain these actions:

| Target | Menu actions |
|---|---|
| File row | `show`, `rm` |
| Directory row | `show`, `cd`, `ls` |
| Process row | `show`, `kill` |
| Directory header | Directory sort and filter actions, `narrow`, `widen` |
| Process header | Process sort and filter actions, `narrow`, `widen` |

A process command cell may end with `…`. Hover over that cell for an
explanation, then click the row or use `Ctrl-O` → `show` to see the full current
command.

## Keyboard reference

| Key | Action |
|---|---|
| Enter | Submit the current input. |
| Tab | Complete a name at the caret; when a completion list is open, move to the next candidate. |
| Up | Recall the next older submission from this session. |
| Down | Move toward newer submissions, then restore unsent input. |
| `Ctrl-O` | Open the action menu for the presentation under the pointer. |
| `Ctrl-G` | Clear input and cancel a pending selection, substring prompt, or menu. |
| Escape | Close a completion list first; otherwise cancel like Ctrl-G, closing an open action menu first. |
| `Ctrl-D` | Exit when ordinary input is empty and nothing is waiting. |
| `Ctrl-C` | Exit from any state. |
| Left, Right, Home, End | Move within the input line. |
| Backspace, Delete | Edit the input line. |

Both exit keys restore the terminal's normal screen, cursor, mouse reporting,
and input mode.

## Five-minute smoke test

Use a directory containing a subdirectory, a filename with spaces, and several
files with different sizes. Avoid valuable files and processes while testing.

1. Run `ls`. Check the `name`, `size`, and `modified` columns. A directory has
   a blank size cell.
2. Hover across a file's name, padding, size, and modified time. The whole row
   should highlight and the documentation line should keep naming that file.
3. Left-click the file. A fresh detail row should appear below the listing.
4. Type `sort size`. The existing listing should reorder in place.
5. Hover over that listing's header, press `Ctrl-O`, and choose `sort mtime`.
6. Type `narrow`, enter part of a filename, then try `only files`. Type
   `widen` to restore all captured members.
7. Open a directory row's menu and choose `ls`. A new listing for that
   directory should be appended while the original remains.
8. Run `ps`. Check the `pid`, `state`, `user`, and `command` columns. Use
   `show` on a truncated command if one is available. Do not choose `kill`.
9. Start `show` with no argument and cancel it with `Ctrl-G`. Start `narrow`
   with no substring and cancel it with Escape. Open a menu and cancel it too.
10. Scroll and resize the terminal. Rows may wrap, but the prompt and
    documentation line should stay fixed and clicks should still describe the
    objects now under the pointer.
11. Exit once with `Ctrl-D`. On another run, exit with `Ctrl-C`. The normal
    shell prompt and visible cursor should return without a traceback.

### Optional destructive check

Only perform this in a disposable directory. `rm` runs as soon as it receives
a file; there is no extra confirmation dialog.

1. Create one clearly designated disposable file before starting pbui.
2. Run `ls`, use `show` on that file, and verify its absolute path.
3. Recheck the absolute directory in the prompt.
4. Open the file's menu and choose `rm`.
5. Run `ls` again to capture fresh state and confirm only that file is gone.

Skip `kill` during an ordinary smoke test. It sends `SIGTERM` as soon as it
receives an eligible process.
