#!/usr/bin/env python3
"""P113 Implement shutter-angle controls correctly.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P113-01 through TC-P113-08 modules.

Exposure time seconds = (shutter_angle_degrees / 360) / fps.
Frame interval seconds = 1 / fps.
A 180-degree shutter at 24 fps is exactly 1/48 s.
"""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Any

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P113"
TITLE = "Implement shutter-angle controls correctly"
GOAL = "Translate creative shutter angle into a feasible physical exposure request."
METHOD = (
    "Compute exposure from rational frame rate and angle, then validate sensor "
    "limits and actual applied results. Keep requested angle separate from "
    "effective exposure. When light levels prevent the desired setting, explain "
    "the tradeoff without silently changing cadence."
)
FIXTURE = (
    "One-hundred-eighty-degree shutter at twenty-four frames per second and a "
    "requested exposure exceeding the selected sensor interval."
)
ORACLE = (
    "The first maps to approximately one forty-eighth second and the second is "
    "rejected or visibly constrained."
)
MUTANT = "Treat shutter angle as an arbitrary blur-strength percentage."
DELIVERABLE = "Shutter-angle model and exposure feasibility tests"

FULL_TURN = Fraction(360)
REFERENCE_ANGLE = Fraction(180)
REFERENCE_FPS = Fraction(24)
REFERENCE_EXPOSURE = Fraction(1, 48)
REFERENCE_INTERVAL = Fraction(1, 24)
EXCEEDING_EXPOSURE = Fraction(1, 12)

RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = {"recorded", "rejected"}
FORBIDDEN_DECISIONS = {"qualified", "allowed"}

_DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "goal",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "deliverable",
    "shutterAngleDegrees",
    "fps",
    "reportedAngleDegrees",
    "reportedExposureSeconds",
    "sourceCadenceFps",
    "syntheticIntegration",
    "sensorConfirmed",
    "measurementId",
    "applyMutant",
    "exceedingRequest",
}
_EXCEEDING_KEYS = {
    "shutterAngleDegrees",
    "fps",
    "requestedExposureSeconds",
    "sensorIntervalSeconds",
    "syntheticIntegration",
    "sourceCadenceFps",
    "reportsAngleAsApplied",
}

_ALIASES = {
    "evidenceId": ("evidenceId", "evidence_id"),
    "shutterAngleDegrees": ("shutterAngleDegrees", "shutter_angle_degrees", "angle"),
    "fps": ("fps", "frameRate", "frame_rate"),
    "syntheticIntegration": ("syntheticIntegration", "synthetic_integration"),
    "sensorConfirmed": ("sensorConfirmed", "sensor_confirmed"),
    "measurementId": ("measurementId", "measurement_id"),
    "requestedExposureSeconds": (
        "requestedExposureSeconds",
        "requested_exposure_seconds",
        "exposureSeconds",
        "exposure_seconds",
    ),
    "reportedAngleDegrees": (
        "reportedAngleDegrees",
        "reported_angle_degrees",
        "displayedAngleDegrees",
        "displayed_angle_degrees",
    ),
    "reportedExposureSeconds": (
        "reportedExposureSeconds",
        "reported_exposure_seconds",
        "displayedExposureSeconds",
        "displayed_exposure_seconds",
    ),
    "sourceCadenceFps": ("sourceCadenceFps", "source_cadence_fps"),
    "sensorIntervalSeconds": ("sensorIntervalSeconds", "sensor_interval_seconds"),
    "sensorMaxExposureSeconds": (
        "sensorMaxExposureSeconds",
        "sensor_max_exposure_seconds",
    ),
    "applyMutant": ("applyMutant", "apply_mutant"),
    "reportsAngleAsApplied": ("reportsAngleAsApplied", "reports_angle_as_applied"),
    "blurPercentInterpretation": (
        "blurPercentInterpretation",
        "blur_percent_interpretation",
    ),
}
_KNOWN_KEYS = {alias for names in _ALIASES.values() for alias in names}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def format_number(value: Fraction) -> str:
    reduced = Fraction(value)
    if reduced.denominator == 1:
        return str(reduced.numerator)
    return f"{reduced.numerator}/{reduced.denominator}"


