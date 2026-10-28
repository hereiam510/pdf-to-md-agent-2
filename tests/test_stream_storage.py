"""Durable stream evidence and scoped SQLite lifecycle; no provider requests."""
import base64
from copy import deepcopy
from hashlib import sha256
import shutil
import sqlite3
import threading

import pytest

from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus, StopRun
from pdfmd.storage import Conflict, Store, encode, uid
from test_request_deadline import Body, Clock
from test_stream_progress import PROTOCOLS, delta, ending, frozen_stream


def registered_stream(setup, *, checkpoint=1, attempt=None, request="evidence-request"):
    store, job = setup
    attempt = attempt or uid()
    old = store.maybe("request", request)
    attempts = [*(old["attempts"] if old else []), attempt]
    store.put("request", request, job["id"], {
        "id": request, "job": job["id"], "attempts": attempts,
        "status": "unknown", "accepted_ref": None,
        "replay_policy": {"replay_unknown": False, "max_attempts_per_request": 2}})
    store.put("attempt", attempt, job["id"], {
        "id": attempt, "request": request, "status": "unknown", "usage": None})
    # Individual chunks can split source characters; their raw-byte view remains exact.
    letter = "繁".encode()
    parts = [b"Retain ", letter[:1], letter[1:] + b" 25 mg."]
    blobs = [store.blob(job["id"], "stream_chunk", part,
        {"request": request, "attempt": attempt, "index": i, "elapsed_seconds": float(i)},
        key=f"stream:{attempt}:{i}") for i, part in enumerate(parts)]
    prefix = b"".join(parts[:checkpoint])
    receipt = {"request": request, "attempt": attempt,
        "cursor": {"format": "ordered_chunks_v1", "chunk_count": checkpoint,
            "bytes": len(prefix), "sha256": sha256(prefix).hexdigest(),
            "last_chunk_ref": blobs[checkpoint - 1]["ref"] if checkpoint else None},
        "transport": {"received_body_bytes": len(prefix), "protocol_complete": False}}
    store.put("stream_receive", attempt, job["id"], receipt)
    return store, job["id"], request, attempt, parts, blobs, receipt


def replace_record(store, kind, key, value, *, job=None):
    """Controlled corrupt catalog fixture, never a production migration."""
    with store.transaction() as db:
        db.execute("UPDATE records SET data=? WHERE kind=? AND id=?", (encode(value).decode(), kind, key))
        if job is not None:
            db.execute("UPDATE records SET job=? WHERE kind=? AND id=?", (job, kind, key))


def test_durable_suffix_recovery_is_read_only_and_preserves_raw_access(setup):
    store, job, request, attempt, parts, blobs, receipt = registered_stream(setup)
    snapshot = {kind: store.records(kind, job) for kind in ["request", "attempt", "stream_receive", "blob"]}
    recovered = Store(store.root).read_stream(job, request, attempt)
    assert recovered["data"] == b"".join(parts)
    assert recovered["chunk_count"] == 3 and recovered["checkpoint_count"] == 1
    assert recovered["received_bytes"] == len(b"".join(parts))
    assert recovered["chunks"] == [blob["ref"] for blob in blobs]
    assert recovered["sha256"] == sha256(b"".join(parts)).hexdigest()
    raw = Evidence(store).read(job, blobs[1]["ref"], view="raw")
    assert base64.b64decode(raw["data"]) == parts[1] and raw["complete"]
    with pytest.raises(StopRun) as stopped:
        Nexus(Store(store.root), lambda _: pytest.fail("Evidence recovery must not send")).send(job, request)
    assert stopped.value.reason == "unknown_outcome"
    assert {kind: store.records(kind, job) for kind in snapshot} == snapshot
    assert not store.records("operation", job)


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_fragmented_native_receive_uses_fixed_field_cursor_and_exact_evidence(setup, protocol, monkeypatch):
    text = "Keep 25 mg. 繁體 μg 🩺."
    raw = delta(protocol, text) + ending(protocol, text)
    parts = [raw[i:i + 11] for i in range(0, len(raw), 11)]
    clock = Clock()
    store, job, nexus, request, seen = frozen_stream(
        setup, protocol, Body(list(enumerate(parts, 1)), clock=clock), clock)
    receipts = []
    original = store.put
    def observe(kind, key, owner, value):
        if kind == "stream_receive":
            receipts.append(deepcopy(value))
        return original(kind, key, owner, value)
    monkeypatch.setattr(store, "put", observe)
    accepted = nexus.send(job["id"], request["id"])
    attempt = store.records("attempt", job["id"])[0]["id"]
    expected_fields = {"format", "chunk_count", "bytes", "sha256", "last_chunk_ref"}
    assert receipts and all(set(r["cursor"]) == expected_fields and "chunks" not in r for r in receipts)
    assert receipts[-1]["cursor"]["chunk_count"] == len(parts)
    assert receipts[-1]["cursor"]["bytes"] == len(raw)
    assert receipts[-1]["cursor"]["sha256"] == sha256(raw).hexdigest()
    durable = store.read_stream(job["id"], request["id"], attempt)
    assert durable["data"] == raw == store.bytes(accepted["stream_ref"], job["id"])
    assert durable["checkpoint_count"] == durable["chunk_count"] == len(parts)
    assert accepted["text"] == text and accepted["native_ref"] != accepted["stream_ref"]
    assert len(seen) == 1


