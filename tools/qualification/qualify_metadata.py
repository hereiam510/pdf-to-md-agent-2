"""Bounded, offline Windows qualification. This never edits an application task.

Run with the repository's pinned PyMuPDF environment; pass exact acquired tools.
All results, originals, preparation failures and full process logs are retained.
The worker's Windows Job bounds descendants before starting the native helper.
"""
from __future__ import annotations

import argparse
import csv
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import zlib

NS = "urn:pdfmd:asset-provenance:1"
DC = "http://purl.org/dc/elements/1.1/"
CONFIG = r"""%Image::ExifTool::UserDefined = (
 'Image::ExifTool::XMP::Main' => { pdfmd => {
  SubDirectory => { TagTable => 'Image::ExifTool::UserDefined::pdfmd' } } });
%Image::ExifTool::UserDefined::pdfmd = (
 GROUPS => { 0 => 'XMP', 1 => 'XMP-pdfmd', 2 => 'Other' },
 NAMESPACE => { pdfmd => 'urn:pdfmd:asset-provenance:1' },
 WRITABLE => 'string',
 SchemaVersion => { Writable => 'integer' }, OccurrenceId => {},
 RepresentationId => {}, RecordJSON => {} );
1;
"""
ALLOW = ["XMP-pdfmd:SchemaVersion", "XMP-pdfmd:OccurrenceId",
         "XMP-pdfmd:RepresentationId", "XMP-pdfmd:RecordJSON",
         "XMP-dc:Title-x-default", "XMP-dc:Title-zh-CN",
         "XMP-dc:Description-x-default", "XMP-dc:Description-zh-CN", "XMP-dc:Source"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def record_json(value):
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    # JSON retains exact strings while the enclosing XML remains XML 1.0.
    return text.replace("\ufffe", r"\ufffe").replace("\uffff", r"\uffff")


def chunk(kind, payload):
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))


def png_chunks(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a PNG")
    out, pos = [], 8
    while pos < len(data):
        size = struct.unpack_from(">I", data, pos)[0]
        kind, payload = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + size]
        crc = struct.unpack_from(">I", data, pos + 8 + size)[0]
        if crc != zlib.crc32(kind + payload):
            raise ValueError("PNG CRC mismatch")
        out.append((kind, payload))
        pos += 12 + size
    if out[-1][0] != b"IEND":
        raise ValueError("Missing IEND")
    return out


def png(extra=(), depth=8, color=6):
    # Generated exact encoded samples: alpha, 16-bit gray and palette variants.
    if color == 6:
        row = b"\x00" + bytes([13, 90, 211, 0, 201, 5, 77, 128, 1, 2, 3, 255])
    elif color == 0:
        row = b"\x00\x00\x00\x12\x34\xff\xff"
    else:
        row = b"\x00\x00\x01\x02"
    chunks = [(b"IHDR", struct.pack(">IIBBBBB", 3, 2, depth, color, 0, 0, 0))]
    if color == 3:
        chunks += [(b"PLTE", b"\xff\x00\x00\x00\xff\x00\x00\x00\xff"), (b"tRNS", b"\x00\x80\xff")]
    chunks += [(b"gAMA", struct.pack(">I", 45455)), (b"tEXt", b"Comment\x00Keep this useful text")]
    chunks += list(extra) + [(b"IDAT", zlib.compress(row * 2)), (b"IEND", b"")]
    return b"\x89PNG\r\n\x1a\n" + b"".join(chunk(k, v) for k, v in chunks)


def xmp(body):
    return ("<x:xmpmeta xmlns:x='adobe:ns:meta/'><rdf:RDF "
            "xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>"
            "<rdf:Description rdf:about='' xmlns:xmp='http://ns.adobe.com/xap/1.0/'>"
            + body + "</rdf:Description></rdf:RDF></x:xmpmeta>").encode()


def with_xmp(data, packet):
    if data.startswith(b"\x89PNG"):
        items = png_chunks(data)
        items.insert(1, (b"iTXt", b"XML:com.adobe.xmp\x00\x00\x00\x00\x00" + packet))
        return data[:8] + b"".join(chunk(k, p) for k, p in items)
    return data[:2] + jpeg_segment(0xE1, b"http://ns.adobe.com/xap/1.0/\x00" + packet) + data[2:]


