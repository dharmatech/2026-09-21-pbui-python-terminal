"""Retained public Bluesky SDK values and fixture-local graph actions."""

from __future__ import annotations

import pytest
from atproto import models

from pbui import bsky
from pbui.chips import PythonChip
from pbui.commands import HeadlessListener, RootedFilesystem
from pbui.repl import ValueTranslator
from pbui.text import display_width, stored_row_text
from pbui.transcript import CommandInput, MenuActionInput


STAMP = "2024-01-01T00:00:00Z"
CID = "bafyreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku"
URI = "at://did:plc:alice/app.bsky.feed.post/one"


class EmptyProcesses:
    pass


def listener_at(tmp_path):
    return HeadlessListener(str(tmp_path), RootedFilesystem(tmp_path), EmptyProcesses())


def basic(handle="alice.example", did="did:plc:alice"):
    return models.AppBskyActorDefs.ProfileViewBasic(did=did, handle=handle)


def detailed(handle="alice.example", name="Alice"):
    return models.AppBskyActorDefs.ProfileViewDetailed(
        did="did:plc:alice", handle=handle, display_name=name
    )


def post(text="hello", *, handle="alice.example", author=None):
    author = author or basic(handle)
    record = models.AppBskyFeedPost.Record(created_at=STAMP, text="safe" if "\ud800" in text else text)
    if "\ud800" in text:
        object.__setattr__(record, "text", text)
    return models.AppBskyFeedDefs.PostView(
        author=author, cid=CID, indexed_at=STAMP, record=record, uri=URI
    )


def node(text="hello", *, parent=None, replies=None):
    return models.AppBskyFeedDefs.ThreadViewPost(
        post=post(text), parent=parent, replies=replies
    )


def response(subject):
    return models.AppBskyFeedGetPostThread.Response(thread=subject)


def missing():
    return models.AppBskyFeedDefs.NotFoundPost(not_found=True, uri=URI)


def blocked():
    return models.AppBskyFeedDefs.BlockedPost(
        author=models.AppBskyFeedDefs.BlockedAuthor(did="did:plc:alice"),
        blocked=True, uri=URI,
    )


def feed(*posts, repost_first=False):
    entries = []
    for index, item in enumerate(posts):
        reason = (
            models.AppBskyFeedDefs.ReasonRepost(by=basic("reposter.example"), indexed_at=STAMP)
            if repost_first and index == 0 else None
        )
        entries.append(models.AppBskyFeedDefs.FeedViewPost(post=item, reason=reason))
    return models.AppBskyFeedGetAuthorFeed.Response(feed=entries)


def values(listener):
    return tuple(p for p in listener.history.presentations if p.type is listener.types.value)


def result_rows(listener):
    inputs = {
        listener.types.python_input, listener.types.command_input,
        listener.types.menu_action_input,
    }
    return tuple(
        row for row in listener.history.rows
        if not row.presentations or row.presentations[0].type not in inputs
    )


def drawings(listener):
    return tuple(stored_row_text(row) for row in result_rows(listener))


def labels(listener, value_presentation):
    return [action.label for action in listener.python_translators_for(value_presentation)]


def present(listener, name, value):
    listener.python_namespace[name] = value
    listener.submit(name)
    return values(listener)[-1]


