"""TC-P103-03 Conversion accuracy regression.

Host fixture. Loading a model is not numerical qualification.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P103-03"
NAME = "Conversion accuracy regression"
INTERVENTION = "Compare exported or quantized model results against the approved host baseline on withheld scenes."
EXPECTED = "Meet declared depth and boundary tolerances or remain experimental despite successful loading."
NEGATIVE = "A model that merely runs is not numerically qualified."
REPEAT = "Repeat hair, glass, low light, thin objects, and saturated illumination."
NEGATIVE_TOKEN = "model-merely-runs-numerically-qualified"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "applyNegative",
    "applyMutant",
    "loaded",
    "depthError",
    "boundaryError",
    "depthTolerance",
    "boundaryTolerance",
    "numericallyQualifiedClaim",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _number(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise ValueError(f"{label} must be finite and >= 0")
    return number


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    if type(payload["applyNegative"]) is not bool or type(payload["applyMutant"]) is not bool:
        raise ValueError("flags must be bools")
    if type(payload["loaded"]) is not bool or type(payload["numericallyQualifiedClaim"]) is not bool:
        raise ValueError("loaded and numericallyQualifiedClaim must be bools")
    depth_error = _number(payload["depthError"], "depthError")
    boundary_error = _number(payload["boundaryError"], "boundaryError")
    depth_tolerance = _number(payload["depthTolerance"], "depthTolerance")
    boundary_tolerance = _number(payload["boundaryTolerance"], "boundaryTolerance")
    if depth_tolerance <= 0.0 or boundary_tolerance <= 0.0:
        raise ValueError("tolerances must be > 0")
    meets = depth_error <= depth_tolerance and boundary_error <= boundary_tolerance
    merely_runs = payload["loaded"] and payload["numericallyQualifiedClaim"] and not meets
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        f"depthError={depth_error:.6f}; depthTolerance={depth_tolerance:.6f}",
        f"boundaryError={boundary_error:.6f}; boundaryTolerance={boundary_tolerance:.6f}",
        f"loaded={payload['loaded']}; meetsTolerances={meets}",
    ]
    rejected: list[str] = []
    if payload["applyMutant"] or payload["applyNegative"] or merely_runs:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        if payload["loaded"] and not meets:
            reasons.append("remains experimental despite successful loading")
        elif meets:
            reasons.append("declared depth and boundary tolerances met; not a physical qualification")
        else:
            reasons.append("model did not load and is not numerically qualified")
        reasons.append("narrower software result retained; physical behavior stays open")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence],
        "openQuestions": ["physical S23 was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
