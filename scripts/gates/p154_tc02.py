"""TC-P154-02 Incomplete public source.

Host reference. A public kernel or firmware-related package that omits
proprietary imaging components must say exactly what can be inspected and keep
the missing components unknown. Calling that archive a complete camera firmware
implementation without evidence is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P154-02",
    "phase": "P154",
    "workstream": 20,
    "name": "Incomplete public source",
    "intervention": "Provide a public kernel or firmware-related package that omits proprietary imaging components.",
    "expected": "Describe exactly what can be inspected and keep missing components unknown.",
    "negative": "A source archive must not be called a complete camera firmware implementation without evidence.",
    "repeat": "Repeat different device variants and software versions.",
}

NEGATIVE_TOKEN = "source-archive-called-complete-without-evidence"
MISSING_UNKNOWN = "missing-component-not-kept-unknown"
LISTED_AS_INSPECTED = "unknown-component-described-as-inspected"
CASE_FIELDS = {
    "inspected",
    "unknownComponents",
    "calledComplete",
    "deviceVariant",
    "softwareVersion",
}


def _load_gate():
    path = Path(__file__).resolve().parent / "p154_survey_public_firmware_and_hal_information.py"
    spec = importlib.util.spec_from_file_location("p154_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, CASE_FIELDS)
    inspected = _GATE.parse_string_list(payload["inspected"], "inspected", allow_empty=False)
    unknown = _GATE.parse_string_list(payload["unknownComponents"], "unknownComponents", allow_empty=True)
    called_complete = _GATE.require_bool(payload["calledComplete"], "calledComplete")
    variant = _GATE.require_text(payload["deviceVariant"], "deviceVariant")
    version = _GATE.require_text(payload["softwareVersion"], "softwareVersion")
    faults = list(bundle["faults"])
    if called_complete:
        faults.append(NEGATIVE_TOKEN)
    if _GATE.PROPRIETARY_COMPONENT not in unknown:
        faults.append(MISSING_UNKNOWN)
    if any(item in inspected for item in unknown):
        faults.append(LISTED_AS_INSPECTED)
    extra = [{
        "inspected": inspected,
        "unknownComponents": unknown,
        "calledComplete": called_complete,
        "deviceVariant": variant,
        "softwareVersion": version,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            MISSING_UNKNOWN: CASE["expected"],
            LISTED_AS_INSPECTED: "a missing component cannot be described as inspected",
        },
    )
