"""Headless HTTP request, response, transport, and action behavior."""

from __future__ import annotations

import io
import urllib.error

import pytest

from pbui.commands import HeadlessListener, RootedFilesystem
from pbui.http import (
    MAX_BODY_BYTES, BodyTooLarge, GetRequest, GetResult, GetTransportError,
    HttpResponse, JsonArray, JsonObject, production_get,
)
from pbui.text import display_width, layout, stored_row_text
from pbui.transcript import CommandInput, MenuActionInput


class EmptyProcesses:
    pass


class FakeGet:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls: list[GetRequest] = []

    def __call__(self, request):
        self.calls.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def listener_at(tmp_path, transport, **kwargs):
    return HeadlessListener(
        str(tmp_path), RootedFilesystem(tmp_path), EmptyProcesses(),
        get_transport=transport, **kwargs,
    )


def records(listener):
    return [(row.presentations[0].type.name, row.presentations[0].value)
            for row in listener.history.rows if row.presentations]


def rows(listener):
    return tuple(stored_row_text(row) for row in listener.history.rows)


def actions(listener, presentation):
    return [item.label for item in listener.python_translators_for(presentation)]


def result(body=b'ok', *, status=200, url='https://final.example/path', headers=None):
    return GetResult(status, url, headers or {'Content-Type': 'text/plain'}, body)


def test_get_is_inert_preserves_argument_and_python_import(tmp_path):
    fake = FakeGet()
    listener = listener_at(tmp_path, fake)
    listener.submit('7')
    previous = listener.python_namespace['_']
    listener.submit(':get https://example.org/a  b ')
    assert [kind for kind, _ in records(listener)][-2:] == ['CommandInput', 'Value']
    request = records(listener)[-1][1]
    assert request == GetRequest('https://example.org/a  b ')
    assert request.method == 'GET'
    assert rows(listener)[-1] == 'GET https://example.org/a  b '
    assert listener.python_namespace['_'] == previous
    assert fake.calls == []
    assert actions(listener, listener.history.presentations[-1]) == ['perform']

    listener.submit(':get')
    assert [kind for kind, _ in records(listener)][-2:] == ['CommandInput', 'Error']
    listener.submit(':get ')
    assert [kind for kind, _ in records(listener)][-2:] == ['CommandInput', 'Error']
    listener.submit('get')
    assert rows(listener)[-1].endswith('Use :get to run the listener command.')
    assert fake.calls == []

    listener.submit('from pbui.http import GetRequest')
    listener.submit('GetRequest("https://example.org/")')
    imported = listener.history.presentations[-1].value
    assert isinstance(imported, GetRequest)
    assert listener.python_namespace['_'] is imported
    assert rows(listener)[-1] == 'GET https://example.org/'


def test_perform_repeats_and_keeps_request_and_transcript(tmp_path):
    fake = FakeGet(result(), result(status=404, body=b'not found'), result())
    listener = listener_at(tmp_path, fake)
    listener.submit(':get https://example.org/')
    request_row = listener.history.rows[-1]
    request = request_row.presentations[0]
    first = listener.invoke_python_translator(request, 0)
    assert [kind for kind, _ in records(listener)][-2:] == ['MenuActionInput', 'Value']
    assert [item.label for item in listener.python_translators_for(first)] == ['body']
    assert first.value == HttpResponse(200, 'https://final.example/path', 'text/plain', b'ok')
    assert rows(listener)[-1] == 'HTTP 200 https://final.example/path'
    assert listener.python_namespace['_'] is first.value
    assert listener.history.rows[1] is request_row

    second = listener.invoke_python_translator(request, 0)
    assert second.value.status == 404
    assert second is not first
    assert listener.history.rows[1] is request_row
    action = next(p for p in reversed(listener.history.presentations)
                  if p.type is listener.types.menu_action_input)
    assert listener.run_again(action)
    assert [kind for kind, _ in records(listener)][-2:] == ['MenuActionInput', 'Value']
    assert fake.calls == [request.value] * 3
    assert all(call is request.value for call in fake.calls)
    assert listener.history.rows[1] is request_row