def test_registration_namespace_identity_chip_and_generic_sdk_values(tmp_path):
    listener = listener_at(tmp_path)
    assert listener.python_namespace == {"__name__": "__pbui__"}
    registered = (
        bsky.ThreadResponse, bsky.ThreadViewPost, bsky.PostView,
        bsky.NotFoundPost, bsky.BlockedPost, bsky.ProfileViewDetailed,
        bsky.AuthorFeedResponse,
    )
    assert all(cls in listener.python_classes._entries for cls in registered)
    source_node = node()
    source = response(source_node)
    target = present(listener, "source", source)
    assert target.value is source
    assert listener.python_namespace["_"] is source
    assert drawings(listener)[-1] == "alice.example: hello"
    listener.set_input_text("id(")
    assert listener.select_for_input(target)
    chip = next(piece for piece in listener.python_pieces if isinstance(piece, PythonChip))
    assert chip.value is source
    listener.insert_python_text(") == id(_)")
    listener.submit()
    assert drawings(listener)[-1] == "bool True"

    reply = node("reply")
    reply_target = present(listener, "reply", reply)
    assert reply_target.value is reply
    assert listener.python_namespace["_"] is reply
    listener.set_input_text("id(")
    assert listener.select_for_input(reply_target)
    assert next(piece for piece in listener.python_pieces if isinstance(piece, PythonChip)).value is reply
    listener.cancel()
    post_target = present(listener, "post_view", reply.post)
    assert post_target.value is reply.post
    assert listener.python_namespace["_"] is reply.post
    for generic in (basic(), post().record, feed(post()).feed[0]):
        generic_target = present(listener, "generic", generic)
        assert listener.python_classes.lookup(generic) is None
        assert drawings(listener)[-1].startswith(type(generic).__name__ + " ")
        assert labels(listener, generic_target) == []


def test_rows_feed_metadata_unavailable_and_unknown_subject(tmp_path):
    listener = listener_at(tmp_path)
    assert drawings(listener) == ()
    p = post("")
    assert drawings_after(listener, p) == "alice.example: (no text)"
    assert drawings_after(listener, detailed(name="Alice")) == "Alice — alice.example"
    assert drawings_after(listener, detailed(name="")) == "alice.example"
    for subject, expected in ((missing(), "unavailable post"), (blocked(), "blocked post")):
        for value in (subject, response(subject)):
            target = present(listener, "item", value)
            assert drawings(listener)[-1] == expected
            assert labels(listener, target) == []
    unknown = bsky.ThreadResponse.model_construct(thread=object())
    target = present(listener, "unknown", unknown)
    assert drawings(listener)[-1].startswith("Response ")
    assert labels(listener, target) == []
    assert target.value is unknown

    empty = feed()
    ordinary = present(listener, "empty_feed", empty)
    assert drawings(listener)[-1] == "feed: 0 posts"
    assert ordinary.value is empty
    assert listener.python_namespace["_"] is empty
    reposted = post("repost text", handle="original.example")
    repost_feed = feed(reposted, repost_first=True)
    assert drawings_after(listener, repost_feed) == "feed: 1 posts"
    labeled = listener.present_bsky_feed(repost_feed, handle="owner.example")
    assert labeled.value is repost_feed
    assert listener.python_namespace["_"] is repost_feed
    assert drawings(listener)[-1] == "owner.example: 1 posts"
    assert "handle" not in repost_feed.model_fields_set
    assert drawings_after(listener, repost_feed) == "feed: 1 posts"


def drawings_after(listener, value):
    present(listener, "item", value)
    return drawings(listener)[-1]


def test_escaping_caps_and_printer_failure_retains_value(tmp_path):
    listener = listener_at(tmp_path)
    unsafe = post("a\x01\t\ud800\n" + "界" * 70)
    target = present(listener, "unsafe", unsafe)
    row = drawings(listener)[-1]
    assert row.startswith(r"alice.example: a\x01\t\ud800\n")
    assert display_width(row) <= 120 and row.endswith("…")
    assert target.value is unsafe
    object.__setattr__(unsafe, "record", object())
    target = present(listener, "unsafe", unsafe)
    assert target.value is unsafe
    assert drawings(listener)[-2].startswith("PostView ")
    assert "AttributeError" in drawings(listener)[-1]
    assert listener.python_namespace["_"] is unsafe


