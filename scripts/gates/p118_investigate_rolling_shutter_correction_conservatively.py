#!/usr/bin/env python3
"""P118 Investigate rolling-shutter correction conservatively.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P118-01 through TC-P118-08 modules.

Row time offset is ``row_index * readout_seconds_per_row``. A geometric
correction is permitted only when that readout is finite and greater than 0
and its source is ``measured``. A corrected row is ``y' = y + velocity_y *
row_time``. The largest absolute applied shift is reported in pixels.

Unknown or missing readout cannot justify a global warp labelled
``rolling_shutter_correction``. The honest result is ``recorded`` with
``correction_applied false`` and every row left on its original y. Optical-flow
approximation is not sensor-timing correction. A global camera shear is not
applied to an independently moving foreground person. Claiming the correction
restores a global shutter is rejected.
"""

from __future__ import annotations

import math
from typing import Any


BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P118"
WORKSTREAM = 15
TITLE = "Investigate rolling-shutter correction conservatively"
GOAL = "Explore geometric correction only with enough timing and motion evidence."
METHOD = (
    "Use measured or documented readout timing, synchronized motion data where available, "
    "and controlled scenes. Separate optical-flow approximation from sensor-timing-based "
    "correction. Preserve the original and restrict correction when foreground motion "
    "violates a global model."
)
FIXTURE = "A fast pan across vertical lines with an independently moving foreground person."
ORACLE = (
    "The system reports residual error and does not warp the person using an unjustified "
    "global camera-motion assumption."
)
MUTANT = "Apply one global shear correction to every object without validating motion."
DELIVERABLE = "Rolling-shutter research report and bounded experimental mode"
DEPENDENCIES = ("P117",)

SOURCE_MEASURED = "measured"
SOURCE_DOCUMENTED = "documented"
SOURCE_UNKNOWN = "unknown"
READOUT_SOURCES = (SOURCE_MEASURED, SOURCE_DOCUMENTED, SOURCE_UNKNOWN)
WARP_NONE = "none"
WARP_SENSOR = "rolling_shutter_correction"
WARP_GLOBAL = "global_camera_shear"
WARP_FLOW = "optical_flow"
WARP_LABELS = (WARP_NONE, WARP_SENSOR, WARP_GLOBAL, WARP_FLOW)
ROLE_BACKGROUND = "background"
ROLE_FOREGROUND = "foreground"
ROLES = (ROLE_BACKGROUND, ROLE_FOREGROUND)

CORRECTION_APPLIED_TRUE = "correction_applied true"
CORRECTION_APPLIED_FALSE = "correction_applied false"
UNKNOWN_READOUT_WARP = "rolling-shutter-correction-without-measured-readout"
UNMEASURED_WARP = "warp-without-measured-readout"
GLOBAL_SHUTTER_CLAIM = "correction-restores-global-shutter"
UNJUSTIFIED_GLOBAL = "unjustified-global-camera-warp-of-foreground"
BACKGROUND_VIOLATION = "background-motion-violates-global-model"

