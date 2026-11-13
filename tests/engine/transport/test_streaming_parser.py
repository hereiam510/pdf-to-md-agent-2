"""Offline protocol controls: framed progress is not native/tool acceptance."""
from copy import deepcopy
import json

import pytest

from pdfmd.nexus import parse_reply
from pdfmd.storage import encode
from pdfmd.streaming import StreamDecoder, StreamError


def event(value, *, name=None, newline="\n"):
    data = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    prefix = f"event: {name}{newline}" if name else ""
    return (prefix + "data: " + data + newline * 2).encode("utf-8")


def chat(delta=None, *, finish=None, **extra):
    return {"id": "reply", "object": "chat.completion.chunk", "model": "offline",
            "choices": [{"index": 0, "delta": delta or {}, "finish_reason": finish}], **extra}


def final_response(output):
    return {"id": "reply", "object": "response", "status": "completed", "output": output,
            "usage": {"input_tokens": 7, "output_tokens": 11}}


def message(text="Source: 25 mg.\n"):
    return {"id": "message", "type": "message", "role": "assistant", "status": "completed",
            "content": [{"type": "output_text", "text": text, "annotations": []}]}


def completed(output):
    return {"type": "response.completed", "response": final_response(output)}


def test_byte_split_utf8_bom_crlf_comments_and_multiline_sse_preserve_content():
    decoder = StreamDecoder("chat_completions")
    raw = b"\xef\xbb\xbf: keep-alive\r\n\r\n" + event(chat({"role": "assistant"}), newline="\r\n")
    # Newlines between JSON tokens are legal multiline SSE data. Newlines in
    # the content string stay escaped and must survive reconstruction exactly.
    raw += ("data: " + json.dumps(chat({"content": "劑量：25 mg.\n"}), ensure_ascii=False)
            .replace(', "choices"', ',\r\ndata: "choices"') + "\r\n\r\n").encode()
    raw += event(chat(finish="stop"), newline="\r") + event("[DONE]", newline="\r")
    results = [decoder.feed(bytes([byte])) for byte in raw]
    assert sum(r.events for r in results) == 4
    assert sum(r.progress for r in results) == 1
    assert decoder.complete and decoder.terminal == "stop"
    value = decoder.finish()
    assert value["choices"][0]["message"]["content"] == "劑量：25 mg.\n"
    assert parse_reply("chat_completions", encode(value))["text"] == "劑量：25 mg.\n"


def test_chat_metadata_and_synthetic_whitespace_do_not_hide_idle_but_are_retained():
    decoder = StreamDecoder("chat_completions")
    assert not decoder.feed(b": keep-alive\n\n").progress
    assert not decoder.feed(event(chat({"role": "assistant", "content": "", "tool_calls": None}))).progress
    assert not decoder.feed(event(chat({"reasoning_content": "\n\n", "content": "  "}))).progress
    for text in ("same", "same"):
        assert decoder.feed(event(chat({"content": text}))).progress
    decoder.feed(event(chat(finish="stop")) + event("[DONE]"))
    assert decoder.finish()["choices"][0]["message"] == {
        "role": "assistant", "content": "  samesame", "reasoning_content": "\n\n"}


