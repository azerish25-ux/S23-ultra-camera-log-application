"""TC-P155-02 Incomplete public source.

Host reference. A public kernel or firmware-related package that omits
proprietary imaging components is not a complete camera firmware implementation.
Inspectable parts are listed. Missing components stay unknown.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P155-02",
    "phase": "P155",
    "workstream": 20,
    "name": "Incomplete public source",
    "intervention": "Provide a public kernel or firmware-related package that omits proprietary imaging components.",
    "expected": "Describe exactly what can be inspected and keep missing components unknown.",
    "negative": "A source archive must not be called a complete camera firmware implementation without evidence.",
    "repeat": "Repeat different device variants and software versions.",
}

NEGATIVE_TOKEN = "source-archive-called-complete-firmware"
NOTHING_INSPECTED = "inspectable-surface-not-described"
PACKAGE_KEYS = frozenset({
    "inspectable",
    "missing",
    "claimedCompleteCameraFirmware",
    "deviceVariant",
    "softwareVersion",
})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "alternatives",
    "conclusion",
    "sourcePackage",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p155_evaluate_reversible_application_level_alternatives.py"
    spec = importlib.util.spec_from_file_location("p155_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _names(value: object, label: str) -> list[str]:
    _GATE.require(isinstance(value, list), label + " must be a list")
    names = [_GATE.require_text(item, f"{label}[{index}]") for index, item in enumerate(value)]
    _GATE.require(len(names) == len(set(names)), label + " entries must be unique")
    return names


def _parse_package(value: object) -> dict:
    _GATE.require(isinstance(value, dict), "sourcePackage must be an object")
    _GATE.require(set(value) == PACKAGE_KEYS, "sourcePackage keys are invalid")
    return {
        "inspectable": _names(value["inspectable"], "sourcePackage.inspectable"),
        "missing": _names(value["missing"], "sourcePackage.missing"),
        "claimedCompleteCameraFirmware": _GATE.require_bool(
            value["claimedCompleteCameraFirmware"],
            "sourcePackage.claimedCompleteCameraFirmware",
        ),
        "deviceVariant": _GATE.require_text(value["deviceVariant"], "sourcePackage.deviceVariant"),
        "softwareVersion": _GATE.require_text(value["softwareVersion"], "sourcePackage.softwareVersion"),
    }


def _source_faults(package: dict) -> list[str]:
    faults: list[str] = []
    if not package["inspectable"]:
        faults.append(NOTHING_INSPECTED)
    if package["claimedCompleteCameraFirmware"]:
        faults.append(NEGATIVE_TOKEN)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    package = _parse_package(payload["sourcePackage"])
    faults = list(bundle["faults"])
    faults.extend(_source_faults(package))
    extra = [{
        "inspectable": list(package["inspectable"]),
        "missingUnknown": list(package["missing"]),
        "claimedCompleteCameraFirmware": package["claimedCompleteCameraFirmware"],
        "deviceVariant": package["deviceVariant"],
        "softwareVersion": package["softwareVersion"],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            NOTHING_INSPECTED: CASE["expected"],
        },
    )
