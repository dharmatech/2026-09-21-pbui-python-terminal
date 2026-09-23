from __future__ import annotations

import os
from dataclasses import FrozenInstanceError

import pytest

from pbui.domain import (
    PROCESS_LISTING_STATES,
    DirectoryListing,
    DirectoryListingMember,
    DirectoryRef,
    DomainParseError,
    FileRef,
    ListingView,
    ListingViewError,
    OSReadOnlyPathAccess,
    ProcessListing,
    ProcessListingMember,
    ProcessRef,
    TypedDomainValue,
    classify_path,
    compose_failure_message,
    directory_listing_rows,
    escape_display,
    format_directory_detail,
    format_empty_directory,
    format_file_detail,
    format_path_detail,
    format_process_detail,
    format_removed_file,
    format_signal_result,
    format_utc_timestamp,
    make_domain_drawing_contexts,
    normalize_path,
    parse_directory,
    parse_file,
    parse_process,
    parse_show,
    path_listing_row,
    process_listing_row,
    process_listing_rows,
    register_domain_types,
    sort_path_references,
)
from pbui.substrate import PresentationHistory, PresentationTypeRegistry
from pbui.text import DrawingContext, display_width, layout, truncate_display


@pytest.fixture
def domain_types():
    return register_domain_types(PresentationTypeRegistry())


@pytest.fixture
def access():
    return OSReadOnlyPathAccess()


def render(row, width=500):
    history = PresentationHistory()
    history.append(row)
    return layout(history, width)


def test_registers_exact_domain_types_in_order_and_by_identity():
    registry = PresentationTypeRegistry()
    types = register_domain_types(registry)

    assert [entry.name for entry in registry] == [
        "File",
        "Directory",
        "Process",
        "Text",
        "Error",
        "DirectoryListing",
        "ProcessListing",
        "Value",
    ]
    assert len({id(entry) for entry in registry}) == 8
    assert types.file is registry.lookup("File")
    assert types.directory is registry.lookup("Directory")
    assert types.process is registry.lookup("Process")
    assert types.text is registry.lookup("Text")
    assert types.error is registry.lookup("Error")
    assert types.directory_listing is registry.lookup("DirectoryListing")
    assert types.process_listing is registry.lookup("ProcessListing")
    assert types.value is registry.lookup("Value")
    assert types.file is not types.directory
    with pytest.raises(ValueError, match="already registered"):
        register_domain_types(registry)


def test_references_are_immutable_absolute_and_exactly_typed(tmp_path):
    file_ref = FileRef(str(tmp_path / "item"))
    directory_ref = DirectoryRef(str(tmp_path))

    with pytest.raises(FrozenInstanceError):
        file_ref.path = "/changed"
    with pytest.raises(FrozenInstanceError):
        directory_ref.path = "/changed"
    for reference_type in (FileRef, DirectoryRef):
        with pytest.raises(ValueError, match="absolute"):
            reference_type("relative")
        with pytest.raises(TypeError, match="string"):
            reference_type(3)

    assert [ProcessRef(pid).pid for pid in (-8, 0, 1)] == [-8, 0, 1]
    for invalid in (True, 1.0, "1"):
        with pytest.raises(TypeError, match="exact integer"):
            ProcessRef(invalid)


def test_normalization_captures_explicit_cwd_lexically(tmp_path, domain_types, access):
    first_cwd = tmp_path / "first" / "child"
    second_cwd = tmp_path / "second"
    first_cwd.mkdir(parents=True)
    second_cwd.mkdir()

    normalized = normalize_path("../item", str(first_cwd), access)
    parsed = parse_file("../item", str(first_cwd), domain_types, access)

    assert normalized == str(tmp_path / "first" / "item")
    assert parsed.value == FileRef(normalized)
    assert normalize_path("../item", str(second_cwd), access) == str(
        tmp_path / "item"
    )
    assert parsed.value.path == normalized


def test_classifies_files_directories_links_broken_links_and_absence(
    tmp_path, domain_types, access
):
    regular_file = tmp_path / "regular"
    regular_file.write_text("content")
    directory = tmp_path / "directory"
    directory.mkdir()
    file_link = tmp_path / "file-link"
    file_link.symlink_to(regular_file)
    directory_link = tmp_path / "directory-link"
    directory_link.symlink_to(directory, target_is_directory=True)
    broken_link = tmp_path / "broken-link"
    broken_link.symlink_to(tmp_path / "missing-target")
    absent = tmp_path / "absent"

    file_item = classify_path(str(regular_file), domain_types, access)
    directory_item = classify_path(str(directory), domain_types, access)
    file_link_item = classify_path(str(file_link), domain_types, access)
    directory_link_item = classify_path(str(directory_link), domain_types, access)
    broken_item = classify_path(str(broken_link), domain_types, access)
    absent_item = classify_path(
        str(absent), domain_types, access, permit_absent=True
    )

    assert file_item == TypedDomainValue(domain_types.file, FileRef(str(regular_file)))
    assert directory_item == TypedDomainValue(
        domain_types.directory, DirectoryRef(str(directory))
    )
    assert file_link_item == TypedDomainValue(
        domain_types.file, FileRef(str(file_link))
    )
    assert directory_link_item == TypedDomainValue(
        domain_types.directory, DirectoryRef(str(directory_link))
    )
    assert broken_item == TypedDomainValue(
        domain_types.file, FileRef(str(broken_link))
    )
    assert absent_item == TypedDomainValue(domain_types.file, FileRef(str(absent)))
    assert file_link_item.value.path != os.path.realpath(file_link_item.value.path)
    assert directory_link_item.value.path != os.path.realpath(
        directory_link_item.value.path
    )
    with pytest.raises(DomainParseError, match="does not exist"):
        classify_path(str(absent), domain_types, access)


