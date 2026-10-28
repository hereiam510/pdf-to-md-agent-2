"""Purpose-specific context planning; all responses and evidence are local fixtures."""
from copy import deepcopy
import json
import random
import string

import pytest

from pdfmd.context import Context
from pdfmd.context_outcomes import policy_ref
from pdfmd.nexus import StopRun, instruction_basis
from pdfmd.storage import encode
from pdfmd.tools import Dispatcher
from test_context_admission import outputs, protocol_job, state_for
from test_context_progress import read_batch
from test_response_repairs import handoff, native
from test_runtime import tool
from pdfmd.nexus import parse_reply


PROTOCOLS = ["chat_completions", "responses"]


def varied_text(size, seed=0):
    """Deterministic synthetic text for capacity transitions, not calibration."""
    return "".join(random.Random(seed).choices(string.ascii_letters + string.digits + " ", k=size))


def candidate(store, job, state, policy, operations=()):
    ref = "context-proposal:fixture"
    store.blob(job["id"], "context_proposal", {"context_proposal": {
        "policy": policy, "instruction_basis": instruction_basis(job),
        "previous": None, "operations": list(operations), "valid": True}}, key=ref)
    return {**state, "context_waiting": ref, "context_latest": ref}


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("kind", ["index", "range", "notes"])
def test_actual_compaction_of_old_policy_is_not_gated_by_normal_reserve(setup, protocol, kind):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    context = Context(store, Dispatcher(store))
    state = {**state_for(job, []), "notes": "", "pin_views": {}}
    if kind == "notes":
        state["notes"] = varied_text(10500)
        changes = {"notes": "Keep exact source values and continue."}
        retained = state["notes"]
    else:
        saved = store.blob(job["id"], "evidence", {"text": varied_text(10500)})["ref"]
        state.update(context.policy(job["id"], state, {"pin": [{"ref": saved, "view": "full"}]}))
        selected = {"ref": saved, "view": "index"} if kind == "index" else {
            "ref": saved, "view": "full", "json_pointer": "/text", "start": 0, "end": 100}
        changes = {"pin": [selected]}
        retained = varied_text(10500)
    before = deepcopy(state)
    baseline = context.normal(job, state)[1]
    job = store.update_job(job["id"], route={**job["route"],
        "context_tokens": baseline["input_estimate"] + baseline["output_reserve"] + 100})
    assert context.normal(job, state)[1]["fits"]
    read_batch(store, job, "history", ["A" * 6000, "B" * 6000])
    policy = context.policy(job["id"], state, changes)
    state = candidate(store, job, {**state, "history": ["history"]}, policy)
    assert not context.normal(job, {**state, "history": [], "handoff": None})[1]["fits"]
    payload, meta = context.compact_request(job, state)
    assert meta["capacity"]["fits"] and retained in json.dumps(payload)
    projected = context.apply_handoff(job, state, json.dumps(handoff(job)), meta, "old-policy-compact")
    exact = context.prospective(job, projected)
    capacity = exact.admission(job, {**projected, "context_waiting": None}, policy)
    assert capacity["fits"] and not capacity["additional_deferrals"]
    assert all(state[k] == before[k] for k in ("pinned", "pin_views", "notes", "released"))
    assert projected["history"] == []


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_last_handoff_uses_specific_applied_outcome_not_unknown_reserve(setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    context = Context(store, Dispatcher(store))
    pin = store.blob(job["id"], "evidence", {"text": varied_text(18000)})["ref"]
    state = {**state_for(job, []), "notes": "Active notes.", "pin_views": {}}
    state.update(context.policy(job["id"], state, {"pin": [{"ref": pin, "view": "full"}]}))
    read_batch(store, job, "history", ["A" * 5000, "B" * 5000])
    policy = context.policy(job["id"], state, {"release": [pin], "notes": "N" * 8000})
    state = candidate(store, job, {**state, "history": ["history"]}, policy)
    text = json.dumps(handoff(job, current_state="C" * 1200))
    record = {"content": json.loads(text), "covered": ["history"], "deferred": [], "request": "last",
        "projection": [], "previous_archive_ref": None,
        "originals": [store.get("request", "history")["accepted_ref"]]}
    ref = store.blob(job["id"], "handoff", record, key="handoff:last")["ref"]
    future = {**state, "handoff": ref, "history": [], "revision": state["revision"] + 1}
    exact = context.prospective(job, future)
    cap = exact.normal(job, {**future, **policy, "context_waiting": None})[1]
    job = store.update_job(job["id"], route={**job["route"],
        "context_tokens": cap["input_estimate"] + cap["output_reserve"]})
    assert not context.normal(job, {**future, **policy})[1]["fits"]
    _, meta = context.compact_request(job, state)
    assert meta["covered"] == ["history"] and meta["projection"] == []
    result = context.apply_handoff(job, state, text, meta, "last")
    admission = exact.admission(job, {**result, "context_waiting": None}, policy)
    assert admission["fits"] and not admission["additional_deferrals"]
    assert context.prospective(job, result).update_feedback == exact.update_feedback


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_positive_body_saving_preserves_the_later_full_evidence_batch(setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    _, envs = read_batch(store, job, "mixed", [varied_text(100000), "S" * 600])
    read_batch(store, job, "tail", [varied_text(22000, 1), varied_text(22000, 2)])
    context = Context(store, Dispatcher(store))
    state = state_for(job, ["mixed", "tail"])
    roomy = {**job, "route": {**job["route"], "context_tokens": 1000000}}
    single = context.compact_request(roomy, {**state, "history": ["tail"]})[1]["capacity"]
    job = store.update_job(job["id"], route={**job["route"],
        "context_tokens": single["input_estimate"] + single["output_reserve"] + 256})
    normal = context.normal(job, state)[1]
    already = next(set(item["refs"]) for item in normal["projection"]["deferred"] if item["request"] == "mixed")
    current = context.group(job, "mixed", state, deferred=already)
    full_refs = context.group(job, "mixed", state, deferred=context.batch_refs(job, "mixed"))
    result_only = context.group(job, "mixed", state, deferred=already | {envs[1]["result_ref"]})
    assert len(encode(current)) <= len(encode(full_refs))
    assert len(encode(current)) > len(encode(result_only))
    _, meta = context.compact_request(job, state)
    assert meta["covered"] == ["mixed"]
    assert all(item["request"] != "tail" for item in meta["projection"])
    # No source is removed merely because its emitted representation changed.
    assert store.json(envs[1]["result_ref"], job["id"]) == envs[1]["data"]


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_mandatory_projection_is_not_a_token_lower_bound_and_preserves_history(setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    context = Context(store, Dispatcher(store))
    bodies = [varied_text(50000, 1), varied_text(50000, 2)]
    read_batch(store, job, "history", bodies)
    state = state_for(job, ["history"])
    bound = context.required(job, state)
    assert bound["fits"] and not bound["proved_excess"] and not bound["proves_full_admission"]
    assert not bound["proof_available"] and bound["necessary_cost_lower_bound"] is None
    payload, capacity = context.normal(job, state)
    assert not capacity["fits"] and all(body in json.dumps(payload) for body in bodies)
    assert state["history"] == ["history"]
    oversized = {**state, "notes": varied_text(100000)}
    reservation = context.required(job, oversized)
    assert not reservation["fits"] and reservation["classification"] == "necessary_estimate_uncertain"
    assert not reservation["proved_excess"] and not reservation["proof_available"]
    assert reservation["necessary_cost_lower_bound"] is None and not reservation["proves_full_admission"]


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_reservation_alone_cannot_prove_mandatory_token_excess(setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    context = Context(store, Dispatcher(store))
    state = state_for(job, [])
    measured = context.required(job, state)
    # Both values come from the proxy: this chooses a synthetic boundary only.
    # It does not use the unreserved count as independent token ground truth.
    allowance = (measured["unreserved_estimate"] + measured["input_estimate"]) // 2
    job = store.update_job(job["id"], route={**job["route"],
        "context_tokens": allowance + job["route"]["output_tokens"]})
    required = context.required(job, state)
    assert required["unreserved_estimate"] < allowance < required["input_estimate"]
    assert not required["fits"] and required["classification"] == "necessary_estimate_uncertain"
    assert not required["proved_excess"] and not required["proof_available"]
    assert required["necessary_cost_lower_bound"] is None


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_actual_outcome_projection_avoids_duplicate_but_survives_removed_batch(setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    call = tool("context_update", {"notes": "Chosen notes"}, "context")
    reply = parse_reply(protocol, json.dumps(native(protocol, call)).encode())
    accepted = store.blob(job["id"], "accepted_response", reply)
    store.put("request", "batch", job["id"], {"accepted_ref": accepted["ref"]})
    dispatcher = Dispatcher(store)
    digest, raw = dispatcher.capture(job["id"], "batch:0", "context_update", call["function"]["arguments"])
    dispatcher.settle(job["id"], "batch:0", "context_update", digest, raw["ref"],
        {"context_saved": {"intent": {"notes": "Chosen notes"}}, "admission": {"applied": False, "status": "saved"}}, True)
    state = state_for(job, ["batch"])
    state = candidate(store, job, state, {"pinned": [], "released": [], "pin_views": {}, "notes": "Chosen notes"}, ["batch:0"])
    original = store.bytes("result:batch:0", job["id"])
    context = Context(store, dispatcher).prospective(job, state)
    state = {**state, "context_waiting": None, "notes": "Chosen notes"}
    payload, _ = context.normal(job, state)
    projected = outputs(payload)[0]["data"]
    assert projected["admission"] == {"applied": False, "status": "saved"}
    assert projected["context_outcome"] == context.update_feedback
    assert "Deferred context update outcome:" not in json.dumps(payload)
    without_batch, _ = context.normal(job, {**state, "history": []})
    assert "Deferred context update outcome:" in json.dumps(without_batch)
    assert store.bytes("result:batch:0", job["id"]) == original
    anchor = json.loads(context.anchor(job, state))
    assert anchor["context_policy_ref"] == policy_ref(state)
    assert anchor["context_candidate_ref"] == state["context_latest"]


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_unknown_image_cost_is_not_proved_excess_and_true_compaction_overflow_stops(setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    dispatcher = Dispatcher(store)
    image = dispatcher.evidence.render_page(job["id"], page=1, dpi=72)["image_ref"]
    state = {**state_for(job, []), "pin_views": {}}
    context = Context(store, dispatcher)
    state.update(context.policy(job["id"], state, {"pin": [{"ref": image, "view": "image"}]}))
    unknown = {**job, "route": {**job["route"], "image_tokens": None}}
    with pytest.raises(StopRun) as failure:
        context.required(unknown, state)
    assert failure.value.reason == "capacity_configuration"
    conservative = {**job, "route": {**job["route"], "image_tokens": 100000}}
    configured = context.required(conservative, state)
    assert configured["images"] == 1 and not configured["fits"]
    assert not configured["proved_excess"] and not configured["proof_available"]
    assert configured["classification"] == "necessary_estimate_uncertain"
    body = varied_text(120000)
    huge = store.blob(job["id"], "evidence", {"text": body})["ref"]
    read_batch(store, job, "history", ["A" * 1000])
    oversized = {**state_for(job, ["history"]), "pinned": [huge]}
    with pytest.raises(StopRun) as failure:
        context.compact_request(job, oversized)
    assert failure.value.reason == "capacity_blocked"
    assert store.json(huge, job["id"])["text"] == body
    assert oversized["pinned"] == [huge] and oversized["history"] == ["history"]
