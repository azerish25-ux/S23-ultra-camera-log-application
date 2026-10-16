"""TC-P123-05 Temporary storage exhaustion.

Host fixture. Required space is intermediate work plus duplicate publication
storage, not the final output alone. Insufficient space pauses or fails with
the source retained, recoverable artifacts, and an explicit cleanup choice.
"""

from __future__ import annotations


CASE_ID = "TC-P123-05"
NAME = "Temporary storage exhaustion"
INTERVENTION = "Make remaining space insufficient for intermediate work or duplicate publication storage."
EXPECTED = "Pause or fail safely before source loss, preserving recoverable artifacts and clear cleanup choices."
NEGATIVE = "Budgeting only final output bytes must fail."
REPEAT = "Repeat before rendering, during chunk assembly, and during gallery publication."
LEGAL_STATES = frozenset({"idle", "queued", "running", "checkpointed", "failed", "cancelled", "completed"})
ACTIONS = ("pause", "fail", "continue")
REPEATS = ("before-rendering", "chunk-assembly", "gallery-publication")
ACTION_STATE = {"pause": "checkpointed", "fail": "failed", "continue": "running"}
PAYLOAD_KEYS = (
    "evidenceId",
    "remainingBytes",
    "intermediateBytes",
    "publicationDuplicateBytes",
    "finalOutputBytes",
    "budgetedBytes",
    "action",
    "jobState",
    "sourceRetained",
    "recoverableArtifacts",
    "cleanupChoice",
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


def evaluate(payload: dict) -> dict:
    """Reject a final-output-only budget and any storage path that drops the source."""
    fields = _payload(payload)
    required = fields["intermediateBytes"] + fields["publicationDuplicateBytes"]
    short = fields["remainingBytes"] < required
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}", f"required bytes {required}"]
    budgets_only_final = fields["budgetedBytes"] <= fields["finalOutputBytes"] and fields["budgetedBytes"] < required
    if budgets_only_final:
        rejected.append("budget-only-final-output-bytes")
        reasons.append(NEGATIVE)
    if short and fields["action"] == "continue":
        rejected.append("continued-without-space")
        reasons.append("remaining space does not cover intermediate and publication bytes")
    if not short and fields["action"] != "continue":
        rejected.append("stopped-despite-sufficient-space")
        reasons.append("space covers the required bytes")
    if fields["jobState"] != ACTION_STATE[fields["action"]]:
        rejected.append("job-state-disagrees-with-storage-action")
        reasons.append("job state does not match pause, fail, or continue")
    if fields["action"] in {"pause", "fail"} and not fields["sourceRetained"]:
        rejected.append("source-deleted-on-storage-failure")
        reasons.append("do not delete the source on failure")
    if fields["action"] in {"pause", "fail"} and not fields["recoverableArtifacts"]:
        rejected.append("recoverable-artifacts-dropped")
        reasons.append("recoverable artifacts must be preserved")
    if fields["action"] in {"pause", "fail"} and not fields["cleanupChoice"]:
        rejected.append("cleanup-choice-missing")
        reasons.append("a clear cleanup choice is required")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("storage decision kept the source and matched the byte budget")
    preserved = [
        fields["evidenceId"],
        {
            "remainingBytes": fields["remainingBytes"],
            "requiredBytes": required,
            "budgetedBytes": fields["budgetedBytes"],
            "finalOutputBytes": fields["finalOutputBytes"],
            "sourceRetained": fields["sourceRetained"],
            "jobState": fields["jobState"],
            "action": fields["action"],
            "cleanupChoice": fields["cleanupChoice"],
        },
    ]
    return _result(decision, reasons, rejected, preserved, ["physical S23 capture was not run", REPEAT])


def _bytes(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    action = payload["action"]
    if action not in ACTIONS:
        raise ValueError("action is unsupported")
    state = payload["jobState"]
    if not isinstance(state, str) or state not in LEGAL_STATES:
        shown = state if isinstance(state, str) else type(state).__name__
        raise ValueError(f"unknown state name: {shown}")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    if type(payload["sourceRetained"]) is not bool or type(payload["recoverableArtifacts"]) is not bool:
        raise ValueError("flags must be bools")
    cleanup = payload["cleanupChoice"]
    if cleanup is not None and (not isinstance(cleanup, str) or cleanup != cleanup.strip()):
        raise ValueError("cleanupChoice must be a string or null")
    if isinstance(cleanup, str) and cleanup == "":
        cleanup = None
    return {
        "evidenceId": evidence,
        "remainingBytes": _bytes(payload["remainingBytes"], "remainingBytes"),
        "intermediateBytes": _bytes(payload["intermediateBytes"], "intermediateBytes"),
        "publicationDuplicateBytes": _bytes(payload["publicationDuplicateBytes"], "publicationDuplicateBytes"),
        "finalOutputBytes": _bytes(payload["finalOutputBytes"], "finalOutputBytes"),
        "budgetedBytes": _bytes(payload["budgetedBytes"], "budgetedBytes"),
        "action": action,
        "jobState": state,
        "sourceRetained": payload["sourceRetained"],
        "recoverableArtifacts": payload["recoverableArtifacts"],
        "cleanupChoice": cleanup,
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
