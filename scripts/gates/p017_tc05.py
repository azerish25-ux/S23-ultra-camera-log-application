"""TC-P017-05 source queue exhaustion.

The source queue has an explicit capacity. Below capacity the incoming frame
is appended. At capacity the failure policy records gap evidence and leaves
existing frames untouched. An unbounded queue or a hidden frame replacement
is rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P017-05"
INTERVENTION = "Delay the source consumer until its explicitly bounded queue reaches capacity."
EXPECTED = (
    "Trigger the documented stop or failure policy with gap evidence; "
    "never silently overwrite source frames."
)
NEGATIVE = "An unbounded queue or hidden frame replacement must fail."
_PAYLOAD_KEYS = (
    "capacity",
    "depth",
    "incomingFrame",
    "existingFrames",
    "unbounded",
    "hiddenReplacement",
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
    """Apply the bounded-queue policy. Do not overwrite source frames."""
    data = _payload(payload)
    reasons = [
        f"capacity {data['capacity']} depth {data['depth']}",
        INTERVENTION,
        EXPECTED,
    ]
    rejected: list[str] = []
    existing = list(data["existingFrames"])
    incoming = data["incomingFrame"]
    if data["unbounded"]:
        rejected.append("unbounded-queue")
    if data["hiddenReplacement"]:
        rejected.append("hidden-frame-replacement")
    if rejected:
        reasons.append(NEGATIVE)
        reasons.append("source frames were not overwritten")
        decision = "rejected"
        preserved = existing
    elif data["depth"] < data["capacity"]:
        decision = "enqueued"
        reasons.append("frame accepted below capacity")
        preserved = existing + [incoming]
    else:
        decision = "failed"
        rejected.append(incoming)
        reasons.append("failure policy")
        reasons.append("gap evidence " + incoming)
        reasons.append("source frames were not overwritten")
        preserved = existing
    if data["hiddenReplacement"] or data["unbounded"] or data["depth"] >= data["capacity"]:
        if incoming in preserved:
            raise ValueError("incoming frame must not overwrite or append on failure")
    for frame in existing:
        if frame not in preserved:
            raise ValueError("existing source frames must be preserved")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    capacity = payload["capacity"]
    depth = payload["depth"]
    if type(capacity) is not int or capacity < 1:
        raise ValueError("capacity must be a positive int")
    if type(depth) is not int or depth < 0 or depth > capacity:
        raise ValueError("depth must be an int from 0 through capacity")
    incoming = payload["incomingFrame"]
    if not isinstance(incoming, str) or not incoming or incoming != incoming.strip():
        raise ValueError("incomingFrame must be a non-empty string")
    frames = payload["existingFrames"]
    if not isinstance(frames, list):
        raise ValueError("existingFrames must be a list")
    seen: set[str] = set()
    for item in frames:
        if not isinstance(item, str) or not item or item != item.strip():
            raise ValueError("existingFrames entries must be non-empty strings")
        if item in seen:
            raise ValueError("existingFrames entries must be unique")
        seen.add(item)
    if len(frames) != depth:
        raise ValueError("depth must equal the number of existing frames")
    if incoming in seen:
        raise ValueError("incomingFrame must not already be queued")
    unbounded = _bool(payload["unbounded"], "unbounded")
    hidden = _bool(payload["hiddenReplacement"], "hiddenReplacement")
    return {
        "capacity": capacity,
        "depth": depth,
        "incomingFrame": incoming,
        "existingFrames": list(frames),
        "unbounded": unbounded,
        "hiddenReplacement": hidden,
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
        raise ValueError("TC-P017-05 must not yield qualified or allowed")
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
