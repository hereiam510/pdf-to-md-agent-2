"""Product-state regressions: valid intent, terminal decisions and input delivery differ."""
from copy import deepcopy
import json

import httpx
import pytest

from pdfmd.context import HandoffRejected
from pdfmd.nexus import Nexus, StopRun, parse_reply
from pdfmd.runtime import Runtime
from pdfmd.storage import Store
from test_context_admission import outputs
from test_context_retry import POLICY, compact, prepare_step, pressure
from test_response_repairs import handoff, native
from test_runtime import tool
from test_stencil_pins import accepted, offline_runtime


PROTOCOLS = ["chat_completions", "responses"]


def config(job):
    return {"configurable": {"thread_id": job["id"]}}


def pending(setup, protocol):
    store, original = setup
    job, state, intent, ref = pressure(store, original, protocol)
    runtime = offline_runtime(store)
    after = {**state, **runtime.tools(state)}
    assert after["context_waiting"]
    return store, job, state, after, runtime


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("amend", [False, True])
def test_capacity_block_checkpoints_revision_need_or_supersession_and_reopens(setup, protocol, amend):
    store, job, before, state, runtime = pending(setup, protocol)
    original = store.bytes(state["context_waiting"], job["id"])
    runtime.graph.update_state(config(job), state, as_node="tools")
    runtime.close()
    store.update_job(job["id"], route={**job["route"], "context_tokens": 4096, "output_tokens": 512},
                     amendments=["Discard the old proposal; follow this new instruction."] if amend else [], active_seconds=17)
    for _ in range(2):
        runtime = offline_runtime(Store(store.root))
        runtime.run(job["id"])
        saved = dict(runtime.graph.get_state(config(job)).values)
        runtime.close()
        assert store.get("job", job["id"])["stop_reason"] == "feedback_capacity_blocked"
        assert all(saved[k] == before[k] for k in POLICY)
        if amend:
            assert saved["context_waiting"] is None
            assert store.json(saved["context_feedback"], job["id"])["summary"]["status"] == "superseded"
        else:
            assert saved["context_waiting"] is None
            assert store.json(saved["context_feedback"], job["id"])["summary"]["status"] == "needs_agent_revision"
        assert store.bytes(state["context_waiting"], job["id"]) == original
    calls = []
    def respond(request):
        calls.append(json.loads(request.content))
        assert request.url.path in {"/v1/chat/completions", "/v1/responses"}
        if not calls[-1].get("tools"):
            return httpx.Response(200, json=native(protocol, text=json.dumps(handoff(job,
                current_state="Retain exact original data and the saved candidate for explicit revision.",
                unfinished_work=[], references=[], cautions=[]))))
        return httpx.Response(200, json=native(protocol, tool("report", {"state": "waiting", "message": "Local check finished."}, "report")))
    store.update_job(job["id"], route=job["route"])
    runtime = Runtime(Store(store.root), Nexus(store, lambda _: "fixture", httpx.MockTransport(respond)))
    try:
        runtime.run(job["id"])
        final = dict(runtime.graph.get_state(config(job)).values)
        assert final["context_waiting"] is None
        assert final["notes"] == before["notes"]
        normal = [payload for payload in calls if payload.get("tools")]
        assert len(normal) == 1
        assert f'"status": "{"superseded" if amend else "needs_agent_revision"}"' in json.dumps(normal[0]).replace('\\"', '"')
        assert store.get("job", job["id"])["attempts"] == len(calls)
        assert store.get("job", job["id"])["active_seconds"] >= 17
        assert len([e for e in store.events(job["id"]) if e["type"] == "context_update_settled"]) == 1
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("status", ["needs_agent_revision", "superseded"])
def test_committed_outcome_checkpoints_even_when_feedback_cannot_fit(setup, protocol, status):
    store, job, before, state, runtime = pending(setup, protocol)
    state = compact(runtime, job, state)
    # A fitting continuation may retain fresh results. Do not force another
    # summary merely to empty history before injecting the commit/checkpoint gap.
    while not runtime.context.normal(job, state)[1]["fits"]:
        state = compact(runtime, job, state)
    key = f"{job['id']}:{state['seq']}:{state['revision']}"
    decision = runtime.context_updates.reject(job, state, key, "Complete diagnostics: " + "D" * 20000, status=status)
    original = store.bytes(decision["context_feedback"], job["id"])
    # Inject the documented settlement-before-checkpoint gap, then reduce capacity.
    runtime.graph.update_state(config(job), state, as_node="tools")
    store.update_job(job["id"], route={**job["route"], "context_tokens": 4096, "output_tokens": 512})
    runtime.run(job["id"])
    projected = dict(runtime.graph.get_state(config(job)).values)
    assert projected["context_waiting"] is None and projected["context_feedback"] == decision["context_feedback"]
    assert store.get("job", job["id"])["stop_reason"] == "feedback_capacity_blocked"
    assert all(projected[k] == before[k] for k in POLICY)
    runtime.close()
    runtime = offline_runtime(Store(store.root))
    try:
        runtime.run(job["id"])
        assert dict(runtime.graph.get_state(config(job)).values)["context_waiting"] is None
        store.update_job(job["id"], route=job["route"])
        step = prepare_step(runtime, projected)
        request = store.get("request", step["pending"])
        body = store.bytes(request["payload_ref"], job["id"])
        assert b'DDDDDDDD' not in body and status.encode() in body
        assert decision["context_feedback"].encode() in body
        assert store.bytes(decision["context_feedback"], job["id"]) == original
        assert len([e for e in store.events(job["id"]) if e["type"] == "context_update_settled"]) == 1
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("kind", ["notes", "pin"])
def test_large_update_cannot_admit_itself_by_deferring_visible_evidence(setup, protocol, kind):
    store, original = setup
    job, state, _, _ = pressure(store, original, protocol)
    read = json.loads(store.json(store.get("request", "pending")["accepted_ref"], job["id"])["calls"][0]["arguments"])
    ref = store.blob(job["id"], "evidence", {"text": "N" * 6000})["ref"]
    intent = {"notes": "N" * 6000} if kind == "notes" else {"pin": [{"ref": ref, "view": "full"}]}
    accepted(store, job, "pending", tool("read_evidence", read, "read"), tool("context_update", intent, "update"))
    runtime = offline_runtime(store)
    try:
        after = {**state, **runtime.tools(state)}
        assert after["context_waiting"] == "context-proposal:pending"
        assert all(after[k] == state[k] for k in POLICY)
        payload, _ = runtime.context.normal(job, after)
        control = outputs(payload)[-1]
        assert control["data"]["admission"]["applied"] is False
        assert control["data"]["full_result_ref"] == "result:pending:1"
        saved = store.bytes(after["context_waiting"], job["id"])
        original_receipt = store.bytes("result:pending:1", job["id"])
        for _ in range(6):
            step = prepare_step(runtime, after)
            after.update(step)
            request = store.get("request", after["pending"])
            if request["kind"] == "normal":
                break
            after = runtime.context.apply_handoff(job, after, json.dumps(handoff(job,
                current_state="Source originals remain available.", unfinished_work=[], references=[], cautions=[])), request["meta"], request["id"])
            after["pending"] = None
        assert after["context_waiting"] is None
        assert after["notes"] == intent["notes"] if kind == "notes" else after["pinned"] == [ref]
        assert store.bytes("context-proposal:pending", job["id"]) == saved
        assert store.bytes("result:pending:1", job["id"]) == original_receipt
        assert store.json(ref, job["id"]) == {"text": "N" * 6000}
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_later_release_can_admit_chain_without_compaction(setup, protocol):
    store, original = setup
    job, state, intent, ref = pressure(store, original, protocol)
    calls = store.json(store.get("request", "pending")["accepted_ref"], job["id"])["calls"]
    accepted(store, job, "pending", tool("read_evidence", json.loads(calls[0]["arguments"]), "read"),
             tool("context_update", intent, "remember"),
             tool("context_update", {"release": ["result:history:0", "result:pending:0"]}, "release"))
    runtime = offline_runtime(store)
    try:
        after = {**state, **runtime.tools(state)}
        assert after["context_waiting"]
        result = {**after, **prepare_step(runtime, after)}
        assert not result["context_waiting"] and result["notes"] == intent["notes"]
        assert store.get("request", result["pending"])["kind"] == "normal"
        assert not any(e["type"] == "context_compacted" for e in store.events(job["id"]))
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_final_handoff_preserves_space_for_pending_policy_and_outcome(setup, protocol):
    store, original = setup
    job, state, intent, ref = pressure(store, original, protocol)
    calls = store.json(store.get("request", "pending")["accepted_ref"], job["id"])["calls"]
    accepted(store, job, "pending", tool("read_evidence", json.loads(calls[0]["arguments"]), "read"),
             tool("context_update", intent, "first"), tool("context_update", {"notes": "N" * 6000}, "second"))
    runtime = offline_runtime(store)
    try:
        after = {**state, **runtime.tools(state)}
        _, meta = runtime.context.compact_request(job, after)
        while len(meta["covered"]) < len(after["history"]):
            after = runtime.context.apply_handoff(job, after, json.dumps(handoff(job,
                current_state="Keep source work.", unfinished_work=[], references=[], cautions=[])), meta, f"prefix:{after['revision']}")
            _, meta = runtime.context.compact_request(job, after)
        original = deepcopy(after)
        with pytest.raises(HandoffRejected, match="pending policy"):
            runtime.context.apply_handoff(job, after, json.dumps(handoff(job,
                current_state="C" * 6000, unfinished_work=[], references=[], cautions=[])), meta, "long")
        assert after == original and store.maybe("blob", "handoff:long")
        after = runtime.context.apply_handoff(job, after, json.dumps(handoff(job,
            current_state="Keep source work.", unfinished_work=[], references=[], cautions=[])), meta, "short")
        after.update(prepare_step(runtime, after))
        assert not after["context_waiting"] and after["notes"] == "N" * 6000
        assert runtime.context.normal(job, after)[1]["fits"]
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_explicit_release_can_reduce_compaction_without_early_policy_application(setup, protocol):
    store, original = setup
    job, state, _, _ = pressure(store, original, protocol)
    job = store.update_job(job["id"], route={**job["route"], "context_tokens": 50000})
    runtime = offline_runtime(store)
    try:
        pin = store.blob(job["id"], "evidence", {"text": "P" * 10200})["ref"]
        accepted(store, job, "pin-init", tool("context_update", {"pin": [{"ref": pin, "view": "full"}]}, "pin"))
        state["pending"] = "pin-init"
        state.update(runtime.tools(state))
        state.update(runtime.coordinate(state))
        assert state["pinned"] == [pin] and not state["context_waiting"]
        payload, capacity = runtime.context.normal(job, state)
        assert capacity["fits"]
        key = "accepted-before-capacity-change"
        request = runtime.nexus.freeze(job["id"], key, payload, "normal", {"capacity": capacity})
        ref = store.blob(job["id"], "evidence", {"text": "B" * 5000})["ref"]
        reply = parse_reply(protocol, json.dumps(native(protocol, tool("read_evidence", {"ref": ref}, "read"),
                            tool("context_update", {"release": [pin]}, "release"))).encode())
        accepted_ref = store.blob(job["id"], "accepted_response", reply)["ref"]
        store.put("request", key, job["id"], {**request, "status": "accepted", "accepted_ref": accepted_ref})
        frozen = store.bytes(request["payload_ref"], job["id"])
        job = store.update_job(job["id"], route={**job["route"], "context_tokens": 28000})
        state["pending"] = key
        state.update(runtime.tools(state))
        assert state["context_waiting"] and state["pinned"] == [pin]
        state.update(prepare_step(runtime, state))
        compact_request = store.get("request", state["pending"])
        assert compact_request["kind"] == "compaction"
        body = store.json(compact_request["payload_ref"], job["id"])
        assert "release_projection" in json.dumps(body) and "not the stored active policy" in json.dumps(body)
        assert state["pinned"] == [pin]
        for _ in range(6):
            state = runtime.context.apply_handoff(job, state, json.dumps(handoff(job,
                current_state="Saved work retained.", unfinished_work=[], references=[], cautions=[])), compact_request["meta"], compact_request["id"])
            state["pending"] = None
            state.update(prepare_step(runtime, state))
            compact_request = store.get("request", state["pending"])
            if compact_request["kind"] == "normal":
                break
        assert state["context_waiting"] is None and pin not in state["pinned"] and pin in state["released"]
        assert store.json(pin, job["id"]) == {"text": "P" * 10200}
        assert store.bytes(request["payload_ref"], job["id"]) == frozen
        assert store.get("request", key)["route"]["context_tokens"] == 50000
        assert store.get("job", job["id"])["attempts"] == 0
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("amend", [False, True])
def test_outcome_reservation_covers_terminal_feedback_at_exact_allowance(setup, protocol, amend):
    store, original = setup
    job, state, intent, ref = pressure(store, original, protocol)
    calls = store.json(store.get("request", "pending")["accepted_ref"], job["id"])["calls"]
    accepted(store, job, "pending", tool("read_evidence", json.loads(calls[0]["arguments"]), "read"),
             tool("context_update", intent, "first"), tool("context_update", {"notes": "N" * 6000}, "large"))
    runtime = offline_runtime(store)
    try:
        after = {**state, **runtime.tools(state)}
        while after["history"]:
            _, meta = runtime.context.compact_request(job, after)
            after = runtime.context.apply_handoff(job, after, json.dumps(handoff(job,
                current_state="Retain source.", unfinished_work=[], references=[], cautions=[])), meta, f"compact:{after['revision']}")
        if amend:
            job = store.update_job(job["id"], amendments=["Replace the old proposal."])
        reserved = runtime.context.normal(job, after)[1]
        assert reserved["outcome_reserve"] > 0
        job = store.update_job(job["id"], route={**job["route"],
            "context_tokens": reserved["input_estimate"] + reserved["output_reserve"]})
        final = {**after, **prepare_step(runtime, after)}
        status = store.json(final["context_feedback"], job["id"])["summary"]["status"]
        assert status == ("superseded" if amend else "needs_agent_revision")
        assert runtime.context.normal(job, final)[1]["fits"]
        assert store.get("request", final["pending"])["kind"] == "normal"
        assert all(final[k] == state[k] for k in POLICY)
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_handoff_only_reduction_preserves_progress_and_original_archive(setup, protocol):
    store, original = setup
    job, state, _, _ = pressure(store, original, protocol)
    state["pending"] = None
    runtime = offline_runtime(store)
    try:
        _, meta = runtime.context.compact_request(job, state)
        state = runtime.context.apply_handoff(job, state, json.dumps(handoff(job,
            current_state="C" * 2000, unfinished_work=[], references=[], cautions=[])), meta, "initial-summary")
        assert state["history"] == []
        original_bytes = store.bytes(state["handoff"], job["id"])
        required = runtime.context.normal(job, {**state, "handoff": None})[1]
        job = store.update_job(job["id"], route={**job["route"],
            "context_tokens": required["input_estimate"] + required["output_reserve"] + 1000})
        assert not runtime.context.normal(job, state)[1]["fits"]
        state.update(prepare_step(runtime, state))
        request = store.get("request", state["pending"])
        assert request["kind"] == "compaction" and request["meta"]["covered"] == []
        with pytest.raises(HandoffRejected, match="did not reduce"):
            runtime.context.apply_handoff(job, state, json.dumps(handoff(job,
                current_state="C" * 4000, unfinished_work=[], references=[], cautions=[])), request["meta"], "no-progress")
        result = runtime.context.apply_handoff(job, state, json.dumps(handoff(job,
            current_state="Keep complete source work.", unfinished_work=[], references=[], cautions=[])), request["meta"], request["id"])
        assert runtime.context.normal(job, result)[1]["fits"]
        assert store.bytes("handoff:initial-summary", job["id"]) == original_bytes
        assert store.maybe("blob", "handoff:no-progress")
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_existing_full_settlement_replays_without_rewriting_original(setup, protocol):
    store, job, before, state, runtime = pending(setup, protocol)
    state = compact(runtime, job, state)
    key = f"{job['id']}:{state['seq']}:{state['revision']}"
    ref = runtime.context_updates.ref(key)
    proposal = runtime.context.waiting(job["id"], state)
    runtime.context_updates.finish(job, state, key,
        {"status": "applied", "applied": True, "proposal_ref": state["context_waiting"],
         "receipt_ref": ref, "reason": "admitted", "message": "D" * 20000}, proposal["policy"])
    original = store.bytes(ref, job["id"])
    runtime.close()
    store.update_job(job["id"], amendments=["New instruction after the historical decision."])
    runtime = offline_runtime(Store(store.root))
    try:
        final = {**state, **prepare_step(runtime, state)}
        assert not final["context_waiting"] and final["notes"] == proposal["policy"]["notes"]
        payload = store.bytes(store.get("request", final["pending"])["payload_ref"], job["id"])
        assert b"applied" in payload and ref.encode() in payload and b"DDDDDDDD" not in payload
        assert b"New instruction after" in payload
        assert store.bytes(ref, job["id"]) == original
        assert store.get("job", job["id"])["attempts"] == 0
    finally:
        runtime.close()
