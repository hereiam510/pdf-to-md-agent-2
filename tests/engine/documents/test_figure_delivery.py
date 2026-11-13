"""Source-led synthetic FD-01 tool/persistence checks; no agent understanding claim."""
from hashlib import sha256
import json
from pathlib import Path
import zipfile

import httpx
import pymupdf
import pytest

from pdfmd.documents import Documents
from pdfmd.nexus import Nexus, StopRun
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher
from tests.engine.documents.test_documents import call


CAPTION = "Figure 1. A and B are related panels. Solid arrow: transfer only if enabled; dashed: no transfer."
TEXTS = {
    "panels": f"**Original caption:** {CAPTION}\n\n**Panel A:** IN; 10 mg. **Panel B:** OUT; 0 mg.\n\n"
              "**Relationship:** The solid arrow runs from A to B only if enabled. The dashed line means no transfer.",
    "curve": "**Original caption:** Figure 2. Response phases.\n\n**Axes:** Time (s): 0, 5. Level (mg): 0, 10.\n\n"
             "**Phases and legend:** Rise; Rest. Solid: enabled. No intermediate numeric values are specified.",
    "uncaptioned": "**Agent description (not a source caption):** Two boxes are linked by a dashed segment.\n\n"
                   "**Source labels:** Left box: LEFT. Right box: RIGHT.\n\n"
                   "**Uncertainty:** The source does not specify the dashed segment's meaning or direction; no causality is inferred.",
    "unlabelled": "**Agent description (not a source caption):** A rectangular image has red and blue areas.\n\n"
                  "No source caption, labels or numerical values are present.",
}


def figure_source(path, angle=0, cropped=False):
    """Four independent units, including related panels and captionless/no-text cases."""
    boxes = {"panels": [20, 60, 245, 230], "curve": [270, 60, 495, 230],
             "uncaptioned": [20, 260, 245, 390]}
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=520, height=420)
        page.insert_text((20, 35), "Substantive body prose outside the figures.")
        page.insert_text((22, 78), "A: IN; 10 mg", fontsize=10)
        page.insert_text((158, 78), "B: OUT; 0 mg", fontsize=10)
        page.draw_rect((23, 90, 95, 145), color=(0, 0, 1))
        page.draw_rect((157, 90, 238, 145), color=(1, 0, 0))
        page.draw_line((95, 105), (157, 105))
        page.draw_line((150, 101), (157, 105))
        page.draw_line((150, 109), (157, 105))
        page.draw_line((95, 130), (157, 130), dashes="[3 3]")
        assert page.insert_textbox((22, 158, 242, 228), CAPTION, fontsize=10) >= 0
        for position, text in [((275, 78), "Level (mg)"), ((275, 96), "10"), ((275, 166), "0"),
                               ((300, 180), "0   Time (s)   5"), ((300, 110), "Rise"), ((420, 110), "Rest"),
                               ((275, 200), "Figure 2. Response phases."), ((275, 218), "Solid: enabled")]:
            page.insert_text(position, text, fontsize=10)
        page.draw_polyline([(300, 90), (300, 165), (480, 165)])
        page.draw_polyline([(300, 165), (360, 125), (420, 120), (480, 120)], color=(0, 0.5, 0))
        page.insert_text((20, 250), "More body prose; do not include this in a figure.", fontsize=10)
        page.draw_rect((25, 280, 90, 350))
        page.draw_rect((165, 280, 240, 350))
        page.insert_text((30, 315), "LEFT", fontsize=10)
        page.insert_text((175, 315), "RIGHT", fontsize=10)
        page.draw_line((90, 315), (165, 315), dashes="[3 3]")
        samples = bytes([220, 20, 30] * (32 * 48) + [20, 30, 220] * (32 * 48))
        pix = pymupdf.Pixmap(pymupdf.csRGB, 64, 48, samples, False)
        page.insert_image((300, 280, 428, 376), pixmap=pix)
        if cropped:
            page.set_cropbox((10, 15, 510, 405))
            boxes = {key: [x0 - 10, y0 - 15, x1 - 10, y1 - 15]
                     for key, (x0, y0, x1, y1) in boxes.items()}
        page.set_rotation(angle)
        pdf.save(path)
    return boxes


