"""TC-P020-06 draft control recreation.

Interface recreation may restore an unapplied or invalid control draft.
Committed effective state stays applied. The draft stays labeled as a draft.
An invalid partial numeric entry that reaches the camera is rejected.

Baseline white-balance inventory stays in preservedResults. This host module
does not touch a device.
"""

from __future__ import annotations

CASE_ID = "TC-P020-06"
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
WB_INVENTORY = (
    "hardware.namespace:hardware.white_balance",
    "hardware.preset:daylight",
    "hardware.locked:true",
    "hardware.gains:1.42,1.00,1.78",
    "hardware.kelvin:unavailable",
    "scene.namespace:scene.calibration",
    "scene.profile:raw-neutral-v1",
    "scene.version:1",
    "scene.neutral:1.00,1.00,1.00",
    "creative.namespace:creative.preview",
    "creative.slider:warm",
    "creative.recipe:preview-warm-v1",
    "creative.tint:12",
    "source.metadata:unchanged",
)
_PAYLOAD_KEYS = {
    "event",
    "committedPreset",
    "committedGains",
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
    event, preset, gains, draft, valid, reaches = _payload(payload)
    preserved = list(WB_INVENTORY)
    preserved.append("applied.preset:" + preset)
    preserved.append("applied.gains:" + gains)
    reasons = [EXPECTED, "repeat event " + event]
    rejected: list[str] = []

    if reaches and not valid:
        decision = "rejected"
        rejected.append("invalid-draft-reached-camera")
        reasons.append(NEGATIVE)
        reasons.append("committed effective state preserved")
    elif reaches:
        decision = "rejected"
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
        raise ValueError("TC-P020-06 must not decide qualified or allowed")
    if "applied.preset:" + preset not in preserved or "applied.gains:" + gains not in preserved:
        raise ValueError("committed white-balance state must be preserved")
    for item in WB_INVENTORY:
        if item not in preserved:
            raise ValueError("white-balance inventory must be preserved")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != _PAYLOAD_KEYS:
        raise ValueError("invalid payload keys")
    event = payload["event"]
    if event not in REPEATS:
        raise ValueError("event is not a TC-P020-06 repeat")
    return (
        event,
        _text(payload["committedPreset"], "committedPreset"),
        _text(payload["committedGains"], "committedGains"),
        _text(payload["draft"], "draft"),
        _bool(payload["draftValid"], "draftValid"),
        _bool(payload["reachesCamera"], "reachesCamera"),
    )


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(name + " must be a bool")
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(name + " must be a non-empty string")
    return value


def _tokens(value: object, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(name + " must be a list")
    seen: set[str] = set()
    tokens: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item or item != item.strip():
            raise ValueError(name + " entries must be non-empty strings")
        if item in seen:
            raise ValueError(name + " entries must be unique")
        seen.add(item)
        tokens.append(item)
    return tokens


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

