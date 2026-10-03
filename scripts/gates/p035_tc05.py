"""TC-P035-05 writer pool saturation.

Intervention: Pause persistent writing until preallocated source-copy capacity
is exhausted.
Expected: Stop visibly with exact retained-frame accounting and no overwritten
queued samples.
Negative: Discarding the oldest RAW record to maintain the recording indicator
must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P035-05"
INTERVENTION = (
    "Pause persistent writing until preallocated source-copy capacity is exhausted."
)
EXPECTED = (
    "Stop visibly with exact retained-frame accounting and no overwritten queued samples."
)
NEGATIVE = "Discarding the oldest RAW record to maintain the recording indicator must fail."

STALLS = ("short", "prolonged")
INDICATORS = ("recording", "stopped")
_PAYLOAD_KEYS = (
    "capacity",
    "queuedIds",
    "stall",
    "cancel",
    "discardOldest",
    "indicator",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "held", "stopped", "cancelled")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Account for every queued RAW id. Never drop the oldest to look busy."""
    capacity, queued, stall, cancel, discard, indicator = _payload(payload)
    preserved = [f"frame:{ident}" for ident in queued]
    preserved.extend((
        f"retained:{len(queued)}",
        f"capacity:{capacity}",
        f"stall:{stall}",
        f"indicator:{indicator}",
    ))
    if discard:
        claims = ["discard-oldest-raw"]
        if indicator == "recording":
            claims.append("indicator-maintained-by-discard")
        return _result(
            "rejected",
            [EXPECTED, NEGATIVE, "queued samples were not overwritten"],
            claims,
            preserved,
            ["oldest frame retained"],
        )
    if len(queued) == capacity and indicator == "recording":
        return _result(
            "rejected",
            [EXPECTED, "a full pool cannot keep a recording indicator"],
            ["false-recording-indicator"],
            preserved,
            ["stop not visible"],
        )
    if len(queued) == capacity and cancel:
        return _result(
            "cancelled",
            [EXPECTED, "cancellation during the full-pool state keeps every queued id"],
            [],
            preserved,
            ["full pool cancelled"],
        )
    if len(queued) == capacity:
        return _result(
            "stopped",
            [EXPECTED, "pool exhaustion stops with exact retained-frame accounting"],
            [],
            preserved,
            [f"{stall} stall stopped"],
        )
    return _result(
        "held",
        [EXPECTED, "capacity remains and no queued sample was overwritten"],
        [],
        preserved,
        [f"{stall} stall still within capacity"],
    )


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload")
    capacity = payload["capacity"]
    queued = payload["queuedIds"]
    stall = payload["stall"]
    cancel = payload["cancel"]
    discard = payload["discardOldest"]
    indicator = payload["indicator"]
    if type(capacity) is not int or capacity < 1:
        raise ValueError("capacity")
    if (
        not isinstance(queued, list)
        or not queued
        or len(queued) != len(set(queued))
        or any(not isinstance(item, str) or not item for item in queued)
    ):
        raise ValueError("queuedIds")
    if len(queued) > capacity:
        raise ValueError("queue cannot already exceed capacity")
    if cancel and len(queued) != capacity:
        raise ValueError("cancellation repeat is the full-pool state")
    if stall not in STALLS or indicator not in INDICATORS:
        raise ValueError("stall or indicator")
    if type(cancel) is not bool or type(discard) is not bool:
        raise ValueError("flags")
    return capacity, list(queued), stall, cancel, discard, indicator


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