def jpeg_segment(marker, payload):
    return b"\xff" + bytes([marker]) + struct.pack(">H", len(payload) + 2) + payload


def jpeg_parts(data):
    if data[:2] != b"\xff\xd8":
        raise ValueError("Not a JPEG")
    parts, pos = [], 2
    while pos < len(data):
        start = pos
        if data[pos] != 255:
            raise ValueError("Invalid marker")
        while data[pos] == 255:
            pos += 1
        marker = data[pos]
        pos += 1
        if marker == 0xDA:
            parts.append((marker, data[start:]))  # Complete scan through EOI.
            return parts
        size = struct.unpack_from(">H", data, pos)[0]
        parts.append((marker, data[pos + 2:pos + size]))
        pos += size
    raise ValueError("Missing scan")


def payload_identity(data):
    if data.startswith(b"\x89PNG"):
        items = [(k.decode(), sha(p)) for k, p in png_chunks(data)
                 if not (k == b"iTXt" and p.startswith(b"XML:com.adobe.xmp\x00"))]
    else:
        items = [(hex(k), sha(p)) for k, p in jpeg_parts(data)
                 if not (k == 0xE1 and p.startswith((b"http://ns.adobe.com/xap/1.0/\x00",
                                                          b"http://ns.adobe.com/xmp/extension/\x00")))]
    # Permit container reordering, but compare every non-XMP payload including EXIF/profile.
    return sorted(items)


def decode_identity(data):
    import pymupdf
    p = pymupdf.Pixmap(data)
    return {"width": p.width, "height": p.height, "n": p.n, "alpha": p.alpha,
            "colorspace": p.colorspace.name, "samples_sha256": sha(p.samples)}


def exif(spp=None):
    # Minimal real little-endian TIFF with orientation=6, artist, original filename.
    entries = [(0x112, 3, 1, 6), (0x13B, 2, 7, b"Artist\x00"),
               (0xC68B, 2, len(b"../outside/source.jpg\x00"), b"../outside/source.jpg\x00")]
    if spp is not None:
        entries += [(0x100, 4, 1, 1), (0x101, 4, 1, 1), (0x103, 3, 1, 1),
                    (0x111, 4, 1, 0), (0x115, 4, 1, spp), (0x117, 4, 1, 1)]
    entries.sort()
    offset, packed, tail = 8 + 2 + len(entries) * 12 + 4, [], b""
    for tag, fmt, count, value in entries:
        if isinstance(value, bytes):
            slot = struct.pack("<I", offset + len(tail)); tail += value
        else:
            slot = struct.pack("<H", value) + b"\x00\x00" if fmt == 3 else struct.pack("<I", value)
        packed.append(struct.pack("<HHI", tag, fmt, count) + slot)
    return b"II*\x00\x08\x00\x00\x00" + struct.pack("<H", len(entries)) + b"".join(packed) + b"\x00" * 4 + tail


