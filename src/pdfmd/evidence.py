from __future__ import annotations

import base64
from hashlib import sha256
import json
from pathlib import Path
import threading
import time
from typing import Any

import pymupdf

from .schema import Limits, Route, pointer
from .storage import Store, uid


# MuPDF is not thread-safe. Never share a live Document across callers.
PDF_LOCK = threading.RLock()


def jsonable(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"encoding": "base64", "bytes": len(value), "data": base64.b64encode(value).decode()}
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(v) for v in value]
    return value


class Evidence:
    def __init__(self, store: Store):
        self.store = store

    def create_job(self, path: str, scope: str, route: dict | None = None, limits: dict | None = None) -> dict:
        route = Route.model_validate(route).model_dump() if route else None
        limits = Limits.model_validate(limits or {}).model_dump()
        if not scope.strip():
            raise ValueError("Describe the requested document or complete section.")
        raw = Path(path).read_bytes()
        with PDF_LOCK, pymupdf.open(stream=raw, filetype="pdf") as document:
            if document.needs_pass:
                raise ValueError("This PDF requires a password. Import an unlocked source copy.")
            if document.page_count == 0:
                raise ValueError("The PDF contains no pages.")
            count = document.page_count
        job_id = uid()
        source = self.store.blob(job_id, "source_pdf", raw, {"filename": Path(path).name, "pages": count})
        job = {"id": job_id, "name": Path(path).stem, "source_ref": source["ref"], "page_count": count,
               "scope": scope, "amendments": [], "route": route, "limits": limits,
               "head": None, "delivery": None, "status": "ready", "stop_reason": None,
               "attempts": 0, "active_seconds": 0.0, "cancel_requested": False,
               "created": time.time(), "updated": time.time(), "last_message": "", "content_claim": "partial"}
        self.store.put("job", job_id, job_id, job)
        self.store.event(job_id, "source_imported", {"name": job["name"], "pages": count, "source_ref": source["ref"]})
        return job

    def source(self, job: str) -> bytes:
        return self.store.bytes(self.store.get("job", job)["source_ref"], job)

    def inspect(self, job: str, pages: list[int] | None = None, mode: str = "text", view: str = "full") -> dict:
        if mode not in {"text", "blocks", "words", "dict", "rawdict", "metadata"}:
            raise ValueError("Use text, blocks, words, dict, rawdict, or metadata.")
        output = []
        with PDF_LOCK, pymupdf.open(stream=self.source(job), filetype="pdf") as document:
            pages = pages if pages is not None else list(range(1, len(document) + 1))
            if not pages or len(set(pages)) != len(pages) or any(p < 1 or p > len(document) for p in pages):
                raise ValueError("Pages must be distinct one-based physical positions in this source.")
            for number in pages:
                page = document[number - 1]
                item = {"page": number, "rect": list(page.rect), "rotation": page.rotation,
                        "coordinate_frame": "PyMuPDF unrotated page points, top-left origin",
                        "images": jsonable(page.get_images(full=True))}
                if mode != "metadata":
                    item["content"] = jsonable(page.get_text(mode, sort=False))
                output.append(item)
        data = {"pages": output, "mode": mode,
                "warnings": ["Text extraction and image metadata do not certify reading order or source fidelity.",
                             "Printed page labels require source observation; PDF position is one-based."],
                "coverage": {"physical_pages": pages, "scope": "extraction only"}}
        record = self.store.blob(job, "evidence", data, {"pages": pages, "mode": mode})
        return self.read(job, record["ref"], view=view)

    def read(self, job: str, ref: str, view: str = "full", json_pointer: str = "",
             start: int | None = None, end: int | None = None) -> dict:
        record = self.store.get("blob", ref, job=job)
        if record["kind"] == "image":
            return {"ref": ref, "image_ref": ref, "meta": record["meta"], "bytes": record["bytes"],
                    "coverage": "complete saved image at native dimensions"}
        if view == "raw":
            raw = self.store.bytes(ref, job)
            first, last = self.bounds(len(raw), start, end)
            return {"ref": ref, "encoding": "base64", "unit": "byte", "range": [first, last],
                    "total": len(raw), "data": base64.b64encode(raw[first:last]).decode(), "complete": first == 0 and last == len(raw)}
        try:
            data = self.store.json(ref, job)
        except (ValueError, UnicodeDecodeError):
            data = self.store.bytes(ref, job).decode("utf-8", errors="strict")
        if view == "index":
            return {"ref": ref, "bytes": record["bytes"], "kind": record["kind"], "meta": record["meta"],
                    "keys": list(data) if isinstance(data, dict) else None,
                    "warnings": data.get("warnings", []) if isinstance(data, dict) else [],
                    "coverage": data.get("coverage") if isinstance(data, dict) else None,
                    "complete": False, "read": "read_evidence(ref, view='full', json_pointer='', start=null, end=null)"}
        if view != "full":
            raise ValueError("Use full, index, or raw. Full reads have no hidden truncation.")
        selected = pointer(data, json_pointer)
        span = None
        total = len(selected) if isinstance(selected, (str, list)) else None
        if start is not None or end is not None:
            if not isinstance(selected, (str, list)):
                raise ValueError("Ranges apply to a string or array selected by JSON Pointer.")
            first, last = self.bounds(len(selected), start, end)
            span = [first, last]
            selected = selected[first:last]
        return {"ref": ref, "pointer": json_pointer, "range": span, "total": total,
                "complete": not json_pointer and span is None, "unit": "Unicode character or array item",
                "value": selected, "bytes": record["bytes"]}

    @staticmethod
    def bounds(length: int, start: int | None, end: int | None) -> tuple[int, int]:
        first, last = 0 if start is None else start, length if end is None else end
        if not 0 <= first <= last <= length:
            raise ValueError("Range endpoints must be zero-based, half-open, and within the saved value.")
        return first, last

    def image(self, job: str, raw: bytes, extension: str, meta: dict) -> dict:
        digest = sha256(raw).hexdigest()
        record = self.store.blob(job, "image", raw,
                                 {**meta, "extension": extension, "asset_path": f"assets/{digest}.{extension}"})
        return {"ref": record["ref"], "image_ref": record["ref"], **record["meta"]}

    def render_page(self, job: str, page: int, dpi: int = 144, region: list[float] | None = None) -> dict:
        if not 36 <= dpi <= 1200:
            raise ValueError("Render DPI must be between 36 and 1200.")
        with PDF_LOCK, pymupdf.open(stream=self.source(job), filetype="pdf") as document:
            if not 1 <= page <= len(document):
                raise ValueError("Page is outside this source.")
            source = document[page - 1]
            clip = pymupdf.Rect(region) if region is not None else source.rect
            if clip.is_empty or not source.rect.contains(clip):
                raise ValueError("The region must be a nonempty rectangle within the rotated page rectangle.")
            image = source.get_pixmap(dpi=dpi, clip=clip, alpha=False)
            meta = {"page": page, "dpi": dpi, "region": list(clip), "rotation": source.rotation,
                    "coordinate_frame": "rotated page points, top-left origin", "transform": [dpi / 72, dpi / 72, clip.x0, clip.y0],
                    "width": image.width, "height": image.height, "source_ref": self.store.get("job", job)["source_ref"],
                    "derivation": "lossless PNG render; no content edits"}
            return self.image(job, image.tobytes("png"), "png", meta)

    def extract_image(self, job: str, page: int, xref: int) -> dict:
        with PDF_LOCK, pymupdf.open(stream=self.source(job), filetype="pdf") as document:
            if not 1 <= page <= len(document):
                raise ValueError("Page is outside this source.")
            members = document[page - 1].get_images(full=True)
            item = next((item for item in members if item[0] == xref), None)
            if item is None:
                raise ValueError("The image reference does not belong to the specified page.")
            original = document.extract_image(xref)
            meta = {"page": page, "xref": xref, "width": original["width"], "height": original["height"],
                    "source_ref": self.store.get("job", job)["source_ref"], "derivation": "native embedded image extraction"}
            result = self.image(job, original["image"], original["ext"], meta)
            if item[1]:
                pix = pymupdf.Pixmap(document, xref)
                mask = pymupdf.Pixmap(document, item[1])
                composed = pymupdf.Pixmap(pix, mask)
                result = {**self.image(job, composed.tobytes("png"), "png", {**meta, "mask_xref": item[1],
                                                                                   "derivation": "embedded image with source soft mask"}),
                          "original_ref": result["ref"]}
            return result
