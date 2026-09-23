from __future__ import annotations

import os
import signal
import stat
import subprocess
import sys
from dataclasses import dataclass, field

import pytest

from pbui.commands import (
    FilesystemEntry,
    HeadlessListener,
    InspectedProcess,
    LinuxProcessService,
    ProcessInspectionError,
    RootedFilesystem,
    process_state_word,
)
from pbui.domain import (
    DirectoryListing,
    DirectoryRef,
    FileRef,
    ProcessListing,
    ProcessRef,
    escape_display,
    format_utc_timestamp,
)
from pbui.substrate import Chip
from pbui.text import layout


@dataclass
class FixedProcesses:
    own_uid: int = 1000
    own_pid: int = 700
    records: dict[int, InspectedProcess] = field(default_factory=dict)
    sent: list[tuple[int, signal.Signals]] = field(default_factory=list)
    signal_failures: set[int] = field(default_factory=set)
    list_uids: list[int] = field(default_factory=list)

    def list_for_uid(self, uid):
        self.list_uids.append(uid)
        return tuple(self.records.values())

    def inspect(self, pid):
        try:
            return self.records[pid]
        except KeyError:
            raise ProcessLookupError("process is gone") from None

    def send_sigterm(self, pid):
        if pid in self.signal_failures:
            raise PermissionError("signal denied")
        self.sent.append((pid, signal.SIGTERM))


def make_listener(tmp_path, processes=None, **kwargs):
    service = processes if processes is not None else FixedProcesses()
    username_lookup = kwargs.pop("username_lookup", lambda uid: str(uid))
    return HeadlessListener(
        str(tmp_path),
        RootedFilesystem(tmp_path),
        service,
        username_lookup=username_lookup,
        **kwargs,
    )


def history_text(listener):
    return tuple(row.text for row in layout(listener.history, 10_000).rows)


PROCESS_HEADER = f"{'pid':>10}  {'state':<10}  {'user':<16}  {'command':<48}"


def process_table_row(pid, state, user, command):
    return f"{pid:>10}  {state:<10}  {user:<16}  {command:<48}"


def directory_table_text(listing):
    visible = listing.visible_members()
    name_width = max(4, *(len(member.displayed_basename) for member in visible))
    size_width = max(
        12,
        *(
            len(str(member.size))
            for member in visible
            if member.size is not None
        ),
    )
    result = [f"{'name':<{name_width}}  {'size':>{size_width}}  {'modified':<20}"]
    for member in visible:
        size = "" if member.size is None else str(member.size)
        result.append(
            f"{member.displayed_basename:<{name_width}}  "
            f"{size:>{size_width}}  {format_utc_timestamp(member.mtime)}"
        )
    return tuple(result)


def one_presentation(listener, presentation_type, value=None):
    matches = [
        presentation
        for presentation in listener.history.presentations
        if presentation.presentation_type is presentation_type
        and (value is None or presentation.value == value)
    ]
    assert len(matches) == 1
    return matches[0]


def listing_owners(listener):
    owners = []
    for row in listener.history.rows:
        owner = row.listing_owner
        if owner is not None and not any(owner is retained for retained in owners):
            owners.append(owner)
    return tuple(owners)


def write_process(proc_root, pid, *, name="worker", uid=1000, state="S", cmdline=b""):
    process_dir = proc_root / str(pid)
    process_dir.mkdir()
    (process_dir / "status").write_text(
        f"Name:\t{name}\nState:\t{state} (word)\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\n"
    )
    (process_dir / "cmdline").write_bytes(cmdline)