def test_directory_and_file_parsers_apply_current_followed_classification(
    tmp_path, domain_types, access
):
    regular_file = tmp_path / "regular"
    regular_file.write_text("content")
    directory = tmp_path / "directory"
    directory.mkdir()
    broken_link = tmp_path / "broken"
    broken_link.symlink_to("missing")

    assert parse_directory("directory", str(tmp_path), domain_types, access) == (
        TypedDomainValue(domain_types.directory, DirectoryRef(str(directory)))
    )
    for argument in ("regular", "broken", "missing"):
        with pytest.raises(DomainParseError):
            parse_directory(argument, str(tmp_path), domain_types, access)

    assert parse_file("regular", str(tmp_path), domain_types, access).value == FileRef(
        str(regular_file)
    )
    assert parse_file("broken", str(tmp_path), domain_types, access).value == FileRef(
        str(broken_link)
    )
    assert parse_file("missing", str(tmp_path), domain_types, access).value == FileRef(
        str(tmp_path / "missing")
    )
    with pytest.raises(DomainParseError, match="is a directory"):
        parse_file("directory", str(tmp_path), domain_types, access)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("17", 17), ("+17", 17), ("0", 0), ("-17", -17), ("-0", 0)],
)
def test_process_parser_accepts_exact_ascii_signed_decimal(
    raw, expected, tmp_path, domain_types, access
):
    parsed = parse_process(raw, str(tmp_path), domain_types, access)

    assert parsed.presentation_type is domain_types.process
    assert parsed.value == ProcessRef(expected)


@pytest.mark.parametrize(
    "raw", ["", " ", " 1", "1 ", "+", "-", "1.0", "1x", "١", "１２"]
)
def test_process_parser_rejects_everything_outside_exact_grammar(
    raw, tmp_path, domain_types, access
):
    with pytest.raises(DomainParseError, match="invalid process id"):
        parse_process(raw, str(tmp_path), domain_types, access)


def test_show_parser_prioritizes_real_paths_then_process_then_absent_file(
    tmp_path, domain_types, access
):
    numeric_file = tmp_path / "123"
    numeric_file.write_text("numbered")
    directory = tmp_path / "dir"
    directory.mkdir()

    assert parse_show("123", str(tmp_path), domain_types, access) == TypedDomainValue(
        domain_types.file, FileRef(str(numeric_file))
    )
    assert parse_show("dir", str(tmp_path), domain_types, access) == TypedDomainValue(
        domain_types.directory, DirectoryRef(str(directory))
    )
    assert parse_show("-42", str(tmp_path), domain_types, access) == TypedDomainValue(
        domain_types.process, ProcessRef(-42)
    )
    assert parse_show("not there", str(tmp_path), domain_types, access) == (
        TypedDomainValue(domain_types.file, FileRef(str(tmp_path / "not there")))
    )


def test_display_escaping_is_safe_fixed_width_and_does_not_mutate_source():
    source = "plain Ω [bold] x y\\\n\r\t\x1b\x85\ud800\U0001d173"
    result = escape_display(source)

    assert result == (
        "plain Ω [bold] x y\\\\\\n\\r\\t\\x1b\\x85"
        "\\ud800\\U0001d173"
    )
    assert source.endswith("\ud800\U0001d173")
    assert "\n" not in result
    assert "\r" not in result
    assert "\t" not in result
    assert all(character.isprintable() for character in result)


def test_path_drawers_use_explicit_modes_and_keep_a_spaced_name_one_span(
    tmp_path, domain_types
):
    reference = FileRef(str(tmp_path / "a name\n[raw]"))
    contexts = make_domain_drawing_contexts(domain_types)

    standalone = render(
        contexts.standalone.present_row(reference, domain_types.file)
    )
    listing_row = contexts.listing.present_row(reference, domain_types.file)
    listing = render(listing_row)

    assert standalone.rows[0].text == escape_display(reference.path)
    assert listing.rows[0].text == r"a name\n[raw]"
    presentation = listing_row.presentations[0]
    assert listing.hit_test(0, 0) is presentation
    assert listing.hit_test(5, 0) is presentation
    assert presentation.value is reference


