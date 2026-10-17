"""TC-P149-05 Thermal safety pressure.

Host reference. Severe or critical thermal status must set continue_capture
false or take a controlled stop that preserves footage. Keeping continue_capture
true to hold an advertised fps is rejected. The shared endurance payload is the
policy; this case does not treat a boolean stub as the decision.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P149-05",
    "phase": "P149",
    "workstream": 19,
    "name": "Thermal safety pressure",
    "intervention": "Exercise sustained workloads until the operating-system thermal policy requires action.",
    "expected": "Reduce optional work or stop capture according to the documented preservation policy.",
    "negative": "Bypassing protection to sustain an advertised rate must fail.",
    "repeat": "Repeat warm starts, charging, longer duration, and combined rendering load where safely testable.",
}

NEGATIVE_TOKEN = "protection-bypassed-for-advertised-rate"
THERMAL_IGNORED = "severe-or-critical-capture-continued"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "thermalStatus",
    "continueCapture",
    "controlledStop",
    "advertisedFpsClaimed",
    "optionalPreviewReduced",
    "footagePreserved",
    "sampleDurationSeconds",
    "frameRateGuaranteeClaimed",
    "measuredOnDevice",
    "envelopeStatus",
    "configuration",
    "ambientCelsius",
    "deviceState",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p149_establish_thermal_and_endurance_acceptance.py"
    spec = importlib.util.spec_from_file_location("p149_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    snap = bundle["snapshot"]
    faults = list(bundle["faults"])
    if snap["ignoredSevereForAdvertisedFps"] and NEGATIVE_TOKEN not in faults:
        faults.append(NEGATIVE_TOKEN)
    if snap["thermalStatus"] in _GATE.PRESSURE_STATUSES and not snap["pressureResolved"]:
        if THERMAL_IGNORED not in faults:
            faults.append(THERMAL_IGNORED)
    observed = {
        "thermalStatus": snap["thermalStatus"],
        "continueCapture": snap["continueCapture"],
        "controlledStop": snap["controlledStop"],
        "advertisedFpsClaimed": snap["advertisedFpsClaimed"],
        "optionalPreviewReduced": snap["optionalPreviewReduced"],
        "footagePreserved": snap["footagePreserved"],
        "envelopeRecorded": snap["envelopeRecorded"],
        "physicalPass": snap["physicalPass"],
        "shortSample": snap["shortSample"],
        "pressureResolved": snap["pressureResolved"],
    }
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [observed],
        {
            NEGATIVE_TOKEN: CASE["negative"],
            THERMAL_IGNORED: CASE["expected"],
        },
    )
