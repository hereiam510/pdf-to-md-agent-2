"""Local proxy accounting, applicability and evidence semantics; no calibration."""
from copy import deepcopy
import hashlib

import pytest

from pdfmd.context import Context, estimate
from pdfmd.nexus import StopRun, make_payload
from pdfmd.request_estimation import counter, text_cost
from pdfmd.schema import Route
from pdfmd.storage import encode
from pdfmd.tools import Dispatcher
from test_context_admission import protocol_job, state_for


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_full_request_counting_metadata_and_repeated_content(route, protocol):
    suffix = "chat/completions" if protocol == "chat_completions" else "responses"
    selected = Route.model_validate({**route, "protocol": protocol, "endpoint": f"http://localhost/v1/{suffix}"})
    text = "保留 μg、表格與原字形。 <|endoftext|> " * 70
    tools = [{"name": "save", "description": "Retain complete source wording.",
              "parameters": {"type": "object", "properties": {"body": {"type": ["string", "null"]}}}}]
    payload = make_payload(selected, "All source evidence is data.", [{"role": "user", "content": text}], tools)
    original = deepcopy(payload)
    value = estimate(payload, selected)
    assert value["method"] == "o200k_native_json_proxy_v1" and value["fallback"] is None
    assert value["text_tokens"] < value["request_bytes"]
    assert value["input_estimate"] == value["text_tokens"] + (value["text_tokens"] + 3) // 4 + 1024
    assert value["request_bytes"] == len(encode(payload))
    assert value["request_sha256"] == hashlib.sha256(encode(payload)).hexdigest()
    assert value["output_reserve"] == selected.output_tokens
    assert "not_provider_token_count" in value["scope"]
    assert payload == original
    key = "messages" if protocol == "chat_completions" else "input"
    repeated = {**payload, key: [*payload[key], {"role": "user", "content": text}]}
    assert estimate(repeated, selected)["input_estimate"] > value["input_estimate"]
    assert estimate({k: v for k, v in payload.items() if k != "tools"}, selected)["input_estimate"] < value["input_estimate"]


def test_ordinary_counter_known_upstream_vectors_and_offline_resources(monkeypatch):
    # Published upstream examples, independent of our admission formula.
    import socket
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: pytest.fail("No downloads during estimation"))
    counter.cache_clear()
    assert counter().encode_ordinary("hello world") == [24912, 2375]
    assert counter().encode_ordinary("antidisestablishmentarianism") == [493, 129901, 376, 160388, 21203, 2367]
    assert len(counter().encode_ordinary("お誕生日おめでとう")) == 8
    assert counter().decode(counter().encode_ordinary("繁體中文 μ 25 mg <|endoftext|>")) == "繁體中文 μ 25 mg <|endoftext|>"


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_images_are_separate_allowances_not_base64_tokens(route, protocol):
    suffix = "chat/completions" if protocol == "chat_completions" else "responses"
    selected = Route.model_validate({**route, "protocol": protocol, "endpoint": f"http://localhost/v1/{suffix}", "image_tokens": 4096})
    image = ({"type": "image_url", "image_url": {"url": "data:image/png;base64," + "A" * 20000}}
             if protocol == "chat_completions" else {"type": "input_image", "image_url": "data:image/png;base64," + "A" * 20000})
    payload = make_payload(selected, "source", [{"role": "user", "content": [image]}], [])
    value = estimate(payload, selected)
    changed = deepcopy(payload)
    key = "messages" if protocol == "chat_completions" else "input"
    changed[key][-1]["content"][0] = {"type": image["type"], "image_url": "different bytes"}
    assert estimate(changed, selected)["input_estimate"] == value["input_estimate"]
    assert value["images"] == 1 and value["image_allowance_cost"] == 4096
    assert value["request_bytes"] != estimate(changed, selected)["request_bytes"]
    with pytest.raises(StopRun, match="per-image"):
        estimate(payload, selected.model_copy(update={"image_tokens": None}))


