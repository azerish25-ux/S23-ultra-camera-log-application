#!/usr/bin/env python3
"""P119 Add practical cinematographic guidance.

Host fixture only. Statements are advice. They are recorded only when each one
is bound to a measured limit and stays inside that limit. This module does not
probe a device, does not qualify a physical S23, and does not change camera
settings.

A measured limit carries fps, shutter_angle (maximum degrees the mode
supports), max_stable_motion_px, and mode_available. Guidance that recommends a
shutter or fps outside that limit is rejected. Guidance that promises
film-stock fidelity, ARRI equivalence, or sensor-derived Log is rejected.
Advice with no measured limit id is ungrounded and is rejected. The sentence
"this mode cannot do 180 degrees at this fps" is recorded when the bound limit
really cannot reach 180 degrees.
"""

from __future__ import annotations

import math
from typing import Any


BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P119"
WORKSTREAM = 15
TITLE = "Add practical cinematographic guidance"
DEPENDENCIES = ("P118",)
SLUG = "add_practical_cinematographic_guidance"
GOAL = (
    "Help the user obtain suitable source footage instead of relying on "
    "postprocessing to conceal capture failures."
)
METHOD = (
    "Provide optional guidance for exposure, focus, source sharpness, clipping, "
    "framing, and virtual-lens compatibility. Separate advice from automatic changes. "
    "Do not change physical camera position or lighting claims through software labels."
)
FIXTURE = (
    "A heavily clipped face and a virtual shallow-focus recipe selected for a "
    "physically out-of-focus source."
)
ORACLE = (
    "The app explains the source limitations and preserves user control rather "
    "than promising restoration."
)
MUTANT = "Hide clipping warnings whenever a cinematic preset is active."
DELIVERABLE = "Capture guidance rules and nonintrusive UI tests"
CASE_IDS = (
    "TC-P119-01",
    "TC-P119-02",
    "TC-P119-03",
    "TC-P119-04",
    "TC-P119-05",
    "TC-P119-06",
    "TC-P119-07",
    "TC-P119-08",
)

HONEST_180 = "this mode cannot do 180 degrees at this fps"
REFERENCE_SHUTTER_DEGREES = 180.0
TOLERANCE = 1e-9
PROMISE_FILM_STOCK = "film-stock fidelity"
PROMISE_ARRI = "ARRI equivalence"
PROMISE_SENSOR_LOG = "sensor-derived Log"
CLAIM_FILM_STOCK = "film-stock-fidelity"
CLAIM_ARRI = "arri-equivalence"
CLAIM_SENSOR_LOG = "sensor-derived-log"
CLAIM_UNGROUNDED = "ungrounded-guidance"
CLAIM_UNSUPPORTED_SHUTTER = "unsupported-shutter"
CLAIM_UNSUPPORTED_FPS = "unsupported-fps"
CLAIM_FALSE_180 = "false-shutter-limitation"
CLAIM_MODE_UNAVAILABLE = "mode-unavailable"
CLAIM_MOTION = "motion-exceeds-measured-limit"
CLAIM_UNGROUNDED_MOTION = "ungrounded-motion"
CLAIM_NOT_SELECTED = "guidance-not-bound-to-selected-mode"
CLAIM_SETTINGS = "advice-changes-settings"
CLAIM_CAMERA = "software-changed-camera-position"
CLAIM_LIGHTING = "software-relabelled-lighting"
CLAIM_CLIP = "clipping-not-explained"
CLAIM_FOCUS = "focus-not-explained"
CLAIM_RESTORATION = "promised-restoration"
FORBIDDEN_PROMISES = (
    (PROMISE_FILM_STOCK, CLAIM_FILM_STOCK),
    (PROMISE_ARRI, CLAIM_ARRI),
    (PROMISE_SENSOR_LOG, CLAIM_SENSOR_LOG),
)

