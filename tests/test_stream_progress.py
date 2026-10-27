"""Offline protocol progress, time boundaries and durable receive/acceptance gates."""
import asyncio
import json

import httpx
import pytest

from pdfmd.nexus import Nexus, StopRun, make_payload
from pdfmd.schema import Route
from pdfmd.storage import Store, encode
from test_context_admission import protocol_job
from test_request_deadline import Body, Clock


PROTOCOLS = ["chat_completions", "responses"]


def sse(value):
    return b"data: " + encode(value) + b"\n\n"


def delta(protocol, text):
    if protocol == "chat_completions":
        return sse({"id": "reply-1", "choices": [{"index": 0, "delta": {"role": "assistant", "content": text}, "finish_reason": None}]})
    return sse({"type": "response.output_text.delta", "item_id": "msg-1", "output_index": 0,
                "content_index": 0, "delta": text})


def ending(protocol, text):
    if protocol == "chat_completions":
        return sse({"id": "reply-1", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 4}}) + b"data: [DONE]\n\n"
    return sse({"type": "response.completed", "response": {"id": "reply-1", "status": "completed",
                "output": [{"id": "msg-1", "type": "message", "status": "completed", "role": "assistant",
                            "content": [{"type": "output_text", "text": text}]}],
                "usage": {"input_tokens": 10, "output_tokens": 4}}})


