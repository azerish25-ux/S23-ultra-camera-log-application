"""TC-P042-03 matrix convention mismatch.

A transposed, reversed, or otherwise mis-aimed transform fails the neutral
and color-vector checks with a named convention error. A finite determinant
by itself is not a certificate.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P042-03"
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
    "authored",
    "transposed",
    "reversed",
    "wrong_white_point",
    "duplicated_white_balance",
    "swapped_direction",
    "determinant_only",
)
_CHECKS = ("pass", "fail", "unrun")
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_DET = re.compile(r"0|-?[1-9][0-9]*(?:\.[0-9]*[1-9])?|-?0\.[0-9]*[1-9]")
_PAYLOAD_KEYS = (
    "matrixId",
    "convention",
    "determinant",
    "neutralCheck",
    "colorCheck",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "withheld")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Name the convention error. Do not treat a finite determinant as proof."""
    matrix_id, convention, determinant, neutral, color = _payload(payload)
    preserved = [f"matrix:{matrix_id}", f"determinant:{determinant}", f"convention:{convention}"]
    if convention == "determinant_only":
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "a finite determinant did not certify the transform"],
            ["finite-determinant"],
            preserved,
            ["neutral and color-vector checks were not implied by the determinant"],
        )
    if convention != "authored":
        return _result(
            "rejected",
            [
                EXPECTED,
                INTERVENTION,
                f"convention error {convention}",
                "independent neutral and color-vector checks failed",
            ],
            [f"convention:{convention}", "neutral-check", "color-vector-check"],
            preserved,
            ["plausible finite numbers did not repair the convention"],
        )
    if neutral == "pass" and color == "pass":
        return _result(
            "withheld",
            [
                "authored convention recorded",
                "host checks are not a color-transform certificate",
            ],
            [],
            preserved,
            ["physical color calibration remains unverified"],
        )
    failed = []
    if neutral != "pass":
        failed.append("neutral-check")
    if color != "pass":
        failed.append("color-vector-check")
    return _result(
        "rejected",
        [EXPECTED, "authored matrix failed an independent check"],
        failed,
        preserved,
        ["a failed check was not replaced by the determinant"],
    )


def _payload(payload: object) -> tuple[str, str, str, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    matrix_id = _token(payload["matrixId"], "matrixId")
    convention = _choice(payload["convention"], _CONVENTIONS, "convention")
    determinant = payload["determinant"]
    if not isinstance(determinant, str) or _DET.fullmatch(determinant) is None:
        raise ValueError("determinant must be a finite canonical number")
    neutral = _choice(payload["neutralCheck"], _CHECKS, "neutralCheck")
    color = _choice(payload["colorCheck"], _CHECKS, "colorCheck")
    return matrix_id, convention, determinant, neutral, color


def _choice(value: object, allowed: tuple[str, ...], label: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{label} is not an allowed value")
    return value


def _token(value: object, label: str) -> str:
    if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
        raise ValueError(f"{label} must be a token")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P042-03 must not yield qualified or allowed")
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
