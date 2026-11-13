"""Frozen native requests, complete replies, and a single durable send gate."""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json
from hashlib import sha256
from random import uniform
import time
from typing import Callable

import httpx

from .clocks import SYSTEM_CLOCKS
from . import network
from .schema import Limits, Route
from .storage import Conflict, Store, encode, uid
from .streaming import StreamDecoder, StreamError, validate_response_item_state
from .waiting import RequestWait
from .usage import interpret_usage


class StopRun(RuntimeError):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason


def instruction_basis(job: dict) -> str:
    """Only human amendments invalidate an unstarted accepted plan; tool writes do not."""
    return sha256(encode(job["amendments"])).hexdigest()


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON keys are not executable.")
        value[key] = item
    return value


def parse_reply(protocol: str, raw: bytes) -> dict:
    try:
        return _parse_reply(protocol, raw)
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise ValueError("The native response contains an unsupported container or missing field. The original is retained.") from exc


def _parse_reply(protocol: str, raw: bytes) -> dict:
    if protocol not in {"chat_completions", "responses"}:
        raise ValueError("Unsupported native protocol.")
    def finite(_):
        raise ValueError("Non-finite JSON numbers are not supported.")
    value = json.loads(raw, object_pairs_hook=unique_object, parse_constant=finite)
    if not isinstance(value, dict):
        raise ValueError("The native response must be an object.")
    calls = []
    texts = []
    if protocol == "chat_completions":
        choices = value.get("choices", [])
        if len(choices) != 1 or choices[0].get("finish_reason") not in {"stop", "tool_calls"}:
            raise ValueError("The response has no single complete accepted choice.")
        message = choices[0]["message"]
        if message.get("refusal") or message.get("role") != "assistant":
            raise ValueError("The model refused or returned an unexpected message role.")
        if any(message.get(key) not in (None, "", [], {}) for key in ("audio", "function_call")):
            raise ValueError("Unsupported native assistant content. The original is retained.")
        content = message.get("content")
        if isinstance(content, str):
            texts.append(content)
        elif content is not None:
            raise ValueError("This route returned an unsupported assistant content format. The original is retained.")
        native = [message]
        native_calls = message.get("tool_calls")
        if native_calls is None:
            native_calls = []
        if not isinstance(native_calls, list):
            raise ValueError("The assistant tool_calls field must be an array or null.")
        for call in native_calls:
            if call.get("type") != "function":
                raise ValueError("Only complete function tool calls can be executed.")
            calls.append({"id": call["id"], "name": call["function"]["name"], "arguments": call["function"]["arguments"]})
    else:
        if value.get("status") != "completed" or value.get("error") or value.get("incomplete_details"):
            raise ValueError("The native response is incomplete, failed, or refused.")
        native = value.get("output", [])
        if not isinstance(native, list):
            raise ValueError("The response output must be a list of native items.")
        item_ids = set()
        for item in native:
            if not isinstance(item, dict):
                raise ValueError("Native output items must be objects.")
            if "id" in item:
                if not isinstance(item["id"], str) or not item["id"] or item["id"] in item_ids:
                    raise ValueError("Native output item IDs must be nonempty and unique when present.")
                item_ids.add(item["id"])
            validate_response_item_state(item, final=True, stage="native")
            if item.get("type") == "function_call":
                calls.append({"id": item["call_id"], "name": item["name"], "arguments": item["arguments"]})
            elif item.get("type") == "message":
                parts = item.get("content", [])
                if not isinstance(parts, list):
                    raise ValueError("Native message content must be a list.")
                for part in parts:
                    if part.get("type") == "refusal":
                        raise ValueError("The model refused the request.")
                    if part.get("type") == "output_text":
                        if not isinstance(part.get("text"), str):
                            raise ValueError("Native output text must be a string.")
                        texts.append(part["text"])
                    else:
                        raise ValueError("Unsupported native message content. The original is retained.")
            elif item.get("type") == "reasoning":
                content, summary = item.get("content"), item.get("summary")
                if (content is not None and not isinstance(content, list)) or (summary is not None and not isinstance(summary, list)):
                    raise ValueError("Native reasoning content and summary must be lists or null.")
                for part in content or []:
                    if not isinstance(part, dict) or part.get("type") != "reasoning_text" or not isinstance(part.get("text"), str):
                        raise ValueError("Unsupported native reasoning content. The original is retained.")
                for part in summary or []:
                    if not isinstance(part, dict) or part.get("type") != "summary_text" or not isinstance(part.get("text"), str):
                        raise ValueError("Unsupported native reasoning summary. The original is retained.")
                if item.get("encrypted_content") is not None and not isinstance(item["encrypted_content"], str):
                    raise ValueError("Opaque reasoning must retain its native string representation.")
            elif item.get("type") != "reasoning":
                raise ValueError("Unsupported native output item. The original is retained; no tools were executed.")
    ids = set()
    for call in calls:
        if not isinstance(call["id"], str) or not call["id"] or call["id"] in ids:
            raise ValueError("Tool call IDs must be nonempty and unique in the accepted batch.")
        ids.add(call["id"])
        if not isinstance(call["arguments"], str) or not isinstance(call["name"], str) or not call["name"]:
            raise ValueError("Tool names and complete argument strings are required.")
        arguments = json.loads(call["arguments"], object_pairs_hook=unique_object, parse_constant=finite)
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be a complete JSON object.")
    if not calls and not any(text.strip() for text in texts):
        raise ValueError("The accepted response contains neither executable calls nor text.")
    return {"native": native, "calls": calls, "text": "\n".join(texts),
            "usage": interpret_usage(protocol, value.get("usage")).value, "provider_id": value.get("id")}


