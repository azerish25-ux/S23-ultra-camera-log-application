"""TC-P022-08 double stop and repeated cleanup.

Send redundant stop, close, cancellation, and detach events in different
orders. Make cleanup idempotent and preserve a single coherent terminal take
identity. Double release, duplicate publication, or a second take created by
cleanup must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P022-08"
INTERVENTION = "Send redundant stop, close, cancellation, and detach events in different orders."
EXPECTED = "Make cleanup idempotent and preserve a single coherent terminal take identity."
NEGATIVE = "Double release, duplicate publication, or a second take created by cleanup must fail."
CONTEXTS = ("empty_startup", "active_video", "active_audiovisual", "recovery_reopening")
EVENTS = ("stop", "close", "cancel", "detach")
_PAYLOAD_KEYS = (
    "context",
    "events",
    "takeId",
    "doubleRelease",
    "duplicatePublication",
    "secondTakeCreated",
    "cleanMasterHash",
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
    """Apply cleanup once. Keep a single terminal take identity."""
    data = _payload(payload)
    order = ",".join(data["events"])
    reasons = [f"context {data['context']}", f"events {order}"]
    rejected: list[str] = []
    if data["doubleRelease"]:
        rejected.append("double-release")
        reasons.append("double release must fail")
    if data["duplicatePublication"]:
        rejected.append("duplicate-publication")
        reasons.append("duplicate publication must fail")
    if data["secondTakeCreated"]:
        rejected.append("second-take-from-cleanup")
        reasons.append("cleanup must not create a second take")
    if rejected:
        decision = "rejected"
    else:
        decision = "idempotent"
        reasons.append("cleanup is idempotent")
        reasons.append("single terminal take " + data["takeId"])
    preserved = [data["takeId"], data["cleanMasterHash"]]
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    context = payload["context"]
    if context not in CONTEXTS:
        raise ValueError("context is not a declared repeat")
    events = payload["events"]
    if not isinstance(events, list) or not events:
        raise ValueError("events must be a non-empty list")
    parsed = []
    for item in events:
        if item not in EVENTS:
            raise ValueError("event must be stop, close, cancel, or detach")
        parsed.append(item)
    return {
        "context": context,
        "events": parsed,
        "takeId": _token(payload["takeId"], "takeId"),
        "doubleRelease": _bool(payload["doubleRelease"], "doubleRelease"),
        "duplicatePublication": _bool(payload["duplicatePublication"], "duplicatePublication"),
        "secondTakeCreated": _bool(payload["secondTakeCreated"], "secondTakeCreated"),
        "cleanMasterHash": _token(payload["cleanMasterHash"], "cleanMasterHash"),
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
        raise ValueError("TC-P022-08 must not yield qualified or allowed")
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
