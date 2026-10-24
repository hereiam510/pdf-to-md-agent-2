from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from .documents import Documents
from .evidence import Evidence
from .schema import Edit, pointer
from .storage import Conflict, Store, encode


def object_schema(properties: dict, required=()) -> dict:
    return {"type": "object", "properties": properties, "required": list(required), "additionalProperties": False}


STRING = {"type": "string"}
INT = {"type": "integer"}
STRINGS = {"type": "array", "items": STRING}


def definitions(scripts: bool = False) -> list[dict]:
    entries = [
        ("inspect_pdf", "Read source pages. Full results are saved. Choose text, layout, words, or metadata without a required reading order.",
         object_schema({"pages": {"type": "array", "items": INT}, "mode": {"enum": ["text", "blocks", "words", "dict", "rawdict", "metadata"]}, "view": {"enum": ["full", "index"]}})),
        ("render_page", "Read actual page pixels. Select DPI and an optional region in rotated page points. The saved PNG is reusable.",
         object_schema({"page": INT, "dpi": INT, "region": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4}}, ["page"])),
        ("extract_image", "Extract a source image by page and xref. Preserve native bytes and apply a source soft mask when needed.",
         object_schema({"page": INT, "xref": INT}, ["page", "xref"])),
        ("read_evidence", "Read saved originals, candidates, or native image pixels. JSON Pointer selects fields. Ranges are zero-based and half-open.",
         object_schema({"ref": STRING, "view": {"enum": ["full", "index", "raw"]}, "json_pointer": STRING, "start": INT, "end": INT}, ["ref"])),
        ("read_document", "Read an explicit saved version. Omit version_id to resolve the current head for this operation. No hidden truncation applies.",
         object_schema({"version_id": STRING, "json_pointer": STRING, "start": INT, "end": INT})),
        ("preview_document", "Inspect actual saved-output pixels. Select an immutable version and viewport. The result identifies the visible region.",
         object_schema({"version_id": STRING, "top": INT, "width": INT, "height": INT}, ["version_id"])),
        ("edit_document", "Save a new version. Default mode=edit requires base_version == expected_head; mode=rebuild explicitly permits another saved or empty base without user approval. Both check the current head at commit. Preserve omitted fields and capture candidates before validation. Apply operations sequentially against the named base. Insert/replace accept either blocks or reuse_candidate (a task-owned candidate pointer to one Block or a block list); only selected content is copied. Top-level reuse_candidate replaces the entire block list. Page metadata uses printed, disposition, and note. Block pages must be included. Complete claims require every physical page classified and a note for each outside_scope or omitted_non_content page. Save partial work at any time.", Edit.model_json_schema()),
        ("context_update", "Choose saved results or arguments to release or pin. Update continuation notes without changing original records.",
         object_schema({"release": STRINGS, "pin": STRINGS, "notes": STRING})),
        ("report", "Record a completion claim or ask the user a question. Select an explicit saved version for delivery when available.",
         object_schema({"state": {"enum": ["complete", "partial", "waiting"]}, "message": STRING, "version_id": STRING}, ["state", "message"])),
        ("ocr_page", "Run local OCR on a chosen page or region. Keep the complete result and logs. OCR confidence does not certify fidelity.",
         object_schema({"page": INT, "languages": STRING, "dpi": INT, "region": {"type": "array", "items": {"type": "number"}}, "view": {"enum": ["full", "index"]}}, ["page", "languages"])),
    ]
    if scripts:
        entries.append(("run_script", "Run trusted Python for this task with host-user permissions. This is not an OS sandbox. Keep full output files and logs.",
                        object_schema({"code": STRING, "timeout_seconds": INT}, ["code"])))
    return [{"name": name, "description": description, "parameters": schema} for name, description, schema in entries]


