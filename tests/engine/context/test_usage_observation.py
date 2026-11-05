"""Offline normal-entry-point equivalence; no provider or historical stores."""
from copy import deepcopy
from hashlib import sha256
import json
from itertools import count
import os
from pathlib import Path
import random
import shutil
from time import perf_counter

import httpx
import pytest

from pdfmd.context import Context
from pdfmd.nexus import Nexus, StopRun
from pdfmd.runtime import Runtime
from pdfmd.storage import Store, encode
from pdfmd.usage_anchoring import (KIMI_PATTERN, PATTERN_DIGESTS, RECIPE, counters, digest,
                                  normalized_input, price, projection)
from pdfmd.usage_observation import ObservationProfile, Opportunity, UsageObserver
from pdfmd.working_context import inspect as inspect_context
from tests.engine.execution.test_runtime import response, tool, transport_for
from tests.engine.transport.test_response_repairs import native


def initial(job):
    return {"job": job["id"], "seq": 0, "revision": 0, "history": [], "handoff": None,
            "notes": "", "released": [], "pinned": [], "terminal": False}


def profile(job):
    return ObservationProfile(digest(job["route"]), "Synthetic fixture: input main count includes cached input once")


def protocol_job(store, job, protocol):
    return store.update_job(job["id"], route={**job["route"], "protocol": protocol,
        "endpoint": "http://127.0.0.1/v1/" + ("responses" if protocol == "responses" else "chat/completions")})


def seed(store, job, *, large=False, missing=False, image=False):
    size = 180000 if large else 120
    body = "".join(random.Random(37).choices("abcdefghijklmnopqrstuvwxyz0123456789", k=size))
    ref = store.blob(job["id"], "evidence", {"source": "synthetic", "text": body,
        "warnings": ["Preserve warning"], "coverage": {"complete": True}})["ref"]
    protocol = job["route"]["protocol"]
    value = native(protocol, tool("render_page", {"page": 1, "dpi": 72}, "read") if image
                   else tool("read_evidence", {"ref": ref}, "read"))
    value["usage"] = (None if missing else ({"prompt_tokens": 8000, "completion_tokens": 30,
        "total_tokens": 8030, "prompt_tokens_details": {"cached_tokens": 3000},
        "completion_tokens_details": {"reasoning_tokens": 20}} if protocol == "chat_completions" else
        {"input_tokens": 8000, "output_tokens": 30, "total_tokens": 8030, "input_tokens_details": {"cached_tokens": 3000}}))
    runtime = Runtime(store, Nexus(store, lambda _: "synthetic", httpx.MockTransport(lambda _: httpx.Response(200, json=value))))
    state = initial(job)
    state.update(runtime.prepare(state))
    runtime.model(state)
    state.update(runtime.tools(state))
    runtime.close()
    return state


def save_measurement(name, value):
    root = os.environ.get("PDFMD_OBSERVER_EVIDENCE")
    if root:
        target = Path(root) / "measurements"
        target.mkdir(parents=True, exist_ok=True)
        (target / (name + ".json")).write_bytes(encode(value))


def fail(*args, **kwargs):
    raise OSError("injected observer-only fault")


def ordinary_records(store):
    # Runtime preparation should only add the same request/blob/event facts.
    # Blob IDs are random, compare bodies and request metadata by content below.
    return {kind: store.records(kind) for kind in ("operation", "attempt", "version", "context_commit")}


