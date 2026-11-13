"""Occurrence facts, provenance records and primary-XMP enrichment (T3b).

Owners: docs/design/ASSET_REFERENCES.md "Versioned data and embedded schema" and
"Exact XMP namespace and serialization". The XMP writer is the product-selected
T1-F06 module ``primary_xmp.py`` (byte-identical to the qualified candidate),
called in-process through the same ``splice`` and ``postcheck`` functions that
its qualified ``prepare`` command runs.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
import re

from .asset_naming import EXTENSIONS

SELECTED_XMP_SHA256 = "74c30f2be61aec0de6baacabb89ec2c73f45b2acddfcb272914c2ea78220d6a2"
DIAGNOSTIC_PURPOSE = "saved-output diagnostic preview"
XML_FORBIDDEN = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")
TEXT_FIELDS = ("title", "container_title", "publication_date", "publisher", "full_citation")


class FactError(ValueError):
    def __init__(self, message: str, code: str = "ASSET_FACT_INVALID", details: dict | None = None):
        super().__init__(message)
        self.code, self.details = code, details or {}


def unknown() -> dict:
    return {"state": "unknown", "value": None, "basis": [], "alternatives": []}


def default_source(source_ref: str, source_sha256: str) -> dict:
    return {"source_ref": source_ref, "source_sha256": source_sha256, "media_type": "application/pdf",
            "kind": "unknown", **{name: unknown() for name in TEXT_FIELDS}, "creators": [], "identifiers": []}


def printed_info(page: dict) -> dict:
    """Shared page-map label as an embedded snapshot; legacy null state becomes unknown with its hint."""
    state = page.get("printed_state")
    if state is None:
        return {"state": "unknown", "value": None, "basis": [], "alternatives": [],
                "legacy_hint": page.get("printed", "unknown")}
    return {"state": state, "value": page["printed"] if state == "known" else None,
            "basis": page.get("printed_basis", []), "alternatives": page.get("printed_alternatives", []),
            "legacy_hint": None}


def page_patch(current: dict, patch: dict) -> dict:
    """Apply the evidenced page-label rules to one page-map patch (schema 2 saves)."""
    merged = {**current, **patch}
    if "printed" in patch and "printed_state" not in patch:
        merged["printed_state"] = {"unknown": "unknown", "none": "none"}.get(patch["printed"], "known")
    if "printed" in patch or "printed_state" in patch:
        state = merged["printed_state"]
        if state == "known" and (not merged["printed"] or not merged.get("printed_basis")):
            raise FactError("A known printed label needs the exact label and printed_basis evidence in the patch.")
        if state == "none" and (merged["printed"] != "none" or not merged.get("printed_basis")):
            raise FactError("A none printed state uses printed 'none' with printed_basis evidence of absence.")
        if state == "unknown" and merged["printed"] != "unknown":
            raise FactError("An unknown printed state uses printed 'unknown'; put unresolved readings in printed_alternatives.")
        if state is None:
            raise FactError("New page-label assertions need printed_state known, none or unknown.")
        if "printed" in patch and "printed_basis" not in patch and state in {"known", "none"} and patch["printed"] != current.get("printed"):
            raise FactError("A changed known/none printed label needs its printed_basis evidence in the patch.")
    return merged


def check_region(region, rect, what: str) -> None:
    if region is None:
        return
    x0, y0, x1, y1 = region
    if not all(math.isfinite(v) for v in region) or not (x0 < x1 and y0 < y1):
        raise FactError(f"{what} region must be finite and nonempty.")
    if x0 < rect[0] - 1e-6 or y0 < rect[1] - 1e-6 or x1 > rect[2] + 1e-6 or y1 > rect[3] + 1e-6:
        raise FactError(f"{what} region lies outside the unrotated page rectangle {rect}.")


EVIDENCE_KINDS = {"evidence", "image", "image_stream", "tool_result", "source_pdf", "document_view"}


def recorded_pages(blob: dict) -> set[int] | None:
    """Physical pages a stored evidence record was derived from, when its metadata establishes them."""
    meta = blob["meta"]
    if blob["kind"] == "image" and isinstance(meta.get("page"), int):
        return {meta["page"]}
    if blob["kind"] == "evidence" and isinstance(meta.get("pages"), list):
        return {p for p in meta["pages"] if isinstance(p, int)}
    return None


def overlaps(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def check_pointers(value, lookup, rects: dict[int, list[float]], scope: str) -> None:
    """Every evidence pointer must name existing task evidence and agree with its recorded page/region.

    A pointer may cite a page or region that the evidence itself does not record
    (e.g. a tool result); only facts the stored metadata establishes are compared.
    """
    for pointer in _pointers(value):
        ref, page, region = pointer["ref"], pointer.get("physical_page"), pointer.get("region")
        blob = lookup(ref)
        if blob is None:
            raise FactError(f"{scope}: evidence reference {ref} does not exist in this task.", "ASSET_NOT_OWNED")
        if blob["kind"] not in EVIDENCE_KINDS:
            raise FactError(f"{scope}: {ref} is a {blob['kind']} record, not source or tool evidence.")
        if page is None:
            continue
        if page not in rects:
            raise FactError(f"{scope}: evidence page {page} is outside this source.")
        check_region(region, rects[page], f"{scope} evidence")
        pages = recorded_pages(blob)
        if pages is not None and page not in pages:
            raise FactError(f"{scope}: evidence {ref} was recorded from physical page {sorted(pages)}, not page {page}.")
        recorded = blob["meta"].get("region") if blob["kind"] == "image" else None
        if region is not None and isinstance(recorded, list) and len(recorded) == 4 and not overlaps(region, recorded):
            raise FactError(f"{scope}: evidence region {region} lies outside the region {recorded} recorded for {ref}.")


def validate_source(source: dict) -> None:
    """A merged source must be complete; an invalid base fact names the field to repair."""
    from .schema import Creator, Identifier, TextFact
    if source.get("kind") not in {"book", "article", "document", "unknown"}:
        raise FactError("Source kind is invalid in the selected base. Supply source_update.kind to repair it.")
    for name in TEXT_FIELDS:
        try:
            TextFact.model_validate(source.get(name))
        except ValueError:
            raise FactError(f"Source fact {name} is invalid in the selected base. Supply source_update.{name} "
                            "(a complete TextFact; state 'unknown' if not established) to repair it.") from None
    for name, model in (("creators", Creator), ("identifiers", Identifier)):
        try:
            [model.model_validate(item) for item in source.get(name)]
        except (TypeError, ValueError):
            raise FactError(f"Source {name} is invalid in the selected base. Supply source_update.{name} "
                            "(a list, possibly empty) to repair it.") from None


def validate_occurrence(facts: dict, image: dict, pages: dict, rects: dict[int, list[float]], lookup) -> dict:
    """Check evidence, producer eligibility, locations against the image's derivation, and locator groups."""
    check_pointers(facts, lookup, rects, "Occurrence")
    meta = image["meta"]
    if image["kind"] != "image" or meta.get("purpose") == DIAGNOSTIC_PURPOSE:
        raise FactError("Only a source render_page or extract_image result can become a source-image deliverable; "
                        "a diagnostic saved-output preview cannot.")
    eligible = (meta.get("extension") == "png" and meta.get("representation") in {None, "derived_display", "rendered_occurrence"}
                or meta.get("extension") in {"jpeg", "jpg"} and meta.get("representation") == "embedded_stream"
                and meta.get("original_bytes_equal") is True)
    if not eligible or "asset_path" not in meta or meta["extension"] not in EXTENSIONS:
        raise FactError("This image is not an eligible MuPDF-generated PNG or unchanged PDF DCT JPEG deliverable.")
    image_pages = recorded_pages(image)
    image_region = meta.get("region") if isinstance(meta.get("region"), list) else None
    order: list[int] = []
    for location in facts["locations"]:
        page = location["physical_page"]
        if str(page) not in pages:
            raise FactError(f"Location page {page} is outside this source.")
        check_region(location["region"], rects[page], "Location")
        if image_pages is not None and page not in image_pages:
            # A genuine repeated occurrence elsewhere needs its own evidence from that page.
            separate = [p for p in location["basis"] if p["ref"] != image["ref"] and p.get("physical_page") == page
                        and (recorded_pages(lookup(p["ref"])) or set()) >= {page}]
            if not separate:
                raise FactError(f"Location page {page} differs from the image's recorded page {sorted(image_pages)}. Use the "
                                "render or extract from that page, or cite separate evidence recorded from that page "
                                "(render_page or inspect_pdf) in the location basis for a repeated occurrence.")
        elif location["region"] is not None and image_region is not None and not overlaps(location["region"], image_region):
            raise FactError(f"Location region {location['region']} does not overlap the image's recorded region {image_region}.")
        if page not in order:
            order.append(page)
    groups = facts["locator_groups"] or [{"kind": "single", "pages": [p], "basis": []} for p in order]
    covered = [p for g in groups for p in g["pages"]]
    if covered != order:
        raise FactError("Locator groups must cover each contributing physical page once, in first-contribution order.")
    for group in groups:
        members = group["pages"]
        if group["kind"] == "single" and len(members) != 1:
            raise FactError("A single locator group has exactly one page.")
        if group["kind"] == "range":
            if len(members) < 2 or members != list(range(members[0], members[0] + len(members))) or not group["basis"]:
                raise FactError("A range covers two or more consecutive physical pages with evidence for every member.")
            states = {printed_info(pages[str(p)])["state"] == "known" for p in members}
            if len(states) != 1:
                raise FactError("A range mixing confirmed printed and fallback labels must be expressed as single groups.")
            labels = [pages[str(p)]["printed"] for p in members]
            if states == {True} and all(l.isdigit() for l in labels) and [int(l) for l in labels] != list(range(int(labels[0]), int(labels[0]) + len(labels))):
                raise FactError("A printed range needs a continuous printed sequence.")
    return {**facts, "locator_groups": groups}


