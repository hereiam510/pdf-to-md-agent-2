"""A committed revision need requires explicit reselection after capacity repair."""
import base64
import json
from pathlib import Path

import httpx
import pymupdf
import pytest

from pdfmd.documents import Documents
from pdfmd.context_outcomes import policy_ref
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus
from pdfmd.runtime import Runtime
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher
from test_context_admission import outputs
from test_context_capacity_wait import pending_capacity_case
from test_context_retry import POLICY
from test_response_repairs import handoff, native
from test_runtime import tool
from test_stencil_pins import TEXT, fixture_job, verify_delivery, offline_runtime


def visible_image_metadata(payload):
    """Read only evidence actually included in this scripted model input."""
    found = {}
    def keep(value):
        if isinstance(value, dict) and "asset_path" in value:
            found[value["asset_path"]] = value
    def restored(handoff_value):
        for reference in (handoff_value or {}).get("content", {}).get("references", []):
            if reference.startswith('{"image_metadata":'):
                keep(json.loads(reference)["image_metadata"])
    if payload.get("tools"):
        groups = [payload]
        for message in payload.get("messages", payload.get("input", [])):
            content = message.get("content")
            if isinstance(content, str) and content.startswith("Continuation handoff:\n"):
                restored(json.loads(content.split("\n", 1)[1]))
    else:
        messages = payload.get("messages", payload.get("input", []))
        compact_input = json.loads(messages[-1]["content"])
        restored(compact_input.get("previous_handoff"))
        groups = compact_input["history"]
    for group in groups:
        for result in outputs(group):
            data = result.get("data", {})
            keep(data)
            if isinstance(data, dict):
                keep(data.get("value"))
    return list(found.values())


