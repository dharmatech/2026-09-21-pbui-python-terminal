"""Headless completion of command tokens and live Python names."""

from __future__ import annotations

import math
import sys
from types import SimpleNamespace

import pytest

from pbui.chips import PythonChip
from pbui.commands import HeadlessListener, RootedFilesystem


class EmptyProcesses:
    own_uid = 1000
    own_pid = 700

    def list_for_uid(self, uid):
        return ()


def listener_at(tmp_path):
    return HeadlessListener(str(tmp_path), RootedFilesystem(tmp_path), EmptyProcesses())


def test_colon_registry_site_edit_and_arguments(tmp_path):
    listener = listener_at(tmp_path)
    listener.set_input_text(":")
    assert listener.completion_candidates() == tuple(sorted(listener.command_names))
    assert listener.complete() == tuple(sorted(listener.command_names))
    assert listener.input_text == ":"
    listener.set_input_text("  : so")
    assert listener.complete() == ("sort",)
    assert listener.input_text == "  : sort"
    assert listener.command_cursor == len(listener.input_text)
    listener.set_input_text(":sorx")
    listener.set_command_cursor(4)
    assert listener.complete() == ("sort",)
    assert listener.input_text == ":sort"
    assert listener.command_cursor == 5
    assert listener.python_pieces == (":sort",)
    for text in (":ls ", ":ls foo", ":ls /tmp", ":get https://example.org"):
        listener.set_input_text(text)
        before = (listener.input_text, listener.command_cursor)
        assert listener.complete() == ()
        assert (listener.input_text, listener.command_cursor) == before
    listener.set_input_text(":so")
    assert not listener.apply_completion("sort", menu_open=True)
    assert listener.input_text == ":so"


def test_bare_namespace_builtin_keyword_and_stale_choice(tmp_path):
    listener = listener_at(tmp_path)
    listener.python_namespace["alpha_value"] = 3
    listener.set_input_text("alpha_v")
    assert listener.complete() == ("alpha_value",)
    assert listener.input_text == "alpha_value"
    listener.set_input_text("prin")
    assert listener.completion_candidates() == ("print",)
    listener.set_input_text("retur")
    assert listener.complete() == ("return",)
    listener.set_input_text("prin")
    assert not listener.apply_completion("return")
    assert listener.apply_completion("print")
    assert listener.input_text == "print"
    listener.set_input_text("")
    assert listener.completion_candidates() == ()
    assert listener.complete() == ()
    assert listener.input_text == ""


def test_namespace_shadowing_and_bound_module_attributes(tmp_path):
    listener = listener_at(tmp_path)
    listener.python_namespace["list"] = SimpleNamespace(append_custom=1)
    listener.set_input_text("list.append_c")
    assert listener.complete() == ("append_custom",)
    assert listener.input_text == "list.append_custom"
    listener.python_namespace["math"] = math
    listener.set_input_text("math.sq")
    assert listener.complete() == ("sqrt",)
    assert listener.input_text == "math.sqrt"


def test_chip_receiver_identity_and_surrounding_text(tmp_path):
    listener = listener_at(tmp_path)
    receiver = SimpleNamespace(apple=1)
    listener.python_namespace["receiver"] = receiver
    listener.submit("receiver")
    presentation = next(
        item for item in listener.history.presentations
        if item.type is listener.types.value
    )
    listener.set_input_text("f(")
    assert listener.select_for_input(presentation)
    chip = next(piece for piece in listener.python_pieces if isinstance(piece, PythonChip))
    listener.insert_python_text(".app, 2)")
    listener.set_python_cursor(7)
    assert listener.complete() == ("apple",)
    assert listener.python_pieces == ("f(", chip, ".apple, 2)")
    assert listener.python_pieces[1] is chip
    assert chip.value is receiver
    assert listener.python_cursor == 9


def test_underscore_filter_and_failing_or_ineligible_receiver(tmp_path):
    listener = listener_at(tmp_path)
    listener.python_namespace["obj"] = SimpleNamespace(_secret=1, visible=2)
    listener.set_input_text("obj.")
    assert listener.completion_candidates() == ("visible",)
    listener.set_input_text("obj._")
    assert "_secret" in listener.completion_candidates()
    listener.python_namespace["_private"] = 4
    listener.set_input_text("_priv")
    assert listener.completion_candidates() == ("_private",)

    class Broken:
        def __getattr__(self, name):
            raise RuntimeError("failed lookup")

        def __dir__(self):
            raise RuntimeError("failed dir")

    listener.python_namespace["broken"] = Broken()
    for text in (
        "unknown.ap", "broken.child.ap", "broken.ap", "make_object().ap",
        "obj[0].ap", "(obj).ap", "obj + other.ap",
    ):
        listener.set_input_text(text)
        before = (listener.input_text, listener.python_cursor)
        assert listener.complete() == ()
        assert (listener.input_text, listener.python_cursor) == before


