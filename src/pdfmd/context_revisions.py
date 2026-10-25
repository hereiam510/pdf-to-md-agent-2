"""Capture ordered context edits; only the coordinator may activate a policy."""
from __future__ import annotations

from .context_outcomes import policy_ref
from .nexus import instruction_basis
from .storage import Conflict


POLICY = {"pinned": [], "released": [], "pin_views": {}, "notes": ""}
FIELDS = {"notes", "pin", "release"}


class ContextRevisions:
    def __init__(self, context):
        self.context, self.store = context, context.store

    def pending(self, job, state):
        proposal = self.context.waiting(job, state)
        if proposal:
            disposition = self.store.maybe("context_disposition", state["context_waiting"])
            if disposition and disposition["status"] != "eligible_pending":
                raise Conflict("This candidate no longer has automatic admission eligibility. Use an explicit active base and selected content in a new revision.")
        return proposal

    def reuse(self, job: str, selections: list) -> tuple[list[dict], list[dict]]:
        if not isinstance(selections, list):
            raise ValueError("reuse must be an array of explicit source selections.")
        intents, origins = [], []
        for selection in selections:
            if not isinstance(selection, dict) or set(selection) - {"ref", "operations", "fields"} or "ref" not in selection:
                raise ValueError("Each reuse selection needs ref, and optional operations and fields.")
            ref = selection["ref"]
            blob = self.store.get("blob", ref, job=job)
            fields = selection.get("fields", sorted(FIELDS))
            if not isinstance(fields, list) or not fields or any(f not in FIELDS for f in fields):
                raise ValueError("Reuse fields must select notes, pin or release.")
            sources = []
            if blob["kind"] == "context_proposal":
                proposal = self.store.json(ref, job)["context_proposal"]
                chosen = selection.get("operations")
                if not isinstance(chosen, list) or not chosen or len(set(chosen)) != len(chosen) or any(op not in proposal["operations"] for op in chosen):
                    raise ValueError("Select exact context operation IDs from the saved proposal.")
                # Selection does not reorder the source operation sequence.
                for op in proposal["operations"]:
                    if op in chosen:
                        sources.extend(self._operation_intents(job, op))
            elif blob["kind"] == "candidate" and blob["meta"].get("tool") == "context_update":
                if "operations" in selection:
                    raise ValueError("operations applies only to a saved context proposal.")
                value = self.store.json(ref, job)
                if not isinstance(value, dict):
                    raise ValueError("The selected original context arguments are not a JSON object.")
                sources = [value]
            elif blob["kind"] == "tool_result":
                sources = self._operation_intents(job, blob["meta"]["operation"])
            else:
                raise ValueError("Reuse requires context proposal, context tool result, or original context candidate arguments.")
            selected = [{k: v for k, v in source.items() if k in fields} for source in sources]
            if not any(selected):
                raise ValueError("The selected source has none of the requested context fields.")
            intents.extend(item for item in selected if item)
            origins.append(dict(selection))
        return intents, origins

    def _operation_intents(self, job, operation):
        record = self.store.get("operation", operation, job=job)
        if record["tool"] != "context_update":
            raise ValueError("Only context operations may be reused.")
        result = self.store.json(record["result_ref"], job)
        saved = result.get("context_saved")
        if saved:
            return saved["intents"]
        original = self.store.json(record["candidate_ref"], job)
        if not isinstance(original, dict):
            raise ValueError("Malformed original arguments remain readable but cannot be guessed into an update.")
        return [original]

    def capture(self, job: dict, state: dict, working: dict, intent: dict, operation: str, candidate: str) -> dict:
        if set(intent) - FIELDS - {"base", "reuse"}:
            raise ValueError("Unknown context field.")
        base = intent.get("base")
        origin = working["base_ref"]
        policy = working["policy"]
        if base is not None:
            if not isinstance(base, dict) or set(base) - {"kind", "ref"} or base.get("kind") not in {"active", "pending"}:
                raise ValueError("base needs kind=active or pending and an optional expected ref.")
            if base["kind"] == "active":
                origin = policy_ref(state)
                policy = {k: state.get(k, default) for k, default in POLICY.items()}
            else:
                pending = self.pending(job["id"], state)
                if not pending:
                    raise Conflict("No eligible pending policy exists; choose an explicit active base.")
                origin, policy = state["context_waiting"], pending["policy"]
            if "ref" in base and base["ref"] != origin:
                raise Conflict("The expected context base changed. Read the current policy reference and choose again.")
        if "reuse" in intent and (base is None or "ref" not in base):
            raise ValueError("Explicit reuse requires base.kind and the expected base.ref from the current anchor.")
        if working.get("selection_required") and base is None:
            raise Conflict("The saved candidate is ineligible. Select base=active explicitly; it is not an automatic pending fallback.")
        intents, origins = self.reuse(job["id"], intent.get("reuse", []))
        changes = {k: v for k, v in intent.items() if k in FIELDS}
        if changes:
            intents.append(changes)
        for change in intents:
            policy = self.context.policy(job["id"], policy, change)
        # Resolve selections now, without estimating images/capacity or committing.
        # Pins() validates field/range content without calling the model.
        self.context.pins(job, {**state, **policy}, images=False)
        return {"context_saved": {"policy": policy, "intents": intents, "base_ref": origin,
                "reused_from": origins, "instruction_basis": instruction_basis(job),
                "operation": operation, "candidate_ref": candidate},
                "admission": {"applied": False, "status": "saved"}, "policy_unchanged": True,
                "message": "Saved and validated, not applied. All context operations in this accepted response form one revision. The coordinator admits the final candidate or returns a saved disposition; originals remain readable."}

    def start(self, job, state):
        pending = self.pending(job, state)
        return {"policy": pending["policy"] if pending else {k: state.get(k, default) for k, default in POLICY.items()},
                "base_ref": state["context_waiting"] if pending else policy_ref(state),
                "selection_required": bool(state.get("context_latest") and not pending and
                    (self.store.maybe("context_disposition", state["context_latest"]) or {}).get("status") != "applied")}

    def complete(self, job: str, state: dict, request: dict, operations: list[str], working: dict, errors: list[dict]) -> str:
        key = f"context-proposal:{request['id']}"
        proposal = {"policy": working["policy"], "base_ref": working["base_ref"],
                    "previous": state.get("context_waiting"), "supersedes": [state["context_waiting"]] if state.get("context_waiting") else [],
                    "operations": operations, "batch": request["id"], "valid": not errors, "errors": errors,
                    "instruction_basis": request["instruction_basis"], "origin_handoff": state.get("handoff")}
        self.store.blob(job, "context_proposal", {"context_proposal": proposal}, key=key)
        return key
