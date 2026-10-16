#!/usr/bin/env python3
"""P120 Validate combined motion and optics.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P120-01 through TC-P120-08 modules.

A combined report is recorded only when shutter timing, disclosed interpolation,
stabilization crop, and rolling-shutter readout agree. Independent spot-checks
and ablations cannot claim that combination passed. The decision is recorded
or rejected, never qualified or allowed.
"""

from __future__ import annotations

import math
from typing import Any

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P120"
WORKSTREAM = 15
TITLE = "Validate combined motion and optics"
GOAL = "Test temporal interactions between shutter simulation, stabilization, depth, and focus."
METHOD = (
    "Use a fixed graph order with shared geometry and timing semantics. Compare ablations and "
    "perfect-motion fixtures. Record whether a defect originates from source blur, flow, "
    "stabilization, depth, or compositing before changing multiple algorithms."
)
FIXTURE = "A handheld focus pull with foreground occlusion, bright bokeh, and synthetic shutter enabled."
ORACLE = "The complete clip maintains coherent motion without doubled edges, drifting masks, or discontinuous focus."
MUTANT = "Approve each temporal effect independently and skip their combined regression."
DELIVERABLE = "Motion-optics integration benchmark and release envelope"
DEPENDENCIES = ("P119",)

EXPOSURE_TOLERANCE = 1e-9
GRAPH_ORDER = (
    "source_blur",
    "shutter",
    "interpolation",
    "stabilization",
    "depth",
    "focus",
    "compositing",
)
COMPARISONS = (
    "perfect-motion",
    "source_blur",
    "flow",
    "stabilization",
    "depth",
    "compositing",
)
DEFECT_ORIGINS = ("source_blur", "flow", "stabilization", "depth", "compositing")
REPORT_FIELDS = (
    "shutter_angle",
    "fps",
    "exposure_seconds",
    "interpolation_fraction",
    "estimated_disclosed",
    "stabilization_crop_fraction",
    "rolling_shutter_readout",
    "correction_applied",
)
READOUTS = ("measured", "unknown")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "combinationPassed",
    "comparison",
    "graphOrder",
    "report",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

MISSING_FIELDS = "combined-report-field-missing"
EXPOSURE_MISMATCH = "exposure-seconds-does-not-match-shutter-formula"
INTERPOLATION_UNDISCLOSED = "interpolation-not-disclosed"
UNKNOWN_READOUT_CORRECTION = "correction-applied-with-unknown-readout"
SPOT_CHECK = "shutter-only-spot-check-claimed-combination-passed"
GRAPH_ORDER_TOKEN = "graph-order-not-shared"
ABLATION_TOKEN = "ablation-claimed-combination-passed"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_number(value: Any, label: str) -> float:
    require(type(value) is not bool and isinstance(value, (int, float)), f"{label} must be a number")
    number = float(value)
    require(math.isfinite(number), f"{label} must be finite")
    return number


def require_text(value: Any, label: str) -> str:
    require(isinstance(value, str) and value.strip(), f"{label} must be a non-empty string")
    require(value == value.strip(), f"{label} must not have surrounding whitespace")
    return value


def expected_exposure(shutter_angle: float, fps: float) -> float:
    """Exposure implied by a shutter angle at a frame rate: (angle/360)/fps."""
    require(fps > 0, "fps must be positive")
    return (shutter_angle / 360.0) / fps


def exposures_match(actual: float, expected: float) -> bool:
    return abs(actual - expected) <= EXPOSURE_TOLERANCE


def format_number(value: float) -> str:
    return format(value, ".12g")


def _parse_report_field(field: str, value: Any) -> Any:
    if field in {"shutter_angle", "fps", "exposure_seconds", "interpolation_fraction", "stabilization_crop_fraction"}:
        number = require_number(value, field)
        if field == "fps":
            require(number > 0, "fps must be positive")
        if field == "interpolation_fraction":
            require(0.0 <= number <= 1.0, "interpolation_fraction must be inside [0, 1]")
        if field == "stabilization_crop_fraction":
            require(0.0 <= number <= 1.0, "stabilization_crop_fraction must be inside [0, 1]")
        return number
    if field in {"estimated_disclosed", "correction_applied"}:
        require(type(value) is bool, field + " must be a bool")
        return value
    if field == "rolling_shutter_readout":
        require(value in READOUTS, "rolling_shutter_readout must be measured or unknown")
        return value
    raise ValueError("unknown report field " + field)


def _preserve_field(field: str, value: Any) -> str:
    if isinstance(value, bool):
        return field + "=" + str(value).lower()
    if isinstance(value, float) or isinstance(value, int):
        return field + "=" + format_number(float(value))
    return field + "=" + str(value)


