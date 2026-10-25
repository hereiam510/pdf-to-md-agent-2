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
    common = {"model": route.model, "stream": False, **deepcopy(route.parameters)}
    if route.protocol == "chat_completions":
        common.update({"messages": [{"role": "system", "content": instructions}, *messages],
                       "max_completion_tokens": route.output_tokens})
        if tools:
            common["tools"] = [{"type": "function", "function": tool} for tool in tools]
    else:
        common.update({"instructions": instructions, "input": messages, "store": False,
                       "max_output_tokens": route.output_tokens,
                       "include": ["reasoning.encrypted_content"]})
        if tools:
            common["tools"] = [{"type": "function", **tool, "strict": False} for tool in tools]
    return common


class Nexus:
    def __init__(self, store: Store, credentials: Callable[[str], str], transport=None):
        self.store, self.credentials, self.transport = store, credentials, transport
        self.active_time = None

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
        if not request["accepted_ref"] and staged:
            # Accepting bytes and updating the request pointer are separate commits.
            request.update(status="accepted", accepted_ref=staged["ref"])
            self.store.put("request", key, job, request)
            attempt = self.store.get("attempt", staged["meta"]["attempt"], job=job)
            attempt.update(status="accepted", usage=self.store.json(staged["ref"], job)["usage"],
                           finished=staged["meta"]["received_at"])
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
                              {"id": attempt_id, "request": key, "status": "in_flight", "started": time.time(), "usage": None})
        self.store.event(job, "request_started", {"request": key, "kind": request["kind"], "attempt": attempt_id})
        payload = self.store.json(request["payload_ref"], job)
        received = bytearray()
        status = None
        started = time.time()
        failure = None
        try:
            status = asyncio.run(self.exchange(job, route, token, payload, received))
            if status < 200 or status >= 300:
                request["status"] = "http_error"
                failure = StopRun("provider_error", f"Nexus returned HTTP {status}. The error body is withheld to protect credentials. No context-overflow diagnosis is assumed.")
            else:
                raw = self.store.blob(job, "native_response", bytes(received), {"request": key, "attempt": attempt_id, "complete_transport": True})
                request["response_ref"] = raw["ref"]
                try:
                    accepted = parse_reply(route.protocol, bytes(received))
                except (ValueError, KeyError, TypeError) as exc:
                    request["status"] = "rejected"
                    failure = StopRun("response_rejected", str(exc))
                else:
                    accepted["native_ref"] = raw["ref"]
                    ref = self.store.blob(job, "accepted_response", accepted,
                                          {"request": key, "attempt": attempt_id, "received_at": time.time()}, key=f"accepted:{key}")
                    request.update(status="accepted", accepted_ref=ref["ref"])
        except (httpx.HTTPError, asyncio.TimeoutError):
            request["status"] = "unknown"
            failure = StopRun("unknown_outcome", "The connection ended before a complete accepted reply. Remote completion and usage are unknown.")
        except StopRun as exc:
            request["status"] = "unknown"
            failure = exc
        finally:
            # Only success-stream bytes are retained. Arbitrary HTTP error bodies can echo credentials.
            if received and request["status"] == "unknown":
                self.store.blob(job, "partial_native_response", bytes(received),
                                {"request": key, "attempt": attempt_id, "complete_transport": False})
            if failure:
                request["failure"] = {"reason": failure.reason, "message": str(failure)}
            self.store.put("request", key, job, request)
            attempt = {"id": attempt_id, "request": key, "status": request["status"], "started": started,
                       "finished": time.time(), "http_status": status, "usage": None, "remote_cancelled": None}
            if request["accepted_ref"]:
                attempt["usage"] = self.store.json(request["accepted_ref"], job)["usage"]
            self.store.put("attempt", attempt_id, job, attempt)
        if failure:
            raise failure
        return self.store.json(request["accepted_ref"], job)

    async def exchange(self, job, route, token, payload, received):
        async def perform():
            async with httpx.AsyncClient(http2=True, trust_env=False, follow_redirects=False,
                                         timeout=httpx.Timeout(route.timeout_seconds, connect=min(30, route.timeout_seconds)),
                                         transport=self.transport) as client:
                async with client.stream("POST", route.endpoint, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                                         content=encode(payload)) as response:
                    if 200 <= response.status_code < 300:
                        async for chunk in response.aiter_bytes():
                            received.extend(chunk)
                    return response.status_code

        task = asyncio.create_task(perform())
        started = time.monotonic()
        try:
            while not task.done():
                if self.active_time:
                    self.active_time.checkpoint(force=False)
                current = self.store.get("job", job)
                elapsed = self.active_time.elapsed(current) if self.active_time else current["active_seconds"]
                if current["cancel_requested"]:
                    raise StopRun("cancelled", "Local request cancelled. Upstream cancellation and final cost are unknown.")
                if elapsed >= current["limits"]["max_active_seconds"]:
                    raise StopRun("budget_exhausted", "Active-time budget exhausted. Upstream completion and cost are unknown.")
                if time.monotonic() - started >= route.timeout_seconds:
                    raise asyncio.TimeoutError()
                await asyncio.wait({task}, timeout=0.1)
            return await task
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
