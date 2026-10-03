"""TC-P020-08 double stop and repeated cleanup.

Redundant stop, close, cancellation, and detach events are idempotent.
Cleanup keeps one terminal take identity. Double release, duplicate
publication, or a second take created by cleanup is rejected.

Baseline white-balance inventory stays in preservedResults. This host module
does not touch a device.
"""

from __future__ import annotations

CASE_ID = "TC-P020-08"
INTERVENTION = "Send redundant stop, close, cancellation, and detach events in different orders."
EXPECTED = "Make cleanup idempotent and preserve a single coherent terminal take identity."
NEGATIVE = "Double release, duplicate publication, or a second take created by cleanup must fail."
REPEATS = (
    "empty_startup",
    "active_video",
    "active_audiovisual",
    "recovery_reopening",
)
EVENTS = ("stop", "close", "cancel", "detach")
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
    "scenario",
    "events",
    "takeId",
    "doubleRelease",
    "duplicatePublication",
    "secondTake",
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
    """Collapse redundant cleanup to one take. Reject a second publication."""
    scenario, events, take_id, double_release, duplicate, second = _payload(payload)
    preserved = list(WB_INVENTORY)
    preserved.append("take:" + take_id)
    reasons = [EXPECTED, "repeat scenario " + scenario, "events " + ",".join(events)]
    rejected: list[str] = []
    negative = double_release or duplicate or second

    if negative:
        decision = "rejected"
        reasons.append(NEGATIVE)
        if double_release:
            rejected.append("double-release")
            reasons.append("double release is rejected")
        if duplicate:
            rejected.append("duplicate-publication")
            reasons.append("duplicate publication is rejected")
        if second:
            rejected.append("second-take")
            reasons.append("cleanup must not create a second take")
    else:
        decision = "idempotent"
        reasons.append("cleanup is idempotent")
        reasons.append("single terminal take " + take_id)

    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P020-08 must not decide qualified or allowed")
    if preserved.count("take:" + take_id) != 1:
        raise ValueError("terminal take identity must stay singular")
    for item in WB_INVENTORY:
        if item not in preserved:
            raise ValueError("white-balance inventory must be preserved")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != _PAYLOAD_KEYS:
        raise ValueError("invalid payload keys")
    scenario = payload["scenario"]
    if scenario not in REPEATS:
        raise ValueError("scenario is not a TC-P020-08 repeat")
    events = payload["events"]
    if not isinstance(events, list) or not events:
        raise ValueError("events must be a non-empty list")
    parsed: list[str] = []
    for item in events:
        if item not in EVENTS:
            raise ValueError("event must be stop, close, cancel, or detach")
        parsed.append(item)
    return (
        scenario,
        parsed,
        _text(payload["takeId"], "takeId"),
        _bool(payload["doubleRelease"], "doubleRelease"),
        _bool(payload["duplicatePublication"], "duplicatePublication"),
        _bool(payload["secondTake"], "secondTake"),
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

