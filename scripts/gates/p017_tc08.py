"""TC-P017-08 double stop and repeated cleanup.

Redundant stop, close, cancellation, and detach events are idempotent.
One terminal take identity is preserved. Double release, duplicate publication,
or a second take created by cleanup is rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P017-08"
INTERVENTION = "Send redundant stop, close, cancellation, and detach events in different orders."
EXPECTED = "Make cleanup idempotent and preserve a single coherent terminal take identity."
NEGATIVE = "Double release, duplicate publication, or a second take created by cleanup must fail."
SCENARIOS = (
    "empty_startup",
    "active_video",
    "active_audiovisual",
    "recovery_reopening",
)
EVENT_NAMES = ("stop", "close", "cancel", "detach")
_PAYLOAD_KEYS = (
    "scenario",
    "events",
    "takeId",
    "doubleRelease",
    "duplicatePublication",
    "secondTakeFromCleanup",
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
    """Collapse repeated cleanup to one take. Negative controls are rejected."""
    data = _payload(payload)
    reasons = [
        f"scenario {data['scenario']}",
        "events " + ">".join(data["events"]),
        INTERVENTION,
        EXPECTED,
        "single terminal take " + data["takeId"],
    ]
    rejected: list[str] = []
    if data["doubleRelease"]:
        rejected.append("double-release")
    if data["duplicatePublication"]:
        rejected.append("duplicate-publication")
    if data["secondTakeFromCleanup"]:
        rejected.append("second-take")
    if rejected:
        reasons.append(NEGATIVE)
        decision = "rejected"
    else:
        decision = "idempotent"
        reasons.append("cleanup is idempotent")
    preserved = [data["takeId"]]
    if preserved.count(data["takeId"]) != 1:
        raise ValueError("cleanup must preserve a single terminal take")
    if len(preserved) != 1:
        raise ValueError("cleanup must not create a second take")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    scenario = payload["scenario"]
    if scenario not in SCENARIOS:
        raise ValueError("scenario is not a TC-P017-08 repeat")
    events = payload["events"]
    if not isinstance(events, list) or not events:
        raise ValueError("events must be a non-empty list")
    for item in events:
        if item not in EVENT_NAMES:
            raise ValueError("events must be stop, close, cancel, or detach")
    take = payload["takeId"]
    if not isinstance(take, str) or not take or take != take.strip():
        raise ValueError("takeId must be a non-empty string")
    return {
        "scenario": scenario,
        "events": list(events),
        "takeId": take,
        "doubleRelease": _bool(payload["doubleRelease"], "doubleRelease"),
        "duplicatePublication": _bool(payload["duplicatePublication"], "duplicatePublication"),
        "secondTakeFromCleanup": _bool(payload["secondTakeFromCleanup"], "secondTakeFromCleanup"),
    }


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P017-08 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": open_questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
