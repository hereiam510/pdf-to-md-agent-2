"""Clock and transaction faults, without sleep or live provider requests."""
import pytest
import asyncio
import httpx
from contextlib import contextmanager

import pdfmd.active_time as module
from pdfmd.active_time import ActiveTime
from pdfmd.nexus import Nexus
from pdfmd.runtime import Runtime
from test_context_admission import protocol_job


class Clock:
    wall = 10000.0
    mono = 100.0

    def time(self):
        return self.wall

    def monotonic(self):
        return self.mono


def test_monotonic_accounting_survives_wall_jumps_and_checkpoint_retry(setup, monkeypatch):
    store, job = setup
    store.update_job(job["id"], active_seconds=17)
    clock = Clock()
    monkeypatch.setattr(module, "time", clock)
    meter = ActiveTime(store)
    meter.start(job["id"])
    clock.mono += 5
    clock.wall -= 10000
    original = store.put_tx
    def fault(*args):
        original(*args)
        raise RuntimeError("before checkpoint transaction commit")
    with monkeypatch.context() as patch:
        patch.setattr(store, "put_tx", fault)
        with pytest.raises(RuntimeError):
            meter.checkpoint()
    assert store.get("job", job["id"])["active_seconds"] == 17
    assert meter.elapsed(store.get("job", job["id"])) == 22
    meter.checkpoint()
    assert store.get("job", job["id"])["active_seconds"] == 22
    clock.mono += 3
    clock.wall += 50000
    meter.checkpoint(close=True)
    current = store.get("job", job["id"])
    assert current["active_seconds"] == 25 and "active_since" not in current
    assert not store.records("active_time_gap", job["id"])


def test_crash_tail_is_distinct_from_known_time_and_restart_is_atomic(setup, monkeypatch):
    store, job = setup
    clock = Clock()
    monkeypatch.setattr(module, "time", clock)
    first = ActiveTime(store)
    first.start(job["id"])
    clock.mono += 12
    clock.wall += 12
    first.checkpoint()
    # No close: a process dies after its last durable checkpoint.
    clock.wall += 10000
    clock.mono += 10000
    second = ActiveTime(store)
    original = store.put_tx
    def fault(db, kind, *args):
        original(db, kind, *args)
        if kind == "job":
            raise RuntimeError("gap insertion before job commit")
    with monkeypatch.context() as patch:
        patch.setattr(store, "put_tx", fault)
        with pytest.raises(RuntimeError):
            second.start(job["id"])
    assert not store.records("active_time_gap", job["id"])
    assert store.get("job", job["id"])["active_seconds"] == 12
    second.start(job["id"])
    gaps = store.records("active_time_gap", job["id"])
    assert len(gaps) == 1 and gaps[0]["wall_span_seconds"] == 10000
    assert gaps[0]["active_seconds"] is None and gaps[0]["budget_policy"] == "known_active_only"
    assert second.elapsed(store.get("job", job["id"])) == 12
    second.checkpoint(close=True)
    second.start(job["id"])
    second.checkpoint(close=True)
    assert store.records("active_time_gap", job["id"]) == gaps


def test_checkpoint_database_wait_is_retained_in_the_unmeasured_tail(setup, monkeypatch):
    store, job = setup
    clock = Clock()
    monkeypatch.setattr(module, "time", clock)
    meter = ActiveTime(store)
    meter.start(job["id"])
    clock.mono += 5
    clock.wall += 5
    observed = clock.wall
    original = store.transaction
    @contextmanager
    def delayed():
        clock.mono += 3
        clock.wall += 3
        with original() as db:
            yield db
    with monkeypatch.context() as patch:
        patch.setattr(store, "transaction", delayed)
        meter.checkpoint()
    # A crash here must not silently lose the time spent persisting that sample.
    current = store.get("job", job["id"])
    assert current["active_seconds"] == 5 and current["active_since"] == observed
    restarted = ActiveTime(store)
    restarted.start(job["id"])
    gap = store.records("active_time_gap", job["id"])[0]
    assert gap["wall_span_seconds"] == 3 and gap["active_seconds"] is None
    restarted.checkpoint(close=True)


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_http_wait_uses_monotonic_budget_and_keeps_unknown_attempt(setup, monkeypatch, protocol):
    store, job = setup
    job = protocol_job(store, job, protocol)
    store.update_job(job["id"], active_seconds=17, limits={**job["limits"], "max_active_seconds": 19})
    clock = Clock()
    monkeypatch.setattr(module, "time", clock)
    sent = []
    async def wait(request):
        sent.append(request.content)
        clock.mono += 2
        clock.wall -= 10000
        await asyncio.Future()
    runtime = Runtime(store, Nexus(store, lambda _: "fixture", httpx.MockTransport(wait)))
    try:
        runtime.run(job["id"])
    finally:
        runtime.close()
    current = store.get("job", job["id"])
    assert current["stop_reason"] == "budget_exhausted" and current["active_seconds"] == 19
    assert len(sent) == current["attempts"] == 1
    attempt = store.records("attempt", job["id"])[0]
    assert attempt["status"] == "unknown" and attempt["usage"] is None and attempt["remote_cancelled"] is None
    assert not store.records("active_time_gap", job["id"])
