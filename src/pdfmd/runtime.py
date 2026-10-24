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
from .nexus import Nexus, StopRun, instruction_basis
from .storage import Store, encode
from .tools import Dispatcher, UnknownEffect


class State(TypedDict, total=False):
    job: str
    seq: int
    revision: int
    history: list[str]
    handoff: str | None
    notes: str
    released: list[str]
    pinned: list[str]
    pending: str | None
    next: str
    terminal: bool
    repairs: dict[str, dict]
    continuation_feedback: str | None


class Runtime:
    def __init__(self, store: Store, nexus: Nexus, *, scripts: bool = False):
        self.store, self.nexus = store, nexus
        self.active_time = ActiveTime(store)
        self.nexus.active_time = self.active_time
        self.dispatcher = Dispatcher(store, scripts=scripts)
        self.dispatcher.active_time = self.active_time
        self.context = Context(store, self.dispatcher)
        self.connection = sqlite3.connect(store.root / "graph.sqlite", check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        builder = StateGraph(State)
        builder.add_node("prepare", self.prepare)
        builder.add_node("model", self.model)
        builder.add_node("tools", self.tools)
        builder.add_node("compact", self.compact)
        builder.add_edge(START, "prepare")
        builder.add_conditional_edges("prepare", lambda state: state["next"], {"model": "model", "compact": "compact"})
        builder.add_conditional_edges("model", lambda state: state["next"], {"prepare": "prepare", "tools": "tools"})
        builder.add_conditional_edges("tools", lambda state: END if state["terminal"] else "prepare", {END: END, "prepare": "prepare"})
        builder.add_edge("compact", "prepare")
        self.graph = builder.compile(checkpointer=SqliteSaver(self.connection))

    def prepare(self, state: State):
        self.active_time.checkpoint()
        job = self.store.get("job", state["job"])
        if job["cancel_requested"]:
            raise StopRun("cancelled", "Stopped at a settled tool-batch boundary.")
        # A new human instruction or document head starts a new correction episode.
        # Merely restarting/pressing Continue does not reset it.
        repairs = {kind: item for kind, item in state.get("repairs", {}).items()
                   if item["basis"] == self.repair_basis(job)}
        for kind, item in repairs.items():
            if item["count"] > job["limits"].get("max_response_repairs", 2):
                raise StopRun("response_repair_exhausted",
                              f"Automatic {kind} correction limit reached. Saved work and replies are retained. "
                              "Add instructions or edit the saved document before starting a new correction episode.")
        state = {**state, "repairs": repairs}
        key = f"{job['id']}:{state['seq']}:{state['revision']}"
        # A frozen request wins over current pointers and newly reconstructed input.
        request = self.store.maybe("request", key)
        if request is None:
            payload, capacity = self.context.normal(job, state)
            if capacity["fits"]:
                request = self.nexus.freeze(job["id"], key, payload, "normal", {"capacity": capacity, "repairs": repairs})
            else:
                payload, meta = self.context.compact_request(job, state)
                request = self.nexus.freeze(job["id"], key, payload, "compaction", {**meta, "repairs": repairs})
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
        released, pinned = set(state["released"]), set(state["pinned"])
        notes, report = state["notes"], None
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
                    result = self.dispatcher.execute(job, operation, call["name"], call["arguments"])
            self.active_time.checkpoint()
            if not result["ok"]:
                continue
            data = result["data"]
            if "context_intent" in data:
                intent = data["context_intent"]
                for ref in intent.get("release", []):
                    released.add(ref)
                    pinned.discard(ref)
                for ref in intent.get("pin", []):
                    pinned.add(ref)
                    released.discard(ref)
                if "notes" in intent:
                    notes = intent["notes"]
            if "report_intent" in data:
                report = data["report_intent"]
        # Restore historical context effects, but an old report cannot terminate a new instruction.
        if request["instruction_basis"] != instruction_basis(self.store.get("job", job)):
            report = None
        # One deterministic policy settlement per complete accepted batch.
        changes = {"released": sorted(released), "pinned": sorted(pinned), "notes": notes,
                   "history": [*state["history"], key], "seq": state["seq"] + 1,
                    "revision": state["revision"] + 1, "pending": None, "terminal": bool(report),
                    "continuation_feedback": None,
                    "repairs": {kind: value for kind, value in state.get("repairs", {}).items() if kind != "normal"}}
        if report:
            self.store.update_job(job, status="waiting" if report["state"] == "waiting" else "completed" if report["state"] == "complete" else "paused",
                                  stop_reason="agent_report", content_claim="complete" if report["state"] == "complete" else "partial",
                                  delivery=report.get("version_id"), last_message=report["message"])
        return changes

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

    def resume_pending(self, state: State, *, continue_failed: bool) -> dict | None:
        """Persist a chosen new-request transition before changing the graph checkpoint."""
        job = self.store.get("job", state["job"])
        key = state.get("pending") or f"{job['id']}:{state['seq']}:{state['revision']}"
        if self.store.maybe("request", key) is None:
            return None
        ref = f"continuation:{key}"
        receipt = self.store.maybe("blob", ref)
        if receipt is None:
            request = self.nexus.reconcile(job["id"], key)
            # A locally accepted reply always wins. Unknown/in-flight outcomes retain their ID and replay gate.
            if request["accepted_ref"] or job["cancel_requested"]:
                return None
            unsent_amended = (request["status"] == "prepared" and not request["attempts"]
                              and request["instruction_basis"] != instruction_basis(job))
            failed = request["status"] in {"http_error", "rejected"} and continue_failed
            if not (unsent_amended or failed):
                return None
            message = ("The unsent prepared request was superseded by new user instructions. No attempt was made."
                       if unsent_amended else
                       "The user chose Continue after a failed or rejected request. No tools from that response were executed. "
                       "The original request and response records remain available. HTTP failure does not establish remote cancellation or known cost. "
                       "Follow the latest user instructions and choose how to continue or repair the submission.")
            self.store.blob(job["id"], "request_continuation", {"request": key, "status": request["status"],
                            "reason": "new_instructions" if unsent_amended else request.get("failure", {}).get("reason", request["status"]),
                            "message": message, "diagnostic": request.get("failure", {}).get("message"), "response_ref": request.get("response_ref"),
                            "attempts": list(request["attempts"]), "revision": state["revision"] + 1}, key=ref)
        feedback = self.store.json(ref, job["id"])
        self.store.event_once(job["id"], "request_continued", key, {"request": key, "feedback_ref": ref, "reason": feedback["reason"]})
        return {"revision": feedback["revision"], "pending": None, "next": "prepare", "terminal": False,
                "continuation_feedback": ref}

    def run(self, job: str, lock: FileLock | None = None, *, continue_failed: bool = False) -> None:
        if lock is None:
            lock = FileLock(str(self.store.root / f"task-{job}.lock"))
            try:
                lock.acquire(timeout=0)
            except Timeout as exc:
                raise StopRun("already_running", "This task already has an active executor.") from exc
        config = {"configurable": {"thread_id": job}, "recursion_limit": 1_000_000}
        try:
            self.active_time.start(job)
            snapshot = self.graph.get_state(config)
            if snapshot.next:
                continuation = self.resume_pending(dict(snapshot.values), continue_failed=continue_failed)
                if continuation:
                    # Supported state update: complete this transition as the model node and route to prepare.
                    self.graph.update_state(config, continuation, as_node="model")
                self.graph.invoke(None, config, durability="sync")
            else:
                initial = dict(snapshot.values) if snapshot.values else {"job": job, "seq": 0, "revision": 0, "history": [],
                                                                       "handoff": None, "notes": "", "released": [], "pinned": []}
                initial.update(terminal=False, pending=None)
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
