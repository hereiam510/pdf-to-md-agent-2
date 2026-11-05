"""Synthetic stores and native mock replies; no provider or real enrollment."""
from copy import deepcopy
import json
import random

import httpx
import pytest

from pdfmd.nexus import Nexus, StopRun
from pdfmd.evidence import Evidence
from pdfmd.runtime import Runtime
from pdfmd.storage import Conflict, Store, encode
from pdfmd.usage_anchoring import digest
from pdfmd.usage_trial import DAYS, OfflineUsageTrial
from pdfmd.working_context import PREFIX, inspect as inspect_context
from tests.engine.context.test_usage_observation import initial
from tests.engine.execution.test_runtime import tool
from tests.engine.transport.test_response_repairs import native


def fixture(setup, *, context=12000, body=8000, measured=500, veto="C", protocol="chat_completions"):
    store, job = setup
    job = store.update_job(job["id"], route={**job["route"], "context_tokens": context, "protocol": protocol,
        "endpoint": "http://127.0.0.1/v1/" + ("responses" if protocol == "responses" else "chat/completions")})
    trial = OfflineUsageTrial.create(store, "synthetic-lineage", job["route"], "Synthetic inclusive-input fixture", veto=veto)
    trial.enroll_synthetic(job["id"], "synthetic-work")
    return seed_member(store, job, trial, body=body, measured=measured)


def seed_member(store, job, trial, *, body=8000, measured=500):
    protocol = job["route"]["protocol"]
    ref = store.blob(job["id"], "evidence", {"text": "".join(random.Random(19).choices("abcdefghijklmnopqrstuvwxyz0123456789", k=body))})["ref"]
    usage_field = "prompt_tokens" if protocol == "chat_completions" else "input_tokens"
    replies = [native(protocol, tool("read_evidence", {"ref": ref}, "read")),
               native(protocol, tool("read_evidence", {"ref": ref, "view": "index"}, "read2"))]
    replies[0]["usage"] = {usage_field: measured}
    replies[1]["usage"] = {usage_field: 600}
    sent = []
    def handler(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json=replies[min(len(sent)-1, 1)])
    nexus = Nexus(store, lambda _: "synthetic", httpx.MockTransport(handler))
    runtime = Runtime(store, nexus, usage_trial=trial)
    state = initial(job)
    state.update(runtime.prepare(state))
    runtime.model(state)
    state.update(runtime.tools(state))
    return store, job, runtime, trial, state, sent, replies


def another_member(store, job, trial, *, body=8000, measured=500):
    path = store.root / "synthetic-copy.pdf"
    if not path.exists():
        path.write_bytes(store.bytes(job["source_ref"], job["id"]))
    other = Evidence(store).create_job(str(path), job["scope"], job["route"])
    peer_store = Store(store.root)
    peer = OfflineUsageTrial(peer_store, trial.lineage, clock=trial.clock)
    peer.enroll_synthetic(other["id"], "synthetic-work")
    return seed_member(peer_store, other, peer, body=body, measured=measured)


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_decisive_send_final_feedback_and_atomic_settlement(setup, protocol):
    store, job, rt, trial, state, sent, _ = fixture(setup, protocol=protocol)
    try:
        state.update(rt.coordinate(state))
        state.update(rt.prepare(state))
        request = store.get("request", state["pending"])
        a = request["meta"]["capacity"]["anchor"]
        assert a["method"] == "usage_anchor"
        d = store.get("trial_decision", a["decision_id"])
        assert not d["pf"]["capacity"]["fits"] and not d["pa"]["capacity"]["fits"]
        assert d["anchor"]["fits"] and d["pa"]["anchor"]["fits"]
        pa = store.json(request["payload_ref"], job["id"])
        pf = store.json(d["pf"]["ref"], job["id"])
        key = "messages" if protocol == "chat_completions" else "input"
        assert pa[key][:-1] == pf[key][:-1]
        summary = json.loads(pa[key][-1]["content"][len(PREFIX):])
        assert summary["input_estimate"] == a["reservation"]
        assert summary["estimate_kind"] == "usage_anchored_reservation_not_provider_bound"
        rt.model(state)
        t = trial.current()
        assert t["attempts"] == 1 and t["slot"] is None and not t["stops"]
        receipt = store.records("trial_attempt")[0]
        assert receipt["status"] == "accepted_scored" and receipt["input"] == 600
        assert len(sent) == 2
        # Re-entry consumes neither a second attempt nor another score.
        rt.nexus.send(job["id"], request["id"])
        assert len(sent) == 2 and trial.report()["scored_logical_requests"] == 1
        state.update(rt.tools(state))
        state.update(rt.prepare(state))
        assert store.get("request", state["pending"])["meta"]["capacity"]["anchor"]["method"] == "usage_anchor"
    finally:
        rt.close()


