"""Domain values, parsers, drawers, and product wording for ``pbui``.

Path classification is performed through a small read-only seam.  Retained
listing values cache only already-captured scalar data; their view operations,
drawing, and formatting remain pure.
"""

from __future__ import annotations

import errno
import os
import stat as stat_module
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from pbui.substrate import PresentationType, PresentationTypeRegistry
from pbui.text import DrawingContext, HistoryRow


@dataclass(frozen=True, slots=True)
class DomainTypes:
    """The seven exact presentation-type entries owned by an application."""

    file: PresentationType
    directory: PresentationType
    process: PresentationType
    text: PresentationType
    error: PresentationType
    directory_listing: PresentationType
    process_listing: PresentationType


def register_domain_types(registry: PresentationTypeRegistry) -> DomainTypes:
    """Register and return the listener's domain types in their stable order."""

    if not isinstance(registry, PresentationTypeRegistry):
        raise TypeError("registry must be a PresentationTypeRegistry")
    return DomainTypes(
        file=registry.register("File"),
        directory=registry.register("Directory"),
        process=registry.register("Process"),
        text=registry.register("Text"),
        error=registry.register("Error"),
        directory_listing=registry.register("DirectoryListing"),
        process_listing=registry.register("ProcessListing"),
    )


def _validate_absolute_path(path: object) -> None:
    if not isinstance(path, str):
        raise TypeError("path must be a string")
    if not os.path.isabs(path):
        raise ValueError("path must be absolute")


@dataclass(frozen=True, slots=True)
class FileRef:
    path: str

    def __post_init__(self) -> None:
        _validate_absolute_path(self.path)


@dataclass(frozen=True, slots=True)
class DirectoryRef:
    path: str

    def __post_init__(self) -> None:
        _validate_absolute_path(self.path)


@dataclass(frozen=True, slots=True)
class ProcessRef:
    pid: int

    def __post_init__(self) -> None:
        if type(self.pid) is not int:
            raise TypeError("pid must be an exact integer")


DomainReference = FileRef | DirectoryRef | ProcessRef
PathReference = FileRef | DirectoryRef


class ListingViewError(ValueError):
    """A listing view is not valid for its listing kind."""


@dataclass(frozen=True, slots=True)
class DirectoryListingMember:
    """One directory member captured for later pure redisplay."""

    reference: PathReference
    displayed_basename: str
    size: int | None
    mtime: int

    def __post_init__(self) -> None:
        if type(self.reference) not in {FileRef, DirectoryRef}:
            raise TypeError("reference must be exactly FileRef or DirectoryRef")
        if type(self.displayed_basename) is not str:
            raise TypeError("displayed basename must be a string")
        if type(self.reference) is FileRef:
            if type(self.size) is not int:
                raise TypeError("file size must be an exact integer")
            if self.size < 0:
                raise ValueError("file size must be nonnegative")
        elif self.size is not None:
            raise TypeError("directory size must be None")
        if type(self.mtime) is not int:
            raise TypeError("mtime must be an exact integer")


PROCESS_LISTING_STATES = frozenset(
    {
        "running",
        "sleeping",
        "disk-sleep",
        "stopped",
        "tracing",
        "zombie",
        "dead",
        "idle",
        "unknown",
    }
)


@dataclass(frozen=True, slots=True)
class ProcessListingMember:
    """One process member captured for later pure redisplay."""

    reference: ProcessRef
    state: str
    uid: int
    displayed_user: str
    command: str

    def __post_init__(self) -> None:
        if type(self.reference) is not ProcessRef:
            raise TypeError("reference must be exactly ProcessRef")
        if type(self.state) is not str:
            raise TypeError("state must be a string")
        if self.state not in PROCESS_LISTING_STATES:
            raise ValueError("state is not a canonical process state")
        if type(self.uid) is not int:
            raise TypeError("uid must be an exact integer")
        if self.uid < 0:
            raise ValueError("uid must be nonnegative")
        if type(self.displayed_user) is not str:
            raise TypeError("displayed user must be a string")
        if type(self.command) is not str:
            raise TypeError("command must be a string")


