"""TC-P064-06 source-lineage laundering.

Intervention: Export an SDR or HLG-derived source under a RAW-derived or
native-camera-equivalent label.
Expected: Reject the label even when the final file is ten-bit and visually flat.
Negative: Changing the encoding cannot upgrade the source acquisition category.
"""

from __future__ import annotations


CASE_ID = "TC-P064-06"
INTERVENTION = "Export an SDR or HLG-derived source under a RAW-derived or native-camera-equivalent label."
EXPECTED = "Reject the label even when the final file is ten-bit and visually flat."
NEGATIVE = "Changing the encoding cannot upgrade the source acquisition category."
REPEAT = "Repeat through import, recipe selection, export naming, and shared metadata."

_STAGES = ("import", "recipe", "export-name", "shared-metadata")
_ACQUISITIONS = ("SDR-derived", "HLG-derived", "RAW-derived")
_LABELS = ("RAW-derived", "native-camera-equivalent", "SDR-derived", "HLG-derived", "processed-look")
_DERIVED = {"SDR-derived", "HLG-derived"}
_LAUNDERED = {"RAW-derived", "native-camera-equivalent"}
_RANK = {
    "SDR-derived": 0,
    "HLG-derived": 1,
    "processed-look": 1,
    "RAW-derived": 2,
    "native-camera-equivalent": 3,
}
_PAYLOAD_KEYS = (
    "stage",
    "acquisition",
    "exportLabel",
    "containerBitDepth",
    "visuallyFlat",
    "encodingChanged",
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
    """Reject labels that upgrade SDR or HLG acquisition, including by re-encoding."""
    stage, acquisition, label, depth, flat, encoding_changed = _payload(payload)
    preserved = [
        f"stage:{stage}",
        f"acquisition:{acquisition}",
        f"export-label:{label}",
        f"container-bits:{depth}",
        f"visually-flat:{_flag(flat)}",
        f"encoding-changed:{_flag(encoding_changed)}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [REPEAT, f"stage {stage} kept"]
    rejected: list[str] = []
    if acquisition in _DERIVED and label in _LAUNDERED:
        rejected.append("lineage-laundering")
        reasons.append(EXPECTED)
        if depth == 10 and flat:
            reasons.append("ten-bit visually flat output does not change the acquisition category")
    if label == "native-camera-equivalent":
        rejected.append("native-camera-equivalent-unproven")
        reasons.append("native-camera equivalence is not established by a label")
    upgraded = _RANK[label] > _RANK[acquisition] and label != "processed-look"
    if encoding_changed and upgraded:
        rejected.append("encoding-does-not-upgrade-acquisition")
        reasons.append(NEGATIVE)
    if label != acquisition and label != "processed-look" and "lineage-laundering" not in rejected:
        if label != "native-camera-equivalent":
            rejected.append("label-does-not-match-acquisition")
    if rejected:
        decision = "rejected"
        questions.append("source acquisition category was kept")
    else:
        decision = "withheld"
        reasons.append("label does not upgrade the source acquisition category")
        questions.append("a matching label is not cinema-camera equivalence")
    return _result(decision, reasons, rejected, preserved, questions)


def _flag(value: bool) -> str:
    return "true" if value else "false"


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    stage = payload["stage"]
    if stage not in _STAGES:
        raise ValueError("stage is unsupported")
    acquisition = payload["acquisition"]
    if acquisition not in _ACQUISITIONS:
        raise ValueError("acquisition is unsupported")
    label = payload["exportLabel"]
    if label not in _LABELS:
        raise ValueError("exportLabel is unsupported")
    depth = payload["containerBitDepth"]
    if type(depth) is not int or depth not in {8, 10}:
        raise ValueError("containerBitDepth must be 8 or 10")
    flat = payload["visuallyFlat"]
    changed = payload["encodingChanged"]
    if type(flat) is not bool:
        raise ValueError("visuallyFlat must be a bool")
    if type(changed) is not bool:
        raise ValueError("encodingChanged must be a bool")
    return stage, acquisition, label, depth, flat, changed


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P064-06 must not yield qualified or allowed")
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
