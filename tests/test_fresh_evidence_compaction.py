"""Latest complete tool results reach normal input after bounded prefix compaction.

All replies are local fixtures; these checks do not establish model comprehension.
"""
import base64
from copy import deepcopy
from hashlib import sha256
import json

import httpx
import pytest

from pdfmd.context import Context, HandoffRejected
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus
from pdfmd.runtime import Runtime
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher
from test_context_admission import outputs, protocol_job, settle, state_for
from test_context_progress import compact_body, read_batch
from test_context_plans import candidate
from test_response_repairs import handoff, native
from test_runtime import tool


PROTOCOLS = ["chat_completions", "responses"]


def image_hashes(payload):
    found = []
    def walk(value):
        if isinstance(value, dict):
            if value.get("type") in {"image_url", "input_image"}:
                url = value["image_url"]
                if isinstance(url, dict):
                    url = url["url"]
                found.append(sha256(base64.b64decode(url.split(",", 1)[1])).hexdigest())
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
    walk(payload)
    return found


def pressure_fixture(store, initial, protocol, *, capacity=None):
    job = protocol_job(store, initial, protocol)
    job = store.update_job(job["id"], route={**job["route"], "image_tokens": 12000})
    read_batch(store, job, "older", ["O" * 30000])
    exact = store.blob(job["id"], "evidence", {"text": "E" * 16000})
    envs = settle(store, job, "fresh",
                  tool("read_evidence", {"ref": exact["ref"]}, "new-text"),
                  tool("render_page", {"page": 1, "dpi": 72}, "new-pixels"),
                  tool("render_page", {"page": 1, "dpi": 96}, "new-detail"))
    state = state_for(job, ["older", "fresh"])
    context = Context(store, Dispatcher(store))
    if capacity is None:
        # Establish the intended initial geometry from actual native input.
        # Tool descriptions, exact-read metadata and working-context feedback
        # are real costs: the former fixed 65,536 no longer held this complete
        # fresh batch. Leave room for a short handoff, but not the old prefix.
        # This is fixture setup; the allowance never changes during the flow.
        generous = {**job, "route": {**job["route"], "context_tokens": 1_000_000}}
        measured = context.normal(generous, {**state, "history": ["fresh"]})[1]
        assert measured["projection"]["deferred"] == []
        capacity = measured["input_estimate"] + measured["output_reserve"] + 2000
    job = store.update_job(job["id"], route={**job["route"], "context_tokens": capacity})
    fresh = context.normal(job, {**state, "history": ["fresh"]})[1]
    assert fresh["fits"] and fresh["projection"]["deferred"] == []
    assert not context.normal(job, state)[1]["fits"]
    return job, context, state, exact, envs


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_older_prefix_preserves_complete_fresh_batch_for_normal_request_and_reopen(setup, protocol):
    store, initial = setup
    job, context, state, exact, envs = pressure_fixture(store, initial, protocol)
    before = deepcopy(state)
    originals = {b["ref"]: b["sha256"] for b in store.records("blob", job["id"])}
    assert not context.normal(job, state)[1]["fits"]
    _, meta = context.compact_request(job, state)
    assert meta["covered"] == ["older"]
    assert meta["retained_normal_target"] == {"history": ["fresh"], "deferred": []}
    assert meta["capacity"]["fits"]
    changed = context.apply_handoff(job, state, json.dumps(handoff(job)), meta, "prefix")
    assert state == before and changed["history"] == ["fresh"]
    payload, capacity = context.normal(job, changed)
    assert capacity["fits"] and capacity["projection"]["deferred"] == []
    expected = [store.get("blob", e["data"]["image_ref"])["sha256"] for e in envs[1:]]
    assert image_hashes(payload) == expected
    assert outputs(payload)[0]["data"]["value"]["text"] == "E" * 16000
    assert [out["pixels_delivered"] for out in outputs(payload)[1:]] == [True, True]
    # Catalog application commits before a graph projection is written. Replay
    # recovers that effect and cannot double-apply or replace its originals.
    reopened = Store(store.root)
    again = Context(reopened, Dispatcher(reopened))
    assert again.apply_handoff(job, state, json.dumps(handoff(job)), meta, "prefix") == changed
    assert again.normal(job, changed) == (payload, capacity)
    assert len([e for e in reopened.events(job["id"]) if e["type"] == "context_compacted"]) == 1
    assert all(reopened.get("blob", ref)["sha256"] == digest for ref, digest in originals.items())
    evidence = Evidence(reopened)
    assert evidence.read(job["id"], exact["ref"])["value"]["text"] == "E" * 16000
    assert base64.b64decode(evidence.read(job["id"], exact["ref"], view="raw")["data"]) == reopened.bytes(exact["ref"], job["id"])
    assert evidence.read(job["id"], exact["ref"], json_pointer="/text", start=14, end=26)["value"] == "E" * 12


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_actual_handoff_must_fit_retained_normal_target_without_silent_eviction(setup, protocol):
    store, initial = setup
    job, context, state, _, _ = pressure_fixture(store, initial, protocol)
    before = deepcopy(state)
    _, meta = context.compact_request(job, state)
    assert meta["covered"] == ["older"]
    # This summary shrinks the old prefix, but not enough to carry its retained
    # normal tool results. Net byte savings alone must not accept it.
    oversized = json.dumps(handoff(job, current_state="C" * 25000))
    with pytest.raises(HandoffRejected, match="retained.*normal"):
        context.apply_handoff(job, state, oversized, meta, "long-summary")
    assert state == before
    assert store.json("handoff:long-summary", job["id"])["content"]["current_state"] == "C" * 25000
    assert not any(e["type"] == "context_compacted" for e in store.events(job["id"]))
    revised = context.apply_handoff(job, state, json.dumps(handoff(job)), meta, "short-summary")
    assert revised["history"] == ["fresh"] and context.normal(job, revised)[1]["fits"]


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_unfit_suffix_keeps_rolling_compaction_fallback(setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    read_batch(store, job, "older", ["O" * 30000])
    refs, _ = read_batch(store, job, "large-tail", ["A" * 30000, "B" * 30000])
    context = Context(store, Dispatcher(store))
    state = state_for(job, ["older", "large-tail"])
    assert not context.normal(job, {**state, "history": ["large-tail"]})[1]["fits"]
    _, meta = context.compact_request(job, state)
    assert not meta.get("retained_normal_target")
    changed = context.apply_handoff(job, state, json.dumps(handoff(job)), meta, "rolling")
    assert context.normal(job, changed)[1]["input_estimate"] < context.normal(job, state)[1]["input_estimate"]
    if changed["history"]:
        assert context.compact_request(job, changed)[1]["capacity"]["fits"]
    assert [store.json(ref, job["id"])["text"] for ref in refs] == ["A" * 30000, "B" * 30000]


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_compaction_pixel_absence_is_explicitly_current_request_only(setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    env = settle(store, job, "render", tool("render_page", {"page": 1, "dpi": 72}))[0]
    state = state_for(job, ["render"])
    context = Context(store, Dispatcher(store))
    normal, _ = context.normal(job, state)
    assert image_hashes(normal) == [store.get("blob", env["data"]["image_ref"])["sha256"]]
    compact, _ = context.compact_request(job, state)
    projected = compact_body(compact)["history"][0]["messages"]
    result = next(json.loads(m.get("content", m.get("output"))) for m in projected
                  if m.get("role") == "tool" or m.get("type") == "function_call_output")
    assert result["pixels_delivered"] is False
    assert result["pixel_delivery_scope"] == "current_request_only"
    assert result["prior_pixel_delivery"] == "not_determined_by_this_projection"
    assert not image_hashes(compact)
    assert store.bytes(env["data"]["image_ref"], job["id"])


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_retained_target_uses_specific_pending_policy_and_applied_outcome(setup, protocol):
    store, initial = setup
    job, context, state, _, _ = pressure_fixture(store, initial, protocol, capacity=75000)
    policy = context.policy(job["id"], state, {"notes": "N" * 6000})
    state = candidate(store, job, state, policy)
    _, meta = context.compact_request(job, state)
    assert meta["covered"] == ["older"] and meta["retained_normal_target"]
    with pytest.raises(HandoffRejected, match="retained.*normal"):
        context.apply_handoff(job, state, json.dumps(handoff(job, current_state="C" * 8000)), meta, "pending-long")
    active_after = {**state, "history": ["fresh"], "handoff": "handoff:pending-long", "context_waiting": None}
    assert context.normal(job, active_after)[1]["fits"]
    preview = context.prospective(job, state)
    assert not preview.admission(job, active_after, policy)["fits"]
    changed = context.apply_handoff(job, state, json.dumps(handoff(job)), meta, "pending-short")
    assert context.handoff_target(job, changed)["fits"]
    assert changed["notes"] == state["notes"]  # Compaction never commits the proposal.


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_retained_results_cannot_disappear_to_make_long_summary_fit(setup, protocol):
    store, initial = setup
    job, context, state, _, _ = pressure_fixture(store, initial, protocol)
    _, meta = context.compact_request(job, state)
    with pytest.raises(HandoffRejected, match="retained.*normal"):
        context.apply_handoff(job, state, json.dumps(handoff(job, current_state="C" * 37000)), meta, "deferring-summary")
    observed = context.normal(job, {**state, "history": ["fresh"], "handoff": "handoff:deferring-summary"})[1]
    assert observed["fits"] and observed["projection"]["deferred"]
    assert not any(e["type"] == "context_compacted" for e in store.events(job["id"]))


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_retained_target_correction_budget_survives_runtime_reopen(setup, protocol):
    store, initial = setup
    job, _, state, _, _ = pressure_fixture(store, initial, protocol)
    job = store.update_job(job["id"], limits={**job["limits"], "max_response_repairs": 1})
    seen = []
    def reply(request):
        payload = json.loads(request.content)
        assert not payload.get("tools")  # Only offline compaction corrections.
        seen.append(payload)
        return httpx.Response(200, json=native(protocol, text=json.dumps(handoff(job, current_state="C" * 25000))))
    service = Nexus(store, lambda _: "offline-only", httpx.MockTransport(reply))
    runtime = Runtime(store, service)
    config = {"configurable": {"thread_id": job["id"]}}
    runtime.graph.update_state(config, state, as_node="tools")
    runtime.run(job["id"])
    before = dict(runtime.graph.get_state(config).values)
    runtime.close()
    assert len(seen) == store.get("job", job["id"])["attempts"] == 2
    assert store.get("job", job["id"])["stop_reason"] == "response_repair_exhausted"
    assert before["history"] == state["history"] and before["handoff"] is None
    frozen = {r["id"]: store.bytes(r["payload_ref"], job["id"]) for r in store.records("request", job["id"]) if r.get("payload_ref")}
    reopened = Store(store.root)
    runtime = Runtime(reopened, Nexus(reopened, lambda _: "offline-only", httpx.MockTransport(reply)))
    runtime.run(job["id"], continue_failed=True)
    after = dict(runtime.graph.get_state(config).values)
    runtime.close()
    assert len(seen) == reopened.get("job", job["id"])["attempts"] == 2
    assert after["history"] == before["history"] and after["repairs"] == before["repairs"]
    assert all(reopened.bytes(reopened.get("request", key)["payload_ref"], job["id"]) == data for key, data in frozen.items())