@pytest.mark.parametrize("damage", [
    "missing_file", "corrupt_file", "missing_middle", "wrong_request", "wrong_attempt",
    "duplicate_index", "wrong_reference", "wrong_job", "checkpoint_ahead", "checkpoint_digest",
    "aggregate_bytes", "aggregate_order", "request_owner", "attempt_owner", "checkpoint_owner",
])
def test_inconsistent_evidence_never_becomes_a_complete_sequence(setup, damage):
    store, job, request, attempt, parts, blobs, receipt = registered_stream(setup, checkpoint=3)
    target = store.root / "objects" / blobs[1]["sha256"]
    if damage == "missing_file":
        target.unlink()
    elif damage == "corrupt_file":
        target.write_bytes(b"different")
    elif damage == "missing_middle":
        with store.transaction() as db:
            db.execute("DELETE FROM records WHERE kind='blob' AND id=?", (blobs[1]["ref"],))
    elif damage in {"wrong_request", "wrong_attempt", "duplicate_index", "wrong_reference", "wrong_job"}:
        value = deepcopy(blobs[1])
        if damage == "wrong_request": value["meta"]["request"] = "another-request"
        elif damage == "wrong_attempt": value["meta"]["attempt"] = uid()
        elif damage == "duplicate_index": value["meta"]["index"] = 0
        elif damage == "wrong_reference": value["ref"] = blobs[0]["ref"]
        else: value["job"] = "another-job"
        replace_record(store, "blob", blobs[1]["ref"], value)
    elif damage in {"request_owner", "attempt_owner", "checkpoint_owner"}:
        kind, key = {"request_owner": ("request", request),
            "attempt_owner": ("attempt", attempt), "checkpoint_owner": ("stream_receive", attempt)}[damage]
        replace_record(store, kind, key, store.get(kind, key), job="another-job")
    elif damage in {"checkpoint_ahead", "checkpoint_digest"}:
        value = deepcopy(receipt)
        if damage == "checkpoint_ahead": value["cursor"]["chunk_count"] = 4
        else: value["cursor"]["sha256"] = sha256(b"wrong").hexdigest()
        replace_record(store, "stream_receive", attempt, value)
    else:
        refs = [blob["ref"] for blob in blobs]
        store.blob(job, "raw_stream", b"wrong" if damage == "aggregate_bytes" else b"".join(parts),
            {"request": request, "attempt": attempt,
                "chunks": list(reversed(refs)) if damage == "aggregate_order" else refs},
            key=f"raw-stream:{attempt}")
    with pytest.raises(ValueError):
        Store(store.root).read_stream(job, request, attempt)
    assert store.get("request", request)["accepted_ref"] is None
    assert not store.records("operation", job)


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_reopen_accepted_stream_rejects_missing_constituent_before_any_send(setup, protocol):
    clock = Clock()
    store, job, nexus, request, _ = frozen_stream(setup, protocol,
        Body([(1, delta(protocol, "Done")), (2, ending(protocol, "Done"))], clock=clock), clock)
    accepted = nexus.send(job["id"], request["id"])
    saved_acceptance = store.get("request", request["id"])["accepted_ref"]
    attempt = store.records("attempt", job["id"])[0]["id"]
    chunk = store.get("blob", f"stream:{attempt}:0", job=job["id"])
    (store.root / "objects" / chunk["sha256"]).unlink()
    with pytest.raises(ValueError, match="missing"):
        Nexus(Store(store.root), lambda _: pytest.fail("Saved evidence cannot authorize a new send")).send(job["id"], request["id"])
    assert len(store.records("attempt", job["id"])) == 1
    assert store.get("request", request["id"])["accepted_ref"] == saved_acceptance
    assert not store.records("operation", job["id"])


