"""Offline compaction progress regressions; scripted replies do not assess summary quality."""
import json
import base64
from copy import deepcopy
from hashlib import sha256
import zipfile

import httpx
import pymupdf
import pytest

from pdfmd.context import Context, HandoffRejected
from pdfmd.documents import Documents
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus
from pdfmd.runtime import Runtime
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher
from test_context_admission import image_source, outputs, protocol_job, settle, state_for, synthetic_text
from test_response_repairs import handoff, native
from test_runtime import tool


def read_batch(store, job, key, values):
    refs = [store.blob(job["id"], "evidence", {"text": value})["ref"] for value in values]
    envs = settle(store, job, key, *[tool("read_evidence", {"ref": ref}, f"{key}-{i}")
                                    for i, ref in enumerate(refs)])
    return refs, envs


def compact_body(payload):
    return json.loads(payload.get("input", payload.get("messages"))[-1]["content"])


def nearly_full_pins(store, job, context, pins=()):
    state = state_for(job, [])
    pin = store.blob(job["id"], "evidence", {"text": synthetic_text("near-full-pin", 40000)})
    state["pinned"] = [pin["ref"], *pins]
    measured = context.normal(job, state)[1]
    # Select this synthetic boundary from its complete request; this is a
    # lower test allowance, never evidence for a larger real route window.
    capacity = measured["input_estimate"] + measured["output_reserve"] + 650
    assert capacity < job["route"]["context_tokens"]
    job["route"] = {**job["route"], "context_tokens": capacity}
    store.update_job(job["id"], route=job["route"])
    assert context.normal(job, state)[1]["fits"]
    return state


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_compaction_retains_fitting_result_from_mixed_oversized_batch(setup, protocol):
    store, original_job = setup
    job = protocol_job(store, original_job, protocol)
    huge, small = synthetic_text("H", 200000), synthetic_text("S", 20000)
    refs, envs = read_batch(store, job, "mixed", [huge, small])
    read_batch(store, job, "tail", [synthetic_text("T", 50000)])
    state = state_for(job, ["mixed", "tail"])
    context = Context(store, Dispatcher(store))
    normal, capacity = context.normal(job, state)
    assert not capacity["fits"] and small in json.dumps(normal)
    payload, meta = context.compact_request(job, state)
    assert meta["capacity"]["fits"]
    assert huge not in json.dumps(payload)
    assert small in json.dumps(payload)
    assert meta["covered"][0] == "mixed" and "mixed" in meta["deferred"]
    assert meta["projection"][0] == {"request": "mixed", "refs": [envs[0]["result_ref"]]}
    assert store.json(refs[0], job["id"])["text"] == huge
    assert store.json(envs[1]["result_ref"], job["id"]) == envs[1]["data"]


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_reference_only_prefix_includes_pressure_batch_instead_of_tiny_handoff(setup, protocol):
    store, original_job = setup
    job = protocol_job(store, original_job, protocol)
    _, pinned = read_batch(store, job, "pinned", ["P" * 15000])
    pressure = [synthetic_text("A", 22000), synthetic_text("B", 22000)]
    refs, _ = read_batch(store, job, "pressure", pressure)
    state = state_for(job, ["pinned", "pressure"], [pinned[0]["result_ref"]])
    context = Context(store, Dispatcher(store))
    # Construct the actual boundary: the second batch fits alone but not with
    # its small predecessor. Derive capacity from payloads, not prompt lengths.
    roomy = {**job, "route": {**job["route"], "context_tokens": 1000000}}
    single = context.compact_request(roomy, {**state, "history": ["pressure"]})[1]["capacity"]["input_estimate"]
    joined = context.compact_request(roomy, state)[1]["capacity"]["input_estimate"]
    capacity = (single + joined) // 2 + job["route"]["output_tokens"]
    job = store.update_job(job["id"], route={**job["route"], "context_tokens": capacity})
    before = context.normal(job, state)[1]
    assert not before["fits"]
    payload, meta = context.compact_request(job, state)
    assert meta["covered"] == ["pinned", "pressure"]
    assert meta["capacity"]["fits"]
    assert any(value in json.dumps(payload) for value in pressure)
    text = json.dumps(handoff(job, cautions=["Retain unresolved source details. " * 12]))
    changed = context.apply_handoff(job, state, text, meta, "joined-handoff")
    assert changed["history"] == [] and changed["pinned"] == state["pinned"]
    assert context.normal(job, changed)[1]["fits"]
    assert [store.json(ref, job["id"])["text"] for ref in refs] == pressure


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_last_handoff_must_fit_normal_input_and_keep_history_for_correction(setup, protocol):
    store, original_job = setup
    job = protocol_job(store, original_job, protocol)
    context = Context(store, Dispatcher(store))
    state = nearly_full_pins(store, job, context)
    read_batch(store, job, "last", ["A" * 3000, "B" * 3000])
    state["history"] = ["last"]
    before = deepcopy(state)
    assert not context.normal(job, state)[1]["fits"]
    _, meta = context.compact_request(job, state)
    assert meta["covered"] == ["last"] and meta["capacity"]["fits"]
    with pytest.raises(HandoffRejected, match="last history"):
        context.apply_handoff(job, state, json.dumps(handoff(job, current_state=synthetic_text("long-handoff", 1600))), meta, "too-large-last")
    assert state == before
    assert store.json("handoff:too-large-last", job["id"])["content"]["current_state"] == synthetic_text("long-handoff", 1600)
    concise = {"task": job["scope"], "current_state": "Unfinished; original evidence retained.",
               "unfinished_work": [], "dependencies": [], "references": [], "cautions": []}
    changed = context.apply_handoff(job, state, json.dumps(concise), meta, "fitting-last")
    assert not changed["history"] and context.normal(job, changed)[1]["fits"]
    assert changed["pinned"] == state["pinned"]


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_partial_reduction_can_replace_same_handoff_while_uncovered_history_overflows(setup, protocol):
    store, original_job = setup
    job = protocol_job(store, original_job, protocol)
    small = synthetic_text("S", 20000)
    read_batch(store, job, "earlier", [synthetic_text("H", 200000), small])
    read_batch(store, job, "later", [synthetic_text("A", 30000), synthetic_text("B", 30000)])
    content = handoff(job, current_state="Unresolved source details remain. " * 20)
    previous = store.blob(job["id"], "handoff", {"content": content, "deferred": [], "originals": []})
    state = {**state_for(job, ["earlier", "later"]), "handoff": previous["ref"]}
    context = Context(store, Dispatcher(store))
    roomy = {**job, "route": {**job["route"], "context_tokens": 1000000}}
    later_size = context.compact_request(roomy, {**state, "history": ["later"]})[1]["capacity"]["input_estimate"]
    job = store.update_job(job["id"], route={**job["route"],
        "context_tokens": later_size + 256 + job["route"]["output_tokens"]})
    before = context.normal(job, state)[1]
    payload, meta = context.compact_request(job, state)
    assert meta["covered"] == ["earlier"] and small in json.dumps(payload)
    changed = context.apply_handoff(job, state, json.dumps(content), meta, "partial")
    after = context.normal(job, changed)[1]
    assert after["input_estimate"] < before["input_estimate"] and not after["fits"]
    assert changed["history"] == ["later"]
    assert context.handoff(job["id"], changed)["content"] == content
    assert store.json(changed["handoff"], job["id"])["previous_archive_ref"] == previous["ref"]
    # Another pass is possible; the final guard did not turn partial progress into a dead end.
    assert context.compact_request(job, changed)[1]["covered"] == ["later"]


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_final_handoff_correction_reopens_and_delivers_exact_source(tmp_path, route, protocol):
    path = tmp_path / "Context progress source.pdf"
    source_pixels = image_source(path)
    store = Store(tmp_path / "workspace")
    evidence = Evidence(store)
    job = protocol_job(store, evidence.create_job(str(path), "Convert the complete page and its figure.", route), protocol)
    with pymupdf.open(path) as pdf:
        xref = pdf[0].get_images(full=True)[0][0]
        source_text = pdf[0].get_text()
        pdf[0].get_pixmap().save(tmp_path / "source-page.png")
    image = evidence.extract_image(job["id"], 1, xref)
    original = Dispatcher(store).execute(job["id"], "useful-draft", "edit_document", json.dumps({
        "base_version": None, "expected_head": None, "replace_blocks": [
            {"id": "text", "pages": [1], "markdown": source_text.splitlines()[0] + "\n"},
            {"id": "figure", "pages": [1], "markdown": f"![Figure 1]({image['asset_path']})"}],
        "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "partial"}))
    assert original["ok"], original
    job = store.get("job", job["id"])
    original_version = job["head"]
    raw_candidate = ' { "text": "μg", "text": "e\\u0301" } '
    candidate = store.blob(job["id"], "candidate", raw_candidate.encode())
    context = Context(store, Dispatcher(store))
    state = nearly_full_pins(store, job, context, [image["ref"], candidate["ref"]])
    large_pin = state["pinned"][0]
    read_batch(store, job, "last", ["A" * 3000, "B" * 3000])
    state["history"] = ["last"]
    original_blobs = {r["ref"]: r["sha256"] for r in store.records("blob", job["id"])}
    seen, compactions, normal, retained = [], [], [], {}

    def reply(request):
        payload = json.loads(request.content)
        seen.append(payload)
        if not payload.get("tools"):
            compactions.append(payload)
            if len(compactions) == 1:
                store.update_job(job["id"], cancel_requested=True)
                answer = handoff(job, current_state=synthetic_text("long-handoff", 1600))
            else:
                assert len(compactions) == 2
                assert "last history" in compact_body(payload)["repair_feedback"]["message"]
                answer = handoff(job, current_state=f"Saved draft {original_version}; finish exact text and keep its image.",
                                 unfinished_work=["Read source text."], references=[], cautions=[])
            return httpx.Response(200, json=native(protocol, text=json.dumps(answer)))
        normal.append(payload)
        results = outputs(payload)
        if len(normal) == 1:
            assert "Continuation handoff" in json.dumps(payload)
            calls = [tool("context_update", {"release": [large_pin]}, "release-reviewed-material")]
        elif len(normal) == 2:
            calls = [tool("inspect_pdf", {"mode": "dict", "view": "full"}, "full-source")]
        elif len(normal) == 3:
            assert results[-1]["body_in_context"] is False
            retained["layout_ref"] = results[-1]["source_view"]["ref"]
            calls = [tool("read_evidence", {"ref": retained["layout_ref"],
                         "json_pointer": "/pages/0/content/blocks/0"}, "precise-text")]
        elif len(normal) == 4:
            block = results[-1]["data"]["value"]
            text = "\n".join("".join(s["text"] for s in line["spans"]) for line in block["lines"]) + "\n"
            assert text == source_text
            calls = [tool("edit_document", {"base_version": original_version, "expected_head": original_version,
                "operations": [{"kind": "replace", "id": "text", "blocks": [{"id": "text", "pages": [1], "markdown": text}]}],
                "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "complete"}, "finish-draft")]
        else:
            assert len(normal) == 5
            calls = [tool("report", {"state": "complete", "message": "Complete source and image saved.",
                                    "version_id": store.get("job", job["id"])["head"]}, "deliver")]
        return httpx.Response(200, json=native(protocol, *calls))

    service = Nexus(store, lambda _: "offline-fixture", httpx.MockTransport(reply))
    runtime = Runtime(store, service)
    config = {"configurable": {"thread_id": job["id"]}}
    runtime.graph.update_state(config, state, as_node="tools")
    runtime.run(job["id"])
    stopped = dict(runtime.graph.get_state(config).values)
    runtime.close()
    assert store.get("job", job["id"])["stop_reason"] == "cancelled"
    assert stopped["history"] == ["last"] and stopped["handoff"] is None
    assert stopped["repairs"]["compaction"]["count"] == 1 and len(seen) == 1
    assert store.get("job", job["id"])["attempts"] == 1
    assert stopped["pinned"] == state["pinned"]
    assert store.get("job", job["id"])["head"] == original_version
    (tmp_path / "paused-checkpoint.json").write_text(json.dumps(stopped, indent=2), encoding="utf-8")

    store = Store(store.root)
    store.update_job(job["id"], cancel_requested=False)
    runtime = Runtime(store, Nexus(store, lambda _: "offline-fixture", httpx.MockTransport(reply)))
    assert dict(runtime.graph.get_state(config).values) == stopped
    runtime.run(job["id"], continue_failed=True)
    finished = dict(runtime.graph.get_state(config).values)
    runtime.close()
    reopened = Store(store.root)
    current = reopened.get("job", job["id"])
    assert current["status"] == "completed" and current["attempts"] == len(seen) == 7
    assert current["limits"] == job["limits"] and current["active_seconds"] > 0
    assert set(finished["pinned"]) == {image["ref"], candidate["ref"]}
    assert "P" * 100 not in json.dumps(finished)  # Checkpoints keep identities, not hydrated bodies.
    assert len([e for e in reopened.events(job["id"]) if e["type"] == "response_correction"]) == 1
    assert len([e for e in reopened.events(job["id"]) if e["type"] == "context_compacted"]) == 1
    for ref, digest in original_blobs.items():
        assert sha256(reopened.bytes(ref, job["id"])).hexdigest() == digest

    # Tool access after compaction and reopening is still exact and unrestricted.
    reader = Evidence(reopened)
    layout_ref = retained["layout_ref"]
    full = reader.read(job["id"], layout_ref)
    assert full["complete"] and len(reopened.bytes(layout_ref, job["id"])) > 200000
    assert base64.b64decode(reader.read(job["id"], layout_ref, view="raw")["data"]) == reopened.bytes(layout_ref, job["id"])
    text_pointer = "/pages/0/content/blocks/0/lines/1/spans/0/text"
    exact = reader.read(job["id"], layout_ref, json_pointer=text_pointer)["value"]
    assert exact == "Keep every value: 25 mg."
    assert reader.read(job["id"], layout_ref, json_pointer=text_pointer, start=5, end=16)["value"] == exact[5:16]
    assert reopened.bytes(candidate["ref"], job["id"]).decode() == raw_candidate
    documents = Documents(reopened)
    saved = documents.version(job["id"], current["delivery"])
    assert saved["parent"] == original_version and saved["content"]["claim"] == "complete"
    assert saved["content"]["blocks"][0]["markdown"] == source_text
    assert saved["content"]["blocks"][1] == documents.version(job["id"], original_version)["content"]["blocks"][1]
    image_bytes = reopened.bytes(image["ref"], job["id"])
    assert pymupdf.Pixmap(image_bytes).samples == source_pixels
    archive = tmp_path / "delivery.zip"
    assert documents.export(job["id"], current["delivery"], str(archive))["verified"]
    with zipfile.ZipFile(archive) as exported:
        for name in exported.namelist():
            assert exported.read(name) == (documents.root / current["delivery"] / name).read_bytes()
        assert source_text in exported.read("document.md").decode()
        assert exported.read(image["asset_path"]) == image_bytes
    assert reopened.bytes(job["source_ref"], job["id"]) == path.read_bytes()
    requests = [r for r in reopened.records("request", job["id"]) if "meta" in r]
    assert len(requests) == 7 and all(r["meta"]["capacity"]["fits"] for r in requests)
    assert len(seen) == 7  # Local reads/reopen/export do not invoke a model.
    (tmp_path / "fixture-payloads.json").write_text(json.dumps(seen, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "finished-checkpoint.json").write_text(json.dumps(finished, indent=2), encoding="utf-8")
    (tmp_path / "verification.json").write_text(json.dumps({"protocol": protocol, "job": job["id"],
        "version": current["delivery"], "original_version": original_version, "source_sha256": sha256(path.read_bytes()).hexdigest(),
        "original_blobs_unchanged": len(original_blobs), "source_text_exact": True, "native_image_pixels_exact": True,
        "all_export_members_exact": True, "saved_reopened_exported": True, "full_raw_field_range_access": True,
        "correction_reopened": True, "mock_requests": 7, "live_model_calls": 0,
        "requests": requests}, indent=2), encoding="utf-8")


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_unfit_final_handoff_uses_persistent_bounded_correction(setup, protocol):
    store, original_job = setup
    job = protocol_job(store, original_job, protocol)
    job = store.update_job(job["id"], limits={**job["limits"], "max_response_repairs": 1})
    context = Context(store, Dispatcher(store))
    state = nearly_full_pins(store, job, context)
    read_batch(store, job, "last", ["A" * 3000, "B" * 3000])
    state["history"] = ["last"]
    seen = []
    def reply(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=native(protocol, text=json.dumps(handoff(job, current_state=synthetic_text("long-handoff", 1600)))))
    service = Nexus(store, lambda _: "fixture", httpx.MockTransport(reply))
    config = {"configurable": {"thread_id": job["id"]}}
    runtime = Runtime(store, service)
    runtime.graph.update_state(config, state, as_node="tools")
    runtime.run(job["id"])
    runtime.close()
    runtime = Runtime(store, service)
    runtime.run(job["id"], continue_failed=True)
    snapshot = runtime.graph.get_state(config)
    runtime.close()
    assert len(seen) == 2 and store.get("job", job["id"])["attempts"] == 2
    assert store.get("job", job["id"])["stop_reason"] == "response_repair_exhausted"
    assert snapshot.values["history"] == ["last"] and snapshot.values["handoff"] is None
    assert snapshot.values["pinned"] == state["pinned"]
    assert snapshot.values["repairs"]["compaction"]["count"] == 2
    assert len([b for b in store.records("blob", job["id"]) if b["kind"] == "handoff"]) == 2
