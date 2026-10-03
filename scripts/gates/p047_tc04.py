"""TC-P047-04 ill-conditioned calibration.

Intervention: Supply a nearly singular matrix or a chart fit lacking adequate
color diversity.
Expected: Reject unstable inversion or report the fit's limited domain with
its uncertainty.
Negative: Returning an identity transform as an invisible fallback must fail.
"""

from __future__ import annotations

from decimal import Decimal

CASE_ID = "TC-P047-04"
INTERVENTION = (
    "Supply a nearly singular matrix or a chart fit lacking adequate color diversity."
)
EXPECTED = (
    "Reject unstable inversion or report the fit\u2019s limited domain with its uncertainty."
)
NEGATIVE = "Returning an identity transform as an invisible fallback must fail."

_DIVERSITY = ("adequate", "inadequate")
_ENDPOINTS = ("present", "invalid", "missing")
_TOKEN = "abcdefghijklmnopqrstuvwxyz0123456789-:+."
_PAYLOAD_KEYS = (
    "fitId",
    "conditionNumber",
    "colorDiversity",
    "illuminantEndpoints",
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
_DECISIONS = ("rejected", "limited_domain", "conditioned")
_FORBIDDEN = {"qualified", "allowed"}
_UNSTABLE = Decimal("100")
_NEAR = Decimal("50")


def evaluate(payload: dict) -> dict:
    """Reject unstable fits and identity fallbacks. Near-threshold stays limited."""
    fit_id, condition, diversity, endpoints, identity = _payload(payload)
    preserved = [
        "fit:" + fit_id,
        "condition:" + condition,
        "diversity:" + diversity,
        "endpoints:" + endpoints,
        "identityFallback:" + str(identity).lower(),
    ]
    number = Decimal(condition)
    rejected: list[str] = []
    limited = False
    if identity:
        rejected.append("identity-fallback")
    if endpoints != "present":
        rejected.append("illuminant-endpoints:" + endpoints)
    if diversity == "inadequate":
        rejected.append("inadequate-color-diversity")
    if number >= _UNSTABLE:
        rejected.append("unstable-inversion")
    elif number >= _NEAR and not rejected:
        limited = True
    if rejected:
        reasons = [EXPECTED, "unstable or unsupported calibration rejected"]
        if identity:
            reasons.append(NEGATIVE)
            reasons.append("identity transform was not substituted for the reported condition")
        if endpoints != "present":
            reasons.append("illuminant endpoints are " + endpoints)
        if diversity == "inadequate":
            reasons.append("color diversity is inadequate")
        if number >= _UNSTABLE:
            reasons.append("condition number is unstable")
        return _result(
            "rejected",
            reasons,
            rejected,
            preserved,
            ["identity fallback is not a measured transform"],
        )
    if limited:
        return _result(
            "limited_domain",
            [
                EXPECTED,
                "fit limited domain reported with uncertainty",
                "condition " + condition + " is near the conditioning threshold",
            ],
            [],
            preserved,
            ["uncertainty:condition:" + condition],
        )
    return _result(
        "conditioned",
        [
            EXPECTED,
            "condition number stayed below the near-threshold band",
            "conditioned is not an invisible identity fallback",
        ],
        [],
        preserved,
        ["host condition number is not a measured camera matrix"],
    )


def _payload(payload: object) -> tuple[str, str, str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    diversity = payload["colorDiversity"]
    if diversity not in _DIVERSITY:
        raise ValueError("colorDiversity is unsupported")
    endpoints = payload["illuminantEndpoints"]
    if endpoints not in _ENDPOINTS:
        raise ValueError("illuminantEndpoints is unsupported")
    identity = payload["identityFallback"]
    if type(identity) is not bool:
        raise ValueError("identityFallback must be a bool")
    fit_id = payload["fitId"]
    if not isinstance(fit_id, str) or not fit_id or any(char not in _TOKEN for char in fit_id):
        raise ValueError("fitId must be a canonical token")
    condition = _decimal(payload["conditionNumber"])
    if Decimal(condition) <= 0:
        raise ValueError("conditionNumber must be positive")
    return fit_id, condition, diversity, endpoints, identity


def _decimal(value: object) -> str:
    if not isinstance(value, str) or not value or value[0] == "-":
        raise ValueError("conditionNumber must be a canonical decimal string")
    if "." in value:
        whole, frac = value.split(".", 1)
        if (
            not frac
            or frac[-1] == "0"
            or not _digits(whole)
            or not _digits(frac)
            or (len(whole) > 1 and whole[0] == "0")
        ):
            raise ValueError("conditionNumber must be a canonical decimal string")
        return value
    if not _digits(value) or (len(value) > 1 and value[0] == "0"):
        raise ValueError("conditionNumber must be a canonical decimal string")
    return value


def _digits(value: str) -> bool:
    return bool(value) and all("0" <= char <= "9" for char in value)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("conditioning decision cannot be qualified or allowed")
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
