"""T3a portable-link save acceptance (engine part). Synthetic sources, no provider calls.

The save collects the role-aware dependency union (embeds and local image
hyperlinks) under existing hash paths, with associated originals, and rejects
diagnostic saved-output previews as source deliverables.
"""
from dataclasses import replace
import json
from pathlib import Path
import zipfile

import pytest

import pdfmd.documents as documents_module
from pdfmd.asset_references import analyze, classify
from pdfmd.evidence import Evidence
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher
from tests.engine.documents.test_documents import call, edit

FIXTURES = Path(__file__).parents[2] / "fixtures" / "pdf"
DIAGNOSTIC = {"purpose": "saved-output diagnostic preview", "coverage": "selected viewport; not the entire document"}


def saved_files(dispatcher, job, version):
    folder = dispatcher.documents.root / version
    return {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}


def assert_rejected(dispatcher, job, operation, args, head, *fragments):
    result = call(dispatcher, job, operation, args)
    assert not result["ok"]
    message = result["data"]["error"]
    for fragment in fragments:
        assert fragment in message, message
    assert result["candidate_ref"] in message
    assert dispatcher.store.get("job", job)["head"] == head
    assert dispatcher.store.json(result["candidate_ref"], job) == args
    return result


def test_hyperlink_only_and_mixed_saves_collect_each_referenced_path_once(setup):
    store, job = setup
    d = Dispatcher(store)
    link = d.evidence.render_page(job["id"], 1, 50)
    embed = d.evidence.render_page(job["id"], 1, 72)
    unrelated = d.evidence.render_page(job["id"], 1, 40)
    only = call(d, job["id"], "link-only", edit([{"id": "b", "pages": [1], "markdown": f"[Open page 1]({link['asset_path']})"}]))
    assert only["ok"], only
    version = only["data"]["version_id"]
    saved = d.documents.version(job["id"], version)
    assert set(saved["assets"]) == {link["asset_path"]}
    assert saved_files(d, job["id"], version) == {"document.json", "document.md", "preview.html", "manifest.json", link["asset_path"]}
    assert (d.documents.root / version / link["asset_path"]).read_bytes() == store.bytes(link["ref"], job["id"])
    assert d.documents.reference_check(job["id"], version) == {"status": "ok", "issues": []}

    text = (f"[Page]({link['asset_path']}) and again [here]({link['asset_path']})\n\n![Figure]({embed['asset_path']})\n\n"
            f"[![thumb]({embed['asset_path']})]({link['asset_path']})\n\n<a href=\"{link['asset_path']}\">raw link</a>\n\n"
            "[External](https://example.invalid/source) `[literal](assets/" + "0" * 64 + ".png)`")
    head = store.get("job", job["id"])["head"]
    args = {**edit([{"id": "b", "pages": [1], "markdown": text}]), "base_version": head, "expected_head": head}
    mixed = call(d, job["id"], "mixed", args)
    assert mixed["ok"], mixed
    version = mixed["data"]["version_id"]
    saved = d.documents.version(job["id"], version)
    assert set(saved["assets"]) == {link["asset_path"], embed["asset_path"]}
    assert unrelated["asset_path"] not in saved_files(d, job["id"], version)
    assert saved["content"]["blocks"][0]["markdown"] == text
    roles = {(r.role, classify(r.destination, r.role)[1]) for r in analyze(saved["content"]["blocks"], saved["content"]["pages"]).references}
    assert ("hyperlink", link["asset_path"]) in roles and ("image", embed["asset_path"]) in roles
    for path in saved["assets"]:
        assert (d.documents.root / version / path).read_bytes() == store.bytes(saved["assets"][path]["ref"], job["id"])


