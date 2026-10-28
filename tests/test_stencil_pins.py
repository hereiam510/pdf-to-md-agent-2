"""Source-led local fixtures. No live inference or claim about model judgment."""
import base64
from copy import deepcopy
import json
from pathlib import Path
import re
import zipfile
from html.parser import HTMLParser

import httpx
import pymupdf
import pytest

from pdfmd.context import Context
from pdfmd.context_outcomes import policy_ref
from pdfmd.documents import Documents
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus, instruction_basis, parse_reply
from pdfmd.runtime import Runtime
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher
from test_context_admission import outputs, protocol_job, state_for, settle
from test_response_repairs import native
from test_runtime import tool


TEXT = "Stencil source: red and blue. Keep 25 mg."
MASK = bytes([0xAA, 0x55] * 4)


def stencil_source(path, rotation=0):
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=420, height=240)
        page.insert_text((20, 30), TEXT)
        cmyk = pymupdf.Pixmap(pymupdf.csCMYK, 128, 128, bytes([0, 180, 255, 0] * 16384), False)
        raw_xref = page.insert_image(pymupdf.Rect(240, 60, 368, 188), pixmap=cmyk)
        mask = pdf.get_new_xref()
        pdf.update_object(mask, "<</Type/XObject /Subtype/Image /Width 8 /Height 8 /ImageMask true /BitsPerComponent 1 /Decode [0 1]>>")
        pdf.update_stream(mask, MASK, compress=False)
        resources = int(pdf.xref_get_key(page.xref, "Resources")[1].split()[0])
        pdf.xref_set_key(resources, "XObject/Stencil", f"{mask} 0 R")
        content = b"\n".join(pdf.xref_stream(x) for x in page.get_contents())
        content += b"\nq 1 0 0 rg 64 0 0 64 20 116 cm /Stencil Do Q\nq 0 0 1 rg 64 0 0 64 120 116 cm /Stencil Do Q"
        stream = pdf.get_new_xref()
        pdf.update_object(stream, "<<>>")
        pdf.update_stream(stream, content)
        page.set_contents(stream)
        page.set_rotation(rotation)
        pdf.save(path)
    return mask, raw_xref


def fixture_job(directory, route, protocol="chat_completions", rotation=0):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / "Stencil source.pdf"
    mask, raw = stencil_source(source, rotation)
    store = Store(directory / "workspace")
    job = protocol_job(store, Evidence(store).create_job(str(source), "Convert the entire page with all source figures.", route), protocol)
    return store, job, source, mask, raw


def accepted(store, job, key, *calls):
    reply = parse_reply(job["route"]["protocol"], json.dumps(native(job["route"]["protocol"], *calls)).encode())
    ref = store.blob(job["id"], "accepted_response", reply)["ref"]
    store.put("request", key, job["id"], {"id": key, "accepted_ref": ref, "instruction_basis": instruction_basis(job)})


def update(runtime, job, state, intent, key="pin", extra=()):
    accepted(runtime.store, job, key, tool("context_update", intent, "pin"), *extra)
    original = {**state, "pending": key}
    completed = {**state, **runtime.tools(original)}
    env = runtime.dispatcher.envelope(job["id"], key + ":0", runtime.store.get("operation", key + ":0"))
    # Raw receipt and completed-batch decision are separate durable boundaries.
    return {**completed, **runtime.coordinate(completed)}, env, completed


