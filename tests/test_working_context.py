"""Local input truthfulness and read-only choice previews, not model behavior."""
from copy import deepcopy
import json

import pytest

from pdfmd.context import Context, estimate
from pdfmd.nexus import Nexus
from pdfmd.schema import Route
from pdfmd.storage import encode
from pdfmd.tools import Dispatcher
from pdfmd.working_context import inspect, inventory, snapshot, summarize, with_feedback
from test_context_admission import protocol_job, settle, state_for
from test_runtime import tool
from test_working_evidence_delivery import feedback


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_feedback_counts_itself_at_digit_boundaries(protocol, route):
    endpoint = "responses" if protocol == "responses" else "chat/completions"
    route = Route.model_validate({**route, "protocol": protocol, "endpoint": f"http://127.0.0.1:8317/v1/{endpoint}"})
    # Independent review found 9/10 headroom could oscillate with the number's
    # own printed cost. Exercise both signs and decimal transitions, not one fix.
    initial = with_feedback(route, "x" * 12000, [], [], None)
    base = estimate(initial, route)["input_estimate"] + route.output_tokens
    for limit in range(base - 115, base + 116):
        selected = route.model_copy(update={"context_tokens": limit})
        payload = with_feedback(selected, "x" * 12000, [], [], None)
        actual = estimate(payload, selected)
        summary = feedback(payload)
        assert actual["input_estimate"] <= summary["input_estimate"] <= actual["input_estimate"] + 16
        assert summary["remaining"] == limit - selected.output_tokens - summary["input_estimate"]


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_snapshot_preview_representation_cost_and_no_effect(setup, protocol):
    store, original = setup
    job = protocol_job(store, original, protocol)
    dispatcher = Dispatcher(store)
    context = Context(store, dispatcher)
    ref = store.blob(job["id"], "evidence", {"text": "字\\\"" * 3000})["ref"]
    env = settle(store, job, "read", tool("read_evidence", {"ref": ref}, "read"))[0]
    state = state_for(job, ["read"])
    payload, capacity = context.normal(job, state)
    assert not capacity["projection"]["deferred"]
    request = Nexus(store, lambda _: pytest.fail("No model call permitted")).freeze(
        job["id"], "snapshot", payload, "normal", {"capacity": capacity, "context_snapshot": snapshot(job, state)})
    # A later operation is deliberately outside this snapshot.
    settle(store, job, "later", tool("read_evidence", {"ref": ref, "json_pointer": "/text", "start": 0, "end": 2}, "new"))
    with store.connect() as db:
        records_before = list(db.execute("SELECT * FROM records ORDER BY kind,id"))
        events_before = list(db.execute("SELECT * FROM events ORDER BY seq"))
    frozen_before = store.bytes(request["payload_ref"], job["id"])
    state_before = deepcopy(state)
    result = inspect(context, request, job, changes={"pin": [{"ref": ref, "view": "full", "json_pointer": "/text", "start": 0, "end": 2}],
                                                   "release": [env["result_ref"]]})
    assert result["preview"]["input_delta"] < 0
    assert result["preview"]["applied"] is False
    assert result["current_input"]["input_estimate"] == estimate(payload, Route.model_validate(job["route"]))["input_estimate"]
    bodies = [row for row in result["inventory"] if row["location"] == "tool_history"]
    assert len(bodies) == 1 and bodies[0]["result_ref"] == env["result_ref"]
    assert bodies[0]["release_ref"] == env["result_ref"]
    assert {row["call_id"] for row in result["inventory"]} == {"read"}
    assert result["current_input"]["tool_definitions_delta"] > 0
    assert result["current_input"]["message_group_deltas"]["tool_history"] > 0
    page = inspect(context, request, job, start=0, end=0)
    assert page["inventory"] == [] and page["total"] == 2 and not page["inventory_complete"]
    assert "ALL tool results" in result["scope"]
    assert state == state_before
    assert store.bytes(request["payload_ref"], job["id"]) == frozen_before
    with store.connect() as db:
        assert list(db.execute("SELECT * FROM records ORDER BY kind,id")) == records_before
        assert list(db.execute("SELECT * FROM events ORDER BY seq")) == events_before


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_precise_new_read_feedback_does_not_claim_old_root_present(setup, protocol):
    store, original = setup
    job = protocol_job(store, original, protocol)
    dispatcher = Dispatcher(store)
    draft = dispatcher.execute(job["id"], "draft", "edit_document", json.dumps({
        "base_version": None, "expected_head": None,
        "replace_blocks": [{"id": "source", "pages": [1], "markdown": "Exact kept text."}],
        "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "partial"}))
    assert draft["ok"], draft
    version = draft["data"]["version_id"]
    job = store.get("job", job["id"])
    settle(store, job, "precise", tool("read_document", {"version_id": version, "json_pointer": "/content/blocks/0/markdown"}, "select"))
    state = state_for(job, ["precise"])
    context = Context(store, dispatcher)
    payload, _ = context.normal(job, state)
    summary = feedback(payload)
    assert summary["head"] == version
    assert summary["document_reads"]["full"] == 0
    assert summary["document_reads"]["selection"] == 1
    assert 'Exact kept text.' in json.dumps(payload)


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_historical_or_changed_recipe_cannot_claim_exact_preview(setup, protocol):
    store, original = setup
    job = protocol_job(store, original, protocol)
    context = Context(store, Dispatcher(store))
    state = state_for(job, [])
    payload, capacity = context.normal(job, state)
    request = Nexus(store, lambda _: "unused").freeze(job["id"], "historical", payload, "normal", {"capacity": capacity})
    assert inspect(context, request, job)["inventory"] == []
    with pytest.raises(ValueError, match="no context snapshot"):
        inspect(context, request, job, changes={"notes": "new"})
    hypothetical = {**request, "meta": {"context_snapshot": snapshot({**job, "head": "changed-head"}, state)}}
    with pytest.raises(ValueError, match="cannot reproduce"):
        inspect(context, hypothetical, job, changes={"notes": "new"})
    assert store.bytes(request["payload_ref"], job["id"]) == encode(payload)


def test_authored_draft_arguments_are_visible_and_receipt_is_not_a_document_read():
    arguments = json.dumps({"replace_blocks": [{"id": "draft", "markdown": "Exact drafted wording. " * 1000}]})
    messages = [{"role": "assistant", "content": None, "tool_calls": [{"id": "save", "type": "function",
                 "function": {"name": "edit_document", "arguments": arguments}}]},
                {"role": "tool", "tool_call_id": "save", "content": json.dumps({"candidate_ref": "candidate:save",
                 "result_ref": "result:save", "data": {"version_id": "saved-version", "claim": "partial"}})}]
    rows = inventory(messages)
    authored = next(row for row in rows if row["representation"] == "arguments")
    assert authored["body_utf8_bytes"] == len(arguments.encode("utf-8"))
    assert authored["release_ref"] == "candidate:save"
    assert summarize(rows, "saved-version")["document_reads"]["body_utf8_bytes"] == 0


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_repeated_call_ids_keep_their_own_argument_release_reference(protocol):
    messages = []
    for index in (1, 2):
        args = json.dumps({"notes": f"Saved intent {index}"})
        receipt = json.dumps({"candidate_ref": f"candidate:{index}", "result_ref": f"result:{index}", "data": {"ok": True}})
        if protocol == "chat_completions":
            messages += [{"role": "assistant", "tool_calls": [{"id": "reused", "function": {"name": "context_update", "arguments": args}}]},
                         {"role": "tool", "tool_call_id": "reused", "content": receipt}]
        else:
            messages += [{"type": "function_call", "name": "context_update", "call_id": "reused", "arguments": args},
                         {"type": "function_call_output", "call_id": "reused", "output": receipt}]
    arguments = [row for row in inventory(messages) if row["location"] == "tool_arguments"]
    assert [row["release_ref"] for row in arguments] == ["candidate:1", "candidate:2"]
