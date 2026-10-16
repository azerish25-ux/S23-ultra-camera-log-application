"""TC-P102-07 Confidence misrepresentation.

Host reference. A score presented as a calibrated probability must come with
calibration residuals whose mean absolute value is within 0.1. Otherwise it
stays an uncalibrated score and unstable predictions must reduce reliance.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P102-07"
NAME = "Confidence misrepresentation"
INTERVENTION = "Provide unstable or unreliable predictions while their confidence metadata claims certainty."
EXPECTED = "Expose uncalibrated confidence and reduce rendering reliance according to the declared policy."
NEGATIVE = "An arbitrary confidence score must not be presented as a calibrated probability."
REPEAT = "Repeat transparent surfaces, low texture, mirrors, and unfamiliar scenes."
NEGATIVE_TOKEN = "arbitrary-confidence-score-presented-calibrated-probability"
SCENE_TAGS = {"transparent-surfaces", "low-texture", "mirrors", "unfamiliar-scenes"}
PAYLOAD_KEYS = {
    "evidenceId",
    "repeat",
    "predictionsUnstable",
    "confidenceScore",
    "presentedAsCalibratedProbability",
    "confidenceCalibrated",
    "renderingRelianceReduced",
    "calibrationResiduals",
    "sceneTag",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
CALIBRATION_LIMIT = 0.1


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def evaluate(payload: dict) -> dict:
    _require(isinstance(payload, dict) and set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
             "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    for flag in ("predictionsUnstable", "presentedAsCalibratedProbability", "confidenceCalibrated", "renderingRelianceReduced"):
        _require(type(payload[flag]) is bool, flag + " must be a bool")
    score = payload["confidenceScore"]
    _require(isinstance(score, (int, float)) and not isinstance(score, bool), "confidenceScore must be a number")
    score = float(score)
    _require(math.isfinite(score) and 0 <= score <= 1, "confidenceScore must be finite and in [0, 1]")
    residuals = payload["calibrationResiduals"]
    _require(isinstance(residuals, list) and len(residuals) <= 32, "calibrationResiduals must be a list")
    parsed: list[float] = []
    for index, item in enumerate(residuals):
        _require(isinstance(item, (int, float)) and not isinstance(item, bool), f"residual {index} must be a number")
        value = float(item)
        _require(math.isfinite(value), f"residual {index} must be finite")
        parsed.append(value)
    scene = payload["sceneTag"]
    _require(scene in SCENE_TAGS, "sceneTag is not a repeat scene")

    rejected: list[str] = []
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, f"repeat {repeat}", "scene " + scene]
    mean_abs = None
    if parsed:
        mean_abs = sum(abs(item) for item in parsed) / len(parsed)
        reasons.append(f"calibration-mean-abs={mean_abs:.3f}")
    presented = payload["presentedAsCalibratedProbability"]
    if presented:
        calibrated = payload["confidenceCalibrated"] and mean_abs is not None and mean_abs <= CALIBRATION_LIMIT
        if not calibrated:
            rejected.append(NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
            reasons.append(f"confidence {score:.3f} is not a calibrated probability")
    if payload["predictionsUnstable"] and not payload["renderingRelianceReduced"]:
        rejected.append("rendering-reliance-not-reduced")
        reasons.append("unstable predictions did not reduce rendering reliance")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        if presented:
            reasons.append("calibrated confidence retained with residuals inside 0.1")
        else:
            reasons.append("confidence left uncalibrated")
    extra = ["uncalibrated" if not presented else "calibrated"]
    if mean_abs is not None:
        extra.append(f"calibration-mean-abs:{mean_abs:.3f}")
    return _finish(decision, reasons, rejected, evidence, extra)


def _finish(decision: str, reasons: list[str], rejected: list[str], evidence: str, extra: list[str]) -> dict:
    _require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, *extra],
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result
