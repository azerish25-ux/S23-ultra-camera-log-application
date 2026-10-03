"""TC-P022-07 independent monitoring toggle.

Toggle overlays and viewing transforms repeatedly while recording the same
controlled source sequence. Leave clean-source or clean-master content
unchanged under its declared deterministic contract. Recording a false-color
overlay or preview grade into a clean master must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P022-07"
INTERVENTION = (
    "Toggle overlays and viewing transforms repeatedly while recording the same "
    "controlled source sequence."
)
EXPECTED = "Leave clean-source or clean-master content unchanged under its declared deterministic contract."
NEGATIVE = "Recording a false-color overlay or preview grade into a clean master must fail."
AIDS = ("histogram", "focus_peaking", "film_preview", "virtual_depth", "false_color")
_PAYLOAD_KEYS = (
    "aid",
    "enabled",
    "sourceHash",
    "cleanMasterHash",
    "previewHash",
    "overlayInMaster",
    "previewGradeInMaster",
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
    """Keep the clean master stable while an aid toggles on the preview."""
    data = _payload(payload)
    reasons = [f"aid {data['aid']}", "enabled" if data["enabled"] else "disabled"]
    rejected: list[str] = []
    if data["overlayInMaster"]:
        rejected.append("overlay-in-clean-master")
        reasons.append("a false-color overlay must not be recorded into the clean master")
    if data["previewGradeInMaster"]:
        rejected.append("preview-grade-in-clean-master")
        reasons.append("a preview grade must not be recorded into the clean master")
    if data["cleanMasterHash"] != data["sourceHash"]:
        rejected.append("clean-master-drift")
        reasons.append("clean master hash diverged from the source hash")
    if data["enabled"] and data["previewHash"] == data["sourceHash"] and not rejected:
        rejected.append("monitoring-branch-missing")
        reasons.append("an enabled aid must change the preview branch only")
    if rejected:
        decision = "rejected"
    else:
        decision = "unchanged"
        reasons.append("clean master unchanged under the monitoring toggle")
        if data["enabled"]:
            reasons.append("overlay appears only in monitoring")
    preserved = [data["sourceHash"], data["cleanMasterHash"]]
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    aid = payload["aid"]
    if aid not in AIDS:
        raise ValueError("aid is not a declared repeat")
    return {
        "aid": aid,
        "enabled": _bool(payload["enabled"], "enabled"),
        "sourceHash": _token(payload["sourceHash"], "sourceHash"),
        "cleanMasterHash": _token(payload["cleanMasterHash"], "cleanMasterHash"),
        "previewHash": _token(payload["previewHash"], "previewHash"),
        "overlayInMaster": _bool(payload["overlayInMaster"], "overlayInMaster"),
        "previewGradeInMaster": _bool(payload["previewGradeInMaster"], "previewGradeInMaster"),
    }


def _token(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P022-07 must not yield qualified or allowed")
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