def job_worker(command, result_path):
    # Limits cover this Python worker and descendants, before writer launch.
    class BASIC(C.Structure):
        _fields_ = [("ProcessTime", C.c_longlong), ("JobTime", C.c_longlong),
                    ("Flags", W.DWORD), ("Min", C.c_size_t), ("Max", C.c_size_t),
                    ("Active", W.DWORD), ("Affinity", C.c_size_t),
                    ("Priority", W.DWORD), ("Scheduling", W.DWORD)]
    class IO(C.Structure):
        _fields_ = [(n, C.c_ulonglong) for n in ("ReadOp", "WriteOp", "OtherOp", "Read", "Write", "Other")]
    class EXT(C.Structure):
        _fields_ = [("Basic", BASIC), ("IO", IO), ("ProcessMemory", C.c_size_t),
                    ("JobMemory", C.c_size_t), ("PeakProcess", C.c_size_t), ("PeakJob", C.c_size_t)]
    k = C.WinDLL("kernel32", use_last_error=True)
    k.CreateJobObjectW.restype = W.HANDLE
    k.CreateJobObjectW.argtypes = [C.c_void_p, W.LPCWSTR]
    k.SetInformationJobObject.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD]
    k.AssignProcessToJobObject.argtypes = [W.HANDLE, W.HANDLE]
    k.GetCurrentProcess.restype = W.HANDLE
    k.QueryInformationJobObject.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.c_void_p]
    handle, limits = k.CreateJobObjectW(None, None), EXT()
    limits.Basic.Flags = 0x2000 | 0x200 | 0x4  # kill on close, job memory, job CPU time
    limits.Basic.JobTime = 5 * 10_000_000
    limits.JobMemory = 256 * 1024 * 1024
    if not handle or not k.SetInformationJobObject(handle, 9, C.byref(limits), C.sizeof(limits)):
        raise C.WinError(C.get_last_error())
    if not k.AssignProcessToJobObject(handle, k.GetCurrentProcess()):
        raise C.WinError(C.get_last_error())
    env = os.environ.copy()
    for name in ("LC_ALL", "LC_CTYPE", "LANG"):
        env.pop(name, None)  # Process-only locale; bundled Windows Perl cannot use C.UTF-8.
    started = time.monotonic()
    code = subprocess.call(command, env=env, shell=False)
    if not k.QueryInformationJobObject(handle, 9, C.byref(limits), C.sizeof(limits), None):
        raise C.WinError(C.get_last_error())
    dump(Path(result_path), {"exit": code, "seconds": time.monotonic() - started,
                             "peak_job_bytes": limits.PeakJob, "memory_limit_bytes": limits.JobMemory,
                             "job_cpu_limit_seconds": 5})
    # Do not close a KILL_ON_JOB_CLOSE job containing our own process before logs flush.


class Runner:
    def __init__(self, root, writer, reader):
        self.root, self.writer, self.reader = root, writer, reader
        self.calls = []
        self.config = root / "pdfmd.config"
        self.config.write_text(CONFIG, encoding="utf-8")

    def call(self, name, command, cwd=None):
        folder = self.root / "calls" / name
        folder.mkdir(parents=True)
        result = folder / "process.json"
        dump(folder / "argv.json", command)
        with (folder / "stdout.bin").open("wb") as out, (folder / "stderr.bin").open("wb") as err:
            try:
                proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker",
                                       str(result), *command], cwd=cwd, stdout=out, stderr=err,
                                      timeout=15, shell=False)
                status = json.loads(result.read_text()) if result.exists() else {"worker_exit": proc.returncode}
            except subprocess.TimeoutExpired:
                status = {"timeout": True}
        status.update(name=name, argv=command)
        self.calls.append(status)
        return status, (folder / "stdout.bin").read_bytes(), (folder / "stderr.bin").read_bytes()

    def writer_call(self, name, args):
        return self.call(name, [str(self.writer), "-config", str(self.config),
                                "-charset", "filename=UTF8", "-charset", "UTF8", *args])

    def read(self, name, path):
        status, out, err = self.call(name, [str(self.reader), str(path)], cwd=path.parent)
        return status, json.loads(out) if status.get("exit") == 0 else [], err


