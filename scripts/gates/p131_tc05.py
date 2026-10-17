"""TC-P131-05 Nonvisual interaction.

Host reference. The shutter control exposes its name, unit, draft, applied
value, and cancellation. An unlabeled canvas as the only control is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P131-05",
    "phase": "P131",
    "workstream": 17,
    "name": "Nonvisual interaction",
    "intervention": "Perform the core phase task using accessibility navigation and spoken state information.",
    "expected": "Expose usable names, order, values, and cancellation without relying only on color or precision gestures.",
    "negative": "An unlabeled custom canvas as the only control must fail.",
    "repeat": "Repeat camera operation, ROI selection, focus editing, and recovery export.",
}

NEGATIVE_TOKEN = "unlabeled-canvas-only-control"
CONTROL_KEYS = {"name", "value", "unit", "cancellable"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "committed",
    "proposed",
    "unlabeledCanvasOnly",
    "controls",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p131_design_manual_controls_for_deliberate_operation.py"
    spec = importlib.util.spec_from_file_location("p131_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_controls(value: object) -> tuple[list[dict], bool]:
    _GATE.require(isinstance(value, list), "controls must be a list")
    parsed: list[dict] = []
    blank = False
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict) and set(item) == CONTROL_KEYS, f"controls[{index}] keys are invalid")
        name = item["name"]
        spoken = item["value"]
        unit = item["unit"]
        _GATE.require(isinstance(name, str), f"controls[{index}].name must be a string")
        _GATE.require(isinstance(spoken, str), f"controls[{index}].value must be a string")
        _GATE.require(isinstance(unit, str), f"controls[{index}].unit must be a string")
        cancellable = _GATE.require_bool(item["cancellable"], f"controls[{index}].cancellable")
        if (
            not name.strip()
            or name != name.strip()
            or not spoken.strip()
            or spoken != spoken.strip()
            or not unit.strip()
            or unit != unit.strip()
        ):
            blank = True
        parsed.append({
            "name": name,
            "value": spoken,
            "unit": unit,
            "cancellable": cancellable,
            "order": index,
        })
    return parsed, blank


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    unlabeled = _GATE.require_bool(payload["unlabeledCanvasOnly"], "unlabeledCanvasOnly")
    controls, blank = _parse_controls(payload["controls"])
    info = bundle["info"]
    draft = info["proposed"]["draft"]
    applied_text = _GATE.format_number(info["surviving"])
    unit = bundle["committed"]["unit"]
    control_id = bundle["committed"]["control_id"]
    matched = [
        item
        for item in controls
        if item["name"] == control_id
        and item["unit"] == unit
        and applied_text in item["value"]
        and (draft in item["value"] if draft else "draft" in item["value"])
    ]
    cancellable = any(item["cancellable"] for item in controls)
    if unlabeled or blank or not controls or not matched or not cancellable:
        faults.append(NEGATIVE_TOKEN)
    extra = [{
        "unlabeledCanvasOnly": unlabeled,
        "controlOrder": [item["name"] for item in controls],
        "draftSpoken": bool(matched),
        "appliedSpoken": applied_text,
        "cancellable": cancellable,
    }]
    return _GATE.finish_case(CASE, bundle, faults, extra, {NEGATIVE_TOKEN: CASE["negative"]})
