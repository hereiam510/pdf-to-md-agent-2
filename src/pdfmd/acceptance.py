"""No-write acceptance validation shared by settlement and conflict diagnosis.

Validation observes complete saved evidence; publication and human recovery are
separate responsibilities. Fresh send may supply its already verified archive.
"""
from __future__ import annotations

import math
from .schema import Route
from .storage import Conflict, encode
from .streaming import StreamDecoder, StreamError


class EvidenceCheckError(ValueError):
    def __init__(self, message, observations):
        super().__init__(message)
        self.observations = observations


def inspect_acceptance(store, job, key, *, verified_stream=None):
    observations = {name: {"status": "unknown"} for name in
                    ("storage", "provenance", "reconstruction", "receive_boundary")}
    try:
        return _inspect_acceptance(store, job, key, verified_stream=verified_stream, observations=observations)
    except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError) as exc:
        message = ("Saved native structure is unsupported by the parser; this is not proof of disk corruption."
                   if isinstance(exc, (AttributeError, IndexError)) else str(exc))
        if isinstance(exc, Conflict):
            exc.observations = observations
            raise  # Settlement concurrency callers retain the Conflict type.
        raise EvidenceCheckError(message, observations) from exc


def _inspect_acceptance(store, job, key, *, verified_stream, observations):
    from .nexus import parse_reply
    request = store.get("request", key, job=job)
    ref = f"accepted:{key}"
    evidence = {}

    def blob(reference):
        record = store.get("blob", reference, job=job)
        if (record.get("ref") != reference or record.get("job") != job
                or not isinstance(record.get("meta"), dict)):
            raise ValueError("Accepted evidence has inconsistent provenance.")
        evidence[reference] = record
        return record

    stage = blob(ref)
    meta = stage["meta"]
    attempt_id = meta.get("attempt")
    received_at = meta.get("received_at")
    if (request.get("id") != key or request.get("job") != job
            or request.get("accepted_ref") not in (None, ref)
            or stage["kind"] != "accepted_response" or meta.get("request") != key
            or not isinstance(attempt_id, str) or request["attempts"].count(attempt_id) != 1
            or type(received_at) not in (int, float) or not math.isfinite(received_at)):
        raise ValueError("Accepted evidence has inconsistent provenance.")
    accepted = store.json(ref, job)
    if not isinstance(accepted, dict):
        raise ValueError("Accepted staging must contain a complete response object.")
    payload = blob(request["payload_ref"])
    if (payload["kind"] != "request_input" or payload["meta"].get("request") != key
            or payload["meta"].get("kind") != request["kind"]):
        raise ValueError("Frozen input has inconsistent provenance.")
    frozen_input = store.json(payload["ref"], job)
    native = blob(accepted["native_ref"])
    route = Route.model_validate(request["route"])
    if (not isinstance(frozen_input, dict)
            or (route.protocol == "chat_completions" and "input" in frozen_input and "messages" not in frozen_input)
            or (route.protocol == "responses" and "messages" in frozen_input and "input" not in frozen_input)):
        raise ValueError("Frozen input contradicts its recorded native protocol.")
    streaming = route.wait_policy is not None
    stream_ref = accepted.get("stream_ref")
    if (native["meta"].get("request") != key or native["meta"].get("attempt") != attempt_id
            or bool(stream_ref) != streaming):
        raise ValueError("Accepted evidence has inconsistent provenance.")
    native_bytes = store.bytes(native["ref"], job)
    observations["storage"] = {"status": "verified", "scope": "staging/input/native bytes"}
    parsed = parse_reply(route.protocol, native_bytes)
    expected = {**parsed, "native_ref": native["ref"]}
    receipt = None
    boundary = {"status": "compatible", "reason": None}
    reconstructed = True
    if streaming:
        stream = blob(stream_ref)
        if (stream_ref != f"raw-stream:{attempt_id}" or stream["kind"] != "raw_stream"
                or stream["meta"].get("request") != key or stream["meta"].get("attempt") != attempt_id
                or stream["meta"].get("complete_protocol") is not True
                or stream["meta"].get("chunk_validation") == "registration_only"
                or native["kind"] != "assembled_response"
                or native["meta"].get("source_stream_ref") != stream_ref
                or native["meta"].get("protocol") != route.protocol
                or native["meta"].get("complete_protocol") is not True):
            raise ValueError("Accepted streaming evidence has inconsistent provenance.")
        if verified_stream != stream:
            durable = store.read_stream(job, key, attempt_id)
            observations["storage"] = {"status": "verified", "scope": "complete staged/input/native/raw/chunk bytes"}
            decoder = StreamDecoder(route.protocol)
            try:
                decoder.feed(durable["data"])
            except StreamError as exc:
                boundary = {"status": "feed_error", "reason": str(exc)}
                reconstructed = False
            else:
                reconstructed = decoder.complete and encode(decoder.value) == native_bytes
                if not reconstructed:
                    observations["reconstruction"] = {"status": "mismatch"}
                    raise ValueError("Accepted native response contradicts its source stream.")
                try:
                    decoder.finish_received()
                except StreamError as exc:
                    supported = str(exc) in {
                        "The stream ended inside a UTF-8 character.",
                        "The stream ended inside a trailing SSE event."}
                    boundary = {"status": "finish_conflict" if supported else "unsupported_finish", "reason": str(exc)}
        receipt = store.maybe("stream_receive", attempt_id)
        if receipt and (receipt.get("request") != key or receipt.get("attempt") != attempt_id):
            raise ValueError("Accepted stream observation has inconsistent provenance.")
        expected["stream_ref"] = stream_ref
    elif (native["kind"] != "native_response" or native["meta"].get("complete_transport") is not True
            or native["meta"].get("within_deadline") is False):
        raise ValueError("Accepted native evidence has inconsistent provenance.")
    if accepted != expected:
        raise ValueError("Accepted staging contradicts its complete native response.")
    observations.update(reconstruction={"status": "matches" if reconstructed else "unknown"},
                        receive_boundary=boundary)

    # Unpublished diagnostic pointers can still name an earlier failed
    # attempt of this request. Validate their ownership before superseding.
    for field in ("response_ref", "stream_ref"):
        previous = request.get(field)
        if previous:
            record = evidence[previous] if previous in evidence else blob(previous)
            kinds = {"native_response", "partial_native_response", "assembled_response"} if field == "response_ref" else {"raw_stream"}
            desired_ref = native["ref"] if field == "response_ref" else stream_ref
            if (record["kind"] not in kinds or record["meta"].get("request") != key
                    or record["meta"].get("attempt") not in request["attempts"]
                    or (record["meta"]["attempt"] == attempt_id and previous != desired_ref)):
                raise ValueError("Request diagnostic pointer has inconsistent provenance.")
    observed = meta.get("transport")
    if observed is None and receipt:
        observed = receipt["transport"]
    if observed is not None and (not isinstance(observed, dict)
            or (observed.get("http_status") is not None
                and (type(observed["http_status"]) is not int or not 200 <= observed["http_status"] < 300))):
        raise ValueError("Accepted transport evidence is inconsistent.")

    attempt = store.get("attempt", attempt_id, job=job)
    if streaming and observed:
        if (observed.get("protocol_complete") is False
                or (observed.get("received_body_bytes") is not None and observed["received_body_bytes"] != stream["bytes"])
                or (observed.get("terminal_event") is not None and stream["meta"].get("terminal_event") is not None
                    and observed["terminal_event"] != stream["meta"]["terminal_event"])):
            raise ValueError("Saved transport facts contradict the complete raw stream.")
        if receipt and receipt.get("transport", {}).get("settled"):
            if any(k in observed and v is not None and observed[k] != v for k, v in receipt["transport"].items()):
                raise ValueError("Settled receive observation contradicts acceptance transport facts.")
    validate_metadata(request, attempt, job, key, attempt_id, ref, accepted, native, stream_ref, observed)
    observations.update(provenance={"status": "verified"},
                        reconstruction={"status": "matches" if reconstructed else "unknown"}, receive_boundary=boundary)
    return {"request": request, "ref": ref, "evidence": evidence, "accepted": accepted,
            "native": native, "attempt_id": attempt_id, "attempt": attempt, "received_at": received_at,
            "streaming": streaming, "stream_ref": stream_ref, "receipt": receipt,
            "observed": observed, "boundary": boundary, "reconstructed": reconstructed}


