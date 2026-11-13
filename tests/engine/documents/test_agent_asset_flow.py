"""Agent-facing evidence-to-save flow through the normal runtime loop (offline).

A scripted Chat Completions model drives the real Runtime, Nexus transport and
tool dispatch with no provider access. Every handle it sends (image xref, render
and extract refs, registered hash path, version and occurrence IDs) is read from
the tool results returned in the request payload, not from the store. The flow
follows the published guidance: create a rendered page and extracted figure in
the first enriched save, correct the figure, then report completion. The saved,
reopened and exported versions are then checked.

This establishes the application wiring and the information tool results give an
agent. It does not show whether a real model chooses this path.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote
import zipfile

import httpx
import pymupdf
import pytest

from pdfmd.documents import Documents
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus
from pdfmd.runtime import Runtime
from pdfmd.storage import Store

TITLE = "Harbour Studies"


def make_source(path: Path) -> Path:
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 48, 32), False)
    pix.set_rect(pymupdf.IRect(0, 0, 24, 32), (20, 80, 160))
    pix.set_rect(pymupdf.IRect(24, 0, 48, 32), (220, 200, 90))
    with pymupdf.open() as pdf:
        one = pdf.new_page(width=400, height=500)
        one.insert_text((40, 50), TITLE, fontsize=18)
        one.insert_image(pymupdf.Rect(40, 80, 280, 240), stream=pix.tobytes("jpeg"))
        one.insert_text((40, 260), "Figure 1 Harbour map.", fontsize=10)
        one.insert_text((360, 480), "7", fontsize=10)
        two = pdf.new_page(width=400, height=500)
        two.insert_text((40, 50), "Field notes continue without a page number.", fontsize=10)
        pdf.save(path)
    return path


def response(*calls, text=None):
    return {"id": "scripted-reply", "choices": [{"finish_reason": "tool_calls" if calls else "stop",
            "message": {"role": "assistant", "content": text, "tool_calls": list(calls)}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50}}


def call(name, arguments, key):
    return {"id": key, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)}}


def ev(ref, page, note):
    return [{"ref": ref, "physical_page": page, "region": None, "note": note}]


def known(value, ref, page, note):
    return {"state": "known", "value": value, "basis": ev(ref, page, note), "alternatives": []}


def results(payload) -> dict:
    """Tool results in this request, keyed by tool call ID."""
    return {m["tool_call_id"]: json.loads(m["content"]) for m in payload["messages"] if m["role"] == "tool"}


class ScriptedAgent:
    """Chooses each step only from the request payload it receives."""

    def __init__(self):
        self.payloads, self.trace = [], []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        self.payloads.append(payload)
        step = len(self.payloads)
        seen = results(payload)
        value = getattr(self, f"step{step}")(payload, seen)
        self.trace.append({"step": step, "calls": [c["function"]["name"] for c in value["choices"][0]["message"]["tool_calls"]]})
        return httpx.Response(200, json=value)

    def step1(self, payload, seen):
        self.system = payload["messages"][0]["content"]
        tools = {t["function"]["name"]: t["function"] for t in payload["tools"]}
        self.guidance = {name: tools[name]["description"] for name in ["render_page", "extract_image", "edit_document"]}
        self.edit_schema = json.dumps(tools["edit_document"]["parameters"])
        return response(call("inspect_pdf", {"pages": [1, 2], "mode": "text"}, "inspect"))

    def step2(self, payload, seen):
        pages = seen["inspect"]["data"]["value"]["pages"]
        self.text = {p["page"]: p["content"] for p in pages}
        xref = pages[0]["images"][0][0]
        return response(call("render_page", {"page": 1, "dpi": 72}, "render1"),
                        call("render_page", {"page": 2, "dpi": 72}, "render2"),
                        call("extract_image", {"page": 1, "xref": xref}, "figure"))

    def step3(self, payload, seen):
        figure = seen["figure"]["data"]
        r1, r2 = seen["render1"]["data"]["ref"], seen["render2"]["data"]["ref"]
        assert "7" in self.text[1] and TITLE in self.text[1]
        return response(call("edit_document", {
            "base_version": None, "expected_head": None, "claim": "complete",
            "replace_blocks": [
                {"id": "harbour", "pages": [1], "markdown": f"# {TITLE}\n\n![Harbour map](asset:new/map)\n\n*Figure 1* Harbour map."},
                {"id": "notes", "pages": [2], "markdown": "Field notes.\n\n[Page 2 image](asset:new/notes)"}],
            "page_updates": {"1": {"disposition": "included", "printed": "7", "printed_basis": ev(r1, 1, "printed 7 lower right")},
                             "2": {"disposition": "included", "printed": "unknown"}},
            "source_update": {"kind": "book", "title": known(TITLE, r1, 1, "heading")},
            "asset_changes": [
                {"kind": "create", "client_key": "map", "facts": {
                    "image_ref": figure["ref"],
                    "description": {"full": "Two-tone harbour map.", "filename": "Harbour map", "language": "en",
                                    "punctuation": "ascii", "basis": ev(figure["ref"], 1, "figure pixels")},
                    "caption": known("Harbour map.", r1, 1, "caption under figure"),
                    "figure": known("Figure 1", r1, 1, "caption label"),
                    "locations": [{"physical_page": 1, "region": None, "basis": ev(r1, 1, "figure on page")}]}},
                {"kind": "create", "client_key": "notes", "facts": {
                    "image_ref": r2,
                    "description": {"full": "Whole page of field notes.", "filename": "Field notes page", "language": "en",
                                    "punctuation": "ascii", "basis": ev(r2, 2, "render")},
                    "figure": {"state": "none", "value": None, "basis": ev(r2, 2, "no figure label"), "alternatives": []},
                    "locations": [{"physical_page": 2, "region": None, "basis": ev(r2, 2, "whole page")}]}}]}, "save1"))

    def step4(self, payload, seen):
        first = seen["save1"]
        assert first["ok"], first
        self.v1 = first["data"]["version_id"]
        self.created = {c["client_key"]: c for c in first["data"]["asset_changes"]}
        occurrence = self.created["map"]["occurrence_id"]
        r1 = seen["render1"]["data"]["ref"]
        return response(call("edit_document", {
            "base_version": self.v1, "expected_head": self.v1,
            "asset_changes": [{"kind": "correct", "occurrence_id": occurrence, "changes": {
                "description": {"full": "Two-tone harbour chart.", "filename": "Harbour chart", "language": "en",
                                "punctuation": "ascii", "basis": ev(r1, 1, "re-read figure")}}}]}, "save2"))

    def step5(self, payload, seen):
        second = seen["save2"]
        assert second["ok"], second
        self.v2 = second["data"]["version_id"]
        self.corrected = second["data"]["asset_changes"]
        return response(call("report", {"state": "complete", "message": "Saved the two pages with both images.",
                                        "version_id": self.v2}, "done"))


def test_scripted_agent_creates_and_corrects_enriched_images_from_tool_results(tmp_path):
    source = make_source(tmp_path / "harbour.pdf")
    store = Store(tmp_path / "workspace")
    route = {"endpoint": "http://127.0.0.1:8317/v1/chat/completions", "model": "offline-fixture",
             "context_tokens": 65536, "output_tokens": 4096}
    job = Evidence(store).create_job(str(source), "Convert both pages with their images.", route)["id"]
    agent = ScriptedAgent()
    runtime = Runtime(store, Nexus(store, lambda _: "offline-key", httpx.MockTransport(agent)))
    try:
        runtime.run(job)
    finally:
        runtime.close()

    # Tool guidance offered to the agent.
    for text in (agent.system, agent.guidance["render_page"], agent.guidance["extract_image"]):
        assert all(term in text for term in ("asset_changes", "facts.image_ref", "asset:new/<client_key>"))
    assert "legacy_path" in agent.system
    assert "asset_changes" in agent.guidance["edit_document"] and "legacy_path" in agent.edit_schema
    assert [t["calls"] for t in agent.trace] == [["inspect_pdf"], ["render_page", "render_page", "extract_image"],
                                                 ["edit_document"], ["edit_document"], ["report"]]
    current = store.get("job", job)
    assert current["status"] == "completed" and current["delivery"] == agent.v2

    documents = Documents(Store(tmp_path / "workspace"))
    v1, v2 = (documents.version(job, v) for v in (agent.v1, agent.v2))
    names = {key: Path(change["asset_path"]).name for key, change in agent.created.items()}
    assert names == {"map": "Harbour map-p7-Figure 1.jpeg", "notes": "Field notes page-i2.png"}
    assert v1["schema_version"] == 2 and set(v1["assets"]) == {c["asset_path"] for c in agent.created.values()}
    [correction] = agent.corrected
    assert Path(correction["asset_path"]).name == "Harbour chart-p7-Figure 1.jpeg"
    assert correction["previous_path"] == agent.created["map"]["asset_path"]
    record = v2["assets"][correction["asset_path"]]["provenance"]
    assert record["source"]["title"]["value"] == TITLE
    assert [(l["physical_page"], l["printed"]["state"], l["printed"]["value"]) for l in record["locations"]] == [(1, "known", "7")]
    notes = v2["assets"][agent.created["notes"]["asset_path"]]["provenance"]
    assert [(l["physical_page"], l["printed"]["state"]) for l in notes["locations"]] == [(2, "unknown")]
    out = tmp_path / "out" / "harbour.zip"
    receipt = documents.export(job, agent.v2, str(out))
    files = store.get("version", agent.v2, job=job)["files"]
    with zipfile.ZipFile(out) as archive:
        members = {n: archive.read(n) for n in archive.namelist()}
    assert receipt["verified"] and set(members) == set(files)
    assert all(sha256(d).hexdigest() == files[n] for n, d in members.items())
    markdown = members["document.md"].decode()
    linked = {unquote(p) for p in re.findall(r"\]\((assets/[^)\s]+)\)", markdown)}
    assert linked == set(v2["assets"]) == {correction["asset_path"], agent.created["notes"]["asset_path"]}
    assert current["attempts"] == 5 and len(agent.payloads) == 5

    if os.environ.get("PDFMD_AGENT_FLOW_REPORT"):
        Path(os.environ["PDFMD_AGENT_FLOW_REPORT"]).write_text(json.dumps({
            "job": job, "versions": [agent.v1, agent.v2], "trace": agent.trace,
            "created": agent.created, "corrected": agent.corrected, "guidance": {"system": agent.system, **agent.guidance},
            "export_zip_members": sorted(members), "requests_to_scripted_model": len(agent.payloads),
            "store_request_records": len(store.records("request", job))}, ensure_ascii=False, indent=1), encoding="utf-8")


@pytest.mark.parametrize("enriched_base", [False, True])
@pytest.mark.parametrize(("markdown", "guidance"), [
    ("![Map](asset:new/map)", "asset_changes create with client_key 'map'"),
    ("![Map](asset:id/0123456789abcdef)", "schema 2 base"),
    ("![Map](asset:new/map.v1)", "Invalid input asset handle"),
    ("![Map](asset:NEW/map)", "Invalid input asset handle"),
    ("<asset:new/map>", "need inline/reference links or HTML attributes"),
])
def test_handle_rejection_guides_to_a_successful_retry(tmp_path, enriched_base, markdown, guidance):
    from pdfmd.tools import Dispatcher

    source = make_source(tmp_path / "harbour.pdf")
    store = Store(tmp_path / "workspace")
    dispatcher = Dispatcher(store)
    job = dispatcher.evidence.create_job(str(source), "Handle guidance check only.")["id"]
    render = dispatcher.evidence.render_page(job, 1, 72)
    basis = ev(render["ref"], 1, "page")
    page = {"1": {"disposition": "included", "printed": "7", "printed_basis": basis}}
    create = {"kind": "create", "client_key": "map", "facts": {
        "image_ref": render["ref"],
        "description": {"full": "Whole page.", "filename": "Harbour page", "language": "en", "punctuation": "ascii", "basis": basis},
        "figure": {"state": "none", "value": None, "basis": basis, "alternatives": []},
        "locations": [{"physical_page": 1, "region": None, "basis": basis}]}}
    base = None

    def request(text, changes=()):
        return {"base_version": base, "expected_head": base, "page_updates": page, "asset_changes": list(changes),
                "replace_blocks": [{"id": "b", "pages": [1], "markdown": text}]}

    if enriched_base:
        initial = request("Harbour notes.")
        initial["source_update"] = {"title": known(TITLE, render["ref"], 1, "visible title")}
        saved = dispatcher.execute(job, "base", "edit_document", json.dumps(initial))
        assert saved["ok"], saved
        base = saved["data"]["version_id"]

    raw = json.dumps(request(markdown))
    rejected = dispatcher.execute(job, "rejected", "edit_document", raw)
    assert not rejected["ok"]
    message = rejected["data"]["error"]
    assert guidance in message and "in block b" in message
    assert "registered assets/ path" not in message
    if markdown == "![Map](asset:new/map)":
        assert "facts.image_ref" in message
    assert store.get("job", job)["head"] == base
    assert store.bytes(rejected["candidate_ref"], job) == raw.encode("utf-8")

    fixed = dispatcher.execute(job, "fixed", "edit_document", json.dumps(request("![Map](asset:new/map)", [create])))
    assert fixed["ok"], fixed
    assert Path(fixed["data"]["asset_changes"][0]["asset_path"]).name == "Harbour page-p7.png"
