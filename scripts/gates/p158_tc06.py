"""TC-P158-06 Computational capture overclaim.

Host reference. A multi-frame merge is computational acquisition. Motion
artifacts and retained information stay separate measurements. An attractive
merge cannot erase source-sampling provenance or pose as one unmodified sensor
exposure.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P158-06",
    "phase": "P158",
    "workstream": 20,
    "name": "Computational capture overclaim",
    "intervention": "Merge multiple exposures and present the result as a single unchanged sensor exposure.",
    "expected": "Label computational acquisition and measure motion artifacts and retained information separately.",
    "negative": "An attractive merge cannot erase its source-sampling provenance.",
    "repeat": "Repeat moving subjects, clipped channels, alignment failures, and temporal ghosts.",
}

NEGATIVE_TOKEN = "merge-erased-source-sampling-provenance"
COMPUTATIONAL_LABEL_MISSING = "computational-acquisition-not-labelled"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "experimentLabel",
    "captureKind",
    "presentedAs",
    "labelsMergeExplicitly",
    "claimsExtraStops",
    "guaranteedEveryScene",
    "motionAlignment",
    "ghosting",
    "alignmentError",
    "motionArtifacts",
    "retainedHighlights",
    "sourceSampling",
    "motionAssumptions",
    "exposureDifferences",
    "mergeArtifacts",
    "outputLineage",
    "singleExposureBaseline",
    "alternativeRawModes",
    "synchronization",
    "claimsSensorDerivedLog",
    "provenanceRetained",
    "attractiveMerge",
    "computationalLabel",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p158_explore_advanced_capture_research_independently.py"
    spec = importlib.util.spec_from_file_location("p158_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _overclaim_faults(retained: bool, label: str) -> list[str]:
    faults: list[str] = []
    if not retained:
        faults.append(NEGATIVE_TOKEN)
    if label != _GATE.COMPUTATIONAL_LABEL:
        faults.append(COMPUTATIONAL_LABEL_MISSING)
    return faults


def case_payload(**overrides):
    payload = _GATE.core_payload()
    payload.update({
        "repeat": "moving-subjects",
        "provenanceRetained": True,
        "attractiveMerge": True,
        "computationalLabel": _GATE.COMPUTATIONAL_LABEL,
    })
    payload.update(overrides)
    return payload


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    retained = _GATE.require_bool(payload["provenanceRetained"], "provenanceRetained")
    attractive = _GATE.require_bool(payload["attractiveMerge"], "attractiveMerge")
    label = _GATE.require_text(payload["computationalLabel"], "computationalLabel")
    faults = list(bundle["faults"])
    faults.extend(_overclaim_faults(retained, label))
    extra = [{
        "provenanceRetained": retained,
        "attractiveMerge": attractive,
        "computationalLabel": label,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            COMPUTATIONAL_LABEL_MISSING: CASE["expected"],
        },
    )
