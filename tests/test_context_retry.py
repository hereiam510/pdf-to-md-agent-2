"""Deferred context updates use exact saved proposals, not model recollection."""
from copy import deepcopy
import json

import httpx
import pytest

from pdfmd.context import Context
from pdfmd.nexus import Nexus
from pdfmd.runtime import Runtime
from pdfmd.storage import Store
from test_context_admission import protocol_job, state_for
from test_context_progress import read_batch
from test_response_repairs import handoff, native
from test_runtime import tool
from test_stencil_pins import accepted, offline_runtime


POLICY = ("pinned", "pin_views", "released", "notes")


def pressure(store, original, protocol, kind="notes"):
    job = protocol_job(store, original, protocol)
    job = store.update_job(job["id"], route={**job["route"], "context_tokens": 28000})
    refs, envs = read_batch(store, job, "history", ["A" * 5000])
    second = store.blob(job["id"], "evidence", {"text": "B" * 5000})["ref"]
    state = {**state_for(job, ["history"]), "notes": "Active notes.", "pin_views": {}}
    intent = {"notes": "Page two inspected; preserve 25 mg."}
    if kind == "index":
        intent = {"pin": [{"ref": refs[0], "view": "index"}]}
    if kind == "release":
        # Release helps without making the complete new history fit.
        _, smaller = read_batch(store, job, "small", ["s" * 1000])
        state["history"].append("small")
        intent = {"release": [smaller[0]["result_ref"]]}
    accepted(store, job, "pending", tool("read_evidence", {"ref": second}, "read"),
             tool("context_update", intent, "update"))
    state["pending"] = "pending"
    return job, state, intent, refs[0]