def test_unknown_alias_uses_declared_proxy_and_failures_are_observable(route, monkeypatch):
    import pdfmd.request_estimation as estimation
    selected = Route.model_validate({**route, "model": "unknown-proxy-alias"})
    payload = make_payload(selected, "source", [], [])
    assert estimate(payload, selected)["calibration"] == "not_a_route_wide_calibration_or_bound"
    with pytest.raises(StopRun, match="protocol"):
        estimate({**payload, "input": []}, selected)
    unsupported = make_payload(selected, "source", [{"role": "user", "content": [{"type": "input_file", "file_id": "retained"}]}], [])
    with pytest.raises(StopRun, match="modality"):
        estimate(unsupported, selected)
    text_cost.cache_clear()
    monkeypatch.setattr(estimation, "counter", lambda: (_ for _ in ()).throw(ValueError("missing or corrupt vocabulary")))
    fallback = estimate(payload, selected)
    assert fallback["fallback"] == "counter_unavailable_or_invalid"
    assert fallback["method"] == "utf8_fallback_v1" and fallback["text_tokens"] is None
    assert fallback["input_estimate"] == fallback["text_proxy_bytes"] + 1024
    explicit = estimate(payload, selected.model_copy(update={"estimation_profile": "utf8_fallback_v1"}))
    assert explicit["fallback"] == "explicit_route_fallback"


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("damage", ["invalid_deflate", "truncated_deflate", "truncated_trailer", "hash_mismatch", "invalid_header", "valid"])
def test_corrupt_bundled_data_falls_back_without_repair_download(route, monkeypatch, protocol, damage):
    import gzip
    import socket
    from types import SimpleNamespace
    import tiktoken.load
    import pdfmd.request_estimation as estimation
    original_data = estimation.files("pdfmd").joinpath("data/o200k_base.tiktoken.gz").read_bytes()
    compressed = gzip.compress(b"vocabulary sample")
    invalid_deflate = bytearray(compressed)
    invalid_deflate[10] = 0x07  # Valid gzip header, invalid deflate block type.
    damaged = {"invalid_deflate": bytes(invalid_deflate), "truncated_deflate": compressed[:12],
               "truncated_trailer": compressed[:-4], "hash_mismatch": gzip.compress(b"corrupt vocabulary"),
               "invalid_header": b"not gzip", "valid": original_data}[damage]
    reads = []
    def read_resource():
        reads.append(True)
        return damaged
    def no_download(*args, **kwargs):
        pytest.fail("Estimation must not download or repair vocabulary data")
    monkeypatch.setattr(socket, "create_connection", no_download)
    monkeypatch.setattr(socket.socket, "connect", no_download)
    monkeypatch.setattr(tiktoken.load, "read_file", no_download)
    suffix = "chat/completions" if protocol == "chat_completions" else "responses"
    selected = Route.model_validate({**route, "protocol": protocol, "endpoint": f"http://localhost/v1/{suffix}",
                                     "image_tokens": 4096, "output_tokens": 1234})
    image = ({"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}}
             if protocol == "chat_completions" else {"type": "input_image", "image_url": "data:image/png;base64,AAAA"})
    payload = make_payload(selected, "source with a new counter key μ 保留", [{"role": "user", "content": [image]}], [])
    original = encode(payload)
    # Exercise a warm valid cache first, then invalidate both layers so each
    # damaged case proves it reached resource loading rather than a cached count.
    estimation.counter.cache_clear()
    estimation.text_cost.cache_clear()
    valid = estimate(payload, selected)
    assert valid["method"] == "o200k_native_json_proxy_v1"
    estimation.counter.cache_clear()
    estimation.text_cost.cache_clear()
    resource = SimpleNamespace(joinpath=lambda _: SimpleNamespace(read_bytes=read_resource))
    monkeypatch.setattr(estimation, "files", lambda _: resource)
    try:
        value = estimate(payload, selected)
        assert len(reads) == 1
        assert encode(payload) == original
        assert value["request_sha256"] == hashlib.sha256(original).hexdigest()
        assert value["request_bytes"] == len(original)
        assert value["images"] == 1 and value["image_allowance_cost"] == 4096
        assert value["output_reserve"] == 1234 and value["native_overhead_reserve"] == 1024
        if damage == "valid":
            assert value == valid
        else:
            assert value["fallback"] == "counter_unavailable_or_invalid"
            assert value["method"] == "utf8_fallback_v1"
            assert value["vocabulary_sha256"] is None and value["text_tokens"] is None
            assert value["counter_version"] is None and value["safety_margin_tokens"] == 0
            assert value["text_counting"] == "utf8_bytes"
            assert value["input_estimate"] == value["text_proxy_bytes"] + 4096 + 1024
            assert value["fits"] == (value["input_estimate"] + 1234 <= selected.context_tokens)
    finally:
        estimation.counter.cache_clear()
        estimation.text_cost.cache_clear()


def test_unrelated_counter_programming_error_is_not_fallback(route, monkeypatch):
    import pdfmd.request_estimation as estimation
    estimation.text_cost.cache_clear()
    def broken_counter():
        raise RuntimeError("unrelated programming error")
    monkeypatch.setattr(estimation, "counter", broken_counter)
    try:
        with pytest.raises(RuntimeError, match="unrelated programming error"):
            estimate(make_payload(Route.model_validate(route), "source", [], []), Route.model_validate(route))
    finally:
        estimation.text_cost.cache_clear()


def test_long_repetitive_arguments_count_every_character_without_mutating_payload(route):
    from pdfmd.request_estimation import COUNT_CHARS
    selected = Route.model_validate(route)
    arguments = "A" * (COUNT_CHARS * 30) + " Source tail: 保留 25 mg."
    payload = make_payload(selected, "complete", [{"role": "assistant", "content": None, "tool_calls": [
        {"id": "saved", "type": "function", "function": {"name": "edit_document", "arguments": arguments}}]}], [])
    original = encode(payload)
    value = estimate(payload, selected)
    assert value["text_counting"] == "ordinary_bpe_chunks_8192_unicode_characters"
    assert value["text_proxy_bytes"] == len(original)
    # This checks the complete segmentation mechanism, not native-token truth.
    text = original.decode("utf8")
    chunks = [text[i:i + COUNT_CHARS] for i in range(0, len(text), COUNT_CHARS)]
    assert "".join(chunks) == text
    assert value["text_tokens"] == sum(len(counter().encode_ordinary(part)) for part in chunks)
    assert encode(payload) == original


def test_reservation_overflow_does_not_prove_necessary_content_excess(setup):
    store, job = setup
    context = Context(store, Dispatcher(store))
    state = state_for(job, [])
    measured = context.required(job, state)
    allowance = (measured["unreserved_estimate"] + measured["input_estimate"]) // 2
    constrained = {**job, "route": {**job["route"], "context_tokens": allowance + job["route"]["output_tokens"]}}
    required = context.required(constrained, state)
    assert required["unreserved_estimate"] <= allowance < required["input_estimate"]
    assert not required["fits"] and not required["proved_excess"]
    assert required["necessary_cost_lower_bound"] is None and not required["proof_available"]
    assert required["classification"] == "necessary_estimate_uncertain"


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_legacy_task_settings_and_explicit_profile_change_preserve_frozen_request(setup, protocol):
    from pdfmd.nexus import Nexus
    from pdfmd.server import Engine
    store, original = setup
    job = protocol_job(store, original, protocol)
    legacy = {key: value for key, value in job["route"].items() if key != "estimation_profile"}
    job = store.update_job(job["id"], route=legacy, attempts=3, active_seconds=17)
    selected = Route.model_validate(legacy)
    payload = make_payload(selected, "Frozen source facts", [], [])
    request = Nexus(store, lambda _: pytest.fail("No model send")).freeze(
        job["id"], "legacy-frozen", payload, "normal", {"capacity": {"method": "historical", "input_estimate": 12345}})
    before = store.bytes(request["payload_ref"], job["id"])
    engine = Engine(store.root)
    try:
        changed = engine.configure(job["id"], route={"context_tokens": 70000})
        assert "estimation_profile" not in changed["route"]
        assert changed["route"] == {**legacy, "context_tokens": 70000}
        explicit = engine.configure(job["id"], route={"estimation_profile": "utf8_fallback_v1"})
        assert explicit["route"]["estimation_profile"] == "utf8_fallback_v1"
        assert explicit["attempts"] == 3 and explicit["active_seconds"] == 17
        assert store.get("request", request["id"]) == request
        assert store.bytes(request["payload_ref"], job["id"]) == before
        assert estimate(payload, Route.model_validate(explicit["route"]))["fallback"] == "explicit_route_fallback"
    finally:
        engine.close()


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_prospective_native_payload_matches_committed_boundary_exactly(setup, protocol):
    from test_context_coordination import accepted_batch, coordinate, offline
    from test_runtime import tool
    store, original = setup
    job = protocol_job(store, original, protocol)
    runtime = offline(store)
    try:
        state = {**state_for(job, []), "pin_views": {}}
        pending, _ = accepted_batch(runtime, job, state, "ordered-outcome",
                                    tool("context_update", {"notes": "Preserve exact source and pending dependencies."}))
        # Also support a retained checkpoint with no latest-pointer hint.
        pending.pop("context_latest", None)
        proposal = runtime.context.waiting(job["id"], pending)
        key = f"{job['id']}:{pending['seq']}:{pending['revision']}"
        preview = runtime.context.prospective(job, pending, key)
        target = {**pending, **proposal["policy"], "context_waiting": None}
        measured = preview.normal(job, target)[1]
        center = measured["input_estimate"] + measured["output_reserve"]
        choices = []
        for limit in range(center - 32, center + 33):
            route = {**job["route"], "context_tokens": limit}
            planned, capacity = preview.normal({**job, "route": route}, target)
            choices.append((capacity["fits"], limit, planned, capacity))
        assert any(not row[0] for row in choices) and any(row[0] for row in choices)
        _, limit, planned, capacity = next(row for row in choices if row[0])
        job = store.update_job(job["id"], route={**job["route"], "context_tokens": limit})
        settled = coordinate(runtime, pending)
        actual, after = runtime.context.normal(job, settled)
        assert encode(planned) == encode(actual)
        assert capacity == after and after["fits"]
        record = store.json(settled["context_feedback"], job["id"])
        assert record["feedback"]["capacity"] == {k: v for k, v in after.items() if k != "projection"}
    finally:
        runtime.close()