def test_hyperlinked_extracted_image_carries_its_original_streams(tmp_path):
    store = Store(tmp_path / "workspace")
    d = Dispatcher(store)
    job = d.evidence.create_job(str(FIXTURES / "rgb-smask.pdf"), "Preserve the source image.")["id"]
    import pymupdf
    with pymupdf.open(FIXTURES / "rgb-smask.pdf") as pdf:
        xref = pdf[0].get_images(full=True)[0][0]
    image = d.evidence.extract_image(job, 1, xref)
    assert len(image["originals"]) == 2
    result = call(d, job, "linked", edit([{"id": "b", "pages": [1], "markdown": f"[Figure on page 1]({image['asset_path']})"}]))
    assert result["ok"], result
    version = result["data"]["version_id"]
    saved = d.documents.version(job, version)
    assert set(saved["originals"]) == {o["path"] for o in image["originals"]}
    for original in image["originals"]:
        assert (d.documents.root / version / original["path"]).read_bytes() == store.bytes(original["ref"], job)
    assert d.documents.reference_check(job, version)["status"] == "ok"


def a03_shaped(renders, inline=None):
    """Section Markdown shaped like the A03 delivery: page-labelled render links in ordinary prose."""
    links = " ".join(f"[p{page}]({image['asset_path']})" for page, image in renders)
    figure = f"\n\n![Figure 2-1 原文]({inline['asset_path']})\n\n*Figure 2-1.* Caption text." if inline else ""
    return [
        {"id": "h", "pages": [1], "markdown": "## 第二章 Assessment\n\nSource pages: " + links},
        {"id": "body", "pages": [1], "markdown": "Dose **25 mg** q6h — see the table.[^1]" + figure +
         "\n\n| Item | Value |\n|---|---|\n| Rate | 12/min |\n\n[^1]: Footnote with [external](https://example.invalid/ref)."},
    ]


@pytest.mark.parametrize("mixed", [False, True])
def test_a03_shaped_regression_saves_succeed_through_shared_resolver(setup, mixed):
    store, job = setup
    d = Dispatcher(store)
    renders = [(1, d.evidence.render_page(job["id"], 1, 50))]
    inline = d.evidence.render_page(job["id"], 1, 72) if mixed else None
    blocks = a03_shaped(renders, inline)
    result = call(d, job["id"], "a03", edit(blocks))
    assert result["ok"], result
    saved = d.documents.version(job["id"], result["data"]["version_id"])
    assert [b["markdown"] for b in saved["content"]["blocks"]] == [b["markdown"] for b in blocks]
    expected = {renders[0][1]["asset_path"]} | ({inline["asset_path"]} if inline else set())
    assert set(saved["assets"]) == expected
    assert d.documents.reference_check(job["id"], result["data"]["version_id"])["status"] == "ok"


def test_rejections_identify_reference_and_preserve_candidate_and_head(setup, tmp_path, monkeypatch):
    store, job = setup
    d = Dispatcher(store)
    other = Evidence(store).create_job(str(FIXTURES / "rgb-jpeg.pdf"), "Other task.")["id"]
    foreign = d.evidence.render_page(other, 1, 40)["asset_path"]
    missing = "assets/" + "a" * 64 + ".png"
    assert_rejected(d, job["id"], "missing", edit([{"id": "b", "pages": [1], "markdown": f"[gone]({missing})"}]), None,
                    "not registered", missing, "block b")
    assert_rejected(d, job["id"], "foreign", edit([{"id": "b", "pages": [1], "markdown": f"[other]({foreign})"}]), None,
                    "not registered", foreign)
    own = d.evidence.render_page(job["id"], 1, 50)["asset_path"]
    assert_rejected(d, job["id"], "markup", edit([{"id": "b", "pages": [1], "markdown": f'<img src="{own}" SRC="{own}">'}]), None,
                    "Ambiguous or duplicate resource attributes")
    assert_rejected(d, job["id"], "handle", edit([{"id": "b", "pages": [1], "markdown": "[new](asset:new/figure)"}]), None,
                    "handles must be resolved")
    real = documents_module.analyze

    def spanless(blocks, pages):
        analysis = real(blocks, pages)
        analysis.references = [replace(r, span=None) for r in analysis.references]
        return analysis
    monkeypatch.setattr(documents_module, "analyze", spanless)
    assert_rejected(d, job["id"], "span", edit([{"id": "b", "pages": [1], "markdown": f"[x]({own})"}]), None,
                    "unambiguous guarded source span", own)
    monkeypatch.undo()
    # The rejected candidate is reusable once corrected.
    fixed = call(d, job["id"], "fixed", edit([{"id": "b", "pages": [1], "markdown": f"[x]({own})"}]))
    assert fixed["ok"], fixed


