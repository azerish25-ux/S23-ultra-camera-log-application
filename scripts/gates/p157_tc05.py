"""TC-P157-05 Advertised unlock without delivery.

Host reference. An expanded mode menu with no valid new sensor frames fails
the acquisition hypothesis. A newly visible setting is not useful capture.
The core protocol still rejects unlocked_claim without captured_output.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P157-05",
    "phase": "P157",
    "workstream": 20,
    "name": "Advertised unlock without delivery",
    "intervention": "Change reported capability metadata but obtain no valid new sensor output.",
    "expected": "Fail the acquisition hypothesis despite the expanded mode menu.",
    "negative": "A newly visible setting is not proof of useful capture.",
    "repeat": "Repeat sample receipt, decoded fidelity, sustained cadence, and thermal checks.",
}

NEGATIVE_TOKEN = "visible-setting-is-not-useful-capture"
HYPOTHESIS_TOKEN = "acquisition-hypothesis-not-failed"
CHECK_KEYS = ("sampleReceipt", "decodedFidelity", "sustainedCadence", "thermal")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "protocolKind",
    "deviceExperimentCompleted",
    "baselinePreserved",
    "checksum",
    "logId",
    "failureTriggers",
    "thermalSafeguardDisabled",
    "capabilityMetadataFalsified",
    "experiments",
    "menuExpanded",
    "newlyVisibleSetting",
    "settingUsedAsCaptureProof",
    "acquisitionHypothesis",
    "checks",
    "validSensorFrames",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p157_design_instrumented_low_level_experiments.py"
    spec = importlib.util.spec_from_file_location("p157_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_checks(value: object) -> dict:
    _GATE.require(isinstance(value, dict), "checks must be an object")
    _GATE.require(set(value) == set(CHECK_KEYS), "checks keys are invalid")
    return {key: _GATE.require_bool(value[key], "checks." + key) for key in CHECK_KEYS}


def _delivery_faults(observed: dict, checks: dict) -> list[str]:
    faults: list[str] = []
    delivered = observed["validSensorFrames"] > 0 and all(checks.values())
    if observed["menuExpanded"] and observed["acquisitionHypothesis"] == "pass" and not delivered:
        faults.append(HYPOTHESIS_TOKEN)
    if observed["settingUsedAsCaptureProof"] and not delivered:
        faults.append(NEGATIVE_TOKEN)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    hypothesis = _GATE.require_text(payload["acquisitionHypothesis"], "acquisitionHypothesis")
    _GATE.require(hypothesis in {"pass", "fail"}, "acquisitionHypothesis must be pass or fail")
    frames = _GATE.require_int(payload["validSensorFrames"], "validSensorFrames")
    _GATE.require(frames >= 0, "validSensorFrames must be >= 0")
    checks = _parse_checks(payload["checks"])
    observed = {
        "menuExpanded": _GATE.require_bool(payload["menuExpanded"], "menuExpanded"),
        "newlyVisibleSetting": _GATE.require_text(payload["newlyVisibleSetting"], "newlyVisibleSetting"),
        "settingUsedAsCaptureProof": _GATE.require_bool(
            payload["settingUsedAsCaptureProof"],
            "settingUsedAsCaptureProof",
        ),
        "acquisitionHypothesis": hypothesis,
        "validSensorFrames": frames,
        "checks": checks,
    }
    faults = list(bundle["faults"])
    faults.extend(_delivery_faults(observed, checks))
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [observed],
        {
            NEGATIVE_TOKEN: CASE["negative"],
            HYPOTHESIS_TOKEN: CASE["expected"],
        },
    )
