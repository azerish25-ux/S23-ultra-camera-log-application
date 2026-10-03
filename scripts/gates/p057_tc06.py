"""TC-P057-06 source-lineage laundering.

Intervention: Export an SDR or HLG-derived source under a RAW-derived or
native-camera-equivalent label.
Expected: Reject the label even when the final file is ten-bit and visually flat.
Negative: Changing the encoding cannot upgrade the source acquisition category.
"""

from __future__ import annotations


CASE_ID = "TC-P057-06"
INTERVENTION = (
    "Export an SDR or HLG-derived source under a RAW-derived or native-camera-equivalent label."
)
EXPECTED = "Reject the label even when the final file is ten-bit and visually flat."
NEGATIVE = "Changing the encoding cannot upgrade the source acquisition category."

_STAGES = ("import", "recipe", "export-name", "shared-metadata")
_ACQUISITIONS = ("sdr", "hlg", "raw")
_LABELS = ("raw-derived", "native-camera-equivalent", "sdr", "hlg")
_UPGRADES = {"raw-derived", "native-camera-equivalent"}
_DERIVED = {"sdr", "hlg"}
_PAYLOAD_KEYS = ("stage", "acquisition", "label", "containerBits", "visuallyFlat")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "withheld")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Reject an acquisition upgrade hidden by a new label or container."""
    stage, acquisition, label, bits, flat = _payload(payload)
    preserved = [
        f"stage:{stage}",
        f"acquisition:{acquisition}",
        f"label:{label}",
        f"container-bits:{bits}",
        f"visually-flat:{str(flat).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = ["label text is not a measured acquisition category"]
    if acquisition in _DERIVED and label in _UPGRADES:
        reasons.append(NEGATIVE)
        reasons.append(f"{stage} kept the {acquisition} acquisition")
        if bits == 10:
            reasons.append("ten-bit storage did not upgrade the source")
        if flat:
            reasons.append("a visually flat image did not upgrade the source")
        return _result(
            "rejected",
            reasons,
            ["lineage-upgrade", f"stage:{stage}"],
            preserved,
            questions,
        )
    reasons.append("no upgrade was claimed; the acquisition category stays unchanged")
    questions.append("withheld is not physical S23 or cinema-camera equivalence")
    return _result("withheld", reasons, [], preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, int, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    stage = payload["stage"]
    acquisition = payload["acquisition"]
    label = payload["label"]
    if stage not in _STAGES:
        raise ValueError("stage is unknown")
    if acquisition not in _ACQUISITIONS:
        raise ValueError("acquisition is unknown")
    if label not in _LABELS:
        raise ValueError("label is unknown")
    bits = payload["containerBits"]
    if type(bits) is not int or bits not in {8, 10}:
        raise ValueError("containerBits must be 8 or 10")
    flat = payload["visuallyFlat"]
    if type(flat) is not bool:
        raise ValueError("visuallyFlat must be a bool")
    return stage, acquisition, label, bits, flat


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("decision cannot be qualified or allowed")
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