ABSOLUTE_TOLERANCE = 1e-9
RELATIVE_TOLERANCE = 1e-9
ROW_KEYS = ("rowIndex", "y", "velocityY", "role")
CORRECTION_INPUT_KEYS = (
    "readoutSecondsPerRow",
    "readoutSource",
    "cameraVelocityY",
    "warpLabel",
    "claimsGlobalShutterRestored",
    "rows",
)
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "readoutSecondsPerRow",
    "readoutSource",
    "cameraVelocityY",
    "warpLabel",
    "claimsGlobalShutterRestored",
    "rows",
}
EVALUATE_KEYS = {
    "caseId",
    "evidenceId",
    "claim",
    "applyMutant",
    "readoutSecondsPerRow",
    "readoutSource",
    "cameraVelocityY",
    "warpLabel",
    "claimsGlobalShutterRestored",
    "rows",
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


def format_number(value: float) -> str:
    return format(value, ".12g")


def row_time_offset(row_index: int, readout_seconds_per_row: float) -> float:
    """Row time offset = row_index * readout_seconds_per_row."""
    require(type(row_index) is int and row_index >= 0, "row_index must be a non-negative integer")
    readout = _finite(readout_seconds_per_row, "readout_seconds_per_row")
    return row_index * readout


def correction_permitted(readout_seconds_per_row: Any, source: Any) -> bool:
    """True only for a finite readout greater than 0 whose source is measured."""
    if source != SOURCE_MEASURED:
        return False
    if type(readout_seconds_per_row) is bool or not isinstance(readout_seconds_per_row, (int, float)):
        return False
    readout = float(readout_seconds_per_row)
    return math.isfinite(readout) and readout > 0.0


def corrected_row_coordinate(y: float, velocity_y: float, row_time: float) -> float:
    """Corrected row coordinate y' = y + velocity_y * row_time."""
    return y + velocity_y * row_time


def max_row_shift_pixels(shifts: list[float]) -> float:
    """Largest absolute applied row shift, in pixels. Unknown readout contributes none."""
    if not shifts:
        return 0.0
    return max(abs(shift) for shift in shifts)


def _finite(value: Any, label: str) -> float:
    require(type(value) is not bool and isinstance(value, (int, float)), f"{label} must be a number")
    number = float(value)
    require(math.isfinite(number), f"{label} must be finite")
    return number


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=RELATIVE_TOLERANCE, abs_tol=ABSOLUTE_TOLERANCE)


def _identity(value: Any, label: str) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(), f"{label} must be a non-empty string")
    return value


def _parse_readout(value: Any, source: Any) -> tuple[float | None, str | None]:
    if source is not None and source not in READOUT_SOURCES:
        raise ValueError("readoutSource is unsupported")
    if value is None:
        return None, source
    readout = _finite(value, "readoutSecondsPerRow")
    require(readout >= 0.0, "readoutSecondsPerRow must be non-negative")
    return readout, source


def _parse_rows(rows: Any) -> list[dict[str, Any]]:
    require(isinstance(rows, list) and len(rows) > 0, "rows must be a non-empty list")
    parsed: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        require(isinstance(row, dict) and set(row) == set(ROW_KEYS), f"rows[{index}] keys are invalid")
        row_index = row["rowIndex"]
        require(type(row_index) is int and row_index >= 0, f"rows[{index}].rowIndex must be a non-negative integer")
        role = row["role"]
        require(role in ROLES, f"rows[{index}].role is unsupported")
        parsed.append(
            {
                "rowIndex": row_index,
                "y": _finite(row["y"], f"rows[{index}].y"),
                "velocityY": _finite(row["velocityY"], f"rows[{index}].velocityY"),
                "role": role,
            }
        )
    return parsed


