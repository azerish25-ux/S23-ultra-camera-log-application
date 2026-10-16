"""TC-P125-05 Temporary storage exhaustion.

Host fixture. Remaining space is checked against the full reserve, including
intermediate duplication. Budgeting only the final output bytes fails.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_ID = "TC-P125-05"
NAME = "Temporary storage exhaustion"
INTERVENTION = "Make remaining space insufficient for intermediate work or duplicate publication storage."
EXPECTED = "Pause or fail safely before source loss, preserving recoverable artifacts and clear cleanup choices."
NEGATIVE = "Budgeting only final output bytes must fail."
REPEAT = "Repeat before rendering, during chunk assembly, and during gallery publication."
FINAL_ONLY = "budget-only-final-output-bytes"
MISMATCH = "budget-does-not-match-reserve"
REPEATS = ("before-rendering", "chunk-assembly", "gallery-publication")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "stage",
    "source_bytes",
    "intermediate_estimate_bytes",
    "safety_bytes",
    "free_bytes",
    "start_allowed",
    "delete_source",
    "frame_count",
    "bytes_per_frame",
    "final_output_bytes",
    "budgeted_bytes",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_SPEC = importlib.util.spec_from_file_location(
    "p125_budget_disk_and_intermediate_storage",
    Path(__file__).resolve().parent / "p125_budget_disk_and_intermediate_storage.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    stage = payload["stage"]
    if repeat not in REPEATS or stage != repeat:
        raise ValueError("repeat is unsupported")
    final_output = _CORE.require_nonnegative_int(payload["final_output_bytes"], "final_output_bytes")
    budgeted = _CORE.require_nonnegative_int(payload["budgeted_bytes"], "budgeted_bytes")
    planned = _CORE.plan_storage(
        source_bytes=payload["source_bytes"],
        intermediate_estimate_bytes=payload["intermediate_estimate_bytes"],
        safety_bytes=payload["safety_bytes"],
        free_bytes=payload["free_bytes"],
        start_allowed=payload["start_allowed"],
        delete_source=payload["delete_source"],
        frame_count=payload["frame_count"],
        bytes_per_frame=payload["bytes_per_frame"],
    )
    reserve = planned["reserveBytes"]
    implied = planned["impliedIntermediateBytes"]
    rejected = list(planned["rejectedClaims"])
    if budgeted != reserve and MISMATCH not in rejected:
        rejected.append(MISMATCH)
    final_only = budgeted == final_output and implied > 0 and budgeted != reserve
    if final_only and FINAL_ONLY not in rejected:
        rejected.append(FINAL_ONLY)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION, f"stage {stage}"]
    reasons.append(_CORE.RESERVE_FORMULA)
    reasons.append(f"reserveBytes={reserve}")
    reasons.append(f"headroomBytes={planned['headroomBytes']}")
    reasons.extend(planned["detailReasons"])
    if FINAL_ONLY in rejected:
        reasons.append(NEGATIVE)
    if MISMATCH in rejected:
        reasons.append("budgeted bytes must equal source_bytes + intermediate_estimate_bytes + safety_bytes")
    if not rejected:
        if planned["headroomBytes"] < 0:
            reasons.append("pause or fail safely before source loss")
        else:
            reasons.append("reserve includes intermediate duplication and fits in free space")
        reasons.append("reproducible intermediates may be removed; source originals stay protected")
    preserved = [
        evidence,
        {
            "stage": stage,
            "reserveBytes": reserve,
            "headroomBytes": planned["headroomBytes"],
            "source_bytes": planned["source_bytes"],
            "intermediate_estimate_bytes": planned["intermediate_estimate_bytes"],
            "safety_bytes": planned["safety_bytes"],
            "free_bytes": planned["free_bytes"],
            "impliedIntermediateBytes": implied,
            "budgetedBytes": budgeted,
            "finalOutputBytes": final_output,
            "startRefused": planned["startRefused"],
            "policyStartAllowed": planned["policyStartAllowed"],
            "recoverable": True,
            "removable": list(planned["removable"]),
            "protected": list(planned["protected"]),
        },
    ]
    return _result("rejected" if rejected else "recorded", reasons, rejected, preserved)


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    report = preserved[1]
    if report["headroomBytes"] < 0 and not report["startRefused"]:
        raise ValueError("headroom may be negative only when start is refused")
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
    if not reasons or preserved[0] not in preserved:
        raise ValueError("evidence wiped")
    return result
