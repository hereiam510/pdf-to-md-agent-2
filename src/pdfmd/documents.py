from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import zipfile

from markdown_it import MarkdownIt
from mdit_py_plugins.footnote import footnote_plugin
import nh3

from .schema import Block, CandidateRef, Document, Edit, pointer
from .storage import Conflict, Store, encode, uid


CSS = """body{max-width:860px;margin:36px auto;padding:0 28px;color:#242b34;font:17px/1.75 system-ui,sans-serif;overflow-wrap:anywhere}h1,h2,h3{line-height:1.3}img{max-width:100%;height:auto}table{border-collapse:collapse;display:block;overflow:auto}td,th{border:1px solid #ccd2da;padding:6px 12px}pre{overflow:auto;background:#f3f5f7;padding:16px}blockquote{margin-left:0;padding-left:20px;border-left:3px solid #ccd2da}sup,sub{line-height:0}a{color:#216a63}"""


def parser() -> MarkdownIt:
    return MarkdownIt("commonmark", {"html": True}).enable("table").use(footnote_plugin)


def render(markdown: str, title: str = "Saved document") -> str:
    import html
    safe = nh3.clean(parser().render(markdown),
                     tags=set(nh3.ALLOWED_TAGS) | {"sup", "sub", "table", "thead", "tbody", "tr", "td", "th", "img"},
                     attributes={**nh3.ALLOWED_ATTRIBUTES, "img": {"src", "alt", "title", "width", "height"},
                                 "td": {"colspan", "rowspan"}, "th": {"colspan", "rowspan", "scope"},
                                 "*": {"id", "class", "lang"}},
                     url_schemes={"http", "https", "mailto"})
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'\">"
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body>{safe}</body></html>")


class ImageLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources: set[str] = set()

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.sources.add(dict(attrs).get("src", ""))


def image_links(markdown: str) -> set[str]:
    scan = ImageLinks()
    scan.feed(parser().render(markdown))
    return scan.sources


class Documents:
    def __init__(self, store: Store):
        self.store = store
        self.root = store.root / "versions"
        self.root.mkdir(exist_ok=True)

    def version(self, job: str, version_id: str) -> dict:
        record = self.store.get("version", version_id, job=job)
        directory = self.root / version_id
        for name, digest in record["files"].items():
            if sha256((directory / name).read_bytes()).hexdigest() != digest:
                raise ValueError(f"Saved version failed integrity verification: {name}")
        return json.loads((directory / "document.json").read_bytes())

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
        body = deepcopy(self.version(job_id, edit.base_version)["content"] if edit.base_version else self.initial(job))
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
            body["pages"][key].update(patch.model_dump(exclude_unset=True))
        for key in ("title", "claim", "known_gaps"):
            value = getattr(edit, key)
            if value is not None:
                body[key] = value
        content = Document.model_validate(body)
        self.validate(content, job["page_count"])
        markdown = self.markdown(content)
        asset_index = {b["meta"]["asset_path"]: b for b in self.store.records("blob", job_id)
                       if "asset_path" in b.get("meta", {})}
        assets = {}
        for path in image_links(markdown):
            if path not in asset_index or not re.fullmatch(r"assets/[a-f0-9]+\.[a-z0-9]+", path):
                raise ValueError(f"Image is not a registered source asset: {path}")
            blob = asset_index[path]
            assets[path] = {"ref": blob["ref"], "sha256": blob["sha256"], "provenance": blob["meta"]}
        originals = {}
        for asset in assets.values():
            for original in asset["provenance"].get("originals", []):
                blob = self.store.get("blob", original["ref"], job=job_id)
                expected = f"originals/{blob['meta'].get('xref')}-{blob['sha256']}."
                if blob["kind"] != "image_stream" or original["path"] not in {expected + ext for ext in ("bin", "jpeg", "jpx")}:
                    raise ValueError("Invalid retained image-stream reference.")
                originals[original["path"]] = {"ref": blob["ref"], "sha256": blob["sha256"], "provenance": blob["meta"]}
        version_id = uid()
        prepared = self.root / f".prepared-{version_id}"
        prepared.mkdir()
        envelope = {"schema_version": 1, "job": job_id, "version": version_id,
                    "parent": edit.base_version, "edit_mode": edit.mode, "expected_head": edit.expected_head, "source_ref": job["source_ref"],
                    "content": content.model_dump(), "assets": assets, "originals": originals, "candidate_ref": candidate_ref}
        files = {"document.json": encode(envelope), "document.md": markdown.encode("utf-8"),
                 "preview.html": render(markdown, content.title).encode("utf-8")}
        files.update({path: self.store.bytes(info["ref"], job_id) for path, info in assets.items()})
        files.update({path: self.store.bytes(info["ref"], job_id) for path, info in originals.items()})
        hashes = {name: sha256(data).hexdigest() for name, data in files.items()}
        files["manifest.json"] = encode({"version": version_id, "claim": content.claim, "files": hashes})
        for name, data in files.items():
            target = prepared / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as out:
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
        os.rename(prepared, self.root / version_id)
        hashes["manifest.json"] = sha256(files["manifest.json"]).hexdigest()
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
        self.version(job, version)
        record = self.store.get("version", version, job=job)
        target = Path(destination).resolve()
        if target.suffix.lower() != ".zip":
            raise ValueError("The export destination must have a .zip extension.")
        if self.store.root == target or self.store.root in target.parents:
            raise ValueError("Choose an export destination outside the private workspace.")
        expected = {name: (self.root / version / name).read_bytes() for name in record["files"]}
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