def prepare_figures(directory, angle=0, cropped=False):
    directory = Path(directory)
    source = directory / "synthetic-figures.pdf"
    boxes = figure_source(source, angle, cropped)
    store = Store(directory / "workspace")
    d = Dispatcher(store)
    job = d.evidence.create_job(str(source), "Convert all substantive content, including unnumbered figures.")
    images = {key: d.evidence.render_page(job["id"], 1, 144, region) for key, region in boxes.items()}
    with pymupdf.open(source) as pdf:
        images["unlabelled"] = d.evidence.extract_image(job["id"], 1, pdf[0].get_images()[0][0])
        pdf[0].get_pixmap(dpi=144).save(directory / "source-page.png")
    blocks = [{"id": "body", "pages": [1], "markdown": "Substantive body prose outside the figures.\n\nMore body prose; do not include this in a figure."}]
    blocks += [{"id": key, "pages": [1], "markdown": f"### {key}\n\n![{key}]({image['asset_path']})\n\n{TEXTS[key]}",
                "source_note": "Synthetic fixture text, not an autonomous transcription."} for key, image in images.items()]
    partial_blocks = [dict(block) for block in blocks]
    partial_blocks[1]["markdown"] = partial_blocks[1]["markdown"].replace("OUT; 0 mg", "[unread]")
    gap = "Panel B's output label and value remain unread."
    first = call(d, job["id"], "partial", {"base_version": None, "expected_head": None,
        "replace_blocks": partial_blocks, "page_updates": {"1": {"printed": "none", "disposition": "included"}},
        "claim": "partial", "known_gaps": [gap]})
    assert first["ok"], first
    one = first["data"]["version_id"]
    rejected_args = {"base_version": one, "expected_head": one, "claim": "complete"}
    rejected = call(d, job["id"], "false-complete", rejected_args)
    assert not rejected["ok"] and store.get("job", job["id"])["head"] == one
    assert json.loads(store.bytes(rejected["candidate_ref"], job["id"])) == rejected_args
    fixed = call(d, job["id"], "correct", {"base_version": one, "expected_head": one,
        "operations": [{"kind": "replace", "id": "panels", "blocks": [blocks[1]]}],
        "known_gaps": [], "claim": "complete"})
    assert fixed["ok"], fixed
    two = fixed["data"]["version_id"]
    # Replaying a historical receipt never rewinds the selected correction.
    assert call(d, job["id"], "false-complete", rejected_args) == rejected
    assert store.get("job", job["id"])["head"] == two
    assert d.documents.version(job["id"], one)["content"]["known_gaps"] == [gap]
    store.update_job(job["id"], delivery=two, status="completed", content_claim="complete")
    fixture = {"job": job["id"], "version": two, "partial_version": one, "source": str(source), "images": images,
               "blocks": blocks, "source_sha256": sha256(source.read_bytes()).hexdigest(), "live_model_calls": 0}
    (directory / "fixture.json").write_text(json.dumps(fixture, indent=2), encoding="utf-8")
    return fixture