def parse_fraction(value: object, name: str) -> Fraction:
    """Parse a finite rational. Bools, non-finites, and garbage are ValueError."""
    if type(value) is bool:
        raise ValueError(f"{name} must be a real number")
    if type(value) is int:
        return Fraction(value)
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
        return Fraction(value)
    if isinstance(value, Fraction):
        return Fraction(value)
    if type(value) is str:
        text = value.strip()
        require(bool(text), f"{name} must be a real number")
        if "/" in text:
            left, right = text.split("/", 1)
            require("/" not in right, f"{name} must be a real number")
            try:
                return Fraction(int(left.strip()), int(right.strip()))
            except (TypeError, ValueError, ZeroDivisionError) as exc:
                raise ValueError(f"{name} must be a real number") from exc
        try:
            if any(token in text.lower() for token in ("nan", "inf")):
                raise ValueError(f"{name} must be finite")
            return Fraction(text)
        except (TypeError, ValueError, ZeroDivisionError) as exc:
            raise ValueError(f"{name} must be a real number") from exc
    if isinstance(value, dict):
        keys = set(value)
        require(
            keys == {"numerator", "denominator"},
            f"{name} rational must have numerator and denominator",
        )
        numerator = value["numerator"]
        denominator = value["denominator"]
        require(type(numerator) is int and type(denominator) is int,
                f"{name} numerator and denominator must be ints")
        require(denominator != 0, f"{name} denominator must not be zero")
        return Fraction(numerator, denominator)
    raise ValueError(f"{name} must be a real number")


def parse_positive(value: object, name: str) -> Fraction:
    number = parse_fraction(value, name)
    if number <= 0:
        raise ValueError(f"{name} must be > 0")
    return number


def exposure_seconds(shutter_angle_degrees: object, fps: object) -> Fraction:
    """Return (shutter_angle_degrees / 360) / fps.

    Non-physical inputs raise ValueError. An angle above 360 is still computed
    so the caller can reject it; non-positive angles are not physical.
    """
    angle = parse_positive(shutter_angle_degrees, "shutter_angle_degrees")
    rate = parse_positive(fps, "fps")
    return (angle / FULL_TURN) / rate


def frame_interval_seconds(fps: object) -> Fraction:
    """Return 1 / fps. Non-physical frame rates raise ValueError."""
    rate = parse_positive(fps, "fps")
    return Fraction(1) / rate


def _present(payload: dict, key: str) -> bool:
    return any(name in payload for name in _ALIASES[key])


def _pick(payload: dict, key: str, default: Any = None) -> Any:
    for name in _ALIASES[key]:
        if name in payload:
            return payload[name]
    return default


def _bool(value: object, name: str) -> bool:
    require(type(value) is bool, f"{name} must be a bool")
    return value


def _evidence(value: object) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(),
            "evidenceId must be a non-empty string")
    return value


def _measurement(value: object) -> str | None:
    if value is None:
        return None
    require(isinstance(value, str), "measurementId must be a string or null")
    text = value.strip()
    if not text or text != value:
        return None
    return value


def _optional_positive(payload: dict, key: str) -> Fraction | None:
    if not _present(payload, key):
        return None
    value = _pick(payload, key)
    if value is None:
        return None
    return parse_positive(value, key)


def physical_questions() -> list[str]:
    return [
        "physical S23 capture was not run",
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
    ]


def finish_result(
    case_id: str,
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str] | None = None,
) -> dict[str, Any]:
    require(decision in DECISIONS, "decision must be recorded or rejected")
    require(decision not in FORBIDDEN_DECISIONS, "decision must not be qualified or allowed")
    require(bool(reasons), "reasons required")
    require(all(isinstance(item, str) and item for item in reasons), "reasons must be text")
    require(all(isinstance(item, str) for item in rejected), "rejectedClaims must be text")
    require(all(isinstance(item, str) and item for item in preserved), "preservedResults must be text")
    open_questions = list(questions) if questions is not None else physical_questions()
    if not any("physical S23" in item for item in open_questions):
        open_questions = ["physical S23 capture was not run", *open_questions]
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": open_questions,
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    return result


