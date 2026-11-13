"""T1-F06 bounded qualification of the primary-XMP-only candidate. Offline, no provider.

Every preparation and every reader call runs under the existing pre-start Windows
Job (256 MiB job memory, five seconds job CPU, 15-second parent wall) from
qualify_metadata.Runner. Checks here are written independently of the candidate's
own postcheck: container order/bytes via qualify_metadata parsers, decoded pixels
via PyMuPDF and standalone values via the pinned production ExifTool 13.55.

  qualify_primary_xmp.py --reader EXIFTOOL_13_55 [--cross-reader EXIFTOOL_13_61] --run NEW_DIR
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qualify_metadata import (Runner, chunk, decode_identity, dump, exif, jpeg_parts, jpeg_segment, make_record,  # noqa: E402
                              payload_identity, png, png_chunks, record_json, sha, with_xmp, xmp)

CANDIDATE = Path(__file__).resolve().parent / "primary_xmp.py"
STD_SIG = b"http://ns.adobe.com/xap/1.0/\x00"
EXT_SIG = b"http://ns.adobe.com/xmp/extension/\x00"
NSDECL = ("xmlns:xmp='http://ns.adobe.com/xap/1.0/' xmlns:dc='http://purl.org/dc/elements/1.1/' "
          "xmlns:my='urn:example:custom:1' xmlns:xmpGImg='http://ns.adobe.com/xap/1.0/g/img/' "
          "xmlns:pdfmd='urn:pdfmd:asset-provenance:1'")
ALLOWED_TAGS = {"XMP-pdfmd:SchemaVersion", "XMP-pdfmd:OccurrenceId", "XMP-pdfmd:RepresentationId", "XMP-pdfmd:RecordJSON",
                "XMP-dc:Title", "XMP-dc:Title-zh-CN", "XMP-dc:Description", "XMP-dc:Description-zh-CN", "XMP-dc:Source",
                "XMP-xmpNote:HasExtendedXMP"}


def packet(body: str, *, extra_ns: str = "", about: str = "", second: str = "", note: str | None = None, wrapper=True) -> bytes:
    attrs = f" xmlns:xmpNote='http://ns.adobe.com/xmp/note/' xmpNote:HasExtendedXMP='{note}'" if note else ""
    xml = (f"<x:xmpmeta xmlns:x='adobe:ns:meta/'><rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>"
           f"<rdf:Description rdf:about='{about}' {NSDECL} {extra_ns}{attrs}>{body}</rdf:Description>{second}"
           "</rdf:RDF></x:xmpmeta>")
    if wrapper:
        xml = "<?xpacket begin='\ufeff' id='W5M0MpCehiHzreSzNTczkc9d'?>" + xml + "<?xpacket end='w'?>"
    return xml.encode("utf-8")


def insert_after_soi(jpeg: bytes, *segments: bytes) -> bytes:
    return jpeg[:2] + b"".join(segments) + jpeg[2:]


def std_segment(xml: bytes) -> bytes:
    return jpeg_segment(0xE1, STD_SIG + xml)


def extension_segments(ext: bytes, guid: str, size: int, order=None, mutate=None) -> list[bytes]:
    frags = [[len(ext), off, ext[off:off + size]] for off in range(0, len(ext), size)]
    if mutate:
        frags = mutate(frags)
    if order:
        frags = [frags[i] for i in order(len(frags))]
    return [jpeg_segment(0xE1, EXT_SIG + guid.encode() + struct.pack(">II", full, off) + data) for full, off, data in frags]


def thumbnail_body(jpeg: bytes) -> str:
    return ("<xmp:Thumbnails><rdf:Alt><rdf:li rdf:parseType='Resource'><xmpGImg:format>JPEG</xmpGImg:format>"
            "<xmpGImg:width>3</xmpGImg:width><xmpGImg:height>2</xmpGImg:height>"
            f"<xmpGImg:image>{base64.b64encode(jpeg).decode()}</xmpGImg:image></rdf:li></rdf:Alt></xmp:Thumbnails>")


def irb(resource: int, data: bytes) -> bytes:
    return b"8BIM" + struct.pack(">H", resource) + b"\x00\x00" + struct.pack(">I", len(data)) + data + (b"\x00" if len(data) % 2 else b"")


def box(kind: bytes, value: bytes) -> bytes:
    return struct.pack(">I", len(value) + 8) + kind + value


def exif_with_xmp(xml: bytes, order: str = "II", kind: int = 1) -> bytes:
    """TIFF with one IFD0 entry: XMP tag 0x02BC (BYTE by default) whose value starts at offset 26."""
    e = "<" if order == "II" else ">"
    head = b"II*\x00" if order == "II" else b"MM\x00*"
    return head + struct.pack(e + "I", 8) + struct.pack(e + "H", 1) + struct.pack(e + "HHII", 0x2BC, kind, len(xml), 26) + b"\x00" * 4 + xml


MARKERS = ("STALE", "LEGACY-ONLY")


def legacy_packet(label: str) -> bytes:
    return packet(f"<dc:title><rdf:Alt><rdf:li xml:lang='x-default'>STALE {label} title</rdf:li></rdf:Alt></dc:title>"
                  f"<my:Legacy>LEGACY-ONLY {label} value</my:Legacy>"
                  "<pdfmd:RecordJSON>{\"stale\":\"nested\"}</pdfmd:RecordJSON>")


def legacy_blank_ok(data: bytes, out: bytes, packets: list[bytes]) -> bool:
    """Independent B-lite check: only the known legacy packet bytes changed, at the same
    length, into an empty XMP packet carrying none of the legacy values."""
    before, after = ordered_non_xmp(data), ordered_non_xmp(out)
    if [k for k, _ in before] != [k for k, _ in after]:
        return False
    changed = 0
    for (_, x), (_, y) in zip(before, after):
        if x == y:
            continue
        hit = next((p for p in packets if p in x), None)
        if hit is None or len(x) != len(y):
            return False
        at = x.index(hit)
        span = y[at:at + len(hit)]
        if x[:at] != y[:at] or x[at + len(hit):] != y[at + len(hit):]:
            return False
        text = span.decode("utf-8")
        body = text.split("?>", 1)[1].rsplit("<?xpacket", 1)[0].strip()
        if any(m in text for m in MARKERS) or body != ("<x:xmpmeta xmlns:x=\"adobe:ns:meta/\"><rdf:RDF xmlns:rdf="
                                                        "\"http://www.w3.org/1999/02/22-rdf-syntax-ns#\"></rdf:RDF></x:xmpmeta>"):
            return False
        changed += 1
    return changed == len(packets)


def unbinary(value):
    # With -b, ExifTool emits values it treats as binary (here: very long text) as base64.
    # Truly binary values (ICC data, thumbnail images) are compared by digest.
    if isinstance(value, str) and value.startswith("base64:"):
        raw = base64.b64decode(value[7:])
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return {"binary_sha256": sha(raw), "bytes": len(raw)}
    return value


def values_for(data: bytes, ext: str, long: bool = False) -> tuple[dict, dict]:
    expected = make_record(data, "中文% p3-12&i5 图像" + ext, long)
    title = "测试图像"
    description = ("Derived image description (JSON-escaped): " + json.dumps(expected["description"]["full"], ensure_ascii=True)
                   + "\nSource title: 完整中文题名\nCitation: Synthetic complete citation — 中文"
                   "\nPublisher: none; container/date: unknown\nPhysical: 2; printed: 3-12; figure: 图 2"
                   "\nPhysical: 5; printed: unknown; figure: 图 2")
    return expected, {"title": {"x-default": title, "zh-CN": title},
                      "description": {"x-default": description, "zh-CN": description},
                      "source": "urn:sha256:" + "a" * 64,
                      "pdfmd": {"SchemaVersion": 1, "OccurrenceId": "1" * 32, "RepresentationId": "2" * 32,
                                "RecordJSON": record_json(expected)}}


def ordered_non_xmp(data: bytes) -> list:
    if data.startswith(b"\x89PNG"):
        return [(k, p) for k, p in png_chunks(data) if not (k == b"iTXt" and p.startswith(b"XML:com.adobe.xmp\x00"))]
    return [(k, p) for k, p in jpeg_parts(data) if not (k == 0xE1 and p.startswith((STD_SIG, EXT_SIG)))]


def fixtures(root: Path) -> list[dict]:
    import pymupdf
    from pdfmd.evidence import Evidence
    from pdfmd.storage import Store
    evidence = Evidence(Store(root / "synthetic-store"))
    pdfs = Path(__file__).resolve().parents[2] / "tests/fixtures/pdf"
    produced = {}
    for name in ("rgb-smask", "cmyk-raw-smask", "jpx", "rgb-jpeg"):
        job = evidence.create_job(str(pdfs / f"{name}.pdf"), "Offline primary-XMP qualification only")["id"]
        with pymupdf.open(pdfs / f"{name}.pdf") as pdf:
            xref = pdf[0].get_images()[0][0]
        image = evidence.extract_image(job, 1, xref)
        produced[name] = (evidence.store.bytes(image["ref"], job), image)
        if name == "rgb-smask":
            render = evidence.render_page(job, 1, 72)
            produced["render"] = (evidence.store.bytes(render["ref"], job), render)
    dct, meta = produced["rgb-jpeg"]
    assert meta["representation"] == "embedded_stream" and meta["original_bytes_equal"], meta["representation"]
    render = produced["render"][0]
    thumb = pymupdf.Pixmap(pymupdf.csRGB, 3, 2, bytes([10, 80, 210] * 6), False).tobytes("jpeg")
    icc = next(__import__("zlib").decompress(p.split(b"\x00", 1)[1][1:]) for k, p in png_chunks(produced["jpx"][0]) if k == b"iCCP")
    complex_body = ("<dc:title><rdf:Alt><rdf:li xml:lang='x-default'>Old XMP title</rdf:li></rdf:Alt></dc:title>"
                    "<dc:rights><rdf:Alt><rdf:li xml:lang='x-default'>Rights text</rdf:li><rdf:li xml:lang='zh-CN'>版权文本</rdf:li></rdf:Alt></dc:rights>"
                    "<dc:subject><rdf:Bag><rdf:li>beta</rdf:li><rdf:li>alpha 中文</rdf:li></rdf:Bag></dc:subject>"
                    "<dc:creator><rdf:Seq><rdf:li>Second author</rdf:li><rdf:li>First author</rdf:li></rdf:Seq></dc:creator>"
                    "<my:Note><![CDATA[alpha <tag> & ]]><!-- </my:Note> --> tail</my:Note>"
                    "<my:Struct rdf:parseType='Resource'><my:Field xml:lang='en'>value</my:Field></my:Struct>"
                    "<pdfmd:RecordJSON>{\"stale\":true}</pdfmd:RecordJSON>" + thumbnail_body(thumb))
    second = ("<rdf:Description rdf:about='' xmlns:photoshop='http://ns.adobe.com/photoshop/1.0/' "
              "photoshop:Headline='Second description &amp; attribute form'/>")
    complex_xmp = packet(complex_body, extra_ns="xmp:CreatorTool='Legacy tool &amp; co'", second=second)
    cases = [
        {"name": "png-render", "data": render, "expect": "accept", "producer": "render_page"},
        {"name": "png-decoded-smask", "data": produced["rgb-smask"][0], "expect": "accept", "producer": "extract_image decoded"},
        {"name": "png-decoded-cmyk", "data": produced["cmyk-raw-smask"][0], "expect": "accept", "producer": "extract_image decoded"},
        {"name": "png-decoded-icc", "data": produced["jpx"][0], "expect": "accept", "producer": "extract_image decoded (iCCP)"},
        {"name": "png-unexpected-xmp", "data": with_xmp(render, xmp("<xmp:Label>old</xmp:Label>")), "expect": "png_unexpected_xmp"},
        {"name": "png-unexpected-cabx", "data": png([(b"caBX", box(b"jumb", b"x" * 16))]), "expect": "png_unexpected_carrier"},
        {"name": "png-wrong-type", "data": exif(), "ext": ".png", "expect": "unsupported_type"},
        {"name": "jpeg-dct-create", "data": dct, "expect": "accept", "producer": "extract_image embedded_stream"},
        {"name": "jpeg-existing-merge", "data": insert_after_soi(dct, std_segment(complex_xmp)), "expect": "accept",
         # ExifTool misreads the input comment; the data-model value is known by construction.
         "reader_input_misparse": {"XMP-my:Note": "alpha <tag> &  tail"}},
        {"name": "jpeg-ar-sdk-01-iptc", "data": insert_after_soi(dct, std_segment(packet(
            "<dc:title><rdf:Alt><rdf:li xml:lang='x-default'>Different XMP title</rdf:li></rdf:Alt></dc:title>")),
            jpeg_segment(0xED, b"Photoshop 3.0\x00" + irb(0x0404, b"\x1c\x02\x05" + struct.pack(">H", 17) + b"Legacy IPTC title"))),
         "expect": "accept"},
        {"name": "jpeg-ar-sdk-02-thumb-long", "data": insert_after_soi(dct, std_segment(packet(thumbnail_body(thumb)))),
         "expect": "accept", "long": True},
        {"name": "jpeg-long-create", "data": dct, "expect": "accept", "long": True},
        {"name": "jpeg-exif-icc", "data": insert_after_soi(dct, jpeg_segment(0xE1, b"Exif\x00\x00" + exif()),
            jpeg_segment(0xE2, b"ICC_PROFILE\x00\x01\x01" + icc)), "expect": "accept"},
        {"name": "jpeg-app11-brob", "data": insert_after_soi(dct, jpeg_segment(0xEB, b"JP\x00\x01\x00\x00\x00\x01" + box(b"jumb",
            box(b"jumd", bytes(range(16)) + b"\x03xmp-witness\x00") + box(b"brob", b"xml " + bytes(range(200)))))),
         "expect": "accept"},
        # B-lite (2026-11-10): legacy XMP values are blanked in place at the same length.
        {"name": "jpeg-stale-nested", "data": insert_after_soi(dct, jpeg_segment(0xED, b"Photoshop 3.0\x00" + irb(
            0x0404, b"\x1c\x02\x05" + struct.pack(">H", 17) + b"Legacy IPTC title") + irb(0x0424, legacy_packet("APP13")))),
         "expect": "accept", "legacy": [legacy_packet("APP13")]},
        {"name": "jpeg-exif-0x02bc-xmp", "data": insert_after_soi(dct, jpeg_segment(0xE1, b"Exif\x00\x00" + exif_with_xmp(
            legacy_packet("EXIF-II")))), "expect": "accept", "legacy": [legacy_packet("EXIF-II")]},
        {"name": "jpeg-legacy-exif-mm", "data": insert_after_soi(dct, jpeg_segment(0xE1, b"Exif\x00\x00" + exif_with_xmp(
            legacy_packet("EXIF-MM"), order="MM", kind=7))), "expect": "accept", "legacy": [legacy_packet("EXIF-MM")]},
        {"name": "jpeg-legacy-both-with-primary", "data": insert_after_soi(dct,
            jpeg_segment(0xE1, b"Exif\x00\x00" + exif_with_xmp(legacy_packet("EXIF-II"))),
            std_segment(packet("<my:Small>kept</my:Small><dc:title><rdf:Alt><rdf:li xml:lang='x-default'>Old primary</rdf:li></rdf:Alt></dc:title>")),
            jpeg_segment(0xED, b"Photoshop 3.0\x00" + irb(0x0424, legacy_packet("APP13")))),
         "expect": "accept", "legacy": [legacy_packet("EXIF-II"), legacy_packet("APP13")]},
        {"name": "jpeg-legacy-too-short", "data": insert_after_soi(dct, jpeg_segment(0xED, b"Photoshop 3.0\x00" + irb(
            0x0424, b"<x:xmpmeta xmlns:x='adobe:ns:meta/'/>"))), "expect": "legacy_xmp_too_short"},
        {"name": "jpeg-legacy-malformed", "data": insert_after_soi(dct, jpeg_segment(0xED, b"Photoshop 3.0\x00" + irb(
            0x0424, b"<x:xmpmeta xmlns:x='adobe:ns:meta/'><rdf:RDF" + b" " * 300))), "expect": "legacy_malformed"},
        {"name": "jpeg-legacy-split-app13", "data": insert_after_soi(dct, jpeg_segment(0xED, b"Photoshop 3.0\x00" + b"8BIM"
            + struct.pack(">H", 0x0424) + b"\x00\x00" + struct.pack(">I", len(legacy_packet("APP13")) + 500) + legacy_packet("APP13"))),
         "expect": "legacy_unparseable"},
        {"name": "jpeg-legacy-exif-wrong-type", "data": insert_after_soi(dct, jpeg_segment(0xE1, b"Exif\x00\x00" + exif_with_xmp(
            legacy_packet("EXIF-II"), kind=3))), "expect": "legacy_unparseable"},
        {"name": "jpeg-mpf", "data": insert_after_soi(dct, jpeg_segment(0xE2, b"MPF\x00II*\x00\x08\x00\x00\x00\x00\x00")), "expect": "mpf_unsupported"},
        {"name": "jpeg-competing-primary", "data": insert_after_soi(dct, std_segment(packet("")), std_segment(packet(""))), "expect": "competing_primary"},
        {"name": "jpeg-malformed-unclosed", "data": insert_after_soi(dct, std_segment(b"<x:xmpmeta xmlns:x='adobe:ns:meta/'><rdf:RDF")), "expect": "malformed_xml"},
        {"name": "jpeg-malformed-utf8", "data": insert_after_soi(dct, std_segment(packet("<my:Note>X</my:Note>").replace(b">X<", b">\xc0\x80<"))), "expect": "invalid_utf8"},
        {"name": "jpeg-dtd-external-entity", "data": insert_after_soi(dct, std_segment(
            b"<!DOCTYPE x [<!ENTITY e SYSTEM 'file:///C:/Windows/win.ini'>]><x:xmpmeta xmlns:x='adobe:ns:meta/'>&e;</x:xmpmeta>")), "expect": "dtd_forbidden"},
    ]
    # Existing ExtendedXMP, reordered fragments, and its negative controls.
    big = "<my:Big>" + "大字" * 15000 + "</my:Big>"
    ext = packet(big, wrapper=False)
    guid = hashlib.md5(ext).hexdigest().upper()
    std = std_segment(packet("<my:Small>kept</my:Small>", note=guid))
    reverse = lambda n: list(reversed(range(n)))  # noqa: E731
    def with_ext(segs, standard=std):
        return insert_after_soi(dct, standard, *segs)
    cases += [
        {"name": "jpeg-existing-extended-reordered", "data": with_ext(extension_segments(ext, guid, 40000, order=reverse)),
         "expect": "accept"},
        {"name": "jpeg-extended-missing-fragment", "data": with_ext(extension_segments(ext, guid, 40000)[::2]), "expect": "gap"},
        {"name": "jpeg-extended-overlap", "data": with_ext(extension_segments(ext, guid, 40000,
            mutate=lambda f: [f[0], [f[1][0], f[1][1] - 10, f[0][2][-10:] + f[1][2]], *f[2:]])), "expect": "overlap"},
        {"name": "jpeg-extended-truncated-length", "data": with_ext(extension_segments(ext, guid, 40000,
            mutate=lambda f: [[full + 7, off, data] for full, off, data in f])), "expect": "incomplete"},
        {"name": "jpeg-extended-digest-mismatch", "data": with_ext(extension_segments(ext, guid, 40000,
            mutate=lambda f: [f[0], [f[1][0], f[1][1], f[1][2][:5] + b"X" + f[1][2][6:]], *f[2:]])), "expect": "digest_mismatch"},
        {"name": "jpeg-extended-orphan", "data": with_ext(extension_segments(ext, guid, 40000),
            standard=std_segment(packet("<my:Small>kept</my:Small>"))), "expect": "orphan_extension"},
        {"name": "jpeg-extended-guid-mismatch", "data": with_ext(extension_segments(ext, guid, 40000),
            standard=std_segment(packet("<my:Small>kept</my:Small>", note="F" * 32))), "expect": "guid_mismatch"},
        {"name": "inject-png-copied-byte", "data": render, "expect": "copied_bytes_changed", "inject": "copied-byte"},
        {"name": "inject-jpeg-drop-extension", "data": dct, "expect": "incomplete", "inject": "drop-extension", "long": True},
        {"name": "inject-jpeg-record-value", "data": dct, "expect": "allowlisted_value_mismatch", "inject": "record-value"},
        {"name": "inject-jpeg-legacy-residue", "data": insert_after_soi(dct, jpeg_segment(0xED, b"Photoshop 3.0\x00" + irb(
            0x0424, legacy_packet("APP13")))), "expect": "legacy_xmp_competes", "inject": "legacy-residue"},
    ]
    return cases


def read(runner, reader, name, path, all_dups=False):
    # Windows command lines cannot carry the UTF-8 Chinese filename to ExifTool's
    # Perl argv, so the fixed read vector and the absolute path travel in a UTF-8
    # -@ argument file kept beside the call log (never in the standalone folder).
    options = ["-charset", "filename=UTF8", "-j", "-b", "-G1", "-s", "-XMP:all", "-IPTC:all",
               "-EXIF:all", "-ICC_Profile:all", "-Warning", "-Error"]
    if all_dups:
        options[4:5] = ["-a", "-G1:3"]
    argfile = runner.root / "argfiles" / (name + ".args")
    argfile.parent.mkdir(exist_ok=True)
    argfile.write_text("\n".join([*options, "--", str(path)]) + "\n", encoding="utf-8")
    status, out, err = runner.call(name, [str(reader), "-config", "", "-@", str(argfile)], cwd=path.parent)
    try:
        return status, {k: unbinary(v) for k, v in json.loads(out.decode("utf-8"))[0].items()}, err
    except (ValueError, IndexError):
        return status, None, err


def run(args):
    root = args.run.resolve()
    root.mkdir(parents=True, exist_ok=False)
    # Verified copies of the reader distributions; retained evidence roots stay untouched.
    source = args.reader.resolve()
    shutil.copytree(source.parent, root / "reader-13.55")
    reader = root / "reader-13.55" / source.name
    if sha(reader.read_bytes()) != sha(source.read_bytes()):
        raise SystemExit("Reader copy differs from its source.")
    if args.cross_reader:
        cross = args.cross_reader.resolve()
        shutil.copytree(cross.parent, root / "reader-13.61")
        args.cross_reader = root / "reader-13.61" / cross.name
    runner = Runner(root, reader, reader)
    (root / "pdfmd.config").unlink()  # the candidate path and the reader use no ExifTool config
    report = {"candidate_sha256": sha(CANDIDATE.read_bytes()), "harness_sha256": sha(Path(__file__).read_bytes()),
              "reader": str(reader), "reader_sha256": sha(reader.read_bytes()), "python": sys.version, "cases": []}
    if args.cross_reader:
        report["cross_reader_sha256"] = sha(args.cross_reader.resolve().read_bytes())
    import pymupdf
    from xml.parsers import expat
    report["decoder"] = {"pymupdf": pymupdf.VersionBind, "mupdf": pymupdf.VersionFitz}
    report["expat"] = expat.EXPAT_VERSION
    for case in fixtures(root):
        name, data = case["name"], case["data"]
        folder = root / "cases" / name
        folder.mkdir(parents=True)
        ext = case.get("ext") or (".png" if data.startswith(b"\x89PNG") else ".jpg")
        original, prepared = folder / ("original" + ext), folder / ("a19f" + ext)
        original.write_bytes(data)
        expected, values = values_for(data, ext, case.get("long", False))
        dump(folder / "values.json", values)
        dump(folder / "expected-record.json", expected)
        result = {"name": name, "expect": case["expect"], "producer": case.get("producer"), "original_sha256": sha(data)}
        command = [sys.executable, "-B", str(CANDIDATE), "prepare", "--input", str(original), "--output", str(prepared),
                   "--values", str(folder / "values.json"), "--report", str(folder / "candidate-report.json")]
        if case.get("inject"):
            command += ["--inject", case["inject"]]
        status, _, _ = runner.call(name + "-prepare", command)
        result["prepare_process"] = status
        candidate = json.loads((folder / "candidate-report.json").read_text("utf-8")) if (folder / "candidate-report.json").exists() else None
        result["candidate"] = candidate
        result["output_exists"] = prepared.exists()
        result["stage_left"] = any(folder.glob("*.stage"))
        if case["expect"] != "accept":
            # Injected output defects must be caught by the postcheck; the exact code
            # depends on which check sees the damage first. Input controls name their code.
            code_ok = (candidate.get("stage") == "postcheck" if case.get("inject") and candidate
                       else bool(candidate) and candidate.get("code") == case["expect"])
            result["passed"] = bool(status.get("exit") == 2 and candidate and not candidate.get("accepted")
                                    and code_ok and not prepared.exists() and not result["stage_left"]
                                    and original.read_bytes() == data)
            report["cases"].append(result)
            dump(folder / "result.json", result)
            continue
        out = prepared.read_bytes() if prepared.exists() else b""
        checks = {"accepted": status.get("exit") == 0 and bool(candidate and candidate.get("accepted")) and prepared.exists()}
        if checks["accepted"]:
            checks["original_unchanged"] = original.read_bytes() == data
            if case.get("legacy"):
                # The one permitted change outside the primary group (B-lite).
                checks["legacy_blanked_only"] = legacy_blank_ok(data, out, case["legacy"])
            else:
                checks["non_xmp_ordered_bytes_equal"] = ordered_non_xmp(data) == ordered_non_xmp(out)
                checks["non_xmp_payload_identity_equal"] = payload_identity(data) == payload_identity(out)
            checks["decoded_equal"] = decode_identity(data) == decode_identity(out)
            if not data.startswith(b"\x89PNG"):
                parts = [p for k, p in jpeg_parts(out) if k == 0xE1 and p.startswith(EXT_SIG)]
                result["extension_fragments"] = len(parts)
                if case.get("long"):
                    pieces = [p[len(EXT_SIG) + 40:] for p in sorted(parts, key=lambda p: struct.unpack_from(">I", p, len(EXT_SIG) + 36)[0])]
                    def clean(b):
                        try:
                            b.decode("utf-8"); return True
                        except UnicodeDecodeError:
                            return False
                    checks["multiple_fragments"] = len(parts) > 1
                    result["utf8_split_across_fragments"] = any(not clean(p) for p in pieces)
            alone = root / "standalone" / name
            alone.mkdir(parents=True)
            copied = alone / ("中文% independently renamed" + ext)
            shutil.copyfile(prepared, copied)
            _, before, _ = read(runner, reader, name + "-read-before", original)
            rstatus, after, rerr = read(runner, reader, name + "-read-standalone", copied)
            _, dups, _ = read(runner, reader, name + "-read-all-documents", copied, all_dups=True)
            dump(folder / "reader-after.json", after)
            dump(folder / "reader-all-documents.json", dups)
            checks["standalone_only_image"] = list(alone.iterdir()) == [copied]
            # A diagnostic already present when reading the untouched input (e.g. an
            # unknown opaque box) is inherited; any new warning/error fails.
            def diagnostics(values):
                return {k: v for k, v in (values or {}).items() if k.endswith(("Warning", "Error"))}
            result["reader_inherited_diagnostics"] = diagnostics(before)
            misparse = case.get("reader_input_misparse", {})
            checks["reader_exit_ok"] = (rstatus.get("exit") == 0 and after is not None and (
                diagnostics(after) == diagnostics(before) or (misparse and not diagnostics(after))))
            after = after or {}
            try:
                checks["record_json_equal"] = json.loads(after.get("XMP-pdfmd:RecordJSON", "null")) == expected
            except ValueError:
                checks["record_json_equal"] = False
            v = values
            checks["standard_fields_equal"] = all(str(after.get(k)) == str(e) for k, e in (
                ("XMP-dc:Title", v["title"]["x-default"]), ("XMP-dc:Title-zh-CN", v["title"]["zh-CN"]),
                ("XMP-dc:Description", v["description"]["x-default"]), ("XMP-dc:Description-zh-CN", v["description"]["zh-CN"]),
                ("XMP-dc:Source", v["source"]), ("XMP-pdfmd:SchemaVersion", 1),
                ("XMP-pdfmd:OccurrenceId", "1" * 32), ("XMP-pdfmd:RepresentationId", "2" * 32)))
            unrelated_before = {k: val for k, val in (before or {}).items() if k not in ALLOWED_TAGS and k != "SourceFile"}
            unrelated_after = {k: val for k, val in after.items() if k not in ALLOWED_TAGS and k != "SourceFile"}
            result["unrelated_before"], result["unrelated_after"] = unrelated_before, unrelated_after
            if misparse:
                # Input misread by the reader: require the construction value instead of its broken reading.
                checks["reader_misparse_values_correct"] = all(unrelated_after.get(k) == v for k, v in misparse.items())
                for k in [*misparse, *diagnostics(before)]:
                    unrelated_before.pop(k, None); unrelated_after.pop(k, None)
            if case.get("legacy"):
                # Values read from the legacy packet are discarded by design; no reader
                # document of the delivered image may still carry them.
                checks["no_legacy_value_in_any_document"] = not any(m in json.dumps(x, ensure_ascii=False)
                                                                    for x in (after, dups) for m in MARKERS)
                legacy_keys = [k for k, val in unrelated_before.items() if any(m in str(val) for m in MARKERS)]
                result["legacy_discarded_reader_keys"] = legacy_keys
                for k in legacy_keys:
                    unrelated_before.pop(k, None); unrelated_after.pop(k, None)
            checks["unrelated_reader_values_preserved"] = unrelated_before == unrelated_after
            if args.cross_reader:
                _, cross, _ = read(runner, args.cross_reader.resolve(), name + "-cross-read-13.61", copied)
                result["cross_reader_record_equal"] = bool(cross) and cross.get("XMP-pdfmd:RecordJSON") == after.get("XMP-pdfmd:RecordJSON")
            checks["no_write_outside_case"] = not (root / "outside").exists() and not (root.parent / "outside").exists()
        result["checks"] = checks
        result["passed"] = all(checks.values())
        report["cases"].append(result)
        dump(folder / "result.json", result)
    # Resource-limit control: exhausting the Job's memory must fail, never pass.
    status, _, _ = runner.call("resource-limit-control", [sys.executable, "-c", "x = bytearray(400 * 1024 * 1024)"])
    report["resource_limit_control"] = {"status": status, "failed_as_required": status.get("exit") not in (0, None) or bool(status.get("timeout"))}
    report["calls"] = runner.calls
    report["summary"] = {"cases": len(report["cases"]), "passed": sum(1 for c in report["cases"] if c["passed"]),
                         "failed": [c["name"] for c in report["cases"] if not c["passed"]]}
    dump(root / "report.json", report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reader", required=True, type=Path, help="Pinned production ExifTool 13.55 executable")
    parser.add_argument("--cross-reader", type=Path, help="Optional supplementary reader (e.g. 13.61); not an acceptance input")
    parser.add_argument("--run", required=True, type=Path, help="New, exclusive ignored directory")
    run(parser.parse_args())
