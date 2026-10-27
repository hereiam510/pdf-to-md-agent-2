"""Offline receive observations and the total deadline, independent of provider latency."""
import asyncio
import json
import time

import httpx
import pytest

from pdfmd.nexus import Nexus, StopRun, make_payload
from pdfmd.schema import Route
from pdfmd.storage import Store, encode
from test_context_admission import protocol_job
from test_response_repairs import native


PROTOCOLS = ["chat_completions", "responses"]


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


class Body(httpx.AsyncByteStream):
    def __init__(self, chunks, *, failure=None, clock=None, hold=False):
        self.chunks, self.failure, self.clock, self.hold = chunks, failure, clock, hold
        self.closed = False

    async def __aiter__(self):
        for elapsed, chunk in self.chunks:
            if self.clock:
                self.clock.value = elapsed
            yield chunk
        if self.failure:
            raise self.failure
        if self.hold:
            await asyncio.Event().wait()

    async def aclose(self):
        self.closed = True


def frozen(setup, protocol, transport, *, deadline=180, clock=None):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    store.update_job(job["id"], route={**job["route"], "timeout_seconds": deadline})
    job = store.get("job", job["id"])
    nexus = Nexus(store, lambda _: "do-not-record-this-credential", transport, **({"clock": clock} if clock else {}))
    payload = make_payload(Route.model_validate(job["route"]), "Offline fixture.", [], [])
    request = nexus.freeze(job["id"], "observed-request", payload, "compaction", {})
    return store, job, nexus, request


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_headers_and_partial_body_survive_read_timeout_without_executing_or_replaying(setup, protocol):
    body = Body([(0, b'{"incomplete":')], failure=httpx.ReadTimeout("secret credential must not be logged"))
    store, job, nexus, request = frozen(setup, protocol, httpx.MockTransport(lambda _: httpx.Response(200, stream=body)))
    original = store.bytes(request["payload_ref"], job["id"])
    with pytest.raises(StopRun, match="Remote|remote|Upstream|upstream") as stopped:
        nexus.send(job["id"], request["id"])
    assert stopped.value.reason == "unknown_outcome"
    attempt = store.records("attempt", job["id"])[0]
    assert attempt["http_status"] == 200
    observed = attempt["transport"]
    assert observed["stop_cause"] == "read_timeout" and observed["settled"]
    assert observed["headers_elapsed_seconds"] is not None
    assert 0 <= observed["first_body_elapsed_seconds"] <= observed["last_body_elapsed_seconds"] <= observed["elapsed_seconds"]
    assert observed["received_body_bytes"] == len(b'{"incomplete":') and observed["body_complete"] is False
    assert body.closed and attempt["usage"] is None and attempt["remote_cancelled"] is None
    current = store.get("request", request["id"])
    assert current["status"] == "unknown" and current["accepted_ref"] is None
    parts = [b for b in store.records("blob", job["id"]) if b["kind"] == "partial_native_response"]
    assert len(parts) == 1 and store.bytes(parts[0]["ref"], job["id"]) == b'{"incomplete":'
    assert not store.records("operation", job["id"])
    with pytest.raises(StopRun):
        Nexus(Store(store.root), lambda _: "unused").send(job["id"], request["id"])
    assert len(store.records("attempt", job["id"])) == 1
    assert store.bytes(request["payload_ref"], job["id"]) == original
    assert "secret credential" not in json.dumps(current) + json.dumps(attempt)


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("deadline,finishes", [(180, False), (600, True)])
def test_later_complete_reply_uses_frozen_deadline_not_latest_task_value(setup, protocol, deadline, finishes):
    clock = Clock()
    raw = encode(native(protocol, text="Complete local reply."))
    body = Body([(181, raw)], clock=clock, hold=not finishes)
    observed_timeouts = []
    def handle(request):
        observed_timeouts.append(request.extensions["timeout"])
        return httpx.Response(200, stream=body)
    store, job, nexus, request = frozen(setup, protocol, httpx.MockTransport(handle), deadline=deadline, clock=clock)
    store.update_job(job["id"], route={**job["route"], "timeout_seconds": 600 if deadline == 180 else 180})
    if finishes:
        assert nexus.send(job["id"], request["id"])["text"] == "Complete local reply."
    else:
        with pytest.raises(StopRun) as stopped:
            nexus.send(job["id"], request["id"])
        assert stopped.value.reason == "unknown_outcome"
    attempt = store.records("attempt", job["id"])[0]
    observation = attempt["transport"]
    assert observation["deadline_seconds"] == deadline and observation["elapsed_seconds"] == 181
    assert observation["connect_timeout_seconds"] == 30
    assert observation["stop_cause"] == ("complete" if finishes else "request_deadline")
    assert observation["body_complete"] is finishes and body.closed
    assert observed_timeouts == [{"connect": 30, "read": deadline, "write": deadline, "pool": deadline}]
    assert attempt["status"] == ("accepted" if finishes else "unknown")


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_incoming_body_does_not_restart_total_deadline(setup, protocol):
    clock = Clock()
    body = Body([(200, b'{"partial":'), (400, b'"kept'), (601, b' bytes"')], clock=clock, hold=True)
    store, job, nexus, request = frozen(setup, protocol, httpx.MockTransport(lambda _: httpx.Response(200, stream=body)), deadline=600, clock=clock)
    with pytest.raises(StopRun) as stopped:
        nexus.send(job["id"], request["id"])
    assert stopped.value.reason == "unknown_outcome"
    observed = store.records("attempt", job["id"])[0]["transport"]
    assert observed["stop_cause"] == "request_deadline" and observed["elapsed_seconds"] == 601
    assert observed["first_body_elapsed_seconds"] == 200 and observed["last_body_elapsed_seconds"] == 601
    assert observed["received_body_bytes"] == len(b'{"partial":"kept bytes"')
    assert body.closed and store.get("job", job["id"])["attempts"] == 1


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("real_clock", [False, True])
def test_completed_late_response_cannot_skip_deadline_but_keeps_complete_bytes(setup, protocol, real_clock):
    clock = None if real_clock else Clock()
    raw = encode(native(protocol, text="A late complete candidate is preserved."))
    class CompletedLate(Body):
        async def __aiter__(self):
            if real_clock:
                # Deliberately block the test event loop so the poller cannot win first.
                time.sleep(1.05)
            else:
                clock.value = 181
            yield raw
    body = CompletedLate([])
    store, job, nexus, request = frozen(setup, protocol, httpx.MockTransport(lambda _: httpx.Response(200, stream=body)),
                                       deadline=1 if real_clock else 180, clock=clock)
    with pytest.raises(StopRun) as stopped:
        nexus.send(job["id"], request["id"])
    assert stopped.value.reason == "unknown_outcome"
    attempt = store.records("attempt", job["id"])[0]
    observation = attempt["transport"]
    assert observation["stop_cause"] == "request_deadline" and observation["body_complete"]
    assert observation["body_complete_elapsed_seconds"] >= observation["deadline_seconds"]
    current = store.get("request", request["id"])
    assert current["status"] == "unknown" and current["accepted_ref"] is None
    assert store.bytes(current["response_ref"], job["id"]) == raw
    blob = store.get("blob", current["response_ref"])
    assert blob["kind"] == "native_response" and blob["meta"]["complete_transport"] is True
    assert blob["meta"]["within_deadline"] is False and body.closed
    assert not any(b["kind"] == "partial_native_response" for b in store.records("blob", job["id"]))
    assert not store.records("operation", job["id"])


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_gateway_status_is_known_without_reading_or_archiving_its_error_body(setup, protocol):
    class ForbiddenBody(Body):
        async def __aiter__(self):
            raise AssertionError("Do not read an arbitrary HTTP error body.")
            yield b"secret"
    body = ForbiddenBody([])
    store, job, nexus, request = frozen(setup, protocol, httpx.MockTransport(lambda _: httpx.Response(502, stream=body)), deadline=600)
    with pytest.raises(StopRun) as stopped:
        nexus.send(job["id"], request["id"])
    assert stopped.value.reason == "provider_error"
    attempt = store.records("attempt", job["id"])[0]
    assert attempt["http_status"] == 502 and attempt["status"] == "http_error"
    assert attempt["transport"]["stop_cause"] == "http_error"
    assert attempt["transport"]["headers_elapsed_seconds"] is not None
    assert attempt["transport"]["body_complete"] is None and attempt["transport"]["received_body_bytes"] == 0
    assert body.closed and not any(b["kind"] in {"native_response", "partial_native_response"} for b in store.records("blob", job["id"]))


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("error,cause", [(httpx.ConnectTimeout,"connect_timeout"), (httpx.ReadTimeout,"read_timeout"),
    (httpx.WriteTimeout,"write_timeout"), (httpx.PoolTimeout,"pool_timeout"), (httpx.ConnectError,"transport_error")])
