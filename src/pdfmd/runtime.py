from __future__ import annotations

import json
import sqlite3
import time
from typing import TypedDict

from filelock import FileLock, Timeout
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from .context import Context
from .nexus import Nexus, StopRun
from .storage import Store
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


class Runtime:
    def __init__(self, store: Store, nexus: Nexus, *, scripts: bool = False):
        self.store, self.nexus = store, nexus
        self.dispatcher = Dispatcher(store, scripts=scripts)
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
        builder.add_conditional_edges("model", lambda state: END if state["terminal"] else "tools", {END: END, "tools": "tools"})
        builder.add_conditional_edges("tools", lambda state: END if state["terminal"] else "prepare", {END: END, "prepare": "prepare"})
        builder.add_edge("compact", "prepare")
        self.graph = builder.compile(checkpointer=SqliteSaver(self.connection))

    def prepare(self, state: State):
        job = self.store.get("job", state["job"])
        if job["cancel_requested"]:
            raise StopRun("cancelled", "Stopped at a settled tool-batch boundary.")
        key = f"{job['id']}:{state['seq']}:{state['revision']}"
        # A frozen request wins over current pointers and newly reconstructed input.
        request = self.store.maybe("request", key)
        if request is None:
            payload, capacity = self.context.normal(job, state)
            if capacity["fits"]:
                request = self.nexus.freeze(job["id"], key, payload, "normal", {"capacity": capacity})
            else:
                payload, meta = self.context.compact_request(job, state)
                request = self.nexus.freeze(job["id"], key, payload, "compaction", meta)
        return {"pending": key, "next": "compact" if request["kind"] == "compaction" else "model", "terminal": False}

    def model(self, state: State):
        reply = self.nexus.send(state["job"], state["pending"])
        if reply["text"]:
            self.store.update_job(state["job"], last_message=reply["text"])
        if reply["calls"]:
            return {"terminal": False}
        self.store.update_job(state["job"], status="paused", stop_reason="assistant_finished",
                              last_message=reply["text"])
        return {"terminal": True, "history": [*state["history"], state["pending"]],
                "seq": state["seq"] + 1, "revision": state["revision"] + 1, "pending": None}

    def tools(self, state: State):
        job, key = state["job"], state["pending"]
        request = self.store.get("request", key, job=job)
        reply = self.store.json(request["accepted_ref"], job)
        released, pinned = set(state["released"]), set(state["pinned"])
        notes, report = state["notes"], None
        for index, call in enumerate(reply["calls"]):
            operation = f"{key}:{index}"
            previous = self.store.maybe("operation", operation)
            if self.store.get("job", job)["cancel_requested"] and not (previous and previous["status"] == "done"):
                raise StopRun("cancelled", "Stopped before the next tool. The accepted pending batch is preserved.")
            current = self.store.get("job", job)
            elapsed = current["active_seconds"] + max(0, time.time() - current.get("active_since", time.time()))
            if elapsed >= current["limits"]["max_active_seconds"] and not (previous and previous["status"] == "done"):
                raise StopRun("budget_exhausted", "Stopped before a new tool because the persistent active-time budget is exhausted.")
            result = self.dispatcher.execute(job, operation, call["name"], call["arguments"])
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
        # One deterministic policy settlement per complete accepted batch.
        changes = {"released": sorted(released), "pinned": sorted(pinned), "notes": notes,
                   "history": [*state["history"], key], "seq": state["seq"] + 1,
                   "revision": state["revision"] + 1, "pending": None, "terminal": bool(report)}
        if report:
            self.store.update_job(job, status="waiting" if report["state"] == "waiting" else "completed" if report["state"] == "complete" else "paused",
                                  stop_reason="agent_report", content_claim="complete" if report["state"] == "complete" else "partial",
                                  delivery=report.get("version_id"), last_message=report["message"])
        return changes

    def compact(self, state: State):
        request = self.store.get("request", state["pending"], job=state["job"])
        reply = self.nexus.send(state["job"], state["pending"])
        if reply["calls"]:
            raise StopRun("handoff_rejected", "The compaction reply unexpectedly requested tools. Previous context is preserved.")
        try:
            result = self.context.apply_handoff(self.store.get("job", state["job"]), state, reply["text"], request["meta"], state["pending"])
        except (ValueError, TypeError, KeyError) as exc:
            raise StopRun("handoff_rejected", str(exc)) from exc
        return {**result, "pending": None}

    def run(self, job: str, lock: FileLock | None = None) -> None:
        if lock is None:
            lock = FileLock(str(self.store.root / f"task-{job}.lock"))
            try:
                lock.acquire(timeout=0)
            except Timeout as exc:
                raise StopRun("already_running", "This task already has an active executor.") from exc
        config = {"configurable": {"thread_id": job}, "recursion_limit": 1_000_000}
        try:
            current = self.store.get("job", job)
            prior_started = current.get("active_since")
            carried = current["active_seconds"] + (max(0, time.time() - prior_started) if prior_started else 0)
            self.store.update_job(job, status="running", stop_reason=None, active_since=time.time(), active_seconds=carried)
            snapshot = self.graph.get_state(config)
            if snapshot.next:
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
            with self.store.transaction() as db:
                current = self.store.get_tx(db, "job", job)
                started = current.pop("active_since", None)
                if started:
                    current["active_seconds"] += max(0, time.time() - started)
                self.store.put_tx(db, "job", job, job, current)
            lock.release()

    def close(self):
        self.connection.close()
