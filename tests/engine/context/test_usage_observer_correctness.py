"""Discriminating offline observer checks, independent of deployed F pricing."""
import base64
from copy import deepcopy
import json
import shutil

import httpx
import pymupdf
import pytest

from pdfmd.context import Context
from pdfmd.nexus import Nexus, StopRun
from pdfmd.runtime import Runtime
from pdfmd.storage import Store, encode
from pdfmd.usage_anchoring import price, projection
from pdfmd.usage_observation import UsageObserver
from tests.engine.context.test_usage_observation import profile, protocol_job, seed
from tests.engine.execution.test_runtime import tool
from tests.engine.transport.test_response_repairs import native


def image_part(protocol, url):
    return ({"type": "image_url", "image_url": {"url": url}} if protocol == "chat_completions"
            else {"type": "input_image", "image_url": url})


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("geometry", ["valid", "undecodable", "invalid_base64", "remote"])
def test_native_positions_and_geometry_are_independent(protocol, geometry):
    document = pymupdf.open()
    document.new_page(width=12, height=20)
    data = document[0].get_pixmap().tobytes("png")
    document.close()
    if geometry == "undecodable":
        data = b"valid base64, not an image"
    url = "data:image/png;base64," + base64.b64encode(data).decode()
    if geometry == "invalid_base64":
        url = "data:image/png;base64,!bad!"
    elif geometry == "remote":
        url = "https://example.invalid/offline-only.png"
    part = image_part(protocol, url)
    text = json.dumps({"image": part, "mask": base64.b64encode(data).decode()})
    key = "messages" if protocol == "chat_completions" else "input"
    receipt = ({"role": "tool", "content": text} if protocol == "chat_completions" else
               {"type": "function_call_output", "output": text})
    payload = {key: [{"role": "user", "content": [part], "metadata": part}, receipt],
               "metadata": {"nested": part}, "tools": [{"schema": part}]}
    before = encode(payload)
    cost = price(payload, 4096, protocol=protocol)
    assert encode(payload) == before
    assert cost["images"] == 1 and cost["image_cost"] == 4096
    facts = cost["image_occurrences"][0]
    assert facts["geometry_coverage"] == "uncalibrated_extrapolation"
    if geometry == "valid":
        assert (facts["width"], facts["height"], facts["area"]) == (12, 20, 240)
        assert facts["geometry_status"] == "available" and facts["geometry_reason"] is None
    else:
        assert facts["geometry_status"] == "unavailable" and facts["geometry_reason"]
        assert all(facts[k] is None for k in ("width", "height", "area", "aspect"))
        if geometry == "undecodable":
            assert facts["image_sha256"]  # Preserve decoded-byte identity despite geometry failure.
    payload[key][0]["content"] = []
    assert price(payload, None, protocol=protocol)["images"] == 0
    # Detached parts are ordinary data unless selected by the trusted v2 adapter.
    assert projection([part], protocol=protocol)[1] == []
    assert price([part], 4096, protocol=protocol, native_image_units=True)["images"] == 1


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("failed", ["decoded_full_local", "anchored"])
def test_comparator_failure_preserves_other_result_and_ordinary_path(setup, tmp_path, monkeypatch, protocol, failed):
    store, job = setup
    job = protocol_job(store, job, protocol)
    state = seed(store, job)
    from pdfmd import usage_observation
    real_price = usage_observation.price
    calls = []
    def pricing(value, *args, **kwargs):
        name = "decoded_full_local" if isinstance(value, dict) else "anchored"
        calls.append(name)
        if name == failed:
            raise OSError("injected " + name)
        return real_price(value, *args, **kwargs)
    monkeypatch.setattr(usage_observation, "price", pricing)
    outcomes = []
    for enabled in (False, True):
        root = tmp_path / str(enabled)
        shutil.copytree(store.root, root)
        local = Store(root)
        observer = UsageObserver(local, profile=profile(job))
        seen = []
        def reply(request):
            seen.append(request.content)
            value = native(protocol, tool("report", {"state": "partial", "message": "fixture"}))
            value["usage"] = {"prompt_tokens" if protocol == "chat_completions" else "input_tokens": 100}
            return httpx.Response(200, json=value)
        rt = Runtime(local, Nexus(local, lambda _: "synthetic", httpx.MockTransport(reply)),
                     usage_observer=observer if enabled else None)
        prepared = rt.prepare(deepcopy(state))
        request = local.get("request", prepared["pending"])
        raw = local.bytes(request["payload_ref"], job["id"])
        rt.model({**state, **prepared})
        outcomes.append((prepared, raw, request["meta"], seen,
                         [local.records(k) for k in ("operation", "version", "context_commit")]))
        if enabled:
            saved = observer.sink.records()[0]
            form = saved["forms"][0]
            surviving = "anchored" if failed == "decoded_full_local" else "decoded_full_local"
            assert saved["basis"]["eligibility"]
            assert form[failed] is None and form[surviving]["reservation"] > 0
            assert form["comparator_status"][failed] == {"status": "unavailable",
                "reason": "injected " + failed, "observer_error": "OSError"}
            assert form["comparator_status"][surviving] == {"status": "available"}
            assert form["eligibility"] == (failed != "anchored")
            assert set(form["reservation_errors"]) == {"full_local", surviving}
            assert form["actual"]["normalized_usage"]["input"] == 100
            rt.prepare(deepcopy(state))
            assert observer.sink.records() == [saved]
        assert seen == [raw]
        rt.close()
    assert outcomes[0] == outcomes[1]
    reopened = Store(tmp_path / "True")
    restored = UsageObserver(reopened, profile=profile(job))
    resumed = Runtime(reopened, Nexus(reopened, lambda _: pytest.fail("frozen preparation sends nothing")),
                      usage_observer=restored)
    resumed.prepare(deepcopy(state))
    assert restored.sink.records() == [saved]
    assert len(reopened.records("request")) == len(reopened.records("attempt")) == 2
    resumed.close()
    assert calls == ["decoded_full_local", "anchored"]


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_http_error_keeps_ordinary_failure_and_one_attempt(setup, tmp_path, protocol):
    store, job = setup
    job = protocol_job(store, job, protocol)
    state = seed(store, job)
    outcomes = []
    for enabled in (False, True):
        root = tmp_path / str(enabled)
        shutil.copytree(store.root, root)
        local = Store(root)
        observer = UsageObserver(local, profile=profile(job))
        seen = []
        def reply(request):
            seen.append(request.content)
            return httpx.Response(400, json={"error": "synthetic ordinary error"})
        rt = Runtime(local, Nexus(local, lambda _: "synthetic", httpx.MockTransport(reply)),
                     usage_observer=observer if enabled else None)
        prepared = rt.prepare(deepcopy(state))
        with pytest.raises(StopRun) as caught:
            rt.model({**state, **prepared})
        request = local.get("request", prepared["pending"])
        attempt = local.get("attempt", request["attempts"][0])
        outcomes.append((caught.value.reason, str(caught.value), seen, request["status"], request["failure"],
                         attempt["status"], attempt["http_status"],
                         [local.records(k) for k in ("operation", "version", "context_commit")]))
        assert len(seen) == len(request["attempts"]) == 1
        assert len(local.records("attempt")) == 2  # Separate seed and target.
        if enabled:
            form = observer.sink.records()[0]["forms"][0]
            assert form["actual"]["status"] == "http_error"
            assert form["actual"]["normalized_usage"] is None
            assert form["reservation_errors"] is None
        rt.close()
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_unreadable_native_image_and_metadata_keep_payload_and_anchor(setup, tmp_path, monkeypatch, protocol):
    store, job = setup
    job = protocol_job(store, job, protocol)
    job = store.update_job(job["id"], route={**job["route"], "vision": True, "image_tokens": 4096,
        "parameters": {"metadata": image_part(protocol, "data:image/png;base64,bm90LXBpeGVscw==")}})
    state = seed(store, job, image=True)
    pixels = Context.pixels
    def unreadable(self, current, ref, label):
        parts = pixels(self, current, ref, label)
        parts[1] = image_part(protocol, "data:image/png;base64,bm90LXBpeGVscw==")
        return parts
    monkeypatch.setattr(Context, "pixels", unreadable)
    outcomes = []
    for enabled in (False, True):
        root = tmp_path / str(enabled)
        shutil.copytree(store.root, root)
        local = Store(root)
        observer = UsageObserver(local, profile=profile(job))
        rt = Runtime(local, Nexus(local, lambda _: pytest.fail("preparation sends nothing")),
                     usage_observer=observer if enabled else None)
        result = rt.prepare(deepcopy(state))
        request = local.get("request", result["pending"])
        outcomes.append((result, local.bytes(request["payload_ref"], job["id"]), request["meta"]))
        if enabled:
            form = observer.sink.records()[0]["forms"][0]
            assert form["eligibility"], form["first_failure"]
            for name in ("anchored", "decoded_full_local"):
                cost = form[name]["components"]
                assert cost["images"] == 1 and cost["image_cost"] == 4096
                assert cost["image_occurrences"][0]["geometry_status"] == "unavailable"
                assert cost["image_occurrences"][0]["geometry_reason"].startswith("image_decode_failed:")
            # R01-MOD changes governing F as well as its observed baseline:
            # one real native image, with route metadata retained as text.
            assert form["full_local"]["components"]["images"] == 1
            assert form["full_local"]["components"]["modality_projection"] == "protocol_native_content_v2"
        rt.close()
    assert outcomes[0] == outcomes[1]
