"""Persistent acceptance publication and historical pointer/attempt repair."""
from copy import deepcopy

import httpx
import pytest

from pdfmd.nexus import Nexus, StopRun, make_payload
from pdfmd.schema import Route
from pdfmd.storage import Store
from test_context_admission import protocol_job
from test_response_repairs import native
from test_streaming_delivery import WAIT, stream_frames
from test_stream_progress import delta
from test_continuation import delivery, check_delivery


PROTOCOLS = ["chat_completions", "responses"]


def forbidden(_):
    pytest.fail("Local acceptance recovery must not obtain credentials or send")


def prepare(setup, protocol, streaming, monkeypatch, *, usage=True, kind="normal", unknown_first=False):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    route = Route.model_validate({**job["route"], "wait_policy": WAIT if streaming else None})
    job = store.update_job(job["id"], route=route.model_dump())
    if unknown_first:
        job = store.update_job(job["id"], limits={**job["limits"], "replay_unknown": True, "max_attempts_per_request": 2})
    sends, inflight = [], []
    original = store.put_tx

    def capture(db, category, key, owner, value):
        if category == "attempt" and value["status"] == "in_flight":
            inflight.append(deepcopy(value))
        return original(db, category, key, owner, value)

    monkeypatch.setattr(store, "put_tx", capture)
    value = native(protocol, text="Preserve the complete reply: 25 mg. 完整保留。")
    value["usage"] = {"input_tokens": 123, "output_tokens": 17} if usage else None

    def respond(request):
        sends.append(request.content)
        if unknown_first and len(sends) == 1 and not streaming:
            raise httpx.ReadError("Synthetic unknown first outcome")
        if streaming:
            # This fixture supplies known usage in its terminal native assembly.
            frames = stream_frames(protocol, value)
            if unknown_first and len(sends) == 1:
                frames = [delta(protocol, "Old unfinished evidence")]
            if not usage:
                frames = [frame.replace(b'"usage": {"prompt_tokens": 100, "completion_tokens": 50}', b'"usage": null')
                          .replace(b'"usage": {"input_tokens": 100, "output_tokens": 50}', b'"usage": null') for frame in frames]
            class Body(httpx.AsyncByteStream):
                async def __aiter__(self):
                    for frame in frames:
                        yield frame
            return httpx.Response(200, stream=Body())
        return httpx.Response(200, json=value)

    nexus = Nexus(store, lambda _: "synthetic-only", httpx.MockTransport(respond))
    request = nexus.freeze(job["id"], "persistent-settlement", make_payload(route, "Offline fixture", [], []), kind, {})
    return store, job, nexus, request, sends, inflight


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("streaming", [False, True])
def test_existing_pointer_repairs_persisted_inflight_attempt_without_send(setup, protocol, streaming, monkeypatch):
    store, job, nexus, request, sends, inflight = prepare(setup, protocol, streaming, monkeypatch)
    accepted = nexus.send(job["id"], request["id"])
    # Recreate exactly the old separate-commit boundary, in an isolated real
    # SQLite store: accepted pointer committed; original in-flight attempt left.
    old_attempt = inflight[0]
    store.put("attempt", old_attempt["id"], job["id"], old_attempt)
    before_request = store.get("request", request["id"])
    before_job = store.get("job", job["id"])
    frozen = store.bytes(request["payload_ref"], job["id"])
    blobs = store.records("blob", job["id"])
    stage = store.get("blob", before_request["accepted_ref"])
    saved_bytes = {blob["ref"]: store.bytes(blob["ref"], job["id"]) for blob in blobs}

    reopened = Store(store.root)
    recovered = Nexus(reopened, forbidden)
    recovered.reconcile(job["id"], request["id"])
    settled = reopened.get("attempt", old_attempt["id"])
    assert settled["status"] == "accepted"
    assert settled["usage"] == accepted["usage"]
    assert settled["finished"] == stage["meta"]["received_at"]
    assert settled["started"] == old_attempt["started"]
    for _ in range(2):
        assert recovered.send(job["id"], request["id"]) == accepted
        recovered.reconcile(job["id"], request["id"])
        assert reopened.get("attempt", old_attempt["id"]) == settled
    assert reopened.get("request", request["id"]) == before_request
    assert reopened.get("job", job["id"]) == before_job
    assert reopened.bytes(request["payload_ref"], job["id"]) == frozen
    assert reopened.records("blob", job["id"]) == blobs
    assert all(reopened.bytes(ref, job["id"]) == raw for ref, raw in saved_bytes.items())
    assert len(sends) == 1 and len(reopened.records("attempt", job["id"])) == 1
    assert not reopened.records("operation", job["id"])


