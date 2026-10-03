#!/usr/bin/env python3
"""TC-P006-06: uncontrolled threshold revision.

Loosening a threshold after results are known is blocked unless the revision
is both reviewed and versioned. The original failure stays on the record.
A reviewed revision still requires renewed validation and must not present
the original run as a pass.
"""

from __future__ import annotations

import math
from typing import Any

CASE_ID = "TC-P006-06"


def evaluate(payload: dict) -> dict:
    """Return the TC-P006-06 gate decision for one threshold payload."""
    threshold = _parse(payload)
    loosened = threshold["loosened"]
    reviewed = threshold["reviewed"]
    version_recorded = threshold["versionRecorded"]
    original_failed = threshold["originalFailed"]
    if loosened and not (reviewed and version_recorded):
        return _blocked(threshold)
    if loosened and reviewed and version_recorded:
        return _reviewed(threshold)
    if original_failed:
        return _failed(threshold)
    return _unchanged(threshold)


def _parse(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    if payload.get("caseId") != CASE_ID:
        raise ValueError(f"wrong caseId: {payload.get('caseId')!r}")
    raw = payload.get("threshold")
    if not isinstance(raw, dict):
        raise ValueError("threshold must be an object")
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("threshold name must be a non-empty string")
    for field in ("originalValue", "proposedValue"):
        value = raw.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"threshold {field} must be a finite number")
    for field in ("unit", "domain"):
        value = raw.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"threshold {field} must be a non-empty string")
    flags: dict[str, bool] = {}
    for field in ("loosened", "reviewed", "versionRecorded", "originalFailed"):
        value = raw.get(field)
        if type(value) is not bool:
            raise ValueError(f"threshold {field} must be a boolean")
        flags[field] = value
    return {
        "name": name,
        "originalValue": raw["originalValue"],
        "proposedValue": raw["proposedValue"],
        "unit": raw["unit"],
        "domain": raw["domain"],
        **flags,
    }


def _num(value: int | float) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("value must be a finite number")
    if isinstance(value, int):
        return str(value)
    return format(value, ".12g")


def _proposed_claim(threshold: dict[str, Any]) -> str:
    return (
        f"proposed-change:{threshold['name']}:"
        f"{_num(threshold['originalValue'])}->{_num(threshold['proposedValue'])}:"
        f"{threshold['unit']}:{threshold['domain']}"
    )


def _finish(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision == "allowed":
        raise ValueError("threshold revision must not decision allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty unless decision is allowed")
    for label, items in (
        ("reasons", reasons),
        ("rejectedClaims", rejected),
        ("preservedResults", preserved),
        ("openQuestions", questions),
    ):
        if not isinstance(items, list) or not all(isinstance(item, str) and item for item in items):
            raise ValueError(f"{label} must be a list of non-empty strings")
    return {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }


def _blocked(threshold: dict[str, Any]) -> dict:
    name = threshold["name"]
    reasons = [
        f"loosened threshold {name} is blocked without a reviewed versioned protocol revision",
        f"original failure of {name} is retained",
    ]
    questions: list[str] = []
    if not threshold["reviewed"]:
        reasons.append(f"{name} revision was not reviewed")
        questions.append(f"reviewed protocol revision required for {name}")
    if not threshold["versionRecorded"]:
        reasons.append(f"{name} revision has no version record")
        questions.append(f"version record required for {name}")
    questions.append(f"renewed validation required for {name}")
    rejected = [_proposed_claim(threshold), f"original-pass:{name}"]
    return _finish("blocked", reasons, rejected, [f"original-failure:{name}"], questions)


def _reviewed(threshold: dict[str, Any]) -> dict:
    name = threshold["name"]
    reasons = [
        f"reviewed protocol revision for {name} requires renewed validation",
        f"the original run of {name} is not rewritten as a success",
    ]
    preserved: list[str] = []
    rejected: list[str] = []
    if threshold["originalFailed"]:
        preserved.append(f"original-failure:{name}")
        rejected.append(f"original-pass:{name}")
        reasons.append(f"original failure of {name} is retained")
    return _finish(
        "reviewed_revision",
        reasons,
        rejected,
        preserved,
        [f"renewed validation required for {name}"],
    )


def _failed(threshold: dict[str, Any]) -> dict:
    name = threshold["name"]
    return _finish(
        "failed",
        [f"{name} failed the unchanged original threshold"],
        [],
        [f"original-failure:{name}"],
        [],
    )


def _unchanged(threshold: dict[str, Any]) -> dict:
    name = threshold["name"]
    return _finish(
        "unchanged",
        [f"{name} threshold is unchanged"],
        [],
        [],
        [],
    )
