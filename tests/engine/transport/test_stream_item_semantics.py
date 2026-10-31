"""SC02 item lifecycle/role controls; synthetic bytes and fresh fixture stores only."""
from copy import deepcopy
from hashlib import sha256

import pytest

from pdfmd.nexus import Nexus, StopRun, parse_reply
from pdfmd.storage import Store, encode
from pdfmd.streaming import StreamDecoder, StreamError
from tests.engine.transport.test_streaming_parser import completed, event, message
from tests.engine.transport.test_stream_terminal import forbidden, prepare, snapshot


ABSENT = object()
TYPES = ["function_call", "message", "reasoning"]


def item(kind="function_call", **changes):
    if kind == "function_call":
        value = {"id": "tool", "type": kind, "call_id": "call", "name": "read_document",
                 "arguments": '{"version":"v1","text":"完整"}'}
    elif kind == "message":
        value = message("Preserve 完整 25 mg.")
    else:
        value = {"id": "reason", "type": kind, "summary": [], "encrypted_content": "opaque-final"}
    return {**value, **changes}


def observation(value, phase):
    if phase in {"created", "in_progress", "queued"}:
        return {"type": "response." + phase, "response": {"id": "reply", "output": [value]}}
    return {"type": "response.output_item." + phase, "output_index": 0, "item": value}


def stream_case(kind="function_call", field="status", value="incomplete", phase="done", omit=False):
    observed = item(kind, **{field: value})
    final = item(kind, status="completed")
    if omit:
        final.pop(field, None)
    return event(observation(observed, phase)) + event(completed([final]))


def decode(raw, width):
    decoder = StreamDecoder("responses")
    for offset in range(0, len(raw), width):
        decoder.feed(raw[offset:offset + width])
    return parse_reply("responses", encode(decoder.finish_received()))


@pytest.mark.parametrize("kind", TYPES)
@pytest.mark.parametrize("status", ["incomplete", "in_progress"])
@pytest.mark.parametrize("omit", [False, True], ids=["terminal-replaces", "terminal-omits"])
def test_done_status_cannot_be_erased(kind, status, omit):
    raw = stream_case(kind, value=status, omit=omit)
    for width in (len(raw), 1, 17):
        with pytest.raises(StreamError):
            decode(raw, width)


@pytest.mark.parametrize("phase", ["added", "done", "created", "in_progress", "queued"])
@pytest.mark.parametrize("omit", [False, True])
def test_message_role_cannot_be_erased_even_with_valid_tool(phase, omit):
    final = item("message", status="completed")
    if omit:
        final.pop("role")
    raw = event(observation(item("message", role="user"), phase)) + event(completed([final, item()]))
    for width in (len(raw), 1, 17):
        with pytest.raises(StreamError):
            decode(raw, width)


@pytest.mark.parametrize("kind", TYPES)
@pytest.mark.parametrize("phase", ["added", "done", "in_progress", "terminal"])
@pytest.mark.parametrize("value", [None, True, 1, [], {}, "", "future-status", "failed", "cancelled", "incomplete"])
def test_invalid_status_is_not_absence(kind, phase, value):
    raw = (event(completed([item(kind, status=value)])) if phase == "terminal"
           else stream_case(kind, value=value, phase=phase, omit=True))
    with pytest.raises(ValueError):
        decode(raw, 17)


@pytest.mark.parametrize("value", [None, True, 1, [], {}, "", "tool", "system", "developer", "future-role"])
@pytest.mark.parametrize("phase", ["added", "done", "in_progress", "terminal"])
def test_invalid_message_role_is_not_absence(value, phase):
    raw = (event(completed([item("message", role=value), item()])) if phase == "terminal"
           else stream_case("message", field="role", value=value, phase=phase, omit=True))
    with pytest.raises(ValueError):
        decode(raw, 17)


@pytest.mark.parametrize("kind", TYPES)
@pytest.mark.parametrize("done_status", [ABSENT, "completed"])
@pytest.mark.parametrize("final_status", [ABSENT, "completed"])
def test_progress_completion_and_optional_fields(kind, done_status, final_status):
    added = item(kind, status="in_progress")
    done, final = item(kind), item(kind)
    if done_status is not ABSENT:
        done["status"] = done_status
    if final_status is not ABSENT:
        final["status"] = final_status
    # The encrypted added representation is explicitly permitted to be partial.
    if kind == "reasoning":
        added["encrypted_content"] = "opaque-partial"
    output = [final, item()] if kind == "reasoning" else [final]
    raw = b"".join(event(x) for x in [observation(added, "added"), observation(done, "done"), completed(output)])
    result = decode(raw, 1)
    assert result["native"] == output


@pytest.mark.parametrize("kind", TYPES)
def test_observed_completion_cannot_regress_across_omitted_snapshot(kind):
    raw = b"".join(event(x) for x in [observation(item(kind, status="completed"), "added"),
        observation(item(kind), "in_progress"), observation(item(kind, status="in_progress"), "added"),
        completed([item(kind)])])
    with pytest.raises(StreamError):
        decode(raw, 17)


