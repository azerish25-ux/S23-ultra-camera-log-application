"""TC-P061-06 source-lineage laundering.

Intervention: Export an SDR or HLG-derived source under a RAW-derived or
native-camera-equivalent label.
Expected: Reject the label even when the final file is ten-bit and visually flat.
Negative: Changing the encoding cannot upgrade the source acquisition category.
"""

from __future__ import annotations


CASE_ID = "TC-P061-06"
INTERVENTION = (
    "Export an SDR or HLG-derived source under a RAW-derived or native-camera-equivalent label."
)
EXPECTED = "Reject the label even when the final file is ten-bit and visually flat."
NEGATIVE = "Changing the encoding cannot upgrade the source acquisition category."
REPEAT = "Repeat through import, recipe selection, export naming, and shared metadata."

_ACQUISITIONS = ("sdr", "hlg-derived", "raw-sensor", "imported-video")
_LABELS = ("RAW-derived", "native-camera-equivalent", "hlg-derived", "sdr", "imported-video")
_STAGES = ("import", "recipe", "export-name", "shared-metadata")
_UPGRADES = {"RAW-derived", "native-camera-equivalent"}
_NON_RAW = {"sdr", "hlg-derived", "imported-video"}
_HONEST = {
    "sdr": "sdr",
    "hlg-derived": "hlg-derived",
    "raw-sensor": "RAW-derived",
    "imported-video": "imported-video",
}
_PAYLOAD_KEYS = (
    "acquisition",
    "exportLabel",
    "containerBits",
    "visuallyFlat",
    "stage",
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
    """Reject acquisition upgrades. Ten-bit and flat appearance do not relabel a source."""
    acquisition, label, bits, flat, stage = _payload(payload)
    preserved = [
        f"acquisition:{acquisition}",
        f"label:{label}",
        f"bits:{bits}",
        f"flat:{str(flat).lower()}",
        f"stage:{stage}",
    ]
    reasons = [EXPECTED, INTERVENTION, f"repeat coverage includes {REPEAT}"]
    questions = [f"lineage stage {stage} kept the acquisition {acquisition}"]
    rejected: list[str] = []
    if acquisition in _NON_RAW and label in _UPGRADES:
        rejected.extend(["lineage-laundering", "encoding-cannot-upgrade"])
        reasons.append(NEGATIVE)
        if bits == 10:
            reasons.append("ten-bit storage did not upgrade the acquisition")
        if flat:
            reasons.append("a visually flat file did not upgrade the acquisition")
        decision = "rejected"
    elif label != _HONEST[acquisition]:
        rejected.append("label-mismatch")
        reasons.append("export label does not match the source acquisition category")
        decision = "rejected"
    elif acquisition == "raw-sensor":
        decision = "withheld"
        reasons.append("honest RAW-derived label is not a physical raw qualification")
        questions.append("host fixture does not prove sensor acquisition")
    else:
        decision = "lineage_kept"
        reasons.append("export label matches the source acquisition and does not upgrade it")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    acquisition = payload["acquisition"]
    if acquisition not in _ACQUISITIONS:
        raise ValueError("acquisition is unsupported")
    label = payload["exportLabel"]
    if label not in _LABELS:
        raise ValueError("exportLabel is unsupported")
    bits = payload["containerBits"]
    if type(bits) is not int or isinstance(bits, bool) or bits not in {8, 10}:
        raise ValueError("containerBits must be 8 or 10")
    flat = payload["visuallyFlat"]
    if type(flat) is not bool:
        raise ValueError("visuallyFlat must be a bool")
    stage = payload["stage"]
    if stage not in _STAGES:
        raise ValueError("stage is unsupported")
    return acquisition, label, bits, flat, stage


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P061-06 must not yield qualified or allowed")
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