@pytest.mark.parametrize("veto", ["A", "C"])
def test_veto_commits_once_and_survives_reopen(setup, veto):
    store, job, rt, trial, state, sent, _ = fixture(setup, context=10000, body=120, measured=8000, veto=veto)
    try:
        pf, f = rt.context.normal(job, state, capacity_deferral=False)
        assert f["fits"]
        if veto == "A":
            with pytest.raises(StopRun, match="committed trial veto"):
                rt.prepare(state)
        else:
            state.update(rt.prepare(state))
            request = store.get("request", state["pending"])
            assert store.bytes(request["payload_ref"], job["id"]) == encode(pf)
            rt.model(state)
            assert len(sent) == 2
        t = trial.current()
        assert t["veto_decision"] and t["status"] == "stopped" and t["attempts"] == 0
        original = t["veto_decision"]
        rt.close()
        reopened = Runtime(store, Nexus(store, lambda _: "synthetic", httpx.MockTransport(lambda _: pytest.fail("no replay"))),
                           usage_trial=OfflineUsageTrial(store, trial.lineage))
        rt = reopened
        if veto == "A":
            with pytest.raises(StopRun, match="committed trial veto"):
                rt.prepare(state)
        else:
            rt.prepare(state)
        assert trial.current()["veto_decision"] == original
    finally:
        rt.close()


@pytest.mark.parametrize("measured,context,body,expected", [(500,65536,120,"ordinary"), (80000,12000,8000,"ordinary")])
def test_both_fit_or_both_block_preserve_ordinary_path(setup, measured, context, body, expected):
    store, job, rt, trial, state, _, _ = fixture(setup, measured=measured, context=context, body=body)
    try:
        ordinary, ordinary_meta, kind = rt.context_updates.continuation(job,state)
        state.update(rt.prepare(state))
        request=store.get("request",state["pending"])
        assert store.bytes(request["payload_ref"],job["id"])==encode(ordinary) and request["kind"]==kind
        assert request["meta"]["capacity"]["anchor"]["disposition"]==expected
        assert trial.current()["attempts"]==0 and not trial.current()["stops"]
    finally: rt.close()


@pytest.mark.parametrize("usage", [None, {"prompt_tokens": 999999}, {"prompt_tokens": 0}])
def test_accepted_missing_or_excess_usage_stops_before_slot_release(setup, usage):
    store, job, rt, trial, state, sent, replies=fixture(setup)
    replies[1]["usage"]=usage
    try:
        state.update(rt.prepare(state));rt.model(state)
        t=trial.current();r=store.get("request",state["pending"])
        assert r["status"]=="accepted" and t["slot"] is None and t["attempts"]==1
        assert t["pause"] if usage is None or usage.get("prompt_tokens")==0 else t["stops"]
        rt.nexus.send(job["id"],r["id"])
        assert len(sent)==2
        state.update(rt.tools(state));state.update(rt.prepare(state))
        next_request=store.get("request",state["pending"])
        assert next_request["meta"]["capacity"]["anchor"]["method"]=="full_local"
    finally: rt.close()


def test_offline_fence_and_default_runtime(setup):
    store,job=setup
    trial=OfflineUsageTrial.create(store,"fence",job["route"],"synthetic")
    with pytest.raises(StopRun,match="mock transport"):
        Runtime(store,Nexus(store,lambda _:pytest.fail("credentials")),usage_trial=trial)
    rt=Runtime(store,Nexus(store,lambda _:"synthetic",httpx.MockTransport(lambda _:httpx.Response(500))))
    try:
        state=initial(job);state.update(rt.prepare(state))
        assert "anchor" not in store.get("request",state["pending"])["meta"]["capacity"]
    finally: rt.close()


