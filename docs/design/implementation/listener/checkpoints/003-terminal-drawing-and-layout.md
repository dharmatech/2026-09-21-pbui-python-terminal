# listener 003 — Terminal drawing and layout

**Status.** Ready to implement.

## Goal

Add the passive Textual terminal surface over the reviewed headless listener:
the three fixed screen regions, one scrollable history widget, Rich styling
derived from retained presentations, exact documentation text, prompt and chip
drawing, display-column-safe span translation, and resize relayout with a
logical-row scroll anchor.

Stop when drawing and layout are green. Do not add keyboard editing, paste,
submission, mouse hover/click/leave handlers, wheel-step behavior, cancellation
bindings, exit bindings, `main()`, a console script, `pbui.__main__`, or the live
terminal hand check. Those belong to listener 004.

The implementer receives this checkpoint and the accepted listener
specification. This checkpoint is the first half of the terminal layer; it does
not revise the specification.

## Identity, authority, and predecessors

- Identity is `(listener, 003)`, spoken **listener 003**.
- [`../spec.md`](../spec.md), especially sections 1, 2, 6, 6.1–6.3, the resize
  and scrolling invariants in 6.4, and 7.4, is the design authority. Preserve
  it when this checkpoint is silent.
- [listener 000](000-presentation-substrate.md),
  [listener 001](001-domain-objects-and-printers.md), and
  [listener 002](002-headless-listener-and-commands.md) are implemented and
  reviewed. All 79 current tests pass.
- The existing `HeadlessListener` exposes cwd, history, presentation types,
  `SubstrateState`, drawing contexts, accept state, chip state, and command
  operations. The existing pure `layout()` returns physical rows and updates
  retained presentations with display-cell intervals. Use those APIs directly.
- The project root is
  `/home/dharmatech/journal/2026-09-21-pbui-python-terminal/`. Application code
  and tests remain there, never under `docs/`.

Only `pbui.terminal` may import Textual. Presentations remain plain model
objects, never Textual widgets.

## Exact file scope

### May create or edit

- `src/pbui/terminal.py` (new)
- `tests/test_terminal.py` (new)
- `pyproject.toml`, only through the required `uv add` commands and to confirm
  that no script entry was added
- `uv.lock`, only through the required uv dependency resolution

### Must not edit or create

- `.python-version`, `README.md`, `AGENTS.md`, or `src/pbui/__init__.py`
- `src/pbui/substrate.py`, `src/pbui/text.py`, `src/pbui/domain.py`,
  `src/pbui/commands.py`, or any of their existing tests
- `src/pbui/__main__.py`
- `[project.scripts]`, `pbui.terminal:main`, or any runnable application entry
  point
- anything under `docs/`, including earlier checkpoints and the specification
- any file outside the project root

If a predecessor production file appears necessary, stop and return the
checkpoint for correction instead of widening the slice.

## Dependencies and uv workflow

Add the terminal-layer dependencies exactly through uv:

```console
uv add textual rich
uv add --dev pytest-asyncio
uv sync
uv run pytest
```

This checkpoint therefore changes both `pyproject.toml` and `uv.lock`. Keep
`wcwidth` as the existing runtime dependency and pytest as the existing
development dependency. Do not add another package. In particular, do not add
snapshot, image, browser, curses, prompt-toolkit, or terminal-emulator test
dependencies.

Use uv for every Python command. Do not use `pip`, `python -m pip`, `uv pip
install`, Poetry, Pipenv, Conda, Hatch, or globally installed Python packages.
If uv is unavailable, stop and tell the human.

## Terminal module boundary

Create `pbui.terminal` as the only module in the package that imports Textual.
Rich is likewise used only for terminal rendering in this slice. Importing any
of `pbui.substrate`, `pbui.text`, `pbui.domain`, or `pbui.commands` must remain
possible without importing Textual transitively.

Define these five terminal objects:

