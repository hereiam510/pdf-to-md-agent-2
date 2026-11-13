"""SC02 full acceptance, interruption and synthetic delivery; never a live route."""
from copy import deepcopy
import json
import zipfile

import httpx
import pymupdf
import pytest

from pdfmd.documents import Documents
from pdfmd.nexus import Nexus, StopRun
from pdfmd.runtime import Runtime
from pdfmd.storage import Conflict, Store
from tests.engine.execution.test_continuation import delivery, check_delivery, continue_job
from tests.engine.transport.test_response_repairs import native
from tests.engine.execution.test_runtime import tool
from tests.engine.transport.test_streaming_parser import event
from tests.engine.transport.test_stream_terminal import Body, WAIT, forbidden, snapshot


def frames(value, defect=None):
    """Independent identities and correct domain arguments come from each test."""
    value = deepcopy(value)
    value["id"] = "sc02-synthetic-response"
    events = []
    for index, current in enumerate(value["output"]):
        current["id"] = f"sc02-item-{index}"
        initial = {**current, "status": "in_progress"}
        initial["arguments" if current["type"] == "function_call" else "content"] = "" if current["type"] == "function_call" else []
        events.append({"type": "response.output_item.added", "output_index": index, "item": initial})
        done = deepcopy(current)
        if defect and index == 0:
            field, bad = defect
            done[field] = bad
        events.append({"type": "response.output_item.done", "output_index": index, "item": done})
    events.append({"type": "response.completed", "response": value})
    return [event(x) for x in events]


def configure(store, job):
    return store.update_job(job["id"], route={**job["route"], "protocol": "responses",
        "endpoint": "https://synthetic.invalid/v1/responses", "wait_policy": WAIT})


@pytest.mark.parametrize("defect", [("status", "incomplete"), ("status", "in_progress"), ("role", "user")])
def test_rejected_runtime_cannot_edit_then_continue_creates_successor(delivery, tmp_path, defect):
    store, job, version, image, source = delivery
    job = configure(store, job)
    sends = []
    invalid = native("responses", tool("edit_document", {"base_version": version, "expected_head": version,
        "operations": [{"kind": "delete", "id": "p2"}]}, "must-not-execute"))
    if defect[0] == "role":
        invalid["output"].insert(0, {"type": "message", "role": "assistant", "status": "completed",
            "content": [{"type": "output_text", "text": "Preserved role control."}]})

    def answer(request):
        payload = json.loads(request.content)
        sends.append(payload)
        if len(sends) == 1:
            return httpx.Response(200, stream=Body([b"".join(frames(invalid, defect))]))
        assert "Request continuation record" in json.dumps(payload)
        assert not any(x.get("type") == "function_call_output" for x in payload["input"])
        value = native("responses", tool("report", {"state": "complete", "version_id": version,
            "message": "The complete synthetic source and image remain saved."}, "successor-report"))
        return httpx.Response(200, stream=Body(frames(value)))

    transport = httpx.MockTransport(answer)
    for _ in range(2):
        current = Store(store.root)
        runtime = Runtime(current, Nexus(current, lambda _: "fixture-only", transport))
        try:
            runtime.run(job["id"])
        finally:
            runtime.close()
    assert len(sends) == 1
    old = store.records("request", job["id"])[0]
    original = snapshot(store, job["id"])
    consumed = store.get("job", job["id"])
    assert old["status"] == "rejected" and old["accepted_ref"] is None
    assert not store.maybe("blob", "accepted:" + old["id"])
    assert store.get("job", job["id"])["head"] == version
    assert not any(x["id"].startswith(old["id"] + ":") for x in store.records("operation", job["id"]))
    frozen = store.bytes(old["payload_ref"], job["id"])
    # This Continue exists only in this newly generated synthetic Store.
    continue_job(store, job, transport)
    reopened = Store(store.root)
    current = reopened.get("job", job["id"])
    assert current["status"] == "completed" and current["attempts"] == len(sends) == 2
    assert current["active_seconds"] >= consumed["active_seconds"]
    assert reopened.get("request", old["id"]) == old
    assert reopened.bytes(old["payload_ref"], job["id"]) == frozen
    assert all(reopened.get("attempt", x["id"]) == x for x in original["attempt"])
    assert sum(x["type"] == "request_continued" for x in reopened.events(job["id"], limit=10000)) == 1
    assert len(reopened.records("version", job["id"])) == 1
    check_delivery(reopened, job, version, image, source, tmp_path / "preserved-source.zip")


