"""T3b writer budget measurement (AR-T3B-08). Offline, no provider, Windows.

Measures the bounded XMP worker (peak Job memory, charged user/kernel CPU, wall
time) against encoded input size, and the engine process's whole-save peak
commit, with a generous measurement ceiling so the shape is visible:

* seeded-noise MuPDF PNGs (worst case for PNG size) of roughly 10, 50 and 100 MiB;
* an unchanged DCT JPEG carrying a valid existing primary record whose
  ExtendedXMP is ~15 MiB of many small nodes (DOM-heavy, near the 16 MiB bound);
* one complete edit_document save of the ~100 MiB PNG, run in a fresh child
  process so its peak commit belongs to that save.

  measure_writer_budget.py --run NEW_DIR
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from hashlib import md5, sha256
import json
from pathlib import Path
import random
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CEILING = 4 * 1024 ** 3
VALUES = {"title": {"x-default": "t"}, "description": {"x-default": "d"}, "source": "urn:sha256:" + "a" * 64,
          "pdfmd": {"SchemaVersion": 1, "OccurrenceId": "1" * 32, "RepresentationId": "2" * 32, "RecordJSON": "{}"}}


def noise_png(side: int) -> bytes:
    import pymupdf
    return pymupdf.Pixmap(pymupdf.csRGB, side, side, random.Random(side).randbytes(side * side * 3), False).tobytes("png")


def heavy_xmp_jpeg() -> bytes:
    import pymupdf
    with pymupdf.open(ROOT / "tests/fixtures/pdf/rgb-jpeg.pdf") as pdf:
        jpeg = pdf.extract_image(pdf[0].get_images()[0][0])["image"]
    ns = ("xmlns:x='adobe:ns:meta/' ", "xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' ",
          "xmlns:my='urn:example:custom:1' ")
    items = "<rdf:li>v</rdf:li>" * 830_000  # ~15 MiB of tiny nodes
    ext = (f"<x:xmpmeta {ns[0]}><rdf:RDF {ns[1]}><rdf:Description rdf:about='' {ns[2]}>"
           f"<my:Big><rdf:Bag>{items}</rdf:Bag></my:Big></rdf:Description></rdf:RDF></x:xmpmeta>").encode()
    guid = md5(ext).hexdigest().upper()
    std = (f"<x:xmpmeta {ns[0]}><rdf:RDF {ns[1]}><rdf:Description rdf:about='' {ns[2]}"
           f"xmlns:xmpNote='http://ns.adobe.com/xmp/note/' xmpNote:HasExtendedXMP='{guid}'>"
           "<my:Small>kept</my:Small></rdf:Description></rdf:RDF></x:xmpmeta>").encode()

    def seg(payload):
        return b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload
    segments = [seg(b"http://ns.adobe.com/xap/1.0/\x00" + std)]
    for offset in range(0, len(ext), 65400):
        segments.append(seg(b"http://ns.adobe.com/xmp/extension/\x00" + guid.encode() +
                            struct.pack(">II", len(ext), offset) + ext[offset:offset + 65400]))
    return jpeg[:2] + b"".join(segments) + jpeg[2:]


def worker_case(name: str, data: bytes, folder: Path) -> dict:
    from pdfmd import xmp_worker
    xmp_worker.POOL = xmp_worker.WriterPool(2 * CEILING, 1)  # measurement: one worker, not throttled by host RAM
    stats: dict = {}
    try:
        out = xmp_worker.enrich_bounded(data, VALUES, folder / name, memory_bytes=CEILING, cpu_seconds=120,
                                        wall_seconds=300, stats=stats)
        outcome = {"accepted": True, "output_bytes": len(out)}
    except xmp_worker.WorkerFailure as exc:
        outcome = {"accepted": False, "code": exc.details["code"]}
    acc = stats.get("accounting", {})
    return {"case": name, "input_bytes": len(data), "input_mib": round(len(data) / 2 ** 20, 1),
            "input_sha256": sha256(data).hexdigest(), **outcome,
            "peak_job_mib": round(acc.get("peak_job_bytes", 0) / 2 ** 20, 1),
            "user_cpu_s": round(acc.get("user_cpu_seconds", 0), 2), "kernel_cpu_s": round(acc.get("kernel_cpu_seconds", 0), 2),
            "wall_s": stats.get("elapsed_seconds")}


PREPARE = r'''
import json, random, sys
from pathlib import Path
import pymupdf
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher
root, side = Path(sys.argv[1]), int(sys.argv[2])
pix = pymupdf.Pixmap(pymupdf.csRGB, side, side, random.Random(side).randbytes(side * side * 3), False)
with pymupdf.open() as pdf:
    page = pdf.new_page(width=side * 72 / 144, height=side * 72 / 144)
    page.insert_image(page.rect, pixmap=pix)
    pdf.save(root / "noise.pdf")
d = Dispatcher(Store(root / "workspace"))
job = d.evidence.create_job(str(root / "noise.pdf"), "Budget measurement")["id"]
render = d.evidence.render_page(job, 1, 144)
print(json.dumps({"job": job, "ref": render["ref"]}))
'''

SAVE = r'''
import ctypes, json, sys
from ctypes import wintypes
from pathlib import Path
from pdfmd import xmp_worker
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher
root, job, ref, ceiling = Path(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4])
seen = {}
real = xmp_worker.prepare_object  # the save path's file-based entry
def measured(*a, **k):
    k.update(stats=seen, memory_bytes=ceiling)
    return real(*a, **k)
xmp_worker.prepare_object = measured
xmp_worker.POOL = xmp_worker.WriterPool(2 * ceiling, 1)
d = Dispatcher(Store(root / "workspace"))
ev = [{"ref": ref, "physical_page": 1, "region": None, "note": "n"}]
result = d.execute(job, "budget", "edit_document", json.dumps({"base_version": None, "expected_head": None,
    "page_updates": {"1": {"disposition": "included"}}, "replace_blocks": [{"id": "b", "pages": [1], "markdown": "![x](asset:new/x)"}],
    "asset_changes": [{"kind": "create", "client_key": "x", "facts": {"image_ref": ref,
        "description": {"full": "f", "filename": "Budget", "language": "en", "punctuation": "ascii", "basis": []},
        "locations": [{"physical_page": 1, "region": None, "basis": ev}]}}]}))
class PMC(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [(n, ctypes.c_size_t) for n in (
        "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage",
        "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
pmc = PMC(); pmc.cb = ctypes.sizeof(PMC)
k = ctypes.windll.kernel32; k.GetCurrentProcess.restype = ctypes.c_void_p
ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), wintypes.DWORD]
ctypes.windll.psapi.GetProcessMemoryInfo(k.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
print(json.dumps({"ok": result["ok"], "error": result["data"].get("error"), "image_bytes": d.store.get("blob", ref, job=job)["bytes"],
                  "engine_peak_commit_mib": round(pmc.PeakPagefileUsage / 2**20, 1),
                  "engine_peak_working_set_mib": round(pmc.PeakWorkingSetSize / 2**20, 1),
                  "worker_peak_job_mib": round(seen.get("accounting", {}).get("peak_job_bytes", 0) / 2**20, 1),
                  "worker_elapsed_s": seen.get("elapsed_seconds")}))
'''


def main(args):
    run = args.run.resolve()
    run.mkdir(parents=True, exist_ok=False)
    report = {"ceiling_bytes": CEILING, "cases": []}
    for side in (2000, 4300, 6000):
        report["cases"].append(worker_case(f"png-{side}", noise_png(side), run / "worker"))
        print(json.dumps(report["cases"][-1]))
    report["cases"].append(worker_case("jpeg-heavy-xmp", heavy_xmp_jpeg(), run / "worker"))
    print(json.dumps(report["cases"][-1]))
    (run / "save").mkdir()
    # Fixture creation and the page render run in one process; a fresh process then
    # performs only the save, so its peak commit belongs to the save.
    made = json.loads(subprocess.run([sys.executable, "-B", "-c", PREPARE, str(run / "save"), "6000"],
                                     capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1])
    save = subprocess.run([sys.executable, "-B", "-c", SAVE, str(run / "save"), made["job"], made["ref"], str(CEILING)],
                          capture_output=True, text=True)
    report["whole_save"] = json.loads(save.stdout.strip().splitlines()[-1]) if save.returncode == 0 else {"stderr": save.stderr[-2000:]}
    print(json.dumps(report["whole_save"])[:600])
    (run / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", required=True, type=Path)
    main(parser.parse_args())
