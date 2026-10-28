"""One received-prefix criterion for first acceptance and persisted recovery.

All traffic uses MockTransport and synthetic inputs. Reopen never obtains a
credential. The expected suffix policy is shared by every tested entry path.
"""
from copy import deepcopy
from hashlib import sha256

import httpx
import pytest

from pdfmd.nexus import Nexus, StopRun, make_payload
from pdfmd.schema import Route
from pdfmd.storage import Store, encode
from pdfmd.streaming import StreamDecoder, StreamError
from test_context_admission import protocol_job
from test_streaming_delivery import WAIT
from test_stream_progress import delta
from test_continuation import delivery, check_delivery


PROTOCOLS = ["chat_completions", "responses"]
SUFFIXES = [
    pytest.param(b"", True, id="empty"),
    pytest.param(b": heartbeat\n\n", True, id="comment-complete"),
    pytest.param(b": heartbeat", True, id="comment-unfinished"),
    pytest.param(": 心跳".encode(), True, id="comment-unicode"),
    pytest.param(b"\r\n: one\r: two\n\n", True, id="comments-crlf"),
    pytest.param(b"event: ignored\nid: x\nretry: 1\nextension: y\n", True, id="nondata-fields"),
    pytest.param(b"data: {}\n\n", False, id="data-complete"),
    pytest.param(b"data: {", False, id="data-unfinished"),
    pytest.param(b"data: {}\n", False, id="data-undispatched"),
    pytest.param(b"data:\n\n", False, id="data-empty"),
    pytest.param(b"data: [DONE]\n\n", False, id="second-terminal"),
    pytest.param(b": comment\ndata: {\n: tail", False, id="comment-cannot-hide-data"),
    pytest.param(b"event: unfinished", False, id="noncomment-unfinished"),
    pytest.param("字".encode(), False, id="utf8-noncomment"),
    pytest.param(b"\xe4", False, id="utf8-unfinished"),
    pytest.param(b": \xe4", False, id="comment-utf8-unfinished"),
    pytest.param(b": \xff", False, id="utf8-invalid"),
]


def forbidden(_):
    pytest.fail("Saved-result recovery must not obtain credentials or dispatch")


def event(value):
    return b"data: " + encode(value) + b"\n\n"


