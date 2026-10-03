"""TC-P021-06 draft control recreation.

Interface recreation may restore an unapplied or invalid control draft.
Committed effective state stays applied. The draft stays labeled as a draft.
An invalid partial numeric entry that reaches the camera is rejected.

Baseline focus inventory stays in preservedResults. This host module does not
touch a device.
"""

from __future__ import annotations

CASE_ID = "TC-P021-06"
INTERVENTION = "Recreate the interface while a user has an unapplied or invalid control draft."
EXPECTED = (
    "Preserve committed effective state and clearly separate any restored draft "
    "from applied sensor control."
)
NEGATIVE = "An invalid partial numeric entry reaching the camera must fail."
REPEATS = (
    "rotation",
    "process_recreation",
    "manual_mode_transition",
    "cancelled_edits",
)
FOCUS_INVENTORY = (
    "physical.namespace:physical.lens",
    "physical.unit:metres",
    "physical.subject:nearby_foreground",
    "physical.distance:unknown",
    "virtual.namespace:virtual.development",
    "virtual.unit:relative_depth",
    "virtual.subject:face",
    "virtual.relativeDepth:0.62",
)
_PAYLOAD_KEYS = {
    "event",
    "committedSubject",
    "committedDistance",
    "draft",
    "draftValid",
    "reachesCamera",
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
    """Keep committed sensor control. Do not apply an invalid draft."""
    event, subject, distance, draft, valid, reaches = _payload(payload)
    preserved = list(FOCUS_INVENTORY)
    preserved.append("applied.subject:" + subject)
    preserved.append("applied.distance:" + distance)
    reasons = [EXPECTED, "repeat event " + event]
    rejected: list[str] = []

    if reaches:
        decision = "rejected"
        if not valid:
            rejected.append("invalid-draft-reached-camera")
            reasons.append(NEGATIVE)
        else:
            rejected.append("unapplied-draft-reached-camera")
            reasons.append("unapplied draft must not reach the camera during recreation")
        reasons.append("committed effective state preserved")
    else:
        decision = "draft_separated"
        preserved.append("draft.unapplied:" + draft)
        reasons.append("restored draft is separate from applied sensor control")
        if event == "cancelled_edits":
            reasons.append("cancelled edit remains a draft and is not applied")

    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P021-06 must not decide qualified or allowed")
    if "applied.distance:" + distance not in preserved:
        raise ValueError("committed distance must be preserved")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != _PAYLOAD_KEYS:
        raise ValueError("invalid payload keys")
    event = payload["event"]
    if event not in REPEATS:
        raise ValueError("event is not a TC-P021-06 repeat")
    draft = _text(payload["draft"], "draft")
    distance = _text(payload["committedDistance"], "committedDistance")
    return (
        event,
        _text(payload["committedSubject"], "committedSubject"),
        distance,
        draft,
        _bool(payload["draftValid"], "draftValid"),
        _bool(payload["reachesCamera"], "reachesCamera"),
    )


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(name + " must be a non-empty string")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(name + " must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("decision must not be qualified or allowed")
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