@dataclass(frozen=True, slots=True)
class ListingView:
    """The three independent choices that determine a listing's visible view."""

    sort_key: str
    substring_filter: str | None = None
    kind_filter: str | None = None

    def __post_init__(self) -> None:
        if type(self.sort_key) is not str:
            raise TypeError("sort key must be a string")
        if self.substring_filter is not None:
            if type(self.substring_filter) is not str:
                raise TypeError("substring filter must be a string or None")
            if not self.substring_filter:
                raise ListingViewError("substring filter must not be empty")
        if self.kind_filter is not None and type(self.kind_filter) is not str:
            raise TypeError("kind filter must be a string or None")


DIRECTORY_LISTING_SORT_KEYS = frozenset({"name", "size", "mtime"})
DIRECTORY_LISTING_KINDS = frozenset({"files", "directories"})
PROCESS_LISTING_SORT_KEYS = frozenset({"pid", "state", "command"})


def _validate_view(
    view: object,
    *,
    sort_keys: frozenset[str],
    kind_filters: frozenset[str],
) -> ListingView:
    if type(view) is not ListingView:
        raise TypeError("view must be exactly ListingView")
    if view.sort_key not in sort_keys:
        raise ListingViewError(f"invalid listing sort key: {view.sort_key}")
    if view.kind_filter is not None and view.kind_filter not in kind_filters:
        raise ListingViewError(f"invalid listing kind filter: {view.kind_filter}")
    return view


class DirectoryListing:
    """One stable captured directory listing with replaceable pure view state."""

    __slots__ = ("_directory", "_members", "_view")

    def __init__(
        self,
        directory: DirectoryRef,
        members: Iterable[DirectoryListingMember],
        view: ListingView | None = None,
    ) -> None:
        if type(directory) is not DirectoryRef:
            raise TypeError("directory must be exactly DirectoryRef")
        captured = tuple(members)
        if any(type(member) is not DirectoryListingMember for member in captured):
            raise TypeError("directory listing members must have the exact member type")
        initial_view = ListingView("name") if view is None else view
        self._directory = directory
        self._members = captured
        self._view = self._validated_view(initial_view)

    @staticmethod
    def _validated_view(view: object) -> ListingView:
        return _validate_view(
            view,
            sort_keys=DIRECTORY_LISTING_SORT_KEYS,
            kind_filters=DIRECTORY_LISTING_KINDS,
        )

    @property
    def directory(self) -> DirectoryRef:
        return self._directory

    @property
    def members(self) -> tuple[DirectoryListingMember, ...]:
        return self._members

    @property
    def view(self) -> ListingView:
        return self._view

    def replace_sort_key(self, sort_key: str) -> None:
        candidate = ListingView(
            sort_key, self._view.substring_filter, self._view.kind_filter
        )
        self._view = self._validated_view(candidate)

    def replace_substring_filter(self, substring_filter: str | None) -> None:
        candidate = ListingView(
            self._view.sort_key, substring_filter, self._view.kind_filter
        )
        self._view = self._validated_view(candidate)

    def replace_kind_filter(self, kind_filter: str | None) -> None:
        candidate = ListingView(
            self._view.sort_key, self._view.substring_filter, kind_filter
        )
        self._view = self._validated_view(candidate)

    def widen(self) -> None:
        self._view = ListingView(self._view.sort_key)

    def visible_members(self) -> tuple[DirectoryListingMember, ...]:
        members: Iterable[DirectoryListingMember] = self._members
        if self._view.substring_filter is not None:
            substring = self._view.substring_filter
            members = (
                member
                for member in members
                if substring in member.displayed_basename
            )
        if self._view.kind_filter == "files":
            members = (
                member for member in members if type(member.reference) is FileRef
            )
        elif self._view.kind_filter == "directories":
            members = (
                member
                for member in members
                if type(member.reference) is DirectoryRef
            )

        if self._view.sort_key == "name":
            key = lambda member: (member.displayed_basename,)
        elif self._view.sort_key == "size":
            key = lambda member: (
                type(member.reference) is DirectoryRef,
                -member.size if member.size is not None else 0,
                member.displayed_basename,
            )
        else:
            key = lambda member: (-member.mtime, member.displayed_basename)
        return tuple(sorted(members, key=key))


