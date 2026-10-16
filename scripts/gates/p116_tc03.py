"""TC-P116-03 Temporal integration energy.

Host fixture. Exposure integration is a normalized linear-domain sum.
Display-encoded averages and unnormalized weights are rejected. Trail extent
follows constant velocity plus half acceleration times window squared.
Estimated frames stay origin=estimated.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

CASE_ID = "TC-P116-03"
NAME = "Temporal integration energy"
INTERVENTION = "Integrate known synthetic motion over an explicitly defined exposure window."
EXPECTED = "Match independent linear-domain energy and trail extent within the numerical tolerance."
NEGATIVE = "Averaging display-encoded frames or unnormalized temporal weights must fail."
REPEAT = "Repeat constant velocity, acceleration, and partial exposure at clip boundaries."
NEGATIVE_TOKEN = "display-encoded-average"
UNNORMALIZED_TOKEN = "unnormalized-temporal-weights"
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
    "captured",
    "estimated",
    "withheldMidpoint",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_SPEC = importlib.util.spec_from_file_location(
    "p116_evaluate_interpolation_without_hidden_hallucination",
    Path(__file__).resolve().parent / "p116_evaluate_interpolation_without_hidden_hallucination.py",
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
    reported_trail = _number(payload["reportedTrailExtent"], "reportedTrailExtent")
    if window < 0:
        raise ValueError("exposureWindow must be non-negative")
    timeline = _CORE.evaluate_timeline(
        payload["captured"], payload["estimated"], payload["withheldMidpoint"]
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(timeline["reasons"])
    rejected = list(timeline["rejectedClaims"])
    weight_sum = math.fsum(parsed_weights)
    if domain != "linear":
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if not _close(weight_sum, 1.0):
        rejected.append(UNNORMALIZED_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("weightSum=" + format(weight_sum, ".12g"))
    energy = math.fsum(weight * value for weight, value in zip(parsed_weights, parsed_values))
    expected_trail = abs(velocity) * window + 0.5 * abs(acceleration) * window * window
    if domain == "linear" and _close(weight_sum, 1.0):
        if not _close(energy, reference) or not _close(reported_trail, expected_trail):
            rejected.append(ENERGY_TOKEN)
            reasons.append(
                "integratedEnergy="
                + format(energy, ".12g")
                + " expectedTrail="
                + format(expected_trail, ".12g")
            )
        else:
            reasons.append("integratedEnergy=" + format(energy, ".12g"))
            reasons.append("trailExtent=" + format(expected_trail, ".12g"))
    if payload["partialBoundary"]:
        reasons.append("partial boundary uses the supplied exposure window only")
    preserved = [evidence]
    preserved.extend(timeline["preservedResults"])
    decision = "rejected" if rejected else "recorded"
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
