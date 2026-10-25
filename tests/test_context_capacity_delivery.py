"""Reopen each formerly rejected proposal and deliver the complete synthetic source."""
import base64
import json
from pathlib import Path

import httpx
import pymupdf
import pytest

from pdfmd.documents import Documents
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus
from pdfmd.runtime import Runtime
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher
from test_context_admission import outputs
from test_context_capacity_wait import pending_capacity_case
from test_context_retry import POLICY
from test_response_repairs import native
from test_runtime import tool
from test_stencil_pins import TEXT, fixture_job, verify_delivery, offline_runtime


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
    policy = runtime.context.waiting(job["id"], state)["policy"]
    frozen = store.get("request", "pending")
    frozen_bytes = store.bytes(frozen["payload_ref"], job["id"])
    config = {"configurable": {"thread_id": job["id"]}}
    runtime.graph.update_state(config, state, as_node="tools")
    runtime.close()
    low = 25000 if scenario == "release" else 19000
    before = store.update_job(job["id"], active_seconds=17,
        route={**job["route"], "context_tokens": low})
    for _ in range(2):
        store = Store(store.root)
        blocked = offline_runtime(store)
        blocked.run(job["id"])
        waiting = dict(blocked.graph.get_state(config).values)
        blocked.close()
        assert store.get("job", job["id"])["stop_reason"] == "capacity_blocked"
        assert store.get("job", job["id"])["attempts"] == before["attempts"] == 0
        assert waiting["context_waiting"] == pending_ref and all(waiting[k] == state[k] for k in POLICY)
        assert store.json(waiting["context_check"], job["id"])["reason"] == "capacity_blocked"
        assert Documents(store).version(job["id"], original_version)["content"]["blocks"] == [original_text]
        assert not any(b["kind"] == "context_settlement" for b in store.records("blob", job["id"]))
    seen, images = [], []
    def respond(request):
        payload = json.loads(request.content)
        seen.append(payload)
        assert payload.get("tools"), "Capacity repair should not require another compaction."
        if len(seen) == 1:
            assert '"status": "applied"' in json.dumps(payload).replace('\\"', '"')
            assert policy["notes"] in json.dumps(payload)
            calls = [tool("inspect_pdf", {"pages": [1], "mode": "text"}, "source"),
                     tool("extract_image", {"page": 1, "xref": mask, "occurrence": 0, "dpi": 144}, "red"),
                     tool("extract_image", {"page": 1, "xref": mask, "occurrence": 1, "dpi": 144}, "blue"),
                     tool("extract_image", {"page": 1, "xref": xref}, "cmyk")]
        elif len(seen) == 2:
            batch = outputs(payload)[-4:]
            assert batch[0]["data"]["value"]["pages"][0]["content"].strip() == TEXT
            images.extend(result["data"] for result in batch[1:])
            figures = [{"id": f"figure{i}", "pages": [1], "markdown": f"![{label}]({image['asset_path']})"}
                       for i, (label, image) in enumerate(zip(["red", "blue", "cmyk"], images))]
            calls = [tool("edit_document", {"base_version": original_version, "expected_head": original_version,
                "operations": [{"kind": "insert", "after_id": "text", "blocks": figures}], "claim": "complete"}, "finish")]
        else:
            assert len(seen) == 3
            calls = [tool("report", {"state": "complete", "version_id": store.get("job", job["id"])["head"],
                                     "message": "Complete source text and figures saved."}, "report")]
        return httpx.Response(200, json=native(protocol, *calls))

    store = Store(store.root)
    store.update_job(job["id"], route={**job["route"], "context_tokens": 500000})
    runtime = Runtime(store, Nexus(store, lambda _: "local-fixture-only", httpx.MockTransport(respond)))
    try:
        runtime.run(job["id"])
        final = dict(runtime.graph.get_state(config).values)
    finally:
        runtime.close()
    current = store.get("job", job["id"])
    assert current["status"] == "completed", current["last_message"]
    assert current["attempts"] == len(seen) == 3 and current["active_seconds"] >= 17
    assert not final["context_waiting"] and all(final[k] == policy[k] for k in POLICY)
    assert store.bytes(pending_ref, job["id"]) == pending_bytes
    assert store.bytes(frozen["payload_ref"], job["id"]) == frozen_bytes
    assert store.get("request", "pending")["route"]["context_tokens"] == 50000
    saved = Documents(store).version(job["id"], current["head"])
    assert saved["content"]["blocks"][0] == original_text
    assert Documents(store).version(job["id"], original_version)["content"]["blocks"] == [original_text]
    evidence = Evidence(store)
    assert evidence.read(job["id"], pending_ref)["value"]["context_proposal"]["policy"] == policy
    assert base64.b64decode(evidence.read(job["id"], pending_ref, view="raw")["data"]) == pending_bytes
    assert evidence.read(job["id"], pending_ref, json_pointer="/context_proposal/policy/notes", start=0, end=8)["value"] == policy["notes"][:8]
    fixture = {"job": job["id"], "version": current["head"], "original_version": original_version,
        "source": str(source), "protocol": protocol, "scenario": scenario, "attempts": current["attempts"],
        "active_seconds_before_reopen": 17, "active_seconds_after": current["active_seconds"],
        "pending_proposal_ref": pending_ref, "compactions": 0,
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
