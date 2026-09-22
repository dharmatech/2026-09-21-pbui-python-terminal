from __future__ import annotations

import os
from dataclasses import FrozenInstanceError

import pytest

from pbui.domain import (
    DirectoryRef,
    DomainParseError,
    FileRef,
    OSReadOnlyPathAccess,
    ProcessRef,
    TypedDomainValue,
    classify_path,
    compose_failure_message,
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
    register_domain_types,
    sort_path_references,
)
from pbui.substrate import PresentationHistory, PresentationTypeRegistry
from pbui.text import DrawingContext, layout


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


def test_registers_exact_five_domain_types_in_order_and_by_identity():
    registry = PresentationTypeRegistry()
    types = register_domain_types(registry)

    assert [entry.name for entry in registry] == [
        "File",
        "Directory",
        "Process",
        "Text",
        "Error",
    ]
    assert len({id(entry) for entry in registry}) == 5
    assert types.file is registry.lookup("File")
    assert types.directory is registry.lookup("Directory")
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
