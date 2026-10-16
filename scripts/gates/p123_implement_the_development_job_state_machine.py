#!/usr/bin/env python3
"""P123 Implement the development job state machine.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P123-01 through TC-P123-08 modules.

Legal states are idle, queued, running, checkpointed, failed, cancelled, and
completed. A transition log is accepted only when every adjacent step is in
the legal set and the declared terminal state is the last entry. Cancellation
with source_retained false is rejected. Failure must not delete the source.
The goal names preparing, rendering, verifying, and publishing are not extra
states; those names raise ValueError.
"""

from __future__ import annotations

from typing import Any


BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P123"
TITLE = "Implement the development job state machine"
WORKSTREAM = 16
DEPENDENCIES = ("P122",)
GOAL = "Make queued, preparing, rendering, verifying, publishing, cancelled, and failed states explicit."
METHOD = (
    "Own jobs independently of the screen while respecting Android execution policy. "
    "Record resource requirements, current phase, progress confidence, and failure reason. "
    "Cancellation is acknowledged only after workers release ownership and retain appropriate partial artifacts."
)
FIXTURE = "Cancellation during output verification followed by reopening the development screen."
ORACLE = (
    "The job state is consistent, source media remains intact, and a stale worker cannot publish a cancelled result."
)
MUTANT = "Mark cancellation complete immediately while background workers still own output handles."
DELIVERABLE = "Job reducer and cancellation race tests"

LEGAL_STATE_ORDER = (
    "idle",
    "queued",
    "running",
    "checkpointed",
    "failed",
    "cancelled",
    "completed",
)
LEGAL_STATES = frozenset(LEGAL_STATE_ORDER)
LEGAL_TRANSITION_LIST = (
    ("idle", "queued"),
    ("queued", "running"),
    ("running", "checkpointed"),
    ("checkpointed", "running"),
    ("running", "completed"),
    ("running", "failed"),
    ("running", "cancelled"),
    ("queued", "cancelled"),
    ("checkpointed", "cancelled"),
    ("checkpointed", "failed"),
)
LEGAL_TRANSITIONS = frozenset(LEGAL_TRANSITION_LIST)
CANCEL_FROM = frozenset({"running", "queued"})

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "transitionLog",
    "terminalState",
    "sourceRetained",
    "workersReleased",
    "stalePublish",
    "applyMutant",
}
EVALUATE_KEYS = {
    "caseId",
    "evidenceId",
    "claim",
    "transitionLog",
    "terminalState",
    "sourceRetained",
    "workersReleased",
    "stalePublish",
    "applyMutant",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _identity(value: object, label: str) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(), f"{label} must be a non-empty string")
    return value


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, f"{label} must be a bool")
    return value


def _state(value: object, label: str) -> str:
    if not isinstance(value, str) or value not in LEGAL_STATES:
        shown = value if isinstance(value, str) else type(value).__name__
        raise ValueError(f"unknown state name: {shown}")
    return value


def _reject(bucket: list[str], token: str) -> None:
    if token not in bucket:
        bucket.append(token)


def inspect_transitions(
    transition_log: object,
    terminal_state: object,
    source_retained: bool,
) -> dict[str, Any]:
    """Validate a whole transition log.

    Unknown state names raise ValueError. Illegal pairs, a terminal that does
    not match the last entry, cancellation without source_retained, and a
    failure that deletes the source are reported rather than repaired.
    """
    require(isinstance(transition_log, list) and len(transition_log) > 0, "transition log must be a non-empty list of states")
    log = [_state(item, f"transitionLog[{index}]") for index, item in enumerate(transition_log)]
    terminal = _state(terminal_state, "terminalState")
    require(type(source_retained) is bool, "sourceRetained must be a bool")
    illegal: list[list[str]] = []
    skipped = False
    for index in range(len(log) - 1):
        pair = (log[index], log[index + 1])
        if pair not in LEGAL_TRANSITIONS:
            illegal.append([pair[0], pair[1]])
            if pair == ("queued", "completed"):
                skipped = True
    saw_cancel = terminal == "cancelled" or any(state == "cancelled" for state in log)
    saw_fail = terminal == "failed" or any(state == "failed" for state in log)
    cancel_from_running_or_queued = any(
        src in CANCEL_FROM and dst == "cancelled" for src, dst in zip(log, log[1:])
    )
    return {
        "log": log,
        "terminal": terminal,
        "illegal": illegal,
        "skippedQueuedToCompleted": skipped,
        "terminalMismatch": terminal != log[-1],
        "cancelWithoutSource": saw_cancel and source_retained is False,
        "cancelFromRunningOrQueued": cancel_from_running_or_queued,
        "failureDeletesSource": saw_fail and source_retained is False,
    }