def _blank(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(rows)
    return {
        "originalY": [row["y"] for row in rows],
        "yPrime": [row["y"] for row in rows],
        "shiftPixels": [0.0] * count,
        "rowTimes": [None] * count,
    }


def _foreground_residual(rows: list[dict[str, Any]], readout: float, camera_velocity_y: float) -> float:
    residuals = []
    for row in rows:
        if row["role"] != ROLE_FOREGROUND:
            continue
        row_time = row_time_offset(row["rowIndex"], readout)
        residuals.append(abs((row["velocityY"] - camera_velocity_y) * row_time))
    return max_row_shift_pixels(residuals)


def plan_correction(
    readout_seconds_per_row: Any,
    readout_source: Any,
    camera_velocity_y: Any,
    warp_label: Any,
    claims_global_shutter_restored: Any,
    rows: Any,
) -> dict[str, Any]:
    """Decide whether a rolling-shutter warp may move rows.

    Unknown readout never produces a non-zero shift. A labelled
    ``rolling_shutter_correction`` without a measured positive readout is rejected.
    """
    readout, source = _parse_readout(readout_seconds_per_row, readout_source)
    camera = _finite(camera_velocity_y, "cameraVelocityY")
    require(warp_label in WARP_LABELS, "warpLabel is unsupported")
    require(type(claims_global_shutter_restored) is bool, "claimsGlobalShutterRestored must be a bool")
    parsed = _parse_rows(rows)
    permitted = correction_permitted(readout, source)
    placed = _blank(parsed)
    rejected: list[str] = []
    notes: list[str] = []
    applied = False

    if claims_global_shutter_restored:
        rejected.append(GLOBAL_SHUTTER_CLAIM)
        notes.append("claiming the correction restores global shutter is rejected")

    if warp_label == WARP_NONE:
        notes.append("no rolling-shutter warp was requested")
    elif warp_label == WARP_FLOW:
        notes.append("optical-flow approximation is separate from sensor-timing correction")
    elif not permitted:
        placed = _blank(parsed)
        if warp_label == WARP_SENSOR:
            rejected.append(UNKNOWN_READOUT_WARP)
            notes.append(
                "unknown or unmeasured readout rejects a global warp labelled rolling_shutter_correction"
            )
        else:
            rejected.append(UNMEASURED_WARP)
            notes.append("a warp that would shift rows is refused without a measured positive readout")
    elif warp_label == WARP_SENSOR:
        applied = True
        shifts: list[float] = []
        primes: list[float] = []
        times: list[float | None] = []
        for row in parsed:
            row_time = row_time_offset(row["rowIndex"], readout)
            prime = corrected_row_coordinate(row["y"], row["velocityY"], row_time)
            shift = prime - row["y"]
            shifts.append(shift)
            primes.append(prime)
            times.append(row_time)
        placed["yPrime"] = primes
        placed["shiftPixels"] = shifts
        placed["rowTimes"] = times
        notes.append("yPrime=y+velocityY*rowTime")
        notes.append("sensor-timing correction uses each row velocity, not one camera shear on the person")
    else:
        require(readout is not None, "measured readout missing")
        violating = False
        background_violation = False
        shifts = []
        primes = []
        times = []
        for row in parsed:
            row_time = row_time_offset(row["rowIndex"], readout)
            times.append(row_time)
            matches = _close(row["velocityY"], camera)
            if row["role"] == ROLE_FOREGROUND and not matches:
                violating = True
                primes.append(row["y"])
                shifts.append(0.0)
                notes.append(
                    "foreground row "
                    + str(row["rowIndex"])
                    + " kept at its original y; global camera velocity was not applied"
                )
            elif not matches:
                background_violation = True
                primes.append(row["y"])
                shifts.append(0.0)
            else:
                prime = corrected_row_coordinate(row["y"], row["velocityY"], row_time)
                primes.append(prime)
                shifts.append(prime - row["y"])
        if background_violation:
            rejected.append(BACKGROUND_VIOLATION)
        if violating:
            rejected.append(UNJUSTIFIED_GLOBAL)
            notes.append(ORACLE)
        applied = True
        placed["yPrime"] = primes
        placed["shiftPixels"] = shifts
        placed["rowTimes"] = times
        notes.append("yPrime=y+velocityY*rowTime")

    if applied and permitted and readout is not None:
        residual = _foreground_residual(parsed, readout, camera)
    else:
        residual = 0.0
    max_shift = max_row_shift_pixels(placed["shiftPixels"]) if applied else 0.0
    if not applied:
        require(all(shift == 0.0 for shift in placed["shiftPixels"]), "refused correction shifted a row")
        require(placed["yPrime"] == placed["originalY"], "refused correction moved a row")
        require(all(item is None for item in placed["rowTimes"]), "unknown readout invented a row time")
    phrase = CORRECTION_APPLIED_TRUE if applied else CORRECTION_APPLIED_FALSE
    max_token = "maxRowShiftPixels=" + format_number(max_shift)
    residual_token = "residualErrorPixels=" + format_number(residual)
    reasons = [phrase, max_token, residual_token]
    if not applied:
        reasons.append("rows were not shifted")
    reasons.extend(notes)
    unique_rejected: list[str] = []
    for claim in rejected:
        if claim not in unique_rejected:
            unique_rejected.append(claim)
    return {
        "correctionApplied": applied,
        "maxRowShiftPixels": max_shift,
        "residualErrorPixels": residual,
        "rejectedClaims": unique_rejected,
        "reasons": reasons,
        "originalY": placed["originalY"],
        "yPrime": placed["yPrime"],
        "shiftPixels": placed["shiftPixels"],
        "rowTimes": placed["rowTimes"],
    }


def case_result(
    case_id: str,
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[Any],
    questions: list[str],
) -> dict[str, Any]:
    """Seal one case result. Evidence must stay in preservedResults."""
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    return _seal(result)


def _seal(result: dict[str, Any]) -> dict[str, Any]:
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(result["decision"] in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(isinstance(result["reasons"], list) and result["reasons"], "reasons must be non-empty")
    require(isinstance(result["rejectedClaims"], list), "rejectedClaims must be a list")
    require(isinstance(result["preservedResults"], list) and result["preservedResults"], "evidence wiped")
    evidence = result["preservedResults"][0]
    require(isinstance(evidence, str) and evidence in result["preservedResults"], "evidence must be preserved")
    require(
        "physical S23 measurement was not run" in result["openQuestions"],
        "openQuestions must say physical S23 measurement was not run",
    )
    return result


def _decide(case_id: str, evidence: str, claim: str, apply_mutant: bool, plan: dict[str, Any]) -> dict[str, Any]:
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "goal: " + GOAL,
        "fixture: " + FIXTURE,
    ]
    reasons.extend(plan["reasons"])
    rejected = list(plan["rejectedClaims"])
    if apply_mutant:
        rejected.insert(0, MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("method: " + METHOD)
        reasons.append("deliverable: " + DELIVERABLE)
    phrase = CORRECTION_APPLIED_TRUE if plan["correctionApplied"] else CORRECTION_APPLIED_FALSE
    preserved = [
        evidence,
        claim,
        phrase,
        "maxRowShiftPixels=" + format_number(plan["maxRowShiftPixels"]),
        "residualErrorPixels=" + format_number(plan["residualErrorPixels"]),
        list(plan["originalY"]),
        list(plan["yPrime"]),
        list(plan["shiftPixels"]),
        list(plan["rowTimes"]),
    ]
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": [
            "physical S23 measurement was not run",
            "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
        ],
    }
    return _seal(result)


def _components(payload: dict[str, Any]) -> tuple:
    evidence = _identity(payload["evidenceId"], "evidenceId")
    claim = _identity(payload["claim"], "claim")
    require(type(payload["applyMutant"]) is bool, "applyMutant must be a bool")
    plan = plan_correction(
        payload["readoutSecondsPerRow"],
        payload["readoutSource"],
        payload["cameraVelocityY"],
        payload["warpLabel"],
        payload["claimsGlobalShutterRestored"],
        payload["rows"],
    )
    return evidence, claim, payload["applyMutant"], plan


def assess(document: dict) -> dict[str, Any]:
    """Apply the rolling-shutter oracle to one host fixture."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence, claim, apply_mutant, plan = _components(document)
    return _decide(PHASE, evidence, claim, apply_mutant, plan)


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate one rolling-shutter payload. Invalid shapes raise ValueError."""
    require(isinstance(payload, dict), "payload must be an object")
    missing = EVALUATE_KEYS - set(payload)
    extra = set(payload) - EVALUATE_KEYS
    require(not missing, "payload missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))
    case_id = _identity(payload["caseId"], "caseId")
    evidence, claim, apply_mutant, plan = _components(payload)
    return _decide(case_id, evidence, claim, apply_mutant, plan)
