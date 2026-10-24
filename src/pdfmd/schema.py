from __future__ import annotations

from typing import Any, Literal
import re
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
    ref: str = Field(description="Immutable candidate reference belonging to this task, including rejected edits.")
    pointer: str = Field(default="/replace_blocks", description="RFC 6901 pointer to block content, e.g. /operations/0/blocks. Never replays the candidate's operations.")


class BlockInput(Strict):
    blocks: list[Block] | None = Field(default=None, description="Exact replacement/inserted blocks. Supply either blocks or reuse_candidate, not both.")
    reuse_candidate: CandidateRef | None = Field(default=None, description="Copy a Block or list of Blocks from this task's retained candidate without regenerating it.")

    @model_validator(mode="after")
    def one_block_source(self):
        if (self.blocks is None) == (self.reuse_candidate is None):
            raise ValueError("Supply exactly one of blocks or reuse_candidate for insert/replace.")
        return self


class Insert(BlockInput):
    kind: Literal["insert"]
    after_id: str | None


class Replace(BlockInput):
    kind: Literal["replace"]
    id: str


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
    mode: Literal["edit", "rebuild"] = Field(default="edit", description="edit requires base_version == expected_head. Use rebuild deliberately to start from an older saved version or an empty base; expected_head must still match the current head. No user approval is required.")
    title: str | None = None
    replace_blocks: list[Block] | None = None
    reuse_candidate: CandidateRef | None = None
    operations: list[Insert | Replace | Delete | Patch] = Field(default_factory=list)
    page_updates: dict[str, Page] = Field(default_factory=dict, description="Partial page metadata by one-based physical-page key. Only explicitly supplied fields change. Use printed for the source label; use unknown when unread. A complete claim needs all pages classified, with a note for outside_scope or omitted_non_content.")
    claim: Literal["partial", "complete"] | None = None
    known_gaps: list[str] | None = None

    @model_validator(mode="after")
    def one_source(self):
        if self.mode == "edit" and self.base_version != self.expected_head:
            raise ValueError("Ordinary edits require base_version == expected_head. Read the current head and reuse retained candidate blocks for a local repair, or explicitly choose mode='rebuild' to reconstruct from another base.")
        if self.replace_blocks is not None and self.reuse_candidate is not None:
            raise ValueError("Use either replacement blocks or a candidate reference.")
        return self


def pointer(value: Any, path: str) -> Any:
    if not path:
        return value
    if not path.startswith("/"):
        raise ValueError("Use an RFC 6901 JSON Pointer beginning with '/'.")
    for part in path[1:].split("/"):
        if re.search(r"~(?![01])", part):
            raise ValueError("Invalid JSON Pointer escape; use ~0 for '~' and ~1 for '/'.")
        key = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", key):
                raise ValueError("JSON Pointer array indices must be nonnegative integers without leading zeros.")
            value = value[int(key)]
        else:
            value = value[key]
    return value
