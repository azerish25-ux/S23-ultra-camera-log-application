#!/usr/bin/env python3
"""P125 Budget disk and intermediate storage.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P125-01 through TC-P125-08 modules.

Reserve bytes = source_bytes + intermediate_estimate_bytes + safety_bytes.
safety_bytes is an explicit integer, not a percentage of free space.
Headroom bytes = free_bytes - reserve. Headroom may be negative only when
start is refused. A start_allowed claim while free_bytes < reserve is rejected.
delete_source is always rejected. An intermediate estimate of 0 is rejected
when frame_count * bytes_per_frame is positive.
"""

from __future__ import annotations

from typing import Any


BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P125"
TITLE = "Budget disk and intermediate storage"
WORKSTREAM = 16
DEPENDENCIES = ("P124",)
GOAL = "Prevent high-quality development from filling storage and destroying recoverability."
METHOD = (
    "Estimate source, proxy, temporary, finalization, and publication requirements separately. "
    "Use conservative reserves and measured growth, not a fixed generic percentage. "
    "Allow explicit cleanup of reproducible intermediates while protecting originals and sole retained outputs."
)
FIXTURE = "A long RAW source whose planned ten-bit export requires temporary duplication during publication."
ORACLE = (
    "The job declines or pauses safely before exhausting reserved space and explains which data can be removed safely."
)
MUTANT = "Budget only the final output size and ignore temporary files."
DELIVERABLE = "Storage planner and low-space continuation policy"
RESERVE_FORMULA = "reserve = source_bytes + intermediate_estimate_bytes + safety_bytes"
SEPARATE_REQUIREMENTS = ("source", "proxy", "temporary", "finalization", "publication")
START_BELOW_RESERVE = "start-allowed-below-reserve"
DELETE_SOURCE = "delete-source"
IGNORED_INTERMEDIATES = "ignored-intermediates"

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "source_bytes",
    "intermediate_estimate_bytes",
    "safety_bytes",
    "free_bytes",
    "start_allowed",
    "delete_source",
    "frame_count",
    "bytes_per_frame",
}
EVALUATE_KEYS = {
    "caseId",
    "evidenceId",
    "claim",
    "applyMutant",
    "source_bytes",
    "intermediate_estimate_bytes",
    "safety_bytes",
    "free_bytes",
    "start_allowed",
    "delete_source",
    "frame_count",
    "bytes_per_frame",
}
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


def require_nonnegative_int(value: object, label: str) -> int:
    """Estimates and byte counts are non-negative integers. Negatives raise ValueError."""
    require(type(value) is int, f"{label} must be a non-negative integer")
    require(value >= 0, f"{label} must be a non-negative integer")
    return value


def require_text(value: object, label: str) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(), f"{label} must be a non-empty string")
    return value


def reserve_bytes(source_bytes: int, intermediate_estimate_bytes: int, safety_bytes: int) -> int:
    """Reserve bytes = source_bytes + intermediate_estimate_bytes + safety_bytes."""
    source = require_nonnegative_int(source_bytes, "source_bytes")
    intermediate = require_nonnegative_int(intermediate_estimate_bytes, "intermediate_estimate_bytes")
    safety = require_nonnegative_int(safety_bytes, "safety_bytes")
    return source + intermediate + safety


def implied_intermediate_bytes(frame_count: int, bytes_per_frame: int) -> int:
    """Measured intermediate growth implied by the frame budget. Not a percentage."""
    frames = require_nonnegative_int(frame_count, "frame_count")
    per_frame = require_nonnegative_int(bytes_per_frame, "bytes_per_frame")
    return frames * per_frame


def headroom_bytes(free_bytes: int, reserve: int) -> int:
    """Headroom = free_bytes - reserve. Negative only when start is refused."""
    free = require_nonnegative_int(free_bytes, "free_bytes")
    reserved = require_nonnegative_int(reserve, "reserve")
    return free - reserved


