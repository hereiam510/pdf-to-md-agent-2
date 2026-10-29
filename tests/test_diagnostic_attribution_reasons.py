"""Attempt attribution and predicate explanations; synthetic file-backed traffic only."""
import base64
import json
import subprocess
import sys
from hashlib import sha256

import httpx
import pytest

from pdfmd.nexus import Nexus, StopRun, make_payload
from pdfmd.recovery import diagnose, resolve
from pdfmd.runtime import Runtime
from pdfmd.schema import Route
from test_accepted_evidence_recovery import historical, replace_blob
from test_continuation import delivery
from test_recovery_diagnostics import files
from test_stream_terminal import Body, WAIT, forbidden
from test_runtime import tool


def retained_native(store, job, key, owner):
    """Explicit extra fixture, NOT a native object naturally made by partial SSE.

    This separately retained incomplete native-shaped diagnostic exercises
    per-reference provenance. It supplies no acceptance or executable calls.
    """
    return store.blob(job["id"], "assembled_response", {"id": "retained-partial", "choices": []},
        {"request": key, "attempt": owner, "protocol": job["route"]["protocol"],
         "complete_protocol": False, "source_stream_ref": f"raw-stream:{owner}"})["ref"]


def two_attempts(setup, protocol, *, second_bytes=False):
    """Use actual freeze/send/ledger paths, with an explicit test-only replay policy."""
    store, job = setup
    job = store.update_job(job["id"], route={**job["route"], "protocol": protocol,
        "endpoint": "https://synthetic.invalid/v1/" + ("responses" if protocol == "responses" else "chat/completions"),
        "wait_policy": WAIT}, limits={**job["limits"], "replay_unknown": True, "max_attempts_per_request": 2})
    route = Route.model_validate(job["route"])
    key = job["id"] + ":0:0"
    sends = []
    # A genuinely partial successful SSE prefix, with no terminal or native reply.
    raw = b'data: {"choices": [{"index": 0, "delta": {"content": "partial A"}}]}\n\n' if protocol == "chat_completions" else b'data: {"type": "response.created", "response": {"id": "A"}}\n\n'
    raw_b = b": current B prefix\n\n"
    def transport(request):
        sends.append(request.content)
        if len(sends) == 2 and not second_bytes:
            raise httpx.ReadTimeout("Synthetic B before headers/body", request=request)
        return httpx.Response(200, stream=Body([raw if len(sends) == 1 else raw_b,
            httpx.ReadTimeout("Synthetic partial timeout", request=request)]))
    service = Nexus(store, lambda _: "synthetic-only", httpx.MockTransport(transport))
    runtime = Runtime(store, service)
    try:
        service.freeze(job["id"], key, make_payload(route, "Offline attribution", [], []), "normal", {})
        runtime.graph.update_state({"configurable": {"thread_id": job["id"]}},
            {"job": job["id"], "seq": 0, "revision": 0, "history": [], "pending": key, "next": "model"}, as_node="prepare")
        for _ in range(2):
            with pytest.raises(StopRun) as stopped:
                service.send(job["id"], key)
            assert stopped.value.reason == "unknown_outcome"
        store.update_job(job["id"], status="blocked", stop_reason="unknown_outcome", last_message="Offline two-attempt fixture")
    finally:
        runtime.close()
    request = store.get("request", key)
    assert len(sends) == 2 and request["replay_policy"]["max_attempts_per_request"] == 2
    assert not store.maybe("blob", f"accepted:{key}") and not request["accepted_ref"]
    assert not request.get("response_ref")  # partial SSE alone did not create native evidence
    return store, job, key, request["attempts"], raw, raw_b


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_actual_partial_a_zero_byte_b_keeps_evidence_owner_and_reopens(setup, protocol):
    store, job, key, (a, b), raw, _ = two_attempts(setup, protocol)
    before = files(store.root)
    result = diagnose(store.root, job["id"])
    assert result["attempt"] == b and result["stream_ref"] == f"raw-stream:{a}"
    assert result.get("evidence_provenance", {}).get("stream_ref", {}).get("attempt") == a, result
    assert result["evidence_provenance"]["stream_ref"]["relation"] == "earlier_attempt"
    assert result["evidence_provenance"]["stream_ref"]["completeness"] == "partial"
    assert result["current_attempt_evidence"]["stream_ref"] == "not_established"
    assert result["attempt_observation"]["received_body_bytes"] == 0
    assert store.bytes(result["stream_ref"], job["id"]) == raw
    assert not result["eligible"] and result["saved_usage_state"] == "unavailable"
    child = subprocess.run([sys.executable, "-c", "import json,sys;from pdfmd.recovery import diagnose;print(json.dumps(diagnose(sys.argv[1],sys.argv[2])))", str(store.root), job["id"]], capture_output=True, text=True, timeout=25)
    assert child.returncode == 0, child.stderr
    assert json.loads(child.stdout) == result
    assert files(store.root) == before