@pytest.mark.parametrize("large", [False, True], ids=["unchanged", "large-deferral"])
@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("fault", [None, "counter", "usage", "write"], ids=["on", "counter-fault", "usage-fault", "write-fault"])
def test_paired_preparation_equivalence(setup, tmp_path, monkeypatch, large, fault, protocol):
    store, job = setup
    job = protocol_job(store, job, protocol)
    if large:
        job = store.update_job(job["id"], route={**job["route"], "context_tokens": 18000})
    state = seed(store, job, large=large)
    roots = [tmp_path / "off", tmp_path / "on"]
    for root in roots:
        shutil.copytree(store.root, root)
    off, on = [Store(root) for root in roots]
    observer = UsageObserver(on, profile=profile(job))
    serialized_forms = []
    observe_form = Opportunity.observe
    def track_serialization(opportunity, role, payload, capacity):
        raw = encode(payload)
        serialized_forms.append((role, sha256(raw).hexdigest(), len(raw)))
        return observe_form(opportunity, role, payload, capacity)
    monkeypatch.setattr(Opportunity, "observe", track_serialization)
    if fault == "counter":
        monkeypatch.setattr("pdfmd.usage_anchoring.counters", fail)
    elif fault == "usage":
        monkeypatch.setattr(observer, "predecessor", fail)
    elif fault == "write":
        monkeypatch.setattr(observer.sink, "put", fail)
    seen = [[], []]
    def transport(index):
        def reply(request):
            seen[index].append(request.content)
            value = native(protocol, tool("report", {"state": "partial", "message": "fixture"}))
            value["usage"] = {"prompt_tokens" if protocol == "chat_completions" else "input_tokens": 100}
            return httpx.Response(200, json=value)
        return httpx.MockTransport(reply)
    runtimes = [Runtime(s, Nexus(s, lambda _: "synthetic", transport(i)), usage_observer=observer if i else None)
                for i, s in enumerate((off, on))]
    snapshots = [ordinary_records(s) for s in (off, on)]
    before_objects = {p.name for p in (on.root / "objects").iterdir()}
    durations, prepared = [], []
    observed_before_deferral = []
    if large:
        admit = runtimes[1].context.admit_group
        def track(*args, **kwargs):
            values = list(observer._opportunities.values())
            assert len(values) == 1
            assert values[0].value["forms"][0]["roles"] == ["initial_complete"]
            observed_before_deferral.append(True)
            return admit(*args, **kwargs)
        monkeypatch.setattr(runtimes[1].context, "admit_group", track)
    for runtime in runtimes:
        start = perf_counter()
        coordinated = {**deepcopy(state), **runtime.coordinate(deepcopy(state))}
        prepared.append(runtime.prepare(coordinated))
        durations.append(perf_counter() - start)
    preparation_work = dict(observer.work)
    preparation_diagnostic_bytes = observer.sink.path.stat().st_size if observer.sink.path.exists() else 0
    assert prepared[0] == prepared[1]
    key = prepared[0]["pending"]
    requests = [s.get("request", key) for s in (off, on)]
    payloads = [s.bytes(r["payload_ref"], job["id"]) for s, r in zip((off, on), requests)]
    assert payloads[0] == payloads[1]
    assert requests[0]["meta"] == requests[1]["meta"]
    assert [e["data"] for e in off.events(job["id"])] == [e["data"] for e in on.events(job["id"])]
    assert [ordinary_records(s) for s in (off, on)] == snapshots
    assert {p.name for p in (off.root / "objects").iterdir()} == {p.name for p in (on.root / "objects").iterdir()}
    assert len({p.name for p in (on.root / "objects").iterdir()} - before_objects) == 1
    value = next(iter(observer._opportunities.values())).value
    assert len(value["forms"]) == (2 if large else 1)
    assert value["distinct_evaluations"] == len(value["forms"])
    assert value["new_payload_bytes"] == 0
    assert value["observation_calls"] == 3  # coordinate, prepare, final; no inner projection
    assert value["deduplicated_calls"] == (1 if large else 2)
    for form in value["forms"]:
        for role in form["roles"]:
            assert (role, form["payload_sha256"], form["payload_bytes"]) in serialized_forms
    assert all(f["actual"] is None for f in value["forms"] if "final_ordinary" not in f["roles"])
    if fault is None:
        assert value["basis"]["normalized_usage"]["input"] == 8000
        assert value["basis"]["normalized_usage"]["cached_input"] == 3000
        assert value["forms"][0]["eligibility"]
        assert value["forms"][0]["anchored"]["normalized_prior"] == 8000
        assert value["forms"][0]["anchored"]["components"]["split_counts"]
        assert value["forms"][0]["full_local"]["reservation"] > 0
        assert value["forms"][0]["decoded_full_local"]["method"] != value["forms"][0]["full_local"]["components"]["method"]
        decoded = value["forms"][0]["decoded_full_local"]
        assert decoded["reservation"] == sum(decoded["components"][key] for key in (
            "text_tokens", "text_uncertainty", "native_overhead_reserve", "outcome_reserve", "image_cost"))
    if large:
        assert observed_before_deferral
        assert requests[1]["meta"]["capacity"]["projection"]["deferred"]
        assert value["forms"][0]["exact_replay"] == "unavailable_digest_only"
        assert value["forms"][0]["payload_ref"] is None
        assert not value["forms"][0]["full_local"]["fits"]
        assert value["forms"][1]["full_local"]["fits"]
    else:
        assert value["forms"][0]["roles"] == ["initial_complete", "final_ordinary"]
    # Frozen re-entry does no new counting and can repair a failed diagnostic
    # write without a second ordinary freeze or model attempt.
    evaluations = value["distinct_evaluations"]
    if fault == "write":
        monkeypatch.undo()
    for runtime in runtimes:
        assert runtime.prepare(deepcopy(state)) == prepared[0]
    assert value["distinct_evaluations"] == evaluations
    assert len(observer.sink.records()) == 1
    # Existing historical preview behavior and tool surface remain identical.
    views = [inspect_context(rt.context, req, s.get("job", job["id"]), changes={"notes": "preview only"})
             for rt, req, s in zip(runtimes, requests, (off, on))]
    for view in views:
        view.pop("snapshot_payload_ref")
    assert views[0] == views[1]
    assert len(observer.sink.records()) == 1 and value["distinct_evaluations"] == evaluations
    for i, runtime in enumerate(runtimes):
        runtime.model({**state, **prepared[i]})
    assert seen[0] == seen[1] == [payloads[0]]
    assert off.get("job", job["id"])["attempts"] == on.get("job", job["id"])["attempts"] == 2
    settled = observer.sink.records()[0]
    final = next(f for f in settled["forms"] if "final_ordinary" in f["roles"])
    assert final["payload_sha256"] == sha256(payloads[1]).hexdigest()
    assert final["payload_bytes"] == len(payloads[1])
    assert final["payload_ref"] == requests[1]["payload_ref"]
    assert final["actual"]["status"] == "accepted"
    assert final["actual"]["normalized_usage"]["input"] == 100
    for runtime in runtimes:
        runtime.close()
    save_measurement(f"{protocol}-{large}-{fault}", {"off_seconds": durations[0], "on_seconds": durations[1],
        "difference_seconds": durations[1]-durations[0], "observation": settled,
        "complete_preparation_observer_seconds": preparation_work,
        "new_diagnostic_database_bytes_after_preparation": preparation_diagnostic_bytes,
        "diagnostic_database_bytes_after_settlement": observer.sink.path.stat().st_size,
        "conditions": "coordinate plus prepare on paired cloned settled synthetic tasks; warm deployed F; observer counters process-local"})