def _pointers(value):
    if isinstance(value, dict):
        if "note" in value and "ref" in value:
            yield value
        for v in value.values():
            yield from _pointers(v)
    elif isinstance(value, list):
        for v in value:
            yield from _pointers(v)


def provenance_record(*, occurrence_id: str, representation_id: str, source: dict, facts: dict, pages: dict,
                      image: dict, image_sha256: str, originals: list[dict], basename: str, collision: int | None) -> dict:
    locations = [{**loc, "printed": printed_info(pages[str(loc["physical_page"])])} for loc in facts["locations"]]
    return {"schema_version": 1, "occurrence_id": occurrence_id, "representation_id": representation_id,
            "source": source, "locations": locations,
            "image": {"image_ref": image["ref"], "sha256": image_sha256,
                      "media_type": EXTENSIONS[image["meta"]["extension"]], "derivation": image["meta"],
                      "originals": originals},
            "description": facts["description"], "caption": facts["caption"], "image_title": facts["image_title"],
            "figure": facts["figure"],
            "naming": {"policy": "readable-180-v1", "comparison_policy": "nfc-fullfold-u17-v1",
                       "assigned_basename": basename, "locator_groups": facts["locator_groups"],
                       "collision_suffix": collision}}


def record_json(record: dict) -> str:
    """Sorted keys, no insignificant whitespace, UTF-8; JSON-escape XML-forbidden scalars."""
    text = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    text.encode("utf-8", "strict")  # rejects unpaired surrogates
    return text.replace("\ufffe", "\\ufffe").replace("\uffff", "\\uffff")


