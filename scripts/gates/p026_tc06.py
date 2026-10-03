"""TC-P026-06 publication destination failure.

Destination space can run out, or a publication grant can be revoked, after
private staging has succeeded. Keep the private source and return a retryable
outcome. Deleting staging before publication, or writing an empty success
entry, must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P026-06"
INTERVENTION = "Exhaust destination space or revoke a publication grant after private staging succeeds."
EXPECTED = "Retain the private source and provide a retryable recovery outcome without empty success entries."
NEGATIVE = "Deleting staging before successful publication must fail."
STAGES = (
    "copy",
    "commit",
    "report_export",
    "redundant_staging_cleanup",
)
_PAYLOAD_KEYS = (
    "stage",
    "destinationExhausted",
    "grantRevoked",
    "stagingPresent",
    "deletedBeforePublication",
    "privateSourceId",
    "emptySuccess",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Keep the private source. Do not publish an empty success."""
    fields = _payload(payload)
    reasons = [INTERVENTION, f"stage {fields['stage']}"]
    preserved = [fields["privateSourceId"], "stage:" + fields["stage"]]
    rejected: list[str] = []
    if fields["deletedBeforePublication"]:
        rejected.append("staging-deleted-before-publication")
        reasons.append(NEGATIVE)
    if fields["emptySuccess"]:
        rejected.append("empty-success-entry")
        reasons.append("empty success entries are rejected")
    if not fields["stagingPresent"]:
        rejected.append("staging-missing")
        reasons.append("private staging is not present")
    if rejected:
        decision = "rejected"
    elif fields["destinationExhausted"] or fields["grantRevoked"]:
        decision = "retryable"
        reasons.append(EXPECTED)
        if fields["destinationExhausted"]:
            reasons.append("destination space exhausted")
        if fields["grantRevoked"]:
            reasons.append("publication grant revoked")
    else:
        decision = "withheld"
        reasons.append("no publication failure was presented")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    stage = payload["stage"]
    if stage not in STAGES:
        raise ValueError("stage is not a declared repeat")
    return {
        "stage": stage,
        "destinationExhausted": _bool(payload["destinationExhausted"], "destinationExhausted"),
        "grantRevoked": _bool(payload["grantRevoked"], "grantRevoked"),
        "stagingPresent": _bool(payload["stagingPresent"], "stagingPresent"),
        "deletedBeforePublication": _bool(payload["deletedBeforePublication"], "deletedBeforePublication"),
        "privateSourceId": _token(payload["privateSourceId"], "privateSourceId"),
        "emptySuccess": _bool(payload["emptySuccess"], "emptySuccess"),
    }


def _token(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P026-06 must not yield qualified or allowed")
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
