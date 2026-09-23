"""Headless listener, host seams, and the ten ``pbui`` commands.

The module is deliberately independent of terminal UI libraries.  It owns the
coherent application model which a later terminal adapter will render.
"""

from __future__ import annotations

import errno
import os
import pwd
import signal
import stat as stat_module
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol

from pbui.domain import (
    DirectoryListing,
    DirectoryListingMember,
    DirectoryRef,
    DomainDrawingContexts,
    DomainParseError,
    DomainTypes,
    FileRef,
    ProcessListing,
    ProcessListingMember,
    ProcessRef,
    TypedDomainValue,
    compose_failure_message,
    directory_listing_rows,
    escape_display,
    format_path_detail,
    format_process_detail,
    format_removed_file,
    format_signal_result,
    make_domain_drawing_contexts,
    parse_directory,
    parse_file,
    parse_process,
    parse_show,
    process_listing_rows,
    register_domain_types,
)
from pbui.substrate import (
    AcceptRequest,
    Chip,
    Presentation,
    PresentationHistory,
    PresentationType,
    PresentationTypeRegistry,
    SubstrateState,
    TranslatorTable,
)
from pbui.chips import Piece, PythonChip, PythonLine, insertion_site_reason
from pbui.text import HistoryRow, logical_presentation_text, truncate_display
from pbui.repl import PythonEvaluator, ValueClasses, ValueTranslator


@dataclass(frozen=True, slots=True)
class FilesystemEntry:
    """The name and lexical absolute path of one directory child."""

    name: str
    path: str


class FilesystemService(Protocol):
    """Filesystem operations used by the headless listener."""

    def abspath(self, path: str) -> str: ...

    def stat(self, path: str) -> os.stat_result: ...

    def lstat(self, path: str) -> os.stat_result: ...

    def readlink(self, path: str) -> str: ...

    def iter_directory(self, path: str) -> Iterable[FilesystemEntry]: ...

    def unlink(self, path: str) -> None: ...


@dataclass(frozen=True, slots=True)
class ProductionFilesystem:
    """Production filesystem service backed directly by :mod:`os`."""

    def abspath(self, path: str) -> str:
        return os.path.abspath(path)

    def stat(self, path: str) -> os.stat_result:
        return os.stat(path)

    def lstat(self, path: str) -> os.stat_result:
        return os.lstat(path)

    def readlink(self, path: str) -> str:
        return os.readlink(path)

    def iter_directory(self, path: str) -> tuple[FilesystemEntry, ...]:
        with os.scandir(path) as entries:
            return tuple(
                FilesystemEntry(entry.name, os.path.join(path, entry.name))
                for entry in entries
            )

    def unlink(self, path: str) -> None:
        os.unlink(path)


class RootedFilesystem:
    """A real-filesystem adapter confined to one canonical test root.

    Followed operations validate the canonical candidate.  Operations on a
    final directory entry validate the canonical parent and retain the final
    component, allowing a safe final symlink to be inspected or unlinked.
    """

    def __init__(self, allowed_root: os.PathLike[str] | str) -> None:
        root = os.path.realpath(os.path.abspath(os.fspath(allowed_root)))
        root_stat = os.stat(root)
        if not stat_module.S_ISDIR(root_stat.st_mode):
            raise NotADirectoryError(errno.ENOTDIR, "not a directory", root)
        self._allowed_root = root

    @property
    def allowed_root(self) -> str:
        return self._allowed_root

    def _normalized_absolute(self, path: str) -> str:
        if not isinstance(path, str):
            raise TypeError("path must be a string")
        if not os.path.isabs(path) or os.path.abspath(path) != path:
            raise PermissionError(errno.EACCES, "path is not absolute and normalized", path)
        return path

    def _is_contained(self, candidate: str) -> bool:
        try:
            return os.path.commonpath((self._allowed_root, candidate)) == self._allowed_root
        except ValueError:
            return False

    def _require_contained(self, candidate: str, original: str) -> None:
        if not self._is_contained(candidate):
            raise PermissionError(errno.EACCES, "path is outside allowed root", original)

    def _check_followed(self, path: str) -> str:
        candidate = self._normalized_absolute(path)
        followed = os.path.realpath(candidate)
        self._require_contained(followed, candidate)
        return candidate

    def _check_final_entry(self, path: str) -> str:
        candidate = self._normalized_absolute(path)
        if candidate == self._allowed_root:
            return candidate
        parent = os.path.realpath(os.path.dirname(candidate))
        self._require_contained(parent, candidate)
        return candidate

    def abspath(self, path: str) -> str:
        candidate = os.path.abspath(path)
        return self._check_final_entry(candidate)

    def stat(self, path: str) -> os.stat_result:
        return os.stat(self._check_followed(path))

    def lstat(self, path: str) -> os.stat_result:
        return os.lstat(self._check_final_entry(path))

    def readlink(self, path: str) -> str:
        return os.readlink(self._check_final_entry(path))

    def iter_directory(self, path: str) -> tuple[FilesystemEntry, ...]:
        candidate = self._check_followed(path)
        with os.scandir(candidate) as entries:
            return tuple(
                FilesystemEntry(entry.name, os.path.join(candidate, entry.name))
                for entry in entries
            )

    def unlink(self, path: str) -> None:
        os.unlink(self._check_final_entry(path))


