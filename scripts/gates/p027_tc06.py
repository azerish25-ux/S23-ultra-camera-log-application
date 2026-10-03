"""TC-P027-06 publication destination failure.

Destination space or a publication grant fails after private staging succeeds.
Keep the private source and a retryable outcome. Deleting staging before
publication, or recording an empty success entry, must fail.

Host fixture only. This module does not qualify a physical S23.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P027-06"
INTERVENTION = "Exhaust destination space or revoke a publication grant after private staging succeeds."
EXPECTED = "Retain the private source and provide a retryable recovery outcome without empty success entries."
NEGATIVE = "Deleting staging before successful publication must fail."
STAGES = ("copy", "commit", "report-export", "redundant-staging-cleanup")
_TOKEN = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
_PAYLOAD_KEYS = {
    "stage",
    "stagingDeleted",
    "privateSource",
    "privateSourceRetained",
    "retryable",
    "emptySuccessEntry",
    "publicationSucceeded",
}
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Keep the private source. Do not record an empty success."""
    data = _payload(payload)
    reasons = [f"stage {data['stage']}", INTERVENTION]
    preserved = [data["privateSource"], data["stage"]]
    rejected: list[str] = []
    if data["stagingDeleted"]:
        rejected.append("staging-deleted-before-publication")
        reasons.append(NEGATIVE)
    if not data["privateSourceRetained"]:
        rejected.append("private-source-lost")
        reasons.append("private source was not retained")
    if not data["retryable"]:
        rejected.append("not-retryable")
        reasons.append("recovery outcome was not retryable")
    if data["emptySuccessEntry"]:
        rejected.append("empty-success-entry")
        reasons.append("empty success entry was recorded")
    if data["publicationSucceeded"]:
        rejected.append("false-publication-success")
        reasons.append("publication was marked successful during a destination failure")
    if rejected:
        decision = "rejected"
    else:
        decision = "retryable"
        reasons.append(EXPECTED)
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != _PAYLOAD_KEYS:
        raise ValueError("invalid payload keys")
    stage = payload["stage"]
    if stage not in STAGES:
        raise ValueError("stage is not a declared publication step")
    source = payload["privateSource"]
    if not isinstance(source, str) or _TOKEN.fullmatch(source) is None:
        raise ValueError("privateSource must be a token")
    return {
        "stage": stage,
        "stagingDeleted": _bool(payload["stagingDeleted"], "stagingDeleted"),
        "privateSource": source,
        "privateSourceRetained": _bool(payload["privateSourceRetained"], "privateSourceRetained"),
        "retryable": _bool(payload["retryable"], "retryable"),
        "emptySuccessEntry": _bool(payload["emptySuccessEntry"], "emptySuccessEntry"),
        "publicationSucceeded": _bool(payload["publicationSucceeded"], "publicationSucceeded"),
    }


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P027-06 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
