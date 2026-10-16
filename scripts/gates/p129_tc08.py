"""TC-P129-08 Real shooting interruption.

Host fixture. Saved state and the next action stay visible. A desktop mockup
cannot substitute for observed physical task completion, and this host run
does not qualify a physical S23.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_ID = "TC-P129-08"
NAME = "Real shooting interruption"
INTERVENTION = "Perform the task on the physical phone with a thermal warning, permission issue, or recovery event."
EXPECTED = "Let the user understand what was saved and complete the appropriate next action without hidden state."
NEGATIVE = "A desktop mockup cannot substitute for observed physical task completion."
REPEAT = "Repeat one-handed operation, outdoor visibility, and finding an interrupted take."
NEGATIVE_TOKEN = "desktop-mockup-substitutes-for-physical"
HIDDEN_STATE = "hidden-interruption-state"
WARNING_MISSING = "interruption-warning-not-listed"
EVENTS = frozenset({"thermal", "permission", "recovery"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "event",
    "savedVisible",
    "nextActionVisible",
    "hiddenState",
    "mockupSubstitutesForPhysical",
    "capture",
    "monitoring",
    "processing",
    "warnings",
    "record_in_scroll_only",
    "warnings_visible",
)

_SPEC = importlib.util.spec_from_file_location(
    "p129_define_the_camera_screen_information_hierarchy",
    Path(__file__).resolve().parent / "p129_define_the_camera_screen_information_hierarchy.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    event = _text(payload["event"], "event")
    if event not in EVENTS:
        raise ValueError("event must be thermal, permission, or recovery")
    saved = _bool(payload["savedVisible"], "savedVisible")
    next_action = _bool(payload["nextActionVisible"], "nextActionVisible")
    hidden = _bool(payload["hiddenState"], "hiddenState")
    mockup = _bool(payload["mockupSubstitutesForPhysical"], "mockupSubstitutesForPhysical")
    judged = _CORE.judge_hierarchy(
        payload["capture"],
        payload["monitoring"],
        payload["processing"],
        payload["warnings"],
        payload["record_in_scroll_only"],
        payload["warnings_visible"],
    )
    rejected = list(judged["rejectedClaims"])
    reasons = [
        f"{CASE_ID} {NAME}",
        EXPECTED,
        INTERVENTION,
        f"repeat {repeat}",
        f"event={event}",
        "host fixture does not substitute for physical S23 task completion",
    ]
    reasons.extend(judged["reasons"])
    if mockup:
        _add(rejected, NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if (not saved) or (not next_action) or hidden:
        _add(rejected, HIDDEN_STATE)
        reasons.append("saved state or the next action is hidden")
    if event in {"thermal", "permission"} and event not in judged["warningKinds"]:
        _add(rejected, WARNING_MISSING)
        reasons.append(f"{event} warning is not listed")
    if not rejected:
        reasons.append("saved state and the next action are visible; physical completion is not claimed")
    decision = "rejected" if rejected else "recorded"
    if decision in {"qualified", "allowed"}:
        raise ValueError("decision cannot be qualified")
    preserved = [evidence, f"event={event}", f"savedVisible={str(saved).lower()}"]
    preserved.extend(judged["preservedResults"])
    questions = [
        _CORE.PHYSICAL_NOTE,
        "desktop mockup is not observed physical task completion",
        REPEAT,
    ]
    return _CORE.seal_result(CASE_ID, decision, reasons, rejected, preserved, questions, evidence)
