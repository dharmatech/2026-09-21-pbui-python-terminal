"""Pure wording and display fitting for the listener's bottom rows."""

from __future__ import annotations

import os
import re

import sympy
import pandas as pd
import yfinance as yf

from pbui.commands import HeadlessListener
from pbui.chart import Candle, Chart
from pbui.domain import (
    DirectoryListing, DirectoryRef, FileRef, ProcessListing,
    ProcessListingMember, ProcessRef, escape_display,
)
from pbui.http import GetRequest, HttpResponse, JsonArray, JsonObject
from pbui.substrate import Presentation
from pbui.text import display_width, truncate_display
from pbui.transcript import CommandInput, MenuActionInput, PythonInput
from pbui.tutorial import TutorialCard, TutorialExample, TutorialTarget


_PRESENTATION_MODES = {
    "rm": "SELECT FILE FOR rm",
    "cd": "SELECT DIRECTORY FOR cd",
    "kill": "SELECT PROCESS FOR kill",
    "show": "SELECT FILE/DIRECTORY/PROCESS FOR show",
}
_REQUIRED = {
    "rm": "File", "cd": "Directory", "kill": "Process",
    "show": "File, Directory, or Process",
}
_MENU_KINDS = {
    "File", "Directory", "Process", "DirectoryListing", "ProcessListing",
    "PythonInput", "CommandInput", "MenuActionInput",
}
MENU_BORDER_DOCUMENTATION = "NO TARGET • Click an item • Esc: close menu • Ctrl-G: close menu"
_CANCEL = " • Esc: cancel • Ctrl-G: cancel"
_SUBSTRING = "Type substring; Enter: narrow listing"


def format_mode(listener: HeadlessListener) -> str:
    """Name the editor state without consulting its visible widget."""
    request = listener.pending_request
    if request is not None:
        return _PRESENTATION_MODES[request.command_name]
    if listener.pending_substring_listing is not None:
        return "SELECT TEXT FOR narrow"
    if listener.pending_python_pieces:
        return "CONTINUE"
    if listener.input_mode == "command":
        return "COMMAND"
    return "PYTHON"


def _domain_kind(listener: HeadlessListener, presentation: Presentation | None) -> str | None:
    """Identify retained values in this listener's exact presentation registry."""
    if presentation is None:
        return None
    presentation_type = presentation.presentation_type
    value = presentation.value
    types = listener.types
    pairs = (
        (types.file, FileRef, "File"),
        (types.directory, DirectoryRef, "Directory"),
        (types.process, ProcessRef, "Process"),
        (types.directory_listing, DirectoryListing, "DirectoryListing"),
        (types.process_listing, ProcessListing, "ProcessListing"),
        (types.python_input, PythonInput, "PythonInput"),
        (types.command_input, CommandInput, "CommandInput"),
        (types.menu_action_input, MenuActionInput, "MenuActionInput"),
        (types.chart, Chart, "Chart"),
        (types.candle, Candle, "Candle"),
        (types.tutorial_card, TutorialCard, "TutorialCard"),
        (types.tutorial_target, TutorialTarget, "TutorialTarget"),
        (types.tutorial_try, TutorialExample, "TutorialTry"),
    )
    for registered, value_type, kind in pairs:
        if presentation_type is registered and type(value) is value_type:
            return kind
    if presentation_type is types.value:
        return "Value"
    if presentation_type is types.pandas_column and isinstance(value, pd.Series):
        return "PandasColumn"
    if presentation_type is types.pandas_row and isinstance(value, pd.DataFrame):
        return "PandasRow"
    if presentation_type is types.text:
        return "Text"
    if presentation_type is types.error:
        return "Error"
    return None


def _name(presentation: Presentation) -> str:
    value = presentation.value
    if type(value) not in {FileRef, DirectoryRef}:
        raise TypeError("path documentation requires a path presentation")
    return escape_display(os.path.basename(value.path))


def _pid(presentation: Presentation) -> str:
    value = presentation.value
    if type(value) is not ProcessRef:
        raise TypeError("process documentation requires a process presentation")
    return str(value.pid)


def _captured_process_member(
    listener: HeadlessListener, presentation: Presentation
) -> ProcessListingMember | None:
    """Find a process row's captured record by presentation identity."""
    seen_listings: set[int] = set()
    for row in listener.history.rows:
        listing = row.listing_owner
        if type(listing) is not ProcessListing or id(listing) in seen_listings:
            continue
        seen_listings.add(id(listing))
        for member, member_presentation in zip(
            listing.members, listing.member_presentations, strict=True
        ):
            if member_presentation is presentation:
                return member
    return None


