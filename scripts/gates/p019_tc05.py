"""TC-P019-05 source queue exhaustion.

The source queue has a positive bound. One free slot still accepts a frame.
Exact capacity stops admission and records gap evidence. The frame that does
not fit is rejected. An unbounded queue or a hidden replacement is rejected,
and the frames already held are kept.
"""

from __future__ import annotations

CASE_ID = "TC-P019-05"
INTERVENTION = (
    "Delay the source consumer until its explicitly bounded queue reaches capacity."
)
EXPECTED = (
    "Trigger the documented stop or failure policy with gap evidence; never "
    "silently overwrite source frames."
)
NEGATIVE = "An unbounded queue or hidden frame replacement must fail."
REPEAT = "Repeat at capacity minus one, exact capacity, and the first rejected item."
_PAYLOAD_KEYS = (
    "capacity",
    "unbounded",
    "hiddenReplacement",
    "depth",
    "incoming",
    "frames",
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
    """Admit only while a bounded slot remains. Never overwrite a source frame."""
    capacity, unbounded, hidden, depth, incoming, frames = _payload(payload)
    reasons = [f"depth {depth}", f"incoming {incoming}"]
    rejected: list[str] = []
    questions: list[str] = []
    preserved = list(frames)

    if unbounded:
        rejected.append("unbounded-queue")
        reasons.append("an unbounded source queue is rejected")
    if hidden:
        rejected.append("hidden-frame-replacement")
        rejected.append(incoming)
        reasons.append("hidden frame replacement is rejected")
        reasons.append("existing source frames were not overwritten")
    if unbounded or hidden:
        if capacity is not None:
            reasons.append(f"declared capacity {capacity} does not authorize the negative")
        decision = "rejected"
    elif depth == capacity - 1:
        decision = "enqueued"
        preserved.append(incoming)
        reasons.append(f"capacity {capacity} still has one free slot")
        reasons.append("frame admitted without overwriting earlier frames")
    elif depth == capacity:
        decision = "stopped"
        rejected.append("rejected:" + incoming)
        reasons.append(f"capacity {capacity} reached")
        reasons.append("gap:" + incoming)
        reasons.append("documented stop policy; the incoming frame was not written over a held frame")
        questions.append("source consumer was late at exact capacity")
    else:
        decision = "enqueued"
        preserved.append(incoming)
        reasons.append(f"capacity {capacity} has room below the last free slot")

    for frame in frames:
        if frame not in preserved:
            raise ValueError("held source frames must be preserved")
    if decision == "stopped" and incoming in preserved:
        raise ValueError("the rejected frame must not replace a held frame")
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P019-05 must not yield qualified or allowed")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[int | None, bool, bool, int, str, list[str]]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    unbounded = payload["unbounded"]
    hidden = payload["hiddenReplacement"]
    if type(unbounded) is not bool or type(hidden) is not bool:
        raise ValueError("unbounded and hiddenReplacement must be bools")
    capacity = payload["capacity"]
    if unbounded:
        if capacity is not None and (type(capacity) is not int or capacity < 1):
            raise ValueError("capacity must be a positive int or null when unbounded")
    else:
        if type(capacity) is not int or capacity < 1:
            raise ValueError("capacity must be a positive int")
    depth = payload["depth"]
    if type(depth) is not int or depth < 0:
        raise ValueError("depth must be a non-negative int")
    incoming = payload["incoming"]
    if not isinstance(incoming, str) or not incoming or incoming != incoming.strip():
        raise ValueError("incoming must be a non-empty string")
    frames = payload["frames"]
    if not isinstance(frames, list):
        raise ValueError("frames must be a list")
    seen: set[str] = set()
    clean: list[str] = []
    for item in frames:
        if not isinstance(item, str) or not item or item != item.strip():
            raise ValueError("frames must contain non-empty strings")
        if item in seen:
            raise ValueError("frames must be unique")
        seen.add(item)
        clean.append(item)
    if len(clean) != depth:
        raise ValueError("depth must equal the number of held frames")
    if not unbounded and not hidden and depth > capacity:
        raise ValueError("depth cannot exceed a bounded capacity")
    if not hidden and incoming in seen:
        raise ValueError("incoming frame is already held")
    return capacity if type(capacity) is int else None, unbounded, hidden, depth, incoming, clean


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
