"""Explicit future-request streaming settings without any provider calls."""
from copy import deepcopy

import pytest
from filelock import FileLock
from pydantic import ValidationError
from fastapi.testclient import TestClient

from pdfmd.nexus import Nexus, instruction_basis
from pdfmd.schema import Route, WaitPolicy
from pdfmd.server import Engine, create_app
from pdfmd.storage import Conflict, Store
from test_context_admission import protocol_job


PROTOCOLS = ["chat_completions", "responses"]


def test_wait_defaults_are_explicit_and_legacy_route_is_not_silently_migrated(route):
    assert WaitPolicy().model_dump() == {"first_progress_seconds": 600, "idle_progress_seconds": 300, "total_seconds": None}
    assert Route.model_validate(route).wait_policy is None
    assert Route.model_validate({**route, "wait_policy": {}}).wait_policy == WaitPolicy()
    selected = Route.model_validate({**route, "wait_policy": {
        "first_progress_seconds": 599.5, "idle_progress_seconds": 299.25, "total_seconds": 3500}})
    assert selected.wait_policy.model_dump() == {
        "first_progress_seconds": 599.5, "idle_progress_seconds": 299.25, "total_seconds": 3500}


@pytest.mark.parametrize("field", ["first_progress_seconds", "idle_progress_seconds", "total_seconds"])
@pytest.mark.parametrize("value", [0, 3600.01, float("nan"), float("inf"), float("-inf")])
def test_invalid_wait_intervals_are_rejected(field, value):
    with pytest.raises(ValidationError):
        WaitPolicy.model_validate({field: value})


def test_only_total_wait_can_be_unset_and_native_stream_control_is_reserved(route):
    for field in ["first_progress_seconds", "idle_progress_seconds"]:
        with pytest.raises(ValidationError):
            WaitPolicy.model_validate({field: None})
    assert WaitPolicy(total_seconds=None).total_seconds is None
    for field in ["stream", "stream_options"]:
        with pytest.raises(ValidationError):
            Route.model_validate({**route, "parameters": {field: {"include_usage": True}}})