def _target(listener: HeadlessListener, presentation: Presentation | None) -> str:
    kind = _domain_kind(listener, presentation)
    if presentation is None or kind is None:
        return "NO TARGET" if presentation is None else (
            f"OBJECT {escape_display(presentation.presentation_type.name)}"
        )
    if kind in {"File", "Directory"}:
        return f"{kind.upper()} “{_name(presentation)}”"
    if kind == "Process":
        return f"PROCESS {_pid(presentation)}"
    if kind == "DirectoryListing":
        return "DIRECTORY LISTING"
    if kind == "ProcessListing":
        return "PROCESS LISTING"
    if kind == "PythonInput":
        return "PYTHON INPUT"
    if kind == "CommandInput":
        return "COMMAND INPUT"
    if kind == "MenuActionInput":
        return f"ACTION “{escape_display(presentation.value.label)}”"
    if kind == "Chart":
        return f"CHART {escape_display(str(presentation.value.symbol))}"
    if kind == "Candle":
        candle = presentation.value
        direction = "rose" if candle.close >= candle.open else "fell"
        return f"CANDLE {candle.date} ({direction})"
    if kind == "Value":
        value = presentation.value
        if isinstance(value, yf.Ticker):
            return f"TICKER {escape_display(str(value.ticker))}"
        if isinstance(value, pd.DataFrame):
            return "DATAFRAME"
        if isinstance(value, pd.Series):
            return "SERIES"
        if type(value) is GetRequest:
            return f"GET REQUEST “{escape_display(value.url)}”"
        if type(value) is HttpResponse:
            return f"HTTP RESPONSE {value.status} “{escape_display(value.final_url)}”"
        if type(value) is JsonObject:
            return f"JSON OBJECT ({len(value)} keys)"
        if type(value) is JsonArray:
            return f"JSON ARRAY ({len(value)} elements)"
        if isinstance(value, sympy.Expr):
            return "SYMPY EXPRESSION"
        return "PYTHON VALUE"
    if kind == "TutorialCard":
        return f"TUTORIAL CARD “{escape_display(presentation.value.title)}”"
    if kind == "TutorialTarget":
        value = presentation.value
        direction = escape_display(value.direction).upper()
        if value.destination is None:
            return f"TUTORIAL {direction}"
        return f"TUTORIAL {direction} “{escape_display(value.destination.title)}”"
    if kind == "TutorialTry":
        return "TUTORIAL TRY"
    if kind == "PandasColumn":
        return "PANDAS COLUMN"
    if kind == "PandasRow":
        return "PANDAS ROW"
    return kind.upper()


def _tutorial_try_busy(listener: HeadlessListener, *, menu_open: bool = False) -> bool:
    return (
        menu_open or listener.input_mode != "empty"
        or bool(listener.python_pieces) or listener.chip is not None
        or bool(listener.pending_python_pieces)
        or listener.pending_request is not None
        or listener.pending_substring_listing is not None
    )


def _clauses(target: str, left: str, right: str = "no menu") -> str:
    return f"{target} • Left: {left} • Right: {right}"


def _selection_lead(listener: HeadlessListener) -> str | None:
    if listener.pending_substring_listing is not None:
        return "SELECTING TEXT FOR narrow"
    if listener.pending_request is not None:
        return f"SELECTING {format_mode(listener)[len('SELECT '):]}"
    return None