def test_same_request_attempts_are_independent_and_legacy_copy_is_readable(setup, tmp_path):
    store, job, request, first, first_parts, first_blobs, first_receipt = registered_stream(setup)
    _, _, _, second, second_parts, second_blobs, _ = registered_stream(setup, checkpoint=2, request=request)
    assert first != second
    assert store.read_stream(job, request, first)["chunks"] == [b["ref"] for b in first_blobs]
    assert store.read_stream(job, request, second)["chunks"] == [b["ref"] for b in second_blobs]
    assert store.read_stream(job, request, first)["data"] == b"".join(first_parts)
    assert store.read_stream(job, request, second)["data"] == b"".join(second_parts)
    original_records = store.records("blob", job)
    copy_root = tmp_path / "legacy-copy"
    shutil.copytree(store.root, copy_root)
    copied = Store(copy_root)
    legacy = {key: value for key, value in first_receipt.items() if key != "cursor"}
    legacy["chunks"] = [first_blobs[0]["ref"]]
    copied.put("stream_receive", first, job, legacy)
    assert copied.read_stream(job, request, first)["data"] == b"".join(first_parts)
    assert copied.read_stream(job, request, first)["checkpoint_count"] == 1
    assert copied.get("stream_receive", first) == legacy
    assert store.get("stream_receive", first) == first_receipt
    assert store.records("blob", job) == original_records == copied.records("blob", job)
    legacy["chunks"] = [first_blobs[1]["ref"]]
    copied.put("stream_receive", first, job, legacy)
    with pytest.raises(ValueError, match="order"):
        copied.read_stream(job, request, first)


def test_connection_scope_reads_external_stop_and_is_thread_confined(setup):
    store, job = setup
    with store.connection_scope():
        owner = store._connections.active
        assert owner.execute("PRAGMA synchronous").fetchone()[0] == 2
        assert not store.get("job", job["id"])["cancel_requested"]
        results, errors = [], []
        def stop():
            try:
                # Same Store in another thread must own a separate handle.
                with store.connection_scope():
                    results.append(store._connections.active is not owner)
                    Store(store.root).update_job(job["id"], cancel_requested=True)
                    results.append(store.get("job", job["id"])["cancel_requested"])
            except BaseException as exc:
                errors.append(exc)
        thread = threading.Thread(target=stop)
        thread.start()
        thread.join(timeout=5)
        assert not thread.is_alive() and not errors and results == [True, True]
        assert store.get("job", job["id"])["cancel_requested"]
        assert not owner.in_transaction
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        owner.execute("SELECT 1")
    assert store.get("job", job["id"])["cancel_requested"]


def test_scoped_transaction_rollback_nested_owner_and_close(setup):
    store, job = setup
    class InjectedFailure(Exception):
        pass
    with pytest.raises(InjectedFailure):
        with store.connection_scope():
            owner = store._connections.active
            with store.connection_scope():
                assert store._connections.active is owner
            assert owner.execute("SELECT 1").fetchone()[0] == 1
            with store.transaction() as db:
                store.put_tx(db, "test", "outer", job["id"], {"retained": True})
                with pytest.raises(Conflict, match="Nested"):
                    with store.transaction():
                        pytest.fail("Nested transaction must not enter")
                assert db.in_transaction
            assert store.get("test", "outer")["retained"]
            with pytest.raises(InjectedFailure):
                with store.transaction() as db:
                    store.put_tx(db, "test", "rolled-back", job["id"], {"retained": False})
                    raise InjectedFailure()
            assert store.maybe("test", "rolled-back") is None and not owner.in_transaction
            store.put("test", "later", job["id"], {"committed": True})
            raise InjectedFailure()
    assert getattr(store._connections, "active", None) is None
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        owner.execute("SELECT 1")
    assert store.get("test", "outer") == {"retained": True}
    assert store.get("test", "later") == {"committed": True}
    assert store.maybe("test", "rolled-back") is None
