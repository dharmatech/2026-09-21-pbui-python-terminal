"""Headless Python evaluator and Value presentation behavior."""

from __future__ import annotations

import sys
from dataclasses import dataclass

from pbui.commands import HeadlessListener, RootedFilesystem
from pbui.repl import ValueTranslator
from pbui.text import display_width, layout


@dataclass
class EmptyProcesses:
    own_uid: int = 1000
    own_pid: int = 700

    def list_for_uid(self, uid):
        return ()


def listener_at(tmp_path):
    return HeadlessListener(str(tmp_path), RootedFilesystem(tmp_path), EmptyProcesses())


def drawings(listener):
    # These predecessor assertions concern result rows.
    return tuple(
        row.text for row in layout(listener.history, 10000).rows
        if not listener.history.rows[row.logical_row].presentations
        or listener.history.rows[row.logical_row].presentations[0].type not in (
            listener.types.python_input,
            listener.types.command_input,
            listener.types.menu_action_input,
        )
    )


def values(listener):
    return tuple(p for p in listener.history.presentations if p.type is listener.types.value)



def result_rows(listener):
    """Rows covered by the predecessor result/listing assertions."""
    input_types = {
        listener.types.python_input,
        listener.types.command_input,
        listener.types.menu_action_input,
    }
    return tuple(
        row for row in listener.history.rows
        if not row.presentations or row.presentations[0].type not in input_types
    )



def test_python_bindings_results_and_colon_command_dispatch(tmp_path):
    listener = listener_at(tmp_path)
    assert listener.python_namespace == {"__name__": "__pbui__"}
    listener.submit("1 + 1")
    assert drawings(listener) == ("int 2",)
    assert values(listener)[0].value is listener.python_namespace["_"]
    listener.submit("import math")
    assert drawings(listener) == ("int 2",)
    listener.submit("math.sqrt(4)")
    assert drawings(listener)[-1] == "float 2.0"
    listener.submit("ls")
    assert drawings(listener)[-1].startswith("Error: Traceback")
    assert drawings(listener)[-1].endswith("Use :ls to run the listener command.")
    assert not any(row.listing_owner is not None for row in result_rows(listener))
    listener.submit(":ls")
    assert any(row.listing_owner is not None for row in result_rows(listener))
    listener.submit(": sort name")
    listener.submit(":ls()")
    assert drawings(listener)[-1] == "Error: unknown command: ls()."
    listener.submit("ls()")
    assert "Use :ls" not in drawings(listener)[-1]


def test_colon_arguments_and_modal_accept(tmp_path):
    child = tmp_path / "child"
    child.mkdir()
    listener = listener_at(tmp_path)
    listener.submit(f": ls {child}")
    assert any(row.listing_owner is not None for row in result_rows(listener))
    listener.submit(":rm")
    assert listener.pending_request is not None
    listener.cancel()
    assert listener.pending_request is None
    listener.submit("   :    ")
    assert listener.input_text == ""


def test_continuation_keeps_blank_and_colon_lines_as_python_and_cancels(tmp_path):
    listener = listener_at(tmp_path)
    listener.submit("if True:")
    assert listener.pending_python_source == "if True:"
    listener.submit("")
    assert listener.pending_python_source == "if True:\n"
    listener.submit(":ls")
    assert listener.pending_python_source == ""
    assert drawings(listener)[-1].startswith("Error: SyntaxError:")
    assert not any(row.listing_owner is not None for row in result_rows(listener))
    for cancel in (listener.cancel, listener.cancel_python_continuation, listener.cancel_python_continuation):
        listener.submit("if True:")
        listener.set_input_text("    pass")
        before = tuple(result_rows(listener))
        cancel()
        assert listener.pending_python_source == ""
        assert listener.input_text == ""
        assert result_rows(listener) == before
    listener.submit("3")
    assert drawings(listener)[-1] == "int 3"


def test_streams_values_and_exception_keep_program_order_and_restore(tmp_path):
    listener = listener_at(tmp_path)
    before = sys.displayhook, sys.stdout, sys.stderr
    listener.submit('print("a"); 1')
    assert drawings(listener) == ("a", "int 1")
    listener.submit("print()")
    assert drawings(listener)[-1] == ""
    listener.submit("import sys")
    listener.submit('sys.stderr.write("bad\\tline\\n")')
    assert drawings(listener)[-2:] == (r"stderr: bad\tline", "int 9")
    listener.submit('sys.displayhook(5); sys.displayhook(None); sys.displayhook(6)')
    assert drawings(listener)[-2:] == ("int 5", "int 6")
    assert listener.python_namespace["_"] == 6
    listener.submit('sys.displayhook(7); print("tail", end=""); raise SystemExit("done")')
    assert drawings(listener)[-3] == "int 7"
    assert drawings(listener)[-2] == "tail"
    assert drawings(listener)[-1].startswith("Error: Traceback")
    assert listener.python_namespace["_"] == 7
    assert (sys.displayhook, sys.stdout, sys.stderr) == before


def test_compile_and_execution_errors_are_single_escaped_rows(tmp_path):
    listener = listener_at(tmp_path)
    before = sys.displayhook, sys.stdout, sys.stderr
    listener.submit("if =")
    assert len(result_rows(listener)) == 1
    assert drawings(listener)[-1].startswith("Error: SyntaxError:")
    assert "\\n" not in drawings(listener)[-1]
    listener.submit('print("first"); raise ValueError("bad\\nline")')
    assert drawings(listener)[-2] == "first"
    assert "ValueError: bad\\nline" in drawings(listener)[-1]
    assert (sys.displayhook, sys.stdout, sys.stderr) == before
    listener.submit("4")
    assert drawings(listener)[-1] == "int 4"