@pytest.mark.parametrize("missing", [False, True])
def test_first_and_missing_usage_are_unavailable_not_zero(setup, missing):
    store, job = setup
    state = seed(store, job, missing=True) if missing else initial(job)
    observer = UsageObserver(store, profile=profile(job))
    runtime = Runtime(store, Nexus(store, lambda _: "unused"), usage_observer=observer)
    result = runtime.prepare(state)
    value = observer.sink.records()[0]
    assert value["forms"][0]["anchored"] is None
    assert value["basis"]["normalized_usage"] is None
    assert value["forms"][0]["first_failure"] == ("input_usage_unavailable:missing" if missing else "no_previous_physical_send")
    assert not store.get("request", result["pending"])["attempts"]
    assert value["forms"][0]["actual"]["normalized_usage"] is None
    runtime.close()


def test_recipe_exact_projection_chunks_and_cache_accounting():
    assert sha256(KIMI_PATTERN.encode()).hexdigest() == PATTERN_DIGESTS[1]
    assert RECIPE["counter"] == "tiktoken-0.14.0"
    text, images = projection([{"b": 'x\\n"y', "a": '{"nested":"\\u4e2d"}'}])
    assert text == '[{"a":"{"nested":"\\u4e2d"}","b":"x\\n"y"}]' and images == []
    value = ["保 留  字 μg <|endoftext|>" * 900]
    projected, _ = projection(value)
    expected = [sum(len(c.encode_ordinary(projected[a:a+8192])) for a in range(0, len(projected), 8192)) for c in counters()]
    cost = price(value, None)
    assert cost["split_counts"] == expected
    assert cost["text_uncertainty"] == (6*max(expected)+99)//100
    assert cost["text_features"]["inter_han_u0020_spaces"] == 2700
    assert normalized_input("chat_completions", {"prompt_tokens": 100, "prompt_tokens_details": {"cached_tokens": 80},
        "completion_tokens": 50, "completion_tokens_details": {"reasoning_tokens": 20}})["input"] == 100
    for raw in (None, {"prompt_tokens": True}, {"prompt_tokens": 0}, {"prompt_tokens": 10, "prompt_tokens_details": {"cached_tokens": 11}}):
        with pytest.raises(ValueError):
            normalized_input("chat_completions", raw)


@pytest.mark.parametrize("fault", [None, "counter", "usage", "write"])
@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_ordinary_obstruction_and_persistence_failure_equivalence(setup, tmp_path, monkeypatch, fault, protocol):
    store, job = setup
    job = protocol_job(store, job, protocol)
    state = seed(store, job)
    # Mandatory instructions alone cannot fit. The ordinary exception must
    # survive every independent telemetry fault, with no frozen request/send.
    job = store.update_job(job["id"], route={**job["route"], "context_tokens": 2048, "output_tokens": 256})
    roots = [tmp_path / "off", tmp_path / "on"]
    for root in roots:
        shutil.copytree(store.root, root)
    stores = [Store(root) for root in roots]
    observer = UsageObserver(stores[1], profile=profile(job))
    if fault == "counter":
        monkeypatch.setattr("pdfmd.usage_anchoring.counters", fail)
    elif fault == "usage":
        monkeypatch.setattr(observer, "predecessor", fail)
    elif fault == "write":
        monkeypatch.setattr(observer.sink, "put", fail)
    outcomes = []
    for i, s in enumerate(stores):
        rt = Runtime(s, Nexus(s, lambda _: pytest.fail("No send")), usage_observer=observer if i else None)
        start = perf_counter()
        with pytest.raises(StopRun) as error:
            rt.prepare(state)
        outcomes.append((error.value.reason, str(error.value)))
        save_measurement(f"obstruction-{protocol}-{fault}-{i}", {"seconds": perf_counter()-start,
            "complete_preparation_observer_seconds": dict(observer.work) if i else None})
        assert len(s.records("request")) == 1 and len(s.records("attempt")) == 1
        rt.close()
    assert outcomes[0] == outcomes[1]
    value = next(iter(observer._opportunities.values())).value
    assert value["ordinary_disposition"] == "ordinary_failure"
    assert value["new_payload_bytes"] == 0 and len(value["forms"]) == 1
    assert value["forms"][0]["actual"] is None


