"""NET-01 acceptance using the graph, durable store and a synthetic clock pair."""
import asyncio
import json
import socket
import ssl

import httpx
import pytest

from pdfmd import network
from pdfmd.nexus import Nexus, StopRun
from pdfmd.runtime import Runtime
from pdfmd.server import Engine
from pdfmd.storage import Conflict, Store
from tests.engine.transport.test_request_deadline import Body
from tests.engine.transport.test_stream_progress import delta
from tests.engine.transport.test_streaming_delivery import WAIT, stream_frames
from tests.engine.execution.test_continuation import delivery, check_delivery
from tests.engine.execution.test_runtime import tool
from tests.engine.transport.test_response_repairs import native


class Clocks:
    def __init__(self, *, boot="boot-a", process="first", interrupt=100, working=100, wall=1_800_000_000):
        self.boot_identity, self.process_basis = boot, process
        self.uptime, self.active, self.timestamp = interrupt, working, wall

    def working(self):
        return self.active

    def interrupt(self):
        return self.uptime

    def monotonic(self):
        return self.uptime

    def wall(self):
        return self.timestamp

    def pair(self):
        return self.active, self.uptime

    def advance(self, seconds, *, asleep=False):
        self.uptime += seconds
        self.timestamp += seconds
        if not asleep:
            self.active += seconds


def runtime(store, reply, clocks=None, *, pause=None):
    clocks = clocks or Clocks()
    return Runtime(store, Nexus(store, lambda _: "fixture-secret", httpx.MockTransport(reply),
                                clocks=clocks, retry_sleep=pause or clocks.advance, jitter=lambda low, high: high))


def final(version):
    return httpx.Response(200, json=native("chat_completions", tool("report", {
        "state": "complete", "message": "Complete saved source.", "version_id": version})))


def fail(error, cause=None):
    def reply(_):
        raise error("private error text") from (cause() if cause else None)
    return reply


def test_loopback_refusal_uses_the_real_transport_cause():
    # Reserve a port without listening. No other process can take it before
    # the request, and the only connection attempt is on loopback.
    with socket.socket() as endpoint:
        endpoint.bind(("127.0.0.1", 0))
        port = endpoint.getsockname()[1]
        url = f"http://127.0.0.1:{port}/v1/chat/completions"
        async def connect():
            async with httpx.AsyncClient(trust_env=False) as client:
                with pytest.raises(httpx.ConnectError) as refused:
                    await client.post(url)
                return network.classify_transport(refused.value, url, "may_have_been_sent")
        assert asyncio.run(connect()) == ("unsent", "not_sent", f"Nexus proxy not reachable at 127.0.0.1:{port}.")


REFUSED = fail(httpx.ConnectError, ConnectionRefusedError)


@pytest.mark.parametrize("failed,category,evidence", [
    (REFUSED, "unsent", "not_sent"),
    (fail(httpx.ConnectError, socket.gaierror), "unsent", "not_sent"),
    (fail(httpx.ConnectTimeout), "unsent", "not_sent"),
    (fail(httpx.PoolTimeout), "unsent", "not_sent"),
    (fail(httpx.ReadTimeout), "lost_after_send", "may_have_been_sent"),
    (fail(httpx.WriteTimeout), "lost_after_send", "may_have_been_sent"),
    (fail(httpx.RemoteProtocolError), "lost_after_send", "may_have_been_sent"),
    *[(lambda _, status=status: httpx.Response(status), "transient_status", "response_observed")
      for status in sorted(network.TRANSIENT_STATUSES)],
])
def test_retry_preserves_payload_and_delivered_version(delivery, tmp_path, failed, category, evidence):
    store, job, version, image, source = delivery
    sends = []
    def reply(request):
        sends.append(request.content)
        return failed(request) if len(sends) == 1 else final(version)

    execution = runtime(store, reply)
    try:
        execution.run(job["id"])
    finally:
        execution.close()
    first, second = store.records("attempt", job["id"])
    assert (first["failure_class"], first["send_evidence"]) == (category, evidence)
    assert first["usage"] is None and first["remote_cancelled"] is None
    assert second["status"] == "accepted" and second["send_evidence"] == "response_observed"
    assert sends[0] == sends[1] and store.get("job", job["id"])["attempts"] == 2
    if failed is REFUSED:
        schedule = next(e["data"] for e in store.events(job["id"]) if e["type"] == "retry_scheduled")
        assert schedule["detail"] == "Nexus proxy not reachable at 127.0.0.1:8317."
    assert len(store.records("operation", job["id"])) == 2  # seed edit and report
    check_delivery(store, job, version, image, source, tmp_path / "recovered.zip")