def test_perform_failures_invalid_url_and_fake_size_cap(tmp_path):
    fake = FakeGet(OSError('offline\nnow'), result(b'x' * (MAX_BODY_BYTES + 1)))
    listener = listener_at(tmp_path, fake)
    listener.submit('12')
    previous = listener.python_namespace['_']
    listener.submit(':get file:///etc/passwd')
    invalid = listener.history.presentations[-1]
    listener.invoke_python_translator(invalid, 0)
    assert [kind for kind, _ in records(listener)][-2:] == ['MenuActionInput', 'Error']
    assert fake.calls == []
    assert listener.python_namespace['_'] == previous

    listener.submit(':get https://example.org/')
    request = listener.history.presentations[-1]
    listener.invoke_python_translator(request, 0)
    assert [kind for kind, _ in records(listener)][-2:] == ['MenuActionInput', 'Error']
    assert r'offline\nnow' in rows(listener)[-1]
    assert listener.python_namespace['_'] == previous
    listener.invoke_python_translator(request, 0)
    assert [kind for kind, _ in records(listener)][-2:] == ['MenuActionInput', 'Error']
    assert 'exceeds' in rows(listener)[-1]
    assert len(fake.calls) == 2
    assert listener.python_namespace['_'] == previous

    for invalid_url in ('http://example.org:bad/', 'https://example.org/a b'):
        listener.submit(':get ' + invalid_url)
        bad = listener.history.presentations[-1]
        listener.invoke_python_translator(bad, 0)
        assert [kind for kind, _ in records(listener)][-2:] == ['MenuActionInput', 'Error']
    assert len(fake.calls) == 2

    redirect = FakeGet(result(status=302))
    other = listener_at(tmp_path, redirect)
    other.submit(':get https://example.org/')
    other.invoke_python_translator(other.history.presentations[-1], 0)
    assert [kind for kind, _ in records(other)][-2:] == ['MenuActionInput', 'Error']


@pytest.mark.parametrize('media_type', [
    ' application/json ; charset=utf-8', 'application/problem+json; charset=UTF-8',
])
def test_json_actions_types_identity_and_eviction(tmp_path, media_type):
    body = b'{"a":[null,true,3,1.25,2e2,{"deep":false}]}'
    fake = FakeGet(result(body, headers={'cOnTeNt-TyPe': media_type}))
    listener = listener_at(tmp_path, fake, history_max_rows=4)
    listener.submit(':get https://example.org/')
    request = listener.history.presentations[-1]
    response = listener.invoke_python_translator(request, 0)
    assert actions(listener, response) == ['json', 'body']
    before = len(listener.history.rows)
    assert actions(listener, response) == ['json', 'body']
    assert len(listener.history.rows) == before
    parsed = listener.invoke_python_translator(response, 0)
    tree = parsed.value
    assert type(tree) is JsonObject
    assert type(tree['a']) is JsonArray
    assert tree['a'][:5] == [None, True, 3, 1.25, 200.0]
    assert [type(item) for item in tree['a'][:5]] == [type(None), bool, int, float, float]
    assert type(tree['a'][5]) is JsonObject
    assert tree['a'][5]['deep'] is False
    assert listener.python_namespace['_'] is tree
    json_action = next(p for p in listener.history.presentations
                       if isinstance(p.value, MenuActionInput) and p.value.label == 'json')
    listener._append_text('evict one')
    listener._append_text('evict response')
    assert response not in listener.history.presentations
    assert listener.run_again(json_action)
    assert listener.history.presentations[-1].value is tree
    assert listener.python_namespace['_'] is tree


def test_json_null_and_body_stays_one_safe_capped_text_row(tmp_path):
    fake = FakeGet(result(b'null', headers={'Content-Type': 'application/json'}))
    listener = listener_at(tmp_path, fake)
    listener.submit(':get https://example.org/')
    response = listener.invoke_python_translator(listener.history.presentations[-1], 0)
    null = listener.invoke_python_translator(response, 0)
    assert null.value is None
    assert listener.python_namespace['_'] is None

    body = b'one\ntwo\t\xff' + b'x' * 5000
    fake2 = FakeGet(result(body))
    second = listener_at(tmp_path, fake2)
    second.submit('99')
    second.submit(':get https://example.org/')
    response2 = second.invoke_python_translator(second.history.presentations[-1], 0)
    previous = second.python_namespace['_']
    second.invoke_python_translator(response2, 0)
    assert [kind for kind, _ in records(second)][-2:] == ['MenuActionInput', 'Text']
    drawing = rows(second)[-1]
    assert drawing.startswith(r'one\ntwo\t')
    assert '�' in drawing
    assert '\n' not in drawing
    assert display_width(drawing) == 4096
    assert drawing.endswith('…')
    assert second.python_namespace['_'] == previous
    action = second.history.presentations[-2]
    assert second.run_again(action)
    assert rows(second)[-1] == drawing
    assert second.python_namespace['_'] == previous


