"""Headless Python input pieces, atomic cursor editing, and source splicing."""

from __future__ import annotations

import ast
import io
import tokenize
from dataclasses import dataclass
from typing import Any, TypeAlias


@dataclass(frozen=True, eq=False, slots=True)
class PythonChip:
    value: Any
    label: str


Piece: TypeAlias = str | PythonChip


def _atoms(pieces: tuple[Piece, ...]) -> list[Piece]:
    return [
        atom
        for piece in pieces
        for atom in (piece if isinstance(piece, str) else (piece,))
    ]


def _pieces(atoms: list[Piece]) -> tuple[Piece, ...]:
    result: list[Piece] = []
    text: list[str] = []
    for atom in atoms:
        if isinstance(atom, str):
            text.append(atom)
        else:
            if text:
                result.append("".join(text))
                text.clear()
            result.append(atom)
    if text:
        result.append("".join(text))
    return tuple(result)


class PythonLine:
    """The cursor counts characters and whole chips, never display cells."""

    def __init__(self, pieces: tuple[Piece, ...] = (), cursor: int | None = None) -> None:
        self._pieces = _pieces(_atoms(pieces))
        length = len(_atoms(self._pieces))
        self.cursor = length if cursor is None else cursor
        if not 0 <= self.cursor <= length:
            raise ValueError("cursor is outside the line")

    @property
    def pieces(self) -> tuple[Piece, ...]:
        return self._pieces

    @property
    def text(self) -> str:
        return "".join(piece for piece in self._pieces if isinstance(piece, str))

    @property
    def has_chips(self) -> bool:
        return any(isinstance(piece, PythonChip) for piece in self._pieces)

    def set_text(self, text: str) -> None:
        if not isinstance(text, str):
            raise TypeError("input text must be a string")
        self._pieces = (text,) if text else ()
        self.cursor = len(text)

    def insert_text(self, text: str) -> None:
        if not isinstance(text, str):
            raise TypeError("input text must be a string")
        atoms = _atoms(self._pieces)
        atoms[self.cursor:self.cursor] = list(text)
        self.cursor += len(text)
        self._pieces = _pieces(atoms)

    def insert_chip(self, chip: PythonChip) -> None:
        atoms = _atoms(self._pieces)
        atoms.insert(self.cursor, chip)
        self.cursor += 1
        self._pieces = _pieces(atoms)

    def split_at_cursor(self) -> tuple[tuple[Piece, ...], tuple[Piece, ...]]:
        atoms = _atoms(self._pieces)
        return _pieces(atoms[:self.cursor]), _pieces(atoms[self.cursor:])

    def left(self) -> None:
        self.cursor = max(0, self.cursor - 1)

    def right(self) -> None:
        self.cursor = min(len(_atoms(self._pieces)), self.cursor + 1)

    def home(self) -> None:
        self.cursor = 0

    def end(self) -> None:
        self.cursor = len(_atoms(self._pieces))

    def backspace(self) -> bool:
        if self.cursor == 0:
            return False
        atoms = _atoms(self._pieces)
        del atoms[self.cursor - 1]
        self.cursor -= 1
        self._pieces = _pieces(atoms)
        return True

    def delete(self) -> bool:
        atoms = _atoms(self._pieces)
        if self.cursor == len(atoms):
            return False
        del atoms[self.cursor]
        self._pieces = _pieces(atoms)
        return True


def _identifier_tail(character: str) -> bool:
    return bool(character) and ("a" + character).isidentifier()


def _contains_identifier(text: str, candidate: str) -> bool:
    start = 0
    while (start := text.find(candidate, start)) >= 0:
        stop = start + len(candidate)
        if (start == 0 or not _identifier_tail(text[start - 1])) and (
            stop == len(text) or not _identifier_tail(text[stop])
        ):
            return True
        start += 1
    return False