def test_diagnostic_preview_registration_is_not_a_source_deliverable(setup):
    store, job = setup
    d = Dispatcher(store)
    source = d.evidence.render_page(job["id"], 1, 50)
    raw = store.bytes(source["ref"], job["id"])
    diagnostic = d.evidence.image(job["id"], raw + b"\x00diagnostic", "png", {"version": "v", **DIAGNOSTIC})
    for role, text in [("hyperlink", f"[preview]({diagnostic['asset_path']})"), ("image", f"![preview]({diagnostic['asset_path']})")]:
        assert_rejected(d, job["id"], f"diag-{role}", edit([{"id": "b", "pages": [1], "markdown": text}]), None,
                        "diagnostic saved-output preview is not a source image", diagnostic["asset_path"], role)
    # Same hash path also registered by a later diagnostic: the eligible source registration still supplies it.
    shared = d.evidence.image(job["id"], raw, "png", {"version": "v", **DIAGNOSTIC})
    assert shared["asset_path"] == source["asset_path"]
    result = call(d, job["id"], "shared", edit([{"id": "b", "pages": [1], "markdown": f"[page]({source['asset_path']})"}]))
    assert result["ok"], result
    asset = d.documents.version(job["id"], result["data"]["version_id"])["assets"][source["asset_path"]]
    assert asset["ref"] == source["ref"] and asset["provenance"].get("purpose") is None


def test_exported_zip_relocates_with_working_relative_links(setup, tmp_path):
    store, job = setup
    d = Dispatcher(store)
    link = d.evidence.render_page(job["id"], 1, 50)
    embed = d.evidence.render_page(job["id"], 1, 72)
    version = call(d, job["id"], "save", edit([{"id": "b", "pages": [1],
                   "markdown": f"[Page 1]({link['asset_path']})\n\n![Figure]({embed['asset_path']})"}]))["data"]["version_id"]
    head = store.get("job", job["id"])["head"]
    call(d, job["id"], "later", {**edit(), "base_version": head, "expected_head": head})
    archive = tmp_path / "delivery.zip"
    requests_before = len(store.records("request", job["id"]))
    receipt = d.documents.export(job["id"], version, str(archive))
    assert receipt["verified"] and len(store.records("request", job["id"])) == requests_before
    target = tmp_path / "elsewhere" / "extracted"
    with zipfile.ZipFile(archive) as zipped:
        assert set(zipped.namelist()) == saved_files(d, job["id"], version)
        for name in zipped.namelist():
            assert zipped.read(name) == (d.documents.root / version / name).read_bytes()
        zipped.extractall(target)
    markdown = (target / "document.md").read_text("utf-8")
    html = (target / "preview.html").read_text("utf-8")
    for image in (link, embed):
        assert image["asset_path"] in markdown and image["asset_path"] in html
        assert (target / image["asset_path"]).read_bytes() == store.bytes(image["ref"], job["id"])
    assert "pdfmd-preview:" not in markdown + html and "pdfmd-resource-" not in markdown + html


@pytest.mark.parametrize("citation", ["appendix/100%-coverage.md", "notes/%ZZ.md", "ref/%FF.html", "50%"])
def test_ordinary_citations_with_malformed_escapes_do_not_block_save(setup, citation):
    store, job = setup
    d = Dispatcher(store)
    image = d.evidence.render_page(job["id"], 1, 50)
    text = f"[Page 1]({image['asset_path']}) — see [coverage]({citation})."
    assert classify(citation, "hyperlink") == ("unrelated", None)
    result = call(d, job["id"], "citation", edit([{"id": "b", "pages": [1], "markdown": text}]))
    assert result["ok"], result
    saved = d.documents.version(job["id"], result["data"]["version_id"])
    assert set(saved["assets"]) == {image["asset_path"]} and saved["content"]["blocks"][0]["markdown"] == text


