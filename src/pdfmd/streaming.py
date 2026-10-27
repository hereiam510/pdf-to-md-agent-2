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


class StreamError(ValueError):
    """Safe local diagnosis. Never include arbitrary upstream error text."""


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
        self._sequence: dict[int, dict] = {}
        self._last_sequence = -1
        self._items: dict[int, dict] = {}
        self._done_items: dict[int, dict] = {}
        self._pieces: dict[tuple, str] = {}
        self._done_pieces: set[tuple] = set()
        self._response_id: str | None = None

    def feed(self, chunk: bytes) -> FeedResult:
        """Consume complete SSE frames; incomplete frames never imply progress.

        Comments, lifecycle events, empty/whitespace deltas and metadata do not
        reset a progress clock. Whitespace is still preserved in assembled data.
        Equal text deltas remain separate additions, not inferred duplicates.
        """
        self.last_feed = FeedResult()
        if self._ended:
            raise StreamError("The stream decoder has already reached EOF.")
        try:
            text = self._utf8.decode(chunk)
        except UnicodeError as exc:
            raise StreamError("The stream is not valid UTF-8.") from exc
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
                except StreamError:
                    # Earlier valid events in this same HTTP chunk are still observed
                    # progress even when a later frame rejects the whole response.
                    self.last_feed = FeedResult(events, progress, self.terminal)
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
            self.complete, self.terminal = True, self._finish
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
            raise StreamError("The provider reported an error inside the stream.")
        if self.protocol == "chat_completions":
            return self._chat(value)
        return self._responses(value, event)

    def _chat(self, value: dict) -> bool:
        if value.get("object", "chat.completion.chunk") != "chat.completion.chunk":
            raise StreamError("The route did not return Chat Completions stream chunks.")
        for key in ("id", "model", "created", "system_fingerprint", "service_tier"):
            if key in value and value[key] is not None:
                if key in self._metadata and self._metadata[key] != value[key]:
                    raise StreamError("The stream changed its response identity or metadata.")
                self._metadata[key] = deepcopy(value[key])
        if value.get("usage") is not None:
            self._usage = deepcopy(_mapping(value["usage"]))
        choices = value.get("choices")
        if not isinstance(choices, list) or len(choices) > 1:
            raise StreamError("The stream must contain a single choice.")
        if not choices:
            return False  # e.g. the optional final usage chunk
        choice = _mapping(choices[0])
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
        response = value.get("response")
        if response is not None:
            response = _mapping(response)
            response_id = response.get("id")
            if response_id is not None:
                response_id = _string(response_id)
                if self._response_id is not None and self._response_id != response_id:
                    raise StreamError("The stream changed its response identifier.")
                self._response_id = response_id
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
                self._check_item(index, _mapping(item), terminal=True)
            if any(index >= len(output) for index in self._items):
                raise StreamError("The completed response omitted an announced output item.")
            for key in self._pieces:
                index = key[0]
                if index >= len(output):
                    raise StreamError("The completed response omitted streamed content.")
                final = self._piece_from_item(output[index], key)
                self._check_piece(key, final)
            self.value = deepcopy(response)
            self.complete, self.terminal = True, kind
            return False
        if kind in {"response.output_item.added", "response.output_item.done"}:
            index = _index(value.get("output_index"))
            item = _mapping(value.get("item"))
            self._check_item(index, item)
            self._items.setdefault(index, deepcopy(item))
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
            previous = self._items.setdefault(index, {})
            if previous.get("type", expected_type) != expected_type:
                raise StreamError("The stream content contradicts its output item type.")
            previous["type"] = expected_type
            item_id = value.get("item_id")
            if item_id is not None:
                item_id = _string(item_id)
                if previous.get("id", item_id) != item_id:
                    raise StreamError("The stream changed the content's output item.")
                previous["id"] = item_id
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
        # Lifecycle, content-part announcements and provider extension events
        # remain in the caller's raw record but do not establish generation.
        return False

    def _check_item(self, index: int, item: dict, *, terminal=False):
        _string(item.get("type"))
        previous = self._items.get(index, {})
        for field in ("id", "type", "call_id", "name"):
            if field in previous and previous[field] != item.get(field):
                raise StreamError("The stream changed an output item's identity.")
        if terminal and index in self._done_items:
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
            content = item.get("content") or []
            if not isinstance(content, list):
                raise StreamError("The stream output content is not a list.")
            for part, value in enumerate(content):
                value = _mapping(value)
                if value.get("type") in {"output_text", "reasoning_text"}:
                    field = "text" if kind == "message" else "reasoning"
                    yield (index, field, part), _string(value.get("text"))
        if kind == "reasoning":
            summary = item.get("summary") or []
            if not isinstance(summary, list):
                raise StreamError("The stream reasoning summary is not a list.")
            for part, value in enumerate(summary):
                value = _mapping(value)
                if value.get("type") == "summary_text":
                    yield (index, "summary", part), _string(value.get("text"))

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

    def finish(self) -> dict:
        """EOF never dispatches an unfinished SSE frame or manufactures a result."""
        self._ended = True
        try:
            self._utf8.decode(b"", final=True)
        except UnicodeError as exc:
            raise StreamError("The stream ended inside a UTF-8 character.") from exc
        if not self.complete:
            raise StreamError("The stream ended before its required terminal event.")
        if self._line or self._data:
            raise StreamError("The stream ended inside a trailing SSE event.")
        return deepcopy(self.value)