def test_chat_interleaved_tools_name_fragments_and_optional_usage_are_assembled_once():
    decoder = StreamDecoder("chat_completions")
    for index, call_id, name in ((0, "a", "inspect_"), (1, "b", "read_evidence")):
        assert not decoder.feed(event(chat({"tool_calls": [{"index": index, "id": call_id, "type": "function",
                "function": {"name": name, "arguments": ""}}]}))).progress
    assert not decoder.feed(event(chat({"tool_calls": [{"index": 0, "function": {"name": "pdf"}}]}))).progress
    for index, fragment in ((1, '{"ref":'), (0, '{"pages":[1]}'), (1, '"source"}')):
        assert decoder.feed(event(chat({"tool_calls": [{"index": index, "function": {"arguments": fragment}}]}))).progress
    decoder.feed(event(chat(finish="tool_calls")))
    usage = {"prompt_tokens": 17, "completion_tokens": 23, "total_tokens": 40}
    assert not decoder.feed(event({"id": "reply", "object": "chat.completion.chunk", "choices": [], "usage": usage})).progress
    decoder.feed(event("[DONE]"))
    accepted = parse_reply("chat_completions", encode(decoder.finish()))
    assert accepted["calls"] == [{"id": "a", "name": "inspect_pdf", "arguments": '{"pages":[1]}'},
                                  {"id": "b", "name": "read_evidence", "arguments": '{"ref":"source"}'}]
    assert accepted["usage"] == usage


def test_responses_preserves_terminal_native_items_and_checks_streamed_prefixes():
    decoder = StreamDecoder("responses")
    reasoning = {"id": "reason", "type": "reasoning", "summary": [{"type": "summary_text", "text": "Compare."}],
                 "encrypted_content": "opaque-retained-value"}
    tool = {"id": "tool", "type": "function_call", "status": "completed", "call_id": "call", "name": "read_document",
            "arguments": '{"version":"v1"}'}
    events = [
        {"type": "response.created", "response": {"id": "reply", "status": "in_progress"}},
        {"type": "response.output_item.added", "output_index": 0,
         "item": {"id": "reason", "type": "reasoning", "summary": []}},
        {"type": "response.reasoning_summary_text.delta", "output_index": 0, "item_id": "reason", "summary_index": 0, "delta": "Compare."},
        {"type": "response.output_item.done", "output_index": 0, "item": reasoning},
        {"type": "response.output_item.added", "output_index": 1, "item": {**tool, "status": "in_progress", "arguments": ""}},
        {"type": "response.function_call_arguments.delta", "output_index": 1, "item_id": "tool", "delta": '{"version":'},
        {"type": "response.function_call_arguments.done", "output_index": 1, "item_id": "tool", "arguments": tool["arguments"]},
        {"type": "response.output_item.done", "output_index": 1, "item": tool},
        completed([reasoning, tool]),
    ]
    progress = []
    for sequence, value in enumerate(events):
        value["sequence_number"] = sequence
        progress.append(decoder.feed(event(value, name=value["type"])).progress)
    assert progress == [False, False, True, False, False, True, True, False, False]
    assert decoder.complete
    assert decoder.finish() == final_response([reasoning, tool])
    accepted = parse_reply("responses", encode(decoder.value))
    assert accepted["native"][0]["encrypted_content"] == "opaque-retained-value"
    assert len(accepted["calls"]) == 1 and accepted["calls"][0]["arguments"] == tool["arguments"]


def test_responses_final_snapshot_without_deltas_is_complete_not_a_progress_requirement():
    decoder = StreamDecoder("responses")
    result = decoder.feed(event(completed([message()])))
    assert result.events == 1 and not result.progress
    assert decoder.complete and decoder.value["output"][0]["content"][0]["text"] == "Source: 25 mg.\n"


