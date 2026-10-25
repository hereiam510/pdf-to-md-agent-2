"""Settle deferred context proposals at unfrozen request boundaries."""
from __future__ import annotations

from hashlib import sha256

from .context import Context
from .context_outcomes import outcome
from .nexus import StopRun, instruction_basis
from .storage import Conflict, encode


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
        changes = {"context_waiting": None, "context_check": None, "context_feedback": self.ref(key), **(policy or {})}
        summary = outcome(feedback["status"], state["context_waiting"], self.ref(key), feedback["reason"])
        self.store.blob(job["id"], "context_settlement", {
            "basis": self.basis(state), "feedback": feedback, "summary": summary, "changes": changes}, key=self.ref(key))
        return self.recover(job, state, key)

    def reject(self, job: dict, state: dict, key: str, message: str, *, status="rejected", capacity=None, reason="proposed_capacity") -> dict:
        return self.finish(job, state, key, {"status": status, "applied": False,
            "reason": reason,
            "proposal_ref": state["context_waiting"], "receipt_ref": self.ref(key),
            "message": message + " The active policy is unchanged. Exact proposals and originals remain readable; choose revised views or ranges if needed.",
            "capacity": capacity})

    def wait(self, job: dict, state: dict, reason: str, message: str, *, capacity=None) -> dict:
        record = {"proposal_ref": state["context_waiting"], "status": "waiting", "reason": reason,
                  "message": message, "capacity": capacity, "basis": self.basis(state),
                  "route": job["route"], "instruction_basis": instruction_basis(job), "head": job["head"]}
        ref = "context-check:" + sha256(encode(record)).hexdigest()
        self.store.blob(job["id"], "context_check", record, key=ref)
        return {"context_check": ref}

    def resolve(self, job: dict, state: dict, key: str) -> dict:
        """Return a durable decision or an explicit, retryable waiting observation."""
        if recovered := self.recover(job, state, key):
            return recovered
        proposal = self.context.waiting(job["id"], state)
        if proposal is None:
            return {}
        if proposal["instruction_basis"] != instruction_basis(job):
            return self.reject(job, state, key, "New user instructions superseded the unapplied proposal chain.",
                               status="superseded", reason="new_instructions")
        policy = proposal["policy"]
        feedback = {"status": "applied", "applied": True, "proposal_ref": state["context_waiting"],
                    "receipt_ref": self.ref(key), "reason": "admitted",
                    "message": "The entire pending policy passed complete-input admission. This outcome settles the original saved-proposal receipts."}
        preview = Context(self.store, self.context.dispatcher,
                          update_feedback=outcome("applied", state["context_waiting"], self.ref(key), "admitted"))
        candidate = {**state, **policy, "context_waiting": None, "context_feedback": self.ref(key)}
        try:
            capacity = preview.admission(job, {**state, "context_waiting": None}, policy)
            feedback["capacity"] = {k: v for k, v in capacity.items() if k not in {"projection", "additional_deferrals"}}
            feedback["additional_deferrals"] = capacity["additional_deferrals"]
            if capacity["fits"] and not capacity["additional_deferrals"]:
                return self.finish(job, state, key, feedback, policy)
            core = preview.normal(job, {**candidate, "history": [], "handoff": None})[1]
            if not core["fits"]:
                # Capacity rejection abandons the pending chain. Its releases
                # cannot be borrowed to prove that the remaining active policy
                # can run. Measure that actual fallback, including the proposed
                # rejection envelope, without committing a decision first.
                fallback = {**state, "context_waiting": None}
                rejected = Context(self.store, self.context.dispatcher,
                    update_feedback=outcome("rejected", state["context_waiting"], self.ref(key), "proposed_capacity"))
                if not rejected.normal(job, fallback)[1]["fits"]:
                    rejected.compact_request(job, fallback)
                return self.reject(job, state, key, "The proposed required content exceeds current capacity.", capacity=core)
            # A feasible proposal may use its explicit releases for compaction.
            # Neither this transient view nor a stripped required core proves
            # that an unfitting proposal can safely be discarded.
            self.context.compact_request(job, state)
        except StopRun as exc:
            return self.wait(job, state, exc.reason, str(exc))
        except ValueError as exc:
            return self.reject(job, state, key, str(exc), reason="invalid_selection")
        return self.wait(job, state, "compaction", "History or the current handoff needs reduction before another admission check.", capacity=capacity)