def test_detail_lines_caps_empty_and_failure_is_atomic(tmp_path):
    listener = listener_at(tmp_path)
    one = post("one")
    target = present(listener, "one", one)
    before = listener.python_namespace["_"]
    assert listener.select(target)
    assert drawings(listener)[-1] == "one"
    assert listener.python_namespace["_"] is before
    multi = post("first\n\n" + "界" * 70 + "\t\x01\ud800\nlast")
    target = present(listener, "multi", multi)
    assert listener.select(target)
    assert drawings(listener)[-4] == "first"
    assert drawings(listener)[-3] == ""
    assert display_width(drawings(listener)[-2]) <= 120
    assert drawings(listener)[-2].endswith("…")
    assert drawings(listener)[-1] == "last"
    long = post("\n".join(f"line {i}" for i in range(27)))
    target = present(listener, "long", long)
    count = len(result_rows(listener))
    assert listener.select(target)
    assert len(result_rows(listener)) == count + 25
    assert drawings(listener)[-1] == "… (3 more lines)"
    empty = post("")
    target = present(listener, "empty", empty)
    assert listener.select(target)
    assert drawings(listener)[-1] == ""
    broken = post("safe")
    target = present(listener, "broken", broken)
    object.__setattr__(broken, "record", object())
    count = len(result_rows(listener))
    previous = listener.python_namespace["_"]
    assert listener.select(target)
    assert len(result_rows(listener)) == count + 1
    assert "AttributeError" in drawings(listener)[-1]
    assert listener.python_namespace["_"] is previous
    assert target.value is broken
    listener.submit(":show")
    assert listener.pending_request is not None
    assert not listener.select(target)
    assert listener.pending_request is not None
    listener.cancel()


def test_menu_order_local_replies_parent_and_saved_target(tmp_path):
    listener = listener_at(tmp_path)
    parent = missing()
    replies = [node(f"reply {i}") for i in range(21)]
    replies[3] = missing()
    replies[4] = blocked()
    source_node = node("source", parent=parent, replies=replies)
    source = response(source_node)
    target = present(listener, "source", source)
    assert labels(listener, target) == ["author", "replies", "parent"]
    assert labels(listener, present(listener, "direct", source_node)) == ["author", "replies", "parent"]
    assert labels(listener, present(listener, "post_only", source_node.post)) == ["author", "replies"]
    assert labels(listener, present(listener, "no_parent", node())) == ["author", "replies"]
    assert listener.python_namespace["_"] is not source
    before = len(values(listener))
    last = listener.invoke_python_translator(target, 1)
    appended = values(listener)[before:]
    assert len(appended) == 20
    assert all(p.value is replies[i] for i, p in enumerate(appended))
    assert last is appended[-1]
    assert listener.python_namespace["_"] is replies[19]
    assert drawings(listener)[-1] == "… (1 more replies)"
    assert result_rows(listener)[-1].presentations == ()
    saved = next(
        p for p in reversed(listener.history.presentations)
        if isinstance(p.value, MenuActionInput) and p.value.label == "replies"
    )
    assert saved.value.target is source
    assert listener.run_again(saved)
    assert values(listener)[-20].value is replies[0]
    assert values(listener)[-1].value is replies[19]
    assert source in [p.value for p in values(listener)]
    got_parent = listener.invoke_python_translator(target, 2)
    assert got_parent.value is parent
    assert listener.python_namespace["_"] is parent
    assert labels(listener, got_parent) == []
    empty = present(listener, "empty", node(replies=[]))
    previous = listener.python_namespace["_"]
    listener.invoke_python_translator(empty, 1)
    assert drawings(listener)[-1] == "no replies"
    assert listener.python_namespace["_"] is previous


