"""TC-P158-02 Incomplete public source.

Host reference. A public kernel or firmware-related package that omits
proprietary imaging stays incomplete. Missing components remain unknown.
Calling that archive a complete camera firmware implementation is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P158-02",
    "phase": "P158",
    "workstream": 20,
    "name": "Incomplete public source",
    "intervention": (
        "Provide a public kernel or firmware-related package that omits proprietary "
        "imaging components."
    ),
    "expected": "Describe exactly what can be inspected and keep missing components unknown.",
    "negative": "A source archive must not be called a complete camera firmware implementation without evidence.",
    "repeat": "Repeat different device variants and software versions.",
}

NEGATIVE_TOKEN = "source-archive-called-complete-firmware"
MISSING_NOT_UNKNOWN = "missing-components-not-kept-unknown"
PROPRIETARY = "proprietary-imaging"
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
    "inspectable",
    "unknownComponents",
    "claimedCompleteFirmware",
    "proprietaryImagingOmitted",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p158_explore_advanced_capture_research_independently.py"
    spec = importlib.util.spec_from_file_location("p158_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _source_faults(inspectable: list[str], unknown: list[str], claimed: bool, omitted: bool) -> list[str]:
    overlap = set(inspectable) & set(unknown)
    _GATE.require(not overlap, "inspectable and unknown components must be disjoint")
    faults: list[str] = []
    if omitted and PROPRIETARY not in unknown:
        faults.append(MISSING_NOT_UNKNOWN)
    if claimed:
        faults.append(NEGATIVE_TOKEN)
    return faults


def case_payload(**overrides):
    payload = _GATE.core_payload()
    payload.update({
        "repeat": "device-variant",
        "inspectable": ["public-kernel-interfaces"],
        "unknownComponents": [PROPRIETARY],
        "claimedCompleteFirmware": False,
        "proprietaryImagingOmitted": True,
    })
    payload.update(overrides)
    return payload


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    inspectable = _GATE.require_string_list(payload["inspectable"], "inspectable", minimum=1)
    unknown = _GATE.require_string_list(payload["unknownComponents"], "unknownComponents", minimum=0)
    claimed = _GATE.require_bool(payload["claimedCompleteFirmware"], "claimedCompleteFirmware")
    omitted = _GATE.require_bool(payload["proprietaryImagingOmitted"], "proprietaryImagingOmitted")
    faults = list(bundle["faults"])
    faults.extend(_source_faults(inspectable, unknown, claimed, omitted))
    extra = [{
        "inspectable": inspectable,
        "unknownComponents": unknown,
        "claimedCompleteFirmware": claimed,
        "proprietaryImagingOmitted": omitted,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            MISSING_NOT_UNKNOWN: CASE["expected"],
        },
    )
