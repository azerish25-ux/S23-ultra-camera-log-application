"""TC-P020-05 source queue exhaustion.

The source queue is explicitly bounded. Below capacity an incoming frame is
enqueued. At capacity the documented stop policy fires, gap evidence is kept,
and the incoming frame is not written over retained frames. An unbounded
queue or a hidden frame replacement is rejected.

Baseline white-balance inventory stays in preservedResults. This host module
does not touch a device.
"""

from __future__ import annotations

CASE_ID = "TC-P020-05"
INTERVENTION = (
    "Delay the source consumer until its explicitly bounded queue reaches capacity."
)
EXPECTED = (
    "Trigger the documented stop or failure policy with gap evidence; never "
    "silently overwrite source frames."
)
NEGATIVE = "An unbounded queue or hidden frame replacement must fail."
REPEATS = (
    "capacity_minus_one",
    "exact_capacity",
    "first_rejected_item",
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
    "capacity",
    "queued",
    "incoming",
    "bounded",
    "replacesHidden",
    "retainedFrames",
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
    """Stop at a full bounded queue. Never replace retained source frames."""
    capacity, queued, incoming, bounded, replaces, retained = _payload(payload)
    preserved = list(WB_INVENTORY)
    preserved.extend("frame:" + item for item in retained)
    reasons = [EXPECTED]
    rejected: list[str] = []
    questions: list[str] = []

    if not bounded or replaces:
        decision = "rejected"
        reasons.append(NEGATIVE)
        if not bounded:
            rejected.append("unbounded-queue")
            reasons.append("unbounded queue is rejected")
        if replaces:
            rejected.append("hidden-frame-replacement")
            reasons.append("hidden frame replacement is rejected")
        reasons.append("retained source frames were not overwritten")
        if any(item == "frame:" + incoming for item in preserved):
            raise ValueError("hidden replacement must not insert the incoming frame")
    elif queued < capacity:
        decision = "enqueued"
        preserved.append("frame:" + incoming)
        if queued == capacity - 1:
            reasons.append("repeat capacity_minus_one")
        reasons.append(
            "queued " + str(queued) + " is below capacity " + str(capacity)
        )
    else:
        decision = "stopped"
        rejected.append(incoming)
        preserved.append("gap-evidence:" + incoming)
        reasons.append("repeat exact_capacity")
        reasons.append("repeat first_rejected_item")
        reasons.append(
            "documented stop policy at capacity " + str(capacity) + " with gap evidence"
        )
        reasons.append("incoming frame " + incoming + " was not written over retained frames")

    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P020-05 must not decide qualified or allowed")
    for item in retained:
        if "frame:" + item not in preserved:
            raise ValueError("retained source frames must survive queue policy")
    for item in WB_INVENTORY:
        if item not in preserved:
            raise ValueError("white-balance inventory must be preserved")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != _PAYLOAD_KEYS:
        raise ValueError("invalid payload keys")
    capacity = _positive(payload["capacity"], "capacity")
    queued = payload["queued"]
    if type(queued) is not int or queued < 0 or queued > capacity:
        raise ValueError("queued must be an int from 0 through capacity")
    incoming = _text(payload["incoming"], "incoming")
    retained = _tokens(payload["retainedFrames"], "retainedFrames")
    if incoming in retained:
        raise ValueError("incoming frame must not already be retained")
    return (
        capacity,
        queued,
        incoming,
        _bool(payload["bounded"], "bounded"),
        _bool(payload["replacesHidden"], "replacesHidden"),
        retained,
    )


def _positive(value: object, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(name + " must be a positive int")
    return value


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

