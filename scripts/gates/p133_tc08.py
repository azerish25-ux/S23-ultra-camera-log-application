"""TC-P133-08 Real shooting interruption.

Host reference. A desktop mockup cannot stand in for a physical S23 task.
What was saved must be spoken by a labeled control. This case does not observe
the phone.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P133-08",
    "phase": "P133",
    "workstream": 17,
    "name": "Real shooting interruption",
    "intervention": "Perform the task on the physical phone with a thermal warning, permission issue, or recovery event.",
    "expected": "Let the user understand what was saved and complete the appropriate next action without hidden state.",
    "negative": "A desktop mockup cannot substitute for observed physical task completion.",
    "repeat": "Repeat one-handed operation, outdoor visibility, and finding an interrupted take.",
}

NEGATIVE_TOKEN = "desktop-mockup-substitutes-for-physical-completion"
UNOBSERVED = "unobserved-physical-completion-claimed"
HIDDEN_SAVE = "hidden-saved-state"
INTERRUPTIONS = frozenset({"thermal", "permission", "recovery", "none"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "controls",
    "focusOrder",
    "physicalObserved",
    "desktopMockupSubstituted",
    "savedStateDisclosed",
    "savedStateText",
    "interruption",
    "nextAction",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p133_implement_accessible_focus_and_recipe_controls.py"
    spec = importlib.util.spec_from_file_location("p133_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    physical = _GATE.require_bool(payload["physicalObserved"], "physicalObserved")
    mockup = _GATE.require_bool(payload["desktopMockupSubstituted"], "desktopMockupSubstituted")
    disclosed = _GATE.require_bool(payload["savedStateDisclosed"], "savedStateDisclosed")
    saved_text = _GATE.require_text(payload["savedStateText"], "savedStateText")
    interruption = _GATE.require_text(payload["interruption"], "interruption")
    _GATE.require(interruption in INTERRUPTIONS, "interruption is not recognized")
    action = _GATE.require_text(payload["nextAction"], "nextAction")
    announced = any(control["state_description"] == saved_text for control in bundle["controls"])
    if mockup:
        faults.append(NEGATIVE_TOKEN)
    if physical:
        faults.append(UNOBSERVED)
    if not disclosed or not announced:
        faults.append(HIDDEN_SAVE)
    extra = [{
        "physicalObserved": physical,
        "desktopMockupSubstituted": mockup,
        "savedStateDisclosed": disclosed,
        "savedStateText": saved_text,
        "savedStateAnnounced": announced,
        "interruption": interruption,
        "nextAction": action,
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        UNOBSERVED: "this host reference did not observe physical task completion",
        HIDDEN_SAVE: "saved state must stay visible after an interruption",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