def compact(runtime, job, state):
    prepared = {**state, **runtime.prepare(state)}
    request = runtime.store.get("request", prepared["pending"])
    assert request["kind"] == "compaction"
    assert not request["attempts"]
    updated = runtime.context.apply_handoff(job, prepared, json.dumps(handoff(job,
        current_state="Saved source and draft remain available.", unfinished_work=[], references=[], cautions=[])),
        request["meta"], request["id"])
    return {**updated, "pending": None}


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("kind", ["notes", "index", "release"])
def test_history_pressure_queues_then_preflights_after_compaction(setup, protocol, kind):
    store, original = setup
    job, state, intent, ref = pressure(store, original, protocol, kind)
    runtime = offline_runtime(store)
    try:
        assert runtime.context.normal(job, state)[1]["fits"]
        after = {**state, **runtime.tools(state)}
        assert after.get("context_waiting") == "result:pending:1"
        receipt = store.bytes(after["context_waiting"], job["id"])
        assert not json.loads(receipt)["admission"]["applied"]
        assert all(after[k] == state[k] for k in POLICY)
        after = compact(runtime, job, after)
        resolved = {**after, **runtime.prepare(after)}
        assert not resolved["context_waiting"]
        outcome = store.json(resolved["context_feedback"], job["id"])
        assert outcome["feedback"]["applied"]
        expected = runtime.context.policy(job["id"], state, intent)
        assert all(resolved[k] == expected[k] for k in POLICY)
        assert runtime.context.normal(job, resolved)[1]["fits"]
        assert outcome["feedback"]["capacity"] == {k: v for k, v in runtime.context.normal(job, resolved)[1].items() if k != "projection"}
        assert store.bytes("result:pending:1", job["id"]) == receipt
        assert store.json(ref, job["id"])["text"] == "A" * 5000
        assert store.get("job", job["id"])["attempts"] == 0
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_deferred_result_pointer_gap_keeps_exact_unapplied_plan(setup, monkeypatch, protocol):
    store, original = setup
    job, state, intent, ref = pressure(store, original, protocol)
    runtime = offline_runtime(store)
    put = store.put
    with monkeypatch.context() as patch:
        def crash(kind, key, owner, value):
            if kind == "operation" and key == "pending:1" and value["status"] == "done":
                raise RuntimeError("proposal saved before operation pointer")
            put(kind, key, owner, value)
        patch.setattr(store, "put", crash)
        with pytest.raises(RuntimeError, match="proposal saved"):
            runtime.tools(state)
    receipt = store.bytes("result:pending:1", job["id"])
    runtime.close()
    store.update_job(job["id"], route={**job["route"], "context_tokens": 500000})
    runtime = offline_runtime(Store(store.root))
    try:
        replay = {**state, **runtime.tools(state)}
        assert replay["context_waiting"] == "result:pending:1"
        assert all(replay[k] == state[k] for k in POLICY)
        assert store.bytes("result:pending:1", job["id"]) == receipt
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_settlement_blob_before_event_is_recovered_after_new_instructions(setup, monkeypatch, protocol):
    store, original = setup
    job, state, intent, ref = pressure(store, original, protocol)
    runtime = offline_runtime(store)
    after = compact(runtime, job, {**state, **runtime.tools(state)})
    blob = store.blob
    with monkeypatch.context() as patch:
        def crash(owner, kind, *args, **kwargs):
            result = blob(owner, kind, *args, **kwargs)
            if kind == "context_settlement":
                raise RuntimeError("decision saved before event")
            return result
        patch.setattr(store, "blob", crash)
        with pytest.raises(RuntimeError, match="decision saved"):
            runtime.prepare(after)
    runtime.close()
    store.update_job(job["id"], amendments=["New requirement."])
    runtime = offline_runtime(Store(store.root))
    try:
        resolved = {**after, **runtime.prepare(after)}
        assert resolved["notes"] == intent["notes"]
        record = store.json(resolved["context_feedback"], job["id"])
        assert record["feedback"]["status"] == "applied"  # Historical acceptance wins.
        frozen = store.get("request", resolved["pending"])
        assert "New requirement." in json.dumps(store.json(frozen["payload_ref"], job["id"]))
        runtime.prepare(after)
        assert len([e for e in store.events(job["id"]) if e["type"] == "context_update_settled"]) == 1
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_unknown_frozen_compaction_is_not_rebuilt_or_settled(setup, protocol):
    store, original = setup
    job, state, intent, ref = pressure(store, original, protocol)
    runtime = offline_runtime(store)
    try:
        after = {**state, **runtime.tools(state)}
        prepared = runtime.prepare(after)
        request = store.get("request", prepared["pending"])
        request["status"] = "unknown"
        store.put("request", request["id"], job["id"], request)
        raw = store.bytes(request["payload_ref"], job["id"])
        store.update_job(job["id"], amendments=["New instruction."], route={**job["route"], "context_tokens": 500000})
        assert runtime.resume_pending(after, continue_failed=True) is None
        assert runtime.prepare(after) == prepared
        assert store.get("request", request["id"]) == request
        assert store.bytes(request["payload_ref"], job["id"]) == raw
        assert not any(b["kind"] == "context_settlement" for b in store.records("blob", job["id"]))
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_failed_compaction_keeps_plan_policy_and_consumption_across_continue(setup, protocol):
    store, original = setup
    job, state, intent, ref = pressure(store, original, protocol)
    runtime = offline_runtime(store)
    after = {**state, **runtime.tools(state)}
    config = {"configurable": {"thread_id": job["id"]}}
    runtime.graph.update_state(config, after, as_node="tools")
    runtime.close()
    store.update_job(job["id"], active_seconds=17, limits={**job["limits"], "max_response_repairs": 0})
    calls = []
    def invalid(request):
        calls.append(request.content)
        return httpx.Response(200, json=native(protocol, text="Invalid handoff; exact original retained."))
    for _ in range(2):
        runtime = Runtime(Store(store.root), Nexus(store, lambda _: "fixture-only", httpx.MockTransport(invalid)))
        runtime.run(job["id"])
        saved = dict(runtime.graph.get_state(config).values)
        runtime.close()
        assert saved["context_waiting"] == after["context_waiting"]
        assert all(saved[k] == after[k] for k in POLICY)
        current = store.get("job", job["id"])
        assert current["stop_reason"] == "response_repair_exhausted"
        assert current["attempts"] == 1 and current["active_seconds"] >= 17
    assert len(calls) == 1


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("amend", [False, True])
def test_ordered_chain_invalid_followup_and_amendment(setup, protocol, amend):
    store, original = setup
    job, state, intent, ref = pressure(store, original, protocol)
    huge = store.blob(job["id"], "image_stream", b"X" * 65536)["ref"]
    accepted(store, job, "pending", tool("read_evidence", {"ref": ref}, "read"),
        tool("context_update", intent, "first"),
        tool("context_update", {"pin": [{"ref": ref, "view": "index"}], "notes": "Latest notes."}, "second"),
        tool("context_update", {"pin": [{"ref": huge, "view": "raw"}], "notes": "Must not leak."}, "huge"))
    runtime = offline_runtime(store)
    try:
        after = {**state, **runtime.tools(state)}
        assert after["context_waiting"] == "result:pending:2"
        plan = runtime.context.waiting(job["id"], after)
        assert plan["previous"] == "result:pending:1"
        assert plan["policy"]["notes"] == "Latest notes." and plan["policy"]["pinned"] == [ref]
        assert not store.get("operation", "pending:3")["ok"]
        assert all(after[k] == state[k] for k in POLICY)
        # A durable deferred receipt is not retrospectively re-admitted.
        store.update_job(job["id"], route={**job["route"], "context_tokens": 500000})
        assert runtime.tools(state)["context_waiting"] == after["context_waiting"]
        store.update_job(job["id"], route=job["route"], amendments=["Use a different approach."] if amend else [])
        if not amend:
            after = compact(runtime, job, after)
        resolved = {**after, **runtime.prepare(after)}
        assert not resolved["context_waiting"]
        expected = state if amend else plan["policy"]
        assert all(resolved[k] == expected[k] for k in POLICY)
        assert store.json(resolved["context_feedback"], job["id"])["feedback"]["status"] == ("superseded" if amend else "applied")
        assert store.bytes(huge, job["id"]) == b"X" * 65536
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_waiting_update_survives_multiple_progressive_compactions(setup, protocol):
    store, original = setup
    job, state, intent, ref = pressure(store, original, protocol)
    for i in range(5):
        read_batch(store, job, f"extra{i}", [str(i) * 5000])
        state["history"].append(f"extra{i}")
    runtime = offline_runtime(store)
    try:
        after = {**state, **runtime.tools(state)}
        pending = after["context_waiting"]
        passes = 0
        while after["context_waiting"]:
            prepared = {**after, **runtime.prepare(after)}
            if not prepared["context_waiting"]:
                after = prepared
                break
            assert prepared["notes"] == state["notes"] and prepared["context_waiting"] == pending
            request = store.get("request", prepared["pending"])
            assert request["kind"] == "compaction"
            after = runtime.context.apply_handoff(job, prepared, json.dumps(handoff(job,
                current_state="Continue exact conversion.", unfinished_work=[], references=[], cautions=[])),
                request["meta"], request["id"])
            after["pending"] = None
            passes += 1
            assert passes <= 7  # Fixture-specific termination check, not a product quota.
        assert passes >= 2 and after["notes"] == intent["notes"]
        assert runtime.context.normal(job, after)[1]["fits"]
        assert store.json(pending, job["id"])["admission"]["applied"] is False
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_retry_rejects_when_policy_no_longer_fits_and_preserves_receipt(setup, protocol):
    store, original = setup
    job, state, intent, ref = pressure(store, original, protocol)
    accepted(store, job, "pending", tool("read_evidence", {"ref": ref}, "read"),
             tool("context_update", intent, "first"),
             tool("context_update", {"notes": "N" * 6000}, "update"))
    runtime = offline_runtime(store)
    try:
        after = {**state, **runtime.tools(state)}
        assert after["context_waiting"]
        after = compact(runtime, job, after)
        while after["history"]:
            _, meta = runtime.context.compact_request(job, after)
            after = runtime.context.apply_handoff(job, after, json.dumps(handoff(job,
                current_state="Saved work remains.", unfinished_work=[], references=[], cautions=[])),
                meta, f"remaining:{after['revision']}")
        old_size = runtime.context.normal(job, after)[1]["input_estimate"]
        job = store.update_job(job["id"], route={**job["route"], "context_tokens": old_size + 4000})
        resolved = {**after, **runtime.prepare(after)}
        outcome = store.json(resolved["context_feedback"], job["id"])
        assert outcome["feedback"]["status"] == "rejected"
        assert all(resolved[k] == state[k] for k in POLICY)
        assert runtime.context.normal(job, resolved)[1]["fits"]
        store.update_job(job["id"], route={**job["route"], "context_tokens": 500000})
        assert runtime.prepare(after) == {k: resolved[k] for k in runtime.prepare(after)}
        assert store.json(resolved["context_feedback"], job["id"]) == outcome
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("amend", [False, True])
def test_settlement_and_freeze_before_checkpoint_recover_without_repricing(setup, monkeypatch, protocol, amend):
    store, original = setup
    job, state, intent, ref = pressure(store, original, protocol)
    runtime = offline_runtime(store)
    after = compact(runtime, job, {**state, **runtime.tools(state)})
    before_job = store.get("job", job["id"])
    freeze = runtime.nexus.freeze
    with monkeypatch.context() as patch:
        def crash(*args, **kwargs):
            freeze(*args, **kwargs)
            raise RuntimeError("after frozen input before checkpoint")
        patch.setattr(runtime.nexus, "freeze", crash)
        with pytest.raises(RuntimeError, match="frozen input"):
            runtime.prepare(after)
    key = f"{job['id']}:{after['seq']}:{after['revision']}"
    frozen = deepcopy(store.get("request", key))
    frozen_bytes = store.bytes(frozen["payload_ref"], job["id"])
    runtime.close()
    runtime = offline_runtime(Store(store.root))
    try:
        if amend:
            store.update_job(job["id"], amendments=["Additional instruction."],
                             route={**job["route"], "context_tokens": 4096, "output_tokens": 512})
            changes = runtime.resume_pending(after, continue_failed=False)
            assert changes["revision"] == after["revision"] + 1
        else:
            changes = runtime.prepare(after)
            assert changes["pending"] == key
        assert changes["notes"] == intent["notes"] and changes["context_waiting"] is None
        assert store.bytes(frozen["payload_ref"], job["id"]) == frozen_bytes
        assert store.get("request", key) == frozen
        assert store.get("job", job["id"])["attempts"] == before_job["attempts"]
        assert store.get("job", job["id"])["active_seconds"] == before_job["active_seconds"]
        assert len([e for e in store.events(job["id"]) if e["type"] == "context_update_settled"]) == 1
    finally:
        runtime.close()