def test_path_sorting_uses_escaped_basename_case_sensitive_codepoint_order(tmp_path):
    references = [
        FileRef(str(tmp_path / "a\n")),
        DirectoryRef(str(tmp_path / ".dot")),
        FileRef(str(tmp_path / "aZ")),
        FileRef(str(tmp_path / "B")),
        FileRef(str(tmp_path / "b")),
    ]

    assert [os.path.basename(item.path) for item in sort_path_references(references)] == [
        ".dot",
        "B",
        "aZ",
        "a\n",
        "b",
    ]


def test_path_rows_are_exact_and_only_the_name_is_presented(tmp_path, domain_types):
    contexts = make_domain_drawing_contexts(domain_types)
    cases = [
        (
            TypedDomainValue(domain_types.file, FileRef(str(tmp_path / "a file"))),
            "file       a file",
        ),
        (
            TypedDomainValue(
                domain_types.directory, DirectoryRef(str(tmp_path / "a directory"))
            ),
            "directory  a directory",
        ),
    ]

    for item, expected in cases:
        row = path_listing_row(item, domain_types, contexts.listing)
        result = render(row)
        presentation = row.presentations[0]

        assert result.rows[0].text == expected
        assert len(row.presentations) == 1
        assert result.hit_test(0, 0) is None
        assert result.hit_test(10, 0) is None
        assert result.hit_test(11, 0) is presentation
        assert result.hit_test(len(expected) - 1, 0) is presentation
        assert presentation.value is item.value


def test_process_row_presents_only_pid_and_escapes_raw_command(domain_types):
    contexts = make_domain_drawing_contexts(domain_types)
    process = ProcessRef(-12)
    row = process_listing_row(
        process, "sleeping", "cmd\n[raw]\\x", domain_types, contexts.listing
    )
    result = render(row)
    presentation = row.presentations[0]

    assert result.rows[0].text == r"-12  sleeping  cmd\n[raw]\\x"
    assert len(row.presentations) == 1
    assert result.hit_test(0, 0) is presentation
    assert result.hit_test(2, 0) is presentation
    assert result.hit_test(3, 0) is None
    assert result.hit_test(5, 0) is None
    assert presentation.value is process


def test_text_and_error_drawers_are_exact_and_not_path_or_process_types(domain_types):
    context = make_domain_drawing_contexts(domain_types).standalone
    text_row = context.present_row("literal [markup]", domain_types.text)
    error_row = context.present_row("failed once", domain_types.error)

    assert render(text_row).rows[0].text == "literal [markup]"
    assert render(error_row).rows[0].text == "Error: failed once"
    assert domain_types.text not in {
        domain_types.file,
        domain_types.directory,
        domain_types.process,
    }
    assert domain_types.error not in {
        domain_types.file,
        domain_types.directory,
        domain_types.process,
    }
    with pytest.raises(TypeError, match="FileRef"):
        context.present_row(DirectoryRef("/tmp"), domain_types.file)


def test_detail_and_result_formatters_cover_every_exact_product_form():
    file_ref = FileRef("/tmp/a\\b\n")
    directory_ref = DirectoryRef("/tmp/dir")
    process = ProcessRef(-7)

    assert format_utc_timestamp(0) == "1970-01-01T00:00:00Z"
    assert format_file_detail(file_ref, 12, 0) == (
        r"path: /tmp/a\\b\n | type: file | size: 12 bytes | mtime: "
        "1970-01-01T00:00:00Z"
    )
    assert format_file_detail(
        file_ref, 4, 1, symlink_target="../target\n"
    ) == (
        r"path: /tmp/a\\b\n | type: file | symlink -> ../target\n"
        " | size: 4 bytes | mtime: 1970-01-01T00:00:01Z"
    )
    assert format_path_detail(
        file_ref,
        size=2,
        mtime=0,
        symlink_target="missing",
        broken_symlink=True,
    ) == (
        r"path: /tmp/a\\b\n | type: file (broken symlink)"
        " | symlink -> missing | size: 2 bytes | mtime: 1970-01-01T00:00:00Z"
    )
    assert format_directory_detail(directory_ref) == (
        "path: /tmp/dir | type: directory"
    )
    assert format_path_detail(
        directory_ref, symlink_target="real-dir"
    ) == "path: /tmp/dir | type: directory | symlink -> real-dir"
    assert format_process_detail(process, "worker\t[1]", "sleeping") == (
        r"pid: -7 | command: worker\t[1] | state: sleeping"
    )
    assert format_removed_file(file_ref) == r"Removed file: /tmp/a\\b\n"
    assert format_signal_result(process) == "Sent SIGTERM to process -7."
    assert format_empty_directory(directory_ref) == "Directory is empty: /tmp/dir"
    assert "FileRef" not in format_file_detail(file_ref, 12, 0)
    assert "ProcessRef" not in format_process_detail(process, "worker", "running")


