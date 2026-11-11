"""AR-Q4-C1 stage-one, read-only source-route witness.

Launch the --inside-job entry only through qualify_metadata.Runner.call.
This is not an observer, packet extractor, validator, or preparation path.
The fixed commands use only the verified copied runtime. No metadata write
method, import, assignment option, alternate config, or image mutation runs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

import qualify_metadata as q


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def box(kind, data):
    return struct.pack(">I", 8 + len(data)) + kind + data


def inside_job(run):
    run = run.resolve(strict=True)
    helper = run / "baseline/exiftool.exe"
    perl = run / "baseline/exiftool_files/perl.exe"
    lib = run / "baseline/exiftool_files/lib"
    config = run / "prior-call-reference/pdfmd.config"
    evidence = run / "closure-witness"
    evidence.mkdir(exist_ok=False)
    calls = []

    def call(name, argv):
        folder = evidence / name
        folder.mkdir()
        save(folder / "argv.json", argv)
        with (folder / "stdout.bin").open("wb") as out, (folder / "stderr.bin").open("wb") as err:
            result = subprocess.run(argv, stdout=out, stderr=err, shell=False, check=False)
        rec = {"name": name, "exit": result.returncode, "argv": argv,
               "stdout_sha256": digest((folder / "stdout.bin").read_bytes()),
               "stderr_sha256": digest((folder / "stderr.bin").read_bytes())}
        calls.append(rec)
        save(evidence / "calls.json", calls)
        return result.returncode, (folder / "stdout.bin").read_bytes()

    def read(name, path, verbose=False):
        # This vector is constructed here, never taken from a source/config value.
        options = ["-v3"] if verbose else ["-j", "-G1", "-s", "-XMP:all", "-EXIF:all", "-Warning", "-Error"]
        argv = [str(helper), "-config", str(config), "-charset", "filename=UTF8", "-charset", "UTF8", *options, "--", str(path)]
        return call(name, argv)

    packet = (run / "inputs/logical-valid.xmp").read_bytes()
    assert digest(packet) == "6075ac4bccb2516e84dd2d581c55a0d48b25e8149adb81a1046385dd03b12034"
    # Existing raw codec only. This is compression of a 256-byte known string,
    # not ExifTool WriteInfo/WriteDirectory or a native metadata writer call.
    codec = evidence / "compress_known_packet.pl"
    codec.write_text("use strict; use warnings; use IO::Compress::Brotli qw(bro);\n"
                     "binmode STDOUT; open my $f, '<:raw', $ARGV[0] or die $!;\n"
                     "local $/; my $s=<$f>; die 'fixture size' unless length($s)==256;\n"
                     "print bro($s);\n", encoding="ascii")
    code, encoded = call("raw-codec", [str(perl), "-I" + str(lib), str(codec), str(run / "inputs/logical-valid.xmp")])
    assert code == 0 and 0 < len(encoded) < 1024
    (evidence / "logical.xmp").write_bytes(packet)
    (evidence / "logical.brotli").write_bytes(encoded)
    # The existing decoder is an independent round-trip check of this tiny
    # constructed edge, not a proof of complete stream consumption in general.
    decode = evidence / "decode_known_packet.pl"
    decode.write_text("use strict; use warnings; use IO::Uncompress::Brotli qw(unbro);\n"
                      "binmode STDOUT; open my $f, '<:raw', $ARGV[0] or die $!;\n"
                      "local $/; my $s=<$f>; die 'fixture size' if length($s)>1024;\n"
                      "print unbro($s, 1024);\n", encoding="ascii")
    code, decoded = call("raw-codec-roundtrip", [str(perl), "-I" + str(lib), str(decode), str(evidence / "logical.brotli")])
    assert code == 0 and decoded == packet
    # Generator-known spans only; this builds no arbitrary-input box parser.
    jumd = box(b"jumd", bytes.fromhex("786d6c2000110010800000aa00389b71") + b"\0")
    raw_child = box(b"uuid", bytes.fromhex("be7acfcb97a942e89c71999491e3afac") + packet)
    compressed_child = box(b"brob", b"xml " + encoded)
    png = (run / "inputs/png-alpha.png").read_bytes()
    jpeg = (run / "inputs/jpeg-basic.jpg").read_bytes()
    fixtures = []
    for kind, child, physical in [("uuid-raw", raw_child, packet), ("brob", compressed_child, encoded)]:
        jumb = box(b"jumb", jumd + child)
        for container in ("png", "jpeg"):
            name = container + "-jumb-" + kind
            if container == "png":
                data = png[:33] + q.chunk(b"caBX", jumb) + png[33:]
                suffix = ".png"
            else:
                data = jpeg[:2] + q.jpeg_segment(0xEB, b"JP\0\x01" + struct.pack(">I", 1) + jumb) + jpeg[2:]
                suffix = ".jpg"
            path = evidence / (name + suffix)
            path.write_bytes(data)
            pos = data.index(physical)
            record = {"name": name, "file": str(path), "sha256": digest(data),
                      "role": "source-recognized route witness, not normative format or preparation acceptance",
                      "expected_occurrences": [{"id": name + "/jumb/child/packet-1", "parent": name + "/jumb/child",
                          "logical_sha256": digest(packet), "logical_length": len(packet),
                          "encoded_span": [pos, pos + len(physical)], "encoded_sha256": digest(physical),
                          "transform": "identity" if kind == "uuid-raw" else "Brotli; generator-known roundtrip only"}],
                      "complete_packet_coverage": False, "accepted_preparation": False}
            for verbose in (False, True):
                code, out = read(name + ("-verbose" if verbose else "-full-readback"), path, verbose)
                record["verbose" if verbose else "full_readback"] = {"exit": code,
                    "has_known_label": b"Nested exact original" in out,
                    "unknown_brotli_type": b"Unknown Brotli box type" in out}
            assert digest(path.read_bytes()) == record["sha256"]
            fixtures.append(record)
    # Verify exact copied earlier inputs without invoking a writer or relabeling
    # their old readbacks as new controls.
    frozen = json.loads((run / "frozen-identities.json").read_text())
    input_checks = {n: digest((run / "inputs" / n).read_bytes()) == info["sha256"]
                    for n, info in frozen["inputs"].items()}
    assert all(input_checks.values())
    save(evidence / "expected-inventories.json", fixtures)
    save(evidence / "copied-input-checks.json", input_checks)
    summary = {"fixtures": fixtures, "native_metadata_writer_invocations": 0, "accepted_preparations": 0,
               "source_closure": False, "complete_packet_coverage": False,
               "observer_built": False, "stage": "source closure only",
               "gap": "Jpeg2000 ProcessBrotli reads DataPt offset 0, ignoring the boxed subrange passed by ProcessJpeg2000Box; native dispatch returns before decompression/ProcessXMP.",
               "limits": "Whole child and descendants share pre-start 256 MiB Job memory / 5 seconds Job CPU / 15 seconds parent wall.",
               "completion": "Witness construction and read-only calls complete; this is not traversal/extraction completion."}
    save(evidence / "summary.json", summary)
    print(json.dumps({"fixtures": len(fixtures), "native_readbacks": 8, "raw_codec_calls": 2,
                      "source_closure": False, "native_metadata_writer_invocations": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inside-job", type=Path, required=True)
    inside_job(parser.parse_args().inside_job)