def format_documentation(
    listener: HeadlessListener,
    presentation: Presentation | None,
    logical_column: int | None = None,
    *,
    menu_open: bool = False,
) -> str:
    """Return the full target-first sentence for the retained pointer target."""
    kind = _domain_kind(listener, presentation)
    target = _target(listener, presentation)
    lead = _selection_lead(listener)
    if kind in {"TutorialTarget", "TutorialTry"}:
        if kind == "TutorialTry":
            left = (
                "finish or cancel current input before trying"
                if _tutorial_try_busy(listener, menu_open=menu_open)
                else "load example into editor; Enter runs"
            )
        else:
            control = presentation.value
            if control.destination is not None:
                left = "open"
            elif control.direction == "Back":
                left = "this section has no previous card"
            else:
                left = "this section has no next card"
        sentence = _clauses(target, left)
        return f"{lead} — {sentence}{_CANCEL}" if lead else sentence

    if listener.pending_substring_listing is not None:
        prefix = lead if presentation is None else f"{lead} — {target}"
        return f"{prefix} • {_SUBSTRING}{_CANCEL}"

    request = listener.pending_request
    if request is not None:
        required = _REQUIRED[request.command_name]
        if presentation is None:
            return f"{lead} • Point at highlighted {required} and click{_CANCEL}"
        if (
            kind in {"File", "Directory", "Process"}
            and presentation.presentation_type in request.acceptable_types
        ):
            left = "use and run command"
        else:
            type_name = escape_display(presentation.presentation_type.name)
            left = f"cannot use {type_name}; {required} required"
        return f"{lead} — {_clauses(target, left)}{_CANCEL}"

    if presentation is None:
        if listener.pending_python_source:
            return "NO TARGET • Python continuation: enter another line • Esc: discard • Ctrl-G: discard"
        return "READY"
    if kind is None:
        return "NO TARGET"

    has_menu = bool(
        listener.python_translators_for(presentation)
        if kind == "Value" else kind in _MENU_KINDS
    )
    right = "menu" if has_menu else "no menu"
    mode = listener.input_mode
    if kind in {"PythonInput", "CommandInput"}:
        if mode == "empty":
            left = "load into editor; Enter runs"
        elif mode == "python":
            left = "insert at cursor"
        else:
            left = "no action while editing command"
        return _clauses(target, left, right)
    if kind == "MenuActionInput":
        if mode == "empty":
            return _clauses(target, "run again on same object", right)
        if mode == "command":
            return _clauses(target, "no action while editing command", right)
    if mode == "python":
        reason = listener.python_insertion_reason(presentation)
        if reason == "valid":
            left = (
                "insert target into expression" if kind == "MenuActionInput"
                else "insert value into expression"
            )
            return _clauses(target, left, right)
        if reason == "literal":
            return _clauses(target, "insertion unavailable in string or comment", right)
        if reason == "expression":
            return _clauses(target, "move cursor to Python expression position to insert", right)

    if kind == "Process":
        member = _captured_process_member(listener, presentation)
        if (
            member is not None and logical_column is not None
            and 42 <= logical_column < 90 and display_width(member.command) > 48
        ):
            return _clauses(target + " (command truncated)", "show full command", right)
    if kind == "PandasColumn":
        return _clauses(target, "take column", right)
    if kind == "PandasRow":
        return _clauses(target, "take row", right)
    if kind == "Candle":
        return _clauses(target, "show", right)
    if kind == "Value" and isinstance(presentation.value, pd.DataFrame):
        return _clauses(target, "show frame preview", right)
    if kind == "Value" and isinstance(presentation.value, pd.Series):
        return _clauses(target, "list values", right)
    if kind in {"File", "Directory", "Process", "Value"}:
        if type(presentation.value) in {JsonObject, JsonArray}:
            return _clauses(target, "list members", right)
        return _clauses(target, "show", right)
    return _clauses(target, "no action", right)


def format_menu_item_documentation(
    listener: HeadlessListener, label: str, target: Presentation
) -> str:
    """Describe a popup item using its saved label and saved target."""
    kind = _domain_kind(listener, target)
    subject = f"MENU “{escape_display(label)}” ON {_target(listener, target)}"
    if kind in {"PythonInput", "CommandInput"}:
        left = "no action while editing command" if listener.input_mode == "command" else "yank into editor"
    elif kind == "MenuActionInput":
        left = "run again on same object"
    elif kind in {"File", "Directory", "Process"}:
        left = "run"
    else:
        left = "apply"
    return _clauses(subject, left)


def format_popup_failure(target: Presentation, listener: HeadlessListener, *, too_large: bool) -> str:
    """Describe a failed Ctrl-O menu open without implying a click action."""
    detail = (
        "Menu does not fit in history area" if too_large
        else "Point at object to open its menu"
    )
    return f"{_target(listener, target)} • {detail}"


_QUOTED_DETAIL = re.compile(r" “[^”]*”")


def fit_documentation(sentence: str, width: int) -> str:
    """Fit one safe row, preserving action and cancel clauses before labels."""
    if width <= 0:
        return ""
    if display_width(sentence) <= width:
        return sentence
    matches = list(_QUOTED_DETAIL.finditer(sentence))
    if matches:
        shortened = sentence
        for match in reversed(matches):
            start, end = match.span()
            excess = display_width(shortened) - width
            detail = shortened[start + 2:end - 1]
            if excess <= 0:
                break
            allowed = display_width(detail) - excess
            replacement = (
                " “" + truncate_display(detail, allowed) + "”"
                if allowed >= 1 else ""
            )
            shortened = shortened[:start] + replacement + shortened[end:]
        if display_width(shortened) <= width:
            return shortened
        sentence = shortened
    return truncate_display(sentence, width)