def test_failure_composer_escapes_raw_fields_once_before_error_drawing(domain_types):
    message = compose_failure_message(
        "cannot remove", "/tmp/a\\b\n", "Denied\tby OS"
    )
    context = make_domain_drawing_contexts(domain_types).standalone

    assert message == r"cannot remove /tmp/a\\b\n: Denied\tby OS."
    assert render(context.present_row(message, domain_types.error)).rows[0].text == (
        r"Error: cannot remove /tmp/a\\b\n: Denied\tby OS."
    )


def test_unexpected_path_access_error_becomes_domain_parse_failure(
    tmp_path, domain_types
):
    class DeniedAccess:
        def abspath(self, path):
            return os.path.abspath(path)

        def stat(self, path):
            raise PermissionError(13, "denied", path)

        def lstat(self, path):
            raise PermissionError(13, "denied", path)

    with pytest.raises(DomainParseError, match="cannot inspect"):
        parse_show("anything", str(tmp_path), domain_types, DeniedAccess())


def test_domain_drawing_contexts_are_independent_application_supplied_tables(
    domain_types,
):
    contexts = make_domain_drawing_contexts(domain_types)

    assert isinstance(contexts.standalone, DrawingContext)
    assert isinstance(contexts.listing, DrawingContext)
    assert contexts.standalone is not contexts.listing


def directory_listing_members():
    return (
        DirectoryListingMember(FileRef("/path-only-token/one"), "zeta", 5, 100),
        DirectoryListingMember(FileRef("/items/two"), "Beta", 10, 50),
        DirectoryListingMember(FileRef("/items/three"), "alpha", 10, 100),
        DirectoryListingMember(DirectoryRef("/items/four"), "adir", None, 200),
        DirectoryListingMember(DirectoryRef("/items/five"), "Zdir", None, 100),
    )


def process_listing_members():
    states = (
        "running",
        "sleeping",
        "disk-sleep",
        "stopped",
        "tracing",
        "zombie",
        "dead",
        "idle",
        "unknown",
    )
    members = [
        ProcessListingMember(ProcessRef(20), "running", 123, "needle-user", "same"),
        ProcessListingMember(
            ProcessRef(3),
            "sleeping",
            99,
            "alice",
            "x" * 60 + "TAIL",
        ),
        ProcessListingMember(ProcessRef(10), "running", 10, "777", "same"),
    ]
    members.extend(
        ProcessListingMember(
            ProcessRef(100 + index), state, index, f"user-{index}", f"cmd-{state}"
        )
        for index, state in enumerate(states[2:], start=2)
    )
    return tuple(members)


def test_listing_member_records_are_frozen_slotted_and_validate_exact_shapes():
    file_member = DirectoryListingMember(FileRef("/file"), "file", 0, -1)
    directory_member = DirectoryListingMember(
        DirectoryRef("/directory"), "directory", None, 0
    )
    process_member = ProcessListingMember(
        ProcessRef(1), "running", 0, "user", "command"
    )

    for member, attribute in (
        (file_member, "size"),
        (directory_member, "mtime"),
        (process_member, "uid"),
    ):
        with pytest.raises(FrozenInstanceError):
            setattr(member, attribute, 1)
        with pytest.raises((AttributeError, TypeError)):
            member.extra = "not slotted"

    for arguments in (
        (ProcessRef(1), "name", 1, 0),
        (FileRef("/file"), 7, 1, 0),
        (FileRef("/file"), "name", None, 0),
        (FileRef("/file"), "name", True, 0),
        (FileRef("/file"), "name", -1, 0),
        (DirectoryRef("/directory"), "name", 0, 0),
        (FileRef("/file"), "name", 1, True),
        (FileRef("/file"), "name", 1, 1.0),
    ):
        with pytest.raises((TypeError, ValueError)):
            DirectoryListingMember(*arguments)

    for arguments in (
        (FileRef("/file"), "running", 0, "user", "command"),
        (ProcessRef(1), "other", 0, "user", "command"),
        (ProcessRef(1), 3, 0, "user", "command"),
        (ProcessRef(1), "running", True, "user", "command"),
        (ProcessRef(1), "running", -1, "user", "command"),
        (ProcessRef(1), "running", 0, 3, "command"),
        (ProcessRef(1), "running", 0, "user", 3),
    ):
        with pytest.raises((TypeError, ValueError)):
            ProcessListingMember(*arguments)


def test_listing_construction_captures_iterables_once_and_uses_identity_equality():
    class OnePass:
        def __init__(self, values):
            self.values = values
            self.iterations = 0

        def __iter__(self):
            self.iterations += 1
            assert self.iterations == 1
            return iter(self.values)

    directory_values = directory_listing_members()
    process_values = process_listing_members()
    directory_input = OnePass(directory_values)
    process_input = OnePass(process_values)
    directory = DirectoryListing(DirectoryRef("/items"), directory_input)
    process = ProcessListing(process_input)

    assert directory_input.iterations == process_input.iterations == 1
    assert directory.members == directory_values
    assert process.members == process_values
    assert isinstance(directory.members, tuple)
    assert isinstance(process.members, tuple)
    assert directory.view == ListingView("name")
    assert process.view == ListingView("pid")
    assert directory != DirectoryListing(DirectoryRef("/items"), directory_values)
    assert process != ProcessListing(process_values)
    with pytest.raises(TypeError):
        DirectoryListing(FileRef("/items"), directory_values)
    with pytest.raises(TypeError):
        DirectoryListing(DirectoryRef("/items"), process_values)
    with pytest.raises(TypeError):
        ProcessListing(directory_values)


