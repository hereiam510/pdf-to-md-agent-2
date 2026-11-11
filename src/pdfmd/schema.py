from __future__ import annotations

from typing import Any, Literal
import re
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConflictResolutionSelection(Strict):
    request: str = Field(min_length=1)
    basis: str
    choice: Literal["preserve_and_replan"] = "preserve_and_replan"


class WaitPolicy(Strict):
    """Explicit streaming policy; values are starting points, not provider limits."""
    first_progress_seconds: float = Field(default=600, ge=1, le=3600, allow_inf_nan=False)
    idle_progress_seconds: float = Field(default=300, ge=1, le=3600, allow_inf_nan=False)
    total_seconds: float | None = Field(default=None, ge=1, le=3600, allow_inf_nan=False)


class Route(Strict):
    endpoint: str
    model: str = Field(min_length=1)
    protocol: Literal["chat_completions", "responses"] = "chat_completions"
    context_tokens: int = Field(ge=2048)
    output_tokens: int = Field(ge=256)
    image_tokens: int | None = Field(default=None, ge=1)
    estimation_profile: Literal["bpe_proxy_v1", "utf8_fallback_v1"] = "bpe_proxy_v1"
    vision: bool = False
    timeout_seconds: float = Field(default=180, ge=1, le=3600)
    # Missing/null retains the historical non-streaming deadline of a saved route.
    wait_policy: WaitPolicy | None = None
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
        reserved = {"model", "messages", "input", "tools", "stream", "stream_options", "store", "instructions", "max_tokens", "max_completion_tokens", "max_output_tokens", "background", "previous_response_id"}
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


def _compact(schema: dict) -> None:
    """Shrink the published tool schema (sent with every request); validation is unchanged.

    Drops generated titles and renders an optional ``X | None = None`` patch field
    as plain ``X`` (omission means unchanged; null is not a meaningful value).
    """
    schema.pop("title", None)
    for prop in schema.get("properties", {}).values():
        prop.pop("title", None)
        options = prop.get("anyOf")
        if options and prop.get("default", 0) is None and len(options) == 2 and {"type": "null"} in options:
            prop.pop("anyOf")
            prop.pop("default")
            prop.update(next(o for o in options if o != {"type": "null"}))


class Compact(Strict):
    model_config = ConfigDict(extra="forbid", json_schema_extra=_compact)


class EvidencePointer(Compact):
    ref: str = Field(min_length=1, description="Task evidence ref (tool result, image or stream), not a path.")
    physical_page: int | None = Field(default=None, ge=1)
    region: list[float] | None = Field(default=None, min_length=4, max_length=4, description="[x0,y0,x1,y1], unrotated page frame.")
    note: str = Field(description="What it shows.")

    @model_validator(mode="after")
    def region_needs_page(self):
        if self.region is not None and self.physical_page is None:
            raise ValueError("An evidence region requires its physical_page.")
        return self


class Alternative(Compact):
    value: str
    basis: list[EvidencePointer] = Field(min_length=1)


class TextFact(Compact):
    state: Literal["known", "none", "unknown", "conflicting"] = "unknown"
    value: str | None = None
    basis: list[EvidencePointer] = Field(default_factory=list)
    alternatives: list[Alternative] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent(self):
        if self.state == "known":
            if not self.value or not self.basis or self.alternatives:
                raise ValueError("A known fact needs a nonempty exact value and basis, and no alternatives.")
        elif self.value is not None:
            raise ValueError(f"A {self.state} fact uses value null.")
        if self.state == "none" and (not self.basis or self.alternatives):
            raise ValueError("A none fact needs evidence of absence and no alternatives.")
        if self.state == "unknown" and self.alternatives:
            raise ValueError("An unknown fact has no alternatives; keep unresolved hints in a basis note.")
        if self.state == "conflicting" and len(self.alternatives) < 2:
            raise ValueError("A conflicting fact needs at least two evidenced alternatives.")
        return self


class Creator(Compact):
    name: TextFact
    role: str = Field(min_length=1)


class Identifier(Compact):
    scheme: str = Field(min_length=1)
    value: str = Field(min_length=1)
    basis: list[EvidencePointer] = Field(min_length=1)


class SourceFactsPatch(Compact):
    """Supplied fields replace values in full."""
    kind: Literal["book", "article", "document", "unknown"] | None = None
    title: TextFact | None = None
    container_title: TextFact | None = None
    publication_date: TextFact | None = None
    publisher: TextFact | None = None
    full_citation: TextFact | None = None
    creators: list[Creator] | None = None
    identifiers: list[Identifier] | None = None

    @model_validator(mode="before")
    @classmethod
    def no_null(cls, data):
        # Omission keeps the base value; null is not a fact. Use an explicit
        # unknown TextFact or an empty list instead.
        if isinstance(data, dict):
            nulls = sorted(key for key, value in data.items() if value is None)
            if nulls:
                raise ValueError(f"source_update fields cannot be null: {', '.join(nulls)}. Omit a field to keep it, or supply "
                                 "a complete TextFact (state 'unknown' clears a fact) or an empty list.")
        return data