@pytest.mark.parametrize("scripts", [False, True])
def test_runtime_graph_is_opt_in_and_links_attributable_attempts(setup, scripts):
    store, job = setup
    seen = []
    observer = UsageObserver(store, profile=profile(job))
    rt = Runtime(store, Nexus(store, lambda _: "synthetic", transport_for(store, job["id"], seen)), usage_observer=observer, scripts=scripts)
    rt.run(job["id"])
    rt.close()
    values = observer.sink.records()
    assert len(values) == 3 and len(seen) == 3
    assert all(v["ordinary_disposition"] == "normal" for v in values)
    assert all(v["forms"][0]["actual"]["normalized_usage"]["input"] == 100 for v in values)
    assert all(v["forms"][0]["eligibility"] for v in values[1:]), [v["forms"][0]["first_failure"] for v in values]
    assert store.get("job", job["id"])["status"] == "completed"


def another_batch(store, job, state):
    ref = store.blob(job["id"], "evidence", {"text": "Another complete result."})["ref"]
    value = native(job["route"]["protocol"], tool("read_evidence", {"ref": ref}, "read"))
    value["usage"] = ({"prompt_tokens": 9000, "completion_tokens": 100} if job["route"]["protocol"] == "chat_completions"
                      else {"input_tokens": 9000, "output_tokens": 100})
    rt = Runtime(store, Nexus(store, lambda _: "synthetic", httpx.MockTransport(lambda _: httpx.Response(200, json=value))))
    state = {**state, **rt.prepare(state)}
    rt.model(state)
    state.update(rt.tools(state))
    rt.close()
    return state


@pytest.mark.parametrize("edit", ["notes", "release", "index_pin", "compound", "native_pin", "forced_deferral"])
def test_v2_native_edit_matching_through_prepare(setup, edit):
    store, job = setup
    state = another_batch(store, job, seed(store, job))
    prior = store.get("request", state["history"][-1])
    old_payload = store.json(prior["payload_ref"], job["id"])
    receipt = next(json.loads(m["content"]) for m in old_payload["messages"] if m.get("role") == "tool")
    ref = receipt["result_ref"]
    if edit == "notes":
        state = {**state, "notes": "保 留原字形、μg 與完整圖片。"}
    elif edit == "release":
        state = {**state, "released": [ref]}
    elif edit in ("index_pin", "native_pin"):
        state = {**state, "pinned": [ref], "pin_views": {ref: [{"ref": ref, "view": "index" if edit == "index_pin" else "full"}]}}
    elif edit == "compound":
        state = {**state, "released": [ref], "notes": "A second simultaneous edit"}
    else:
        # Tighten capacity without changing the predecessor's frozen route.
        # That is an incompatible basis, never permission for forced removals.
        job = store.update_job(job["id"], route={**job["route"], "context_tokens": 18000})
    observer = UsageObserver(store, profile=profile(job))
    rt = Runtime(store, Nexus(store, lambda _: "unused"), usage_observer=observer)
    rt.prepare(state)
    value = observer.sink.records()[0]["forms"][0]
    if edit in ("notes", "release", "index_pin"):
        assert value["eligibility"], value["first_failure"]
        assert value["anchored"]["edit"] == edit
        if edit == "index_pin":
            # The inserted pin plus the replacement retained receipt are both
            # charged, in addition to controls and the new native batch.
            assert value["anchored"]["components"]["text_tokens"] > 600
    else:
        assert not value["eligibility"] and value["anchored"] is None
    rt.close()


@pytest.mark.parametrize("case", ["undeclared", "changed_route", "intervening_failure", "compaction", "staged", "contradictory_usage"])
def test_predecessor_trust_never_selects_an_older_send(setup, case):
    store, job = setup
    state = seed(store, job)
    previous = store.get("request", state["history"][-1])
    attempt = store.get("attempt", previous["attempts"][-1])
    if case == "changed_route":
        job = store.update_job(job["id"], route={**job["route"], "estimation_profile": "utf8_fallback_v1"})
    elif case == "intervening_failure":
        failed = {**attempt, "id": "later-attempt", "request": "later-request", "started": attempt["started"]+1,
                  "status": "http_error", "usage": None}
        store.put("attempt", failed["id"], job["id"], failed)
        store.put("request", "later-request", job["id"], {**previous, "id": "later-request", "attempts": [failed["id"]], "status": "http_error"})
    elif case == "compaction":
        store.put("request", previous["id"], job["id"], {**previous, "kind": "compaction"})
    elif case == "staged":
        store.put("request", previous["id"], job["id"], {**previous, "status": "in_flight", "accepted_ref": None})
    elif case == "contradictory_usage":
        store.put("attempt", attempt["id"], job["id"], {**attempt, "usage": {"prompt_tokens": 1}})
    observer = UsageObserver(store, profile=None if case == "undeclared" else profile(job))
    # Deliberately corrupted acceptance is not a valid ordinary assembly; use
    # the actual initial opportunity hook before the ordinary error escapes.
    rt = Runtime(store, Nexus(store, lambda _: "unused"), usage_observer=observer)
    if case in ("staged", "compaction"):
        # Group assembly may reject the changed request before any candidate
        # can finalize. The obstruction itself is the correct observation.
        try:
            rt.prepare(state)
        except (StopRun, ValueError):
            pass
    else:
        rt.prepare(state)
    values = observer.sink.records()
    assert len(values) == 1
    assert all(not f["eligibility"] and f["anchored"] is None for f in values[0]["forms"])
    if case == "intervening_failure":
        assert values[0]["basis"]["predecessor"]["attempt"] == "later-attempt"
    rt.close()


