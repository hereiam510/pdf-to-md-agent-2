from __future__ import annotations

import json
from hashlib import sha256
import sqlite3
from typing import TypedDict

from filelock import FileLock, Timeout
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from .active_time import ActiveTime
from .context import Context, HandoffRejected
from .context_updates import ContextUpdates
from .context_revisions import ContextRevisions
from .nexus import Nexus, StopRun, instruction_basis
from .storage import Conflict, Store, encode
from .tools import Dispatcher, UnknownEffect
from .working_context import inspect as inspect_working_context, snapshot as context_snapshot


class State(TypedDict, total=False):
    job: str
    seq: int
    revision: int
    history: list[str]
    handoff: str | None
    notes: str
    released: list[str]
    pinned: list[str]
    pin_views: dict[str, list[dict]]
    pending: str | None
    next: str
    terminal: bool
    repairs: dict[str, dict]
    continuation_feedback: str | None
    context_waiting: str | None
    context_feedback: str | None
    context_check: str | None
    context_latest: str | None
    report: dict | None


class Runtime:
    def __init__(self, store: Store, nexus: Nexus, *, scripts: bool = False):
        self.store, self.nexus = store, nexus
        self.active_time = ActiveTime(store)
        self.nexus.active_time = self.active_time
        self.dispatcher = Dispatcher(store, scripts=scripts)
        self.dispatcher.active_time = self.active_time
        self.context = Context(store, self.dispatcher)
        self.context_updates = ContextUpdates(self.context)
        self.context_revisions = ContextRevisions(self.context)
        self.connection = sqlite3.connect(store.root / "graph.sqlite", check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        builder = StateGraph(State)
        builder.add_node("coordinate", self.coordinate)
        builder.add_node("prepare", self.prepare)
        builder.add_node("model", self.model)
        builder.add_node("tools", self.tools)
        builder.add_node("compact", self.compact)
        builder.add_edge(START, "coordinate")
        builder.add_conditional_edges("coordinate", lambda state: END if state.get("terminal") else "prepare", {END: END, "prepare": "prepare"})
        builder.add_conditional_edges("prepare", lambda state: state["next"], {"model": "model", "compact": "compact"})
        builder.add_conditional_edges("model", lambda state: state["next"], {"prepare": "coordinate", "tools": "tools"})
        builder.add_edge("tools", "coordinate")
        builder.add_edge("compact", "coordinate")
        self.graph = builder.compile(checkpointer=SqliteSaver(self.connection))

    def coordinate(self, state: State):
        """Commit outcomes before request preparation or a valid terminal report."""
        self.active_time.checkpoint()
        job = self.store.get("job", state["job"])
        key = f"{job['id']}:{state['seq']}:{state['revision']}"
        changes = self.context_updates.recover(job, state, key)
        state = {**state, **changes}
        if job["cancel_requested"]:
            raise StopRun("cancelled", "Stopped at a settled tool-batch boundary.")
        repairs = {kind: item for kind, item in state.get("repairs", {}).items()
                   if item["basis"] == self.repair_basis(job)}
        state = {**state, "repairs": repairs}
        frozen = self.store.maybe("request", key)
        if frozen is None and state.get("context_waiting"):
            changes.update(self.context_updates.resolve(job, state, key))
            state = {**state, **changes}
        report = state.get("report")
        terminal = bool(report and report["instruction_basis"] == instruction_basis(job))
        if terminal:
            value = report["intent"]
            self.store.update_job(job["id"], status="waiting" if value["state"] == "waiting" else "completed" if value["state"] == "complete" else "paused",
                stop_reason="agent_report", content_claim="complete" if value["state"] == "complete" else "partial",
                delivery=value.get("version_id"), last_message=value["message"])
        elif frozen is None and not state.get("context_waiting"):
            # Persist diagnostic obstruction without reverting a committed result.
            try:
                self.context_updates.continuation(job, state)
                changes["context_check"] = None
            except StopRun as exc:
                changes.update(self.context_updates.wait(job, state, exc.reason, str(exc)))
        return {**changes, "repairs": repairs, "terminal": terminal}

    def prepare(self, state: State):
        self.active_time.checkpoint()
        job = self.store.get("job", state["job"])
        if job["cancel_requested"]:
            raise StopRun("cancelled", "Stopped at a settled tool-batch boundary.")
        key = f"{job['id']}:{state['seq']}:{state['revision']}"
        repairs = state.get("repairs", {})
        request = self.store.maybe("request", key)
        if request is None:
            payload, meta, kind = self.context_updates.continuation(job, state)
            if repairs.get(kind, {}).get("count", 0) > job["limits"].get("max_response_repairs", 2):
                raise StopRun("response_repair_exhausted", f"Automatic {kind} correction limit reached. Saved work, candidates and replies remain available. Continue does not reset this correction episode.")
            request = self.nexus.freeze(job["id"], key, payload, kind, {**meta, "repairs": repairs,
                **({"context_snapshot": context_snapshot(job, state)} if kind == "normal" else {})})
        return {"pending": key, "next": "compact" if request["kind"] == "compaction" else "model", "terminal": False,
                "repairs": repairs}

    @staticmethod
    def repair_basis(job: dict) -> str:
        return sha256(encode({"head": job["head"], "amendments": job["amendments"]})).hexdigest()

    def repair(self, state: State, kind: str, code: str, message: str) -> dict:
        """Persist feedback before advancing the graph; re-entry returns the same transition."""
        job, key = state["job"], state["pending"]
        ref = f"repair:{key}"
        saved = self.store.maybe("blob", ref)
        if saved is None:
            basis = self.repair_basis(self.store.get("job", job))
            previous = state.get("repairs", {}).get(kind, {})
            count = previous.get("count", 0) + 1 if previous.get("basis") == basis else 1
            request = self.store.get("request", key, job=job)
            self.store.blob(job, "response_repair", {"request": key, "kind": kind, "code": code,
                            "message": message, "candidate_ref": request["accepted_ref"], "basis": basis,
                            "count": count}, key=ref)
        feedback = self.store.json(ref, job)
        self.store.event_once(job, "response_correction", key,
                              {"request": key, "kind": kind, "code": code, "feedback_ref": ref})
        changes = {"repairs": {**state.get("repairs", {}), kind: {"feedback_ref": ref, "request": key,
                   "basis": feedback["basis"], "count": feedback["count"]}},
                   "revision": state["revision"] + 1, "pending": None, "next": "prepare", "terminal": False}
        if kind == "normal":
            changes.update(history=[*state["history"], key], seq=state["seq"] + 1)
        return changes

    def model(self, state: State):
        reply = self.nexus.send(state["job"], state["pending"])
        if reply["text"]:
            self.store.update_job(state["job"], last_message=reply["text"])
        if reply["calls"]:
            return {"terminal": False, "next": "tools"}
        return self.repair(state, "normal", "missing_tool_call",
                           "The last response contained text but no tool call or explicit report. "
                           "If work remains, choose a tool and continue. To finish, deliver partial work, or ask a necessary "
                           "user question, call report with the appropriate state. No new user answer has arrived. "
                           "If the last text asked a necessary question, use report(waiting) with that question; do not assume an answer. "
                           "Do not assume the task is complete.")

    def tools(self, state: State):
        job, key = state["job"], state["pending"]
        request = self.store.get("request", key, job=job)
        reply = self.store.json(request["accepted_ref"], job)
        working = self.context_revisions.start(job, state)
        operations, errors = [], []
        historical = {}
        report = None
        for index, call in enumerate(reply["calls"]):
            self.active_time.checkpoint()
            operation = f"{key}:{index}"
            result = self.dispatcher.reconcile(job, operation, call["name"], call["arguments"])
            current = self.store.get("job", job)
            if result is None:
                if current["cancel_requested"]:
                    raise StopRun("cancelled", "Stopped before the next tool. The accepted pending batch is preserved.")
                if request["instruction_basis"] != instruction_basis(current):
                    result = self.dispatcher.skip(job, operation, call["name"], call["arguments"])
                else:
                    elapsed = self.active_time.elapsed(current)
                    if elapsed >= current["limits"]["max_active_seconds"]:
                        raise StopRun("budget_exhausted", "Stopped before a new tool because the persistent active-time budget is exhausted.")
                    self.dispatcher.context_preflight = lambda intent, op, candidate: self.context_revisions.capture(
                        current, state, working, intent, op, candidate)
                    self.dispatcher.context_inspector = lambda **args: inspect_working_context(self.context, request, current, **args)
                    try:
                        result = self.dispatcher.execute(job, operation, call["name"], call["arguments"])
                    finally:
                        self.dispatcher.context_preflight = None
                        self.dispatcher.context_inspector = None
            self.active_time.checkpoint()
            data = result["data"]
            if call["name"] == "context_update":
                if "context_intent" in data:
                    # Previously committed per-tool effects are historical facts.
                    historical = data.get("context_policy") or self.context.policy(job, {**state, **historical}, data["context_intent"])
                    working["policy"].update(historical)
                    continue
                operations.append(operation)
                if not result["ok"] or "context_saved" not in data:
                    errors.append({"operation": operation, "result_ref": result["result_ref"], "candidate_ref": result["candidate_ref"],
                                   "message": data.get("error", data.get("message", "Context operation did not validate."))})
                else:
                    saved = data["context_saved"]
                    working.update(policy=saved["policy"], base_ref=saved["base_ref"], selection_required=False)
            if result["ok"] and "report_intent" in data:
                report = {"intent": data["report_intent"], "instruction_basis": request["instruction_basis"]}
        waiting = state.get("context_waiting")
        if operations:
            waiting = self.context_revisions.complete(job, state, request, operations, working, errors)
        return {**historical, "context_waiting": waiting, "context_latest": waiting or state.get("context_latest"),
                "context_check": None, "history": [*state["history"], key], "seq": state["seq"] + 1,
                "revision": state["revision"] + 1, "pending": None, "terminal": False, "report": report,
                "continuation_feedback": None,
                "repairs": {kind: value for kind, value in state.get("repairs", {}).items() if kind != "normal"}}

    def compact(self, state: State):
        request = self.store.get("request", state["pending"], job=state["job"])
        reply = self.nexus.send(state["job"], state["pending"])
        if reply["calls"]:
            return self.repair(state, "compaction", "unexpected_tools",
                               "No tools were executed. Return only the six-field handoff JSON, without tool calls.")
        try:
            result = self.context.apply_handoff(self.store.get("job", state["job"]), state, reply["text"], request["meta"], state["pending"])
        except HandoffRejected as exc:
            return self.repair(state, "compaction", "invalid_handoff", str(exc))
        return {**result, "pending": None,
                "repairs": {kind: value for kind, value in state.get("repairs", {}).items() if kind != "compaction"}}

    def pending_request(self, job: str) -> dict | None:
        """Return the request owned by the current resumable graph position."""
        snapshot = self.graph.get_state({"configurable": {"thread_id": job}})
        state = snapshot.values
        if not snapshot.next or not state:
            return None
        key = state.get("pending") or f"{job}:{state['seq']}:{state['revision']}"
        return self.store.maybe("request", key)

    def accepted_locally(self, request: dict) -> bool:
        return bool(request.get("accepted_ref") or self.store.maybe("blob", f"accepted:{request['id']}"))

    def compaction_recovery(self, job: str) -> dict | None:
        """Offer an explicit choice only for the current unresolved compaction."""
        request = self.pending_request(job)
        if (request and request["kind"] == "compaction" and request["status"] == "unknown"
                and not self.accepted_locally(request)
                and self.store.maybe("blob", f"continuation:{request['id']}") is None):
            return {"request": request["id"]}
        return None

    def validate_compaction_recovery(self, job: str, selected: str) -> None:
        """Validate before changing settings; a stale click grants no new choice."""
        request = self.pending_request(job)
        if (not isinstance(selected, str) or not selected or not request
                or selected != request["id"] or request["kind"] != "compaction"):
            raise Conflict("The selected compaction is no longer the task's pending request. Refresh the task before choosing recovery.")
        # A response saved before its request pointer wins over a fresh send.
        if self.accepted_locally(request):
            return
        receipt = self.store.maybe("blob", f"continuation:{selected}")
        if receipt and self.store.json(receipt["ref"], job).get("reason") == "explicit_compaction_recovery":
            return  # The same committed choice may still need its graph projection.
        if request["status"] != "unknown" or receipt:
            raise Conflict("Only an unresolved unknown compaction can receive this recovery choice.")

    def resume_pending(self, state: State, *, continue_failed: bool,
                       recover_compaction_request: str | None = None) -> dict | None:
        """Persist a chosen new-request transition before changing the graph checkpoint."""
        job = self.store.get("job", state["job"])
        key = state.get("pending") or f"{job['id']}:{state['seq']}:{state['revision']}"
        if self.store.maybe("request", key) is None:
            return None
        ref = f"continuation:{key}"
        receipt = self.store.maybe("blob", ref)
        if receipt is None:
            request = self.nexus.reconcile(job["id"], key)
            # A locally accepted reply always wins. The explicit compaction choice
            # creates a successor; it never changes this request's replay gate.
            if request["accepted_ref"] or job["cancel_requested"]:
                return None
            unsent_amended = (request["status"] == "prepared" and not request["attempts"]
                              and request["instruction_basis"] != instruction_basis(job))
            failed = request["status"] in {"http_error", "rejected"} and continue_failed
            recover_compaction = (recover_compaction_request == key and request["kind"] == "compaction"
                                  and request["status"] == "unknown")
            if not (unsent_amended or failed or recover_compaction):
                return None
            message = ("The user explicitly chose a new continuation after this unknown compaction. "
                       "No handoff or tools from the unknown response were applied. The original request, payload and attempts remain unchanged. "
                       "Upstream completion and cost are unknown; a new request may duplicate upstream computation."
                       if recover_compaction else
                       "The unsent prepared request was superseded by new user instructions. No attempt was made."
                       if unsent_amended else
                       "The user chose Continue after a failed or rejected request. No tools from that response were executed. "
                       "The original request and response records remain available. HTTP failure does not establish remote cancellation or known cost. "
                       "Follow the latest user instructions and choose how to continue or repair the submission.")
            choice = ({"authorization": {"kind": "human_compaction_recovery", "request": key},
                       "payload_ref": request["payload_ref"]} if recover_compaction else {})
            self.store.blob(job["id"], "request_continuation", {"request": key, "status": request["status"],
                            "reason": "explicit_compaction_recovery" if recover_compaction else
                                      "new_instructions" if unsent_amended else request.get("failure", {}).get("reason", request["status"]),
                            "message": message, "diagnostic": request.get("failure", {}).get("message"), "response_ref": request.get("response_ref"),
                            "attempts": list(request["attempts"]), "revision": state["revision"] + 1, **choice}, key=ref)
        feedback = self.store.json(ref, job["id"])
        self.store.event_once(job["id"], "request_continued", key, {"request": key, "feedback_ref": ref, "reason": feedback["reason"]})
        recovered = self.context_updates.recover(job, state, key)
        return {**recovered, "revision": feedback["revision"], "pending": None, "next": "prepare", "terminal": False,
                "continuation_feedback": ref}

    def run(self, job: str, lock: FileLock | None = None, *, continue_failed: bool = False,
            recover_compaction_request: str | None = None) -> None:
        if lock is None:
            lock = FileLock(str(self.store.root / f"task-{job}.lock"))
            try:
                lock.acquire(timeout=0)
            except Timeout as exc:
                raise StopRun("already_running", "This task already has an active executor.") from exc
        if recover_compaction_request is not None:
            try:
                self.validate_compaction_recovery(job, recover_compaction_request)
            except BaseException:
                lock.release()
                raise
        config = {"configurable": {"thread_id": job}, "recursion_limit": 1_000_000}
        try:
            self.active_time.start(job)
            snapshot = self.graph.get_state(config)
            if snapshot.next:
                continuation = self.resume_pending(dict(snapshot.values), continue_failed=continue_failed,
                                                   recover_compaction_request=recover_compaction_request)
                if continuation:
                    # Supported state update: complete this transition as the model node and route to prepare.
                    self.graph.update_state(config, continuation, as_node="model")
                elif snapshot.next == ("prepare",):
                    key = f"{job}:{snapshot.values['seq']}:{snapshot.values['revision']}"
                    if self.store.maybe("request", key) is None:
                        # Re-evaluate current instructions/settings and the correction
                        # episode before any unfrozen preparation. Never rebuild F.
                        self.graph.update_state(config, {"next": "prepare"}, as_node="model")
                self.graph.invoke(None, config, durability="sync")
            else:
                initial = dict(snapshot.values) if snapshot.values else {"job": job, "seq": 0, "revision": 0, "history": [],
                                                                       "handoff": None, "notes": "", "released": [], "pinned": []}
                initial.update(terminal=False, pending=None, report=None)
                self.graph.invoke(initial, config, durability="sync")
        except StopRun as exc:
            self.store.update_job(job, status="cancelled" if exc.reason == "cancelled" else "blocked",
                                  stop_reason=exc.reason, last_message=str(exc))
            self.store.event(job, "stopped", {"reason": exc.reason, "message": str(exc)})
        except UnknownEffect as exc:
            self.store.update_job(job, status="blocked", stop_reason="local_outcome_unknown", last_message=str(exc))
        except Exception as exc:
            self.store.update_job(job, status="blocked", stop_reason="internal_error", last_message=f"Local engine error: {type(exc).__name__}. Saved work is retained.")
            raise
        finally:
            try:
                self.active_time.checkpoint(close=True)
            finally:
                lock.release()

    def close(self):
        self.connection.close()
