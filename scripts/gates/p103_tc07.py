"""TC-P103-07 Confidence misrepresentation.

Host fixture. An arbitrary score is not a calibrated probability. Expected
calibration error uses five bins and is not a physical probability.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P103-07"
NAME = "Confidence misrepresentation"
INTERVENTION = "Provide unstable or unreliable predictions while their confidence metadata claims certainty."
EXPECTED = "Expose uncalibrated confidence and reduce rendering reliance according to the declared policy."
NEGATIVE = "An arbitrary confidence score must not be presented as a calibrated probability."
REPEAT = "Repeat transparent surfaces, low texture, mirrors, and unfamiliar scenes."
NEGATIVE_TOKEN = "arbitrary-confidence-score-presented-calibrated-probability"
ECE_TOKEN = "expected-calibration-error-exceeds-declared-max"
NARROW_INTERVAL_TOKEN = "high-error-uncertainty-narrower-than-low-error"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "applyNegative",
    "applyMutant",
    "calibrated",
    "calibrationSetId",
    "binCounts",
    "tolerance",
    "maxEce",
    "confidenceMetadataPresent",
    "blurReducedOnLowConfidence",
    "pairs",
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
    "p103_estimate_confidence_and_uncertainty_for_tc07",
    Path(__file__).resolve().with_name("p103_estimate_confidence_and_uncertainty.py"),
)
_PHASE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_PHASE)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    for name in ("applyNegative", "applyMutant", "calibrated", "confidenceMetadataPresent", "blurReducedOnLowConfidence"):
        if type(payload[name]) is not bool:
            raise ValueError(f"{name} must be a bool")
    tolerance = _PHASE._number(payload["tolerance"], "tolerance")
    if tolerance <= 0.0:
        raise ValueError("tolerance must be > 0")
    max_ece = _PHASE._number(payload["maxEce"], "maxEce")
    if not 0.0 <= max_ece <= 1.0:
        raise ValueError("maxEce must be in 0..1")
    pairs = payload["pairs"]
    if not isinstance(pairs, list):
        raise ValueError("pairs must be a list")
    set_id = payload["calibrationSetId"]
    counts = payload["binCounts"]
    if payload["calibrated"] is not True:
        if set_id is not None or counts is not None:
            raise ValueError("calibration set fields require calibrated=true")
    else:
        if set_id is not None:
            _text(set_id, "calibrationSetId")
        if counts is not None:
            if not isinstance(counts, list) or len(counts) != _PHASE.BIN_COUNT:
                raise ValueError("binCounts must contain 5 integers")
            if any(type(count) is not int or count < 0 for count in counts) or sum(counts) <= 0:
                raise ValueError("binCounts must be five non-negative ints with a positive total")
    scored: list[tuple[float, float]] = []
    widths: list[tuple[float, float]] = []
    for index, item in enumerate(pairs):
        if not isinstance(item, dict):
            raise ValueError(f"pair {index} must be an object")
        if set(item) != {"confidence", "absoluteError", "intervalWidth"}:
            raise ValueError(f"pair {index} keys are invalid")
        error = _PHASE._number(item["absoluteError"], f"pair {index} absoluteError")
        width = _PHASE._number(item["intervalWidth"], f"pair {index} intervalWidth")
        if error < 0.0 or width < 0.0:
            raise ValueError(f"pair {index} error and interval must be >= 0")
        widths.append((error, width))
        if payload["confidenceMetadataPresent"] is not True:
            if item["confidence"] is not None:
                raise ValueError(f"pair {index} confidence must be null when metadata is absent")
        else:
            confidence = _PHASE._number(item["confidence"], f"pair {index} confidence")
            if not 0.0 <= confidence <= 1.0:
                raise ValueError(f"pair {index} confidence must be in 0..1")
            scored.append((confidence, error))
    if payload["confidenceMetadataPresent"] and not scored:
        raise ValueError("pairs are required when confidence metadata is present")

    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        "scores are not physical probabilities",
        "ECE = mean over non-empty bins of |mean(confidence)-mean(accuracy)| "
        "with accuracy 1 if absolute error <= tolerance else 0; bins=5",
    ]
    rejected: list[str] = []
    status = "uncalibrated"
    reliance = 0.0
    if payload["applyMutant"] or payload["applyNegative"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if payload["confidenceMetadataPresent"] is not True:
        status = "uncalibrated"
        reliance = 0.0
        reasons.append("confidence metadata missing; status=uncalibrated; relianceWeight=0; not treated as certain")
        if payload["calibrated"] is True and NEGATIVE_TOKEN not in rejected:
            rejected.append(NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
    else:
        ece = _PHASE.expected_calibration_error(scored, tolerance, _PHASE.BIN_COUNT)
        reasons.append(f"expectedCalibrationError={ece:.6f}; maxEce={max_ece:.6f}")
        low_confidence = any(confidence < _PHASE.LOW_CONFIDENCE_THRESHOLD for confidence, _error in scored)
        if payload["calibrated"] is True:
            if set_id is None or counts is None:
                if NEGATIVE_TOKEN not in rejected:
                    rejected.append(NEGATIVE_TOKEN)
                    reasons.append(NEGATIVE)
                reasons.append("calibrated=true without a calibration set id and bin counts")
            elif ece > max_ece + 1e-12:
                rejected.append(ECE_TOKEN)
                reasons.append("calibrated probability claim rejected because ECE exceeds the declared max")
            else:
                status = "calibrated-score"
                reliance = min(confidence for confidence, _error in scored)
                reasons.append(
                    "calibrated-score retained as a rendering control; not a physical probability; "
                    f"relianceWeight={reliance:.6f}"
                )
        else:
            reliance = min(confidence for confidence, _error in scored)
            reasons.append(
                "uncalibrated confidence exposed; not a physical probability; "
                f"relianceWeight={reliance:.6f}"
            )
        if low_confidence and payload["blurReducedOnLowConfidence"] is not True:
            rejected.append("low-confidence-blur-not-reduced")
            reasons.append("low-confidence region did not reduce blur")
    if widths and _PHASE.intervals_narrow_on_high_error(widths, tolerance):
        rejected.append(NARROW_INTERVAL_TOKEN)
        reasons.append("high-error samples have narrower uncertainty intervals than low-error samples")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append(f"calibrationStatus={status}; relianceWeight={reliance:.6f}")
        reasons.append("narrower software result retained; physical behavior stays open")
    if payload["confidenceMetadataPresent"] is not True and decision == "recorded":
        if status != "uncalibrated" or reliance != 0.0:
            raise ValueError("missing confidence metadata must stay uncalibrated with reliance weight 0")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, f"calibrationStatus={status}", f"relianceWeight={reliance:.6f}"],
        "openQuestions": ["physical S23 was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
