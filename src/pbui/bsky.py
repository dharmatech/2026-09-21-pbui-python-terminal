"""Pure access and one-line drawings for retained public Bluesky SDK models."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from atproto import models


ThreadResponse = models.AppBskyFeedGetPostThread.Response
ThreadViewPost = models.AppBskyFeedDefs.ThreadViewPost
PostView = models.AppBskyFeedDefs.PostView
NotFoundPost = models.AppBskyFeedDefs.NotFoundPost
BlockedPost = models.AppBskyFeedDefs.BlockedPost
ProfileViewDetailed = models.AppBskyActorDefs.ProfileViewDetailed
AuthorFeedResponse = models.AppBskyFeedGetAuthorFeed.Response

FeedViewPost = models.AppBskyFeedDefs.FeedViewPost

_HANDLE_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\Z")
_DID = re.compile(r"did:[a-z]+:[A-Za-z0-9._:%-]*[A-Za-z0-9._-]\Z")
_RKEY = re.compile(r"[A-Za-z0-9._:~-]{1,512}\Z")


def valid_actor(actor: str) -> bool:
    """Check AT Protocol handle or DID syntax without resolving the actor."""

    if actor.startswith("did:"):
        return len(actor) <= 2048 and _DID.fullmatch(actor) is not None
    if len(actor) > 253:
        return False
    labels = actor.split(".")
    return (
        len(labels) >= 2
        and all(_HANDLE_LABEL.fullmatch(label) for label in labels)
        and labels[-1][0].isascii()
        and labels[-1][0].isalpha()
    )


def valid_rkey(key: str) -> bool:
    return key not in {".", ".."} and _RKEY.fullmatch(key) is not None


def post_uri(argument: str) -> str:
    """Return a validated post AT URI from an AT URI or bsky.app URL."""

    if not argument or any(character.isspace() for character in argument):
        raise ValueError("post requires one valid post URI or bsky.app URL")
    if argument.startswith("at://"):
        if "?" in argument or "#" in argument:
            raise ValueError("post AT URI cannot have a query or fragment")
        parts = argument[5:].split("/")
        if len(parts) != 3 or parts[1] != "app.bsky.feed.post":
            raise ValueError("post requires an app.bsky.feed.post record URI")
        actor, _, key = parts
        if not valid_actor(actor) or not valid_rkey(key):
            raise ValueError("post has an invalid actor or record key")
        return argument
    parsed = urlsplit(argument)
    if parsed.scheme != "https" or parsed.netloc.lower() != "bsky.app":
        raise ValueError("post requires an HTTPS bsky.app URL")
    parts = parsed.path.split("/")
    if len(parts) != 5 or parts[0] or parts[1] != "profile" or parts[3] != "post":
        raise ValueError("post URL must have /profile/ACTOR/post/RKEY")
    actor, key = parts[2], parts[4]
    if not valid_actor(actor) or not valid_rkey(key):
        raise ValueError("post has an invalid actor or record key")
    return f"at://{actor}/app.bsky.feed.post/{key}"



def thread_node(value: object) -> object | None:
    if isinstance(value, ThreadResponse):
        return value.thread
    if isinstance(value, ThreadViewPost):
        return value
    return None


def visible_post(value: object) -> bool:
    return isinstance(value, PostView) or isinstance(thread_node(value), ThreadViewPost)


def post_view(value: object) -> PostView:
    if isinstance(value, PostView):
        return value
    node = thread_node(value)
    if isinstance(node, ThreadViewPost):
        return node.post
    raise TypeError("value is not a visible post")


def post_text(value: object) -> str:
    return post_view(value).record.text


def post_row(value: object) -> str:
    post = post_view(value)
    return f"{post.author.handle}: {post.record.text or '(no text)'}"


def thread_response_row(value: ThreadResponse) -> str:
    subject = value.thread
    if isinstance(subject, ThreadViewPost):
        return post_row(subject)
    if isinstance(subject, NotFoundPost):
        return "unavailable post"
    if isinstance(subject, BlockedPost):
        return "blocked post"
    raise TypeError("unrecognized thread subject")


def profile_row(value: ProfileViewDetailed) -> str:
    return (
        f"{value.display_name} — {value.handle}"
        if value.display_name else value.handle
    )


def feed_row(value: AuthorFeedResponse, *, handle: str | None = None) -> str:
    prefix = "feed" if handle is None else handle
    return f"{prefix}: {min(len(value.feed), 20)} posts"
