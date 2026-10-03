"""TC-P045-04 ill-conditioned calibration.

Intervention: Supply a nearly singular matrix or a chart fit lacking adequate
color diversity.
Expected: Reject unstable inversion or report the fit's limited domain with
its uncertainty.
Negative: Returning an identity transform as an invisible fallback must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal

CASE_ID = "TC-P045-04"
INTERVENTION = (
    "Supply a nearly singular matrix or a chart fit lacking adequate color diversity."
)
EXPECTED = (
    "Reject unstable inversion or report the fit's limited domain with its uncertainty."
)
NEGATIVE = "Returning an identity transform as an invisible fallback must fail."

_DIVERSITY = ("adequate", "inadequate")
_ENDPOINTS = ("present", "missing", "invalid")
_PAYLOAD_KEYS = (
    "fitId",
    "conditionNumber",
    "colorDiversity",
    "identityFallback",
    "illuminantEndpoints",
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
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
_NEAR = Decimal("100")
_UNSTABLE = Decimal("1000")


def evaluate(payload: dict) -> dict:
    """Reject an identity fallback and an unstable inversion."""
    fit_id, condition, diversity, fallback, endpoints, uncertainty = _payload(payload)
    preserved = [
        f"fit:{fit_id}",
        f"condition:{condition}",
        f"diversity:{diversity}",
        f"endpoints:{endpoints}",
        f"uncertainty:{uncertainty}",
    ]
    number = Decimal(condition)
    rejected: list[str] = []
    questions: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"uncertainty {uncertainty} stays with fit {fit_id}"]
    near = _NEAR <= number < _UNSTABLE
    unstable = number >= _UNSTABLE
    if fallback:
        rejected.append("identity-fallback")
        reasons.append(NEGATIVE)
        reasons.append("the reported condition number was not replaced by an identity transform")
    if unstable:
        rejected.append("unstable-inversion")
        reasons.append("condition number is at or above the rejection threshold")
    if diversity == "inadequate":
        rejected.append("inadequate-color-diversity")
        reasons.append("color diversity does not support an unrestricted fit")
    if endpoints != "present":
        rejected.append(f"illuminant-endpoints:{endpoints}")
        reasons.append(f"illuminant endpoints are {endpoints}")
    if near:
        reasons.append("condition number is near the conditioning threshold")
        questions.append("near-condition-threshold")
    if fallback or unstable or endpoints != "present":
        decision = "rejected"
        questions.append("unstable or unscoped calibration was not given an identity fallback")
    elif near or diversity == "inadequate":
        decision = "limited_domain"
        reasons.append("limited domain is reported with its uncertainty")
        if diversity == "inadequate":
            questions.append("limited domain from inadequate color diversity")
    else:
        decision = "conditioned"
        reasons.append("identity fallback was not used")
        questions.append("conditioned fit is not a physical S23 profile")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, bool, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    fit_id = payload["fitId"]
    if not isinstance(fit_id, str) or _TOKEN.fullmatch(fit_id) is None:
        raise ValueError("fitId must be a token")
    condition = payload["conditionNumber"]
    uncertainty = payload["uncertainty"]
    for name, value in (("conditionNumber", condition), ("uncertainty", uncertainty)):
        if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
            raise ValueError(f"{name} must be a canonical decimal string")
    if Decimal(condition) <= 0:
        raise ValueError("conditionNumber must be positive")
    diversity = payload["colorDiversity"]
    if diversity not in _DIVERSITY:
        raise ValueError("colorDiversity must be adequate or inadequate")
    fallback = payload["identityFallback"]
    if type(fallback) is not bool:
        raise ValueError("identityFallback must be a bool")
    endpoints = payload["illuminantEndpoints"]
    if endpoints not in _ENDPOINTS:
        raise ValueError("illuminantEndpoints is unsupported")
    return fit_id, condition, diversity, fallback, endpoints, uncertainty


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P045-04 must not yield qualified or allowed")
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
