"""TC-P107-02 Disoccluded background.

Host reference. Newly visible pixels must use current evidence, not old depth.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P107-02"
NAME = "Disoccluded background"
INTERVENTION = "Reveal new background behind a moving foreground object where historical depth is invalid."
EXPECTED = "Use current evidence and uncertainty rather than smearing previous foreground values into the new region."
NEGATIVE = "Filling all newly visible pixels with old depth must fail."
REPEAT = "Repeat thin objects, hands, hair, and large foreground occluders."
NEGATIVE_TOKEN = "old-depth-fill"
PIXEL_KEYS = {"id", "current_depth", "historical_depth", "filled_with_old_depth", "uncertainty"}
PAYLOAD_KEYS = ("evidenceId", "repeat", "pixels")
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _number(value: object, label: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{label} must be a number")
    value_f = float(value)
    _require(math.isfinite(value_f), f"{label} must be finite")
    return value_f


def evaluate(payload: dict) -> dict:
    _require(isinstance(payload, dict) and set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(), "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    pixels = payload["pixels"]
    _require(isinstance(pixels, list) and pixels, "pixels must be a non-empty list")
    smeared = 0
    uncertainties: list[float] = []
    for index, pixel in enumerate(pixels):
        _require(isinstance(pixel, dict) and set(pixel) == PIXEL_KEYS, f"pixels[{index}] has invalid keys")
        _require(isinstance(pixel["id"], str) and pixel["id"].strip(), f"pixels[{index}].id must be a string")
        _require(type(pixel["filled_with_old_depth"]) is bool, "filled_with_old_depth must be a bool")
        current = _number(pixel["current_depth"], f"pixels[{index}].current_depth")
        uncertainty = _number(pixel["uncertainty"], f"pixels[{index}].uncertainty")
        _require(uncertainty >= 0.0, "uncertainty must be non-negative")
        historical = pixel["historical_depth"]
        if historical is not None:
            _number(historical, f"pixels[{index}].historical_depth")
        if pixel["filled_with_old_depth"]:
            smeared += 1
        else:
            uncertainties.append(uncertainty)
        del current
    fraction = smeared / float(len(pixels))
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        INTERVENTION,
        f"smeared={smeared}/{len(pixels)}",
    ]
    rejected: list[str] = []
    if smeared:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE if fraction == 1.0 else "old depth was written into newly visible pixels")
        if fraction == 1.0:
            reasons.append("every newly visible pixel was filled with old depth")
    else:
        mean_uncertainty = sum(uncertainties) / float(len(uncertainties))
        reasons.append("current evidence retained; mean uncertainty %s" % format(mean_uncertainty, ".12g"))
    decision = "rejected" if rejected else "recorded"
    preserved = [evidence, f"smear_fraction={format(fraction, '.12g')}"]
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 was not run", REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result