def plan_storage(
    *,
    source_bytes: int,
    intermediate_estimate_bytes: int,
    safety_bytes: int,
    free_bytes: int,
    start_allowed: bool,
    delete_source: bool,
    frame_count: int,
    bytes_per_frame: int,
) -> dict[str, Any]:
    """Apply the low-space continuation policy. Does not qualify a device."""
    require(type(start_allowed) is bool, "start_allowed must be a bool")
    require(type(delete_source) is bool, "delete_source must be a bool")
    source = require_nonnegative_int(source_bytes, "source_bytes")
    intermediate = require_nonnegative_int(intermediate_estimate_bytes, "intermediate_estimate_bytes")
    safety = require_nonnegative_int(safety_bytes, "safety_bytes")
    free = require_nonnegative_int(free_bytes, "free_bytes")
    frames = require_nonnegative_int(frame_count, "frame_count")
    per_frame = require_nonnegative_int(bytes_per_frame, "bytes_per_frame")
    reserve = reserve_bytes(source, intermediate, safety)
    implied = implied_intermediate_bytes(frames, per_frame)
    headroom = headroom_bytes(free, reserve)
    insufficient = free < reserve
    rejected: list[str] = []
    detail: list[str] = []
    if insufficient and start_allowed:
        rejected.append(START_BELOW_RESERVE)
        detail.append("start_allowed must be false when free_bytes < reserve")
    if delete_source:
        rejected.append(DELETE_SOURCE)
        detail.append("delete_source is rejected; originals are protected")
    if intermediate == 0 and implied > 0:
        rejected.append(IGNORED_INTERMEDIATES)
        detail.append("intermediate_estimate_bytes is 0 while frame_count * bytes_per_frame is positive")
    policy_start_allowed = start_allowed and not insufficient
    start_refused = not policy_start_allowed
    require(
        headroom >= 0 or start_refused,
        "headroom may be negative only when start is refused",
    )
    require(not (headroom < 0 and policy_start_allowed), "start must be refused when headroom is negative")
    return {
        "source_bytes": source,
        "intermediate_estimate_bytes": intermediate,
        "safety_bytes": safety,
        "free_bytes": free,
        "frame_count": frames,
        "bytes_per_frame": per_frame,
        "reserveBytes": reserve,
        "headroomBytes": headroom,
        "impliedIntermediateBytes": implied,
        "submittedStartAllowed": start_allowed,
        "policyStartAllowed": policy_start_allowed,
        "startRefused": start_refused,
        "delete_source": delete_source,
        "rejectedClaims": rejected,
        "detailReasons": detail,
        "removable": ["reproducible-intermediates"],
        "protected": ["source-originals", "sole-retained-outputs"],
    }


def _seal(result: dict[str, Any]) -> dict[str, Any]:
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(result["decision"] in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(isinstance(result["reasons"], list) and all(isinstance(item, str) and item for item in result["reasons"]), "reasons must be non-empty strings")
    require(result["reasons"], "reasons must be non-empty")
    require(isinstance(result["rejectedClaims"], list), "rejectedClaims must be a list")
    require(all(isinstance(item, str) and item for item in result["rejectedClaims"]), "rejectedClaims must be strings")
    if result["decision"] == "recorded":
        require(result["rejectedClaims"] == [], "recorded result cannot reject claims")
    else:
        require(result["rejectedClaims"], "rejected result needs a rejected claim")
    require(isinstance(result["preservedResults"], list) and result["preservedResults"], "evidence wiped")
    evidence = result["preservedResults"][0]
    require(isinstance(evidence, str) and evidence in result["preservedResults"], "evidence must be preserved")
    report = result["preservedResults"][2]
    require(isinstance(report, dict), "reserve report missing")
    require(
        report["reserveBytes"]
        == report["source_bytes"] + report["intermediate_estimate_bytes"] + report["safety_bytes"],
        "reserve formula drifted",
    )
    require(report["headroomBytes"] == report["free_bytes"] - report["reserveBytes"], "headroom drifted")
    if report["headroomBytes"] < 0:
        require(report["startRefused"] is True, "headroom may be negative only when start is refused")
        require(report["policyStartAllowed"] is False, "start must be refused when headroom is negative")
    require(isinstance(result["openQuestions"], list) and result["openQuestions"], "openQuestions must be non-empty")
    require(any("physical S23" in item for item in result["openQuestions"]), "physical S23 was not noted")
    return result


def _decide(
    *,
    case_id: str,
    evidence_id: str,
    claim: str,
    apply_mutant: bool,
    source_bytes: int,
    intermediate_estimate_bytes: int,
    safety_bytes: int,
    free_bytes: int,
    start_allowed: bool,
    delete_source: bool,
    frame_count: int,
    bytes_per_frame: int,
) -> dict[str, Any]:
    require(type(apply_mutant) is bool, "applyMutant must be a bool")
    planned = plan_storage(
        source_bytes=source_bytes,
        intermediate_estimate_bytes=intermediate_estimate_bytes,
        safety_bytes=safety_bytes,
        free_bytes=free_bytes,
        start_allowed=start_allowed,
        delete_source=delete_source,
        frame_count=frame_count,
        bytes_per_frame=bytes_per_frame,
    )
    rejected = list(planned["rejectedClaims"])
    if apply_mutant:
        rejected.insert(0, MUTANT)
    decision = "rejected" if rejected else "recorded"
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        RESERVE_FORMULA,
        "safety_bytes is an explicit reserve, not a fixed generic percentage",
        "source, proxy, temporary, finalization, and publication are estimated separately",
        f"reserveBytes={planned['reserveBytes']}",
        f"headroomBytes={planned['headroomBytes']}",
        f"impliedIntermediateBytes={planned['impliedIntermediateBytes']}",
        "reproducible intermediates may be removed; source originals and sole retained outputs are protected",
    ]
    reasons.extend(planned["detailReasons"])
    if apply_mutant:
        reasons.append("mutant rejected: " + MUTANT)
    if decision == "recorded":
        if planned["headroomBytes"] < 0:
            reasons.append("start refused before reserved space is exhausted")
        elif planned["policyStartAllowed"]:
            reasons.append("reserve fits in free space for " + evidence_id)
        else:
            reasons.append("start refused by the continuation policy")
        reasons.append("method: " + METHOD)
    report = {
        "reserveBytes": planned["reserveBytes"],
        "headroomBytes": planned["headroomBytes"],
        "source_bytes": planned["source_bytes"],
        "intermediate_estimate_bytes": planned["intermediate_estimate_bytes"],
        "safety_bytes": planned["safety_bytes"],
        "free_bytes": planned["free_bytes"],
        "frame_count": planned["frame_count"],
        "bytes_per_frame": planned["bytes_per_frame"],
        "impliedIntermediateBytes": planned["impliedIntermediateBytes"],
        "submittedStartAllowed": planned["submittedStartAllowed"],
        "policyStartAllowed": planned["policyStartAllowed"],
        "startRefused": planned["startRefused"],
        "delete_source": planned["delete_source"],
        "removable": list(planned["removable"]),
        "protected": list(planned["protected"]),
        "separateRequirements": list(SEPARATE_REQUIREMENTS),
    }
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence_id, claim, report],
        "openQuestions": [
            "physical S23 capture was not run",
            "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
        ],
    }
    return _seal(result)