- `PbuiApp`: the Textual `App` adapting one injected `HeadlessListener`;
- `ListenerScreen`: the sole screen arranging the fixed regions;
- `HistorySurface`: one custom scrollable widget drawing the complete history;
- `DocumentationLine`: one plain-text, one-row widget; and
- `CommandInput`: one custom, one-row widget drawing prompt, command text,
  cursor position, and an optional atomic chip.

This checkpoint constructs `PbuiApp` only with an injected listener. It does
not create production services or expose `main()`. `PbuiApp.run_test()` is the
only required way to run it in this slice.

There is exactly one `HistorySurface`, one `DocumentationLine`, and one
`CommandInput`. Never create a `Button`, `Label`, `Static`, or other widget per
file, directory, process, presentation, logical row, or physical row. Textual
may create its own internal scroll machinery; application object identity must
not live there.

## Three fixed regions

`ListenerScreen` mounts the application widgets in this exact top-to-bottom
order and gives them stable ids:

```text
HistorySurface      #history        flexible remaining height
DocumentationLine   #documentation  exactly one row
CommandInput        #command-input  exactly one row
```

The history is the only scrollable region. Documentation and command input
stay pinned while history content or scroll position changes. The
documentation widget is mounted even when history is empty and no presentation
is under the pointer.

Keep product text on one visual row where required. The documentation line and
command input do not wrap. At narrow widths, documentation truncates with one
ellipsis rather than wrapping into the history or prompt. Provide a small pure
display-column truncation helper so this behavior can be tested without
depending on a terminal screenshot; it must not split a wide character or
separate a combining mark from its base.

## Pure history layout ownership

`HistorySurface` owns the current pure `pbui.text.Layout` for its listener's
retained history. Relayout at the widget's current **content width**, excluding
border, padding, and scrollbar space, and normalize through the predecessor's
width rule. Do not use screen width or Python string length as history width.

The surface exposes a narrow synchronization operation for listener 004 and
tests. It must:

1. detect a history revision or content-width change;
2. call the existing pure `layout(listener.history, content_width)`;
3. use the returned physical rows as its complete scrollable content;
4. update virtual height and clamp vertical scrolling; and
5. refresh the renderable, presentation styles, and documentation state.

The history surface does not duplicate wrapping, retention, presentation
ownership, or hit testing. Its current `Layout.hit_test(x, y)` remains the sole
authority for object hits after listener 004 translates viewport coordinates.
Rich character spans are drawing metadata only.

When the retained history is empty, the scrollable content still renders
cleanly with height zero or one as required by Textual, while pure hit testing
returns no presentation. The prompt and documentation remain mounted.

## One Rich renderable and character-span translation

Build one Rich `Text` renderable for the whole current history, joining physical
rows with literal newline separators. Construct product strings as literal
text; never enable Rich markup parsing. Literal brackets and markup-like
filenames remain visible characters.

The pure model's `DisplayInterval` uses physical-row/display-column
coordinates. Rich styling uses code-point offsets. Translate explicitly; never
pass a display column to a Rich character-span API. The translation must handle:

- narrow characters;
- wide characters occupying two cells;
- zero-width combining characters, which stay styled with their owning base
  presentation;
- physical-row newline separators in the combined Rich text;
- wrapped presentations with a separate interval on each physical row; and
- nested presentations, where deeper spans are applied after outer spans.

An interval may style only code points whose drawn cells belong to that exact
row interval, plus attached zero-width combining code points. It must not style
literal padding, a neighboring field, a newline separator, or empty cells in a
multi-row bounding rectangle. If an oversized wide character occupies the
predecessor's intentional interval beyond a one-cell width, style the character
once without indexing outside its string.

Keep presentation ids available while constructing the Rich spans, but retain
the original `Presentation` values in history. Do not parse the combined text
or a Rich span to reconstruct an object.

## Presentation visual states