@pytest.mark.parametrize("entry", ["send", "reconcile"])
@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("streaming", [False, True])
def test_acceptance_metadata_failure_rolls_back_both_records_then_recovers(setup, protocol, entry, streaming, monkeypatch):
    store, job, nexus, request, sends, inflight = prepare(setup, protocol, streaming, monkeypatch)
    original = store.put_tx
    reached = []

    def fail_attempt(db, category, key, owner, value):
        if category == "attempt" and value["status"] == "accepted":
            # Fail after the request update has executed, before commit.
            reached.append(True)
            raise RuntimeError("controlled settlement write failure")
        return original(db, category, key, owner, value)

    monkeypatch.setattr(store, "put_tx", fail_attempt)
    with pytest.raises(RuntimeError, match="controlled settlement"):
        nexus.send(job["id"], request["id"])
    staged = store.get("blob", "accepted:" + request["id"])
    if entry == "reconcile":
        # A second failure directly through reopen/reconcile must also roll back.
        with pytest.raises(RuntimeError, match="controlled settlement"):
            nexus.reconcile(job["id"], request["id"])
    assert len(reached) == (2 if entry == "reconcile" else 1)
    pending = store.get("request", request["id"])
    assert pending["accepted_ref"] is None and pending["status"] == "in_flight"
    assert store.get("attempt", inflight[0]["id"]) == inflight[0]
    before_job = store.get("job", job["id"])
    monkeypatch.setattr(store, "put_tx", original)
    reopened = Store(store.root)
    service = Nexus(reopened, forbidden)
    accepted = service.send(job["id"], request["id"])
    assert accepted == reopened.json(staged["ref"], job["id"])
    attempt = reopened.get("attempt", inflight[0]["id"])
    assert attempt["status"] == "accepted" and attempt["usage"] == accepted["usage"]
    assert attempt["finished"] == staged["meta"]["received_at"]
    assert reopened.get("job", job["id"]) == before_job and len(sends) == 1


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("streaming", [False, True])
def test_unknown_usage_and_legacy_diagnostics_remain_unknown_with_stable_finish(setup, protocol, streaming, monkeypatch):
    store, job, nexus, request, sends, inflight = prepare(setup, protocol, streaming, monkeypatch, usage=False, kind="compaction")
    accepted = nexus.send(job["id"], request["id"])
    assert accepted["usage"] is None
    stage = store.get("blob", "accepted:" + request["id"])
    stage["meta"].pop("transport")  # Historical staging did not save transport.
    store.put("blob", stage["ref"], job["id"], stage)
    prior = {**inflight[0], "finished": stage["meta"]["received_at"] + 0.25,
             "remote_cancelled": None, "diagnostic_note": "Keep this field."}
    store.put("attempt", prior["id"], job["id"], prior)
    reopened = Store(store.root)
    service = Nexus(reopened, forbidden)
    assert service.send(job["id"], request["id"]) == accepted
    settled = reopened.get("attempt", prior["id"])
    assert settled["usage"] is None and settled["finished"] == prior["finished"]
    assert settled["remote_cancelled"] is None and settled["diagnostic_note"] == prior["diagnostic_note"]
    if streaming:
        assert settled["http_status"] == 200 and settled["transport"]["settled"]
    else:
        assert settled.get("http_status") is None and settled["transport"] == prior["transport"]
    original = reopened.put_tx
    def no_republication(db, category, key, owner, value):
        assert category not in {"request", "attempt"}, "Complete re-entry must not republish metadata"
        return original(db, category, key, owner, value)
    monkeypatch.setattr(reopened, "put_tx", no_republication)
    for _ in range(2):
        service.reconcile(job["id"], request["id"])
        assert service.send(job["id"], request["id"]) == accepted
    assert reopened.get("attempt", prior["id"]) == settled and len(sends) == 1


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("streaming", [False, True])
def test_only_staging_owned_attempt_is_settled_with_earlier_unknown_preserved(setup, protocol, streaming, monkeypatch):
    store, job, nexus, request, sends, inflight = prepare(setup, protocol, streaming, monkeypatch, unknown_first=True)
    with pytest.raises(StopRun):
        nexus.send(job["id"], request["id"])
    unknown = store.get("attempt", inflight[0]["id"])
    frozen = store.bytes(request["payload_ref"], job["id"])
    old_blobs = store.records("blob", job["id"])
    accepted = nexus.send(job["id"], request["id"])
    target = inflight[1]
    store.put("attempt", target["id"], job["id"], target)
    consumed = store.get("job", job["id"])
    reopened = Store(store.root)
    service = Nexus(reopened, forbidden)
    assert service.send(job["id"], request["id"]) == accepted
    assert reopened.get("attempt", target["id"])["status"] == "accepted"
    assert reopened.get("attempt", target["id"])["usage"] == accepted["usage"]
    assert reopened.get("attempt", unknown["id"]) == unknown
    assert unknown["usage"] is None and unknown["remote_cancelled"] is None
    assert reopened.get("job", job["id"]) == consumed and consumed["attempts"] == 2
    assert reopened.bytes(request["payload_ref"], job["id"]) == frozen
    assert all(reopened.get("blob", b["ref"]) == b and reopened.bytes(b["ref"], job["id"]) for b in old_blobs)
    assert len(sends) == 2 and sends[0] == sends[1] == frozen


