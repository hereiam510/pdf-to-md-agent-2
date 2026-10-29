"""Isolated diagnostic UI inputs and source-led audits; no real model transport."""
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import zipfile

import httpx
import pymupdf
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_accepted_evidence_recovery import historical, preserved
from test_continuation import delivery
from test_runtime import tool
from pdfmd.documents import Documents
from pdfmd.nexus import Nexus, StopRun, make_payload
from pdfmd.recovery import diagnose, inspection, resolve
from pdfmd.runtime import Runtime
from pdfmd.schema import Route
from pdfmd.storage import Store


def hash_files(directory):
    return {p.relative_to(directory).as_posix(): sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob("*") if p.is_file()}


def prepare(directory, protocol):
    route = {"endpoint": "https://synthetic.invalid/v1/" + ("responses" if protocol == "responses" else "chat/completions"),
             "protocol": protocol, "model": "offline-diagnostics-only", "context_tokens": 65536, "output_tokens": 2048}
    store, job, version, image, source = delivery.__wrapped__(directory, route)
    content = Documents(store).version(job["id"], version)["content"]
    calls = [tool("edit_document", {"base_version": version, "expected_head": version,
             "replace_blocks": content["blocks"], "claim": "complete"}, "saved-edit"),
             tool("read_document", {}, "unstarted-read")]
    with pytest.MonkeyPatch.context() as patch:
        store, job, key, reply, raw = historical((store, job), patch, protocol,
            published=protocol == "chat_completions", calls=calls, suffix=b"\xe4", endpoint=route["endpoint"])
    runtime = Runtime(store, Nexus(store, lambda _: pytest.fail("No provider in fixture preparation")))
    call = reply["calls"][0]
    result = runtime.dispatcher.execute(job["id"], key + ":0", call["name"], call["arguments"])
    runtime.close()
    store.update_job(job["id"], status="blocked", stop_reason="accepted_evidence_conflict", cancel_requested=True,
        last_message="Synthetic historical finish conflict; no real task or model.")
    value = {"job": job["id"], "request": key, "version": result["data"]["version_id"],
             "seed_version": version, "image": image, "source": str(source),
             "preserved": preserved(store, job["id"]), "blobs": store.records("blob", job["id"]),
             "original_usage": store.get("attempt", store.get("request", key)["attempts"][0]).get("usage"),
             "saved_usage": reply["usage"], "native_ref": reply["native_ref"], "stream_ref": reply["stream_ref"],
             "native": json.loads(store.bytes(reply["native_ref"], job["id"])), "raw_hex": raw.hex()}
    (directory / "fixture.json").write_text(json.dumps(value, indent=2), encoding="utf-8")
    return value