class Dispatcher:
    def __init__(self, store: Store, *, scripts: bool = False):
        self.store, self.scripts = store, scripts
        self.documents = Documents(store)
        self.evidence = Evidence(store)

    def capture(self, job: str, operation: str, name: str, raw_arguments: str) -> tuple[str, dict]:
        digest = sha256(encode([name, raw_arguments])).hexdigest()
        candidate = self.store.blob(job, "candidate", raw_arguments.encode("utf-8"),
                                    {"operation": operation, "tool": name}, key=f"candidate:{operation}")
        return digest, candidate

    def reconcile(self, job: str, operation: str, name: str, raw_arguments: str) -> dict | None:
        """Recover a durable result without starting or repeating the tool."""
        digest = sha256(encode([name, raw_arguments])).hexdigest()
        previous = self.store.maybe("operation", operation)
        if previous:
            if previous["args_hash"] != digest:
                raise Conflict("An operation ID cannot be reused with different arguments.")
            if previous["status"] == "done":
                return self.envelope(job, operation, previous)
            staged = self.store.maybe("blob", f"result:{operation}")
            if staged:
                if staged["meta"].get("args_hash") != digest:
                    raise Conflict("The retained result does not match this operation's arguments.")
                recovered = {**previous, "status": "done", "result_ref": staged["ref"], "ok": staged["meta"]["ok"]}
                self.store.put("operation", operation, job, recovered)
                return self.envelope(job, operation, recovered)
        return None

    def skip(self, job: str, operation: str, name: str, raw_arguments: str) -> dict:
        digest, candidate = self.capture(job, operation, name, raw_arguments)
        recovered = self.reconcile(job, operation, name, raw_arguments)
        if recovered is not None:
            return recovered
        previous = self.store.maybe("operation", operation)
        if previous and previous["status"] != "skipping":
            raise UnknownEffect("A previous local tool started without a settled receipt. Its files are preserved. "
                                "New instructions prevent replay; it cannot be marked as unexecuted.")
        self.store.put("operation", operation, job,
                       {"id": operation, "args_hash": digest, "status": "skipping", "tool": name, "candidate_ref": candidate["ref"]})
        result = {"skipped": True, "execution": "not_started", "reason": "superseded_by_user_amendment",
                  "candidate_ref": candidate["ref"], "message": "This tool was not executed because the user added new instructions. "
                  "Read user_amendments before choosing your next action. The original candidate remains available."}
        return self.settle(job, operation, name, digest, candidate["ref"], result, False)

    def execute(self, job: str, operation: str, name: str, raw_arguments: str) -> dict:
        digest, candidate = self.capture(job, operation, name, raw_arguments)
        recovered = self.reconcile(job, operation, name, raw_arguments)
        if recovered is not None:
            return recovered
        previous = self.store.maybe("operation", operation)
        if previous:
            if previous["status"] == "skipping":
                return self.skip(job, operation, name, raw_arguments)
            if name in {"run_script", "ocr_page"}:
                raise UnknownEffect("The previous local process has no settled receipt. Its files are preserved; automatic replay is disabled.")
        self.store.put("operation", operation, job,
                       {"id": operation, "args_hash": digest, "status": "started", "tool": name, "candidate_ref": candidate["ref"]})
        try:
            arguments = json.loads(raw_arguments)
            if not isinstance(arguments, dict):
                raise ValueError("Tool arguments must be one complete JSON object.")
            result = self.dispatch(job, operation, name, arguments, digest, candidate["ref"])
            saved = self.store.maybe("operation", operation)
            if name == "edit_document" and saved and saved["status"] == "done":
                return self.envelope(job, operation, saved)
            success = True
        except UnknownEffect:
            raise
        except (ValueError, KeyError, IndexError, TypeError, OSError, RuntimeError) as exc:
            result = {"error": str(exc), "candidate_ref": candidate["ref"], "tool": name}
            success = False
        return self.settle(job, operation, name, digest, candidate["ref"], result, success)

    def settle(self, job: str, operation: str, name: str, digest: str, candidate_ref: str, result: dict, success: bool) -> dict:
        result_blob = self.store.blob(job, "tool_result", result, {"operation": operation, "args_hash": digest, "ok": success}, key=f"result:{operation}")
        record = {"id": operation, "args_hash": digest, "status": "done", "tool": name,
                  "candidate_ref": candidate_ref, "result_ref": result_blob["ref"], "ok": success}
        self.store.put("operation", operation, job, record)
        self.store.event(job, "tool_settled", {"operation": operation, "tool": name, "ok": success, "result_ref": result_blob["ref"]})
        return self.envelope(job, operation, record)

    def envelope(self, job: str, operation: str, record: dict) -> dict:
        if "result_ref" in record:
            result = self.store.json(record["result_ref"], job)
            reference = record["result_ref"]
        else:
            # A document commit can precede result projection and graph checkpointing.
            result = record["result"]
            reference = self.store.blob(job, "tool_result", result, {"operation": operation}, key=f"result:{operation}")["ref"]
        return {"ok": record.get("ok", True), "result_ref": reference,
                "candidate_ref": record["candidate_ref"], "data": result}

    def dispatch(self, job, operation, name, args, digest, candidate):
        if name == "inspect_pdf":
            return self.evidence.inspect(job, **args)
        if name == "render_page":
            return self.evidence.render_page(job, **args)
        if name == "extract_image":
            return self.evidence.extract_image(job, **args)
        if name == "read_evidence":
            return self.evidence.read(job, **args)
        if name == "read_document":
            version = args.pop("version_id", None) or self.store.get("job", job)["head"]
            if not version:
                return {"head": None, "message": "No document version is saved yet."}
            saved = self.documents.version(job, version)
            ref = self.store.blob(job, "document_view", saved, {"version": version})
            return {"version_id": version, **self.evidence.read(job, ref["ref"], **args)}
        if name == "edit_document":
            return self.documents.edit(job, operation, args, digest, candidate)
        if name == "preview_document":
            return self.preview(job, operation, **args)
        if name == "context_update":
            if set(args) - {"release", "pin", "notes"}:
                raise ValueError("Unknown context field.")
            for key in ("release", "pin"):
                for ref in args.get(key, []):
                    self.store.get("blob", ref, job=job)
            return {"context_intent": args}
        if name == "report":
            if args.get("state") not in {"complete", "partial", "waiting"} or not isinstance(args.get("message"), str):
                raise ValueError("Report needs a state and a message.")
            if args.get("version_id"):
                version = self.documents.version(job, args["version_id"])
                if args["state"] == "complete" and version["content"]["claim"] != "complete":
                    raise ValueError("The selected version is still partial.")
            elif args["state"] == "complete":
                raise ValueError("A complete report requires a saved version.")
            return {"report_intent": args}
        if name == "ocr_page":
            return self.ocr(job, operation, **args)
        if name == "run_script" and self.scripts:
            return self.script(job, operation, **args)
        raise ValueError(f"Tool is not enabled: {name}")

    def process(self, job: str, operation: str, command: list[str], directory: Path, timeout: int, env=None):
        stdout, stderr = directory / "stdout.txt", directory / "stderr.txt"
        started = time.monotonic()
        with stdout.open("wb") as out, stderr.open("wb") as err:
            process = subprocess.Popen(command, cwd=directory, stdout=out, stderr=err, env=env,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            while process.poll() is None:
                current = self.store.get("job", job)
                active = current["active_seconds"] + max(0, time.time() - current.get("active_since", time.time()))
                if current["cancel_requested"] or time.monotonic() - started > timeout or active >= current["limits"]["max_active_seconds"]:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    raise UnknownEffect(f"Local process stopped. Files and logs remain at {directory}. Child effects may require inspection.")
                time.sleep(0.1)
        return process.returncode, stdout, stderr

    def ocr(self, job: str, operation: str, page: int, languages: str, dpi: int = 240,
            region: list | None = None, view: str = "full") -> dict:
        if not re.fullmatch(r"[a-z_]+(?:\+[a-z_]+)*", languages):
            raise ValueError("Use Tesseract language codes joined by '+', such as eng+chi_tra.")
        worker = os.environ.get("PDFMD_OCR_WORKER")
        node = os.environ.get("PDFMD_NODE")
        if not worker or not node:
            raise ValueError("Local OCR requires the desktop OCR worker. Start through the desktop launcher.")
        image = self.evidence.render_page(job, page, dpi, region)
        directory = self.store.root / "processes" / sha256(operation.encode()).hexdigest()
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "input.png").write_bytes(self.store.bytes(image["ref"], job))
        env = {**os.environ, "ELECTRON_RUN_AS_NODE": "1"}
        code, out, err = self.process(job, operation, [node, worker, str(directory / "input.png"), languages,
                                                     str(directory / "result.json"), str(self.store.root / "ocr-cache")], directory, 600, env)
        logs = [self.store.blob(job, "process_log", path.read_bytes(), {"operation": operation, "stream": path.stem})["ref"] for path in (out, err)]
        if code != 0 or not (directory / "result.json").exists():
            return {"error": "OCR did not produce a complete result.", "exit_code": code, "logs": logs, "image_ref": image["ref"]}
        result = json.loads((directory / "result.json").read_bytes())
        ref = self.store.blob(job, "evidence", {"ocr": result, "image": image, "logs": logs,
                                               "warnings": ["OCR is derived evidence. Compare uncertain text with source pixels."],
                                               "coverage": {"page": page, "region": image["region"], "languages": languages}},
                              {"operation": operation, "page": page, "mode": "ocr"})
        return self.evidence.read(job, ref["ref"], view=view)

    def script(self, job: str, operation: str, code: str, timeout_seconds: int = 120) -> dict:
        if not 1 <= timeout_seconds <= 3600:
            raise ValueError("Script timeout must be between 1 and 3600 seconds.")
        executable = os.environ.get("PDFMD_SCRIPT_PYTHON") or sys.executable
        directory = self.store.root / "processes" / sha256(operation.encode()).hexdigest()
        directory.mkdir(parents=True, exist_ok=True)
        script = directory / "task.py"
        script.write_text(code, encoding="utf-8", newline="")
        source = directory / "source.pdf"
        source.write_bytes(self.evidence.source(job))
        env = {k: v for k, v in os.environ.items() if not any(word in k.upper() for word in ("TOKEN", "SECRET", "API_KEY", "PASSWORD"))}
        env.update({"PDFMD_SOURCE": str(source), "PDFMD_OUTPUT": str(directory), "PYTHONIOENCODING": "utf-8"})
        command = [executable, "--task-script", str(script)] if getattr(sys, "frozen", False) and not os.environ.get("PDFMD_SCRIPT_PYTHON") else [executable, str(script)]
        exit_code, stdout, stderr = self.process(job, operation, command, directory, timeout_seconds, env)
        logs = {path.stem: self.store.blob(job, "process_log", path.read_bytes(), {"operation": operation})["ref"] for path in (stdout, stderr)}
        outputs = []
        for path in directory.rglob("*"):
            if path.is_file() and path not in {script, source, stdout, stderr}:
                record = self.store.blob(job, "script_output", path.read_bytes(), {"operation": operation, "filename": str(path.relative_to(directory))})
                outputs.append({"ref": record["ref"], "file": str(path.relative_to(directory)), "bytes": record["bytes"]})
        return {"exit_code": exit_code, "logs": logs, "files": outputs, "directory": str(directory),
                "stdout_preview": stdout.read_bytes()[:4000].decode("utf-8", errors="replace"),
                "preview_complete": stdout.stat().st_size <= 4000}

    def preview(self, job: str, operation: str, version_id: str, top: int = 0, width: int = 1024, height: int = 900) -> dict:
        self.documents.version(job, version_id)
        if not (0 <= top and 320 <= width <= 3000 and 200 <= height <= 3000):
            raise ValueError("Use a nonnegative scroll offset, width 320–3000, and height 200–3000.")
        command = json.loads(os.environ.get("PDFMD_PREVIEW_LAUNCH", "null"))
        if not command:
            raise ValueError("Saved-output pixels require the desktop preview worker.")
        directory = self.store.root / "processes" / sha256(operation.encode()).hexdigest()
        directory.mkdir(parents=True, exist_ok=True)
        image = directory / "preview.png"
        if not image.exists():
            env = dict(os.environ)
            env.pop("ELECTRON_RUN_AS_NODE", None)
            exit_code, _, _ = self.process(job, operation, [*command, "--preview-worker", str(self.documents.root / version_id),
                                                           str(image), str(top), str(width), str(height)], directory, 90, env)
            if exit_code != 0 or not image.exists():
                raise ValueError("The saved-output preview worker failed. Its logs remain in the process directory.")
        viewport = json.loads(image.with_name(image.name + ".json").read_bytes())
        return self.evidence.image(job, image.read_bytes(), "png", {"version": version_id, "purpose": "saved-output diagnostic preview",
                                                                  **viewport,
                                                                  "coordinate_frame": "CSS viewport/document pixels; width and height are actual PNG pixels",
                                                                  "coverage": "selected viewport; not the entire document"})


class UnknownEffect(RuntimeError):
    pass