def splice(
    lines: tuple[tuple[Piece, ...], ...], namespace: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    """Allocate one fresh binding for every chip occurrence in source order."""

    # The collision scan must see adjacent text runs as contiguous source.
    stretches: list[str] = []
    for line in lines:
        stretch = ""
        for piece in line:
            if isinstance(piece, str):
                stretch += piece
            else:
                stretches.append(stretch)
                stretch = ""
        stretches.append(stretch)
    bindings: dict[str, Any] = {}
    parts: list[str] = []
    number = 0
    for line_number, line in enumerate(lines):
        if line_number:
            parts.append("\n")
        for piece in line:
            if isinstance(piece, str):
                parts.append(piece)
                continue
            while True:
                name = f"_pbui_chip_{number}"
                number += 1
                if name not in namespace and not any(
                    _contains_identifier(stretch, name) for stretch in stretches
                ):
                    break
            bindings[name] = piece.value
            parts.append(name)
    return "".join(parts), bindings


def _probe_source(
    lines: tuple[tuple[Piece, ...], ...], line: PythonLine
) -> tuple[str, int, str]:
    occupied = "".join(
        piece
        for row in lines + (line.pieces,)
        for piece in row
        if isinstance(piece, str)
    )
    marker = "__pbui_probe__"
    while marker in occupied:
        marker += "_"

    def render(pieces: tuple[Piece, ...]) -> str:
        return "".join(
            piece if isinstance(piece, str) else "__pbui_prior_chip__"
            for piece in pieces
        )
    current_atoms = _atoms(line.pieces)
    prefix = render(_pieces(current_atoms[:line.cursor]))
    suffix = render(_pieces(current_atoms[line.cursor:]))
    pending = "\n".join(render(row) for row in lines)
    before = pending + "\n" if lines else ""
    return before + prefix + marker + suffix, len(before + prefix), marker


def insertion_site_reason(lines: tuple[tuple[Piece, ...], ...], line: PythonLine) -> str:
    """Classify a probe as valid, literal text, or another invalid site."""

    source, position, marker = _probe_source(lines, line)
    original = source[:position] + source[position + len(marker):]
    starts = [0]
    for index, character in enumerate(original):
        if character == "\n":
            starts.append(index + 1)

    def absolute(point: tuple[int, int]) -> int:
        row, column = point
        return starts[row - 1] + column if row <= len(starts) else len(original)
    opening: list[str] = []
    fstrings: list[int] = []
    fstring_start = getattr(tokenize, "FSTRING_START", None)
    fstring_end = getattr(tokenize, "FSTRING_END", None)
    try:
        tokens = tokenize.generate_tokens(io.StringIO(original).readline)
        for token in tokens:
            start, end = absolute(token.start), absolute(token.end)
            if token.type == fstring_start:
                fstrings.append(start)
            elif token.type == fstring_end and fstrings:
                if fstrings.pop() < position <= end:
                    return "literal"
            if (
                token.type in (tokenize.STRING, tokenize.COMMENT)
                and start < position <= end
            ):
                return "literal"
            if token.type == tokenize.ERRORTOKEN and token.string in ("'", '"'):
                line_end = original.find("\n", start)
                if line_end < 0:
                    line_end = len(original)
                if start < position <= line_end:
                    return "literal"
            if token.type == tokenize.OP:
                if token.string in "([{":
                    opening.append({"(": ")", "[": "]", "{": "}"}[token.string])
                elif opening and token.string == opening[-1]:
                    opening.pop()
    except tokenize.TokenError as error:
        message, point = error.args
        if "string" in message and absolute(point) < position:
            return "literal"
    if fstrings and fstrings[-1] < position:
        return "literal"
    try:
        tree = ast.parse(source + "".join(reversed(opening)))
    except (SyntaxError, ValueError):
        return "expression"
    return "valid" if any(
        isinstance(node, ast.Name)
        and node.id == marker
        and isinstance(node.ctx, ast.Load)
        for node in ast.walk(tree)
    ) else "expression"


def valid_insertion_site(lines: tuple[tuple[Piece, ...], ...], line: PythonLine) -> bool:
    return insertion_site_reason(lines, line) == "valid"
