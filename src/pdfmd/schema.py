from __future__ import annotations

from typing import Any, Literal
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Route(Strict):
    endpoint: str
    model: str = Field(min_length=1)
    protocol: Literal["chat_completions", "responses"] = "chat_completions"
    context_tokens: int = Field(ge=2048)
    output_tokens: int = Field(ge=256)
    image_tokens: int | None = Field(default=None, ge=1)
    vision: bool = False
    timeout_seconds: float = Field(default=180, ge=1, le=3600)
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_route(self):
        url = urlsplit(self.endpoint)
        if (not url.hostname or url.username or url.password or url.query or url.fragment
                or (url.scheme != "https" and not (url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"}))):
            raise ValueError("Use a full HTTPS endpoint, or HTTP on loopback. Omit credentials, query, and fragment.")
        expected = "/chat/completions" if self.protocol == "chat_completions" else "/responses"
        if not url.path.rstrip("/").endswith(expected):
            raise ValueError(f"The endpoint must end with {expected}.")
        reserved = {"model", "messages", "input", "tools", "stream", "store", "instructions", "max_tokens", "max_completion_tokens", "max_output_tokens", "background", "previous_response_id"}
        if reserved.intersection(self.parameters):
            raise ValueError("Generation parameters contain controller-owned fields.")
        if self.output_tokens >= self.context_tokens:
            raise ValueError("The output reserve must be smaller than context capacity.")
        return self


class Limits(Strict):
    max_requests: int = Field(default=80, ge=1, le=10000)
    max_active_seconds: int = Field(default=7200, ge=1)
    max_response_repairs: int = Field(default=2, ge=0)
    replay_unknown: bool = False
    max_attempts_per_request: int = Field(default=1, ge=1, le=10)


class Block(Strict):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")
    markdown: str
    pages: list[int] = Field(min_length=1)
    source_note: str = ""


class Page(Strict):
    printed: str = "unknown"
    disposition: Literal["unprocessed", "included", "outside_scope", "omitted_non_content"] = "unprocessed"
    note: str = ""


class Document(Strict):
    title: str
    scope: str
    blocks: list[Block] = Field(default_factory=list)
    pages: dict[str, Page]
    claim: Literal["partial", "complete"] = "partial"
    known_gaps: list[str] = Field(default_factory=list)


class CandidateRef(Strict):
    ref: str
    pointer: str = "/replace_blocks"


class Insert(Strict):
    kind: Literal["insert"]
    after_id: str | None
    blocks: list[Block]


class Replace(Strict):
    kind: Literal["replace"]
    id: str
    blocks: list[Block]


class Delete(Strict):
    kind: Literal["delete"]
    id: str


class Patch(Strict):
    kind: Literal["patch"]
    id: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    expected: str
    text: str


class Edit(Strict):
    base_version: str | None
    expected_head: str | None
    title: str | None = None
    replace_blocks: list[Block] | None = None
    reuse_candidate: CandidateRef | None = None
    operations: list[Insert | Replace | Delete | Patch] = Field(default_factory=list)
    page_updates: dict[str, Page] = Field(default_factory=dict, description="Partial page metadata by one-based physical-page key. Only explicitly supplied fields change. Use printed for the source label; use unknown when unread. A complete claim needs all pages classified, with a note for outside_scope or omitted_non_content.")
    claim: Literal["partial", "complete"] | None = None
    known_gaps: list[str] | None = None

    @model_validator(mode="after")
    def one_source(self):
        if self.replace_blocks is not None and self.reuse_candidate is not None:
            raise ValueError("Use either replacement blocks or a candidate reference.")
        return self


def pointer(value: Any, path: str) -> Any:
    if not path:
        return value
    if not path.startswith("/"):
        raise ValueError("Use an RFC 6901 JSON Pointer beginning with '/'.")
    for part in path[1:].split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value
