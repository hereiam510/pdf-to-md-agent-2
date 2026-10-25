import json

import httpx
import pytest

from pdfmd.nexus import Nexus, StopRun, parse_reply
from pdfmd.runtime import Runtime


def response(*calls, text=None):
    return {"id": "fixture-reply", "choices": [{"finish_reason": "tool_calls" if calls else "stop",
            "message": {"role": "assistant", "content": text, "tool_calls": list(calls)}}], "usage": {"prompt_tokens": 100, "completion_tokens": 50}}


def tool(name, arguments, key="call"):
    return {"id": key, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}


def transport_for(store, job, seen):
    def serve(request):
        payload = json.loads(request.content)
        seen.append(payload)
        if len(seen) == 1:
            value = response(tool("inspect_pdf", {"pages": [1], "mode": "text"}))
        elif len(seen) == 2:
            tools = [m for m in payload["messages"] if m["role"] == "tool"]
            text = json.loads(tools[-1]["content"])["data"]["value"]["pages"][0]["content"]
            value = response(tool("edit_document", {"base_version": None, "expected_head": None,
                              "replace_blocks": [{"id": "section", "pages": [1], "markdown": text}],
                              "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "complete"}))
        else:
            value = response(tool("report", {"state": "complete", "message": "Saved the synthetic section.", "version_id": store.get("job", job)["head"]}))
        return httpx.Response(200, json=value)
    return httpx.MockTransport(serve)


def test_autonomous_loop_complete_tool_only_responses_and_restart_gap(setup, monkeypatch):
    store, job = setup
    seen = []
    service = Nexus(store, lambda _: "offline-key", transport_for(store, job["id"], seen))
    runtime = Runtime(store, service)
    execute = runtime.dispatcher.execute
    injected = []

    def fault(*args, **kwargs):
        result = execute(*args, **kwargs)
        if args[2] == "edit_document" and not injected:
            injected.append(True)
            raise RuntimeError("injected gap after commit before graph checkpoint")
        return result

    monkeypatch.setattr(runtime.dispatcher, "execute", fault)
    with pytest.raises(RuntimeError):
        runtime.run(job["id"])
    version = store.get("job", job["id"])["head"]
    assert version and len(seen) == 2
    runtime.close()
    resumed = Runtime(store, service)
    resumed.run(job["id"])
    resumed.close()
    current = store.get("job", job["id"])
    assert current["status"] == "completed" and current["delivery"] == version
    assert current["attempts"] == 3 and len(seen) == 3
    assert len(store.records("version", job["id"])) == 1


def test_attempt_budget_survives_resume_without_extra_send(setup):
    store, job = setup
    store.update_job(job["id"], limits={**job["limits"], "max_requests": 1})
    seen = []
    service = Nexus(store, lambda _: "key", transport_for(store, job["id"], seen))
    for _ in range(2):
        runtime = Runtime(store, service)
        runtime.run(job["id"])
        runtime.close()
    assert len(seen) == 1
    assert store.get("job", job["id"])["stop_reason"] == "budget_exhausted"
    assert store.get("job", job["id"])["attempts"] == 1


def test_rejected_native_reply_is_retained_and_not_executed(setup):
    store, job = setup
    broken = response(tool("edit_document", {}))
    broken["choices"][0]["finish_reason"] = "length"
    service = Nexus(store, lambda _: "key", httpx.MockTransport(lambda _: httpx.Response(200, json=broken)))
    runtime = Runtime(store, service)
    runtime.run(job["id"])
    runtime.close()
    assert store.get("job", job["id"])["stop_reason"] == "response_rejected"
    assert not store.records("operation", job["id"])
    assert any(b["kind"] == "native_response" for b in store.records("blob", job["id"]))


def test_responses_native_reasoning_and_duplicate_json_boundary():
    native = {"status": "completed", "output": [
        {"type": "reasoning", "encrypted_content": "opaque", "summary": []},
        {"type": "function_call", "call_id": "a", "name": "inspect_pdf", "arguments": "{}", "status": "completed"}]}
    accepted = parse_reply("responses", json.dumps(native).encode())
    assert accepted["native"][0]["encrypted_content"] == "opaque"
    native["output"][1]["arguments"] = '{"page":1,"page":2}'
    with pytest.raises(ValueError, match="Duplicate"):
        parse_reply("responses", json.dumps(native).encode())


@pytest.mark.parametrize("shape", ["missing", "null", "empty"])
def test_chat_text_reply_accepts_absent_tool_calls_without_rewriting_native(shape):
    value = response(text="Preserve this exact handoff: 25 mg.")
    message = value["choices"][0]["message"]
    if shape == "missing":
        message.pop("tool_calls")
    elif shape == "null":
        message["tool_calls"] = None
    accepted = parse_reply("chat_completions", json.dumps(value).encode())
    assert accepted["calls"] == []
    assert accepted["text"] == message["content"]
    assert accepted["native"] == [message]


@pytest.mark.parametrize("calls", ["", {}, 0, False])
def test_chat_nonlist_tool_calls_are_not_mistaken_for_no_calls(calls):
    value = response(text="Do not accept a malformed call container.")
    value["choices"][0]["message"]["tool_calls"] = calls
    with pytest.raises(ValueError, match="tool_calls"):
        parse_reply("chat_completions", json.dumps(value).encode())


def test_text_only_native_history_does_not_hide_undelivered_context_outcome():
    from pdfmd.context import Context
    message = {"role": "assistant", "content": "Continuing.", "tool_calls": None}
    assert not Context.outcome_in_groups([[message]], {"status": "needs_agent_revision"})
    assert message["tool_calls"] is None


def test_saved_accepted_reply_recovers_before_request_pointer_commit(setup, monkeypatch):
    store, job = setup
    calls = []
    service = Nexus(store, lambda _: "key", httpx.MockTransport(lambda req: calls.append(req) or httpx.Response(200, json=response(text="Saved reply"))))
    service.freeze(job["id"], "gap", {"model": "fixture", "messages": []}, "normal", {})
    original = store.put
    injected = []

    def fail_pointer(kind, key, owner, value):
        if kind == "request" and value["status"] == "accepted" and not injected:
            injected.append(True)
            raise RuntimeError("injected pointer gap")
        return original(kind, key, owner, value)

    monkeypatch.setattr(store, "put", fail_pointer)
    with pytest.raises(RuntimeError):
        service.send(job["id"], "gap")
    assert service.send(job["id"], "gap")["text"] == "Saved reply"
    assert len(calls) == 1 and store.get("job", job["id"])["attempts"] == 1
    assert store.records("attempt", job["id"])[0]["status"] == "accepted"


def test_responses_loop_preserves_reasoning_and_pairs_tool_output(setup):
    store, job = setup
    route = {**job["route"], "protocol": "responses", "endpoint": "http://127.0.0.1:8317/v1/responses"}
    store.update_job(job["id"], route=route)
    payloads = []

    def reply(request):
        payload = json.loads(request.content)
        payloads.append(payload)
        if len(payloads) == 1:
            output = [{"type": "reasoning", "encrypted_content": "opaque-native", "summary": []},
                      {"type": "function_call", "name": "inspect_pdf", "call_id": "r1", "arguments": '{"pages":[1]}', "status": "completed"}]
        else:
            assert payload["input"][1]["encrypted_content"] == "opaque-native"
            assert payload["input"][3]["type"] == "function_call_output"
            assert payload["input"][3]["call_id"] == "r1"
            output = [{"type": "function_call", "call_id": "r2", "name": "report", "status": "completed",
                       "arguments": json.dumps({"state": "waiting", "message": "Which source section is intended?"})}]
        return httpx.Response(200, json={"status": "completed", "output": output})

    runtime = Runtime(store, Nexus(store, lambda _: "key", httpx.MockTransport(reply)))
    runtime.run(job["id"])
    runtime.close()
    assert len(payloads) == 2 and store.get("job", job["id"])["status"] == "waiting"


def test_cancelled_pending_batch_does_not_dispatch_next_tool(setup):
    store, job = setup
    network = []
    value = response(tool("inspect_pdf", {"pages": [1]}, "one"), tool("inspect_pdf", {"pages": [1], "mode": "words"}, "two"))
    service = Nexus(store, lambda _: "key", httpx.MockTransport(lambda request: network.append(request) or httpx.Response(200, json=value)))
    runtime = Runtime(store, service)
    execute = runtime.dispatcher.execute

    def cancel_after_first(*args):
        result = execute(*args)
        store.update_job(job["id"], cancel_requested=True)
        return result

    runtime.dispatcher.execute = cancel_after_first
    runtime.run(job["id"])
    runtime.close()
    assert store.get("job", job["id"])["status"] == "cancelled"
    assert len(store.records("operation", job["id"])) == 1
    assert len(network) == 1