def verify_figures(directory):
    directory = Path(directory)
    fixture = json.loads((directory / "fixture.json").read_text("utf-8"))
    store = Store(directory / "workspace")
    documents = Documents(store)
    saved = documents.version(fixture["job"], fixture["version"])
    assert saved["content"]["blocks"] == [{"source_note": "", **b} for b in fixture["blocks"]]
    assert saved["content"]["known_gaps"] == [] and saved["content"]["claim"] == "complete"
    with zipfile.ZipFile(directory / "delivery.zip") as zipped:
        assert json.loads(zipped.read("document.json")) == saved
        for member in zipped.namelist():
            assert zipped.read(member) == (documents.root / fixture["version"] / member).read_bytes()
        markdown = zipped.read("document.md").decode("utf-8")
        html = zipped.read("preview.html").decode("utf-8")
        for key, image in fixture["images"].items():
            assert TEXTS[key] in markdown
            assert zipped.read(image["asset_path"]) == store.bytes(image["ref"], fixture["job"])
            # Each section retains its own source labels/description in portable visible HTML.
            section = html.split(f"<h3>{key}</h3>", 1)[1].split("<h3>", 1)[0]
            assert f'src="{image["asset_path"]}"' in section
            assert ("Panel A:" if key == "panels" else "Axes:" if key == "curve" else "Agent description (not a source caption)") in section
        for name, original in saved["originals"].items():
            assert zipped.read(name) == store.bytes(original["ref"], fixture["job"])
        zipped.extractall(directory / "exported")
    assert len(saved["assets"]) == 4 and len(saved["originals"]) == 1
    assert store.bytes(saved["source_ref"], fixture["job"]) == Path(fixture["source"]).read_bytes()
    return {"version": fixture["version"], "assets": 4, "originals": 1, "attempts": store.get("job", fixture["job"])["attempts"],
            "all_members_equal": True, "fixture_associations_preserved": True, "live_model_calls": 0}


@pytest.mark.parametrize("angle", [0, 90, 180, 270])
@pytest.mark.parametrize("cropped", [False, True])
def test_independent_figures_edges_correction_reopen_and_zero_send_export(tmp_path, route, angle, cropped):
    fixture = prepare_figures(tmp_path, angle, cropped)
    store = Store(tmp_path / "workspace")
    d = Dispatcher(store)
    with pymupdf.open(fixture["source"]) as pdf:
        page = pdf[0]
        full = page.get_pixmap(dpi=144, alpha=False)
        full_samples = full.samples
        for key, image in fixture["images"].items():
            if key == "unlabelled":
                continue  # Native image/original-stream case, covered separately above.
            bounds = pymupdf.Rect(image["region"]) * page.rotation_matrix * pymupdf.Matrix(2, 2)
            box = bounds.irect
            expected = b"".join(full_samples[y * full.stride + box.x0 * 3:y * full.stride + box.x1 * 3]
                                for y in range(box.y0, box.y1))
            actual = pymupdf.Pixmap(store.bytes(image["ref"], fixture["job"]))
            assert (actual.width, actual.height, actual.samples) == (box.width, box.height, expected)
            assert image["source_ref"] == store.get("job", fixture["job"])["source_ref"]
            assert image["rotation"] == angle and image["dpi"] == 144
            assert image["region"] != list(page.rect * page.derotation_matrix)
        words = d.evidence.inspect(fixture["job"], [1], "words")["value"]["pages"][0]["content"]
        for label, key in [("A:", "panels"), ("mg", "panels"), ("Rest", "curve"), ("RIGHT", "uncaptioned")]:
            assert any(w[4] == label and pymupdf.Rect(fixture["images"][key]["region"]).contains(pymupdf.Rect(w[:4])) for w in words)
    current = store.get("job", fixture["job"])
    store.update_job(fixture["job"], route=route, attempts=1, limits={**current["limits"], "max_requests": 1})
    nexus = Nexus(store, lambda _: "offline", httpx.MockTransport(lambda _: pytest.fail("Exhausted allowance must not send")))
    nexus.freeze(fixture["job"], "exhausted", {"model": route["model"], "messages": []}, "normal", {})
    with pytest.raises(StopRun) as failure:
        nexus.send(fixture["job"], "exhausted")
    assert failure.value.reason == "budget_exhausted"
    reopened = Documents(Store(store.root))
    assert reopened.export(fixture["job"], fixture["version"], str(tmp_path / "delivery.zip"))["verified"]
    result = verify_figures(tmp_path)
    assert result["attempts"] == 1
    assert not store.records("attempt", fixture["job"])
