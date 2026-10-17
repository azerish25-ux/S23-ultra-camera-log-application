"""TC-P159-06 Computational capture overclaim.

Host reference. A merge of multiple exposures is computational acquisition.
It is not a single unchanged sensor exposure. Motion artifacts and retained
information are measured separately from the attractive result.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P159-06",
    "phase": "P159",
    "workstream": 20,
    "name": "Computational capture overclaim",
    "intervention": "Merge multiple exposures and present the result as a single unchanged sensor exposure.",
    "expected": "Label computational acquisition and measure motion artifacts and retained information separately.",
    "negative": "An attractive merge cannot erase its source-sampling provenance.",
    "repeat": "Repeat moving subjects, clipped channels, alignment failures, and temporal ghosts.",
}

NEGATIVE_TOKEN = "merge-erases-source-sampling-provenance"
UNLABELED = "computational-acquisition-unlabeled"
NOT_MEASURED = "motion-or-information-not-measured"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "baseline_stable",
    "stabilityNoted",
    "baselineRank",
    "candidates",
    "exposuresMerged",
    "presentedAsSingleUnchangedExposure",
    "labeledComputational",
    "motionArtifactsMeasured",
    "retainedInformationMeasured",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p159_explore_higher_quality_computational_optics.py"
    spec = importlib.util.spec_from_file_location("p159_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _merge_faults(
    exposures: int,
    presented_unchanged: bool,
    labeled: bool,
    motion_measured: bool,
    information_measured: bool,
) -> list[str]:
    faults: list[str] = []
    if exposures > 1 and presented_unchanged:
        faults.append(NEGATIVE_TOKEN)
    if exposures > 1 and not labeled:
        faults.append(UNLABELED)
    if exposures > 1 and not (motion_measured and information_measured):
        faults.append(NOT_MEASURED)
    return _GATE.dedupe(faults)


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    exposures = _GATE.require_int(payload["exposuresMerged"], "exposuresMerged")
    _GATE.require(exposures >= 1, "exposuresMerged must be >= 1")
    presented = _GATE.require_bool(
        payload["presentedAsSingleUnchangedExposure"],
        "presentedAsSingleUnchangedExposure",
    )
    labeled = _GATE.require_bool(payload["labeledComputational"], "labeledComputational")
    motion = _GATE.require_bool(payload["motionArtifactsMeasured"], "motionArtifactsMeasured")
    retained = _GATE.require_bool(payload["retainedInformationMeasured"], "retainedInformationMeasured")
    faults = list(bundle["faults"])
    faults.extend(_merge_faults(exposures, presented, labeled, motion, retained))
    extra = [{
        "exposuresMerged": exposures,
        "presentedAsSingleUnchangedExposure": presented,
        "labeledComputational": labeled,
        "motionArtifactsMeasured": motion,
        "retainedInformationMeasured": retained,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            UNLABELED: CASE["expected"],
            NOT_MEASURED: CASE["expected"],
        },
    )
