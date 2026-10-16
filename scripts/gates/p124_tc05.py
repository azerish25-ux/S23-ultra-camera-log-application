"""TC-P124-05 Temporary storage exhaustion.

Host fixture. Intermediate bytes are part of the budget. The job pauses or
fails before source loss when remaining space cannot hold that work.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P124-05"
NAME = "Temporary storage exhaustion"
INTERVENTION = "Make remaining space insufficient for intermediate work or duplicate publication storage."
EXPECTED = "Pause or fail safely before source loss, preserving recoverable artifacts and clear cleanup choices."
NEGATIVE = "Budgeting only final output bytes must fail."
REPEAT = "Repeat before rendering, during chunk assembly, and during gallery publication."
BUDGET_FINAL_ONLY = "budget-only-final-output-bytes"
SOURCE_LOSS = "source-loss"
NOT_RECOVERABLE = "artifacts-not-recoverable"
CONTINUED = "continued-under-exhaustion"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "phase",
    "remainingBytes",
    "intermediateBytes",
    "finalOutputBytes",
    "budgetedBytes",
    "sourcePreserved",
    "recoverableArtifacts",
    "action",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
PHASES = ("before-render", "chunk-assembly", "gallery-publication")

_SPEC = importlib.util.spec_from_file_location(
    "p124_checkpoint_temporal_rendering_safely",
    Path(__file__).resolve().parent / "p124_checkpoint_temporal_rendering_safely.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _count(value, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be an int >= 0")
    return value


def _bool(value, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    phase = payload["phase"]
    if phase not in PHASES:
        raise ValueError("phase is invalid")
    remaining = _count(payload["remainingBytes"], "remainingBytes")
    intermediate = _count(payload["intermediateBytes"], "intermediateBytes")
    final_bytes = _count(payload["finalOutputBytes"], "finalOutputBytes")
    budgeted = _count(payload["budgetedBytes"], "budgetedBytes")
    source_preserved = _bool(payload["sourcePreserved"], "sourcePreserved")
    recoverable = _bool(payload["recoverableArtifacts"], "recoverableArtifacts")
    action = payload["action"]
    if action not in {"continue", "pause", "fail"}:
        raise ValueError("action must be continue, pause, or fail")

    required = intermediate + final_bytes
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        INTERVENTION,
        f"requiredBytes={required}",
        f"budgetedBytes={budgeted}",
        "phase=" + phase,
    ]
    rejected: list[str] = []
    if intermediate > 0 and budgeted == final_bytes:
        rejected.append(BUDGET_FINAL_ONLY)
        reasons.append(NEGATIVE)
    if remaining < required and not source_preserved:
        rejected.append(SOURCE_LOSS)
        reasons.append("storage exhaustion must not lose the source")
    if remaining < required and not recoverable:
        rejected.append(NOT_RECOVERABLE)
        reasons.append("recoverable artifacts were not preserved")
    if remaining < required and action == "continue":
        rejected.append(CONTINUED)
        reasons.append("work continued without room for intermediate bytes")
    if remaining < required and action in {"pause", "fail"} and source_preserved and recoverable:
        reasons.append(action + " before source loss")
    if remaining >= required and source_preserved and recoverable and BUDGET_FINAL_ONLY not in rejected:
        reasons.append("remaining space covers intermediate and final bytes")
    decision = "rejected" if rejected else "recorded"
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, f"requiredBytes={required}", "phase=" + phase],
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    return _CORE.seal(result)