def test_reopen_and_failed_write_reentry_have_no_duplicate_effects(setup, monkeypatch):
    store, job = setup
    state = seed(store, job)
    observer = UsageObserver(store, profile=profile(job))
    rt = Runtime(store, Nexus(store, lambda _: "unused"), usage_observer=observer)
    put = observer.sink.put
    monkeypatch.setattr(observer.sink, "put", fail)
    first = rt.prepare(state)
    assert not observer.sink.records()
    monkeypatch.setattr(observer.sink, "put", put)
    assert rt.prepare(state) == first
    saved = deepcopy(observer.sink.records())
    rt.close()
    reopened = Store(store.root)
    resumed = UsageObserver(reopened, profile=profile(job))
    rt = Runtime(reopened, Nexus(reopened, lambda _: "unused"), usage_observer=resumed)
    assert rt.prepare(state) == first
    assert resumed.sink.records() == saved
    assert len(reopened.records("request")) == 2 and len(reopened.records("attempt")) == 1
    rt.close()


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
@pytest.mark.parametrize("legacy", [False, True], ids=["explicit-profile", "basis-profile"])
def test_settled_usage_survives_preparation_and_profile_relinking(setup, monkeypatch, protocol, legacy):
    store, job = setup
    endpoint = "http://127.0.0.1:8317/v1/" + ("responses" if protocol == "responses" else "chat/completions")
    job = store.update_job(job["id"], route={**job["route"], "protocol": protocol, "endpoint": endpoint})
    state = initial(job)
    declared = profile(job)
    observer = UsageObserver(store, profile=declared)
    seen = []

    def reply(request):
        seen.append(request.content)
        value = native(protocol, tool("report", {"state": "partial", "message": "fixture"}))
        value["usage"] = ({"prompt_tokens": 100, "completion_tokens": 50} if protocol == "chat_completions"
                          else {"input_tokens": 100, "output_tokens": 50})
        return httpx.Response(200, json=value)

    def runtime(local, observed):
        return Runtime(local, Nexus(local, lambda _: "synthetic", httpx.MockTransport(reply)),
                       usage_observer=observed)

    rt = runtime(store, observer)
    prepared = rt.prepare(state)
    request = store.get("request", prepared["pending"])
    payload = store.bytes(request["payload_ref"], job["id"])
    if legacy:
        # Pre-repair rows retain their accounting declaration only in basis.
        value = observer.sink.records()[0]
        value.pop("profile", None)
        observer.sink.put(value)
        rt.close()
        observer = UsageObserver(store, profile=declared)
        rt = runtime(store, observer)
    rt.model({**state, **prepared})
    baseline = observer.sink.records()[0]
    final = baseline["forms"][0]
    actual = final["actual"]
    assert actual["attempt"] == store.get("request", request["id"])["attempts"][0]
    assert actual["normalized_usage"]["input"] == 100
    raw_ref = actual["normalized_usage"]["raw_usage_ref"]
    raw_usage = store.json(raw_ref, job["id"])["usage"]
    assert actual["normalized_usage"]["raw_usage_sha256"] == digest(raw_usage)
    assert final["reservation_errors"] == {
        name: final[name]["reservation"] - 100 for name in ("full_local", "decoded_full_local")}

    def assert_preserved(observed, local):
        saved = observed.sink.records()[0]
        assert saved.get("profile") == baseline.get("profile")
        assert saved["basis"] == baseline["basis"]
        assert saved["forms"][0]["actual"] == actual
        assert saved["forms"][0]["reservation_errors"] == final["reservation_errors"]
        assert local.bytes(request["payload_ref"], job["id"]) == payload
        assert seen == [payload]
        assert len(local.records("attempt", job["id"])) == 1
        assert len(local.records("request", job["id"])) == 1

    assert rt.prepare(state) == prepared
    assert_preserved(observer, store)
    with monkeypatch.context() as injected:
        injected.setattr(observer.sink, "put", fail)
        assert rt.prepare(state) == prepared
        assert_preserved(observer, store)
    assert rt.prepare(state) == prepared
    assert_preserved(observer, store)
    rt.close()
    reopened = Store(store.root)
    resumed = UsageObserver(reopened, profile=declared)
    rt = runtime(reopened, resumed)
    assert rt.prepare(state) == prepared
    assert_preserved(resumed, reopened)
    rt.close()
    for caller in (None, ObservationProfile(declared.route_sha256, "Another fixture declaration"), declared):
        relinker = UsageObserver(reopened, profile=caller)
        rt = runtime(reopened, relinker)
        rt.model({**state, **prepared})
        assert_preserved(relinker, reopened)
        rt.close()
    save_measurement(f"settled-{protocol}-{legacy}", {"before": baseline,
        "after": resumed.sink.records()[0], "physical_sends": len(seen),
        "request_sha256": sha256(payload).hexdigest()})


