from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import zipfile
import base64

from .schema import Block, CandidateRef, Document, Edit, Page, pointer
from .storage import Conflict, Store, encode, file_digest, uid
from .asset_references import (POLICY, ReferenceError, analyze, assess, asset_uri, bind_preview, classify, dependencies,
                               display_mime, parser, rewrite, safe_fragment)
from .asset_catalog import (FactError, check_pointers, default_source, enrich_object as enrich, page_patch, printed_info, provenance_record,
                            validate_occurrence, validate_source, xmp_values, SELECTED_XMP_SHA256)
from .asset_naming import COMPARISON_POLICY, EXTENSIONS, NameBudgetError, build, comparison_key


class AssetEditError(ValueError):
    """A rejected asset edit with a stable error code and structured issues (candidate retained)."""

    def __init__(self, code: str, message: str, issues: list[dict] | None = None, details: dict | None = None):
        super().__init__(message)
        self.error_code = code
        self.issues = issues or [{"code": code, "message": message, "occurrence_id": None, "destination": None,
                                  "role": None, "span": None, "details": details or {}}]


CSS = """body{max-width:860px;margin:36px auto;padding:0 28px;color:#242b34;font:17px/1.75 system-ui,sans-serif;overflow-wrap:anywhere}h1,h2,h3{line-height:1.3}img{max-width:100%;height:auto}table{border-collapse:collapse;display:block;overflow:auto}td,th{border:1px solid #ccd2da;padding:6px 12px}pre{overflow:auto;background:#f3f5f7;padding:16px}blockquote{margin-left:0;padding-left:20px;border-left:3px solid #ccd2da}sup,sub{line-height:0}a{color:#216a63}"""


def render(markdown: str, title: str = "Saved document") -> str:
    return html_page(safe_fragment(parser().render(markdown)), title)


def html_page(safe: str, title: str) -> str:
    import html
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'\">"
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body>{safe}</body></html>")


DIAGNOSTIC_PURPOSE = "saved-output diagnostic preview"
RECOVERY = ("Regenerate the source evidence with the same render_page or extract_image call; identical bytes restore the "
            "stored object and re-register the image under the same asset path. Then retry the retained candidate. "
            "Evidence with different settings receives a new asset path, which the edit must reference instead.")


def source_registrations(records: list[dict]) -> tuple[dict[str, dict], set[str]]:
    """Split task-owned asset registrations into source images and diagnostic-only paths.

    Asset paths are content hashes, so several registrations can share one path.
    The latest eligible source registration supplies it, matching the previous
    last-registration-wins index. A path backed only by diagnostic saved-output
    previews (identified by their app-authored ``purpose``) is not a source asset.
    """
    sources: dict[str, dict] = {}
    diagnostic: set[str] = set()
    for record in records:
        meta = record.get("meta", {})
        path = meta.get("asset_path")
        if path is None:
            continue
        if meta.get("purpose") == DIAGNOSTIC_PURPOSE:
            diagnostic.add(path)
        else:
            sources[path] = record
    return sources, diagnostic - set(sources)


def issue_for(ref) -> dict:
    return {"destination": ref.destination, "role": ref.role,
            "span": {"block_id": ref.span.block_id} if ref.span else None}


def describe(issue: dict) -> str:
    if not issue.get("destination"):
        return ""
    span = issue.get("span") or {}
    where = f" in block {span['block_id']}" if span.get("block_id") else ""
    return f"Offending {issue.get('role') or 'resource'} destination{where}: {issue['destination']!r}."


