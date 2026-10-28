"""Historical dispositions stay final; current estimate uncertainty stays distinct."""
import base64
from copy import deepcopy
import json

import httpx
import pytest

from pdfmd.context import Context, SYSTEM, estimate
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus
from pdfmd.working_context import with_feedback
from pdfmd.runtime import Runtime
from pdfmd.schema import Route
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher, definitions
from test_context_admission import outputs, protocol_job, state_for, synthetic_text
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

    history = store.blob(job["id"], "evidence", {"text": synthetic_text("history-A", 5000)})["ref"]
    batch("history", tool("read_evidence", {"ref": history}, "history"))
    old_pin = None
    if scenario == "release":
        old_pin = store.blob(job["id"], "evidence", {"text": synthetic_text("prior-pin", 10000)})["ref"]
        batch("pin-init", tool("context_update", {"pin": [{"ref": old_pin, "view": "full"}]}, "pin"))
        state.update(runtime.coordinate(state))
        assert state["pinned"] == [old_pin] and not state.get("context_waiting")
    else:
        assert scenario == "handoff"
        state["handoff"] = store.blob(job["id"], "handoff", {
            "content": handoff(job, current_state=synthetic_text("prior-handoff", 16000)), "deferred": [], "originals": []})["ref"]
    intent = {"notes": synthetic_text("new-notes", 8000)}
    if selection == "pin":
        new_pin = store.blob(job["id"], "evidence", {"text": synthetic_text("new-notes", 8000)})["ref"]
        intent = {"pin": [{"ref": new_pin, "view": "full"}]}
    if old_pin:
        intent["release"] = [old_pin]
    second = store.blob(job["id"], "evidence", {"text": synthetic_text("history-B", 5000)})["ref"]
    batch("pending", tool("read_evidence", {"ref": second}, "read"),
          tool("context_update", intent, "update"))
    assert state["context_waiting"] == "context-proposal:pending"
    policy = runtime.context.waiting(job["id"], state)["policy"]
    preview = runtime.context.prospective(job, state)
    mandatory = preview.required(job, {**state, **policy, "context_waiting": None})
    complete = preview.admission(job, {**state, "context_waiting": None}, policy)
    allowance = (mandatory["input_estimate"] + complete["input_estimate"]) // 2
    assert mandatory["input_estimate"] < allowance < complete["input_estimate"]
    job = store.update_job(job["id"], route={**job["route"], "context_tokens": allowance + job["route"]["output_tokens"]})
    return runtime, job, state


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("scenario", ["release", "handoff"])
@pytest.mark.parametrize("selection", ["notes", "pin"])
def test_unusable_fallback_commits_revision_need_and_never_revives_on_restore(setup, protocol, scenario, selection):
    store, original = setup
    runtime, job, state = pending_capacity_case(store, original, protocol, scenario, selection)
    old = deepcopy(state)
    # Seed an explicitly historical confirmed disposition. A current local
    # proxy overflow alone cannot establish this claim.
    runtime.context_updates.reject(job, state, f"{job['id']}:{state['seq']}:{state['revision']}",
        "Historical confirmed necessary-content excess.", reason="required_content_exceeds_capacity")
    proposal_ref = state["context_waiting"]
    proposal_bytes = store.bytes(proposal_ref, job["id"])
    policy = runtime.context.waiting(job["id"], state)["policy"]
    frozen = store.get("request", "pending")
    frozen_bytes = store.bytes(frozen["payload_ref"], job["id"])
    config = {"configurable": {"thread_id": job["id"]}}
    runtime.graph.update_state(config, state, as_node="tools")
    runtime.close()
    low = 4096
    store.update_job(job["id"], route={**job["route"], "context_tokens": low}, active_seconds=17, attempts=7)
    for _ in range(2):
        runtime = offline_runtime(Store(store.root))
        try:
            runtime.run(job["id"])
            saved = dict(runtime.graph.get_state(config).values)
            assert saved["context_waiting"] is None
            assert all(saved[k] == old[k] for k in POLICY)
            assert store.get("job", job["id"])["stop_reason"] == "necessary_estimate_uncertain"
            assert store.json(saved["context_feedback"], job["id"])["summary"]["status"] == "needs_agent_revision"
            assert store.get("context_disposition", proposal_ref)["status"] == "needs_agent_revision"
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
        if not payload.get("tools"):
            return httpx.Response(200, json=native(protocol, text=json.dumps(handoff(job,
                current_state="Original content and the ineligible candidate remain available.",
                unfinished_work=[], references=[], cautions=[]))))
        assert '"status": "needs_agent_revision"' in json.dumps(payload).replace('\\"', '"')
        return httpx.Response(200, json=native(protocol, tool("report", {
            "state": "waiting", "message": "The local continuation check is complete."}, "report")))
    store.update_job(job["id"], route=job["route"])
    runtime = Runtime(Store(store.root), Nexus(store, lambda _: "offline", httpx.MockTransport(respond)))
    try:
        runtime.run(job["id"])
        final = dict(runtime.graph.get_state(config).values)
        assert final["context_waiting"] is None
        assert all(final[k] == old[k] for k in POLICY)
        assert len([p for p in seen if p.get("tools")]) == 1
        assert store.get("job", job["id"])["attempts"] == 7 + len(seen)
        assert store.get("job", job["id"])["active_seconds"] >= 17
        assert len([b for b in store.records("blob", job["id"]) if b["kind"] == "context_settlement"
                    and store.json(b["ref"], job["id"])["feedback"]["proposal_ref"] == proposal_ref]) == 1
        evidence = Evidence(store)
        assert evidence.read(job["id"], proposal_ref)["value"]["context_proposal"]["policy"] == policy
        assert base64.b64decode(evidence.read(job["id"], proposal_ref, view="raw")["data"]) == proposal_bytes
        assert evidence.read(job["id"], proposal_ref, json_pointer="/context_proposal/policy/notes", start=0, end=6)["value"] == policy["notes"][:6]
        assert store.bytes(frozen["payload_ref"], job["id"]) == frozen_bytes
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_historical_revision_need_can_deliver_through_active_compaction(setup, protocol):
    store, original = setup
    runtime, job, state = pending_capacity_case(store, original, protocol, "handoff")
    try:
        historical = runtime.context_updates.reject(job, state, f"{job['id']}:{state['seq']}:{state['revision']}",
            "Historical confirmed necessary-content excess.", reason="required_content_exceeds_capacity")
        diagnostic = {**state, **historical}
        mandatory = runtime.context.required(job, diagnostic)["input_estimate"]
        compact = runtime.context.compact_request(job, diagnostic)[1]["capacity"]["input_estimate"]
        normal = runtime.context.normal(job, diagnostic)[1]["input_estimate"]
        allowance = (max(mandatory, compact) + normal) // 2
        assert max(mandatory, compact) < allowance < normal
        job = store.update_job(job["id"], route={**job["route"],
            "context_tokens": allowance + job["route"]["output_tokens"]})
        assert not runtime.context.normal(job, diagnostic)[1]["fits"]
        decided = {**state, **runtime.coordinate(state)}
        receipt = store.bytes(decided["context_feedback"], job["id"])
        assert store.json(decided["context_feedback"], job["id"])["summary"]["status"] == "needs_agent_revision"
        assert decided["context_waiting"] is None and all(decided[k] == state[k] for k in POLICY)
        prepared = {**decided, **runtime.prepare(decided)}
        frozen = store.get("request", prepared["pending"])
        assert frozen["kind"] == "compaction" and frozen["meta"]["capacity"]["fits"]
        raw = store.bytes(frozen["payload_ref"], job["id"])
        store.update_job(job["id"], route={**job["route"], "context_tokens": 40000})
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
    alternative = with_feedback(Route.model_validate(job["route"]), SYSTEM,
        [{"role": "user", "content": context.anchor(job, state)}, *group], definitions(False), job["head"])
    size = estimate(alternative, Route.model_validate(job["route"]))
    job = store.update_job(job["id"], route={**job["route"],
        "context_tokens": size["input_estimate"] + size["output_reserve"] + 20})
    payload, capacity = context.normal(job, state)
    assert capacity["fits"]
    assert capacity["projection"]["deferred"] == [{"request": "short", "refs": [envs[0]["result_ref"]]}]
    assert outputs(payload)[1]["data"]["value"] == {"text": "S" * 1000}
    assert Evidence(store).read(job["id"], refs[0])["value"] == {"text": "L" * 200000}
