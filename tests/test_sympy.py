"""SymPy Expr presentation through the headless listener."""

from __future__ import annotations

import sympy

from pbui.chips import PythonChip
from pbui.commands import HeadlessListener, RootedFilesystem
from pbui.repl import ValueTranslator
from pbui.text import display_width, layout


class EmptyProcesses:
    own_uid = 1000
    own_pid = 700

    def list_for_uid(self, uid):
        return ()


def listener_at(tmp_path):
    return HeadlessListener(str(tmp_path), RootedFilesystem(tmp_path), EmptyProcesses())


def drawings(listener):
    return tuple(row.text for row in layout(listener.history, 10000).rows)


def values(listener):
    return tuple(p for p in listener.history.presentations if p.type is listener.types.value)


def test_namespace_symbolic_row_and_one_line_detail(tmp_path):
    listener = listener_at(tmp_path)
    assert listener.python_namespace == {"__name__": "__pbui__"}
    listener.submit("import sympy")
    assert listener.python_namespace["sympy"] is sympy
    assert not values(listener)
    listener.submit("sympy.sqrt(8)")
    target = values(listener)[0]
    assert isinstance(target.value, sympy.Expr)
    assert target.value is listener.python_namespace["_"]
    assert drawings(listener) == (sympy.pretty(target.value, use_unicode=True, wrap_line=False),)
    assert not drawings(listener)[0].startswith(type(target.value).__name__)
    assert listener.select(target)
    assert drawings(listener)[-1] == sympy.pretty(target.value, use_unicode=True, wrap_line=False)
    assert listener.python_namespace["_"] is target.value


def test_actions_keep_source_and_forward_result_as_chip(tmp_path):
    listener = listener_at(tmp_path)
    listener.submit("import sympy")
    listener.submit("x = sympy.Symbol('x')")
    listener.submit("(x + 1)**2")
    source = values(listener)[-1]
    original = source.value
    assert [entry.label for entry in listener.python_translators_for(source)] == [
        "simplify", "expand", "factor"
    ]
    expanded = listener.invoke_python_translator(source, 1)
    assert expanded is values(listener)[-1]
    assert expanded.value == listener.python_namespace["x"]**2 + 2*listener.python_namespace["x"] + 1
    assert source.value is original
    assert listener.python_namespace["_"] is expanded.value
    listener.set_input_text("id(")
    assert listener.select_for_input(expanded)
    chip = next(piece for piece in listener.python_pieces if isinstance(piece, PythonChip))
    assert chip.value is expanded.value
    listener.insert_python_text(") == id(_)")
    listener.submit()
    assert drawings(listener)[-1] == "bool True"

    listener.submit("x**2 - 1")
    source = values(listener)[-1]
    original = source.value
    factored = listener.invoke_python_translator(source, 2)
    x = listener.python_namespace["x"]
    assert factored.value == (x - 1)*(x + 1)
    assert factored.value is listener.python_namespace["_"]
    assert source.value is original

    listener.submit("sympy.sin(x)**2 + sympy.cos(x)**2")
    source = values(listener)[-1]
    simplified = listener.invoke_python_translator(source, 0)
    assert simplified.value == sympy.Integer(1)
    assert simplified.value is listener.python_namespace["_"]
    assert source.value is not simplified.value


def test_generic_objects_and_test_only_none_failure(tmp_path):
    listener = listener_at(tmp_path)
    listener.submit("import sympy")
    listener.submit("42")
    listener.submit("sympy.Matrix([[1]])")
    original = object()
    listener.python_namespace["item"] = original
    listener.submit("item")
    for target in values(listener):
        assert not listener.python_translators_for(target)
        assert listener.select(target)
        assert drawings(listener)[-1].startswith(f"{type(target.value).__name__}: ")

    class TestValue:
        pass

    seen = []
    listener.register_python_class(
        TestValue, lambda value: "test value",
        (
            ValueTranslator("none", lambda value: seen.append(value)),
            ValueTranslator("fail", lambda value: (_ for _ in ()).throw(RuntimeError("broken"))),
        ),
    )
    custom = TestValue()
    listener.python_namespace["custom"] = custom
    listener.submit("custom")
    target = values(listener)[-1]
    previous = listener.python_namespace["_"]
    before = len(listener.history.rows)
    assert listener.invoke_python_translator(target, 1) is None
    assert len(listener.history.rows) == before + 1
    assert drawings(listener)[-1].endswith("RuntimeError: broken")
    assert listener.python_namespace["_"] is previous
    assert values(listener)[-1] is target
    returned = listener.invoke_python_translator(target, 0)
    assert seen == [custom]
    assert returned.value is None
    assert listener.python_namespace["_"] is None
    assert target.value is custom
    assert [entry.label for entry in listener.python_translators_for(target)] == ["none", "fail"]