@dataclass(frozen=True, slots=True)
class InspectedProcess:
    """Freshly inspected process information used for listing and details."""

    pid: int
    real_uid: int
    state: str
    command: str


class ProcessService(Protocol):
    @property
    def own_uid(self) -> int: ...

    @property
    def own_pid(self) -> int: ...

    def list_for_uid(self, uid: int) -> Iterable[InspectedProcess]: ...

    def inspect(self, pid: int) -> InspectedProcess: ...

    def send_sigterm(self, pid: int) -> None: ...


class ProcessInspectionError(OSError):
    """A missing or malformed required field in a process record."""


_PROCESS_STATES = {
    "R": "running",
    "S": "sleeping",
    "D": "disk-sleep",
    "T": "stopped",
    "t": "tracing",
    "Z": "zombie",
    "X": "dead",
    "x": "dead",
    "I": "idle",
}


def process_state_word(code: str) -> str:
    """Translate one Linux process-state code to the product wording."""

    return _PROCESS_STATES.get(code, "unknown")


class LinuxProcessService:
    """Linux process inspection through ``/proc`` and signaling through ``os``."""

    def __init__(
        self,
        proc_root: os.PathLike[str] | str = "/proc",
        *,
        getuid: Callable[[], int] | None = None,
        getpid: Callable[[], int] | None = None,
        kill: Callable[[int, int], None] | None = None,
    ) -> None:
        self._proc_root = os.fspath(proc_root)
        self._getuid = os.getuid if getuid is None else getuid
        self._getpid = os.getpid if getpid is None else getpid
        self._kill = os.kill if kill is None else kill
        self._own_uid = self._getuid()
        self._own_pid = self._getpid()

    @property
    def own_uid(self) -> int:
        return self._own_uid

    @property
    def own_pid(self) -> int:
        return self._own_pid

    @property
    def proc_root(self) -> str:
        return self._proc_root

    def _read_status(self, pid: int) -> tuple[str, int, str]:
        status_path = os.path.join(self._proc_root, str(pid), "status")
        with open(status_path, "rb") as status_file:
            status_text = status_file.read().decode(
                sys.getfilesystemencoding(), errors="surrogateescape"
            )

        fields: dict[str, str] = {}
        for line in status_text.splitlines():
            key, separator, value = line.partition(":")
            if separator and key in {"Name", "Uid", "State"} and key not in fields:
                fields[key] = value.lstrip(" \t")

        missing = {"Name", "Uid", "State"}.difference(fields)
        if missing:
            names = ", ".join(sorted(missing))
            raise ProcessInspectionError(
                f"malformed process {pid} status: missing {names}"
            )
        if not fields["Name"]:
            raise ProcessInspectionError(f"malformed process {pid} status: empty Name")

        uid_fields = fields["Uid"].split()
        if not uid_fields:
            raise ProcessInspectionError(f"malformed process {pid} status: invalid Uid")
        try:
            real_uid = int(uid_fields[0], 10)
        except ValueError as error:
            raise ProcessInspectionError(
                f"malformed process {pid} status: invalid Uid"
            ) from error

        state_value = fields["State"]
        if not state_value or state_value[0].isspace():
            raise ProcessInspectionError(f"malformed process {pid} status: invalid State")
        return fields["Name"], real_uid, process_state_word(state_value[0])

    def inspect(self, pid: int) -> InspectedProcess:
        name, real_uid, state = self._read_status(pid)
        cmdline_path = os.path.join(self._proc_root, str(pid), "cmdline")
        with open(cmdline_path, "rb") as cmdline_file:
            raw_command = cmdline_file.read()
        if raw_command:
            command = raw_command.replace(b"\0", b" ").decode(
                sys.getfilesystemencoding(), errors="surrogateescape"
            )
        else:
            command = name
        return InspectedProcess(pid, real_uid, state, command)

    def list_for_uid(self, uid: int) -> tuple[InspectedProcess, ...]:
        with os.scandir(self._proc_root) as entries:
            pids = sorted(
                int(entry.name)
                for entry in entries
                if entry.name.isascii() and entry.name.isdecimal()
            )
        records: list[InspectedProcess] = []
        for pid in pids:
            try:
                record = self.inspect(pid)
            except OSError:
                continue
            if record.real_uid == uid:
                records.append(record)
        return tuple(records)

    def send_sigterm(self, pid: int) -> None:
        self._kill(pid, signal.SIGTERM)


