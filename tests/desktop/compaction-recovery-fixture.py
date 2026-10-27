"""Isolated desktop recovery fixture; no credentials or real model requests."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import zipfile

import httpx
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_response_repairs import seed_compaction
from pdfmd.documents import Documents
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus, make_payload
from pdfmd.runtime import Runtime
from pdfmd.schema import Route
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher


OPENING = "Keep 25 mg. Do not change this quantity."
CLOSING = "The final source sentence is preserved."


def fingerprint(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def catalog_records(store, job, kind):
    # Record identity belongs to the catalog; synthetic historical values may
    # omit it. Retain the raw stored JSON and row identity for exact comparison.
    with store.connect() as db:
        return {row["id"]: dict(row) for row in db.execute(
            "SELECT * FROM records WHERE kind=? AND job=? ORDER BY id", (kind, job))}


def prepare(directory, protocol, endpoint):
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / "Compaction recovery source.pdf"
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=420, height=300)
        page.insert_text((30, 40), OPENING, fontsize=12)
        page.insert_text((30, 65), CLOSING, fontsize=12)
        page.draw_rect((30, 95, 390, 260), color=(0.15, 0.4, 0.3), fill=(0.85, 0.95, 0.9))
        page.draw_circle((110, 170), 35, fill=(0.2, 0.6, 0.4))
        page.draw_line((160, 170), (300, 170), color=(0.15, 0.4, 0.3), width=3)
        pdf.save(source)
    store = Store(directory / "workspace")
    route = {"endpoint": endpoint, "protocol": protocol, "model": "local-compaction-recovery",
             "context_tokens": 65536, "output_tokens": 2048, "vision": True, "image_tokens": 1024,
             "timeout_seconds": 180}
    job = Evidence(store).create_job(str(source), "Convert the complete one-page synthetic source.", route,
        {"max_requests": 8, "max_active_seconds": 600, "replay_unknown": False, "max_attempts_per_request": 1})
    dispatcher = Dispatcher(store)
    image = dispatcher.evidence.render_page(job["id"], 1, 72)
    saved = dispatcher.execute(job["id"], "saved-before-interruption", "edit_document", json.dumps({
        "base_version": None, "expected_head": None,
        "replace_blocks": [{"id": "opening", "pages": [1], "markdown": OPENING},
                           {"id": "image", "pages": [1], "markdown": f"![Source figure]({image['asset_path']})"}],
        "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "partial"}))
    assert saved["ok"]
    version = saved["data"]["version_id"]
    store.update_job(job["id"], active_seconds=23.25)
    failures = []

    def unknown(request):
        payload = json.loads(request.content)
        assert not payload.get("tools"), "The seed must reach actual compaction."
        failures.append(payload)
        raise httpx.ReadTimeout("Offline interrupted compaction fixture.", request=request)

    runtime = Runtime(store, Nexus(store, lambda _: "fixture-only", httpx.MockTransport(unknown)))
    history_metadata = runtime.nexus.freeze(job["id"], "large-history", make_payload(
        Route.model_validate(job["route"]), "Synthetic retained-history fixture.", [], []), "normal", {})
    seed_compaction(runtime, store, job)
    runtime.graph.update_state({"configurable": {"thread_id": job["id"]}},
                               {"pinned": [image["ref"]]}, as_node="tools")
    # The shared unit helper stores minimal history. Give the real service a
    # complete, native-protocol historical record for its request inventory.
    historical = {**history_metadata, **store.get("request", "large-history", job=job["id"])}
    if protocol == "responses":
        accepted = store.json(historical["accepted_ref"], job["id"])
        accepted["native"] = [{"type": "function_call", "call_id": c["id"], "name": c["name"],
                               "arguments": c["arguments"], "status": "completed"} for c in accepted["calls"]]
        historical["accepted_ref"] = store.blob(job["id"], "accepted_response", accepted)["ref"]
    historical.update(id="large-history", job=job["id"], kind="normal", status="accepted", attempts=[],
                      route=store.get("job", job["id"])["route"], meta={},
                      replay_policy={"replay_unknown": False, "max_attempts_per_request": 1})
    store.put("request", "large-history", job["id"], historical)
    try:
        runtime.run(job["id"])
        snapshot = runtime.graph.get_state({"configurable": {"thread_id": job["id"]}})
        assert snapshot.next == ("compact",)
    finally:
        runtime.close()
    current = store.get("job", job["id"])
    assert current["stop_reason"] == "unknown_outcome" and current["attempts"] == len(failures) == 1
    request = next(r for r in store.records("request", job["id"]) if r["kind"] == "compaction")
    attempt = store.get("attempt", request["attempts"][0], job=job["id"])
    assert request["status"] == attempt["status"] == "unknown"
    value = {"job": job["id"], "version": version, "source": str(source), "protocol": protocol,
        "route": current["route"], "limits": current["limits"], "deadline_seconds": 600,
        "opening": OPENING, "closing": CLOSING,
        "source_ref": job["source_ref"], "source_sha256": fingerprint(source), "image": image,
        "unknown_request": request, "unknown_attempt": attempt,
        "frozen_payload_sha256": sha256(store.bytes(request["payload_ref"], job["id"])).hexdigest(),
        "attempts_before": current["attempts"], "active_seconds_before": current["active_seconds"],
        "unknown_stop_events_before": sum(e["type"] == "stopped" for e in store.events(job["id"])),
        "context_policy": {field: snapshot.values.get(field) for field in ("notes", "pinned", "pin_views", "released")},
        "original_requests": store.records("request", job["id"]),
        "original_operations": catalog_records(store, job["id"], "operation"),
        "prior_version_files": store.get("version", version, job=job["id"])["files"],
        "original_blobs": [{"ref": b["ref"], "sha256": b["sha256"]} for b in store.records("blob", job["id"])]}
    (directory / "fixture.json").write_text(json.dumps(value, indent=2), encoding="utf-8")
    # Safe fixture defaults, without a remembered credential. Electron supplies
    # a dummy key in memory when the test opens its connection dialog.
    (directory / "connection.json").write_text(json.dumps({"route": current["route"], "limits": current["limits"]}), encoding="utf-8")
    return value


def verify(directory):
    fixture = json.loads((directory / "fixture.json").read_text(encoding="utf-8"))
    store = Store(directory / "workspace")
    job_id = fixture["job"]
    job = store.get("job", job_id)
    original = fixture["unknown_request"]
    assert store.get("request", original["id"], job=job_id) == original
    assert store.get("attempt", fixture["unknown_attempt"]["id"], job=job_id) == fixture["unknown_attempt"]
    assert sha256(store.bytes(original["payload_ref"], job_id)).hexdigest() == fixture["frozen_payload_sha256"]
    assert original["route"]["timeout_seconds"] == fixture["unknown_attempt"]["transport"]["deadline_seconds"] == 180
    updated_route = {**fixture["route"], "timeout_seconds": fixture["deadline_seconds"]}
    assert job["limits"] == fixture["limits"] and job["route"] == updated_route
    settings = store.records("task_settings", job_id)
    assert len(settings) == 1
    assert settings[0]["before"] == {"route": fixture["route"], "limits": fixture["limits"]}
    assert settings[0]["after"] == {"route": updated_route, "limits": fixture["limits"]}
    connection = json.loads((directory / "connection.json").read_text(encoding="utf-8"))
    assert connection["route"] == fixture["route"] and connection["limits"] == fixture["limits"]
    assert job["attempts"] == fixture["attempts_before"] + 3
    assert job["active_seconds"] >= fixture["active_seconds_before"] and not job["amendments"]
    assert job["status"] == "completed"
    requests = [r for r in store.records("request", job_id) if r["kind"] == "compaction"]
    assert len(requests) == 2 and sum(r["status"] == "accepted" for r in requests) == 1
    original_ids = {request["id"] for request in fixture["original_requests"]}
    new_requests = [request for request in store.records("request", job_id) if request["id"] not in original_ids]
    assert len(new_requests) == 3
    for request in new_requests:
        assert request["route"] == updated_route and request["replay_policy"] == original["replay_policy"]
        assert request["status"] == "accepted" and len(request["attempts"]) == 1
        attempt = store.get("attempt", request["attempts"][0], job=job_id)
        assert attempt["transport"]["deadline_seconds"] == fixture["deadline_seconds"]
    for request in fixture["original_requests"]:
        assert store.get("request", request["id"], job=job_id) == request
    current_operations = catalog_records(store, job_id, "operation")
    for identity, operation in fixture["original_operations"].items():
        assert current_operations[identity] == operation
    receipt = store.json(f"continuation:{original['id']}", job_id)
    assert receipt["reason"] == "explicit_compaction_recovery"
    assert receipt["authorization"] == {"kind": "human_compaction_recovery", "request": original["id"]}
    assert receipt["payload_ref"] == original["payload_ref"] and receipt["attempts"] == original["attempts"]
    events = store.events(job_id, limit=10000)
    assert sum(e["type"] == "request_continued" for e in events) == 1
    for item in fixture["original_blobs"]:
        assert sha256(store.bytes(item["ref"], job_id)).hexdigest() == item["sha256"]
    assert store.bytes(fixture["source_ref"], job_id) == Path(fixture["source"]).read_bytes()
    runtime = Runtime(store, Nexus(store, lambda _: "unused-offline-fixture"))
    try:
        state = runtime.graph.get_state({"configurable": {"thread_id": job_id}}).values
        assert {field: state.get(field) for field in fixture["context_policy"]} == fixture["context_policy"]
    finally:
        runtime.close()
    documents = Documents(store)
    prior = documents.version(job_id, fixture["version"])
    for name, expected in fixture["prior_version_files"].items():
        assert fingerprint(documents.root / fixture["version"] / name) == expected
    saved = documents.version(job_id, job["delivery"])
    assert len(store.records("version", job_id)) == 2 and saved["content"]["claim"] == "complete"
    assert saved["content"]["blocks"][:2] == prior["content"]["blocks"]
    assert saved["content"]["blocks"][2]["markdown"] == CLOSING
    assert len(saved["assets"]) == 1
    with pymupdf.open(fixture["source"]) as pdf:
        rendered = pdf[0].get_pixmap(dpi=72)
        actual = pymupdf.Pixmap(store.bytes(fixture["image"]["ref"], job_id))
        assert rendered.samples == actual.samples
        with zipfile.ZipFile(directory / "delivery.zip") as archive:
            expected_files = store.get("version", job["delivery"], job=job_id)["files"]
            assert len(archive.namelist()) == len(expected_files) and set(archive.namelist()) == set(expected_files)
            for member in archive.namelist():
                assert archive.read(member) == (documents.root / job["delivery"] / member).read_bytes()
            markdown = archive.read("document.md").decode("utf-8")
            assert all(line in markdown for line in pdf[0].get_text().splitlines())
            assert archive.read(fixture["image"]["asset_path"]) == store.bytes(fixture["image"]["ref"], job_id)
            archive.extractall(directory / "exported")
    result = {"verified": True, "protocol": fixture["protocol"], "version": job["delivery"],
              "original_request_attempt_payload_unchanged": True, "originals_and_prior_version_preserved": True,
              "one_authorized_successor": True, "consumption_not_reset": True,
              "frozen_deadline_seconds": 180, "new_request_deadline_seconds": fixture["deadline_seconds"],
              "task_settings_receipt": settings[0], "connection_defaults_and_context_policy_preserved": True,
              "successor_request": next(request["id"] for request in new_requests if request["kind"] == "compaction"),
              "attempts": job["attempts"], "active_seconds": job["active_seconds"],
              "source_pixels_and_all_zip_bytes_equal": True, "assets": 1, "live_model_calls": 0}
    (directory / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    mode, directory = sys.argv[1], Path(sys.argv[2])
    result = prepare(directory, sys.argv[3], sys.argv[4]) if mode == "prepare" else verify(directory)
    print(json.dumps(result))
