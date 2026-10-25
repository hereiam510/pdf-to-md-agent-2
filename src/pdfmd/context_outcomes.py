"""Small control messages; full decisions and authored arguments stay in the store."""
from __future__ import annotations

from hashlib import sha256

from .storage import encode


POLICY_DEFAULTS = {"pinned": [], "released": [], "pin_views": {}, "notes": ""}


def policy_ref(state: dict) -> str:
    """Content identity of the effective policy, not a second mutable authority."""
    policy = {key: state.get(key, default) for key, default in POLICY_DEFAULTS.items()}
    return "context-policy:" + sha256(encode(policy)).hexdigest()


def outcome(status: str, proposal: str, receipt: str, reason: str) -> dict:
    return {"status": status, "applied": status == "applied", "proposal_ref": proposal,
            "receipt_ref": receipt, "reason": reason}


def reserved_outcome(state: dict) -> dict:
    # Runtime request IDs contain a task UUID and two increasing integers. Reserve
    # their full prospective envelope, not a guessed number of provider tokens.
    key = f"{state['job']}:{state['seq'] + 1}:{state['revision'] + 1}"
    return outcome("needs_agent_revision", state["context_waiting"], f"context-settlement:{key}", "x" * 64)


def control_result(envelope: dict, settlement: dict | None = None) -> dict:
    data = envelope["data"]
    if not isinstance(data, dict):
        return envelope
    if "context_saved" in data:
        admission = {"applied": False, "status": "saved"}
    elif "context_intent" in data:
        admission = {"applied": True, "status": "applied"}
    elif "context_proposal" in data:
        admission = {"applied": False, "status": data["admission"]["status"]}
    elif data.get("context_rejected"):
        admission = {"applied": False, "status": "rejected", "reason": data.get("reason", "invalid_update")}
    elif envelope["ok"] is False:
        admission = {"applied": False, "status": "rejected", "reason": "invalid_or_unexecuted_update"}
    else:
        # Generic validation/skip errors have no policy to project. Preserve them.
        return envelope
    projected = {"admission": admission, "full_result_ref": envelope["result_ref"],
                 "read": {"ref": envelope["result_ref"], "view": "full"}}
    if settlement is None:
        projected["policy_unchanged"] = not admission["applied"]
    else:
        # This is a transient view of two facts, never a rewrite of the raw receipt.
        projected["policy_at_operation_unchanged"] = not admission["applied"]
        projected["context_outcome"] = settlement
    return {**envelope, "data": projected}
