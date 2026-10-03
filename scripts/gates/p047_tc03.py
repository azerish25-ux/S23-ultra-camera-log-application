"""TC-P047-03 matrix convention mismatch.

Intervention: Transpose or reverse one calibration transform while keeping all
numbers finite and plausible.
Expected: Fail the independent neutral and color-vector checks with a specific
convention error.
Negative: A finite determinant alone must not certify a color transform.
"""

from __future__ import annotations

CASE_ID = "TC-P047-03"
INTERVENTION = (
    "Transpose or reverse one calibration transform while keeping all numbers "
    "finite and plausible."
)
EXPECTED = (
    "Fail the independent neutral and color-vector checks with a specific "
    "convention error."
)
NEGATIVE = "A finite determinant alone must not certify a color transform."

_CONVENTIONS = (
    "row-major",
    "transposed",
    "reversed",
    "wrong-white-point",
    "duplicated-white-balance",
    "swapped-direction",
)
_CHECKS = ("pass", "fail")
_TOKEN = "abcdefghijklmnopqrstuvwxyz0123456789-:+."
_PAYLOAD_KEYS = (
    "matrixId",
    "convention",
    "determinantFinite",
    "neutralCheck",
    "colorVectorCheck",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "convention_held")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Fail a convention mismatch. A finite determinant does not certify it."""
    matrix_id, convention, finite, neutral, color = _payload(payload)
    preserved = [
        "matrix:" + matrix_id,
        "convention:" + convention,
        "determinantFinite:" + str(finite).lower(),
        "reported-neutral:" + neutral,
        "reported-color:" + color,
    ]
    rejected: list[str] = []
    reasons = [EXPECTED]
    if convention != "row-major":
        rejected.extend(
            [
                "convention-error:" + convention,
                "neutral-check-failed",
                "color-vector-check-failed",
            ]
        )
        reasons.append("specific convention error " + convention)
        reasons.append("independent neutral and color-vector checks failed")
        if finite:
            reasons.append(NEGATIVE)
    else:
        if not finite:
            rejected.append("non-finite-transform")
            reasons.append("non-finite transform is not a color convention")
        if neutral == "fail":
            rejected.append("neutral-check-failed")
        if color == "fail":
            rejected.append("color-vector-check-failed")
        if finite and not rejected:
            reasons.append("row-major convention recorded without colorimetric certification")
            reasons.append(NEGATIVE)
    if rejected:
        return _result(
            "rejected",
            reasons,
            rejected,
            preserved,
            ["finite determinant is not a colorimetric certificate"],
        )
    return _result(
        "convention_held",
        reasons,
        [],
        preserved,
        ["convention held is not physical colorimetric accuracy"],
    )


def _payload(payload: object) -> tuple[str, str, bool, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    convention = payload["convention"]
    if convention not in _CONVENTIONS:
        raise ValueError("convention is unsupported")
    finite = payload["determinantFinite"]
    if type(finite) is not bool:
        raise ValueError("determinantFinite must be a bool")
    neutral = payload["neutralCheck"]
    color = payload["colorVectorCheck"]
    if neutral not in _CHECKS or color not in _CHECKS:
        raise ValueError("checks must be pass or fail")
    matrix_id = payload["matrixId"]
    if not isinstance(matrix_id, str) or not matrix_id or any(char not in _TOKEN for char in matrix_id):
        raise ValueError("matrixId must be a canonical token")
    return matrix_id, convention, finite, neutral, color


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("convention decision cannot be qualified or allowed")
    if not reasons or any(type(item) is not str or not item for item in reasons):
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
