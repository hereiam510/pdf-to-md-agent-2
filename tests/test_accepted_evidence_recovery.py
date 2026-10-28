"""File-backed historical evidence; no provider or original task inputs."""
from copy import deepcopy
import json

import httpx
import pytest

from pdfmd.nexus import Nexus, make_payload
from pdfmd.runtime import Runtime
from pdfmd.schema import Route
from pdfmd.storage import Store, encode
from pdfmd.streaming import StreamDecoder
from test_response_repairs import native
from test_runtime import tool
from test_stream_terminal import Body, WAIT, forbidden
from test_streaming_delivery import stream_frames
from test_continuation import delivery, check_delivery


PROTOCOLS = ["chat_completions", "responses"]


def historical(setup, monkeypatch, protocol, published=True, *, suffix=b"data: {", calls=None, kind="normal", text=None, initial=None, endpoint=None):
    store, job = setup
    path = "chat/completions" if protocol == "chat_completions" else "responses"
    job = store.update_job(job["id"], route={**job["route"], "protocol": protocol,
        "endpoint": endpoint or "https://synthetic.invalid/v1/" + path, "wait_policy": WAIT})
    route = Route.model_validate(job["route"])
    key = job["id"] + ":0:0"
    value = native(protocol, *(calls if calls is not None else [tool("read_document", {}, "read")]), text=text)
    raw = b"".join(stream_frames(protocol, value)) + suffix
    service = Nexus(store, forbidden, httpx.MockTransport(lambda _: httpx.Response(200, stream=Body([raw]))))
    service.credentials = lambda _: "synthetic-only"
    runtime = Runtime(store, service)
    state = {"job": job["id"], "seq": 0, "revision": 0, "history": [], "handoff": None,
             "notes": "", "pinned": [], "released": [], "pending": key, "next": "compact" if kind == "compaction" else "model", **(initial or {})}
    runtime.graph.update_state({"configurable": {"thread_id": job["id"]}}, state, as_node="prepare")
    service.freeze(job["id"], key, make_payload(route, "Synthetic", [], []), kind,
                   {"covered": state["history"], "revision": state["revision"], "deferred": []} if kind == "compaction" else {})
    inflight = []
    put = store.put_tx
    with monkeypatch.context() as old:
        def capture(db, category, identity, owner, record):
            if category == "attempt" and record["status"] == "in_flight":
                inflight.append(deepcopy(record))
            return put(db, category, identity, owner, record)
        old.setattr(store, "put_tx", capture)
        old.setattr(StreamDecoder, "finish_received", lambda self: deepcopy(self.value))
        reply = service.send(job["id"], key)
    if not published:
        request = store.get("request", key)
        store.put("request", key, job["id"], {**request, "status": "in_flight", "accepted_ref": None})
        store.put("attempt", inflight[0]["id"], job["id"], inflight[0])
    runtime.close()
    return store, job, key, reply, raw