def head_refusal_fixture(setup, monkeypatch, protocol="chat_completions"):
    """One completed source read establishes a real effect independently of head."""
    store, job, key, reply, raw = historical(setup, monkeypatch, protocol,
        calls=[tool("inspect_pdf", {"pages": [1], "mode": "text"}, "completed-source-read")])
    from pdfmd.tools import Dispatcher
    call = reply["calls"][0]
    result = Dispatcher(store).execute(job["id"], key + ":0", call["name"], call["arguments"])
    assert result["ok"]
    return store, job, key, reply, raw


def test_supported_finish_head_failure_has_only_actual_reason(delivery, monkeypatch):
    store, job, version, _, _ = delivery
    store, job, key, _, _ = head_refusal_fixture((store, job), monkeypatch)
    (store.root / "versions" / version / "document.json").rename(store.root / "preserved-head.json")
    before = files(store.root)
    result = diagnose(store.root, job["id"])
    assert result["receive_boundary"]["status"] == "finish_conflict"
    assert result["effects"]["status"] == "established" and not result["eligible"]
    assert result["effects"]["operations"][0]["certainty"] == "completed"
    assert result["reasons"] == result["fact_errors"], result["reasons"]
    assert "Current head" in result["reasons"][0]
    with pytest.raises(ValueError):
        resolve(store, job["id"], key, result["basis"])
    # Resolve may create its explicit task lock; diagnosis itself did not write.
    assert {k: v for k, v in files(store.root).items() if not k.endswith('.lock')} == {k: v for k, v in before.items() if not k.endswith('.lock')}


def test_current_raw_and_separately_retained_earlier_native_are_independent(setup):
    store, job, key, (a, b), _, raw_b = two_attempts(setup, "responses", second_bytes=True)
    ref = retained_native(store, job, key, a)
    request = store.get("request", key)
    store.put("request", key, job["id"], {**request, "response_ref": ref})
    before = files(store.root)
    result = diagnose(store.root, job["id"])
    assert result["evidence_provenance"]["native_ref"]["attempt"] == a
    assert result["evidence_provenance"]["native_ref"]["relation"] == "earlier_attempt"
    assert result["evidence_provenance"]["native_ref"]["completeness"] == "partial"
    assert result["evidence_provenance"]["stream_ref"]["attempt"] == b
    assert result["evidence_provenance"]["stream_ref"]["relation"] == "selected_attempt"
    assert result["current_attempt_evidence"] == {"native_ref": "not_established", "stream_ref": "established"}
    assert result["attempt_observation"]["received_body_bytes"] == len(raw_b)
    assert store.bytes(result["stream_ref"], job["id"]) == raw_b
    assert result["verification"]["raw"] == "unknown" and not result["eligible"]
    assert files(store.root) == before


@pytest.mark.parametrize("case", ["wrong_request", "foreign_task", "missing_descriptor", "missing_meta",
    "wrong_kind", "wrong_ref", "duplicate_membership", "missing_member", "missing_attempt", "attempt_request", "nonobject_descriptor", "partial_complete"])