def test_direct_feed_posts_include_reposts_and_empty_feed(tmp_path):
    listener = listener_at(tmp_path)
    posts = [post(f"entry {i}", handle=f"author{i}.example") for i in range(22)]
    source = feed(*posts, repost_first=True)
    target = present(listener, "source", source)
    assert drawings(listener)[-1] == "feed: 20 posts"
    assert labels(listener, target) == ["posts"]
    start = len(values(listener))
    last = listener.invoke_python_translator(target, 0)
    listed = values(listener)[start:]
    assert [item.value for item in listed] == posts[:20]
    assert all(item.value is posts[i] for i, item in enumerate(listed))
    assert drawings(listener)[-20] == "author0.example: entry 0"
    assert last is listed[-1]
    assert listener.python_namespace["_"] is posts[19]
    listener.set_input_text("id(")
    assert listener.select_for_input(listed[0])
    assert next(piece for piece in listener.python_pieces if isinstance(piece, PythonChip)).value is posts[0]
    listener.cancel()
    empty = present(listener, "empty", feed())
    previous = listener.python_namespace["_"]
    listener.invoke_python_translator(empty, 0)
    assert drawings(listener)[-1] == "no posts"
    assert listener.python_namespace["_"] is previous
    profile = present(listener, "profile", detailed())
    assert labels(listener, profile) == ["posts"]
    assert listener.python_namespace["_"] is profile.value


