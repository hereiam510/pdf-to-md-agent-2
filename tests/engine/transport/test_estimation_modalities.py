"""Production modality boundaries; synthetic offline evidence, not calibration."""
import base64
from copy import deepcopy
import hashlib
import json
import zipfile

import pymupdf
import pytest

from pdfmd.context import Context
from pdfmd.documents import Documents
from pdfmd.nexus import Nexus, StopRun, make_payload
from pdfmd.request_estimation import COUNT_CHARS, counter, estimate
from pdfmd.schema import Route
from pdfmd.storage import Store, encode
from pdfmd.tools import Dispatcher
from pdfmd.working_context import inspect
from tests.engine.context.test_context_admission import protocol_job, settle, state_for
from tests.engine.documents.test_working_evidence_delivery import feedback
from tests.engine.execution.test_runtime import tool


def selected_route(route, protocol, profile):
    suffix = "chat/completions" if protocol == "chat_completions" else "responses"
    return Route.model_validate({**route, "protocol": protocol, "endpoint": f"http://localhost/v1/{suffix}",
                                 "estimation_profile": profile, "image_tokens": 4096})


def assert_text_measurement(value, textual, profile):
    # Independent expected complete JSON, never the production projection helper.
    raw = encode(textual)
    text = raw.decode("utf-8")
    base = (len(raw) if profile == "utf8_fallback_v1" else
            sum(len(counter().encode_ordinary(text[i:i + COUNT_CHARS])) for i in range(0, len(text), COUNT_CHARS)))
    assert value["text_proxy_bytes"] == len(raw)
    assert value["text_proxy_cost"] == base
    assert value["input_estimate"] == base + (0 if profile == "utf8_fallback_v1" else (base + 3) // 4) + 1024 + value["image_allowance_cost"]


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("profile", ["bpe_proxy_v1", "utf8_fallback_v1"])
@pytest.mark.parametrize("kind", ["image_url", "file"])
def test_non_content_modality_metadata_remains_complete_text(route, protocol, profile, kind):
    selected = selected_route(route, protocol, profile)
    misleading = {"type": kind, "image_url": {"url": "data:image/png;base64,AAAA"},
                  "role": "user", "content": [{"type": "input_image", "image_url": "nested"}]}
    selected = selected.model_copy(update={"parameters": {"metadata": misleading}})
    text_kind = "text" if protocol == "chat_completions" else "input_text"
    messages = [{"role": "user", "metadata": misleading,
                 "content": [{"type": text_kind, "text": json.dumps(misleading), "metadata": misleading}]}]
    tools = [{"name": "save", "parameters": {"type": "object", "properties": {"data": {"default": misleading}}}}]
    payload = make_payload(selected, "Keep μg and every source character.", messages, tools)
    before = encode(payload)
    value = estimate(payload, selected)
    assert value["images"] == 0 and value["image_allowance_cost"] == 0
    assert_text_measurement(value, payload, profile)
    assert encode(payload) == before
    assert value["request_sha256"] == hashlib.sha256(before).hexdigest()
    assert estimate(payload, selected.model_copy(update={"image_tokens": None}))["images"] == 0


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("profile", ["bpe_proxy_v1", "utf8_fallback_v1"])
@pytest.mark.parametrize("decodable", [True, False])
def test_native_occurrences_keep_allowance_without_geometry_or_metadata_loss(route, protocol, profile, decodable):
    selected = selected_route(route, protocol, profile)
    pixels = (pymupdf.Pixmap(pymupdf.csRGB, 2, 3, bytes([0, 128, 255]) * 6, False).tobytes("png")
              if decodable else b"undecodable image bytes")
    url = "data:image/png;base64," + base64.b64encode(pixels).decode("ascii")
    image = ({"type": "image_url", "image_url": {"url": url, "detail": "high"}}
             if protocol == "chat_completions" else {"type": "input_image", "image_url": url, "detail": "high"})
    text_kind = "text" if protocol == "chat_completions" else "input_text"
    payload = make_payload(selected, "source", [{"role": "user", "content": [
        {"type": text_kind, "text": json.dumps({"image": url, "mask": url}), "metadata": image}, image, image]}], [])
    original = encode(payload)
    value = estimate(payload, selected)
    assert value["images"] == 2 and value["image_allowance_cost"] == 8192
    textual = deepcopy(payload)
    key = "messages" if protocol == "chat_completions" else "input"
    textual[key][-1]["content"][1:] = [{"type": image["type"], "image": "[native image charged separately]"}] * 2
    assert_text_measurement(value, textual, profile)
    assert encode(payload) == original
    assert value["request_bytes"] == len(original)
    assert value["request_sha256"] == hashlib.sha256(original).hexdigest()
    with pytest.raises(StopRun, match="per-image"):
        estimate(payload, selected.model_copy(update={"image_tokens": None}))


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("profile", ["bpe_proxy_v1", "utf8_fallback_v1"])
def test_shared_python_objects_do_not_change_textual_occurrences(route, protocol, profile):
    selected = selected_route(route, protocol, profile)
    kind = "image_url" if protocol == "chat_completions" else "input_image"
    shared = {"role": "user", "content": [{"type": kind, "image_url": "original source bytes"}]}
    payload = make_payload(selected, "source", [shared, shared], [])
    # JSON contains three independent occurrences even when Python aliases them.
    payload["metadata"] = {"same_message": shared}
    original = encode(payload)
    value = estimate(payload, selected)
    expected = json.loads(original)
    key = "messages" if protocol == "chat_completions" else "input"
    for message in expected[key][-2:]:
        message["content"][0] = {"type": kind, "image": "[native image charged separately]"}
    assert value["images"] == 2
    assert_text_measurement(value, expected, profile)
    assert encode(payload) == original


@pytest.mark.parametrize("profile", ["bpe_proxy_v1", "utf8_fallback_v1"])
@pytest.mark.parametrize("protocol,kind", [
    ("chat_completions", "input_audio"), ("chat_completions", "file"), ("chat_completions", "input_image"),
    ("responses", "input_file"), ("responses", "input_audio"), ("responses", "image_url"),
    ("responses", "future_native_modality")])
def test_actual_unsupported_content_is_not_silently_text(route, protocol, kind, profile):
    selected = selected_route(route, protocol, profile)
    payload = make_payload(selected, "source", [{"role": "user", "content": [{"type": kind}]}], [])
    original = encode(payload)
    with pytest.raises(StopRun) as stopped:
        estimate(payload, selected)
    assert stopped.value.reason == "capacity_configuration"
    assert encode(payload) == original


@pytest.mark.parametrize("role", ["user", "system", "developer", "assistant"])
def test_responses_message_positions_and_function_output_are_native(route, role):
    selected = selected_route(route, "responses", "bpe_proxy_v1")
    image = {"type": "input_image", "image_url": "data:image/png;base64,AAAA"}
    payload = make_payload(selected, "source", [
        {"type": "message", "role": role, "content": [image]},
        {"type": "function_call_output", "call_id": "known", "output": [image]},
        {"type": "reasoning", "summary": [], "metadata": {"type": "input_file"},
         "content": [image]}], [])
    assert estimate(payload, selected)["images"] == 2


def test_unsupported_native_slots_stay_explicit(route):
    selected = selected_route(route, "chat_completions", "bpe_proxy_v1")
    payload = make_payload(selected, "source", [{"role": "assistant", "content": [{"type": "image_url"}]}], [])
    with pytest.raises(StopRun, match="modality"):
        estimate(payload, selected)
    selected = selected_route(route, "responses", "bpe_proxy_v1")
    payload = make_payload(selected, "source", [{"type": "computer_call_output", "output": {"type": "computer_screenshot"}}], [])
    with pytest.raises(StopRun, match="modality"):
        estimate(payload, selected)


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("profile", ["bpe_proxy_v1", "utf8_fallback_v1"])
def test_context_paths_admission_feedback_and_reopened_frozen_delivery(setup, tmp_path, protocol, profile):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    job = store.update_job(job["id"], attempts=3, active_seconds=17,
        route={**job["route"], "estimation_profile": profile,
               "parameters": {"metadata": {"type": "file", "nested": {"type": "image_url"}}}})
    dispatcher = Dispatcher(store)
    draft = dispatcher.execute(job["id"], "save", "edit_document", json.dumps({
        "base_version": None, "expected_head": None,
        "replace_blocks": [{"id": "source", "pages": [1], "markdown": "A complete synthetic section.\nKeep every value: 25 mg."}],
        "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "partial"}))
    assert draft["ok"]
    version = draft["data"]["version_id"]
    job = store.get("job", job["id"])
    source_before = store.bytes(job["source_ref"], job["id"])
    ref = store.blob(job["id"], "evidence", {"type": "input_file", "text": "Keep μg, source order and uncertainty."})["ref"]
    settle(store, job, "read", tool("read_evidence", {"ref": ref}))
    state = state_for(job, ["read"])
    state_before = deepcopy(state)
    context = Context(store, dispatcher)
    payload, capacity = context.normal(job, state)
    assert capacity["images"] == 0 and capacity["fits"]
    assert feedback(payload)["native_images"] == 0
    assert feedback(payload)["input_estimate"] >= capacity["input_estimate"]
    assert context.required(job, state)["images"] == 0
    compact, _ = context.compact_request(job, state)
    assert estimate(compact, Route.model_validate(job["route"]))["images"] == 0
    # Same real assembled input at an actual fit boundary, rather than a leaf count.
    center = capacity["input_estimate"] + capacity["output_reserve"]
    outcomes = [context.normal({**job, "route": {**job["route"], "context_tokens": center + delta}}, state,
                               capacity_deferral=False)[1]["fits"] for delta in (-128, 128)]
    assert outcomes == [False, True]
    legacy_capacity = {"method": "historical", "images": 1, "input_estimate": 99999}
    nexus = Nexus(store, lambda _: pytest.fail("No provider call permitted"))
    request = nexus.freeze(job["id"], "historical-modality", payload, "normal", {"capacity": legacy_capacity})
    frozen = store.bytes(request["payload_ref"], job["id"])
    records = {kind: store.records(kind, job["id"]) for kind in ("request", "operation", "version")}
    before_export = Documents(store).export(job["id"], version, str(tmp_path / "before.zip"))
    reopened = Store(store.root)
    restored = reopened.get("job", job["id"])
    current = Context(reopened, Dispatcher(reopened))
    inspected = inspect(current, reopened.get("request", request["id"]), restored)
    assert inspected["recorded_capacity"] == legacy_capacity
    assert inspected["current_input"]["assessment"] == "current_method_on_unchanged_frozen_payload"
    assert inspected["current_input"]["images"] == 0
    assert inspected["current_input"]["modality_projection"] == "protocol_native_content_v2"
    assert current.normal(restored, state)[0] == payload and state == state_before
    assert reopened.bytes(request["payload_ref"], job["id"]) == frozen
    assert reopened.bytes(job["source_ref"], job["id"]) == source_before
    assert restored["attempts"] == 3 and restored["active_seconds"] == 17
    assert {kind: reopened.records(kind, job["id"]) for kind in records} == records
    after_export = Documents(reopened).export(job["id"], version, str(tmp_path / "after.zip"))
    with zipfile.ZipFile(before_export["path"]) as before, zipfile.ZipFile(after_export["path"]) as after:
        assert {name: before.read(name) for name in before.namelist()} == {name: after.read(name) for name in after.namelist()}