def judge_report(report: Any, *, combination_passed: bool) -> dict[str, Any]:
    """Apply the combined motion-optics consistency rules.

    Missing report fields and inconsistent honest-looking claims are rejected.
    A shutter-angle-only spot-check that claims the combination passed is rejected.
    Malformed types raise ValueError. Consistent reports are not qualified.
    """
    require(isinstance(report, dict), "report must be an object")
    require(type(combination_passed) is bool, "combinationPassed must be a bool")
    unknown = set(report) - set(REPORT_FIELDS)
    require(not unknown, "report has unexpected fields: " + ", ".join(sorted(unknown)))
    parsed: dict[str, Any] = {}
    for field in REPORT_FIELDS:
        if field in report:
            parsed[field] = _parse_report_field(field, report[field])
    missing = [field for field in REPORT_FIELDS if field not in report]
    reasons: list[str] = []
    rejected: list[str] = []
    origins: list[str] = []
    if missing:
        rejected.append(MISSING_FIELDS)
        reasons.append("missing combined report fields: " + ", ".join(missing))
        origins.append("compositing")
    if set(report) == {"shutter_angle"} and combination_passed:
        rejected.append(SPOT_CHECK)
        reasons.append("a spot-check that only includes shutter_angle cannot claim the combination passed")
        if "compositing" not in origins:
            origins.append("compositing")
    if not missing:
        angle = parsed["shutter_angle"]
        fps = parsed["fps"]
        exposure = parsed["exposure_seconds"]
        fraction = parsed["interpolation_fraction"]
        disclosed = parsed["estimated_disclosed"]
        readout = parsed["rolling_shutter_readout"]
        applied = parsed["correction_applied"]
        expected = expected_exposure(angle, fps)
        if not exposures_match(exposure, expected):
            rejected.append(EXPOSURE_MISMATCH)
            reasons.append(
                "exposure_seconds="
                + format_number(exposure)
                + " expected="
                + format_number(expected)
                + " tolerance=1e-9"
            )
            origins.append("source_blur")
        else:
            reasons.append(
                "exposure_seconds=" + format_number(exposure) + "=(shutter_angle/360)/fps"
            )
        if fraction > 0 and not disclosed:
            rejected.append(INTERPOLATION_UNDISCLOSED)
            reasons.append("interpolation_fraction > 0 requires estimated_disclosed")
            origins.append("flow")
        elif disclosed:
            reasons.append("estimated samples disclosed")
        else:
            reasons.append("no undisclosed interpolation")
        if applied and readout == "unknown":
            rejected.append(UNKNOWN_READOUT_CORRECTION)
            reasons.append("correction_applied cannot be true while rolling_shutter_readout is unknown")
            origins.append("stabilization")
        elif applied:
            reasons.append("rolling-shutter correction uses a measured readout")
        else:
            reasons.append("rolling-shutter correction was not applied")
    preserved = [_preserve_field(field, parsed[field]) for field in REPORT_FIELDS if field in parsed]
    for origin in origins:
        token = "defectOrigin=" + origin
        reasons.append(token)
        preserved.append(token)
    return {
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "defectOrigins": origins,
    }


def require_payload(payload: Any, keys: tuple[str, ...]) -> tuple[str, str]:
    require(isinstance(payload, dict) and set(payload) == set(keys), "invalid payload keys")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    require(type(payload["combinationPassed"]) is bool, "combinationPassed must be a bool")
    return evidence, repeat


def assemble_result(
    *,
    case_id: str,
    evidence: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    repeat_note: str,
) -> dict[str, Any]:
    decision = "rejected" if rejected else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    if decision == "recorded":
        reasons.append("defectOrigin=none")
        preserved.append("defectOrigin=none")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 measurement was not run", repeat_note],
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(bool(result["reasons"]), "reasons must be non-empty")
    return result


def assess(document: dict) -> dict[str, Any]:
    """Record a consistent combined report or reject a skipped combination."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = require_text(document["evidenceId"], "evidenceId")
    claim = require_text(document["claim"], "claim")
    require(type(document["applyMutant"]) is bool, "applyMutant must be a bool")
    require(type(document["combinationPassed"]) is bool, "combinationPassed must be a bool")
    require(document["comparison"] in COMPARISONS, "comparison must name perfect-motion or an ablation")
    order = document["graphOrder"]
    require(
        isinstance(order, list) and all(isinstance(item, str) for item in order),
        "graphOrder must be a list of strings",
    )
    judgement = judge_report(document["report"], combination_passed=document["combinationPassed"])
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "goal: " + GOAL,
        "fixture: " + FIXTURE,
    ]
    reasons.extend(judgement["reasons"])
    rejected = list(judgement["rejectedClaims"])
    if tuple(order) != GRAPH_ORDER:
        rejected.append(GRAPH_ORDER_TOKEN)
        reasons.append("graph order must stay " + ">".join(GRAPH_ORDER))
        reasons.append("defectOrigin=compositing")
    else:
        reasons.append("graphOrder=" + ">".join(GRAPH_ORDER))
    if document["comparison"] != "perfect-motion" and document["combinationPassed"]:
        rejected.append(ABLATION_TOKEN)
        reasons.append("ablation " + document["comparison"] + " cannot claim the combination passed")
        reasons.append("defectOrigin=" + document["comparison"])
    elif document["comparison"] != "perfect-motion":
        reasons.append("ablation " + document["comparison"] + " compared; combination not claimed")
    else:
        reasons.append("perfect-motion fixture uses the full graph")
    if document["applyMutant"]:
        rejected.insert(0, MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
    preserved = [evidence, claim]
    preserved.extend(judgement["preservedResults"])
    if tuple(order) == GRAPH_ORDER:
        preserved.append("graphOrder=" + ">".join(GRAPH_ORDER))
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("method: " + METHOD)
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("defectOrigin=none")
        preserved.append("defectOrigin=none")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    questions = [
        "physical S23 measurement was not run",
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
    ]
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
    return result
