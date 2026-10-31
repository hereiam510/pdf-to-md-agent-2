"""R07 execution evidence: synthetic HTTP only, real catalog/graph and reopen.

Complete malformed replies, decoder failures and incomplete transport evidence
are separate cases. No decoder is replaced to make a native shape reachable.
"""
from copy import deepcopy
import json

import httpx
import pytest

from pdfmd.nexus import Nexus, StopRun
from pdfmd.runtime import Runtime
from pdfmd.server import Engine
from pdfmd.storage import Store
from tests.engine.execution.test_continuation import delivery, check_delivery, use_protocol
from tests.engine.execution.test_runtime import tool
from tests.engine.transport.test_response_repairs import native, seed_compaction, handoff
from tests.engine.transport.test_streaming_delivery import WAIT, stream_frames
from tests.engine.transport.test_stream_terminal import Body, event, forbidden


ORIGINALS = [
    pytest.param("chat_completions", b"[]", id="cc-array"),
    pytest.param("chat_completions", b'{"choices":[{"finish_reason":"stop","message":null}]}', id="cc-null-message"),
    pytest.param("responses", b'{"status":"completed","output":[null]}', id="responses-null-item"),
]


def state(runtime, job):
    return deepcopy(runtime.graph.get_state({"configurable": {"thread_id": job["id"]}}).values)


def run(store, job, transport, *, compact=False, credentials=None, continue_failed=False):
    runtime = Runtime(store, Nexus(store, credentials or (lambda _: "synthetic-only"), transport))
    try:
        if compact:
            seed_compaction(runtime, store, job)
        runtime.run(job["id"], continue_failed=continue_failed)
        return state(runtime, job)
    finally:
        runtime.close()


def configure(store, job, protocol, streaming):
    use_protocol(store, job, protocol)
    current = store.get("job", job["id"])
    store.update_job(job["id"], route={**current["route"], "wait_policy": WAIT if streaming else None})


def assert_failed_reopen(store, job, request, before_state, transport, expected="rejected"):
    """Inspect/reconcile and plain graph re-entry cannot grant failed Continue."""
    identity = job["id"]
    old_attempt = store.get("attempt", request["attempts"][0])
    old_payload = store.bytes(request["payload_ref"], identity)
    original_blobs = {b["ref"]: store.bytes(b["ref"], identity) for b in store.records("blob", identity)}
    operations = store.records("operation", identity)
    versions = store.records("version", identity)
    count = store.get("job", identity)["attempts"]
    reopened = Store(store.root)
    engine = Engine(store.root, transport=transport)
    try:
        assert not engine.futures and not engine.keys
        assert engine.store.get("request", request["id"]) == request
    finally:
        engine.close()
    service = Nexus(reopened, forbidden, transport)
    assert service.reconcile(identity, request["id"]) == request
    with pytest.raises(StopRun) as stopped:
        service.send(identity, request["id"])
    assert stopped.value.reason == ("response_rejected" if expected == "rejected" else "unknown_outcome")
    after = run(reopened, job, transport, credentials=forbidden)
    for key in ("history", "handoff", "notes", "pinned", "released", "revision", "pending"):
        assert after.get(key) == before_state.get(key)
    assert reopened.get("request", request["id"]) == request
    assert reopened.get("attempt", old_attempt["id"]) == old_attempt
    assert reopened.bytes(request["payload_ref"], identity) == old_payload
    assert reopened.get("job", identity)["attempts"] == count
    assert reopened.records("operation", identity) == operations
    assert reopened.records("version", identity) == versions
    assert all(reopened.bytes(ref, identity) == raw for ref, raw in original_blobs.items())
    assert not any(b["kind"] == "request_continuation" for b in reopened.records("blob", identity))
    return old_attempt, original_blobs


def assert_rejection(store, job, snapshot, compact, seen):
    current = store.get("job", job["id"])
    assert current["stop_reason"] == "response_rejected" and current["attempts"] == len(seen) == 1
    request = store.get("request", snapshot["pending"])
    assert request["kind"] == ("compaction" if compact else "normal")
    assert request["status"] == "rejected" and request["accepted_ref"] is None
    assert request["failure"]["reason"] == "response_rejected"
    assert len(request["attempts"]) == 1
    attempt = store.get("attempt", request["attempts"][0])
    assert attempt["status"] == "rejected" and attempt["finished"] >= attempt["started"]
    assert attempt["http_status"] == 200 and attempt["usage"] is None and attempt["remote_cancelled"] is None
    assert attempt["transport"]["settled"]
    assert not any(b["kind"] == "accepted_response" and b["meta"].get("request") == request["id"]
                   for b in store.records("blob", job["id"]))
    assert not any(op.get("id", "").startswith(request["id"] + ":") for op in store.records("operation", job["id"]))
    assert snapshot["handoff"] is None and snapshot["pinned"] == []
    assert snapshot["notes"] == ("Preserve all source values." if compact else "")
    assert snapshot["history"] == (["large-history"] if compact else [])
    return request, attempt