@pytest.mark.parametrize("destination", ["assets/100%-coverage.png", "assets/%GG.png", "assets/%FF.png", "x%2Fassets%2F%GG.png",
                                         "ASSETS/a%ZZ.png", "notes/assets/%ZZ.png"])
def test_malformed_reserved_asset_paths_still_reject(setup, destination):
    store, job = setup
    d = Dispatcher(store)
    assert classify(destination, "hyperlink")[0] == "invalid" and classify(destination, "image")[0] == "invalid"
    assert classify("figures/100%.png", "image")[0] == "invalid"
    assert_rejected(d, job["id"], "reserved", edit([{"id": "b", "pages": [1], "markdown": f"[bad]({destination})"}]), None,
                    "exact registered asset URI", destination)


@pytest.mark.parametrize("target", ["asset", "original"])
def test_corrupt_dependency_names_the_reference_and_publishes_nothing(tmp_path, target):
    store = Store(tmp_path / "workspace")
    d = Dispatcher(store)
    job = d.evidence.create_job(str(FIXTURES / "rgb-smask.pdf"), "Preserve the source image.")["id"]
    import pymupdf
    with pymupdf.open(FIXTURES / "rgb-smask.pdf") as pdf:
        xref = pdf[0].get_images(full=True)[0][0]
    image = d.evidence.extract_image(job, 1, xref)
    ref = image["ref"] if target == "asset" else image["originals"][0]["ref"]
    obj = store.root / "objects" / store.get("blob", ref, job=job)["sha256"]
    obj.write_bytes(obj.read_bytes() + b"corrupt")
    before = set((store.root / "versions").iterdir())
    result = assert_rejected(d, job, "corrupt", edit([{"id": "b", "pages": [1], "markdown": f"[Figure]({image['asset_path']})"}]), None,
                             "failed its integrity check", image["asset_path"], "hyperlink", "block b", "Regenerate the source evidence", "retry the retained candidate")
    assert ("registered image file" if target == "asset" else "retained original stream") in result["data"]["error"]
    assert set((store.root / "versions").iterdir()) == before

def smask_job(tmp_path):
    import pymupdf
    store = Store(tmp_path / "workspace")
    d = Dispatcher(store)
    job = d.evidence.create_job(str(FIXTURES / "rgb-smask.pdf"), "Preserve the source image.")["id"]
    with pymupdf.open(FIXTURES / "rgb-smask.pdf") as pdf:
        xref = pdf[0].get_images(full=True)[0][0]
    return store, d, job, xref


def reuse(candidate_ref):
    return {"base_version": None, "expected_head": None, "reuse_candidate": {"ref": candidate_ref},
            "page_updates": {"1": {"printed": "none", "disposition": "included"}}}


@pytest.mark.parametrize("target", ["render", "extracted", "original"])
@pytest.mark.parametrize("damage", ["append", "same-length", "deleted"])
def test_regenerating_identical_evidence_restores_object_and_retained_candidate_saves(tmp_path, target, damage):
    store, d, job, xref = smask_job(tmp_path)
    image = d.evidence.render_page(job, 1, 50) if target == "render" else d.evidence.extract_image(job, 1, xref)
    ref = image["originals"][0]["ref"] if target == "original" else image["ref"]
    record = store.get("blob", ref, job=job)
    obj = store.root / "objects" / record["sha256"]
    good = obj.read_bytes()
    if damage == "append":
        obj.write_bytes(good + b"corrupt")
    elif damage == "same-length":
        obj.write_bytes(bytes([good[0] ^ 0xFF]) + good[1:])
    else:
        obj.unlink()
    rejected = assert_rejected(d, job, "first", edit([{"id": "b", "pages": [1], "markdown": f"[Figure]({image['asset_path']})"}]),
                               None, image["asset_path"], "Regenerate the source evidence")
    again = d.evidence.render_page(job, 1, 50) if target == "render" else d.evidence.extract_image(job, 1, xref)
    assert again["asset_path"] == image["asset_path"]
    assert obj.read_bytes() == good
    result = call(d, job, "retry", reuse(rejected["candidate_ref"]))
    assert result["ok"], result
    version = result["data"]["version_id"]
    saved = d.documents.version(job, version)
    assert (d.documents.root / version / image["asset_path"]).read_bytes() == store.bytes(again["ref"], job)
    for path, original in saved["originals"].items():
        assert (d.documents.root / version / path).read_bytes() == store.bytes(original["ref"], job)
    assert not list((store.root / "objects").glob(".*.tmp"))


