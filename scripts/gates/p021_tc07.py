"""TC-P021-07 independent monitoring toggle.

Overlays and viewing transforms may toggle while the same source sequence is
recorded. The clean source and clean master stay unchanged when the master
hash matches the source hash. Recording a false-color overlay or preview
grade into the clean master is rejected.

Baseline focus inventory stays in preservedResults. This host module does not
touch a device.
"""

from __future__ import annotations

CASE_ID = "TC-P021-07"
INTERVENTION = (
    "Toggle overlays and viewing transforms repeatedly while recording the same "
    "controlled source sequence."
)
EXPECTED = (
    "Leave clean-source or clean-master content unchanged under its declared "
    "deterministic contract."
)
NEGATIVE = "Recording a false-color overlay or preview grade into a clean master must fail."
REPEATS = (
    "histogram",
    "focus_peaking",
    "film_preview",
    "virtual_depth_display",
)
FOCUS_INVENTORY = (
    "physical.namespace:physical.lens",
    "physical.unit:metres",
    "physical.subject:nearby_foreground",
    "physical.distance:unknown",
    "virtual.namespace:virtual.development",
    "virtual.unit:relative_depth",
    "virtual.subject:face",
    "virtual.relativeDepth:0.62",
)
_PAYLOAD_KEYS = {
    "aid",
    "toggles",
    "sourceHash",
    "masterHash",
    "overlayRecordedIntoMaster",
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
    """Keep the clean master free of monitoring overlays."""
    aid, toggles, source_hash, master_hash, overlay = _payload(payload)
    preserved = list(FOCUS_INVENTORY)
    preserved.append("source.hash:" + source_hash)
    reasons = [EXPECTED, "repeat aid " + aid, "toggles " + str(toggles)]
    rejected: list[str] = []

    if overlay:
        decision = "rejected"
        rejected.append("overlay-in-master:" + aid)
        reasons.append(NEGATIVE)
        reasons.append(aid + " was not written into the clean master")
    elif master_hash != source_hash:
        decision = "rejected"
        rejected.append("clean-master-changed")
        reasons.append("clean master hash differs from the controlled source")
    else:
        decision = "unchanged"
        preserved.append("master.hash:" + master_hash)
        reasons.append("clean master unchanged under the deterministic contract")

    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P021-07 must not decide qualified or allowed")
    if "source.hash:" + source_hash not in preserved:
        raise ValueError("clean source hash must be preserved")
    if overlay and "master.hash:" + master_hash in preserved:
        raise ValueError("contaminated master must not be kept as the clean master")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != _PAYLOAD_KEYS:
        raise ValueError("invalid payload keys")
    aid = payload["aid"]
    if aid not in REPEATS:
        raise ValueError("aid is not a TC-P021-07 repeat")
    toggles = payload["toggles"]
    if type(toggles) is not int or toggles < 1:
        raise ValueError("toggles must be a positive int")
    return (
        aid,
        toggles,
        _text(payload["sourceHash"], "sourceHash"),
        _text(payload["masterHash"], "masterHash"),
        _bool(payload["overlayRecordedIntoMaster"], "overlayRecordedIntoMaster"),
    )


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(name + " must be a non-empty string")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(name + " must be a bool")
    return value


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