def reject_more(result: dict[str, Any], claims: list[str], extra_reasons: list[str]) -> dict[str, Any]:
    """Keep a judged result, or flip it to rejected when more claims apply."""
    extra = [claim for claim in claims if claim not in result["rejectedClaims"]]
    if not extra and not extra_reasons:
        return result
    merged_claims = list(result["rejectedClaims"]) + extra
    reasons = list(result["reasons"]) + list(extra_reasons)
    decision = "rejected" if merged_claims else result["decision"]
    return finish_result(
        result["caseId"],
        decision,
        reasons,
        merged_claims,
        result["preservedResults"],
        result["openQuestions"],
    )


def _exposure_lines(
    angle: Fraction,
    fps: Fraction,
    effective: Fraction,
    *,
    sensor_confirmed: bool,
    measurement_id: str | None,
    evidence: str,
    source_cadence: Fraction,
) -> tuple[list[str], list[str], list[str]]:
    derived = exposure_seconds(angle, fps)
    interval = frame_interval_seconds(fps)
    reasons = [
        "exposure time seconds = (shutter_angle_degrees / 360) / fps",
        f"frame interval seconds = 1/fps = {format_number(interval)} s",
        f"requested angle {format_number(angle)} degrees",
        f"effective exposure {format_number(effective)} s",
        (
            f"{format_number(angle)} deg at {format_number(fps)} fps "
            f"maps to {format_number(derived)} s"
        ),
    ]
    if angle == REFERENCE_ANGLE and fps == REFERENCE_FPS:
        reasons.append("180 deg at 24 fps = 1/48 s")
    preserved = [
        evidence,
        f"requested-angle-degrees:{format_number(angle)}",
        f"effective-exposure-seconds:{format_number(effective)}",
        f"formula-exposure-seconds:{format_number(derived)}",
        f"frame-interval-seconds:{format_number(interval)}",
        f"source-cadence-fps:{format_number(source_cadence)}",
        f"sensor-confirmed:{str(sensor_confirmed).lower()}",
    ]
    rejected: list[str] = []
    if sensor_confirmed:
        if measurement_id is None:
            rejected.append("sensor-confirmed-without-measurement-id")
            reasons.append("sensor_confirmed is true but no measurement id was supplied")
        else:
            preserved.append(f"measurement-id:{measurement_id}")
            reasons.append(
                "sensor used the shutter angle only as recorded by measurement "
                + measurement_id
            )
            reasons.append("a measurement id is not a physical S23 qualification")
    else:
        reasons.append(
            "sensor_confirmed is false; no sensor-angle claim is made"
        )
    return reasons, preserved, rejected


