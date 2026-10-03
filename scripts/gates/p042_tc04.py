"""TC-P042-04 ill-conditioned calibration.

A nearly singular matrix or a chart without color diversity is an unstable
inversion. Near a conditioning threshold, or with a bad illuminant endpoint,
the fit stays inside its reported domain. An identity fallback is rejected.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P042-04"
INTERVENTION = "Supply a nearly singular matrix or a chart fit lacking adequate color diversity."
EXPECTED = "Reject unstable inversion or report the fit’s limited domain with its uncertainty."
NEGATIVE = "Returning an identity transform as an invisible fallback must fail."

_CONDITIONS = (
    "nearly_singular",
    "low_diversity",
    "near_threshold",
    "missing_illuminant",
    "invalid_illuminant",
    "identity_fallback",
)
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_NUMBER = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?")
_POSITIVE = re.compile(r"(?:[1-9][0-9]*)(?:\.[0-9]*[1-9])?|0\.[0-9]*[1-9]")
_PAYLOAD_KEYS = (
    "matrixId",
    "condition",
    "conditionNumber",
    "diversity",
    "uncertainty",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "limited_domain")
_FORBIDDEN = {"qualified", "allowed"}
_UNSTABLE = {"nearly_singular", "low_diversity"}
_LIMITED = {"near_threshold", "missing_illuminant", "invalid_illuminant"}


def evaluate(payload: dict) -> dict:
    """Reject an identity fallback and any unstable inversion."""
    matrix_id, condition, number, diversity, uncertainty = _payload(payload)
    preserved = [
        f"matrix:{matrix_id}",
        f"condition:{number}",
        f"diversity:{diversity}",
        f"uncertainty:{uncertainty}",
        f"fit:{condition}",
    ]
    if condition == "identity_fallback":
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "identity was not substituted for the unstable fit"],
            ["identity-fallback"],
            preserved,
            ["the condition number was not a hidden fallback"],
        )
    if condition in _UNSTABLE:
        return _result(
            "rejected",
            [EXPECTED, INTERVENTION, f"unstable inversion rejected for {condition}"],
            ["unstable-inversion", condition],
            preserved,
            ["no identity matrix was inserted"],
        )
    return _result(
        "limited_domain",
        [
            EXPECTED,
            f"limited domain {condition} uncertainty {uncertainty}",
            "the fit was not replaced by an identity transform",
        ],
        ["limited-domain"],
        preserved,
        ["fit restricted to the reported domain"],
    )


def _payload(payload: object) -> tuple[str, str, str, int, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    matrix_id = _token(payload["matrixId"], "matrixId")
    condition = _choice(payload["condition"], _CONDITIONS, "condition")
    number = payload["conditionNumber"]
    if not isinstance(number, str) or _POSITIVE.fullmatch(number) is None:
        raise ValueError("conditionNumber must be a canonical positive decimal")
    diversity = payload["diversity"]
    if type(diversity) is not int or diversity < 0 or diversity > 64:
        raise ValueError("diversity must be an int from 0 to 64")
    uncertainty = payload["uncertainty"]
    if not isinstance(uncertainty, str) or _NUMBER.fullmatch(uncertainty) is None:
        raise ValueError("uncertainty must be a canonical non-negative decimal")
    if condition not in _UNSTABLE and condition != "identity_fallback" and condition not in _LIMITED:
        raise ValueError("condition is not handled")
    return matrix_id, condition, number, diversity, uncertainty


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
        raise ValueError("TC-P042-04 must not yield qualified or allowed")
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
