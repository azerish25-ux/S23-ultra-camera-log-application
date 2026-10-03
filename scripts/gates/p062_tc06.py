"""TC-P062-06 source-lineage laundering.

Intervention: Export an SDR or HLG-derived source under a RAW-derived or
native-camera-equivalent label.
Expected: Reject the label even when the final file is ten-bit and visually flat.
Negative: Changing the encoding cannot upgrade the source acquisition category.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P062-06"
INTERVENTION = "Export an SDR or HLG-derived source under a RAW-derived or native-camera-equivalent label."
EXPECTED = "Reject the label even when the final file is ten-bit and visually flat."
NEGATIVE = "Changing the encoding cannot upgrade the source acquisition category."
REPEAT = "Repeat through import, recipe selection, export naming, and shared metadata."

_STAGES = ("import", "recipe", "export-name", "shared-metadata")
_ACQUISITIONS = ("sdr", "hlg", "raw")
_CLAIMS = ("sdr-derived", "hlg-derived", "raw-derived", "native-camera-equivalent")
_RANK = {
    "sdr": 0,
    "hlg": 1,
    "raw": 2,
    "sdr-derived": 0,
    "hlg-derived": 1,
    "raw-derived": 2,
    "native-camera-equivalent": 3,
}
_PAYLOAD_KEYS = (
    "sampleId",
    "stage",
    "acquisition",
    "claimedLabel",
    "encodingChanged",
    "containerBits",
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
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")


def evaluate(payload: dict) -> dict:
    """Reject labels that upgrade SDR, HLG, or encoding into a higher source."""
    sample, stage, acquisition, claimed, changed, bits, flat = _payload(payload)
    preserved = [
        sample,
        f"stage:{stage}",
        f"acquisition:{acquisition}",
        f"claimed:{claimed}",
        f"encoding-changed:{'yes' if changed else 'no'}",
        f"container-bits:{bits}",
        f"visually-flat:{'yes' if flat else 'no'}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = [REPEAT, "host case does not establish cinema-camera equivalence"]
    laundered = acquisition in {"sdr", "hlg"} and claimed in {"raw-derived", "native-camera-equivalent"}
    if laundered:
        rejected.append("lineage-laundering")
        reasons.append(
            f"{acquisition} at {stage} stays {acquisition}; {bits}-bit and visually flat do not make it {claimed}"
        )
    if claimed == "native-camera-equivalent":
        rejected.append("native-camera-equivalence")
        reasons.append("native-camera-equivalent is not granted by this host record")
    if changed and _RANK[claimed] > _RANK[acquisition]:
        rejected.append("encoding-cannot-upgrade")
        reasons.append(NEGATIVE)
    if rejected:
        decision = "rejected"
    else:
        decision = "lineage_recorded"
        reasons.append(f"{claimed} matches acquisition {acquisition} and was not upgraded")
        reasons.append("a matching label is not physical source qualification")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    sample = payload["sampleId"]
    if not isinstance(sample, str) or _TOKEN.fullmatch(sample) is None:
        raise ValueError("sampleId must be a token")
    stage = payload["stage"]
    if stage not in _STAGES:
        raise ValueError("stage is unsupported")
    acquisition = payload["acquisition"]
    if acquisition not in _ACQUISITIONS:
        raise ValueError("acquisition is unsupported")
    claimed = payload["claimedLabel"]
    if claimed not in _CLAIMS:
        raise ValueError("claimedLabel is unsupported")
    changed = payload["encodingChanged"]
    flat = payload["visuallyFlat"]
    if type(changed) is not bool or type(flat) is not bool:
        raise ValueError("encodingChanged and visuallyFlat must be bools")
    bits = payload["containerBits"]
    if bits not in (8, 10) or type(bits) is not int:
        raise ValueError("containerBits must be 8 or 10")
    return sample, stage, acquisition, claimed, changed, bits, flat


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P062-06 must not yield qualified or allowed")
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