LIMIT_KEYS = {"id", "fps", "shutter_angle", "max_stable_motion_px", "mode_available"}
STATEMENT_KEYS = {
    "text",
    "limitId",
    "recommendsFps",
    "recommendsShutter",
    "observedMotionPx",
    "claimsStableMotion",
    "promises",
}
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "selectedLimitId",
    "measuredLimits",
    "guidance",
    "sourceClipped",
    "sourceOutOfFocus",
    "virtualShallowFocusSelected",
    "cinematicPresetActive",
    "clippingWarningsVisible",
    "adviceChangesSettings",
    "changesCameraPosition",
    "relabelsLighting",
}
EVALUATE_KEYS = {
    "caseId",
    "evidenceId",
    "claim",
    "applyMutant",
    "selectedLimitId",
    "measuredLimits",
    "guidance",
    "sourceClipped",
    "sourceOutOfFocus",
    "virtualShallowFocusSelected",
    "cinematicPresetActive",
    "clippingWarningsVisible",
    "adviceChangesSettings",
    "changesCameraPosition",
    "relabelsLighting",
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


def exposure_seconds(shutter_angle: float, fps: float) -> float:
    """Exposure time in seconds for a shutter angle at a measured frame rate."""
    require(fps > 0.0, "fps must be positive")
    return (shutter_angle / 360.0) / fps


def _fmt(value: float) -> str:
    return format(value, ".12g")


def _reject(bucket: list[str], token: str) -> None:
    if token not in bucket:
        bucket.append(token)


def _finite(value: object, label: str) -> float:
    require(type(value) is not bool, f"{label} must be a number")
    require(isinstance(value, (int, float)), f"{label} must be a number")
    number = float(value)
    require(math.isfinite(number), f"{label} must be finite")
    return number


def _optional_number(value: object, label: str) -> float | None:
    if value is None:
        return None
    return _finite(value, label)


def _text(value: object, label: str) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(), f"{label} must be a non-empty string")
    return value


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, f"{label} must be a bool")
    return value


def _supports_shutter(limit: dict[str, Any], angle: float) -> bool:
    return bool(limit["mode_available"]) and 0.0 < angle <= limit["shutter_angle"] + TOLERANCE


def _supports_fps(limit: dict[str, Any], fps: float) -> bool:
    return bool(limit["mode_available"]) and abs(fps - limit["fps"]) <= TOLERANCE


def _promises_restoration(text: str) -> bool:
    lowered = text.lower()
    if "restor" not in lowered:
        return False
    if (
        "not restore" in lowered
        or "cannot restore" in lowered
        or "will not restore" in lowered
        or "won't restore" in lowered
    ):
        return False
    return True


def _parse_limit(item: object, index: int) -> dict[str, Any]:
    require(isinstance(item, dict), f"measuredLimits[{index}] must be an object")
    require(set(item) == LIMIT_KEYS, f"measuredLimits[{index}] keys must be the measured limit fields")
    limit_id = _text(item["id"], f"measuredLimits[{index}].id")
    fps = _finite(item["fps"], f"measuredLimits[{index}].fps")
    shutter = _finite(item["shutter_angle"], f"measuredLimits[{index}].shutter_angle")
    motion = _finite(item["max_stable_motion_px"], f"measuredLimits[{index}].max_stable_motion_px")
    available = _bool(item["mode_available"], f"measuredLimits[{index}].mode_available")
    require(fps > 0.0, f"measuredLimits[{index}].fps must be positive")
    require(0.0 < shutter <= 360.0, f"measuredLimits[{index}].shutter_angle must be inside (0, 360]")
    require(motion >= 0.0, f"measuredLimits[{index}].max_stable_motion_px must be >= 0")
    return {
        "id": limit_id,
        "fps": fps,
        "shutter_angle": shutter,
        "max_stable_motion_px": motion,
        "mode_available": available,
    }


def _parse_limits(measured_limits: object) -> dict[str, dict[str, Any]]:
    require(isinstance(measured_limits, list) and measured_limits, "measuredLimits must be a non-empty list")
    found: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(measured_limits):
        parsed = _parse_limit(item, index)
        require(parsed["id"] not in found, "duplicate measured limit id")
        found[parsed["id"]] = parsed
    return found


