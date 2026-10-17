"""TC-P155-06 Computational capture overclaim.

Host reference. A merge of multiple exposures is computational acquisition.
Motion artifacts and retained information are measured separately. The merge
cannot be presented as one unchanged sensor exposure, and its sampling
provenance stays attached.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P155-06",
    "phase": "P155",
    "workstream": 20,
    "name": "Computational capture overclaim",
    "intervention": "Merge multiple exposures and present the result as a single unchanged sensor exposure.",
    "expected": "Label computational acquisition and measure motion artifacts and retained information separately.",
    "negative": "An attractive merge cannot erase its source-sampling provenance.",
    "repeat": "Repeat moving subjects, clipped channels, alignment failures, and temporal ghosts.",
}

NEGATIVE_TOKEN = "merge-erases-source-sampling-provenance"
UNLABELLED = "computational-acquisition-unlabelled"
MOTION_NOT_MEASURED = "motion-artifacts-not-measured"
INFORMATION_NOT_MEASURED = "retained-information-not-measured"
LABELS = frozenset({"computational", "single-unchanged-sensor-exposure"})
MEASURES = frozenset({"measured", "omitted"})
PROVENANCE = frozenset({"retained", "erased"})
ACQUISITION_KEYS = frozenset({
    "exposureCount",
    "label",
    "motionArtifacts",
    "retainedInformation",
    "provenance",
})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "alternatives",
    "conclusion",
    "acquisition",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p155_evaluate_reversible_application_level_alternatives.py"
    spec = importlib.util.spec_from_file_location("p155_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_acquisition(value: object) -> dict:
    _GATE.require(isinstance(value, dict), "acquisition must be an object")
    _GATE.require(set(value) == ACQUISITION_KEYS, "acquisition keys are invalid")
    count = value["exposureCount"]
    _GATE.require(type(count) is int and count >= 1, "acquisition.exposureCount must be an int >= 1")
    label = _GATE.require_text(value["label"], "acquisition.label")
    _GATE.require(label in LABELS, "acquisition.label is not recognized")
    motion = _GATE.require_text(value["motionArtifacts"], "acquisition.motionArtifacts")
    _GATE.require(motion in MEASURES, "acquisition.motionArtifacts is not recognized")
    retained = _GATE.require_text(value["retainedInformation"], "acquisition.retainedInformation")
    _GATE.require(retained in MEASURES, "acquisition.retainedInformation is not recognized")
    provenance = _GATE.require_text(value["provenance"], "acquisition.provenance")
    _GATE.require(provenance in PROVENANCE, "acquisition.provenance is not recognized")
    return {
        "exposureCount": count,
        "label": label,
        "motionArtifacts": motion,
        "retainedInformation": retained,
        "provenance": provenance,
    }


def _acquisition_faults(acquisition: dict) -> list[str]:
    faults: list[str] = []
    merged = acquisition["exposureCount"] >= 2
    if merged and acquisition["label"] != "computational":
        faults.append(UNLABELLED)
        faults.append(NEGATIVE_TOKEN)
    if merged and acquisition["motionArtifacts"] != "measured":
        faults.append(MOTION_NOT_MEASURED)
    if merged and acquisition["retainedInformation"] != "measured":
        faults.append(INFORMATION_NOT_MEASURED)
    if acquisition["provenance"] != "retained":
        faults.append(NEGATIVE_TOKEN)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    acquisition = _parse_acquisition(payload["acquisition"])
    faults = list(bundle["faults"])
    faults.extend(_acquisition_faults(acquisition))
    extra = [dict(acquisition)]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            UNLABELLED: CASE["expected"],
            MOTION_NOT_MEASURED: CASE["expected"],
            INFORMATION_NOT_MEASURED: CASE["expected"],
        },
    )