@pytest.mark.parametrize("contradiction", ["pointer", "attempt_request", "attempt_member", "attempt_usage",
    "attempt_stream", "native_owner", "native_bytes", "partial", "stage_usage", "row_owner"])
def test_contradictory_acceptance_is_rejected_without_metadata_mutation(setup, monkeypatch, contradiction):
    store, job, nexus, request, sends, inflight = prepare(setup, "responses", True, monkeypatch)
    accepted = nexus.send(job["id"], request["id"])
    current = store.get("request", request["id"])
    attempt = inflight[0]
    store.put("attempt", attempt["id"], job["id"], attempt)
    if contradiction == "pointer":
        store.put("request", request["id"], job["id"], {**current, "accepted_ref": accepted["native_ref"]})
    elif contradiction == "attempt_request":
        store.put("attempt", attempt["id"], job["id"], {**attempt, "request": "another-request"})
    elif contradiction == "attempt_member":
        store.put("request", request["id"], job["id"], {**current, "attempts": []})
    elif contradiction == "attempt_usage":
        store.put("attempt", attempt["id"], job["id"], {**attempt, "usage": {"input_tokens": 999}})
    elif contradiction == "attempt_stream":
        store.put("attempt", attempt["id"], job["id"], {**attempt, "stream_ref": "another-stream"})
    elif contradiction in {"native_owner", "partial"}:
        record = store.get("blob", accepted["native_ref"] if contradiction == "native_owner" else accepted["stream_ref"])
        record["meta"]["attempt" if contradiction == "native_owner" else "chunk_validation"] = "another-attempt" if contradiction == "native_owner" else "registration_only"
        store.put("blob", record["ref"], job["id"], record)
    elif contradiction in {"native_bytes", "stage_usage"}:
        ref = accepted["native_ref"] if contradiction == "native_bytes" else current["accepted_ref"]
        record = store.get("blob", ref)
        content = store.json(ref, job["id"])
        content["usage"] = {"input_tokens": 999}
        # New immutable bytes, but deliberately tampered catalog linkage in
        # this isolated store. Both hash-valid content and provenance matter.
        replacement = store.blob(job["id"], record["kind"], content, record["meta"])
        store.put("blob", ref, job["id"], {**replacement, "ref": ref})
    else:
        with store.transaction() as db:
            db.execute("UPDATE records SET job='another-job' WHERE kind='attempt' AND id=?", (attempt["id"],))
    before = {kind: store.records(kind) for kind in ("request", "attempt", "blob", "job", "operation", "stream_receive")}
    reopened = Store(store.root)
    with pytest.raises(ValueError):
        Nexus(reopened, forbidden).send(job["id"], request["id"])
    assert {kind: reopened.records(kind) for kind in before} == before
    assert len(sends) == 1 and not reopened.records("operation", job["id"])


