import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pdfmd.evidence import Evidence
from pdfmd.asset_catalog import record_json
from pdfmd.server import Engine, create_app
from pdfmd.storage import InvalidUnicode, Store, encode
from pdfmd.tools import Dispatcher
from tests.engine.documents.test_documents import edit


@pytest.mark.parametrize("suffix,body", [
    ("", {"path": "source.pdf", "scope": "A\ud800C"}),
    ("", {"path": "bad\ud800.pdf", "scope": "all"}),
    ("/task/start", {"amendment": "A\ud800C"}),
    ("/task/settings", {"route": {"parameters": {"value": "A\ud800C"}}}),
    ("/task/edit", {**edit(), "title": "A\ud800C"}),
    ("/task/export", {"version_id": "version", "destination": "bad\ud800.zip"}),
    ("/task/accepted-evidence-resolution", {"request": "request", "basis": "A\ud800C"}),
    ("", {"path": [], "scope": "A\ud800C"}),
])
def test_api_rejects_unicode_before_validation_or_writes(tmp_path, source, suffix, body):
    with TestClient(create_app(tmp_path / "api", "local"), headers={"Authorization": "Bearer local"}) as client:
        job = client.post("/jobs", json={"path": str(source), "scope": "all"}).json()["id"]
        store = client.app.state.engine.store
        before = store.get("job", job)
        objects = set((store.root / "objects").iterdir())
        response = client.post("/jobs" + suffix.replace("/task", "/" + job), content=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
        assert response.status_code == 400, response.text
        assert "U+D800" in response.json()["error"] and "character offset" in response.json()["error"]
        assert store.records("job") == [before]
        assert set((store.root / "objects").iterdir()) == objects
        assert client.post(f"/jobs/{job}/settings", json={"limits": {"max_requests": 5}}).status_code == 200


def test_direct_user_input_and_paths_reject_before_state_changes(setup, source):
    store, job = setup
    before = store.get("job", job["id"])
    for changes in [{"scope": "A\ud800C"}, {"path": "bad\ud800.pdf"}, {"path": Path("bad\ud800.pdf")}]:
        with pytest.raises(InvalidUnicode, match=r"U\+D800"):
            Evidence(store).create_job(**{"path": str(source), "scope": "all", **changes})
    engine = Engine(store.root)
    try:
        with pytest.raises(InvalidUnicode, match="amendment"):
            engine.start(job["id"], "offline", amendment="A\ud800C")
        with pytest.raises(InvalidUnicode, match="parameters"):
            engine.configure(job["id"], route={"parameters": {"value": "A\ud800C"}})
        assert not (store.root / f"task-{job['id']}.lock").exists()
        with pytest.raises(InvalidUnicode, match="export destination"):
            engine.documents.export(job["id"], "not-a-version", "bad\ud800.zip")
        with pytest.raises(InvalidUnicode, match="document edit"):
            engine.documents.edit(job["id"], "direct", {"title": "A\ud800C"}, "hash", "candidate")
        with pytest.raises(InvalidUnicode, match="script code"):
            Dispatcher(store, scripts=True).script(job["id"], "direct-script", "A\ud800C")
        assert store.get("job", job["id"]) == before
        assert engine.configure(job["id"], limits={"max_requests": 5})["limits"]["max_requests"] == 5
    finally:
        engine.close()


def test_persistence_rejection_is_atomic_and_valid_non_bmp_stays_exact(setup):
    store, job = setup
    original = {"text": "A\udfffC"}
    with pytest.raises(InvalidUnicode, match=r"U\+DFFF.*character offset 1"):
        encode(original)
    with pytest.raises(InvalidUnicode):
        store.put("test", "invalid", job["id"], original)
    before = set((store.root / "objects").iterdir())
    with pytest.raises(InvalidUnicode, match="blob metadata"):
        store.blob(job["id"], "script_output", b"preserved bytes", {"filename": "bad\ud800.txt"})
    assert set((store.root / "objects").iterdir()) == before
    assert not store.maybe("test", "invalid") and original["text"] == "A\udfffC"
    text = json.loads('"\\ud83d\\ude00 \\ud840\\udc00"')
    store.put("test", "valid", job["id"], {"text": text})
    assert Store(store.root).get("test", "valid")["text"] == "😀 𠀀" == text


@pytest.mark.parametrize("producer", ["json_key", "record_identity", "event", "file_metadata", "catalog", "store_path"])
def test_direct_persistence_boundaries_name_field_and_offset(setup, tmp_path, producer):
    store, job = setup
    actions = {
        "json_key": lambda: encode({"A\ud800C": 1}),
        "record_identity": lambda: store.put("test", "A\ud800C", job["id"], {}),
        "event": lambda: store.event(job["id"], "A\ud800C", {}),
        "file_metadata": lambda: store.blob_from_file(job["id"], "source", tmp_path / "absent", {"filename": "A\ud800C"}),
        "catalog": lambda: record_json({"caption": "A\ud800C"}),
        "store_path": lambda: Store(tmp_path / "A\ud800C"),
    }
    with pytest.raises(InvalidUnicode, match=r"U\+D800.*character offset"):
        actions[producer]()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows wide filename path")
def test_discovered_script_filename_surrogate_rejects_without_renaming(setup):
    store, job = setup
    d = Dispatcher(store, scripts=True)
    code = "from pathlib import Path\nPath('file' + chr(0xd800) + '.txt').write_bytes(b'original')\n"
    result = d.execute(job["id"], "filename", "run_script", json.dumps({"code": code}))
    assert not result["ok"] and "U+D800" in result["data"]["error"]
    files = list((store.root / "processes").rglob("file*.txt"))
    assert len(files) == 1 and files[0].name == "file\ud800.txt" and files[0].read_bytes() == b"original"
    assert len([b for b in store.records("blob", job["id"]) if b["kind"] == "process_log"]) == 2


def test_api_valid_surrogate_pairs_save_reopen_and_export_exactly(tmp_path, source):
    text = "😀 𠀀"
    with TestClient(create_app(tmp_path / "api", "local"), headers={"Authorization": "Bearer local"}) as client:
        imported = client.post("/jobs", content=json.dumps({"path": str(source), "scope": text}).encode(),
                               headers={"Content-Type": "application/json"})
        assert imported.status_code == 200, imported.text
        job = imported.json()["id"]
        data = {**edit(), "replace_blocks": [{"id": "body", "pages": [1], "markdown": text}]}
        result = client.post(f"/jobs/{job}/edit", content=json.dumps(data).encode(),
                             headers={"Content-Type": "application/json"})
        assert result.status_code == 200 and result.json()["ok"]
        version = result.json()["data"]["version_id"]
        d = Dispatcher(Store(client.app.state.engine.store.root))
        assert d.documents.version(job, version)["content"]["blocks"][0]["markdown"] == text
        exported = client.post(f"/jobs/{job}/export", json={"version_id": version, "destination": str(tmp_path / "emoji.zip")})
        assert exported.status_code == 200 and exported.json()["verified"]
