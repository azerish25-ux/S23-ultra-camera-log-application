#!/usr/bin/env python3
"""P103 Estimate confidence and uncertainty.

Host fixture only. Confidence scores are control signals, not physical
probabilities. This module does not probe a device and does not qualify a
physical S23.
"""

from __future__ import annotations

import math
from typing import Any

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P103"
TITLE = "Estimate confidence and uncertainty"
GOAL = "Prevent uncertain depth from producing unnecessarily aggressive visual artifacts."
METHOD = (
    "Use available model confidence or explicitly defined proxy measures, consistency checks, "
    "and boundary uncertainty. Calibrate thresholds against held-out footage. Confidence controls "
    "rendering strength and fallback; it must not be presented as a probability without calibration."
)
FIXTURE = "A low-texture wall and a transparent glass edge where repeated estimates vary significantly."
ORACLE = (
    "The renderer receives low-confidence regions and can reduce blur instead of forcing an "
    "unstable segmentation boundary."
)
MUTANT = "Treat every depth pixel as equally reliable."
DELIVERABLE = "Confidence policy and uncertainty-aware rendering tests"
WORKSTREAM = 13
DEPENDENCIES = ("P102",)
BIN_COUNT = 5
LOW_CONFIDENCE_THRESHOLD = 0.5
ARBITRARY_CALIBRATED_TOKEN = "arbitrary-confidence-score-presented-calibrated-probability"
ECE_TOKEN = "expected-calibration-error-exceeds-declared-max"
NARROW_INTERVAL_TOKEN = "high-error-uncertainty-narrower-than-low-error"
BLUR_TOKEN = "low-confidence-blur-not-reduced"
PHYSICAL_TOKEN = "physical-probability-claimed"

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "tolerance",
    "maxEce",
    "calibrated",
    "calibrationSetId",
    "binCounts",
    "confidenceMetadataPresent",
    "pairs",
    "blurReducedOnLowConfidence",
    "applyMutant",
}
PAIR_KEYS = {"confidence", "absoluteError", "intervalWidth"}
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


def _number(value: Any, label: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{label} must be a number")
    number = float(value)
    require(math.isfinite(number), f"{label} must be finite")
    return number


def _text(value: Any, label: str) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(), f"{label} must be a non-empty string")
    return value


def bin_index(confidence: float, bins: int = BIN_COUNT) -> int:
    """Map a confidence in [0, 1] onto ``bins`` equal bins. The last bin includes 1."""
    require(bins >= 1, "bins must be positive")
    if confidence >= 1.0:
        return bins - 1
    index = int(confidence * bins)
    if index < 0:
        return 0
    if index >= bins:
        return bins - 1
    return index


def expected_calibration_error(
    samples: list[tuple[float, float]],
    tolerance: float,
    bins: int = BIN_COUNT,
) -> float:
    """Unweighted mean over non-empty bins of |mean(confidence) - mean(accuracy)|.

    Each sample is ``(confidence, absolute_depth_error)``. Accuracy is 1 when
    ``absolute_depth_error <= tolerance`` and 0 otherwise. Empty bins are omitted
    because a bin mean is undefined without samples. This is not a physical probability.
    """
    require(isinstance(samples, list) and samples, "samples must be a non-empty list")
    require(isinstance(tolerance, (int, float)) and not isinstance(tolerance, bool), "tolerance must be a number")
    require(math.isfinite(float(tolerance)) and float(tolerance) >= 0.0, "tolerance must be finite and >= 0")
    require(isinstance(bins, int) and not isinstance(bins, bool) and bins >= 1, "bins must be a positive int")
    grouped: list[list[tuple[float, float]]] = [[] for _ in range(bins)]
    for index, sample in enumerate(samples):
        require(isinstance(sample, tuple) and len(sample) == 2, f"sample {index} must be a pair")
        confidence = _number(sample[0], f"sample {index} confidence")
        error = _number(sample[1], f"sample {index} absolute error")
        require(0.0 <= confidence <= 1.0, f"sample {index} confidence must be in 0..1")
        require(error >= 0.0, f"sample {index} absolute error must be >= 0")
        accuracy = 1.0 if error <= float(tolerance) else 0.0
        grouped[bin_index(confidence, bins)].append((confidence, accuracy))
    gaps: list[float] = []
    for bucket in grouped:
        if not bucket:
            continue
        mean_confidence = sum(item[0] for item in bucket) / len(bucket)
        mean_accuracy = sum(item[1] for item in bucket) / len(bucket)
        gaps.append(abs(mean_confidence - mean_accuracy))
    require(gaps, "expected calibration error needs at least one non-empty bin")
    return sum(gaps) / len(gaps)


