"""Synthetic evaluator semantics, not observed model usage or calibration."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from pdfmd.calibration import EvaluationError, digest, evaluate, main, route_fingerprint, write_report
from pdfmd.nexus import make_payload
from pdfmd.request_estimation import VOCAB_SHA256, estimate
from pdfmd.schema import Route
from pdfmd.storage import encode


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket
    import tiktoken.load
    def fail(*args, **kwargs):
        pytest.fail("Offline evaluation must not access the network")
    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket.socket, "connect", fail)
    monkeypatch.setattr(tiktoken.load, "read_file", fail)


def case(tmp_path, protocol="chat_completions", images=False, offset=0):
    suffix = "chat/completions" if protocol == "chat_completions" else "responses"
    route = Route(endpoint=f"http://localhost/v1/{suffix}", protocol=protocol, model="offline-evaluation",
                  context_tokens=2048, output_tokens=256, image_tokens=4096,
                  parameters={"metadata": {"type": "file"}})
    study = {"version": 1, "route": route.model_dump(mode="json"), "measurement": {
        "method": "o200k_native_json_proxy_v1", "modality_projection": "protocol_native_content_v2",
        "vocabulary_sha256": VOCAB_SHA256},
        "candidates": [{"id": "declared", "text_margin": "0", "fixed_tokens": 0, "image_tokens": 0}],
        "gates": {"max_run_overestimate_pct": "100", "max_group_overestimate_pct": "100",
                  "min_known_per_run": 1, "min_known_per_group": 1,
                  "required_groups": ["normal"], "require_fit_improvement": False},
        "validation": {"predeclared": True, "source_sha256": [digest(b"synthetic validation PDF identity")]}}
    payloads, usages, observations, texts = [], [], [], []
    for index, partition in enumerate(("development", "validation")):
        content = "PRIVATE_NATIVE_CONTENT_" + partition
        if images:
            image = ({"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}}
                     if protocol == "chat_completions" else {"type": "input_image", "image_url": "data:image/png;base64,AAAA"})
            content = [{"type": "text" if protocol == "chat_completions" else "input_text", "text": content}, image]
        payload = make_payload(route, "Complete source access.", [{"role": "user", "content": content}], [])
        text = estimate(payload, route)["text_tokens"]
        payloads.append(payload)
        texts.append(text)
        incoming = text + offset
        usage = ({"prompt_tokens": incoming, "completion_tokens": 7, "total_tokens": incoming + 7,
                  "prompt_tokens_details": {"cached_tokens": incoming // 2}}
                 if protocol == "chat_completions" else {
                     "input_tokens": incoming, "output_tokens": 7, "total_tokens": incoming + 7,
                     "input_tokens_details": {"cached_tokens": incoming // 2}})
        row = {"id": str(index), "run": partition, "attempt_id": f"physical-{index}", "partition": partition,
               "source_sha256": digest(("synthetic " + partition + " PDF identity").encode()),
               "previously_inspected": partition == "development", "request_kind": "normal", "group": "normal"}
        observations.append(row)
        usages.append({"run": row["run"], "attempt_id": row["attempt_id"], "protocol": protocol,
                       "request_sha256": digest(encode(payload)), "route_sha256": route_fingerprint(route),
                       "accounting": "inclusive_input_v1", "native_usage": usage})
    state = SimpleNamespace(study=study, observations=observations, payloads=payloads, usages=usages, texts=texts,
                            study_path=tmp_path / "study.json", corpus_path=tmp_path / "corpus.json", root=tmp_path)
    def save():
        state.study_path.write_bytes(encode(study))
        rows = deepcopy(observations)
        for index, row in enumerate(rows):
            for name, value in (("payload", payloads[index]), ("usage", usages[index])):
                raw = encode(value)
                path = tmp_path / f"{name}-{index}.json"
                path.write_bytes(raw)
                row[name] = {"path": path.name, "sha256": digest(raw)}
        state.corpus_path.write_bytes(encode({"version": 1, "study_sha256": digest(state.study_path.read_bytes()),
                                             "observations": rows}))
        return state.study_path, state.corpus_path
    state.save = save
    return state


def selected(report):
    return report["candidates"][0]


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_declared_numeric_pass_is_read_only_and_conditional(tmp_path, protocol):
    data = case(tmp_path, protocol)
    paths = data.save()
    protected = {p: p.read_bytes() for p in tmp_path.iterdir()}
    report = write_report(*paths, tmp_path / "report.json")
    assert selected(report)["gate"]["status"] == "pass"
    assert selected(report)["summary"]["overall"]["scored_rows"] == 2
    assert selected(report)["summary"]["overall"]["signed_error_tokens"] == 0
    assert [r["usage_input"] for r in selected(report)["rows"]] == data.texts  # Cached input is a subset.
    assert json.loads((tmp_path / "report.json").read_bytes()) == report
    assert all(p.read_bytes() == raw for p, raw in protected.items())
    raw_report = encode(report)
    assert b"PRIVATE_NATIVE_CONTENT" not in raw_report and b"http://localhost" not in raw_report
    assert "not_production_adoption" in selected(report)["gate"]["meaning"]
    assert any("supplied claims" in limit for limit in report["limits"])


@pytest.mark.parametrize("protocol", ["chat_completions", "responses"])
def test_fractional_ceiling_images_and_fixed_payload_fit(tmp_path, protocol):
    data = case(tmp_path, protocol, images=True, offset=9)
    data.study["candidates"][0].update(text_margin="0.000001", fixed_tokens=5, image_tokens=3)
    data.study["gates"]["require_fit_improvement"] = True
    report = evaluate(*data.save())
    candidate = selected(report)
    assert candidate["gate"]["status"] == "pass" and candidate["gate"]["fixed_payload_fit_improvement"]
    for row, text in zip(candidate["rows"], data.texts):
        assert row["input_estimate"] == text + 9
        assert row["baseline"]["images"] == 1 and not row["baseline"]["fits"] and row["candidate_fit"]


def test_undercount_does_not_cancel_positive_excess(tmp_path):
    data = case(tmp_path)
    for index, difference in enumerate((-10, 10)):
        usage = data.usages[index]["native_usage"]
        usage.update(prompt_tokens=data.texts[index] + difference, total_tokens=data.texts[index] + difference + 7,
                     prompt_tokens_details={"cached_tokens": 0})
    report = selected(evaluate(*data.save()))
    totals = report["summary"]["overall"]
    assert totals["signed_error_tokens"] == 0 and totals["positive_excess_tokens"] == 10
    assert totals["undercount_count"] == 1 and totals["worst_undercount_tokens"] == 10
    assert report["gate"]["status"] == "fail" and report["gate"]["failures"] == ["observed_undercount"]


def test_development_undercount_is_not_hidden_by_perfect_validation(tmp_path):
    data = case(tmp_path)
    data.usages[0]["native_usage"].update(prompt_tokens=data.texts[0] + 1, total_tokens=data.texts[0] + 8)
    report = selected(evaluate(*data.save()))
    assert report["summary"]["partitions"]["validation"]["overall"]["undercount_count"] == 0
    assert report["gate"]["status"] == "fail" and "observed_undercount" in report["gate"]["failures"]


@pytest.mark.parametrize("kind", ["run", "group"])
def test_run_and_composition_limits_are_independent(tmp_path, kind):
    data = case(tmp_path)
    data.usages[1]["native_usage"].update(prompt_tokens=data.texts[1] - 1, total_tokens=data.texts[1] + 6,
                                         prompt_tokens_details={"cached_tokens": 0})
    data.study["gates"][f"max_{kind}_overestimate_pct"] = "0"
    report = selected(evaluate(*data.save()))
    assert report["gate"]["status"] == "fail"
    expected = "excess_limit:runs:validation" if kind == "run" else "excess_limit:groups:normal"
    assert report["gate"]["failures"] == [expected]


def test_distinct_retry_exposures_remain_distinct_without_inventing_new_payloads(tmp_path):
    data = case(tmp_path)
    paths = data.save()
    corpus = json.loads(data.corpus_path.read_bytes())
    row = deepcopy(corpus["observations"][1])
    row.update(id="retry", attempt_id="another-physical-attempt")
    usage = deepcopy(data.usages[1])
    usage["attempt_id"] = row["attempt_id"]
    (tmp_path / "retry-usage.json").write_bytes(encode(usage))
    row["usage"] = {"path": "retry-usage.json", "sha256": digest(encode(usage))}
    corpus["observations"].append(row)
    data.corpus_path.write_bytes(encode(corpus))
    report = selected(evaluate(*paths))
    assert report["summary"]["overall"]["physical_attempts"] == 3
    assert report["summary"]["overall"]["unique_payloads"] == 2
    assert report["gate"]["status"] == "pass"


@pytest.mark.parametrize("below", [False, True])
def test_gates_use_exact_ratios_instead_of_display_rounding(tmp_path, below):
    data = case(tmp_path)
    text = data.texts[1]
    data.usages[1]["native_usage"].update(prompt_tokens=text - 1, total_tokens=text + 6,
                                         prompt_tokens_details={"cached_tokens": 0})
    exact = Fraction(100, text - 1)
    limit = exact - (Fraction(1, 10**12) if below else 0)
    for name in ("max_run_overestimate_pct", "max_group_overestimate_pct"):
        data.study["gates"][name] = str(limit)
    report = selected(evaluate(*data.save()))
    assert report["gate"]["status"] == ("fail" if below else "pass")


@pytest.mark.parametrize("fault", ["missing", "subset", "total", "output_only", "attribution", "accounting"])
def test_unknown_or_unattributable_validation_stays_in_denominator(tmp_path, fault):
    data = case(tmp_path)
    record = data.usages[1]
    if fault == "missing":
        record["native_usage"] = None
    elif fault == "subset":
        record["native_usage"]["prompt_tokens_details"]["cached_tokens"] = data.texts[1] + 1
    elif fault == "total":
        record["native_usage"]["total_tokens"] += 1
    elif fault == "output_only":
        record["native_usage"] = {"completion_tokens": 7}
    elif fault == "attribution":
        record["request_sha256"] = "0" * 64
    else:
        record["accounting"] = "unknown_provider_semantics"
    report = selected(evaluate(*data.save()))
    totals = report["summary"]["overall"]
    assert totals["total_rows"] == 2 and totals["scored_rows"] == 1 and totals["unknown_usage_rows"] == 1
    assert report["gate"]["status"] == "inconclusive"
    assert "unknown_validation_usage" in report["gate"]["evidence_gaps"]


def test_partial_usage_with_valid_input_is_not_discarded(tmp_path):
    data = case(tmp_path)
    data.usages[1]["native_usage"] = {"prompt_tokens": data.texts[1]}
    report = selected(evaluate(*data.save()))
    assert report["rows"][1]["usage_status"] == "partial" and report["gate"]["status"] == "pass"


@pytest.mark.parametrize("fault", ["source", "run", "payload", "inspected", "unconfirmed", "predeclared",
                                    "coverage", "support", "unknown_source"])
def test_holdout_claims_cannot_hide_overlap_or_missing_evidence(tmp_path, fault):
    data = case(tmp_path)
    if fault == "source":
        data.observations[1]["source_sha256"] = data.observations[0]["source_sha256"]
    elif fault == "run":
        data.observations[1]["run"] = data.observations[0]["run"]
        data.usages[1]["run"] = data.usages[0]["run"]
    elif fault == "payload":
        data.payloads[1] = data.payloads[0]
        data.usages[1]["request_sha256"] = digest(encode(data.payloads[0]))
        data.usages[1]["native_usage"] = deepcopy(data.usages[0]["native_usage"])
    elif fault in ("inspected", "unconfirmed"):
        data.observations[1]["previously_inspected"] = True if fault == "inspected" else None
    elif fault == "predeclared":
        data.study["validation"]["predeclared"] = False
    elif fault == "coverage":
        data.study["gates"]["required_groups"].append("compaction")
    elif fault == "support":
        data.study["gates"]["min_known_per_run"] = 2
    else:
        data.observations[1]["source_sha256"] = None
    assert selected(evaluate(*data.save()))["gate"]["status"] == "inconclusive"


def test_development_only_and_zero_usage_are_not_validation_passes(tmp_path):
    data = case(tmp_path)
    data.observations.pop()
    data.payloads.pop()
    data.usages.pop()
    result = selected(evaluate(*data.save()))
    assert result["gate"]["status"] == "inconclusive" and "no_validation_rows" in result["gate"]["evidence_gaps"]
    data = case(tmp_path)
    data.usages[1]["native_usage"] = {"prompt_tokens": 0}
    result = selected(evaluate(*data.save()))
    assert result["summary"]["partitions"]["validation"]["overall"]["weighted_overestimate_pct"] is None
    assert result["rows"][1]["signed_error_pct"] is None and result["gate"]["status"] == "inconclusive"


@pytest.mark.parametrize("fault", ["hash", "missing", "noncanonical", "unsupported", "measurement", "fallback"])
def test_unavailable_measurement_is_reported_without_applying_bpe_coefficients(tmp_path, fault):
    data = case(tmp_path)
    if fault == "measurement":
        data.study["measurement"]["modality_projection"] = "wrong_recipe"
    if fault == "fallback":
        data.study["route"]["estimation_profile"] = "utf8_fallback_v1"
        route = Route.model_validate(data.study["route"])
        for record in data.usages:
            record["route_sha256"] = route_fingerprint(route)
    paths = data.save()
    if fault in ("hash", "noncanonical", "unsupported"):
        path = tmp_path / "payload-1.json"
        raw = path.read_bytes()
        if fault == "hash":
            path.write_bytes(raw + b" ")
        else:
            native = json.loads(raw)
            if fault == "unsupported":
                native["messages"][-1]["content"] = [{"type": "file"}]
                changed = encode(native)
            else:
                changed = json.dumps(native, indent=2).encode()
            path.write_bytes(changed)
            corpus = json.loads(data.corpus_path.read_bytes())
            corpus["observations"][1]["payload"]["sha256"] = digest(changed)
            data.corpus_path.write_bytes(encode(corpus))
    if fault == "missing":
        (tmp_path / "payload-1.json").unlink()
    result = selected(evaluate(*paths))
    assert result["gate"]["status"] == "inconclusive"
    assert result["rows"][1]["input_estimate"] is None
    if fault == "fallback":
        assert result["rows"][1]["baseline"]["fallback"] == "explicit_route_fallback"


@pytest.mark.parametrize("fault", ["study_binding", "duplicate_id", "duplicate_attempt", "invalid_margin"])
def test_invalid_declarations_are_rejected_instead_of_dropping_rows(tmp_path, fault):
    data = case(tmp_path)
    if fault == "invalid_margin":
        data.study["candidates"][0]["text_margin"] = "NaN"
    paths = data.save()
    corpus = json.loads(data.corpus_path.read_bytes())
    if fault == "study_binding":
        data.study_path.write_bytes(data.study_path.read_bytes() + b" ")
    elif fault == "duplicate_id":
        corpus["observations"][1]["id"] = "0"
    elif fault == "duplicate_attempt":
        corpus["observations"][1].update(run="development", attempt_id="physical-0")
    data.corpus_path.write_bytes(encode(corpus))
    with pytest.raises(EvaluationError):
        evaluate(*paths)


def test_reports_do_not_overwrite_inputs_or_prior_results_and_cli_is_usable(tmp_path, capsys):
    data = case(tmp_path)
    paths = data.save()
    with pytest.raises(EvaluationError, match="output_is_input"):
        write_report(*paths, tmp_path / "payload-0.json")
    output = tmp_path / "report.json"
    write_report(*paths, output)
    protected = output.read_bytes()
    with pytest.raises(EvaluationError, match="output_exists"):
        write_report(*paths, output)
    assert output.read_bytes() == protected
    result = subprocess.run([sys.executable, "-B", "-m", "pdfmd.calibration", *map(str, paths),
                             "--output", str(tmp_path / "cli.json")], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path / "cli.json").read_bytes()) == json.loads(protected)
    data.study["route"]["endpoint"] = "https://user:PRIVATE_SECRET@example.com/v1/chat/completions"
    data.save()
    assert main([*map(str, paths), "--output", str(tmp_path / "invalid.json")]) == 2
    output_text = capsys.readouterr()
    assert "PRIVATE_SECRET" not in output_text.err and "invalid_study" in output_text.err