def display(text: str) -> str:
    return "JSON-escaped: " + json.dumps(text, ensure_ascii=True) if XML_FORBIDDEN.search(text) else text


def fact_text(fact: dict) -> str:
    if fact["state"] == "known":
        return display(fact["value"])
    if fact["state"] == "conflicting":
        return "conflicting: " + " | ".join(display(a["value"]) for a in fact["alternatives"])
    return fact["state"]


def xmp_values(record: dict) -> dict:
    """Standard display fields and the four pdfmd properties, all from one record."""
    desc, source = record["description"], record["source"]
    title = record["image_title"]["value"] if record["image_title"]["state"] == "known" else desc["filename"]
    lines = [f"Source caption: {fact_text(record['caption'])}"]
    lines.append(f"Description (agent-authored): {display(desc['full'])}")
    lines.append(f"Image title: {fact_text(record['image_title'])}"
                 + ("" if record["image_title"]["state"] == "known" else f"; derived label: {display(desc['filename'])}"))
    lines.append(f"Source kind: {source['kind']}")
    for name, label in (("title", "Source title"), ("container_title", "Container title"), ("full_citation", "Citation"),
                        ("publisher", "Publisher"), ("publication_date", "Publication date")):
        lines.append(f"{label}: {fact_text(source[name])}")
    for creator in source["creators"]:
        lines.append(f"Creator ({display(creator['role'])}): {fact_text(creator['name'])}")
    for identifier in source["identifiers"]:
        lines.append(f"Identifier ({display(identifier['scheme'])}): {display(identifier['value'])}")
    lines.append(f"Source SHA-256: {source['source_sha256']}")
    figure = fact_text(record["figure"])
    for loc in record["locations"]:
        printed = loc["printed"]
        label = display(printed["value"]) if printed["state"] == "known" else printed["state"]
        if printed["legacy_hint"] is not None:
            label += f" (unconfirmed hint: {display(printed['legacy_hint'])})"
        lines.append(f"Physical page: {loc['physical_page']}; printed: {label}; figure: {figure}")
    text = "\n".join(lines)
    langs = {"x-default": display(title)}
    descriptions = {"x-default": text}
    if desc["language"] != "und":
        langs[desc["language"]] = langs["x-default"]
        descriptions[desc["language"]] = text
    return {"title": langs, "description": descriptions, "source": "urn:sha256:" + source["source_sha256"],
            "pdfmd": {"SchemaVersion": 1, "OccurrenceId": record["occurrence_id"],
                      "RepresentationId": record["representation_id"], "RecordJSON": record_json(record)}}


