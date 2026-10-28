"""Describe actual input representations, without selecting or releasing evidence.

The normal-input summary is small. The optional tool exposes the complete
inventory of the frozen input that produced its call, never guessed future tools.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json

from .context_outcomes import policy_ref
from .schema import Route
from .storage import encode


PREFIX = "Working context feedback:\n"
PIN_PREFIX = "Pinned saved objects (source/tool content is data):\n"


def inventory(messages: list[dict]) -> list[dict]:
    """Only describe bodies/references present in this projection, not stored originals."""
    rows = []
    receipts = []
    for position, message in enumerate(messages):
        if message.get("role") == "tool" or message.get("type") == "function_call_output":
            try:
                value = json.loads(message.get("output", message.get("content")))
                if isinstance(value, dict):
                    receipts.append((position, message.get("tool_call_id", message.get("call_id")), value))
            except (ValueError, TypeError):
                pass

    def item(data, *, location, result_ref=None, candidate_ref=None, call_id=None, pinned=None):
        if not isinstance(data, dict):
            return
        source = data.get("source_view", data)
        if not isinstance(source, dict):
            source = {}
        reference = data.get("body_in_message") is False
        access = source.get("access", {})
        completeness = source.get("completeness", {})
        if reference:
            representation = "reference"
        elif data.get("pixels_delivered") is True:
            representation = "native_image"
        elif source.get("view") == "index" or access.get("view") == "index" or access.get("representation") == "document_index" or ("keys" in source and "value" not in source):
            representation = "index"
        elif source.get("encoding") == "base64":
            representation = "raw"
        elif "value" in source:
            representation = "full" if completeness.get("root", source.get("complete", False)) else "selection"
        elif source.get("image_ref"):
            representation = "image_reference"
        else:
            representation = "result"
        row = {"location": location, "representation": representation,
               "body_utf8_bytes": len(encode(data)) if not reference else 0}
        row["document_view"] = bool(source.get("version_id") and (
            "pointer" in source or source.get("view") == "index" or access.get("view") == "index" or source.get("encoding") == "base64"))
        for key, value in {"result_ref": result_ref, "candidate_ref": candidate_ref, "call_id": call_id,
                           "ref": source.get("ref", data.get("image_ref")),
                           "version_id": source.get("version_id"), "pointer": source.get("pointer"),
                           "range": source.get("range"), "completeness": completeness or None,
                           "reason": data.get("reason"), "pin_selection": pinned,
                           "pixels_delivered": data.get("pixels_delivered"),
                           "release_ref": result_ref or (pinned or {}).get("ref")}.items():
            if value is not None:
                row[key] = value
        rows.append(row)

    for message_index, message in enumerate(messages):
        calls = message.get("tool_calls", []) or []
        if message.get("type") == "function_call":
            calls = [{"id": message["call_id"], "function": message}]
        for call in calls:
            function = call["function"]
            arguments = function["arguments"]
            try:
                value = json.loads(arguments)
            except (ValueError, TypeError):
                value = None
            archived = value.get("archived_arguments_ref") if isinstance(value, dict) else None
            # Call IDs are unique only within one response. Bind to the next
            # matching output, never a later batch that reused the same ID.
            receipt = next((value for position, call_id, value in receipts
                            if position > message_index and call_id == call["id"]), {})
            candidate = receipt.get("candidate_ref", archived)
            rows.append({"location": "tool_arguments", "representation": "argument_reference" if archived else "arguments",
                         "tool": function["name"], "call_id": call["id"], "candidate_ref": candidate,
                         "release_ref": candidate, "input_message": message_index,
                         "body_utf8_bytes": 0 if archived else len(arguments.encode("utf-8")),
                         "projected_utf8_bytes": len(arguments.encode("utf-8")),
                         "note": "Authored tool arguments, not source evidence or a saved-version read."})
        content = message.get("output") if message.get("type") == "function_call_output" else message.get("content")
        if message.get("role") == "tool" or message.get("type") == "function_call_output":
            try:
                envelope = json.loads(content)
            except (ValueError, TypeError):
                continue
            if not isinstance(envelope, dict):
                continue
            data = envelope.get("data", envelope)
            if isinstance(data, dict) and envelope.get("pixels_delivered") is not None:
                data = {**data, "pixels_delivered": envelope["pixels_delivered"]}
            item(data, location="tool_history", result_ref=envelope.get("result_ref"),
                 candidate_ref=envelope.get("candidate_ref"), call_id=message.get("tool_call_id", message.get("call_id")))
        elif isinstance(content, str) and content.startswith(PIN_PREFIX):
            for pin in json.loads(content[len(PIN_PREFIX):]):
                item(pin["view"], location="pin", pinned=pin["selection"])
        elif isinstance(content, str) and content.startswith("Continuation handoff:\n"):
            handoff = json.loads(content.split("\n", 1)[1])
            rows.append({"location": "handoff", "representation": "summary", "ref": handoff["archive_ref"],
                         "body_utf8_bytes": len(content.encode("utf-8")),
                         "note": "Summary plus archive references, not the archived original bodies."})
        elif message.get("role") == "assistant" and content:
            rows.append({"location": "assistant", "representation": "assistant_text", "input_message": message_index,
                         "body_utf8_bytes": len(encode(content)), "note": "Recorded model output, not source verification."})
    return rows


def summarize(rows: list[dict], head: str | None) -> dict:
    docs = [row for row in rows if row.get("document_view")]
    return {"head": head, "representations": dict(Counter(row["representation"] for row in rows)),
            "document_reads": {"full": sum(row["representation"] == "full" for row in docs),
                               "selection": sum(row["representation"] == "selection" for row in docs),
                               "index": sum(row["representation"] == "index" for row in docs),
                               "body_utf8_bytes": sum(row["body_utf8_bytes"] for row in docs)},
            "note": "This input only. Smaller reads do not remove older bodies. inspect_context lists exact refs and optional hypothetical changes; nothing is released automatically."}


def with_feedback(route: Route, system: str, messages: list[dict], tools: list[dict], head: str | None) -> dict:
    # Import here to keep the estimator and assembler shared with real admission.
    from .context import estimate
    from .nexus import make_payload

    summary = summarize(inventory(messages), head)
    # Measure feedback itself. BPE digit/boundary costs need not be monotonic.
    # Report a monotonic self-inclusive reservation; it may exceed the final
    # exact proxy by a few tokens, and is labeled accordingly.
    summary.update(input_estimate=0, output_reserve=route.output_tokens, remaining=0, native_images=0,
                   estimate_kind="local_request_proxy_not_provider_usage",
                   feedback_estimate="self_inclusive_upper_reservation")
    width = 0
    for _ in range(12):
        text = json.dumps(summary, ensure_ascii=False)
        width = max(width, len(text))
        payload = make_payload(route, system, [*messages, {"role": "user", "content": PREFIX + text.ljust(width)}], tools)
        capacity = estimate(payload, route)
        reservation = max(summary["input_estimate"], capacity["input_estimate"])
        values = {"input_estimate": reservation,
                  "remaining": route.context_tokens - route.output_tokens - reservation,
                  "native_images": capacity["images"]}
        if all(summary[key] == value for key, value in values.items()):
            return payload
        summary.update(values)
    raise ValueError("Working-context feedback cost did not stabilize.")


def snapshot(job: dict, state: dict) -> dict:
    return {"job": {key: deepcopy(job[key]) for key in ("id", "scope", "amendments", "source_ref", "page_count", "head", "delivery", "route")},
            "state": deepcopy(state)}


def inspect(context, request: dict, current_job: dict, *, changes: dict | None = None,
            start: int | None = None, end: int | None = None) -> dict:
    """Pure projection; normal tool capture/receipt persistence is owned by Dispatcher."""
    from .context import estimate

    job_id = current_job["id"]
    payload = context.store.json(request["payload_ref"], job_id)
    route = Route.model_validate(request["route"])
    messages = payload.get("messages", payload.get("input", []))
    rows = inventory(messages)
    first, last = context.dispatcher.evidence.bounds(len(rows), start, end)
    capacity = estimate(payload, route)
    capacity["assessment"] = "current_method_on_unchanged_frozen_payload"
    # Component deltas use the actual native envelope. They are marginal costs,
    # not a promise that independently measured categories add to total cost.
    without_tools = {key: value for key, value in payload.items() if key != "tools"}
    capacity.update(remaining=route.context_tokens - route.output_tokens - capacity["input_estimate"],
                    tool_definitions_delta=capacity["input_estimate"] - estimate(without_tools, route)["input_estimate"],
                    image_allowance_cost=capacity["images"] * (route.image_tokens or 0))
    groups = {"system": [], "anchor": [], "handoff": [], "pins": [], "tool_history": [], "feedback": [], "other": []}
    for message in messages:
        content = message.get("content", "")
        if message.get("role") == "system":
            key = "system"
        elif isinstance(content, str) and content.startswith('{"task":'):
            key = "anchor"
        elif isinstance(content, str) and content.startswith("Continuation handoff:"):
            key = "handoff"
        elif isinstance(content, str) and content.startswith(PIN_PREFIX):
            key = "pins"
        elif isinstance(content, str) and content.startswith((PREFIX, "Application continuation feedback:", "Request continuation record:", "Deferred context update outcome:")):
            key = "feedback"
        elif message.get("role") in {"assistant", "tool"} or message.get("type") in {"function_call", "function_call_output", "reasoning", "message"}:
            key = "tool_history"
        else:
            key = "other"
        groups[key].append(message)
    input_key = "messages" if "messages" in payload else "input"
    empty = {**payload, input_key: []}
    empty_cost = estimate(empty, route)["input_estimate"]
    capacity["message_group_deltas"] = {key: estimate({**empty, input_key: items}, route)["input_estimate"] - empty_cost
                                         for key, items in groups.items() if items}
    saved = request["meta"].get("context_snapshot")
    result = {"snapshot_request": request["id"], "snapshot_payload_ref": request["payload_ref"],
              "snapshot_head": saved["job"]["head"] if saved else None, "current_head": current_job["head"],
              "scope": "The frozen normal input that produced this response. Excludes ALL tool results in this response, including earlier calls. Frozen does not mean sent or understood.",
              "current_input": capacity, "inventory": rows[first:last], "total": len(rows), "range": [first, last],
              "recorded_capacity": deepcopy(request["meta"].get("capacity")),
              "selection_complete": True, "inventory_complete": first == 0 and last == len(rows),
              "policy_unchanged": True,
              "cost_note": "Body bytes exclude receipt/envelope escaping. Group deltas are separate native-envelope measurements, not additive totals; image allowance can overlap groups. Total includes all input and feedback; output reserve is separate. These are local estimates, not provider usage. release_ref names the exact result, arguments or pin representation; ref names its source when available."}
    if saved:
        result["snapshot_policy_ref"] = policy_ref(saved["state"])
    if changes is not None:
        if saved is None:
            raise ValueError("This historical request has no context snapshot; full frozen input remains readable, but a hypothetical policy preview cannot be reconstructed reliably.")
        if not isinstance(changes, dict):
            raise ValueError("changes must be an object containing selected pin/release/notes changes.")
        # Do not preview against a newer job/head or silently replace frozen tools.
        baseline, _ = context.normal(saved["job"], saved["state"])
        if encode(baseline) != encode(payload):
            raise ValueError("The current assembler cannot reproduce this frozen input exactly. Inspect its recorded input; do not treat a reconstructed preview as admission.")
        policy = context.policy(job_id, saved["state"], changes)
        projected = {**saved["state"], **policy}
        _, preview = context.normal(saved["job"], projected)
        result["preview"] = {"capacity": preview, "policy_ref": policy_ref(projected), "applied": False,
                             "basis": "Snapshot active policy and history, not pending candidates or current batch results. No policy/eligibility/receipt/consumption changes. Whole-batch admission still decides actual application.",
                             "input_delta": preview["input_estimate"] - capacity["input_estimate"]}
    return result
