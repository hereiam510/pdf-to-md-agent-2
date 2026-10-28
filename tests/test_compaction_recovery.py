"""Explicit one-shot unknown-compaction recovery; every response is offline."""
from copy import deepcopy
import json

from fastapi.testclient import TestClient
import httpx
import pytest

from pdfmd.documents import Documents
from pdfmd.nexus import Nexus
from pdfmd.runtime import Runtime
from pdfmd.server import Engine, create_app
from pdfmd.storage import Conflict
from test_context_admission import protocol_job, state_for, synthetic_text
from test_context_progress import read_batch
from test_continuation import delivery, check_delivery
from test_response_repairs import handoff, native
from test_runtime import tool


PROTOCOLS = ["chat_completions", "responses"]


def seed(runtime, store, job, pins=()):
    """Seed complete historical records, then let real Runtime prepare/send."""
    payload, capacity = runtime.context.normal(job, state_for(job, []))
    frozen = runtime.nexus.freeze(job["id"], "seed-history", payload, "normal", {"capacity": capacity})
    refs, _ = read_batch(store, job, "seed-history", [synthetic_text("recovery-A", 40000), synthetic_text("recovery-B", 40000)])
    accepted = store.get("request", "seed-history")["accepted_ref"]
    store.put("request", "seed-history", job["id"], {**frozen, "status": "accepted", "accepted_ref": accepted})
    state = state_for(job, ["seed-history"], pins)
    runtime.graph.update_state({"configurable": {"thread_id": job["id"]}}, state, as_node="tools")
    assert not runtime.context.normal(job, state)[1]["fits"]
    return refs


def waiting_reply(job, protocol, payload):
    return native(protocol, tool("report", {"state": "waiting", "message": "Saved work retained."})) if payload.get("tools") else native(
        protocol, text=json.dumps(handoff(job)))


def start(engine, job, **kwargs):
    engine.start(job, "offline-fixture", **kwargs)
    engine.futures[job].result(timeout=30)