def _parse_limit_id(value: object, index: int) -> str | None:
    if value is None or value == "":
        return None
    require(isinstance(value, str), f"guidance[{index}].limitId must be a string or null")
    require(value == value.strip(), f"guidance[{index}].limitId must not have surrounding whitespace")
    return value


def _parse_statement(item: object, index: int) -> dict[str, Any]:
    require(isinstance(item, dict), f"guidance[{index}] must be an object")
    require(set(item) == STATEMENT_KEYS, f"guidance[{index}] keys are invalid")
    text = _text(item["text"], f"guidance[{index}].text")
    recommends_fps = _optional_number(item["recommendsFps"], f"guidance[{index}].recommendsFps")
    recommends_shutter = _optional_number(item["recommendsShutter"], f"guidance[{index}].recommendsShutter")
    observed = _optional_number(item["observedMotionPx"], f"guidance[{index}].observedMotionPx")
    if recommends_fps is not None:
        require(recommends_fps > 0.0, f"guidance[{index}].recommendsFps must be positive")
    if recommends_shutter is not None:
        require(
            0.0 < recommends_shutter <= 360.0,
            f"guidance[{index}].recommendsShutter must be inside (0, 360]",
        )
    if observed is not None:
        require(observed >= 0.0, f"guidance[{index}].observedMotionPx must be >= 0")
    promises = item["promises"]
    require(isinstance(promises, list), f"guidance[{index}].promises must be a list")
    parsed_promises = []
    for promise_index, promise in enumerate(promises):
        parsed_promises.append(_text(promise, f"guidance[{index}].promises[{promise_index}]"))
    return {
        "text": text,
        "limitId": _parse_limit_id(item["limitId"], index),
        "recommendsFps": recommends_fps,
        "recommendsShutter": recommends_shutter,
        "observedMotionPx": observed,
        "claimsStableMotion": _bool(item["claimsStableMotion"], f"guidance[{index}].claimsStableMotion"),
        "promises": parsed_promises,
    }


def _parse_guidance(guidance: object) -> list[dict[str, Any]]:
    require(isinstance(guidance, list), "guidance must be a list")
    return [_parse_statement(item, index) for index, item in enumerate(guidance)]


