"""TC-P133-03 Invalid control draft.

Host reference. An incomplete or out-of-range numeric draft stays unapplied.
Partially typed input that reaches the camera, or replaces a control's spoken
state, is rejected. Committed control state stays in the preserved surface.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P133-03",
    "phase": "P133",
    "workstream": 17,
    "name": "Invalid control draft",
    "intervention": "Enter an incomplete or out-of-range numeric value and interrupt editing before Apply.",
    "expected": "Preserve committed settings and keep the draft visibly unapplied or invalid.",
    "negative": "Partially typed input reaching the camera must fail.",
    "repeat": "Repeat shutter, ISO, focus distance, ROI coordinates, and output dimensions.",
}

NEGATIVE_TOKEN = "partial-draft-reached-camera"
OUT_OF_RANGE = "out-of-range-draft-applied"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "controls",
    "focusOrder",
    "controlId",
    "committedState",
    "draftText",
    "draftApplied",
    "draftMinimum",
    "draftMaximum",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p133_implement_accessible_focus_and_recipe_controls.py"
    spec = importlib.util.spec_from_file_location("p133_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    control_id = _GATE.require_text(payload["controlId"], "controlId")
    committed_state = _GATE.require_text(payload["committedState"], "committedState")
    value, kind = _GATE.parse_complete_number(payload["draftText"], "draftText")
    applied = _GATE.require_bool(payload["draftApplied"], "draftApplied")
    minimum = _GATE.require_number(payload["draftMinimum"], "draftMinimum")
    maximum = _GATE.require_number(payload["draftMaximum"], "draftMaximum")
    _GATE.require(minimum <= maximum, "draft range is inverted")
    control = _GATE.find_control(bundle["controls"], control_id)
    _GATE.require(control is not None, "controlId is not on the surface")
    state = control["state_description"]
    partial_reached = kind != "complete" and (applied or state == payload["draftText"].strip())
    out_of_range = kind == "complete" and applied and (value < minimum or value > maximum)
    state_replaced = state != committed_state and (kind != "complete" or out_of_range or not applied)
    if partial_reached or (kind != "complete" and state != committed_state):
        faults.append(NEGATIVE_TOKEN)
    if out_of_range or (kind == "complete" and (value < minimum or value > maximum) and state != committed_state):
        faults.append(OUT_OF_RANGE)
    if state_replaced and NEGATIVE_TOKEN not in faults and OUT_OF_RANGE not in faults:
        faults.append(NEGATIVE_TOKEN)
    extra = [{
        "controlId": control_id,
        "committedState": committed_state,
        "spokenState": state,
        "draftKind": kind,
        "draftApplied": applied,
        "draftValue": value,
        "draftMinimum": minimum,
        "draftMaximum": maximum,
        "draftVisibleUnapplied": not applied and state == committed_state,
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        OUT_OF_RANGE: "an out-of-range draft must not reach the camera",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
