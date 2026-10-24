"""Offline recovery checks. Scripted replies test mechanics, not model judgment."""
import json
import zipfile

import httpx
import pytest

from pdfmd.context import estimate
from pdfmd.documents import Documents
from pdfmd.nexus import Nexus
from pdfmd.runtime import Runtime
from pdfmd.schema import Route
from pdfmd.storage import Store
from test_context import history
from test_runtime import response, tool, transport_for


def native(protocol, *calls, text=None):
    if protocol == "chat_completions":
        return response(*calls, text=text)
    output = [{"type": "function_call", "call_id": c["id"], "name": c["function"]["name"],
               "arguments": c["function"]["arguments"], "status": "completed"} for c in calls]
    if text is not None:
        output.append({"type": "message", "role": "assistant", "status": "completed",
                       "content": [{"type": "output_text", "text": text}]})
    return {"status": "completed", "output": output}


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_text_only_recovers_to_complete_saved_reopened_exported_source(setup, tmp_path, protocol):
    store, job = setup
    route = {**job["route"], "protocol": protocol, "vision": True, "image_tokens": 1024,
             "endpoint": "http://127.0.0.1:8317/v1/" + ("responses" if protocol == "responses" else "chat/completions")}
    store.update_job(job["id"], route=route)
    seen, source_image = [], []
    expected = "A complete synthetic section.\nKeep every value: 25 mg.\n"

    def reply(request):
        payload = json.loads(request.content)
        seen.append(payload)
        messages = payload.get("messages", payload.get("input"))
        outputs = [json.loads(m.get("content", m.get("output"))) for m in messages
                   if m.get("role") == "tool" or m.get("type") == "function_call_output"]
        if len(seen) == 1:
            value = native(protocol, text="I will inspect the source next.")
        elif len(seen) == 2:
            assert "Application continuation feedback" in json.dumps(payload)
            value = native(protocol, tool("inspect_pdf", {"pages": [1], "mode": "text"}))
        elif len(seen) == 3:
            assert outputs[0]["data"]["value"]["pages"][0]["content"] == expected
            value = native(protocol, tool("render_page", {"page": 1, "dpi": 72}))
        elif len(seen) == 4:
            source_image.append(outputs[1]["data"])
            assert "data:image/png;base64," in json.dumps(payload)
            value = native(protocol, tool("edit_document", {"base_version": None, "expected_head": None,
                "replace_blocks": [{"id": "section", "pages": [1], "markdown": expected},
                                   {"id": "image", "pages": [1], "markdown": f"![Source page]({source_image[0]['asset_path']})"}],
                "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "complete"}))
        else:
            value = native(protocol, tool("report", {"state": "complete", "message": "Saved the complete source section.",
                                                     "version_id": store.get("job", job["id"])["head"]}))
        return httpx.Response(200, json=value)

    runtime = Runtime(store, Nexus(store, lambda _: "fixture", httpx.MockTransport(reply)))
    runtime.run(job["id"])
    runtime.close()
    current = store.get("job", job["id"])
    assert current["status"] == "completed" and current["attempts"] == len(seen) == 5
    assert len([e for e in store.events(job["id"]) if e["type"] == "response_correction"]) == 1
    reopened = Store(store.root)
    documents = Documents(reopened)
    saved = documents.version(job["id"], current["delivery"])
    assert saved["content"]["blocks"][0]["markdown"] == expected
    archive = tmp_path / "completed-section.zip"
    assert documents.export(job["id"], current["delivery"], str(archive))["verified"]
    with zipfile.ZipFile(archive) as output:
        assert expected in output.read("document.md").decode("utf-8")
        assert output.read(source_image[0]["asset_path"]) == store.bytes(source_image[0]["ref"], job["id"])
        assert "25 mg" in output.read("preview.html").decode("utf-8")
    assert len(seen) == 5  # Reopen and export do not run inference.


@pytest.mark.parametrize("limit", [0, 2])
def test_repair_limit_survives_resume_and_new_instruction_starts_new_episode(setup, limit):
    store, job = setup
    store.update_job(job["id"], limits={**job["limits"], "max_response_repairs": limit})
    calls = []
    def reply(request):
        calls.append(request)
        value = response(text="I will continue.") if not store.get("job", job["id"])["amendments"] else response(
            tool("report", {"state": "waiting", "message": "Please supply the missing scope decision."}))
        return httpx.Response(200, json=value)
    service = Nexus(store, lambda _: "fixture", httpx.MockTransport(reply))
    for _ in range(2):
        runtime = Runtime(store, service)
        runtime.run(job["id"])
        runtime.close()
    assert len(calls) == limit + 1
    assert store.get("job", job["id"])["stop_reason"] == "response_repair_exhausted"
    store.update_job(job["id"], amendments=["Ask me which section if the scope is ambiguous."])
    runtime = Runtime(store, service)
    runtime.run(job["id"])
    runtime.close()
    assert len(calls) == limit + 2
    assert store.get("job", job["id"])["status"] == "waiting"


@pytest.mark.parametrize("boundary", ["cancelled", "budget_exhausted"])
def test_repair_obeys_cancellation_and_original_budget(setup, boundary):
    store, job = setup
    if boundary == "budget_exhausted":
        store.update_job(job["id"], limits={**job["limits"], "max_requests": 1})
    calls = []
    def reply(request):
        calls.append(request)
        if boundary == "cancelled":
            store.update_job(job["id"], cancel_requested=True)
        return httpx.Response(200, json=response(text="I will read the source."))
    runtime = Runtime(store, Nexus(store, lambda _: "fixture", httpx.MockTransport(reply)))
    runtime.run(job["id"])
    runtime.close()
    assert len(calls) == 1 and store.get("job", job["id"])["attempts"] == 1
    assert store.get("job", job["id"])["stop_reason"] == boundary


def test_feedback_saved_before_checkpoint_replays_without_resend_or_duplicate_event(setup, monkeypatch):
    store, job = setup
    calls = []
    def reply(request):
        calls.append(request)
        return httpx.Response(200, json=response(text="Continue shortly.") if len(calls) == 1 else response(
            tool("report", {"state": "waiting", "message": "A source decision is needed."})))
    service = Nexus(store, lambda _: "fixture", httpx.MockTransport(reply))
    runtime = Runtime(store, service)
    original = runtime.repair
    def fault(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("after feedback before checkpoint")
    monkeypatch.setattr(runtime, "repair", fault)
    with pytest.raises(RuntimeError, match="before checkpoint"):
        runtime.run(job["id"])
    runtime.close()
    resumed = Runtime(store, service)
    resumed.run(job["id"])
    resumed.close()
    assert len(calls) == 2 and store.get("job", job["id"])["status"] == "waiting"
    assert len([e for e in store.events(job["id"]) if e["type"] == "response_correction"]) == 1
    assert len([b for b in store.records("blob", job["id"]) if b["kind"] == "response_repair"]) == 1


@pytest.mark.parametrize("intent,status", [("waiting", "waiting"), ("partial", "paused")])
def test_correction_can_formalize_question_or_partial_stop_without_more_conversion(setup, intent, status):
    store, job = setup
    calls = []
    def reply(request):
        payload = json.loads(request.content)
        calls.append(payload)
        if len(calls) == 1:
            value = response(text="Which section did you intend?" if intent == "waiting" else "I cannot complete this scope yet.")
        else:
            assert "No new user answer has arrived" in json.dumps(payload)
            value = response(tool("report", {"state": intent, "message": "Which section did you intend?" if intent == "waiting"
                                             else "The requested conversion is incomplete."}))
        return httpx.Response(200, json=value)
    runtime = Runtime(store, Nexus(store, lambda _: "fixture", httpx.MockTransport(reply)))
    runtime.run(job["id"])
    runtime.close()
    assert len(calls) == 2
    current = store.get("job", job["id"])
    assert current["status"] == status and current["stop_reason"] == "agent_report"
    assert current["head"] is None and current["content_claim"] == "partial"
    assert [op["tool"] for op in store.records("operation", job["id"])] == ["report"]


def seed_compaction(runtime, store, job):
    # The giant body can now be deferred before normal inference. Two individually
    # fitting results still create aggregate pressure and exercise real compaction.
    result, _ = history(store, job["id"], "large-history", "Retained evidence. " * 10000,
                        extra_texts=["Earlier extraction. " * 1500, "Later extraction. " * 1700])
    state = {"job": job["id"], "seq": 1, "revision": 1, "history": ["large-history"],
             "handoff": None, "notes": "Preserve all source values.", "released": [], "pinned": [], "repairs": {}, "terminal": False}
    runtime.graph.update_state({"configurable": {"thread_id": job["id"]}}, state, as_node="tools")
    return result


def handoff(job, **changes):
    return {"task": job["scope"], "current_state": "No output saved yet. Original evidence is retained.",
            "unfinished_work": ["Read and convert the source."], "dependencies": [],
            "references": [job["source_ref"]], "cautions": ["Do not infer fidelity from saved references."], **changes}


@pytest.mark.parametrize("failure", ["schema", "tools", "no_reduction"])
def test_handoff_correction_returns_to_conversion_and_preserves_originals(setup, failure):
    store, job = setup
    compactions, normal = [], []
    converter = transport_for(store, job["id"], normal)
    def reply(request):
        payload = json.loads(request.content)
        if payload.get("tools"):
            return converter.handle_request(request)
        compactions.append(payload)
        if len(compactions) == 1:
            value = response(tool("edit_document", {})) if failure == "tools" else response(text=(
                "```json\n{}\n```" if failure == "schema" else json.dumps(handoff(job, current_state="x" * 300000))))
        else:
            body = json.loads(payload["messages"][1]["content"])
            feedback = body["repair_feedback"]
            assert feedback["code"] == ("unexpected_tools" if failure == "tools" else "invalid_handoff")
            if failure == "no_reduction":
                assert not feedback["candidate_body_in_context"]
            assert estimate(payload, Route.model_validate(job["route"]))["fits"]
            value = response(text=json.dumps(handoff(job)))
        return httpx.Response(200, json=value)
    runtime = Runtime(store, Nexus(store, lambda _: "fixture", httpx.MockTransport(reply)))
    original = seed_compaction(runtime, store, job)
    runtime.run(job["id"])
    runtime.close()
    current = store.get("job", job["id"])
    assert current["status"] == "completed" and len(compactions) == 2 and len(normal) == 3
    assert current["attempts"] == 5
    assert store.json(original["ref"], job["id"])["value"] == "Retained evidence. " * 10000
    corrections = [b for b in store.records("blob", job["id"]) if b["kind"] == "response_repair"]
    failed = store.get("request", store.json(corrections[0]["ref"], job["id"])["request"])
    assert failed["status"] == "accepted" and failed["accepted_ref"]
    assert not any(op.get("id", "").startswith(failed["id"] + ":") for op in store.records("operation", job["id"]))
    assert len(store.records("version", job["id"])) == 1


def test_repeated_handoff_failures_stop_without_discarding_history(setup):
    store, job = setup
    calls = []
    service = Nexus(store, lambda _: "fixture", httpx.MockTransport(
        lambda request: calls.append(request) or httpx.Response(200, json=response(text="{}"))))
    runtime = Runtime(store, service)
    original = seed_compaction(runtime, store, job)
    runtime.run(job["id"])
    runtime.close()
    runtime = Runtime(store, service)
    runtime.run(job["id"])
    snapshot = runtime.graph.get_state({"configurable": {"thread_id": job["id"]}})
    runtime.close()
    assert len(calls) == 3
    assert store.get("job", job["id"])["stop_reason"] == "response_repair_exhausted"
    assert snapshot.values["history"] == ["large-history"] and snapshot.values["handoff"] is None
    assert store.bytes(original["ref"], job["id"])


def test_applied_handoff_before_checkpoint_has_stable_identity_and_one_event(setup, monkeypatch):
    store, job = setup
    compactions, normal = [], []
    converter = transport_for(store, job["id"], normal)
    def reply(request):
        if json.loads(request.content).get("tools"):
            return converter.handle_request(request)
        compactions.append(request)
        return httpx.Response(200, json=response(text=json.dumps(handoff(job))))
    service = Nexus(store, lambda _: "fixture", httpx.MockTransport(reply))
    runtime = Runtime(store, service)
    seed_compaction(runtime, store, job)
    original = runtime.context.apply_handoff
    def fault(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("after handoff before checkpoint")
    monkeypatch.setattr(runtime.context, "apply_handoff", fault)
    with pytest.raises(RuntimeError, match="before checkpoint"):
        runtime.run(job["id"])
    runtime.close()
    resumed = Runtime(store, service)
    resumed.run(job["id"])
    resumed.close()
    assert len(compactions) == 1 and len(normal) == 3
    assert store.get("job", job["id"])["status"] == "completed"
    assert len([e for e in store.events(job["id"]) if e["type"] == "context_compacted"]) == 1
    assert len([b for b in store.records("blob", job["id"]) if b["kind"] == "handoff"]) == 1
