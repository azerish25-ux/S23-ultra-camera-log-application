"""TC-P135-05 Nonvisual interaction.

Host fixture. Comparison controls expose usable names, values, order, and
cancellation for both transfers, the matched frame, and the sync offset.
An unlabeled canvas as the only control is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P135-05",
    "phase": "P135",
    "workstream": 17,
    "name": "Nonvisual interaction",
    "intervention": "Perform the core phase task using accessibility navigation and spoken state information.",
    "expected": "Expose usable names, order, values, and cancellation without relying only on color or precision gestures.",
    "negative": "An unlabeled custom canvas as the only control must fail.",
    "repeat": "Repeat camera operation, ROI selection, focus editing, and recovery export.",
}

NEGATIVE_TOKEN = "unlabeled-canvas-only-control"
CONTROL_KEYS = {"name", "value", "cancellable"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "comparison",
    "unlabeledCanvasOnly",
    "controls",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p135_build_side_by_side_comparison_tools.py"
    spec = importlib.util.spec_from_file_location("p135_gate_for_tc05", path)
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
        _GATE.require(isinstance(name, str), f"controls[{index}].name must be a string")
        _GATE.require(isinstance(spoken, str), f"controls[{index}].value must be a string")
        cancellable = _GATE.require_bool(item["cancellable"], f"controls[{index}].cancellable")
        if not name.strip() or name != name.strip() or not spoken.strip() or spoken != spoken.strip():
            blank = True
        parsed.append({"name": name, "value": spoken, "cancellable": cancellable, "order": index})
    return parsed, blank


def _expected_controls(comparison: dict, info: dict) -> dict[str, str]:
    frame_value = str(comparison["left"]["frame_index"]) if info["framesMatch"] else "unmatched"
    left_transfer = comparison["left"]["transfer"] if isinstance(comparison["left"]["transfer"], str) else "undeclared"
    right_transfer = comparison["right"]["transfer"] if isinstance(comparison["right"]["transfer"], str) else "undeclared"
    return {
        "left-transfer": left_transfer,
        "right-transfer": right_transfer,
        "frame": frame_value,
        "sync-offset": _GATE.format_offset(comparison["sync_offset"]),
    }


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    unlabeled = _GATE.require_bool(payload["unlabeledCanvasOnly"], "unlabeledCanvasOnly")
    controls, blank = _parse_controls(payload["controls"])
    expected = _expected_controls(bundle["comparison"], bundle["info"])
    spoken = {
        name: any(item["name"] == name and item["value"] == value for item in controls)
        for name, value in expected.items()
    }
    cancellable = any(item["cancellable"] for item in controls)
    if unlabeled or blank or not controls or not cancellable or not all(spoken.values()):
        faults.append(NEGATIVE_TOKEN)
    extra = [{
        "unlabeledCanvasOnly": unlabeled,
        "controlOrder": [item["name"] for item in controls],
        "spoken": spoken,
        "cancellable": cancellable,
    }]
    return _GATE.finish_case(CASE, bundle, faults, extra, {NEGATIVE_TOKEN: CASE["negative"]})
