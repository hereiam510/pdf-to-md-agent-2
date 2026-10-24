"""Prepare or verify a source-led renderer fixture without starting an agent."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import zipfile

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_pdf_delivery import FIXTURES, IMAGE_CASES, rotated_source
from pdfmd.documents import Documents
from pdfmd.evidence import Evidence
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher


def prepare(directory):
    directory = Path(directory)
    source = directory / "PDF delivery source.pdf"
    with pymupdf.open() as combined:
        for name in IMAGE_CASES:
            with pymupdf.open(FIXTURES / f"{name}.pdf") as pdf:
                combined.insert_pdf(pdf)
                combined[-1].insert_text((40, 25), name, fontsize=14)
        for angle in [0, 90, 180, 270]:
            path = directory / f"rotation-{angle}.pdf"
            rotated_source(path, angle, True)
            with pymupdf.open(path) as pdf:
                combined.insert_pdf(pdf)
        combined.save(source)
    store = Store(directory / "workspace")
    dispatcher = Dispatcher(store)
    job = dispatcher.evidence.create_job(str(source), "Preserve all source labels and figures, including rotated regions.")
    blocks, images = [], []
    with pymupdf.open(source) as pdf:
        for i, page in enumerate(pdf):
            text = dispatcher.evidence.inspect(job["id"], [i + 1], "text")["value"]["pages"][0]["content"]
            blocks.append({"id": f"text{i}", "pages": [i + 1], "markdown": text})
            if i < len(IMAGE_CASES):
                results = [(IMAGE_CASES[i], dispatcher.evidence.extract_image(job["id"], i + 1, page.get_images()[0][0]))]
                page.get_pixmap().save(directory / f"source-{IMAGE_CASES[i]}.png")
            else:
                info = dispatcher.evidence.inspect(job["id"], [i + 1], "dict")["value"]["pages"][0]
                region = next(block["bbox"] for block in info["content"]["blocks"] if block["type"] == 1)
                words = dispatcher.evidence.inspect(job["id"], [i + 1], "words")["value"]["pages"][0]["content"]
                edge = next(word[:4] for word in words if word[4] == "EDGE")
                results = [(f"rotation-{page.rotation}-{name}", dispatcher.evidence.render_page(job["id"], i + 1, 144, box))
                           for name, box in [("figure", region), ("edge", edge)]]
                page.get_pixmap().save(directory / f"source-rotation-{page.rotation}.png")
            for label, result in results:
                blocks.append({"id": f"image{len(images)}", "pages": [i + 1], "markdown": f"![{label}]({result['asset_path']})"})
                images.append({"label": label, "width": result["width"], "height": result["height"],
                               "path": result["asset_path"], "page": i + 1, "provenance": result})
    saved = dispatcher.execute(job["id"], "save", "edit_document", json.dumps({
        "base_version": None, "expected_head": None, "replace_blocks": blocks,
        "page_updates": {str(i): {"printed": "none", "disposition": "included"} for i in range(1, job["page_count"] + 1)},
        "claim": "complete"}))
    assert saved["ok"]
    version = saved["data"]["version_id"]
    store.update_job(job["id"], delivery=version, content_claim="complete", status="completed")
    result = {"job": job["id"], "version": version, "source": str(source), "images": images,
              "source_sha256": sha256(source.read_bytes()).hexdigest(), "live_model_calls": 0}
    (directory / "fixture.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def verify(directory):
    directory = Path(directory)
    fixture = json.loads((directory / "fixture.json").read_text(encoding="utf-8"))
    store = Store(directory / "workspace")
    documents = Documents(store)
    saved = documents.version(fixture["job"], fixture["version"])
    with pymupdf.open(fixture["source"]) as pdf, zipfile.ZipFile(directory / "delivery.zip") as zipped:
        markdown = zipped.read("document.md").decode("utf-8")
        assert all(line in markdown for page in pdf for line in page.get_text().splitlines())
        for member in zipped.namelist():
            assert zipped.read(member) == (documents.root / fixture["version"] / member).read_bytes()
        for path, original in saved["originals"].items():
            assert zipped.read(path) == pdf.xref_stream_raw(original["provenance"]["xref"])
        assert store.bytes(saved["source_ref"], fixture["job"]) == Path(fixture["source"]).read_bytes()
        zipped.extractall(directory / "exported")
    result = {"source_preserved": True, "all_source_text_present": True, "all_members_equal": True,
              "originals": len(saved["originals"]), "assets": len(saved["assets"]), "visible_images": len(fixture["images"]),
              "attempts": store.get("job", fixture["job"])["attempts"], "version": fixture["version"]}
    (directory / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps((prepare if sys.argv[1] == "prepare" else verify)(sys.argv[2])))
