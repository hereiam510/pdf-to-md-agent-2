"""Bounded bad-resource work and automatic repair; no latency/route claim."""
from copy import deepcopy
import gzip
from types import SimpleNamespace
import zlib

import pytest

from pdfmd.context import Context
from pdfmd.nexus import Nexus
import pdfmd.request_estimation as estimation
from pdfmd.schema import Route
from pdfmd.storage import Store, encode
from pdfmd.tools import Dispatcher
import pdfmd.usage_anchoring as shadow
from pdfmd.working_context import inspect
from tests.engine.context.test_context_admission import protocol_job, state_for


def clear_counters():
    estimation.counter.cache_clear()
    estimation.text_cost.cache_clear()
    shadow.counters.cache_clear()
    for module, name in ((estimation, "_counter_from_resource"), (shadow, "_counters_from_resource")):
        cached = getattr(module, name, None)
        if cached is not None:
            cached.cache_clear()


class ResourceState(SimpleNamespace):
    def __repr__(self):
        return f"ResourceState(reads={self.reads}, decompressions={self.decompressions})"


@pytest.fixture
def resource(monkeypatch):
    import socket
    import tiktoken.load
    valid = estimation.files("pdfmd").joinpath("data/o200k_base.tiktoken.gz").read_bytes()
    invalid_deflate = bytearray(gzip.compress(b"invalid vocabulary"))
    invalid_deflate[10] = 7
    state = ResourceState(valid=valid, current={"production": valid, "shadow": valid},
                            reads={"production": 0, "shadow": 0}, decompressions=0,
                            damage={"hash": gzip.compress(b"invalid vocabulary"), "header": b"not gzip",
                                    "truncated": valid[:-4], "deflate": bytes(invalid_deflate)})
    original = gzip.decompress

    def decompress(data):
        state.decompressions += 1
        return original(data)

    def reader(owner):
        def read():
            state.reads[owner] += 1
            value = state.current[owner]
            if isinstance(value, Exception):
                raise value
            return value
        # A Traversable-style resource deliberately has no stat/mtime interface.
        return lambda _: SimpleNamespace(joinpath=lambda _: SimpleNamespace(read_bytes=read))

    def no_network(*args, **kwargs):
        pytest.fail("Counter recovery must not download or call a provider")

    clear_counters()
    monkeypatch.setattr(estimation, "files", reader("production"))
    monkeypatch.setattr(shadow, "files", reader("shadow"))
    monkeypatch.setattr(gzip, "decompress", decompress)
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(tiktoken.load, "read_file", no_network)
    yield state
    clear_counters()


def load(owner):
    return (estimation.counter(),) if owner == "production" else shadow.counters()


@pytest.mark.parametrize("owner", ["production", "shadow"])
@pytest.mark.parametrize("damage", ["hash", "header", "truncated", "deflate"])
def test_identical_invalid_bytes_reuse_validation_and_repair_automatically(resource, owner, damage):
    expected = [counter.encode_ordinary("保留 μg hello world") for counter in load(owner)]
    clear_counters()
    resource.decompressions = 0
    resource.reads[owner] = 0
    resource.current[owner] = resource.damage[damage]
    for _ in range(3):
        with pytest.raises((ValueError, OSError, EOFError, zlib.error)):
            load(owner)
    assert resource.reads[owner] == 3  # Rereads are necessary to detect repair.
    assert resource.decompressions == 1
    resource.current[owner] = resource.valid
    assert [counter.encode_ordinary("保留 μg hello world") for counter in load(owner)] == expected
    assert resource.decompressions == 2 and resource.reads[owner] == 4
    assert [counter.encode_ordinary("保留 μg hello world") for counter in load(owner)] == expected
    assert resource.decompressions == 2 and resource.reads[owner] == 4  # Warm success remains cached.


@pytest.mark.parametrize("owner", ["production", "shadow"])
def test_changed_bad_versions_evict_the_previous_single_entry(resource, owner):
    first = resource.damage["hash"]
    second = gzip.compress(b"a different invalid vocabulary")
    for content in (first, first, second, second, first):
        resource.current[owner] = content
        with pytest.raises(ValueError):
            load(owner)
    assert resource.reads[owner] == 5 and resource.decompressions == 3
    resource.current[owner] = resource.valid
    assert load(owner)[0].encode_ordinary("hello world") == [24912, 2375]


@pytest.mark.parametrize("owner", ["production", "shadow"])
@pytest.mark.parametrize("error", [FileNotFoundError, PermissionError])
def test_transient_reads_do_not_poison_recovery(resource, owner, error):
    resource.current[owner] = error("temporarily unreadable")
    with pytest.raises(error):
        load(owner)
    assert resource.decompressions == 0
    resource.current[owner] = resource.valid
    assert load(owner)[0].encode_ordinary("hello world") == [24912, 2375]
    assert resource.reads[owner] == 2 and resource.decompressions == 1


