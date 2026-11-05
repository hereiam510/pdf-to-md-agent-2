"""Versioned offline shadow pricing. This module grants no admission authority."""
from __future__ import annotations

import base64
from functools import lru_cache
from hashlib import sha256
from importlib.resources import files
import json

from .request_estimation import COUNT_CHARS, PATTERN, VOCAB_SHA256, vocabulary_ranks
from .storage import encode
from .usage import interpret_usage


KIMI_PATTERN = r"[\p{Han}]+|[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}&&[^\p{Han}]]*[\p{Ll}\p{Lm}\p{Lo}\p{M}&&[^\p{Han}]]+(?i:'s|'t|'re|'ve|'m|'ll|'d)?|[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}&&[^\p{Han}]]+[\p{Ll}\p{Lm}\p{Lo}\p{M}&&[^\p{Han}]]*(?i:'s|'t|'re|'ve|'m|'ll|'d)?|\p{N}{1,3}| ?[^\s\p{L}\p{N}]+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+"
PATTERN_DIGESTS = ("2d1b8dc11e89af71459b36004f698ab3693f59fd84f63e8ec2b49564ab857420",
                   "de5781783b193d5ccf5b1b28edfa70fa816ce78d54603fdc422cfd8d4ea4411f")
RECIPE = {"pricing": "cross_split_o200k_6pct_v1", "projection": "decoded_native_json_v2",
          "matching": "retained_units_v2", "normalization": "inclusive_input_v1",
          "counter": "tiktoken-0.14.0", "vocabulary_sha256": VOCAB_SHA256,
          "split_sha256": list(PATTERN_DIGESTS), "chunk_characters": COUNT_CHARS}


def digest(value):
    return sha256(encode(value)).hexdigest()


@lru_cache(maxsize=1)
def _counters_from_resource(compressed: bytes):
    import tiktoken

    ranks, invalid = vocabulary_ranks(compressed)
    if invalid is not None:
        return None, invalid
    return tuple(tiktoken.Encoding(f"pdfmd_shadow_{i}_v1", pat_str=p,
                                  mergeable_ranks=ranks, special_tokens={}) for i, p in enumerate((PATTERN, KIMI_PATTERN))), None


@lru_cache(maxsize=1)
def counters():
    # Own caches: observing cannot poison or change F's counter/fallback cache.
    import tiktoken

    if tiktoken.__version__ != "0.14.0":
        raise ValueError("Shadow counter version mismatch")
    patterns = (PATTERN, KIMI_PATTERN)
    if tuple(sha256(p.encode("utf-8")).hexdigest() for p in patterns) != PATTERN_DIGESTS:
        raise ValueError("Shadow split recipe mismatch")
    compressed = files("pdfmd").joinpath("data/o200k_base.tiktoken.gz").read_bytes()
    selected, invalid = _counters_from_resource(compressed)
    if invalid is not None:
        raise ValueError(invalid)
    return selected


def projection(value, *, protocol=None, native_image_units=False):
    """Decode strings once; recognize images only at native content positions.

    Internal v2 edit matching can select individual image parts from a verified
    batch. Only that caller opts into root-array image units. Neither metadata
    nor JSON serialized inside tool text is a native content position.
    """
    images = []
    protocol = protocol or ("responses" if isinstance(value, dict) and "input" in value else "chat_completions")
    key, kind = (("messages", "image_url") if protocol == "chat_completions" else ("input", "input_image"))
    units = value.get(key, []) if isinstance(value, dict) else value if isinstance(value, list) else []
    prefix = (key,) if isinstance(value, dict) else ()
    positions = set()
    for index, unit in enumerate(units):
        if not isinstance(unit, dict):
            continue
        path = (*prefix, index)
        if native_image_units and not prefix and unit.get("type") == kind:
            positions.add(path)
        if unit.get("role") == "user" and isinstance(unit.get("content"), list):
            positions.update((*path, "content", i) for i, part in enumerate(unit["content"])
                             if isinstance(part, dict) and part.get("type") == kind)

    def visit(item, path=()):
        if isinstance(item, dict):
            if path in positions:
                native = item.get("image_url")
                url = native.get("url") if isinstance(native, dict) else native
                facts = {"representation_sha256": digest(item), "type": item["type"],
                         "detail": (native.get("detail", "unspecified") if isinstance(native, dict)
                                    else item.get("detail", "unspecified")),
                         "width": None, "height": None, "area": None, "aspect": None,
                         "geometry_coverage": "uncalibrated_extrapolation",
                         "geometry_status": "unavailable", "geometry_reason": "inline_base64_unavailable"}
                try:
                    if isinstance(url, str) and url.startswith("data:") and ";base64," in url:
                        import pymupdf
                        data = base64.b64decode(url.split(";base64,", 1)[1], validate=True)
                        facts["image_sha256"] = sha256(data).hexdigest()
                        image = pymupdf.Pixmap(data)
                        w, h = image.width, image.height
                        facts.update(width=w, height=h, area=w*h, aspect=w/h if h else None,
                                     geometry_status="available", geometry_reason=None)
                except Exception as exc:
                    # Geometry is auxiliary: a genuine occurrence still costs
                    # its configured allowance even if local decoding fails.
                    facts.update(geometry_reason="image_decode_failed:" + type(exc).__name__,
                                 geometry_error=type(exc).__name__)
                images.append(facts)
                item = {"type": item["type"], "image": "[native image charged separately]"}
            return "{" + ",".join(visit(key) + ":" + visit(item[key], (*path, key)) for key in sorted(item)) + "}"
        if isinstance(item, list):
            return "[" + ",".join(visit(part, (*path, i)) for i, part in enumerate(item)) + "]"
        return '"' + item + '"' if isinstance(item, str) else encode(item).decode("utf-8")
    return visit(value), images