@pytest.mark.parametrize('body', [b'\xff', b'{bad}', b'NaN', b'Infinity'])
def test_invalid_json_keeps_response_one_error_and_body_action(tmp_path, body):
    fake = FakeGet(result(body, headers={'Content-Type': 'application/json'}))
    listener = listener_at(tmp_path, fake)
    listener.submit(':get https://example.org/')
    response = listener.invoke_python_translator(listener.history.presentations[-1], 0)
    assert [kind for kind, _ in records(listener)][-2:] == ['Value', 'Error']
    assert listener.python_namespace['_'] is response.value
    before = len(listener.history.rows)
    assert actions(listener, response) == ['body']
    assert actions(listener, response) == ['body']
    assert len(listener.history.rows) == before
    listener.invoke_python_translator(response, 0)
    assert [kind for kind, _ in records(listener)][-2:] == ['MenuActionInput', 'Text']


class StubResponse:
    def __init__(self, body, *, status=200):
        self.status = status
        self.headers = {'Content-Type': 'application/json'}
        self.body = io.BytesIO(body)
        self.read_sizes = []
        self.closed = False

    def read(self, size):
        self.read_sizes.append(size)
        return self.body.read(size)

    def geturl(self):
        return 'https://final.example/'

    def close(self):
        self.closed = True


def test_production_adapter_bounded_read_headers_and_http_errors(monkeypatch):
    seen = []
    response = StubResponse(b'ok')

    def open_stub(request, *, timeout):
        seen.append((request, timeout))
        return response

    monkeypatch.setattr('pbui.http.urllib.request.urlopen', open_stub)
    request = GetRequest('https://example.org/')
    assert production_get(request).body == b'ok'
    assert seen[0][0].get_header('User-agent') == 'pbui/1.0'
    assert seen[0][1] == 15
    assert response.read_sizes == [MAX_BODY_BYTES + 1]
    assert response.closed

    oversized = StubResponse(b'x' * (MAX_BODY_BYTES + 2))
    monkeypatch.setattr('pbui.http.urllib.request.urlopen', lambda *a, **k: oversized)
    with pytest.raises(BodyTooLarge):
        production_get(request)
    assert oversized.read_sizes == [MAX_BODY_BYTES + 1]
    assert oversized.closed

    returned_redirect = StubResponse(b'', status=302)
    monkeypatch.setattr('pbui.http.urllib.request.urlopen', lambda *a, **k: returned_redirect)
    with pytest.raises(GetTransportError):
        production_get(request)
    assert returned_redirect.closed

    for status in (404, 301, 302, 303, 307, 308):
        error = urllib.error.HTTPError(
            request.url, status, 'failure', {'Content-Type': 'text/plain'}, io.BytesIO(b'error')
        )
        monkeypatch.setattr('pbui.http.urllib.request.urlopen', lambda *a, **k: (_ for _ in ()).throw(error))
        if status == 404:
            completed = production_get(request)
            assert completed.status == 404 and completed.body == b'error'
        else:
            with pytest.raises(GetTransportError):
                production_get(request)
        assert error.fp.closed


