"""Attempt-local SSE decoding and native reply assembly; no I/O or tool execution.

``complete`` means protocol completion, not acceptance by ``parse_reply`` or the
handoff validator. The caller retains the exact received bytes independently of
``value``, which is a reconstruction (CC) or the terminal response snapshot
(Responses). A decoder must never be reused for another transport attempt.
"""
from __future__ import annotations

import codecs
from copy import deepcopy
from dataclasses import dataclass
import json
from .usage import Usage, interpret_usage, accounting_fields


class StreamError(ValueError):
    """Safe local diagnosis. Never include arbitrary upstream error text."""

    def __init__(self, message, *, category="invalid_stream", field="event", stage="decode", ordinal=None):
        super().__init__(message)
        self.diagnostic = {"category": category, "field": field, "stage": stage, "ordinal": ordinal}


@dataclass(frozen=True)
class FeedResult:
    events: int = 0
    progress: bool = False
    terminal: str | None = None


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise StreamError("The stream contains duplicate JSON keys.")
        value[key] = item
    return value


def _index(value):
    if type(value) is not int or value < 0:
        raise StreamError("The stream contains an invalid item index.")
    return value


def _string(value):
    if not isinstance(value, str):
        raise StreamError("The stream contains an invalid text field.")
    return value


def _mapping(value):
    if not isinstance(value, dict):
        raise StreamError("The stream contains an invalid object.")
    return value


def validate_response_item_state(item: dict, *, final: bool, stage="decode"):
    """Validate explicit lifecycle semantics, without inventing optional fields.

    These three supported output types share a non-null status vocabulary;
    only messages have an assistant role. Missing fields retain the existing
    native-parser tolerance. A done boundary is final even when the outer
    response has not completed. Opaque reasoning is not a message or a call.
    """
    kind = item.get("type")
    if kind not in ("function_call", "message", "reasoning"):
        return  # Other item types still face their existing native/content gate.
    if "status" in item:
        status = item["status"]
        if not isinstance(status, str) or status not in ("in_progress", "completed", "incomplete"):
            raise StreamError("The output item has an unsupported status.",
                              category="unsupported_content", field="item", stage=stage)
        if status == "incomplete" or (final and status != "completed"):
            raise StreamError("The output item has no successful completion.",
                              category="content_conflict", field="item", stage=stage)
    if kind == "message" and "role" in item and item["role"] != "assistant":
        raise StreamError("The output message has an unexpected role.",
                          category="content_conflict", field="item", stage=stage)


