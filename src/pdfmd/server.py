from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import hmac
import json
import logging
import os
import re
from pathlib import Path
import socket
import sqlite3
import threading

from fastapi import FastAPI, Header, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from filelock import FileLock, Timeout
import uvicorn

from . import __version__
from .documents import Documents
from .diagnostics import Diagnostics, Unavailable, record_summary
from .evidence import Evidence
from .network import NETWORK_PAUSES, legacy_policy
from .nexus import Nexus
from .runtime import Runtime, committed_network_retry
from .schema import ConflictResolutionSelection, Limits, Route
from .storage import Conflict, Store, uid
from .tools import Dispatcher


class Engine:
    def __init__(self, root: Path, *, transport=None):
        self.store = Store(root)
        self.documents = Documents(self.store)
        self.evidence = Evidence(self.store)
        self.keys: dict[str, str] = {}
        self.transport = transport
        self.diagnostics = Diagnostics(self.store.root)
        self.pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="pdfmd-task")
        self.futures = {}
        self.guard = threading.Lock()

    def _configure(self, job: str, route: dict | None, limits: dict | None,
                   *, starting: bool = False, amendment: str = "") -> dict:
        """Caller holds the task lock; validate and record settings atomically."""
        with self.store.transaction() as db:
            current = self.store.get_tx(db, "job", job)
            if current is None:
                raise ValueError("Task does not exist.")
            frozen = current["attempts"] > 0 or db.execute(
                "SELECT 1 FROM records WHERE job=? AND kind='request' LIMIT 1", (job,)).fetchone() is not None
            updated_route = (Route.model_validate({**(current["route"] or {}), **route}).model_dump()
                             if route is not None else current["route"])
            if current["route"] is not None and route is not None:
                # An unrelated save must not materialize defaults in a legacy
                # route, or mistake them for an unauthorized connection change.
                for name in ("wait_policy", "estimation_profile"):
                    if name not in current["route"] and name not in route:
                        updated_route.pop(name, None)
            updated_limits = (Limits.model_validate({**current["limits"], **limits}).model_dump()
                              if limits is not None else current["limits"])
            if starting and updated_route is None:
                raise ValueError("Configure a Nexus connection before starting this task.")
            if frozen:
                for name, before, after, allowed in (
                    ("route", current["route"], updated_route, {"context_tokens", "output_tokens", "image_tokens", "estimation_profile", "timeout_seconds", "wait_policy"}),
                    ("limits", current["limits"], updated_limits, {"max_requests", "max_active_seconds",
                       "automatic_retry", "max_attempts_per_request", "max_server_wait_seconds"}),
                ):
                    changed = {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
                    if changed - allowed:
                        raise Conflict(f"This task already has a frozen request. Cannot change {name}: "
                                       + ", ".join(sorted(changed - allowed))
                                       + ". Only capacity, new-request waiting and retry policies, and total request/time allowances can change.")
            if updated_route != current["route"] or updated_limits != current["limits"]:
                if (frozen and "automatic_retry" not in current["limits"]
                        and updated_limits != current["limits"]):
                    current.setdefault("legacy_replay_policy", legacy_policy(current))
                change = {"id": uid(), "before": {"route": current["route"], "limits": current["limits"]},
                          "after": {"route": updated_route, "limits": updated_limits}}
                self.store.put_tx(db, "task_settings", change["id"], job, change)
                current.update(route=updated_route, limits=updated_limits)
            if starting:
                current["cancel_requested"] = False
                if amendment.strip():
                    current["amendments"] = [*current["amendments"], amendment]
            self.store.put_tx(db, "job", job, job, current)
        return current

    def configure(self, job: str, route: dict | None = None, limits: dict | None = None):
        with self.guard:
            lock = FileLock(str(self.store.root / f"task-{job}.lock"))
            try:
                with lock.acquire(timeout=0):
                    return self._configure(job, route, limits)
            except Timeout as exc:
                raise Conflict("Stop the task before changing its settings.") from exc

    def start(self, job: str, key: str, route: dict | None = None, limits: dict | None = None,
              amendment: str = "", scripts: bool = False, recover_compaction_request: str | None = None,
              retry_request: str | None = None):
        with self.guard:
            future = self.futures.get(job)
            if future and not future.done():
                if isinstance(retry_request, str) and committed_network_retry(self.store, job, retry_request):
                    return {"started": False, "job": job}
                raise Conflict("This task is already running.")
            if retry_request is not None and recover_compaction_request is not None:
                raise Conflict("Choose one recovery action.")
            lock = FileLock(str(self.store.root / f"task-{job}.lock"), thread_local=False)
            try:
                lock.acquire(timeout=0)
            except Timeout as exc:
                raise Conflict("This task has an active executor in another process.") from exc
            runtime = None
            try:
                if not key:
                    raise ValueError("Enter the Nexus credential in Connection settings.")
                if recover_compaction_request is not None or retry_request is not None:
                    runtime = Runtime(self.store, Nexus(self.store, lambda _: self.keys[job], self.transport), scripts=scripts)
                if recover_compaction_request is not None:
                    runtime.validate_compaction_recovery(job, recover_compaction_request)
                if retry_request is not None and not runtime.validate_network_retry(job, retry_request):
                    runtime.close()
                    lock.release()
                    return {"started": False, "job": job}
                self._configure(job, route, limits, starting=True, amendment=amendment)
                self.keys[job] = key
            except BaseException:
                if runtime:
                    runtime.close()
                lock.release()
                raise

            def run():
                nonlocal runtime
                try:
                    runtime = runtime or Runtime(self.store, Nexus(self.store, lambda _: self.keys[job], self.transport), scripts=scripts)
                    # This API is the user's Start/Continue action, distinct from crash re-entry.
                    runtime.run(job, lock, continue_failed=True, recover_compaction_request=recover_compaction_request,
                                retry_request=retry_request)
                except Exception:
                    logging.exception("Task stopped with a local engine error")
                finally:
                    if runtime:
                        runtime.close()
                    lock.release()
                    self.keys.pop(job, None)

            self.futures[job] = self.pool.submit(run)
        return {"started": True, "job": job}

    def network_recovery(self, job: str) -> dict | None:
        # Only an executor holding the task lock can renew a cooldown after
        # reboot. The UI uses the resulting authoritative remaining time.
        with self.guard:
            lock = FileLock(str(self.store.root / f"task-{job}.lock"))
            try:
                with lock.acquire(timeout=0):
                    runtime = Runtime(self.store, Nexus(self.store, lambda _: "", self.transport))
                    try:
                        return runtime.network_recovery(job)
                    finally:
                        runtime.close()
            except Timeout:
                return None

    def compaction_recovery(self, job: str) -> dict | None:
        """Inspect the authoritative graph position without changing a request."""
        with self.guard:
            future = self.futures.get(job)
            if future and not future.done():
                return None
            if not any(r["kind"] == "compaction" and r["status"] == "unknown"
                       for r in self.store.records("request", job)):
                return None
            from .recovery import existing_task_lease, inspection
            try:
                with existing_task_lease(self.store.root / f"task-{job}.lock") as leased:
                    with inspection(self.store.root, job, locked=leased) as (view, _, snapshot):
                        state = snapshot.values
                        if not snapshot.next or not state:
                            return None
                        key = state.get("pending") or f"{job}:{state['seq']}:{state['revision']}"
                        request = view.maybe("request", key)
                        if (request and request["kind"] == "compaction" and request["status"] == "unknown"
                                and request.get("failure", {}).get("reason") not in NETWORK_PAUSES | {"retry_scheduled"}
                                and not request.get("accepted_ref") and not view.maybe("blob", f"accepted:{key}")
                                and not view.maybe("blob", f"continuation:{key}")):
                            return {"request": key}
            except (OSError, ValueError, sqlite3.Error):
                return None
            return None

    def diagnose_conflict(self, job: str):
        from .recovery import diagnose, unavailable
        with self.guard:
            if job in self.futures and not self.futures[job].done():
                return unavailable("busy", "Stop the task before inspecting a stable recovery view.")
            return diagnose(self.store.root, job)

    def resolve_conflict(self, job: str, body: dict):
        from .recovery import resolve
        with self.guard:
            if job in self.futures and not self.futures[job].done():
                raise Conflict("Stop the task before local recovery.")
            return resolve(self.store, job, body["request"], body["basis"], choice=body.get("choice", "preserve_and_replan"))

    def receive_observation(self, job: str, request: dict) -> dict | None:
        """Expose bounded receive facts, never native fragments or raw headers."""
        if not request["attempts"]:
            return None
        attempt = self.store.get("attempt", request["attempts"][-1], job=job)
        retained = self.store.maybe("stream_receive", attempt["id"])
        observed = (retained["transport"] if attempt["status"] == "in_flight" and retained
                    else attempt.get("transport", {}))
        from .receive_diagnostics import safe_receive
        return safe_receive({"http_status": attempt.get("http_status"), **observed})

    def close(self):
        for job, future in self.futures.items():
            if not future.done():
                self.store.update_job(job, cancel_requested=True)
        self.pool.shutdown(wait=True, cancel_futures=True)
        self.diagnostics.close()


def create_app(root: Path, token: str, *, transport=None) -> FastAPI:
    engine = Engine(root, transport=transport)

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.close()

    def authorize(authorization: str | None = Header(default=None)):
        if not authorization or not hmac.compare_digest(authorization, f"Bearer {token}"):
            raise HTTPException(401, "Unauthorized local client.")

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan,
                  dependencies=[Depends(authorize)])
    app.state.engine = engine

    @app.exception_handler(ValueError)
    async def invalid(_, error):
        return JSONResponse(status_code=409 if isinstance(error, Conflict) else 400,
                            content={"error": str(error)})

    @app.get("/health")
    def health():
        return {"version": __version__, "ready": True}

    @app.get("/jobs")
    def jobs():
        result = engine.store.records("job")
        for job in result:
            if job["status"] == "running" and not (job["id"] in engine.futures and not engine.futures[job["id"]].done()):
                job["status"] = "interrupted"
        return list(reversed(result))

    @app.post("/jobs")
    def import_source(body: dict):
        return engine.evidence.create_job(body["path"], body["scope"], body.get("route"), body.get("limits"))

    @app.get("/jobs/{job}")
    def get_job(job: str):
        value = engine.store.get("job", job)
        value["versions"] = list(reversed(engine.store.records("version", job)))
        # This display projection must not prevent opening the diagnostic UI.
        # Keep strict domain readers and all execution/recovery checks unchanged.
        value["requests"] = []
        with engine.store._db() as db:
            rows = db.execute("SELECT id,data FROM records WHERE kind='request' AND job=? ORDER BY created", (job,)).fetchall()
        for row in rows:
            try:
                r = json.loads(row["data"])
                summary = record_summary(r, "request")
                if r.get("id", row["id"]) != row["id"] or r.get("job", job) != job:
                    raise ValueError("Request identity/task is inconsistent.")
                meta = r.get("meta", {})
                if not isinstance(meta, dict) or not isinstance(r.get("route", {}), (dict, type(None))):
                    raise ValueError("Request display metadata/route has an unsupported shape.")
                capacity = meta.get("capacity")
                if capacity is not None and (not isinstance(capacity, dict) or any(
                        type(capacity.get(field)) not in (int, float) for field in ("input_estimate", "capacity", "output_reserve"))):
                    raise ValueError("Request display capacity has an unsupported shape.")
                value["requests"].append({"id": row["id"], "kind": r.get("kind") or "unknown", "status": r.get("status") or "unknown",
                                          "capacity": capacity, "attempts": summary["attempts"], "route": r.get("route"),
                                          "receive": engine.receive_observation(job, r),
                                          "retry_schedule": r.get("retry_schedule"),
                                          "replay_policy": r.get("replay_policy", legacy_policy(value))})
            except (ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
                value["requests"].append({"id": row["id"], "kind": "unknown", "status": "unavailable",
                                          "diagnostic_status": "unavailable", "reason": "Malformed record JSON." if isinstance(exc, json.JSONDecodeError) else str(exc)})
        unavailable_requests = sum(r.get("diagnostic_status") == "unavailable" for r in value["requests"])
        value["diagnostic_limitations"] = ([f"{unavailable_requests} request display summaries unavailable. Inspect diagnostic rows for identities and reasons."]
                                           if unavailable_requests else [])
        value["active_time_gaps"] = engine.store.records("active_time_gap", job)
        value["suspended_intervals"] = engine.store.records("suspended_interval", job)
        value["active_time_budget_policy"] = "known_active_only"
        value["exports"] = engine.store.records("export", job)
        value["event_summary"] = engine.store.event_summary(job)
        value["evidence"] = [{"ref": b["ref"], "kind": b["kind"], "bytes": b["bytes"], "meta": b["meta"]}
                             for b in engine.store.records("blob", job) if b["kind"] in {"evidence", "image", "candidate", "handoff"}]
        running = job in engine.futures and not engine.futures[job].done()
        if value["status"] == "running" and not running:
            value["status"] = "interrupted"
        value["running"] = running
        value["network_recovery"] = None
        if value["stop_reason"] in NETWORK_PAUSES | {"provider_configuration_error"} and not running:
            try:
                value["network_recovery"] = engine.network_recovery(job)
            except (OSError, ValueError, sqlite3.Error, KeyError, TypeError, AttributeError) as exc:
                value["diagnostic_limitations"].append("Network recovery display unavailable: " + str(exc))
        try:
            value["compaction_recovery"] = engine.compaction_recovery(job)
        except (OSError, ValueError, sqlite3.Error, KeyError, TypeError, AttributeError) as exc:
            value["compaction_recovery"] = None
            value["diagnostic_limitations"].append("Compaction recovery display unavailable; no eligibility conclusion: " + str(exc))
        return value

    def diagnostic_read(fn, **kwargs):
        try:
            return fn(**kwargs)
        except Unavailable as exc:
            return {"status": exc.status, "job": kwargs.get("job"), "reason": str(exc), "refreshable": True}
        except (OSError, sqlite3.Error, KeyError, TypeError, ValueError, AttributeError, IndexError) as exc:
            return {"status": "unavailable", "job": kwargs.get("job"), "reason": str(exc), "refreshable": True}

    @app.get("/jobs/{job}/activity")
    def activity(job: str, cursor: str | None = Query(None, max_length=1024), limit: int = Query(100, ge=1, le=200)):
        return diagnostic_read(engine.diagnostics.events, job=job, cursor=cursor, limit=limit)

    @app.get("/jobs/{job}/diagnostics")
    def diagnostics(job: str, kind: str = "request", view: str | None = Query(None, max_length=128),
                    cursor: str | None = Query(None, max_length=1024), limit: int = Query(50, ge=1, le=100)):
        return diagnostic_read(engine.diagnostics.records, job=job, kind=kind, token=view, cursor=cursor, limit=limit)

    @app.get("/jobs/{job}/diagnostics/record")
    def diagnostic_record(job: str, view: str = Query(max_length=128), kind: str = Query(max_length=64), key: str = Query(max_length=1024)):
        return diagnostic_read(engine.diagnostics.detail, job=job, token=view, kind=kind, key=key)

    @app.get("/jobs/{job}/diagnostics/evidence")
    def diagnostic_evidence(job: str, view: str = Query(max_length=128), ref: str = Query(max_length=1024),
                            mode: str = "full", pointer: str = "", start: int | None = Query(None, ge=0), end: int | None = Query(None, ge=0)):
        return diagnostic_read(engine.diagnostics.evidence, job=job, token=view, ref=ref, mode=mode, pointer=pointer, start=start, end=end)

    @app.delete("/jobs/{job}/diagnostics/{view}")
    def close_diagnostics(job: str, view: str):
        engine.diagnostics.close(job, view)
        return {"closed": True}

    @app.post("/jobs/{job}/start")
    def start(job: str, body: dict):
        return engine.start(job, body.get("key", ""), body.get("route"), body.get("limits"), body.get("amendment", ""), body.get("scripts", False),
                            recover_compaction_request=body.get("recover_compaction_request"), retry_request=body.get("retry_request"))

    @app.get("/jobs/{job}/accepted-evidence-diagnosis")
    def accepted_evidence_diagnosis(job: str):
        return engine.diagnose_conflict(job)

    @app.post("/jobs/{job}/accepted-evidence-resolution")
    def accepted_evidence_resolution(job: str, body: ConflictResolutionSelection):
        return engine.resolve_conflict(job, body.model_dump())

    @app.post("/jobs/{job}/settings")
    def task_settings(job: str, body: dict):
        return engine.configure(job, body.get("route"), body.get("limits"))

    @app.post("/jobs/{job}/cancel")
    def cancel(job: str):
        engine.store.update_job(job, cancel_requested=True)
        return {"cancel_requested": True, "remote_cancelled": None}

    @app.get("/jobs/{job}/versions/{version}")
    def version(job: str, version: str):
        return engine.documents.selected(job, version)

    @app.get("/jobs/{job}/page/{page}")
    def page(job: str, page: int):
        image = engine.evidence.render_page(job, page, dpi=110)
        return {"page": page, "url": "data:image/png;base64," + base64.b64encode(engine.store.bytes(image["ref"], job)).decode()}

    @app.get("/jobs/{job}/evidence/{ref}")
    def evidence(job: str, ref: str, view: str = "full", json_pointer: str = "", start: int | None = None, end: int | None = None):
        result = engine.evidence.read(job, ref, view, json_pointer, start, end)
        if result.get("image_ref"):
            info = engine.store.get("blob", ref, job=job)
            ext = info["meta"]["extension"]
            mime = "image/jpeg" if ext in {"jpg", "jpeg"} else f"image/{ext}"
            result["url"] = f"data:{mime};base64," + base64.b64encode(engine.store.bytes(ref, job)).decode()
        return result

    @app.post("/jobs/{job}/edit")
    def edit(job: str, body: dict, idempotency_key: str | None = Header(default=None)):
        # A caller-created Idempotency-Key makes transport retries return the
        # original receipt; without one each request is a new operation.
        if idempotency_key is not None and not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", idempotency_key):
            raise ValueError("Idempotency-Key must be 1-128 ASCII letters, digits or ._:-")
        # Scoped by task: candidate/result/operation records use store-wide keys.
        operation = f"manual:{job}:{idempotency_key}" if idempotency_key else f"manual:{uid()}"
        lock = FileLock(str(engine.store.root / f"task-{job}.lock"))
        try:
            with lock.acquire(timeout=0):
                return Dispatcher(engine.store).execute(job, operation, "edit_document", json.dumps(body, ensure_ascii=False))
        except Timeout as exc:
            raise Conflict("Pause the agent before editing a saved document.") from exc

    @app.post("/jobs/{job}/export")
    def export(job: str, body: dict):
        result = engine.documents.export(job, body["version_id"], body["destination"])
        return {**result, "asset_reference_check": engine.documents.reference_check(job, body["version_id"])}

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    arguments = parser.parse_args()
    token = os.environ.get("PDFMD_LOCAL_TOKEN")
    if not token:
        raise SystemExit("PDFMD_LOCAL_TOKEN must be supplied by the local launcher.")
    # The desktop reads only the bounded ready announcement from stdout.
    # Progress comes from durable snapshots over the authenticated loopback channel.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    port = sock.getsockname()[1]
    app = create_app(Path(arguments.workspace), token)
    print(json.dumps({"type": "ready", "port": port, "version": __version__}), flush=True)
    uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)).run(sockets=[sock])


if __name__ == "__main__":
    main()