def test_local_detailed_author_identity_and_no_fetch_on_menu(tmp_path, monkeypatch):
    import socket

    listener = listener_at(tmp_path)
    author = detailed()
    exact_post = bsky.PostView.model_construct(
        author=author, cid=CID, indexed_at=STAMP,
        record=models.AppBskyFeedPost.Record(created_at=STAMP, text="owned"),
        uri=URI,
    )
    calls = []

    def forbid_connect(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("presenting and opening a menu must not connect")

    monkeypatch.setattr(socket.socket, "connect", forbid_connect)
    target = present(listener, "exact_post", exact_post)
    assert labels(listener, target) == ["author", "replies"]
    assert calls == []
    author_target = listener.invoke_python_translator(target, 0)
    assert author_target.value is author
    assert listener.python_namespace["_"] is author
    assert labels(listener, author_target) == ["posts"]
    assert calls == []


def test_local_post_printer_failure_uses_value_fallback(tmp_path):
    listener = listener_at(tmp_path)
    item = post("before")
    source = feed(item)
    target = present(listener, "source", source)
    object.__setattr__(item, "record", object())
    result = listener.invoke_python_translator(target, 0)
    assert result.value is item
    assert drawings(listener)[-2].startswith("PostView ")
    assert "AttributeError" in drawings(listener)[-1]
    assert listener.python_namespace["_"] is item
    assert target.value is source


def test_more_specific_class_registration_keeps_mro_precedence(tmp_path):
    listener = listener_at(tmp_path)

    class CustomResponse(bsky.ThreadResponse):
        pass

    listener.register_python_class(CustomResponse, lambda _value: "custom response")
    custom_response = CustomResponse.model_construct(thread=object())
    target = present(listener, "custom_response", custom_response)
    assert drawings(listener)[-1] == "custom response"
    assert labels(listener, target) == []

    class CustomPost(bsky.PostView):
        pass

    listener.register_python_class(
        CustomPost, lambda _value: "custom post",
        (ValueTranslator("custom", lambda value: value),),
    )
    original = post()
    custom_post = CustomPost.model_construct(
        author=original.author, cid=CID, indexed_at=STAMP,
        record=original.record, uri=URI,
    )
    target = present(listener, "custom_post", custom_post)
    assert drawings(listener)[-1] == "custom post"
    assert labels(listener, target) == ["custom"]


class FakeBsky:
    def __init__(self, *, thread=None, profile=None, author_feed=None):
        self.thread = thread
        self.profile = profile
        self.author_feed = author_feed
        self.calls = []

    def _result(self, name, argument, result):
        self.calls.append((name, argument))
        if isinstance(result, Exception):
            raise result
        return result

    def get_post_thread(self, uri):
        return self._result("thread", uri, self.thread)

    def get_profile(self, actor):
        return self._result("profile", actor, self.profile)

    def get_author_feed(self, actor, limit=20):
        return self._result("feed", (actor, limit), self.author_feed)


def test_client_is_lazy_and_independent_of_python_evaluation(tmp_path, monkeypatch):
    import pbui.commands as commands

    constructed = []

    class RequestSpy:
        def __init__(self, *, timeout):
            self.timeout = timeout

    class ClientSpy:
        def __init__(self, *, base_url, request):
            constructed.append((base_url, request))
            self.profile = detailed()

        def login(self, *args, **kwargs):
            pytest.fail("public client must not log in")

        def get_profile(self, actor):
            assert actor == "alice.example"
            return self.profile

    monkeypatch.setattr(commands, "Request", RequestSpy)
    monkeypatch.setattr(commands, "Client", ClientSpy)
    listener = listener_at(tmp_path)
    assert listener.python_namespace == {"__name__": "__pbui__"}
    held = present(listener, "held", response(node("held")))
    assert labels(listener, held) == ["author", "replies"]
    assert constructed == []
    assert values(listener)[-1].value is held.value
    listener.submit(":profile alice.example")
    assert len(constructed) == 1
    assert constructed[0][0] == "https://public.api.bsky.app"
    assert constructed[0][1].timeout == 15.0
    assert values(listener)[-1].value is listener._bsky_client.profile
    listener.submit(":profile alice.example")
    assert len(constructed) == 1


def test_injected_commands_retain_sdk_results_and_bare_hints(tmp_path):
    thread = response(node("from thread"))
    profile = detailed()
    fake = FakeBsky(thread=thread, profile=profile)
    listener = HeadlessListener(str(tmp_path), RootedFilesystem(tmp_path), EmptyProcesses(), bsky_client=fake)
    assert listener.python_namespace == {"__name__": "__pbui__"}
    for command, call, result in (
        (":post https://bsky.app/profile/alice.example/post/one?view=1#top",
         ("thread", "at://alice.example/app.bsky.feed.post/one"), thread),
        (":post " + URI, ("thread", URI), thread),
        (":profile alice.example", ("profile", "alice.example"), profile),
        (":profile did:web:example.com", ("profile", "did:web:example.com"), profile),
    ):
        before = len(listener.history.rows)
        listener.submit(command)
        assert fake.calls[-1] == call
        assert len(listener.history.rows) == before + 2
        assert isinstance(listener.history.rows[-2].presentations[0].value, CommandInput)
        assert listener.history.rows[-1].presentations[0].value is result
        assert listener.python_namespace["_"] is result
    for word in ("post", "profile"):
        listener.submit(word)
        assert f"NameError: name '{word}' is not defined" in drawings(listener)[-1]
        assert f":{word}" in drawings(listener)[-1]
    assert fake.calls == [
        ("thread", "at://alice.example/app.bsky.feed.post/one"),
        ("thread", URI),
        ("profile", "alice.example"),
        ("profile", "did:web:example.com"),
    ]


@pytest.mark.parametrize("argument", [
    "", " ", "  alice.example", "http://bsky.app/profile/alice.example/post/one",
    "https://other.example/profile/alice.example/post/one",
    "https://user@bsky.app/profile/alice.example/post/one",
    "https://bsky.app:443/profile/alice.example/post/one",
    "https://bsky.app/profile/alice.example/post/one/extra",
    "https://bsky.app/profile/nope/post/one",
    "https://bsky.app/profile/alice.example/post/.",
    "https://bsky.app/profile/alice.example/post/one two",
    "at://alice.example/app.bsky.feed.post/",
    "at://alice.example/app.bsky.feed.post/one/extra",
    "at://alice.example/app.bsky.feed.post/one?x",
    "at://alice.example/app.bsky.feed.post/one#x",
    "at://a..example/app.bsky.feed.post/one",
    "at://alice.example/app.bsky.feed.post/one+two",
])
def test_bad_post_input_is_atomic_and_does_not_call_client(tmp_path, argument):
    fake = FakeBsky()
    listener = HeadlessListener(str(tmp_path), RootedFilesystem(tmp_path), EmptyProcesses(), bsky_client=fake)
    held = present(listener, "held", post())
    before = len(listener.history.rows)
    listener.submit(":post" + (" " + argument if argument else ""))
    assert len(listener.history.rows) == before + 2
    assert listener.history.rows[-1].presentations[0].type is listener.types.error
    assert listener.history.rows[-2].presentations[0].type is listener.types.command_input
    assert listener.python_namespace["_"] is held.value
    assert fake.calls == []


@pytest.mark.parametrize("argument", [
    "", " ", "alice", "https://bsky.app/profile/alice.example",
    "alice.example other", "alice.example ", "a..example", "-a.example",
    "a.8", "did:PLC:abc", "did:plc:", "did:plc:abc?x",
])
def test_bad_profile_input_is_atomic_and_does_not_call_client(tmp_path, argument):
    fake = FakeBsky()
    listener = HeadlessListener(str(tmp_path), RootedFilesystem(tmp_path), EmptyProcesses(), bsky_client=fake)
    held = present(listener, "held", post())
    before = len(listener.history.rows)
    listener.submit(":profile" + (" " + argument if argument else ""))
    assert len(listener.history.rows) == before + 2
    assert listener.history.rows[-1].presentations[0].type is listener.types.error
    assert listener.python_namespace["_"] is held.value
    assert fake.calls == []


def test_fetch_backed_author_posts_and_replies_keep_identity(tmp_path):
    author = detailed()
    entries = [post(f"entry {i}", handle=f"author{i}.example") for i in range(22)]
    page = feed(*entries, repost_first=True)
    direct_replies = [node(f"reply {i}") for i in range(21)]
    direct_replies[4] = missing()
    fetched = response(node("root", replies=direct_replies))
    fake = FakeBsky(thread=fetched, profile=author, author_feed=page)
    listener = HeadlessListener(str(tmp_path), RootedFilesystem(tmp_path), EmptyProcesses(), bsky_client=fake)
    source = present(listener, "source", post("source"))
    assert fake.calls == []
    profile_result = listener.invoke_python_translator(source, 0)
    assert profile_result.value is author
    assert fake.calls == [("profile", "did:plc:alice")]
    before = len(values(listener))
    listener.invoke_python_translator(profile_result, 0)
    assert [p.value for p in values(listener)[before:]] == entries[:20]
    assert all(p.value is entries[i] for i, p in enumerate(values(listener)[before:]))
    assert fake.calls[-1] == ("feed", ("did:plc:alice", 20))
    assert listener.python_namespace["_"] is entries[19]
    before = len(values(listener))
    listener.invoke_python_translator(source, 1)
    listed = values(listener)[before:]
    assert len(listed) == 20
    assert all(item.value is direct_replies[i] for i, item in enumerate(listed))
    assert drawings(listener)[-1] == "… (1 more replies)"
    assert fake.calls[-1] == ("thread", URI)
    assert listener.python_namespace["_"] is direct_replies[19]
    assert source.value in [p.value for p in values(listener)]
    assert len(fake.calls) == 3
    saved = next(p for p in reversed(listener.history.presentations)
                 if isinstance(p.value, MenuActionInput) and p.value.label == "replies")
    assert saved.value.target is source.value
    assert listener.run_again(saved)
    assert fake.calls[-1] == ("thread", URI)
    assert len(fake.calls) == 4
    listener.invoke_python_translator(source, 1)
    assert len(fake.calls) == 5
    local = present(listener, "page", page)
    listener.invoke_python_translator(local, 0)
    assert len(fake.calls) == 5


def test_empty_fetches_and_missing_subject_are_text_only(tmp_path):
    fake = FakeBsky(thread=response(missing()), author_feed=feed())
    listener = HeadlessListener(str(tmp_path), RootedFilesystem(tmp_path), EmptyProcesses(), bsky_client=fake)
    source = present(listener, "source", post())
    previous = listener.python_namespace["_"]
    listener.invoke_python_translator(source, 1)
    assert drawings(listener)[-1] == "no replies"
    assert listener.python_namespace["_"] is previous
    profile_target = present(listener, "profile", detailed())
    previous = listener.python_namespace["_"]
    listener.invoke_python_translator(profile_target, 0)
    assert drawings(listener)[-1] == "no posts"
    assert listener.python_namespace["_"] is previous


@pytest.mark.parametrize("action,bad", [
    ("post", RuntimeError("failed")), ("post", TimeoutError("late")),
    ("post", object()), ("profile", RuntimeError("failed")),
    ("profile", TimeoutError("late")), ("profile", object()),
    ("author", RuntimeError("failed")), ("author", TimeoutError("late")),
    ("author", object()), ("posts", RuntimeError("failed")),
    ("posts", TimeoutError("late")), ("posts", object()),
    ("replies", RuntimeError("failed")), ("replies", TimeoutError("late")),
    ("replies", object()),
])
def test_fetch_failure_is_one_error_and_preserves_last_value(tmp_path, action, bad):
    kwargs = {"thread": response(node()), "profile": detailed(), "author_feed": feed()}
    field = {"post": "thread", "profile": "profile", "author": "profile",
             "posts": "author_feed", "replies": "thread"}[action]
    kwargs[field] = bad
    fake = FakeBsky(**kwargs)
    listener = HeadlessListener(str(tmp_path), RootedFilesystem(tmp_path), EmptyProcesses(), bsky_client=fake)
    source = present(listener, "source", post())
    target = source if action in {"author", "replies"} else (
        present(listener, "target", detailed()) if action == "posts" else None
    )
    previous = listener.python_namespace["_"]
    before_rows, before_values = len(listener.history.rows), len(values(listener))
    if action in {"post", "profile"}:
        listener.submit(":post " + URI if action == "post" else ":profile alice.example")
    else:
        listener.invoke_python_translator(target, {"author": 0, "replies": 1, "posts": 0}[action])
    assert len(values(listener)) == before_values
    assert len(listener.history.rows) == before_rows + 2
    assert listener.history.rows[-1].presentations[0].type is listener.types.error
    assert listener.python_namespace["_"] is previous


def test_bad_fetch_listing_member_is_atomic(tmp_path):
    good = post("good")
    invalid = bsky.PostView.model_construct(
        author=basic(), cid=CID, indexed_at=STAMP, record=object(), uri=URI
    )
    bad_page = bsky.AuthorFeedResponse.model_construct(feed=[
        models.AppBskyFeedDefs.FeedViewPost(post=good),
        models.AppBskyFeedDefs.FeedViewPost.model_construct(post=invalid),
    ])
    bad_node = bsky.ThreadViewPost.model_construct(post=good, replies=[
        node("good"), bsky.ThreadViewPost.model_construct(post=invalid)
    ])
    fake = FakeBsky(thread=response(bad_node), author_feed=bad_page)
    listener = HeadlessListener(str(tmp_path), RootedFilesystem(tmp_path), EmptyProcesses(), bsky_client=fake)
    profile = present(listener, "profile", detailed())
    for target, index in ((profile, 0), (present(listener, "source", post()), 1)):
        previous = listener.python_namespace["_"]
        before_values = len(values(listener))
        listener.invoke_python_translator(target, index)
        assert len(values(listener)) == before_values
        assert listener.history.rows[-1].presentations[0].type is listener.types.error
        assert listener.python_namespace["_"] is previous


def test_unknown_thread_subject_keeps_generic_response_row(tmp_path):
    unknown = bsky.ThreadResponse.model_construct(thread=object())
    fake = FakeBsky(thread=unknown)
    listener = HeadlessListener(str(tmp_path), RootedFilesystem(tmp_path), EmptyProcesses(), bsky_client=fake)
    listener.submit(":post " + URI)
    assert values(listener)[-1].value is unknown
    assert drawings(listener)[-1].startswith("Response ")
