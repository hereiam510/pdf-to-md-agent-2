"""Exact access describes what was returned, not inferred source coverage."""
import base64
from hashlib import sha256
import json

import pytest

from pdfmd.documents import Documents
from pdfmd.evidence import Evidence
from pdfmd.schema import pointer
from pdfmd.storage import encode
from pdfmd.tools import Dispatcher


def saved_document(store, job):
    blocks = [{"id": f"block-{i}", "pages": [1], "markdown": f"{i}: 原文 μg / e\u0301 / **exact**"}
              for i in range(12)]
    dispatcher = Dispatcher(store)
    saved = dispatcher.execute(job["id"], "access-save", "edit_document", json.dumps({
        "base_version": None, "expected_head": None, "replace_blocks": blocks,
        "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "complete"}, ensure_ascii=False))
    assert saved["ok"]
    version = saved["data"]["version_id"]
    body = dispatcher.documents.version(job["id"], version)
    ref = store.blob(job["id"], "document_view", body, {"version": version})["ref"]
    return dispatcher, version, body, ref


def test_root_target_selection_and_selected_size_are_independent(setup):
    store, job = setup
    dispatcher, version, body, ref = saved_document(store, job)
    reader = dispatcher.evidence
    full = reader.read(job["id"], ref)
    assert full["version_id"] == version
    assert reader.read(job["id"], ref, view="index")["version_id"] == version
    assert reader.read(job["id"], ref, view="raw", start=0, end=5)["version_id"] == version
    assert full["value"] == body
    assert full["completeness"] == {"root": True, "target": True, "selection": True}
    assert full["returned_bytes"] == len(encode(body))

    for args in ({}, {"start": 0, "end": 12}):
        all_blocks = reader.read(job["id"], ref, json_pointer="/content/blocks", **args)
        assert all_blocks["value"] == body["content"]["blocks"]
        assert all_blocks["total"] == 12 and not all_blocks["complete"]
        assert all_blocks["completeness"] == {"root": False, "target": True, "selection": True}
    selected = reader.read(job["id"], ref, json_pointer="/content/blocks", start=11, end=12)
    assert selected["version_id"] == version
    assert selected["value"] == body["content"]["blocks"][11:12]
    assert selected["total"] == 12 and selected["range"] == [11, 12]
    assert selected["completeness"] == {"root": False, "target": False, "selection": True}
    assert selected["original_bytes"] == full["original_bytes"] == store.get("blob", ref)["bytes"]
    assert selected["returned_bytes"] == len(encode(selected["value"])) < full["returned_bytes"]
    assert store.get("job", job["id"])["head"] == version
    assert store.bytes(ref, job["id"]) == encode(body)


def test_string_scalar_and_explicit_complete_root_range(setup):
    store, job = setup
    reader = Evidence(store)
    text = "原文 μg / e\u0301 / 🙂"
    ref = store.blob(job["id"], "evidence", {"text": text, "count": 3, "nil": None})["ref"]
    selected = reader.read(job["id"], ref, json_pointer="/text", start=0, end=len(text))
    assert selected["value"] == text and selected["total"] == len(text)
    assert selected["returned_bytes"] == len(text.encode("utf-8"))
    assert selected["completeness"] == {"root": False, "target": True, "selection": True}
    partial = reader.read(job["id"], ref, json_pointer="/text", start=1, end=4)
    assert partial["value"] == text[1:4]
    assert partial["completeness"] == {"root": False, "target": False, "selection": True}
    for path, expected in (("/count", 3), ("/nil", None)):
        result = reader.read(job["id"], ref, json_pointer=path)
        assert result["value"] == expected and result["total"] is None and result["unit"] is None
        assert result["completeness"] == {"root": False, "target": True, "selection": True}
    for value in (["one", "two"], "", text):
        root = store.blob(job["id"], "evidence", encode(value))["ref"]
        result = reader.read(job["id"], root, start=0, end=len(value))
        assert result["value"] == value and result["complete"]
        assert result["completeness"] == {"root": True, "target": True, "selection": True}


def test_document_index_paths_bind_to_exact_version_without_mutation(setup):
    store, job = setup
    dispatcher, version, body, ref = saved_document(store, job)
    docs = dispatcher.documents
    before = {p.name: sha256(p.read_bytes()).hexdigest() for p in (docs.root / version).iterdir() if p.is_file()}
    index = docs.index(job["id"], version)
    assert index["completeness"] == {"root": False, "target": False, "selection": True}
    value = index["value"]
    assert value["version_id"] == version and value["source_ref"] == job["source_ref"]
    assert value["block_count"] == 12 and "content" in value["keys"] and "blocks" in value["content_keys"]
    for entry, block in zip(value["blocks"], body["content"]["blocks"], strict=True):
        assert pointer(body, entry["pointer"]) == block
        assert pointer(body, entry["markdown_pointer"]) == block["markdown"]
        assert entry["markdown_characters"] == len(block["markdown"])
        assert entry["markdown_utf8_bytes"] == len(block["markdown"].encode("utf-8"))
        assert entry["id"] == block["id"] and entry["pages"] == block["pages"]
    assert index["returned_bytes"] == len(encode(value))
    newer = dispatcher.execute(job["id"], "access-later", "edit_document", json.dumps({
        "base_version": version, "expected_head": version,
        "operations": [{"kind": "delete", "id": "block-11"}]}))["data"]["version_id"]
    assert docs.index(job["id"], version) == index
    assert docs.index(job["id"], newer)["value"]["block_count"] == 11
    assert before == {p.name: sha256(p.read_bytes()).hexdigest() for p in (docs.root / version).iterdir() if p.is_file()}
    assert store.bytes(ref, job["id"]) == encode(body)


def test_errors_identify_saved_wrapper_and_recoverable_selectors(setup):
    store, job = setup
    dispatcher, _, body, ref = saved_document(store, job)
    with pytest.raises(ValueError, match="/content/blocks"):
        dispatcher.evidence.read(job["id"], ref, json_pointer="/blocks", start=11, end=12)
    with pytest.raises(ValueError, match="/content/blocks/0/markdown"):
        dispatcher.evidence.read(job["id"], ref, start=0, end=2000)
    with pytest.raises(ValueError, match="12 items"):
        pointer(body, "/content/blocks/12")
    with pytest.raises(ValueError, match="scalar"):
        pointer(body, "/content/blocks/0/markdown/x")
    assert pointer({"a/b": {"~value": 2}}, "/a~1b/~0value") == 2
    assert pointer({"01": "object key"}, "/01") == "object key"
    for invalid in ("no-leading-slash", "/~2", None):
        with pytest.raises(ValueError):
            pointer(body, invalid)
    for start, end in ((-1, 1), (0, 13), (True, 1), (0, 1.0)):
        with pytest.raises(ValueError, match="selected value"):
            dispatcher.evidence.read(job["id"], ref, json_pointer="/content/blocks", start=start, end=end)


def test_raw_index_and_native_image_have_explicit_representations(setup):
    store, job = setup
    reader = Evidence(store)
    raw = b"\xff\x00\x01abc\x80"
    ref = store.blob(job["id"], "image_stream", raw, {"role": "image"})["ref"]
    for view in ("full", "raw"):
        full = reader.read(job["id"], ref, view=view)
        assert base64.b64decode(full["data"]) == raw
        assert full["completeness"] == {"root": True, "target": True, "selection": True}
        part = reader.read(job["id"], ref, view=view, start=1, end=4)
        assert base64.b64decode(part["data"]) == raw[1:4]
        assert part["returned_bytes"] == 3 and part["original_bytes"] == len(raw)
        assert part["completeness"] == {"root": False, "target": False, "selection": True}
    image = reader.render_page(job["id"], 1)
    pixels = reader.read(job["id"], image["ref"])
    assert pixels["image_ref"] == image["ref"]
    assert pixels["access"]["representation"] == "native_image_reference"
    assert pixels["returned_bytes"] is None
    for item in (ref, image["ref"], store.blob(job["id"], "evidence", {"some": [1, 2, 3]})["ref"]):
        index = reader.read(job["id"], item, view="index")
        assert "image_ref" not in index and "data" not in index and "value" not in index
        assert index["completeness"] == {"root": False, "target": False, "selection": True}
        assert index["original_bytes"] == store.get("blob", item)["bytes"]
    with pytest.raises(ValueError, match="Raw reads"):
        reader.read(job["id"], image["ref"], view="raw", json_pointer="/meta")
    with pytest.raises(ValueError, match="Index returns metadata"):
        reader.read(job["id"], ref, view="index", start=0)
    with pytest.raises(ValueError, match="Native image reads"):
        reader.read(job["id"], image["ref"], end=1)

