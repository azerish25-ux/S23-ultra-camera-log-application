"""TC-P008-04 contradictory-outcome gate.

A passing aggregate cannot hide a failing raw log, a skipped physical test
counted as a pass, or a stale report. Inspectable evidence and the concurrent
remote commit are preserved. Local build success never yields complete or allowed.
"""
from __future__ import annotations

CASE_ID = "TC-P008-04"
RESULT_KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
FIELDS = (
    "summaryPassed",
    "rawFailed",
    "skippedPhysicalAsPass",
    "staleReport",
    "rawLogId",
    "remoteCommit",
    "localBuildSucceeded",
)
BOOLS = ("summaryPassed", "rawFailed", "skippedPhysicalAsPass", "staleReport", "localBuildSucceeded")


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    missing = [name for name in FIELDS if name not in payload]
    if missing:
        raise ValueError("missing " + ", ".join(missing))
    flags = {name: _flag(payload[name], name) for name in BOOLS}
    raw_log_id = _text(payload["rawLogId"], "rawLogId")
    remote_commit = _text(payload["remoteCommit"], "remoteCommit")

    summary_passed = flags["summaryPassed"]
    raw_failed = flags["rawFailed"]
    skipped_as_pass = flags["skippedPhysicalAsPass"]
    stale = flags["staleReport"]
    build_succeeded = flags["localBuildSucceeded"]
    contradiction = summary_passed and (raw_failed or skipped_as_pass or stale)

    reasons: list[str] = []
    rejected: list[str] = []
    questions: list[str] = []
    if contradiction:
        decision = "blocked"
        rejected.append("summary")
        if raw_failed:
            reasons.append("passing summary contradicts the failing raw log; acceptance is blocked")
        if skipped_as_pass:
            reasons.append("skipped physical test was counted as a pass; acceptance is blocked")
            questions.append("physical device gate pending")
        if stale:
            reasons.append("stale report cannot support a passing summary; acceptance is blocked")
        reasons.append("green summary is not trusted without the underlying failure")
    elif raw_failed:
        decision = "failed"
        reasons.append("raw evidence failed without a contradictory passing summary")
    else:
        decision = "consistent"
        reasons.append("summary and raw evidence are consistent; completion is not claimed")
    if build_succeeded:
        reasons.append("local build success does not establish completion or an allowed decision")
    if decision in {"complete", "allowed"}:
        raise ValueError("contradictory or unverified evidence cannot be complete or allowed")

    preserved = [raw_log_id, remote_commit]
    return _result(decision, reasons, rejected, preserved, questions)


def _flag(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a boolean")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value


def _result(decision: str, reasons: list[str], rejected: list[str],
            preserved: list[str], questions: list[str]) -> dict:
    if decision in {"complete", "allowed"}:
        raise ValueError("decision must not be complete or allowed")
    if decision != "allowed" and not reasons:
        raise ValueError("reasons must be non-empty unless decision is allowed")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys are not exact")
    return result