_ABSENT_OR_UNRESOLVED = frozenset({errno.ENOENT, errno.ENOTDIR, errno.ELOOP})


def _production_username_lookup(uid: int) -> str:
    return pwd.getpwuid(uid).pw_name


class HeadlessListener:
    """One UI-independent listener model and its complete command layer."""

    COMMAND_NAMES = (
        "ls",
        "ps",
        "show",
        "kill",
        "cd",
        "rm",
        "sort",
        "narrow",
        "only",
        "widen",
    )
    VIEW_COMMAND_NAMES = frozenset({"sort", "narrow", "only", "widen"})

    def __init__(
        self,
        starting_cwd: str,
        filesystem: FilesystemService,
        processes: ProcessService,
        *,
        history_max_rows: int = PresentationHistory.MAX_LOGICAL_ROWS,
        username_lookup: Callable[[int], object] | None = None,
    ) -> None:
        normalized_cwd = filesystem.abspath(starting_cwd)
        cwd_stat = filesystem.stat(normalized_cwd)
        if not stat_module.S_ISDIR(cwd_stat.st_mode):
            raise NotADirectoryError(
                errno.ENOTDIR, "starting cwd is not a directory", normalized_cwd
            )

        self._filesystem = filesystem
        self._processes = processes
        self._username_lookup = (
            _production_username_lookup
            if username_lookup is None
            else username_lookup
        )
        if not callable(self._username_lookup):
            raise TypeError("username lookup must be callable")
        self._cwd = normalized_cwd
        self._registry = PresentationTypeRegistry()
        self._types = register_domain_types(self._registry)
        self._history = PresentationHistory(history_max_rows)
        self._contexts = make_domain_drawing_contexts(self._types)
        self._state = SubstrateState()
        self._python_line = PythonLine()
        self._suspended_python: tuple[tuple[tuple[Piece, ...], ...], PythonLine] | None = None
        self._pending_substring_listing: DirectoryListing | ProcessListing | None = (
            None
        )
        self._repl = PythonEvaluator(
            self._history,
            self._contexts.standalone,
            self._types.value,
            self._append_text,
            self._append_error,
            self.COMMAND_NAMES,
        )
        self._translators = TranslatorTable()
        for presentation_type in (
            self._types.file,
            self._types.directory,
            self._types.process,
        ):
            self._translators.register(presentation_type, self._translate_show)

    @classmethod
    def production(cls) -> HeadlessListener:
        filesystem = ProductionFilesystem()
        return cls(os.getcwd(), filesystem, LinuxProcessService())

    @property
    def cwd(self) -> str:
        return self._cwd

    @property
    def current_cwd(self) -> str:
        return self._cwd

    @property
    def filesystem(self) -> FilesystemService:
        return self._filesystem

    @property
    def processes(self) -> ProcessService:
        return self._processes

    @property
    def registry(self) -> PresentationTypeRegistry:
        return self._registry

    @property
    def types(self) -> DomainTypes:
        return self._types

    @property
    def domain_types(self) -> DomainTypes:
        return self._types

    @property
    def history(self) -> PresentationHistory:
        return self._history

    @property
    def drawing_contexts(self) -> DomainDrawingContexts:
        return self._contexts

    @property
    def state(self) -> SubstrateState:
        return self._state

    @property
    def input_text(self) -> str:
        return self._state.input_text

    @property
    def python_pieces(self) -> tuple[Piece, ...]:
        return self._python_line.pieces

    @property
    def python_cursor(self) -> int:
        return self._python_line.cursor

    @property
    def pending_python_pieces(self) -> tuple[tuple[Piece, ...], ...]:
        return self._repl.pending_lines

    @property
    def input_mode(self) -> str:
        if self._state.pending_request is not None or self._pending_substring_listing is not None:
            return "command"
        if self._repl.pending_lines:
            return "python"
        if self._python_line.has_chips:
            return "python"
        stripped = self._state.input_text.lstrip()
        return "command" if stripped.startswith(":") else "python" if stripped else "empty"

    def _sync_python_text(self) -> None:
        self._state.input_text = self._python_line.text

    def insert_python_text(self, text: str) -> None:
        self._python_line.insert_text(text)
        self._sync_python_text()

    def set_python_cursor(self, position: int) -> None:
        if type(position) is not int or not 0 <= position <= len(
            [atom for piece in self._python_line.pieces for atom in (
                piece if isinstance(piece, str) else (piece,)
            )]
        ):
            raise ValueError("cursor is outside the Python line")
        self._python_line.cursor = position

    def capture_python_input(self) -> tuple[tuple[tuple[Piece, ...], ...], PythonLine]:
        return self._repl.pending_lines, self._python_line

    def restore_python_input(
        self, saved: tuple[tuple[tuple[Piece, ...], ...], PythonLine]
    ) -> None:
        self._repl.pending_lines, self._python_line = saved
        self._sync_python_text()

    def python_insertion_reason(self, presentation: Presentation | None) -> str:
        if (
            presentation is None
            or self.pending_request is not None
            or self._pending_substring_listing is not None
            or self.input_mode != "python"
            or logical_presentation_text(self._history, presentation) is None
        ):
            return "unavailable"
        return insertion_site_reason(self._repl.pending_lines, self._python_line)

    def python_left(self) -> None:
        self._python_line.left()

    def python_right(self) -> None:
        self._python_line.right()

    def python_home(self) -> None:
        self._python_line.home()

    def python_end(self) -> None:
        self._python_line.end()

    def python_backspace(self) -> bool:
        changed = self._python_line.backspace()
        self._sync_python_text()
        return changed

    def python_delete(self) -> bool:
        changed = self._python_line.delete()
        self._sync_python_text()
        return changed

    def insert_python_chip(self, presentation: Presentation | None) -> bool:
        if (
            presentation is None
            or self.pending_request is not None
            or self._pending_substring_listing is not None
            or self.input_mode != "python"
        ):
            return False
        label = logical_presentation_text(self._history, presentation)
        if label is None or self.python_insertion_reason(presentation) != "valid":
            return False
        self._python_line.insert_chip(PythonChip(presentation.value, truncate_display(label, 32)))
        self._sync_python_text()
        return True

    @property
    def pending_request(self) -> AcceptRequest | None:
        return self._state.pending_request

    @property
    def chip(self) -> Chip | None:
        return self._state.chip

    @property
    def pending_substring_listing(
        self,
    ) -> DirectoryListing | ProcessListing | None:
        """The exact listing bound to a modal textual substring accept."""

        return self._pending_substring_listing

    @property
    def translators(self) -> TranslatorTable:
        return self._translators

    @property
    def python_namespace(self) -> dict[str, object]:
        return self._repl.namespace

    @property
    def pending_python_source(self) -> str:
        return self._repl.pending_source

    @property
    def python_classes(self) -> ValueClasses:
        return self._repl.classes

    def register_python_class(
        self,
        cls: type,
        printer: Callable[[object], str],
        translators: Iterable[ValueTranslator] = (),
    ) -> None:
        self._repl.classes.register(cls, printer, translators)

    def python_translators_for(
        self, presentation: Presentation
    ) -> tuple[ValueTranslator, ...]:
        if presentation.presentation_type is not self._types.value:
            return ()
        return self._repl.classes.translators_for(presentation.value)

    def invoke_python_translator(
        self, presentation: Presentation, index: int
    ) -> Presentation | None:
        return self._repl.invoke_translator(presentation, index)

    def cancel_python_continuation(self) -> None:
        self._repl.cancel()
        self._python_line = PythonLine()
        self._state.input_text = ""

    @property
    def command_names(self) -> tuple[str, ...]:
        return self.COMMAND_NAMES

    def set_input_text(self, text: str) -> None:
        if not isinstance(text, str):
            raise TypeError("input text must be a string")
        self._state.input_text = text
        self._python_line.set_text(text)

    @staticmethod
    def _split_input(line: str) -> tuple[str, str | None] | None:
        start = 0
        while start < len(line) and line[start].isspace():
            start += 1
        if start == len(line):
            return None
        end = start
        while end < len(line) and not line[end].isspace():
            end += 1
        command = line[start:end]
        argument_start = end
        while argument_start < len(line) and line[argument_start].isspace():
            argument_start += 1
        argument = line[argument_start:] if argument_start < len(line) else None
        return command, argument

    def submit(self, line: str | None = None) -> None:
        if line is not None:
            self.set_input_text(line)
        if self._pending_substring_listing is not None:
            self._finish_substring_accept()
            return
        submitted = self._state.input_text
        if self._repl.pending_lines or self._python_line.has_chips:
            pieces = self._python_line.pieces
            self._state.input_text = ""
            self._python_line = PythonLine()
            self._repl.submit_pieces(pieces)
            return
        if not submitted.strip():
            return
        decision = submitted.lstrip()
        if decision.startswith(":"):
            command_line = decision[1:]
            if command_line.startswith(" "):
                command_line = command_line[1:]
            if not command_line.strip():
                self._state.input_text = ""
                self._python_line = PythonLine()
                return
        elif self._state.pending_request is not None:
            command_line = submitted
        else:
            self._state.input_text = ""
            self._python_line = PythonLine()
            self._repl.submit(submitted)
            return
        parsed = self._split_input(command_line)
        if parsed is None:
            return
        command_name, raw_argument = parsed
        if command_name not in self.COMMAND_NAMES:
            try:
                self._append_error(
                    f"unknown command: {escape_display(command_name)}."
                )
            finally:
                self._clear_attempt()
            return
        if command_name in self.VIEW_COMMAND_NAMES:
            self._submit_view_command(command_name, raw_argument)
            return
        if command_name == "ps" and raw_argument is not None:
            try:
                self._append_error(
                    f"{escape_display(command_name)} does not take an argument."
                )
            finally:
                self._clear_attempt()
            return
        if raw_argument is None:
            if command_name == "ls":
                item = TypedDomainValue(
                    self._types.directory, DirectoryRef(self._cwd)
                )
                self._run_typed(command_name, item)
            elif command_name == "ps":
                self._run_without_argument(command_name)
            else:
                self._begin_accept(command_name)
            return

        parser = {
            "ls": parse_directory,
            "show": parse_show,
            "kill": parse_process,
            "cd": parse_directory,
            "rm": parse_file,
        }[command_name]
        try:
            item = parser(raw_argument, self._cwd, self._types, self._filesystem)
        except DomainParseError as error:
            try:
                self._append_error(str(error))
            finally:
                self._clear_attempt()
            return
        self._run_typed(command_name, item)

    def _acceptable_types(self, command_name: str) -> frozenset[PresentationType]:
        accepted = {
            "cd": (self._types.directory,),
            "rm": (self._types.file,),
            "kill": (self._types.process,),
            "show": (
                self._types.file,
                self._types.directory,
                self._types.process,
            ),
        }
        return frozenset(accepted[command_name])

    def _begin_accept(self, command_name: str) -> None:
        self._state.input_text = command_name
        self._python_line.set_text(command_name)
        self._state.chip = None

        def continue_with(chip: Chip) -> None:
            self._finish_chip(command_name, chip)

        self._state.begin_accept(
            AcceptRequest(
                command_name,
                self._acceptable_types(command_name),
                continue_with,
            )
        )

    def _label_for(self, item: TypedDomainValue) -> str:
        if type(item.value) in {FileRef, DirectoryRef}:
            return escape_display(item.value.path)
        if type(item.value) is ProcessRef:
            return str(item.value.pid)
        raise TypeError("command chips require a path or process reference")

    def _run_typed(self, command_name: str, item: TypedDomainValue) -> None:
        chip = Chip(item.presentation_type, item.value, self._label_for(item))
        self._state.chip = chip
        self._finish_chip(command_name, chip)

    def _run_without_argument(self, command_name: str) -> None:
        try:
            self._execute(command_name, None)
        finally:
            self._clear_attempt()

    def _finish_chip(self, command_name: str, chip: Chip) -> None:
        try:
            self._execute(command_name, chip.value)
        finally:
            self._clear_attempt()

    def _clear_attempt(self) -> None:
        self._state.input_text = ""
        self._python_line = PythonLine()
        self._state.pending_request = None
        self._state.chip = None
        self._pending_substring_listing = None

    def cancel(self) -> None:
        saved = self._suspended_python
        self._suspended_python = None
        self._repl.cancel()
        self._state.input_text = ""
        self._python_line = PythonLine()
        self._state.cancel()
        self._pending_substring_listing = None
        if saved is not None:
            self.restore_python_input(saved)

    def backspace_chip(self) -> bool:
        return self._state.backspace()

    def select_for_input(
        self, presentation: Presentation | None, label: str = ""
    ) -> bool:
        """Route a headless history selection using modal and input precedence."""

        if self._pending_substring_listing is not None or presentation is None:
            return False
        if self._state.pending_request is not None:
            return self._state.select_presentation(presentation, label)
        if self.input_mode == "python":
            return self.insert_python_chip(presentation)
        return self.select(presentation, label)

    def select(self, presentation: Presentation | None, label: str = "") -> bool:
        # The current terminal adapter continues to call this legacy route.
        if self._pending_substring_listing is not None or self._repl.pending_lines:
            return False
        if presentation is None:
            return False
        if self._state.pending_request is not None:
            return self._state.select_presentation(presentation, label)
        if presentation.presentation_type is self._types.value:
            return self._repl.show_detail(presentation)
        translator = self._translators.lookup(presentation.presentation_type)
        if translator is None:
            return False
        translator(presentation.value)
        return True

    def select_presentation(
        self, presentation: Presentation | None, label: str = ""
    ) -> bool:
        return self.select(presentation, label)

    def execute_stored_member(
        self, presentation: Presentation, command_name: str
    ) -> bool:
        """Run a member command using its exact currently retained reference."""

        if (
            self.pending_request is not None
            or self._pending_substring_listing is not None
        ):
            return False
        if presentation not in self._history.presentations:
            return False
        allowed = {
            self._types.file: (FileRef, frozenset({"show", "rm"})),
            self._types.directory: (
                DirectoryRef,
                frozenset({"show", "cd", "ls"}),
            ),
            self._types.process: (ProcessRef, frozenset({"show", "kill"})),
        }
        rule = allowed.get(presentation.presentation_type)
        if (
            rule is None
            or type(presentation.value) is not rule[0]
            or command_name not in rule[1]
        ):
            return False
        self._run_typed(
            command_name,
            TypedDomainValue(presentation.presentation_type, presentation.value),
        )
        return True

    def begin_listing_narrow(self, listing: DirectoryListing | ProcessListing) -> bool:
        """Bind modal substring input to an exact retained listing header."""

        if type(listing) not in {DirectoryListing, ProcessListing}:
            raise TypeError(
                "listing must be exactly DirectoryListing or ProcessListing"
            )
        if (
            self.pending_request is not None
            or self._pending_substring_listing is not None
        ):
            return False
        if listing.header_presentation not in self._history.presentations:
            return False
        if self.input_mode == "python":
            self._suspended_python = self.capture_python_input()
        self._begin_substring_accept(listing)
        if self._suspended_python is not None:
            self._repl.pending_lines = ()
        return True

    def _translate_show(self, value: object) -> None:
        self._command_show(value)

    def _execute(self, command_name: str, value: object | None) -> None:
        if command_name == "ls":
            self._command_ls(value)
        elif command_name == "ps":
            self._command_ps()
        elif command_name == "show":
            self._command_show(value)
        elif command_name == "kill":
            self._command_kill(value)
        elif command_name == "cd":
            self._command_cd(value)
        elif command_name == "rm":
            self._command_rm(value)
        else:
            raise AssertionError(f"unregistered command {command_name!r}")

    def _append_text(self, text: str) -> None:
        self._history.append(
            self._contexts.standalone.present_row(text, self._types.text)
        )

    def _append_error(self, message: str) -> None:
        self._history.append(
            self._contexts.standalone.present_row(message, self._types.error)
        )

    def _append_host_error(
        self, action: str, subject: str | int, error: BaseException
    ) -> None:
        self._append_error(compose_failure_message(action, subject, error))

    def _classify_current(self, path: str) -> TypedDomainValue:
        try:
            followed = self._filesystem.stat(path)
        except OSError as stat_error:
            if stat_error.errno not in _ABSENT_OR_UNRESOLVED:
                raise
            unlinked = self._filesystem.lstat(path)
            if stat_module.S_ISLNK(unlinked.st_mode):
                return TypedDomainValue(self._types.file, FileRef(path))
            raise stat_error
        if stat_module.S_ISDIR(followed.st_mode):
            return TypedDomainValue(self._types.directory, DirectoryRef(path))
        return TypedDomainValue(self._types.file, FileRef(path))

    def _require_directory(self, reference: DirectoryRef) -> os.stat_result:
        result = self._filesystem.stat(reference.path)
        if not stat_module.S_ISDIR(result.st_mode):
            raise NotADirectoryError("Not a directory")
        return result

    def _newest_retained_listing(
        self,
    ) -> DirectoryListing | ProcessListing | None:
        for row in reversed(self._history.rows):
            owner = row.listing_owner
            if type(owner) in {DirectoryListing, ProcessListing}:
                return owner
        return None

    def _listing_is_retained(
        self, listing: DirectoryListing | ProcessListing
    ) -> bool:
        return any(row.listing_owner is listing for row in self._history.rows)

    def _submit_view_command(
        self, command_name: str, raw_argument: str | None
    ) -> None:
        listing = self._newest_retained_listing()
        if listing is None:
            try:
                self._append_error("no listing in history.")
            finally:
                self._clear_attempt()
            return

        if command_name == "narrow" and raw_argument is None:
            self._begin_substring_accept(listing)
            return

        grammar_error: str | None = None
        if command_name == "sort" and (
            raw_argument is None
            or any(character.isspace() for character in raw_argument)
        ):
            grammar_error = "sort requires one key."
        elif command_name == "only" and (
            raw_argument is None
            or any(character.isspace() for character in raw_argument)
        ):
            grammar_error = "only requires one word."
        elif command_name == "widen" and raw_argument is not None:
            grammar_error = "widen does not take an argument."

        if grammar_error is not None:
            try:
                self._append_error(grammar_error)
            finally:
                self._clear_attempt()
            return

        try:
            self.apply_listing_view(listing, command_name, raw_argument)
        finally:
            self._clear_attempt()

    def _begin_substring_accept(
        self, listing: DirectoryListing | ProcessListing
    ) -> None:
        self._clear_attempt()
        self._pending_substring_listing = listing

    def _finish_substring_accept(self) -> bool:
        listing = self._pending_substring_listing
        if listing is None:
            return False
        substring = self._state.input_text
        if not substring:
            return False
        try:
            return self.apply_listing_view(listing, "narrow", substring)
        finally:
            saved = self._suspended_python
            self._suspended_python = None
            self._clear_attempt()
            if saved is not None:
                self.restore_python_input(saved)

    def apply_listing_view(
        self,
        listing: DirectoryListing | ProcessListing,
        operation: str,
        argument: str | None = None,
    ) -> bool:
        """Apply one view operation to an exact retained listing and redisplay it."""

        if type(listing) not in {DirectoryListing, ProcessListing}:
            raise TypeError(
                "listing must be exactly DirectoryListing or ProcessListing"
            )
        if operation not in self.VIEW_COMMAND_NAMES:
            raise ValueError(f"unknown listing view operation {operation!r}")
        if not self._listing_is_retained(listing):
            return False

        if operation == "sort":
            if type(argument) is not str or not argument:
                raise ValueError("sort requires a nonempty string argument")
            try:
                listing.replace_sort_key(argument)
            except ValueError:
                kind = "directory" if type(listing) is DirectoryListing else "process"
                self._append_error(
                    f"cannot sort this {kind} listing by {escape_display(argument)}."
                )
                return False
        elif operation == "narrow":
            if type(argument) is not str or not argument:
                raise ValueError("narrow requires a nonempty string argument")
            listing.replace_substring_filter(argument)
        elif operation == "only":
            if type(argument) is not str or not argument:
                raise ValueError("only requires a nonempty string argument")
            try:
                listing.replace_kind_filter(argument)
            except ValueError:
                kind = "directory" if type(listing) is DirectoryListing else "process"
                self._append_error(
                    "cannot apply only "
                    f"{escape_display(argument)} to this {kind} listing."
                )
                return False
        else:
            if argument is not None:
                raise ValueError("widen does not accept an argument")
            listing.widen()

        self._history.replace_listing_rows(listing, self._listing_rows(listing))
        return True

    def _listing_rows(
        self, listing: DirectoryListing | ProcessListing
    ) -> tuple[HistoryRow, ...]:
        if type(listing) is DirectoryListing:
            return directory_listing_rows(listing)
        if type(listing) is ProcessListing:
            return process_listing_rows(listing)
        raise TypeError("listing rows require an exact listing value")

    def _allocate_directory_presentations(
        self, listing: DirectoryListing
    ) -> None:
        context = self._contexts.listing
        header_fragment = context.present(listing, self._types.directory_listing)
        header = context.presentation(header_fragment.presentation_id)
        presentations: list[Presentation] = []
        for member in listing.members:
            presentation_type = (
                self._types.directory
                if type(member.reference) is DirectoryRef
                else self._types.file
            )
            fragment = context.present(member.reference, presentation_type)
            presentations.append(context.presentation(fragment.presentation_id))
        listing.bind_presentations(header, presentations, self._types)

    def _allocate_process_presentations(
        self, listing: ProcessListing
    ) -> None:
        context = self._contexts.listing
        header_fragment = context.present(listing, self._types.process_listing)
        header = context.presentation(header_fragment.presentation_id)
        presentations: list[Presentation] = []
        for member in listing.members:
            fragment = context.present(member.reference, self._types.process)
            presentations.append(context.presentation(fragment.presentation_id))
        listing.bind_presentations(header, presentations, self._types)

    def _command_ls(self, value: object | None) -> None:
        if type(value) is not DirectoryRef:
            raise TypeError("ls requires DirectoryRef")
        try:
            self._require_directory(value)
            captured_members: list[DirectoryListingMember] = []
            for entry in self._filesystem.iter_directory(value.path):
                if entry.name in {".", ".."}:
                    continue
                child_path = self._filesystem.abspath(entry.path)
                try:
                    metadata = self._filesystem.stat(child_path)
                except OSError as stat_error:
                    if stat_error.errno not in _ABSENT_OR_UNRESOLVED:
                        raise
                    unlinked = self._filesystem.lstat(child_path)
                    if not stat_module.S_ISLNK(unlinked.st_mode):
                        raise stat_error
                    reference: FileRef | DirectoryRef = FileRef(child_path)
                    size: int | None = int(unlinked.st_size)
                    metadata = unlinked
                else:
                    if stat_module.S_ISDIR(metadata.st_mode):
                        reference = DirectoryRef(child_path)
                        size = None
                    else:
                        reference = FileRef(child_path)
                        size = int(metadata.st_size)
                captured_members.append(
                    DirectoryListingMember(
                        reference,
                        escape_display(entry.name),
                        size,
                        int(round(metadata.st_mtime)),
                    )
                )
        except OSError as error:
            self._append_host_error("cannot list", value.path, error)
            return

        listing = DirectoryListing(value, captured_members)
        self._allocate_directory_presentations(listing)
        for row in self._listing_rows(listing):
            self._history.append(row)

    def _command_ps(self) -> None:
        try:
            own_uid = self._processes.own_uid
            captured_members: list[ProcessListingMember] = []
            for record in self._processes.list_for_uid(own_uid):
                if record.real_uid != own_uid:
                    continue
                try:
                    username = self._username_lookup(record.real_uid)
                except (KeyError, OSError):
                    username = None
                displayed_user = (
                    username if isinstance(username, str) else str(record.real_uid)
                )
                captured_members.append(
                    ProcessListingMember(
                        ProcessRef(record.pid),
                        record.state,
                        record.real_uid,
                        escape_display(displayed_user),
                        escape_display(record.command),
                    )
                )
        except OSError as error:
            message = f"cannot list processes: {escape_display(str(error))}"
            self._append_error(message if message.endswith(".") else f"{message}.")
            return

        listing = ProcessListing(captured_members)
        self._allocate_process_presentations(listing)
        for row in self._listing_rows(listing):
            self._history.append(row)

    def _command_show(self, value: object | None) -> None:
        if type(value) is ProcessRef:
            try:
                record = self._processes.inspect(value.pid)
            except OSError as error:
                self._append_host_error(
                    "cannot show process", value.pid, error
                )
                return
            self._append_text(
                format_process_detail(value, record.command, record.state)
            )
            return
        if type(value) not in {FileRef, DirectoryRef}:
            raise TypeError("show requires a path or process reference")
        self._show_path(value.path)

    def _show_path(self, path: str) -> None:
        try:
            unlinked = self._filesystem.lstat(path)
            is_link = stat_module.S_ISLNK(unlinked.st_mode)
            link_target = self._filesystem.readlink(path) if is_link else None
            try:
                followed = self._filesystem.stat(path)
            except OSError as error:
                if is_link and error.errno in _ABSENT_OR_UNRESOLVED:
                    detail = format_path_detail(
                        FileRef(path),
                        size=unlinked.st_size,
                        mtime=unlinked.st_mtime,
                        symlink_target=link_target,
                        broken_symlink=True,
                    )
                    self._append_text(detail)
                    return
                raise
            if stat_module.S_ISDIR(followed.st_mode):
                detail = format_path_detail(
                    DirectoryRef(path), symlink_target=link_target
                )
            else:
                detail = format_path_detail(
                    FileRef(path),
                    size=followed.st_size,
                    mtime=followed.st_mtime,
                    symlink_target=link_target,
                )
        except OSError as error:
            self._append_host_error("cannot show", path, error)
            return
        self._append_text(detail)

    def _command_cd(self, value: object | None) -> None:
        if type(value) is not DirectoryRef:
            raise TypeError("cd requires DirectoryRef")
        try:
            self._require_directory(value)
        except OSError as error:
            self._append_host_error(
                "cannot change directory to", value.path, error
            )
            return
        self._cwd = value.path

    def _command_rm(self, value: object | None) -> None:
        if type(value) is not FileRef:
            raise TypeError("rm requires FileRef")
        path = value.path
        try:
            unlinked = self._filesystem.lstat(path)
            is_link = stat_module.S_ISLNK(unlinked.st_mode)
            try:
                followed = self._filesystem.stat(path)
            except OSError as error:
                if not (is_link and error.errno in _ABSENT_OR_UNRESOLVED):
                    raise
                followed = None
            if followed is not None and stat_module.S_ISDIR(followed.st_mode):
                self._append_error(
                    f"refusing to remove directory {escape_display(path)}."
                )
                return
            self._filesystem.unlink(path)
        except OSError as error:
            self._append_host_error("cannot remove", path, error)
            return
        self._append_text(format_removed_file(value))

    def _command_kill(self, value: object | None) -> None:
        if type(value) is not ProcessRef:
            raise TypeError("kill requires ProcessRef")
        pid = value.pid
        if pid < 2 or pid == self._processes.own_pid:
            self._append_error(f"refusing to signal process {pid}.")
            return
        try:
            self._processes.inspect(pid)
            self._processes.send_sigterm(pid)
        except OSError as error:
            self._append_host_error("cannot signal process", pid, error)
            return
        self._append_text(format_signal_result(value))


def make_production_listener() -> HeadlessListener:
    """Compose the production headless listener without starting a UI."""

    return HeadlessListener.production()


__all__ = [
    "FilesystemEntry",
    "FilesystemService",
    "HeadlessListener",
    "InspectedProcess",
    "LinuxProcessService",
    "ProcessInspectionError",
    "ProcessService",
    "ProductionFilesystem",
    "RootedFilesystem",
    "make_production_listener",
    "process_state_word",
]
