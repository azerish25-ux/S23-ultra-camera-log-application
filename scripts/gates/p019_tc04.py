"""TC-P019-04 preview consumer stalls.

Scopes, depth inference, thumbnails, and a detached display may stall. That
work is dropped while source timing stays intact. A cosmetic consumer that
blocks irreplaceable source capture is rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P019-04"
INTERVENTION = (
    "Block preview analysis or depth consumption while source acquisition remains healthy."
)
EXPECTED = (
    "Drop or reduce stale monitoring work without corrupting source timing or "
    "exhausting capture resources."
)
NEGATIVE = "A cosmetic consumer that blocks irreplaceable source capture must fail."
REPEAT = (
    "Repeat with scopes, depth inference, thumbnail generation, and a detached display surface."
)
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
    "monitoringBacklog",
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
    """Drop stale monitoring. Do not let it block or rewrite source timing."""
    consumer, healthy, blocks, timing, backlog = _payload(payload)
    preserved = [timing]
    reasons = [f"consumer {consumer}", f"monitoring backlog {backlog}", f"source timing {timing}"]
    rejected: list[str] = []
    questions: list[str] = []

    if blocks:
        decision = "rejected"
        rejected.extend(["cosmetic-blocks-source", consumer])
        reasons.append("a cosmetic consumer must not block irreplaceable source capture")
    elif not healthy:
        decision = "withheld"
        questions.append("source acquisition unhealthy")
        reasons.append("source acquisition is not healthy; monitoring is not reduced into a pass")
    else:
        decision = "monitoring_reduced"
        preserved.append("source-healthy")
        reasons.append(f"dropped stale {consumer} work")
        reasons.append("source timing unchanged")
        reasons.append("capture resources not exhausted")

    if timing not in preserved:
        raise ValueError("source timing must be preserved")
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P019-04 must not yield qualified or allowed")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, bool, bool, str, int]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    consumer = payload["consumer"]
    if consumer not in CONSUMERS:
        raise ValueError("consumer is not a P019 monitoring repeat")
    healthy = payload["sourceHealthy"]
    blocks = payload["blocksSourceCapture"]
    if type(healthy) is not bool or type(blocks) is not bool:
        raise ValueError("sourceHealthy and blocksSourceCapture must be bools")
    timing = payload["sourceTiming"]
    if not isinstance(timing, str) or not timing or timing != timing.strip():
        raise ValueError("sourceTiming must be a non-empty string")
    backlog = payload["monitoringBacklog"]
    if type(backlog) is not int or backlog < 0:
        raise ValueError("monitoringBacklog must be a non-negative int")
    return consumer, healthy, blocks, timing, backlog


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