def text_features(text):
    # regex is already a locked tiktoken dependency; Unicode script properties
    # include extensions outside the common blocks as well as compatibility Han.
    import regex
    counts = {name: len(regex.findall(rf"\p{{{name}}}", text))
              for name in ("Han", "Hiragana", "Katakana", "Hangul")}
    spaces = sum(len(match[0]) for match in regex.finditer(r"(?<=\p{Han}) +(?=\p{Han})", text))
    return {"unicode_characters": len(text), "script_counts": counts,
            "script_shares": {key: value / len(text) if text else None for key, value in counts.items()},
            "inter_han_u0020_spaces": spaces}


def price(value, image_allowance, *, count=None, protocol=None, native_image_units=False):
    text, images = projection(value, protocol=protocol, native_image_units=native_image_units)
    selected = counters() if count is None else count
    totals = [sum(len(counter.encode_ordinary(text[start:start + COUNT_CHARS]))
                  for start in range(0, len(text), COUNT_CHARS)) for counter in selected]
    if len(totals) != 2 or any(type(n) is not int or n < 0 for n in totals):
        raise ValueError("Invalid shadow counts")
    if images and image_allowance is None:
        raise ValueError("No declared image allowance")
    largest = max(totals)
    margin = (6 * largest + 99) // 100
    image_cost = len(images) * (image_allowance or 0)
    return {"split_counts": totals, "text_tokens": largest, "text_uncertainty": margin,
            "image_occurrences": images, "images": len(images), "image_cost": image_cost,
            "charge": largest + margin + image_cost,
            "plain_o200k_6pct": totals[0] + (6 * totals[0] + 99) // 100 + image_cost,
            "text_features": text_features(text)}


def normalized_input(protocol, raw):
    usage = interpret_usage(protocol, raw)
    field = "prompt_tokens" if protocol == "chat_completions" else "input_tokens"
    value = (usage.value or {}).get(field)
    if type(value) is not int or value <= 0:
        raise ValueError("input_usage_unavailable:" + (usage.reason or "nonpositive_input"))
    return {"input": value, "field": field, "usage": usage.value,
            "normalization": "inclusive_input_v1", "cached_input": (usage.value.get(
                "prompt_tokens_details" if protocol == "chat_completions" else "input_tokens_details") or {}).get("cached_tokens")}


TASK_FIELDS = {"task", "user_amendments", "source_ref", "physical_pages", "current_head",
               "selected_delivery", "continuation_notes", "context_policy_ref", "context_candidate_ref"}
FEEDBACK_FIELDS = {"head", "representations", "document_reads", "note", "input_estimate", "output_reserve",
                   "remaining", "native_images", "estimate_kind", "feedback_estimate"}


