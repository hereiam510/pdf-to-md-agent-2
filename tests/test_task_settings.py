"""Offline Phase 2 regressions. No live model calls or model-quality claims."""
import json
import base64
from hashlib import sha256
import time
import zipfile

import httpx
import pymupdf
import pytest
from fastapi.testclient import TestClient
from filelock import FileLock

from pdfmd.documents import Documents
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus, StopRun, instruction_basis
from pdfmd.runtime import Runtime
from pdfmd.server import Engine, create_app
from pdfmd.storage import Conflict, Store
from pdfmd.tools import Dispatcher
from test_context_admission import image_source, outputs, protocol_job
from test_response_repairs import native
from test_runtime import tool


def start(engine, job, **settings):
    engine.start(job, "fixture-only", **settings)
    engine.futures[job].result(timeout=30)
    return engine.store.get("job", job)


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_capacity_can_change_before_first_request(setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    store.update_job(job["id"], route={**job["route"], "context_tokens": 2048, "output_tokens": 256})
    seen = []
    def reply(request):
        seen.append(request.content)
        return httpx.Response(200, json=native(protocol, tool("report", {"state": "waiting", "message": "Ready."})))
    engine = Engine(store.root, transport=httpx.MockTransport(reply))
    try:
        assert start(engine, job["id"])["stop_reason"] == "necessary_estimate_uncertain"
        assert not seen and not store.records("request", job["id"])
        current = start(engine, job["id"], route=job["route"])
        assert current["status"] == "waiting" and current["attempts"] == len(seen) == 1
        assert current["route"] == job["route"]
    finally:
        engine.close()


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_allowance_change_retains_consumption_and_frozen_input(setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    store.update_job(job["id"], limits={**job["limits"], "max_requests": 1}, active_seconds=17)
    seen = []
    def reply(request):
        seen.append(request.content)
        response = (native(protocol, text="I will continue with the saved evidence.") if len(seen) == 1 else
                    native(protocol, tool("report", {"state": "waiting", "message": "Preserved."})))
        return httpx.Response(200, json=response)
    engine = Engine(store.root, transport=httpx.MockTransport(reply))
    try:
        stopped = start(engine, job["id"])
        assert stopped["stop_reason"] == "budget_exhausted" and len(seen) == 1
        frozen = store.records("request", job["id"])[-1]
        original = store.bytes(frozen["payload_ref"], job["id"])
        current = start(engine, job["id"], limits={**job["limits"], "max_requests": 5})
        assert current["status"] == "waiting" and current["attempts"] == len(seen) == 2
        assert current["active_seconds"] >= stopped["active_seconds"] >= 17
        assert store.bytes(frozen["payload_ref"], job["id"]) == original == seen[-1]
        assert store.get("request", frozen["id"])["route"] == frozen["route"]
    finally:
        engine.close()


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("allow_replay", [False, True])
def test_frozen_replay_policy_does_not_follow_later_task_values(setup, protocol, allow_replay):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    job = store.update_job(job["id"], limits={**job["limits"], "replay_unknown": allow_replay,
                                            "max_attempts_per_request": 2 if allow_replay else 1})
    sent = []
    def unknown(request):
        sent.append(request.content)
        raise httpx.ReadError("offline unknown outcome")
    nexus = Nexus(store, lambda _: "fixture", httpx.MockTransport(unknown))
    frozen = nexus.freeze(job["id"], "frozen", {"original": "input"}, "normal", {})
    with pytest.raises(StopRun):
        nexus.send(job["id"], frozen["id"])
    store.update_job(job["id"], limits={**job["limits"], "max_requests": 100,
                                       "replay_unknown": True, "max_attempts_per_request": 3})
    if allow_replay:
        with pytest.raises(StopRun):
            nexus.send(job["id"], frozen["id"])
    with pytest.raises(StopRun) as stopped:
        nexus.send(job["id"], frozen["id"])
    assert stopped.value.reason == "unknown_outcome"
    assert len(sent) == (2 if allow_replay else 1)
    assert store.get("job", job["id"])["attempts"] == len(sent)


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("kind", ["normal", "compaction"])
def test_deadline_change_is_only_used_by_newly_frozen_requests(setup, protocol, kind):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    job = store.update_job(job["id"], active_seconds=17, amendments=["Preserve the source units."])
    sent = []

    def reply(request):
        sent.append({"payload": request.content, "timeout": request.extensions["timeout"]})
        if len(sent) == 1:
            raise httpx.ReadError("offline unknown outcome")
        return httpx.Response(200, json=native(protocol, text="Retained reply."))

    nexus = Nexus(store, lambda _: "fixture-only", httpx.MockTransport(reply))
    prepared = nexus.freeze(job["id"], "old-prepared", {"original": "unsent"}, kind, {"basis": "retained"})
    unknown = nexus.freeze(job["id"], "old-unknown", {"original": "unknown"}, kind, {"basis": "retained"})
    with pytest.raises(StopRun):
        nexus.send(job["id"], unknown["id"])
    unknown = store.get("request", unknown["id"])
    before = store.get("job", job["id"])
    old_payloads = {request["id"]: store.bytes(request["payload_ref"], job["id"])
                    for request in [prepared, unknown]}
    engine = Engine(store.root)
    try:
        updated = engine.configure(job["id"], route={"timeout_seconds": 600})
        assert updated == {**before, "route": {**before["route"], "timeout_seconds": 600}}
        assert instruction_basis(updated) == instruction_basis(before)
        assert len(sent) == 1 and updated["attempts"] == 1 and updated["active_seconds"] == 17
        changes = store.records("task_settings", job["id"])
        assert len(changes) == 1
        assert changes[0]["before"] == {"route": before["route"], "limits": before["limits"]}
        assert changes[0]["after"] == {"route": updated["route"], "limits": before["limits"]}
        # Omitted settings and re-entry retain the explicit task value and every old request.
        assert engine.configure(job["id"]) == updated
        assert store.records("task_settings", job["id"]) == changes
        for request in [prepared, unknown]:
            assert store.get("request", request["id"]) == request
            assert store.bytes(request["payload_ref"], job["id"]) == old_payloads[request["id"]]
            assert nexus.freeze(job["id"], request["id"], {"replacement": "must not apply"}, kind, {}) == request
        # A new deadline does not reopen the unknown request's exhausted replay gate.
        with pytest.raises(StopRun) as stopped:
            nexus.send(job["id"], unknown["id"])
        assert stopped.value.reason == "unknown_outcome" and len(sent) == 1
        assert store.get("request", unknown["id"]) == unknown
        nexus.send(job["id"], prepared["id"])
        assert sent[-1]["payload"] == old_payloads[prepared["id"]]
        assert sent[-1]["timeout"]["read"] == prepared["route"]["timeout_seconds"] == 180
        newly_frozen = nexus.freeze(job["id"], "new-request", {"new": "input"}, kind, {})
        assert newly_frozen["route"] == updated["route"]
        assert newly_frozen["instruction_basis"] == prepared["instruction_basis"]
        assert newly_frozen["replay_policy"] == prepared["replay_policy"]
        nexus.send(job["id"], newly_frozen["id"])
        assert sent[-1]["timeout"]["read"] == 600
        assert sent[-1]["timeout"]["connect"] == 30
        assert store.get("job", job["id"])["attempts"] == len(sent) == 3
        assert store.get("job", job["id"])["active_seconds"] == 17
    finally:
        engine.close()


def test_stale_active_interval_is_unknown_not_ten_thousand_seconds_of_work(setup, monkeypatch):
    store, job = setup
    import time
    store.update_job(job["id"], active_seconds=17, active_since=time.time() - 10000)
    runtime = Runtime(store, Nexus(store, lambda _: "fixture", httpx.MockTransport(lambda _: pytest.fail("No send"))))
    monkeypatch.setattr(runtime.graph, "invoke", lambda *args, **kwargs: None)
    try:
        runtime.run(job["id"])
        current = store.get("job", job["id"])
        assert 17 <= current["active_seconds"] < 60
        gaps = store.records("active_time_gap", job["id"])
        assert len(gaps) == 1 and gaps[0]["active_seconds"] is None
        assert gaps[0]["wall_span_seconds"] >= 10000
        runtime.run(job["id"])
        assert store.records("active_time_gap", job["id"]) == gaps
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_settings_are_atomic_and_do_not_relax_recovery_or_protocol(setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    nexus = Nexus(store, lambda _: "fixture")
    frozen = nexus.freeze(job["id"], "frozen", {}, "normal", {})
    engine = Engine(store.root)
    try:
        for route, limits in [({"protocol": "responses" if protocol == "chat_completions" else "chat_completions",
                                "endpoint": "http://127.0.0.1/v1/" + ("responses" if protocol == "chat_completions" else "chat/completions")}, {}),
                              ({"endpoint": job["route"]["endpoint"].replace(":8317", ":8318")}, {}),
                              ({"model": "another-model"}, {}), ({"vision": False}, {}),
                              ({"parameters": {"temperature": 0.4}}, {}),
                              ({"context_tokens": 131072}, {"max_requests": 90, "replay_unknown": True}),
                              ({}, {"max_attempts_per_request": 3}), ({}, {"max_response_repairs": 9})]:
            with pytest.raises(Conflict):
                engine.configure(job["id"], route={"timeout_seconds": 600, **route}, limits=limits)
            assert store.get("job", job["id"]) == job
            assert not store.records("task_settings", job["id"])
            assert store.get("request", "frozen") == frozen
        for invalid_deadline in [0, 3600.01, None, "invalid"]:
            with pytest.raises(ValueError):
                engine.configure(job["id"], route={"timeout_seconds": invalid_deadline, "context_tokens": 131072},
                                 limits={"max_requests": 90})
            assert store.get("job", job["id"]) == job
            assert not store.records("task_settings", job["id"])
            assert store.get("request", "frozen") == frozen
        with pytest.raises(ValueError):
            engine.configure(job["id"], route={"output_tokens": 131072})
        with FileLock(str(store.root / f"task-{job['id']}.lock")):
            with pytest.raises(Conflict, match="Stop the task"):
                engine.configure(job["id"], route={"timeout_seconds": 600}, limits={"max_requests": 90})
        updated = engine.configure(job["id"], route={"context_tokens": 131072, "timeout_seconds": 600}, limits={"max_requests": 90})
        assert updated["attempts"] == 0 and updated["active_seconds"] == 0
        assert updated["route"]["timeout_seconds"] == 600
        assert store.get("request", "frozen") == frozen
        assert len(store.records("task_settings", job["id"])) == 1
    finally:
        engine.close()


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_deadline_and_total_allowance_do_not_reopen_same_correction_episode(setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    store.update_job(job["id"], limits={**job["limits"], "max_response_repairs": 0})
    seen = []
    def reply(request):
        seen.append(request.content)
        return httpx.Response(200, json=native(protocol, text="Still planning."))
    engine = Engine(store.root, transport=httpx.MockTransport(reply))
    try:
        assert start(engine, job["id"])["stop_reason"] == "response_repair_exhausted"
        engine.configure(job["id"], route={"timeout_seconds": 600}, limits={"max_requests": 100, "max_active_seconds": 9000})
        assert start(engine, job["id"])["stop_reason"] == "response_repair_exhausted"
        assert len(seen) == 1
        # A meaningful instruction remains an existing supported episode boundary.
        assert start(engine, job["id"], amendment="Use exact source references.")["stop_reason"] == "response_repair_exhausted"
        assert len(seen) == 2
    finally:
        engine.close()


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_settings_do_not_bypass_unknown_local_effect(setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    sent = []
    def reply(request):
        sent.append(request.content)
        return httpx.Response(200, json=native(protocol, tool("run_script", {"code": "pass"})))
    runtime = Runtime(store, Nexus(store, lambda _: "fixture", httpx.MockTransport(reply)))
    # Freeze a genuine accepted response, then retain a started, unsettled script.
    state = {"job": job["id"], "seq": 0, "revision": 0, "history": [], "handoff": None,
             "notes": "", "released": [], "pinned": []}
    prepared = runtime.prepare(state)
    runtime.nexus.send(job["id"], prepared["pending"])
    call = {"job": job["id"], "tool": "run_script", "arguments": json.dumps({"code": "pass"}),
            "status": "started", "result_ref": None}
    # Retain the exact candidate and started marker, without executing a script.
    operation = prepared["pending"] + ":0"
    digest, candidate = runtime.dispatcher.capture(job["id"], operation, "run_script", call["arguments"])
    store.put("operation", operation, job["id"], {"id": operation, "tool": "run_script", "status": "started",
                                                "args_hash": digest, "candidate_ref": candidate["ref"]})
    runtime.close()
    engine = Engine(store.root, transport=httpx.MockTransport(reply))
    try:
        engine.configure(job["id"], route={"timeout_seconds": 600}, limits={"max_requests": 100})
        current = start(engine, job["id"])
        assert current["stop_reason"] == "local_outcome_unknown" and len(sent) == 1
    finally:
        engine.close()


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("boundary", ["capacity", "requests", "time"])
def test_settings_continue_to_saved_reopened_exported_source(tmp_path, route, protocol, boundary):
    source = tmp_path / "Settings source.pdf"
    source_pixels = image_source(source)
    with pymupdf.open(source) as pdf:
        source_text = pdf[0].get_text()
        image_xref = pdf[0].get_images()[0][0]
        pdf[0].get_pixmap().save(tmp_path / "source-page.png")
    seen = []
    def reply(request):
        payload = json.loads(request.content)
        seen.append(payload)
        if len(seen) == 1:
            value = tool("inspect_pdf", {"pages": [1], "mode": "text"}, "read")
        elif len(seen) == 2:
            text = outputs(payload)[-1]["data"]["value"]["pages"][0]["content"]
            assert text == source_text
            value = tool("edit_document", {"base_version": original_version, "expected_head": original_version,
                "operations": [{"kind": "replace", "id": "text", "blocks": [{"id": "text", "pages": [1], "markdown": text}]}],
                "page_updates": {"1": {"printed": "unknown", "disposition": "included"}}, "claim": "complete"}, "save")
        else:
            value = tool("report", {"state": "complete", "version_id": outputs(payload)[-1]["data"]["version_id"],
                                    "message": "All source text and the original image are saved."}, "done")
        return httpx.Response(200, json=native(protocol, value))
    transport = httpx.MockTransport(reply)
    workspace = tmp_path / "workspace"
    app = create_app(workspace, "local-fixture", transport=transport)
    store = app.state.engine.store
    job = app.state.engine.evidence.create_job(str(source), "Convert the complete page and preserve the image.", route)
    job = protocol_job(store, job, protocol)
    dispatcher = Dispatcher(store)
    image = dispatcher.evidence.extract_image(job["id"], 1, image_xref)
    seed = dispatcher.execute(job["id"], "seed", "edit_document", json.dumps({"base_version": None, "expected_head": None,
        "replace_blocks": [{"id": "text", "pages": [1], "markdown": "Useful partial draft."},
                           {"id": "figure", "pages": [1], "markdown": f"![Source figure]({image['asset_path']})"}],
        "page_updates": {"1": {"printed": "unknown", "disposition": "included"}}, "claim": "partial"}))
    assert seed["ok"]
    original_version = seed["data"]["version_id"]
    limits = {**job["limits"], "max_requests": 1 if boundary == "requests" else 80,
              "max_active_seconds": 1 if boundary == "time" else 7200}
    route = {**job["route"], **({"context_tokens": 2048, "output_tokens": 256} if boundary == "capacity" else {})}
    store.update_job(job["id"], route=route, limits=limits, active_seconds=17)
    headers = {"Authorization": "Bearer local-fixture"}
    with TestClient(app, headers=headers) as client:
        assert client.post(f"/jobs/{job['id']}/start", json={"key": "fixture-only"}).status_code == 200
        app.state.engine.futures[job["id"]].result(timeout=30)
        stopped = client.get(f"/jobs/{job['id']}").json()
        assert stopped["stop_reason"] == ("necessary_estimate_uncertain" if boundary == "capacity" else "budget_exhausted")
        assert stopped["head"] == original_version
        originals = {b["ref"]: sha256(store.bytes(b["ref"], job["id"])).hexdigest() for b in store.records("blob", job["id"])}
        frozen = store.records("request", job["id"])
        configured = client.post(f"/jobs/{job['id']}/settings", json={
            "route": {"context_tokens": 131072, "output_tokens": 3072, "timeout_seconds": 600},
            "limits": {"max_requests": 10, "max_active_seconds": 1800}})
        assert configured.status_code == 200
        changed = configured.json()
        assert changed["attempts"] == stopped["attempts"] and changed["active_seconds"] == stopped["active_seconds"]
        assert store.records("request", job["id"]) == frozen
        if boundary == "time":
            store.update_job(job["id"], active_since=time.time() - 10000, active_session="interrupted-fixture")
    # Reopen the engine/API before Continue. Task settings, source and draft are durable.
    app = create_app(workspace, "local-fixture", transport=transport)
    with TestClient(app, headers=headers) as client:
        loaded = client.get(f"/jobs/{job['id']}").json()
        assert loaded["route"]["context_tokens"] == 131072 and loaded["limits"]["max_requests"] == 10
        assert loaded["route"]["timeout_seconds"] == 600
        assert client.post(f"/jobs/{job['id']}/start", json={"key": "fixture-only"}).status_code == 200
        app.state.engine.futures[job["id"]].result(timeout=30)
        current = client.get(f"/jobs/{job['id']}").json()
        assert current["status"] == "completed" and current["attempts"] == len(seen) == 3
        assert stopped["active_seconds"] <= current["active_seconds"] < 100
        assert len(current["active_time_gaps"]) == (1 if boundary == "time" else 0)
    store = Store(workspace)
    documents = Documents(store)
    saved = documents.version(job["id"], current["delivery"])
    assert saved["parent"] == original_version and saved["content"]["claim"] == "complete"
    assert saved["content"]["blocks"][0]["markdown"] == source_text
    assert saved["content"]["blocks"][1] == documents.version(job["id"], original_version)["content"]["blocks"][1]
    image_bytes = store.bytes(image["ref"], job["id"])
    assert pymupdf.Pixmap(image_bytes).samples == source_pixels
    assert store.bytes(job["source_ref"], job["id"]) == source.read_bytes()
    for ref, digest in originals.items():
        assert sha256(store.bytes(ref, job["id"])).hexdigest() == digest
    for old in frozen:
        recovered = store.get("request", old["id"])
        for field in ["id", "payload_ref", "route", "meta", "replay_policy"]:
            assert recovered[field] == old[field]
    new_requests = [request for request in store.records("request", job["id"])
                    if request["id"] not in {old["id"] for old in frozen}]
    assert new_requests and all(request["route"]["timeout_seconds"] == 600 for request in new_requests)
    evidence = Evidence(store)
    text_ref = evidence.inspect(job["id"], [1], "text")["ref"]
    assert evidence.read(job["id"], text_ref)["complete"]
    assert base64.b64decode(evidence.read(job["id"], text_ref, view="raw")["data"]) == store.bytes(text_ref, job["id"])
    assert evidence.read(job["id"], text_ref, json_pointer="/pages/0/content", start=0, end=16)["value"] == source_text[:16]
    archive = tmp_path / "delivery.zip"
    assert documents.export(job["id"], current["delivery"], str(archive))["verified"]
    with zipfile.ZipFile(archive) as zipped:
        for name in zipped.namelist():
            assert zipped.read(name) == (documents.root / current["delivery"] / name).read_bytes()
        assert source_text in zipped.read("document.md").decode()
        assert zipped.read(image["asset_path"]) == image_bytes
        zipped.extractall(tmp_path / "exported")
    (tmp_path / "fixture-payloads.json").write_text(json.dumps(seen, indent=2), encoding="utf-8")
    (tmp_path / "saved-version.json").write_text(json.dumps(saved, indent=2), encoding="utf-8")
    (tmp_path / "verification.json").write_text(json.dumps({"protocol": protocol, "boundary": boundary,
        "source_sha256": sha256(source.read_bytes()).hexdigest(), "attempts": current["attempts"],
        "known_before": stopped["active_seconds"], "known_after": current["active_seconds"],
        "time_gaps": current["active_time_gaps"], "effective_limits": current["limits"], "effective_route": current["route"],
        "original_blobs_unchanged": len(originals), "saved_source_text_exact": True, "native_pixels_exact": True,
        "all_export_members_exact": True, "full_raw_field_range_access": True, "frozen_input_unchanged": True,
        "live_model_calls": 0}, indent=2), encoding="utf-8")
