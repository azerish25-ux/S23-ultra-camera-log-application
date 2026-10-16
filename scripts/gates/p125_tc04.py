"""TC-P125-04 Cancellation at acceptance boundary.

Host fixture. Cancellation is acknowledged only after ownership is controlled.
A cancelled job is not published as accepted, and a late callback cannot reverse it.
"""

from __future__ import annotations


CASE_ID = "TC-P125-04"
NAME = "Cancellation at acceptance boundary"
INTERVENTION = "Cancel during rendering, verification, publication, or final cleanup."
EXPECTED = "Acknowledge cancellation only after ownership is controlled and never publish a cancelled job as accepted."
NEGATIVE = "A late worker callback that reverses cancellation must fail."
REPEAT = "Repeat with process restart and an already retained partial output."
LATE_TOKEN = "late-callback-reverses-cancellation"
PUBLISHED_TOKEN = "cancelled-job-published-as-accepted"
EARLY_TOKEN = "cancellation-before-ownership"
REPEATS = ("process-restart", "retained-partial-output")
STAGES = ("rendering", "verification", "publication", "final-cleanup")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "stage",
    "ownershipControlled",
    "cancellationAcknowledged",
    "publishedAsAccepted",
    "lateCallbackReversesCancellation",
    "partialOutputRetained",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    stage = payload["stage"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    if stage not in STAGES:
        raise ValueError("stage is unsupported")
    ownership = _bool(payload["ownershipControlled"], "ownershipControlled")
    acknowledged = _bool(payload["cancellationAcknowledged"], "cancellationAcknowledged")
    published = _bool(payload["publishedAsAccepted"], "publishedAsAccepted")
    late = _bool(payload["lateCallbackReversesCancellation"], "lateCallbackReversesCancellation")
    partial = _bool(payload["partialOutputRetained"], "partialOutputRetained")
    rejected: list[str] = []
    if late:
        rejected.append(LATE_TOKEN)
    if published:
        rejected.append(PUBLISHED_TOKEN)
    if acknowledged and not ownership:
        rejected.append(EARLY_TOKEN)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION, f"stage {stage}"]
    if LATE_TOKEN in rejected:
        reasons.append(NEGATIVE)
    if PUBLISHED_TOKEN in rejected:
        reasons.append("a cancelled job was not published as accepted")
    if EARLY_TOKEN in rejected:
        reasons.append("cancellation is acknowledged only after ownership is controlled")
    if not rejected:
        if acknowledged:
            reasons.append("cancellation acknowledged after ownership was controlled")
        else:
            reasons.append("acknowledgement waits until ownership is controlled")
    preserved = [
        evidence,
        {
            "stage": stage,
            "ownershipControlled": ownership,
            "cancellationAcknowledged": acknowledged,
            "publishedAsAccepted": published,
            "lateCallbackReversesCancellation": late,
            "partialOutputRetained": partial,
        },
    ]
    return _result("rejected" if rejected else "recorded", reasons, rejected, preserved)


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 capture was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if not reasons or not preserved or preserved[0] not in preserved:
        raise ValueError("evidence wiped")
    return result
