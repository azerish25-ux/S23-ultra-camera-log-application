"""TC-P006-04 contradictory-outcomes gate.

P006 baseline remains in force: a firmware experiment with no identified blocked
stream and no verified recovery procedure is deferred. This case blocks acceptance
when a passing summary disagrees with inspectable raw evidence.
"""

from __future__ import annotations

CASE_ID = "TC-P006-04"
_BASELINE_REASON = (
    "Firmware experiment without an identified blocked stream and verified recovery "
    "is deferred while non-destructive capability and application-level investigations remain available."
)
_BOOL_FIELDS = ("summaryPassed", "rawFailed", "skippedPhysicalAsPass", "staleReport")


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if payload.get("caseId") != CASE_ID:
        raise ValueError(f"caseId mismatch: expected {CASE_ID}")

    flags = {name: _require_bool(payload, name) for name in _BOOL_FIELDS}
    summary_passed = flags["summaryPassed"]
    raw_failed = flags["rawFailed"]
    skipped_physical_as_pass = flags["skippedPhysicalAsPass"]
    stale_report = flags["staleReport"]
    raw_log_id = payload.get("rawLogId")
    if not isinstance(raw_log_id, str) or not raw_log_id.strip():
        raise ValueError("rawLogId must be a non-empty string")

    distorted = skipped_physical_as_pass or stale_report
    reasons = [_BASELINE_REASON]
    rejected: list[str] = []
    open_questions: list[str] = []

    if summary_passed and (raw_failed or distorted):
        decision = "blocked"
        reasons.append(
            "Contradiction between the passing aggregate summary and inspectable underlying evidence; "
            f"prefer the raw log {raw_log_id}."
        )
        _append_flag_reasons(reasons, raw_failed, skipped_physical_as_pass, stale_report)
        reasons.append("Trusting the green summary without the raw log is blocked and is never allowed.")
        rejected = ["aggregate-summary"]
    elif distorted:
        decision = "blocked"
        reasons.append(
            "Contradiction in the outcome record; "
            f"prefer the raw log {raw_log_id}."
        )
        _append_flag_reasons(reasons, raw_failed, skipped_physical_as_pass, stale_report)
        reasons.append("A distorted report must not be allowed.")
        rejected = ["aggregate-summary"]
    elif (not summary_passed) and raw_failed:
        decision = "failed"
        reasons.append(
            "Summary did not pass and the critical raw log failed; outcome is failed. "
            f"Prefer and preserve the raw log {raw_log_id}."
        )
        _append_flag_reasons(reasons, False, skipped_physical_as_pass, stale_report)
    elif summary_passed:
        decision = "consistent"
        reasons.append(
            "Aggregate summary and raw log agree, with no skipped physical pass and no stale report. "
            f"Outcome is consistent. Raw log {raw_log_id} is retained. "
            "Consistency does not authorize the deferred firmware experiment."
        )
    else:
        decision = "failed"
        reasons.append(
            "Summary did not pass, so acceptance is not granted. "
            f"Raw log {raw_log_id} is preserved."
        )

    if decision == "allowed":
        raise RuntimeError("contradictory or unverified outcomes must not be allowed")

    return {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [raw_log_id],
        "openQuestions": open_questions,
    }


def _require_bool(payload: dict, name: str) -> bool:
    value = payload.get(name)
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a bool")
    return value


def _append_flag_reasons(
    reasons: list[str],
    raw_failed: bool,
    skipped_physical_as_pass: bool,
    stale_report: bool,
) -> None:
    if raw_failed:
        reasons.append("The critical raw log failed.")
    if skipped_physical_as_pass:
        reasons.append("A skipped physical test was incorrectly counted as passing.")
    if stale_report:
        reasons.append("The report is stale and cannot override the raw log.")
