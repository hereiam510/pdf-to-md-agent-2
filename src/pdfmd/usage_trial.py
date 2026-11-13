"""Offline bounded usage-anchoring coordinator.

There is deliberately no Engine, HTTP API, UI or CLI enrollment entry point.
The injected coordinator requires MockTransport, including for ordinary sends.
Catalog receipts own decisions/claims/settlement; graph state and diagnostics do not.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import time
import zipfile

import httpx

from .acceptance import inspect_acceptance
from .anchor_basis import AnchorEvaluator, ObservationProfile, preparation_basis
from .nexus import StopRun
from .request_estimation import estimate
from .schema import Route
from .storage import Conflict, encode
from .usage_anchoring import RECIPE, digest, normalized_input, price, unit_manifest
from .working_context import PREFIX


VERSION = "offline_usage_trial_v1"
DAYS = 60 * 24 * 60 * 60


def route_identity(route):
    # Normalize typed settings consistently across Pydantic default construction
    # and reload (e.g. timeout 180 versus 180.0). Free native parameters retain
    # their exact JSON representations; aliases are never inferred equivalent.
    return digest(Route.model_validate(route).model_dump())


def implementation_identity():
    names = ("request_estimation.py", "context.py", "working_context.py", "anchor_basis.py",
             "usage_anchoring.py", "usage_trial.py", "usage.py", "nexus.py", "runtime.py",
             "context_updates.py", "context_outcomes.py", "acceptance.py", "storage.py", "schema.py")
    return {"version": VERSION, "recipe": RECIPE,
            "dependencies": {name: version(name) for name in ("langgraph", "langgraph-checkpoint-sqlite", "httpx", "pydantic", "tiktoken")},
            "sources": {name: sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in names}}


def anchored_form(pf, route, basis_id, measured, units, reserve):
    """Change only feedback; charge its final native representation too."""
    payload = deepcopy(pf)
    key = "messages" if route.protocol == "chat_completions" else "input"
    summary = json.loads(payload[key][-1]["content"][len(PREFIX):])
    summary.update(input_estimate=0, remaining=0, estimate_kind="usage_anchored_reservation_not_provider_bound",
                   anchor={"basis_id": basis_id, "pricing": RECIPE["pricing"], "measured_input": measured})
    width = 0
    for _ in range(12):
        text = json.dumps(summary, ensure_ascii=False)
        width = max(width, len(text))
        feedback = {"role": "user", "content": PREFIX + text.ljust(width)}
        payload[key][-1] = feedback
        charge = price([*units[:-1], feedback], route.image_tokens, protocol=route.protocol, native_image_units=True)
        reservation = max(summary["input_estimate"], measured + charge["charge"] + reserve)
        values = {"input_estimate": reservation,
                  "remaining": route.context_tokens - route.output_tokens - reservation}
        if all(summary[k] == v for k, v in values.items()):
            return payload, {"reservation": reservation, "components": charge,
                             "outcome_reserve": reserve, "normalized_prior": measured,
                             "fits": reservation <= route.context_tokens - route.output_tokens}
        summary.update(values)
    raise ValueError("anchored_feedback_did_not_stabilize")


class OfflineUsageTrial:
    def __init__(self, store, lineage, *, clock=None):
        self.store, self.lineage = store, lineage
        self.clock = clock or time.time
        self.nexus = None

    @classmethod
    def create(cls, store, lineage, route, declaration, *, veto="C", clock=None):
        """Create an offline fixture lineage, never reset an existing one."""
        if not lineage or not declaration.strip() or veto not in {"A", "C"}:
            raise ValueError("A named lineage, accounting declaration and A/C disposition are required.")
        Route.model_validate(route)
        route = deepcopy(route)
        trial = cls(store, lineage, clock=clock)
        with store.transaction() as db:
            if store.get_tx(db, "usage_trial", lineage):
                raise Conflict("An existing trial lineage cannot be reset.")
            value = {"id": lineage, "version": VERSION, "offline": True, "generation": 1,
                     "route": route, "route_identity": route_identity(route),
                     "profile": ObservationProfile(digest(route), declaration).__dict__,
                     "implementation": implementation_identity(), "veto": veto, "activated": trial.clock(),
                     "status": "active", "stops": [], "pause": None, "slot": None,
                     "attempts": 0, "members": {}, "families": {}, "intake_closed": False,
                     "cohort_closed": False, "locked_tasks": [], "veto_decision": None}
            store.put_tx(db, "usage_trial", lineage, lineage, value)
        return trial

    def current(self):
        return self.store.get("usage_trial", self.lineage)

    def bind(self, nexus):
        self.fence(nexus)
        if nexus.store.root != self.store.root:
            raise ValueError("The coordinator and Nexus must share a workspace.")
        if nexus.usage_trial is not None and nexus.usage_trial is not self:
            raise ValueError("Nexus already has a coordinator.")
        self.nexus, nexus.usage_trial = nexus, self

    @staticmethod
    def fence(nexus):
        if not isinstance(nexus.transport, httpx.MockTransport):
            raise StopRun("offline_trial_only", "The offline coordinator requires a mock transport; no request was sent.")

    def enroll_synthetic(self, job_id, family):
        job = self.store.get("job", job_id)
        source = self.store.get("blob", job["source_ref"], job=job_id)
        if not isinstance(family, str) or not family.strip():
            raise ValueError("Declare the source work family before evaluation.")
        with self.store.transaction() as db:
            t = self.store.get_tx(db, "usage_trial", self.lineage)
            if job_id in t["members"]:
                member = t["members"][job_id]
                if member["source_sha256"] != source["sha256"] or member["family"] != family:
                    raise Conflict("Frozen source/family declarations cannot change in place.")
                return member
            if self.unavailable(t, job_id, enrollment=True) or route_identity(job["route"]) != t["route_identity"]:
                raise Conflict("This offline trial is not open for this enrollment.")
            previous = t["families"].get(source["sha256"])
            if previous is not None and previous != family:
                raise Conflict("Repeat source hashes retain their declared family.")
            member = {"job": job_id, "source_sha256": source["sha256"], "family": family,
                      "enrolled": self.clock(), "finished": False}
            t["families"][source["sha256"]] = family
            t["members"][job_id] = member
            t["intake_closed"] = len(t["members"]) >= 10
            self.store.put_tx(db, "usage_trial", self.lineage, self.lineage, t)
            return member

    def unavailable(self, t, job, *, enrollment=False):
        if self.clock() >= t["activated"] + DAYS:
            return "time_closed"
        if t["stops"]:
            return "stopped"
        if t["pause"]:
            return "paused"
        if t["cohort_closed"]:
            return "cohort_closed"
        if t["attempts"] >= 20:
            return "attempt_budget_exhausted"
        if job in t["locked_tasks"]:
            return "task_locked"
        if enrollment:
            return "intake_closed" if t["intake_closed"] else None
        if job not in t["members"]:
            return "not_enrolled"
        if t["members"][job]["finished"]:
            return "conversion_finished"
        return None

    def finish_conversion(self, job):
        with self.store.transaction() as db:
            t = self.store.get_tx(db, "usage_trial", self.lineage)
            t["members"][job]["finished"] = True
            if t["intake_closed"] and all(m["finished"] for m in t["members"].values()):
                t["cohort_closed"] = True
            self.store.put_tx(db, "usage_trial", self.lineage, self.lineage, t)

    def close_cohort(self):
        with self.store.transaction() as db:
            t = self.store.get_tx(db, "usage_trial", self.lineage)
            t.update(cohort_closed=True, intake_closed=True)
            self.store.put_tx(db, "usage_trial", self.lineage, self.lineage, t)

    def correct_family(self, source_sha256, family, correction_ref):
        """Explicit linked correction; keep original enrollment declarations."""
        if not family.strip():
            raise ValueError("A declared work family is required.")
        correction = self.store.get("blob", correction_ref)
        with self.store.transaction() as db:
            t = self.store.get_tx(db, "usage_trial", self.lineage)
            previous = t["families"][source_sha256]
            t.setdefault("family_corrections", []).append({"source_sha256": source_sha256,
                "previous": previous, "family": family, "ref": correction_ref, "sha256": correction["sha256"]})
            t["families"][source_sha256] = family
            for member in t["members"].values():
                if member["source_sha256"] == source_sha256:
                    member.setdefault("declared_family", member["family"])
                    member["family"] = family
            self.store.put_tx(db, "usage_trial", self.lineage, self.lineage, t)

    def reconcile_previous(self, job):
        """Only this task's immediate physical predecessor; no backward search."""
        attempts = self.store.records("attempt", job)
        if not attempts:
            return
        # Invalid/tied ordering remains an eligibility failure in AnchorEvaluator.
        if any(type(a.get("started")) not in (int, float) for a in attempts):
            return
        a = max(attempts, key=lambda a: a["started"])
        self.recover_request(job, a["request"])

    def prepare(self, context, job, state, key):
        """Return chosen normal form or an ordinary-path provenance descriptor."""
        if state.get("context_waiting"):
            return None, None
        self.reconcile_previous(job["id"])
        identity = digest({"lineage": self.lineage, "preparation": preparation_basis(job, state), "request": key})
        saved = self.store.maybe("trial_decision", identity)
        if saved is not None:
            return self.restore(saved, job)
        with self.store.connection_scope(), self.store.read_snapshot():
            t = self.current()
            if job["id"] not in t["members"]:
                return None, None
            reason = self.unavailable(t, job["id"])
            if route_identity(job["route"]) != t["route_identity"] or implementation_identity() != t["implementation"]:
                reason = "frozen_configuration_changed"
            # Eligibility retains each actual frozen route hash after the
            # lineage's normalized complete effective settings have matched.
            evaluator = AnchorEvaluator(self.store, ObservationProfile(**{**t["profile"], "route_sha256": digest(job["route"])}))
            basis, prior = evaluator.predecessor(job, state) if reason is None else (
                {"eligibility": False, "first_failure": reason, "recipe": RECIPE}, None)
        pf, f = context.normal(job, state, capacity_deferral=False)
        route = Route.model_validate(job["route"])
        reserve = f.get("outcome_reserve", 0)
        basis.update(id=identity, snapshot=preparation_basis(job, state), lineage=self.lineage,
                     generation=t["generation"], implementation=t["implementation"], route_sha256=digest(job["route"]),
                     ordered_units=unit_manifest(pf), policy_receipt=state.get("context_feedback"))
        decision = {"id": identity, "job": job["id"], "request": key, "lineage": self.lineage,
                    "generation": t["generation"], "disposition": "ordinary", "first_failure": basis.get("first_failure"),
                    "pf": {"sha256": digest(pf), "capacity": f}, "pa": None, "anchor": None,
                    "created": self.clock(), "slot_busy": bool(t["slot"]), "otherwise_qualified": False,
                    "allowance": route.context_tokens-route.output_tokens}
        pa = None
        if prior is not None:
            try:
                prior["usage_input"] = basis["normalized_usage"]["input"]
                basis["measured_units"] = unit_manifest(prior["payload"])
                units, edit, edit_evidence = evaluator.charged(job, state, pf, prior, f)
                if edit not in evaluator.profile.edits:
                    raise ValueError("edit_not_declared_in_profile")
                components = price(units, route.image_tokens, protocol=route.protocol, native_image_units=True)
                if components["images"] and evaluator.profile.image_rule != "configured_per_occurrence_uncalibrated_v1":
                    raise ValueError("unsupported_image_rule")
                a = {"reservation": prior["usage_input"] + components["charge"] + reserve,
                     "normalized_prior": prior["usage_input"], "components": components, "outcome_reserve": reserve}
                a["fits"] = a["reservation"] <= route.context_tokens - route.output_tokens
                decision["anchor"] = a
                basis.update(edit=edit, edit_evidence=edit_evidence, charged_units=[digest(u) for u in units])
                if f["fits"] and not a["fits"]:
                    decision["disposition"] = "veto_" + t["veto"]
                elif not f["fits"] and a["fits"]:
                    pa, anchored = anchored_form(pf, route, identity, prior["usage_input"], units, reserve)
                    final_f = estimate(pa, route)
                    final_f["input_estimate"] += reserve
                    final_f["fits"] = final_f["input_estimate"] + route.output_tokens <= route.context_tokens
                    decision["pa"] = {"sha256": digest(pa), "capacity": final_f, "anchor": anchored}
                    decision["pa"].update(same_payload_recovered_headroom=final_f["input_estimate"]-anchored["reservation"],
                                          headroom=route.context_tokens-route.output_tokens-anchored["reservation"])
                    if not final_f["fits"] and anchored["fits"]:
                        decision["otherwise_qualified"] = True
                        decision["disposition"] = "busy" if t["slot"] else "decisive"
                    else:
                        decision["first_failure"] = "pa_not_decisive"
            except (ImportError, OSError, EOFError, ValueError, KeyError, TypeError) as exc:
                # Only optional anchor evaluation is inside this boundary.
                # Ordinary assembly, durable writes and restore remain outside.
                failure = ("anchor_evaluation_unavailable:" + type(exc).__name__
                           if isinstance(exc, (ImportError, OSError, EOFError)) else str(exc) or type(exc).__name__)
                decision.update(first_failure=failure,
                                disposition="ordinary", anchor=None, pa=None, otherwise_qualified=False)
                pa = None
        basis["first_failure"] = decision["first_failure"]
        basis["eligibility"] = decision["anchor"] is not None and decision["first_failure"] is None
        decision["basis_ref"] = self.store.blob(job["id"], "trial_basis", basis)["ref"]
        decision["pf"]["ref"] = self.store.blob(job["id"], "trial_pf", pf)["ref"]
        if pa is not None:
            decision["pa"]["ref"] = self.store.blob(job["id"], "trial_pa", pa)["ref"]
        with self.store.transaction() as db:
            old = self.store.get_tx(db, "trial_decision", identity)
            if old is not None:
                decision = old
            else:
                current = self.store.get_tx(db, "usage_trial", self.lineage)
                revoked = self.unavailable(current, job["id"])
                if revoked and decision["disposition"] != "ordinary":
                    decision.update(disposition="ordinary", first_failure="revoked_before_decision:" + revoked,
                                    otherwise_qualified=False)
                elif decision["disposition"].startswith("veto_"):
                    current["veto_decision"] = identity
                    self.stop(current, "governing_veto", job["id"], identity)
                elif decision["disposition"] == "decisive" and current["slot"]:
                    decision["disposition"] = "busy"
                    decision["slot_busy"] = True
                self.store.put_tx(db, "usage_trial", self.lineage, self.lineage, current)
                self.store.put_tx(db, "trial_decision", identity, job["id"], decision)
        return self.restore(decision, job)

    def ordinary_result(self, descriptor, payload, meta, kind, job):
        """Link the actual ordinary content change without a third trial form."""
        identity = digest({"decision": descriptor["decision_id"], "ordinary_payload": digest(payload), "kind": kind})
        value = {"id": identity, "lineage": self.lineage, "job": job,
                 "parent_decision": descriptor["decision_id"], "kind": kind,
                 "payload_sha256": digest(payload), "capacity": deepcopy(meta["capacity"])}
        old = self.store.maybe("trial_ordinary", identity)
        if old is None:
            value["payload_ref"] = self.store.blob(job, "trial_ordinary_input", payload)["ref"]
            with self.store.transaction() as db:
                old = self.store.get_tx(db, "trial_ordinary", identity, job=job)
                if old is None:
                    self.store.put_tx(db, "trial_ordinary", identity, job, value)
                    old = value
        return {**descriptor, "ordinary_evaluation_id": identity,
                "ordinary_payload_sha256": old["payload_sha256"], "ordinary_payload_ref": old["payload_ref"]}

    def restore(self, d, job):
        descriptor = {"version": VERSION, "lineage": self.lineage, "generation": d["generation"],
                      "decision_id": d["id"], "basis_ref": d["basis_ref"], "disposition": d["disposition"],
                      "method": "full_local", "pf_ref": d["pf"]["ref"], "pf_sha256": d["pf"]["sha256"]}
        # Read every immutable decision dependency again on reopen. A missing
        # anchor-capable manifest is evidence failure, never a legacy downgrade.
        self.store.json(d["basis_ref"], job["id"])
        pf = self.store.json(d["pf"]["ref"], job["id"])
        if digest(pf) != d["pf"]["sha256"]:
            raise Conflict("Frozen Pf identity mismatch.")
        if d["disposition"] == "veto_A":
            raise StopRun("usage_anchor_veto_hold", "The committed trial veto holds this exact fitting full-local request for review.")
        if d["disposition"] == "decisive":
            t = self.current()
            revoked = self.unavailable(t, job["id"])
            if route_identity(job["route"]) != t["route_identity"] or implementation_identity() != t["implementation"]:
                revoked = "frozen_configuration_changed"
            if revoked or t["slot"]:
                descriptor.update(disposition="revoked_before_freeze", prohibition=revoked or "slot_busy")
                return None, descriptor
            pa = self.store.json(d["pa"]["ref"], job["id"])
            if digest(pa) != d["pa"]["sha256"]:
                raise Conflict("Frozen Pa identity mismatch.")
            a = d["pa"]["anchor"]
            descriptor.update(method="usage_anchor", reservation=a["reservation"], payload_sha256=d["pa"]["sha256"])
            capacity = {**d["pa"]["capacity"], "input_estimate": a["reservation"], "fits": True,
                        "governing_method": "usage_anchor", "anchor": descriptor}
            return (pa, {"capacity": capacity}, "normal"), descriptor
        if d["disposition"] == "veto_C":
            return (pf, {"capacity": {**d["pf"]["capacity"], "anchor": descriptor}}, "normal"), descriptor
        return None, descriptor

    @staticmethod
    def stop(t, reason, job, evidence):
        item = {"reason": reason, "job": job, "evidence": evidence}
        if item not in t["stops"]:
            t["stops"].append(item)
        t["status"] = "stopped"
        if job not in t["locked_tasks"]:
            t["locked_tasks"].append(job)

    def preflight(self, request, *, freezing=False):
        a = request.get("meta", {}).get("capacity", {}).get("anchor")
        result = {"implementation": implementation_identity(), "evidence": {}, "decision": None}
        if a and a.get("method") == "usage_anchor":
            if digest(self.store.json(request["payload_ref"], request["job"])) != a["payload_sha256"]:
                raise Conflict("Frozen anchored payload identity mismatch.")
            d = self.store.get("trial_decision", a["decision_id"], job=request["job"])
            basis = self.store.json(a["basis_ref"], request["job"])
            if freezing and basis["route_sha256"] != digest(request["route"]):
                result["revocation"] = "route_changed_before_freeze"
                return result
            if (d["request"] != request["id"] or d["lineage"] != a["lineage"] or d["generation"] != a["generation"]
                    or d["basis_ref"] != a["basis_ref"] or d["disposition"] != "decisive"
                    or d["pa"]["sha256"] != a["payload_sha256"]
                    or d["pa"]["anchor"]["reservation"] != a["reservation"]
                    or basis["id"] != d["id"] or basis["route_sha256"] != digest(request["route"])):
                raise Conflict("Frozen governing decision or basis identity mismatch.")
            for ref in (a["basis_ref"], d["pf"]["ref"], d["pa"]["ref"], request["payload_ref"]):
                self.store.bytes(ref, request["job"])
                result["evidence"][ref] = self.store.get("blob", ref, job=request["job"])
            result["decision"] = d
        return result

    def proof_matches_tx(self, db, proof):
        d = proof["decision"]
        return (d is not None and self.store.get_tx(db, "trial_decision", d["id"], job=d["job"]) == d
                and all(self.store.get_tx(db, "blob", ref, job=d["job"]) == record for ref,record in proof["evidence"].items()))

    def prohibit_tx(self, db, request, phase, reason):
        a = request["meta"]["capacity"]["anchor"]
        identity = digest({"decision": a["decision_id"], "request": request["id"], "phase": phase, "reason": reason})
        if self.store.get_tx(db, "trial_prohibition", identity) is None:
            self.store.put_tx(db, "trial_prohibition", identity, request["job"],
                {"id": identity, "lineage": self.lineage, "request": request["id"], "phase": phase,
                 "reason": reason, "payload_ref": request["payload_ref"], "decision_id": a["decision_id"], "created": self.clock()})

    def freeze_tx(self, db, request, actual_implementation):
        a = request.get("meta", {}).get("capacity", {}).get("anchor")
        if not a or a.get("method") != "usage_anchor":
            return None
        t = self.store.get_tx(db, "usage_trial", self.lineage)
        if actual_implementation.get("revocation"):
            return actual_implementation["revocation"]
        if (a["lineage"] != self.lineage or a["generation"] != t["generation"]
                or route_identity(request["route"]) != t["route_identity"]
                or route_identity(self.store.get_tx(db, "job", request["job"])["route"]) != t["route_identity"]
                or actual_implementation["implementation"] != t["implementation"]
                or not self.proof_matches_tx(db, actual_implementation)):
            return "frozen_configuration_changed"
        return self.unavailable(t, request["job"]) or ("slot_busy" if t["slot"] else None)

    def claim_tx(self, db, request, attempt_id, actual_implementation):
        """Same transaction as the physical attempt and ordinary job budget."""
        a = request.get("meta", {}).get("capacity", {}).get("anchor")
        if not a or a.get("method") != "usage_anchor":
            return
        t = self.store.get_tx(db, "usage_trial", self.lineage)
        d = self.store.get_tx(db, "trial_decision", a["decision_id"], job=request["job"])
        reason = self.unavailable(t, request["job"])
        if (a["lineage"] != self.lineage or a["generation"] != t["generation"] or not d
                or d["disposition"] != "decisive" or route_identity(request["route"]) != t["route_identity"]
                or a["payload_sha256"] != d["pa"]["sha256"] or a["reservation"] != d["pa"]["anchor"]["reservation"]
                or actual_implementation["implementation"] != t["implementation"]
                or not self.proof_matches_tx(db, actual_implementation)
                or route_identity(self.store.get_tx(db, "job", request["job"])["route"]) != t["route_identity"]
                or self.store.get_tx(db, "blob", request["payload_ref"], job=request["job"])["sha256"] != a["payload_sha256"]):
            reason = "frozen_trial_identity_changed"
        if reason or t["slot"]:
            return reason or "slot_busy"
        t["attempts"] += 1
        t["slot"] = {"attempt": attempt_id, "request": request["id"], "job": request["job"],
                     "decision_id": a["decision_id"], "claimed": self.clock()}
        self.store.put_tx(db, "usage_trial", self.lineage, self.lineage, t)
        self.store.put_tx(db, "trial_attempt", attempt_id, request["job"],
                          {**t["slot"], "lineage": self.lineage, "ordinal": t["attempts"],
                           "reservation": a["reservation"], "status": "claimed", "input": None, "margin": None})

    def settle_tx(self, db, request, attempt, raw_usage):
        receipt = self.store.get_tx(db, "trial_attempt", attempt["id"])
        if receipt is None:
            raise Conflict("Anchored acceptance has no durable physical trial claim.")
        a = request["meta"]["capacity"]["anchor"]
        if (receipt["request"] != request["id"] or receipt["job"] != request["job"]
                or receipt["lineage"] != self.lineage or receipt["decision_id"] != a["decision_id"]
                or receipt["reservation"] != a["reservation"]):
            raise Conflict("Accepted trial claim does not match its frozen governing decision.")
        if receipt.get("status") != "claimed":
            return
        t = self.store.get_tx(db, "usage_trial", receipt["lineage"])
        if t["slot"] is None or t["slot"]["attempt"] != attempt["id"]:
            raise Conflict("Trial settlement has no matching outstanding slot.")
        try:
            actual = normalized_input(request["route"]["protocol"], raw_usage)["input"]
        except ValueError:
            actual = None
        receipt.update(status="accepted_unscorable" if actual is None else "accepted_scored",
                       accepted_ref=request["accepted_ref"], input=actual,
                       margin=None if actual is None else receipt["reservation"] - actual,
                       finished=self.clock(), usage_sha256=digest(raw_usage))
        if actual is None:
            t["pause"] = {"reason": "accepted_input_usage_unavailable", "attempt": attempt["id"]}
            if not t["stops"]:
                t["status"] = "paused"
        elif actual > receipt["reservation"]:
            self.stop(t, "reservation_exceeded", request["job"], attempt["id"])
        t["slot"] = None  # only after durable applicable pause/stop is included
        self.store.put_tx(db, "trial_attempt", attempt["id"], request["job"], receipt)
        self.store.put_tx(db, "usage_trial", t["id"], t["id"], t)

    def failed_tx(self, db, request, attempt):
        receipt = self.store.get_tx(db, "trial_attempt", attempt["id"])
        if receipt is None or receipt.get("status") != "claimed":
            return
        t = self.store.get_tx(db, "usage_trial", receipt["lineage"])
        self.stop(t, "decisive_attempt_failed_or_unresolved", request["job"], attempt["id"])
        receipt.update(status="failed_or_unresolved", finished=self.clock(), outcome=attempt["status"])
        t["slot"] = None
        self.store.put_tx(db, "trial_attempt", attempt["id"], request["job"], receipt)
        self.store.put_tx(db, "usage_trial", t["id"], t["id"], t)

    def recover_request(self, job, key):
        if self.nexus is None:
            raise ValueError("Bind the coordinator to Nexus before recovery.")
        request = self.nexus.reconcile(job, key)
        if request.get("accepted_ref"):
            return
        with self.store.transaction() as db:
            t = self.store.get_tx(db, "usage_trial", self.lineage)
            slot = t["slot"]
            if slot and slot["job"] == job and slot["request"] == key:
                attempt = self.store.get_tx(db, "attempt", slot["attempt"], job=job)
                if attempt is None:
                    raise Conflict("Trial slot has no durable physical attempt; review is required.")
                self.failed_tx(db, request, attempt)

    def confirm_overflow(self, job, key, evidence_ref):
        """Explicit reviewed evidence, never classify a generic HTTP failure."""
        request = self.store.get("request", key, job=job)
        evidence = self.store.get("blob", evidence_ref, job=job)
        if not request["attempts"]:
            raise ValueError("Overflow confirmation requires a physical attempt.")
        with self.store.transaction() as db:
            t = self.store.get_tx(db, "usage_trial", self.lineage)
            if route_identity(request["route"]) != t["route_identity"]:
                raise Conflict("Overflow evidence is outside this route generation.")
            self.stop(t, "confirmed_context_overflow", job, {"request": key, "ref": evidence_ref, "sha256": evidence["sha256"]})
            self.store.put_tx(db, "usage_trial", self.lineage, self.lineage, t)

    def late_usage(self, job, attempt_id, evidence_ref):
        """Reviewed same-attempt input evidence; it never resumes or extends."""
        receipt = self.store.get("trial_attempt", attempt_id, job=job)
        if receipt["lineage"] != self.lineage:
            raise Conflict("Late evidence belongs to another trial lineage.")
        evidence = self.store.json(evidence_ref, job)
        request = self.store.get("request", receipt["request"], job=job)
        if (evidence.get("request") != request["id"] or evidence.get("attempt") != attempt_id
                or evidence.get("accepted_ref") != request["accepted_ref"]
                or evidence.get("payload_sha256") != self.store.get("blob", request["payload_ref"], job=job)["sha256"]
                or evidence.get("route_sha256") != digest(request["route"])):
            raise Conflict("Late evidence does not identify this same accepted physical attempt.")
        actual = normalized_input(request["route"]["protocol"], evidence.get("native_usage"))["input"]
        with self.store.transaction() as db:
            r = self.store.get_tx(db, "trial_attempt", attempt_id, job=job)
            if r["status"] != "accepted_unscorable":
                raise Conflict("Only an accepted unscorable attempt can receive late attribution.")
            t = self.store.get_tx(db, "usage_trial", self.lineage)
            r.update(status="accepted_scored", input=actual, margin=r["reservation"]-actual,
                     late_evidence_ref=evidence_ref, attribution_review_required=True)
            if actual > r["reservation"]:
                self.stop(t, "reservation_exceeded", job, attempt_id)
            self.store.put_tx(db, "trial_attempt", attempt_id, job, r)
            self.store.put_tx(db, "usage_trial", self.lineage, self.lineage, t)

    def ordinary_alternative(self, job, key):
        """Reproduce the ordinary alternative offline, never dispatch it."""
        from .context import Context
        from .context_updates import ContextUpdates
        from .tools import Dispatcher
        request = self.store.get("request", key, job=job)
        a = request["meta"]["capacity"]["anchor"]
        d = self.store.get("trial_decision", a["decision_id"], job=job)
        if a["method"] != "usage_anchor" or a["lineage"] != self.lineage:
            raise ValueError("A decisive request is required.")
        saved = request["meta"]["context_snapshot"]
        scripts = any(tool.get("function", tool).get("name") == "run_script" for tool in
                      self.store.json(request["payload_ref"], job).get("tools", []))
        context = Context(self.store, Dispatcher(self.store, scripts=scripts))
        pf = context.normal(saved["job"], saved["state"], capacity_deferral=False)[0]
        if digest(pf) != d["pf"]["sha256"] or implementation_identity() != self.current()["implementation"]:
            raise Conflict("The original full-local alternative cannot be reproduced with this implementation.")
        result = {"request": key, "decision_id": d["id"], "pf_sha256": digest(pf),
                  "snapshot_sha256": digest(saved), "implementation": self.current()["implementation"],
                  "execution": "projection_only_not_dispatched"}
        try:
            payload, meta, kind = ContextUpdates(context).continuation(saved["job"], saved["state"])
            result.update(disposition="compaction" if kind == "compaction" else "deferral",
                          payload_ref=self.store.blob(job, "trial_ordinary_alternative_input", payload)["ref"],
                          payload_sha256=digest(payload), capacity=meta["capacity"])
        except StopRun as exc:
            result.update(disposition="stop", reason=exc.reason)
        return self.store.blob(job, "trial_ordinary_alternative", result)["ref"]

    def check_chain(self, job, key, review_ref):
        """Bind an explicit source-led review to actual receipts and output bytes.

        This validates correspondence. The reviewer's source-fidelity judgment
        remains an attributed declaration, never an inference from tool success.
        """
        request = self.store.get("request", key, job=job)
        a = request["meta"]["capacity"]["anchor"]
        review = self.store.json(review_ref, job)
        if (a["method"] != "usage_anchor" or a["lineage"] != self.lineage
                or review.get("request") != key or review.get("payload_sha256") != a["payload_sha256"]
                or review.get("source_sha256") != self.current()["members"][job]["source_sha256"]
                or review.get("useful") is not True or review.get("source_fidelity") is not True
                or review.get("saved_reopened_exported") is not True
                or not isinstance(review.get("review_note"), str) or not review["review_note"].strip()
                or not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip()
                or not isinstance(review.get("reviewed_pages"), list) or not review["reviewed_pages"]
                or any(type(p) is not int or not 1 <= p <= self.store.get("job", job)["page_count"] for p in review["reviewed_pages"])):
            raise ValueError("A complete attributed same-payload useful-recovery review is required.")
        accepted = self.store.json(request["accepted_ref"], job)
        operations = {f"{key}:{i}" for i in range(len(accepted["calls"]))}
        op_id = review.get("executed_operation")
        op = self.store.get("operation", op_id, job=job) if op_id in operations else None
        if not op or op.get("status") != "done" or op.get("ok", True) is not True:
            raise ValueError("The reviewed action has no reconciled successful execution receipt.")
        call = accepted["calls"][int(op_id.rsplit(":", 1)[1])]
        if op["tool"] != call["name"] or op["args_hash"] != digest([call["name"], call["arguments"]]):
            raise Conflict("The execution receipt does not match the accepted action.")
        if self.store.bytes(op["candidate_ref"], job) != call["arguments"].encode("utf-8"):
            raise Conflict("The executed candidate does not match the accepted action.")
        if op.get("result_ref"):
            self.store.json(op["result_ref"], job)
        alternative = self.store.json(review["ordinary_alternative_ref"], job)
        d = self.store.get("trial_decision", a["decision_id"], job=job)
        if (alternative.get("request") != key or alternative.get("decision_id") != d["id"]
                or alternative.get("pf_sha256") != d["pf"]["sha256"]
                or alternative.get("snapshot_sha256") != digest(request["meta"]["context_snapshot"])
                or alternative.get("implementation") != self.current()["implementation"]
                or alternative.get("execution") != "projection_only_not_dispatched"
                or alternative.get("disposition") not in {"deferral", "compaction", "stop"}):
            raise ValueError("The ordinary alternative does not reproduce the original decision basis.")
        if alternative.get("payload_ref"):
            if digest(self.store.json(alternative["payload_ref"], job)) != alternative["payload_sha256"]:
                raise Conflict("Ordinary alternative bytes changed.")
        version = review["version_id"]
        record = self.store.get("version", version, job=job)
        # Read the existing version without constructing a write-capable service
        # or creating a missing directory during a read-only report.
        for name, checksum in record["files"].items():
            if sha256((self.store.root / "versions" / version / name).read_bytes()).hexdigest() != checksum:
                raise Conflict("The reviewed saved version failed reopened byte verification.")
        export = self.store.get("export", review["export_id"], job=job)
        if export.get("version_id") != version or export.get("verified") is not True:
            raise ValueError("The reviewed export does not identify the verified saved version.")
        with zipfile.ZipFile(export["path"]) as archive:
            if len(archive.namelist()) != len(record["files"]) or set(archive.namelist()) != set(record["files"]) or any(
                    sha256(archive.read(name)).hexdigest() != checksum for name, checksum in record["files"].items()):
                raise Conflict("The reviewed export does not match the saved version bytes.")
        chain = {"id": key, "lineage": self.lineage, "job": job, "review_ref": review_ref,
                 "review_sha256": digest(review), "payload_sha256": a["payload_sha256"]}
        return chain

    def record_chain(self, job, key, review_ref):
        chain = self.check_chain(job, key, review_ref)
        with self.store.transaction() as db:
            scores = db.execute("SELECT data FROM records WHERE kind='trial_attempt' AND job=?", (job,)).fetchall()
            if not any((r := json.loads(row[0]))["request"] == key and r["status"] == "accepted_scored" for row in scores):
                raise ValueError("Only a scored accepted decisive logical request can have a reviewed chain.")
            prior = self.store.get_tx(db, "trial_chain", key, job=job)
            if prior and prior != chain:
                raise Conflict("A chain review cannot be silently replaced; retain a linked correction separately.")
            self.store.put_tx(db, "trial_chain", key, job, chain)

    def resume(self, *, reviewed_attempt):
        actual_implementation = implementation_identity()
        with self.store.transaction() as db:
            t = self.store.get_tx(db, "usage_trial", self.lineage)
            pause = t["pause"]
            r = self.store.get_tx(db, "trial_attempt", reviewed_attempt)
            if (not pause or pause["attempt"] != reviewed_attempt or not r or r["status"] != "accepted_scored"
                    or r["lineage"] != self.lineage
                    or not r.get("late_evidence_ref") or t["stops"] or t["slot"] or t["cohort_closed"]
                    or t["attempts"] >= 20 or self.clock() >= t["activated"] + DAYS
                    or actual_implementation != t["implementation"]):
                raise Conflict("Explicit resume requires reviewed attribution and an otherwise open unchanged trial.")
            r["attribution_review_required"] = False
            t.update(pause=None, status="active")
            self.store.put_tx(db, "trial_attempt", reviewed_attempt, r["job"], r)
            self.store.put_tx(db, "usage_trial", self.lineage, self.lineage, t)

    def review_attribution(self, *, reviewed_attempt):
        """A closed trial may accept reviewed attribution without resuming."""
        with self.store.transaction() as db:
            r = self.store.get_tx(db, "trial_attempt", reviewed_attempt)
            if (not r or r["lineage"] != self.lineage or r["status"] != "accepted_scored"
                    or not r.get("late_evidence_ref")):
                raise Conflict("Reviewed attribution requires same-lineage late accepted evidence.")
            r["attribution_review_required"] = False
            self.store.put_tx(db, "trial_attempt", reviewed_attempt, r["job"], r)

    def check_score(self, t, receipt):
        """Read-only correspondence for every score, before logical reduction.

        Settlement established these facts once. A report must also establish
        that their required evidence is still available, including for scores
        that have no useful-recovery review. Never reprice historical inputs.
        """
        job, key, attempt_id = receipt["job"], receipt["request"], receipt["attempt"]
        request = self.store.get("request", key, job=job)
        a = request["meta"]["capacity"]["anchor"]
        d = self.store.get("trial_decision", receipt["decision_id"], job=job)
        basis = self.store.json(d["basis_ref"], job)
        saved = request["meta"]["context_snapshot"]
        if (receipt["lineage"] != self.lineage or job not in t["members"]
                or receipt["status"] != "accepted_scored"
                or self.store.get("trial_attempt", attempt_id, job=job) != receipt
                or type(receipt["ordinal"]) is not int or not 1 <= receipt["ordinal"] <= t["attempts"]
                or request["kind"] != "normal" or request["status"] != "accepted"
                or a["method"] != "usage_anchor" or a["lineage"] != self.lineage
                or a["generation"] != t["generation"] or a["decision_id"] != d["id"]
                or d["request"] != key or d["job"] != job or d["lineage"] != self.lineage
                or d["generation"] != a["generation"] or d["disposition"] != "decisive"
                or d["otherwise_qualified"] is not True or a["basis_ref"] != d["basis_ref"]
                or basis["id"] != d["id"] or basis["lineage"] != self.lineage
                or basis["generation"] != d["generation"] or basis["eligibility"] is not True
                or basis["first_failure"] is not None or basis["implementation"] != t["implementation"]
                or basis["recipe"] != t["implementation"]["recipe"]
                or basis["snapshot"] != preparation_basis(saved["job"], saved["state"])
                or route_identity(request["route"]) != t["route_identity"]
                or basis["route_sha256"] != digest(request["route"])):
            raise Conflict("Scored claim, decision and frozen basis do not correspond.")
        pf, pa = (self.store.json(d[form]["ref"], job) for form in ("pf", "pa"))
        native_key = "messages" if request["route"]["protocol"] == "chat_completions" else "input"
        if (digest(pf) != d["pf"]["sha256"] or digest(pa) != d["pa"]["sha256"]
                or a["pf_ref"] != d["pf"]["ref"] or a["pf_sha256"] != digest(pf)
                or a["payload_sha256"] != digest(pa)
                or self.store.bytes(request["payload_ref"], job) != encode(pa)
                or pa[native_key][:-1] != pf[native_key][:-1]
                or {k:v for k,v in pa.items() if k != native_key} != {k:v for k,v in pf.items() if k != native_key}
                or d["pa"]["capacity"]["fits"] is not False or d["pa"]["anchor"]["fits"] is not True
                or receipt["reservation"] != a["reservation"] or a["reservation"] != d["pa"]["anchor"]["reservation"]):
            raise Conflict("Scored reservation or same-final-payload evidence changed.")
        # The source and predecessor behind the manifest must survive too;
        # validating a manifest hash is not validation of its references.
        source = self.store.bytes(saved["job"]["source_ref"], job)
        if sha256(source).hexdigest() != t["members"][job]["source_sha256"]:
            raise Conflict("Scored source differs from its enrolled hash.")
        predecessor = basis["predecessor"]
        prior = inspect_acceptance(self.store, job, predecessor["request"])
        prior_request = prior["request"]
        raw_prior = prior["accepted"]["usage"]
        usage = basis["normalized_usage"]
        if (prior["attempt_id"] != predecessor["attempt"] or prior["boundary"]["status"] != "compatible"
                or prior_request["status"] != "accepted" or prior["attempt"]["status"] != "accepted"
                or prior_request["payload_ref"] != predecessor["payload_ref"]
                or digest(self.store.json(predecessor["payload_ref"], job)) != predecessor["payload_sha256"]
                or prior_request["accepted_ref"] != predecessor["accepted_ref"]
                or prior["native"]["ref"] != predecessor["native_ref"] or prior["stream_ref"] != predecessor["stream_ref"]
                or usage != {**normalized_input(prior_request["route"]["protocol"], raw_prior),
                             "raw_usage_sha256": digest(raw_prior), "raw_usage_ref": prior["native"]["ref"]}
                or d["pa"]["anchor"]["normalized_prior"] != usage["input"]):
            raise Conflict("Scored predecessor or normalized anchor usage changed.")
        checked = inspect_acceptance(self.store, job, key)
        raw = checked["accepted"]["usage"]
        if (checked["attempt_id"] != attempt_id or checked["attempt"]["status"] != "accepted"
                or checked["boundary"]["status"] != "compatible"
                or receipt["accepted_ref"] != request["accepted_ref"]
                or digest(raw) != receipt["usage_sha256"]):
            raise Conflict("Scored accepted attempt or native usage changed.")
        if receipt.get("late_evidence_ref"):
            evidence = self.store.json(receipt["late_evidence_ref"], job)
            if (evidence["request"] != key or evidence["attempt"] != attempt_id
                    or evidence["accepted_ref"] != request["accepted_ref"]
                    or evidence["payload_sha256"] != digest(pa) or evidence["route_sha256"] != digest(request["route"])
                    or type(receipt.get("attribution_review_required")) is not bool):
                raise Conflict("Late usage does not identify this scored physical attempt.")
            # Late attribution supplements an originally unscorable reply;
            # it never substitutes another attempt for known native usage.
            try:
                normalized_input(request["route"]["protocol"], raw)
            except ValueError:
                pass
            else:
                raise Conflict("Late usage contradicts already attributable native usage.")
            raw = evidence["native_usage"]
        actual = normalized_input(request["route"]["protocol"], raw)["input"]
        if (type(receipt["input"]) is not int or receipt["input"] != actual
                or type(receipt["reservation"]) is not int or type(receipt["margin"]) is not int
                or receipt["margin"] != receipt["reservation"] - actual):
            raise Conflict("Scored input or margin contradicts attributable usage.")
        return receipt

    def report(self):
        with self.store.connection_scope(), self.store.read_snapshot():
            t = self.current()
            attempts = [r for r in self.store.records("trial_attempt") if r["lineage"] == self.lineage]
            decisions = [d for d in self.store.records("trial_decision") if d["lineage"] == self.lineage]
            unavailable_decisions = []
            for d in decisions:
                try:
                    basis = self.store.json(d["basis_ref"], d["job"])
                    if basis["id"] != d["id"] or basis["lineage"] != self.lineage:
                        raise Conflict("Decision basis identity changed.")
                    for form in (d["pf"], d.get("pa")):
                        if form is not None and digest(self.store.json(form["ref"], d["job"])) != form["sha256"]:
                            raise Conflict("Decision form identity changed.")
                except (ValueError, KeyError, TypeError, OSError) as exc:
                    unavailable_decisions.append({"decision_id": d["id"], "reason": type(exc).__name__})
            prohibitions = [p for p in self.store.records("trial_prohibition") if p["lineage"] == self.lineage]
            chains = [c for c in self.store.records("trial_chain") if c["lineage"] == self.lineage]
            verified_chains, unavailable_chains = [], []
            for c in chains:
                try:
                    if self.check_chain(c["job"], c["id"], c["review_ref"]) != c:
                        raise ValueError("Chain correspondence changed.")
                    verified_chains.append(c)
                except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile) as exc:
                    unavailable_chains.append({"request": c["id"], "reason": type(exc).__name__})
            scores, unavailable_scores = {}, []
            for r in attempts:
                if r.get("status") == "accepted_scored":
                    try:
                        checked = self.check_score(t, r)
                        scores[checked["request"]] = checked
                    except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError) as exc:
                        unavailable_scores.append({"request": r.get("request"), "attempt": r.get("attempt"),
                            "job": r.get("job"), "input": None, "margin": None,
                            "reason": str(exc) or type(exc).__name__})
            tasks = {job:self.store.maybe("job", job) or {} for job in t["members"]}
            requests = [r for job in t["members"] for r in self.store.records("request", job)]
        conversions = Counter(r["job"] for r in scores.values())
        families = Counter(t["members"][r["job"]]["family"] for r in scores.values())
        sources = {t["members"][r["job"]]["source_sha256"] for r in scores.values()}
        n = len(scores)
        reasons = []
        if unavailable_scores: reasons.append("required_score_evidence_unavailable")
        if unavailable_decisions: reasons.append("required_decision_evidence_unavailable")
        if t["attempts"] != len(attempts): reasons.append("physical_claim_receipts_incomplete")
        if n < 10: reasons.append("fewer_than_ten_logical_scores")
        if len(sources) < 4: reasons.append("fewer_than_four_scored_source_hashes")
        if len(families) < 3: reasons.append("fewer_than_three_scored_families")
        if n and any(v * 5 > n * 2 for v in [*conversions.values(), *families.values()]):
            reasons.append("score_concentration_exceeds_40pct")
        if any(r["status"] in {"claimed", "accepted_unscorable", "failed_or_unresolved"} or r.get("attribution_review_required") for r in attempts):
            reasons.append("required_attribution_unresolved")
        if t["stops"]: reasons.append("trial_stopped_requires_review")
        reviewed = {c["id"] for c in verified_chains if c["id"] in scores}
        if unavailable_chains: reasons.append("reviewed_chain_evidence_unavailable")
        if len(reviewed) < 5:
            reasons.append("fewer_than_five_reviewed_useful_recovery_chains")
        availability = self.unavailable(t, "")
        if availability == "not_enrolled": availability = None
        qualified = [d for d in decisions if d["otherwise_qualified"]]
        busy_ids = {d["id"] for d in qualified if d["disposition"] == "busy"}
        qualified_ids = {d["id"] for d in qualified}
        busy_ids.update(p["decision_id"] for p in prohibitions if p["reason"] == "slot_busy" and p["decision_id"] in qualified_ids)
        margins_by_conversion, margins_by_family = {}, {}
        for r in scores.values():
            margins_by_conversion.setdefault(r["job"], []).append(r["margin"])
            family = t["members"][r["job"]]["family"]
            margins_by_family.setdefault(family, []).append(r["margin"])
        return {"version": VERSION, "lineage": self.lineage, "offline": True,
                "state": t, "allocation_closed": t["attempts"] >= 20 or bool(availability),
                "pending_settlement": t["slot"], "physical_attempts": len(attempts),
                "charged_physical_attempts": t["attempts"], "exposure_gate": availability or "active",
                "scored_logical_requests": n, "scored_source_hashes": len(sources),
                "scored_conversions": dict(conversions), "scored_families": dict(families),
                "enrolled_conversions": len(t["members"]), "decisions": decisions, "attempts": attempts,
                "otherwise_qualified": len(qualified), "busy_qualified": len(busy_ids),
                "busy_fraction": None if not qualified else len(busy_ids)/len(qualified),
                "prohibitions": prohibitions, "logical_margins_by_conversion": margins_by_conversion,
                "logical_margins_by_family": margins_by_family,
                "reviewed_useful_recovery_chains": len(reviewed),
                "unavailable_chain_evidence": unavailable_chains,
                "unavailable_decision_evidence": unavailable_decisions,
                "unavailable_score_evidence": unavailable_scores, "score_validation": "accepted_trial_evidence_v1",
                "review": "reject" if any(s["reason"] in {"reservation_exceeded", "confirmed_context_overflow"} for s in t["stops"])
                          else "inconclusive" if reasons else "eligible_for_separate_expansion_review",
                "review_reasons": reasons, "fidelity_basis": "attributed_source_led_reviews_only",
                "task_outcomes": {job:{k:value.get(k) for k in ("status", "stop_reason", "content_claim", "delivery")}
                                  for job,value in tasks.items()},
                "actual_requests": [{"request":r["id"], "job":r["job"], "kind":r["kind"],
                                     "status":r["status"], "attempts":r["attempts"], "accepted_ref":r["accepted_ref"]}
                                    for r in requests],
                "cost": None, "savings": None, "fidelity": "not_established"}
