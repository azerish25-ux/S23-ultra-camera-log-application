"""TC-P159-05 Advertised unlock without delivery.

Host reference. Expanding reported capability metadata is not useful capture.
The acquisition hypothesis fails unless valid sensor samples, decoded fidelity,
sustained cadence, and a thermal check are all present.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P159-05",
    "phase": "P159",
    "workstream": 20,
    "name": "Advertised unlock without delivery",
    "intervention": "Change reported capability metadata but obtain no valid new sensor output.",
    "expected": "Fail the acquisition hypothesis despite the expanded mode menu.",
    "negative": "A newly visible setting is not proof of useful capture.",
    "repeat": "Repeat sample receipt, decoded fidelity, sustained cadence, and thermal checks.",
}

NEGATIVE_TOKEN = "visible-setting-proves-useful-capture"
HYPOTHESIS_WITHOUT_OUTPUT = "acquisition-hypothesis-accepted-without-output"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "baseline_stable",
    "stabilityNoted",
    "baselineRank",
    "candidates",
    "modeMenuExpanded",
    "samplesReceived",
    "decodedFidelity",
    "sustainedCadence",
    "thermalChecked",
    "hypothesisAccepted",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p159_explore_higher_quality_computational_optics.py"
    spec = importlib.util.spec_from_file_location("p159_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_fidelity(value: object) -> float | None:
    if value is None:
        return None
    number = _GATE.require_number(value, "decodedFidelity")
    _GATE.require(0 <= number <= 1, "decodedFidelity must be between 0 and 1")
    return number


def _delivery_faults(
    expanded: bool,
    samples: int,
    fidelity: float | None,
    sustained: bool,
    thermal: bool,
    accepted: bool,
) -> list[str]:
    faults: list[str] = []
    usable = samples > 0 and fidelity is not None and fidelity > 0 and sustained and thermal
    if accepted and not usable:
        faults.append(HYPOTHESIS_WITHOUT_OUTPUT)
    if accepted and expanded and not usable:
        faults.append(NEGATIVE_TOKEN)
    return _GATE.dedupe(faults)


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    expanded = _GATE.require_bool(payload["modeMenuExpanded"], "modeMenuExpanded")
    samples = _GATE.require_int(payload["samplesReceived"], "samplesReceived")
    _GATE.require(samples >= 0, "samplesReceived must be >= 0")
    fidelity = _parse_fidelity(payload["decodedFidelity"])
    sustained = _GATE.require_bool(payload["sustainedCadence"], "sustainedCadence")
    thermal = _GATE.require_bool(payload["thermalChecked"], "thermalChecked")
    accepted = _GATE.require_bool(payload["hypothesisAccepted"], "hypothesisAccepted")
    faults = list(bundle["faults"])
    faults.extend(_delivery_faults(expanded, samples, fidelity, sustained, thermal, accepted))
    extra = [{
        "modeMenuExpanded": expanded,
        "samplesReceived": samples,
        "decodedFidelity": None if fidelity is None else _GATE.display_number(fidelity),
        "sustainedCadence": sustained,
        "thermalChecked": thermal,
        "hypothesisAccepted": accepted,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            HYPOTHESIS_WITHOUT_OUTPUT: CASE["expected"],
        },
    )
