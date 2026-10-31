"""Selected A controls. Synthetic bytes and isolated stores; no live transport."""
from copy import deepcopy
import json
import pytest

from pdfmd.nexus import Nexus, StopRun, parse_reply
from pdfmd.storage import Store, encode
from pdfmd.streaming import StreamDecoder, StreamError
from pdfmd.usage import interpret_usage
from pdfmd.receive_diagnostics import safe_receive
from tests.engine.transport.test_streaming_parser import chat, event, message, completed
from tests.engine.transport.test_stream_terminal import prepare, forbidden, snapshot


PROTOCOLS = ["chat_completions", "responses"]

def counts(protocol):
    return ({"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13,
             "prompt_tokens_details": {"cached_tokens": 2, "cache_write_tokens": 3, "image_tokens": 4, "text_tokens": 5, "audio_tokens": 1},
             "completion_tokens_details": {"reasoning_tokens": 1, "text_tokens": 2, "audio_tokens": 0}}
            if protocol == PROTOCOLS[0] else {"input_tokens": 10, "output_tokens": 3, "total_tokens": 13,
             "input_tokens_details": {"cached_tokens": 2, "cache_write_tokens": 3,
                 "cache_write_tokens_details": {"ttl_30m_tokens": 1, "ttl_12h_tokens": 2}}})

def raw_reply(protocol, usage, *, text="Faithful 完整 25 mg."):
    if protocol == PROTOCOLS[0]:
        return event(chat({"content": text}, finish="stop", usage=usage)) + event("[DONE]")
    value = completed([message(text)])
    value["response"]["usage"] = usage
    return event(value)


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("bad", [-1, True, "3", 1.5])
def test_usage_counts_are_integer_and_not_bool(protocol, bad):
    raw = counts(protocol)
    raw[next(iter(raw))] = bad
    assert interpret_usage(protocol, raw).reason == "count"
    assert interpret_usage(protocol, raw).value is None


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_usage_partial_total_subset_unknown_metadata_and_missing(protocol):
    raw = counts(protocol)
    incoming, outgoing = list(raw)[:2]
    assert interpret_usage(protocol, raw).status == "complete"
    assert interpret_usage(protocol, {incoming: 10}).status == "partial"
    assert interpret_usage(protocol, {incoming: 10}).value == {incoming: 10}
    assert interpret_usage(protocol, {**raw, "extra": {"arbitrary": "not a count"}}).status == "complete"
    assert interpret_usage(protocol, {**raw, "total_tokens": 14}).reason == "total"
    details = incoming + "_details"
    assert interpret_usage(protocol, {**raw, details: {"cached_tokens": 11}}).reason == "subset"
    assert interpret_usage(protocol, {details: {"cached_tokens": 9}}).status == "partial"
    assert interpret_usage(protocol, {**raw, outgoing + "_details": {"reasoning_tokens": 2}}).value is not None
    for absent in (None, {}, [], "bad", False):
        assert interpret_usage(protocol, absent).value is None


@pytest.mark.parametrize("values,expected,status", [
    (["auto", "default"], "default", "known"), (["default", None], None, "unknown"),
    ([None, "priority"], "priority", "known"), (["flex", "flex"], "flex", "known"),
    (["default", {"bad": True}], None, "unavailable")])
def test_service_observations_update_without_changing_identity(values, expected, status):
    decoder = StreamDecoder(PROTOCOLS[0])
    for value in values:
        decoder.feed(event(chat(service_tier=value, system_fingerprint=None, created=1)))
    decoder.feed(event(chat({"content": "Final"}, finish="stop", benign_extra={"x": True})))
    decoder.feed(event("[DONE]"))
    assert decoder.finish()["service_tier"] == expected
    assert [o for o in decoder.service_observations if o["field"] == "service_tier"][-1]["status"] == status
    assert decoder.service_observations[-1]["ordinal"] == 2


@pytest.mark.parametrize("field,value", [("id", "other"), ("model", "other"), ("created", 2)])
def test_identity_stays_strict(field, value):
    decoder = StreamDecoder(PROTOCOLS[0])
    decoder.feed(event(chat(created=1)))
    with pytest.raises(StreamError) as caught:
        decoder.feed(event({**chat(created=1), field: value}))
    assert caught.value.diagnostic == {"category": "identity_conflict", "field": field, "stage": "decode", "ordinal": 2}