def test_directory_listing_sorts_only_cached_fields_with_deterministic_ties():
    listing = DirectoryListing(DirectoryRef("/items"), directory_listing_members())

    assert [member.displayed_basename for member in listing.visible_members()] == [
        "Beta",
        "Zdir",
        "adir",
        "alpha",
        "zeta",
    ]
    listing.replace_sort_key("size")
    assert [member.displayed_basename for member in listing.visible_members()] == [
        "Beta",
        "alpha",
        "zeta",
        "Zdir",
        "adir",
    ]
    listing.replace_sort_key("mtime")
    assert [member.displayed_basename for member in listing.visible_members()] == [
        "adir",
        "Zdir",
        "alpha",
        "zeta",
        "Beta",
    ]


def test_directory_listing_filters_replace_combine_widen_and_ignore_paths():
    listing = DirectoryListing(DirectoryRef("/items"), directory_listing_members())

    listing.replace_kind_filter("files")
    assert {member.displayed_basename for member in listing.visible_members()} == {
        "Beta",
        "alpha",
        "zeta",
    }
    listing.replace_kind_filter("directories")
    assert {member.displayed_basename for member in listing.visible_members()} == {
        "Zdir",
        "adir",
    }
    listing.replace_substring_filter("dir")
    assert [member.displayed_basename for member in listing.visible_members()] == [
        "Zdir",
        "adir",
    ]
    listing.replace_substring_filter("a")
    assert listing.view == ListingView("name", "a", "directories")
    assert [member.displayed_basename for member in listing.visible_members()] == [
        "adir"
    ]
    listing.replace_sort_key("size")
    assert listing.view == ListingView("size", "a", "directories")
    listing.replace_kind_filter(None)
    listing.replace_substring_filter("path-only-token")
    assert listing.visible_members() == ()
    listing.widen()
    assert listing.view == ListingView("size")
    assert len(listing.visible_members()) == 5


def test_directory_invalid_view_changes_are_atomic_and_preserve_all_identities():
    listing = DirectoryListing(DirectoryRef("/items"), directory_listing_members())
    listing.replace_sort_key("mtime")
    listing.replace_substring_filter("a")
    listing.replace_kind_filter("files")
    original_view = listing.view
    original_members = listing.members
    original_member_ids = tuple(map(id, listing.members))

    for operation, argument in (
        (listing.replace_sort_key, "pid"),
        (listing.replace_substring_filter, ""),
        (listing.replace_kind_filter, "running"),
    ):
        with pytest.raises(ListingViewError):
            operation(argument)
        assert listing.view is original_view
        assert listing.members is original_members
        assert tuple(map(id, listing.members)) == original_member_ids


def test_process_listing_sorts_by_pid_state_and_full_command_with_pid_ties():
    listing = ProcessListing(process_listing_members())

    assert [member.reference.pid for member in listing.visible_members()] == [
        3,
        10,
        20,
        102,
        103,
        104,
        105,
        106,
        107,
        108,
    ]
    listing.replace_sort_key("state")
    assert [
        (member.state, member.reference.pid) for member in listing.visible_members()
    ] == sorted(
        (member.state, member.reference.pid) for member in listing.members
    )
    listing.replace_sort_key("command")
    assert [
        (member.command, member.reference.pid) for member in listing.visible_members()
    ] == sorted(
        (member.command, member.reference.pid) for member in listing.members
    )
    assert [
        member.reference.pid
        for member in listing.visible_members()
        if member.command == "same"
    ] == [10, 20]


@pytest.mark.parametrize("state", sorted(PROCESS_LISTING_STATES))
def test_process_listing_accepts_each_exact_state_filter(state):
    listing = ProcessListing(process_listing_members())

    listing.replace_kind_filter(state)

    assert listing.visible_members()
    assert {member.state for member in listing.visible_members()} == {state}


def test_process_listing_filters_only_full_command_and_combines_replacements():
    listing = ProcessListing(process_listing_members())

    listing.replace_substring_filter("TAIL")
    assert [member.reference.pid for member in listing.visible_members()] == [3]
    listing.replace_substring_filter("needle")
    assert listing.visible_members() == ()
    listing.replace_substring_filter("777")
    assert listing.visible_members() == ()
    listing.replace_substring_filter("20")
    assert listing.visible_members() == ()
    listing.replace_substring_filter("running")
    assert listing.visible_members() == ()
    listing.replace_substring_filter("same")
    listing.replace_kind_filter("running")
    listing.replace_sort_key("command")
    assert [member.reference.pid for member in listing.visible_members()] == [10, 20]
    assert listing.view == ListingView("command", "same", "running")
    listing.replace_kind_filter("sleeping")
    assert listing.visible_members() == ()
    listing.widen()
    assert listing.view == ListingView("command")
    assert len(listing.visible_members()) == len(listing.members)


