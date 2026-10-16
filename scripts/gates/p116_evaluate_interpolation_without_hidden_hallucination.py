#!/usr/bin/env python3
"""P116 Evaluate interpolation without hidden hallucination.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P116-01 through TC-P116-08 modules.

Estimated samples are linear interpolants between neighbouring captured
samples. Every estimated sample this module emits is tagged origin="estimated".
A submitted estimated sample tagged origin="captured" is a hidden hallucination
and is rejected. A withheld captured midpoint, when provided, contributes a
reported residual and is never used to relabel an estimate as captured.
Times outside the captured span are extrapolation and are rejected rather than
invented.
"""

from __future__ import annotations

import math
from typing import Any

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P116"
WORKSTREAM = 15
TITLE = "Evaluate interpolation without hidden hallucination"
GOAL = "Use motion interpolation only where it passes explicit scene and confidence tests."
METHOD = (
    "Compare candidate flow or learned interpolators on owned footage with high-frame-rate references. "
    "Inspect occlusions, thin structures, speculars, and repetitive patterns. Avoid cloud generation and "
    "store whether intermediate frames were synthesized."
)
FIXTURE = (
    "A rotating fan, crossing hands, and a fast moving reflective object with known high-rate reference footage."
)
ORACLE = (
    "Artifacts are quantified and low-confidence intervals can fall back without being presented as "
    "original sensor frames."
)
MUTANT = "Label synthesized intermediate frames as additional native captured frames."
DELIVERABLE = "Interpolation benchmark and provenance flags"
DEPENDENCIES = ("P115",)

