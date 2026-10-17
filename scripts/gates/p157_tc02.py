"""TC-P157-02 Incomplete public source.

Host reference. A public kernel or firmware-related package that omits
proprietary imaging stays incomplete. Inspectable parts are named. Missing
parts stay unknown. The archive is not a complete camera firmware.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P157-02",
    "phase": "P157",
    "workstream": 20,
    "name": "Incomplete public source",
    "intervention": "Provide a public kernel or firmware-related package that omits proprietary imaging components.",
    "expected": "Describe exactly what can be inspected and keep missing components unknown.",
    "negative": "A source archive must not be called a complete camera firmware implementation without evidence.",
    "repeat": "Repeat different device variants and software versions.",
}

NEGATIVE_TOKEN = "source-archive-called-complete-firmware"
UNKNOWN_TOKEN = "missing-component-not-kept-unknown"
UNDESCRIBED_TOKEN = "inspectable-components-not-described"
COMPONENT_KEYS = {"name", "inspectable", "status", "evidence"}
STATUSES = frozenset({"inspected", "unknown"})
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
    "components",
    "labelledCompleteCameraFirmware",
    "deviceVariant",
    "softwareVersion",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p157_design_instrumented_low_level_experiments.py"
    spec = importlib.util.spec_from_file_location("p157_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_components(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list) and bool(value), "components must be a non-empty list")
    rows = []
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict), f"components[{index}] must be an object")
        _GATE.require(set(item) == COMPONENT_KEYS, f"components[{index}] keys are invalid")
        status = _GATE.require_text(item["status"], f"components[{index}].status")
        _GATE.require(status in STATUSES, f"components[{index}].status is not recognized")
        inspectable = _GATE.require_bool(item["inspectable"], f"components[{index}].inspectable")
        evidence = item["evidence"]
        if status == "inspected":
            evidence = _GATE.require_text(evidence, f"components[{index}].evidence")
        else:
            _GATE.require(evidence is None, f"components[{index}].evidence must be null when unknown")
        rows.append({
            "name": _GATE.require_text(item["name"], f"components[{index}].name"),
            "inspectable": inspectable,
            "status": status,
            "evidence": evidence,
        })
    names = [row["name"] for row in rows]
    _GATE.require(len(names) == len(set(names)), "component names must be unique")
    return rows


def _source_faults(components: list[dict], labelled_complete: bool) -> list[str]:
    faults: list[str] = []
    unknown = [row for row in components if row["status"] == "unknown"]
    inspected = [row for row in components if row["status"] == "inspected"]
    if not inspected:
        faults.append(UNDESCRIBED_TOKEN)
    if any(row["inspectable"] for row in unknown):
        faults.append(UNKNOWN_TOKEN)
    if labelled_complete and (unknown or any(row["evidence"] is None for row in components)):
        faults.append(NEGATIVE_TOKEN)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    components = _parse_components(payload["components"])
    labelled = _GATE.require_bool(payload["labelledCompleteCameraFirmware"], "labelledCompleteCameraFirmware")
    variant = _GATE.require_text(payload["deviceVariant"], "deviceVariant")
    version = _GATE.require_text(payload["softwareVersion"], "softwareVersion")
    faults = list(bundle["faults"])
    faults.extend(_source_faults(components, labelled))
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [{
            "deviceVariant": variant,
            "softwareVersion": version,
            "unknownComponents": [row["name"] for row in components if row["status"] == "unknown"],
            "inspectableComponents": [row["name"] for row in components if row["status"] == "inspected"],
            "labelledCompleteCameraFirmware": labelled,
        }],
        {
            NEGATIVE_TOKEN: CASE["negative"],
            UNKNOWN_TOKEN: CASE["expected"],
            UNDESCRIBED_TOKEN: CASE["expected"],
        },
    )