def judge_guidance(
    measured_limits: object,
    selected_limit_id: object,
    guidance: object,
) -> dict[str, Any]:
    """Judge statements against measured fps, shutter, motion, and availability.

    Invalid shapes raise ValueError. A well-formed statement that is not bound
    to a measured limit is rejected as ungrounded guidance rather than dropped.
    """
    limits = _parse_limits(measured_limits)
    selected_id = _text(selected_limit_id, "selectedLimitId")
    require(selected_id in limits, "selectedLimitId is not a measured limit")
    selected = limits[selected_id]
    statements = _parse_guidance(guidance)
    rejected: list[str] = []
    reasons = [
        "selectedLimitId=" + selected_id,
        "measured fps="
        + _fmt(selected["fps"])
        + " shutter_angle="
        + _fmt(selected["shutter_angle"])
        + " max_stable_motion_px="
        + _fmt(selected["max_stable_motion_px"])
        + " mode_available="
        + str(selected["mode_available"]).lower(),
    ]
    texts: list[str] = []
    for index, statement in enumerate(statements):
        texts.append(statement["text"])
        reasons.append(f"guidance[{index}]: {statement['text']}")
        limit_id = statement["limitId"]
        if limit_id is None or limit_id not in limits:
            _reject(rejected, CLAIM_UNGROUNDED)
            reasons.append(f"guidance[{index}] has no measured limit id")
            continue
        limit = limits[limit_id]
        if limit_id != selected_id:
            _reject(rejected, CLAIM_NOT_SELECTED)
            reasons.append(f"guidance[{index}] is not bound to the selected mode")
            continue
        if not limit["mode_available"]:
            _reject(rejected, CLAIM_MODE_UNAVAILABLE)
            reasons.append(f"guidance[{index}] selected mode is not available")
        promise_blob = statement["text"] + "\n" + "\n".join(statement["promises"])
        for phrase, token in FORBIDDEN_PROMISES:
            if phrase in promise_blob:
                _reject(rejected, token)
                reasons.append(f"guidance[{index}] promises {phrase}")
        if _promises_restoration(statement["text"]):
            _reject(rejected, CLAIM_RESTORATION)
            reasons.append(f"guidance[{index}] promises restoration")
        if statement["recommendsShutter"] is not None and not _supports_shutter(limit, statement["recommendsShutter"]):
            _reject(rejected, CLAIM_UNSUPPORTED_SHUTTER)
            reasons.append(
                f"guidance[{index}] recommends shutter "
                + _fmt(statement["recommendsShutter"])
                + " but the mode supports at most "
                + _fmt(limit["shutter_angle"])
            )
        if statement["recommendsFps"] is not None and not _supports_fps(limit, statement["recommendsFps"]):
            _reject(rejected, CLAIM_UNSUPPORTED_FPS)
            reasons.append(
                f"guidance[{index}] recommends fps "
                + _fmt(statement["recommendsFps"])
                + " but the mode measures "
                + _fmt(limit["fps"])
            )
        if HONEST_180 in statement["text"]:
            if limit["shutter_angle"] + TOLERANCE < REFERENCE_SHUTTER_DEGREES:
                reasons.append(
                    "honest-180: fps="
                    + _fmt(limit["fps"])
                    + " shutter_angle="
                    + _fmt(limit["shutter_angle"])
                    + " exposureSeconds="
                    + _fmt(exposure_seconds(limit["shutter_angle"], limit["fps"]))
                    + " reference180ExposureSeconds="
                    + _fmt(exposure_seconds(REFERENCE_SHUTTER_DEGREES, limit["fps"]))
                )
            else:
                _reject(rejected, CLAIM_FALSE_180)
                reasons.append(
                    f"guidance[{index}] says 180 degrees is impossible but shutter_angle="
                    + _fmt(limit["shutter_angle"])
                )
        if statement["claimsStableMotion"] and statement["observedMotionPx"] is None:
            _reject(rejected, CLAIM_UNGROUNDED_MOTION)
            reasons.append(f"guidance[{index}] claims stable motion without a measurement")
        elif (
            statement["claimsStableMotion"]
            and statement["observedMotionPx"] is not None
            and statement["observedMotionPx"] > limit["max_stable_motion_px"] + TOLERANCE
        ):
            _reject(rejected, CLAIM_MOTION)
            reasons.append(
                f"guidance[{index}] motion "
                + _fmt(statement["observedMotionPx"])
                + " exceeds max_stable_motion_px "
                + _fmt(limit["max_stable_motion_px"])
            )
    decision = "rejected" if rejected else "recorded"
    preserved = [dict(selected), list(texts)]
    return {
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
    }


def _source_flags(payload: dict) -> dict[str, bool]:
    return {
        "sourceClipped": _bool(payload["sourceClipped"], "sourceClipped"),
        "sourceOutOfFocus": _bool(payload["sourceOutOfFocus"], "sourceOutOfFocus"),
        "virtualShallowFocusSelected": _bool(
            payload["virtualShallowFocusSelected"], "virtualShallowFocusSelected"
        ),
        "cinematicPresetActive": _bool(payload["cinematicPresetActive"], "cinematicPresetActive"),
        "clippingWarningsVisible": _bool(payload["clippingWarningsVisible"], "clippingWarningsVisible"),
        "adviceChangesSettings": _bool(payload["adviceChangesSettings"], "adviceChangesSettings"),
        "changesCameraPosition": _bool(payload["changesCameraPosition"], "changesCameraPosition"),
        "relabelsLighting": _bool(payload["relabelsLighting"], "relabelsLighting"),
        "applyMutant": _bool(payload["applyMutant"], "applyMutant"),
    }