def _components(payload: dict[str, Any]) -> tuple[Any, ...]:
    evidence = require_text(payload["evidenceId"], "evidenceId")
    claim = require_text(payload["claim"], "claim")
    require(type(payload["applyMutant"]) is bool, "applyMutant must be a bool")
    return (
        evidence,
        claim,
        payload["applyMutant"],
        payload["source_bytes"],
        payload["intermediate_estimate_bytes"],
        payload["safety_bytes"],
        payload["free_bytes"],
        payload["start_allowed"],
        payload["delete_source"],
        payload["frame_count"],
        payload["bytes_per_frame"],
    )


def assess(document: dict) -> dict[str, Any]:
    """Apply the storage oracle to one disk-budget fixture."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    (
        evidence,
        claim,
        apply_mutant,
        source_bytes,
        intermediate_estimate_bytes,
        safety_bytes,
        free_bytes,
        start_allowed,
        delete_source,
        frame_count,
        bytes_per_frame,
    ) = _components(document)
    return _decide(
        case_id=PHASE,
        evidence_id=evidence,
        claim=claim,
        apply_mutant=apply_mutant,
        source_bytes=source_bytes,
        intermediate_estimate_bytes=intermediate_estimate_bytes,
        safety_bytes=safety_bytes,
        free_bytes=free_bytes,
        start_allowed=start_allowed,
        delete_source=delete_source,
        frame_count=frame_count,
        bytes_per_frame=bytes_per_frame,
    )


def evaluate(payload: dict) -> dict[str, Any]:
    """Budget one job. Invalid shapes and negative estimates raise ValueError."""
    require(isinstance(payload, dict), "payload must be an object")
    missing = EVALUATE_KEYS - set(payload)
    extra = set(payload) - EVALUATE_KEYS
    require(not missing, "payload missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))
    case_id = require_text(payload["caseId"], "caseId")
    (
        evidence,
        claim,
        apply_mutant,
        source_bytes,
        intermediate_estimate_bytes,
        safety_bytes,
        free_bytes,
        start_allowed,
        delete_source,
        frame_count,
        bytes_per_frame,
    ) = _components(payload)
    return _decide(
        case_id=case_id,
        evidence_id=evidence,
        claim=claim,
        apply_mutant=apply_mutant,
        source_bytes=source_bytes,
        intermediate_estimate_bytes=intermediate_estimate_bytes,
        safety_bytes=safety_bytes,
        free_bytes=free_bytes,
        start_allowed=start_allowed,
        delete_source=delete_source,
        frame_count=frame_count,
        bytes_per_frame=bytes_per_frame,
    )