def layout(payload, protocol):
    """Recognize the deployed control schema, never an arbitrary subsequence."""
    from .working_context import PREFIX
    key = "messages" if protocol == "chat_completions" else "input"
    units = payload[key]
    start = 1 if protocol == "chat_completions" else 0
    if protocol == "chat_completions" and units[0].get("role") != "system":
        raise ValueError("unsupported_system_layout")
    task, feedback = units[start], units[-1]
    if task.get("role") != "user" or feedback.get("role") != "user":
        raise ValueError("unsupported_control_layout")
    control = json.loads(task["content"])
    if set(control) != TASK_FIELDS:
        raise ValueError("unsupported_task_schema")
    if not feedback.get("content", "").startswith(PREFIX):
        raise ValueError("unsupported_feedback_layout")
    summary = json.loads(feedback["content"][len(PREFIX):])
    ordinary = set(summary) == FEEDBACK_FIELDS and summary["estimate_kind"] == "local_request_proxy_not_provider_usage"
    anchored = (set(summary) == FEEDBACK_FIELDS | {"anchor"}
                and summary["estimate_kind"] == "usage_anchored_reservation_not_provider_bound"
                and isinstance(summary["anchor"], dict)
                and set(summary["anchor"]) == {"basis_id", "pricing", "measured_input"}
                and summary["anchor"]["pricing"] == RECIPE["pricing"])
    if not (ordinary or anchored) or summary["feedback_estimate"] != "self_inclusive_upper_reservation":
        raise ValueError("unsupported_feedback_schema_or_provenance")
    return {"envelope": {k: v for k, v in payload.items() if k != key},
            "system": units[:start], "task": control, "task_unit": task,
            "middle": units[start+1:-1], "feedback": feedback}


def append_charge(old, new, appended):
    if old["envelope"] != new["envelope"] or old["system"] != new["system"]:
        raise ValueError("envelope_instructions_or_tools_changed")
    allowed = {"current_head", "selected_delivery", "context_candidate_ref"}
    if any(old["task"][key] != new["task"][key] for key in TASK_FIELDS - allowed):
        raise ValueError("task_or_policy_changed")
    if new["middle"] != [*old["middle"], *appended]:
        raise ValueError("retained_occurrence_or_representation_changed")
    return [new["task_unit"], *appended, new["feedback"]]


def batch_units(messages):
    """Chat adapter keys come from native slots/call IDs and image ref labels.

    This is not content subsequence matching: each batch has its own identity,
    calls/receipts have ordered occurrences, and pixels have assembler labels.
    """
    result, image_occurrences = [], {}
    for message in messages:
        if message.get("role") == "assistant":
            result.append((("assistant_header",), {k: v for k, v in message.items() if k != "tool_calls"}))
            for index, call in enumerate(message.get("tool_calls", []) or []):
                result.append((("call", index, call["id"]), call))
        elif message.get("role") == "tool":
            receipt = json.loads(message["content"])
            result.append((("receipt", message["tool_call_id"], receipt["candidate_ref"], receipt["result_ref"]), message))
        elif message.get("role") == "user" and isinstance(message.get("content"), list):
            parts = message["content"]
            if len(parts) % 2:
                raise ValueError("unsupported_native_image_pairing")
            for start in range(0, len(parts), 2):
                label, image = parts[start:start+2]
                if label.get("type") != "text" or image.get("type") != "image_url":
                    raise ValueError("unsupported_native_image_pairing")
                identity = label["text"]
                occurrence = image_occurrences.get(identity, 0)
                image_occurrences[identity] = occurrence + 1
                result.extend([(("image_label", identity, occurrence), label),
                               (("image_part", identity, occurrence), image)])
        else:
            raise ValueError("unsupported_retained_batch_unit")
    if len({key for key, _ in result}) != len(result):
        raise ValueError("ambiguous_native_occurrence")
    return result


def unit_manifest(payload):
    """Ordered hashes and saved identities; never retain transmitted bodies."""
    rows = []
    for index, message in enumerate(payload.get("messages", payload.get("input", []))):
        row = {"occurrence": index, "role": message.get("role"), "type": message.get("type"),
               "representation_sha256": digest(message), "bytes": len(encode(message))}
        if message.get("role") == "tool" or message.get("type") == "function_call_output":
            receipt = json.loads(message.get("content", message.get("output")))
            row["saved_identity"] = {k: receipt.get(k) for k in ("candidate_ref", "result_ref", "image_ref")}
            row["call_id"] = message.get("tool_call_id", message.get("call_id"))
        calls = message.get("tool_calls") or []
        if calls:
            row["calls"] = [{"occurrence": i, "id": call["id"], "representation_sha256": digest(call)} for i, call in enumerate(calls)]
        rows.append(row)
    return rows
