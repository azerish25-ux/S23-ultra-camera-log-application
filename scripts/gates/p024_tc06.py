"""TC-P024-06 draft control recreation.

Rotation, process recreation, manual-mode transition, and cancelled edits keep
the committed effective state. A restored draft stays labelled as a draft.
An invalid partial numeric entry that reaches the camera fails.
"""

from __future__ import annotations

CASE_ID = "TC-P024-06"
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
    "committed",
    "draft",
    "draftAppliedToCamera",
    "draftSeparated",
    "invalidPartial",
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
    """Keep committed state. Reject a draft that is applied or visually merged."""
    fields = _payload(payload)
    reasons = [f"recreation {fields['recreation']}", INTERVENTION]
    rejected: list[str] = []
    if fields["invalidPartial"] and fields["draftAppliedToCamera"]:
        rejected.append("invalid-partial-applied")
    if fields["draftAppliedToCamera"]:
        rejected.append("draft-applied-to-camera")
    if fields["draft"] is not None and not fields["draftSeparated"]:
        rejected.append("draft-not-separated")

    open_questions: list[str] = []
    if rejected:
        decision = "rejected"
        reasons.append(NEGATIVE if "invalid-partial-applied" in rejected else EXPECTED)
        reasons.append("draft must not become applied sensor control")
    else:
        decision = "committed_preserved"
        reasons.append(EXPECTED)
        if fields["draft"] is not None:
            open_questions.append("restored draft is not applied sensor control")
            reasons.append("restored draft kept separate from committed state")
        else:
            reasons.append("no draft remained; committed state kept")

    preserved = [f"committed:{fields['committed']}"]
    if fields["draft"] is not None:
        preserved.append(f"draft:{fields['draft']}")
    return _result(decision, reasons, rejected, preserved, open_questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    recreation = payload["recreation"]
    if recreation not in RECREATIONS:
        raise ValueError("recreation is not a TC-P024-06 repeat")
    committed = _label(payload["committed"], "committed")
    draft = payload["draft"]
    if draft is not None:
        draft = _label(draft, "draft")
    applied = _bool(payload["draftAppliedToCamera"], "draftAppliedToCamera")
    separated = _bool(payload["draftSeparated"], "draftSeparated")
    invalid = _bool(payload["invalidPartial"], "invalidPartial")
    if draft is None and (applied or invalid or not separated):
        raise ValueError("absent draft cannot be applied, invalid, or unseparated")
    if invalid and draft is None:
        raise ValueError("invalid partial entry requires a draft")
    return {
        "recreation": recreation,
        "committed": committed,
        "draft": draft,
        "draftAppliedToCamera": applied,
        "draftSeparated": separated,
        "invalidPartial": invalid,
    }


def _label(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\n" in value:
        raise ValueError(f"{name} must be a non-empty single-line string")
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
        raise ValueError("TC-P024-06 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
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
