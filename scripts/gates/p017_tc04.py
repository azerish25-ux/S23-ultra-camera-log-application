"""TC-P017-04 preview consumer stalls.

Scopes, depth, thumbnails, and a detached display are monitoring consumers.
If they stall while source acquisition is healthy, monitoring is dropped or
reduced. Source timing stays as given. A cosmetic consumer that blocks
irreplaceable source capture is rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P017-04"
INTERVENTION = (
    "Block preview analysis or depth consumption while source acquisition remains healthy."
)
EXPECTED = (
    "Drop or reduce stale monitoring work without corrupting source timing or "
    "exhausting capture resources."
)
NEGATIVE = "A cosmetic consumer that blocks irreplaceable source capture must fail."
CONSUMERS = (
    "scopes",
    "depth_inference",
    "thumbnail_generation",
    "detached_display_surface",
)
_PAYLOAD_KEYS = (
    "consumer",
    "sourceHealthy",
    "blocksSourceCapture",
    "sourceTiming",
    "resourceCount",
    "resourceBound",
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
    """Drop stalled monitoring. Blocking the source is rejected."""
    data = _payload(payload)
    reasons = [
        f"consumer {data['consumer']}",
        INTERVENTION,
        EXPECTED,
    ]
    rejected: list[str] = []
    open_questions: list[str] = []
    if data["blocksSourceCapture"]:
        rejected.append("cosmetic-blocks-source")
        reasons.append(NEGATIVE)
        decision = "rejected"
    elif not data["sourceHealthy"]:
        decision = "withheld"
        reasons.append("source acquisition is not healthy")
        open_questions.append("source acquisition is not healthy")
    else:
        decision = "monitoring_dropped"
        reasons.append("stale monitoring work dropped")
        reasons.append("source timing unchanged")
        if data["resourceCount"] > data["resourceBound"]:
            reasons.append("monitoring reduced instead of exhausting capture resources")
        else:
            reasons.append("capture resources remain within bound")
    preserved = [data["sourceTiming"]]
    if data["sourceTiming"] not in preserved:
        raise ValueError("source timing must be preserved")
    return _result(decision, reasons, rejected, preserved, open_questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    consumer = payload["consumer"]
    if consumer not in CONSUMERS:
        raise ValueError("consumer is not a TC-P017-04 repeat")
    healthy = _bool(payload["sourceHealthy"], "sourceHealthy")
    blocks = _bool(payload["blocksSourceCapture"], "blocksSourceCapture")
    timing = payload["sourceTiming"]
    if not isinstance(timing, str) or not timing or timing != timing.strip():
        raise ValueError("sourceTiming must be a non-empty string")
    count = payload["resourceCount"]
    bound = payload["resourceBound"]
    if type(count) is not int or count < 0:
        raise ValueError("resourceCount must be a non-negative int")
    if type(bound) is not int or bound < 1:
        raise ValueError("resourceBound must be a positive int")
    return {
        "consumer": consumer,
        "sourceHealthy": healthy,
        "blocksSourceCapture": blocks,
        "sourceTiming": timing,
        "resourceCount": count,
        "resourceBound": bound,
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
        raise ValueError("TC-P017-04 must not yield qualified or allowed")
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