def test_process_invalid_view_changes_are_atomic_and_preserve_all_identities():
    listing = ProcessListing(process_listing_members())
    listing.replace_sort_key("state")
    listing.replace_substring_filter("cmd")
    listing.replace_kind_filter("idle")
    original_view = listing.view
    original_members = listing.members
    original_member_ids = tuple(map(id, listing.members))

    for operation, argument in (
        (listing.replace_sort_key, "mtime"),
        (listing.replace_substring_filter, ""),
        (listing.replace_kind_filter, "files"),
    ):
        with pytest.raises(ListingViewError):
            operation(argument)
        assert listing.view is original_view
        assert listing.members is original_members
        assert tuple(map(id, listing.members)) == original_member_ids


def test_listing_view_operations_never_revisit_host_or_escape_functions(monkeypatch):
    import pbui.domain as domain_module

    directory = DirectoryListing(DirectoryRef("/items"), directory_listing_members())
    process = ProcessListing(process_listing_members())

    def fail(*args, **kwargs):
        del args, kwargs
        raise AssertionError("pure listing view called a host or escape operation")

    monkeypatch.setattr(domain_module.os, "stat", fail)
    monkeypatch.setattr(domain_module.os, "lstat", fail)
    monkeypatch.setattr(domain_module.os, "scandir", fail)
    monkeypatch.setattr(domain_module.os.path, "basename", fail)
    monkeypatch.setattr(domain_module, "escape_display", fail)

    for sort_key in ("name", "size", "mtime"):
        directory.replace_sort_key(sort_key)
        directory.replace_substring_filter("a")
        directory.replace_kind_filter("files")
        directory.visible_members()
        directory.replace_kind_filter("directories")
        directory.visible_members()
        directory.widen()
        directory.visible_members()
    for sort_key in ("pid", "state", "command"):
        process.replace_sort_key(sort_key)
        process.replace_substring_filter("cmd")
        process.replace_kind_filter("running")
        process.visible_members()
        process.replace_kind_filter("sleeping")
        process.visible_members()
        process.widen()
        process.visible_members()


def presentation_for(context, value, presentation_type):
    fragment = context.present(value, presentation_type)
    return context.presentation(fragment.presentation_id)


def bind_listing_presentations(listing, domain_types):
    context = make_domain_drawing_contexts(domain_types).listing
    if type(listing) is DirectoryListing:
        listing_type = domain_types.directory_listing
        member_types = (
            domain_types.directory
            if type(member.reference) is DirectoryRef
            else domain_types.file
            for member in listing.members
        )
    else:
        listing_type = domain_types.process_listing
        member_types = (domain_types.process for _member in listing.members)
    header = presentation_for(context, listing, listing_type)
    members = tuple(
        presentation_for(context, member.reference, presentation_type)
        for member, presentation_type in zip(
            listing.members, member_types, strict=True
        )
    )
    listing.bind_presentations(header, members, domain_types)
    return header, members


def render_table(rows, width=500):
    history = PresentationHistory()
    for row in rows:
        history.append(row)
    return layout(history, width)


def test_directory_table_rows_are_complete_pure_display_cell_presentations(
    domain_types,
):
    long_name = "x" * 30
    listing = DirectoryListing(
        DirectoryRef("/items"),
        (
            DirectoryListingMember(FileRef("/items/a"), "a", 0, 0),
            DirectoryListingMember(
                FileRef(f"/items/{long_name}"), long_name, 1_234_567_890_123, 1
            ),
            DirectoryListingMember(
                DirectoryRef("/items/wide"), "界é", None, 1
            ),
        ),
    )
    with pytest.raises(ValueError, match="not bound"):
        directory_listing_rows(listing)
    header, member_presentations = bind_listing_presentations(listing, domain_types)

    rows = directory_listing_rows(listing)
    rendered = render_table(rows)
    texts = tuple(row.text for row in rendered.rows)
    assert texts == (
        f"{'name':<30}  {'size':>13}  {'modified':<20}",
        f"{'a':<30}  {0:>13}  1970-01-01T00:00:00Z",
        f"{long_name}  {1_234_567_890_123:>13}  1970-01-01T00:00:01Z",
        f"界é{' ' * 27}  {'':13}  1970-01-01T00:00:01Z",
    )
    visible_presentations = (
        header,
        member_presentations[0],
        member_presentations[1],
        member_presentations[2],
    )
    for row_number, (row, presentation) in enumerate(
        zip(rows, visible_presentations, strict=True)
    ):
        assert row.listing_owner is listing
        assert row.presentations == (presentation,)
        assert row.presentation_ids == (presentation.id,)
        for column in range(display_width(texts[row_number])):
            assert rendered.hit_test(column, row_number) is presentation

    listing.replace_substring_filter("界")
    filtered = directory_listing_rows(listing)
    assert tuple(row.text for row in render_table(filtered).rows) == (
        f"{'name':<4}  {'size':>12}  {'modified':<20}",
        f"界é {' ' * 14}  1970-01-01T00:00:01Z",
    )
    assert filtered[1].presentations == (member_presentations[2],)

    listing.replace_substring_filter("absent")
    no_match = directory_listing_rows(listing)
    assert tuple(row.text for row in render_table(no_match).rows)[-1] == (
        "Nothing matches the active filters."
    )
    assert no_match[-1].presentations == ()
    assert no_match[-1].listing_owner is listing