@pytest.mark.parametrize("change", ["unrelated", "route", "stage", "pointer", "receipt"])
def test_publication_rechecks_current_state_and_preserves_unrelated_fields(setup, monkeypatch, change):
    from contextlib import contextmanager
    store, job, nexus, request, sends, inflight = prepare(setup, "chat_completions", True, monkeypatch)
    nexus.send(job["id"], request["id"])
    store.put("attempt", inflight[0]["id"], job["id"], inflight[0])
    original = store.transaction
    external = Store(store.root)
    expected = {}

    @contextmanager
    def race():
        # Runs after evidence preparation and before BEGIN IMMEDIATE.
        current = external.get("request", request["id"])
        if change == "unrelated":
            external.put("request", request["id"], job["id"], {**current, "diagnostic_note": "new request field"})
            attempt = external.get("attempt", inflight[0]["id"])
            external.put("attempt", attempt["id"], job["id"], {**attempt, "diagnostic_note": "new attempt field"})
        elif change in {"route", "pointer"}:
            current["route" if change == "route" else "accepted_ref"] = {**current["route"], "model": "changed"} if change == "route" else "another-pointer"
            external.put("request", request["id"], job["id"], current)
        elif change == "stage":
            stage = external.get("blob", current["accepted_ref"])
            stage["meta"]["received_at"] += 1
            external.put("blob", stage["ref"], job["id"], stage)
        else:
            receipt = external.get("stream_receive", inflight[0]["id"])
            receipt["transport"]["cleanup_complete"] = False
            external.put("stream_receive", inflight[0]["id"], job["id"], receipt)
        expected.update({kind: external.records(kind) for kind in ("request", "attempt", "blob", "stream_receive")})
        with original() as db:
            yield db
    monkeypatch.setattr(store, "transaction", race)
    if change == "unrelated":
        nexus.reconcile(job["id"], request["id"])
        assert store.get("request", request["id"])["diagnostic_note"] == "new request field"
        assert store.get("attempt", inflight[0]["id"])["diagnostic_note"] == "new attempt field"
    else:
        with pytest.raises(ValueError):
            nexus.reconcile(job["id"], request["id"])
        assert {kind: store.records(kind) for kind in expected} == expected
    assert len(sends) == 1