def advance(directory):
    value = json.loads((directory / "fixture.json").read_text(encoding="utf-8"))
    store = Store(directory / "workspace")
    job = value["job"]
    first = diagnose(store.root, job)
    if first["status"] != "resolved":
        resolve(store, job, value["request"], first["basis"])
    # This isolated fixture explicitly starts a new synthetic request. The old
    # Stop remains preserved in its receipt; the fixture clears its current gate.
    store.update_job(job, cancel_requested=False)
    sent = []
    def timeout(request):
        sent.append(str(request.url))
        raise httpx.ReadTimeout("Synthetic newer-request timeout; MockTransport only", request=request)
    service = Nexus(store, lambda _: "synthetic-only", httpx.MockTransport(timeout))
    runtime = Runtime(store, service)
    try:
        config = {"configurable": {"thread_id": job}}
        state = dict(runtime.graph.get_state(config).values)
        key = f"{job}:{state['seq']}:{state['revision']}"
        route = Route.model_validate(store.get("job", job)["route"])
        service.freeze(job, key, make_payload(route, "Synthetic newer request", [], []), "normal", {})
        runtime.graph.update_state(config, {"pending": key, "next": "model"}, as_node="prepare")
        try:
            service.send(job, key)
        except StopRun as error:
            store.update_job(job, status="blocked", stop_reason=error.reason, last_message=str(error))
        else:
            raise AssertionError("Mock request did not time out")
        assert len(sent) == 1
        request = store.get("request", key)
        assert not store.maybe("blob", f"accepted:{key}")
        result = {"job": job, "old_request": value["request"], "request": key,
                  "request_status": request["status"], "request_failure": request.get("failure"),
                  "mock_sends": len(sent), "actual_network_sends": 0}
    finally:
        runtime.close()
    (directory / "newer-request.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def verify(directory):
    value = json.loads((directory / "fixture.json").read_text(encoding="utf-8"))
    job, version = value["job"], value["version"]
    before = hash_files(directory / "workspace")
    with inspection(directory / "workspace", job) as (view, graph, snapshot):
        assert preserved(view, job) == value["preserved"]
        for blob in value["blobs"]:
            assert view.get("blob", blob["ref"], job=job) == blob
            assert sha256(view.bytes(blob["ref"], job)).hexdigest() == blob["sha256"]
        receipt = view.json(f"conflict-resolution:{value['request']}", job)
        assert receipt["request"] == value["request"]
        assert snapshot.values["resolutions"][value["request"]] == receipt["ref"]
        assert len(view.records("conflict_resolution", job)) == 1
        assert len(view.records("version", job)) == 2
        assert view.get("job", job)["head"] == version
        assert view.bytes(value["stream_ref"], job) == bytes.fromhex(value["raw_hex"])
        assert view.bytes(value["stream_ref"], job).endswith(b"\xe4")
        assert view.json(value["native_ref"], job) == value["native"]
        saved_dir = directory / "workspace" / "versions" / version
        seed_dir = directory / "workspace" / "versions" / value["seed_version"]
        with zipfile.ZipFile(directory / "delivery.zip") as archive, pymupdf.open(value["source"]) as pdf:
            markdown = archive.read("document.md").decode("utf-8")
            lines = [line for page in pdf for line in page.get_text().splitlines()]
            assert all(line in markdown for line in lines)
            assert all(line in (seed_dir / "document.md").read_text(encoding="utf-8") for line in lines)
            assert view.bytes(view.get("job", job)["source_ref"], job) == Path(value["source"]).read_bytes()
            expected_members = {path.relative_to(saved_dir).as_posix() for path in saved_dir.rglob("*") if path.is_file()}
            assert set(archive.namelist()) == expected_members
            image_refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", markdown)
            assert image_refs == [value["image"]["asset_path"]]
            assert all(ref in expected_members for ref in image_refs)
            for member in archive.namelist():
                assert archive.read(member) == (saved_dir / member).read_bytes()
            actual = archive.read(value["image"]["asset_path"])
            assert actual == view.bytes(value["image"]["ref"], job)
            expected, image = pdf[1].get_pixmap(dpi=144, alpha=False), pymupdf.Pixmap(actual)
            assert image.samples == expected.samples and (image.width, image.height) == (expected.width, expected.height)
            report = {"verified": True, "job": job, "version": version, "seed_version": value["seed_version"],
                      "source_lines": lines, "pixels": [image.width, image.height], "members": archive.namelist(),
                      "exact_member_set": True, "markdown_image_refs": image_refs,
                      "raw_tail_hex": "e4", "raw_sha256": sha256(bytes.fromhex(value["raw_hex"])).hexdigest(),
                      "original_records_preserved": True, "actual_network_sends": 0}
    assert hash_files(directory / "workspace") == before
    report["audit_workspace_unchanged"] = True
    (directory / "source-export-audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    mode, path, *args = sys.argv[1:]
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    if mode == "prepare":
        result = prepare(directory, *args)
    elif mode == "advance":
        result = advance(directory)
    elif mode == "verify":
        result = verify(directory)
    elif mode == "hash":
        result = hash_files(directory / "workspace")
    else:
        raise ValueError(mode)
    print(json.dumps(result))
