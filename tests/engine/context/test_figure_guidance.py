"""Transmitted FD-01 instructions and continuation mechanics, not visual judgment."""
from hashlib import sha256
import json

import httpx
import pytest

from pdfmd.context import Context, SYSTEM, COMPACT, estimate
from pdfmd.nexus import Nexus
from pdfmd.schema import Route
from pdfmd.storage import Store, encode
from pdfmd.tools import Dispatcher
from tests.engine.context.test_context import history
from tests.engine.context.test_context_admission import protocol_job, state_for, synthetic_text
from tests.engine.transport.test_response_repairs import native


def send_fixture(store, job, payload, capacity, key, kind):
    seen = []

    def serve(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=native(job["route"]["protocol"], text="Offline fixture only."))

    nexus = Nexus(store, lambda _: "offline-fixture", httpx.MockTransport(serve))
    frozen = nexus.freeze(job["id"], key, payload, kind, {"capacity": capacity})
    nexus.send(job["id"], key)
    assert seen == [payload]
    assert frozen["meta"]["capacity"]["request_sha256"] == sha256(encode(seen[0])).hexdigest()
    assert frozen["meta"]["capacity"]["request_bytes"] == len(encode(seen[0]))
    return seen[0]


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("scripts", [False, True])
def test_normal_transmits_figure_obligations_tools_and_actual_cost(setup, protocol, scripts):
    store, job = setup
    job = protocol_job(store, job, protocol)
    job = store.update_job(job["id"], amendments=["Preserve negation, all panels and original physical page identities."])
    context = Context(store, Dispatcher(store, scripts=scripts))
    payload, capacity = context.normal(job, state_for(job, []))
    transmitted = send_fixture(store, job, payload, capacity, "normal", "normal")
    system = transmitted["messages"][0]["content"] if protocol == "chat_completions" else transmitted["instructions"]
    assert system == SYSTEM
    # Discriminating obligations missing from the earlier effective guidance.
    for obligation in ["independent figure crops", "without a figure number, caption, or labels",
                       "actual figure/panel associations", "Agent description (not a source caption)",
                       "required gaps prevent a complete claim", "actual selected saved version"]:
        assert obligation in system
    assert job["amendments"][0] in json.dumps(transmitted)
    tools = {entry["function"]["name"]: entry["function"] for entry in transmitted["tools"]} if protocol == "chat_completions" else {entry["name"]: entry for entry in transmitted["tools"]}
    assert "adjacent searchable text automatically" in tools["render_page"]["description"]
    assert "not automatically a complete independent figure" in tools["extract_image"]["description"]
    assert ("run_script" in tools) == scripts
    assert capacity["input_estimate"] == estimate(transmitted, Route.model_validate(job["route"]))["input_estimate"]
    assert capacity["fallback"] is None and capacity["images"] == 0
    assert context.required(job, state_for(job, []))["proof_available"] is False


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_compaction_and_reopened_continuation_preserve_figure_work(setup, protocol):
    store, job = setup
    job = protocol_job(store, job, protocol)
    job = store.update_job(job["id"], amendments=["Convert only original physical page 1; preserve all substantive figures."])
    source, _ = history(store, job["id"], "read", synthetic_text("figure-pressure", 35000))
    context = Context(store, Dispatcher(store))
    state = state_for(job, ["read"])
    state["notes"] = "Independent crop and panel-text association are unfinished; source caption absent."
    compact, meta = context.compact_request(job, state)
    transmitted = send_fixture(store, job, compact, meta["capacity"], "compact", "compaction")
    instruction = transmitted["messages"][0]["content"] if protocol == "chat_completions" else transmitted["instructions"]
    assert instruction == COMPACT
    assert "unfinished crop/text associations" in instruction and "without captions or labels" in instruction
    assert job["amendments"][0] in json.dumps(transmitted)
    # The response is developer-authored fixture data, not a natural model handoff.
    handoff = {"task": job["scope"], "current_state": "No verified figure delivery yet.",
               "unfinished_work": [state["notes"]], "dependencies": ["Read edge labels before claiming complete."],
               "references": [job["source_ref"], source["ref"]],
               "cautions": ["Agent description (not a source caption); do not invent an original title."]}
    changed = context.apply_handoff(job, state, json.dumps(handoff), meta, "compact")
    reopened = Context(Store(store.root), Dispatcher(Store(store.root)))
    next_payload, capacity = reopened.normal(store.get("job", job["id"]), changed)
    wire = json.dumps(send_fixture(store, job, next_payload, capacity, "continued", "normal"))
    assert "independent figure crops" in wire and job["amendments"][0] in wire
    assert state["notes"] in wire and source["ref"] in wire
    assert reopened.store.json(changed["handoff"], job["id"])["content"] == handoff
    assert store.bytes(source["ref"], job["id"]) == reopened.store.bytes(source["ref"], job["id"])
