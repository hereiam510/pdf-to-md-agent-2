"""Pure interpretation of native accounting, independent of content acceptance.

Original reports belong to immutable native/SSE evidence. ``value`` is a
validated projection, never a bill. Missing fields are not zero. Details are
subsets of their parent, not extra tokens. Unknown metadata remains in raw
evidence and is excluded from validated counts and aggregate comparison.
"""
from copy import deepcopy
from dataclasses import dataclass


@dataclass(frozen=True)
class Usage:
    value: dict | None
    status: str
    reason: str | None = None


def interpret_usage(protocol: str, raw) -> Usage:
    if raw is None:
        return Usage(None, "unknown", "missing")
    if not isinstance(raw, dict):
        return Usage(None, "unknown", "container")
    incoming, outgoing, details_in, details_out = (
        ("prompt_tokens", "completion_tokens", "prompt_tokens_details", "completion_tokens_details")
        if protocol == "chat_completions" else
        ("input_tokens", "output_tokens", "input_tokens_details", "output_tokens_details"))
    main = (incoming, outgoing, "total_tokens")
    subsets = ((details_in, incoming, ("cached_tokens", "cache_write_tokens", "audio_tokens", "image_tokens", "text_tokens")),
               (details_out, outgoing, ("reasoning_tokens", "audio_tokens", "text_tokens", "accepted_prediction_tokens", "rejected_prediction_tokens"))) if protocol == "chat_completions" else (
               (details_in, incoming, ("cached_tokens", "cache_write_tokens")),
               (details_out, outgoing, ("reasoning_tokens",)))
    present = 0
    for name in main:
        if name in raw and raw[name] is not None:
            if type(raw[name]) is not int or raw[name] < 0:
                return Usage(None, "unknown", "count")
            present += 1
    if all(raw.get(name) is not None for name in main):
        if raw[incoming] + raw[outgoing] != raw["total_tokens"]:
            return Usage(None, "unknown", "total")
    for container, parent, names in subsets:
        detail = raw.get(container)
        if detail is None:
            continue
        if not isinstance(detail, dict):
            return Usage(None, "unknown", "details_container")
        for name in names:
            if detail.get(name) is None:
                continue
            count = detail[name]
            if type(count) is not int or count < 0:
                return Usage(None, "unknown", "count")
            present += 1
            if raw.get(parent) is not None and count > raw[parent]:
                return Usage(None, "unknown", "subset")
    write_details = None
    if protocol == "responses":
        detail = raw.get(details_in) or {}
        # Official Responses caching semantics: reads and writes do not
        # overlap; write lifetimes partition writes, never additional tokens.
        if (raw.get(incoming) is not None and all(detail.get(k) is not None for k in ("cached_tokens", "cache_write_tokens"))
                and detail["cached_tokens"] + detail["cache_write_tokens"] > raw[incoming]):
            return Usage(None, "unknown", "subset")
        writes = detail.get("cache_write_tokens_details")
        if writes is not None:
            if not isinstance(writes, dict):
                return Usage(None, "unknown", "details_container")
            write_details = {k: writes[k] for k in ("ttl_30m_tokens", "ttl_12h_tokens") if k in writes}
            parent = detail.get("cache_write_tokens")
            for count in write_details.values():
                if count is None:
                    continue
                if type(count) is not int or count < 0:
                    return Usage(None, "unknown", "count")
                present += 1
                if parent is not None and count > parent:
                    return Usage(None, "unknown", "subset")
            if parent is not None and all(write_details.get(k) is not None for k in ("ttl_30m_tokens", "ttl_12h_tokens")):
                if sum(write_details.values()) != parent:
                    return Usage(None, "unknown", "details_total")
    if not present:
        return Usage(None, "unknown", "missing")
    validated = {key: deepcopy(raw[key]) for key in main if key in raw}
    for container, _, names in subsets:
        if container in raw:
            validated[container] = ({key: deepcopy(raw[container][key]) for key in names if key in raw[container]}
                                    if isinstance(raw[container], dict) else None)
    if write_details is not None:
        validated.setdefault(details_in, {})["cache_write_tokens_details"] = deepcopy(write_details)
    return Usage(validated, "complete" if all(raw.get(k) is not None for k in main) else "partial")


def accounting_fields(raw: dict) -> dict:
    """Only accounting meaning participates in duplicate aggregate comparison."""
    result = {}
    for key, value in raw.items():
        if isinstance(value, dict):
            value = accounting_fields(value)
            if not value:
                continue
        if value is not None:
            result[key] = deepcopy(value)
    return result
