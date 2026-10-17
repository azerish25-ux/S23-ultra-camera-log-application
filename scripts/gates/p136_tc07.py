"""TC-P136-07 Unfair comparison view.

Host fixture. Time, scale, and display-transform mismatches are computed.
Automatically enhancing one side is rejected. A preference needs alignment
or an explicit mismatch disclosure.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p136_run_usability_acceptance_on_the_physical_phone",
    Path(__file__).resolve().parent / "p136_run_usability_acceptance_on_the_physical_phone.py",
)
_GATE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_GATE)

import math

CASE = {
    "id": "TC-P136-07",
    "phase": "P136",
    "workstream": 17,
    "name": "Unfair comparison view",
    "intervention": "Compare outputs at different times, scales, or display transforms without making those differences visible.",
    "expected": "Align comparable content or clearly disclose the mismatch before presenting a preference judgment.",
    "negative": "Automatically enhancing one side of a comparison must fail.",
    "repeat": "Repeat source-versus-result, recipe revisions, and different output aspect ratios.",
}
NEGATIVE_TOKEN = "auto-enhanced-comparison-side"
UNDISCLOSED = "preference-without-disclosed-mismatch"
SIDES = frozenset({"none", "left", "right"})
PAYLOAD_KEYS = {
    "evidenceId",
    "repeat",
    "report",
    "leftTime",
    "rightTime",
    "leftScale",
    "rightScale",
    "leftTransform",
    "rightTransform",
    "mismatchDisclosed",
    "aligned",
    "autoEnhancedSide",
    "preferencePresented",
}


def mismatch_map(left_time, right_time, left_scale, right_scale, left_transform, right_transform):
    return {
        "time": not math.isclose(left_time, right_time, rel_tol=0.0, abs_tol=1e-9),
        "scale": not math.isclose(left_scale, right_scale, rel_tol=0.0, abs_tol=1e-9),
        "transform": left_transform != right_transform,
    }


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    report = _GATE.parse_report(payload["report"])
    left_time = _GATE.require_number(payload["leftTime"], "leftTime")
    right_time = _GATE.require_number(payload["rightTime"], "rightTime")
    left_scale = _GATE.require_number(payload["leftScale"], "leftScale")
    right_scale = _GATE.require_number(payload["rightScale"], "rightScale")
    _GATE.require(left_scale > 0 and right_scale > 0, "scales must be positive")
    left_transform = _GATE.require_text(payload["leftTransform"], "leftTransform")
    right_transform = _GATE.require_text(payload["rightTransform"], "rightTransform")
    disclosed = _GATE.require_bool(payload["mismatchDisclosed"], "mismatchDisclosed")
    aligned = _GATE.require_bool(payload["aligned"], "aligned")
    enhanced = _GATE.require_text(payload["autoEnhancedSide"], "autoEnhancedSide")
    _GATE.require(enhanced in SIDES, "autoEnhancedSide is not recognized")
    preference = _GATE.require_bool(payload["preferencePresented"], "preferencePresented")
    delta = mismatch_map(left_time, right_time, left_scale, right_scale, left_transform, right_transform)
    mismatch = any(delta.values())
    faults = []
    if enhanced != "none":
        faults.append(NEGATIVE_TOKEN)
    if preference and mismatch and not (aligned or disclosed):
        faults.append(UNDISCLOSED)
    reasons = [
        f"mismatch time={str(delta['time']).lower()} scale={str(delta['scale']).lower()} transform={str(delta['transform']).lower()}",
        f"aligned={str(aligned).lower()} mismatchDisclosed={str(disclosed).lower()} preferencePresented={str(preference).lower()}",
        f"autoEnhancedSide={enhanced}",
    ]
    preserved = [{
        "mismatch": delta,
        "mismatchPresent": mismatch,
        "aligned": aligned,
        "mismatchDisclosed": disclosed,
        "autoEnhancedSide": enhanced,
        "preferencePresented": preference,
    }]
    return _GATE.finish_tc(
        CASE,
        evidence,
        repeat,
        report,
        faults,
        reasons,
        preserved,
        {NEGATIVE_TOKEN: CASE["negative"], UNDISCLOSED: CASE["expected"]},
        {
            NEGATIVE_TOKEN: "Do not automatically enhance one side of a comparison.",
            UNDISCLOSED: "Align the comparison or disclose the mismatch before a preference.",
        },
    )
