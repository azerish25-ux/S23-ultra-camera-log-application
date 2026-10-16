"""TC-P120-03 Temporal integration energy.

Host fixture. Exposure integration is a normalized linear-domain sum.
Display-encoded averages and unnormalized weights are rejected. Trail extent
is |velocity| * window + 0.5 * |acceleration| * window^2. The window matches
the combined-report exposure.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

CASE_ID = "TC-P120-03"
NAME = "Temporal integration energy"
INTERVENTION = "Integrate known synthetic motion over an explicitly defined exposure window."
EXPECTED = "Match independent linear-domain energy and trail extent within the numerical tolerance."
NEGATIVE = "Averaging display-encoded frames or unnormalized temporal weights must fail."
REPEAT = "Repeat constant velocity, acceleration, and partial exposure at clip boundaries."
NEGATIVE_TOKEN = "display-encoded-average"
UNNORMALIZED_TOKEN = "unnormalized-temporal-weights"
ENERGY_TOKEN = "energy-or-trail-mismatch"
WINDOW_TOKEN = "exposure-window-disagrees-with-combined-report"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "combinationPassed",
    "report",
    "domain",
    "weights",
    "linearValues",
    "referenceEnergy",
    "velocity",
    "acceleration",
    "exposureWindow",
    "reportedTrailExtent",
    "partialBoundary",
)

_SPEC = importlib.util.spec_from_file_location(
    "p120_validate_combined_motion_and_optics",
    Path(__file__).resolve().parent / "p120_validate_combined_motion_and_optics.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def evaluate(payload: dict) -> dict:
    evidence, repeat = _CORE.require_payload(payload, PAYLOAD_KEYS)
    domain = payload["domain"]
    _CORE.require(domain in {"linear", "display"}, "domain must be linear or display")
    _CORE.require(type(payload["partialBoundary"]) is bool, "partialBoundary must be a bool")
    weights = payload["weights"]
    values = payload["linearValues"]
    _CORE.require(
        isinstance(weights, list) and isinstance(values, list) and bool(weights),
        "weights and linearValues must be non-empty lists",
    )
    _CORE.require(len(weights) == len(values), "weights and linearValues must have the same length")
    parsed_weights = [_CORE.require_number(item, f"weights[{index}]") for index, item in enumerate(weights)]
    parsed_values = [_CORE.require_number(item, f"linearValues[{index}]") for index, item in enumerate(values)]
    reference = _CORE.require_number(payload["referenceEnergy"], "referenceEnergy")
    velocity = _CORE.require_number(payload["velocity"], "velocity")
    acceleration = _CORE.require_number(payload["acceleration"], "acceleration")
    window = _CORE.require_number(payload["exposureWindow"], "exposureWindow")
    reported_trail = _CORE.require_number(payload["reportedTrailExtent"], "reportedTrailExtent")
    _CORE.require(window >= 0, "exposureWindow must be non-negative")
    judgement = _CORE.judge_report(payload["report"], combination_passed=payload["combinationPassed"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(judgement["reasons"])
    rejected = list(judgement["rejectedClaims"])
    weight_sum = math.fsum(parsed_weights)
    if domain != "linear":
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if not _CORE.exposures_match(weight_sum, 1.0):
        rejected.append(UNNORMALIZED_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("weightSum=" + _CORE.format_number(weight_sum))
    report_ready = _CORE.MISSING_FIELDS not in rejected and _CORE.EXPOSURE_MISMATCH not in rejected
    if report_ready:
        exposure = _CORE.require_number(payload["report"]["exposure_seconds"], "exposure_seconds")
        if not _CORE.exposures_match(window, exposure):
            rejected.append(WINDOW_TOKEN)
            reasons.append("exposure window must match the combined report")
    energy = math.fsum(weight * value for weight, value in zip(parsed_weights, parsed_values))
    expected_trail = abs(velocity) * window + 0.5 * abs(acceleration) * window * window
    if domain == "linear" and _CORE.exposures_match(weight_sum, 1.0):
        if not _CORE.exposures_match(energy, reference) or not _CORE.exposures_match(reported_trail, expected_trail):
            rejected.append(ENERGY_TOKEN)
            reasons.append(
                "integratedEnergy="
                + _CORE.format_number(energy)
                + " expectedTrail="
                + _CORE.format_number(expected_trail)
            )
        else:
            reasons.append("integratedEnergy=" + _CORE.format_number(energy))
            reasons.append("trailExtent=" + _CORE.format_number(expected_trail))
    if payload["partialBoundary"]:
        reasons.append("partial boundary uses the supplied exposure window only")
    preserved = [evidence]
    preserved.extend(judgement["preservedResults"])
    preserved.append("integratedEnergy=" + _CORE.format_number(energy))
    return _CORE.assemble_result(
        case_id=CASE_ID,
        evidence=evidence,
        reasons=reasons,
        rejected=rejected,
        preserved=preserved,
        repeat_note=REPEAT,
    )
