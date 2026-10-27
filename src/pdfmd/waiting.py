"""Elapsed-time decisions; transport bytes never imply generation progress."""
from __future__ import annotations

from .schema import Route


class RequestWait:
    def __init__(self, route: Route):
        self.policy = route.wait_policy
        self.total = self.policy.total_seconds if self.policy else route.timeout_seconds
        self.first_progress: float | None = None
        self.last_progress: float | None = None

    def boundary(self) -> tuple[float, str]:
        deadlines = []
        if self.total is not None:
            deadlines.append((self.total, "total_deadline" if self.policy else "request_deadline"))
        if self.policy:
            deadlines.append((self.policy.first_progress_seconds, "first_progress_timeout")
                             if self.last_progress is None else
                             (self.last_progress + self.policy.idle_progress_seconds, "progress_idle_timeout"))
        return min(deadlines)

    def expired(self, elapsed: float) -> str | None:
        deadline, cause = self.boundary()
        return cause if elapsed >= deadline else None

    def progress(self, elapsed: float) -> None:
        # The receiver must check expiry before accepting a late delta as progress.
        if self.expired(elapsed):
            raise ValueError("A late event cannot revive an expired request.")
        if self.first_progress is None:
            self.first_progress = elapsed
        self.last_progress = elapsed