def make_record(data, basename, long=False):
    basis = [{"ref": "synthetic:qualification", "physical_page": 2, "region": None,
              "note": "Synthetic facts for transport qualification, not a real citation"}]
    def fact(text=None, state="known"):
        return {"state": state if text is None else "known", "value": text,
                "basis": basis if text is not None or state == "none" else [], "alternatives": []}
    text = "图像原文\r\n第二行\r第三行\n控制\x00\x01\ufffe % $(literal) <tag> & e\u0301"
    description = {"full": text + ("完整中文说明。" * 14000 if long else ""),
                   "filename": "测试图像", "language": "zh-CN", "punctuation": "fullwidth", "basis": basis}
    locations = [{"physical_page": p, "region": None, "basis": basis,
                  "printed": {"state": "known" if p == 2 else "unknown",
                              "value": "3-12" if p == 2 else None, "basis": basis,
                              "alternatives": [], "legacy_hint": None}} for p in (2, 5)]
    return {"schema_version": 1, "occurrence_id": "1" * 32, "representation_id": "2" * 32,
            "source": {"source_ref": "synthetic:source", "source_sha256": "a" * 64,
                       "media_type": "application/pdf", "kind": "document", "title": fact("完整中文题名"),
                       "container_title": fact(state="unknown"), "publication_date": fact(state="unknown"),
                       "publisher": fact(state="none"), "full_citation": fact("Synthetic complete citation — 中文"),
                       "creators": [], "identifiers": []}, "locations": locations,
            "image": {"image_ref": "synthetic:image", "sha256": sha(data),
                      "media_type": "image/png" if data.startswith(b"\x89PNG") else "image/jpeg",
                      "derivation": {"kind": "synthetic", "coordinate_frame": "unrotated",
                                     "transform": [1, 0, 0, 1, 0, 0]}, "originals": []},
            "description": description, "caption": fact(text), "image_title": fact(state="unknown"),
            "figure": fact("图 2"), "naming": {"policy": "readable-180-v1",
                "comparison_policy": "nfc-fullfold-u17-v1", "assigned_basename": basename,
                "locator_groups": [{"kind": "single", "pages": [p], "basis": basis} for p in (2, 5)],
                "collision_suffix": None}}