class ProcessListing:
    """One stable captured process listing with replaceable pure view state."""

    __slots__ = ("_members", "_view")

    def __init__(
        self,
        members: Iterable[ProcessListingMember],
        view: ListingView | None = None,
    ) -> None:
        captured = tuple(members)
        if any(type(member) is not ProcessListingMember for member in captured):
            raise TypeError("process listing members must have the exact member type")
        initial_view = ListingView("pid") if view is None else view
        self._members = captured
        self._view = self._validated_view(initial_view)

    @staticmethod
    def _validated_view(view: object) -> ListingView:
        return _validate_view(
            view,
            sort_keys=PROCESS_LISTING_SORT_KEYS,
            kind_filters=PROCESS_LISTING_STATES,
        )

    @property
    def members(self) -> tuple[ProcessListingMember, ...]:
        return self._members

    @property
    def view(self) -> ListingView:
        return self._view

    def replace_sort_key(self, sort_key: str) -> None:
        candidate = ListingView(
            sort_key, self._view.substring_filter, self._view.kind_filter
        )
        self._view = self._validated_view(candidate)

    def replace_substring_filter(self, substring_filter: str | None) -> None:
        candidate = ListingView(
            self._view.sort_key, substring_filter, self._view.kind_filter
        )
        self._view = self._validated_view(candidate)

    def replace_kind_filter(self, kind_filter: str | None) -> None:
        candidate = ListingView(
            self._view.sort_key, self._view.substring_filter, kind_filter
        )
        self._view = self._validated_view(candidate)

    def widen(self) -> None:
        self._view = ListingView(self._view.sort_key)

    def visible_members(self) -> tuple[ProcessListingMember, ...]:
        members: Iterable[ProcessListingMember] = self._members
        if self._view.substring_filter is not None:
            substring = self._view.substring_filter
            members = (
                member for member in members if substring in member.command
            )
        if self._view.kind_filter is not None:
            state = self._view.kind_filter
            members = (member for member in members if member.state == state)

        if self._view.sort_key == "pid":
            key = lambda member: (member.reference.pid,)
        elif self._view.sort_key == "state":
            key = lambda member: (member.state, member.reference.pid)
        else:
            key = lambda member: (member.command, member.reference.pid)
        return tuple(sorted(members, key=key))


ListingValue = DirectoryListing | ProcessListing
DomainValue = DomainReference | ListingValue | str


@dataclass(frozen=True, slots=True)
class TypedDomainValue:
    """A stored value paired with its explicit registry entry."""

    presentation_type: PresentationType
    value: DomainValue

    @property
    def type(self) -> PresentationType:
        return self.presentation_type


class DomainParseError(ValueError):
    """A typed-argument or path-classification failure safe to report."""


class ReadOnlyPathAccess(Protocol):
    """The host operations needed for lexical paths and classification."""

    def abspath(self, path: str) -> str: ...

    def stat(self, path: str) -> os.stat_result: ...

    def lstat(self, path: str) -> os.stat_result: ...


@dataclass(frozen=True, slots=True)
class OSReadOnlyPathAccess:
    """Production read-only path access backed by :mod:`os`."""

    def abspath(self, path: str) -> str:
        return os.path.abspath(path)

    def stat(self, path: str) -> os.stat_result:
        return os.stat(path)

    def lstat(self, path: str) -> os.stat_result:
        return os.lstat(path)


def normalize_path(raw_path: str, cwd: str, access: ReadOnlyPathAccess) -> str:
    """Capture an absolute lexical path without resolving the final symlink."""

    if not isinstance(raw_path, str):
        raise DomainParseError("path input must be a string")
    if not isinstance(cwd, str) or not os.path.isabs(cwd):
        raise DomainParseError("current directory must be an absolute path")
    candidate = raw_path if os.path.isabs(raw_path) else os.path.join(cwd, raw_path)
    try:
        normalized = access.abspath(candidate)
    except (OSError, TypeError, ValueError) as error:
        raise DomainParseError(
            f"cannot normalize {escape_display(raw_path)}: "
            f"{escape_display(str(error))}"
        ) from error
    if not isinstance(normalized, str) or not os.path.isabs(normalized):
        raise DomainParseError("path access returned a non-absolute path")
    return normalized


_ABSENT_OR_UNRESOLVED = frozenset({errno.ENOENT, errno.ENOTDIR, errno.ELOOP})


def _access_failure(action: str, path: str, error: OSError) -> DomainParseError:
    return DomainParseError(
        f"{action} {escape_display(path)}: {escape_display(str(error))}"
    )