@pytest.mark.parametrize("failure", [None, httpx.ReadError("synthetic socket reset")])
def test_stream_break_or_incomplete_prefix_preserves_evidence(delivery, tmp_path, failure):
    store, job, version, image, source = delivery
    store.update_job(job["id"], route={**job["route"], "wait_policy": WAIT})
    prefix = delta("chat_completions", "Incomplete native stream.")
    frames = stream_frames("chat_completions", final(version).json())
    def reply(_):
        if len(store.records("attempt", job["id"])) == 1:
            return httpx.Response(200, stream=Body([(0, prefix)], failure=failure))
        return httpx.Response(200, stream=Body([(0, part) for part in frames]))
    execution = runtime(store, reply)
    try:
        execution.run(job["id"])
    finally:
        execution.close()
    first, second = store.records("attempt", job["id"])
    assert first["failure_class"] == "lost_after_send" and first["send_evidence"] == "response_observed"
    assert store.bytes(first["stream_ref"], job["id"]) == prefix and second["status"] == "accepted"
    check_delivery(store, job, version, image, source, tmp_path / "stream.zip")


@pytest.mark.parametrize("headers,expected", [
    ({"Retry-After": "20"}, 20), ({"Retry-After": "yesterday"}, 2),
    ({"Retry-After": "Fri, 15 Jan 2027 08:00:20 GMT", "Date": "Fri, 15 Jan 2027 08:00:00 GMT"}, 20),
    ({"Retry-After": "Fri, 15 Jan 2027 08:00:20 GMT"}, 20),
])
def test_retry_after_forms(delivery, tmp_path, headers, expected):
    store, job, version, image, source = delivery
    clock = Clocks(wall=1_800_000_000)
    def reply(_):
        if len(store.records("attempt", job["id"])) == 1:
            return httpx.Response(503, headers=headers)
        assert clock.uptime == 100 + expected
        return final(version)
    execution = runtime(store, reply, clock)
    try:
        execution.run(job["id"])
    finally:
        execution.close()
    schedule = next(event["data"] for event in store.events(job["id"]) if event["type"] == "retry_scheduled")
    assert schedule["delay_seconds"] == expected
    assert schedule["source"] == ("backoff" if expected == 2 else "retry_after")
    check_delivery(store, job, version, image, source, tmp_path / "retry-after.zip")


@pytest.mark.parametrize("mode", ["stop", "requests", "active", "sleep"])
def test_wait_respects_controls_and_sleep_elapsed_time(delivery, tmp_path, mode):
    store, job, version, image, source = delivery
    clock = Clocks()
    def reply(_):
        if len(store.records("attempt", job["id"])) == 1:
            return httpx.Response(503, headers={"Retry-After": "8"})
        assert clock.uptime >= 108
        return final(version)
    def pause(seconds):
        assert seconds <= 1
        if mode == "sleep":
            clock.advance(10, asleep=True)
        elif mode == "stop":
            store.update_job(job["id"], cancel_requested=True)
        else:
            field = "max_requests" if mode == "requests" else "max_active_seconds"
            store.update_job(job["id"], limits={**job["limits"], field: 1})
            clock.advance(1)
    execution = runtime(store, reply, clock, pause=pause)
    try:
        execution.run(job["id"])
        current = store.get("job", job["id"])
        if mode == "sleep":
            assert current["active_seconds"] == 0 and current["attempts"] == 2
            assert [r["duration_seconds"] for r in store.records("suspended_interval", job["id"])] == [10]
        else:
            assert current["attempts"] == 1
            assert current["stop_reason"] == ("cancelled" if mode == "stop" else "budget_exhausted")
            store.update_job(job["id"], cancel_requested=False, limits=job["limits"])
            clock.advance(8)
            execution.run(job["id"])
    finally:
        execution.close()
    check_delivery(store, job, version, image, source, tmp_path / "wait.zip")


