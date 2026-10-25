"""Offline input/delivery checks. Scripted replies do not measure model judgment."""
import base64
from copy import deepcopy
from hashlib import sha256
import json
import random
import zipfile

import httpx
import pymupdf
import pytest

from pdfmd.context import Context, estimate
from pdfmd.documents import Documents
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus, StopRun, instruction_basis, parse_reply
from pdfmd.runtime import Runtime
from pdfmd.schema import Route
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher
from test_response_repairs import handoff, native
from test_runtime import tool


def protocol_job(store, job, protocol):
    return store.update_job(job["id"], route={**job["route"], "protocol": protocol, "vision": True,
        "image_tokens": 1024, "endpoint": "http://127.0.0.1:8317/v1/" + (
            "responses" if protocol == "responses" else "chat/completions")})


def settle(store, job, key, *calls):
    value = native(job["route"]["protocol"], *calls)
    if job["route"]["protocol"] == "responses":
        value["output"].insert(0, {"type": "reasoning", "encrypted_content": "unchanged-opaque-item", "summary": []})
    reply = parse_reply(job["route"]["protocol"], json.dumps(value).encode())
    accepted = store.blob(job["id"], "accepted_response", reply)
    store.put("request", key, job["id"], {"id": key, "accepted_ref": accepted["ref"], "instruction_basis": instruction_basis(job)})
    dispatcher = Dispatcher(store)
    return [dispatcher.execute(job["id"], f"{key}:{i}", c["name"], c["arguments"]) for i, c in enumerate(reply["calls"])]


def state_for(job, history, pins=()):
    return {"job": job["id"], "seq": 10, "revision": 1, "history": history, "handoff": None, "terminal": False,
            "notes": "Preserve exact source scope and all values.", "released": [], "pinned": list(pins)}


def outputs(payload):
    return [json.loads(m.get("output", m.get("content"))) for m in payload.get("input", payload.get("messages"))
            if m.get("role") == "tool" or m.get("type") == "function_call_output"]


