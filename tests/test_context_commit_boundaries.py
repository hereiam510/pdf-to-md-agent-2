"""Fault boundaries distinguish saved bytes, committed dispositions and projections."""
from copy import deepcopy

import pytest

from pdfmd.nexus import StopRun
from pdfmd.storage import Store
from test_context_admission import protocol_job, state_for
from test_context_coordination import accepted_batch, coordinate, offline, settlements
from test_context_progress import read_batch
from test_runtime import tool


PROTOCOLS = ["chat_completions", "responses"]


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_staged_decision_is_not_commit_and_does_not_override_new_instructions(setup, protocol, monkeypatch):
    store, original = setup
    job = protocol_job(store, original, protocol)
    runtime = offline(store)
    state = {**state_for(job, []), "pin_views": {}}
    try:
        after, _ = accepted_batch(runtime, job, state, "staging", tool("context_update", {"notes": "Uncommitted choice"}))
        put = store.put_tx
        with monkeypatch.context() as patch:
            def crash(db, kind, key, owner, value):
                if kind == "context_commit":
                    raise RuntimeError("before metadata commit")
                return put(db, kind, key, owner, value)
            patch.setattr(store, "put_tx", crash)
            with pytest.raises(RuntimeError, match="before metadata commit"):
                coordinate(runtime, after)
        assert not settlements(store, job)
        assert not store.records("context_policy", job["id"])
        assert any(b["kind"] == "context_decision_candidate" for b in store.records("blob", job["id"]))
        original_receipt = store.bytes("result:staging:0", job["id"])
    finally:
        runtime.close()
    store = Store(store.root)
    store.update_job(job["id"], amendments=["Choose context again under this instruction."])
    runtime = offline(store)
    try:
        restored = coordinate(runtime, after)
        assert restored["notes"] == state["notes"]
        assert settlements(store, job)[-1]["feedback"]["status"] == "superseded"
        assert store.bytes("result:staging:0", job["id"]) == original_receipt
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("oversize", [False, True])
def test_committed_decision_recovers_before_new_settings_and_graph(setup, protocol, oversize, monkeypatch):
    store, original = setup
    job = protocol_job(store, original, protocol)
    runtime = offline(store)
    state = {**state_for(job, []), "pin_views": {}}
    notes = "N" * 100000 if oversize else "Committed continuity facts"
    try:
        after, _ = accepted_batch(runtime, job, state, "commit-gap", tool("context_update", {"notes": notes}))
        event = store.event_once
        with monkeypatch.context() as patch:
            def crash(owner, kind, key, data):
                if kind == "context_update_settled":
                    raise RuntimeError("after transaction before graph")
                return event(owner, kind, key, data)
            patch.setattr(store, "event_once", crash)
            with pytest.raises(RuntimeError, match="before graph"):
                coordinate(runtime, after)
        saved = deepcopy(settlements(store, job)[-1])
        assert saved["feedback"]["status"] == ("needs_agent_revision" if oversize else "applied")
        bytes0 = store.bytes("result:commit-gap:0", job["id"])
    finally:
        runtime.close()
    store = Store(store.root)
    store.update_job(job["id"], amendments=["New instruction after commit"], attempts=5, active_seconds=18,
                     route={**job["route"], "context_tokens": 500000 if oversize else 4096})
    runtime = offline(store)
    try:
        restored = coordinate(runtime, after)
        assert restored["notes"] == (state["notes"] if oversize else notes)
        assert restored["context_waiting"] is None
        assert coordinate(runtime, after)["notes"] == restored["notes"]
        assert settlements(store, job) == [saved]
        assert len([e for e in store.events(job["id"]) if e["type"] == "context_update_settled"]) == 1
        assert store.bytes("result:commit-gap:0", job["id"]) == bytes0
        assert store.get("job", job["id"])["attempts"] == 5
        assert store.get("job", job["id"])["active_seconds"] == 18
    finally:
        runtime.close()


@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_fitting_compaction_does_not_create_reachable_required_diagnostic(setup, protocol):
    store, original = setup
    job = protocol_job(store, original, protocol)
    state = {**state_for(job, []), "notes": "A" * 10000, "pin_views": {}}
    read_batch(store, job, "history", ["Useful original " * 300])
    state["history"] = ["history"]
    runtime = offline(store)
    try:
        after, _ = accepted_batch(runtime, job, state, "large", tool("context_update", {"notes": "Q" * 80000}))
        job = store.update_job(job["id"], route={**job["route"], "context_tokens": 17000})
        decided = coordinate(runtime, after)
        assert settlements(store, job)[-1]["feedback"]["status"] == "needs_agent_revision"
        assert not runtime.context.required(job, decided)["fits"]
        _, meta = runtime.context.compact_request(job, decided)
        assert meta["capacity"]["fits"]  # Different purpose, actually executable envelope.
        with pytest.raises(StopRun) as error:
            runtime.prepare(decided)
        assert error.value.reason == "feedback_capacity_blocked"
        assert store.get("job", job["id"])["attempts"] == 0
        assert decided["notes"] == state["notes"]
        assert store.json(decided["context_check"], job["id"])["reason"] == "feedback_capacity_blocked"
    finally:
        runtime.close()
