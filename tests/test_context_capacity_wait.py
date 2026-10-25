"""Capacity repair must preserve valid intent, not silently turn waiting into rejection."""
import base64
from copy import deepcopy
import json

import httpx
import pytest

from pdfmd.context import Context, SYSTEM, estimate
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus, make_payload
from pdfmd.runtime import Runtime
from pdfmd.schema import Route
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher, definitions
from test_context_admission import outputs, protocol_job, state_for
from test_context_progress import read_batch
from test_context_retry import POLICY
from test_response_repairs import handoff, native
from test_runtime import tool
from test_stencil_pins import accepted, offline_runtime


PROTOCOLS = ["chat_completions", "responses"]


def pending_capacity_case(store, original, protocol, scenario, selection="notes"):
    """Seed exact accepted calls, not provider executions; retain full frozen metadata."""
    job = protocol_job(store, original, protocol)
    job = store.update_job(job["id"], route={**job["route"], "context_tokens": 50000})
    runtime = offline_runtime(store)
    state = {**state_for(job, []), "notes": "Active notes.", "pin_views": {}}

    def batch(key, *calls, admission_capacity=None):
        nonlocal job, state
        payload, capacity = runtime.context.normal(job, state)
        assert capacity["fits"]
        frozen = runtime.nexus.freeze(job["id"], key, payload, "normal", {"capacity": capacity})
        accepted(store, job, key, *calls)
        reply = store.get("request", key)
        store.put("request", key, job["id"], {**frozen, **reply, "status": "accepted"})
        if admission_capacity:
            job = store.update_job(job["id"], route={**job["route"], "context_tokens": admission_capacity})
        state["pending"] = key
        state.update(runtime.tools(state))

    history = store.blob(job["id"], "evidence", {"text": "A" * 5000})["ref"]
    batch("history", tool("read_evidence", {"ref": history}, "history"))
    old_pin = None
    if scenario == "release":
        old_pin = store.blob(job["id"], "evidence", {"text": "P" * 10000})["ref"]
        batch("pin-init", tool("context_update", {"pin": [{"ref": old_pin, "view": "full"}]}, "pin"))
        assert state["pinned"] == [old_pin] and not state.get("context_waiting")
    else:
        assert scenario == "handoff"
        state["handoff"] = store.blob(job["id"], "handoff", {
            "content": handoff(job, current_state="H" * 16000), "deferred": [], "originals": []})["ref"]
    intent = {"notes": "N" * 8000}
    if selection == "pin":
        new_pin = store.blob(job["id"], "evidence", {"text": "N" * 8000})["ref"]
        intent = {"pin": [{"ref": new_pin, "view": "full"}]}
    if old_pin:
        intent["release"] = [old_pin]
    second = store.blob(job["id"], "evidence", {"text": "B" * 5000})["ref"]
    batch("pending", tool("read_evidence", {"ref": second}, "read"),
          tool("context_update", intent, "update"), admission_capacity=35000 if old_pin else 40000)
    assert state["context_waiting"] == "result:pending:1"
    return runtime, job, state


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("scenario", ["release", "handoff"])
@pytest.mark.parametrize("selection", ["notes", "pin"])
def test_unusable_fallback_waits_reopens_and_applies_exact_intent(setup, protocol, scenario, selection):
    store, original = setup
    runtime, job, state = pending_capacity_case(store, original, protocol, scenario, selection)
    old = deepcopy(state)
    proposal_ref = state["context_waiting"]
    proposal_bytes = store.bytes(proposal_ref, job["id"])
    policy = runtime.context.waiting(job["id"], state)["policy"]
    frozen = store.get("request", "pending")
    frozen_bytes = store.bytes(frozen["payload_ref"], job["id"])
    config = {"configurable": {"thread_id": job["id"]}}
    runtime.graph.update_state(config, state, as_node="tools")
    runtime.close()
    low = 25000 if scenario == "release" else 19000
    store.update_job(job["id"], route={**job["route"], "context_tokens": low}, active_seconds=17, attempts=7)
    for _ in range(2):
        runtime = offline_runtime(Store(store.root))
        try:
            runtime.run(job["id"])
            saved = dict(runtime.graph.get_state(config).values)
            assert saved["context_waiting"] == proposal_ref
            assert all(saved[k] == old[k] for k in POLICY)
            assert store.get("job", job["id"])["stop_reason"] == "capacity_blocked"
            assert store.json(saved["context_check"], job["id"])["reason"] == "capacity_blocked"
            assert not any(b["kind"] == "context_settlement" for b in store.records("blob", job["id"]))
            assert store.get("job", job["id"])["attempts"] == 7
            assert store.bytes(proposal_ref, job["id"]) == proposal_bytes
            assert store.bytes(frozen["payload_ref"], job["id"]) == frozen_bytes
            assert store.get("request", "pending")["route"]["context_tokens"] == 50000
        finally:
            runtime.close()
    seen = []
    def respond(request):
        payload = json.loads(request.content)
        seen.append(payload)
        assert '"status": "applied"' in json.dumps(payload).replace('\\"', '"')
        return httpx.Response(200, json=native(protocol, tool("report", {
            "state": "waiting", "message": "The local continuation check is complete."}, "report")))
    store.update_job(job["id"], route={**job["route"], "context_tokens": 500000})
    runtime = Runtime(Store(store.root), Nexus(store, lambda _: "offline", httpx.MockTransport(respond)))
    try:
        runtime.run(job["id"])
        final = dict(runtime.graph.get_state(config).values)
        assert final["context_waiting"] is None
        assert all(final[k] == policy[k] for k in POLICY)
        assert len(seen) == 1 and store.get("job", job["id"])["attempts"] == 8
        assert store.get("job", job["id"])["active_seconds"] >= 17
        assert len([e for e in store.events(job["id"]) if e["type"] == "context_update_settled"]) == 1
        evidence = Evidence(store)
        assert evidence.read(job["id"], proposal_ref)["value"]["context_proposal"]["policy"] == policy
        assert base64.b64decode(evidence.read(job["id"], proposal_ref, view="raw")["data"]) == proposal_bytes
        assert evidence.read(job["id"], proposal_ref, json_pointer="/context_proposal/policy/notes", start=0, end=6)["value"] == policy["notes"][:6]
        assert store.bytes(frozen["payload_ref"], job["id"]) == frozen_bytes
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_unfit_proposal_rejects_when_active_compaction_can_deliver_outcome(setup, protocol):
    store, original = setup
    runtime, job, state = pending_capacity_case(store, original, protocol, "handoff")
    try:
        job = store.update_job(job["id"], route={**job["route"], "context_tokens": 26000})
        assert not runtime.context.normal(job, state)[1]["fits"]
        decided = {**state, **runtime.coordinate(state)}
        receipt = store.bytes(decided["context_feedback"], job["id"])
        assert store.json(decided["context_feedback"], job["id"])["summary"]["status"] == "rejected"
        assert decided["context_waiting"] is None and all(decided[k] == state[k] for k in POLICY)
        prepared = {**decided, **runtime.prepare(decided)}
        frozen = store.get("request", prepared["pending"])
        assert frozen["kind"] == "compaction" and frozen["meta"]["capacity"]["fits"]
        raw = store.bytes(frozen["payload_ref"], job["id"])
        store.update_job(job["id"], route={**job["route"], "context_tokens": 500000})
        # A historical decision and frozen input must not revive or be repriced.
        replayed = {**state, **runtime.coordinate(state)}
        assert replayed["context_waiting"] is None and replayed["context_feedback"] == decided["context_feedback"]
        assert runtime.prepare(replayed)["pending"] == frozen["id"]
        assert store.bytes(frozen["payload_ref"], job["id"]) == raw
        assert store.bytes(decided["context_feedback"], job["id"]) == receipt
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_short_arguments_do_not_defer_an_individually_fitting_result(setup, protocol):
    store, original = setup
    job = protocol_job(store, original, protocol)
    refs, envs = read_batch(store, job, "short", ["L" * 200000, "S" * 1000])
    state = {**state_for(job, ["short"]), "pin_views": {}}
    context = Context(store, Dispatcher(store))
    # Independent feasible input: full short arguments and small result; only the
    # large result is archived. This is an observable retention target, not a copy
    # of the implementation's per-object classification algorithm.
    group = context.group(job, "short", state, deferred={envs[0]["result_ref"]})
    alternative = make_payload(Route.model_validate(job["route"]), SYSTEM,
        [{"role": "user", "content": context.anchor(job, state)}, *group], definitions(False))
    size = estimate(alternative, Route.model_validate(job["route"]))
    job = store.update_job(job["id"], route={**job["route"],
        "context_tokens": size["input_estimate"] + size["output_reserve"] + 20})
    payload, capacity = context.normal(job, state)
    assert capacity["fits"]
    assert capacity["projection"]["deferred"] == [{"request": "short", "refs": [envs[0]["result_ref"]]}]
    assert outputs(payload)[1]["data"]["value"] == {"text": "S" * 1000}
    assert Evidence(store).read(job["id"], refs[0])["value"] == {"text": "L" * 200000}
