from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import hmac
import json
import logging
import os
from pathlib import Path
import socket
import threading

from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.responses import JSONResponse
from filelock import FileLock, Timeout
import uvicorn

from . import __version__
from .documents import Documents
from .evidence import Evidence
from .nexus import Nexus
from .runtime import Runtime
from .schema import Limits, Route
from .storage import Conflict, Store, uid
from .tools import Dispatcher


class Engine:
    def __init__(self, root: Path, *, transport=None):
        self.store = Store(root)
        self.documents = Documents(self.store)
        self.evidence = Evidence(self.store)
        self.keys: dict[str, str] = {}
        self.transport = transport
        self.pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="pdfmd-task")
        self.futures = {}
        self.guard = threading.Lock()

    def start(self, job: str, key: str, route: dict | None = None, limits: dict | None = None,
              amendment: str = "", scripts: bool = False):
        with self.guard:
            future = self.futures.get(job)
            if future and not future.done():
                raise Conflict("This task is already running.")
            lock = FileLock(str(self.store.root / f"task-{job}.lock"), thread_local=False)
            try:
                lock.acquire(timeout=0)
            except Timeout as exc:
                raise Conflict("This task has an active executor in another process.") from exc
            try:
                current = self.store.get("job", job)
                changes = {"cancel_requested": False}
                if current["route"] is None:
                    changes["route"] = Route.model_validate(route).model_dump()
                if limits and current["attempts"] == 0 and not self.store.records("request", job):
                    changes["limits"] = Limits.model_validate(limits).model_dump()
                if amendment.strip():
                    changes["amendments"] = [*current["amendments"], amendment]
                if not key:
                    raise ValueError("Enter the Nexus credential in Connection settings.")
                self.keys[job] = key
                self.store.update_job(job, **changes)
            except BaseException:
                lock.release()
                raise

            def run():
                runtime = None
                try:
                    runtime = Runtime(self.store, Nexus(self.store, lambda _: self.keys[job], self.transport), scripts=scripts)
                    # This API is the user's Start/Continue action, distinct from crash re-entry.
                    runtime.run(job, lock, continue_failed=True)
                except Exception:
                    logging.exception("Task stopped with a local engine error")
                finally:
                    if runtime:
                        runtime.close()
                    lock.release()
                    self.keys.pop(job, None)

            self.futures[job] = self.pool.submit(run)
        return {"started": True, "job": job}

    def close(self):
        for job, future in self.futures.items():
            if not future.done():
                self.store.update_job(job, cancel_requested=True)
        self.pool.shutdown(wait=True, cancel_futures=True)


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
        value["requests"] = [{"id": r["id"], "kind": r["kind"], "status": r["status"], "capacity": r["meta"].get("capacity"),
                              "attempts": len(r["attempts"])} for r in engine.store.records("request", job)]
        value["exports"] = engine.store.records("export", job)
        value["events"] = engine.store.events(job, limit=1000)
        value["evidence"] = [{"ref": b["ref"], "kind": b["kind"], "bytes": b["bytes"], "meta": b["meta"]}
                             for b in engine.store.records("blob", job) if b["kind"] in {"evidence", "image", "candidate", "handoff"}]
        running = job in engine.futures and not engine.futures[job].done()
        if value["status"] == "running" and not running:
            value["status"] = "interrupted"
        value["running"] = running
        return value

    @app.post("/jobs/{job}/start")
    def start(job: str, body: dict):
        return engine.start(job, body.get("key", ""), body.get("route"), body.get("limits"), body.get("amendment", ""), body.get("scripts", False))

    @app.post("/jobs/{job}/cancel")
    def cancel(job: str):
        engine.store.update_job(job, cancel_requested=True)
        return {"cancel_requested": True, "remote_cancelled": None}

    @app.get("/jobs/{job}/versions/{version}")
    def version(job: str, version: str):
        saved = engine.documents.version(job, version)
        directory = engine.documents.root / version
        preview = (directory / "preview.html").read_text(encoding="utf-8")
        for path, asset in saved["assets"].items():
            extension = path.rsplit(".", 1)[-1]
            mime = "image/jpeg" if extension in {"jpg", "jpeg"} else f"image/{extension}"
            url = f"data:{mime};base64," + base64.b64encode(engine.store.bytes(asset["ref"], job)).decode()
            preview = preview.replace(f'src="{path}"', f'src="{url}"')
        return {**saved, "markdown": (directory / "document.md").read_bytes().decode("utf-8"),
                "preview": preview}

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
    def edit(job: str, body: dict):
        lock = FileLock(str(engine.store.root / f"task-{job}.lock"))
        try:
            with lock.acquire(timeout=0):
                return Dispatcher(engine.store).execute(job, f"manual:{uid()}", "edit_document", json.dumps(body, ensure_ascii=False))
        except Timeout as exc:
            raise Conflict("Pause the agent before editing a saved document.") from exc

    @app.post("/jobs/{job}/export")
    def export(job: str, body: dict):
        return engine.documents.export(job, body["version_id"], body["destination"])

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