def test_strings_comments_imports_and_unrelated_positions(tmp_path):
    listener = listener_at(tmp_path)
    listener.python_namespace["alpha"] = 1
    for text in (
        "'alpha'", '"alpha"', "# alpha", "value # alpha",
        "'unfinished alpha", '"""unfinished alpha',
        "x = 1 ",
    ):
        listener.set_input_text(text)
        before = (listener.input_text, listener.python_cursor)
        assert listener.complete() == ()
        assert (listener.input_text, listener.python_cursor) == before
    listener.submit("if True:")
    listener.set_input_text(":alpha")
    assert listener.complete() == ()
    assert listener.input_text == ":alpha"
    listener.set_input_text('    """unfinished alpha')
    before = (listener.input_text, listener.python_cursor)
    assert listener.complete() == ()
    assert (listener.input_text, listener.python_cursor) == before


def test_mid_token_shared_prefix_and_preserved_history_recall(tmp_path):
    listener = listener_at(tmp_path)
    listener.python_namespace.update(qalpha=1, qalpine=2)
    listener.submit("1 + 1")
    rows = listener.history.rows
    revision = listener.history.revision
    entries = listener.recall_entries
    listener.set_input_text("qa + 3")
    listener.set_python_cursor(2)
    assert listener.complete() == ("qalpha", "qalpine")
    assert listener.input_text == "qalp + 3"
    assert listener.python_cursor == 4
    assert listener.history.rows == rows
    assert listener.history.revision == revision
    assert listener.recall_entries == entries
    listener.set_input_text("qalphx + 3")
    listener.set_python_cursor(5)
    assert listener.complete() == ("qalpha",)
    assert listener.input_text == "qalpha + 3"
    assert listener.python_cursor == 6
    listener.set_input_text("qa")
    assert listener.recall_previous()
    position = listener.recall_position
    listener.set_input_text("qalph")
    assert listener.complete() == ("qalpha",)
    assert listener.recall_position == position
    assert listener.recall_entries == entries
    assert listener.recall_next()
    assert listener.input_text == "qa"


def test_accept_and_menu_guards_are_inert(tmp_path):
    listener = listener_at(tmp_path)
    listener.set_input_text(":so")
    snapshot = (listener.input_text, listener.command_cursor, listener.history.revision)
    assert listener.completion_candidates(menu_open=True) == ()
    assert listener.complete(menu_open=True) == ()
    assert not listener.apply_completion("sort", menu_open=True)
    assert (listener.input_text, listener.command_cursor, listener.history.revision) == snapshot

    listener.submit(":show")
    assert listener.pending_request is not None
    listener.set_input_text(":so")
    snapshot = (listener.input_text, listener.command_cursor, listener.history.revision)
    assert listener.completion_candidates() == ()
    assert listener.complete() == ()
    assert not listener.apply_completion("sort")
    assert (listener.input_text, listener.command_cursor, listener.history.revision) == snapshot
    listener.cancel()

    (tmp_path / "one").write_text("x")
    listener.submit(":ls")
    listener.submit(":narrow")
    assert listener.pending_substring_listing is not None
    listener.set_input_text("so")
    snapshot = (listener.input_text, listener.command_cursor, listener.history.revision)
    assert listener.completion_candidates() == ()
    assert listener.complete() == ()
    assert not listener.apply_completion("sort")
    assert (listener.input_text, listener.command_cursor, listener.history.revision) == snapshot



@pytest.fixture
def import_modules(tmp_path, monkeypatch):
    (tmp_path / "pbui_import_alpha.py").write_text("")
    (tmp_path / "pbui_import_alpine.py").write_text("")
    package = tmp_path / "pbui_import_pkg"
    package.mkdir()
    (package / "__init__.py").write_text("attribute_only = 1\n")
    (package / "mellow.py").write_text("")
    (package / "merry.py").write_text("")
    nested = package / "nested"
    nested.mkdir()
    (nested / "__init__.py").write_text("")
    (nested / "resources.py").write_text("")
    monkeypatch.syspath_prepend(str(tmp_path))
    return listener_at(tmp_path)


