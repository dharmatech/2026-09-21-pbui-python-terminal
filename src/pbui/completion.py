"""Headless lexical sites and live name discovery for input completion."""

from __future__ import annotations

import builtins
import importlib.machinery
import io
import keyword
import pkgutil
import sys
import tokenize
from dataclasses import dataclass
from typing import Any, Iterable

from pbui.chips import Piece, PythonChip, PythonLine


@dataclass(frozen=True, slots=True)
class CompletionResult:
    start: int
    end: int
    fragment: str
    candidates: tuple[str, ...]


def _matching(names: Iterable[str], fragment: str) -> tuple[str, ...]:
    return tuple(sorted({
        name for name in names
        if isinstance(name, str)
        and name.isidentifier()
        and name.startswith(fragment)
        and (fragment.startswith("_") or not name.startswith("_"))
    }))



_ADDITIONAL_CHILDREN = {"os": ("path",), "collections": ("abc",)}


def _module_children(parent: tuple[str, ...]) -> tuple[str, ...]:
    """Find direct children using package search paths, without importing parents."""

    if not parent:
        try:
            discovered = (name for _, name, _ in pkgutil.iter_modules())
            return tuple(
                set(discovered) | set(sys.builtin_module_names) | set(sys.stdlib_module_names)
            )
        except Exception:
            return ()
    locations = None
    try:
        for length in range(1, len(parent) + 1):
            spec = importlib.machinery.PathFinder.find_spec(
                ".".join(parent[:length]), locations,
            )
            if spec is None or spec.submodule_search_locations is None:
                locations = None
                break
            locations = spec.submodule_search_locations
        discovered = (
            {name for _, name, _ in pkgutil.iter_modules(locations)}
            if locations is not None else set()
        )
    except Exception:
        return ()
    return tuple(discovered | set(_ADDITIONAL_CHILDREN.get(".".join(parent), ())))


def command_completion(
    text: str, cursor: int, names: Iterable[str], *, has_chip: bool = False
) -> CompletionResult | None:
    """Locate only the command-name token in the existing colon grammar."""

    if has_chip:
        return None
    start = len(text) - len(text.lstrip())
    if start >= len(text) or text[start] != ":":
        return None
    start += 1
    while start < len(text) and text[start].isspace():
        start += 1
    end = start
    while end < len(text) and (text[end].isalnum() or text[end] == "_"):
        end += 1
    if text[end:] or not start <= cursor <= end:
        return None
    fragment = text[start:cursor]
    return CompletionResult(start, end, fragment, tuple(sorted({
        name for name in names if name.startswith(fragment)
    })))


def _atoms(pieces: tuple[Piece, ...]) -> list[Piece]:
    return [atom for piece in pieces for atom in (
        piece if isinstance(piece, str) else (piece,)
    )]


def _render_source(
    pending: tuple[tuple[Piece, ...], ...], atoms: list[Piece], cursor: int
) -> tuple[str, int, str]:
    """Render chips as opaque tokens and map the current atom boundary."""

    all_text = "".join(
        piece for row in pending for piece in row if isinstance(piece, str)
    ) + "".join(atom for atom in atoms if isinstance(atom, str))
    sentinel = "__pbui_completion_chip__"
    while sentinel in all_text:
        sentinel += "_"
    count = 0

    def render(row: Iterable[Piece]) -> str:
        nonlocal count
        parts: list[str] = []
        for atom in row:
            if isinstance(atom, str):
                parts.append(atom)
            else:
                parts.append(f"{sentinel}{count}__")
                count += 1
        return "".join(parts)

    prefix = "\n".join(render(row) for row in pending)
    before = prefix + "\n" if pending else ""
    left = render(atoms[:cursor])
    right = render(atoms[cursor:])
    return before + left + right, len(before) + len(left), sentinel


