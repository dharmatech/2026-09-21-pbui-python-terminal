"""Retained HTTP values and the bounded, synchronous GET transport."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass, field
from typing import Protocol


MAX_BODY_BYTES = 2_097_152
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


@dataclass(frozen=True, slots=True)
class GetRequest:
    url: str
    method: str = field(default="GET", init=False)


@dataclass(frozen=True, slots=True)
class GetResult:
    status: int
    final_url: str
    headers: Mapping[str, str]
    body: bytes


class GetTransport(Protocol):
    def __call__(self, request: GetRequest) -> GetResult: ...


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status: int
    final_url: str
    content_type: str | None
    body: bytes


class JsonObject(dict):
    """A JSON object that remains distinguishable from a Python dict."""


class JsonArray(list):
    """A JSON array that remains distinguishable from a Python list."""


class GetTransportError(Exception):
    """A GET that did not produce a complete, usable response."""


class BodyTooLarge(GetTransportError):
    def __init__(self) -> None:
        super().__init__(f"HTTP body exceeds {MAX_BODY_BYTES} bytes")


def validate_url(request: GetRequest) -> None:
    """Check the supported URL shape before invoking even an injected transport."""

    try:
        parts = urllib.parse.urlsplit(request.url)
        valid = (
            isinstance(request.url, str)
            and not any(ord(character) <= 32 or ord(character) == 127
                        for character in request.url)
            and parts.scheme.lower() in {"http", "https"}
            and bool(parts.hostname)
            and not any(character.isspace() for character in parts.hostname)
        )
        parts.port  # Validate a supplied port, including its numeric range.
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise GetTransportError("GET requires an http or https URL with a host")


def _bounded_body(response: object) -> bytes:
    body = response.read(MAX_BODY_BYTES + 1)
    if len(body) > MAX_BODY_BYTES:
        raise BodyTooLarge()
    return body


def _result(response: object) -> GetResult:
    status = int(response.status)
    if status in REDIRECT_STATUSES:
        raise GetTransportError(f"HTTP redirect failed: {status}")
    return GetResult(status, response.geturl(), response.headers, _bounded_body(response))


def production_get(request: GetRequest) -> GetResult:
    """Follow redirects with urllib, reading at most one byte past the cap."""

    validate_url(request)
    outgoing = urllib.request.Request(request.url, headers={"User-Agent": "pbui/1.0"})
    try:
        response = urllib.request.urlopen(outgoing, timeout=15)
    except urllib.error.HTTPError as error:
        if error.code in REDIRECT_STATUSES:
            error.close()
            raise GetTransportError(f"HTTP redirect failed: {error.code}") from error
        with closing(error):
            return _result(error)
    with closing(response):
        return _result(response)


def content_type_of(headers: Mapping[str, str]) -> str | None:
    for name, value in headers.items():
        if name.lower() == "content-type":
            return value
    return None


def is_json_media_type(content_type: str | None) -> bool:
    if content_type is None:
        return False
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type == "application/json" or media_type.endswith("+json")


def _reject_constant(value: str) -> object:
    raise ValueError(f"nonstandard JSON constant: {value}")


def _convert_json(value: object) -> object:
    if isinstance(value, dict):
        return JsonObject({key: _convert_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return JsonArray(_convert_json(item) for item in value)
    return value


def parse_json(body: bytes) -> object:
    return _convert_json(json.loads(body.decode("utf-8", "strict"), parse_constant=_reject_constant))


__all__ = [
    "MAX_BODY_BYTES", "REDIRECT_STATUSES", "BodyTooLarge", "GetRequest",
    "GetResult", "GetTransport", "GetTransportError", "HttpResponse",
    "JsonArray", "JsonObject", "content_type_of", "is_json_media_type",
    "parse_json", "production_get", "validate_url",
]