def test_relink_preserves_each_rows_accounting_declaration(setup):
    store, job = setup
    state = seed(store, job)
    seen = []

    def reply(request):
        seen.append(request.content)
        return httpx.Response(200, json=response(tool("report", {"state": "partial", "message": "fixture"})))

    observers = [UsageObserver(store, profile=profile(job)), UsageObserver(store)]
    runtimes = [Runtime(store, Nexus(store, lambda _: "synthetic", httpx.MockTransport(reply)),
                        usage_observer=observer) for observer in observers]
    # Both profiles see this preparation before either freezes the request.
    for rt in runtimes:
        rt.coordinate(deepcopy(state))
    prepared = [rt.prepare(deepcopy(state)) for rt in runtimes]
    assert prepared[0] == prepared[1]
    runtimes[0].model({**state, **prepared[0]})
    baseline = {value["id"]: value for value in observers[0].sink.records()}
    assert len(baseline) == 2
    for value in baseline.values():
        final = value["forms"][0]
        if value["profile"]:
            assert final["actual"]["normalized_usage"]["input"] == 100
            assert "anchored" in final["reservation_errors"]
        else:
            assert final["actual"]["normalized_usage"] is None
            assert final["actual"]["usage_unavailable"] == "route_accounting_or_profile_undeclared"
            assert final["reservation_errors"] is None
    for rt in reversed(runtimes):
        # coordinate also flushes a cached pre-settlement opportunity.
        rt.coordinate(deepcopy(state))
        rt.prepare(deepcopy(state))
        rt.model({**state, **prepared[0]})
        for value in observers[0].sink.records():
            expected = baseline[value["id"]]
            assert value["profile"] == expected["profile"]
            assert value["forms"][0]["actual"] == expected["forms"][0]["actual"]
            assert value["forms"][0]["reservation_errors"] == expected["forms"][0]["reservation_errors"]
        rt.close()
    request = store.get("request", prepared[0]["pending"])
    assert seen == [store.bytes(request["payload_ref"], job["id"])]
    assert len(store.records("attempt", job["id"])) == 2  # One seed, one target send.


@pytest.mark.parametrize("fault", [None, "counter", "usage", "write"])
def test_original_freeze_failure_is_preserved(setup, tmp_path, monkeypatch, fault):
    store, job = setup
    state = seed(store, job)
    for mode in ("off", "on"):
        root = tmp_path / mode
        shutil.copytree(store.root, root)
        local = Store(root)
        observer = UsageObserver(local, profile=profile(job))
        if fault == "counter":
            monkeypatch.setattr("pdfmd.usage_anchoring.counters", fail)
        elif fault == "usage":
            monkeypatch.setattr(observer, "predecessor", fail)
        elif fault == "write":
            monkeypatch.setattr(observer.sink, "put", fail)
        rt = Runtime(local, Nexus(local, lambda _: "unused"), usage_observer=observer if mode == "on" else None)
        put = local.put
        def ordinary_failure(kind, *args, **kwargs):
            if kind == "request":
                raise RuntimeError("original ordinary request publication failure")
            return put(kind, *args, **kwargs)
        monkeypatch.setattr(local, "put", ordinary_failure)
        with pytest.raises(RuntimeError, match="^original ordinary request publication failure$"):
            rt.prepare(state)
        assert len(local.records("request")) == len(local.records("attempt")) == 1
        assert not local.get("job", job["id"])["cancel_requested"]
        rt.close()


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_native_images_preserve_pixels_and_charge_only_new_occurrences(setup, protocol, tmp_path):
    store, job = setup
    job = store.update_job(job["id"], route={**job["route"], "protocol": protocol, "vision": True,
        "image_tokens": 4096, "endpoint": "http://127.0.0.1/v1/" + ("responses" if protocol == "responses" else "chat/completions")})
    state = seed(store, job, image=True)
    roots = [tmp_path / "off", tmp_path / "on"]
    for root in roots:
        shutil.copytree(store.root, root)
    prepared = []
    for i, root in enumerate(roots):
        local = Store(root)
        observer = UsageObserver(local, profile=profile(job))
        rt = Runtime(local, Nexus(local, lambda _: "unused"), usage_observer=observer if i else None)
        result = rt.prepare(state)
        request = local.get("request", result["pending"])
        prepared.append((local.bytes(request["payload_ref"], job["id"]), request["meta"]))
        if i:
            value = observer.sink.records()[0]["forms"][0]
            assert value["eligibility"], value["first_failure"]
            charge = value["anchored"]["components"]
            assert charge["images"] == 1 and charge["image_cost"] == 4096
            assert charge["image_occurrences"][0]["area"] == 595*842
            assert charge["image_occurrences"][0]["detail"] == "unspecified"
            assert value["image_rule"] == "configured_per_occurrence_uncalibrated_v1"
        rt.close()
    assert prepared[0] == prepared[1]
    state = another_batch(store, job, state)
    observer = UsageObserver(store, profile=profile(job))
    rt = Runtime(store, Nexus(store, lambda _: "unused"), usage_observer=observer)
    rt.prepare(state)
    value = observer.sink.records()[0]["forms"][0]
    assert value["eligibility"], value["first_failure"]
    assert value["anchored"]["components"]["images"] == 0
    assert value["decoded_full_local"]["components"]["images"] == 1
    rt.close()