Render styles from the listener's current pending accept and an explicitly set
`hovered_presentation`. This checkpoint exposes a setter or equivalent model
operation so tests and listener 004 can change hover and redraw; it does not
install mouse event handlers yet.

Apply these exact states:

- **no accept, normal File/Directory/Process/Text:** theme foreground with no
  forced bold, underline, dim, or reverse;
- **no accept, Error:** red text;
- **no accept, hovered innermost presentation:** add reverse video to that
  presentation only;
- **accept pending, acceptable exact type:** foreground `#00d787`, bold, and
  underline;
- **accept pending, hovered acceptable target:** the acceptable style plus
  reverse video; and
- **accept pending, every non-acceptable presentation:** foreground `#808080`,
  dim, and no underline or reverse, even when designated as hovered.

Acceptability uses exact `PresentationType` identity from the request. It is
not based on Python value class or type name. During accept, the inert style
also applies to `Text` and `Error`; the outside-accept red Error style does not
override inertness.

For nested or malformed overlapping spans, apply shallower/earlier styles
first and deeper/later styles last, consistent with pure hit-test precedence.
Color is reinforcement; bold/underline/dim/reverse must carry the same state
distinctions without hue.

## Documentation wording model

Implement one pure formatter from `(listener, presentation-or-None)` to the
documentation sentence. `DocumentationLine` displays that formatter's current
result as literal text. Listener 004 will call it after hover, accept,
execution, scrolling, and resize.

With no accept pending, return exactly:

| Pointer | Sentence |
|---|---|
| none/literal | `No presentation under pointer.` |
| `File` | `Click to show file “NAME”.` |
| `Directory` | `Click to show directory “NAME”.` |
| `Process` | `Click to show process PID.` |
| `Text` | `Text has no default click action.` |
| `Error` | `Error has no default click action.` |

`NAME` is the safely escaped basename of the stored absolute path and `PID` is
the canonical decimal pid. Use curly quotation marks exactly as shown.

While accept is pending, reproduce every sentence in the normative table in
specification section 6.2 exactly. This includes the no-pointer, matching, and
all four/five nonmatching cases for `rm`, `cd`, `kill`, and `show`; the exact
type-list spelling `File, Directory, or Process`; exact capitalization; and the
suffix `Ctrl-G or Esc cancels.` where shown. Do not generate an alternative
grammar or mention accept types in the prompt. `ls` never creates an accept
request.

The formatter reads exact registry identity. A value with a misleading Python
class or equal-looking type token does not acquire a domain sentence.

## Prompt and passive command-line drawing

`CommandInput` renders this literal prompt prefix using safe path display:

```text
pbui:/absolute/current/directory> 
```

Append the listener's current input text exactly as editor text. The cwd comes
from `HeadlessListener.cwd`, not `os.getcwd()`. A later `cd` changes the prompt
without changing process-global cwd.

If a chip is present, render one ASCII space after the command name followed by
the chip as:

```text
⟨Type: LABEL⟩
```

`Type` is the chip's exact presentation-type name. `LABEL` is the chip's stored
display label. Do not parse the label, append it to listener input text, or
duplicate the acceptable type in the prompt. The chip is one visual/editor
unit even though it occupies multiple cells.

Maintain an integer cursor position in the editable text, clamped to Python
code-point boundaries from zero through `len(input_text)`. Draw a visible
cursor at that position when focused, without mutating the listener model. This
checkpoint tests drawing and external cursor placement only; key-driven cursor
movement and editing belong to listener 004.

Product prompt, editor, and chip text are literal, not Rich markup. Keep the
input widget one visual row and clip or horizontally reveal the cursor as
needed; never wrap it into a fourth screen region.

## Resize and scroll-anchor preservation

The history's vertical unit is a physical row. Expose programmatic vertical
scrolling and clamp it to current content; listener 004 will map wheel events to
three-row steps.

On a content-width change, preserve the **oldest visible logical row** where
possible:

1. before relayout, identify the retained `HistoryRow` object corresponding to
   the top visible physical row;
2. relayout all current retained logical rows at the new content width;
3. find the first new physical row for that same logical-row object and make it
   the new top visible row; and
4. clamp to the new scroll range.

Do not preserve a stale physical coordinate. If the old anchor row was dropped
by 500-row retention, use the nearest valid/clamped scroll position. Resize
keeps every retained `Presentation` and stored value identical while replacing
its derived intervals through the pure layout call.

A Textual resize message may trigger this synchronization because it is needed
for drawing. Do not add mouse move, leave, click, mouse-wheel, key, paste,
submit, cancel, or exit handling in this checkpoint.

## Passive Textual tests

Add `tests/test_terminal.py`; it is the only test module allowed to import
Textual. Use pytest-asyncio and `PbuiApp.run_test()` with a `HeadlessListener`
backed by `RootedFilesystem(tmp_path)` and a fixed process service. Do not start
a physical terminal, use the production process table, synthesize a mouse
click, or perform the listener 004 live hand check.

At minimum prove all of the following:

1. Dependency metadata contains Textual and Rich at runtime and pytest-asyncio
   for development, with no console script or `pbui.__main__`.
2. Only `pbui.terminal` imports Textual; predecessor modules and tests remain
   unchanged and green.
3. `PbuiApp.run_test()` mounts exactly one application history surface,
   documentation line, and command input in the required order and fixed/flex
   heights, including with empty history.
4. Several pre-populated `ls`, `ps`, Text, and Error rows render as one literal
   Rich history text with no widget per presentation and with brackets shown
   literally.
5. The pure layout width equals the history content width rather than screen
   width, and wrapped physical rows determine virtual height.
6. Display-column intervals translate to correct Rich character spans for a
   narrow character, wide character, combining sequence, wrapped
   presentation, literal neighbor, and nested outer/inner presentation.
7. Pure `Layout.hit_test` remains the authority and returns the original stored
   object independently of Rich styles.
8. Outside accept, only Error is red and only the explicitly hovered
   presentation is reversed. During each accept set, all and only exact targets
   are green/bold/underlined, the hovered target adds reverse, and every inert
   presentation is gray/dim/non-underlined/non-reversed.
9. The documentation formatter covers every exact sentence in specification
   section 6.2, including all no-pointer, matching, and nonmatching cases for
   `rm`, `cd`, `kill`, and `show`.
10. The documentation widget is always mounted, stays one row, and its pure
    truncation uses an ellipsis at narrow display widths without splitting a
    wide/combining sequence.
11. The prompt uses the listener's safely displayed absolute cwd, not process
    cwd, and updates after a headless `cd`; accept type text is absent from the
    prompt.
12. Passive command drawing covers ordinary input, external cursor positions,
    and exact `⟨Type: LABEL⟩` chip rendering while proving the chip's original
    value and atomic listener model are unchanged.
13. Programmatic scrolling moves only history. A width change rewraps, preserves
    the oldest visible logical-row object when retained, replaces display
    intervals, and clamps safely when the anchor was dropped.
14. No custom mouse, wheel, keyboard, paste, submission, cancellation, exit, or
    production lifecycle path is required or tested in this slice.
15. All 79 predecessor tests remain unchanged and green.

The final specification's pilot-driven `l`, `s`, `enter` test is intentionally
deferred to listener 004 because this checkpoint has no key dispatch.

## Verification and completion

Run the complete test suite through uv:

```console
uv run pytest
```

The checkpoint is complete when substrate, domain, command, and passive
terminal tests pass; only the allowed files changed; dependencies were added
only through uv; no entry point exists; only `pbui.terminal` imports Textual;
and no physical terminal or live host effect was used beyond listener 002's
already-reviewed isolated child-SIGTERM test.

Stop after reporting the passing command and changed files. Do not start
listener 004.