def validate_metadata(current, attempt, job, key, attempt_id, ref, accepted, native, stream_ref, observed, original=None):
    original = original or current
    streaming = bool(stream_ref)
    if (current is None or attempt is None or current.get("id") != key or current.get("job") != job
            or attempt.get("id") != attempt_id or attempt.get("request") != key
            or current.get("attempts", []).count(attempt_id) != 1
            or current.get("accepted_ref") not in (None, ref)
            or current.get("status") not in {"in_flight", "unknown", "accepted"}
            or attempt.get("status") not in {"in_flight", "unknown", "accepted"}):
        raise Conflict("Accepted request/attempt identity or state is inconsistent.")
    desired = {"response_ref": native["ref"], **({"stream_ref": stream_ref} if streaming else {})}
    for field in ("response_ref", "stream_ref"):
        value = current.get(field)
        if ((current["accepted_ref"] and value not in (None, desired.get(field)))
                or value not in (None, original.get(field), desired.get(field))):
            raise Conflict("Request acceptance pointers are inconsistent.")
    if attempt.get("stream_ref") not in (None, stream_ref):
        raise Conflict("Attempt acceptance pointer is inconsistent.")
    if attempt.get("usage") is not None and attempt["usage"] != accepted["usage"]:
        raise Conflict("Attempt usage contradicts accepted evidence.")
    if attempt.get("http_status") is not None and (type(attempt["http_status"]) is not int
            or not 200 <= attempt["http_status"] < 300):
        raise Conflict("Attempt HTTP status contradicts accepted evidence.")
    finished = attempt.get("finished")
    if finished is not None and (type(finished) not in (int, float) or not math.isfinite(finished)):
        raise Conflict("Attempt finish time is inconsistent.")
    if observed is not None:
        http_status = observed.get("http_status")
        if attempt.get("http_status") not in (None, http_status):
            raise Conflict("Attempt HTTP status contradicts accepted evidence.")
        transport = {k: v for k, v in observed.items() if k != "http_status"}
        old_transport = attempt.get("transport", {})
        if old_transport.get("settled") and any(k in old_transport and old_transport[k] != v for k, v in transport.items()):
            raise Conflict("Attempt transport contradicts accepted evidence.")