def image_source(path):
    # Incompressible native RGB image reproduces dict/rawdict Base64 pressure.
    pixels = random.Random(42).randbytes(512 * 512 * 3)
    pix = pymupdf.Pixmap(pymupdf.csRGB, 512, 512, pixels, False)
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=420, height=480)
        page.insert_text((35, 35), "Capacity fixture\nKeep every value: 25 mg.\nFigure 1. Unchanged source pixels.")
        page.insert_image(pymupdf.Rect(35, 100, 385, 450), pixmap=pix)
        pdf.save(path)
    return pixels


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("mode", ["dict", "rawdict"])
def test_large_first_full_result_is_explicitly_deferred_with_exact_reads(tmp_path, route, protocol, mode):
    path = tmp_path / "source.pdf"
    image_source(path)
    store = Store(tmp_path / "workspace")
    job = protocol_job(store, Evidence(store).create_job(str(path), "Convert the complete page.", route), protocol)
    env = settle(store, job, "extract", tool("inspect_pdf", {"pages": [1], "mode": mode, "view": "full"}))[0]
    original = store.bytes(env["result_ref"], job["id"])
    assert len(original) > 1000000
    state = state_for(job, ["extract"])
    before = deepcopy(state)
    context = Context(store, Dispatcher(store))
    payload, capacity = context.normal(job, state)
    assert capacity["fits"] and capacity["images"] == 0
    assert capacity["projection"]["before_admission_estimate"] > 1000000
    assert capacity["projection"]["deferred"] == [{"request": "extract", "refs": [env["result_ref"]]}]
    deferred = outputs(payload)[0]
    assert deferred["ok"] and not deferred["body_in_context"]
    assert deferred["coverage"] == env["data"]["value"]["coverage"]
    assert deferred["warnings"] == env["data"]["value"]["warnings"]
    assert deferred["source_view"]["ref"] == env["data"]["ref"]
    assert not deferred["source_view"]["body_in_message"]
    evidence = Evidence(store)
    assert evidence.read(job["id"], **deferred["read"])["value"] == env["data"]
    assert evidence.read(job["id"], env["data"]["ref"])["value"] == env["data"]["value"]
    raw = evidence.read(job["id"], env["result_ref"], view="raw", start=15, end=131)
    assert base64.b64decode(raw["data"]) == original[15:131]
    blocks = env["data"]["value"]["pages"][0]["content"]["blocks"]
    index = next(i for i, b in enumerate(blocks) if b["type"] == 1)
    pointer = f"/pages/0/content/blocks/{index}/image/data"
    selected = evidence.read(job["id"], env["data"]["ref"], json_pointer=pointer, start=100, end=240)
    assert selected["value"] == blocks[index]["image"]["data"][100:240]
    if protocol == "responses":
        assert any(m.get("encrypted_content") == "unchanged-opaque-item" for m in payload["input"])
        assert [m["call_id"] for m in payload["input"] if m.get("type") == "function_call"] == [
            m["call_id"] for m in payload["input"] if m.get("type") == "function_call_output"]
    else:
        assert payload["messages"][2]["tool_calls"][0]["function"]["arguments"] == json.dumps({"pages": [1], "mode": mode, "view": "full"})
    assert state == before and store.bytes(env["result_ref"], job["id"]) == original
    # Preparing/freezing is local and does not invoke credentials or transport.
    def forbidden(*_):
        raise AssertionError("Unexpected model dispatch")
    runtime = Runtime(store, Nexus(store, forbidden, httpx.MockTransport(forbidden)))
    pending = runtime.prepare(state)["pending"]
    record = store.get("request", pending)
    assert record["meta"]["capacity"] == capacity and record["attempts"] == []
    runtime.close()
    reopened = Store(store.root)
    assert Context(reopened, Dispatcher(reopened)).normal(job, state) == (payload, capacity)


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_pins_survive_prefix_compaction_and_restart_without_retaining_history(setup, protocol):
    store, original_job = setup
    job = protocol_job(store, original_job, protocol)
    envs = settle(store, job, "first", tool("inspect_pdf", {"pages": [1]}, "text"),
                  tool("render_page", {"page": 1, "dpi": 72}, "pixels"))
    pins = [envs[0]["result_ref"], envs[0]["candidate_ref"], envs[1]["data"]["image_ref"]]
    large = [store.blob(job["id"], "evidence", {"text": value})["ref"]
             for value in ("large" * 40000, "A" * 30000, "B" * 30000)]
    settle(store, job, "pressure", *[tool("read_evidence", {"ref": ref}, f"r{i}") for i, ref in enumerate(large)])
    state = state_for(job, ["first", "pressure"], pins)
    context = Context(store, Dispatcher(store))
    originals = {ref: store.bytes(ref, job["id"]) for ref in [*pins, *large]}
    assert not context.normal(job, state)[1]["fits"]
    payload, meta = context.compact_request(job, state)
    assert estimate(payload, Route.model_validate(job["route"]))["fits"]
    assert meta["covered"] == ["first", "pressure"] and meta["deferred"] == ["pressure"]
    assert "Keep every value: 25 mg." in json.dumps(payload)
    changed = context.apply_handoff(job, state, json.dumps(handoff(job)), meta, "handoff-pins")
    assert changed["history"] == [] and changed["pinned"] == pins
    # Persist only references with the real checkpointer, then reopen it.
    runtime = Runtime(store, Nexus(store, lambda _: "unused"))
    runtime.graph.update_state({"configurable": {"thread_id": job["id"]}}, changed, as_node="tools")
    runtime.close()
    reopened = Store(store.root)
    runtime = Runtime(reopened, Nexus(reopened, lambda _: "unused"))
    restored = runtime.graph.get_state({"configurable": {"thread_id": job["id"]}}).values
    result, capacity = runtime.context.normal(job, restored)
    runtime.close()
    assert capacity["fits"] and capacity["images"] == 1
    assert "Keep every value: 25 mg." in json.dumps(result)
    assert json.dumps(result).count("data:image/png;base64,") == 1
    assert outputs(result) == []  # Original native batch is gone; the pin is not.
    assert {ref: reopened.bytes(ref, job["id"]) for ref in originals} == originals
    released = {**restored, "pinned": [], "released": pins}
    assert Context(reopened, Dispatcher(reopened)).normal(job, released)[1]["images"] == 0


def test_fitting_reads_stay_full_aggregate_pressure_is_not_arbitrary_eviction(setup):
    store, job = setup
    refs = [store.blob(job["id"], "evidence", {"text": value})["ref"] for value in ("a" * 30000, "b" * 30000)]
    envs = settle(store, job, "both", *[tool("read_evidence", {"ref": ref}, str(i)) for i, ref in enumerate(refs)])
    payload, capacity = Context(store, Dispatcher(store)).normal(job, state_for(job, ["both"]))
    assert not capacity["fits"] and capacity["projection"]["deferred"] == []
    assert [o["data"] for o in outputs(payload)] == [e["data"] for e in envs]