class Description(Compact):
    full: str = Field(description="Complete agent-authored description.")
    filename: str = Field(description="Faithful filename label within 180 UTF-8 bytes; never shortened by the app.")
    language: str = Field(min_length=1, description="BCP 47 tag or und.")
    punctuation: Literal["fullwidth", "ascii"]
    basis: list[EvidencePointer] = Field(default_factory=list)


class Location(Compact):
    physical_page: int = Field(ge=1)
    region: list[float] | None = Field(default=None, min_length=4, max_length=4)
    basis: list[EvidencePointer] = Field(min_length=1)


class LocatorGroup(Compact):
    kind: Literal["single", "range"]
    pages: list[int] = Field(min_length=1)
    basis: list[EvidencePointer] = Field(default_factory=list)


class OccurrenceFacts(Compact):
    image_ref: str = Field(min_length=1, description="render_page/extract_image ref.")
    description: Description
    caption: TextFact = Field(default_factory=TextFact)
    image_title: TextFact = Field(default_factory=TextFact)
    figure: TextFact = Field(default_factory=TextFact, description="Source figure label; never invented.")
    locations: list[Location] = Field(min_length=1)
    locator_groups: list[LocatorGroup] = Field(default_factory=list, description="Omit for one single group per page.")


class AssetCreate(Compact):
    kind: Literal["create"]
    client_key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$", description="Markdown destination asset:new/<client_key>.")
    facts: OccurrenceFacts
    legacy_path: str | None = Field(default=None, description="Adopt a schema 1 assets/<sha256> path.")


class AssetCorrect(Compact):
    kind: Literal["correct"]
    occurrence_id: str
    changes: dict[str, Any]


class Page(Strict):
    printed: str = "unknown"
    disposition: Literal["unprocessed", "included", "outside_scope", "omitted_non_content"] = "unprocessed"
    note: str = ""
    printed_state: Literal["known", "none", "unknown"] | None = None
    printed_basis: list[EvidencePointer] = Field(default_factory=list)
    printed_alternatives: list[Alternative] = Field(default_factory=list)


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
    asset_changes: list[AssetCreate | AssetCorrect] = Field(default_factory=list, description="Create source-image occurrences; the save replaces asset:new/<client_key> with the assigned URI.")
    source_update: SourceFactsPatch = Field(default_factory=SourceFactsPatch)

    @model_validator(mode="after")
    def one_source(self):
        if self.mode == "edit" and self.base_version != self.expected_head:
            raise ValueError("Ordinary edits require base_version == expected_head. Read the current head and reuse retained candidate blocks for a local repair, or explicitly choose mode='rebuild' to reconstruct from another base.")
        if self.replace_blocks is not None and self.reuse_candidate is not None:
            raise ValueError("Use either replacement blocks or a candidate reference.")
        return self


def pointer(value: Any, path: str) -> Any:
    if not isinstance(path, str):
        raise ValueError("JSON Pointer must be a string; use '' for the complete root.")
    if not path:
        return value
    if not path.startswith("/"):
        raise ValueError("Use an RFC 6901 JSON Pointer beginning with '/'.")
    traversed = ""
    for part in path[1:].split("/"):
        if re.search(r"~(?![01])", part):
            raise ValueError("Invalid JSON Pointer escape; use ~0 for '~' and ~1 for '/'.")
        key = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", key):
                raise ValueError("JSON Pointer array indices must be nonnegative integers without leading zeros.")
            index = int(key)
            if index >= len(value):
                raise ValueError(f"JSON Pointer array at {traversed or '(root)'} has {len(value)} items; index {index} is outside it.")
            value = value[index]
        elif isinstance(value, dict):
            if key not in value:
                keys = list(value)
                available = repr(keys[:12]) + (f" (first 12 of {len(keys)} keys)" if len(keys) > 12 else "")
                hint = ""
                if not traversed and isinstance(value.get("content"), dict) and key in value["content"]:
                    hint = f" Saved document fields are under /content; use /content/{part}."
                raise ValueError(f"JSON Pointer key {key!r} is absent at {traversed or '(root)'}. Available keys: {available}.{hint}")
            value = value[key]
        else:
            raise ValueError(f"JSON Pointer cannot descend through the scalar at {traversed or '(root)'}. Read that value directly.")
        traversed += "/" + part
    return value
