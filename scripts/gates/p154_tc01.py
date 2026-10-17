"""TC-P154-01 Wrong bottleneck attribution.

Host reference. A throughput limit caused by storage or scheduling is not a
hidden firmware restriction. Controlled isolation is required before any
low-level modification is proposed. Assuming every slow path is vendor
blocking is rejected. The public-firmware survey rules still apply.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P154-01",
    "phase": "P154",
    "workstream": 20,
    "name": "Wrong bottleneck attribution",
    "intervention": "Present a throughput problem caused by storage or scheduling as evidence of a hidden firmware restriction.",
    "expected": "Require controlled isolation of the bottleneck before low-level modification is proposed.",
    "negative": "Assuming every slow path is vendor blocking must fail.",
    "repeat": "Repeat acquisition-only, saved-source, development, and encoder-stage measurements.",
}

NEGATIVE_TOKEN = "every-slow-path-is-vendor-blocking"
UNISOLATED = "low-level-modification-before-controlled-isolation"
THROUGHPUT_NOT_FIRMWARE = "storage-or-scheduling-is-not-a-firmware-restriction"
STAGES = frozenset({"acquisition-only", "saved-source", "development", "encoder-stage"})
CAUSES = frozenset({
    "storage",
    "scheduling",
    "sensor-stream",
    "hal-exposure",
    "codec-interface",
    "synchronization",
    "app-performance",
    "firmware",
})
THROUGHPUT = frozenset({"storage", "scheduling"})
MEASUREMENT_KEYS = {"stage", "cause", "isolated"}
CASE_FIELDS = {
    "measurements",
    "attributesEverySlowPathToVendor",
    "proposesLowLevelModification",
}


def _load_gate():
    path = Path(__file__).resolve().parent / "p154_survey_public_firmware_and_hal_information.py"
    spec = importlib.util.spec_from_file_location("p154_gate_for_tc01", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_measurements(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list) and bool(value), "measurements must be a non-empty list")
    rows = []
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict), f"measurements[{index}] must be an object")
        _GATE.require(set(item) == MEASUREMENT_KEYS, f"measurements[{index}] keys are invalid")
        stage = _GATE.require_text(item["stage"], f"measurements[{index}].stage")
        _GATE.require(stage in STAGES, f"measurements[{index}].stage is not recognized")
        cause = _GATE.require_text(item["cause"], f"measurements[{index}].cause")
        _GATE.require(cause in CAUSES, f"measurements[{index}].cause is not recognized")
        rows.append({
            "stage": stage,
            "cause": cause,
            "isolated": _GATE.require_bool(item["isolated"], f"measurements[{index}].isolated"),
        })
    stages = [row["stage"] for row in rows]
    _GATE.require(len(stages) == len(set(stages)), "measurement stages must be unique")
    return rows


def _bottleneck_faults(measurements: list[dict], attributes_every: bool, proposes: bool) -> list[str]:
    faults: list[str] = []
    if attributes_every:
        faults.append(NEGATIVE_TOKEN)
    fully_isolated = STAGES <= {row["stage"] for row in measurements} and all(row["isolated"] for row in measurements)
    if proposes and not fully_isolated:
        faults.append(UNISOLATED)
    if proposes and fully_isolated and any(row["cause"] in THROUGHPUT for row in measurements):
        faults.append(THROUGHPUT_NOT_FIRMWARE)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, CASE_FIELDS)
    measurements = _parse_measurements(payload["measurements"])
    attributes_every = _GATE.require_bool(
        payload["attributesEverySlowPathToVendor"],
        "attributesEverySlowPathToVendor",
    )
    proposes = _GATE.require_bool(payload["proposesLowLevelModification"], "proposesLowLevelModification")
    faults = list(bundle["faults"])
    faults.extend(_bottleneck_faults(measurements, attributes_every, proposes))
    extra = [{
        "measurements": measurements,
        "attributesEverySlowPathToVendor": attributes_every,
        "proposesLowLevelModification": proposes,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            UNISOLATED: CASE["expected"],
            THROUGHPUT_NOT_FIRMWARE: (
                "storage or scheduling throughput is not evidence of a hidden firmware restriction"
            ),
        },
    )
