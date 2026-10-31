"""Bounded public receive values. This projection never rewrites raw evidence."""
import math

TERMINALS = {"stop", "tool_calls", "length", "content_filter", "function_call", "unsupported_finish", "error",
             "response.completed", "response.failed", "response.incomplete", "response.cancelled"}
CAUSES = {"complete", "stream_error", "stream_incomplete", "request_deadline", "first_progress_timeout",
          "progress_idle_timeout", "total_deadline", "connect_timeout", "read_timeout", "write_timeout",
          "pool_timeout", "transport_timeout", "transport_error", "http_error", "user_stop", "active_time_limit", "local_stop"}
CATEGORIES = {"invalid_stream", "identity_type", "identity_conflict", "competing_content", "content_conflict", "unsupported_content", "unsupported_event", "refusal", "provider_error"}
FIELDS = {"event", "id", "model", "created", "response", "item", "part", "summary", "choice"}

def safe_receive(observed):
    result = {}
    for key, allowed in (("mode", {"streaming_progress", "legacy_total"}), ("stop_cause", CAUSES), ("terminal_event", TERMINALS)):
        value = observed.get(key)
        if key in observed:
            result[key] = value if value is None or (isinstance(value, str) and value in allowed) else "unsupported"
    for key in ("settled", "protocol_complete"):
        if type(observed.get(key)) is bool:
            result[key] = observed[key]
    for key in ("headers_elapsed_seconds", "first_body_elapsed_seconds", "last_body_elapsed_seconds",
                "first_progress_elapsed_seconds", "last_progress_elapsed_seconds", "received_body_bytes", "event_count", "progress_count"):
        value = observed.get(key)
        if value is None:
            if key in observed:
                result[key] = None
        elif type(value) in (int, float) and 0 <= value <= 10**15 and math.isfinite(value):
            result[key] = value
    status = observed.get("http_status")
    result["http_status"] = status if type(status) is int and 100 <= status <= 599 else None
    diagnostic = observed.get("diagnostic")
    if isinstance(diagnostic, dict):
        result["diagnostic"] = {
            "category": diagnostic.get("category") if isinstance(diagnostic.get("category"), str) and diagnostic["category"] in CATEGORIES else "invalid_stream",
            "field": diagnostic.get("field") if isinstance(diagnostic.get("field"), str) and diagnostic["field"] in FIELDS else "event",
            "stage": diagnostic.get("stage") if isinstance(diagnostic.get("stage"), str) and diagnostic["stage"] in {"decode", "finish", "native"} else "decode",
            "ordinal": diagnostic.get("ordinal") if type(diagnostic.get("ordinal")) is int and 0 <= diagnostic["ordinal"] <= 10**9 else None}
    return result
