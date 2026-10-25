"""Behavioral checks for whole-batch context authority. All transports are local mocks."""
from copy import deepcopy
import json

import httpx
import pytest

from pdfmd.context import Context
from pdfmd.context_outcomes import policy_ref
from pdfmd.documents import Documents
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus, StopRun, instruction_basis, parse_reply
from pdfmd.runtime import Runtime
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher
from test_context_admission import outputs, protocol_job, state_for
from test_context_progress import read_batch
from test_response_repairs import handoff, native
from test_runtime import tool


PROTOCOLS = ["chat_completions", "responses"]
POLICY = ("notes", "pinned", "pin_views", "released")


def snapshot(runtime, job):
    return dict(runtime.graph.get_state({"configurable": {"thread_id": job["id"]}}).values)


def settlements(store, job):
    return [store.json(b["ref"], job["id"]) for b in store.records("blob", job["id"])
            if b["kind"] == "context_settlement"]


def offline(store):
    def forbidden(*_):
        raise AssertionError("Unexpected inference in a local state transition")
    return Runtime(store, Nexus(store, forbidden, httpx.MockTransport(forbidden)))


def accepted_batch(runtime, job, state, key, *calls):
    """Record a synthetic accepted batch with exact frozen input, then execute tools."""
    payload, capacity = runtime.context.normal(job, state)
    request = runtime.nexus.freeze(job["id"], key, payload, "normal", {"capacity": capacity})
    reply = parse_reply(job["route"]["protocol"], json.dumps(native(job["route"]["protocol"], *calls)).encode())
    ref = runtime.store.blob(job["id"], "accepted_response", reply)["ref"]
    runtime.store.put("request", key, job["id"], {**request, "status": "accepted", "accepted_ref": ref})
    original = {**state, "pending": key}
    return {**state, **runtime.tools(original)}, original


def coordinate(runtime, state):
    return {**state, **runtime.coordinate(state)}