def offline_runtime(store):
    def forbidden(*_):
        raise AssertionError("Unexpected inference")
    return Runtime(store, Nexus(store, forbidden, httpx.MockTransport(forbidden)))


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_stencil_component_and_selected_occurrences_match_source(tmp_path, route, rotation):
    store, job, source, mask, _ = fixture_job(tmp_path, route, rotation=rotation)
    evidence = Evidence(store)
    component = evidence.extract_image(job["id"], 1, mask)
    assert component["representation"] == "stencil_mask" and component["display_semantics"] == "coverage_only"
    assert "asset_path" not in component and component["warnings"] and len(component["occurrences"]) == 2
    assert component["original_bytes_equal"] is False
    assert base64.b64decode(evidence.read(job["id"], component["original_ref"], view="raw")["data"]) == MASK
    assert base64.b64decode(evidence.read(job["id"], component["original_ref"], start=1, end=4)["data"]) == MASK[1:4]
    assets = []
    with pymupdf.open(source) as pdf:
        for index, color in [(0, (255, 0, 0)), (1, (0, 0, 255))]:
            asset = evidence.extract_image(job["id"], 1, mask, occurrence=index, dpi=144)
            assert asset["source_image_kind"] == "stencil_mask" and asset["representation"] == "rendered_occurrence"
            assert asset["occurrence"] == index and asset["warnings"] and asset["originals"]
            clip = pymupdf.Rect(asset["region"]) * pdf[0].rotation_matrix
            expected = pdf[0].get_pixmap(dpi=144, clip=clip, alpha=False)
            actual = pymupdf.Pixmap(store.bytes(asset["ref"], job["id"]))
            assert actual.samples == expected.samples
            colors = set(tuple(actual.samples[i:i+3]) for i in range(0, len(actual.samples), 3))
            assert color in colors and (255, 255, 255) in colors
            assert (0, 0, 255) not in colors if index == 0 else (255, 0, 0) not in colors
            point = pymupdf.Point(32, 71)
            recovered = point * pymupdf.Matrix(asset["page_to_pixel"]) * pymupdf.Matrix(asset["pixel_to_page"])
            assert tuple(recovered) == pytest.approx(tuple(point))
            assets.append(asset)
        pdf[0].get_pixmap().save(tmp_path / "source-render.png")
    with pytest.raises(ValueError, match="occurrence"):
        evidence.extract_image(job["id"], 1, mask, occurrence=2)
    assert store.bytes(job["source_ref"], job["id"]) == source.read_bytes()
    (tmp_path / "occurrences.json").write_text(json.dumps({"component": component, "assets": assets}, indent=2), encoding="utf-8")


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_unadmitted_pin_preserves_policy_then_exact_views_fit_and_replay(tmp_path, route, protocol):
    store, job, source, mask, raw_xref = fixture_job(tmp_path, route, protocol)
    evidence = Evidence(store)
    image = evidence.extract_image(job["id"], 1, raw_xref)
    stream = image["original_ref"]
    exact = store.bytes(stream, job["id"])
    text = store.blob(job["id"], "evidence", {"text": "Keep 25 mg. Do not lose this.", "extra": "complete original"})["ref"]
    runtime = offline_runtime(store)
    state = state_for(job, [])
    state, first, _ = update(runtime, job, state, {"pin": [{"ref": text, "view": "full"}], "notes": "Working notes."}, "first")
    assert first["ok"] and first["data"]["admission"] == {"applied": False, "status": "saved"}
    first_decision = store.json(state["context_feedback"], job["id"])
    assert first_decision["summary"]["status"] == "applied"
    actual = runtime.context.normal(job, state)[1]
    assert first_decision["feedback"]["capacity"] == {k: v for k, v in actual.items() if k != "projection"}
    before = deepcopy(state)
    state, saved, decision_state = update(runtime, job, state, {
        "release": [text], "pin": [{"ref": stream, "view": "raw"}], "notes": "Must not replace working notes."}, "denied")
    assert saved["ok"] and not saved["data"]["admission"]["applied"]
    saved_receipt = store.bytes(saved["result_ref"], job["id"])
    denied = store.json(state["context_feedback"], job["id"])
    assert denied["summary"]["status"] == "needs_agent_revision"
    assert denied["summary"]["reason"] == "necessary_estimate_uncertain"
    assert denied["feedback"]["capacity"]["proved_excess"] is False
    for field in ["pinned", "pin_views", "released", "notes"]:
        assert state[field] == before[field]
    assert runtime.context.normal(job, state)[1]["fits"]
    # Raising capacity after O committed cannot reclassify the saved raw proposal.
    # It is a recovery control, not a capacity increase used to pass conversion.
    store.update_job(job["id"], route={**job["route"], "context_tokens": 500000})
    replay = {**decision_state, **runtime.coordinate(decision_state)}
    assert replay["context_feedback"] == state["context_feedback"] and replay["context_waiting"] is None
    assert all(replay[field] == before[field] for field in ["pinned", "pin_views", "released", "notes"])
    store.update_job(job["id"], route=job["route"])
    selected = [{"ref": stream, "view": "index"}, {"ref": stream, "view": "raw", "start": 2, "end": 7},
                {"ref": image["image_ref"], "view": "image"},
                {"ref": text, "view": "full", "json_pointer": "/text", "start": 5, "end": 11},
                {"ref": text, "view": "full", "json_pointer": "/extra"}]
    state, saved, decision_state = update(runtime, job, state,
        {"base": {"kind": "active", "ref": policy_ref(state)}, "pin": selected}, "selected")
    assert saved["ok"] and not saved["data"]["admission"]["applied"] and len(state["pin_views"][stream]) == 2
    assert store.json(state["context_feedback"], job["id"])["summary"]["status"] == "applied"
    payload, capacity = runtime.context.normal(job, state)
    assert capacity["fits"] and capacity["images"] == 1
    assert "25 mg." in json.dumps(payload) and base64.b64encode(exact[2:7]).decode() in json.dumps(payload)
    runtime.close()
    # A committed batch effect recovers even when today's limits would reject it.
    store.update_job(job["id"], route={**job["route"], "context_tokens": 4096, "output_tokens": 512})
    reopened = offline_runtime(Store(store.root))
    replay = {**decision_state, **reopened.coordinate(decision_state)}
    assert replay["pin_views"] == state["pin_views"] and replay["pinned"] == state["pinned"]
    assert store.bytes(stream, job["id"]) == exact
    assert store.bytes("result:denied:0", job["id"]) == saved_receipt
    assert store.get("job", job["id"])["attempts"] == 0
    reopened.close()


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_selected_result_pin_does_not_claim_full_body_or_pixels(tmp_path, route, protocol):
    store, job, source, mask, _ = fixture_job(tmp_path, route, protocol)
    env = settle(store, job, "inspect", tool("inspect_pdf", {"pages": [1], "mode": "text"}))[0]
    context = Context(store, Dispatcher(store))
    state = state_for(job, ["inspect"])
    state.update(context.policy(job["id"], state, {"pin": [{"ref": env["result_ref"], "view": "index"}]}))
    receipt = outputs(context.normal(job, state)[0])[0]
    assert not receipt["body_in_context"] and not receipt["body_in_message"]
    assert "selected representation" in receipt["reason"]
    assert "Stencil source" not in json.dumps(context.normal(job, state)[0])
    assert TEXT in json.dumps(context.dispatcher.evidence.read(job["id"], env["result_ref"]))
    component = context.dispatcher.evidence.extract_image(job["id"], 1, mask)
    state.update(context.policy(job["id"], state, {"pin": [{"ref": component["image_ref"], "view": "image"}]}))
    assert context.normal(job, state)[1]["images"] == 1  # Component remains available to inspect.