def test_composition_is_coherent_bounded_and_never_changes_process_cwd(tmp_path):
    process_cwd = os.getcwd()
    child = tmp_path / "child"
    child.mkdir()
    processes = FixedProcesses()
    listener = make_listener(tmp_path, processes, history_max_rows=2)

    assert listener.cwd == str(tmp_path)
    assert listener.current_cwd == str(tmp_path)
    assert [entry.name for entry in listener.registry] == [
        "File",
        "Directory",
        "Process",
        "Text",
        "Error",
        "DirectoryListing",
        "ProcessListing",
    ]
    assert listener.command_names == (
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
    assert listener.filesystem.allowed_root == str(tmp_path)
    assert listener.processes is processes
    assert listener.translators.lookup(listener.types.file) is not None
    assert listener.translators.lookup(listener.types.directory) is not None
    assert listener.translators.lookup(listener.types.process) is not None
    assert listener.translators.lookup(listener.types.text) is None
    assert listener.translators.lookup(listener.types.error) is None
    assert listener.translators.lookup(listener.types.directory_listing) is None
    assert listener.translators.lookup(listener.types.process_listing) is None
    for command in ("cd", "rm", "kill", "show"):
        accepted = listener._acceptable_types(command)
        assert listener.types.directory_listing not in accepted
        assert listener.types.process_listing not in accepted

    listener.submit("cd child")
    assert listener.cwd == str(child)
    assert os.getcwd() == process_cwd
    for command in ("unknown-1", "unknown-2", "unknown-3"):
        listener.submit(command)
    assert len(listener.history) == 2


def test_input_dispatch_preserves_one_argument_and_clears_attempts(tmp_path):
    spaced = tmp_path / "a b  "
    spaced.write_text("x")
    listener = make_listener(tmp_path)

    listener.submit(" \tshow   a b  ")
    assert history_text(listener)[-1].startswith(f"path: {spaced} | type: file")
    assert listener.input_text == ""
    assert listener.chip is None
    assert listener.pending_request is None

    previous = tuple(listener.history.rows)
    listener.submit("  \t  ")
    assert listener.history.rows == previous

    listener.submit("bad\\name")
    listener.submit("ps forbidden  value ")
    assert history_text(listener)[-2:] == (
        r"Error: unknown command: bad\\name.",
        "Error: ps does not take an argument.",
    )


def test_ls_lists_current_objects_in_escaped_display_order(tmp_path):
    (tmp_path / ".dot").write_text("dot")
    (tmp_path / "B").mkdir()
    (tmp_path / "a name").write_text("space")
    (tmp_path / "aZ").write_text("az")
    (tmp_path / "target-file").write_text("target")
    (tmp_path / "target-dir").mkdir()
    (tmp_path / "file-link").symlink_to("target-file")
    (tmp_path / "dir-link").symlink_to("target-dir", target_is_directory=True)
    (tmp_path / "broken-link").symlink_to("missing")
    listener = make_listener(tmp_path)

    listener.submit("ls")

    expected_names = [
        ".dot",
        "B",
        "a name",
        "aZ",
        "broken-link",
        "dir-link",
        "file-link",
        "target-dir",
        "target-file",
    ]
    rows = history_text(listener)
    assert [text[:11].rstrip() for text in rows[1:]] == expected_names
    by_name = {
        os.path.basename(presentation.value.path): presentation
        for presentation in listener.history.presentations
        if type(presentation.value) in {FileRef, DirectoryRef}
    }
    assert by_name["B"].type is listener.types.directory
    assert by_name["dir-link"].type is listener.types.directory
    assert by_name["file-link"].type is listener.types.file
    assert by_name["broken-link"].type is listener.types.file

    rendered = layout(listener.history, 10_000)
    row = rendered.rows[3]
    presentation = rendered.hit_test(0, 3)
    assert presentation.value == FileRef(str(tmp_path / "a name"))
    assert all(
        rendered.hit_test(column, 3) is presentation
        for column in range(row.display_width)
    )
    assert row.text.startswith("a name")


def test_ls_empty_and_expected_failures_leave_listener_usable(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    ordinary = tmp_path / "ordinary"
    ordinary.write_text("x")
    listener = make_listener(tmp_path)

    listener.submit("ls empty")
    listener.submit("ls ordinary")
    listener.submit("ls missing")
    listener.submit("show ordinary")

    rows = history_text(listener)
    assert rows[0] == f"{'name':<4}  {'size':>12}  {'modified':<20}"
    assert rows[1] == f"Directory is empty: {empty}"
    assert rows[2] == f"Error: not a directory: {ordinary}"
    assert rows[3].startswith("Error: path does not exist:")
    assert rows[4].startswith(f"path: {ordinary} | type: file")


def test_ls_reports_rooted_permission_failure_without_escaping(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    listener = HeadlessListener(
        str(root), RootedFilesystem(root), FixedProcesses()
    )

    listener.submit(f"ls {outside}")

    assert history_text(listener)[0].startswith("Error: cannot normalize")
    assert "path is outside allowed root" in history_text(listener)[0]
    assert listener.input_text == ""


def test_rooted_filesystem_blocks_escape_and_unlinks_only_final_link(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    safe = root / "safe"
    safe.write_text("safe")
    external_dir = tmp_path / "external-dir"
    external_dir.mkdir()
    external_file = external_dir / "outside"
    external_file.write_text("outside")
    intermediate = root / "escape"
    intermediate.symlink_to(external_dir, target_is_directory=True)
    final_link = root / "final-link"
    final_link.symlink_to(external_file)
    filesystem = RootedFilesystem(root)

    assert filesystem.stat(str(safe)).st_size == 4
    assert filesystem.lstat(str(final_link)).st_mode
    assert filesystem.readlink(str(final_link)) == str(external_file)
    with pytest.raises(PermissionError):
        filesystem.abspath(str(root / ".." / "external-dir"))
    with pytest.raises(PermissionError):
        filesystem.stat(str(intermediate / "outside"))
    with pytest.raises(PermissionError):
        filesystem.unlink(str(intermediate / "outside"))
    with pytest.raises(PermissionError):
        filesystem.stat(str(final_link))

    filesystem.unlink(str(final_link))
    assert not final_link.exists()
    assert external_file.read_text() == "outside"


def test_linux_process_parser_filters_sorts_decodes_and_falls_back(tmp_path):
    proc_root = tmp_path / "proc"
    proc_root.mkdir()
    write_process(proc_root, 20, uid=1000, state="R", cmdline=b"run\0two\0")
    write_process(proc_root, 3, name="fallback raw ", uid=1000, state="I")
    write_process(proc_root, 25, uid=1000, state="S", cmdline=b"bad\xff\0")
    write_process(proc_root, 11, uid=2000, state="S", cmdline=b"other")
    malformed = proc_root / "7"
    malformed.mkdir()
    (malformed / "status").write_text("Name:\tbad\n")
    (malformed / "cmdline").write_bytes(b"bad")
    (proc_root / "not-a-pid").mkdir()
    service = LinuxProcessService(
        proc_root, getuid=lambda: 1000, getpid=lambda: 20, kill=lambda pid, sig: None
    )

    records = service.list_for_uid(1000)
    assert [record.pid for record in records] == [3, 20, 25]
    assert records[0].command == "fallback raw "
    assert records[0].state == "idle"
    assert records[1].command == "run two "
    assert records[1].state == "running"
    assert records[2].command == b"bad\xff ".decode(
        sys.getfilesystemencoding(), errors="surrogateescape"
    )
    assert service.own_uid == 1000
    assert service.own_pid == 20


@pytest.mark.parametrize(
    ("code", "word"),
    [
        ("R", "running"),
        ("S", "sleeping"),
        ("D", "disk-sleep"),
        ("T", "stopped"),
        ("t", "tracing"),
        ("Z", "zombie"),
        ("X", "dead"),
        ("x", "dead"),
        ("I", "idle"),
        ("?", "unknown"),
    ],
)
def test_linux_process_state_mapping(code, word):
    assert process_state_word(code) == word


def test_linux_process_direct_inspection_reports_missing_and_malformed(tmp_path):
    proc_root = tmp_path / "proc"
    proc_root.mkdir()
    malformed = proc_root / "4"
    malformed.mkdir()
    (malformed / "status").write_text("Name:\tbad\nUid:\t1000\n")
    (malformed / "cmdline").write_bytes(b"")
    service = LinuxProcessService(
        proc_root, getuid=lambda: 1000, getpid=lambda: 99, kill=lambda pid, sig: None
    )

    with pytest.raises(ProcessInspectionError, match="missing State"):
        service.inspect(4)
    with pytest.raises(FileNotFoundError):
        service.inspect(5)


def test_ps_filters_sorts_keeps_own_pid_and_presents_only_pid(tmp_path):
    processes = FixedProcesses(
        records={
            700: InspectedProcess(700, 1000, "running", "pbui\0raw"),
            2: InspectedProcess(2, 1000, "sleeping", "two"),
            1: InspectedProcess(1, 2000, "idle", "foreign"),
        }
    )
    listener = make_listener(tmp_path, processes)

    listener.submit("ps")

    assert history_text(listener) == (
        PROCESS_HEADER,
        process_table_row(2, "sleeping", "1000", "two"),
        process_table_row(700, "running", "1000", r"pbui\x00raw"),
    )
    presentations = listener.history.presentations
    assert type(presentations[0].value) is ProcessListing
    assert [item.value for item in presentations[1:]] == [
        ProcessRef(2),
        ProcessRef(700),
    ]


def test_show_covers_files_directories_links_broken_and_current_type(tmp_path):
    ordinary = tmp_path / "ordinary"
    ordinary.write_text("data")
    os.utime(ordinary, (0, 0))
    directory = tmp_path / "directory"
    directory.mkdir()
    file_link = tmp_path / "file-link"
    file_link.symlink_to("ordinary")
    directory_link = tmp_path / "directory-link"
    directory_link.symlink_to("directory", target_is_directory=True)
    broken = tmp_path / "broken"
    broken.symlink_to("missing")
    listener = make_listener(tmp_path)

    for path in (ordinary, directory, file_link, directory_link, broken):
        listener.submit(f"show {path.name}")

    rows = history_text(listener)
    assert rows[0] == (
        f"path: {ordinary} | type: file | size: 4 bytes | "
        "mtime: 1970-01-01T00:00:00Z"
    )
    assert rows[1] == f"path: {directory} | type: directory"
    assert "type: file | symlink -> ordinary | size: 4 bytes" in rows[2]
    assert rows[3] == (
        f"path: {directory_link} | type: directory | symlink -> directory"
    )
    assert (
        f"path: {broken} | type: file (broken symlink) | symlink -> missing"
        in rows[4]
    )

    listener = make_listener(tmp_path)
    listener.submit("ls")
    stale = one_presentation(
        listener, listener.types.file, FileRef(str(ordinary))
    )
    ordinary.unlink()
    ordinary.mkdir()
    listener.select(stale, "ordinary")
    assert history_text(listener)[-1] == f"path: {ordinary} | type: directory"
    ordinary.rmdir()
    listener.select(stale, "ordinary")
    assert history_text(listener)[-1].startswith(f"Error: cannot show {ordinary}:")


def test_show_process_refreshes_and_reports_an_exited_process(tmp_path):
    processes = FixedProcesses(
        records={8: InspectedProcess(8, 1000, "sleeping", "worker\targ")}
    )
    listener = make_listener(tmp_path, processes)

    listener.submit("show 8")
    del processes.records[8]
    listener.submit("show 8")

    assert history_text(listener) == (
        r"pid: 8 | command: worker\targ | state: sleeping",
        "Error: cannot show process 8: process is gone.",
    )


def test_cd_preserves_history_and_old_absolute_presentations(tmp_path):
    first = tmp_path / "first"
    first.mkdir()
    old = first / "old"
    old.write_text("old")
    second = tmp_path / "second"
    second.mkdir()
    listener = HeadlessListener(
        str(first), RootedFilesystem(tmp_path), FixedProcesses()
    )
    listener.submit("ls")
    old_presentation = one_presentation(listener, listener.types.file)
    previous_rows = listener.history.rows

    listener.submit(f"cd {second}")
    assert listener.cwd == str(second)
    assert listener.history.rows == previous_rows
    listener.select(old_presentation, "old")
    assert history_text(listener)[-1].startswith(f"path: {old} | type: file")

    listener.submit("cd missing")
    listener.submit(f"cd {old}")
    assert listener.cwd == str(second)
    assert history_text(listener)[-2].startswith("Error: path does not exist:")
    assert history_text(listener)[-1].startswith("Error: not a directory:")


def test_rm_unlinks_files_and_links_but_refuses_current_directories(tmp_path):
    ordinary = tmp_path / "ordinary"
    ordinary.write_text("x")
    directory = tmp_path / "directory"
    directory.mkdir()
    directory_link = tmp_path / "directory-link"
    directory_link.symlink_to(directory, target_is_directory=True)
    broken = tmp_path / "broken"
    broken.symlink_to("missing")
    listener = make_listener(tmp_path)

    listener.submit("rm ordinary")
    listener.submit("rm broken")
    listener.submit("rm directory")
    listener.submit("rm directory-link")
    listener.submit("rm absent")

    assert not ordinary.exists()
    assert not broken.is_symlink()
    assert directory.is_dir()
    assert directory_link.is_symlink()
    rows = history_text(listener)
    assert rows[0] == f"Removed file: {ordinary}"
    assert rows[1] == f"Removed file: {broken}"
    assert rows[2].startswith("Error: is a directory:")
    assert rows[3].startswith("Error: is a directory:")
    assert rows[4].startswith(f"Error: cannot remove {tmp_path / 'absent'}:")


def test_rm_revalidates_stale_files_and_refuses_current_directories(tmp_path):
    changed = tmp_path / "changed"
    changed.write_text("old file")
    link = tmp_path / "link"
    link.symlink_to("future-directory")
    listener = make_listener(tmp_path)
    listener.submit("ls")
    changed_presentation = one_presentation(
        listener, listener.types.file, FileRef(str(changed))
    )
    link_presentation = one_presentation(
        listener, listener.types.file, FileRef(str(link))
    )
    changed.unlink()
    changed.mkdir()
    (tmp_path / "future-directory").mkdir()

    listener.submit("rm")
    assert listener.select(changed_presentation, "changed")
    listener.submit("rm")
    assert listener.select(link_presentation, "link")

    assert changed.is_dir()
    assert link.is_symlink()
    assert history_text(listener)[-2:] == (
        f"Error: refusing to remove directory {changed}.",
        f"Error: refusing to remove directory {link}.",
    )


def test_kill_records_only_sigterm_and_refuses_unsafe_pids(tmp_path):
    processes = FixedProcesses(
        records={
            20: InspectedProcess(20, 1000, "sleeping", "worker"),
            21: InspectedProcess(21, 1000, "running", "denied"),
        },
        signal_failures={21},
    )
    listener = make_listener(tmp_path, processes)

    for pid in (20, 21, 22, processes.own_pid, 1, 0, -4):
        listener.submit(f"kill {pid}")

    assert processes.sent == [(20, signal.SIGTERM)]
    rows = history_text(listener)
    assert rows[0] == "Sent SIGTERM to process 20."
    assert rows[1] == "Error: cannot signal process 21: signal denied."
    assert rows[2] == "Error: cannot signal process 22: process is gone."
    assert rows[3:] == (
        f"Error: refusing to signal process {processes.own_pid}.",
        "Error: refusing to signal process 1.",
        "Error: refusing to signal process 0.",
        "Error: refusing to signal process -4.",
    )


@pytest.mark.parametrize(
    ("command", "type_names"),
    [
        ("cd", {"Directory"}),
        ("rm", {"File"}),
        ("kill", {"Process"}),
        ("show", {"File", "Directory", "Process"}),
    ],
)
def test_missing_arguments_enter_the_exact_accept_set(tmp_path, command, type_names):
    listener = make_listener(tmp_path)

    listener.submit(f"  {command}   ")

    assert listener.input_text == command
    assert listener.pending_request.command_name == command
    assert {item.name for item in listener.pending_request.acceptable_types} == type_names
    assert listener.chip is None


def test_accept_uses_original_object_non_targets_cancel_and_backspace_are_atomic(tmp_path):
    target = tmp_path / "target"
    target.write_text("x")
    directory = tmp_path / "directory"
    directory.mkdir()
    listener = make_listener(tmp_path)
    listener.submit("ls")
    file_presentation = one_presentation(listener, listener.types.file)
    directory_presentation = one_presentation(listener, listener.types.directory)
    listener.submit("rm")
    before = (listener.input_text, listener.pending_request, listener.chip, listener.history.rows)

    assert not listener.select(directory_presentation, "directory")
    assert (listener.input_text, listener.pending_request, listener.chip, listener.history.rows) == before
    assert listener.select(file_presentation, "a label that is not a path")
    assert not target.exists()
    assert listener.input_text == ""
    assert listener.pending_request is None
    assert listener.chip is None

    listener.submit("show")
    listener.cancel()
    assert listener.input_text == ""
    assert listener.pending_request is None
    listener.state.chip = Chip(listener.types.file, FileRef(str(target)), "whole chip")
    assert listener.backspace_chip()
    assert listener.chip is None
    assert not listener.backspace_chip()


def test_default_show_translators_preserve_editor_and_ignore_text_error_none(tmp_path):
    target = tmp_path / "target"
    target.write_text("x")
    listener = make_listener(tmp_path)
    listener.submit("ls")
    file_presentation = one_presentation(listener, listener.types.file)
    listener.set_input_text("unfinished command")

    assert listener.select(file_presentation, "target")
    assert listener.input_text == "unfinished command"
    detail = one_presentation(listener, listener.types.text)
    assert not listener.select(detail, history_text(listener)[-1])
    listener.submit("unknown")
    error = one_presentation(listener, listener.types.error)
    assert not listener.select(error, "error")
    assert not listener.select(None, "")


def test_missing_ls_runs_cwd_and_missing_ps_runs_immediately(tmp_path):
    processes = FixedProcesses(
        records={9: InspectedProcess(9, 1000, "idle", "worker")}
    )
    listener = make_listener(tmp_path, processes)

    listener.submit("ls")
    listener.submit("ps")

    assert history_text(listener) == (
        f"{'name':<4}  {'size':>12}  {'modified':<20}",
        f"Directory is empty: {tmp_path}",
        PROCESS_HEADER,
        process_table_row(9, "idle", "1000", "worker"),
    )
    assert listener.pending_request is None


def test_production_send_sigterm_reaches_only_its_created_child(tmp_path):
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"]
    )
    try:
        assert child.poll() is None
        listener = HeadlessListener(
            str(tmp_path), RootedFilesystem(tmp_path), LinuxProcessService()
        )
        listener.submit(f"kill {child.pid}")
        child.wait(timeout=5)
        assert child.returncode == -signal.SIGTERM
        assert history_text(listener) == (
            f"Sent SIGTERM to process {child.pid}.",
        )
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=2)


@dataclass(frozen=True)
class FakeStat:
    st_mode: int
    st_size: int
    st_mtime: float


class CountingFilesystem:
    def __init__(self, root, entries, followed, unlinked=None):
        self.root = os.path.abspath(root)
        self.entries = tuple(entries)
        self.followed = dict(followed)
        self.unlinked = {} if unlinked is None else dict(unlinked)
        self.stat_calls = []
        self.lstat_calls = []
        self.iter_calls = []

    @staticmethod
    def _result(value):
        if isinstance(value, BaseException):
            raise value
        return value

    def abspath(self, path):
        return os.path.abspath(path)

    def stat(self, path):
        path = os.path.abspath(path)
        self.stat_calls.append(path)
        if path == self.root:
            return FakeStat(stat.S_IFDIR, 0, 0.0)
        return self._result(self.followed[path])

    def lstat(self, path):
        path = os.path.abspath(path)
        self.lstat_calls.append(path)
        return self._result(self.unlinked[path])

    def readlink(self, path):
        raise AssertionError(f"unexpected readlink: {path}")

    def iter_directory(self, path):
        path = os.path.abspath(path)
        self.iter_calls.append(path)
        return self.entries

    def unlink(self, path):
        raise AssertionError(f"unexpected unlink: {path}")


def test_ls_captures_metadata_and_stable_presentations_once_then_refreshes(tmp_path):
    dotfile = tmp_path / ".dot"
    dotfile.write_text("dot")
    target_file = tmp_path / "target-file"
    target_file.write_text("target")
    target_directory = tmp_path / "target-directory"
    target_directory.mkdir()
    file_link = tmp_path / "file-link"
    file_link.symlink_to(target_file.name)
    directory_link = tmp_path / "directory-link"
    directory_link.symlink_to(target_directory.name, target_is_directory=True)
    broken_link = tmp_path / "broken-link"
    broken_link.symlink_to("missing")
    os.utime(target_file, (101.4, 101.4))
    os.utime(target_directory, (202.6, 202.6))
    os.utime(broken_link, (303.4, 303.4), follow_symlinks=False)
    expected_stats = {
        ".dot": os.stat(dotfile),
        "target-file": os.stat(target_file),
        "target-directory": os.stat(target_directory),
        "file-link": os.stat(file_link),
        "directory-link": os.stat(directory_link),
        "broken-link": os.lstat(broken_link),
    }
    listener = make_listener(tmp_path)

    listener.submit("ls")

    (listing,) = listing_owners(listener)
    assert type(listing) is DirectoryListing
    assert listing.directory == DirectoryRef(str(tmp_path))
    assert all(row.listing_owner is listing for row in listener.history.rows)
    assert listing.header_presentation.type is listener.types.directory_listing
    assert listing.header_presentation.value is listing
    assert listing.header_presentation in listener.history.presentations
    assert len(listing.member_presentations) == len(listing.members) == 6

    members = {member.displayed_basename: member for member in listing.members}
    assert set(members) == set(expected_stats)
    for name, member in members.items():
        assert member.reference.path == str(tmp_path / name)
        assert member.displayed_basename == escape_display(name)
        assert member.mtime == int(round(expected_stats[name].st_mtime))
    assert members["target-file"].size == expected_stats["target-file"].st_size
    assert members["file-link"].size == expected_stats["file-link"].st_size
    assert members["broken-link"].size == expected_stats["broken-link"].st_size
    assert members["target-directory"].size is None
    assert members["directory-link"].size is None
    assert type(members["target-directory"].reference) is DirectoryRef
    assert type(members["directory-link"].reference) is DirectoryRef
    assert type(members["file-link"].reference) is FileRef
    assert type(members["broken-link"].reference) is FileRef

    for member, presentation in zip(
        listing.members, listing.member_presentations, strict=True
    ):
        assert presentation.value is member.reference
        expected_type = (
            listener.types.directory
            if type(member.reference) is DirectoryRef
            else listener.types.file
        )
        assert presentation.type is expected_type
    assert {row.presentations[0] for row in listener.history.rows} == {
        listing.header_presentation,
        *listing.member_presentations,
    }
    assert history_text(listener) == directory_table_text(listing)
    rendered = layout(listener.history, 10_000)
    for row_number, row in enumerate(rendered.rows):
        presentation = listener.history.rows[row_number].presentations[0]
        assert all(
            rendered.hit_test(column, row_number) is presentation
            for column in range(row.display_width)
        )

    captured_snapshot = tuple(
        (member.reference, member.displayed_basename, member.size, member.mtime)
        for member in listing.members
    )
    target_file.write_text("a much longer replacement")
    (tmp_path / "new-file").write_text("new")
    assert tuple(
        (member.reference, member.displayed_basename, member.size, member.mtime)
        for member in listing.members
    ) == captured_snapshot
    assert tuple(listing.visible_members()) == tuple(
        sorted(listing.members, key=lambda member: member.displayed_basename)
    )

    listener.submit("ls")
    first, second = listing_owners(listener)
    assert first is listing
    assert second is not first
    assert "new-file" in {
        member.displayed_basename for member in second.members
    }
    assert next(
        member for member in second.members if member.displayed_basename == "target-file"
    ).size == len("a much longer replacement")


def test_ls_omits_only_dot_entries_and_does_not_repeat_member_metadata_reads(tmp_path):
    root = str(tmp_path)
    file_path = str(tmp_path / ".hidden")
    directory_path = str(tmp_path / "directory")
    entries = (
        FilesystemEntry(".", str(tmp_path / ".")),
        FilesystemEntry("..", str(tmp_path / "..")),
        FilesystemEntry(".hidden", file_path),
        FilesystemEntry("directory", directory_path),
    )
    filesystem = CountingFilesystem(
        root,
        entries,
        {
            file_path: FakeStat(stat.S_IFREG, 17, 10.6),
            directory_path: FakeStat(stat.S_IFDIR, 999, 20.4),
        },
    )
    listener = HeadlessListener(
        root,
        filesystem,
        FixedProcesses(),
        username_lookup=lambda uid: str(uid),
    )

    listener.submit("ls")

    (listing,) = listing_owners(listener)
    assert [member.displayed_basename for member in listing.members] == [
        ".hidden",
        "directory",
    ]
    assert filesystem.iter_calls == [root]
    assert filesystem.stat_calls.count(file_path) == 1
    assert filesystem.stat_calls.count(directory_path) == 1
    assert filesystem.lstat_calls == []


def test_ls_mid_capture_failure_appends_only_error_and_no_owned_rows(tmp_path):
    root = str(tmp_path)
    first = str(tmp_path / "first")
    denied = str(tmp_path / "denied")
    filesystem = CountingFilesystem(
        root,
        (FilesystemEntry("first", first), FilesystemEntry("denied", denied)),
        {
            first: FakeStat(stat.S_IFREG, 1, 1.0),
            denied: PermissionError(13, "denied", denied),
        },
    )
    listener = HeadlessListener(
        root,
        filesystem,
        FixedProcesses(),
        username_lookup=lambda uid: str(uid),
    )

    listener.submit("ls")

    assert filesystem.stat_calls.count(first) == 1
    assert history_text(listener) == (
        f"Error: cannot list {root}: [Errno 13] denied: '{denied}'.",
    )
    assert listener.history.rows[0].listing_owner is None
    assert listing_owners(listener) == ()
    assert all(
        presentation.type is listener.types.error
        for presentation in listener.history.presentations
    )


def test_empty_ls_and_ps_retain_bound_listing_targets(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    listener = make_listener(tmp_path)

    listener.submit("ls empty")
    directory_listing = listener.history.rows[0].listing_owner
    assert type(directory_listing) is DirectoryListing
    assert directory_listing.members == ()
    assert directory_listing.member_presentations == ()
    assert directory_listing.header_presentation.value is directory_listing
    assert history_text(listener) == (
        f"{'name':<4}  {'size':>12}  {'modified':<20}",
        f"Directory is empty: {empty}",
    )
    assert listener.history.rows[0].presentations == (
        directory_listing.header_presentation,
    )
    assert listener.history.rows[1].presentations == ()

    listener.submit("ps")
    process_rows = listener.history.rows[-2:]
    process_listing = process_rows[0].listing_owner
    assert type(process_listing) is ProcessListing
    assert process_listing.members == ()
    assert process_listing.member_presentations == ()
    assert process_listing.header_presentation.value is process_listing
    assert process_rows[0].presentations == (process_listing.header_presentation,)
    assert process_rows[1].presentations == ()
    assert history_text(listener)[-2:] == (
        PROCESS_HEADER,
        "No processes are available.",
    )


def test_ps_captures_filtered_cached_members_and_owned_presentations(tmp_path):
    processes = FixedProcesses(
        records={
            700: InspectedProcess(700, 1000, "running", "pbui\nfull\\command"),
            2: InspectedProcess(2, 1000, "sleeping", "two\targs"),
            1: InspectedProcess(1, 2000, "idle", "foreign"),
        }
    )
    lookups = []

    def username_lookup(uid):
        lookups.append(uid)
        return "ali\nce"

    listener = make_listener(
        tmp_path, processes, username_lookup=username_lookup
    )

    listener.submit("ps")

    (listing,) = listing_owners(listener)
    assert type(listing) is ProcessListing
    assert processes.list_uids == [1000]
    assert lookups == [1000, 1000]
    assert [member.reference.pid for member in listing.members] == [700, 2]
    assert [member.reference.pid for member in listing.visible_members()] == [2, 700]
    assert [member.uid for member in listing.members] == [1000, 1000]
    assert [member.displayed_user for member in listing.members] == [
        r"ali\nce",
        r"ali\nce",
    ]
    assert [member.command for member in listing.members] == [
        r"pbui\nfull\\command",
        r"two\targs",
    ]
    assert history_text(listener) == (
        PROCESS_HEADER,
        process_table_row(2, "sleeping", r"ali\nce", r"two\targs"),
        process_table_row(
            700, "running", r"ali\nce", r"pbui\nfull\\command"
        ),
    )
    assert all(row.listing_owner is listing for row in listener.history.rows)
    assert listing.header_presentation.type is listener.types.process_listing
    assert listing.header_presentation.value is listing
    assert listing.header_presentation in listener.history.presentations
    assert len(listing.member_presentations) == 2
    for member, presentation in zip(
        listing.members, listing.member_presentations, strict=True
    ):
        assert presentation.type is listener.types.process
        assert presentation.value is member.reference
    assert {row.presentations[0] for row in listener.history.rows} == {
        listing.header_presentation,
        *listing.member_presentations,
    }


def test_ps_username_failures_fall_back_to_decimal_uid(tmp_path):
    def missing(_uid):
        raise KeyError("missing")

    def failed(_uid):
        raise OSError("database unavailable")

    for lookup in (missing, failed, lambda _uid: 1000):
        processes = FixedProcesses(
            records={5: InspectedProcess(5, 1000, "idle", "worker")}
        )
        listener = make_listener(
            tmp_path, processes, username_lookup=lookup
        )

        listener.submit("ps")

        (listing,) = listing_owners(listener)
        assert listing.members[0].displayed_user == "1000"
        assert history_text(listener) == (
            PROCESS_HEADER,
            process_table_row(5, "idle", "1000", "worker"),
        )


def test_ps_capture_is_stable_and_a_later_command_is_fresh(tmp_path):
    processes = FixedProcesses(
        records={5: InspectedProcess(5, 1000, "sleeping", "first")}
    )
    names = iter(("alpha", "beta"))
    listener = make_listener(
        tmp_path, processes, username_lookup=lambda _uid: next(names)
    )

    listener.submit("ps")
    (first,) = listing_owners(listener)
    processes.records[5] = InspectedProcess(5, 1000, "running", "second")
    assert first.members[0].state == "sleeping"
    assert first.members[0].displayed_user == "alpha"
    assert first.members[0].command == "first"

    listener.submit("ps")
    first_again, second = listing_owners(listener)
    assert first_again is first
    assert second is not first
    assert second.members[0].state == "running"
    assert second.members[0].displayed_user == "beta"
    assert second.members[0].command == "second"
    assert processes.list_uids == [1000, 1000]


def test_ps_enumeration_failure_has_no_partial_listing(tmp_path):
    class FailingProcesses(FixedProcesses):
        def list_for_uid(self, uid):
            self.list_uids.append(uid)
            raise OSError("proc unavailable")

    processes = FailingProcesses()
    listener = make_listener(
        tmp_path,
        processes,
        username_lookup=lambda _uid: pytest.fail("username lookup must not run"),
    )

    listener.submit("ps")

    assert processes.list_uids == [1000]
    assert history_text(listener) == (
        "Error: cannot list processes: proc unavailable.",
    )
    assert listing_owners(listener) == ()
    assert listener.history.rows[0].listing_owner is None


def test_listing_owner_survives_suffix_eviction_then_disappears(tmp_path):
    for name in ("a", "b", "c"):
        (tmp_path / name).write_text(name)
    listener = make_listener(tmp_path, history_max_rows=2)

    listener.submit("ls")

    assert len(listener.history.rows) == 2
    owner = listener.history.rows[0].listing_owner
    assert type(owner) is DirectoryListing
    assert all(row.listing_owner is owner for row in listener.history.rows)

    listener.submit("unknown-one")
    listener.submit("unknown-two")

    assert all(row.listing_owner is None for row in listener.history.rows)
    assert not any(row.listing_owner is owner for row in listener.history.rows)


def test_view_commands_require_a_retained_listing_before_grammar(tmp_path):
    listener = make_listener(tmp_path)

    for command in ("sort", "narrow value", "only two words", "widen extra"):
        listener.set_input_text(command)
        listener.submit()
        assert listener.input_text == ""
        assert listener.pending_request is None
        assert listener.pending_substring_listing is None
        assert listener.chip is None

    assert history_text(listener) == (
        "Error: no listing in history.",
        "Error: no listing in history.",
        "Error: no listing in history.",
        "Error: no listing in history.",
    )


@pytest.mark.parametrize("sort_key", ("name", "size", "mtime"))
def test_directory_sort_words_dispatch_through_the_listing_model(tmp_path, sort_key):
    (tmp_path / "file").write_text("data")
    (tmp_path / "directory").mkdir()
    listener = make_listener(tmp_path)
    listener.submit("ls")
    (listing,) = listing_owners(listener)

    listener.submit(f"sort {sort_key}")

    assert listing.view.sort_key == sort_key
    assert all(row.listing_owner is listing for row in listener.history.rows)


@pytest.mark.parametrize("kind", ("files", "directories"))
def test_directory_only_words_dispatch_through_the_listing_model(tmp_path, kind):
    (tmp_path / "file").write_text("data")
    (tmp_path / "directory").mkdir()
    listener = make_listener(tmp_path)
    listener.submit("ls")
    (listing,) = listing_owners(listener)

    listener.submit(f"only {kind}")

    assert listing.view.kind_filter == kind


@pytest.mark.parametrize("sort_key", ("pid", "state", "command"))
def test_process_sort_words_dispatch_through_the_listing_model(tmp_path, sort_key):
    processes = FixedProcesses(
        records={8: InspectedProcess(8, 1000, "sleeping", "worker")}
    )
    listener = make_listener(tmp_path, processes)
    listener.submit("ps")
    (listing,) = listing_owners(listener)

    listener.submit(f"sort {sort_key}")

    assert listing.view.sort_key == sort_key


@pytest.mark.parametrize(
    "kind",
    (
        "running",
        "sleeping",
        "disk-sleep",
        "stopped",
        "tracing",
        "zombie",
        "dead",
        "idle",
        "unknown",
    ),
)
def test_process_only_words_dispatch_through_the_listing_model(tmp_path, kind):
    processes = FixedProcesses(
        records={8: InspectedProcess(8, 1000, "sleeping", "worker")}
    )
    listener = make_listener(tmp_path, processes)
    listener.submit("ps")
    (listing,) = listing_owners(listener)

    listener.submit(f"only {kind}")

    assert listing.view.kind_filter == kind


def test_view_command_grammar_value_errors_and_atomic_views(tmp_path):
    (tmp_path / "file").write_text("data")
    listener = make_listener(tmp_path)
    listener.submit("ls")
    (directory_listing,) = listing_owners(listener)
    original = directory_listing.view

    for command, message in (
        ("sort", "Error: sort requires one key."),
        ("sort name extra", "Error: sort requires one key."),
        ("only", "Error: only requires one word."),
        ("only files ", "Error: only requires one word."),
        ("widen extra", "Error: widen does not take an argument."),
        ("sort pid", "Error: cannot sort this directory listing by pid."),
        (
            "only running",
            "Error: cannot apply only running to this directory listing.",
        ),
        (
            "sort bad\0key",
            r"Error: cannot sort this directory listing by bad\x00key.",
        ),
        (
            "only bad\\kind",
            r"Error: cannot apply only bad\\kind to this directory listing.",
        ),
    ):
        listener.submit(command)
        assert history_text(listener)[-1] == message
        assert directory_listing.view is original

    processes = FixedProcesses(
        records={8: InspectedProcess(8, 1000, "sleeping", "worker")}
    )
    listener = make_listener(tmp_path, processes)
    listener.submit("ps")
    (process_listing,) = listing_owners(listener)
    original = process_listing.view

    listener.submit("sort name")
    assert history_text(listener)[-1] == (
        "Error: cannot sort this process listing by name."
    )
    assert process_listing.view is original
    listener.submit("only files")
    assert history_text(listener)[-1] == (
        "Error: cannot apply only files to this process listing."
    )
    assert process_listing.view is original


def test_narrow_preserves_rest_of_line_and_widen_preserves_sort(tmp_path):
    processes = FixedProcesses(
        records={
            9: InspectedProcess(9, 1000, "sleeping", "before a b  "),
            2: InspectedProcess(2, 1000, "running", "unmatched"),
        }
    )
    listener = make_listener(tmp_path, processes)
    listener.submit("ps")
    (listing,) = listing_owners(listener)

    listener.submit("sort command")
    listener.submit("narrow a b  ")

    assert listing.view.substring_filter == "a b  "
    assert history_text(listener) == (
        PROCESS_HEADER,
        process_table_row(9, "sleeping", "1000", "before a b  "),
    )

    listener.submit("only sleeping")
    assert listing.view.kind_filter == "sleeping"
    listener.submit("widen")
    assert listing.view.sort_key == "command"
    assert listing.view.substring_filter is None
    assert listing.view.kind_filter is None
    assert history_text(listener) == (
        PROCESS_HEADER,
        process_table_row(9, "sleeping", "1000", "before a b  "),
        process_table_row(2, "running", "1000", "unmatched"),
    )


def test_empty_listing_redisplay_keeps_headers_and_explanatory_rows(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    listener = make_listener(tmp_path)
    listener.submit("ls empty")
    directory_listing = listener.history.rows[0].listing_owner

    listener.submit("sort size")
    assert history_text(listener) == (
        f"{'name':<4}  {'size':>12}  {'modified':<20}",
        f"Directory is empty: {empty}",
    )
    assert listener.history.rows[0].listing_owner is directory_listing

    listener.submit("only files")
    assert history_text(listener)[-1] == f"Directory is empty: {empty}"
    assert listener.history.rows[0].presentations == (
        directory_listing.header_presentation,
    )
    assert listener.history.rows[1].presentations == ()
    assert listener.history.rows[1].listing_owner is directory_listing

    listener.submit("widen")
    assert history_text(listener)[-1] == f"Directory is empty: {empty}"

    listener.submit("ps")
    process_listing = listener.history.rows[-2].listing_owner
    listener.submit("sort command")
    assert history_text(listener)[-2:] == (
        PROCESS_HEADER,
        "No processes are available.",
    )
    assert listener.history.rows[-1].presentations == ()
    assert listener.history.rows[-1].listing_owner is process_listing


def test_typed_and_explicit_targets_replace_their_blocks_in_place(tmp_path):
    (tmp_path / "large").write_text("12345")
    (tmp_path / "small").write_text("x")
    processes = FixedProcesses(
        records={
            9: InspectedProcess(9, 1000, "sleeping", "z-command"),
            2: InspectedProcess(2, 1000, "running", "a-command"),
        }
    )
    listener = make_listener(tmp_path, processes)
    listener.submit("ls")
    (directory_listing,) = listing_owners(listener)
    listener.submit("unknown-between")
    separator = listener.history.rows[-1]
    listener.submit("ps")
    directory_listing, process_listing = listing_owners(listener)
    directory_rows = tuple(
        row for row in listener.history.rows if row.listing_owner is directory_listing
    )
    revision = listener.history.revision

    listener.submit("sort command")

    assert process_listing.view.sort_key == "command"
    assert directory_listing.view.sort_key == "name"
    assert listener.history.revision == revision + 1
    assert listener.history.rows[len(directory_rows)] is separator
    assert tuple(listener.history.rows[: len(directory_rows)]) == directory_rows
    assert history_text(listener)[-3:] == (
        PROCESS_HEADER,
        process_table_row(2, "running", "1000", "a-command"),
        process_table_row(9, "sleeping", "1000", "z-command"),
    )

    process_rows = tuple(
        row for row in listener.history.rows if row.listing_owner is process_listing
    )
    revision = listener.history.revision
    assert listener.apply_listing_view(directory_listing, "sort", "size")

    assert directory_listing.view.sort_key == "size"
    assert process_listing.view.sort_key == "command"
    assert listener.history.revision == revision + 1
    assert listener.history.rows[len(directory_rows)] is separator
    assert tuple(listener.history.rows[-3:]) == process_rows
    assert history_text(listener)[:3] == directory_table_text(directory_listing)
    assert len(listener.history.rows) == 7


def test_partial_listing_is_targeted_and_evicted_listing_is_rejected(tmp_path):
    for name in ("a", "b", "c"):
        (tmp_path / name).write_text(name)
    listener = make_listener(tmp_path, history_max_rows=2)
    listener.submit("ls")
    listing = listener.history.rows[0].listing_owner
    assert type(listing) is DirectoryListing
    assert len(listener.history.rows) == 2

    listener.submit("sort size")

    assert listing.view.sort_key == "size"
    assert len(listener.history.rows) == 2
    assert all(row.listing_owner is listing for row in listener.history.rows)
    assert listing.header_presentation not in listener.history.presentations

    listener.submit("narrow c")
    assert listener.history.rows[0].presentations == (
        listing.header_presentation,
    )
    assert listener.history.presentations[0] is listing.header_presentation

    listener._append_error("first eviction.")
    listener._append_error("second eviction.")
    retained_snapshot = listener.history.rows
    view_snapshot = listing.view
    assert not listener.apply_listing_view(listing, "sort", "name")
    assert listing.view is view_snapshot
    assert listener.history.rows == retained_snapshot


def test_filter_and_widen_reuse_exact_directory_and_process_presentations(tmp_path):
    (tmp_path / "alpha").write_text("a")
    (tmp_path / "beta").write_text("b")
    processes = FixedProcesses(
        records={
            1: InspectedProcess(1, 1000, "running", "alpha-process"),
            2: InspectedProcess(2, 1000, "sleeping", "beta-process"),
        }
    )
    listener = make_listener(tmp_path, processes)
    listener.submit("ls")
    (directory_listing,) = listing_owners(listener)
    directory_member = next(
        member
        for member in directory_listing.members
        if member.displayed_basename == "beta"
    )
    directory_presentation = directory_listing.member_presentations[
        directory_listing.members.index(directory_member)
    ]

    listener.submit("narrow alpha")
    assert directory_presentation not in listener.history.presentations
    listener.submit("widen")
    restored = one_presentation(
        listener, listener.types.file, directory_member.reference
    )
    assert restored is directory_presentation
    assert restored.value is directory_member.reference

    listener.submit("ps")
    _, process_listing = listing_owners(listener)
    process_member = next(
        member for member in process_listing.members if member.reference.pid == 2
    )
    process_presentation = process_listing.member_presentations[
        process_listing.members.index(process_member)
    ]

    listener.submit("only running")
    assert process_presentation not in listener.history.presentations
    listener.submit("widen")
    restored = one_presentation(
        listener, listener.types.process, process_member.reference
    )
    assert restored is process_presentation
    assert restored.value is process_member.reference


def test_directory_redisplay_uses_cached_sort_filter_and_tie_breakers(tmp_path):
    (tmp_path / "z-file").write_text("12345")
    (tmp_path / "a-file").write_text("12345")
    (tmp_path / "directory").mkdir()
    os.utime(tmp_path / "z-file", (100, 100))
    os.utime(tmp_path / "a-file", (100, 100))
    os.utime(tmp_path / "directory", (200, 200))
    listener = make_listener(tmp_path)
    listener.submit("ls")
    (listing,) = listing_owners(listener)

    assert history_text(listener) == directory_table_text(listing)
    listener.submit("sort size")
    assert history_text(listener) == directory_table_text(listing)
    assert [member.displayed_basename for member in listing.visible_members()] == [
        "a-file",
        "z-file",
        "directory",
    ]
    listener.submit("sort mtime")
    assert history_text(listener) == directory_table_text(listing)
    assert [member.displayed_basename for member in listing.visible_members()] == [
        "directory",
        "a-file",
        "z-file",
    ]

    listener.submit(f"narrow {tmp_path.name}")
    assert listing.view.substring_filter == tmp_path.name
    assert history_text(listener) == (
        f"{'name':<4}  {'size':>12}  {'modified':<20}",
        "Nothing matches the active filters.",
    )


def test_process_redisplay_uses_full_cached_command_and_tie_breakers(tmp_path):
    long_prefix = "x" * 60
    processes = FixedProcesses(
        records={
            9: InspectedProcess(9, 1000, "sleeping", "same"),
            2: InspectedProcess(2, 1000, "sleeping", "same"),
            5: InspectedProcess(5, 1000, "running", f"{long_prefix}needle"),
        }
    )
    listener = make_listener(tmp_path, processes)
    listener.submit("ps")
    (listing,) = listing_owners(listener)

    listener.submit("sort state")
    displayed_pids = [
        row.text[:10].strip()
        for row in layout(listener.history, 10_000).rows[1:]
    ]
    assert displayed_pids == [
        "5",
        "2",
        "9",
    ]
    listener.submit("sort command")
    displayed_pids = [
        row.text[:10].strip()
        for row in layout(listener.history, 10_000).rows[1:]
    ]
    assert displayed_pids == [
        "2",
        "9",
        "5",
    ]
    listener.submit("narrow needle")
    listener.submit("only running")
    assert listing.view.substring_filter == "needle"
    assert listing.view.kind_filter == "running"
    assert history_text(listener) == (
        PROCESS_HEADER,
        process_table_row(
            5,
            "running",
            "1000",
            f"{'x' * 47}…",
        ),
    )
    assert listing.members[2].command == f"{long_prefix}needle"
    listener.submit("show 5")
    assert history_text(listener)[-1] == (
        f"pid: 5 | command: {long_prefix}needle | state: running"
    )


def test_modal_narrow_binds_original_listing_and_preserves_buffer_verbatim(tmp_path):
    (tmp_path / " alpha ").write_text("a")
    (tmp_path / "other").write_text("b")
    processes = FixedProcesses(
        records={8: InspectedProcess(8, 1000, "sleeping", "newer")}
    )
    listener = make_listener(tmp_path, processes)
    listener.submit("ls")
    (directory_listing,) = listing_owners(listener)
    rows_before = listener.history.rows
    revision_before = listener.history.revision

    listener.submit("narrow")

    assert listener.pending_substring_listing is directory_listing
    assert listener.input_text == ""
    assert listener.pending_request is None
    assert listener.chip is None
    assert listener.history.rows == rows_before
    assert listener.history.revision == revision_before

    listener.submit()
    assert listener.pending_substring_listing is directory_listing
    assert listener.history.rows == rows_before

    listener._command_ps()
    assert listing_owners(listener)[-1] is not directory_listing
    listener.set_input_text(" alpha ")
    listener.submit()

    assert directory_listing.view.substring_filter == " alpha "
    assert listener.pending_substring_listing is None
    assert listener.input_text == ""
    assert history_text(listener)[1].startswith(" alpha ")
    assert history_text(listener)[-1] == process_table_row(
        8, "sleeping", "1000", "newer"
    )


def test_modal_narrow_cancel_and_selection_are_atomic(tmp_path):
    target = tmp_path / "target"
    target.write_text("data")
    listener = make_listener(tmp_path)
    listener.submit("ls")
    (listing,) = listing_owners(listener)
    presentation = one_presentation(
        listener, listener.types.file, FileRef(str(target))
    )
    view_before = listing.view
    rows_before = listener.history.rows

    listener.submit("narrow")
    assert not listener.select(presentation, "target")
    assert listener.history.rows == rows_before
    listener.set_input_text("discard me")
    listener.cancel()

    assert listener.pending_substring_listing is None
    assert listener.input_text == ""
    assert listing.view is view_before
    assert listener.history.rows == rows_before
    assert listener.select(presentation, "target")
    assert history_text(listener)[-1].startswith(f"path: {target} | type: file")


def test_modal_narrow_fails_safely_when_bound_listing_is_evicted(tmp_path):
    (tmp_path / "target").write_text("data")
    listener = make_listener(tmp_path, history_max_rows=1)
    listener.submit("ls")
    listing = listener.history.rows[0].listing_owner
    listener.submit("narrow")
    view_before = listing.view
    listener._append_error("evicted.")
    rows_before_completion = listener.history.rows

    listener.set_input_text("target")
    listener.submit()

    assert listing.view is view_before
    assert listener.history.rows == rows_before_completion
    assert listener.pending_substring_listing is None
    assert listener.input_text == ""


def test_view_operations_do_not_refresh_directory_or_process_capture(tmp_path):
    root = str(tmp_path)
    file_path = str(tmp_path / "file")
    filesystem = CountingFilesystem(
        root,
        (FilesystemEntry("file", file_path),),
        {file_path: FakeStat(stat.S_IFREG, 3, 10.0)},
    )
    processes = FixedProcesses(
        records={7: InspectedProcess(7, 1000, "sleeping", "worker needle")}
    )
    lookups = []
    listener = HeadlessListener(
        root,
        filesystem,
        processes,
        username_lookup=lambda uid: lookups.append(uid) or "user",
    )
    listener.submit("ls")
    directory_listing = listing_owners(listener)[0]
    listener.submit("ps")
    process_listing = listing_owners(listener)[1]
    calls = (
        tuple(filesystem.stat_calls),
        tuple(filesystem.lstat_calls),
        tuple(filesystem.iter_calls),
        tuple(processes.list_uids),
        tuple(lookups),
    )

    listener.submit("sort command")
    listener.submit("narrow needle")
    listener.submit("only sleeping")
    listener.submit("widen")
    assert listener.apply_listing_view(directory_listing, "only", "files")
    assert listener.apply_listing_view(directory_listing, "narrow", "file")
    assert listener.apply_listing_view(directory_listing, "sort", "size")
    assert listener.apply_listing_view(directory_listing, "widen")
    listener.submit("narrow")
    listener.set_input_text("worker")
    listener.submit()

    assert process_listing.view.substring_filter == "worker"
    assert (
        tuple(filesystem.stat_calls),
        tuple(filesystem.lstat_calls),
        tuple(filesystem.iter_calls),
        tuple(processes.list_uids),
        tuple(lookups),
    ) == calls


def test_stored_member_seam_uses_retained_reference_and_existing_checks(tmp_path):
    file_path = tmp_path / "remove-me"
    file_path.write_text("payload")
    directory = tmp_path / "child"
    directory.mkdir()
    processes = FixedProcesses(records={42: InspectedProcess(42, 1000, "sleeping", "worker")})
    listener = make_listener(tmp_path, processes)
    listener.submit("ls")
    listing = listing_owners(listener)[0]
    file_presentation = one_presentation(listener, listener.types.file, FileRef(str(file_path)))
    directory_presentation = one_presentation(
        listener, listener.types.directory, DirectoryRef(str(directory))
    )

    assert not listener.execute_stored_member(file_presentation, "kill")
    assert listener.execute_stored_member(file_presentation, "show")
    assert history_text(listener)[-1].startswith(f"path: {file_path} | type: file")
    assert listener.execute_stored_member(directory_presentation, "cd")
    assert listener.cwd == str(directory)
    assert listener.execute_stored_member(directory_presentation, "ls")
    assert listing_owners(listener)[-1] is not listing
    assert listing_owners(listener)[-1].directory is directory_presentation.value
    assert listener.execute_stored_member(file_presentation, "rm")
    assert not file_path.exists()

    listener.submit("ps")
    process_presentation = one_presentation(listener, listener.types.process, ProcessRef(42))
    assert listener.execute_stored_member(process_presentation, "show")
    assert listener.execute_stored_member(process_presentation, "kill")
    assert processes.sent == [(42, signal.SIGTERM)]
    processes.records.pop(42)
    assert listener.execute_stored_member(process_presentation, "kill")
    assert processes.sent == [(42, signal.SIGTERM)]
    assert history_text(listener)[-1].startswith("Error:")


def test_stored_member_and_exact_narrow_reject_stale_or_modal_targets(tmp_path):
    (tmp_path / "file").write_text("x")
    listener = make_listener(tmp_path, history_max_rows=3)
    listener.submit("ls")
    listing = listing_owners(listener)[0]
    member = one_presentation(listener, listener.types.file)
    assert listener.begin_listing_narrow(listing)
    assert listener.pending_substring_listing is listing
    assert not listener.execute_stored_member(member, "show")
    assert not listener.begin_listing_narrow(listing)
    listener.cancel()

    listener._append_error("evict one")
    listener._append_error("evict two")
    listener._append_error("evict three")
    assert listing.header_presentation not in listener.history.presentations
    assert member not in listener.history.presentations
    assert not listener.begin_listing_narrow(listing)
    assert not listener.execute_stored_member(member, "show")
