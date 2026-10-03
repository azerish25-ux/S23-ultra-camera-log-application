"""TC-P017-06 draft control recreation.

Interface recreation keeps the committed effective control. An unapplied or
invalid draft stays separate from applied sensor control. An invalid partial
numeric entry that reaches the camera is rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P017-06"
INTERVENTION = "Recreate the interface while a user has an unapplied or invalid control draft."
EXPECTED = (
    "Preserve committed effective state and clearly separate any restored draft "
    "from applied sensor control."
)
NEGATIVE = "An invalid partial numeric entry reaching the camera must fail."
RECREATIONS = (
    "rotation",
    "process_recreation",
    "manual_mode_transition",
    "cancelled_edits",
)
_PAYLOAD_KEYS = (
    "recreation",
    "committedEffective",
    "draft",
    "draftInvalid",
    "reachesCamera",
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
    """Keep committed state. Invalid drafts that reach the camera are rejected."""
    data = _payload(payload)
    reasons = [
        f"recreation {data['recreation']}",
        INTERVENTION,
        EXPECTED,
        "committed effective state preserved",
    ]
    rejected: list[str] = []
    open_questions: list[str] = []
    if data["draftInvalid"] and data["reachesCamera"]:
        rejected.append("invalid-partial-entry")
        reasons.append(NEGATIVE)
        decision = "rejected"
    else:
        decision = "separated"
        reasons.append("restored draft is separate from applied sensor control")
        if data["recreation"] == "cancelled_edits":
            reasons.append("cancelled draft is not applied")
        if data["draft"] and data["draft"] != data["committedEffective"]:
            reasons.append("draft not applied: " + data["draft"])
            open_questions.append("draft-not-applied")
    preserved = [data["committedEffective"]]
    if preserved != [data["committedEffective"]]:
        raise ValueError("committed effective state was replaced")
    if data["draftInvalid"] and data["draft"] in preserved:
        raise ValueError("invalid draft must not be preserved as applied control")
    return _result(decision, reasons, rejected, preserved, open_questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    recreation = payload["recreation"]
    if recreation not in RECREATIONS:
        raise ValueError("recreation is not a TC-P017-06 repeat")
    committed = _text(payload["committedEffective"], "committedEffective")
    draft = payload["draft"]
    if not isinstance(draft, str) or draft != draft.strip():
        raise ValueError("draft must be a string without surrounding whitespace")
    invalid = _bool(payload["draftInvalid"], "draftInvalid")
    reaches = _bool(payload["reachesCamera"], "reachesCamera")
    if invalid and draft == committed:
        raise ValueError("invalid draft must differ from committed effective state")
    return {
        "recreation": recreation,
        "committedEffective": committed,
        "draft": draft,
        "draftInvalid": invalid,
        "reachesCamera": reaches,
    }


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


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
        raise ValueError("TC-P017-06 must not yield qualified or allowed")
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
