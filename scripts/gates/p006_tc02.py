#!/usr/bin/env python3
"""P006 TC-P006-02 conflicting source-revision decision gate.

A repository revision that differs from the inspected revision invalidates the
affected inspection assumptions until an incremental review is recorded. Unrelated
verified evidence is preserved exactly. A documentation-only change and a capture
interface change are distinguished when that review exists. Equal revisions leave
the inspection unchanged.
"""
from __future__ import annotations

CASE_ID = "TC-P006-02"
CHANGE_SCOPES = {"documentation", "capture_interface", "none"}
RESULT_KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_keys(value: dict, required: set[str], context: str, optional: set[str] | None = None) -> None:
    require(isinstance(value, dict), context + " must be an object")
    optional = optional or set()
    missing = required - set(value)
    extra = set(value) - required - optional
    require(not missing, f"{context} missing fields: {', '.join(sorted(missing))}")
    require(not extra, f"{context} has unexpected fields: {', '.join(sorted(extra))}")


def required_text(value: object, context: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), context + " must be a non-empty string")
    return value


def boolean(value: object, context: str) -> bool:
    require(type(value) is bool, context + " must be a boolean")
    return value


def string_list(items: list[str], context: str) -> None:
    require(isinstance(items, list) and all(isinstance(item, str) for item in items),
            context + " must be a list of strings")


def finish(decision: str, reasons: list[str], preserved: list[str]) -> dict:
    require(decision in {"invalidated", "reviewed", "unchanged"}, "unexpected TC-P006-02 decision")
    require(decision != "allowed", "a conflicting or matched revision is never silently allowed")
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


def evaluate(payload: dict) -> dict:
    require(isinstance(payload, dict), "payload must be a dict")
    if payload.get("caseId") != CASE_ID:
        raise ValueError("caseId mismatches the module")
    exact_keys(payload, {"caseId", "inspectionRevision", "currentRevision", "incrementalReview",
                         "changeScope", "unrelatedEvidence"}, "payload")
    inspection = required_text(payload["inspectionRevision"], "inspectionRevision")
    current = required_text(payload["currentRevision"], "currentRevision")
    incremental = boolean(payload["incrementalReview"], "incrementalReview")
    scope = required_text(payload["changeScope"], "changeScope")
    require(scope in CHANGE_SCOPES, "changeScope must be documentation, capture_interface, or none")
    evidence = payload["unrelatedEvidence"]
    require(isinstance(evidence, list), "unrelatedEvidence must be a list")
    require(all(isinstance(item, str) and bool(item.strip()) for item in evidence),
            "unrelatedEvidence must contain non-empty strings")
    preserved = list(evidence)

    if inspection == current:
        return finish(
            "unchanged",
            ["Inspection revision matches the current revision; inspection assumptions are unchanged."],
            preserved,
        )
    if not incremental:
        return finish(
            "invalidated",
            ["Inspection assumptions are invalidated because the current revision differs and incremental review is required."],
            preserved,
        )
    if scope == "capture_interface":
        reasons = ["Incremental review distinguishes a capture interface change."]
    elif scope == "documentation":
        reasons = ["Incremental review distinguishes a documentation-only change."]
    else:
        reasons = ["Incremental review recorded the revision change."]
    return finish("reviewed", reasons, preserved)
