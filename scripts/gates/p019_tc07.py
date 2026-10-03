"""TC-P019-07 independent monitoring toggle.

Histogram, focus peaking, film preview, and virtual-depth display may change
while a controlled source is recorded. The clean-master hash must stay the
same. Writing a false-color overlay or a preview grade into that master is
rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P019-07"
INTERVENTION = (
    "Toggle overlays and viewing transforms repeatedly while recording the same "
    "controlled source sequence."
)
EXPECTED = (
    "Leave clean-source or clean-master content unchanged under its declared "
    "deterministic contract."
)
NEGATIVE = "Recording a false-color overlay or preview grade into a clean master must fail."
REPEAT = "Repeat with histogram, focus peaking, film preview, and virtual-depth display."
AIDS = (
    "histogram",
    "focus_peaking",
    "film_preview",
    "virtual_depth_display",
)
_PAYLOAD_KEYS = (
    "aid",
    "enabled",
    "cleanMasterHash",
    "recordedHash",
    "overlayRecordedIntoMaster",
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
    """Compare hashes. A monitoring aid must not alter the clean master."""
    aid, enabled, clean_hash, recorded_hash, overlay = _payload(payload)
    preserved = ["clean:" + clean_hash]
    reasons = [
        f"aid {aid}",
        "enabled" if enabled else "disabled",
        "clean " + clean_hash,
    ]
    rejected: list[str] = []
    contaminated = overlay or recorded_hash != clean_hash
    if contaminated:
        decision = "rejected"
        rejected.extend(["overlay-in-clean-master", aid])
        reasons.append("false-color overlay or preview grade must not enter the clean master")
        if recorded_hash != clean_hash:
            reasons.append("recorded hash disagrees with the clean master")
    else:
        decision = "clean_unchanged"
        reasons.append("clean-master content unchanged under the deterministic contract")

    if "clean:" + clean_hash not in preserved:
        raise ValueError("clean master must be preserved")
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P019-07 must not yield qualified or allowed")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> tuple[str, bool, str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    aid = payload["aid"]
    if aid not in AIDS:
        raise ValueError("aid is not a P019 monitoring repeat")
    enabled = payload["enabled"]
    overlay = payload["overlayRecordedIntoMaster"]
    if type(enabled) is not bool or type(overlay) is not bool:
        raise ValueError("enabled and overlayRecordedIntoMaster must be bools")
    clean_hash = _hash(payload["cleanMasterHash"], "cleanMasterHash")
    recorded_hash = _hash(payload["recordedHash"], "recordedHash")
    return aid, enabled, clean_hash, recorded_hash, overlay


def _hash(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


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