def judge_shutter(payload: dict, case_id: str = PHASE) -> dict[str, Any]:
    """Judge one shutter-angle request.

    Effective rotary exposure is (angle / 360) / fps. Exposure longer than the
    frame interval is rejected unless synthetic_integration is explicitly true.
    Angles above 360 are rejected even then. Requested angle and effective
    exposure are both reported. A 180-degree label with any other duration is
    an inconsistency and is rejected.
    """
    require(isinstance(payload, dict), "payload must be an object")
    extra = set(payload) - _KNOWN_KEYS
    require(not extra, "unexpected fields: " + ", ".join(sorted(extra)))
    for required in ("evidenceId", "shutterAngleDegrees", "fps"):
        require(_present(payload, required), f"{required} is required")

    evidence = _evidence(_pick(payload, "evidenceId"))
    angle = parse_positive(_pick(payload, "shutterAngleDegrees"), "shutter_angle_degrees")
    fps = parse_positive(_pick(payload, "fps"), "fps")
    synthetic = False
    if _present(payload, "syntheticIntegration"):
        synthetic = _bool(_pick(payload, "syntheticIntegration"), "synthetic_integration")
    sensor_confirmed = False
    if _present(payload, "sensorConfirmed"):
        sensor_confirmed = _bool(_pick(payload, "sensorConfirmed"), "sensor_confirmed")
    measurement_id = None
    if _present(payload, "measurementId"):
        measurement_id = _measurement(_pick(payload, "measurementId"))
    apply_mutant = False
    if _present(payload, "applyMutant"):
        apply_mutant = _bool(_pick(payload, "applyMutant"), "applyMutant")
    blur_percent = False
    if _present(payload, "blurPercentInterpretation"):
        blur_percent = _bool(
            _pick(payload, "blurPercentInterpretation"),
            "blurPercentInterpretation",
        )
    requested = _optional_positive(payload, "requestedExposureSeconds")
    reported_angle = None
    if _present(payload, "reportedAngleDegrees") and _pick(payload, "reportedAngleDegrees") is not None:
        reported_angle = parse_positive(
            _pick(payload, "reportedAngleDegrees"),
            "reported_angle_degrees",
        )
    reported_exposure = _optional_positive(payload, "reportedExposureSeconds")
    reports_applied = True
    if _present(payload, "reportsAngleAsApplied"):
        reports_applied = _bool(
            _pick(payload, "reportsAngleAsApplied"),
            "reports_angle_as_applied",
        )
    source_cadence = fps
    if _present(payload, "sourceCadenceFps") and _pick(payload, "sourceCadenceFps") is not None:
        source_cadence = parse_positive(_pick(payload, "sourceCadenceFps"), "source_cadence_fps")
    sensor_interval = _optional_positive(payload, "sensorIntervalSeconds")
    sensor_max = _optional_positive(payload, "sensorMaxExposureSeconds")

    derived = exposure_seconds(angle, fps)
    interval = frame_interval_seconds(fps)
    effective = derived if requested is None else requested
    reasons, preserved, rejected = _exposure_lines(
        angle,
        fps,
        effective,
        sensor_confirmed=sensor_confirmed,
        measurement_id=measurement_id,
        evidence=evidence,
        source_cadence=source_cadence,
    )
    reasons.append("oracle: " + ORACLE)

    if apply_mutant or blur_percent:
        rejected.append(MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
        reasons.append(
            "shutter angle is an exposure fraction of the frame, not a blur-strength percentage"
        )
    if angle > FULL_TURN:
        rejected.append("angle-above-360")
        reasons.append(
            f"shutter angle {format_number(angle)} degrees is above 360 and is rejected"
        )
    if source_cadence != fps:
        rejected.append("silent-cadence-change")
        reasons.append(
            "source cadence "
            f"{format_number(source_cadence)} fps differs from the shutter frame rate; "
            "cadence was not rewritten"
        )
    else:
        reasons.append(f"source cadence {format_number(source_cadence)} fps was not changed")

    exceeds_frame = effective > interval
    if exceeds_frame and synthetic is not True:
        rejected.append("exposure-exceeds-frame-interval")
        reasons.append(
            f"effective exposure {format_number(effective)} s exceeds frame interval "
            f"{format_number(interval)} s"
        )
        reasons.append(
            "rejected unless synthetic_integration is explicitly true; cadence unchanged"
        )
    elif exceeds_frame and synthetic is True and angle <= FULL_TURN:
        reasons.append(
            "synthetic_integration is true, so an exposure longer than one frame "
            "is an explicit synthetic request rather than a rotary shutter"
        )
        reasons.append(
            "requested angle "
            f"{format_number(angle)} degrees is not the applied shutter for effective "
            f"exposure {format_number(effective)} s; the rotary exposure for that angle is "
            f"{format_number(derived)} s"
        )
    if sensor_interval is not None and effective > sensor_interval and synthetic is not True:
        if sensor_interval != interval and "exposure-exceeds-sensor-interval" not in rejected:
            rejected.append("exposure-exceeds-sensor-interval")
            reasons.append(
                f"requested exposure {format_number(effective)} s exceeds the selected "
                f"sensor interval {format_number(sensor_interval)} s and is rejected "
                "without changing cadence"
            )
    if sensor_max is not None and effective > sensor_max:
        rejected.append("exposure-exceeds-sensor-limit")
        reasons.append(
            "light or sensor limit "
            f"{format_number(sensor_max)} s prevents the desired exposure "
            f"{format_number(effective)} s; the tradeoff is explicit and cadence stays "
            f"{format_number(fps)} fps"
        )

    displayed_angle = reported_angle if reported_angle is not None else (
        angle if reports_applied else None
    )
    displayed_exposure = reported_exposure if reported_exposure is not None else (
        effective if reports_applied else None
    )
    if displayed_angle is not None and displayed_exposure is not None:
        matching = exposure_seconds(displayed_angle, fps)
        if displayed_exposure != matching:
            rejected.append("angle-exposure-inconsistency")
            reasons.append(
                f"reporting a {format_number(displayed_angle)}-degree shutter while "
                f"exposure is {format_number(displayed_exposure)} s is rejected; "
                f"that angle at {format_number(fps)} fps is {format_number(matching)} s"
            )
    if reports_applied and effective != derived and "angle-exposure-inconsistency" not in rejected:
        rejected.append("angle-exposure-inconsistency")
        reasons.append(
            f"reporting a {format_number(angle)}-degree shutter while exposure is "
            f"{format_number(effective)} s is rejected; the angle requires "
            f"{format_number(derived)} s"
        )
    if (
        displayed_angle == REFERENCE_ANGLE
        and displayed_exposure is not None
        and displayed_exposure != exposure_seconds(REFERENCE_ANGLE, fps)
        and "angle-exposure-inconsistency" not in rejected
    ):
        rejected.append("angle-exposure-inconsistency")
        reasons.append(
            "reporting a 180-degree shutter while exposure is a different duration is rejected"
        )

    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("requested angle and effective exposure were retained together")
        reasons.append("method: " + METHOD)
    return finish_result(case_id, decision, reasons, rejected, preserved, physical_questions())


def _phase_request(document: dict) -> dict[str, Any]:
    return {
        "evidenceId": document["evidenceId"],
        "shutterAngleDegrees": document["shutterAngleDegrees"],
        "fps": document["fps"],
        "reportedAngleDegrees": document["reportedAngleDegrees"],
        "reportedExposureSeconds": document["reportedExposureSeconds"],
        "sourceCadenceFps": document["sourceCadenceFps"],
        "syntheticIntegration": document["syntheticIntegration"],
        "sensorConfirmed": document["sensorConfirmed"],
        "measurementId": document["measurementId"],
        "applyMutant": document["applyMutant"],
        "reportsAngleAsApplied": True,
    }


def _exceeding_request(document: dict) -> dict[str, Any]:
    extra = document["exceedingRequest"]
    return {
        "evidenceId": document["evidenceId"],
        "shutterAngleDegrees": extra["shutterAngleDegrees"],
        "fps": extra["fps"],
        "requestedExposureSeconds": extra["requestedExposureSeconds"],
        "sensorIntervalSeconds": extra["sensorIntervalSeconds"],
        "syntheticIntegration": extra["syntheticIntegration"],
        "sourceCadenceFps": extra["sourceCadenceFps"],
        "reportsAngleAsApplied": extra["reportsAngleAsApplied"],
        "sensorConfirmed": False,
        "measurementId": None,
        "applyMutant": False,
    }


def validate_document(document: dict) -> None:
    require(isinstance(document, dict), "document must be an object")
    missing = _DOCUMENT_KEYS - set(document)
    extra = set(document) - _DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    _evidence(document["evidenceId"])
    require(document["goal"] == GOAL, "goal text drifted")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    require(document["deliverable"] == DELIVERABLE, "deliverable text drifted")
    require(type(document["syntheticIntegration"]) is bool, "syntheticIntegration must be a bool")
    require(type(document["sensorConfirmed"]) is bool, "sensorConfirmed must be a bool")
    require(type(document["applyMutant"]) is bool, "applyMutant must be a bool")
    if document["measurementId"] is not None:
        require(_measurement(document["measurementId"]) is not None, "measurementId must be a non-empty string")
    exceeding = document["exceedingRequest"]
    require(isinstance(exceeding, dict), "exceedingRequest must be an object")
    missing_extra = _EXCEEDING_KEYS - set(exceeding)
    extra_fields = set(exceeding) - _EXCEEDING_KEYS
    require(not missing_extra, "exceedingRequest missing fields: " + ", ".join(sorted(missing_extra)))
    require(not extra_fields, "exceedingRequest has unexpected fields: " + ", ".join(sorted(extra_fields)))
    require(type(exceeding["syntheticIntegration"]) is bool, "exceeding syntheticIntegration must be a bool")
    require(type(exceeding["reportsAngleAsApplied"]) is bool, "exceeding reportsAngleAsApplied must be a bool")


def assess(document: dict) -> dict[str, Any]:
    """Assess the authored host fixture.

    180 degrees at 24 fps maps to 1/48 s. The second exposure, which exceeds the
    selected sensor interval, must be rejected or visibly constrained. The phase
    decision is recorded only when both hold, the sensor is not claimed, and the
    blur-percentage mutant is absent.
    """
    validate_document(document)
    primary = judge_shutter(_phase_request(document), PHASE)
    exceeding = judge_shutter(_exceeding_request(document), PHASE)
    evidence = document["evidenceId"]
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "180 deg at 24 fps = 1/48 s",
        *primary["reasons"],
    ]
    rejected: list[str] = []
    if document["applyMutant"]:
        rejected.append(MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
    if "sensor used the shutter angle only as recorded" in " ".join(primary["reasons"]):
        rejected.append("host-fixture-must-not-claim-sensor")
        reasons.append("host fixture must not make a sensor-angle claim")
    if primary["decision"] != "recorded":
        for claim in primary["rejectedClaims"]:
            if claim not in rejected:
                rejected.append(claim)
        reasons.append("primary shutter request was not a consistent recorded mapping")
    else:
        reasons.append("primary 180-degree shutter at 24 fps is recorded as 1/48 s")
    if exceeding["decision"] == "recorded":
        rejected.append("exceeding-exposure-was-not-rejected")
        reasons.append(
            "the exposure that exceeds the selected sensor interval was not rejected or constrained"
        )
    else:
        reasons.append(
            "the requested exposure that exceeds the selected sensor interval is rejected "
            "without changing source cadence"
        )
        reasons.append("second request rejected claims: " + ",".join(exceeding["rejectedClaims"]))
    if document["sensorConfirmed"] is not False:
        reasons.append("host fixture must leave sensor_confirmed false")
        if "sensor-confirmed-without-measurement-id" not in rejected:
            rejected.append("host-fixture-must-not-claim-sensor")
    else:
        reasons.append(
            "sensor_confirmed is false; no sensor-angle claim is made"
        )
    angle_token = f"requested-angle-degrees:{format_number(REFERENCE_ANGLE)}"
    exposure_token = f"effective-exposure-seconds:{format_number(REFERENCE_EXPOSURE)}"
    if angle_token not in primary["preservedResults"] or exposure_token not in primary["preservedResults"]:
        if "angle-or-exposure-not-reported" not in rejected:
            rejected.append("angle-or-exposure-not-reported")
        reasons.append("the result must report the requested angle and the effective exposure")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("method: " + METHOD)
        reasons.append("fixture: " + FIXTURE)
    preserved = [
        evidence,
        angle_token,
        exposure_token,
        f"frame-interval-seconds:{format_number(REFERENCE_INTERVAL)}",
        "sensor-confirmed:false",
        f"source-cadence-fps:{format_number(REFERENCE_FPS)}",
        "exceeding-exposure-seconds:1/12",
        "exceeding-sensor-interval-seconds:1/24",
    ]
    require(evidence in preserved, "evidence must be preserved")
    return finish_result(PHASE, decision, reasons, rejected, preserved, physical_questions())


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate a shutter request, or the phase document when one is given."""
    require(isinstance(payload, dict), "payload must be an object")
    if payload.get("phase") == PHASE and "schemaVersion" in payload and "exceedingRequest" in payload:
        return assess(payload)
    return judge_shutter(payload, PHASE)