def _probe_path(
    path: str,
    types: DomainTypes,
    access: ReadOnlyPathAccess,
) -> TypedDomainValue | None:
    """Classify an extant entry, returning ``None`` only for true absence."""

    _validate_absolute_path(path)
    try:
        followed = access.stat(path)
    except OSError as stat_error:
        try:
            unlinked = access.lstat(path)
        except OSError as lstat_error:
            if (
                stat_error.errno in _ABSENT_OR_UNRESOLVED
                and lstat_error.errno in _ABSENT_OR_UNRESOLVED
            ):
                return None
            raise _access_failure("cannot inspect", path, lstat_error) from lstat_error
        if stat_module.S_ISLNK(unlinked.st_mode):
            return TypedDomainValue(types.file, FileRef(path))
        raise _access_failure("cannot inspect", path, stat_error) from stat_error
    except (TypeError, ValueError) as error:
        raise DomainParseError(
            f"cannot inspect {escape_display(path)}: {escape_display(str(error))}"
        ) from error

    if stat_module.S_ISDIR(followed.st_mode):
        return TypedDomainValue(types.directory, DirectoryRef(path))
    return TypedDomainValue(types.file, FileRef(path))


def classify_path(
    path: str,
    types: DomainTypes,
    access: ReadOnlyPathAccess,
    *,
    permit_absent: bool = False,
) -> TypedDomainValue:
    """Classify one already-normalized path using followed ``stat``."""

    try:
        result = _probe_path(path, types, access)
    except (TypeError, ValueError) as error:
        if isinstance(error, DomainParseError):
            raise
        raise DomainParseError(str(error)) from error
    if result is not None:
        return result
    if permit_absent:
        return TypedDomainValue(types.file, FileRef(path))
    raise DomainParseError(f"path does not exist: {escape_display(path)}")


def parse_directory(
    raw_argument: str,
    cwd: str,
    types: DomainTypes,
    access: ReadOnlyPathAccess,
) -> TypedDomainValue:
    path = normalize_path(raw_argument, cwd, access)
    classified = classify_path(path, types, access)
    if classified.presentation_type is not types.directory:
        raise DomainParseError(f"not a directory: {escape_display(path)}")
    return classified


def parse_file(
    raw_argument: str,
    cwd: str,
    types: DomainTypes,
    access: ReadOnlyPathAccess,
) -> TypedDomainValue:
    path = normalize_path(raw_argument, cwd, access)
    classified = classify_path(path, types, access, permit_absent=True)
    if classified.presentation_type is types.directory:
        raise DomainParseError(f"is a directory: {escape_display(path)}")
    return classified


def _is_process_argument(raw_argument: object) -> bool:
    if not isinstance(raw_argument, str) or not raw_argument:
        return False
    digits = raw_argument[1:] if raw_argument[0] in "+-" else raw_argument
    return bool(digits) and all("0" <= character <= "9" for character in digits)


def parse_process(
    raw_argument: str,
    cwd: str,
    types: DomainTypes,
    access: ReadOnlyPathAccess,
) -> TypedDomainValue:
    del cwd, access
    if not _is_process_argument(raw_argument):
        shown = escape_display(raw_argument) if isinstance(raw_argument, str) else repr(raw_argument)
        raise DomainParseError(f"invalid process id: {shown}")
    return TypedDomainValue(types.process, ProcessRef(int(raw_argument, 10)))


def parse_show(
    raw_argument: str,
    cwd: str,
    types: DomainTypes,
    access: ReadOnlyPathAccess,
) -> TypedDomainValue:
    path = normalize_path(raw_argument, cwd, access)
    classified = _probe_path(path, types, access)
    if classified is not None:
        return classified
    if _is_process_argument(raw_argument):
        return TypedDomainValue(types.process, ProcessRef(int(raw_argument, 10)))
    return TypedDomainValue(types.file, FileRef(path))


def escape_display(value: str) -> str:
    """Escape unsafe code points while preserving printable Unicode literally."""

    if not isinstance(value, str):
        raise TypeError("display input must be a string")
    escaped: list[str] = []
    for character in value:
        codepoint = ord(character)
        if character == "\\":
            escaped.append("\\\\")
        elif character == "\n":
            escaped.append("\\n")
        elif character == "\r":
            escaped.append("\\r")
        elif character == "\t":
            escaped.append("\\t")
        elif character.isprintable():
            escaped.append(character)
        elif codepoint <= 0xFF:
            escaped.append(f"\\x{codepoint:02x}")
        elif codepoint <= 0xFFFF:
            escaped.append(f"\\u{codepoint:04x}")
        else:
            escaped.append(f"\\U{codepoint:08x}")
    return "".join(escaped)


