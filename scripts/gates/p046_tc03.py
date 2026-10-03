"""TC-P046-03 matrix convention mismatch.

Intervention: Transpose or reverse one calibration transform while keeping all
numbers finite and plausible.
Expected: Fail the independent neutral and color-vector checks with a specific
convention error.
Negative: A finite determinant alone must not certify a color transform.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P046-03"
INTERVENTION = (
    "Transpose or reverse one calibration transform while keeping all numbers finite "
    "and plausible."
)
EXPECTED = (
    "Fail the independent neutral and color-vector checks with a specific convention error."
)
NEGATIVE = "A finite determinant alone must not certify a color transform."

_CONVENTIONS = (
    "row-camera-to-xyz",
    "transposed",
    "reversed",
    "wrong-white",
    "duplicated-wb",
    "swapped-direction",
)
_SPECIFIC = {
    "transposed": "convention-error:transposed",
    "reversed": "convention-error:reversed",
    "wrong-white": "convention-error:wrong-white",
    "duplicated-wb": "convention-error:duplicated-white-balance",
    "swapped-direction": "convention-error:swapped-direction",
}
_CHECKS = ("pass", "fail", "skipped")
_PAYLOAD_KEYS = (
    "matrixId",
    "convention",
    "determinant",
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
_DECISIONS = ("rejected", "convention_error", "checks_failed", "checks_observed", "withheld")
_FORBIDDEN = {"qualified", "allowed"}
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")
_INT = re.compile(r"0|-?[1-9][0-9]*")


def evaluate(payload: dict) -> dict:
    """Fail a convention mismatch. A finite determinant is not a certificate."""
    matrix_id, convention, determinant, finite, neutral_check, color_check = _payload(payload)
    preserved = [
        f"matrix:{matrix_id}",
        f"convention:{convention}",
        f"determinant:{determinant}",
        f"determinant-finite:{str(finite).lower()}",
        f"neutral-check:{neutral_check}",
        f"color-vector-check:{color_check}",
    ]
    reasons = [EXPECTED]
    both_pass = neutral_check == "pass" and color_check == "pass"
    if convention != "row-camera-to-xyz":
        decision = "convention_error"
        rejected = [_SPECIFIC[convention], "neutral-check", "color-vector-check"]
        if finite:
            rejected.append("finite-determinant")
        reasons.append(f"convention error {_SPECIFIC[convention]}")
        questions = [_SPECIFIC[convention]]
    elif not both_pass and finite and neutral_check == "skipped" and color_check == "skipped":
        decision = "rejected"
        rejected = ["finite-determinant"]
        reasons.append(NEGATIVE)
        questions = ["finite determinant is not a color-transform certificate"]
    elif not both_pass:
        decision = "checks_failed"
        rejected = []
        if neutral_check != "pass":
            rejected.append("neutral-check")
        if color_check != "pass":
            rejected.append("color-vector-check")
        if finite:
            rejected.append("finite-determinant")
        reasons.append("independent checks failed")
        questions = list(rejected)
    elif not finite:
        decision = "withheld"
        rejected = []
        reasons.append("non-finite determinant withholds the transform")
        questions = ["determinant is not finite"]
    else:
        decision = "checks_observed"
        rejected = []
        reasons.append(
            "neutral and color-vector checks passed; a finite determinant was not the certificate"
        )
        questions = []
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, bool, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    matrix_id = payload["matrixId"]
    if not isinstance(matrix_id, str) or _TOKEN.fullmatch(matrix_id) is None:
        raise ValueError("matrixId must be a token")
    convention = payload["convention"]
    if convention not in _CONVENTIONS:
        raise ValueError("convention is unknown")
    determinant = payload["determinant"]
    if not isinstance(determinant, str) or _INT.fullmatch(determinant) is None:
        raise ValueError("determinant must be a canonical integer string")
    finite = payload["determinantFinite"]
    if type(finite) is not bool:
        raise ValueError("determinantFinite must be a bool")
    neutral_check = payload["neutralCheck"]
    color_check = payload["colorVectorCheck"]
    if neutral_check not in _CHECKS or color_check not in _CHECKS:
        raise ValueError("checks must be pass, fail, or skipped")
    return matrix_id, convention, determinant, finite, neutral_check, color_check


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("convention decision cannot be qualified or allowed")
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