def raw_receipts(store, job):
    return {b["ref"]: store.bytes(b["ref"], job["id"])
            for b in store.records("blob", job["id"]) if b["kind"] == "tool_result"}


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_whole_batch_replacement_uses_final_policy_and_settles_before_report(setup, protocol):
    store, original = setup
    job = protocol_job(store, original, protocol)
    refs = [store.blob(job["id"], "evidence", {"text": char * 9000})["ref"] for char in "XY"]
    state = {**state_for(job, [], [refs[0]]), "pin_views": {refs[0]: [{"ref": refs[0], "view": "full"}]}}
    context = Context(store, Dispatcher(store))
    cap = context.normal(job, state)[1]
    job = store.update_job(job["id"], route={**job["route"],
        "context_tokens": cap["input_estimate"] + cap["output_reserve"] + 3500})
    assert context.normal(job, state)[1]["fits"]
    intermediate = context.policy(job["id"], state, {"pin": [{"ref": refs[1], "view": "full"}]})
    assert not context.normal(job, {**state, **intermediate})[1]["fits"]
    calls = []
    def reply(request):
        calls.append(json.loads(request.content))
        assert len(calls) == 1, "Local whole-batch settlement needs no extra model call"
        return httpx.Response(200, json=native(protocol,
            tool("context_update", {"pin": [{"ref": refs[1], "view": "full"}]}, "pin-y"),
            tool("context_update", {"release": [refs[0]]}, "release-x"),
            tool("report", {"state": "waiting", "message": "Local scenario finished."}, "report")))
    runtime = Runtime(store, Nexus(store, lambda _: "mock-only", httpx.MockTransport(reply)))
    try:
        runtime.graph.update_state({"configurable": {"thread_id": job["id"]}}, state, as_node="tools")
        runtime.run(job["id"])
        final = snapshot(runtime, job)
        assert final["pinned"] == [refs[1]] and refs[0] in final["released"]
        assert final["pin_views"][refs[1]] == [{"ref": refs[1], "view": "full"}]
        assert not final.get("context_waiting")
        assert settlements(store, job)[-1]["feedback"]["status"] == "applied"
        for op in store.records("operation", job["id"]):
            if op["tool"] == "context_update":
                saved = store.json(op["result_ref"], job["id"])
                assert saved["admission"]["applied"] is False
        assert store.get("job", job["id"])["stop_reason"] == "agent_report"
        assert store.get("job", job["id"])["attempts"] == 1
        for ref, char in zip(refs, "XY"):
            assert Evidence(store).read(job["id"], ref)["value"] == {"text": char * 9000}
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_invalid_later_update_blocks_entire_context_revision_but_keeps_document(setup, protocol):
    store, original = setup
    job = protocol_job(store, original, protocol)
    y = store.blob(job["id"], "evidence", {"text": "Keep 25 mg."})["ref"]
    draft = Dispatcher(store).execute(job["id"], "draft", "edit_document", json.dumps({
        "base_version": None, "expected_head": None,
        "replace_blocks": [{"id": "section", "pages": [1], "markdown": "Keep 25 mg."}],
        "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "partial"}))
    assert draft["ok"]
    version = draft["data"]["version_id"]
    state = {**state_for(job, []), "notes": "Existing valid policy", "pin_views": {}}
    runtime = offline(store)
    try:
        changed, _ = accepted_batch(runtime, store.get("job", job["id"]), state, "invalid",
            tool("context_update", {"notes": "Work from Y."}, "notes"),
            tool("context_update", {"pin": [{"ref": y, "view": "full", "start": 40, "end": 2}]}, "bad-pin"),
            tool("edit_document", {"base_version": version, "expected_head": version, "title": "Saved improvement"}, "edit"),
            tool("context_update", {"notes": "A later valid update must not erase the error."}, "later"))
        receipt_bytes = raw_receipts(store, job)
        final = coordinate(runtime, changed)
        assert final["notes"] == state["notes"] and final["pinned"] == []
        assert settlements(store, job)[-1]["feedback"]["status"] == "needs_agent_revision"
        assert not final.get("context_waiting")
        assert Documents(store).version(job["id"], store.get("job", job["id"])["head"])["content"]["title"] == "Saved improvement"
        assert Documents(store).version(job["id"], version)["content"]["blocks"][0]["markdown"] == "Keep 25 mg."
        assert raw_receipts(store, job) == receipt_bytes
        # A larger allowance cannot repair invalid parameters or activate only notes.
        store.update_job(job["id"], route={**job["route"], "context_tokens": 500000})
        replay = coordinate(runtime, changed)
        assert all(replay.get(k, [] if k != "notes" else "") == final.get(k, [] if k != "notes" else "") for k in POLICY)
        assert len(settlements(store, job)) == 1
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_oversized_final_candidate_has_durable_revision_result_even_when_feedback_blocked(setup, protocol):
    store, original = setup
    job = protocol_job(store, original, protocol)
    raw = store.blob(job["id"], "evidence", b"R" * 100000)["ref"]
    state = {**state_for(job, []), "notes": "Keep the active policy", "pin_views": {}}
    runtime = offline(store)
    try:
        changed, _ = accepted_batch(runtime, job, state, "oversize",
            tool("context_update", {"pin": [{"ref": raw, "view": "raw"}], "notes": "Proposed large policy"}, "raw"))
        frozen = store.get("request", "oversize")
        frozen_bytes = store.bytes(frozen["payload_ref"], job["id"])
        original_receipt = store.bytes("result:oversize:0", job["id"])
        # Make even the unchanged active-policy diagnostic request unusable.
        store.update_job(job["id"], route={**job["route"], "context_tokens": 4096, "output_tokens": 512}, attempts=7, active_seconds=17)
        decided = coordinate(runtime, changed)
        record = settlements(store, job)[-1]
        assert record["feedback"]["status"] == "needs_agent_revision"
        assert record["feedback"]["reason"] == "required_content_exceeds_capacity"
        assert not decided.get("context_waiting") and decided["notes"] == state["notes"]
        assert decided["pinned"] == []
        with pytest.raises(StopRun):
            runtime.prepare(decided)
        config = {"configurable": {"thread_id": job["id"]}}
        runtime.graph.update_state(config, decided, as_node="tools")
    finally:
        runtime.close()
    store = Store(store.root)
    store.update_job(job["id"], route=job["route"])
    reopened = offline(store)
    try:
        final = coordinate(reopened, snapshot(reopened, job))
        assert not final.get("context_waiting") and final["pinned"] == []
        assert settlements(store, job)[-1] == record
        assert len(settlements(store, job)) == 1
        assert store.bytes("result:oversize:0", job["id"]) == original_receipt
        assert store.bytes(frozen["payload_ref"], job["id"]) == frozen_bytes
        assert store.get("request", "oversize")["route"] == frozen["route"]
        assert store.get("job", job["id"])["attempts"] == 7
        assert store.get("job", job["id"])["active_seconds"] == 17
        assert store.bytes(raw, job["id"]) == b"R" * 100000
    finally:
        reopened.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("dispose_before_restore", [False, True])
def test_restoring_exact_original_capacity_respects_committed_disposition(setup, protocol, dispose_before_restore):
    store, original = setup
    job = protocol_job(store, original, protocol)
    state = {**state_for(job, []), "notes": "Active notes", "pin_views": {}}
    runtime = offline(store)
    try:
        proposed = "Detailed continuity notes. " * 300
        changed, _ = accepted_batch(runtime, job, state, "settings",
            tool("context_update", {"notes": proposed}, "notes"))
        # No capacity/validity disposition has yet committed for this batch.
        assert not settlements(store, job)
        receipt = store.bytes("result:settings:0", job["id"])
        assert runtime.context.normal(job, {**changed, "notes": proposed})[1]["fits"]
        store.update_job(job["id"], route={**job["route"], "context_tokens": 4096, "output_tokens": 512})
        if dispose_before_restore:
            changed = coordinate(runtime, changed)
            assert settlements(store, job)[-1]["feedback"]["status"] == "needs_agent_revision"
        store.update_job(job["id"], route=job["route"])
        final = coordinate(runtime, changed)
        outcome = settlements(store, job)[-1]["feedback"]["status"]
        assert outcome == ("needs_agent_revision" if dispose_before_restore else "applied")
        assert final["notes"] == (state["notes"] if dispose_before_restore else proposed)
        assert store.bytes("result:settings:0", job["id"]) == receipt
        assert len(settlements(store, job)) == 1
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_unknown_image_allowance_is_not_confirmed_required_excess(setup, protocol):
    store, original = setup
    job = protocol_job(store, original, protocol)
    image = Evidence(store).render_page(job["id"], 1, dpi=72)
    job = store.update_job(job["id"], route={**job["route"], "image_tokens": None})
    runtime = offline(store)
    state = {**state_for(job, []), "pin_views": {}}
    try:
        changed, _ = accepted_batch(runtime, job, state, "unknown-image",
            tool("context_update", {"pin": [{"ref": image["image_ref"], "view": "image"}]}, "image"))
        result = store.json("result:unknown-image:0", job["id"])
        assert runtime.dispatcher.envelope(job["id"], "unknown-image:0", store.get("operation", "unknown-image:0"))["ok"]
        assert not result["admission"]["applied"]
        final = coordinate(runtime, changed)
        assert final["pinned"] == []
        records = settlements(store, job)
        assert all(r["feedback"].get("reason") != "required_content_exceeds_capacity" for r in records)
        if records:
            assert records[-1]["feedback"]["status"] == "needs_agent_revision"
            assert not final.get("context_waiting")
        else:
            assert final.get("context_waiting") and final.get("context_check")
            assert store.json(final["context_check"], job["id"])["reason"] == "capacity_configuration"
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_invalid_replacement_does_not_fall_back_to_earlier_pending_candidate(setup, protocol):
    store, original = setup
    job = protocol_job(store, original, protocol)
    runtime = offline(store)
    state = {**state_for(job, []), "notes": "Active notes", "pin_views": {}}
    try:
        pending, _ = accepted_batch(runtime, job, state, "older",
            tool("context_update", {"notes": "Earlier candidate, not current intent."}, "older"))
        oldref = pending["context_waiting"]
        oldbytes = store.bytes(oldref, job["id"])
        changed, _ = accepted_batch(runtime, job, pending, "replacement",
            tool("context_update", {"notes": None}, "invalid"))
        final = coordinate(runtime, changed)
        assert final["notes"] == state["notes"] and not final.get("context_waiting")
        assert settlements(store, job)[-1]["feedback"]["status"] == "needs_agent_revision"
        assert store.bytes(oldref, job["id"]) == oldbytes
        # Replaying the current decision or providing more space is not consent
        # to restore the older automatic candidate.
        store.update_job(job["id"], route={**job["route"], "context_tokens": 500000})
        again = coordinate(runtime, final)
        assert again["notes"] == state["notes"] and not again.get("context_waiting")
        assert not any(r["feedback"]["status"] == "applied" for r in settlements(store, job))
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("amended", [False, True])
def test_stop_after_saved_update_preserves_incomplete_batch_without_early_commit(setup, protocol, amended):
    store, original = setup
    job = protocol_job(store, original, protocol)
    dispatcher = Dispatcher(store)
    version = dispatcher.execute(job["id"], "draft", "edit_document", json.dumps({
        "base_version": None, "expected_head": None, "title": "Original",
        "replace_blocks": [{"id": "text", "pages": [1], "markdown": "Keep 25 mg."}],
        "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "partial"}))["data"]["version_id"]
    seen=[]
    def respond(request):
        payload=json.loads(request.content);seen.append(payload)
        if len(seen)==1:
            return httpx.Response(200,json=native(protocol,
                tool("context_update", {"notes": "Saved before Stop"}, "notes"),
                tool("edit_document", {"base_version": version, "expected_head": version, "title": "Old tool completed"}, "edit"),
                tool("report", {"state": "waiting", "message": "Original batch finished"}, "report")))
        assert amended and len(seen)==2
        assert "Do not change the saved document" in json.dumps(payload)
        assert "superseded" in json.dumps(payload)
        return httpx.Response(200,json=native(protocol,
            tool("report", {"state": "waiting", "message": "New instructions received"}, "new-report")))
    transport=httpx.MockTransport(respond)
    runtime=Runtime(store,Nexus(store,lambda _:"mock-only",transport))
    execute=runtime.dispatcher.execute
    def stop(*args):
        result=execute(*args)
        if args[2]=="context_update":store.update_job(job["id"],cancel_requested=True)
        return result
    runtime.dispatcher.execute=stop
    runtime.run(job["id"])
    initial=snapshot(runtime,job)
    assert initial.get("notes", "") == ""
    assert not settlements(store,job)
    first=store.records("request",job["id"])[0]
    frozen=store.bytes(first["payload_ref"],job["id"])
    raw=store.bytes(f"result:{first['id']}:0",job["id"])
    before=store.get("job",job["id"])
    assert before["stop_reason"]=="cancelled" and before["attempts"]==1
    runtime.close()
    store=Store(store.root)
    store.update_job(job["id"],cancel_requested=False,
        amendments=["Do not change the saved document. Ask for the next task."] if amended else [])
    runtime=Runtime(store,Nexus(store,lambda _:"mock-only",transport))
    try:
        runtime.run(job["id"])
        final=snapshot(runtime,job)
        assert final["notes"] == ("" if amended else "Saved before Stop")
        assert settlements(store,job)[-1]["feedback"]["status"] == ("superseded" if amended else "applied")
        current=store.get("job",job["id"])
        assert current["attempts"]==len(seen)==(2 if amended else 1)
        assert current["active_seconds"]>=before["active_seconds"]
        if amended:
            assert current["head"]==version
            assert store.json(f"result:{first['id']}:1",job["id"])["execution"]=="not_started"
        else:
            assert Documents(store).version(job["id"],current["head"])["content"]["title"]=="Old tool completed"
        assert store.bytes(first["payload_ref"],job["id"])==frozen
        assert store.bytes(f"result:{first['id']}:0",job["id"])==raw
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_explicit_reuse_repairs_selected_fields_and_rejects_stale_base(setup, protocol):
    store, original = setup
    job = protocol_job(store, original, protocol)
    y = store.blob(job["id"], "evidence", {"text": "Use the exact source: 25 mg."})["ref"]
    runtime = offline(store)
    state = {**state_for(job, []), "notes": "Old active notes", "pin_views": {}}
    try:
        saved, _ = accepted_batch(runtime, job, state, "bad-source",
            tool("context_update", {"notes": "Selected notes remain useful", "pin": [{"ref": "missing", "view": "image"}]}, "bad"))
        failed = coordinate(runtime, saved)
        assert settlements(store, job)[-1]["feedback"]["status"] == "needs_agent_revision"
        stale_base = policy_ref(failed)
        bad_source = store.get("operation", "bad-source:0")["candidate_ref"]
        original_bytes = store.bytes(bad_source, job["id"])
        fixed, _ = accepted_batch(runtime, job, failed, "repair",
            tool("context_update", {"base": {"kind": "active", "ref": stale_base},
                "reuse": [{"ref": bad_source, "fields": ["notes"]}],
                "pin": [{"ref": y, "view": "full", "json_pointer": "/text", "start": 0, "end": 10}]}, "fixed"))
        applied = coordinate(runtime, fixed)
        assert applied["notes"] == "Selected notes remain useful"
        assert applied["pinned"] == [y] and "missing" not in applied["pinned"]
        assert settlements(store, job)[-1]["feedback"]["status"] == "applied"
        assert store.bytes(bad_source, job["id"]) == original_bytes
        # Referencing an older base is an observable conflict. Do not silently
        # merge it into or replace the later valid context choice.
        conflicting, _ = accepted_batch(runtime, job, applied, "stale",
            tool("context_update", {"base": {"kind": "active", "ref": stale_base},
                "reuse": [{"ref": bad_source, "fields": ["notes"]}], "notes": "Would overwrite later choice"}, "stale"))
        final = coordinate(runtime, conflicting)
        assert all(final[k] == applied[k] for k in POLICY)
        assert settlements(store, job)[-1]["feedback"]["status"] == "needs_agent_revision"
        assert store.bytes(bad_source, job["id"]) == original_bytes
        assert store.json("result:stale:0", job["id"])["error"]
    finally:
        runtime.close()