def test_reasoning_has_no_message_role_or_function_fields():
    reasoning = item("reasoning", status="completed", role=None)
    raw = event(observation(reasoning, "done")) + event(completed([reasoning, item()]))
    assert decode(raw, 1)["native"][0] == reasoning
    for status in (None, "incomplete", "in_progress", [], "future-status"):
        with pytest.raises(ValueError):
            parse_reply("responses", encode(completed([item("reasoning", status=status), item()])["response"]))


@pytest.mark.parametrize("phase", ["created", "queued"])
def test_unsuccessful_status_in_lifecycle_output_is_not_an_observation_only(phase):
    with pytest.raises(StreamError):
        decode(stream_case("message", value="incomplete", phase=phase, omit=True), 17)


@pytest.mark.parametrize("done_role", [ABSENT, "assistant"])
def test_optional_role_does_not_require_an_announcement(done_role):
    final = item("message")
    final.pop("role")
    done = deepcopy(final)
    if done_role is not ABSENT:
        done["role"] = done_role
    raw = event(observation(done, "done")) + event(completed([final]))
    assert decode(raw, 1)["native"] == [final]


@pytest.mark.parametrize("announcements", [False, True])
def test_interleaved_tools_and_permitted_delta_segmentation(announcements):
    results = []
    first, second = item(status="completed"), item(id="second", call_id="second-call", status="completed")
    for size in (1, 9, 999):
        events = []
        if announcements:
            events += [observation({**first, "status": "in_progress", "arguments": ""}, "added"),
                {"type": "response.output_item.added", "output_index": 1,
                 "item": {**second, "status": "in_progress", "arguments": ""}}]
        arguments = first["arguments"]
        for offset in range(0, len(arguments), size):
            for index, current in enumerate((first, second)):
                events.append({"type": "response.function_call_arguments.delta", "output_index": index,
                    "item_id": current["id"], "delta": arguments[offset:offset + size]})
        events += [completed([first, second])]
        raw = b"".join(event(x) for x in events)
        for width in (len(raw), 1, 17):
            results.append(decode(raw, width))
    assert all(result == results[0] for result in results)
    assert len(results[0]["calls"]) == 2


@pytest.mark.parametrize("kind", ["normal", "compaction"])
@pytest.mark.parametrize("case", ["valid", "done-incomplete", "done-progress", "role", "omitted-status", "omitted-role"])
@pytest.mark.parametrize("width", [None, 17], ids=["whole", "transport-cuts"])
def test_first_reopen_raw_provenance_and_consumption(setup, kind, case, width):
    raw = stream_case(value="completed" if case == "valid" else "in_progress" if case == "done-progress" else "incomplete",
                      omit=case == "omitted-status")
    if case in {"role", "omitted-role"}:
        final = item("message")
        if case == "omitted-role":
            final.pop("role")
        raw = event(observation(item("message", role="user"), "done")) + event(completed([final, item()]))
    chunks = [raw] if width is None else [raw[offset:offset + width] for offset in range(0, len(raw), width)]
    store, job, nexus, request, body, sends = prepare(setup, "responses", chunks, kind=kind)
    accepted = None
    if case == "valid":
        accepted = nexus.send(job["id"], request["id"])
    else:
        with pytest.raises(StopRun, match="complete"):
            nexus.send(job["id"], request["id"])
    before, consumed = snapshot(store, job["id"]), store.get("job", job["id"])
    reopened = Store(store.root)
    service = Nexus(reopened, forbidden)
    saved = service.reconcile(job["id"], request["id"])
    if accepted:
        assert service.send(job["id"], request["id"]) == accepted
        native = reopened.get("blob", accepted["native_ref"])
        stage = reopened.get("blob", saved["accepted_ref"])
        assert native["kind"] == "assembled_response"
        assert native["meta"]["source_stream_ref"] == accepted["stream_ref"]
        assert native["meta"]["attempt"] == stage["meta"]["attempt"] == saved["attempts"][0]
        assert native["meta"]["request"] == stage["meta"]["request"] == request["id"]
    else:
        assert saved["status"] == "rejected" and saved["accepted_ref"] is None
        assert not reopened.maybe("blob", "accepted:" + request["id"])
        with pytest.raises(StopRun):
            service.send(job["id"], request["id"])
    durable = reopened.read_stream(job["id"], request["id"], saved["attempts"][0])
    # A rejected early event can stop receiving before later fixture chunks;
    # only bytes actually received belong to its immutable stream evidence.
    received = b"".join(body.received)
    assert durable["data"] == received and raw.startswith(received)
    assert durable["sha256"] == sha256(received).hexdigest()
    if accepted or width is None:
        assert received == raw
    assert snapshot(reopened, job["id"]) == before
    assert reopened.get("job", job["id"]) == consumed
    assert consumed["attempts"] == len(sends) == 1
    assert not reopened.records("operation", job["id"])
