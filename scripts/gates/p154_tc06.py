"""TC-P154-06 Computational capture overclaim.

Host reference. A merge of multiple exposures is computational acquisition.
It is not a single unchanged sensor exposure. Motion artifacts and retained
information are measured separately. The merge cannot erase source-sampling
provenance.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P154-06",
    "phase": "P154",
    "workstream": 20,
    "name": "Computational capture overclaim",
    "intervention": "Merge multiple exposures and present the result as a single unchanged sensor exposure.",
    "expected": "Label computational acquisition and measure motion artifacts and retained information separately.",
    "negative": "An attractive merge cannot erase its source-sampling provenance.",
    "repeat": "Repeat moving subjects, clipped channels, alignment failures, and temporal ghosts.",
}

NEGATIVE_TOKEN = "attractive-merge-erased-source-provenance"
PRESENTED_AS_SINGLE = "merge-presented-as-unchanged-sensor-exposure"
NOT_SEPARATE = "motion-and-retained-information-not-separate"
PRESENTATIONS = frozenset({"computational-acquisition", "single-unchanged-sensor-exposure"})
CASE_FIELDS = {
    "exposureCount",
    "presentedAs",
    "labeledComputational",
    "motionArtifactsMeasured",
    "retainedInformationMeasured",
    "provenanceRetained",
}


def _load_gate():
    path = Path(__file__).resolve().parent / "p154_survey_public_firmware_and_hal_information.py"
    spec = importlib.util.spec_from_file_location("p154_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _merge_faults(
    exposure_count: int,
    presented_as: str,
    labeled: bool,
    motion: bool,
    retained: bool,
    provenance: bool,
) -> list[str]:
    faults: list[str] = []
    if exposure_count >= 2 and (presented_as == "single-unchanged-sensor-exposure" or not labeled):
        faults.append(PRESENTED_AS_SINGLE)
    if exposure_count >= 2 and not (motion and retained):
        faults.append(NOT_SEPARATE)
    if not provenance:
        faults.append(NEGATIVE_TOKEN)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, CASE_FIELDS)
    count = payload["exposureCount"]
    _GATE.require(type(count) is int and count >= 1, "exposureCount must be an int >= 1")
    presented = _GATE.require_text(payload["presentedAs"], "presentedAs")
    _GATE.require(presented in PRESENTATIONS, "presentedAs is not recognized")
    labeled = _GATE.require_bool(payload["labeledComputational"], "labeledComputational")
    motion = _GATE.require_bool(payload["motionArtifactsMeasured"], "motionArtifactsMeasured")
    retained = _GATE.require_bool(payload["retainedInformationMeasured"], "retainedInformationMeasured")
    provenance = _GATE.require_bool(payload["provenanceRetained"], "provenanceRetained")
    faults = list(bundle["faults"])
    faults.extend(_merge_faults(count, presented, labeled, motion, retained, provenance))
    extra = [{
        "exposureCount": count,
        "presentedAs": presented,
        "labeledComputational": labeled,
        "motionArtifactsMeasured": motion,
        "retainedInformationMeasured": retained,
        "provenanceRetained": provenance,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            PRESENTED_AS_SINGLE: CASE["intervention"],
            NOT_SEPARATE: CASE["expected"],
        },
    )