def test_individually_unfit_pixels_keep_result_metadata_and_exact_original(setup):
    store, job = setup
    job = protocol_job(store, job, "responses")
    job = store.update_job(job["id"], route={**job["route"], "image_tokens": 100000})
    env = settle(store, job, "pixels", tool("render_page", {"page": 1, "dpi": 72}))[0]
    image_ref = env["data"]["image_ref"]
    original = store.bytes(image_ref, job["id"])
    state = state_for(job, ["pixels"])
    context = Context(store, Dispatcher(store))
    payload, capacity = context.normal(job, state)
    assert capacity["fits"] and capacity["images"] == 0
    assert capacity["projection"]["deferred"] == [{"request": "pixels", "refs": [image_ref]}]
    result = outputs(payload)[0]
    assert result["data"] == env["data"] and not result["pixels_delivered"]
    assert result["image_ref"] == image_ref and "not included" in result["pixel_note"]
    assert store.bytes(image_ref, job["id"]) == original
    assert Evidence(store).read(job["id"], image_ref)["image_ref"] == image_ref
    pinned = {**state, "pinned": [image_ref]}
    # The actual text-only compaction can fit even though this pinned-pixel
    # normal continuation is unreachable. The coordinator, not a mismatched
    # normal guard inside the compaction builder, must stop that futile route.
    compact_payload, compact_meta = context.compact_request(job, pinned)
    assert compact_meta["capacity"]["fits"] and "data:image" not in json.dumps(compact_payload)
    runtime = Runtime(store, Nexus(store, lambda _: pytest.fail("No inference for blocked input")))
    try:
        with pytest.raises(StopRun) as stopped:
            runtime.prepare(pinned)
        assert stopped.value.reason == "capacity_blocked"
        assert not store.records("request", job["id"])[-1].get("payload_ref")
    finally:
        runtime.close()
    assert store.bytes(image_ref, job["id"]) == original


def test_large_authored_candidate_retains_exact_unicode_and_field_range_access(setup):
    store, job = setup
    markdown = "本文件 μg / e\u0301 / **literal**\n" * 12000
    args = {"base_version": None, "expected_head": None, "replace_blocks": [
        {"id": "section", "pages": [1], "markdown": markdown}], "page_updates": {"2": {"printed": "none"}}}
    env = settle(store, job, "candidate", tool("edit_document", args))[0]
    assert not env["ok"] and store.get("job", job["id"])["head"] is None
    state = state_for(job, ["candidate"])
    payload, capacity = Context(store, Dispatcher(store)).normal(job, state)
    assert capacity["fits"] and env["candidate_ref"] in capacity["projection"]["deferred"][0]["refs"]
    args_view = json.loads(payload["messages"][2]["tool_calls"][0]["function"]["arguments"])
    assert args_view["archived_arguments_ref"] == env["candidate_ref"]
    evidence = Evidence(store)
    assert evidence.read(job["id"], env["candidate_ref"])["value"] == args
    assert evidence.read(job["id"], env["candidate_ref"], json_pointer="/replace_blocks/0/markdown",
                         start=7, end=61)["value"] == markdown[7:61]
    with pytest.raises(StopRun, match="No fitting compaction segment"):
        Context(store, Dispatcher(store)).compact_request(job, {**state, "pinned": [env["candidate_ref"]]})