def preserved(store, job):
    return {kind: store.records(kind, job) for kind in ("request", "attempt", "stream_receive", "version")}


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("published", [False, True])
def test_diagnose_resolve_reopen_and_separate_continue(setup, monkeypatch, protocol, published):
    from pdfmd.recovery import diagnose, resolve
    store, job, key, reply, raw = historical(setup, monkeypatch, protocol, published)
    before = preserved(store, job["id"])
    blobs = {b["ref"]: (b, store.bytes(b["ref"], job["id"])) for b in store.records("blob", job["id"])}
    files = {p.name: p.read_bytes() for p in store.root.glob("*.sqlite")}
    result = diagnose(store.root, job["id"])
    assert result["eligible"] and result["receive_boundary"]["status"] == "finish_conflict"
    assert {p.name: p.read_bytes() for p in store.root.glob("*.sqlite")} == files
    resolved = resolve(store, job["id"], key, result["basis"])
    assert resolved["projection"] == "ready"
    assert preserved(store, job["id"]) == before
    assert all((store.get("blob", ref), store.bytes(ref, job["id"])) == old for ref, old in blobs.items())
    operation = store.get("operation", key + ":0")
    assert store.json(operation["result_ref"], job["id"])["execution"] == "not_started"
    reopened = Store(store.root)
    assert resolve(reopened, job["id"], key, "old-view") == resolved
    runtime = Runtime(reopened, Nexus(reopened, forbidden))
    try:
        snapshot = runtime.graph.get_state({"configurable": {"thread_id": job["id"]}})
        assert snapshot.next == ("coordinate",)
        assert snapshot.values["history"] == [key]
        assert snapshot.values["seq"] == snapshot.values["revision"] == 1
        payload, capacity = runtime.context.normal(reopened.get("job", job["id"]), snapshot.values)
        assert "conflict-resolution:" in json.dumps(payload)
        assert "not_started" in json.dumps(payload)
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("suffix,eligible", [(b": compatible", False), (b"event: unfinished", True), (b"\xe4", True)])
def test_tail_classification_is_pure(setup, monkeypatch, protocol, suffix, eligible):
    from pdfmd.recovery import diagnose
    store, job, _, _, _ = historical(setup, monkeypatch, protocol, suffix=suffix)
    before = {p.relative_to(store.root).as_posix(): p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
    diagnosis = diagnose(store.root, job["id"])
    assert diagnosis["eligible"] == eligible
    assert diagnosis["receive_boundary"]["status"] == ("finish_conflict" if eligible else "compatible")
    assert {p.relative_to(store.root).as_posix(): p.read_bytes() for p in store.root.rglob('*') if p.is_file()} == before


@pytest.mark.parametrize("case", ["missing_graph", "missing_staging", "bad_usage", "missing_native", "native_mismatch", "feed_error", "schema"])
def test_unsupported_evidence_is_not_force_accepted(setup, monkeypatch, case):
    from pdfmd.recovery import diagnose
    from hashlib import sha256
    store, job, key, reply, raw = historical(setup, monkeypatch, "chat_completions")
    if case == "missing_graph":
        (store.root / "graph.sqlite").rename(store.root / "preserved-graph.sqlite")
    elif case == "schema":
        import sqlite3
        with sqlite3.connect(store.root / "graph.sqlite") as db:
            db.execute("ALTER TABLE writes RENAME TO old_writes")
    elif case == "missing_staging":
        with store.transaction() as db:
            db.execute("DELETE FROM records WHERE kind='blob' AND id=?", (f"accepted:{key}",))
    elif case == "bad_usage":
        request = store.get("request", key)
        attempt = store.get("attempt", request["attempts"][0])
        store.put("attempt", attempt["id"], job["id"], {**attempt, "usage": {"wrong": 1}})
    elif case == "missing_native":
        blob = store.get("blob", reply["native_ref"])
        (store.root / "objects" / blob["sha256"]).rename(store.root / "saved-native-original")
    elif case == "native_mismatch":
        value = json.loads(store.bytes(reply["native_ref"], job["id"]))
        value["id"] = "different-native"
        replace_blob(store, job["id"], reply["native_ref"], encode(value))
    elif case == "feed_error":
        request = store.get("request", key)
        attempt = request["attempts"][0]
        changed = raw[:-len(b"data: {")] + b"data: {}\n\n"
        replace_blob(store, job["id"], f"stream:{attempt}:0", changed)
        replace_blob(store, job["id"], f"raw-stream:{attempt}", changed)
        observed = store.get("stream_receive", attempt)
        observed["cursor"].update(bytes=len(changed), sha256=sha256(changed).hexdigest())
        observed["transport"]["received_body_bytes"] = len(changed)
        store.put("stream_receive", attempt, job["id"], observed)
        stage = store.get("blob", f"accepted:{key}")
        stage["meta"]["transport"]["received_body_bytes"] = len(changed)
        store.put("blob", stage["ref"], job["id"], stage)
        attempt_record = store.get("attempt", attempt)
        attempt_record["transport"]["received_body_bytes"] = len(changed)
        store.put("attempt", attempt, job["id"], attempt_record)
    before = preserved(store, job["id"])
    result = diagnose(store.root, job["id"])
    assert not result["eligible"]
    assert result["status"] == {"missing_graph": "missing_graph", "missing_staging": "missing_staging", "schema": "unsupported_schema"}.get(case, "unsupported" if case == "feed_error" else "evidence_unconfirmed")
    assert "corrupt" not in json.dumps(result).lower()
    if case == "feed_error":
        assert result["receive_boundary"]["status"] == "feed_error"
        assert result["reconstruction"]["status"] == "unknown"
    if case == "bad_usage":
        assert result["storage"]["status"] == "verified"
        assert result["receive_boundary"]["status"] == "finish_conflict"
    assert preserved(store, job["id"]) == before


def replace_blob(store, job, ref, raw):
    """Synthetic contradictory history, constructed before the diagnostic snapshot."""
    record = store.get("blob", ref)
    changed = store.blob(job, record["kind"], raw, record["meta"])
    store.put("blob", ref, job, {**changed, "ref": ref})


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("completed", [0, 1, 2])
def test_known_effects_are_paired_without_reexecution(setup, monkeypatch, protocol, completed):
    from pdfmd.recovery import diagnose, resolve
    from pdfmd.tools import Dispatcher
    calls = [tool("read_document", {}, "read"), tool("report", {"state": "partial", "message": "Retained"}, "report")]
    store, job, key, reply, _ = historical(setup, monkeypatch, protocol, calls=calls)
    dispatcher = Dispatcher(store)
    originals = []
    for i in range(completed):
        call = reply["calls"][i]
        originals.append(dispatcher.execute(job["id"], f"{key}:{i}", call["name"], call["arguments"]))
    monkeypatch.setattr(Dispatcher, "execute", forbidden)
    result = diagnose(store.root, job["id"])
    assert [o["certainty"] for o in result["effects"]["operations"]] == ["completed"] * completed + ["not_started"] * (2-completed)
    resolve(store, job["id"], key, result["basis"])
    for i, old in enumerate(originals):
        assert dispatcher.envelope(job["id"], f"{key}:{i}", store.get("operation", f"{key}:{i}")) == old


@pytest.mark.parametrize("stage", ["staged", "skipping", "unknown", "done_only", "nominal_done", "failed_process"])
def test_tool_effect_certainty_uses_more_than_status_or_blob(setup, monkeypatch, stage):
    from pdfmd.recovery import diagnose, resolve
    from pdfmd.tools import Dispatcher
    store, job, key, reply, _ = historical(setup, monkeypatch, "responses", calls=
        [tool("run_script", {"code": "print('synthetic candidate only')"}, "process")] if stage == "failed_process" else None)
    call, op = reply["calls"][0], f"{key}:0"
    dispatcher = Dispatcher(store)
    args_hash, candidate = dispatcher.capture(job["id"], op, call["name"], call["arguments"])
    record = {"id": op, "tool": call["name"], "args_hash": args_hash, "candidate_ref": candidate["ref"],
              "status": "skipping" if stage == "skipping" else "done" if stage in {"done_only", "nominal_done", "failed_process"} else "started"}
    store.put("operation", op, job["id"], record)
    if stage == "staged":
        store.blob(job["id"], "tool_result", {"head": None, "message": "No document version is saved yet."},
                   {"operation": op, "args_hash": args_hash, "ok": True}, key=f"result:{op}")
    elif stage == "nominal_done":
        store.blob(job["id"], "tool_result", {"unconfirmed_effect": True},
                   {"operation": op, "args_hash": args_hash, "ok": True}, key=f"result:{op}")
    elif stage == "failed_process":
        store.blob(job["id"], "tool_result", {"error": "A process failed without retained completion/log evidence."},
                   {"operation": op, "args_hash": args_hash, "ok": False}, key=f"result:{op}")
    result = diagnose(store.root, job["id"])
    assert result["eligible"] == (stage in {"staged", "skipping"})
    if result["eligible"]:
        resolve(store, job["id"], key, result["basis"])
        saved = store.json(f"result:{op}", job["id"])
        if stage == "skipping":
            assert saved["reason"] == "superseded_by_user_amendment"
        assert store.get("operation", op)["status"] == "done"
    else:
        assert result["effects"]["status"] == "unknown"
        assert store.get("operation", op) == record


@pytest.mark.parametrize("boundary", ["prepared", "committed", "projected"])
def test_cross_store_interruptions_reuse_one_choice_and_preserve_new_facts(setup, monkeypatch, boundary):
    import pdfmd.recovery as recovery
    from pdfmd.storage import Conflict
    store, job, key, _, _ = historical(setup, monkeypatch, "chat_completions")
    diagnosis = recovery.diagnose(store.root, job["id"])
    def interrupt(*_):
        raise RuntimeError("controlled recovery interruption")
    with monkeypatch.context() as patch:
        patch.setattr(recovery, boundary, interrupt)
        with pytest.raises(RuntimeError, match="controlled"):
            recovery.resolve(store, job["id"], key, diagnosis["basis"])
    if boundary == "prepared":
        assert not store.maybe("conflict_resolution", key)
        assert not store.maybe("blob", f"result:{key}:0")
        assert not store.maybe("blob", f"conflict-resolution:{key}")
        assert not store.records("operation", job["id"])
        assert recovery.diagnose(store.root, job["id"])["preparation"]["status"] == "uncommitted_candidates"
    current = store.update_job(job["id"], amendments=["New instruction"],
                               route={**job["route"], "context_tokens": 50000}, cancel_requested=True)
    if boundary == "prepared":
        with pytest.raises(Conflict, match="Stale"):
            recovery.resolve(store, job["id"], key, diagnosis["basis"])
        diagnosis = recovery.diagnose(store.root, job["id"])
    result = recovery.resolve(Store(store.root), job["id"], key, diagnosis["basis"])
    assert result["projection"] == "ready"
    assert store.get("job", job["id"]) == current
    assert len(store.records("conflict_resolution", job["id"])) == 1
    assert recovery.resolve(store, job["id"], key, "stale-click") == result


def test_atomic_catalog_publication_rolls_back_every_alias_and_operation(setup, monkeypatch):
    from pdfmd.recovery import diagnose, resolve
    store, job, key, _, _ = historical(setup, monkeypatch, "responses")
    diagnosis = diagnose(store.root, job["id"])
    put = store.put_tx
    with monkeypatch.context() as patch:
        def fail(db, kind, identity, owner, value):
            if kind == "conflict_resolution":
                raise RuntimeError("catalog interruption")
            return put(db, kind, identity, owner, value)
        patch.setattr(store, "put_tx", fail)
        with pytest.raises(RuntimeError, match="catalog interruption"):
            resolve(store, job["id"], key, diagnosis["basis"])
    assert not store.records("operation", job["id"])
    assert not store.maybe("blob", f"result:{key}:0")
    assert not store.maybe("blob", f"candidate:{key}:0")
    assert resolve(store, job["id"], key, diagnosis["basis"])["projection"] == "ready"


@pytest.mark.parametrize("boundary", ["prepared", "committed", "projected"])
def test_own_child_abrupt_exit_preserves_authority_boundaries(setup, monkeypatch, boundary):
    import subprocess
    import sys
    from pdfmd.recovery import diagnose, resolve
    store, job, key, _, _ = historical(setup, monkeypatch, "responses")
    result = diagnose(store.root, job["id"])
    code = ("import os,sys; import pdfmd.recovery as r; from pdfmd.storage import Store; "
            "setattr(r,sys.argv[5],lambda *_:os._exit(73)); "
            "r.resolve(Store(sys.argv[1]),sys.argv[2],sys.argv[3],sys.argv[4])")
    child = subprocess.run([sys.executable, "-c", code, str(store.root), job["id"], key, result["basis"], boundary],
                           capture_output=True, timeout=40)
    assert child.returncode == 73, child.stderr
    if boundary == "prepared":
        assert not store.maybe("blob", f"result:{key}:0")
        assert not store.maybe("conflict_resolution", key)
    else:
        assert store.maybe("conflict_resolution", key)
        assert diagnose(store.root, job["id"])["projection"] == ("pending" if boundary == "committed" else "ready")
    assert resolve(store, job["id"], key, result["basis"])["projection"] == "ready"


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_document_commit_report_replan_and_source_led_continue_export(delivery, tmp_path, monkeypatch, protocol):
    from pdfmd.documents import Documents
    from pdfmd.recovery import diagnose, resolve
    from pdfmd.tools import Dispatcher
    store, job, version, image, source = delivery
    content = Documents(store).version(job["id"], version)["content"]
    calls = [tool("edit_document", {"base_version": version, "expected_head": version,
             "replace_blocks": content["blocks"], "claim": "complete"}, "save"),
             tool("report", {"state": "complete", "version_id": version, "message": "Historical complete claim"}, "claim")]
    store, job, key, reply, _ = historical((store, job), monkeypatch, protocol, calls=calls)
    runtime = Runtime(store, Nexus(store, forbidden))
    config = {"configurable": {"thread_id": job["id"]}}
    state = dict(runtime.graph.get_state(config).values)
    # Atomic document commit before Dispatcher result projection.
    op, call = key + ":0", reply["calls"][0]
    args_hash, candidate = runtime.dispatcher.capture(job["id"], op, call["name"], call["arguments"])
    result = runtime.dispatcher.documents.edit(job["id"], op, json.loads(call["arguments"]), args_hash, candidate["ref"])
    assert not store.maybe("blob", f"result:{op}")
    call = reply["calls"][1]
    runtime.dispatcher.execute(job["id"], key + ":1", call["name"], call["arguments"])
    runtime.graph.update_state(config, {"report": {"intent": json.loads(call["arguments"]),
        "instruction_basis": store.get("request", key)["instruction_basis"]}, "next": "tools"}, as_node="model")
    runtime.close()
    before = preserved(store, job["id"])
    seed = store.get("operation", "seed")
    job_before = store.get("job", job["id"])
    diagnosis = diagnose(store.root, job["id"])
    assert diagnosis["eligible"], diagnosis
    resolve(store, job["id"], key, diagnosis["basis"])
    assert preserved(store, job["id"]) == before
    assert store.get("job", job["id"]) == job_before
    assert len(store.records("version", job["id"])) == 2
    assert store.get("operation", "seed") == seed
    saved = result["version_id"]
    check_delivery(store, job, saved, image, source, tmp_path / "before-continue.zip")
    sends = []
    def answer(request):
        payload = json.loads(request.content)
        sends.append(payload)
        assert "Historical conflict resolution:" in json.dumps(payload)
        assert key in json.dumps(payload) and "Historical complete claim" in json.dumps(payload)
        value = native(protocol, tool("report", {"state": "complete", "version_id": saved,
            "message": "Independent scripted Continue; complete saved source."}, "new-report"))
        return httpx.Response(200, stream=Body(stream_frames(protocol, value)))
    from pdfmd.server import Engine
    engine = Engine(store.root, transport=httpx.MockTransport(answer))
    try:
        engine.start(job["id"], "local-fixture-only")
        engine.futures[job["id"]].result(timeout=40)
    finally:
        engine.close()
    assert len(sends) == 1
    assert store.get("job", job["id"])["status"] == "completed"
    assert store.get("request", key) == before["request"][0]
    assert store.get("attempt", before["attempt"][0]["id"]) == before["attempt"][0]
    assert store.get("job", job["id"])["attempts"] == job_before["attempts"] + 1
    assert len(store.records("version", job["id"])) == 2
    check_delivery(Store(store.root), job, saved, image, source, tmp_path / "reopened-delivery.zip")
    # A duplicate after later graph progress cannot rewind or duplicate history.
    after = (store.root / "graph.sqlite").read_bytes()
    assert resolve(store, job["id"], key, "old click")["projection"] == "ready"
    runtime = Runtime(store, Nexus(store, forbidden))
    try:
        state = runtime.graph.get_state(config).values
        assert state["history"].count(key) == 1 and state["seq"] == 2
        assert state["resolutions"][key] == f"conflict-resolution:{key}"
        payload, meta = runtime.context.compact_request(store.get("job", job["id"]), state)
        assert f"conflict-resolution:{key}" in json.dumps(payload)
        from pdfmd.context import estimate
        route = Route.model_validate(store.get("job", job["id"])["route"])
        assert meta["capacity"]["input_estimate"] == estimate(payload, route)["input_estimate"]
        for old in state["history"]:
            assert old in json.dumps(payload) or old not in meta["covered"]
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_resolution_survives_actual_compaction_archive_and_feedback_clear(setup, monkeypatch, protocol):
    from pdfmd.recovery import diagnose, resolve
    from test_context_progress import read_batch
    from test_context_plans import varied_text
    from test_response_repairs import handoff
    from pdfmd.context import estimate
    store, job, key, reply, _ = historical(setup, monkeypatch, protocol)
    # A real saved read result provides a meaningful body for subsequent compaction.
    runtime = Runtime(store, Nexus(store, forbidden))
    call = reply["calls"][0]
    runtime.dispatcher.execute(job["id"], key + ":0", call["name"], call["arguments"])
    runtime.close()
    diagnosis = diagnose(store.root, job["id"])
    resolve(store, job["id"], key, diagnosis["basis"])
    seen = []
    def compact_answer(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, stream=Body(stream_frames(protocol, native(protocol,
            text=json.dumps(handoff(job, current_state="Saved work and conflict resolution retained.", references=[f"conflict-resolution:{key}"]))))))
    runtime = Runtime(store, Nexus(store, lambda _: "scripted", httpx.MockTransport(compact_answer)))
    config = {"configurable": {"thread_id": job["id"]}}
    try:
        state = dict(runtime.graph.get_state(config).values)
        # Add ordinary completed evidence without altering the resolved batch.
        read_batch(store, store.get("job", job["id"]), "later", [varied_text(12000, 19)])
        runtime.graph.update_state(config, {"history": [key, "later"], "continuation_feedback": None}, as_node="tools")
        state = dict(runtime.graph.get_state(config).values)
        current = store.get("job", job["id"])
        payload, meta = runtime.context.compact_request(current, state)
        assert key in meta["covered"]
        new_key = f"{job['id']}:{state['seq']}:{state['revision']}"
        runtime.nexus.freeze(job["id"], new_key, payload, "compaction", meta)
        state.update(pending=new_key)
        changes = runtime.compact(state)
        runtime.graph.update_state(config, changes, as_node="compact")
        archive = store.json(changes["handoff"], job["id"])
        assert archive["resolution_refs"][0] == f"conflict-resolution:{key}"
        assert archive["originals"][0] == f"accepted:{key}"
        after = runtime.graph.get_state(config).values
        normal, capacity = runtime.context.normal(current, after)
        assert f"conflict-resolution:{key}" in json.dumps(normal)
        assert capacity["input_estimate"] == estimate(normal, Route.model_validate(current["route"]))["input_estimate"]
        assert after["resolutions"][key] == f"conflict-resolution:{key}"
    finally:
        runtime.close()
    assert len(seen) == 1
    assert resolve(Store(store.root), job["id"], key, "later click")["projection"] == "ready"


def test_live_wal_is_observed_without_source_database_side_effects(setup, monkeypatch):
    from pdfmd.recovery import diagnose
    store, job, key, _, _ = historical(setup, monkeypatch, "responses")
    with store.connection_scope():
        store.update_job(job["id"], amendments=["Committed in a live WAL"])
        assert (store.root / "catalog.sqlite-wal").stat().st_size > 0
        before = {p.relative_to(store.root).as_posix(): p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
        result = diagnose(store.root, job["id"])
        assert result["eligible"], result
        assert before == {p.relative_to(store.root).as_posix(): p.read_bytes() for p in store.root.rglob('*') if p.is_file()}


def test_snapshot_timestamp_housekeeping_does_not_invalidate_identical_bytes(setup, monkeypatch):
    import os
    import pdfmd.recovery as recovery
    store, job, _, _, _ = historical(setup, monkeypatch, "chat_completions")
    original = recovery.inspect_current
    def timestamp_only(*args):
        value = original(*args)
        path = store.root / "catalog.sqlite"
        stat = path.stat()
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1000000000))
        return value
    monkeypatch.setattr(recovery, "inspect_current", timestamp_only)
    assert recovery.diagnose(store.root, job["id"])["eligible"]


