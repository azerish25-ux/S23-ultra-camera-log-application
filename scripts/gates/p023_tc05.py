"""TC-P023-05 source queue exhaustion.

The source queue is explicitly bounded. Capacity minus one and exact capacity
still hold the original frames. The first item that does not fit triggers the
documented stop or failure policy and records gap evidence. An unbounded queue
or a hidden frame replacement fails.
"""

from __future__ import annotations

CASE_ID = "TC-P023-05"
INTERVENTION = (
    "Delay the source consumer until its explicitly bounded queue reaches capacity."
)
EXPECTED = (
    "Trigger the documented stop or failure policy with gap evidence; "
    "never silently overwrite source frames."
)
NEGATIVE = "An unbounded queue or hidden frame replacement must fail."
POSITIONS = ("capacity_minus_one", "exact_capacity", "first_rejected")
_PAYLOAD_KEYS = (
    "capacity",
    "position",
    "queuedIds",
    "rejectedItemId",
    "unbounded",
    "hiddenReplacement",
    "stopOrFail",
    "gapEvidence",
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
    """Keep every queued source frame. Reject unbounded queues and silent overwrite."""
    fields = _payload(payload)
    reasons = [
        f"position {fields['position']} capacity {fields['capacity']}",
        INTERVENTION,
    ]
    rejected: list[str] = []
    if fields["unbounded"]:
        rejected.append("unbounded-queue")
    if fields["hiddenReplacement"]:
        rejected.append("hidden-frame-replacement")
    if fields["position"] == "first_rejected" and not fields["stopOrFail"]:
        rejected.append("missing-stop-policy")
    if fields["position"] == "first_rejected" and not fields["gapEvidence"]:
        rejected.append("missing-gap-evidence")

    open_questions: list[str] = []
    if rejected:
        decision = "rejected"
        reasons.append(NEGATIVE)
        reasons.append("source frames must not be overwritten or queued without a bound")
    elif fields["position"] == "capacity_minus_one":
        decision = "accepted"
        reasons.append("queue still below capacity; source frames retained")
    elif fields["position"] == "exact_capacity":
        decision = "at_capacity"
        reasons.append("queue is at its explicit bound; no source frame was replaced")
    else:
        decision = "stopped"
        reasons.append(EXPECTED)
        reasons.append("first rejected item recorded as gap evidence")
        open_questions.append("gap evidence recorded; source frames were not replaced")

    preserved = [f"capacity:{fields['capacity']}"]
    preserved.extend(f"frame:{item}" for item in fields["queuedIds"])
    if fields["rejectedItemId"] is not None:
        preserved.append(f"gap:{fields['rejectedItemId']}")
    return _result(decision, reasons, rejected, preserved, open_questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    capacity = payload["capacity"]
    if type(capacity) is not int or not 1 <= capacity <= 64:
        raise ValueError("capacity must be an int from 1 to 64")
    position = payload["position"]
    if position not in POSITIONS:
        raise ValueError("position is not a TC-P023-05 repeat")
    queued = _ids(payload["queuedIds"])
    expected_len = capacity - 1 if position == "capacity_minus_one" else capacity
    if len(queued) != expected_len:
        raise ValueError("queuedIds length does not match the position")
    rejected_item = payload["rejectedItemId"]
    stop_or_fail = _bool(payload["stopOrFail"], "stopOrFail")
    gap = _bool(payload["gapEvidence"], "gapEvidence")
    if position == "first_rejected":
        if not isinstance(rejected_item, str) or not rejected_item or rejected_item in queued:
            raise ValueError("rejectedItemId must be a new non-empty token")
        if " " in rejected_item or rejected_item != rejected_item.strip():
            raise ValueError("rejectedItemId must be a token")
    else:
        if rejected_item is not None or stop_or_fail or gap:
            raise ValueError("only the first rejected item carries stop and gap evidence")
        rejected_item = None
    return {
        "capacity": capacity,
        "position": position,
        "queuedIds": queued,
        "rejectedItemId": rejected_item,
        "unbounded": _bool(payload["unbounded"], "unbounded"),
        "hiddenReplacement": _bool(payload["hiddenReplacement"], "hiddenReplacement"),
        "stopOrFail": stop_or_fail,
        "gapEvidence": gap,
    }


def _ids(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("queuedIds must be a list")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item or item != item.strip() or " " in item:
            raise ValueError("queuedIds must be non-empty tokens")
        if item in items:
            raise ValueError("queuedIds must be unique")
        items.append(item)
    return items


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
        raise ValueError("TC-P023-05 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
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
