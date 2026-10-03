"""TC-P048-04 ill-conditioned calibration.

Intervention: Supply a nearly singular matrix or a chart fit lacking adequate
color diversity.
Expected: Reject unstable inversion or report the fit's limited domain with
its uncertainty.
Negative: Returning an identity transform as an invisible fallback must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P048-04"
INTERVENTION = (
    "Supply a nearly singular matrix or a chart fit lacking adequate color diversity."
)
EXPECTED = "Reject unstable inversion or report the fit\u2019s limited domain with its uncertainty."
NEGATIVE = "Returning an identity transform as an invisible fallback must fail."

_CONDITION_LIMIT = 1000
_ENDPOINTS = ("present", "invalid", "missing", "near_threshold")
_PAYLOAD_KEYS = (
    "conditionNumber",
    "colorCount",
    "identityFallback",
    "illuminantEndpoint",
    "domainNote",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "limited_domain", "withheld")
_FORBIDDEN = {"qualified", "allowed"}
_POS = re.compile(r"[1-9][0-9]*")


def evaluate(payload: dict) -> dict:
    """Reject unstable inversion and an invisible identity fallback."""
    condition, colors, fallback, endpoint, note = _payload(payload)
    preserved = [
        f"condition:{condition}",
        f"colors:{colors}",
        f"endpoint:{endpoint}",
        f"domain:{note}",
    ]
    reasons = [EXPECTED]
    number = int(condition)
    if fallback:
        decision = "rejected"
        rejected = ["identity-fallback"]
        reasons.append(NEGATIVE)
        questions = ["identity fallback did not replace the recorded condition"]
    elif number > _CONDITION_LIMIT:
        decision = "rejected"
        rejected = ["unstable-inversion"]
        reasons.append("unstable inversion rejected")
        questions = [f"condition {condition} exceeds {_CONDITION_LIMIT}"]
    elif colors < 4:
        decision = "limited_domain"
        rejected = ["limited-color-diversity"]
        reasons.append("limited domain reported with uncertainty")
        questions = ["uncertainty recorded for a limited fit domain"]
    elif endpoint == "missing":
        decision = "rejected"
        rejected = ["missing-illuminant-endpoint"]
        reasons.append("missing illuminant endpoint")
        questions = ["illuminant endpoint missing"]
    elif endpoint == "invalid":
        decision = "rejected"
        rejected = ["invalid-illuminant-endpoint"]
        reasons.append("invalid illuminant endpoint")
        questions = ["illuminant endpoint invalid"]
    elif endpoint == "near_threshold" or number == _CONDITION_LIMIT:
        decision = "withheld"
        rejected = []
        reasons.append("near the conditioning threshold; inversion is not certified")
        questions = ["near conditioning threshold; inversion not certified"]
    else:
        decision = "withheld"
        rejected = []
        reasons.append("host fit is not a measured color profile")
        questions = ["host fit is not a measured color profile"]
    if "transform:identity" in preserved:
        raise ValueError("identity must not be written as a successful fallback")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, int, bool, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    condition = payload["conditionNumber"]
    if not isinstance(condition, str) or _POS.fullmatch(condition) is None:
        raise ValueError("conditionNumber must be a canonical positive integer string")
    colors = payload["colorCount"]
    if type(colors) is not int or colors <= 0:
        raise ValueError("colorCount must be a positive int")
    fallback = payload["identityFallback"]
    if type(fallback) is not bool:
        raise ValueError("identityFallback must be a bool")
    endpoint = payload["illuminantEndpoint"]
    if endpoint not in _ENDPOINTS:
        raise ValueError("illuminantEndpoint is unknown")
    note = payload["domainNote"]
    if not isinstance(note, str) or not note or note != note.strip():
        raise ValueError("domainNote must be a non-empty string")
    return condition, colors, fallback, endpoint, note


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
