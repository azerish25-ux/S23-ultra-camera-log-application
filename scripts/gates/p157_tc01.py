"""TC-P157-01 Wrong bottleneck attribution.

Host reference. A throughput limit caused by storage or scheduling is not a
hidden firmware restriction. Every stage must be isolated before a low-level
modification is proposed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P157-01",
    "phase": "P157",
    "workstream": 20,
    "name": "Wrong bottleneck attribution",
    "intervention": "Present a throughput problem caused by storage or scheduling as evidence of a hidden firmware restriction.",
    "expected": "Require controlled isolation of the bottleneck before low-level modification is proposed.",
    "negative": "Assuming every slow path is vendor blocking must fail.",
    "repeat": "Repeat acquisition-only, saved-source, development, and encoder-stage measurements.",
}

NEGATIVE_TOKEN = "slow-path-assumed-vendor-blocking"
ISOLATION_TOKEN = "bottleneck-not-isolated"
REQUIRED_STAGES = ("acquisition-only", "saved-source", "development", "encoder-stage")
LIMITING_CAUSES = frozenset({"storage", "scheduling", "development", "encoder", "firmware-restriction"})
SLOW_PATH_CAUSES = frozenset({"storage", "scheduling"})
MEASUREMENT_KEYS = {"stage", "limitingCause", "isolated"}
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
    "measurements",
    "attributedCause",
    "lowLevelModificationProposed",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p157_design_instrumented_low_level_experiments.py"
    spec = importlib.util.spec_from_file_location("p157_gate_for_tc01", path)
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
        _GATE.require(stage in REQUIRED_STAGES, f"measurements[{index}].stage is not recognized")
        cause = _GATE.require_text(item["limitingCause"], f"measurements[{index}].limitingCause")
        _GATE.require(cause in LIMITING_CAUSES, f"measurements[{index}].limitingCause is not recognized")
        rows.append({
            "stage": stage,
            "limitingCause": cause,
            "isolated": _GATE.require_bool(item["isolated"], f"measurements[{index}].isolated"),
        })
    stages = [row["stage"] for row in rows]
    _GATE.require(len(stages) == len(set(stages)), "measurement stages must be unique")
    return rows


def _bottleneck_faults(measurements: list[dict], attributed: str, proposed: bool) -> list[str]:
    by_stage = {row["stage"]: row for row in measurements}
    isolated_complete = all(stage in by_stage and by_stage[stage]["isolated"] for stage in REQUIRED_STAGES)
    faults: list[str] = []
    if proposed and not isolated_complete:
        faults.append(ISOLATION_TOKEN)
    slow_path_isolated = any(
        row["isolated"] and row["limitingCause"] in SLOW_PATH_CAUSES for row in measurements
    )
    firmware_isolated = any(
        row["isolated"] and row["limitingCause"] == "firmware-restriction" for row in measurements
    )
    if attributed == "firmware-restriction" and slow_path_isolated and not firmware_isolated:
        faults.append(NEGATIVE_TOKEN)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    measurements = _parse_measurements(payload["measurements"])
    attributed = _GATE.require_text(payload["attributedCause"], "attributedCause")
    _GATE.require(attributed in LIMITING_CAUSES, "attributedCause is not recognized")
    proposed = _GATE.require_bool(payload["lowLevelModificationProposed"], "lowLevelModificationProposed")
    faults = list(bundle["faults"])
    faults.extend(_bottleneck_faults(measurements, attributed, proposed))
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [{
            "attributedCause": attributed,
            "lowLevelModificationProposed": proposed,
            "stages": [row["stage"] for row in measurements],
        }],
        {
            NEGATIVE_TOKEN: CASE["negative"],
            ISOLATION_TOKEN: CASE["expected"],
        },
    )