def test_empty_update_preserves_pre_policy_route_without_creating_a_receipt(setup):
    store, job = setup
    historical = {key: value for key, value in job["route"].items() if key != "wait_policy"}
    before = store.update_job(job["id"], route=historical)
    engine = Engine(store.root)
    try:
        assert engine.configure(job["id"], route={}) == before
        assert not store.records("task_settings", job["id"])
        changed = engine.configure(job["id"], route={"timeout_seconds": 600})
        assert changed["route"] == {**historical, "timeout_seconds": 600}
    finally:
        engine.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_wait_settings_preserve_frozen_legacy_and_streaming_requests_across_reopen(setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    job = store.update_job(job["id"], active_seconds=17, attempts=3,
                           amendments=["Preserve the complete source."])
    # This is a prepared frozen request; no transport call is needed for this boundary.
    nexus = Nexus(store, lambda _: "must-not-be-requested")
    legacy = nexus.freeze(job["id"], "legacy-request", {"stream": False, "content": "retained"}, "compaction", {})
    old_payload = store.bytes(legacy["payload_ref"], job["id"])
    selected = WaitPolicy().model_dump()
    engine = Engine(store.root)
    try:
        before = store.get("job", job["id"])
        after = engine.configure(job["id"], route={"wait_policy": selected})
        assert after == {**before, "route": {**before["route"], "wait_policy": selected}}
        assert instruction_basis(after) == instruction_basis(before)
        assert store.get("request", legacy["id"]) == legacy
        assert store.bytes(legacy["payload_ref"], job["id"]) == old_payload
        assert not store.records("attempt", job["id"])
        changes = store.records("task_settings", job["id"])
        assert len(changes) == 1
        assert changes[0]["before"]["route"] == before["route"]
        assert changes[0]["after"]["route"] == after["route"]
        future = nexus.freeze(job["id"], "new-stream-request", {"stream": True}, "normal", {})
        assert future["route"]["wait_policy"] == selected
        changed = {**selected, "first_progress_seconds": 800, "idle_progress_seconds": 400, "total_seconds": 1200}
        engine.configure(job["id"], route={"wait_policy": changed})
        assert store.get("request", future["id"]) == future
        current = engine.configure(job["id"], route={"wait_policy": None})
        assert current["route"]["wait_policy"] is None
        assert current["attempts"] == before["attempts"] and current["active_seconds"] == 17
        assert current["limits"] == before["limits"]
    finally:
        engine.close()
    reopened = Store(store.root)
    assert reopened.get("request", legacy["id"]) == legacy
    assert reopened.get("request", future["id"]) == future
    assert reopened.get("job", job["id"])["route"]["wait_policy"] is None


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_invalid_or_locked_wait_change_is_atomic_and_does_not_send(setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    Nexus(store, lambda _: "unused").freeze(job["id"], "prepared", {"stream": False}, "normal", {})
    engine = Engine(store.root)
    try:
        before = deepcopy(store.get("job", job["id"]))
        for patch in [{"wait_policy": {"total_seconds": 0}},
                      {"wait_policy": {}, "model": "not-authorized"}]:
            with pytest.raises((ValidationError, Conflict)):
                engine.configure(job["id"], route={"context_tokens": 131072, **patch})
            assert store.get("job", job["id"]) == before
            assert not store.records("task_settings", job["id"])
        with FileLock(str(store.root / f"task-{job['id']}.lock")):
            with pytest.raises(Conflict, match="Stop"):
                engine.configure(job["id"], route={"wait_policy": {}})
        assert store.get("job", job["id"]) == before
        assert not store.records("task_settings", job["id"])
        assert not store.records("attempt", job["id"])
    finally:
        engine.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_job_api_exposes_only_current_receive_facts_then_final_attempt(setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    request = Nexus(store, lambda _: "unused").freeze(job["id"], "observed", {"stream": True}, "normal", {})
    request.update(attempts=["receive-attempt"], status="in_flight")
    store.put("request", request["id"], job["id"], request)
    attempt = {"id": "receive-attempt", "request": request["id"], "status": "in_flight",
               "transport": {"mode": "streaming_progress", "progress_count": 0}, "http_status": None}
    store.put("attempt", attempt["id"], job["id"], attempt)
    store.put("stream_receive", attempt["id"], job["id"], {
        "attempt": attempt["id"], "request": request["id"], "chunks": ["private-raw-chunk"],
        "transport": {"mode": "streaming_progress", "http_status": 200, "received_body_bytes": 123,
                      "progress_count": 2, "event_count": 5, "first_progress_elapsed_seconds": 12,
                      "raw_content": "must-not-leak", "headers": {"Authorization": "must-not-leak"}}})
    app = create_app(store.root, "local-only")
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer local-only"}
        response = client.get(f"/jobs/{job['id']}", headers=headers)
        assert response.status_code == 200
        receive = response.json()["requests"][0]["receive"]
        assert receive == {"mode": "streaming_progress", "http_status": 200, "received_body_bytes": 123,
                           "progress_count": 2, "event_count": 5, "first_progress_elapsed_seconds": 12}
        assert "must-not-leak" not in response.text and "private-raw-chunk" not in response.text
        attempt.update(status="unknown", http_status=200,
                       transport={"mode": "streaming_progress", "received_body_bytes": 200,
                                  "progress_count": 3, "settled": True, "stop_cause": "progress_idle_timeout"})
        store.put("attempt", attempt["id"], job["id"], attempt)
        final = client.get(f"/jobs/{job['id']}", headers=headers).json()["requests"][0]["receive"]
        assert final["received_body_bytes"] == 200 and final["settled"]
        assert final["stop_cause"] == "progress_idle_timeout" and final["http_status"] == 200
        assert not store.records("operation", job["id"])
