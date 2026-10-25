"""Complete scripted context repair and artifact delivery through the real Runtime.

This checks local mechanics, exact preservation and export contents; it does not
measure autonomous real-model choices, summary fidelity or general PDF quality.
"""
import base64
import json
from pathlib import Path

import httpx
import pymupdf
import pytest

from pdfmd.context_outcomes import policy_ref
from pdfmd.documents import Documents
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus
from pdfmd.runtime import Runtime
from pdfmd.storage import Store
from pdfmd.tools import Dispatcher
from test_context_coordination import raw_receipts, settlements, snapshot
from test_response_repairs import native
from test_runtime import tool
from test_stencil_pins import TEXT, fixture_job, verify_delivery


NOTES = "Use the source figures, preserve 25 mg and the entire requested page."


def run_coordination_delivery(directory, route, protocol):
    directory=Path(directory)
    store,job,source,mask,xref=fixture_job(directory,route,protocol)
    evidence=Evidence(store)
    images=[evidence.extract_image(job["id"],1,mask,occurrence=0,dpi=144),
            evidence.extract_image(job["id"],1,mask,occurrence=1,dpi=144),
            evidence.extract_image(job["id"],1,xref)]
    stream=images[-1]["original_ref"]
    original_stream=store.bytes(stream,job["id"])
    assert len(base64.b64encode(original_stream)) > job["route"]["context_tokens"]
    draft=Dispatcher(store).execute(job["id"],"draft","edit_document",json.dumps({
        "base_version":None,"expected_head":None,
        "replace_blocks":[{"id":"text","pages":[1],"markdown":TEXT+"\n"}],
        "page_updates":{"1":{"printed":"none","disposition":"included"}},"claim":"partial"}))
    assert draft["ok"]
    original_version=draft["data"]["version_id"]
    original_content=Documents(store).version(job["id"],original_version)
    store.update_job(job["id"],active_seconds=17)
    seen=[]
    retained={}
    active_runtime=[]
    def respond(request):
        payload=json.loads(request.content); seen.append(payload)
        assert payload.get("tools"), "This diagnosis should fit without forced compaction"
        if len(seen)==1:
            calls=[tool("context_update",{"notes":NOTES,"pin":[{"ref":stream,"view":"raw"}]},"oversize")]
        elif len(seen)==2:
            encoded=json.dumps(payload).replace('\\"','"')
            assert 'needs_agent_revision' in encoded
            assert 'required_content_exceeds_capacity' in encoded
            assert snapshot(active_runtime[0],job)["pinned"]==[]
            first=store.records("request",job["id"])[0]
            candidate=store.get("operation",f"{first['id']}:0")["candidate_ref"]
            retained["reused_candidate"]=candidate
            current_state=snapshot(active_runtime[0],job)
            calls=[tool("context_update",{
                "base":{"kind":"active","ref":policy_ref(current_state)},
                "reuse":[{"ref":candidate,"fields":["notes"]}],
                "pin":[{"ref":stream,"view":"index"},
                       {"ref":stream,"view":"raw","start":0,"end":16},
                       {"ref":images[-1]["image_ref"],"view":"image"}]},"repair")]
        elif len(seen)==3:
            state=snapshot(active_runtime[0],job)
            assert state["notes"]==NOTES
            assert state["pin_views"][stream]==[{"ref":stream,"view":"index"},
                {"ref":stream,"view":"raw","start":0,"end":16}]
            assert 'applied' in json.dumps(payload)
            figures=[{"id":f"figure{i}","pages":[1],"markdown":f"![{label}]({image['asset_path']})"}
                     for i,(label,image) in enumerate(zip(["red","blue","cmyk"],images))]
            calls=[tool("edit_document",{"base_version":original_version,"expected_head":original_version,
                "operations":[{"kind":"insert","after_id":"text","blocks":figures}],"claim":"complete"},"finish")]
        else:
            assert len(seen)==4
            calls=[tool("report",{"state":"complete","version_id":store.get("job",job["id"])["head"],
                "message":"All source text and source figures are saved."},"report")]
        return httpx.Response(200,json=native(protocol,*calls))
    transport=httpx.MockTransport(respond)
    runtime=Runtime(store,Nexus(store,lambda _:"mock-fixture-only",transport));active_runtime[:]=[runtime]
    finish=runtime.context_updates.finish
    def pause_after_disposition(*args,**kwargs):
        result=finish(*args,**kwargs)
        if settlements(store,job)[-1]["feedback"]["status"]=="needs_agent_revision":
            store.update_job(job["id"],cancel_requested=True)
        return result
    runtime.context_updates.finish=pause_after_disposition
    runtime.run(job["id"])
    before=store.get("job",job["id"])
    first_request=store.records("request",job["id"])[0]
    frozen=store.bytes(first_request["payload_ref"],job["id"])
    frozen_route=first_request["route"]
    receipt_before=raw_receipts(store,job)
    disposition_before=settlements(store,job)[-1]
    assert disposition_before["feedback"]["status"]=="needs_agent_revision"
    assert snapshot(runtime,job)["pinned"]==[] and snapshot(runtime,job)["notes"]==""
    assert before["stop_reason"]=="cancelled" and before["attempts"]==1
    assert before["active_seconds"]>=17
    assert Documents(store).version(job["id"],original_version)==original_content
    runtime.close()

    store=Store(store.root)
    store.update_job(job["id"],cancel_requested=False)
    runtime=Runtime(store,Nexus(store,lambda _:"mock-fixture-only",transport));active_runtime[:]=[runtime]
    runtime.run(job["id"])
    final=snapshot(runtime,job)
    runtime.close()
    current=store.get("job",job["id"])
    assert current["status"]=="completed",current["last_message"]
    assert current["attempts"]==len(seen)==4
    assert current["active_seconds"]>=before["active_seconds"]
    assert current["route"]==job["route"]
    assert final["notes"]==NOTES and not final.get("context_waiting")
    assert [r["feedback"]["status"] for r in settlements(store,job)]==["needs_agent_revision","applied"]
    assert settlements(store,job)[0]==disposition_before
    for ref,body in receipt_before.items():assert store.bytes(ref,job["id"])==body
    assert store.bytes(first_request["payload_ref"],job["id"])==frozen
    assert store.get("request",first_request["id"])["route"]==frozen_route
    docs=Documents(store);saved=docs.version(job["id"],current["delivery"])
    assert docs.version(job["id"],original_version)==original_content
    assert saved["content"]["blocks"][0]==original_content["content"]["blocks"][0]
    assert store.bytes(job["source_ref"],job["id"])==source.read_bytes()
    assert store.bytes(stream,job["id"])==original_stream
    evidence=Evidence(store)
    assert base64.b64decode(evidence.read(job["id"],stream,view="raw")["data"])==original_stream
    assert base64.b64decode(evidence.read(job["id"],stream,view="raw",start=4,end=18)["data"])==original_stream[4:18]
    old_args=evidence.read(job["id"],retained["reused_candidate"],json_pointer="/notes")["value"]
    assert old_args==NOTES
    assert all(r["meta"]["capacity"]["fits"] for r in store.records("request",job["id"]))
    fixture={"job":job["id"],"version":current["delivery"],"original_version":original_version,
        "source":str(source),"protocol":protocol,"attempts":current["attempts"],
        "active_seconds_before_reopen":before["active_seconds"],"active_seconds_after":current["active_seconds"],
        "reused_candidate_ref":retained["reused_candidate"],"dispositions":[r["feedback"] for r in settlements(store,job)],
        "frozen_request":first_request["id"],"images":[{"label":label,"path":im["asset_path"],
        "width":im["width"],"height":im["height"],"provenance":im}
        for label,im in zip(["red","blue","cmyk"],images)],"live_model_calls":0}
    (directory/"fixture.json").write_text(json.dumps(fixture,indent=2),encoding="utf-8")
    (directory/"payloads.json").write_text(json.dumps(seen,indent=2),encoding="utf-8")
    with pymupdf.open(source) as pdf:pdf[0].get_pixmap(dpi=144).save(directory/"source-render.png")
    assert docs.export(job["id"],current["delivery"],str(directory/"delivery.zip"))["verified"]
    assert verify_delivery(directory)["source_and_originals_preserved"]
    # Reopening the selected exported version performs no inference.
    assert Documents(Store(store.root)).version(job["id"],current["delivery"])==saved
    assert store.get("job",job["id"])["attempts"]==4
    return fixture


@pytest.mark.parametrize("protocol",["chat_completions","responses"])
def test_needs_revision_explicit_reuse_reopen_and_source_delivery(tmp_path,route,protocol):
    run_coordination_delivery(tmp_path,route,protocol)
