"""Offline fixed-payload calibration reports; no fitting or runtime authority."""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
from typing import Annotated, Any, Literal

from pydantic import Field, StrictBool, StrictInt, StrictStr, ValidationError, field_validator, model_validator

from . import request_estimation
from .nexus import StopRun, unique_object
from .schema import Route, Strict
from .storage import encode
from .usage import interpret_usage


Digest = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]
Name = Annotated[StrictStr, Field(min_length=1)]
Nonnegative = Annotated[StrictInt, Field(ge=0)]
Positive = Annotated[StrictInt, Field(ge=1)]
Version = Annotated[StrictInt, Field(ge=1, le=1)]


class EvaluationError(ValueError):
    """A safe reason code, without native content or configuration values."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ratio(value: str) -> Fraction:
    try:
        result = Fraction(value)
    except (ValueError, ZeroDivisionError):
        raise ValueError("A finite nonnegative rational string is required.") from None
    if result < 0:
        raise ValueError("A finite nonnegative rational string is required.")
    return result


class Candidate(Strict):
    id: Name
    text_margin: StrictStr
    fixed_tokens: Nonnegative
    image_tokens: Nonnegative

    @field_validator("text_margin")
    @classmethod
    def valid_ratio(cls, value):
        ratio(value)
        return value


class Measurement(Strict):
    method: Name
    modality_projection: Name
    vocabulary_sha256: Digest


class Gates(Strict):
    max_run_overestimate_pct: StrictStr
    max_group_overestimate_pct: StrictStr
    min_known_per_run: Positive
    min_known_per_group: Positive
    required_groups: list[Name] = Field(min_length=1)
    require_fit_improvement: StrictBool

    @field_validator("max_run_overestimate_pct", "max_group_overestimate_pct")
    @classmethod
    def valid_ratio(cls, value):
        ratio(value)
        return value


class Validation(Strict):
    predeclared: StrictBool
    source_sha256: list[Digest]


class Study(Strict):
    version: Version
    route: Route
    measurement: Measurement
    candidates: list[Candidate] = Field(min_length=1)
    gates: Gates
    validation: Validation

    @model_validator(mode="after")
    def unique_declarations(self):
        for values in ([c.id for c in self.candidates], self.gates.required_groups, self.validation.source_sha256):
            if len(set(values)) != len(values):
                raise ValueError("Duplicate study declarations.")
        return self


class FileRef(Strict):
    path: Name
    sha256: Digest


class Observation(Strict):
    id: Name
    run: Name
    attempt_id: Name
    partition: Literal["development", "validation"]
    source_sha256: Digest | None
    previously_inspected: StrictBool | None
    request_kind: Literal["normal", "compaction"]
    group: Name
    payload: FileRef
    usage: FileRef


class Corpus(Strict):
    version: Version
    study_sha256: Digest
    observations: list[Observation]

    @model_validator(mode="after")
    def unique_exposures(self):
        ids = [o.id for o in self.observations]
        attempts = [(o.run, o.attempt_id) for o in self.observations]
        if len(set(ids)) != len(ids) or len(set(attempts)) != len(attempts):
            raise ValueError("Duplicate observation or physical attempt.")
        return self


class UsageRecord(Strict):
    run: Name
    attempt_id: Name
    protocol: Literal["chat_completions", "responses"]
    request_sha256: Digest
    route_sha256: Digest
    accounting: Name
    native_usage: Any


def route_fingerprint(route: Route) -> str:
    return digest(encode(route.model_dump(mode="json")))


def read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        raise EvaluationError("read_failed") from None


def decode(data: bytes):
    def nonfinite(_):
        raise ValueError("Non-finite JSON")
    try:
        return json.loads(data, object_pairs_hook=unique_object, parse_constant=nonfinite)
    except (ValueError, UnicodeError):
        raise EvaluationError("invalid_json") from None


def model(kind, data, reason):
    try:
        return kind.model_validate(data)
    except ValidationError:
        raise EvaluationError(reason) from None


def referenced(ref: FileRef, root: Path) -> bytes:
    try:
        path = (root / ref.path).resolve()
    except (ValueError, OSError):
        raise EvaluationError("invalid_reference_path") from None
    raw = read_bytes(path)
    if digest(raw) != ref.sha256:
        raise EvaluationError("sha256_mismatch")
    return raw


def measure(study: Study, observation: Observation, root: Path) -> dict:
    row = observation.model_dump(exclude={"payload", "usage"})
    row.update(payload_sha256=observation.payload.sha256, usage_sha256=observation.usage.sha256,
               baseline=None, estimate_reason=None, usage_input=None, usage_status="unknown", usage_reason=None)
    try:
        raw = referenced(observation.payload, root)
        payload = decode(raw)
        if not isinstance(payload, dict):
            raise EvaluationError("invalid_payload_container")
        if encode(payload) != raw:
            raise EvaluationError("noncanonical_payload")
        baseline = request_estimation.estimate(payload, study.route)
        row["baseline"] = baseline
        if baseline["fallback"] is not None:
            row["estimate_reason"] = "bpe_unavailable:" + baseline["fallback"]
        elif any(baseline.get(key) != value for key, value in study.measurement.model_dump().items()):
            row["estimate_reason"] = "measurement_identity_mismatch"
    except StopRun as exc:
        row["estimate_reason"] = exc.reason
    except UnicodeError:
        row["estimate_reason"] = "invalid_payload_utf8"
    except EvaluationError as exc:
        row["estimate_reason"] = str(exc)
    try:
        usage = model(UsageRecord, decode(referenced(observation.usage, root)), "invalid_usage_record")
        expected = (observation.run, observation.attempt_id, study.route.protocol,
                    observation.payload.sha256, route_fingerprint(study.route))
        actual = (usage.run, usage.attempt_id, usage.protocol, usage.request_sha256, usage.route_sha256)
        if actual != expected:
            raise EvaluationError("usage_attribution_mismatch")
        if usage.accounting != "inclusive_input_v1":
            raise EvaluationError("unsupported_input_accounting")
        interpreted = interpret_usage(study.route.protocol, usage.native_usage)
        row["usage_status"] = interpreted.status
        row["usage_reason"] = interpreted.reason
        key = "prompt_tokens" if study.route.protocol == "chat_completions" else "input_tokens"
        row["usage_input"] = (interpreted.value or {}).get(key)
        if row["usage_input"] is None and row["usage_reason"] is None:
            row["usage_reason"] = "input_missing"
    except EvaluationError as exc:
        row["usage_reason"] = str(exc)
    return row


def percentage(numerator: int, denominator: int) -> str | None:
    if denominator == 0:
        return None
    # Display only. Gates compare exact Fractions, never these rounded strings.
    return format(Fraction(numerator * 100, denominator), ".6f")


def metrics(rows: list[dict]) -> dict:
    scored = [r for r in rows if r["usage_input"] is not None and r["input_estimate"] is not None]
    errors = [r["input_estimate"] - r["usage_input"] for r in scored]
    incoming = sum(r["usage_input"] for r in scored)
    excess = sum(max(e, 0) for e in errors)
    relatives = [Fraction(abs(r["input_estimate"] - r["usage_input"]), r["usage_input"])
                 for r in scored if r["usage_input"] > 0]
    zero_denominators = sum(r["usage_input"] == 0 for r in scored)
    return {"total_rows": len(rows), "physical_attempts": len(rows),
            "unique_payloads": len({r["payload_sha256"] for r in rows}),
            "known_usage_rows": sum(r["usage_input"] is not None for r in rows),
            "unknown_usage_rows": sum(r["usage_input"] is None for r in rows),
            "unavailable_estimate_rows": sum(r["input_estimate"] is None for r in rows),
            "scored_rows": len(scored), "scored_input_tokens": incoming,
            "signed_error_tokens": sum(errors), "positive_excess_tokens": excess,
            "undercount_count": sum(e < 0 for e in errors),
            "worst_undercount_tokens": max([0, *[-e for e in errors if e < 0]]),
            "weighted_signed_error_pct": percentage(sum(errors), incoming),
            "weighted_overestimate_pct": percentage(excess, incoming),
            "zero_usage_denominators": zero_denominators,
            "max_absolute_relative_error_pct": (format(max(relatives) * 100, ".6f")
                                                if relatives and not zero_denominators else None)}


def summary(rows: list[dict]) -> dict:
    partitions = {}
    for partition in ("development", "validation"):
        selected = [r for r in rows if r["partition"] == partition]
        partitions[partition] = {"overall": metrics(selected), **{
            name: {key: metrics([r for r in selected if r[field] == key])
                   for key in sorted({r[field] for r in selected})}
            for name, field in (("runs", "run"), ("groups", "group"))}}
    return {"overall": metrics(rows), "partitions": partitions}


def gate(study: Study, rows: list[dict], stats: dict) -> dict:
    failures, gaps = [], []
    development = [r for r in rows if r["partition"] == "development"]
    validation = [r for r in rows if r["partition"] == "validation"]
    if stats["overall"]["undercount_count"]:
        failures.append("observed_undercount")
    if not validation:
        gaps.append("no_validation_rows")
    if not study.validation.predeclared:
        gaps.append("validation_not_predeclared")
    if any(r["source_sha256"] is None for r in rows):
        gaps.append("unknown_source_identity")
    for field in ("source_sha256", "run", "payload_sha256"):
        left = {r[field] for r in development if r[field] is not None}
        right = {r[field] for r in validation if r[field] is not None}
        if left & right:
            gaps.append("partition_overlap:" + field)
    declared = set(study.validation.source_sha256)
    observed = {r["source_sha256"] for r in validation}
    if not declared or declared - observed:
        gaps.append("missing_validation_source")
    if observed - declared:
        gaps.append("undeclared_validation_source")
    if any(r["previously_inspected"] is not False for r in validation):
        gaps.append("validation_inspected_or_unconfirmed")
    if any(r["input_estimate"] is None for r in rows):
        gaps.append("unavailable_estimate")
    if any(r["usage_input"] is None for r in validation):
        gaps.append("unknown_validation_usage")
    required = set(study.gates.required_groups)
    groups = {r["group"] for r in validation}
    if required - groups:
        gaps.append("missing_validation_group")
    if groups - required:
        gaps.append("undeclared_validation_group")
    for name, minimum, limit in (
        ("runs", study.gates.min_known_per_run, study.gates.max_run_overestimate_pct),
        ("groups", study.gates.min_known_per_group, study.gates.max_group_overestimate_pct)):
        for label, values in stats["partitions"]["validation"][name].items():
            if values["scored_rows"] < minimum:
                gaps.append("insufficient_support:" + name + ":" + label)
            elif values["scored_input_tokens"] == 0:
                gaps.append("zero_usage_denominator:" + name + ":" + label)
            elif Fraction(values["positive_excess_tokens"] * 100, values["scored_input_tokens"]) > ratio(limit):
                failures.append("excess_limit:" + name + ":" + label)
    improved = any(r["baseline"] is not None and not r["baseline"]["fits"] and r["candidate_fit"] is True for r in rows)
    if study.gates.require_fit_improvement and not improved:
        gaps.append("fixed_payload_fit_improvement_not_observed")
    return {"status": "fail" if failures else "inconclusive" if gaps else "pass",
            "failures": failures, "evidence_gaps": gaps, "fixed_payload_fit_improvement": improved,
            "meaning": "declared_finite_corpus_checks_only_not_production_adoption"}


def load(study_path: str | Path, corpus_path: str | Path):
    study_path, corpus_path = Path(study_path).resolve(), Path(corpus_path).resolve()
    study_raw, corpus_raw = read_bytes(study_path), read_bytes(corpus_path)
    study = model(Study, decode(study_raw), "invalid_study")
    corpus = model(Corpus, decode(corpus_raw), "invalid_corpus")
    if corpus.study_sha256 != digest(study_raw):
        raise EvaluationError("study_binding_mismatch")
    return study, corpus, study_raw, corpus_raw, corpus_path.parent


def evaluate(study_path: str | Path, corpus_path: str | Path) -> dict:
    return evaluate_loaded(*load(study_path, corpus_path))


def evaluate_loaded(study: Study, corpus: Corpus, study_raw: bytes, corpus_raw: bytes, root: Path) -> dict:
    measured = [measure(study, o, root) for o in corpus.observations]
    candidates = []
    for candidate in study.candidates:
        rows = []
        margin = ratio(candidate.text_margin)
        for original in measured:
            row = {**original, "input_estimate": None, "candidate_fit": None,
                   "signed_error_tokens": None, "signed_error_pct": None}
            baseline = row["baseline"]
            if row["estimate_reason"] is None and baseline is not None:
                text = baseline["text_tokens"]
                reserve = (text * margin.numerator + margin.denominator - 1) // margin.denominator
                row["input_estimate"] = text + reserve + candidate.fixed_tokens + baseline["images"] * candidate.image_tokens
                row["candidate_fit"] = row["input_estimate"] + study.route.output_tokens <= study.route.context_tokens
                if row["usage_input"] is not None:
                    row["signed_error_tokens"] = row["input_estimate"] - row["usage_input"]
                    row["signed_error_pct"] = percentage(row["signed_error_tokens"], row["usage_input"])
            rows.append(row)
        stats = summary(rows)
        candidates.append({"candidate": candidate.model_dump(), "summary": stats,
                           "gate": gate(study, rows, stats), "rows": rows})
    baseline_rows = [{**r, "input_estimate": r["baseline"]["input_estimate"] if r["baseline"] else None} for r in measured]
    return {"version": 1, "study_sha256": digest(study_raw), "corpus_sha256": digest(corpus_raw),
            "route_sha256": route_fingerprint(study.route), "measurement": study.measurement.model_dump(),
            "estimator_source_sha256": digest(read_bytes(Path(request_estimation.__file__))),
            "evaluator_source_sha256": digest(read_bytes(Path(__file__))),
            "gates": study.gates.model_dump(), "validation_declaration": study.validation.model_dump(),
            "baseline": summary(baseline_rows), "candidates": candidates,
            "limits": ["No fitting, selected profile, production activation, network or task mutation.",
                       "Validation chronology and semantic independence are supplied claims, not proved by hashes.",
                       "Same canonical frozen bytes only; feedback is not reassembled for candidate profiles.",
                       "Configured capacity is not a discovered route limit; usage is not a bill.",
                       "No upstream acceptance, unseen-input bound, source fidelity or savings is established."]}


def write_report(study_path: str | Path, corpus_path: str | Path, output: str | Path) -> dict:
    loaded = load(study_path, corpus_path)
    _, corpus, _, _, root = loaded
    try:
        inputs = {Path(study_path).resolve(), Path(corpus_path).resolve(), *[
            (root / ref.path).resolve() for row in corpus.observations for ref in (row.payload, row.usage)]}
        output = Path(output).resolve()
    except (ValueError, OSError):
        raise EvaluationError("invalid_reference_path") from None
    if output in inputs:
        raise EvaluationError("output_is_input")
    report = evaluate_loaded(*loaded)
    try:
        with output.open("xb") as stream:
            stream.write(encode(report))
    except FileExistsError:
        raise EvaluationError("output_exists") from None
    except OSError:
        raise EvaluationError("output_write_failed") from None
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", type=Path)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="New exclusive JSON report; never overwrites an input/result.")
    args = parser.parse_args(argv)
    try:
        report = write_report(args.study, args.corpus, args.output)
    except EvaluationError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps({"report": str(args.output), "candidates": {
        c["candidate"]["id"]: c["gate"]["status"] for c in report["candidates"]}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
