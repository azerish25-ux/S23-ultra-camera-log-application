"""TC-P155-05 Advertised unlock without delivery.

Host reference. An expanded mode menu without valid new sensor output fails
the acquisition hypothesis. Sample receipt, decoded fidelity, sustained
cadence, and thermal checks stay separate from the advertised setting.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P155-05",
    "phase": "P155",
    "workstream": 20,
    "name": "Advertised unlock without delivery",
    "intervention": "Change reported capability metadata but obtain no valid new sensor output.",
    "expected": "Fail the acquisition hypothesis despite the expanded mode menu.",
    "negative": "A newly visible setting is not proof of useful capture.",
    "repeat": "Repeat sample receipt, decoded fidelity, sustained cadence, and thermal checks.",
}

NEGATIVE_TOKEN = "visible-setting-proves-useful-capture"
CHECK_VALUES = frozenset({"not-checked", "failed", "passed"})
HYPOTHESES = frozenset({"failed", "useful-capture"})
CHECK_KEYS = frozenset({
    "modeMenuExpanded",
    "validSensorSamples",
    "decodedFidelity",
    "sustainedCadence",
    "thermal",
    "hypothesis",
})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "alternatives",
    "conclusion",
    "captureCheck",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p155_evaluate_reversible_application_level_alternatives.py"
    spec = importlib.util.spec_from_file_location("p155_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _check(value: object, label: str) -> str:
    text = _GATE.require_text(value, label)
    _GATE.require(text in CHECK_VALUES, label + " is not recognized")
    return text


def _parse_check(value: object) -> dict:
    _GATE.require(isinstance(value, dict), "captureCheck must be an object")
    _GATE.require(set(value) == CHECK_KEYS, "captureCheck keys are invalid")
    samples = value["validSensorSamples"]
    _GATE.require(type(samples) is int and samples >= 0, "captureCheck.validSensorSamples must be an int >= 0")
    hypothesis = _GATE.require_text(value["hypothesis"], "captureCheck.hypothesis")
    _GATE.require(hypothesis in HYPOTHESES, "captureCheck.hypothesis is not recognized")
    return {
        "modeMenuExpanded": _GATE.require_bool(value["modeMenuExpanded"], "captureCheck.modeMenuExpanded"),
        "validSensorSamples": samples,
        "decodedFidelity": _check(value["decodedFidelity"], "captureCheck.decodedFidelity"),
        "sustainedCadence": _check(value["sustainedCadence"], "captureCheck.sustainedCadence"),
        "thermal": _check(value["thermal"], "captureCheck.thermal"),
        "hypothesis": hypothesis,
    }


def _delivered(check: dict) -> bool:
    return (
        check["validSensorSamples"] > 0
        and check["decodedFidelity"] == "passed"
        and check["sustainedCadence"] == "passed"
        and check["thermal"] == "passed"
    )


def _capture_faults(check: dict) -> list[str]:
    faults: list[str] = []
    if check["hypothesis"] == "useful-capture" and not _delivered(check):
        faults.append(NEGATIVE_TOKEN)
    if check["modeMenuExpanded"] and check["validSensorSamples"] == 0 and check["hypothesis"] != "failed":
        faults.append(NEGATIVE_TOKEN)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    check = _parse_check(payload["captureCheck"])
    faults = list(bundle["faults"])
    faults.extend(_capture_faults(check))
    extra = [{
        "modeMenuExpanded": check["modeMenuExpanded"],
        "validSensorSamples": check["validSensorSamples"],
        "decodedFidelity": check["decodedFidelity"],
        "sustainedCadence": check["sustainedCadence"],
        "thermal": check["thermal"],
        "hypothesis": check["hypothesis"],
        "delivered": _delivered(check),
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {NEGATIVE_TOKEN: CASE["negative"]},
    )
