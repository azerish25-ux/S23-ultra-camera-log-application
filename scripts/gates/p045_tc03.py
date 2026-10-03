"""TC-P045-03 matrix convention mismatch.

Intervention: Transpose or reverse one calibration transform while keeping all
numbers finite and plausible.
Expected: Fail the independent neutral and color-vector checks with a specific
convention error.
Negative: A finite determinant alone must not certify a color transform.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P045-03"
INTERVENTION = (
    "Transpose or reverse one calibration transform while keeping all numbers "
    "finite and plausible."
)
EXPECTED = (
    "Fail the independent neutral and color-vector checks with a specific "
    "convention error."
)
NEGATIVE = "A finite determinant alone must not certify a color transform."

_CONVENTIONS = ("row_major", "transposed", "reversed", "swapped_direction")
_CONVENTION_ERRORS = {"transposed", "reversed", "swapped_direction"}
_WHITE = ("matched", "wrong")
_BALANCE = ("single", "duplicated")
_CHECKS = ("pass", "fail")
_PAYLOAD_KEYS = (
    "matrixId",
    "convention",
    "determinantFinite",
    "whitePoint",
    "whiteBalance",
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
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")


def evaluate(payload: dict) -> dict:
    """Fail a convention mismatch. A finite determinant is not a certificate."""
    (
        matrix_id,
        convention,
        finite,
        white_point,
        white_balance,
        neutral_check,
        color_check,
    ) = _payload(payload)
    preserved = [
        f"matrix:{matrix_id}",
        f"convention:{convention}",
        "determinant:" + ("finite" if finite else "non-finite"),
        f"white-point:{white_point}",
        f"white-balance:{white_balance}",
        f"neutral-check:{neutral_check}",
        f"color-vector:{color_check}",
    ]
    rejected: list[str] = []
    if convention in _CONVENTION_ERRORS:
        rejected.append(f"convention:{convention}")
    if white_point == "wrong":
        rejected.append("wrong-white-point")
    if white_balance == "duplicated":
        rejected.append("duplicated-white-balance")
    if neutral_check == "fail":
        rejected.append("neutral-check")
    if color_check == "fail":
        rejected.append("color-vector-check")
    if not finite:
        rejected.append("non-finite-determinant")
    reasons = [EXPECTED, INTERVENTION]
    questions: list[str] = []
    clean = (
        convention == "row_major"
        and white_point == "matched"
        and white_balance == "single"
        and neutral_check == "pass"
        and color_check == "pass"
        and finite
    )
    if clean:
        decision = "convention_checked"
        reasons.append("independent neutral and color-vector checks passed")
        reasons.append("a finite determinant was not the certificate")
    else:
        decision = "rejected"
        if finite:
            rejected.append("finite-determinant-not-certificate")
            reasons.append(NEGATIVE)
        reasons.append("convention or independent checks failed")
        questions.append("color transform was not certified from a finite determinant")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, bool, str, str, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    matrix_id = payload["matrixId"]
    if not isinstance(matrix_id, str) or _TOKEN.fullmatch(matrix_id) is None:
        raise ValueError("matrixId must be a token")
    convention = payload["convention"]
    if convention not in _CONVENTIONS:
        raise ValueError("convention is unsupported")
    finite = payload["determinantFinite"]
    if type(finite) is not bool:
        raise ValueError("determinantFinite must be a bool")
    white_point = payload["whitePoint"]
    if white_point not in _WHITE:
        raise ValueError("whitePoint must be matched or wrong")
    white_balance = payload["whiteBalance"]
    if white_balance not in _BALANCE:
        raise ValueError("whiteBalance must be single or duplicated")
    neutral_check = payload["neutralCheck"]
    color_check = payload["colorVectorCheck"]
    if neutral_check not in _CHECKS or color_check not in _CHECKS:
        raise ValueError("checks must be pass or fail")
    return matrix_id, convention, finite, white_point, white_balance, neutral_check, color_check


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P045-03 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
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
