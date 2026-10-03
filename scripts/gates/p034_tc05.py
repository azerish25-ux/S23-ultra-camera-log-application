"""TC-P034-05 writer pool saturation.

A full preallocated copy pool stops visibly or cancels with every queued id
still present. Discarding the oldest RAW record to keep a recording indicator
fails and does not erase those ids.
"""

from __future__ import annotations

CASE_ID = "TC-P034-05"
INTERVENTION = (
    "Pause persistent writing until preallocated source-copy capacity is exhausted."
)
EXPECTED = (
    "Stop visibly with exact retained-frame accounting and no overwritten queued samples."
)
NEGATIVE = "Discarding the oldest RAW record to maintain the recording indicator must fail."

STALLS = ("short", "prolonged")
_PAYLOAD_KEYS = ("capacity", "queuedIds", "stall", "cancelDuringFull", "discardOldest")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "accepting", "stopped", "cancelled"}
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Account for every queued frame when the copy pool is full."""
    capacity, queued, stall, cancel, discard = _payload(payload)
    preserved = [f"capacity:{capacity}", f"retained:{len(queued)}", f"stall:{stall}"]
    preserved.extend(f"frame:{item}" for item in queued)
    reasons = [INTERVENTION, EXPECTED, f"stall {stall}", f"retained {len(queued)} of capacity {capacity}"]
    if discard:
        reasons.append(NEGATIVE)
        reasons.append("queued samples were not overwritten to keep a recording indicator")
        return _result(
            "rejected",
            reasons,
            ["discard-oldest"],
            preserved,
            ["recording indicator is not retained-frame accounting"],
        )
    if len(queued) < capacity:
        reasons.append("pool is not exhausted; queued samples remain")
        return _result("accepting", reasons, [], preserved, ["pool not full"])
    if cancel:
        reasons.append("cancellation during the full-pool state kept every queued sample")
        return _result("cancelled", reasons, [], preserved, ["cancelled during full pool"])
    reasons.append("visible stop; no queued sample was overwritten")
    return _result("stopped", reasons, [], preserved, ["visible stop"])


def _payload(payload: object) -> tuple[int, list[str], str, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    capacity = payload["capacity"]
    if type(capacity) is not int or not 1 <= capacity <= 64:
        raise ValueError("capacity must be an int from 1 to 64")
    queued = payload["queuedIds"]
    if (
        not isinstance(queued, list)
        or not queued
        or len(queued) > capacity
        or len(queued) != len(set(queued))
        or any(not isinstance(item, str) or not item or item != item.strip() for item in queued)
    ):
        raise ValueError("queuedIds must be unique non-empty ids within capacity")
    stall = payload["stall"]
    if stall not in STALLS:
        raise ValueError("stall must be short or prolonged")
    cancel = payload["cancelDuringFull"]
    discard = payload["discardOldest"]
    if type(cancel) is not bool or type(discard) is not bool:
        raise ValueError("cancelDuringFull and discardOldest must be bools")
    if cancel and len(queued) != capacity:
        raise ValueError("cancelDuringFull requires a full pool")
    return capacity, list(queued), stall, cancel, discard


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
