"""TC-P160-02 Incomplete public source.

Host reference. A public package that omits proprietary imaging components can
be inspected only for what it actually contains. Missing components stay
unknown. Calling that package a complete camera firmware implementation
without evidence is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P160-02",
    "phase": "P160",
    "workstream": 20,
    "name": "Incomplete public source",
    "intervention": "Provide a public kernel or firmware-related package that omits proprietary imaging components.",
    "expected": "Describe exactly what can be inspected and keep missing components unknown.",
    "negative": "A source archive must not be called a complete camera firmware implementation without evidence.",
    "repeat": "Repeat different device variants and software versions.",
}

NEGATIVE_TOKEN = "incomplete-source-called-complete-firmware"
MISSING_NOT_UNKNOWN = "missing-components-not-unknown"
INSPECTION_UNSTATED = "inspectable-surface-not-described"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "records",
    "maintenanceNote",
    "only_passes",
    "inspectable",
    "omittedComponents",
    "missingMarkedUnknown",
    "calledCompleteFirmware",
    "completenessEvidence",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p160_close_the_programme_with_a_reproducible_evidence_archive.py"
    spec = importlib.util.spec_from_file_location("p160_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _names(value: object, label: str) -> list[str]:
    _GATE.require(isinstance(value, list), label + " must be a list")
    names = [_GATE.require_text(item, f"{label}[{index}]") for index, item in enumerate(value)]
    _GATE.require(len(names) == len(set(names)), label + " entries must be unique")
    return names


def _source_faults(payload: dict) -> dict:
    inspectable = _names(payload["inspectable"], "inspectable")
    omitted = _names(payload["omittedComponents"], "omittedComponents")
    unknown = _GATE.require_bool(payload["missingMarkedUnknown"], "missingMarkedUnknown")
    called_complete = _GATE.require_bool(payload["calledCompleteFirmware"], "calledCompleteFirmware")
    evidenced = _GATE.require_bool(payload["completenessEvidence"], "completenessEvidence")
    faults: list[str] = []
    if not inspectable:
        faults.append(INSPECTION_UNSTATED)
    if omitted and not unknown:
        faults.append(MISSING_NOT_UNKNOWN)
    if called_complete and (bool(omitted) or not evidenced):
        faults.append(NEGATIVE_TOKEN)
    return {
        "faults": faults,
        "observed": {
            "inspectable": inspectable,
            "omittedComponents": omitted,
            "missingMarkedUnknown": unknown,
            "calledCompleteFirmware": called_complete,
            "completenessEvidence": evidenced,
        },
    }


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    judged = _source_faults(payload)
    faults = list(bundle["faults"])
    faults.extend(judged["faults"])
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [judged["observed"]],
        {
            NEGATIVE_TOKEN: CASE["negative"],
            MISSING_NOT_UNKNOWN: CASE["expected"],
            INSPECTION_UNSTATED: CASE["expected"],
        },
    )
