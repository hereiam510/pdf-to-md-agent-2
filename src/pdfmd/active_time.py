"""Known monotonic runtime and explicitly unmeasured crash tails.

The caller owns the task execution lock. No wall-clock restart interval is
charged as work. Checkpoints and the known total move in one short transaction.
"""
from __future__ import annotations

from contextlib import contextmanager

from .clocks import Clocks, SYSTEM_CLOCKS
from .storage import Conflict, Store, uid


class ActiveTime:
    def __init__(self, store: Store, clocks: Clocks | None = None):
        self.store = store
        self.clocks = clocks or SYSTEM_CLOCKS
        self.job: str | None = None
        self.session: str | None = None
        self.mark = 0.0
        self.last_sample = (0.0, 0.0)

    def start(self, job: str) -> None:
        wall, sample, session = self.clocks.wall(), self.clocks.pair(), uid()
        with self.store.transaction() as db:
            current = self.store.get_tx(db, "job", job)
            prior = current.get("active_since")
            if prior is not None:
                gap = {"id": current.get("active_session") or uid(), "from_wall": prior,
                       "observed_wall": wall, "wall_span_seconds": wall - prior,
                       "active_seconds": None, "budget_policy": "known_active_only"}
                self.store.put_tx(db, "active_time_gap", gap["id"], job, gap)
            current.update(status="running", stop_reason=None, active_since=wall, active_session=session)
            self.store.put_tx(db, "job", job, job, current)
        self.job, self.session, self.mark = job, session, sample[0]
        self.last_sample = sample

    def elapsed(self, current: dict) -> float:
        pending = (max(0.0, self.clocks.working() - self.mark)
                   if self.session and current.get("active_session") == self.session else 0.0)
        return current["active_seconds"] + pending

    @contextmanager
    def exclude_diagnostic_time(self):
        """Measure observer latency separately from ordinary conversion work.

        The single task writer performs no ordinary work/checkpoint inside this
        interval. Failure still excludes its elapsed time; no metadata commits
        or allowance changes are made here. Crash tails retain the usual unknown
        interval semantics rather than inventing a known exclusion.
        """
        session, started = self.session, self.clocks.working()
        try:
            yield
        finally:
            if session is not None and self.session == session:
                self.mark += max(0.0, self.clocks.working() - started)

    def checkpoint(self, *, force: bool = True, close: bool = False) -> None:
        if self.session is None:
            return
        sample, wall = self.clocks.pair(), self.clocks.wall()
        working, interrupt = sample
        previous_working, previous_interrupt = self.last_sample
        suspended = (interrupt - previous_interrupt) - (working - previous_working)
        delta = max(0.0, working - self.mark)
        if not force and delta < 1.0 and suspended < 2.0:
            self.last_sample = sample
            return
        with self.store.transaction() as db:
            current = self.store.get_tx(db, "job", self.job)
            if current.get("active_session") != self.session:
                raise Conflict("The active-time owner changed during execution.")
            current["active_seconds"] += delta
            if suspended >= 2.0:
                interval = {"id": uid(), "duration_seconds": suspended, "detected_wall": wall}
                self.store.put_tx(db, "suspended_interval", interval["id"], self.job, interval)
                self.store.event_tx(db, self.job, "resumed_after_sleep", interval)
            if close:
                current.pop("active_since", None)
                current.pop("active_session", None)
            else:
                current["active_since"] = wall
            self.store.put_tx(db, "job", self.job, self.job, current)
        self.mark = working
        self.last_sample = sample
        if close:
            self.job = self.session = None
