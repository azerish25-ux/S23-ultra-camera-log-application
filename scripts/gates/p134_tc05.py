"""TC-P134-05 Nonvisual interaction.

Host reference. Progress and stage expose usable names, values, and cancellation.
An unlabeled canvas as the only control is rejected. Spoken progress matches the
indeterminate or accounted/expected reading and never announces a false 100 percent.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P134-05",
    "phase": "P134",
    "workstream": 17,
    "name": "Nonvisual interaction",
    "intervention": "Perform the core phase task using accessibility navigation and spoken state information.",
    "expected": (
        "Expose usable names, order, values, and cancellation without relying only on color "
        "or precision gestures."
    ),
    "negative": "An unlabeled custom canvas as the only control must fail.",
    "repeat": "Repeat camera operation, ROI selection, focus editing, and recovery export.",
}

NEGATIVE_TOKEN = "unlabeled-canvas-only-control"
PROGRESS_NOT_SPOKEN = "spoken-progress-mismatch"
CONTROL_KEYS = {"name", "value", "cancellable"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "progress",
    "unlabeledCanvasOnly",
    "controls",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p134_design_transparent_progress_and_failure_states.py"
    spec = importlib.util.spec_from_file_location("p134_gate_for_tc05", path)
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


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    unlabeled = _GATE.require_bool(payload["unlabeledCanvasOnly"], "unlabeledCanvasOnly")
    controls, blank = _parse_controls(payload["controls"])
    expected_progress = _GATE.spoken_progress(bundle["info"])
    expected_stage = bundle["progress"]["stage"]
    progress_spoken = any(
        item["name"] == "progress" and item["value"] == expected_progress for item in controls
    )
    stage_spoken = any(item["name"] == "stage" and item["value"] == expected_stage for item in controls)
    cancellable = any(item["cancellable"] for item in controls)
    if unlabeled or blank or not controls or not cancellable:
        faults.append(NEGATIVE_TOKEN)
    if not progress_spoken or not stage_spoken:
        faults.append(PROGRESS_NOT_SPOKEN)
    extra = [{
        "unlabeledCanvasOnly": unlabeled,
        "controlOrder": [item["name"] for item in controls],
        "spokenProgress": expected_progress,
        "progressSpoken": progress_spoken,
        "stageSpoken": stage_spoken,
        "cancellable": cancellable,
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        PROGRESS_NOT_SPOKEN: "spoken progress must match indeterminate or accounted_frames/expected_frames",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
