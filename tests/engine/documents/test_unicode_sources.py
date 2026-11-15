from hashlib import sha256
import json

import pymupdf
import pytest

from pdfmd.storage import InvalidUnicode, Store
from pdfmd.tools import Dispatcher
from tests.engine.documents.test_documents import edit


def surrogate_pdf(path):
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((72, 72), "ABC")
        xref = pdf.get_new_xref()
        pdf.update_object(xref, "<<>>")
        pdf.update_stream(xref, b"/CIDInit /ProcSet findresource begin 12 dict begin begincmap "
            b"/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def "
            b"/CMapName /BadUnicode def /CMapType 2 def 1 begincodespacerange <00> <FF> "
            b"endcodespacerange 1 beginbfchar <42> <D800> endbfchar "
            b"endcmap CMapName currentdict /CMap defineresource pop end end")
        pdf.xref_set_key(page.get_fonts()[0][0], "ToUnicode", f"{xref} 0 R")
        raw = pdf.tobytes()
    path.write_bytes(raw)
    return raw


@pytest.mark.parametrize("mode", ["text", "blocks", "words", "dict", "rawdict"])
def test_pdf_surrogate_is_reported_before_upstream_substitution(tmp_path, mode):
    source = tmp_path / "surrogate.pdf"
    original = surrogate_pdf(source)
    store = Store(tmp_path / "store")
    d = Dispatcher(store)
    job = d.evidence.create_job(str(source), "all")["id"]
    result = d.execute(job, "inspect", "inspect_pdf", json.dumps({"pages": [1], "mode": mode}))
    assert not result["ok"]
    message = result["data"]["error"]
    assert "U+D800" in message and "PDF page 1" in message and "character offset 1" in message
    assert "\ufffd" not in message
    assert source.read_bytes() == original == d.evidence.source(job)
    assert d.execute(job, "render", "render_page", '{"page":1,"dpi":72}')["ok"]
    assert not [b for b in store.records("blob", job) if b["kind"] == "evidence"]


def test_ocr_json_surrogate_reports_page_and_field_and_keeps_bytes(setup, monkeypatch):
    store, task = setup
    d = Dispatcher(store)
    original = b'{"text":"A\\ud800C","blocks":[]}'
    monkeypatch.setenv("PDFMD_OCR_WORKER", "offline-worker")
    monkeypatch.setenv("PDFMD_NODE", "offline-node")
    def process(job, operation, command, directory, timeout, env):
        (directory / "result.json").write_bytes(original)
        out, err = directory / "stdout.log", directory / "stderr.log"
        out.write_bytes(b"complete stdout")
        err.write_bytes(b"complete stderr")
        return 0, out, err
    monkeypatch.setattr(d, "process", process)
    result = d.execute(task["id"], "ocr", "ocr_page", '{"page":1,"languages":"eng"}')
    assert not result["ok"]
    assert "OCR page 1['text']" in result["data"]["error"]
    assert "character offset 1" in result["data"]["error"]
    directory = store.root / "processes" / sha256(b"ocr").hexdigest()
    assert (directory / "result.json").read_bytes() == original
    assert {store.bytes(b["ref"], task["id"]) for b in store.records("blob", task["id"])
            if b["kind"] == "process_log"} == {b"complete stdout", b"complete stderr"}
    assert d.execute(task["id"], "retry-inspection", "inspect_pdf", '{"pages":[1]}')["ok"]


def test_script_json_output_and_arguments_are_rejected_without_changing_originals(setup):
    store, task = setup
    d = Dispatcher(store, scripts=True)
    code = "from pathlib import Path\nPath('output.json').write_bytes(b'{\"text\":\"A\\\\ud800C\"}')\n"
    result = d.execute(task["id"], "script", "run_script", json.dumps({"code": code}))
    assert result["ok"]
    [output] = result["data"]["files"]
    original = store.bytes(output["ref"], task["id"])
    read = d.execute(task["id"], "read", "read_evidence", json.dumps({"ref": output["ref"]}))
    assert not read["ok"] and "U+D800" in read["data"]["error"]
    with pytest.raises(InvalidUnicode, match=r"\['text'\].*character offset 1"):
        store.json(output["ref"], task["id"])
    raw = d.evidence.read(task["id"], output["ref"], view="raw")
    assert raw["encoding"] == "base64" and store.bytes(output["ref"], task["id"]) == original
    arguments = json.dumps({"state": "waiting", "message": "A\ud800C"})
    rejected = d.execute(task["id"], "bad-arguments", "report", arguments)
    assert not rejected["ok"] and "character offset 1" in rejected["data"]["error"]
    assert store.bytes(rejected["candidate_ref"], task["id"]) == arguments.encode()
    assert d.execute(task["id"], "good", "inspect_pdf", '{"pages":[1]}')["ok"]


def test_rejected_argument_candidate_cannot_bypass_check_by_reuse(setup):
    store, task = setup
    d = Dispatcher(store)
    arguments = json.dumps(edit([{"id": "body", "pages": [1], "markdown": "A\ud800C"}]))
    first = d.execute(task["id"], "bad-edit", "edit_document", arguments)
    assert not first["ok"]
    reuse = d.execute(task["id"], "reuse", "edit_document", json.dumps({
        "base_version": None, "expected_head": None, "reuse_candidate": {"ref": first["candidate_ref"]},
        "page_updates": {"1": {"printed": "none", "disposition": "included"}}}))
    assert not reuse["ok"] and "['markdown']" in reuse["data"]["error"]
    assert store.get("job", task["id"])["head"] is None
    assert store.bytes(first["candidate_ref"], task["id"]) == arguments.encode()
    assert d.execute(task["id"], "valid-edit", "edit_document", json.dumps(edit()))["ok"]