def terminal(protocol, text="Saved text 完整", usage=None):
    if protocol == "chat_completions":
        return event({"id": "r", "choices": [{"index": 0,
            "delta": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
            "usage": usage}) + b"data: [DONE]\n\n"
    return event({"type": "response.completed", "response": {"id": "r", "status": "completed",
        "output": [{"id": "m", "type": "message", "status": "completed", "role": "assistant",
                    "content": [{"type": "output_text", "text": text}]}], "usage": usage}})


class Body(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks, self.received, self.eof, self.closed = chunks, [], False, False

    async def __aiter__(self):
        for chunk in self.chunks:
            if isinstance(chunk, Exception):
                raise chunk
            self.received.append(chunk)
            yield chunk
        self.eof = True

    async def aclose(self):
        self.closed = True


def prepare(setup, protocol, chunks, *, kind="normal"):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    path = "chat/completions" if protocol == "chat_completions" else "responses"
    route = Route.model_validate({**job["route"], "endpoint": "https://synthetic.invalid/v1/" + path,
                                  "wait_policy": WAIT})
    job = store.update_job(job["id"], route=route.model_dump())
    body, sends = Body(chunks), []
    def respond(request):
        sends.append(request.content)
        return httpx.Response(200, stream=body)
    service = Nexus(store, lambda _: "synthetic-only", httpx.MockTransport(respond))
    request = service.freeze(job["id"], "terminal-prefix", make_payload(route, "Offline", [], []), kind, {})
    return store, job, service, request, body, sends


def outcome(service, owner, key):
    try:
        return True, service.send(owner, key)
    except StopRun as exc:
        assert exc.reason == "response_rejected"
        return False, None


def snapshot(store, job):
    return {kind: store.records(kind, job) for kind in
            ("request", "attempt", "blob", "stream_receive", "operation", "version")}


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("suffix,acceptable", SUFFIXES)
@pytest.mark.parametrize("cut", ["same-chunk", "terminal-split"])
def test_file_store_fresh_saved_reopen_uses_one_rule(setup, protocol, suffix, acceptable, cut):
    usage = {"input_tokens": 19, "output_tokens": 7}
    raw = terminal(protocol, usage=usage)
    # Split inside JSON/UTF-8 and the terminal delimiter, while delivering the
    # same final received bytes. The suffix is already in the terminal chunk.
    points = [0] if cut == "same-chunk" else [0, raw.index("完".encode()) + 1, len(raw) - 1]
    chunks = [raw[a:b] for a, b in zip(points, points[1:])] + [raw[points[-1]:] + suffix]
    store, job, service, request, body, sends = prepare(setup, protocol, chunks)
    first, accepted = outcome(service, job["id"], request["id"])
    saved = store.get("request", request["id"])
    attempt = store.get("attempt", saved["attempts"][0])
    evidence = store.read_stream(job["id"], request["id"], attempt["id"])
    assert evidence["data"] == b"".join(body.received) == raw + suffix
    assert evidence["chunk_count"] == len(chunks)
    assert evidence["sha256"] == sha256(raw + suffix).hexdigest()
    assert store.bytes(saved["stream_ref"], job["id"]) == raw + suffix
    assert [store.bytes(ref, job["id"]) for ref in evidence["chunks"]] == chunks
    assert body.closed and not body.eof  # no extra read to seek gateway EOF
    before, consumed = snapshot(store, job["id"]), store.get("job", job["id"])
    reopened = Store(store.root)
    recovery = Nexus(reopened, forbidden)
    recovered = recovery.reconcile(job["id"], request["id"])
    second, answer = outcome(recovery, job["id"], request["id"])
    assert first == second == acceptable
    assert answer == accepted
    assert recovered["status"] == ("accepted" if acceptable else "rejected")
    assert snapshot(reopened, job["id"]) == before
    assert reopened.get("job", job["id"]) == consumed and consumed["attempts"] == len(sends) == 1
    assert reopened.bytes(request["payload_ref"], job["id"]) == sends[0]
    if acceptable:
        stage = reopened.get("blob", saved["accepted_ref"])
        assert attempt["usage"] == accepted["usage"] == usage
        assert attempt["finished"] == stage["meta"]["received_at"]
        assert accepted["text"] == "Saved text 完整"
    else:
        assert saved["accepted_ref"] is None and attempt["usage"] is None
        assert not reopened.maybe("blob", "accepted:" + request["id"])


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("suffix,acceptable", SUFFIXES)
def test_decoder_cuts_inside_suffix_sse_json_and_utf8_preserve_the_rule(protocol, suffix, acceptable):
    raw = terminal(protocol) + suffix
    # These feed all chosen bytes before finalizing. Unlike the live receiver,
    # the decoder alone does not decide which later chunks to request.
    for width in (len(raw), 1, 3, 7):
        decoder = StreamDecoder(protocol)
        try:
            for start in range(0, len(raw), width):
                decoder.feed(raw[start:start + width])
            value = decoder.finish_received()
        except StreamError:
            assert not acceptable
        else:
            assert acceptable
            expected = StreamDecoder(protocol)
            expected.feed(terminal(protocol))
            assert value == expected.finish_received() == decoder.finish()


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("suffix", [b"data: {", b"\xe4", b": heartbeat"])
def test_unread_later_chunks_are_not_claimed_as_received(setup, protocol, suffix):
    raw = terminal(protocol)
    store, job, service, request, body, sends = prepare(setup, protocol, [raw, suffix])
    first, accepted = outcome(service, job["id"], request["id"])
    assert first
    saved = store.get("request", request["id"])
    evidence = store.read_stream(job["id"], request["id"], saved["attempts"][0])
    assert body.received == [raw] and not body.eof and body.closed
    assert evidence["data"] == raw and evidence["chunk_count"] == 1
    assert Nexus(Store(store.root), forbidden).send(job["id"], request["id"]) == accepted
    assert len(sends) == 1


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("suffix,cut,acceptable", [
    (b": heartbeat", 1, True), (b": heartbeat", 5, True),
    (b"data: {\"x\":1}\n\n", 1, False), (b"data: {\"x\":1}\n\n", 9, False),
    (": 心跳".encode(), 3, False), (": 心跳".encode(), 5, True)])
def test_terminal_chunk_with_only_part_of_suffix_saves_exact_actual_prefix(setup, protocol, suffix, cut, acceptable):
    raw = terminal(protocol)
    # The final terminal token itself is split, then only part of the suffix
    # arrives with its completion. A later chunk must remain unread.
    split = raw.index(b"[DONE]") + 2 if protocol == "chat_completions" else len(raw) - 8
    chunks = [raw[:split], raw[split:] + suffix[:cut], suffix[cut:]]
    store, job, service, request, body, sends = prepare(setup, protocol, chunks)
    first, accepted = outcome(service, job["id"], request["id"])
    assert first == acceptable and body.received == chunks[:2]
    actual = raw + suffix[:cut]
    saved = store.get("request", request["id"])
    evidence = store.read_stream(job["id"], request["id"], saved["attempts"][0])
    assert evidence["data"] == actual and evidence["chunk_count"] == 2
    recovered, answer = outcome(Nexus(Store(store.root), forbidden), job["id"], request["id"])
    assert recovered == acceptable and answer == accepted
    assert len(sends) == 1


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_send_validates_suffix_without_repeating_full_constituent_read(setup, monkeypatch, protocol):
    raw = terminal(protocol) + b": heartbeat"
    store, job, service, request, _, _ = prepare(setup, protocol, [raw])
    read_stream, reads = store.read_stream, []
    def track(*args):
        reads.append(args)
        return read_stream(*args)
    monkeypatch.setattr(store, "read_stream", track)
    assert outcome(service, job["id"], request["id"])[0]
    assert len(reads) == 1  # existing strict archive pass, no settlement reread
    service.reconcile(job["id"], request["id"])
    assert len(reads) == 2  # reopen validation remains strict


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("case", ["invalid-json", "invalid-utf8", "unfinished-frame", "eof", "disconnect"])
def test_bad_prefix_or_absent_terminal_is_never_rescued_by_suffix_rule(setup, protocol, case):
    partial = delta(protocol, "Preserved partial 完整")
    chunks = {
        "invalid-json": [b"data: {bad}\n\n" + terminal(protocol)],
        "invalid-utf8": [b": \xff\n\n" + terminal(protocol)],
        "unfinished-frame": [b"data: {" + terminal(protocol)],
        "eof": [partial],
        "disconnect": [partial, httpx.ReadError("synthetic disconnect")],
    }[case]
    store, job, service, request, body, sends = prepare(setup, protocol, chunks)
    with pytest.raises(StopRun) as error:
        service.send(job["id"], request["id"])
    unknown = case in {"eof", "disconnect"}
    assert error.value.reason == ("unknown_outcome" if unknown else "response_rejected")
    saved = store.get("request", request["id"])
    assert saved["status"] == ("unknown" if unknown else "rejected") and saved["accepted_ref"] is None
    attempt = store.get("attempt", saved["attempts"][0])
    assert attempt["usage"] is None and not store.records("operation", job["id"])
    assert store.read_stream(job["id"], request["id"], attempt["id"])["data"] == b"".join(body.received)
    if unknown:
        assert store.get("blob", saved["stream_ref"])["meta"]["chunk_validation"] == "registration_only"
    before = snapshot(store, job["id"])
    assert Nexus(Store(store.root), forbidden).reconcile(job["id"], request["id"]) == saved
    assert snapshot(store, job["id"]) == before and len(sends) == 1


def old_send(monkeypatch, service, job, request):
    """Isolated legacy fixture: old reception returned at decoder.complete.

    Only the newly added final boundary check is omitted. Feed, chunks, Store,
    staging and atomic settlement remain real; full data frames still reject.
    """
    with monkeypatch.context() as legacy:
        legacy.setattr(StreamDecoder, "finish_received", lambda self: deepcopy(self.value))
        return service.send(job, request)


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("suffix,acceptable", [
    (b": heartbeat", True), (b"data: {", False), (b"\xe4", False)])
@pytest.mark.parametrize("state", ["staged", "pointer-inflight", "settled"])
def test_historical_acceptance_reuse_or_explicit_conflict_preserves_all_evidence(
        setup, monkeypatch, protocol, suffix, acceptable, state):
    usage = None if state == "staged" else {"input_tokens": 19, "output_tokens": 7}
    store, job, service, request, body, sends = prepare(setup, protocol, [terminal(protocol, usage=usage) + suffix],
                                                       kind="compaction" if state == "staged" else "normal")
    inflight, put = [], store.put_tx
    def capture(db, kind, key, owner, value):
        if kind == "attempt" and value["status"] == "in_flight":
            inflight.append(deepcopy(value))
        return put(db, kind, key, owner, value)
    monkeypatch.setattr(store, "put_tx", capture)
    accepted = old_send(monkeypatch, service, job["id"], request["id"])
    saved = store.get("request", request["id"])
    if state != "settled":
        store.put("attempt", inflight[0]["id"], job["id"], inflight[0])
    if state == "staged":
        store.put("request", request["id"], job["id"], {**saved, "status": "in_flight", "accepted_ref": None})
    before, consumed = snapshot(store, job["id"]), store.get("job", job["id"])
    all_bytes = {b["ref"]: store.bytes(b["ref"], job["id"]) for b in before["blob"]}
    reopened = Store(store.root)
    recovery = Nexus(reopened, forbidden)
    if acceptable:
        recovered = recovery.reconcile(job["id"], request["id"])
        assert recovery.send(job["id"], request["id"]) == accepted
        assert recovered == saved
        attempt = reopened.get("attempt", saved["attempts"][0])
        assert attempt["status"] == "accepted" and attempt["usage"] == usage
        assert attempt["finished"] == reopened.get("blob", saved["accepted_ref"])["meta"]["received_at"]
        stable = snapshot(reopened, job["id"])
        assert recovery.reconcile(job["id"], request["id"]) == saved
        assert snapshot(reopened, job["id"]) == stable
    else:
        for operation in (recovery.reconcile, recovery.send):
            with pytest.raises(StopRun) as error:
                operation(job["id"], request["id"])
            assert error.value.reason == "accepted_evidence_conflict"
            assert "retained" in str(error.value)
            assert snapshot(reopened, job["id"]) == before
    assert reopened.get("job", job["id"]) == consumed and consumed["attempts"] == len(sends) == 1
    assert {b["ref"]: reopened.bytes(b["ref"], job["id"]) for b in before["blob"]} == all_bytes
    assert reopened.records("blob", job["id"]) == before["blob"]
    assert reopened.records("stream_receive", job["id"]) == before["stream_receive"]


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("suffix,historical,acceptable", [
    (b": heartbeat", False, True), (b": heartbeat", True, True),
    (b"data: {", True, False), (b"\xe4", True, False)])
def test_runtime_tool_commit_checkpoint_reopen_preserves_effects_and_delivery(
        delivery, tmp_path, monkeypatch, protocol, suffix, historical, acceptable):
    from pdfmd.documents import Documents
    from pdfmd.runtime import Runtime
    from test_response_repairs import native
    from test_runtime import tool
    from test_streaming_delivery import stream_frames

    store, initial, version, image, source = delivery
    job = protocol_job(store, initial, protocol)
    path = "chat/completions" if protocol == "chat_completions" else "responses"
    store.update_job(job["id"], route={**job["route"], "wait_policy": WAIT,
                                     "endpoint": "https://synthetic.invalid/v1/" + path})
    content = Documents(store).version(job["id"], version)["content"]
    reply = native(protocol, tool("edit_document", {"base_version": version, "expected_head": version,
        "replace_blocks": content["blocks"], "claim": "complete"}, "save"),
        tool("report", {"state": "waiting", "message": "Preserved both source pages and figure."}, "report"))
    raw, sends = b"".join(stream_frames(protocol, reply)) + suffix, []
    def respond(request):
        sends.append(request.content)
        return httpx.Response(200, stream=Body([raw]))
    runtime = Runtime(store, Nexus(store, lambda _: "synthetic-only", httpx.MockTransport(respond)))
    execute, effects = runtime.dispatcher.execute, []
    def commit_gap(*args):
        result = execute(*args)
        if args[2] == "edit_document":
            effects.append(args[1])
            raise RuntimeError("synthetic commit before graph checkpoint")
        return result
    monkeypatch.setattr(runtime.dispatcher, "execute", commit_gap)
    try:
        with monkeypatch.context() as reception:
            if historical:
                reception.setattr(StreamDecoder, "finish_received", lambda self: deepcopy(self.value))
            with pytest.raises(RuntimeError, match="synthetic commit"):
                runtime.run(job["id"])
    finally:
        runtime.close()
    saved = store.get("job", job["id"])["head"]
    assert saved != version and len(effects) == 1
    edit_receipt = store.get("operation", effects[0])
    before, seed = snapshot(store, job["id"]), store.get("operation", "seed")
    request = before["request"][0]
    accepted = store.json(request["accepted_ref"], job["id"])
    received = store.read_stream(job["id"], request["id"], request["attempts"][0])
    assert received["data"] == raw and received["chunk_count"] == 1
    frozen = store.bytes(request["payload_ref"], job["id"])
    reopened = Store(store.root)
    restored = Runtime(reopened, Nexus(reopened, forbidden))
    dispatches = []
    dispatch = restored.dispatcher.execute
    def track(*args):
        dispatches.append(args[2])
        return dispatch(*args)
    monkeypatch.setattr(restored.dispatcher, "execute", track)
    try:
        restored.run(job["id"])
        if acceptable:
            assert not restored.graph.get_state({"configurable": {"thread_id": job["id"]}}).next
    finally:
        restored.close()
    current = reopened.get("job", job["id"])
    assert current["head"] == saved and current["attempts"] == len(sends) == 1
    assert len(reopened.records("version", job["id"])) == 2
    assert reopened.get("operation", effects[0]) == edit_receipt and reopened.get("operation", "seed") == seed
    assert reopened.get("request", request["id"]) == request
    assert reopened.records("attempt", job["id"]) == before["attempt"]
    assert reopened.records("stream_receive", job["id"]) == before["stream_receive"]
    assert reopened.bytes(request["payload_ref"], job["id"]) == frozen
    assert reopened.json(request["accepted_ref"], job["id"]) == accepted
    assert all(reopened.get("blob", b["ref"]) == b for b in before["blob"])
    assert reopened.bytes(accepted["stream_ref"], job["id"]) == raw
    if acceptable:
        assert current["status"] == "waiting" and dispatches == ["report"]
    else:
        assert current["status"] == "blocked" and current["stop_reason"] == "accepted_evidence_conflict"
        assert "retained" in current["last_message"] and dispatches == []
        assert reopened.records("operation", job["id"]) == before["operation"]
    check_delivery(reopened, job, saved, image, source, tmp_path / "terminal-delivery.zip")
    assert Documents(reopened).version(job["id"], saved)["content"] == content


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_suffix_rule_covers_real_compaction_handoff_edit_and_export(tmp_path, monkeypatch, protocol):
    import test_streaming_delivery as flow
    original = flow.stream_frames
    def suffixed(protocol, value):
        frames = original(protocol, value)
        # The reused transport cuts frames at byte 19. Keep the terminal past
        # that cut so this workflow actually receives the entire suffix.
        frames[-1] = b": receive-boundary padding\n\n" + frames[-1] + b": heartbeat"
        return frames
    monkeypatch.setattr(flow, "stream_frames", suffixed)
    # Reuse the source-led Engine workflow and its complete native/raw/usage,
    # historical unknown, draft, image and every-ZIP-member assertions.
    flow.test_streamed_handoff_then_edit_preserves_reopen_export_and_unknown_boundary(tmp_path, protocol)


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_native_acceptance_with_safe_suffix_does_not_accept_invalid_handoff(setup, protocol):
    from pdfmd.runtime import Runtime
    store, job, service, request, _, sends = prepare(setup, protocol,
        [terminal(protocol, text="Not handoff JSON") + b": heartbeat"], kind="compaction")
    runtime = Runtime(store, service)
    state = {"job": job["id"], "pending": request["id"], "seq": 0, "revision": 0,
             "history": [], "handoff": None, "repairs": {}}
    try:
        result = runtime.compact(state)
    finally:
        runtime.close()
    saved = store.get("request", request["id"])
    assert saved["status"] == "accepted" and saved["accepted_ref"]
    feedback = store.json(result["repairs"]["compaction"]["feedback_ref"], job["id"])
    assert feedback["code"] == "invalid_handoff" and result["next"] == "prepare"
    assert not store.records("operation", job["id"]) and len(sends) == 1
    assert Nexus(Store(store.root), forbidden).reconcile(job["id"], request["id"]) == saved