def _expect_exact(value: Any, expected: type[Any], label: str) -> None:
    if type(value) is not expected:
        raise TypeError(f"{label} drawer requires {expected.__name__}")


def register_domain_drawers(
    context: DrawingContext,
    types: DomainTypes,
    *,
    path_mode: str,
) -> DrawingContext:
    """Install all five drawers into ``context`` for one explicit path mode."""

    if path_mode not in {"standalone", "listing"}:
        raise ValueError("path mode must be 'standalone' or 'listing'")

    def path_label(path: str) -> str:
        label = path if path_mode == "standalone" else os.path.basename(path)
        return escape_display(label)

    def draw_file(value: Any, _context: DrawingContext) -> str:
        _expect_exact(value, FileRef, "File")
        return path_label(value.path)

    def draw_directory(value: Any, _context: DrawingContext) -> str:
        _expect_exact(value, DirectoryRef, "Directory")
        return path_label(value.path)

    def draw_process(value: Any, _context: DrawingContext) -> str:
        _expect_exact(value, ProcessRef, "Process")
        return str(value.pid)

    def draw_text(value: Any, _context: DrawingContext) -> str:
        _expect_exact(value, str, "Text")
        return value

    def draw_error(value: Any, _context: DrawingContext) -> str:
        _expect_exact(value, str, "Error")
        return f"Error: {value}"

    context.register_drawer(types.file, draw_file)
    context.register_drawer(types.directory, draw_directory)
    context.register_drawer(types.process, draw_process)
    context.register_drawer(types.text, draw_text)
    context.register_drawer(types.error, draw_error)
    return context


@dataclass(frozen=True, slots=True)
class DomainDrawingContexts:
    standalone: DrawingContext
    listing: DrawingContext


def make_domain_drawing_contexts(types: DomainTypes) -> DomainDrawingContexts:
    return DomainDrawingContexts(
        standalone=register_domain_drawers(
            DrawingContext(), types, path_mode="standalone"
        ),
        listing=register_domain_drawers(DrawingContext(), types, path_mode="listing"),
    )


def path_sort_key(reference: PathReference) -> str:
    if type(reference) not in {FileRef, DirectoryRef}:
        raise TypeError("path sorting requires a FileRef or DirectoryRef")
    return escape_display(os.path.basename(reference.path))


def sort_path_references(references: Iterable[PathReference]) -> tuple[PathReference, ...]:
    return tuple(sorted(references, key=path_sort_key))


def path_listing_row(
    item: TypedDomainValue,
    types: DomainTypes,
    context: DrawingContext,
) -> HistoryRow:
    if item.presentation_type is types.file and type(item.value) is FileRef:
        prefix = "file       "
    elif (
        item.presentation_type is types.directory
        and type(item.value) is DirectoryRef
    ):
        prefix = "directory  "
    else:
        raise TypeError("path row requires an exactly typed FileRef or DirectoryRef")
    return context.row(prefix, context.present(item.value, item.presentation_type))


def process_listing_row(
    process: ProcessRef,
    state: str,
    command: str,
    types: DomainTypes,
    context: DrawingContext,
) -> HistoryRow:
    _expect_exact(process, ProcessRef, "Process")
    if not isinstance(state, str) or not isinstance(command, str):
        raise TypeError("process state and command must be strings")
    return context.row(
        context.present(process, types.process),
        "  ",
        state,
        "  ",
        escape_display(command),
    )


def format_utc_timestamp(timestamp: int | float) -> str:
    if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
        raise TypeError("timestamp must be a number")
    try:
        instant = datetime.fromtimestamp(timestamp, UTC)
    except (OverflowError, OSError, ValueError) as error:
        raise ValueError("timestamp is outside the supported range") from error
    return instant.isoformat(timespec="seconds").replace("+00:00", "Z")


def format_file_detail(
    reference: FileRef,
    size: int,
    mtime: int | float,
    *,
    symlink_target: str | None = None,
    broken_symlink: bool = False,
) -> str:
    _expect_exact(reference, FileRef, "File detail")
    if isinstance(size, bool) or not isinstance(size, int):
        raise TypeError("file size must be an integer")
    if not isinstance(symlink_target, (str, type(None))):
        raise TypeError("symlink target must be a string or None")
    if broken_symlink and symlink_target is None:
        raise ValueError("broken symlink detail requires its raw link target")
    kind = "file (broken symlink)" if broken_symlink else "file"
    result = f"path: {escape_display(reference.path)} | type: {kind}"
    if symlink_target is not None:
        result += f" | symlink -> {escape_display(symlink_target)}"
    return (
        f"{result} | size: {size} bytes | mtime: "
        f"{format_utc_timestamp(mtime)}"
    )