def _lexical_context(source: str, position: int) -> tuple[bool, tuple[str, ...]]:
    """Reject literal positions and return tokens of the current statement."""

    starts = [0]
    for index, char in enumerate(source):
        if char == "\n":
            starts.append(index + 1)

    def absolute(point: tuple[int, int]) -> int:
        row, column = point
        return starts[row - 1] + column if row <= len(starts) else len(source)

    statement: list[str] = []
    depth = 0
    fstring_start = getattr(tokenize, "FSTRING_START", -1)
    fstring_end = getattr(tokenize, "FSTRING_END", -1)
    in_fstring = False
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            start, end = absolute(token.start), absolute(token.end)
            if token.type == fstring_start:
                in_fstring = True
            if in_fstring and start < position <= end:
                return False, ()
            if token.type == fstring_end:
                in_fstring = False
            if token.type in (tokenize.STRING, tokenize.COMMENT) and start < position <= end:
                return False, ()
            if token.type == tokenize.ERRORTOKEN and token.string in ("'", '"'):
                line_end = source.find("\n", start)
                if line_end < 0:
                    line_end = len(source)
                if start < position <= line_end:
                    return False, ()
            if start >= position:
                break
            if token.type == tokenize.NEWLINE:
                statement.clear()
                continue
            if token.type == tokenize.OP:
                if token.string in "([{":
                    depth += 1
                elif token.string in ")]}":
                    depth = max(0, depth - 1)
                elif token.string == ";" and depth == 0:
                    statement.clear()
                    continue
                elif token.string == ":" and depth == 0 and statement:
                    statement.clear()
                    continue
            if token.type not in (
                tokenize.NL, tokenize.INDENT, tokenize.DEDENT,
                tokenize.ENCODING, tokenize.ENDMARKER, tokenize.COMMENT,
            ):
                statement.append(token.string)
    except tokenize.TokenError as error:
        message, point = error.args
        if "string" in message and absolute(point) < position:
            return False, ()
    if in_fstring:
        return False, ()
    return True, tuple(statement)



def _plain_name(token: str) -> bool:
    return token.isidentifier() and not keyword.iskeyword(token)


def _import_module_context(tokens: tuple[str, ...]) -> tuple[str, tuple[str, ...]] | None:
    """Parse completed import targets up to the component at the caret."""

    parts: list[str] = []
    state = "name"
    for token in tokens:
        if state == "name":
            if not _plain_name(token):
                return None
            parts.append(token)
            state = "after_name"
        elif state == "after_name":
            if token == ".":
                state = "name"
            elif token == ",":
                parts.clear()
                state = "name"
            elif token == "as":
                state = "alias"
            else:
                return None
        elif state == "alias":
            if not _plain_name(token):
                return None
            state = "after_alias"
        elif state == "after_alias":
            if token != ",":
                return None
            parts.clear()
            state = "name"
    return ("module", tuple(parts)) if state == "name" else None


def _from_target_context(
    tokens: tuple[str, ...], module: tuple[str, ...],
) -> tuple[str, tuple[str, ...]] | None:
    state = "target"
    parenthesized = False
    for index, token in enumerate(tokens):
        if state == "target":
            if index == 0 and token == "(":
                parenthesized = True
            elif _plain_name(token):
                state = "after_target"
            else:
                return None
        elif state == "after_target":
            if token == ",":
                state = "target"
            elif token == "as":
                state = "alias"
            elif token == ")" and parenthesized:
                state = "closed"
            else:
                return None
        elif state == "alias":
            if not _plain_name(token):
                return None
            state = "after_alias"
        elif state == "after_alias":
            if token == ",":
                state = "target"
            elif token == ")" and parenthesized:
                state = "closed"
            else:
                return None
        else:
            return None
    return ("from_target", module) if state == "target" else None


def _import_context(
    statement: tuple[str, ...], current_name: str, fragment: str,
) -> tuple[str, tuple[str, ...]] | None:
    """Find the import grammar position immediately before this identifier."""

    tokens = statement
    if fragment and tokens and tokens[-1] == current_name:
        tokens = tokens[:-1]
    if not tokens:
        return None
    if tokens[0] == "import":
        return _import_module_context(tokens[1:])
    if tokens[0] != "from":
        return None
    module: list[str] = []
    state = "name"
    for index, token in enumerate(tokens[1:], 1):
        if state == "name":
            if not _plain_name(token):
                return None
            module.append(token)
            state = "after_name"
        elif token == ".":
            state = "name"
        elif token == "import":
            return _from_target_context(tokens[index + 1:], tuple(module))
        else:
            return None
    return ("module", tuple(module)) if state == "name" else None


