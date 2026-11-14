import json

import httpx
import pytest

from pdfmd.nexus import Nexus
from pdfmd.request_estimation import estimate
from pdfmd.runtime import Runtime
from pdfmd.schema import Route
from pdfmd.storage import InvalidUnicode, Store
from pdfmd.documents import Documents
from tests.engine.context.test_context_admission import protocol_job
from tests.engine.documents.test_documents import edit
from tests.engine.execution.test_continuation import continue_job
from tests.engine.execution.test_runtime import tool
from tests.engine.transport.test_response_repairs import native
from tests.engine.transport.test_streaming_delivery import WAIT


def wire(protocol, value, streaming):
    def event(value):
        return b"data: " + json.dumps(value, ensure_ascii=True).encode() + b"\n\n"
    if not streaming:
        return json.dumps(value, ensure_ascii=True).encode()
    if protocol == "chat_completions":
        choice = value["choices"][0]
        delta = choice["message"].copy()
        if delta.get("tool_calls"):
            delta["tool_calls"] = [{"index": i, **call} for i, call in enumerate(delta["tool_calls"])]
        return event({"id": "reply", "choices": [{"index": 0, "delta": delta,
                       "finish_reason": choice["finish_reason"]}]}) + b"data: [DONE]\n\n"
    return event({"type": "response.completed", "response": {"id": "reply", **value}})


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("field", ["text", "arguments"])
@pytest.mark.parametrize("bad", ["\ud800", "\udfff"])
def test_invalid_reply_blocks_then_explicit_continue_saves_exact_text(setup, tmp_path, protocol, streaming, field, bad):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    if streaming:
        store.update_job(job["id"], route={**job["route"], "wait_policy": WAIT})
    invalid = native(protocol, text="A" + bad + "C") if field == "text" else native(protocol,
        tool("report", {"state": "waiting", "message": "A" + bad + "C"}, "bad-call"))
    valid_text = "Valid 😀 𠀀"
    valid = native(protocol,
        tool("edit_document", edit([{"id": "body", "pages": [1], "markdown": valid_text}]), "save"),
        tool("report", {"state": "waiting", "message": valid_text}, "good-call"))
    received = wire(protocol, invalid, streaming)
    sent = []
    def reply(request):
        sent.append(request.content)
        return httpx.Response(200, content=received if len(sent) == 1 else wire(protocol, valid, streaming),
                              headers={"Content-Type": "text/event-stream" if streaming else "application/json"})
    runtime = Runtime(store, Nexus(store, lambda _: "offline", httpx.MockTransport(reply)))
    try:
        runtime.run(job["id"])
    finally:
        runtime.close()
    current = store.get("job", job["id"])
    assert current["status"] == "blocked" and current["stop_reason"] == "response_rejected", current
    assert len(sent) == current["attempts"] == 1
    [first] = store.records("request", job["id"])
    assert first["status"] == "rejected" and first["failure"]["class"] == "rejected_reply"
    assert first["accepted_ref"] is None
    if streaming and field == "text":
        [attempt] = store.records("attempt", job["id"])
        assert attempt["transport"]["diagnostic"]["field"] == "unicode"
    else:
        assert "character offset 1" in first["failure"]["message"]
    assert store.bytes(first["stream_ref"] if streaming else first["response_ref"], job["id"]) == received
    assert not store.records("operation", job["id"]) and current["head"] is None
    # Reopening alone neither retries nor grants automatic repair.
    reopened = Runtime(Store(store.root), Nexus(store, lambda _: "offline", httpx.MockTransport(reply)))
    try:
        reopened.run(job["id"])
    finally:
        reopened.close()
    assert len(sent) == 1
    continue_job(store, job, httpx.MockTransport(reply))  # Existing Engine.start Continue path.
    current = Store(store.root).get("job", job["id"])
    assert current["status"] == "waiting" and current["last_message"] == valid_text, current
    assert len(sent) == current["attempts"] == 2
    assert store.records("request", job["id"])[1]["status"] == "accepted"
    assert store.get("request", first["id"]) == first
    assert store.bytes(first["stream_ref"] if streaming else first["response_ref"], job["id"]) == received
    assert not [event for event in store.events(job["id"]) if event["type"] == "response_correction"]
    assert len(store.records("operation", job["id"])) == 2
    documents = Documents(Store(store.root))
    assert documents.version(job["id"], current["head"])["content"]["blocks"][0]["markdown"] == valid_text
    assert documents.export(job["id"], current["head"], str(tmp_path / "continued.zip"))["verified"]


@pytest.mark.parametrize("producer", ["estimation", "freeze"])
def test_request_preparation_fallback_rejects_before_freezing(setup, producer):
    store, job = setup
    payload = {"model": job["route"]["model"], "messages": [{"role": "user", "content": "A\ud800C"}]}
    with pytest.raises(InvalidUnicode, match=r"U\+D800.*character offset 1"):
        if producer == "estimation":
            estimate(payload, Route.model_validate(job["route"]))
        else:
            Nexus(store, lambda _: pytest.fail("No provider call")).freeze(job["id"], "invalid", payload, "normal", {})
    assert not store.records("request", job["id"])
    assert payload["messages"][0]["content"] == "A\ud800C"
