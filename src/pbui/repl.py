"""Synchronous, headless Python evaluation and object-bearing value rows."""

from __future__ import annotations

import code
import reprlib
import sys
import traceback
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

import sympy

from pbui.chips import Piece, splice
from pbui.domain import escape_display
from pbui.substrate import Presentation, PresentationHistory, PresentationType
from pbui.text import (
    DrawingContext,
    HistoryRow,
    LiteralFragment,
    PresentedFragment,
    display_width,
    truncate_display,
)


@dataclass(frozen=True, slots=True)
class ValueTranslator:
    label: str
    function: Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class ValueRegistration:
    printer: Callable[[Any], str]
    translators: tuple[ValueTranslator, ...]


class ValueClasses:
    """First registered class in the value's MRO supplies its presentation rules."""

    def __init__(self) -> None:
        self._entries: dict[type, ValueRegistration] = {}

    def register(
        self,
        cls: type,
        printer: Callable[[Any], str],
        translators: Iterable[ValueTranslator] = (),
    ) -> None:
        if not isinstance(cls, type):
            raise TypeError("class registration needs a Python class")
        if cls in self._entries:
            raise ValueError("class is already registered")
        if not callable(printer):
            raise TypeError("printer must be callable")
        entries = tuple(translators)
        if any(
            not isinstance(item, ValueTranslator)
            or not item.label
            or not callable(item.function)
            for item in entries
        ):
            raise TypeError("translators need a label and callable function")
        self._entries[cls] = ValueRegistration(printer, entries)

    def lookup(self, value: Any) -> ValueRegistration | None:
        for cls in type(value).__mro__:
            if cls in self._entries:
                return self._entries[cls]
        return None

    def translators_for(self, value: Any) -> tuple[ValueTranslator, ...]:
        registration = self.lookup(value)
        return () if registration is None else registration.translators


class _LineWriter:
    def __init__(self, prefix: str, append_text: Callable[[str], None]) -> None:
        self.prefix = prefix
        self.append_text = append_text
        self.partial = ""

    def write(self, text: str) -> int:
        if not isinstance(text, str):
            raise TypeError("write() argument must be str")
        pieces = (self.partial + text).split("\n")
        for complete in pieces[:-1]:
            self.append_text(
                truncate_display(escape_display(self.prefix + complete), 4096)
            )
        self.partial = pieces[-1]
        return len(text)

    def flush(self) -> None:
        pass

    def finish(self) -> None:
        if self.partial:
            self.append_text(
                truncate_display(escape_display(self.prefix + self.partial), 4096)
            )
            self.partial = ""


class _ValueRepr(reprlib.Repr):
    def repr_instance(self, value: Any, level: int) -> str:
        return repr(value)


def _bounded_repr(value: Any, *, depth: int = 4, items: int = 16) -> str:
    printer = _ValueRepr()
    printer.maxlevel = depth
    printer.maxdict = printer.maxlist = printer.maxtuple = items
    printer.maxset = printer.maxfrozenset = printer.maxdeque = items
    printer.maxstring = printer.maxother = 512
    return printer.repr(value)


def _sympy_row(value: sympy.Expr) -> str:
    pretty = sympy.pretty(value, use_unicode=True, wrap_line=False)
    return pretty if "\n" not in pretty else sympy.sstr(value)


def _compile_error(error: SyntaxError | OverflowError | ValueError) -> str:
    kind = "SyntaxError" if isinstance(error, SyntaxError) else type(error).__name__
    message = f"{kind}: {error.msg if isinstance(error, SyntaxError) else error}"
    if isinstance(error, SyntaxError) and error.lineno is not None and error.offset is not None:
        message += f" (line {error.lineno}, column {error.offset})"
    return truncate_display(escape_display(message + "."), 4096)


def _execution_error(
    error: BaseException, source: str, command_names: tuple[str, ...]
) -> str:
    last = f"{type(error).__name__}: {error}"
    name = source.strip()
    if isinstance(error, NameError) and name in command_names and error.name == name:
        last += f" Use :{name} to run the listener command."
    final = escape_display(last)
    if display_width(final) > 4096:
        return truncate_display(final, 4096)
    header = escape_display("Traceback (most recent call last):\n")
    frames = [
        escape_display(item)
        for item in traceback.format_list(
            traceback.extract_tb(error.__traceback__, limit=-8)
        )
    ]
    while frames and display_width(header + "".join(frames) + final) > 4096:
        frames.pop(0)
    combined = header + "".join(frames) + final
    if display_width(combined) > 4096:
        budget = 4096 - display_width(final)
        combined = truncate_display(header, budget) + final if budget > 0 else final
    return combined


