"""TC-P023-04 preview consumer stalls.

Scopes, depth inference, thumbnails, and a detached display surface are
cosmetic consumers. They may be dropped or reduced while source acquisition
is healthy. A consumer that blocks irreplaceable source capture fails.
"""

from __future__ import annotations

CASE_ID = "TC-P023-04"
INTERVENTION = (
    "Block preview analysis or depth consumption while source acquisition remains healthy."
)
EXPECTED = (
    "Drop or reduce stale monitoring work without corrupting source timing "
    "or exhausting capture resources."
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
    "consumerBlocksSource",
    "sourceTimingCorrupted",
    "resourcesExhausted",
    "staleMonitoringDropped",
    "sourceIdentity",
    "framesKept",
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
    fields = _payload(payload)
    reasons = [f"consumer {fields['consumer']}", INTERVENTION]
    rejected: list[str] = []
    if fields["consumerBlocksSource"]:
        rejected.append("cosmetic-blocks-source")
    if fields["sourceTimingCorrupted"]:
        rejected.append("source-timing-corrupted")
    if fields["resourcesExhausted"]:
        rejected.append("capture-resources-exhausted")
    if not fields["staleMonitoringDropped"]:
        rejected.append("stale-monitoring-kept")

    if rejected:
        decision = "rejected"
        reasons.append(NEGATIVE)
        reasons.append("preview consumer must not block or corrupt source capture")
    else:
        decision = "monitoring_reduced"
        reasons.append(EXPECTED)
        reasons.append("stale monitoring dropped; source timing and frames kept")

    preserved = [fields["sourceIdentity"], f"frames:{fields['framesKept']}"]
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    consumer = payload["consumer"]
    if consumer not in CONSUMERS:
        raise ValueError("consumer is not a TC-P023-04 repeat")
    if _bool(payload["sourceHealthy"], "sourceHealthy") is not True:
        raise ValueError("source acquisition must remain healthy for this intervention")
    frames = payload["framesKept"]
    if type(frames) is not int or frames < 0:
        raise ValueError("framesKept must be a non-negative int")
    identity = payload["sourceIdentity"]
    if not isinstance(identity, str) or not identity or identity != identity.strip() or " " in identity:
        raise ValueError("sourceIdentity must be a non-empty token")
    return {
        "consumer": consumer,
        "sourceHealthy": True,
        "consumerBlocksSource": _bool(payload["consumerBlocksSource"], "consumerBlocksSource"),
        "sourceTimingCorrupted": _bool(payload["sourceTimingCorrupted"], "sourceTimingCorrupted"),
        "resourcesExhausted": _bool(payload["resourcesExhausted"], "resourcesExhausted"),
        "staleMonitoringDropped": _bool(payload["staleMonitoringDropped"], "staleMonitoringDropped"),
        "sourceIdentity": identity,
        "framesKept": frames,
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
        raise ValueError("TC-P023-04 must not yield qualified or allowed")
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