def test_json_summary_dig_nested_identity_and_plain_containers(tmp_path):
    listener = listener_at(tmp_path, FakeGet())
    child = JsonObject({'leaf': 'ok'})
    array = JsonArray([child, None])
    tree = JsonObject({'a': array, 'plain': 3})
    listener.python_namespace.update(tree=tree, array=array, ordinary={'a': 1}, sequence=[1])
    listener.submit('tree')
    parent_row = listener.history.rows[-1]
    parent = parent_row.presentations[0]
    assert rows(listener)[-1] == '▸ JsonObject (2 keys)'
    assert actions(listener, parent) == []
    assert listener.python_classes.lookup({}) is None
    assert listener.python_classes.lookup([]) is None
    before = len(listener.history.rows)
    assert listener.select_for_input(parent)
    assert listener.history.rows[before - 1] is parent_row
    assert rows(listener)[-2:] == ('["a"]  ▸ JsonArray (2 elements)', '["plain"]  int 3')
    assert [row.presentations[0].value for row in listener.history.rows[before:]] == [array, 3]
    assert all(row.presentations[0].type is listener.types.value
               for row in listener.history.rows[before:])
    assert not any(p.type is listener.types.menu_action_input
                   for p in listener.history.presentations)

    nested = listener.history.rows[before].presentations[0]
    assert listener.select_for_input(nested)
    assert rows(listener)[-2:] == ('[0]  ▸ JsonObject (1 keys)', '[1]  NoneType None')
    assert listener.history.rows[-2].presentations[0].value is child
    assert listener.history.rows[-1].presentations[0].value is None
    assert listener.select_for_input(listener.history.rows[-2].presentations[0])
    assert rows(listener)[-1] == '["leaf"]  str \'ok\''
    scalar = listener.history.rows[-1].presentations[0]
    assert listener.select_for_input(scalar)
    assert rows(listener)[-1] == "str: 'ok'"
    assert listener.history.rows[before - 1] is parent_row

    listener.submit('array')
    assert rows(listener)[-1] == '▸ JsonArray (2 elements)'
    listener.submit('ordinary')
    ordinary = listener.history.presentations[-1]
    assert rows(listener)[-1].startswith("dict ")
    assert listener.select_for_input(ordinary)
    assert rows(listener)[-1].startswith("dict: ")
    listener.submit('sequence')
    sequence = listener.history.presentations[-1]
    assert rows(listener)[-1].startswith("list ")
    assert listener.select_for_input(sequence)
    assert rows(listener)[-1].startswith("list: ")


def test_json_dig_empty_bounded_literal_trailer_and_repeat(tmp_path):
    listener = listener_at(tmp_path, FakeGet())
    listener.python_namespace['empty'] = JsonArray()
    listener.submit('empty')
    empty = listener.history.presentations[-1]
    old_rows = listener.history.rows
    assert listener.select_for_input(empty)
    assert listener.history.rows == old_rows
    assert rows(listener)[-1] == '▸ JsonArray (0 elements)'

    values = JsonArray(range(101))
    listener.python_namespace['values'] = values
    listener.submit('values')
    parent_row = listener.history.rows[-1]
    parent = parent_row.presentations[0]
    assert rows(listener)[-1] == '▸ JsonArray (101 elements)'
    before = len(listener.history.rows)
    assert listener.select_for_input(parent)
    added = listener.history.rows[before:]
    assert len(added) == 101
    assert [row.presentations[0].value for row in added[:100]] == list(range(100))
    assert rows(listener)[-2:] == ('[99]  int 99', '… (1 more members)')
    assert added[-1].presentations == ()
    assert added[-1].presentation_ids == ()
    assert listener.history.rows[before - 1] is parent_row
    assert listener.select_for_input(parent)
    assert len(listener.history.rows) == before + 202
    assert listener.history.rows[before - 1] is parent_row


def test_json_member_escaping_caps_and_wrapped_single_hit_target(tmp_path):
    from pbui.text import logical_presentation_text

    listener = listener_at(tmp_path, FakeGet())
    key = 'a"\n'
    value = 'short'
    long_key = '\x00' + '界' * 60
    long_value = 'z' * 500
    tree = JsonObject({key: value, long_key: long_value})
    listener.python_namespace['tree'] = tree
    listener.submit('tree')
    assert listener.select_for_input(listener.history.presentations[-1])
    first, second = listener.history.rows[-2:]
    assert logical_presentation_text(listener.history, first.presentations[0]) == (
        '["a\\"\\n"]  str \'short\''
    )
    drawing = logical_presentation_text(listener.history, second.presentations[0])
    label, separator, _ = drawing.partition('  ')
    assert separator == '  '
    assert label.startswith('["\\u0000')
    assert label.endswith('…"]')
    assert display_width(label) <= 48
    assert display_width(drawing) <= 120
    assert drawing.endswith('…')
    assert second.presentations[0].value is long_value
    rendered = layout(listener.history, 17)
    logical_index = len(listener.history.rows) - 2
    for y, row in enumerate(rendered.rows):
        if row.logical_row == logical_index:
            for x in range(2, row.display_width):
                assert rendered.hit_test(x, y) is first.presentations[0]
            assert rendered.hit_test(0, y) is None
            assert rendered.hit_test(1, y) is None
    logical_index += 1
    for y, row in enumerate(rendered.rows):
        if row.logical_row == logical_index:
            for x in range(2, row.display_width):
                assert rendered.hit_test(x, y) is second.presentations[0]
            assert rendered.hit_test(0, y) is None
            assert rendered.hit_test(1, y) is None
