"""Corrupt acceptance staging must not settle another attempt's unknown usage."""
from copy import deepcopy

import httpx
import pytest

from pdfmd.nexus import Nexus, StopRun, make_payload
from pdfmd.schema import Route
from pdfmd.storage import Store
from test_context_admission import protocol_job
from test_request_deadline import Body, Clock
from test_stream_progress import PROTOCOLS, delta, ending


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("mismatch", ["attempt", "request", "kind", "ref"])
def test_corrupt_acceptance_stage_cannot_publish_or_rewrite_unknown_attempt(setup, protocol, mismatch, monkeypatch):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    route = Route.model_validate({**job["route"], "wait_policy": {
        "first_progress_seconds": 600, "idle_progress_seconds": 300, "total_seconds": None}})
    job = store.update_job(job["id"], route=route.model_dump(), limits={
        **job["limits"], "replay_unknown": True, "max_attempts_per_request": 2})
    clock, sends = Clock(), []

    def respond(request):
        sends.append(request.content)
        chunks = [(1, delta(protocol, "Incomplete" if len(sends) == 1 else "Complete"))]
        if len(sends) == 2:
            chunks.append((2, ending(protocol, "Complete")))
        return httpx.Response(200, stream=Body(chunks, clock=clock))

    nexus = Nexus(store, lambda _: "synthetic-only", httpx.MockTransport(respond), clock=clock)
    request = nexus.freeze(job["id"], "same-request-staged-provenance",
        make_payload(route, "Synthetic preservation fixture.", [], []), "normal", {})
    frozen = store.bytes(request["payload_ref"], job["id"])
    with pytest.raises(StopRun, match="Remote completion and usage are unknown"):
        nexus.send(job["id"], request["id"])
    first_id = store.get("request", request["id"])["attempts"][0]
    first = store.get("attempt", first_id)
    assert first["status"] == "unknown" and first["usage"] is None

    # Genuine accepted-object/request-pointer gap on the second mocked attempt.
    original_put = store.put
    def pointer_gap(kind, key, owner, value):
        if kind == "request" and value.get("accepted_ref"):
            raise OSError("synthetic acceptance pointer gap")
        return original_put(kind, key, owner, value)
    monkeypatch.setattr(store, "put", pointer_gap)
    with pytest.raises(OSError, match="acceptance pointer gap"):
        nexus.send(job["id"], request["id"])
    monkeypatch.setattr(store, "put", original_put)
    pending = store.get("request", request["id"])
    assert pending["accepted_ref"] is None and len(pending["attempts"]) == 2
    stage_key = "accepted:" + request["id"]
    stage = store.get("blob", stage_key)
    original_bytes = store.bytes(stage_key, job["id"])
    original_meta = deepcopy(stage["meta"])
    assert original_meta["attempt"] == pending["attempts"][1]

    # Deliberately corrupt only catalog provenance. Keep complete accepted JSON,
    # its native assembly and its stream/chunks intact for the counterexample.
    if mismatch == "attempt":
        stage["meta"]["attempt"] = first_id
    elif mismatch == "request":
        stage["meta"]["request"] = "another-request"
    elif mismatch == "kind":
        stage["kind"] = "candidate"
    else:
        stage["ref"] = "another-acceptance"
    original_put("blob", stage_key, job["id"], stage)
    before_job = store.get("job", job["id"])
    before_attempts = store.records("attempt", job["id"])
    before_request = store.get("request", request["id"])

    reopened = Store(store.root)
    def forbidden(_):
        pytest.fail("Evidence rejection must not request credentials or resend")
    # A corrupt self-reference fails the scoped lookup before chain validation;
    # the other cases reach explicit provenance rejection. Both must be read-only.
    error = "Unknown blob reference" if mismatch == "ref" else "inconsistent provenance"
    with pytest.raises(ValueError, match=error):
        Nexus(reopened, forbidden).send(job["id"], request["id"])
    assert reopened.get("request", request["id"]) == before_request
    assert reopened.records("attempt", job["id"]) == before_attempts
    assert reopened.get("attempt", first_id) == first
    assert reopened.get("job", job["id"]) == before_job
    assert reopened.bytes(request["payload_ref"], job["id"]) == frozen
    assert reopened.bytes(stage_key, job["id"]) == original_bytes
    assert reopened.get("blob", stage_key) == stage
    assert len(sends) == 2 and not reopened.records("operation", job["id"])
