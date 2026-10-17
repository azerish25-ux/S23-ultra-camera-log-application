"""TC-P154-05 Advertised unlock without delivery.

Host reference. An expanded mode menu or a newly visible setting is not useful
capture. Without valid new sensor output the acquisition hypothesis fails.
Sample receipt, decoded fidelity, sustained cadence, and thermal checks stay
separate from the menu claim.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P154-05",
    "phase": "P154",
    "workstream": 20,
    "name": "Advertised unlock without delivery",
    "intervention": "Change reported capability metadata but obtain no valid new sensor output.",
    "expected": "Fail the acquisition hypothesis despite the expanded mode menu.",
    "negative": "A newly visible setting is not proof of useful capture.",
    "repeat": "Repeat sample receipt, decoded fidelity, sustained cadence, and thermal checks.",
}

NEGATIVE_TOKEN = "visible-setting-is-not-useful-capture"
HYPOTHESIS_NOT_FAILED = "acquisition-hypothesis-not-failed"
CHECK_KEYS = ("sampleReceipt", "decodedFidelity", "sustainedCadence", "thermal")
HYPOTHESES = frozenset({"pass", "fail"})
CASE_FIELDS = {
    "modeMenuExpanded",
    "newSettingVisible",
    "validSensorOutput",
    "acquisitionHypothesis",
    "settingTreatedAsCaptureProof",
    "checks",
}


def _load_gate():
    path = Path(__file__).resolve().parent / "p154_survey_public_firmware_and_hal_information.py"
    spec = importlib.util.spec_from_file_location("p154_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_checks(value: object) -> dict:
    _GATE.require(isinstance(value, dict), "checks must be an object")
    _GATE.require(set(value) == set(CHECK_KEYS), "checks keys are invalid")
    return {key: _GATE.require_bool(value[key], "checks." + key) for key in CHECK_KEYS}


def _delivery_faults(
    visible: bool,
    valid_output: bool,
    hypothesis: str,
    treated_as_proof: bool,
    checks: dict,
) -> list[str]:
    faults: list[str] = []
    if (visible or treated_as_proof) and not valid_output and hypothesis != "fail":
        faults.append(HYPOTHESIS_NOT_FAILED)
    if hypothesis == "pass" and (not valid_output or not all(checks.values())):
        faults.append(HYPOTHESIS_NOT_FAILED)
    if (treated_as_proof or hypothesis == "pass") and not valid_output:
        faults.append(NEGATIVE_TOKEN)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, CASE_FIELDS)
    expanded = _GATE.require_bool(payload["modeMenuExpanded"], "modeMenuExpanded")
    visible = _GATE.require_bool(payload["newSettingVisible"], "newSettingVisible")
    valid_output = _GATE.require_bool(payload["validSensorOutput"], "validSensorOutput")
    hypothesis = _GATE.require_text(payload["acquisitionHypothesis"], "acquisitionHypothesis")
    _GATE.require(hypothesis in HYPOTHESES, "acquisitionHypothesis is not recognized")
    treated_as_proof = _GATE.require_bool(payload["settingTreatedAsCaptureProof"], "settingTreatedAsCaptureProof")
    checks = _parse_checks(payload["checks"])
    faults = list(bundle["faults"])
    faults.extend(_delivery_faults(visible, valid_output, hypothesis, treated_as_proof, checks))
    extra = [{
        "modeMenuExpanded": expanded,
        "newSettingVisible": visible,
        "validSensorOutput": valid_output,
        "acquisitionHypothesis": hypothesis,
        "settingTreatedAsCaptureProof": treated_as_proof,
        "checks": checks,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            HYPOTHESIS_NOT_FAILED: CASE["expected"],
        },
    )
