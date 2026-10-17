"""TC-P149-04 Unexpected network transmission.

Host reference. Under the offline default, frames, depth, audio, and private
metadata stay on device. An analytics thumbnail upload is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P149-04",
    "phase": "P149",
    "workstream": 19,
    "name": "Unexpected network transmission",
    "intervention": "Observe capture and development traffic with local assets already installed.",
    "expected": "Transmit no frames, depth, audio, or private metadata under the offline default.",
    "negative": "An analytics thumbnail upload contradicts the local-processing claim.",
    "repeat": "Repeat startup, errors, crashes, export, and model initialization.",
}

NEGATIVE_TOKEN = "analytics-thumbnail-upload"
OFFLINE_TRANSMISSION = "offline-private-transmission"
OFFLINE_DISABLED = "offline-default-disabled"
TRANSMISSION_KEYS = {"kind", "bytes", "endpoint"}
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
    "offlineDefault",
    "transmissions",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p149_establish_thermal_and_endurance_acceptance.py"
    spec = importlib.util.spec_from_file_location("p149_gate_for_tc04", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_transmissions(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list), "transmissions must be a list")
    rows = []
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict), f"transmissions[{index}] must be an object")
        _GATE.require(set(item) == TRANSMISSION_KEYS, f"transmissions[{index}] keys are invalid")
        kind = _GATE.require_text(item["kind"], f"transmissions[{index}].kind")
        _GATE.require(kind in _GATE.TRANSMISSION_KINDS, f"transmissions[{index}].kind is not recognized")
        byte_count = _GATE.require_int(item["bytes"], f"transmissions[{index}].bytes")
        _GATE.require(byte_count >= 0, f"transmissions[{index}].bytes must be >= 0")
        rows.append({
            "kind": kind,
            "bytes": byte_count,
            "endpoint": _GATE.require_text(item["endpoint"], f"transmissions[{index}].endpoint"),
        })
    return rows


def _traffic_faults(offline: bool, transmissions: list[dict]) -> list[str]:
    faults: list[str] = []
    if not offline:
        faults.append(OFFLINE_DISABLED)
    for item in transmissions:
        endpoint = item["endpoint"].casefold()
        private = item["kind"] in _GATE.PRIVATE_TRANSMISSIONS and item["bytes"] > 0
        if offline and private:
            faults.append(OFFLINE_TRANSMISSION)
        thumbnail = item["kind"] == "thumbnail" and item["bytes"] > 0 and "analytics" in endpoint
        if thumbnail:
            faults.append(NEGATIVE_TOKEN)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    offline = _GATE.require_bool(payload["offlineDefault"], "offlineDefault")
    transmissions = _parse_transmissions(payload["transmissions"])
    faults = list(bundle["faults"])
    faults.extend(_traffic_faults(offline, transmissions))
    extra = [{
        "offlineDefault": offline,
        "transmissionCount": len(transmissions),
        "bytes": sum(item["bytes"] for item in transmissions),
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            OFFLINE_TRANSMISSION: CASE["expected"],
            OFFLINE_DISABLED: "offline default is required",
        },
    )
