"""Scripted exact-read/context-choice delivery, not real-model autonomy evidence."""
from copy import deepcopy
import base64
import json
from pathlib import Path
import zipfile

import httpx
import pymupdf
import pytest

from pdfmd.context import estimate
from pdfmd.documents import Documents
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus
from pdfmd.runtime import Runtime
from pdfmd.schema import Route
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher
from test_context_admission import outputs, protocol_job
from test_context_coordination import raw_receipts, snapshot
from test_response_repairs import native
from test_runtime import tool
from test_stencil_pins import TEXT, stencil_source, verify_delivery


def source_and_draft(directory, route, protocol):
    """All draft text comes from the generated PDF, not padding hidden from it."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / "Working evidence source.pdf"
    mask, xref = stencil_source(source)
    with pymupdf.open(source) as pdf:
        for section in range(1, 12):
            page = pdf.new_page()
            text = f"Section {section}: exact source text.\n" + "\n".join(
                f"Item {line}: retain this wording, 25 mg, and source order for section {section}."
                for line in range(1, 17))
            page.insert_text((40, 45), text, fontsize=11)
        pdf.saveIncr()
    store = Store(directory / "workspace")
    job = protocol_job(store, Evidence(store).create_job(str(source),
        "Convert all twelve pages, preserving all source text and figures.", route), protocol)
    with pymupdf.open(source) as pdf:
        blocks = [{"id": "text" if index == 0 else f"section{index}", "pages": [index + 1],
                   "markdown": page.get_text(), "source_note": ""} for index, page in enumerate(pdf)]
    result = Dispatcher(store).execute(job["id"], "draft", "edit_document", json.dumps({
        "base_version": None, "expected_head": None, "replace_blocks": blocks,
        "page_updates": {str(page): {"printed": "none", "disposition": "included"}
                         for page in range(1, 13)}, "claim": "partial",
        "known_gaps": ["Source figures have not yet been inserted."]}))
    assert result["ok"]
    return store, job, source, mask, xref, blocks, result["data"]["version_id"]


def feedback(payload):
    values = []
    for message in payload.get("messages", payload.get("input", [])):
        content = message.get("content")
        if isinstance(content, str) and content.startswith("Working context feedback:\n"):
            values.append(json.loads(content.split("\n", 1)[1]))
    assert len(values) == 1, "One current-view summary must describe the assembled input."
    return values[0]


def run_working_delivery(directory, route, protocol):
    directory = Path(directory)
    store, job, source, mask, xref, blocks, original_version = source_and_draft(directory, route, protocol)
    evidence = Evidence(store)
    images = [evidence.extract_image(job["id"], 1, mask, occurrence=0, dpi=144),
              evidence.extract_image(job["id"], 1, mask, occurrence=1, dpi=144),
              evidence.extract_image(job["id"], 1, xref)]
    source_bytes = source.read_bytes()
    image_bytes = {im["ref"]: store.bytes(im["ref"], job["id"]) for im in images}
    original_stream = store.bytes(images[-1]["original_ref"], job["id"])
    original_content = Documents(store).version(job["id"], original_version)
    store.update_job(job["id"], active_seconds=17)
    seen, retained, active_runtime = [], {}, []

    def respond(request):
        payload = json.loads(request.content)
        seen.append(payload)
        assert payload.get("tools"), "This exact-read exercise must not force compaction."
        summary = feedback(payload)
        computed = estimate(payload, Route.model_validate(job["route"]))
        assert computed["fits"]
        assert summary["input_estimate"] == computed["input_estimate"]
        assert summary["remaining"] == job["route"]["context_tokens"] - job["route"]["output_tokens"] - computed["input_estimate"]
        retained.setdefault("summaries", []).append(summary)
        current_outputs = outputs(payload)
        if len(seen) == 1:
            calls = [tool("read_document", {"version_id": original_version}, "full")]
        elif len(seen) == 2:
            full = current_outputs[-1]
            assert full["data"]["value"] == original_content
            assert full["data"]["completeness"] == {"root": True, "target": True, "selection": True}
            retained.update(full_result_ref=full["result_ref"], document_ref=full["data"]["ref"])
            calls = [tool("read_document", {"version_id": original_version, "view": "index"}, "index"),
                     tool("read_document", {"version_id": original_version, "json_pointer": "/content/blocks",
                                             "start": 11, "end": 12}, "selected")]
            calls += [tool("read_evidence", {"ref": im["ref"]}, f"image{i}") for i, im in enumerate(images)]
        elif len(seen) == 3:
            assert any(item["result_ref"] == retained["full_result_ref"] and item["data"].get("value") == original_content
                       for item in current_outputs), "A new smaller read must not remove old full content."
            index = next(item for item in current_outputs if item["data"].get("view") == "index")
            last = index["data"]["value"]["blocks"][-1]
            assert last["id"] == blocks[-1]["id"] and last["pointer"] == "/content/blocks/11"
            selection = next(item for item in current_outputs if item["data"].get("range") == [11, 12])
            assert selection["data"]["value"] == [blocks[-1]]
            assert selection["data"]["completeness"] == {"root": False, "target": False, "selection": True}
            retained["selection_result_ref"] = selection["result_ref"]
            assert summary["document_reads"]["full"] == 1
            assert summary["document_reads"]["selection"] == 1
            assert summary["document_reads"]["index"] == 1
            assert computed["images"] == 3
            calls = [tool("inspect_context", {"changes": {"release": [retained["full_result_ref"]]}}, "inspect"),
                     tool("context_update", {"release": [retained["full_result_ref"]]}, "choose")]
        elif len(seen) == 4:
            state = snapshot(active_runtime[0], job)
            assert retained["full_result_ref"] in state["released"]
            previous = next(item for item in current_outputs if item["result_ref"] == retained["full_result_ref"])
            assert previous.get("data", {}).get("value") is None, "Only explicit release changes the old representation."
            assert any(item["result_ref"] == retained["selection_result_ref"] and item["data"].get("value") == [blocks[-1]]
                       for item in current_outputs)
            assert computed["images"] == 3, "Releasing a document read must not release source images."
            assert summary["document_reads"]["full"] == 0
            assert summary["document_reads"]["selection"] == 1
            figures = [{"id": f"figure{i}", "pages": [1], "markdown": f"![{label}]({im['asset_path']})"}
                       for i, (label, im) in enumerate(zip(["red", "blue", "cmyk"], images))]
            calls = [tool("edit_document", {"base_version": original_version, "expected_head": original_version,
                "operations": [{"kind": "insert", "after_id": "text", "blocks": figures}],
                "claim": "complete", "known_gaps": []}, "save")]
        else:
            assert len(seen) == 5
            calls = [tool("report", {"state": "complete", "version_id": store.get("job", job["id"])["head"],
                                     "message": "All twelve source pages and figures are saved."}, "finish")]
        return httpx.Response(200, json=native(protocol, *calls))

    transport = httpx.MockTransport(respond)
    runtime = Runtime(store, Nexus(store, lambda _: "mock-only", transport))
    active_runtime[:] = [runtime]
    execute = runtime.dispatcher.execute

    def pause_after_inspection(*args, **kwargs):
        result = execute(*args, **kwargs)
        if args[2] == "inspect_context":
            assert result["ok"], result
            retained["inspection"] = deepcopy(result["data"])
            inspected = result["data"]
            assert inspected["policy_unchanged"] is True
            assert inspected["preview"]["applied"] is False
            assert inspected["preview"]["input_delta"] < 0
            assert inspected["snapshot_head"] == inspected["current_head"] == original_version
            assert inspected["inventory_complete"] and inspected["selection_complete"]
            assert any(item.get("result_ref") == retained["full_result_ref"] for item in inspected["inventory"])
            assert any(item.get("result_ref") == retained["selection_result_ref"] for item in inspected["inventory"])
            assert snapshot(runtime, job).get("released", []) == []
            assert Documents(store).version(job["id"], original_version) == original_content
            store.update_job(job["id"], cancel_requested=True)
        return result

    runtime.dispatcher.execute = pause_after_inspection
    runtime.run(job["id"])
    before = store.get("job", job["id"])
    state_before = snapshot(runtime, job)
    assert before["stop_reason"] == "cancelled" and before["attempts"] == len(seen) == 3
    assert state_before.get("released", []) == []
    pending = store.get("request", state_before["pending"], job=job["id"])
    assert pending["accepted_ref"]
    assert retained["inspection"]["snapshot_request"] == pending["id"]
    assert retained["inspection"]["snapshot_payload_ref"] == pending["payload_ref"]
    assert not any(item.get("call_id") in {"inspect", "choose"}
                   for item in retained["inspection"]["inventory"])
    frozen = deepcopy(pending)
    frozen_bytes = store.bytes(pending["payload_ref"], job["id"])
    receipts = raw_receipts(store, job)
    assert store.maybe("operation", pending["id"] + ":1") is None
    runtime.close()

    store = Store(store.root)
    store.update_job(job["id"], cancel_requested=False)
    runtime = Runtime(store, Nexus(store, lambda _: "mock-only", transport))
    active_runtime[:] = [runtime]
    runtime.run(job["id"])
    final_state = snapshot(runtime, job)
    runtime.close()
    current = store.get("job", job["id"])
    assert current["status"] == "completed", current["last_message"]
    assert current["attempts"] == len(seen) == 5
    assert current["active_seconds"] >= before["active_seconds"] >= 17
    assert current["route"] == job["route"]
    assert store.get("request", pending["id"], job=job["id"]) == frozen
    assert store.bytes(pending["payload_ref"], job["id"]) == frozen_bytes
    for ref, value in receipts.items():
        assert store.bytes(ref, job["id"]) == value
    assert final_state["released"] == [retained["full_result_ref"]]
    inspector_operations = [op for op in store.records("operation", job["id"]) if op["tool"] == "inspect_context"]
    assert len(inspector_operations) == 1
    assert Documents(store).version(job["id"], original_version) == original_content
    assert store.bytes(job["source_ref"], job["id"]) == source_bytes
    assert all(store.bytes(ref, job["id"]) == value for ref, value in image_bytes.items())
    evidence = Evidence(store)
    assert evidence.read(job["id"], retained["document_ref"])["value"] == original_content
    assert evidence.read(job["id"], retained["document_ref"], json_pointer="/content/blocks/11/markdown")["value"] == blocks[-1]["markdown"]
    assert base64.b64decode(evidence.read(job["id"], images[-1]["original_ref"], view="raw")["data"]) == original_stream
    assert base64.b64decode(evidence.read(job["id"], images[-1]["original_ref"], view="raw", start=4, end=18)["data"]) == original_stream[4:18]
    saved = Documents(store).version(job["id"], current["delivery"])
    assert [block for block in saved["content"]["blocks"] if not block["id"].startswith("figure")] == blocks
    assert saved["content"]["claim"] == "complete" and saved["content"]["known_gaps"] == []
    assert set(saved["content"]["pages"]) == {str(i) for i in range(1, 13)}
    fixture = {"job": job["id"], "version": current["delivery"], "original_version": original_version,
        "source": str(source), "protocol": protocol, "attempts": current["attempts"],
        "active_seconds_before_reopen": before["active_seconds"], "active_seconds_after": current["active_seconds"],
        "frozen_request": pending["id"], "full_result_ref": retained["full_result_ref"],
        "selection_result_ref": retained["selection_result_ref"], "inspection": retained["inspection"],
        "summaries": retained["summaries"], "text_blocks": blocks,
        "images": [{"label": label, "path": im["asset_path"], "width": im["width"], "height": im["height"], "provenance": im}
                   for label, im in zip(["red", "blue", "cmyk"], images)], "live_model_calls": 0}
    (directory / "fixture.json").write_text(json.dumps(fixture, indent=2), encoding="utf-8")
    (directory / "payloads.json").write_text(json.dumps(seen, indent=2), encoding="utf-8")
    with pymupdf.open(source) as pdf:
        pdf[0].get_pixmap(dpi=144).save(directory / "source-render.png")
    assert Documents(store).export(job["id"], current["delivery"], str(directory / "delivery.zip"))["verified"]
    assert verify_working_delivery(directory)["all_twelve_pages_preserved"]
    assert Documents(Store(store.root)).version(job["id"], current["delivery"]) == saved
    assert store.get("job", job["id"])["attempts"] == 5
    return fixture


def verify_working_delivery(directory):
    directory = Path(directory)
    result = verify_delivery(directory)
    fixture = json.loads((directory / "fixture.json").read_text(encoding="utf-8"))
    store = Store(directory / "workspace")
    docs = Documents(store)
    saved = docs.version(fixture["job"], fixture["version"])
    draft = docs.version(fixture["job"], fixture["original_version"])
    assert draft["content"]["blocks"] == fixture["text_blocks"]
    assert [block for block in saved["content"]["blocks"] if not block["id"].startswith("figure")] == draft["content"]["blocks"]
    with pymupdf.open(fixture["source"]) as pdf, zipfile.ZipFile(directory / "delivery.zip") as archive:
        markdown = archive.read("document.md").decode("utf-8")
        assert len(pdf) == 12
        for page, block in zip(pdf, fixture["text_blocks"]):
            assert page.get_text() == block["markdown"]
            assert block["markdown"].strip() in markdown
        assert json.loads(archive.read("document.json")) == saved
    result.update(all_twelve_pages_preserved=True, original_draft_unchanged=True)
    (directory / "working-verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_precise_read_old_full_preview_choice_reopen_and_delivery(tmp_path, route, protocol):
    run_working_delivery(tmp_path, {**route, "context_tokens": 131072}, protocol)