def test_committed_duplicate_is_idempotent_during_background_polling(setup, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from fastapi.testclient import TestClient
    from pdfmd.server import create_app
    from pdfmd.recovery import diagnose, resolve
    store, job, key, _, _ = historical(setup, monkeypatch, "chat_completions")
    result = diagnose(store.root, job["id"])
    resolve(store, job["id"], key, result["basis"])
    app = create_app(store.root, "local-only")
    headers = {"Authorization": "Bearer local-only"}
    stop, started = Event(), Event()
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=1) as pool:
        def poll():
            started.set()
            while not stop.is_set():
                assert client.get(f"/jobs/{job['id']}", headers=headers).status_code == 200
        future = pool.submit(poll)
        assert started.wait(5)
        try:
            for _ in range(12):
                response = client.post(f"/jobs/{job['id']}/accepted-evidence-resolution", headers=headers,
                    json={"request": key, "basis": "old-click"})
                assert response.status_code == 200, response.text
                assert response.json()["projection"] == "ready"
        finally:
            stop.set()
            future.result(timeout=20)
    assert len(store.records("conflict_resolution", job["id"])) == 1


def test_new_manual_head_after_catalog_commit_is_preserved(delivery, monkeypatch):
    import pdfmd.recovery as recovery
    from pdfmd.tools import Dispatcher
    from pdfmd.documents import Documents
    store, job, version, _, _ = delivery
    store, job, key, _, _ = historical((store, job), monkeypatch, "responses")
    diagnosis = recovery.diagnose(store.root, job["id"])
    with monkeypatch.context() as patch:
        patch.setattr(recovery, "committed", lambda *_: (_ for _ in ()).throw(RuntimeError("commit before manual edit")))
        with pytest.raises(RuntimeError):
            recovery.resolve(store, job["id"], key, diagnosis["basis"])
    edited = Dispatcher(store).execute(job["id"], "manual-new-head", "edit_document", json.dumps({
        "base_version": version, "expected_head": version, "title": "New manual head after recovery commit"}))
    assert edited["ok"]
    current = store.update_job(job["id"], amendments=["Latest amendment"])
    recovery.resolve(store, job["id"], key, "old basis")
    assert store.get("job", job["id"]) == current
    assert Documents(store).version(job["id"], current["head"])["content"]["title"] == "New manual head after recovery commit"


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_real_runtime_failed_tool_checkpoint_can_be_resolved(delivery, monkeypatch, protocol):
    from pdfmd.documents import Documents
    from pdfmd.recovery import diagnose, resolve
    store, job, version, _, _ = delivery
    path = "responses" if protocol == "responses" else "chat/completions"
    store.update_job(job["id"], route={**job["route"], "protocol": protocol,
        "endpoint": "https://synthetic.invalid/v1/" + path, "wait_policy": WAIT})
    content = Documents(store).version(job["id"], version)["content"]
    value = native(protocol, tool("edit_document", {"base_version": version, "expected_head": version,
        "replace_blocks": content["blocks"], "claim": "complete"}, "save"),
        tool("report", {"state": "partial", "message": "Old unexecuted report"}, "report"))
    raw = b"".join(stream_frames(protocol, value)) + b"data: {"
    runtime = Runtime(store, Nexus(store, lambda _: "scripted", httpx.MockTransport(lambda _: httpx.Response(200, stream=Body([raw])))))
    execute = runtime.dispatcher.execute
    def interrupted(*args):
        execute(*args)
        raise RuntimeError("old tool commit before failed graph checkpoint")
    with monkeypatch.context() as patch:
        patch.setattr(runtime.dispatcher, "execute", interrupted)
        patch.setattr(StreamDecoder, "finish_received", lambda self: deepcopy(self.value))
        with pytest.raises(RuntimeError, match="old tool commit"):
            runtime.run(job["id"])
    original = preserved(store, job["id"])
    request = original["request"][0]
    snapshot = runtime.graph.get_state({"configurable": {"thread_id": job["id"]}})
    assert snapshot.next == ("tools",) and snapshot.tasks[0].error
    runtime.close()
    diagnosis = diagnose(store.root, job["id"])
    assert diagnosis["eligible"], diagnosis
    resolve(store, job["id"], request["id"], diagnosis["basis"])
    assert preserved(store, job["id"]) == original
    runtime = Runtime(store, Nexus(store, forbidden))
    try:
        snapshot = runtime.graph.get_state({"configurable": {"thread_id": job["id"]}})
        assert snapshot.next == ("coordinate",) and snapshot.values["seq"] == 1
    finally:
        runtime.close()