@pytest.mark.parametrize("compact", [False, True], ids=["normal", "compaction"])
@pytest.mark.parametrize("protocol,raw", ORIGINALS)
def test_original_complete_malformed_replies_settle_and_reopen(delivery, protocol, raw, compact):
    store, job, version, _, _ = delivery
    configure(store, job, protocol, False)
    seen = []
    transport = httpx.MockTransport(lambda req: seen.append(req.content) or httpx.Response(200, content=raw))
    snapshot = run(store, job, transport, compact=compact)
    request, attempt = assert_rejection(store, job, snapshot, compact, seen)
    assert attempt["transport"]["body_complete"] is True
    assert attempt["transport"]["diagnostic"]["stage"] == "native"
    assert store.bytes(request["response_ref"], job["id"]) == raw
    assert store.get("blob", request["response_ref"])["meta"]["complete_transport"] is True
    assert store.get("job", job["id"])["head"] == version
    assert_failed_reopen(store, job, request, snapshot, transport)
    assert len(seen) == 1


def stream_case(protocol, case):
    if case == "container":
        # CC has delta, not message: the null-message complete-response example
        # cannot arise from this decoder. Responses carries the original output.
        return ([event([])] if protocol == "chat_completions" else
                [event({"type": "response.completed", "response": {"status": "completed", "output": [None]}})]), "decoder"
    if case == "empty":
        return ([event({"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}), b"data: [DONE]\n\n"]
                if protocol == "chat_completions" else
                [event({"type": "response.completed", "response": {"status": "completed", "output": []}})]), "native"
    value = native(protocol, tool("context_update", {"notes": "Must never apply"}, "blocked-policy"),
                   tool("edit_document", {"title": "Must never save"}, "blocked-edit"))
    # A complete native function argument string can still contain invalid JSON.
    if case != "missing-terminal":
        if protocol == "chat_completions":
            value["choices"][0]["message"]["tool_calls"][1]["function"]["arguments"] = "["
        else:
            value["output"][1]["arguments"] = "["
    frames = stream_frames(protocol, value)
    return (frames[:-1], "unknown") if case == "missing-terminal" else (frames, "native")


@pytest.mark.parametrize("compact", [False, True], ids=["normal", "compaction"])
@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("case", ["container", "empty", "arguments", "missing-terminal"])
def test_stream_boundaries_preserve_evidence_and_reopen(delivery, protocol, compact, case):
    store, job, version, _, _ = delivery
    configure(store, job, protocol, True)
    chunks, boundary = stream_case(protocol, case)
    seen, bodies = [], []
    def reply(req):
        seen.append(req.content)
        body = Body(chunks)
        bodies.append(body)
        return httpx.Response(200, stream=body)
    transport = httpx.MockTransport(reply)
    snapshot = run(store, job, transport, compact=compact)
    if boundary == "unknown":
        request = store.get("request", snapshot["pending"])
        assert request["status"] == "unknown" and request["accepted_ref"] is None
        assert store.get("job", job["id"])["stop_reason"] == "unknown_outcome"
        attempt = store.get("attempt", request["attempts"][0])
        assert attempt["transport"]["stop_cause"] == "stream_incomplete"
        assert not attempt["transport"]["protocol_complete"]
        assert attempt["usage"] is None and attempt["remote_cancelled"] is None
    else:
        request, attempt = assert_rejection(store, job, snapshot, compact, seen)
        assert attempt["transport"]["diagnostic"]["stage"] == ("native" if boundary == "native" else "decode")
        assert attempt["transport"]["protocol_complete"] == (boundary == "native")
    assert bodies[0].closed
    raw = store.bytes(request["stream_ref"], job["id"])
    assert raw == b"".join(bodies[0].received) == b"".join(chunks)
    assert store.read_stream(job["id"], request["id"], request["attempts"][0])["data"] == raw
    if boundary == "native":
        assembled = store.get("blob", request["response_ref"])
        assert assembled["kind"] == "assembled_response" and assembled["meta"]["source_stream_ref"] == request["stream_ref"]
    assert store.get("job", job["id"])["head"] == version
    assert_failed_reopen(store, job, request, snapshot, transport, "unknown" if boundary == "unknown" else "rejected")
    if boundary == "unknown":
        # Ordinary failed Continue is not authority to replace unknown input,
        # including a compaction without its separate exact-ID recovery choice.
        run(Store(store.root), job, transport, credentials=forbidden, continue_failed=True)
        assert store.get("request", request["id"]) == request
        assert not any(b["kind"] == "request_continuation" for b in store.records("blob", job["id"]))
    assert len(seen) == store.get("job", job["id"])["attempts"] == 1


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("compact", [False, True], ids=["normal", "compaction"])
def test_explicit_failed_continue_survives_receipt_gap_without_rewriting_attempt(delivery, tmp_path, protocol, streaming, compact, monkeypatch):
    store, job, version, image, source = delivery
    configure(store, job, protocol, streaming)
    seen = []
    def reply(req):
        seen.append(req.content)
        payload = json.loads(req.content)
        if len(seen) == 1:
            if streaming:
                return httpx.Response(200, stream=Body(stream_case(protocol, "arguments")[0]))
            # Retain an apparently useful tool before the invalid item. Neither
            # context nor document changes may execute from this rejected reply.
            value = native(protocol, tool("context_update", {"notes": "Must never apply"}))
            if protocol == "responses":
                value["output"].append(None)
            else:
                value["choices"].append(None)
            value["usage"] = {"prompt_tokens": 100, "completion_tokens": 50} if protocol == "chat_completions" else {"input_tokens": 100, "output_tokens": 50}
        else:
            if len(seen) == 2:
                assert ("Request continuation record" if payload.get("tools") else "request_continuation") in json.dumps(payload)
            value = (native(protocol, text=json.dumps(handoff(job, current_state="Preserve complete version " + version)))
                     if not payload.get("tools") else native(protocol, tool("report", {"state": "complete", "version_id": version, "message": "Preserved source and image"})))
        return httpx.Response(200, stream=Body(stream_frames(protocol, value))) if streaming else httpx.Response(200, json=value)
    transport = httpx.MockTransport(reply)
    snapshot = run(store, job, transport, compact=compact)
    original, _ = assert_rejection(store, job, snapshot, compact, seen)
    old_attempt, blobs = assert_failed_reopen(store, job, original, snapshot, transport)
    completed_operations = store.records("operation", job["id"])
    if not streaming:
        # Reported counts survive in raw even though rejected content has no
        # accepted usage ledger. Attempt count is not a known monetary charge.
        assert store.json(original["response_ref"], job["id"])["usage"] is not None
    runtime = Runtime(store, Nexus(store, lambda _: "synthetic-only", transport))
    update = runtime.graph.update_state
    def fault(*args, **kwargs):
        raise RuntimeError("synthetic gap after durable Continue receipt")
    monkeypatch.setattr(runtime.graph, "update_state", fault)
    try:
        with pytest.raises(RuntimeError, match="durable Continue receipt"):
            runtime.run(job["id"], continue_failed=True)
    finally:
        monkeypatch.setattr(runtime.graph, "update_state", update)
        runtime.close()
    receipt_ref = "continuation:" + original["id"]
    receipt = store.bytes(receipt_ref, job["id"])
    feedback = store.json(receipt_ref, job["id"])
    assert feedback["attempts"] == original["attempts"] and feedback["response_ref"] == original["response_ref"]
    assert feedback["reason"] == "response_rejected"
    run(Store(store.root), job, transport)  # Recover recorded choice, no second authorization.
    assert store.get("job", job["id"])["status"] == "completed"
    assert len(seen) == store.get("job", job["id"])["attempts"] == (3 if compact else 2)
    assert store.get("request", original["id"]) == original
    assert store.get("attempt", old_attempt["id"]) == old_attempt
    assert all(store.bytes(ref, job["id"]) == data for ref, data in blobs.items())
    assert store.bytes(receipt_ref, job["id"]) == receipt
    assert len([b for b in store.records("blob", job["id"]) if b["kind"] == "request_continuation"]) == 1
    assert len([e for e in store.events(job["id"]) if e["type"] == "request_continued"]) == 1
    assert len(store.records("version", job["id"])) == 1
    assert all(op in store.records("operation", job["id"]) for op in completed_operations)
    assert not any(op.get("id", "").startswith(original["id"] + ":") for op in store.records("operation", job["id"]))
    check_delivery(store, job, version, image, source, tmp_path / "preserved.zip")


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("known_usage", [False, True])
def test_valid_controls_accept_once_with_truthful_usage_and_reopen(delivery, tmp_path, protocol, streaming, known_usage):
    store, job, version, image, source = delivery
    configure(store, job, protocol, streaming)
    value = native(protocol, tool("report", {"state": "complete", "version_id": version, "message": "Valid complete control"}))
    usage = ({"prompt_tokens": 100, "completion_tokens": 50} if protocol == "chat_completions" else
             {"input_tokens": 100, "output_tokens": 50}) if known_usage else None
    value["usage"] = usage
    seen = []
    def reply(req):
        seen.append(req.content)
        if not streaming:
            return httpx.Response(200, json=value)
        chunks = stream_frames(protocol, value)
        if not known_usage:
            # Fixture construction only. Received/stored evidence is never edited.
            chunks = [part.replace(json.dumps({"prompt_tokens": 100, "completion_tokens": 50}).encode(), b"null")
                      .replace(json.dumps({"input_tokens": 100, "output_tokens": 50}).encode(), b"null") for part in chunks]
        return httpx.Response(200, stream=Body(chunks))
    run(store, job, httpx.MockTransport(reply))
    assert store.get("job", job["id"])["status"] == "completed"
    request = store.records("request", job["id"])[0]
    attempt = store.get("attempt", request["attempts"][0])
    assert request["status"] == attempt["status"] == "accepted" and attempt["usage"] == usage
    accepted = Nexus(Store(store.root), forbidden).send(job["id"], request["id"])
    assert accepted["usage"] == usage and len(accepted["calls"]) == 1
    assert store.get("job", job["id"])["attempts"] == len(seen) == 1
    check_delivery(store, job, version, image, source, tmp_path / "valid-control.zip")
