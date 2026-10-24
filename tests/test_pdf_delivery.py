"""Source-led Phase 3 checks. Synthetic PDFs, no provider or OCR-service calls."""
import base64
from hashlib import sha256
import json
from pathlib import Path
import zipfile

import pymupdf
import pytest

from pdfmd.documents import Documents
from pdfmd.context import Context
from pdfmd.evidence import Evidence
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher


FIXTURES = Path(__file__).parent / "fixtures" / "pdf"
IMAGE_CASES = [p.stem for p in sorted(FIXTURES.glob("*.pdf"))]


def rotated_source(path, angle, cropped=False):
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=440, height=340)
        page.insert_text((60, 90), "TARGET 25 mg", fontsize=20)
        page.insert_text((340, 240), "EDGE", fontsize=16)
        samples = bytes([210, 20, 40, 10, 160, 60] * (64 * 48 // 2))
        pix = pymupdf.Pixmap(pymupdf.csRGB, 64, 48, samples, False)
        page.insert_image(pymupdf.Rect(60, 120, 124, 168), pixmap=pix)
        if cropped:
            page.set_cropbox(pymupdf.Rect(20, 15, 420, 315))
        page.set_rotation(angle)
        pdf.save(path)


@pytest.mark.parametrize("angle", [0, 90, 180, 270])
@pytest.mark.parametrize("cropped", [False, True])
def test_extracted_boxes_crop_actual_rotated_source(tmp_path, angle, cropped):
    source = tmp_path / "source.pdf"
    rotated_source(source, angle, cropped)
    store = Store(tmp_path / "workspace")
    evidence = Evidence(store)
    job = evidence.create_job(str(source), "Keep the complete source.")["id"]
    item = evidence.inspect(job, [1], "dict")["value"]["pages"][0]
    words = evidence.inspect(job, [1], "words")["value"]["pages"][0]["content"]
    boxes = {word[4]: word[:4] for word in words if word[4] in {"TARGET", "EDGE"}}
    boxes["image"] = next(block["bbox"] for block in item["content"]["blocks"] if block["type"] == 1)
    with pymupdf.open(source) as pdf:
        page = pdf[0]
        assert item["rect"] == list(page.rect * page.derotation_matrix)
        for name, bbox in boxes.items():
            result = evidence.render_page(job, 1, dpi=72, region=bbox)
            actual = pymupdf.Pixmap(store.bytes(result["ref"], job))
            expected = page.get_pixmap(dpi=72, clip=pymupdf.Rect(bbox) * page.rotation_matrix)
            assert (actual.width, actual.height, actual.samples) == (expected.width, expected.height, expected.samples), name
            assert any(value < 200 for value in actual.samples), name
            (tmp_path / f"{name}.png").write_bytes(store.bytes(result["ref"], job))
        assert evidence.source(job) == source.read_bytes()


@pytest.mark.parametrize("angle", [0, 90, 180, 270])
def test_fractional_region_has_invertible_actual_pixel_mapping(tmp_path, angle):
    source = tmp_path / "source.pdf"
    rotated_source(source, angle, True)
    evidence = Evidence(Store(tmp_path / "workspace"))
    job = evidence.create_job(str(source), "Keep the source.")["id"]
    region = [10.25, 20.25, 100.75, 80.75]
    result = evidence.render_page(job, 1, dpi=100, region=region)
    forward = pymupdf.Matrix(result["page_to_pixel"])
    inverse = pymupdf.Matrix(result["pixel_to_page"])
    with pymupdf.open(source) as pdf:
        page = pdf[0]
        expected = page.get_pixmap(dpi=100, clip=pymupdf.Rect(region) * page.rotation_matrix)
        assert result["pixel_origin"] == [expected.x, expected.y]
        for x, y in [(10.25, 20.25), (100.75, 80.75), (50.5, 45.125)]:
            point = pymupdf.Point(x, y)
            rendered = point * page.rotation_matrix * pymupdf.Matrix(100 / 72, 100 / 72)
            want = (rendered.x - expected.x, rendered.y - expected.y)
            assert tuple(point * forward) == pytest.approx(want, abs=0.0001)
            assert tuple(point * forward * inverse) == pytest.approx((x, y), abs=0.0001)


@pytest.mark.parametrize("name", IMAGE_CASES)
def test_image_originals_display_and_portable_delivery(tmp_path, name):
    source = FIXTURES / f"{name}.pdf"
    store = Store(tmp_path / "workspace")
    evidence = Evidence(store)
    job = evidence.create_job(str(source), "Preserve the source image.")["id"]
    with pymupdf.open(source) as pdf:
        entry = pdf[0].get_images(full=True)[0]
        result = evidence.extract_image(job, 1, entry[0])
        raw = pdf.xref_stream_raw(entry[0])
        assert store.bytes(result["original_ref"], job) == raw
        assert result["original_bytes_equal"] == (store.bytes(result["ref"], job) == raw)
        for original in result["originals"]:
            info = store.get("blob", original["ref"], job=job)
            assert store.bytes(original["ref"], job) == pdf.xref_stream_raw(info["meta"]["xref"])
            assert base64.b64decode(evidence.read(job, original["ref"], "raw")["data"]) == store.bytes(original["ref"], job)
            assert base64.b64decode(evidence.read(job, original["ref"], "full", start=0, end=17)["data"]) == store.bytes(original["ref"], job)[:17]
        image = pymupdf.Pixmap(store.bytes(result["ref"], job))
        assert (image.width, image.height) == (64, 48)
        assert result["extension"] in {"png", "jpeg", "jpg"}
        assert result["mask_xref"] == entry[1]
        if entry[1]:
            assert image.alpha and len(result["originals"]) == 2
        if name == "rgb-jpeg":
            assert result["original_bytes_equal"] and result["representation"] == "embedded_stream"
        else:
            assert result["extension"] == "png" and result["representation"] == "derived_display"
        if name.startswith("cmyk"):
            assert result["color_conversion"] and not result["original_bytes_equal"]
        # Compare visible source pixels at native resolution, including the PDF's background.
        rect = pdf[0].get_image_rects(entry[0])[0]
        expected = pdf[0].get_pixmap(dpi=36, clip=rect, alpha=False)
        background = pdf[0].get_pixmap(dpi=36, clip=pymupdf.Rect(0, 0, 2, 2)).samples[:3]
        actual = image.samples
        composited = bytes(min(255, actual[i + c] + round(background[c] * (1 - actual[i + 3] / 255)))
                           for i in range(0, len(actual), 4) for c in range(3)) if image.alpha else actual
        delta = max(abs(a - b) for a, b in zip(composited, expected.samples, strict=True))
        assert delta <= 3, (name, delta)
        expected.save(tmp_path / "source-native.png")
    raw_image = store.bytes(result["ref"], job)
    assert base64.b64decode(evidence.read(job, result["ref"], "raw", start=0, end=17)["data"]) == raw_image[:17]
    saved = Dispatcher(store).execute(job, "save", "edit_document", json.dumps({
        "base_version": None, "expected_head": None,
        "replace_blocks": [{"id": "figure", "pages": [1], "markdown": f"![{name}]({result['asset_path']})"}],
        "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "complete"}))
    assert saved["ok"]
    version = saved["data"]["version_id"]
    reopened = Documents(Store(store.root))
    document = reopened.version(job, version)
    assert len(document["originals"]) == len(result["originals"])
    archive = tmp_path / "delivery.zip"
    assert reopened.export(job, version, str(archive))["verified"]
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.namelist():
            assert zipped.read(member) == (reopened.root / version / member).read_bytes()
        for path, original in document["originals"].items():
            assert zipped.read(path) == store.bytes(original["ref"], job)
        zipped.extractall(tmp_path / "exported")
    assert evidence.source(job) == source.read_bytes()
    (tmp_path / "verification.json").write_text(json.dumps({"case": name, "version": version,
        "source_sha256": sha256(source.read_bytes()).hexdigest(), "source_max_channel_difference": delta,
        "result": result, "source_preserved": True, "export_members_equal": True}, indent=2), encoding="utf-8")


@pytest.mark.parametrize("angle", [0, 90, 180, 270])
def test_ocr_uses_same_extracted_region_and_pixel_mapping(tmp_path, monkeypatch, angle):
    source = tmp_path / "source.pdf"
    rotated_source(source, angle, True)
    store = Store(tmp_path / "workspace")
    dispatcher = Dispatcher(store)
    job = dispatcher.evidence.create_job(str(source), "Keep the source.")["id"]
    words = dispatcher.evidence.inspect(job, [1], "words")["value"]["pages"][0]["content"]
    region = next(word[:4] for word in words if word[4] == "EDGE")
    monkeypatch.setenv("PDFMD_OCR_WORKER", "offline-worker")
    monkeypatch.setenv("PDFMD_NODE", "offline-node")
    def worker(_job, _operation, command, directory, timeout, env):
        # Exercise the real image preparation and result persistence, not OCR recognition.
        with pymupdf.open(source) as pdf:
            expected = pdf[0].get_pixmap(dpi=144, clip=pymupdf.Rect(region) * pdf[0].rotation_matrix)
        actual = pymupdf.Pixmap(str(directory / "input.png"))
        assert actual.samples == expected.samples
        (directory / "result.json").write_text(json.dumps({"text": "EDGE", "fixture": True}), encoding="utf-8")
        logs = [directory / name for name in ["stdout.txt", "stderr.txt"]]
        for path in logs:
            path.write_bytes(b"offline fixture; no OCR recognition performed")
        return 0, *logs
    monkeypatch.setattr(dispatcher, "process", worker)
    result = dispatcher.ocr(job, "ocr", 1, "eng", dpi=144, region=region)
    image = result["value"]["image"]
    assert image["region"] == region and len(image["pixel_to_page"]) == 6
    raw = dispatcher.evidence.read(job, result["ref"], "raw")
    assert base64.b64decode(raw["data"]) == store.bytes(result["ref"], job)
    assert dispatcher.evidence.read(job, result["ref"], json_pointer="/ocr/text", start=0, end=2)["value"] == "ED"


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_jpx_display_pixels_remain_available_to_both_protocols(tmp_path, route, protocol):
    store = Store(tmp_path / "workspace")
    dispatcher = Dispatcher(store)
    route = {**route, "protocol": protocol, "vision": True, "image_tokens": 1024,
             "endpoint": "http://127.0.0.1/v1/" + ("responses" if protocol == "responses" else "chat/completions")}
    job = dispatcher.evidence.create_job(str(FIXTURES / "jpx.pdf"), "Preserve image.", route)
    with pymupdf.open(FIXTURES / "jpx.pdf") as pdf:
        result = dispatcher.evidence.extract_image(job["id"], 1, pdf[0].get_images()[0][0])
    parts = Context(store, dispatcher).pixels(job, result["image_ref"], "Source image")
    urls = [part["image_url"]["url"] if isinstance(part["image_url"], dict) else part["image_url"]
            for part in parts if "image_url" in part]
    assert len(urls) == 1 and urls[0].startswith("data:image/png;base64,")
    assert base64.b64decode(urls[0].split(",", 1)[1]) == store.bytes(result["ref"], job["id"])
