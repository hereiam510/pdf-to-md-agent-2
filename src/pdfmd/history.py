"""One history classification for ordinary accepted and resolved historical batches."""
from __future__ import annotations

from .storage import Conflict


def batch_identity(store, job, key):
    request = store.get("request", key, job=job)
    authority = store.maybe("conflict_resolution", key)
    if authority:
        if authority.get("job") != job or authority.get("request") != key:
            raise Conflict("Historical resolution ownership is inconsistent.")
        receipt = store.json(authority["ref"], job)
        if (receipt.get("ref") != authority["ref"] or receipt.get("basis") != authority.get("basis")
                or receipt.get("original_request") != request):
            raise Conflict("Resolved history contradicts the retained request facts.")
        return {"classification": "resolved_historical", "evidence_ref": receipt["accepted_staging_ref"],
                "resolution_ref": authority["ref"], "receipt": receipt}
    ref = request.get("accepted_ref")
    if not ref:
        raise Conflict("History has neither ordinary acceptance nor committed historical resolution.")
    return {"classification": "ordinary_accepted", "evidence_ref": ref, "resolution_ref": None}


def batch_reply(store, job, key):
    identity = batch_identity(store, job, key)
    reply = store.json(identity["evidence_ref"], job)
    if identity["classification"] == "resolved_historical":
        receipt = identity["receipt"]
        for ref, descriptor in receipt["evidence"].items():
            if store.get("blob", ref, job=job) != descriptor:
                raise Conflict("Resolved historical evidence descriptor changed.")
        from .nexus import parse_reply
        parsed = parse_reply(receipt["original_request"]["route"]["protocol"], store.bytes(reply["native_ref"], job))
        expected = {**parsed, "native_ref": reply["native_ref"], "stream_ref": reply["stream_ref"]}
        if expected != reply or len(receipt["operations"]) != len(reply["calls"]):
            raise Conflict("Resolved staging/native pairing changed.")
        for index, item in enumerate(receipt["operations"]):
            op = f"{key}:{index}"
            current = store.get("operation", op, job=job)
            if current != item["settled"] or item["call"] != reply["calls"][index]:
                raise Conflict("Resolved historical operation pairing changed.")
            store.bytes(item["result_ref"], job)
            if store.bytes(item["candidate_ref"], job) != item["call"]["arguments"].encode("utf-8"):
                raise Conflict("Resolved candidate arguments changed.")
    return {**identity, "reply": reply}


def provenance(store, job, keys):
    identities = [batch_identity(store, job, key) for key in keys]
    return {"originals": [value["evidence_ref"] for value in identities],
            "resolution_refs": [value["resolution_ref"] for value in identities]}
