"""Scripted native-protocol conversion with a durable deferred update and process reopen."""
import base64
import json
from pathlib import Path

import httpx
import pymupdf
import pytest

from pdfmd.documents import Documents
from pdfmd.context import Context
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus
from pdfmd.runtime import Runtime
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher
from test_context_admission import outputs, state_for
from test_context_progress import read_batch
from test_response_repairs import handoff, native
from test_runtime import tool
from test_stencil_pins import TEXT, fixture_job, verify_delivery, offline_runtime


def run_retry_delivery(directory, route, protocol):
    directory = Path(directory)
    store, job, source, mask, xref = fixture_job(directory, route, protocol)
    draft = Dispatcher(store).execute(job["id"], "draft", "edit_document", json.dumps({
        "base_version": None, "expected_head": None,
        "replace_blocks": [{"id": "text", "pages": [1], "markdown": TEXT + "\n"}],
        "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "partial"}))
    assert draft["ok"]
    job = store.update_job(job["id"], route={**job["route"], "context_tokens": 40000}, active_seconds=17)
    # This retained history is seeded, not inferred. Use the normal request
    # service's complete metadata so the desktop can inspect the whole task.
    payload, capacity = Context(store, Dispatcher(store)).normal(job, state_for(job, []))
    seed_request = Nexus(store, lambda _: pytest.fail("No seed inference")).freeze(
        job["id"], "history", payload, "normal", {"capacity": capacity})
    first, _ = read_batch(store, job, "history", ["A" * 11000])
    accepted_ref = store.get("request", "history")["accepted_ref"]
    store.put("request", "history", job["id"], {**seed_request, "status": "accepted", "accepted_ref": accepted_ref})
    second = store.blob(job["id"], "evidence", {"text": "B" * 11000})["ref"]
    original_version = job["head"]
    original_text = Documents(store).version(job["id"], original_version)["content"]["blocks"][0]
    seen, normal, summaries, retained = [], [], [], {}

    def respond(request):
        payload = json.loads(request.content)
        seen.append(payload)
        if not payload.get("tools"):
            summaries.append(payload)
            assert "pending_context_update" in json.dumps(payload)
            # Deliberately omit pending notes/pins: the app must retain their exact intent.
            answer = handoff(job, current_state="Saved draft retained; finish the source page.",
                             unfinished_work=[], references=[], cautions=[])
            return httpx.Response(200, json=native(protocol, text=json.dumps(answer)))
        normal.append(payload)
        results = outputs(payload)
        if len(normal) == 1:
            calls = [tool("read_evidence", {"ref": second}, "read"), tool("context_update", {
                "pin": [{"ref": first[0], "view": "index"}],
                "notes": "Retain exact source wording, 25 mg and all three source figures."}, "remember")]
        elif len(normal) == 2:
            assert '"status": "applied"' in json.dumps(payload).replace('\\"', '"')
            assert "Retain exact source wording, 25 mg and all three source figures." in json.dumps(payload)
            calls = [tool("inspect_pdf", {"pages": [1], "mode": "text"}, "source"),
                     tool("extract_image", {"page": 1, "xref": mask, "occurrence": 0, "dpi": 144}, "red"),
                     tool("extract_image", {"page": 1, "xref": mask, "occurrence": 1, "dpi": 144}, "blue"),
                     tool("extract_image", {"page": 1, "xref": xref}, "cmyk")]
        elif len(normal) == 3:
            batch = results[-4:]
            assert batch[0]["data"]["value"]["pages"][0]["content"].strip() == TEXT
            retained["images"] = [result["data"] for result in batch[1:]]
            figures = [{"id": f"figure{i}", "pages": [1], "markdown": f"![{label}]({image['asset_path']})"}
                       for i, (label, image) in enumerate(zip(["red", "blue", "cmyk"], retained["images"]))]
            calls = [tool("edit_document", {"base_version": original_version, "expected_head": original_version,
                "operations": [{"kind": "insert", "after_id": "text", "blocks": figures}], "claim": "complete"}, "finish")]
        else:
            assert len(normal) == 4
            calls = [tool("report", {"state": "complete", "version_id": store.get("job", job["id"])["head"],
                                     "message": "All source text and figures saved."}, "report")]
        return httpx.Response(200, json=native(protocol, *calls))

    runtime = Runtime(store, Nexus(store, lambda _: "local-fixture-only", httpx.MockTransport(respond)))
    config = {"configurable": {"thread_id": job["id"]}}
    runtime.graph.update_state(config, {**state_for(job, ["history"]), "pin_views": {}, "pending": None}, as_node="tools")
    wait = runtime.context_updates.wait
    def stop_after_queue(*args, **kwargs):
        result = wait(*args, **kwargs)
        if args[2] == "compaction":
            store.update_job(job["id"], cancel_requested=True)
        return result
    runtime.context_updates.wait = stop_after_queue
    runtime.run(job["id"])
    waiting = dict(runtime.graph.get_state(config).values)
    assert waiting["context_waiting"] and waiting["notes"] != "Retain exact source wording, 25 mg and all three source figures."
    pending_bytes = store.bytes(waiting["context_waiting"], job["id"])
    before = store.get("job", job["id"])
    assert before["attempts"] == 1 and before["active_seconds"] >= 17
    runtime.close()

    store = Store(store.root)
    store.update_job(job["id"], cancel_requested=False)
    blocked = offline_runtime(store)
    blocked_state = dict(blocked.graph.get_state(config).values)
    blocked.close()
    assert blocked_state["context_waiting"] == waiting["context_waiting"]
    check = store.json(blocked_state["context_check"], job["id"])
    assert check["reason"] == "compaction"
    assert store.get("job", job["id"])["route"] == job["route"]
    assert store.get("job", job["id"])["attempts"] == before["attempts"]
    assert Documents(store).version(job["id"], original_version)["content"]["blocks"] == [original_text]
    # Reopen at unchanged capacity. The existing proposal, not a model repeat,
    # must resume through admission and finish the same source-led artifact.
    store = Store(store.root)
    runtime = Runtime(store, Nexus(store, lambda _: "local-fixture-only", httpx.MockTransport(respond)))
    runtime.run(job["id"])
    final = dict(runtime.graph.get_state(config).values)
    runtime.close()
    current = store.get("job", job["id"])
    assert current["status"] == "completed", current["last_message"]
    assert current["attempts"] == len(seen) == len(summaries) + 4 and summaries
    assert current["active_seconds"] >= before["active_seconds"]
    assert final["context_waiting"] is None and final["pinned"] == first
    assert final["notes"] == "Retain exact source wording, 25 mg and all three source figures."
    assert store.bytes(waiting["context_waiting"], job["id"]) == pending_bytes
    saved = Documents(store).version(job["id"], current["head"])
    assert saved["content"]["blocks"][0] == original_text
    assert Documents(store).version(job["id"], original_version)["content"]["blocks"] == [original_text]
    evidence = Evidence(store)
    assert evidence.read(job["id"], first[0])["value"] == {"text": "A" * 11000}
    assert evidence.read(job["id"], first[0], json_pointer="/text", start=2, end=8)["value"] == "A" * 6
    assert base64.b64decode(evidence.read(job["id"], first[0], view="raw")["data"]) == store.bytes(first[0], job["id"])
    assert all(r["meta"]["capacity"]["fits"] for r in store.records("request", job["id"]) if "meta" in r)
    fixture = {"job": job["id"], "version": current["head"], "original_version": original_version,
        "source": str(source), "protocol": protocol, "attempts": current["attempts"],
        "active_seconds_before_reopen": before["active_seconds"], "active_seconds_after": current["active_seconds"],
        "pending_proposal_ref": waiting["context_waiting"], "compactions": len(summaries),
        "capacity_wait_ref": blocked_state["context_check"], "capacity_wait_reopened": True,
        "images": [{"label": label, "path": im["asset_path"], "width": im["width"], "height": im["height"], "provenance": im}
                   for label, im in zip(["red", "blue", "cmyk"], retained["images"])], "live_model_calls": 0}
    (directory / "fixture.json").write_text(json.dumps(fixture, indent=2), encoding="utf8")
    (directory / "payloads.json").write_text(json.dumps(seen, indent=2), encoding="utf8")
    with pymupdf.open(source) as pdf:
        pdf[0].get_pixmap(dpi=144).save(directory / "source-render.png")
    return fixture


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_deferred_update_survives_reopen_and_delivers_source(tmp_path, route, protocol):
    fixture = run_retry_delivery(tmp_path, route, protocol)
    docs = Documents(Store(tmp_path / "workspace"))
    assert docs.export(fixture["job"], fixture["version"], str(tmp_path / "delivery.zip"))["verified"]
    assert verify_delivery(tmp_path)["source_and_originals_preserved"]