def test_responses_done_duplicate_snapshot_does_not_refresh_but_new_suffix_does():
    decoder = StreamDecoder("responses")
    delta = {"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "item_id": "message", "delta": "Source"}
    done = {**delta, "type": "response.output_text.done", "text": "Source: 25 mg.\n"}
    done.pop("delta")
    assert decoder.feed(event(delta)).progress
    assert decoder.feed(event(done)).progress
    assert not decoder.feed(event(done)).progress
    decoder.feed(event(completed([message()])))
    assert decoder.finish()["output"][0] == message()


def test_responses_item_done_fallback_counts_only_unseen_text_or_arguments():
    decoder = StreamDecoder("responses")
    tool = {"id": "tool", "type": "function_call", "status": "completed", "call_id": "call", "name": "report", "arguments": "{}"}
    done = {"type": "response.output_item.done", "output_index": 0, "item": tool}
    assert decoder.feed(event(done)).progress
    assert not decoder.feed(event(done)).progress
    decoder.feed(event(completed([tool])))
    assert decoder.finish()["output"] == [tool]


def test_responses_reasoning_optional_null_content_and_additional_final_metadata():
    decoder = StreamDecoder("responses")
    reasoning = {"id": "reason", "type": "reasoning", "content": None, "summary": [], "encrypted_content": "opaque"}
    decoder.feed(event({"type": "response.output_item.done", "output_index": 0, "item": reasoning}))
    decoder.feed(event(completed([{**reasoning, "status": "completed"}, message()])))
    assert decoder.finish()["output"][0]["encrypted_content"] == "opaque"


def test_responses_text_delta_cannot_turn_into_a_function_call_at_completion():
    decoder = StreamDecoder("responses")
    decoder.feed(event({"type": "response.output_text.delta", "output_index": 0, "content_index": 0,
                        "item_id": "message", "delta": "Source"}))
    impostor = {**message("Source"), "type": "function_call", "call_id": "call", "name": "report", "arguments": "{}"}
    with pytest.raises(StreamError):
        decoder.feed(event(completed([impostor])))


def test_responses_explicit_same_sequence_is_duplicate_not_repeated_text():
    decoder = StreamDecoder("responses")
    delta = {"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "item_id": "message",
             "sequence_number": 1, "delta": "same"}
    assert decoder.feed(event(delta)).progress
    assert not decoder.feed(event(delta)).progress
    assert decoder.feed(event({**delta, "sequence_number": 2})).progress
    decoder.feed(event(completed([message("samesame")])))
    assert decoder.finish()["output"][0]["content"][0]["text"] == "samesame"


@pytest.mark.parametrize("bad", [
    {"sequence_number": 1, "delta": "changed"}, {"sequence_number": 0, "delta": "same"},
])
def test_responses_conflicting_or_backward_sequence_rejects(bad):
    decoder = StreamDecoder("responses")
    delta = {"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "item_id": "message",
             "sequence_number": 1, "delta": "same"}
    decoder.feed(event(delta))
    with pytest.raises(StreamError):
        decoder.feed(event({**delta, **bad}))


@pytest.mark.parametrize("bad_output", [[], [message("changed")], [{**message("Source"), "id": "other"}]])
def test_responses_terminal_cannot_omit_or_change_received_content(bad_output):
    decoder = StreamDecoder("responses")
    decoder.feed(event({"type": "response.output_text.delta", "output_index": 0, "content_index": 0,
                        "item_id": "message", "delta": "Source"}))
    with pytest.raises(StreamError):
        decoder.feed(event(completed(bad_output)))
    assert not decoder.complete


@pytest.mark.parametrize("kind", ["response.failed", "response.incomplete", "response.cancelled"])
def test_responses_unsuccessful_terminal_retains_native_candidate_and_safe_diagnosis(kind):
    decoder = StreamDecoder("responses")
    response = {"id": "reply", "status": kind.split(".")[1], "output": [message()], "error": {"message": "private-key"}}
    with pytest.raises(StreamError) as error:
        decoder.feed(event({"type": kind, "response": response}))
    assert "private-key" not in str(error.value)
    assert decoder.value == response and not decoder.complete and decoder.terminal == kind


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_error_after_http_success_is_not_completed_output(protocol):
    decoder = StreamDecoder(protocol)
    with pytest.raises(StreamError) as error:
        decoder.feed(event({"error": {"message": "credential must not escape"}}))
    assert decoder.terminal == "error" and not decoder.complete
    assert "credential" not in str(error.value)


@pytest.mark.parametrize("raw", [b"data: not-json\n\n", b'data: {"x":1,"x":2}\n\n', b"data: NaN\n\n",
                                  b"data: []\n\n", b"data: \xff\n\n"])
def test_malformed_framed_data_never_assembles_an_executable_reply(raw):
    decoder = StreamDecoder("chat_completions")
    with pytest.raises(StreamError):
        decoder.feed(raw)
    assert not decoder.complete and decoder.value is None


@pytest.mark.parametrize("tail", [b"", b"data: [DONE]", b"data: [DONE]\n", b"\xf0\x9f"])
def test_chat_requires_a_complete_terminal_frame_not_eof(tail):
    decoder = StreamDecoder("chat_completions")
    decoder.feed(event(chat({"content": "useful partial"}, finish="stop")) + tail)
    with pytest.raises(StreamError):
        decoder.finish()
    assert not decoder.complete and decoder.value is None


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_plain_json_is_not_silently_accepted_for_a_stream_request(protocol):
    decoder = StreamDecoder(protocol)
    decoder.feed(b'{"choices":[],"status":"completed","output":[]}')
    with pytest.raises(StreamError):
        decoder.finish()


@pytest.mark.parametrize("finish", ["length", "content_filter"])
def test_complete_chat_transport_is_distinct_from_native_acceptance(finish):
    decoder = StreamDecoder("chat_completions")
    decoder.feed(event(chat({"content": "useful partial"}, finish=finish)) + event("[DONE]"))
    assert decoder.complete and decoder.terminal == finish
    with pytest.raises(ValueError):
        parse_reply("chat_completions", encode(decoder.finish()))


@pytest.mark.parametrize("bad", [
    {"choices": [{"index": 1, "delta": {}, "finish_reason": None}]},
    {"choices": [{"index": 0, "delta": {"role": "user"}, "finish_reason": None}]},
    {"choices": [{"index": 0, "delta": {"content": []}, "finish_reason": None}]},
    {"choices": [{"index": 0, "delta": {"audio": {"data": "unknown"}}, "finish_reason": None}]},
])
def test_chat_rejects_unsupported_choice_or_content_instead_of_dropping_it(bad):
    decoder = StreamDecoder("chat_completions")
    with pytest.raises(StreamError):
        decoder.feed(event({**chat(), **bad}))


def test_incomplete_tool_indices_and_conflicting_identity_are_not_executable():
    decoder = StreamDecoder("chat_completions")
    delta = {"tool_calls": [{"index": 1, "id": "a", "type": "function", "function": {"name": "report", "arguments": "{}"}}]}
    decoder.feed(event(chat(delta, finish="tool_calls")))
    with pytest.raises(StreamError):
        decoder.feed(event("[DONE]"))
    decoder = StreamDecoder("chat_completions")
    decoder.feed(event(chat(delta)))
    different = deepcopy(delta)
    different["tool_calls"][0]["id"] = "b"
    with pytest.raises(StreamError):
        decoder.feed(event(chat(different)))


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_contradictory_data_in_same_chunk_after_terminal_is_rejected(protocol):
    decoder = StreamDecoder(protocol)
    raw = (event(chat({"content": "complete"}, finish="stop")) + event("[DONE]")) if protocol == "chat_completions" else event(completed([message()]))
    with pytest.raises(StreamError):
        decoder.feed(raw + event({"error": {"message": "late failure"}}))


def test_done_snapshot_must_not_be_changed_or_followed_by_more_deltas():
    decoder = StreamDecoder("responses")
    done = {"type": "response.output_text.done", "output_index": 0, "content_index": 0, "item_id": "message", "text": "Final"}
    decoder.feed(event(done))
    with pytest.raises(StreamError):
        decoder.feed(event({**done, "text": "Final changed"}))
    decoder = StreamDecoder("responses")
    decoder.feed(event(done))
    with pytest.raises(StreamError):
        decoder.feed(event({"type": "response.output_text.delta", "output_index": 0, "content_index": 0,
                            "item_id": "message", "delta": "more"}))