def make_payload(route: Route, instructions: str, messages: list[dict], tools: list[dict]) -> dict:
    common = {"model": route.model, "stream": route.wait_policy is not None, **deepcopy(route.parameters)}
    if route.protocol == "chat_completions":
        common.update({"messages": [{"role": "system", "content": instructions}, *messages],
                       "max_completion_tokens": route.output_tokens})
        if tools:
            common["tools"] = [{"type": "function", "function": tool} for tool in tools]
        if route.wait_policy is not None:
            common["stream_options"] = {"include_usage": True}
    else:
        common.update({"instructions": instructions, "input": messages, "store": False,
                       "max_output_tokens": route.output_tokens,
                       "include": ["reasoning.encrypted_content"]})
        if tools:
            common["tools"] = [{"type": "function", **tool, "strict": False} for tool in tools]
    return common


class Nexus:
    def __init__(self, store: Store, credentials: Callable[[str], str], transport=None, *,
                 clock=None, clocks=None, retry_sleep=None, jitter=None):
        self.store, self.credentials, self.transport = store, credentials, transport
        self.active_time = None
        self.usage_trial = None
        self.clocks = clocks or SYSTEM_CLOCKS
        self.clock = clock or self.clocks.working
        self.retry_sleep = retry_sleep or time.sleep
        self.jitter = jitter or uniform

    def freeze(self, job: str, key: str, payload: dict, kind: str, meta: dict, *, not_before=None) -> dict:
        old = self.store.maybe("request", key)
        if old:
            # Re-entry never rebuilds or alters a frozen request.
            return old
        current = self.store.get("job", job)
        route = current["route"]
        if meta.get("capacity", {}).get("anchor"):
            meta = {**meta, "admission_version": meta["capacity"]["anchor"]["version"]}
        blob = self.store.blob(job, "request_input", payload, {"kind": kind, "request": key})
        limits = Limits.model_validate(current["limits"]).model_dump()
        record = {"id": key, "job": job, "kind": kind, "payload_ref": blob["ref"],
                  "route": route, "meta": meta, "instruction_basis": instruction_basis(current),
                  "replay_policy": {**{field: limits[field] for field in network.RETRY_POLICY_FIELDS}, **network.BACKOFF},
                  "status": "prepared", "attempts": [], "accepted_ref": None}
        if not_before is not None:
            record["not_before"] = not_before
        trial_identity = self.usage_trial.preflight(record, freezing=True) if self.usage_trial else None
        prohibition = None
        with self.store.transaction() as db:
            current_request = self.store.get_tx(db, "request", key, job=job)
            if current_request:
                return current_request
            if self.usage_trial is not None:
                prohibition = self.usage_trial.freeze_tx(db, record, trial_identity)
            if prohibition:
                self.usage_trial.prohibit_tx(db, record, "before_freeze", prohibition)
            else:
                self.store.put_tx(db, "request", key, job, record)
        if prohibition:
            raise StopRun("usage_trial_revoked_before_freeze", "Trial authority changed before freeze: " + prohibition)
        capacity = meta.get("capacity", {})
        self.store.event(job, "request_prepared", {"request": key, "kind": kind,
            **{field: capacity[field] for field in ("input_estimate", "output_reserve", "fits", "method", "anchor") if field in capacity}})
        return record

    def reconcile(self, job: str, key: str) -> dict:
        """Recover locally accepted bytes without sending anything."""
        request = self.store.get("request", key, job=job)
        staged = self.store.maybe("blob", f"accepted:{key}")
        if request["accepted_ref"] or staged:
            return self._settle_accepted(job, key)
        if request["status"] == "accepted":
            raise Conflict("Accepted request has no saved acceptance evidence.")
        return request

    def trial_for(self, request):
        anchor = request.get("meta", {}).get("capacity", {}).get("anchor")
        if not anchor and (request.get("meta", {}).get("admission_version")
                           or request.get("meta", {}).get("capacity", {}).get("governing_method") == "usage_anchor"):
            raise Conflict("Anchor-capable input is missing its required governing provenance.")
        if not anchor or anchor.get("method") != "usage_anchor":
            return None
        if self.usage_trial is not None and self.usage_trial.lineage == anchor["lineage"]:
            return self.usage_trial
        # Settlement must preserve its durable authority even when a resumed
        # Runtime omitted the optional coordinator. This grants no dispatch.
        from .usage_trial import OfflineUsageTrial
        return OfflineUsageTrial(self.store, anchor["lineage"])

    def _settle_accepted(self, job: str, key: str, *, verified_stream: dict | None = None) -> dict:
        """Validate immutable evidence, then atomically merge current metadata.

        Only a freshly archived complete stream from this send can reuse its
        disk reconstruction and receive-boundary check. Reopen repeats both.
        No file reads/decoder work occurs while holding the write transaction.
        """
        from .acceptance import EvidenceCheckError, inspect_acceptance, validate_metadata
        try:
            checked = inspect_acceptance(self.store, job, key, verified_stream=verified_stream)
        except EvidenceCheckError as exc:
            raise StopRun("accepted_evidence_conflict",
                          "Saved acceptance is incompatible or inconsistent with retained native evidence. "
                          "Original records, consumption and tool facts are retained; no request was sent.") from exc
        request, ref, evidence = checked["request"], checked["ref"], checked["evidence"]
        accepted, native = checked["accepted"], checked["native"]
        attempt_id, received_at = checked["attempt_id"], checked["received_at"]
        streaming, stream_ref = checked["streaming"], checked["stream_ref"]
        receipt, observed = checked["receipt"], checked["observed"]
        if checked["boundary"]["status"] != "compatible":
            raise StopRun("accepted_evidence_conflict",
                          "Saved acceptance conflicts with its received stream: " + checked["boundary"]["reason"]
                          + " All evidence and committed tool effects are retained; no request was sent.")

        trial = self.trial_for(request)
        raw_usage = self.store.json(native["ref"], job).get("usage") if trial else None
        with self.store.transaction() as db:
            current = self.store.get_tx(db, "request", key, job=job)
            attempt = self.store.get_tx(db, "attempt", attempt_id, job=job)
            validate_metadata(current, attempt, job, key, attempt_id, ref, accepted,
                              native, stream_ref, observed, original=request)
            # Recheck the frozen identity and validated catalog descriptors, not
            # stale whole-record copies. Preserve unrelated current fields.
            for field in ("kind", "payload_ref", "route", "instruction_basis", "replay_policy", "attempts"):
                if current.get(field) != request.get(field):
                    raise Conflict("Request identity changed during acceptance validation.")
            for reference, record in evidence.items():
                if self.store.get_tx(db, "blob", reference, job=job) != record:
                    raise Conflict("Accepted evidence changed during validation.")
            if streaming and self.store.get_tx(db, "stream_receive", attempt_id, job=job) != receipt:
                raise Conflict("Accepted stream observation changed during validation.")
            desired = {"response_ref": native["ref"], **({"stream_ref": stream_ref} if streaming else {})}
            finished = attempt.get("finished")
            updated_attempt = {**attempt, "status": "accepted", "usage": accepted["usage"],
                               "finished": received_at if finished is None else finished}
            updated_attempt["send_evidence"] = "response_observed"
            updated_attempt.setdefault("remote_cancelled", None)
            if streaming:
                updated_attempt["stream_ref"] = stream_ref
            if observed is not None:
                http_status = observed.get("http_status")
                transport = {k: v for k, v in observed.items() if k != "http_status"}
                old_transport = attempt.get("transport", {})
                updated_attempt.update(http_status=http_status, transport={**old_transport, **transport})
            updated_request = {**current, "status": "accepted", "accepted_ref": ref, **desired}
            if trial is not None:
                trial.settle_tx(db, updated_request, updated_attempt, raw_usage)
            if updated_request != current:
                self.store.put_tx(db, "request", key, job, updated_request)
            if updated_attempt != attempt:
                self.store.put_tx(db, "attempt", attempt_id, job, updated_attempt)
        return updated_request

    def send(self, job: str, key: str) -> dict:
        if self.usage_trial is not None:
            self.usage_trial.fence(self)
        if self.active_time:
            self.active_time.checkpoint()
        while True:
            request = self.reconcile(job, key)
            if request["accepted_ref"]:
                return self.store.json(request["accepted_ref"], job)
            if self.trial_for(request) is not None and self.usage_trial is None:
                raise StopRun("usage_trial_coordinator_required", "This frozen anchored input requires its offline coordinator. No request was sent.")
            if self.usage_trial is not None and request["attempts"]:
                self.usage_trial.recover_request(job, key)
            if request["attempts"]:
                self._recover_failed_attempt(request)
                self._check_reentry(request)
            self._wait_for_retry(request)
            result = self._send_attempt(job, key, request)
            if result is not None:
                return result

    def _budget(self, current, *, admission=False):
        if current["cancel_requested"]:
            raise StopRun("cancelled", "Stopped before a new model request." if admission else
                          "Local request cancelled. Upstream cancellation and final cost are unknown.")
        active = self.active_time.elapsed(current) if self.active_time else current["active_seconds"]
        limits = current["limits"]
        if active >= limits["max_active_seconds"] or (admission and current["attempts"] >= limits["max_requests"]):
            raise StopRun("budget_exhausted", "The persistent request or active-time budget is exhausted. Saved versions remain exportable.")

    def deadline_remaining(self, request: dict, field: str) -> float:
        record = request.get(field)
        if record is None or record.get("satisfied_by"):
            return 0.0
        seconds, renewed = network.remaining(self.clocks, record)
        if renewed is not record:
            request[field] = renewed
            schedule = request.get("retry_schedule")
            if field == "not_before" and schedule and schedule.get("source") == "retry_after":
                request["retry_schedule"] = {**schedule, **renewed}
            with self.store.transaction() as db:
                self.store.put_tx(db, "request", request["id"], request["job"], request)
                if field == "retry_schedule" or request.get("retry_schedule") is not schedule:
                    self.store.event_tx(db, request["job"], "retry_scheduled", request["retry_schedule"])
        return seconds

    def _wait_for_retry(self, request):
        if not (request.get("not_before") or request.get("retry_schedule")):
            return
        while True:
            if self.active_time:
                self.active_time.checkpoint(force=False)
            self._budget(self.store.get("job", request["job"]), admission=True)
            seconds = max(self.deadline_remaining(request, "not_before"),
                          self.deadline_remaining(request, "retry_schedule"))
            if seconds <= 0:
                return
            self.retry_sleep(min(1.0, seconds))

    def _recover_failed_attempt(self, request):
        if request["status"] != "in_flight":
            return
        job, key = request["job"], request["id"]
        attempt = self.store.get("attempt", request["attempts"][-1], job=job)
        observation = self.store.maybe("stream_receive", attempt["id"])
        if observation and observation["transport"].get("http_status") is not None:
            attempt.update(http_status=observation["transport"]["http_status"], send_evidence="response_observed")
        status = attempt.get("http_status")
        if status is not None and not 200 <= status < 300:
            failure_class = "transient_status" if status in network.TRANSIENT_STATUSES else "configuration"
            attempt.update(failure_class=failure_class, upstream_code=attempt.get("upstream_code", "unavailable"))
            detail = f"Nexus returned HTTP {status}."
            request["status"] = "http_error"
        else:
            attempt.update(failure_class="lost_after_send")
            detail = "The engine stopped before it recorded a complete accepted reply."
            request["status"] = "unknown"
        attempt.update(status=request["status"], finished=self.clocks.wall(), remote_cancelled=None)
        attempt.setdefault("send_evidence", "may_have_been_sent")
        self._settle_failure(request, attempt, detail)

    def _check_reentry(self, request):
        failure = request.get("failure", {})
        if request["status"] == "rejected":
            raise StopRun("response_rejected", failure.get("message", "The saved response was rejected."))
        policy = request.get("replay_policy")
        if policy is None:
            policy = network.legacy_policy(self.store.get("job", request["job"]))
        if "automatic_retry" not in policy:
            # Historical requests keep their prior re-entry gate, with no
            # automatic retry loop on the exchange that encounters a failure.
            if request["status"] == "http_error":
                raise StopRun(failure.get("reason", "provider_configuration_error"),
                              failure.get("message", "Nexus returned an HTTP error."))
            if (failure.get("reason") == "provider_configuration_error"
                    or not policy.get("replay_unknown")
                    or len(request["attempts"]) >= policy.get("max_attempts_per_request", 1)):
                raise StopRun(failure.get("reason", "unknown_outcome"),
                              failure.get("message", "The prior request has no accepted reply. Remote completion and cost are unknown."))
            return
        if request.get("retry_schedule"):
            return
        # A user/allowance stop can end an exchange before the transport
        # provides a result. On re-entry schedule it like other unresolved sends.
        if failure.get("reason") in {"cancelled", "budget_exhausted"}:
            attempt = self.store.get("attempt", request["attempts"][-1], job=request["job"])
            self._settle_failure(request, attempt, "The previous exchange ended before an accepted reply.")
            if request.get("retry_schedule"):
                return
            failure = request["failure"]
        raise StopRun(failure.get("reason", "unknown_outcome"),
                      failure.get("message", "The prior request has no accepted reply."))

    def _settle_failure(self, request, attempt, detail):
        job, key = request["job"], request["id"]
        policy = request.get("replay_policy")
        if policy is None:
            policy = network.legacy_policy(self.store.get("job", job))
        failure_class = attempt["failure_class"]
        used = len(request["attempts"])
        maximum = policy.get("max_attempts_per_request", 1)
        usage_trial = self.trial_for(request)
        delay = attempt.get("retry_after_seconds")
        if delay is not None and "not_before" not in request:
            request["not_before"] = network.deadline(self.clocks, delay)
        if failure_class == "configuration":
            reason = "provider_configuration_error"
        elif failure_class == "rejected_reply":
            reason = "response_rejected"
        elif delay is not None and delay > policy.get("max_server_wait_seconds", float("inf")):
            reason = "retry_wait_exceeds_limit"
        elif usage_trial or not policy.get("automatic_retry"):
            reason = ("network_retry_disabled" if not usage_trial and ("automatic_retry" in policy or failure_class == "unsent")
                      else "provider_error" if failure_class == "transient_status" else "unknown_outcome")
        elif used >= maximum:
            reason = "network_retry_exhausted"
        else:
            backoff = min(policy["backoff_max_seconds"], policy["backoff_initial_seconds"] * 2 ** (used - 1))
            schedule = dict(request["not_before"]) if delay is not None else network.deadline(self.clocks, self.jitter(0, backoff))
            schedule.update(request=key, failed_attempt=attempt["id"], failure_class=failure_class,
                            detail=detail, source="retry_after" if delay is not None else "backoff",
                            next_attempt=used + 1, max_attempts=maximum)
            request["retry_schedule"] = schedule
            reason = "retry_scheduled"
        meaning = ("No request reached the provider and this attempt incurred no inference usage."
                   if attempt["send_evidence"] == "not_sent" else
                   "Remote completion and usage are unknown. A repeated request may duplicate upstream work.")
        pause = {"network_retry_disabled": "Automatic retry is off. ",
                 "network_retry_exhausted": "Automatic attempts exhausted. ",
                 "retry_wait_exceeds_limit": f"The server requested {delay:g} seconds, above the automatic wait limit. "
                 if delay is not None else ""}
        label = {"unsent": "Connection failed before sending", "lost_after_send": "Connection lost after possible send",
                 "transient_status": "Temporary HTTP failure", "configuration": "Provider configuration error",
                 "rejected_reply": "Reply rejected"}[failure_class]
        request["failure"] = {"reason": reason, "message": f"{pause.get(reason, '')}{label}. {detail} Attempt {used} of {maximum}. {meaning}",
                              "class": failure_class}
        with self.store.transaction() as db:
            if self.usage_trial is not None:
                self.usage_trial.failed_tx(db, request, attempt)
            self.store.put_tx(db, "request", key, job, request)
            self.store.put_tx(db, "attempt", attempt["id"], job, attempt)
            if reason == "retry_scheduled":
                self.store.event_tx(db, job, "retry_scheduled", request["retry_schedule"])
        return StopRun(reason, request["failure"]["message"])

    def _send_attempt(self, job: str, key: str, request: dict) -> dict | None:
        token = self.credentials(job)
        route = Route.model_validate(request["route"])
        attempt_id = uid()
        started = self.clocks.wall()
        streaming = route.wait_policy is not None
        observed = {"deadline_seconds": route.wait_policy.total_seconds if streaming else route.timeout_seconds,
                    "wait_policy": route.wait_policy.model_dump() if streaming else None,
                    "mode": "streaming_progress" if streaming else "legacy_total",
                    "connect_timeout_seconds": min(30, route.wait_policy.first_progress_seconds if streaming else route.timeout_seconds),
                    "settled": False, "stop_cause": None, "error_type": None,
                    "http_status": None, "headers_elapsed_seconds": None,
                    "first_body_elapsed_seconds": None, "last_body_elapsed_seconds": None,
                    "received_body_bytes": 0, "body_complete": None,
                    "body_complete_elapsed_seconds": None, "elapsed_seconds": None,
                    "first_event_elapsed_seconds": None, "last_event_elapsed_seconds": None,
                    "first_progress_elapsed_seconds": None, "last_progress_elapsed_seconds": None,
                    "event_count": 0, "progress_count": 0, "terminal_event": None,
                    "protocol_complete": False, "terminal_elapsed_seconds": None}
        trial_identity = self.usage_trial.preflight(request) if self.usage_trial else None
        prohibition = None
        with self.store.transaction() as db:
            current = self.store.get_tx(db, "job", job)
            self._budget(current, admission=True)
            frozen = self.store.get_tx(db, "request", key, job=job)
            if frozen != request:
                raise Conflict("The pending request changed before attempt admission.")
            if self.usage_trial is not None:
                prohibition = self.usage_trial.claim_tx(db, request, attempt_id, trial_identity)
            if prohibition:
                self.usage_trial.prohibit_tx(db, request, "physical_dispatch", prohibition)
            else:
                current["attempts"] += 1
                self.store.put_tx(db, "job", job, job, current)
                request["attempts"].append(attempt_id)
                request["status"] = "in_flight"
                for field in ("failure", "retry_schedule"):
                    request.pop(field, None)
                cooldown = request.get("not_before")
                if cooldown and not cooldown.get("satisfied_by"):
                    request["not_before"] = {**cooldown, "satisfied_by": attempt_id}
                self.store.put_tx(db, "request", key, job, request)
                self.store.put_tx(db, "attempt", attempt_id, job,
                                  {"id": attempt_id, "request": key, "status": "in_flight", "started": started, "usage": None,
                                   "send_evidence": "may_have_been_sent",
                                   **({"not_before": cooldown} if cooldown and not cooldown.get("satisfied_by") else {}),
                                   "transport": {k: v for k, v in observed.items() if k != "http_status"}})
                self.store.event_tx(db, job, "request_started", {"request": key, "kind": request["kind"],
                    "attempt": attempt_id, "attempt_number": len(request["attempts"]),
                    "max_attempts": request.get("replay_policy", {}).get("max_attempts_per_request", 1)})
        if prohibition:
            raise StopRun("usage_trial_dispatch_blocked", "Frozen anchored dispatch is prohibited: " + prohibition + ". No request was sent.")
        payload = self.store.json(request["payload_ref"], job)
        received = bytearray()
        decoder = StreamDecoder(route.protocol) if streaming else None
        cursor = {"format": "ordered_chunks_v1", "chunk_count": 0, "bytes": 0,
                  "sha256": sha256(b"").hexdigest(), "last_chunk_ref": None}
        stream_digest = sha256()

        def record_chunk(chunk, moment):
            # Immutable decoded SSE bytes are persisted before interpretation. Each attempt
            # has its own sequence; re-entry never appends to another attempt's stream.
            index = cursor["chunk_count"]
            blob = self.store.blob(job, "stream_chunk", chunk,
                                   {"request": key, "attempt": attempt_id, "index": index,
                                    "elapsed_seconds": moment}, key=f"stream:{attempt_id}:{index}")
            stream_digest.update(chunk)
            cursor.update(chunk_count=index + 1, bytes=cursor["bytes"] + len(chunk),
                          sha256=stream_digest.hexdigest(), last_chunk_ref=blob["ref"])

        def record_observation():
            # Checkpoint observations independently of final acceptance. A hard stop may
            # leave extra durable chunks beyond this observation; absence is not zero work.
            self.store.put("stream_receive", attempt_id, job,
                           {"attempt": attempt_id, "request": key, "cursor": dict(cursor),
                            "transport": deepcopy(observed)})

        def record_headers():
            status = observed["http_status"]
            if observed.get("retry_after_seconds") is not None:
                request["not_before"] = network.deadline(self.clocks, observed["retry_after_seconds"])
            with self.store.transaction() as db:
                attempt = self.store.get_tx(db, "attempt", attempt_id, job=job)
                attempt.update(http_status=status, send_evidence="response_observed",
                               transport={k: v for k, v in observed.items() if k != "http_status"})
                if not 200 <= status < 300:
                    attempt.update(failure_class=observed["failure_class"], upstream_code="unavailable",
                                   retry_after_seconds=observed.get("retry_after_seconds"))
                    self.store.put_tx(db, "request", key, job, request)
                self.store.put_tx(db, "attempt", attempt_id, job, attempt)

        failure = None
        failure_class = detail = None
        attempt_response_ref = None
        send_evidence = "may_have_been_sent"
        verified_stream = None
        try:
            with self.store.connection_scope():
                status = asyncio.run(self.exchange(job, route, token, payload, received, observed,
                                                   decoder=decoder, record_chunk=record_chunk,
                                                   record_observation=record_observation, record_headers=record_headers))
            if status < 200 or status >= 300:
                request["status"] = "http_error"
                failure_class = observed["failure_class"]
                detail = f"Nexus returned HTTP {status}."
            else:
                if streaming:
                    stream = self.archive_stream(job, request, attempt_id, received, observed, cursor)
                    verified_stream = stream
                    raw = self.store.blob(job, "assembled_response", decoder.value,
                                          {"request": key, "attempt": attempt_id, "source_stream_ref": stream["ref"],
                                           "protocol": route.protocol, "complete_protocol": decoder.complete})
                    native_bytes = self.store.bytes(raw["ref"], job)
                else:
                    raw = self.store.blob(job, "native_response", bytes(received), {"request": key, "attempt": attempt_id, "complete_transport": True})
                    native_bytes = bytes(received)
                request["response_ref"] = raw["ref"]
                attempt_response_ref = raw["ref"]
                try:
                    accepted = parse_reply(route.protocol, native_bytes)
                except (ValueError, KeyError, TypeError) as exc:
                    request["status"] = "rejected"
                    observed["diagnostic"] = {"category": "invalid_stream", "field": "response", "stage": "native",
                                              "ordinal": decoder.event_ordinal if streaming else None}
                    failure_class, detail = "rejected_reply", str(exc)
                else:
                    accepted["native_ref"] = raw["ref"]
                    if streaming:
                        accepted["stream_ref"] = request["stream_ref"]
                    ref = self.store.blob(job, "accepted_response", accepted,
                                          {"request": key, "attempt": attempt_id, "received_at": time.time(),
                                           "transport": deepcopy(observed)}, key=f"accepted:{key}")
                    request.update(status="accepted", accepted_ref=ref["ref"])
        except StreamError as exc:
            observed["diagnostic"] = exc.diagnostic
            # Do not echo provider error events, which can contain arbitrary secrets.
            incomplete = observed["stop_cause"] == "stream_incomplete"
            request["status"] = "unknown" if incomplete else "rejected"
            failure_class = "lost_after_send" if incomplete else "rejected_reply"
            detail = ("The stream ended without a complete terminal response." if incomplete else
                      "The stream failed validation. Original received bytes are retained; no partial tools were executed.")
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            failure_class, send_evidence, explanation = network.classify_transport(
                exc, route.endpoint, "response_observed" if observed["http_status"] is not None else send_evidence)
            request["status"] = "unsent" if failure_class == "unsent" else "http_error" if failure_class == "configuration" else "unknown"
            cause = observed["stop_cause"]
            detail = explanation or (f"The local {route.timeout_seconds:g}-second request deadline was reached."
                      if cause == "request_deadline" else
                      {"first_progress_timeout": "The first generation-progress wait expired.",
                       "progress_idle_timeout": "The generation-progress idle wait expired.",
                       "total_deadline": "The explicitly selected total request deadline expired."}.get(cause) or
                      "The connection ended before a complete accepted reply (" + str(cause or "unclassified") + ").")
            status_text = (f"HTTP {observed['http_status']} headers were received."
                           if observed["http_status"] is not None else "No HTTP status was observed.")
            if failure_class == "lost_after_send":
                detail += f" {status_text} Received {observed['received_body_bytes']} success-body bytes."
        except StopRun as exc:
            failure_class = observed.get("failure_class", "lost_after_send")
            request["status"] = "http_error" if observed.get("failure_class") else "unknown"
            detail = f"Nexus returned HTTP {observed['http_status']}." if request["status"] == "http_error" else None
            failure = exc
        finally:
            # Only success-stream bytes are retained. Arbitrary HTTP error bodies can echo credentials.
            if streaming:
                if received:
                    self.archive_stream(job, request, attempt_id, received, observed, cursor)
                if decoder.value is not None and attempt_response_ref is None:
                    candidate = self.store.blob(job, "assembled_response", decoder.value,
                                               {"request": key, "attempt": attempt_id, "source_stream_ref": request.get("stream_ref"),
                                                "protocol": route.protocol, "complete_protocol": decoder.complete,
                                                "accepted": False})
                    request["response_ref"] = candidate["ref"]
                    attempt_response_ref = candidate["ref"]
                record_observation()
            elif received and request["status"] == "unknown":
                complete = observed["body_complete"] is True
                raw = self.store.blob(job, "native_response" if complete else "partial_native_response", bytes(received),
                                      {"request": key, "attempt": attempt_id, "complete_transport": complete,
                                       "within_deadline": (observed["body_complete_elapsed_seconds"] < route.timeout_seconds)
                                       if complete else None})
                if complete:
                    request["response_ref"] = raw["ref"]
                attempt_response_ref = raw["ref"]
            if request["accepted_ref"]:
                request = self._settle_accepted(job, key, verified_stream=verified_stream)
            else:
                # Exceptions outside the transport/validation boundary leave
                # the admission unresolved for re-entry.
                attempt = {**self.store.get("attempt", attempt_id, job=job),
                           "id": attempt_id, "request": key, "status": request["status"], "started": started,
                           "finished": self.clocks.wall(), "http_status": observed["http_status"], "usage": None, "remote_cancelled": None,
                           "send_evidence": "response_observed" if observed["http_status"] is not None else send_evidence,
                           "failure_class": failure_class,
                           "transport": {k: v for k, v in observed.items() if k != "http_status"}}
                for field in ("upstream_code", "retry_after_seconds"):
                    if field in observed:
                        attempt[field] = observed[field]
                if streaming and received:
                    attempt["stream_ref"] = request["stream_ref"]
                if attempt_response_ref:
                    attempt["response_ref"] = attempt_response_ref
                if detail is not None:
                    settled = self._settle_failure(request, attempt, detail)
                    if failure is None and settled.reason != "retry_scheduled":
                        failure = settled
                elif failure is not None:
                    request["failure"] = {"reason": failure.reason, "message": str(failure), "class": failure_class}
                    with self.store.transaction() as db:
                        if self.usage_trial is not None:
                            self.usage_trial.failed_tx(db, request, attempt)
                        self.store.put_tx(db, "request", key, job, request)
                        self.store.put_tx(db, "attempt", attempt_id, job, attempt)
                elif received:
                    # A local fault can follow a durable success-body write.
                    # Publish its proven pointers while leaving the admission unresolved.
                    attempt.pop("finished", None)
                    attempt.pop("failure_class", None)
                    with self.store.transaction() as db:
                        self.store.put_tx(db, "request", key, job, request)
                        self.store.put_tx(db, "attempt", attempt_id, job, attempt)
        if failure:
            raise failure
        return self.store.json(request["accepted_ref"], job) if request["accepted_ref"] else None

    def archive_stream(self, job, request, attempt_id, received, observed, cursor):
        key = f"raw-stream:{attempt_id}"
        previous = self.store.maybe("blob", key)
        if previous is None:
            count = cursor["chunk_count"]
            known_prefix = (type(count) is int and 0 <= count <= len(received)
                            and cursor["bytes"] == len(received)
                            and cursor["sha256"] == sha256(received).hexdigest()
                            and cursor["last_chunk_ref"] == (f"stream:{attempt_id}:{count - 1}" if count else None))
            if not observed["protocol_complete"] and not request["accepted_ref"] and known_prefix:
                # Preserve unaccepted partial evidence without a second full file
                # pass after Stop. Each cursor entry already completed blob durability.
                refs = [f"stream:{attempt_id}:{index}" for index in range(count)]
                validation = "registration_only"
            else:
                durable = self.store.read_stream(job, request["id"], attempt_id)
                if durable["data"] != bytes(received):
                    raise ValueError("Received stream does not match its durable chunk evidence.")
                refs, validation = durable["chunks"], "reconstructed"
            previous = self.store.blob(job, "raw_stream", bytes(received),
                                       {"request": request["id"], "attempt": attempt_id,
                                        "chunks": refs, "chunk_validation": validation,
                                        "encoding": "decoded HTTP body / SSE UTF-8",
                                        "complete_protocol": observed["protocol_complete"],
                                        "complete_transport": observed["body_complete"],
                                        "terminal_event": observed["terminal_event"]}, key=key)
        request["stream_ref"] = previous["ref"]
        return previous

    async def exchange(self, job, route, token, payload, received, observed, *, decoder=None,
                       record_chunk=None, record_observation=None, record_headers=None):
        wait = RequestWait(route, clock=self.clock)
        elapsed = wait.elapsed

        def check_wait(moment):
            cause = wait.expired(moment)
            if cause:
                observed["stop_cause"] = cause
                raise asyncio.TimeoutError()

        def check_control():
            self._budget(self.store.get("job", job))

        io_seconds = 30 if decoder else route.timeout_seconds
        timeout = httpx.Timeout(None, connect=observed["connect_timeout_seconds"], write=io_seconds, pool=io_seconds)
        client = httpx.AsyncClient(http2=True, trust_env=False, follow_redirects=False,
                                   timeout=timeout, transport=self.transport)
        response = None
        diagnostic_deadline = None

        async def perform():
            nonlocal response, diagnostic_deadline
            native_request = client.build_request("POST", route.endpoint,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, content=encode(payload))
            response = await client.send(native_request, stream=True)
            # These observations survive a later body timeout. Do not retain response headers.
            observed["http_status"] = response.status_code
            observed["headers_elapsed_seconds"] = elapsed()
            success = 200 <= response.status_code < 300
            if not success:
                observed.update(stop_cause="http_error", upstream_code="unavailable",
                                failure_class="transient_status" if response.status_code in network.TRANSIENT_STATUSES else "configuration",
                                retry_after_seconds=network.retry_after(response.headers, self.clocks.wall()))
            if record_headers:
                record_headers()
            if decoder:
                record_observation()
            if success:
                observed["body_complete"] = False
                async for chunk in response.aiter_bytes():
                    received.extend(chunk)
                    if chunk:
                        moment = elapsed()
                        if observed["first_body_elapsed_seconds"] is None:
                            observed["first_body_elapsed_seconds"] = moment
                        observed["last_body_elapsed_seconds"] = moment
                        observed["received_body_bytes"] = len(received)
                        if decoder:
                            record_chunk(chunk, moment)
                            check_control()
                            check_wait(moment)  # A late delta cannot reset an expired clock.
                            try:
                                decoder.feed(chunk)
                            finally:
                                update = decoder.last_feed
                                if update.events:
                                    if observed["first_event_elapsed_seconds"] is None:
                                        observed["first_event_elapsed_seconds"] = moment
                                    observed["last_event_elapsed_seconds"] = moment
                                    observed["event_count"] += update.events
                                if update.progress:
                                    wait.progress(moment)
                                    observed["progress_count"] += 1
                                observed.update(first_progress_elapsed_seconds=wait.first_progress,
                                                last_progress_elapsed_seconds=wait.last_progress,
                                                terminal_event=decoder.terminal,
                                                protocol_complete=decoder.complete)
                                if decoder.complete:
                                    observed.update(terminal_elapsed_seconds=moment, stop_cause="complete")
                                record_observation()
                            if decoder.complete:
                                # Check all bytes already received, including the suffix
                                # in this chunk, using the same rule as saved replay.
                                # Do not wait for gateway EOF or read another chunk.
                                decoder.finish_received()
                                return response.status_code
                observed["body_complete"] = True
                observed["body_complete_elapsed_seconds"] = elapsed()
                # A synchronous transport segment can finish before the poller gets control.
                # Full late bytes remain evidence, but cannot bypass the frozen deadline.
                check_wait(observed["body_complete_elapsed_seconds"])
                if decoder:
                    if not decoder.complete:
                        observed["stop_cause"] = "stream_incomplete"
                    decoder.finish()
                observed["stop_cause"] = "complete"
            else:
                check_control()
                diagnostic_deadline = asyncio.get_running_loop().time() + network.DIAGNOSTIC_SECONDS
                observed["upstream_code"] = await self._error_code(response)
            return response.status_code

        task = asyncio.create_task(perform())
        try:
            while not task.done():
                if self.active_time:
                    self.active_time.checkpoint(force=False)
                check_control()
                remaining = 0.1
                if observed["stop_cause"] != "http_error":
                    check_wait(elapsed())
                    remaining = max(0.0, wait.boundary()[0] - elapsed())
                await asyncio.wait({task}, timeout=min(0.1, remaining))
            return await task
        except StreamError as exc:
            observed["diagnostic"] = exc.diagnostic
            observed.update(terminal_event=decoder.terminal, protocol_complete=decoder.complete)
            if observed["stop_cause"] != "stream_incomplete":
                observed["stop_cause"] = "stream_error"
            raise
        except httpx.TimeoutException as exc:
            observed["stop_cause"] = next((cause for kind, cause in (
                (httpx.ConnectTimeout, "connect_timeout"), (httpx.ReadTimeout, "read_timeout"),
                (httpx.WriteTimeout, "write_timeout"), (httpx.PoolTimeout, "pool_timeout")) if isinstance(exc, kind)), "transport_timeout")
            observed["error_type"] = type(exc).__name__
            raise
        except httpx.HTTPError as exc:
            observed.update(stop_cause="transport_error", error_type=type(exc).__name__)
            raise
        except asyncio.TimeoutError:
            if observed["stop_cause"] not in {"request_deadline", "total_deadline", "first_progress_timeout", "progress_idle_timeout"}:
                observed["stop_cause"] = "transport_timeout"
            raise
        except StopRun as exc:
            if observed["stop_cause"] != "http_error":
                observed["stop_cause"] = {"cancelled": "user_stop", "budget_exhausted": "active_time_limit"}.get(exc.reason, "local_stop")
            raise
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            # Generation waiting has ended. Cleanup must not demote a timely terminal
            # to unknown, nor wait forever when the HTTP connection fails to close.
            observed["receive_elapsed_seconds"] = elapsed()
            async def cleanup():
                try:
                    if response is not None:
                        await response.aclose()
                finally:
                    await client.aclose()
            cleanup_started = self.clock()
            try:
                cleanup_budget = 5
                if diagnostic_deadline is not None:
                    # The optional error-body path shares one wall-time budget
                    # with cleanup, even if the upstream stops producing bytes.
                    cleanup_budget = max(0.001, diagnostic_deadline - asyncio.get_running_loop().time())
                await asyncio.wait_for(cleanup(), timeout=cleanup_budget)
                observed["cleanup_complete"] = True
            except (Exception, asyncio.CancelledError) as exc:
                observed.update(cleanup_complete=False, cleanup_error_type=type(exc).__name__)
            observed["cleanup_elapsed_seconds"] = max(0.0, self.clock() - cleanup_started)
            observed["elapsed_seconds"] = elapsed()
            observed["settled"] = True

    @staticmethod
    async def _error_code(response):
        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if (content_type != "application/json" and not content_type.endswith("+json")
                or response.headers.get("content-encoding", "identity").lower() != "identity"):
            return "unavailable"

        async def read():
            if response.is_stream_consumed:
                return network.upstream_code(response.content) if len(response.content) <= network.DIAGNOSTIC_BYTES else "unavailable"
            body = bytearray()
            async for chunk in response.aiter_raw():
                if len(body) + len(chunk) > network.DIAGNOSTIC_BYTES:
                    return "unavailable"
                body.extend(chunk)
            return network.upstream_code(body)

        try:
            return await asyncio.wait_for(read(), timeout=network.DIAGNOSTIC_SECONDS)
        except (httpx.HTTPError, httpx.StreamError, TimeoutError, OSError, ValueError):
            return "unavailable"