class Documents:
    def __init__(self, store: Store):
        self.store = store
        self.root = store.root / "versions"
        self.root.mkdir(exist_ok=True)

    def version(self, job: str, version_id: str) -> dict:
        return self._verified_version(job, version_id, load_files=False)[0]

    def _verified_version(self, job: str, version_id: str, *, load_files: bool = True) -> tuple[dict, dict[str, bytes]]:
        record = self.store.get("version", version_id, job=job)
        directory = self.root / version_id
        files = {}
        for name, digest in record["files"].items():
            path = directory / name
            try:
                if load_files or name == "document.json":
                    files[name] = path.read_bytes()
                    actual = sha256(files[name]).hexdigest()
                else:
                    actual, _ = file_digest(path)
            except OSError as exc:
                raise ValueError(f"Saved version failed integrity verification: missing/unreadable {name}") from exc
            if actual != digest:
                raise ValueError(f"Saved version failed integrity verification: {name}")
        saved = json.loads(files["document.json"])
        if saved["job"] != job or saved["version"] != version_id:
            raise ValueError("Saved version failed integrity verification: task/version identity")
        return saved, files

    def selected(self, job: str, version_id: str) -> dict:
        saved, files = self._verified_version(job, version_id)
        record = self.store.get("version", version_id, job=job)
        check, analysis = assess(saved, record["files"])
        bindings, resources, slots = {}, [], []
        referenced = {path for use in analysis.references for kind, path in [classify(use.destination, use.role)]
                      if kind == "asset"} if analysis is not None else set()
        if analysis is not None and check["status"] != "unavailable":
            for path, asset in saved["assets"].items():
                if path not in referenced:
                    continue
                if record["files"].get(path) != asset["sha256"]:
                    continue
                data = files[path]
                try:
                    mime = display_mime(path, data)
                    key = f"pdfmd-resource-{len(resources)}"
                    bindings[path] = key
                    resources.append({"key": key, "asset": path, "representation": asset.get("representation_id", asset["ref"]),
                                      "mime": mime, "length": len(data), "sha256": asset["sha256"],
                                      "base64": base64.b64encode(data).decode("ascii")})
                except ValueError as exc:
                    check["status"] = "incomplete"
                    check["issues"].append({"code": "inventory_mismatch", "message": str(exc), "destination": asset_uri(path), "role": "image", "span": None})
        markdown = files["document.md"].decode("utf-8")
        # Re-render the canonical content, never scan app-generated data URLs.
        # On failed analysis the normal sanitized view remains inspectable, with
        # local targets disabled. Immutable saved HTML/Markdown stay untouched.
        preview = html_page(analysis.html, saved["content"]["title"]) if analysis else render(markdown, saved["content"]["title"])
        preview = bind_preview(preview, bindings, available=check["status"] != "unavailable" and bool(analysis) and not analysis.issues
                               and not any(i["code"] == "inventory_mismatch" for i in check["issues"]), slots=slots)
        used = {slot["key"] for slot in slots}
        return {**saved, "markdown": markdown, "preview": preview, "asset_reference_check": check,
                "preview_transfer": {"job": job, "version": version_id, "slots": slots,
                                     "resources": [r for r in resources if r["key"] in used]}}

    def reference_check(self, job: str, version_id: str) -> dict:
        saved = self.version(job, version_id)
        record = self.store.get("version", version_id, job=job)
        return assess(saved, record["files"])[0]

    def index(self, job: str, version_id: str) -> dict:
        """Describe exact saved-version selectors without importing its bodies."""
        saved = self.version(job, version_id)
        content = saved["content"]
        entries = []
        for position, block in enumerate(content["blocks"]):
            path = f"/content/blocks/{position}"
            entries.append({"id": block["id"], "pages": block["pages"], "pointer": path,
                            "markdown_pointer": path + "/markdown",
                            "markdown_characters": len(block["markdown"]),
                            "markdown_utf8_bytes": len(block["markdown"].encode("utf-8"))})
        value = {"version_id": version_id, "source_ref": saved["source_ref"], "keys": list(saved),
                 "content_keys": list(content), "claim": content["claim"], "known_gaps": content["known_gaps"],
                 "blocks": entries, "block_count": len(entries), "pages_pointer": "/content/pages",
                 "read": {"tool": "read_document", "version_id": version_id, "view": "full",
                          "json_pointer": "/content/blocks", "start": 0, "end": len(entries)},
                 "meaning": "Index of this immutable saved version, not block bodies or a source-fidelity verification. Empty JSON Pointer reads the full version envelope; edit_document accepts edits against its content, not this envelope. A precise read does not release an earlier full read from context."}
        return {"version_id": version_id, "view": "index", "value": value,
                "original_bytes": (self.root / version_id / "document.json").stat().st_size,
                "returned_bytes": len(encode(value)), "returned_size_basis": "canonical JSON value",
                "complete": False, "completeness": {"root": False, "target": False, "selection": True},
                "access": {"view": "index", "representation": "document_index"}}

    def initial(self, job: dict) -> dict:
        return Document(title=job["name"], scope=job["scope"],
                        pages={str(i): {} for i in range(1, job["page_count"] + 1)}).model_dump()

    def edit(self, job_id: str, operation: str, arguments: dict, args_hash: str, candidate_ref: str) -> dict:
        previous = self.store.maybe("operation", operation)
        if previous and previous["args_hash"] != args_hash:
            raise Conflict("The operation ID belongs to different arguments.")
        if previous and previous["status"] == "done":
            return previous["result"]
        edit = Edit.model_validate(arguments)
        job = self.store.get("job", job_id)
        base = self.version(job_id, edit.base_version) if edit.base_version else None
        # T3b: a save that creates an occurrence, updates source facts or builds on a
        # schema 2 base is an enriched schema 2 save. Schema 1 bases keep hash paths
        # until an explicit legacy_path adoption moves them.
        enriched = bool(edit.asset_changes) or bool(edit.source_update.model_dump(exclude_unset=True)) or (
            base is not None and base.get("schema_version") == 2)
        body = deepcopy(base["content"] if base else self.initial(job))
        if edit.replace_blocks is not None:
            body["blocks"] = [block.model_dump() for block in edit.replace_blocks]
        if edit.reuse_candidate is not None:
            body["blocks"] = self.candidate_blocks(job_id, edit.reuse_candidate, allow_single=False)
        for operation_change in edit.operations:
            change = operation_change.model_dump()
            blocks = body["blocks"]
            kind = change.get("kind")
            if kind in {"insert", "replace"} and operation_change.reuse_candidate is not None:
                change["blocks"] = self.candidate_blocks(job_id, operation_change.reuse_candidate)
            if kind == "insert":
                after = change.get("after_id")
                index = 0 if after is None else self.block_index(blocks, after) + 1
                blocks[index:index] = deepcopy(change["blocks"])
            elif kind in {"replace", "delete", "patch"}:
                index = self.block_index(blocks, change["id"])
                if kind == "delete":
                    del blocks[index]
                elif kind == "replace":
                    blocks[index:index + 1] = deepcopy(change["blocks"])
                else:
                    text = blocks[index]["markdown"]
                    start, end = change["start"], change["end"]
                    if not (isinstance(start, int) and isinstance(end, int) and 0 <= start <= end <= len(text)):
                        raise ValueError("Patch offsets must be zero-based, half-open Unicode character offsets.")
                    if text[start:end] != change["expected"]:
                        raise Conflict("Patch text does not match the named base and offsets.")
                    blocks[index]["markdown"] = text[:start] + change["text"] + text[end:]
            else:
                raise ValueError("Unknown edit operation. Use insert, replace, delete, or patch.")
        for key, patch in edit.page_updates.items():
            if key not in body["pages"]:
                raise ValueError(f"Page {key} is outside this source.")
            supplied = patch.model_dump(exclude_unset=True)
            if enriched:
                try:
                    body["pages"][key] = page_patch(Page.model_validate(body["pages"][key]).model_dump(), supplied)
                except FactError as exc:
                    raise AssetEditError(exc.code, f"Page {key}: {exc} Candidate retained: {candidate_ref}") from exc
            else:
                body["pages"][key].update(supplied)
        for key in ("title", "claim", "known_gaps"):
            value = getattr(edit, key)
            if value is not None:
                body[key] = value
        content = Document.model_validate(body)
        self.validate(content, job["page_count"])
        if enriched:
            return self._save_enriched(job_id, job, operation, args_hash, candidate_ref, edit, base, content)
        markdown = self.markdown(content)
        # T3a: collect the same role-aware dependency union that the selected
        # preview interprets (embeds and local hyperlinks) under existing hash
        # paths. Input handles are recognized here but allocated only by T3b's
        # enriched creation path, so an unresolved one never publishes.
        interpretation = analyze([b.model_dump() for b in content.blocks], {k: v.model_dump() for k, v in content.pages.items()})
        handle = next((ref for ref in interpretation.references if ref.destination.lower().startswith("asset:")), None)
        if handle is not None:
            raise ValueError("Input asset handles must be resolved by the asset edit operation before publication. "
                             f"{describe(issue_for(handle))} Use a registered assets/ path. Candidate retained: {candidate_ref}")
        sources, diagnostic_only = source_registrations(self.store.records("blob", job_id))
        try:
            union = dependencies(interpretation, set(sources) | diagnostic_only)
        except ReferenceError as exc:
            raise ValueError(f"{exc} {describe(exc.issue)} Candidate retained: {candidate_ref}") from exc
        assets = {}
        for path, uses in union.items():
            if path in diagnostic_only:
                raise ValueError(f"A diagnostic saved-output preview is not a source image deliverable. {describe(issue_for(uses[0]))} "
                                 f"Replace it with a page render or extracted image from the source. Candidate retained: {candidate_ref}")
            if not re.fullmatch(r"assets/[a-f0-9]+\.[a-z0-9]+", path):
                raise ValueError(f"Image is not a registered source asset: {path}. Candidate retained: {candidate_ref}")
            blob = sources[path]
            assets[path] = {"ref": blob["ref"], "sha256": blob["sha256"], "provenance": blob["meta"]}
        originals = {}
        members: dict[str, str] = {}  # published path -> object ref, copied in chunks, never loaded

        def read_dependency(name: str, ref: str, path: str, what: str) -> None:
            # Verify every dependency before preparing a version directory, so a
            # missing/corrupt object names the reference that needs replacing.
            try:
                self.store.verify_object(ref, job_id)
                members[name] = ref
            except (OSError, ValueError) as exc:
                raise ValueError(f"The {what} for a referenced image failed its integrity check or is unreadable. "
                                 f"{describe(issue_for(union[path][0]))} {RECOVERY} Candidate retained: {candidate_ref}") from exc

        for path, asset in assets.items():
            read_dependency(path, asset["ref"], path, "registered image file")
            for original in asset["provenance"].get("originals", []):
                try:
                    blob = self.store.get("blob", original["ref"], job=job_id)
                except ValueError as exc:
                    raise ValueError(f"A retained original stream record for a referenced image is missing from this task. "
                                     f"{describe(issue_for(union[path][0]))} {RECOVERY} Candidate retained: {candidate_ref}") from exc
                expected = f"originals/{blob['meta'].get('xref')}-{blob['sha256']}."
                if blob["kind"] != "image_stream" or original["path"] not in {expected + ext for ext in ("bin", "jpeg", "jpx")}:
                    raise ValueError(f"Invalid retained image-stream reference. {describe(issue_for(union[path][0]))} Candidate retained: {candidate_ref}")
                originals[original["path"]] = {"ref": blob["ref"], "sha256": blob["sha256"], "provenance": blob["meta"]}
                read_dependency(original["path"], blob["ref"], path, "retained original stream")
        version_id = uid()
        # Catalog registration publishes the version. Prepare in its unique final
        # directory so a concurrent Windows reader need not permit a rename.
        # Failed/unregistered work stays preserved but is not a readable version.
        prepared = self.root / version_id
        prepared.mkdir()
        envelope = {"schema_version": 1, "job": job_id, "version": version_id,
                    "parent": edit.base_version, "edit_mode": edit.mode, "expected_head": edit.expected_head, "source_ref": job["source_ref"],
                    "content": content.model_dump(), "assets": assets, "originals": originals, "candidate_ref": candidate_ref}
        hashes = self._write_version(job_id, prepared, version_id, content, envelope, markdown, members,
                                     f" Candidate retained: {candidate_ref}")
        result = {"version_id": version_id, "parent": edit.base_version, "claim": content.claim,
                  "edit_mode": edit.mode, "candidate_ref": candidate_ref, "blocks": len(content.blocks), "known_gaps": content.known_gaps}
        with self.store.transaction() as db:
            prior = self.store.get_tx(db, "operation", operation)
            if prior and prior["status"] == "done":
                if prior["args_hash"] != args_hash:
                    raise Conflict("The operation ID belongs to different arguments.")
                return prior["result"]
            current = self.store.get_tx(db, "job", job_id)
            if current["head"] != edit.expected_head:
                raise Conflict(f"Head changed. Expected {edit.expected_head}; found {current['head']}. Candidate retained: {candidate_ref}")
            self.store.put_tx(db, "version", version_id, job_id,
                              {"id": version_id, "job": job_id, "parent": edit.base_version,
                               "claim": content.claim, "title": content.title, "files": hashes})
            current["head"] = version_id
            self.store.put_tx(db, "job", job_id, job_id, current)
            self.store.put_tx(db, "operation", operation, job_id,
                              {"id": operation, "args_hash": args_hash, "status": "done", "result": result,
                               "candidate_ref": candidate_ref, "tool": "edit_document"})
        self.store.event(job_id, "version_saved", result)
        return result

    # ------------------------------------------------------------------ T3b
    def _page_rects(self, job: dict) -> dict[int, list[float]]:
        import pymupdf
        from .evidence import PDF_LOCK
        # Open the verified source file by path: the engine does not load the whole PDF into memory.
        path, _ = self.store.verify_object(job["source_ref"], job["id"])
        with PDF_LOCK, pymupdf.open(str(path), filetype="pdf") as document:
            return {i + 1: list(page.rect * page.derotation_matrix) for i, page in enumerate(document)}

    def _reserve(self, job_id: str, operation: str, occurrence: str, make, client_key: str) -> tuple[str, int | None, str]:
        """Allocate the first free complete name; only a real registered conflict adds a suffix.

        One (job, comparison policy, portable key) record owns each name. An assigned
        name stays with its occurrence; a pending one belongs to its unresolved
        operation; a released one (settled failure) is free again. The chosen
        allocation is persisted in the operation's preparation record in the same
        transaction, and a resumed operation reclaims exactly that allocation, even
        if a lower-numbered name has since become free (AR-T3B-03).
        """
        held = (self.store.get("asset_preparation", operation, job=job_id)["ids"][client_key].get("reservation"))
        collision = held["collision"] if held else None
        while True:
            name = make(collision)
            key = comparison_key(name)
            rid = sha256(encode([job_id, COMPARISON_POLICY, key])).hexdigest()
            if held and (name != held["name"] or rid != held["rid"]):
                raise AssetEditError("OPERATION_CONFLICT", "The resumed operation no longer produces its reserved name.")
            with self.store.transaction() as db:
                record = self.store.get_tx(db, "asset_name", rid, job=job_id)
                free = record is None or record["status"] == "released"
                own = record is not None and record["occurrence_id"] == occurrence and (
                    record["status"] == "assigned" or record["operation"] == operation)
                if free or own:
                    self.store.put_tx(db, "asset_name", rid, job_id, {
                        "id": rid, "job": job_id, "key": key, "name": name, "occurrence_id": occurrence,
                        "operation": operation, "status": "assigned" if own and record["status"] == "assigned" else "pending"})
                    prep = self.store.get_tx(db, "asset_preparation", operation, job=job_id)
                    prep["ids"][client_key]["reservation"] = {"name": name, "collision": collision, "rid": rid}
                    self.store.put_tx(db, "asset_preparation", operation, job_id, prep)
                    return name, collision, rid
                if held:
                    raise AssetEditError("OPERATION_CONFLICT", f"The name {name} reserved by this operation now belongs to "
                                         "another occurrence; retry with a new operation.")
            collision = 2 if collision is None else collision + 1

    def _release(self, job_id: str, operation: str, reservations: list[str] | None = None) -> None:
        """Settle a failed operation: release every pending name it owns, not only this attempt's."""
        with self.store.transaction() as db:
            rows = db.execute("SELECT data FROM records WHERE kind='asset_name' AND job=?", (job_id,)).fetchall()
            for row in rows:
                record = json.loads(row[0])
                if record["status"] == "pending" and record["operation"] == operation:
                    self.store.put_tx(db, "asset_name", record["id"], job_id, {**record, "status": "released"})
            prep = self.store.get_tx(db, "asset_preparation", operation, job=job_id)
            if prep and prep["status"] != "committed":
                self.store.put_tx(db, "asset_preparation", operation, job_id, {**prep, "status": "failed"})

    def _prepare_images(self, job_id: str, pending: list[dict], kept: str) -> list[dict]:
        """Enrich every image of one save concurrently; the shared writer pool admits the workers.

        A representation already prepared by an earlier attempt of this operation is
        reused when its blob is intact (identical name-bearing record, deterministic
        bytes), so a resumed save does not rerun the writer.
        """
        from concurrent.futures import ThreadPoolExecutor
        from . import xmp_worker

        def meta(item):
            return {"occurrence_id": item["occurrence_id"], "representation_id": item["representation_id"],
                    "deliverable_path": item["path"], "pre_enrichment_ref": item["image"]["ref"],
                    "xmp_module_sha256": SELECTED_XMP_SHA256}

        def one(item):
            key = f"enriched:{item['representation_id']}"
            existing = self.store.maybe("blob", key)
            if existing and existing["job"] == job_id and existing["meta"] == meta(item):
                try:
                    self.store.verify_object(key, job_id)
                    return existing
                except (OSError, ValueError):
                    pass
            attempt, output, digest = enrich(self.store, item["image"]["ref"], job_id, xmp_values(item["record"]), item["folder"])
            try:
                blob = self.store.blob_from_file(job_id, "enriched_image", output, meta(item), key=key,
                                                 expected_sha256=digest)
            except Conflict:
                raise
            except (OSError, ValueError) as exc:
                raise FactError(f"The validated writer output could not be registered ({exc}). The attempt is retained.",
                                "ASSET_INTEGRITY_FAILED", {"stage": "output", "code": "integrity", "attempt": attempt.name}) from exc
            xmp_worker.finish(attempt)
            return blob

        results: list[dict | None] = [None] * len(pending)
        failures = []
        with ThreadPoolExecutor(max_workers=max(1, min(len(pending), 32))) as executor:
            futures = [executor.submit(one, item) for item in pending]
            for index, future in enumerate(futures):
                try:
                    results[index] = future.result()
                except FactError as exc:
                    failures.append((pending[index], exc))
        if failures:
            item, exc = failures[0]
            raise AssetEditError(exc.code, f"Create {item['key']}: {exc}{kept}", details=exc.details) from exc
        return results

    def _write_version(self, job_id: str, prepared: Path, version_id: str, content: Document, envelope: dict,
                       markdown: str, members: dict[str, str], kept: str) -> dict[str, str]:
        """Write small members from memory and copy image/original members in chunks, each hash-verified."""
        files = {"document.json": encode(envelope), "document.md": markdown.encode("utf-8"),
                 "preview.html": render(markdown, content.title).encode("utf-8")}
        hashes = {name: sha256(data).hexdigest() for name, data in files.items()}
        for name, ref in members.items():
            hashes[name] = self.store.get("blob", ref, job=job_id)["sha256"]
        files["manifest.json"] = encode({"version": version_id, "claim": content.claim, "files": hashes})
        for name, data in files.items():
            with (prepared / name).open("xb") as out:
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
        for name, ref in members.items():
            target = prepared / name
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                self.store.copy_object(ref, job_id, target)
            except (OSError, ValueError) as exc:
                raise AssetEditError("ASSET_INTEGRITY_FAILED", f"{name} changed or became unreadable while the version "
                                     f"was being written; nothing was published. Retry the retained candidate.{kept}") from exc
        hashes["manifest.json"] = sha256(files["manifest.json"]).hexdigest()
        return hashes

    def _ensure_enriched(self, job_id: str, representation: dict, path: str, where: str, kept: str) -> str:
        """Verify an enriched deliverable's object; restore it from a verified identical saved-version copy.

        Re-extracting source evidence cannot rebuild enriched bytes (AR-T3A-02), but
        every published version holds a hash-verified copy of the same immutable bytes.
        Verification and restore stream the file; the engine never loads the image.
        """
        ref, digest = representation["enriched_ref"], representation["enriched_sha256"]
        try:
            self.store.verify_object(ref, job_id)
            return ref
        except (OSError, ValueError):
            pass
        record = self.store.get("blob", ref, job=job_id)
        for version in self.store.records("version", job_id):
            for name, expected in version["files"].items():
                if expected != digest:
                    continue
                candidate = self.root / version["id"] / name
                try:
                    if file_digest(candidate) != (digest, record["bytes"]):
                        continue
                except OSError:
                    continue
                self.store.blob_from_file(job_id, record["kind"], candidate, record["meta"], key=ref,
                                          expected_sha256=digest)
                self.store.event(job_id, "enriched_object_restored", {"ref": ref, "path": path, "from_version": version["id"]})
                self.store.verify_object(ref, job_id)
                return ref
        raise AssetEditError("ASSET_INTEGRITY_FAILED", f"The enriched image {path} failed its integrity check, and no saved "
                             f"version holds a verified copy to restore it from. {where} Re-extracting the source image "
                             "cannot rebuild it. Create a new occurrence from the same source evidence (asset_changes "
                             f"create) and reference its asset:new handle instead.{kept}")

    def _save_enriched(self, job_id: str, job: dict, operation: str, args_hash: str, candidate_ref: str,
                       edit: Edit, base: dict | None, content: Document) -> dict:
        kept = f" Candidate retained: {candidate_ref}"
        schema2 = base is not None and base.get("schema_version") == 2
        if any(change.kind == "correct" for change in edit.asset_changes):
            raise AssetEditError("ASSET_FACT_INVALID", "Occurrence correction is not available yet (it belongs to the T4 "
                                 "synchronized-correction increment). Create a new occurrence instead." + kept)
        creates = [change for change in edit.asset_changes if change.kind == "create"]
        keys = [change.client_key for change in creates]
        if len(set(keys)) != len(keys):
            raise AssetEditError("ASSET_FACT_INVALID", "Each create needs a unique client_key in this edit." + kept)
        pages = {k: v.model_dump() for k, v in content.pages.items()}
        source_blob = self.store.get("blob", job["source_ref"], job=job_id)
        source = deepcopy(base["source_facts"]) if schema2 else default_source(job["source_ref"], source_blob["sha256"])
        source.update(edit.source_update.model_dump(exclude_unset=True))
        rects = self._page_rects(job)

        def lookup(ref: str):
            blob = self.store.maybe("blob", ref)
            return blob if blob is not None and blob["job"] == job_id else None
        try:
            validate_source(source)
            check_pointers(source, lookup, rects, "Source facts")
            check_pointers(pages, lookup, rects, "Page labels")
        except FactError as exc:
            raise AssetEditError(exc.code, f"{exc}{kept}") from exc
        catalog = deepcopy(base["asset_catalog"]) if schema2 else {}
        # Changing facts embedded in existing occurrences needs synchronized
        # regeneration and reference updates (T4). Refuse rather than leave stale XMP.
        for occurrence_id, entry in catalog.items():
            old = entry["representation"]["provenance_record"]
            fresh = {**old, "source": source,
                     "locations": [{**loc, "printed": printed_info(pages[str(loc["physical_page"])])} for loc in entry["facts"]["locations"]]}
            if fresh != old:
                raise AssetEditError("ASSET_FACT_INVALID", "This edit changes source facts or a page label embedded in existing "
                                     f"occurrence {occurrence_id}. Synchronized correction is not available yet (T4)." + kept)
        prep = self.store.maybe("asset_preparation", operation)
        if prep and prep["args_hash"] != args_hash:
            raise AssetEditError("OPERATION_CONFLICT", "The operation ID belongs to different arguments.")
        ids = dict(prep["ids"]) if prep else {}
        for key in keys:
            ids.setdefault(key, {"occurrence_id": uid(), "representation_id": uid()})
        self.store.put("asset_preparation", operation, job_id,
                       {"id": operation, "args_hash": args_hash, "ids": ids, "status": "preparing"})
        reservations: list[str] = []
        try:
            return self._prepare_and_publish(job_id, job, operation, args_hash, candidate_ref, edit, base, content,
                                             creates, ids, pages, source, catalog, reservations, kept, rects, lookup)
        except BaseException:
            self._release(job_id, operation)
            raise

    def _prepare_and_publish(self, job_id, job, operation, args_hash, candidate_ref, edit, base, content,
                             creates, ids, pages, source, catalog, reservations, kept, rects, lookup) -> dict:
        legacy: dict[str, str] = {}
        changes, pending = [], []
        for change in creates:
            facts = change.facts.model_dump()
            key, occurrence_id = change.client_key, ids[change.client_key]["occurrence_id"]
            representation_id = ids[key]["representation_id"]
            try:
                image = self.store.get("blob", facts["image_ref"], job=job_id)
            except ValueError:
                raise AssetEditError("ASSET_NOT_OWNED", f"Create {key}: image_ref is not an image of this task." + kept) from None
            try:
                facts = validate_occurrence(facts, image, pages, rects, lookup)
            except FactError as exc:
                raise AssetEditError(exc.code, f"Create {key}: {exc}{kept}") from exc
            if change.legacy_path is not None:
                if base is None or base.get("schema_version") != 1 or change.legacy_path not in base["assets"]:
                    raise AssetEditError("ASSET_REFERENCE_INVALID", f"Create {key}: legacy_path must be a registered asset of "
                                         "the selected schema 1 base." + kept)
                if base["assets"][change.legacy_path]["ref"] != image["ref"] or change.legacy_path in legacy:
                    raise AssetEditError("ASSET_REFERENCE_INVALID", f"Create {key}: legacy_path must match image_ref and be adopted once." + kept)
            try:
                self.store.verify_object(image["ref"], job_id)  # streamed; the engine never loads the image
            except (OSError, ValueError) as exc:
                raise AssetEditError("ASSET_INTEGRITY_FAILED", f"Create {key}: the image failed its integrity check. {RECOVERY}{kept}") from exc
            extension = image["meta"]["extension"]
            display_mime(f"x.{extension}", self.store.head(image["ref"], job_id))
            groups = facts["locator_groups"]
            printed = {p: printed_info(pages[str(p)]) for g in groups for p in g["pages"]}
            figure = facts["figure"]["value"] if facts["figure"]["state"] == "known" else None
            description = facts["description"]

            def make(collision, description=description, groups=groups, printed=printed, figure=figure, extension=extension):
                return build(description["filename"], groups, printed, figure, extension, description["punctuation"], collision)
            try:
                name, collision, rid = self._reserve(job_id, operation, occurrence_id, make, key)
            except NameBudgetError as exc:
                raise AssetEditError("ASSET_NAME_BUDGET", f"Create {key}: {exc}{kept}", details=exc.details) from exc
            except FactError as exc:
                raise AssetEditError(exc.code, f"Create {key}: {exc}{kept}") from exc
            except ValueError as exc:
                raise AssetEditError("ASSET_FACT_INVALID", f"Create {key}: {exc}{kept}") from exc
            reservations.append(rid)
            path = "assets/" + name
            originals = []
            for original in image["meta"].get("originals", []):
                blob = self.store.get("blob", original["ref"], job=job_id)
                originals.append({"ref": blob["ref"], "sha256": blob["sha256"], "path": original["path"], "metadata": blob["meta"]})
            record = provenance_record(occurrence_id=occurrence_id, representation_id=representation_id, source=source,
                                       facts=facts, pages=pages, image=image, image_sha256=image["sha256"],
                                       originals=originals, basename=name, collision=collision)
            pending.append({"key": key, "occurrence_id": occurrence_id, "representation_id": representation_id,
                            "image": image, "facts": facts, "record": record, "path": path, "extension": extension,
                            "legacy_path": change.legacy_path,
                            "folder": self.store.root / "preparation" / sha256(operation.encode()).hexdigest()[:24] / representation_id})
        # Run every image of this save through the shared writer pool at once; register in request order.
        for item, blob in zip(pending, self._prepare_images(job_id, pending, kept)):
            occurrence_id, representation_id, path = item["occurrence_id"], item["representation_id"], item["path"]
            catalog[occurrence_id] = {"facts": item["facts"], "representation": {
                "id": representation_id, "image_ref": item["image"]["ref"], "pre_enrichment_sha256": item["image"]["sha256"],
                "enriched_ref": blob["ref"], "enriched_sha256": blob["sha256"], "extension": item["extension"],
                "mime": EXTENSIONS[item["extension"]], "asset_path": path, "asset_uri": asset_uri(path),
                "provenance_record": item["record"]}}
            if item["legacy_path"] is not None:
                legacy[item["legacy_path"]] = path
            changes.append({"occurrence_id": occurrence_id, "client_key": item["key"], "previous_path": item["legacy_path"],
                            "asset_path": path, "asset_uri": asset_uri(path), "representation_id": representation_id,
                            "enriched_sha256": blob["sha256"]})
        # Resolve handles and adopted legacy paths through guarded span rewrites.
        by_path = {entry["representation"]["asset_path"]: occurrence_id for occurrence_id, entry in catalog.items()}
        handles = {f"asset:new/{c['client_key']}": c["asset_path"] for c in changes}
        handles.update({f"asset:id/{occurrence_id}": entry["representation"]["asset_path"] for occurrence_id, entry in catalog.items()})
        blocks = [b.model_dump() for b in content.blocks]
        interpretation = analyze(blocks, pages)

        def reference_error(exc: ReferenceError) -> AssetEditError:
            issue = {**exc.issue, "occurrence_id": None, "details": {}}
            hint = (" A schema 1 hash path must be adopted with a create's legacy_path." if exc.issue["code"] == "ASSET_NOT_OWNED" else "")
            return AssetEditError(exc.issue["code"] if exc.issue["code"].startswith("ASSET_") else "ASSET_REFERENCE_INVALID",
                                  f"{exc} {describe(exc.issue)}{hint}{kept}", [issue])
        try:
            dependencies(interpretation, set(by_path) | set(legacy), handles=handles)
            replacements = {}
            for ref in interpretation.references:
                kind, path = classify(ref.destination, ref.role)
                if kind == "handle":
                    replacements[ref.destination] = asset_uri(handles[ref.destination])
                elif kind == "asset" and path in legacy:
                    replacements[ref.destination] = asset_uri(legacy[path])
            if replacements:
                blocks = rewrite(blocks, pages, interpretation, replacements)
            content = Document.model_validate({**content.model_dump(), "blocks": blocks})
            interpretation = analyze(blocks, pages)
            union = dependencies(interpretation, set(by_path))
        except ReferenceError as exc:
            raise reference_error(exc) from exc
        markdown = self.markdown(content)
        assets, originals, members = {}, {}, {}  # members: published path -> verified object ref (copied, never loaded)
        for path in union:
            entry = catalog[by_path[path]]
            representation = entry["representation"]
            use = union[path][0]
            where = describe(issue_for(use))
            members[path] = self._ensure_enriched(job_id, representation, path, where, kept)
            for original in representation["provenance_record"]["image"]["originals"]:
                try:
                    blob = self.store.get("blob", original["ref"], job=job_id)
                except ValueError:
                    raise AssetEditError("ASSET_INTEGRITY_FAILED", f"The retained original stream record {original['path']} for "
                                         f"{path} is missing from this task. {where} Create the occurrence again from current "
                                         f"extract_image evidence.{kept}") from None
                try:
                    if blob["kind"] != "image_stream" or blob["sha256"] != original["sha256"]:
                        raise ValueError("Invalid retained image-stream reference.")
                    self.store.verify_object(blob["ref"], job_id)
                    members[original["path"]] = blob["ref"]
                except (OSError, ValueError) as exc:
                    raise AssetEditError("ASSET_INTEGRITY_FAILED", f"The retained original stream {original['path']} for {path} "
                                         f"failed its integrity check. {where} Repeat the extract_image call that produced it; "
                                         f"identical stream bytes restore the stored object. Then retry the retained candidate.{kept}") from exc
                originals[original["path"]] = {"ref": blob["ref"], "sha256": blob["sha256"], "provenance": blob["meta"]}
            assets[path] = {"occurrence_id": by_path[path], "representation_id": representation["id"],
                            "ref": representation["enriched_ref"], "sha256": representation["enriched_sha256"],
                            "provenance": representation["provenance_record"]}
        version_id = uid()
        prepared = self.root / version_id
        prepared.mkdir()
        envelope = {"schema_version": 2, "job": job_id, "version": version_id, "parent": edit.base_version,
                    "edit_mode": edit.mode, "expected_head": edit.expected_head, "source_ref": job["source_ref"],
                    "asset_policy": POLICY, "source_facts": source, "asset_catalog": catalog,
                    "content": content.model_dump(), "assets": assets, "originals": originals, "candidate_ref": candidate_ref}
        hashes = self._write_version(job_id, prepared, version_id, content, envelope, markdown, members, kept)
        result = {"version_id": version_id, "parent": edit.base_version, "claim": content.claim,
                  "edit_mode": edit.mode, "candidate_ref": candidate_ref, "blocks": len(content.blocks),
                  "known_gaps": content.known_gaps, "asset_changes": changes}
        with self.store.transaction() as db:
            prior = self.store.get_tx(db, "operation", operation)
            if prior and prior["status"] == "done":
                if prior["args_hash"] != args_hash:
                    raise Conflict("The operation ID belongs to different arguments.")
                return prior["result"]
            current = self.store.get_tx(db, "job", job_id)
            if current["head"] != edit.expected_head:
                raise AssetEditError("HEAD_CONFLICT", f"Head changed. Expected {edit.expected_head}; found {current['head']}.{kept}")
            for rid in reservations:
                record = self.store.get_tx(db, "asset_name", rid, job=job_id)
                if (record is None or record["occurrence_id"] not in {c["occurrence_id"] for c in changes}
                        or record["status"] == "released" or (record["status"] == "pending" and record["operation"] != operation)):
                    raise AssetEditError("OPERATION_CONFLICT", "A name reservation was lost before publication." + kept)
                self.store.put_tx(db, "asset_name", rid, job_id, {**record, "status": "assigned"})
            self.store.put_tx(db, "version", version_id, job_id,
                              {"id": version_id, "job": job_id, "parent": edit.base_version,
                               "claim": content.claim, "title": content.title, "files": hashes})
            current["head"] = version_id
            self.store.put_tx(db, "job", job_id, job_id, current)
            prep = self.store.get_tx(db, "asset_preparation", operation, job=job_id)
            self.store.put_tx(db, "asset_preparation", operation, job_id, {**prep, "status": "committed", "version": version_id})
            self.store.put_tx(db, "operation", operation, job_id,
                              {"id": operation, "args_hash": args_hash, "status": "done", "result": result,
                               "candidate_ref": candidate_ref, "tool": "edit_document"})
        self.store.event(job_id, "version_saved", result)
        return result

    def candidate_blocks(self, job: str, reference: CandidateRef, *, allow_single: bool = True) -> list[dict]:
        origin = self.store.get("blob", reference.ref, job=job)
        if origin["kind"] != "candidate":
            raise ValueError("Reuse requires a candidate reference from this task.")
        selected = pointer(self.store.json(origin["ref"], job), reference.pointer)
        if allow_single and isinstance(selected, dict):
            selected = [selected]
        if not isinstance(selected, list):
            raise ValueError("Candidate pointer must select a list of Blocks (or one Block for insert/replace).")
        return [Block.model_validate(block).model_dump() for block in selected]

    @staticmethod
    def block_index(blocks: list[dict], key: str) -> int:
        found = [i for i, block in enumerate(blocks) if block["id"] == key]
        if len(found) != 1:
            raise ValueError(f"Block ID must identify one block: {key}")
        return found[0]

    @staticmethod
    def validate(content: Document, page_count: int) -> None:
        if set(content.pages) != {str(i) for i in range(1, page_count + 1)}:
            raise ValueError("The merged page map must contain every physical page exactly once.")
        ids: set[str] = set()
        for block in content.blocks:
            if block.id in ids:
                raise ValueError("Block IDs must be unique.")
            ids.add(block.id)
            if len(set(block.pages)) != len(block.pages) or any(str(p) not in content.pages for p in block.pages):
                raise ValueError("Block pages must be distinct physical positions in this source.")
            if any(content.pages[str(p)].disposition != "included" for p in block.pages):
                raise ValueError("Each block page must have the included disposition.")
            if re.search(r"<!--\s*PDF pages?:", block.markdown, re.I):
                raise ValueError("Page markers are generated from metadata. Omit authored PDF page markers.")
        for page in content.pages.values():
            if not page.printed.strip() or re.search(r"[<>|\r\n]", page.printed):
                raise ValueError("Printed labels cannot be empty or contain angle brackets, bars, or newlines.")
        if content.claim == "complete":
            if content.known_gaps or any(p.disposition == "unprocessed" for p in content.pages.values()):
                raise ValueError("Complete claims require no known gaps or unprocessed scope.")
            used = {str(p) for block in content.blocks for p in block.pages}
            if any(k not in used for k, p in content.pages.items() if p.disposition == "included"):
                raise ValueError("Every included page must have output provenance before a complete claim.")
            if any(not p.note.strip() for p in content.pages.values() if p.disposition in {"outside_scope", "omitted_non_content"}):
                raise ValueError("Explain each outside-scope or non-content page in its note.")

    @staticmethod
    def markdown(content: Document) -> str:
        pieces = []
        for block in content.blocks:
            positions = ", ".join(str(p) for p in block.pages)
            labels = ", ".join(f"{p}={content.pages[str(p)].printed}" for p in block.pages)
            pieces.append(f"<!-- PDF pages: {positions} | printed pages: {labels} -->\n\n{block.markdown}")
        return "\n\n".join(pieces) + ("\n" if pieces else "")

    def export(self, job: str, version: str, destination: str) -> dict:
        _, expected = self._verified_version(job, version)
        record = self.store.get("version", version, job=job)
        target = Path(destination).resolve()
        if target.suffix.lower() != ".zip":
            raise ValueError("The export destination must have a .zip extension.")
        if self.store.root == target or self.store.root in target.parents:
            raise ValueError("Choose an export destination outside the private workspace.")
        intent = sha256(encode([job, version, str(target)])).hexdigest()
        existing = self.store.maybe("export", intent)

        def verify(path):
            with zipfile.ZipFile(path) as archive:
                return len(archive.namelist()) == len(expected) and set(archive.namelist()) == set(expected) and all(archive.read(name) == data for name, data in expected.items())

        if target.exists():
            if existing and verify(target):
                result = {**existing, "verified": True}
                self.store.put("export", intent, job, result)
                return result
            raise Conflict("The destination exists. Choose a different filename; existing files are preserved.")
        target.parent.mkdir(parents=True, exist_ok=True)
        result = {"id": intent, "version_id": version, "path": str(target), "claim": record["claim"], "verified": False}
        self.store.put("export", intent, job, result)
        temp = target.with_name(f".{target.name}.{intent}.tmp")
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in expected.items():
                archive.writestr(name, data)
        if not verify(temp):
            raise ValueError("Prepared ZIP failed its member and byte checks.")
        # Exclusive publication. A concurrent destination is never replaced.
        try:
            os.link(temp, target)
        except FileExistsError as exc:
            raise Conflict("The destination appeared during export. Prepared work is retained.") from exc
        temp.unlink()
        result["verified"] = verify(target)
        self.store.put("export", intent, job, result)
        self.store.event(job, "exported", result)
        return result