ORIGIN_ESTIMATED = "estimated"
ORIGIN_CAPTURED = "captured"
HIDDEN_HALLUCINATION = "hidden-hallucination"
EXTRAPOLATION = "extrapolation-labelled-interpolation"
VALUE_MISMATCH = "estimated-value-not-linear-interpolation"

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "captured",
    "estimated",
    "withheldMidpoint",
}
SAMPLE_KEYS = {"time", "value", "origin"}
WITHHELD_KEYS = {"time", "value"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
ABSOLUTE_TOLERANCE = 1e-8
RELATIVE_TOLERANCE = 1e-9


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_number(value: Any, label: str) -> float:
    require(type(value) is not bool and isinstance(value, (int, float)), f"{label} must be a number")
    number = float(value)
    require(math.isfinite(number), f"{label} must be finite")
    return number


def require_text(value: Any, label: str, *, stripped: bool) -> str:
    require(isinstance(value, str) and value.strip(), f"{label} must be a non-empty string")
    if stripped:
        require(value == value.strip(), f"{label} must not have surrounding whitespace")
    return value


def format_number(value: float) -> str:
    return format(value, ".12g")


def fraction_token(estimated_count: int, total_count: int) -> str:
    require(total_count > 0, "total_count must be positive")
    ratio = estimated_count / total_count
    return f"interpolationFraction={estimated_count}/{total_count}={ratio}"


def linear_interpolation(
    left_value: float,
    right_value: float,
    left_time: float,
    right_time: float,
    time: float,
) -> float:
    """Linear sample between captured times t0 and t1. Not an extrapolator."""
    span = right_time - left_time
    require(span > 0, "captured times must be strictly increasing")
    weight = (time - left_time) / span
    return left_value + weight * (right_value - left_value)


def _parse_sample(item: Any, index: int, role: str) -> dict[str, Any]:
    require(isinstance(item, dict), f"{role}[{index}] must be an object")
    require(set(item) == SAMPLE_KEYS, f"{role}[{index}] keys must be time, value, origin")
    return {
        "time": require_number(item["time"], f"{role}[{index}].time"),
        "value": require_number(item["value"], f"{role}[{index}].value"),
        "origin": item["origin"],
    }


def parse_captured(samples: Any) -> list[dict[str, Any]]:
    require(isinstance(samples, list) and len(samples) >= 2, "captured must contain at least 2 samples")
    parsed = [_parse_sample(item, index, "captured") for index, item in enumerate(samples)]
    for index, sample in enumerate(parsed):
        require(sample["origin"] == ORIGIN_CAPTURED, f"captured[{index}].origin must be captured")
        if index:
            require(
                sample["time"] > parsed[index - 1]["time"],
                "captured times must be strictly increasing",
            )
    return parsed


def parse_estimated(samples: Any) -> list[dict[str, Any]]:
    require(isinstance(samples, list), "estimated must be a list")
    parsed = [_parse_sample(item, index, "estimated") for index, item in enumerate(samples)]
    for index, sample in enumerate(parsed):
        require(
            sample["origin"] in {ORIGIN_ESTIMATED, ORIGIN_CAPTURED},
            f"estimated[{index}].origin must be estimated or captured",
        )
        if index:
            require(
                sample["time"] > parsed[index - 1]["time"],
                "estimated times must be strictly increasing",
            )
    return parsed


def parse_withheld(value: Any) -> dict[str, float] | None:
    if value is None:
        return None
    require(isinstance(value, dict) and set(value) == WITHHELD_KEYS,
            "withheldMidpoint must be null or an object with time and value")
    return {
        "time": require_number(value["time"], "withheldMidpoint.time"),
        "value": require_number(value["value"], "withheldMidpoint.value"),
    }


def find_bracket(captured: list[dict[str, Any]], time: float) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for index in range(len(captured) - 1):
        left = captured[index]
        right = captured[index + 1]
        if left["time"] < time < right["time"]:
            return left, right
    return None


def evaluate_timeline(
    captured: Any,
    estimated: Any,
    withheld_midpoint: Any,
) -> dict[str, Any]:
    """Interpolate inside the captured span and keep provenance explicit.

    ``estimated_count / total_count`` counts submitted estimated slots over
    captured anchors plus those slots. The withheld midpoint is not an extra
    timeline sample. Out-of-span estimated times are rejected and are not given
    invented values.
    """
    anchors = parse_captured(captured)
    estimates = parse_estimated(estimated)
    withheld = parse_withheld(withheld_midpoint)
    estimated_count = len(estimates)
    total_count = len(anchors) + estimated_count
    token = fraction_token(estimated_count, total_count)
    first = anchors[0]["time"]
    last = anchors[-1]["time"]
    reasons = [token, f"fixture: {FIXTURE}"]
    preserved = [token]
    rejected: list[str] = []
    hidden = False
    extrapolated = False
    mismatch = False

    for sample in estimates:
        label = format_number(sample["time"])
        if sample["origin"] == ORIGIN_CAPTURED:
            hidden = True
            reasons.append(
                "hidden hallucination at t="
                + label
                + ": estimated sample presented as captured"
            )
        if sample["time"] < first or sample["time"] > last:
            extrapolated = True
            reasons.append(
                "extrapolation labelled interpolation is rejected at t=" + label
            )
            continue
        bracket = find_bracket(anchors, sample["time"])
        require(bracket is not None, "estimated time collides with a captured sample")
        left, right = bracket
        computed = linear_interpolation(
            left["value"], right["value"], left["time"], right["time"], sample["time"]
        )
        if not math.isclose(
            sample["value"], computed, rel_tol=RELATIVE_TOLERANCE, abs_tol=ABSOLUTE_TOLERANCE
        ):
            mismatch = True
            reasons.append(
                "estimated value at t="
                + label
                + " is not the linear interpolation "
                + format_number(computed)
            )
        tag = (
            "origin="
            + ORIGIN_ESTIMATED
            + " t="
            + label
            + " value="
            + format_number(computed)
        )
        preserved.append(tag)
        reasons.append(tag)

    if hidden:
        rejected.append(HIDDEN_HALLUCINATION)
    if extrapolated:
        rejected.append(EXTRAPOLATION)
    if mismatch:
        rejected.append(VALUE_MISMATCH)

    if withheld is None:
        reasons.append("withheldMidpointResidual=not-provided")
    else:
        bracket = find_bracket(anchors, withheld["time"])
        require(
            bracket is not None,
            "withheld midpoint must lie strictly between captured samples",
        )
        left, right = bracket
        computed = linear_interpolation(
            left["value"], right["value"], left["time"], right["time"], withheld["time"]
        )
        residual = abs(computed - withheld["value"])
        residual_token = "withheldMidpointResidual=" + format_number(residual)
        reasons.append(residual_token)
        preserved.append(residual_token)
        reasons.append("residual does not relabel estimated samples as captured")

    decision = "rejected" if rejected else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    return {
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
    }


def assess(document: dict) -> dict[str, Any]:
    """Apply the phase oracle and reject hidden interpolation hallucinations."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = require_text(document["evidenceId"], "evidenceId", stripped=True)
    claim = require_text(document["claim"], "claim", stripped=False)
    require(type(document["applyMutant"]) is bool, "applyMutant must be a bool")

    timeline = evaluate_timeline(
        document["captured"], document["estimated"], document["withheldMidpoint"]
    )
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "goal: " + GOAL,
    ]
    reasons.extend(timeline["reasons"])
    rejected = list(timeline["rejectedClaims"])
    if document["applyMutant"]:
        rejected.insert(0, MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("method: " + METHOD)
        reasons.append("deliverable: " + DELIVERABLE)
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    questions = [
        "physical S23 measurement was not run",
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
    ]
    preserved = [evidence, claim]
    preserved.extend(timeline["preservedResults"])
    result = {
        "caseId": PHASE,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(
        any("interpolationFraction=" in item for item in result["reasons"] + result["preservedResults"]),
        "interpolation fraction missing",
    )
    return result