@pytest.mark.parametrize("protocol,streaming", [("chat_completions", False), ("responses", True)])
def test_runtime_repairs_old_pointer_then_replays_committed_tool_without_new_effect(delivery, tmp_path, monkeypatch, protocol, streaming):
    import json
    from pdfmd.documents import Documents
    from pdfmd.runtime import Runtime
    from test_runtime import tool
    store, initial, version, image, source = delivery
    job = protocol_job(store, initial, protocol)
    store.update_job(job["id"], route={**job["route"], "wait_policy": WAIT if streaming else None})
    content = Documents(store).version(job["id"], version)["content"]
    value = native(protocol, tool("edit_document", {"base_version": version, "expected_head": version,
        "replace_blocks": content["blocks"], "claim": "complete"}, "save"),
        tool("report", {"state": "waiting", "message": "Preserved all source content and figure."}, "report"))
    value["usage"] = {"input_tokens": 123, "output_tokens": 17}
    sends, inflight = [], []
    original = store.put_tx
    def capture(db, category, key, owner, record):
        if category == "attempt" and record["status"] == "in_flight":
            inflight.append(deepcopy(record))
        return original(db, category, key, owner, record)
    monkeypatch.setattr(store, "put_tx", capture)
    def respond(request):
        sends.append(request.content)
        if streaming:
            class Body(httpx.AsyncByteStream):
                async def __aiter__(self):
                    for frame in stream_frames(protocol, value):
                        yield frame
            return httpx.Response(200, stream=Body())
        return httpx.Response(200, json=value)
    service = Nexus(store, lambda _: "synthetic-only", httpx.MockTransport(respond))
    send = service.send
    def old_gap(owner, key):
        send(owner, key)
        store.put("attempt", inflight[0]["id"], owner, inflight[0])
        raise RuntimeError("historical pointer/attempt gap before graph checkpoint")
    monkeypatch.setattr(service, "send", old_gap)
    runtime = Runtime(store, service)
    try:
        with pytest.raises(RuntimeError, match="historical pointer"):
            runtime.run(job["id"])
    finally:
        runtime.close()
    request = store.records("request", job["id"])[0]
    accepted = store.json(request["accepted_ref"], job["id"])
    stage = store.get("blob", request["accepted_ref"])
    frozen = store.bytes(request["payload_ref"], job["id"])
    known_active = store.get("job", job["id"])["active_seconds"]
    seed_operation = store.get("operation", "seed")

    reopened = Store(store.root)
    runtime = Runtime(reopened, Nexus(reopened, forbidden))
    execute = runtime.dispatcher.execute
    effects = []
    def commit_gap(*args):
        result = execute(*args)
        if args[2] == "edit_document":
            effects.append(args[1])
            raise RuntimeError("tool committed before graph checkpoint")
        return result
    monkeypatch.setattr(runtime.dispatcher, "execute", commit_gap)
    try:
        with pytest.raises(RuntimeError, match="tool committed"):
            runtime.run(job["id"])
    finally:
        runtime.close()
    saved = reopened.get("job", job["id"])["head"]
    assert saved != version
    edit_receipt = reopened.get("operation", effects[0])
    settled = reopened.get("attempt", inflight[0]["id"])
    assert settled["status"] == "accepted" and settled["usage"] == accepted["usage"]
    assert settled["finished"] == stage["meta"]["received_at"]

    final_store = Store(store.root)
    final_runtime = Runtime(final_store, Nexus(final_store, forbidden))
    try:
        final_runtime.run(job["id"])
    finally:
        final_runtime.close()
    current = final_store.get("job", job["id"])
    assert current["status"] == "waiting" and current["head"] == saved
    assert current["attempts"] == 1 and current["active_seconds"] >= known_active
    assert len(sends) == len(final_store.records("attempt", job["id"])) == 1
    assert len(final_store.records("version", job["id"])) == 2
    assert final_store.get("operation", effects[0]) == edit_receipt
    assert final_store.get("operation", "seed") == seed_operation
    assert final_store.get("attempt", inflight[0]["id"]) == settled
    assert final_store.bytes(request["payload_ref"], job["id"]) == frozen
    check_delivery(final_store, job, saved, image, source, tmp_path / "delivery.zip")
    assert json.loads((Documents(final_store).root / saved / "document.json").read_text(encoding="utf-8"))["content"] == content


@pytest.mark.parametrize("entry,protocol,streaming,exit_after", [("send", "chat_completions", False, "request"),
    ("send", "chat_completions", False, "attempt"), ("reconcile", "responses", True, "request")])
