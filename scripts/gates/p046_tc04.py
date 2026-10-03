"""TC-P046-04 ill-conditioned calibration.

Intervention: Supply a nearly singular matrix or a chart fit lacking adequate
color diversity.
Expected: Reject unstable inversion or report the fit's limited domain with
its uncertainty.
Negative: Returning an identity transform as an invisible fallback must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P046-04"
INTERVENTION = (
    "Supply a nearly singular matrix or a chart fit lacking adequate color diversity."
)
EXPECTED = (
    "Reject unstable inversion or report the fit\u2019s limited domain with its uncertainty."
)
NEGATIVE = "Returning an identity transform as an invisible fallback must fail."

_DIVERSITY = ("adequate", "narrow", "invalid", "missing-endpoints")
_PAYLOAD_KEYS = (
    "fitId",
    "conditionNumerator",
    "conditionDenominator",
    "thresholdNumerator",
    "thresholdDenominator",
    "diversity",
    "identityFallback",
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
_DECISIONS = ("rejected", "limited_domain", "conditioned")
_FORBIDDEN = {"qualified", "allowed"}
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")
_UINT = re.compile(r"0|[1-9][0-9]*")
_POSITIVE = re.compile(r"[1-9][0-9]*")


def evaluate(payload: dict) -> dict:
    """Reject an identity fallback or an unstable fit. Keep the condition number."""
    (
        fit_id,
        cond_n,
        cond_d,
        thresh_n,
        thresh_d,
        diversity,
        identity,
        uncertainty,
    ) = _payload(payload)
    preserved = [
        f"fit:{fit_id}",
        f"condition:{cond_n}/{cond_d}",
        f"threshold:{thresh_n}/{thresh_d}",
        f"diversity:{diversity}",
        f"uncertainty:{uncertainty}",
        f"identity-fallback:{str(identity).lower()}",
    ]
    unstable = cond_n * thresh_d >= thresh_n * cond_d
    near = (not unstable) and (2 * cond_n * thresh_d >= thresh_n * cond_d)
    rejected: list[str] = []
    if identity:
        rejected.append("identity-fallback")
    if diversity == "invalid":
        rejected.append("invalid-illuminant-endpoints")
    elif diversity == "missing-endpoints":
        rejected.append("missing-illuminant-endpoints")
    if unstable:
        rejected.append("unstable-inversion")
    reasons = [EXPECTED]
    if rejected:
        decision = "rejected"
        if identity:
            reasons.append(NEGATIVE)
        if unstable:
            reasons.append(
                f"condition {cond_n}/{cond_d} is not below threshold {thresh_n}/{thresh_d}"
            )
        questions = ["calibration rejected"]
    elif diversity == "narrow" or near:
        decision = "limited_domain"
        reasons.append(f"limited domain uncertainty {uncertainty}")
        questions = [f"uncertainty {uncertainty}"]
        rejected = []
    else:
        decision = "conditioned"
        reasons.append("conditioning is inside the stable region and is not a physical calibration")
        questions = []
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(
    payload: object,
) -> tuple[str, int, int, int, int, str, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    fit_id = payload["fitId"]
    if not isinstance(fit_id, str) or _TOKEN.fullmatch(fit_id) is None:
        raise ValueError("fitId must be a token")
    cond_n = _uint(payload["conditionNumerator"], "conditionNumerator")
    cond_d = _positive(payload["conditionDenominator"], "conditionDenominator")
    thresh_n = _positive(payload["thresholdNumerator"], "thresholdNumerator")
    thresh_d = _positive(payload["thresholdDenominator"], "thresholdDenominator")
    diversity = payload["diversity"]
    if diversity not in _DIVERSITY:
        raise ValueError("diversity is unknown")
    identity = payload["identityFallback"]
    if type(identity) is not bool:
        raise ValueError("identityFallback must be a bool")
    uncertainty = payload["uncertainty"]
    if not isinstance(uncertainty, str) or _UINT.fullmatch(uncertainty) is None:
        raise ValueError("uncertainty must be a canonical non-negative integer string")
    return fit_id, int(cond_n), int(cond_d), int(thresh_n), int(thresh_d), diversity, identity, uncertainty


def _uint(value: object, label: str) -> str:
    if not isinstance(value, str) or _UINT.fullmatch(value) is None:
        raise ValueError(label + " must be a canonical non-negative integer string")
    return value


def _positive(value: object, label: str) -> str:
    if not isinstance(value, str) or _POSITIVE.fullmatch(value) is None:
        raise ValueError(label + " must be a canonical positive integer string")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("conditioning decision cannot be qualified or allowed")
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