def format_directory_detail(
    reference: DirectoryRef,
    *,
    symlink_target: str | None = None,
) -> str:
    _expect_exact(reference, DirectoryRef, "Directory detail")
    if not isinstance(symlink_target, (str, type(None))):
        raise TypeError("symlink target must be a string or None")
    result = f"path: {escape_display(reference.path)} | type: directory"
    if symlink_target is not None:
        result += f" | symlink -> {escape_display(symlink_target)}"
    return result


def format_path_detail(
    reference: PathReference,
    *,
    size: int | None = None,
    mtime: int | float | None = None,
    symlink_target: str | None = None,
    broken_symlink: bool = False,
) -> str:
    """Format either exact path-reference shape without reading the host."""

    if type(reference) is DirectoryRef:
        if size is not None or mtime is not None or broken_symlink:
            raise ValueError("directory detail has no size, mtime, or broken-link flag")
        return format_directory_detail(reference, symlink_target=symlink_target)
    if type(reference) is FileRef:
        if size is None or mtime is None:
            raise ValueError("file detail requires size and mtime")
        return format_file_detail(
            reference,
            size,
            mtime,
            symlink_target=symlink_target,
            broken_symlink=broken_symlink,
        )
    raise TypeError("path detail requires a FileRef or DirectoryRef")


def format_process_detail(process: ProcessRef, command: str, state: str) -> str:
    _expect_exact(process, ProcessRef, "Process detail")
    if not isinstance(command, str) or not isinstance(state, str):
        raise TypeError("process command and state must be strings")
    return f"pid: {process.pid} | command: {escape_display(command)} | state: {state}"


def format_removed_file(reference: FileRef) -> str:
    _expect_exact(reference, FileRef, "Removed file")
    return f"Removed file: {escape_display(reference.path)}"


def format_signal_result(process: ProcessRef) -> str:
    _expect_exact(process, ProcessRef, "Signal result")
    return f"Sent SIGTERM to process {process.pid}."


def format_empty_directory(reference: DirectoryRef) -> str:
    _expect_exact(reference, DirectoryRef, "Empty directory")
    return f"Directory is empty: {escape_display(reference.path)}"


def compose_failure_message(
    action_phrase: str,
    raw_subject: str | int,
    raw_os_error: str | BaseException,
) -> str:
    """Compose an unprefixed, once-escaped failure for the ``Error`` drawer."""

    if not isinstance(action_phrase, str):
        raise TypeError("failure action phrase must be a string")
    if isinstance(raw_subject, bool) or not isinstance(raw_subject, (str, int)):
        raise TypeError("failure subject must be text or an integer")
    subject = escape_display(str(raw_subject))
    error = escape_display(str(raw_os_error))
    message = f"{action_phrase} {subject}: {error}"
    return message if message.endswith(".") else f"{message}."


__all__ = [
    "DIRECTORY_LISTING_KINDS",
    "DIRECTORY_LISTING_SORT_KEYS",
    "DirectoryListing",
    "DirectoryListingMember",
    "DirectoryRef",
    "DomainValue",
    "DomainDrawingContexts",
    "DomainParseError",
    "DomainTypes",
    "FileRef",
    "ListingValue",
    "ListingView",
    "ListingViewError",
    "OSReadOnlyPathAccess",
    "PathReference",
    "PROCESS_LISTING_SORT_KEYS",
    "PROCESS_LISTING_STATES",
    "ProcessListing",
    "ProcessListingMember",
    "ProcessRef",
    "ReadOnlyPathAccess",
    "TypedDomainValue",
    "classify_path",
    "compose_failure_message",
    "escape_display",
    "format_directory_detail",
    "format_empty_directory",
    "format_file_detail",
    "format_path_detail",
    "format_process_detail",
    "format_removed_file",
    "format_signal_result",
    "format_utc_timestamp",
    "make_domain_drawing_contexts",
    "normalize_path",
    "parse_directory",
    "parse_file",
    "parse_process",
    "parse_show",
    "path_listing_row",
    "path_sort_key",
    "process_listing_row",
    "register_domain_drawers",
    "register_domain_types",
    "sort_path_references",
]
