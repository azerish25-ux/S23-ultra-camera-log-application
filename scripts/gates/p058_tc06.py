"""TC-P058-06 source-lineage laundering.

Intervention: Export an SDR or HLG-derived source under a RAW-derived or
native-camera-equivalent label.
Expected: Reject the label even when the final file is ten-bit and visually flat.
Negative: Changing the encoding cannot upgrade the source acquisition category.
"""

from __future__ import annotations

CASE_ID = "TC-P058-06"
INTERVENTION = "Export an SDR or HLG-derived source under a RAW-derived or native-camera-equivalent label."
EXPECTED = "Reject the label even when the final file is ten-bit and visually flat."
NEGATIVE = "Changing the encoding cannot upgrade the source acquisition category."

_ACQUISITIONS = ("sdr", "hlg", "raw")
_LABELS = ("sdr", "hlg", "raw-derived", "native-camera-equivalent")
_STAGES = ("import", "recipe", "export-name", "shared-metadata")
_UPGRADE = {"raw-derived", "native-camera-equivalent"}
_PAYLOAD_KEYS = (
    "acquisition",
    "exportLabel",
    "tenBit",
    "visuallyFlat",
    "stage",
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
    """Reject a label that upgrades SDR or HLG into a RAW or camera-equivalent source."""
    acquisition, label, ten_bit, flat, stage, encoding_changed = _payload(payload)
    preserved = [
        f"acquisition:{acquisition}",
        f"label:{label}",
        f"stage:{stage}",
        "ten-bit:" + ("true" if ten_bit else "false"),
        "visually-flat:" + ("true" if flat else "false"),
        "encoding-changed:" + ("true" if encoding_changed else "false"),
    ]
    reasons = [EXPECTED, INTERVENTION, f"stage {stage} kept the acquisition category"]
    rejected: list[str] = []
    questions = [f"lineage at {stage} is not cinema-camera equivalence"]
    upgrade = acquisition in {"sdr", "hlg"} and label in _UPGRADE
    native = label == "native-camera-equivalent"
    if upgrade or native:
        decision = "rejected"
        rejected.append("laundered-lineage" if upgrade else "native-equivalent-unproven")
        if ten_bit:
            rejected.append("ten-bit-file")
        if flat:
            rejected.append("visually-flat")
        reasons.append("ten-bit storage and a flat picture do not change acquisition")
        if encoding_changed:
            rejected.append("encoding-does-not-upgrade-acquisition")
            reasons.append(NEGATIVE)
    else:
        decision = "lineage_retained"
        reasons.append("acquisition category was retained")
        questions.append("retained lineage is not a qualified source")
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
    stage = payload["stage"]
    if stage not in _STAGES:
        raise ValueError("stage is unsupported")
    ten_bit = payload["tenBit"]
    flat = payload["visuallyFlat"]
    encoding_changed = payload["encodingChanged"]
    for name, value in (
        ("tenBit", ten_bit),
        ("visuallyFlat", flat),
        ("encodingChanged", encoding_changed),
    ):
        if type(value) is not bool:
            raise ValueError(name + " must be a bool")
    return acquisition, label, ten_bit, flat, stage, encoding_changed


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P058-06 must not yield qualified or allowed")
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