def test_missing_original_record_names_reference_and_reextraction_recovers(tmp_path):
    store, d, job, xref = smask_job(tmp_path)
    image = d.evidence.extract_image(job, 1, xref)
    with store.transaction() as db:
        db.execute("DELETE FROM records WHERE kind='blob' AND id=?", (image["originals"][0]["ref"],))
    rejected = assert_rejected(d, job, "first", edit([{"id": "b", "pages": [1], "markdown": f"[Figure]({image['asset_path']})"}]),
                               None, "retained original stream record", image["asset_path"], "hyperlink", "block b",
                               "Regenerate the source evidence")
    assert image["originals"][0]["ref"] not in rejected["data"]["error"]
    d.evidence.extract_image(job, 1, xref)
    result = call(d, job, "retry", reuse(rejected["candidate_ref"]))
    assert result["ok"], result
    assert len(d.documents.version(job, result["data"]["version_id"])["originals"]) == 2


def test_store_blob_never_replaces_an_intact_object(tmp_path):
    store = Store(tmp_path / "workspace")
    record = store.blob("job", "image", b"exact bytes")
    obj = store.root / "objects" / record["sha256"]
    before = obj.stat().st_mtime_ns
    store.blob("job", "image", b"exact bytes")
    assert obj.stat().st_mtime_ns == before and obj.read_bytes() == b"exact bytes"

def test_store_restore_cleans_stage_on_write_failure_and_keeps_original_error(tmp_path, monkeypatch):
    import pdfmd.storage as storage_module
    store = Store(tmp_path / "workspace")
    record = store.blob("job", "image", b"exact bytes")
    obj = store.root / "objects" / record["sha256"]
    obj.write_bytes(b"corrupt!!!!")

    def failing_fsync(fd):
        raise OSError("injected fsync failure")
    monkeypatch.setattr(storage_module.os, "fsync", failing_fsync)
    with pytest.raises(OSError, match="injected fsync failure"):
        store.blob("job", "image", b"exact bytes")
    assert obj.read_bytes() == b"corrupt!!!!"
    assert not list((store.root / "objects").glob(".*.tmp"))
    monkeypatch.undo()
    store.blob("job", "image", b"exact bytes")
    assert obj.read_bytes() == b"exact bytes"


@pytest.mark.parametrize("winner", [True, False])
def test_store_restore_replace_failure_accepts_concurrently_restored_target(tmp_path, monkeypatch, winner):
    import pdfmd.storage as storage_module
    store = Store(tmp_path / "workspace")
    record = store.blob("job", "image", b"exact bytes")
    obj = store.root / "objects" / record["sha256"]
    obj.write_bytes(b"corrupt!!!!")
    real_replace = storage_module.os.replace

    def blocked_replace(src, dst):
        if winner:  # another repair finished first, then a reader blocked our replace
            Path(dst).write_bytes(b"exact bytes")
        raise PermissionError("injected sharing violation")
    monkeypatch.setattr(storage_module.os, "replace", blocked_replace)
    if winner:
        assert store.blob("job", "image", b"exact bytes")["sha256"] == record["sha256"]
        assert obj.read_bytes() == b"exact bytes"
    else:
        with pytest.raises(ValueError, match="close readers and retry") as error:
            store.blob("job", "image", b"exact bytes")
        assert isinstance(error.value.__cause__, PermissionError)
        assert obj.read_bytes() == b"corrupt!!!!"
    assert not list((store.root / "objects").glob(".*.tmp"))
    monkeypatch.setattr(storage_module.os, "replace", real_replace)