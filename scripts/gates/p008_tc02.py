#!/usr/bin/env python3
"""P008 TC-P008-02 conflicting source-revision decision gate.

A current revision that differs from the inspected revision invalidates the
affected inspection assumptions until an incremental review is recorded.
Unrelated verified evidence and the concurrent remote commit are preserved.
Documentation-only and capture-interface scopes are distinguished. Equal
revisions leave the inspection unchanged. Review alone does not complete the
phase, and completion is not invented.
"""
from __future__ import annotations

CASE_ID = "TC-P008-02"
CHANGE_SCOPES = {"documentation", "capture_interface", "none"}
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


def required_text(value: object, context: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), context + " must be a non-empty string")
    return value


def boolean(value: object, context: str) -> bool:
    require(type(value) is bool, context + " must be a boolean")
    return value


def string_list(items: list[str], context: str) -> None:
    require(
        isinstance(items, list) and all(isinstance(item, str) for item in items),
        context + " must be a list of strings",
    )


def finish(decision: str, reasons: list[str], preserved: list[str]) -> dict:
    require(decision in {"invalidated", "reviewed", "unchanged"}, "unexpected TC-P008-02 decision")
    require(decision not in {"complete", "allowed"}, "revision disposition must not be complete or allowed")
    require(bool(reasons), "reasons are required unless decision is allowed")
    string_list(reasons, "reasons")
    string_list(preserved, "preservedResults")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": [],
        "preservedResults": preserved,
        "openQuestions": [],
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    return result


def _scope_reason(scope: str, *, reviewed: bool) -> str | None:
    if scope == "documentation":
        if reviewed:
            return "Incremental review distinguishes a documentation-only change."
        return "Change scope is documentation-only."
    if scope == "capture_interface":
        if reviewed:
            return "Incremental review distinguishes a capture interface change."
        return "Change scope is the capture interface."
    return None


def evaluate(payload: dict) -> dict:
    require(isinstance(payload, dict), "payload must be a dict")
    require(payload.get("caseId") == CASE_ID, "caseId mismatches the module")
    required = {
        "caseId",
        "inspectionRevision",
        "currentRevision",
        "incrementalReview",
        "changeScope",
        "unrelatedEvidence",
        "remoteCommit",
    }
    missing = required - set(payload)
    require(not missing, "bad payload: missing " + ", ".join(sorted(missing)))

    inspection = required_text(payload["inspectionRevision"], "inspectionRevision")
    current = required_text(payload["currentRevision"], "currentRevision")
    incremental = boolean(payload["incrementalReview"], "incrementalReview")
    scope = required_text(payload["changeScope"], "changeScope")
    require(scope in CHANGE_SCOPES, "changeScope must be documentation, capture_interface, or none")
    evidence = payload["unrelatedEvidence"]
    require(isinstance(evidence, list), "unrelatedEvidence must be a list")
    require(all(isinstance(item, str) for item in evidence), "unrelatedEvidence must contain strings")
    remote_commit = required_text(payload["remoteCommit"], "remoteCommit")
    preserved = list(evidence) + [remote_commit]
    require(remote_commit in preserved, "remote commit dropped")
    for item in evidence:
        require(item in preserved, "unrelated evidence dropped")

    remote_reason = "Concurrent remote commit is preserved and completion is not invented."
    if inspection != current and not incremental:
        reasons = [
            "Inspection assumptions are invalidated because the current revision differs "
            "and incremental review is required.",
            "The new revision is not treated as already inspected.",
            remote_reason,
        ]
        scope_reason = _scope_reason(scope, reviewed=False)
        if scope_reason:
            reasons.append(scope_reason)
        decision = "invalidated"
    elif inspection != current and incremental:
        reasons = [
            "Incremental review was recorded for the differing revision.",
            "Incremental review alone does not make the phase complete.",
            remote_reason,
        ]
        scope_reason = _scope_reason(scope, reviewed=True)
        if scope_reason:
            reasons.insert(0, scope_reason)
        else:
            reasons.insert(0, "Incremental review recorded the revision change.")
        decision = "reviewed"
    else:
        reasons = [
            "Inspection revision matches the current revision; inspection assumptions are unchanged.",
            remote_reason,
        ]
        scope_reason = _scope_reason(scope, reviewed=False)
        if scope_reason:
            reasons.append(scope_reason)
        decision = "unchanged"

    require(decision not in {"complete", "allowed"}, "completion must not be invented")
    return finish(decision, reasons, preserved)
