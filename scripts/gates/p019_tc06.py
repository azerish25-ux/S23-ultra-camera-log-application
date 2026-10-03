"""TC-P019-06 draft control recreation.

Rotation, process recreation, a manual-mode transition, or a cancelled edit
keeps the committed effective control. A restored draft stays separate from
applied sensor control. An invalid partial entry that reaches the camera is
rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P019-06"
INTERVENTION = (
    "Recreate the interface while a user has an unapplied or invalid control draft."
)
EXPECTED = (
    "Preserve committed effective state and clearly separate any restored draft "
    "from applied sensor control."
)
NEGATIVE = "An invalid partial numeric entry reaching the camera must fail."
REPEAT = (
    "Repeat with rotation, process recreation, manual-mode transition, and cancelled edits."
)
RECREATIONS = (
    "rotation",
    "process_recreation",
    "manual_mode_transition",
    "cancelled_edits",
)
_PAYLOAD_KEYS = (
    "recreation",
    "committed",
    "draft",
    "draftValid",
    "appliedToCamera",
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
    """Keep committed controls. Do not push an invalid draft to the camera."""
    recreation, committed, draft, draft_valid, applied = _payload(payload)
    preserved = [f"committed:{key}={committed[key]}" for key in sorted(committed)]
    reasons = [f"recreation {recreation}"]
    rejected: list[str] = []
    questions: list[str] = []

    if applied and not draft_valid:
        decision = "rejected"
        rejected.append("invalid-draft-applied")
        reasons.append("invalid partial numeric entry must not reach the camera")
    elif applied and draft_valid:
        decision = "withheld"
        rejected.append("draft-applied-on-recreation")
        reasons.append("recreation must not apply a draft as sensor control")
        questions.append("draft was submitted during recreation without a separate commit")
    else:
        decision = "draft_separated"
        reasons.append("committed effective state preserved")
        reasons.append("restored draft kept separate from applied sensor control")
        if recreation == "cancelled_edits":
            reasons.append("cancelled edit dropped the draft")
        elif draft is None:
            questions.append("no draft to restore")
        else:
            reasons.append("draft restored separately")
            if not draft_valid:
                questions.append("invalid draft not applied")

    for key, value in committed.items():
        token = f"committed:{key}={value}"
        if token not in preserved:
            raise ValueError("committed effective state must be preserved")
    if draft is not None:
        for key, value in draft.items():
            if f"committed:{key}={value}" in preserved and committed.get(key) != value:
                raise ValueError("draft value must not replace committed state")
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P019-06 must not yield qualified or allowed")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, dict, dict | None, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    recreation = payload["recreation"]
    if recreation not in RECREATIONS:
        raise ValueError("recreation is not a P019 repeat")
    committed = _control_map(payload["committed"], "committed")
    if not committed:
        raise ValueError("committed control must be non-empty")
    draft_value = payload["draft"]
    if draft_value is None:
        draft = None
    else:
        draft = _control_map(draft_value, "draft")
        if not draft:
            raise ValueError("draft must be a non-empty object or null")
    draft_valid = payload["draftValid"]
    applied = payload["appliedToCamera"]
    if type(draft_valid) is not bool or type(applied) is not bool:
        raise ValueError("draftValid and appliedToCamera must be bools")
    if draft is None and not draft_valid:
        raise ValueError("a missing draft cannot be marked invalid")
    if draft is None and applied:
        raise ValueError("a missing draft cannot reach the camera")
    if draft is not None:
        for value in draft.values():
            if value == "" and draft_valid:
                raise ValueError("a blank draft entry is not valid")
    return recreation, committed, draft, draft_valid, applied


def _control_map(value: object, name: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    cleaned: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key or key != key.strip():
            raise ValueError(f"{name} keys must be non-empty strings")
        if not isinstance(item, str) or item != item.strip():
            raise ValueError(f"{name} values must be strings")
        cleaned[key] = item
    return cleaned


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
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