@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("sleep", [False, True])
def test_receive_clocks_at_exchange_start(delivery, tmp_path, streaming, sleep):
    store, job, version, image, source = delivery
    store.update_job(job["id"], route={**job["route"], "timeout_seconds": 1,
                     "wait_policy": {"first_progress_seconds": 1, "idle_progress_seconds": 1} if streaming else None},
                     limits={**job["limits"], "automatic_retry": False})
    clock = Clocks()
    timeouts = []
    def reply(request):
        timeouts.append(request.extensions["timeout"])
        class Reply(httpx.AsyncByteStream):
            async def __aiter__(self):
                clock.advance(20 if sleep else 2, asleep=sleep)
                await asyncio.sleep(0)
                for part in (stream_frames("chat_completions", final(version).json()) if streaming else [final(version).content]):
                    yield part
        return httpx.Response(200, stream=Reply())
    execution = runtime(store, reply, clock)
    try:
        execution.run(job["id"])
    finally:
        execution.close()
    attempt = store.records("attempt", job["id"])[0]
    assert timeouts[0]["read"] is None and timeouts[0]["write"] == (30 if streaming else 1)
    if sleep:
        assert attempt["status"] == "accepted"
        assert store.get("job", job["id"])["active_seconds"] == 0
        assert len(store.records("suspended_interval", job["id"])) == 1
    else:
        assert attempt["failure_class"] == "lost_after_send"
        assert attempt["transport"]["stop_cause"] == ("first_progress_timeout" if streaming else "request_deadline")
    check_delivery(store, job, version, image, source, tmp_path / "receive.zip")


@pytest.mark.parametrize("mode", ["stalled", "oversized", "malformed", "stop", "known"])
def test_http_diagnostics_are_isolated(delivery, tmp_path, monkeypatch, mode):
    store, job, version, image, source = delivery
    monkeypatch.setattr(network, "DIAGNOSTIC_SECONDS", 0.15)
    async def reply(_):
        if len(store.records("attempt", job["id"])) > 1:
            return final(version)
        class ErrorBody(httpx.AsyncByteStream):
            async def __aiter__(self):
                admitted = store.records("attempt", job["id"])[0]
                assert admitted["http_status"] == 503 and admitted["retry_after_seconds"] == 1
                if mode == "oversized":
                    yield b"x" * (network.DIAGNOSTIC_BYTES + 1)
                elif mode == "malformed":
                    yield b'{"error": "fixture-secret"'
                elif mode == "known":
                    yield b'{"error":{"type":"server_error","message":"fixture-secret"}}'
                else:
                    if mode == "stop":
                        store.update_job(job["id"], cancel_requested=True)
                    await asyncio.Event().wait()
        return httpx.Response(503, stream=ErrorBody(), headers={"Content-Type": "application/json", "Retry-After": "1"})
    execution = runtime(store, reply)
    try:
        execution.run(job["id"])
        if mode == "stop":
            assert store.get("job", job["id"])["stop_reason"] == "cancelled"
            store.update_job(job["id"], cancel_requested=False)
            execution.run(job["id"])
    finally:
        execution.close()
    first, second = store.records("attempt", job["id"])
    assert first["failure_class"] == "transient_status" and first["transport"]["stop_cause"] == "http_error"
    assert first["upstream_code"] == ("server_error" if mode == "known" else "unavailable")
    assert second["status"] == "accepted"
    assert all(b"fixture-secret" not in path.read_bytes() for path in (store.root / "objects").iterdir())
    check_delivery(store, job, version, image, source, tmp_path / "diagnostics.zip")


