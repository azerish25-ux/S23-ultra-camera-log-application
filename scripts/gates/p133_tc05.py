"""TC-P133-05 Nonvisual interaction.

Host reference. Names, focus order, spoken values, and cancellation come from
the control surface itself. An unlabeled canvas is rejected by that audit.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P133-05",
    "phase": "P133",
    "workstream": 17,
    "name": "Nonvisual interaction",
    "intervention": "Perform the core phase task using accessibility navigation and spoken state information.",
    "expected": "Expose usable names, order, values, and cancellation without relying only on color or precision gestures.",
    "negative": "An unlabeled custom canvas as the only control must fail.",
    "repeat": "Repeat camera operation, ROI selection, focus editing, and recovery export.",
}

NEGATIVE_TOKEN = "unlabeled-canvas-only-control"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "controls",
    "focusOrder",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p133_implement_accessible_focus_and_recipe_controls.py"
    spec = importlib.util.spec_from_file_location("p133_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    controls = bundle["controls"]
    names = [control["accessible_name"] for control in controls]
    states = [control["state_description"] for control in controls]
    if not names or any(not name for name in names) or any(not state for state in states):
        if NEGATIVE_TOKEN not in faults:
            faults.append(NEGATIVE_TOKEN)
    if not bundle["info"]["cancelAvailable"]:
        if _GATE.CANCEL_UNAVAILABLE not in faults:
            faults.append(_GATE.CANCEL_UNAVAILABLE)
    color_only = [control["id"] for control in controls if control["color_only_failure"]]
    gesture_only = [
        control["id"] for control in controls if control["path"] not in _GATE.NON_GESTURE_PATHS
    ]
    extra = [{
        "names": names,
        "states": states,
        "focusOrder": list(bundle["focusOrder"]),
        "cancelAvailable": bundle["info"]["cancelAvailable"],
        "colorOnlyIds": color_only,
        "gestureOnlyIds": gesture_only,
        "minimumTargetSize": bundle["public"]["minimumTargetSize"],
        "recipeSeparate": bundle["public"]["recipeSeparate"],
    }]
    texts = {NEGATIVE_TOKEN: CASE["negative"]}
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
