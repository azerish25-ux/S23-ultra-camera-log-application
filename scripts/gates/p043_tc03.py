"""TC-P043-03 matrix convention mismatch.

Intervention: Transpose or reverse one calibration transform while keeping all
numbers finite and plausible.
Expected: Fail the independent neutral and color-vector checks with a specific
convention error.
Negative: A finite determinant alone must not certify a color transform.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P043-03"
INTERVENTION = (
    "Transpose or reverse one calibration transform while keeping all numbers "
    "finite and plausible."
)
EXPECTED = (
    "Fail the independent neutral and color-vector checks with a specific convention error."
)
NEGATIVE = "A finite determinant alone must not certify a color transform."

_FAULTS = (
    "none",
    "transposed",
    "reversed",
    "wrong-white",
    "duplicated-wb",
    "swapped-direction",
)
_PAYLOAD_KEYS = (
    "matrixId",
    "determinant",
    "finite",
    "fault",
    "neutralCheck",
    "colorVectorCheck",
    "certifyFromDeterminant",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "convention_checked", "withheld")
_FORBIDDEN = {"qualified", "allowed"}
_DET = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")


def evaluate(payload: dict) -> dict:
    """A finite determinant does not certify a transform. Name the convention fault."""
    matrix, determinant, fault, neutral, color, certify = _payload(payload)
    preserved = [f"matrix:{matrix}", f"determinant:{determinant}", f"fault:{fault}"]
    rejected: list[str] = []
    questions = ["finite determinant is not a color certificate"]
    if certify:
        decision = "rejected"
        rejected.append("determinant-certificate")
        if fault != "none":
            rejected.append(f"convention-error:{fault}")
        reasons = [NEGATIVE, EXPECTED, f"determinant {determinant} stayed finite and uncertified"]
    elif fault != "none":
        decision = "rejected"
        rejected.append(f"convention-error:{fault}")
        reasons = [
            EXPECTED,
            f"convention error {fault}",
            "neutral check failed",
            "color-vector check failed",
        ]
        if neutral:
            rejected.append("neutral-check-ignored")
        if color:
            rejected.append("color-vector-check-ignored")
    elif neutral and color:
        decision = "convention_checked"
        reasons = [
            "neutral and color-vector checks passed without a convention fault",
            "this check is not a physical color qualification",
        ]
        questions.append("host convention check is not a measured matrix")
    else:
        decision = "withheld"
        reasons = ["a failed check without a named convention fault stays withheld"]
        questions.append("convention fault was not identified")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    matrix = payload["matrixId"]
    if not isinstance(matrix, str) or not matrix or matrix != matrix.strip():
        raise ValueError("matrixId must be a non-empty string")
    determinant = payload["determinant"]
    if not isinstance(determinant, str) or _DET.fullmatch(determinant) is None:
        raise ValueError("determinant must be a canonical signed decimal string")
    finite = payload["finite"]
    if type(finite) is not bool or finite is not True:
        raise ValueError("finite must be true")
    fault = payload["fault"]
    if fault not in _FAULTS:
        raise ValueError("fault is not a known convention fault")
    neutral = _bool(payload["neutralCheck"], "neutralCheck")
    color = _bool(payload["colorVectorCheck"], "colorVectorCheck")
    certify = _bool(payload["certifyFromDeterminant"], "certifyFromDeterminant")
    return matrix, determinant, fault, neutral, color, certify


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


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