def test_observation_only_contract_cannot_be_mislabeled_as_trial_authority(setup):
    from pdfmd.usage_observation import UsageObserver
    store,job=setup
    trial=OfflineUsageTrial.create(store,"separate-modes",job["route"],"synthetic")
    nexus=Nexus(store,lambda _:pytest.fail("credentials"),httpx.MockTransport(lambda _:pytest.fail("send")))
    with pytest.raises(ValueError,match="separate Runtime instances"):
        Runtime(store,nexus,usage_observer=UsageObserver(store),usage_trial=trial)
    assert nexus.usage_trial is None and not store.records("request")


def test_historical_preview_keeps_governing_decision_and_fails_closed_on_missing_basis(setup):
    store,job,rt,trial,state,_,_=fixture(setup)
    try:
        state.update(rt.prepare(state));request=store.get("request",state["pending"])
        result=inspect_context(rt.context,request,job,changes={"notes":"hypothetical"})
        assert result["historical_governing"]["status"]=="available"
        assert result["preview"]["governing_trial_decision"]=="not_recomputed_full_local_hypothetical_only"
        a=request["meta"]["capacity"]["anchor"]
        with store.transaction() as db: db.execute("DELETE FROM records WHERE kind='blob' AND id=?",(a["basis_ref"],))
        result=inspect_context(rt.context,request,job)
        assert result["historical_governing"]["status"]=="unavailable"
        with pytest.raises(ValueError,match="provenance is unavailable"):
            inspect_context(rt.context,request,job,changes={"notes":"hypothetical"})
    finally: rt.close()


