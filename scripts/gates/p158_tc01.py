"""TC-P158-01 Wrong bottleneck attribution.

Host reference. A storage or scheduling slow path must not be recorded as vendor
blocking or a hidden firmware restriction. Low-level modification is rejected
until the bottleneck is isolated across acquisition-only, saved-source,
development, and encoder-stage measurements.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P158-01",
    "phase": "P158",
    "workstream": 20,
    "name": "Wrong bottleneck attribution",
    "intervention": (
        "Present a throughput problem caused by storage or scheduling as evidence of a "
        "hidden firmware restriction."
    ),
    "expected": "Require controlled isolation of the bottleneck before low-level modification is proposed.",
    "negative": "Assuming every slow path is vendor blocking must fail.",
    "repeat": "Repeat acquisition-only, saved-source, development, and encoder-stage measurements.",
}

NEGATIVE_TOKEN = "assuming-slow-path-is-vendor-blocking"
MODIFICATION_WITHOUT_ISOLATION = "modification-without-isolation"
CAUSES = frozenset({"storage", "scheduling", "firmware", "sensor", "encoder", "unknown"})
ATTRIBUTIONS = frozenset({
    "storage",
    "scheduling",
    "firmware-restriction",
    "vendor-blocking",
    "unresolved",
    "encoder",
})
SLOW_CAUSES = frozenset({"storage", "scheduling"})
BLOCKING_ATTRIBUTIONS = frozenset({"vendor-blocking", "firmware-restriction"})
REQUIRED_STAGES = (
    "acquisition-only",
    "saved-source",
    "development",
    "encoder-stage",
)
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
    "bottleneckCause",
    "attributedTo",
    "isolated",
    "proposedModification",
    "stagesMeasured",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p158_explore_advanced_capture_research_independently.py"
    spec = importlib.util.spec_from_file_location("p158_gate_for_tc01", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _stages(value: object) -> list[str]:
    stages = _GATE.require_string_list(value, "stagesMeasured", minimum=1)
    for stage in stages:
        _GATE.require(stage in REQUIRED_STAGES, "stagesMeasured entry is not recognized")
    return stages


def _bottleneck_faults(cause: str, attributed: str, isolated: bool, proposed: bool, stages: list[str]) -> list[str]:
    faults: list[str] = []
    if cause in SLOW_CAUSES and attributed in BLOCKING_ATTRIBUTIONS:
        faults.append(NEGATIVE_TOKEN)
    if proposed and (not isolated or not set(REQUIRED_STAGES) <= set(stages)):
        faults.append(MODIFICATION_WITHOUT_ISOLATION)
    return faults


def case_payload(**overrides):
    payload = _GATE.core_payload()
    payload.update({
        "repeat": "acquisition-only",
        "bottleneckCause": "storage",
        "attributedTo": "storage",
        "isolated": True,
        "proposedModification": False,
        "stagesMeasured": list(REQUIRED_STAGES),
    })
    payload.update(overrides)
    return payload


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    cause = _GATE.require_text(payload["bottleneckCause"], "bottleneckCause")
    _GATE.require(cause in CAUSES, "bottleneckCause is not recognized")
    attributed = _GATE.require_text(payload["attributedTo"], "attributedTo")
    _GATE.require(attributed in ATTRIBUTIONS, "attributedTo is not recognized")
    isolated = _GATE.require_bool(payload["isolated"], "isolated")
    proposed = _GATE.require_bool(payload["proposedModification"], "proposedModification")
    stages = _stages(payload["stagesMeasured"])
    faults = list(bundle["faults"])
    faults.extend(_bottleneck_faults(cause, attributed, isolated, proposed, stages))
    extra = [{
        "bottleneckCause": cause,
        "attributedTo": attributed,
        "isolated": isolated,
        "proposedModification": proposed,
        "stagesMeasured": stages,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            MODIFICATION_WITHOUT_ISOLATION: CASE["expected"],
        },
    )
