"""TC-P022-04 preview consumer stalls.

Block preview analysis or depth consumption while source acquisition remains
healthy. Drop or reduce stale monitoring work without corrupting source timing
or exhausting capture resources. A cosmetic consumer that blocks irreplaceable
source capture must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P022-04"
INTERVENTION = "Block preview analysis or depth consumption while source acquisition remains healthy."
EXPECTED = (
    "Drop or reduce stale monitoring work without corrupting source timing "
    "or exhausting capture resources."
)
NEGATIVE = "A cosmetic consumer that blocks irreplaceable source capture must fail."
CONSUMERS = ("scopes", "depth_inference", "thumbnail", "detached_display")
_PAYLOAD_KEYS = (
    "consumer",
    "sourceHealthy",
    "dropsStaleMonitoring",
    "sourceTimingIntact",
    "resourcesExhausted",
    "blocksSourceCapture",
    "sourceTimestamps",
    "cleanMasterHash",
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
    """Reduce stale monitoring. Do not let a cosmetic consumer block the source."""
    data = _payload(payload)
    reasons = [f"consumer {data['consumer']}"]
    rejected: list[str] = []
    questions: list[str] = []
    if data["blocksSourceCapture"]:
        rejected.append("cosmetic-consumer-blocks-source")
        reasons.append("a cosmetic consumer must not block irreplaceable source capture")
    if not data["sourceTimingIntact"]:
        rejected.append("source-timing-corrupted")
        reasons.append("source timing must stay intact")
    if data["resourcesExhausted"]:
        rejected.append("capture-resources-exhausted")
        reasons.append("capture resources must not be exhausted by monitoring")
    if not data["sourceHealthy"]:
        questions.append("source acquisition is not healthy")
    if rejected:
        decision = "rejected"
    elif not data["sourceHealthy"]:
        decision = "withheld"
        reasons.append("monitoring reduction is not claimed while the source is unhealthy")
    elif not data["dropsStaleMonitoring"]:
        decision = "rejected"
        rejected.append("stale-monitoring-retained")
        reasons.append("stale monitoring work must be dropped or reduced")
    else:
        decision = "monitoring_reduced"
        reasons.append("stale monitoring dropped without changing source timestamps")
    preserved = list(data["sourceTimestamps"]) + [data["cleanMasterHash"]]
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    consumer = payload["consumer"]
    if consumer not in CONSUMERS:
        raise ValueError("consumer is not a declared repeat")
    timestamps = _tokens(payload["sourceTimestamps"], "sourceTimestamps")
    if not timestamps:
        raise ValueError("sourceTimestamps must keep at least one source time")
    return {
        "consumer": consumer,
        "sourceHealthy": _bool(payload["sourceHealthy"], "sourceHealthy"),
        "dropsStaleMonitoring": _bool(payload["dropsStaleMonitoring"], "dropsStaleMonitoring"),
        "sourceTimingIntact": _bool(payload["sourceTimingIntact"], "sourceTimingIntact"),
        "resourcesExhausted": _bool(payload["resourcesExhausted"], "resourcesExhausted"),
        "blocksSourceCapture": _bool(payload["blocksSourceCapture"], "blocksSourceCapture"),
        "sourceTimestamps": timestamps,
        "cleanMasterHash": _token(payload["cleanMasterHash"], "cleanMasterHash"),
    }


def _token(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _tokens(value: object, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return [_token(item, name) for item in value]


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P022-04 must not yield qualified or allowed")
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
