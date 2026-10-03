"""TC-P017-07 independent monitoring toggle.

Histogram, focus peaking, film preview, and virtual-depth display may toggle
while the same source sequence is recorded. The clean source and clean master
stay unchanged. Recording a false-color overlay or a preview grade into the
clean master is rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P017-07"
INTERVENTION = (
    "Toggle overlays and viewing transforms repeatedly while recording the same "
    "controlled source sequence."
)
EXPECTED = (
    "Leave clean-source or clean-master content unchanged under its declared "
    "deterministic contract."
)
NEGATIVE = "Recording a false-color overlay or preview grade into a clean master must fail."
MONITORS = (
    "histogram",
    "focus_peaking",
    "film_preview",
    "virtual_depth_display",
)
_PAYLOAD_KEYS = (
    "monitor",
    "sourceSequence",
    "cleanMaster",
    "toggleCount",
    "recordsOverlay",
    "recordsPreviewGrade",
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
    """Keep the clean master. Overlay and preview-grade recording are rejected."""
    data = _payload(payload)
    reasons = [
        f"monitor {data['monitor']} toggled {data['toggleCount']}",
        INTERVENTION,
        EXPECTED,
    ]
    rejected: list[str] = []
    if data["recordsOverlay"]:
        rejected.append("false-color-overlay")
    if data["recordsPreviewGrade"]:
        rejected.append("preview-grade-in-master")
    if rejected:
        reasons.append(NEGATIVE)
        decision = "rejected"
    else:
        decision = "unchanged"
        reasons.append("clean master unchanged under the deterministic contract")
    preserved = [data["sourceSequence"], data["cleanMaster"]]
    if preserved != [data["sourceSequence"], data["cleanMaster"]]:
        raise ValueError("clean source or master changed")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    monitor = payload["monitor"]
    if monitor not in MONITORS:
        raise ValueError("monitor is not a TC-P017-07 repeat")
    source = _text(payload["sourceSequence"], "sourceSequence")
    master = _text(payload["cleanMaster"], "cleanMaster")
    toggles = payload["toggleCount"]
    if type(toggles) is not int or toggles < 1:
        raise ValueError("toggleCount must be a positive int")
    overlay = _bool(payload["recordsOverlay"], "recordsOverlay")
    grade = _bool(payload["recordsPreviewGrade"], "recordsPreviewGrade")
    return {
        "monitor": monitor,
        "sourceSequence": source,
        "cleanMaster": master,
        "toggleCount": toggles,
        "recordsOverlay": overlay,
        "recordsPreviewGrade": grade,
    }


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


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
        raise ValueError("TC-P017-07 must not yield qualified or allowed")
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