def test_traceback_cap_preserves_final_line_and_cuts_huge_exception(tmp_path, monkeypatch):
    import pbui.repl as repl

    listener = listener_at(tmp_path)
    monkeypatch.setattr(repl.traceback, "format_list", lambda frames: ["frame" * 1000] * 8)
    listener.submit('raise RuntimeError("short")')
    stored = listener.history.presentations[-1].value
    assert display_width(stored) <= 4096
    assert stored.endswith("RuntimeError: short")
    listener.submit('raise RuntimeError("x" * 5000)')
    stored = listener.history.presentations[-1].value
    assert display_width(stored) == 4096
    assert stored.startswith("RuntimeError: ")
    assert stored.endswith("…")


def test_repr_fallback_bounded_display_and_identity(tmp_path):
    listener = listener_at(tmp_path)

    class Bad:
        def __repr__(self):
            raise RuntimeError("repr failed")

    bad = Bad()
    listener.python_namespace["bad"] = bad
    listener.submit("bad")
    assert values(listener)[0].value is bad
    assert drawings(listener)[0] == "Bad <repr unavailable>"
    assert "RuntimeError: repr failed" in drawings(listener)[1]
    assert listener.python_namespace["_"] is bad
    listener.submit("'ok'")
    assert drawings(listener)[-1] == "str 'ok'"
    listener.submit("'a' * 1000")
    assert display_width(drawings(listener)[-1].removeprefix("str ")) <= 96
    listener.submit("'a\\n\\t\\ud800'")
    assert r"\\n\\t\\ud800" in drawings(listener)[-1]
    assert "\n" not in drawings(listener)[-1]


def test_class_mro_printer_translators_and_exact_acceptance(tmp_path):
    listener = listener_at(tmp_path)

    class Base:
        pass

    class Child(Base):
        pass

    original = Child()
    seen = []
    listener.register_python_class(object, lambda value: "object printer")
    listener.register_python_class(
        Base,
        lambda value: "base\nprinter",
        (ValueTranslator("to none", lambda value: seen.append(value)),
         ValueTranslator("fail", lambda value: 1 / 0)),
    )
    listener.python_namespace["item"] = original
    listener.submit("item")
    presentation = values(listener)[0]
    assert presentation.value is original
    assert drawings(listener)[0] == r"base\nprinter"
    assert [item.label for item in listener.python_translators_for(presentation)] == ["to none", "fail"]
    for command in ("show", "rm", "cd", "kill"):
        assert listener.types.value not in listener._acceptable_types(command)
    translated = listener.invoke_python_translator(presentation, 0)
    assert seen == [original]
    assert translated is not None and translated.value is None
    assert listener.python_namespace["_"] is None
    assert drawings(listener)[-1] == "object printer"
    previous_rows = len(result_rows(listener))
    listener.invoke_python_translator(presentation, 1)
    assert len(result_rows(listener)) == previous_rows + 1
    assert "ZeroDivisionError" in drawings(listener)[-1]
    assert listener.python_namespace["_"] is None


def test_output_rows_are_escaped_and_capped(tmp_path):
    listener = listener_at(tmp_path)
    listener.submit('print("x" * 5000)')
    stored = listener.history.presentations[-1].value
    assert display_width(stored) == 4096
    assert stored.endswith("…")
    listener.submit('import sys; sys.stderr.write("\\x01\\n\\n")')
    assert drawings(listener)[-3:-1] == (r"stderr: \x01", "stderr: ")
    assert listener.history.presentations[-3].type is listener.types.text


def test_registered_printer_failure_keeps_one_value_and_translator_result_uses_lookup(tmp_path):
    listener = listener_at(tmp_path)

    class Broken:
        pass

    original = Broken()
    listener.register_python_class(
        Broken,
        lambda value: (_ for _ in ()).throw(RuntimeError("printer broke")),
        (ValueTranslator("convert", lambda value: 12),),
    )
    listener.python_namespace["item"] = original
    listener.submit("item")
    assert len(values(listener)) == 1
    assert values(listener)[0].value is original
    assert drawings(listener)[0] == "Broken <repr unavailable>"
    assert "RuntimeError: printer broke" in drawings(listener)[1]
    assert listener.python_namespace["_"] is original
    converted = listener.invoke_python_translator(values(listener)[0], 0)
    assert converted is values(listener)[-1]
    assert converted.value == 12
    assert drawings(listener)[-1] == "int 12"
    assert listener.python_namespace["_"] == 12


def test_value_detail_is_bounded_retains_identity_and_does_not_extend_show(tmp_path):
    listener = listener_at(tmp_path)
    original = list(range(100))
    listener.python_namespace["original"] = original
    listener.submit("original")
    target = values(listener)[0]
    assert target.value is original
    assert "..." in drawings(listener)[0]
    assert listener.select(target)
    detail = drawings(listener)[-1]
    assert detail.startswith("list: [0, 1, 2,")
    assert "63" in detail and "64" not in detail
    assert listener.python_namespace["_"] is original
    listener.submit(":show")
    assert listener.pending_request is not None
    assert not listener.select(target)
    assert listener.chip is None
    assert listener.pending_request is not None
    listener.cancel()

    class Broken:
        def __repr__(self):
            raise RuntimeError("detail failed")

    broken = Broken()
    listener.register_python_class(Broken, lambda value: "safe printer")
    listener.python_namespace["broken"] = broken
    listener.submit("broken")
    target = values(listener)[-1]
    assert listener.python_namespace["_"] is broken
    assert listener.select(target)
    assert listener.history.presentations[-1].type is listener.types.error
    assert "RuntimeError: detail failed" in drawings(listener)[-1]
    assert listener.python_namespace["_"] is broken
    assert target.value is broken
