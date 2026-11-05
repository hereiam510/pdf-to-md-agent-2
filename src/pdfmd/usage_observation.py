"""Opt-in preparation diagnostics, independent of admission and task commits.

Default Runtime construction supplies no observer. No trial, dispatch, replay or
enrollment authority exists here. All observer entry points are best effort.
"""
from __future__ import annotations

from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from time import perf_counter

from .anchor_basis import AnchorEvaluator, ObservationProfile, preparation_basis
from .acceptance import inspect_acceptance
from .schema import Route
from .storage import encode
from .usage_anchoring import RECIPE, digest, normalized_input, price, unit_manifest
from .working_context import snapshot



def safely(call, *args, **kwargs):
    """Telemetry must preserve both the ordinary return and its original error."""
    try:
        return call(*args, **kwargs)
    except Exception:
        return None



class DiagnosticSink:
    """Private scalars/references only, in a separate SQLite database."""
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=0.1)
        db.execute("CREATE TABLE IF NOT EXISTS observations (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
        return db

    def get(self, key):
        if not self.path.exists():
            return None
        with closing(self.connect()) as db:
            row = db.execute("SELECT data FROM observations WHERE id=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, value, *, preserve_actual=False):
        with closing(self.connect()) as db, db:
            # Preparation may hold a pre-settlement in-memory copy. Keep the
            # settlement writer's fields together, including calculated errors.
            db.execute("BEGIN IMMEDIATE")
            if preserve_actual:
                row = db.execute("SELECT data FROM observations WHERE id=?", (value["id"],)).fetchone()
                saved = json.loads(row[0]) if row else {"forms": []}
                for form in value["forms"]:
                    previous = next((f for f in saved["forms"] if f.get("payload_ref")
                        and f["payload_ref"] == form.get("payload_ref")
                        and f["payload_sha256"] == form["payload_sha256"]), None)
                    if previous and previous.get("actual") is not None:
                        form["actual"] = previous["actual"]
                        if "reservation_errors" in previous:
                            form["reservation_errors"] = previous["reservation_errors"]
            db.execute("INSERT INTO observations VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                       (value["id"], encode(value).decode("utf-8")))

    def records(self):
        if not self.path.exists():
            return []
        with closing(self.connect()) as db:
            return [json.loads(row[0]) for row in db.execute("SELECT data FROM observations ORDER BY rowid")]



class UsageObserver(AnchorEvaluator):
    def __init__(self, store, *, profile: ObservationProfile | None = None, sink=None):
        self.store, self.profile = store, profile
        self.sink = sink if sink is not None else DiagnosticSink(store.root / "usage-observations.sqlite")
        self._opportunities = {}
        self.work = {}

    def invoke(self, method, *args, opportunity=None, **kwargs):
        """Measure complete observer work, including failed reads/writes."""
        started = perf_counter()
        result = None
        try:
            result = safely(method, *args, **kwargs)
            return result
        finally:
            measured = opportunity or (result if isinstance(result, Opportunity) else None)
            key = measured.value["id"] if measured else "observer_lifecycle"
            self.work[key] = self.work.get(key, 0.0) + perf_counter() - started

    def start(self, job, state, key, *, existing_only=False):
        identity = digest({"request": key, "snapshot": preparation_basis(job, state), "recipe": RECIPE,
                           "profile": self.profile.__dict__ if self.profile else None})
        if identity not in self._opportunities:
            restored = self.sink.get(identity)
            if existing_only and restored is None:
                return None
            self._opportunities[identity] = Opportunity(self, job, state, key, identity, restored)
        return self._opportunities[identity]

    def link(self, job, key):
        """Refresh actual attempt facts after normal settlement; never send."""
        request = self.store.get("request", key, job=job)
        outcome = {"request": key, "attempts": list(request["attempts"]), "status": request["status"],
                   "accepted_ref": request.get("accepted_ref"), "normalized_usage": None}
        try:
            if request["status"] == "accepted":
                checked = inspect_acceptance(self.store, job, key)
                raw = self.store.json(checked["native"]["ref"], job).get("usage")
                outcome["attempt"] = checked["attempt_id"]
        except Exception as exc:
            outcome["usage_unavailable"] = str(exc) or type(exc).__name__
            outcome["observer_error"] = type(exc).__name__
        for value in self.sink.records():
            if value["request_key"] != key or value["job"] != job:
                continue
            actual = deepcopy(outcome)
            if "attempt" in actual:
                # Older rows bind the declaration in basis.profile. Never use
                # the profile of whichever observer happens to relink them.
                bound = value.get("profile", (value.get("basis") or {}).get("profile"))
                try:
                    if (bound and bound["route_sha256"] == digest(request["route"])
                            and bound["accounting"] == "inclusive_input_v1" and bound["declaration"]):
                        actual["normalized_usage"] = {**normalized_input(request["route"]["protocol"], raw),
                            "raw_usage_ref": checked["native"]["ref"], "raw_usage_sha256": digest(raw)}
                    else:
                        actual["usage_unavailable"] = "route_accounting_or_profile_undeclared"
                except Exception as exc:
                    actual["usage_unavailable"] = str(exc) or type(exc).__name__
                    actual["observer_error"] = type(exc).__name__
            for form in value["forms"]:
                if form.get("payload_ref") == request["payload_ref"]:
                    form["actual"] = actual
                    measured = actual["normalized_usage"]
                    form["reservation_errors"] = ({name: form[name]["reservation"] - measured["input"]
                        for name in ("full_local", "anchored", "decoded_full_local") if form.get(name)
                        and form[name].get("reservation") is not None} if measured else None)
            self.sink.put(value)


class Opportunity:
    def __init__(self, owner, job, state, key, identity, restored):
        self.owner, self.job, self.state = owner, deepcopy(job), deepcopy(state)
        self.prior = None
        self.value = restored or {"id": identity, "job": job["id"], "request_key": key,
            "snapshot_sha256": digest(snapshot(job, state)), "mode": "observation_only",
            "profile": owner.profile.__dict__ if owner.profile else None,
            "active_time_policy": "observer_work_outside_ordinary_active_budget_v1",
            "governing_method": "deployed_full_local_F", "recipe": RECIPE, "basis": None,
            "forms": [], "obstructions": [], "ordinary_disposition": None,
            "evaluation_and_flush_seconds": 0.0, "observation_calls": 0, "deduplicated_calls": 0,
            "distinct_evaluations": 0, "new_payload_bytes": 0}

    def persist(self):
        self.owner.sink.put(self.value, preserve_actual=True)

    def observe(self, role, payload, capacity):
        started = perf_counter()
        self.value["observation_calls"] += 1
        evaluated_form = None
        try:
            identity = digest(payload)
            for form in self.value["forms"]:
                if form["payload_sha256"] == identity:
                    self.value["deduplicated_calls"] += 1
                    if role not in form["roles"]:
                        form["roles"].append(role)
                    return
            if len(self.value["forms"]) >= 2:
                raise ValueError("observation_form_limit")
            form = {"roles": [role], "payload_sha256": identity, "payload_bytes": len(encode(payload)),
                    "payload_ref": None, "exact_replay": "unavailable_digest_only",
                    "basis_id": None, "eligibility": False, "first_failure": None,
                    "full_local": {"reservation": capacity["input_estimate"], "fits": capacity["fits"],
                                   "components": deepcopy(capacity)},
                    "anchored": None, "decoded_full_local": None, "actual": None,
                    "comparator_status": {"full_local": {"status": "available"},
                        "decoded_full_local": {"status": "unavailable", "reason": "not_computed"},
                        "anchored": {"status": "unavailable", "reason": "not_computed"}},
                    "allowance": capacity["capacity"] - capacity["output_reserve"],
                    "image_rule": self.owner.profile.image_rule if self.owner.profile else None}
            self.value["forms"].append(form)
            evaluated_form = form
            self.value["distinct_evaluations"] += 1
            form["ordered_units"] = unit_manifest(payload)
            if self.value["basis"] is None:
                try:
                    self.value["basis"], self.prior = self.owner.predecessor(self.job, self.state)
                except Exception as exc:
                    self.value["basis"] = {"eligibility": False, "first_failure": "predecessor_read_failed:" + type(exc).__name__,
                        "recipe": RECIPE, "cutoff": "committed_catalog_snapshot_at_initial_observation",
                        "predecessor": None, "normalized_usage": None, "observer_error": type(exc).__name__,
                        "failure_detail": str(exc)}
                self.value["basis"]["id"] = digest(self.value["basis"])
            basis = self.value["basis"]
            form["basis_id"] = basis["id"]
            form["first_failure"] = basis["first_failure"]
            route = Route.model_validate(self.job["route"])
            # Distinctly labeled decoded full-local shadow, retaining today's
            # 25%/1024 structure. It never replaces deployed F.
            try:
                full = price(payload, route.image_tokens, protocol=route.protocol)
                reservation = full["split_counts"][0] + (full["split_counts"][0] + 3)//4 + full["image_cost"] + 1024 + capacity.get("outcome_reserve", 0)
                form["decoded_full_local"] = {"method": "decoded_full_local_o200k_25pct_1024_v1",
                    "reservation": reservation, "fits": reservation <= form["allowance"], "components": {
                        "text_tokens": full["split_counts"][0], "text_uncertainty": (full["split_counts"][0]+3)//4,
                        "native_overhead_reserve": 1024, "outcome_reserve": capacity.get("outcome_reserve", 0),
                        **{key: full[key] for key in ("images", "image_cost", "image_occurrences", "text_features")}}}
                form["comparator_status"]["decoded_full_local"] = {"status": "available"}
            except Exception as exc:
                form["comparator_status"]["decoded_full_local"] = {"status": "unavailable",
                    "reason": str(exc) or type(exc).__name__, "observer_error": type(exc).__name__}
            if not basis["eligibility"]:
                form["comparator_status"]["anchored"] = {"status": "unavailable", "reason": basis["first_failure"]}
                return
            if self.prior is None:
                # Restore only the already selected evidence. No later usage
                # can change a missing measurement at the original cutoff.
                bound = basis["predecessor"]
                request = self.owner.store.get("request", bound["request"], job=self.job["id"])
                previous = self.owner.store.json(bound["payload_ref"], self.job["id"])
                if digest(previous) != bound["payload_sha256"] or request["payload_ref"] != bound["payload_ref"]:
                    raise ValueError("bound_basis_reconstruction_mismatch")
                self.prior = {"request": request, "payload": previous, "snapshot": request["meta"]["context_snapshot"]}
            self.prior["usage_input"] = basis["normalized_usage"]["input"]
            units, edit, evidence = self.owner.charged(self.job, self.state, payload, self.prior, capacity)
            if edit not in self.owner.profile.edits:
                raise ValueError("edit_not_declared_in_profile")
            charge = price(units, route.image_tokens, protocol=route.protocol, native_image_units=True)
            if charge["images"] and self.owner.profile.image_rule != "configured_per_occurrence_uncalibrated_v1":
                raise ValueError("unsupported_image_rule")
            reservation = self.prior["usage_input"] + charge["charge"] + capacity.get("outcome_reserve", 0)
            form.update(eligibility=True, anchored={"method": RECIPE["pricing"], "reservation": reservation,
                "fits": reservation <= form["allowance"], "normalized_prior": self.prior["usage_input"],
                "components": charge, "outcome_reserve": capacity.get("outcome_reserve", 0),
                "edit": edit, "edit_evidence": evidence})
            form["comparator_status"]["anchored"] = {"status": "available"}
        except Exception as exc:
            if evaluated_form is not None:
                form = evaluated_form
                if form["first_failure"] is None:
                    form["first_failure"] = str(exc) or type(exc).__name__
                form["observer_error"] = type(exc).__name__
                form["comparator_status"]["anchored"] = {"status": "unavailable",
                    "reason": str(exc) or type(exc).__name__, "observer_error": type(exc).__name__}
            else:
                self.value["obstructions"].append({"role": role, "reason": type(exc).__name__})
        finally:
            self.value["evaluation_and_flush_seconds"] += perf_counter() - started
            before = perf_counter()
            safely(self.persist)
            self.value["evaluation_and_flush_seconds"] += perf_counter() - before

    def finish(self, disposition, *, request=None, obstruction=None):
        self.prior = None  # Do not retain hydrated predecessor payloads for the task lifetime.
        self.value["ordinary_disposition"] = disposition
        if obstruction:
            roles = {r for f in self.value["forms"] for r in f["roles"]}
            for role in ("initial_complete", "final_ordinary"):
                if role not in roles:
                    item = {"role": role, "reason": obstruction}
                    if item not in self.value["obstructions"]:
                        self.value["obstructions"].append(item)
        if request:
            self.value["ordinary_request"] = {"id": request["id"], "kind": request["kind"],
                "payload_ref": request["payload_ref"], "capacity": request["meta"].get("capacity")}
            if request["kind"] == "normal":
                try:
                    # Verify the retained source itself, not only its catalogue
                    # hash. A diagnostic read fault cannot undo the freeze.
                    raw = self.owner.store.bytes(request["payload_ref"], self.job["id"])
                    descriptor = self.owner.store.get("blob", request["payload_ref"], job=self.job["id"])
                    for form in self.value["forms"]:
                        if form["payload_sha256"] == descriptor["sha256"] and form["payload_bytes"] == len(raw):
                            form.update(payload_ref=request["payload_ref"], exact_replay="immutable_request_input")
                            form["actual"] = {"request": request["id"], "attempts": request["attempts"],
                                              "status": request["status"], "normalized_usage": None}
                except Exception as exc:
                    self.value["ordinary_request"]["observer_reference_error"] = type(exc).__name__
        if disposition == "compaction":
            item = {"role": "final_ordinary", "reason": "ordinary_compaction_selected"}
            if item not in self.value["obstructions"]:
                self.value["obstructions"].append(item)
        self.persist()
