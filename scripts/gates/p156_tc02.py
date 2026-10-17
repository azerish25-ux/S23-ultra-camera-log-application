"""TC-P156-02 Incomplete public source.

Host reference. A public kernel or firmware-related package that omits
proprietary imaging components stays incomplete. Calling that archive a
complete camera firmware implementation is rejected. A component listed as
both inspectable and missing was not kept unknown.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P156-02",
    "phase": "P156",
    "workstream": 20,
    "name": "Incomplete public source",
    "intervention": "Provide a public kernel or firmware-related package that omits proprietary imaging components.",
    "expected": "Describe exactly what can be inspected and keep missing components unknown.",
    "negative": "A source archive must not be called a complete camera firmware implementation without evidence.",
    "repeat": "Repeat different device variants and software versions.",
}

NEGATIVE_TOKEN = "source-archive-called-complete-firmware"
UNKNOWN_OMITTED = "missing-component-not-kept-unknown"
PROPRIETARY_IMAGING = "proprietary-imaging"
PACKAGE_KEYS = {"name", "inspectable", "missing", "claimedComplete"}
EXTRA_KEYS = {"package"}


def _load_gate():
    path = Path(__file__).resolve().parent / "p156_prepare_a_separate_firmware_risk_gate.py"
    spec = importlib.util.spec_from_file_location("p156_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_names(value: object, label: str) -> list[str]:
    _GATE.require(isinstance(value, list), label + " must be a list")
    names = [_GATE.require_text(item, f"{label}[{index}]") for index, item in enumerate(value)]
    _GATE.require(len(names) == len(set(names)), label + " entries must be unique")
    return names


def _parse_package(value: object) -> dict:
    _GATE.require(isinstance(value, dict), "package must be an object")
    _GATE.require(set(value) == PACKAGE_KEYS, "package keys are invalid")
    return {
        "name": _GATE.require_text(value["name"], "package.name"),
        "inspectable": _parse_names(value["inspectable"], "package.inspectable"),
        "missing": _parse_names(value["missing"], "package.missing"),
        "claimedComplete": _GATE.require_bool(value["claimedComplete"], "package.claimedComplete"),
    }


def _source_faults(package: dict) -> list[str]:
    faults: list[str] = []
    inspectable = set(package["inspectable"])
    missing = set(package["missing"])
    if inspectable & missing:
        faults.append(UNKNOWN_OMITTED)
    evidence = PROPRIETARY_IMAGING in inspectable and PROPRIETARY_IMAGING not in missing and not missing
    if package["claimedComplete"] and not evidence:
        faults.append(NEGATIVE_TOKEN)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, EXTRA_KEYS)
    package = _parse_package(payload["package"])
    faults = list(bundle["faults"])
    faults.extend(_source_faults(package))
    extra = [{
        "package": package["name"],
        "inspectable": list(package["inspectable"]),
        "missing": list(package["missing"]),
        "claimedComplete": package["claimedComplete"],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            UNKNOWN_OMITTED: CASE["expected"],
        },
    )