def test_unexpected_compaction_calls_never_execute(setup, monkeypatch):
    from pdfmd.recovery import diagnose, resolve
    from pdfmd.tools import Dispatcher
    store, job, key, _, _ = historical(setup, monkeypatch, "responses", kind="compaction",
        calls=[tool("run_script", {"code": "raise RuntimeError('must never run')"}, "unexpected")])
    monkeypatch.setattr(Dispatcher, "execute", forbidden)
    result = diagnose(store.root, job["id"])
    assert result["eligible"] and result["transition"] == "C2"
    resolve(store, job["id"], key, result["basis"])
    assert store.json(f"result:{key}:0", job["id"])["execution"] == "not_started"


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("large_part", ["result", "arguments", "context_arguments"])
def test_resolved_history_keeps_agent_release_and_capacity_projection(setup, monkeypatch, protocol, large_part):
    from pdfmd.recovery import diagnose, resolve
    from test_context_plans import varied_text
    from pdfmd.tools import Dispatcher
    store, job = setup
    source = store.blob(job["id"], "evidence", {"text": varied_text(50000, 89)})
    args = {"ref": source["ref"]} if large_part == "result" else {"unexpected_large_argument": varied_text(50000, 7)}
    call_name = "read_evidence" if large_part == "result" else "read_document"
    if large_part == "context_arguments":
        args, call_name = {"notes": varied_text(50000, 7)}, "context_update"
    store, job, key, reply, _ = historical((store, job), monkeypatch, protocol, calls=[tool(call_name, args, "read")])
    call = reply["calls"][0]
    if large_part == "context_arguments":
        capture_runtime = Runtime(store, Nexus(store, forbidden))
        source_state = capture_runtime.graph.get_state({"configurable": {"thread_id": job["id"]}}).values
        working = capture_runtime.context_revisions.start(job["id"], source_state)
        capture_runtime.dispatcher.context_preflight = lambda intent, op, candidate: capture_runtime.context_revisions.capture(job, source_state, working, intent, op, candidate)
        assert capture_runtime.dispatcher.execute(job["id"], key + ":0", call["name"], call["arguments"])["ok"]
        capture_runtime.close()
    else:
        Dispatcher(store).execute(job["id"], key + ":0", call["name"], call["arguments"])
    store.update_job(job["id"], route={**job["route"], "context_tokens": 20000})
    diagnosis = diagnose(store.root, job["id"])
    assert diagnosis["eligible"], diagnosis
    resolve(store, job["id"], key, diagnosis["basis"])
    runtime = Runtime(store, Nexus(store, forbidden))
    try:
        state = runtime.graph.get_state({"configurable": {"thread_id": job["id"]}}).values
        current = store.get("job", job["id"])
        assert runtime.context.required(current, state)["fits"]
        payload, capacity = runtime.context.normal(current, state)
        assert capacity["fits"]
        assert "capacity deferred" in json.dumps(payload)
        assert f"conflict-resolution:{key}" in json.dumps(payload)
        ref = f"result:{key}:0" if large_part == "result" else f"candidate:{key}:0"
        full = store.bytes(ref, job["id"])
        released, _ = runtime.context.normal(current, {**state, "released": [ref]})
        assert "agent released" in json.dumps(released)
        assert store.bytes(ref, job["id"]) == full
        from pdfmd.history import batch_reply
        assert batch_reply(store, job["id"], key)["reply"] == reply
    finally:
        runtime.close()


