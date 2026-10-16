#!/usr/bin/env python3
"""P114 Define synthetic shutter scope.

Host fixture only. A synthetic shutter scope lists input frames whose origin is
"captured" or "estimated", each with a weight. This module does not probe a
device, does not qualify a physical S23, and does not execute the TC-P114-01
through TC-P114-08 modules.
"""

from __future__ import annotations

import math
from typing import Any, Callable

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P114"
GOAL = "Make deferred motion rendering an explicit optional operation with clear source requirements."
METHOD = (
    "Estimate available temporal sampling and existing source blur before synthesizing "
    "additional exposure integration. State that already blurred or undersampled motion "
    "cannot always be corrected. Preserve original cadence and record any interpolation "
    "or frame synthesis."
)
FIXTURE = (
    "A short-exposure source, a heavily blurred source, and a rapidly moving thin object "
    "captured with insufficient temporal samples."
)
ORACLE = (
    "The tool applies only its qualified operation and labels unsupported reconstruction "
    "rather than promising perfect shutter conversion."
)
MUTANT = "Claim that any video can be converted exactly to any shutter angle."
DELIVERABLE = "Synthetic-shutter eligibility policy and limitation tests"

WEIGHT_TOLERANCE = 1e-6
ORIGINS = frozenset({"captured", "estimated"})
DISCLOSURE_RULE = (
    'Any frame with origin "estimated" must set contains_estimated true. '
    "If estimated frames exist and disclosed is false, reject (hidden hallucination)."
)

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "shutter_angle_degrees",
    "fps",
    "contains_estimated",
    "disclosed",
    "labelled_as_longer_sensor_exposure",
    "frames",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
OPEN_QUESTION = "physical S23 measurement was not run"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def evidence_id(value: object) -> str:
    require(
        isinstance(value, str) and bool(value.strip()) and value == value.strip(),
        "evidenceId must be a non-empty string",
    )
    return value


def repeat_text(value: object) -> str:
    require(isinstance(value, str) and bool(value.strip()), "repeat must be a non-empty string")
    return value


def flag(value: object, name: str) -> bool:
    require(type(value) is bool, name + " must be a bool")
    return value


def positive_number(value: object, name: str) -> float:
    require(isinstance(value, (int, float)) and type(value) is not bool, name + " must be a number")
    number = float(value)
    require(math.isfinite(number) and number > 0.0, name + " must be a positive finite number")
    return number


def finite_number(value: object, name: str) -> float:
    require(isinstance(value, (int, float)) and type(value) is not bool, name + " must be a number")
    number = float(value)
    require(math.isfinite(number), name + " must be finite")
    return number


def optional_positive(value: object, name: str) -> float | None:
    if value is None:
        return None
    return positive_number(value, name)


def exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def weight(value: object, name: str) -> float:
    require(isinstance(value, (int, float)) and type(value) is not bool, name + " must be a number")
    number = float(value)
    require(math.isfinite(number) and number >= 0.0, name + " must be a finite weight >= 0")
    return number


