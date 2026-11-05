"""Shared immutable anchor validation; no diagnostics or dispatch authority."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
import json
import math
from .acceptance import inspect_acceptance
from .context import Context
from .context_outcomes import POLICY_DEFAULTS, policy_ref
from .schema import Route
from .storage import encode
from .tools import Dispatcher
from .usage_anchoring import RECIPE, append_charge, batch_units, digest, layout, normalized_input, price
from .working_context import snapshot

PREPARATION_FIELDS = ("job", "seq", "revision", "history", "handoff", "notes", "released", "pinned", "pin_views",
                      "repairs", "continuation_feedback", "context_waiting", "context_feedback", "context_latest", "resolutions")


def preparation_basis(job, state):
    # Graph routing/check labels do not change assembled bytes. Coordinate's
    # ordinary precheck and prepare must identify one preparation opportunity.
    selected = snapshot(job, state)
    defaults = {**POLICY_DEFAULTS, "history": [], "repairs": {}}
    selected["state"] = {key: state.get(key, defaults.get(key)) for key in PREPARATION_FIELDS}
    return selected

@dataclass(frozen=True)
class ObservationProfile:
    # A protocol/model alias is not an accounting declaration. The caller binds
    # an explicit declaration and coverage to this exact effective route.
    route_sha256: str
    declaration: str
    accounting: str = "inclusive_input_v1"
    edits: tuple[str, ...] = ("append", "notes", "release", "index_pin")
    image_rule: str = "configured_per_occurrence_uncalibrated_v1"

class ReadOnlyStore:
    """Projection can reuse immutable results but cannot materialize new work."""
    def __init__(self, store):
        self.store = store

    def __getattr__(self, name):
        if name not in {"get", "maybe", "records", "bytes", "json", "read_stream", "root"}:
            raise ValueError("Observer reconstruction requires unavailable immutable evidence")
        return getattr(self.store, name)

    def blob(self, job, kind, data, meta=None, *, key=None):
        old = self.store.get("blob", key, job=job) if key else None
        raw = data if isinstance(data, bytes) else encode(data)
        if not old or old["kind"] != kind or old["meta"] != (meta or {}) or self.store.bytes(key, job) != raw:
            raise ValueError("Observer cannot create a missing projection artifact")
        return old



def reproduce(context, request, saved):
    """Reproduce ordinary assembly or verify the committed same-content Pa."""
    anchor = request.get("meta", {}).get("capacity", {}).get("anchor")
    if not anchor:
        if request.get("meta", {}).get("admission_version"):
            raise ValueError("historical_anchor_provenance_missing")
        return context.normal(saved["job"], saved["state"])[0]
    d = context.store.get("trial_decision", anchor["decision_id"], job=request["job"])
    basis = context.store.json(anchor["basis_ref"], request["job"])
    if (d["request"] != request["id"] or d["lineage"] != anchor["lineage"]
            or d["generation"] != anchor["generation"] or d["basis_ref"] != anchor["basis_ref"]
            or basis["snapshot"] != preparation_basis(saved["job"], saved["state"])):
        raise ValueError("historical_anchor_basis_mismatch")
    if anchor["method"] != "usage_anchor":
        return context.normal(saved["job"], saved["state"])[0]
    pf = context.normal(saved["job"], saved["state"], capacity_deferral=False)[0]
    if digest(pf) != d["pf"]["sha256"] or encode(pf) != context.store.bytes(d["pf"]["ref"], request["job"]):
        raise ValueError("historical_full_local_form_unavailable")
    pa = context.store.json(d["pa"]["ref"], request["job"])
    key = "messages" if "messages" in pa else "input"
    if (digest(pa) != d["pa"]["sha256"] or anchor["payload_sha256"] != digest(pa)
            or pa[key][:-1] != pf[key][:-1]
            or {k:v for k,v in pa.items() if k != key} != {k:v for k,v in pf.items() if k != key}):
        raise ValueError("historical_anchored_form_unavailable")
    layout(pa, saved["job"]["route"]["protocol"])
    return pa


class AnchorEvaluator:
    def __init__(self, store, profile):
        self.store, self.profile = store, profile

    def predecessor(self, job, state):
        """First physical predecessor, never an older convenient usable anchor."""
        basis = {"eligibility": False, "first_failure": None, "recipe": RECIPE,
                 "cutoff": "committed_catalog_snapshot_at_initial_observation",
                 "profile": self.profile.__dict__ if self.profile else None,
                 "predecessor": None, "normalized_usage": None}
        def fail(reason):
            basis["first_failure"] = reason
            return basis, None
        with self.store.connection_scope(), self.store.read_snapshot():
            attempts = self.store.records("attempt", job["id"])
            if not attempts:
                return fail("no_previous_physical_send")
            if any(type(a.get("started")) not in (int, float) or not math.isfinite(a["started"]) for a in attempts):
                return fail("physical_send_order_unavailable")
            attempts.sort(key=lambda a: a["started"])
            attempt = attempts[-1]
            basis["predecessor"] = {"request": attempt["request"], "attempt": attempt["id"]}
            if len(attempts) > 1 and attempts[-2]["started"] == attempt["started"]:
                return fail("physical_send_order_ambiguous")
            request = self.store.get("request", attempt["request"], job=job["id"])
            if self.store.maybe("blob", f"accepted:{request['id']}") and request.get("status") != "accepted":
                return fail("staged_acceptance_requires_reconciliation")
            if request.get("kind") != "normal":
                return fail("compaction_or_non_normal_boundary")
            if request["id"] not in state.get("history", []) or state.get("history", [])[-1] != request["id"]:
                return fail("predecessor_not_retained_latest_normal")
            if request.get("status") != "accepted" or attempt.get("status") != "accepted":
                return fail("predecessor_not_settled_accepted")
            if self.store.maybe("conflict_resolution", request["id"]):
                return fail("historically_resolved_predecessor")
            checked = inspect_acceptance(self.store, job["id"], request["id"])
            if checked["attempt_id"] != attempt["id"] or checked["boundary"]["status"] != "compatible":
                return fail("accepted_attempt_or_boundary_mismatch")
            payload = self.store.json(request["payload_ref"], job["id"])
            basis["predecessor"].update(payload_ref=request["payload_ref"], payload_sha256=digest(payload),
                accepted_ref=request["accepted_ref"], native_ref=checked["native"]["ref"],
                stream_ref=checked["stream_ref"], settlement_status=request["status"])
            if request["route"] != job["route"]:
                return fail("incompatible_route_or_effective_settings")
            profile = self.profile
            if (profile is None or profile.route_sha256 != digest(job["route"]) or not profile.declaration
                    or profile.accounting != "inclusive_input_v1"):
                return fail("route_accounting_or_profile_undeclared")
            raw = self.store.json(checked["native"]["ref"], job["id"]).get("usage")
            try:
                usage = normalized_input(job["route"]["protocol"], raw)
            except ValueError as exc:
                return fail(str(exc))
            basis["normalized_usage"] = {**usage, "raw_usage_sha256": digest(raw),
                                          "raw_usage_ref": checked["native"]["ref"]}
            saved = request["meta"].get("context_snapshot")
            if not saved:
                return fail("predecessor_snapshot_unavailable")
            basis["eligibility"] = True
            return basis, {"request": request, "payload": payload, "snapshot": saved}

    def charged(self, job, state, payload, prior, capacity):
        """V2 verified native projections; only declared single edits qualify."""
        protocol = job["route"]["protocol"]
        old_state = prior["snapshot"]["state"]
        if state.get("history", []) != [*old_state.get("history", []), prior["request"]["id"]]:
            raise ValueError("history_not_one_attributable_normal_append")
        if state.get("handoff") != old_state.get("handoff"):
            raise ValueError("handoff_boundary_or_change")
        old, new = layout(prior["payload"], protocol), layout(payload, protocol)
        if old["task"]["context_policy_ref"] != policy_ref(old_state) or new["task"]["context_policy_ref"] != policy_ref(state):
            raise ValueError("policy_control_provenance_mismatch")
        ro = ReadOnlyStore(self.store)
        scripts = any(tool.get("function", tool).get("name") == "run_script"
                      for tool in prior["payload"].get("tools", []))
        # Reconstruct the actual frozen tool configuration. This advertises
        # definitions for comparison only; the read-only adapter executes none.
        context = Context(ro, Dispatcher(ro, scripts=scripts))
        # Reproduce the predecessor's actual frozen representation first. This
        # fails closed on changed assemblers or unavailable immutable evidence.
        reproduced = reproduce(context, prior["request"], prior["snapshot"])
        if encode(reproduced) != encode(prior["payload"]):
            raise ValueError("predecessor_reconstruction_mismatch")
        changes = [key for key, default in POLICY_DEFAULTS.items()
                   if state.get(key, default) != old_state.get(key, default)]
        baseline_state = {**state, **{k: deepcopy(old_state.get(k, v)) for k, v in POLICY_DEFAULTS.items()}}
        appended_deferrals = next((set(item["refs"]) for item in capacity.get("projection", {}).get("deferred", [])
                                  if item["request"] == prior["request"]["id"]), set())
        appended = context.group(job, prior["request"]["id"], baseline_state, deferred=appended_deferrals)
        if not changes:
            return append_charge(old, new, appended), "append", None
        if protocol != "chat_completions":
            raise ValueError("edit_profile_unsupported_for_protocol")
        baseline, cap = context.normal(job, baseline_state, capacity_deferral=False)
        base_layout = layout(baseline, protocol)
        base_units = append_charge(old, base_layout, appended)
        route = Route.model_validate(job["route"])
        pre_edit = price(base_units, route.image_tokens, protocol=protocol, native_image_units=True)
        if pre_edit["charge"] + prior["usage_input"] + cap.get("outcome_reserve", 0) > route.context_tokens - route.output_tokens:
            raise ValueError("pre_edit_anchor_does_not_fit")
        selected_ref = None
        if changes == ["notes"]:
            edit = "notes"
            allowed = {"continuation_notes", "context_policy_ref", "context_candidate_ref"}
        elif changes == ["released"]:
            before, after = set(old_state.get("released", [])), set(state.get("released", []))
            if not before.issubset(after) or len(after - before) != 1:
                raise ValueError("unsupported_release_change")
            selected_ref = next(iter(after-before))
            edit, allowed = "release", {"context_policy_ref", "context_candidate_ref"}
        elif set(changes).issubset({"pinned", "pin_views"}) and "pinned" in changes:
            before, after = set(old_state.get("pinned", [])), set(state.get("pinned", []))
            if not before.issubset(after) or len(after-before) != 1:
                raise ValueError("unsupported_pin_change")
            if before:
                raise ValueError("index_pin_insertion_with_existing_pins_unvalidated")
            selected_ref = next(iter(after-before))
            specs = context.pin_specs(job["id"], state, selected_ref)
            if specs != [{"ref": selected_ref, "view": "index"}] or any(
                    state.get("pin_views", {}).get(ref) != old_state.get("pin_views", {}).get(ref) for ref in before):
                raise ValueError("unsupported_pin_view_or_compound_change")
            edit, allowed = "index_pin", {"context_policy_ref", "context_candidate_ref"}
        else:
            raise ValueError("compound_or_unsupported_policy_change")
        if edit not in self.profile.edits:
            raise ValueError("edit_not_declared_in_profile")
        if any(base_layout["task"][k] != new["task"][k] for k in base_layout["task"] if k not in allowed):
            raise ValueError("unexplained_task_control_change")
        if base_layout["envelope"] != new["envelope"] or base_layout["system"] != new["system"]:
            raise ValueError("envelope_instructions_or_tools_changed")
        expected, expected_cap = context.normal(job, state, capacity_deferral=False)
        if encode(expected) != encode(payload):
            raise ValueError("forced_deferral_or_unexplained_reassembly")
        if selected_ref:
            # A release adapter is for a measured retained occurrence, not an
            # unrelated saved ref. Match source references as well as bytes.
            from .working_context import inventory
            refs = {r.get(k) for r in inventory(prior["payload"]["messages"])
                    for k in ("release_ref", "candidate_ref", "result_ref", "ref")}
            if selected_ref not in refs:
                raise ValueError("selected_reference_not_measured")
        # Match stable occurrences in order by assembler-defined message slots.
        # Pins can change the prefix length: compare prefix and each batch
        # independently, never search an arbitrary equal-content subsequence.
        charged = [new["task_unit"]]
        before_pins, after_pins = context.pins(job, baseline_state), context.pins(job, state)
        fixed_prefix = 1 if state.get("handoff") else 0
        if base_layout["middle"][:fixed_prefix] != new["middle"][:fixed_prefix]:
            raise ValueError("retained_handoff_changed")
        if before_pins != after_pins:
            charged.extend(after_pins)
        offset_old, offset_new = fixed_prefix + len(before_pins), fixed_prefix + len(after_pins)
        for request_id in state["history"]:
            a = context.group(job, request_id, baseline_state)
            b = context.group(job, request_id, state)
            if base_layout["middle"][offset_old:offset_old+len(a)] != a or new["middle"][offset_new:offset_new+len(b)] != b:
                raise ValueError("ordered_batch_identity_mismatch")
            if request_id == prior["request"]["id"]:
                charged.extend(b)
            elif a != b:
                if edit == "notes":
                    raise ValueError("notes_changed_retained_history")
                # Charge every changed/inserted unit; deleted measured units get
                # no credit. Native image groups are one occurrence per part.
                before_units = dict(batch_units(a))
                charged.extend(unit for identity, unit in batch_units(b) if before_units.get(identity) != unit)
            offset_old += len(a)
            offset_new += len(b)
        if offset_old != len(base_layout["middle"]) or offset_new != len(new["middle"]):
            raise ValueError("unsupported_tail_or_retained_layout")
        charged.append(new["feedback"])
        return charged, edit, {"selected_ref": selected_ref, "pre_edit_reservation": pre_edit["charge"] + prior["usage_input"],
            "pre_edit_payload_sha256": digest(baseline), "pre_edit_payload_bytes": len(encode(baseline)),
            "pre_edit_components": pre_edit, "scope": "internal_eligibility_projection_not_observed_normal_form",
            "exact_replay": "unavailable_digest_only"}
