"""D01/D02 diagnostic subjects and facts, using isolated historical fixtures only."""
from copy import deepcopy
import json
import subprocess
import sys

import httpx
import pytest

from pdfmd.documents import Documents
from pdfmd.nexus import Nexus, StopRun, make_payload
from pdfmd.recovery import diagnose, resolve
from pdfmd.runtime import Runtime
from pdfmd.schema import Route
from pdfmd.storage import Store
from pdfmd.streaming import StreamDecoder
from test_accepted_evidence_recovery import historical, replace_blob
from test_continuation import delivery, check_delivery
from test_response_repairs import native
from test_runtime import tool
from test_stream_terminal import Body, forbidden
from test_streaming_delivery import stream_frames


def files(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def resolved(setup, monkeypatch, protocol="chat_completions", published=True, **kwargs):
    store, job, key, reply, raw = historical(setup, monkeypatch, protocol, published, **kwargs)
    first = diagnose(store.root, job["id"])
    assert first["eligible"], first
    decision = resolve(store, job["id"], key, first["basis"])
    assert decision["projection"] == "ready"
    return store, job, key, reply, raw


def next_request(store, job, monkeypatch, outcome="timeout", suffix=b"data: {"):
    sends = []
    protocol = job["route"]["protocol"]
    value = native(protocol, tool("read_document", {}, "next-read"))
    raw = b"".join(stream_frames(protocol, value)) + suffix
    def transport(request):
        sends.append(request.content)
        if outcome == "timeout":
            raise httpx.ReadTimeout("Synthetic next request timed out", request=request)
        return httpx.Response(200, stream=Body([raw]))
    service = Nexus(store, lambda _: "synthetic-only", httpx.MockTransport(transport))
    runtime = Runtime(store, service)
    config = {"configurable": {"thread_id": job["id"]}}
    try:
        state = runtime.graph.get_state(config).values
        key = f"{job['id']}:{state['seq']}:{state['revision']}"
        route = Route.model_validate(store.get("job", job["id"])["route"])
        service.freeze(job["id"], key, make_payload(route, "Synthetic next request", [], []), "normal", {})
        runtime.graph.update_state(config, {"pending": key, "next": "model"}, as_node="prepare")
        if outcome == "prepared":
            return key, sends
        with monkeypatch.context() as patch:
            if outcome == "historical":
                patch.setattr(StreamDecoder, "finish_received", lambda self: deepcopy(self.value))
            try:
                service.send(job["id"], key)
            except StopRun as exc:
                store.update_job(job["id"], status="blocked", stop_reason=exc.reason, last_message=str(exc))
        return key, sends
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol,published", [("chat_completions", True), ("responses", False)])
@pytest.mark.parametrize("outcome", ["timeout", "prepared", "historical"])
def test_new_frozen_request_remains_primary_without_or_with_staging(setup, monkeypatch, protocol, published, outcome):
    store, job, old, _, _ = resolved(setup, monkeypatch, protocol, published)
    key, sends = next_request(store, job, monkeypatch, outcome)
    before = files(store.root)
    current = diagnose(store.root, job["id"])
    assert current["request"] == key, current
    assert current.get("projection") != "ready"
    assert current["status"] == ("eligible" if outcome == "historical" else "missing_staging")
    assert old in json.dumps(current.get("historical_resolutions", []))
    assert files(store.root) == before
    assert len(sends) == (0 if outcome == "prepared" else 1)


@pytest.mark.parametrize("protocol,published", [("chat_completions", True), ("responses", False)])
def test_immediate_boundary_reopens_without_phantom_request_and_complete_facts(setup, monkeypatch, protocol, published):
    store, job, key, reply, raw = resolved(setup, monkeypatch, protocol, published, suffix=b"\xe4")
    before = files(store.root)
    first = diagnose(store.root, job["id"])
    child = subprocess.run([sys.executable, "-c", "import json,sys;from pdfmd.recovery import diagnose;print(json.dumps(diagnose(sys.argv[1],sys.argv[2])))", str(store.root), job["id"]], capture_output=True, text=True, timeout=25)
    assert child.returncode == 0, child.stderr
    reopened = json.loads(child.stdout)
    assert reopened == first
    assert first["request"] == key and first["projection"] == "ready"
    assert first["job"] == job["id"]
    assert first["native_ref"] == reply["native_ref"] and first["stream_ref"] == reply["stream_ref"]
    assert first["original_usage"] == store.get("attempt", first["attempt"])["usage"]
    assert first["saved_usage"] == reply["usage"]
    request = store.get("request", key)
    attempt = store.get("attempt", first["attempt"])
    assert first["original_request_status"] == request["status"]
    assert first["original_attempt_status"] == attempt["status"]
    assert first["original_finish"] == attempt.get("finished")
    assert first["verification"] == {"original": "checked_now", "saved": "verified_at_resolution",
                                      "raw": "verified_at_resolution", "operations": "verified_at_resolution"}
    assert "head" in first and "versions" in first
    operation = first["effects"]["operations"][0]
    assert operation["certainty"] == "not_started"
    assert operation["candidate_ref"] == f"candidate:{key}:0" and operation["result_ref"] == f"result:{key}:0"
    assert store.bytes(first["stream_ref"], job["id"]) == raw and raw.endswith(b"\xe4")
    assert len(store.records("request", job["id"])) == 1
    assert files(store.root) == before


@pytest.mark.parametrize("blocked", [False, True])
def test_current_own_resolution_pending_or_blocked_cannot_be_hidden_by_old_ready(setup, monkeypatch, blocked):
    import pdfmd.recovery as recovery
    store, job, old, _, _ = resolved(setup, monkeypatch)
    key, _ = next_request(store, job, monkeypatch, "historical")
    current = diagnose(store.root, job["id"])
    def interrupt(*_):
        raise RuntimeError("committed before projection")
    with monkeypatch.context() as patch:
        patch.setattr(recovery, "committed", interrupt)
        with pytest.raises(RuntimeError, match="before projection"):
            resolve(store, job["id"], key, current["basis"])
    if blocked:
        runtime = Runtime(store, Nexus(store, forbidden))
        try:
            runtime.graph.update_state({"configurable": {"thread_id": job["id"]}}, {"notes": "divergence after committed choice"}, as_node="prepare")
        finally:
            runtime.close()
    before = files(store.root)
    current = diagnose(store.root, job["id"])
    assert current["request"] == key
    assert current["projection"] == ("blocked" if blocked else "pending")
    assert current["resolution_ref"] == f"conflict-resolution:{key}"
    assert old in json.dumps(current.get("historical_resolutions", []))
    assert files(store.root) == before
    if not blocked:
        decision = resolve(store, job["id"], key, "duplicate old basis")
        assert decision["projection"] == "ready"
        assert len(store.records("conflict_resolution", job["id"])) == 2


def test_multiple_resolutions_select_relationship_not_catalog_order(setup, monkeypatch):
    store, job, old, _, _ = resolved(setup, monkeypatch)
    key, _ = next_request(store, job, monkeypatch, "historical")
    first = diagnose(store.root, job["id"])
    resolve(store, job["id"], key, first["basis"])
    # Historical rows can have any insertion order. Move R last without changing its bytes.
    with store.transaction() as db:
        db.execute("UPDATE records SET created=(SELECT MAX(created)+1 FROM records) WHERE kind='conflict_resolution' AND id=?", (old,))
    before = files(store.root)
    result = diagnose(store.root, job["id"])
    assert result["request"] == key and result["projection"] == "ready"
    assert files(store.root) == before


@pytest.mark.parametrize("progress", ["coordinate", "completed"])
def test_later_progress_does_not_reuse_historical_ready_as_current(setup, monkeypatch, progress):
    store, job, old, _, _ = resolved(setup, monkeypatch)
    runtime = Runtime(store, Nexus(store, forbidden))
    try:
        config = {"configurable": {"thread_id": job["id"]}}
        if progress == "completed":
            store.update_job(job["id"], status="completed")
            runtime.graph.update_state(config, {"terminal": True, "next": "done"}, as_node="tools")
        else:
            runtime.graph.update_state(config, {"notes": "later workflow progress", "next": "model"}, as_node="coordinate")
    finally:
        runtime.close()
    before = files(store.root)
    result = diagnose(store.root, job["id"])
    assert result.get("projection") != "ready", result
    assert not result["eligible"]
    assert old in json.dumps(result.get("historical_resolutions", []))
    assert files(store.root) == before


@pytest.mark.parametrize("case", ["known", "original_unknown", "zero", "different_known"])
def test_usage_projection_preserves_known_unknown_zero_and_inconsistency(setup, monkeypatch, case):
    import test_accepted_evidence_recovery as fixtures
    value = native("chat_completions", tool("read_document", {}, "read"))
    if case == "zero":
        value["usage"] = {"prompt_tokens": 0, "completion_tokens": 0}
    with monkeypatch.context() as patch:
        patch.setattr(fixtures, "native", lambda *_args, **_kwargs: value)
        if case == "zero":
            patch.setattr(fixtures, "stream_frames", lambda *args: [
                frame.replace(b'"prompt_tokens": 100, "completion_tokens": 50', b'"prompt_tokens": 0, "completion_tokens": 0')
                for frame in stream_frames(*args)])
        store, job, key, reply, _ = historical(setup, patch, "chat_completions", published=case != "original_unknown")
    if case == "different_known":
        request = store.get("request", key)
        attempt = store.get("attempt", request["attempts"][0])
        store.put("attempt", attempt["id"], job["id"], {**attempt, "usage": {"prompt_tokens": 7, "completion_tokens": 2}})
    first = diagnose(store.root, job["id"])
    expected = None if case == "original_unknown" else {"prompt_tokens": 7, "completion_tokens": 2} if case == "different_known" else value["usage"]
    assert "original_usage" in first and first["original_usage"] == expected
    if case == "different_known":
        assert not first["eligible"] and first["status"] == "evidence_unconfirmed"
        assert "usage" in json.dumps(first["reasons"]).lower()
        return
    assert first["saved_usage"] == reply["usage"]
    resolve(store, job["id"], key, first["basis"])
    before = files(store.root)
    reopened = diagnose(store.root, job["id"])
    assert reopened["original_usage"] == expected and reopened["saved_usage"] == reply["usage"]
    assert files(store.root) == before


@pytest.mark.parametrize("missing", ["native", "raw"])
def test_known_missing_evidence_stays_explicit_and_cannot_claim_ready(setup, monkeypatch, missing):
    store, job, key, reply, _ = resolved(setup, monkeypatch)
    ref = reply["native_ref"] if missing == "native" else reply["stream_ref"]
    blob = store.get("blob", ref)
    (store.root / "objects" / blob["sha256"]).rename(store.root / f"preserved-{missing}")
    before = files(store.root)
    result = diagnose(store.root, job["id"])
    assert result["request"] == key
    assert result.get("projection") != "ready" and not result["eligible"]
    assert result["evidence_availability"][ref]["status"] == "unavailable"
    assert result["original_usage"] == {"prompt_tokens": 100, "completion_tokens": 50}
    assert files(store.root) == before


def test_current_head_is_separate_from_resolution_head_and_source_delivery_unchanged(delivery, monkeypatch, tmp_path):
    from pdfmd.tools import Dispatcher
    store, job, version, image, source = delivery
    store, job, key, reply, _ = resolved((store, job), monkeypatch)
    receipt_ref = f"conflict-resolution:{key}"
    receipt = store.bytes(receipt_ref, job["id"])
    content = Documents(store).version(job["id"], version)["content"]
    edit = Dispatcher(store).execute(job["id"], "later-manual-edit", "edit_document", json.dumps({
        "base_version": version, "expected_head": version, "replace_blocks": content["blocks"], "claim": "complete"}))
    new_head = edit["data"]["version_id"]
    before = files(store.root)
    current = diagnose(store.root, job["id"])
    assert current["head"] == new_head and set(current["versions"]) == {version, new_head}
    assert current["resolution_head"] == version
    assert store.bytes(receipt_ref, job["id"]) == receipt
    assert files(store.root) == before
    check_delivery(Store(store.root), job, version, image, source, tmp_path / "explicit-original.zip")
    check_delivery(Store(store.root), job, new_head, image, source, tmp_path / "explicit-current.zip")


def test_resolved_inspection_busy_and_stale_do_not_report_ready(setup, monkeypatch):
    from filelock import FileLock
    from contextlib import contextmanager
    import pdfmd.recovery as recovery
    store, job, _, _, _ = resolved(setup, monkeypatch)
    with FileLock(str(store.root / f"task-{job['id']}.lock")):
        result = diagnose(store.root, job["id"])
        assert result["status"] == "busy" and result.get("projection") != "ready"
    original = recovery.inspection
    @contextmanager
    def racing(*args, **kwargs):
        with original(*args, **kwargs) as value:
            yield value
            store.update_job(job["id"], amendments=["changed during inspection"])
    with monkeypatch.context() as patch:
        patch.setattr(recovery, "inspection", racing)
        result = diagnose(store.root, job["id"])
    assert result["status"] == "stale_view" and result.get("projection") != "ready", result


def test_resolved_diagnosis_never_initializes_store_runtime_or_reconciles(setup, monkeypatch):
    store, job, key, _, _ = resolved(setup, monkeypatch)
    before = files(store.root)
    monkeypatch.setattr(Store, "__init__", forbidden)
    monkeypatch.setattr(Runtime, "__init__", forbidden)
    monkeypatch.setattr(Nexus, "reconcile", forbidden)
    monkeypatch.setattr(Store, "put", forbidden)
    monkeypatch.setattr(Store, "blob", forbidden)
    result = diagnose(store.root, job["id"])
    assert result["request"] == key and result["projection"] == "ready"
    assert files(store.root) == before


def test_actual_authenticated_api_opens_saved_native_and_incomplete_utf8_raw(setup, monkeypatch):
    import base64
    from fastapi.testclient import TestClient
    from pdfmd.server import create_app
    store, job, key, reply, raw = resolved(setup, monkeypatch, suffix=b"\xe4")
    app = create_app(store.root, "diagnostics-local-only", transport=httpx.MockTransport(forbidden))
    headers = {"Authorization": "Bearer diagnostics-local-only"}
    with TestClient(app) as client:
        before = files(store.root)
        result = client.get(f"/jobs/{job['id']}/accepted-evidence-diagnosis", headers=headers).json()
        assert result["request"] == key
        assert result["original_usage"] == {"prompt_tokens": 100, "completion_tokens": 50}
        native_result = client.get(f"/jobs/{job['id']}/evidence/{result['native_ref']}", headers=headers)
        raw_result = client.get(f"/jobs/{job['id']}/evidence/{result['stream_ref']}", params={"view": "raw"}, headers=headers)
        assert native_result.status_code == raw_result.status_code == 200
        assert native_result.json()["value"] == json.loads(store.bytes(reply["native_ref"], job["id"]))
        assert base64.b64decode(raw_result.json()["data"]) == raw
        assert raw_result.json()["complete"] and raw.endswith(b"\xe4")
        assert files(store.root) == before


def test_inconsistent_current_resolution_keeps_current_identity_and_blocks(setup, monkeypatch):
    import pdfmd.recovery as recovery
    store, job, old, _, _ = resolved(setup, monkeypatch)
    key, _ = next_request(store, job, monkeypatch, "historical")
    result = diagnose(store.root, job["id"])
    def interrupt(*_):
        raise RuntimeError("committed before projection")
    with monkeypatch.context() as patch:
        patch.setattr(recovery, "committed", interrupt)
        with pytest.raises(RuntimeError, match="before projection"):
            resolve(store, job["id"], key, result["basis"])
    authority = store.get("conflict_resolution", key)
    store.put("conflict_resolution", key, job["id"], {**authority, "basis": "inconsistent authority basis"})
    before = files(store.root)
    result = diagnose(store.root, job["id"])
    assert result["request"] == key, result
    assert result.get("projection") != "ready" and not result["eligible"]
    assert result["reasons"]
    assert files(store.root) == before


def test_readonly_snapshot_failure_never_reports_fresh_verified_or_ready(setup, monkeypatch):
    from contextlib import contextmanager
    import pdfmd.recovery as recovery
    store, job, _, _, _ = resolved(setup, monkeypatch)
    before = files(store.root)
    @contextmanager
    def unavailable_snapshot(*_args, **_kwargs):
        raise OSError("Synthetic read-only snapshot unavailable")
        yield
    monkeypatch.setattr(recovery, "inspection", unavailable_snapshot)
    result = diagnose(store.root, job["id"])
    assert not result["eligible"] and result.get("projection") != "ready"
    assert result["status"] in {"busy", "evidence_unconfirmed", "unavailable"}
    assert result["storage"]["status"] in {"unknown", "unavailable"}
    assert result["reasons"]
    assert files(store.root) == before


def test_current_timeout_without_staging_reports_unavailable_current_head(delivery, monkeypatch):
    store, job, version, _, _ = delivery
    store, job, old, _, _ = resolved((store, job), monkeypatch)
    key, sends = next_request(store, job, monkeypatch, "timeout")
    document = store.root / "versions" / version / "document.json"
    document.rename(store.root / "preserved-current-head-document.json")
    before = files(store.root)
    result = diagnose(store.root, job["id"])
    assert result["request"] == key and key != old
    assert result["head"] == version and result["head_verification"] == "unavailable"
    assert result["status"] == "missing_staging" and not result["eligible"]
    assert result.get("projection") != "ready"
    assert any("Current head is unavailable/inconsistent" in reason for reason in result["reasons"]), result
    assert len(sends) == 1 and files(store.root) == before


def test_completed_job_alone_cannot_reuse_immediate_graph_boundary_ready(setup, monkeypatch):
    store, job, old, _, _ = resolved(setup, monkeypatch)
    store.update_job(job["id"], status="completed")
    before = files(store.root)
    result = diagnose(store.root, job["id"])
    assert result.get("request") is None and result.get("projection") != "ready"
    assert not result["eligible"]
    assert old in json.dumps(result["historical_resolutions"])
    assert files(store.root) == before


@pytest.mark.parametrize("missing_staging", [False, True])
def test_resolved_links_remain_bound_to_selected_attempt_with_earlier_diagnostics(setup, monkeypatch, missing_staging):
    # Isolated historical fixture: an earlier unknown attempt's diagnostic
    # pointers coexist with a complete later saved response awaiting publication.
    store, job, key, reply, raw = historical(setup, monkeypatch, "chat_completions", published=False)
    request = store.get("request", key)
    selected_attempt = request["attempts"][0]
    earlier_attempt = key + ":earlier-attempt"
    previous_raw = store.blob(job["id"], "raw_stream", b": earlier attempt, incomplete\n\n",
        {"request": key, "attempt": earlier_attempt, "complete_protocol": False}, key="zzzz-earlier-raw")
    previous_native = store.blob(job["id"], "assembled_response", {"id": "earlier-native", "choices": []},
        {"request": key, "attempt": earlier_attempt, "source_stream_ref": previous_raw["ref"],
         "protocol": "chat_completions", "complete_protocol": False}, key="zzzz-earlier-native")
    store.put("attempt", earlier_attempt, job["id"], {**store.get("attempt", selected_attempt),
        "id": earlier_attempt, "status": "unknown", "usage": None, "finished": None, "stream_ref": previous_raw["ref"]})
    store.put("request", key, job["id"], {**request, "attempts": [earlier_attempt, selected_attempt],
        "response_ref": previous_native["ref"], "stream_ref": previous_raw["ref"]})
    result = diagnose(store.root, job["id"])
    assert result["eligible"], result
    resolve(store, job["id"], key, result["basis"])
    receipt_bytes = store.bytes(f"conflict-resolution:{key}", job["id"])
    if missing_staging:
        staging = store.get("blob", f"accepted:{key}")
        (store.root / "objects" / staging["sha256"]).rename(store.root / "preserved-selected-staging")
    before = files(store.root)
    result = diagnose(store.root, job["id"])
    assert result["request"] == key and result["attempt"] == selected_attempt
    assert result["native_ref"] == reply["native_ref"]
    assert result["stream_ref"] == reply["stream_ref"]
    assert result["evidence_provenance"]["stream_ref"]["attempt"] == selected_attempt
    assert result["evidence_provenance"]["native_ref"]["attempt"] == selected_attempt
    assert result["current_attempt_evidence"] == {"native_ref": "established", "stream_ref": "established"}
    assert store.bytes(result["stream_ref"], job["id"]) == raw
    if missing_staging:
        assert result.get("projection") != "ready"
        assert result["evidence_availability"][f"accepted:{key}"]["status"] == "unavailable"
    else:
        assert result["projection"] == "ready"
    assert store.bytes(f"conflict-resolution:{key}", job["id"]) == receipt_bytes
    assert files(store.root) == before