def test_unfinalizable_form_records_obstruction_without_changing_error(setup, monkeypatch):
    store, job = setup
    observer = UsageObserver(store, profile=profile(job))
    def unstable(*args, **kwargs):
        raise ValueError("Working-context feedback cost did not stabilize.")
    monkeypatch.setattr("pdfmd.context.with_feedback", unstable)
    for enabled in (False, True):
        rt = Runtime(store, Nexus(store, lambda _: "unused"), usage_observer=observer if enabled else None)
        with pytest.raises(ValueError, match="^Working-context feedback cost did not stabilize.$"):
            rt.prepare(initial(job))
        rt.close()
    value = observer.sink.records()[0]
    assert value["forms"] == [] and value["distinct_evaluations"] == 0
    assert value["ordinary_disposition"] == "ordinary_failure"
    assert {i["role"] for i in value["obstructions"]} == {"initial_complete", "final_ordinary"}
    assert not store.records("request")


def test_actual_compaction_selection_has_only_initial_normal_observation(setup, tmp_path):
    store, job = setup
    calls = []
    for index in range(2):
        text = "".join(random.Random(index).choices("abcdefghijklmnopqrstuvwxyz0123456789", k=50000))
        ref = store.blob(job["id"], "evidence", {"text": text})["ref"]
        calls.append(tool("read_evidence", {"ref": ref}, str(index)))
    reply = response(*calls)
    reply["usage"] = {"prompt_tokens": 8000}
    rt = Runtime(store, Nexus(store, lambda _: "synthetic", httpx.MockTransport(lambda _: httpx.Response(200, json=reply))))
    state = initial(job)
    state.update(rt.prepare(state))
    rt.model(state)
    state.update(rt.tools(state))
    rt.close()
    prepared = []
    for enabled in (False, True):
        root = tmp_path / ("on" if enabled else "off")
        shutil.copytree(store.root, root)
        local = Store(root)
        observer = UsageObserver(local, profile=profile(job))
        rt = Runtime(local, Nexus(local, lambda _: pytest.fail("No extra send")), usage_observer=observer if enabled else None)
        result = rt.prepare(state)
        assert result["next"] == "compact"
        request = local.get("request", result["pending"])
        prepared.append((request["meta"], local.bytes(request["payload_ref"], job["id"])))
        if enabled:
            value = observer.sink.records()[0]
            assert value["ordinary_disposition"] == "compaction"
            assert value["distinct_evaluations"] == len(value["forms"]) == 1
            assert value["forms"][0]["roles"] == ["initial_complete"]
            assert value["forms"][0]["actual"] is None
            assert value["ordinary_request"]["kind"] == "compaction"
        rt.close()
    assert prepared[0] == prepared[1]


def test_image_release_keeps_measured_charge_and_prices_replacement_once(setup):
    store, job = setup
    job = store.update_job(job["id"], route={**job["route"], "vision": True, "image_tokens": 4096})
    state = another_batch(store, job, seed(store, job, image=True))
    prior = store.get("request", state["history"][-1])
    payload = store.json(prior["payload_ref"], job["id"])
    receipt = next(json.loads(m["content"]) for m in payload["messages"] if m.get("role") == "tool")
    ref = receipt["image_ref"]
    original = store.bytes(ref, job["id"])
    state = {**state, "released": [ref]}
    observer = UsageObserver(store, profile=profile(job))
    rt = Runtime(store, Nexus(store, lambda _: "unused"), usage_observer=observer)
    rt.prepare(state)
    value = observer.sink.records()[0]["forms"][0]
    assert value["eligibility"], value["first_failure"]
    anchor = value["anchored"]
    assert anchor["edit"] == "release" and anchor["normalized_prior"] == 9000
    assert anchor["components"]["image_cost"] == 0
    assert anchor["reservation"] >= 9000  # No credit for measured removed pixels.
    assert store.bytes(ref, job["id"]) == original
    rt.close()


def test_deployed_explicit_fallback_still_governs_identical_payload(setup, tmp_path):
    store, job = setup
    job = store.update_job(job["id"], route={**job["route"], "estimation_profile": "utf8_fallback_v1"})
    state = seed(store, job)
    results = []
    for enabled in (False, True):
        root = tmp_path / str(enabled)
        shutil.copytree(store.root, root)
        local = Store(root)
        observer = UsageObserver(local, profile=profile(job))
        rt = Runtime(local, Nexus(local, lambda _: "unused"), usage_observer=observer if enabled else None)
        selected = rt.prepare(state)
        request = local.get("request", selected["pending"])
        assert request["meta"]["capacity"]["method"] == "utf8_fallback_v1"
        assert request["meta"]["capacity"]["fallback"] == "explicit_route_fallback"
        results.append((local.bytes(request["payload_ref"], job["id"]), request["meta"]["capacity"]))
        if enabled:
            assert observer.sink.records()[0]["forms"][0]["full_local"]["components"]["method"] == "utf8_fallback_v1"
        rt.close()
    assert results[0] == results[1]


