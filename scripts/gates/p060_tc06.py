"""TC-P060-06 source-lineage laundering.

Intervention: Export an SDR or HLG-derived source under a RAW-derived or
native-camera-equivalent label.
Expected: Reject the label even when the final file is ten-bit and visually flat.
Negative: Changing the encoding cannot upgrade the source acquisition category.
"""

from __future__ import annotations


CASE_ID = "TC-P060-06"
INTERVENTION = (
    "Export an SDR or HLG-derived source under a RAW-derived or native-camera-equivalent label."
)
EXPECTED = "Reject the label even when the final file is ten-bit and visually flat."
NEGATIVE = "Changing the encoding cannot upgrade the source acquisition category."
REPEAT = "Repeat through import, recipe selection, export naming, and shared metadata."

_STAGES = ("import", "recipe", "export-name", "shared-metadata")
_ACQUISITIONS = ("sdr", "hlg", "raw", "native-camera")
_LABELS = ("raw-derived", "native-camera-equivalent", "sdr", "hlg", "ten-bit-flat")
_DEPTHS = ("8", "10")
_LAUNDER = {
    ("sdr", "raw-derived"),
    ("sdr", "native-camera-equivalent"),
    ("hlg", "raw-derived"),
    ("hlg", "native-camera-equivalent"),
}
_PAYLOAD_KEYS = (
    "stage",
    "acquisition",
    "exportLabel",
    "containerBitDepth",
    "visuallyFlat",
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
    """Reject a RAW or native-camera label placed on an SDR or HLG source."""
    stage, acquisition, label, depth, flat = _payload(payload)
    preserved = [
        f"stage:{stage}",
        f"acquisition:{acquisition}",
        f"label:{label}",
        f"depth:{depth}",
        f"visually-flat:{'yes' if flat else 'no'}",
    ]
    reasons = [EXPECTED, INTERVENTION, f"stage {stage} keeps acquisition {acquisition}"]
    questions = [f"repeat coverage includes {REPEAT}"]
    rejected: list[str] = []
    if (acquisition, label) in _LAUNDER:
        rejected.append("laundered-source-lineage")
        reasons.append(NEGATIVE)
        if depth == "10":
            reasons.append("ten-bit storage did not upgrade the source acquisition category")
        if flat:
            reasons.append("a visually flat file did not upgrade the source acquisition category")
        decision = "rejected"
    else:
        decision = "withheld"
        reasons.append(NEGATIVE)
        reasons.append("the export label was not accepted as a change of acquisition category")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    stage = payload["stage"]
    acquisition = payload["acquisition"]
    label = payload["exportLabel"]
    depth = payload["containerBitDepth"]
    flat = payload["visuallyFlat"]
    if stage not in _STAGES:
        raise ValueError("stage is unsupported")
    if acquisition not in _ACQUISITIONS:
        raise ValueError("acquisition is unsupported")
    if label not in _LABELS:
        raise ValueError("exportLabel is unsupported")
    if depth not in _DEPTHS:
        raise ValueError("containerBitDepth must be 8 or 10")
    if type(flat) is not bool:
        raise ValueError("visuallyFlat must be a bool")
    return stage, acquisition, label, depth, flat


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P060-06 must not yield qualified or allowed")
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
