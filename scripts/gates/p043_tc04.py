"""TC-P043-04 ill-conditioned calibration.

Intervention: Supply a nearly singular matrix or a chart fit lacking adequate
color diversity.
Expected: Reject unstable inversion or report the fit's limited domain with
its uncertainty.
Negative: Returning an identity transform as an invisible fallback must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal

CASE_ID = "TC-P043-04"
INTERVENTION = "Supply a nearly singular matrix or a chart fit lacking adequate color diversity."
EXPECTED = "Reject unstable inversion or report the fit\u2019s limited domain with its uncertainty."
NEGATIVE = "Returning an identity transform as an invisible fallback must fail."

_CONDITIONS = ("stable", "near-threshold", "nearly-singular", "low-diversity")
_ENDPOINTS = ("present", "invalid", "missing")
_PAYLOAD_KEYS = (
    "fitId",
    "condition",
    "conditionNumber",
    "colorCount",
    "illuminantEndpoints",
    "uncertainty",
    "identityFallback",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "limited_domain", "fit_recorded")
_FORBIDDEN = {"qualified", "allowed"}
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
_NEAR = Decimal("100")
_SINGULAR = Decimal("1000")


def evaluate(payload: dict) -> dict:
    """Refuse an identity fallback. Report limited domains with uncertainty."""
    fit, condition, number, colors, endpoints, uncertainty, fallback = _payload(payload)
    preserved = [
        f"fit:{fit}",
        f"condition:{condition}",
        f"conditionNumber:{number}",
        f"colors:{colors}",
        f"uncertainty:{uncertainty}",
        "fallback:refused" if fallback else "fallback:absent",
    ]
    rejected: list[str] = []
    questions = [f"uncertainty {uncertainty} stays attached to {fit}"]
    if fallback:
        decision = "rejected"
        rejected.append("identity-fallback")
        reasons = [NEGATIVE, EXPECTED, "identity transform was not substituted"]
        if condition == "nearly-singular":
            rejected.append("unstable-inversion")
        return _result(decision, reasons, rejected, preserved, questions)
    if endpoints != "present":
        rejected.append(f"illuminant-endpoints:{endpoints}")
    if condition == "nearly-singular":
        rejected.append("unstable-inversion")
    if condition == "low-diversity":
        questions.append("limited color diversity")
    if condition == "near-threshold":
        questions.append("near conditioning threshold")
    if rejected:
        decision = "rejected"
        reasons = [EXPECTED, f"uncertainty {uncertainty}", "unstable fit was not inverted"]
    elif condition in {"near-threshold", "low-diversity"}:
        decision = "limited_domain"
        reasons = [EXPECTED, f"limited domain uncertainty {uncertainty}", f"condition {condition}"]
    else:
        decision = "fit_recorded"
        reasons = [
            f"stable fit recorded with uncertainty {uncertainty}",
            "this record is not a physical calibration",
        ]
        questions.append("host fit is not a measured profile")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, int, str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    fit = payload["fitId"]
    if not isinstance(fit, str) or not fit or fit != fit.strip():
        raise ValueError("fitId must be a non-empty string")
    condition = payload["condition"]
    if condition not in _CONDITIONS:
        raise ValueError("condition is not a known conditioning label")
    number_text = payload["conditionNumber"]
    if not isinstance(number_text, str) or _DECIMAL.fullmatch(number_text) is None:
        raise ValueError("conditionNumber must be a canonical decimal string")
    number = Decimal(number_text)
    colors = payload["colorCount"]
    if type(colors) is not int or colors < 0:
        raise ValueError("colorCount must be a non-negative int")
    endpoints = payload["illuminantEndpoints"]
    if endpoints not in _ENDPOINTS:
        raise ValueError("illuminantEndpoints must be present, invalid, or missing")
    uncertainty = payload["uncertainty"]
    if not isinstance(uncertainty, str) or _DECIMAL.fullmatch(uncertainty) is None:
        raise ValueError("uncertainty must be a canonical decimal string")
    fallback = payload["identityFallback"]
    if type(fallback) is not bool:
        raise ValueError("identityFallback must be a bool")
    if condition == "nearly-singular" and number < _SINGULAR:
        raise ValueError("nearly-singular requires conditionNumber >= 1000")
    if condition == "near-threshold" and not (_NEAR <= number < _SINGULAR):
        raise ValueError("near-threshold requires 100 <= conditionNumber < 1000")
    if condition == "stable" and number >= _NEAR:
        raise ValueError("stable requires conditionNumber < 100")
    if condition == "low-diversity" and colors >= 4:
        raise ValueError("low-diversity requires colorCount < 4")
    if condition != "low-diversity" and colors < 4:
        raise ValueError("colorCount below 4 must be labeled low-diversity")
    return fit, condition, number_text, colors, endpoints, uncertainty, fallback


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("fit decision cannot be qualified or allowed")
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
