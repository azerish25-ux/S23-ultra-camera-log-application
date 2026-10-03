"""TC-P036-05 writer pool saturation.

Intervention: Pause persistent writing until preallocated source-copy capacity
is exhausted.
Expected: Stop visibly with exact retained-frame accounting and no overwritten
queued samples.
Negative: Discarding the oldest RAW record to maintain the recording indicator
must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P036-05"
INTERVENTION = "Pause persistent writing until preallocated source-copy capacity is exhausted."
EXPECTED = "Stop visibly with exact retained-frame accounting and no overwritten queued samples."
NEGATIVE = "Discarding the oldest RAW record to maintain the recording indicator must fail."

_STALLS = ("short", "prolonged")
_PAYLOAD_KEYS = (
    "capacity",
    "queuedIds",
    "droppedIds",
    "stall",
    "cancelled",
    "discardOldest",
    "recordingIndicator",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "stopped", "cancelled", "holding")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Stop a full preallocated pool without dropping queued RAW samples."""
    fields = _payload(payload)
    preserved = [
        f"capacity:{fields['capacity']}",
        f"stall:{fields['stall']}",
        f"retained:{len(fields['queuedIds'])}",
    ]
    preserved.extend(f"frame:{item}" for item in fields["queuedIds"])
    preserved.extend(f"dropped:{item}" for item in fields["droppedIds"])
    full = len(fields["queuedIds"]) == fields["capacity"]
    rejected: list[str] = []
    questions: list[str] = []
    if fields["discardOldest"]:
        rejected.append("discard-oldest-raw")
        if fields["recordingIndicator"]:
            rejected.append("recording-indicator-maintained")
        decision = "rejected"
        reasons = [NEGATIVE, EXPECTED, "queued samples were not overwritten"]
        questions.append("dropped samples remain in the accounting")
    elif fields["cancelled"]:
        decision = "cancelled"
        reasons = [
            EXPECTED,
            "cancellation during the pool state kept every queued sample",
            f"stall {fields['stall']}",
        ]
        if full:
            reasons.append("cancelled while the preallocated pool was full")
        questions.append("cancelled")
    elif full:
        decision = "stopped"
        reasons = [
            EXPECTED,
            f"stopped at capacity {fields['capacity']} after a {fields['stall']} stall",
            "no queued sample was overwritten",
        ]
        questions.append("pool exhausted")
    else:
        decision = "holding"
        reasons = [
            INTERVENTION,
            f"pool holds {len(fields['queuedIds'])} of {fields['capacity']}",
            "no queued sample was overwritten",
        ]
    reasons.append(f"exact retained count {len(fields['queuedIds'])}")
    return _result(decision, reasons, rejected, preserved, questions)


def _ids(value: object, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(label + " must be a list")
    if any(not isinstance(item, str) or not item for item in value):
        raise ValueError(label + " must be non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(label + " must be unique")
    return list(value)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    capacity = payload["capacity"]
    if type(capacity) is not int or capacity <= 0:
        raise ValueError("capacity must be a positive int")
    queued = _ids(payload["queuedIds"], "queuedIds")
    dropped = _ids(payload["droppedIds"], "droppedIds")
    if len(queued) > capacity:
        raise ValueError("queuedIds cannot exceed preallocated capacity")
    overlap = set(queued) & set(dropped)
    if overlap:
        raise ValueError("droppedIds must not still be queued")
    stall = payload["stall"]
    if stall not in _STALLS:
        raise ValueError("stall must be short or prolonged")
    cancelled = payload["cancelled"]
    discard = payload["discardOldest"]
    indicator = payload["recordingIndicator"]
    if type(cancelled) is not bool or type(discard) is not bool or type(indicator) is not bool:
        raise ValueError("cancelled, discardOldest, and recordingIndicator must be bools")
    if discard == (len(dropped) == 0):
        raise ValueError("discardOldest must match droppedIds")
    return {
        "capacity": capacity,
        "queuedIds": queued,
        "droppedIds": dropped,
        "stall": stall,
        "cancelled": cancelled,
        "discardOldest": discard,
        "recordingIndicator": indicator,
    }


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("pool decision cannot be qualified or allowed")
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
