"""Offline handoff settlement/re-entry checks; no provider or model-quality claims."""
import base64
from copy import deepcopy
from hashlib import sha256
import json
import zipfile

import httpx
import pymupdf
import pytest

from pdfmd.context import Context, ConflictError, HandoffRejected
from pdfmd.documents import Documents
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus
from pdfmd.runtime import Runtime
from pdfmd.storage import Conflict, Store
from pdfmd.tools import Dispatcher
from test_context_admission import image_source, outputs, protocol_job
from test_context_progress import compact_body, nearly_full_pins, read_batch
from test_response_repairs import handoff, native
from test_runtime import tool


def prepared_handoff(store, job):
    context = Context(store, Dispatcher(store))
    state = nearly_full_pins(store, job, context)
    read_batch(store, job, "last", ["A" * 3000, "B" * 3000])
    state["history"] = ["last"]
    _, meta = context.compact_request(job, state)
    text = json.dumps(handoff(job, current_state="Saved work retained.",
                              unfinished_work=[], references=[], cautions=[]))
    return context, state, meta, text


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("settled", [False, True], ids=["archive-only", "applied"])
def test_receipt_distinguishes_applied_handoff_from_archived_candidate(setup, monkeypatch, protocol, settled):
    store, original_job = setup
    job = protocol_job(store, original_job, protocol)
    context, state, meta, text = prepared_handoff(store, job)
    original = deepcopy(state)
    if settled:
        applied = context.apply_handoff(job, state, text, meta, "handoff-request")
    else:
        # Archive and validation succeeded, but acceptance was not committed.
        with monkeypatch.context() as patch:
            def interrupt(*args, **kwargs):
                raise RuntimeError("before application receipt")
            patch.setattr(store, "event_once", interrupt)
            with pytest.raises(RuntimeError, match="before application receipt"):
                context.apply_handoff(job, state, text, meta, "handoff-request")
    archive = store.bytes("handoff:handoff-request", job["id"])
    events = store.events(job["id"])
    # This new instruction makes even the old concise candidate too large.
    current = store.update_job(job["id"], amendments=["Keep these additional requirements. " * 100])
    if settled:
        replayed = context.apply_handoff(current, state, text, meta, "handoff-request")
        assert replayed == applied
        assert not context.normal(current, replayed)[1]["fits"]
        # Recovered acceptance is historical; it is not permission to send oversized new input.
        runtime = Runtime(store, Nexus(store, lambda _: "fixture", httpx.MockTransport(
            lambda _: pytest.fail("No send is allowed for oversized required context"))))
        try:
            from pdfmd.nexus import StopRun
            with pytest.raises(StopRun) as stopped:
                runtime.prepare(replayed)
            assert stopped.value.reason == "capacity_blocked"
        finally:
            runtime.close()
    else:
        with pytest.raises(HandoffRejected, match="last history"):
            context.apply_handoff(current, state, text, meta, "handoff-request")
    assert store.events(job["id"]) == events
    assert store.bytes("handoff:handoff-request", job["id"]) == archive
    assert state == original
    assert store.get("job", job["id"])["attempts"] == 0


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_handoff_receipt_does_not_relax_revision_coverage_or_immutable_content(setup, protocol):
    store, original_job = setup
    job = protocol_job(store, original_job, protocol)
    context, state, meta, text = prepared_handoff(store, job)
    applied = context.apply_handoff(job, state, text, meta, "handoff-request")
    events = store.events(job["id"])
    with pytest.raises(ConflictError, match="revision"):
        context.apply_handoff(job, {**state, "revision": state["revision"] + 1}, text, meta, "handoff-request")
    with pytest.raises(ConflictError, match="revision"):
        context.apply_handoff(job, {**state, "history": ["different"]}, text, meta, "handoff-request")
    with pytest.raises(Conflict, match="immutable"):
        changed = json.dumps({**json.loads(text), "current_state": "Different content."})
        context.apply_handoff(job, state, changed, meta, "handoff-request")
    with pytest.raises(Conflict, match="immutable"):
        context.apply_handoff(job, {**state, "handoff": "different-previous"}, text, meta, "handoff-request")
    receipt = store.get("event_receipt", f"{job['id']}:context_compacted:handoff-request", job=job["id"])
    with pytest.raises(Conflict, match="original receipt"):
        store.event_once(job["id"], "context_compacted", "handoff-request", {**receipt, "after": 0})
    assert context.apply_handoff(job, state, text, meta, "handoff-request") == applied
    assert store.events(job["id"]) == events


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("amend", [False, True], ids=["unchanged", "new-instruction"])
def test_corrected_handoff_replays_across_amendment_and_delivers(tmp_path, route, protocol, amend):
    path = tmp_path / "Handoff replay source.pdf"
    source_pixels = image_source(path)
    store = Store(tmp_path / "workspace")
    job = protocol_job(store, Evidence(store).create_job(str(path), "Convert the complete page and figure.", route), protocol)
    with pymupdf.open(path) as pdf:
        source_text = pdf[0].get_text()
        xref = pdf[0].get_images(full=True)[0][0]
        pdf[0].get_pixmap().save(tmp_path / "source-page.png")
    image = Evidence(store).extract_image(job["id"], 1, xref)
    draft = Dispatcher(store).execute(job["id"], "draft", "edit_document", json.dumps({
        "base_version": None, "expected_head": None,
        "replace_blocks": [{"id": "text", "pages": [1], "markdown": source_text.splitlines()[0] + "\n"},
                           {"id": "figure", "pages": [1], "markdown": f"![Figure 1]({image['asset_path']})"}],
        "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "partial"}))
    assert draft["ok"]
    job = store.update_job(job["id"], active_seconds=17)
    original_version = job["head"]
    raw_candidate = b' { "text": "literal", "text": "e\\u0301" } '
    candidate = store.blob(job["id"], "candidate", raw_candidate)
    state = nearly_full_pins(store, job, Context(store, Dispatcher(store)), [image["ref"], candidate["ref"]])
    large_pin = state["pinned"][0]
    read_batch(store, job, "last", ["A" * 3000, "B" * 3000])
    state["history"] = ["last"]
    originals = {r["ref"]: r["sha256"] for r in store.records("blob", job["id"])}
    amendment = "Preserve the exact source wording, 25 mg, and original figure. Finish the whole page."
    seen, compactions, normal, retained = [], [], [], {}

    def reply(request):
        payload = json.loads(request.content)
        seen.append(payload)
        if not payload.get("tools"):
            compactions.append(payload)
            if len(compactions) == 1:
                answer = handoff(job, current_state="C" * 1600)
            else:
                assert len(compactions) == 2
                assert "last history" in compact_body(payload)["repair_feedback"]["message"]
                answer = handoff(job, current_state=f"Draft {original_version} retained; finish source text and preserve image.",
                                 unfinished_work=[], references=[], cautions=[])
            return httpx.Response(200, json=native(protocol, text=json.dumps(answer)))
        normal.append(payload)
        assert (amendment in json.dumps(payload)) == amend
        assert "Continuation handoff" in json.dumps(payload)
        results = outputs(payload)
        if len(normal) == 1:
            calls = [tool("context_update", {"release": [large_pin]}, "release-reviewed-pin")]
        elif len(normal) == 2:
            calls = [tool("inspect_pdf", {"mode": "dict", "view": "full"}, "full-source")]
        elif len(normal) == 3:
            assert results[-1]["body_in_context"] is False
            retained["layout_ref"] = results[-1]["source_view"]["ref"]
            calls = [tool("read_evidence", {"ref": retained["layout_ref"],
                         "json_pointer": "/pages/0/content/blocks/0"}, "precise-text")]
        elif len(normal) == 4:
            block = results[-1]["data"]["value"]
            text = "\n".join("".join(span["text"] for span in line["spans"]) for line in block["lines"]) + "\n"
            assert text == source_text
            calls = [tool("edit_document", {"base_version": original_version, "expected_head": original_version,
                "operations": [{"kind": "replace", "id": "text", "blocks": [{"id": "text", "pages": [1], "markdown": text}]}],
                "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "complete"}, "finish")]
        else:
            assert len(normal) == 5
            calls = [tool("report", {"state": "complete", "message": "Source and image saved.",
                                    "version_id": store.get("job", job["id"])["head"]}, "deliver")]
        return httpx.Response(200, json=native(protocol, *calls))

    def open_runtime():
        return Runtime(store, Nexus(store, lambda _: "offline-fixture", httpx.MockTransport(reply)))

    def interrupt_after_application(runtime):
        apply = runtime.context.apply_handoff
        def fault(*args, **kwargs):
            result = apply(*args, **kwargs)
            retained["applied"] = result
            raise RuntimeError("after application receipt, before graph checkpoint")
        runtime.context.apply_handoff = fault

    config = {"configurable": {"thread_id": job["id"]}}
    runtime = open_runtime()
    runtime.graph.update_state(config, state, as_node="tools")
    interrupt_after_application(runtime)
    try:
        with pytest.raises(RuntimeError, match="before graph checkpoint"):
            runtime.run(job["id"])
        paused = dict(runtime.graph.get_state(config).values)
    finally:
        runtime.close()
    assert paused["history"] == ["last"] and paused["handoff"] is None
    assert paused["repairs"]["compaction"]["count"] == 1
    assert len(seen) == 2 and len(normal) == 0
    initial_applied = deepcopy(retained["applied"])
    frozen = [r for r in store.records("request", job["id"]) if "payload_ref" in r]
    frozen_objects = {r[part]: store.bytes(r[part], job["id"]) for r in frozen for part in ("payload_ref", "accepted_ref")}
    failure_receipt = store.json(paused["repairs"]["compaction"]["feedback_ref"], job["id"])
    compacted_events = [e for e in store.events(job["id"]) if e["type"] == "context_compacted"]
    assert len(compacted_events) == 1
    consumed = store.get("job", job["id"])["active_seconds"]
    if amend:
        store.update_job(job["id"], amendments=[amendment])

    # Reopen, recover the accepted transition, and interrupt again at the same gap.
    store = Store(store.root)
    runtime = open_runtime()
    interrupt_after_application(runtime)
    try:
        with pytest.raises(RuntimeError, match="before graph checkpoint"):
            runtime.run(job["id"], continue_failed=True)
        assert dict(runtime.graph.get_state(config).values) == paused
    finally:
        runtime.close()
    assert retained["applied"] == initial_applied
    assert len(seen) == 2 and store.get("job", job["id"])["attempts"] == 2
    assert store.get("job", job["id"])["active_seconds"] >= consumed >= 17
    assert store.get("job", job["id"])["head"] == original_version
    assert [e for e in store.events(job["id"]) if e["type"] == "context_compacted"] == compacted_events

    store = Store(store.root)
    runtime = open_runtime()
    try:
        runtime.run(job["id"], continue_failed=True)
        finished = dict(runtime.graph.get_state(config).values)
    finally:
        runtime.close()
    store = Store(store.root)
    current = store.get("job", job["id"])
    assert current["status"] == "completed" and current["attempts"] == len(seen) == 7
    assert current["limits"] == job["limits"] and current["active_seconds"] >= consumed
    assert current["amendments"] == ([amendment] if amend else [])
    assert set(finished["pinned"]) == {image["ref"], candidate["ref"]}
    assert finished["repairs"] == {}
    assert [e for e in store.events(job["id"]) if e["type"] == "context_compacted"] == compacted_events
    assert len([e for e in store.events(job["id"]) if e["type"] == "response_correction"]) == 1
    assert store.json(paused["repairs"]["compaction"]["feedback_ref"], job["id"]) == failure_receipt
    for request in frozen:
        assert store.get("request", request["id"], job=job["id"]) == request
    for ref, raw in frozen_objects.items():
        assert store.bytes(ref, job["id"]) == raw
    for ref, digest in originals.items():
        assert sha256(store.bytes(ref, job["id"])).hexdigest() == digest

    reader = Evidence(store)
    layout = retained["layout_ref"]
    assert reader.read(job["id"], layout)["complete"]
    assert base64.b64decode(reader.read(job["id"], layout, view="raw")["data"]) == store.bytes(layout, job["id"])
    pointer = "/pages/0/content/blocks/0/lines/1/spans/0/text"
    exact = reader.read(job["id"], layout, json_pointer=pointer)["value"]
    assert exact == "Keep every value: 25 mg."
    assert reader.read(job["id"], layout, json_pointer=pointer, start=5, end=16)["value"] == exact[5:16]
    assert store.bytes(candidate["ref"], job["id"]) == raw_candidate
    documents = Documents(store)
    saved = documents.version(job["id"], current["delivery"])
    assert saved["parent"] == original_version and saved["content"]["claim"] == "complete"
    assert saved["content"]["blocks"][0]["markdown"] == source_text
    assert saved["content"]["blocks"][1] == documents.version(job["id"], original_version)["content"]["blocks"][1]
    image_bytes = store.bytes(image["ref"], job["id"])
    assert pymupdf.Pixmap(image_bytes).samples == source_pixels
    archive = tmp_path / "delivery.zip"
    assert documents.export(job["id"], current["delivery"], str(archive))["verified"]
    with zipfile.ZipFile(archive) as exported:
        for name in exported.namelist():
            assert exported.read(name) == (documents.root / current["delivery"] / name).read_bytes()
        assert source_text in exported.read("document.md").decode()
        assert exported.read(image["asset_path"]) == image_bytes
    assert store.bytes(job["source_ref"], job["id"]) == path.read_bytes()
    assert len(seen) == 7
    (tmp_path / "fixture-payloads.json").write_text(json.dumps(seen, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "paused-checkpoint.json").write_text(json.dumps(paused, indent=2), encoding="utf-8")
    (tmp_path / "finished-checkpoint.json").write_text(json.dumps(finished, indent=2), encoding="utf-8")
    (tmp_path / "verification.json").write_text(json.dumps({"protocol": protocol, "amended": amend,
        "job": job["id"], "version": current["delivery"], "original_version": original_version,
        "source_sha256": sha256(path.read_bytes()).hexdigest(), "original_blobs_unchanged": len(originals),
        "source_text_exact": True, "native_image_pixels_exact": True, "all_export_members_exact": True,
        "full_raw_field_range_access": True, "frozen_requests_unchanged": True, "replayed_without_send": True,
        "application_events": compacted_events, "failure_receipt": failure_receipt,
        "consumed_before_reopen": consumed, "consumed_after_delivery": current["active_seconds"],
        "attempts_before_replay": 2, "attempts_after_replay": 2, "mock_requests_total": 7,
        "live_model_calls": 0}, indent=2), encoding="utf-8")
