"""TC-P041-04 ill-conditioned calibration.

A nearly singular matrix or a chart without color diversity is not inverted
invisibly. An identity fallback fails. Limited domains keep their uncertainty.
"""

from __future__ import annotations

import re
from decimal import Decimal

CASE_ID = "TC-P041-04"
INTERVENTION = "Supply a nearly singular matrix or a chart fit lacking adequate color diversity."
EXPECTED = "Reject unstable inversion or report the fit\u2019s limited domain with its uncertainty."
NEGATIVE = "Returning an identity transform as an invisible fallback must fail."

_THRESHOLD = Decimal("10000")
_DIVERSITY = ("adequate", "narrow")
_ENDPOINTS = ("present", "missing", "invalid")
_FINITE = re.compile(r"^(?:0|0\.[0-9]*[1-9]|[1-9][0-9]*(?:\.[0-9]*[1-9])?)$")
_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9-]{0,63}$")
_PAYLOAD_KEYS = (
    "conditionNumber",
    "colorDiversity",
    "illuminantEndpoints",
    "identityFallback",
    "uncertainty",
    "domain",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "limited_domain", "inversion_stable"}
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Reject an identity fallback or an unstable inversion without a stated domain."""
    fields = _payload(payload)
    preserved = [
        f"condition:{fields['conditionNumber']}",
        f"diversity:{fields['colorDiversity']}",
        f"endpoints:{fields['illuminantEndpoints']}",
        f"domain:{fields['domain']}",
        f"uncertainty:{fields['uncertainty']}",
    ]
    claims: list[str] = []
    reasons = [EXPECTED]
    if fields["identityFallback"]:
        claims.append("identity-fallback")
        reasons.append(NEGATIVE)
    if fields["illuminantEndpoints"] != "present":
        claims.append("illuminant-endpoints-" + fields["illuminantEndpoints"])
        reasons.append("illuminant endpoints are " + fields["illuminantEndpoints"])
    unstable = Decimal(fields["conditionNumber"]) > _THRESHOLD
    narrow = fields["colorDiversity"] == "narrow"
    if unstable:
        claims.append("unstable-inversion")
    if narrow:
        claims.append("narrow-diversity")
    if fields["identityFallback"] or fields["illuminantEndpoints"] != "present":
        reasons.append("no identity matrix was substituted")
        return _result("rejected", reasons, claims, preserved, ["inversion was not silently replaced"])
    if unstable or narrow:
        if fields["uncertainty"] == "unreported":
            reasons.append("unstable inversion rejected because uncertainty was unreported")
            return _result(
                "rejected",
                reasons,
                claims,
                preserved,
                ["limited domain was not invented"],
            )
        reasons.append(
            f"limited domain {fields['domain']} uncertainty {fields['uncertainty']}"
        )
        return _result(
            "limited_domain",
            reasons,
            claims,
            preserved,
            [f"domain:{fields['domain']}", f"uncertainty:{fields['uncertainty']}"],
        )
    return _result(
        "inversion_stable",
        reasons + ["condition is at or below the threshold and diversity is adequate"],
        [],
        preserved,
        ["stable inversion is not a certified profile"],
    )


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    condition = payload["conditionNumber"]
    if not isinstance(condition, str) or _FINITE.fullmatch(condition) is None:
        raise ValueError("conditionNumber must be a non-negative canonical decimal")
    diversity = payload["colorDiversity"]
    if diversity not in _DIVERSITY:
        raise ValueError("colorDiversity must be adequate or narrow")
    endpoints = payload["illuminantEndpoints"]
    if endpoints not in _ENDPOINTS:
        raise ValueError("illuminantEndpoints must be present, missing, or invalid")
    fallback = payload["identityFallback"]
    if type(fallback) is not bool:
        raise ValueError("identityFallback must be a bool")
    uncertainty = payload["uncertainty"]
    if uncertainty != "unreported" and (
        not isinstance(uncertainty, str) or _FINITE.fullmatch(uncertainty) is None
    ):
        raise ValueError("uncertainty must be unreported or a non-negative canonical decimal")
    domain = payload["domain"]
    if not isinstance(domain, str) or _TOKEN.fullmatch(domain) is None:
        raise ValueError("domain must be a token")
    return {
        "conditionNumber": condition,
        "colorDiversity": diversity,
        "illuminantEndpoints": endpoints,
        "identityFallback": fallback,
        "uncertainty": uncertainty,
        "domain": domain,
    }


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P041-04 must not yield qualified or allowed")
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
