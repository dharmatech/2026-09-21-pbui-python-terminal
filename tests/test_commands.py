from __future__ import annotations

import os
import signal
import subprocess
import sys
from dataclasses import dataclass, field

import pytest

from pbui.commands import (
    HeadlessListener,
    InspectedProcess,
    LinuxProcessService,
    ProcessInspectionError,
    RootedFilesystem,
    process_state_word,
)
from pbui.domain import DirectoryRef, FileRef, ProcessRef
from pbui.substrate import Chip
from pbui.text import layout


@dataclass
class FixedProcesses:
    own_uid: int = 1000
    own_pid: int = 700
    records: dict[int, InspectedProcess] = field(default_factory=dict)
    sent: list[tuple[int, signal.Signals]] = field(default_factory=list)
    signal_failures: set[int] = field(default_factory=set)

    def list_for_uid(self, uid):
        del uid
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
    return HeadlessListener(
        str(tmp_path), RootedFilesystem(tmp_path), service, **kwargs
    )


def history_text(listener):
    return tuple(row.text for row in layout(listener.history, 10_000).rows)


def one_presentation(listener, presentation_type, value=None):
    matches = [
        presentation
        for presentation in listener.history.presentations
        if presentation.presentation_type is presentation_type
        and (value is None or presentation.value == value)
    ]
    assert len(matches) == 1
    return matches[0]


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
    ]
    assert listener.command_names == ("ls", "ps", "show", "kill", "cd", "rm")
    assert listener.filesystem.allowed_root == str(tmp_path)
    assert listener.processes is processes
    assert listener.translators.lookup(listener.types.file) is not None
    assert listener.translators.lookup(listener.types.directory) is not None
    assert listener.translators.lookup(listener.types.process) is not None
    assert listener.translators.lookup(listener.types.text) is None
    assert listener.translators.lookup(listener.types.error) is None

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
    assert [text[11:] for text in history_text(listener)] == expected_names
    by_name = {
        os.path.basename(presentation.value.path): presentation
        for presentation in listener.history.presentations
    }
    assert by_name["B"].type is listener.types.directory
    assert by_name["dir-link"].type is listener.types.directory
    assert by_name["file-link"].type is listener.types.file
    assert by_name["broken-link"].type is listener.types.file

    rendered = layout(listener.history, 10_000)
    row = rendered.rows[2]
    assert rendered.hit_test(0, 2) is None
    assert rendered.hit_test(11, 2).value == FileRef(str(tmp_path / "a name"))
    assert row.text == "file       a name"


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
    assert rows[0] == f"Directory is empty: {empty}"
    assert rows[1] == f"Error: not a directory: {ordinary}"
    assert rows[2].startswith("Error: path does not exist:")
    assert rows[3].startswith(f"path: {ordinary} | type: file")


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

    assert history_text(listener) == ("2  sleeping  two", r"700  running  pbui\x00raw")
    presentations = listener.history.presentations
    assert [item.value for item in presentations] == [ProcessRef(2), ProcessRef(700)]


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
        f"Directory is empty: {tmp_path}",
        "9  idle  worker",
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