def test_import_top_level_discovery_shared_prefix_and_no_import(import_modules):
    listener = import_modules
    assert "pbui_import_alpha" not in sys.modules
    assert "pbui_import_alpine" not in sys.modules
    listener.set_input_text("import pbui_import_al")
    assert listener.complete() == ("pbui_import_alpha", "pbui_import_alpine")
    assert listener.input_text == "import pbui_import_alp"
    assert listener.python_cursor == len(listener.input_text)
    assert listener.apply_completion("pbui_import_alpha")
    assert listener.input_text == "import pbui_import_alpha"
    assert "pbui_import_alpha" not in sys.modules
    assert "pbui_import_alpha" not in listener.python_namespace
    assert "pbui_import_alpine" not in listener.python_namespace

    pathlib_loaded = "pathlib" in sys.modules
    listener.set_input_text("import pathl")
    assert listener.complete() == ("pathlib",)
    assert listener.input_text == "import pathlib"
    assert ("pathlib" in sys.modules) == pathlib_loaded
    assert "pathlib" not in listener.python_namespace


def test_dotted_import_and_later_comma_target(import_modules):
    listener = import_modules
    resources_loaded = "importlib.resources" in sys.modules
    listener.set_input_text("import importlib.res")
    assert listener.complete() == ("resources",)
    assert listener.input_text == "import importlib.resources"
    assert ("importlib.resources" in sys.modules) == resources_loaded
    assert "importlib" not in listener.python_namespace

    listener.set_input_text("import pbui_import_pkg.nest")
    assert listener.complete() == ("nested",)
    assert listener.input_text == "import pbui_import_pkg.nested"
    assert "pbui_import_pkg" not in sys.modules
    listener.set_input_text("import os, pbui_import_pkg.nested.res")
    assert listener.complete() == ("resources",)
    assert listener.input_text == "import os, pbui_import_pkg.nested.resources"
    assert "pbui_import_pkg.nested" not in sys.modules
    assert "pbui_import_pkg.nested.resources" not in sys.modules
    listener.set_input_text("import os as operating, pbui_import_al")
    assert listener.completion_candidates() == (
        "pbui_import_alpha", "pbui_import_alpine",
    )


def test_additional_children_and_empty_import_sites(import_modules):
    listener = import_modules
    listener.set_input_text("import os.pa")
    assert listener.complete() == ("path",)
    assert listener.input_text == "import os.path"
    listener.set_input_text("import collections.ab")
    assert listener.complete() == ("abc",)
    assert listener.input_text == "import collections.abc"
    listener.set_input_text("from os import pa")
    assert listener.complete() == ("path",)
    assert listener.input_text == "from os import path"
    listener.set_input_text("from pbui_import_pkg import ")
    assert {"mellow", "merry", "nested"} <= set(listener.completion_candidates())
    listener.set_input_text("import ")
    assert "pbui_import_pkg" in listener.completion_candidates()
    assert "pbui_import_pkg" not in sys.modules


def test_from_bound_attributes_unbound_submodules_and_continuation(import_modules):
    listener = import_modules
    listener.set_input_text("from math import sq")
    assert listener.completion_candidates() == ()
    assert "math" not in listener.python_namespace
    listener.python_namespace["math"] = math
    assert listener.complete() == ("sqrt",)
    assert listener.input_text == "from math import sqrt"

    listener.set_input_text("from pbui_import_pkg import me")
    assert listener.completion_candidates() == ("mellow", "merry")
    assert "pbui_import_pkg" not in sys.modules
    assert "pbui_import_pkg" not in listener.python_namespace
    listener.submit("from pbui_import_pkg import (")
    assert listener.pending_python_pieces
    listener.set_input_text("    me")
    assert listener.complete() == ("mellow", "merry")
    assert listener.input_text == "    me"
    assert listener.apply_completion("mellow")
    assert listener.input_text == "    mellow"
    assert "pbui_import_pkg.mellow" not in sys.modules


def test_import_refusal_mid_token_and_statement_boundaries(import_modules):
    listener = import_modules
    for text in (
        "import pbui_import_pkg as alias", "import pbui_import_pkg as al",
        "from pbui_import_pkg import mellow as al",
        "from .pbui_import_pkg import me",
        "from .. import me", "'import pbui_import_al'",
        "# import pbui_import_al", "import os; pbui_import_al",
        "import os\nnot_an_import = pbui_import_al",
    ):
        listener.set_input_text(text)
        before = (listener.input_text, listener.python_cursor)
        assert listener.complete() == ()
        assert (listener.input_text, listener.python_cursor) == before

    listener.set_input_text("import pbui_import_alxyz")
    listener.set_python_cursor(len("import pbui_import_al"))
    assert listener.complete() == ("pbui_import_alpha", "pbui_import_alpine")
    assert listener.input_text == "import pbui_import_alp"

    listener.set_input_text("import pbui_import_al")
    listener._python_line.insert_chip(PythonChip(object(), "opaque"))
    assert listener.completion_candidates() == ()