def intervals_narrow_on_high_error(
    samples: list[tuple[float, float]],
    tolerance: float,
) -> bool:
    """True when high-error samples have a narrower mean interval than low-error samples.

    High error means absolute error > tolerance. Accuracy uses <= tolerance, so the
    boundary sample stays in the low-error class. One-sided samples are not an inversion.
    """
    require(isinstance(samples, list), "interval samples must be a list")
    require(isinstance(tolerance, (int, float)) and not isinstance(tolerance, bool), "tolerance must be a number")
    require(math.isfinite(float(tolerance)) and float(tolerance) >= 0.0, "tolerance must be finite and >= 0")
    high: list[float] = []
    low: list[float] = []
    for index, sample in enumerate(samples):
        require(isinstance(sample, tuple) and len(sample) == 2, f"interval sample {index} must be a pair")
        error = _number(sample[0], f"interval sample {index} absolute error")
        width = _number(sample[1], f"interval sample {index} width")
        require(error >= 0.0, f"interval sample {index} absolute error must be >= 0")
        require(width >= 0.0, f"interval sample {index} width must be >= 0")
        if error > float(tolerance):
            high.append(width)
        else:
            low.append(width)
    if not high or not low:
        return False
    return (sum(high) / len(high)) < (sum(low) / len(low))


def _pairs(document: dict) -> list[dict]:
    raw = document["pairs"]
    require(isinstance(raw, list), "pairs must be a list")
    parsed: list[dict] = []
    for index, item in enumerate(raw):
        require(isinstance(item, dict), f"pair {index} must be an object")
        require(set(item) == PAIR_KEYS, f"pair {index} keys must be confidence, absoluteError, intervalWidth")
        parsed.append(item)
    return parsed


def _calibration_fields(document: dict) -> None:
    calibrated = document["calibrated"]
    require(type(calibrated) is bool, "calibrated must be a bool")
    set_id = document["calibrationSetId"]
    counts = document["binCounts"]
    if not calibrated:
        require(set_id is None, "calibrationSetId must be null unless calibrated")
        require(counts is None, "binCounts must be null unless calibrated")
        return
    if set_id is not None:
        _text(set_id, "calibrationSetId")
    if counts is not None:
        require(isinstance(counts, list) and len(counts) == BIN_COUNT, "binCounts must contain 5 integers")
        total = 0
        for index, count in enumerate(counts):
            require(type(count) is int, f"binCounts[{index}] must be an int")
            require(count >= 0, f"binCounts[{index}] must be >= 0")
            total += count
        require(total > 0, "binCounts must describe a non-empty calibration set")


def _claims_physical_probability(claim: str) -> bool:
    lowered = claim.lower()
    return "physical probability" in lowered or "physical probabilities" in lowered