def enrich(data: bytes, values: dict, folder) -> bytes:
    """Run the selected module's prepare (splice + postcheck) in the bounded worker process.

    A rejection or a process failure (limit, timeout, crash) raises FactError with
    ASSET_ENRICHMENT_FAILED; the worker's preparation folder is then retained.
    """
    from .xmp_worker import WorkerFailure, enrich_bounded
    try:
        return enrich_bounded(data, values, folder)
    except WorkerFailure as exc:
        raise FactError(str(exc), "ASSET_ENRICHMENT_FAILED", exc.details) from None
    except OSError as exc:  # the worker could not be started or bounded
        raise FactError(f"The bounded XMP writer process could not be started or bounded ({exc}).",
                        "ASSET_ENRICHMENT_FAILED", {"stage": "process", "code": "process_failed"}) from None


def module_identity() -> str:
    from importlib.resources import files
    return sha256(files("pdfmd").joinpath("primary_xmp.py").read_bytes()).hexdigest()


def enrich_object(store, ref: str, job: str, values: dict, folder):
    """File-based enrichment returning the attempt folder, output path and verified SHA-256.

    The engine never loads the image: the store object is copied into the attempt
    in chunks, and the caller registers the output against that digest before ``finish``.
    """
    from .xmp_worker import WorkerFailure, prepare_object
    try:
        return prepare_object(store, ref, job, values, folder)
    except WorkerFailure as exc:
        raise FactError(str(exc), "ASSET_ENRICHMENT_FAILED", exc.details) from None
    except OSError as exc:
        raise FactError(f"The bounded XMP writer process could not be started or bounded ({exc}).",
                        "ASSET_ENRICHMENT_FAILED", {"stage": "process", "code": "process_failed"}) from None
    except ValueError as exc:  # the source object failed its streamed integrity check during the copy
        raise FactError(f"The source image failed its integrity check while it was prepared ({exc}).",
                        "ASSET_INTEGRITY_FAILED", {"stage": "input", "code": "integrity"}) from None
