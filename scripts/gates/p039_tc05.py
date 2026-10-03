"""TC-P039-05 writer pool saturation.

A paused writer that fills the preallocated copy pool stops visibly. Queued
samples stay in order. Discarding the oldest RAW record to keep a green
recording indicator is rejected. Short stalls, prolonged stalls, and
cancellation during the full-pool state share that stop.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P039-05"
INTERVENTION = "Pause persistent writing until preallocated source-copy capacity is exhausted."
EXPECTED = "Stop visibly with exact retained-frame accounting and no overwritten queued samples."
NEGATIVE = "Discarding the oldest RAW record to maintain the recording indicator must fail."

_STALLS = ("short", "prolonged", "cancelled_full")
_INDICATORS = ("green", "stopped")
_TS = re.compile(r"^(0|[1-9][0-9]*)$")
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_PAYLOAD_KEYS = (
    "capacity",
    "stall",
    "queuedIds",
    "queuedTimestamps",
    "overflowId",
    "overflowTimestamp",
    "overwriteOldest",
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
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Stop when the copy pool is full. Do not overwrite the oldest frame."""
    fields = _payload(payload)
    frames = [
        f"frame:{ident}@{stamp}"
        for ident, stamp in zip(fields["queuedIds"], fields["queuedTimestamps"])
    ]
    overflow = f"overflow:{fields['overflowId']}@{fields['overflowTimestamp']}"
    preserved = frames + [overflow]
    reasons = [
        EXPECTED,
        INTERVENTION,
        f"retained {fields['capacity']}",
        f"stall {fields['stall']}",
    ]
    questions = [_STALL_QUESTION[fields["stall"]]]
    if fields["overwriteOldest"] or fields["indicator"] == "green":
        reasons.append(NEGATIVE)
        reasons.append("oldest queued sample was kept in the inventory")
        return _result(
            "rejected",
            reasons,
            ["oldest-discarded-for-indicator"],
            preserved,
            questions,
        )
    reasons.append("queued samples were not overwritten")
    reasons.append("overflow is visible")
    return _result("stopped_visible", reasons, [overflow], preserved, questions)


_STALL_QUESTION = {
    "short": "short stall stopped at the full pool",
    "prolonged": "prolonged stall stopped at the full pool",
    "cancelled_full": "cancellation during the full-pool state did not resume the take",
}


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    capacity = payload["capacity"]
    if type(capacity) is not int or not 1 <= capacity <= 32:
        raise ValueError("capacity must be an int from 1 to 32")
    stall = payload["stall"]
    if stall not in _STALLS:
        raise ValueError("stall is not a TC-P039-05 repeat")
    queued = _tokens(payload["queuedIds"], "queuedIds")
    stamps = _timestamps(payload["queuedTimestamps"], "queuedTimestamps")
    if len(queued) != capacity or len(stamps) != capacity:
        raise ValueError("queued samples must equal capacity")
    overflow_id = payload["overflowId"]
    overflow_ts = payload["overflowTimestamp"]
    if not isinstance(overflow_id, str) or _TOKEN.fullmatch(overflow_id) is None:
        raise ValueError("overflowId must be a token")
    if overflow_id in queued:
        raise ValueError("overflowId must be new")
    if not isinstance(overflow_ts, str) or _TS.fullmatch(overflow_ts) is None:
        raise ValueError("overflowTimestamp must be canonical")
    if int(overflow_ts) <= int(stamps[-1]):
        raise ValueError("overflowTimestamp must follow the queued samples")
    overwrite = payload["overwriteOldest"]
    if type(overwrite) is not bool:
        raise ValueError("overwriteOldest must be a bool")
    indicator = payload["indicator"]
    if indicator not in _INDICATORS:
        raise ValueError("indicator must be green or stopped")
    return {
        "capacity": capacity,
        "stall": stall,
        "queuedIds": queued,
        "queuedTimestamps": stamps,
        "overflowId": overflow_id,
        "overflowTimestamp": overflow_ts,
        "overwriteOldest": overwrite,
        "indicator": indicator,
    }


def _tokens(value: object, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(label + " must be a list")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or _TOKEN.fullmatch(item) is None:
            raise ValueError(label + " must be tokens")
        if item in items:
            raise ValueError(label + " must be unique")
        items.append(item)
    return items


def _timestamps(value: object, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(label + " must be a list")
    items: list[str] = []
    previous: int | None = None
    for item in value:
        if not isinstance(item, str) or _TS.fullmatch(item) is None:
            raise ValueError(label + " must be canonical timestamps")
        stamp = int(item)
        if previous is not None and stamp <= previous:
            raise ValueError(label + " must strictly increase")
        previous = stamp
        items.append(item)
    return items


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in _FORBIDDEN:
        raise ValueError("TC-P039-05 must not yield qualified or allowed")
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
