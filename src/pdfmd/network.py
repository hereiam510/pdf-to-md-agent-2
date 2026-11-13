"""Failure classification and persisted deadlines for the Nexus send gate."""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import math
import re
import ssl
from urllib.parse import urlsplit

import httpx


TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})
NETWORK_PAUSES = frozenset({"network_retry_exhausted", "network_retry_disabled", "retry_wait_exceeds_limit"})
RETRY_POLICY_FIELDS = ("automatic_retry", "max_attempts_per_request", "max_server_wait_seconds")
BACKOFF = {"backoff_initial_seconds": 2, "backoff_max_seconds": 60}
DIAGNOSTIC_BYTES = 16 * 1024
DIAGNOSTIC_SECONDS = 5
UPSTREAM_CODES = frozenset({
    "authentication_error", "invalid_api_key", "invalid_request_error", "permission_denied",
    "model_not_found", "rate_limit_exceeded", "insufficient_quota", "server_error",
    "service_unavailable", "overloaded_error", "context_length_exceeded",
})


def legacy_policy(job: dict) -> dict:
    limits = job["limits"]
    return job.get("legacy_replay_policy") or {"replay_unknown": limits.get("replay_unknown", False),
                                              "max_attempts_per_request": limits.get("max_attempts_per_request", 1)}


def caused_by(error, kind) -> bool:
    visited = set()
    while error is not None and id(error) not in visited:
        if isinstance(error, kind):
            return True
        visited.add(id(error))
        error = error.__cause__ or (None if error.__suppress_context__ else error.__context__)
    return False


def classify_transport(error, endpoint: str, send_evidence: str) -> tuple[str, str, str]:
    if send_evidence == "response_observed":
        return "lost_after_send", send_evidence, ""
    if isinstance(error, httpx.ConnectError) and caused_by(error, ssl.SSLCertVerificationError):
        return "configuration", "not_sent", "Nexus TLS certificate verification failed."
    if isinstance(error, (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)):
        url = urlsplit(endpoint)
        refused = isinstance(error, httpx.ConnectError) and caused_by(error, ConnectionRefusedError)
        if refused and url.hostname in {"localhost", "127.0.0.1", "::1"}:
            port = url.port or (443 if url.scheme == "https" else 80)
            host = "[::1]" if url.hostname == "::1" else url.hostname
            return "unsent", "not_sent", f"Nexus proxy not reachable at {host}:{port}."
        return "unsent", "not_sent", "Could not establish a connection to Nexus."
    return "lost_after_send", send_evidence, ""


def _http_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        result = parsedate_to_datetime(value)
        return result if result.tzinfo is not None else result.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None


def retry_after(headers: httpx.Headers, wall: float) -> float | None:
    value = headers.get("retry-after", "").strip()
    if re.fullmatch(r"[0-9]+", value):
        delay = float(value)
        # Keep oversized delay-seconds pending beyond any representable
        # operating-system clock interval without writing a nonfinite number.
        return min(delay, 1e300)
    target = _http_date(value)
    if target is None:
        return None
    origin = _http_date(headers.get("date"))
    if origin:
        return max(0.0, (target - origin).total_seconds())
    return max(0.0, target.timestamp() - wall)


def upstream_code(body: bytes) -> str:
    try:
        value = json.loads(body)
    except (ValueError, RecursionError):
        return "unavailable"
    if isinstance(value, dict):
        error = value.get("error", value)
        if isinstance(error, dict):
            for field in ("code", "type"):
                candidate = error.get(field)
                if isinstance(candidate, str) and candidate in UPSTREAM_CODES:
                    return candidate
    return "unrecognized"


def deadline(clocks, delay: float) -> dict:
    interrupt = clocks.interrupt()
    clock_basis = {"delay_seconds": delay, "process_basis": clocks.process_basis, "started_interrupt": interrupt,
                   "due_interrupt": interrupt + delay, "due_monotonic": clocks.monotonic() + delay,
                   "due_wall": clocks.wall() + delay}
    return {**clock_basis, "boot_identity": clocks.boot_identity}


def remaining(clocks, record: dict) -> tuple[float, dict]:
    if record.get("process_basis") == clocks.process_basis and _valid(record.get("due_monotonic")):
        return max(0.0, record["due_monotonic"] - clocks.monotonic()), record
    boot = clocks.boot_identity
    interrupt = clocks.interrupt()
    if (boot and boot == record.get("boot_identity") and _valid(record.get("due_interrupt"))
            and _valid(record.get("started_interrupt")) and record["started_interrupt"] <= interrupt):
        return max(0.0, record["due_interrupt"] - interrupt), record
    renewed = {**record, **deadline(clocks, record["delay_seconds"])}
    return renewed["delay_seconds"], renewed


def _valid(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def retry_available(record: dict) -> str:
    try:
        return datetime.fromtimestamp(record["due_wall"]).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    except (OverflowError, OSError, ValueError):
        return "the server cooldown deadline (outside the supported calendar)"
