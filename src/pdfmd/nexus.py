"""Frozen native requests, complete replies, and a single durable send gate."""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json
from hashlib import sha256
import time
from typing import Callable

import httpx

from .schema import Route
from .storage import Conflict, Store, encode, uid
from .streaming import StreamDecoder, StreamError
from .waiting import RequestWait


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
    value = json.loads(raw, object_pairs_hook=unique_object)
    calls = []
    texts = []
    if protocol == "chat_completions":
        choices = value.get("choices", [])
        if len(choices) != 1 or choices[0].get("finish_reason") not in {"stop", "tool_calls"}:
            raise ValueError("The response has no single complete accepted choice.")
        message = choices[0]["message"]
        if message.get("refusal") or message.get("role") != "assistant":
            raise ValueError("The model refused or returned an unexpected message role.")
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
        for item in native:
            if item.get("type") == "function_call":
                if item.get("status", "completed") != "completed":
                    raise ValueError("The function call is incomplete.")
                calls.append({"id": item["call_id"], "name": item["name"], "arguments": item["arguments"]})
            elif item.get("type") == "message":
                if item.get("status", "completed") != "completed":
                    raise ValueError("The assistant message is incomplete.")
                for part in item.get("content", []):
                    if part.get("type") == "refusal":
                        raise ValueError("The model refused the request.")
                    if part.get("type") == "output_text":
                        texts.append(part["text"])
            elif item.get("type") != "reasoning":
                raise ValueError("Unsupported native output item. The original is retained; no tools were executed.")
    ids = set()
    for call in calls:
        if not isinstance(call["id"], str) or not call["id"] or call["id"] in ids:
            raise ValueError("Tool call IDs must be nonempty and unique in the accepted batch.")
        ids.add(call["id"])
        if not isinstance(call["arguments"], str) or not isinstance(call["name"], str):
            raise ValueError("Tool names and complete argument strings are required.")
        arguments = json.loads(call["arguments"], object_pairs_hook=unique_object)
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be a complete JSON object.")
    if not calls and not any(text.strip() for text in texts):
        raise ValueError("The accepted response contains neither executable calls nor text.")
    return {"native": native, "calls": calls, "text": "\n".join(texts), "usage": value.get("usage"), "provider_id": value.get("id")}


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
    def __init__(self, store: Store, credentials: Callable[[str], str], transport=None, *, clock=None):
        self.store, self.credentials, self.transport = store, credentials, transport
        self.active_time = None
        self.clock = clock or time.monotonic

    def freeze(self, job: str, key: str, payload: dict, kind: str, meta: dict) -> dict:
        old = self.store.maybe("request", key)
        if old:
            # Re-entry never rebuilds or alters a frozen request.
            return old
        current = self.store.get("job", job)
        route = current["route"]
        blob = self.store.blob(job, "request_input", payload, {"kind": kind, "request": key})
        record = {"id": key, "job": job, "kind": kind, "payload_ref": blob["ref"],
                  "route": route, "meta": meta, "instruction_basis": instruction_basis(current),
                  "replay_policy": {field: current["limits"][field] for field in ("replay_unknown", "max_attempts_per_request")},
                  "status": "prepared", "attempts": [], "accepted_ref": None}
        self.store.put("request", key, job, record)
        self.store.event(job, "request_prepared", {"request": key, "kind": kind, **meta.get("capacity", {})})
        return record

    def reconcile(self, job: str, key: str) -> dict:
        """Recover locally accepted bytes without sending anything."""
        request = self.store.get("request", key, job=job)
        staged = self.store.maybe("blob", f"accepted:{key}")
        accepted_ref = request["accepted_ref"] or (staged["ref"] if staged else None)
        if accepted_ref:
            acceptance = self.store.get("blob", accepted_ref, job=job)
            accepted = self.store.json(accepted_ref, job)
            if accepted.get("stream_ref"):
                stream = self.store.get("blob", accepted["stream_ref"], job=job)
                attempt_id = stream["meta"]["attempt"]
                self.store.read_stream(job, key, attempt_id)
                native = self.store.get("blob", accepted["native_ref"], job=job)
                if (acceptance["ref"] != accepted_ref or acceptance["kind"] != "accepted_response"
                        or acceptance["meta"].get("request") != key
                        or acceptance["meta"].get("attempt") != attempt_id
                        or stream["ref"] != f"raw-stream:{attempt_id}" or not stream["meta"].get("complete_protocol")
                        or native["kind"] != "assembled_response" or native["meta"].get("request") != key
                        or native["meta"].get("attempt") != attempt_id
                        or native["meta"].get("source_stream_ref") != stream["ref"]
                        or not native["meta"].get("complete_protocol")):
                    raise ValueError("Accepted streaming evidence has inconsistent provenance.")
                self.store.bytes(native["ref"], job)
        if not request["accepted_ref"] and staged:
            # Accepting bytes and updating the request pointer are separate commits.
            accepted = self.store.json(staged["ref"], job)
            request.update(status="accepted", accepted_ref=staged["ref"])
            if accepted.get("stream_ref"):
                request.update(stream_ref=accepted["stream_ref"], response_ref=accepted["native_ref"])
            self.store.put("request", key, job, request)
            attempt = self.store.get("attempt", staged["meta"]["attempt"], job=job)
            attempt.update(status="accepted", usage=self.store.json(staged["ref"], job)["usage"],
                           finished=staged["meta"]["received_at"])
            if accepted.get("stream_ref"):
                attempt["stream_ref"] = accepted["stream_ref"]
                receipt = self.store.maybe("stream_receive", attempt["id"])
                if receipt:
                    attempt["http_status"] = receipt["transport"]["http_status"]
                    attempt["transport"] = {k: v for k, v in receipt["transport"].items() if k != "http_status"}
            self.store.put("attempt", attempt["id"], job, attempt)
        return request

    def send(self, job: str, key: str) -> dict:
        if self.active_time:
            self.active_time.checkpoint()
        request = self.reconcile(job, key)
        if request["accepted_ref"]:
            return self.store.json(request["accepted_ref"], job)
        state = self.store.get("job", job)
        limits = state["limits"]
        # Pre-snapshot records retain their task's immutable recovery policy.
        policy = request.get("replay_policy", limits)
        if request["status"] in {"rejected", "http_error"}:
            raise StopRun("response_rejected", "The saved response was rejected. Its original is retained. No partial tool calls were executed.")
        if request["attempts"] and (not policy["replay_unknown"] or len(request["attempts"]) >= policy["max_attempts_per_request"]):
            raise StopRun("unknown_outcome", "The prior request has no accepted reply. Configured replay is disabled or exhausted. Remote completion and cost are unknown.")
        token = self.credentials(job)
        route = Route.model_validate(request["route"])
        attempt_id = uid()
        started = time.time()
        streaming = route.wait_policy is not None
        wait = RequestWait(route)
        observed = {"deadline_seconds": wait.total,
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
        with self.store.transaction() as db:
            current = self.store.get_tx(db, "job", job)
            elapsed = self.active_time.elapsed(current) if self.active_time else current["active_seconds"]
            if current["cancel_requested"]:
                raise StopRun("cancelled", "Stopped before a new model request.")
            if current["attempts"] >= limits["max_requests"] or elapsed >= limits["max_active_seconds"]:
                raise StopRun("budget_exhausted", "The persistent request or active-time budget is exhausted. Saved versions remain exportable.")
            current["attempts"] += 1
            self.store.put_tx(db, "job", job, job, current)
            request["attempts"].append(attempt_id)
            request["status"] = "in_flight"
            self.store.put_tx(db, "request", key, job, request)
            self.store.put_tx(db, "attempt", attempt_id, job,
                              {"id": attempt_id, "request": key, "status": "in_flight", "started": started, "usage": None,
                               "transport": {k: v for k, v in observed.items() if k != "http_status"}})
        self.store.event(job, "request_started", {"request": key, "kind": request["kind"], "attempt": attempt_id})
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

        failure = None
        try:
            with self.store.connection_scope():
                status = asyncio.run(self.exchange(job, route, token, payload, received, observed,
                                                   decoder=decoder, wait=wait, record_chunk=record_chunk,
                                                   record_observation=record_observation))
            if status < 200 or status >= 300:
                request["status"] = "http_error"
                failure = StopRun("provider_error", f"Nexus returned HTTP {status}. The error body is withheld to protect credentials. No context-overflow diagnosis is assumed.")
            else:
                if streaming:
                    stream = self.archive_stream(job, request, attempt_id, received, observed, cursor)
                    raw = self.store.blob(job, "assembled_response", decoder.value,
                                          {"request": key, "attempt": attempt_id, "source_stream_ref": stream["ref"],
                                           "protocol": route.protocol, "complete_protocol": decoder.complete})
                    native_bytes = self.store.bytes(raw["ref"], job)
                else:
                    raw = self.store.blob(job, "native_response", bytes(received), {"request": key, "attempt": attempt_id, "complete_transport": True})
                    native_bytes = bytes(received)
                request["response_ref"] = raw["ref"]
                try:
                    accepted = parse_reply(route.protocol, native_bytes)
                except (ValueError, KeyError, TypeError) as exc:
                    request["status"] = "rejected"
                    failure = StopRun("response_rejected", str(exc))
                else:
                    accepted["native_ref"] = raw["ref"]
                    if streaming:
                        accepted["stream_ref"] = request["stream_ref"]
                    ref = self.store.blob(job, "accepted_response", accepted,
                                          {"request": key, "attempt": attempt_id, "received_at": time.time()}, key=f"accepted:{key}")
                    request.update(status="accepted", accepted_ref=ref["ref"])
        except StreamError:
            # Do not echo provider error events, which can contain arbitrary secrets.
            incomplete = observed["stop_cause"] == "stream_incomplete"
            request["status"] = "unknown" if incomplete else "rejected"
            failure = StopRun("unknown_outcome" if incomplete else "response_rejected",
                              "The stream ended without a complete terminal response. Remote completion and usage are unknown."
                              if incomplete else "The stream was invalid, failed, or incomplete. Original received bytes are retained; no partial tools were executed.")
        except (httpx.HTTPError, asyncio.TimeoutError):
            request["status"] = "unknown"
            cause = observed["stop_cause"]
            detail = (f"The local {route.timeout_seconds:g}-second request deadline was reached."
                      if cause == "request_deadline" else
                      {"first_progress_timeout": "The first generation-progress wait expired.",
                       "progress_idle_timeout": "The generation-progress idle wait expired.",
                       "total_deadline": "The explicitly selected total request deadline expired."}.get(cause) or
                      "The connection ended before a complete accepted reply (" + str(cause or "unclassified") + ").")
            status_text = (f"HTTP {observed['http_status']} headers were received."
                           if observed["http_status"] is not None else "No HTTP status was observed.")
            failure = StopRun("unknown_outcome", f"{detail} {status_text} "
                              f"Received {observed['received_body_bytes']} success-body bytes. "
                              "Remote completion and usage are unknown.")
        except StopRun as exc:
            request["status"] = "unknown"
            failure = exc
        finally:
            # Only success-stream bytes are retained. Arbitrary HTTP error bodies can echo credentials.
            if streaming:
                if received:
                    self.archive_stream(job, request, attempt_id, received, observed, cursor)
                if decoder.value is not None and not request.get("response_ref"):
                    candidate = self.store.blob(job, "assembled_response", decoder.value,
                                               {"request": key, "attempt": attempt_id, "source_stream_ref": request.get("stream_ref"),
                                                "protocol": route.protocol, "complete_protocol": decoder.complete,
                                                "accepted": False})
                    request["response_ref"] = candidate["ref"]
                record_observation()
            elif received and request["status"] == "unknown":
                complete = observed["body_complete"] is True
                raw = self.store.blob(job, "native_response" if complete else "partial_native_response", bytes(received),
                                      {"request": key, "attempt": attempt_id, "complete_transport": complete,
                                       "within_deadline": (observed["body_complete_elapsed_seconds"] < route.timeout_seconds)
                                       if complete else None})
                if complete:
                    request["response_ref"] = raw["ref"]
            if failure:
                request["failure"] = {"reason": failure.reason, "message": str(failure)}
            self.store.put("request", key, job, request)
            attempt = {"id": attempt_id, "request": key, "status": request["status"], "started": started,
                       "finished": time.time(), "http_status": observed["http_status"], "usage": None, "remote_cancelled": None,
                       "transport": {k: v for k, v in observed.items() if k != "http_status"}}
            if streaming:
                attempt["stream_ref"] = request.get("stream_ref")
            if request["accepted_ref"]:
                attempt["usage"] = self.store.json(request["accepted_ref"], job)["usage"]
            self.store.put("attempt", attempt_id, job, attempt)
        if failure:
            raise failure
        return self.store.json(request["accepted_ref"], job)

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
                       wait=None, record_chunk=None, record_observation=None):
        started = self.clock()
        elapsed = lambda: max(0.0, self.clock() - started)
        wait = wait or RequestWait(route)

        def check_wait(moment):
            cause = wait.expired(moment)
            if cause:
                observed["stop_cause"] = cause
                raise asyncio.TimeoutError()

        def check_control():
            current = self.store.get("job", job)
            if current["cancel_requested"]:
                raise StopRun("cancelled", "Local request cancelled. Upstream cancellation and final cost are unknown.")
            active = self.active_time.elapsed(current) if self.active_time else current["active_seconds"]
            if active >= current["limits"]["max_active_seconds"]:
                raise StopRun("budget_exhausted", "Active-time budget exhausted. Upstream completion and cost are unknown.")

        timeout = (httpx.Timeout(None, connect=observed["connect_timeout_seconds"], write=30, pool=30)
                   if decoder else httpx.Timeout(route.timeout_seconds, connect=observed["connect_timeout_seconds"]))
        client = httpx.AsyncClient(http2=True, trust_env=False, follow_redirects=False,
                                   timeout=timeout, transport=self.transport)
        response = None

        async def perform():
            nonlocal response
            native_request = client.build_request("POST", route.endpoint,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, content=encode(payload))
            response = await client.send(native_request, stream=True)
            # These observations survive a later body timeout. Do not retain response headers.
            observed["http_status"] = response.status_code
            observed["headers_elapsed_seconds"] = elapsed()
            if decoder:
                record_observation()
            if 200 <= response.status_code < 300:
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
                                # Terminal protocol output is sufficient. Do not wait for
                                # a gateway to close an otherwise complete SSE connection.
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
                # An observed error status is sufficient; arbitrary error bodies may echo credentials.
                observed["stop_cause"] = "http_error"
            return response.status_code

        task = asyncio.create_task(perform())
        try:
            while not task.done():
                if self.active_time:
                    self.active_time.checkpoint(force=False)
                check_control()
                check_wait(elapsed())
                remaining = wait.boundary()[0] - elapsed()
                await asyncio.wait({task}, timeout=min(0.1, remaining))
            return await task
        except StreamError:
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
                await asyncio.wait_for(cleanup(), timeout=5)
                observed["cleanup_complete"] = True
            except (Exception, asyncio.CancelledError) as exc:
                observed.update(cleanup_complete=False, cleanup_error_type=type(exc).__name__)
            observed["cleanup_elapsed_seconds"] = max(0.0, self.clock() - cleanup_started)
            observed["elapsed_seconds"] = elapsed()
            observed["settled"] = True
