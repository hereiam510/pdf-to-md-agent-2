"""Offline complete-native-request proxies, not provider usage or token bounds.

There is deliberately no model-alias lookup or network-capable vocabulary loader.
Context owns admission policy; this module only supplies its common measurement.
"""
from __future__ import annotations

import base64
from functools import lru_cache
import gzip
import hashlib
from importlib.resources import files
import zlib

from .nexus import StopRun
from .schema import Route
from .storage import encode


VOCAB_SHA256 = "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"
COUNT_CHARS = 8192
# Upstream tiktoken 0.14.0, tiktoken_ext/openai_public.py:o200k_base.
# Ordinary text includes literal special-token spellings without interpreting them.
PATTERN = "|".join([
    r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]*[\p{Ll}\p{Lm}\p{Lo}\p{M}]+(?i:'s|'t|'re|'ve|'m|'ll|'d)?",
    r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]+[\p{Ll}\p{Lm}\p{Lo}\p{M}]*(?i:'s|'t|'re|'ve|'m|'ll|'d)?",
    r"\p{N}{1,3}", r" ?[^\s\p{L}\p{N}]+[\r\n/]*", r"\s*[\r\n]+", r"\s+(?!\S)", r"\s+",
])


@lru_cache(maxsize=1)
def counter():
    import tiktoken

    if tiktoken.__version__ != "0.14.0":
        raise ValueError("The installed counter differs from the selected version.")
    compressed = files("pdfmd").joinpath("data/o200k_base.tiktoken.gz").read_bytes()
    try:
        data = gzip.decompress(compressed)
    except zlib.error as exc:
        # Normalize only the decompressor's invalid-data error. Other expected
        # resource failures already reach estimate's explicit offline fallback.
        raise ValueError("Bundled counter vocabulary has invalid compressed data.") from exc
    if hashlib.sha256(data).hexdigest() != VOCAB_SHA256:
        raise ValueError("Bundled counter vocabulary failed its SHA-256 check.")
    ranks = {base64.b64decode(token): int(rank) for token, rank in (line.split() for line in data.splitlines())}
    return tiktoken.Encoding("pdfmd_o200k_ordinary_v1", pat_str=PATTERN, mergeable_ranks=ranks, special_tokens={})


@lru_cache(maxsize=512)
def text_cost(text: str) -> int:
    # Bounded small pieces, never a disk cache or an entire growing history.
    return len(counter().encode_ordinary(text))


def estimate(payload: dict, route: Route) -> dict:
    if route.protocol not in {"chat_completions", "responses"}:
        raise StopRun("capacity_configuration", "This protocol has no supported local request estimator.")
    expected = "messages" if route.protocol == "chat_completions" else "input"
    other = "input" if expected == "messages" else "messages"
    if expected not in payload or other in payload or payload.get("model") != route.model:
        raise StopRun("capacity_configuration", "The native payload does not match the selected route/protocol; no capacity estimate is available.")
    images = 0

    def walk(value):
        nonlocal images
        if isinstance(value, dict):
            kind = value.get("type", "")
            if isinstance(kind, str) and kind in {"image_url", "input_image"}:
                images += 1
                return {"type": kind, "image": "[native image charged separately]"}
            if isinstance(kind, str) and kind in {"input_audio", "audio", "audio_url", "input_video", "video", "input_file", "file", "image"}:
                raise StopRun("capacity_configuration", "This native modality has no supported local cost rule. Preserve the content and configure an applicable estimator before sending.")
            return {key: walk(item) for key, item in value.items()}
        if isinstance(value, list):
            return [walk(item) for item in value]
        return value

    wire = encode(payload)
    textual = encode(walk(payload))
    if images and route.image_tokens is None:
        raise StopRun("capacity_configuration", "Configure a conservative per-image token allowance for this route before sending pixels.")
    fallback = None
    if route.estimation_profile == "utf8_fallback_v1":
        fallback = "explicit_route_fallback"
    try:
        if fallback:
            base = len(textual)
        else:
            text = textual.decode("utf-8")
            # Artificial boundaries make this an approximate request proxy.
            # All characters are counted exactly once. This avoids quadratic
            # BPE work on unbroken/repetitive arguments without truncation.
            base = sum(text_cost(text[start:start + COUNT_CHARS]) for start in range(0, len(text), COUNT_CHARS))
    except (ImportError, OSError, ValueError, EOFError):
        fallback = "counter_unavailable_or_invalid"
        base = len(textual)
    margin = 0 if fallback else (base + 3) // 4
    image_cost = images * (route.image_tokens or 0)
    point = base + image_cost
    total = point + margin + 1024
    method = "utf8_fallback_v1" if fallback else "o200k_native_json_proxy_v1"
    return {"method": method, "method_version": 1, "counter_version": None if fallback else "tiktoken-0.14.0",
            "vocabulary_sha256": None if fallback else VOCAB_SHA256,
            "scope": "complete_native_json_proxy_not_provider_token_count",
            "calibration": "not_a_route_wide_calibration_or_bound",
            "route_identity": hashlib.sha256(encode({key: route.model_dump()[key] for key in ("endpoint", "model", "protocol", "parameters")})).hexdigest(),
            "protocol": route.protocol, "fallback": fallback,
            "request_bytes": len(wire), "request_sha256": hashlib.sha256(wire).hexdigest(),
            "text_proxy_bytes": len(textual), "text_tokens": None if fallback else base,
            "text_counting": "utf8_bytes" if fallback else "ordinary_bpe_chunks_8192_unicode_characters",
            "text_proxy_cost": base, "unreserved_estimate": point,
            "safety_margin_tokens": margin, "native_overhead_reserve": 1024,
            "images": images, "image_allowance": route.image_tokens, "image_allowance_cost": image_cost,
            "image_rule": "configured_per_native_image_not_measured_cost",
            "input_estimate": total, "output_reserve": route.output_tokens,
            "capacity": route.context_tokens, "capacity_basis": "configured_not_discovered_route_limit",
            "fits": total + route.output_tokens <= route.context_tokens}