def test_slot_busy_does_not_wait_and_frozen_contender_cannot_spend(setup, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    store,job,rt,trial,state,_,replies=fixture(setup)
    _,job2,rt2,trial2,state2,sent2,_=another_member(store,job,trial)
    entered,release=Event(),Event()
    try:
        state.update(rt.prepare(state));state2.update(rt2.prepare(state2))
        replies[1]["usage"]=None
        original=rt.nexus._settle_accepted
        def paused_settlement(*args,**kwargs):
            entered.set()
            assert release.wait(20)
            return original(*args,**kwargs)
        monkeypatch.setattr(rt.nexus,"_settle_accepted",paused_settlement)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(rt.nexus.send,job["id"],state["pending"])
            assert entered.wait(20)
            try:
                assert trial2.current()["slot"]["job"]==job["id"]
                before=store.get("job",job2["id"])["attempts"]
                with pytest.raises(StopRun,match="slot_busy"):
                    rt2.nexus.send(job2["id"],state2["pending"])
                assert store.get("job",job2["id"])["attempts"]==before and len(sent2)==1
                # A new preparation opportunity is nonblocking and ordinary.
                new_state={**state2,"revision":state2["revision"]+1}
                new_state.update(rt2.prepare(new_state))
                a=store.get("request",new_state["pending"])["meta"]["capacity"]["anchor"]
                assert a["method"]=="full_local" and a["disposition"]=="busy"
            finally: release.set()
            future.result(timeout=20)
        assert trial2.current()["pause"] and trial2.current()["slot"] is None
        with pytest.raises(StopRun,match="paused"):
            rt2.nexus.send(job2["id"],state2["pending"])
        assert trial.report()["busy_qualified"]==2  # frozen refusal and fresh busy preparation
    finally:
        release.set();rt2.close();rt.close()


@pytest.mark.parametrize("missing", [False, True])
def test_acceptance_commit_crash_reconciles_without_coordinator_or_send(setup, monkeypatch, missing):
    store,job,rt,trial,state,sent,replies=fixture(setup)
    if missing: replies[1]["usage"]=None
    try:
        state.update(rt.prepare(state))
        def crash(*args): raise RuntimeError("fault before atomic settlement")
        monkeypatch.setattr(trial,"settle_tx",crash)
        with pytest.raises(RuntimeError,match="fault before"):
            rt.model(state)
        request=store.get("request",state["pending"])
        assert request["status"]=="in_flight" and trial.current()["slot"]
        assert store.maybe("blob",f"accepted:{request['id']}")
        rt.close()
        rt=Runtime(store,Nexus(store,lambda _:pytest.fail("credentials"),httpx.MockTransport(lambda _:pytest.fail("replay"))))
        rt.model(state)
        assert store.get("request",request["id"])["status"]=="accepted"
        assert trial.current()["slot"] is None and bool(trial.current()["pause"])==missing
        state.update(rt.tools(state));operations=store.records("operation",job["id"])
        rt.nexus.send(job["id"],request["id"])
        assert len(sent)==2 and store.records("operation",job["id"])==operations
    finally: rt.close()


def test_unresolved_claim_is_never_refunded_or_automatically_replayed(setup, monkeypatch):
    store,job,rt,trial,state,sent,_=fixture(setup)
    try:
        state.update(rt.prepare(state))
        rt.nexus.transport=httpx.MockTransport(lambda _:(_ for _ in ()).throw(httpx.ReadError("synthetic")))
        original=trial.failed_tx
        def crash(*args): raise RuntimeError("fault before failure settlement")
        monkeypatch.setattr(trial,"failed_tx",crash)
        with pytest.raises(RuntimeError,match="fault before"):
            rt.model(state)
        assert trial.current()["slot"] and trial.current()["attempts"]==1
        monkeypatch.setattr(trial,"failed_tx",original)
        trial.recover_request(job["id"],state["pending"])
        assert trial.current()["slot"] is None and trial.current()["stops"]
        assert job["id"] in trial.current()["locked_tasks"] and trial.current()["attempts"]==1
        # Even a permissive ordinary recovery policy cannot buy trial exposure.
        r=store.get("request",state["pending"]);r["replay_policy"]={"replay_unknown":True,"max_attempts_per_request":20}
        store.put("request",r["id"],job["id"],r)
        with pytest.raises(StopRun,match="stopped"):
            rt.nexus.send(job["id"],r["id"])
        assert len(sent)==1 and trial.current()["attempts"]==1
    finally: rt.close()


@pytest.mark.parametrize("ordinal", [19,20])
def test_last_claim_closes_allocations_and_pending_settlement_survives(setup, monkeypatch, ordinal):
    store,job,rt,trial,state,sent,_=fixture(setup)
    try:
        state.update(rt.prepare(state))
        t=trial.current();t["attempts"]=ordinal;store.put("usage_trial",t["id"],t["id"],t)
        if ordinal==20:
            with pytest.raises(StopRun,match="budget_exhausted"):
                rt.nexus.send(job["id"],state["pending"])
            assert len(sent)==1
        else:
            original=trial.settle_tx
            def check(db,*args):
                current=store.get_tx(db,"usage_trial",trial.lineage)
                assert current["attempts"]==20 and current["slot"]
                return original(db,*args)
            monkeypatch.setattr(trial,"settle_tx",check)
            rt.model(state)
            assert trial.current()["attempts"]==20 and trial.current()["slot"] is None
        assert trial.report()["allocation_closed"]
    finally: rt.close()


def late_evidence(store,job,request,attempt,value=600):
    return store.blob(job,"reviewed_late_usage",{"request":request["id"],"attempt":attempt,
        "accepted_ref":request["accepted_ref"],"payload_sha256":store.get("blob",request["payload_ref"])["sha256"],
        "route_sha256":digest(request["route"]),"native_usage":{"prompt_tokens":value}})["ref"]


@pytest.mark.parametrize("closure", [None,"budget","cohort","time"])
def test_late_same_attempt_attribution_needs_explicit_open_trial_resume(setup, closure):
    store,job,rt,trial,state,sent,replies=fixture(setup)
    replies[1]["usage"]=None
    try:
        state.update(rt.prepare(state));rt.model(state)
        request=store.get("request",state["pending"]);attempt=request["attempts"][-1]
        t=trial.current()
        if closure=="budget":
            t["attempts"]=20;store.put("usage_trial",t["id"],t["id"],t)
        elif closure=="cohort": trial.close_cohort()
        elif closure=="time": trial.clock=lambda:t["activated"]+DAYS
        trial.late_usage(job["id"],attempt,late_evidence(store,job["id"],request,attempt))
        assert trial.current()["pause"] and store.get("trial_attempt",attempt)["input"]==600
        if closure:
            with pytest.raises(Conflict,match="Explicit resume"):
                trial.resume(reviewed_attempt=attempt)
            trial.review_attribution(reviewed_attempt=attempt)
            assert trial.current()["pause"] and not store.get("trial_attempt",attempt)["attribution_review_required"]
        else:
            trial.resume(reviewed_attempt=attempt)
            assert trial.current()["pause"] is None
        assert len(sent)==2
    finally: rt.close()


def test_late_exceedance_rejects_after_closure_and_mismatched_attempt_is_rejected(setup):
    store,job,rt,trial,state,_,replies=fixture(setup)
    replies[1]["usage"]=None
    try:
        state.update(rt.prepare(state));rt.model(state);trial.close_cohort()
        request=store.get("request",state["pending"]);attempt=request["attempts"][-1]
        bad=late_evidence(store,job["id"],request,"another-attempt")
        with pytest.raises(Conflict,match="same accepted physical attempt"):
            trial.late_usage(job["id"],attempt,bad)
        trial.late_usage(job["id"],attempt,late_evidence(store,job["id"],request,attempt,999999))
        assert trial.report()["review"]=="reject" and job["id"] in trial.current()["locked_tasks"]
    finally: rt.close()


def test_tenth_enrollment_closes_only_intake_and_family_is_frozen(setup):
    store,job,rt,trial,state,_,_=fixture(setup)
    runtimes=[]
    try:
        for _ in range(9):
            values=another_member(store,job,trial,body=0);runtimes.append(values[2])
        t=trial.current()
        assert len(t["members"])==10 and t["intake_closed"] and not t["cohort_closed"]
        assert trial.unavailable(t,job["id"]) is None
        with pytest.raises(Conflict,match="not open"):
            another_member(store,job,trial)
        with pytest.raises(Conflict,match="cannot change"):
            trial.enroll_synthetic(job["id"],"different-work")
        for member in list(t["members"]): trial.finish_conversion(member)
        assert trial.current()["cohort_closed"] and trial.report()["enrolled_conversions"]==10
    finally:
        for runtime in runtimes: runtime.close()
        rt.close()


def test_confirmed_overflow_on_ordinary_send_stops_route_but_generic_http_is_not_confirmation(setup):
    store,job,rt,trial,state,_,_=fixture(setup,context=65536,body=120)
    try:
        state.update(rt.prepare(state))
        rt.nexus.transport=httpx.MockTransport(lambda _:httpx.Response(400,json={"error":"synthetic"}))
        with pytest.raises(StopRun,match="No context-overflow diagnosis"):
            rt.model(state)
        assert not trial.current()["stops"]
        evidence=store.blob(job["id"],"reviewed_overflow",{"confirmed":True,"note":"synthetic confirmed context overflow"})
        trial.confirm_overflow(job["id"],state["pending"],evidence["ref"])
        assert trial.current()["stops"][-1]["reason"]=="confirmed_context_overflow"
    finally: rt.close()


def test_frozen_trial_cannot_dispatch_without_injection_or_after_configuration_change(setup):
    store,job,rt,trial,state,_,_=fixture(setup)
    try:
        state.update(rt.prepare(state));request=store.get("request",state["pending"])
        plain=Nexus(store,lambda _:pytest.fail("credentials"),httpx.MockTransport(lambda _:pytest.fail("send")))
        with pytest.raises(StopRun,match="requires its offline coordinator"):
            plain.send(job["id"],request["id"])
        store.update_job(job["id"],route={**job["route"],"model":"changed"})
        with pytest.raises(StopRun,match="identity_changed"):
            rt.nexus.send(job["id"],request["id"])
        assert not store.get("request",request["id"])["attempts"]
        with pytest.raises(Conflict,match="cannot be reset"):
            OfflineUsageTrial.create(store,trial.lineage,job["route"],"synthetic")
    finally: rt.close()


def test_revocation_between_selection_and_freeze_remeasures_ordinary_and_links_prohibition(setup, monkeypatch):
    store,job,rt,trial,state,_,_=fixture(setup)
    try:
        original=rt.nexus.freeze
        fired=[]
        def revoke(*args):
            if not fired:
                fired.append(True);trial.close_cohort()
            return original(*args)
        monkeypatch.setattr(rt.nexus,"freeze",revoke)
        state.update(rt.prepare(state));request=store.get("request",state["pending"])
        a=request["meta"]["capacity"]["anchor"]
        assert a["method"]=="full_local" and a["disposition"]=="revoked_before_freeze"
        assert store.records("trial_prohibition")[0]["phase"]=="before_freeze"
        assert a["ordinary_evaluation_id"] and trial.current()["attempts"]==0
    finally: rt.close()


def test_route_change_between_selection_and_freeze_uses_fresh_ordinary_settings(setup, monkeypatch):
    store,job,rt,trial,state,sent,_=fixture(setup)
    try:
        original=rt.nexus.freeze
        fired=[]
        def change_route(*args):
            if not fired:
                fired.append(True)
                store.update_job(job["id"],route={**job["route"],"model":"explicit-new-route","context_tokens":65536})
            return original(*args)
        monkeypatch.setattr(rt.nexus,"freeze",change_route)
        state.update(rt.prepare(state));request=store.get("request",state["pending"])
        assert request["route"]["model"]=="explicit-new-route"
        assert store.json(request["payload_ref"],job["id"])["model"]=="explicit-new-route"
        assert request["meta"]["capacity"]["anchor"]["method"]=="full_local"
        assert trial.current()["attempts"]==0 and len(sent)==1
        assert store.records("trial_prohibition")[0]["reason"]=="route_changed_before_freeze"
    finally: rt.close()


def test_committed_negative_cutoff_does_not_reselect_newer_physical_evidence(setup):
    store,job,rt,trial,state,_,_=fixture(setup,context=65536,body=120)
    try:
        # An intervening unresolved physical send blocks the usable older reply.
        store.put("attempt","intervening",job["id"],{"id":"intervening","request":state["history"][-1],
            "started":9999999999,"status":"unknown"})
        result,descriptor=trial.prepare(rt.context,job,state,f"{job['id']}:{state['seq']}:{state['revision']}")
        d=store.get("trial_decision",descriptor["decision_id"])
        assert d["first_failure"]=="predecessor_not_settled_accepted"
        with store.transaction() as db: db.execute("DELETE FROM records WHERE kind='attempt' AND id='intervening'")
        state.update(rt.prepare(state))
        request=store.get("request",state["pending"])
        assert request["meta"]["capacity"]["anchor"]["decision_id"]==d["id"]
        assert store.get("trial_decision",d["id"])["first_failure"]==d["first_failure"]
    finally: rt.close()


@pytest.mark.parametrize("missing", [False,True])
def test_intermediate_stream_usage_does_not_pause_before_accepted_settlement(setup, missing):
    from tests.engine.transport.test_streaming_parser import chat,event
    store,job=setup
    job=store.update_job(job["id"],route={**job["route"],"context_tokens":12000,
        "wait_policy":{"first_progress_seconds":30,"idle_progress_seconds":30,"total_seconds":180}})
    trial=OfflineUsageTrial.create(store,"stream-fixture",job["route"],"synthetic inclusive input")
    trial.enroll_synthetic(job["id"],"synthetic-work")
    ref=store.blob(job["id"],"evidence",{"text":"".join(random.Random(17).choices("abcdef0123456789",k=10000))})["ref"]
    sent=[]
    class Bytes(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield event(chat({"role":"assistant"}))
            if len(sent)==2:
                assert trial.current()["slot"] and trial.current()["pause"] is None
            yield event(chat({"tool_calls":[{"index":0,"id":"read","type":"function",
                "function":{"name":"read_evidence","arguments":json.dumps({"ref":ref})}}]}))
            usage=None if missing and len(sent)==2 else {"prompt_tokens":500}
            yield event(chat(finish="tool_calls",usage=usage))+event("[DONE]")
    def handler(request):
        sent.append(request)
        return httpx.Response(200,headers={"content-type":"text/event-stream"},stream=Bytes())
    rt=Runtime(store,Nexus(store,lambda _:"synthetic",httpx.MockTransport(handler)),usage_trial=trial)
    try:
        state=initial(job);state.update(rt.prepare(state));rt.model(state);state.update(rt.tools(state))
        state.update(rt.prepare(state))
        assert store.get("request",state["pending"])["meta"]["capacity"]["anchor"]["method"]=="usage_anchor"
        rt.model(state)
        assert bool(trial.current()["pause"])==missing and trial.current()["slot"] is None
    finally: rt.close()


def test_ordinary_alternative_and_attributed_chain_bind_real_local_receipts_and_output(setup, tmp_path):
    from pdfmd.documents import Documents
    from tests.engine.documents.test_documents import call, edit
    store,job,rt,trial,state,sent,_=fixture(setup)
    try:
        state.update(rt.prepare(state));rt.model(state)
        request=store.get("request",state["pending"]);key=request["id"]
        state.update(rt.tools(state))
        alternative=trial.ordinary_alternative(job["id"],key)
        assert len(sent)==2 and store.json(alternative,job["id"])["disposition"]=="deferral"
        version=call(rt.dispatcher,job["id"],"synthetic-save",edit())['data']['version_id']
        export=Documents(store).export(job["id"],version,str(tmp_path/'synthetic-result.zip'))
        a=request["meta"]["capacity"]["anchor"]
        review={"request":key,"payload_sha256":a["payload_sha256"],
            "source_sha256":trial.current()["members"][job["id"]]["source_sha256"],
            "useful":True,"source_fidelity":True,"saved_reopened_exported":True,
            "reviewer":"Synthetic test declaration, no real fidelity claim", "reviewed_pages":[1],
            "review_note":"Synthetic correspondence control only", "executed_operation":f"{key}:0",
            "ordinary_alternative_ref":alternative,"version_id":version,"export_id":export["id"]}
        wrong={**review,"payload_sha256":"0"*64}
        with pytest.raises(ValueError,match="complete attributed"):
            trial.record_chain(job["id"],key,store.blob(job["id"],"review",wrong)["ref"])
        review_ref=store.blob(job["id"],"synthetic_review",review)["ref"]
        trial.record_chain(job["id"],key,review_ref);trial.record_chain(job["id"],key,review_ref)
        report=trial.report()
        assert report["reviewed_useful_recovery_chains"]==1 and report["review"]=="inconclusive"
        assert report["cost"] is None and report["savings"] is None
        # A recorded verification flag cannot hide changed exported bytes.
        with open(export["path"],"wb") as output: output.write(b"not a ZIP")
        import zipfile
        with pytest.raises(zipfile.BadZipFile): trial.record_chain(job["id"],key,review_ref)
        assert trial.report()["reviewed_useful_recovery_chains"]==0
    finally: rt.close()


@pytest.mark.parametrize("problem", [None,"concentration","unattributed","exceedance","few_sources","few_chains"])
def test_review_gate_denominators_are_separate_and_passing_only_invites_review(setup, problem, monkeypatch):
    store,job=setup
    trial=OfflineUsageTrial.create(store,"report-fixture",job["route"],"synthetic reducer fixture")
    t=trial.current();t["attempts"]=10
    for i in range(10):
        member=f"synthetic-job-{i%4}"
        family=f"family-{i%4}"
        if problem=="concentration": family="same-family"
        t["members"][member]={"job":member,"family":family,"source_sha256":("0"*64 if problem=="few_sources" else str(i%4)*64),"finished":True}
        store.put("job",member,member,{**job,"id":member})
        key=f"synthetic-request-{i}"
        store.put("trial_attempt",str(i),member,{"request":key,"job":member,"lineage":trial.lineage,
            "status":"accepted_unscorable" if problem=="unattributed" and i==9 else "accepted_scored","margin":5})
        if i<(4 if problem=="few_chains" else 5):
            store.put("trial_chain",key,member,{"id":key,"job":member,"lineage":trial.lineage,"review_ref":key})
    # This is the reporting reducer, with correspondence exercised separately
    # above against actual local receipts, saved/reopened versions and a ZIP.
    monkeypatch.setattr(trial,"check_chain",lambda member,key,ref:store.get("trial_chain",key))
    if problem=="exceedance": trial.stop(t,"reservation_exceeded",member,"synthetic")
    store.put("usage_trial",trial.lineage,trial.lineage,t)
    result=trial.report()
    assert result["physical_attempts"]==10 and result["enrolled_conversions"]==4
    assert result["busy_fraction"] is None
    expected="eligible_for_separate_expansion_review" if problem is None else "reject" if problem=="exceedance" else "inconclusive"
    assert result["review"]==expected
    assert result["fidelity"]=="not_established" and result["cost"] is None


@pytest.mark.parametrize("gate", ["cancel", "requests", "active_time"])
@pytest.mark.parametrize("veto", [False,True])
def test_ordinary_task_guards_apply_without_consuming_trial_budget(setup, gate, veto):
    store,job,rt,trial,state,sent,_=fixture(setup,context=10000 if veto else 12000,
        body=120 if veto else 8000, measured=8000 if veto else 500)
    try:
        state.update(rt.prepare(state));current=store.get("job",job["id"])
        if gate=="cancel": store.update_job(job["id"],cancel_requested=True)
        elif gate=="requests": store.update_job(job["id"],limits={**current["limits"],"max_requests":current["attempts"]})
        else: store.update_job(job["id"],active_seconds=current["limits"]["max_active_seconds"])
        with pytest.raises(StopRun): rt.nexus.send(job["id"],state["pending"])
        assert len(sent)==1 and trial.current()["attempts"]==0 and trial.current()["slot"] is None
    finally: rt.close()


def test_veto_in_another_task_preserves_outstanding_accepted_settlement(setup):
    store,job,rt,trial,state,_,_=fixture(setup)
    _,job2,rt2,trial2,state2,_,_=another_member(store,job,trial,body=120,measured=20000)
    try:
        state.update(rt.prepare(state))
        def handler(_):
            assert trial.current()["slot"]
            state2.update(rt2.prepare(state2))
            assert trial.current()["veto_decision"] and trial.current()["slot"]
            value=native("chat_completions",tool("read_evidence",{"ref":job["source_ref"],"view":"index"},"after-veto"))
            value["usage"]={"prompt_tokens":600}
            return httpx.Response(200,json=value)
        rt.nexus.transport=httpx.MockTransport(handler)
        rt.model(state)
        assert trial.current()["stops"] and trial.current()["slot"] is None
        assert store.records("trial_attempt")[0]["status"]=="accepted_scored"
    finally: rt2.close();rt.close()


@pytest.mark.parametrize("missing", ["anchor", "basis"])
def test_required_frozen_provenance_cannot_be_downgraded_to_legacy(setup, missing):
    store,job,rt,trial,state,sent,_=fixture(setup)
    try:
        state.update(rt.prepare(state));request=store.get("request",state["pending"])
        if missing=="anchor":
            request["meta"]["capacity"].pop("anchor")
            store.put("request",request["id"],job["id"],request)
        else:
            ref=request["meta"]["capacity"]["anchor"]["basis_ref"]
            with store.transaction() as db: db.execute("DELETE FROM records WHERE kind='blob' AND id=?",(ref,))
        with pytest.raises(ValueError): rt.nexus.send(job["id"],request["id"])
        result=inspect_context(rt.context,request,job)
        assert result["historical_governing"]["status"]=="unavailable"
        if missing=="basis":
            report=trial.report()
            assert report["unavailable_decision_evidence"] and "required_decision_evidence_unavailable" in report["review_reasons"]
        assert len(sent)==1 and trial.current()["attempts"]==0
    finally: rt.close()


def test_preparation_event_identity_cannot_be_shadowed_by_capacity_metadata(setup):
    store,job=setup
    nexus=Nexus(store,lambda _:"synthetic")
    nexus.freeze(job["id"],"actual-request",{"model":"synthetic"},"normal",
        {"capacity":{"request":"forged","kind":"compaction","input_estimate":12,"fits":True,"arbitrary":"private"}})
    event=[e for e in store.events(job["id"]) if e["type"]=="request_prepared"][-1]
    assert event["data"]=={"request":"actual-request","kind":"normal","input_estimate":12,"fits":True}


@pytest.mark.parametrize("missing", [False,True])
def test_native_graph_checkpoint_reopen_settles_before_report_without_replay(setup, monkeypatch, missing):
    store,job,rt,trial,state,sent,replies=fixture(setup)
    replies[1].update(native("chat_completions",tool("report",{"state":"waiting","message":"Synthetic graph acceptance."},"done")))
    replies[1]["usage"]=None if missing else {"prompt_tokens":600}
    config={"configurable":{"thread_id":job["id"]}}
    try:
        rt.graph.update_state(config,state,as_node="tools")
        def crash(*args): raise RuntimeError("synthetic graph settlement crash")
        monkeypatch.setattr(trial,"settle_tx",crash)
        with pytest.raises(RuntimeError,match="graph settlement crash"):
            rt.run(job["id"])
        snapshot=rt.graph.get_state(config)
        assert snapshot.next==("model",) and trial.current()["slot"]
        pending=snapshot.values["pending"]
        rt.close()
        reopened_trial=OfflineUsageTrial(Store(store.root),trial.lineage)
        rt=Runtime(reopened_trial.store,Nexus(reopened_trial.store,lambda _:pytest.fail("credentials"),
            httpx.MockTransport(lambda _:pytest.fail("replay"))),usage_trial=reopened_trial)
        rt.run(job["id"])
        assert store.get("request",pending)["status"]=="accepted"
        assert store.get("job",job["id"])["status"]=="waiting"
        assert reopened_trial.current()["slot"] is None and bool(reopened_trial.current()["pause"])==missing
        assert reopened_trial.current()["attempts"]==1 and len(sent)==2
        assert not rt.graph.get_state(config).next
    finally: rt.close()
