"""TC-P020-04 preview consumer stalls.

Preview analysis or depth consumption may block while source acquisition stays
healthy. Stale monitoring work is dropped. Source timing stays intact. A
cosmetic consumer that blocks irreplaceable source capture is rejected.

Baseline white-balance inventory stays in preservedResults. This host module
does not touch a device.
"""

from __future__ import annotations

CASE_ID = "TC-P020-04"
INTERVENTION = (
    "Block preview analysis or depth consumption while source acquisition remains healthy."
)
EXPECTED = (
    "Drop or reduce stale monitoring work without corrupting source timing or "
    "exhausting capture resources."
)
NEGATIVE = "A cosmetic consumer that blocks irreplaceable source capture must fail."
REPEATS = (
    "scopes",
    "depth_inference",
    "thumbnail_generation",
    "detached_display_surface",
)
WB_INVENTORY = (
    "hardware.namespace:hardware.white_balance",
    "hardware.preset:daylight",
    "hardware.locked:true",
    "hardware.gains:1.42,1.00,1.78",
    "hardware.kelvin:unavailable",
    "scene.namespace:scene.calibration",
    "scene.profile:raw-neutral-v1",
    "scene.version:1",
    "scene.neutral:1.00,1.00,1.00",
    "creative.namespace:creative.preview",
    "creative.slider:warm",
    "creative.recipe:preview-warm-v1",
    "creative.tint:12",
    "source.metadata:unchanged",
)
_PAYLOAD_KEYS = {
    "consumer",
    "sourceHealthy",
    "blocksSourceCapture",
    "sourceTiming",
    "monitoringDropped",
}
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Drop stale monitoring. Do not let a cosmetic consumer stop the source."""
    consumer, healthy, blocks, timing, dropped = _payload(payload)
    preserved = list(WB_INVENTORY)
    preserved.append("source.timing:" + timing)
    reasons = [EXPECTED, "repeat consumer " + consumer]
    rejected: list[str] = []
    questions: list[str] = []

    if blocks:
        decision = "rejected"
        rejected.append("cosmetic-consumer-blocks-source")
        reasons.append(NEGATIVE)
        reasons.append(consumer + " must not block irreplaceable source capture")
    elif not healthy:
        decision = "withheld"
        questions.append("source acquisition is not healthy")
        reasons.append("source acquisition is not healthy; monitoring policy withheld")
    elif not dropped:
        decision = "rejected"
        rejected.append("stale-monitoring-retained")
        reasons.append("stale monitoring work was not dropped or reduced")
    else:
        decision = "monitoring_reduced"
        reasons.append("stale monitoring work dropped")
        reasons.append("source timing unchanged")

    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P020-04 must not decide qualified or allowed")
    if "source.timing:" + timing not in preserved:
        raise ValueError("source timing must be preserved")
    for item in WB_INVENTORY:
        if item not in preserved:
            raise ValueError("white-balance inventory must be preserved")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != _PAYLOAD_KEYS:
        raise ValueError("invalid payload keys")
    consumer = payload["consumer"]
    if consumer not in REPEATS:
        raise ValueError("consumer is not a TC-P020-04 repeat")
    return (
        consumer,
        _bool(payload["sourceHealthy"], "sourceHealthy"),
        _bool(payload["blocksSourceCapture"], "blocksSourceCapture"),
        _text(payload["sourceTiming"], "sourceTiming"),
        _bool(payload["monitoringDropped"], "monitoringDropped"),
    )


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(name + " must be a bool")
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(name + " must be a non-empty string")
    return value


def _tokens(value: object, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(name + " must be a list")
    seen: set[str] = set()
    tokens: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item or item != item.strip():
            raise ValueError(name + " entries must be non-empty strings")
        if item in seen:
            raise ValueError(name + " entries must be unique")
        seen.add(item)
        tokens.append(item)
    return tokens


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("decision must not be qualified or allowed")
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

