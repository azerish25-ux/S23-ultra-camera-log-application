"""TC-P133-01 Landscape and large-text stress.

Host reference. Record, Stop, warnings, and source status stay in the focus
order and readable under large text. Critical actions hidden in scrolling
content are rejected. Focus order is preserved across orientation changes.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P133-01",
    "phase": "P133",
    "workstream": 17,
    "name": "Landscape and large-text stress",
    "intervention": "Open advanced controls with increased font scale in landscape during an active take.",
    "expected": "Keep Record or Stop, essential warnings, and selected source status reachable and readable.",
    "negative": "Critical actions hidden inside scrolling content must fail.",
    "repeat": "Repeat small display settings, orientation changes, and simultaneous audio and storage warnings.",
}

NEGATIVE_TOKEN = "critical-actions-hidden-in-scrolling-content"
FOCUS_DRIFT = "focus-order-not-preserved-across-layout"
CRITICAL_IDS = (
    "record",
    "stop",
    "source-status",
    "audio-warning",
    "storage-warning",
)
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "controls",
    "focusOrder",
    "fontScale",
    "orientation",
    "activeTake",
    "actionsHiddenInScroll",
    "baselineFocusOrder",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p133_implement_accessible_focus_and_recipe_controls.py"
    spec = importlib.util.spec_from_file_location("p133_gate_for_tc01", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_order(value: object, label: str) -> list[str]:
    _GATE.require(isinstance(value, list), label + " must be a list")
    order = []
    for index, item in enumerate(value):
        order.append(_GATE.require_text(item, f"{label}[{index}]"))
    return order


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    font_scale = _GATE.require_number(payload["fontScale"], "fontScale")
    _GATE.require(font_scale > 0, "fontScale must be positive")
    orientation = _GATE.require_text(payload["orientation"], "orientation")
    _GATE.require(orientation in {"landscape", "portrait"}, "orientation is not recognized")
    active_take = _GATE.require_bool(payload["activeTake"], "activeTake")
    hidden = _GATE.require_bool(payload["actionsHiddenInScroll"], "actionsHiddenInScroll")
    baseline = _parse_order(payload["baselineFocusOrder"], "baselineFocusOrder")
    controls = bundle["controls"]
    order = bundle["focusOrder"]
    readable = []
    for control_id in CRITICAL_IDS:
        control = _GATE.find_control(controls, control_id)
        named = control is not None and bool(control["accessible_name"]) and bool(control["state_description"])
        reachable = named and control_id in order and not hidden
        readable.append(reachable)
    if hidden or not all(readable):
        faults.append(NEGATIVE_TOKEN)
    if baseline != order:
        faults.append(FOCUS_DRIFT)
    extra = [{
        "fontScale": font_scale,
        "orientation": orientation,
        "activeTake": active_take,
        "actionsHiddenInScroll": hidden,
        "criticalReachable": all(readable) and not hidden,
        "focusPreserved": baseline == order,
        "minimumTargetSize": bundle["public"]["minimumTargetSize"],
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        FOCUS_DRIFT: "focus order must be preserved across panels and orientation changes",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
