"""Stage-one AR-Q4 evidence probe, not a validator or an accepted preparation path.

Only outer PNG/JPEG containers are inventoried. Nested carriers, encoded profiles,
extensions and opaque scan/trailer regions remain explicitly unavailable. This
probe must run through qualify_metadata.py's pre-start bounded Job worker. It
never runs a writer, repairs XML or declares complete packet coverage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import struct
import sys
import sysconfig
import xml.parsers.expat as expat
import zlib

PNG = b"\x89PNG\r\n\x1a\n"
STD = b"http://ns.adobe.com/xap/1.0/\0"
EXT = b"http://ns.adobe.com/xmp/extension/\0"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def span(data, start, end, kind):
    if not 0 <= start <= end <= len(data):
        raise ValueError("span outside source")
    return {"kind": kind, "start": start, "end": end, "length": end - start,
            "sha256": sha(data[start:end])}


def inventory(path):
    data = path.read_bytes()
    result = {"file": str(path), "size": len(data), "sha256": sha(data),
              "packets": [], "carriers": [], "gaps": [],
              "complete_packet_coverage": False, "accepted_preparation": False,
              "syntax_validation": "not run: stage-one coverage probe"}
    packets, carriers, gaps = result["packets"], result["carriers"], result["gaps"]
    try:
        if data.startswith(PNG):
            result["actual_type"] = "PNG"
            pos = 8
            while pos < len(data):
                if len(data) - pos < 12:
                    raise ValueError("truncated PNG chunk header")
                size = struct.unpack_from(">I", data, pos)[0]
                start, end = pos + 8, pos + 8 + size
                if end + 4 > len(data):
                    raise ValueError("PNG chunk length exceeds remaining bytes")
                kind = data[pos + 4:pos + 8]
                payload = data[start:end]
                if zlib.crc32(kind + payload) != struct.unpack_from(">I", data, end)[0]:
                    raise ValueError("PNG CRC mismatch")
                carriers.append(span(data, start, end, kind.decode("latin1")))
                if kind == b"iTXt" and payload.startswith(b"XML:com.adobe.xmp\0"):
                    head = start + len(b"XML:com.adobe.xmp\0")
                    if head + 2 > end:
                        raise ValueError("truncated iTXt compression fields")
                    flag, method = data[head:head + 2]
                    lang_end = data.find(b"\0", head + 2, end)
                    name_end = data.find(b"\0", lang_end + 1, end) if lang_end >= 0 else -1
                    if name_end < 0 or flag not in (0, 1) or method != 0:
                        raise ValueError("invalid iTXt fields")
                    if flag:
                        gaps.append("compressed iTXt: not decompressed in this stage-one probe")
                    else:
                        packets.append(span(data, name_end + 1, end, "PNG iTXt raw XMP"))
                elif kind in (b"tEXt", b"zTXt", b"tXMP", b"meTa"):
                    gaps.append(kind.decode() + ": legacy/text/XML extraction unqualified")
                elif kind in (b"eXIf", b"zxIf", b"zXIf", b"caBX"):
                    gaps.append(kind.decode() + ": reachable nested packet inventory unavailable")
                pos = end + 4
                if kind == b"IEND":
                    if size:
                        raise ValueError("nonempty IEND")
                    if pos != len(data):
                        gaps.append("bytes after IEND: trailer reachability unqualified")
                    break
            else:
                raise ValueError("missing IEND")
        elif data.startswith(b"\xff\xd8"):
            result["actual_type"] = "JPEG"
            pos = 2
            while pos < len(data):
                if data[pos] != 0xff:
                    raise ValueError("expected JPEG marker")
                while pos < len(data) and data[pos] == 0xff:
                    pos += 1
                if pos == len(data):
                    raise ValueError("truncated JPEG marker")
                marker = data[pos]
                pos += 1
                if marker == 0xd9:
                    if pos != len(data):
                        gaps.append("JPEG trailer reachability unqualified")
                    break
                if marker == 0xda:
                    carriers.append(span(data, pos - 2, len(data), "JPEG scan suffix (opaque)"))
                    gaps.append("JPEG scans/inter-scan markers/trailers not inventoried by this probe")
                    break
                if len(data) - pos < 2:
                    raise ValueError("truncated JPEG segment length")
                size = struct.unpack_from(">H", data, pos)[0]
                if size < 2 or pos + size > len(data):
                    raise ValueError("JPEG segment length outside source")
                start, end = pos + 2, pos + size
                payload = data[start:end]
                carriers.append(span(data, start, end, f"JPEG marker {marker:02x}"))
                if marker == 0xe1 and payload.startswith(STD):
                    packets.append(span(data, start + len(STD), end, "JPEG StandardXMP"))
                elif marker == 0xe1 and payload.startswith(EXT):
                    gaps.append("ExtendedXMP: assembly/association unqualified; fragment is not XML")
                elif marker in (0xe1, 0xed, 0xeb):
                    gaps.append(f"JPEG marker {marker:02x}: nested/nonstandard packet inventory unavailable")
                pos = end
        else:
            result["actual_type"] = "other"
            gaps.append("actual input type outside PNG/JPEG probe")
        result["outer_packet_status"] = "located" if packets else "absent in inspected outer forms only"
        result["coverage_status"] = "unavailable" if gaps else "outer inventory only; reachability not certified"
        if len(packets) > 1:
            result["coverage_status"] = "ambiguous"
            gaps.append("multiple outer packets: semantics not resolved")
    except (ValueError, struct.error) as error:
        result.update(coverage_status="malformed-container", diagnostic=str(error))
    return result


def identity():
    # Record the installed candidate, without claiming any validation settings or tests.
    parser = expat.ParserCreate()
    pyd = Path(sys.modules["pyexpat"].__file__)
    return {"python": sys.version, "executable": sys.executable,
            "base_executable": sys._base_executable, "platform": platform.platform(),
            "python_build": platform.python_build(), "compiler": platform.python_compiler(),
            "config": {n: sysconfig.get_config_var(n) for n in ("Py_DEBUG", "WITH_PYMALLOC", "SOABI")},
            "expat_version": expat.EXPAT_VERSION, "expat_version_info": expat.version_info,
            "expat_features": expat.features, "pyexpat_module": str(pyd),
            "pyexpat_sha256": sha(pyd.read_bytes()),
            "identity_probe_settings": {"ParserCreate": {"encoding": None, "namespace_separator": None},
                 "buffer_text": parser.buffer_text, "ordered_attributes": parser.ordered_attributes,
                 "specified_attributes": parser.specified_attributes,
                 "ExternalEntityRefHandler": parser.ExternalEntityRefHandler,
                 "StartDoctypeDeclHandler": parser.StartDoctypeDeclHandler,
                 "reparse_deferral": parser.GetReparseDeferralEnabled() if hasattr(parser, "GetReparseDeferralEnabled") else "API unavailable"},
            "qualification_validation_settings": None,
            "validation_stage": "not reached: packet coverage first"}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--inputs", type=Path)
    cli.add_argument("--identity", action="store_true")
    args = cli.parse_args()
    if args.identity:
        output = identity()
    else:
        inputs = json.loads(args.inputs.read_text(encoding="utf-8"))
        output = {"stage": 1, "disposition": "inconclusive: outer-only inventory",
                  "writer_invocations": 0, "cases": [inventory(Path(n)) for n in inputs]}
    print(json.dumps(output, ensure_ascii=True, indent=2))