def parse_frames(frames: object, extra: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    """Each frame has origin captured or estimated, plus a weight. Extra keys are case data."""
    require(isinstance(frames, list) and len(frames) >= 1, "frames must be a non-empty list")
    allowed = {"origin", "weight", *extra}
    parsed: list[dict[str, Any]] = []
    for index, frame in enumerate(frames):
        require(isinstance(frame, dict), f"frame {index} must be an object")
        require(set(frame) == allowed, f"frame {index} keys must be {', '.join(sorted(allowed))}")
        origin = frame["origin"]
        require(origin in ORIGINS, f"frame {index} origin must be captured or estimated")
        parsed.append({
            "origin": origin,
            "weight": weight(frame["weight"], f"frame {index} weight"),
            **{key: frame[key] for key in extra},
        })
    return parsed


def simulated_exposure_seconds(shutter_angle_degrees: float, fps: float) -> float:
    """Exposure implied by a named shutter angle at a named frame rate. angle/360/fps."""
    return (shutter_angle_degrees / 360.0) / fps


def scope_problems(
    frames: list[dict[str, Any]],
    *,
    contains_estimated: bool,
    disclosed: bool,
    labelled_as_longer_sensor_exposure: bool,
    shutter_angle_degrees: float | None,
    fps: float | None,
) -> tuple[list[str], list[str]]:
    """Policy failures are claims. They do not raise. Invalid types are the caller's job.

    Weight sum must be 1 within 1e-6. Estimated frames require contains_estimated and
    disclosed. A captured-only integration may be recorded only when it is not labelled
    as a longer sensor exposure. The scope must name shutter angle and fps.
    """
    rejected: list[str] = []
    reasons: list[str] = []
    total = math.fsum(frame["weight"] for frame in frames)
    if abs(total - 1.0) > WEIGHT_TOLERANCE:
        rejected.append("unnormalized-temporal-weights")
        reasons.append(f"weight sum {total} is outside 1±{WEIGHT_TOLERANCE}")
    else:
        reasons.append(f"weight sum {total} is within {WEIGHT_TOLERANCE} of 1")

    estimated = any(frame["origin"] == "estimated" for frame in frames)
    if estimated and not contains_estimated:
        rejected.append("estimated-origin-requires-contains-estimated")
        reasons.append(DISCLOSURE_RULE)
    elif (not estimated) and contains_estimated:
        rejected.append("contains-estimated-without-estimated-origin")
        reasons.append("contains_estimated is true but every frame origin is captured")
    elif estimated:
        reasons.append("contains_estimated set because an estimated frame is present")

    if estimated and not disclosed:
        rejected.append("hidden-hallucination")
        reasons.append("hidden hallucination: estimated frames exist and disclosed is false")
    elif estimated and disclosed:
        reasons.append("estimated frames are disclosed")

    if labelled_as_longer_sensor_exposure:
        rejected.append("labelled-as-longer-sensor-exposure")
        reasons.append("scope must not be labelled as a longer sensor exposure")
    elif not estimated:
        reasons.append("captured-only integration is not labelled as a longer sensor exposure")
    else:
        reasons.append("disclosed synthetic integration is not a sensor exposure")

    if shutter_angle_degrees is None:
        rejected.append("missing-shutter-angle")
        reasons.append("scope is missing the shutter angle it simulates")
    if fps is None:
        rejected.append("missing-fps")
        reasons.append("scope is missing the fps it simulates")
    if shutter_angle_degrees is not None and fps is not None:
        exposure = simulated_exposure_seconds(shutter_angle_degrees, fps)
        reasons.append(
            f"simulates shutter angle {shutter_angle_degrees} degrees at {fps} fps ({exposure} s)"
        )
    return rejected, reasons


def open_questions(*extra: str) -> list[str]:
    questions = [OPEN_QUESTION]
    questions.extend(extra)
    return questions


def seal(result: dict[str, Any], evidence: str) -> dict[str, Any]:
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    decision = result["decision"]
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(isinstance(result["reasons"], list) and result["reasons"], "reasons must be a non-empty list")
    require(all(isinstance(item, str) and item for item in result["reasons"]), "reasons must be non-empty strings")
    for key in ("rejectedClaims", "preservedResults", "openQuestions"):
        require(isinstance(result[key], list), key + " must be a list")
        require(all(isinstance(item, str) and item for item in result[key]), key + " must be non-empty strings")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(OPEN_QUESTION in result["openQuestions"], "openQuestions must say physical S23 measurement was not run")
    return result


def preserved_for(evidence: str, angle: float | None, fps: float | None, extra: list[str] | None = None) -> list[str]:
    preserved = [evidence]
    if angle is not None and fps is not None:
        preserved.append(f"simulation:{angle}deg@{fps}fps")
    if extra:
        preserved.extend(item for item in extra if item not in preserved)
    return preserved


def assess(document: dict) -> dict[str, Any]:
    """Record an honest synthetic-shutter scope or reject a hidden or unnamed one."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = evidence_id(document["evidenceId"])
    claim = document["claim"]
    require(isinstance(claim, str) and bool(claim.strip()), "claim must be a non-empty string")
    apply_mutant = flag(document["applyMutant"], "applyMutant")
    frames = parse_frames(document["frames"])
    contains_estimated = flag(document["contains_estimated"], "contains_estimated")
    disclosed = flag(document["disclosed"], "disclosed")
    labelled = flag(document["labelled_as_longer_sensor_exposure"], "labelled_as_longer_sensor_exposure")
    angle = optional_positive(document["shutter_angle_degrees"], "shutter_angle_degrees")
    fps = optional_positive(document["fps"], "fps")

    rejected, scope_reasons = scope_problems(
        frames,
        contains_estimated=contains_estimated,
        disclosed=disclosed,
        labelled_as_longer_sensor_exposure=labelled,
        shutter_angle_degrees=angle,
        fps=fps,
    )
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        *scope_reasons,
    ]
    if apply_mutant:
        rejected.append(MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
    if rejected:
        decision = "rejected"
    else:
        decision = "recorded"
        reasons.append("method: " + METHOD)
        reasons.append("finite synthetic-shutter scope retained for " + evidence)
    result = {
        "caseId": PHASE,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved_for(evidence, angle, fps, [claim]),
        "openQuestions": open_questions(
            "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
        ),
    }
    return seal(result, evidence)


def check_extra(frames: list[dict[str, Any]], validators: dict[str, Callable[[object, str], Any]]) -> list[dict[str, Any]]:
    checked: list[dict[str, Any]] = []
    for index, frame in enumerate(frames):
        item = {"origin": frame["origin"], "weight": frame["weight"]}
        for key, validator in validators.items():
            item[key] = validator(frame[key], f"frame {index} {key}")
        checked.append(item)
    return checked
