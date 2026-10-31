"""Version visibility is a catalog commit, independent of directory renaming."""
import ctypes
import json
import os
import sys
import zipfile

import pytest

from pdfmd.documents import Documents
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher
from tests.engine.documents.test_documents import call, edit


@pytest.mark.skipif(sys.platform != "win32", reason="Windows delete-sharing boundary")
def test_save_edit_reopen_export_with_reader_denying_delete(setup, tmp_path, monkeypatch):
    store, job = setup
    dispatcher = Dispatcher(store)
    image = dispatcher.evidence.render_page(job["id"], 1, 72)
    arguments = edit([
        {"id": "body", "pages": [1], "markdown": "Keep 25 mg; do not change μg or e\u0301."},
        {"id": "image", "pages": [1], "markdown": f"![source]({image['asset_path']})"},
    ])
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
    kernel.CreateFileW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.restype = ctypes.c_int
    handles = {}
    fsync = os.fsync

    def observe_readers(fd):
        fsync(fd)
        for path in dispatcher.documents.root.glob("*/document.md"):
            if path in handles:
                continue
            # Model a concurrent reader, not a claim about the old OS cause.
            handle = kernel.CreateFileW(str(path), 0x80000000, 0x1 | 0x2,
                None, 3, 0x80, None)  # OPEN_EXISTING, READ/WRITE sharing, no DELETE
            if handle == ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            handles[path] = handle
            version = path.parent.name.removeprefix(".prepared-")
            assert store.maybe("version", version) is None
            with pytest.raises(ValueError, match="Unknown version"):
                Documents(Store(store.root)).version(job["id"], version)

    monkeypatch.setattr(os, "fsync", observe_readers)
    try:
        first = call(dispatcher, job["id"], "first", arguments)
        assert first["ok"], first
        one = first["data"]["version_id"]
        changed = {"base_version": one, "expected_head": one,
            "operations": [{"kind": "insert", "after_id": "image", "blocks": [
                {"id": "end", "pages": [1], "markdown": "Saved after the first version."}]}]}
        second = call(dispatcher, job["id"], "second", changed)
        assert second["ok"], second
        two = second["data"]["version_id"]
        assert len(handles) == 2  # Readers remain open throughout save and export.
        reopened_store = Store(store.root)
        reopened = Dispatcher(reopened_store)
        assert call(reopened, job["id"], "first", arguments) == first
        assert reopened_store.get("job", job["id"])["head"] == two
        for version in (one, two):
            saved = reopened.documents.version(job["id"], version)
            archive = tmp_path / f"{version}.zip"
            assert reopened.documents.export(job["id"], version, str(archive))["verified"]
            with zipfile.ZipFile(archive) as zipped:
                assert json.loads(zipped.read("document.json")) == saved
                assert zipped.read(image["asset_path"]) == store.bytes(image["ref"], job["id"])
                for name in reopened_store.get("version", version)["files"]:
                    assert zipped.read(name) == (reopened.documents.root / version / name).read_bytes()
            assert saved["content"]["blocks"][0] == {**arguments["replace_blocks"][0], "source_note": ""}
        assert store.bytes(job["source_ref"], job["id"]) == (tmp_path / "source.pdf").read_bytes()
    finally:
        for handle in handles.values():
            assert kernel.CloseHandle(handle)


@pytest.mark.parametrize("failure", ["file_flush", "catalog_commit"])
def test_unregistered_files_remain_invisible_after_failure(setup, monkeypatch, failure):
    store, job = setup
    dispatcher = Dispatcher(store)
    first = call(dispatcher, job["id"], "first", edit())
    assert first["ok"], first
    one = first["data"]["version_id"]
    original = {p.relative_to(dispatcher.documents.root / one): p.read_bytes()
        for p in (dispatcher.documents.root / one).rglob("*") if p.is_file()}
    arguments = {"base_version": one, "expected_head": one, "title": "Next draft"}
    digest, candidate = dispatcher.capture(job["id"], "interrupted", "edit_document", json.dumps(arguments))
    # Direct core entry lets a failed transaction remain an unsettled operation,
    # rather than testing Dispatcher's separately covered failure projection.
    with monkeypatch.context() as injected:
        if failure == "file_flush":
            fsync = os.fsync
            def fail_flush(fd):
                if any(p.name != one for p in dispatcher.documents.root.iterdir()):
                    raise OSError("injected file flush failure")
                fsync(fd)
            injected.setattr(os, "fsync", fail_flush)
        else:
            put_tx = store.put_tx
            def fail_commit(db, kind, key, identity, value):
                if kind == "operation" and key == "interrupted":
                    raise OSError("injected catalog commit failure")
                put_tx(db, kind, key, identity, value)
            injected.setattr(store, "put_tx", fail_commit)
        with pytest.raises(OSError, match="injected"):
            dispatcher.documents.edit(job["id"], "interrupted", arguments, digest, candidate["ref"])
    retained = [p for p in dispatcher.documents.root.iterdir() if p.name != one]
    assert len(retained) == 1 and list(retained[0].iterdir())
    retained_bytes = {p: p.read_bytes() for p in retained[0].rglob("*") if p.is_file()}
    reopened = Dispatcher(Store(store.root))
    assert reopened.store.get("job", job["id"])["head"] == one
    assert [v["id"] for v in reopened.store.records("version", job["id"])] == [one]
    assert reopened.store.maybe("operation", "interrupted") is None
    with pytest.raises(ValueError, match="Unknown version"):
        reopened.documents.version(job["id"], retained[0].name)
    assert reopened.store.bytes(candidate["ref"], job["id"]) == json.dumps(arguments).encode()
    repaired = call(reopened, job["id"], "new-choice", arguments)
    assert repaired["ok"], repaired
    assert all(path.read_bytes() == data for path, data in retained_bytes.items())
    assert all((dispatcher.documents.root / one / path).read_bytes() == data for path, data in original.items())


def test_existing_version_directory_is_never_overwritten(setup, monkeypatch):
    store, job = setup
    dispatcher = Dispatcher(store)
    version = "a" * 32
    occupied = dispatcher.documents.root / version
    occupied.mkdir()
    sentinel = occupied / "document.md"
    sentinel.write_bytes(b"Useful unregistered work")
    monkeypatch.setattr("pdfmd.documents.uid", lambda: version)
    result = call(dispatcher, job["id"], "collision", edit())
    assert not result["ok"], result
    assert sentinel.read_bytes() == b"Useful unregistered work"
    assert store.get("job", job["id"])["head"] is None
    assert not store.records("version", job["id"])
    assert store.bytes(result["candidate_ref"], job["id"])