@pytest.mark.parametrize("boundary", ["admission", "dispatch", "accepted"])
def test_attempt_recovery_distinguishes_admission_dispatch_and_acceptance(delivery, tmp_path, monkeypatch, boundary):
    store, job, version, image, source = delivery
    sent = []
    def reply(request):
        sent.append(request.content)
        if boundary == "dispatch" and len(sent) == 1:
            raise Interrupted
        return final(version)
    execution = runtime(store, reply)
    if boundary == "admission":
        original = store.json
        def stop_before_dispatch(ref, *args, **kwargs):
            if store.records("attempt", job["id"]) and store.get("blob", ref).get("kind") == "request_input":
                raise Interrupted
            return original(ref, *args, **kwargs)
        monkeypatch.setattr(store, "json", stop_before_dispatch)
    elif boundary == "accepted":
        monkeypatch.setattr(execution.nexus, "_settle_accepted", lambda *_args, **_kwargs: (_ for _ in ()).throw(Interrupted()))
    try:
        with pytest.raises(Interrupted):
            execution.run(job["id"])
    finally:
        execution.close()
    attempt = store.records("attempt", job["id"])[0]
    assert attempt["send_evidence"] == ("response_observed" if boundary == "accepted" else "may_have_been_sent")
    monkeypatch.undo()
    reopened = Store(store.root)
    resumed = runtime(reopened, reply)
    try:
        resumed.run(job["id"])
    finally:
        resumed.close()
    attempts = reopened.records("attempt", job["id"])
    assert len(attempts) == (1 if boundary == "accepted" else 2)
    if boundary != "accepted":
        assert attempts[0]["failure_class"] == "lost_after_send"
    assert attempts[-1]["status"] == "accepted"
    assert len(sent) == (2 if boundary == "dispatch" else 1)
    check_delivery(reopened, job, version, image, source, tmp_path / "crash.zip")


def test_compaction_retry_uses_shared_gate(delivery, tmp_path):
    from tests.engine.context.test_compaction_recovery import seed
    from tests.engine.transport.test_response_repairs import handoff
    store, job, version, image, source = delivery
    sends = []
    def reply(request):
        sends.append(request.content)
        if len(sends) <= 2:
            assert not json.loads(request.content).get("tools")
            if len(sends) == 1:
                raise httpx.ConnectTimeout("offline")
            return httpx.Response(200, json=native("chat_completions", text=json.dumps(handoff(job))))
        return final(version)
    execution = runtime(store, reply)
    try:
        seed(execution, store, job)
        execution.run(job["id"])
    finally:
        execution.close()
    attempts = store.records("attempt", job["id"])
    assert len(attempts) == 3 and attempts[0]["failure_class"] == "unsent"
    assert attempts[0]["request"] == attempts[1]["request"] and sends[0] == sends[1]
    check_delivery(store, job, version, image, source, tmp_path / "compaction.zip")


def test_historical_policy_and_complete_rejection(delivery, tmp_path, monkeypatch):
    store, job, version, image, source = delivery
    job_id = job["id"]
    def reply(_):
        attempts = store.records("attempt", job_id)
        if len(attempts) == 1:
            return httpx.Response(200, json={"choices": []})
        return final(version)
    execution = runtime(store, reply)
    freeze = execution.nexus.freeze
    def legacy(*args, **kwargs):
        request = freeze(*args, **kwargs)
        request["replay_policy"] = {"replay_unknown": False, "max_attempts_per_request": 1}
        store.put("request", request["id"], job_id, request)
        return request
    monkeypatch.setattr(execution.nexus, "freeze", legacy)
    try:
        execution.run(job_id)
        old = execution.pending_request(job_id)
        assert old["status"] == "rejected"
        assert store.get("job", job_id)["stop_reason"] == "response_rejected"
        assert store.get("attempt", old["attempts"][0])["failure_class"] == "rejected_reply"
        execution.run(job_id)
        assert store.get("job", job_id)["attempts"] == 1
        monkeypatch.undo()
        execution.run(job_id, continue_failed=True)
    finally:
        execution.close()
    assert store.get("request", old["id"]) == old
    check_delivery(store, job, version, image, source, tmp_path / "native-rejection.zip")


