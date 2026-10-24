from __future__ import annotations

import base64
from hashlib import sha256
import json
import math
from pathlib import Path
import threading
import time
from typing import Any

import pymupdf

from .schema import Limits, Route, pointer
from .storage import Store, uid


# MuPDF is not thread-safe. Never share a live Document across callers.
PDF_LOCK = threading.RLock()
PAGE_FRAME = "PyMuPDF unrotated page points, top-left origin"


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
                item = {"page": number, "rect": list(page.rect * page.derotation_matrix), "rotation": page.rotation,
                        "coordinate_frame": PAGE_FRAME, "rotated_rect": list(page.rect),
                        "rotation_matrix": list(page.rotation_matrix), "derotation_matrix": list(page.derotation_matrix),
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
        if record["kind"] == "image_stream" and json_pointer:
            raise ValueError("An encoded image stream is binary. Use its index for metadata or full/raw byte ranges.")
        if view == "raw" or (view == "full" and record["kind"] == "image_stream"):
            raw = self.store.bytes(ref, job)
            first, last = self.bounds(len(raw), start, end)
            return {"ref": ref, "encoding": "base64", "unit": "byte", "range": [first, last],
                    "total": len(raw), "data": base64.b64encode(raw[first:last]).decode(), "complete": first == 0 and last == len(raw),
                    "meta": record["meta"]}
        if record["kind"] == "image":
            return {"ref": ref, "image_ref": ref, "meta": record["meta"], "bytes": record["bytes"],
                    "coverage": "complete saved image at native dimensions"}
        if view == "index" and record["kind"] == "image_stream":
            return {"ref": ref, "kind": record["kind"], "bytes": record["bytes"], "meta": record["meta"],
                    "complete": False, "read": "read_evidence(ref, view='raw', start=null, end=null)"}
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

    def image(self, job: str, raw: bytes, extension: str, meta: dict, *, component: bool = False) -> dict:
        digest = sha256(raw).hexdigest()
        record = self.store.blob(job, "image", raw,
                                 {**meta, "extension": extension,
                                  **({} if component else {"asset_path": f"assets/{digest}.{extension}"})})
        return {"ref": record["ref"], "image_ref": record["ref"], **record["meta"]}

    def render_page(self, job: str, page: int, dpi: int = 144, region: list[float] | None = None) -> dict:
        return self._render_page(job, page, dpi, region)

    def _render_page(self, job: str, page: int, dpi: int, region: list[float] | None,
                     provenance: dict | None = None) -> dict:
        if not 36 <= dpi <= 1200:
            raise ValueError("Render DPI must be between 36 and 1200.")
        with PDF_LOCK, pymupdf.open(stream=self.source(job), filetype="pdf") as document:
            if not 1 <= page <= len(document):
                raise ValueError("Page is outside this source.")
            source = document[page - 1]
            bounds = source.rect * source.derotation_matrix
            if region is not None and (len(region) != 4 or not all(math.isfinite(v) for v in region)):
                raise ValueError("The region needs four finite unrotated page coordinates.")
            clip = pymupdf.Rect(region) if region is not None else bounds
            if clip.is_empty or not bounds.contains(clip):
                raise ValueError("The region must be a nonempty rectangle within the unrotated page rectangle.")
            rotated = clip * source.rotation_matrix
            image = source.get_pixmap(dpi=dpi, clip=rotated, alpha=False)
            # MuPDF rounds the raster bounds to integer pixels. Use the actual
            # pixmap origin, not the fractional clip origin multiplied by DPI.
            mapping = source.rotation_matrix * pymupdf.Matrix(dpi / 72, dpi / 72) * pymupdf.Matrix(1, 0, 0, 1, -image.x, -image.y)
            meta = {"page": page, "dpi": dpi, "region": list(clip), "rotation": source.rotation,
                    "coordinate_frame": PAGE_FRAME, "rotated_region": list(rotated),
                    "pixel_origin": [image.x, image.y], "page_to_pixel": list(mapping), "pixel_to_page": list(~mapping),
                    "pixel_frame": "saved image pixels, top-left origin; page rotation preserved",
                    "width": image.width, "height": image.height, "source_ref": self.store.get("job", job)["source_ref"],
                    "derivation": "lossless PNG render; no content edits"}
            return self.image(job, image.tobytes("png"), "png", {**meta, **(provenance or {})})

    def extract_image(self, job: str, page: int, xref: int, occurrence: int | None = None, dpi: int = 144) -> dict:
        with PDF_LOCK, pymupdf.open(stream=self.source(job), filetype="pdf") as document:
            if not 1 <= page <= len(document):
                raise ValueError("Page is outside this source.")
            members = document[page - 1].get_images(full=True)
            item = next((item for item in members if item[0] == xref), None)
            if item is None:
                raise ValueError("The image reference does not belong to the specified page.")
            source_ref = self.store.get("job", job)["source_ref"]
            source_hash = self.store.get("blob", source_ref, job=job)["sha256"]
            originals = []
            for number in [xref, *([item[1]] if item[1] else [])]:
                raw = document.xref_stream_raw(number)
                filter_name = document.xref_get_key(number, "Filter")[1]
                extension = {"/DCTDecode": "jpeg", "/JPXDecode": "jpx"}.get(filter_name, "bin")
                record = self.store.blob(job, "image_stream", raw, {
                    "source_ref": source_ref, "source_sha256": source_hash, "xref": number,
                    "role": "image" if number == xref else "soft_mask", "filter": filter_name,
                    "object_dictionary": document.xref_object(number),
                    "derivation": "unmodified encoded PDF stream; object dependencies remain in the source PDF",
                    "extraction": f"PyMuPDF {pymupdf.VersionBind} Document.xref_stream_raw"})
                originals.append({"ref": record["ref"], "path": f"originals/{number}-{record['sha256']}.{extension}"})
            stencil = document.xref_get_key(xref, "ImageMask")[1] == "true"
            occurrences = []
            if stencil or occurrence is not None:
                occurrences = [{"occurrence": i, "region": list(rect), "image_to_page": list(matrix),
                                "render": {"page": page, "xref": xref, "occurrence": i, "dpi": dpi}}
                               for i, (rect, matrix) in enumerate(document[page - 1].get_image_rects(xref, transform=True))]
            if occurrence is not None:
                if isinstance(occurrence, bool) or not isinstance(occurrence, int) or not 0 <= occurrence < len(occurrences):
                    raise ValueError("Choose a zero-based occurrence listed for this image on this page.")
                selected = occurrences[occurrence]
                bounds = document[page - 1].rect * document[page - 1].derotation_matrix
                region = pymupdf.Rect(selected["region"]) & bounds
                return self._render_page(job, page, dpi, list(region), {
                    "representation": "rendered_occurrence", "source_image_kind": "stencil_mask" if stencil else "image",
                    "xref": xref, "occurrence": occurrence, "occurrence_region": selected["region"],
                    "image_to_page": selected["image_to_page"], "clipped_to_page": list(region) != selected["region"],
                    "original_ref": originals[0]["ref"], "originals": originals,
                    "original_bytes_equal": False, "source_sha256": source_hash,
                    "derivation": "PNG rendering of the selected page occurrence, including page graphics state and background",
                    "warnings": ["This page crop includes any overlapping content; it is not an isolated embedded image."],
                    "decoder": f"PyMuPDF {pymupdf.VersionBind} / MuPDF {pymupdf.VersionFitz}"})
            # extract_image may reencode CMYK JPEG as RGB JPEG. Do not publish
            # that lossy intermediate. Decode the PDF image directly instead.
            extracted = document.extract_image(xref)
            pix = pymupdf.Pixmap(document, xref)
            if stencil or pix.colorspace is None:
                return self.image(job, pix.tobytes("png"), "png", {
                    "representation": "stencil_mask", "display_semantics": "coverage_only",
                    "page": page, "xref": xref, "width": pix.width, "height": pix.height,
                    "source_ref": source_ref, "source_sha256": source_hash,
                    "original_ref": originals[0]["ref"], "originals": originals, "original_bytes_equal": False,
                    "coordinate_frame": PAGE_FRAME, "occurrences": occurrences,
                    "derivation": "decoded stencil coverage; page paint color, background and compositing are not included",
                    "warnings": ["This is a mask component, not the source page appearance. No deliverable asset_path is registered. "
                                 "Choose an occurrence with extract_image, render a page/region, or use another source-led method."],
                    "decoder": f"PyMuPDF {pymupdf.VersionBind} / MuPDF {pymupdf.VersionFitz}"}, component=True)
            colorspace = pix.colorspace.name if pix.colorspace else None
            conversion = bool(pix.colorspace and pix.colorspace.n not in {1, 3})
            embedded = self.store.bytes(originals[0]["ref"], job)
            unchanged = (not item[1] and not conversion and extracted["ext"] in {"jpeg", "png"}
                         and extracted["image"] == embedded and document.xref_get_key(xref, "Decode")[0] == "null")
            steps = []
            if unchanged:
                data, extension = embedded, extracted["ext"]
            else:
                steps.append("decode PDF image at native dimensions")
                if conversion:
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                    steps.append("convert source colorspace to RGB with MuPDF")
                if item[1]:
                    mask = pymupdf.Pixmap(document, item[1])
                    pix = pymupdf.Pixmap(pix, mask)
                    steps.append("compose source soft mask")
                data, extension = pix.tobytes("png"), "png"
                steps.append("encode decoded samples as PNG without resampling")
            bit_type, bit_value = document.xref_get_key(xref, "BitsPerComponent")
            source_bits = int(bit_value) if bit_type == "int" else None
            warnings = (["Display decoding uses 8-bit samples; higher-depth encoded originals remain available. "
                         "This display asset does not preserve the source sample precision."]
                        if not unchanged and source_bits and source_bits > 8 else [])
            meta = {"page": page, "xref": xref, "mask_xref": item[1], "width": pix.width, "height": pix.height,
                    "source_ref": source_ref, "source_sha256": source_hash,
                    "original_ref": originals[0]["ref"], "originals": originals,
                    "original_bytes_equal": data == embedded,
                    "representation": "embedded_stream" if unchanged else "derived_display",
                    "source_colorspace": colorspace, "color_conversion": conversion,
                    "source_bits_per_component": source_bits,
                    "display_bits_per_component": source_bits if unchanged else 8, "steps": steps, "warnings": warnings,
                    "derivation": "unchanged embedded image bytes" if unchanged else "; ".join(steps),
                    "decoder": f"PyMuPDF {pymupdf.VersionBind} / MuPDF {pymupdf.VersionFitz}"}
            return self.image(job, data, extension, meta)