def test_unconfirmed_owner_cannot_be_trusted_and_other_facts_survive(setup, case):
    store, job, key, (a, b), _, _ = two_attempts(setup, "chat_completions", second_bytes=True)
    ref = retained_native(store, job, key, a)
    request = store.get("request", key)
    store.put("request", key, job["id"], {**request, "response_ref": ref})
    descriptor = store.get("blob", ref)
    if case in {"wrong_request", "missing_meta", "wrong_kind", "wrong_ref", "nonobject_descriptor", "partial_complete"}:
        if case == "wrong_request": descriptor["meta"]["request"] = "wrong-request"
        elif case == "missing_meta": descriptor.pop("meta")
        elif case == "wrong_kind": descriptor["kind"] = "tool_result"
        elif case == "wrong_ref": descriptor["ref"] = "different-reference"
        elif case == "nonobject_descriptor": descriptor = []
        else:
            descriptor["kind"] = "partial_native_response"
            descriptor["meta"]["complete_transport"] = True
        store.put("blob", ref, job["id"], descriptor)
    elif case in {"foreign_task", "missing_descriptor"}:
        with store.transaction() as db:
            if case == "foreign_task":
                db.execute("UPDATE records SET job='foreign' WHERE kind='blob' AND id=?", (ref,))
            else:
                db.execute("DELETE FROM records WHERE kind='blob' AND id=?", (ref,))
    elif case in {"duplicate_membership", "missing_member"}:
        request = store.get("request", key)
        request["attempts"] = [a, a, b] if case == "duplicate_membership" else [b]
        store.put("request", key, job["id"], request)
    elif case == "missing_attempt":
        with store.transaction() as db:
            db.execute("DELETE FROM records WHERE kind='attempt' AND id=?", (a,))
    else:
        attempt = store.get("attempt", a)
        store.put("attempt", a, job["id"], {**attempt, "request": "wrong-request"})
    before = files(store.root)
    result = diagnose(store.root, job["id"])
    assert result["attempt"] == b and result["original_usage_state"] == "unknown"
    assert result["evidence_provenance"]["native_ref"]["status"] == "unconfirmed"
    assert "attempt" not in result["evidence_provenance"]["native_ref"]
    assert result["evidence_availability"][ref]["status"] == "unavailable"
    assert result["evidence_provenance"]["stream_ref"]["attempt"] == b
    assert result["current_attempt_evidence"]["stream_ref"] == "established"
    assert result["fact_errors"] and not result["eligible"]
    assert files(store.root) == before


@pytest.mark.parametrize("transport", [None, {}, {"settled": False}, {"received_body_bytes": None}])
def test_missing_observation_is_never_zero(setup, transport):
    store, job, _, (_, b), _, _ = two_attempts(setup, "responses")
    attempt = store.get("attempt", b)
    attempt.pop("transport")
    if transport is not None:
        attempt["transport"] = transport
    store.put("attempt", b, job["id"], attempt)
    result = diagnose(store.root, job["id"])
    assert result["attempt_observation"]["status"] == ("unavailable" if transport and "received_body_bytes" in transport else "missing")
    assert "received_body_bytes" not in result["attempt_observation"]
    assert result["current_attempt_evidence"]["stream_ref"] == "not_established"


def unsupported_tail(store, job, key, raw):
    """Consistent historical archive with a feed-time-invalid post-terminal event."""
    attempt = store.get("request", key)["attempts"][0]
    changed = raw[:-len(b"data: {")] + b"data: {}\n\n"
    replace_blob(store, job["id"], f"stream:{attempt}:0", changed)
    replace_blob(store, job["id"], f"raw-stream:{attempt}", changed)
    observed = store.get("stream_receive", attempt)
    observed["cursor"].update(bytes=len(changed), sha256=sha256(changed).hexdigest())
    observed["transport"]["received_body_bytes"] = len(changed)
    store.put("stream_receive", attempt, job["id"], observed)
    stage = store.get("blob", f"accepted:{key}")
    stage["meta"]["transport"]["received_body_bytes"] = len(changed)
    store.put("blob", stage["ref"], job["id"], stage)
    sending = store.get("attempt", attempt)
    sending["transport"]["received_body_bytes"] = len(changed)
    store.put("attempt", attempt, job["id"], sending)


