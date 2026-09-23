# listings 005 — Terminal listing affordances

**Status.** Ready to implement.

## Goal

Make the completed tables legible and discoverable in the terminal. Add the
specified semantic row colors, bold headers, listing-header and truncated
process-command documentation, and the visible modal substring editor. Keep
all existing mouse and command behavior. This is an intermediate part of the
screen-and-menu layer in specification section 7.3: viewport anchoring and the
action menu remain later checkpoints.

## Identity, authority, and predecessors

- Identity is `(listings, 005)`, spoken **listings 005**.
- [`../spec.md`](../spec.md), especially sections 4.3, 6.1–6.4, 7.3, and 8,
  is the design authority. Preserve the rest of that specification when this
  checkpoint is silent.
- Listings 000–004 are implemented and reviewed. They supply owned history,
  captured listing values, stable whole-row presentations, cached view
  operations, headless substring state, and exact table text.
- The baseline suite has **171 passing tests**.
- The project root is
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application
  code and tests remain there, never under `docs/`.

## Exact file scope

### May edit

- `src/pbui/terminal.py`
- `tests/test_terminal.py`

### Must not edit or create

- `.python-version`, `pyproject.toml`, `uv.lock`, `README.md`, or `AGENTS.md`
- `src/pbui/__init__.py` or `src/pbui/__main__.py`
- `src/pbui/commands.py`, `src/pbui/domain.py`, `src/pbui/substrate.py`, or
  `src/pbui/text.py`
- another production module or test module
- anything under `docs/`, including this checkpoint, the specification, and
  earlier checkpoints
- any file outside the project root

Do not broaden this slice if styling or documentation seems to need another
host read, model mutation, dependency, action menu, or history change. Return
the checkpoint for correction instead.

## Preserved behavior

Preserve all reviewed capture, view, replacement, table, accept, chip,
translator, and lifecycle behavior. In particular:

- Every table member and header remains one whole-row presentation; literal
  explanatory rows remain non-presented and inert.
- Member click and accept still use the original stored object, even from a
  separator, padding cell, or truncated cell. Header left-click still has no
  default action.
- Hover restyles only the physical rows occupied by the presentation being
  left and entered. Do not construct or slice an accumulated history-wide Rich
  `Text`, create a widget per row, or add a host lookup to hover or drawing.
- The existing documentation sentences for `File`, `Directory`, `Process`,
  `Text`, and `Error`, including accept-mode wording, remain exact except for
  the specified pointer-in-truncated-command override.
- The original input editor, presentation accept, `Ctrl-C`, `Ctrl-D`, scroll,
  resize, and terminal cleanup retain their behavior except where the modal
  substring rules below explicitly change it.

The header documentation may advertise `Ctrl-O` and right-click before those
gestures are implemented. Do **not** add either gesture or a menu here.

## Semantic whole-row styles

Extend the terminal's presentation-kind recognition to exact
`DirectoryListing` and `ProcessListing` values and their registered types.
Other presentation types remain inert. Style every displayed cell of a
presentation identically, including header/member separators and padding.

Outside accept, use these exact foregrounds:

| Presentation | Foreground |
|---|---|
| `File` member | theme foreground |
| `Directory` member | `#00afff` |
| `Process` with cached `running` state | `#00d787` |
| `Process` with cached `sleeping` or `idle` state | `#5f87d7` |
| `Process` with cached `disk-sleep` state | `#d7af00` |
| `Process` with cached `stopped` or `tracing` state | `#d787ff` |
| `Process` with cached `zombie` or `dead` state | `#ff5f5f` |
| `Process` with cached `unknown` state | `#a8a8a8` |
| either listing header | theme foreground, bold |
| `Error` | existing red |
| `Text` | theme foreground |

The state color must come from the containing listing's captured member
record aligned by presentation identity, not `/proc`, a fresh inspect, the
visible state cell, a pid search, or the current filter text. A synthetic
process presentation without a captured listing record retains the existing
default foreground. A process shown after sort/filter/widen keeps its captured
state accent.

Interaction style wins over base accents across the whole presentation:

- Ordinary hover adds reverse video but keeps its base foreground and header
  boldness.
- When a presentation accept is pending, an acceptable member row keeps the
  existing bold bright green `#00d787` and underline, adding reverse only
  while hovered.
- An inert row, including either listing header, keeps the existing neutral
  `#808080`, dim, non-underlined, non-reversed accept style even when hovered.

Keep base-style resolution pure with respect to host state and do not rebuild
all history rows for a hover change.

## Documentation line

Add these exact ordinary header-hover sentences:

```text
Directory listing: Ctrl-O or right-click to open its view menu.
Process listing: Ctrl-O or right-click to open its view menu.
```

Under a pending presentation accept, headers remain inert. Use exactly:

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

