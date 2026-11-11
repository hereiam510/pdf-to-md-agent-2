"""T1-F06 qualification candidate: primary-XMP-only PNG/JPEG enrichment.

This is a qualification artifact, not application code. It reads one input
image, validates its container and primary XMP strictly, writes only the
primary XMP (PNG iTXt, or JPEG StandardXMP APP1 plus its ExtendedXMP APP1
group), blanks any legacy APP13 0x0424 / EXIF IFD0 0x02BC XMP value in place
at the same length (B-lite, 2026-11-10), copies every other byte range
unchanged, reopens its own output and
re-validates it before the output file is published.

Usage (run as a child of the bounded Windows Job worker):
  primary_xmp.py prepare --input IN --output OUT --values VALUES.json --report REPORT.json [--inject DEFECT]
Exit codes: 0 accepted (OUT written), 2 rejected (no OUT), anything else is a harness failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
from xml.dom import minidom
from xml.parsers import expat
import zlib

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
X = "adobe:ns:meta/"
XMLNS = "http://www.w3.org/2000/xmlns/"
XML = "http://www.w3.org/XML/1998/namespace"
DC = "http://purl.org/dc/elements/1.1/"
PDFMD = "urn:pdfmd:asset-provenance:1"
NOTE = "http://ns.adobe.com/xmp/note/"
ALLOWED = {(DC, "title"), (DC, "description"), (DC, "source"), (PDFMD, "SchemaVersion"),
           (PDFMD, "OccurrenceId"), (PDFMD, "RepresentationId"), (PDFMD, "RecordJSON")}
FRAMING = {(NOTE, "HasExtendedXMP")}
STD_SIG = b"http://ns.adobe.com/xap/1.0/\x00"
EXT_SIG = b"http://ns.adobe.com/xmp/extension/\x00"
PNG_SIG = b"\x89PNG\r\n\x1a\n"
PNG_XMP_KEYWORDS = {b"XML:com.adobe.xmp", b"Raw profile type xmp", b"Raw profile type APP1"}
PNG_XMP_CARRIERS = {b"caBX", b"tXMP", b"eXIf", b"zXIf"}  # outside the generated-PNG profile
MAX_XML = 16 * 1024 * 1024
STD_LIMIT = 65000          # Adobe Part 3 recommended StandardXMP packet budget
EXT_DATA = 65400           # <= 65458 data bytes per extension segment
GUID_RE = re.compile(rb"[0-9A-F]{32}")
PACKET_ID = "W5M0MpCehiHzreSzNTczkc9d"


class Reject(Exception):
    def __init__(self, stage: str, code: str, message: str):
        super().__init__(message)
        self.stage, self.code = stage, code


def md5_upper(data: bytes) -> str:
    return hashlib.md5(data).hexdigest().upper()


# ---------------------------------------------------------------- containers
def parse_png(data: bytes) -> dict:
    if not data.startswith(PNG_SIG):
        raise Reject("container", "not_png", "Input is not a PNG file.")
    chunks, pos = [], 8
    while True:
        if pos + 12 > len(data):
            raise Reject("container", "png_truncated", "PNG chunk header runs past the end of the file.")
        size = struct.unpack_from(">I", data, pos)[0]
        end = pos + 12 + size
        if size > 0x7FFFFFFF or end > len(data):
            raise Reject("container", "png_bounds", "PNG chunk length exceeds the remaining bytes.")
        kind, payload = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + size]
        if struct.unpack_from(">I", data, pos + 8 + size)[0] != zlib.crc32(kind + payload):
            raise Reject("container", "png_crc", f"PNG {kind!r} chunk CRC mismatch.")
        chunks.append({"start": pos, "end": end, "kind": kind, "payload": payload})
        pos = end
        if kind == b"IEND":
            break
    if chunks[0]["kind"] != b"IHDR" or not any(c["kind"] == b"IDAT" for c in chunks):
        raise Reject("container", "png_structure", "PNG must start with IHDR and contain IDAT.")
    return {"format": "png", "chunks": chunks, "trailer": data[pos:]}


def png_profile(parsed: dict) -> None:
    """The generated-PNG input profile: no XMP-bearing or provenance carrier chunks."""
    for c in parsed["chunks"]:
        keyword = c["payload"].split(b"\x00", 1)[0] if c["kind"] in (b"iTXt", b"zTXt", b"tEXt") else None
        if keyword in PNG_XMP_KEYWORDS:
            raise Reject("profile", "png_unexpected_xmp", f"Unexpected XMP-bearing {c['kind'].decode()} chunk ({keyword.decode()}).")
        if c["kind"] in PNG_XMP_CARRIERS:
            raise Reject("profile", "png_unexpected_carrier", f"Unexpected {c['kind'].decode()} chunk outside the generated-PNG profile.")


def parse_jpeg(data: bytes) -> dict:
    if data[:2] != b"\xff\xd8":
        raise Reject("container", "not_jpeg", "Input is not a JPEG file.")
    segments, pos = [], 2
    while True:
        if pos + 2 > len(data) or data[pos] != 0xFF:
            raise Reject("container", "jpeg_marker", f"Expected a JPEG marker at offset {pos}.")
        start = pos
        while pos < len(data) and data[pos] == 0xFF:
            pos += 1
        if pos >= len(data):
            raise Reject("container", "jpeg_truncated", "JPEG ends inside a marker.")
        marker = data[pos]
        pos += 1
        if marker == 0xDA:
            return {"format": "jpeg", "segments": segments, "tail_start": start, "tail": data[start:]}
        if marker in (0x01, 0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            raise Reject("container", "jpeg_structure", f"Unexpected standalone marker FF{marker:02X} before the first scan.")
        if pos + 2 > len(data):
            raise Reject("container", "jpeg_truncated", "JPEG segment length runs past the end of the file.")
        size = struct.unpack_from(">H", data, pos)[0]
        if size < 2 or pos + size > len(data):
            raise Reject("container", "jpeg_bounds", f"JPEG FF{marker:02X} segment length exceeds the remaining bytes.")
        segments.append({"start": start, "end": pos + size, "marker": marker, "payload_start": pos + 2,
                         "payload": data[pos + 2:pos + size]})
        pos += size


def jpeg_segment(marker: int, payload: bytes) -> bytes:
    if len(payload) + 2 > 0xFFFF:
        raise Reject("serialize", "segment_too_large", "A JPEG segment exceeds 65,535 bytes.")
    return b"\xff" + bytes([marker]) + struct.pack(">H", len(payload) + 2) + payload


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))


# ----------------------------------------------------------------- XMP/XML
def strict_xml(data: bytes, label: str) -> minidom.Document:
    if len(data) > MAX_XML:
        raise Reject("xml", "xml_too_large", f"{label} exceeds the {MAX_XML} byte bound.")
    try:
        data.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise Reject("xml", "invalid_utf8", f"{label} is not valid UTF-8 at byte {exc.start}.") from None
    parser = expat.ParserCreate(encoding="UTF-8", namespace_separator=" ")
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)

    def forbid(*_args):
        raise Reject("xml", "dtd_forbidden", f"{label} declares a DTD or entity; XMP forbids them and none is resolved.")
    parser.StartDoctypeDeclHandler = forbid
    parser.EntityDeclHandler = forbid
    parser.ExternalEntityRefHandler = lambda *a: 0
    try:
        parser.Parse(data, True)
    except expat.ExpatError as exc:
        raise Reject("xml", "malformed_xml", f"{label} is not well-formed XML: {exc}.") from None
    # The DTD/entity gate above has passed, so the DOM builder expands nothing.
    return minidom.parseString(data)


def in_scope_namespaces(element) -> dict[str, str]:
    scope: dict[str, str] = {}
    node = element
    while node is not None and node.nodeType == node.ELEMENT_NODE:
        for attr in list(node.attributes.values()):
            if attr.name == "xmlns" or attr.name.startswith("xmlns:"):
                scope.setdefault(attr.name, attr.value)
        node = node.parentNode
    return scope


def canon(node) -> tuple:
    if node.nodeType in (node.TEXT_NODE, node.CDATA_SECTION_NODE):
        return ("#text", node.data)
    attrs = tuple(sorted((a.namespaceURI or "", a.localName, a.value) for a in node.attributes.values()
                         if a.namespaceURI != XMLNS and a.name != "xmlns"))
    elements = [c for c in node.childNodes if c.nodeType == c.ELEMENT_NODE]
    if elements:
        if any(c.nodeType in (c.TEXT_NODE, c.CDATA_SECTION_NODE) and c.data.strip() for c in node.childNodes):
            raise Reject("xml", "mixed_content", f"Mixed content in {node.tagName} is not valid RDF.")
        return (node.namespaceURI or "", node.localName, attrs, tuple(canon(c) for c in elements), None)
    text = "".join(c.data for c in node.childNodes if c.nodeType in (c.TEXT_NODE, c.CDATA_SECTION_NODE))
    return (node.namespaceURI or "", node.localName, attrs, (), text)


class Packet:
    """Top-level properties of one logical XMP record (standard + extension)."""

    def __init__(self):
        self.about: str | None = None
        self.props: dict[tuple[str, str], dict] = {}

    def add_document(self, doc: minidom.Document, label: str) -> None:
        root = doc.documentElement
        if (root.namespaceURI, root.localName) == (X, "xmpmeta"):
            rdfs = [c for c in root.childNodes if c.nodeType == c.ELEMENT_NODE]
            if len(rdfs) != 1 or (rdfs[0].namespaceURI, rdfs[0].localName) != (RDF, "RDF"):
                raise Reject("xmp", "xmp_structure", f"{label}: x:xmpmeta must contain exactly one rdf:RDF.")
            rdf = rdfs[0]
        elif (root.namespaceURI, root.localName) == (RDF, "RDF"):
            rdf = root
        else:
            raise Reject("xmp", "xmp_structure", f"{label}: root must be x:xmpmeta or rdf:RDF.")
        for child in rdf.childNodes:
            if child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE) and child.data.strip():
                raise Reject("xmp", "xmp_structure", f"{label}: text directly inside rdf:RDF.")
            if child.nodeType != child.ELEMENT_NODE:
                continue
            if (child.namespaceURI, child.localName) != (RDF, "Description"):
                raise Reject("xmp", "xmp_structure", f"{label}: rdf:RDF may contain only rdf:Description (found {child.tagName}).")
            self._description(child, label)

    def _description(self, desc, label: str) -> None:
        for attr in list(desc.attributes.values()):
            if attr.name == "xmlns" or attr.name.startswith("xmlns:"):
                continue
            key = (attr.namespaceURI or "", attr.localName)
            if key == (RDF, "about"):
                if self.about is not None and self.about != attr.value:
                    raise Reject("xmp", "about_conflict", f"{label}: rdf:about values disagree.")
                self.about = attr.value
                continue
            if attr.namespaceURI in (RDF, XML, None, ""):
                raise Reject("xmp", "unsupported_attribute", f"{label}: unsupported rdf:Description attribute {attr.name}.")
            self._put(key, {"form": "attribute", "name": attr.name, "value": attr.value,
                            "canon": (key[0], key[1], (), (), attr.value)}, label)
        for child in desc.childNodes:
            if child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE) and child.data.strip():
                raise Reject("xmp", "xmp_structure", f"{label}: text directly inside rdf:Description.")
            if child.nodeType != child.ELEMENT_NODE:
                continue
            key = (child.namespaceURI or "", child.localName)
            if not key[0]:
                raise Reject("xmp", "unqualified_property", f"{label}: property {child.tagName} has no namespace.")
            self._put(key, {"form": "element", "node": child, "canon": canon(child)}, label)

    def _put(self, key, prop, label) -> None:
        if key in self.props:
            raise Reject("xmp", "duplicate_property", f"{label}: property {{{key[0]}}}{key[1]} occurs more than once.")
        self.props[key] = prop

    def preserved(self) -> dict:
        return {k: v for k, v in self.props.items() if k not in ALLOWED and k not in FRAMING}


def esc(text: str, attr: bool = False) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if attr:
        text = text.replace('"', "&quot;")
    # XML parsers normalize raw CR; a character reference keeps the exact value.
    return text.replace("\r", "&#13;")


def serialize_node(node, declare: dict[str, str] | None = None) -> str:
    """Normalized RDF/XML: same names, attributes and values; comments dropped, CDATA escaped.

    Comments and CDATA boundaries are not part of the XMP data model, and tag-like
    text inside them is misparsed by non-XML metadata scanners.
    """
    if node.nodeType in (node.TEXT_NODE, node.CDATA_SECTION_NODE):
        return esc(node.data)
    if node.nodeType != node.ELEMENT_NODE:
        return ""
    attrs = dict(declare or {})
    for a in node.attributes.values():
        attrs[a.name] = a.value
    head = node.tagName + "".join(f' {name}="{esc(value, True)}"' for name, value in attrs.items())
    inner = "".join(serialize_node(c) for c in node.childNodes)
    return f"<{head}>{inner}</{node.tagName}>"


def serialize_preserved(key, prop) -> str:
    if prop["form"] == "attribute":
        prefix = prop["name"].split(":", 1)[0]
        return f'<{prefix}:{key[1]} xmlns:{prefix}="{esc(key[0], True)}">{esc(prop["value"])}</{prefix}:{key[1]}>'
    scope = {n: v for n, v in in_scope_namespaces(prop["node"]).items() if not prop["node"].hasAttribute(n)}
    return serialize_node(prop["node"], scope)


BLANK_HEAD = (f'<?xpacket begin="﻿" id="{PACKET_ID}"?><x:xmpmeta xmlns:x="{X}">'
              f'<rdf:RDF xmlns:rdf="{RDF}"></rdf:RDF></x:xmpmeta>\n').encode("utf-8")
BLANK_TAIL = b'<?xpacket end="w"?>'


def blank_packet(size: int) -> bytes | None:
    """An empty XMP packet of exactly `size` bytes (space padding), or None if it cannot fit."""
    pad = size - len(BLANK_HEAD) - len(BLANK_TAIL)
    return None if pad < 0 else BLANK_HEAD + b" " * pad + BLANK_TAIL


def legacy_xmp_carriers(parsed: dict) -> list[dict]:
    """Top-level legacy JPEG carriers that a whole-file reader may merge with the primary record.

    Each entry gives the carrier name and the absolute byte range of its value.
    """
    found = []
    for s in parsed["segments"]:
        p, base = s["payload"], s["payload_start"]
        if s["marker"] == 0xED and p.startswith(b"Photoshop 3.0\x00"):
            pos = 14
            while pos < len(p):
                if p[pos:pos + 4] != b"8BIM" or pos + 7 > len(p):
                    raise Reject("profile", "legacy_unparseable", "Photoshop APP13 resource block is malformed; competing XMP cannot be excluded.")
                resource = struct.unpack_from(">H", p, pos + 4)[0]
                name_len = p[pos + 6]
                pos += 6 + 1 + name_len + ((1 + name_len) % 2)
                if pos + 4 > len(p):
                    raise Reject("profile", "legacy_unparseable", "Photoshop APP13 resource length is truncated.")
                size = struct.unpack_from(">I", p, pos)[0]
                pos += 4
                if pos + size > len(p):
                    raise Reject("profile", "legacy_unparseable", "Photoshop APP13 resource exceeds its segment.")
                if resource == 0x0424:
                    found.append({"carrier": "APP13 Photoshop 0x0424", "start": base + pos, "end": base + pos + size,
                                  "value": p[pos:pos + size]})
                pos += size + (size % 2)
        if s["marker"] == 0xE1 and p.startswith(b"Exif\x00\x00"):
            tiff = p[6:]
            if len(tiff) < 8 or tiff[:2] not in (b"II", b"MM"):
                raise Reject("profile", "legacy_unparseable", "EXIF APP1 TIFF header is malformed; competing XMP cannot be excluded.")
            order = "<" if tiff[:2] == b"II" else ">"
            ifd = struct.unpack_from(order + "I", tiff, 4)[0]
            if ifd + 2 > len(tiff):
                raise Reject("profile", "legacy_unparseable", "EXIF IFD0 offset is outside the segment.")
            count = struct.unpack_from(order + "H", tiff, ifd)[0]
            if ifd + 2 + count * 12 > len(tiff):
                raise Reject("profile", "legacy_unparseable", "EXIF IFD0 entries exceed the segment.")
            for i in range(count):
                entry = ifd + 2 + i * 12
                tag, kind, size = struct.unpack_from(order + "HHI", tiff, entry)
                if tag != 0x02BC:
                    continue
                if kind not in (1, 7):
                    raise Reject("profile", "legacy_unparseable", f"EXIF IFD0 0x02BC has TIFF type {kind}; expected BYTE or UNDEFINED.")
                at = entry + 8 if size <= 4 else struct.unpack_from(order + "I", tiff, entry + 8)[0]
                if at + size > len(tiff):
                    raise Reject("profile", "legacy_unparseable", "EXIF IFD0 0x02BC value exceeds the segment.")
                found.append({"carrier": "EXIF IFD0 0x02BC", "start": base + 6 + at, "end": base + 6 + at + size,
                              "value": tiff[at:at + size]})
    return found


def blank_legacy(data: bytes, parsed: dict) -> tuple[bytes, list[dict]]:
    """B-lite: overwrite each legacy XMP value in place with an empty packet of the same length.

    Nothing is resized or moved, so segment lengths, IRB sizes, IFD counts and offsets
    stay valid. The legacy packet must be valid XMP; its properties are discarded from
    the delivered image only (the retained original keeps them).
    """
    out, report = bytearray(data), []
    for c in legacy_xmp_carriers(parsed):
        value, size = c["value"], c["end"] - c["start"]
        blank = blank_packet(size)
        if value == blank:
            report.append({"carrier": c["carrier"], "bytes": size, "already_blank": True})
            continue
        if blank is None:
            raise Reject("profile", "legacy_xmp_too_short", f"{c['carrier']} holds {size} bytes, fewer than the "
                         f"{len(BLANK_HEAD) + len(BLANK_TAIL)}-byte empty packet; it cannot be blanked at the same length.")
        legacy = Packet()
        try:
            legacy.add_document(strict_xml(value.rstrip(b"\x00"), c["carrier"]), c["carrier"])
        except Reject as rej:
            raise Reject("profile", "legacy_malformed", f"{c['carrier']} is not valid XMP ({rej.code}); "
                         "it cannot be blanked safely.") from None
        out[c["start"]:c["end"]] = blank
        report.append({"carrier": c["carrier"], "bytes": size, "discarded_properties": len(legacy.props)})
    return bytes(out), report


def generated(values: dict) -> dict:
    def alt(prefix, local, langs):
        items = "".join(f'<rdf:li xml:lang="{esc(lang, True)}">{esc(text)}</rdf:li>' for lang, text in langs.items())
        return f'<{prefix}:{local} xmlns:{prefix}="{DC}"><rdf:Alt>{items}</rdf:Alt></{prefix}:{local}>'
    out = {(DC, "title"): alt("dc", "title", values["title"]),
           (DC, "description"): alt("dc", "description", values["description"]),
           (DC, "source"): f'<dc:source xmlns:dc="{DC}">{esc(values["source"])}</dc:source>'}
    for local in ("SchemaVersion", "OccurrenceId", "RepresentationId", "RecordJSON"):
        out[(PDFMD, local)] = f'<pdfmd:{local} xmlns:pdfmd="{PDFMD}">{esc(str(values["pdfmd"][local]))}</pdfmd:{local}>'
    return out


def wrap(about: str, items: list[str], *, guid: str | None, packet: bool, padding: int) -> bytes:
    note = f' xmlns:xmpNote="{NOTE}" xmpNote:HasExtendedXMP="{guid}"' if guid else ""
    body = (f'<x:xmpmeta xmlns:x="{X}"><rdf:RDF xmlns:rdf="{RDF}">'
            f'<rdf:Description rdf:about="{esc(about, True)}"{note}>' + "".join(items) +
            "</rdf:Description></rdf:RDF></x:xmpmeta>")
    if packet:
        body = f'<?xpacket begin="﻿" id="{PACKET_ID}"?>' + body + "\n" + " " * padding + '\n<?xpacket end="w"?>'
    return body.encode("utf-8")


def build_record(existing: Packet, values: dict, fmt: str) -> tuple[bytes, bytes | None]:
    about = existing.about or ""
    items = {k: serialize_preserved(k, p) for k, p in existing.preserved().items()}
    items.update(generated(values))
    order = list(items)
    if fmt == "png":
        return wrap(about, [items[k] for k in order], guid=None, packet=True, padding=2048), None
    standard = list(order)
    extended: list = []
    placeholder = "0" * 32
    def std_size():
        return len(wrap(about, [items[k] for k in standard], guid=placeholder if extended else None, packet=True, padding=0))
    while std_size() > STD_LIMIT:
        movable = [k for k in standard]
        if not movable:
            raise Reject("serialize", "standard_too_large", "StandardXMP cannot fit even after moving every property.")
        first = (PDFMD, "RecordJSON") if (PDFMD, "RecordJSON") in standard else max(movable, key=lambda k: len(items[k].encode()))
        standard.remove(first)
        extended.append(first)
    if not extended:
        packet = wrap(about, [items[k] for k in standard], guid=None, packet=True, padding=min(2048, STD_LIMIT - std_size()))
        return packet, None
    ext = wrap(about, [items[k] for k in extended], guid=None, packet=False, padding=0)
    guid = md5_upper(ext)
    return wrap(about, [items[k] for k in standard], guid=guid, packet=True, padding=0), ext


# ------------------------------------------------------------- primary scan
def locate_jpeg_primary(parsed: dict) -> dict:
    standard = [s for s in parsed["segments"] if s["marker"] == 0xE1 and s["payload"].startswith(STD_SIG)]
    extension = [s for s in parsed["segments"] if s["marker"] == 0xE1 and s["payload"].startswith(EXT_SIG)]
    for s in parsed["segments"]:
        if s["marker"] == 0xE2 and s["payload"].startswith(b"MPF\x00"):
            raise Reject("profile", "mpf_unsupported", "MPF-bearing JPEG: enrichment would change the MP Index image size; unsupported.")
    if len(standard) > 1:
        raise Reject("xmp", "competing_primary", f"{len(standard)} StandardXMP APP1 segments compete for the primary record.")
    legacy = [c["carrier"] for c in legacy_xmp_carriers(parsed) if c["value"] != blank_packet(c["end"] - c["start"])]
    if legacy:
        raise Reject("profile", "legacy_xmp_competes", "A non-empty legacy XMP packet would compete with the primary record "
                     "in whole-file readers: " + ", ".join(legacy) + ".")
    packet = Packet()
    ext_bytes = None
    guid = None
    if standard:
        packet.add_document(strict_xml(standard[0]["payload"][len(STD_SIG):], "StandardXMP"), "StandardXMP")
        note = packet.props.get((NOTE, "HasExtendedXMP"))
        if note:
            guid = note["value"] if note["form"] == "attribute" else note["canon"][4]
            if not isinstance(guid, str) or not GUID_RE.fullmatch(guid.encode()):
                raise Reject("extended", "bad_guid", "xmpNote:HasExtendedXMP is not a 32-character uppercase MD5 GUID.")
    if extension and guid is None:
        raise Reject("extended", "orphan_extension", "ExtendedXMP segments exist without an associated StandardXMP GUID.")
    if guid is not None:
        ext_bytes = reconstruct_extension(extension, guid)
        packet.add_document(strict_xml(ext_bytes, "ExtendedXMP"), "ExtendedXMP")
    return {"standard": standard[0] if standard else None, "extension": extension, "packet": packet,
            "guid": guid, "extension_bytes": ext_bytes}


def reconstruct_extension(segments: list[dict], guid: str) -> bytes:
    if not segments:
        raise Reject("extended", "missing_extension", "StandardXMP declares ExtendedXMP but no extension segment exists.")
    parts, total = [], None
    for s in segments:
        p = s["payload"]
        if len(p) < len(EXT_SIG) + 40:
            raise Reject("extended", "short_extension", "ExtendedXMP segment header is truncated.")
        seg_guid = p[len(EXT_SIG):len(EXT_SIG) + 32]
        if seg_guid != guid.encode():
            raise Reject("extended", "guid_mismatch", "An ExtendedXMP segment belongs to a different GUID than the StandardXMP declares.")
        full, offset = struct.unpack_from(">II", p, len(EXT_SIG) + 32)
        if total is not None and full != total:
            raise Reject("extended", "length_conflict", "ExtendedXMP segments disagree on the full length.")
        total = full
        parts.append((offset, p[len(EXT_SIG) + 40:]))
    if total > MAX_XML:
        raise Reject("extended", "extension_too_large", "ExtendedXMP full length exceeds the bound.")
    parts.sort(key=lambda item: item[0])
    cursor = 0
    for offset, data in parts:
        if offset < cursor:
            raise Reject("extended", "overlap", f"ExtendedXMP fragments overlap at offset {offset}.")
        if offset > cursor:
            raise Reject("extended", "gap", f"ExtendedXMP is missing bytes {cursor}..{offset}.")
        cursor = offset + len(data)
    if cursor != total:
        raise Reject("extended", "incomplete", f"ExtendedXMP fragments cover {cursor} of {total} bytes.")
    assembled = b"".join(data for _, data in parts)
    if md5_upper(assembled) != guid:
        raise Reject("extended", "digest_mismatch", "ExtendedXMP MD5 digest does not match its GUID.")
    return assembled


def locate_png_primary(parsed: dict) -> dict:
    found = [c for c in parsed["chunks"] if c["kind"] in (b"iTXt", b"zTXt", b"tEXt")
             and c["payload"].split(b"\x00", 1)[0] in PNG_XMP_KEYWORDS]
    if len(found) != 1 or found[0]["kind"] != b"iTXt":
        raise Reject("postcheck", "png_primary_count", f"Expected exactly one primary iTXt XMP chunk, found {len(found)}.")
    p = found[0]["payload"]
    keyword, rest = p.split(b"\x00", 1)
    flag, method = rest[0], rest[1]
    lang, rest = rest[2:].split(b"\x00", 1)
    translated, text = rest.split(b"\x00", 1)
    if flag != 0 or method != 0:
        raise Reject("postcheck", "png_compressed", "Generated primary iTXt must be uncompressed.")
    packet = Packet()
    packet.add_document(strict_xml(text, "PNG iTXt XMP"), "PNG iTXt XMP")
    return {"chunk": found[0], "packet": packet}


# ------------------------------------------------------------------ prepare
def splice(data: bytes, values: dict) -> tuple[bytes, dict]:
    if data.startswith(PNG_SIG):
        parsed = parse_png(data)
        png_profile(parsed)
        xml, _ = build_record(Packet(), values, "png")
        new = png_chunk(b"iTXt", b"XML:com.adobe.xmp\x00\x00\x00\x00\x00" + xml)
        first_idat = next(i for i, c in enumerate(parsed["chunks"]) if c["kind"] == b"IDAT")
        out = PNG_SIG + b"".join(data[c["start"]:c["end"]] for c in parsed["chunks"][:first_idat]) + new + \
            b"".join(data[c["start"]:c["end"]] for c in parsed["chunks"][first_idat:]) + parsed["trailer"]
        return out, {"format": "png", "mode": "create", "standard_bytes": len(xml)}
    if data[:2] == b"\xff\xd8":
        data, legacy = blank_legacy(data, parse_jpeg(data))
        parsed = parse_jpeg(data)
        primary = locate_jpeg_primary(parsed)
        standard, ext = build_record(primary["packet"], values, "jpeg")
        group = jpeg_segment(0xE1, STD_SIG + standard)
        fragments = 0
        if ext is not None:
            guid = md5_upper(ext).encode()
            for offset in range(0, len(ext), EXT_DATA):
                group += jpeg_segment(0xE1, EXT_SIG + guid + struct.pack(">II", len(ext), offset) + ext[offset:offset + EXT_DATA])
                fragments += 1
        drop = {id(s) for s in primary["extension"]}
        out, placed = [data[:2]], False
        segs = parsed["segments"]
        if primary["standard"] is None:
            # Insert after leading JFIF/APP0 and EXIF APP1, before other metadata.
            lead = 0
            while lead < len(segs) and (segs[lead]["marker"] == 0xE0 or
                                         (segs[lead]["marker"] == 0xE1 and segs[lead]["payload"].startswith(b"Exif\x00"))):
                lead += 1
            for i, s in enumerate(segs):
                if i == lead:
                    out.append(group); placed = True
                out.append(data[s["start"]:s["end"]])
            if not placed:
                out.append(group)
        else:
            for s in segs:
                if s is primary["standard"]:
                    out.append(group)
                elif id(s) not in drop:
                    out.append(data[s["start"]:s["end"]])
        out.append(parsed["tail"])
        return b"".join(out), {"format": "jpeg", "mode": "merge" if primary["standard"] else "create",
                               "standard_bytes": len(standard), "extension_bytes": len(ext or b""),
                               "extension_fragments": fragments, "preserved_properties": len(primary["packet"].preserved()),
                               "legacy_blanked": legacy}
    raise Reject("container", "unsupported_type", "Input is neither PNG nor JPEG by content.")


def copied_ranges(data: bytes) -> list[bytes]:
    """Every byte range outside the primary XMP group, in order."""
    if data.startswith(PNG_SIG):
        parsed = parse_png(data)
        return [data[c["start"]:c["end"]] for c in parsed["chunks"] if not (c["kind"] == b"iTXt" and
                c["payload"].split(b"\x00", 1)[0] == b"XML:com.adobe.xmp")] + [parsed["trailer"]]
    parsed = parse_jpeg(data)
    return [data[s["start"]:s["end"]] for s in parsed["segments"] if not (s["marker"] == 0xE1 and
            s["payload"].startswith((STD_SIG, EXT_SIG)))] + [parsed["tail"]]


def postcheck(original: bytes, output: bytes, values: dict) -> dict:
    expected_copy, blanked = original, []
    before = Packet()
    if original[:2] == b"\xff\xd8":
        # The only permitted change outside the primary group: legacy XMP values blanked
        # in place at the same length. Every other byte must equal the input.
        expected_copy, blanked = blank_legacy(original, parse_jpeg(original))
        ranges = [(c["start"], c["end"]) for c in legacy_xmp_carriers(parse_jpeg(original))]
        diff = [i for i in range(len(original)) if original[i] != expected_copy[i]] if len(original) == len(expected_copy) else None
        if diff is None or any(not any(lo <= i < hi for lo, hi in ranges) for i in diff):
            raise Reject("postcheck", "copied_bytes_changed", "Legacy blanking changed bytes outside the legacy XMP values.")
        before = locate_jpeg_primary(parse_jpeg(expected_copy))["packet"]
    if output.startswith(PNG_SIG):
        after = locate_png_primary(parse_png(output))
        located = {"fragments": 0}
    else:
        primary = locate_jpeg_primary(parse_jpeg(output))
        if primary["standard"] is None:
            raise Reject("postcheck", "missing_primary", "Output has no StandardXMP.")
        after = primary
        located = {"fragments": len(primary["extension"]), "guid": primary["guid"]}
    if copied_ranges(expected_copy) != copied_ranges(output):
        raise Reject("postcheck", "copied_bytes_changed", "A byte range outside the primary XMP differs from the input.")
    packet = after["packet"]
    if {k: v["canon"] for k, v in before.preserved().items()} != {k: v["canon"] for k, v in packet.preserved().items()}:
        raise Reject("postcheck", "preserved_property_changed", "A non-allowlisted primary property changed.")
    expected = Packet()
    expected.add_document(strict_xml(wrap(before.about or "", list(generated(values).values()), guid=None, packet=False, padding=0),
                                     "expected"), "expected")
    for key in ALLOWED:
        if key not in packet.props or packet.props[key]["canon"] != expected.props[key]["canon"]:
            raise Reject("postcheck", "allowlisted_value_mismatch", f"Output value for {{{key[0]}}}{key[1]} is not the expected value.")
    unexpected = set(packet.props) - set(packet.preserved()) - ALLOWED - FRAMING
    if unexpected:
        raise Reject("postcheck", "unexpected_property", "Output contains properties outside the allowlist and preserved set.")
    return {"copied_ranges": len(copied_ranges(output)), "preserved_properties": len(packet.preserved()),
            "legacy_blanked": len([b for b in blanked if not b.get("already_blank")]), **located}


def inject(output: bytes, defect: str) -> bytes:
    if defect == "copied-byte":
        ranges = copied_ranges(output)
        target = ranges[0] if not output.startswith(PNG_SIG) else ranges[1]
        at = output.index(target) + len(target) - 5  # inside a copied payload, before its CRC/end
        return output[:at] + bytes([output[at] ^ 0x01]) + output[at + 1:]
    if defect == "drop-extension":
        parsed = parse_jpeg(output)
        ext = [s for s in parsed["segments"] if s["marker"] == 0xE1 and s["payload"].startswith(EXT_SIG)]
        s = ext[-1]
        return output[:s["start"]] + output[s["end"]:]
    if defect == "record-value":
        return output.replace(b"<pdfmd:SchemaVersion", b"<pdfmd:SchemaVersioN", 1).replace(
            b"</pdfmd:SchemaVersion>", b"</pdfmd:SchemaVersioN>", 1)
    if defect == "legacy-residue":
        at = output.index(BLANK_HEAD) + len(BLANK_HEAD)  # first padding byte of a blanked legacy value
        return output[:at] + b"X" + output[at + 1:]
    raise ValueError(defect)


def prepare(args) -> int:
    report: dict = {"input": str(args.input), "output": str(args.output)}
    data = Path(args.input).read_bytes()
    report["input_sha256"] = hashlib.sha256(data).hexdigest()
    values = json.loads(Path(args.values).read_text(encoding="utf-8"))
    try:
        output, info = splice(data, values)
        report["splice"] = info
        if args.inject:
            output = inject(output, args.inject)
            report["injected_defect"] = args.inject
        try:
            report["postcheck"] = postcheck(data, output, values)
        except Reject as rej:
            raise Reject("postcheck", rej.code, str(rej)) from None
    except Reject as rej:
        report.update(accepted=False, stage=rej.stage, code=rej.code, message=str(rej))
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 2
    staged = Path(str(args.output) + ".stage")
    staged.write_bytes(output)
    if staged.read_bytes() != output:
        staged.unlink()
        raise RuntimeError("Staged output differs after write.")
    os.replace(staged, args.output)
    report.update(accepted=True, output_sha256=hashlib.sha256(output).hexdigest())
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--values", required=True, type=Path)
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--inject", choices=("copied-byte", "drop-extension", "record-value", "legacy-residue"))
    sys.exit(prepare(parser.parse_args()))