def _identifier_span(atoms: list[Piece], cursor: int) -> tuple[int, int, str] | None:
    start = cursor
    while start > 0 and isinstance(atoms[start - 1], str) and (
        atoms[start - 1].isalnum() or atoms[start - 1] == "_"
    ):
        start -= 1
    end = cursor
    while end < len(atoms) and isinstance(atoms[end], str) and (
        atoms[end].isalnum() or atoms[end] == "_"
    ):
        end += 1
    name = "".join(atoms[start:end])
    if name and not name.isidentifier():
        return None
    return start, end, "".join(atoms[start:cursor])


def _receiver(atoms: list[Piece], dot: int, namespace: dict[str, Any]) -> Any:
    """Resolve a plain dotted chain, without evaluating expressions."""

    position = dot
    attributes: list[str] = []
    while True:
        if position and isinstance(atoms[position - 1], PythonChip):
            if position > 1 and (
                isinstance(atoms[position - 2], PythonChip)
                or atoms[position - 2] in (".", ")", "]", "}")
                or (
                    isinstance(atoms[position - 2], str)
                    and (atoms[position - 2].isalnum() or atoms[position - 2] == "_")
                )
            ):
                raise LookupError("chip is not a plain receiver")
            value = atoms[position - 1].value
            break
        end = position
        while position and isinstance(atoms[position - 1], str) and (
            atoms[position - 1].isalnum() or atoms[position - 1] == "_"
        ):
            position -= 1
        name = "".join(atoms[position:end])
        if not name.isidentifier() or keyword.iskeyword(name):
            raise LookupError("not a plain attribute chain")
        if position and atoms[position - 1] == ".":
            attributes.append(name)
            position -= 1
            continue
        if name in namespace:
            value = namespace[name]
        elif hasattr(builtins, name):
            value = getattr(builtins, name)
        else:
            raise LookupError("unbound root")
        break
    for attribute in reversed(attributes):
        value = getattr(value, attribute)
    return value


def python_completion(
    pending: tuple[tuple[Piece, ...], ...], line: PythonLine,
    namespace: dict[str, Any],
) -> CompletionResult | None:
    """Find a current-line Python name, attribute, or import site."""

    atoms = _atoms(line.pieces)
    cursor = line.cursor
    span = _identifier_span(atoms, cursor)
    if span is None:
        return None
    start, end, fragment = span
    dotted = start > 0 and atoms[start - 1] == "."
    source, position, sentinel = _render_source(pending, atoms, cursor)
    permitted, statement = _lexical_context(source, position)
    if not permitted:
        return None
    if statement and statement[0] in {"import", "from"}:
        if any(isinstance(atom, PythonChip) for atom in atoms):
            return None
        if any(token.startswith(sentinel) for token in statement):
            return None
        current_name = "".join(atoms[start:end])
        context = _import_context(statement, current_name, fragment)
        if context is None:
            return None
        kind, parent = context
        if kind == "module":
            names = _module_children(parent)
        elif parent[0] in namespace:
            try:
                value = namespace[parent[0]]
                for attribute in parent[1:]:
                    value = getattr(value, attribute)
                names = dir(value)
            except Exception:
                return None
        else:
            names = _module_children(parent)
        return CompletionResult(start, end, fragment, _matching(names, fragment))
    if not dotted and not fragment:
        return None
    if statement and statement[0] in {
        ":", "def", "class", "global", "nonlocal",
    }:
        return None
    if dotted:
        try:
            names = dir(_receiver(atoms, start - 1, namespace))
        except Exception:
            return None
    else:
        names = (*namespace, *vars(builtins), *keyword.kwlist)
    return CompletionResult(start, end, fragment, _matching(names, fragment))
