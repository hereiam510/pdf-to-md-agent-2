"""One authority for context disposition, policy commitment and continuation."""
from __future__ import annotations

from hashlib import sha256

from .context import Context
from .context_outcomes import outcome, policy_ref
from .context_revisions import POLICY
from .nexus import StopRun, instruction_basis
from .storage import Conflict, encode


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
        ref = self.ref(key)
        if not state.get("context_waiting") or not self.store.maybe("blob", ref):
            return {}
        record = self.store.json(ref, job["id"])
        if record.get("version") == 2 and not self.store.maybe("context_commit", ref):
            return {}  # File/catalog registration alone did not commit this decision.
        if record["basis"] != self.basis(state):
            raise Conflict("The context settlement belongs to a different state transition.")
        self.store.event_once(job["id"], "context_update_settled", key,
                              {"receipt_ref": ref, "status": record["feedback"]["status"]})
        return record["changes"]

    def register(self, job: dict, state: dict, proposal: dict):
        ref = state["context_waiting"]
        with self.store.transaction() as db:
            existing = self.store.get_tx(db, "context_disposition", ref)
            if existing:
                return existing
            for old in proposal.get("supersedes", []):
                prior = self.store.get_tx(db, "context_disposition", old)
                if prior and prior["status"] not in {"eligible_pending", "superseded"}:
                    raise Conflict("A completed or ineligible revision cannot be used as an implicit pending base.")
                self.store.put_tx(db, "context_disposition", old, job["id"],
                    {"proposal_ref": old, "status": "superseded", "reason": "replacement_revision",
                     "replacement_ref": ref})
            value = {"proposal_ref": ref, "status": "eligible_pending", "instruction_basis": proposal["instruction_basis"]}
            self.store.put_tx(db, "context_disposition", ref, job["id"], value)
            return value

    def finish(self, job: dict, state: dict, key: str, feedback: dict, policy: dict | None = None) -> dict:
        ref = self.ref(key)
        changes = {"context_waiting": None, "context_check": None, "context_feedback": ref,
                   "context_latest": state["context_waiting"], **(policy or {})}
        summary = outcome(feedback["status"], state["context_waiting"], ref, feedback["reason"])
        record = {"version": 2, "basis": self.basis(state), "evaluation": {
            "route": job["route"], "instruction_basis": instruction_basis(job), "head": job["head"]},
            "feedback": feedback, "summary": summary, "changes": changes}
        # Stage immutable content, then commit disposition/effect together. An
        # uncommitted staged object can be abandoned after a changed evaluation.
        staged = self.store.blob(job["id"], "context_decision_candidate", record)
        with self.store.transaction() as db:
            committed = self.store.get_tx(db, "context_commit", ref)
            if committed is None:
                current = self.store.get_tx(db, "job", job["id"])
                if any(current[k] != job[k] for k in ("route", "head", "amendments")):
                    raise Conflict("Context evaluation changed before commit; retry against the current task state.")
                active = self.store.get_tx(db, "context_policy", job["id"])
                if active and active["ref"] != policy_ref(state):
                    raise Conflict("Active context changed before this transition committed.")
                blob = {**staged, "ref": ref, "kind": "context_settlement"}
                self.store.put_tx(db, "blob", ref, job["id"], blob)
                self.store.put_tx(db, "context_commit", ref, job["id"],
                    {"receipt_ref": ref, "proposal_ref": state["context_waiting"], "status": feedback["status"]})
                self.store.put_tx(db, "context_disposition", state["context_waiting"], job["id"],
                    {"proposal_ref": state["context_waiting"], "status": feedback["status"],
                     "reason": feedback["reason"], "receipt_ref": ref})
                if policy is not None:
                    self.store.put_tx(db, "context_policy", job["id"], job["id"],
                        {"ref": policy_ref(policy), "policy": policy, "receipt_ref": ref})
        return self.recover(job, state, key)

    def reject(self, job: dict, state: dict, key: str, message: str, *, status="needs_agent_revision", capacity=None, reason="required_content_exceeds_capacity") -> dict:
        return self.finish(job, state, key, {"status": status, "applied": False, "reason": reason,
            "proposal_ref": state["context_waiting"], "receipt_ref": self.ref(key),
            "message": message + " The active policy is unchanged. Read the saved candidate; choose an explicit current active base and reuse selected fields or operations in a new revision. Raw uses Base64; index, native image or exact field/range remain agent choices.",
            "capacity": capacity})

    def wait(self, job: dict, state: dict, reason: str, message: str, *, capacity=None) -> dict:
        record = {"proposal_ref": state.get("context_waiting"), "status": "waiting", "reason": reason,
                  "message": message, "capacity": capacity, "basis": self.basis(state),
                  "route": job["route"], "instruction_basis": instruction_basis(job), "head": job["head"]}
        ref = "context-check:" + sha256(encode(record)).hexdigest()
        self.store.blob(job["id"], "context_check", record, key=ref)
        return {"context_check": ref}

    def resolve(self, job: dict, state: dict, key: str) -> dict:
        if recovered := self.recover(job, state, key):
            return recovered
        proposal = self.context.waiting(job["id"], state)
        if proposal is None:
            return {}
        disposition = self.register(job, state, proposal)
        if disposition["status"] != "eligible_pending":
            receipt = disposition.get("receipt_ref")
            if receipt:
                record = self.store.json(receipt, job["id"])
                return record["changes"]
            return {"context_waiting": None, "context_latest": state["context_waiting"]}
        if proposal["instruction_basis"] != instruction_basis(job):
            return self.reject(job, state, key, "New instructions superseded this uncommitted revision.", status="superseded", reason="new_instructions")
        if not proposal.get("valid", True):
            return self.reject(job, state, key, "A context operation in this batch is structurally invalid. No context subset or older pending fallback was applied.", reason="invalid_revision")
        policy = proposal["policy"]
        preview = self.context.prospective(job, state, key)
        candidate = {**state, **policy, "context_waiting": None}
        try:
            capacity = preview.admission(job, {**state, "context_waiting": None}, policy)
            if capacity["fits"] and not capacity["additional_deferrals"]:
                feedback = {"status": "applied", "applied": True, "proposal_ref": state["context_waiting"],
                    "receipt_ref": self.ref(key), "reason": "admitted",
                    "capacity": {k: v for k, v in capacity.items() if k not in {"projection", "additional_deferrals"}},
                    "additional_deferrals": capacity["additional_deferrals"],
                    "message": "The complete batch revision passed actual normal-input admission."}
                return self.finish(job, state, key, feedback, policy)
            required = preview.required(job, candidate)
            if not required["fits"]:
                return self.reject(job, state, key, "The final candidate's necessary content exceeds the current allowance.", capacity=required)
            repair = state.get("repairs", {}).get("compaction", {})
            if repair.get("count", 0) > job["limits"].get("max_response_repairs", 2):
                diagnostic = Context(self.store, self.context.dispatcher,
                    update_feedback=outcome("needs_agent_revision", state["context_waiting"], self.ref(key), "compaction_repair_exhausted"))
                fallback = {**state, "context_waiting": None}
                if diagnostic.normal(job, fallback)[1]["fits"]:
                    return self.reject(job, state, key, "The saved candidate's bounded handoff correction episode is exhausted. Choose a new revision during normal work.", reason="compaction_repair_exhausted")
                return self.wait(job, state, "response_repair_exhausted", "Handoff correction is exhausted and no normal active-policy diagnostic fits. Existing history, candidate and budgets are retained.")
            self.context.compact_request(job, state)
        except StopRun as exc:
            if exc.reason == "capacity_configuration":
                # Unknown is not measured excess. Hand control back only when an
                # actual A continuation is available; otherwise keep named wait.
                diagnostic = Context(self.store, self.context.dispatcher,
                    update_feedback=outcome("needs_agent_revision", state["context_waiting"], self.ref(key), "unknown_capacity_agent_choice"))
                try:
                    if diagnostic.normal(job, {**state, "context_waiting": None})[1]["fits"]:
                        return self.reject(job, state, key, str(exc), reason="unknown_capacity_agent_choice")
                except (StopRun, ValueError):
                    pass
            return self.wait(job, state, exc.reason, str(exc))
        except ValueError as exc:
            return self.reject(job, state, key, str(exc), reason="invalid_selection")
        return self.wait(job, state, "compaction", "The complete candidate remains eligible. History or handoff needs reduction before admission.", capacity=capacity)

    def continuation(self, job: dict, state: dict) -> tuple[dict, dict, str]:
        """Select an actual executable request; a saved disposition never changes."""
        if state.get("context_waiting"):
            check = self.store.json(state["context_check"], job["id"])
            if check["reason"] != "compaction":
                raise StopRun(check["reason"], check["message"])
            payload, meta = self.context.compact_request(job, state)
            return payload, meta, "compaction"
        payload, capacity = self.context.normal(job, state)
        if capacity["fits"]:
            return payload, {"capacity": capacity}, "normal"
        # Only the target's supported lower bound can establish an obstruction
        # history compaction cannot fix. A failing full normal input cannot.
        required = self.context.required(job, state)
        if not required["fits"]:
            raise StopRun("feedback_capacity_blocked" if state.get("context_feedback") else "capacity_blocked",
                "Necessary active-policy content exceeds the current allowance. History compaction cannot make this normal request fit. Saved policy, candidate, decisions and work are retained; change the route capacity or another authorized required condition.")
        payload, meta = self.context.compact_request(job, state)
        return payload, meta, "compaction"