def test_readonly_authenticated_api_busy_missing_and_stale_views(setup, monkeypatch):
    from fastapi.testclient import TestClient
    from filelock import FileLock
    from pdfmd.server import create_app
    import pdfmd.recovery as recovery
    store, job, key, _, _ = historical(setup, monkeypatch, "responses")
    app = create_app(store.root, "local-only", transport=httpx.MockTransport(forbidden))
    headers = {"Authorization": "Bearer local-only"}
    with TestClient(app) as client:
        url = f"/jobs/{job['id']}/accepted-evidence-diagnosis"
        assert client.get(url).status_code == 401
        assert client.post(f"/jobs/{job['id']}/accepted-evidence-resolution", headers=headers, json={}).status_code == 422
        before = {p.relative_to(store.root).as_posix(): p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
        result = client.get(url, headers=headers).json()
        assert result["eligible"]
        assert before == {p.relative_to(store.root).as_posix(): p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
        with FileLock(str(store.root / f"task-{job['id']}.lock")):
            assert client.get(url, headers=headers).json()["status"] == "busy"
        original = recovery.inspect_current
        with monkeypatch.context() as patch:
            def changed(*args):
                value = original(*args)
                store.update_job(job["id"], amendments=["race during snapshot"])
                return value
            patch.setattr(recovery, "inspect_current", changed)
            assert client.get(url, headers=headers).json()["status"] == "stale_view"
        stale = client.post(f"/jobs/{job['id']}/accepted-evidence-resolution", headers=headers,
                            json={"request": key, "basis": result["basis"]})
        assert stale.status_code == 409
        assert not store.records("conflict_resolution", job["id"])


@pytest.mark.parametrize("status", ["applied", "superseded", "needs_agent_revision"])
@pytest.mark.parametrize("foreign_commit", [False, True])
def test_committed_context_settlement_recovers_exact_basis(setup, monkeypatch, status, foreign_commit):
    from pdfmd.recovery import diagnose, resolve
    from pdfmd.context_outcomes import policy_ref
    store, job, key, _, _ = historical(setup, monkeypatch, "chat_completions")
    runtime = Runtime(store, Nexus(store, forbidden))
    config = {"configurable": {"thread_id": job["id"]}}
    source = runtime.graph.get_state(config).values
    proposal = store.blob(job["id"], "context_proposal", {"context_proposal": {
        "batch": "previous", "operations": [], "policy": {"notes": "Committed notes", "pinned": [], "released": [], "pin_views": {}},
        "instruction_basis": store.get("request", key)["instruction_basis"]}})["ref"]
    runtime.graph.update_state(config, {"context_waiting": proposal, "next": "model"}, as_node="prepare")
    source = runtime.graph.get_state(config).values
    policy = {"notes": "Committed notes", "pinned": [], "released": [], "pin_views": {}}
    expected = runtime.context_updates.finish(store.get("job", job["id"]), source, key,
        {"status": status, "proposal_ref": proposal, "receipt_ref": f"context-settlement:{key}", "reason": "original_disposition"},
        policy if status == "applied" else None)
    settlement = store.bytes(f"context-settlement:{key}", job["id"])
    disposition = store.get("context_disposition", proposal)
    runtime.close()
    if foreign_commit:
        with store.transaction() as db:
            db.execute("UPDATE records SET job='foreign-task' WHERE kind='context_commit' AND id=?", (f"context-settlement:{key}",))
    diagnosis = diagnose(store.root, job["id"])
    if foreign_commit:
        assert not diagnosis["eligible"], diagnosis
        assert diagnosis["provenance"]["status"] != "verified"
        return
    assert diagnosis["eligible"], diagnosis
    resolve(store, job["id"], key, diagnosis["basis"])
    runtime = Runtime(store, Nexus(store, forbidden))
    try:
        after = runtime.graph.get_state(config).values
        assert all(after[k] == v for k, v in expected.items())
        assert store.bytes(f"context-settlement:{key}", job["id"]) == settlement
        assert store.get("context_disposition", proposal) == disposition
    finally:
        runtime.close()


@pytest.mark.parametrize("related", [False, True])
def test_pending_context_ancestor_is_distinct_from_unrelated_pending(setup, monkeypatch, related):
    from pdfmd.recovery import diagnose, resolve
    from pdfmd.context_outcomes import policy_ref
    store, job, key, reply, _ = historical(setup, monkeypatch, "responses",
        calls=[tool("context_update", {"base": {"kind": "pending" if related else "active"}, "notes": "New intent"}, "ctx")])
    runtime = Runtime(store, Nexus(store, forbidden))
    config = {"configurable": {"thread_id": job["id"]}}
    proposal = store.blob(job["id"], "context_proposal", {"context_proposal": {"batch": "prior", "operations": [],
        "policy": {"notes": "Older pending", "pinned": [], "released": [], "pin_views": {}},
        "instruction_basis": store.get("request", key)["instruction_basis"]}})["ref"]
    store.put("context_disposition", proposal, job["id"], {"proposal_ref": proposal, "status": "eligible_pending"})
    runtime.graph.update_state(config, {"context_waiting": proposal, "next": "model"}, as_node="prepare")
    state = runtime.graph.get_state(config).values
    working = runtime.context_revisions.start(job["id"], state)
    runtime.dispatcher.context_preflight = lambda intent, op, candidate: runtime.context_revisions.capture(job, state, working, intent, op, candidate)
    call = reply["calls"][0]
    assert runtime.dispatcher.execute(job["id"], key + ":0", call["name"], call["arguments"])["ok"]
    runtime.close()
    diagnosis = diagnose(store.root, job["id"])
    assert diagnosis["eligible"], diagnosis
    resolve(store, job["id"], key, diagnosis["basis"])
    runtime = Runtime(store, Nexus(store, forbidden))
    try:
        state = runtime.graph.get_state(config).values
        assert state.get("context_waiting") == (None if related else proposal)
        assert state["notes"] == ""
        assert store.get("context_disposition", proposal)["status"] == ("superseded" if related else "eligible_pending")
    finally:
        runtime.close()


def test_projection_divergence_cannot_overwrite_graph(setup, monkeypatch):
    import pdfmd.recovery as recovery
    from pdfmd.storage import Conflict
    store, job, key, _, _ = historical(setup, monkeypatch, "responses")
    diagnosis = recovery.diagnose(store.root, job["id"])
    with monkeypatch.context() as patch:
        patch.setattr(recovery, "committed", lambda *_: (_ for _ in ()).throw(RuntimeError("before projection")))
        with pytest.raises(RuntimeError):
            recovery.resolve(store, job["id"], key, diagnosis["basis"])
    runtime = Runtime(store, Nexus(store, forbidden))
    config = {"configurable": {"thread_id": job["id"]}}
    runtime.graph.update_state(config, {"notes": "Unexpected divergent state"}, as_node="prepare")
    graph_before = runtime.graph.get_state(config)
    runtime.close()
    with pytest.raises(Conflict, match="marker|diverged"):
        recovery.resolve(store, job["id"], key, "old basis")
    runtime = Runtime(store, Nexus(store, forbidden))
    try:
        assert runtime.graph.get_state(config).values == graph_before.values
    finally:
        runtime.close()


@pytest.mark.parametrize("tamper", ["authority_owner", "receipt_owner", "receipt_kind", "authority_link"])
def test_resolution_authority_and_receipt_membership_are_required(setup, monkeypatch, tamper):
    from pdfmd.recovery import diagnose, resolve
    from pdfmd.history import batch_reply
    from pdfmd.storage import Conflict
    store, job, key, _, _ = historical(setup, monkeypatch, "responses")
    diagnosis = diagnose(store.root, job["id"])
    resolve(store, job["id"], key, diagnosis["basis"])
    ref = f"conflict-resolution:{key}"
    if tamper == "authority_owner":
        with store.transaction() as db:
            db.execute("UPDATE records SET job='foreign-task' WHERE kind='conflict_resolution' AND id=?", (key,))
    elif tamper == "authority_link":
        authority = store.get("conflict_resolution", key)
        store.put("conflict_resolution", key, job["id"], {**authority, "basis": "contradictory-basis"})
    else:
        blob = store.get("blob", ref)
        store.put("blob", ref, job["id"], {**blob, **({"job": "foreign-task"} if tamper == "receipt_owner" else {"kind": "evidence"})})
    before = (store.root / "graph.sqlite").read_bytes()
    with pytest.raises((ValueError, Conflict)):
        resolve(store, job["id"], key, "old-click")
    with pytest.raises((ValueError, Conflict)):
        batch_reply(store, job["id"], key)
    assert (store.root / "graph.sqlite").read_bytes() == before


@pytest.mark.parametrize("case", ["missing_context", "wrong_graph_phase"])
def test_unconfirmed_context_or_graph_relationship_cannot_offer_recovery(setup, monkeypatch, case):
    from pdfmd.recovery import diagnose
    store, job, _, _, _ = historical(setup, monkeypatch, "responses")
    runtime = Runtime(store, Nexus(store, forbidden))
    config = {"configurable": {"thread_id": job["id"]}}
    if case == "missing_context":
        runtime.graph.update_state(config, {"context_waiting": "missing-pending-proposal", "next": "model"}, as_node="prepare")
    else:
        runtime.graph.update_state(config, {"next": "compact"}, as_node="prepare")
    runtime.close()
    result = diagnose(store.root, job["id"])
    assert not result["eligible"], result


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("complete", [False, True])
def test_uncommitted_context_requires_reselection_and_explicit_reuse(setup, monkeypatch, protocol, complete):
    from pdfmd.recovery import diagnose, resolve
    from pdfmd.context_outcomes import policy_ref
    calls = [tool("context_update", {"notes": "Retained candidate notes"}, "notes"),
             tool("context_update", {"notes": "Final uncommitted notes"}, "final")]
    store, job, key, reply, _ = historical(setup, monkeypatch, protocol, calls=calls)
    runtime = Runtime(store, Nexus(store, forbidden))
    config = {"configurable": {"thread_id": job["id"]}}
    state = dict(runtime.graph.get_state(config).values)
    working = runtime.context_revisions.start(job["id"], state)
    runtime.dispatcher.context_preflight = lambda intent, op, candidate: runtime.context_revisions.capture(job, state, working, intent, op, candidate)
    for index in range(2 if complete else 1):
        call = reply["calls"][index]
        result = runtime.dispatcher.execute(job["id"], f"{key}:{index}", call["name"], call["arguments"])
        assert result["ok"]
        working.update(policy=result["data"]["context_saved"]["policy"])
    if complete:
        proposal = runtime.context_revisions.complete(job["id"], state, store.get("request", key), [f"{key}:0", f"{key}:1"], working, [])
        runtime.graph.update_state(config, {"context_waiting": proposal, "next": "tools"}, as_node="model")
        proposal_bytes = store.bytes(proposal, job["id"])
    runtime.close()
    diagnosis = diagnose(store.root, job["id"])
    assert diagnosis["eligible"], diagnosis
    resolve(store, job["id"], key, diagnosis["basis"])
    runtime = Runtime(store, Nexus(store, forbidden))
    try:
        restored = runtime.graph.get_state(config).values
        assert restored["notes"] == "" and restored.get("context_waiting") is None
        feedback = runtime.context.feedback(job["id"], restored)
        assert feedback["status"] == "needs_agent_revision" and feedback["reason"] == "historical_conflict_replan"
        assert runtime.context.feedback_operations(job["id"], restored) == {f"{key}:0", f"{key}:1"}
        reuse_ref = f"context-proposal:{key}" if complete else f"recovery-context:{key}"
        reused = runtime.context_revisions.capture(store.get("job", job["id"]), restored,
            runtime.context_revisions.start(job["id"], restored),
            {"base": {"kind": "active", "ref": policy_ref(restored)},
             "reuse": [{"ref": reuse_ref, "operations": [f"{key}:0"], "fields": ["notes"]}]}, "explicit-reuse", "not-yet-published")
        assert reused["context_saved"]["policy"]["notes"] == "Retained candidate notes"
        if complete:
            assert store.bytes(proposal, job["id"]) == proposal_bytes
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("applied", [False, True])
def test_compaction_candidate_and_committed_handoff_have_distinct_successors(setup, monkeypatch, protocol, applied):
    from pdfmd.recovery import diagnose, resolve
    from test_context_progress import read_batch
    from test_context_plans import varied_text
    from test_response_repairs import handoff
    store, initial = setup
    # Match protocol before generating ordinary history.
    from test_context_admission import protocol_job
    job = protocol_job(store, initial, protocol)
    read_batch(store, job, "older", [varied_text(4000, 3)])
    repair_ref = store.blob(job["id"], "response_repair", {"request": "older", "code": "historical",
        "message": "Preserve this unrelated repair episode.", "candidate_ref": None})["ref"]
    text = json.dumps(handoff(job, current_state="Retained saved work.", references=[]))
    store, job, key, _, _ = historical((store, job), monkeypatch, protocol, kind="compaction", calls=[], text=text,
                                      initial={"history": ["older"], "repairs": {"normal": {"count": 4, "basis": "unrelated", "feedback_ref": repair_ref}}})
    runtime = Runtime(store, Nexus(store, forbidden))
    config = {"configurable": {"thread_id": job["id"]}}
    state = dict(runtime.graph.get_state(config).values)
    meta = store.get("request", key)["meta"]
    if applied:
        expected = runtime.context.apply_handoff(job, state, text, meta, key)
    else:
        with monkeypatch.context() as patch:
            patch.setattr(store, "event_once", lambda *_: (_ for _ in ()).throw(RuntimeError("before handoff commit")))
            with pytest.raises(RuntimeError):
                runtime.context.apply_handoff(job, state, text, meta, key)
    archive = store.bytes(f"handoff:{key}", job["id"])
    runtime.close()
    diagnosis = diagnose(store.root, job["id"])
    assert diagnosis["eligible"], diagnosis
    assert diagnosis["transition"] == ("C1" if applied else "C2")
    resolve(store, job["id"], key, diagnosis["basis"])
    runtime = Runtime(store, Nexus(store, forbidden))
    try:
        after = runtime.graph.get_state(config).values
        assert after["seq"] == 0 and after["revision"] == 1
        assert after["history"] == ([] if applied else ["older"])
        assert after.get("handoff") == (f"handoff:{key}" if applied else None)
        assert after["repairs"] == state["repairs"]
        assert store.bytes(f"handoff:{key}", job["id"]) == archive
    finally:
        runtime.close()
