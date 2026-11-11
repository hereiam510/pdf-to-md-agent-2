"""T3b desktop fixture: one enriched schema 2 save through the production edit_document path.

A MuPDF page render (PNG) and an unchanged PDF DCT JPEG become occurrences with
readable non-ASCII names and embedded primary XMP. No provider access.
"""
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import unquote
import zipfile

import pymupdf

from pdfmd import primary_xmp
from pdfmd.documents import Documents
from pdfmd.storage import Store, encode
from pdfmd.tools import Dispatcher

SOURCE = Path(__file__).parents[2] / "fixtures" / "pdf" / "rgb-jpeg.pdf"


def ev(ref, note):
    return [{"ref": ref, "physical_page": 1, "region": None, "note": note}]


def prepare(directory):
    root = Path(directory)
    source = root / "Enriched save fixture.pdf"
    shutil.copyfile(SOURCE, source)
    store = Store(root / "workspace")
    dispatcher = Dispatcher(store)
    job = dispatcher.evidence.create_job(str(source), "T3b enriched-save fixture only; do not start conversion.")
    store.update_job(job["id"], name="T3b enriched save", status="paused", active_seconds=999999)
    render = dispatcher.evidence.render_page(job["id"], 1, 60)
    with pymupdf.open(source) as pdf:
        xref = pdf[0].get_images(full=True)[0][0]
    figure = dispatcher.evidence.extract_image(job["id"], 1, xref)
    assert figure["representation"] == "embedded_stream"
    known = lambda value, ref, note: {"state": "known", "value": value, "basis": ev(ref, note), "alternatives": []}
    args = {"base_version": None, "expected_head": None, "claim": "complete",
            "replace_blocks": [
                {"id": "h", "pages": [1], "markdown": "## 第四章 新聞\n\nSource pages: [Open page 1](asset:new/page)"},
                {"id": "body", "pages": [1], "markdown": "![Inline figure](asset:new/fig)\n\n*圖4–2* 新聞的基本屬性。\n\n"
                 "[Open figure](asset:new/fig) and `asset:new/fig` stays literal."}],
            "page_updates": {"1": {"disposition": "included", "printed": "58", "printed_basis": ev(render["ref"], "printed 58 at foot")}},
            "source_update": {"kind": "book", "title": known("新聞學概論（合成）", render["ref"], "title page")},
            "asset_changes": [
                {"kind": "create", "client_key": "page", "facts": {
                    "image_ref": render["ref"], "description": {"full": "Whole page 1.", "filename": "News & framing (page)",
                                                                "language": "en", "punctuation": "ascii", "basis": ev(render["ref"], "render")},
                    "figure": {"state": "none", "value": None, "basis": ev(render["ref"], "whole page"), "alternatives": []},
                    "locations": [{"physical_page": 1, "region": None, "basis": ev(render["ref"], "page")}]}},
                {"kind": "create", "client_key": "fig", "facts": {
                    "image_ref": figure["ref"], "description": {"full": "新聞的基本屬性示意圖。", "filename": "新聞基本屬性: 示意",
                                                                "language": "zh-Hant", "punctuation": "fullwidth", "basis": ev(figure["ref"], "figure")},
                    "caption": known("新聞的基本屬性。", render["ref"], "caption"), "figure": known("圖4–2", render["ref"], "label"),
                    "locations": [{"physical_page": 1, "region": None, "basis": ev(render["ref"], "figure")}]}}]}
    result = dispatcher.execute(job["id"], "t3b-desktop", "edit_document", json.dumps(args, ensure_ascii=False))
    assert result["ok"], result
    changes = {c["client_key"]: c for c in result["data"]["asset_changes"]}
    version = result["data"]["version_id"]
    fixture = {"job": job["id"], "version": version, "page": changes["page"]["asset_path"], "figure": changes["fig"]["asset_path"],
               "page_uri": changes["page"]["asset_uri"],
               "render_size": [render["width"], render["height"]], "figure_size": [figure["width"], figure["height"]],
               "originals": [o["path"] for o in figure["originals"]], "files": store.get("version", version, job=job["id"])["files"]}
    (root / "fixture.json").write_bytes(encode(fixture))
    return fixture


def record(data: bytes) -> dict:
    parsed = primary_xmp.locate_png_primary(primary_xmp.parse_png(data)) if data.startswith(primary_xmp.PNG_SIG) else \
        primary_xmp.locate_jpeg_primary(primary_xmp.parse_jpeg(data))
    node = parsed["packet"].props[(primary_xmp.PDFMD, "RecordJSON")]["node"]
    return json.loads("".join(c.data for c in node.childNodes))


def verify(directory):
    root = Path(directory)
    fixture = json.loads((root / "fixture.json").read_bytes())
    store = Store(root / "workspace")
    documents = Documents(store)
    version = fixture["version"]
    files = store.get("version", version, job=fixture["job"])["files"]
    assert files == fixture["files"]
    saved = documents.version(fixture["job"], version)
    assert saved["schema_version"] == 2 and set(saved["assets"]) == {fixture["page"], fixture["figure"]}
    target = root / "relocated" / "extracted"
    with zipfile.ZipFile(root / "enriched.zip") as archive:
        assert set(archive.namelist()) == set(files)
        for member in archive.namelist():
            assert sha256(archive.read(member)).hexdigest() == files[member]
        archive.extractall(target)
    markdown = (target / "document.md").read_text("utf-8")
    html = (target / "preview.html").read_text("utf-8")
    encoded = set(re.findall(r"\]\((assets/[^)\s]+)\)", markdown)) | set(re.findall(r'(?:src|href)="(assets/[^"]+)"', html))
    decoded = {unquote(p, errors="strict") for p in encoded}
    assert decoded == set(saved["assets"]), decoded
    names = {}
    for path in decoded:
        data = (target / path).read_bytes()
        assert pymupdf.Pixmap(data).width > 0
        assert record(data) == saved["assets"][path]["provenance"]
        names[path] = len(Path(path).name.encode("utf-8"))
    for original in fixture["originals"]:
        assert (target / original).read_bytes() == store.bytes(saved["originals"][original]["ref"], fixture["job"])
    assert "asset:new/fig" in markdown and "pdfmd-preview:" not in markdown + html
    # The UI edit after export reached the engine with a task-scoped desktop key (AR-T3B-04).
    desktop_ops = [o for o in store.records("operation", fixture["job"]) if o["id"].startswith(f"manual:{fixture['job']}:desktop:")]
    assert len(desktop_ops) == 1 and desktop_ops[0].get("ok", True), desktop_ops
    head = store.get("job", fixture["job"])["head"]
    edited = documents.version(fixture["job"], head)
    assert head != version and edited["schema_version"] == 2 and set(edited["assets"]) == {fixture["page"]}
    assert edited["asset_catalog"] == saved["asset_catalog"]
    assert all(j["attempts"] == 0 for j in store.records("job"))
    assert all(not store.records("request", j["id"]) for j in store.records("job"))
    return {"version_unchanged": True, "relocated_links_resolve": True, "embedded_records_equal": True,
            "desktop_edit_operation": desktop_ops[0]["id"].split(":")[0:3],
            "provider_requests": 0, "relative_destinations": sorted(encoded), "basename_utf8_bytes": names}


if __name__ == "__main__":
    print(json.dumps(globals()[sys.argv[1]](sys.argv[2]), ensure_ascii=True))
