"""TC-P123-04 Cancellation at acceptance boundary.

Host fixture. Cancellation during rendering, verification, publication, or
cleanup is acknowledged only after workers release ownership and the source
stays retained. A cancelled job is not published as accepted. A late worker
callback cannot reverse cancellation.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_ID = "TC-P123-04"
NAME = "Cancellation at acceptance boundary"
INTERVENTION = "Cancel during rendering, verification, publication, or final cleanup."
EXPECTED = "Acknowledge cancellation only after ownership is controlled and never publish a cancelled job as accepted."
NEGATIVE = "A late worker callback that reverses cancellation must fail."
REPEAT = "Repeat with process restart and an already retained partial output."
PHASES = ("rendering", "verification", "publication", "cleanup")
REPEATS = ("process-restart", "retained-partial-output")
PAYLOAD_KEYS = (
    "evidenceId",
    "phaseAtCancel",
    "transitionLog",
    "terminalState",
    "sourceRetained",
    "workersReleased",
    "lateCallback",
    "publishedAccepted",
    "partialRetained",
    "repeat",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _machine():
    path = Path(__file__).resolve().parent / "p123_implement_the_development_job_state_machine.py"
    spec = importlib.util.spec_from_file_location("p123_implement_the_development_job_state_machine", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate(payload: dict) -> dict:
    """Reject early cancellation, accepted publication, and reversing callbacks."""
    fields = _payload(payload)
    machine = _machine()
    inspected = machine.inspect_transitions(fields["transitionLog"], fields["terminalState"], fields["sourceRetained"])
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}", f"phase {fields['phaseAtCancel']}"]
    if inspected["illegal"]:
        rejected.append("illegal-transition")
        reasons.append("illegal transition in the cancellation log")
    if inspected["skippedQueuedToCompleted"]:
        rejected.append("skipped-queued-to-completed")
        reasons.append("skipping queued->completed is rejected")
    if inspected["terminalMismatch"]:
        rejected.append("terminal-state-mismatch")
        reasons.append("terminal state does not match the last log entry")
    if inspected["cancelWithoutSource"]:
        rejected.append("source-not-retained-on-cancel")
        reasons.append("cancel from running must set source_retained true")
    if inspected["failureDeletesSource"]:
        rejected.append("source-deleted-on-failure")
        reasons.append("do not delete the source on failure")
    log = inspected["log"]
    cancel_from = [src for src, dst in zip(log, log[1:]) if dst == "cancelled"]
    if not cancel_from or inspected["terminal"] != "cancelled":
        rejected.append("cancellation-not-terminal")
        reasons.append("cancellation must be the terminal state")
    if any(src != "running" for src in cancel_from):
        rejected.append("phase-not-running-at-acceptance-boundary")
        reasons.append("acceptance-boundary cancellation leaves the running state")
    if not fields["workersReleased"]:
        rejected.append("cancellation-before-workers-released")
        reasons.append(machine.MUTANT)
    if fields["publishedAccepted"]:
        rejected.append("cancelled-job-published-as-accepted")
        reasons.append("a cancelled job was published as accepted")
    if fields["lateCallback"] is not None:
        rejected.append("late-worker-reverses-cancellation")
        reasons.append(NEGATIVE)
        pair = ("cancelled", fields["lateCallback"])
        if pair not in machine.LEGAL_TRANSITIONS:
            reasons.append(f"late callback {fields['lateCallback']} is not a legal transition from cancelled")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("cancellation acknowledged after workers released ownership; source retained")
    preserved = [
        fields["evidenceId"],
        list(log),
        inspected["terminal"],
        {
            "sourceRetained": fields["sourceRetained"],
            "workersReleased": fields["workersReleased"],
            "partialRetained": fields["partialRetained"],
            "publishedAccepted": fields["publishedAccepted"],
            "lateCallback": fields["lateCallback"],
            "phaseAtCancel": fields["phaseAtCancel"],
        },
    ]
    return _result(decision, reasons, rejected, preserved, ["physical S23 capture was not run", REPEAT])


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    phase = payload["phaseAtCancel"]
    if phase not in PHASES:
        raise ValueError("phaseAtCancel is unsupported")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    late = payload["lateCallback"]
    if late is not None:
        machine = _machine()
        if not isinstance(late, str) or late not in machine.LEGAL_STATES:
            shown = late if isinstance(late, str) else type(late).__name__
            raise ValueError(f"unknown state name: {shown}")
    partial = _bool(payload["partialRetained"], "partialRetained")
    if repeat == "retained-partial-output" and not partial:
        raise ValueError("retained-partial-output repeat requires partialRetained")
    return {
        "evidenceId": evidence,
        "phaseAtCancel": phase,
        "transitionLog": payload["transitionLog"],
        "terminalState": payload["terminalState"],
        "sourceRetained": _bool(payload["sourceRetained"], "sourceRetained"),
        "workersReleased": _bool(payload["workersReleased"], "workersReleased"),
        "lateCallback": late,
        "publishedAccepted": _bool(payload["publishedAccepted"], "publishedAccepted"),
        "partialRetained": partial,
        "repeat": repeat,
    }


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if not reasons or not preserved or preserved[0] not in preserved:
        raise ValueError("evidence wiped")
    return result