def frozen_stream(setup, protocol, body, clock, *, policy=None):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    route = {**job["route"], "wait_policy": policy or {
        "first_progress_seconds": 600, "idle_progress_seconds": 300, "total_seconds": None}}
    store.update_job(job["id"], route=Route.model_validate(route).model_dump())
    seen = []
    def handle(request):
        seen.append({"payload": json.loads(request.content), "timeout": request.extensions["timeout"]})
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=body)
    nexus = Nexus(store, lambda _: "fixture-private-credential", httpx.MockTransport(handle), clock=clock)
    payload = make_payload(Route.model_validate(route), "Offline fixture only.", [], [])
    request = nexus.freeze(job["id"], "stream-request", payload, "compaction", {})
    return store, job, nexus, request, seen


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_continued_progress_exceeds_old_and_candidate_total_cutoffs_then_accepts_without_eof(setup, protocol):
    clock = Clock()
    parts = [(500, delta(protocol, "Keep ")), (750, delta(protocol, "25 mg. ")),
             (1000, delta(protocol, "Complete.")), (1250, ending(protocol, "Keep 25 mg. Complete."))]
    body = Body(parts, clock=clock, hold=True)
    store, job, nexus, request, seen = frozen_stream(setup, protocol, body, clock)
    accepted = nexus.send(job["id"], request["id"])
    assert accepted["text"] == "Keep 25 mg. Complete."
    assert seen[0]["payload"]["stream"] is True and seen[0]["timeout"]["read"] is None
    assert seen[0]["timeout"]["connect"] == 30 and seen[0]["timeout"]["write"] == 30
    if protocol == "chat_completions":
        assert seen[0]["payload"]["stream_options"] == {"include_usage": True}
    attempt = store.records("attempt", job["id"])[0]
    observed = attempt["transport"]
    assert observed["first_progress_elapsed_seconds"] == 500
    assert observed["last_progress_elapsed_seconds"] == 1000
    assert observed["terminal_elapsed_seconds"] == 1250 and observed["elapsed_seconds"] == 1250
    assert observed["deadline_seconds"] is None and observed["protocol_complete"]
    assert observed["body_complete"] is False and observed["stop_cause"] == "complete" and body.closed
    raw = store.bytes(accepted["stream_ref"], job["id"])
    assert raw == b"".join(b for _, b in parts)
    assert store.get("blob", accepted["native_ref"])["kind"] == "assembled_response"
    assert store.get("blob", accepted["native_ref"])["meta"]["source_stream_ref"] == accepted["stream_ref"]
    assert len(store.records("stream_receive", job["id"])[0]["chunks"]) == 4
    reopened = Store(store.root)
    # Accepted bytes win even when current settings change or credentials/network disappear.
    reopened.update_job(job["id"], route={**job["route"], "timeout_seconds": 1})
    assert Nexus(reopened, lambda _: pytest.fail("Must not request credentials")).send(job["id"], request["id"]) == accepted
    assert reopened.get("job", job["id"])["attempts"] == 1


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("kind", ["heartbeat", "empty_delta", "late_first", "idle", "late_terminal", "total"])
def test_only_timely_generation_can_extend_wait_and_late_event_cannot_revive(setup, protocol, kind):
    clock = Clock()
    policy = {"first_progress_seconds": 600, "idle_progress_seconds": 300, "total_seconds": 600 if kind == "total" else None}
    if kind == "heartbeat":
        chunks = [(100, b": keep-alive\n\n"), (400, b": keep-alive\n\n"), (601, b": keep-alive\n\n")]
    elif kind == "empty_delta":
        chunks = [(100, delta(protocol, "\n\n")), (500, delta(protocol, " ")), (601, delta(protocol, "\n"))]
    elif kind == "late_first":
        chunks = [(601, delta(protocol, "Too late"))]
    else:
        chunks = [(100, delta(protocol, "Timely"))]
        if kind == "total":
            chunks += [(350, delta(protocol, " continued")), (550, delta(protocol, " progress")), (601, delta(protocol, " active"))]
        elif kind == "late_terminal":
            chunks += [(401, ending(protocol, "Timely"))]
        else:
            chunks += [(250, b": heartbeat\n\n"), (401, delta(protocol, " late"))]
    body = Body(chunks, clock=clock, hold=True)
    store, job, nexus, request, _ = frozen_stream(setup, protocol, body, clock, policy=policy)
    with pytest.raises(StopRun) as failure:
        nexus.send(job["id"], request["id"])
    assert failure.value.reason == "unknown_outcome"
    attempt = store.records("attempt", job["id"])[0]
    expected = "total_deadline" if kind == "total" else "progress_idle_timeout" if kind in {"idle", "late_terminal"} else "first_progress_timeout"
    assert attempt["transport"]["stop_cause"] == expected and body.closed
    assert attempt["usage"] is None and attempt["remote_cancelled"] is None
    assert store.bytes(attempt["stream_ref"], job["id"]) == b"".join(b for _, b in chunks)
    assert not store.records("operation", job["id"])
    with pytest.raises(StopRun):
        Nexus(Store(store.root), lambda _: pytest.fail("Unknown must not resend")).send(job["id"], request["id"])
    assert store.get("job", job["id"])["attempts"] == 1


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_header_only_wait_retains_status_without_waiting_for_body_bytes(setup, protocol):
    clock = Clock()
    class Silent(httpx.AsyncByteStream):
        async def __aiter__(self):
            clock.value = 601
            await asyncio.Event().wait()
            yield b""
    store, job, nexus, request, _ = frozen_stream(setup, protocol, Silent(), clock)
    with pytest.raises(StopRun):
        nexus.send(job["id"], request["id"])
    attempt = store.records("attempt", job["id"])[0]
    assert attempt["http_status"] == 200
    assert attempt["transport"]["first_body_elapsed_seconds"] is None
    assert attempt["transport"]["stop_cause"] == "first_progress_timeout"


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("failure_mode", ["eof", "error", "read_timeout"])
def test_partial_failed_and_disconnected_streams_never_execute(setup, protocol, failure_mode):
    clock = Clock()
    chunks = [(1, delta(protocol, "Incomplete useful draft"))]
    if failure_mode == "error":
        chunks.append((2, sse({"type": "error", "error": {"message": "do-not-expose-private-key"}})))
    body = Body(chunks, clock=clock, failure=httpx.ReadTimeout("private") if failure_mode == "read_timeout" else None)
    store, job, nexus, request, _ = frozen_stream(setup, protocol, body, clock)
    with pytest.raises(StopRun) as stopped:
        nexus.send(job["id"], request["id"])
    assert stopped.value.reason == ("response_rejected" if failure_mode == "error" else "unknown_outcome")
    current = store.get("request", request["id"])
    assert current["accepted_ref"] is None and not store.records("operation", job["id"])
    assert store.bytes(current["stream_ref"], job["id"]) == b"".join(b for _, b in chunks)
    assert "do-not-expose-private-key" not in str(stopped.value)
    assert len([b for b in store.records("blob", job["id"]) if b["kind"] == "stream_chunk"]) == len(chunks)


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_staged_acceptance_survives_pointer_failure_and_reentry_without_resending(setup, protocol, monkeypatch):
    clock = Clock()
    body = Body([(1, delta(protocol, "Done")), (2, ending(protocol, "Done"))], clock=clock)
    store, job, nexus, request, _ = frozen_stream(setup, protocol, body, clock)
    original_put = store.put
    def crash(kind, key, job_id, value):
        if kind == "request" and value.get("accepted_ref"):
            raise OSError("injected pointer failure")
        return original_put(kind, key, job_id, value)
    monkeypatch.setattr(store, "put", crash)
    with pytest.raises(OSError):
        nexus.send(job["id"], request["id"])
    reopened = Store(store.root)
    accepted = Nexus(reopened, lambda _: pytest.fail("Saved acceptance must win")).send(job["id"], request["id"])
    assert accepted["text"] == "Done" and accepted["stream_ref"]
    current = reopened.get("request", request["id"])
    assert current["stream_ref"] == accepted["stream_ref"] and current["response_ref"] == accepted["native_ref"]
    assert len(reopened.records("attempt", job["id"])) == 1
    restored = reopened.records("attempt", job["id"])[0]
    assert restored["transport"]["protocol_complete"] and restored["transport"]["settled"]
    assert restored["transport"]["first_progress_elapsed_seconds"] == 1
    assert restored["stream_ref"] == accepted["stream_ref"] and restored["http_status"] == 200


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("cancel", [True, False])
def test_stop_or_budget_before_terminal_wins_even_without_poll_yield(setup, protocol, cancel):
    clock = Clock()
    store, initial = setup
    class Interrupted(Body):
        async def __aiter__(self):
            yield delta(protocol, "Partial")
            store.update_job(initial["id"], **({"cancel_requested": True} if cancel else {"active_seconds": 99999999}))
            yield ending(protocol, "Partial")
    body = Interrupted([])
    store, job, nexus, request, _ = frozen_stream(setup, protocol, body, clock)
    with pytest.raises(StopRun) as failure:
        nexus.send(job["id"], request["id"])
    assert failure.value.reason == ("cancelled" if cancel else "budget_exhausted")
    assert store.get("request", request["id"])["accepted_ref"] is None
    assert store.get("job", job["id"])["attempts"] == 1
    assert store.records("attempt", job["id"])[0]["transport"]["stop_cause"] == ("user_stop" if cancel else "active_time_limit")


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("close_fails", [False, True])
def test_timely_terminal_ends_generation_wait_before_slow_or_failed_cleanup(setup, protocol, close_fails):
    clock = Clock()
    class LateClose(Body):
        async def aclose(self):
            self.closed = True
            clock.value = 700
            await asyncio.sleep(0.01)
            if close_fails:
                raise httpx.ReadError("private cleanup error")
    body = LateClose([(1, delta(protocol, "Done")), (2, ending(protocol, "Done"))], clock=clock)
    store, job, nexus, request, _ = frozen_stream(setup, protocol, body, clock)
    assert nexus.send(job["id"], request["id"])["text"] == "Done"
    observed = store.records("attempt", job["id"])[0]["transport"]
    assert observed["terminal_elapsed_seconds"] == 2 and observed["receive_elapsed_seconds"] == 2
    assert observed["stop_cause"] == "complete" and observed["cleanup_complete"] is (not close_fails)
    assert observed["elapsed_seconds"] == 700
    assert "private cleanup" not in json.dumps(observed)


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_valid_progress_before_error_in_same_chunk_is_not_lost(setup, protocol):
    clock = Clock()
    raw = delta(protocol, "Retained draft") + sse({"type": "error", "error": {"message": "withheld"}})
    body = Body([(7, raw)], clock=clock)
    store, job, nexus, request, _ = frozen_stream(setup, protocol, body, clock)
    with pytest.raises(StopRun):
        nexus.send(job["id"], request["id"])
    observed = store.records("attempt", job["id"])[0]["transport"]
    assert observed["first_event_elapsed_seconds"] == 7
    assert observed["first_progress_elapsed_seconds"] == 7 and observed["progress_count"] == 1
    assert observed["terminal_event"] == "error" and observed["stop_cause"] == "stream_error"
    assert store.get("request", request["id"])["accepted_ref"] is None
