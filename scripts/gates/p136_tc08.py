"""TC-P136-08 Real shooting interruption.

Host fixture. A desktop mockup cannot substitute for observed physical task
completion. This module does not invent a shooting workflow, saved footage,
or a next action that was not observed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p136_run_usability_acceptance_on_the_physical_phone",
    Path(__file__).resolve().parent / "p136_run_usability_acceptance_on_the_physical_phone.py",
)
_GATE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_GATE)

CASE = {
    "id": "TC-P136-08",
    "phase": "P136",
    "workstream": 17,
    "name": "Real shooting interruption",
    "intervention": "Perform the task on the physical phone with a thermal warning, permission issue, or recovery event.",
    "expected": "Let the user understand what was saved and complete the appropriate next action without hidden state.",
    "negative": "A desktop mockup cannot substitute for observed physical task completion.",
    "repeat": "Repeat one-handed operation, outdoor visibility, and finding an interrupted take.",
}
NEGATIVE_TOKEN = "desktop-mockup-substituted-for-physical-task"
INVENTED_WORKFLOW = "invented-shooting-workflow"
HIDDEN_STATE = "hidden-footage-state"
FOOTAGE_WITHOUT_WORKFLOW = "footage-result-without-observed-workflow"
EVENTS = frozenset({"thermal", "permission", "recovery"})
PAYLOAD_KEYS = {
    "evidenceId",
    "repeat",
    "report",
    "event",
    "footageSavedKnown",
    "nextActionKnown",
    "hiddenState",
    "desktopMockupSubstituted",
    "workflowObserved",
}


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    report = _GATE.parse_report(payload["report"])
    event = _GATE.require_text(payload["event"], "event")
    _GATE.require(event in EVENTS, "event must be thermal, permission, or recovery")
    footage = _GATE.require_bool(payload["footageSavedKnown"], "footageSavedKnown")
    next_action = _GATE.require_bool(payload["nextActionKnown"], "nextActionKnown")
    hidden = _GATE.require_bool(payload["hiddenState"], "hiddenState")
    mockup = _GATE.require_bool(payload["desktopMockupSubstituted"], "desktopMockupSubstituted")
    observed = _GATE.require_bool(payload["workflowObserved"], "workflowObserved")
    faults = []
    if mockup:
        faults.append(NEGATIVE_TOKEN)
    if observed:
        faults.append(INVENTED_WORKFLOW)
    if hidden:
        faults.append(HIDDEN_STATE)
    if not observed and (footage or next_action):
        faults.append(FOOTAGE_WITHOUT_WORKFLOW)
    reasons = [
        f"plannedEvent={event} workflowObserved={str(observed).lower()}",
        f"footageSavedKnown={str(footage).lower()} nextActionKnown={str(next_action).lower()} hiddenState={str(hidden).lower()}",
        "shooting workflow result was not invented",
    ]
    preserved = [{
        "plannedEvent": event,
        "workflowObserved": observed,
        "footageSavedKnown": footage,
        "nextActionKnown": next_action,
        "hiddenState": hidden,
        "desktopMockupSubstituted": mockup,
        "shootingWorkflow": None,
    }]
    return _GATE.finish_tc(
        CASE,
        evidence,
        repeat,
        report,
        faults,
        reasons,
        preserved,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            INVENTED_WORKFLOW: "Do not invent a shooting workflow result.",
            HIDDEN_STATE: CASE["expected"],
            FOOTAGE_WITHOUT_WORKFLOW: "Do not invent whether footage was saved without an observed workflow.",
        },
        {
            NEGATIVE_TOKEN: "Do not substitute a desktop mockup for observed physical task completion.",
            INVENTED_WORKFLOW: "Do not invent a shooting workflow result.",
            HIDDEN_STATE: "Do not hide whether footage was saved.",
            FOOTAGE_WITHOUT_WORKFLOW: "Do not claim a footage or next-action result that was not observed.",
        },
    )