@pytest.mark.parametrize("neutral", [None, "", [], {}, {"role": "assistant", "refusal": None, "content": "", "tool_calls": []}])
def test_choice_competing_container_neutral_values(neutral):
    value = chat({"content": "Final"}, finish="stop")
    value["choices"][0]["message"] = neutral
    decoder = StreamDecoder(PROTOCOLS[0])
    decoder.feed(event(value) + event("[DONE]"))
    assert parse_reply(PROTOCOLS[0], encode(decoder.finish()))["text"] == "Final"


@pytest.mark.parametrize("field,value", [("message", {"refusal": "hidden"}), ("text", "hidden"), ("content", ["hidden"]), ("refusal", "hidden"), ("tool_calls", [{"id": "hidden"}])])
def test_choice_cannot_hide_content(field, value):
    chunk = chat({"content": "Final"}, finish="stop")
    chunk["choices"][0][field] = value
    with pytest.raises(StreamError):
        StreamDecoder(PROTOCOLS[0]).feed(event(chunk))


@pytest.mark.parametrize("summary", [False, True])
@pytest.mark.parametrize("contradiction", [False, True])
def test_official_part_events_match_or_conflict_with_terminal(summary, contradiction):
    decoder = StreamDecoder("responses")
    part = {"type": "summary_text" if summary else "output_text", "text": "Original"}
    item = {"id": "message", "type": "reasoning", "summary": [part], "encrypted_content": "opaque"} if summary else message("Original")
    stem = "response.reasoning_summary_part" if summary else "response.content_part"
    key = "summary_index" if summary else "content_index"
    decoder.feed(event({"type": stem + ".added", "output_index": 0, "item_id": "message", key: 0, "part": {**part, "text": ""}}))
    decoder.feed(event({"type": stem + ".done", "output_index": 0, "item_id": "message", key: 0, "part": part}))
    final = deepcopy(item)
    if contradiction:
        final["summary" if summary else "content"][0]["text"] = "Changed"
        with pytest.raises(StreamError):
            decoder.feed(event(completed([final])))
    else:
        decoder.feed(event(completed([final])))
        assert decoder.finish()["output"][0] == final


@pytest.mark.parametrize("kind", ["response.refusal.delta", "response.refusal.done", "response.unknown.delta"])
def test_semantic_signals_cannot_disappear(kind):
    with pytest.raises(StreamError):
        StreamDecoder("responses").feed(event({"type": kind, "output_index": 0, "content_index": 0, "item_id": "m", "delta": "hidden", "refusal": "hidden"}))


@pytest.mark.parametrize("container", ["message", "reasoning"])
def test_unknown_native_parts_rejected_in_stream_and_nonstream(container):
    item = {"id": "m", "type": container, "content": [{"type": "future_content", "text": "hidden"}]}
    with pytest.raises(StreamError):
        StreamDecoder("responses").feed(event(completed([item])))
    with pytest.raises(ValueError):
        parse_reply("responses", encode(completed([item])["response"]))