def test_before_headers_failure_is_distinct_and_does_not_leak_exception_text(setup, protocol, error, cause):
    def handle(_):
        raise error("private-token-and-url")
    store, job, nexus, request = frozen(setup, protocol, httpx.MockTransport(handle))
    with pytest.raises(StopRun):
        nexus.send(job["id"], request["id"])
    attempt = store.records("attempt", job["id"])[0]
    observed = attempt["transport"]
    assert attempt["http_status"] is None and observed["headers_elapsed_seconds"] is None
    assert observed["first_body_elapsed_seconds"] is None and observed["received_body_bytes"] == 0
    assert observed["stop_cause"] == cause and observed["settled"]
    assert "private-token-and-url" not in json.dumps(attempt) + json.dumps(store.get("request", request["id"]))


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("boundary,cause", [("cancel_requested", "user_stop"), ("active_seconds", "active_time_limit")])
def test_stop_and_persistent_budget_interrupt_body_with_observations(setup, protocol, boundary, cause):
    store, initial = setup
    class Interrupt(Body):
        async def __aiter__(self):
            yield b"retained partial"
            store.update_job(initial["id"], **{boundary: True if boundary == "cancel_requested" else 99999999})
            await asyncio.Event().wait()
    body = Interrupt([])
    store, job, nexus, request = frozen(setup, protocol, httpx.MockTransport(lambda _: httpx.Response(200, stream=body)))
    with pytest.raises(StopRun) as stopped:
        nexus.send(job["id"], request["id"])
    assert stopped.value.reason == ("cancelled" if boundary == "cancel_requested" else "budget_exhausted")
    attempt = store.records("attempt", job["id"])[0]
    assert attempt["transport"]["stop_cause"] == cause and attempt["http_status"] == 200
    assert attempt["transport"]["received_body_bytes"] == len(b"retained partial") and body.closed


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_complete_transport_does_not_accept_incomplete_native_reply(setup, protocol):
    value = native(protocol, text="Useful but not accepted.")
    if protocol == "chat_completions":
        value["choices"][0]["finish_reason"] = "length"
    else:
        value["status"] = "incomplete"
    store, job, nexus, request = frozen(setup, protocol, httpx.MockTransport(lambda _: httpx.Response(200, json=value)))
    with pytest.raises(StopRun) as stopped:
        nexus.send(job["id"], request["id"])
    assert stopped.value.reason == "response_rejected"
    attempt = store.records("attempt", job["id"])[0]
    assert attempt["transport"]["body_complete"] and attempt["transport"]["stop_cause"] == "complete"
    assert store.get("request", request["id"])["accepted_ref"] is None
    assert any(b["kind"] == "native_response" for b in store.records("blob", job["id"]))
