"""Scripted streamed recovery and exact product preservation, not model autonomy."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import zipfile

import httpx
import pymupdf
import pytest

from pdfmd.documents import Documents
from pdfmd.nexus import Nexus
from pdfmd.runtime import Runtime
from pdfmd.server import Engine
from pdfmd.storage import Store
from test_response_repairs import native
from test_runtime import tool


WAIT = {"first_progress_seconds": 600, "idle_progress_seconds": 300, "total_seconds": None}
_spec = importlib.util.spec_from_file_location("stream_delivery_legacy_fixture",
    Path(__file__).parent / "desktop" / "compaction-recovery-fixture.py")
legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(legacy)


def prepare_stream_delivery(directory, protocol, endpoint):
    """Start from a genuinely frozen legacy unknown, without altering its contract."""
    directory = Path(directory)
    value = legacy.prepare(directory, protocol, endpoint)
    value["wait_policy"] = deepcopy(WAIT)
    (directory / "fixture.json").write_text(json.dumps(value, indent=2), encoding="utf-8")
    return value


def reply_value(protocol, fixture, number, head=None):
    if number == 1:
        return native(protocol, text=json.dumps({
            "task": "Convert the complete one-page synthetic source.",
            "current_state": f"Version {fixture['version']} preserves the opening text and source figure.",
            "unfinished_work": ["Append the final source sentence, then save and report."],
            "dependencies": [], "references": [fixture["source_ref"], fixture["image"]["ref"]],
            "cautions": ["Retain the existing draft and source image."]}))
    if number == 2:
        return native(protocol, tool("edit_document", {
            "base_version": fixture["version"], "expected_head": fixture["version"],
            "operations": [{"kind": "insert", "after_id": "image", "blocks": [
                {"id": "closing", "pages": [1], "markdown": fixture["closing"]}]}],
            "claim": "complete", "known_gaps": []}, "save"))
    assert number == 3
    return native(protocol, tool("report", {"state": "complete", "version_id": head,
        "message": "The complete synthetic source and figure are saved."}, "finish"))


def stream_frames(protocol, value):
    """Create actual SSE frames, not a JSON body mislabeled as streaming."""
    def event(value, name=None):
        return ((f"event: {name}\n" if name else "") + "data: " +
            json.dumps(value, ensure_ascii=False) + "\n\n").encode("utf-8")
    if protocol == "chat_completions":
        common = {"id": "scripted-stream", "object": "chat.completion.chunk", "model": "offline-fixture"}
        def chunk(delta, finish=None):
            return event({**common, "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]})
        message = value["choices"][0]["message"]
        frames = [b": connection heartbeat\n\n", chunk({"role": "assistant"})]
        content = message.get("content") or ""
        for offset in range(0, len(content), 40):
            frames.append(chunk({"content": content[offset:offset + 40]}))
        for index, call in enumerate(message.get("tool_calls") or []):
            frames.append(chunk({"tool_calls": [{"index": index, "id": call["id"], "type": "function",
                "function": {"name": call["function"]["name"], "arguments": ""}}]}))
            arguments = call["function"]["arguments"]
            for offset in range(0, len(arguments), 40):
                frames.append(chunk({"tool_calls": [{"index": index,
                    "function": {"arguments": arguments[offset:offset + 40]}}]}))
        frames += [chunk({}, value["choices"][0]["finish_reason"]),
            event({**common, "choices": [], "usage": {"prompt_tokens": 100, "completion_tokens": 50}}),
            b"data: [DONE]\n\n"]
        return frames
    value = deepcopy(value)
    value.update(id="scripted-stream", object="response", usage={"input_tokens": 100, "output_tokens": 50})
    frames = [b": connection heartbeat\n\n", event({"type": "response.created", "sequence_number": 0,
        "response": {"id": value["id"], "status": "in_progress", "output": []}}, "response.created")]
    sequence = 1
    for index, item in enumerate(value["output"]):
        item["id"] = f"item-{index}"
        initial = {**item, "status": "in_progress"}
        initial["arguments" if item["type"] == "function_call" else "content"] = "" if item["type"] == "function_call" else []
        frames.append(event({"type": "response.output_item.added", "sequence_number": sequence,
            "output_index": index, "item": initial}, "response.output_item.added"))
        sequence += 1
        text = item["arguments"] if item["type"] == "function_call" else item["content"][0]["text"]
        kind = "response.function_call_arguments.delta" if item["type"] == "function_call" else "response.output_text.delta"
        for offset in range(0, len(text), 40):
            frames.append(event({"type": kind, "sequence_number": sequence, "output_index": index,
                "item_id": item["id"], "content_index": 0, "delta": text[offset:offset + 40]}, kind))
            sequence += 1
        frames.append(event({"type": "response.output_item.done", "sequence_number": sequence,
            "output_index": index, "item": item}, "response.output_item.done"))
        sequence += 1
    frames.append(event({"type": "response.completed", "sequence_number": sequence,
        "response": value}, "response.completed"))
    return frames


def verify_stream_delivery(directory, *, extract=True):
    directory = Path(directory)
    fixture = json.loads((directory / "fixture.json").read_text(encoding="utf-8"))
    store = Store(directory / "workspace")
    identity = fixture["job"]
    job = store.get("job", identity)
    expected_route = {**fixture["route"], "wait_policy": fixture["wait_policy"]}
    assert job["route"] == expected_route and job["limits"] == fixture["limits"]
    assert job["status"] == "completed" and job["attempts"] == fixture["attempts_before"] + 3
    assert job["active_seconds"] >= fixture["active_seconds_before"] and not job["amendments"]
    for request in fixture["original_requests"]:
        assert store.get("request", request["id"], job=identity) == request
    assert store.get("attempt", fixture["unknown_attempt"]["id"], job=identity) == fixture["unknown_attempt"]
    assert sha256(store.bytes(fixture["unknown_request"]["payload_ref"], identity)).hexdigest() == fixture["frozen_payload_sha256"]
    current_operations = legacy.catalog_records(store, identity, "operation")
    for operation_id, operation in fixture["original_operations"].items():
        assert current_operations[operation_id] == operation
    for blob in fixture["original_blobs"]:
        assert sha256(store.bytes(blob["ref"], identity)).hexdigest() == blob["sha256"]
    settings = store.records("task_settings", identity)
    assert len(settings) == 1 and settings[0]["before"] == {"route": fixture["route"], "limits": fixture["limits"]}
    assert settings[0]["after"] == {"route": expected_route, "limits": fixture["limits"]}
    old_ids = {request["id"] for request in fixture["original_requests"]}
    requests = [request for request in store.records("request", identity) if request["id"] not in old_ids]
    assert len(requests) == 3 and sum(request["kind"] == "compaction" for request in requests) == 1
    for request in requests:
        assert request["route"] == expected_route and request["status"] == "accepted"
        assert request["replay_policy"] == fixture["unknown_request"]["replay_policy"] and len(request["attempts"]) == 1
        assert store.json(request["payload_ref"], identity)["stream"] is True
        accepted = store.json(request["accepted_ref"], identity)
        assert accepted["usage"] is not None
        # Raw SSE and derived native JSON must have distinct immutable provenance.
        assembled = store.get("blob", accepted["native_ref"], job=identity)
        assert assembled["kind"] == "assembled_response"
        raw_ref = assembled["meta"]["source_stream_ref"]
        assert raw_ref != accepted["native_ref"]
        assert request["stream_ref"] == accepted["stream_ref"] == raw_ref
        raw = store.get("blob", raw_ref, job=identity)
        assert raw["kind"] == "raw_stream" and b"data:" in store.bytes(raw_ref, identity)
    assert sum(event["type"] == "request_continued" for event in store.events(identity, limit=10000)) == 1
    runtime = Runtime(store, Nexus(store, lambda _: "never-used"))
    try:
        state = runtime.graph.get_state({"configurable": {"thread_id": identity}}).values
        assert {key: state.get(key) for key in fixture["context_policy"]} == fixture["context_policy"]
    finally:
        runtime.close()
    documents = Documents(store)
    previous = documents.version(identity, fixture["version"])
    saved = documents.version(identity, job["delivery"])
    assert saved["content"]["blocks"][:2] == previous["content"]["blocks"]
    assert saved["content"]["blocks"][2]["markdown"] == fixture["closing"]
    assert saved["content"]["claim"] == "complete" and len(saved["assets"]) == 1
    for name, expected in fixture["prior_version_files"].items():
        assert legacy.fingerprint(documents.root / fixture["version"] / name) == expected
    assert store.bytes(fixture["source_ref"], identity) == Path(fixture["source"]).read_bytes()
    with pymupdf.open(fixture["source"]) as pdf, zipfile.ZipFile(directory / "delivery.zip") as archive:
        source_image = pdf[0].get_pixmap(dpi=72)
        stored_image = pymupdf.Pixmap(store.bytes(fixture["image"]["ref"], identity))
        assert source_image.samples == stored_image.samples
        expected_files = store.get("version", job["delivery"], job=identity)["files"]
        assert set(archive.namelist()) == set(expected_files) and len(archive.namelist()) == len(expected_files)
        for name in archive.namelist():
            assert archive.read(name) == (documents.root / job["delivery"] / name).read_bytes()
        assert json.loads(archive.read("document.json")) == saved
        assert all(line in archive.read("document.md").decode("utf-8") for line in pdf[0].get_text().splitlines())
        assert archive.read(fixture["image"]["asset_path"]) == store.bytes(fixture["image"]["ref"], identity)
        if extract:
            archive.extractall(directory / "exported")
    result = {"verified": True, "protocol": fixture["protocol"], "selected_version": job["delivery"],
        "attempts": job["attempts"], "old_request_attempt_blobs_policy_and_draft_preserved": True,
        "source_and_image_pixels_preserved": True, "all_zip_bytes_equal": True,
        "one_compaction_successor": True, "streamed_successors": len(requests), "live_model_calls": 0}
    (directory / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_streamed_handoff_then_edit_preserves_reopen_export_and_unknown_boundary(tmp_path, protocol):
    endpoint = "http://127.0.0.1:8317/v1/" + ("responses" if protocol == "responses" else "chat/completions")
    fixture = prepare_stream_delivery(tmp_path, protocol, endpoint)
    store = Store(tmp_path / "workspace")
    calls, streams = [], []

    class Body(httpx.AsyncByteStream):
        def __init__(self, frames):
            self.frames = frames
        async def __aiter__(self):
            for frame in self.frames:
                # Decoder must not rely on transport chunks matching SSE/JSON boundaries.
                split = min(19, len(frame))
                yield frame[:split]
                yield frame[split:]

    def respond(request):
        payload = json.loads(request.content)
        calls.append(payload)
        assert payload["stream"] is True
        assert bool(payload.get("tools")) == (len(calls) > 1)
        frames = stream_frames(protocol, reply_value(protocol, fixture, len(calls), store.get("job", fixture["job"])["head"]))
        streams.append(b"".join(frames))
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=Body(frames))

    engine = Engine(store.root, transport=httpx.MockTransport(respond))
    try:
        original = fixture["unknown_request"]
        engine.configure(fixture["job"], route={"wait_policy": WAIT})
        assert calls == []
        engine.start(fixture["job"], "offline-only")
        engine.futures[fixture["job"]].result(timeout=30)
        assert calls == [] and store.get("job", fixture["job"])["attempts"] == fixture["attempts_before"]
        engine.start(fixture["job"], "offline-only", recover_compaction_request=original["id"])
        engine.futures[fixture["job"]].result(timeout=30)
        assert len(calls) == 3, store.get("job", fixture["job"])
    finally:
        engine.close()
    reopened = Store(store.root)
    job = reopened.get("job", fixture["job"])
    assert job["status"] == "completed", job["last_message"]
    assert Documents(reopened).export(job["id"], job["delivery"], str(tmp_path / "delivery.zip"))["verified"]
    assert verify_stream_delivery(tmp_path)["verified"]
    retained_streams = [reopened.bytes(blob["ref"], job["id"]) for blob in reopened.records("blob", job["id"])
                       if blob["kind"] == "raw_stream"]
    assert retained_streams == streams
    assert len(calls) == 3, "Reopening and exporting do not issue another model request."
