"""Partial raw preservation is distinct from complete stream validation."""
from hashlib import sha256

import httpx
import pytest

from pdfmd.nexus import Nexus, StopRun
from pdfmd.storage import Store
from test_request_deadline import Body, Clock
from test_stream_progress import PROTOCOLS, delta, ending, frozen_stream


def retained_attempt(store, job, request):
    pending = store.get("request", request["id"])
    assert pending["accepted_ref"] is None
    assert not store.maybe("blob", "accepted:" + request["id"])
    attempts = store.records("attempt", job["id"])
    assert len(attempts) == 1 and attempts[0]["usage"] is None
    assert not store.records("operation", job["id"])
    return attempts[0]


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("stop", [False, True])
def test_partial_stop_or_disconnect_preserves_raw_without_claiming_reconstruction(setup, protocol, stop):
    store, initial = setup
    parts = [delta(protocol, "First retained 25 mg. "), delta(protocol, "Second retained 繁體中文.")]
    class Interrupted(Body):
        async def __aiter__(self):
            yield parts[0]
            if stop:
                store.update_job(initial["id"], cancel_requested=True)
            yield parts[1]
            raise httpx.ReadError("synthetic disconnect")
    body, clock = Interrupted([]), Clock()
    store, job, nexus, request, seen = frozen_stream(setup, protocol, body, clock)
    frozen = store.bytes(request["payload_ref"], job["id"])
    with pytest.raises(StopRun) as failure:
        nexus.send(job["id"], request["id"])
    assert failure.value.reason == ("cancelled" if stop else "unknown_outcome")
    attempt = retained_attempt(store, job, request)
    assert attempt["remote_cancelled"] is None and body.closed
    raw = store.get("blob", attempt["stream_ref"])
    assert raw["meta"]["chunk_validation"] == "registration_only"
    assert raw["meta"]["complete_protocol"] is False
    assert store.bytes(raw["ref"], job["id"]) == b"".join(parts)
    verified = Store(store.root).read_stream(job["id"], request["id"], attempt["id"])
    assert verified["data"] == b"".join(parts) and verified["chunk_count"] == 2
    assert verified["sha256"] == sha256(b"".join(parts)).hexdigest()
    assert store.bytes(request["payload_ref"], job["id"]) == frozen and len(seen) == 1


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("damage", ["missing", "corrupt"])
def test_partial_archive_preserves_aggregate_but_strict_read_rejects_damaged_constituent(setup, protocol, damage):
    store, _ = setup
    parts = [delta(protocol, "Distinct first fragment."), delta(protocol, "Distinct second fragment.")]
    damaged = []
    class Disconnected(Body):
        async def __aiter__(self):
            for part in parts:
                yield part
            chunks = [blob for blob in store.records("blob") if blob["kind"] == "stream_chunk"]
            assert len(chunks) == 2
            first = next(blob for blob in chunks if blob["meta"]["index"] == 0)
            path = store.root / "objects" / first["sha256"]
            if damage == "missing":
                path.unlink()
            else:
                path.write_bytes(b"synthetically damaged after registration")
            damaged.append(first)
            raise httpx.ReadError("synthetic disconnect after registered chunks")
    body, clock = Disconnected([]), Clock()
    store, job, nexus, request, seen = frozen_stream(setup, protocol, body, clock)
    with pytest.raises(StopRun, match="Remote completion and usage are unknown"):
        nexus.send(job["id"], request["id"])
    attempt = retained_attempt(store, job, request)
    raw = store.get("blob", attempt["stream_ref"])
    # Two distinct chunks keep the aggregate at a different content address.
    assert raw["sha256"] not in {blob["sha256"] for blob in damaged}
    assert raw["meta"]["chunk_validation"] == "registration_only"
    assert store.bytes(raw["ref"], job["id"]) == b"".join(parts)
    with pytest.raises(ValueError, match="missing|integrity"):
        Store(store.root).read_stream(job["id"], request["id"], attempt["id"])
    assert len(seen) == 1 and not attempt["transport"]["protocol_complete"]


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_complete_protocol_corruption_is_rejected_before_acceptance_staging(setup, protocol, monkeypatch):
    clock = Clock()
    body = Body([(1, delta(protocol, "Complete 25 mg.")), (2, ending(protocol, "Complete 25 mg."))], clock=clock)
    store, job, nexus, request, seen = frozen_stream(setup, protocol, body, clock)
    original_blob, damaged = store.blob, []
    def damage_registered_chunk(owner, kind, data, *args, **kwargs):
        blob = original_blob(owner, kind, data, *args, **kwargs)
        if kind == "stream_chunk" and not damaged:
            (store.root / "objects" / blob["sha256"]).write_bytes(b"corrupt after FULL registration")
            damaged.append(blob)
        return blob
    monkeypatch.setattr(store, "blob", damage_registered_chunk)
    with pytest.raises(ValueError, match="integrity"):
        nexus.send(job["id"], request["id"])
    attempt = retained_attempt(store, job, request)
    assert damaged and body.closed and len(seen) == 1
    assert store.maybe("blob", "raw-stream:" + attempt["id"]) is None
    def forbidden(_):
        pytest.fail("Corrupt unaccepted evidence must not resend on reopen")
    with pytest.raises(StopRun) as stopped:
        Nexus(Store(store.root), forbidden).send(job["id"], request["id"])
    assert stopped.value.reason == "unknown_outcome"


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_committed_chunk_before_cursor_advancement_uses_strict_suffix_recovery(setup, protocol, monkeypatch):
    parts = [delta(protocol, "Checkpointed prefix."), delta(protocol, "Durable suffix before callback return.")]
    clock = Clock()
    body = Body([(1, parts[0]), (2, parts[1])], clock=clock)
    store, job, nexus, request, seen = frozen_stream(setup, protocol, body, clock)
    original_blob, injected = store.blob, []
    def committed_before_callback_return(owner, kind, data, *args, **kwargs):
        blob = original_blob(owner, kind, data, *args, **kwargs)
        if kind == "stream_chunk" and blob["meta"]["index"] == 1 and not injected:
            injected.append(blob)
            raise OSError("synthetic durable-before-cursor gap")
        return blob
    monkeypatch.setattr(store, "blob", committed_before_callback_return)
    with pytest.raises(OSError, match="durable-before-cursor gap"):
        nexus.send(job["id"], request["id"])
    attempt = retained_attempt(store, job, request)
    raw = store.get("blob", attempt["stream_ref"])
    assert raw["meta"]["chunk_validation"] == "reconstructed"
    assert raw["meta"]["chunks"] == [f"stream:{attempt['id']}:{i}" for i in range(2)]
    assert store.bytes(raw["ref"], job["id"]) == b"".join(parts)
    recovered = Store(store.root).read_stream(job["id"], request["id"], attempt["id"])
    assert recovered["data"] == b"".join(parts)
    assert recovered["chunk_count"] == 2 and recovered["checkpoint_count"] == 1
    assert len(seen) == 1 and body.closed