def run(args):
    import pymupdf
    root = args.run.resolve()
    root.mkdir(parents=True, exist_ok=False)
    runner = Runner(root, args.writer.resolve(), args.reader.resolve())
    rgb = pymupdf.Pixmap(pymupdf.csRGB, 3, 2, bytes([10, 80, 210] * 6), False).tobytes("jpeg")
    valid = xmp("<xmp:Label><![CDATA[alpha <tag>]]><![CDATA[ beta & tail]]></xmp:Label>"
                "<xmp:Nickname>Keep<!-- </xmp:Nickname> --> this</xmp:Nickname>")
    simple = xmp("<xmp:Label>Keep this exact value</xmp:Label>")
    def box(kind, value):
        return struct.pack(">I", len(value) + 8) + kind + value
    # Matches the upstream #453 regression structure (not a signed C2PA claim).
    jumd = box(b"jumd", b"c2pa\x00\x11\x00\x10\x80\x00\x00\xaa\x00\x38\x9b\x71\x03c2pa\x00")
    cabx = (b"caBX", box(b"jumb", jumd))
    fixtures = [("png-alpha", png()), ("png-16", png(depth=16, color=0)),
                ("png-palette", png(color=3)), ("jpeg-basic", rgb),
                ("png-valid-complex-xmp", with_xmp(png(), valid)),
                ("jpeg-valid-complex-xmp", with_xmp(rgb, valid)),
                ("png-simple-xmp", with_xmp(png(), simple)),
                ("jpeg-extended", with_xmp(rgb, simple)),
                ("png-exif-percent", png([(b"eXIf", exif())])),
                ("jpeg-exif-percent", rgb[:2] + jpeg_segment(0xE1, b"Exif\x00\x00" + exif()) + rgb[2:])]
    fixtures += [("png-cabx-before-exif", png([cabx, (b"eXIf", exif())])),
                 ("png-exif-before-cabx", png([(b"eXIf", exif()), cabx]))]
    fixtures.append(("png-unrelated-dc", with_xmp(png(), xmp(
        "<dc:subject xmlns:dc='http://purl.org/dc/elements/1.1/'><rdf:Bag>"
        "<rdf:li>Unrelated subject</rdf:li><rdf:li>中文主题</rdf:li></rdf:Bag></dc:subject>"
        "<dc:creator xmlns:dc='http://purl.org/dc/elements/1.1/'><rdf:Seq>"
        "<rdf:li>Actual image creator</rdf:li></rdf:Seq></dc:creator>"))))
    for label, body in (("multiple-cdata", "<xmp:Label><![CDATA[first]]><![CDATA[second]]></xmp:Label>"),
                        ("taglike-cdata", "<xmp:Label><![CDATA[before </xmp:Label> after]]></xmp:Label>"),
                        ("taglike-comment", "<xmp:Label>before<!-- </xmp:Label> --> after</xmp:Label>")):
        for ext, data in (("png", png()), ("jpeg", rgb)):
            fixtures.append((ext + "-valid-" + label, with_xmp(data, xmp(body))))
    # Reuse all seven canonical PDF image fixtures through existing extraction code.
    # This is an isolated synthetic store, never the original A03 workspace.
    from pdfmd.storage import Store
    from pdfmd.evidence import Evidence
    evidence = Evidence(Store(root / "synthetic-store"))
    for source in sorted((Path(__file__).resolve().parents[2] / "tests/fixtures/pdf").glob("*.pdf")):
        job = evidence.create_job(str(source), "Offline metadata qualification only")["id"]
        with pymupdf.open(source) as pdf:
            image = evidence.extract_image(job, 1, pdf[0].get_images()[0][0])
            raw = pdf.extract_image(pdf[0].get_images()[0][0])
        extracted = evidence.store.bytes(image["ref"], job)
        fixtures.append(("existing-" + source.stem, extracted))
        if source.stem in ("cmyk-jpeg", "rgb-jpeg") and raw["ext"] == "jpeg":
            fixtures.append(("raw-" + source.stem, raw["image"]))
        if source.stem == "jpx":
            profile = next(zlib.decompress(p.split(b"\x00", 1)[1][1:])
                           for k, p in png_chunks(extracted) if k == b"iCCP")
            fixtures.append(("jpeg-icc", rgb[:2] + jpeg_segment(0xE2, b"ICC_PROFILE\x00\x01\x01" + profile) + rgb[2:]))
        dump(root / ("extraction-" + source.stem + ".json"), image)
    for kind, packet in (("cdata", xmp("<xmp:Label><![CDATA[unterminated")),
                         ("comment", xmp("<xmp:Label><!-- unterminated")),
                         ("utf8", simple.replace(b"Keep this exact value", b"\xc0\x80\xf5\x80\x80\x80"))):
        for ext, data in (("png", png()), ("jpeg", rgb)):
            fixtures.append((f"{ext}-malformed-{kind}", with_xmp(data, packet)))
    # Modest malformed EXIF counts under a pre-start Job. No huge allocation fixture.
    for ext, data in (("png", png([(b"eXIf", exif(4096))])),
                      ("jpeg", rgb[:2] + jpeg_segment(0xE1, b"Exif\x00\x00" + exif(4096)) + rgb[2:])):
        fixtures.append((ext + "-exif-count", data))
    # An actual TIFF with misleading extension tests content validation, not parser isolation by suffix.
    fixtures.append(("mismatched-type", exif()))
    cases = []
    for name, data in fixtures:
        if args.case and name not in args.case:
            continue
        folder = root / "cases" / name
        folder.mkdir(parents=True)
        ext = ".png" if data.startswith(b"\x89PNG") or name == "mismatched-type" else ".jpg"
        original, prepared = folder / ("original" + ext), folder / ("a19f" + ext)
        original.write_bytes(data)
        shutil.copyfile(original, prepared)
        result = {"name": name, "original_sha256": sha(data)}
        malformed = "malformed" in name or "exif-count" in name
        if name == "mismatched-type":
            try:
                payload_identity(data)
                result["type_rejected"] = False
            except ValueError:
                result["type_rejected"] = True
            cases.append(result)
            continue
        try:
            bstatus, before, _ = runner.read(name + "-before", original)
            result["independent_before_exit"] = bstatus.get("exit")
            # Exercise actual UTF-8 JSON conversion and observe EXIF despite the
            # outer extension. Full output is private evidence, never a model input.
            runner.writer_call(name + "-before-full-readback", [
                "-j", "-G1", "-s", "-XMP:all", "-EXIF:all", "-Warning", "-Error", "--", str(original)])
            expected = make_record(data, "中文% p3-12&i5 图像" + ext, name == "jpeg-extended")
            serialized = record_json(expected)
            title = "测试图像"
            description = ("Derived image description (JSON-escaped): " + json.dumps(expected["description"]["full"], ensure_ascii=True)
                           + "\nSource title: 完整中文题名\nCitation: Synthetic complete citation — 中文"
                             "\nPublisher: none; container/date: unknown\nPhysical: 2; printed: 3-12; figure: 图 2"
                             "\nPhysical: 5; printed: unknown; figure: 图 2")
            tags = {"XMP-pdfmd:SchemaVersion": 1, "XMP-pdfmd:OccurrenceId": "1" * 32,
                    "XMP-pdfmd:RepresentationId": "2" * 32, "XMP-pdfmd:RecordJSON": serialized,
                    "XMP-dc:Title-x-default": title, "XMP-dc:Title-zh-CN": title,
                    "XMP-dc:Description-x-default": description, "XMP-dc:Description-zh-CN": description,
                    "XMP-dc:Source": "urn:sha256:" + "a" * 64}
            dump(folder / "expected-record.json", expected)
            dump(folder / "input.json", [{"SourceFile": str(prepared), **tags}])
            # The pinned JSON importer double-decodes literal \\uXXXX sequences.
            # CSV is another documented structured transport and preserves them.
            with (folder / "input.csv").open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["SourceFile", *ALLOW])
                writer.writeheader()
                writer.writerow({"SourceFile": str(prepared), **tags})
            status, stdout, stderr = runner.writer_call(name + "-write", [
                "-overwrite_original", "-XMP-dc:Title=", "-XMP-dc:Description=",
                "-" + args.transport + "=" + str(folder / ("input." + args.transport)),
                *["-" + tag for tag in ALLOW], "--", str(prepared)])
            result["writer"] = status
            # Preserve complete diagnostics, reject warnings/errors independently of exit status.
            result["diagnostic_rejection"] = status.get("exit") != 0 or b"warning" in stderr.lower() or b"error" in stderr.lower()
            result["encoded_non_xmp_equal"] = payload_identity(data) == payload_identity(prepared.read_bytes())
            result["decoded_equal"] = decode_identity(data) == decode_identity(prepared.read_bytes())
            result["original_unchanged"] = original.read_bytes() == data
            result["prepared_sha256"] = sha(prepared.read_bytes())
            rstatus, readback, rerr = runner.writer_call(name + "-readback", [
                "-j", "-G1", "-s", "-XMP:all", "-EXIF:all", "-Warning", "-Error", "--", str(prepared)])
            try:
                readback = json.loads(readback)[0]
                result["writer_record_equal"] = json.loads(readback["XMP-pdfmd:RecordJSON"]) == expected
                result["readback_diagnostic_rejection"] = (rstatus.get("exit") != 0 or bool(rerr)
                    or any(key.split(":")[-1] in ("Warning", "Error") for key in readback))
            except (ValueError, KeyError):
                result["writer_record_equal"] = False
                result["readback_diagnostic_rejection"] = True
            # Empty standalone location: copied+renamed image; reader receives no expected file/config.
            alone = root / "standalone" / name
            alone.mkdir(parents=True)
            copied = alone / ("中文% independently renamed" + ext)
            shutil.copyfile(prepared, copied)
            astatus, after, _ = runner.read(name + "-standalone", copied)
            props = {p["path"]: p["value"] for p in after}
            try:
                result["independent_record_equal"] = json.loads(props.get("pdfmd:RecordJSON", "null")) == expected
            except ValueError as error:
                result["independent_record_equal"] = False
                result["independent_record_error"] = str(error)
            result["independent_standard_equal"] = all(props.get(p) == v for p, v in (
                ("dc:title[1]", title), ("dc:title[2]", title),
                ("dc:description[1]", description), ("dc:description[2]", description),
                ("dc:source", "urn:sha256:" + "a" * 64), ("pdfmd:SchemaVersion", "1"),
                ("pdfmd:OccurrenceId", "1" * 32), ("pdfmd:RepresentationId", "2" * 32)))
            def is_replaced(prop):
                return prop["namespace"] == NS or (prop["namespace"] == DC and
                    prop["path"].split("[", 1)[0].split("/", 1)[0] in ("dc:title", "dc:description", "dc:source"))
            unrelated = [p for p in before if not is_replaced(p)]
            result["unrelated_before"] = unrelated
            result["unrelated_after"] = [p for p in after if not is_replaced(p)]
            result["unrelated_preserved"] = all(p in after for p in unrelated)
            result["standalone_only_image"] = list(alone.iterdir()) == [copied]
            result["standalone_hash_equal"] = copied.read_bytes() == prepared.read_bytes()
            result["no_metadata_directed_output"] = (prepared.name == "a19f" + ext
                and not (root / "cases/outside").exists() and not (root / "outside").exists())
            result["expected_record_utf8_bytes"] = len(serialized.encode())
            result["malformed_control"] = malformed
            if not malformed:
                result["qualified_case"] = all(result[k] for k in (
                    "encoded_non_xmp_equal", "decoded_equal", "original_unchanged", "writer_record_equal",
                    "independent_record_equal", "independent_standard_equal", "unrelated_preserved",
                    "standalone_only_image", "standalone_hash_equal")) and not result["diagnostic_rejection"] and not result["readback_diagnostic_rejection"]
        except Exception as error:
            result["harness_error"] = repr(error)
        dump(folder / "result.json", result)
        cases.append(result)
        dump(root / "report.json", {"cases": cases, "calls": runner.calls, "decoder": pymupdf.VersionBind})
    # Deliberately strip XMP in a new copy; this is a limitation control, not an accepted deliverable.
    enriched = root / "cases/png-alpha/a19f.png"
    leaves = None
    if enriched.exists():
        stripped = root / "stripped.png"
        stripped.write_bytes(enriched.read_bytes()[:8] + b"".join(chunk(k, p) for k, p in png_chunks(enriched.read_bytes())
            if not (k == b"iTXt" and p.startswith(b"XML:com.adobe.xmp\x00"))))
        _, leaves, _ = runner.read("stripped-limitation", stripped)
    extended = root / "cases/jpeg-extended/a19f.jpg"
    extended_control = None
    if extended.exists():
        parts = jpeg_parts(extended.read_bytes())
        header = b"http://ns.adobe.com/xmp/extension/\x00"
        ext = [p for k, p in parts if k == 0xE1 and p.startswith(header)]
        packets = sorted((struct.unpack_from(">I", p, len(header) + 36)[0], p[len(header) + 40:]) for p in ext)
        payload = b"".join(p for _, p in packets)
        negative = root / "missing-extended.jpg"
        negative.write_bytes(b"\xff\xd8" + b"".join(
            p if k == 0xDA else jpeg_segment(k, p) for k, p in parts
            if not (k == 0xE1 and p.startswith(header))))
        nstatus, nprops, _ = runner.read("missing-extended-negative", negative)
        extended_control = {"extension_segments": len(ext), "extension_bytes": len(payload),
            "guid_md5_equal": bool(ext) and all(p[len(header):len(header) + 32].decode().lower()
                == hashlib.md5(payload).hexdigest() for p in ext),
            "missing_extended_reader_exit": nstatus.get("exit"),
            "missing_extended_record_absent": not any(p["namespace"] == NS and p["path"] == "pdfmd:RecordJSON" for p in nprops)}
    dump(root / "report.json", {"cases": cases, "calls": runner.calls,
        "decoder": pymupdf.VersionBind, "transport": args.transport,
        "stripping_loses_record": None if leaves is None else not any(p["namespace"] == NS for p in leaves),
        "extended_control": extended_control,
        "writer_sha256": sha(args.writer.read_bytes()), "reader_sha256": sha(args.reader.read_bytes()),
        "harness_sha256": sha(Path(__file__).read_bytes())})
    print(json.dumps([{k: c.get(k) for k in ("name", "qualified_case", "diagnostic_rejection",
                                           "unrelated_preserved", "harness_error")} for c in cases], indent=2))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        job_worker(sys.argv[3:], sys.argv[2])
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--writer", required=True, type=Path)
        parser.add_argument("--reader", required=True, type=Path)
        parser.add_argument("--run", required=True, type=Path, help="New, exclusive ignored directory")
        parser.add_argument("--case", action="append", help="Select named controls for a focused rerun")
        parser.add_argument("--transport", choices=("csv", "json"), default="csv",
                            help="JSON is retained to reproduce the rejected import path")
        run(parser.parse_args())
