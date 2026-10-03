"""TC-P044-03 matrix convention mismatch.

Intervention: Transpose or reverse one calibration transform while keeping all
numbers finite and plausible.
Expected: Fail the independent neutral and color-vector checks with a specific
convention error.
Negative: A finite determinant alone must not certify a color transform.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P044-03"
INTERVENTION = (
    "Transpose or reverse one calibration transform while keeping all numbers finite "
    "and plausible."
)
EXPECTED = (
    "Fail the independent neutral and color-vector checks with a specific convention error."
)
NEGATIVE = "A finite determinant alone must not certify a color transform."

_TRANSFORMS = ("forward", "transposed", "reversed", "swapped_direction")
_WHITE = ("d65", "wrong", "duplicated_wb")
_PAYLOAD_KEYS = (
    "transform",
    "determinant",
    "neutralCheck",
    "colorVectorCheck",
    "whitePoint",
    "certifyByDeterminant",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "checks_held")
_FORBIDDEN = {"qualified", "allowed"}
_DET = re.compile(r"-?(?:[1-9][0-9]*)")


def evaluate(payload: dict) -> dict:
    """Fail a convention mismatch. A finite determinant is not a certificate."""
    transform, determinant, neutral, color, white, certify = _payload(payload)
    preserved = [
        f"transform:{transform}",
        f"determinant:{determinant}",
        f"white-point:{white}",
        f"neutral-check:{str(neutral).lower()}",
        f"color-vector-check:{str(color).lower()}",
    ]
    rejected: list[str] = []
    if transform != "forward":
        rejected.append(f"convention-error:{transform}")
    if white == "wrong":
        rejected.append("wrong-white-point")
    elif white == "duplicated_wb":
        rejected.append("duplicated-white-balance")
    if not neutral:
        rejected.append("neutral-check-failed")
    if not color:
        rejected.append("color-vector-check-failed")
    if certify:
        rejected.append("determinant-not-a-certificate")
    reasons = [EXPECTED]
    if rejected:
        decision = "rejected"
        if transform != "forward":
            reasons.append(f"specific convention error {transform}")
        if certify:
            reasons.append(NEGATIVE)
        if white != "d65":
            reasons.append(f"white point {white} is not an independent certificate")
        if not neutral or not color:
            reasons.append("independent neutral or color-vector check failed")
        questions = list(rejected)
    else:
        decision = "checks_held"
        reasons.append("checks held; a finite determinant did not certify the transform")
        questions = ["held checks are not a measured color profile"]
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, bool, bool, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    transform = payload["transform"]
    if transform not in _TRANSFORMS:
        raise ValueError("transform is unknown")
    determinant = payload["determinant"]
    if not isinstance(determinant, str) or _DET.fullmatch(determinant) is None:
        raise ValueError("determinant must be a finite non-zero canonical integer string")
    neutral = payload["neutralCheck"]
    color = payload["colorVectorCheck"]
    certify = payload["certifyByDeterminant"]
    if type(neutral) is not bool or type(color) is not bool or type(certify) is not bool:
        raise ValueError("checks and certifyByDeterminant must be bools")
    white = payload["whitePoint"]
    if white not in _WHITE:
        raise ValueError("whitePoint is unknown")
    return transform, determinant, neutral, color, white, certify


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("matrix decision cannot be qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