def assess(document: dict) -> dict[str, Any]:
    """Apply the confidence policy. Decisions are recorded or rejected, never qualified."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = _text(document["evidenceId"], "evidenceId")
    claim = _text(document["claim"], "claim")
    tolerance = _number(document["tolerance"], "tolerance")
    require(tolerance > 0.0, "tolerance must be > 0")
    max_ece = _number(document["maxEce"], "maxEce")
    require(0.0 <= max_ece <= 1.0, "maxEce must be in 0..1")
    require(type(document["confidenceMetadataPresent"]) is bool, "confidenceMetadataPresent must be a bool")
    require(type(document["blurReducedOnLowConfidence"]) is bool, "blurReducedOnLowConfidence must be a bool")
    require(type(document["applyMutant"]) is bool, "applyMutant must be a bool")
    _calibration_fields(document)
    pairs = _pairs(document)
    metadata = document["confidenceMetadataPresent"]
    if metadata:
        require(pairs, "pairs are required when confidence metadata is present")
    else:
        for index, item in enumerate(pairs):
            require(item["confidence"] is None, f"pair {index} confidence must be null when metadata is absent")

    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "scores are not physical probabilities",
        "ECE = mean over non-empty bins of |mean(confidence)-mean(accuracy)| "
        "with accuracy 1 if absolute error <= tolerance else 0; bins=5",
    ]
    rejected: list[str] = []
    questions = [
        "physical S23 was not run",
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, "
        "and cinema-camera equivalence are not claimed",
        "confidence scores are not physical probabilities",
    ]
    status = "uncalibrated"
    reliance = 0.0
    ece: float | None = None

    if _claims_physical_probability(claim):
        rejected.append(PHYSICAL_TOKEN)
        reasons.append("physical probability claim rejected")
    if document["applyMutant"]:
        rejected.append(MUTANT)
        reasons.append("mutant rejected: " + MUTANT)

    interval_samples: list[tuple[float, float]] = []
    for index, item in enumerate(pairs):
        error = _number(item["absoluteError"], f"pair {index} absoluteError")
        width = _number(item["intervalWidth"], f"pair {index} intervalWidth")
        require(error >= 0.0, f"pair {index} absoluteError must be >= 0")
        require(width >= 0.0, f"pair {index} intervalWidth must be >= 0")
        interval_samples.append((error, width))

    if not metadata:
        status = "uncalibrated"
        reliance = 0.0
        reasons.append("confidence metadata missing; status=uncalibrated; relianceWeight=0; not treated as certain")
        if document["calibrated"] is True:
            rejected.append(ARBITRARY_CALIBRATED_TOKEN)
            reasons.append("missing confidence metadata cannot be a calibrated probability")
    else:
        scored: list[tuple[float, float]] = []
        confidences: list[float] = []
        for index, item in enumerate(pairs):
            confidence = _number(item["confidence"], f"pair {index} confidence")
            require(0.0 <= confidence <= 1.0, f"pair {index} confidence must be in 0..1")
            error = _number(item["absoluteError"], f"pair {index} absoluteError")
            scored.append((confidence, error))
            confidences.append(confidence)
        ece = expected_calibration_error(scored, tolerance, BIN_COUNT)
        reasons.append(f"expectedCalibrationError={ece:.6f}; maxEce={max_ece:.6f}; tolerance={tolerance:.6f}")
        low_confidence = [value for value in confidences if value < LOW_CONFIDENCE_THRESHOLD]
        if document["calibrated"] is True:
            set_id = document["calibrationSetId"]
            counts = document["binCounts"]
            if set_id is None or counts is None:
                rejected.append(ARBITRARY_CALIBRATED_TOKEN)
                reasons.append("calibrated=true without a calibration set id and bin counts")
            elif ece > max_ece + 1e-12:
                rejected.append(ECE_TOKEN)
                reasons.append("calibrated probability claim rejected because ECE exceeds the declared max")
            else:
                status = "calibrated-score"
                reliance = min(confidences)
                reasons.append(
                    "calibrated-score retained as a rendering control; not a physical probability; "
                    f"relianceWeight={reliance:.6f}"
                )
        else:
            status = "uncalibrated"
            reliance = min(confidences)
            reasons.append(
                "confidence metadata present but uncalibrated; not a physical probability; "
                f"relianceWeight={reliance:.6f}"
            )
        if low_confidence and document["blurReducedOnLowConfidence"] is not True:
            rejected.append(BLUR_TOKEN)
            reasons.append("low-confidence region did not reduce blur")
        elif low_confidence:
            reasons.append("low-confidence region reduces blur instead of forcing an unstable boundary")

    if interval_samples and intervals_narrow_on_high_error(interval_samples, tolerance):
        rejected.append(NARROW_INTERVAL_TOKEN)
        reasons.append("high-error samples have narrower uncertainty intervals than low-error samples")
    elif interval_samples:
        reasons.append("uncertainty intervals are not narrower on high-error samples")

    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("narrower software result retained; physical behavior stays open")
        reasons.append("method: " + METHOD)
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    if not metadata:
        require(status == "uncalibrated" and reliance == 0.0, "missing confidence metadata must stay uncalibrated")
    preserved = [
        evidence,
        claim,
        f"calibrationStatus={status}",
        f"relianceWeight={reliance:.6f}",
    ]
    if ece is not None:
        preserved.append(f"expectedCalibrationError={ece:.6f}")
    result = {
        "caseId": PHASE,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    return result


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate one confidence-and-uncertainty payload. Invalid input raises ValueError."""
    require(isinstance(payload, dict), "payload must be an object")
    return assess(payload)