def test_cc_aggregate_repeat_conflict_and_malformed_are_not_content_errors():
    for reports, reason in [([counts(PROTOCOLS[0])] * 2, None),
                            ([counts(PROTOCOLS[0]), {"prompt_tokens": 20}], "conflicting_aggregates"),
                            ([[], counts(PROTOCOLS[0])], "container")]:
        decoder = StreamDecoder(PROTOCOLS[0])
        for usage in reports:
            decoder.feed(event({"id": "reply", "choices": [], "usage": usage}))
        decoder.feed(event(chat({"content": "Valid"}, finish="stop")) + event("[DONE]"))
        accepted = parse_reply(PROTOCOLS[0], encode(decoder.finish()))
        assert accepted["text"] == "Valid"
        assert decoder.usage.reason == reason
        assert accepted["usage"] == (counts(PROTOCOLS[0]) if reason is None else None)


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("outcome", ["known", "unknown", "content_conflict"])
@pytest.mark.parametrize("kind", ["normal", "compaction"])
def test_first_save_reopen_outcomes_match_without_effects(setup, protocol, outcome, kind):
    raw = raw_reply(protocol, counts(protocol) if outcome == "known" else ["invalid usage"])
    if outcome == "content_conflict":
        if protocol == PROTOCOLS[0]:
            prefix = chat()
            prefix["choices"][0]["message"] = {"refusal": "hidden"}
        else:
            prefix = {"type": "response.refusal.done", "output_index": 0, "item_id": "message", "content_index": 0, "refusal": "hidden"}
        raw = event(prefix) + raw
    store, job, nexus, request, body, sends = prepare(setup, protocol, [raw], kind=kind)
    if outcome == "content_conflict":
        with pytest.raises(StopRun):
            nexus.send(job["id"], request["id"])
        accepted = None
    else:
        accepted = nexus.send(job["id"], request["id"])
        assert accepted["usage"] == (counts(protocol) if outcome == "known" else None)
        assert store.json(accepted["native_ref"], job["id"])
    before = snapshot(store, job["id"])
    consumption = store.get("job", job["id"])
    reopened = Store(store.root)
    recovery = Nexus(reopened, forbidden)
    recovery.reconcile(job["id"], request["id"])
    if accepted:
        assert recovery.send(job["id"], request["id"]) == accepted
    else:
        with pytest.raises(StopRun):
            recovery.send(job["id"], request["id"])
    assert snapshot(reopened, job["id"]) == before
    assert reopened.get("job", job["id"]) == consumption
    assert len(sends) == consumption["attempts"] == 1
    assert not reopened.records("operation", job["id"])
    assert reopened.read_stream(job["id"], request["id"], before["attempt"][0]["id"])["data"] == raw


def test_summary_never_echoes_arbitrary_upstream_values():
    secret = "synthetic-upstream-secret-DO-NOT-SUMMARIZE"
    decoder = StreamDecoder(PROTOCOLS[0])
    decoder.feed(event(chat({"content": "Valid"}, finish=secret)) + event("[DONE]"))
    assert decoder.terminal == "unsupported_finish"
    with pytest.raises(ValueError):
        parse_reply(PROTOCOLS[0], encode(decoder.finish()))
    compact = safe_receive({"terminal_event": secret, "stop_cause": secret, "error": secret, "received_body_bytes": secret,
        "diagnostic": {"category": secret, "field": secret, "stage": secret, "ordinal": secret}})
    assert secret not in json.dumps(compact)
    assert secret in json.dumps(decoder.value)


def test_responses_metadata_final_snapshot_and_lifecycle_are_observations():
    decoder = StreamDecoder("responses")
    for tier in ("auto", None, "default"):
        assert not decoder.feed(event({"type": "response.in_progress", "response": {
            "id": "reply", "model": "offline", "created_at": 1, "service_tier": tier}})).progress
    value = completed([message()])
    decoder.feed(event(value))
    assert decoder.finish()["service_tier"] == "default"
    assert decoder.usage.value == value["response"]["usage"]  # terminal owns final usage


@pytest.mark.parametrize("variant", ["item-id", "call-id", "omitted", "duplicate-item", "bad-arguments"])
def test_response_attribution_and_tool_integrity_stay_strict(variant):
    item = {"id": "tool", "type": "function_call", "call_id": "call", "name": "read_document", "arguments": "{}"}
    decoder = StreamDecoder("responses")
    decoder.feed(event({"type": "response.output_item.added", "output_index": 0, "item": {**item, "arguments": ""}}))
    final = deepcopy(item)
    if variant == "item-id": final["id"] = "different"
    if variant == "call-id": final["call_id"] = "different"
    if variant == "bad-arguments": final["arguments"] = '{"incomplete":'
    output = [] if variant == "omitted" else [final, deepcopy(final)] if variant == "duplicate-item" else [final]
    try:
        decoder.feed(event(completed(output)))
        value = decoder.finish()
    except StreamError:
        assert variant != "bad-arguments"
    else:
        with pytest.raises(ValueError):
            parse_reply("responses", encode(value))


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_native_malformed_containers_and_nonfinite_arguments_are_bounded(protocol):
    for raw in (b'[]', b'null', b'{"choices":[null]}', b'{"status":"completed","output":[null]}'):
        with pytest.raises(ValueError):
            parse_reply(protocol, raw)
    from tests.engine.transport.test_response_repairs import native
    value = native(protocol)
    if protocol == PROTOCOLS[0]:
        value['choices'][0]['message']['tool_calls'] = [{'id': 'call', 'type': 'function', 'function': {'name': 'report', 'arguments': '{"bad":NaN}'}}]
    else:
        value['output'] = [{'id': 'item', 'type': 'function_call', 'call_id': 'call', 'name': 'report', 'arguments': '{"bad":NaN}'}]
    with pytest.raises(ValueError): parse_reply(protocol, encode(value))