def test_legacy_frozen_request_never_gets_new_automatic_policy(delivery, tmp_path, monkeypatch):
    store, job, version, image, source = delivery
    job_id = job["id"]
    execution = runtime(store, lambda _: httpx.Response(503))
    freeze = execution.nexus.freeze
    def legacy(*args, **kwargs):
        request = freeze(*args, **kwargs)
        request["replay_policy"] = {"replay_unknown": False, "max_attempts_per_request": 1}
        store.put("request", request["id"], job_id, request)
        return request
    monkeypatch.setattr(execution.nexus, "freeze", legacy)
    try:
        execution.run(job_id)
        original = execution.pending_request(job_id)
        execution.run(job_id)
    finally:
        execution.close()
    assert store.get("request", original["id"]) == original
    assert store.get("job", job_id)["attempts"] == 1
    assert "retry_schedule" not in original
    check_delivery(store, job, version, image, source, tmp_path / "legacy.zip")


def test_tool_sleep_is_excluded_from_active_time(delivery, tmp_path, monkeypatch):
    store, job, version, image, source = delivery
    clock = Clocks()
    execution = runtime(store, lambda _: final(version), clock)
    dispatch = execution.dispatcher.execute
    def execute(*args, **kwargs):
        clock.advance(1, asleep=True)
        execution.active_time.checkpoint(force=False)
        clock.advance(10, asleep=True)
        clock.advance(2)
        return dispatch(*args, **kwargs)
    monkeypatch.setattr(execution.dispatcher, "execute", execute)
    try:
        execution.run(job["id"])
    finally:
        execution.close()
    assert store.get("job", job["id"])["active_seconds"] == 2
    assert [r["duration_seconds"] for r in store.records("suspended_interval", job["id"])] == [10]
    assert not store.records("active_time_gap", job["id"])
    check_delivery(store, job, version, image, source, tmp_path / "tool-sleep.zip")


@pytest.mark.parametrize("status", [400, 401, 403, 404, 413, 422, 501, 505, None])
def test_configuration_requires_continue(delivery, tmp_path, status):
    store, job, version, image, source = delivery
    def reply(request):
        if len(store.records("attempt", job["id"])) == 1:
            if status is None:
                return fail(httpx.ConnectError, ssl.SSLCertVerificationError)(request)
            return httpx.Response(status, json={"error": {"code": "fixture-secret", "message": "fixture-secret"}})
        return final(version)
    execution = runtime(store, reply)
    try:
        execution.run(job["id"])
        current = store.get("job", job["id"])
        assert current["stop_reason"] == "provider_configuration_error" and current["attempts"] == 1
        recovery = execution.network_recovery(job["id"])
        assert recovery["action"] == "continue"
        with pytest.raises(Conflict):
            execution.validate_network_retry(job["id"], recovery["request"])
        execution.run(job["id"], continue_failed=True)
    finally:
        execution.close()
    first, second = store.records("attempt", job["id"])
    assert first["http_status"] == status and second["status"] == "accepted"
    assert first.get("upstream_code") == ("unrecognized" if status else None)
    assert all(b"fixture-secret" not in path.read_bytes() for path in (store.root / "objects").iterdir())
    check_delivery(store, job, version, image, source, tmp_path / "continued.zip")


class Interrupted(BaseException):
    """Interrupt at a durable boundary without a failure settlement."""


@pytest.mark.parametrize("wall_jump,new_boot,expected", [(0, False, 40), (100, False, 40), (-50, False, 40),
                                                        (100, True, 60), (-50, None, 60)])