def test_multiline_row_and_bounded_detail(tmp_path, monkeypatch):
    import pbui.repl as repl

    listener = listener_at(tmp_path)
    expression = sympy.Symbol("x")
    listener.python_namespace["expression"] = expression
    pretty = "first\n\n" + "a" * 130 + "\x01\t" + "\n" + "\n".join(f"line {i}" for i in range(24))
    lines = pretty.split("\n")
    assert len(lines) == 27
    monkeypatch.setattr(repl.sympy, "pretty", lambda *args, **kwargs: pretty)
    listener.submit("expression")
    target = values(listener)[-1]
    assert target.value is expression
    assert drawings(listener)[0] == sympy.sstr(expression)
    assert listener.select(target)
    detail = drawings(listener)[1:]
    assert len(detail) == 25
    assert detail[0] == "first"
    assert detail[1] == ""
    assert display_width(detail[2]) == 120
    assert detail[2].endswith("…")
    assert detail[-1] == "… (3 more lines)"
    assert listener.python_namespace["_"] is expression


def test_control_escaping_and_printer_detail_failures(tmp_path, monkeypatch):
    import pbui.repl as repl

    listener = listener_at(tmp_path)
    expression = sympy.Symbol("x")
    listener.python_namespace["expression"] = expression
    monkeypatch.setattr(repl.sympy, "pretty", lambda *args, **kwargs: "a\x01\t\ud800\nb")
    listener.submit("expression")
    target = values(listener)[0]
    assert drawings(listener)[0] == sympy.sstr(expression)
    assert listener.select(target)
    assert drawings(listener)[1:3] == (r"a\x01\t\ud800", "b")
    assert target.value is expression

    def broken(*args, **kwargs):
        raise RuntimeError("pretty failed")

    monkeypatch.setattr(repl.sympy, "pretty", broken)
    before = len(listener.history.rows)
    assert listener.select(target)
    assert len(listener.history.rows) == before + 1
    assert drawings(listener)[-1].endswith("RuntimeError: pretty failed")
    assert listener.python_namespace["_"] is expression

    listener.submit("expression")
    assert values(listener)[-1].value is expression
    assert drawings(listener)[-2] == "Symbol <repr unavailable>"
    assert drawings(listener)[-1].endswith("RuntimeError: pretty failed")
    assert listener.python_namespace["_"] is expression


def test_sstr_failure_and_translator_result_printer_failure(tmp_path, monkeypatch):
    import pbui.repl as repl

    listener = listener_at(tmp_path)
    expression = sympy.Symbol("x")
    listener.python_namespace["expression"] = expression
    monkeypatch.setattr(repl.sympy, "pretty", lambda *args, **kwargs: "top\nbottom")
    def broken_sstr(value):
        raise RuntimeError("sstr failed")
    monkeypatch.setattr(repl.sympy, "sstr", broken_sstr)
    listener.submit("expression")
    assert drawings(listener)[0] == "Symbol <repr unavailable>"
    assert drawings(listener)[1].endswith("RuntimeError: sstr failed")
    assert values(listener)[0].value is expression

    class BrokenResult:
        pass

    result = BrokenResult()
    listener.register_python_class(BrokenResult, lambda value: (_ for _ in ()).throw(RuntimeError("print failed")))

    class Source:
        pass

    listener.register_python_class(Source, lambda value: "source", (ValueTranslator("convert", lambda value: result),))
    source = Source()
    listener.python_namespace["source"] = source
    listener.submit("source")
    target = values(listener)[-1]
    converted = listener.invoke_python_translator(target, 0)
    assert converted.value is result
    assert listener.python_namespace["_"] is result
    assert drawings(listener)[-2] == "BrokenResult <repr unavailable>"
    assert drawings(listener)[-1].endswith("RuntimeError: print failed")
    assert target.value is source


def test_one_line_row_and_detail_share_120_cell_cap(tmp_path, monkeypatch):
    import pbui.repl as repl

    listener = listener_at(tmp_path)
    expression = sympy.Symbol("x")
    listener.python_namespace["expression"] = expression
    monkeypatch.setattr(repl.sympy, "pretty", lambda *args, **kwargs: "界" * 70)
    listener.submit("expression")
    target = values(listener)[0]
    assert display_width(drawings(listener)[0]) == 119
    assert drawings(listener)[0].endswith("…")
    assert listener.select(target)
    assert drawings(listener)[1] == drawings(listener)[0]
    assert target.value is expression
