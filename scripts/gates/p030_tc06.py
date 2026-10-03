"""TC-P030-06 publication destination failure.

Intervention: Exhaust destination space or revoke a publication grant after
private staging succeeds.
Expected: Retain the private source and provide a retryable recovery outcome
without empty success entries.
Negative: Deleting staging before successful publication must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P030-06"
INTERVENTION = (
    "Exhaust destination space or revoke a publication grant after private staging succeeds."
)
EXPECTED = (
    "Retain the private source and provide a retryable recovery outcome without empty success entries."
)
NEGATIVE = "Deleting staging before successful publication must fail."

_STAGES = ("copy", "commit", "report_export", "redundant_staging_cleanup")
_DESTINATIONS = ("none", "exhausted", "grant_revoked")
_PAYLOAD_KEYS = (
    "stage",
    "destinationFailure",
    "privateSource",
    "stagingBytes",
    "publicationSucceeded",
    "deleteStagingBeforePublication",
    "successEntries",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "retryable", "withheld", "publication_recorded")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep the private source. Do not record an empty publication success."""
    stage, failure, source, staging_bytes, published, delete, entries = _payload(payload)
    preserved = [source, f"stage:{stage}", f"stagingBytes:{staging_bytes}"]
    rejected: list[str] = []
    questions: list[str] = []
    false_success = (not published) and bool(entries)

    if delete:
        decision = "rejected"
        rejected.append("staging-deleted-before-publication")
        if failure != "none":
            rejected.append(failure)
        if false_success:
            rejected.extend(f"false-success:{item}" for item in entries)
        questions.append("staging must survive until publication succeeds")
        reasons = [NEGATIVE, EXPECTED, "private source retained"]
    elif false_success:
        decision = "rejected"
        rejected.extend(f"false-success:{item}" for item in entries)
        questions.append("publication failure cannot carry success entries")
        reasons = [EXPECTED, "false success entries were rejected", "private source retained"]
    elif failure != "none" and staging_bytes > 0 and not published:
        decision = "retryable"
        rejected.append(failure)
        questions.append(f"retryable:{stage}")
        reasons = [EXPECTED, "private source retained", "no empty success entry"]
    elif published and failure == "none" and entries:
        decision = "publication_recorded"
        questions.append("publication record is not physical qualification")
        reasons = [
            "publication was recorded without deleting staging early",
            "this record is not a physical S23 qualification",
        ]
    else:
        decision = "withheld"
        if staging_bytes == 0:
            questions.append("private staging is empty")
        else:
            questions.append("publication not finished")
        reasons = ["private source retained", "no empty success entry"]

    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, int, bool, bool, list[str]]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    stage = payload["stage"]
    if stage not in _STAGES:
        raise ValueError("stage is not a known publication stage")
    failure = payload["destinationFailure"]
    if failure not in _DESTINATIONS:
        raise ValueError("destinationFailure is not a known destination state")
    source = payload["privateSource"]
    if not isinstance(source, str) or not source or source != source.strip():
        raise ValueError("privateSource must be a non-empty string")
    staging_bytes = payload["stagingBytes"]
    if type(staging_bytes) is not int or staging_bytes < 0:
        raise ValueError("stagingBytes must be a non-negative int")
    published = _bool(payload["publicationSucceeded"], "publicationSucceeded")
    delete = _bool(payload["deleteStagingBeforePublication"], "deleteStagingBeforePublication")
    entries = payload["successEntries"]
    if not isinstance(entries, list) or any(not isinstance(item, str) or not item for item in entries):
        raise ValueError("successEntries must be a list of non-empty strings")
    if "" in entries:
        raise ValueError("successEntries must not contain an empty success entry")
    return stage, failure, source, staging_bytes, published, delete, list(entries)


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("publication decision cannot be qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