Outside accept, retain the ordinary process sentence unless the pointer is
specifically within the 48-display-cell command field of a `Process` table
member whose **full cached escaped command** is wider than 48 display cells.
In that field, use exactly:

```text
Command is truncated; click to show the full command for process PID.
```

Substitute that member's decimal pid for `PID`. The command field begins
after the fixed 10/10/16 cells and three two-space separators, at logical
display column 42, and spans columns 42–89 inclusive. Resolve pointer
coordinates through the current physical-row layout; a wrapped row must
still identify its logical command-field columns correctly. Moving within
the **same** presentation from another cell into or out of this field must
refresh the documentation without rebuilding or restyling the row. A full
command of width exactly 48 is not truncated. A user cell ending in an
ellipsis does not trigger this sentence.

The one mounted documentation row still ellipsis-truncates rather than
wrapping. Preserve its ordinary no-presentation and accept-mode precedence.
While substring accept is active, it overrides all hover sentences with the
modal sentence below. Mouse movement, scroll, relayout, and history
replacement must not leave a stale truncated-command sentence.

## Visible substring accept

The headless listener already owns the exact pending listing target and the
editable substring buffer. Adapt the terminal editor to that state without
adding a second target or buffer. When `pending_substring_listing` is not
`None`, render:

```text
pbui:/absolute/current/directory> narrow SUBSTRING
```

The normal prompt still reflects the listener's current directory. The
literal `narrow ` prefix is non-editable and appears even before typing any
substring; the empty editor ends immediately after that space. Put the
cursor at the start/end of the actual substring buffer, after the prefix.
Left/right, Home/End, Backspace/Delete, insertion, and paste operate only on
that buffer. Backspace at buffer position zero cannot delete the prefix.
No presentation chip is made in this state.

While waiting, the documentation sentence is exactly:

```text
Type a substring and press Enter to narrow this listing; Ctrl-G or Esc cancels.
```

Enter with an empty buffer leaves the same target pending and changes no
listing/history. Enter with a nonempty buffer delegates once to the existing
headless `submit` operation, then returns to ordinary prompt/documentation;
it must not append a confirmation or recapture host data. `Ctrl-G` or Escape
uses existing listener cancellation to clear both target and buffer, changes
no listing or history, and restores ordinary input. A click on history while
waiting remains inert as in the headless listener. `Ctrl-D` with an empty
substring must **not** exit while the modal target is pending; `Ctrl-C` keeps
its existing unconditional exit behavior.

This checkpoint does not redesign the terminal's scroll-to-newest behavior
after an in-place view operation. The specified viewport-anchor policy is a
separate later checkpoint, and its implementation will distinguish replacement
from appended output.

## Automated tests

Extend `tests/test_terminal.py` without deleting or weakening predecessor
tests. Use injected services, temporary filesystem roots, constructed cached
listings, and `PbuiApp.run_test()` where appropriate; do not read live
`/proc` or signal an arbitrary process.

Prove at least:

- every semantic foreground, bold header, and the full accept/hover/inert
  precedence, with colors sourced from cached process states;
- whole-row styles and hits across padding, separators, and truncated cells;
- exact header documentation and all eight header accept refusals;
- ordinary member documentation remains exact, including when a command is
  not truncated or the pointer is over another field;
- the truncated-command sentence appears only within the actual command
  field, survives wrapping, and changes on pointer movement within one
  presentation without full-row restyling;
- modal prefix, cursor placement, editor boundary, paste, empty Enter,
  nonempty Enter, cancellation, inert history click, and `Ctrl-D` guard;
- documentation refresh after hover/scroll/resize/replacement, and one-row
  ellipsis truncation; and
- the listener 005 regression with hundreds of injected long process rows:
  hover changes rebuild only entered/exited physical rows, with no elapsed
  time assertion.

Keep all 171 predecessor tests green. Do not weaken headless modal and
capture-failure assertions to fit terminal behavior.

## uv workflow and verification

Add no dependency. Use only the existing uv-managed project:

```console
uv sync
uv run pytest
```

All predecessor tests plus new listings 005 tests must pass. Do not use
`pip`, `python -m pip`, `uv pip install`, Poetry, Pipenv, Conda, Hatch, a
hand-made virtual environment, or a globally installed Python. If `uv` is
unavailable, stop and tell the human.

No physical-terminal hand check, live `/proc` exercise, action-menu test, or
new dependency is required for this intermediate screen checkpoint.

## Completion boundary

Listings 005 is complete when table headers and members have the specified
base and interaction styles; the documentation line gives exact header,
accept, modal, and pointer-specific truncated-command sentences; the modal
substring prefix and editor are correct; exit/cancellation rules hold; and the
full suite passes with local hover rendering intact.

Stop there. Do not implement viewport anchoring, right-click, `Ctrl-O`, an
action menu, menu actions or documentation, menu layout, or the live hand
check.