class StreamDecoder:
    def __init__(self, protocol: str):
        if protocol not in {"chat_completions", "responses"}:
            raise ValueError("Unsupported stream protocol.")
        self.protocol = protocol
        self.complete = False
        self.value: dict | None = None
        self.terminal: str | None = None
        self.last_feed = FeedResult()
        self._utf8 = codecs.getincrementaldecoder("utf-8-sig")("strict")
        self._line: list[str] = []
        self._after_cr = False
        self._data: list[str] = []
        self._event = ""
        self._ended = False
        self._metadata: dict = {}
        self._message: dict = {"role": "assistant", "content": None}
        self._tools: dict[int, dict] = {}
        self._finish: str | None = None
        self._usage = None
        self.usage = Usage(None, "unknown", "missing")
        self.usage_observations = []
        self.service_observations = []
        self._usage_key = None
        self._usage_invalid = False
        self._ordinal = 0
        self._done_parts = {}
        self._annotations = {}
        self._sequence: dict[int, dict] = {}
        self._last_sequence = -1
        self._items: dict[int, dict] = {}
        self._item_statuses: dict[int, str] = {}
        self._done_items: dict[int, dict] = {}
        self._pieces: dict[tuple, str] = {}
        self._done_pieces: set[tuple] = set()
        self._response_id: str | None = None

    @property
    def event_ordinal(self):
        return self._ordinal

    def feed(self, chunk: bytes) -> FeedResult:
        """Consume complete SSE frames; incomplete frames never imply progress.

        Comments, lifecycle events, empty/whitespace deltas and metadata do not
        reset a progress clock. Whitespace is still preserved in assembled data.
        Equal text deltas remain separate additions, not inferred duplicates.
        """
        self.last_feed = FeedResult()
        if self._ended:
            raise StreamError("The stream decoder has already reached its receive boundary.")
        try:
            text = self._utf8.decode(chunk)
        except UnicodeError as exc:
            raise StreamError("The stream is not valid UTF-8.", ordinal=self._ordinal) from exc
        events, progress = 0, False
        for char in text:
            if self._after_cr:
                self._after_cr = False
                if char == "\n":
                    continue
            if char in "\r\n":
                line, self._line = "".join(self._line), []
                self._after_cr = char == "\r"
                try:
                    result = self._consume_line(line)
                except StreamError as exc:
                    # Earlier valid events in this same HTTP chunk are still observed
                    # progress even when a later frame rejects the whole response.
                    self.last_feed = FeedResult(events, progress, self.terminal)
                    exc.diagnostic["ordinal"] = self._ordinal
                    raise
                events += result.events
                progress |= result.progress
            else:
                self._line.append(char)
        self.last_feed = FeedResult(events, progress, self.terminal)
        return self.last_feed

    def _consume_line(self, line: str) -> FeedResult:
        if not line:
            data, event = self._data, self._event
            self._data, self._event = [], ""
            if not data:
                return FeedResult()
            return FeedResult(1, self._dispatch("\n".join(data), event), self.terminal)
        if line.startswith(":"):
            return FeedResult()
        field, separator, value = line.partition(":")
        if separator and value.startswith(" "):
            value = value[1:]
        if field == "data":
            self._data.append(value)
        elif field == "event":
            self._event = value
        # id/retry and unknown SSE fields do not initiate reconnection or reset
        # the progress clock. In particular, an SSE id can apply to many frames.
        return FeedResult()

    def _dispatch(self, data: str, event: str) -> bool:
        self._ordinal += 1
        if self.complete:
            raise StreamError("The stream contains data after its terminal event.")
        if data == "[DONE]":
            if self.protocol != "chat_completions" or self._finish is None:
                raise StreamError("The stream ended without a complete protocol result.")
            if sorted(self._tools) != list(range(len(self._tools))):
                raise StreamError("The stream tool indices are incomplete.")
            tools = [self._tools[i] for i in sorted(self._tools)]
            if tools:
                if any(not tool.get("id") or not tool["function"]["name"] for tool in tools):
                    raise StreamError("The stream tool identifiers are incomplete.")
                self._message["tool_calls"] = deepcopy(tools)
            self.value = {**deepcopy(self._metadata), "object": "chat.completion",
                          "choices": [{"index": 0, "message": deepcopy(self._message),
                                       "finish_reason": self._finish}], "usage": deepcopy(self._usage)}
            self.complete = True
            self.terminal = self._finish if self._finish in {"stop", "tool_calls", "length", "content_filter", "function_call"} else "unsupported_finish"
            return False
        try:
            value = json.loads(data, object_pairs_hook=_object,
                               parse_constant=lambda _: (_ for _ in ()).throw(StreamError("The stream contains non-finite JSON numbers.")))
        except (ValueError, TypeError) as exc:
            if isinstance(exc, StreamError):
                raise
            raise StreamError("The stream contains malformed JSON data.") from exc
        value = _mapping(value)
        if event == "error" or value.get("type") == "error" or value.get("error"):
            self.terminal = "error"
            raise StreamError("The provider reported an error inside the stream.", category="provider_error", field="event")
        try:
            if self.protocol == "chat_completions":
                return self._chat(value)
            return self._responses(value, event)
        except (KeyError, TypeError, AttributeError, IndexError) as exc:
            # Bounded R07 treatment for touched native containers. Preserve the
            # same rejected-stream settlement instead of leaking a Python error.
            raise StreamError("The stream contains an unsupported native container.") from exc

    def _chat(self, value: dict) -> bool:
        if value.get("object", "chat.completion.chunk") != "chat.completion.chunk":
            raise StreamError("The route did not return Chat Completions stream chunks.")
        for key in ("id", "model", "created"):
            if key in value and value[key] is not None:
                if ((key == "created" and (type(value[key]) is not int or value[key] < 0))
                        or (key != "created" and (not isinstance(value[key], str) or not value[key]))):
                    raise StreamError("The stream contains an invalid response identity.", category="identity_type", field=key)
                if key in self._metadata and self._metadata[key] != value[key]:
                    raise StreamError("The stream changed its response identity.", category="identity_conflict", field=key)
                self._metadata[key] = deepcopy(value[key])
        self._service(value)
        if value.get("usage") is not None:
            report = interpret_usage(self.protocol, value["usage"])
            self.usage_observations.append({"ordinal": self._ordinal, "usage": deepcopy(value["usage"])})
            key = accounting_fields(report.value) if report.value is not None else None
            if report.value is None or (self._usage_key is not None and self._usage_key != key):
                self._usage_invalid = True
                self.usage = Usage(None, "unknown", report.reason if report.value is None else "conflicting_aggregates")
            elif not self._usage_invalid:
                self.usage = report
            self._usage_key = key if self._usage_key is None else self._usage_key
            self._usage = deepcopy(self.usage.value)
        choices = value.get("choices")
        if not isinstance(choices, list) or len(choices) > 1:
            raise StreamError("The stream must contain a single choice.")
        if not choices:
            return False  # e.g. the optional final usage chunk
        choice = _mapping(choices[0])
        for key in ("message", "text", "content", "refusal", "tool_calls"):
            competing = choice.get(key)
            if key == "message" and isinstance(competing, dict):
                competing = {k: v for k, v in competing.items() if not (k == "role" and v == "assistant")
                             and v not in (None, "", [], {})}
            if competing not in (None, "", [], {}):
                raise StreamError("The choice contains competing assistant content.", category="competing_content", field="choice")
        if _index(choice.get("index")) != 0:
            raise StreamError("The stream must contain choice zero only.")
        delta = _mapping(choice.get("delta", {}))
        if self._finish is not None:
            raise StreamError("The stream contains a choice after its finish reason.")
        if any(key not in {"role", "content", "reasoning_content", "refusal", "tool_calls", "annotations"}
               and item is not None for key, item in delta.items()):
            raise StreamError("The stream contains an unsupported assistant delta.")
        role = delta.get("role")
        if role is not None and role != "assistant":
            raise StreamError("The stream returned an unexpected assistant role.")
        progress = False
        for field in ("content", "reasoning_content", "refusal"):
            if delta.get(field) is not None:
                fragment = _string(delta[field])
                self._message[field] = (self._message.get(field) or "") + fragment
                if field != "refusal":
                    progress |= bool(fragment.strip())
        if delta.get("annotations") is not None:
            if not isinstance(delta["annotations"], list):
                raise StreamError("The stream annotations are invalid.")
            self._message.setdefault("annotations", []).extend(deepcopy(delta["annotations"]))
        native_calls = delta.get("tool_calls")
        if native_calls is not None:
            if not isinstance(native_calls, list):
                raise StreamError("The stream tool calls are invalid.")
            for part in native_calls:
                part = _mapping(part)
                index = _index(part.get("index"))
                tool = self._tools.setdefault(index, {"type": "function", "function": {"name": "", "arguments": ""}})
                if part.get("type", "function") != "function":
                    raise StreamError("The stream contains an unsupported tool call.")
                if part.get("id") is not None:
                    call_id = _string(part["id"])
                    if "id" in tool and tool["id"] != call_id:
                        raise StreamError("The stream changed a tool call identifier.")
                    tool["id"] = call_id
                function = _mapping(part.get("function", {}))
                if any(key not in {"name", "arguments"} for key in function):
                    raise StreamError("The stream contains an unsupported function field.")
                for field in ("name", "arguments"):
                    if function.get(field) is not None:
                        fragment = _string(function[field])
                        tool["function"][field] += fragment
                        if field == "arguments":
                            progress |= bool(fragment.strip())
        finish = choice.get("finish_reason")
        if finish is not None:
            self._finish = _string(finish)
            if not self._finish:
                raise StreamError("The stream finish reason is empty.")
            if finish in {"stop", "tool_calls"} and choice.get("native_finish_reason", finish) not in {None, finish}:
                raise StreamError("The stream native finish reason contradicts completion.")
        return progress

    def _service(self, value):
        for key in ("service_tier", "system_fingerprint"):
            if key not in value:
                continue
            item = value[key]
            valid = isinstance(item, str) and bool(item)
            if key == "service_tier":
                valid = valid and item in {"auto", "default", "flex", "scale", "priority", "fast"}
            self._metadata[key] = item if valid else None
            self.service_observations.append({"ordinal": self._ordinal, "field": key,
                "status": "known" if valid else "unknown" if item is None else "unavailable"})

    def _responses(self, value: dict, event: str) -> bool:
        kind = _string(value.get("type"))
        if event and event != "message" and event != kind:
            raise StreamError("The SSE event name contradicts its response data.")
        if not kind.startswith("response."):
            raise StreamError("The route did not return Responses stream events.")
        sequence = value.get("sequence_number")
        if sequence is not None:
            sequence = _index(sequence)
            if sequence in self._sequence:
                if self._sequence[sequence] != value:
                    raise StreamError("The stream reused an event sequence with different data.")
                return False
            if sequence <= self._last_sequence:
                raise StreamError("The stream event sequence moved backwards.")
            self._sequence[sequence] = deepcopy(value)
            self._last_sequence = sequence
        if value.get("response_id") is not None:
            response_id = _string(value["response_id"])
            if not response_id or self._response_id not in (None, response_id):
                raise StreamError("The stream changed its response identifier.", category="identity_conflict", field="response")
            self._response_id = response_id
        response = value.get("response")
        if response is not None:
            response = _mapping(response)
            if response.get("error") or response.get("incomplete_details") or response.get("status") in {"failed", "incomplete", "cancelled"}:
                self.terminal = kind if kind in {"response.failed", "response.incomplete", "response.cancelled"} else "error"
                self.value = deepcopy(response)
                raise StreamError("The response observed an error or unsuccessful status.", category="provider_error", field="response")
            response_id = response.get("id")
            if response_id is not None:
                response_id = _string(response_id)
                if not response_id:
                    raise StreamError("The stream contains an empty response identifier.", category="identity_type", field="response")
                if self._response_id is not None and self._response_id != response_id:
                    raise StreamError("The stream changed its response identifier.")
                self._response_id = response_id
            for key in ("model", "created_at"):
                if response.get(key) is not None:
                    item = response[key]
                    if ((key == "model" and (not isinstance(item, str) or not item))
                            or (key == "created_at" and (type(item) is not int or item < 0))):
                        raise StreamError("The response identity is invalid.", category="identity_type", field="response")
                    if key in self._metadata and self._metadata[key] != item:
                        raise StreamError("The response identity changed.", category="identity_conflict", field="response")
                    self._metadata[key] = item
            self._service(response)
        if kind in {"response.failed", "response.incomplete", "response.cancelled"}:
            self.terminal = kind
            self.value = deepcopy(response)
            raise StreamError("The provider reported an unsuccessful response terminal.")
        if kind == "response.completed":
            if response is None or response.get("status") != "completed" or response.get("error") or response.get("incomplete_details"):
                self.terminal = kind
                raise StreamError("The completion event does not contain a completed response.")
            output = response.get("output")
            if not isinstance(output, list):
                raise StreamError("The completion event has no native output list.")
            for index, item in enumerate(output):
                self._check_item(index, _mapping(item), phase="terminal")
                list(self._item_pieces(index, item))  # validate even terminal-only parts
            if any(index >= len(output) for index in self._items):
                raise StreamError("The completed response omitted an announced output item.")
            for key in self._pieces:
                index = key[0]
                if index >= len(output):
                    raise StreamError("The completed response omitted streamed content.")
                final = self._piece_from_item(output[index], key)
                self._check_piece(key, final)
            for (index, group, part), observed in self._done_parts.items():
                try:
                    final = output[index][group][part]
                except (KeyError, IndexError, TypeError) as exc:
                    raise StreamError("The completed response omitted a completed part.", category="content_conflict", field="part") from exc
                for key in ("type", "text", "refusal", "annotations"):
                    if key in observed and final.get(key) != observed[key]:
                        raise StreamError("The completed response changed a completed part.", category="content_conflict", field="part")
            for (index, part, ordinal), annotation in self._annotations.items():
                try:
                    final = output[index]["content"][part]["annotations"][ordinal]
                except (KeyError, IndexError, TypeError) as exc:
                    raise StreamError("The completed response omitted an annotation.") from exc
                if final != annotation:
                    raise StreamError("The completed response changed an annotation.")
            self.value = deepcopy(response)
            self.value.update({key: deepcopy(item) for key, item in self._metadata.items() if key in {"service_tier", "system_fingerprint"}})
            self.usage = interpret_usage(self.protocol, response.get("usage"))
            self.usage_observations.append({"ordinal": self._ordinal, "usage": deepcopy(response.get("usage"))})
            self.complete, self.terminal = True, kind
            return False
        if kind in {"response.output_item.added", "response.output_item.done"}:
            index = _index(value.get("output_index"))
            item = _mapping(value.get("item"))
            self._check_item(index, item, phase="done" if kind.endswith(".done") else "progress")
            self._items.setdefault(index, deepcopy(item))
            for key, full in self._item_pieces(index, item):
                self._check_piece(key, full) if kind.endswith(".done") else self._check_initial_piece(key, full)
            if kind.endswith(".done"):
                if index in self._done_items and self._done_items[index] != item:
                    raise StreamError("The stream changed a completed output item.")
                self._done_items[index] = deepcopy(item)
                for key in self._pieces:
                    if key[0] == index:
                        self._check_piece(key, self._piece_from_item(item, key))
                # Some routes emit only the completed item, without deltas.
                # Count its actual unseen content, never its repeated snapshot.
                progress = False
                for key, full in self._item_pieces(index, item):
                    self._check_piece(key, full)
                    progress |= bool(full[len(self._pieces.get(key, "")):].strip())
                    self._pieces[key] = full
                    self._done_pieces.add(key)
                return progress
            return False
        if kind in {"response.content_part.added", "response.content_part.done", "response.reasoning_summary_part.added", "response.reasoning_summary_part.done"}:
            summary = kind.startswith("response.reasoning_summary_part.")
            index = self._bind_content(value, "reasoning" if summary else None)
            part_index = _index(value.get("summary_index" if summary else "content_index"))
            part = _mapping(value.get("part"))
            item_type = self._items[index].get("type", "message")
            if not summary:
                item_type = "reasoning" if part.get("type") == "reasoning_text" else "message"
                self._bind_content(value, item_type)
            field = "summary" if summary else "reasoning" if item_type == "reasoning" else "text"
            expected = "summary_text" if summary else "reasoning_text" if item_type == "reasoning" else "output_text"
            if part.get("type") != expected:
                raise StreamError("The stream contains an unsupported or refused content part.", category="unsupported_content", field="part")
            key = (index, field, part_index)
            text = _string(part.get("text"))
            unseen = ""
            if kind.endswith(".done"):
                self._check_piece(key, text)
                unseen = text[len(self._pieces.get(key, "")):]
                self._pieces[key] = text
                self._done_pieces.add(key)
                part_key = (index, "summary" if summary else "content", part_index)
                if part_key in self._done_parts and self._done_parts[part_key] != part:
                    raise StreamError("The completed part changed.")
                self._done_parts[part_key] = deepcopy(part)
            else:
                self._check_initial_piece(key, text)
            return bool(unseen.strip())
        if kind in {"response.refusal.delta", "response.refusal.done"}:
            raise StreamError("The stream observed a refusal.", category="refusal", field="part")
        if kind == "response.output_text.annotation.added":
            index = self._bind_content(value, "message")
            key = (index, _index(value.get("content_index")), _index(value.get("annotation_index")))
            annotation = value.get("annotation")
            if annotation is not None:
                _mapping(annotation)
            if key in self._annotations and self._annotations[key] != annotation:
                raise StreamError("The stream changed an annotation.")
            self._annotations[key] = deepcopy(annotation)
            return False
        fields = {
            "response.output_text": ("text", "content_index", "text"),
            "response.reasoning_text": ("reasoning", "content_index", "text"),
            "response.reasoning_summary_text": ("summary", "summary_index", "text"),
            "response.function_call_arguments": ("arguments", None, "arguments"),
            "response.custom_tool_call_input": ("input", None, "input"),
        }
        stem, _, suffix = kind.rpartition(".")
        if stem in fields and suffix in {"delta", "done"}:
            field, part_key, full_field = fields[stem]
            index = _index(value.get("output_index"))
            expected_type = {"text": "message", "reasoning": "reasoning", "summary": "reasoning",
                             "arguments": "function_call", "input": "custom_tool_call"}[field]
            self._bind_content(value, expected_type)
            part = _index(value.get(part_key)) if part_key else None
            key = (index, field, part)
            if suffix == "delta":
                if key in self._done_pieces or index in self._done_items:
                    raise StreamError("The stream added content after its completed item.")
                fragment = _string(value.get("delta"))
                self._pieces[key] = self._pieces.get(key, "") + fragment
                return bool(fragment.strip())
            full = _string(value.get(full_field))
            self._check_piece(key, full)
            unseen = full[len(self._pieces.get(key, "")):]
            self._pieces[key] = full
            self._done_pieces.add(key)
            return bool(unseen.strip())  # only a previously unseen suffix counts
        # Finite official observation-only families. No output/text/arguments
        # are discarded by a general event-name or object-shape heuristic.
        if kind in {"response.created", "response.in_progress", "response.queued"}:
            if response is None:
                raise StreamError("The lifecycle event has no response object.")
            output = response.get("output", [])
            if not isinstance(output, list):
                raise StreamError("The lifecycle output must be a list.")
            for index, item in enumerate(output):
                self._check_item(index, _mapping(item))
                self._items.setdefault(index, deepcopy(item))
                for key, full in self._item_pieces(index, item):
                    self._check_initial_piece(key, full)
            return False
        if kind == "response.compaction.compacting":
            self._bind_content(value, "compaction")
            return False
        raise StreamError("The stream contains an unsupported semantic event.", category="unsupported_event", field="event")

    def _bind_content(self, value, expected_type):
        index = _index(value.get("output_index"))
        previous = self._items.setdefault(index, {})
        if expected_type is not None:
            if previous.get("type", expected_type) != expected_type:
                raise StreamError("The stream content contradicts its output item type.")
            previous["type"] = expected_type
        if value.get("item_id") is not None:
            item_id = _string(value["item_id"])
            if not item_id or previous.get("id", item_id) != item_id:
                raise StreamError("The stream changed the content's output item.", category="identity_conflict", field="item")
            previous["id"] = item_id
        for field in ("call_id", "name"):
            if value.get(field) is not None:
                item = _string(value[field])
                if not item or previous.get(field, item) != item:
                    raise StreamError("The stream changed its function attribution.", category="identity_conflict", field="item")
                previous[field] = item
        return index

    def _check_initial_piece(self, key, text):
        seen = self._pieces.get(key, "")
        if not seen.startswith(text):
            if key in self._done_pieces or not text.startswith(seen):
                raise StreamError("An announced part contradicts observed content.")
            self._pieces[key] = text

    def _check_item(self, index: int, item: dict, *, phase="progress"):
        _string(item.get("type"))
        validate_response_item_state(item, final=phase != "progress")
        if item["type"] in ("function_call", "message", "reasoning"):
            status = item.get("status")
            if self._item_statuses.get(index) == "completed" and status == "in_progress":
                raise StreamError("The output item's completed state regressed.",
                                  category="content_conflict", field="item")
            # Absence cannot forget a prior completion. Done itself marks the
            # boundary; added/lifecycle in_progress can legitimately complete.
            if phase != "progress" or status == "completed":
                self._item_statuses[index] = "completed"
            elif status is not None:
                self._item_statuses[index] = status
        previous = self._items.get(index, {})
        if item.get("id"):
            if any(other != index and old.get("id") == item["id"] for other, old in self._items.items()):
                raise StreamError("The stream reused an output item identifier.")
        for field in ("id", "type", "call_id", "name"):
            if field in previous and previous[field] != item.get(field):
                raise StreamError("The stream changed an output item's identity.")
        if phase == "terminal" and index in self._done_items:
            done = self._done_items[index]
            for field in ("id", "type", "call_id", "name", "arguments", "input", "content", "summary", "encrypted_content"):
                if field in done and done[field] != item.get(field):
                    raise StreamError("The completed response contradicts a completed output item.")

    def _check_piece(self, key: tuple, full: str):
        full = _string(full)
        seen = self._pieces.get(key, "")
        if (key in self._done_pieces and full != seen) or not full.startswith(seen):
            raise StreamError("The completed content contradicts its streamed content.")

    @staticmethod
    def _item_pieces(index: int, item: dict):
        kind = item.get("type")
        if kind in {"function_call", "custom_tool_call"}:
            field = "arguments" if kind == "function_call" else "input"
            if field in item:
                yield (index, field, None), _string(item[field])
        if kind in {"message", "reasoning"}:
            content = item.get("content")
            if content is None:
                content = []
            if not isinstance(content, list):
                raise StreamError("The stream output content is not a list.")
            for part, value in enumerate(content):
                value = _mapping(value)
                if value.get("type") in {"output_text", "reasoning_text"}:
                    if value["type"] != ("output_text" if kind == "message" else "reasoning_text"):
                        raise StreamError("The output part contradicts its item type.")
                    field = "text" if kind == "message" else "reasoning"
                    yield (index, field, part), _string(value.get("text"))
                else:
                    raise StreamError("The stream contains an unsupported or refused content part.", category="unsupported_content", field="part")
        if kind == "reasoning":
            summary = item.get("summary")
            if summary is None:
                summary = []
            if not isinstance(summary, list):
                raise StreamError("The stream reasoning summary is not a list.")
            for part, value in enumerate(summary):
                value = _mapping(value)
                if value.get("type") == "summary_text":
                    yield (index, "summary", part), _string(value.get("text"))
                else:
                    raise StreamError("The stream contains an unsupported summary part.", category="unsupported_content", field="summary")

    @staticmethod
    def _piece_from_item(item: dict, key: tuple) -> str:
        _, field, part = key
        try:
            if field in {"arguments", "input"}:
                return _string(item[field])
            parts = item["summary" if field == "summary" else "content"]
            return _string(parts[part]["text"])
        except (KeyError, IndexError, TypeError) as exc:
            raise StreamError("The completed response omitted streamed content.") from exc

    def finish_received(self) -> dict:
        """Validate the entire received prefix at terminal stop or natural EOF.

        A recognized comment prefix cannot become data, so it needs no trailing
        newline. Every received UTF-8 character must still be complete. Pending
        data and other unfinished lines are not silently discarded. This does
        not assert HTTP EOF or read bytes beyond the caller's receive boundary.
        """
        self._ended = True
        try:
            self._utf8.decode(b"", final=True)
        except UnicodeError as exc:
            raise StreamError("The stream ended inside a UTF-8 character.", stage="finish", ordinal=self._ordinal) from exc
        if not self.complete:
            raise StreamError("The stream ended before its required terminal event.", stage="finish", ordinal=self._ordinal)
        if self._data or (self._line and self._line[0] != ":"):
            raise StreamError("The stream ended inside a trailing SSE event.", stage="finish", ordinal=self._ordinal)
        return deepcopy(self.value)

    def finish(self) -> dict:
        """Natural EOF uses the same rule; it cannot manufacture a terminal."""
        return self.finish_received()
