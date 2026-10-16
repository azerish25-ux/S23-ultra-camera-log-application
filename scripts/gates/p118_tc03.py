"""TC-P118-03 Temporal integration energy.

Host fixture. Exposure energy is the linear-domain weighted sum. Weights must
sum to 1. Trail extent is |velocity| * window + 0.5 * |acceleration| * window^2.
Display-encoded averages fail. Unknown readout does not shift rows.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path


CASE_ID = "TC-P118-03"
NAME = "Temporal integration energy"
INTERVENTION = "Integrate known synthetic motion over an explicitly defined exposure window."
EXPECTED = "Match independent linear-domain energy and trail extent within the numerical tolerance."
NEGATIVE = "Averaging display-encoded frames or unnormalized temporal weights must fail."
REPEAT = "Repeat constant velocity, acceleration, and partial exposure at clip boundaries."
NEGATIVE_TOKEN = "display-encoded-average"
UNNORMALIZED_TOKEN = "unnormalized-temporal-weights"
NEGATIVE_WEIGHT = "negative-weight"
ENERGY_TOKEN = "energy-or-trail-mismatch"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "domain",
    "weights",
    "linearValues",
    "referenceEnergy",
    "velocity",
    "acceleration",
    "exposureWindow",
    "reportedTrailExtent",
    "partialBoundary",
    "readoutSecondsPerRow",
    "readoutSource",
    "cameraVelocityY",
    "warpLabel",
    "claimsGlobalShutterRestored",
    "rows",
)

_SPEC = importlib.util.spec_from_file_location(
    "p118_investigate_rolling_shutter_correction_conservatively",
    Path(__file__).resolve().parent / "p118_investigate_rolling_shutter_correction_conservatively.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _number(value, label: str) -> float:
    if type(value) is bool or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=_CORE.RELATIVE_TOLERANCE, abs_tol=_CORE.ABSOLUTE_TOLERANCE)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    domain = payload["domain"]
    if domain not in {"linear", "display"}:
        raise ValueError("domain must be linear or display")
    if type(payload["partialBoundary"]) is not bool:
        raise ValueError("partialBoundary must be a bool")
    weights = payload["weights"]
    values = payload["linearValues"]
    if not isinstance(weights, list) or not isinstance(values, list) or not weights:
        raise ValueError("weights and linearValues must be non-empty lists")
    if len(weights) != len(values):
        raise ValueError("weights and linearValues must have the same length")
    parsed_weights = [_number(item, f"weights[{index}]") for index, item in enumerate(weights)]
    parsed_values = [_number(item, f"linearValues[{index}]") for index, item in enumerate(values)]
    reference = _number(payload["referenceEnergy"], "referenceEnergy")
    velocity = _number(payload["velocity"], "velocity")
    acceleration = _number(payload["acceleration"], "acceleration")
    window = _number(payload["exposureWindow"], "exposureWindow")
    reported = _number(payload["reportedTrailExtent"], "reportedTrailExtent")
    if window < 0.0:
        raise ValueError("exposureWindow must be non-negative")
    plan = _CORE.plan_correction(
        payload["readoutSecondsPerRow"],
        payload["readoutSource"],
        payload["cameraVelocityY"],
        payload["warpLabel"],
        payload["claimsGlobalShutterRestored"],
        payload["rows"],
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if domain != "linear":
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    negatives = [index for index, weight in enumerate(parsed_weights) if weight < 0.0]
    if negatives:
        rejected.append(NEGATIVE_WEIGHT)
        reasons.append("negative weight rejected and not dropped")
    weight_sum = math.fsum(parsed_weights)
    if not _close(weight_sum, 1.0):
        rejected.append(UNNORMALIZED_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("weightSum=" + _CORE.format_number(weight_sum))
    energy = math.fsum(weight * value for weight, value in zip(parsed_weights, parsed_values))
    expected_trail = abs(velocity) * window + 0.5 * abs(acceleration) * window * window
    if domain == "linear" and _close(weight_sum, 1.0) and not negatives:
        if not _close(energy, reference) or not _close(reported, expected_trail):
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
    reasons.extend(plan["reasons"])
    rejected.extend(plan["rejectedClaims"])
    preserved = [
        evidence,
        plan["reasons"][0],
        plan["reasons"][1],
        plan["originalY"],
        plan["yPrime"],
        plan["shiftPixels"],
        parsed_weights,
        energy,
        expected_trail,
    ]
    decision = "rejected" if rejected else "recorded"
    return _CORE.case_result(
        CASE_ID,
        decision,
        reasons,
        rejected,
        preserved,
        ["physical S23 measurement was not run", REPEAT],
    )