def test_pin_retains_authored_candidate_syntax_and_metadata_with_arbitrary_shapes(setup):
    store, job = setup
    raw = ' { "text": "μg", "text": "e\\u0301" } '
    candidate = store.blob(job["id"], "candidate", raw.encode())
    context = Context(store, Dispatcher(store))
    messages = context.pins(job, state_for(job, [], [candidate["ref"]]))
    pinned = json.loads(messages[0]["content"].split("\n", 1)[1])
    assert pinned[0]["view"]["value"] == raw
    data = {"warnings": "outer diagnostic", "coverage": "outer", "value": {
        "warnings": {"source key": "untrusted text"}, "coverage": "inner"}}
    result = store.blob(job["id"], "tool_result", data)
    envelope = {"ok": True, "result_ref": result["ref"], "candidate_ref": candidate["ref"], "data": data}
    deferred = context.omitted_result(job, envelope, "capacity deferred; relevance unresolved")
    assert deferred["warnings"] == data["warnings"] and deferred["selected_value_warnings"] == data["value"]["warnings"]
    assert deferred["coverage"] == "outer" and deferred["selected_value_coverage"] == "inner"


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_large_source_to_saved_reopened_exported_delivery(tmp_path, route, protocol):
    path = tmp_path / "Capacity source.pdf"
    source_pixels = image_source(path)
    store = Store(tmp_path / "workspace")
    job = protocol_job(store, Evidence(store).create_job(str(path), "Convert the complete page, including its figure.", route), protocol)
    seen, retained = [], {}
    def reply(request):
        payload = json.loads(request.content)
        assert estimate(payload, Route.model_validate(job["route"]))["fits"]
        seen.append(payload)
        results = outputs(payload)
        if len(seen) == 1:
            calls = [tool("inspect_pdf", {"mode": "dict", "view": "full"}, "full-layout")]
        elif len(seen) == 2:
            assert not results[-1]["body_in_context"]
            retained["layout_ref"] = results[-1]["source_view"]["ref"]
            calls = [tool("read_evidence", {"ref": retained["layout_ref"], "json_pointer": "/pages/0/content/blocks/0"}, "text-block"),
                     tool("read_evidence", {"ref": retained["layout_ref"], "json_pointer": "/pages/0/images"}, "image-index")]
        elif len(seen) == 3:
            block = results[-2]["data"]["value"]
            retained["text"] = "\n".join("".join(s["text"] for s in line["spans"]) for line in block["lines"]) + "\n"
            xref = results[-1]["data"]["value"][0][0]
            retained["pin"] = results[-2]["result_ref"]
            calls = [tool("context_update", {"pin": [retained["pin"]]}, "pin"),
                     tool("extract_image", {"page": 1, "xref": xref}, "source-image")]
        elif len(seen) == 4:
            assert "Pinned saved objects" in json.dumps(payload)
            assert "data:image/png;base64," in json.dumps(payload)
            retained["image"] = results[-1]["data"]
            calls = [tool("edit_document", {"base_version": None, "expected_head": None, "replace_blocks": [
                {"id": "text", "pages": [1], "markdown": retained["text"]},
                {"id": "figure", "pages": [1], "markdown": f"![Figure 1]({retained['image']['asset_path']})"}],
                "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "complete"}, "save")]
        else:
            assert len(seen) == 5
            calls = [tool("report", {"state": "complete", "message": "Complete synthetic source saved.",
                                      "version_id": store.get("job", job["id"])["head"]}, "finish")]
        return httpx.Response(200, json=native(protocol, *calls))
    runtime = Runtime(store, Nexus(store, lambda _: "offline-fixture", httpx.MockTransport(reply)))
    runtime.run(job["id"])
    runtime.close()
    reopened = Store(store.root)
    current = reopened.get("job", job["id"])
    assert current["status"] == "completed" and current["attempts"] == 5
    documents = Documents(reopened)
    saved = documents.version(job["id"], current["delivery"])
    assert saved["content"]["claim"] == "complete" and saved["content"]["pages"]["1"]["disposition"] == "included"
    with pymupdf.open(path) as source:
        assert saved["content"]["blocks"][0]["markdown"] == source[0].get_text()
        source[0].get_pixmap().save(tmp_path / "source-page.png")
    image = retained["image"]
    image_bytes = reopened.bytes(image["ref"], job["id"])
    assert pymupdf.Pixmap(image_bytes).samples == source_pixels
    archive = tmp_path / "delivery.zip"
    assert documents.export(job["id"], current["delivery"], str(archive))["verified"]
    with zipfile.ZipFile(archive) as exported:
        assert retained["text"] in exported.read("document.md").decode("utf-8")
        assert exported.read(image["asset_path"]) == image_bytes
        assert "Keep every value: 25 mg." in exported.read("preview.html").decode("utf-8")
    assert reopened.bytes(job["source_ref"], job["id"]) == path.read_bytes()
    assert len(seen) == 5  # Reopen/export never invoke the model.
    (tmp_path / "fixture-payloads.json").write_text(json.dumps(seen, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "verification.json").write_text(json.dumps({"protocol": protocol, "job": job["id"],
        "version": current["delivery"], "source_sha256": sha256(path.read_bytes()).hexdigest(),
        "source_text_exact": True, "native_image_pixels_exact": True, "exported_image_bytes_exact": True,
        "saved_reopened_exported": True, "mock_requests": len(seen), "live_model_calls": 0,
        "frozen_capacity": [r["meta"]["capacity"] for r in reopened.records("request", job["id"])]}, indent=2), encoding="utf-8")