def test_empty_directory_table_always_keeps_header_and_empty_sentence(domain_types):
    listing = DirectoryListing(DirectoryRef("/empty"), ())
    header, _members = bind_listing_presentations(listing, domain_types)

    for mutate in (
        lambda: None,
        lambda: listing.replace_sort_key("size"),
        lambda: listing.replace_substring_filter("missing"),
        lambda: listing.replace_kind_filter("files"),
    ):
        mutate()
        rows = directory_listing_rows(listing)
        assert tuple(row.text for row in render_table(rows).rows) == (
            f"{'name':<4}  {'size':>12}  {'modified':<20}",
            "Directory is empty: /empty",
        )
        assert rows[0].presentations == (header,)
        assert rows[1].presentations == ()
        assert all(row.listing_owner is listing for row in rows)


def test_process_table_fixed_cells_truncate_at_the_final_display_cell(
    domain_types,
):
    long_user = "a" * 13 + "é界x"
    long_command = "x" * 46 + "界needle"
    listing = ProcessListing(
        (
            ProcessListingMember(ProcessRef(2), "sleeping", 1000, "alice", "short"),
            ProcessListingMember(
                ProcessRef(700), "running", 1000, long_user, long_command
            ),
        )
    )
    with pytest.raises(ValueError, match="not bound"):
        process_listing_rows(listing)
    header, member_presentations = bind_listing_presentations(listing, domain_types)

    rows = process_listing_rows(listing)
    rendered = render_table(rows)
    texts = tuple(row.text for row in rendered.rows)
    assert texts == (
        f"{'pid':>10}  {'state':<10}  {'user':<16}  {'command':<48}",
        f"{2:>10}  {'sleeping':<10}  {'alice':<16}  {'short':<48}",
        f"{700:>10}  {'running':<10}  {'a' * 13 + 'é …'}  "
        f"{'x' * 46 + ' …'}",
    )
    assert all(display_width(text) == 90 for text in texts)
    for row_number, presentation in enumerate(
        (header, member_presentations[0], member_presentations[1])
    ):
        assert rows[row_number].presentations == (presentation,)
        assert all(
            rendered.hit_test(column, row_number) is presentation
            for column in range(90)
        )
    assert all(
        presentation.presentation_type is not domain_types.text
        for row in rows
        for presentation in row.presentations
    )
    assert listing.members[1].displayed_user == long_user
    assert listing.members[1].command == long_command

    listing.replace_substring_filter("needle")
    filtered = process_listing_rows(listing)
    assert filtered[1].presentations == (member_presentations[1],)
    assert render_table(filtered).rows[1].text.endswith("x" * 46 + " …")


def test_process_table_empty_filter_states_and_width_rejections(domain_types):
    listing = ProcessListing(())
    header, _members = bind_listing_presentations(listing, domain_types)
    rows = process_listing_rows(listing)
    assert tuple(row.text for row in render_table(rows).rows) == (
        f"{'pid':>10}  {'state':<10}  {'user':<16}  {'command':<48}",
        "No processes are available.",
    )
    assert rows[0].presentations == (header,)
    assert rows[1].presentations == ()

    listing.replace_sort_key("command")
    assert render_table(process_listing_rows(listing)).rows[-1].text == (
        "No processes are available."
    )
    listing.replace_kind_filter("running")
    assert render_table(process_listing_rows(listing)).rows[-1].text == (
        "Nothing matches the active filters."
    )
    listing.widen()
    listing.replace_substring_filter("missing")
    assert render_table(process_listing_rows(listing)).rows[-1].text == (
        "Nothing matches the active filters."
    )

    impossible = ProcessListing(
        (
            ProcessListingMember(
                ProcessRef(12_345_678_901), "running", 1, "user", "command"
            ),
        )
    )
    bind_listing_presentations(impossible, domain_types)
    with pytest.raises(ValueError, match="pid value exceeds 10 display cells"):
        process_listing_rows(impossible)


def test_pure_display_helpers_keep_wide_and_combining_clusters_intact():
    assert display_width("Aé界") == 4
    assert truncate_display("界x", 2) == "…"
    assert truncate_display("Aé界Z", 4) == "Aé…"
    assert not truncate_display("Aé界Z", 4).endswith("e…")