def test_wait_restart_uses_interrupt_clock(delivery, tmp_path, wall_jump, new_boot, expected):
    store, job, version, image, source = delivery
    clock = Clocks()
    def interrupt(_):
        clock.advance(20)
        raise Interrupted
    original = runtime(store, lambda _: httpx.Response(503, headers={"Retry-After": "60"}), clock, pause=interrupt)
    try:
        with pytest.raises(Interrupted):
            original.run(job["id"])
        pending = original.pending_request(job["id"])
        assert pending["retry_schedule"]["delay_seconds"] == 60
    finally:
        original.close()
    assert store.get("job", job["id"])["attempts"] == 1
    reopened = Store(store.root)
    now = Clocks(boot="boot-b" if new_boot else (None if new_boot is None else "boot-a"), process="restart",
                 interrupt=10 if new_boot else clock.uptime, wall=clock.wall() + wall_jump)
    start = now.uptime
    def reply(_):
        assert now.uptime - start == expected
        return final(version)
    resumed = runtime(reopened, reply, now)
    try:
        resumed.run(job["id"])
    finally:
        resumed.close()
    assert reopened.get("job", job["id"])["attempts"] == 2
    check_delivery(reopened, job, version, image, source, tmp_path / "reopened.zip")


@pytest.mark.parametrize("automatic,maximum,retry_after,reason,used", [
    (True, 3, None, "network_retry_exhausted", 3),
    (False, 3, None, "network_retry_disabled", 1),
    (True, 3, 600, "retry_wait_exceeds_limit", 1),
    (True, 3, 600, "retry_wait_exceeds_limit", 3),
    (False, 3, 600, "retry_wait_exceeds_limit", 1),
])
def test_retry_receipt_cooldown_and_current_policy(delivery, tmp_path, automatic, maximum, retry_after, reason, used):
    store, job, version, image, source = delivery
    job_id = job["id"]
    store.update_job(job_id, limits={**job["limits"], "automatic_retry": automatic, "max_attempts_per_request": maximum})
    clock = Clocks()
    sends = []
    def reply(request):
        sends.append(request.content)
        if len(sends) > used:
            return final(version)
        return httpx.Response(429, headers={"Retry-After": str(retry_after)} if retry_after and len(sends) == used else {})
    execution = runtime(store, reply, clock)
    execution.run(job_id)
    original = execution.pending_request(job_id)
    assert store.get("job", job_id)["stop_reason"] == reason and len(sends) == used
    if retry_after:
        assert original["not_before"]["delay_seconds"] == 600
        with pytest.raises(Conflict, match="Retry available at"):
            execution.validate_network_retry(job_id, original["id"])
        execution.close()
        clock = Clocks(boot="reboot", process="restart", interrupt=1)
        execution = runtime(Store(store.root), reply, clock)
        for seconds in (0, 599):
            clock.advance(seconds)
            with pytest.raises(Conflict, match="Retry available at"):
                execution.validate_network_retry(job_id, original["id"])
        clock.advance(1)
        original = execution.pending_request(job_id)
    engine = Engine(store.root)
    try:
        engine.configure(job_id, limits={"automatic_retry": True, "max_attempts_per_request": 5})
    finally:
        engine.close()
    transition = execution.resume_pending
    def interrupted(*args, **kwargs):
        transition(*args, **kwargs)
        raise Interrupted
    execution.resume_pending = interrupted
    try:
        with pytest.raises(Interrupted):
            execution.run(job_id, retry_request=original["id"])
    finally:
        execution.close()
    resumed = runtime(Store(store.root), reply, clock)
    try:
        resumed.run(job_id)
        resumed.run(job_id, retry_request=original["id"])
    finally:
        resumed.close()
    old, successor = store.records("request", job_id)
    receipt = store.json("continuation:" + old["id"], job_id)
    assert old == original and len(sends) == used + 1
    assert receipt["authorization"] == {"kind": "human_network_retry", "request": old["id"]}
    assert successor["replay_policy"]["max_attempts_per_request"] == 5
    assert receipt.get("not_before") == old.get("not_before")
    if retry_after:
        attempt = store.get("attempt", successor["attempts"][0])
        assert attempt["not_before"] == receipt["not_before"]
        assert successor["not_before"]["satisfied_by"] == attempt["id"]
    check_delivery(store, job, version, image, source, tmp_path / "retry.zip")