@pytest.mark.parametrize("boundary,unknown_effect,bad_head", [
    ("finish_conflict", False, False), ("finish_conflict", True, False),
    ("feed_error", False, False), ("feed_error", True, True),
    ("compatible", False, False), ("compatible", False, True), ("compatible", True, True)])
def test_reasons_follow_each_failed_predicate_and_action_guards(delivery, monkeypatch, boundary, unknown_effect, bad_head):
    store, job, version, _, _ = delivery
    calls = [tool("read_document", {}, "unknown-read")] if unknown_effect else []
    store, job, key, _, raw = historical((store, job), monkeypatch, "responses", calls=calls,
        text="Synthetic retained reply", suffix=b": compatible" if boundary == "compatible" else b"data: {")
    if unknown_effect:
        runtime = Runtime(store, Nexus(store, forbidden))
        try:
            from pdfmd.recovery import digest
            call = store.json(f"accepted:{key}", job["id"])["calls"][0]
            candidate = store.blob(job["id"], "candidate", call["arguments"].encode(),
                {"operation": key + ":0", "tool": call["name"]}, key=f"candidate:{key}:0")
            store.put("operation", key + ":0", job["id"], {"id": key + ":0", "tool": call["name"],
                "args_hash": digest([call["name"], call["arguments"]]), "candidate_ref": candidate["ref"], "status": "started"})
        finally:
            runtime.close()
    if boundary == "feed_error": unsupported_tail(store, job, key, raw)
    if bad_head:
        (store.root / "versions" / version / "document.json").rename(store.root / "preserved-head.json")
    before = files(store.root)
    result = diagnose(store.root, job["id"])
    assert result["receive_boundary"]["status"] == boundary
    assert result["eligible"] == (boundary == "finish_conflict" and not unknown_effect and not bad_head)
    reasons = result["reasons"]
    assert sum("outside the supported" in r for r in reasons) == (boundary == "feed_error")
    assert sum("Unknown tool effect" in r for r in reasons) == unknown_effect
    assert sum("Current head" in r for r in reasons) == bad_head
    assert sum("Receive evidence is compatible" in r for r in reasons) == (boundary == "compatible")
    assert len(reasons) == len(set(reasons))
    assert files(store.root) == before
    if not result["eligible"]:
        with pytest.raises(ValueError): resolve(store, job["id"], key, result["basis"])


def test_attribution_authenticated_api_evidence_read_has_no_execution_or_writes(setup, monkeypatch):
    from fastapi.testclient import TestClient
    from pdfmd.server import create_app
    from pdfmd.storage import Store
    store, job, _, (a, b), raw, _ = two_attempts(setup, "chat_completions")
    app = create_app(store.root, "offline-attribution", transport=httpx.MockTransport(forbidden))
    with TestClient(app) as client:
        before = files(store.root)
        monkeypatch.setattr(Store, "__init__", forbidden)
        monkeypatch.setattr(Runtime, "__init__", forbidden)
        monkeypatch.setattr(Nexus, "reconcile", forbidden)
        monkeypatch.setattr(Store, "put", forbidden)
        monkeypatch.setattr(Store, "blob", forbidden)
        headers = {"Authorization": "Bearer offline-attribution"}
        response = client.get(f"/jobs/{job['id']}/accepted-evidence-diagnosis", headers=headers)
        assert response.status_code == 200
        result = response.json()
        assert result["attempt"] == b and result["evidence_provenance"]["stream_ref"]["attempt"] == a
        response = client.get(f"/jobs/{job['id']}/evidence/{result['stream_ref']}", params={"view": "raw"}, headers=headers)
        assert response.status_code == 200 and base64.b64decode(response.json()["data"]) == raw
        assert files(store.root) == before
