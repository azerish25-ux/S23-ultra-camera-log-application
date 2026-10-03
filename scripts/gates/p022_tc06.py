"""TC-P022-06 draft control recreation.

Recreate the interface while a user has an unapplied or invalid control draft.
Preserve committed effective state and clearly separate any restored draft
from applied sensor control. An invalid partial numeric entry reaching the
camera must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P022-06"
INTERVENTION = "Recreate the interface while a user has an unapplied or invalid control draft."
EXPECTED = (
    "Preserve committed effective state and clearly separate any restored draft "
    "from applied sensor control."
)
NEGATIVE = "An invalid partial numeric entry reaching the camera must fail."
EVENTS = ("rotation", "process_recreation", "manual_mode_transition", "cancelled_edit")
_PAYLOAD_KEYS = (
    "event",
    "committedControl",
    "committedValue",
    "draftValue",
    "draftValid",
    "appliedToSensor",
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
    """Keep the committed control. Do not apply an invalid or cancelled draft."""
    data = _payload(payload)
    committed = f"{data['committedControl']}={data['committedValue']}"
    reasons = [f"event {data['event']}", f"committed {committed}"]
    rejected: list[str] = []
    draft = data["draftValue"]
    partial = draft is not None and _partial_numeric(draft)
    invalid = partial or not data["draftValid"]
    if data["appliedToSensor"] and invalid:
        decision = "rejected"
        rejected.append("invalid-draft-reached-camera")
        reasons.append("an invalid partial numeric entry must not reach the camera")
    elif data["appliedToSensor"] and draft != data["committedValue"]:
        decision = "rejected"
        rejected.append("draft-replaced-committed-control")
        reasons.append("an unapplied draft must not replace committed sensor control")
    elif data["event"] == "cancelled_edit" and data["appliedToSensor"]:
        decision = "rejected"
        rejected.append("cancelled-draft-applied")
        reasons.append("a cancelled edit must not reach the camera")
    else:
        decision = "separated"
        reasons.append("committed effective state preserved")
        if data["event"] == "cancelled_edit":
            reasons.append("cancelled draft was discarded")
        elif draft is not None and draft != data["committedValue"]:
            reasons.append("restored draft is not applied sensor control")
    preserved = [committed]
    if (
        decision == "separated"
        and data["event"] != "cancelled_edit"
        and draft is not None
        and draft != data["committedValue"]
    ):
        preserved.append("draft-unapplied:" + draft)
    preserved.append(data["cleanMasterHash"])
    return _result(decision, reasons, rejected, preserved, [])


def _partial_numeric(value: str) -> bool:
    return value[-1] in ".+-"


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    event = payload["event"]
    if event not in EVENTS:
        raise ValueError("event is not a declared repeat")
    draft = payload["draftValue"]
    if draft is not None:
        draft = _token(draft, "draftValue")
    draft_valid = _bool(payload["draftValid"], "draftValid")
    applied = _bool(payload["appliedToSensor"], "appliedToSensor")
    if draft is None and (not draft_valid or applied):
        raise ValueError("an empty draft cannot be invalid or applied")
    if draft is not None and _partial_numeric(draft) and draft_valid:
        draft_valid = False
    return {
        "event": event,
        "committedControl": _token(payload["committedControl"], "committedControl"),
        "committedValue": _token(payload["committedValue"], "committedValue"),
        "draftValue": draft,
        "draftValid": draft_valid,
        "appliedToSensor": applied,
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
        raise ValueError("TC-P022-06 must not yield qualified or allowed")
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
