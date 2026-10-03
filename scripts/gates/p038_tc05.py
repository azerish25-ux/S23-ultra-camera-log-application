"""TC-P038-05 writer pool saturation.

Intervention: Pause persistent writing until preallocated source-copy capacity
is exhausted.
Expected: Stop visibly with exact retained-frame accounting and no overwritten
queued samples.
Negative: Discarding the oldest RAW record to maintain the recording indicator
must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P038-05"
INTERVENTION = "Pause persistent writing until preallocated source-copy capacity is exhausted."
EXPECTED = "Stop visibly with exact retained-frame accounting and no overwritten queued samples."
NEGATIVE = "Discarding the oldest RAW record to maintain the recording indicator must fail."

_STALLS = ("short", "prolonged")
_PAYLOAD_KEYS = (
    "capacity",
    "queuedIds",
    "incomingId",
    "stall",
    "cancelDuringFull",
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
_DECISIONS = ("rejected", "stopped", "queued")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Stop when the copy pool is full. Never drop the oldest queued sample."""
    capacity, queued, incoming, stall, cancel, discard, indicator = _payload(payload)
    full = len(queued) >= capacity
    preserved = [f"queued:{item}" for item in queued]
    preserved.append(f"capacity:{capacity}")
    preserved.append(f"stall:{stall}")
    if discard:
        preserved.append(f"refused:{incoming}")
        return _result(
            "rejected",
            [
                NEGATIVE,
                EXPECTED,
                "oldest queued sample was not overwritten",
                "recording indicator was not kept green by discarding RAW",
            ],
            ["discarded-oldest-raw"],
            preserved,
            ["recording indicator is not retention"],
        )
    if full:
        preserved.append(f"refused:{incoming}")
        questions = [f"{stall}-stall", f"retained:{len(queued)}"]
        if cancel:
            questions.append("cancelled-during-full")
        if indicator:
            questions.append("recording indicator is not proof of retention")
        return _result(
            "stopped",
            [
                EXPECTED,
                f"stopped with {len(queued)} retained frames",
                "incoming sample was refused instead of overwriting a queued sample",
            ],
            [],
            preserved,
            questions,
        )
    preserved.append(f"queued:{incoming}")
    return _result(
        "queued",
        [EXPECTED, "capacity remains", "this queue acceptance is not a recording qualification"],
        [],
        preserved,
        [],
    )


def _payload(payload: object) -> tuple[int, list[str], str, str, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    capacity = payload["capacity"]
    if type(capacity) is not int or capacity <= 0:
        raise ValueError("capacity must be a positive int")
    queued = payload["queuedIds"]
    if type(queued) is not list or any(type(item) is not str or not item for item in queued):
        raise ValueError("queuedIds must be a list of non-empty strings")
    if len(queued) != len(set(queued)):
        raise ValueError("queuedIds must be unique")
    incoming = payload["incomingId"]
    if type(incoming) is not str or not incoming or incoming in queued:
        raise ValueError("incomingId must be a new non-empty string")
    stall = payload["stall"]
    if stall not in _STALLS:
        raise ValueError("stall must be short or prolonged")
    cancel = payload["cancelDuringFull"]
    discard = payload["discardOldest"]
    indicator = payload["recordingIndicator"]
    if type(cancel) is not bool or type(discard) is not bool or type(indicator) is not bool:
        raise ValueError("flags must be bools")
    return capacity, list(queued), incoming, stall, cancel, discard, indicator


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
