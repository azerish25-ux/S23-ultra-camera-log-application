"""TC-P131-08 Real shooting interruption.

Host reference. A desktop mockup cannot stand in for a physical S23 task.
The surviving applied value and source configuration stay disclosed. This
case does not observe the phone.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P131-08",
    "phase": "P131",
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
    "committed",
    "proposed",
    "physicalObserved",
    "desktopMockupSubstituted",
    "savedStateText",
    "interruption",
    "nextAction",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p131_design_manual_controls_for_deliberate_operation.py"
    spec = importlib.util.spec_from_file_location("p131_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    physical = _GATE.require_bool(payload["physicalObserved"], "physicalObserved")
    mockup = _GATE.require_bool(payload["desktopMockupSubstituted"], "desktopMockupSubstituted")
    saved = _GATE.require_text(payload["savedStateText"], "savedStateText")
    interruption = _GATE.require_text(payload["interruption"], "interruption")
    _GATE.require(interruption in INTERRUPTIONS, "interruption is not recognized")
    action = _GATE.require_text(payload["nextAction"], "nextAction")
    applied_text = _GATE.format_number(bundle["info"]["surviving"])
    source = bundle["committed"]["source_configuration"]
    if mockup:
        faults.append(NEGATIVE_TOKEN)
    if physical:
        faults.append(UNOBSERVED)
    if applied_text not in saved or source not in saved:
        faults.append(HIDDEN_SAVE)
    extra = [{
        "physicalObserved": physical,
        "desktopMockupSubstituted": mockup,
        "savedStateText": saved,
        "interruption": interruption,
        "nextAction": action,
        "applied": bundle["info"]["surviving"],
        "source_configuration": source,
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        UNOBSERVED: "this host reference did not observe physical task completion",
        HIDDEN_SAVE: "saved applied value and source configuration must stay visible",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