def decide_guidance(
    *,
    case_id: str,
    evidence_id: str,
    claim: str,
    measured_limits: object,
    selected_limit_id: object,
    guidance: object,
    flags: dict[str, bool],
) -> dict[str, Any]:
    """Apply the phase oracle. Evidence stays in preservedResults either way."""
    judged = judge_guidance(measured_limits, selected_limit_id, guidance)
    rejected = list(judged["rejectedClaims"])
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "goal: " + GOAL,
        "fixture: " + FIXTURE,
    ]
    reasons.extend(judged["reasons"])
    texts = judged["preservedResults"][1]
    if flags["applyMutant"] or (flags["cinematicPresetActive"] and not flags["clippingWarningsVisible"]):
        _reject(rejected, MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
    if flags["adviceChangesSettings"]:
        _reject(rejected, CLAIM_SETTINGS)
        reasons.append("advice was separated from automatic changes")
    if flags["changesCameraPosition"]:
        _reject(rejected, CLAIM_CAMERA)
        reasons.append("software did not move the physical camera")
    if flags["relabelsLighting"]:
        _reject(rejected, CLAIM_LIGHTING)
        reasons.append("software did not relabel the lighting")
    if flags["sourceClipped"] and not any("clipped" in text.lower() for text in texts):
        _reject(rejected, CLAIM_CLIP)
        reasons.append("clipped source was explained instead of hidden")
    if (
        flags["sourceOutOfFocus"]
        and flags["virtualShallowFocusSelected"]
        and not any("out of focus" in text.lower() for text in texts)
    ):
        _reject(rejected, CLAIM_FOCUS)
        reasons.append("out-of-focus source was explained instead of restored")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("method: " + METHOD)
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("guidance stayed advice and user control was preserved")
    questions = [
        "physical S23 measurement was not run",
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
    ]
    preserved = [evidence_id, claim]
    preserved.extend(judged["preservedResults"])
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    return _seal(result, evidence_id)


def _seal(result: dict[str, Any], evidence_id: str) -> dict[str, Any]:
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(result["decision"] in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(isinstance(result["reasons"], list) and result["reasons"], "reasons must be non-empty")
    require(isinstance(result["rejectedClaims"], list), "rejectedClaims must be a list")
    require(isinstance(result["preservedResults"], list) and result["preservedResults"], "evidence wiped")
    require(evidence_id in result["preservedResults"], "evidence must be preserved")
    require(isinstance(result["openQuestions"], list) and result["openQuestions"], "openQuestions must be non-empty")
    require(
        any("physical S23" in item for item in result["openQuestions"]),
        "physical S23 measurement was not noted",
    )
    return result


def assess(document: dict) -> dict[str, Any]:
    """Apply the phase oracle to one guidance fixture."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = _text(document["evidenceId"], "evidenceId")
    claim = _text(document["claim"], "claim")
    flags = _source_flags(document)
    return decide_guidance(
        case_id=PHASE,
        evidence_id=evidence,
        claim=claim,
        measured_limits=document["measuredLimits"],
        selected_limit_id=document["selectedLimitId"],
        guidance=document["guidance"],
        flags=flags,
    )


def evaluate(payload: dict) -> dict[str, Any]:
    """Judge one guidance payload. Invalid shapes raise ValueError."""
    require(isinstance(payload, dict), "payload must be an object")
    missing = EVALUATE_KEYS - set(payload)
    extra = set(payload) - EVALUATE_KEYS
    require(not missing, "payload missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))
    case_id = _text(payload["caseId"], "caseId")
    evidence = _text(payload["evidenceId"], "evidenceId")
    claim = _text(payload["claim"], "claim")
    flags = _source_flags(payload)
    return decide_guidance(
        case_id=case_id,
        evidence_id=evidence,
        claim=claim,
        measured_limits=payload["measuredLimits"],
        selected_limit_id=payload["selectedLimitId"],
        guidance=payload["guidance"],
        flags=flags,
    )