def fail_unknown(setup, protocol):
    store, original = setup
    job = protocol_job(store, original, protocol)
    seen = []
    def failed(request):
        seen.append(request.content)
        raise httpx.ReadTimeout("Injected unknown completion.")
    transport = httpx.MockTransport(failed)
    runtime = Runtime(store, Nexus(store, lambda _: "offline", transport))
    refs = seed(runtime, store, job)
    runtime.run(job["id"])
    old = runtime.pending_request(job["id"])
    runtime.close()
    assert old["kind"] == "compaction" and old["status"] == "unknown" and len(seen) == 1
    return store, job, old, refs, seen


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_task_deadline_change_then_compaction_recovery_preserves_delivery(delivery, tmp_path, protocol):
    store, original, version, image, source = delivery
    job = protocol_job(store, store.get("job", original["id"]), protocol)
    job = store.update_job(job["id"], route={**job["route"], "timeout_seconds": 180}, active_seconds=17)
    documents = Documents(store)
    original_version = documents.version(job["id"], version)
    original_files = {name: (documents.root / version / name).read_bytes()
                      for name in store.get("version", version, job=job["id"])["files"]}
    seen = []
    def reply(request):
        payload = json.loads(request.content)
        seen.append(payload)
        if len(seen) == 1:
            raise httpx.ReadTimeout("Unknown upstream completion.")
        if len(seen) == 2:
            assert not payload.get("tools")
            assert "explicit_compaction_recovery" in json.dumps(payload)
            assert payload.get("max_completion_tokens", payload.get("max_output_tokens")) == job["route"]["output_tokens"]
            value = native(protocol, text=json.dumps(handoff(job, current_state="Complete saved version: " + version)))
        elif len(seen) == 3:
            value = native(protocol, tool("edit_document", {"base_version": version, "expected_head": version,
                "title": "Recovered complete document"}))
        else:
            assert len(seen) == 4
            value = native(protocol, tool("report", {"state": "complete", "message": "Saved complete result.",
                "version_id": store.get("job", job["id"])["head"]}))
        return httpx.Response(200, json=value)
    transport = httpx.MockTransport(reply)
    runtime = Runtime(store, Nexus(store, lambda _: "offline", transport))
    refs = seed(runtime, store, job, pins=[image["ref"]])
    runtime.run(job["id"])
    old = runtime.pending_request(job["id"])
    policy = {field: runtime.graph.get_state({"configurable": {"thread_id": job["id"]}}).values.get(field)
              for field in ("notes", "pinned", "pin_views", "released")}
    runtime.close()
    assert old["route"]["timeout_seconds"] == 180
    old_attempt = store.get("attempt", old["attempts"][0], job=job["id"])
    original_requests = store.records("request", job["id"])
    original_operations = store.records("operation", job["id"])
    original_blobs = {blob["ref"]: store.bytes(blob["ref"], job["id"])
                      for blob in store.records("blob", job["id"])}
    frozen = store.bytes(old["payload_ref"], job["id"])
    before = store.get("job", job["id"])
    app = create_app(store.root, "local", transport=transport)
    with TestClient(app, headers={"Authorization": "Bearer local"}) as client:
        engine = app.state.engine
        assert client.get(f"/jobs/{job['id']}").json()["compaction_recovery"] == {"request": old["id"]}
        response = client.post(f"/jobs/{job['id']}/settings", json={"route": {"timeout_seconds": 600}})
        assert response.status_code == 200
        updated_route = {**before["route"], "timeout_seconds": 600}
        assert response.json() == {**before, "route": updated_route}
        assert len(seen) == 1 and store.records("request", job["id"]) == original_requests
        settings = store.records("task_settings", job["id"])
        assert len(settings) == 1
        assert settings[0]["before"] == {"route": before["route"], "limits": before["limits"]}
        assert settings[0]["after"] == {"route": updated_route, "limits": before["limits"]}
        # Ordinary Continue remains the original frozen replay gate.
        start(engine, job["id"])
        assert len(seen) == 1 and engine.store.get("job", job["id"])["stop_reason"] == "unknown_outcome"
        response = client.post(f"/jobs/{job['id']}/start", json={"key": "offline",
            "recover_compaction_request": old["id"]})
        assert response.status_code == 200
        engine.futures[job["id"]].result(timeout=30)
        assert client.get(f"/jobs/{job['id']}").json()["compaction_recovery"] is None
        completed = store.get("job", job["id"])
        requests = store.records("request", job["id"])
        response = client.post(f"/jobs/{job['id']}/start", json={"key": "offline",
            "recover_compaction_request": old["id"]})
        assert response.status_code == 409 and "pending request" in response.json()["error"]
        assert store.get("job", job["id"]) == completed
        assert store.records("request", job["id"]) == requests and len(seen) == 4
    current = store.get("job", job["id"])
    assert current["status"] == "completed" and current["attempts"] == 4
    assert current["active_seconds"] >= before["active_seconds"] >= 17
    assert store.get("request", old["id"]) == old and store.bytes(old["payload_ref"], job["id"]) == frozen
    assert store.get("attempt", old_attempt["id"], job=job["id"]) == old_attempt
    assert old_attempt["transport"]["deadline_seconds"] == 180
    new_requests = [request for request in requests if request["id"] not in {r["id"] for r in original_requests}]
    assert len(new_requests) == 3 and sum(r["kind"] == "compaction" for r in new_requests) == 1
    for request in new_requests:
        assert request["route"] == updated_route and request["replay_policy"] == old["replay_policy"]
        assert request["status"] == "accepted" and len(request["attempts"]) == 1
        assert store.get("attempt", request["attempts"][0], job=job["id"])["transport"]["deadline_seconds"] == 600
    for request in original_requests:
        assert store.get("request", request["id"], job=job["id"]) == request
    for operation in original_operations:
        assert store.get("operation", operation["id"], job=job["id"]) == operation
    for ref, content in original_blobs.items():
        assert store.bytes(ref, job["id"]) == content
    reopened = Runtime(store, Nexus(store, lambda _: "offline", transport))
    state = reopened.graph.get_state({"configurable": {"thread_id": job["id"]}}).values
    reopened.close()
    assert {field: state.get(field) for field in policy} == policy
    choice = store.json(f"continuation:{old['id']}", job["id"])
    assert choice["authorization"] == {"kind": "human_compaction_recovery", "request": old["id"]}
    assert choice["payload_ref"] == old["payload_ref"] and choice["attempts"] == old["attempts"]
    assert len([e for e in store.events(job["id"]) if e["type"] == "request_continued"]) == 1
    assert not any(op["id"].startswith(old["id"] + ":") for op in store.records("operation", job["id"]))
    assert [store.json(ref, job["id"])["text"] for ref in refs] == [synthetic_text("recovery-A", 40000), synthetic_text("recovery-B", 40000)]
    assert current["head"] != version and current["limits"] == before["limits"] and current["route"] == updated_route
    assert documents.version(job["id"], version) == original_version
    assert documents.version(job["id"], current["delivery"])["content"]["blocks"] == original_version["content"]["blocks"]
    for name, content in original_files.items():
        assert (documents.root / version / name).read_bytes() == content
    check_delivery(store, job, current["delivery"], image, source, tmp_path / "recovered.zip")


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("gap", ["before_receipt", "after_receipt", "before_checkpoint", "after_checkpoint"])
def test_explicit_choice_recovers_only_after_its_receipt_commits(setup, monkeypatch, protocol, gap):
    store, job, old, refs, seen = fail_unknown(setup, protocol)
    original_request = deepcopy(old)
    def reply(request):
        payload = json.loads(request.content)
        seen.append(request.content)
        return httpx.Response(200, json=waiting_reply(job, protocol, payload))
    transport = httpx.MockTransport(reply)
    runtime = Runtime(store, Nexus(store, lambda _: "offline", transport))
    if gap in {"before_receipt", "after_receipt"}:
        original = store.blob
        def fail(*args, **kwargs):
            if args[1] == "request_continuation":
                if gap == "after_receipt":
                    original(*args, **kwargs)
                raise RuntimeError(gap)
            return original(*args, **kwargs)
        monkeypatch.setattr(store, "blob", fail)
    elif gap == "before_checkpoint":
        original = runtime.resume_pending
        def fail(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError(gap)
        runtime.resume_pending = fail
    else:
        original = runtime.graph.update_state
        def fail(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError(gap)
        runtime.graph.update_state = fail
    with pytest.raises(RuntimeError, match=gap):
        runtime.run(job["id"], recover_compaction_request=old["id"])
    runtime.close()
    monkeypatch.undo()
    resumed = Runtime(store, Nexus(store, lambda _: "offline", transport))
    resumed.run(job["id"])
    if gap == "before_receipt":
        assert len(seen) == 1 and store.get("job", job["id"])["stop_reason"] == "unknown_outcome"
        assert store.maybe("blob", f"continuation:{old['id']}") is None
        resumed.run(job["id"], recover_compaction_request=old["id"])
    resumed.close()
    assert store.get("job", job["id"])["status"] == "waiting"
    assert len(seen) == store.get("job", job["id"])["attempts"] == 3
    assert store.get("request", old["id"]) == original_request
    assert len([e for e in store.events(job["id"]) if e["type"] == "request_continued"]) == 1
    assert all(store.json(ref, job["id"])["text"] for ref in refs)


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_stale_choice_cannot_recover_successor_unknown_or_change_settings(setup, protocol):
    store, job, old, _, seen = fail_unknown(setup, protocol)
    def failed(request):
        seen.append(request.content)
        raise httpx.ReadTimeout("Successor is independently unknown.")
    engine = Engine(store.root, transport=httpx.MockTransport(failed))
    try:
        start(engine, job["id"], recover_compaction_request=old["id"])
        offer = engine.compaction_recovery(job["id"])
        assert offer and offer["request"] != old["id"] and len(seen) == 2
        before = store.update_job(job["id"], cancel_requested=True)
        requests = deepcopy(store.records("request", job["id"]))
        with pytest.raises(Conflict, match="pending request"):
            start(engine, job["id"], recover_compaction_request=old["id"], amendment="Must not be added.",
                  route={"context_tokens": 200000})
        assert store.get("job", job["id"]) == before
        assert store.records("request", job["id"]) == requests
        start(engine, job["id"])
        assert len(seen) == store.get("job", job["id"])["attempts"] == 2
        assert store.get("job", job["id"])["stop_reason"] == "unknown_outcome"
        assert len([b for b in store.records("blob", job["id"]) if b["kind"] == "request_continuation"]) == 1
    finally:
        engine.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_locally_accepted_handoff_wins_before_pointer_commit(setup, monkeypatch, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    seen = []
    def reply(request):
        payload = json.loads(request.content)
        seen.append(payload)
        return httpx.Response(200, json=waiting_reply(job, protocol, payload))
    transport = httpx.MockTransport(reply)
    runtime = Runtime(store, Nexus(store, lambda _: "offline", transport))
    seed(runtime, store, job)
    original = store.put
    def fail(kind, key, owner, value):
        if kind == "request" and value.get("kind") == "compaction" and value["status"] == "accepted":
            raise RuntimeError("accepted bytes before pointer")
        return original(kind, key, owner, value)
    monkeypatch.setattr(store, "put", fail)
    with pytest.raises(RuntimeError, match="accepted bytes"):
        runtime.run(job["id"])
    old = runtime.pending_request(job["id"])
    assert not old["accepted_ref"] and store.maybe("blob", f"accepted:{old['id']}")
    runtime.close()
    monkeypatch.undo()
    engine = Engine(store.root, transport=transport)
    try:
        assert engine.compaction_recovery(job["id"]) is None
        start(engine, job["id"], recover_compaction_request=old["id"])
    finally:
        engine.close()
    assert len(seen) == 2 and sum(not p.get("tools") for p in seen) == 1
    assert store.get("job", job["id"])["status"] == "waiting"
    assert store.maybe("blob", f"continuation:{old['id']}") is None
    assert store.get("request", old["id"])["accepted_ref"] == f"accepted:{old['id']}"


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_normal_unknown_is_not_a_compaction_recovery_target(setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    seen = []
    def failed(request):
        seen.append(request.content)
        raise httpx.ReadTimeout("Normal unknown.")
    engine = Engine(store.root, transport=httpx.MockTransport(failed))
    try:
        start(engine, job["id"])
        old = store.records("request", job["id"])[0]
        assert engine.compaction_recovery(job["id"]) is None
        before = store.get("job", job["id"])
        with pytest.raises(Conflict):
            start(engine, job["id"], recover_compaction_request=old["id"], amendment="Do not commit.")
        assert store.get("job", job["id"]) == before
        start(engine, job["id"])
        assert len(seen) == 1 and store.get("request", old["id"]) == old
    finally:
        engine.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_recovery_replans_normal_input_when_current_capacity_fits(setup, protocol):
    store, job, old, _, seen = fail_unknown(setup, protocol)
    def reply(request):
        payload = json.loads(request.content)
        seen.append(request.content)
        assert payload.get("tools") and "explicit_compaction_recovery" in json.dumps(payload)
        return httpx.Response(200, json=waiting_reply(job, protocol, payload))
    engine = Engine(store.root, transport=httpx.MockTransport(reply))
    try:
        start(engine, job["id"], recover_compaction_request=old["id"], route={"context_tokens": 200000})
        assert len(seen) == 2 and store.get("job", job["id"])["status"] == "waiting"
        latest = store.records("request", job["id"])[-1]
        assert latest["kind"] == "normal" and latest["route"]["context_tokens"] == 200000
        assert store.get("request", old["id"]) == old
    finally:
        engine.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_explicit_recovery_does_not_reset_handoff_correction_budget(setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    job = store.update_job(job["id"], limits={**job["limits"], "max_response_repairs": 1})
    seen = []
    def reply(request):
        payload = json.loads(request.content)
        assert not payload.get("tools")
        seen.append(payload)
        if len(seen) == 2:
            raise httpx.ReadTimeout("Unknown first correction attempt.")
        return httpx.Response(200, json=native(protocol, text="{}"))
    transport = httpx.MockTransport(reply)
    runtime = Runtime(store, Nexus(store, lambda _: "offline", transport))
    seed(runtime, store, job)
    runtime.run(job["id"])
    old = runtime.pending_request(job["id"])
    assert old["status"] == "unknown"
    before = runtime.graph.get_state({"configurable": {"thread_id": job["id"]}}).values
    assert before["repairs"]["compaction"]["count"] == 1
    runtime.run(job["id"], recover_compaction_request=old["id"])
    after = runtime.graph.get_state({"configurable": {"thread_id": job["id"]}}).values
    runtime.close()
    assert len(seen) == 3 and store.get("job", job["id"])["stop_reason"] == "response_repair_exhausted"
    assert after["repairs"]["compaction"]["count"] == 2 and after["history"] == before["history"]
    assert store.get("request", old["id"]) == old
    engine = Engine(store.root, transport=transport)
    try:
        start(engine, job["id"])
        assert len(seen) == 3
    finally:
        engine.close()


@pytest.mark.parametrize("boundary", ["requests", "active_time"])
def test_explicit_recovery_keeps_consumed_total_budgets(setup, boundary):
    store, job, old, _, seen = fail_unknown(setup, "chat_completions")
    current = store.get("job", job["id"])
    if boundary == "requests":
        store.update_job(job["id"], limits={**current["limits"], "max_requests": current["attempts"]})
    else:
        store.update_job(job["id"], active_seconds=current["limits"]["max_active_seconds"])
    before = store.get("job", job["id"])
    engine = Engine(store.root, transport=httpx.MockTransport(lambda _: pytest.fail("No exhausted-budget send")))
    try:
        start(engine, job["id"], recover_compaction_request=old["id"])
        after = store.get("job", job["id"])
        assert after["stop_reason"] == "budget_exhausted" and after["attempts"] == before["attempts"]
        assert after["active_seconds"] >= before["active_seconds"] and after["limits"] == before["limits"]
        assert store.get("request", old["id"]) == old and len(seen) == 1
    finally:
        engine.close()