@pytest.mark.parametrize("owner", ["production", "shadow"])
@pytest.mark.parametrize("error", [RuntimeError, ValueError])
def test_constructor_programming_error_is_neither_cached_nor_reclassified(resource, monkeypatch, owner, error):
    import tiktoken
    original = tiktoken.Encoding
    calls = []

    def broken(*args, **kwargs):
        calls.append(True)
        raise error("unrelated constructor bug")

    monkeypatch.setattr(tiktoken, "Encoding", broken)
    for _ in range(2):
        with pytest.raises(error, match="unrelated constructor bug"):
            load(owner)
    assert len(calls) == 2 and resource.decompressions == 2
    monkeypatch.setattr(tiktoken, "Encoding", original)
    assert load(owner)[0].encode_ordinary("hello world") == [24912, 2375]


@pytest.mark.parametrize("owner", ["production", "shadow"])
def test_version_failure_can_recover_without_resource_poisoning(resource, monkeypatch, owner):
    import tiktoken
    original = tiktoken.__version__
    monkeypatch.setattr(tiktoken, "__version__", "unsupported")
    with pytest.raises(ValueError):
        load(owner)
    assert resource.reads[owner] == 0 and resource.decompressions == 0
    monkeypatch.setattr(tiktoken, "__version__", original)
    assert load(owner)[0].encode_ordinary("hello world") == [24912, 2375]


def test_shadow_recipe_failure_does_not_latch(resource, monkeypatch):
    original = shadow.PATTERN_DIGESTS
    monkeypatch.setattr(shadow, "PATTERN_DIGESTS", ("wrong", "wrong"))
    with pytest.raises(ValueError, match="recipe mismatch"):
        shadow.counters()
    assert resource.reads["shadow"] == 0 and resource.decompressions == 0
    monkeypatch.setattr(shadow, "PATTERN_DIGESTS", original)
    assert shadow.counters()[0].encode_ordinary("hello world") == [24912, 2375]


def test_owner_failure_caches_are_independent(resource):
    for owner in ("shadow", "production"):
        resource.current[owner] = resource.damage["hash"]
        for _ in range(3):
            with pytest.raises(ValueError):
                load(owner)
    assert resource.decompressions == 2  # One independently owned result per arm.
    resource.current["production"] = resource.valid
    assert estimation.counter().encode_ordinary("hello world") == [24912, 2375]
    assert resource.decompressions == 3
    with pytest.raises(ValueError):
        shadow.counters()
    assert resource.decompressions == 3
    resource.current["shadow"] = resource.valid
    assert shadow.counters()[0].encode_ordinary("hello world") == [24912, 2375]
    assert resource.decompressions == 4


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_complete_preparation_fallback_repair_and_frozen_reopen(resource, setup, protocol):
    store, initial = setup
    job = protocol_job(store, initial, protocol)
    state = state_for(job, [])
    before_state = deepcopy(state)
    context = Context(store, Dispatcher(store))
    expected_payload, expected_capacity = context.normal(job, state)
    clear_counters()
    resource.decompressions = 0
    resource.reads["production"] = 0
    resource.current["production"] = resource.damage["hash"]
    payload, capacity = context.normal(job, state)
    assert resource.reads["production"] > 1 and resource.decompressions == 1
    assert capacity["fallback"] == "counter_unavailable_or_invalid"
    assert capacity["method"] == "utf8_fallback_v1" and capacity["text_tokens"] is None
    explicit = estimation.estimate(payload, Route.model_validate({**job["route"], "estimation_profile": "utf8_fallback_v1"}))
    assert {k: capacity[k] for k in explicit} == {**explicit, "fallback": "counter_unavailable_or_invalid"}
    request = Nexus(store, lambda _: pytest.fail("Preparation must not send")).freeze(
        job["id"], "bad-counter-frozen", payload, "normal", {"capacity": capacity})
    frozen = store.bytes(request["payload_ref"], job["id"])
    source = store.bytes(job["source_ref"], job["id"])
    resource.current["production"] = resource.valid
    reopened = Store(store.root)
    current = Context(reopened, Dispatcher(reopened))
    repaired_payload, repaired_capacity = current.normal(job, state)
    assert encode(repaired_payload) == encode(expected_payload) and repaired_capacity == expected_capacity
    assert state == before_state and resource.decompressions == 2
    result = inspect(current, reopened.get("request", request["id"]), job)
    assert result["recorded_capacity"] == capacity
    assert result["current_input"]["fallback"] is None
    assert result["current_input"]["assessment"] == "current_method_on_unchanged_frozen_payload"
    assert reopened.get("request", request["id"]) == request
    assert reopened.bytes(request["payload_ref"], job["id"]) == frozen
    assert reopened.bytes(job["source_ref"], job["id"]) == source
    assert reopened.get("job", job["id"]) == job


def test_explicit_fallback_never_reads_or_repairs_resources(resource, route):
    from pdfmd.nexus import make_payload
    selected = Route.model_validate({**route, "estimation_profile": "utf8_fallback_v1"})
    resource.current["production"] = PermissionError("must not be read")
    result = estimation.estimate(make_payload(selected, "source", [], []), selected)
    assert result["fallback"] == "explicit_route_fallback"
    assert resource.reads["production"] == 0 and resource.decompressions == 0
