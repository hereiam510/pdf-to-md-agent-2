"""Settle deferred context proposals at unfrozen request boundaries."""
from __future__ import annotations

from .context import Context
from .nexus import StopRun, instruction_basis
from .storage import Conflict


POLICY = {"pinned": [], "released": [], "pin_views": {}, "notes": ""}


class ContextUpdates:
    def __init__(self, context: Context):
        self.context, self.store = context, context.store

    @staticmethod
    def basis(state: dict) -> dict:
        return {**{k: state.get(k) for k in ("seq", "revision", "history", "handoff", "context_waiting")},
                "policy": {k: state.get(k, default) for k, default in POLICY.items()}}

    @staticmethod
    def ref(key: str) -> str:
        return f"context-settlement:{key}"

    def recover(self, job: dict, state: dict, key: str) -> dict:
        if not state.get("context_waiting") or not self.store.maybe("blob", self.ref(key)):
            return {}
        record = self.store.json(self.ref(key), job["id"])
        if record["basis"] != self.basis(state):
            raise Conflict("The context settlement belongs to a different state transition.")
        self.store.event_once(job["id"], "context_update_settled", key,
                              {"receipt_ref": self.ref(key), "status": record["feedback"]["status"]})
        return record["changes"]

    def finish(self, job: dict, state: dict, key: str, feedback: dict, policy: dict | None = None) -> dict:
        changes = {"context_waiting": None, "context_feedback": self.ref(key), **(policy or {})}
        self.store.blob(job["id"], "context_settlement", {
            "basis": self.basis(state), "feedback": feedback, "changes": changes}, key=self.ref(key))
        return self.recover(job, state, key)

    def reject(self, job: dict, state: dict, key: str, message: str, *, status="rejected", capacity=None) -> dict:
        return self.finish(job, state, key, {"status": status, "applied": False,
            "proposal_ref": state["context_waiting"], "receipt_ref": self.ref(key),
            "message": message + " The active policy is unchanged. Exact proposals and originals remain readable; choose revised views or ranges if needed.",
            "capacity": capacity})

    def resolve(self, job: dict, state: dict, key: str) -> dict | None:
        """None requests another compaction under the active policy; no speculative application."""
        if recovered := self.recover(job, state, key):
            return recovered
        proposal = self.context.waiting(job["id"], state)
        if proposal is None:
            return {}
        if proposal["instruction_basis"] != instruction_basis(job):
            return self.reject(job, state, key, "New user instructions superseded the unapplied proposal chain.", status="superseded")
        policy = proposal["policy"]
        feedback = {"status": "applied", "applied": True, "proposal_ref": state["context_waiting"],
                    "receipt_ref": self.ref(key),
                    "message": "Compaction completed and the entire pending policy passed preflight. This outcome settles the earlier awaiting-compaction receipts."}
        preview = Context(self.store, self.context.dispatcher, update_feedback=feedback)
        candidate = {**state, **policy, "context_waiting": None, "context_feedback": self.ref(key)}
        try:
            # Charge the outcome itself, including its scalar capacity fields.
            for _ in range(8):
                capacity = preview.normal(job, candidate)[1]
                summary = {k: v for k, v in capacity.items() if k != "projection"}
                if feedback.get("capacity") == summary:
                    break
                feedback["capacity"] = summary
            else:
                return self.reject(job, state, key, "The deferred update estimate did not stabilize.")
            compacted = state.get("handoff") != proposal["origin_handoff"]
            if compacted and capacity["fits"]:
                return self.finish(job, state, key, feedback, policy)
            # Do not spend compaction requests on a policy whose required content
            # no longer fits (for example, after a route limit change).
            core = preview.normal(job, {**candidate, "history": [], "handoff": None})[1]
        except (StopRun, ValueError) as exc:
            return self.reject(job, state, key, str(exc))
        if not core["fits"] or not state["history"]:
            return self.reject(job, state, key, "The proposed input still exceeds capacity after available history reduction.", capacity=summary)
        return None
