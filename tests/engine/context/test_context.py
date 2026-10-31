import json
import random

import pytest

from pdfmd.context import Context, estimate
from pdfmd.nexus import Nexus, StopRun
from pdfmd.schema import Route
from pdfmd.tools import Dispatcher


def history(store, job, key, text, *, extra_texts=()):
    calls = [{"id": f"{key}-{i}", "name": "inspect_pdf", "arguments": "{}"} for i in range(1 + len(extra_texts))]
    native = [{"role": "assistant", "content": None, "tool_calls": [
        {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}} for c in calls]}]
    accepted = store.blob(job, "accepted_response", {"native": native, "calls": calls, "text": ""})
    results = []
    for i, value in enumerate([text, *extra_texts]):
        result = store.blob(job, "tool_result", {"value": value, "coverage": {"page": 1}, "warnings": ["Derived extraction."]})
        candidate = store.blob(job, "candidate", b"{}")
        store.put("operation", f"{key}:{i}", job, {"status": "done", "result_ref": result["ref"], "candidate_ref": candidate["ref"]})
        results.append((result, candidate))
    store.put("request", key, job, {"accepted_ref": accepted["ref"]})
    return results[0]


def test_rolling_handoff_preserves_uncovered_history_and_originals(setup):
    store, job = setup
    context = Context(store, Dispatcher(store))
    source, _ = history(store, job["id"], "old", "original\u03bc" * 14000, extra_texts=["a" * 30000, "b" * 30000])
    history(store, job["id"], "tail", "recent fact" * 5300)
    state = {"job": job["id"], "seq": 0, "history": ["old", "tail"], "revision": 2, "released": [], "pinned": [], "notes": "Cross-page dependency remains unresolved.", "handoff": None}
    assert not context.normal(job, state)[1]["fits"]
    payload, meta = context.compact_request(job, state)
    assert estimate(payload, Route.model_validate(job["route"]))["fits"]
    text = json.dumps({"task": job["scope"], "current_state": "No saved version yet.", "unfinished_work": ["Read deferred extraction before completing."],
                       "dependencies": [state["notes"]], "references": [source["ref"]], "cautions": ["The large original was not read in this request."]})
    changed = context.apply_handoff(job, state, text, meta, "compact")
    assert changed["history"] == state["history"][len(meta["covered"]):]
    assert meta["covered"] == ["old"] and changed["history"] == ["tail"]
    assert store.json(source["ref"], job["id"])["value"] == "original\u03bc" * 14000
    assert context.normal(job, changed)[1]["input_estimate"] < context.normal(job, state)[1]["input_estimate"]
    assert state["history"] == ["old", "tail"]
    assert state["notes"] == changed["notes"]
    with pytest.raises(ValueError):
        context.apply_handoff(job, state, "{}", meta, "bad")
    assert state["handoff"] is None


def test_unknown_image_cost_and_truly_oversized_pins_block_without_erasing(setup):
    store, job = setup
    route = Route.model_validate({**job["route"], "vision": True, "image_tokens": None})
    with pytest.raises(StopRun, match="per-image"):
        estimate({"model": route.model, "messages": [{"content": [{"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}}]}]}, route)
    original = "".join(random.Random("unfit-pin").choices("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=100000))
    result, _ = history(store, job["id"], "old", original)
    state = {"history": ["old"], "revision": 1, "released": [], "pinned": [result["ref"]], "notes": "", "handoff": None}
    with pytest.raises(StopRun) as failure:
        Context(store, Dispatcher(store)).compact_request(job, state)
    assert failure.value.reason == "capacity_blocked"
    assert store.json(result["ref"], job["id"])["value"] == original