def run_capacity_delivery(directory, route, protocol, scenario):
    directory = Path(directory)
    store, job, source, mask, xref = fixture_job(directory, route, protocol)
    draft = Dispatcher(store).execute(job["id"], "draft", "edit_document", json.dumps({
        "base_version": None, "expected_head": None,
        "replace_blocks": [{"id": "text", "pages": [1], "markdown": TEXT + "\n"}],
        "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "partial"}))
    assert draft["ok"]
    runtime, job, state = pending_capacity_case(store, store.get("job", job["id"]), protocol, scenario)
    original_version = job["head"]
    original_text = Documents(store).version(job["id"], original_version)["content"]["blocks"][0]
    pending_ref = state["context_waiting"]
    pending_bytes = store.bytes(pending_ref, job["id"])
    raw_receipt = store.bytes("result:pending:1", job["id"])
    policy = runtime.context.waiting(job["id"], state)["policy"]
    frozen = store.get("request", "pending")
    frozen_bytes = store.bytes(frozen["payload_ref"], job["id"])
    config = {"configurable": {"thread_id": job["id"]}}
    runtime.graph.update_state(config, state, as_node="tools")
    runtime.close()
    low = 4096
    before = store.update_job(job["id"], active_seconds=17,
        route={**job["route"], "context_tokens": low})
    for _ in range(2):
        store = Store(store.root)
        blocked = offline_runtime(store)
        blocked.run(job["id"])
        waiting = dict(blocked.graph.get_state(config).values)
        blocked.close()
        assert store.get("job", job["id"])["stop_reason"] == "feedback_capacity_blocked"
        assert store.get("job", job["id"])["attempts"] == before["attempts"] == 0
        assert waiting["context_waiting"] is None and all(waiting[k] == state[k] for k in POLICY)
        assert store.json(waiting["context_feedback"], job["id"])["summary"]["status"] == "needs_agent_revision"
        assert store.get("context_disposition", pending_ref)["status"] == "needs_agent_revision"
        assert Documents(store).version(job["id"], original_version)["content"]["blocks"] == [original_text]
    seen, normal, summaries, images = [], [], [], []
    def respond(request):
        payload = json.loads(request.content)
        seen.append(payload)
        if not payload.get("tools"):
            summaries.append(payload)
            retained_metadata = visible_image_metadata(payload)
            return httpx.Response(200, json=native(protocol, text=json.dumps(handoff(job,
                current_state="Saved text and source images remain available; complete the source page.",
                unfinished_work=[], references=[json.dumps({"image_metadata": image}) for image in retained_metadata],
                cautions=[]))))
        normal.append(payload)
        if len(normal) == 1:
            assert '"status": "needs_agent_revision"' in json.dumps(payload).replace('\\"', '"')
            current_state = dict(runtime.graph.get_state(config).values)
            assert all(current_state[k] == state[k] for k in POLICY)
            calls = [tool("context_update", {
                "base": {"kind": "active", "ref": policy_ref(current_state)},
                "reuse": [{"ref": pending_ref, "operations": ["pending:1"]}]}, "reselect")]
        elif len(normal) == 2:
            assert '"status": "applied"' in json.dumps(payload).replace('\\"', '"')
            assert policy["notes"] in json.dumps(payload)
            calls = [tool("inspect_pdf", {"pages": [1], "mode": "text"}, "source"),
                     tool("extract_image", {"page": 1, "xref": mask, "occurrence": 0, "dpi": 144}, "red"),
                     tool("extract_image", {"page": 1, "xref": mask, "occurrence": 1, "dpi": 144}, "blue"),
                     tool("extract_image", {"page": 1, "xref": xref}, "cmyk")]
        elif len(normal) == 3:
            batch = outputs(payload)[-4:]
            assert batch[0]["data"]["value"]["pages"][0]["content"].strip() == TEXT
            # At the original allowance, source pixels may be explicitly
            # deferred. Select the saved full extraction metadata through the
            # advertised references; do not repair the fixture by raising capacity.
            calls = [tool("read_evidence", {"ref": result["result_ref"], "view": "full"}, f"image-metadata-{i}")
                     for i, result in enumerate(batch[1:])]
        elif len(normal) == 4:
            # The reads may now be in the model-authored handoff instead of the
            # native tool tail. Never assume an empty tail means no figures.
            images.extend(visible_image_metadata(payload))
            assert len(images) == 3, "All three source image records must reach the scripted converter."
            figures = [{"id": f"figure{i}", "pages": [1], "markdown": f"![{label}]({image['asset_path']})"}
                       for i, (label, image) in enumerate(zip(["red", "blue", "cmyk"], images))]
            calls = [tool("edit_document", {"base_version": original_version, "expected_head": original_version,
                "operations": [{"kind": "insert", "after_id": "text", "blocks": figures}], "claim": "complete"}, "finish")]
        else:
            assert len(normal) == 5
            calls = [tool("report", {"state": "complete", "version_id": store.get("job", job["id"])["head"],
                                     "message": "Complete source text and figures saved."}, "report")]
        return httpx.Response(200, json=native(protocol, *calls))

    store = Store(store.root)
    store.update_job(job["id"], route=job["route"])
    runtime = Runtime(store, Nexus(store, lambda _: "local-fixture-only", httpx.MockTransport(respond)))
    try:
        runtime.run(job["id"])
        final = dict(runtime.graph.get_state(config).values)
    finally:
        runtime.close()
    current = store.get("job", job["id"])
    assert current["status"] == "completed", current["last_message"]
    assert current["attempts"] == len(seen) == 5 + len(summaries) and current["active_seconds"] >= 17
    assert not final["context_waiting"] and all(final[k] == policy[k] for k in POLICY)
    assert store.bytes(pending_ref, job["id"]) == pending_bytes
    assert store.bytes("result:pending:1", job["id"]) == raw_receipt
    assert store.get("context_disposition", pending_ref)["status"] == "needs_agent_revision"
    assert store.bytes(frozen["payload_ref"], job["id"]) == frozen_bytes
    assert store.get("request", "pending")["route"]["context_tokens"] == 50000
    saved = Documents(store).version(job["id"], current["head"])
    assert len(images) == 3 and len(saved["assets"]) == 3
    assert saved["content"]["blocks"][0] == original_text
    assert Documents(store).version(job["id"], original_version)["content"]["blocks"] == [original_text]
    evidence = Evidence(store)
    assert evidence.read(job["id"], pending_ref)["value"]["context_proposal"]["policy"] == policy
    assert base64.b64decode(evidence.read(job["id"], pending_ref, view="raw")["data"]) == pending_bytes
    assert evidence.read(job["id"], pending_ref, json_pointer="/context_proposal/policy/notes", start=0, end=8)["value"] == policy["notes"][:8]
    fixture = {"job": job["id"], "version": current["head"], "original_version": original_version,
        "source": str(source), "protocol": protocol, "scenario": scenario, "attempts": current["attempts"],
        "active_seconds_before_reopen": 17, "active_seconds_after": current["active_seconds"],
        "pending_proposal_ref": pending_ref, "compactions": len(summaries),
        "old_proposal_status": "needs_agent_revision", "explicit_reselection": True,
        "restored_capacity": job["route"]["context_tokens"],
        "capacity_wait_ref": waiting["context_check"], "capacity_wait_reopened": True, "blocked_capacity": low,
        "frozen_request": "pending", "frozen_route_capacity": 50000,
        "images": [{"label": label, "path": im["asset_path"], "width": im["width"], "height": im["height"], "provenance": im}
                   for label, im in zip(["red", "blue", "cmyk"], images)], "live_model_calls": 0}
    (directory / "fixture.json").write_text(json.dumps(fixture, indent=2), encoding="utf8")
    (directory / "payloads.json").write_text(json.dumps(seen, indent=2), encoding="utf8")
    with pymupdf.open(source) as pdf:
        pdf[0].get_pixmap(dpi=144).save(directory / "source-render.png")
    return fixture


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("scenario", ["release", "handoff"])
def test_capacity_repair_reopens_and_delivers_source(tmp_path, route, protocol, scenario):
    fixture = run_capacity_delivery(tmp_path, route, protocol, scenario)
    docs = Documents(Store(tmp_path / "workspace"))
    assert docs.export(fixture["job"], fixture["version"], str(tmp_path / "delivery.zip"))["verified"]
    assert verify_delivery(tmp_path)["source_and_originals_preserved"]
