"""Synthetic local recovery delivery; never reads a real workspace or credential."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
import zipfile

import pymupdf
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_accepted_evidence_recovery import historical, preserved
from test_continuation import delivery
from test_runtime import tool
from test_response_repairs import native
from test_streaming_delivery import stream_frames
from pdfmd.documents import Documents
from pdfmd.nexus import Nexus
from pdfmd.recovery import inspection
from pdfmd.runtime import Runtime
from pdfmd.storage import Store


def prepare(directory, protocol, endpoint):
    route = {"endpoint": endpoint, "protocol": protocol, "model": "scripted-local-recovery",
             "context_tokens": 65536, "output_tokens": 2048}
    store, job, version, image, source = delivery.__wrapped__(directory, route)
    content = Documents(store).version(job["id"], version)["content"]
    calls = [tool("edit_document", {"base_version": version, "expected_head": version,
             "replace_blocks": content["blocks"], "claim": "complete"}, "saved-edit"),
             tool("report", {"state": "complete", "version_id": version, "message": "Historical completion claim"}, "old-report")]
    with pytest.MonkeyPatch.context() as patch:
        store, job, key, reply, raw = historical((store, job), patch, protocol,
            published=(protocol == "chat_completions"), calls=calls, endpoint=endpoint)
    runtime = Runtime(store, Nexus(store, lambda _: pytest.fail("No provider in fixture preparation")))
    config = {"configurable": {"thread_id": job["id"]}}
    op, call = key + ":0", reply["calls"][0]
    digest, candidate = runtime.dispatcher.capture(job["id"], op, call["name"], call["arguments"])
    result = runtime.dispatcher.documents.edit(job["id"], op, json.loads(call["arguments"]), digest, candidate["ref"])
    call = reply["calls"][1]
    runtime.dispatcher.execute(job["id"], key + ":1", call["name"], call["arguments"])
    runtime.graph.update_state(config, {"report": {"intent": json.loads(call["arguments"]),
        "instruction_basis": store.get("request", key)["instruction_basis"]}, "next": "tools"}, as_node="model")
    runtime.close()
    current = store.update_job(job["id"], status="blocked", stop_reason="accepted_evidence_conflict",
        cancel_requested=True, last_message="Saved acceptance has an unfinished received tail. Work is retained.")
    # A prior explicit local attempt exited after A. Its inert candidates must
    # be visible as uncommitted and must not obstruct a new current selection.
    import pdfmd.recovery as recovery
    diagnosis = recovery.diagnose(store.root, job["id"])
    with pytest.MonkeyPatch.context() as patch:
        def after_a(*_):
            raise RuntimeError("Synthetic exit after inert candidates")
        patch.setattr(recovery, "prepared", after_a)
        try:
            recovery.resolve(store, job["id"], key, diagnosis["basis"])
        except RuntimeError as error:
            assert "inert candidates" in str(error)
        else:
            raise AssertionError("The A boundary did not interrupt")
    assert not store.records("conflict_resolution", job["id"])
    value = {"job": job["id"], "request": key, "version": result["version_id"], "image": image,
             "source": str(source), "route": current["route"], "limits": current["limits"],
             "original_job": current, "preserved": preserved(store, job["id"]),
             "original_operations": store.records("operation", job["id"]),
             "blobs": store.records("blob", job["id"])}
    response = native(protocol, tool("report", {"state": "complete", "version_id": value["version"],
        "message": "Scripted Continue confirmed both saved source pages and pixels."}, "new-report"))
    (directory / "scripted-response.sse").write_bytes(b"".join(stream_frames(protocol, response)))
    (directory / "fixture.json").write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return value


def verify(directory):
    value = json.loads((directory / "fixture.json").read_text(encoding="utf-8"))
    job, version = value["job"], value["version"]
    # Independent source/catalog/files/ZIP verification, without Store initialization.
    with inspection(directory / "workspace", job) as (view, graph, snapshot):
        for kind, records in value["preserved"].items():
            current = view.records(kind, job)
            if kind in {"request", "attempt", "stream_receive"}:
                field = "attempt" if kind == "stream_receive" else "id"
                by_id = {record[field]: record for record in current}
                assert all(by_id[record[field]] == record for record in records)
            else:
                assert current == records
        for blob in value["blobs"]:
            assert view.get("blob", blob["ref"], job=job) == blob
            assert sha256(view.bytes(blob["ref"], job)).hexdigest() == blob["sha256"]
        for old in value["original_operations"]:
            current_op = view.get("operation", old["id"], job=job)
            assert all(current_op[k] == v for k, v in old.items())
        current = view.get("job", job)
        assert current["status"] == "completed" and current["attempts"] == value["original_job"]["attempts"] + 1
        assert current["head"] == version and current["active_seconds"] >= value["original_job"]["active_seconds"]
        assert snapshot.values["history"].count(value["request"]) == 1
        resolution = view.get("conflict_resolution", value["request"], job=job)
        receipt = view.json(resolution["ref"], job)
        assert receipt["observed_job"] == value["original_job"]
        assert len(view.records("conflict_resolution", job)) == 1
        assert len(view.records("version", job)) == 2
        assert view.bytes(current["source_ref"], job) == Path(value["source"]).read_bytes()
        saved_dir = directory / "workspace" / "versions" / version
        with zipfile.ZipFile(directory / "delivery.zip") as archive, pymupdf.open(value["source"]) as pdf:
            markdown = archive.read("document.md").decode("utf-8")
            lines = [line for page in pdf for line in page.get_text().splitlines()]
            assert all(line in markdown for line in lines)
            for member in archive.namelist():
                assert archive.read(member) == (saved_dir / member).read_bytes()
            actual = archive.read(value["image"]["asset_path"])
            source_image = view.bytes(value["image"]["ref"], job)
            assert actual == source_image
            a, b = pymupdf.Pixmap(actual), pymupdf.Pixmap(source_image)
            assert a.samples == b.samples
            with pymupdf.open(stream=view.bytes(current["source_ref"], job), filetype="pdf") as source_pdf:
                expected = source_pdf[1].get_pixmap(dpi=144, alpha=False)
                assert expected.samples == a.samples and (a.width, a.height) == (expected.width, expected.height)
            report = {"verified": True, "job": job, "resolution_ref": resolution["ref"], "source_lines": lines,
                      "version": version, "image_sha256": sha256(actual).hexdigest(), "pixels": [a.width, a.height],
                      "members": archive.namelist(), "original_acceptance_and_usage_preserved": True}
    (directory / "independent-verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    mode, directory, *args = sys.argv[1:]
    directory = Path(directory)
    print(json.dumps(prepare(directory, *args) if mode == "prepare" else verify(directory)))
