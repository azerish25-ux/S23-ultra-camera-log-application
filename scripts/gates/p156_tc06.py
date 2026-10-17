"""TC-P156-06 Computational capture overclaim.

Host reference. A merge of multiple exposures is computational acquisition.
Presenting it as one unchanged sensor exposure is rejected. Motion artifacts
and retained information must be measured separately.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P156-06",
    "phase": "P156",
    "workstream": 20,
    "name": "Computational capture overclaim",
    "intervention": "Merge multiple exposures and present the result as a single unchanged sensor exposure.",
    "expected": "Label computational acquisition and measure motion artifacts and retained information separately.",
    "negative": "An attractive merge cannot erase its source-sampling provenance.",
    "repeat": "Repeat moving subjects, clipped channels, alignment failures, and temporal ghosts.",
}

NEGATIVE_TOKEN = "merge-erases-source-sampling-provenance"
NOT_LABELED = "computational-acquisition-not-labeled"
NOT_MEASURED = "motion-or-retention-not-measured-separately"
EXTRA_KEYS = {
    "exposures",
    "labeledComputational",
    "presentedAsSingleSensorExposure",
    "motionArtifactsMeasured",
    "retainedInformationMeasured",
}


def _load_gate():
    path = Path(__file__).resolve().parent / "p156_prepare_a_separate_firmware_risk_gate.py"
    spec = importlib.util.spec_from_file_location("p156_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _merge_faults(
    exposures: int,
    labeled: bool,
    presented_as_single: bool,
    motion_measured: bool,
    retention_measured: bool,
) -> list[str]:
    faults: list[str] = []
    if exposures <= 1:
        return faults
    if presented_as_single or not labeled:
        faults.append(NEGATIVE_TOKEN)
    if not labeled:
        faults.append(NOT_LABELED)
    if not motion_measured or not retention_measured:
        faults.append(NOT_MEASURED)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, EXTRA_KEYS)
    exposures = _GATE.require_int(payload["exposures"], "exposures")
    _GATE.require(exposures >= 1, "exposures must be >= 1")
    labeled = _GATE.require_bool(payload["labeledComputational"], "labeledComputational")
    presented = _GATE.require_bool(payload["presentedAsSingleSensorExposure"], "presentedAsSingleSensorExposure")
    motion = _GATE.require_bool(payload["motionArtifactsMeasured"], "motionArtifactsMeasured")
    retained = _GATE.require_bool(payload["retainedInformationMeasured"], "retainedInformationMeasured")
    faults = list(bundle["faults"])
    faults.extend(_merge_faults(exposures, labeled, presented, motion, retained))
    extra = [{
        "exposures": exposures,
        "labeledComputational": labeled,
        "presentedAsSingleSensorExposure": presented,
        "motionArtifactsMeasured": motion,
        "retainedInformationMeasured": retained,
        "merged": exposures > 1,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            NOT_LABELED: CASE["expected"],
            NOT_MEASURED: CASE["expected"],
        },
    )
