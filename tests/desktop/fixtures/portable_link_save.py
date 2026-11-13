"""T3a desktop fixture: new schema 1 saves through the production edit_document path.

Hyperlink-only and mixed A03-shaped saves, with a hyperlinked extracted image
carrying original streams. No snapshot constructor and no provider access.
"""
from hashlib import sha256
import json
from pathlib import Path
import random
import re
import sys
import zipfile

import pymupdf

from pdfmd.documents import Documents
from pdfmd.storage import Store, encode
from pdfmd.tools import Dispatcher


def save(dispatcher, job, blocks, operation):
    current = dispatcher.store.get("job", job)
    result = dispatcher.execute(job, operation, "edit_document", json.dumps({
        "base_version": current["head"], "expected_head": current["head"], "replace_blocks": blocks,
        "page_updates": {"1": {"disposition": "included", "printed": "none"}}, "claim": "complete"}, ensure_ascii=False))
    assert result["ok"], result
    return result["data"]["version_id"]


def prepare(directory):
    root = Path(directory)
    source = root / "Portable link fixture.pdf"
    picture = pymupdf.Pixmap(pymupdf.csRGB, 320, 240, random.Random(7).randbytes(320 * 240 * 3), False)
    mask = pymupdf.Pixmap(pymupdf.csGRAY, 320, 240, bytes([200]) * (320 * 240), False)
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=600, height=500)
        page.insert_text((32, 30), "Synthetic portable-link evidence. No provider.")
        page.insert_image(pymupdf.Rect(40, 60, 360, 300), pixmap=pymupdf.Pixmap(picture, mask))
        pdf.save(source)
    store = Store(root / "workspace")
    dispatcher = Dispatcher(store)
    job = dispatcher.evidence.create_job(str(source), "T3a portable-link fixture only; do not start conversion.")
    store.update_job(job["id"], name="T3a portable links", status="paused", active_seconds=999999)
    render = dispatcher.evidence.render_page(job["id"], 1, 60)
    with pymupdf.open(source) as pdf:
        xref = pdf[0].get_images(full=True)[0][0]
    extracted = dispatcher.evidence.extract_image(job["id"], 1, xref)
    assert len(extracted["originals"]) == 2
    link = save(dispatcher, job["id"], [
        {"id": "h", "pages": [1], "markdown": f"## 第二章 Assessment\n\nSource pages: [Open page 1]({render['asset_path']})"},
        {"id": "body", "pages": [1], "markdown": f"Dose **25 mg** q6h.[^1] See [Open figure]({extracted['asset_path']}).\n\n"
         "| Item | Value |\n|---|---|\n| Rate | 12/min |\n\n[^1]: Footnote with [External citation](https://example.invalid/ref)."}],
        "t3a-link-only")
    mixed = save(dispatcher, job["id"], [
        {"id": "h", "pages": [1], "markdown": f"## Mixed section\n\nSource pages: [Open page 1]({render['asset_path']})"},
        {"id": "body", "pages": [1], "markdown": f"![Inline figure]({extracted['asset_path']})\n\n*Figure 1.* Caption.\n\n"
         f"[Open figure]({extracted['asset_path']})"}],
        "t3a-mixed")
    result ={"job": job["id"], "link": link, "mixed": mixed, "render": render["asset_path"], "figure": extracted["asset_path"],
              "render_size": [render["width"], render["height"]], "figure_size": [extracted["width"], extracted["height"]],
              "originals": [o["path"] for o in extracted["originals"]],
              "versions": {v: store.get("version", v, job=job["id"])["files"] for v in [link, mixed]}}
    (root / "fixture.json").write_bytes(encode(result))
    return result


def verify(directory):
    """Check versions are unchanged, then relocate each exported ZIP and resolve its relative links."""
    root = Path(directory)
    fixture = json.loads((root / "fixture.json").read_bytes())
    store = Store(root / "workspace")
    documents = Documents(store)
    report = {}
    for name, version in [("link", fixture["link"]), ("mixed", fixture["mixed"])]:
        files = store.get("version", version, job=fixture["job"])["files"]
        assert files == fixture["versions"][version]
        saved = documents.version(fixture["job"], version)
        assert set(saved["assets"]) == {fixture["render"], fixture["figure"]}
        assert set(saved["originals"]) == set(fixture["originals"])
        target = root / "relocated" / name / "extracted"
        with zipfile.ZipFile(root / f"{name}.zip") as archive:
            assert set(archive.namelist()) == set(files)
            for member in archive.namelist():
                assert archive.read(member) == (documents.root / version / member).read_bytes()
                assert sha256(archive.read(member)).hexdigest() == files[member]
            archive.extractall(target)
        markdown = (target / "document.md").read_text("utf-8")
        html = (target / "preview.html").read_text("utf-8")
        destinations = set(re.findall(r"\]\((assets/[^)\s]+)\)", markdown)) | set(re.findall(r'(?:src|href)="(assets/[^"]+)"', html))
        assert destinations and destinations == set(saved["assets"])
        for path in destinations:
            decoded = pymupdf.Pixmap((target / path).read_bytes())
            assert decoded.width > 0 and decoded.height > 0
        assert "pdfmd-preview:" not in markdown + html and "pdfmd-resource-" not in markdown + html
        report[name] = {"members": len(files), "relative_destinations": sorted(destinations), "originals": sorted(saved["originals"])}
    assert all(j["attempts"] == 0 for j in store.records("job"))
    assert all(not store.records("request", j["id"]) for j in store.records("job"))
    return {"versions_unchanged": True, "relocated_links_resolve": True, "provider_requests": 0, "report": report}


if __name__ == "__main__":
    print(json.dumps(globals()[sys.argv[1]](sys.argv[2]), ensure_ascii=True))