class PythonEvaluator:
    def __init__(
        self,
        history: PresentationHistory,
        context: DrawingContext,
        value_type: PresentationType,
        append_text: Callable[[str], None],
        append_error: Callable[[str], None],
        command_names: tuple[str, ...],
    ) -> None:
        self.namespace: dict[str, Any] = {"__name__": "__pbui__"}
        self.pending_lines: tuple[tuple[Piece, ...], ...] = ()
        self.classes = ValueClasses()
        self.classes.register(
            sympy.Expr,
            _sympy_row,
            (
                ValueTranslator("simplify", sympy.simplify),
                ValueTranslator("expand", sympy.expand),
                ValueTranslator("factor", sympy.factor),
            ),
        )
        self._history = history
        self._context = context
        self._value_type = value_type
        self._append_text = append_text
        self._append_error = append_error
        self._command_names = command_names

    @property
    def pending_source(self) -> str:
        # Retain the chip-free string interface used by the terminal adapter.
        return "\n".join(
            "".join(piece if isinstance(piece, str) else f"⟨{piece.label}⟩" for piece in line)
            for line in self.pending_lines
        )

    def cancel(self) -> None:
        self.pending_lines = ()

    def submit(self, line: str) -> None:
        self.submit_pieces((line,))

    def submit_pieces(self, line: tuple[Piece, ...]) -> None:
        lines = self.pending_lines + (line,)
        source, bindings = splice(lines, self.namespace)
        try:
            compiled = code.compile_command(source, symbol="single")
        except (SyntaxError, OverflowError, ValueError) as error:
            self.pending_lines = ()
            self._append_error(_compile_error(error))
            return
        if compiled is None:
            self.pending_lines = lines
            return
        self.pending_lines = ()
        stdout = _LineWriter("", self._append_text)
        stderr = _LineWriter("stderr: ", self._append_text)
        old_hook, old_stdout, old_stderr = sys.displayhook, sys.stdout, sys.stderr
        try:
            self.namespace.update(bindings)
            sys.displayhook = self._display_hook
            sys.stdout, sys.stderr = stdout, stderr
            try:
                exec(compiled, self.namespace, self.namespace)
            except BaseException as error:
                stdout.finish()
                stderr.finish()
                self._append_error(_execution_error(error, source, self._command_names))
            else:
                stdout.finish()
                stderr.finish()
        finally:
            sys.displayhook, sys.stdout, sys.stderr = old_hook, old_stdout, old_stderr
            for name in bindings:
                self.namespace.pop(name, None)

    def _display_hook(self, value: Any) -> None:
        self.display_value(value)

    def display_value(
        self, value: Any, *, include_none: bool = False
    ) -> Presentation | None:
        if value is None and not include_none:
            return None
        self.namespace["_"] = value
        row = self._context.present_row(value, self._value_type)
        self._history.append(row)
        presentation = row.presentations[0]
        try:
            registration = self.classes.lookup(value)
            if registration is None:
                kind = truncate_display(escape_display(type(value).__name__), 64)
                representation = truncate_display(
                    escape_display(_bounded_repr(value)), 96
                )
                drawing = f"{kind} {representation}"
            else:
                drawing = truncate_display(escape_display(registration.printer(value)), 120)
            updated = HistoryRow(
                (PresentedFragment(presentation.id, (LiteralFragment(drawing),)),),
                (presentation,),
            )
            self._history.replace_row(row, updated)
        except BaseException as error:
            self._append_error(_execution_error(error, "", self._command_names))
        return presentation

    def invoke_translator(
        self, presentation: Presentation, index: int
    ) -> Presentation | None:
        if (
            presentation.presentation_type is not self._value_type
            or self._history.get_presentation(presentation.id) is not presentation
        ):
            raise ValueError("translator requires a retained Value presentation")
        translator = self.classes.translators_for(presentation.value)[index]
        try:
            result = translator.function(presentation.value)
        except BaseException as error:
            self._append_error(_execution_error(error, "", self._command_names))
            return None
        return self.display_value(result, include_none=True)

    def show_detail(self, presentation: Presentation) -> bool:
        """Append detail for the exact retained Value, leaving its identity intact."""

        if (
            presentation.presentation_type is not self._value_type
            or self._history.get_presentation(presentation.id) is not presentation
        ):
            return False
        value = presentation.value
        try:
            if isinstance(value, sympy.Expr):
                pretty_lines = sympy.pretty(
                    value, use_unicode=True, wrap_line=False
                ).split("\n")
                detail_rows = [
                    truncate_display(escape_display(line), 120)
                    for line in pretty_lines[:24]
                ]
                if len(pretty_lines) > 24:
                    detail_rows.append(f"… ({len(pretty_lines) - 24} more lines)")
            else:
                kind = truncate_display(escape_display(type(value).__name__), 64)
                representation = truncate_display(
                    escape_display(_bounded_repr(value, depth=6, items=64)), 4096
                )
                detail_rows = [f"{kind}: {representation}"]
        except BaseException as error:
            self._append_error(_execution_error(error, "", self._command_names))
        else:
            for row in detail_rows:
                self._append_text(row)
        return True
