"""Known monotonic runtime and explicitly unmeasured crash tails.

The caller owns the task execution lock. No wall-clock restart interval is
charged as work. Checkpoints and the known total move in one short transaction.
"""
from __future__ import annotations

import time

from .storage import Conflict, Store, uid


class ActiveTime:
    def __init__(self, store: Store):
        self.store = store
        self.job: str | None = None
        self.session: str | None = None
        self.mark = 0.0

    def start(self, job: str) -> None:
        wall, monotonic, session = time.time(), time.monotonic(), uid()
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
        self.job, self.session, self.mark = job, session, monotonic

    def elapsed(self, current: dict) -> float:
        pending = (max(0.0, time.monotonic() - self.mark)
                   if self.session and current.get("active_session") == self.session else 0.0)
        return current["active_seconds"] + pending

    def checkpoint(self, *, force: bool = True, close: bool = False) -> None:
        if self.session is None:
            return
        monotonic, wall = time.monotonic(), time.time()
        delta = max(0.0, monotonic - self.mark)
        if not force and delta < 1.0:
            return
        with self.store.transaction() as db:
            current = self.store.get_tx(db, "job", self.job)
            if current.get("active_session") != self.session:
                raise Conflict("The active-time owner changed during execution.")
            current["active_seconds"] += delta
            if close:
                current.pop("active_since", None)
                current.pop("active_session", None)
            else:
                current["active_since"] = wall
            self.store.put_tx(db, "job", self.job, self.job, current)
        self.mark = monotonic
        if close:
            self.job = self.session = None
