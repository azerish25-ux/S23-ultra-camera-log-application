#!/usr/bin/env python3
"""TC-P007-04 contradictory-outcome gate.

A green aggregate summary cannot outrank a failing raw log, a skipped physical
test counted as a pass, or a stale report. Identical display names with
different content hashes stay distinct in the preserved evidence.
"""
from __future__ import annotations

from typing import Any

CASE_ID = "TC-P007-04"
PAYLOAD_KEYS = {"caseId", "summaryPassed", "rawFailed", "skippedPhysicalAsPass", "staleReport", "rawLogId", "profiles"}
PROFILE_KEYS = {"displayName", "sha256"}
RESULT_KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _exact_keys(value: dict, required: set[str], context: str) -> None:
    missing = required - set(value)
    extra = set(value) - required
    _require(not missing, "bad payload: " + context + " missing fields: " + ", ".join(sorted(missing)))
    _require(not extra, "bad payload: " + context + " unexpected fields: " + ", ".join(sorted(extra)))


def _flag(payload: dict, key: str) -> bool:
    value = payload[key]
    _require(type(value) is bool, "bad payload: " + key + " must be a bool")
    return value


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str], questions: list[str]) -> dict:
    _require(decision != "allowed", "false-pass must not be allowed")
    _require(bool(reasons), "reasons must be non-empty unless decision is allowed")
    value = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    _require(tuple(value) == RESULT_KEYS, "result keys drifted")
    return value


def _validate(payload: Any) -> tuple[bool, bool, bool, bool, str, list[dict]]:
    _require(isinstance(payload, dict), "bad payload")
    _exact_keys(payload, PAYLOAD_KEYS, "payload")
    _require(payload.get("caseId") == CASE_ID, "wrong caseId: " + repr(payload.get("caseId")))
    summary_passed = _flag(payload, "summaryPassed")
    raw_failed = _flag(payload, "rawFailed")
    skipped = _flag(payload, "skippedPhysicalAsPass")
    stale = _flag(payload, "staleReport")
    _require(_text(payload["rawLogId"]), "bad payload: rawLogId must be non-empty text")
    profiles = payload["profiles"]
    _require(isinstance(profiles, list), "bad payload: profiles must be a list")
    for index, profile in enumerate(profiles):
        context = "profiles[" + str(index) + "]"
        _require(isinstance(profile, dict), "bad payload: " + context + " must be an object")
        _exact_keys(profile, PROFILE_KEYS, context)
        _require(_text(profile["displayName"]), "bad payload: " + context + ".displayName must be non-empty text")
        _require(_text(profile["sha256"]), "bad payload: " + context + ".sha256 must be non-empty text")
    return summary_passed, raw_failed, skipped, stale, payload["rawLogId"], profiles


def _identical_names_differ(profiles: list[dict]) -> bool:
    grouped: dict[str, set[str]] = {}
    for profile in profiles:
        grouped.setdefault(profile["displayName"], set()).add(profile["sha256"])
    return any(len(hashes) > 1 for hashes in grouped.values())


def evaluate(payload: Any) -> dict:
    """Return the TC-P007-04 contradiction decision for one payload.

    summaryPassed combined with a failing raw log, a skipped physical test
    counted as a pass, or a stale report is blocked and is never allowed.
    Otherwise two different profile hashes yield failed when rawFailed is set
    and consistent when it is not. preservedResults always keeps the raw log id
    and every profile content hash, so display name alone cannot collapse them.
    """
    summary_passed, raw_failed, skipped, stale, raw_log_id, profiles = _validate(payload)
    false_pass = summary_passed and (raw_failed or skipped or stale)
    if false_pass:
        decision = "blocked"
    elif raw_failed:
        decision = "failed"
    else:
        decision = "consistent"
    rejected: list[str] = []
    reasons: list[str] = []
    questions: list[str] = []
    if decision == "blocked":
        rejected.append("acceptance")
        rejected.append("summary-pass")
        reasons.append("A passing aggregate summary cannot authorize acceptance.")
        if raw_failed:
            rejected.append("raw-log")
            reasons.append("A passing summary contradicts the failing raw log; acceptance is blocked.")
        if skipped:
            rejected.append("skipped-physical-as-pass")
            reasons.append("A skipped physical test counted as passing blocks acceptance.")
        if stale:
            rejected.append("stale-report")
            reasons.append("A stale report cannot support acceptance.")
    elif decision == "failed":
        rejected.extend(["acceptance", "raw-log"])
        reasons.append("The raw log failed, so acceptance is not granted.")
    else:
        reasons.append("No false-pass contradiction is present.")
    if skipped:
        questions.append("Physical-device qualification is unresolved because a skipped test was counted as passing.")
    if stale:
        questions.append("Whether the report still matches this run is unresolved.")
    if _identical_names_differ(profiles) or len({profile["sha256"] for profile in profiles}) >= 2:
        reasons.append("Different content hashes are distinct, including when display names match.")
    preserved = [raw_log_id]
    preserved.extend(profile["sha256"] for profile in profiles)
    return _result(decision, reasons, rejected, preserved, questions)