@pytest.mark.parametrize("boundary", ["settlement", "publication", "tool-checkpoint"])
def test_valid_runtime_interruption_reopens_without_resend_or_duplicate_effect(delivery, tmp_path, monkeypatch, boundary):
    store, job, version, image, source = delivery
    job = configure(store, job)
    content = Documents(store).version(job["id"], version)["content"]
    value = native("responses", tool("edit_document", {"base_version": version, "expected_head": version,
        "replace_blocks": content["blocks"], "claim": "complete"}, "save"),
        tool("report", {"state": "waiting", "message": "Saved complete source text and image."}, "report"))
    raw = b"".join(frames(value))
    sends = []

    def answer(request):
        sends.append(request.content)
        assert len(sends) == 1
        return httpx.Response(200, stream=Body([raw]))

    service = Nexus(store, lambda _: "fixture-only", httpx.MockTransport(answer))
    runtime = Runtime(store, service)
    with monkeypatch.context() as fault:
        if boundary == "settlement":
            put = store.put_tx
            def fail(db, category, key, owner, record):
                if category == "attempt" and record["status"] == "accepted":
                    raise RuntimeError("SC02 settlement interruption")
                return put(db, category, key, owner, record)
            fault.setattr(store, "put_tx", fail)
        elif boundary == "publication":
            send = service.send
            def fail(*args):
                send(*args)
                raise RuntimeError("SC02 publication interruption")
            fault.setattr(service, "send", fail)
        else:
            execute = runtime.dispatcher.execute
            def fail(*args):
                result = execute(*args)
                if args[2] == "edit_document":
                    assert result["ok"]
                    raise RuntimeError("SC02 tool-checkpoint interruption")
                return result
            fault.setattr(runtime.dispatcher, "execute", fail)
        try:
            with pytest.raises(RuntimeError, match="SC02"):
                runtime.run(job["id"])
        finally:
            runtime.close()
    request = store.records("request", job["id"])[0]
    stage = store.get("blob", "accepted:" + request["id"])
    consumed = store.get("job", job["id"])
    if boundary == "settlement":
        assert request["accepted_ref"] is None
        assert store.get("attempt", request["attempts"][0])["status"] == "in_flight"
    original_ops = store.records("operation", job["id"])
    reopened = Store(store.root)
    runtime = Runtime(reopened, Nexus(reopened, forbidden))
    try:
        runtime.run(job["id"])
    finally:
        runtime.close()
    current = reopened.get("job", job["id"])
    assert current["status"] == "waiting" and current["head"] != version
    assert current["attempts"] == len(sends) == 1
    assert current["active_seconds"] >= consumed["active_seconds"]
    assert len(reopened.records("version", job["id"])) == 2
    assert all(reopened.get("operation", x["id"]) == x for x in original_ops)
    attempt = reopened.get("attempt", request["attempts"][0])
    assert attempt["status"] == "accepted" and attempt["finished"] == stage["meta"]["received_at"]
    assert attempt["usage"] is None  # Fixture does not report usage.
    assert reopened.read_stream(job["id"], request["id"], attempt["id"])["data"] == raw
    assert reopened.bytes(request["payload_ref"], job["id"]) == sends[0]
    check_delivery(reopened, job, current["head"], image, source, tmp_path / "reopened-delivery.zip")
    # Compare decoded saved source pixels, in addition to exact archive bytes.
    with pymupdf.open(source) as pdf, zipfile.ZipFile(tmp_path / "reopened-delivery.zip") as archive:
        expected = pdf[1].get_pixmap(dpi=144)
        actual = pymupdf.Pixmap(archive.read(image["asset_path"]))
        assert (actual.width, actual.height, actual.samples) == (expected.width, expected.height, expected.samples)


@pytest.mark.parametrize("resolved", [False, True])
def test_incompatible_old_semantics_preserve_facts_and_stop(setup, monkeypatch, resolved):
    """Simulate the previous omission only in new evidence, never migrate originals."""
    import pdfmd.nexus as nexus_module
    import pdfmd.streaming as stream_module
    import tests.engine.execution.test_accepted_evidence_recovery as history_fixture
    from pdfmd.history import batch_reply
    from pdfmd.recovery import diagnose, resolve

    def old_frames(protocol, value):
        assert protocol == "responses"
        return frames(value, ("status", "incomplete"))

    with monkeypatch.context() as old:
        old.setattr(stream_module, "validate_response_item_state", lambda *args, **kwargs: None)
        old.setattr(nexus_module, "validate_response_item_state", lambda *args, **kwargs: None)
        old.setattr(history_fixture, "stream_frames", old_frames)
        store, job, key, reply, raw = history_fixture.historical(setup, monkeypatch, "responses", suffix=b"data: {")
        if resolved:
            diagnosis = diagnose(store.root, job["id"])
            assert diagnosis["eligible"]
            assert resolve(store, job["id"], key, diagnosis["basis"])["projection"] == "ready"
    before, consumed = snapshot(store, job["id"]), store.get("job", job["id"])
    originals = {x["ref"]: store.bytes(x["ref"], job["id"]) for x in before["blob"]}
    reopened = Store(store.root)
    if resolved:
        with pytest.raises(Conflict):
            batch_reply(reopened, job["id"], key)
        # Keep its owned identity/facts while blocking current semantic reuse.
        diagnosis = diagnose(store.root, job["id"])
        assert diagnosis["request"] == key and diagnosis["attempt"] == before["attempt"][0]["id"]
        assert not diagnosis["eligible"] and diagnosis["projection"] == "blocked"
        assert "boundary" in " ".join(diagnosis["reasons"])
        with pytest.raises(Conflict):
            resolve(reopened, job["id"], key, "old click")
    else:
        with pytest.raises(StopRun) as stopped:
            Nexus(reopened, forbidden).reconcile(job["id"], key)
        assert stopped.value.reason == "accepted_evidence_conflict"
        assert not diagnose(store.root, job["id"])["eligible"]
    assert snapshot(reopened, job["id"]) == before
    assert reopened.get("job", job["id"]) == consumed
    assert all(reopened.bytes(ref, job["id"]) == data for ref, data in originals.items())
    assert reopened.bytes(reply["stream_ref"], job["id"]) == raw
