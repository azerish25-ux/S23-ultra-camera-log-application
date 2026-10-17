"""TC-P160-06 Computational capture overclaim.

Host reference. A merge of multiple exposures is computational acquisition.
Motion artifacts and retained information are measured separately. An attractive
merge cannot erase its source-sampling provenance or be presented as one
unchanged sensor exposure.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P160-06",
    "phase": "P160",
    "workstream": 20,
    "name": "Computational capture overclaim",
    "intervention": "Merge multiple exposures and present the result as a single unchanged sensor exposure.",
    "expected": "Label computational acquisition and measure motion artifacts and retained information separately.",
    "negative": "An attractive merge cannot erase its source-sampling provenance.",
    "repeat": "Repeat moving subjects, clipped channels, alignment failures, and temporal ghosts.",
}

NEGATIVE_TOKEN = "attractive-merge-erases-provenance"
UNLABELED = "computational-acquisition-unlabeled"
NOT_SEPARATED = "motion-and-retention-not-measured-separately"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "records",
    "maintenanceNote",
    "only_passes",
    "exposureCount",
    "presentedAsUnchangedSensorExposure",
    "labeledComputational",
    "motionArtifactsMeasured",
    "retainedInformationMeasured",
    "provenanceErased",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p160_close_the_programme_with_a_reproducible_evidence_archive.py"
    spec = importlib.util.spec_from_file_location("p160_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _merge_faults(payload: dict) -> dict:
    count = _GATE.require_int(payload["exposureCount"], "exposureCount")
    _GATE.require(count >= 1, "exposureCount must be >= 1")
    presented = _GATE.require_bool(
        payload["presentedAsUnchangedSensorExposure"],
        "presentedAsUnchangedSensorExposure",
    )
    labeled = _GATE.require_bool(payload["labeledComputational"], "labeledComputational")
    motion = _GATE.require_bool(payload["motionArtifactsMeasured"], "motionArtifactsMeasured")
    retained = _GATE.require_bool(payload["retainedInformationMeasured"], "retainedInformationMeasured")
    erased = _GATE.require_bool(payload["provenanceErased"], "provenanceErased")
    faults: list[str] = []
    merged = count >= 2
    if merged and (presented or not labeled):
        faults.append(UNLABELED)
    if merged and (not motion or not retained):
        faults.append(NOT_SEPARATED)
    if merged and erased:
        faults.append(NEGATIVE_TOKEN)
    return {
        "faults": faults,
        "observed": {
            "exposureCount": count,
            "merged": merged,
            "presentedAsUnchangedSensorExposure": presented,
            "labeledComputational": labeled,
            "motionArtifactsMeasured": motion,
            "retainedInformationMeasured": retained,
            "provenanceErased": erased,
        },
    }


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    judged = _merge_faults(payload)
    faults = list(bundle["faults"])
    faults.extend(judged["faults"])
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [judged["observed"]],
        {
            NEGATIVE_TOKEN: CASE["negative"],
            UNLABELED: CASE["expected"],
            NOT_SEPARATED: CASE["expected"],
        },
    )
