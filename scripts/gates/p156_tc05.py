"""TC-P156-05 Advertised unlock without delivery.

Host reference. An expanded mode menu without valid sensor frames fails the
acquisition hypothesis. Treating the newly visible setting as useful capture
is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P156-05",
    "phase": "P156",
    "workstream": 20,
    "name": "Advertised unlock without delivery",
    "intervention": "Change reported capability metadata but obtain no valid new sensor output.",
    "expected": "Fail the acquisition hypothesis despite the expanded mode menu.",
    "negative": "A newly visible setting is not proof of useful capture.",
    "repeat": "Repeat sample receipt, decoded fidelity, sustained cadence, and thermal checks.",
}

NEGATIVE_TOKEN = "visible-setting-is-not-useful-capture"
HYPOTHESIS_NOT_FAILED = "acquisition-hypothesis-not-failed"
HYPOTHESES = frozenset({"acquisition-delivered", "not-delivered"})
EXTRA_KEYS = {"modeMenuExpanded", "sensorFrames", "validSensorOutput", "hypothesis"}


def _load_gate():
    path = Path(__file__).resolve().parent / "p156_prepare_a_separate_firmware_risk_gate.py"
    spec = importlib.util.spec_from_file_location("p156_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _delivery_faults(
    mode_menu_expanded: bool,
    sensor_frames: int,
    valid_sensor_output: bool,
    hypothesis: str,
) -> tuple[list[str], bool]:
    delivered = valid_sensor_output is True and sensor_frames > 0
    faults: list[str] = []
    if mode_menu_expanded and not delivered and hypothesis == "acquisition-delivered":
        faults.append(NEGATIVE_TOKEN)
    if mode_menu_expanded and not delivered and hypothesis != "not-delivered":
        faults.append(HYPOTHESIS_NOT_FAILED)
    return faults, delivered


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, EXTRA_KEYS)
    expanded = _GATE.require_bool(payload["modeMenuExpanded"], "modeMenuExpanded")
    frames = _GATE.require_int(payload["sensorFrames"], "sensorFrames")
    _GATE.require(frames >= 0, "sensorFrames must be >= 0")
    valid = _GATE.require_bool(payload["validSensorOutput"], "validSensorOutput")
    hypothesis = _GATE.require_text(payload["hypothesis"], "hypothesis")
    _GATE.require(hypothesis in HYPOTHESES, "hypothesis is not recognized")
    case_faults, delivered = _delivery_faults(expanded, frames, valid, hypothesis)
    faults = list(bundle["faults"])
    faults.extend(case_faults)
    extra = [{
        "modeMenuExpanded": expanded,
        "sensorFrames": frames,
        "validSensorOutput": valid,
        "hypothesis": hypothesis,
        "delivered": delivered,
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
