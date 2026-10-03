"""TC-P024-07 independent monitoring toggle.

Histogram, focus peaking, film preview, and virtual-depth display may toggle
while the same controlled source is recorded. Clean-source and clean-master
digests stay unchanged. A false-color overlay or preview grade in the clean
master fails.
"""

from __future__ import annotations

CASE_ID = "TC-P024-07"
INTERVENTION = (
    "Toggle overlays and viewing transforms repeatedly while recording the same "
    "controlled source sequence."
)
EXPECTED = (
    "Leave clean-source or clean-master content unchanged under its declared "
    "deterministic contract."
)
NEGATIVE = "Recording a false-color overlay or preview grade into a clean master must fail."
OVERLAYS = (
    "histogram",
    "focus_peaking",
    "film_preview",
    "virtual_depth_display",
)
CONTRACTS = ("clean_source", "clean_master")
_PAYLOAD_KEYS = (
    "overlay",
    "toggleCount",
    "contract",
    "cleanDigest",
    "recordedDigest",
    "overlayRecordedIntoMaster",
    "previewGradeRecorded",
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
    """Keep the clean digest. Reject overlay or preview grade baked into the master."""
    fields = _payload(payload)
    reasons = [
        f"overlay {fields['overlay']} toggled {fields['toggleCount']} contract {fields['contract']}",
        INTERVENTION,
    ]
    rejected: list[str] = []
    if fields["overlayRecordedIntoMaster"]:
        rejected.append("overlay-recorded-into-clean-master")
    if fields["previewGradeRecorded"]:
        rejected.append("preview-grade-in-clean-master")
    if fields["cleanDigest"] != fields["recordedDigest"]:
        rejected.append("clean-content-changed")

    if rejected:
        decision = "rejected"
        reasons.append(NEGATIVE)
        reasons.append("clean contract content must stay unchanged")
    else:
        decision = "unchanged"
        reasons.append(EXPECTED)
        reasons.append("clean digest matches the recorded digest")

    preserved = [
        f"clean:{fields['cleanDigest']}",
        f"recorded:{fields['recordedDigest']}",
        fields["overlay"],
    ]
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    overlay = payload["overlay"]
    if overlay not in OVERLAYS:
        raise ValueError("overlay is not a TC-P024-07 repeat")
    toggles = payload["toggleCount"]
    if type(toggles) is not int or toggles < 2:
        raise ValueError("toggleCount must be an int of at least 2")
    contract = payload["contract"]
    if contract not in CONTRACTS:
        raise ValueError("contract must be clean_source or clean_master")
    return {
        "overlay": overlay,
        "toggleCount": toggles,
        "contract": contract,
        "cleanDigest": _digest(payload["cleanDigest"], "cleanDigest"),
        "recordedDigest": _digest(payload["recordedDigest"], "recordedDigest"),
        "overlayRecordedIntoMaster": _bool(
            payload["overlayRecordedIntoMaster"], "overlayRecordedIntoMaster"
        ),
        "previewGradeRecorded": _bool(payload["previewGradeRecorded"], "previewGradeRecorded"),
    }


def _digest(value: object, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{name} must be 64 hex characters")
    if any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{name} must be lowercase hex")
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
        raise ValueError("TC-P024-07 must not yield qualified or allowed")
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
