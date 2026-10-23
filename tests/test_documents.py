import json
import zipfile

import pytest

from pdfmd.documents import Documents
from pdfmd.tools import Dispatcher


def edit(blocks=None):
    return {"base_version": None, "expected_head": None,
            "replace_blocks": blocks or [{"id": "body", "pages": [1], "markdown": "本文件 **25 mg** / μg / e\u0301"}],
            "page_updates": {"1": {"printed": "none", "disposition": "included"}}}


def call(dispatcher, job, op, data):
    return dispatcher.execute(job, op, "edit_document", json.dumps(data, ensure_ascii=False))


def test_rejected_candidate_reused_exactly_and_replayed_after_new_head(setup):
    store, job = setup
    d = Dispatcher(store)
    bad = edit()
    bad["page_updates"]["2"] = {"printed": "none"}
    result = call(d, job["id"], "bad", bad)
    assert not result["ok"]
    assert store.get("job", job["id"])["head"] is None
    repaired = {"base_version": None, "expected_head": None, "reuse_candidate": {"ref": result["candidate_ref"]},
                "page_updates": {"1": {"printed": "none", "disposition": "included"}}}
    first = call(d, job["id"], "fix", repaired)
    one = first["data"]["version_id"]
    content = d.documents.version(job["id"], one)["content"]
    assert content["blocks"][0]["markdown"] == bad["replace_blocks"][0]["markdown"]
    patch = {"base_version": one, "expected_head": one, "page_updates": {"1": {"printed": "iii"}},
             "operations": [{"kind": "insert", "after_id": "body", "blocks": [{"id": "end", "pages": [1], "markdown": "End."}]}]}
    two = call(d, job["id"], "append", patch)["data"]["version_id"]
    assert call(d, job["id"], "fix", repaired) == first
    assert store.get("job", job["id"])["head"] == two
    assert d.documents.version(job["id"], two)["content"]["blocks"][0] == content["blocks"][0]
    page = d.documents.version(job["id"], two)["content"]["pages"]["1"]
    assert page["printed"] == "iii" and page["disposition"] == "included"
    stale = call(d, job["id"], "stale", patch)
    assert not stale["ok"] and store.get("job", job["id"])["head"] == two


def test_whole_document_render_export_and_exact_patch(setup, tmp_path):
    store, job = setup
    d = Dispatcher(store)
    args = edit([{"id": "first", "pages": [1], "markdown": "[link][target] with a note[^n]."},
                 {"id": "definitions", "pages": [1], "markdown": "[target]: https://example.com\n\n[^n]: Footnote."}])
    one = call(d, job["id"], "save", args)["data"]["version_id"]
    html = (d.documents.root / one / "preview.html").read_text("utf-8")
    assert 'href="https://example.com"' in html and "Footnote." in html
    patch = {"base_version": one, "expected_head": one,
             "operations": [{"kind": "patch", "id": "first", "start": 0, "end": 6, "expected": "wrong!", "text": "new"}]}
    assert not call(d, job["id"], "wrong", patch)["ok"]
    archive = tmp_path / "delivery.zip"
    receipt = d.documents.export(job["id"], one, str(archive))
    assert receipt["verified"] and receipt["claim"] == "partial"
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            assert z.read(name) == (d.documents.root / one / name).read_bytes()
    assert d.documents.export(job["id"], one, str(archive)) == receipt
    archive.write_bytes(b"unrelated")
    with pytest.raises((ValueError, zipfile.BadZipFile)):
        d.documents.export(job["id"], one, str(archive))
    assert archive.read_bytes() == b"unrelated"


def test_source_image_bytes_in_explicit_version_export(setup, tmp_path):
    store, job = setup
    d = Dispatcher(store)
    image = d.evidence.render_page(job["id"], 1)
    args = edit([{"id": "figure", "pages": [1], "markdown": f"![Source]({image['asset_path']})"}])
    one = call(d, job["id"], "image-save", args)["data"]["version_id"]
    archive = tmp_path / "image.zip"
    d.documents.export(job["id"], one, str(archive))
    with zipfile.ZipFile(archive) as z:
        assert z.read(image["asset_path"]) == store.bytes(image["ref"], job["id"])


def test_result_blob_reconciles_before_operation_pointer_commit(setup, monkeypatch):
    store, job = setup
    dispatcher = Dispatcher(store)
    original = store.put
    injected = []

    def fail_pointer(kind, key, owner, value):
        if kind == "operation" and value["status"] == "done" and not injected:
            injected.append(True)
            raise RuntimeError("injected receipt gap")
        return original(kind, key, owner, value)

    monkeypatch.setattr(store, "put", fail_pointer)
    with pytest.raises(RuntimeError):
        dispatcher.execute(job["id"], "inspect", "inspect_pdf", '{}')
    blobs = len(store.records("blob", job["id"]))
    recovered = dispatcher.execute(job["id"], "inspect", "inspect_pdf", '{}')
    assert recovered["ok"]
    assert len(store.records("blob", job["id"])) == blobs