def test_own_process_abrupt_exit_during_publication_rolls_back(setup, monkeypatch, tmp_path, entry, protocol, streaming, exit_after):
    import json
    import subprocess
    import sys
    store, job, nexus, request, sends, inflight = prepare(setup, protocol, streaming, monkeypatch)
    if entry == "reconcile":
        nexus.send(job["id"], request["id"])
        current = store.get("request", request["id"])
        store.put("request", request["id"], job["id"], {**current, "status": "in_flight", "accepted_ref": None})
        store.put("attempt", inflight[0]["id"], job["id"], inflight[0])
    marker = tmp_path / "child-interruption.json"
    code = '''
import json, os, sys
from pathlib import Path
import httpx
from pdfmd.nexus import Nexus
from pdfmd.storage import Store
root, job, key, entry, marker, value, exit_after = sys.argv[1:]
store = Store(root)
original = store.put_tx
def interrupt(db, kind, identity, owner, record):
    original(db, kind, identity, owner, record)
    if kind == exit_after and record.get("status") == "accepted":
        Path(marker).write_text(json.dumps({"entry": entry, "exit_after": exit_after, "in_transaction": db.in_transaction, "pid": os.getpid()}))
        os._exit(79)  # Own isolated child only: bypass finally/rollback/close.
store.put_tx = interrupt
service = Nexus(store, lambda _: "synthetic-only", httpx.MockTransport(lambda _: httpx.Response(200, json=json.loads(value))))
getattr(service, entry)(job, key)
'''
    completed = subprocess.run([sys.executable, "-c", code, str(store.root), job["id"], request["id"], entry,
        str(marker), json.dumps(native(protocol, text="Complete synthetic reply.")), exit_after], capture_output=True, text=True, timeout=30)
    assert completed.returncode == 79, completed.stderr
    assert json.loads(marker.read_text())["in_transaction"] is True
    reopened = Store(store.root)
    pending = reopened.get("request", request["id"])
    assert pending["accepted_ref"] is None and pending["status"] == "in_flight"
    attempt = reopened.get("attempt", pending["attempts"][0])
    assert attempt["status"] == "in_flight" and attempt["usage"] is None and "finished" not in attempt
    staging = reopened.get("blob", "accepted:" + request["id"])
    before = reopened.get("job", job["id"])
    accepted = Nexus(reopened, forbidden).send(job["id"], request["id"])
    settled = reopened.get("attempt", attempt["id"])
    assert settled["status"] == "accepted" and settled["usage"] == accepted["usage"]
    assert settled["finished"] == staging["meta"]["received_at"]
    assert reopened.get("job", job["id"]) == before and before["attempts"] == 1


def test_recovery_keeps_file_and_decoder_validation_outside_write_transaction(setup, monkeypatch):
    from contextlib import contextmanager
    store, job, nexus, request, sends, inflight = prepare(setup, "responses", True, monkeypatch)
    nexus.send(job["id"], request["id"])
    store.put("attempt", inflight[0]["id"], job["id"], inflight[0])
    transaction, read_bytes, read_stream = store.transaction, store.bytes, store.read_stream
    writing, checked = [], []
    @contextmanager
    def tracked_transaction():
        with transaction() as db:
            writing.append(True)
            try:
                yield db
            finally:
                writing.pop()
    def checked_bytes(*args):
        assert not writing, "File reads must not extend the SQLite write transaction"
        checked.append("bytes")
        return read_bytes(*args)
    def checked_stream(*args):
        assert not writing, "Stream reconstruction must precede metadata publication"
        checked.append("stream")
        return read_stream(*args)
    monkeypatch.setattr(store, "transaction", tracked_transaction)
    monkeypatch.setattr(store, "bytes", checked_bytes)
    monkeypatch.setattr(store, "read_stream", checked_stream)
    nexus.reconcile(job["id"], request["id"])
    assert "stream" in checked and "bytes" in checked and len(sends) == 1