def test_graph_obstruction_is_observed_at_coordinate_before_wait(setup):
    store, job = setup
    job = store.update_job(job["id"], route={**job["route"], "context_tokens": 2048, "output_tokens": 256})
    observer = UsageObserver(store, profile=profile(job))
    rt = Runtime(store, Nexus(store, lambda _: pytest.fail("No sends on obstruction")), usage_observer=observer)
    rt.run(job["id"])
    rt.close()
    value = observer.sink.records()[0]
    assert value["forms"][0]["roles"] == ["initial_complete"]
    assert value["ordinary_disposition"] == "ordinary_failure"
    assert not store.records("request") and not store.records("attempt")


@pytest.mark.parametrize("fault", [None, "counter", "usage", "write"])
@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_complete_graph_fault_equivalence_and_single_document_effect(setup, tmp_path, monkeypatch, fault, protocol):
    store, job = setup
    job = protocol_job(store, job, protocol)
    results = []
    for enabled in (False, True):
        root = tmp_path / str(enabled)
        shutil.copytree(store.root, root)
        local = Store(root)
        identifiers = count(1)
        def stable_uid():
            return f"{next(identifiers):032x}"
        # Align otherwise random ordinary IDs across the two isolated arms so
        # later request bytes, including saved-version references, can compare.
        for module in ("storage", "nexus", "documents", "evidence"):
            monkeypatch.setattr(f"pdfmd.{module}.uid", stable_uid)
        observer = UsageObserver(local, profile=profile(job))
        if fault == "counter":
            monkeypatch.setattr("pdfmd.usage_anchoring.counters", fail)
        elif fault == "usage":
            monkeypatch.setattr(observer, "predecessor", fail)
        elif fault == "write":
            monkeypatch.setattr(observer.sink, "put", fail)
        seen = []
        def reply(request):
            payload = json.loads(request.content)
            seen.append(payload)
            if len(seen) == 1:
                call = tool("inspect_pdf", {"pages": [1], "mode": "text"})
            elif len(seen) == 2:
                receipts = [m.get("content", m.get("output")) for m in payload.get("messages", payload.get("input", []))
                            if m.get("role") == "tool" or m.get("type") == "function_call_output"]
                text = json.loads(receipts[-1])["data"]["value"]["pages"][0]["content"]
                call = tool("edit_document", {"base_version": None, "expected_head": None,
                    "replace_blocks": [{"id": "section", "pages": [1], "markdown": text}],
                    "page_updates": {"1": {"printed": "none", "disposition": "included"}}, "claim": "complete"})
            else:
                call = tool("report", {"state": "complete", "message": "Saved the synthetic section.",
                                       "version_id": local.get("job", job["id"])["head"]})
            value = native(protocol, call)
            value["usage"] = {"prompt_tokens" if protocol == "chat_completions" else "input_tokens": 100}
            return httpx.Response(200, json=value)
        rt = Runtime(local, Nexus(local, lambda _: "synthetic", httpx.MockTransport(reply)), usage_observer=observer if enabled else None)
        rt.run(job["id"])
        frozen = local.records("request")[0]
        rt.prepare(frozen["meta"]["context_snapshot"]["state"])
        rt.close()
        current = local.get("job", job["id"])
        assert current["status"] == "completed" and current["attempts"] == len(seen) == 3
        assert len(local.records("version")) == 1
        requests = local.records("request")
        results.append({"outgoing": [encode(p) for p in seen], "operations": local.records("operation"),
            "versions": [local.json(v["manifest_ref"], job["id"]) if "manifest_ref" in v else v for v in local.records("version")],
            "requests": [{"kind": r["kind"], "capacity": r["meta"]["capacity"], "status": r["status"]} for r in requests]})
        if enabled:
            assert len(observer._opportunities) == 3
            assert all(op.value["distinct_evaluations"] == 1 for op in observer._opportunities.values())
    # Operation/version timestamps are persistence facts, not transmitted input.
    assert results[0]["outgoing"] == results[1]["outgoing"]
    assert results[0]["requests"] == results[1]["requests"]
    assert results[0]["operations"] == results[1]["operations"]
    assert [{k: v for k, v in version.items() if k != "created"} for version in results[0]["versions"]] == [
        {k: v for k, v in version.items() if k != "created"} for version in results[1]["versions"]]


def test_observer_failure_time_cannot_exhaust_ordinary_active_budget(setup, tmp_path, monkeypatch):
    store, job = setup
    job = store.update_job(job["id"], limits={**job["limits"], "max_active_seconds": 1})
    outcomes = []
    for enabled in (False, True):
        root = tmp_path / str(enabled)
        shutil.copytree(store.root, root)
        local = Store(root)
        ticks = [0.0]
        monkeypatch.setattr("time.monotonic", lambda: ticks[0])
        def slow_counter_failure():
            ticks[0] += 100.0  # Simulated diagnostic delay; no blocking sleep.
            raise OSError("slow observer-only counter failure")
        monkeypatch.setattr("pdfmd.usage_anchoring.counters", slow_counter_failure)
        observer = UsageObserver(local, profile=profile(job))
        seen = []
        rt = Runtime(local, Nexus(local, lambda _: "synthetic", transport_for(local, job["id"], seen)), usage_observer=observer if enabled else None)
        rt.run(job["id"])
        rt.close()
        current = local.get("job", job["id"])
        outcomes.append((current["status"], current["attempts"], current["active_seconds"], len(seen)))
    assert outcomes[0] == outcomes[1] == ("completed", 3, 0.0, 3)
