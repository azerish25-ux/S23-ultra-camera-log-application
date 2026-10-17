"""TC-P158-05 Advertised unlock without delivery.

Host reference. An expanded mode menu or a newly visible setting is not useful
capture. The acquisition hypothesis fails when no valid new sensor frames arrive.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P158-05",
    "phase": "P158",
    "workstream": 20,
    "name": "Advertised unlock without delivery",
    "intervention": "Change reported capability metadata but obtain no valid new sensor output.",
    "expected": "Fail the acquisition hypothesis despite the expanded mode menu.",
    "negative": "A newly visible setting is not proof of useful capture.",
    "repeat": "Repeat sample receipt, decoded fidelity, sustained cadence, and thermal checks.",
}

NEGATIVE_TOKEN = "visible-setting-is-not-useful-capture"
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
    "modeMenuExpanded",
    "newSettingVisible",
    "sensorFramesValid",
    "sensorFrameCount",
    "hypothesisAccepted",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p158_explore_advanced_capture_research_independently.py"
    spec = importlib.util.spec_from_file_location("p158_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _delivery_faults(expanded: bool, visible: bool, valid: bool, count: int, accepted: bool) -> list[str]:
    if valid:
        _GATE.require(count > 0, "sensorFrameCount must be > 0 when frames are valid")
    else:
        _GATE.require(count == 0, "sensorFrameCount must be 0 when frames are not valid")
    faults: list[str] = []
    if (expanded or visible) and not valid and accepted:
        faults.append(NEGATIVE_TOKEN)
    return faults


def case_payload(**overrides):
    payload = _GATE.core_payload()
    payload.update({
        "repeat": "sample-receipt",
        "modeMenuExpanded": True,
        "newSettingVisible": True,
        "sensorFramesValid": False,
        "sensorFrameCount": 0,
        "hypothesisAccepted": False,
    })
    payload.update(overrides)
    return payload


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    expanded = _GATE.require_bool(payload["modeMenuExpanded"], "modeMenuExpanded")
    visible = _GATE.require_bool(payload["newSettingVisible"], "newSettingVisible")
    valid = _GATE.require_bool(payload["sensorFramesValid"], "sensorFramesValid")
    count = _GATE.require_int(payload["sensorFrameCount"], "sensorFrameCount")
    _GATE.require(count >= 0, "sensorFrameCount must be >= 0")
    accepted = _GATE.require_bool(payload["hypothesisAccepted"], "hypothesisAccepted")
    faults = list(bundle["faults"])
    faults.extend(_delivery_faults(expanded, visible, valid, count, accepted))
    extra = [{
        "modeMenuExpanded": expanded,
        "newSettingVisible": visible,
        "sensorFramesValid": valid,
        "sensorFrameCount": count,
        "hypothesisAccepted": accepted,
        "hypothesisFailed": not accepted,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {NEGATIVE_TOKEN: CASE["negative"]},
    )
