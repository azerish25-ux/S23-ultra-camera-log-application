"""TC-P033-05 writer pool saturation.

Persistent writing is paused until the preallocated source-copy pool is full.
The stop is visible and the retained-frame count matches the pool. Discarding
the oldest RAW record to keep a recording indicator is rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P033-05"
INTERVENTION = "Pause persistent writing until preallocated source-copy capacity is exhausted."
EXPECTED = "Stop visibly with exact retained-frame accounting and no overwritten queued samples."
NEGATIVE = "Discarding the oldest RAW record to maintain the recording indicator must fail."
REPEATS = ("short stalls", "prolonged stalls", "cancellation during the full-pool state")
_STALLS = ("short", "prolonged")
_PAYLOAD_KEYS = (
    "capacity",
    "queuedIds",
    "retained",
    "stall",
    "cancelled",
    "discardOldest",
    "indicatorOn",
    "overwrittenIds",
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
    """Stop when the pool is full without dropping queued RAW records."""
    data = _payload(payload)
    queued = len(data["queuedIds"])
    expected = min(queued, data["capacity"])
    full = queued >= data["capacity"]
    reasons = [
        "stall " + data["stall"],
        "queued " + str(queued),
        "capacity " + str(data["capacity"]),
    ]
    rejected: list[str] = []
    if data["discardOldest"]:
        rejected.append("oldest-discarded")
        reasons.append(NEGATIVE)
        if data["indicatorOn"]:
            reasons.append("the recording indicator does not justify dropping the oldest RAW record")
    if data["overwrittenIds"]:
        rejected.append("overwritten-samples")
        reasons.append("queued samples were overwritten")
    if data["retained"] != expected and not data["discardOldest"]:
        rejected.append("accounting-mismatch")
        reasons.append("retained count does not match the preallocated pool")
    if rejected:
        decision = "rejected"
    elif not full and data["cancelled"]:
        decision = "cancelled"
        reasons.append("cancellation before the pool was full")
    elif not full:
        decision = "accepting"
        reasons.append("preallocated capacity is not exhausted")
    else:
        decision = "stopped"
        reasons.append(EXPECTED)
        reasons.append("stopped is a visible host accounting label, not a recording qualification")
        if data["cancelled"]:
            reasons.append("cancellation during the full-pool state kept the retained frames")
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P033-05 must not yield qualified or allowed")
    questions = []
    if data["stall"] == "prolonged" and decision == "stopped":
        questions.append("a prolonged stall is not evidence the sensor kept the advertised rate")
    return _result(decision, reasons, rejected, _preserved(data, expected), questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    capacity = payload["capacity"]
    if type(capacity) is not int or capacity <= 0:
        raise ValueError("capacity must be a positive int")
    queued = _tokens(payload["queuedIds"], "queuedIds", allow_empty=True)
    retained = payload["retained"]
    if type(retained) is not int or retained < 0:
        raise ValueError("retained must be a non-negative int")
    stall = payload["stall"]
    if stall not in _STALLS:
        raise ValueError("stall must be short or prolonged")
    overwritten = _tokens(payload["overwrittenIds"], "overwrittenIds", allow_empty=True)
    if any(item not in queued for item in overwritten):
        raise ValueError("overwrittenIds must be queued ids")
    return {
        "capacity": capacity,
        "queuedIds": queued,
        "retained": retained,
        "stall": stall,
        "cancelled": _bool(payload["cancelled"], "cancelled"),
        "discardOldest": _bool(payload["discardOldest"], "discardOldest"),
        "indicatorOn": _bool(payload["indicatorOn"], "indicatorOn"),
        "overwrittenIds": overwritten,
    }


def _preserved(data: dict, expected: int) -> list[str]:
    preserved = ["queued:" + item for item in data["queuedIds"]]
    preserved.extend("overwritten:" + item for item in data["overwrittenIds"])
    preserved.extend([
        "capacity:" + str(data["capacity"]),
        "retained-claimed:" + str(data["retained"]),
        "retained-expected:" + str(expected),
        "stall:" + data["stall"],
        "indicator:" + ("on" if data["indicatorOn"] else "off"),
    ])
    if data["cancelled"] and len(data["queuedIds"]) >= data["capacity"]:
        preserved.append("cancelled:full-pool")
    elif data["cancelled"]:
        preserved.append("cancelled:before-full")
    return preserved


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _tokens(value: object, name: str, allow_empty: bool) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError(f"{name} must be a list")
    items = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item or item != item.strip() or item in seen:
            raise ValueError(f"{name} items must be unique non-empty strings")
        seen.add(item)
        items.append(item)
    return items


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P033-05 must not yield qualified or allowed")
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