def test_pure_listings_start_unbound_and_binding_preserves_stable_identity(
    domain_types,
):
    directory = DirectoryListing(DirectoryRef("/items"), directory_listing_members())
    process = ProcessListing(process_listing_members())

    assert directory.header_presentation is None
    assert directory.member_presentations == ()
    assert process.header_presentation is None
    assert process.member_presentations == ()

    contexts = make_domain_drawing_contexts(domain_types)
    directory_header = presentation_for(
        contexts.listing, directory, domain_types.directory_listing
    )
    directory_presentations = tuple(
        presentation_for(
            contexts.listing,
            member.reference,
            domain_types.file
            if type(member.reference) is FileRef
            else domain_types.directory,
        )
        for member in directory.members
    )
    process_header = presentation_for(
        contexts.listing, process, domain_types.process_listing
    )
    process_presentations = tuple(
        presentation_for(contexts.listing, member.reference, domain_types.process)
        for member in process.members
    )

    directory.bind_presentations(
        directory_header, directory_presentations, domain_types
    )
    process.bind_presentations(process_header, process_presentations, domain_types)

    assert directory.header_presentation is directory_header
    assert directory.member_presentations is directory_presentations
    assert process.header_presentation is process_header
    assert process.member_presentations is process_presentations
    assert directory_header.value is directory
    assert process_header.value is process
    assert [item.value for item in directory_presentations] == [
        member.reference for member in directory.members
    ]
    assert [item.value for item in process_presentations] == [
        member.reference for member in process.members
    ]
    assert len(
        {
            directory_header.id,
            *(item.id for item in directory_presentations),
        }
    ) == 1 + len(directory_presentations)
    assert len(
        {process_header.id, *(item.id for item in process_presentations)}
    ) == 1 + len(process_presentations)

    owned_before = (
        directory.header_presentation,
        directory.member_presentations,
        process.header_presentation,
        process.member_presentations,
    )
    directory.replace_sort_key("mtime")
    directory.replace_kind_filter("files")
    process.replace_sort_key("command")
    process.replace_kind_filter("running")
    assert (
        directory.header_presentation,
        directory.member_presentations,
        process.header_presentation,
        process.member_presentations,
    ) == owned_before

    with pytest.raises(ValueError, match="already bound"):
        directory.bind_presentations(
            directory_header, directory_presentations, domain_types
        )


def test_listing_binding_rejects_invalid_owned_sets_atomically(domain_types):
    context = make_domain_drawing_contexts(domain_types).listing

    def fresh_directory():
        references = (FileRef("/one"), DirectoryRef("/two"))
        listing = DirectoryListing(
            DirectoryRef("/"),
            (
                DirectoryListingMember(references[0], "one", 1, 10),
                DirectoryListingMember(references[1], "two", None, 20),
            ),
        )
        header = presentation_for(context, listing, domain_types.directory_listing)
        valid = (
            presentation_for(context, references[0], domain_types.file),
            presentation_for(context, references[1], domain_types.directory),
        )
        return listing, header, valid

    invalid_bindings = []
    listing, header, valid = fresh_directory()
    invalid_bindings.append((listing, header, valid[:1]))
    listing, header, valid = fresh_directory()
    invalid_bindings.append((listing, header, tuple(reversed(valid))))
    listing, header, valid = fresh_directory()
    wrong_value = presentation_for(context, FileRef("/other"), domain_types.file)
    invalid_bindings.append((listing, header, (wrong_value, valid[1])))
    listing, header, valid = fresh_directory()
    wrong_type = presentation_for(
        context, listing.members[0].reference, domain_types.file
    )
    wrong_type.presentation_type = domain_types.directory
    invalid_bindings.append((listing, header, (wrong_type, valid[1])))

    for listing, header, members in invalid_bindings:
        with pytest.raises(ValueError):
            listing.bind_presentations(header, members, domain_types)
        assert listing.header_presentation is None
        assert listing.member_presentations == ()

    shared_reference = ProcessRef(7)
    duplicate_listing = ProcessListing(
        (
            ProcessListingMember(
                shared_reference, "running", 1, "user", "first"
            ),
            ProcessListingMember(
                shared_reference, "sleeping", 1, "user", "second"
            ),
        )
    )
    duplicate_header = presentation_for(
        context, duplicate_listing, domain_types.process_listing
    )
    duplicate_member = presentation_for(
        context, shared_reference, domain_types.process
    )
    with pytest.raises(ValueError, match="ids must be unique"):
        duplicate_listing.bind_presentations(
            duplicate_header,
            (duplicate_member, duplicate_member),
            domain_types,
        )
    assert duplicate_listing.header_presentation is None
    assert duplicate_listing.member_presentations == ()

    listing, wrong_header, valid = fresh_directory()
    wrong_header.presentation_type = domain_types.process_listing
    with pytest.raises(ValueError, match="header presentation"):
        listing.bind_presentations(wrong_header, valid, domain_types)
    assert listing.header_presentation is None
    assert listing.member_presentations == ()
