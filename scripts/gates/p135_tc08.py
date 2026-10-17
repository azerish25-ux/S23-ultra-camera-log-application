"""TC-P135-08 Real shooting interruption.

Host fixture. A desktop mockup cannot stand in for a physical S23 task.
Saved comparison state stays disclosed. This case does not observe the phone.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P135-08",
    "phase": "P135",
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
    "comparison",
    "physicalObserved",
    "desktopMockupSubstituted",
    "savedComparisonDisclosed",
    "interruption",
    "nextAction",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p135_build_side_by_side_comparison_tools.py"
    spec = importlib.util.spec_from_file_location("p135_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    physical = _GATE.require_bool(payload["physicalObserved"], "physicalObserved")
    mockup = _GATE.require_bool(payload["desktopMockupSubstituted"], "desktopMockupSubstituted")
    disclosed = _GATE.require_bool(payload["savedComparisonDisclosed"], "savedComparisonDisclosed")
    interruption = _GATE.require_text(payload["interruption"], "interruption")
    _GATE.require(interruption in INTERRUPTIONS, "interruption is not recognized")
    action = _GATE.require_text(payload["nextAction"], "nextAction")
    if mockup:
        faults.append(NEGATIVE_TOKEN)
    if physical:
        faults.append(UNOBSERVED)
    if not disclosed:
        faults.append(HIDDEN_SAVE)
    extra = [{
        "physicalObserved": physical,
        "desktopMockupSubstituted": mockup,
        "savedComparisonDisclosed": disclosed,
        "interruption": interruption,
        "nextAction": action,
        "matchedInputs": bundle["info"]["matchedInputs"],
        "source_sha256": bundle["comparison"]["left"]["source_sha256"],
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        UNOBSERVED: "this host fixture did not observe physical task completion",
        HIDDEN_SAVE: "saved comparison state must stay visible after an interruption",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