def test_cc_protocol_delta_segmentation_and_transport_chunking_are_independent():
    results = []
    for fragments in (["完整 text"], ["完", "整 ", "text"]):
        raw = b"".join(event(chat({"content": text})) for text in fragments) + event(chat(finish="stop")) + event("[DONE]")
        for width in (1, 7, len(raw)):
            decoder = StreamDecoder(PROTOCOLS[0])
            for offset in range(0, len(raw), width): decoder.feed(raw[offset:offset+width])
            results.append(parse_reply(PROTOCOLS[0], encode(decoder.finish())))
    assert all(value == results[0] for value in results)


def test_responses_delta_segmentation_and_annotation_completion():
    results = []
    for fragments in (["Complete"], ["Com", "plete"]):
        annotation = {"type": "url_citation", "url": "https://synthetic.invalid", "title": "source", "start_index": 0, "end_index": 3}
        events = [event({"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "item_id": "message", "delta": text}) for text in fragments]
        events.append(event({"type": "response.output_text.annotation.added", "output_index": 0, "content_index": 0,
            "item_id": "message", "annotation_index": 0, "annotation": annotation}))
        final = message("Complete")
        final["content"][0]["annotations"] = [annotation]
        raw = b"".join(events) + event(completed([final]))
        for width in (1, 9, len(raw)):
            decoder = StreamDecoder("responses")
            for offset in range(0, len(raw), width): decoder.feed(raw[offset:offset+width])
            results.append(parse_reply("responses", encode(decoder.finish())))
        decoder = StreamDecoder("responses")
        decoder.feed(b"".join(events))
        with pytest.raises(StreamError): decoder.feed(event(completed([message("Complete")])))
    assert all(value == results[0] for value in results)


def test_saved_upstream_finish_remains_raw_but_never_in_compact_engine_summary(setup):
    from pdfmd.server import Engine
    secret = "synthetic-finish-DO-NOT-SUMMARIZE"
    raw = event(chat({"content": "Preserved"}, finish=secret)) + event("[DONE]")
    store, job, nexus, request, _, sends = prepare(setup, PROTOCOLS[0], [raw])
    with pytest.raises(StopRun): nexus.send(job['id'], request['id'])
    for current in (store, Store(store.root)):
        engine = Engine.__new__(Engine)
        engine.store = current
        saved = current.get('request', request['id'])
        summary = engine.receive_observation(job['id'], saved)
        assert secret not in json.dumps(summary)
        assert summary['terminal_event'] == 'unsupported_finish'
        assert summary['diagnostic']['stage'] == 'native'
        assert secret.encode() in current.bytes(saved['stream_ref'], job['id'])
    assert len(sends) == 1


@pytest.mark.parametrize('protocol', PROTOCOLS)
def test_old_unvalidated_projection_stops_without_rewriting_original_facts(setup, protocol, monkeypatch):
    """An explicitly synthetic old interpreter; never original task evidence."""
    import httpx
    import pdfmd.nexus as module
    from pdfmd.schema import Route
    from pdfmd.usage import Usage
    from tests.engine.context.test_context_admission import protocol_job
    from tests.engine.transport.test_response_repairs import native
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    route = Route.model_validate(job['route'])
    value = native(protocol, text='Historical synthetic content retained.')
    value['usage'] = {next(iter(counts(protocol))): -1}
    sends = []
    def transport(request):
        sends.append(request.content)
        return httpx.Response(200, json=value)
    service = Nexus(store, lambda _: 'synthetic-only', httpx.MockTransport(transport))
    from pdfmd.nexus import make_payload
    request = service.freeze(job['id'], 'synthetic-old-projection', make_payload(route, 'Offline', [], []), 'normal', {})
    with monkeypatch.context() as old:
        old.setattr(module, 'interpret_usage', lambda protocol, raw: Usage(raw, 'complete'))
        service.send(job['id'], request['id'])
    before = snapshot(store, job['id'])
    counter = store.get('job', job['id'])
    originals = {b['ref']: store.bytes(b['ref'], job['id']) for b in before['blob']}
    with pytest.raises(StopRun) as caught:
        Nexus(Store(store.root), forbidden).reconcile(job['id'], request['id'])
    assert caught.value.reason == 'accepted_evidence_conflict'
    assert snapshot(store, job['id']) == before and store.get('job', job['id']) == counter
    assert all(store.bytes(ref, job['id']) == raw for ref, raw in originals.items())
    assert len(sends) == 1


def test_official_compaction_observation_does_not_authorize_native_compaction():
    decoder = StreamDecoder('responses')
    assert not decoder.feed(event({'type': 'response.compaction.compacting', 'output_index': 0, 'item_id': 'compact'})).progress
    decoder.feed(event(completed([{'id': 'compact', 'type': 'compaction', 'encrypted_content': 'opaque'}])))
    with pytest.raises(ValueError): parse_reply('responses', encode(decoder.finish()))


@pytest.mark.parametrize('value', [
    {'type': 'response.in_progress', 'response': {'id': 'reply', 'status': 'failed'}},
    {'type': 'response.in_progress', 'response': {'id': 'reply', 'error': {'message': 'secret'}}},
    {'type': 'response.in_progress', 'response': {'status': {}}},
    {'type': 'response.in_progress', 'response': {'output': None}},
])
def test_error_control_or_malformed_lifecycle_cannot_disappear(value):
    with pytest.raises(StreamError): StreamDecoder('responses').feed(event(value))


@pytest.mark.parametrize('protocol', PROTOCOLS)
def test_accounting_detail_scope_and_additional_metadata(protocol):
    raw = counts(protocol)
    incoming = 'prompt_tokens_details' if protocol == PROTOCOLS[0] else 'input_tokens_details'
    raw[incoming]['vendor'] = {'arbitrary': True}
    if protocol == 'responses': raw[incoming]['audio_tokens'] = 'unknown metadata for this schema'
    result = interpret_usage(protocol, raw)
    assert result.status == 'complete' and result.value == counts(protocol)
    raw[incoming]['cache_write_tokens'] = True
    assert interpret_usage(protocol, raw).reason == 'count'


@pytest.mark.parametrize('field', ['image_tokens', 'text_tokens', 'cache_write_tokens'])
def test_cc_documented_details_are_validated(field):
    raw = counts(PROTOCOLS[0])
    raw['prompt_tokens_details'][field] = 11
    assert interpret_usage(PROTOCOLS[0], raw).reason == 'subset'


@pytest.mark.parametrize('detail,reason', [
    ({'cached_tokens': 7, 'cache_write_tokens': 7}, 'subset'),
    ({'cache_write_tokens': 3, 'cache_write_tokens_details': {'ttl_30m_tokens': 1, 'ttl_12h_tokens': 1}}, 'details_total'),
    ({'cache_write_tokens': 3, 'cache_write_tokens_details': {'ttl_30m_tokens': -1}}, 'count'),
    ({'cache_write_tokens': 3, 'cache_write_tokens_details': {'ttl_12h_tokens': True}}, 'count'),
    ({'cache_write_tokens': 3, 'cache_write_tokens_details': {'ttl_12h_tokens': 4}}, 'subset'),
    ({'cache_write_tokens_details': []}, 'details_container'),
])
def test_responses_write_breakdown_never_double_counts_or_invents_total(detail, reason):
    raw = {**counts('responses'), 'input_tokens_details': detail}
    assert interpret_usage('responses', raw).reason == reason
    assert interpret_usage('responses', {'input_tokens_details': {'cache_write_tokens_details': {'ttl_12h_tokens': 2}}}).status == 'partial'
