"""T3b integrated standalone readback check. Offline, no provider.

Saves an enriched schema 2 version through the normal edit_document path
(MuPDF render PNG + unchanged PDF DCT JPEG, one long record), exports the ZIP,
extracts it elsewhere, copies each delivered image alone under a new name into
an empty folder and reads it with the independent production ExifTool 13.55
(13.61 optional cross-reader) under the qualification Job limits.

  check_enriched_readback.py --reader EXIFTOOL_13_55 [--cross-reader EXIFTOOL_13_61] --run NEW_DIR
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qualify_metadata import Runner, dump, sha  # noqa: E402
from qualify_primary_xmp import read  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def main(args):
    import pymupdf
    from pdfmd.storage import Store
    from pdfmd.tools import Dispatcher

    run = args.run.resolve()
    run.mkdir(parents=True, exist_ok=False)
    shutil.copytree(args.reader.resolve().parent, run / "reader-13.55")
    reader = run / "reader-13.55" / args.reader.name
    cross = None
    if args.cross_reader:
        shutil.copytree(args.cross_reader.resolve().parent, run / "reader-13.61")
        cross = run / "reader-13.61" / args.cross_reader.name
    runner = Runner(run, reader, reader)
    (run / "pdfmd.config").unlink()
    d = Dispatcher(Store(run / "workspace"))
    pdf = ROOT / "tests/fixtures/pdf/rgb-jpeg.pdf"
    job = d.evidence.create_job(str(pdf), "Integrated T3b readback check")["id"]
    with pymupdf.open(pdf) as document:
        xref = document[0].get_images()[0][0]
    jpeg = d.evidence.extract_image(job, 1, xref)
    png = d.evidence.render_page(job, 1, 72)

    def ev(ref, note):
        return [{"ref": ref, "physical_page": 1, "region": None, "note": note}]

    def known(value, ref, note):
        return {"state": "known", "value": value, "basis": ev(ref, note), "alternatives": []}

    long_full = "完整中文描述，含換行\r\n與 & < > 符號。" + "長描述" * 9000
    occurrences = {
        "fig": {"image_ref": jpeg["ref"], "description": {"full": long_full, "filename": "新聞基本屬性: 比較", "language": "zh-Hant",
                                                          "punctuation": "fullwidth", "basis": ev(jpeg["ref"], "figure content")},
                "caption": known("圖4–2　新聞的基本屬性", png["ref"], "caption under the figure"),
                "figure": known("圖4–2", png["ref"], "figure label"),
                "locations": [{"physical_page": 1, "region": None, "basis": ev(png["ref"], "figure on page")}]},
        "page": {"image_ref": png["ref"], "description": {"full": "Whole page view.", "filename": "Page view", "language": "en",
                                                          "punctuation": "ascii", "basis": ev(png["ref"], "render")},
                 "figure": {"state": "none", "value": None, "basis": ev(png["ref"], "no figure label"), "alternatives": []},
                 "locations": [{"physical_page": 1, "region": None, "basis": ev(png["ref"], "whole page")}]},
    }
    edit = {"base_version": None, "expected_head": None,
            "replace_blocks": [{"id": "b", "pages": [1], "markdown": "![圖4–2](asset:new/fig)\n\n[Open page 1](asset:new/page)"}],
            "page_updates": {"1": {"printed": "58", "printed_basis": ev(png["ref"], "printed 58 at foot"), "disposition": "included"}},
            "source_update": {"kind": "book", "title": known("完整中文題名：新聞學", png["ref"], "title page"),
                              "full_citation": known("Synthetic citation — 中文, p. 58", png["ref"], "imprint")},
            "asset_changes": [{"kind": "create", "client_key": k, "facts": f} for k, f in occurrences.items()]}
    result = d.execute(job, "t3b-readback", "edit_document", json.dumps(edit, ensure_ascii=False))
    if not result["ok"]:
        raise SystemExit(json.dumps(result["data"], ensure_ascii=False))
    version = result["data"]["version_id"]
    saved = d.documents.version(job, version)
    exported = d.documents.export(job, version, str(run / "export" / "t3b.zip"))
    with zipfile.ZipFile(exported["path"]) as archive:
        archive.extractall(run / "relocated")
    report = {"version": version, "export_sha256": sha(Path(exported["path"]).read_bytes()),
              "reference_check": d.documents.reference_check(job, version), "images": []}
    for change in result["data"]["asset_changes"]:
        path = change["asset_path"]
        record = saved["assets"][path]["provenance"]
        relocated = run / "relocated" / path
        alone = run / "standalone" / change["client_key"]
        alone.mkdir(parents=True)
        copy = alone / ("独立 renamed copy" + Path(path).suffix)
        shutil.copyfile(relocated, copy)
        status, values, _ = read(runner, reader, change["client_key"] + "-read", copy)
        all_status, all_docs, _ = read(runner, reader, change["client_key"] + "-read-all", copy, all_dups=True)
        values = values or {}
        title = record["image_title"]["value"] if record["image_title"]["state"] == "known" else record["description"]["filename"]
        checks = {
            "reader_exit_ok": status.get("exit") == 0 and not any(k.endswith(("Warning", "Error")) for k in values),
            "record_json_equal": json.loads(values.get("XMP-pdfmd:RecordJSON", "null")) == record,
            "title_equal": values.get("XMP-dc:Title") == title,
            "source_equal": values.get("XMP-dc:Source") == "urn:sha256:" + saved["source_facts"]["source_sha256"],
            "occurrence_equal": values.get("XMP-pdfmd:OccurrenceId") == change["occurrence_id"],
            "relocated_bytes_equal": relocated.read_bytes() == (d.documents.root / version / path).read_bytes(),
            "standalone_only_image": list(alone.iterdir()) == [copy],
            # -a -G1:3 names each document (Main, Doc1...); exactly one record, in Main.
            "single_record_document": all_status.get("exit") == 0 and
                [k for k in (all_docs or {}) if k.endswith(":RecordJSON")] == ["XMP-pdfmd:Main:RecordJSON"],
        }
        item = {"path": path, "bytes": relocated.stat().st_size, "sha256": change["enriched_sha256"], "checks": checks,
                "description_contains_citation": "Synthetic citation — 中文, p. 58" in str(values.get("XMP-dc:Description"))}
        if cross:
            _, cross_values, _ = read(runner, cross, change["client_key"] + "-cross-13.61", copy)
            item["cross_reader_record_equal"] = json.loads((cross_values or {}).get("XMP-pdfmd:RecordJSON", "null")) == record
        item["passed"] = all(checks.values()) and item["description_contains_citation"]
        report["images"].append(item)
    report["calls"] = runner.calls
    report["passed"] = all(i["passed"] for i in report["images"]) and report["reference_check"]["status"] == "ok"
    dump(run / "report.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "calls"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reader", required=True, type=Path)
    parser.add_argument("--cross-reader", type=Path)
    parser.add_argument("--run", required=True, type=Path)
    main(parser.parse_args())