@pytest.mark.parametrize("intent", [
    {"view": "image"}, {"view": "index", "start": 0}, {"view": "raw", "json_pointer": "/text"},
    {"view": "full", "json_pointer": "/missing"}, {"view": "full", "json_pointer": "/text", "end": 999},
    {"view": "full", "start": True}, {"view": "full", "json_pointer": 1},
])
def test_invalid_pin_is_settled_without_changing_working_policy(setup, intent):
    store, job = setup
    ref = store.blob(job["id"], "evidence", {"text": "Keep 25 mg."})["ref"]
    runtime = offline_runtime(store)
    state = state_for(job, [])
    updated, env, _ = update(runtime, job, state, {"pin": [{"ref": ref, **intent}], "notes": "Unaccepted"})
    assert not env["ok"] and updated["pinned"] == [] and updated["notes"] == state["notes"]
    assert store.json(ref, job["id"]) == {"text": "Keep 25 mg."}
    runtime.close()


def run_delivery(directory, route, protocol):
    store, job, source, mask, raw_xref = fixture_job(directory, route, protocol)
    directory = Path(directory)
    seen, retained = [], {}
    def respond(request):
        payload = json.loads(request.content)
        seen.append(payload)
        results = outputs(payload)
        step = len(seen)
        if step == 1:
            calls = [tool("inspect_pdf", {"pages": [1], "mode": "text"}, "text"),
                     tool("extract_image", {"page": 1, "xref": mask}, "mask"),
                     tool("extract_image", {"page": 1, "xref": raw_xref}, "cmyk")]
        elif step == 2:
            retained.update(text=results[0]["data"]["value"]["pages"][0]["content"], component=results[1]["data"], cmyk=results[2]["data"])
            assert "asset_path" not in retained["component"]
            calls = [tool("context_update", {"pin": [{"ref": retained["cmyk"]["original_ref"], "view": "raw"}], "notes": "Reject this entire update"})]
        elif step == 3:
            receipt = results[-1]
            assert receipt["ok"] and receipt["data"]["admission"] == {"applied": False, "status": "saved"}
            assert receipt["data"]["context_outcome"]["status"] == "needs_agent_revision"
            assert receipt["data"]["context_outcome"]["reason"] == "necessary_estimate_uncertain"
            retained["original_context_receipt"] = (receipt["result_ref"], store.bytes(receipt["result_ref"], job["id"]))
            anchor = json.loads(next(m["content"] for m in payload.get("messages", payload.get("input")) if m.get("role") == "user"))
            calls = [tool("context_update", {"base": {"kind": "active", "ref": anchor["context_policy_ref"]}, "pin": [
                {"ref": retained["cmyk"]["original_ref"], "view": "index"},
                {"ref": retained["cmyk"]["original_ref"], "view": "raw", "start": 0, "end": 4},
                {"ref": retained["cmyk"]["image_ref"], "view": "image"}], "notes": "Preserve source colors and all content."}, "choose"),
                tool("extract_image", {"page": 1, "xref": mask, "occurrence": 0, "dpi": 144}, "red"),
                tool("extract_image", {"page": 1, "xref": mask, "occurrence": 1, "dpi": 144}, "blue")]
        elif step == 4:
            assert results[-3]["ok"] and results[-3]["data"]["context_outcome"]["status"] == "applied"
            retained["images"] = [results[-2]["data"], results[-1]["data"], retained["cmyk"]]
            blocks = [{"id": "text", "pages": [1], "markdown": retained["text"]}] + [
                {"id": f"figure{i}", "pages": [1], "markdown": f"![{label}]({image['asset_path']})"}
                for i, (label, image) in enumerate(zip(["red", "blue", "cmyk"], retained["images"]))]
            calls = [tool("edit_document", {"base_version": None, "expected_head": None, "replace_blocks": blocks,
                       "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "complete"})]
        else:
            assert step == 5
            calls = [tool("report", {"state": "complete", "version_id": store.get("job", job["id"])["head"], "message": "All source text and figures saved."})]
        return httpx.Response(200, json=native(protocol, *calls))
    runtime = Runtime(store, Nexus(store, lambda _: "fixture-only", httpx.MockTransport(respond)))
    runtime.run(job["id"])
    snapshot = dict(runtime.graph.get_state({"configurable": {"thread_id": job["id"]}}).values)
    runtime.close()
    current = store.get("job", job["id"])
    assert current["status"] == "completed" and current["attempts"] == 5
    assert snapshot["notes"] == "Preserve source colors and all content."
    original_ref, original_receipt = retained["original_context_receipt"]
    assert store.bytes(original_ref, job["id"]) == original_receipt
    assert not store.json(original_ref, job["id"])["admission"]["applied"]
    assert all(request["meta"]["capacity"]["fits"] for request in store.records("request", job["id"]))
    fixture = {"job": job["id"], "version": current["head"], "source": str(source), "protocol": protocol,
               "images": [{"label": label, "path": im["asset_path"], "width": im["width"], "height": im["height"], "provenance": im}
                          for label, im in zip(["red", "blue", "cmyk"], retained["images"])], "live_model_calls": 0}
    (directory / "fixture.json").write_text(json.dumps(fixture, indent=2), encoding="utf-8")
    (directory / "payloads.json").write_text(json.dumps(seen, indent=2), encoding="utf-8")
    with pymupdf.open(source) as pdf:
        pdf[0].get_pixmap(dpi=144).save(directory / "source-render.png")
    return fixture


def verify_delivery(directory):
    directory = Path(directory)
    fixture = json.loads((directory / "fixture.json").read_text(encoding="utf-8"))
    store = Store(directory / "workspace")
    docs = Documents(store)
    saved = docs.version(fixture["job"], fixture["version"])
    expected_labels = ["red", "blue", "cmyk"]
    assert [image["label"] for image in fixture["images"]] == expected_labels, "The fixture must contain all three source figures."
    expected_paths = [image["path"] for image in fixture["images"]]
    assert len(set(expected_paths)) == 3
    assert set(saved["assets"]) == set(expected_paths), "Saved asset inventory must match the three source figures."
    class PreviewImages(HTMLParser):
        def __init__(self):
            super().__init__()
            self.sources = []
        def handle_starttag(self, tag, attrs):
            if tag == "img":
                self.sources.append(dict(attrs).get("src"))
    with pymupdf.open(fixture["source"]) as pdf, zipfile.ZipFile(directory / "delivery.zip") as archive:
        markdown = archive.read("document.md").decode()
        assert TEXT in markdown
        assert re.findall(r"!\[[^\]]*\]\((assets/[^)]+)\)", markdown) == expected_paths
        assert {name for name in archive.namelist() if name.startswith("assets/")} == set(expected_paths)
        for preview in [archive.read("preview.html"), (docs.root / fixture["version"] / "preview.html").read_bytes()]:
            parsed = PreviewImages()
            parsed.feed(preview.decode("utf-8"))
            assert parsed.sources == expected_paths, "Saved/exported HTML must actually render the three figures."
        assert json.loads(archive.read("document.json")) == saved
        assert store.bytes(saved["source_ref"], fixture["job"]) == Path(fixture["source"]).read_bytes()
        for name in archive.namelist():
            assert archive.read(name) == (docs.root / fixture["version"] / name).read_bytes()
        for path, info in saved["originals"].items():
            assert archive.read(path) == pdf.xref_stream_raw(info["provenance"]["xref"])
        for image in fixture["images"]:
            encoded = archive.read(image["path"])
            pixels = pymupdf.Pixmap(encoded)
            assert (pixels.width, pixels.height) == (image["width"], image["height"])
            assert encoded == store.bytes(saved["assets"][image["path"]]["ref"], fixture["job"])
        for image in fixture["images"][:2]:
            meta = image["provenance"]
            expected = pdf[0].get_pixmap(dpi=144, clip=pymupdf.Rect(meta["region"]) * pdf[0].rotation_matrix)
            assert pymupdf.Pixmap(archive.read(image["path"])).samples == expected.samples
        archive.extractall(directory / "exported")
    result = {"all_source_text_present": True, "all_members_equal": True, "source_and_originals_preserved": True,
              "stencil_occurrence_pixels_equal": True, "images": len(expected_paths), "originals": len(saved["originals"]),
              "mock_attempts": store.get("job", fixture["job"])["attempts"], "live_model_calls": 0}
    (directory / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def test_delivery_verifier_rejects_text_only_false_positive(tmp_path, route):
    """A completed label and an empty verification loop do not prove delivery."""
    store, job, source, _, _ = fixture_job(tmp_path, route, "chat_completions")
    result = Dispatcher(store).execute(job["id"], "text-only", "edit_document", json.dumps({
        "base_version": None, "expected_head": None,
        "replace_blocks": [{"id": "text", "pages": [1], "markdown": TEXT + "\n"}],
        "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "complete"}))
    assert result["ok"]
    version = store.get("job", job["id"])["head"]
    assert Documents(store).export(job["id"], version, str(tmp_path / "delivery.zip"))["verified"]
    fixture = {"job": job["id"], "version": version, "source": str(source), "images": []}
    (tmp_path / "fixture.json").write_text(json.dumps(fixture), encoding="utf-8")
    with pytest.raises(AssertionError, match="all three source figures"):
        verify_delivery(tmp_path)
    fixture["images"] = [{"label": label, "path": f"assets/{label}.png"} for label in ["red", "blue", "cmyk"]]
    (tmp_path / "fixture.json").write_text(json.dumps(fixture), encoding="utf-8")
    with pytest.raises(AssertionError, match="Saved asset inventory"):
        verify_delivery(tmp_path)


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_rejected_stream_pin_can_be_revised_and_delivered_without_user_intervention(tmp_path, route, protocol):
    fixture = run_delivery(tmp_path, route, protocol)
    docs = Documents(Store(tmp_path / "workspace"))
    assert docs.export(fixture["job"], fixture["version"], str(tmp_path / "delivery.zip"))["verified"]
    assert verify_delivery(tmp_path)["images"] == 3


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_original_stream_pin_rejected_before_policy_changes(tmp_path, route, protocol):
    """Old bare-ref request reproduces the pre-change unconditional acceptance."""
    store, job, _, _, xref = fixture_job(tmp_path, route, protocol)
    ref = Evidence(store).extract_image(job["id"], 1, xref)["original_ref"]
    runtime = offline_runtime(store)
    state = state_for(job, [])
    changed, result, _ = update(runtime, job, state, {"pin": [ref], "notes": "Must be rejected."})
    assert result["ok"] and not result["data"]["admission"]["applied"]
    assert store.json(changed["context_feedback"], job["id"])["summary"]["status"] == "needs_agent_revision"
    assert changed["pinned"] == state["pinned"] and changed["notes"] == state["notes"]
    assert runtime.context.normal(job, changed)[1]["fits"]
    runtime.close()


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("admitted", [False, True])
def test_pin_receipt_pointer_gap_restores_decision_and_same_batch_policy(tmp_path, route, protocol, admitted, monkeypatch):
    store, job, _, _, xref = fixture_job(tmp_path, route, protocol)
    stream = Evidence(store).extract_image(job["id"], 1, xref)["original_ref"]
    small = store.blob(job["id"], "evidence", {"text": "Keep 25 mg."})["ref"]
    runtime = offline_runtime(store)
    state = {**state_for(job, []), "pin_views": {}}
    accepted(store, job, "batch", tool("context_update", {"pin": [{"ref": small, "view": "full"}], "notes": "Earlier accepted."}, "earlier"),
             tool("context_update", {"release": [small], "pin": [{"ref": stream, "view": "index" if admitted else "raw"}], "notes": "Later change."}, "later"))
    state["pending"] = "batch"
    original = store.put
    def fault(kind, key, owner, value):
        if kind == "operation" and key == "batch:1" and value["status"] == "done":
            raise RuntimeError("receipt saved before pointer and checkpoint")
        return original(kind, key, owner, value)
    monkeypatch.setattr(store, "put", fault)
    with pytest.raises(RuntimeError, match="receipt saved"):
        runtime.tools(state)
    monkeypatch.undo()
    raw_receipt = store.bytes("result:batch:1", job["id"])
    runtime.close()
    # No policy effect existed at the raw-result gap. Recover the complete
    # batch and decide it as one revision under the original capacity.
    reopened = offline_runtime(Store(store.root))
    completed = {**state, **reopened.tools(state)}
    assert completed["pinned"] == state["pinned"] and completed["notes"] == state["notes"]
    result = {**completed, **reopened.coordinate(completed)}
    settled = store.json(result["context_feedback"], job["id"])
    assert settled["summary"]["status"] == ("applied" if admitted else "needs_agent_revision")
    assert result["pinned"] == ([stream] if admitted else state["pinned"])
    assert result["released"] == ([small] if admitted else state["released"])
    assert result["notes"] == ("Later change." if admitted else state["notes"])
    assert store.bytes("result:batch:1", job["id"]) == raw_receipt
    reopened.close()
    # After the settlement, changed settings cannot reverse its historical effect.
    store.update_job(job["id"], route={**job["route"], "context_tokens": 4096 if admitted else 500000,
                                    "output_tokens": 512 if admitted else 2048})
    reopened = offline_runtime(Store(store.root))
    replay = {**completed, **reopened.coordinate(completed)}
    assert replay["context_feedback"] == result["context_feedback"]
    assert all(replay[field] == result[field] for field in ["pinned", "pin_views", "released", "notes"])
    assert store.bytes("result:batch:1", job["id"]) == raw_receipt
    assert store.get("job", job["id"])["attempts"] == 0
    reopened.close()



@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_image_pin_configuration_failure_keeps_prior_policy(tmp_path, route, protocol):
    store, job, _, mask, _ = fixture_job(tmp_path, route, protocol)
    image = Evidence(store).extract_image(job["id"], 1, mask, occurrence=0)
    runtime = offline_runtime(store)
    state = state_for(job, [])
    for i, changes in enumerate([{"vision": False}, {"image_tokens": None}, {"image_tokens": 100000}]):
        current = store.update_job(job["id"], route={**job["route"], **changes})
        result, env, _ = update(runtime, current, state, {"base": {"kind": "active", "ref": policy_ref(state)},
            "pin": [{"ref": image["ref"], "view": "image"}], "notes": "Unaccepted"}, f"config{i}")
        assert result["notes"] == state["notes"] and result["pinned"] == []
        decided = store.json(result["context_feedback"], job["id"])["summary"]
        assert decided["status"] == "needs_agent_revision"
        assert decided["reason"] == ["invalid_revision", "unknown_capacity_agent_choice", "necessary_estimate_uncertain"][i]
        assert env["ok"] is (i != 0)
        state = result
    runtime.close()