def _seal(result: dict[str, Any]) -> dict[str, Any]:
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(result["decision"] in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(isinstance(result["reasons"], list) and result["reasons"], "reasons must be non-empty")
    require(isinstance(result["rejectedClaims"], list), "rejectedClaims must be a list")
    require(isinstance(result["preservedResults"], list) and result["preservedResults"], "evidence wiped")
    require(isinstance(result["openQuestions"], list) and result["openQuestions"], "openQuestions must be non-empty")
    evidence = result["preservedResults"][0]
    require(isinstance(evidence, str) and evidence in result["preservedResults"], "evidence must be preserved")
    require(any("physical S23" in item for item in result["openQuestions"]), "physical S23 was not noted")
    return result


def decide_job(
    *,
    case_id: str,
    evidence_id: str,
    claim: str,
    transition_log: object,
    terminal_state: object,
    source_retained: bool,
    workers_released: bool,
    stale_publish: bool,
    apply_mutant: bool,
) -> dict[str, Any]:
    """Record the log only when every step is legal and the terminal matches.

    source_retained false on cancel is rejected. Cancel from running or queued
    must keep the source. Failure does not delete the source. A stale worker
    must not publish a cancelled result, and cancellation is not complete while
    workers still own output handles.
    """
    inspected = inspect_transitions(transition_log, terminal_state, source_retained)
    require(type(workers_released) is bool, "workersReleased must be a bool")
    require(type(stale_publish) is bool, "stalePublish must be a bool")
    require(type(apply_mutant) is bool, "applyMutant must be a bool")
    log = inspected["log"]
    terminal = inspected["terminal"]
    rejected: list[str] = []
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "fixture: " + FIXTURE,
    ]
    if inspected["illegal"]:
        _reject(rejected, "illegal-transition")
        rendered = ", ".join(f"{src}->{dst}" for src, dst in inspected["illegal"])
        reasons.append("illegal transition rejected: " + rendered)
    if inspected["skippedQueuedToCompleted"]:
        _reject(rejected, "skipped-queued-to-completed")
        reasons.append("skipping queued->completed is rejected")
    if inspected["terminalMismatch"]:
        _reject(rejected, "terminal-state-mismatch")
        reasons.append(f"terminal state {terminal} does not match last log entry {log[-1]}")
    if inspected["cancelWithoutSource"]:
        _reject(rejected, "source-not-retained-on-cancel")
        reasons.append("source_retained false on cancel is rejected")
        if inspected["cancelFromRunningOrQueued"]:
            reasons.append("cancel from running or queued must set source_retained true")
    if inspected["failureDeletesSource"]:
        _reject(rejected, "source-deleted-on-failure")
        reasons.append("do not delete the source on failure")
    cancelled = terminal == "cancelled" or any(state == "cancelled" for state in log)
    if cancelled and not workers_released:
        _reject(rejected, "workers-still-own-output-handles")
        reasons.append("cancellation is not acknowledged while workers own output handles")
    if stale_publish and cancelled:
        _reject(rejected, "stale-worker-published-cancelled-result")
        reasons.append("a stale worker cannot publish a cancelled result")
    elif stale_publish:
        _reject(rejected, "stale-worker-publish")
        reasons.append("a stale worker publish is rejected")
    if apply_mutant:
        _reject(rejected, MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
    if rejected:
        decision = "rejected"
    else:
        decision = "recorded"
        reasons.append("every transition is legal and the terminal state matches the last entry")
        reasons.append("source media remains intact for " + evidence_id)
        reasons.append("method: " + METHOD)
    questions = [
        "physical S23 capture was not run",
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
    ]
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [
            evidence_id,
            claim,
            list(log),
            terminal,
            source_retained,
            {
                "workersReleased": workers_released,
                "stalePublish": stale_publish,
                "illegalTransitions": inspected["illegal"],
            },
        ],
        "openQuestions": questions,
    }
    return _seal(result)


def _components(payload: dict) -> tuple:
    evidence = _identity(payload["evidenceId"], "evidenceId")
    claim = _identity(payload["claim"], "claim")
    source_retained = _bool(payload["sourceRetained"], "sourceRetained")
    workers_released = _bool(payload["workersReleased"], "workersReleased")
    stale_publish = _bool(payload["stalePublish"], "stalePublish")
    apply_mutant = _bool(payload["applyMutant"], "applyMutant")
    return (
        evidence,
        claim,
        payload["transitionLog"],
        payload["terminalState"],
        source_retained,
        workers_released,
        stale_publish,
        apply_mutant,
    )


def assess(document: dict) -> dict[str, Any]:
    """Apply the job-state oracle to one host fixture."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence, claim, log, terminal, source_retained, workers_released, stale_publish, apply_mutant = _components(document)
    return decide_job(
        case_id=PHASE,
        evidence_id=evidence,
        claim=claim,
        transition_log=log,
        terminal_state=terminal,
        source_retained=source_retained,
        workers_released=workers_released,
        stale_publish=stale_publish,
        apply_mutant=apply_mutant,
    )


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate one transition log. Unknown state names raise ValueError."""
    require(isinstance(payload, dict), "payload must be an object")
    missing = EVALUATE_KEYS - set(payload)
    extra = set(payload) - EVALUATE_KEYS
    require(not missing, "payload missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))
    case_id = _identity(payload["caseId"], "caseId")
    evidence, claim, log, terminal, source_retained, workers_released, stale_publish, apply_mutant = _components(payload)
    return decide_job(
        case_id=case_id,
        evidence_id=evidence,
        claim=claim,
        transition_log=log,
        terminal_state=terminal,
        source_retained=source_retained,
        workers_released=workers_released,
        stale_publish=stale_publish,
        apply_mutant=apply_mutant,
    )
